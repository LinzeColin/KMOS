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

SKILL="/Users/linzezhang/Documents/Codex/GithubProject/KMOS/KMFA/skills/每日资金"
STATE="${DAILY_FUNDS_SMB_DIR:-/Volumes/share/03_资料库/MetaData/IDS_MetaData/60_受限资料/财务/每日资金看板}"
LOG="${STATE}/daily_funds_run.log"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export LANG=zh_CN.UTF-8

# 变量紧邻中文一律写 ${VAR}：bash 会把后面的高位字节当成变量名，
# 实测 "$TODAY_CN）已发过" 会报 unbound variable，而且只在走到那条分支时才炸。
log() { echo "[$(date '+%F %T %Z')] $*" >> "${LOG}"; }

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
KMROOT="/Users/linzezhang/Documents/Codex/GithubProject/KMOS"

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
  # 直接把输出追加进日志，**不走管道**：
  #   · 实时可见，十几分钟不再是一片空白；
  #   · $! 拿到的是 python 自己的 pid。用管道的话 $! 是 tee 的 pid，
  #     杀它只会让 python 收到 SIGPIPE 而不是 SIGTERM，而 skill 明确要求
  #     用 SIGTERM 让它写完当前 manifest 窗口，粗暴中断会写坏 manifest。
  # 判断「有没有被锁挡住」靠记下起始字节偏移，事后只读本轮新增那一段。
  local mark=0
  [ -f "${LOG}" ] && mark=$(wc -c < "${LOG}" | tr -d ' ')
  python3 "scripts/${script}" "$@" >> "${LOG}" 2>&1 &
  local pid=$! waited=0 rc=0
  while kill -0 "${pid}" 2>/dev/null; do
    if [ "${waited}" -ge "${ARCHIVE_BUDGET_SEC}" ]; then
      # 按 skill 的要求用 SIGTERM，让它写完当前 manifest 窗口再退。
      # 绝不 kill -9：那会写坏 manifest。
      log "${name} 超过 ${ARCHIVE_BUDGET_SEC}s 预算，发 TERM 让它收尾，本轮不等了"
      kill -TERM "${pid}" 2>/dev/null
      sleep 20
      kill -0 "${pid}" 2>/dev/null && log "${name} 收尾中，留它在后台跑完"
      rc=124
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done
  [ "${rc}" -eq 0 ] && { wait "${pid}"; rc=$?; }
  if tail -c "+$((mark + 1))" "${LOG}" 2>/dev/null | grep -q "另一个 pipeline 实例仍在运行"; then
    log "${name} 被锁挡住，本次没有拉到新数据"
  elif [ "${rc}" -eq 124 ]; then
    : # 超预算，上面已经记过了
  elif [ "${rc}" -eq 0 ]; then
    log "${name} 完成"
  else
    log "${name} 失败（退出码 ${rc}），继续"
  fi
}

archive_scan "KMFile 付款请示群" "${KMROOT}/KMFile/skills/KMFile-Archive" \
             kmfile_pipeline.py  /private/tmp/kmfile_work \
             scan --only-group 付款请示群 --since-manifest --window-days 1
archive_scan "KMMedia 付款请示群" "${KMROOT}/KMVideo/skills/KMMedia-Archive" \
             kmvideo_pipeline.py /private/tmp/kmvideo_work \
             scan --only-group 付款请示群 --since-manifest --media-type photo

cd "${SKILL}" || { log "进不去 skill 目录"; exit 1; }

# 1) 把新截图读成数字。拉不到不是致命错——SMB 上还有历史数据，
#    卡片会自己标出滞后天数，比什么都不发强。
if ! python3 scripts/run_local_daily_funds.py poll >> "${LOG}" 2>&1; then
  log "poll 失败，继续用已有数据出图"
fi

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
if python3 scripts/run_local_daily_funds.py send --to-group >> "${LOG}" 2>&1; then
  : > "${STAMP}"
  find "${STATE}" -maxdepth 1 -name '.sent-*' -mtime +10 -delete 2>/dev/null
  log "已发送"
  echo "已发送（图 + 文字）到付款请示群"
else
  log "发送失败，详见 ${LOG}"
  echo "发送失败，详见 ${LOG}" >&2
  exit 2
fi
