"""Stage078 的纯内存整阶段机械复审，不读取真实资料或启动 Stage079。"""

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
    / "STAGE-078_索引冒烟测试.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-079_索引原子切换.md"
)
P1_CONTRACT = BASE / "stage078_index_smoke_test_contract.json"
P2_CONTRACT = BASE / "stage078_index_smoke_test_slice_contract.json"
P3_CONTRACT = BASE / "stage078_index_smoke_test_scenarios_contract.json"
P4_CONTRACT = BASE / "stage078_index_smoke_test_delivery_contract.json"

SCHEMA_VERSION = "ids.stage078.index_smoke_test.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE078-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-078"
PASS_RESULT = "PASS_REVIEWED_INDEX_SMOKE_TEST_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_INDEX_SMOKE_TEST_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE078-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE079-P1-GATE"
RETURN_STATE = "PASS_INDEX_SMOKE_TEST_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_INDEX_SMOKE_TEST_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_INDEX_SMOKE_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = RETURN_STATE

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_index_version_field_count": 7,
    "phase1_active_pointer_field_count": 5,
    "phase1_building_version_field_count": 5,
    "phase1_smoke_input_field_count": 6,
    "phase1_smoke_output_field_count": 5,
    "phase1_switch_condition_count": 5,
    "phase1_failure_state_count": 9,
    "phase2_control_request_count": 5,
    "phase2_index_version_record_count": 5,
    "phase2_candidate_build_projection_count": 5,
    "phase2_active_pointer_projection_count": 5,
    "phase2_smoke_test_projection_count": 5,
    "phase2_switch_projection_count": 5,
    "phase2_rollback_projection_count": 5,
    "phase2_control_field_check_count": 250,
    "phase2_failure_state_count": 7,
    "phase3_scenario_count": 6,
    "phase3_scenario_field_count": 26,
    "phase3_scenario_field_check_count": 156,
    "phase3_operations_view_count": 5,
    "phase3_report_snapshot_view_count": 5,
    "phase3_human_handling_required_count": 6,
    "phase3_failure_state_count": 13,
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
    "authorized_fixture_access_performed",
    "actual_index_version_record_created",
    "actual_document_scope_recorded",
    "actual_chunk_count_recorded",
    "actual_embedding_model_recorded",
    "actual_bulk_import_detected",
    "actual_background_build_started",
    "actual_index_build_started",
    "actual_candidate_build_record_created",
    "actual_shadow_index_created",
    "actual_shadow_index_queried",
    "actual_smoke_test_performed",
    "actual_smoke_test_result_recorded",
    "actual_active_pointer_read_performed",
    "actual_active_pointer_write_performed",
    "actual_switch_record_created",
    "actual_retrieval_query_performed",
    "actual_concurrent_retrieval_performed",
    "actual_rollback_record_created",
    "actual_rollback_execution_performed",
    "actual_operations_display_written",
    "actual_report_snapshot_written",
    "actual_index_manifest_written",
    "actual_smoke_test_log_written",
    "actual_switch_record_written",
    "actual_rollback_proof_written",
    "actual_old_index_retention_record_written",
    "actual_space_impact_measurement_performed",
    "actual_operational_instruction_issued",
    "database_schema_migration_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
    "external_api_call_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_index_smoke_test_stage078_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage078 P1--P4，只输出零运行时结论及后续门禁。"""

    try:
        phase2_module = _load_module("stage078_index_smoke_test_slice.py")
        phase3_module = _load_module("stage078_index_smoke_test_scenarios.py")
        phase4_module = _load_module("stage078_index_smoke_test_delivery.py")
    except Exception:
        return _failed_report()

    phase1 = _provider_value(phase1_contract_provider or _json_provider(P1_CONTRACT))
    phase2 = _provider_value(phase2_contract_provider or _json_provider(P2_CONTRACT))
    phase3 = _provider_value(phase3_contract_provider or _json_provider(P3_CONTRACT))
    phase4 = _provider_value(phase4_contract_provider or _json_provider(P4_CONTRACT))
    phase2_report = _provider_value(
        phase2_report_provider
        or (
            lambda: phase2_module.execute_index_smoke_test_control_slice(
                phase2_module.build_control_input()
            )
        )
    )
    phase3_report = _provider_value(
        phase3_report_provider or phase3_module.build_index_smoke_test_phase3_report
    )
    phase4_report = _provider_value(
        phase4_report_provider
        or phase4_module.build_index_smoke_test_phase4_delivery_report
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
        phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "single_authority_boundary_preserved": _single_authority_boundary(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "fixed_control_shapes_preserved": _controlled_replay_is_expected(
            controlled_replay
        ),
        "failure_stop_and_rollback_boundaries_preserved": _failure_stop_and_rollback_boundary(
            phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
        ),
        "delivery_and_whitebox_boundaries_preserved": _delivery_and_whitebox_boundary(
            phase3_report, phase4_report
        ),
        "stage079_gate_only_opens_after_review": _future_stage_boundary(
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
        "source_authority": "FROZEN_STAGE078_TASKPACK_AND_STAGE078_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
        "stage077_review_evidence_read": True,
        "stage078_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": review_valid,
        "batch_review_performed": False,
        "stage079_started": False,
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
            "scope": "STAGE078_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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
            "stage079_gate_only_opens_after_review": False,
            "runtime_actions_disabled": False,
        },
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
    except Exception:
        return {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    versions = _mapping(contract.get("index_version_and_active_pointer_contract"))
    building = _mapping(contract.get("building_version_and_shadow_index_contract"))
    smoke = _mapping(contract.get("smoke_test_contract"))
    switch = _mapping(contract.get("future_switch_and_rollback_contract"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    local_code = _mapping(contract.get("local_code"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE078-P1",
            task_id="IDS-V0_1-STAGE078-P1",
            schema_version="ids.stage078.index_smoke_test.phase1.v1",
            contract_state="PHASE1_INDEX_SMOKE_TEST_CONTRACT_RUNTIME_DISABLED",
            next_gate="IDS-STAGE078-P2-GATE",
        )
        and _expected(
            versions,
            {
                "index_version_field_count": 7,
                "active_pointer_field_count": 5,
                "one_active_version_per_index_kind_required": True,
                "all_values_are_control_labels_only": True,
                "actual_index_version_record_created": False,
                "actual_active_pointer_read_performed": False,
                "actual_active_pointer_write_performed": False,
            },
        )
        and _expected(
            building,
            {
                "field_count": 5,
                "new_candidate_required_after_each_bulk_import": True,
                "candidate_must_not_overwrite_active_version": True,
                "candidate_must_remain_isolated_before_smoke_test": True,
                "old_active_index_must_continue_serving_during_build_and_smoke_test": True,
                "background_build_execution_allowed_in_phase1": False,
            },
        )
        and _expected(
            smoke,
            {
                "input_field_count": 6,
                "output_field_count": 5,
                "passed_smoke_test_required_before_switch": True,
                "failed_or_missing_smoke_test_blocks_switch": True,
                "failed_smoke_test_must_not_replace_active_version": True,
                "smoke_test_execution_allowed_in_phase1": False,
            },
        )
        and _expected(
            switch,
            {
                "condition_count": 5,
                "future_atomic_switch_required": True,
                "active_pointer_must_remain_unchanged_on_failure": True,
                "previous_active_index_version_must_be_retained": True,
                "future_rollback_target_must_be_previous_active_index_version": True,
                "automatic_rollback_execution_allowed": False,
            },
        )
        and _expected(
            failures,
            {
                "failure_state_count": 9,
                "automatic_business_write_allowed": False,
                "automatic_active_pointer_switch_allowed": False,
                "actual_failure_record_created": False,
            },
        )
        and _expected(
            local_code,
            {
                "static_contract_only": True,
                "runtime_module_created": False,
                "database_schema_created": False,
                "background_worker_created": False,
                "index_artifact_created": False,
                "smoke_test_runner_created": False,
            },
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    reuse = _mapping(contract.get("phase1_reuse_contract"))
    inputs = _mapping(contract.get("reference_only_control_input_contract"))
    projections = _mapping(contract.get("control_projection_contract"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE078-P2",
            task_id="IDS-V0_1-STAGE078-P2",
            schema_version="ids.stage078.index_smoke_test.phase2.v1",
            contract_state="PHASE2_INDEX_SMOKE_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
            next_gate="IDS-STAGE078-P3-GATE",
        )
        and contract.get("slice_executable") is True
        and contract.get("execution_ready") is False
        and _expected(
            reuse,
            {
                "stage078_phase1_contract_required": True,
                "stage078_phase1_contract_state": "PHASE1_INDEX_SMOKE_TEST_CONTRACT_RUNTIME_DISABLED",
                "future_index_version_field_count": 7,
                "future_active_pointer_field_count": 5,
                "future_smoke_test_input_field_count": 6,
            },
        )
        and _expected(
            inputs,
            {
                "control_request_count": 5,
                "input_field_count": 14,
                "all_reference_values_use_control_labels_only": True,
                "chunk_count_is_zero_for_every_control_request": True,
                "actual_input_request_count": 0,
            },
        )
        and _expected(
            projections,
            {
                "index_version_control_record_count": 5,
                "candidate_build_control_projection_count": 5,
                "active_pointer_control_projection_count": 5,
                "smoke_test_control_projection_count": 5,
                "switch_control_projection_count": 5,
                "rollback_control_projection_count": 5,
                "index_version_control_record_field_count": 8,
                "candidate_build_control_projection_field_count": 5,
                "active_pointer_control_projection_field_count": 5,
                "smoke_test_control_projection_field_count": 13,
                "switch_control_projection_field_count": 11,
                "rollback_control_projection_field_count": 8,
                "candidate_must_differ_from_active_version": True,
                "shadow_candidate_must_remain_isolated_from_active_service": True,
                "old_active_index_continues_serving_during_control_build_and_smoke_test": True,
                "failed_or_missing_smoke_test_blocks_switch": True,
                "switch_projection_is_not_actual_pointer_write": True,
                "rollback_projection_is_not_actual_rollback": True,
            },
        )
        and _expected(
            failures,
            {
                "failure_state_count": 7,
                "automatic_business_write_allowed": False,
                "automatic_active_pointer_switch_allowed": False,
                "automatic_rollback_execution_allowed": False,
                "actual_failure_record_created": False,
            },
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_control_slice_replay_contract"))
    scenarios = _mapping(contract.get("controlled_scenario_contract"))
    views = _mapping(contract.get("control_view_projection_contract"))
    continuity = _mapping(contract.get("failure_and_continuity_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE078-P3",
            task_id="IDS-V0_1-STAGE078-P3",
            schema_version="ids.stage078.index_smoke_test.phase3.v1",
            contract_state="PHASE3_INDEX_SMOKE_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            next_gate="IDS-STAGE078-P4-GATE",
        )
        and contract.get("scenario_executable") is True
        and contract.get("execution_ready") is False
        and _expected(
            replay,
            {
                "control_request_count": 5,
                "index_version_record_field_count": 8,
                "candidate_build_projection_field_count": 5,
                "active_pointer_projection_field_count": 5,
                "smoke_test_projection_field_count": 13,
                "switch_projection_field_count": 11,
                "rollback_projection_field_count": 8,
                "phase2_control_field_check_count": 250,
                "actual_input_request_count": 0,
                "actual_background_build_count": 0,
                "actual_index_build_count": 0,
                "actual_smoke_test_count": 0,
                "actual_retrieval_query_count": 0,
                "actual_index_rollback_count": 0,
                "phase2_shape_must_match_before_scenario_evaluation": True,
                "phase2_invalid_result_fails_closed": True,
            },
        )
        and _expected(
            scenarios,
            {
                "field_count": 26,
                "scenario_count": 6,
                "control_references_are_non_business_labels": True,
                "source_or_document_body_allowed": False,
                "physical_path_or_actual_uri_allowed": False,
                "silent_drop_allowed": False,
                "actual_scenario_record_persisted": False,
            },
        )
        and _expected(
            views,
            {
                "operations_view_projection_count": 5,
                "operations_view_field_count": 6,
                "report_snapshot_projection_count": 5,
                "report_snapshot_field_count": 6,
                "actual_operations_display_written": False,
                "actual_report_snapshot_written": False,
            },
        )
        and _expected(
            continuity,
            {
                "build_not_complete_blocks_switch": True,
                "smoke_test_failure_blocks_switch": True,
                "switch_failure_preserves_active_version": True,
                "rollback_references_retained_previous_active": True,
                "old_active_version_continues_during_build": True,
                "concurrent_retrieval_isolated_from_background_build_in_control_projection": True,
                "operations_and_report_snapshot_version_visibility_projected": True,
                "actual_index_build_started": False,
                "actual_retrieval_query_performed": False,
                "actual_rollback_execution_performed": False,
            },
        )
        and _expected(
            authority,
            {
                "source_document_remains_authoritative": True,
                "control_scenario_can_replace_source_document": False,
                "control_view_can_become_business_fact_authority": False,
                "automatic_business_recommendation_allowed": False,
                "business_line_whitebox_human_review_required": True,
                "actual_business_decision_created": False,
            },
        )
        and _expected(
            failures,
            {"failure_state_count": 13, "actual_failure_record_created": False},
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    phase2_replay = _mapping(contract.get("phase2_control_slice_replay_contract"))
    phase3_replay = _mapping(contract.get("phase3_controlled_scenario_replay_contract"))
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    return (
        _contract_common_valid(
            contract,
            phase="P4",
            task_id="IDS-V0_1-STAGE078-P4",
            schema_version="ids.stage078.index_smoke_test.phase4.delivery.v1",
            contract_state="PHASE4_INDEX_SMOKE_TEST_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            next_gate=REVIEW_GATE,
        )
        and contract.get("delivery_executable") is True
        and contract.get("execution_ready") is False
        and _expected(
            phase2_replay,
            {
                "control_request_count": 5,
                "index_version_record_field_count": 8,
                "candidate_build_projection_field_count": 5,
                "active_pointer_projection_field_count": 5,
                "smoke_test_projection_field_count": 13,
                "switch_projection_field_count": 11,
                "rollback_projection_field_count": 8,
                "phase2_control_field_check_count": 250,
                "actual_control_record_persisted": False,
            },
        )
        and _expected(
            phase3_replay,
            {
                "scenario_count": 6,
                "scenario_field_count": 26,
                "scenario_field_check_count": 156,
                "operations_version_control_view_count": 5,
                "report_snapshot_version_control_view_count": 5,
                "actual_control_scenario_record_persisted": False,
            },
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
            failures,
            {"failure_state_count": 13, "actual_failure_record_created": False},
        )
    )


def _contract_common_valid(
    contract: Mapping[str, Any],
    *,
    phase: str,
    task_id: str,
    schema_version: str,
    contract_state: str,
    next_gate: str,
) -> bool:
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("phase") == phase
        and contract.get("task_id") == task_id
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("schema_version") == schema_version
        and contract.get("contract_state") == contract_state
        and contract.get("next_gate") == next_gate
        and _authority_closed(contract)
        and _all_false(_mapping(contract.get("protected_surface_boundary")))
        and _all_false(_mapping(contract.get("runtime_boundary")))
        and (
            boundary.get("stage078_started") is True
            or boundary.get("stage078_phase1_completed") is True
        )
        and boundary.get("stage079_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _phase2_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    record_specs = (
        ("index_version_control_records", "INDEX_VERSION_RECORD_FIELDS"),
        ("candidate_build_control_projections", "CANDIDATE_BUILD_FIELDS"),
        ("active_pointer_control_projections", "ACTIVE_POINTER_FIELDS"),
        ("smoke_test_control_projections", "SMOKE_TEST_PROJECTION_FIELDS"),
        ("switch_control_projections", "SWITCH_PROJECTION_FIELDS"),
        ("rollback_control_projections", "ROLLBACK_PROJECTION_FIELDS"),
    )
    return (
        report.get("schema_version") == "ids.stage078.index_smoke_test.phase2.v1"
        and report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_request_count") == 5
        and report.get("actual_input_request_count") == 0
        and _expected(
            report,
            {
                "index_version_control_record_count": 5,
                "candidate_build_control_projection_count": 5,
                "active_pointer_control_projection_count": 5,
                "smoke_test_control_projection_count": 5,
                "switch_control_projection_count": 5,
                "rollback_control_projection_count": 5,
                "control_build_not_complete_count": 1,
                "control_smoke_test_not_run_count": 1,
                "control_smoke_test_failed_count": 1,
                "control_switch_blocked_count": 2,
                "control_switch_failure_count": 1,
                "control_rollback_candidate_count": 1,
                "all_control_records_keep_required_shapes": True,
                "all_candidate_versions_differ_from_active_versions": True,
                "all_shadow_candidates_are_isolated_from_active_service": True,
                "all_old_active_versions_continue_serving": True,
                "all_nonpassed_smoke_tests_block_switch": True,
                "all_switch_projections_keep_active_pointer_unchanged": True,
                "all_rollback_targets_reference_retained_previous_active": True,
            },
        )
        and all(
            _records_have_exact_shape(
                report.get(record_key), 5, getattr(module, field_name, ())
            )
            for record_key, field_name in record_specs
        )
        and _report_runtime_closed(report, module)
    )


def _phase3_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    scenarios = report.get("scenario_results")
    return (
        report.get("schema_version") == "ids.stage078.index_smoke_test.phase3.v1"
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE078-P4-GATE"
        and _expected(
            report,
            {
                "phase2_control_slice_reexecuted": True,
                "phase2_shape_preserved": True,
                "phase2_side_effect_free": True,
                "phase2_control_record_field_check_count": 250,
                "scenario_count": 6,
                "scenario_field_count": 26,
                "scenario_field_check_count": 156,
                "passed_scenario_count": 6,
                "explicit_disposition_count": 6,
                "silent_drop_count": 0,
                "human_handling_required_count": 6,
                "operations_version_control_view_count": 5,
                "report_snapshot_version_control_view_count": 5,
                "control_views_preserved": True,
                "build_not_complete_preserved": True,
                "smoke_test_failure_preserved": True,
                "switch_failure_preserved": True,
                "rollback_preserved": True,
                "concurrent_retrieval_isolation_preserved": True,
                "operations_and_report_snapshot_visibility_preserved": True,
                "all_control_references_opaque": True,
                "source_document_remains_authoritative": True,
                "control_scenario_can_replace_source_document": False,
                "control_view_can_become_business_fact_authority": False,
                "automatic_business_recommendation_allowed": False,
                "stage079_started": False,
                "github_upload_allowed": False,
                "push_allowed": False,
            },
        )
        and _records_have_exact_shape(
            scenarios, 6, getattr(module, "SCENARIO_RESULT_FIELDS", ())
        )
        and _report_runtime_closed(report, module)
    )


def _phase4_report_valid(report: Mapping[str, Any], module: Any) -> bool:
    return (
        report.get("schema_version") == "ids.stage078.index_smoke_test.phase4.delivery.v1"
        and report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and _expected(
            report,
            {
                "phase3_controlled_scenarios_reused_as_reference_only": True,
                "phase3_controlled_scenarios_report_valid": True,
                "phase2_control_slice_reexecuted_in_memory_only": True,
                "phase2_control_slice_report_valid": True,
                "delivery_evidence_metadata_only": True,
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
                "all_delivery_references_control_only": True,
                "source_document_remains_authoritative": True,
                "business_line_whitebox_human_review_remains_authoritative": True,
                "delivery_control_metadata_can_replace_source_document": False,
                "delivery_control_metadata_can_become_business_fact_authority": False,
                "automatic_business_recommendation_allowed": False,
                "stage079_started": False,
                "github_upload_allowed": False,
                "push_allowed": False,
            },
        )
        and isinstance(report.get("chinese_feedback"), list)
        and len(report["chinese_feedback"]) == 4
        and _report_runtime_closed(report, module)
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int]:
    versions = _mapping(phase1.get("index_version_and_active_pointer_contract"))
    building = _mapping(phase1.get("building_version_and_shadow_index_contract"))
    smoke = _mapping(phase1.get("smoke_test_contract"))
    switch = _mapping(phase1.get("future_switch_and_rollback_contract"))
    p1_failures = _mapping(phase1.get("failure_and_stop_contract"))
    p2_failures = _mapping(phase2.get("failure_and_stop_contract"))
    p3_failures = _mapping(phase3.get("failure_and_stop_contract"))
    p4_failures = _mapping(phase4.get("failure_and_stop_contract"))
    return {
        "phase1_index_version_field_count": _as_int(
            versions.get("index_version_field_count")
        ),
        "phase1_active_pointer_field_count": _as_int(
            versions.get("active_pointer_field_count")
        ),
        "phase1_building_version_field_count": _as_int(building.get("field_count")),
        "phase1_smoke_input_field_count": _as_int(smoke.get("input_field_count")),
        "phase1_smoke_output_field_count": _as_int(smoke.get("output_field_count")),
        "phase1_switch_condition_count": _as_int(switch.get("condition_count")),
        "phase1_failure_state_count": _as_int(p1_failures.get("failure_state_count")),
        "phase2_control_request_count": _as_int(phase2_report.get("control_request_count")),
        "phase2_index_version_record_count": _as_int(
            phase2_report.get("index_version_control_record_count")
        ),
        "phase2_candidate_build_projection_count": _as_int(
            phase2_report.get("candidate_build_control_projection_count")
        ),
        "phase2_active_pointer_projection_count": _as_int(
            phase2_report.get("active_pointer_control_projection_count")
        ),
        "phase2_smoke_test_projection_count": _as_int(
            phase2_report.get("smoke_test_control_projection_count")
        ),
        "phase2_switch_projection_count": _as_int(
            phase2_report.get("switch_control_projection_count")
        ),
        "phase2_rollback_projection_count": _as_int(
            phase2_report.get("rollback_control_projection_count")
        ),
        "phase2_control_field_check_count": _as_int(
            phase3_report.get("phase2_control_record_field_check_count")
        ),
        "phase2_failure_state_count": _as_int(p2_failures.get("failure_state_count")),
        "phase3_scenario_count": _as_int(phase3_report.get("scenario_count")),
        "phase3_scenario_field_count": _as_int(phase3_report.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _as_int(
            phase3_report.get("scenario_field_check_count")
        ),
        "phase3_operations_view_count": _as_int(
            phase3_report.get("operations_version_control_view_count")
        ),
        "phase3_report_snapshot_view_count": _as_int(
            phase3_report.get("report_snapshot_version_control_view_count")
        ),
        "phase3_human_handling_required_count": _as_int(
            phase3_report.get("human_handling_required_count")
        ),
        "phase3_failure_state_count": _as_int(p3_failures.get("failure_state_count")),
        "phase4_index_manifest_sample_count": _as_int(
            phase4_report.get("index_manifest_control_sample_count")
        ),
        "phase4_smoke_log_sample_count": _as_int(
            phase4_report.get("smoke_test_log_control_sample_count")
        ),
        "phase4_switch_record_sample_count": _as_int(
            phase4_report.get("switch_record_control_sample_count")
        ),
        "phase4_rollback_proof_sample_count": _as_int(
            phase4_report.get("rollback_proof_control_sample_count")
        ),
        "phase4_old_index_retention_count": _as_int(
            phase4_report.get("old_index_retention_projection_count")
        ),
        "phase4_operational_instruction_count": _as_int(
            phase4_report.get("operational_instruction_projection_count")
        ),
        "phase4_chinese_feedback_count": len(
            phase4_report.get("chinese_feedback", [])
            if isinstance(phase4_report.get("chinese_feedback"), list)
            else []
        ),
        "phase4_failure_state_count": _as_int(p4_failures.get("failure_state_count")),
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
        all(_authority_closed(contract) for contract in (phase1, phase2, phase3, phase4))
        and phase3_report.get("source_document_remains_authoritative") is True
        and phase3_report.get("control_scenario_can_replace_source_document") is False
        and phase3_report.get("control_view_can_become_business_fact_authority") is False
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and phase4_report.get("delivery_control_metadata_can_replace_source_document")
        is False
        and phase4_report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
    )


def _failure_stop_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    p1_switch = _mapping(phase1.get("future_switch_and_rollback_contract"))
    p2_projection = _mapping(phase2.get("control_projection_contract"))
    p3_continuity = _mapping(phase3.get("failure_and_continuity_contract"))
    p4_delivery = _mapping(phase4.get("delivery_evidence_contract"))
    return (
        _expected(
            p1_switch,
            {
                "active_pointer_must_remain_unchanged_on_failure": True,
                "previous_active_index_version_must_be_retained": True,
                "future_rollback_target_must_be_previous_active_index_version": True,
                "automatic_rollback_execution_allowed": False,
            },
        )
        and _expected(
            p2_projection,
            {
                "failed_or_missing_smoke_test_blocks_switch": True,
                "switch_projection_is_not_actual_pointer_write": True,
                "rollback_projection_is_not_actual_rollback": True,
            },
        )
        and _expected(
            p3_continuity,
            {
                "build_not_complete_blocks_switch": True,
                "smoke_test_failure_blocks_switch": True,
                "switch_failure_preserves_active_version": True,
                "rollback_references_retained_previous_active": True,
                "old_active_version_continues_during_build": True,
            },
        )
        and _expected(
            p4_delivery,
            {
                "old_index_retention_projection_count": 1,
                "operational_instruction_projection_count": 3,
                "actual_space_impact_measurement_performed": False,
                "actual_operational_instruction_issued": False,
            },
        )
        and phase2_report.get("all_nonpassed_smoke_tests_block_switch") is True
        and phase2_report.get("all_switch_projections_keep_active_pointer_unchanged")
        is True
        and phase2_report.get("all_rollback_targets_reference_retained_previous_active")
        is True
        and all(
            phase3_report.get(field) is True
            for field in (
                "build_not_complete_preserved",
                "smoke_test_failure_preserved",
                "switch_failure_preserved",
                "rollback_preserved",
                "concurrent_retrieval_isolation_preserved",
                "operations_and_report_snapshot_visibility_preserved",
            )
        )
        and phase4_report.get("all_delivery_references_control_only") is True
        and phase4_report.get("old_index_retention_projection_count") == 1
        and phase4_report.get("operational_instruction_projection_count") == 3
    )


def _delivery_and_whitebox_boundary(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    return (
        phase3_report.get("human_handling_required_count") == 6
        and phase3_report.get("silent_drop_count") == 0
        and phase3_report.get("all_control_references_opaque") is True
        and phase4_report.get("delivery_evidence_metadata_only") is True
        and phase4_report.get("all_delivery_references_control_only") is True
        and phase4_report.get("automatic_business_recommendation_allowed") is False
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
        NEXT_TASKPACK.is_file()
        and all(
            _mapping(contract.get("stage_and_phase_boundary")).get("stage079_started")
            is False
            for contract in (phase1, phase2, phase3, phase4)
        )
        and phase4.get("next_gate") == REVIEW_GATE
        and phase3_report.get("stage079_started") is False
        and phase4_report.get("stage079_started") is False
        and phase3_report.get("next_gate") == "IDS-STAGE078-P4-GATE"
        and phase4_report.get("next_gate") == REVIEW_GATE
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
            _all_false(_mapping(contract.get("runtime_boundary")))
            for contract in (phase1, phase2, phase3, phase4)
        )
        and _report_runtime_closed(phase2_report, phase2_module)
        and _report_runtime_closed(phase3_report, phase3_module)
        and _report_runtime_closed(phase4_report, phase4_module)
    )


def _controlled_replay_is_expected(controlled_replay: Mapping[str, int]) -> bool:
    return dict(controlled_replay) == EXPECTED_CONTROLLED_REPLAY


def _contract_has_closed_rollback(contract: Mapping[str, Any]) -> bool:
    rollback = _mapping(contract.get("rollback_contract"))
    return _expected(
        rollback,
        {
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
    )


def _authority_closed(contract: Mapping[str, Any]) -> bool:
    authority = _mapping(contract.get("source_authority"))
    protected = _mapping(contract.get("protected_surface_boundary"))
    return (
        isinstance(authority.get("authority"), str)
        and authority["authority"].startswith("FROZEN_STAGE078_TASKPACK")
        and _expected(
            authority,
            {
                "second_authoritative_source_created": False,
                "source_body_or_path_allowed": False,
                "raw_metadata_content_access_allowed": False,
                "live_source_read_performed": False,
                "authorized_fixture_access_performed": False,
            },
        )
        and _all_false(protected)
        and _contract_has_closed_rollback(contract)
    )


def _report_runtime_closed(report: Mapping[str, Any], module: Any) -> bool:
    fields = getattr(module, "RUNTIME_CLOSED_FIELDS", ())
    return (
        isinstance(fields, Sequence)
        and all(report.get(field) is False for field in fields)
        and _all_actual_counts_zero(report)
    )


def _all_actual_counts_zero(report: Mapping[str, Any]) -> bool:
    values = [
        value
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    ]
    return all(value == 0 for value in values)


def _records_have_exact_shape(
    records: object, expected_count: int, fields: Sequence[object]
) -> bool:
    if not isinstance(records, list) or len(records) != expected_count:
        return False
    expected = set(fields)
    return bool(expected) and all(
        isinstance(record, Mapping) and set(record) == expected for record in records
    )


def _expected(mapping: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(mapping.get(key) == value for key, value in expected.items())


def _all_false(mapping: Mapping[str, Any]) -> bool:
    return bool(mapping) and all(value is False for value in mapping.values())


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _chinese_feedback(review_valid: bool) -> list[str]:
    if review_valid:
        return [
            "Stage078 索引冒烟测试控制合同已机械复审，未执行实际索引操作。",
            "失败关闭、旧活动版本连续服务和回退保留边界保持不变。",
            "交付证据仅为内存控制投影，业务线白箱人工复核仍是唯一权威。",
            "仅开放 Stage079 P1 门，未启动后续阶段、生产或上传。",
        ]
    return [
        "Stage078 整阶段复审未通过，保持在 Review 门。",
        "任何合同、控制形状或零运行时边界不一致均不得打开后续阶段。",
        "请由业务线白箱人工处理异常，不执行实际索引操作。",
        "未启动 Stage079、生产或上传。",
    ]
