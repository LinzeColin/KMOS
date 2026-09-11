#!/bin/bash
# 每日资金看门狗：由 Codex automation kmfa-daily-funds-watchdog 每个工作日上午调用。
# 主任务停摆（被暂停、被删、没被触发）时它自己报不了，只能由另一条任务来看。
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export LANG=zh_CN.UTF-8
cd "${SKILL}" || { echo "进不去 skill 目录" >&2; exit 1; }
exec python3 scripts/run_local_daily_funds.py watchdog
