#!/bin/sh
# Load the container-start snapshot before executing an unattended job.
# Cron itself intentionally has no Coolify environment.  The snapshot lives
# only in the root-owned state volume and is generated with shell-escaped
# values by entrypoint.sh, so credentials never appear in /etc/cron.d.
set -eu

CRON_ENV_FILE="/var/lib/kmfa/daily-funds-state/cron.env"
if [ ! -r "$CRON_ENV_FILE" ]; then
  echo "DAILY_FUNDS_CRON_ENV_MISSING" >&2
  exit 70
fi

# shellcheck source=/var/lib/kmfa/daily-funds-state/cron.env
. "$CRON_ENV_FILE"
exec python3 /opt/daily-funds/scripts/run_daily_funds.py "$@"
