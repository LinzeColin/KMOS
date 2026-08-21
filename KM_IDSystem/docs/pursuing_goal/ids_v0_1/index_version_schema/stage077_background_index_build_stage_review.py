"""Stage077 的纯内存整阶段机械复审，不读取真实资料或启动 Stage078。"""

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
    / "STAGE-077_后台索引构建.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-078_索引冒烟测试.md"
)
P1_CONTRACT = BASE / "stage077_background_index_build_contract.json"
P2_CONTRACT = BASE / "stage077_background_index_build_slice_contract.json"
P3_CONTRACT = BASE / "stage077_background_index_build_scenarios_contract.json"
P4_CONTRACT = BASE / "stage077_background_index_build_delivery_contract.json"

SCHEMA_VERSION = "ids.stage077.background_index_build.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE077-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-077"
PASS_RESULT = "PASS_REVIEWED_BACKGROUND_INDEX_BUILD_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_BACKGROUND_INDEX_BUILD_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE077-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE078-P1-GATE"
RETURN_STATE = "PASS_BACKGROUND_INDEX_BUILD_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_BACKGROUND_INDEX_BUILD_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = RETURN_STATE

P2_EXPECTED_COUNTS = {
    "control_request_count": 5,
    "index_version_control_record_count": 5,
    "building_version_control_record_count": 5,
    "active_pointer_control_projection_count": 5,
    "background_build_output_control_projection_count": 5,
    "smoke_test_control_projection_count": 5,
    "switch_control_projection_count": 5,
    "rollback_control_projection_count": 5,
    "control_background_building_count": 1,
    "control_smoke_test_failed_count": 1,
    "control_switch_blocked_count": 2,
    "control_switch_failure_count": 1,
    "control_rollback_candidate_count": 1,
}
P3_EXPECTED_COUNTS = {
    "scenario_count": 6,
    "scenario_field_count": 26,
    "scenario_field_check_count": 156,
    "passed_scenario_count": 6,
    "explicit_disposition_count": 6,
    "silent_drop_count": 0,
    "human_handling_required_count": 6,
    "operations_version_control_view_count": 5,
    "report_snapshot_version_control_view_count": 5,
    "phase2_control_record_field_check_count": 255,
}
P4_EXPECTED_COUNTS = {
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
    "actual_building_version_record_created",
    "actual_shadow_index_created",
    "actual_shadow_index_queried",
    "actual_smoke_test_performed",
    "actual_smoke_test_result_recorded",
    "actual_active_pointer_read_performed",
    "actual_active_pointer_write_performed",
    "actual_switch_record_created",
    "actual_retrieval_query_performed",
    "actual_rollback_record_created",
    "actual_rollback_execution_performed",
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
    "actual_concurrent_retrieval_performed",
    "actual_operations_display_written",
    "actual_report_snapshot_written",
    "actual_index_manifest_written",
    "actual_smoke_test_log_written",
    "actual_switch_record_written",
    "actual_rollback_proof_written",
    "actual_old_index_retention_record_written",
    "actual_space_impact_measurement_performed",
    "actual_operational_instruction_issued",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_background_index_build_stage077_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage077 P1--P4，只输出零运行时结论及后续门禁。"""

    try:
        phase2_module = _load_module("stage077_background_index_build_slice.py")
        phase3_module = _load_module("stage077_background_index_build_scenarios.py")
        phase4_module = _load_module("stage077_background_index_build_delivery.py")
    except Exception:
        return _failed_report()

    phase1 = _provider_value(phase1_contract_provider or _json_provider(P1_CONTRACT))
    phase2 = _provider_value(phase2_contract_provider or _json_provider(P2_CONTRACT))
    phase3 = _provider_value(phase3_contract_provider or _json_provider(P3_CONTRACT))
    phase4 = _provider_value(phase4_contract_provider or _json_provider(P4_CONTRACT))
    phase2_report = _provider_value(
        phase2_report_provider
        or (
            lambda: phase2_module.execute_background_index_build_control_slice(
                phase2_module.build_control_input()
            )
        )
    )
    phase3_report = _provider_value(
        phase3_report_provider or phase3_module.build_background_index_build_phase3_report
    )
    phase4_report = _provider_value(
        phase4_report_provider
        or phase4_module.build_background_index_build_phase4_delivery_report
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2)
        and _phase2_report_valid(phase2_report, phase2_module, phase3_module),
        "P3": _phase3_contract_valid(phase3)
        and _phase3_report_valid(phase3_report, phase3_module),
        "P4": _phase4_contract_valid(phase4)
        and _phase4_report_valid(phase4_report, phase4_module),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2_report, phase3_report, phase4, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "single_authority_boundary_preserved": _single_authority_boundary(
            phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
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
        "stage078_gate_only_opens_after_review": _future_stage_boundary(
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
        "source_authority": "FROZEN_STAGE077_TASKPACK_AND_STAGE077_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
        "stage076_review_evidence_read": True,
        "stage077_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": review_valid,
        "batch_review_performed": False,
        "stage078_started": False,
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
            "scope": "STAGE077_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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
            "stage078_gate_only_opens_after_review": False,
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
    input_output = _mapping(contract.get("background_build_input_output_contract"))
    lifecycle = _mapping(contract.get("background_build_lifecycle_contract"))
    smoke = _mapping(contract.get("smoke_and_atomic_switch_contract"))
    retention = _mapping(contract.get("rollback_and_retention_contract"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    local_code = _mapping(contract.get("local_code"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE077-P1",
            task_id="IDS-V0_1-STAGE077-P1",
            schema_version="ids.stage077.background_index_build.phase1.v1",
            contract_state="PHASE1_BACKGROUND_INDEX_BUILD_CONTRACT_RUNTIME_DISABLED",
            next_gate="IDS-STAGE077-P2-GATE",
            failure_state_count=8,
            phase_flags={
                "stage077_entry_authorized": True,
                "stage077_started": True,
                "phase1_started": True,
                "phase2_started": False,
                "phase3_started": False,
                "phase4_started": False,
            },
        )
        and input_output.get("input_field_count") == 6
        and input_output.get("output_field_count") == 6
        and input_output.get("all_values_are_control_labels_only") is True
        and input_output.get("background_build_execution_allowed_in_phase1") is False
        and lifecycle.get("state_count") == 7
        and lifecycle.get("active_index_must_continue_serving_during_build") is True
        and lifecycle.get("candidate_must_remain_isolated_before_switch") is True
        and smoke.get("condition_count") == 6
        and smoke.get("failed_or_missing_smoke_test_blocks_switch") is True
        and smoke.get("active_pointer_must_remain_unchanged_on_failure") is True
        and retention.get("previous_active_index_version_must_be_retained") is True
        and retention.get("old_active_index_must_continue_serving_until_successful_switch")
        is True
        and retention.get("automatic_rollback_execution_allowed") is False
        and feedback.get("feedback_count") == 4
        and feedback.get("business_line_whitebox_human_review_required_for_future_exception")
        is True
        and local_code.get("static_contract_only") is True
        and local_code.get("runtime_module_created") is False
        and local_code.get("database_schema_created") is False
        and local_code.get("background_worker_created") is False
        and local_code.get("index_artifact_created") is False
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _mapping(contract.get("reference_only_control_input_contract"))
    schema_reuse = _mapping(contract.get("schema_reuse_contract"))
    projections = _mapping(contract.get("control_projection_contract"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE077-P2",
            task_id="IDS-V0_1-STAGE077-P2",
            schema_version="ids.stage077.background_index_build.phase2.v1",
            contract_state="PHASE2_BACKGROUND_INDEX_BUILD_CONTROL_SLICE_RUNTIME_DISABLED",
            next_gate="IDS-STAGE077-P3-GATE",
            failure_state_count=7,
            phase_flags={
                "stage077_phase1_completed": True,
                "stage077_phase2_started": True,
                "phase3_started": False,
                "phase4_started": False,
            },
        )
        and contract.get("slice_executable") is True
        and contract.get("execution_ready") is False
        and input_contract.get("control_request_count") == 5
        and input_contract.get("actual_input_request_count") == 0
        and input_contract.get("chunk_count_is_zero_for_every_control_request") is True
        and input_contract.get("all_reference_values_use_control_labels_only") is True
        and schema_reuse.get("index_version_record_field_count") == 8
        and schema_reuse.get("building_version_field_count") == 5
        and schema_reuse.get("active_pointer_field_count") == 5
        and schema_reuse.get("candidate_must_differ_from_active_version") is True
        and schema_reuse.get("old_active_index_continues_serving_during_control_build")
        is True
        and schema_reuse.get("shadow_candidate_must_remain_isolated_from_active_service")
        is True
        and all(
            projections.get(field) == 5
            for field in (
                "index_version_control_record_count",
                "building_version_control_record_count",
                "active_pointer_control_projection_count",
                "background_build_output_control_projection_count",
                "smoke_test_control_projection_count",
                "switch_control_projection_count",
                "rollback_control_projection_count",
            )
        )
        and projections.get("background_build_output_field_count") == 6
        and projections.get("failed_or_pending_smoke_test_blocks_switch") is True
        and projections.get("rollback_projection_is_not_actual_rollback") is True
        and projections.get("switch_projection_is_not_actual_pointer_write") is True
        and feedback.get("feedback_count") == 4
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_control_slice_replay_contract"))
    scenarios = _mapping(contract.get("controlled_scenario_contract"))
    views = _mapping(contract.get("control_view_projection_contract"))
    continuity = _mapping(contract.get("failure_and_continuity_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    return (
        _contract_common_valid(
            contract,
            phase="IDS-STAGE077-P3",
            task_id="IDS-V0_1-STAGE077-P3",
            schema_version="ids.stage077.background_index_build.phase3.v1",
            contract_state="PHASE3_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            next_gate="IDS-STAGE077-P4-GATE",
            failure_state_count=13,
            phase_flags={
                "stage077_phase1_completed": True,
                "stage077_phase2_completed": True,
                "stage077_phase3_started": True,
                "phase4_started": False,
            },
        )
        and contract.get("scenario_executable") is True
        and contract.get("execution_ready") is False
        and replay.get("control_request_count") == 5
        and replay.get("phase2_control_field_check_count") == 255
        and replay.get("index_version_record_field_count") == 8
        and replay.get("building_version_record_field_count") == 5
        and replay.get("active_pointer_projection_field_count") == 5
        and replay.get("background_build_output_projection_field_count") == 6
        and replay.get("smoke_test_projection_field_count") == 8
        and replay.get("switch_projection_field_count") == 11
        and replay.get("rollback_projection_field_count") == 8
        and scenarios.get("scenario_count") == 6
        and scenarios.get("field_count") == 26
        and scenarios.get("control_references_are_non_business_labels") is True
        and scenarios.get("silent_drop_allowed") is False
        and views.get("operations_view_projection_count") == 5
        and views.get("operations_view_field_count") == 6
        and views.get("report_snapshot_projection_count") == 5
        and views.get("report_snapshot_field_count") == 6
        and continuity.get("build_not_complete_blocks_switch") is True
        and continuity.get("smoke_test_failure_blocks_switch") is True
        and continuity.get("switch_failure_preserves_active_version") is True
        and continuity.get("rollback_references_retained_previous_active") is True
        and continuity.get("concurrent_retrieval_isolated_from_background_build_in_control_projection")
        is True
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_required") is True
        and authority.get("control_scenario_can_replace_source_document") is False
        and authority.get("control_view_can_become_business_fact_authority") is False
        and authority.get("automatic_business_recommendation_allowed") is False
        and feedback.get("feedback_count") == 4
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    phase2_replay = _mapping(contract.get("phase2_control_slice_replay_contract"))
    phase3_replay = _mapping(contract.get("phase3_controlled_scenario_replay_contract"))
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    authority = _mapping(contract.get("authority_and_decision_boundary"))
    return (
        _contract_common_valid(
            contract,
            phase="P4",
            task_id="IDS-V0_1-STAGE077-P4",
            schema_version="ids.stage077.background_index_build.phase4.delivery.v1",
            contract_state="PHASE4_BACKGROUND_INDEX_BUILD_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            next_gate=REVIEW_GATE,
            failure_state_count=13,
            phase_flags={
                "stage077_phase1_completed": True,
                "stage077_phase2_completed": True,
                "stage077_phase3_completed": True,
                "phase4_started": True,
            },
        )
        and contract.get("delivery_executable") is True
        and contract.get("execution_ready") is False
        and phase2_replay.get("control_request_count") == 5
        and phase2_replay.get("phase2_control_field_check_count") == 255
        and phase2_replay.get("index_version_record_field_count") == 8
        and phase2_replay.get("building_version_record_field_count") == 5
        and phase2_replay.get("active_pointer_projection_field_count") == 5
        and phase2_replay.get("background_build_output_projection_field_count") == 6
        and phase2_replay.get("smoke_test_projection_field_count") == 8
        and phase2_replay.get("switch_projection_field_count") == 11
        and phase2_replay.get("rollback_projection_field_count") == 8
        and phase3_replay.get("scenario_count") == 6
        and phase3_replay.get("scenario_field_count") == 26
        and phase3_replay.get("scenario_field_check_count") == 156
        and phase3_replay.get("operations_version_control_view_count") == 5
        and phase3_replay.get("report_snapshot_version_control_view_count") == 5
        and _has_expected_counts(delivery, {
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
        })
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and authority.get("delivery_control_metadata_can_replace_source_document")
        is False
        and authority.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and authority.get("automatic_business_recommendation_allowed") is False
    )


def _contract_common_valid(
    contract: Mapping[str, Any],
    *,
    phase: str,
    task_id: str,
    schema_version: str,
    contract_state: str,
    next_gate: str,
    failure_state_count: int,
    phase_flags: Mapping[str, bool],
) -> bool:
    source_authority = _mapping(contract.get("source_authority"))
    runtime_boundary = _mapping(contract.get("runtime_boundary"))
    phase_boundary = _mapping(contract.get("stage_and_phase_boundary"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    protected = _mapping(contract.get("protected_surface_boundary"))
    rollback = _mapping(contract.get("rollback_contract"))
    return (
        contract.get("stage") == "STAGE-077"
        and contract.get("phase") == phase
        and contract.get("task_id") == task_id
        and contract.get("schema_version") == schema_version
        and contract.get("contract_state") == contract_state
        and contract.get("next_gate") == next_gate
        and _source_authority_closed(source_authority)
        and _all_false_mapping(runtime_boundary)
        and all(phase_boundary.get(field) is value for field, value in phase_flags.items())
        and phase_boundary.get("whole_stage_review_performed") is False
        and phase_boundary.get("stage078_started") is False
        and phase_boundary.get("github_upload_allowed") is False
        and phase_boundary.get("push_allowed") is False
        and failures.get("failure_state_count") == failure_state_count
        and failures.get("actual_failure_record_created") is False
        and _all_false_mapping(protected)
        and rollback.get("source_or_raw_data_change_allowed") is False
        and rollback.get("database_or_persistent_state_change_allowed") is False
        and rollback.get("github_or_ovh_change_allowed") is False
    )


def _phase2_report_valid(
    report: Mapping[str, Any], phase2_module: Any, phase3_module: Any
) -> bool:
    record_specs = (
        ("index_version_control_records", phase2_module.INDEX_VERSION_RECORD_FIELDS),
        ("building_version_control_records", phase2_module.BUILDING_VERSION_FIELDS),
        ("active_pointer_control_projections", phase2_module.ACTIVE_POINTER_FIELDS),
        (
            "background_build_output_control_projections",
            phase2_module.BACKGROUND_BUILD_OUTPUT_FIELDS,
        ),
        ("smoke_test_control_projections", phase2_module.SMOKE_TEST_FIELDS),
        ("switch_control_projections", phase2_module.SWITCH_PROJECTION_FIELDS),
        ("rollback_control_projections", phase2_module.ROLLBACK_PROJECTION_FIELDS),
    )
    return (
        report.get("schema_version") == phase2_module.SCHEMA_VERSION
        and report.get("record_kind") == phase2_module.RECORD_KIND
        and report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_scenarios_covered")
        == list(phase2_module.CONTROL_SCENARIOS)
        and _has_expected_counts(report, P2_EXPECTED_COUNTS)
        and all(
            _records_have_exact_shape(_mapping_sequence(report.get(key)), 5, tuple(fields))
            for key, fields in record_specs
        )
        and report.get("all_control_records_keep_required_shapes") is True
        and report.get("all_candidate_versions_differ_from_active_versions") is True
        and report.get("all_active_versions_continue_serving_during_control_build")
        is True
        and report.get("all_failed_or_pending_smoke_tests_block_switch") is True
        and report.get("all_rollback_targets_reference_retained_previous_active")
        is True
        and report.get("all_shadow_candidates_are_isolated_from_active_service") is True
        and report.get("all_switch_projections_keep_active_pointer_unchanged") is True
        and report.get("control_output_is_not_actual_index_database_or_retrieval")
        is True
        and report.get("actual_input_request_count") == 0
        and _all_false(report, tuple(phase3_module.P2_RUNTIME_CLOSED_FIELDS))
    )


def _phase3_report_valid(report: Mapping[str, Any], phase3_module: Any) -> bool:
    scenarios = _mapping_sequence(report.get("scenario_results"))
    operations = _mapping_sequence(report.get("operations_version_control_views"))
    snapshots = _mapping_sequence(report.get("report_snapshot_version_control_views"))
    expected_ids = [item["scenario_id"] for item in phase3_module.SCENARIOS]
    return (
        report.get("schema_version") == phase3_module.SCHEMA_VERSION
        and report.get("record_kind") == phase3_module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE077-P4-GATE"
        and report.get("stage077_started") is True
        and report.get("phase1_started") is True
        and report.get("phase2_started") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("stage078_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
        and _has_expected_counts(report, P3_EXPECTED_COUNTS)
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and _records_have_exact_shape(
            scenarios, 6, tuple(phase3_module.SCENARIO_RESULT_FIELDS)
        )
        and _records_have_exact_shape(
            operations, 5, tuple(phase3_module.OPERATIONS_VIEW_FIELDS)
        )
        and _records_have_exact_shape(
            snapshots, 5, tuple(phase3_module.REPORT_SNAPSHOT_FIELDS)
        )
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("silent_drop") is False for item in scenarios)
        and all(
            report.get(field) is True
            for field in (
                "phase2_control_slice_reexecuted",
                "phase2_shape_preserved",
                "phase2_side_effect_free",
                "control_views_preserved",
                "all_control_references_opaque",
                "build_not_complete_preserved",
                "smoke_test_failure_preserved",
                "switch_failure_preserved",
                "rollback_preserved",
                "concurrent_retrieval_isolation_preserved",
                "operations_and_report_snapshot_visibility_preserved",
                "source_document_remains_authoritative",
            )
        )
        and report.get("control_scenario_can_replace_source_document") is False
        and report.get("control_view_can_become_business_fact_authority") is False
        and report.get("automatic_business_recommendation_allowed") is False
        and _actual_counts_are_zero(report)
        and _all_false(report, tuple(phase3_module.RUNTIME_CLOSED_FIELDS))
    )


def _phase4_report_valid(report: Mapping[str, Any], phase4_module: Any) -> bool:
    manifests = _mapping_sequence(report.get("index_manifest_control_samples"))
    smoke_logs = _mapping_sequence(report.get("smoke_test_log_control_samples"))
    switches = _mapping_sequence(report.get("switch_record_control_samples"))
    rollbacks = _mapping_sequence(report.get("rollback_proof_control_samples"))
    retention = _mapping(report.get("old_index_retention_projection"))
    instructions = _mapping_sequence(report.get("operational_instruction_projections"))
    return (
        report.get("schema_version") == phase4_module.SCHEMA_VERSION
        and report.get("record_kind") == phase4_module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and report.get("stage077_started") is True
        and report.get("phase1_started") is True
        and report.get("phase2_started") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is True
        and report.get("whole_stage_review_performed") is False
        and report.get("stage078_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
        and _has_expected_counts(report, P4_EXPECTED_COUNTS)
        and _records_have_exact_shape(
            manifests, 5, tuple(phase4_module.INDEX_MANIFEST_FIELDS)
        )
        and _records_have_exact_shape(
            smoke_logs, 6, tuple(phase4_module.SMOKE_TEST_LOG_FIELDS)
        )
        and _records_have_exact_shape(
            switches, 5, tuple(phase4_module.SWITCH_RECORD_FIELDS)
        )
        and _records_have_exact_shape(
            rollbacks, 5, tuple(phase4_module.ROLLBACK_PROOF_FIELDS)
        )
        and set(retention) == set(phase4_module.OLD_INDEX_RETENTION_FIELDS)
        and _records_have_exact_shape(
            instructions, 3, tuple(phase4_module.OPERATIONAL_INSTRUCTION_FIELDS)
        )
        and report.get("phase2_control_slice_report_valid") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("all_delivery_references_control_only") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document")
        is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and report.get("automatic_business_recommendation_allowed") is False
        and retention.get("space_impact_state")
        == "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED"
        and retention.get("actual_space_impact_measurement_performed") is False
        and retention.get("actual_index_deletion_performed") is False
        and all(item.get("actual_operation_performed") is False for item in instructions)
        and _actual_counts_are_zero(report)
        and _all_false(report, tuple(phase4_module.RUNTIME_CLOSED_FIELDS))
    )


def _source_authority_closed(source_authority: Mapping[str, Any]) -> bool:
    authority = source_authority.get("authority")
    return (
        isinstance(authority, str)
        and authority.startswith("FROZEN_STAGE077_TASKPACK")
        and source_authority.get("second_authoritative_source_created") is False
        and source_authority.get("source_body_or_path_allowed") is False
        and source_authority.get("raw_metadata_content_access_allowed") is False
        and source_authority.get("live_source_read_performed") is False
        and source_authority.get("authorized_fixture_access_performed") is False
    )


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        all(
            _source_authority_closed(_mapping(contract.get("source_authority")))
            for contract in (phase1, phase2, phase3, phase4)
        )
        and phase2_report.get("control_output_is_not_actual_index_database_or_retrieval")
        is True
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
        and phase4_report.get("automatic_business_recommendation_allowed") is False
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int]:
    input_output = _mapping(phase1.get("background_build_input_output_contract"))
    lifecycle = _mapping(phase1.get("background_build_lifecycle_contract"))
    smoke = _mapping(phase1.get("smoke_and_atomic_switch_contract"))
    phase1_failures = _mapping(phase1.get("failure_and_stop_contract"))
    phase4_delivery = _mapping(phase4.get("delivery_evidence_contract"))
    phase4_failures = _mapping(phase4.get("failure_and_stop_contract"))
    feedback = _sequence(phase4_report.get("chinese_feedback"))
    return {
        "phase1_input_field_count": _int_field(input_output, "input_field_count"),
        "phase1_output_field_count": _int_field(input_output, "output_field_count"),
        "phase1_lifecycle_state_count": _int_field(lifecycle, "state_count"),
        "phase1_smoke_condition_count": _int_field(smoke, "condition_count"),
        "phase1_failure_state_count": _int_field(phase1_failures, "failure_state_count"),
        "phase2_control_request_count": _int_field(
            phase2_report, "control_request_count"
        ),
        "phase2_index_version_record_count": _int_field(
            phase2_report, "index_version_control_record_count"
        ),
        "phase2_building_version_record_count": _int_field(
            phase2_report, "building_version_control_record_count"
        ),
        "phase2_active_pointer_projection_count": _int_field(
            phase2_report, "active_pointer_control_projection_count"
        ),
        "phase2_background_build_projection_count": _int_field(
            phase2_report, "background_build_output_control_projection_count"
        ),
        "phase2_smoke_test_projection_count": _int_field(
            phase2_report, "smoke_test_control_projection_count"
        ),
        "phase2_switch_projection_count": _int_field(
            phase2_report, "switch_control_projection_count"
        ),
        "phase2_rollback_projection_count": _int_field(
            phase2_report, "rollback_control_projection_count"
        ),
        "phase3_scenario_count": _int_field(phase3_report, "scenario_count"),
        "phase3_scenario_field_count": _int_field(
            phase3_report, "scenario_field_count"
        ),
        "phase3_scenario_field_check_count": _int_field(
            phase3_report, "scenario_field_check_count"
        ),
        "phase3_operations_view_count": _int_field(
            phase3_report, "operations_version_control_view_count"
        ),
        "phase3_report_snapshot_view_count": _int_field(
            phase3_report, "report_snapshot_version_control_view_count"
        ),
        "phase3_human_handling_required_count": _int_field(
            phase3_report, "human_handling_required_count"
        ),
        "phase4_index_manifest_sample_count": _int_field(
            phase4_report, "index_manifest_control_sample_count"
        ),
        "phase4_smoke_log_sample_count": _int_field(
            phase4_report, "smoke_test_log_control_sample_count"
        ),
        "phase4_switch_record_sample_count": _int_field(
            phase4_report, "switch_record_control_sample_count"
        ),
        "phase4_rollback_proof_sample_count": _int_field(
            phase4_report, "rollback_proof_control_sample_count"
        ),
        "phase4_old_index_retention_count": _int_field(
            phase4_report, "old_index_retention_projection_count"
        ),
        "phase4_operational_instruction_count": _int_field(
            phase4_report, "operational_instruction_projection_count"
        ),
        "phase4_chinese_feedback_count": len(feedback),
        "phase4_failure_state_count": _int_field(
            phase4_failures, "failure_state_count"
        ),
        "phase4_delivery_contract_chinese_feedback_count": _int_field(
            phase4_delivery, "chinese_feedback_count"
        ),
    }


def _controlled_replay_is_expected(replay: Mapping[str, int]) -> bool:
    return dict(replay) == {
        "phase1_input_field_count": 6,
        "phase1_output_field_count": 6,
        "phase1_lifecycle_state_count": 7,
        "phase1_smoke_condition_count": 6,
        "phase1_failure_state_count": 8,
        "phase2_control_request_count": 5,
        "phase2_index_version_record_count": 5,
        "phase2_building_version_record_count": 5,
        "phase2_active_pointer_projection_count": 5,
        "phase2_background_build_projection_count": 5,
        "phase2_smoke_test_projection_count": 5,
        "phase2_switch_projection_count": 5,
        "phase2_rollback_projection_count": 5,
        "phase3_scenario_count": 6,
        "phase3_scenario_field_count": 26,
        "phase3_scenario_field_check_count": 156,
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
        "phase4_delivery_contract_chinese_feedback_count": 4,
    }


def _failure_stop_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    phase4_retention = _mapping(phase4_report.get("old_index_retention_projection"))
    phase4_instructions = _mapping_sequence(
        phase4_report.get("operational_instruction_projections")
    )
    return (
        _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        == 8
        and _mapping(phase2.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 7
        and _mapping(phase3.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 13
        and _mapping(phase4.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 13
        and phase2_report.get("all_failed_or_pending_smoke_tests_block_switch")
        is True
        and phase2_report.get("all_switch_projections_keep_active_pointer_unchanged")
        is True
        and phase2_report.get("all_rollback_targets_reference_retained_previous_active")
        is True
        and phase3_report.get("switch_failure_preserved") is True
        and phase3_report.get("rollback_preserved") is True
        and _mapping(phase4.get("rollback_contract")).get("return_to")
        == "PASS_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and phase4_retention.get("space_impact_state")
        == "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED"
        and phase4_retention.get("actual_space_impact_measurement_performed") is False
        and phase4_retention.get("actual_index_deletion_performed") is False
        and len(phase4_instructions) == 3
        and all(
            item.get("actual_operation_performed") is False
            and item.get("human_handling_required") is True
            for item in phase4_instructions
        )
    )


def _delivery_and_whitebox_boundary(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = _mapping_sequence(phase3_report.get("scenario_results"))
    return (
        len(scenarios) == 6
        and all(item.get("human_handling_required") is True for item in scenarios)
        and phase3_report.get("source_document_remains_authoritative") is True
        and phase3_report.get("automatic_business_recommendation_allowed") is False
        and phase4_report.get("delivery_evidence_metadata_only") is True
        and phase4_report.get("all_delivery_references_control_only") is True
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
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
        NEXT_GATE == "IDS-STAGE078-P1-GATE"
        and all(
            _mapping(contract.get("stage_and_phase_boundary")).get(
                "stage078_started"
            )
            is False
            for contract in (phase1, phase2, phase3, phase4)
        )
        and phase3_report.get("stage078_started") is False
        and phase4_report.get("stage078_started") is False
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
    phase3_module: Any,
    phase4_module: Any,
) -> bool:
    return (
        all(
            _all_false_mapping(_mapping(contract.get("runtime_boundary")))
            for contract in (phase1, phase2, phase3, phase4)
        )
        and phase2_report.get("actual_input_request_count") == 0
        and _all_false(phase2_report, tuple(phase3_module.P2_RUNTIME_CLOSED_FIELDS))
        and _actual_counts_are_zero(phase3_report)
        and _all_false(phase3_report, tuple(phase3_module.RUNTIME_CLOSED_FIELDS))
        and _actual_counts_are_zero(phase4_report)
        and _all_false(phase4_report, tuple(phase4_module.RUNTIME_CLOSED_FIELDS))
    )


def _has_expected_counts(report: Mapping[str, Any], expected: Mapping[str, int]) -> bool:
    return all(report.get(field) == count for field, count in expected.items())


def _records_have_exact_shape(
    records: Sequence[Mapping[str, Any]], expected_count: int, fields: Sequence[str]
) -> bool:
    return len(records) == expected_count and all(
        set(record) == set(fields) for record in records
    )


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    records = list(value)
    return records if all(isinstance(record, Mapping) for record in records) else []


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _all_false_mapping(value: Mapping[str, Any]) -> bool:
    return bool(value) and all(item is False for item in value.values())


def _all_false(report: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(report.get(field) is False for field in fields)


def _actual_counts_are_zero(report: Mapping[str, Any]) -> bool:
    return all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _int_field(source: Mapping[str, Any], field: str) -> int:
    value = source.get(field)
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _chinese_feedback(review_valid: bool) -> list[str]:
    if review_valid:
        return [
            "Stage077 的固定控制合同与内存交付证据复审一致，未启动真实后台索引构建。",
            "构建、冒烟、切换、回退、保留和空间影响均保持控制投影；实际服务未变更。",
            "来源文档与业务线白箱人工复核仍是唯一权威，复审结果不形成业务事实或自动建议。",
            "仅开放 Stage078 P1 门禁；Stage078 尚未启动，上传、生产、Agent 与模型 Token 保持关闭。",
        ]
    return [
        "Stage077 复审未通过，后续 Stage078 门禁保持关闭。",
        "请仅修复冻结控制工件或治理投影中的不一致，不读取真实资料或启动运行时。",
        "来源文档与业务线白箱人工复核仍是唯一权威。",
    ]
