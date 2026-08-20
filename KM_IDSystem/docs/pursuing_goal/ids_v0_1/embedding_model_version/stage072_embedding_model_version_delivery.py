"""Stage072 P4 Embedding 模型版本的 metadata-only 交付证据。

本模块只从已验证的 P3 五条固定、非业务、reference-only :control: 场景，
以及 P2 的纯内存控制切片派生策略样例、十八字段审计投影、零值成本估算、失败
处理、未外发原因、查询与回滚说明。所有结果只存在于当前 Python 进程，不能替代
来源文档、成为业务事实或发起外部调用。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage072.embedding_model_version.phase4.delivery.v1"
RECORD_KIND = "EMBEDDING_MODEL_VERSION_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_PHASE4_EMBEDDING_MODEL_VERSION_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EMBEDDING_MODEL_VERSION_DELIVERY_EVIDENCE"
ENTRY_GATE = "IDS-STAGE072-P4-GATE"
NEXT_GATE = "IDS-STAGE072-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_EMBEDDING_MODEL_VERSION_CONTROL_SLICE"

POLICY_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_EMBEDDING_MODEL_VERSION_POLICY_SAMPLE_NOT_REAL_PAYLOAD"
)
AUDIT_LOG_SAMPLE_KIND = (
    "CONTROL_EMBEDDING_MODEL_VERSION_AUDIT_LOG_SAMPLE_NOT_PERSISTED"
)
COST_ESTIMATE_SAMPLE_KIND = "CONTROL_ZERO_COST_ESTIMATE_NOT_PROVIDER_PRICE"
FAILURE_HANDLING_KIND = (
    "CONTROL_EMBEDDING_MODEL_VERSION_FAILURE_HANDLING_NOT_REAL_FAILURE_RECORD"
)
NON_EXTERNALIZED_DATA_KIND = (
    "CONTROL_NON_EXTERNALIZED_EMBEDDING_MODEL_VERSION_REFERENCE_NOT_REAL_DATA"
)
QUERY_INSTRUCTION_KIND = (
    "EMBEDDING_MODEL_VERSION_EXTERNALIZATION_RECORD_QUERY_INSTRUCTIONS_IN_MEMORY_CONTROL_ONLY"
)
ROLLBACK_INSTRUCTION_KIND = (
    "EMBEDDING_MODEL_VERSION_POLICY_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)

EXPECTED_SCENARIO_IDS = (
    "denied-policy-blocks-embedding-model-version-egress-control",
    "summary-only-policy-keeps-summary-reference-only-control",
    "document-restriction-keeps-full-text-at-summary-reference-control",
    "full-text-policy-keeps-chunk-reference-control-before-future-call",
    "budget-insufficient-pauses-full-text-external-api-control",
)
EXPECTED_SCENARIO_CATEGORIES = (
    "DENIED_EGRESS_BLOCK_CONTROL",
    "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL",
    "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL",
    "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL",
    "BUDGET_INSUFFICIENT_PAUSE_CONTROL",
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
    "expected_budget_check_state",
    "observed_budget_check_state",
    "audit_projection_required",
    "audit_projection_present",
    "audit_field_count",
    "audit_required_fields_present",
    "audit_reference_fields_are_control_only",
    "expected_audit_disposition",
    "observed_audit_disposition",
    "future_external_api_call_candidate",
    "actual_external_api_call_performed",
    "actual_model_token_consumption_performed",
    "model_version_sent_to_external_api",
    "human_handling_required",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)
P2_POLICY_RESOLUTION_FIELDS = (
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
P2_QUEUE_FIELDS = (
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
    "control_queue_state",
    "control_queue_reason",
)
P2_CACHE_FIELDS = (
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
P2_RETRY_FIELDS = (
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
CONTROL_AUDIT_PROJECTION_FIELDS = (
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
P2_RUNTIME_FALSE_FIELDS = (
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_estimation_performed",
    "actual_budget_lookup_performed",
    "actual_model_version_record_created",
    "actual_external_api_audit_record_created",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "external_payload_created",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "cost_estimation_execution_performed",
    "budget_lookup_performed",
    "model_version_record_execution_performed",
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
)
RUNTIME_CLOSED_FIELDS = (
    "authorized_fixture_access_performed",
    "actual_delivery_file_written",
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
    *P2_RUNTIME_FALSE_FIELDS,
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]
Phase2ReportProvider = Callable[[], Mapping[str, Any]]


def build_embedding_model_version_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
    phase2_report_provider: Phase2ReportProvider | None = None,
) -> dict[str, Any]:
    """派生 P4 纯内存交付证据；任一前序合同异常即失败关闭。"""

    phase3_provider = phase3_report_provider or _load_phase3_report_provider()
    phase3_report = _provider_result(phase3_provider)
    phase3_valid = _phase3_report_is_valid(phase3_report)
    phase2_provider = phase2_report_provider or _load_phase2_report_provider()
    phase2_report = _provider_result(phase2_provider) if phase3_valid else {}
    phase2_valid = _phase2_report_is_valid(phase2_report)
    scenarios = _mapping_sequence(phase3_report.get("scenario_results"))
    index = _phase2_index(phase2_report) if phase2_valid else {}

    if phase3_valid and phase2_valid:
        policy_samples = [_policy_sample(item, index) for item in scenarios]
        audit_log_samples = [_audit_log_sample(item, index) for item in scenarios]
        cost_estimate_samples = [
            _cost_estimate_sample(item, index) for item in scenarios
        ]
        failure_handling_results = [_failure_handling_result(item) for item in scenarios]
        non_externalized_data_records = [
            _non_externalized_data_record(item) for item in scenarios
        ]
    else:
        policy_samples = []
        audit_log_samples = []
        cost_estimate_samples = []
        failure_handling_results = []
        non_externalized_data_records = []

    query_instructions = _query_instructions(phase3_valid and phase2_valid)
    rollback_instructions = _rollback_instructions()
    runtime_closed_flags = _runtime_closed_flags()
    valid = (
        phase3_valid
        and phase2_valid
        and _expected_scenario_ids(policy_samples)
        and len(audit_log_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(cost_estimate_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(failure_handling_results) == len(EXPECTED_SCENARIO_IDS)
        and len(non_externalized_data_records) == len(EXPECTED_SCENARIO_IDS)
        and all(_policy_sample_is_control_only(item) for item in policy_samples)
        and all(_audit_log_sample_has_exact_projection(item) for item in audit_log_samples)
        and all(_cost_estimate_sample_is_zero(item) for item in cost_estimate_samples)
        and all(
            item["failure_closed"] is True
            and item["actual_failure_record_created"] is False
            and item["actual_retry_execution_performed"] is False
            for item in failure_handling_results
        )
        and all(
            item["externalization_performed"] is False
            and item["external_payload_created"] is False
            and item["source_content_retained"] is False
            and item["actual_external_api_call_performed"] is False
            for item in non_externalized_data_records
        )
        and sum(
            item["future_external_api_call_candidate"] for item in policy_samples
        )
        == 3
        and sum(
            item["effective_external_api_policy"] == "denied"
            for item in policy_samples
        )
        == 1
        and sum(
            item["control_budget_check_state"] == "CONTROL_BUDGET_INSUFFICIENT"
            for item in policy_samples
        )
        == 1
        and sum(item["human_handling_required"] for item in policy_samples) == 4
        and query_instructions["query_contract_available"] is True
        and rollback_instructions["rollback_target_result"] == P3_PASS_RESULT
        and all(runtime_closed_flags[field] is False for field in RUNTIME_CLOSED_FIELDS)
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "entry_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": phase3_valid,
        "phase3_controlled_scenarios_report_valid": phase3_valid,
        "phase2_control_slice_reexecuted_in_memory_only": phase2_valid,
        "embedding_model_version_policy_samples": policy_samples,
        "embedding_model_version_policy_sample_lines": tuple(
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
        "policy_sample_count": len(policy_samples),
        "control_audit_log_sample_count": len(audit_log_samples),
        "control_audit_field_count": len(CONTROL_AUDIT_PROJECTION_FIELDS),
        "control_audit_field_check_count": len(audit_log_samples)
        * len(CONTROL_AUDIT_PROJECTION_FIELDS),
        "zero_cost_estimate_sample_count": len(cost_estimate_samples),
        "failure_handling_result_count": len(failure_handling_results),
        "non_externalized_data_record_count": len(non_externalized_data_records),
        "future_external_api_call_candidate_count": sum(
            item["future_external_api_call_candidate"] for item in policy_samples
        ),
        "policy_denied_sample_count": sum(
            item["effective_external_api_policy"] == "denied"
            for item in policy_samples
        ),
        "budget_pause_sample_count": sum(
            item["control_budget_check_state"] == "CONTROL_BUDGET_INSUFFICIENT"
            for item in policy_samples
        ),
        "human_handling_required_count": sum(
            item["human_handling_required"] for item in policy_samples
        ),
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
        "stage071_review_evidence_read": True,
        "stage072_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage073_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本页仅展示五条固定控制样例，不代表已读取、保留或外发任何业务资料。",
            "策略、模型版本、审计与成本字段均为控制引用或零值投影；当前没有真实 provider、模型或外部调用。",
            "未授权、策略收紧、预算不足或尚未完成白箱复核时，控制引用均不会外发，且不会静默放行。",
            "回滚仅撤回本阶段交付工件并恢复到 P3 控制场景；不影响真实资料、审计日志、GitHub、OVH 或生产。",
        ],
    }


def _load_phase3_report_provider() -> Phase3ReportProvider:
    module = _load_module("stage072_embedding_model_version_scenarios.py")
    provider = getattr(module, "build_embedding_model_version_phase3_report", None)
    if not callable(provider):
        raise RuntimeError("Stage072 P3 scenario report provider is unavailable")
    return provider


def _load_phase2_report_provider() -> Phase2ReportProvider:
    module = _load_module("stage072_embedding_model_version_slice.py")
    input_builder = getattr(module, "build_control_input", None)
    executor = getattr(module, "execute_embedding_model_version_control_slice", None)
    if not callable(input_builder) or not callable(executor):
        raise RuntimeError("Stage072 P2 control slice provider is unavailable")
    return lambda: executor(input_builder())


def _load_module(filename: str) -> Any:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(
        f"stage072_embedding_model_version_{path.stem}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _phase3_report_is_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _mapping_sequence(report.get("scenario_results"))
    references = (
        "referenced_policy_resolution_ref",
        "referenced_embedding_queue_request_ref",
        "referenced_cache_entry_ref",
        "referenced_retry_ref",
        "referenced_external_api_audit_ref",
    )
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
        and report.get("control_audit_field_count")
        == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and report.get("control_audit_field_check_count")
        == len(EXPECTED_SCENARIO_IDS) * len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and report.get("future_external_api_call_candidate_count") == 3
        and report.get("actual_external_api_call_count") == 0
        and report.get("actual_model_token_count") == 0
        and report.get("source_document_remains_authoritative") is True
        and report.get("embedding_model_version_scenario_can_replace_source_document")
        is False
        and report.get("embedding_model_version_scenario_can_become_business_fact_authority")
        is False
        and report.get("stage072_started") is True
        and report.get("phase1_started") is True
        and report.get("phase2_started") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("batch_review_performed") is False
        and tuple(item.get("scenario_id") for item in scenarios)
        == EXPECTED_SCENARIO_IDS
        and tuple(item.get("scenario_category") for item in scenarios)
        == EXPECTED_SCENARIO_CATEGORIES
        and all(
            set(item) == set(P3_SCENARIO_FIELDS)
            and item.get("expectation_met") is True
            and item.get("silent_drop") is False
            and item.get("audit_projection_required") is True
            and item.get("audit_projection_present") is True
            and item.get("audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
            and item.get("audit_required_fields_present") is True
            and item.get("audit_reference_fields_are_control_only") is True
            and item.get("actual_external_api_call_performed") is False
            and item.get("actual_model_token_consumption_performed") is False
            and item.get("model_version_sent_to_external_api") is False
            and all(
                isinstance(item.get(field), str)
                and ":control:stage072-p2:" in item[field]
                for field in references
            )
            for item in scenarios
        )
    )


def _phase2_report_is_valid(report: Mapping[str, Any]) -> bool:
    checks = (
        ("policy_resolutions", P2_POLICY_RESOLUTION_FIELDS),
        ("embedding_queue_records", P2_QUEUE_FIELDS),
        ("cache_records", P2_CACHE_FIELDS),
        ("failed_retry_records", P2_RETRY_FIELDS),
        ("model_version_control_projections", MODEL_VERSION_FIELDS),
        ("cost_control_projections", COST_FIELDS),
        ("external_api_audit_projections", CONTROL_AUDIT_PROJECTION_FIELDS),
    )
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_request_count") == len(EXPECTED_SCENARIO_IDS)
        and tuple(report.get("control_scenarios_covered", ()))
        == (
            "default_denied",
            "summary_only_inherited",
            "document_restricts_full_text_to_summary_only",
            "full_text_allowed_control_only",
            "budget_insufficient_pauses_full_text",
        )
        and all(
            _records_have_exact_shape(
                report.get(key), len(EXPECTED_SCENARIO_IDS), fields
            )
            for key, fields in checks
        )
        and report.get("all_control_records_keep_required_shapes") is True
        and report.get("all_model_version_sent_statuses_are_false") is True
        and report.get("source_body_summary_body_or_chunk_text_retained") is False
        and report.get("actual_input_request_count") == 0
        and all(report.get(field) is False for field in P2_RUNTIME_FALSE_FIELDS)
    )


def _records_have_exact_shape(
    records: object, expected_count: int, fields: Sequence[str]
) -> bool:
    return (
        isinstance(records, list)
        and len(records) == expected_count
        and all(
            isinstance(record, Mapping) and set(record) == set(fields)
            for record in records
        )
    )


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _phase2_index(report: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    audits = _mapping_sequence(report.get("external_api_audit_projections"))
    models = _mapping_sequence(report.get("model_version_control_projections"))
    costs = _mapping_sequence(report.get("cost_control_projections"))
    policies = _mapping_sequence(report.get("policy_resolutions"))
    queues = _mapping_sequence(report.get("embedding_queue_records"))
    caches = _mapping_sequence(report.get("cache_records"))
    retries = _mapping_sequence(report.get("failed_retry_records"))
    index: dict[str, dict[str, Mapping[str, Any]]] = {}
    for audit, model, cost, policy, queue, cache, retry in zip(
        audits, models, costs, policies, queues, caches, retries
    ):
        audit_ref = audit.get("external_api_audit_ref")
        if isinstance(audit_ref, str):
            index[audit_ref] = {
                "audit": audit,
                "model": model,
                "cost": cost,
                "policy": policy,
                "queue": queue,
                "cache": cache,
                "retry": retry,
            }
    return index


def _p2_records_for(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> Mapping[str, Mapping[str, Any]]:
    records = index.get(item.get("referenced_external_api_audit_ref"))
    return records if isinstance(records, Mapping) else {}


def _policy_sample(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    records = _p2_records_for(item, index)
    model = records.get("model", {})
    return {
        "sample_id": (
            "embedding-model-version-policy-delivery-sample:"
            f"{item['scenario_id']}"
        ),
        "sample_kind": POLICY_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "scenario_category": item["scenario_category"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item[
            "referenced_embedding_queue_request_ref"
        ],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "external_payload_mode": item["external_payload_mode"],
        "control_payload_scope": item["observed_control_payload_scope"],
        "control_queue_state": item["observed_queue_state"],
        "control_cache_disposition": item["observed_cache_disposition"],
        "control_retry_state": item["observed_retry_state"],
        "control_budget_check_state": item["observed_budget_check_state"],
        "audit_disposition": item["observed_audit_disposition"],
        "provider_ref": model.get("provider_ref"),
        "model_ref": model.get("model_ref"),
        "model_version": model.get("model_version"),
        "dimension": model.get("dimension"),
        "created_at": model.get("created_at"),
        "sent_to_external_api": model.get("sent_to_external_api"),
        "future_external_api_call_candidate": item[
            "future_external_api_call_candidate"
        ],
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


def _policy_sample_is_control_only(item: Mapping[str, Any]) -> bool:
    references = (
        "policy_resolution_ref",
        "embedding_queue_request_ref",
        "cache_entry_ref",
        "retry_ref",
        "external_api_audit_ref",
        "provider_ref",
        "model_ref",
        "model_version",
        "dimension",
        "created_at",
    )
    return (
        item.get("sample_kind") == POLICY_SAMPLE_KIND
        and item.get("control_metadata_only") is True
        and item.get("source_content_retained") is False
        and item.get("sent_to_external_api") is False
        and item.get("actual_external_payload_created") is False
        and item.get("actual_embedding_queue_created") is False
        and item.get("actual_cache_entry_created") is False
        and item.get("actual_failed_retry_record_created") is False
        and item.get("actual_external_api_call_performed") is False
        and item.get("actual_model_token_consumption_performed") is False
        and all(
            isinstance(item.get(field), str) and ":control:stage072-p2:" in item[field]
            for field in references
        )
    )


def _audit_log_sample(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    projection = _audit_projection(item, index)
    return {
        "audit_log_sample_id": (
            "embedding-model-version-audit-log-sample:" f"{item['scenario_id']}"
        ),
        "record_kind": AUDIT_LOG_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item[
            "referenced_embedding_queue_request_ref"
        ],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "audit_projection": projection,
        "audit_field_count": len(projection),
        "audit_projection_required": True,
        "audit_projection_present": set(projection)
        == set(CONTROL_AUDIT_PROJECTION_FIELDS),
        "control_metadata_only": True,
        "actual_audit_record_created": False,
        "actual_audit_record_persisted": False,
    }


def _audit_projection(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    records = _p2_records_for(item, index)
    audit = records.get("audit", {})
    policy = records.get("policy", {})
    queue = records.get("queue", {})
    cache = records.get("cache", {})
    retry = records.get("retry", {})
    if not all(
        isinstance(record, Mapping) for record in (audit, policy, queue, cache, retry)
    ):
        return {}
    if (
        audit.get("external_api_audit_ref")
        != item.get("referenced_external_api_audit_ref")
        or audit.get("effective_external_api_policy")
        != item.get("effective_external_api_policy")
        or policy.get("policy_resolution_ref")
        != item.get("referenced_policy_resolution_ref")
        or queue.get("embedding_queue_request_ref")
        != item.get("referenced_embedding_queue_request_ref")
        or cache.get("cache_entry_ref") != item.get("referenced_cache_entry_ref")
        or retry.get("retry_ref") != item.get("referenced_retry_ref")
        or audit.get("embedding_queue_request_ref")
        != queue.get("embedding_queue_request_ref")
    ):
        return {}
    return dict(audit)


def _audit_log_sample_has_exact_projection(item: Mapping[str, Any]) -> bool:
    projection = item.get("audit_projection")
    return (
        isinstance(projection, Mapping)
        and set(projection) == set(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("audit_projection_required") is True
        and item.get("audit_projection_present") is True
        and item.get("control_metadata_only") is True
        and item.get("external_api_audit_ref")
        == projection.get("external_api_audit_ref")
        and projection.get("token_count") == 0
        and projection.get("cost_estimate") == 0
        and item.get("actual_audit_record_created") is False
        and item.get("actual_audit_record_persisted") is False
    )


def _cost_estimate_sample(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    records = _p2_records_for(item, index)
    cost = records.get("cost", {})
    model = records.get("model", {})
    return {
        "cost_estimate_sample_id": (
            "embedding-model-version-zero-cost-estimate:" f"{item['scenario_id']}"
        ),
        "record_kind": COST_ESTIMATE_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "control_budget_check_state": item["observed_budget_check_state"],
        "provider_ref": cost.get("provider_ref"),
        "model_ref": cost.get("model_ref"),
        "model_version": cost.get("model_version"),
        "dimension": model.get("dimension"),
        "created_at": model.get("created_at"),
        "sent_to_external_api": model.get("sent_to_external_api"),
        "estimated_token_count": cost.get("estimated_token_count"),
        "estimated_cost": cost.get("estimated_cost"),
        "cost_currency": cost.get("cost_currency"),
        "cost_estimation_reason": cost.get("cost_estimation_reason"),
        "control_metadata_only": True,
        "provider_price_lookup_performed": False,
        "actual_cost_recorded": False,
        "actual_model_token_consumption_performed": False,
    }


def _cost_estimate_sample_is_zero(item: Mapping[str, Any]) -> bool:
    return (
        item.get("record_kind") == COST_ESTIMATE_SAMPLE_KIND
        and item.get("estimated_token_count") == 0
        and item.get("estimated_cost") == 0
        and item.get("sent_to_external_api") is False
        and item.get("control_metadata_only") is True
        and item.get("provider_price_lookup_performed") is False
        and item.get("actual_cost_recorded") is False
        and item.get("actual_model_token_consumption_performed") is False
    )


def _failure_handling_result(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "failure_handling_id": (
            "embedding-model-version-failure-handling:" f"{item['scenario_id']}"
        ),
        "record_kind": FAILURE_HANDLING_KIND,
        "scenario_id": item["scenario_id"],
        "failure_state": _failure_state(item),
        "control_queue_state": item["observed_queue_state"],
        "control_cache_disposition": item["observed_cache_disposition"],
        "control_retry_state": item["observed_retry_state"],
        "control_budget_check_state": item["observed_budget_check_state"],
        "audit_disposition": item["observed_audit_disposition"],
        "human_handling_required": item["human_handling_required"],
        "explicit_disposition": item["explicit_disposition"],
        "failure_closed": True,
        "actual_failure_record_created": False,
        "actual_retry_execution_performed": False,
    }


def _failure_state(item: Mapping[str, Any]) -> str:
    if item.get("effective_external_api_policy") == "denied":
        return "CONTROL_POLICY_DENIED_BLOCKS_EXTERNALIZATION"
    if item.get("observed_budget_check_state") == "CONTROL_BUDGET_INSUFFICIENT":
        return "CONTROL_BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API"
    if item.get("scenario_category") == "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL":
        return "CONTROL_DOCUMENT_RESTRICTION_BLOCKS_FULL_TEXT_ESCALATION"
    if item.get("effective_external_api_policy") == "summary_only":
        return "CONTROL_SUMMARY_ONLY_REFERENCE_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW"
    return "CONTROL_FULL_TEXT_REFERENCE_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW"


def _non_externalized_data_record(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "non_externalized_record_id": (
            "embedding-model-version-non-externalized:" f"{item['scenario_id']}"
        ),
        "record_kind": NON_EXTERNALIZED_DATA_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "control_budget_check_state": item["observed_budget_check_state"],
        "non_externalization_reason": _non_externalization_reason(item),
        "externalization_performed": False,
        "external_payload_created": False,
        "source_content_retained": False,
        "actual_external_api_call_performed": False,
    }


def _non_externalization_reason(item: Mapping[str, Any]) -> str:
    if item.get("effective_external_api_policy") == "denied":
        return "CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD"
    if item.get("observed_budget_check_state") == "CONTROL_BUDGET_INSUFFICIENT":
        return "CONTROL_BUDGET_INSUFFICIENT_PAUSES_NO_EXTERNALIZATION"
    return "CONTROL_RUNTIME_DISABLED_AUDIT_AND_WHITEBOX_REVIEW_REQUIRED"


def _query_instructions(predecessors_valid: bool) -> dict[str, Any]:
    return {
        "instruction_kind": QUERY_INSTRUCTION_KIND,
        "query_contract_available": predecessors_valid,
        "query_scope": "IN_MEMORY_PHASE4_CONTROL_DELIVERY_REPORT_ONLY",
        "supported_query_keys": [
            "scenario_id",
            "effective_external_api_policy",
            "policy_resolution_ref",
            "embedding_queue_request_ref",
            "cache_entry_ref",
            "retry_ref",
            "external_api_audit_ref",
        ],
        "persistent_audit_log_available": False,
        "real_externalization_history_available": False,
        "actual_audit_log_query_performed": False,
        "actual_externalization_record_query_performed": False,
    }


def _rollback_instructions() -> dict[str, Any]:
    return {
        "instruction_kind": ROLLBACK_INSTRUCTION_KIND,
        "rollback_scope": "STAGE072_PHASE4_DELIVERY_EVIDENCE_AND_LOCAL_GOVERNANCE_ONLY",
        "rollback_target_result": P3_PASS_RESULT,
        "rollback_target_gate": ENTRY_GATE,
        "preserve_phase1_contract": True,
        "preserve_phase2_control_slice": True,
        "preserve_phase3_controlled_scenarios": True,
        "real_source_change_allowed": False,
        "persistent_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
        "actual_policy_rollback_performed": False,
    }


def _expected_scenario_ids(samples: Sequence[Mapping[str, Any]]) -> bool:
    return tuple(item.get("scenario_id") for item in samples) == EXPECTED_SCENARIO_IDS


def _json_line(sample: Mapping[str, Any]) -> str:
    return json.dumps(dict(sample), ensure_ascii=False, sort_keys=True)


def _human_confirmation_prompts() -> list[str]:
    return [
        "本页仅展示固定控制样例，不代表已读取、保留或外发任何业务资料。",
        "未来调用候选仍须业务线白箱复核、审计前置和运行时授权；当前没有真实调用。",
        "策略 denied、来源或文档收紧、预算不足或运行时未授权时均保持不外发，不会静默放行。",
        "回滚仅撤回本阶段交付工件，恢复到 P3 控制场景；不影响真实资料、审计日志、GitHub、OVH 或生产。",
    ]


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
