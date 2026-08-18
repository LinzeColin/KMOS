#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_tools_index.py —— 生成 KMFA/tools 与 KMFA/tests 的导航索引

为什么需要它（2026-08-19 实测）：
  列一次 KMFA/tools 目录 = 854 个条目 / 66184 字符 ≈ **16546 tokens**
  列一次 KMFA/tests     = 470 个条目 / 36167 字符 ≈  9041 tokens
  agent 每探索一次 KMFA 就要付掉两万五千 token，而其中 1033 个文件
  （683 个 v013/v014 冻结阶段校验器 + 350 个配套测试）是已完成阶段的产物，
  agent 几乎永远不需要逐个看。文件名中位数 59 字符、最长 207 字符 ——
  名字本身就是成本。

  这些文件不能移也不能删：KMFA/tests 里的测试真的
  `from KMFA.tools.check_v013_... import`，移动会断 import，
  删除会连带删掉治理证据链。所以改成让 agent **不必列目录**：
  读这份 2KB 的索引（≈500 tokens）代替 66KB 的目录列表，省约 16000 tokens。

索引是**生成的**，不是手写的 —— 手写的索引第二天就过期，
然后所有人继续列目录。CI 跑 --check，对不上就红。

用法:
  python3 KMFA/tools/build_tools_index.py            # 写入 KMFA/tools/INDEX.md
  python3 KMFA/tools/build_tools_index.py --check    # 只校验是否最新（CI 用）
退出码: 0=OK  1=索引过期（--check 模式）
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

FROZEN = re.compile(r"^(check_)?v01[34]_")
HEADER = "<!-- 本文件由 KMFA/tools/build_tools_index.py 生成。请勿手写——下次生成会覆盖。 -->"


def scan(root: Path):
    tools = root / "KMFA" / "tools"
    tests = root / "KMFA" / "tests"
    frozen_t = sorted(p.name for p in tools.glob("*.py") if FROZEN.match(p.name))
    live_top = sorted(p.name for p in tools.glob("*.py") if not FROZEN.match(p.name))
    subdirs = defaultdict(list)
    for p in sorted(tools.rglob("*.py")):
        rel = p.relative_to(tools)
        if len(rel.parts) > 1:
            subdirs[rel.parts[0]].append(rel.parts[-1])
    frozen_tests = sorted(p.name for p in tests.glob("test_v01[34]_*.py")) if tests.is_dir() else []
    live_tests = ([p.name for p in tests.glob("*.py")
                   if not re.match(r"^test_v01[34]_", p.name)] if tests.is_dir() else [])
    return frozen_t, live_top, subdirs, frozen_tests, sorted(live_tests)


def render(root: Path) -> str:
    frozen_t, live_top, subdirs, frozen_tests, live_tests = scan(root)
    total = len(frozen_t) + len(live_top) + sum(len(v) for v in subdirs.values())
    out = [HEADER, "", "# KMFA/tools 导航索引", "",
           "**先读这里，不要列目录。** 列 `KMFA/tools` 要 ≈16500 tokens，读这份 ≈500。", "",
           "## 一、别看的那部分", "",
           f"- `KMFA/tools/` 里有 **{len(frozen_t)}** 个 `v013_*` / `v014_*` / `check_v01*_*` 开头的文件，"
           f"是**已完成阶段的冻结校验器**。",
           f"- `KMFA/tests/` 里有 **{len(frozen_tests)}** 个对应的 `test_v01*` 测试。",
           "- 它们近 30 天零改动。**除非你在查某个具体阶段的历史结论，否则不要浏览它们**；",
           "  要找就用精确文件名 grep，不要列目录、不要通配。",
           "- 为什么不删：`KMFA/tests` 里的测试真的 `from KMFA.tools.check_v01... import`，",
           "  移动会断 import，删除会连带断掉治理证据链。", "",
           "## 二、日常要用的部分", "",
           f"### 顶层活跃脚本（{len(live_top)} 个）", ""]
    for n in live_top:
        out.append(f"- `{n}`")
    out += ["", "### 按子目录", ""]
    for d in sorted(subdirs):
        names = [n for n in subdirs[d] if not FROZEN.match(n)]
        out.append(f"- **`{d}/`** —— {len(names)} 个：" + "、".join(f"`{n}`" for n in sorted(names)[:8])
                   + ("…" if len(names) > 8 else ""))
    out += ["", "### 活跃测试", "",
            f"`KMFA/tests/` 里非 `test_v01*` 的共 **{len(live_tests)}** 个。", "",
            "---", "",
            f"统计：tools 共 {total} 个 .py（冻结 {len(frozen_t)} / 活跃 {total - len(frozen_t)}），"
            f"tests 冻结 {len(frozen_tests)} / 活跃 {len(live_tests)}。", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    target = root / "KMFA" / "tools" / "INDEX.md"
    body = render(root)
    if args.check:
        cur = target.read_text(encoding="utf-8") if target.is_file() else None
        if cur != body:
            print("FAIL: KMFA/tools/INDEX.md 已过期。跑 python3 KMFA/tools/build_tools_index.py 重新生成。")
            return 1
        print("PASS: KMFA/tools/INDEX.md 与目录一致")
        return 0
    target.write_text(body, encoding="utf-8")
    print(f"已生成 {target}（{len(body)} 字符）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
