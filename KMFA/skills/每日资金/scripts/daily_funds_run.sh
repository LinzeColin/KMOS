#!/bin/bash
# 每日资金卡片：拉钉钉新截图 → 读成数字 → 出图 → 发付款请示群。
# 一条命令跑完整条链路，所以只需要设一个 session cron。
#
# 由 Codex automation（~/.codex/automations/kmfa-daily-funds）调用，
# 本机不装系统级 cron。
#
# 状态全在 SMB，本机不留持久文件：
#   数据      <SMB>/60_受限资料/财务/每日资金看板/daily_funds.jsonl
#   运行日志  同目录 daily_funds_run.log
#   当日标记  同目录 .sent-YYYY-MM-DD
# 不放 KMVideo/付款请示群/：那是归档 skill 管理并会 audit 的项目群目录。
# 唯一留在本机的是 ~/.kmfa_daily_funds.env（179 字节的密钥，不该放共享盘）。
#
# 出图确实要落一个临时 PNG，跑完就删——渲染不可能不落盘。
set -uo pipefail

# 运行位是 ~/.codex/skills/KMFA-Daily-Funds/，仓库里这份是源。
# 路径按脚本自身位置推算，整包搬到哪都不用改一行——主工作树按规矩只 pull 不写，
# 放在那里跑的生产代码会被恢复原状（2026-09-10 实测被清过一次）。
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${DAILY_FUNDS_SMB_DIR:-/Volumes/share/03_资料库/MetaData/IDS_MetaData/60_受限资料/财务/每日资金看板}"
LOG="${STATE}/daily_funds_run.log"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export LANG=zh_CN.UTF-8

# 变量紧邻中文一律写 ${VAR}：bash 会把后面的高位字节当成变量名，
# 实测 "$TODAY_CN）已发过" 会报 unbound variable，而且只在走到那条分支时才炸。
TMPROOT="${DAILY_FUNDS_TMP_DIR:-/private/tmp}"

# SMB 上的直接重定向会静默产生全零文件。所有持久状态均在本地暂存，
# 再通过 rsync --inplace 写入并以 cmp 读回确认。
publish_smb_file() {
  local source="$1" target="$2"
  /usr/bin/rsync -a --inplace -- "${source}" "${target}" && cmp -s "${source}" "${target}"
}

append_log_file() {
  local source="$1" staged
  staged=$(mktemp "${TMPROOT%/}/daily-funds-log.XXXXXX") || return 1
  if [ -f "${LOG}" ] && ! /bin/cp "${LOG}" "${staged}"; then
    rm -f "${staged}"
    return 1
  fi
  cat "${source}" >> "${staged}"
  if ! publish_smb_file "${staged}" "${LOG}"; then
    rm -f "${staged}"
    return 1
  fi
  rm -f "${staged}"
}

log() {
  local line rc
  line=$(mktemp "${TMPROOT%/}/daily-funds-line.XXXXXX") || return 1
  printf '[%s] %s\n' "$(date '+%F %T %Z')" "$*" > "${line}"
  append_log_file "${line}"
  rc=$?
  rm -f "${line}"
  return "${rc}"
}

# 失败告警只发张霖泽个人，永远不进群——群里不加噪音。
# 走 notify.send_failure，它自带重试和「dws 退出码恒为 0，错误在返回体里」的处理。
alert_owner() {
  python3 -c 'import sys; sys.path.insert(0, "'"${SKILL}"'"); from daily_funds_local import notify; notify.send_failure(sys.argv[1])' "$*" >/dev/null 2>&1 \
    || log "告警发送失败（原文：$*）"
}

if [ ! -d "${STATE}" ]; then
  echo "SMB 不可用: ${STATE}" >&2
  exit 1
fi

# 一天只发一条。补跑（休眠唤醒、机器重启、手动重试）不该变成刷屏。
TODAY_CN=$(TZ=Asia/Shanghai date +%F)
STAMP="${STATE}/.sent-${TODAY_CN}"
if [ -f "${STAMP}" ]; then
  log "今天（北京 ${TODAY_CN}）已发过，跳过"
  echo "今天已发过，跳过"
  exit 0
fi

