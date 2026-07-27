#!/usr/bin/env bash
# 容器入口：校验 secrets 权限 → 装载 crontab → 前台 cron。
# 带参数时透传执行（调试/验收用，如 docker run <img> sh -c '…'），不进 cron。
set -euo pipefail

# 业务锚不变量：容器挂钟必须是北京时间（+0800，中国无夏令时，全年零漂移）。
# 任何运行时 TZ 覆盖（曾见 docker-compose environment 误设 Australia/Sydney）都会让
# cron 按错时区评估排程、让技能打错报表日期——此处快速失败，杜绝 #100/#108 锚定被静默回退。
TZ_OFFSET="$(date +%z)"
if [ "$TZ_OFFSET" != "+0800" ]; then
  echo "拒绝启动：容器挂钟偏移 $TZ_OFFSET（TZ=${TZ:-未设}），业务锚要求 +0800（Asia/Shanghai）。" >&2
  echo "  多半是 docker-compose 的 environment.TZ 覆盖了镜像 Asia/Shanghai——改回 Asia/Shanghai。" >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

SECRETS=/opt/kmfa/secrets/skills.env

# Coolify 部署没有宿主机 bind mount，/opt/kmfa/secrets/skills.env 永远不存在——
# 于是每一次 cron 触发都以 NOTIFIER_CONFIG_MISSING 空跑：技能"在跑"但一条钉钉都不发
# （Owner 实报：所有 skill 没运行、钉钉零消息；容器日志坐实是这一行警告）。
# 修法与下面的备份密钥同构：把 Coolify 注入的环境变量在启动时**合成**成 600 的 skills.env。
# 只写"有值"的键：全空则不生成文件，仍走原告警路径，不伪装成已配置。
if [ ! -f "$SECRETS" ]; then
  mkdir -p /opt/kmfa/secrets /var/log/kmfa   # 日志目录须先于下面写 cron.log 存在
  TMP_ENV="$(mktemp)"
  for k in DINGTALK_ROBOT_URL DINGTALK_ROBOT_SIGNING_KEY DINGTALK_DING_ROBOT_CODE \
           KMFA_ALERT_WEBHOOK_TOKEN KMFA_DELIVERY_ENABLED \
           KMFA_BACKUP_GH_TOKEN KMFA_NOTIFICATION_TARGETS \
           KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS; do
    v="$(printenv "$k" 2>/dev/null || true)"
    [ -n "$v" ] && printf '%s=%s\n' "$k" "$v" >> "$TMP_ENV"
  done
  if [ -s "$TMP_ENV" ]; then
    install -m 600 "$TMP_ENV" "$SECRETS"
    # 只记键名与条数，绝不记值
    echo "$(date -Is) entrypoint: 已从环境变量合成 skills.env（$(wc -l < "$SECRETS") 项：$(cut -d= -f1 "$SECRETS" | tr '\n' ' ')）" >> /var/log/kmfa/cron.log
  fi
  rm -f "$TMP_ENV"
fi

if [ -f "$SECRETS" ]; then
  PERM="$(stat -c '%a' "$SECRETS" 2>/dev/null || stat -f '%Lp' "$SECRETS")"
  if [ "$PERM" != "600" ] && [ "$PERM" != "400" ]; then
    echo "拒绝启动：$SECRETS 权限为 $PERM，要求 600/400" >&2
    exit 1
  fi
else
  echo "警告：$SECRETS 不存在——全部技能将以 NOTIFIER_CONFIG_MISSING 空跑" >&2
fi

mkdir -p /var/log/kmfa

# App 状态面备份的部署密钥：Coolify 传 base64 单行（私钥多行且含敏感内容，不宜进 cron.d 0644）。
# 这里在启动时解到 600 文件，只把**路径**给 cron —— 密钥本体不落 cron.d、不进日志。
BACKUP_KEY_FILE=/opt/kmfa/secrets/kmfa_backup_deploy_key
if [ -n "${KMFA_BACKUP_SSH_KEY_B64:-}" ]; then
  mkdir -p /opt/kmfa/secrets
  echo "$KMFA_BACKUP_SSH_KEY_B64" | base64 -d > "$BACKUP_KEY_FILE" 2>/dev/null \
    && chmod 600 "$BACKUP_KEY_FILE" \
    && echo "$(date -Is) entrypoint: 备份部署密钥已就位（600）" >> /var/log/kmfa/cron.log \
    || echo "$(date -Is) entrypoint: 警告——KMFA_BACKUP_SSH_KEY_B64 解码失败，异地备份将降级" >> /var/log/kmfa/cron.log
fi

