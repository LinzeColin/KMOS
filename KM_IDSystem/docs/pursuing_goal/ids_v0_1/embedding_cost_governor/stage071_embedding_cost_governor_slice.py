"""Stage071 P2 的纯内存 Embedding 成本治理控制切片。

模块只接受七条固定、非业务、reference-only 控制请求，在内存中机械投影
策略继承、未来 Embedding 队列/缓存/重试、三重预算关闭、成本与模型版本、
以及外部 API 审计字段。它不会读取来源正文、摘要、文本块、物理路径或真实
URI；不会创建持久队列、缓存、重试、成本或审计记录；也不会选择 provider/
模型、调用外部 API 或消耗模型 Token。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage071.embedding_cost_governor.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EMBEDDING_COST_GOVERNOR"
CONTROL_ADAPTER_VERSION = "ids.embedding_cost_governor.control_adapter.v0_1.stage071.p2"
CONTROL_FIELDS = ("embedding_cost_governor_requests",)

POLICY_VALUES = ("denied", "summary_only", "full_text_allowed")
POLICY_RANK = {policy: rank for rank, policy in enumerate(POLICY_VALUES)}
BUDGET_AVAILABLE = "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY"
BUDGET_DENIED_NOT_APPLICABLE = "CONTROL_BUDGET_NOT_APPLICABLE_POLICY_DENIED"
BUDGET_INSUFFICIENT = "CONTROL_BUDGET_INSUFFICIENT"
TASK_CAP_EXCEEDED = "CONTROL_TASK_CAP_EXCEEDED"

CONTROL_SCENARIOS = (
    "default_denied",
    "summary_only_inherited_all_budget_gates_pass",
    "document_restricts_full_text_to_summary_only_all_budget_gates_pass",
    "full_text_allowed_all_budget_gates_pass",
    "current_batch_budget_insufficient_pauses_full_text",
    "monthly_budget_insufficient_pauses_full_text",
    "single_task_cap_exceeded_pauses_full_text",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "default_denied": {
        "source_policy": "denied",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_DENIED_NOT_APPLICABLE,
        "monthly_budget_check_state": BUDGET_DENIED_NOT_APPLICABLE,
        "task_budget_cap_check_state": BUDGET_DENIED_NOT_APPLICABLE,
    },
    "summary_only_inherited_all_budget_gates_pass": {
        "source_policy": "summary_only",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_AVAILABLE,
        "monthly_budget_check_state": BUDGET_AVAILABLE,
        "task_budget_cap_check_state": BUDGET_AVAILABLE,
    },
    "document_restricts_full_text_to_summary_only_all_budget_gates_pass": {
        "source_policy": "full_text_allowed",
        "document_policy": "summary_only",
        "batch_budget_check_state": BUDGET_AVAILABLE,
        "monthly_budget_check_state": BUDGET_AVAILABLE,
        "task_budget_cap_check_state": BUDGET_AVAILABLE,
    },
    "full_text_allowed_all_budget_gates_pass": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_AVAILABLE,
        "monthly_budget_check_state": BUDGET_AVAILABLE,
        "task_budget_cap_check_state": BUDGET_AVAILABLE,
    },
    "current_batch_budget_insufficient_pauses_full_text": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_INSUFFICIENT,
        "monthly_budget_check_state": BUDGET_AVAILABLE,
        "task_budget_cap_check_state": BUDGET_AVAILABLE,
    },
    "monthly_budget_insufficient_pauses_full_text": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_AVAILABLE,
        "monthly_budget_check_state": BUDGET_INSUFFICIENT,
        "task_budget_cap_check_state": BUDGET_AVAILABLE,
    },
    "single_task_cap_exceeded_pauses_full_text": {
        "source_policy": "full_text_allowed",
        "document_policy": None,
        "batch_budget_check_state": BUDGET_AVAILABLE,
        "monthly_budget_check_state": BUDGET_AVAILABLE,
        "task_budget_cap_check_state": TASK_CAP_EXCEEDED,
    },
}

REFERENCE_INPUT_FIELDS = (
    "cost_governor_request_ref",
    "embedding_queue_request_ref",
    "policy_resolution_ref",
    "data_source_ref",
    "document_ref",
    "chunk_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "provider_ref",
    "model_ref",
    "model_version",
    "estimated_token_count",
    "batch_budget_ref",
    "monthly_budget_ref",
    "task_budget_cap_ref",
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
COST_GOVERNOR_FIELDS = (
    "cost_governor_request_ref",
    "embedding_queue_request_ref",
    "effective_external_api_policy",
    "provider_ref",
    "model_ref",
    "model_version",
    "estimated_token_count",
    "estimated_cost",
    "cost_currency",
    "batch_budget_ref",
    "monthly_budget_ref",
    "task_budget_cap_ref",
    "batch_budget_check_state",
    "monthly_budget_check_state",
    "task_budget_cap_check_state",
    "external_api_audit_ref",
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


def build_control_request(scenario: str) -> dict[str, Any]:
    """返回固定控制请求；其中没有正文、路径、真实 URI 或业务标识。"""

    if scenario not in CONTROL_SCENARIO_CONFIGURATION:
        raise ValueError("unknown embedding cost governor control scenario")
    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    effective_policy, _ = resolve_effective_policy(
        config["source_policy"], config["document_policy"]
    )
    marker = f":control:stage071-p2:{scenario}"
    return {
        "cost_governor_request_ref": f"cost-governor-request{marker}",
        "embedding_queue_request_ref": f"embedding-queue-request{marker}",
        "policy_resolution_ref": f"policy-resolution{marker}",
        "data_source_ref": f"data-source{marker}",
        "document_ref": f"document{marker}",
        "chunk_ref": f"chunk{marker}",
        "effective_external_api_policy": effective_policy,
        "external_payload_mode": _external_payload_mode(effective_policy),
        "provider_ref": f"provider{marker}",
        "model_ref": f"model{marker}",
        "model_version": f"model-version{marker}",
        "estimated_token_count": 0,
        "batch_budget_ref": f"batch-budget{marker}",
        "monthly_budget_ref": f"monthly-budget{marker}",
        "task_budget_cap_ref": f"task-budget-cap{marker}",
        "external_api_audit_ref": f"external-api-audit{marker}",
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦测试与本地回归使用。"""

    return {
        "embedding_cost_governor_requests": [
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


def execute_embedding_cost_governor_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定策略、队列/缓存、三重预算、成本/版本和审计控制记录。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    resolutions = [
        _policy_resolution(scenario, request)
        for scenario, request in zip(CONTROL_SCENARIOS, requests)
    ]
    governor_records = [
        _cost_governor_record(scenario, resolution, request)
        for scenario, resolution, request in zip(
            CONTROL_SCENARIOS, resolutions, requests
        )
    ]
    queue_records = [
        _queue_record(resolution, governor, request)
        for resolution, governor, request in zip(
            resolutions, governor_records, requests
        )
    ]
    cache_records = [
        _cache_record(resolution, governor, request)
        for resolution, governor, request in zip(
            resolutions, governor_records, requests
        )
    ]
    retry_records = [
        _retry_record(resolution, governor, request)
        for resolution, governor, request in zip(
            resolutions, governor_records, requests
        )
    ]
    audit_projections = [
        _audit_projection(resolution, governor, request)
        for resolution, governor, request in zip(
            resolutions, governor_records, requests
        )
    ]

    queue_states = [record["control_queue_state"] for record in queue_records]
    cache_states = [record["cache_disposition"] for record in cache_records]
    retry_states = [record["retry_state"] for record in retry_records]
    governor_states = [
        record["control_cost_governor_state"] for record in governor_records
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE",
        "control_request_count": len(requests),
        "actual_input_request_count": 0,
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "policy_resolutions": resolutions,
        "policy_resolution_count": len(resolutions),
        "all_chunks_inherit_effective_document_policy_automatically": True,
        "chunk_manual_policy_assignment_performed": False,
        "cost_governor_records": governor_records,
        "cost_governor_record_count": len(governor_records),
        "embedding_queue_records": queue_records,
        "embedding_queue_record_count": len(queue_records),
        "cache_records": cache_records,
        "cache_record_count": len(cache_records),
        "failed_retry_records": retry_records,
        "failed_retry_record_count": len(retry_records),
        "external_api_audit_projections": audit_projections,
        "external_api_audit_projection_count": len(audit_projections),
        "control_cost_governor_blocked_policy_denied_count": governor_states.count(
            "CONTROL_COST_GOVERNOR_BLOCKED_POLICY_DENIED"
        ),
        "control_cost_governor_paused_three_budget_gates_count": governor_states.count(
            "CONTROL_COST_GOVERNOR_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED"
        ),
        "control_cost_governor_eligible_not_persisted_count": governor_states.count(
            "CONTROL_COST_GOVERNOR_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        ),
        "control_queue_blocked_policy_denied_count": queue_states.count(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED"
        ),
        "control_queue_paused_three_budget_gates_count": queue_states.count(
            "CONTROL_QUEUE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED"
        ),
        "control_queue_eligible_not_persisted_count": queue_states.count(
            "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        ),
        "control_cache_blocked_policy_denied_count": cache_states.count(
            "CONTROL_CACHE_BLOCKED_POLICY_DENIED"
        ),
        "control_cache_paused_three_budget_gates_count": cache_states.count(
            "CONTROL_CACHE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED"
        ),
        "control_cache_eligible_not_persisted_count": cache_states.count(
            "CONTROL_CACHE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        ),
        "control_retry_blocked_policy_denied_count": retry_states.count(
            "CONTROL_RETRY_BLOCKED_POLICY_DENIED"
        ),
        "control_retry_paused_three_budget_gates_count": retry_states.count(
            "CONTROL_RETRY_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED"
        ),
        "control_retry_not_scheduled_count": retry_states.count(
            "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED"
        ),
        "all_control_records_keep_required_shapes": _all_record_shapes_are_exact(
            queue_records,
            cache_records,
            retry_records,
            governor_records,
            audit_projections,
        ),
        "all_three_budget_scope_failure_closures_covered": True,
        "source_body_summary_body_or_chunk_text_retained": False,
        "control_output_is_not_actual_queue_cache_retry_cost_or_audit": True,
        "control_request_reference_validation_performed": True,
        "control_policy_inheritance_projection_performed": True,
        "control_embedding_queue_projection_performed": True,
        "control_cache_projection_performed": True,
        "control_retry_projection_performed": True,
        "control_cost_governor_projection_performed": True,
        "control_external_api_audit_projection_performed": True,
        "chinese_feedback": [
            "当前只在内存中投影七条固定成本治理控制记录，未读取或保留真实资料、摘要正文、文本块、路径、页面或业务结论。",
            "有效外部 API 策略从 data source 经 document 自动继承到 chunk；默认 denied，document 不能放宽来源策略，也不能手工标记单个 chunk。",
            "策略拒绝时成本治理、队列、缓存和重试均关闭；本批次、自然月或单任务任一预算门未通过时只暂停控制候选，任何可行候选也不会被持久化或调度。",
            "provider、model、model_version、token、chunk 和 policy reason 都只是固定控制引用或零值投影；本切片未选择 provider 或模型，未调用外部 API，业务线例外仍需白箱人工复核。",
        ],
        **_runtime_closed_flags(),
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, Any]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("embedding_cost_governor_requests")
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
        "budget_check_state": _aggregate_budget_state(config, effective_policy),
    }


def _cost_governor_record(
    scenario: str, resolution: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    state, reason = _control_disposition(resolution, config)
    return {
        "cost_governor_request_ref": request["cost_governor_request_ref"],
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "effective_external_api_policy": resolution["effective_external_api_policy"],
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "cost_currency": "CONTROL_NO_CURRENCY_NO_EXTERNAL_COST",
        "batch_budget_ref": request["batch_budget_ref"],
        "monthly_budget_ref": request["monthly_budget_ref"],
        "task_budget_cap_ref": request["task_budget_cap_ref"],
        "batch_budget_check_state": config["batch_budget_check_state"],
        "monthly_budget_check_state": config["monthly_budget_check_state"],
        "task_budget_cap_check_state": config["task_budget_cap_check_state"],
        "external_api_audit_ref": request["external_api_audit_ref"],
        "control_cost_governor_state": f"CONTROL_COST_GOVERNOR_{state}",
        "control_cost_governor_reason": reason,
    }


def _queue_record(
    resolution: Mapping[str, Any],
    governor: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    state, reason = _control_disposition_from_governor(resolution, governor)
    return {
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "policy_resolution_ref": request["policy_resolution_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "external_payload_mode": request["external_payload_mode"],
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "estimated_token_count": 0,
        "estimated_cost": 0,
        "budget_check_state": resolution["budget_check_state"],
        "external_api_audit_ref": request["external_api_audit_ref"],
        "control_queue_state": f"CONTROL_QUEUE_{state}",
        "control_queue_reason": reason,
    }


def _cache_record(
    resolution: Mapping[str, Any],
    governor: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    state, _ = _control_disposition_from_governor(resolution, governor)
    return {
        "cache_entry_ref": _derived_ref("cache-entry", request),
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "policy_resolution_ref": request["policy_resolution_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "external_payload_mode": request["external_payload_mode"],
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "cache_disposition": f"CONTROL_CACHE_{state}",
    }


def _retry_record(
    resolution: Mapping[str, Any],
    governor: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    state, reason = _control_disposition_from_governor(resolution, governor)
    retry_state = f"CONTROL_RETRY_{state}"
    if retry_state == "CONTROL_RETRY_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED":
        retry_state = "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED"
    return {
        "retry_ref": _derived_ref("retry", request),
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "policy_resolution_ref": request["policy_resolution_ref"],
        "budget_check_state": resolution["budget_check_state"],
        "external_api_audit_ref": request["external_api_audit_ref"],
        "retry_state": retry_state,
        "retry_reason": reason,
    }


def _audit_projection(
    resolution: Mapping[str, Any],
    governor: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    state, _ = _control_disposition_from_governor(resolution, governor)
    if state == "BLOCKED_POLICY_DENIED":
        disposition = "BLOCKED_POLICY_DENIED"
    elif state == "PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED":
        disposition = "PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED"
    else:
        disposition = "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL"
    return {
        "external_api_audit_ref": request["external_api_audit_ref"],
        "data_source_ref": request["data_source_ref"],
        "document_ref": request["document_ref"],
        "chunk_ref": request["chunk_ref"],
        "effective_external_api_policy": resolution["effective_external_api_policy"],
        "external_payload_mode": resolution["external_payload_mode"],
        "policy_inheritance_reason": resolution["policy_inheritance_reason"],
        "owner_authorization_ref": _derived_ref("owner-authorization", request),
        "authorized_at": _derived_ref("authorized-at", request),
        "authorization_reason": _derived_ref("authorization-reason", request),
        "provider_ref": request["provider_ref"],
        "model_ref": request["model_ref"],
        "model_version": request["model_version"],
        "token_count": 0,
        "cost_estimate": 0,
        "embedding_queue_request_ref": request["embedding_queue_request_ref"],
        "budget_check_state": resolution["budget_check_state"],
        "audit_disposition": disposition,
    }


def _control_disposition(
    resolution: Mapping[str, Any], config: Mapping[str, str | None]
) -> tuple[str, str]:
    if resolution["effective_external_api_policy"] == "denied":
        return (
            "BLOCKED_POLICY_DENIED",
            "CONTROL_EXTERNALIZATION_FORBIDDEN_BY_EFFECTIVE_POLICY",
        )
    if not _all_three_budget_gates_pass(config):
        return (
            "PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
            "CONTROL_NO_EXTERNAL_TASK_CREATED_UNTIL_ALL_THREE_BUDGET_GATES_PASS",
        )
    return (
        "ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "CONTROL_REFERENCE_ONLY_NO_QUEUE_CACHE_OR_PROVIDER_INITIALIZED",
    )


def _control_disposition_from_governor(
    resolution: Mapping[str, Any], governor: Mapping[str, Any]
) -> tuple[str, str]:
    state = str(governor["control_cost_governor_state"]).replace(
        "CONTROL_COST_GOVERNOR_", "", 1
    )
    return state, str(governor["control_cost_governor_reason"])


def _all_three_budget_gates_pass(config: Mapping[str, str | None]) -> bool:
    return all(
        config[field] == BUDGET_AVAILABLE
        for field in (
            "batch_budget_check_state",
            "monthly_budget_check_state",
            "task_budget_cap_check_state",
        )
    )


def _aggregate_budget_state(
    config: Mapping[str, str | None], effective_policy: str
) -> str:
    if effective_policy == "denied":
        return BUDGET_DENIED_NOT_APPLICABLE
    if _all_three_budget_gates_pass(config):
        return "CONTROL_ALL_THREE_BUDGET_GATES_AVAILABLE_REFERENCE_ONLY"
    return "CONTROL_BUDGET_GATE_NOT_PASSED"


def _external_payload_mode(effective_policy: str) -> str:
    if effective_policy == "denied":
        return "NO_EXTERNAL_PAYLOAD_POLICY_DENIED"
    if effective_policy == "summary_only":
        return "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY"
    return "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY"


def _derived_ref(prefix: str, request: Mapping[str, Any]) -> str:
    marker = str(request["cost_governor_request_ref"]).replace(
        "cost-governor-request", "", 1
    )
    return f"{prefix}{marker}"


def _all_record_shapes_are_exact(
    queue_records: Sequence[Mapping[str, Any]],
    cache_records: Sequence[Mapping[str, Any]],
    retry_records: Sequence[Mapping[str, Any]],
    governor_records: Sequence[Mapping[str, Any]],
    audit_projections: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        all(
            set(record)
            == set(QUEUE_FIELDS) | {"control_queue_state", "control_queue_reason"}
            for record in queue_records
        )
        and all(set(record) == set(CACHE_FIELDS) for record in cache_records)
        and all(set(record) == set(RETRY_FIELDS) for record in retry_records)
        and all(
            set(record)
            == set(COST_GOVERNOR_FIELDS)
            | {"control_cost_governor_state", "control_cost_governor_reason"}
            for record in governor_records
        )
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
        "cost_governor_records": [],
        "cost_governor_record_count": 0,
        "embedding_queue_records": [],
        "embedding_queue_record_count": 0,
        "cache_records": [],
        "cache_record_count": 0,
        "failed_retry_records": [],
        "failed_retry_record_count": 0,
        "external_api_audit_projections": [],
        "external_api_audit_projection_count": 0,
        "control_request_reference_validation_performed": True,
        "control_policy_inheritance_projection_performed": False,
        "control_embedding_queue_projection_performed": False,
        "control_cache_projection_performed": False,
        "control_retry_projection_performed": False,
        "control_cost_governor_projection_performed": False,
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
        "actual_cost_governor_record_created": False,
        "actual_cost_estimation_performed": False,
        "actual_batch_budget_lookup_performed": False,
        "actual_monthly_budget_lookup_performed": False,
        "actual_task_cap_evaluation_performed": False,
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
        "failed_retry_execution_performed": False,
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
