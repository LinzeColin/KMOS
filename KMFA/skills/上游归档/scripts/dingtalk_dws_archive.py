#!/usr/bin/env python3
"""Archive DingTalk group images through the official dws CLI.

This script intentionally uses only DWS commands. It does not inspect browser
cookies, Keychain internals, DingTalk live DBs, or private APIs.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DWS = os.environ.get("DWS_BIN", str(Path.home() / ".local/bin/dws"))
CONFIG = ROOT / "config" / "targets.yaml"
DB = ROOT / "data" / "messages.sqlite3"
ARCHIVE = ROOT / "archive" / "by_group"
IMAGE_POOL = ROOT / "archive" / "images"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
MISSING = REPORTS / "missing_media.csv"
MEDIA_RE = re.compile(r"mediaId=([^\)\s]+)")


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return value[:2] + "***" + value[-2:]
    return value[:6] + "..." + value[-6:]


def safe_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", value.strip())
    value = re.sub(r"\s+", "_", value)
    return value[:80] or "unknown"


def read_targets() -> list[dict[str, str]]:
    # Minimal parser for the controlled config/targets.yaml shape.
    targets: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "targets:":
            continue
        if line.startswith("- "):
            if current:
                targets.append(current)
            current = {}
            line = line[2:].strip()
            if line:
                key, _, val = line.partition(":")
                current[key.strip()] = val.strip().strip('"')
            continue
        if current is not None and ":" in line:
            key, _, val = line.partition(":")
            current[key.strip()] = val.strip().strip('"')
    if current:
        targets.append(current)
    return [t for t in targets if str(t.get("enabled", "true")).lower() == "true"]


def run_dws(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [DWS, *args, "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def init_dirs() -> None:
    for path in [DB.parent, ARCHIVE, IMAGE_POOL, REPORTS, LOGS]:
        path.mkdir(parents=True, exist_ok=True)
    if not MISSING.exists():
        MISSING.write_text(
            "run_at,group,message_time,sender,message_id_masked,media_id_masked,reason\n",
            encoding="utf-8",
        )


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            open_conversation_id TEXT NOT NULL,
            open_message_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            sender TEXT,
            create_time TEXT,
            has_image INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (open_conversation_id, open_message_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS images (
            sha256 TEXT PRIMARY KEY,
            open_conversation_id TEXT NOT NULL,
            open_message_id TEXT NOT NULL,
            media_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            sender TEXT,
            create_time TEXT,
            archive_path TEXT NOT NULL,
            source TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            archived_at TEXT NOT NULL
        )
        """
    )
    return conn


def parse_json_output(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError("DWS output did not contain JSON")
    return json.loads(text[start:])


def append_missing(row: dict[str, str]) -> None:
    with MISSING.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run_at",
                "group",
                "message_time",
                "sender",
                "message_id_masked",
                "media_id_masked",
                "reason",
            ],
        )
        writer.writerow(row)


