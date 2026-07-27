# -*- coding: utf-8 -*-
"""科目→报表行 映射的回归测试。

这张表决定「按项目算出来的钱填进你那张表的哪一行」。最该防的两件事：
  · 钱被静默丢掉（映射到一个不存在的行，或科目没登记）；
  · 报表某一行无人认领（既没人往里填，也没说它算不出）。
两件都是"看着正常、数字是错的"，比崩溃危险得多。
"""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "project_cost"))
import account_map  # noqa: E402


def _data():
    return account_map.load(ROOT)


def test_live_map_passes_gate():
    assert account_map.check(_data()) == []


def test_every_template_row_is_accounted_for():
    """闭环性质：模板每一行要么有账可归、要么声明算不出、要么是派生行。"""
    d = _data()
    victim = d["unmappable_rows"].pop()
    errs = account_map.check(d)
    assert any("无人认领" in e for e in errs), f"漏掉一行竟没被发现：{victim}"


def test_mapping_to_nonexistent_row_is_rejected():
    """打错行名 = 那笔钱静默消失，报表还看着正常。"""
    d = _data()
    d["mappings"][0]["row"] = "（一）原材料费"          # 多一个字
    assert any("静默丢掉" in e for e in account_map.check(d))


def test_duplicate_account_is_rejected():
    d = _data()
    d["mappings"].append(dict(d["mappings"][0]))
    assert any("重复登记" in e for e in account_map.check(d))


def test_low_confidence_must_explain_itself():
    d = _data()
    m = next(x for x in d["mappings"] if x["confidence"] != "high")
    m["note"] = ""
    assert any("没写理由" in e for e in account_map.check(d))


def test_row_cannot_be_both_mapped_and_unmappable():
    d = _data()
    d["unmappable_rows"].append({"row": d["mappings"][0]["row"], "why": "自相矛盾"})
    assert any("自相矛盾" in e for e in account_map.check(d))


def test_summarize_refuses_to_drop_unknown_accounts():
    """账上冒出新科目时必须炸，不能默默少算。"""
    d = _data()
    with pytest.raises(KeyError, match="拒绝静默丢弃"):
        account_map.summarize(d, {"5001099-生产成本_新来的": "100.00"})


def test_summarize_merges_accounts_sharing_a_row():
    d = _data()
    same = [m["account"] for m in d["mappings"] if m["row"] == "3 外协 加工费"]
    assert len(same) >= 2, "外协费与加工费本应合并到同一行，样本失效"
    got = account_map.summarize(d, {same[0]: "10.00", same[1]: "5.50"})
    assert got["3 外协 加工费"] == Decimal("15.50")


def test_map_is_public_safe():
    """公开仓：只能有科目名与行标签，不得混入金额。"""
    import json
    import re
    raw = (ROOT / "machine" / "facts" / "project_cost_account_map.json").read_text(encoding="utf-8")
    assert "public_safe" in json.loads(raw)
    assert not re.search(r"\d{1,3}(,\d{3})+(\.\d+)?", raw), "映射表混入了金额"
