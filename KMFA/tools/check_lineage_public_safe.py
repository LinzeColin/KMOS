#!/usr/bin/env python3
"""血缘图的 public-safe 边界门禁。

KMOS 是**公开仓**。`KMFA/machine/lineage.yaml` 由 `lineage_graph build` 机械生成，
其中每个节点带 `domain` 和 `batch`——这两个字段来自私有库的 raw 账本。今天它们是
分类名（`工资`、`KMFA金蝶明细账`），但账本是 Owner 那边写的，哪天有人在 batch 里
带上客户名或项目全称，就会顺着这条管线流进公开仓，而且没人会发现。

所以这道门禁盯的不是「现在有没有泄露」，而是「产物的形状有没有超出约定」：
  · 只允许出现约定内的键；
  · 值里不允许出现金额形态的长数字串；
  · 抽取来源必须写明——降级不能悄悄发生。

用法：python3 KMFA/tools/check_lineage_public_safe.py [路径]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "KMFA" / "machine" / "lineage.yaml"

#: 顶层与节点/边上允许出现的键。新增键要在这里显式登记——默认不放行。
ALLOWED_KEYS = {
    "schema", "generated_from", "extractions_source", "covered_categories",
    "raw_assets", "raw_with_staging_edges", "raw_deferred_all_sheets",
    "raw_not_yet_extracted", "staging_tables", "lineage_complete_v1",
    "lineage_complete_note", "nodes", "edges",
    "asset", "domain", "batch", "size_bytes", "status",
    "from", "to", "sheet_hash", "rows", "version",
}

#: 金额形态：带小数点两位、或带千分位。行数与字节数是裸整数，不会命中。
_MONEY = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2}(?!\d)")


def check(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")

    if "extractions_source:" not in text:
        problems.append("产物没写 extractions_source——DuckDB 降级会悄悄发生，"
                        "读图的人会以为刚跟抽取账本对过账")

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key = line.removeprefix("- ").split(":", 1)[0].strip()
        if key and not key.startswith("-") and ":" in line and key not in ALLOWED_KEYS:
            problems.append(f"{path.name}:{number} 出现未登记的键 {key!r}——"
                            f"公开面用白名单，新字段必须显式登记")
        value = line.split(":", 1)[1].strip() if ":" in line else ""
        if _MONEY.search(value):
            problems.append(f"{path.name}:{number} 值里出现金额形态的数字：{value[:60]!r}")
    return problems


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.is_file():
        print(f"缺 {path}", file=sys.stderr)
        return 2
    problems = check(path)
    if problems:
        for item in problems:
            print(f"::error::{item}")
        return 1
    print(f"PASS —— {path.name} 仍是 public-safe（键全在白名单内、无金额形态值、"
          f"抽取来源已声明）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
