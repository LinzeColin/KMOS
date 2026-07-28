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
  # 源文件自带的 SHELL/PATH 去掉，避免与上面重复
  grep -vE '^(SHELL|PATH)=' /opt/runtime/crontab.txt
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

  # ── 全量压测：一次部署把**每个**技能都跑一遍 ───────────────────────────
  # Owner 2026-07-28：「所有的 skill 你全部都要主动 手动 压力检查运行状态，
  # 不允许等待自然时间，那会浪费搁置很多时间」。
  #
  # 上面那段只重试**最近一次失败**的，而这远远不够：
  #   · 从未跑过的（mgmt-monthly 运行次数 0）永远轮不到，因为它「没失败过」；
  #   · 上一次侥幸成功、这次代码改动可能弄坏的，也轮不到；
  #   · 周任务／月任务要等一周一月才知道死活。
  # 结果就是「改一版等一天」，而那正是把一个月耗掉的模式。
  #
  # 默认开（`KMFA_BOOT_SWEEP=0` 可关）。串行跑：并发会让几个技能同时抢 dws 登录态
  # 和稀疏克隆，把「压测」变成「制造假故障」。
  #
  # 让路给 App：2026-07-28 首次全量压测跑到一半，线上 kmfa.linzezhang.com 连续
  # 503「no available server」约 3 分钟才恢复（Coolify 侧同期报 running:healthy，
  # 也没有部署在进行中，所以不是重新部署造成的）。这台是 3.7GB 的机器，
  # 而压测里 project-cost-refresh 要克隆私有库再解析上千张表、self-audit 要 tar 整个仓，
  # 跟 App 抢资源。**因果是从时间相关性推的，没有当场的内存/CPU 度量**，
  # 所以这里用的是两种成因都能缓解的保守做法：nice 让 App 赢 CPU，
  # 间隔从 5s 拉到 20s 给内存回收留窗口。压测是后台活，慢几分钟无所谓；
  # 为了压测把 Owner 的页面打下线，那是本末倒置。
  # 冷却闸：容器每重启一次 entrypoint 就跑一次，压测又是这里最重的一段——
  # 2026-07-28 首轮压测后当场观察到的：19:28 扫过一轮，19:44 又从头扫了一轮
  # （attendance-bootstrap-targets 运行次数 2→3、upstream-archive 56→57），
  # 说明容器在压测期间重启了，而重启又触发下一轮压测。这条链会自我维持，
  # 且每轮都在字母序靠后的技能之前断掉——work-check 两条因此**一次都没被扫到**，
  # 表现却只是「它俩时间戳还是 cron 时间」，极难看出是压测从没走到那里。
  # 冷却窗口内直接跳过：压测的价值是「部署后确认每个技能还能跑」，
  # 一小时内重复扫十遍并不会多确认什么，只会把机器压垮。
  SWEEP_STAMP=/var/log/kmfa/.last_boot_sweep
  SWEEP_COOLDOWN="${KMFA_BOOT_SWEEP_COOLDOWN_SECONDS:-3600}"
  if [ "${KMFA_BOOT_SWEEP:-1}" = "1" ] && [ -f "$SWEEP_STAMP" ] \
     && [ "$(( $(date +%s) - $(cat "$SWEEP_STAMP" 2>/dev/null || echo 0) ))" -lt "$SWEEP_COOLDOWN" ]; then
    echo "$(date -Is) entrypoint: 距上轮全量压测不足 ${SWEEP_COOLDOWN}s，本次跳过（防重启压测环）" \
      >> /var/log/kmfa/cron.log
  elif [ "${KMFA_BOOT_SWEEP:-1}" = "1" ]; then
    date +%s > "$SWEEP_STAMP"
    echo "$(date -Is) entrypoint: 全量压测开始（每个技能跑一遍）" >> /var/log/kmfa/cron.log
    SWEPT=0
    # 技能名从 `run_skill.sh` 的 case 分支取——**那才是技能清单的真源**，
    # 排程只是「什么时候跑」，不是「有哪些技能」。
    #
    # 2026-07-28 真跑提取逻辑抓到的：只看 crontab 会漏掉
    # `attendance-bootstrap-targets`（它不在排程里，只由上面那段前置补跑触发），
    # 排程 12 个而台账 13 个。写死清单同样不行——新增技能被漏掉的表现是
    # 「它一直没跑」，跟排程没配一模一样，极难查。
    # case 分支允许 `a|b)` 合并写法（work-check 两条共用同一段守卫），
    # 所以抽取要认 `|` 再拆开。不认的话表现是「那两个技能一直没跑」，
    # 跟排程没配一模一样、极难查——2026-07-28 合并 work-check 时被这条的测试当场抓住。
    #
    # 顺序按「最久没跑」而不是字母序。字母序下 work-check 两条永远排最后，
    # 压测一被打断就固定饿死同一批——2026-07-28 实测两轮压测都没走到它们，
    # 而表现只是「时间戳还停在 cron 时间」，看不出是压测从没到达。
    # 最久没跑优先：从没跑过的（mgmt-monthly 曾经运行次数 0）排最前，
    # 每次中断都由下一轮自动补上，不会有固定的尾巴长期没人碰。
    # 台账读不动就退回字母序——排序只是优化，绝不能因为它丢覆盖。
    SWEEP_ORDER="$(grep -oE '^  [a-z0-9|-]+\)' /opt/runtime/run_skill.sh \
                   | tr -d ' )' | tr '|' '\n' | sort -u \
                   | python3 -c '
import json, os, sys
names = [n.strip() for n in sys.stdin if n.strip()]
last = {}
try:
    with open("/var/log/kmfa/ledger.jsonl", encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("skill") in names and row.get("ts"):
                last[row["skill"]] = max(last.get(row["skill"], ""), str(row["ts"]))
except OSError:
    pass
print("\n".join(sorted(names, key=lambda n: (last.get(n, ""), n))))
' 2>/dev/null)"
    [ -n "$SWEEP_ORDER" ] || SWEEP_ORDER="$(grep -oE '^  [a-z0-9|-]+\)' /opt/runtime/run_skill.sh \
                                            | tr -d ' )' | tr '|' '\n' | sort -u)"
    for SK in $SWEEP_ORDER; do
      echo "$(date -Is) entrypoint: 压测 $SK" >> /var/log/kmfa/cron.log
      # 给压测跑打标：它和排程跑问的是两个问题——排程问「今天这件事办成没有」，
      # 压测问「这个技能的机器还转不转」。不打标就会互相污染：时间锚定的技能
      # 被拉到窗口外跑必然合法失败（19:44 跑早班实时提醒），
      # 那条会把当天真成功的排程结论顶红。
      KMFA_SWEEP_RUN=1 nice -n 19 /opt/runtime/run_skill.sh "$SK" >> /var/log/kmfa/cron.log 2>&1 || true
      SWEPT=$((SWEPT + 1))
      sleep 20
    done
    echo "$(date -Is) entrypoint: 全量压测结束，共 $SWEPT 个技能" >> /var/log/kmfa/cron.log
  fi

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
