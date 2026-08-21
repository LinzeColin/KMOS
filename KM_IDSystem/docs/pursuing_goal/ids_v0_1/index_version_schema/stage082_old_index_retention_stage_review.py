"""Stage082 的纯内存整阶段机械复审，不读取真实资料或启动 Stage083。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-082_旧索引保留策略.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-083_关键词检索基线.md"
)
P1_CONTRACT = BASE / "stage082_old_index_retention_contract.json"
P2_CONTRACT = BASE / "stage082_old_index_retention_slice_contract.json"
P3_CONTRACT = BASE / "stage082_old_index_retention_scenarios_contract.json"
P4_CONTRACT = BASE / "stage082_old_index_retention_delivery_contract.json"

SCHEMA_VERSION = "ids.stage082.old_index_retention.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE082-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-082"
PASS_RESULT = "PASS_REVIEWED_OLD_INDEX_RETENTION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_OLD_INDEX_RETENTION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE082-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE083-P1-GATE"
RETURN_STATE = "PASS_OLD_INDEX_RETENTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_OLD_INDEX_RETENTION_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_OLD_INDEX_RETENTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_index_version_field_count": 7,
    "phase1_active_pointer_field_count": 5,
    "phase1_building_and_shadow_field_count": 5,
    "phase1_smoke_input_field_count": 6,
    "phase1_smoke_output_field_count": 5,
    "phase1_retention_policy_field_count": 10,
    "phase1_cleanup_eligibility_field_count": 6,
    "phase1_failure_state_count": 14,
    "phase2_control_request_count": 5,
    "phase2_index_version_record_count": 5,
    "phase2_building_and_shadow_projection_count": 5,
    "phase2_active_pointer_projection_count": 5,
    "phase2_smoke_input_projection_count": 5,
    "phase2_smoke_output_projection_count": 5,
    "phase2_switch_projection_count": 5,
    "phase2_rollback_request_projection_count": 5,
    "phase2_retention_policy_projection_count": 5,
    "phase2_cleanup_eligibility_projection_count": 5,
    "phase2_control_field_check_count": 305,
    "phase3_scenario_count": 6,
    "phase3_scenario_field_count": 31,
    "phase3_scenario_field_check_count": 186,
    "phase3_operations_view_count": 5,
    "phase3_report_snapshot_view_count": 5,
    "phase3_human_handling_required_count": 6,
    "phase4_index_manifest_sample_count": 5,
    "phase4_smoke_log_sample_count": 6,
    "phase4_switch_record_sample_count": 5,
    "phase4_rollback_proof_sample_count": 5,
    "phase4_old_index_retention_count": 1,
    "phase4_operational_instruction_count": 3,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 15,
}

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "background_build_execution_performed",
    "index_build_execution_performed",
    "shadow_index_build_performed",
    "smoke_test_execution_performed",
    "active_pointer_read_performed",
    "active_pointer_switch_performed",
    "retrieval_query_performed",
    "concurrent_retrieval_performed",
    "index_rollback_execution_performed",
    "old_index_cleanup_performed",
    "space_measurement_performed",
    "actual_operations_display_written",
    "actual_report_snapshot_written",
    "actual_index_manifest_written",
    "actual_smoke_test_log_written",
    "actual_switch_record_written",
    "actual_rollback_proof_written",
    "actual_old_index_retention_record_written",
    "actual_space_impact_measurement_performed",
    "actual_operational_instruction_issued",
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
)

P2_RECORD_SHAPES = {
    "index_version_control_records": (
        "index_version",
        "index_kind",
        "lifecycle_state",
        "document_scope_ref",
        "chunk_count",
        "embedding_model_ref",
        "source_import_ref",
    ),
    "building_and_shadow_control_projections": (
        "building_index_version_ref",
        "candidate_index_version_ref",
        "shadow_index_ref",
        "source_import_ref",
        "build_state",
    ),
    "active_pointer_control_projections": (
        "index_kind",
        "active_index_version_ref",
        "previous_active_index_version_ref",
        "pointer_state",
        "switch_record_ref",
    ),
    "smoke_test_input_control_projections": (
        "candidate_index_version_ref",
        "active_index_version_ref",
        "document_scope_ref",
        "chunk_count",
        "embedding_model_ref",
        "shadow_index_ref",
    ),
    "smoke_test_output_control_projections": (
        "smoke_test_ref",
        "smoke_test_status",
        "failure_reason_ref",
        "tested_at_ref",
        "switch_eligibility",
    ),
    "switch_control_projections": (
        "control_scenario",
        "index_kind",
        "candidate_index_version_ref",
        "active_index_version_ref",
        "switch_eligible",
        "switch_applied",
        "switch_outcome",
        "resulting_active_index_version_ref",
        "switch_record_ref",
    ),
    "rollback_request_control_projections": (
        "index_kind",
        "current_active_index_version_ref",
        "previous_active_index_version_ref",
        "rollback_request_ref",
        "rollback_reason_ref",
        "retention_window_state",
        "rollback_eligibility",
        "rollback_applied",
    ),
    "retention_policy_control_projections": (
        "retention_policy_ref",
        "index_kind",
        "active_index_version_ref",
        "previous_active_index_version_ref",
        "minimum_retained_previous_active_version_count",
        "additional_retained_version_count_requirement_ref",
        "rollback_window_requirement_ref",
        "cleanup_timing_requirement_ref",
        "business_line_whitebox_approval_ref",
        "policy_state",
    ),
    "cleanup_eligibility_control_projections": (
        "retention_policy_ref",
        "previous_active_index_version_ref",
        "rollback_window_state",
        "cleanup_timing_state",
        "business_line_whitebox_approval_state",
        "cleanup_eligibility",
    ),
}


def build_old_index_retention_stage082_review_report(
    *,
    phase1_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_report_provider: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recheck only frozen control artifacts and return a fail-closed report."""
    phase1 = _provider_result(phase1_contract_provider or _default_phase1_contract_provider)
    phase2_contract = _provider_result(phase2_contract_provider or _default_phase2_contract_provider)
    phase3_contract = _provider_result(phase3_contract_provider or _default_phase3_contract_provider)
    phase4_contract = _provider_result(phase4_contract_provider or _default_phase4_contract_provider)
    phase2_module = _load_module("stage082_review_phase2", "stage082_old_index_retention_control_slice.py")
    phase3_module = _load_module("stage082_review_phase3", "stage082_old_index_retention_scenarios.py")
    phase4_module = _load_module("stage082_review_phase4", "stage082_old_index_retention_delivery.py")
    phase2 = _provider_result(phase2_report_provider or _default_phase2_report_provider)
    phase3 = _provider_result(phase3_report_provider or _default_phase3_report_provider)
    phase4 = _provider_result(phase4_report_provider or _default_phase4_report_provider)

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2_contract)
        and _phase2_report_valid(phase2_module, phase2),
        "P3": _phase3_contract_valid(phase3_contract)
        and _phase3_report_valid(phase3_module, phase3),
        "P4": _phase4_contract_valid(phase4_contract)
        and _phase4_report_valid(phase4_module, phase4),
    }
    controlled_replay = _controlled_replay(phase1, phase2, phase3, phase4_contract, phase4)
    fixed_shapes = controlled_replay == EXPECTED_CONTROLLED_REPLAY
    all_phases_pass = all(phase_results.values())
    authority_preserved = _single_authority_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    failure_and_rollback_preserved = _failure_and_rollback_boundary(
        phase1, phase2, phase3, phase4_contract, phase4
    )
    delivery_and_whitebox_preserved = _delivery_and_whitebox_boundary(phase3, phase4_contract, phase4)
    nested_runtime_closed = _nested_runtime_closed(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase2, phase3, phase4
    )
    next_stage_available_but_not_started = (
        NEXT_TASKPACK.is_file()
        and phase1.get("stage_and_phase_boundary", {}).get("stage083_started") is False
        and phase3.get("stage083_started") is False
        and phase4.get("stage083_started") is False
    )
    runtime_flags = _runtime_closed_flags()
    review_valid = (
        TASKPACK.is_file()
        and all_phases_pass
        and fixed_shapes
        and authority_preserved
        and failure_and_rollback_preserved
        and delivery_and_whitebox_preserved
        and nested_runtime_closed
        and next_stage_available_but_not_started
        and all(value is False for value in runtime_flags.values())
    )
    next_gate = NEXT_GATE if review_valid else REVIEW_GATE
    review_invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all_phases_pass,
        "fixed_control_shapes_preserved": fixed_shapes,
        "single_authority_boundary_preserved": authority_preserved,
        "failure_stop_and_rollback_boundaries_preserved": failure_and_rollback_preserved,
        "delivery_and_whitebox_boundaries_preserved": delivery_and_whitebox_preserved,
        "runtime_actions_disabled": nested_runtime_closed
        and all(value is False for value in runtime_flags.values()),
        "next_stage_taskpack_available_but_not_started": next_stage_available_but_not_started,
        "stage083_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE082_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "reviewed_phase_ids": [
            "IDS-STAGE082-P1",
            "IDS-STAGE082-P2",
            "IDS-STAGE082-P3",
            "IDS-STAGE082-P4",
        ],
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": review_invariants,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": next_gate,
        "source_document_remains_authoritative": authority_preserved,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "business_line_whitebox_human_review_remains_authoritative": (
            _mapping(phase4_contract.get("authority_and_decision_boundary")).get(
                "business_line_whitebox_human_review_remains_authoritative"
            )
            is True
        ),
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "stage082_started": True,
        "stage083_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "automatic_business_recommendation_allowed": False,
        "actual_input_request_count": 0,
        "actual_background_build_count": 0,
        "actual_index_build_count": 0,
        "actual_smoke_test_count": 0,
        "actual_retrieval_query_count": 0,
        "actual_concurrent_retrieval_count": 0,
        "actual_index_rollback_count": 0,
        "actual_old_index_cleanup_count": 0,
        "actual_operations_display_count": 0,
        "actual_report_snapshot_count": 0,
        "actual_index_manifest_count": 0,
        "actual_smoke_test_log_count": 0,
        "actual_switch_record_count": 0,
        "actual_rollback_proof_count": 0,
        "actual_old_index_retention_record_count": 0,
        "actual_space_impact_measurement_count": 0,
        "actual_operational_instruction_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "rollback": {
            "scope": "STAGE082_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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


