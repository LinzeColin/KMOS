#!/usr/bin/env python3
"""Archive all DWS-downloadable files from configured DingTalk groups.

The script only calls the official dws CLI. Browser state, DingTalk local
databases, cookies, and private APIs are intentionally out of scope.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DWS = os.environ.get("DWS_BIN", str(Path.home() / ".local/bin/dws"))
CONFIG = ROOT / "config" / "target_groups.yaml"
DB = ROOT / "data" / "all_files_manifest.sqlite3"
DATA_ARCHIVE = ROOT / "data" / "archive"
CHAT_RECORDS = ROOT / "data" / "chat_records"
STAGING = ROOT / "data" / "staging"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
SNAPSHOTS = ROOT / "snapshots"
PROJECT_MISSING = REPORTS / "missing_media.csv"
DEFAULT_COLD_ARCHIVE_ROOT = Path.home() / "onedrive" / "DWS_Archive"
DEFAULT_HOT_STORAGE_DAYS = 60
DEFAULT_MAX_FAILURE_ATTEMPTS = 3
DEFAULT_STAGING_TTL_HOURS = 24
DEFAULT_LOG_RETENTION_DAYS = 15
DEFAULT_AUTOMATION_NAME = "每日钉钉DWS归档"
DEFAULT_HEARTBEAT_RESOURCE_INTERVAL = 25
DEFAULT_PROJECT_IDLE_COMPLETION_DAYS = 7
DEFAULT_DWS_HTTP_TIMEOUT_SECONDS = 120
DEFAULT_DWS_COMMAND_RETRIES = 3
DEFAULT_DWS_RETRY_BACKOFF_SECONDS = 5

DWS_HTTP_TIMEOUT_SECONDS = DEFAULT_DWS_HTTP_TIMEOUT_SECONDS
DWS_COMMAND_RETRIES = DEFAULT_DWS_COMMAND_RETRIES
DWS_RETRY_BACKOFF_SECONDS = DEFAULT_DWS_RETRY_BACKOFF_SECONDS

MEDIA_RE = re.compile(r"mediaId=([^\)\s]+)")
FILE_RE = re.compile(r"\[文件\]\s*(.*?)\s+fileId:\s*([^\s]+)")
ALIDOC_RE = re.compile(r"https?://alidocs\.dingtalk\.com/[^\s\]\)]+")
URL_RE = re.compile(r"https?://[^\s\]\)]+")

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "heic", "bmp", "tif", "tiff"}
OFFICE_EXTS = {"xls", "xlsx", "et", "doc", "docx", "wps", "ppt", "pptx", "csv"}
ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz"}
VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "wmv", "m4v"}
AUDIO_EXTS = {"mp3", "wav", "m4a", "aac", "ogg", "amr", "flac"}
COMMON_SNAPSHOT_EXTS = IMAGE_EXTS | OFFICE_EXTS | ARCHIVE_EXTS | VIDEO_EXTS | AUDIO_EXTS | {"pdf", "txt"}
FORBIDDEN_MIRROR_PARTS = {
    "SKILL.md",
    "target_groups.yaml",
    "archive_dingtalk_all_files.py",
    "sync_notion_skill_backup.py",
    "validate_dws_output_structure.py",
}

MANIFEST_FIELDS = [
    "group_name",
    "open_conversation_id",
    "message_id",
    "message_time",
    "sender_name",
    "sender_id",
    "msg_type",
    "resource_type",
    "resource_id",
    "original_filename",
    "local_archive_path",
    "output_path",
    "sha256",
    "size_bytes",
    "download_method",
    "status",
    "error_reason",
    "attempt_count",
    "first_failed_at",
    "last_failed_at",
    "dws_error_code",
    "error_summary",
    "next_action",
    "exhausted",
    "storage_tier",
    "cold_archive_path",
    "cold_archive_inner_path",
]

MISSING_FIELDS = [
    "group_name",
    "message_id",
    "message_time",
    "resource_type",
    "resource_id",
    "attempted_methods",
    "attempt_count",
    "first_failed_at",
    "last_failed_at",
    "dws_error_code",
    "error_summary",
    "exhausted",
    "error_reason",
    "next_action",
]

CHAT_RECORD_FIELDS = [
    "group_name",
    "open_conversation_id",
    "open_message_id",
    "message_time",
    "sender_name",
    "sender_id",
    "content",
    "quoted_message_id",
    "quoted_sender",
    "quoted_content",
    "resource_count",
    "resource_types",
]

CHAT_RECORD_FILE_FIELDS = [
    "group_name",
    "file_role",
    "output_path",
    "record_count",
    "sha256",
    "size_bytes",
]

RECENT_FILE_RECORD_FIELDS = [
    "group_name",
    "message_time",
    "sender_name",
    "message_id",
    "resource_type",
    "original_filename",
    "normalized_filename",
    "similarity_key",
    "sha256",
    "size_bytes",
    "status",
    "download_method",
    "output_path",
]

SIMILAR_FILE_RECORD_FIELDS = [
    *RECENT_FILE_RECORD_FIELDS,
    "same_normalized_filename_count",
    "same_similarity_key_count",
    "same_sha256_count",
    "similarity_reason",
]


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def run_id() -> str:
    return dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")


def write_heartbeat(run: str, event: str, **fields: Any) -> None:
    payload = {
        "updated_at": now(),
        "run_id": run,
        "event": event,
        **fields,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "current_run_heartbeat.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("DWS_HEARTBEAT " + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def parse_controlled_yaml(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {"scan": {}, "groups": []}
    section = ""
    current_group: dict[str, Any] | None = None
    in_aliases = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            in_aliases = False
            if line.endswith(":"):
                section = line[:-1]
                continue
            key, _, value = line.partition(":")
            config[key.strip()] = parse_scalar(value)
            continue
        if section == "scan" and indent >= 2 and ":" in line:
            key, _, value = line.partition(":")
            config["scan"][key.strip()] = parse_scalar(value)
            continue
        if section != "groups":
            continue
        if current_group is not None and in_aliases and line.startswith("- "):
            current_group.setdefault("aliases", []).append(parse_scalar(line[2:].strip()))
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if current_group is None or item:
                if current_group:
                    config["groups"].append(current_group)
                current_group = {}
                in_aliases = False
            if item and ":" in item:
                key, _, value = item.partition(":")
                current_group[key.strip()] = parse_scalar(value)
            continue
        if current_group is None:
            continue
        if line == "aliases:":
            current_group["aliases"] = []
            in_aliases = True
            continue
        if ":" in line:
            in_aliases = False
            key, _, value = line.partition(":")
            current_group[key.strip()] = parse_scalar(value)
    if current_group:
        config["groups"].append(current_group)
    return config


def safe_name(value: str, limit: int = 96) -> str:
    value = value.strip() or "unknown"
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", value)
    value = re.sub(r"\s+", "_", value)
    value = value.strip("._ ")
    return (value[:limit] or "unknown")


def mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return value[:2] + "***" + value[-2:]
    return value[:6] + "..." + value[-6:]


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:10]


def parse_message_time(value: str) -> dt.datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(value[:19], fmt)
            return parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        except ValueError:
            continue
    return None


def format_message_time(value: dt.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def config_int(config: dict[str, Any], key: str, default: int) -> int:
    value = config.get("scan", {}).get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def project_idle_completion_days(config: dict[str, Any]) -> int:
    return config_int(config, "project_auto_complete_idle_days", DEFAULT_PROJECT_IDLE_COMPLETION_DAYS)


def configure_dws_runtime(config: dict[str, Any]) -> None:
    global DWS_HTTP_TIMEOUT_SECONDS, DWS_COMMAND_RETRIES, DWS_RETRY_BACKOFF_SECONDS
    DWS_HTTP_TIMEOUT_SECONDS = max(
        30,
        config_int(config, "dws_http_timeout_seconds", DEFAULT_DWS_HTTP_TIMEOUT_SECONDS),
    )
    DWS_COMMAND_RETRIES = max(
        0,
        config_int(config, "dws_command_retries", DEFAULT_DWS_COMMAND_RETRIES),
    )
    DWS_RETRY_BACKOFF_SECONDS = max(
        0,
        config_int(config, "dws_retry_backoff_seconds", DEFAULT_DWS_RETRY_BACKOFF_SECONDS),
    )


def hot_cutoff_time(config: dict[str, Any]) -> dt.datetime:
    days = config_int(config, "hot_storage_days", DEFAULT_HOT_STORAGE_DAYS)
    return dt.datetime.now().astimezone() - dt.timedelta(days=days)


def is_hot_message_time(message_time: str, cutoff: dt.datetime) -> bool:
    parsed = parse_message_time(message_time or "")
    return parsed is None or parsed >= cutoff


def parse_date_value(value: Any) -> dt.date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def date_to_scan_time(value: Any) -> str:
    parsed = parse_date_value(value)
    if parsed is None:
        return ""
    return f"{parsed:%Y-%m-%d} 00:00:00"


def bump_message_time(value: str) -> str:
    parsed = parse_message_time(value)
    if parsed is None:
        return value
    return (parsed + dt.timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def normalize_filename(value: str) -> str:
    name = Path(value or "unknown").name.lower()
    stem = Path(name).stem
    suffix = Path(name).suffix.lower().lstrip(".")
    stem = re.sub(r"[\s_\-（）()【】\[\].,，。]+", "", stem)
    return f"{stem}.{suffix}" if suffix else stem


def similarity_key(value: str) -> str:
    key = normalize_filename(value)
    stem = Path(key).stem
    suffix = Path(key).suffix.lower()
    stem = re.sub(r"(20\d{2}|19\d{2})[-_.年]?\d{0,2}[-_.月]?\d{0,2}日?", "", stem)
    stem = re.sub(r"\d+", "#", stem)
    stem = re.sub(r"#+", "#", stem).strip("#")
    return f"{stem}{suffix}" if suffix else stem


def redact_error(text: str) -> str:
    text = text.strip().replace("\n", " ")
    text = re.sub(r"(mediaId=)([^\s\)]+)", lambda m: m.group(1) + mask(m.group(2)), text)
    text = re.sub(r"(fileId:\s*)([^\s]+)", lambda m: m.group(1) + mask(m.group(2)), text)
    text = re.sub(r"(fileId[：:]\s*)([^\s\"，,}]+)", lambda m: m.group(1) + mask(m.group(2)), text)
    text = re.sub(r"(cid[A-Za-z0-9+/=]{12,})", lambda m: mask(m.group(1)), text)
    text = re.sub(r"https?://\S+", "[url_redacted]", text)
    return text[:500]


def parse_json_output(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("DWS output did not contain JSON")
    return json.loads(text[start : end + 1])


def dws_retryable_output(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "io_timeout",
        "request_timeout",
        "context deadline",
        "i/o timeout",
        "dial tcp",
        "connection reset",
        "temporarily unavailable",
        "timeout",
    ]
    return any(marker in lowered for marker in markers)


def run_dws(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess[str]:
    full_args = [DWS, *args]
    if "--format" not in full_args and "-f" not in full_args:
        full_args += ["--format", "json"]
    if "--timeout" not in full_args:
        full_args += ["--timeout", str(DWS_HTTP_TIMEOUT_SECONDS)]
    process_timeout = max(timeout, DWS_HTTP_TIMEOUT_SECONDS + 30)
    attempts = DWS_COMMAND_RETRIES + 1
    last_proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                full_args,
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=process_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            proc = subprocess.CompletedProcess(
                full_args,
                124,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=f"DWS process timeout after {process_timeout}s",
            )
        last_proc = proc
        combined = f"{proc.stdout}\n{proc.stderr}"
        if proc.returncode == 0 or attempt >= attempts or not dws_retryable_output(combined):
            return proc
        print(
            "DWS_RETRY "
            + json.dumps(
                {
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "sleep_seconds": DWS_RETRY_BACKOFF_SECONDS,
                    "reason": redact_error(combined),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        if DWS_RETRY_BACKOFF_SECONDS:
            time.sleep(DWS_RETRY_BACKOFF_SECONDS * attempt)
    return last_proc


def dws_download_timeout() -> int:
    raw = os.environ.get("DWS_DOWNLOAD_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return 180
    try:
        value = int(raw)
    except ValueError:
        return 180
    return max(10, value)


def init_dirs(config: dict[str, Any]) -> None:
    for path in [DB.parent, DATA_ARCHIVE, CHAT_RECORDS, STAGING, REPORTS, LOGS, SNAPSHOTS]:
        path.mkdir(parents=True, exist_ok=True)
    for group in enabled_groups(config):
        (SNAPSHOTS / group["canonical_name"]).mkdir(parents=True, exist_ok=True)
        (CHAT_RECORDS / safe_name(group["canonical_name"])).mkdir(parents=True, exist_ok=True)


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manifest (
            group_name TEXT NOT NULL,
            group_slug TEXT NOT NULL,
            open_conversation_id TEXT NOT NULL,
            open_message_id TEXT NOT NULL,
            message_time TEXT,
            sender_name TEXT,
            sender_id TEXT,
            msg_type TEXT,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            original_filename TEXT,
            local_archive_path TEXT,
            zip_path TEXT,
            sha256 TEXT,
            size_bytes INTEGER,
            download_method TEXT,
            status TEXT NOT NULL,
            error_reason TEXT,
            attempted_methods TEXT,
            archived_at TEXT NOT NULL,
            PRIMARY KEY (group_name, open_message_id, resource_type, resource_id)
        )
        """
    )
    ensure_manifest_columns(conn)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manifest_group_status
        ON manifest (group_name, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_manifest_resource
        ON manifest (group_name, resource_type, resource_id, status)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            group_name TEXT NOT NULL,
            open_conversation_id TEXT NOT NULL,
            open_message_id TEXT NOT NULL,
            message_time TEXT,
            sender_name TEXT,
            sender_id TEXT,
            msg_type TEXT,
            content TEXT,
            quoted_message_json TEXT,
            reactions_json TEXT,
            raw_json TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            PRIMARY KEY (group_name, open_message_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_group_time
        ON messages (group_name, message_time)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS group_cursors (
            group_name TEXT PRIMARY KEY,
            group_type TEXT,
            scan_mode TEXT,
            last_success_run_id TEXT,
            last_success_cursor_time TEXT,
            last_message_time_seen TEXT,
            completion_boundary TEXT,
            dws_version TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def ensure_manifest_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(manifest)").fetchall()}
    columns = {
        "attempt_count": "INTEGER DEFAULT 0",
        "first_failed_at": "TEXT",
        "last_failed_at": "TEXT",
        "dws_error_code": "TEXT",
        "error_summary": "TEXT",
        "next_action": "TEXT",
        "exhausted": "INTEGER DEFAULT 0",
        "storage_tier": "TEXT DEFAULT 'hot'",
        "cold_archive_path": "TEXT",
        "cold_archive_inner_path": "TEXT",
    }
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE manifest ADD COLUMN {name} {ddl}")


def enabled_groups(config: dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    for group in config.get("groups", []):
        if group.get("enabled", True):
            group.setdefault("aliases", [group["canonical_name"]])
            groups.append(group)
    return groups


def validate_config(config: dict[str, Any]) -> None:
    for group in enabled_groups(config):
        mode = str(group.get("scan_mode", "auto") or "auto")
        if mode not in {"auto", "manual_only"}:
            raise RuntimeError(f"invalid scan_mode for {group['canonical_name']}: {mode}")
        group_type = str(group.get("group_type", "standing") or "standing")
        if group_type not in {"standing", "project"}:
            raise RuntimeError(f"invalid group_type for {group['canonical_name']}: {group_type}")
        if group_type == "project":
            for field in ("start_date", "completed_date", "grace_days"):
                if field not in group:
                    raise RuntimeError(f"project group missing {field}: {group['canonical_name']}")


def effective_scan_mode(group: dict[str, Any], today: dt.date | None = None) -> str:
    mode = str(group.get("scan_mode", "auto") or "auto").strip()
    if mode == "manual_only":
        return "manual_only"
    if str(group.get("group_type", "standing")) != "project":
        return mode
    completed = parse_date_value(group.get("completed_date"))
    if completed is None:
        return mode
    grace_days = int(group.get("grace_days", 7) or 7)
    today = today or dt.datetime.now().astimezone().date()
    if today > completed + dt.timedelta(days=grace_days):
        return "manual_only"
    return mode


def selected_groups(config: dict[str, Any], requested: list[str] | None) -> list[dict[str, Any]]:
    groups = enabled_groups(config)
    if not requested:
        return [group for group in groups if effective_scan_mode(group) != "manual_only"]
    wanted = {item.strip() for value in requested for item in value.split(",") if item.strip()}
    selected = [
        group
        for group in groups
        if group["canonical_name"] in wanted or any(alias in wanted for alias in group.get("aliases", []))
    ]
    matched = {group["canonical_name"] for group in selected}
    matched.update(alias for group in selected for alias in group.get("aliases", []) if alias in wanted)
    missing = sorted(wanted - matched)
    if missing:
        raise RuntimeError(f"requested groups not found or disabled: {missing}")
    return selected


def resolve_group(group: dict[str, Any]) -> dict[str, Any]:
    aliases = list(dict.fromkeys([group["canonical_name"], *group.get("aliases", [])]))
    exact_matches: dict[str, dict[str, Any]] = {}
    loose_matches: dict[str, dict[str, Any]] = {}
    for alias in aliases:
        proc = run_dws(["chat", "search", "--query", alias, "--limit", "10", "--cursor", "0"], timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(redact_error(proc.stderr or proc.stdout))
        data = parse_json_output(proc.stdout)
        for item in data.get("result", {}).get("groups", []):
            title = item.get("title", "")
            conv_id = item.get("openConversationId", "")
            if not conv_id:
                continue
            if title in aliases:
                exact_matches[conv_id] = item
            else:
                loose_matches[conv_id] = item
    if len(exact_matches) == 1:
        item = next(iter(exact_matches.values()))
    elif not exact_matches and len(loose_matches) == 1:
        item = next(iter(loose_matches.values()))
    else:
        candidates = list(exact_matches.values()) or list(loose_matches.values())
        safe = [
            {
                "title": c.get("title", ""),
                "memberCount": c.get("memberCount"),
                "openConversationId": mask(c.get("openConversationId", "")),
            }
            for c in candidates
        ]
        raise RuntimeError(f"group resolution is not unique for {group['canonical_name']}: {safe}")
    configured = group.get("open_conversation_id")
    if configured and configured != item.get("openConversationId"):
        raise RuntimeError(f"configured group id mismatch for {group['canonical_name']}")
    resolved = dict(group)
    resolved["open_conversation_id"] = item["openConversationId"]
    resolved["resolved_title"] = item.get("title", group["canonical_name"])
    resolved["member_count"] = item.get("memberCount")
    return resolved


def initial_scan_start(group: dict[str, Any], config: dict[str, Any]) -> str:
    scan = config.get("scan", {})
    since = str(scan.get("full_scan_since", "2026-01-01 00:00:00"))
    if group.get("group_type") == "project":
        since = date_to_scan_time(group.get("start_date")) or since
    return since


def get_group_cursor(conn: sqlite3.Connection, group_name: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM group_cursors WHERE group_name = ?", (group_name,)).fetchone()


def scan_start_for_group(
    conn: sqlite3.Connection,
    group: dict[str, Any],
    config: dict[str, Any],
    full_reconciliation: bool,
) -> tuple[str, str]:
    if full_reconciliation:
        return initial_scan_start(group, config), "full_reconciliation"
    cursor = get_group_cursor(conn, group["canonical_name"])
    if cursor and cursor["last_success_cursor_time"]:
        return bump_message_time(cursor["last_success_cursor_time"]), "group_cursor"
    return initial_scan_start(group, config), "initial_config_start"


def update_group_cursor(
    conn: sqlite3.Connection,
    group: dict[str, Any],
    stats: dict[str, Any],
    current_run: str,
    dws_version: str,
) -> None:
    if not stats.get("message_scan_exhausted"):
        raise RuntimeError(f"refuse to update cursor without completion boundary for {group['canonical_name']}")
    cursor_time = stats.get("last_message_time_seen") or stats.get("history_scan_start") or ""
    last_message_time_seen = (
        stats.get("last_message_time_seen")
        or stats.get("previous_last_message_time_seen")
        or stats.get("previous_last_success_cursor_time")
        or cursor_time
    )
    conn.execute(
        """
        INSERT INTO group_cursors (
            group_name, group_type, scan_mode, last_success_run_id,
            last_success_cursor_time, last_message_time_seen, completion_boundary,
            dws_version, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(group_name) DO UPDATE SET
            group_type = excluded.group_type,
            scan_mode = excluded.scan_mode,
            last_success_run_id = excluded.last_success_run_id,
            last_success_cursor_time = excluded.last_success_cursor_time,
            last_message_time_seen = excluded.last_message_time_seen,
            completion_boundary = excluded.completion_boundary,
            dws_version = excluded.dws_version,
            updated_at = excluded.updated_at
        """,
        (
            group["canonical_name"],
            group.get("group_type", "standing"),
            group.get("scan_mode", "auto"),
            current_run,
            cursor_time,
            last_message_time_seen,
            stats.get("message_completion_boundary", ""),
            dws_version,
            now(),
        ),
    )


def update_group_field_lines(lines: list[str], start: int, end: int, key: str, value: str) -> tuple[int, bool]:
    pattern = re.compile(rf"^    {re.escape(key)}:\s*")
    new_line = f"    {key}: {value}"
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            changed = lines[index] != new_line
            lines[index] = new_line
            return end, changed
    insert_at = end
    for index in range(start + 1, end):
        if re.match(r"^    enabled:\s*", lines[index]):
            insert_at = index
            break
    lines.insert(insert_at, new_line)
    return end + 1, True


def mark_project_group_manual_only_in_config(
    group_name: str,
    completed_at: str,
    reason: str,
    current_run: str,
    config_path: Path = CONFIG,
) -> dict[str, Any]:
    lines = config_path.read_text(encoding="utf-8").splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^  - canonical_name:\s*(.+?)\s*$", line)
        if match and parse_scalar(match.group(1)) == group_name:
            start = index
            break
    if start is None:
        raise RuntimeError(f"cannot find project group in config: {group_name}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.match(r"^  - canonical_name:\s*", lines[index]):
            end = index
            break

    original = "\n".join(lines) + "\n"
    completed_date = completed_at[:10]
    updates = [
        ("scan_mode", yaml_quote("manual_only")),
        ("completed_date", yaml_quote(completed_date)),
        ("completed_at", yaml_quote(completed_at)),
        ("last_active_message_time", yaml_quote(completed_at)),
        ("completion_reason", yaml_quote(reason)),
        ("completion_run_id", yaml_quote(current_run)),
        ("auto_completed", "true"),
    ]
    changed = False
    for key, value in updates:
        end, field_changed = update_group_field_lines(lines, start, end, key, value)
        changed = changed or field_changed

    new_text = "\n".join(lines) + "\n"
    if new_text != original:
        config_path.write_text(new_text, encoding="utf-8")
        changed = True
    return {
        "config_updated": changed,
        "completed_at": completed_at,
        "completed_date": completed_date,
        "scan_mode_after": "manual_only",
        "completion_reason": reason,
        "completion_run_id": current_run,
    }


def maybe_auto_complete_project_group(
    config: dict[str, Any],
    group: dict[str, Any],
    stats: dict[str, Any],
    current_run: str,
    config_path: Path = CONFIG,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "checked": group.get("group_type") == "project",
        "completed": False,
        "config_updated": False,
    }
    if group.get("group_type") != "project":
        return result
    idle_days_required = project_idle_completion_days(config)
    result["idle_days_required"] = idle_days_required
    if str(group.get("scan_mode", "auto")) == "manual_only":
        result["reason"] = "already_manual_only"
        return result
    if not stats.get("message_scan_exhausted"):
        result["reason"] = "message_scan_not_at_completion_boundary"
        return result
    if int(stats.get("messages_scanned", 0) or 0) != 0:
        result["reason"] = "new_messages_seen_this_run"
        return result
    new_file_signal = sum(
        int(stats.get(key, 0) or 0)
        for key in ("resources_found", "downloaded", "duplicate", "failed", "snapshot")
    )
    if new_file_signal:
        result["reason"] = "new_file_signal_seen_this_run"
        return result

    last_activity_text = (
        stats.get("last_message_time_seen")
        or stats.get("previous_last_message_time_seen")
        or stats.get("previous_last_success_cursor_time")
        or ""
    )
    result["last_active_message_time"] = last_activity_text
    last_activity = parse_message_time(last_activity_text)
    if last_activity is None:
        result["reason"] = "missing_last_message_time"
        return result

    elapsed = dt.datetime.now().astimezone() - last_activity
    observed_days = elapsed.total_seconds() / 86400
    result["idle_days_observed"] = round(observed_days, 3)
    if elapsed < dt.timedelta(days=idle_days_required):
        result["reason"] = "idle_window_not_reached"
        return result

    reason = f"auto_idle_{idle_days_required}d_no_new_messages_or_files"
    update = mark_project_group_manual_only_in_config(
        group["canonical_name"],
        last_activity.strftime("%Y-%m-%d %H:%M:%S"),
        reason,
        current_run,
        config_path=config_path,
    )
    group["scan_mode"] = "manual_only"
    group["completed_date"] = update["completed_date"]
    group["completed_at"] = update["completed_at"]
    result.update(update)
    result["completed"] = True
    result["reason"] = reason
    return result


def list_messages(
    group: dict[str, Any],
    config: dict[str, Any],
    start_time: str,
    progress_cb: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scan = config.get("scan", {})
    limit = str(scan.get("page_size", scan.get("daily_limit", 500)))
    current_time = start_time
    messages: list[dict[str, Any]] = []
    seen: set[str] = set()
    page_count = 0
    stop_reason = ""
    exhausted = False
    while True:
        proc = run_dws(
            [
                "chat",
                "message",
                "list",
                "--group",
                group["open_conversation_id"],
                "--time",
                current_time,
                "--limit",
                limit,
                "--forward",
                "true",
            ],
            timeout=180,
        )
        if proc.returncode != 0:
            detail = redact_error(proc.stderr or proc.stdout)
            raise RuntimeError(f"DWS message scan failed after {len(messages)} messages: {detail}")
        data = parse_json_output(proc.stdout)
        result = data.get("result", {})
        page_messages = result.get("messages", [])
        page_count += 1
        new_count = 0
        for msg in page_messages:
            msg_id = msg.get("openMessageId") or json.dumps(msg, ensure_ascii=False, sort_keys=True)
            if msg_id in seen:
                continue
            seen.add(msg_id)
            messages.append(msg)
            new_count += 1
        if progress_cb:
            progress_cb(
                "message_page",
                pages_scanned=page_count,
                total_messages=len(messages),
                new_messages=new_count,
                current_cursor=current_time,
                has_more=bool(result.get("hasMore")),
            )
        if not result.get("hasMore"):
            exhausted = True
            stop_reason = "hasMore_false"
            break
        if not page_messages:
            stop_reason = "empty_page"
            break
        page_times = [msg.get("createTime", "") for msg in page_messages if msg.get("createTime")]
        next_time = max(page_times) if page_times else ""
        if not next_time:
            stop_reason = "missing_cursor_time"
            break
        if next_time <= current_time:
            bumped = bump_message_time(current_time)
            if bumped == current_time:
                stop_reason = "cursor_time_not_advanced"
                break
            current_time = bumped
            continue
        current_time = next_time
    last_message_time_seen = max((msg.get("createTime", "") for msg in messages if msg.get("createTime")), default="")
    return messages, {
        "history_scan_start": start_time,
        "message_pages_scanned": page_count,
        "message_scan_exhausted": exhausted,
        "message_scan_stop_reason": stop_reason,
        "message_scan_last_cursor_time": current_time,
        "last_message_time_seen": last_message_time_seen,
        "message_completion_boundary": "DWS hasMore=false",
    }


def infer_resource_type(filename: str, hint: str = "") -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if hint in {"image", "video", "audio"}:
        return hint
    if ext in IMAGE_EXTS:
        return "image"
    if ext in OFFICE_EXTS:
        return "office"
    if ext == "pdf":
        return "pdf"
    if ext in ARCHIVE_EXTS:
        return "archive"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext == "txt":
        return "txt"
    return "unknown"


def media_hint(content: str, start: int) -> str:
    prefix = content[max(0, start - 16) : start + 16]
    if "图片" in prefix:
        return "image"
    if "视频" in prefix:
        return "video"
    if "语音" in prefix or "音频" in prefix:
        return "audio"
    return "unknown"


def iter_json_values(obj: Any, parent_key: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                found.append((key, value))
            elif isinstance(value, (dict, list)):
                found.extend(iter_json_values(value, key))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(iter_json_values(value, parent_key))
    return found


def candidate_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        candidate.get("open_message_id", ""),
        candidate.get("resource_type", ""),
        candidate.get("resource_id", ""),
    )


def extract_from_content(base: dict[str, Any], content: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in FILE_RE.finditer(content):
        filename = match.group(1).strip()
        resource_id = match.group(2).strip()
        candidates.append(
            {
                **base,
                "msg_type": "file",
                "resource_type": infer_resource_type(filename),
                "resource_id": resource_id,
                "original_filename": filename or f"drive_{short_hash(resource_id)}",
                "download_methods": ["dws_drive_download"],
            }
        )
    for match in MEDIA_RE.finditer(content):
        resource_id = match.group(1).strip()
        hint = media_hint(content, match.start())
        candidates.append(
            {
                **base,
                "msg_type": "media",
                "resource_type": infer_resource_type("", hint),
                "resource_id": resource_id,
                "original_filename": f"{hint if hint != 'unknown' else 'media'}_{short_hash(resource_id)}",
                "download_methods": ["dws_chat_message_download_media"],
            }
        )
    for match in ALIDOC_RE.finditer(content):
        url = match.group(0).strip()
        candidates.append(
            {
                **base,
                "msg_type": "doc",
                "resource_type": "doc",
                "resource_id": url,
                "original_filename": f"alidoc_{short_hash(url)}",
                "download_methods": ["dws_doc_download", "dws_drive_download"],
            }
        )
    for match in URL_RE.finditer(content):
        url = match.group(0).strip()
        if "alidocs.dingtalk.com" in url:
            continue
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc == "down.dingtalk.com":
            name = Path(parsed.path).name or f"url_{short_hash(url)}"
            candidates.append(
                {
                    **base,
                    "msg_type": "url",
                    "resource_type": infer_resource_type(name),
                    "resource_id": url,
                    "original_filename": name,
                    "download_methods": ["http_get_public_url"],
                }
            )
    return candidates


def extract_candidates_from_message(msg: dict[str, Any], group: dict[str, Any]) -> list[dict[str, Any]]:
    base = {
        "group_name": group["canonical_name"],
        "group_slug": safe_name(group["canonical_name"]),
        "open_conversation_id": group["open_conversation_id"],
        "open_message_id": msg.get("openMessageId", ""),
        "message_time": msg.get("createTime", ""),
        "sender_name": msg.get("sender", ""),
        "sender_id": msg.get("senderOpenDingTalkId", ""),
    }
    candidates = extract_from_content(base, msg.get("content", "") or "")
    quoted = msg.get("quotedMessage")
    if isinstance(quoted, dict):
        quoted_base = {
            **base,
            "open_message_id": quoted.get("openMessageId", base["open_message_id"]),
            "message_time": quoted.get("createTime", base["message_time"]),
            "sender_name": quoted.get("sender", base["sender_name"]),
        }
        candidates.extend(extract_from_content(quoted_base, quoted.get("content", "") or ""))
    for key, value in iter_json_values(msg):
        lower_key = key.lower()
        if lower_key in {"mediaid", "media_id"} and value:
            hint = "unknown"
            candidates.append(
                {
                    **base,
                    "msg_type": "media",
                    "resource_type": "unknown",
                    "resource_id": value,
                    "original_filename": f"media_{short_hash(value)}",
                    "download_methods": ["dws_chat_message_download_media"],
                }
            )
        elif lower_key in {"fileid", "file_id", "dentryid", "dentryuuid"} and value:
            candidates.append(
                {
                    **base,
                    "msg_type": "file",
                    "resource_type": "unknown",
                    "resource_id": value,
                    "original_filename": f"drive_{short_hash(value)}",
                    "download_methods": ["dws_drive_download"],
                }
            )
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        deduped.setdefault(candidate_key(candidate), candidate)
    return list(deduped.values())


def find_downloaded_file(path: Path) -> Path | None:
    if path.is_file():
        return path
    files = [p for p in path.rglob("*") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_size)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_ext_from_magic(path: Path, fallback_name: str) -> str:
    ext = Path(fallback_name).suffix.lower()
    if ext and ext not in {".unknown", ".bin"}:
        return ext
    data = path.read_bytes()[:16]
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"PK\x03\x04"):
        return ".zip"
    guessed = mimetypes.guess_extension(mimetypes.guess_type(fallback_name)[0] or "")
    return guessed or ext or ".bin"


def normalized_message_day(message_time: str) -> tuple[str, str, str]:
    try:
        parsed = dt.datetime.strptime(message_time[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        parsed = dt.datetime.now()
    return f"{parsed:%Y}", f"{parsed:%m}", f"{parsed:%d}"


def archive_names(candidate: dict[str, Any], downloaded: Path) -> tuple[Path, str]:
    group_slug = candidate["group_slug"]
    _year, month, _day = normalized_message_day(candidate.get("message_time", ""))
    original = candidate.get("original_filename") or downloaded.name or "downloaded_file"
    ext = infer_ext_from_magic(downloaded, original)
    original_stem = safe_name(Path(original).stem, 72)
    stamp = re.sub(r"[-: ]", "", (candidate.get("message_time") or "")[:19]) or "unknown_time"
    sender = safe_name(candidate.get("sender_name", "unknown"), 32)
    msg_short = short_hash(candidate.get("open_message_id", ""))
    filename = f"{stamp}_{sender}_{msg_short}_{original_stem}{ext}"
    archive_rel = Path("data") / "archive" / group_slug / "files" / month / filename
    output_path = str(Path("files") / month / filename)
    return archive_rel, output_path


def existing_success(conn: sqlite3.Connection, candidate: dict[str, Any]) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT * FROM manifest
        WHERE group_name = ? AND resource_type = ? AND resource_id = ?
          AND status IN ('downloaded', 'duplicate', 'snapshot')
          AND local_archive_path IS NOT NULL AND local_archive_path != ''
        ORDER BY archived_at DESC
        LIMIT 1
        """,
        (candidate["group_name"], candidate["resource_type"], candidate["resource_id"]),
    ).fetchone()
    if row and (ROOT / row["local_archive_path"]).exists():
        return row
    return None


def existing_failure(conn: sqlite3.Connection, candidate: dict[str, Any]) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT * FROM manifest
        WHERE group_name = ? AND resource_type = ? AND resource_id = ?
          AND status = 'failed'
        ORDER BY attempt_count DESC, archived_at DESC
        LIMIT 1
        """,
        (candidate["group_name"], candidate["resource_type"], candidate["resource_id"]),
    ).fetchone()


def extract_dws_error_code(text: str) -> str:
    for pattern in (r'"server_error_code"\s*:\s*"([^"]+)"', r"server_error_code[=:]\s*([A-Za-z0-9_-]+)"):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    if "TimeoutExpired" in text or "timed out" in text:
        return "timeout"
    return ""


def output_path_for_existing(candidate: dict[str, Any], local_archive_path: str) -> str:
    _archive_rel, output_path = archive_names(candidate, ROOT / local_archive_path)
    return output_path


def upsert_manifest(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    defaults: dict[str, Any] = {
        "attempt_count": 0,
        "first_failed_at": "",
        "last_failed_at": "",
        "dws_error_code": "",
        "error_summary": "",
        "next_action": "",
        "exhausted": 0,
        "storage_tier": "hot",
        "cold_archive_path": "",
        "cold_archive_inner_path": "",
    }
    for key, value in defaults.items():
        row.setdefault(key, value)
    conn.execute(
        """
        INSERT INTO manifest (
            group_name, group_slug, open_conversation_id, open_message_id,
            message_time, sender_name, sender_id, msg_type, resource_type,
            resource_id, original_filename, local_archive_path, zip_path, sha256,
            size_bytes, download_method, status, error_reason, attempted_methods,
            archived_at, attempt_count, first_failed_at, last_failed_at,
            dws_error_code, error_summary, next_action, exhausted, storage_tier,
            cold_archive_path, cold_archive_inner_path
        ) VALUES (
            :group_name, :group_slug, :open_conversation_id, :open_message_id,
            :message_time, :sender_name, :sender_id, :msg_type, :resource_type,
            :resource_id, :original_filename, :local_archive_path, :zip_path, :sha256,
            :size_bytes, :download_method, :status, :error_reason, :attempted_methods,
            :archived_at, :attempt_count, :first_failed_at, :last_failed_at,
            :dws_error_code, :error_summary, :next_action, :exhausted, :storage_tier,
            :cold_archive_path, :cold_archive_inner_path
        )
        ON CONFLICT(group_name, open_message_id, resource_type, resource_id)
        DO UPDATE SET
            group_slug = excluded.group_slug,
            open_conversation_id = excluded.open_conversation_id,
            message_time = excluded.message_time,
            sender_name = excluded.sender_name,
            sender_id = excluded.sender_id,
            msg_type = excluded.msg_type,
            original_filename = excluded.original_filename,
            local_archive_path = excluded.local_archive_path,
            zip_path = excluded.zip_path,
            sha256 = excluded.sha256,
            size_bytes = excluded.size_bytes,
            download_method = excluded.download_method,
            status = excluded.status,
            error_reason = excluded.error_reason,
            attempted_methods = excluded.attempted_methods,
            archived_at = excluded.archived_at,
            attempt_count = excluded.attempt_count,
            first_failed_at = excluded.first_failed_at,
            last_failed_at = excluded.last_failed_at,
            dws_error_code = excluded.dws_error_code,
            error_summary = excluded.error_summary,
            next_action = excluded.next_action,
            exhausted = excluded.exhausted,
            storage_tier = excluded.storage_tier,
            cold_archive_path = excluded.cold_archive_path,
            cold_archive_inner_path = excluded.cold_archive_inner_path
        """,
        row,
    )


def run_download_method(candidate: dict[str, Any], method: str, output: Path) -> tuple[bool, str]:
    timeout = dws_download_timeout()
    if method == "dws_chat_message_download_media":
        proc = run_dws(
            [
                "chat",
                "message",
                "download-media",
                "--type",
                "mediaId",
                "--resource-id",
                candidate["resource_id"],
                "--message-id",
                candidate["open_message_id"],
                "--open-conversation-id",
                candidate["open_conversation_id"],
                "--output",
                str(output),
            ],
            timeout=timeout,
        )
        return proc.returncode == 0, redact_error(proc.stderr or proc.stdout)
    if method == "dws_drive_download":
        filename = safe_name(candidate.get("original_filename", "") or f"drive_{short_hash(candidate['resource_id'])}")
        target = output / filename
        proc = run_dws(
            ["drive", "download", "--node", candidate["resource_id"], "--output", str(target)],
            timeout=timeout,
        )
        return proc.returncode == 0, redact_error(proc.stderr or proc.stdout)
    if method == "dws_doc_download":
        filename = safe_name(candidate.get("original_filename", "") or f"doc_{short_hash(candidate['resource_id'])}")
        target = output / filename
        proc = run_dws(
            ["doc", "download", "--node", candidate["resource_id"], "--output", str(target)],
            timeout=timeout,
        )
        return proc.returncode == 0, redact_error(proc.stderr or proc.stdout)
    if method == "http_get_public_url":
        parsed = urllib.parse.urlparse(candidate["resource_id"])
        if parsed.netloc != "down.dingtalk.com" or "Signature=" in parsed.query or "Expires=" in parsed.query:
            return False, "unsafe_or_signed_url_skipped"
        filename = safe_name(candidate.get("original_filename", "") or Path(parsed.path).name or f"url_{short_hash(candidate['resource_id'])}")
        target = output / filename
        with urllib.request.urlopen(candidate["resource_id"], timeout=60) as response:
            target.write_bytes(response.read())
        return True, ""
    return False, f"unsupported_method:{method}"


def download_candidate(
    conn: sqlite3.Connection,
    candidate: dict[str, Any],
    current_run: str,
    max_failure_attempts: int,
    retry_exhausted: bool = False,
) -> dict[str, Any]:
    reused = existing_success(conn, candidate)
    if reused:
        row = base_manifest_row(candidate, current_run)
        row.update(
            {
                "local_archive_path": reused["local_archive_path"],
                "zip_path": output_path_for_existing(candidate, reused["local_archive_path"]),
                "sha256": reused["sha256"],
                "size_bytes": reused["size_bytes"],
                "download_method": reused["download_method"],
                "status": "duplicate",
                "error_reason": "",
                "attempted_methods": "reuse_existing_resource",
                "attempt_count": 0,
                "exhausted": 0,
                "storage_tier": "hot",
                "next_action": "",
            }
        )
        upsert_manifest(conn, row)
        return row

    previous_failure = existing_failure(conn, candidate)
    previous_attempts = int(previous_failure["attempt_count"] or 0) if previous_failure else 0
    if previous_failure and int(previous_failure["exhausted"] or 0) and not retry_exhausted:
        row = base_manifest_row(candidate, current_run)
        row.update(
            {
                "status": "failed",
                "error_reason": previous_failure["error_reason"] or "exhausted_failure_not_retried",
                "attempted_methods": "skipped_exhausted",
                "attempt_count": previous_attempts,
                "first_failed_at": previous_failure["first_failed_at"] or "",
                "last_failed_at": previous_failure["last_failed_at"] or "",
                "dws_error_code": previous_failure["dws_error_code"] or "",
                "error_summary": previous_failure["error_summary"] or "",
                "next_action": "manual_retry_exhausted_resource",
                "exhausted": 1,
                "storage_tier": "hot",
            }
        )
        upsert_manifest(conn, row)
        return row

    attempted: list[str] = []
    errors: list[str] = []
    methods = candidate.get("download_methods") or []
    with tempfile.TemporaryDirectory(prefix="dws-all-files-", dir=STAGING) as td:
        tmp = Path(td)
        for method in methods:
            attempted.append(method)
            try:
                ok, detail = run_download_method(candidate, method, tmp)
            except Exception as exc:  # noqa: BLE001 - keep resource-level failures non-fatal.
                ok, detail = False, redact_error(str(exc))
            if not ok:
                errors.append(f"{method}:{detail}")
                continue
            downloaded = find_downloaded_file(tmp)
            if not downloaded:
                errors.append(f"{method}:no_file_created")
                continue
            size = downloaded.stat().st_size
            if size <= 0:
                errors.append(f"{method}:empty_file")
                continue
            digest = sha256_file(downloaded)
            archive_rel, output_path = archive_names(candidate, downloaded)
            archive_abs = ROOT / archive_rel
            archive_abs.parent.mkdir(parents=True, exist_ok=True)
            if not archive_abs.exists():
                shutil.copy2(downloaded, archive_abs)
            row = base_manifest_row(candidate, current_run)
            row.update(
                {
                    "local_archive_path": str(archive_rel),
                    "zip_path": output_path,
                    "sha256": digest,
                    "size_bytes": size,
                    "download_method": method,
                    "status": "downloaded",
                    "error_reason": "",
                    "attempted_methods": ",".join(attempted),
                    "attempt_count": 0,
                    "first_failed_at": "",
                    "last_failed_at": "",
                    "dws_error_code": "",
                    "error_summary": "",
                    "next_action": "",
                    "exhausted": 0,
                    "storage_tier": "hot",
                }
            )
            if candidate["resource_type"] == "unknown":
                row["resource_type"] = infer_resource_type(archive_abs.name)
            upsert_manifest(conn, row)
            return row
    attempt_count = previous_attempts + 1
    error_reason = " | ".join(errors)[-500:]
    failed_at = now()
    exhausted = attempt_count >= max_failure_attempts
    row = base_manifest_row(candidate, current_run)
    row.update(
        {
            "local_archive_path": "",
            "zip_path": "",
            "sha256": "",
            "size_bytes": 0,
            "download_method": "",
            "status": "failed",
            "error_reason": error_reason,
            "attempted_methods": ",".join(attempted),
            "attempt_count": attempt_count,
            "first_failed_at": (previous_failure["first_failed_at"] if previous_failure else "") or failed_at,
            "last_failed_at": failed_at,
            "dws_error_code": extract_dws_error_code(error_reason),
            "error_summary": error_reason[:240],
            "next_action": "manual_retry_exhausted_resource" if exhausted else "retry_with_backoff",
            "exhausted": 1 if exhausted else 0,
            "storage_tier": "hot",
        }
    )
    upsert_manifest(conn, row)
    return row


def base_manifest_row(candidate: dict[str, Any], current_run: str) -> dict[str, Any]:
    return {
        "group_name": candidate["group_name"],
        "group_slug": candidate["group_slug"],
        "open_conversation_id": candidate["open_conversation_id"],
        "open_message_id": candidate["open_message_id"],
        "message_time": candidate.get("message_time", ""),
        "sender_name": candidate.get("sender_name", ""),
        "sender_id": candidate.get("sender_id", ""),
        "msg_type": candidate.get("msg_type", ""),
        "resource_type": candidate.get("resource_type", "unknown"),
        "resource_id": candidate["resource_id"],
        "original_filename": candidate.get("original_filename", ""),
        "local_archive_path": "",
        "zip_path": "",
        "sha256": "",
        "size_bytes": 0,
        "download_method": "",
        "status": "failed",
        "error_reason": "",
        "attempted_methods": "",
        "archived_at": current_run,
        "attempt_count": 0,
        "first_failed_at": "",
        "last_failed_at": "",
        "dws_error_code": "",
        "error_summary": "",
        "next_action": "",
        "exhausted": 0,
        "storage_tier": "hot",
        "cold_archive_path": "",
        "cold_archive_inner_path": "",
    }


def ingest_snapshots(conn: sqlite3.Connection, group: dict[str, Any], current_run: str) -> int:
    root = SNAPSHOTS / group["canonical_name"]
    root.mkdir(parents=True, exist_ok=True)
    added = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        ext = path.suffix.lower().lstrip(".")
        if ext and ext not in COMMON_SNAPSHOT_EXTS:
            continue
        digest = sha256_file(path)
        resource_id = f"snapshot:{path.relative_to(root)}"
        candidate = {
            "group_name": group["canonical_name"],
            "group_slug": safe_name(group["canonical_name"]),
            "open_conversation_id": group["open_conversation_id"],
            "open_message_id": f"snapshot:{short_hash(str(path.relative_to(root)))}",
            "message_time": now()[:19].replace("T", " "),
            "sender_name": "cache_snapshot",
            "sender_id": "",
            "msg_type": "snapshot",
            "resource_type": infer_resource_type(path.name),
            "resource_id": resource_id,
            "original_filename": path.name,
        }
        if existing_success(conn, candidate):
            continue
        archive_rel, output_path = archive_names(candidate, path)
        archive_abs = ROOT / archive_rel
        archive_abs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, archive_abs)
        row = base_manifest_row(candidate, current_run)
        row.update(
            {
                "local_archive_path": str(archive_rel),
                "zip_path": output_path,
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "download_method": "cache_snapshot",
                "status": "snapshot",
                "attempted_methods": "cache_snapshot",
            }
        )
        upsert_manifest(conn, row)
        added += 1
    return added


def csv_safe_manifest(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "group_name": row["group_name"],
        "open_conversation_id": mask(row["open_conversation_id"]),
        "message_id": mask(row["open_message_id"]),
        "message_time": row["message_time"] or "",
        "sender_name": row["sender_name"] or "",
        "sender_id": mask(row["sender_id"]),
        "msg_type": row["msg_type"] or "",
        "resource_type": row["resource_type"] or "",
        "resource_id": mask(row["resource_id"]),
        "original_filename": row["original_filename"] or "",
        "local_archive_path": row["local_archive_path"] or "",
        "output_path": row["zip_path"] or "",
        "sha256": row["sha256"] or "",
        "size_bytes": row["size_bytes"] or 0,
        "download_method": row["download_method"] or "",
        "status": row["status"] or "",
        "error_reason": row["error_reason"] or "",
        "attempt_count": row["attempt_count"] or 0,
        "first_failed_at": row["first_failed_at"] or "",
        "last_failed_at": row["last_failed_at"] or "",
        "dws_error_code": row["dws_error_code"] or "",
        "error_summary": row["error_summary"] or "",
        "next_action": row["next_action"] or "",
        "exhausted": int(row["exhausted"] or 0),
        "storage_tier": row["storage_tier"] or "hot",
        "cold_archive_path": row["cold_archive_path"] or "",
        "cold_archive_inner_path": row["cold_archive_inner_path"] or "",
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def chat_record_rows(
    group: dict[str, Any],
    messages: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_message: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_message.setdefault(candidate.get("open_message_id", ""), []).append(candidate)
    rows: list[dict[str, Any]] = []
    for msg in messages:
        msg_id = msg.get("openMessageId", "")
        quoted = msg.get("quotedMessage") if isinstance(msg.get("quotedMessage"), dict) else {}
        resources = by_message.get(msg_id, [])
        rows.append(
            {
                "group_name": group["canonical_name"],
                "open_conversation_id": mask(group["open_conversation_id"]),
                "open_message_id": mask(msg_id),
                "message_time": msg.get("createTime", ""),
                "sender_name": msg.get("sender", ""),
                "sender_id": mask(msg.get("senderOpenDingTalkId", "")),
                "content": msg.get("content", ""),
                "quoted_message_id": mask(quoted.get("openMessageId", "")) if quoted else "",
                "quoted_sender": quoted.get("sender", "") if quoted else "",
                "quoted_content": quoted.get("content", "") if quoted else "",
                "resource_count": len(resources),
                "resource_types": ",".join(sorted({r.get("resource_type", "unknown") for r in resources})),
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def upsert_messages(
    conn: sqlite3.Connection,
    group: dict[str, Any],
    messages: list[dict[str, Any]],
    current_run: str,
) -> None:
    for msg in messages:
        msg_id = msg.get("openMessageId", "")
        if not msg_id:
            continue
        quoted = msg.get("quotedMessage") if isinstance(msg.get("quotedMessage"), dict) else {}
        reactions = msg.get("reactions") or msg.get("emotionReplyList") or []
        conn.execute(
            """
            INSERT INTO messages (
                group_name, open_conversation_id, open_message_id, message_time,
                sender_name, sender_id, msg_type, content, quoted_message_json,
                reactions_json, raw_json, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_name, open_message_id) DO UPDATE SET
                open_conversation_id = excluded.open_conversation_id,
                message_time = excluded.message_time,
                sender_name = excluded.sender_name,
                sender_id = excluded.sender_id,
                msg_type = excluded.msg_type,
                content = excluded.content,
                quoted_message_json = excluded.quoted_message_json,
                reactions_json = excluded.reactions_json,
                raw_json = excluded.raw_json,
                archived_at = excluded.archived_at
            """,
            (
                group["canonical_name"],
                group["open_conversation_id"],
                msg_id,
                msg.get("createTime", ""),
                msg.get("sender", ""),
                msg.get("senderOpenDingTalkId", ""),
                msg.get("msgType", ""),
                msg.get("content", "") or "",
                json.dumps(quoted, ensure_ascii=False, sort_keys=True),
                json.dumps(reactions, ensure_ascii=False, sort_keys=True),
                json.dumps(msg, ensure_ascii=False, sort_keys=True),
                current_run,
            ),
        )


def import_existing_chat_records(conn: sqlite3.Connection, config: dict[str, Any], current_run: str) -> int:
    imported = 0
    for group in enabled_groups(config):
        path = CHAT_RECORDS / safe_name(group["canonical_name"]) / "raw_messages.jsonl"
        if not path.is_file():
            continue
        messages: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    messages.append(value)
        if messages:
            group_for_store = dict(group)
            group_for_store.setdefault("open_conversation_id", group.get("open_conversation_id", ""))
            upsert_messages(conn, group_for_store, messages, current_run)
            imported += len(messages)
    return imported


def seed_missing_group_cursors_from_messages(
    conn: sqlite3.Connection,
    config: dict[str, Any],
    current_run: str,
    dws_version: str,
) -> int:
    seeded = 0
    for group in enabled_groups(config):
        if get_group_cursor(conn, group["canonical_name"]):
            continue
        row = conn.execute(
            """
            SELECT MAX(message_time) AS last_message_time
            FROM messages
            WHERE group_name = ? AND message_time IS NOT NULL AND message_time != ''
            """,
            (group["canonical_name"],),
        ).fetchone()
        last_message_time = row[0] if row else ""
        if not last_message_time:
            continue
        conn.execute(
            """
            INSERT INTO group_cursors (
                group_name, group_type, scan_mode, last_success_run_id,
                last_success_cursor_time, last_message_time_seen, completion_boundary,
                dws_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group["canonical_name"],
                group.get("group_type", "standing"),
                group.get("scan_mode", "auto"),
                f"seed_from_existing_messages:{current_run}",
                last_message_time,
                last_message_time,
                "seeded_from_existing_raw_messages",
                dws_version,
                now(),
            ),
        )
        seeded += 1
    return seeded


def repair_empty_cursor_last_message_times(conn: sqlite3.Connection) -> int:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT c.group_name, MAX(m.message_time) AS last_message_time
        FROM group_cursors c
        JOIN messages m ON m.group_name = c.group_name
        WHERE COALESCE(c.last_message_time_seen, '') = ''
          AND COALESCE(m.message_time, '') != ''
        GROUP BY c.group_name
        """
    ).fetchall()
    repaired = 0
    for row in rows:
        conn.execute(
            """
            UPDATE group_cursors
            SET last_message_time_seen = ?, updated_at = ?
            WHERE group_name = ? AND COALESCE(last_message_time_seen, '') = ''
            """,
            (row["last_message_time"], now(), row["group_name"]),
        )
        repaired += 1
    return repaired


def stored_message_rows(conn: sqlite3.Connection, group_name: str, cutoff: dt.datetime) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cutoff_text = format_message_time(cutoff)
    return conn.execute(
        """
        SELECT * FROM messages
        WHERE group_name = ? AND (message_time IS NULL OR message_time = '' OR message_time >= ?)
        ORDER BY message_time, open_message_id
        """,
        (group_name, cutoff_text),
    ).fetchall()


def chat_record_rows_from_store(
    group: dict[str, Any],
    message_rows: list[sqlite3.Row],
    manifest_rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:
    resources_by_message: dict[str, list[sqlite3.Row]] = {}
    for row in manifest_rows:
        resources_by_message.setdefault(row["open_message_id"], []).append(row)
    rows: list[dict[str, Any]] = []
    for row in message_rows:
        quoted = {}
        if row["quoted_message_json"]:
            try:
                quoted = json.loads(row["quoted_message_json"])
            except json.JSONDecodeError:
                quoted = {}
        resources = resources_by_message.get(row["open_message_id"], [])
        rows.append(
            {
                "group_name": group["canonical_name"],
                "open_conversation_id": mask(row["open_conversation_id"]),
                "open_message_id": mask(row["open_message_id"]),
                "message_time": row["message_time"] or "",
                "sender_name": row["sender_name"] or "",
                "sender_id": mask(row["sender_id"] or ""),
                "content": row["content"] or "",
                "quoted_message_id": mask(quoted.get("openMessageId", "")) if quoted else "",
                "quoted_sender": quoted.get("sender", "") if quoted else "",
                "quoted_content": quoted.get("content", "") if quoted else "",
                "resource_count": len(resources),
                "resource_types": ",".join(sorted({r["resource_type"] or "unknown" for r in resources})),
            }
        )
    return rows


def recent_file_analysis_rows(rows: list[sqlite3.Row], days: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cutoff = dt.datetime.now().astimezone() - dt.timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for row in rows:
        if row["status"] not in {"downloaded", "duplicate", "snapshot"}:
            continue
        parsed_time = parse_message_time(row["message_time"] or "")
        if parsed_time is None or parsed_time < cutoff:
            continue
        original = row["original_filename"] or Path(row["zip_path"] or "").name
        normalized = normalize_filename(original)
        similar = similarity_key(original)
        recent.append(
            {
                "group_name": row["group_name"],
                "message_time": row["message_time"] or "",
                "sender_name": row["sender_name"] or "",
                "message_id": mask(row["open_message_id"]),
                "resource_type": row["resource_type"] or "",
                "original_filename": original,
                "normalized_filename": normalized,
                "similarity_key": similar,
                "sha256": row["sha256"] or "",
                "size_bytes": row["size_bytes"] or 0,
                "status": row["status"] or "",
                "download_method": row["download_method"] or "",
                "output_path": row["zip_path"] or "",
            }
        )

    by_name: dict[str, int] = {}
    by_similar: dict[str, int] = {}
    by_sha: dict[str, int] = {}
    for item in recent:
        by_name[item["normalized_filename"]] = by_name.get(item["normalized_filename"], 0) + 1
        by_similar[item["similarity_key"]] = by_similar.get(item["similarity_key"], 0) + 1
        if item["sha256"]:
            by_sha[item["sha256"]] = by_sha.get(item["sha256"], 0) + 1

    similar_rows: list[dict[str, Any]] = []
    for item in recent:
        reasons: list[str] = []
        same_name = by_name.get(item["normalized_filename"], 0)
        same_similar = by_similar.get(item["similarity_key"], 0)
        same_sha = by_sha.get(item["sha256"], 0) if item["sha256"] else 0
        if same_name > 1:
            reasons.append("same_normalized_filename")
        if same_similar > 1:
            reasons.append("similar_filename_key")
        if same_sha > 1:
            reasons.append("same_sha256")
        if not reasons:
            continue
        similar_rows.append(
            {
                **item,
                "same_normalized_filename_count": same_name,
                "same_similarity_key_count": same_similar,
                "same_sha256_count": same_sha,
                "similarity_reason": ",".join(reasons),
            }
        )
    return recent, similar_rows


def copy_chat_records_into_output_dir(
    group: dict[str, Any],
    messages: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    rows = chat_record_rows(group, messages, candidates)
    project_dir = CHAT_RECORDS / safe_name(group["canonical_name"])
    csv_path = project_dir / "chat_records.csv"
    jsonl_path = project_dir / "chat_records.jsonl"
    raw_jsonl_path = project_dir / "raw_messages.jsonl"
    write_csv(csv_path, CHAT_RECORD_FIELDS, rows)
    write_jsonl(jsonl_path, rows)
    write_jsonl(raw_jsonl_path, messages)

    output_chat_dir = output_dir / "chat_records"
    output_chat_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(csv_path, output_chat_dir / "chat_records.csv")
    shutil.copy2(jsonl_path, output_chat_dir / "chat_records.jsonl")
    shutil.copy2(raw_jsonl_path, output_chat_dir / "raw_messages.jsonl")

    file_rows: list[dict[str, Any]] = []
    for role, path, output_path in [
        ("chat_records_csv", output_chat_dir / "chat_records.csv", "chat_records/chat_records.csv"),
        ("chat_records_jsonl", output_chat_dir / "chat_records.jsonl", "chat_records/chat_records.jsonl"),
        ("raw_messages_jsonl", output_chat_dir / "raw_messages.jsonl", "chat_records/raw_messages.jsonl"),
    ]:
        file_rows.append(
            {
                "group_name": group["canonical_name"],
                "file_role": role,
                "output_path": output_path,
                "record_count": len(rows),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return file_rows


def copy_stored_chat_records_into_output_dir(
    group: dict[str, Any],
    message_rows: list[sqlite3.Row],
    manifest_rows: list[sqlite3.Row],
    output_dir: Path,
) -> list[dict[str, Any]]:
    rows = chat_record_rows_from_store(group, message_rows, manifest_rows)
    raw_messages: list[dict[str, Any]] = []
    for row in message_rows:
        try:
            raw_messages.append(json.loads(row["raw_json"]))
        except (TypeError, json.JSONDecodeError):
            raw_messages.append(
                {
                    "openMessageId": row["open_message_id"],
                    "createTime": row["message_time"],
                    "sender": row["sender_name"],
                    "content": row["content"],
                }
            )

    project_dir = CHAT_RECORDS / safe_name(group["canonical_name"])
    csv_path = project_dir / "chat_records.csv"
    jsonl_path = project_dir / "chat_records.jsonl"
    raw_jsonl_path = project_dir / "raw_messages.jsonl"
    write_csv(csv_path, CHAT_RECORD_FIELDS, rows)
    write_jsonl(jsonl_path, rows)
    write_jsonl(raw_jsonl_path, raw_messages)

    output_chat_dir = output_dir / "chat_records"
    output_chat_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(csv_path, output_chat_dir / "chat_records.csv")
    shutil.copy2(jsonl_path, output_chat_dir / "chat_records.jsonl")
    shutil.copy2(raw_jsonl_path, output_chat_dir / "raw_messages.jsonl")

    file_rows: list[dict[str, Any]] = []
    for role, path, output_path in [
        ("chat_records_csv", output_chat_dir / "chat_records.csv", "chat_records/chat_records.csv"),
        ("chat_records_jsonl", output_chat_dir / "chat_records.jsonl", "chat_records/chat_records.jsonl"),
        ("raw_messages_jsonl", output_chat_dir / "raw_messages.jsonl", "chat_records/raw_messages.jsonl"),
    ]:
        file_rows.append(
            {
                "group_name": group["canonical_name"],
                "file_role": role,
                "output_path": output_path,
                "record_count": len(rows),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return file_rows


def group_rows(conn: sqlite3.Connection, group_name: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT * FROM manifest
        WHERE group_name = ?
        ORDER BY message_time, open_message_id, resource_type, resource_id
        """,
        (group_name,),
    ).fetchall()


def output_path_from_local_archive(local_archive_path: str, message_time: str) -> str:
    _year, month, _day = normalized_message_day(message_time or "")
    return str(Path("files") / month / Path(local_archive_path).name)


def normalize_group_output_paths(conn: sqlite3.Connection, group_name: str) -> int:
    changed = 0
    for row in group_rows(conn, group_name):
        if row["status"] not in {"downloaded", "duplicate", "snapshot"}:
            continue
        if not row["local_archive_path"]:
            continue
        output_path = output_path_from_local_archive(row["local_archive_path"], row["message_time"] or "")
        if row["zip_path"] == output_path:
            continue
        conn.execute(
            """
            UPDATE manifest
            SET zip_path = ?
            WHERE group_name = ? AND open_message_id = ? AND resource_type = ? AND resource_id = ?
            """,
            (output_path, row["group_name"], row["open_message_id"], row["resource_type"], row["resource_id"]),
        )
        changed += 1
    return changed


def group_rows_for_output(conn: sqlite3.Connection, group_name: str, cutoff: dt.datetime) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cutoff_text = format_message_time(cutoff)
    return conn.execute(
        """
        SELECT * FROM manifest
        WHERE group_name = ?
          AND (message_time IS NULL OR message_time = '' OR message_time >= ?)
          AND COALESCE(storage_tier, 'hot') = 'hot'
        ORDER BY message_time, open_message_id, resource_type, resource_id
        """,
        (group_name, cutoff_text),
    ).fetchall()


def cold_storage_inner_path(group_name: str, local_archive_path: str, message_time: str) -> str:
    return str(Path(group_name) / output_path_from_local_archive(local_archive_path, message_time or ""))


def cold_storage_file_for(cold_root: Path, group_name: str, local_archive_path: str, message_time: str) -> Path:
    return cold_root / cold_storage_inner_path(group_name, local_archive_path, message_time)


def migrate_cold_files(
    conn: sqlite3.Connection,
    group_name: str,
    cutoff: dt.datetime,
    cold_root: Path,
) -> dict[str, Any]:
    rows = [
        row
        for row in group_rows(conn, group_name)
        if row["status"] in {"downloaded", "duplicate", "snapshot"}
        and row["local_archive_path"]
        and is_hot_message_time(row["message_time"] or "", cutoff) is False
        and (row["storage_tier"] or "hot") != "cold"
    ]
    by_local: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_local.setdefault(row["local_archive_path"], []).append(row)

    migrated_files = 0
    migrated_bytes = 0
    missing_local = 0
    cold_storage_paths: set[str] = set()
    for local_rel, local_rows in by_local.items():
        src = ROOT / local_rel
        first = local_rows[0]
        inner_path = cold_storage_inner_path(first["group_name"], local_rel, first["message_time"] or "")
        cold_file_path = cold_root / inner_path
        cold_file_path.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            size = src.stat().st_size
            if cold_file_path.exists():
                if cold_file_path.stat().st_size != size or sha256_file(cold_file_path) != sha256_file(src):
                    raise RuntimeError(f"cold storage collision: {cold_file_path}")
            else:
                shutil.copy2(src, cold_file_path)
            if not cold_file_path.is_file():
                raise RuntimeError(f"cold storage missing migrated file: {cold_file_path}")
            if cold_file_path.stat().st_size != size or sha256_file(cold_file_path) != sha256_file(src):
                raise RuntimeError(f"cold storage verification failed: {cold_file_path}")
            src.unlink()
            migrated_files += 1
            migrated_bytes += size
            cold_storage_paths.add(str(cold_root / first["group_name"]))
        else:
            missing_local += 1
            if not cold_file_path.exists():
                continue
        for row in local_rows:
            conn.execute(
                """
                UPDATE manifest
                SET storage_tier = 'cold',
                    cold_archive_path = ?,
                    cold_archive_inner_path = ?,
                    zip_path = ?
                WHERE group_name = ? AND open_message_id = ? AND resource_type = ? AND resource_id = ?
                """,
                (
                    str(cold_file_path),
                    inner_path,
                    output_path_from_local_archive(local_rel, row["message_time"] or ""),
                    row["group_name"],
                    row["open_message_id"],
                    row["resource_type"],
                    row["resource_id"],
                ),
            )
    return {
        "cold_migrated_files": migrated_files,
        "cold_migrated_bytes": migrated_bytes,
        "cold_missing_local_files": missing_local,
        "cold_storage_paths": sorted(cold_storage_paths),
    }


def normalize_existing_cold_storage_layout(conn: sqlite3.Connection, cold_root: Path) -> dict[str, Any]:
    stats = {
        "cold_layout_moved_files": 0,
        "cold_layout_merged_duplicates": 0,
        "cold_layout_db_rows_updated": 0,
        "cold_layout_removed_ds_store": 0,
    }
    if not cold_root.exists():
        return stats

    for ds_store in sorted(cold_root.rglob(".DS_Store")):
        if ds_store.is_file():
            ds_store.unlink()
            stats["cold_layout_removed_ds_store"] += 1

    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT group_name, open_message_id, resource_type, resource_id, message_time,
               local_archive_path, cold_archive_path, cold_archive_inner_path
        FROM manifest
        WHERE COALESCE(storage_tier, 'hot') = 'cold'
          AND COALESCE(local_archive_path, '') != ''
        """
    ).fetchall()
    for row in rows:
        new_inner = cold_storage_inner_path(
            row["group_name"],
            row["local_archive_path"],
            row["message_time"] or "",
        )
        new_path = cold_root / new_inner
        old_candidates = []
        if row["cold_archive_path"]:
            old_candidates.append(Path(row["cold_archive_path"]))
        if row["cold_archive_inner_path"]:
            old_candidates.append(cold_root / row["cold_archive_inner_path"])
        old_path = next((path for path in old_candidates if path.exists()), None)
        if old_path and old_path != new_path:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            if new_path.exists():
                if sha256_file(new_path) != sha256_file(old_path):
                    raise RuntimeError(f"cold storage layout collision: {new_path}")
                old_path.unlink()
                stats["cold_layout_merged_duplicates"] += 1
            else:
                shutil.move(str(old_path), str(new_path))
                stats["cold_layout_moved_files"] += 1
        if row["cold_archive_path"] != str(new_path) or row["cold_archive_inner_path"] != new_inner:
            conn.execute(
                """
                UPDATE manifest
                SET cold_archive_path = ?, cold_archive_inner_path = ?, zip_path = ?
                WHERE group_name = ? AND open_message_id = ? AND resource_type = ? AND resource_id = ?
                """,
                (
                    str(new_path),
                    new_inner,
                    output_path_from_local_archive(row["local_archive_path"], row["message_time"] or ""),
                    row["group_name"],
                    row["open_message_id"],
                    row["resource_type"],
                    row["resource_id"],
                ),
            )
            stats["cold_layout_db_rows_updated"] += 1

    for files_root in sorted(cold_root.glob("*/files")):
        if not files_root.is_dir():
            continue
        for old_dir in sorted(path for path in files_root.iterdir() if path.is_dir()):
            if not (len(old_dir.name) == 4 and old_dir.name.isdigit()):
                continue
            month = old_dir.name[:2]
            target_dir = files_root / month
            target_dir.mkdir(parents=True, exist_ok=True)
            for child in sorted(old_dir.iterdir()):
                if not child.is_file():
                    continue
                target = target_dir / child.name
                if target.exists():
                    if sha256_file(target) == sha256_file(child):
                        child.unlink()
                        stats["cold_layout_merged_duplicates"] += 1
                    else:
                        stem = child.stem
                        suffix = child.suffix
                        target = target_dir / f"{stem}_migrated_{short_hash(str(child))}{suffix}"
                        shutil.move(str(child), str(target))
                        stats["cold_layout_moved_files"] += 1
                else:
                    shutil.move(str(child), str(target))
                    stats["cold_layout_moved_files"] += 1
            try:
                old_dir.rmdir()
            except OSError:
                pass
    return stats


def validate_group_output_dir(output_dir: Path, rows: list[sqlite3.Row], group_name: str) -> None:
    required = {
        "_manifest/manifest.csv",
        "_manifest/missing_media.csv",
        "_manifest/status.md",
        "_manifest/chat_record_files.csv",
        "_analysis/recent_30d_file_records.csv",
        "_analysis/similar_recent_30d.csv",
        "chat_records/chat_records.csv",
        "chat_records/chat_records.jsonl",
        "chat_records/raw_messages.jsonl",
    }
    missing = [rel for rel in sorted(required) if not (output_dir / rel).is_file()]
    if missing:
        raise RuntimeError(f"group output evidence missing for {group_name}: {', '.join(missing)}")

    legacy_zips = sorted(output_dir.glob("*_latest.zip"))
    if legacy_zips:
        raise RuntimeError(f"legacy per-group zip still exists for {group_name}: {legacy_zips[0].name}")

    successful_rows = [row for row in rows if row["status"] in {"downloaded", "duplicate", "snapshot"}]
    if not successful_rows:
        return

    files_dir = output_dir / "files"
    if not files_dir.is_dir():
        raise RuntimeError(f"files directory missing for {group_name}")
    month_dirs = sorted(path for path in files_dir.iterdir() if path.is_dir())
    invalid_month_dirs = [path for path in month_dirs if not _is_month_dir_name(path.name)]
    if invalid_month_dirs:
        raise RuntimeError(f"non-MM directory under files is not allowed for {group_name}: {invalid_month_dirs[0]}")
    direct_files = [path for month_dir in month_dirs for path in sorted(month_dir.iterdir())]
    if not any(path.is_file() for path in direct_files):
        raise RuntimeError(f"no direct files/MM files for {group_name}")
    nested_dirs = [path for path in direct_files if path.is_dir()]
    if nested_dirs:
        raise RuntimeError(f"nested directory under files/MM is not allowed for {group_name}: {nested_dirs[0]}")
    old_date_dirs = sorted(files_dir.glob("[12][0-9][0-9][0-9]/[0-1][0-9]/[0-3][0-9]"))
    if old_date_dirs:
        raise RuntimeError(f"legacy files/YYYY/MM/DD layout still exists for {group_name}: {old_date_dirs[0]}")


def _is_month_dir_name(value: str) -> bool:
    return len(value) == 2 and value.isdigit() and 1 <= int(value) <= 12


def publish_group_output_dir(staged_dir: Path, output_root: Path, group_name: str, current_run: str) -> Path:
    final_dir = output_root / group_name
    temp_dir = output_root / f".{safe_name(group_name)}.{current_run}.tmp"
    backup_dir = output_root / f".{safe_name(group_name)}.{current_run}.backup"
    output_root.mkdir(parents=True, exist_ok=True)
    for path in (temp_dir, backup_dir):
        if path.exists():
            shutil.rmtree(path)
    shutil.move(str(staged_dir), temp_dir)
    try:
        if final_dir.exists():
            final_dir.rename(backup_dir)
        temp_dir.rename(final_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception:
        if temp_dir.exists() and not final_dir.exists():
            temp_dir.rename(final_dir)
        if backup_dir.exists() and not final_dir.exists():
            backup_dir.rename(final_dir)
        raise
    return final_dir


def remove_legacy_group_zips(output_root: Path, group_names: list[str] | None = None) -> list[str]:
    removed: list[str] = []
    if not output_root.exists():
        return removed
    group_dirs = [output_root / name for name in group_names] if group_names else sorted(output_root.iterdir())
    for group_dir in group_dirs:
        if not group_dir.is_dir():
            continue
        for path in sorted(group_dir.glob("*_latest.zip")):
            if not path.is_file():
                continue
            path.unlink()
            removed.append(str(path))
    return removed


def write_group_output_dir(
    conn: sqlite3.Connection,
    group: dict[str, Any],
    output_root: Path,
    stats: dict[str, Any],
    current_run: str,
    config: dict[str, Any],
    cutoff: dt.datetime,
) -> Path:
    normalize_group_output_paths(conn, group["canonical_name"])
    rows = group_rows_for_output(conn, group["canonical_name"], cutoff)
    message_rows = stored_message_rows(conn, group["canonical_name"], cutoff)
    group_stage = STAGING / current_run / safe_name(group["canonical_name"])
    if group_stage.exists():
        shutil.rmtree(group_stage)
    recent_similarity_days = config_int(config, "recent_similarity_days", 30)

    (group_stage / "files").mkdir(parents=True, exist_ok=True)
    (group_stage / "_manifest").mkdir(parents=True, exist_ok=True)
    (group_stage / "_analysis").mkdir(parents=True, exist_ok=True)

    manifest_rows = [csv_safe_manifest(row) for row in rows]
    missing_rows = [
        {
            "group_name": row["group_name"],
            "message_id": mask(row["open_message_id"]),
            "message_time": row["message_time"] or "",
            "resource_type": row["resource_type"] or "",
            "resource_id": mask(row["resource_id"]),
            "attempted_methods": row["attempted_methods"] or "",
            "attempt_count": row["attempt_count"] or 0,
            "first_failed_at": row["first_failed_at"] or "",
            "last_failed_at": row["last_failed_at"] or "",
            "dws_error_code": row["dws_error_code"] or "",
            "error_summary": row["error_summary"] or "",
            "exhausted": int(row["exhausted"] or 0),
            "error_reason": row["error_reason"] or "",
            "next_action": row["next_action"] or "retry_with_dws_or_add_cache_snapshot",
        }
        for row in rows
        if row["status"] == "failed"
    ]

    copied: set[str] = set()
    for row in rows:
        if row["status"] not in {"downloaded", "duplicate", "snapshot"}:
            continue
        if not row["local_archive_path"] or not row["zip_path"]:
            continue
        src = ROOT / row["local_archive_path"]
        if not src.exists():
            continue
        dest = group_stage / row["zip_path"]
        if str(dest) in copied:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)
        copied.add(str(dest))

    status_md = render_group_status(group, stats, rows, current_run)
    chat_file_rows = copy_stored_chat_records_into_output_dir(group, message_rows, rows, group_stage)
    recent_rows, similar_rows = recent_file_analysis_rows(rows, recent_similarity_days)
    write_csv(group_stage / "_manifest" / "manifest.csv", MANIFEST_FIELDS, manifest_rows)
    write_csv(group_stage / "_manifest" / "missing_media.csv", MISSING_FIELDS, missing_rows)
    write_csv(group_stage / "_manifest" / "chat_record_files.csv", CHAT_RECORD_FILE_FIELDS, chat_file_rows)
    write_csv(group_stage / "_analysis" / "recent_30d_file_records.csv", RECENT_FILE_RECORD_FIELDS, recent_rows)
    write_csv(group_stage / "_analysis" / "similar_recent_30d.csv", SIMILAR_FILE_RECORD_FIELDS, similar_rows)
    (group_stage / "_manifest" / "status.md").write_text(status_md, encoding="utf-8")

    validate_group_output_dir(group_stage, rows, group["canonical_name"])
    final_dir = publish_group_output_dir(group_stage, output_root, group["canonical_name"], current_run)
    validate_group_output_dir(final_dir, rows, group["canonical_name"])
    return final_dir


def publish_skipped_group_output(
    conn: sqlite3.Connection,
    group: dict[str, Any],
    output_root: Path,
    current_run: str,
    config: dict[str, Any],
    cutoff: dt.datetime,
) -> dict[str, Any]:
    cursor = get_group_cursor(conn, group["canonical_name"])
    message_rows = stored_message_rows(conn, group["canonical_name"], cutoff)
    rows = group_rows_for_output(conn, group["canonical_name"], cutoff)
    stats: dict[str, Any] = {
        "unique_resolved": None,
        "resolved_title": group["canonical_name"],
        "member_count": "",
        "group_type": group.get("group_type", "standing"),
        "scan_mode": group.get("scan_mode", "auto"),
        "effective_scan_mode": effective_scan_mode(group),
        "manual_specified": False,
        "action": "跳过并重建历史输出",
        "cursor_start": "",
        "cursor_source": "skipped_group_history",
        "previous_last_success_cursor_time": cursor["last_success_cursor_time"] if cursor else "",
        "previous_last_message_time_seen": cursor["last_message_time_seen"] if cursor else "",
        "cursor_end": cursor["last_success_cursor_time"] if cursor else "",
        "messages_scanned": 0,
        "message_pages_scanned": 0,
        "message_scan_exhausted": False,
        "message_scan_stop_reason": "skipped_manual_or_not_selected",
        "message_scan_last_cursor_time": cursor["last_success_cursor_time"] if cursor else "",
        "last_message_time_seen": cursor["last_message_time_seen"] if cursor else "",
        "message_completion_boundary": cursor["completion_boundary"] if cursor else "",
        "chat_records_saved": len(message_rows),
        "resources_found": 0,
        "resources_by_type": {},
        "downloaded": 0,
        "duplicate": 0,
        "failed": sum(1 for row in rows if row["status"] == "failed"),
        "exhausted": sum(1 for row in rows if row["exhausted"]),
        "snapshot": 0,
        "skipped_output_rebuilt": True,
    }
    output_dir = write_group_output_dir(conn, group, output_root, stats, current_run, config, cutoff)
    stats["output_dir"] = str(output_dir)
    stats["output_layout"] = "group_directory_files_MM"
    stats["output_no_group_zip"] = not any(output_dir.glob("*_latest.zip"))
    stats["snapshots_dir"] = str(SNAPSHOTS / group["canonical_name"])
    return stats


def mirror_output_tree_to_archive(output_root: Path, archive_path: Path) -> Path:
    if not output_root.is_dir():
        raise RuntimeError(f"missing output root for mirror: {output_root}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_archive = archive_path.with_name(f"{archive_path.name}.tmp")
    if tmp_archive.exists():
        tmp_archive.unlink()
    old_tree = archive_path.with_suffix("")
    if old_tree.exists() and old_tree.is_dir():
        shutil.rmtree(old_tree)
    with zipfile.ZipFile(tmp_archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(p for p in output_root.rglob("*") if p.is_file()):
            zf.write(file_path, output_root.name / file_path.relative_to(output_root))
    if tmp_archive.stat().st_size <= 0:
        raise RuntimeError(f"empty mirror archive generated: {archive_path}")
    with zipfile.ZipFile(tmp_archive) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"mirror archive integrity failed: {bad}")
        names = zf.namelist()
        legacy = [name for name in names if name.endswith("_latest.zip")]
        if legacy:
            raise RuntimeError(f"mirror archive contains legacy per-group zip: {legacy[0]}")
        forbidden = [
            name
            for name in names
            if any(part in FORBIDDEN_MIRROR_PARTS for part in Path(name).parts)
        ]
        if forbidden:
            raise RuntimeError(f"mirror archive contains skill/config backup: {forbidden[0]}")
    os.replace(tmp_archive, archive_path)
    return archive_path


def validate_existing_mirror_archive(archive_path: Path) -> None:
    if not archive_path.is_file():
        raise RuntimeError(f"missing mirror archive: {archive_path}")
    with zipfile.ZipFile(archive_path) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"mirror archive integrity failed: {bad}")
        names = zf.namelist()
        legacy = [name for name in names if name.endswith("_latest.zip")]
        if legacy:
            raise RuntimeError(f"mirror archive contains legacy per-group zip: {legacy[0]}")
        forbidden = [
            name
            for name in names
            if any(part in FORBIDDEN_MIRROR_PARTS for part in Path(name).parts)
        ]
        if forbidden:
            raise RuntimeError(f"mirror archive contains skill/config backup: {forbidden[0]}")


def path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def has_other_archive_process() -> bool:
    proc = subprocess.run(
        ["ps", "-axo", "pid,command"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return True
    current_pid = os.getpid()
    for line in proc.stdout.splitlines():
        if "archive_dingtalk_all_files.py" not in line:
            continue
        parts = line.strip().split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid != current_pid:
            return True
    return False


def cleanup_stale_staging(ttl_hours: int) -> dict[str, Any]:
    if has_other_archive_process():
        return {"staging_cleanup_skipped": True, "staging_cleanup_reason": "archive_process_running"}
    cutoff = dt.datetime.now().astimezone().timestamp() - ttl_hours * 3600
    removed = 0
    bytes_removed = 0
    STAGING.mkdir(parents=True, exist_ok=True)
    for path in sorted(STAGING.iterdir()):
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            continue
        if mtime >= cutoff:
            continue
        size = path_size_bytes(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed += 1
        bytes_removed += size
    return {
        "staging_cleanup_skipped": False,
        "staging_removed_items": removed,
        "staging_removed_bytes": bytes_removed,
    }


def write_log_rotation_pending(retention_days: int) -> dict[str, Any]:
    cutoff = dt.datetime.now().astimezone().timestamp() - retention_days * 86400
    old_logs = []
    if LOGS.exists():
        for path in sorted(LOGS.rglob("*")):
            if path.is_file() and path.stat().st_mtime < cutoff:
                old_logs.append(path)
    if not old_logs:
        return {"old_logs_found": 0, "old_logs_deleted": 0, "log_rotation_pending": ""}
    total_bytes = sum(path.stat().st_size for path in old_logs)
    pending = REPORTS / "log_rotation_notion_pending.md"
    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 钉钉DWS归档旧日志摘要待同步",
        "",
        f"- generated_at: {now()}",
        f"- retention_days: {retention_days}",
        f"- old_log_count: {len(old_logs)}",
        f"- old_log_bytes: {total_bytes}",
        "",
        "旧日志需先同步到 Notion 后才能删除。本摘要不含 token、open_conversation_id、完整 resource_id、cookie 或账号敏感信息。",
        "",
        "## 文件清单",
    ]
    for path in old_logs[:200]:
        lines.append(f"- `{path.relative_to(ROOT)}` bytes={path.stat().st_size}")
    pending.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "old_logs_found": len(old_logs),
        "old_logs_deleted": 0,
        "log_rotation_pending": str(pending),
    }


def remove_temp_downloads_output_after_mirror(output_root: Path, mirror_archive: Path) -> dict[str, Any]:
    validate_existing_mirror_archive(mirror_archive)
    if output_root.exists() and not output_root.is_dir():
        raise RuntimeError(f"refuse to remove non-directory output root: {output_root}")
    if output_root.is_dir():
        shutil.rmtree(output_root)
    return {
        "downloads_temp_output_removed": True,
        "local_downloads_output_path": str(output_root),
        "downloads_temp_output_removed_at": now(),
        "downloads_temp_output_remove_reason": "verified_onedrive_current_package",
        "mirror_archive_path": str(mirror_archive),
    }


def render_group_status(group: dict[str, Any], stats: dict[str, Any], rows: list[sqlite3.Row], current_run: str) -> str:
    failed = sum(1 for row in rows if row["status"] == "failed")
    success = sum(1 for row in rows if row["status"] in {"downloaded", "duplicate", "snapshot"})
    lines = [
        f"# {group['canonical_name']} DWS all-files archive status",
        "",
        f"- run_id: {current_run}",
        f"- generated_at: {now()}",
        f"- group_resolved: {group.get('resolved_title', group['canonical_name'])}",
        f"- group_type: {group.get('group_type', 'standing')}",
        f"- scan_mode: {group.get('scan_mode', 'auto')}",
        f"- effective_scan_mode: {effective_scan_mode(group)}",
        f"- member_count: {group.get('member_count', '')}",
        f"- messages_scanned_this_run: {stats.get('messages_scanned', 0)}",
        f"- message_pages_scanned: {stats.get('message_pages_scanned', 0)}",
        f"- message_scan_exhausted: {stats.get('message_scan_exhausted', False)}",
        f"- message_scan_stop_reason: {stats.get('message_scan_stop_reason', '')}",
        f"- message_scan_last_cursor_time: {stats.get('message_scan_last_cursor_time', '')}",
        f"- message_completion_boundary: {stats.get('message_completion_boundary', '')}",
        f"- chat_records_saved_this_run: {stats.get('chat_records_saved', 0)}",
        f"- resources_found_this_run: {stats.get('resources_found', 0)}",
        f"- cumulative_success_resources: {success}",
        f"- cumulative_failed_resources: {failed}",
        f"- output_layout: group_directory_files_MM",
        f"- per_group_latest_zip: false",
        f"- project_auto_completion_checked: {stats.get('project_auto_completion', {}).get('checked', False)}",
        f"- project_auto_completed: {stats.get('auto_completed_project', False)}",
        f"- project_completed_at: {stats.get('completed_at', '')}",
        f"- project_completion_reason: {stats.get('completion_reason', '')}",
        "",
        "## Resource Types This Run",
    ]
    for key, value in sorted(stats.get("resources_by_type", {}).items()):
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Download Result This Run",
        f"- downloaded: {stats.get('downloaded', 0)}",
        f"- duplicate: {stats.get('duplicate', 0)}",
        f"- failed: {stats.get('failed', 0)}",
        f"- snapshot: {stats.get('snapshot', 0)}",
    ]
    return "\n".join(lines) + "\n"


def write_project_reports(summary: dict[str, Any], conn: sqlite3.Connection) -> None:
    missing_rows: list[dict[str, Any]] = []
    for group_name, stats in summary["groups"].items():
        for row in group_rows(conn, group_name):
            if row["status"] == "failed":
                missing_rows.append(
                    {
                        "group_name": row["group_name"],
                        "message_id": mask(row["open_message_id"]),
                        "message_time": row["message_time"] or "",
                        "resource_type": row["resource_type"] or "",
                        "resource_id": mask(row["resource_id"]),
                        "attempted_methods": row["attempted_methods"] or "",
                        "attempt_count": row["attempt_count"] or 0,
                        "first_failed_at": row["first_failed_at"] or "",
                        "last_failed_at": row["last_failed_at"] or "",
                        "dws_error_code": row["dws_error_code"] or "",
                        "error_summary": row["error_summary"] or "",
                        "exhausted": int(row["exhausted"] or 0),
                        "error_reason": row["error_reason"] or "",
                        "next_action": row["next_action"] or "retry_with_dws_or_add_cache_snapshot",
                    }
                )
    summary["missing_total"] = len(missing_rows)
    summary["exhausted_total"] = sum(1 for row in missing_rows if row.get("exhausted"))
    report_lines = render_human_report(summary)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "daily_report.md").write_text(report_lines, encoding="utf-8")
    (REPORTS / "daily_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (REPORTS / "status.md").write_text(render_project_status(summary), encoding="utf-8")
    write_csv(PROJECT_MISSING, MISSING_FIELDS, missing_rows)


def render_human_report(summary: dict[str, Any]) -> str:
    success = summary.get("success", False)
    partial = bool(summary.get("error"))
    conclusion = "完成" if success and not partial else ("部分完成" if summary.get("groups") else "失败")
    lines = [
        "# 钉钉DWS全文件原始数据归档报告",
        "",
        "## 1. 本次结论",
        f"- 结论：{conclusion}",
        f"- 是否生成 OneDrive 当前包：{'是' if summary.get('mirror_archive_path') else '否'}",
        f"- 是否删除 Downloads 临时输出：{'是' if summary.get('downloads_temp_output_removed') else '否'}",
        f"- 是否有冷存储迁移：{'是' if summary.get('cold_migrated_files_total', 0) else '否'}",
        f"- 是否有资源超过 3 次失败：{'是' if summary.get('exhausted_total', 0) else '否'}",
        f"- 是否有项目群自动完工转 manual_only：{'是' if summary.get('auto_completed_project_groups') else '否'}",
        "",
        "## 2. 本次运行方式",
        f"- 运行方式：{summary.get('run_source', '')}",
        f"- automation 名称：{summary.get('automation_name', '')}",
        f"- 运行时间：{summary.get('run_started', '')} 至 {summary.get('run_ended', '')}",
        f"- run_id：{summary.get('run_id', '')}",
        f"- DWS version：{summary.get('dws_version', '')}",
        "",
        "## 3. 本次处理群聊清单",
        "| 群名 | 类型 | scan_mode | 本次动作 | cursor 起点 | cursor 终点 | 说明 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    stats_by_group = summary.get("groups", {})
    for row in summary.get("run_plan", []):
        stats = stats_by_group.get(row["group_name"], {})
        note = row.get("risk", "")
        if stats.get("auto_completed_project"):
            note = (
                f"连续 {stats.get('project_auto_completion', {}).get('idle_days_required', DEFAULT_PROJECT_IDLE_COMPLETION_DAYS)} "
                f"天无新增消息/文件，已自动转 manual_only；完工时间 {stats.get('completed_at', '')}"
            )
        lines.append(
            f"| {row['group_name']} | {row['group_type_label']} | {row['scan_mode']} | {stats.get('action', row['action'])} | "
            f"{stats.get('cursor_start', row.get('cursor_start', ''))} | {stats.get('cursor_end', '')} | {note} |"
        )
    lines += [
        "",
        "## 4. 下载结果",
        "| 群名 | 新下载 | 复用 | 失败 | 超过 3 次不再重试 | missing 数量 | 是否需要人工处理 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for group_name, stats in stats_by_group.items():
        missing = int(stats.get("failed", 0))
        exhausted = int(stats.get("exhausted", 0))
        lines.append(
            f"| {group_name} | {stats.get('downloaded', 0)} | {stats.get('duplicate', 0)} | {stats.get('failed', 0)} | "
            f"{exhausted} | {missing} | {'是' if missing else '否'} |"
        )
    lines += [
        "",
        "## 5. 存储结果",
        "| 项目 | 结果 |",
        "| --- | --- |",
        f"| 当前热存储窗口 | 最近 {summary.get('hot_storage_days', DEFAULT_HOT_STORAGE_DAYS)} 天 |",
        f"| 冷存储范围 | 60 天及以上 |",
        f"| 当前 DWS_Outputs.zip 大小 | {summary.get('mirror_archive_size_bytes', 0)} bytes |",
        f"| DWS_Archive 冷存储新增大小 | {summary.get('cold_migrated_bytes_total', 0)} bytes |",
        f"| 本机 data/archive 前后大小 | {summary.get('data_archive_size_before', 0)} -> {summary.get('data_archive_size_after', 0)} bytes |",
        f"| staging 清理大小 | {summary.get('staging_removed_bytes', 0)} bytes |",
        f"| Downloads 临时输出是否已删除 | {'是' if summary.get('downloads_temp_output_removed') else '否'} |",
        "",
        "## 6. 风险与阻塞",
    ]
    risks: list[str] = []
    if summary.get("error"):
        risks.append(f"运行错误：{summary['error']}")
    if summary.get("missing_total", 0):
        risks.append(f"仍有 {summary.get('missing_total', 0)} 条 missing/exhausted 质量证据需要保留。")
    if summary.get("notion_pending"):
        risks.append(f"Notion 同步待处理：{summary['notion_pending']}")
    if not summary.get("downloads_temp_output_removed"):
        risks.append("Downloads 临时输出未删除，请先确认 OneDrive 当前包完整性。")
    if summary.get("auto_completed_project_groups"):
        risks.append(
            "本次有项目群因 7 天无新增消息/文件自动转为 manual_only；后续不会被 automation 主动扫描。"
        )
    if not risks:
        risks.append("未发现阻塞；DWS 后续仍可能对历史媒体返回超时或业务错误。")
    lines.extend(f"- {risk}" for risk in risks)
    lines += [
        "",
        "## 7. 推荐下一步",
        "- 保持 Codex automation 触发，不恢复本机 launchd 无人值守入口。",
        "- 对 exhausted 资源只在用户显式要求时手动补扫。",
        "- 项目群连续 7 天无新增消息/文件会自动记录最后消息时间为完工时间并转入 manual_only；如需继续追踪，请手动改回 auto 或显式补扫。",
        "",
        "## 8. 机器可读附录",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def render_project_status(summary: dict[str, Any]) -> str:
    lines = [
        "# 钉钉全文件归档状态",
        "",
        f"更新时间：{summary['run_ended']}",
        "",
        "## 当前结论",
        "- 当前只允许 Codex automation 或用户手动让 Codex 唤起脚本执行。",
        "- 当前包：OneDrive/DWS_Outputs.zip 只包含最近 60 天热数据。",
        "- 冷存储：60 天及以上文件本体进入 OneDrive/DWS_Archive/<群名>/files/MM/<文件>，无年份目录，无 zip；SQLite manifest 永久保留追溯字段。",
        "- Downloads/DWS_Outputs/ 是临时构建输出，OneDrive 当前包验证通过后删除。",
        "",
        "## 最近一次运行",
    ]
    lines += [
        "",
        "## OneDrive 当前包与临时输出",
        f"- mirror_archive_path: `{summary.get('mirror_archive_path', '')}`",
        f"- downloads_temp_output_removed: `{summary.get('downloads_temp_output_removed', False)}`",
        f"- local_downloads_output_path: `{summary.get('local_downloads_output_path', '')}`",
        f"- downloads_temp_output_removed_at: `{summary.get('downloads_temp_output_removed_at', '')}`",
        f"- downloads_temp_output_remove_reason: `{summary.get('downloads_temp_output_remove_reason', '')}`",
        f"- hot_storage_days: `{summary.get('hot_storage_days', DEFAULT_HOT_STORAGE_DAYS)}`",
        f"- cold_migrated_files_total: `{summary.get('cold_migrated_files_total', 0)}`",
        "",
    ]
    if summary.get("legacy_group_zips_removed"):
        lines += [
            "",
            "## 本次移除旧每群 zip",
            *(f"- `{path}`" for path in summary["legacy_group_zips_removed"]),
            "",
        ]
    for group_name, stats in summary["groups"].items():
        lines += [
            f"### {group_name}",
            f"- 扫描消息：{stats.get('messages_scanned', 0)}",
            f"- 保存聊天记录：{stats.get('chat_records_saved', 0)}",
            f"- 发现资源：{stats.get('resources_found', 0)}",
            f"- 新下载：{stats.get('downloaded', 0)}",
            f"- 去重/复用：{stats.get('duplicate', 0)}",
            f"- 失败：{stats.get('failed', 0)}",
            f"- 输出目录：`{stats.get('output_dir', '')}`",
            f"- 输出结构：`{stats.get('output_layout', '')}`",
            f"- 无每群 latest.zip：`{stats.get('output_no_group_zip', False)}`",
            f"- cursor 起点：`{stats.get('cursor_start', '')}`",
            f"- cursor 终点：`{stats.get('cursor_end', '')}`",
            f"- exhausted：`{stats.get('exhausted', 0)}`",
            "",
        ]
    return "\n".join(lines)


def collect_dws_version() -> str:
    proc = run_dws(["version"], timeout=30)
    if proc.returncode != 0:
        return "unknown"
    try:
        return parse_json_output(proc.stdout).get("version", "unknown")
    except Exception:
        return "unknown"


def group_type_label(group: dict[str, Any]) -> str:
    return "常驻" if group.get("group_type", "standing") == "standing" else "项目"


def run_action_for_group(group: dict[str, Any], requested: list[str] | None) -> str:
    if requested and group in selected_groups({"groups": enabled_groups({"groups": [group]})}, [group["canonical_name"]]):
        return "手动指定"
    if effective_scan_mode(group) == "manual_only":
        return "跳过"
    return "主动扫描"


def requested_names(requested: list[str] | None) -> set[str]:
    if not requested:
        return set()
    return {item.strip() for value in requested for item in value.split(",") if item.strip()}


def build_run_plan(
    conn: sqlite3.Connection,
    config: dict[str, Any],
    requested: list[str] | None,
    full_reconciliation: bool,
) -> list[dict[str, Any]]:
    wanted = requested_names(requested)
    selected = selected_groups(config, requested)
    selected_names = {group["canonical_name"] for group in selected}
    idle_days = project_idle_completion_days(config)
    rows: list[dict[str, Any]] = []
    for group in enabled_groups(config):
        mode = effective_scan_mode(group)
        manual = bool(wanted) and (group["canonical_name"] in selected_names or any(alias in wanted for alias in group.get("aliases", [])))
        action = "手动指定" if manual else ("主动扫描" if group["canonical_name"] in selected_names and mode != "manual_only" else "跳过")
        start, source = scan_start_for_group(conn, group, config, full_reconciliation)
        rows.append(
            {
                "group_name": group["canonical_name"],
                "group_type": group.get("group_type", "standing"),
                "group_type_label": group_type_label(group),
                "scan_mode": mode,
                "action": action,
                "cursor_start": start if action != "跳过" else "",
                "cursor_source": source if action != "跳过" else "",
                "risk": f"项目群 auto；若连续 {idle_days} 天无新增消息/文件，成功扫描后自动转 manual_only"
                if group.get("group_type") == "project" and mode == "auto" and not group.get("completed_date")
                else "",
            }
        )
    return rows


def render_preflight_report(summary: dict[str, Any]) -> str:
    lines = [
        "# 钉钉DWS归档运行前确认",
        "",
        f"- 运行方式：{summary.get('run_source', '')}",
        f"- automation：{summary.get('automation_name', '')}",
        f"- run_id：{summary.get('run_id', '')}",
        f"- 热存储窗口：最近 {summary.get('hot_storage_days', DEFAULT_HOT_STORAGE_DAYS)} 天",
        f"- 当前包：{summary.get('mirror_archive_path', '')}",
        "",
        "| 群名 | 类型 | scan_mode | 本次动作 | cursor 起点 | 说明 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary.get("run_plan", []):
        lines.append(
            "| {group_name} | {group_type_label} | {scan_mode} | {action} | {cursor_start} | {risk} |".format(
                **row
            )
        )
    risks = [row["risk"] for row in summary.get("run_plan", []) if row.get("risk")]
    lines += [
        "",
        "## 预计风险",
    ]
    if risks:
        lines.extend(f"- {risk}" for risk in sorted(set(risks)))
    else:
        lines.append("- 未发现配置级阻塞风险；DWS 单资源仍可能超时或返回业务错误。")
    return "\n".join(lines) + "\n"


def process_group(
    conn: sqlite3.Connection,
    config: dict[str, Any],
    group: dict[str, Any],
    output_root: Path,
    current_run: str,
    dws_version: str,
    cutoff: dt.datetime,
    cold_root: Path,
    probe_only: bool = False,
    full_reconciliation: bool = False,
    retry_exhausted: bool = False,
    manual_specified: bool = False,
) -> dict[str, Any]:
    write_heartbeat(current_run, "group_start", group_name=group["canonical_name"])
    resolved = resolve_group(group)
    previous_cursor = get_group_cursor(conn, resolved["canonical_name"])
    previous_last_success_cursor_time = previous_cursor["last_success_cursor_time"] if previous_cursor else ""
    previous_last_message_time_seen = previous_cursor["last_message_time_seen"] if previous_cursor else ""
    cursor_start, cursor_source = scan_start_for_group(conn, resolved, config, full_reconciliation)
    write_heartbeat(
        current_run,
        "group_resolved",
        group_name=resolved["canonical_name"],
        group_type=resolved.get("group_type", "standing"),
        scan_mode=resolved.get("scan_mode", "auto"),
        cursor_start=cursor_start,
        cursor_source=cursor_source,
    )

    def group_progress(event: str, **fields: Any) -> None:
        write_heartbeat(current_run, event, group_name=resolved["canonical_name"], **fields)

    messages, scan_stats = list_messages(resolved, config, cursor_start, progress_cb=group_progress)
    candidates: list[dict[str, Any]] = []
    for msg in messages:
        candidates.extend(extract_candidates_from_message(msg, resolved))
    max_failure_attempts = config_int(config, "max_failure_attempts", DEFAULT_MAX_FAILURE_ATTEMPTS)
    stats: dict[str, Any] = {
        "unique_resolved": True,
        "resolved_title": resolved.get("resolved_title"),
        "member_count": resolved.get("member_count"),
        "group_type": resolved.get("group_type", "standing"),
        "scan_mode": resolved.get("scan_mode", "auto"),
        "effective_scan_mode": effective_scan_mode(resolved),
        "manual_specified": manual_specified,
        "action": "手动指定" if manual_specified else "主动扫描",
        "cursor_start": cursor_start,
        "cursor_source": cursor_source,
        "previous_last_success_cursor_time": previous_last_success_cursor_time,
        "previous_last_message_time_seen": previous_last_message_time_seen,
        "cursor_end": "",
        "messages_scanned": len(messages),
        **scan_stats,
        "chat_records_saved": len(messages),
        "resources_found": len(candidates),
        "resources_by_type": {},
        "downloaded": 0,
        "duplicate": 0,
        "failed": 0,
        "exhausted": 0,
        "snapshot": 0,
    }
    write_heartbeat(
        current_run,
        "group_scan_complete",
        group_name=resolved["canonical_name"],
        messages_scanned=len(messages),
        resources_found=len(candidates),
        pages_scanned=scan_stats.get("message_pages_scanned", 0),
        completion_boundary=scan_stats.get("message_completion_boundary", ""),
    )
    heartbeat_interval = config_int(config, "heartbeat_resource_interval", DEFAULT_HEARTBEAT_RESOURCE_INTERVAL)
    for index, candidate in enumerate(candidates, start=1):
        stats["resources_by_type"][candidate["resource_type"]] = (
            stats["resources_by_type"].get(candidate["resource_type"], 0) + 1
        )
        if probe_only:
            continue
        if index == 1 or index % heartbeat_interval == 0 or index == len(candidates):
            write_heartbeat(
                current_run,
                "resource_progress",
                group_name=resolved["canonical_name"],
                resource_index=index,
                resources_total=len(candidates),
                downloaded=stats["downloaded"],
                duplicate=stats["duplicate"],
                failed=stats["failed"],
                exhausted=stats["exhausted"],
            )
        row = download_candidate(conn, candidate, current_run, max_failure_attempts, retry_exhausted=retry_exhausted)
        if row["status"] == "downloaded":
            stats["downloaded"] += 1
        elif row["status"] == "duplicate":
            stats["duplicate"] += 1
        elif row["status"] == "snapshot":
            stats["snapshot"] += 1
        else:
            stats["failed"] += 1
            if row.get("exhausted"):
                stats["exhausted"] += 1
    if not probe_only:
        upsert_messages(conn, resolved, messages, current_run)
        stats["snapshot"] += ingest_snapshots(conn, resolved, current_run)
        normalize_group_output_paths(conn, resolved["canonical_name"])
        cold_stats = migrate_cold_files(conn, resolved["canonical_name"], cutoff, cold_root)
        stats.update(cold_stats)
        update_group_cursor(conn, resolved, stats, current_run, dws_version)
        stats["cursor_end"] = (
            stats.get("last_message_time_seen")
            or stats.get("previous_last_message_time_seen")
            or stats.get("history_scan_start", "")
        )
        completion_result = maybe_auto_complete_project_group(config, resolved, stats, current_run)
        stats["project_auto_completion"] = completion_result
        if completion_result.get("completed"):
            stats["auto_completed_project"] = True
            stats["scan_mode_after"] = "manual_only"
            stats["completed_at"] = completion_result.get("completed_at", "")
            stats["completion_reason"] = completion_result.get("completion_reason", completion_result.get("reason", ""))
            write_heartbeat(
                current_run,
                "project_auto_completed",
                group_name=resolved["canonical_name"],
                completed_at=stats["completed_at"],
                idle_days_observed=completion_result.get("idle_days_observed"),
                config_updated=completion_result.get("config_updated", False),
            )
        conn.commit()
        output_dir = write_group_output_dir(conn, resolved, output_root, stats, current_run, config, cutoff)
        stats["output_dir"] = str(output_dir)
        stats["output_layout"] = "group_directory_files_MM"
        stats["output_no_group_zip"] = not any(output_dir.glob("*_latest.zip"))
        stats["snapshots_dir"] = str(SNAPSHOTS / resolved["canonical_name"])
    write_heartbeat(
        current_run,
        "group_complete",
        group_name=resolved["canonical_name"],
        cursor_start=stats.get("cursor_start", ""),
        cursor_end=stats.get("cursor_end", ""),
        auto_completed_project=stats.get("auto_completed_project", False),
        messages_scanned=stats.get("messages_scanned", 0),
        resources_found=stats.get("resources_found", 0),
        downloaded=stats.get("downloaded", 0),
        duplicate=stats.get("duplicate", 0),
        failed=stats.get("failed", 0),
        exhausted=stats.get("exhausted", 0),
    )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive DingTalk all downloadable group files via DWS.")
    parser.add_argument("--probe", action="store_true", help="Resolve groups and scan messages without downloading.")
    parser.add_argument("--plan-only", action="store_true", help="Print the Codex-controlled run plan and exit.")
    parser.add_argument(
        "--run-source",
        default=os.environ.get("DWS_RUN_SOURCE", "codex_manual"),
        choices=["codex_manual", "codex_automation"],
        help="Who triggered this run.",
    )
    parser.add_argument(
        "--automation-name",
        default=os.environ.get("DWS_AUTOMATION_NAME", DEFAULT_AUTOMATION_NAME),
        help="Codex automation name when run_source=codex_automation.",
    )
    parser.add_argument("--full-reconciliation", action="store_true", help="Manual full scan from configured start.")
    parser.add_argument("--retry-exhausted", action="store_true", help="Retry resources already marked exhausted.")
    parser.add_argument(
        "--group",
        action="append",
        dest="groups",
        help="Only process a canonical group name or alias. May be repeated or comma-separated.",
    )
    args = parser.parse_args()

    config = parse_controlled_yaml(CONFIG)
    validate_config(config)
    configure_dws_runtime(config)
    init_dirs(config)
    conn = init_db()
    current_run = run_id()
    output_root = Path(str(config.get("output_root", "~/Downloads/DWS_Outputs"))).expanduser()
    mirror_value = str(config.get("mirror_archive_path", "")).strip()
    mirror_archive = Path(mirror_value).expanduser() if mirror_value else None
    cold_root = Path(str(config.get("cold_archive_root", str(DEFAULT_COLD_ARCHIVE_ROOT)))).expanduser()
    cutoff = hot_cutoff_time(config)
    hot_storage_days = config_int(config, "hot_storage_days", DEFAULT_HOT_STORAGE_DAYS)
    dws_version = collect_dws_version()
    summary: dict[str, Any] = {
        "success": True,
        "run_started": now(),
        "run_id": current_run,
        "run_source": args.run_source,
        "automation_name": args.automation_name,
        "dws_version": dws_version,
        "hot_storage_days": hot_storage_days,
        "hot_cutoff_time": format_message_time(cutoff),
        "output_root": str(output_root),
        "mirror_archive_path": str(mirror_archive) if mirror_archive else "",
        "cold_archive_root": str(cold_root),
        "groups": {},
    }
    try:
        imported_messages = import_existing_chat_records(conn, config, current_run)
        seeded_cursors = seed_missing_group_cursors_from_messages(conn, config, current_run, dws_version)
        repaired_cursor_last_message_times = repair_empty_cursor_last_message_times(conn)
        summary["imported_existing_messages"] = imported_messages
        summary["seeded_group_cursors"] = seeded_cursors
        summary["repaired_cursor_last_message_times"] = repaired_cursor_last_message_times
        conn.commit()
        summary["run_plan"] = build_run_plan(conn, config, args.groups, args.full_reconciliation)
        preflight = render_preflight_report(summary)
        print(preflight, flush=True)
        write_heartbeat(
            current_run,
            "run_preflight_complete",
            run_source=args.run_source,
            automation_name=args.automation_name,
            groups_planned=len(summary.get("run_plan", [])),
            long_span_policy="full_depth_no_time_or_page_truncation",
        )
        if args.plan_only:
            summary["success"] = True
            summary["run_ended"] = now()
            write_heartbeat(current_run, "plan_only_complete", groups_planned=len(summary.get("run_plan", [])))
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        summary["data_archive_size_before"] = path_size_bytes(DATA_ARCHIVE)
        summary.update(cleanup_stale_staging(config_int(config, "staging_ttl_hours", DEFAULT_STAGING_TTL_HOURS)))
        summary.update(write_log_rotation_pending(config_int(config, "log_retention_days", DEFAULT_LOG_RETENTION_DAYS)))
        if not args.probe:
            summary.update(normalize_existing_cold_storage_layout(conn, cold_root))
            conn.commit()

        if not args.probe and output_root.exists():
            shutil.rmtree(output_root)

        selected = selected_groups(config, args.groups)
        wanted = requested_names(args.groups)
        for group in selected_groups(config, args.groups):
            manual_specified = bool(wanted) and (
                group["canonical_name"] in wanted or any(alias in wanted for alias in group.get("aliases", []))
            )
            summary["groups"][group["canonical_name"]] = process_group(
                conn,
                config,
                group,
                output_root,
                current_run,
                dws_version,
                cutoff,
                cold_root,
                probe_only=args.probe,
                full_reconciliation=args.full_reconciliation,
                retry_exhausted=args.retry_exhausted,
                manual_specified=manual_specified,
            )
            write_heartbeat(
                current_run,
                "run_group_recorded",
                group_name=group["canonical_name"],
                groups_completed=len(summary["groups"]),
                groups_total=len(selected),
            )
        if not args.probe:
            rebuilt_skipped: list[str] = []
            for group in enabled_groups(config):
                if group["canonical_name"] in summary["groups"]:
                    continue
                summary["groups"][group["canonical_name"]] = publish_skipped_group_output(
                    conn,
                    group,
                    output_root,
                    current_run,
                    config,
                    cutoff,
                )
                rebuilt_skipped.append(group["canonical_name"])
            summary["skipped_group_outputs_rebuilt"] = rebuilt_skipped
            if rebuilt_skipped:
                write_heartbeat(
                    current_run,
                    "skipped_group_outputs_rebuilt",
                    groups=rebuilt_skipped,
                    count=len(rebuilt_skipped),
                )
        summary["run_ended"] = now()
        if not args.probe:
            summary["cold_migrated_files_total"] = sum(
                int(stats.get("cold_migrated_files", 0)) for stats in summary["groups"].values()
            )
            summary["cold_migrated_bytes_total"] = sum(
                int(stats.get("cold_migrated_bytes", 0)) for stats in summary["groups"].values()
            )
            summary["data_archive_size_after"] = path_size_bytes(DATA_ARCHIVE)
            summary["auto_completed_project_groups"] = [
                {
                    "group_name": group_name,
                    "completed_at": stats.get("completed_at", ""),
                    "completion_reason": stats.get("completion_reason", ""),
                    "config_updated": stats.get("project_auto_completion", {}).get("config_updated", False),
                }
                for group_name, stats in summary["groups"].items()
                if stats.get("auto_completed_project")
            ]
            summary["auto_completed_project_group_count"] = len(summary["auto_completed_project_groups"])
            summary["legacy_group_zips_removed"] = remove_legacy_group_zips(output_root, list(summary["groups"]))
            if mirror_archive is not None:
                summary["mirror_archive_path"] = str(mirror_output_tree_to_archive(output_root, mirror_archive))
                summary["mirror_archive_size_bytes"] = mirror_archive.stat().st_size
                summary.update(remove_temp_downloads_output_after_mirror(output_root, mirror_archive))
            else:
                summary["downloads_temp_output_removed"] = False
                summary["local_downloads_output_path"] = str(output_root)
                summary["downloads_temp_output_remove_reason"] = "mirror_archive_path_not_configured"
            write_project_reports(summary, conn)
        write_heartbeat(
            current_run,
            "run_complete",
            success=True,
            groups_completed=len(summary.get("groups", {})),
            mirror_archive_path=summary.get("mirror_archive_path", ""),
            downloads_temp_output_removed=summary.get("downloads_temp_output_removed", False),
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        summary["success"] = False
        summary["run_ended"] = now()
        summary["error"] = redact_error(str(exc))
        write_heartbeat(current_run, "run_failed", success=False, error=summary["error"])
        REPORTS.mkdir(parents=True, exist_ok=True)
        if args.probe:
            (REPORTS / "last_probe_error.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            (REPORTS / "daily_report.md").write_text(render_human_report(summary), encoding="utf-8")
            (REPORTS / "daily_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
