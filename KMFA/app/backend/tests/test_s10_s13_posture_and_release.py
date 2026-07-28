# -*- coding: utf-8 -*-
"""S10–S13 —— 安全态势、质量、可观测性、成本与发布。

覆盖 T-S10-01..04、T-S11-01..04、T-S12-01..04、T-S13-01..04 的 pass_gate。

## 这一批测的是**判据本身**，不是功能

「SLO 达标」「告警可定位」「回滚通过」这类说法在复盘时毫无约束力——
谁都可以说自己达标了。所以每条 pass_gate 都落成一个返回布尔或抛错的函数，
而这里测的是：**该抛的时候真的抛**。

一个只会在顺利路径上返回 True 的判据函数，等于没有判据。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import reliability_ops as OPS
from app import security_posture as SEC


# ═════════ T-S10-01 高风险威胁四件齐全 ═════════

def _threat(**overrides):
    base = {"name": "跨 workspace 读取", "risk": "high",
            "prevent": "查询自带 workspace 谓词", "detect": "结果集自检 + canary",
            "respond": "撤销会话并清缓存", "oracle": "15 路由 × 3 身份矩阵"}
    base.update(overrides)
    return base


def test_a_high_risk_threat_without_an_oracle_is_not_treated():
    """**没有 Oracle 的威胁条目是一段声明**，
    而声明在事故复盘里唯一的作用是证明我们当初想到过。"""
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.validate_threat(_threat(oracle=""))
    assert caught.value.code == "threat_controls_incomplete"
    assert "oracle" in caught.value.payload["missing"]


@pytest.mark.parametrize("missing", ["prevent", "detect", "respond", "oracle"])
def test_every_one_of_the_four_controls_is_required(missing):
    with pytest.raises(SEC.SecurityError):
        SEC.validate_threat(_threat(**{missing: "  "}))


def test_a_low_risk_threat_does_not_need_the_full_set():
    SEC.validate_threat({"name": "低危", "risk": "low"})


def test_coverage_is_reported_as_gaps_not_a_percentage():
    """百分比会让「92% 覆盖」听起来不错——而缺的那 8% 才是重点。"""
    report = SEC.threat_coverage([_threat(), _threat(name="缺 oracle", oracle="")])
    assert report["complete"] is False
    assert report["high_risk"] == 2 and report["high_risk_covered"] == 1
    assert SEC.threat_coverage([_threat()])["complete"] is True


# ═════════ T-S10-02 Critical/High 阻断 = 0 ═════════

def test_an_unaccepted_high_finding_blocks():
    blockers = SEC.blocking_findings([
        {"id": "CVE-1", "severity": "critical"},
        {"id": "CVE-2", "severity": "medium"},
        {"id": "CVE-3", "severity": "high", "accepted_until": "2026-09-01"},
    ])
    assert [b["id"] for b in blockers] == ["CVE-1"]


def test_an_exception_without_an_expiry_still_blocks():
    """**永久接受的高危**和「没发现」在后果上没有区别，
    只是多了一份让人安心的记录。"""
    assert SEC.blocking_findings([{"id": "x", "severity": "high",
                                   "accepted_until": "  "}])


def test_overdue_patches_are_computed_from_an_injected_clock():
    """读时钟的函数无法测「明天会不会逾期」。"""
    items = [
        {"id": "a", "severity": "critical", "discovered_ordinal": 100},
        {"id": "b", "severity": "low", "discovered_ordinal": 100},
        {"id": "c", "severity": "critical", "discovered_ordinal": 100, "fixed": True},
    ]
    assert [i["id"] for i in SEC.overdue_patches(items, today_ordinal=108)] == ["a"]
    assert SEC.overdue_patches(items, today_ordinal=105) == []


def test_a_finding_without_a_discovery_date_cannot_be_judged():
    with pytest.raises(SEC.SecurityError):
        SEC.overdue_patches([{"id": "x", "severity": "high"}], today_ordinal=1)


def test_sbom_without_versions_cannot_answer_the_only_question_it_exists_for():
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.validate_sbom({"components": [{"name": "fastapi", "source": "pypi"}]})
    assert caught.value.code == "sbom_incomplete"
    with pytest.raises(SEC.SecurityError):
        SEC.validate_sbom({"components": []})
    assert SEC.validate_sbom({"components": [
        {"name": "fastapi", "version": "0.140.7", "source": "pypi"}]})["complete"]


def test_a_digest_is_not_a_substitute_for_a_signature():
    """摘要证明「没被改过」，签名证明「是我们发的」——
    攻击者能同时替换制品和它的摘要，但替换不了签名。"""
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.artifact_signature_required({"sha256": "a" * 64})
    assert caught.value.code == "artifact_signature_missing"
    SEC.artifact_signature_required({"sha256": "a" * 64, "signature": "sig"})


# ═════════ T-S10-03 canary 命中 = 0 ═════════

def test_a_canary_anywhere_public_is_a_stop_condition():
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.assert_no_leak({"sitemap": "…CANARY-9f2b…"}, ["CANARY-9f2b"])
    assert caught.value.code == "canary_leaked"
    SEC.assert_no_leak({"page": "干净内容"}, ["CANARY-9f2b"])


def test_scanning_fewer_surfaces_than_required_is_itself_a_failure():
    """**少扫一个面的表现和一切正常完全一样。**"""
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.assert_surfaces_covered({"page": "", "api": ""})
    assert "cache" in caught.value.payload["missing"]
    SEC.assert_surfaces_covered({name: "" for name in SEC.REQUIRED_LEAK_SURFACES})


# ═════════ T-S10-04 AI scope 与代码一致 ═════════

def test_model_capability_is_detected_from_code_not_from_memory():
    """问人得到的是记忆，扫代码得到的是事实。"""
    assert SEC.detect_model_capability(
        {"a.py": "import json"})["has_model_capability"] is False
    found = SEC.detect_model_capability({"b.py": "client.messages.create(...)"})
    assert found["has_model_capability"] is True and found["evidence"]


def test_a_scope_declaration_that_disagrees_with_the_code_stops_everything():
    """不一致本身就说明有人改了东西而没改声明。"""
    with pytest.raises(SEC.SecurityError) as caught:
        SEC.ai_scope_decision({"has_model_capability": True, "evidence": ["x"]},
                              {"in_scope": False})
    assert caught.value.code == "ai_scope_mismatch"


def test_not_applicable_is_recorded_differently_from_skipped():
    """两者的区别必须留痕，否则后来的人看到「没有 eval」会以为是漏了。"""
    decision = SEC.ai_scope_decision({"has_model_capability": False, "evidence": []},
                                     {"in_scope": False})
    assert decision["dual_pipeline"] == "not_applicable"
    assert "不适用" in decision["理由"] and "不是被跳过" in decision["理由"]


def test_this_repository_has_no_model_capability_in_the_backend():
    """对本仓后端源码真扫一遍——AI scope 的结论必须来自实测。"""
    backend = Path(SEC.__file__).parent
    sources = {p.name: p.read_text(encoding="utf-8")
               for p in backend.glob("*.py")}
    detection = SEC.detect_model_capability(sources)
    decision = SEC.ai_scope_decision(detection, {"in_scope": False})
    assert decision["in_scope"] is False, detection["evidence"]


def test_the_detector_does_not_find_itself():
    """**扫描器扫到自己**是这个检测第一版真踩到的坑：它的正则字面量里
    就写着 anthropic / torch / openai，于是任何仓库扫出来都「有模型能力」。

    一个恒为真的检测器等于没有检测器。这条用例把排除规则钉住。
    """
    own = Path(SEC.__file__).read_text(encoding="utf-8")
    assert "anthropic" in own.lower(), "前提变了：本文件已不含那些字面量"
    assert SEC.detect_model_capability(
        {"security_posture.py": own})["has_model_capability"] is False
    # 但换个文件名装同样的内容，就该被检出——排除的是自身，不是关键词
    assert SEC.detect_model_capability(
        {"some_other.py": "client = anthropic.Anthropic()"})["has_model_capability"]


# ═════════ T-S11 质量 ═════════

def test_path_matrix_demands_all_five_classes():
    """没覆盖的那部分不是随机的，而是最难写测试的那部分。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.assert_path_matrix_complete({"上传": ["golden", "black"]})
    assert "abuse" in str(caught.value.payload["gaps"])
    OPS.assert_path_matrix_complete({"上传": list(OPS.PATH_CLASSES)})


