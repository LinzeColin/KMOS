#!/bin/bash
# Codex automation 就调这一条。不传参数、不做判断、不读 prompt。
#
# 两种触发，靠「离计划钟点多远」自己分辨：
#   排程触发（计划钟点 ±15 分钟）—— 周末不跑、没到北京 17:15 出报时刻不跑。
#   人在 Codex 里点 Run（其它时刻）—— 带 --force，周末和截止线都不拦。
# 「今天这份已经发过了」是无条件的，--force 也不放行 —— 一个业务日只进群一次。
#
# 所有判读都认 stderr 里的固定标记（SEND_COMPLETED / SKIP_* / *_FAILED …），
# 不认中文措辞。中文只给人看，改文案不影响调度侧。
set -uo pipefail
# HOME 没设的话，下面那行默认 venv 路径里的 $HOME 会在 set -u 下直接把脚本打死，
# 而且是在任何标记输出之前 —— stderr 里只有一句 bash 报错，调度侧对不上任何标记，
# 手机上也没有告警。宁可自己响一声：CONFIG_MISSING 是结论性标记，会被判 ESCALATE。
if [ -z "${HOME:-}" ]; then
  echo "CONFIG_MISSING | HOME 未设置，定位不到 venv 与配置文件" >&2; exit 2
fi
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${KMFA_BRIEF_VENV:-$HOME/.local/share/kmfa-attendance-brief/venv}"
ENVF="$SKILL/private_runtime/kmfa_brief.env"

if [ ! -f "$ENVF" ]; then
  echo "CONFIG_MISSING | 缺少 $ENVF，先跑 scripts/setup_attendance_brief.sh" >&2; exit 2
fi
if [ ! -x "$VENV/bin/python" ]; then
  echo "VENV_MISSING | 缺少 $VENV，先跑 scripts/setup_attendance_brief.sh" >&2; exit 2
fi
set -a; . "$ENVF"; set +a

# 计划钟点（本机墙钟），跟 Codex automation 的 rrule 保持一致。
# 主 19:15,20:15 / 备位 20:15,21:15 —— 悉尼一年有夏令时而北京没有，
# 换算过去总有至少两个钟点落在北京 17:15 之后，剩下的会被已发标记挡掉。
SLOT_H="${KMFA_BRIEF_SLOT_HOURS:-19 20 21}"
SLOT_M="${KMFA_BRIEF_SLOT_MIN:-15}"
NOW=$(( 10#$(date +%H) * 60 + 10#$(date +%M) ))
near_slot=0
for h in $SLOT_H; do
  d=$(( NOW - (10#$h * 60 + 10#$SLOT_M) )); [ "$d" -lt 0 ] && d=$(( -d ))
  [ "$d" -le 15 ] && near_slot=1
done
# launchd 那条兜底触发器要自报家门。
# 「离钟点远 ⇒ 一定是人按的 Run ⇒ 给 --force」这个推断，只在「Codex 是唯一触发者」
# 时成立。机器睡过了钟点，launchd 醒来会把错过的那一枪补上，补到北京 23 点也照样
# 离钟点很远 —— 按旧推断它会拿到 --force，绕开周末闸和出报时刻闸，把简报发进群。
# 所以触发者显式声明自己是谁，不再靠时钟去猜。
[ "${KMFA_BRIEF_TRIGGER:-}" = "launchd" ] && near_slot=1
# 不要用数组。macOS 自带 bash 3.2，在 set -u 下展开空数组 "${ARGS[@]}" 会被判成
# 未绑定变量直接退出（bash 4.4+ 才修）。而空数组恰恰是排程触发那条路径 ——
# 2026-09-07 18:07 第一次真实触发就栽在这里：脚本第 42 行崩掉，
# run_attendance_brief.py 一次都没被执行到，运行日志里连 RUN_START 都没有。
# 用普通字符串：要么是空串，要么是 --force，不带引号展开，两种都安全。
FORCE=""
[ "$near_slot" -eq 0 ] && FORCE="--force"

export KMFA_RUN_SLOT=evening
# 这一位是「本轮由调度器触发」的凭据，只有本文件会置。
# 手工在终端直接跑 run_attendance_brief.py 时它是空的，于是只出报不发送。
export KMFA_BRIEF_SCHEDULED=1

# 硬墙钟，由本进程执行，不由被监控的那个进程自己执行。
#
# python 里那个 Deadline 是「两个阶段之间检查一下还剩多少秒」——它要求进程还在跑。
# 共享盘挂起时进程卡在 open() 里进 U 态（不可中断），Deadline 一次都轮不到，
# 信号也送不进去。2026-09-15 实测：一次正常的 SKIP_BEFORE_PUBLISH 在 smb_ready
# 里卡了 3 分 44 秒才出来 —— 盘是活的，只是慢。真挂起时就是无限期，
# 而且卡在第一个标记之前：群里没简报，日志里没有一行，手机上没有告警。
#
# 所以超时判定必须在进程外面。900 秒远高于正常全程（实测约 90 秒），
# 也高于内部预算之和，正常情况永远轮不到它；轮到了就是真出事了。
HARD="${KMFA_BRIEF_HARD_TIMEOUT:-900}"
"$VENV/bin/python" "$SKILL/scripts/run_attendance_brief.py" $FORCE &
child=$!
waited=0
while kill -0 "$child" 2>/dev/null && [ "$waited" -lt "$HARD" ]; do
  sleep 5; waited=$(( waited + 5 ))
done
if kill -0 "$child" 2>/dev/null; then
  kill -9 "$child" 2>/dev/null
  echo "ABORTED_TIMEOUT | 硬墙钟 ${HARD} 秒到了，进程还卡着（多半是共享盘挂起），今天这份没发出去" >&2
  # 告警得由本脚本发：那个 python 已经卡死，它自己的告警代码执行不到。
  DWSBIN="${KMFA_BRIEF_DWS:-$HOME/.local/bin/dws}"
  if [ -x "$DWSBIN" ] && [ -n "${KMFA_BRIEF_NOTIFY_USER:-}" ]; then
    "$DWSBIN" chat message send --user "$KMFA_BRIEF_NOTIFY_USER" \
      --title "⚠ 考勤简报故障 · ABORTED_TIMEOUT" \
      --text "考勤简报卡死了 ${HARD} 秒，已强制中止，今天这份没发出去。常见原因是共享盘挂起（进程进不可中断 IO）。下一个触发点会再试一次。" \
      >/dev/null 2>&1 || true
  fi
  exit 1
fi
wait "$child"
exit $?