# 仅用于无消息的恢复验证；automation 的既有调用不设置此变量。
if [ "${DAILY_FUNDS_DRY_RUN:-0}" = "1" ]; then
  log "dry run：未拉取素材、未发送、未写当日标记"
  echo "NOT_SENT_DRY_RUN"
  exit 0
fi

# 太早就不发 —— 但只在「今天还有更晚的一次触发」时才跳过。
#
# 为什么要读配置而不是写死：automation.toml 会被 Codex 应用反复覆盖（实测多次），
# 所以正确性不能押在配置上，只能押在「读当下真正生效的那份」。
#
# 规则：BYHOUR 走本机时区（悉尼），北京 = 悉尼 − 偏移。
#   · 现在换算到北京 ≥12 点 → 照常发。
#   · 现在太早，但今天还排了一次能落在北京 ≥12 点的触发 → 跳过且不写标记，等那次。
#   · 现在太早，且今天没有更晚的触发了 → 照样发，只是早了点。
#     宁可早发一小时，也绝不能因为守卫而整天不发——那是静默停摆。
#
# 这样 10-04 悉尼转夏令时时无人干预：配置是双触发就等第二次，
# 是单触发就早发一小时并在日志里说明。
TOML="${HOME}/.codex/automations/kmfa-daily-funds/automation.toml"
DECIDE=$(BJ_NOW="$(TZ=Asia/Shanghai date +%H)" SYD_NOW="$(date +%H)" TOML="${TOML}" python3 - <<'PYEOF'
import os, re
bj, syd = int(os.environ["BJ_NOW"]), int(os.environ["SYD_NOW"])
if bj >= 12:
    print("GO now"); raise SystemExit
offset = (syd - bj) % 24          # 悉尼比北京快几小时
hours = []
try:
    txt = open(os.environ["TOML"], encoding="utf-8").read()
    m = re.search(r'rrule\s*=\s*"([^"]*)"', txt)
    if m:
        h = re.search(r"BYHOUR=([0-9,]+)", m.group(1))
        if h: hours = [int(x) for x in h.group(1).split(",") if x.strip()]
except Exception:
    pass
# 今天还有哪次触发能落在北京 >=12 点
later = [h for h in hours if h > syd and (h - offset) % 24 >= 12]
print("WAIT %d" % min(later) if later else "GO late")
PYEOF
)
case "${DECIDE}" in
  "GO now") : ;;
  WAIT*)
    log "北京 $(TZ=Asia/Shanghai date +%H) 点太早，今天还排了悉尼 ${DECIDE#WAIT } 点那次，本轮不发也不写标记"
    echo "北京时间太早，等今天更晚的那次触发"
    exit 0 ;;
  *)
    log "北京 $(TZ=Asia/Shanghai date +%H) 点早于 12 点，但今天没有更晚的触发了，照发（宁可早发也不静默停摆）" ;;
esac

# 0) 先把「付款请示群」的新素材从钉钉拉到 SMB：文件在前，图片在后。
#
# 只拉「付款请示群」，只跑 scan 这一个阶段。
#
# 范围划分：全量归档（所有群、所有类型、完整流水线）是 kmfa-kmfile-daily 和
# kmfa-kmmedia-daily 两个专职 automation 的活，它们 03:00 / 03:30 已经在跑。
# 资金线只管自己这一个群——把全量塞进来等于重复干别人的活，还把卡片
# 压在一条耗时不可控的流水线后面。实测那样一轮要 20–40 分钟。
#
# 只跑 scan：资金卡片需要的全部东西就是「图片落盘 + manifest 更新」，都在 scan 里。
# 后面 probe/thumbs/dedup/label/rename/registry/upload/accept/report 九个阶段
# 是素材库的活，对这里没用，却是九个额外的失败点——实测 2026-09-05
# thumbs 阶段 `size mismatch` 崩过，整条流水线停在那。
#
# --since-manifest 是日增量入口，不带它会从 2025-01-01 全量回填，
# 文档明确写着回填不许进调度。
# --window-days 只有 kmfile_pipeline 有，kmvideo_pipeline 没有这个参数，
# 照 SKILL.md 给 kmvideo 传会直接报错。
export KMOS_ROOT="/Users/linzezhang/Documents/Codex/GithubProject/KMOS"
KMROOT="${DAILY_FUNDS_KMROOT:-/Users/linzezhang/Documents/Codex/GithubProject/KMOS}"

