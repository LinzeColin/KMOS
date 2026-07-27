# -*- coding: utf-8 -*-
"""项目成本表输出格式回归：行序/行数必须与业务原报表一致（Owner：格式要一模一样）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "project_cost"))
import render_report as R


def _demo(tpl):
    return {"file": f"demo{tpl}.pdf", "template": tpl, "contract_no": "HT-1",
            "contract": "100.00", "sec2": "80.00", "total_expense": "85.00",
            "gross_profit_recomputed": "15.00", "output_value": "90.00",
            "l2": [{"label": "（一）原材料", "amount": "50.00"}], "extra": {"分摊管理费": "2.00"}}


def test_template_a_row_count_and_order():
    rows = R.rows_for(_demo("A"))
    assert len(rows) == 44, f"模板A 应 44 行（源报表结构），实得 {len(rows)}"
    labels = [l for l, _ in rows]
    assert labels[0] == "合同编号" and labels[1] == ""
    assert labels[2] == "一、合同额"
    assert labels[3] == "二、资金运用及各项支出"
    assert labels[-2] == "合计支出" and labels[-1] == "（七）毛利"


def test_template_b_ends_with_profit():
    rows = R.rows_for(_demo("B"))
    labels = [l for l, _ in rows]
    assert labels[2] == "一、合同额" and labels[3] == "项目产值"
    assert labels[-1] == "三 利润"
    assert "（七）税金" in labels and "（八） 分摊的管理费用（合同的2%）" in labels


def test_amount_formatting_thousands_two_decimals():
    assert R.fmt("1234567.5") == "1,234,567.50"
    assert R.fmt(None) == "" and R.fmt("") == ""


def test_never_fabricates_missing_values():
    d = _demo("A"); d["l2"] = []; d["extra"] = {}
    vals = [v for l, v in R.rows_for(d) if l.startswith("（一）")]
    assert vals == [""], "缺值必须留空，不得臆造"
