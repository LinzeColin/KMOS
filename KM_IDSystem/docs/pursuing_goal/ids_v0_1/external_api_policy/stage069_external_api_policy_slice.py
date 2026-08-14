"""Stage069 P2 的纯内存外部 API 策略继承控制切片。

本模块只接受五条固定、非业务、reference-only 控制请求，并在内存中投影
策略继承、Embedding 队列意图、缓存关闭、成本/模型版本字段和审计字段。
它不会读取来源或 chunk 正文，不会创建真实队列、缓存或审计记录，不会选择
provider/模型，也不会调用外部 API、消耗模型 Token、写入索引或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage069.external_api_policy.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_API_POLICY_INHERITANCE"
CONTROL_ADAPTER_VERSION = "ids.external_api_policy.control_adapter.v0_1.stage069.p2"
CONTROL_FIELDS = ("external_api_policy_requests",)

POLICY_VALUES = ("denied", "summary_only", "full_text_allowed")
POLICY_RANK = {policy: rank for rank, policy in enumerate(POLICY_VALUES)}

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
        "budget_check_state": "CONTROL_BUDGET_NOT_APPLICABLE_POLICY_DENIED",
    },
    "summary_only_inherited": {
        "source_policy": "summary_only",
        "document_policy": None,
        "budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
    },
    "document_restricts_full_text_to_summary_only": {
        "source_policy": "full_text_allowed",
        "document_policy": "summary_only",
        "budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
    },
    "full_text_allowed_control_only": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
    },
    "budget_insufficient_pauses_full_text": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "budget_check_state": "CONTROL_BUDGET_INSUFFICIENT",
    },
}

POLICY_INPUT_FIELDS = (
    "data_source_ref",
    "document_ref",
    "chunk_ref",
    "source_external_api_policy",
    "document_external_api_policy",
    "effective_external_api_policy",
    "policy_inheritance_reason",
    "owner_authorization_ref",
    "authorized_at",
    "authorization_reason",
    "provider_ref",
    "model_ref",
    "model_version",
    "embedding_queue_request_ref",
    "external_api_audit_ref",
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
    "policy_resolution_state",
    "external_payload_mode",
    "embedding_queue_request_ref",
    "budget_check_state",
    "estimated_token_count",
    "estimated_cost",
    "provider_ref",
    "model_ref",
    "model_version",
    "external_api_audit_ref",
    "audit_state",
    "policy_decision_reason",
    "owner_authorization_ref",
    "authorized_at",
    "authorization_reason",
)
QUEUE_INTENT_FIELDS = (
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
COST_MODEL_FIELDS = (
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
    "chunk_ref",
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


def build_control_request(scenario: str) -> dict[str, str | None]:
    """返回固定控制请求；其中没有来源正文、摘要正文、文本块或物理路径。"""

    if scenario not in CONTROL_SCENARIO_CONFIGURATION:
        raise ValueError("unknown external API policy control scenario")
    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = f":control:stage069-p2:{scenario}"
    return {
        "data_source_ref": f"data-source{marker}",
        "document_ref": f"document{marker}",
        "chunk_ref": f"chunk{marker}",
        "source_external_api_policy": config["source_policy"],
        "document_external_api_policy": config["document_policy"],
        "effective_external_api_policy": None,
        "policy_inheritance_reason": f"policy-inheritance-reason{marker}",
        "owner_authorization_ref": f"owner-authorization{marker}",
        "authorized_at": f"authorization-time{marker}",
        "authorization_reason": f"authorization-reason{marker}",
        "provider_ref": f"provider{marker}",
        "model_ref": f"model{marker}",
        "model_version": f"model-version{marker}",
        "embedding_queue_request_ref": f"embedding-queue-request{marker}",
        "external_api_audit_ref": f"external-api-audit{marker}",
    }


def build_control_input() -> dict[str, list[dict[str, str | None]]]:
    """返回完整固定控制输入，供本地单元测试使用。"""

    return {
        "external_api_policy_requests": [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def resolve_effective_policy(
    source_policy: object, document_policy: object
) -> tuple[str, str]:
    """纯函数：只解析枚举，不读取 data source/document/chunk。"""

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


def execute_external_api_policy_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定政策、队列意图、成本字段和审计字段。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    resolutions = [
        _policy_resolution(scenario, request)
        for scenario, request in zip(CONTROL_SCENARIOS, requests)
    ]
    queue_intents = [_queue_intent(resolution) for resolution in resolutions]
    queue_dispositions = [
        _queue_disposition(resolution) for resolution in resolutions
    ]
    cost_records = [_cost_model_record(resolution) for resolution in resolutions]
    audit_projections = [_audit_projection(resolution) for resolution in resolutions]
    effective_policies = [
        str(resolution["effective_external_api_policy"]) for resolution in resolutions
    ]
    queue_state_values = [
        disposition["control_queue_state"] for disposition in queue_dispositions
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": (
            "COMPLETED_IN_MEMORY_EXTERNAL_API_POLICY_INHERITANCE_CONTROL_SLICE"
        ),
        "control_policy_request_count": len(requests),
        "actual_input_request_count": 0,
        "policy_resolutions": resolutions,
        "policy_resolution_count": len(resolutions),
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "control_scenario_count": len(CONTROL_SCENARIOS),
        "one_control_resolution_per_scenario": len(resolutions)
        == len(CONTROL_SCENARIOS),
        "effective_policy_values_observed": effective_policies,
        "effective_policy_value_count": len(set(effective_policies)),
        "all_chunks_inherit_effective_document_policy_automatically": True,
        "chunk_manual_policy_assignment_performed": False,
        "embedding_queue_intents": queue_intents,
        "embedding_queue_intent_count": len(queue_intents),
        "queue_intent_dispositions": queue_dispositions,
        "control_queue_blocked_policy_denied_count": queue_state_values.count(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED"
        ),
        "control_queue_paused_budget_insufficient_count": queue_state_values.count(
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT"
        ),
        "control_queue_eligible_but_not_persisted_count": queue_state_values.count(
            "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        ),
        "cost_model_records": cost_records,
        "cost_model_record_count": len(cost_records),
        "external_api_audit_projections": audit_projections,
        "external_api_audit_projection_count": len(audit_projections),
        "all_control_audit_projections_have_required_fields": all(
            set(audit) == set(AUDIT_FIELDS) for audit in audit_projections
        ),
        "control_cache_state": "CONTROL_CACHE_DISABLED_NO_READ_OR_WRITE",
        "control_request_reference_validation_performed": True,
        "control_policy_resolution_projection_performed": True,
        "control_embedding_queue_intent_projection_performed": True,
        "control_cost_model_projection_performed": True,
        "control_external_api_audit_projection_performed": True,
        "source_body_summary_body_or_chunk_text_retained": False,
        "control_output_is_not_actual_policy_assignment_queue_cache_cost_or_audit": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影五条固定外部 API 策略控制记录，未读取或保留任何真实资料、摘要正文、文本块、路径、页面或业务结论。",
            "策略默认 denied；数据源或文档的有效策略自动继承到 chunk，系统不允许逐条手工标记 chunk。",
            "预算不足的控制记录只标记暂停；任何队列意图、缓存、成本、模型版本或审计字段都不会创建真实外部任务或持久记录。",
            "本切片未选择 provider 或模型，未调用外部 API，未消耗模型 Token，策略例外仍需业务线白箱人工复核。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, str | None]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(
        CONTROL_FIELDS
    ):
        return None
    requests = control_input.get("external_api_policy_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    expected = [build_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    if list(requests) != expected:
        return None
    return expected


def _policy_resolution(
    scenario: str, request: Mapping[str, str | None]
) -> dict[str, Any]:
    effective_policy, reason = resolve_effective_policy(
        request["source_external_api_policy"],
        request["document_external_api_policy"],
    )
    budget_state = CONTROL_SCENARIO_CONFIGURATION[scenario]["budget_check_state"]
    if effective_policy == "denied":
        external_payload_mode = "NO_EXTERNAL_PAYLOAD_POLICY_DENIED"
        audit_state = "CONTROL_AUDIT_DISPOSITION_BLOCKED_NOT_PERSISTED"
        decision_reason = "CONTROL_SOURCE_OR_DOCUMENT_POLICY_DENIED"
    elif effective_policy == "summary_only":
        external_payload_mode = "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY"
        audit_state = "CONTROL_AUDIT_PROJECTION_NOT_PERSISTED"
        decision_reason = "CONTROL_SUMMARY_ONLY_REQUIRES_FUTURE_AUTHORIZATION"
    else:
        external_payload_mode = "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY"
        audit_state = "CONTROL_AUDIT_PROJECTION_NOT_PERSISTED"
        decision_reason = "CONTROL_FULL_TEXT_REQUIRES_FUTURE_AUTHORIZATION"
    return {
        "policy_resolution_ref": (
            f"policy-resolution:control:stage069-p2:{scenario}"
        ),
        "data_source_ref": request["data_source_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "source_external_api_policy": request["source_external_api_policy"],
        "document_external_api_policy": request["document_external_api_policy"],
        "effective_external_api_policy": effective_policy,
        "policy_inheritance_reason": reason,
        "policy_resolution_state": (
            "CONTROL_RESOLVED_IN_MEMORY_NOT_PERSISTED"
        ),
        "external_payload_mode": external_payload_mode,
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "budget_check_state": budget_state,
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "external_api_audit_ref": request["external_api_audit_ref"],
        "audit_state": audit_state,
        "policy_decision_reason": decision_reason,
        "owner_authorization_ref": request["owner_authorization_ref"],
        "authorized_at": request["authorized_at"],
        "authorization_reason": request["authorization_reason"],
    }


def _queue_intent(resolution: Mapping[str, Any]) -> dict[str, Any]:
    return {field: resolution[field] for field in QUEUE_INTENT_FIELDS}


def _queue_disposition(resolution: Mapping[str, Any]) -> dict[str, Any]:
    effective_policy = resolution["effective_external_api_policy"]
    budget_state = resolution["budget_check_state"]
    if effective_policy == "denied":
        queue_state = "CONTROL_QUEUE_BLOCKED_POLICY_DENIED"
        reason = "CONTROL_EXTERNALIZATION_FORBIDDEN_BY_EFFECTIVE_POLICY"
    elif budget_state == "CONTROL_BUDGET_INSUFFICIENT":
        queue_state = "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT"
        reason = "CONTROL_NO_EXTERNAL_TASK_CREATED_WHEN_BUDGET_IS_INSUFFICIENT"
    else:
        queue_state = "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        reason = "CONTROL_INTENT_ONLY_NO_QUEUE_CACHE_OR_PROVIDER_INITIALIZED"
    return {
        "embedding_queue_request_ref": resolution["embedding_queue_request_ref"],
        "effective_external_api_policy": effective_policy,
        "budget_check_state": budget_state,
        "control_queue_state": queue_state,
        "control_queue_reason": reason,
    }


def _cost_model_record(resolution: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_ref": resolution["provider_ref"],
        "model_ref": resolution["model_ref"],
        "model_version": resolution["model_version"],
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "budget_check_state": resolution["budget_check_state"],
        "cost_currency": "CONTROL_NO_CURRENCY_NO_EXTERNAL_COST",
        "cost_estimation_reason": (
            "CONTROL_NO_EXTERNAL_PAYLOAD_OR_MODEL_CALL_WAS_CREATED"
        ),
    }


def _audit_projection(resolution: Mapping[str, Any]) -> dict[str, Any]:
    disposition = (
        "BLOCKED_POLICY_DENIED"
        if resolution["effective_external_api_policy"] == "denied"
        else "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL"
    )
    return {
        "external_api_audit_ref": resolution["external_api_audit_ref"],
        "data_source_ref": resolution["data_source_ref"],
        "document_ref": resolution["document_ref"],
        "chunk_ref": resolution["chunk_ref"],
        "effective_external_api_policy": resolution[
            "effective_external_api_policy"
        ],
        "external_payload_mode": resolution["external_payload_mode"],
        "policy_inheritance_reason": resolution["policy_inheritance_reason"],
        "owner_authorization_ref": resolution["owner_authorization_ref"],
        "authorized_at": resolution["authorized_at"],
        "authorization_reason": resolution["authorization_reason"],
        "provider_ref": resolution["provider_ref"],
        "model_ref": resolution["model_ref"],
        "model_version": resolution["model_version"],
        "token_count": 0,
        "cost_estimate": 0,
        "embedding_queue_request_ref": resolution["embedding_queue_request_ref"],
        "budget_check_state": resolution["budget_check_state"],
        "audit_disposition": disposition,
    }


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "control_policy_request_count": 0,
        "actual_input_request_count": 0,
        "policy_resolutions": [],
        "policy_resolution_count": 0,
        "embedding_queue_intents": [],
        "embedding_queue_intent_count": 0,
        "queue_intent_dispositions": [],
        "cost_model_records": [],
        "cost_model_record_count": 0,
        "external_api_audit_projections": [],
        "external_api_audit_projection_count": 0,
        "control_request_reference_validation_performed": True,
        "control_policy_resolution_projection_performed": False,
        "control_embedding_queue_intent_projection_performed": False,
        "control_cost_model_projection_performed": False,
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
        "actual_cache_read_or_write_performed": False,
        "actual_cost_recorded": False,
        "actual_model_version_recorded": False,
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