def test_an_empty_matrix_is_not_100_percent():
    """空矩阵的覆盖率恒为 100%，那是自欺。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.assert_path_matrix_complete({})
    assert caught.value.code == "path_matrix_empty"


def test_mutation_score_denominator_is_injected_not_detected():
    assert OPS.mutation_score(80, 100) == 0.8
    with pytest.raises(OPS.OpsError):
        OPS.mutation_score(0, 0)
    with pytest.raises(OPS.OpsError):
        OPS.assert_mutation_gate(60, 100, threshold=0.8)
    OPS.assert_mutation_gate(85, 100, threshold=0.8)


def test_the_knee_is_a_number_because_capacity_decisions_consume_it():
    samples = [{"concurrency": 1, "p95_ms": 50}, {"concurrency": 10, "p95_ms": 70},
               {"concurrency": 50, "p95_ms": 120}, {"concurrency": 100, "p95_ms": 400}]
    knee = OPS.load_curve_knee(samples)
    # 基线 50ms，两倍即 100ms。并发 50 时 P95=120ms 已越过 —— 拐点在 50，
    # 不在 100。（第一版把期望写成 100，是我按「最后一个样本」想当然了。）
    assert knee["knee_concurrency"] == 50
    assert knee["safe_concurrency"] == 25


def test_no_knee_within_range_is_not_the_same_as_no_knee():
    flat = [{"concurrency": 1, "p95_ms": 50}, {"concurrency": 10, "p95_ms": 60}]
    result = OPS.load_curve_knee(flat)
    assert result["knee_concurrency"] is None
    assert result["safe_concurrency"] == 10, "未见拐点时不外推，取实测最高点"
    assert "不外推" in result["注"]
    with pytest.raises(OPS.OpsError):
        OPS.load_curve_knee([{"concurrency": 1, "p95_ms": 50}])


def test_slo_is_judged_item_by_item():
    """「整体还行」是最容易被用来掩盖单项崩溃的说法。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.assert_slo({"p95_ms": 100, "error_rate": 0.05},
                       {"p95_ms": 200, "error_rate": 0.01})
    assert "error_rate" in str(caught.value.payload["breaches"])
    with pytest.raises(OPS.OpsError):
        OPS.assert_slo({"p95_ms": 100}, {"p95_ms": 200, "error_rate": 0.01})
    OPS.assert_slo({"p95_ms": 100, "error_rate": 0.001},
                   {"p95_ms": 200, "error_rate": 0.01})


