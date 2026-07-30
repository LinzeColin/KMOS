# -*- coding: utf-8 -*-
"""层级上卷的回归测试。

上卷错了不会报错，只会让表里的数悄悄变大或变小——所以这里逐条钉死不变量：
总额守恒、每一级等于自身加下级、中间行不许空着。
"""
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "project_cost"))
import rollup as R  # noqa: E402

# 仅使用合成金额验证层级守恒。
LEAF_SYNTHETIC = {
    "（四）现场管理费": Decimal("36000.00"),
    "（一）原材料": Decimal("7400.00"),
    "1.管理人员工资": Decimal("6300.00"),
    "5.1加油费及保养": Decimal("5800.00"),
    "2.1车票": Decimal("3600.00"),
    "5.2过路、停车费": Decimal("2500.00"),
    "3.物流运输费": Decimal("2300.00"),
}


def test_total_is_conserved():
    _, sec2 = R.rollup("A", LEAF_SYNTHETIC)
    assert sec2 == sum(LEAF_SYNTHETIC.values()), "上卷改变了总额——不是漏钱就是重复计"


def test_intermediate_rows_get_filled():
    """只按二级归并的话，这两行会空着，而它们的下级有数。"""
    val, _ = R.rollup("A", LEAF_SYNTHETIC)
    assert val["2.差旅费"] == Decimal("3600.00")
    assert val["5.工程车辆使用费"] == Decimal("5800.00") + Decimal("2500.00")


def test_level2_equals_own_plus_children():
    val, _ = R.rollup("A", LEAF_SYNTHETIC)
    expect = (LEAF_SYNTHETIC["（四）现场管理费"] + LEAF_SYNTHETIC["1.管理人员工资"]
              + val["2.差旅费"] + val["5.工程车辆使用费"])
    assert val["（四）现场管理费"] == expect


def test_invariants_pass_on_real_data():
    assert R.check_invariants("A", LEAF_SYNTHETIC) == []


def test_invariants_catch_a_broken_rollup(monkeypatch):
    """把父级找错（一律挂到二级）时，中间行会空——不变量必须发现。"""
    monkeypatch.setattr(R, "parent_of", lambda node, label: node.get(label, (None, ()))[0])
    val, sec2 = R.rollup("A", LEAF_SYNTHETIC)
    assert sec2 == sum(LEAF_SYNTHETIC.values()), "总额仍守恒，所以只靠总额查不出这个 bug"
    assert "2.差旅费" not in val, "样本失效：这个 bug 本应让中间行空着"


def test_template_b_hierarchy_is_parsed():
    node = R.hierarchy("B")
    assert node["1.自有人员工资"][0] == "（四）现场管理费"
    assert node["（七）税金"] == (None, ())


def test_deeper_path_rolls_through_every_level():
    """三层：5.3 → 5. → （四）。"""
    val, sec2 = R.rollup("A", {"5.3维修费": Decimal("100.00")})
    assert val["5.工程车辆使用费"] == Decimal("100.00")
    assert val["（四）现场管理费"] == Decimal("100.00")
    assert sec2 == Decimal("100.00")


# —— 模板 B 的无行号明细行（真 bug 回归） ——
# 合成回归曾在二级之和与叶子之和之间发现原材料差异：
# 模板 B 的「采购材料/外协人员工资/外协人员生活费/临时用工费用」都没有行号，
# 早先按「无行号即无父」处理，它们永远卷不上去，金额静默蒸发。
LEAF_B = {
    "（四）现场管理费": Decimal("2600.00"),
    "9.其他费用": Decimal("1600.00"),
    "2.差旅费": Decimal("1000.00"),
    "1.自有人员工资": Decimal("500.00"),
    "采购材料": Decimal("480.00"),          # 无行号，此前会丢
}


def test_unnumbered_detail_row_rolls_into_its_level2():
    val, _ = R.rollup("B", LEAF_B)
    assert val["（一）原材料"] == Decimal("480.00"), "无行号明细行必须卷进它的二级"


def test_template_b_total_is_conserved_with_unnumbered_rows():
    _, sec2 = R.rollup("B", LEAF_B)
    assert sec2 == sum(LEAF_B.values())
    assert R.check_invariants("B", LEAF_B) == []


def test_every_unnumbered_detail_row_in_both_templates_has_a_parent():
    """把两套模板里所有无行号的明细行都过一遍，防止将来加行又漏。"""
    for tpl in ("A", "B"):
        node = R.hierarchy(tpl)
        for label, (l2, path) in node.items():
            if l2 and not path:
                assert R.parent_of(node, label) == l2, f"模板 {tpl} 的『{label}』没有父级，会丢钱"
