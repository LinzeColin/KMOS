"""Stage082 P3 的纯内存旧索引保留策略受控场景重放。

模块只重放 Stage082 P2 的固定控制输入与控制投影，用于核验构建／冒烟／切换
失败、未设值回滚窗口、旧活动版本连续服务、后台构建检索隔离及版本可见性。
它不读取业务资料，不创建或查询真实索引，不执行并发检索，也不写入
Operations 或报告快照。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage082.old_index_retention.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_OLD_INDEX_RETENTION_SCENARIOS"
PASS_RESULT = "PASS_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE082-P4-GATE"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_OLD_INDEX_RETENTION_CONTROL_SLICE"
P2_SCENARIOS = (
    "fulltext_smoke_passed_retention_unconfigured_switch_candidate",
    "vector_background_build_incomplete_preserves_active",
    "hybrid_shadow_smoke_failure_blocks_switch",
    "fulltext_atomic_switch_failure_preserves_active",
    "hybrid_retained_previous_rollback_window_unconfigured",
)

P2_RUNTIME_CLOSED_FIELDS = (
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
RUNTIME_CLOSED_FIELDS = (
    *P2_RUNTIME_CLOSED_FIELDS,
    "actual_operations_display_written",
    "actual_report_snapshot_written",
)

PHASE2_RECORD_SPECS = (
    ("index_version_control_records", "INDEX_VERSION_RECORD_FIELDS"),
    ("building_and_shadow_control_projections", "BUILDING_AND_SHADOW_FIELDS"),
    ("active_pointer_control_projections", "ACTIVE_POINTER_FIELDS"),
    ("smoke_test_input_control_projections", "SMOKE_TEST_INPUT_FIELDS"),
    ("smoke_test_output_control_projections", "SMOKE_TEST_OUTPUT_FIELDS"),
    ("switch_control_projections", "SWITCH_PROJECTION_FIELDS"),
    ("rollback_request_control_projections", "ROLLBACK_REQUEST_FIELDS"),
    ("retention_policy_control_projections", "RETENTION_POLICY_FIELDS"),
    ("cleanup_eligibility_control_projections", "CLEANUP_ELIGIBILITY_FIELDS"),
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
    "referenced_candidate_index_version_ref",
    "referenced_shadow_index_ref",
    "referenced_smoke_test_ref",
    "referenced_switch_ref",
    "referenced_rollback_request_ref",
    "referenced_retention_policy_ref",
    "referenced_cleanup_eligibility_ref",
    "referenced_operations_view_ref",
    "referenced_report_snapshot_ref",
    "index_kind",
    "observed_build_state",
    "observed_smoke_test_status",
    "observed_switch_outcome",
    "observed_rollback_eligibility",
    "observed_cleanup_eligibility",
    "active_version_before_ref",
    "observed_active_version_after_ref",
    "rollback_target_is_retained_previous_active",
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
        "scenario_id": "build_not_complete_old_active_continues",
        "scenario_category": "BUILD_NOT_COMPLETE_OLD_ACTIVE_CONTINUES_CONTROL",
        "phase2_control_scenario": "vector_background_build_incomplete_preserves_active",
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_INCOMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "NOT_RUN",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_BUILD_NOT_COMPLETE_BLOCKED_OLD_ACTIVE_CONTINUES",
    },
    {
        "scenario_id": "smoke_test_failure_blocks_switch",
        "scenario_category": "SHADOW_SMOKE_TEST_FAILURE_BLOCKS_SWITCH_CONTROL",
        "phase2_control_scenario": "hybrid_shadow_smoke_failure_blocks_switch",
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_COMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "FAILED",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_SHADOW_SMOKE_TEST_FAILED",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_SHADOW_SMOKE_TEST_FAILURE_BLOCKS_SWITCH",
    },
    {
        "scenario_id": "switch_failure_preserves_active",
        "scenario_category": "ATOMIC_SWITCH_FAILURE_PRESERVES_ACTIVE_CONTROL",
        "phase2_control_scenario": "fulltext_atomic_switch_failure_preserves_active",
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_COMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "PASSED",
        "expected_switch_outcome": "CONTROL_ATOMIC_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_ATOMIC_SWITCH_FAILURE_ACTIVE_VERSION_UNCHANGED",
    },
    {
        "scenario_id": "rollback_window_unconfigured_preserves_previous_active",
        "scenario_category": "ROLLBACK_WINDOW_UNCONFIGURED_RETAINS_PREVIOUS_ACTIVE_CONTROL",
        "phase2_control_scenario": "hybrid_retained_previous_rollback_window_unconfigured",
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_COMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "PASSED",
        "expected_switch_outcome": "CONTROL_ROLLBACK_CANDIDATE_NOT_APPLIED",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_ROLLBACK_BLOCKED_WINDOW_UNCONFIGURED_RETAINED_PREVIOUS_ACTIVE",
    },
    {
        "scenario_id": "background_build_concurrent_retrieval_isolated",
        "scenario_category": "BACKGROUND_BUILD_CONCURRENT_RETRIEVAL_ISOLATION_CONTROL",
        "phase2_control_scenario": "vector_background_build_incomplete_preserves_active",
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_INCOMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "NOT_RUN",
        "expected_switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": True,
        "explicit_disposition": "CONTROL_BACKGROUND_BUILD_ISOLATION_LEAVES_OLD_ACTIVE_FOR_RETRIEVAL",
    },
    {
        "scenario_id": "operations_and_report_snapshot_version_visibility",
        "scenario_category": "OPERATIONS_AND_REPORT_SNAPSHOT_VERSION_VISIBILITY_CONTROL",
        "phase2_control_scenario": (
            "fulltext_smoke_passed_retention_unconfigured_switch_candidate"
        ),
        "expected_build_state": "CONTROL_BACKGROUND_BUILD_COMPLETE_REFERENCE_ONLY",
        "expected_smoke_test_status": "PASSED",
        "expected_switch_outcome": "CONTROL_ATOMIC_SWITCH_CANDIDATE_NOT_APPLIED",
        "expected_rollback_eligibility": "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
        "expected_cleanup_eligibility": "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
        "expected_concurrent_retrieval_isolated": False,
        "explicit_disposition": "CONTROL_VERSION_VISIBLE_IN_OPERATIONS_AND_REPORT_SNAPSHOT",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_old_index_retention_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2，并在内存中评估固定的 Stage082 P3 控制场景。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    raw_phase2_result = executor(_phase2_control_input(phase2_module))
    phase2_result = raw_phase2_result if isinstance(raw_phase2_result, Mapping) else {}
    phase2_shape_preserved = _phase2_shape_preserved(phase2_module, phase2_result)
    phase2_side_effect_free = _phase2_side_effect_free(phase2_result, phase2_module)
    phase2_records = (
        _index_phase2_records(phase2_result) if phase2_shape_preserved else {}
    )
    operations_views = (
        _build_operations_views(phase2_records) if phase2_shape_preserved else []
    )
    report_snapshot_views = (
        _build_report_snapshot_views(phase2_records)
        if phase2_shape_preserved
        else []
    )
    operations_views_by_scenario = {
        item["control_scenario"]: item for item in operations_views
    }
    report_snapshot_views_by_scenario = {
        item["control_scenario"]: item for item in report_snapshot_views
    }
    control_views_preserved = _control_views_preserved(
        operations_views, report_snapshot_views
    )
    scenario_results = [
        _evaluate_scenario(
            scenario,
            phase2_records,
            operations_views_by_scenario,
            report_snapshot_views_by_scenario,
            phase2_result,
            phase2_shape_preserved,
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
    build_not_complete_preserved = _scenario_expectation(
        scenario_results, "build_not_complete_old_active_continues"
    )
    smoke_test_failure_preserved = _scenario_expectation(
        scenario_results, "smoke_test_failure_blocks_switch"
    )
    switch_failure_preserved = _scenario_expectation(
        scenario_results, "switch_failure_preserves_active"
    )
    rollback_window_unconfigured_preserved = _scenario_expectation(
        scenario_results, "rollback_window_unconfigured_preserves_previous_active"
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
        and build_not_complete_preserved
        and smoke_test_failure_preserved
        and switch_failure_preserved
        and rollback_window_unconfigured_preserved
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
        "scenario_field_check_count": len(scenario_results)
        * len(SCENARIO_RESULT_FIELDS),
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
        "build_not_complete_preserved": build_not_complete_preserved,
        "smoke_test_failure_preserved": smoke_test_failure_preserved,
        "switch_failure_preserved": switch_failure_preserved,
        "rollback_window_unconfigured_preserved": (
            rollback_window_unconfigured_preserved
        ),
        "concurrent_retrieval_isolation_preserved": concurrent_retrieval_isolation_preserved,
        "operations_and_report_snapshot_visibility_preserved": visibility_preserved,
        "all_control_references_opaque": all_control_references_opaque,
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
        "source_document_remains_authoritative": True,
        "control_scenario_can_replace_source_document": False,
        "control_view_can_become_business_fact_authority": False,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_business_recommendation_allowed": False,
        "stage081_review_evidence_declared": True,
        "stage082_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "stage083_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本次只重放固定控制引用，未构建、查询、切换、回滚或清理实际索引。",
            "候选构建未完成、影子冒烟失败或切换失败均保持旧活动版本继续服务。",
            "后台构建期间检索隔离只在控制投影中核验，未执行实际并发检索。",
            "Operations 和报告快照仅显示不透明控制版本引用，仍需业务线白箱人工处理。",
        ],
    }


def _phase2_executor(phase2_module: Any) -> Phase2Executor:
    return phase2_module.execute_old_index_retention_control_slice


def _phase2_control_input(phase2_module: Any) -> Mapping[str, object]:
    return phase2_module.build_control_input()


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage082_old_index_retention_control_slice.py")
    spec = importlib.util.spec_from_file_location("stage082_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage082 P2 old-index retention slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_shape_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("expected_control_request_count") != len(P2_SCENARIOS)
        or result.get("received_control_request_count") != len(P2_SCENARIOS)
        or result.get("actual_input_request_count") != 0
    ):
        return False
    for output_key, field_constant in PHASE2_RECORD_SPECS:
        records = result.get(output_key)
        expected_fields = getattr(phase2_module, field_constant)
        if (
            not isinstance(records, list)
            or len(records) != len(P2_SCENARIOS)
            or any(
                not isinstance(record, Mapping)
                or set(record) != set(expected_fields)
                for record in records
            )
        ):
            return False
    return all(
        result.get(field) is True
        for field in (
            "all_candidate_versions_are_isolated",
            "all_old_active_versions_continue_serving",
            "all_active_pointer_projections_unchanged",
            "all_minimum_previous_active_versions_retained",
            "all_rollback_targets_reference_retained_previous_active",
            "all_cleanup_projections_fail_closed",
        )
    )


def _phase2_side_effect_free(result: Mapping[str, Any], phase2_module: Any) -> bool:
    return (
        all(result.get(field) is False for field in phase2_module.RUNTIME_CLOSED_FIELDS)
        and result.get("business_line_whitebox_human_approval_recorded") is False
        and result.get("automatic_business_write_allowed") is False
        and result.get("automatic_active_pointer_switch_allowed") is False
        and result.get("automatic_rollback_allowed") is False
        and result.get("automatic_old_index_cleanup_allowed") is False
    )


def _phase2_field_check_count(phase2_module: Any, result: Mapping[str, Any]) -> int:
    if not _phase2_shape_preserved(phase2_module, result):
        return 0
    return sum(
        len(getattr(phase2_module, field_constant)) * len(result[output_key])
        for output_key, field_constant in PHASE2_RECORD_SPECS
    )


def _index_phase2_records(
    result: Mapping[str, Any],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    output_keys = {
        "index": "index_version_control_records",
        "build": "building_and_shadow_control_projections",
        "pointer": "active_pointer_control_projections",
        "smoke": "smoke_test_output_control_projections",
        "switch": "switch_control_projections",
        "rollback": "rollback_request_control_projections",
        "retention": "retention_policy_control_projections",
        "cleanup": "cleanup_eligibility_control_projections",
    }
    return {
        scenario: {
            record_name: result[output_key][index]
            for record_name, output_key in output_keys.items()
        }
        for index, scenario in enumerate(P2_SCENARIOS)
    }


def _build_operations_views(
    phase2_records: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        {
            "control_scenario": scenario,
            "operations_view_ref": f"operations-view:control:stage082-p2:{scenario}",
            "index_kind": records["index"]["index_kind"],
            "index_version_ref": records["index"]["index_version"],
            "active_index_version_ref": records["pointer"]["active_index_version_ref"],
            "view_state": "CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
        }
        for scenario, records in phase2_records.items()
    ]


def _build_report_snapshot_views(
    phase2_records: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        {
            "control_scenario": scenario,
            "report_snapshot_ref": (
                f"report-snapshot:control:stage082-p2:{scenario}"
            ),
            "index_kind": records["index"]["index_kind"],
            "index_version_ref": records["index"]["index_version"],
            "active_index_version_ref": records["pointer"]["active_index_version_ref"],
            "snapshot_state": "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
        }
        for scenario, records in phase2_records.items()
    ]


def _control_views_preserved(
    operations_views: list[Mapping[str, Any]],
    report_snapshot_views: list[Mapping[str, Any]],
) -> bool:
    return (
        len(operations_views) == len(P2_SCENARIOS)
        and len(report_snapshot_views) == len(P2_SCENARIOS)
        and all(set(view) == set(OPERATIONS_VIEW_FIELDS) for view in operations_views)
        and all(
            set(view) == set(REPORT_SNAPSHOT_FIELDS) for view in report_snapshot_views
        )
        and all(
            ":control:stage082-p2:" in view["operations_view_ref"]
            for view in operations_views
        )
        and all(
            ":control:stage082-p2:" in view["report_snapshot_ref"]
            for view in report_snapshot_views
        )
    )


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    phase2_records: Mapping[str, Mapping[str, Mapping[str, Any]]],
    operations_views: Mapping[str, Mapping[str, Any]],
    report_snapshot_views: Mapping[str, Mapping[str, Any]],
    phase2_result: Mapping[str, Any],
    phase2_shape_preserved: bool,
    phase2_side_effect_free: bool,
) -> dict[str, Any]:
    phase2_scenario = scenario["phase2_control_scenario"]
    records = phase2_records.get(phase2_scenario, {})
    index = records.get("index", {})
    build = records.get("build", {})
    pointer = records.get("pointer", {})
    smoke = records.get("smoke", {})
    switch = records.get("switch", {})
    rollback = records.get("rollback", {})
    retention = records.get("retention", {})
    cleanup = records.get("cleanup", {})
    operations_view = operations_views.get(phase2_scenario, {})
    report_snapshot_view = report_snapshot_views.get(phase2_scenario, {})

    active_before = _text(pointer, "active_index_version_ref")
    active_after = _text(switch, "resulting_active_index_version_ref")
    rollback_target_retained = (
        _text(rollback, "previous_active_index_version_ref")
        == _text(retention, "previous_active_index_version_ref")
        and _text(rollback, "previous_active_index_version_ref") != active_before
        and retention.get("minimum_retained_previous_active_version_count") == 1
        and phase2_result.get("all_rollback_targets_reference_retained_previous_active")
        is True
    )
    old_active_continues = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and bool(active_before)
        and active_before == active_after
        and phase2_result.get("all_old_active_versions_continue_serving") is True
    )
    concurrent_retrieval_isolated = (
        scenario["expected_concurrent_retrieval_isolated"]
        and old_active_continues
        and phase2_result.get("retrieval_query_performed") is False
        and phase2_result.get("concurrent_retrieval_performed") is False
    )
    operations_version_visible = (
        _text(operations_view, "view_state")
        == "CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN"
        and _text(operations_view, "index_version_ref") == _text(index, "index_version")
        and _text(operations_view, "active_index_version_ref") == active_before
    )
    report_snapshot_version_visible = (
        _text(report_snapshot_view, "snapshot_state")
        == "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN"
        and _text(report_snapshot_view, "index_version_ref") == _text(index, "index_version")
        and _text(report_snapshot_view, "active_index_version_ref") == active_before
    )
    human_handling_required = phase2_shape_preserved and phase2_side_effect_free
    observed_build_state = _text(build, "build_state")
    observed_smoke_test_status = _text(smoke, "smoke_test_status")
    observed_switch_outcome = _text(switch, "switch_outcome")
    observed_rollback_eligibility = _text(rollback, "rollback_eligibility")
    observed_cleanup_eligibility = _text(cleanup, "cleanup_eligibility")
    expectation_met = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and observed_build_state == scenario["expected_build_state"]
        and observed_smoke_test_status == scenario["expected_smoke_test_status"]
        and observed_switch_outcome == scenario["expected_switch_outcome"]
        and observed_rollback_eligibility == scenario["expected_rollback_eligibility"]
        and observed_cleanup_eligibility == scenario["expected_cleanup_eligibility"]
        and old_active_continues
        and rollback_target_retained
        and concurrent_retrieval_isolated
        == scenario["expected_concurrent_retrieval_isolated"]
        and operations_version_visible
        and report_snapshot_version_visible
        and human_handling_required
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "phase2_control_scenario": phase2_scenario,
        "referenced_index_version_ref": _text(index, "index_version"),
        "referenced_active_pointer_ref": _text(pointer, "switch_record_ref"),
        "referenced_candidate_index_version_ref": _text(
            build, "candidate_index_version_ref"
        ),
        "referenced_shadow_index_ref": _text(build, "shadow_index_ref"),
        "referenced_smoke_test_ref": _text(smoke, "smoke_test_ref"),
        "referenced_switch_ref": _text(switch, "switch_record_ref"),
        "referenced_rollback_request_ref": _text(rollback, "rollback_request_ref"),
        "referenced_retention_policy_ref": _text(retention, "retention_policy_ref"),
        "referenced_cleanup_eligibility_ref": _text(
            cleanup, "retention_policy_ref"
        ),
        "referenced_operations_view_ref": _text(operations_view, "operations_view_ref"),
        "referenced_report_snapshot_ref": _text(
            report_snapshot_view, "report_snapshot_ref"
        ),
        "index_kind": _text(index, "index_kind"),
        "observed_build_state": observed_build_state,
        "observed_smoke_test_status": observed_smoke_test_status,
        "observed_switch_outcome": observed_switch_outcome,
        "observed_rollback_eligibility": observed_rollback_eligibility,
        "observed_cleanup_eligibility": observed_cleanup_eligibility,
        "active_version_before_ref": active_before,
        "observed_active_version_after_ref": active_after,
        "rollback_target_is_retained_previous_active": rollback_target_retained,
        "old_active_continues": old_active_continues,
        "concurrent_retrieval_isolated": concurrent_retrieval_isolated,
        "operations_version_visible": operations_version_visible,
        "report_snapshot_version_visible": report_snapshot_version_visible,
        "human_handling_required": human_handling_required,
        "explicit_disposition": (
            scenario["explicit_disposition"] if human_handling_required else ""
        ),
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _text(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    return value if isinstance(value, str) else ""


def _scenario_references_are_control_only(result: Mapping[str, Any]) -> bool:
    reference_fields = (
        "referenced_index_version_ref",
        "referenced_active_pointer_ref",
        "referenced_candidate_index_version_ref",
        "referenced_shadow_index_ref",
        "referenced_smoke_test_ref",
        "referenced_switch_ref",
        "referenced_rollback_request_ref",
        "referenced_retention_policy_ref",
        "referenced_cleanup_eligibility_ref",
        "referenced_operations_view_ref",
        "referenced_report_snapshot_ref",
        "active_version_before_ref",
        "observed_active_version_after_ref",
    )
    return all(
        ":control:stage082-p2:" in _text(result, field) for field in reference_fields
    )


def _scenario_expectation(
    scenario_results: list[Mapping[str, Any]], scenario_id: str
) -> bool:
    return any(
        result["scenario_id"] == scenario_id and result["expectation_met"]
        for result in scenario_results
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
