"""Stage074 P4 本地 Embedding 兜底的 metadata-only 交付证据。

本模块只重放已验证的 P3 五条固定、非业务、reference-only ``:control:`` 场景，
并重新执行 P2 的纯内存控制切片，派生策略样例、十八字段审计投影、零值成本、失败
处理、未外发原因、查询和回滚说明。所有结果仅存在于当前 Python 进程，不能替代
来源文档、成为业务事实、写入审计日志或发起外部调用。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage074.local_embedding_fallback.phase4.delivery.v1"
RECORD_KIND = "LOCAL_EMBEDDING_FALLBACK_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_LOCAL_EMBEDDING_FALLBACK_DELIVERY_EVIDENCE"
ENTRY_GATE = "IDS-STAGE074-P4-GATE"
NEXT_GATE = "IDS-STAGE074-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_LOCAL_EMBEDDING_FALLBACK_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_LOCAL_EMBEDDING_FALLBACK_CONTROL_SLICE"

POLICY_SAMPLE_KIND = "DELIVERY_METADATA_ONLY_LOCAL_EMBEDDING_FALLBACK_POLICY_SAMPLE_NOT_REAL_PAYLOAD"
AUDIT_LOG_SAMPLE_KIND = "CONTROL_LOCAL_EMBEDDING_FALLBACK_AUDIT_LOG_SAMPLE_NOT_PERSISTED"
COST_ESTIMATE_SAMPLE_KIND = "CONTROL_ZERO_COST_ESTIMATE_NOT_PROVIDER_PRICE"
FAILURE_HANDLING_KIND = "CONTROL_LOCAL_EMBEDDING_FALLBACK_FAILURE_HANDLING_NOT_REAL_FAILURE_RECORD"
NON_EXTERNALIZED_DATA_KIND = "CONTROL_NON_EXTERNALIZED_LOCAL_EMBEDDING_FALLBACK_REFERENCE_NOT_REAL_DATA"
QUERY_INSTRUCTION_KIND = "LOCAL_EMBEDDING_FALLBACK_EXTERNALIZATION_RECORD_QUERY_INSTRUCTIONS_IN_MEMORY_CONTROL_ONLY"
ROLLBACK_INSTRUCTION_KIND = "LOCAL_EMBEDDING_FALLBACK_POLICY_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"

EXPECTED_SCENARIO_IDS = ("S074-P3-001", "S074-P3-002", "S074-P3-003", "S074-P3-004", "S074-P3-005")
EXPECTED_SCENARIO_CATEGORIES = (
    "DENIED_EGRESS_BLOCK_CONTROL",
    "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL",
    "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL",
    "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL",
    "BUDGET_INSUFFICIENT_PAUSE_CONTROL",
)
P3_SCENARIO_FIELDS = (
    "scenario_id", "scenario_category", "phase2_control_scenario",
    "referenced_policy_resolution_ref", "referenced_embedding_queue_request_ref",
    "referenced_cache_entry_ref", "referenced_retry_ref", "referenced_external_api_audit_ref",
    "effective_external_api_policy", "external_payload_mode", "observed_control_payload_scope",
    "expected_control_payload_scope", "expected_queue_state", "observed_queue_state",
    "expected_cache_disposition", "observed_cache_disposition", "expected_retry_state",
    "observed_retry_state", "expected_budget_check_state", "observed_budget_check_state",
    "audit_projection_required", "audit_projection_present", "audit_field_count",
    "audit_required_fields_present", "audit_reference_fields_are_control_only",
    "expected_audit_disposition", "observed_audit_disposition", "future_external_api_call_candidate",
    "actual_external_api_call_performed", "actual_model_token_consumption_performed",
    "model_version_sent_to_external_api", "human_handling_required", "explicit_disposition",
    "silent_drop", "expectation_met",
)
CONTROL_AUDIT_PROJECTION_FIELDS = (
    "external_api_audit_ref", "data_source_ref", "document_ref", "chunk_id",
    "effective_external_api_policy", "external_payload_mode", "policy_inheritance_reason",
    "owner_authorization_ref", "authorized_at", "authorization_reason", "provider_ref",
    "model_ref", "model_version", "token_count", "cost_estimate",
    "embedding_queue_request_ref", "budget_check_state", "audit_disposition",
)
P2_RUNTIME_FALSE_FIELDS = (
    "actual_data_source_policy_read", "actual_document_policy_resolved",
    "actual_chunk_policy_assigned", "actual_policy_resolution_record_created",
    "actual_local_provider_selected", "actual_local_model_selected",
    "actual_local_embedding_execution_performed", "actual_local_embedding_or_index_written",
    "actual_embedding_queue_request_created", "actual_cache_entry_created",
    "actual_cache_read_or_write_performed", "actual_failed_retry_record_created",
    "actual_retry_execution_performed", "actual_cost_governor_record_created",
    "actual_cost_estimation_performed", "actual_budget_lookup_performed",
    "actual_model_version_record_created", "actual_external_api_audit_record_created",
    "ids_business_source_read_performed", "raw_metadata_content_accessed",
    "source_file_open_performed", "parser_execution_performed", "chunking_execution_performed",
    "summary_generation_performed", "external_payload_created", "embedding_queue_execution_performed",
    "cache_read_or_write_performed", "failed_retry_execution_performed",
    "cost_estimation_execution_performed", "budget_lookup_performed",
    "model_version_record_execution_performed", "provider_credential_read_performed",
    "provider_or_model_selected", "local_provider_or_model_selected",
    "local_embedding_execution_performed", "local_embedding_or_index_write_performed",
    "external_api_client_initialized", "external_api_call_performed",
    "audit_record_creation_performed", "audit_log_query_performed", "model_call_performed",
    "model_token_consumption_performed", "embedding_or_index_write_performed",
    "database_connection_performed", "persistent_state_write_performed",
    "agent_execution_performed", "ovh_deployment_performed",
    "production_runtime_activation_performed", "github_upload_performed", "push_performed",
)
P3_RUNTIME_FALSE_FIELDS = (
    *P2_RUNTIME_FALSE_FIELDS,
    "actual_control_scenario_record_persisted", "actual_external_payload_created",
    "control_payload_content_retained", "audit_test_execution_performed",
)
RUNTIME_CLOSED_FIELDS = (
    "authorized_fixture_access_performed", "actual_delivery_file_written",
    "actual_audit_log_query_performed", "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed", *P3_RUNTIME_FALSE_FIELDS,
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]
Phase2ReportProvider = Callable[[], Mapping[str, Any]]


def build_local_embedding_fallback_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
    phase2_report_provider: Phase2ReportProvider | None = None,
) -> dict[str, Any]:
    """派生 P4 纯内存交付证据；任一前序合同异常即失败关闭。"""

    phase3_report = _provider_result(
        phase3_report_provider or _default_phase3_report_provider
    )
    phase2_report = _provider_result(
        phase2_report_provider or _default_phase2_report_provider
    )
    phase3_valid = _phase3_report_is_valid(phase3_report)
    phase2_valid = _phase2_report_is_valid(phase2_report)
    predecessors_valid = phase3_valid and phase2_valid

    scenario_records = _mapping_sequence(phase3_report.get("scenario_results"))
    audit_records = _mapping_sequence(phase2_report.get("external_api_audit_projections"))
    cost_records = _mapping_sequence(phase2_report.get("cost_control_projections"))

    policy_samples = [
        _policy_sample(scenario) for scenario in scenario_records
    ] if predecessors_valid else []
    audit_samples = [
        _audit_log_sample(scenario, audit)
        for scenario, audit in zip(scenario_records, audit_records)
    ] if predecessors_valid else []
    cost_samples = [
        _cost_estimate_sample(scenario, cost)
        for scenario, cost in zip(scenario_records, cost_records)
    ] if predecessors_valid else []
    failure_results = [
        _failure_handling_result(scenario) for scenario in scenario_records
    ] if predecessors_valid else []
    non_externalized = [
        _non_externalized_data_record(scenario) for scenario in scenario_records
    ] if predecessors_valid else []
    query_instructions = _query_instructions(predecessors_valid)
    rollback_instructions = _rollback_instructions()
    runtime_closed_flags = _runtime_closed_flags()

    delivery_integrity = (
        predecessors_valid
        and len(policy_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(audit_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(cost_samples) == len(EXPECTED_SCENARIO_IDS)
        and len(failure_results) == len(EXPECTED_SCENARIO_IDS)
        and len(non_externalized) == len(EXPECTED_SCENARIO_IDS)
        and _expected_scenario_ids(policy_samples)
        and all(_policy_sample_is_control_only(item) for item in policy_samples)
        and all(_audit_log_sample_has_exact_projection(item) for item in audit_samples)
        and all(_cost_estimate_sample_is_zero(item) for item in cost_samples)
        and all(item["failure_closed"] for item in failure_results)
        and all(not item["externalization_performed"] for item in non_externalized)
        and len(query_instructions["supported_query_keys"]) == 7
        and all(value is False for value in runtime_closed_flags.values())
    )
    valid = bool(delivery_integrity)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": phase3_valid,
        "phase3_controlled_scenarios_report_valid": phase3_valid,
        "phase2_control_slice_reexecuted_in_memory_only": phase2_valid,
        "phase2_control_slice_report_valid": phase2_valid,
        "delivery_evidence_metadata_only": True,
        "policy_sample_count": len(policy_samples),
        "control_audit_log_sample_count": len(audit_samples),
        "control_audit_field_count": len(CONTROL_AUDIT_PROJECTION_FIELDS),
        "control_audit_field_check_count": sum(
            item["audit_field_count"] for item in audit_samples
        ),
        "zero_cost_estimate_sample_count": len(cost_samples),
        "failure_handling_result_count": len(failure_results),
        "non_externalized_data_record_count": len(non_externalized),
        "future_external_api_call_candidate_count": sum(
            item["future_external_api_call_candidate"] for item in policy_samples
        ),
        "policy_denied_sample_count": sum(
            item["effective_external_api_policy"] == "denied"
            for item in policy_samples
        ),
        "budget_pause_sample_count": sum(
            item["observed_budget_check_state"] == "CONTROL_BUDGET_INSUFFICIENT"
            for item in policy_samples
        ),
        "human_handling_required_count": sum(
            item["human_handling_required"] for item in policy_samples
        ),
        "local_embedding_fallback_policy_samples": policy_samples,
        "control_audit_log_samples": audit_samples,
        "cost_estimate_samples": cost_samples,
        "failure_handling_results": failure_results,
        "non_externalized_data_records": non_externalized,
        "externalization_record_query_instructions": query_instructions,
        "policy_rollback_instructions": rollback_instructions,
        "human_confirmation_prompts_zh": _human_confirmation_prompts(),
        "chinese_feedback": _chinese_feedback(),
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "external_model_output_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "actual_business_decision_created": False,
        "stage073_review_evidence_read": True,
        "stage074_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": valid,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage074_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "actual_embedding_queue_count": 0,
        "actual_cache_entry_count": 0,
        "actual_failed_retry_count": 0,
        "actual_cost_count": 0,
        "actual_model_version_record_count": 0,
        "actual_external_api_audit_record_count": 0,
        "actual_external_api_call_count": 0,
        "actual_model_token_count": 0,
    }
    report.update(runtime_closed_flags)
    return report


def _default_phase3_report_provider() -> Mapping[str, Any]:
    module = _load_module("stage074_local_embedding_fallback_scenarios.py")
    return module.build_local_embedding_fallback_phase3_report()


def _default_phase2_report_provider() -> Mapping[str, Any]:
    module = _load_module("stage074_local_embedding_fallback_slice.py")
    return module.execute_local_embedding_fallback_control_slice(module.build_control_input())


def _load_module(filename: str) -> Any:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        result = provider()
    except Exception:
        return {}
    return result if isinstance(result, Mapping) else {}


def _phase3_report_is_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _mapping_sequence(report.get("scenario_results"))
    ref_fields = (
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
        and report.get("control_audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and report.get("control_audit_field_check_count") == 90
        and report.get("future_external_api_call_candidate_count") == 3
        and report.get("human_handling_required_count") == 4
        and report.get("actual_external_api_call_count") == 0
        and report.get("actual_model_token_count") == 0
        and report.get("source_document_remains_authoritative") is True
        and report.get("control_scenario_can_replace_source_document") is False
        and report.get("audit_projection_can_become_business_fact_authority") is False
        and report.get("automatic_business_recommendation_allowed") is False
        and report.get("stage073_review_evidence_read") is True
        and report.get("stage074_started") is True
        and report.get("phase1_started") is True
        and report.get("phase2_started") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("batch_review_performed") is False
        and report.get("stage075_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
        and tuple(item.get("scenario_id") for item in scenarios) == EXPECTED_SCENARIO_IDS
        and tuple(item.get("scenario_category") for item in scenarios) == EXPECTED_SCENARIO_CATEGORIES
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
                isinstance(item.get(field), str) and ":control:stage074-p2:" in item[field]
                for field in ref_fields
            )
            for item in scenarios
        )
        and all(report.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS)
    )


def _phase2_report_is_valid(report: Mapping[str, Any]) -> bool:
    audits = _mapping_sequence(report.get("external_api_audit_projections"))
    costs = _mapping_sequence(report.get("cost_control_projections"))
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_request_count") == len(EXPECTED_SCENARIO_IDS)
        and len(audits) == len(EXPECTED_SCENARIO_IDS)
        and len(costs) == len(EXPECTED_SCENARIO_IDS)
        and all(set(item) == set(CONTROL_AUDIT_PROJECTION_FIELDS) for item in audits)
        and all(
            item.get("estimated_token_count") == 0
            and item.get("estimated_cost") == 0
            for item in costs
        )
        and report.get("actual_input_request_count") == 0
        and all(report.get(field) is False for field in P2_RUNTIME_FALSE_FIELDS)
    )


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _policy_sample(scenario: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "sample_kind": POLICY_SAMPLE_KIND,
        "control_metadata_only": True,
        "source_content_retained": False,
        "sent_to_external_api": False,
        "actual_external_payload_created": False,
        "actual_embedding_queue_created": False,
        "actual_cache_entry_created": False,
        "actual_failed_retry_record_created": False,
        "actual_external_api_call_performed": False,
        "actual_model_token_consumption_performed": False,
        "policy_resolution_ref": scenario["referenced_policy_resolution_ref"],
        "embedding_queue_request_ref": scenario["referenced_embedding_queue_request_ref"],
        "cache_entry_ref": scenario["referenced_cache_entry_ref"],
        "retry_ref": scenario["referenced_retry_ref"],
        "external_api_audit_ref": scenario["referenced_external_api_audit_ref"],
        "effective_external_api_policy": scenario["effective_external_api_policy"],
        "external_payload_mode": scenario["external_payload_mode"],
        "observed_control_payload_scope": scenario["observed_control_payload_scope"],
        "observed_queue_state": scenario["observed_queue_state"],
        "observed_cache_disposition": scenario["observed_cache_disposition"],
        "observed_retry_state": scenario["observed_retry_state"],
        "observed_budget_check_state": scenario["observed_budget_check_state"],
        "future_external_api_call_candidate": scenario["future_external_api_call_candidate"],
        "human_handling_required": scenario["human_handling_required"],
        "whitebox_review_required_before_future_call": scenario[
            "human_handling_required"
        ],
    }


def _policy_sample_is_control_only(item: Mapping[str, Any]) -> bool:
    refs = (
        "policy_resolution_ref",
        "embedding_queue_request_ref",
        "cache_entry_ref",
        "retry_ref",
        "external_api_audit_ref",
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
            isinstance(item.get(field), str)
            and ":control:stage074-p2:" in item[field]
            for field in refs
        )
    )


def _audit_log_sample(
    scenario: Mapping[str, Any], audit: Mapping[str, Any]
) -> dict[str, Any]:
    projection = {field: audit[field] for field in CONTROL_AUDIT_PROJECTION_FIELDS}
    return {
        "record_kind": AUDIT_LOG_SAMPLE_KIND,
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "audit_projection": projection,
        "audit_field_count": len(projection),
        "audit_projection_required": True,
        "audit_projection_present": True,
        "audit_reference_fields_are_control_only": all(
            isinstance(projection.get(field), str)
            and ":control:stage074-p2:" in projection[field]
            for field in (
                "external_api_audit_ref",
                "data_source_ref",
                "document_ref",
                "chunk_id",
                "provider_ref",
                "model_ref",
                "model_version",
                "embedding_queue_request_ref",
            )
        ),
        "actual_audit_record_created": False,
        "actual_audit_record_persisted": False,
        "actual_external_api_call_performed": False,
        "actual_model_token_consumption_performed": False,
    }


def _audit_log_sample_has_exact_projection(item: Mapping[str, Any]) -> bool:
    projection = item.get("audit_projection")
    return (
        item.get("record_kind") == AUDIT_LOG_SAMPLE_KIND
        and isinstance(projection, Mapping)
        and set(projection) == set(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("audit_field_count") == len(CONTROL_AUDIT_PROJECTION_FIELDS)
        and item.get("audit_projection_required") is True
        and item.get("audit_projection_present") is True
        and item.get("audit_reference_fields_are_control_only") is True
        and projection.get("token_count") == 0
        and projection.get("cost_estimate") == 0
        and item.get("actual_audit_record_created") is False
        and item.get("actual_audit_record_persisted") is False
    )


def _cost_estimate_sample(
    scenario: Mapping[str, Any], cost: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "sample_kind": COST_ESTIMATE_SAMPLE_KIND,
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "provider_ref": cost.get("provider_ref"),
        "model_ref": cost.get("model_ref"),
        "model_version": cost.get("model_version"),
        "estimated_token_count": cost.get("estimated_token_count"),
        "estimated_cost": cost.get("estimated_cost"),
        "budget_check_state": cost.get("budget_check_state"),
        "cost_currency": cost.get("cost_currency"),
        "cost_estimation_reason": cost.get("cost_estimation_reason"),
        "sent_to_external_api": False,
        "control_metadata_only": True,
        "provider_price_lookup_performed": False,
        "actual_cost_recorded": False,
        "actual_model_token_consumption_performed": False,
    }


def _cost_estimate_sample_is_zero(item: Mapping[str, Any]) -> bool:
    return (
        item.get("sample_kind") == COST_ESTIMATE_SAMPLE_KIND
        and item.get("estimated_token_count") == 0
        and item.get("estimated_cost") == 0
        and item.get("sent_to_external_api") is False
        and item.get("control_metadata_only") is True
        and item.get("provider_price_lookup_performed") is False
        and item.get("actual_cost_recorded") is False
        and item.get("actual_model_token_consumption_performed") is False
    )


def _failure_handling_result(scenario: Mapping[str, Any]) -> dict[str, Any]:
    category = str(scenario["scenario_category"])
    state_by_category = {
        "DENIED_EGRESS_BLOCK_CONTROL": "CONTROL_POLICY_DENIED_BLOCKS_EXTERNALIZATION",
        "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL": "CONTROL_SUMMARY_ONLY_PRESERVES_REFERENCE_BOUNDARY",
        "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL": "CONTROL_DOCUMENT_RESTRICTION_BLOCKS_FULL_TEXT_ESCALATION",
        "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL": "CONTROL_FULL_TEXT_REFERENCE_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW",
        "BUDGET_INSUFFICIENT_PAUSE_CONTROL": "CONTROL_BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API",
    }
    return {
        "record_kind": FAILURE_HANDLING_KIND,
        "scenario_id": scenario["scenario_id"],
        "scenario_category": category,
        "failure_state": state_by_category[category],
        "failure_closed": True,
        "actual_failure_record_created": False,
        "actual_retry_execution_performed": False,
        "actual_external_api_call_performed": False,
    }


def _non_externalized_data_record(scenario: Mapping[str, Any]) -> dict[str, Any]:
    category = str(scenario["scenario_category"])
    reason_by_category = {
        "DENIED_EGRESS_BLOCK_CONTROL": "CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD",
        "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL": "CONTROL_SUMMARY_REFERENCE_REMAINS_WHITEBOX_REVIEW_PENDING",
        "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL": "CONTROL_DOCUMENT_RESTRICTION_PREVENTS_FULL_TEXT_EXTERNALIZATION",
        "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL": "CONTROL_FULL_TEXT_REFERENCE_REMAINS_AUDIT_AND_WHITEBOX_REVIEW_PENDING",
        "BUDGET_INSUFFICIENT_PAUSE_CONTROL": "CONTROL_BUDGET_INSUFFICIENT_PAUSES_EXTERNALIZATION",
    }
    return {
        "record_kind": NON_EXTERNALIZED_DATA_KIND,
        "scenario_id": scenario["scenario_id"],
        "scenario_category": category,
        "non_externalization_reason": reason_by_category[category],
        "control_budget_check_state": scenario["observed_budget_check_state"],
        "externalization_performed": False,
        "external_payload_created": False,
        "source_content_retained": False,
        "actual_external_api_call_performed": False,
        "actual_model_token_consumption_performed": False,
    }


def _query_instructions(predecessors_valid: bool) -> dict[str, Any]:
    return {
        "record_kind": QUERY_INSTRUCTION_KIND,
        "query_contract_available": predecessors_valid,
        "supported_query_keys": (
            "scenario_id",
            "scenario_category",
            "effective_external_api_policy",
            "observed_queue_state",
            "observed_budget_check_state",
            "policy_resolution_ref",
            "external_api_audit_ref",
        ),
        "persistent_audit_log_available": False,
        "real_externalization_history_available": False,
        "actual_audit_log_query_performed": False,
        "actual_externalization_record_query_performed": False,
        "query_scope": "CURRENT_PYTHON_PROCESS_CONTROL_DELIVERY_REPORT_ONLY",
    }


def _rollback_instructions() -> dict[str, Any]:
    return {
        "record_kind": ROLLBACK_INSTRUCTION_KIND,
        "rollback_target_result": P3_PASS_RESULT,
        "rollback_target_gate": ENTRY_GATE,
        "real_source_change_allowed": False,
        "persistent_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
        "actual_policy_rollback_performed": False,
    }


def _expected_scenario_ids(samples: Sequence[Mapping[str, Any]]) -> bool:
    return tuple(item.get("scenario_id") for item in samples) == EXPECTED_SCENARIO_IDS


def _human_confirmation_prompts() -> list[str]:
    return [
        "确认 denied 控制样例仅记录阻断原因，不包含任何外发载荷。",
        "确认 summary_only 与 document 收紧样例只保留摘要引用类别，不能升级为文本块。",
        "确认 full_text_allowed 仍须完整审计前置和业务线白箱人工复核，不能自动外发。",
        "确认预算不足样例保持暂停，并可只回退本 P4 控制交付证据到 P3。",
    ]


def _chinese_feedback() -> list[str]:
    return [
        "本次只派生五条固定控制样例，未读取、保留或外发真实来源正文、摘要或文本块。",
        "默认 denied 阻断外发；summary_only 只保留摘要引用，document 收紧不得升级为全文。",
        "full_text_allowed 仅是未来文本块引用候选，须先满足审计前置和业务线白箱人工复核。",
        "预算不足时外部 API 候选保持暂停；本步骤可回退到 Stage074 P3，不影响来源资料、OVH 或生产状态。",
    ]


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
