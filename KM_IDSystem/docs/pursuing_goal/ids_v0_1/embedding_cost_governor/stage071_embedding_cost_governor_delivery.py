"""Stage071 P4 Embedding 成本治理器的 metadata-only 交付证据。

模块只从已验证的 P3 七条固定、非业务、reference-only ``:control:`` 场景和
P2 纯内存控制切片派生策略样例、18 字段审计投影样例、零成本估算、失败处理、
未外发原因、查询与回滚说明。所有结果仅存于当前 Python 进程，不能替代来源
文档、形成业务事实或发起外部调用。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage071.embedding_cost_governor.phase4.delivery.v1"
RECORD_KIND = "EMBEDDING_COST_GOVERNOR_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_PHASE4_EMBEDDING_COST_GOVERNOR_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EMBEDDING_COST_GOVERNOR_DELIVERY_EVIDENCE"
ENTRY_GATE = "IDS-STAGE071-P4-GATE"
NEXT_GATE = "IDS-STAGE071-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_EMBEDDING_COST_GOVERNOR_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE"

POLICY_SAMPLE_KIND = "DELIVERY_METADATA_ONLY_EMBEDDING_COST_GOVERNOR_POLICY_SAMPLE_NOT_REAL_PAYLOAD"
AUDIT_LOG_SAMPLE_KIND = "CONTROL_EMBEDDING_COST_GOVERNOR_AUDIT_LOG_SAMPLE_NOT_PERSISTED"
COST_ESTIMATE_SAMPLE_KIND = "CONTROL_ZERO_COST_ESTIMATE_NOT_PROVIDER_PRICE"
FAILURE_HANDLING_KIND = "CONTROL_COST_GOVERNOR_FAILURE_HANDLING_NOT_REAL_FAILURE_RECORD"
NON_EXTERNALIZED_DATA_KIND = "CONTROL_NON_EXTERNALIZED_COST_GOVERNOR_REFERENCE_NOT_REAL_DATA"
QUERY_INSTRUCTION_KIND = "EMBEDDING_COST_GOVERNOR_EXTERNALIZATION_RECORD_QUERY_INSTRUCTIONS_IN_MEMORY_CONTROL_ONLY"
ROLLBACK_INSTRUCTION_KIND = "EMBEDDING_COST_GOVERNOR_POLICY_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"

EXPECTED_SCENARIO_IDS = (
    "denied-policy-blocks-cost-governor-queue-cache-retry-and-externalization-control",
    "summary-only-policy-limits-control-payload-after-all-budget-gates-pass",
    "document-restriction-limits-full-text-to-summary-control-after-all-budget-gates-pass",
    "full-text-policy-keeps-only-control-text-reference-after-all-budget-gates-pass",
    "current-batch-budget-insufficient-pauses-full-text-control",
    "monthly-budget-insufficient-pauses-full-text-control",
    "single-task-cap-exceeded-pauses-full-text-control",
)
EXPECTED_SCENARIO_CATEGORIES = (
    "DENIED_NO_EXTERNALIZATION_CONTROL",
    "SUMMARY_ONLY_PAYLOAD_BOUNDARY_CONTROL",
    "DOCUMENT_RESTRICTION_PAYLOAD_BOUNDARY_CONTROL",
    "FULL_TEXT_PAYLOAD_BOUNDARY_CONTROL",
    "CURRENT_BATCH_BUDGET_PAUSE_CONTROL",
    "MONTHLY_BUDGET_PAUSE_CONTROL",
    "SINGLE_TASK_CAP_PAUSE_CONTROL",
)
P3_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "referenced_cost_governor_request_ref",
    "referenced_policy_resolution_ref",
    "referenced_embedding_queue_request_ref",
    "referenced_cache_entry_ref",
    "referenced_retry_ref",
    "referenced_external_api_audit_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "observed_control_payload_scope",
    "expected_control_payload_scope",
    "expected_cost_governor_state",
    "observed_cost_governor_state",
    "expected_budget_failure_scope",
    "observed_budget_failure_scope",
    "expected_queue_state",
    "observed_queue_state",
    "expected_cache_disposition",
    "observed_cache_disposition",
    "expected_retry_state",
    "observed_retry_state",
    "audit_projection_required",
    "audit_projection_present",
    "audit_field_count",
    "expected_audit_disposition",
    "observed_audit_disposition",
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
    "control_cost_governor_state",
    "control_cost_governor_reason",
)
P3_RUNTIME_FALSE_FIELDS = (
    "authorized_fixture_access_performed",
    "actual_external_payload_created",
    "control_payload_content_retained",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_batch_budget_lookup_performed",
    "actual_monthly_budget_lookup_performed",
    "actual_task_cap_evaluation_performed",
    "actual_model_version_recorded",
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
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_batch_budget_lookup_performed",
    "actual_monthly_budget_lookup_performed",
    "actual_task_cap_evaluation_performed",
    "actual_model_version_recorded",
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
    *P3_RUNTIME_FALSE_FIELDS,
    "actual_delivery_file_written",
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]
Phase2ReportProvider = Callable[[], Mapping[str, Any]]


def build_embedding_cost_governor_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
    phase2_report_provider: Phase2ReportProvider | None = None,
) -> dict[str, Any]:
    """派生 P4 纯内存交付证据；任一前序合同异常即失败关闭。"""

    phase3_provider = phase3_report_provider or _load_phase3_report_provider()
    phase3_report = _provider_result(phase3_provider)
    predecessor_valid = _phase3_report_is_valid(phase3_report)
    phase2_provider = phase2_report_provider or _load_phase2_report_provider()
    phase2_report = _provider_result(phase2_provider) if predecessor_valid else {}
    phase2_valid = _phase2_report_is_valid(phase2_report)
    scenario_results = _scenario_results(phase3_report) if predecessor_valid else []
    phase2_index = _phase2_index(phase2_report) if phase2_valid else {}

    policy_samples = [_policy_sample(item) for item in scenario_results]
    audit_log_samples = [
        _audit_log_sample(item, phase2_index) for item in scenario_results
    ]
    cost_estimate_samples = [
        _cost_estimate_sample(item, phase2_index) for item in scenario_results
    ]
    failure_handling_results = [_failure_handling_result(item) for item in scenario_results]
    non_externalized_data_records = [
        _non_externalized_data_record(item) for item in scenario_results
    ]
    query_instructions = _query_instructions(predecessor_valid and phase2_valid)
    rollback_instructions = _rollback_instructions()

    valid = (
        predecessor_valid
        and phase2_valid
        and _expected_scenario_ids(policy_samples)
        and len(audit_log_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(cost_estimate_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(failure_handling_results) == len(EXPECTED_SCENARIO_IDS)
        and len(non_externalized_data_records) == len(EXPECTED_SCENARIO_IDS)
        and all(_audit_log_sample_has_exact_projection(item) for item in audit_log_samples)
        and all(_cost_estimate_sample_is_zero(item) for item in cost_estimate_samples)
        and all(
            item["externalization_performed"] is False
            for item in non_externalized_data_records
        )
        and all(item["actual_failure_record_created"] is False for item in failure_handling_results)
        and query_instructions["query_contract_available"]
        and rollback_instructions["rollback_target_result"] == P3_PASS_RESULT
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "entry_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": predecessor_valid,
        "phase3_controlled_scenarios_report_valid": predecessor_valid,
        "phase2_control_slice_reexecuted_in_memory_only": phase2_valid,
        "embedding_cost_governor_policy_samples": policy_samples,
        "embedding_cost_governor_policy_sample_lines": tuple(
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
        "control_audit_field_check_count": sum(
            item["audit_field_count"] for item in audit_log_samples
        ),
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
        "three_budget_scope_pause_sample_count": sum(
            item["budget_failure_scope"] is not None for item in policy_samples
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
        "actual_delivery_file_written": False,
        **_runtime_closed_flags(),
        "stage071_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage072_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "chinese_feedback": [
            "已从七条固定成本治理控制场景派生策略样例、审计投影样例、零成本估算和失败处理；它们不是实际外发、审计日志、成本记录或业务资料。",
            "七条控制引用均未外发：denied 被策略阻断，摘要或文本块引用仍需业务线白箱复核且运行时关闭，三类预算不足项保持成本治理、队列、缓存和重试暂停；没有形成真实载荷。",
            "外发记录查询只说明在本报告内按场景、策略、成本治理、队列、缓存、重试与审计控制引用核对投影；当前没有持久审计日志、真实外发记录或生产历史可查。",
            "如需撤回本 phase，只撤回 P4 交付工件并回到 P3 控制场景，不改动真实资料、审计日志、成本、队列、缓存、数据库、OVH 或部署。",
        ],
    }


def _load_phase3_report_provider() -> Phase3ReportProvider:
    module_path = Path(__file__).with_name("stage071_embedding_cost_governor_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage071_p3", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage071 P3 controlled-scenarios module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, "build_embedding_cost_governor_phase3_report", None)
    if not callable(provider):
        raise RuntimeError("Stage071 P3 report provider is unavailable")
    return provider


def _load_phase2_report_provider() -> Phase2ReportProvider:
    module_path = Path(__file__).with_name("stage071_embedding_cost_governor_slice.py")
    spec = importlib.util.spec_from_file_location("stage071_p2", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage071 P2 control-slice module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_input = getattr(module, "build_control_input", None)
    execute = getattr(module, "execute_embedding_cost_governor_control_slice", None)
    if not callable(build_input) or not callable(execute):
        raise RuntimeError("Stage071 P2 control-slice provider is unavailable")
    return lambda: execute(build_input())


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        value = provider()
    except (OSError, RuntimeError, TypeError, ValueError):
        return {}
    return value if isinstance(value, Mapping) else {}


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
        and report.get("human_handling_required_count") == 6
        and report.get("control_policy_resolution_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_cost_governor_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_embedding_queue_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_cache_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_failed_retry_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_external_api_audit_projection_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("control_audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and report.get("control_audit_field_check_count")
        == len(EXPECTED_SCENARIO_IDS) * len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and report.get("audit_projection_required_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("audit_projection_present_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("future_external_api_call_candidate_count") == 3
        and report.get("three_budget_scope_paused_count") == 3
        and report.get("actual_input_request_count") == 0
        and report.get("actual_external_api_call_count") == 0
        and report.get("actual_model_token_count") == 0
        and report.get("actual_external_api_audit_record_count") == 0
        and report.get("source_document_remains_authoritative") is True
        and report.get("embedding_cost_governor_scenario_can_replace_source_document")
        is False
        and report.get("embedding_cost_governor_scenario_can_become_business_fact_authority")
        is False
        and tuple(item.get("scenario_id") for item in scenarios) == EXPECTED_SCENARIO_IDS
        and tuple(item.get("scenario_category") for item in scenarios)
        == EXPECTED_SCENARIO_CATEGORIES
        and all(_scenario_is_control_only(item) for item in scenarios)
        and all(report.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS)
    )


def _phase2_report_is_valid(report: Mapping[str, Any]) -> bool:
    records = _mapping_sequence(report.get("external_api_audit_projections"))
    governor_records = _mapping_sequence(report.get("cost_governor_records"))
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_request_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("policy_resolution_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("cost_governor_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("embedding_queue_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("cache_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("failed_retry_record_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("external_api_audit_projection_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("all_control_records_keep_required_shapes") is True
        and report.get("all_three_budget_scope_failure_closures_covered") is True
        and all(set(item) == set(CONTROL_AUDIT_PROJECTION_FIELDS) for item in records)
        and all(set(item) == set(COST_GOVERNOR_FIELDS) for item in governor_records)
        and all(report.get(field) is False for field in P2_RUNTIME_FALSE_FIELDS)
    )


def _scenario_results(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _mapping_sequence(report.get("scenario_results"))


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _scenario_is_control_only(item: Mapping[str, Any]) -> bool:
    references = (
        "referenced_cost_governor_request_ref",
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
        and item.get("audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("actual_external_api_call_performed") is False
        and item.get("actual_model_token_consumption_performed") is False
        and all(
            isinstance(item.get(field), str) and ":control:stage071-p2:" in item[field]
            for field in references
        )
    )


def _phase2_index(report: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    return {
        "audit": _index_by(
            _mapping_sequence(report.get("external_api_audit_projections")),
            "external_api_audit_ref",
        ),
        "governor": _index_by(
            _mapping_sequence(report.get("cost_governor_records")),
            "cost_governor_request_ref",
        ),
        "policy": _index_by(
            _mapping_sequence(report.get("policy_resolutions")),
            "policy_resolution_ref",
        ),
        "queue": _index_by(
            _mapping_sequence(report.get("embedding_queue_records")),
            "embedding_queue_request_ref",
        ),
        "cache": _index_by(
            _mapping_sequence(report.get("cache_records")),
            "cache_entry_ref",
        ),
        "retry": _index_by(
            _mapping_sequence(report.get("failed_retry_records")),
            "retry_ref",
        ),
    }


def _index_by(
    records: Sequence[Mapping[str, Any]], key: str
) -> dict[str, Mapping[str, Any]]:
    return {
        value: item
        for item in records
        if isinstance((value := item.get(key)), str)
    }


def _policy_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": f"embedding-cost-governor-policy-delivery-sample:{item['scenario_id']}",
        "sample_kind": POLICY_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "scenario_category": item["scenario_category"],
        "cost_governor_request_ref": item["referenced_cost_governor_request_ref"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "external_payload_mode": item["external_payload_mode"],
        "control_payload_scope": item["observed_control_payload_scope"],
        "control_cost_governor_state": item["observed_cost_governor_state"],
        "budget_failure_scope": item["observed_budget_failure_scope"],
        "control_queue_state": item["observed_queue_state"],
        "control_cache_disposition": item["observed_cache_disposition"],
        "control_retry_state": item["observed_retry_state"],
        "audit_disposition": item["observed_audit_disposition"],
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


def _audit_log_sample(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    projection = _audit_projection(item, index)
    return {
        "audit_log_sample_id": f"embedding-cost-governor-audit-log-sample:{item['scenario_id']}",
        "record_kind": AUDIT_LOG_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "cost_governor_request_ref": item["referenced_cost_governor_request_ref"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": item["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": item["referenced_cache_entry_ref"],
        "retry_ref": item["referenced_retry_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "audit_projection": projection,
        "audit_field_count": len(projection),
        "audit_projection_required": True,
        "audit_projection_present": set(projection) == set(CONTROL_AUDIT_PROJECTION_FIELDS),
        "control_metadata_only": True,
        "actual_audit_record_created": False,
        "actual_audit_record_persisted": False,
    }


def _audit_projection(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    audit = index.get("audit", {}).get(item.get("referenced_external_api_audit_ref"))
    governor = index.get("governor", {}).get(item.get("referenced_cost_governor_request_ref"))
    policy = index.get("policy", {}).get(item.get("referenced_policy_resolution_ref"))
    queue = index.get("queue", {}).get(item.get("referenced_embedding_queue_request_ref"))
    cache = index.get("cache", {}).get(item.get("referenced_cache_entry_ref"))
    retry = index.get("retry", {}).get(item.get("referenced_retry_ref"))
    if not all(isinstance(value, Mapping) for value in (audit, governor, policy, queue, cache, retry)):
        return {}
    if (
        audit.get("external_api_audit_ref") != item.get("referenced_external_api_audit_ref")
        or audit.get("embedding_queue_request_ref") != item.get("referenced_embedding_queue_request_ref")
        or governor.get("external_api_audit_ref") != audit.get("external_api_audit_ref")
        or governor.get("embedding_queue_request_ref") != queue.get("embedding_queue_request_ref")
        or queue.get("policy_resolution_ref") != policy.get("policy_resolution_ref")
        or cache.get("embedding_queue_request_ref") != queue.get("embedding_queue_request_ref")
        or retry.get("embedding_queue_request_ref") != queue.get("embedding_queue_request_ref")
        or retry.get("external_api_audit_ref") != audit.get("external_api_audit_ref")
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
        and item.get("external_api_audit_ref") == projection.get("external_api_audit_ref")
        and item.get("embedding_queue_request_ref")
        == projection.get("embedding_queue_request_ref")
        and projection.get("token_count") == 0
        and projection.get("cost_estimate") == 0
    )


def _cost_estimate_sample(
    item: Mapping[str, Any], index: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    governor = index.get("governor", {}).get(item.get("referenced_cost_governor_request_ref"))
    governor = governor if isinstance(governor, Mapping) else {}
    return {
        "cost_estimate_sample_id": f"embedding-cost-governor-zero-cost-estimate:{item['scenario_id']}",
        "record_kind": COST_ESTIMATE_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "cost_governor_request_ref": item["referenced_cost_governor_request_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "control_cost_governor_state": item["observed_cost_governor_state"],
        "budget_failure_scope": item["observed_budget_failure_scope"],
        "provider_ref": governor.get("provider_ref"),
        "model_ref": governor.get("model_ref"),
        "model_version": governor.get("model_version"),
        "estimated_token_count": governor.get("estimated_token_count"),
        "estimated_cost": governor.get("estimated_cost"),
        "cost_currency": governor.get("cost_currency"),
        "batch_budget_check_state": governor.get("batch_budget_check_state"),
        "monthly_budget_check_state": governor.get("monthly_budget_check_state"),
        "task_budget_cap_check_state": governor.get("task_budget_cap_check_state"),
        "control_metadata_only": True,
        "provider_price_lookup_performed": False,
        "actual_cost_recorded": False,
        "actual_model_token_consumption_performed": False,
    }


def _cost_estimate_sample_is_zero(item: Mapping[str, Any]) -> bool:
    return (
        item.get("estimated_token_count") == 0
        and item.get("estimated_cost") == 0
        and item.get("provider_price_lookup_performed") is False
        and item.get("actual_cost_recorded") is False
        and item.get("actual_model_token_consumption_performed") is False
    )


def _failure_handling_result(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "failure_handling_id": f"embedding-cost-governor-failure-handling:{item['scenario_id']}",
        "record_kind": FAILURE_HANDLING_KIND,
        "scenario_id": item["scenario_id"],
        "failure_state": _failure_state(item),
        "control_cost_governor_state": item["observed_cost_governor_state"],
        "control_queue_state": item["observed_queue_state"],
        "control_cache_disposition": item["observed_cache_disposition"],
        "control_retry_state": item["observed_retry_state"],
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
    scope = item.get("observed_budget_failure_scope")
    if scope == "current_batch":
        return "CONTROL_CURRENT_BATCH_BUDGET_PAUSE"
    if scope == "calendar_month":
        return "CONTROL_MONTHLY_BUDGET_PAUSE"
    if scope == "single_task":
        return "CONTROL_SINGLE_TASK_CAP_PAUSE"
    return "CONTROL_FUTURE_CALL_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW"


def _non_externalized_data_record(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "non_externalized_record_id": f"embedding-cost-governor-non-externalized:{item['scenario_id']}",
        "record_kind": NON_EXTERNALIZED_DATA_KIND,
        "scenario_id": item["scenario_id"],
        "policy_resolution_ref": item["referenced_policy_resolution_ref"],
        "cost_governor_request_ref": item["referenced_cost_governor_request_ref"],
        "external_api_audit_ref": item["referenced_external_api_audit_ref"],
        "effective_external_api_policy": item["effective_external_api_policy"],
        "budget_failure_scope": item["observed_budget_failure_scope"],
        "non_externalization_reason": _non_externalization_reason(item),
        "externalization_performed": False,
        "external_payload_created": False,
        "source_content_retained": False,
        "actual_external_api_call_performed": False,
    }


def _non_externalization_reason(item: Mapping[str, Any]) -> str:
    if item.get("effective_external_api_policy") == "denied":
        return "CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD"
    if item.get("observed_budget_failure_scope") is not None:
        return "CONTROL_THREE_BUDGET_GATES_PAUSED_NO_EXTERNALIZATION"
    return "CONTROL_FUTURE_CANDIDATE_RUNTIME_DISABLED_WHITEBOX_REVIEW_REQUIRED"


def _query_instructions(predecessor_valid: bool) -> dict[str, Any]:
    return {
        "instruction_kind": QUERY_INSTRUCTION_KIND,
        "query_contract_available": predecessor_valid,
        "query_scope": "IN_MEMORY_PHASE4_CONTROL_DELIVERY_REPORT_ONLY",
        "supported_query_keys": [
            "scenario_id",
            "effective_external_api_policy",
            "cost_governor_request_ref",
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
        "rollback_scope": "STAGE071_PHASE4_DELIVERY_EVIDENCE_AND_LOCAL_GOVERNANCE_ONLY",
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
        "本页仅展示固定控制样例，不代表已读取或外发任何业务资料。",
        "允许未来调用的控制引用仍须业务线白箱复核、审计前置和运行时授权；当前没有真实调用。",
        "任一预算关闭都会暂停成本治理、队列、缓存和重试，不会静默放行或丢弃。",
        "回滚仅撤回本阶段交付工件，恢复到 P3 控制场景；不影响真实资料、审计日志、GitHub、OVH 或生产。",
    ]


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
