"""Stage079 P2 的纯内存索引原子切换控制切片。

模块只接受五条固定、非业务、reference-only 控制请求，并在内存中投影
索引版本、候选构建、影子隔离、冒烟门、活动指针、未应用的未来原子切换
候选和回退候选。它不读取业务资料，不连接数据库，不构建或查询真实索引，
也不选择或调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "ids.stage079.atomic_index_switch.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_ATOMIC_INDEX_SWITCH"
CONTROL_ADAPTER_VERSION = "ids.atomic_index_switch.control_adapter.v0_1.stage079.p2"
CONTROL_FIELDS = ("atomic_index_switch_control_requests",)

INDEX_VERSION_RECORD_FIELDS = (
    "index_version",
    "index_kind",
    "lifecycle_state",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "source_import_ref",
)
CANDIDATE_BUILD_FIELDS = (
    "candidate_index_version_ref",
    "build_state",
    "shadow_index_ref",
    "active_service_continuity_asserted",
    "candidate_isolated_from_active_service",
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
    "smoke_test_status",
    "required_conditions",
    "switch_eligible",
)
SWITCH_PROJECTION_FIELDS = (
    "control_scenario",
    "switch_record_ref",
    "index_kind",
    "candidate_index_version_ref",
    "active_index_version_ref",
    "resulting_active_index_version_ref",
    "switch_outcome",
    "switch_eligible",
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
REQUIRED_SWITCH_CONDITIONS = (
    "candidate_build_marked_complete",
    "candidate_isolated_from_active_service",
    "active_service_continuity_asserted",
    "passed_smoke_test_recorded",
    "previous_active_index_version_retained",
)
RUNTIME_CLOSED_FIELDS = (
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

CONTROL_SCENARIOS = (
    "fulltext_smoke_passed_switch_candidate",
    "vector_build_incomplete_preserves_active",
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
        "candidate_isolated": True,
    },
    "vector_build_incomplete_preserves_active": {
        "index_kind": "vector",
        "lifecycle_state": "BUILDING",
        "build_state": "CONTROL_CANDIDATE_BUILD_NOT_COMPLETE",
        "smoke_test_status": "NOT_RUN",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "candidate_isolated": True,
    },
    "hybrid_smoke_test_failure_blocks_switch": {
        "index_kind": "hybrid",
        "lifecycle_state": "SMOKE_TEST_FAILED",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "FAILED",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "candidate_isolated": True,
    },
    "fulltext_switch_failure_preserves_active": {
        "index_kind": "fulltext",
        "lifecycle_state": "SMOKE_TEST_PASSED_SWITCH_CANDIDATE",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "rollback_state": "CONTROL_ROLLBACK_CANDIDATE_PREVIOUS_ACTIVE_RETAINED",
        "candidate_isolated": True,
    },
    "hybrid_rollback_candidate_retains_previous": {
        "index_kind": "hybrid",
        "lifecycle_state": "ROLLBACK_CANDIDATE",
        "build_state": "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_ROLLBACK_CANDIDATE_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
        "candidate_isolated": True,
    },
}


def build_control_request(scenario: str) -> dict[str, Any]:
    """构造一条固定、无业务含义的 Stage079 P2 控制请求."""

    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = f":control:stage079-p2:{scenario}"
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
    """返回完整固定控制输入，供本地聚焦用例与回归使用."""

    return {
        CONTROL_FIELDS[0]: [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def execute_atomic_index_switch_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定的原子切换、失败关闭和回退控制记录."""

    if control_input != build_control_input():
        return _rejected_result()

    requests = control_input[CONTROL_FIELDS[0]]
    index_versions: list[dict[str, Any]] = []
    candidate_builds: list[dict[str, Any]] = []
    active_pointers: list[dict[str, Any]] = []
    smoke_tests: list[dict[str, Any]] = []
    switch_projections: list[dict[str, Any]] = []
    rollback_projections: list[dict[str, Any]] = []

    for scenario, request in zip(CONTROL_SCENARIOS, requests):
        config = CONTROL_SCENARIO_CONFIGURATION[scenario]
        marker = f":control:stage079-p2:{scenario}"
        conditions = {
            "candidate_build_marked_complete": (
                request["planned_build_state"]
                == "CONTROL_CANDIDATE_BUILD_COMPLETE_NOT_STARTED"
            ),
            "candidate_isolated_from_active_service": (
                config["candidate_isolated"]
                and request["candidate_index_version_ref"]
                != request["active_index_version_ref"]
                and request["shadow_index_ref"]
                != request["active_index_version_ref"]
            ),
            "active_service_continuity_asserted": True,
            "passed_smoke_test_recorded": (
                request["planned_smoke_test_status"] == "PASSED"
            ),
            "previous_active_index_version_retained": (
                request["previous_active_index_version_ref"]
                != request["active_index_version_ref"]
            ),
        }
        switch_eligible = all(conditions.values())

        index_versions.append(
            {
                "index_version": request["candidate_index_version_ref"],
                "index_kind": request["index_kind"],
                "lifecycle_state": config["lifecycle_state"],
                "document_scope_ref": request["document_scope_ref"],
                "chunk_count": request["chunk_count"],
                "embedding_model_ref": request["embedding_model_ref"],
                "source_import_ref": request["source_import_ref"],
            }
        )
        candidate_builds.append(
            {
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "build_state": request["planned_build_state"],
                "shadow_index_ref": request["shadow_index_ref"],
                "active_service_continuity_asserted": conditions[
                    "active_service_continuity_asserted"
                ],
                "candidate_isolated_from_active_service": conditions[
                    "candidate_isolated_from_active_service"
                ],
            }
        )
        active_pointers.append(
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
        smoke_tests.append(
            {
                "control_scenario": scenario,
                "smoke_test_ref": f"smoke-test{marker}",
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "smoke_test_status": request["planned_smoke_test_status"],
                "required_conditions": conditions,
                "switch_eligible": switch_eligible,
            }
        )
        switch_projections.append(
            {
                "control_scenario": scenario,
                "switch_record_ref": f"switch-record{marker}",
                "index_kind": request["index_kind"],
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "resulting_active_index_version_ref": request[
                    "active_index_version_ref"
                ],
                "switch_outcome": request["planned_switch_outcome"],
                "switch_eligible": switch_eligible,
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

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_ATOMIC_INDEX_SWITCH_CONTROL_SLICE",
        "control_request_count": len(requests),
        "actual_input_request_count": 0,
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "index_version_control_records": index_versions,
        "index_version_control_record_count": len(index_versions),
        "candidate_build_control_projections": candidate_builds,
        "candidate_build_control_projection_count": len(candidate_builds),
        "active_pointer_control_projections": active_pointers,
        "active_pointer_control_projection_count": len(active_pointers),
        "smoke_test_control_projections": smoke_tests,
        "smoke_test_control_projection_count": len(smoke_tests),
        "switch_control_projections": switch_projections,
        "switch_control_projection_count": len(switch_projections),
        "rollback_control_projections": rollback_projections,
        "rollback_control_projection_count": len(rollback_projections),
        "all_candidate_versions_are_isolated": all(
            item["candidate_isolated_from_active_service"] for item in candidate_builds
        ),
        "all_old_active_versions_continue_serving": all(
            item["active_service_continuity_asserted"] for item in candidate_builds
        ),
        "all_active_pointer_projections_unchanged": all(
            item["resulting_active_index_version_ref"]
            == item["active_index_version_ref"]
            and item["switch_applied"] is False
            for item in switch_projections
        ),
        "all_rollback_targets_reference_retained_previous_active": all(
            item["rollback_target_index_version_ref"]
            == item["previous_active_index_version_ref"]
            and item["rollback_applied"] is False
            for item in rollback_projections
        ),
        "chinese_feedback": [
            "原子切换控制切片已完成，未执行真实切换。",
            "候选索引未满足切换条件，活动版本保持不变。",
            "旧活动索引继续服务，等待业务线白箱人工处理。",
            "回退候选只指向保留的上一活动版本。",
        ],
        **_runtime_closed(),
    }


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_CONTROL_INPUT_RUNTIME_DISABLED",
        "rejection_reason": "CONTROL_INPUT_REJECTED",
        "control_request_count": 0,
        "actual_input_request_count": 0,
        "control_scenarios_covered": [],
        **_runtime_closed(),
    }


def _runtime_closed() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}