def _default_phase1_contract_provider() -> Mapping[str, Any]:
    return _read_json(P1_CONTRACT)


def _default_phase2_contract_provider() -> Mapping[str, Any]:
    return _read_json(P2_CONTRACT)


def _default_phase3_contract_provider() -> Mapping[str, Any]:
    return _read_json(P3_CONTRACT)


def _default_phase4_contract_provider() -> Mapping[str, Any]:
    return _read_json(P4_CONTRACT)


def _default_phase2_report_provider() -> Mapping[str, Any]:
    module = _load_module("stage082_review_phase2_provider", "stage082_old_index_retention_control_slice.py")
    if module is None:
        return {}
    return module.execute_old_index_retention_control_slice(module.build_control_input())


def _default_phase3_report_provider() -> Mapping[str, Any]:
    module = _load_module("stage082_review_phase3_provider", "stage082_old_index_retention_scenarios.py")
    if module is None:
        return {}
    return module.build_old_index_retention_phase3_report()


def _default_phase4_report_provider() -> Mapping[str, Any]:
    module = _load_module("stage082_review_phase4_provider", "stage082_old_index_retention_delivery.py")
    if module is None:
        return {}
    return module.build_old_index_retention_phase4_delivery_report()


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    fields = _mapping(contract.get("index_version_active_pointer_build_and_smoke_contract"))
    retention = _mapping(contract.get("old_index_retention_cleanup_and_rollback_window_contract"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    authority = _mapping(contract.get("source_authority"))
    runtime = _mapping(contract.get("runtime_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    rollback = _mapping(contract.get("rollback_contract"))
    return (
        contract.get("schema_version") == "ids.stage082.old_index_retention_contract.phase1.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE082-P1"
        and contract.get("stage") == "STAGE-082"
        and contract.get("phase") == "IDS-STAGE082-P1"
        and contract.get("next_gate") == "IDS-STAGE082-P2-GATE"
        and fields.get("index_version_field_count") == 7
        and fields.get("active_pointer_field_count") == 5
        and fields.get("building_and_shadow_field_count") == 5
        and fields.get("smoke_test_input_field_count") == 6
        and fields.get("smoke_test_output_field_count") == 5
        and fields.get("old_active_index_must_continue_serving_during_build_smoke_switch_rollback_and_retention_confirmation")
        is True
        and retention.get("retention_policy_field_count") == 10
        and retention.get("cleanup_eligibility_field_count") == 6
        and retention.get("minimum_retained_previous_active_version_count") == 1
        and retention.get("unconfigured_policy_values_fail_closed") is True
        and failures.get("failure_state_count") == 14
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and _runtime_boundary_closed(runtime)
        and boundary.get("stage082_started") is True
        and boundary.get("stage083_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and rollback.get("return_to") == "PASS_REVIEWED_SHADOW_INDEX_RUNTIME_DISABLED"
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    projection = _mapping(contract.get("control_projection_contract"))
    inputs = _mapping(contract.get("reference_only_control_input_contract"))
    authority = _mapping(contract.get("source_authority"))
    runtime = _mapping(contract.get("runtime_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("schema_version") == "ids.stage082.old_index_retention.phase2.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE082-P2"
        and contract.get("stage") == "STAGE-082"
        and contract.get("phase") == "IDS-STAGE082-P2"
        and contract.get("next_gate") == "IDS-STAGE082-P3-GATE"
        and inputs.get("control_request_count") == 5
        and inputs.get("input_field_count") == 20
        and inputs.get("all_references_are_opaque_control_labels") is True
        and inputs.get("all_chunk_counts_are_zero") is True
        and inputs.get("all_minimum_retained_previous_active_version_counts_are_one") is True
        and projection.get("each_projection_count") == 5
        and projection.get("index_version_record_field_count") == 7
        and projection.get("building_and_shadow_field_count") == 5
        and projection.get("active_pointer_field_count") == 5
        and projection.get("smoke_test_input_field_count") == 6
        and projection.get("smoke_test_output_field_count") == 5
        and projection.get("switch_projection_field_count") == 9
        and projection.get("rollback_request_field_count") == 8
        and projection.get("retention_policy_field_count") == 10
        and projection.get("cleanup_eligibility_field_count") == 6
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and _runtime_boundary_closed(runtime)
        and boundary.get("stage082_phase1_completed") is True
        and boundary.get("stage082_phase2_started") is True
        and boundary.get("stage083_started") is False
        and boundary.get("whole_stage_review_performed") is False
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenarios = _mapping(contract.get("scenario_result_contract"))
    authority = _mapping(contract.get("source_authority"))
    runtime = _mapping(contract.get("runtime_boundary"))
    boundary = _mapping(contract.get("stage_boundary"))
    return (
        contract.get("schema_version") == "ids.stage082.old_index_retention.phase3.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE082-P3"
        and contract.get("stage") == "STAGE-082"
        and contract.get("phase") == "IDS-STAGE082-P3"
        and contract.get("next_gate") == "IDS-STAGE082-P4-GATE"
        and replay.get("required_control_request_count") == 5
        and replay.get("expected_phase2_field_check_count") == 305
        and scenarios.get("scenario_field_count") == 31
        and _sequence_length(scenarios.get("required_scenarios")) == 6
        and scenarios.get("silent_drop_allowed") is False
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("control_scenario_can_replace_source_document") is False
        and authority.get("control_view_can_become_business_fact_authority") is False
        and authority.get("new_business_fact_source_created") is False
        and _runtime_boundary_closed(runtime)
        and boundary.get("stage082_started") is True
        and boundary.get("stage083_started") is False
        and boundary.get("whole_stage_review_performed") is False
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    phase2 = _mapping(contract.get("phase2_control_slice_replay_contract"))
    phase3 = _mapping(contract.get("phase3_controlled_scenario_replay_contract"))
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    runtime = _mapping(contract.get("runtime_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    rollback = _mapping(contract.get("rollback_contract"))
    return (
        contract.get("schema_version") == "ids.stage082.old_index_retention.phase4.delivery.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE082-P4"
        and contract.get("stage") == "STAGE-082"
        and contract.get("phase") == "P4"
        and contract.get("next_gate") == REVIEW_GATE
        and phase2.get("control_request_count") == 5
        and phase2.get("phase2_control_field_check_count") == 305
        and phase3.get("scenario_count") == 6
        and phase3.get("scenario_field_count") == 31
        and phase3.get("scenario_field_check_count") == 186
        and delivery.get("index_manifest_control_sample_count") == 5
        and delivery.get("smoke_test_log_control_sample_count") == 6
        and delivery.get("switch_record_control_sample_count") == 5
        and delivery.get("rollback_proof_control_sample_count") == 5
        and delivery.get("old_index_retention_projection_count") == 1
        and delivery.get("operational_instruction_projection_count") == 3
        and delivery.get("chinese_feedback_count") == 4
        and failures.get("failure_state_count") == 15
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("delivery_control_metadata_can_replace_source_document") is False
        and authority.get("delivery_control_metadata_can_become_business_fact_authority") is False
        and authority.get("business_line_whitebox_human_review_remains_authoritative") is True
        and _runtime_boundary_closed(runtime)
        and boundary.get("stage083_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and rollback.get("return_to") == P3_PASS_RESULT
    )


def _phase2_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    counts = {
        "received_control_request_count": 5,
        "expected_control_request_count": 5,
        "index_version_control_record_count": 5,
        "building_and_shadow_control_projection_count": 5,
        "active_pointer_control_projection_count": 5,
        "smoke_test_input_control_projection_count": 5,
        "smoke_test_output_control_projection_count": 5,
        "switch_control_projection_count": 5,
        "rollback_request_control_projection_count": 5,
        "retention_policy_control_projection_count": 5,
        "cleanup_eligibility_control_projection_count": 5,
    }
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and all(report.get(key) == value for key, value in counts.items())
        and all(_records_have_exact_shape(report.get(key), 5, shape) for key, shape in P2_RECORD_SHAPES.items())
        and report.get("all_candidate_versions_are_isolated") is True
        and report.get("all_active_pointer_projections_unchanged") is True
        and report.get("all_old_active_versions_continue_serving") is True
        and report.get("all_minimum_previous_active_versions_retained") is True
        and report.get("all_rollback_targets_reference_retained_previous_active") is True
        and report.get("all_cleanup_projections_fail_closed") is True
        and report.get("automatic_active_pointer_switch_allowed") is False
        and report.get("automatic_rollback_allowed") is False
        and report.get("automatic_old_index_cleanup_allowed") is False
        and report.get("automatic_business_write_allowed") is False
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase3_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    expected_ids = [
        "build_not_complete_old_active_continues",
        "smoke_test_failure_blocks_switch",
        "switch_failure_preserves_active",
        "rollback_window_unconfigured_preserves_previous_active",
        "background_build_concurrent_retrieval_isolated",
        "operations_and_report_snapshot_version_visibility",
    ]
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE082-P4-GATE"
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("phase2_control_record_field_check_count") == 305
        and report.get("scenario_count") == 6
        and report.get("passed_scenario_count") == 6
        and report.get("scenario_field_count") == 31
        and report.get("scenario_field_check_count") == 186
        and report.get("human_handling_required_count") == 6
        and report.get("operations_version_control_view_count") == 5
        and report.get("report_snapshot_version_control_view_count") == 5
        and [item.get("scenario_id") for item in _sequence(report.get("scenario_results"))] == expected_ids
        and _records_have_exact_shape(
            report.get("scenario_results"), 6, module.SCENARIO_RESULT_FIELDS
        )
        and all(item.get("expectation_met") is True for item in _sequence(report.get("scenario_results")))
        and report.get("build_not_complete_preserved") is True
        and report.get("smoke_test_failure_preserved") is True
        and report.get("switch_failure_preserved") is True
        and report.get("rollback_window_unconfigured_preserved") is True
        and report.get("concurrent_retrieval_isolation_preserved") is True
        and report.get("operations_and_report_snapshot_visibility_preserved") is True
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase4_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    return (
        report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_completed") is True
        and report.get("phase2_control_slice_report_valid") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("all_delivery_references_control_only") is True
        and report.get("index_manifest_control_sample_count") == 5
        and report.get("smoke_test_log_control_sample_count") == 6
        and report.get("switch_record_control_sample_count") == 5
        and report.get("rollback_proof_control_sample_count") == 5
        and report.get("old_index_retention_projection_count") == 1
        and report.get("operational_instruction_projection_count") == 3
        and _sequence_length(report.get("chinese_feedback")) == 4
        and _records_have_exact_shape(
            report.get("index_manifest_control_samples"), 5, module.INDEX_MANIFEST_FIELDS
        )
        and _records_have_exact_shape(
            report.get("smoke_test_log_control_samples"), 6, module.SMOKE_TEST_LOG_FIELDS
        )
        and _records_have_exact_shape(
            report.get("switch_record_control_samples"), 5, module.SWITCH_RECORD_FIELDS
        )
        and _records_have_exact_shape(
            report.get("rollback_proof_control_samples"), 5, module.ROLLBACK_PROOF_FIELDS
        )
        and set(_mapping(report.get("old_index_retention_projection")))
        == set(module.OLD_INDEX_RETENTION_FIELDS)
        and _records_have_exact_shape(
            report.get("operational_instruction_projections"),
            3,
            module.OPERATIONAL_INSTRUCTION_FIELDS,
        )
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> dict[str, int]:
    p1 = _mapping(phase1.get("index_version_active_pointer_build_and_smoke_contract"))
    retention = _mapping(phase1.get("old_index_retention_cleanup_and_rollback_window_contract"))
    failures = _mapping(phase1.get("failure_and_stop_contract"))
    p4_failures = _mapping(phase4_contract.get("failure_and_stop_contract"))
    return {
        "phase1_index_version_field_count": _integer(p1.get("index_version_field_count")),
        "phase1_active_pointer_field_count": _integer(p1.get("active_pointer_field_count")),
        "phase1_building_and_shadow_field_count": _integer(p1.get("building_and_shadow_field_count")),
        "phase1_smoke_input_field_count": _integer(p1.get("smoke_test_input_field_count")),
        "phase1_smoke_output_field_count": _integer(p1.get("smoke_test_output_field_count")),
        "phase1_retention_policy_field_count": _integer(retention.get("retention_policy_field_count")),
        "phase1_cleanup_eligibility_field_count": _integer(retention.get("cleanup_eligibility_field_count")),
        "phase1_failure_state_count": _integer(failures.get("failure_state_count")),
        "phase2_control_request_count": _integer(phase2.get("received_control_request_count")),
        "phase2_index_version_record_count": _integer(phase2.get("index_version_control_record_count")),
        "phase2_building_and_shadow_projection_count": _integer(phase2.get("building_and_shadow_control_projection_count")),
        "phase2_active_pointer_projection_count": _integer(phase2.get("active_pointer_control_projection_count")),
        "phase2_smoke_input_projection_count": _integer(phase2.get("smoke_test_input_control_projection_count")),
        "phase2_smoke_output_projection_count": _integer(phase2.get("smoke_test_output_control_projection_count")),
        "phase2_switch_projection_count": _integer(phase2.get("switch_control_projection_count")),
        "phase2_rollback_request_projection_count": _integer(phase2.get("rollback_request_control_projection_count")),
        "phase2_retention_policy_projection_count": _integer(phase2.get("retention_policy_control_projection_count")),
        "phase2_cleanup_eligibility_projection_count": _integer(phase2.get("cleanup_eligibility_control_projection_count")),
        "phase2_control_field_check_count": _integer(phase3.get("phase2_control_record_field_check_count")),
        "phase3_scenario_count": _integer(phase3.get("scenario_count")),
        "phase3_scenario_field_count": _integer(phase3.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _integer(phase3.get("scenario_field_check_count")),
        "phase3_operations_view_count": _integer(phase3.get("operations_version_control_view_count")),
        "phase3_report_snapshot_view_count": _integer(phase3.get("report_snapshot_version_control_view_count")),
        "phase3_human_handling_required_count": _integer(phase3.get("human_handling_required_count")),
        "phase4_index_manifest_sample_count": _integer(phase4.get("index_manifest_control_sample_count")),
        "phase4_smoke_log_sample_count": _integer(phase4.get("smoke_test_log_control_sample_count")),
        "phase4_switch_record_sample_count": _integer(phase4.get("switch_record_control_sample_count")),
        "phase4_rollback_proof_sample_count": _integer(phase4.get("rollback_proof_control_sample_count")),
        "phase4_old_index_retention_count": _integer(phase4.get("old_index_retention_projection_count")),
        "phase4_operational_instruction_count": _integer(phase4.get("operational_instruction_projection_count")),
        "phase4_chinese_feedback_count": _sequence_length(phase4.get("chinese_feedback")),
        "phase4_failure_state_count": _integer(p4_failures.get("failure_state_count")),
    }


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        _mapping(phase1.get("source_authority")).get("second_authoritative_source_created") is False
        and _mapping(phase1.get("source_authority")).get("source_body_or_path_allowed") is False
        and _mapping(phase2_contract.get("source_authority")).get("second_authoritative_source_created") is False
        and _mapping(phase2_contract.get("source_authority")).get("source_body_or_path_allowed") is False
        and _mapping(phase3_contract.get("source_authority")).get("source_document_remains_authoritative") is True
        and _mapping(phase3_contract.get("source_authority")).get("control_scenario_can_replace_source_document") is False
        and _mapping(phase3_contract.get("source_authority")).get("control_view_can_become_business_fact_authority") is False
        and _mapping(phase3_contract.get("source_authority")).get("new_business_fact_source_created") is False
        and _mapping(phase4_contract.get("authority_and_decision_boundary")).get(
            "source_document_remains_authoritative"
        )
        is True
        and _mapping(phase4_contract.get("authority_and_decision_boundary")).get(
            "delivery_control_metadata_can_replace_source_document"
        )
        is False
        and phase3.get("source_document_remains_authoritative") is True
        and phase3.get("control_scenario_can_replace_source_document") is False
        and phase4.get("source_document_remains_authoritative") is True
        and phase4.get("delivery_control_metadata_can_replace_source_document") is False
    )


def _failure_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    p1_retention = _mapping(phase1.get("old_index_retention_cleanup_and_rollback_window_contract"))
    p4_rollback = _mapping(phase4_contract.get("rollback_contract"))
    return (
        _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count") == 14
        and p1_retention.get("minimum_retained_previous_active_version_count") == 1
        and p1_retention.get("unconfigured_policy_values_fail_closed") is True
        and phase2.get("all_old_active_versions_continue_serving") is True
        and phase2.get("all_minimum_previous_active_versions_retained") is True
        and phase2.get("all_cleanup_projections_fail_closed") is True
        and phase3.get("build_not_complete_preserved") is True
        and phase3.get("smoke_test_failure_preserved") is True
        and phase3.get("switch_failure_preserved") is True
        and phase3.get("rollback_window_unconfigured_preserved") is True
        and _mapping(phase4_contract.get("failure_and_stop_contract")).get("failure_state_count") == 15
        and phase4.get("old_index_retention_projection_count") == 1
        and p4_rollback.get("return_to") == P3_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_report_valid") is True
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any], phase4_contract: Mapping[str, Any], phase4: Mapping[str, Any]
) -> bool:
    authority = _mapping(phase4_contract.get("authority_and_decision_boundary"))
    return (
        phase3.get("human_handling_required_count") == 6
        and phase4.get("delivery_evidence_metadata_only") is True
        and phase4.get("all_delivery_references_control_only") is True
        and phase4.get("business_line_whitebox_human_review_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative") is True
        and authority.get("automatic_business_recommendation_allowed") is False
    )


def _nested_runtime_closed(*items: Mapping[str, Any]) -> bool:
    for item in items:
        for field, value in item.items():
            if field.endswith("_performed") or field.endswith("_written") or field.endswith("_issued"):
                if value is not False:
                    return False
            if field.startswith("actual_") and field.endswith("_count") and value != 0:
                return False
        runtime = _mapping(item.get("runtime_boundary"))
        if runtime and not _runtime_boundary_closed(runtime):
            return False
    return True


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _load_module(module_name: str, file_name: str) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location(module_name, BASE / file_name)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError, SyntaxError, ValueError):
        return None


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        result = provider()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}
    return result if isinstance(result, Mapping) else {}


def _read_json(path: Path) -> Mapping[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, Mapping) else {}


def _records_have_exact_shape(value: object, count: int, fields: Sequence[str]) -> bool:
    records = _sequence(value)
    return len(records) == count and all(
        isinstance(record, Mapping) and set(record) == set(fields) for record in records
    )


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence_length(value: object) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return 0
    return len(value)


def _all_false(mapping: Mapping[str, Any], fields: Sequence[str] | Any) -> bool:
    return all(mapping.get(field) is False for field in fields)


def _runtime_boundary_closed(mapping: Mapping[str, Any]) -> bool:
    return all(
        value == 0 if key.startswith("actual_") and key.endswith("_count") else value is False
        for key, value in mapping.items()
    )


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1
