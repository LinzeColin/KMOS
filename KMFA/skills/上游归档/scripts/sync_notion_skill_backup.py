#!/usr/bin/env python3
"""Sync DWS skill/archive configuration backup to Notion when files change.

This script intentionally writes no DingTalk archive output. It only tracks the
DWS skill tree and local archive project configuration needed for handoff.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DWS = os.environ.get("DWS_BIN", str(Path.home() / ".local/bin/dws"))
CONFIG = ROOT / "config" / "target_groups.yaml"
REPORTS = ROOT / "reports"
STATE_DIR = ROOT / "data" / "notion_skill_backup"
STATE_FILE = STATE_DIR / "state.json"
LATEST_MD = REPORTS / "notion_skill_backup_latest.md"
PENDING_MD = REPORTS / "notion_skill_backup_pending.md"
DEFAULT_PAGE_ID = "394b1a986ba680c2abe5c549d242ad43"
NOTION_VERSION = os.environ.get("NOTION_VERSION", "2022-06-28")

PROJECT_FILES = [
    Path("SKILL.md"),
    Path("config/target_groups.yaml"),
    Path("templates/target_groups.example.yaml"),
    Path("scripts/archive_dingtalk_all_files.py"),
    Path("scripts/sync_notion_skill_backup.py"),
    Path("scripts/validate_dws_output_structure.py"),
    Path("scripts/weekly_dws_smoke.py"),
    Path("scripts/run_daily.sh"),
    Path("scripts/run_weekly.sh"),
    Path("automation/com.linze.dingtalk-dws-archive.daily.plist"),
    Path("automation/com.linze.dingtalk-dws-archive.weekly.plist"),
    Path("references/operating_contract.md"),
    Path("references/功能清单.md"),
    Path("references/模型参数文件.md"),
    Path("references/开发记录.md"),
    Path("references/recovery.md"),
]
SKILL_ROOTS = [
    ROOT,
    Path.home() / ".codex" / "skills" / "dingtalk-dws-archive",
    Path.home() / ".agents" / "skills" / "dingtalk-dws-archive",
    Path.home() / ".codex" / "skills" / "dws",
    Path.home() / ".agents" / "skills" / "dws",
]
SKIP_NAMES = {".DS_Store"}
SKIP_DIRS = {"__pycache__", ".git"}


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def read_config_value(key: str, default: str = "") -> str:
    if not CONFIG.exists():
        return default
    prefix = f"{key}:"
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            return line.partition(":")[2].strip().strip('"').strip("'")
    return default


def notion_page_id() -> str:
    return read_config_value("notion_backup_page_id", DEFAULT_PAGE_ID)


def notion_backup_enabled() -> bool:
    value = read_config_value("notion_backup_enabled", "true").lower()
    return value not in {"0", "false", "no", "off"}


def label_path(path: Path) -> str:
    path = path.expanduser()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def relative_to_source(path: Path, source: Path) -> str:
    try:
        return str(path.relative_to(source))
    except ValueError:
        return path.name


def should_skip(path: Path) -> bool:
    return path.name in SKIP_NAMES or bool(set(path.parts) & SKIP_DIRS) or path.suffix == ".pyc"


def iter_source_files(source: Path) -> list[Path]:
    source = source.expanduser()
    if not source.exists():
        return []
    if source.is_file():
        return [source] if not should_skip(source) else []
    return sorted(p for p in source.rglob("*") if p.is_file() and not should_skip(p))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_summary(source: Path) -> dict[str, Any]:
    files = iter_source_files(source)
    tree_hash = hashlib.sha256()
    total_bytes = 0
    entries: list[dict[str, Any]] = []
    for path in files:
        digest = sha256_file(path)
        size = path.stat().st_size
        total_bytes += size
        rel = relative_to_source(path, source.expanduser())
        tree_hash.update(rel.encode("utf-8"))
        tree_hash.update(digest.encode("ascii"))
        entries.append({"relative_path": rel, "size_bytes": size, "sha256": digest})
    return {
        "source": label_path(source),
        "exists": source.expanduser().exists(),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "tree_sha256": tree_hash.hexdigest(),
        "entries": entries,
    }


def collect_snapshot() -> dict[str, Any]:
    sources = [ROOT / rel for rel in PROJECT_FILES] + SKILL_ROOTS
    summaries = [source_summary(source) for source in sources]
    fingerprint_hash = hashlib.sha256()
    for summary in summaries:
        fingerprint_hash.update(summary["source"].encode("utf-8"))
        fingerprint_hash.update(str(summary["exists"]).encode("ascii"))
        fingerprint_hash.update(summary["tree_sha256"].encode("ascii"))
    return {
        "generated_at": now(),
        "notion_page_id": notion_page_id(),
        "dws_version": collect_dws_version(),
        "fingerprint": fingerprint_hash.hexdigest(),
        "sources": summaries,
        "groups": parse_group_names(),
    }


def collect_dws_version() -> str:
    for args in (["version", "--format", "json"], ["version"]):
        try:
            proc = subprocess.run([DWS, *args], cwd=ROOT, text=True, capture_output=True, timeout=30)
        except Exception:
            continue
        if proc.returncode != 0:
            continue
        text = proc.stdout.strip()
        try:
            data = json.loads(text[text.find("{") : text.rfind("}") + 1])
            return str(data.get("version") or data.get("result", {}).get("version") or "unknown")
        except Exception:
            return text.splitlines()[0][:80] if text else "unknown"
    return "unknown"


def parse_group_names() -> list[str]:
    if not CONFIG.exists():
        return []
    groups: list[str] = []
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- canonical_name:"):
            groups.append(line.partition(":")[2].strip().strip('"'))
    return groups


def redact_text(text: str) -> str:
    replacements = [
        (r'(open_conversation_id:\s*")[^"]+(")', r"\1<redacted>\2"),
        (r'("(?:openConversationId|open_conversation_id|token|access_token|refresh_token|password|secret)"\s*:\s*")[^"]+(")', r"\1<redacted>\2"),
        (r"(cid[A-Za-z0-9+/=]{12,})", "<redacted-cid>"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def read_redacted_config() -> str:
    if not CONFIG.exists():
        return "# missing config/target_groups.yaml"
    return redact_text(CONFIG.read_text(encoding="utf-8"))


def render_markdown(snapshot: dict[str, Any]) -> str:
    source_lines = []
    for source in snapshot["sources"]:
        source_lines.append(
            f"- `{source['source']}`: exists={source['exists']}, files={source['file_count']}, "
            f"bytes={source['total_bytes']}, tree_sha256_prefix=`{source['tree_sha256'][:16]}`"
        )
    groups = ", ".join(snapshot["groups"]) if snapshot["groups"] else "none"
    full_scan_since = read_config_value("full_scan_since", "unset")
    page_size = read_config_value("page_size", read_config_value("daily_limit", "unset"))
    recent_similarity_days = read_config_value("recent_similarity_days", "30")
    hot_storage_days = read_config_value("hot_storage_days", "60")
    project_idle_days = read_config_value("project_auto_complete_idle_days", "7")
    dws_http_timeout = read_config_value("dws_http_timeout_seconds", "120")
    dws_retries = read_config_value("dws_command_retries", "3")
    dws_backoff = read_config_value("dws_retry_backoff_seconds", "5")
    return "\n".join(
        [
            "# DWS raw archive skill/config Notion backup",
            "",
            f"- generated_at: {snapshot['generated_at']}",
            f"- dws_version: {snapshot['dws_version']}",
            f"- source_fingerprint: `{snapshot['fingerprint']}`",
            f"- target_groups: {groups}",
            "- skill_scope: 钉钉DWS归档 means DWS full-file raw data archive only; business reports and conclusions are out of scope.",
            "- execution_boundary: only Codex automation or Codex manual control may run the archive; launchd/local unattended execution is disabled.",
            "- automation_schedule: Codex automation runs at 11:00 and 19:00 local time unless the user changes it.",
            "- target_change_policy: whenever target groups are added, removed, renamed, or mode-changed, update/check the Codex automation and sync this Notion backup.",
            "- output_boundary: Downloads/DWS_Outputs is a temporary build tree and is deleted after OneDrive/DWS_Outputs.zip is verified.",
            f"- hot_cold_policy: OneDrive/DWS_Outputs.zip contains only the latest `{hot_storage_days}` days; older file bodies move to OneDrive/DWS_Archive/<group>/files/MM/ as plain files; no year directory and no zip are used while SQLite manifest remains permanent.",
            "- current_cold_layout_policy: legacy cold files/MMDD folders are migrated to files/MM during real runs and SQLite cold paths are updated.",
            "- group_output_layout: each group uses `<group>/files/MM/` for downloaded files plus `_manifest/`, `_analysis/`, and `chat_records/`; per-group `<group>_latest.zip` is not a current output path.",
            "- manual_only_output_policy: manual_only groups are skipped for active DWS scanning but still rebuilt from historical manifest/messages into the current DWS_Outputs.zip.",
            "- mirror_policy: OneDrive/DWS_Outputs.zip never contains skill/config backups and must pass integrity checks before temporary Downloads output is deleted.",
            f"- scan_boundary: daily auto scans start from each group's SQLite cursor; `{full_scan_since}` is only the initial/manual reconciliation fallback; `page_size={page_size}` is request size, not a stop condition.",
            "- long_span_policy: standing groups and long project groups are normal; full-time full-depth collection must not be shortened, page-capped, sampled, or limited to recent messages just to finish faster.",
            "- heartbeat_policy: long scans write `reports/current_run_heartbeat.json`; only no heartbeat/log/subprocess progress past the configured stale threshold should be treated as blocked.",
            f"- dws_resilience_policy: every DWS CLI call passes `--timeout={dws_http_timeout}` and retries transient timeout/dial errors up to `{dws_retries}` times with `{dws_backoff}` seconds base backoff.",
            f"- similarity_window: `recent_similarity_days={recent_similarity_days}`; keep at least 30 days for downstream incremental analysis agents.",
            f"- group_lifecycle: standing groups stay auto; project groups auto-complete after `{project_idle_days}` days with no new messages/files after a successful incremental scan; completed_at is the last message time and scan_mode becomes manual_only.",
            "- sync_policy: `scripts/run_daily.sh` and `scripts/run_weekly.sh` call this script; it syncs only when the source fingerprint changes.",
            "- notion_connector_policy: if shell token is missing, the Codex run should use the available Notion connector; pending is only acceptable when connector/browser fallback also fails.",
            "- security_policy: OAuth tokens, cookies, browser state, DingTalk local DB, and open_conversation_id values are excluded or redacted.",
            "",
            "## Restore outline",
            "",
            "1. Install DWS and login to the China DingTalk organization.",
            "2. Run `dws skill setup --mode mono --target all --yes`.",
            "3. Restore or recreate this archive project, then copy the tracked project files listed below.",
            "4. Re-resolve target group IDs with `dws chat search --query \"群名\" --limit 10 --cursor 0 --format json`.",
            "5. Fill `config/target_groups.yaml`, then run `/usr/bin/python3 scripts/archive_dingtalk_all_files.py --plan-only` from Codex to review the preflight list.",
            "6. After the preflight is accepted, run `DWS_CODEX_CONTROLLED=1 DWS_RUN_SOURCE=codex_manual /bin/sh scripts/run_daily.sh` from Codex.",
            "",
            "## Covered sources",
            "",
            *source_lines,
            "",
            "## Redacted config/target_groups.yaml",
            "",
            "```yaml",
            read_redacted_config().rstrip(),
            "```",
            "",
        ]
    )


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_latest(markdown: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    LATEST_MD.write_text(markdown, encoding="utf-8")


def text_block(block_type: str, text: str) -> dict[str, Any]:
    return {block_type: {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]}, "type": block_type}


def code_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for i in range(0, len(markdown), 1800):
        blocks.append(
            {
                "type": "code",
                "code": {
                    "language": "markdown",
                    "rich_text": [{"type": "text", "text": {"content": markdown[i : i + 1800]}}],
                },
            }
        )
    return blocks


def create_notion_backup_page(token: str, page_id: str, snapshot: dict[str, Any], markdown: str) -> str:
    title = f"DWS skill/config backup {snapshot['generated_at'][:19].replace('T', ' ')}"
    payload = {
        "parent": {"type": "page_id", "page_id": page_id},
        "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
        "children": [
            text_block("heading_1", "DWS skill/config backup"),
            text_block("paragraph", f"Generated at {snapshot['generated_at']}. Fingerprint {snapshot['fingerprint']}."),
            text_block("paragraph", "Sensitive DingTalk IDs and credentials are redacted. DWS output directories and mirrors remain DingTalk-only."),
            *code_blocks(markdown),
        ],
    }
    request = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Notion API HTTP {exc.code}: {body}") from exc
    return str(data.get("url") or data.get("id") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync DWS skill/archive config backup to Notion on change.")
    parser.add_argument("--force", action="store_true", help="Sync even if the fingerprint has not changed.")
    parser.add_argument("--dry-run", action="store_true", help="Generate the markdown backup but do not call Notion.")
    parser.add_argument("--quiet", action="store_true", help="Print compact JSON only.")
    parser.add_argument("--record-external-sync", default="", help="Record a Notion page URL/ID created by an external connector.")
    args = parser.parse_args()

    snapshot = collect_snapshot()
    markdown = render_markdown(snapshot)
    write_latest(markdown)
    state = load_state()
    changed = snapshot["fingerprint"] != state.get("last_synced_fingerprint")
    result: dict[str, Any] = {
        "success": True,
        "changed": changed,
        "fingerprint": snapshot["fingerprint"],
        "latest_markdown": str(LATEST_MD),
        "notion_page_id": snapshot["notion_page_id"],
    }

    if args.record_external_sync:
        for key in ("last_pending_at", "last_pending_fingerprint", "pending_reason"):
            state.pop(key, None)
        state.update(
            {
                "last_synced_at": now(),
                "last_synced_fingerprint": snapshot["fingerprint"],
                "last_synced_page": args.record_external_sync,
                "last_sync_method": "external_connector",
            }
        )
        write_state(state)
        if PENDING_MD.exists():
            PENDING_MD.unlink()
        result["synced"] = True
        result["sync_method"] = "external_connector"
        result["notion_backup_page"] = args.record_external_sync
        if PENDING_MD.exists():
            PENDING_MD.unlink()
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0

    if not notion_backup_enabled():
        result["synced"] = False
        result["reason"] = "notion_backup_disabled"
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0
    if not changed and not args.force:
        result["synced"] = False
        result["reason"] = "unchanged"
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0
    if args.dry_run:
        result["synced"] = False
        result["reason"] = "dry_run"
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0

    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        PENDING_MD.write_text(markdown, encoding="utf-8")
        state.update(
            {
                "last_pending_at": now(),
                "last_pending_fingerprint": snapshot["fingerprint"],
                "pending_reason": "NOTION_TOKEN/NOTION_API_KEY is not set for shell automation.",
            }
        )
        write_state(state)
        result["synced"] = False
        result["reason"] = "missing_notion_token_pending_written"
        result["pending_markdown"] = str(PENDING_MD)
        result["fallback_required"] = True
        result["fallback_options"] = [
            "Use Notion connector/API from Codex if available.",
            "Use Chrome/computer-use against an already logged-in Notion page.",
        ]
        result["operator_warning"] = (
            "No Notion token in shell. The pending markdown must be synced by an interactive "
            "Notion path or a later token-backed run; this is not a completed sync."
        )
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 0

    try:
        page = create_notion_backup_page(token, snapshot["notion_page_id"], snapshot, markdown)
    except Exception as exc:
        PENDING_MD.write_text(markdown, encoding="utf-8")
        result["success"] = False
        result["synced"] = False
        result["reason"] = str(exc)
        print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
        return 1

    state.update(
        {
            "last_synced_at": now(),
            "last_synced_fingerprint": snapshot["fingerprint"],
            "last_synced_page": page,
            "last_sync_method": "notion_api",
        }
    )
    write_state(state)
    if PENDING_MD.exists():
        PENDING_MD.unlink()
    result["synced"] = True
    result["notion_backup_page"] = page
    print(json.dumps(result, ensure_ascii=False, indent=None if args.quiet else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
