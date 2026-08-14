"""Stage070 P4 的 Embedding 队列、缓存与外发控制交付证据。

模块只从 P3 五条固定、非业务、reference-only 控制场景派生内存交付样例、
审计投影样例、零成本估算、失败处理、未外发原因、查询和回滚说明。它不读取
来源、不保留摘要或文本块、不写审计日志或队列，也不选择 provider/模型、调用
外部 API、消耗 Token、连接数据库或启动运行时服务。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage070.embedding_queue_cache.phase4.delivery.v1"
RECORD_KIND = "EMBEDDING_QUEUE_CACHE_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_PHASE4_EMBEDDING_QUEUE_CACHE_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EMBEDDING_QUEUE_CACHE_DELIVERY_EVIDENCE"
ENTRY_GATE = "IDS-STAGE070-P4-GATE"
NEXT_GATE = "IDS-STAGE070-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_EMBEDDING_QUEUE_CACHE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

POLICY_SAMPLE_KIND = "DELIVERY_METADATA_ONLY_EMBEDDING_QUEUE_CACHE_POLICY_SAMPLE_NOT_REAL_PAYLOAD"
AUDIT_LOG_SAMPLE_KIND = "CONTROL_EMBEDDING_QUEUE_CACHE_AUDIT_LOG_SAMPLE_NOT_PERSISTED"
COST_ESTIMATE_SAMPLE_KIND = "CONTROL_ZERO_COST_ESTIMATE_NOT_PROVIDER_PRICE"
FAILURE_HANDLING_KIND = "CONTROL_QUEUE_CACHE_RETRY_FAILURE_HANDLING_NOT_REAL_FAILURE_RECORD"
NON_EXTERNALIZED_DATA_KIND = "CONTROL_NON_EXTERNALIZED_QUEUE_CACHE_REFERENCE_NOT_REAL_DATA"
QUERY_INSTRUCTION_KIND = "EMBEDDING_QUEUE_CACHE_EXTERNALIZATION_RECORD_QUERY_INSTRUCTIONS_IN_MEMORY_CONTROL_ONLY"
ROLLBACK_INSTRUCTION_KIND = "EMBEDDING_QUEUE_CACHE_POLICY_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"

EXPECTED_SCENARIO_IDS = (
    "denied-policy-blocks-queue-cache-retry-and-externalization-control",
    "summary-only-policy-limits-control-payload",
    "document-restriction-limits-full-text-to-summary-control",
    "full-text-policy-allows-only-control-text-reference",
    "budget-insufficient-pauses-full-text-control",
)
P3_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "referenced_policy_resolution_ref",
    "referenced_embedding_queue_request_ref",
    "referenced_cache_entry_ref",
    "referenced_retry_ref",
    "referenced_external_api_audit_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "observed_control_payload_scope",
    "expected_control_payload_scope",
    "expected_queue_state",
    "observed_queue_state",
    "expected_cache_disposition",
    "observed_cache_disposition",
    "expected_retry_state",
    "observed_retry_state",
    "audit_projection_required",
    "audit_projection_present",
    "audit_field_count",
    "audit_disposition",
    "future_external_api_call_candidate",
    "actual_external_api_call_performed",
    "actual_model_token_consumption_performed",
    "human_handling_required",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)
CONTROL_AUDIT_PROJECTION_FIELDS = (
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
CONTROL_POLICY_INHERITANCE_REASON_BY_PHASE2_SCENARIO = {
    "default_denied": "CONTROL_INHERITED_FROM_DATA_SOURCE",
    "summary_only_inherited": "CONTROL_INHERITED_FROM_DATA_SOURCE",
    "document_restricts_full_text_to_summary_only": (
        "CONTROL_DOCUMENT_POLICY_RESTRICTED_EFFECTIVE"
    ),
    "full_text_allowed_control_only": "CONTROL_INHERITED_FROM_DATA_SOURCE",
    "budget_insufficient_pauses_full_text": "CONTROL_INHERITED_FROM_DATA_SOURCE",
}
CONTROL_BUDGET_CHECK_STATE_BY_PHASE2_SCENARIO = {
    "default_denied": "CONTROL_BUDGET_NOT_APPLICABLE_POLICY_DENIED",
    "summary_only_inherited": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
    "document_restricts_full_text_to_summary_only": (
        "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY"
    ),
    "full_text_allowed_control_only": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
    "budget_insufficient_pauses_full_text": "CONTROL_BUDGET_INSUFFICIENT",
}
P3_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_recorded",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "external_payload_created",
    "actual_external_payload_created",
    "control_payload_content_retained",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "phase4_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "stage071_started",
    "github_upload_allowed",
    "push_allowed",
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_recorded",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "external_payload_created",
    "actual_external_payload_created",
    "control_payload_content_retained",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "actual_delivery_file_written",
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]


def build_embedding_queue_cache_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
) -> dict[str, Any]:
    """输出 P4 纯内存交付证据；P3 形状异常时失败关闭。"""

    provider = phase3_report_provider or _load_phase3_report_provider()
    try:
        candidate = provider()
    except (OSError, RuntimeError, TypeError, ValueError):
        candidate = {}
    phase3_report = candidate if isinstance(candidate, Mapping) else {}
    predecessor_valid = _phase3_report_is_valid(phase3_report)
    scenarios = _scenario_results(phase3_report) if predecessor_valid else []
    policy_samples = [_policy_sample(item) for item in scenarios]
    audit_log_samples = [_audit_log_sample(item) for item in scenarios]
    cost_estimate_samples = [_cost_estimate_sample(item) for item in scenarios]
    failure_handling_results = [_failure_handling_result(item) for item in scenarios]
    non_externalized_data_records = [
        _non_externalized_data_record(item) for item in scenarios
    ]
    query_instructions = _query_instructions(predecessor_valid)
    rollback_instructions = _rollback_instructions()
    valid = (
        predecessor_valid
        and _expected_scenario_ids(policy_samples)
        and len(audit_log_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(cost_estimate_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(failure_handling_results) == len(EXPECTED_SCENARIO_IDS)
        and len(non_externalized_data_records) == len(EXPECTED_SCENARIO_IDS)
        and all(_audit_log_sample_has_exact_projection(item) for item in audit_log_samples)
        and all(item["token_count"] == 0 for item in cost_estimate_samples)
        and all(item["cost_estimate"] == 0 for item in cost_estimate_samples)
        and all(
            item["externalization_performed"] is False
            for item in non_externalized_data_records
        )
        and query_instructions["query_contract_available"]
        and rollback_instructions["rollback_target_result"] == P3_PASS_RESULT
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "entry_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": predecessor_valid,
        "phase3_controlled_scenarios_report_valid": predecessor_valid,
        "embedding_queue_cache_policy_samples": policy_samples,
        "embedding_queue_cache_policy_sample_lines": tuple(
            _json_line(item) for item in policy_samples
        ),
        "control_audit_log_samples": audit_log_samples,
        "cost_estimate_samples": cost_estimate_samples,
        "failure_handling_results": failure_handling_results,
        "non_externalized_data_records": non_externalized_data_records,
        "externalization_record_query_instructions": query_instructions,
        "policy_rollback_instructions": rollback_instructions,
        "human_confirmation_prompts_zh": _human_confirmation_prompts(),
        "source_document_remains_authoritative": True,
        "business_line_white_box_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "real_source_content_retained": False,
        "actual_input_request_count": 0,
        "actual_embedding_queue_count": 0,
        "actual_cache_entry_count": 0,
        "actual_failed_retry_count": 0,
        "actual_external_payload_count": 0,
        "actual_external_api_call_count": 0,
        "actual_model_token_count": 0,
        "actual_cost_count": 0,
        "actual_external_api_audit_log_count": 0,
        "actual_failure_record_count": 0,
        "actual_non_externalized_data_record_count": 0,
        "actual_delivery_file_written": False,
        **_runtime_closed_flags(),
        "stage070_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage071_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "chinese_feedback": [
            "已从五条固定队列、缓存和重试控制场景生成策略样例、审计投影样例、零成本估算和失败处理结果；它们不是实际外发、审计日志、成本记录或业务资料。",
            "五条控制引用均未外发：denied 被策略阻断，摘要和文本块引用仍需业务线白箱复核且运行时关闭，预算不足项保持队列、缓存和重试暂停；没有形成真实载荷。",
            "外发记录查询只说明在本报告内按场景和策略、队列、缓存、重试及审计控制引用核对投影；当前没有持久审计日志、真实外发记录或可供查询的生产历史。",
            "如需撤回本 phase，只撤回 P4 交付工件并回到 P3 控制场景，不改动真实资料、审计日志、成本、队列、缓存、数据库、OVH 或部署。",
        ],
    }


def _load_phase3_report_provider() -> Phase3ReportProvider:
    module_path = Path(__file__).with_name("stage070_embedding_queue_cache_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage070_p3", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage070 P3 controlled-scenarios module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, "build_embedding_queue_cache_phase3_report", None)
    if not callable(provider):
        raise RuntimeError("Stage070 P3 report provider is unavailable")
    return provider


def _phase3_report_is_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _scenario_results(report)
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == ENTRY_GATE
        and report.get("phase2_control_slice_reexecuted") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("explicit_disposition_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("silent_drop_count") == 0
        and report.get("human_handling_required_count") == 4
        and report.get("control_policy_resolution_record_count") == 5
        and report.get("control_embedding_queue_record_count") == 5
        and report.get("control_cache_record_count") == 5
        and report.get("control_failed_retry_record_count") == 5
        and report.get("control_external_api_audit_projection_count") == 5
        and report.get("control_audit_field_count") == 18
        and report.get("control_audit_field_check_count") == 90
        and report.get("audit_projection_required_count") == 5
        and report.get("audit_projection_present_count") == 5
        and report.get("future_external_api_call_candidate_count") == 3
        and report.get("denied_control_blocked_count") == 1
        and report.get("summary_only_control_scope_count") == 2
        and report.get("full_text_control_scope_count") == 1
        and report.get("budget_insufficient_paused_count") == 1
        and report.get("actual_input_request_count") == 0
        and report.get("actual_embedding_queue_count") == 0
        and report.get("actual_cache_entry_count") == 0
        and report.get("actual_failed_retry_count") == 0
        and report.get("actual_external_api_call_count") == 0
        and report.get("actual_model_token_count") == 0
        and report.get("actual_external_api_audit_record_count") == 0
        and report.get("source_document_remains_authoritative") is True
        and report.get("embedding_queue_cache_scenario_can_replace_source_document")
        is False
        and report.get("embedding_queue_cache_scenario_can_become_business_fact_authority")
        is False
        and tuple(item.get("scenario_id") for item in scenarios) == EXPECTED_SCENARIO_IDS
        and all(_scenario_is_control_only(item) for item in scenarios)
        and all(report.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS)
    )


def _scenario_results(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = report.get("scenario_results")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _scenario_is_control_only(item: Mapping[str, Any]) -> bool:
    references = (
        "referenced_policy_resolution_ref",
        "referenced_embedding_queue_request_ref",
        "referenced_cache_entry_ref",
        "referenced_retry_ref",
        "referenced_external_api_audit_ref",
    )
    return (
        set(item) == set(P3_SCENARIO_FIELDS)
        and item.get("expectation_met") is True
        and item.get("silent_drop") is False
        and item.get("audit_projection_required") is True
        and item.get("audit_projection_present") is True
        and item.get("audit_field_count") == 18
        and item.get("actual_external_api_call_performed") is False
        and item.get("actual_model_token_consumption_performed") is False
        and all(
            isinstance(item.get(field), str) and ":control:stage070-p2:" in item[field]
            for field in references
        )
    )


def _policy_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": f"embedding-queue-cache-policy-delivery-sample:{item['scenario_id']}",
        "sample_kind": POLICY_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "scenario_category": item["scenario_category"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "external_payload_mode": item["external_payload_mode"],
        "control_payload_scope": item["observed_control_payload_scope"],
        "control_queue_state": item["observed_queue_state"],
        "control_cache_disposition": item["observed_cache_disposition"],
        "control_retry_state": item["observed_retry_state"],
        "audit_disposition": item["audit_disposition"],
        "future_external_api_call_candidate": item["future_external_api_call_candidate"],
        "human_handling_required": item["human_handling_required"],
        "explicit_disposition": item["explicit_disposition"],
        "control_metadata_only": True,
        "source_content_retained": False,
        "actual_external_payload_created": False,
        "actual_embedding_queue_created": False,
        "actual_cache_entry_created": False,
        "actual_failed_retry_record_created": False,
        "actual_external_api_call_performed": False,
        "actual_model_token_consumption_performed": False,
    }


def _audit_log_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    projection = _control_audit_projection(item)
    return {
        "audit_log_sample_id": f"embedding-queue-cache-audit-log-sample:{item['scenario_id']}",
        "record_kind": AUDIT_LOG_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "external_api_audit_ref": projection.get("external_api_audit_ref"),
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": projection.get("embedding_queue_request_ref"),
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "audit_projection": projection,
        "audit_field_count": len(projection),
        "audit_projection_required": True,
        "audit_projection_present": True,
        "control_metadata_only": True,
        "actual_audit_record_created": False,
        "actual_audit_record_persisted": False,
    }


def _control_audit_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    """从 P3 的控制场景重建 P2 已冻结的十八字段审计投影形状。"""

    phase2_scenario = item.get("phase2_control_scenario")
    if (
        not isinstance(phase2_scenario, str)
        or phase2_scenario not in CONTROL_POLICY_INHERITANCE_REASON_BY_PHASE2_SCENARIO
        or phase2_scenario not in CONTROL_BUDGET_CHECK_STATE_BY_PHASE2_SCENARIO
    ):
        return {}
    marker = f":control:stage070-p2:{phase2_scenario}"
    return {
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "data_source_ref": f"data-source{marker}",
        "document_ref": f"document{marker}",
        "chunk_ref": f"chunk{marker}",
        "effective_external_api_policy": item["effective_external_api_policy"],
        "external_payload_mode": item["external_payload_mode"],
        "policy_inheritance_reason": (
            CONTROL_POLICY_INHERITANCE_REASON_BY_PHASE2_SCENARIO[phase2_scenario]
        ),
        "owner_authorization_ref": f"owner-authorization{marker}",
        "authorized_at": f"authorized-at{marker}",
        "authorization_reason": f"authorization-reason{marker}",
        "provider_ref": f"provider{marker}",
        "model_ref": f"model{marker}",
        "model_version": f"model-version{marker}",
        "token_count": 0,
        "cost_estimate": 0,
        "embedding_queue_request_ref": item[
            "referenced_embedding_queue_request_ref"
        ],
        "budget_check_state": (
            CONTROL_BUDGET_CHECK_STATE_BY_PHASE2_SCENARIO[phase2_scenario]
        ),
        "audit_disposition": item["audit_disposition"],
    }


def _audit_log_sample_has_exact_projection(item: Mapping[str, Any]) -> bool:
    projection = item.get("audit_projection")
    return (
        isinstance(projection, Mapping)
        and set(projection) == set(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("external_api_audit_ref")
        == projection.get("external_api_audit_ref")
        and item.get("embedding_queue_request_ref")
        == projection.get("embedding_queue_request_ref")
        and projection.get("token_count") == 0
        and projection.get("cost_estimate") == 0
        and all(
            isinstance(projection.get(field), str)
            and ":control:stage070-p2:" in projection[field]
            for field in (
                "external_api_audit_ref",
                "data_source_ref",
                "document_ref",
                "chunk_ref",
                "owner_authorization_ref",
                "authorized_at",
                "authorization_reason",
                "provider_ref",
                "model_ref",
                "model_version",
                "embedding_queue_request_ref",
            )
        )
    )


def _cost_estimate_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cost_estimate_id": f"embedding-queue-cache-cost-estimate-sample:{item['scenario_id']}",
        "record_kind": COST_ESTIMATE_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "token_count": 0,
        "cost_estimate": 0,
        "provider_selected": False,
        "model_selected": False,
        "actual_cost_recorded": False,
        "control_metadata_only": True,
    }


def _failure_handling_result(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "failure_handling_id": f"embedding-queue-cache-failure-handling:{item['scenario_id']}",
        "record_kind": FAILURE_HANDLING_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "failure_state": _failure_state(item),
        "handling_result": item["explicit_disposition"],
        "queue_cache_retry_stopped_or_paused": True,
        "externalization_stopped": True,
        "silent_drop": False,
        "human_handling_required": item["human_handling_required"],
        "control_metadata_only": True,
        "actual_failure_record_created": False,
    }


def _failure_state(item: Mapping[str, Any]) -> str:
    if item["effective_external_api_policy"] == "denied":
        return "POLICY_DENIED_QUEUE_CACHE_RETRY_BLOCKED_NO_EXTERNAL_PAYLOAD"
    if item["observed_queue_state"] == "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT":
        return "BUDGET_INSUFFICIENT_QUEUE_CACHE_RETRY_PAUSED_NO_EXTERNALIZATION"
    if item["effective_external_api_policy"] == "summary_only":
        return "WHITEBOX_REVIEW_REQUIRED_SUMMARY_REFERENCE_QUEUE_CACHE_NOT_PERSISTED"
    return "WHITEBOX_REVIEW_REQUIRED_CHUNK_REFERENCE_QUEUE_CACHE_NOT_PERSISTED"


def _non_externalized_data_record(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": f"embedding-queue-cache-non-externalized-reference:{item['scenario_id']}",
        "record_kind": NON_EXTERNALIZED_DATA_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "non_externalized_reference_category": item["observed_control_payload_scope"],
        "non_externalization_reason": _non_externalization_reason(item),
        "business_line_whitebox_review_required": item["human_handling_required"],
        "control_metadata_only": True,
        "source_content_retained": False,
        "externalization_performed": False,
        "actual_non_externalized_data_record_persisted": False,
    }


def _non_externalization_reason(item: Mapping[str, Any]) -> str:
    if item["effective_external_api_policy"] == "denied":
        return "默认 denied 策略阻断，未形成队列、缓存、重试或外发载荷。"
    if item["observed_queue_state"] == "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT":
        return "预算不足控制状态暂停队列、缓存和重试，未形成任何外发载荷。"
    if item["effective_external_api_policy"] == "summary_only":
        return "仅允许控制摘要引用类别，仍需业务线白箱复核且本 phase 运行时关闭。"
    return "仅允许控制文本块引用类别，仍需业务线白箱复核且本 phase 运行时关闭。"


def _query_instructions(predecessor_valid: bool) -> dict[str, Any]:
    return {
        "instruction_kind": QUERY_INSTRUCTION_KIND,
        "query_contract_available": predecessor_valid,
        "query_scope": "仅本 P4 内存控制交付报告，不是持久审计日志、队列/缓存记录或生产外发历史。",
        "query_keys": [
            "scenario_id",
            "external_api_audit_ref",
            "policy_resolution_ref",
            "embedding_queue_request_ref",
            "cache_entry_ref",
            "retry_ref",
        ],
        "query_result_kind": AUDIT_LOG_SAMPLE_KIND,
        "query_instruction_zh": "按场景 ID 或 :control: 审计、策略、队列、缓存、重试引用核对本报告的投影样例；不得将结果解释为真实外发记录。",
        "persistent_audit_log_available": False,
        "persistent_queue_or_cache_record_available": False,
        "actual_audit_log_query_performed": False,
        "actual_externalization_record_query_performed": False,
        "can_return_real_externalization_history": False,
    }


def _rollback_instructions() -> dict[str, Any]:
    return {
        "instruction_kind": ROLLBACK_INSTRUCTION_KIND,
        "rollback_target_result": P3_PASS_RESULT,
        "rollback_instruction": "仅撤回 P4 交付合同、纯内存模块、用例、run、事件、事实投影和生成中文视图，然后回到 P3 控制场景。",
        "query_after_rollback_instruction": "回退后只可重放 P3 控制场景；P4 内存样例不形成持久外发、审计、队列、缓存或重试记录。",
        "in_memory_control_replay_only": True,
        "phase1_phase2_phase3_artifacts_preserved": True,
        "actual_policy_rollback_performed": False,
        "source_or_raw_data_change_allowed": False,
        "fixture_change_allowed": False,
        "audit_log_change_allowed": False,
        "queue_or_cache_change_allowed": False,
        "database_schema_change_allowed": False,
        "persistent_runtime_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _expected_scenario_ids(samples: Sequence[Mapping[str, Any]]) -> bool:
    return tuple(sample.get("scenario_id") for sample in samples) == EXPECTED_SCENARIO_IDS


def _json_line(sample: Mapping[str, Any]) -> str:
    return json.dumps(sample, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _human_confirmation_prompts() -> list[str]:
    return [
        "请确认：五条策略、队列、缓存、重试、审计和成本样例均是控制元数据，不是实际外发、审计日志、成本或业务资料。",
        "请确认：未外发原因仅覆盖固定控制引用；真实资料是否可外发仍须业务线白箱人工复核。",
        "请确认：回滚只回到 P3 控制场景，查询只核对内存投影，不触及真实审计、队列、缓存、成本、OVH 或生产。",
    ]


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
