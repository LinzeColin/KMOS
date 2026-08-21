"""Stage076 P3 的纯内存索引版本异常场景重放。

模块只重放 Stage076 P2 的固定控制输入与控制投影。它观察失败关闭、旧活动版本
连续服务、回退候选、构建期间检索隔离及版本可见性；不读取业务资料、不操作实际
索引、不执行并发检索，也不写入 Operations 或报告快照。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage076.index_version_schema.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INDEX_VERSION_SCHEMA_SCENARIOS"
PASS_RESULT = "PASS_INDEX_VERSION_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_INDEX_VERSION_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE076-P4-GATE"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_INDEX_VERSION_SCHEMA_CONTROL_SLICE"
P2_SCENARIOS = (
    "fulltext_verified_switch_candidate",
    "vector_building_keeps_active",
    "hybrid_verification_failure_blocks_switch",
    "fulltext_switch_failure_preserves_active",
    "hybrid_rollback_candidate_retains_previous",
)

P2_RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "actual_index_version_record_created",
    "actual_document_scope_recorded",
    "actual_chunk_count_recorded",
    "actual_embedding_model_recorded",
    "actual_bulk_import_detected",
    "actual_index_build_started",
    "actual_building_version_record_created",
    "actual_shadow_index_created",
    "actual_shadow_index_queried",
    "actual_verification_run_performed",
    "actual_verification_result_recorded",
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
)
RUNTIME_CLOSED_FIELDS = (
    *P2_RUNTIME_CLOSED_FIELDS,
    "actual_concurrent_retrieval_performed",
    "actual_operations_display_written",
    "actual_report_snapshot_written",
)

PHASE2_RECORD_SPECS = (
    ("index_version_control_records", "INDEX_VERSION_RECORD_FIELDS"),
    ("building_version_control_records", "BUILDING_VERSION_FIELDS"),
    ("active_pointer_control_projections", "ACTIVE_POINTER_FIELDS"),
    ("verification_control_projections", "VERIFICATION_FIELDS"),
    ("switch_control_projections", "SWITCH_PROJECTION_FIELDS"),
    ("rollback_control_projections", "ROLLBACK_PROJECTION_FIELDS"),
)
OPERATIONS_VIEW_FIELDS = (
    "control_scenario",
    "operations_view_ref",
    "index_kind",
    "index_version_ref",
    "active_index_version_ref",
    "view_state",
)
REPORT_SNAPSHOT_FIELDS = (
    "control_scenario",
    "report_snapshot_ref",
    "index_kind",
    "index_version_ref",
    "active_index_version_ref",
    "snapshot_state",
)
SCENARIO_RESULT_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "referenced_index_version_ref",
    "referenced_active_pointer_ref",
    "referenced_building_version_ref",
    "referenced_verification_ref",
    "referenced_switch_ref",
    "referenced_rollback_ref",
    "referenced_operations_view_ref",
    "referenced_report_snapshot_ref",
    "index_kind",
    "observed_build_state",
    "observed_verification_state",
    "observed_switch_outcome",
    "observed_rollback_state",
    "active_version_before_ref",
    "observed_active_version_after_ref",
    "old_active_continues",
    "concurrent_retrieval_isolated",
    "operations_version_visible",
    "report_snapshot_version_visible",
    "human_handling_required",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)

SCENARIOS = (
    {
        "scenario_id": "build_failure_old_active_continues",
        "scenario_category": "BUILD_FAILURE_OLD_ACTIVE_CONTINUES_CONTROL",
        "phase2_control_scenario": "hybrid_verification_failure_blocks_switch",
        "expected_build_state": "CONTROL_BUILD_FAILED_NOT_STARTED",
        "expected_verification_state": "FAILED",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_VERIFICATION_FAILED",
        "expected_rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_BUILD_FAILURE_BLOCKED_OLD_ACTIVE_CONTINUES",
    },
    {
        "scenario_id": "smoke_validation_failure_blocks_switch",
        "scenario_category": "SMOKE_VALIDATION_FAILURE_BLOCKS_SWITCH_CONTROL",
        "phase2_control_scenario": "hybrid_verification_failure_blocks_switch",
        "expected_build_state": "CONTROL_BUILD_FAILED_NOT_STARTED",
        "expected_verification_state": "FAILED",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_VERIFICATION_FAILED",
        "expected_rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_SMOKE_VALIDATION_FAILURE_BLOCKS_SWITCH",
    },
    {
        "scenario_id": "switch_failure_preserves_active",
        "scenario_category": "SWITCH_FAILURE_PRESERVES_ACTIVE_CONTROL",
        "phase2_control_scenario": "fulltext_switch_failure_preserves_active",
        "expected_build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "expected_verification_state": "PASSED",
        "expected_switch_outcome": "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "expected_rollback_state": "CONTROL_ROLLBACK_CANDIDATE_PREVIOUS_ACTIVE_RETAINED",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_SWITCH_FAILURE_ACTIVE_VERSION_UNCHANGED",
    },
    {
        "scenario_id": "rollback_retains_previous_active",
        "scenario_category": "ROLLBACK_RETAINS_PREVIOUS_ACTIVE_CONTROL",
        "phase2_control_scenario": "hybrid_rollback_candidate_retains_previous",
        "expected_build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "expected_verification_state": "PASSED",
        "expected_switch_outcome": "CONTROL_ROLLBACK_PROJECTED_NOT_APPLIED",
        "expected_rollback_state": "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_ROLLBACK_TARGET_IS_RETAINED_PREVIOUS_ACTIVE",
    },
    {
        "scenario_id": "background_build_concurrent_retrieval_isolated",
        "scenario_category": "BACKGROUND_BUILD_CONCURRENT_RETRIEVAL_ISOLATION_CONTROL",
        "phase2_control_scenario": "vector_building_keeps_active",
        "expected_build_state": "CONTROL_BUILDING_NOT_STARTED",
        "expected_verification_state": "PENDING",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILDING",
        "expected_rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "expected_concurrent_retrieval_isolated": True,
        "explicit_disposition": "CONTROL_BACKGROUND_BUILD_LEAVES_OLD_ACTIVE_FOR_RETRIEVAL",
    },
    {
        "scenario_id": "operations_and_report_snapshot_version_visibility",
        "scenario_category": "OPERATIONS_AND_REPORT_SNAPSHOT_VERSION_VISIBILITY_CONTROL",
        "phase2_control_scenario": "fulltext_verified_switch_candidate",
        "expected_build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "expected_verification_state": "PASSED",
        "expected_switch_outcome": "CONTROL_ATOMIC_SWITCH_PROJECTED_NOT_APPLIED",
        "expected_rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_VERSION_VISIBLE_IN_OPERATIONS_AND_REPORT_SNAPSHOT",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_index_version_schema_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2，并在内存中评估固定的 Stage076 P3 控制场景。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    raw_phase2_result = executor(_phase2_control_input(phase2_module))
    phase2_result = raw_phase2_result if isinstance(raw_phase2_result, Mapping) else {}
    phase2_shape_preserved = _phase2_shape_preserved(phase2_module, phase2_result)
    phase2_side_effect_free = _phase2_side_effect_free(phase2_result)

    operations_views = _build_operations_views(phase2_result) if phase2_shape_preserved else []
    report_snapshot_views = (
        _build_report_snapshot_views(phase2_result) if phase2_shape_preserved else []
    )
    control_views_preserved = _control_views_preserved(
        operations_views, report_snapshot_views
    )
    scenario_results = [
        _evaluate_scenario(
            scenario,
            phase2_result,
            operations_views,
            report_snapshot_views,
            phase2_side_effect_free,
        )
        for scenario in SCENARIOS
    ]
    runtime_closed_flags = _runtime_closed_flags()
    no_runtime_performed = all(
        runtime_closed_flags[field] is False for field in RUNTIME_CLOSED_FIELDS
    )
    category_order_preserved = [
        result["scenario_category"] for result in scenario_results
    ] == [scenario["scenario_category"] for scenario in SCENARIOS]
    all_control_references_opaque = all(
        _scenario_references_are_control_only(result) for result in scenario_results
    )
    build_failure_preserved = _scenario_expectation(
        scenario_results, "build_failure_old_active_continues"
    )
    smoke_validation_failure_preserved = _scenario_expectation(
        scenario_results, "smoke_validation_failure_blocks_switch"
    )
    switch_failure_preserved = _scenario_expectation(
        scenario_results, "switch_failure_preserves_active"
    )
    rollback_preserved = _scenario_expectation(
        scenario_results, "rollback_retains_previous_active"
    )
    concurrent_retrieval_isolation_preserved = _scenario_expectation(
        scenario_results, "background_build_concurrent_retrieval_isolated"
    )
    visibility_preserved = _scenario_expectation(
        scenario_results, "operations_and_report_snapshot_version_visibility"
    )
    valid = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and control_views_preserved
        and len(scenario_results) == len(SCENARIOS)
        and category_order_preserved
        and all(result["expectation_met"] for result in scenario_results)
        and not any(result["silent_drop"] for result in scenario_results)
        and all_control_references_opaque
        and build_failure_preserved
        and smoke_validation_failure_preserved
        and switch_failure_preserved
        and rollback_preserved
        and concurrent_retrieval_isolation_preserved
        and visibility_preserved
        and no_runtime_performed
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "valid": valid,
        "next_gate": NEXT_GATE,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "phase2_side_effect_free": phase2_side_effect_free,
        "phase2_control_record_field_check_count": _phase2_field_check_count(
            phase2_module, phase2_result
        ),
        "control_scenario_order": list(P2_SCENARIOS),
        "scenario_results": scenario_results,
        "scenario_count": len(scenario_results),
        "scenario_field_count": len(SCENARIO_RESULT_FIELDS),
        "scenario_field_check_count": len(scenario_results) * len(SCENARIO_RESULT_FIELDS),
        "passed_scenario_count": sum(
            1 for result in scenario_results if result["expectation_met"]
        ),
        "explicit_disposition_count": sum(
            1 for result in scenario_results if result["explicit_disposition"]
        ),
        "silent_drop_count": sum(
            1 for result in scenario_results if result["silent_drop"]
        ),
        "human_handling_required_count": sum(
            1 for result in scenario_results if result["human_handling_required"]
        ),
        "operations_version_control_views": operations_views,
        "operations_version_control_view_count": len(operations_views),
        "report_snapshot_version_control_views": report_snapshot_views,
        "report_snapshot_version_control_view_count": len(report_snapshot_views),
        "control_views_preserved": control_views_preserved,
        "build_failure_preserved": build_failure_preserved,
        "smoke_validation_failure_preserved": smoke_validation_failure_preserved,
        "switch_failure_preserved": switch_failure_preserved,
        "rollback_preserved": rollback_preserved,
        "concurrent_retrieval_isolation_preserved": concurrent_retrieval_isolation_preserved,
        "operations_and_report_snapshot_visibility_preserved": visibility_preserved,
        "all_control_references_opaque": all_control_references_opaque,
        "actual_input_request_count": 0,
        "actual_index_build_count": 0,
        "actual_retrieval_query_count": 0,
        "actual_index_rollback_count": 0,
        "actual_operations_display_count": 0,
        "actual_report_snapshot_count": 0,
        "source_document_remains_authoritative": True,
        "control_scenario_can_replace_source_document": False,
        "control_view_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "stage075_review_evidence_read": True,
        "stage076_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "stage077_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本次只重放固定控制引用，未构建、查询、切换或持久化实际索引。",
            "构建失败、验证失败或切换失败均保持旧活动版本继续服务。",
            "构建期间检索隔离只在控制投影中核验，未执行实际并发检索。",
            "Operations 和报告快照仅显示不透明控制版本引用，仍需业务线白箱人工处理。",
        ],
    }


def _phase2_executor(phase2_module: Any) -> Phase2Executor:
    return phase2_module.execute_index_version_schema_control_slice


def _phase2_control_input(phase2_module: Any) -> Mapping[str, object]:
    return phase2_module.build_control_input()


def _load_phase2_module() -> Any:
    path = Path(__file__).with_name("stage076_index_version_schema_slice.py")
    spec = importlib.util.spec_from_file_location("stage076_phase2_slice", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage076 P2 index version schema slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_shape_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("control_scenarios_covered") != list(P2_SCENARIOS)
        or result.get("control_request_count") != len(P2_SCENARIOS)
        or result.get("actual_input_request_count") != 0
        or result.get("all_control_records_keep_required_shapes") is not True
    ):
        return False
    for record_key, field_name in PHASE2_RECORD_SPECS:
        fields = _field_tuple(phase2_module, field_name)
        if not _records_have_exact_shape(
            result.get(record_key), len(P2_SCENARIOS), fields
        ):
            return False
    return all(
        _record_references_are_control_only(record)
        for record_key, _field_name in PHASE2_RECORD_SPECS
        for record in _as_records(result.get(record_key))
    )


def _phase2_side_effect_free(result: Mapping[str, Any]) -> bool:
    return (
        all(result.get(field) is False for field in P2_RUNTIME_CLOSED_FIELDS)
        and result.get("control_output_is_not_actual_index_database_or_retrieval")
        is True
    )


def _build_operations_views(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _build_control_views(
        result,
        ref_field="operations_view_ref",
        state_field="view_state",
        state_value="CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
    )


def _build_report_snapshot_views(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _build_control_views(
        result,
        ref_field="report_snapshot_ref",
        state_field="snapshot_state",
        state_value="CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
    )


def _build_control_views(
    result: Mapping[str, Any],
    *,
    ref_field: str,
    state_field: str,
    state_value: str,
) -> list[dict[str, Any]]:
    records = _as_records(result.get("index_version_control_records"))
    pointers = _as_records(result.get("active_pointer_control_projections"))
    if len(records) != len(P2_SCENARIOS) or len(pointers) != len(P2_SCENARIOS):
        return []
    projections: list[dict[str, Any]] = []
    for scenario, record, pointer in zip(P2_SCENARIOS, records, pointers):
        marker = f":control:stage076-p2:{scenario}"
        projections.append(
            {
                "control_scenario": scenario,
                ref_field: f"{ref_field.replace('_ref', '')}{marker}",
                "index_kind": record.get("index_kind"),
                "index_version_ref": record.get("index_version"),
                "active_index_version_ref": pointer.get("active_index_version_ref"),
                state_field: state_value,
            }
        )
    return projections


def _control_views_preserved(
    operations_views: Sequence[Mapping[str, Any]],
    report_snapshot_views: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        _records_have_exact_shape(
            operations_views, len(P2_SCENARIOS), OPERATIONS_VIEW_FIELDS
        )
        and _records_have_exact_shape(
            report_snapshot_views, len(P2_SCENARIOS), REPORT_SNAPSHOT_FIELDS
        )
        and all(_record_references_are_control_only(view) for view in operations_views)
        and all(_record_references_are_control_only(view) for view in report_snapshot_views)
        and all(
            view.get("view_state")
            == "CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN"
            for view in operations_views
        )
        and all(
            view.get("snapshot_state")
            == "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN"
            for view in report_snapshot_views
        )
    )


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    result: Mapping[str, Any],
    operations_views: Sequence[Mapping[str, Any]],
    report_snapshot_views: Sequence[Mapping[str, Any]],
    phase2_side_effect_free: bool,
) -> dict[str, Any]:
    scenario_name = str(scenario["phase2_control_scenario"])
    index = P2_SCENARIOS.index(scenario_name)
    index_record = _record_at(result.get("index_version_control_records"), index)
    building = _record_at(result.get("building_version_control_records"), index)
    pointer = _record_at(result.get("active_pointer_control_projections"), index)
    verification = _record_at(result.get("verification_control_projections"), index)
    switch = _record_at(result.get("switch_control_projections"), index)
    rollback = _record_at(result.get("rollback_control_projections"), index)
    operations_view = _record_at(operations_views, index)
    report_snapshot_view = _record_at(report_snapshot_views, index)

    active_before = pointer.get("active_index_version_ref")
    active_after = switch.get("resulting_active_index_version_ref")
    old_active_continues = (
        pointer.get("pointer_state")
        == "CONTROL_ACTIVE_POINTER_UNCHANGED_RUNTIME_DISABLED"
        and switch.get("active_service_continues") is True
        and switch.get("switch_applied") is False
        and active_after == active_before
    )
    concurrent_retrieval_isolated = (
        scenario["expected_concurrent_retrieval_isolated"] is True
        and building.get("build_state") == "CONTROL_BUILDING_NOT_STARTED"
        and old_active_continues
        and result.get("all_active_versions_continue_serving_during_control_build")
        is True
        and result.get("actual_retrieval_query_performed") is False
    )
    operations_version_visible = _view_visible(
        operations_view,
        OPERATIONS_VIEW_FIELDS,
        "operations_view_ref",
        "CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
        "view_state",
        index_record,
        pointer,
    )
    report_snapshot_version_visible = _view_visible(
        report_snapshot_view,
        REPORT_SNAPSHOT_FIELDS,
        "report_snapshot_ref",
        "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
        "snapshot_state",
        index_record,
        pointer,
    )
    rollback_target_preserved = (
        rollback.get("rollback_target_index_version_ref")
        == rollback.get("previous_active_index_version_ref")
        and rollback.get("rollback_applied") is False
    )
    expectation_met = (
        phase2_side_effect_free
        and index_record.get("index_kind") == building.get("index_kind")
        and index_record.get("index_kind") == pointer.get("index_kind")
        and building.get("build_state") == scenario["expected_build_state"]
        and verification.get("verification_state")
        == scenario["expected_verification_state"]
        and switch.get("switch_outcome") == scenario["expected_switch_outcome"]
        and rollback.get("rollback_state") == scenario["expected_rollback_state"]
        and old_active_continues
        and concurrent_retrieval_isolated
        == scenario["expected_concurrent_retrieval_isolated"]
        and operations_version_visible
        and report_snapshot_version_visible
        and rollback_target_preserved
        and bool(scenario["explicit_disposition"])
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "phase2_control_scenario": scenario_name,
        "referenced_index_version_ref": index_record.get("index_version"),
        "referenced_active_pointer_ref": pointer.get("switch_record_ref"),
        "referenced_building_version_ref": building.get("building_index_version_ref"),
        "referenced_verification_ref": verification.get("verification_ref"),
        "referenced_switch_ref": switch.get("switch_record_ref"),
        "referenced_rollback_ref": rollback.get("rollback_record_ref"),
        "referenced_operations_view_ref": operations_view.get("operations_view_ref"),
        "referenced_report_snapshot_ref": report_snapshot_view.get(
            "report_snapshot_ref"
        ),
        "index_kind": index_record.get("index_kind"),
        "observed_build_state": building.get("build_state"),
        "observed_verification_state": verification.get("verification_state"),
        "observed_switch_outcome": switch.get("switch_outcome"),
        "observed_rollback_state": rollback.get("rollback_state"),
        "active_version_before_ref": active_before,
        "observed_active_version_after_ref": active_after,
        "old_active_continues": old_active_continues,
        "concurrent_retrieval_isolated": concurrent_retrieval_isolated,
        "operations_version_visible": operations_version_visible,
        "report_snapshot_version_visible": report_snapshot_version_visible,
        "human_handling_required": True,
        "explicit_disposition": scenario["explicit_disposition"],
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _view_visible(
    view: Mapping[str, Any],
    expected_fields: Sequence[str],
    ref_field: str,
    expected_state: str,
    state_field: str,
    index_record: Mapping[str, Any],
    pointer: Mapping[str, Any],
) -> bool:
    return (
        set(view) == set(expected_fields)
        and isinstance(view.get(ref_field), str)
        and ":control:stage076-p2:" in view[ref_field]
        and view.get(state_field) == expected_state
        and view.get("index_kind") == index_record.get("index_kind")
        and view.get("index_version_ref") == index_record.get("index_version")
        and view.get("active_index_version_ref")
        == pointer.get("active_index_version_ref")
    )


def _scenario_expectation(
    results: Sequence[Mapping[str, Any]], scenario_id: str
) -> bool:
    return any(
        result.get("scenario_id") == scenario_id
        and result.get("expectation_met") is True
        for result in results
    )


def _scenario_references_are_control_only(result: Mapping[str, Any]) -> bool:
    reference_fields = tuple(
        field for field in SCENARIO_RESULT_FIELDS if field.startswith("referenced_")
    ) + ("active_version_before_ref", "observed_active_version_after_ref")
    return all(
        isinstance(result.get(field), str)
        and ":control:stage076-p2:" in result[field]
        for field in reference_fields
    )


def _record_references_are_control_only(record: Mapping[str, Any]) -> bool:
    reference_fields = tuple(
        field
        for field in record
        if field.endswith("_ref") or field == "index_version"
    )
    return all(
        isinstance(record.get(field), str) and ":control:stage076-p2:" in record[field]
        for field in reference_fields
    )


def _phase2_field_check_count(phase2_module: Any, result: Mapping[str, Any]) -> int:
    return sum(
        len(_as_records(result.get(record_key))) * len(_field_tuple(phase2_module, field_name))
        for record_key, field_name in PHASE2_RECORD_SPECS
    )


def _field_tuple(module: Any, field_name: str) -> tuple[str, ...]:
    fields = getattr(module, field_name, ())
    return (
        fields
        if isinstance(fields, tuple)
        and all(isinstance(field, str) for field in fields)
        else ()
    )


def _records_have_exact_shape(
    records: object, expected_count: int, fields: Sequence[str]
) -> bool:
    return (
        isinstance(records, Sequence)
        and not isinstance(records, (str, bytes))
        and len(records) == expected_count
        and all(
            isinstance(record, Mapping) and set(record) == set(fields)
            for record in records
        )
    )


def _as_records(records: object) -> list[Mapping[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _record_at(records: object, index: int) -> Mapping[str, Any]:
    if (
        isinstance(records, Sequence)
        and not isinstance(records, (str, bytes))
        and 0 <= index < len(records)
        and isinstance(records[index], Mapping)
    ):
        return records[index]
    return {}


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
