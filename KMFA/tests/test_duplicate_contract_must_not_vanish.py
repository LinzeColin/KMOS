# -*- coding: utf-8 -*-
"""同一合同号挂着不同甲方时，两个项目都必须留下来。

2026-07-28 实证：《生产项目状态表》里 `KMX202595-064` 有两行——

    日照钢铁有限公司      施工中   合同额 1,263,546
    新疆宜化化工有限公司   已完工   合同额 1,180,000

而 `read_projects` 用 `found[合同号] = record` 加「保留完工日期较晚的」收口，于是
**日照钢铁整个项目从表上消失**：32 行进、31 个出，没有任何提示，而消失的那个恰好
是合同额最大的几个之一。

静默丢弃比归并更糟——归并至少金额还在，丢弃是凭空少一个项目。

另一线程的参考回放把这条列为 **P0 项目身份冲突：不得自动归并**。所以这里的口径是：
同合同号同甲方＝重复导出，按完工日期取新；同合同号不同甲方＝身份冲突，两条都留、
都打标，交给人裁。
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "project_cost"
sys.path.insert(0, str(TOOLS))
import build_recent_completed as B  # noqa: E402


def _rows(monkeypatch, rows):
    """把一张最小的《生产项目状态表》喂进去。"""
    header = ["甲方名称", "合同号", "含税合同金额", "施工状态", "完工时间",
              "自有人工工时", "劳务人工工时", "材料费", "交通费", "生活住宿费",
              "其他费用", "结算金额", "开票金额", "项目类型", "负责人", "开工时间",
              "是否提供项目成本表"]
    table = [header] + rows

    class _Sheet:
        def iter_rows(self, min_row=1, max_row=None, values_only=True):
            stop = max_row if max_row is not None else len(table)
            return iter(table[min_row - 1:stop])

    class _Book:
        sheetnames = ["信息表"]

        def __getitem__(self, _):
            return _Sheet()

        def close(self):
            pass

    monkeypatch.setattr(B, "glob", type("G", (), {
        "glob": staticmethod(lambda *a, **k: ["/fake/生产项目状态表.xlsx"])})())
    monkeypatch.setattr(B, "open_workbook", lambda path: _Book())
    monkeypatch.setattr(B, "iter_sheet_rows", lambda sheet, values_only=True: iter(table))
    return B.read_projects("/fake", only_completed=False)


def _row(party, code, amount, status, done=""):
    return [party, code, amount, status, done, "", "", "", "", "", "", "", "", "", "", "", ""]


def test_same_contract_different_parties_both_survive(monkeypatch):
    """这就是日照钢铁消失的那个形状。"""
    found = _rows(monkeypatch, [
        _row("日照钢铁有限公司", "KMX202595-064", 1263546, "施工中"),
        _row("新疆宜化化工有限公司", "KMX202595-064", 1180000, "已完工", "2026-01-12"),
    ])
    assert len(found) == 2, "同合同号不同甲方被吃掉了一个"
    parties = {r["甲方名称"] for r in found.values()}
    assert parties == {"日照钢铁有限公司", "新疆宜化化工有限公司"}
    amounts = {r["含税合同金额"] for r in found.values()}
    assert "1263546.0" in amounts, "合同额最大的那个项目消失了"


def test_the_conflict_is_flagged_on_every_side(monkeypatch):
    """留下来但不打标等于没修——用表的人看不出这两条需要人工裁定。"""
    found = _rows(monkeypatch, [
        _row("日照钢铁有限公司", "KMX202595-064", 1263546, "施工中"),
        _row("新疆宜化化工有限公司", "KMX202595-064", 1180000, "已完工", "2026-01-12"),
    ])
    for record in found.values():
        note = record.get("身份冲突") or ""
        assert "不得自动归并" in note
        assert "日照钢铁有限公司" in note and "新疆宜化化工有限公司" in note


def test_same_contract_same_party_still_dedupes_to_the_latest(monkeypatch):
    """同甲方的重复导出仍要合并，否则一次重导就多出一堆重复项目。"""
    found = _rows(monkeypatch, [
        _row("福建鼎信实业有限公司", "KMX2026112-002", 91000, "已完工", "2026-02-01"),
        _row("福建鼎信实业有限公司", "KMX2026112-002", 91000, "已完工", "2026-02-14"),
    ])
    assert len(found) == 1
    assert next(iter(found.values()))["完工日期"] == "2026-02-14"


def test_a_clean_table_is_untouched(monkeypatch):
    """没有冲突时不该凭空多出 `身份冲突` 字段。"""
    found = _rows(monkeypatch, [
        _row("甲公司", "KMX2026112-002", 91000, "已完工", "2026-02-14"),
        _row("乙公司", "KMX2026116-003", 40000, "已完工", "2026-03-27"),
    ])
    assert len(found) == 2
    assert all("身份冲突" not in r for r in found.values())


# ── 工数冲突：两个来源都摆出来，不替换 ──────────────────────────────────
def test_labour_hour_conflicts_are_declared_from_the_reference_replay():
    """数字来自另一线程的参考回放核对（P0 人工工数冲突）。"""
    assert B.LABOUR_HOURS_CONFLICT["KMX20251119-079"] == {"报表工数": 119, "红圈工数": 214}
    assert B.LABOUR_HOURS_CONFLICT["KMX2026120-004"] == {"报表工数": 31, "红圈工数": 32}


def test_the_conflict_is_material_not_a_rounding_issue():
    """广安台泥两个口径差 47,500——不摆出来，用表的人会以为人工是确定的。"""
    conflict = B.LABOUR_HOURS_CONFLICT["KMX20251119-079"]
    gap = (conflict["红圈工数"] - conflict["报表工数"]) * B.LABOUR_RATE_OWN
    assert gap == 47500
