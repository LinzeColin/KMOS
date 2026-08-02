#!/bin/sh
set -eu
python3 /opt/daily-funds/scripts/run_daily_funds.py healthcheck >/dev/null

# ``procps`` costs a surprising amount on the small Coolify builder only to
# run ``pgrep`` here.  PID 1 records the cron child in a volatile runtime file;
# inspect its Linux proc name as well as signalability so a stale/reused PID
# cannot make a stopped scheduler look healthy.
CRON_PID_FILE="/run/daily-funds-cron.pid"
[ -r "$CRON_PID_FILE" ]
CRON_PID="$(cat "$CRON_PID_FILE")"
case "$CRON_PID" in
  ''|*[!0-9]*) exit 1 ;;
esac
[ -r "/proc/$CRON_PID/comm" ]
[ "$(cat "/proc/$CRON_PID/comm")" = "cron" ]
