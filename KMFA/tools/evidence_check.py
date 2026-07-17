#!/usr/bin/env python3
"""断言证据链完整性检查（无会议对账制的可追溯承诺）。

校验 `KMFA/metadata/quality/assertions.jsonl`：
  1. 每条断言必须有 `evidence_ref` 且路径真实存在（仓库相对路径）；
  2. 指向目录时必须非空。
结构口径（不强制 human/machine 双子目录）：记录类单元=平铺 md 或仅 human/ 均可；
带机器产物的单元必须有 machine/。本工具只管「引用不悬空」这条硬线。
退出码 0=全通过，1=有悬空。自带 --selftest。
用法：python3 KMFA/tools/evidence_check.py [--assertions <path>] [--root <repo>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def check(assertions_path: Path, root: Path) -> tuple[int, list[str]]:
    problems = []
    total = 0
    for ln in assertions_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        total += 1
        o = json.loads(ln)
        aid = o.get("assertion_id", "<无 id>")
        ref = o.get("evidence_ref")
        if not ref:
            problems.append(f"{aid}: 缺 evidence_ref")
            continue
        p = root / ref
        if not p.exists():
            problems.append(f"{aid}: 悬空引用 {ref}")
        elif p.is_dir() and not any(p.iterdir()):
            problems.append(f"{aid}: 空目录引用 {ref}")
    return total, problems


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "有货").mkdir()
        (root / "有货" / "记录.md").write_text("x", encoding="utf-8")
        (root / "空壳").mkdir()
        aj = root / "assertions.jsonl"
        aj.write_text("\n".join([
            json.dumps({"assertion_id": "A1", "evidence_ref": "有货"}),
            json.dumps({"assertion_id": "A2", "evidence_ref": "不存在/路径"}),
            json.dumps({"assertion_id": "A3", "evidence_ref": "空壳"}),
            json.dumps({"assertion_id": "A4"}),
        ]), encoding="utf-8")
        total, problems = check(aj, root)
        assert total == 4 and len(problems) == 3, (total, problems)
        assert any("悬空" in p for p in problems)
        assert any("空目录" in p for p in problems)
        assert any("缺 evidence_ref" in p for p in problems)
    print("selftest: 全部通过")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assertions", default=str(REPO / "KMFA/metadata/quality/assertions.jsonl"))
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    total, problems = check(Path(args.assertions), Path(args.root))
    if problems:
        print(f"FAIL —— {len(problems)}/{total} 条证据链有问题")
        for p in problems:
            print(" ✗", p)
        return 1
    print(f"PASS —— {total} 条断言证据链全部可追溯（零悬空、零空目录）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
