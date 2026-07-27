# -*- coding: utf-8 -*-
"""项目毛利的口径边界测试。

这一页最容易出的错不是算错，是**把一个残缺的数说成完整的数**。
实测抓到过一次：初版按毛利率降序排，榜首六个项目全是「成本填 0、率 100%」——
它们不是最赚钱的六个，是数据最烂的六个。排序把最不该被信的行顶到了最显眼的位置。

所以这里测的重点是：残缺的数不能冒充完整的数，也不能排到前面去。
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# 同目录同侪用裸 import 互引（脚本式跑法），当包导入必须先把该目录放进 sys.path。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "project_cost"))

from build_project_margin import cost_confidence, data_flags, stage_of  # noqa: E402


def test_zero_cost_on_both_calibers_is_called_out_not_reported_as_full_margin():
    """成本两边都是 0 ⇒ 上限率必然 100%。这不是赚钱，是没数据，必须说出来。"""
    flags = data_flags(stage="已完工", revenue=Decimal("608000"),
                       business=Decimal(0), ledger=Decimal(0))
    assert any("一分钱成本都没落到它头上" in f for f in flags)


def test_business_ledger_blank_says_not_filled_rather_than_no_spend():
    """业务四项全空的含义是「没填」，不是「没花钱」——两者结论完全相反。"""
    flags = data_flags(stage="已完工", revenue=Decimal("100000"),
                       business=Decimal(0), ledger=Decimal("5000"))
    assert any("没填" in f for f in flags)


def test_kingdee_capturing_far_less_than_the_business_ledger_is_flagged():
    """金蝶远小于台账 ⇒ 大部分成本记去了『不分项目』，这个项目的账是残的。"""
    flags = data_flags(stage="已完工", revenue=Decimal("100000"),
                       business=Decimal("40000"), ledger=Decimal("3000"))
    assert any("不分项目" in f for f in flags)


def test_unfinished_projects_are_marked_as_not_final():
    flags = data_flags(stage="施工中", revenue=Decimal("100000"),
                       business=Decimal("30000"), ledger=Decimal("28000"))
    assert any("未完工" in f for f in flags)


def test_missing_contract_amount_admits_it_cannot_be_computed():
    flags = data_flags(stage="已完工", revenue=None,
                       business=Decimal("30000"), ledger=Decimal("28000"))
    assert any("算不出上限" in f for f in flags)


def test_negative_cost_is_flagged_rather_than_silently_boosting_the_margin():
    """红冲多于发生会让成本为负、毛利虚增——不标出来就是一个凭空变好看的数。"""
    flags = data_flags(stage="已完工", revenue=Decimal("100000"),
                       business=Decimal("-5000"), ledger=Decimal("2000"))
    assert any("成本为负" in f for f in flags)


# ——— 成本可用度：排序的第一依据 ———

def test_cost_confidence_separates_no_data_from_real_data():
    assert cost_confidence(Decimal(0), Decimal(0)) == "无成本数据"
    assert cost_confidence(Decimal("100"), Decimal(0)) == "仅单口径有数"
    assert cost_confidence(Decimal(0), Decimal("100")) == "仅单口径有数"
    assert cost_confidence(Decimal("100"), Decimal("80")) == "两口径均有数"


def test_no_cost_data_never_outranks_real_cost_data():
    """这条就是初版那个错的回归锁：可用度必须排在毛利率前面。

    没有它，「成本为 0 所以率 100%」会永远霸占榜首——把最不可信的行放在最显眼的位置。
    """
    from build_project_margin import 可用度序
    assert 可用度序["两口径均有数"] < 可用度序["仅单口径有数"] < 可用度序["无成本数据"]


# ——— 阶段归并 ———

def test_status_wordings_collapse_into_stable_stages():
    """原始表里写法不统一（「已完工」「完工」「部分施工」），同一件事不能散成几档。"""
    assert stage_of("已完工", True) == "已完工"
    assert stage_of("完工", False) == "已完工"
    assert stage_of("施工中", False) == "施工中"
    assert stage_of("部分施工", False) == "部分施工"
    assert stage_of("待入场", False) == "待入场"
    assert stage_of("", False) == "状态不明"


def test_partial_construction_is_not_swallowed_by_the_completion_matcher():
    """『部分施工』含「施工」，不能被误判成「施工中」而丢掉「只做了一部分」这个信息。"""
    assert stage_of("部分施工", False) == "部分施工"
