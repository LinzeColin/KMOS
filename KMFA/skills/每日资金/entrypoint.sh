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

# The control volume contains only fixed request/session envelopes, never raw
# source data or credentials.  It can survive a prior deployment whose image
# used a different default UID, so normalize it to the explicit app/worker
# root group on every startup without altering any existing bytes.
chmod 0770 "$CONTROL_DIR"

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

# The scheduler writes only fixed-schema, values-free cron events to this
# file.  Relay newly appended events to container stdout so the Cloud control
# plane can verify an actual refresh without reading any private state,
# attachments, provider replies, or financial values.  Starting at byte zero
# prevents a restarted worker from replaying historical records.
CRON_LOG="/var/log/daily-funds/cron.log"
touch "$CRON_LOG"
tail -n 0 -F "$CRON_LOG" &
CRON_LOG_RELAY_PID=$!

python3 /opt/daily-funds/scripts/run_daily_funds.py preflight >> "$CRON_LOG" 2>&1 || true
python3 /opt/daily-funds/scripts/run_daily_funds.py runtime-audit >> "$CRON_LOG" 2>&1 || true
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
python3 /opt/daily-funds/scripts/run_recovery_broker.py >/dev/null 2>&1 &
RECOVERY_BROKER_PID=$!
# A deployment gets one immediate, isolated page refresh; later runs are
# handled by the offset cron line.  This DWS snapshot has its own process lock
# and does not wait for the historical raw-archive reader.
python3 /opt/daily-funds/scripts/run_daily_funds.py payment-request-refresh >> "$CRON_LOG" 2>&1 &
PAYMENT_REQUEST_REFRESH_PID=$!
cron -f &
CRON_PID=$!
printf '%s\n' "$CRON_PID" > "$CRON_PID_FILE"

# A parser version change must re-open already-acquired private raw evidence
# before the next daily 05:20 audit.  A restart with an already complete
# current-version capability scope must not duplicate that full read or force
# an explicitly requested recovery to wait behind the same work.  The gate
# fails closed: missing configuration or journal evidence starts the normal
# bounded audit.
#
# A rolling deployment can overlap a prior container's final sparse-Git read.
# The worker deliberately returns 75 for that *specific* lease collision, but
# leaving the first RUNNING receipt untouched until tomorrow's fixed audit
# makes a finished old holder look like a hung current audit.  Retry exactly
# once after the maximum 13-minute lease plus a small scheduling margin.  Do
# not retry any source, integrity, parser, or credential failure.
STARTUP_RAW_ARCHIVE_RETRY_DELAY_SECONDS=800
RAW_ARCHIVE_AUDIT_PID=""

run_startup_raw_archive_audit() {
  RAW_ARCHIVE_AUDIT_CHILD_PID=""

  stop_startup_raw_archive_audit_child() {
    if [ -n "$RAW_ARCHIVE_AUDIT_CHILD_PID" ]; then
      kill -TERM "$RAW_ARCHIVE_AUDIT_CHILD_PID" 2>/dev/null || true
      wait "$RAW_ARCHIVE_AUDIT_CHILD_PID" 2>/dev/null || true
    fi
    exit 0
  }

  # The outer entrypoint owns this wrapper. Forward its termination signal to
  # the actual audit process so a rolling deployment releases the process lock
  # before the replacement recovery broker resumes the same request.
  trap stop_startup_raw_archive_audit_child INT TERM

  python3 /opt/daily-funds/scripts/run_daily_funds.py raw-archive-audit >> "$CRON_LOG" 2>&1 &
  RAW_ARCHIVE_AUDIT_CHILD_PID=$!
  if wait "$RAW_ARCHIVE_AUDIT_CHILD_PID"; then
    RAW_ARCHIVE_AUDIT_RC=0
  else
    RAW_ARCHIVE_AUDIT_RC=$?
  fi
  RAW_ARCHIVE_AUDIT_CHILD_PID=""

  if [ "$RAW_ARCHIVE_AUDIT_RC" -eq 75 ]; then
    sleep "$STARTUP_RAW_ARCHIVE_RETRY_DELAY_SECONDS" &
    RAW_ARCHIVE_AUDIT_CHILD_PID=$!
    if ! wait "$RAW_ARCHIVE_AUDIT_CHILD_PID"; then
      exit 0
    fi
    RAW_ARCHIVE_AUDIT_CHILD_PID=""
    python3 /opt/daily-funds/scripts/run_daily_funds.py raw-archive-audit >> "$CRON_LOG" 2>&1 &
    RAW_ARCHIVE_AUDIT_CHILD_PID=$!
    wait "$RAW_ARCHIVE_AUDIT_CHILD_PID" || true
    RAW_ARCHIVE_AUDIT_CHILD_PID=""
  fi
}

stop_startup_raw_archive_audit() {
  if [ -n "$RAW_ARCHIVE_AUDIT_PID" ]; then
    kill -TERM "$RAW_ARCHIVE_AUDIT_PID" 2>/dev/null || true
    wait "$RAW_ARCHIVE_AUDIT_PID" 2>/dev/null || true
    RAW_ARCHIVE_AUDIT_PID=""
  fi
}

if python3 /opt/daily-funds/scripts/startup_raw_archive_audit_required.py >/dev/null 2>&1; then
  run_startup_raw_archive_audit &
  RAW_ARCHIVE_AUDIT_PID=$!
fi

shutdown() {
  kill -TERM "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" "$RECOVERY_BROKER_PID" "$PAYMENT_REQUEST_REFRESH_PID" "$CRON_LOG_RELAY_PID" 2>/dev/null || true
  wait "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" "$RECOVERY_BROKER_PID" "$PAYMENT_REQUEST_REFRESH_PID" "$CRON_LOG_RELAY_PID" 2>/dev/null || true
  stop_startup_raw_archive_audit
  rm -f "$CRON_PID_FILE"
  exit 0
}
trap shutdown INT TERM

# PID 1 supervises every fixed component.  If either narrow control broker
# exits, restart the isolated slice rather than silently keeping a partial
# control plane beside the scheduled collector.
while kill -0 "$CRON_PID" 2>/dev/null && kill -0 "$AUTH_BROKER_PID" 2>/dev/null && kill -0 "$HISTORY_PROBE_BROKER_PID" 2>/dev/null && kill -0 "$RECOVERY_BROKER_PID" 2>/dev/null && kill -0 "$CRON_LOG_RELAY_PID" 2>/dev/null; do
  sleep 2
done
kill -TERM "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" "$RECOVERY_BROKER_PID" "$PAYMENT_REQUEST_REFRESH_PID" "$CRON_LOG_RELAY_PID" 2>/dev/null || true
wait "$CRON_PID" "$AUTH_BROKER_PID" "$HISTORY_PROBE_BROKER_PID" "$RECOVERY_BROKER_PID" "$PAYMENT_REQUEST_REFRESH_PID" "$CRON_LOG_RELAY_PID" 2>/dev/null || true
stop_startup_raw_archive_audit
rm -f "$CRON_PID_FILE"
exit 1
