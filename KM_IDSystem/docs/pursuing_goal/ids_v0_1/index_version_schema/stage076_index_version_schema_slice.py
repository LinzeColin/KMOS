"""Stage076 P2 的纯内存索引版本 Schema 控制切片。

模块只接受五条固定、非业务、reference-only 控制请求，并在内存中投影
index version、building version、shadow candidate、切换前验证、活动指针、
原子切换候选和回退候选。它不读取业务资料，不连接数据库，不构建或查询真实
索引，也不选择或调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage076.index_version_schema.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INDEX_VERSION_SCHEMA"
CONTROL_ADAPTER_VERSION = "ids.index_version_schema.control_adapter.v0_1.stage076.p2"
CONTROL_FIELDS = ("index_version_schema_requests",)

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
ACTIVE_POINTER_FIELDS = (
    "index_kind",
    "active_index_version_ref",
    "previous_active_index_version_ref",
    "pointer_state",
    "switch_record_ref",
)
BUILDING_VERSION_FIELDS = (
    "index_kind",
    "building_index_version_ref",
    "build_state",
    "source_import_ref",
    "shadow_index_ref",
)
VERIFICATION_FIELDS = (
    "verification_ref",
    "index_version_ref",
    "verification_state",
    "required_conditions",
    "passed_condition_count",
    "active_service_continuity_asserted",
    "switch_allowed",
    "verification_reason",
)
SWITCH_PROJECTION_FIELDS = (
    "control_scenario",
    "switch_record_ref",
    "index_kind",
    "candidate_index_version_ref",
    "verification_state",
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
REQUIRED_VERIFICATION_CONDITIONS = (
    "index_version_schema_complete",
    "candidate_build_marked_complete",
    "document_scope_declared",
    "chunk_count_declared",
    "embedding_model_declared",
    "active_service_continuity_asserted",
)
INPUT_FIELDS = (
    "control_scenario",
    *INDEX_VERSION_RECORD_FIELDS,
    "active_index_version_ref",
    "previous_active_index_version_ref",
    "planned_build_state",
    "planned_verification_state",
    "planned_switch_outcome",
    "planned_rollback_state",
)

CONTROL_SCENARIOS = (
    "fulltext_verified_switch_candidate",
    "vector_building_keeps_active",
    "hybrid_verification_failure_blocks_switch",
    "fulltext_switch_failure_preserves_active",
    "hybrid_rollback_candidate_retains_previous",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "fulltext_verified_switch_candidate": {
        "index_kind": "fulltext",
        "lifecycle_state": "VERIFIED",
        "build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "verification_state": "PASSED",
        "switch_outcome": "CONTROL_ATOMIC_SWITCH_PROJECTED_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": (),
    },
    "vector_building_keeps_active": {
        "index_kind": "vector",
        "lifecycle_state": "BUILDING",
        "build_state": "CONTROL_BUILDING_NOT_STARTED",
        "verification_state": "PENDING",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_BUILDING",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": ("candidate_build_marked_complete",),
    },
    "hybrid_verification_failure_blocks_switch": {
        "index_kind": "hybrid",
        "lifecycle_state": "FAILED",
        "build_state": "CONTROL_BUILD_FAILED_NOT_STARTED",
        "verification_state": "FAILED",
        "switch_outcome": "CONTROL_SWITCH_BLOCKED_VERIFICATION_FAILED",
        "rollback_state": "CONTROL_ROLLBACK_NOT_REQUESTED",
        "failed_conditions": ("candidate_build_marked_complete",),
    },
    "fulltext_switch_failure_preserves_active": {
        "index_kind": "fulltext",
        "lifecycle_state": "VERIFIED",
        "build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "verification_state": "PASSED",
        "switch_outcome": "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
        "rollback_state": "CONTROL_ROLLBACK_CANDIDATE_PREVIOUS_ACTIVE_RETAINED",
        "failed_conditions": (),
    },
    "hybrid_rollback_candidate_retains_previous": {
        "index_kind": "hybrid",
        "lifecycle_state": "ROLLED_BACK",
        "build_state": "CONTROL_BUILD_COMPLETE_NOT_PERSISTED",
        "verification_state": "PASSED",
        "switch_outcome": "CONTROL_ROLLBACK_PROJECTED_NOT_APPLIED",
        "rollback_state": "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
        "failed_conditions": (),
    },
}


def build_control_request(scenario: str) -> dict[str, Any]:
    """构造一条固定、无业务含义的 Stage076 P2 控制请求。"""

    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = f":control:stage076-p2:{scenario}"
    return {
        "control_scenario": scenario,
        "index_version": f"index-version{marker}:candidate",
        "index_kind": config["index_kind"],
        "lifecycle_state": config["lifecycle_state"],
        "document_scope_ref": f"document-scope{marker}",
        "chunk_count": 0,
        "embedding_model_ref": f"embedding-model{marker}",
        "source_import_ref": f"source-import{marker}",
        "created_at_ref": f"created-at{marker}",
        "active_index_version_ref": f"index-version{marker}:active",
        "previous_active_index_version_ref": f"index-version{marker}:previous-active",
        "planned_build_state": config["build_state"],
        "planned_verification_state": config["verification_state"],
        "planned_switch_outcome": config["switch_outcome"],
        "planned_rollback_state": config["rollback_state"],
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦用例与回归使用。"""

    return {
        "index_version_schema_requests": [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def execute_index_version_schema_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定的版本、构建、验证、切换和回退控制记录。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    index_version_records: list[dict[str, Any]] = []
    building_version_records: list[dict[str, Any]] = []
    active_pointer_projections: list[dict[str, Any]] = []
    verification_projections: list[dict[str, Any]] = []
    switch_projections: list[dict[str, Any]] = []
    rollback_projections: list[dict[str, Any]] = []

    for scenario, request in zip(CONTROL_SCENARIOS, requests):
        config = CONTROL_SCENARIO_CONFIGURATION[scenario]
        marker = f":control:stage076-p2:{scenario}"
        conditions = {
            condition: condition not in config["failed_conditions"]
            for condition in REQUIRED_VERIFICATION_CONDITIONS
        }
        switch_allowed = all(conditions.values()) and config["verification_state"] == "PASSED"
        index_version_records.append(
            {field: request[field] for field in INDEX_VERSION_RECORD_FIELDS}
        )
        building_version_records.append(
            {
                "index_kind": request["index_kind"],
                "building_index_version_ref": request["index_version"],
                "build_state": request["planned_build_state"],
                "source_import_ref": request["source_import_ref"],
                "shadow_index_ref": f"shadow-index{marker}",
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
        verification_projections.append(
            {
                "verification_ref": f"verification{marker}",
                "index_version_ref": request["index_version"],
                "verification_state": request["planned_verification_state"],
                "required_conditions": conditions,
                "passed_condition_count": sum(conditions.values()),
                "active_service_continuity_asserted": conditions[
                    "active_service_continuity_asserted"
                ],
                "switch_allowed": switch_allowed,
                "verification_reason": _verification_reason(
                    request["planned_verification_state"], conditions
                ),
            }
        )
        switch_projections.append(
            {
                "control_scenario": scenario,
                "switch_record_ref": f"switch-record{marker}",
                "index_kind": request["index_kind"],
                "candidate_index_version_ref": request["index_version"],
                "verification_state": request["planned_verification_state"],
                "switch_outcome": request["planned_switch_outcome"],
                "resulting_active_index_version_ref": request[
                    "active_index_version_ref"
                ],
                "previous_active_index_version_ref": request[
                    "previous_active_index_version_ref"
                ],
                "atomicity_contract": "FUTURE_SWITCH_IS_ALL_OR_NOTHING",
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
        "execution_state": "COMPLETED_IN_MEMORY_INDEX_VERSION_SCHEMA_CONTROL_SLICE",
        "control_request_count": len(requests),
        "actual_input_request_count": 0,
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "index_version_control_records": index_version_records,
        "index_version_control_record_count": len(index_version_records),
        "building_version_control_records": building_version_records,
        "building_version_control_record_count": len(building_version_records),
        "active_pointer_control_projections": active_pointer_projections,
        "active_pointer_control_projection_count": len(active_pointer_projections),
        "verification_control_projections": verification_projections,
        "verification_control_projection_count": len(verification_projections),
        "switch_control_projections": switch_projections,
        "switch_control_projection_count": len(switch_projections),
        "rollback_control_projections": rollback_projections,
        "rollback_control_projection_count": len(rollback_projections),
        "control_building_count": sum(
            record["build_state"] == "CONTROL_BUILDING_NOT_STARTED"
            for record in building_version_records
        ),
        "control_build_failed_count": sum(
            record["build_state"] == "CONTROL_BUILD_FAILED_NOT_STARTED"
            for record in building_version_records
        ),
        "control_verification_failed_count": sum(
            record["verification_state"] == "FAILED"
            for record in verification_projections
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
            building_version_records,
            active_pointer_projections,
            verification_projections,
            switch_projections,
            rollback_projections,
        ),
        "all_building_versions_differ_from_active_versions": all(
            building["building_index_version_ref"] != pointer["active_index_version_ref"]
            for building, pointer in zip(
                building_version_records, active_pointer_projections
            )
        ),
        "all_active_versions_continue_serving_during_control_build": all(
            switch["active_service_continues"] for switch in switch_projections
        ),
        "all_failed_or_pending_candidates_block_switch": all(
            not verification["switch_allowed"]
            for verification in verification_projections
            if verification["verification_state"] != "PASSED"
        ),
        "all_rollback_targets_reference_retained_previous_active": all(
            record["rollback_target_index_version_ref"]
            == record["previous_active_index_version_ref"]
            for record in rollback_projections
        ),
        "control_output_is_not_actual_index_database_or_retrieval": True,
        "control_request_reference_validation_performed": True,
        "control_index_version_projection_performed": True,
        "control_building_version_projection_performed": True,
        "control_shadow_candidate_projection_performed": True,
        "control_verification_projection_performed": True,
        "control_atomic_switch_projection_performed": True,
        "control_rollback_projection_performed": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "索引版本控制切片已在内存中投影，未构建或持久化实际索引。",
            "构建中版本不替换活动版本，旧活动版本继续服务。",
            "候选验证未通过或未完成时，活动指针保持不变。",
            "回退候选只指向保留的上一活动版本，需业务线白箱人工处理。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, Any]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("index_version_schema_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    expected = [build_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    if list(requests) != expected:
        return None
    return expected


def _verification_reason(
    verification_state: str,
    conditions: Mapping[str, bool],
) -> str:
    if verification_state == "PASSED":
        return "CONTROL_ALL_REQUIRED_CONDITIONS_DECLARED"
    if verification_state == "PENDING":
        return "CONTROL_BUILD_NOT_COMPLETE_SWITCH_BLOCKED"
    if not all(conditions.values()):
        return "CONTROL_REQUIRED_CONDITION_FAILED_SWITCH_BLOCKED"
    return "CONTROL_VERIFICATION_FAILED_SWITCH_BLOCKED"


def _all_record_shapes_are_exact(
    index_version_records: Sequence[Mapping[str, Any]],
    building_version_records: Sequence[Mapping[str, Any]],
    active_pointer_projections: Sequence[Mapping[str, Any]],
    verification_projections: Sequence[Mapping[str, Any]],
    switch_projections: Sequence[Mapping[str, Any]],
    rollback_projections: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        all(set(record) == set(INDEX_VERSION_RECORD_FIELDS) for record in index_version_records)
        and all(set(record) == set(BUILDING_VERSION_FIELDS) for record in building_version_records)
        and all(set(record) == set(ACTIVE_POINTER_FIELDS) for record in active_pointer_projections)
        and all(set(record) == set(VERIFICATION_FIELDS) for record in verification_projections)
        and all(set(record) == set(SWITCH_PROJECTION_FIELDS) for record in switch_projections)
        and all(set(record) == set(ROLLBACK_PROJECTION_FIELDS) for record in rollback_projections)
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "control_request_count": 0,
        "actual_input_request_count": 0,
        "index_version_control_records": [],
        "index_version_control_record_count": 0,
        "building_version_control_records": [],
        "building_version_control_record_count": 0,
        "active_pointer_control_projections": [],
        "active_pointer_control_projection_count": 0,
        "verification_control_projections": [],
        "verification_control_projection_count": 0,
        "switch_control_projections": [],
        "switch_control_projection_count": 0,
        "rollback_control_projections": [],
        "rollback_control_projection_count": 0,
        "all_control_records_keep_required_shapes": False,
        "control_request_reference_validation_performed": True,
        "control_index_version_projection_performed": False,
        "control_building_version_projection_performed": False,
        "control_shadow_candidate_projection_performed": False,
        "control_verification_projection_performed": False,
        "control_atomic_switch_projection_performed": False,
        "control_rollback_projection_performed": False,
        **_runtime_closed_flags(),
    }


def _runtime_closed_flags() -> dict[str, bool]:
    return {
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "actual_index_version_record_created": False,
        "actual_document_scope_recorded": False,
        "actual_chunk_count_recorded": False,
        "actual_embedding_model_recorded": False,
        "actual_bulk_import_detected": False,
        "actual_index_build_started": False,
        "actual_building_version_record_created": False,
        "actual_shadow_index_created": False,
        "actual_shadow_index_queried": False,
        "actual_verification_run_performed": False,
        "actual_verification_result_recorded": False,
        "actual_active_pointer_read_performed": False,
        "actual_active_pointer_write_performed": False,
        "actual_switch_record_created": False,
        "actual_retrieval_query_performed": False,
        "actual_rollback_record_created": False,
        "actual_rollback_execution_performed": False,
        "database_schema_migration_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "provider_or_model_selected": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "external_api_call_performed": False,
        "agent_execution_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
    }
