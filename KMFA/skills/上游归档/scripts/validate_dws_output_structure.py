#!/usr/bin/env python3
"""Validate the current DWS raw archive output layout."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_EVIDENCE = [
    "_manifest/manifest.csv",
    "_manifest/missing_media.csv",
    "_manifest/status.md",
    "_manifest/chat_record_files.csv",
    "_analysis/recent_30d_file_records.csv",
    "_analysis/similar_recent_30d.csv",
    "chat_records/chat_records.csv",
    "chat_records/chat_records.jsonl",
    "chat_records/raw_messages.jsonl",
]

FORBIDDEN_MIRROR_PARTS = {
    "SKILL.md",
    "target_groups.yaml",
    "archive_dingtalk_all_files.py",
    "sync_notion_skill_backup.py",
    "validate_dws_output_structure.py",
}

SUCCESS_STATUSES = {"downloaded", "duplicate", "snapshot"}


def parse_message_time(value: str) -> dt.datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(value[:19], fmt).replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        except ValueError:
            continue
    return None


def local_manifest_has_success(group_dir: Path) -> bool:
    manifest = group_dir / "_manifest" / "manifest.csv"
    if not manifest.is_file():
        return False
    with manifest.open(newline="", encoding="utf-8") as f:
        return any((row.get("status") or "") in SUCCESS_STATUSES for row in csv.DictReader(f))


def mirror_manifest_has_success(zf: zipfile.ZipFile, prefix: str) -> bool:
    manifest_name = f"{prefix}_manifest/manifest.csv"
    if manifest_name not in zf.namelist():
        return False
    with zf.open(manifest_name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8", newline="")
        return any((row.get("status") or "") in SUCCESS_STATUSES for row in csv.DictReader(text))


def validate_group(output_root: Path, group_name: str) -> dict[str, Any]:
    group_dir = output_root / group_name
    errors: list[str] = []
    direct_file_count = 0
    mm_dirs: list[str] = []

    if not group_dir.is_dir():
        errors.append("missing_group_dir")
    else:
        has_success_files = local_manifest_has_success(group_dir)
        legacy_zips = sorted(path.name for path in group_dir.glob("*_latest.zip"))
        if legacy_zips:
            errors.append(f"legacy_latest_zip_exists:{legacy_zips[0]}")
        for rel in REQUIRED_EVIDENCE:
            if not (group_dir / rel).is_file():
                errors.append(f"missing_evidence:{rel}")
        files_dir = group_dir / "files"
        if not files_dir.is_dir():
            errors.append("missing_files_dir")
        else:
            for month_dir in sorted(path for path in files_dir.iterdir() if path.is_dir()):
                if _is_month_dir_name(month_dir.name):
                    mm_dirs.append(month_dir.name)
                    for child in month_dir.iterdir():
                        if child.is_file():
                            direct_file_count += 1
                        elif child.is_dir():
                            errors.append(f"nested_dir_under_mm:{month_dir.name}/{child.name}")
                elif len(month_dir.name) == 4 and month_dir.name.isdigit():
                    errors.append(f"mmdd_dir_forbidden_under_files:{month_dir.name}")
                else:
                    errors.append(f"non_mm_dir_under_files:{month_dir.name}")
            old_date_dirs = sorted(files_dir.glob("[12][0-9][0-9][0-9]/[0-1][0-9]/[0-3][0-9]"))
            if old_date_dirs:
                rel = old_date_dirs[0].relative_to(group_dir)
                errors.append(f"legacy_yyyy_mm_dd_layout:{rel}")
            if has_success_files and direct_file_count == 0:
                errors.append("no_direct_files_under_files_mm")

    return {
        "group": group_name,
        "path": str(group_dir),
        "ok": not errors,
        "errors": errors,
        "mm_dirs": mm_dirs,
        "direct_file_count": direct_file_count,
    }


def validate_mirror(mirror_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    file_count = 0
    if not mirror_path.is_file():
        errors.append("missing_mirror_archive")
    else:
        with zipfile.ZipFile(mirror_path) as zf:
            bad = zf.testzip()
            if bad:
                errors.append(f"mirror_integrity_failed:{bad}")
            names = zf.namelist()
            file_count = sum(1 for name in names if not name.endswith("/"))
            latest = [name for name in names if name.endswith("_latest.zip")]
            if latest:
                errors.append(f"mirror_contains_legacy_latest_zip:{latest[0]}")
            forbidden = [
                name
                for name in names
                if any(part in FORBIDDEN_MIRROR_PARTS for part in Path(name).parts)
            ]
            if forbidden:
                errors.append(f"mirror_contains_skill_or_config_backup:{forbidden[0]}")
    return {"path": str(mirror_path), "ok": not errors, "errors": errors, "file_count": file_count}


def parse_cutoff_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    parsed = parse_message_time(value)
    if parsed:
        return parsed
    return None


def parse_config_scalar(value: str) -> Any:
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
    return value


def load_config_groups(config_path: Path) -> list[str]:
    groups: list[str] = []
    section = ""
    current: dict[str, Any] | None = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0:
            if current and current.get("enabled", True) and current.get("canonical_name"):
                groups.append(str(current["canonical_name"]))
            current = None
            section = line[:-1] if line.endswith(":") else ""
            continue
        if section != "groups":
            continue
        if line.startswith("- "):
            if current and current.get("enabled", True) and current.get("canonical_name"):
                groups.append(str(current["canonical_name"]))
            current = {}
            item = line[2:].strip()
            if item and ":" in item:
                key, _, value = item.partition(":")
                current[key.strip()] = parse_config_scalar(value)
            continue
        if current is not None and ":" in line:
            key, _, value = line.partition(":")
            if key.strip() in {"canonical_name", "enabled"}:
                current[key.strip()] = parse_config_scalar(value)
    if current and current.get("enabled", True) and current.get("canonical_name"):
        groups.append(str(current["canonical_name"]))
    return groups


def load_summary_cutoff(summary_path: Path) -> dt.datetime | None:
    if not summary_path.is_file():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return parse_cutoff_time(data.get("hot_cutoff_time"))


def validate_group_in_mirror(mirror_path: Path, group_name: str, hot_cutoff: dt.datetime | None = None) -> dict[str, Any]:
    errors: list[str] = []
    direct_file_count = 0
    mm_dirs: set[str] = set()
    prefix = f"DWS_Outputs/{group_name}/"
    if not mirror_path.is_file():
        errors.append("missing_mirror_archive")
        names: list[str] = []
        has_success_files = False
    else:
        with zipfile.ZipFile(mirror_path) as zf:
            names = zf.namelist()
            has_success_files = mirror_manifest_has_success(zf, prefix)
    group_names = [name for name in names if name.startswith(prefix)]
    if not group_names:
        errors.append("missing_group_dir_in_mirror")
    legacy_zips = [name for name in group_names if name.endswith("_latest.zip")]
    if legacy_zips:
        errors.append(f"mirror_group_contains_legacy_latest_zip:{legacy_zips[0]}")
    for rel in REQUIRED_EVIDENCE:
        if f"{prefix}{rel}" not in names:
            errors.append(f"missing_mirror_evidence:{rel}")
    manifest_name = f"{prefix}_manifest/manifest.csv"
    if hot_cutoff and manifest_name in names:
        with zipfile.ZipFile(mirror_path) as zf:
            with zf.open(manifest_name) as f:
                text = io.TextIOWrapper(f, encoding="utf-8", newline="")
                for row in csv.DictReader(text):
                    parsed = parse_message_time(row.get("message_time", ""))
                    if parsed and parsed < hot_cutoff:
                        errors.append(f"mirror_manifest_contains_cold_row:{row.get('message_time')}")
                        break
    files_prefix = f"{prefix}files/"
    file_names = [name for name in group_names if name.startswith(files_prefix) and not name.endswith("/")]
    if has_success_files and not file_names:
        errors.append("missing_mirror_files")
    for name in file_names:
        rel_parts = name[len(files_prefix) :].split("/")
        if len(rel_parts) >= 1 and _is_month_dir_name(rel_parts[0]):
            mm_dirs.add(rel_parts[0])
            if len(rel_parts) == 2 and rel_parts[1]:
                direct_file_count += 1
            else:
                errors.append(f"nested_file_under_mm:{'/'.join(rel_parts[:3])}")
        elif len(rel_parts) >= 1 and len(rel_parts[0]) == 4 and rel_parts[0].isdigit():
            errors.append(f"mmdd_file_path_forbidden:{'/'.join(rel_parts[:3])}")
        else:
            errors.append(f"non_mm_file_path:{'/'.join(rel_parts[:3])}")
        if len(rel_parts) >= 4 and len(rel_parts[0]) == 4 and rel_parts[0].startswith(("20", "19")):
            errors.append(f"legacy_yyyy_mm_dd_layout:files/{'/'.join(rel_parts[:3])}")
    if group_names and has_success_files and direct_file_count == 0:
        errors.append("no_direct_files_under_mirror_files_mm")
    return {
        "group": group_name,
        "mirror_prefix": prefix,
        "ok": not errors,
        "errors": errors,
        "mm_dirs": sorted(mm_dirs),
        "direct_file_count": direct_file_count,
    }


def validate_cold_root(cold_root: Path | None) -> dict[str, Any]:
    if cold_root is None:
        return {"ok": True, "path": "", "group_dirs": [], "zip_files": [], "errors": []}
    errors: list[str] = []
    group_dirs: list[Path] = []
    zip_files: list[Path] = []
    if not cold_root.exists():
        errors.append("missing_cold_root")
    else:
        zip_files = sorted(cold_root.rglob("*.zip"))
        if zip_files:
            errors.extend(f"cold_zip_forbidden:{path}" for path in zip_files[:20])
        for child in sorted(cold_root.iterdir()):
            if child.name == ".DS_Store":
                continue
            if not child.is_dir():
                errors.append(f"unexpected_cold_root_file:{child.name}")
                continue
            if child.name.isdigit() and len(child.name) in {2, 4}:
                errors.append(f"year_directory_forbidden:{child}")
                continue
            group_dirs.append(child)
            files_root = child / "files"
            if not files_root.exists():
                continue
            for path in files_root.rglob("*"):
                if path.is_dir():
                    rel = path.relative_to(files_root).parts
                    if len(rel) == 1 and not _is_month_dir_name(rel[0]):
                        errors.append(f"cold_non_mm_directory:{path}")
                    elif len(rel) > 1:
                        errors.append(f"cold_nested_directory_forbidden:{path}")
                elif path.is_file():
                    rel = path.relative_to(files_root).parts
                    if len(rel) != 2 or not _is_month_dir_name(rel[0]):
                        errors.append(f"cold_file_not_under_files_mm:{path}")
    return {
        "ok": not errors,
        "path": str(cold_root),
        "group_dirs": [str(path) for path in group_dirs],
        "zip_files": [str(path) for path in zip_files],
        "errors": errors,
    }


def _is_month_dir_name(value: str) -> bool:
    return len(value) == 2 and value.isdigit() and 1 <= int(value) <= 12


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DWS output directories.")
    parser.add_argument(
        "--output-root",
        default="~/Downloads/DWS_Outputs",
        help="DWS output root. Defaults to ~/Downloads/DWS_Outputs.",
    )
    parser.add_argument("--group", action="append", help="Group name to validate. May repeat. Defaults to enabled groups in config.")
    parser.add_argument("--config", default="config/target_groups.yaml", help="Target group config used when --group is omitted.")
    parser.add_argument("--mirror", help="Optional whole-tree mirror zip path to validate.")
    parser.add_argument("--expect-downloads-deleted", action="store_true", help="Require local Downloads output root to be absent.")
    parser.add_argument("--hot-days", type=int, default=None, help="Require current mirror package manifest rows to be within this hot window.")
    parser.add_argument("--hot-cutoff-time", help="Explicit hot cutoff time. Overrides --summary-json and --hot-days.")
    parser.add_argument(
        "--summary-json",
        default="reports/daily_summary.json",
        help="Daily summary JSON whose hot_cutoff_time should be used for mirror validation.",
    )
    parser.add_argument("--cold-root", help="Optional cold archive root to validate.")
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser()
    mirror_path = Path(args.mirror).expanduser() if args.mirror else None
    cold_root = Path(args.cold_root).expanduser() if args.cold_root else None
    config_path = Path(args.config).expanduser()
    groups = args.group or load_config_groups(config_path)
    if not groups:
        raise SystemExit("No groups provided and no enabled groups found in config.")
    hot_cutoff = parse_cutoff_time(args.hot_cutoff_time)
    cutoff_source = "explicit" if hot_cutoff else ""
    if hot_cutoff is None and args.summary_json:
        hot_cutoff = load_summary_cutoff(Path(args.summary_json).expanduser())
        cutoff_source = "summary_json" if hot_cutoff else ""
    if hot_cutoff is None and args.hot_days:
        hot_cutoff = dt.datetime.now().astimezone() - dt.timedelta(days=args.hot_days)
        cutoff_source = "validation_time_hot_days"
    result: dict[str, Any] = {
        "output_root": str(output_root),
        "expect_downloads_deleted": args.expect_downloads_deleted,
        "groups_source": "args" if args.group else str(config_path),
        "hot_cutoff_time": hot_cutoff.isoformat() if hot_cutoff else "",
        "hot_cutoff_source": cutoff_source,
    }
    local_errors: list[str] = []
    if args.expect_downloads_deleted:
        if output_root.exists():
            local_errors.append("downloads_output_still_exists")
        if mirror_path is None:
            local_errors.append("mirror_required_when_downloads_deleted")
        result["groups"] = [
            validate_group_in_mirror(mirror_path, group, hot_cutoff) if mirror_path is not None else {
                "group": group,
                "ok": False,
                "errors": ["mirror_required_when_downloads_deleted"],
                "mmdd_dirs": [],
                "direct_file_count": 0,
            }
            for group in groups
        ]
    else:
        result["groups"] = [validate_group(output_root, group) for group in groups]
    result["local_output_root"] = {
        "path": str(output_root),
        "exists": output_root.exists(),
        "ok": not local_errors,
        "errors": local_errors,
    }
    if mirror_path is not None:
        result["mirror"] = validate_mirror(mirror_path)
    result["cold_storage"] = validate_cold_root(cold_root)
    result["ok"] = (
        result["local_output_root"]["ok"]
        and all(group["ok"] for group in result["groups"])
        and result.get("mirror", {"ok": True})["ok"]
        and result["cold_storage"]["ok"]
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