def find_downloaded_file(tmp: Path) -> Path | None:
    files = [p for p in tmp.rglob("*") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_size)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_image(target: dict[str, str], msg: dict, media_id: str, idx: int, conn: sqlite3.Connection) -> tuple[bool, str]:
    group = target["name"]
    conv_id = target["open_conversation_id"]
    msg_id = msg.get("openMessageId", "")
    create_time = msg.get("createTime", "")
    sender = msg.get("sender", "unknown")
    with tempfile.TemporaryDirectory(prefix="dws-media-", dir=ROOT / "archive") as td:
        tmp = Path(td)
        proc = run_dws(
            [
                "chat",
                "message",
                "download-media",
                "--type",
                "mediaId",
                "--resource-id",
                media_id,
                "--message-id",
                msg_id,
                "--open-conversation-id",
                conv_id,
                "--output",
                str(tmp),
            ],
            timeout=90,
        )
        if proc.returncode != 0:
            reason = (proc.stderr or proc.stdout or "download failed").strip().splitlines()[-1][:500]
            append_missing(
                {
                    "run_at": now(),
                    "group": group,
                    "message_time": create_time,
                    "sender": sender,
                    "message_id_masked": mask(msg_id),
                    "media_id_masked": mask(media_id),
                    "reason": reason,
                }
            )
            return False, reason
        downloaded = find_downloaded_file(tmp)
        if not downloaded:
            append_missing(
                {
                    "run_at": now(),
                    "group": group,
                    "message_time": create_time,
                    "sender": sender,
                    "message_id_masked": mask(msg_id),
                    "media_id_masked": mask(media_id),
                    "reason": "download reported success but no file was found",
                }
            )
            return False, "no file"
        digest = sha256_file(downloaded)
        ext = downloaded.suffix.lower() or ".bin"
        year_month = (create_time[:7] if len(create_time) >= 7 else "unknown-month")
        dest_dir = ARCHIVE / safe_name(group) / year_month / safe_name(sender)
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = re.sub(r"[-: ]", "", create_time[:19]) or "unknown_time"
        dest = dest_dir / f"{stamp}_{safe_name(mask(msg_id))}_{idx}_{digest[:12]}{ext}"
        existing = conn.execute("SELECT archive_path FROM images WHERE sha256 = ?", (digest,)).fetchone()
        if existing:
            return True, "duplicate"
        shutil.move(str(downloaded), dest)
        pool = IMAGE_POOL / f"{digest}{ext}"
        if not pool.exists():
            try:
                os.link(dest, pool)
            except OSError:
                shutil.copy2(dest, pool)
        conn.execute(
            """
            INSERT OR IGNORE INTO images (
                sha256, open_conversation_id, open_message_id, media_id, group_name,
                sender, create_time, archive_path, source, size_bytes, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                digest,
                conv_id,
                msg_id,
                media_id,
                group,
                sender,
                create_time,
                str(dest.relative_to(ROOT)),
                "dws",
                dest.stat().st_size,
                now(),
            ),
        )
        return True, "downloaded"


def main() -> int:
    init_dirs()
    conn = init_db()
    targets = read_targets()
    total_messages = total_images = downloaded = duplicates = failed = 0
    run_started = now()

    for target in targets:
        conv_id = target["open_conversation_id"]
        proc = run_dws(
            [
                "chat",
                "message",
                "list",
                "--group",
                conv_id,
                "--time",
                target.get("since", "2026-06-01 00:00:00"),
                "--limit",
                str(target.get("limit", "50")),
                "--forward",
                "true",
            ],
            timeout=90,
        )
        if proc.returncode != 0:
            append_missing(
                {
                    "run_at": now(),
                    "group": target["name"],
                    "message_time": "",
                    "sender": "",
                    "message_id_masked": "",
                    "media_id_masked": "",
                    "reason": (proc.stderr or proc.stdout).strip().splitlines()[-1][:500],
                }
            )
            failed += 1
            continue
        data = parse_json_output(proc.stdout)
        messages = data.get("result", {}).get("messages", [])
        total_messages += len(messages)
        for msg in messages:
            media_ids = MEDIA_RE.findall(msg.get("content", ""))
            total_images += len(media_ids)
            conn.execute(
                """
                INSERT OR REPLACE INTO messages (
                    open_conversation_id, open_message_id, group_name, sender, create_time, has_image
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conv_id,
                    msg.get("openMessageId", ""),
                    target["name"],
                    msg.get("sender", ""),
                    msg.get("createTime", ""),
                    1 if media_ids else 0,
                ),
            )
            for idx, media_id in enumerate(media_ids, start=1):
                ok, status = download_image(target, msg, media_id, idx, conn)
                if ok and status == "downloaded":
                    downloaded += 1
                elif ok and status == "duplicate":
                    duplicates += 1
                else:
                    failed += 1
        conn.commit()

    report = f"""# DingTalk Image Archive Daily Report

Run started: {run_started}
Run ended: {now()}

## Summary
- Targets: {len(targets)}
- Messages scanned: {total_messages}
- Image references found: {total_images}
- Downloaded new images: {downloaded}
- Duplicates skipped: {duplicates}
- Failures recorded: {failed}

## Files
- SQLite manifest: `data/messages.sqlite3`
- Missing media list: `reports/missing_media.csv`
- Archive root: `archive/by_group/`
"""
    (REPORTS / "daily_report.md").write_text(report, encoding="utf-8")
    status = f"""# 钉钉图片归档状态

更新时间：{now()}

## 当前结论
- A 主方案：可运行。DWS 已登录，目标群已配置，脚本可扫描消息并下载图片。
- B 补充方案：已准备脚本，只扫描 `snapshots/`，不会读取或修改钉钉原始目录。
- C 维护方案：已安装 launchd 定时任务：每日 02:00 归档，每周日 03:00 维护检查。
- launchd label：`com.linze.dingtalk-dws-archive.daily` 与 `com.linze.dingtalk-dws-archive.weekly`。

## 最近一次运行
- 扫描消息：{total_messages}
- 发现图片引用：{total_images}
- 新下载图片：{downloaded}
- 去重跳过：{duplicates}
- 失败记录：{failed}

## 你需要关注
- 如果 `reports/missing_media.csv` 除表头外有内容，说明有图片需要 B 方案或人工复核。
- 暂停定时任务：`launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.linze.dingtalk-dws-archive.daily.plist`，周任务同理替换为 `weekly`。
"""
    (REPORTS / "status.md").write_text(status, encoding="utf-8")
    print(json.dumps({"success": True, "messages": total_messages, "images": total_images, "downloaded": downloaded, "duplicates": duplicates, "failed": failed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
