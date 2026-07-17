#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=${DWS_ARCHIVE_ROOT:-$(dirname "$SCRIPT_DIR")}
cd "$PROJECT_DIR"
mkdir -p logs

if [ "${DWS_CODEX_CONTROLLED:-}" != "1" ]; then
  echo "DWS daily archive is disabled for local unattended execution. Run through Codex automation or Codex manual control."
  exit 2
fi

/usr/bin/python3 scripts/sync_notion_skill_backup.py --quiet >> logs/notion_skill_backup.log 2>&1 || true
/usr/bin/python3 scripts/archive_dingtalk_all_files.py \
  --run-source "${DWS_RUN_SOURCE:-codex_manual}" \
  --automation-name "${DWS_AUTOMATION_NAME:-每日钉钉DWS归档}" \
  "$@" >> logs/daily_codex_controlled.log 2>&1
/usr/bin/python3 scripts/sync_notion_skill_backup.py --quiet >> logs/notion_skill_backup.log 2>&1 || true
