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
           KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS \
           KMFA_ATTENDANCE_RUNTIME_DIR; do
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
  echo "KMFA_ATTENDANCE_ARCHIVE_ROOT=${KMFA_ATTENDANCE_ARCHIVE_ROOT:-/var/log/kmfa/dingtalk_attendance}"
  # 备份密钥文件路径（值是路径不是密钥本体，单行安全）；密钥不在时 daily-backup 自动降级。
  [ -f "$BACKUP_KEY_FILE" ] && echo "KMFA_BACKUP_SSH_KEY_FILE=$BACKUP_KEY_FILE"
  echo
  # 源文件自带的 SHELL/PATH 去掉，避免与上面重复。
  #
  # 压测节拍的总闸也在这里落地——**不能写在 cron 行里**：cron.d 不做变量展开、
  # cron 也不继承容器 ENV（上面那三行注释就是为这个坑写的）。所以由 entrypoint
  # 在渲染时决定这一行进不进 crontab。
  #
  # 开关名 `KMFA_BOOT_SWEEP` 是历史遗留——那时压测在启动时一口气跑完。
  # 现在压测摊成节拍了，名字不再贴切，但它是**现存唯一、且已经被用过的压测开关**：
  # 2026-07-28 压测把线上打下线时就是用它止的血，Coolify 里那个 0 还在。
  # 换个新名字，那个 0 就变成「看着像总闸、其实不管用」的雷——
  # 下次谁想关压测，关了个寂寞。
  if [ "${KMFA_BOOT_SWEEP:-1}" = "1" ]; then
    grep -vE '^(SHELL|PATH)=' /opt/runtime/crontab.txt
  else
    echo "# 压测节拍已由 KMFA_BOOT_SWEEP=0 关闭（排程本身不受影响）"
    grep -vE '^(SHELL|PATH)=' /opt/runtime/crontab.txt | grep -v pick_stalest_skill
  fi
} > "$CRON_D"
chmod 0644 "$CRON_D"; chown root:root "$CRON_D"
# cron.d 硬性要求：文件名不含点（kmfa-skills 合规）、末尾必须有换行
if [ -n "$(tail -c1 "$CRON_D")" ]; then
  echo >> "$CRON_D"
fi
# 归档根必须存在且可写——否则考勤报告写不出去
mkdir -p "${KMFA_ATTENDANCE_ARCHIVE_ROOT:-/var/log/kmfa/dingtalk_attendance}"

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
# 冷启动先补一次项目成本：排程是每天 05:45，新容器起来后若干等到明天，
# 页面就会一直显示「还没产出」——对 Owner 而言等于没做。故启动即先算一次。
# 后台跑、失败只记日志：这一步绝不能挡住 cron 启动。
# 判据从「产物不在」改成「每次部署都算」。
# 原来是 `[ ! -s recent_completed.json ]`——产物一旦存在就再也不重算，于是新代码
# 部署上去，页面还在显示旧算法的旧结果，要等次日 05:45 才更新。
# Owner 2026-07-28：「项目成本是实时更新的」「不允许等待自然时间，那会浪费搁置很多时间」。
# 重算一次的代价是一次稀疏克隆＋一遍账簿，几分钟；显示一天旧数的代价是决策用错数。
if [ -f /opt/kmfa/secrets/kmfa_backup_deploy_key ]; then
  echo "$(date -Is) entrypoint: 冷启动重算项目成本（后台，每次部署都算）" >> /var/log/kmfa/cron.log
  ( /opt/runtime/run_skill.sh project-cost-refresh >> /var/log/kmfa/cron.log 2>&1 || true ) &
fi