# 每条归档线的时间预算。超了就放手去出卡片，归档留在后台自己跑完。
# 单群 scan 实测 1–2 分钟，给 240s 已经是三倍余量；跑不完说明被锁着干等
# 或者出了别的问题，那更不该拖着卡片。整轮上界因此是 8 分钟出头。
ARCHIVE_BUDGET_SEC="${ARCHIVE_BUDGET_SEC:-240}"

# 先文件后媒体。两个都只跑 scan、只跑这一个群、都是尽力而为：
# 拉不到新东西不是致命错——SMB 上还有历史数据，卡片会自己标出滞后天数，
# 比什么都不发强。
# pipeline 用 pid 锁防并发写 manifest。两个真实缺陷叠在一起会让归档永久静默停摆：
#   ① 运行被中断（休眠、退应用、kill）时锁文件留在原地，持有者已经不存在；
#   ② 被锁挡住时 pipeline **退出码是 0**，调用方会把它当成功。
# 结果：一次中断之后，此后每次 scan 都秒退并报告「完成」，新数据再也进不来，
# 卡片一直发旧图，而且没有任何报错。所以扫之前先收掉确认已死的锁。
reap_stale_lock() {
  local root="$1" f pid
  for f in $(find "${root}" -name ".pipeline.lock" 2>/dev/null); do
    pid=$(awk '{print $1}' "${f}" 2>/dev/null)
    case "${pid}" in
      ''|*[!0-9]*) log "锁文件内容异常，收掉：${f}"; rm -f "${f}"; continue ;;
    esac
    if kill -0 "${pid}" 2>/dev/null; then
      log "锁被 pid ${pid} 真实持有，等它：${f}"
    else
      log "收掉陈旧锁（持有者 pid ${pid} 已不存在）：${f}"
      rm -f "${f}"
    fi
  done
}

archive_scan() {
  local name="$1" dir="$2" script="$3" work="$4"
  shift 4
  if [ ! -d "${dir}" ]; then
    log "找不到 ${name} skill，跳过：${dir}"
    return 0
  fi
  reap_stale_lock "${work}"
  cd "${dir}" || { log "${name} 目录进不去"; return 0; }

  # 阶段和范围全部由调用方传入，函数本身不假设任何范围。
  #
  # 但要给时间预算。归档是全量所有群，耗时不可控，还可能被别的 pipeline
  # 的活锁挡住干等。卡片才是交付物，不能被归档无限期扣着——超预算就放手，
  # 用 SMB 上已有的数据照常出图，卡片自己会标出滞后几天。
  #
  # 输出先落本地。SMB 只接受 rsync --inplace 加读回校验过的完整文件；$!
  # 仍然是 python 自己的 pid，因此 TERM 仍由 pipeline 正常收尾处理。
  local output
  output=$(mktemp "${TMPROOT%/}/daily-funds-archive.XXXXXX") || {
    log "无法创建 ${name} 本地输出暂存，跳过"
    return 0
  }
  python3 "scripts/${script}" "$@" >> "${output}" 2>&1 &
  local pid=$! waited=0 rc=0 finished=1
  while kill -0 "${pid}" 2>/dev/null; do
    if [ "${waited}" -ge "${ARCHIVE_BUDGET_SEC}" ]; then
      # 按 skill 的要求用 SIGTERM，让它写完当前 manifest 窗口再退。
      # 绝不 kill -9：那会写坏 manifest。
      log "${name} 超过 ${ARCHIVE_BUDGET_SEC}s 预算，发 TERM 让它收尾，本轮不等了"
      kill -TERM "${pid}" 2>/dev/null
      sleep 20
      if kill -0 "${pid}" 2>/dev/null; then
        log "${name} 收尾中，留它在后台跑完；输出暂存于本机"
        finished=0
      else
        wait "${pid}"
      fi
      rc=124
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done
  [ "${rc}" -eq 0 ] && { wait "${pid}"; rc=$?; }
  if [ "${finished}" -eq 1 ]; then
    append_log_file "${output}" || echo "无法安全写入归档输出日志" >&2
  fi
  # 归档没跑成 = 今天的素材可能不全 = 卡片的权威性没有保证。
  # 这三种情况都不拦发送（历史数据还在，卡片自带报表日），但**一条都不许静默**：
  # 素材缺失是无声的，只有告警能让人知道该去看一眼。
  if grep -q "另一个 pipeline 实例仍在运行" "${output}" 2>/dev/null; then
    log "${name} 被锁挡住，本次没有拉到新数据"
    alert_owner "每日资金：${name} 被另一个 pipeline 的锁挡住，本轮没拉到新素材，卡片可能滞后。"
  elif [ "${rc}" -eq 124 ]; then
    alert_owner "每日资金：${name} 超过 ${ARCHIVE_BUDGET_SEC}s 预算被中断，本轮素材可能不全。"
  elif [ "${rc}" -eq 0 ]; then
    log "${name} 完成"
  else
    log "${name} 失败（退出码 ${rc}），继续"
    alert_owner "每日资金：${name} 归档失败（退出码 ${rc}），本轮素材可能不全。查 ${LOG}"
  fi
  [ "${finished}" -eq 1 ] && rm -f "${output}"
}

