#!/bin/sh
set -eu

if [ "$(date +%z)" != "+0800" ]; then
  echo "DAILY_FUNDS_TIMEZONE_INVALID"
  exit 1
fi

mkdir -p /var/log/daily-funds \
  "${DAILY_FUNDS_STATE_DIR:-/var/lib/kmfa/daily-funds-state}" \
  "${DAILY_FUNDS_PUBLICATION_DIR:-/var/lib/kmfa/daily-funds-publication}" \
  "${DAILY_FUNDS_CONTROL_DIR:-/var/lib/kmfa/daily-funds-control}" \
  "${DAILY_FUNDS_DWS_CONFIG_DIR:-/var/lib/kmfa/daily-funds-dws/config}" \
  "${DAILY_FUNDS_DWS_KEYRING_DIR:-/var/lib/kmfa/daily-funds-dws/keyring}"

python3 /opt/daily-funds/scripts/run_daily_funds.py preflight >> /var/log/daily-funds/cron.log 2>&1 || true
cp /opt/daily-funds/crontab.txt /etc/cron.d/daily-funds
chmod 0644 /etc/cron.d/daily-funds
exec cron -f