def test_chaos_needs_recovery_evidence_not_just_injection():
    """「注入了故障」和「验证了恢复」是两件事，
    只做前者等于确认系统会坏。"""
    injected_only = [{"mode": m} for m in OPS.CRITICAL_FAILURE_MODES]
    assert OPS.chaos_coverage(injected_only)["complete"] is False
    with_evidence = [{"mode": m, "recovery_evidence": "log"}
                     for m in OPS.CRITICAL_FAILURE_MODES]
    assert OPS.chaos_coverage(with_evidence)["complete"] is True


def test_an_invariant_violation_during_chaos_is_a_hard_failure():
    with pytest.raises(OPS.OpsError) as caught:
        OPS.chaos_coverage([{"mode": "disk_full", "recovery_evidence": "log",
                             "invariant_violations": ["余额对不平"]}])
    assert caught.value.code == "chaos_invariant_violated"


def test_rpo_rto_need_measurements_not_targets():
    """目标值人人都有，实测值才是证据。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.assert_rpo_rto({"rto_seconds": 100}, rpo_seconds=60, rto_seconds=300)
    assert caught.value.code == "recovery_objective_unmeasured"
    with pytest.raises(OPS.OpsError):
        OPS.assert_rpo_rto({"rpo_seconds": 600, "rto_seconds": 100},
                           rpo_seconds=60, rto_seconds=300)
    OPS.assert_rpo_rto({"rpo_seconds": 30, "rto_seconds": 100},
                       rpo_seconds=60, rto_seconds=300)


# ═════════ T-S12 可观测性、告警、成本 ═════════

def test_telemetry_never_carries_sensitive_values():
    hits = OPS.telemetry_sensitive_hits([
        {"name": "ok", "route": "dashboard"},
        {"name": "bad", "auth": "Bearer abc.def.ghi"},
        {"name": "worse", "user": "13800138000"},
    ])
    assert len(hits) == 2


def test_a_span_without_a_trace_id_is_a_broken_link():
    """一条断了的链路在排查时的价值是零，
    而它在仪表盘上看起来是正常的。"""
    report = OPS.journey_correlation([
        {"name": "a", "trace_id": "t1"}, {"name": "b"}])
    assert report["complete"] is False and report["orphans"] == ["b"]
    assert OPS.journey_correlation([{"name": "a", "trace_id": "t"}])["rate"] == 1.0


@pytest.mark.parametrize("action", sorted(OPS.NEVER_AUTOMATED))
def test_destructive_actions_are_never_automated(action):
    """**宁可不愈，不可愈错。** 这三类是 T-S12-02 的 stop_condition，
    硬编码在代码里而不是配置——配置会被改。"""
    plan = OPS.plan_remediation(action, idempotent=True)
    assert plan["mode"] == "ticket_only"


def test_an_unknown_action_defaults_to_ticket_only():
    """白名单默认拒绝——未知动作自动执行一次，就够了。"""
    assert OPS.plan_remediation("某个新动作",
                                idempotent=True)["mode"] == "ticket_only"


def test_a_non_idempotent_action_is_never_retried_automatically():
    """重试一个不幂等的动作，等于把一次故障放大成 N 次。"""
    assert OPS.plan_remediation("retry", idempotent=False)["mode"] == "ticket_only"
    assert OPS.plan_remediation("retry", idempotent=True)["mode"] == "automatic"


def test_an_alert_without_a_runbook_is_just_an_interruption():
    with pytest.raises(OPS.OpsError) as caught:
        OPS.alert_is_actionable({"name": "磁盘满", "symptom": "写入失败"})
    assert "runbook" in caught.value.payload["missing"]
    OPS.alert_is_actionable({"name": "磁盘满", "symptom": "写入失败",
                             "runbook": "runbooks/disk.md", "owner": "ops",
                             "diagnostic_bundle": "bundle.sh"})


def test_a_budget_without_an_owner_means_nobody_handles_the_overrun():
    gaps = OPS.budget_gaps([
        {"name": "对象存储", "budget": 100, "alert_threshold": 80},
        {"name": "出网", "budget": 50, "owner": "ops", "alert_threshold": 40},
    ])
    assert gaps == ["对象存储：缺 owner"]


def test_unit_cost_is_integer_and_refuses_zero_units():
    assert OPS.unit_cost(10000, 3) == 3333
    with pytest.raises(OPS.OpsError):
        OPS.unit_cost(100, 0)


def test_a_service_trigger_must_be_a_number():
    """「感觉需要了」不是触发条件——它无法被复核，也无法被反驳。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.service_trigger_met(10, {"service": "队列"})
    assert caught.value.code == "service_trigger_unquantified"
    assert OPS.service_trigger_met(120, {"service": "队列", "threshold": 100}) is True
    assert OPS.service_trigger_met(80, {"service": "队列", "threshold": 100}) is False


