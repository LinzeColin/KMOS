#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retired legacy project-margin generator.

The former implementation treated the larger of two incomplete cost views as
a cost floor and published the remainder as a margin upper bound.  That output
could reach 100% when project labour was unallocated, so it is not a safe
business metric and must never be generated again.

Use the governed ``项目成本表`` Skill and its ``/public-api/项目成本`` runtime
projection.  That path publishes gross profit and gross margin only after the
revenue and full project-cost basis pass the fail-closed completeness gates.
"""

from __future__ import annotations

import sys


RETIREMENT_MESSAGE = (
    "build_project_margin.py 已下线：禁止用不完整成本生成毛利上限。"
    "请运行 项目成本表 Skill，并使用 /public-api/项目成本。"
)


def main() -> int:
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
