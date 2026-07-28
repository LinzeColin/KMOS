# -*- coding: utf-8 -*-
"""S09 —— 财务核心：血缘、金额不变量、幂等重跑、经营分析。

| 任务 | 验收 | pass_gate |
|---|---|---|
| T-S09-01 | AC-FIN-002 | 关键结果 100% 可追溯，**来源链断点=0** |
| T-S09-02 | AC-FIN-001 | 所有精确测试通过，**权威浮点字段=0** |
| T-S09-03 | AC-FIN-003 | **静默覆盖=0，重复结果=0**，冲突均可解释 |
| T-S09-04 | AC-FIN-004 | Golden Path 100%，Black Path 数据不丢，报告 hash/数值/来源一致 |

## 金额这一组用「定点值」测，不用随机值

`0.1 + 0.2` 这类问题只在特定值上出现，随机测试可能几千次都撞不到。
所以用已知会出问题的值定点打：`2.675`（浮点表示低于真值）、
`0.1/0.2/0.3`、以及会暴露分摊余数的 `100 / 3`。
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app import finance_core as FC


# ═════════ T-S09-02 权威浮点字段 = 0 ═════════

@pytest.mark.parametrize("bad", [0.1, 2.675, 1e6, float("nan"), float("inf")])
def test_float_amounts_are_refused_not_converted(bad):
    """**拒绝而不是转换。** 转换会让 2.675 变成 267（不是 268），
    而调用方不会知道自己刚刚丢了一分钱。"""
    with pytest.raises(FC.FinanceError) as caught:
        FC.to_cents(bad)
    assert caught.value.code == "amount_is_float"


def test_decimal_and_string_amounts_are_exact():
    """定点值：这几个是浮点会出错的经典位置。"""
    assert FC.to_cents("0.1") == 10
    assert FC.to_cents("0.2") == 20
    assert FC.to_cents("0.1") + FC.to_cents("0.2") == FC.to_cents("0.3")
    assert FC.to_cents(Decimal("2.675")) == 268, "银行家舍入应进到 268，浮点会给 267"
    assert FC.to_cents("40,960,322.77") == 4096032277
    assert FC.to_cents(-1) == -1


def test_bool_is_not_an_amount():
    with pytest.raises(FC.FinanceError):
        FC.to_cents(True)


def test_display_conversion_happens_exactly_once():
    assert FC.format_cents(4096032277) == "40,960,322.77"
    assert FC.format_cents(-1) == "-0.01"
    assert FC.format_cents(0) == "0.00"
    with pytest.raises(FC.FinanceError):
        FC.format_cents(1.5)


def test_allocation_always_sums_to_the_total():
    """朴素做法是各自 round 然后相加——那样几乎必然差几分，
    而「合计对不上明细」是财务报表里最招人质疑的一种错误。"""
    for total, weights in [
        (10000, [1, 1, 1]),          # 100.00 分三份，除不尽
        (100, [1, 1, 1]),
        (1, [1, 1, 1]),              # 1 分分三份
        (-10000, [3, 1]),            # 负数
        (4096032277, [7, 11, 13, 17]),
        (0, [1, 2, 3]),
    ]:
        parts = FC.allocate(total, weights)
        assert sum(parts) == total, f"{total} 按 {weights} 分摊后合计对不上"
        assert len(parts) == len(weights)


def test_allocation_is_deterministic():
    """同分时按索引补余数——不确定的分摊会让两次报表出现不同的明细。"""
    assert FC.allocate(100, [1, 1, 1]) == FC.allocate(100, [1, 1, 1])
    assert FC.allocate(100, [1, 1, 1]) == [34, 33, 33]


def test_allocation_rejects_degenerate_input():
    for total, weights in [(100, []), (100, [0, 0]), (100, [1, -1])]:
        with pytest.raises(FC.FinanceError):
            FC.allocate(total, weights)


def test_zero_diff_has_no_tolerance():
    """设容差（「差 1 分算平」）等于把对账变成一句安慰：
    真正的错误常常就是一分钱起步，而容差恰好把它盖住。"""
    assert FC.zero_diff(100, 100)["balanced"] is True
    result = FC.zero_diff(100, 99)
    assert result["balanced"] is False and result["delta_cents"] == 1
    with pytest.raises(FC.FinanceError):
        FC.zero_diff(100.0, 100)


def test_the_repository_wide_float_gate_still_exists():
    """守卫：本仓有一条 AST 级静态检查禁止业务金额用 float。
    它被删掉的话，上面这些运行时检查就成了唯一防线——而它们只覆盖走到的路径。"""
    from pathlib import Path
    gate = Path(FC.__file__).resolve().parents[4] / "KMFA" / "tools" / "check_no_float_money.py"
    assert gate.exists(), "check_no_float_money.py 不见了"


# ═════════ T-S09-01 来源链断点 = 0 ═════════

def test_a_number_without_a_source_is_not_traceable():
    with pytest.raises(FC.FinanceError) as caught:
        FC.assert_traceable("revenue_cents", {"value_cents": 100})
    assert caught.value.code == "lineage_missing"


def test_an_estimate_may_not_masquerade_as_an_authoritative_metric():
    """**T-S09-01 的 stop_condition。** 推断值做决策的问题不是「可能不准」，
    是「没人知道它不准」。"""
    record = {"provenance": FC.provenance("estimated", source_ref="模型推断",
                                          field="revenue")}
    with pytest.raises(FC.FinanceError) as caught:
        FC.assert_traceable("revenue_cents", record)
    assert caught.value.code == "estimated_value_in_authoritative_metric"

    # 非权威口径可以是推断值——它能显示，只是带标记
    FC.assert_traceable("headcount_estimate", record)


def test_measured_and_derived_pass():
    for kind in ("measured", "derived"):
        FC.assert_traceable("cost_cents", {
            "provenance": FC.provenance(kind, source_ref="税务申报表",
                                        field="cost", inputs=["税务申报表"])})


def test_provenance_requires_a_real_source():
    """没有来源的数字无法被追溯，而无法追溯的数字在对账时只能靠猜。"""
    with pytest.raises(FC.FinanceError):
        FC.provenance("measured", source_ref="", field="cost")
    with pytest.raises(FC.FinanceError):
        FC.provenance("guessed", source_ref="x", field="cost")
    with pytest.raises(FC.FinanceError):
        FC.provenance("measured", source_ref="x", field="Bad-Field")


def test_a_broken_link_is_worse_than_no_link_and_is_detected():
    """断了的链条比没有链条更危险：**它看起来是完整的**。"""
    known = {"税务申报表", "银行流水"}
    breaks = FC.lineage_breaks([
        {"metric": "a", "provenance": FC.provenance(
            "derived", source_ref="税务申报表", field="a", inputs=["银行流水"])},
        {"metric": "b", "provenance": FC.provenance(
            "derived", source_ref="税务申报表", field="b", inputs=["已删除的源"])},
        {"metric": "c", "provenance": FC.provenance(
            "measured", source_ref="不存在的源", field="c")},
        {"metric": "d"},
    ], known)
    assert len(breaks) == 3
    assert any("已删除的源" in b for b in breaks)
    assert any("不存在的源" in b for b in breaks)
    assert any("d：无来源" in b for b in breaks)


def test_derived_without_inputs_is_a_break():
    breaks = FC.lineage_breaks([{"metric": "x", "provenance": {
        "kind": "derived", "source_ref": "s", "field": "x", "inputs": []}}], {"s"})
    assert any("没有输入" in b for b in breaks)


# ═════════ T-S09-03 静默覆盖 = 0 / 重复结果 = 0 ═════════

def test_a_rerun_creates_a_new_version_and_never_overwrites():
    """覆盖的问题不是丢了旧值，是丢了「为什么变了」——
    对账时唯一有用的信息恰恰是两版之间的差异。"""
    existing = {"version_id": "v1", "content_sha256": "aaa"}
    plan = FC.plan_rerun(existing, {"content_sha256": "bbb"})
    assert plan["action"] == "create_new_version"
    assert plan["supersedes"] == "v1"


def test_a_byte_identical_rerun_produces_no_second_result():
    """重复结果 = 0：内容逐字节相同才算真重复。"""
    existing = {"version_id": "v1", "content_sha256": "aaa"}
    assert FC.plan_rerun(existing, {"content_sha256": "aaa"})["action"] == "noop"
    assert FC.plan_rerun(None, {"content_sha256": "aaa"})["action"] == "create"


def test_rerun_key_includes_version_so_a_second_edition_is_not_deduped():
    """同一期间的第二版数据是**新结果**，不是重复——
    把它去重掉才是真正的数据丢失。"""
    first = FC.rerun_key(source="税务", period="2026-06", version="v1")
    second = FC.rerun_key(source="税务", period="2026-06", version="v2")
    assert first != second
    assert first == FC.rerun_key(source="税务", period="2026-06", version="v1")
    with pytest.raises(FC.FinanceError):
        FC.rerun_key(source="", period="2026-06", version="v1")


def test_cross_source_conflict_carries_the_losers_too():
    """只返回赢家等于把冲突藏起来：看报表的人不知道另一个源说的是别的数，
    也就无从判断这次裁决对不对。"""
    decision = FC.decide_cross_source(
        [{"source": "金蝶", "value_cents": 100},
         {"source": "税务", "value_cents": 130}],
        priority=["税务", "银行", "金蝶"])
    assert decision["winner"]["source"] == "税务"
    assert decision["unanimous"] is False
    assert decision["disagreement"] == [
        {"source": "金蝶", "value_cents": 100, "delta_cents": -30}]
    assert "税务" in decision["reason"]


def test_agreeing_sources_are_reported_as_unanimous():
    decision = FC.decide_cross_source(
        [{"source": "金蝶", "value_cents": 100},
         {"source": "税务", "value_cents": 100}],
        priority=["税务", "金蝶"])
    assert decision["unanimous"] is True and decision["disagreement"] == []


def test_an_unranked_source_stops_the_decision():
    """没有默认裁决规则时必须停下来问，而不是随手选一个。"""
    with pytest.raises(FC.FinanceError) as caught:
        FC.decide_cross_source([{"source": "某个新系统", "value_cents": 1}],
                               priority=["税务"])
    assert caught.value.code == "source_not_in_priority"


# ═════════ T-S09-04 分析与报告 ═════════

def test_margin_is_basis_points_not_a_float():
    """浮点比率在累加与比较时会带来和金额一样的问题，而它同样会进报表。"""
    result = FC.analyse(revenue_cents=1000000, cost_cents=746300)
    assert result["gross_margin_cents"] == 253700
    assert result["gross_margin_bps"] == 2537   # 25.37%
    assert isinstance(result["gross_margin_bps"], int)


def test_margin_is_none_when_revenue_is_zero_not_zero():
    """给 0 会在图表上画出一条「毛利率 0%」的线,那是编造。"""
    assert FC.analyse(revenue_cents=0, cost_cents=500)["gross_margin_bps"] is None


def test_ratio_multiplies_before_dividing():
    """先除会在整数除法里直接归零——小额场景下毛利率会全变成 0。"""
    result = FC.analyse(revenue_cents=3, cost_cents=1)
    assert result["gross_margin_bps"] == 6666


def test_budget_variance_is_reported_with_direction():
    result = FC.analyse(revenue_cents=1000, cost_cents=1200, budget_cents=1000)
    assert result["variance_cents"] == 200 and result["over_budget"] is True
    ok = FC.analyse(revenue_cents=1000, cost_cents=800, budget_cents=1000)
    assert ok["variance_cents"] == -200 and ok["over_budget"] is False


def test_report_digest_is_stable_across_key_order():
    """否则「报告 hash 一致」这条验收无法自证。"""
    a = FC.report_digest({"revenue_cents": 1, "cost_cents": 2})
    b = FC.report_digest({"cost_cents": 2, "revenue_cents": 1})
    assert a == b
    assert a != FC.report_digest({"revenue_cents": 1, "cost_cents": 3})


def test_black_path_keeps_what_was_already_computed():
    """抛掉的代价不只是重算——用户已经填进去的东西也一起没了。"""
    result = FC.black_path_preserve({"revenue_cents": 1000}, "成本源不可读")
    assert result["status"] == "partial"
    assert result["preserved"]["revenue_cents"] == 1000
    assert result["failure"] == "成本源不可读"
    with pytest.raises(FC.FinanceError):
        FC.black_path_preserve({}, "")


def test_golden_path_end_to_end_is_exact():
    """Golden Path：从字符串金额到报告摘要，全程整数，逐项可对。"""
    revenue = FC.to_cents("1,234,567.89")
    cost = FC.to_cents("987,654.32")
    analysis = FC.analyse(revenue_cents=revenue, cost_cents=cost)
    assert analysis["gross_margin_cents"] == revenue - cost
    assert FC.format_cents(analysis["gross_margin_cents"]) == "246,913.57"
    parts = FC.allocate(analysis["gross_margin_cents"], [1, 2, 3])
    assert sum(parts) == analysis["gross_margin_cents"]
    assert FC.zero_diff(sum(parts), analysis["gross_margin_cents"])["balanced"]
