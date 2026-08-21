"""Stage080 P2 的纯内存索引回滚控制切片。

模块仅接受五条固定、非业务、reference-only 控制请求，并在内存中投影
索引版本、候选构建、影子隔离、冒烟门、活动指针、未应用切换和未应用回滚
资格。它不读取业务资料，不连接数据库，不构建或查询真实索引，也不选择或
调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "ids.stage080.index_rollback.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INDEX_ROLLBACK"
CONTROL_ADAPTER_VERSION = "ids.index_rollback.control_adapter.v0_1.stage080.p2"
CONTROL_FIELDS = ("index_rollback_control_requests",)

INDEX_VERSION_RECORD_FIELDS = (
    "index_version",
    "index_kind",
    "lifecycle_state",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "source_import_ref",
)
BUILDING_AND_SHADOW_FIELDS = (
    "building_index_version_ref",
    "candidate_index_version_ref",
    "shadow_index_ref",
    "source_import_ref",
    "build_state",
)
ACTIVE_POINTER_FIELDS = (
    "index_kind",
    "active_index_version_ref",
    "previous_active_index_version_ref",
    "pointer_state",
    "switch_record_ref",
)
SMOKE_TEST_INPUT_FIELDS = (
    "candidate_index_version_ref",
    "active_index_version_ref",
    "document_scope_ref",
    "chunk_count",
    "embedding_model_ref",
    "shadow_index_ref",
)
SMOKE_TEST_OUTPUT_FIELDS = (
    "smoke_test_ref",
    "smoke_test_status",
    "failure_reason_ref",
    "tested_at_ref",
    "switch_eligibility",
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
ROLLBACK_REQUEST_FIELDS = (
    "rollback_request_ref",
    "index_kind",
    "current_active_index_version_ref",
    "previous_active_index_version_ref",
    "rollback_reason_ref",
    "retention_window_state",
    "rollback_eligibility",
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
    "planned_retention_window_state",
    "planned_business_line_whitebox_approval_state",
)
REQUIRED_SWITCH_CONDITIONS = (
    "candidate_build_marked_complete",
    "candidate_isolated_from_active_service",
    "active_service_continuity_asserted",
    "passed_smoke_test_recorded",
    "previous_active_index_version_retained",
)
REQUIRED_ROLLBACK_CONDITIONS = (
    "previous_active_index_version_retained",
    "rollback_target_is_retained_previous_active_version",
    "retention_window_allows_rollback",
    "old_active_index_service_continuity_asserted",
    "business_line_whitebox_human_approval_reference_only",
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
        "build_state": "CONTROL_BUILD_COMPLETE_REFERENCE_ONLY",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_ATOMIC_SWITCH_CANDIDATE_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "retention_window_state": "CONTROL_RETENTION_WINDOW_VALID",
    },
    "vector_build_incomplete_preserves_active": {
        "index_kind": "vector",
        "lifecycle_state": "BUILDING",
        "build_state": "CONTROL_BUILD_INCOMPLETE_REFERENCE_ONLY",
        "smoke_test_status": "NOT_RUN",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "retention_window_state": "CONTROL_RETENTION_WINDOW_VALID",
    },
    "hybrid_smoke_test_failure_blocks_switch": {
        "index_kind": "hybrid",
        "lifecycle_state": "SMOKE_TEST_FAILED",
        "build_state": "CONTROL_BUILD_COMPLETE_REFERENCE_ONLY",
        "smoke_test_status": "FAILED",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "retention_window_state": "CONTROL_RETENTION_WINDOW_VALID",
    },
    "fulltext_switch_failure_preserves_active": {
        "index_kind": "fulltext",
        "lifecycle_state": "SMOKE_TEST_PASSED_SWITCH_CANDIDATE",
        "build_state": "CONTROL_BUILD_COMPLETE_REFERENCE_ONLY",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "rollback_state": "CONTROL_ROLLBACK_CANDIDATE_PREVIOUS_ACTIVE_RETAINED",
        "retention_window_state": "CONTROL_RETENTION_WINDOW_VALID",
    },
    "hybrid_rollback_candidate_retains_previous": {
        "index_kind": "hybrid",
        "lifecycle_state": "ROLLBACK_CANDIDATE",
        "build_state": "CONTROL_BUILD_COMPLETE_REFERENCE_ONLY",
        "smoke_test_status": "PASSED",
        "switch_outcome": "CONTROL_ROLLBACK_CANDIDATE_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
        "retention_window_state": "CONTROL_RETENTION_WINDOW_VALID",
    },
}


def build_control_request(scenario: str) -> dict[str, Any]:
    """构造一条固定、无业务含义的 Stage080 P2 控制请求。"""

    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = f":control:stage080-p2:{scenario}"
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
        "planned_retention_window_state": config["retention_window_state"],
        "planned_business_line_whitebox_approval_state": (
            "CONTROL_WHITEBOX_APPROVAL_REFERENCE_ONLY"
        ),
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦用例与回归使用。"""

    return {
        CONTROL_FIELDS[0]: [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def execute_index_rollback_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定的索引回滚控制记录，并拒绝任何其他输入。"""

    if control_input != build_control_input():
        return _rejected_result()

    requests = control_input[CONTROL_FIELDS[0]]
    index_versions: list[dict[str, Any]] = []
    building_and_shadow: list[dict[str, Any]] = []
    active_pointers: list[dict[str, Any]] = []
    smoke_inputs: list[dict[str, Any]] = []
    smoke_outputs: list[dict[str, Any]] = []
    switch_projections: list[dict[str, Any]] = []
    rollback_requests: list[dict[str, Any]] = []

    for scenario, request in zip(CONTROL_SCENARIOS, requests):
        config = CONTROL_SCENARIO_CONFIGURATION[scenario]
        marker = f":control:stage080-p2:{scenario}"
        switch_conditions = _switch_conditions(request)
        switch_eligible = all(switch_conditions.values())
        rollback_conditions = _rollback_conditions(request)
        rollback_eligible = (
            all(rollback_conditions.values())
            and request["planned_rollback_state"] != "CONTROL_ROLLBACK_NOT_REQUESTED"
        )

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
        building_and_shadow.append(
            {
                "building_index_version_ref": (
                    f"building-index-version{marker}:reference-only"
                ),
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "shadow_index_ref": request["shadow_index_ref"],
                "source_import_ref": request["source_import_ref"],
                "build_state": request["planned_build_state"],
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
        smoke_inputs.append(
            {
                "candidate_index_version_ref": request["candidate_index_version_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "document_scope_ref": request["document_scope_ref"],
                "chunk_count": request["chunk_count"],
                "embedding_model_ref": request["embedding_model_ref"],
                "shadow_index_ref": request["shadow_index_ref"],
            }
        )
        smoke_outputs.append(
            {
                "smoke_test_ref": f"smoke-test{marker}",
                "smoke_test_status": request["planned_smoke_test_status"],
                "failure_reason_ref": _failure_reason_ref(request, marker),
                "tested_at_ref": f"tested-at{marker}:not-executed",
                "switch_eligibility": (
                    "CONTROL_ELIGIBLE_NOT_APPLIED"
                    if switch_eligible
                    else "CONTROL_BLOCKED_RUNTIME_DISABLED"
                ),
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
        rollback_requests.append(
            {
                "rollback_request_ref": f"rollback-request{marker}",
                "index_kind": request["index_kind"],
                "current_active_index_version_ref": request[
                    "active_index_version_ref"
                ],
                "previous_active_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "rollback_reason_ref": f"rollback-reason{marker}",
                "retention_window_state": request[
                    "planned_retention_window_state"
                ],
                "rollback_eligibility": (
                    "CONTROL_ELIGIBLE_REFERENCE_ONLY"
                    if rollback_eligible
                    else "CONTROL_NOT_ELIGIBLE_OR_NOT_REQUESTED"
                ),
                "rollback_applied": False,
            }
        )

    result = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_INDEX_ROLLBACK_CONTROL_SLICE",
        "expected_control_request_count": len(CONTROL_SCENARIOS),
        "received_control_request_count": len(requests),
        "actual_input_request_count": 0,
        "index_version_control_records": index_versions,
        "index_version_control_record_count": len(index_versions),
        "building_and_shadow_control_projections": building_and_shadow,
        "building_and_shadow_control_projection_count": len(building_and_shadow),
        "active_pointer_control_projections": active_pointers,
        "active_pointer_control_projection_count": len(active_pointers),
        "smoke_test_input_control_projections": smoke_inputs,
        "smoke_test_input_control_projection_count": len(smoke_inputs),
        "smoke_test_output_control_projections": smoke_outputs,
        "smoke_test_output_control_projection_count": len(smoke_outputs),
        "switch_control_projections": switch_projections,
        "switch_control_projection_count": len(switch_projections),
        "rollback_request_control_projections": rollback_requests,
        "rollback_request_control_projection_count": len(rollback_requests),
        "all_candidate_versions_are_isolated": _all_candidate_versions_are_isolated(
            requests
        ),
        "all_old_active_versions_continue_serving": True,
        "all_active_pointer_projections_unchanged": all(
            projection["active_index_version_ref"]
            == request["active_index_version_ref"]
            for projection, request in zip(active_pointers, requests)
        ),
        "all_rollback_targets_reference_retained_previous_active": all(
            request["previous_active_index_version_ref"]
            != request["active_index_version_ref"]
            for request in requests
        ),
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_business_write_allowed": False,
        "automatic_active_pointer_switch_allowed": False,
        "automatic_rollback_allowed": False,
        "feedback": (
            "索引回滚控制切片已在本地验证，尚未执行回滚。",
            "新候选索引未通过冒烟测试，活动版本保持不变。",
            "旧索引继续服务，等待业务线白箱人工处理。",
            "回滚只能指向保留且仍在窗口内的上一活动版本。",
        ),
    }
    result.update(_runtime_closed())
    return result


def _switch_conditions(request: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "candidate_build_marked_complete": (
            request["planned_build_state"] == "CONTROL_BUILD_COMPLETE_REFERENCE_ONLY"
        ),
        "candidate_isolated_from_active_service": (
            request["candidate_index_version_ref"]
            != request["active_index_version_ref"]
            and request["shadow_index_ref"] != request["active_index_version_ref"]
        ),
        "active_service_continuity_asserted": True,
        "passed_smoke_test_recorded": request["planned_smoke_test_status"] == "PASSED",
        "previous_active_index_version_retained": (
            request["previous_active_index_version_ref"]
            != request["active_index_version_ref"]
        ),
    }


def _rollback_conditions(request: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "previous_active_index_version_retained": (
            request["previous_active_index_version_ref"]
            != request["active_index_version_ref"]
        ),
        "rollback_target_is_retained_previous_active_version": True,
        "retention_window_allows_rollback": (
            request["planned_retention_window_state"] == "CONTROL_RETENTION_WINDOW_VALID"
        ),
        "old_active_index_service_continuity_asserted": True,
        "business_line_whitebox_human_approval_reference_only": (
            request["planned_business_line_whitebox_approval_state"]
            == "CONTROL_WHITEBOX_APPROVAL_REFERENCE_ONLY"
        ),
    }


def _failure_reason_ref(request: Mapping[str, Any], marker: str) -> str:
    status = request["planned_smoke_test_status"]
    if status == "PASSED":
        return f"smoke-failure{marker}:none"
    if status == "FAILED":
        return f"smoke-failure{marker}:control-failed"
    return f"smoke-failure{marker}:control-not-run-or-missing"


def _all_candidate_versions_are_isolated(requests: list[dict[str, Any]]) -> bool:
    return all(
        request["candidate_index_version_ref"] != request["active_index_version_ref"]
        and request["candidate_index_version_ref"]
        != request["previous_active_index_version_ref"]
        and request["shadow_index_ref"] != request["active_index_version_ref"]
        for request in requests
    )


def _runtime_closed() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _rejected_result() -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_CONTROL_INPUT_RUNTIME_DISABLED",
        "rejection_reason": "CONTROL_INPUT_REJECTED",
        "actual_input_request_count": 0,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_business_write_allowed": False,
        "automatic_active_pointer_switch_allowed": False,
        "automatic_rollback_allowed": False,
    }
    result.update(_runtime_closed())
    return result
