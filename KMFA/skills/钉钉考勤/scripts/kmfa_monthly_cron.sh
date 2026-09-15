#!/bin/bash
# 考勤累计（越线通知 + 周一月报）。automation-2 的第二条命令。
# 不传参数、不做判断：业务日、门槛、发送窗口、首报制全在脚本里。
set -uo pipefail
if [ -z "${HOME:-}" ]; then
  echo "CONFIG_MISSING | HOME 未设置，定位不到 venv 与配置文件" >&2; exit 2
fi
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KMFA_BRIEF_VENV:-$HOME/.local/share/kmfa-attendance-brief/venv}"
ENVF="$SKILL/private_runtime/kmfa_brief.env"
[ -f "$ENVF" ]           || { echo "CONFIG_MISSING | 缺少 $ENVF" >&2; exit 2; }
[ -x "$VENV/bin/python" ] || { echo "VENV_MISSING | 缺少 $VENV" >&2; exit 2; }
set -a; . "$ENVF"; set +a
export KMFA_RUN_SLOT=morning

# 硬墙钟在进程外。共享盘挂起时进程会卡在 open() 进不可中断 IO，
# 里面任何协作式超时都轮不到；实测正常一次 smb_ready 都能卡 3 分 44 秒。
HARD="${KMFA_BRIEF_HARD_TIMEOUT:-900}"
"$VENV/bin/python" "$SKILL/scripts/run_attendance_monthly.py" &
child=$!
waited=0
while kill -0 "$child" 2>/dev/null && [ "$waited" -lt "$HARD" ]; do
  sleep 5; waited=$(( waited + 5 ))
done
if kill -0 "$child" 2>/dev/null; then
  kill -9 "$child" 2>/dev/null
  echo "ABORTED_TIMEOUT | 硬墙钟 ${HARD} 秒到了，进程还卡着（多半是共享盘挂起）" >&2
  DWSBIN="${KMFA_BRIEF_DWS:-$HOME/.local/bin/dws}"
  if [ -x "$DWSBIN" ] && [ -n "${KMFA_BRIEF_NOTIFY_USER:-}" ]; then
    "$DWSBIN" chat message send --user "$KMFA_BRIEF_NOTIFY_USER" \
      --title "⚠ 考勤累计故障 · ABORTED_TIMEOUT" \
      --text "考勤累计卡死了 ${HARD} 秒，已强制中止。常见原因是共享盘挂起。下一个工作日上午会再试。" \
      >/dev/null 2>&1 || true
  fi
  exit 1
fi
wait "$child"
exit $?
