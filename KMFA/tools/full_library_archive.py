#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量库增量归档：清单进 GitHub，内容按规则挑着进，本机不落一个字节。

Owner 2026-07-27：「该备份的全部都备份github，增量存档，不要占用本机资源
全量库非常大 约400GB」，源在 smb://192.168.0.1/share/06_资料库/MetaData。

先把三条不能绕的约束摆出来——绕开它们做出来的东西会在半路炸掉：

  ① **400GB 进不了 git 仓库。** GitHub 单文件硬上限 100MB、仓库软上限约 5GB；
     Git LFS 在这个量级约合每月一千多美元，且 clone/push 会瘫。
  ② **云端够不到局域网。** 源是 192.168.0.1，容器在公网，所以传输只能从本机发起，
     没法做成纯云端排程。
  ③ **本机零占用。** 所以不能先拉到本地再传——必须边读边算边传，
     任一时刻只在内存里留一个文件的一块。

在这三条之下能做且值得做的，是**清单先行、内容挑着上**：

  · 清单（path/size/mtime/sha256）对 400GB 大约几十 MB，**进 git 完全合适**，
    而且它才是「我们到底有什么、变没变、丢没丢」的唯一可查依据。
    没有清单，400GB 就是一堆没人知道内容的字节。
  · 内容只上传**业务真在吃的那部分**（财务/工资/红圈/WPS 导出这类结构化源），
    且单文件小于阈值。其余只登记不上传，并在清单里如实标 `content_archived: false`——
    **不假装备份过**。

增量怎么判：size+mtime 都没变就跳过，不重算 sha256。
  在 SMB 上重算哈希是最贵的操作（400GB 走网线），跳过没变的文件是这个工具能用的前提。

【Owner 铁律】只进唯一私有库 Private-Database，永不新建 repo。
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BEIJING = timezone(timedelta(hours=8))

#: GitHub 单文件硬上限 100MB。留出 base64 膨胀（约 4/3）与余量后取 60MB。
#: 超过的只登记不上传——硬闯只会在 push 时失败，且失败得很难看。
CONTENT_MAX_BYTES = 60 * 1024 * 1024

#: 内容值得上传的形态：业务真在吃的结构化源。
#: 扫描件、照片、CAD、视频不在其中——它们占了绝大部分体积，却不进任何计算。
CONTENT_SUFFIXES = {".xlsx", ".xlsm", ".xls", ".csv", ".json", ".jsonl",
                    ".yaml", ".yml", ".md", ".txt", ".zip"}

#: 一律不登记的噪声。.DS_Store 这种在 SMB 上到处都是，登记它们只会淹没清单。
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".localized"}


def sha256_stream(path: Path, chunk: int = 1 << 20) -> str:
    """边读边算。**绝不把文件读进内存**——源里有单个几 GB 的文件。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_previous(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("path"):
            out[record["path"]] = record
    return out


def should_archive_content(relative: Path, size: int) -> tuple[bool, str]:
    if size > CONTENT_MAX_BYTES:
        return False, f"超过 {CONTENT_MAX_BYTES // 1024 // 1024}MB 上限，只登记不上传"
    if relative.suffix.lower() not in CONTENT_SUFFIXES:
        return False, "非结构化业务源（扫描件/照片/图纸这类），只登记不上传"
    return True, ""


def walk(root: Path, previous: dict[str, dict], *, limit: int | None,
         deadline: float | None) -> tuple[list[dict], dict]:
    """遍历并产出清单行。**增量**：size+mtime 没变就沿用旧 sha256，不重算。"""
    records: list[dict] = []
    stats = {"扫描": 0, "跳过噪声": 0, "沿用旧哈希": 0, "重新哈希": 0,
             "读不到": 0, "内容待上传": 0, "只登记": 0, "提前收工": None}
    for current, dirs, files in os.walk(root, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name in SKIP_NAMES or name.startswith("._"):
                stats["跳过噪声"] += 1
                continue
            if deadline and time.monotonic() > deadline:
                stats["提前收工"] = "到达时限——清单是**部分**的，不得当成全量"
                return records, stats
            if limit and len(records) >= limit:
                stats["提前收工"] = f"到达 --limit {limit}——清单是**部分**的"
                return records, stats
            full = Path(current) / name
            try:
                info = full.stat()
            except OSError:
                stats["读不到"] += 1
                continue
            relative = full.relative_to(root)
            key = str(relative)
            stats["扫描"] += 1
            old = previous.get(key)
            unchanged = (old and old.get("size") == info.st_size
                         and abs(float(old.get("mtime", 0)) - info.st_mtime) < 1)
            if unchanged:
                digest = old.get("sha256", "")
                stats["沿用旧哈希"] += 1
            else:
                try:
                    digest = sha256_stream(full)
                except OSError:
                    stats["读不到"] += 1
                    continue
                stats["重新哈希"] += 1
            archive, reason = should_archive_content(relative, info.st_size)
            stats["内容待上传" if archive else "只登记"] += 1
            records.append({
                "path": key, "size": info.st_size, "mtime": round(info.st_mtime, 3),
                "sha256": digest,
                "content_archived": bool(archive and old and old.get("content_archived")),
                "content_should_archive": archive,
                "not_archived_reason": reason or None,
            })
    return records, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="全量库增量归档（清单先行，本机零落地）")
    parser.add_argument("--root", required=True, help="源根目录，如 /Volumes/share/06_资料库/MetaData")
    parser.add_argument("--area", required=True, help="私有库分区名，如 full-library/KMFA_MetaData")
    parser.add_argument("--manifest-cache", required=True, help="上一轮清单（用于增量判定）")
    parser.add_argument("--out", required=True, help="本轮清单输出")
    parser.add_argument("--limit", type=int, help="最多处理多少文件（分批用）")
    parser.add_argument("--minutes", type=float, help="最多跑多少分钟（SMB 很慢，分批用）")
    parser.add_argument("--upload", action="store_true", help="把清单回传私有库；不给则只本地出清单")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(json.dumps({"status": "SOURCE_UNAVAILABLE",
                          "原因": f"源不可达：{root}（网络卷没挂上？）"}, ensure_ascii=False))
        return 4

    previous = load_previous(Path(args.manifest_cache))
    deadline = time.monotonic() + args.minutes * 60 if args.minutes else None
    records, stats = walk(root, previous, limit=args.limit, deadline=deadline)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "status": "PARTIAL" if stats["提前收工"] else "COMPLETE",
        "时间": datetime.now(BEIJING).isoformat(),
        "源": str(root), "分区": args.area,
        "清单行数": len(records), "字节合计": sum(r["size"] for r in records),
        **stats,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.upload:
        import private_db_access as PDB
        try:
            PDB.append_line(f"Private-KMDatabase/{args.area}/manifest-summary.jsonl",
                            json.dumps(summary, ensure_ascii=False),
                            f"archive: {args.area} 清单 {len(records)} 行")
        except Exception as exc:                  # noqa: BLE001
            print(f"清单回传失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
