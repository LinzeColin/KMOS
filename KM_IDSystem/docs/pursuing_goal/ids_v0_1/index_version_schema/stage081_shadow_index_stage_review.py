"""Stage081 的纯内存整阶段机械复审，不读取真实资料或启动 Stage082。"""

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
    / "STAGE-081_影子索引合同.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-082_旧索引保留策略.md"
)
P1_CONTRACT = BASE / "stage081_shadow_index_contract.json"
P2_CONTRACT = BASE / "stage081_shadow_index_slice_contract.json"
P3_CONTRACT = BASE / "stage081_shadow_index_scenarios_contract.json"
P4_CONTRACT = BASE / "stage081_shadow_index_delivery_contract.json"

SCHEMA_VERSION = "ids.stage081.shadow_index.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE081-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-081"
PASS_RESULT = "PASS_REVIEWED_SHADOW_INDEX_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_SHADOW_INDEX_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE081-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE082-P1-GATE"
RETURN_STATE = "PASS_SHADOW_INDEX_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_SHADOW_INDEX_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_SHADOW_INDEX_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_SHADOW_INDEX_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_index_version_field_count": 7,
    "phase1_active_pointer_field_count": 5,
    "phase1_building_and_shadow_field_count": 5,
    "phase1_smoke_input_field_count": 6,
    "phase1_smoke_output_field_count": 5,
    "phase1_rollback_request_field_count": 8,
    "phase1_rollback_proof_field_count": 8,
    "phase1_rollback_condition_count": 5,
    "phase1_failure_state_count": 10,
    "phase2_control_request_count": 5,
    "phase2_index_version_record_count": 5,
    "phase2_building_and_shadow_projection_count": 5,
    "phase2_active_pointer_projection_count": 5,
    "phase2_smoke_input_projection_count": 5,
    "phase2_smoke_output_projection_count": 5,
    "phase2_switch_projection_count": 5,
    "phase2_rollback_request_projection_count": 5,
    "phase2_control_field_check_count": 225,
    "phase2_failure_state_count": 10,
    "phase3_scenario_count": 6,
    "phase3_scenario_field_count": 28,
    "phase3_scenario_field_check_count": 168,
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
    "phase4_failure_state_count": 13,
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

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_shadow_index_stage081_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage081 P1--P4，只输出零运行时结论及后续门禁。"""

    try:
        phase2_module = _load_module("stage081_shadow_index_control_slice.py")
        phase3_module = _load_module("stage081_shadow_index_scenarios.py")
        phase4_module = _load_module("stage081_shadow_index_delivery.py")
    except (ImportError, OSError, RuntimeError):
        return _failed_report()

    phase1 = _provider_value(phase1_contract_provider or _json_provider(P1_CONTRACT))
    phase2 = _provider_value(phase2_contract_provider or _json_provider(P2_CONTRACT))
    phase3 = _provider_value(phase3_contract_provider or _json_provider(P3_CONTRACT))
    phase4 = _provider_value(phase4_contract_provider or _json_provider(P4_CONTRACT))
    phase2_report = _provider_value(
        phase2_report_provider
        or (
            lambda: phase2_module.execute_shadow_index_control_slice(
                phase2_module.build_control_input()
            )
        )
    )
    phase3_report = _provider_value(
        phase3_report_provider or phase3_module.build_shadow_index_phase3_report
    )
    phase4_report = _provider_value(
        phase4_report_provider
        or phase4_module.build_shadow_index_phase4_delivery_report
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2)
        and _phase2_report_valid(phase2_report, phase2_module),
        "P3": _phase3_contract_valid(phase3)
        and _phase3_report_valid(phase3_report, phase3_module),
        "P4": _phase4_contract_valid(phase4)
        and _phase4_report_valid(phase4_report, phase4_module),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2, phase3_report, phase4, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "single_authority_boundary_preserved": _single_authority_boundary(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "fixed_control_shapes_preserved": controlled_replay == EXPECTED_CONTROLLED_REPLAY,
        "failure_stop_and_rollback_boundaries_preserved": _failure_and_rollback_boundary(
            phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
        ),
        "delivery_and_whitebox_boundaries_preserved": _delivery_and_whitebox_boundary(
            phase3_report, phase4, phase4_report
        ),
        "stage082_gate_only_opens_after_review": _future_stage_boundary(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "runtime_actions_disabled": _runtime_closed(
            phase1,
            phase2,
            phase3,
            phase4,
            phase2_report,
            phase3_report,
            phase4_report,
            phase2_module,
            phase3_module,
            phase4_module,
        ),
    }
    return _review_report(phase_results, controlled_replay, invariants)


def _review_report(
    phase_results: Mapping[str, bool],
    controlled_replay: Mapping[str, int],
    invariants: Mapping[str, bool],
) -> dict[str, Any]:
    review_valid = all(invariants.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE081_TASKPACK_AND_STAGE081_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "reviewed_phase_ids": ("P1", "P2", "P3", "P4"),
        "phase_results": dict(phase_results),
        "controlled_replay": dict(controlled_replay),
        "review_invariants": dict(invariants),
        "review_finding_count": 0 if review_valid else 1,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "stage080_review_evidence_read": True,
        "stage081_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": review_valid,
        "batch_review_performed": False,
        "stage082_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "actual_input_request_count": 0,
        "actual_background_build_count": 0,
        "actual_index_build_count": 0,
        "actual_smoke_test_count": 0,
        "actual_retrieval_query_count": 0,
        "actual_index_rollback_count": 0,
        "actual_concurrent_retrieval_count": 0,
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
        **_runtime_closed_flags(),
        "rollback": {
            "return_to": RETURN_STATE,
            "scope": "STAGE081_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
            "preserve_phase1_contract": True,
            "preserve_phase2_control_slice": True,
            "preserve_phase3_controlled_scenarios": True,
            "preserve_phase4_delivery_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "chinese_feedback": _chinese_feedback(review_valid),
    }


def _failed_report() -> dict[str, Any]:
    return _review_report(
        {"P1": False, "P2": False, "P3": False, "P4": False},
        {},
        {
            "frozen_taskpack_available": TASKPACK.is_file(),
            "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
            "all_phase_contracts_and_control_reports_pass": False,
            "single_authority_boundary_preserved": False,
            "fixed_control_shapes_preserved": False,
            "failure_stop_and_rollback_boundaries_preserved": False,
            "delivery_and_whitebox_boundaries_preserved": False,
            "stage082_gate_only_opens_after_review": False,
            "runtime_actions_disabled": False,
        },
    )


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    versions = _mapping(contract.get("index_version_and_active_pointer_contract"))
    building = _mapping(contract.get("building_version_shadow_and_smoke_contract"))
    rollback = _mapping(contract.get("rollback_eligibility_and_service_continuity_contract"))
    return (
        _contract_identity(
            contract,
            "ids.stage081.shadow_index_contract.phase1.v1",
            "IDS-STAGE081-P1",
            "IDS-V0_1-STAGE081-P1",
            "PHASE1_SHADOW_INDEX_CONTRACT_RUNTIME_DISABLED",
            "IDS-STAGE081-P2-GATE",
        )
        and _expected(
            versions,
            {
                "index_version_field_count": 7,
                "active_pointer_field_count": 5,
                "one_active_version_per_index_kind_required": True,
                "reuses_stage080_control_field_shapes_only": True,
                "all_values_are_control_labels_only": True,
                "actual_index_version_record_created": False,
                "actual_active_pointer_read_performed": False,
                "actual_active_pointer_write_performed": False,
            },
        )
        and _expected(
            building,
            {
                "building_and_shadow_field_count": 5,
                "smoke_test_input_field_count": 6,
                "smoke_test_output_field_count": 5,
                "new_candidate_required_after_each_bulk_import": True,
                "candidate_must_not_overwrite_active_version": True,
                "shadow_index_must_remain_isolated_before_smoke_test": True,
                "old_active_index_must_continue_serving_during_build_smoke_switch_and_rollback_preparation": True,
                "actual_bulk_import_detected": False,
                "actual_background_build_started": False,
                "actual_shadow_index_created": False,
                "actual_smoke_test_performed": False,
            },
        )
        and _expected(
            rollback,
            {
                "rollback_request_field_count": 8,
                "rollback_proof_field_count": 8,
                "condition_count": 5,
                "future_index_rollback_required": True,
                "failed_or_missing_smoke_test_blocks_switch": True,
                "active_pointer_must_remain_unchanged_when_build_or_smoke_fails": True,
                "future_rollback_target_must_be_retained_previous_active_index_version": True,
                "actual_index_rollback_performed": False,
            },
        )
        and _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
        == 10
        and _runtime_mapping_closed(contract.get("runtime_boundary"))
        and _expected(
            _mapping(contract.get("stage_and_phase_boundary")),
            {
                "stage081_started": True,
                "phase1_started": True,
                "phase2_started": False,
                "phase3_started": False,
                "phase4_started": False,
                "whole_stage_review_performed": False,
                "stage082_started": False,
                "github_upload_allowed": False,
                "push_allowed": False,
            },
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _mapping(contract.get("reference_only_control_input_contract"))
    projection = _mapping(contract.get("control_projection_contract"))
    continuity = _mapping(contract.get("failure_and_continuity_contract"))
    return (
        _contract_identity(
            contract,
            "ids.stage081.shadow_index.phase2.v1",
            "IDS-STAGE081-P2",
            "IDS-V0_1-STAGE081-P2",
            "PHASE2_SHADOW_INDEX_CONTROL_SLICE_RUNTIME_DISABLED",
            "IDS-STAGE081-P3-GATE",
        )
        and _expected(
            input_contract,
            {
                "control_request_count": 5,
                "input_field_count": 16,
                "all_chunk_counts_are_zero": True,
                "all_references_are_opaque_control_labels": True,
                "actual_source_import_read_performed": False,
                "actual_document_scope_read_performed": False,
                "actual_embedding_model_selected": False,
            },
        )
        and _expected(
            projection,
            {
                "index_version_record_field_count": 7,
                "building_and_shadow_field_count": 5,
                "active_pointer_field_count": 5,
                "smoke_test_input_field_count": 6,
                "smoke_test_output_field_count": 5,
                "switch_projection_field_count": 9,
                "rollback_request_field_count": 8,
                "each_projection_count": 5,
                "actual_index_version_record_created": False,
                "actual_shadow_index_created": False,
                "actual_active_pointer_read_performed": False,
                "actual_active_pointer_write_performed": False,
                "actual_smoke_test_performed": False,
                "actual_switch_record_created": False,
                "actual_rollback_request_created": False,
            },
        )
        and _expected(
            continuity,
            {
                "switch_required_condition_count": 5,
                "rollback_required_condition_count": 5,
                "failure_state_count": 10,
                "failed_or_missing_smoke_test_blocks_switch": True,
                "active_pointer_must_remain_unchanged_when_build_or_smoke_fails": True,
                "old_active_index_must_continue_serving_during_control_projection": True,
                "future_rollback_target_must_be_retained_previous_active_index_version": True,
                "automatic_business_write_allowed": False,
                "automatic_active_pointer_switch_allowed": False,
                "automatic_rollback_allowed": False,
                "business_line_whitebox_human_approval_recorded": False,
                "business_line_whitebox_human_approval_control_label_only": True,
            },
        )
        and _runtime_mapping_closed(contract.get("runtime_boundary"))
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenarios = _mapping(contract.get("scenario_result_contract"))
    views = _mapping(contract.get("control_views"))
    boundary = _mapping(contract.get("stage_boundary"))
    authority = _mapping(contract.get("source_authority"))
    return (
        _contract_identity(
            contract,
            "ids.stage081.shadow_index.phase3.v1",
            "IDS-STAGE081-P3",
            "IDS-V0_1-STAGE081-P3",
            "PHASE3_SHADOW_INDEX_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE081-P4-GATE",
            phase_key="phase_id",
        )
        and contract.get("record_kind") == "CONTROL_ONLY_IN_MEMORY_SHADOW_INDEX_SCENARIOS"
        and contract.get("scenario_executable") is True
        and contract.get("execution_ready") is False
        and _expected(
            replay,
            {
                "required_control_request_count": 5,
                "expected_phase2_field_check_count": 225,
                "actual_input_request_count": 0,
                "all_candidate_versions_are_isolated": True,
                "all_old_active_versions_continue_serving": True,
                "all_active_pointer_projections_unchanged": True,
                "all_rollback_targets_reference_retained_previous_active": True,
            },
        )
        and _expected(
            scenarios,
            {
                "scenario_field_count": 28,
                "silent_drop_allowed": False,
                "human_handling_required": True,
            },
        )
        and _sequence_length(scenarios.get("required_scenarios")) == 6
        and _expected(
            views,
            {
                "operations_version_control_view_count": 5,
                "report_snapshot_version_control_view_count": 5,
                "operations_write_performed": False,
                "report_snapshot_write_performed": False,
                "only_opaque_control_references": True,
            },
        )
        and _expected(
            authority,
            {
                "source_document_remains_authoritative": True,
                "control_scenario_can_replace_source_document": False,
                "control_view_can_become_business_fact_authority": False,
                "automatic_business_recommendation_allowed": False,
                "new_business_fact_source_created": False,
            },
        )
        and _expected(
            boundary,
            {
                "stage081_started": True,
                "phase1_completed": True,
                "phase2_completed": True,
                "phase3_started": True,
                "phase4_started": False,
                "whole_stage_review_performed": False,
                "stage082_started": False,
                "github_upload_allowed": False,
                "push_allowed": False,
            },
        )
        and _runtime_mapping_closed(contract.get("runtime_boundary"))
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        _contract_identity(
            contract,
            "ids.stage081.shadow_index.phase4.delivery.v1",
            "P4",
            "IDS-V0_1-STAGE081-P4",
            "PHASE4_SHADOW_INDEX_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            REVIEW_GATE,
        )
        and _expected(
            delivery,
            {
                "index_manifest_control_sample_count": 5,
                "index_manifest_field_count": 10,
                "smoke_test_log_control_sample_count": 6,
                "smoke_test_log_field_count": 9,
                "switch_record_control_sample_count": 5,
                "switch_record_field_count": 8,
                "rollback_proof_control_sample_count": 5,
                "rollback_proof_field_count": 8,
                "old_index_retention_projection_count": 1,
                "old_index_retention_field_count": 9,
                "operational_instruction_projection_count": 3,
                "operational_instruction_field_count": 8,
                "chinese_feedback_count": 4,
                "actual_index_manifest_written": False,
                "actual_smoke_test_log_written": False,
                "actual_switch_record_written": False,
                "actual_rollback_proof_written": False,
                "actual_old_index_retention_record_written": False,
                "actual_space_impact_measurement_performed": False,
                "actual_operational_instruction_issued": False,
            },
        )
        and _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
        == 13
        and _expected(
            authority,
            {
                "source_document_remains_authoritative": True,
                "business_line_whitebox_human_review_remains_authoritative": True,
                "delivery_control_metadata_can_replace_source_document": False,
                "delivery_control_metadata_can_become_business_fact_authority": False,
                "automatic_business_recommendation_allowed": False,
                "actual_business_decision_created": False,
            },
        )
        and _expected(
            boundary,
            {
                "stage081_phase1_completed": True,
                "stage081_phase2_completed": True,
                "stage081_phase3_completed": True,
                "phase4_started": True,
                "whole_stage_review_performed": False,
                "stage082_started": False,
                "github_upload_allowed": False,
                "push_allowed": False,
            },
        )
        and _runtime_mapping_closed(contract.get("runtime_boundary"))
    )


def _phase2_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    groups = (
        ("index_version_control_records", module.INDEX_VERSION_RECORD_FIELDS),
        ("building_and_shadow_control_projections", module.BUILDING_AND_SHADOW_FIELDS),
        ("active_pointer_control_projections", module.ACTIVE_POINTER_FIELDS),
        ("smoke_test_input_control_projections", module.SMOKE_TEST_INPUT_FIELDS),
        ("smoke_test_output_control_projections", module.SMOKE_TEST_OUTPUT_FIELDS),
        ("switch_control_projections", module.SWITCH_PROJECTION_FIELDS),
        ("rollback_request_control_projections", module.ROLLBACK_REQUEST_FIELDS),
    )
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("expected_control_request_count") == 5
        and report.get("received_control_request_count") == 5
        and report.get("actual_input_request_count") == 0
        and report.get("all_candidate_versions_are_isolated") is True
        and report.get("all_old_active_versions_continue_serving") is True
        and report.get("all_active_pointer_projections_unchanged") is True
        and report.get("all_rollback_targets_reference_retained_previous_active") is True
        and all(_records_have_exact_shape(report.get(key), 5, fields) for key, fields in groups)
        and sum(len(_records(report.get(key))) * len(fields) for key, fields in groups)
        == 225
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase3_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    scenarios = _records(report.get("scenario_results"))
    expected_ids = [item["scenario_id"] for item in module.SCENARIOS]
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE081-P4-GATE"
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_views_preserved") is True
        and report.get("phase2_control_record_field_check_count") == 225
        and report.get("scenario_count") == 6
        and report.get("passed_scenario_count") == 6
        and report.get("scenario_field_count") == 28
        and report.get("scenario_field_check_count") == 168
        and report.get("human_handling_required_count") == 6
        and report.get("operations_version_control_view_count") == 5
        and report.get("report_snapshot_version_control_view_count") == 5
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and _records_have_exact_shape(scenarios, 6, module.SCENARIO_RESULT_FIELDS)
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase4_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    return (
        report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
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
    phase3_report: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int]:
    p1_versions = _mapping(phase1.get("index_version_and_active_pointer_contract"))
    p1_building = _mapping(phase1.get("building_version_shadow_and_smoke_contract"))
    p1_rollback = _mapping(phase1.get("rollback_eligibility_and_service_continuity_contract"))
    p2_input = _mapping(phase2.get("reference_only_control_input_contract"))
    p2_projection = _mapping(phase2.get("control_projection_contract"))
    p2_failures = _mapping(phase2.get("failure_and_continuity_contract"))
    p4_delivery = _mapping(phase4.get("delivery_evidence_contract"))
    return {
        "phase1_index_version_field_count": _int(p1_versions.get("index_version_field_count")),
        "phase1_active_pointer_field_count": _int(p1_versions.get("active_pointer_field_count")),
        "phase1_building_and_shadow_field_count": _int(p1_building.get("building_and_shadow_field_count")),
        "phase1_smoke_input_field_count": _int(p1_building.get("smoke_test_input_field_count")),
        "phase1_smoke_output_field_count": _int(p1_building.get("smoke_test_output_field_count")),
        "phase1_rollback_request_field_count": _int(p1_rollback.get("rollback_request_field_count")),
        "phase1_rollback_proof_field_count": _int(p1_rollback.get("rollback_proof_field_count")),
        "phase1_rollback_condition_count": _int(p1_rollback.get("condition_count")),
        "phase1_failure_state_count": _int(_mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")),
        "phase2_control_request_count": _int(p2_input.get("control_request_count")),
        "phase2_index_version_record_count": _int(p2_projection.get("each_projection_count")),
        "phase2_building_and_shadow_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_active_pointer_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_smoke_input_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_smoke_output_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_switch_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_rollback_request_projection_count": _int(p2_projection.get("each_projection_count")),
        "phase2_control_field_check_count": _int(phase3_report.get("phase2_control_record_field_check_count")),
        "phase2_failure_state_count": _int(p2_failures.get("failure_state_count")),
        "phase3_scenario_count": _int(phase3_report.get("scenario_count")),
        "phase3_scenario_field_count": _int(phase3_report.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _int(phase3_report.get("scenario_field_check_count")),
        "phase3_operations_view_count": _int(phase3_report.get("operations_version_control_view_count")),
        "phase3_report_snapshot_view_count": _int(phase3_report.get("report_snapshot_version_control_view_count")),
        "phase3_human_handling_required_count": _int(phase3_report.get("human_handling_required_count")),
        "phase4_index_manifest_sample_count": _int(phase4_report.get("index_manifest_control_sample_count")),
        "phase4_smoke_log_sample_count": _int(phase4_report.get("smoke_test_log_control_sample_count")),
        "phase4_switch_record_sample_count": _int(phase4_report.get("switch_record_control_sample_count")),
        "phase4_rollback_proof_sample_count": _int(phase4_report.get("rollback_proof_control_sample_count")),
        "phase4_old_index_retention_count": _int(phase4_report.get("old_index_retention_projection_count")),
        "phase4_operational_instruction_count": _int(phase4_report.get("operational_instruction_projection_count")),
        "phase4_chinese_feedback_count": _sequence_length(phase4_report.get("chinese_feedback")),
        "phase4_failure_state_count": _int(_mapping(phase4.get("failure_and_stop_contract")).get("failure_state_count")),
    }


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        _expected(_mapping(phase1.get("source_authority")), {"second_authoritative_source_created": False, "source_body_or_path_allowed": False})
        and _expected(_mapping(phase2.get("source_authority")), {"second_authoritative_source_created": False, "source_body_or_path_allowed": False})
        and _expected(_mapping(phase3.get("source_authority")), {"source_document_remains_authoritative": True, "control_scenario_can_replace_source_document": False, "control_view_can_become_business_fact_authority": False, "new_business_fact_source_created": False})
        and _expected(_mapping(phase4.get("authority_and_decision_boundary")), {"source_document_remains_authoritative": True, "delivery_control_metadata_can_replace_source_document": False, "delivery_control_metadata_can_become_business_fact_authority": False})
        and phase3_report.get("source_document_remains_authoritative") is True
        and phase3_report.get("control_scenario_can_replace_source_document") is False
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("delivery_control_metadata_can_replace_source_document") is False
    )


def _failure_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    p4_rollback = _mapping(phase4.get("rollback_contract"))
    return (
        _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count") == 10
        and _mapping(phase2.get("failure_and_continuity_contract")).get("failure_state_count") == 10
        and _mapping(phase4.get("failure_and_stop_contract")).get("failure_state_count") == 13
        and phase2_report.get("all_active_pointer_projections_unchanged") is True
        and phase2_report.get("all_rollback_targets_reference_retained_previous_active") is True
        and phase3_report.get("build_not_complete_preserved") is True
        and phase3_report.get("smoke_test_failure_preserved") is True
        and phase3_report.get("switch_failure_preserved") is True
        and phase3_report.get("rollback_preserved") is True
        and phase4_report.get("valid") is True
        and p4_rollback.get("return_to") == "PASS_SHADOW_INDEX_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and p4_rollback.get("preserve_phase1_contract") is True
        and p4_rollback.get("preserve_phase2_control_slice") is True
        and p4_rollback.get("preserve_phase3_controlled_scenarios") is True
    )


def _delivery_and_whitebox_boundary(
    phase3_report: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        phase3_report.get("human_handling_required_count") == 6
        and phase3_report.get("operations_version_control_view_count") == 5
        and phase3_report.get("report_snapshot_version_control_view_count") == 5
        and phase4_report.get("all_delivery_references_control_only") is True
        and phase4_report.get("delivery_evidence_metadata_only") is True
        and phase4_report.get("business_line_whitebox_human_review_remains_authoritative") is True
        and _mapping(phase4.get("authority_and_decision_boundary")).get(
            "business_line_whitebox_human_review_remains_authoritative"
        )
        is True
    )


def _future_stage_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        _mapping(phase1.get("stage_and_phase_boundary")).get("stage082_started") is False
        and _mapping(phase2.get("stage_and_phase_boundary")).get("stage082_started") is False
        and _mapping(phase3.get("stage_boundary")).get("stage082_started") is False
        and _mapping(phase4.get("stage_and_phase_boundary")).get("stage082_started") is False
        and phase3_report.get("stage082_started") is False
        and phase4_report.get("stage082_started") is False
        and phase4_report.get("github_upload_allowed") is False
        and phase4_report.get("push_allowed") is False
    )


def _runtime_closed(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
    phase2_module: Any,
    phase3_module: Any,
    phase4_module: Any,
) -> bool:
    return (
        all(
            _runtime_mapping_closed(contract.get("runtime_boundary"))
            for contract in (phase1, phase2, phase3, phase4)
        )
        and all(phase2_report.get(field) is False for field in phase2_module.RUNTIME_CLOSED_FIELDS)
        and all(phase3_report.get(field) is False for field in phase3_module.RUNTIME_CLOSED_FIELDS)
        and all(phase4_report.get(field) is False for field in phase4_module.RUNTIME_CLOSED_FIELDS)
        and all(_actual_counts_are_zero(report) for report in (phase2_report, phase3_report, phase4_report))
    )


def _contract_identity(
    contract: Mapping[str, Any],
    schema_version: str,
    phase: str,
    task_id: str,
    state: str,
    next_gate: str,
    *,
    phase_key: str = "phase",
) -> bool:
    return (
        contract.get("schema_version") == schema_version
        and contract.get(phase_key) == phase
        and contract.get("task_id") == task_id
        and contract.get("contract_state") == state
        and contract.get("next_gate") == next_gate
    )


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_module(filename: str) -> Any:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_value(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        return _mapping(provider())
    except (KeyError, OSError, TypeError, ValueError):
        return {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence_length(value: object) -> int:
    return len(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else 0


def _records_have_exact_shape(
    value: object, expected_count: int, fields: Sequence[str]
) -> bool:
    records = _records(value)
    return len(records) == expected_count and all(set(record) == set(fields) for record in records)


def _expected(mapping: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(mapping.get(key) == value for key, value in expected.items())


def _runtime_mapping_closed(value: object) -> bool:
    mapping = _mapping(value)
    return bool(mapping) and all(
        (item is False if isinstance(item, bool) else item == 0 if isinstance(item, int) else False)
        for item in mapping.values()
    )


def _actual_counts_are_zero(report: Mapping[str, Any]) -> bool:
    return all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _chinese_feedback(review_valid: bool) -> list[str]:
    if review_valid:
        return [
            "Stage081 P1--P4 控制工件已在本地机械复审，未构建或切换实际索引。",
            "候选构建未完成、影子冒烟失败或切换失败均保持旧活动版本连续服务。",
            "索引清单、冒烟日志、切换记录和回滚证明均为未写入的控制投影。",
            "Stage082 仅开放后续门禁，仍须业务线白箱人工处理和新的独立 run。",
        ]
    return [
        "Stage081 Review 未通过，保持在 Review Gate，不启动 Stage082。",
        "任一控制形状、回退、单一权威或零运行时边界不一致均失败关闭。",
    ]