# 冷启动重试当前失败的技能：修好的代码要等下一次排程才被跑到，而排程可能是一天后。
# Owner 2026-07-27：「你已经浪费了我一个月的时间都还没有修好考勤」——
# 「等明天那次排程」正是把一个月耗掉的那个模式。所以部署即重试，不等排程。
# 只重试台账里最近一次非 0 的技能；从未跑过的不动（那是排程问题不是失败）。
( 
  sleep 20
  L=/var/log/kmfa/ledger.jsonl
  [ -s "$L" ] || exit 0
  python3 - "$L" <<'PYR' | while read -r s; do
import json, sys
last = {}
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("skill"):
        last[r["skill"]] = r
for name, r in sorted(last.items()):
    if r.get("rc") not in (0, None):
        print(name)
PYR
    echo "$(date -Is) entrypoint: 冷启动重试失败技能 $s" >> /var/log/kmfa/cron.log
    /opt/runtime/run_skill.sh "$s" >> /var/log/kmfa/cron.log 2>&1 || true
  done

  # ── 压测摊开成节拍，不再一次性全跑 ───────────────────────────────────
  #
  # Owner 2026-07-28：「所有的 skill 你全部都要主动 手动 压力检查运行状态，
  # 不允许等待自然时间，那会浪费搁置很多时间」。
  #
  # 第一版做成「部署后一口气把 13 个技能全跑一遍」。**当天把线上打下线三次**，
  # 最长一次 5.5 分钟，恢复后又掉；私有库台账证实掉线期间压测正在跑。
  # 加 nice -n 19、把间隔从 5s 拉到 20s **都不够**——所以不是调参能解决的，
  # 是形状不对：这台机器 3.7GB，而压测里 project-cost-refresh 要克隆私有库
  # 解析上千张表、self-audit 要 tar 整个仓。
  #
  # 关键在于：**单跑一个技能是正常负载**，排程本来天天就在这么跑；
  # 出问题的是「13 个背靠背」这个突发。所以压测挪进 crontab，每跳只挑一个
  # 最久没跑的（见 KMFA/tools/pick_stalest_skill.py），摊开到一天里。
  # 从没跑过的几小时内就会被碰到，而不是永远轮不到——「不等自然时间」仍然成立，
  # 只是不再用突发去换。启动时这里什么都不做。


  # 冷启动补齐「别的技能依赖、但产物还不在」的前置技能。
  #
  # 为什么不是「没跑过的都补跑一遍」：经营月报那种一跑就可能发出东西的，
  # 绝不该因为一次部署被触发。所以判据是**产物在不在**，不是**跑没跑过**。
  #
  # 实测踩到的那条链（2026-07-27）：
  #   dws-bootstrap-groups 排在周日 10:30，加进排程后一直没轮到（运行次数 0）
  #     → 没有候选群清单 → 驾驶舱无群可勾 → 没有 target_groups.yaml
  #     → upstream-archive 每天 exit 4。
  #   一个周任务，把一个日任务卡了整整一周，而失败看起来像是归档自己的毛病。
  # 变量名只能用 ASCII——bash 的 read/for 不接受中文标识符，而 `bash -n` 查不出来
  # （报错发生在运行时）。真跑一遍才抓到，语法检查会放行。
  # 「产物在不在」还不够——**空产物和没有产物一样没用，但它长得像有**。
  # 实测（2026-07-28）：candidate_groups.json 存在且非空，内容却是 `"群数": 0`。
  # 于是 `[ ! -s ]` 判定"前置已就绪"，自举从此再也不会被补跑，
  # 而它排在周日 10:30，等于每周只有一次机会翻身；归档则每天红一次。
  # 这里把"零群的候选清单"当成没有：删掉它，让下面的补跑逻辑正常接手，
  # 自举于是走 run_skill.sh 跑（登记进台账 + 带失败码 + 回传私有库取证）。
  CAND_JSON=/var/log/kmfa/dws/candidate_groups.json
  if [ -s "$CAND_JSON" ] && ! python3 -c "
import json, sys
try:
    d = json.load(open('$CAND_JSON', encoding='utf-8'))
except Exception:
    sys.exit(1)
sys.exit(0 if (d.get('群数') or 0) > 0 else 1)
" 2>/dev/null; then
    echo "$(date -Is) entrypoint: 候选群清单为零群/不可解析 → 视为缺产物，删除以触发补跑" >> /var/log/kmfa/cron.log
    rm -f "$CAND_JSON"
  fi

  while IFS='|' read -r ARTIFACT SKILL_NAME; do
    [ -n "$SKILL_NAME" ] || continue
    if [ ! -s "$ARTIFACT" ]; then
      echo "$(date -Is) entrypoint: 缺前置产物 $ARTIFACT → 冷启动补跑 $SKILL_NAME" >> /var/log/kmfa/cron.log
      /opt/runtime/run_skill.sh "$SKILL_NAME" >> /var/log/kmfa/cron.log 2>&1 || true
    fi
  done <<'PREREQ'
/var/log/kmfa/dws/candidate_groups.json|dws-bootstrap-groups
/var/log/kmfa/attendance-runtime/notification_targets_resolved.json|attendance-bootstrap-targets
PREREQ
) &

echo "$(date -Is) entrypoint: cron 启动（TZ=$TZ，KMFA_DELIVERY_ENABLED=${KMFA_DELIVERY_ENABLED:-0}）" >> /var/log/kmfa/cron.log
exec cron -f
