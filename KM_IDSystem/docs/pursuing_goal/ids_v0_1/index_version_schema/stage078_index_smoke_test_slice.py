"""Stage078 P2 的纯内存索引冒烟测试控制切片。

模块只接受五条固定、非业务、reference-only 控制请求，并在内存中投影
索引版本、候选构建、影子隔离、冒烟门、活动指针、未来原子切换候选与
回退候选。它不读取业务资料，不连接数据库，不构建或查询真实索引，
也不选择或调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage078.index_smoke_test.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INDEX_SMOKE_TEST"
CONTROL_ADAPTER_VERSION = "ids.index_smoke_test.control_adapter.v0_1.stage078.p2"
CONTROL_FIELDS = ("index_smoke_test_control_requests",)

INDEX_KINDS = ("fulltext", "vector", "hybrid")
INDEX_VERSION_RECORD_FIELDS = (
    "index_version",
    "index_kind",
    "lifecycle_state",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "source_import_ref",
    "created_at_ref",
)
CANDIDATE_BUILD_FIELDS = (
    "index_kind",
    "candidate_index_version_ref",
    "build_state",
    "source_import_ref",
    "shadow_index_ref",
)
ACTIVE_POINTER_FIELDS = (
    "index_kind",
    "active_index_version_ref",
    "previous_active_index_version_ref",
    "pointer_state",
    "switch_record_ref",
)
SMOKE_TEST_PROJECTION_FIELDS = (
    "control_scenario",
    "smoke_test_ref",
    "candidate_index_version_ref",
    "active_index_version_ref",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "shadow_index_ref",
    "smoke_test_status",
    "required_conditions",
    "passed_condition_count",
    "switch_eligible",
    "failure_reason_ref",
)
SWITCH_PROJECTION_FIELDS = (
    "control_scenario",
    "switch_record_ref",
    "index_kind",
    "candidate_index_version_ref",
    "smoke_test_status",
    "switch_outcome",
    "resulting_active_index_version_ref",
    "previous_active_index_version_ref",
    "atomicity_contract",
    "active_service_continues",
    "switch_applied",
)
ROLLBACK_PROJECTION_FIELDS = (
    "control_scenario",
    "rollback_record_ref",
    "index_kind",
    "rollback_target_index_version_ref",
    "previous_active_index_version_ref",
    "retention_window_state",
    "rollback_state",
    "rollback_applied",
)
REQUIRED_SMOKE_TEST_CONDITIONS = (
    "candidate_build_marked_complete",
    "document_scope_declared",
    "chunk_count_declared",
    "embedding_model_declared",
    "candidate_isolated_from_active_service",
    "active_service_continuity_asserted",
)
INPUT_FIELDS = (
    "control_scenario",
    "source_import_ref",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "index_kind",
    "candidate_index_version_ref",
    "active_index_version_ref",
    "previous_active_index_version_ref",
    "shadow_index_ref",
    "planned_build_state",
    "planned_smoke_test_status",
    "planned_switch_outcome",
    "planned_rollback_state",
)
RUNTIME_CLOSED_FIELDS = (
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

CONTROL_SCENARIOS = (
    "fulltext_smoke_passed_switch_candidate",
    "vector_build_incomplete_keeps_active",
    "hybrid_smoke_test_failure_blocks_switch",
    "fulltext_switch_failure_preserves_active",
    "hybrid_rollback_candidate_retains_previous",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "fulltext_smoke_passed_switch_candidate": {
        "index_kind": "fulltext",
        "lifecycle_state": "SMOKE_TEST_PASSED_SWITCH_CANDIDATE",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_ATOMIC_SWITCH_CANDIDATE_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": (),
    },
    "vector_build_incomplete_keeps_active": {
        "index_kind": "vector",
        "lifecycle_state": "BUILDING",
        "build_state": "CONTROL_CANDIDATE_BUILD_NOT_COMPLETE",
        "smoke_test_status": "NOT_RUN",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": ("candidate_build_marked_complete",),
    },
    "hybrid_smoke_test_failure_blocks_switch": {
        "index_kind": "hybrid",
        "lifecycle_state": "SMOKE_TEST_FAILED",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "FAILED",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": (),
    },
    "fulltext_switch_failure_preserves_active": {
        "index_kind": "fulltext",
        "lifecycle_state": "SMOKE_TEST_PASSED_SWITCH_CANDIDATE",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "rollback_state": "CONTROL_ROLLBACK_CANDIDATE_PREVIOUS_ACTIVE_RETAINED",
        "failed_conditions": (),
    },
    "hybrid_rollback_candidate_retains_previous": {
        "index_kind": "hybrid",
        "lifecycle_state": "ROLLBACK_CANDIDATE",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_ROLLBACK_CANDIDATE_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
        "failed_conditions": (),
    },
}


def build_control_request(scenario: str) -> dict[str, Any]:
    """构造一条固定、无业务含义的 Stage078 P2 控制请求。"""

    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = f":control:stage078-p2:{scenario}"
    return {
        "control_scenario": scenario,
        "source_import_ref": f"source-import{marker}",
        "document_scope_ref": f"document-scope{marker}",
        "chunk_count": 0,
        "embedding_model_ref": f"embedding-model{marker}",
        "index_kind": config["index_kind"],
        "candidate_index_version_ref": f"index-version{marker}:candidate",
        "active_index_version_ref": f"index-version{marker}:active",
        "previous_active_index_version_ref": f"index-version{marker}:previous-active",
        "shadow_index_ref": f"shadow-index{marker}",
        "planned_build_state": config["build_state"],
        "planned_smoke_test_status": config["smoke_test_status"],
        "planned_switch_outcome": config["switch_outcome"],
        "planned_rollback_state": config["rollback_state"],
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦用例与回归使用。"""

    return {
        "index_smoke_test_control_requests": [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def execute_index_smoke_test_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影候选构建、冒烟门、切换和回退控制记录。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    index_version_records: list[dict[str, Any]] = []
    candidate_build_records: list[dict[str, Any]] = []
    active_pointer_projections: list[dict[str, Any]] = []
    smoke_test_projections: list[dict[str, Any]] = []
    switch_projections: list[dict[str, Any]] = []
    rollback_projections: list[dict[str, Any]] = []

    for scenario, request in zip(CONTROL_SCENARIOS, requests):
        config = CONTROL_SCENARIO_CONFIGURATION[scenario]
        marker = f":control:stage078-p2:{scenario}"
        conditions = {
            condition: condition not in config["failed_conditions"]
            for condition in REQUIRED_SMOKE_TEST_CONDITIONS
        }
        smoke_test_status = request["planned_smoke_test_status"]
        switch_eligible = smoke_test_status == "PASSED" and all(conditions.values())

        index_version_records.append(
            {
                "index_version": request["candidate_index_version_ref"],
                "index_kind": request["index_kind"],
                "lifecycle_state": config["lifecycle_state"],
                "document_scope_ref": request["document_scope_ref"],
                "chunk_count": request["chunk_count"],
                "embedding_model_ref": request["embedding_model_ref"],
                "source_import_ref": request["source_import_ref"],
                "created_at_ref": f"created-at{marker}",
            }
        )
        candidate_build_records.append(
            {
                "index_kind": request["index_kind"],
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "build_state": request["planned_build_state"],
                "source_import_ref": request["source_import_ref"],
                "shadow_index_ref": request["shadow_index_ref"],
            }
        )
        active_pointer_projections.append(
            {
                "index_kind": request["index_kind"],
                "active_index_version_ref": request["active_index_version_ref"],
                "previous_active_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "pointer_state": "CONTROL_ACTIVE_POINTER_UNCHANGED_RUNTIME_DISABLED",
                "switch_record_ref": f"switch-record{marker}",
            }
        )
        smoke_test_projections.append(
            {
                "control_scenario": scenario,
                "smoke_test_ref": f"smoke-test{marker}",
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "document_scope_ref": request["document_scope_ref"],
                "chunk_count": request["chunk_count"],
                "embedding_model_ref": request["embedding_model_ref"],
                "shadow_index_ref": request["shadow_index_ref"],
                "smoke_test_status": smoke_test_status,
                "required_conditions": conditions,
                "passed_condition_count": sum(conditions.values()),
                "switch_eligible": switch_eligible,
                "failure_reason_ref": _failure_reason_ref(
                    smoke_test_status, conditions
                ),
            }
        )
        switch_projections.append(
            {
                "control_scenario": scenario,
                "switch_record_ref": f"switch-record{marker}",
                "index_kind": request["index_kind"],
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "smoke_test_status": smoke_test_status,
                "switch_outcome": request["planned_switch_outcome"],
                "resulting_active_index_version_ref": request[
                    "active_index_version_ref"
                ],
                "previous_active_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "atomicity_contract": "FUTURE_ATOMIC_SWITCH_IS_ALL_OR_NOTHING",
                "active_service_continues": True,
                "switch_applied": False,
            }
        )
        rollback_projections.append(
            {
                "control_scenario": scenario,
                "rollback_record_ref": f"rollback-record{marker}",
                "index_kind": request["index_kind"],
                "rollback_target_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "previous_active_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "retention_window_state": "CONTROL_PREVIOUS_ACTIVE_RETAINED",
                "rollback_state": request["planned_rollback_state"],
                "rollback_applied": False,
            }
        )

    switch_outcomes = [record["switch_outcome"] for record in switch_projections]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_INDEX_SMOKE_TEST_CONTROL_SLICE",
        "control_request_count": len(requests),
        "actual_input_request_count": 0,
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "index_version_control_records": index_version_records,
        "index_version_control_record_count": len(index_version_records),
        "candidate_build_control_projections": candidate_build_records,
        "candidate_build_control_projection_count": len(candidate_build_records),
        "active_pointer_control_projections": active_pointer_projections,
        "active_pointer_control_projection_count": len(active_pointer_projections),
        "smoke_test_control_projections": smoke_test_projections,
        "smoke_test_control_projection_count": len(smoke_test_projections),
        "switch_control_projections": switch_projections,
        "switch_control_projection_count": len(switch_projections),
        "rollback_control_projections": rollback_projections,
        "rollback_control_projection_count": len(rollback_projections),
        "control_build_not_complete_count": sum(
            record["build_state"] == "CONTROL_CANDIDATE_BUILD_NOT_COMPLETE"
            for record in candidate_build_records
        ),
        "control_smoke_test_not_run_count": sum(
            record["smoke_test_status"] == "NOT_RUN"
            for record in smoke_test_projections
        ),
        "control_smoke_test_failed_count": sum(
            record["smoke_test_status"] == "FAILED"
            for record in smoke_test_projections
        ),
        "control_switch_blocked_count": sum(
            "BLOCKED" in outcome for outcome in switch_outcomes
        ),
        "control_switch_failure_count": sum(
            outcome == "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED"
            for outcome in switch_outcomes
        ),
        "control_rollback_candidate_count": sum(
            record["rollback_state"]
            == "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED"
            for record in rollback_projections
        ),
        "all_control_records_keep_required_shapes": _all_record_shapes_are_exact(
            index_version_records,
            candidate_build_records,
            active_pointer_projections,
            smoke_test_projections,
            switch_projections,
            rollback_projections,
        ),
        "all_candidate_versions_differ_from_active_versions": all(
            candidate["candidate_index_version_ref"]
            != pointer["active_index_version_ref"]
            for candidate, pointer in zip(
                candidate_build_records, active_pointer_projections
            )
        ),
        "all_shadow_candidates_are_isolated_from_active_service": all(
            candidate["shadow_index_ref"] != pointer["active_index_version_ref"]
            for candidate, pointer in zip(
                candidate_build_records, active_pointer_projections
            )
        ),
        "all_old_active_versions_continue_serving": all(
            switch["active_service_continues"] for switch in switch_projections
        ),
        "all_nonpassed_smoke_tests_block_switch": all(
            not smoke["switch_eligible"]
            for smoke in smoke_test_projections
            if smoke["smoke_test_status"] != "PASSED"
        ),
        "all_switch_projections_keep_active_pointer_unchanged": all(
            switch["resulting_active_index_version_ref"]
            == pointer["active_index_version_ref"]
            and not switch["switch_applied"]
            for switch, pointer in zip(switch_projections, active_pointer_projections)
        ),
        "all_rollback_targets_reference_retained_previous_active": all(
            record["rollback_target_index_version_ref"]
            == record["previous_active_index_version_ref"]
            for record in rollback_projections
        ),
        "control_output_is_not_actual_index_database_or_retrieval": True,
        "control_request_reference_validation_performed": True,
        "control_index_version_projection_performed": True,
        "control_candidate_build_projection_performed": True,
        "control_shadow_candidate_projection_performed": True,
        "control_smoke_test_projection_performed": True,
        "control_atomic_switch_projection_performed": True,
        "control_rollback_projection_performed": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "索引冒烟测试控制切片已在内存中投影，未构建或持久化实际索引。",
            "候选索引与影子引用保持隔离，旧活动版本继续服务。",
            "构建未完成、冒烟未执行或失败时，活动指针保持不变。",
            "回退候选只指向保留的上一活动版本，需业务线白箱人工处理。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, Any]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("index_smoke_test_control_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    expected = [build_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    if list(requests) != expected:
        return None
    return expected


def _failure_reason_ref(
    smoke_test_status: str,
    conditions: Mapping[str, bool],
) -> str:
    if smoke_test_status == "PASSED":
        return "CONTROL_ALL_REQUIRED_CONDITIONS_DECLARED"
    if smoke_test_status == "NOT_RUN":
        return "CONTROL_SMOKE_TEST_NOT_RUN_SWITCH_BLOCKED"
    if not all(conditions.values()):
        return "CONTROL_BUILD_NOT_COMPLETE_SWITCH_BLOCKED"
    if smoke_test_status == "FAILED":
        return "CONTROL_SMOKE_TEST_FAILED_SWITCH_BLOCKED"
    return "CONTROL_SMOKE_TEST_STATUS_NOT_PASSED_SWITCH_BLOCKED"


def _all_record_shapes_are_exact(
    index_version_records: Sequence[Mapping[str, Any]],
    candidate_build_records: Sequence[Mapping[str, Any]],
    active_pointer_projections: Sequence[Mapping[str, Any]],
    smoke_test_projections: Sequence[Mapping[str, Any]],
    switch_projections: Sequence[Mapping[str, Any]],
    rollback_projections: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        all(set(record) == set(INDEX_VERSION_RECORD_FIELDS) for record in index_version_records)
        and all(set(record) == set(CANDIDATE_BUILD_FIELDS) for record in candidate_build_records)
        and all(set(record) == set(ACTIVE_POINTER_FIELDS) for record in active_pointer_projections)
        and all(
            set(record) == set(SMOKE_TEST_PROJECTION_FIELDS)
            for record in smoke_test_projections
        )
        and all(set(record) == set(SWITCH_PROJECTION_FIELDS) for record in switch_projections)
        and all(set(record) == set(ROLLBACK_PROJECTION_FIELDS) for record in rollback_projections)
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_CONTROL_INPUT_RUNTIME_DISABLED",
        "control_request_count": 0,
        "actual_input_request_count": 0,
        "control_scenarios_covered": [],
        "rejection_reason": "CONTROL_INPUT_REJECTED",
        "control_output_is_not_actual_index_database_or_retrieval": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "控制输入未通过固定合同，未执行任何索引、冒烟、切换或回退。"
        ],
    }