# ═════════ T-S13 发布 ═════════

def test_a_high_risk_flag_must_default_off_with_owner_expiry_and_kill_switch():
    """永久存在的临时开关最终没人知道它是干什么的——
    于是没人敢关，也没人敢开。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.validate_flag({"name": "公开索引", "default": True, "owner": "o",
                           "expiry": "2026-12-31", "kill_switch": True})
    assert any("默认必须是关" in p for p in caught.value.payload["problems"])

    for field in ("owner", "expiry"):
        payload = {"name": "f", "default": False, "owner": "o",
                   "expiry": "2026-12-31", "kill_switch": True}
        payload[field] = ""
        with pytest.raises(OPS.OpsError):
            OPS.validate_flag(payload)

    with pytest.raises(OPS.OpsError):
        OPS.validate_flag({"name": "f", "default": False, "owner": "o",
                           "expiry": "2026-12-31", "kill_switch": False})

    assert OPS.validate_flag({"name": "f", "default": False, "owner": "o",
                              "expiry": "2026-12-31",
                              "kill_switch": True})["kill_switch"] is True


def test_threshold_breach_rolls_back_without_asking_a_human():
    """「先通知人，人来决定」的问题是：人可能在睡觉，
    而错误版本在这段时间里继续产生坏数据。"""
    decision = OPS.promotion_decision({"error_rate": 0.05, "p95_ms": 100},
                                      {"error_rate": 0.01, "p95_ms": 200})
    assert decision["decision"] == "rollback" and decision["automatic"] is True


def test_missing_metrics_are_treated_as_a_breach():
    """「测不到」和「很糟」在风险上等价。"""
    decision = OPS.promotion_decision({"p95_ms": 100},
                                      {"error_rate": 0.01, "p95_ms": 200})
    assert decision["decision"] == "rollback"
    assert any("没有实测值" in b for b in decision["breaches"])


def test_a_clean_run_promotes():
    assert OPS.promotion_decision({"error_rate": 0.001, "p95_ms": 100},
                                  {"error_rate": 0.01, "p95_ms": 200}
                                  )["decision"] == "promote"


def test_rollback_itself_must_be_verified():
    """回滚到一个也坏了的版本，比不回滚更难查。"""
    with pytest.raises(OPS.OpsError) as caught:
        OPS.assert_rollback_verified({"rolled_back": True,
                                      "oracles": {"下载": True, "对账": False}})
    assert caught.value.payload["failed"] == ["对账"]
    with pytest.raises(OPS.OpsError):
        OPS.assert_rollback_verified({"oracles": {}})
    OPS.assert_rollback_verified({"rolled_back": True, "oracles": {"下载": True}})


def test_ga_requires_p0_at_one_hundred_percent():
    """不存在「基本都过了」。"""
    held = OPS.ga_decision({"AC-DL-001": True, "AC-FIN-001": False}, [], {})
    assert held["decision"] == "hold" and held["p0_failed"] == ["AC-FIN-001"]


def test_ga_is_held_by_an_unaccepted_high_risk():
    held = OPS.ga_decision({"AC-DL-001": True},
                           [{"name": "出网费用未封顶", "severity": "high"}], {})
    assert held["decision"] == "hold" and "出网费用未封顶" in held["unaccepted"]
    passed = OPS.ga_decision({"AC-DL-001": True},
                             [{"name": "x", "severity": "high",
                               "accepted_by": "owner"}],
                             {"成本": True, "可靠性": True, "安全": True})
    assert passed["decision"] == "ga"


def test_ga_is_held_by_a_failed_gate():
    held = OPS.ga_decision({"AC-DL-001": True}, [],
                           {"成本": True, "可靠性": False, "安全": True})
    assert held["decision"] == "hold" and held["gate_failed"] == ["可靠性"]
