#!/bin/sh
set -eu
python3 /opt/daily-funds/scripts/run_daily_funds.py healthcheck >/dev/null
pgrep -x cron >/dev/null
