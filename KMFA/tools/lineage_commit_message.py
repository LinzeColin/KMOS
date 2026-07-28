#!/usr/bin/env python3
"""把 `lineage_graph build` 的摘要拼成提交信息。

放成脚本而不是塞进 workflow 的 shell：嵌在 YAML 里的多行 `$(...)` 会把 YAML 撑破
（本次就撞上了），而且埋在 CI 里的逻辑测不到。

用法：python3 KMFA/tools/lineage_commit_message.py <build.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SUBJECT = "chore(kmfa): 血缘图随新资产重建（机械产出，勿手改）"
TRAILER = "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
#: 表名清单动辄十几项，摘要里放不下也没意义——图本身就有。
SKIP = {"staging_tables"}


def render(summary: dict) -> str:
    lines = [SUBJECT, ""]
    if summary.get("extractions_source") == "existing_lineage":
        lines += [
            "抽取账本（DuckDB）这次够不着，已有的边从上一版图原样带过来，",
            "新资产记为 not_yet_extracted——不是重新对过账。",
            "",
        ]
    lines += [f"{key}: {value}" for key, value in summary.items() if key not in SKIP]
    lines += ["", TRAILER]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：lineage_commit_message.py <build.json>", file=sys.stderr)
        return 2
    summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(render(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
