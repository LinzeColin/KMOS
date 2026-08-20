"""Stage072 P2 的纯内存 Embedding 模型版本控制切片。

模块只接受五条固定、非业务、reference-only 控制请求，并在内存中机械投影
策略继承、未来队列/缓存/失败重试、零值成本、六字段模型版本及外部 API 审计
字段。它不会读取来源正文、摘要、文本块、物理路径或真实 URI；不会创建持久
记录；也不会选择 provider/模型、调用外部 API 或消耗模型 Token。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage072.embedding_model_version.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EMBEDDING_MODEL_VERSION"
CONTROL_ADAPTER_VERSION = "ids.embedding_model_version.control_adapter.v0_1.stage072.p2"
CONTROL_FIELDS = ("embedding_model_version_requests",)

POLICY_VALUES = ("denied", "summary_only", "full_text_allowed")
POLICY_RANK = {policy: rank for rank, policy in enumerate(POLICY_VALUES)}
BUDGET_AVAILABLE = "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY"
BUDGET_DENIED_NOT_APPLICABLE = "CONTROL_BUDGET_NOT_APPLICABLE_POLICY_DENIED"
BUDGET_INSUFFICIENT = "CONTROL_BUDGET_INSUFFICIENT"

CONTROL_SCENARIOS = (
    "default_denied",
    "summary_only_inherited",
    "document_restricts_full_text_to_summary_only",
    "full_text_allowed_control_only",
    "budget_insufficient_pauses_full_text",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "default_denied": {
        "source_policy": "denied",
        "document_policy": None,
        "budget_check_state": BUDGET_DENIED_NOT_APPLICABLE,
    },
    "summary_only_inherited": {
        "source_policy": "summary_only",
        "document_policy": None,
        "budget_check_state": BUDGET_AVAILABLE,
    },
    "document_restricts_full_text_to_summary_only": {
        "source_policy": "full_text_allowed",
        "document_policy": "summary_only",
        "budget_check_state": BUDGET_AVAILABLE,
    },
    "full_text_allowed_control_only": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "budget_check_state": BUDGET_AVAILABLE,
    },
    "budget_insufficient_pauses_full_text": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "budget_check_state": BUDGET_INSUFFICIENT,
    },
}

REFERENCE_INPUT_FIELDS = (
    "embedding_model_version_request_ref",
    "policy_resolution_ref",
    "data_source_ref",
    "document_ref",
    "chunk_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "provider_ref",
    "model_ref",
    "model_version",
    "dimension",
    "created_at",
    "sent_to_external_api",
    "estimated_token_count",
    "estimated_cost",
    "budget_check_state",
    "external_api_audit_ref",
    "embedding_queue_request_ref",
    "cache_entry_ref",
    "retry_ref",
)
POLICY_RESOLUTION_FIELDS = (
    "policy_resolution_ref",
    "data_source_ref",
    "document_ref",
    "chunk_ref",
    "source_external_api_policy",
    "document_external_api_policy",
    "effective_external_api_policy",
    "policy_inheritance_reason",
    "external_payload_mode",
    "budget_check_state",
)
QUEUE_FIELDS = (
    "embedding_queue_request_ref",
    "policy_resolution_ref",
    "document_ref",
    "chunk_ref",
    "external_payload_mode",
    "provider_ref",
    "model_ref",
    "model_version",
    "estimated_token_count",
    "estimated_cost",
    "budget_check_state",
    "external_api_audit_ref",
)
CACHE_FIELDS = (
    "cache_entry_ref",
    "embedding_queue_request_ref",
    "policy_resolution_ref",
    "document_ref",
    "chunk_ref",
    "external_payload_mode",
    "provider_ref",
    "model_ref",
    "model_version",
    "cache_disposition",
)
RETRY_FIELDS = (
    "retry_ref",
    "embedding_queue_request_ref",
    "policy_resolution_ref",
    "budget_check_state",
    "external_api_audit_ref",
    "retry_state",
    "retry_reason",
)
MODEL_VERSION_FIELDS = (
    "provider_ref",
    "model_ref",
    "model_version",
    "dimension",
    "created_at",
    "sent_to_external_api",
)
COST_FIELDS = (
    "provider_ref",
    "model_ref",
    "model_version",
    "estimated_token_count",
    "estimated_cost",
    "budget_check_state",
    "cost_currency",
    "cost_estimation_reason",
)
AUDIT_FIELDS = (
    "external_api_audit_ref",
    "data_source_ref",
    "document_ref",
    "chunk_id",
    "effective_external_api_policy",
    "external_payload_mode",
    "policy_inheritance_reason",
    "owner_authorization_ref",
    "authorized_at",
    "authorization_reason",
    "provider_ref",
    "model_ref",
    "model_version",
    "token_count",
    "cost_estimate",
    "embedding_queue_request_ref",
    "budget_check_state",
    "audit_disposition",
)


def build_control_request(scenario: str) -> dict[str, Any]:
    """返回固定控制请求；其中没有正文、路径、真实 URI 或业务标识。"""

    if scenario not in CONTROL_SCENARIO_CONFIGURATION:
        raise ValueError("unknown embedding model version control scenario")
    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    effective_policy, _ = resolve_effective_policy(
        config["source_policy"], config["document_policy"]
    )
    marker = f":control:stage072-p2:{scenario}"
    return {
        "embedding_model_version_request_ref": f"model-version-request{marker}",
        "policy_resolution_ref": f"policy-resolution{marker}",
        "data_source_ref": f"data-source{marker}",
        "document_ref": f"document{marker}",
        "chunk_ref": f"chunk{marker}",
        "effective_external_api_policy": effective_policy,
        "external_payload_mode": _external_payload_mode(effective_policy),
        "provider_ref": f"provider{marker}",
        "model_ref": f"model{marker}",
        "model_version": f"model-version{marker}",
        "dimension": f"dimension{marker}",
        "created_at": f"created-at{marker}",
        "sent_to_external_api": False,
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "budget_check_state": config["budget_check_state"],
        "external_api_audit_ref": f"external-api-audit{marker}",
        "embedding_queue_request_ref": f"embedding-queue-request{marker}",
        "cache_entry_ref": f"cache-entry{marker}",
        "retry_ref": f"retry{marker}",
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦测试与本地回归使用。"""

    return {
        "embedding_model_version_requests": [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def resolve_effective_policy(
    source_policy: object, document_policy: object
) -> tuple[str, str]:
    """只解析固定策略枚举；缺失、无效或放宽均关闭为 denied。"""

    if source_policy not in POLICY_VALUES:
        return "denied", "CONTROL_SOURCE_POLICY_INVALID_FAIL_CLOSED"
    if document_policy is None:
        return str(source_policy), "CONTROL_INHERITED_FROM_DATA_SOURCE"
    if document_policy not in POLICY_VALUES:
        return "denied", "CONTROL_DOCUMENT_POLICY_INVALID_FAIL_CLOSED"
    if POLICY_RANK[str(document_policy)] > POLICY_RANK[str(source_policy)]:
        return "denied", "CONTROL_DOCUMENT_POLICY_WIDENING_BLOCKED"
    if document_policy == source_policy:
        return str(source_policy), "CONTROL_DOCUMENT_POLICY_MATCHED_SOURCE"
    return str(document_policy), "CONTROL_DOCUMENT_POLICY_RESTRICTED_EFFECTIVE"


def execute_embedding_model_version_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定策略、队列、缓存、模型版本、成本和审计控制记录。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    resolutions = [
        _policy_resolution(scenario, request)
        for scenario, request in zip(CONTROL_SCENARIOS, requests)
    ]
    queue_records = [
        _queue_record(resolution, request)
        for resolution, request in zip(resolutions, requests)
    ]
    cache_records = [
        _cache_record(resolution, request)
        for resolution, request in zip(resolutions, requests)
    ]
    retry_records = [
        _retry_record(resolution, request)
        for resolution, request in zip(resolutions, requests)
    ]
    model_version_projections = [
        _model_version_projection(request) for request in requests
    ]
    cost_projections = [
        _cost_projection(resolution, request)
        for resolution, request in zip(resolutions, requests)
    ]
    audit_projections = [
        _audit_projection(resolution, request)
        for resolution, request in zip(resolutions, requests)
    ]

    queue_states = [record["control_queue_state"] for record in queue_records]
    cache_states = [record["cache_disposition"] for record in cache_records]
    retry_states = [record["retry_state"] for record in retry_records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_EMBEDDING_MODEL_VERSION_CONTROL_SLICE",
        "control_request_count": len(requests),
        "actual_input_request_count": 0,
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "policy_resolutions": resolutions,
        "policy_resolution_count": len(resolutions),
        "all_chunks_inherit_effective_document_policy_automatically": True,
        "chunk_manual_policy_assignment_performed": False,
        "embedding_queue_records": queue_records,
        "embedding_queue_record_count": len(queue_records),
        "cache_records": cache_records,
        "cache_record_count": len(cache_records),
        "failed_retry_records": retry_records,
        "failed_retry_record_count": len(retry_records),
        "model_version_control_projections": model_version_projections,
        "model_version_control_projection_count": len(model_version_projections),
        "cost_control_projections": cost_projections,
        "cost_control_projection_count": len(cost_projections),
        "external_api_audit_projections": audit_projections,
        "external_api_audit_projection_count": len(audit_projections),
        "control_queue_blocked_policy_denied_count": queue_states.count(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED"
        ),
        "control_queue_paused_budget_insufficient_count": queue_states.count(
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT"
        ),
        "control_queue_eligible_not_persisted_count": queue_states.count(
            "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        ),
        "control_cache_blocked_policy_denied_count": cache_states.count(
            "CONTROL_CACHE_BLOCKED_POLICY_DENIED"
        ),
        "control_cache_paused_budget_insufficient_count": cache_states.count(
            "CONTROL_CACHE_PAUSED_BUDGET_INSUFFICIENT"
        ),
        "control_retry_blocked_policy_denied_count": retry_states.count(
            "CONTROL_RETRY_BLOCKED_POLICY_DENIED"
        ),
        "control_retry_paused_budget_insufficient_count": retry_states.count(
            "CONTROL_RETRY_PAUSED_BUDGET_INSUFFICIENT"
        ),
        "all_control_records_keep_required_shapes": _all_record_shapes_are_exact(
            queue_records,
            cache_records,
            retry_records,
            model_version_projections,
            cost_projections,
            audit_projections,
        ),
        "all_model_version_sent_statuses_are_false": all(
            not record["sent_to_external_api"] for record in model_version_projections
        ),
        "source_body_summary_body_or_chunk_text_retained": False,
        "control_output_is_not_actual_queue_cache_model_version_cost_or_audit": True,
        "control_request_reference_validation_performed": True,
        "control_policy_inheritance_projection_performed": True,
        "control_embedding_queue_projection_performed": True,
        "control_cache_projection_performed": True,
        "control_retry_projection_performed": True,
        "control_model_version_projection_performed": True,
        "control_cost_projection_performed": True,
        "control_external_api_audit_projection_performed": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影五条固定模型版本、队列、缓存和审计控制记录，未读取或保留任何真实资料、摘要正文、文本块、路径、页面或业务结论。",
            "有效外部 API 策略从 data source 经 document 自动继承到 chunk；默认 denied，文档不能放宽来源策略，也不能手工标记单个 chunk。",
            "未授权 chunk 不会外发；provider、模型、版本、维度、创建时间、Token、成本和审计字段只是控制引用与零值投影，未创建运行时记录。",
            "任何控制候选都不会被持久化、调度或发送；provider 调用前仍需要未来授权、预算、审计及业务线白箱人工复核。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, Any]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("embedding_model_version_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    expected = [build_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    if list(requests) != expected:
        return None
    return expected


def _policy_resolution(scenario: str, request: Mapping[str, Any]) -> dict[str, Any]:
    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    effective_policy, reason = resolve_effective_policy(
        config["source_policy"], config["document_policy"]
    )
    if effective_policy != request["effective_external_api_policy"]:
        raise ValueError("fixed control request policy does not match inheritance")
    return {
        "policy_resolution_ref": request["policy_resolution_ref"],
        "data_source_ref": request["data_source_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "source_external_api_policy": config["source_policy"],
        "document_external_api_policy": config["document_policy"],
        "effective_external_api_policy": effective_policy,
        "policy_inheritance_reason": reason,
        "external_payload_mode": request["external_payload_mode"],
        "budget_check_state": request["budget_check_state"],
    }


def _queue_record(resolution: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    state, reason = _control_disposition(resolution)
    return {
        **{field: request[field] for field in QUEUE_FIELDS},
        "control_queue_state": state,
        "control_queue_reason": reason,
    }


def _cache_record(resolution: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    state, _ = _control_disposition(resolution)
    return {
        "cache_entry_ref": request["cache_entry_ref"],
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "policy_resolution_ref": request["policy_resolution_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "external_payload_mode": request["external_payload_mode"],
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "cache_disposition": state.replace("QUEUE", "CACHE"),
    }


def _retry_record(resolution: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    state, reason = _control_disposition(resolution)
    retry_state = state.replace("QUEUE", "RETRY")
    if retry_state == "CONTROL_RETRY_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED":
        retry_state = "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED"
    return {
        "retry_ref": request["retry_ref"],
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "policy_resolution_ref": request["policy_resolution_ref"],
        "budget_check_state": request["budget_check_state"],
        "external_api_audit_ref": request["external_api_audit_ref"],
        "retry_state": retry_state,
        "retry_reason": reason,
    }


def _model_version_projection(request: Mapping[str, Any]) -> dict[str, Any]:
    return {field: request[field] for field in MODEL_VERSION_FIELDS}


def _cost_projection(
    resolution: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "budget_check_state": resolution["budget_check_state"],
        "cost_currency": "CONTROL_NO_CURRENCY_NO_EXTERNAL_COST",
        "cost_estimation_reason": "CONTROL_NO_EXTERNAL_PAYLOAD_OR_MODEL_CALL_WAS_CREATED",
    }


def _audit_projection(
    resolution: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    if resolution["effective_external_api_policy"] == "denied":
        disposition = "BLOCKED_POLICY_DENIED"
    elif resolution["budget_check_state"] == BUDGET_INSUFFICIENT:
        disposition = "CONTROL_AUDIT_REQUIRED_BUDGET_PAUSED"
    else:
        disposition = "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL"
    marker = request["external_api_audit_ref"].replace("external-api-audit", "authorization")
    return {
        "external_api_audit_ref": request["external_api_audit_ref"],
        "data_source_ref": request["data_source_ref"],
        "document_ref": request["document_ref"],
        "chunk_id": request["chunk_ref"],
        "effective_external_api_policy": resolution["effective_external_api_policy"],
        "external_payload_mode": resolution["external_payload_mode"],
        "policy_inheritance_reason": resolution["policy_inheritance_reason"],
        "owner_authorization_ref": f"owner-authorization{marker}",
        "authorized_at": f"authorized-at{marker}",
        "authorization_reason": f"authorization-reason{marker}",
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "token_count": 0,
        "cost_estimate": 0,
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "budget_check_state": request["budget_check_state"],
        "audit_disposition": disposition,
    }


def _control_disposition(resolution: Mapping[str, Any]) -> tuple[str, str]:
    if resolution["effective_external_api_policy"] == "denied":
        return (
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
            "CONTROL_EXTERNALIZATION_FORBIDDEN_BY_EFFECTIVE_POLICY",
        )
    if resolution["budget_check_state"] == BUDGET_INSUFFICIENT:
        return (
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
            "CONTROL_NO_EXTERNAL_TASK_CREATED_WHEN_BUDGET_IS_INSUFFICIENT",
        )
    return (
        "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "CONTROL_REFERENCE_ONLY_NO_QUEUE_CACHE_OR_PROVIDER_INITIALIZED",
    )


def _external_payload_mode(effective_policy: str) -> str:
    if effective_policy == "denied":
        return "NO_EXTERNAL_PAYLOAD_POLICY_DENIED"
    if effective_policy == "summary_only":
        return "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY"
    return "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY"


def _all_record_shapes_are_exact(
    queue_records: Sequence[Mapping[str, Any]],
    cache_records: Sequence[Mapping[str, Any]],
    retry_records: Sequence[Mapping[str, Any]],
    model_version_projections: Sequence[Mapping[str, Any]],
    cost_projections: Sequence[Mapping[str, Any]],
    audit_projections: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        all(
            set(record) == set(QUEUE_FIELDS) | {"control_queue_state", "control_queue_reason"}
            for record in queue_records
        )
        and all(set(record) == set(CACHE_FIELDS) for record in cache_records)
        and all(set(record) == set(RETRY_FIELDS) for record in retry_records)
        and all(set(record) == set(MODEL_VERSION_FIELDS) for record in model_version_projections)
        and all(set(record) == set(COST_FIELDS) for record in cost_projections)
        and all(set(record) == set(AUDIT_FIELDS) for record in audit_projections)
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
        "policy_resolutions": [],
        "policy_resolution_count": 0,
        "embedding_queue_records": [],
        "embedding_queue_record_count": 0,
        "cache_records": [],
        "cache_record_count": 0,
        "failed_retry_records": [],
        "failed_retry_record_count": 0,
        "model_version_control_projections": [],
        "model_version_control_projection_count": 0,
        "cost_control_projections": [],
        "cost_control_projection_count": 0,
        "external_api_audit_projections": [],
        "external_api_audit_projection_count": 0,
        "control_request_reference_validation_performed": True,
        "control_policy_inheritance_projection_performed": False,
        "control_embedding_queue_projection_performed": False,
        "control_cache_projection_performed": False,
        "control_retry_projection_performed": False,
        "control_model_version_projection_performed": False,
        "control_cost_projection_performed": False,
        "control_external_api_audit_projection_performed": False,
        **_runtime_closed_flags(),
    }


def _runtime_closed_flags() -> dict[str, bool]:
    return {
        "actual_data_source_policy_read": False,
        "actual_document_policy_resolved": False,
        "actual_chunk_policy_assigned": False,
        "actual_policy_resolution_record_created": False,
        "actual_embedding_queue_request_created": False,
        "actual_cache_entry_created": False,
        "actual_cache_read_or_write_performed": False,
        "actual_failed_retry_record_created": False,
        "actual_retry_execution_performed": False,
        "actual_cost_estimation_performed": False,
        "actual_budget_lookup_performed": False,
        "actual_model_version_record_created": False,
        "actual_external_api_audit_record_created": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "chunking_execution_performed": False,
        "summary_generation_performed": False,
        "external_payload_created": False,
        "embedding_queue_execution_performed": False,
        "cache_read_or_write_performed": False,
        "failed_retry_execution_performed": False,
        "cost_estimation_execution_performed": False,
        "budget_lookup_performed": False,
        "model_version_record_execution_performed": False,
        "provider_credential_read_performed": False,
        "provider_or_model_selected": False,
        "external_api_client_initialized": False,
        "external_api_call_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
    }
