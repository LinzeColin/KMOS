#!/bin/sh
set -eu

if [ "$(date +%z)" != "+0800" ]; then
  echo "DAILY_FUNDS_TIMEZONE_INVALID"
  exit 1
fi

STATE_DIR="${DAILY_FUNDS_STATE_DIR:-/var/lib/kmfa/daily-funds-state}"
PUBLICATION_DIR="${DAILY_FUNDS_PUBLICATION_DIR:-/var/lib/kmfa/daily-funds-publication}"
CONTROL_DIR="${DAILY_FUNDS_CONTROL_DIR:-/var/lib/kmfa/daily-funds-control}"
DWS_CONFIG_DIR="${DAILY_FUNDS_DWS_CONFIG_DIR:-/var/lib/kmfa/daily-funds-dws/config}"
DWS_KEYRING_DIR="${DAILY_FUNDS_DWS_KEYRING_DIR:-/var/lib/kmfa/daily-funds-dws/keyring}"

# Docker Compose fixes these paths to named volumes.  Refuse an override
# before creating/chmodding anything: a typo must not turn this bootstrap into
# a broad filesystem operation.
if [ "$STATE_DIR" != "/var/lib/kmfa/daily-funds-state" ] \
  || [ "$PUBLICATION_DIR" != "/var/lib/kmfa/daily-funds-publication" ] \
  || [ "$CONTROL_DIR" != "/var/lib/kmfa/daily-funds-control" ] \
  || [ "$DWS_CONFIG_DIR" != "/var/lib/kmfa/daily-funds-dws/config" ] \
  || [ "$DWS_KEYRING_DIR" != "/var/lib/kmfa/daily-funds-dws/keyring" ]; then
  echo "DAILY_FUNDS_RUNTIME_PATH_INVALID"
  exit 1
fi

mkdir -p /var/log/daily-funds \
  "$STATE_DIR" \
  "$PUBLICATION_DIR" \
  "$CONTROL_DIR" \
  "$DWS_CONFIG_DIR" \
  "$DWS_KEYRING_DIR"

# The state journal and the dedicated DWS config/keyring contain cursors or
# refreshable authentication material.  They are never shared with the app
# service, so make their volume roots owner-only even when a Docker volume was
# created previously with a permissive default mode.  Publication and control
# remain outside this set because the protected KMFA app consumes those two
# explicitly shared volumes.
chmod 0700 \
  "$STATE_DIR" \
  "$DWS_CONFIG_DIR" \
  "$DWS_KEYRING_DIR"

python3 /opt/daily-funds/scripts/run_daily_funds.py preflight >> /var/log/daily-funds/cron.log 2>&1 || true
python3 /opt/daily-funds/scripts/run_daily_funds.py runtime-audit >> /var/log/daily-funds/cron.log 2>&1 || true
cp /opt/daily-funds/crontab.txt /etc/cron.d/daily-funds
chmod 0644 /etc/cron.d/daily-funds
exec cron -f
