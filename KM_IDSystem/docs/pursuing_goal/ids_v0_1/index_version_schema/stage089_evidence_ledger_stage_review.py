"""Stage089 证据账本 Schema 的纯内存整阶段机械复审。

本模块只复核冻结的 P1--P4 合同与控制输出。它不会读取业务资料、真实
evidence ledger、报告、审计、数据库或物理索引；也不会执行 OCR、版本／
冲突评估、风险计算、可信等级变更、撤回、恢复、投毒处置、模型、Agent、
OVH、生产或上传。复审通过只开放下一阶段闸门，不启动 Stage090。
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
    / "STAGE-089_证据账本Schema.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-090_从检索捕获证据.md"
)
P1_CONTRACT = BASE / "stage089_evidence_ledger_schema_contract.json"
P2_CONTRACT = BASE / "stage089_evidence_ledger_control_slice_contract.json"
P3_CONTRACT = BASE / "stage089_evidence_ledger_scenarios_contract.json"
P4_CONTRACT = BASE / "stage089_evidence_ledger_delivery_contract.json"
P2_MODULE = BASE / "stage089_evidence_ledger_control_slice.py"
P3_MODULE = BASE / "stage089_evidence_ledger_controlled_scenarios.py"
P4_MODULE = BASE / "stage089_evidence_ledger_delivery.py"

SCHEMA_VERSION = "ids.stage089.evidence_ledger.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE089-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-089"
PASS_RESULT = "PASS_REVIEWED_EVIDENCE_LEDGER_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_EVIDENCE_LEDGER_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE089-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE090-P1-GATE"
RETURN_STATE = "PASS_EVIDENCE_LEDGER_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage089-p2:"
DELIVERY_PREFIX = ":control:stage089-p4:"

P1_FIELD_SHAPES = {
    "future_evidence_record_fields": ("evidence_record_field_count", 10),
    "future_evidence_relation_record_fields": (
        "evidence_relation_record_field_count",
        8,
    ),
    "future_evidence_gap_record_fields": ("evidence_gap_record_field_count", 5),
    "future_risk_score_record_fields": ("risk_score_record_field_count", 8),
    "future_revocation_record_fields": ("revocation_record_field_count", 7),
    "future_knowledge_base_poisoning_defense_record_fields": (
        "knowledge_base_poisoning_defense_record_field_count",
        8,
    ),
    "future_critical_conclusion_binding_record_fields": (
        "critical_conclusion_binding_record_field_count",
        7,
    ),
}
P2_PROJECTION_FIELD_COUNTS = {
    "evidence_schema": 10,
    "evidence_relation": 8,
    "evidence_gap": 5,
    "evidence_capture": 6,
    "risk_score": 8,
    "revocation": 7,
    "poisoning_defense": 8,
    "critical_conclusion_binding": 7,
    "degradation": 8,
    "future_integration": 7,
}
P2_CONTROL_SCENARIOS = (
    "grade_a_pending_whitebox_review_reference_only",
    "low_grade_evidence_degraded_reference_only",
    "conflict_evidence_degraded_reference_only",
    "expired_evidence_degraded_reference_only",
    "revoked_evidence_degraded_reference_only",
    "suspected_poisoning_quarantined_reference_only",
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
EXPECTED_CONTROLLED_REPLAY = {
    "phase1_record_shapes": "10/8/5/8/7/8/7",
    "phase1_failure_state_count": 23,
    "phase2_control_request_count": 6,
    "phase2_control_input_field_count": 24,
    "phase2_projection_set_count": 10,
    "phase2_control_field_check_count": 444,
    "phase2_failure_state_count": 23,
    "phase3_scenario_count": 7,
    "phase3_scenario_field_count": 32,
    "phase3_scenario_field_check_count": 224,
    "phase3_human_handling_required_count": 7,
    "phase3_failure_state_count": 15,
    "phase4_delivery_shape": "7/7/7/7/7/4/2",
    "phase4_delivery_field_check_count": 517,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 18,
}
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "retrieval_evidence_capture_performed",
    "risk_score_calculation_performed",
    "evidence_grade_change_performed",
    "ocr_quality_evaluation_performed",
    "source_version_comparison_performed",
    "conflict_resolution_performed",
    "revocation_execution_performed",
    "recovery_execution_performed",
    "poisoning_defense_execution_performed",
    "report_status_update_performed",
    "audit_log_write_performed",
    "persistent_state_write_performed",
    "external_api_call_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage090_started",
)
ACTUAL_COUNT_FIELDS = (
    "actual_input_request_count",
    "actual_evidence_ledger_access_count",
    "actual_database_connection_count",
    "actual_evidence_capture_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_recovery_execution_count",
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


def build_evidence_ledger_stage089_review_report(
    *,
    phase1_contract_provider: ArtifactProvider | None = None,
    phase2_contract_provider: ArtifactProvider | None = None,
    phase3_contract_provider: ArtifactProvider | None = None,
    phase4_contract_provider: ArtifactProvider | None = None,
    phase2_report_provider: ArtifactProvider | None = None,
    phase3_report_provider: ArtifactProvider | None = None,
    phase4_report_provider: ArtifactProvider | None = None,
) -> dict[str, Any]:
    """机械复审冻结 P1--P4 工件；任何漂移都留在 Review gate。"""

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
        and _phase2_report_valid(phase2_contract, phase2),
        "P3": _phase3_contract_valid(phase3_contract)
        and _phase3_report_valid(phase3_contract, phase3),
        "P4": _phase4_contract_valid(phase4_contract)
        and _phase4_report_valid(phase4_contract, phase4),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    fixed_shapes = controlled_replay == EXPECTED_CONTROLLED_REPLAY
    authority_preserved = _single_authority_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    failure_and_rollback_preserved = _failure_and_rollback_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract
    )
    delivery_and_whitebox_preserved = _delivery_and_whitebox_boundary(phase3, phase4)
    runtime_actions_disabled = _nested_runtime_closed(
        phase1,
        phase2_contract,
        phase3_contract,
        phase4_contract,
        phase2,
        phase3,
        phase4,
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
        "failure_stop_and_rollback_boundaries_preserved": (
            failure_and_rollback_preserved
        ),
        "delivery_and_whitebox_boundaries_preserved": (
            delivery_and_whitebox_preserved
        ),
        "runtime_actions_disabled": runtime_actions_disabled
        and all(value is False for value in runtime_flags.values()),
        "next_stage_taskpack_available_but_not_started": (
            next_stage_available_but_not_started
        ),
        "stage090_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE089_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "reviewed_phase_ids": [
            "IDS-STAGE089-P1",
            "IDS-STAGE089-P2",
            "IDS-STAGE089-P3",
            "IDS-STAGE089-P4",
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
        "stage089_started": True,
        "review_control_completed": review_valid,
        "whole_stage_review_performed": False,
        "stage090_started": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "automatic_business_recommendation_allowed": False,
        **{field: 0 for field in ACTUAL_COUNT_FIELDS},
        "rollback": {
            "scope": "STAGE089_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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
    module = _load_module("stage089_review_phase2", P2_MODULE)
    if module is None:
        return {}
    return _mapping(
        module.execute_evidence_ledger_control_slice(module.build_control_input())
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage089_review_phase3", P3_MODULE)
    if module is None:
        return {}
    return _mapping(module.build_evidence_ledger_phase3_report())


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage089_review_phase4", P4_MODULE)
    if module is None:
        return {}
    return _mapping(module.build_evidence_ledger_phase4_delivery_report())


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    schema = _mapping(contract.get("evidence_ledger_schema_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    grades = _records(schema.get("evidence_grade_definitions"))
    shapes_valid = all(
        _sequence_length(schema.get(fields_key)) == expected_count
        and _integer(schema.get(count_key)) == expected_count
        for fields_key, (count_key, expected_count) in P1_FIELD_SHAPES.items()
    )
    return (
        contract.get("schema_version")
        == "ids.stage089.evidence_ledger_schema_contract.phase1.v1"
        and contract.get("stage") == "STAGE-089"
        and contract.get("phase") == "IDS-STAGE089-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE089-P1"
        and contract.get("contract_state")
        == "PHASE1_EVIDENCE_LEDGER_SCHEMA_CONTRACT_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE089-P2-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and shapes_valid
        and tuple(item.get("grade") for item in grades) == ("A", "B", "C", "D", "E")
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 23
        and _integer(_mapping(contract.get("chinese_feedback_contract")).get("feedback_count"))
        == 4
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage089_started") is True
        and boundary.get("phase1_started") is True
        and boundary.get("phase2_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage090_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    control_input = _mapping(contract.get("reference_only_control_input_contract"))
    projections = _mapping(contract.get("control_projection_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    shapes_valid = all(
        _sequence_length(projections.get(f"{prefix}_projection_fields")) == count
        and _integer(projections.get(f"{prefix}_projection_field_count")) == count
        for prefix, count in P2_PROJECTION_FIELD_COUNTS.items()
    )
    return (
        contract.get("schema_version") == "ids.stage089.evidence_ledger_schema.phase2.v1"
        and contract.get("stage") == "STAGE-089"
        and contract.get("phase") == "IDS-STAGE089-P2"
        and contract.get("task_id") == "IDS-V0_1-STAGE089-P2"
        and contract.get("contract_state")
        == "PHASE2_EVIDENCE_LEDGER_CONTROL_SLICE_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE089-P3-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and control_input.get("control_prefix") == CONTROL_PREFIX
        and _integer(control_input.get("control_request_count")) == 6
        and _integer(control_input.get("input_field_count")) == 24
        and tuple(control_input.get("fixed_control_scenarios", ())) == P2_CONTROL_SCENARIOS
        and shapes_valid
        and _integer(projections.get("control_projection_field_total_per_request")) == 74
        and _integer(projections.get("control_projection_field_total")) == 444
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 23
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_started") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is False
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage090_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenarios = _mapping(contract.get("scenario_result_contract"))
    boundary = _mapping(contract.get("stage_boundary"))
    return (
        contract.get("schema_version") == "ids.stage089.evidence_ledger.phase3.v1"
        and contract.get("stage") == "STAGE-089"
        and contract.get("phase") == "IDS-STAGE089-P3"
        and contract.get("task_id") == "IDS-V0_1-STAGE089-P3"
        and contract.get("contract_state")
        == "PHASE3_EVIDENCE_LEDGER_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE089-P4-GATE"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and replay.get("control_prefix") == CONTROL_PREFIX
        and _integer(replay.get("required_control_request_count")) == 6
        and _integer(replay.get("required_input_field_count")) == 24
        and _integer(replay.get("required_projection_group_count")) == 10
        and _integer(replay.get("expected_phase2_field_check_count")) == 444
        and _integer(scenarios.get("scenario_count")) == 7
        and _integer(scenarios.get("scenario_field_count")) == 32
        and _integer(scenarios.get("expected_scenario_field_check_count")) == 224
        and scenarios.get("all_scenarios_require_business_line_whitebox_handling")
        is True
        and scenarios.get("actual_report_status_updated") is False
        and scenarios.get("actual_evidence_grade_changed") is False
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 15
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is True
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_started") is False
        and boundary.get("stage090_started") is False
        and boundary.get("ovh_started") is False
        and boundary.get("production_started") is False
        and boundary.get("upload_or_push_started") is False
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    expected_counts = {
        "evidence_ledger_sample_control_record_count": 7,
        "evidence_ledger_sample_field_count": 14,
        "evidence_grade_report_control_record_count": 7,
        "evidence_grade_report_field_count": 13,
        "revocation_impact_control_record_count": 7,
        "revocation_impact_field_count": 13,
        "regression_test_control_record_count": 7,
        "regression_test_record_field_count": 14,
        "non_conclusion_evidence_type_control_record_count": 7,
        "non_conclusion_evidence_type_field_count": 11,
        "degradation_instruction_count": 4,
        "degradation_instruction_field_count": 10,
        "revocation_recovery_instruction_count": 2,
        "revocation_recovery_instruction_field_count": 11,
        "delivery_field_check_count": 517,
        "chinese_feedback_count": 4,
    }
    return (
        contract.get("schema_version") == "ids.stage089.evidence_ledger.phase4.delivery.v1"
        and contract.get("stage") == "STAGE-089"
        and contract.get("phase") == "IDS-STAGE089-P4"
        and contract.get("task_id") == "IDS-V0_1-STAGE089-P4"
        and contract.get("contract_state")
        == "PHASE4_EVIDENCE_LEDGER_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and contract.get("entry_gate") == "IDS-STAGE089-P4-GATE"
        and contract.get("next_gate") == REVIEW_GATE
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and all(_integer(delivery.get(key)) == expected for key, expected in expected_counts.items())
        and delivery.get("revocation_impact_declared_not_applied") is True
        and delivery.get("low_grade_cannot_support_high_trust_conclusion") is True
        and delivery.get("non_conclusion_evidence_types_recorded") is True
        and all(
            delivery.get(key) is False
            for key in (
                "actual_evidence_ledger_sample_written",
                "actual_evidence_grade_report_written",
                "actual_revocation_impact_list_written",
                "actual_regression_test_record_written",
                "actual_non_conclusion_type_record_written",
                "actual_evidence_degradation_performed",
                "actual_revocation_execution_performed",
                "actual_recovery_execution_performed",
            )
        )
        and _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
        == 18
        and _runtime_mapping_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage089_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_completed") is True
        and boundary.get("phase4_started") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage089_review_started") is False
        and boundary.get("stage090_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase2_report_valid(
    contract: Mapping[str, Any], report: Mapping[str, Any]
) -> bool:
    projections = _mapping(contract.get("control_projection_contract"))
    groups_valid = True
    for prefix, field_count in P2_PROJECTION_FIELD_COUNTS.items():
        records = _records(report.get(f"{prefix}_control_projections"))
        expected_fields = tuple(projections.get(f"{prefix}_projection_fields", ()))
        groups_valid = groups_valid and (
            _integer(report.get(f"{prefix}_control_projection_count")) == 6
            and len(records) == 6
            and all(set(record) == set(expected_fields) for record in records)
            and all(len(record) == field_count for record in records)
            and _records_references_are_opaque(records)
        )
    return (
        report.get("schema_version") == "ids.stage089.evidence_ledger_schema.phase2.v1"
        and report.get("input_accepted") is True
        and report.get("execution_state")
        == "CONTROL_EVIDENCE_LEDGER_PROJECTIONS_DECLARED_NOT_EXECUTED"
        and report.get("failure_state") is None
        and _integer(report.get("control_input_count")) == 6
        and report.get("persistent_record_created") is False
        and _actual_counts_zero(report)
        and _runtime_mapping_closed(_mapping(report.get("runtime_boundary")))
        and groups_valid
    )


def _phase3_report_valid(
    contract: Mapping[str, Any], report: Mapping[str, Any]
) -> bool:
    scenario_contract = _mapping(contract.get("scenario_result_contract"))
    scenarios = _records(report.get("scenario_results"))
    expected_fields = tuple(scenario_contract.get("scenario_fields", ()))
    scenario_semantics = _phase3_scenario_semantics(scenarios)
    return (
        report.get("schema_version") == "ids.stage089.evidence_ledger.phase3.v1"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_EVIDENCE_LEDGER_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE089-P3-GATE"
        and report.get("next_gate") == "IDS-STAGE089-P4-GATE"
        and report.get("phase2_control_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and _integer(report.get("phase2_control_request_count")) == 6
        and _integer(report.get("phase2_projection_group_count")) == 10
        and _integer(report.get("phase2_field_check_count")) == 444
        and _integer(report.get("scenario_count")) == 7
        and _integer(report.get("scenario_field_count")) == 32
        and _integer(report.get("scenario_field_check_count")) == 224
        and tuple(item.get("scenario_id") for item in scenarios) == P3_SCENARIOS
        and len(scenarios) == 7
        and all(set(record) == set(expected_fields) for record in scenarios)
        and all(_records_references_are_opaque([record]) for record in scenarios)
        and all(
            record.get("expectation_met") is True
            and record.get("human_handling_required") is True
            and record.get("business_line_whitebox_human_approval_recorded") is False
            and record.get("actual_report_status_updated") is False
            and record.get("actual_evidence_grade_changed") is False
            and record.get("silent_drop") is False
            for record in scenarios
        )
        and scenario_semantics
        and _actual_counts_zero(report)
        and _runtime_mapping_closed(_mapping(report.get("runtime_boundary")))
    )


def _phase4_report_valid(
    contract: Mapping[str, Any], report: Mapping[str, Any]
) -> bool:
    groups_valid = True
    for records_key, record_count, field_count in P4_DELIVERY_GROUPS:
        records = _records(report.get(records_key))
        groups_valid = groups_valid and (
            len(records) == record_count
            and all(len(record) == field_count for record in records)
            and _records_references_are_opaque(records)
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
    recovery = _records(report.get("revocation_recovery_instruction_control_records"))
    degradation = _records(report.get("degradation_instruction_control_records"))
    return (
        report.get("schema_version") == "ids.stage089.evidence_ledger.phase4.delivery.v1"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_EVIDENCE_LEDGER_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE089-P4-GATE"
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("phase3_control_shape_preserved") is True
        and report.get("phase3_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and report.get("delivery_evidence_metadata_only") is True
        and _integer(report.get("phase2_control_field_check_count")) == 444
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
        and masquerade.get("non_conclusion_state")
        == "CONTROL_NOT_A_CONCLUSION_BASIS"
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
        and report.get("stage090_started") is False
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
    phase1_schema = _mapping(phase1.get("evidence_ledger_schema_contract"))
    phase2_input = _mapping(phase2.get("reference_only_control_input_contract"))
    phase2_projections = _mapping(phase2.get("control_projection_contract"))
    phase3_scenarios = _mapping(phase3.get("scenario_result_contract"))
    phase4_delivery = _mapping(phase4.get("delivery_evidence_contract"))
    return {
        "phase1_record_shapes": "/".join(
            str(expected_count)
            for _fields_key, (_count_key, expected_count) in P1_FIELD_SHAPES.items()
        ),
        "phase1_failure_state_count": _integer(
            _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase2_control_request_count": _integer(control_input_or_empty(phase2_input, "control_request_count")),
        "phase2_control_input_field_count": _integer(control_input_or_empty(phase2_input, "input_field_count")),
        "phase2_projection_set_count": len(P2_PROJECTION_FIELD_COUNTS),
        "phase2_control_field_check_count": _integer(
            phase2_projections.get("control_projection_field_total")
        ),
        "phase2_failure_state_count": _integer(
            _mapping(phase2.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase3_scenario_count": _integer(phase3_scenarios.get("scenario_count")),
        "phase3_scenario_field_count": _integer(phase3_scenarios.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _integer(
            phase3_scenarios.get("expected_scenario_field_check_count")
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
        "phase4_delivery_field_check_count": _integer(
            phase4_delivery.get("delivery_field_check_count")
        ),
        "phase4_chinese_feedback_count": _sequence_length(
            phase4_report.get("chinese_feedback")
        ),
        "phase4_failure_state_count": _integer(
            _mapping(phase4.get("failure_and_stop_contract")).get("failure_state_count")
        ),
    }


def control_input_or_empty(mapping: Mapping[str, Any], key: str) -> Any:
    """保持复审字段读取为显式空值，不从业务输入回退。"""

    return mapping.get(key)


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        all(
            _source_authority_closed(_mapping(artifact.get("source_authority")))
            for artifact in (phase1, phase2, phase3, phase4)
        )
        and phase3_report.get("second_authoritative_source_created") is False
        and phase4_report.get("second_authoritative_source_created") is False
        and phase4_report.get("source_document_remains_authoritative") is True
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
    contracts = (
        (phase1, 23),
        (phase2, 23),
        (phase3, 15),
        (phase4, 18),
    )
    phase4_failure = _mapping(phase4.get("failure_and_stop_contract"))
    phase4_rollback = _mapping(phase4.get("rollback_contract"))
    return (
        all(
            _integer(_mapping(contract.get("failure_and_stop_contract")).get("failure_state_count"))
            == count
            for contract, count in contracts
        )
        and phase4_failure.get("automatic_conclusion_allowed") is False
        and phase4_failure.get("automatic_degradation_allowed") is False
        and phase4_failure.get("automatic_revocation_allowed") is False
        and phase4_failure.get("automatic_recovery_allowed") is False
        and phase4_failure.get("automatic_report_status_update_allowed") is False
        and phase4_rollback.get("fallback_result")
        == "PASS_EVIDENCE_LEDGER_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and phase4_rollback.get("actual_revocation_or_recovery_performed") is False
        and phase4_rollback.get("actual_runtime_or_production_state_changed") is False
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any], phase4: Mapping[str, Any]
) -> bool:
    scenarios = _records(phase3.get("scenario_results"))
    non_conclusion = _records(phase4.get("non_conclusion_evidence_type_control_records"))
    return (
        len(scenarios) == 7
        and all(
            item.get("human_handling_required") is True
            and item.get("business_line_whitebox_human_approval_recorded") is False
            for item in scenarios
        )
        and phase4.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and all(item.get("automatic_conclusion_allowed") is False for item in non_conclusion)
    )


def _nested_runtime_closed(*artifacts: Mapping[str, Any]) -> bool:
    return all(
        _runtime_mapping_closed(_mapping(artifact.get("runtime_boundary")))
        and _actual_counts_zero(artifact)
        for artifact in artifacts
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
        and all(boundary.get("stage090_started") is False for boundary in boundaries)
        and phase4_report.get("stage090_started") is False
        and phase4_report.get("github_upload_allowed") is False
        and phase4_report.get("push_allowed") is False
    )


def _phase3_scenario_semantics(scenarios: Sequence[Mapping[str, Any]]) -> bool:
    revoked = _record_by_id(
        scenarios, "scenario_id", "revoked_evidence_report_impact_control"
    )
    masquerade = _record_by_id(
        scenarios, "scenario_id", "low_grade_high_trust_masquerade_control"
    )
    return (
        revoked.get("report_status_impact_state")
        == "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        and revoked.get("actual_report_status_updated") is False
        and masquerade.get("evidence_grade_label") == "D"
        and masquerade.get("conclusion_acceptance_state")
        == "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
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
    reasons = [f"{phase}_CONTROL_ARTIFACT_INVALID" for phase, valid in phase_results.items() if not valid]
    if not fixed_shapes:
        reasons.append("FIXED_CONTROL_SHAPE_MISMATCH")
    if not authority_preserved:
        reasons.append("SINGLE_AUTHORITY_BOUNDARY_BROKEN")
    if not failure_and_rollback_preserved:
        reasons.append("FAILURE_OR_ROLLBACK_BOUNDARY_BROKEN")
    if not delivery_and_whitebox_preserved:
        reasons.append("DELIVERY_OR_WHITEBOX_BOUNDARY_BROKEN")
    if not runtime_actions_disabled:
        reasons.append("RUNTIME_SIGNAL_DETECTED")
    if not next_stage_available_but_not_started:
        reasons.append("STAGE090_BOUNDARY_BROKEN")
    return reasons


def _source_authority_closed(source: Mapping[str, Any]) -> bool:
    shared_false = (
        "second_authoritative_source_created",
        "source_body_or_path_allowed",
        "raw_metadata_content_access_allowed",
        "live_source_read_performed",
        "authorized_fixture_access_performed",
        "evidence_ledger_access_performed",
    )
    audit_false = (
        source.get("audit_log_access_performed") is False
        or source.get("report_or_audit_log_access_performed") is False
    )
    return bool(source) and all(source.get(key) is False for key in shared_false) and audit_false


def _runtime_mapping_closed(mapping: Mapping[str, Any]) -> bool:
    return bool(mapping) and all(
        value is False or (key.startswith("actual_") and value == 0)
        for key, value in mapping.items()
    )


def _actual_counts_zero(artifact: Mapping[str, Any]) -> bool:
    values = [
        value
        for key, value in artifact.items()
        if key.startswith("actual_") and key.endswith("_count")
    ]
    return all(value == 0 for value in values)


def _records_references_are_opaque(records: Sequence[Mapping[str, Any]]) -> bool:
    return all(
        isinstance(value, str)
        and (CONTROL_PREFIX in value or DELIVERY_PREFIX in value)
        for record in records
        for field, value in record.items()
        if field.endswith("_ref")
    )


def _record_by_id(
    records: Sequence[Mapping[str, Any]], key: str, expected: str
) -> Mapping[str, Any]:
    return next((record for record in records if record.get(key) == expected), {})


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _load_module(name: str, path: Path) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _provider_result(provider: ArtifactProvider) -> Mapping[str, Any]:
    try:
        return _mapping(provider())
    except Exception:
        return {}


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _records(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence_length(value: Any) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return 0
    return len(value)


def _integer(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