# 主体任务之前先归档本群素材，确保读数用的是当天最全的一份。
#
# window-days 取 4，不是 1：BYDAY 只排周一到周五，周五那轮到周一那轮之间隔 3 天。
# 窗口只有 1 天时，财务在周六发的余额表对周一这轮是不可见的——直接漏一天。
# 4 天 = 周五→周一的 3 天，再留 1 天冗余给「某一轮没触发」。
# 实测代价：窗口 1 约 57s，窗口 4 约 137s，都在 240s 预算内。
# 长假（国庆/春节）超出 4 天的缺口由 STALE_ALERT_DAYS 兜底告警，人工 backfill 补。
archive_scan "KMFile 付款请示群" "${KMROOT}/KMFile/skills/KMFile-Archive" \
             kmfile_pipeline.py  /private/tmp/kmfile_work \
             scan --only-group 付款请示群 --since-manifest --window-days 4
archive_scan "KMMedia 付款请示群" "${KMROOT}/KMVideo/skills/KMMedia-Archive" \
             kmvideo_pipeline.py /private/tmp/kmvideo_work \
             scan --only-group 付款请示群 --since-manifest --media-type photo

cd "${SKILL}" || { log "进不去 skill 目录"; exit 1; }

# 1) 把新截图读成数字。
#
# poll 的退出码分三档，处理方式完全不同，绝不能一视同仁：
#
#   0  正常跑完（含「上游今天还没发新表」）。今天没新表是常态，不是故障，
#      卡片自己会标滞后天数。
#   2  取到候选但一张都没入库（读图全失败 / 文件全不在盘上）。
#      数据没更新但代码是活的——照发历史数据，同时私聊告警。
#   其它（traceback 走 1）代码崩了。**一律拒发。**
#
# 这一档以前写的是「继续用已有数据出图」，代价实测过：2026-09-10
# smb_source.fetch 少一行 import hashlib，poll 崩在第一条候选上，
# 于是把 09-08 的数字当当天卡片发进了群，脚本还报「已发送」、
# automation 记「正常发送完成 ACTION: NONE」——一条告警都没有。
# 给管理层看错数字，比当天不发严重得多。
RUN_OUTPUT=$(mktemp "${TMPROOT%/}/daily-funds-run.XXXXXX") || {
  echo "无法创建本地运行输出暂存" >&2
  exit 2
}
POLL_RC=0
python3 scripts/run_local_daily_funds.py poll >> "${RUN_OUTPUT}" 2>&1 || POLL_RC=$?
append_log_file "${RUN_OUTPUT}" || true
rm -f "${RUN_OUTPUT}"

if [ "${POLL_RC}" -eq 0 ]; then
  :
elif [ "${POLL_RC}" -eq 2 ]; then
  log "poll 取到候选但一张都没入库，照发历史数据并告警"
  alert_owner "每日资金：poll 取到了新截图但一张都没读进库，今天的卡片用的是历史数据。查 ${LOG}"
