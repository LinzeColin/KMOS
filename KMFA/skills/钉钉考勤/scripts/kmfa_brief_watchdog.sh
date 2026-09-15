#!/bin/bash
# Codex automation kmfa-attendance-watchdog 就调这一条。
# 主线那两条 automation 停摆时它自己报不了 —— 只能由另一条任务来看。
set -uo pipefail
if [ -z "${HOME:-}" ]; then
  echo "WATCHDOG_ALERT problem=no_home detail=HOME 未设置" >&2; exit 2
fi
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LANG=zh_CN.UTF-8
# 故意用系统 python3，不用主线那个 venv：venv 烂掉恰恰是要被报出来的故障之一，
# 看门狗不能跟它同生共死。脚本本身只用标准库。
exec /usr/bin/python3 "$SKILL/scripts/kmfa_brief_watchdog.py"
