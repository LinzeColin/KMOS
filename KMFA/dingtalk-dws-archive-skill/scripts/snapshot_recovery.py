#!/usr/bin/env python3
"""Scan only user-provided snapshots/ for image files.

This B-plan helper never touches live DingTalk cache or DB locations. Copy
candidate folders into snapshots/ first, then run this script.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "snapshots"
REPORTS = ROOT / "reports"
RECOVERED = ROOT / "archive" / "by_group" / "_cache_snapshot"

MAGIC = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"RIFF": ".webp",
    b"BM": ".bmp",
    b"II*\x00": ".tiff",
    b"MM\x00*": ".tiff",
    b"\x00\x00\x00": ".heic",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_ext(path: Path) -> str | None:
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return None
    if head[4:12] == b"ftypheic" or head[4:12] == b"ftypheix":
        return ".heic"
    if head.startswith(b"RIFF") and b"WEBP" in head[:16]:
        return ".webp"
    for sig, ext in MAGIC.items():
        if head.startswith(sig) and ext != ".heic":
            return ext
    return None


def main() -> int:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    RECOVERED.mkdir(parents=True, exist_ok=True)
    candidates = []
    for path in SNAPSHOTS.rglob("*"):
        if not path.is_file():
            continue
        ext = image_ext(path)
        if ext:
            candidates.append((path, ext, sha256_file(path), path.stat().st_size))
    copied = 0
    for path, ext, digest, _size in candidates:
        dest = RECOVERED / f"{digest}{ext}"
        if not dest.exists():
            shutil.copy2(path, dest)
            copied += 1
    report = ["# B 方案快照恢复报告", "", f"- 快照目录：`{SNAPSHOTS}`", f"- 识别图片文件：{len(candidates)}", f"- 新复制到归档：{copied}", "", "说明：本脚本只扫描 `snapshots/`，不读取钉钉 live DB/cache，不修改原始目录。"]
    (REPORTS / "b_recovery_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print({"success": True, "candidates": len(candidates), "copied": copied})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