# 排程只走 /etc/cron.d，不碰用户 crontab。
#
# 原实现是 `crontab <file> 2>/dev/null || cp <file> /etc/cron.d/kmfa-skills`，
# 指望 crontab 对系统格式文件报错后走 || 右边。**实测它退出码 0**：crontab.txt 带
# user 字段（`root /opt/runtime/run_skill.sh ...`），`crontab` 把 "root ..." 整体
# 当成命令原样收下，于是排程被静默装成用户 crontab，每次触发只吐
# "root: command not found"——10 条排程从上线起一次都没执行过（含 dws-keepalive，
# 即 #123 补回的认证保活，因此那个"修复"实际从未生效）。
# 教训：别拿命令的返回码去猜它是否理解了输入格式。
CRON_D=/etc/cron.d/kmfa-skills
crontab -r 2>/dev/null || true   # 清掉可能残留的用户 crontab，杜绝两种格式并存重复触发

# cron **不继承容器环境**，必须把值写进 cron.d 文件头；且 cron.d **不做变量展开**，
# 所以这里用实际值渲染，不能照抄 "${VAR:-0}" 字面量。
# 每一行都是实测出来的坑：
#   HOME     —— 缺了 dws 找不到 /root/.dws，首跑直接 DWS_AUTH_REQUIRED rc=2
#   TZ       —— 缺了 cron 按 UTC 评估排程，晨报会在错误时刻触发（#100/#108 的锚定被绕开）
#   DELIVERY —— 缺了任务按 dry-run 跑，ledger 记 delivery_enabled:"0"，消息永远发不出去
{
  echo "SHELL=/bin/bash"
  echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  echo "HOME=/root"
  echo "TZ=${TZ}"
  echo "KMFA_DELIVERY_ENABLED=${KMFA_DELIVERY_ENABLED:-0}"
  echo "KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS=${KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS:-0}"
  echo "KMFA_ATTENDANCE_ARCHIVE_ROOT=${KMFA_ATTENDANCE_ARCHIVE_ROOT:-/var/lib/kmfa/attendance}"
  # 备份密钥文件路径（值是路径不是密钥本体，单行安全）；密钥不在时 daily-backup 自动降级。
  [ -f "$BACKUP_KEY_FILE" ] && echo "KMFA_BACKUP_SSH_KEY_FILE=$BACKUP_KEY_FILE"
  echo
  # 源文件自带的 SHELL/PATH 去掉，避免与上面重复
  grep -vE '^(SHELL|PATH)=' /opt/runtime/crontab.txt
} > "$CRON_D"
chmod 0644 "$CRON_D"; chown root:root "$CRON_D"
# cron.d 硬性要求：文件名不含点（kmfa-skills 合规）、末尾必须有换行
if [ -n "$(tail -c1 "$CRON_D")" ]; then
  echo >> "$CRON_D"
fi
# 归档根必须存在且可写——否则考勤报告写不出去
mkdir -p "${KMFA_ATTENDANCE_ARCHIVE_ROOT:-/var/lib/kmfa/attendance}"

# 装完自检——**装不上就不许启动**。静默失效比起不来危险得多：上一版就是这样
# 安安静静一个月不发消息，还得靠 Owner 说"我没收到"才被发现。
#
# 注意两处 `|| true`：本脚本开了 set -e，而 `grep -c` 数到 0 条时**退出码是 1**，
# 不加就会在这里静默打死脚本、连下面的拒绝理由都打不出来——第一版就这么写的，
# 负例测试里容器确实退出了却不说为什么，等于把"静默失败"又造了一遍。
EXPECT_JOBS="$(grep -cE '^[0-9*].*run_skill' /opt/runtime/crontab.txt || true)"
GOT_JOBS="$(grep -cE '^[0-9*].*run_skill' "$CRON_D" 2>/dev/null || true)"
EXPECT_JOBS="${EXPECT_JOBS:-0}"
GOT_JOBS="${GOT_JOBS:-0}"
if [ "$GOT_JOBS" -ne "$EXPECT_JOBS" ] || [ "$EXPECT_JOBS" -eq 0 ]; then
  echo "拒绝启动：排程装入 $CRON_D 失败（期望 $EXPECT_JOBS 条，实得 $GOT_JOBS 条）" >&2
  exit 1
fi
if crontab -l >/dev/null 2>&1; then
  echo "拒绝启动：仍存在用户 crontab，与 cron.d 并存会重复触发" >&2
  exit 1
fi
# 环境行也要自检：少一行就是一整类静默失效（认证失败/时刻错乱/永远 dry-run）
for KEY in HOME TZ KMFA_DELIVERY_ENABLED KMFA_ATTENDANCE_ARCHIVE_ROOT; do
  grep -qE "^${KEY}=" "$CRON_D" || {
    echo "拒绝启动：$CRON_D 缺环境行 ${KEY}=（cron 不继承容器环境）" >&2
    exit 1
  }
done
echo "$(date -Is) entrypoint: 排程已装入 $CRON_D（$GOT_JOBS 条）" >> /var/log/kmfa/cron.log
touch /var/log/kmfa/cron.log /var/log/kmfa/ledger.jsonl
echo "$(date -Is) entrypoint: cron 启动（TZ=$TZ，KMFA_DELIVERY_ENABLED=${KMFA_DELIVERY_ENABLED:-0}）" >> /var/log/kmfa/cron.log
exec cron -f
