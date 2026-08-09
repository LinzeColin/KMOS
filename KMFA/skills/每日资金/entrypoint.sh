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

# Vixie cron starts jobs with a deliberately minimal environment.  In
# particular it drops the Coolify-injected DAILY_FUNDS_* values, which would
# make a manually healthy worker report CONFIG_INVALID as soon as its first
# scheduled probe runs.  Keep the necessary snapshot *only* in the existing
# owner-only state volume; never place secret values in /etc/cron.d (normally
# world-readable) or in the cron log.
CRON_ENV_FILE="$STATE_DIR/cron.env"
umask 077
python3 - "$CRON_ENV_FILE" <<'PY'
import os
import shlex
import sys
from pathlib import Path

target = Path(sys.argv[1])
keys = ["TZ"] + sorted(
    key for key in os.environ
    if key.startswith("DAILY_FUNDS_")
)
with target.open("w", encoding="utf-8") as handle:
    handle.write("# generated at container start; owner-only runtime state\n")
    for key in keys:
        value = os.environ.get(key)
        if value is not None:
            handle.write(f"export {key}={shlex.quote(value)}\n")
PY
chmod 0600 "$CRON_ENV_FILE"

python3 /opt/daily-funds/scripts/run_daily_funds.py preflight >> /var/log/daily-funds/cron.log 2>&1 || true
python3 /opt/daily-funds/scripts/run_daily_funds.py runtime-audit >> /var/log/daily-funds/cron.log 2>&1 || true
cp /opt/daily-funds/crontab.txt /etc/cron.d/daily-funds
chmod 0644 /etc/cron.d/daily-funds

# Coolify's Bearer API deliberately has no container-exec endpoint, while the
# official DWS device flow needs a cloud process that can hold its own DWS
# volume.  This is not a second service, scheduler, shell, or public port:
# the broker accepts only a strict request from the already Access-protected
# KMFA app through the existing control volume.  Its terminal output is sent
# to /dev/null so a device code can never appear in cron logs.
CRON_PID_FILE="/run/daily-funds-cron.pid"
python3 /opt/daily-funds/scripts/run_auth_broker.py >/dev/null 2>&1 &
AUTH_BROKER_PID=$!
python3 /opt/daily-funds/scripts/run_history_probe_broker.py >/dev/null 2>&1 &
HISTORY_PROBE_BROKER_PID=$!
cron -f &
CRON_PID=$!
printf '%s\n' "$CRON_PID" > "$CRON_PID_FILE"

shutdown() {
  kill -TERM "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" 2>/dev/null || true
  wait "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" 2>/dev/null || true
  rm -f "$CRON_PID_FILE"
  exit 0
}
trap shutdown INT TERM

# PID 1 supervises every fixed component.  If either narrow control broker
# exits, restart the isolated slice rather than silently keeping a partial
# control plane beside the scheduled collector.
while kill -0 "$CRON_PID" 2>/dev/null && kill -0 "$AUTH_BROKER_PID" 2>/dev/null && kill -0 "$HISTORY_PROBE_BROKER_PID" 2>/dev/null; do
  sleep 2
done
kill -TERM "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" 2>/dev/null || true
wait "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" 2>/dev/null || true
rm -f "$CRON_PID_FILE"
exit 1
