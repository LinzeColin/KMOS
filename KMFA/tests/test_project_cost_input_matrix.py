# -*- coding: utf-8 -*-
"""项目成本输入矩阵的回归测试。

这份矩阵是给 Owner 看「还缺什么、要传什么」的，所以最该防的不是崩溃，
而是**悄悄变成一张说『都齐了』的表**——那会让人以为可以出正式财务结论。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "project_cost"))
import input_matrix  # noqa: E402


def _data():
    return input_matrix.load(ROOT)


def test_slots_match_skill_declared_inputs():
    """槽位必须与技能声明的固定输入一一对应，不能自己加减。"""
    manifest = (ROOT / "skills" / "项目成本表" / "config" / "input_manifest.template.yml").read_text(
        encoding="utf-8")
    declared = [ln.strip().rstrip(":") for ln in manifest.splitlines()
                if ln.startswith("  ") and not ln.startswith("   ") and ln.rstrip().endswith(":")]
    declared = [d for d in declared if d and not d.startswith("#")]
    got = [s["slot"] for s in _data()["slots"]]
    assert set(got) == set(declared), f"矩阵槽位与技能声明不一致：矩阵={got} 技能={declared}"


def test_gate_rejects_matrix_that_claims_everything_is_ready():
    """把一个缺失槽位改成 ready 但不给上传指引——门禁必须拦住。"""
    data = _data()
    victim = next(s for s in data["slots"] if s["status"] != "ready")
    victim["ask"] = None
    victim["status"] = "partial"
    errs = input_matrix.check(data)
    assert any("ask 为空" in e for e in errs), f"门禁没拦住无指引的缺失槽位：{errs}"


def test_gate_rejects_slot_without_blocked_rows():
    data = _data()
    data["slots"][0]["blocks_rows"] = []
    assert any("blocks_rows" in e for e in input_matrix.check(data))


def test_live_matrix_passes_gate():
    assert input_matrix.check(_data()) == []


def test_reference_reports_never_feed_calculation():
    """8 份历史报表是校验基准，参与计算就等于自己抄自己的答案。"""
    slot = next(s for s in _data()["slots"] if s["slot"] == "reference_reports")
    assert "prohibited_in_calculate" in slot["gap"]
    manifest = (ROOT / "skills" / "项目成本表" / "config" / "input_manifest.template.yml").read_text(
        encoding="utf-8")
    assert "prohibited_in_calculate: true" in manifest


def test_public_safe_no_amounts_or_client_names():
    """本文件在公开仓：不得混入金额或客户名。"""
    raw = (ROOT / "machine" / "facts" / "project_cost_input_matrix.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert "public_safe" in data
    import re
    # 千分位金额（如 1,234.56）或长数字串都不该出现在业务字段里
    for s in data["slots"]:
        blob = json.dumps(s, ensure_ascii=False)
        assert not re.search(r"\d{1,3}(,\d{3})+(\.\d+)?", blob), f"槽位混入金额：{s['slot']}"
