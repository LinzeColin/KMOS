#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目成本表输出：**一行不差复刻业务原报表格式**（Owner 2026-07-26 要求）。

Owner：「你最后提供的格式要和我一模一样，按正规财务税务银行政府交付的标准去做」。
行序、层级、编号、括号写法全部照抄源报表；金额右对齐、千分位、两位小数。

两套模板（源报表本身就有两套，实测确认）：
  A —— 终行为「合计支出」+「（七）毛利」，分摊管理费/资金利息在「三」下
  B —— 二级到「（八）」（税金、分摊管理费入二级），终行为「三 利润」，多一行「项目产值」

口径声明（交付件必须自带，供银行/税务核查）：
  · 毛利统一按「合同额 − 合计支出」重算；源报表中与其表内数据不自洽者逐项标注。
  · 二级小计留空时由其下级明细回填；「分摊的管理费用（合同的2%）」缺值时按合同额×2% 计。
"""
from __future__ import annotations
import argparse, json, sys
from decimal import Decimal
from pathlib import Path

TPL_A = [
    ("合同编号", "key"), ("", "blank"), ("一、合同额", "contract"),
    ("二、资金运用及各项支出", "sec2"),
    ("（一）原材料", "l2"), ("其中:1.主要材料", "d"), ("2.辅助材料", "d"),
    ("2.1气体", "d"), ("2.2焊材", "d"), ("2.3漆料", "d"), ("2.4低值易损耗材", "d"),
    ("3 外协 加工费", "d"),
    ("（二）租赁费", "l2"), ("其中:1.吊车租赁费", "d"), ("2.脚手架租赁费", "d"), ("3.物流运输费", "d"),
    ("（三）保险费", "l2"),
    ("（四）现场管理费", "l2"), ("1.管理人员工资", "d"), ("2.差旅费", "d"), ("2.1车票", "d"),
    ("2.2住宿", "d"), ("3.业务费用", "d"), ("3.1招待费", "d"), ("4.生活费用", "d"),
    ("4.1生活用品", "d"), ("4.2生活费", "d"), ("5.工程车辆使用费", "d"), ("5.1加油费及保养", "d"),
    ("5.2过路、停车费", "d"), ("5.3维修费", "d"), ("6.办公费", "d"), ("7.安全防护费", "d"),
    ("8.房租", "d"), ("9.临电", "d"), ("10.体检及工伤支出等", "d"), ("11.罚款", "d"), ("12.挂靠管理费", "d"),
    ("（五）工资（承包费）支出", "l2"), ("（六）信息费", "l2"),
    ("三 1.1分摊的管理费用（合同的2%）", "extra"), ("1.2占用的资金利息", "extra"),
    ("合计支出", "total"), ("（七）毛利", "profit"),
]
TPL_B = [
    ("合同编号", "key"), ("", "blank"), ("一、合同额", "contract"), ("项目产值", "output_value"),
    ("二、资金运用及各项支出", "sec2"),
    ("（一）原材料", "l2"), ("采购材料", "d"),
    ("（二）租赁费", "l2"), ("其中:1.机械费", "d"),
    ("（三）保险费", "l2"),
    ("（四）现场管理费", "l2"), ("1.自有人员工资", "d"), ("2.差旅费", "d"), ("3.招待费", "d"),
    ("4.运输费", "d"), ("5.办公费", "d"), ("6.房租", "d"), ("7.水电费", "d"),
    ("8.备用金", "d"), ("9.其他费用", "d"),
    ("（五）工资（承包费）支出", "l2"), ("外协人员工资", "d"), ("外协人员生活费", "d"), ("临时用工费用", "d"),
    ("（六）信息费", "l2"), ("（七）税金", "l2"), ("（八） 分摊的管理费用（合同的2%）", "l2"),
    ("已发生尚未支付费用", "d"), ("三 利润", "profit"),
]


def fmt(v) -> str:
    if v is None or v == "":
        return ""
    try:
        d = Decimal(str(v))
    except Exception:
        return str(v)
    return f"{d:,.2f}"


def rows_for(project: dict) -> list[tuple[str, str]]:
    """按模板行序产出 (行标签, 金额文本)；缺值留空，绝不臆造。"""
    tpl = TPL_A if str(project.get("template", "A")).upper() == "A" else TPL_B
    l2 = {i["label"]: i["amount"] for i in project.get("l2", [])}
    extra = project.get("extra", {}) or {}
    out = []
    for label, kind in tpl:
        v = ""
        if kind == "blank":
            v = ""
        elif kind == "key":
            v = project.get("contract_no", "") or ""
        elif kind == "contract":
            v = fmt(project.get("contract"))
        elif kind == "output_value":
            v = fmt(project.get("output_value"))
        elif kind == "sec2":
            v = fmt(project.get("sec2"))
        elif kind == "total":
            v = fmt(project.get("total_expense"))
        elif kind == "profit":
            v = fmt(project.get("gross_profit_recomputed") or project.get("profit"))
        elif kind == "l2":
            for k, amt in l2.items():
                if k.replace(" ", "")[:6] in label.replace(" ", ""):
                    v = fmt(amt); break
        elif kind == "extra":
            for k, amt in extra.items():
                if ("分摊" in label and "分摊" in k) or ("利息" in label and "利息" in k):
                    v = fmt(amt); break
        out.append((label, v))
    return out


def to_csv(project: dict) -> str:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["项目", project.get("name") or project.get("file", "")])
    w.writerow(["", "金额（元）"])
    for label, v in rows_for(project):
        w.writerow([label, v])
    note = project.get("caliber_note")
    if note:
        w.writerow([]); w.writerow(["口径声明", note])
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description="按业务原格式渲染项目成本表")
    ap.add_argument("--baseline", required=True, help="a0_baseline_v6.json（私有）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--format", default="csv", choices=("csv",))
    a = ap.parse_args()
    data = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
    outd = Path(a.out_dir); outd.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in data.get("projects", []):
        stem = Path(str(p.get("file", f"project_{n}"))).stem
        (outd / f"{stem}.csv").write_text(to_csv(p), encoding="utf-8-sig")
        n += 1
    print(f"✓ 已渲染 {n} 份，输出目录 {outd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
