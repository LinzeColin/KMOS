"""Stage090 从检索捕获证据的纯内存整阶段机械复审。

复审只读取冻结任务包和 P1--P4 控制工件，确认控制形状、单一权威、白箱
人工处理、失败关闭与回退边界。它不读取真实资料或启动 Stage091，也不执行
检索、证据账本写入、撤回、恢复、模型调用、Agent、OVH 或生产运行。
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-090_从检索捕获证据.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-091_证据缺口处理.md"
)
P1_CONTRACT = BASE / "stage090_retrieval_evidence_capture_contract.json"
P2_CONTRACT = BASE / "stage090_retrieval_evidence_capture_control_slice_contract.json"
P3_CONTRACT = BASE / "stage090_retrieval_evidence_capture_scenarios_contract.json"
P4_CONTRACT = BASE / "stage090_retrieval_evidence_capture_delivery_contract.json"
P2_MODULE = BASE / "stage090_retrieval_evidence_capture_control_slice.py"
P3_MODULE = BASE / "stage090_retrieval_evidence_capture_controlled_scenarios.py"
P4_MODULE = BASE / "stage090_retrieval_evidence_capture_delivery.py"

SCHEMA_VERSION = "ids.stage090.retrieval_evidence_capture.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE090-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-090"
PASS_RESULT = "PASS_REVIEWED_RETRIEVAL_EVIDENCE_CAPTURE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_RETRIEVAL_EVIDENCE_CAPTURE_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE090-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE091-P1-GATE"
RETURN_STATE = "PASS_RETRIEVAL_EVIDENCE_CAPTURE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P4_RETURN_STATE = "PASS_RETRIEVAL_EVIDENCE_CAPTURE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage090-p2:"
DELIVERY_PREFIX = ":control:stage090-p4:"

P1_SHAPES = (
    ("future_retrieval_capture_request_fields", "retrieval_capture_request_field_count", 10),
    ("future_evidence_ledger_capture_fields", "evidence_ledger_capture_field_count", 9),
    ("future_capture_relation_fields", "capture_relation_field_count", 7),
)
P2_GROUPS = (
    ("evidence_schema_binding", 6),
    ("retrieval_capture", 10),
    ("evidence_ledger_capture", 9),
    ("capture_relation", 7),
    ("risk_score", 8),
    ("revocation", 7),
    ("poisoning_defense", 8),
    ("critical_conclusion_binding", 7),
    ("degradation", 8),
    ("future_integration", 7),
)
P3_SCENARIOS = (
    "no_internal_evidence_gap_control",
    "low_ocr_evidence_degradation_control",
    "old_version_evidence_degradation_control",
    "conflict_evidence_degradation_control",
    "revoked_evidence_report_impact_control",
    "malicious_evidence_quarantine_control",
    "low_grade_high_trust_masquerade_control",
)
P4_DELIVERY_GROUPS = (
    ("evidence_ledger_sample_control_records", 7, 14),
    ("evidence_grade_report_control_records", 7, 13),
    ("revocation_impact_control_records", 7, 13),
    ("regression_test_control_records", 7, 14),
    ("non_conclusion_evidence_type_control_records", 7, 11),
    ("degradation_instruction_control_records", 4, 10),
    ("revocation_recovery_instruction_control_records", 2, 11),
)
P4_REPORT_COUNT_KEYS = {
    "evidence_ledger_sample_control_records": "evidence_ledger_sample_control_record_count",
    "evidence_grade_report_control_records": "evidence_grade_report_control_record_count",
    "revocation_impact_control_records": "revocation_impact_control_record_count",
    "regression_test_control_records": "regression_test_control_record_count",
    "non_conclusion_evidence_type_control_records": "non_conclusion_evidence_type_control_record_count",
    "degradation_instruction_control_records": "degradation_instruction_count",
    "revocation_recovery_instruction_control_records": "revocation_recovery_instruction_count",
}
EXPECTED_CONTROLLED_REPLAY = {
    "phase1_static_shape": "10/9/7/5",
    "phase1_failure_state_count": 12,
    "phase2_control_request_count": 6,
    "phase2_control_input_field_count": 26,
    "phase2_projection_group_count": 10,
    "phase2_fields_per_request": 77,
    "phase2_control_field_check_count": 462,
    "phase2_failure_state_count": 25,
    "phase3_scenario_count": 7,
    "phase3_scenario_field_count": 32,
    "phase3_scenario_field_check_count": 224,
    "phase3_human_handling_required_count": 7,
    "phase3_failure_state_count": 15,
    "phase4_delivery_shape": "7/7/7/7/7/4/2",
    "phase4_chinese_feedback_count": 4,
    "phase4_delivery_field_check_count": 517,
    "phase4_failure_state_count": 18,
}
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "retrieval_execution_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "retrieval_evidence_capture_performed",
    "risk_score_calculation_performed",
    "evidence_grade_change_performed",
    "revocation_execution_performed",
    "recovery_execution_performed",
    "poisoning_defense_execution_performed",
    "report_status_update_performed",
    "audit_log_write_performed",
    "persistent_state_write_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage091_started",
)
ACTUAL_COUNT_FIELDS = (
    "actual_input_request_count",
    "actual_retrieval_execution_count",
    "actual_retrieval_evidence_capture_count",
    "actual_evidence_ledger_access_count",
    "actual_evidence_capture_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_recovery_execution_count",
    "actual_poisoning_defense_execution_count",
    "actual_report_status_update_count",
    "actual_audit_log_write_count",
    "actual_evidence_ledger_sample_write_count",
    "actual_evidence_grade_report_write_count",
    "actual_revocation_impact_list_write_count",
    "actual_regression_test_record_write_count",
    "actual_non_conclusion_type_record_write_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

ArtifactProvider = Callable[[], Mapping[str, Any]]


def build_retrieval_evidence_capture_stage090_review_report(
    *,
    phase1_contract_provider: ArtifactProvider | None = None,
    phase2_contract_provider: ArtifactProvider | None = None,
    phase3_contract_provider: ArtifactProvider | None = None,
    phase4_contract_provider: ArtifactProvider | None = None,
    phase2_report_provider: ArtifactProvider | None = None,
    phase3_report_provider: ArtifactProvider | None = None,
    phase4_report_provider: ArtifactProvider | None = None,
) -> dict[str, Any]:
    """复审冻结 P1--P4 控制工件；漂移时停留在 Stage090 Review gate。"""

    phase1 = _provider_result(phase1_contract_provider or _default_phase1_contract)
    phase2_contract = _provider_result(
        phase2_contract_provider or _default_phase2_contract
    )
    phase3_contract = _provider_result(
        phase3_contract_provider or _default_phase3_contract
    )
    phase4_contract = _provider_result(
        phase4_contract_provider or _default_phase4_contract
    )
    phase2 = _provider_result(phase2_report_provider or _default_phase2_report)
    phase3 = _provider_result(phase3_report_provider or _default_phase3_report)
    phase4 = _provider_result(phase4_report_provider or _default_phase4_report)

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2_contract)
        and _phase2_report_valid(phase2),
        "P3": _phase3_contract_valid(phase3_contract)
        and _phase3_report_valid(phase3),
        "P4": _phase4_contract_valid(phase4_contract)
        and _phase4_report_valid(phase4),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    fixed_shapes = controlled_replay == EXPECTED_CONTROLLED_REPLAY
    authority_preserved = _single_authority_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase4
    )
    failure_and_rollback_preserved = _failure_and_rollback_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract
    )
    delivery_and_whitebox_preserved = _delivery_and_whitebox_boundary(phase3, phase4)
    runtime_actions_disabled = all(
        _runtime_mapping_closed(_mapping(artifact.get("runtime_boundary")))
        and _actual_counts_zero(artifact)
        for artifact in (phase1, phase2_contract, phase3_contract, phase4_contract, phase2, phase3, phase4)
    )
    next_stage_available_but_not_started = _next_stage_available_but_not_started(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase4
    )
    runtime_flags = _runtime_closed_flags()
    review_valid = (
        TASKPACK.is_file()
        and NEXT_TASKPACK.is_file()
        and all(phase_results.values())
        and fixed_shapes
        and authority_preserved
        and failure_and_rollback_preserved
        and delivery_and_whitebox_preserved
        and runtime_actions_disabled
        and next_stage_available_but_not_started
        and all(value is False for value in runtime_flags.values())
    )
    failure_reasons = _failure_reasons(
        phase_results,
        fixed_shapes,
        authority_preserved,
        failure_and_rollback_preserved,
        delivery_and_whitebox_preserved,
        runtime_actions_disabled,
        next_stage_available_but_not_started,
    )
    next_gate = NEXT_GATE if review_valid else REVIEW_GATE
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "fixed_control_shapes_preserved": fixed_shapes,
        "single_authority_boundary_preserved": authority_preserved,
        "failure_stop_and_rollback_boundaries_preserved": failure_and_rollback_preserved,
        "delivery_and_whitebox_boundaries_preserved": delivery_and_whitebox_preserved,
        "runtime_actions_disabled": runtime_actions_disabled
        and all(value is False for value in runtime_flags.values()),
        "next_stage_taskpack_available_but_not_started": next_stage_available_but_not_started,
        "stage091_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE090_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "reviewed_phase_ids": [
            "IDS-STAGE090-P1",
            "IDS-STAGE090-P2",
            "IDS-STAGE090-P3",
            "IDS-STAGE090-P4",
        ],
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": invariants,
        "review_valid": review_valid,
        "failure_reasons": failure_reasons,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": next_gate,
        "source_document_remains_authoritative": authority_preserved,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "business_line_whitebox_human_review_remains_authoritative": (
            delivery_and_whitebox_preserved
        ),
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage090_started": True,
        "stage090_review_started": True,
        "review_control_completed": review_valid,
        "whole_stage_review_performed": False,
        "stage091_started": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "automatic_business_recommendation_allowed": False,
        **{field: 0 for field in ACTUAL_COUNT_FIELDS},
        "rollback": {
            "scope": "STAGE090_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
            "return_to": RETURN_STATE,
            "preserve_phase1_contract": True,
            "preserve_phase2_control_slice": True,
            "preserve_phase3_controlled_scenarios": True,
            "preserve_phase4_delivery_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        **runtime_flags,
    }


def _default_phase1_contract() -> Mapping[str, Any]:
    return _read_json(P1_CONTRACT)


def _default_phase2_contract() -> Mapping[str, Any]:
    return _read_json(P2_CONTRACT)


def _default_phase3_contract() -> Mapping[str, Any]:
    return _read_json(P3_CONTRACT)


def _default_phase4_contract() -> Mapping[str, Any]:
    return _read_json(P4_CONTRACT)


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module("stage090_review_phase2", P2_MODULE)
    return (
        {}
        if module is None
        else _mapping(
            module.execute_retrieval_evidence_capture_control_slice(
                module.build_control_input()
            )
        )
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage090_review_phase3", P3_MODULE)
    return (
        {}
        if module is None
        else _mapping(module.build_retrieval_evidence_capture_phase3_report())
    )


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage090_review_phase4", P4_MODULE)
    return (
        {}
        if module is None
        else _mapping(module.build_retrieval_evidence_capture_phase4_delivery_report())
    )


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    shape = _mapping(contract.get("retrieval_evidence_capture_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    grades = _records(shape.get("evidence_grade_definitions"))
    return (
        contract.get("schema_version")
        == "ids.stage090.retrieval_evidence_capture_contract.phase1.v1"
        and contract.get("stage") == "STAGE-090"
        and contract.get("phase") == "IDS-STAGE090-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE090-P1"
        and contract.get("contract_state")
        == "PHASE1_RETRIEVAL_EVIDENCE_CAPTURE_CONTRACT_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE090-P2-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and all(
            _sequence_length(shape.get(fields_key)) == count
            and _integer(shape.get(count_key)) == count
            for fields_key, count_key, count in P1_SHAPES
        )
        and _integer(shape.get("evidence_grade_count")) == 5
        and tuple(item.get("grade") for item in grades) == ("A", "B", "C", "D", "E")
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 12
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage090_started") is True
        and boundary.get("phase1_started") is True
        and boundary.get("phase2_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage091_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    control_input = _mapping(contract.get("reference_only_control_input_contract"))
    projections = _mapping(contract.get("control_projection_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("schema_version") == "ids.stage090.retrieval_evidence_capture.phase2.v1"
        and contract.get("stage") == "STAGE-090"
        and contract.get("phase") == "IDS-STAGE090-P2"
        and contract.get("task_id") == "IDS-V0_1-STAGE090-P2"
        and contract.get("contract_state")
        == "PHASE2_RETRIEVAL_EVIDENCE_CAPTURE_CONTROL_SLICE_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE090-P3-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and control_input.get("control_prefix") == CONTROL_PREFIX
        and _integer(control_input.get("control_request_count")) == 6
        and _integer(control_input.get("input_field_count")) == 26
        and _sequence_length(control_input.get("fixed_control_scenarios")) == 6
        and _integer(projections.get("each_projection_count")) == 6
        and _integer(projections.get("control_projection_field_total_per_request")) == 77
        and _integer(projections.get("control_projection_field_total")) == 462
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 25
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is False
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage091_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenarios = _mapping(contract.get("scenario_result_contract"))
    boundary = _mapping(contract.get("stage_boundary"))
    return (
        contract.get("schema_version") == "ids.stage090.retrieval_evidence_capture.phase3.v1"
        and contract.get("stage") == "STAGE-090"
        and contract.get("phase") == "IDS-STAGE090-P3"
        and contract.get("task_id") == "IDS-V0_1-STAGE090-P3"
        and contract.get("contract_state")
        == "PHASE3_RETRIEVAL_EVIDENCE_CAPTURE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE090-P4-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and replay.get("control_prefix") == CONTROL_PREFIX
        and _integer(replay.get("required_control_request_count")) == 6
        and _integer(replay.get("required_input_field_count")) == 26
        and _integer(replay.get("required_projection_group_count")) == 10
        and _integer(replay.get("expected_projection_fields_per_request")) == 77
        and _integer(replay.get("expected_phase2_field_check_count")) == 462
        and _integer(scenarios.get("scenario_count")) == 7
        and _integer(scenarios.get("scenario_field_count")) == 32
        and _integer(scenarios.get("expected_scenario_field_check_count")) == 224
        and scenarios.get("all_scenarios_require_business_line_whitebox_handling") is True
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 15
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is True
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_started") is False
        and boundary.get("stage091_started") is False
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    expected_counts = (
        ("evidence_ledger_sample_control_record_count", 7, "evidence_ledger_sample_field_count", 14),
        ("evidence_grade_report_control_record_count", 7, "evidence_grade_report_field_count", 13),
        ("revocation_impact_control_record_count", 7, "revocation_impact_field_count", 13),
        ("regression_test_control_record_count", 7, "regression_test_record_field_count", 14),
        ("non_conclusion_evidence_type_control_record_count", 7, "non_conclusion_evidence_type_field_count", 11),
        ("degradation_instruction_count", 4, "degradation_instruction_field_count", 10),
        ("revocation_recovery_instruction_count", 2, "revocation_recovery_instruction_field_count", 11),
    )
    return (
        contract.get("schema_version")
        == "ids.stage090.retrieval_evidence_capture.phase4.delivery.v1"
        and contract.get("stage") == "STAGE-090"
        and contract.get("phase") == "IDS-STAGE090-P4"
        and contract.get("task_id") == "IDS-V0_1-STAGE090-P4"
        and contract.get("contract_state")
        == "PHASE4_RETRIEVAL_EVIDENCE_CAPTURE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and contract.get("next_gate") == REVIEW_GATE
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and delivery.get("delivery_executable") is True
        and delivery.get("execution_ready") is False
        and delivery.get("metadata_only") is True
        and all(
            _integer(delivery.get(count_key)) == expected_count
            and _integer(delivery.get(field_key)) == expected_field_count
            for count_key, expected_count, field_key, expected_field_count in expected_counts
        )
        and _integer(delivery.get("delivery_field_check_count")) == 517
        and _integer(delivery.get("chinese_feedback_count")) == 4
        and delivery.get("revocation_impact_declared_not_applied") is True
        and delivery.get("non_conclusion_evidence_types_recorded") is True
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 18
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_completed") is True
        and boundary.get("phase4_started") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage090_review_started") is False
        and boundary.get("stage091_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase2_report_valid(report: Mapping[str, Any]) -> bool:
    groups_valid = all(
        _integer(report.get(f"{prefix}_control_projection_count")) == 6
        and len(_records(report.get(f"{prefix}_control_projections"))) == 6
        and all(
            len(record) == field_count
            and _record_references_are_control_only(record, (CONTROL_PREFIX,))
            for record in _records(report.get(f"{prefix}_control_projections"))
        )
        for prefix, field_count in P2_GROUPS
    )
    return (
        report.get("schema_version") == "ids.stage090.retrieval_evidence_capture.phase2.v1"
        and report.get("record_kind") == "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_EVIDENCE_CAPTURE"
        and report.get("input_accepted") is True
        and report.get("execution_state")
        == "CONTROL_RETRIEVAL_EVIDENCE_CAPTURE_PROJECTIONS_DECLARED_NOT_EXECUTED"
        and report.get("failure_state") is None
        and _integer(report.get("control_input_count")) == 6
        and report.get("persistent_record_created") is False
        and groups_valid
        and _actual_counts_zero(report)
        and _runtime_mapping_closed(_mapping(report.get("runtime_boundary")))
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _records(report.get("scenario_results"))
    by_id = {record.get("scenario_id"): record for record in scenarios}
    degraded = {
        "low_ocr_evidence_degradation_control": "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
        "old_version_evidence_degradation_control": "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
        "conflict_evidence_degradation_control": "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
    }
    return (
        report.get("schema_version") == "ids.stage090.retrieval_evidence_capture.phase3.v1"
        and report.get("record_kind")
        == "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_EVIDENCE_CAPTURE_EXCEPTION_SCENARIOS"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_RETRIEVAL_EVIDENCE_CAPTURE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE090-P3-GATE"
        and report.get("next_gate") == "IDS-STAGE090-P4-GATE"
        and report.get("phase2_control_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and _integer(report.get("phase2_control_request_count")) == 6
        and _integer(report.get("phase2_projection_group_count")) == 10
        and _integer(report.get("phase2_field_check_count")) == 462
        and _integer(report.get("scenario_count")) == 7
        and _integer(report.get("scenario_field_count")) == 32
        and _integer(report.get("scenario_field_check_count")) == 224
        and tuple(record.get("scenario_id") for record in scenarios) == P3_SCENARIOS
        and all(len(record) == 32 for record in scenarios)
        and all(_record_references_are_control_only(record, (CONTROL_PREFIX,)) for record in scenarios)
        and all(
            record.get("expectation_met") is True
            and record.get("human_handling_required") is True
            and record.get("business_line_whitebox_human_approval_recorded") is False
            and record.get("actual_report_status_updated") is False
            and record.get("actual_evidence_grade_changed") is False
            and record.get("silent_drop") is False
            for record in scenarios
        )
        and by_id.get("no_internal_evidence_gap_control", {}).get("conclusion_acceptance_state")
        == "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW"
        and all(
            by_id.get(scenario_id, {}).get("evidence_disposition_state") == expected
            for scenario_id, expected in degraded.items()
        )
        and by_id.get("revoked_evidence_report_impact_control", {}).get("report_status_impact_state")
        == "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        and by_id.get("malicious_evidence_quarantine_control", {}).get("evidence_disposition_state")
        == "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED"
        and by_id.get("low_grade_high_trust_masquerade_control", {}).get("evidence_grade_label")
        == "D"
        and by_id.get("low_grade_high_trust_masquerade_control", {}).get("conclusion_acceptance_state")
        == "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
        and _actual_counts_zero(report)
        and _runtime_mapping_closed(_mapping(report.get("runtime_boundary")))
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    groups_valid = all(
        _integer(report.get(P4_REPORT_COUNT_KEYS[records_key])) == record_count
        and len(_records(report.get(records_key))) == record_count
        and all(
            len(record) == field_count
            and _record_references_are_control_only(
                record, (CONTROL_PREFIX, DELIVERY_PREFIX)
            )
            for record in _records(report.get(records_key))
        )
        for records_key, record_count, field_count in P4_DELIVERY_GROUPS
    )
    revoked = _record_by_id(
        _records(report.get("revocation_impact_control_records")),
        "scenario_id",
        "revoked_evidence_report_impact_control",
    )
    masquerade = _record_by_id(
        _records(report.get("non_conclusion_evidence_type_control_records")),
        "scenario_id",
        "low_grade_high_trust_masquerade_control",
    )
    degradation = _records(report.get("degradation_instruction_control_records"))
    recovery = _records(report.get("revocation_recovery_instruction_control_records"))
    return (
        report.get("schema_version")
        == "ids.stage090.retrieval_evidence_capture.phase4.delivery.v1"
        and report.get("record_kind") == "RETRIEVAL_EVIDENCE_CAPTURE_DELIVERY_EVIDENCE_REPORT"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_RETRIEVAL_EVIDENCE_CAPTURE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE090-P4-GATE"
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("phase3_control_shape_preserved") is True
        and report.get("phase3_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and report.get("delivery_evidence_metadata_only") is True
        and _integer(report.get("phase2_control_field_check_count")) == 462
        and _integer(report.get("phase3_scenario_count")) == 7
        and _integer(report.get("phase3_scenario_field_count")) == 32
        and _integer(report.get("phase3_scenario_field_check_count")) == 224
        and _integer(report.get("delivery_field_check_count")) == 517
        and groups_valid
        and _sequence_length(report.get("chinese_feedback")) == 4
        and report.get("all_delivery_references_control_only") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document") is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and report.get("second_authoritative_source_created") is False
        and report.get("automatic_conclusion_allowed") is False
        and report.get("automatic_degradation_allowed") is False
        and report.get("automatic_revocation_allowed") is False
        and report.get("automatic_recovery_allowed") is False
        and report.get("automatic_report_status_update_allowed") is False
        and revoked.get("report_status_impact_state")
        == "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        and revoked.get("actual_report_status_updated") is False
        and revoked.get("actual_revocation_impact_list_written") is False
        and masquerade.get("non_conclusion_state") == "CONTROL_NOT_A_CONCLUSION_BASIS"
        and masquerade.get("automatic_conclusion_allowed") is False
        and all(
            item.get("instruction_state")
            == "CONTROL_DEGRADATION_INSTRUCTION_DECLARED_NOT_EXECUTED"
            and item.get("actual_evidence_degradation_performed") is False
            and item.get("automatic_degradation_allowed") is False
            and item.get("human_handling_required") is True
            for item in degradation
        )
        and all(
            item.get("entry_precondition")
            == "CONTROL_FUTURE_AUTHORIZATION_AND_WHITEBOX_APPROVAL_REQUIRED"
            and item.get("actual_revocation_execution_performed") is False
            and item.get("actual_recovery_execution_performed") is False
            and item.get("human_handling_required") is True
            for item in recovery
        )
        and _actual_counts_zero(report)
        and _runtime_mapping_closed(_mapping(report.get("runtime_boundary")))
        and report.get("stage091_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int | str]:
    p1 = _mapping(phase1.get("retrieval_evidence_capture_contract"))
    p2_input = _mapping(phase2.get("reference_only_control_input_contract"))
    p2_projection = _mapping(phase2.get("control_projection_contract"))
    p3_scenarios = _mapping(phase3.get("scenario_result_contract"))
    p4_delivery = _mapping(phase4.get("delivery_evidence_contract"))
    return {
        "phase1_static_shape": "/".join(
            str(_integer(p1.get(count_key)))
            for _fields_key, count_key, _expected in P1_SHAPES
        )
        + f"/{_integer(p1.get('evidence_grade_count'))}",
        "phase1_failure_state_count": _integer(
            _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase2_control_request_count": _integer(p2_input.get("control_request_count")),
        "phase2_control_input_field_count": _integer(p2_input.get("input_field_count")),
        "phase2_projection_group_count": len(P2_GROUPS),
        "phase2_fields_per_request": _integer(
            p2_projection.get("control_projection_field_total_per_request")
        ),
        "phase2_control_field_check_count": _integer(
            p2_projection.get("control_projection_field_total")
        ),
        "phase2_failure_state_count": _integer(
            _mapping(phase2.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase3_scenario_count": _integer(p3_scenarios.get("scenario_count")),
        "phase3_scenario_field_count": _integer(p3_scenarios.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _integer(
            p3_scenarios.get("expected_scenario_field_check_count")
        ),
        "phase3_human_handling_required_count": sum(
            item.get("human_handling_required") is True
            for item in _records(phase3_report.get("scenario_results"))
        ),
        "phase3_failure_state_count": _integer(
            _mapping(phase3.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase4_delivery_shape": "/".join(
            str(record_count) for _key, record_count, _field_count in P4_DELIVERY_GROUPS
        ),
        "phase4_chinese_feedback_count": _sequence_length(
            phase4_report.get("chinese_feedback")
        ),
        "phase4_delivery_field_check_count": _integer(
            p4_delivery.get("delivery_field_check_count")
        ),
        "phase4_failure_state_count": _integer(
            _mapping(phase4.get("failure_and_stop_contract")).get("failure_state_count")
        ),
    }


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        all(
            _source_authority_closed(_mapping(artifact.get("source_authority")))
            for artifact in (phase1, phase2, phase3, phase4)
        )
        and _mapping(phase4.get("source_authority")).get(
            "source_document_remains_authoritative"
        )
        is True
        and _mapping(phase4.get("source_authority")).get(
            "business_line_whitebox_human_review_remains_authoritative"
        )
        is True
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and phase4_report.get("second_authoritative_source_created") is False
        and phase4_report.get("delivery_control_metadata_can_replace_source_document")
        is False
        and phase4_report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
    )


def _failure_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        _integer(_mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count"))
        == 12
        and _integer(_mapping(phase2.get("failure_and_stop_contract")).get("failure_state_count"))
        == 25
        and _integer(_mapping(phase3.get("failure_and_stop_contract")).get("failure_state_count"))
        == 15
        and _integer(_mapping(phase4.get("failure_and_stop_contract")).get("failure_state_count"))
        == 18
        and _mapping(phase4.get("rollback_contract")).get("fallback_result")
        == P4_RETURN_STATE
        and _mapping(phase4.get("stage_and_phase_boundary")).get(
            "whole_stage_review_performed"
        )
        is False
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any], phase4: Mapping[str, Any]
) -> bool:
    p3_scenarios = _records(phase3.get("scenario_results"))
    p4_records = _records(phase4.get("non_conclusion_evidence_type_control_records"))
    return (
        len(p3_scenarios) == 7
        and all(item.get("human_handling_required") is True for item in p3_scenarios)
        and len(p4_records) == 7
        and all(
            item.get("automatic_conclusion_allowed") is False
            and item.get("human_handling_required") is True
            for item in p4_records
        )
        and phase4.get("all_delivery_references_control_only") is True
        and phase4.get("automatic_conclusion_allowed") is False
        and phase4.get("automatic_degradation_allowed") is False
        and phase4.get("automatic_revocation_allowed") is False
        and phase4.get("automatic_recovery_allowed") is False
    )


def _next_stage_available_but_not_started(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    boundaries = (
        _mapping(phase1.get("stage_and_phase_boundary")),
        _mapping(phase2.get("stage_and_phase_boundary")),
        _mapping(phase3.get("stage_boundary")),
        _mapping(phase4.get("stage_and_phase_boundary")),
    )
    return (
        NEXT_TASKPACK.is_file()
        and all(boundary.get("stage091_started") is False for boundary in boundaries)
        and phase4_report.get("stage091_started") is False
        and phase4_report.get("next_gate") == REVIEW_GATE
    )


def _failure_reasons(
    phase_results: Mapping[str, bool],
    fixed_shapes: bool,
    authority_preserved: bool,
    failure_and_rollback_preserved: bool,
    delivery_and_whitebox_preserved: bool,
    runtime_actions_disabled: bool,
    next_stage_available_but_not_started: bool,
) -> list[str]:
    reasons = [
        f"{phase}_CONTRACT_OR_CONTROL_OUTPUT_INVALID"
        for phase, valid in phase_results.items()
        if not valid
    ]
    if not fixed_shapes:
        reasons.append("CONTROLLED_REPLAY_SHAPE_MISMATCH")
    if not authority_preserved:
        reasons.append("SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not failure_and_rollback_preserved:
        reasons.append("FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH")
    if not delivery_and_whitebox_preserved:
        reasons.append("DELIVERY_OR_WHITEBOX_BOUNDARY_MISMATCH")
    if not runtime_actions_disabled or not next_stage_available_but_not_started:
        reasons.append("RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED")
    return reasons


def _source_authority_closed(source: Mapping[str, Any]) -> bool:
    required_false = (
        "second_authoritative_source_created",
        "source_body_or_path_allowed",
        "raw_metadata_content_access_allowed",
        "live_source_read_performed",
        "authorized_fixture_access_performed",
        "retrieval_result_access_performed",
        "evidence_ledger_access_performed",
    )
    return bool(source) and all(source.get(field) is False for field in required_false)


def _runtime_mapping_closed(boundary: Mapping[str, Any]) -> bool:
    return bool(boundary) and all(
        (value is False or _integer(value) == 0)
        if key.startswith("actual_")
        else value is False
        for key, value in boundary.items()
    )


def _actual_counts_zero(report: Mapping[str, Any]) -> bool:
    return all(
        _integer(value) == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _record_references_are_control_only(
    record: Mapping[str, Any], prefixes: Sequence[str]
) -> bool:
    return all(
        isinstance(value, str) and any(prefix in value for prefix in prefixes)
        for key, value in record.items()
        if key.endswith("_ref")
    )


def _record_by_id(
    records: Sequence[Mapping[str, Any]], key: str, expected: str
) -> Mapping[str, Any]:
    return next((record for record in records if record.get(key) == expected), {})


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _provider_result(provider: ArtifactProvider) -> Mapping[str, Any]:
    try:
        value = provider()
    except Exception:
        return {}
    return _mapping(value)


def _load_module(name: str, path: Path) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError, RuntimeError, SyntaxError):
        return None


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _records(value: object) -> list[Mapping[str, Any]]:
    return (
        list(value)
        if isinstance(value, list) and all(isinstance(item, Mapping) for item in value)
        else []
    )


def _sequence_length(value: object) -> int:
    return len(value) if isinstance(value, (list, tuple)) else 0


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1
