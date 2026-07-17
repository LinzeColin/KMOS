#!/usr/bin/env python3
"""KMDatabase/data 内容寻址入仓工具（TSK.KMFA.DATA.0001，设计依据：打通任务包 09 三节 v2 / D11）。

用法：
  python3 KMDatabase/machine/tools/ingest_data.py add <文件或目录...> --domain 财务 [--batch 2026-07-16] [--dry-run] [--target <dir>]
  python3 KMDatabase/machine/tools/ingest_data.py verify [--target <dir>]
  python3 KMDatabase/machine/tools/ingest_data.py --selftest

约定（与 data/README.md 一致）：
  - objects/<sha256 前 2 位>/<sha256>_<原文件名>：内容寻址——同名不同内容天然共存，永不互相覆盖。
  - manifest.jsonl：append-only 账本，一行一文件（原名/批次/域/sha256/大小/来源路径）。
  - 幂等：同 sha256 已登记则跳过（重复 add 无副作用）。
  - 凭据红线：凭据类文件名/扩展名直接拒绝；小文本文件做密钥模式扫描，命中即拒绝。
  - >95MB 的文件拒绝并提示走 Git LFS（GitHub 单文件 100MB 硬限制）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import shutil
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

REPO_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MAX_PLAIN_SIZE = 95 * 1024 * 1024
DOMAINS = ("财务", "WPS钉钉红圈", "绩效", "预算", "对账基准", "其他")
CREDENTIAL_NAME_PATTERNS = (
    re.compile(r"\.env(\.|$)"),
    re.compile(r"\.(pem|key|p12|pfx|keychain)$", re.I),
    re.compile(r"(^|[._-])(token|secret|credential|cookie|passwd|password)s?([._-]|\.|$)", re.I),
    re.compile(r"^id_(rsa|ed25519|ecdsa|dsa)", re.I),
)
CREDENTIAL_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\."),
)
TEXT_SCAN_EXTS = {".txt", ".md", ".csv", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".html", ".py", ".sh"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def credential_name_hit(name: str) -> bool:
    return any(pattern.search(name) for pattern in CREDENTIAL_NAME_PATTERNS)


def credential_content_hit(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SCAN_EXTS or path.stat().st_size > 5 * 1024 * 1024:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for pattern in CREDENTIAL_CONTENT_PATTERNS:
        found = pattern.search(text)
        if found:
            return found.group(0)[:24]
    return None


def iter_files(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser()
        if path.is_symlink():
            raise SystemExit(f"拒绝符号链接: {path}")
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and not child.is_symlink() and child.name not in SKIP_NAMES:
                    files.append(child)
        elif path.is_file():
            if path.name not in SKIP_NAMES:
                files.append(path)
        else:
            raise SystemExit(f"路径不存在: {path}")
    return files


def load_manifest(manifest_path: Path) -> dict[str, dict]:
    known: dict[str, dict] = {}
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                known[row["sha256"]] = row
    return known


def cmd_add(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser() if args.target else REPO_DATA_DIR
    manifest_path = target / "manifest.jsonl"
    objects_dir = target / "objects"
    known = load_manifest(manifest_path)
    batch = args.batch or date.today().isoformat()
    added, skipped, rejected = [], [], []

    for src in iter_files(args.paths):
        name = unicodedata.normalize("NFC", src.name)
        if credential_name_hit(name):
            rejected.append((src, "凭据类文件名"))
            continue
        hit = credential_content_hit(src)
        if hit:
            rejected.append((src, f"内容疑似凭据（{hit}…）"))
            continue
        size = src.stat().st_size
        if size > MAX_PLAIN_SIZE:
            rejected.append((src, f"{size/1048576:.0f}MB 超过 95MB——先配置 Git LFS 再入仓"))
            continue
        digest = sha256_of(src)
        if digest in known:
            skipped.append((src, digest))
            continue
        object_rel = f"objects/{digest[:2]}/{digest}_{name}"
        row = {
            "sha256": digest,
            "original_name": name,
            "size_bytes": size,
            "domain": args.domain,
            "batch": batch,
            "source_path": str(src),
            "object_path": object_rel,
            "ingested_at": args.now or date.today().isoformat(),
        }
        if not args.dry_run:
            dest = target / object_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            shutil.copy2(src, tmp)
            if sha256_of(tmp) != digest:
                tmp.unlink(missing_ok=True)
                raise SystemExit(f"复制后哈希不一致: {src}")
            os.replace(tmp, dest)
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        known[digest] = row
        added.append((src, digest))

    mode = "DRY-RUN " if args.dry_run else ""
    print(f"{mode}入仓 {len(added)} 个，幂等跳过 {len(skipped)} 个，拒绝 {len(rejected)} 个（域={args.domain} 批次={batch}）")
    for src, why in rejected:
        print(f"  ✗ {src.name}: {why}")
    return 1 if rejected else 0


def cmd_verify(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser() if args.target else REPO_DATA_DIR
    manifest_path = target / "manifest.jsonl"
    known = load_manifest(manifest_path)
    bad = 0
    for digest, row in known.items():
        obj = target / row["object_path"]
        if not obj.exists():
            print(f"✗ 缺对象: {row['object_path']}")
            bad += 1
        elif sha256_of(obj) != digest:
            print(f"✗ 哈希不符: {row['object_path']}")
            bad += 1
    orphans = 0
    objects_dir = target / "objects"
    if objects_dir.exists():
        manifest_objects = {row["object_path"] for row in known.values()}
        for obj in objects_dir.rglob("*"):
            if obj.is_file() and str(obj.relative_to(target)) not in manifest_objects:
                print(f"✗ 账外对象: {obj.relative_to(target)}")
                orphans += 1
    print(f"verify: {len(known)} 条账目，损坏/缺失 {bad}，账外 {orphans}")
    return 1 if (bad or orphans) else 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a报表.xlsx").write_bytes(b"alpha-bytes")
        (src_dir / "b.txt").write_text("plain business note")
        (src_dir / ".DS_Store").write_bytes(b"junk")
        (src_dir / "secrets.env").write_text("X=1")
        (src_dir / "note.md").write_text("-----BEGIN RSA PRIVATE KEY-----\nabc")
        target = tmp_path / "data"

        ns = argparse.Namespace(paths=[str(src_dir)], domain="其他", batch="2026-07-17", dry_run=False, target=str(target), now="2026-07-17")
        rc1 = cmd_add(ns)
        assert rc1 == 1, "凭据文件应被拒绝并返回非零"
        known = load_manifest(target / "manifest.jsonl")
        assert len(known) == 2, f"应入仓 2 个文件，实为 {len(known)}"
        rc2 = cmd_add(ns)
        assert rc2 == 1 and len(load_manifest(target / "manifest.jsonl")) == 2, "重复 add 必须幂等"
        same_name = src_dir / "a报表.xlsx"
        same_name.write_bytes(b"alpha-bytes-v2")
        ns2 = argparse.Namespace(paths=[str(same_name)], domain="其他", batch="2026-07-18", dry_run=False, target=str(target), now="2026-07-18")
        assert cmd_add(ns2) == 0
        rows = load_manifest(target / "manifest.jsonl")
        assert len(rows) == 3, "同名不同内容必须共存"
        assert cmd_verify(argparse.Namespace(target=str(target))) == 0
        obj = next((target / row["object_path"]) for row in rows.values() if row["batch"] == "2026-07-18")
        obj.write_bytes(b"corrupted")
        assert cmd_verify(argparse.Namespace(target=str(target))) == 1, "损坏必须被 verify 捕获"
    print("selftest: 全部通过")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="command")
    add_p = sub.add_parser("add", help="登记文件/目录进 data/")
    add_p.add_argument("paths", nargs="+")
    add_p.add_argument("--domain", required=True, choices=DOMAINS)
    add_p.add_argument("--batch", default=None, help="批次日期 YYYY-MM-DD，缺省=今天")
    add_p.add_argument("--dry-run", action="store_true")
    add_p.add_argument("--target", default=None, help="目标 data 目录（默认仓内 KMDatabase/data）")
    add_p.add_argument("--now", default=None, help=argparse.SUPPRESS)
    verify_p = sub.add_parser("verify", help="全量核对 manifest 与 objects 一致性")
    verify_p.add_argument("--target", default=None)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.command == "add":
        return cmd_add(args)
    if args.command == "verify":
        return cmd_verify(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
