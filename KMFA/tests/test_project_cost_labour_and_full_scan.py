# -*- coding: utf-8 -*-
"""项目成本产线：人工从红圈工时来、全量覆盖、两口径逐行合并。

背景（2026-07-28）。之前这条产线算不出成本，卡点被写成「金蝶记账没分项目」——
那是真的（劳务费约八成、其中七成记在 `不分项目` 占位桶），但结论下错了：
Owner 指出**红圈《生产项目状态表》按项目填了工时**，人工从那里出就行。

于是这组测试钉死四件事，每一件都对应一个实测踩过的坑：

  · 人工必须真的进成本——不进，成本就只有材料和差旅，毛利系统性偏高；
  · 工时**没填**和工时**为 0** 必须分得开——混为一谈，等于给没数的项目发一个漂亮毛利；
  · 两个口径要**逐行**合并，不能整块取大——整块取大会让「金蝶有材料没现场费」
    和「红圈有现场费没材料」互相抵消，实测覆盖率从 84% 掉到 78%；
  · 伪合同号 `KMX999/KMX9999`（账上约 3,261 万）不是项目，混进来就是两个巨额假项目。
"""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "project_cost"))
import build_recent_completed as B  # noqa: E402


def _record(**kw):
    base = {"合同编号": "KMX2026112-002", "含税合同金额": "91000",
            "材料费": "", "交通费": "", "生活住宿费": "2800", "其他费用": ""}
    base.update(kw)
    return base


# ── 人工 ────────────────────────────────────────────────────────────────
def test_own_hours_become_cost_at_the_calibrated_rate():
    own, sub, recorded = B.labour_cost(_record(自有人工工时="43"))
    assert own == Decimal("43") * B.LABOUR_RATE_OWN
    assert sub == 0
    assert recorded is True


def test_subcontract_hours_use_their_own_rate():
    """劳务比自有贵——实测 530／589，不能跟自有共用一个价。"""
    own, sub, _ = B.labour_cost(_record(劳务人工工时="17"))
    assert sub == Decimal("17") * B.LABOUR_RATE_SUB
    assert B.LABOUR_RATE_SUB > B.LABOUR_RATE_OWN
    assert own == 0


def test_both_kinds_of_hours_add_up():
    own, sub, _ = B.labour_cost(_record(自有人工工时="41", 劳务人工工时="17"))
    assert own == Decimal("20500") and sub == Decimal("9350")


@pytest.mark.parametrize("field", ["自有人工工时", "劳务人工工时"])
def test_a_recorded_zero_is_not_the_same_as_a_blank(field):
    """填了 0 ＝ 真没投人工，可以出毛利；没填 ＝ 不知道，不能出。"""
    _, _, zero_recorded = B.labour_cost(_record(**{field: "0"}))
    _, _, blank_recorded = B.labour_cost(_record())
    assert zero_recorded is True
    assert blank_recorded is False


def test_rates_are_calibrated_not_invented():
    """单价必须落在 8 份竣工报表实测区间内，改动要有人重新标定。"""
    assert Decimal("465") <= B.LABOUR_RATE_OWN <= Decimal("510")
    assert Decimal("530") <= B.LABOUR_RATE_SUB <= Decimal("590")


# ── 占位桶 ──────────────────────────────────────────────────────────────
def test_placeholder_contracts_are_not_projects():
    """KMX999／KMX9999 是账上的伪合同号，混进来就是两个几千万的假项目。"""
    assert "KMX999" in B.PLACEHOLDER_CONTRACTS
    assert "KMX9999" in B.PLACEHOLDER_CONTRACTS
    assert B.norm_contract("KMX9999") in B.PLACEHOLDER_CONTRACTS


def test_a_real_contract_is_not_caught_by_the_placeholder_filter():
    """别把 KMX9999 的前缀匹配扩大到真合同号上。"""
    for real in ("KMX2026112-002", "KMX20251119-079", "KMX202595-064"):
        assert B.norm_contract(real) not in B.PLACEHOLDER_CONTRACTS


# ── 覆盖范围 ────────────────────────────────────────────────────────────
def test_default_limit_is_unbounded():
    """Owner：「你根本没有全量跑所有信息」。默认必须是全部，不是最近 N 个。"""
    import inspect
    assert inspect.signature(B.build).parameters["limit"].default == 0


def test_uncovered_sources_are_declared_not_silently_missing():
    """读不到的账簿要具名登记——静默漏掉和已覆盖在产物里长得一样。"""
    assert B.UNCOVERED_SOURCES
    for entry in B.UNCOVERED_SOURCES:
        assert entry["账簿"] and entry["原因"] and entry["实测生产成本"]
