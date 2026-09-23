#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C4 人工单价工具（仅 Python 3 标准库，可离线跑）。

用途：读 `人工单价.csv`，把不同单位的价格统一成「元/日」，按省×工种汇总，
比较定额价与市场价的差距，并按「人天 × 日薪 × (1+附加率)」正着算人工成本。

用法：
    python3 labor_cost.py summary 人工单价.csv            # 按省×类型汇总日薪
    python3 labor_cost.py gap 人工单价.csv                # 定额 vs 市场 比值
    python3 labor_cost.py cost --days 40 --daily 450 --overhead 0.25
    python3 labor_cost.py test                            # 跑自带测试

单位换算约定（写死在这里，改口径就改这里）：
    元/工日、元/天、元/日 → 原值
    元/小时 → ×8
    元/月   → ÷21.75（国家规定月计薪天数）
    元/年   → ÷(21.75×12)
区间价「300-400」取中点；无法解析的价格跳过并计数，不猜。
"""
import csv
import re
import statistics
import sys
import unittest
from collections import defaultdict

MONTH_PAY_DAYS = 21.75
HOURS_PER_DAY = 8

UNIT_FACTORS = [
    (re.compile(r"工日|/天|/日|每天|日薪"), 1.0),
    (re.compile(r"小时|/时|时薪"), float(HOURS_PER_DAY)),
    (re.compile(r"月"), 1.0 / MONTH_PAY_DAYS),
    (re.compile(r"年"), 1.0 / (MONTH_PAY_DAYS * 12)),
]

_NUM = re.compile(r"\d+(?:\.\d+)?")


def parse_price(text):
    """'350' → 350.0；'300-400' / '300～400' → 350.0；解析不了 → None。"""
    if text is None:
        return None
    nums = [float(x) for x in _NUM.findall(str(text).replace(",", "").replace("，", ""))]
    if not nums:
        return None
    if len(nums) >= 2 and re.search(r"[-~～—至到]", str(text)):
        return (nums[0] + nums[1]) / 2
    return nums[0]


def to_daily(price, unit):
    """按单位把价格换成元/日；单位不认识 → None。"""
    if price is None or not unit:
        return None
    for pat, factor in UNIT_FACTORS:
        if pat.search(unit):
            return round(price * factor, 2)
    return None


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out, skipped = [], 0
    for r in rows:
        daily = to_daily(parse_price(r.get("价格")), r.get("单位", ""))
        if daily is None:
            skipped += 1
            continue
        r["日薪"] = daily
        out.append(r)
    return out, skipped


def is_quota(row):
    return "定额" in row.get("类型", "")


def summary(rows):
    """{(省份, 类型): [中位日薪, 条数]}"""
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("省份", ""), r.get("类型", ""))].append(r["日薪"])
    return {k: [round(statistics.median(v), 2), len(v)] for k, v in sorted(groups.items())}


def gap(rows):
    """每省：市场中位日薪 / 定额中位日薪。任一侧缺数据 → 该省不出比值。"""
    quota, market = defaultdict(list), defaultdict(list)
    for r in rows:
        (quota if is_quota(r) else market)[r.get("省份", "")].append(r["日薪"])
    res = {}
    for prov in sorted(set(quota) | set(market)):
        q = statistics.median(quota[prov]) if quota[prov] else None
        m = statistics.median(market[prov]) if market[prov] else None
        ratio = round(m / q, 3) if q and m else None
        res[prov] = {"定额中位": q, "市场中位": m, "市场/定额": ratio}
    return res


def labor_cost(days, daily, overhead=0.0):
    """人天 × 日薪 × (1+附加率)。附加率 = 社保/管理费/利润等，调用方按口径给。"""
    if days < 0 or daily < 0 or overhead < 0:
        raise ValueError("人天、日薪、附加率都不能为负")
    return round(days * daily * (1 + overhead), 2)


def _cli(argv):
    if not argv or argv[0] == "test":
        unittest.main(argv=[sys.argv[0]], exit=True)
    cmd = argv[0]
    if cmd == "cost":
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--days", type=float, required=True)
        p.add_argument("--daily", type=float, required=True)
        p.add_argument("--overhead", type=float, default=0.0)
        a = p.parse_args(argv[1:])
        print(labor_cost(a.days, a.daily, a.overhead))
        return
    rows, skipped = load_rows(argv[1])
    print(f"# 有效 {len(rows)} 行，价格/单位无法解析跳过 {skipped} 行")
    if cmd == "summary":
        for (prov, typ), (med, n) in summary(rows).items():
            print(f"{prov},{typ},中位日薪={med},n={n}")
    elif cmd == "gap":
        for prov, d in gap(rows).items():
            print(f"{prov},定额中位={d['定额中位']},市场中位={d['市场中位']},市场/定额={d['市场/定额']}")
    else:
        sys.exit(f"未知命令 {cmd}")


class _Tests(unittest.TestCase):
    def test_parse_price(self):
        self.assertEqual(parse_price("350"), 350.0)
        self.assertEqual(parse_price("300-400"), 350.0)
        self.assertEqual(parse_price("6,500"), 6500.0)
        self.assertEqual(parse_price("300～400元"), 350.0)
        self.assertIsNone(parse_price("未查到"))

    def test_to_daily(self):
        self.assertEqual(to_daily(350, "元/工日"), 350)
        self.assertEqual(to_daily(50, "元/小时"), 400)
        self.assertEqual(to_daily(6525, "元/月"), 300)
        self.assertIsNone(to_daily(100, "吨"))

    def test_gap_and_summary(self):
        rows = [
            {"省份": "甲省", "类型": "定额官方", "日薪": 200.0},
            {"省份": "甲省", "类型": "市场招聘", "日薪": 300.0},
            {"省份": "甲省", "类型": "市场招聘", "日薪": 400.0},
            {"省份": "乙省", "类型": "市场招聘", "日薪": 300.0},
        ]
        g = gap(rows)
        self.assertEqual(g["甲省"]["市场/定额"], 1.75)
        self.assertIsNone(g["乙省"]["市场/定额"])
        self.assertEqual(summary(rows)[("甲省", "市场招聘")], [350.0, 2])

    def test_labor_cost(self):
        self.assertEqual(labor_cost(40, 450, 0.25), 22500.0)
        with self.assertRaises(ValueError):
            labor_cost(-1, 100)

    def test_load_rows(self):
        import os, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("省份,类型,单位,价格\n甲省,定额官方,元/工日,120\n甲省,市场招聘,元/月,未查到\n")
        try:
            rows, skipped = load_rows(f.name)
            self.assertEqual((len(rows), skipped), (1, 1))
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    _cli(sys.argv[1:])
