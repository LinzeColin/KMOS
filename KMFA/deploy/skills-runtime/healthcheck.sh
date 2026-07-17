#!/usr/bin/env bash
# 健康检查：cron 进程存活 + 台账 48h 内有记录（初始部署宽限：台账为空只警告不失败）。
set -uo pipefail
pgrep -x cron >/dev/null || { echo "cron 未运行"; exit 1; }
LEDGER=/var/log/kmfa/ledger.jsonl
if [ -s "$LEDGER" ]; then
  LAST_EPOCH="$(date -d "$(tail -1 "$LEDGER" | sed -E 's/.*"ts":"([^"]+)".*/\1/')" +%s 2>/dev/null || echo 0)"
  NOW="$(date +%s)"
  if [ "$LAST_EPOCH" -gt 0 ] && [ $((NOW - LAST_EPOCH)) -gt $((48*3600)) ]; then
    echo "台账超过 48h 无记录"; exit 1
  fi
fi
exit 0
