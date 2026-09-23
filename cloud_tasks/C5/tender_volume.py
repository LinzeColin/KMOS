#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C5 非主业类别公开标量统计工具（仅 Python 3 标准库，可离线跑）。

云端环境打不开招标平台，只能拿到搜索可见的少量样例。本工具留给能上国内网的
本地 agent：把从招标平台导出/抓到的公告清单（CSV：标题,日期,URL[,正文]）喂进来，
自动完成 归类 → 去重 → 窗口过滤 → 除以工作日数 → 金额分档。

用法：
    python3 tender_volume.py count 公告.csv --start 2026-07-25 --end 2026-09-23 \
        [--holidays 2026-10-01,2026-10-02] [--workdays 2026-09-20]
    python3 tender_volume.py test

说明：
- 工作日 = 周一到周五，去掉 --holidays，加上 --workdays（调休上班日）。
  节假日表**不写死**：法定假日安排以国务院办公厅当年通知为准，由调用方传入。
- 一条公告可命中多个类别（如"风机及电机检修"），各类别都计 1 条。
- 去重键：URL；URL 为空时用「标题+日期」。
"""
import argparse
import csv
import re
import sys
import unittest
from collections import defaultdict
from datetime import date, timedelta

# 类别 → 关键词正则。顺序无关；按需增删。
CATEGORIES = {
    "皮带机/输送机维修": r"皮带机|输送机|输送带|皮带.{0,4}(维修|检修|更换)|托辊",
    "钢结构制作安装": r"钢结构",
    "工业管道安装": r"管道.{0,6}(安装|施工|改造)|压力管道",
    "设备年度维保(包干)": r"年度.{0,8}(维保|维护|检修)|维保.{0,4}(包干|框架)|包干.{0,6}(维修|维护|检修)",
    "除尘器/收尘改造": r"除尘|收尘",
    "阀门泵类检修": r"阀门|泵.{0,6}(维修|检修|修理)|(水|油|渣浆|循环)泵",
    "起重设备维修": r"起重|行车|桥式?吊|门式?吊|天车|电动葫芦",
    "耐磨防腐": r"耐磨|防腐|堆焊|陶瓷贴片",
    "机加工外协": r"机加工|机械加工|外协加工|零部件加工",
    "锅炉辅机检修": r"锅炉",
    "风机检修": r"风机",
    "电机维修": r"电机.{0,6}(维修|检修|修理|修复)|电动机.{0,4}(维修|检修|修理)",
    "液压系统检修": r"液压",
    "破碎机维修": r"破碎机",
    "斗式提升机维修": r"斗式?提升机|斗提",
    "耐火材料砌筑/检修": r"耐火|浇注料|窑衬|砌筑",
    "设备保温": r"保温",
}
_CAT_RE = {k: re.compile(v) for k, v in CATEGORIES.items()}

_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(万元|万|元)")
# 金额分档边界（元）
BANDS = [(0, 100_000, "<10万"), (100_000, 500_000, "10-50万"), (500_000, 2_000_000, "50-200万"),
         (2_000_000, 10_000_000, "200-1000万"), (10_000_000, float("inf"), ">=1000万")]


def classify(text):
    return [k for k, rx in _CAT_RE.items() if rx.search(text or "")]


def parse_amount(text):
    """返回文本里第一个金额（元）；没有 → None。'35.6万元' → 356000.0。"""
    m = _AMOUNT.search((text or "").replace(",", "").replace("，", ""))
    if not m:
        return None
    v = float(m.group(1))
    return v * 10_000 if m.group(2).startswith("万") else v


def band(amount):
    if amount is None:
        return "金额未披露"
    for lo, hi, name in BANDS:
        if lo <= amount < hi:
            return name
    return "金额未披露"


def workdays(start, end, holidays=(), extra_workdays=()):
    hol, extra = set(holidays), set(extra_workdays)
    n, d = 0, start
    while d <= end:
        if (d.weekday() < 5 and d not in hol) or d in extra:
            n += 1
        d += timedelta(days=1)
    return n


def _d(s):
    return date.fromisoformat(s.strip()[:10])


def count(rows, start, end, holidays=(), extra_workdays=()):
    """rows: [{'标题','日期','URL','正文'?}] → {类别: {'条数','每工作日','金额档':{档:n}}}"""
    wd = workdays(start, end, holidays, extra_workdays)
    seen, per = set(), defaultdict(lambda: {"条数": 0, "金额档": defaultdict(int)})
    for r in rows:
        try:
            d = _d(r.get("日期", ""))
        except ValueError:
            continue
        if not (start <= d <= end):
            continue
        key = r.get("URL") or (r.get("标题", "") + r.get("日期", ""))
        if key in seen:
            continue
        seen.add(key)
        text = r.get("标题", "") + " " + r.get("正文", "")
        for cat in classify(text):
            per[cat]["条数"] += 1
            per[cat]["金额档"][band(parse_amount(text))] += 1
    out = {}
    for cat in CATEGORIES:
        c = per.get(cat, {"条数": 0, "金额档": {}})
        out[cat] = {"条数": c["条数"], "工作日": wd,
                    "每工作日": round(c["条数"] / wd, 2) if wd else None,
                    "金额档": dict(c["金额档"])}
    return out


def _cli(argv):
    if not argv or argv[0] == "test":
        unittest.main(argv=[sys.argv[0]], exit=True)
    p = argparse.ArgumentParser()
    p.add_argument("cmd")
    p.add_argument("csv")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--holidays", default="")
    p.add_argument("--workdays", default="")
    a = p.parse_args(argv)
    split = lambda s: [_d(x) for x in s.split(",") if x.strip()]
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    res = count(rows, _d(a.start), _d(a.end), split(a.holidays), split(a.workdays))
    print("类别,窗口内条数,工作日数,每工作日条数,金额档分布")
    for cat, r in res.items():
        bands = ";".join(f"{k}:{v}" for k, v in sorted(r["金额档"].items()))
        print(f"{cat},{r['条数']},{r['工作日']},{r['每工作日']},{bands}")


class _Tests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("某水泥公司2026年皮带机维修项目招标公告"), ["皮带机/输送机维修"])
        self.assertIn("风机检修", classify("风机及电机检修框架采购"))
        self.assertIn("电机维修", classify("风机及电机检修框架采购"))
        self.assertEqual(classify("办公用品采购"), [])

    def test_amount_and_band(self):
        self.assertEqual(parse_amount("最高限价：35.6万元"), 356000.0)
        self.assertEqual(parse_amount("预算金额 1,200,000 元"), 1200000.0)
        self.assertIsNone(parse_amount("金额见附件"))
        self.assertEqual(band(356000.0), "10-50万")
        self.assertEqual(band(None), "金额未披露")

    def test_workdays(self):
        # 2026-09-21(一) ~ 2026-09-27(日)：5 个工作日；去掉 9-25，加回 9-27 → 5
        s, e = date(2026, 9, 21), date(2026, 9, 27)
        self.assertEqual(workdays(s, e), 5)
        self.assertEqual(workdays(s, e, [date(2026, 9, 25)], [date(2026, 9, 27)]), 5)

    def test_count_dedupe_window(self):
        rows = [
            {"标题": "皮带机维修招标 限价20万元", "日期": "2026-09-22", "URL": "u1"},
            {"标题": "皮带机维修招标 限价20万元", "日期": "2026-09-22", "URL": "u1"},  # 重复
            {"标题": "皮带机维修", "日期": "2026-06-01", "URL": "u2"},  # 窗口外
            {"标题": "输送机检修", "日期": "2026-09-23", "URL": "u3"},
            {"标题": "坏日期", "日期": "不详", "URL": "u4"},
        ]
        r = count(rows, date(2026, 9, 21), date(2026, 9, 25))
        c = r["皮带机/输送机维修"]
        self.assertEqual((c["条数"], c["工作日"], c["每工作日"]), (2, 5, 0.4))
        self.assertEqual(c["金额档"], {"10-50万": 1, "金额未披露": 1})


if __name__ == "__main__":
    _cli(sys.argv[1:])
