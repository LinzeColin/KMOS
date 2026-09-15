#!/bin/bash
# automation-2 的**唯一**一条命令：看门狗 + 生产部周报，最后打一行 ACTION。
#
# 为什么合成一条：调度侧跑的是 SCNet 那个小模型。让它对着两条命令、两张十几行的
# 标记表做判读，等于把业务判断交给一个判不了的东西。判读全部在这里做完，
# automation 的 prompt 只剩「跑这条命令 → 把最后那行 ACTION 抄到第一行」。
set -uo pipefail
if [ -z "${HOME:-}" ]; then
  echo "CONFIG_MISSING | HOME 未设置，定位不到 venv 与配置文件" >&2
  echo "ACTION: ESCALATE" >&2; exit 2
fi
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KMFA_BRIEF_VENV:-$HOME/.local/share/kmfa-attendance-brief/venv}"
ENVF="$SKILL/private_runtime/kmfa_brief.env"
[ -f "$ENVF" ]            || { echo "CONFIG_MISSING | 缺少 $ENVF" >&2; echo "ACTION: ESCALATE" >&2; exit 2; }
[ -x "$VENV/bin/python" ] || { echo "VENV_MISSING | 缺少 $VENV" >&2;  echo "ACTION: ESCALATE" >&2; exit 2; }

worst() {   # 取更严重的那一个：ESCALATE > ACT > NONE
  case "$1|$2" in
    *ESCALATE*) echo ESCALATE ;;
    *ACT*)      echo ACT ;;
    *)          echo NONE ;;
  esac
}

# ── ① 看门狗 ───────────────────────────────────────────────
# 故意用系统 python3，不用主线那个 venv：venv 烂掉恰恰是要被报出来的故障之一。
echo "=== 看门狗 ===" >&2
WD_OUT="$(PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
          LANG=zh_CN.UTF-8 /usr/bin/python3 "$SKILL/scripts/kmfa_brief_watchdog.py" 2>&1)"
echo "$WD_OUT" >&2
case "$WD_OUT" in
  *WATCHDOG_ALERT*) A1=ESCALATE ;;
  *WATCHDOG_OK*|*WATCHDOG_KNOWN*) A1=NONE ;;
  *) A1=ESCALATE ;;              # 一个标记都没有 = 不知道发生了什么
esac

# ── ② 周报 ────────────────────────────────────────────────
# 硬墙钟在进程外。共享盘挂起时进程会卡在 open() 进不可中断 IO，
# 里面任何协作式超时都轮不到；实测正常一次 smb_ready 都能卡 3 分 44 秒。
set -a; . "$ENVF"; set +a
export KMFA_RUN_SLOT=morning
echo "=== 生产部周报 ===" >&2
HARD="${KMFA_BRIEF_HARD_TIMEOUT:-900}"
ERRF="$(mktemp -t kmfa_weekly_err)"
trap 'rm -f "$ERRF"' EXIT
"$VENV/bin/python" "$SKILL/scripts/run_attendance_weekly.py" 2>"$ERRF" &
child=$!
waited=0
while kill -0 "$child" 2>/dev/null && [ "$waited" -lt "$HARD" ]; do
  sleep 5; waited=$(( waited + 5 ))
done
if kill -0 "$child" 2>/dev/null; then
  kill -9 "$child" 2>/dev/null
  cat "$ERRF" >&2
  echo "ABORTED_TIMEOUT | 硬墙钟 ${HARD} 秒到了，进程还卡着（多半是共享盘挂起）" >&2
  DWSBIN="${KMFA_BRIEF_DWS:-$HOME/.local/bin/dws}"
  if [ -x "$DWSBIN" ] && [ -n "${KMFA_BRIEF_NOTIFY_USER:-}" ]; then
    "$DWSBIN" chat message send --user "$KMFA_BRIEF_NOTIFY_USER" \
      --title "⚠ 生产部周报故障 · ABORTED_TIMEOUT" \
      --text "生产部周报卡死了 ${HARD} 秒，已强制中止。常见原因是共享盘挂起。下一个工作日上午会再试。" \
      >/dev/null 2>&1 || true
  fi
  A2=ESCALATE; rc=1
else
  wait "$child"; rc=$?
  cat "$ERRF" >&2
  # run_attendance_weekly.py 在 finally 里把 `ACTION: X` 打进自己的 stderr。
  # 直接从这一轮的 stderr 里取，不去读运行日志 —— 那个日志是日报和周报共用的，
  # 去那里 grep 会把日报昨晚那一行当成本轮结论。
  A2="$(grep -o 'ACTION: [A-Z]*' "$ERRF" | tail -1 | sed 's/ACTION: //')"
  [ -z "$A2" ] && A2=ESCALATE     # 没打 ACTION = 没跑到收尾
fi

FINAL="$(worst "$A1" "$A2")"
echo "看门狗=$A1 周报=$A2 退出码=$rc" >&2
echo "ACTION: $FINAL" >&2
[ "$FINAL" = "ESCALATE" ] && exit 1
exit 0