else
  log "poll 崩溃（退出码 ${POLL_RC}），拒绝发送"
  alert_owner "每日资金：poll 崩溃（退出码 ${POLL_RC}），今天不发卡片，避免把旧数字当当天数据发进群。查 ${LOG}"
  echo "poll 崩溃（退出码 ${POLL_RC}），已拒发并私聊告警" >&2
  exit 2
fi

# 1.5)「现存票据」→ 卡片上的「14 天内到期承兑」。
#
# 这一步只影响卡片上的一个色块，所以处理方式和 poll 不同：
#   0 / 2  正常，或本轮读图没过校验——表在有效期内，下一轮再试。卡片用最近一张
#          合格的表按报表日滚动；太旧就不画，并由 send 首报告警。数字不会错。
#   其它   崩溃。卡片照发（色块只用已经过闸门入库的表），但必须私聊告警。
BILLS_OUTPUT=$(mktemp "${TMPROOT%/}/daily-funds-bills.XXXXXX") || {
  echo "无法创建本地票据步骤输出暂存" >&2
  exit 2
}
BILLS_RC=0
python3 scripts/run_local_daily_funds.py bills >> "${BILLS_OUTPUT}" 2>&1 || BILLS_RC=$?
append_log_file "${BILLS_OUTPUT}" || true
rm -f "${BILLS_OUTPUT}"
case "${BILLS_RC}" in
  0|2) : ;;
  *)
    log "票据表步骤崩溃（退出码 ${BILLS_RC}），卡片照发，色块按已入库的合格表计算"
    alert_owner "每日资金：「现存票据」步骤崩溃（退出码 ${BILLS_RC}），卡片照发，14 天内到期承兑按已入库的合格表计算。查 ${LOG}" ;;
esac

# 2) 出图 + 发送到「付款请示群」。
#
# 发群这个开关在 notify.py 里是硬锁的，必须显式打开才放行——这里打开它，
# 依据是用户 2026-09-05 的明确授权：「这个cron直接发到群里去 进入下一个阶段」。
# 锁本身保留：任何别的调用方（手动跑、别的脚本、agent 乱试）默认仍然只能发单聊。
#
# 两条规矩不变：
#   · 失败通知永远只发张霖泽个人，不进群——群里不加噪音。
#   · 数据滞后 ≥3 天时拒绝进群，改成私聊告警（见 run_local_daily_funds.py 的
#     STALE_ALERT_DAYS）。不把过期数字摆到管理层面前。
# 发之前再查一次当日标记。
# 开头查过一次，但归档要跑几分钟，这期间另一轮（另一个触发时刻、或人手动跑）
# 可能已经发完并写下标记了。只在开头查会导致群里出现两条重复。
# 实测 2026-09-07：16:46 启动时无标记，16:49 另一轮发了，16:54 本轮才走到发送。
if [ -f "${STAMP}" ]; then
  log "归档期间已有另一轮发过了，本轮不重复发"
  echo "已有另一轮发送完成，本轮跳过"
  exit 0
fi

export DAILY_FUNDS_ALLOW_GROUP=1
SEND_OUTPUT=$(mktemp "${TMPROOT%/}/daily-funds-send.XXXXXX") || {
  echo "无法创建本地发送输出暂存" >&2
  exit 2
}
if python3 scripts/run_local_daily_funds.py send --to-group >> "${SEND_OUTPUT}" 2>&1; then
  append_log_file "${SEND_OUTPUT}" || true
  rm -f "${SEND_OUTPUT}"
  MARKER=$(mktemp "${TMPROOT%/}/daily-funds-marker.XXXXXX") || {
    echo "发送完成但无法创建幂等标记暂存" >&2
    exit 2
  }
  : > "${MARKER}"
  if ! publish_smb_file "${MARKER}" "${STAMP}"; then
    rm -f "${MARKER}"
    log "发送完成但幂等标记写入或读回失败"
    echo "发送完成但幂等标记写入失败" >&2
    exit 2
  fi
  rm -f "${MARKER}"
  log "已发送"
  echo "已发送（图 + 文字）到付款请示群"
else
  append_log_file "${SEND_OUTPUT}" || true
  rm -f "${SEND_OUTPUT}"
  log "发送失败，详见 ${LOG}"
  echo "发送失败，详见 ${LOG}" >&2
  exit 2
fi
