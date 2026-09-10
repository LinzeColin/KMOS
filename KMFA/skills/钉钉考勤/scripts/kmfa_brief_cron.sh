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
# 配了两条 automation（19:15 与 20:15）来免疫悉尼夏令时：
# 一年里只有一条落在北京 17:15，另一条会被已发标记挡掉。
SLOT1_H="${KMFA_BRIEF_SLOT_HOUR:-19}"; SLOT2_H="${KMFA_BRIEF_SLOT_HOUR2:-20}"
SLOT_M="${KMFA_BRIEF_SLOT_MIN:-15}"
NOW=$(( 10#$(date +%H) * 60 + 10#$(date +%M) ))
near_slot=0
for h in "$SLOT1_H" "$SLOT2_H"; do
  d=$(( NOW - (10#$h * 60 + 10#$SLOT_M) )); [ "$d" -lt 0 ] && d=$(( -d ))
  [ "$d" -le 15 ] && near_slot=1
done
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
exec "$VENV/bin/python" "$SKILL/scripts/run_attendance_brief.py" $FORCE
