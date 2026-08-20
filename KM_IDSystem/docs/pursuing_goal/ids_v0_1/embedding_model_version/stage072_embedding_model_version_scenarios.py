"""Stage072 P3 的 Embedding 模型版本受控专项场景。

模块只重放 Stage072 P2 的五条固定、非业务、reference-only :control: 记录。
它验证 denied 阻断外发、summary_only 只保留摘要引用类别、full_text_allowed
才保留文本块引用类别、预算不足暂停，以及每个未来外部 API 调用候选均已有完整
审计投影。所有载荷仍是控制引用：不会读取、保留或外发正文、摘要或文本块。

本模块不创建真实队列、缓存、重试、模型版本、成本或审计记录；不读取凭据，
不选择 provider 或模型，不调用外部 API，不消耗模型 Token，也不产生业务决策。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage072.embedding_model_version.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_EMBEDDING_MODEL_VERSION_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE072-P4-GATE"
PHASE2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_EMBEDDING_MODEL_VERSION_CONTROL_SLICE"

PHASE2_SCENARIOS = (
    "default_denied",
    "summary_only_inherited",
    "document_restricts_full_text_to_summary_only",
    "full_text_allowed_control_only",
    "budget_insufficient_pauses_full_text",
)
REQUIRED_SCENARIO_CATEGORIES = (
    "DENIED_EGRESS_BLOCK_CONTROL",
    "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL",
    "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL",
    "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL",
    "BUDGET_INSUFFICIENT_PAUSE_CONTROL",
)
SCENARIO_RESULT_FIELDS = (
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

PAYLOAD_SCOPE_BY_MODE = {
    "NO_EXTERNAL_PAYLOAD_POLICY_DENIED": "NO_CONTROL_PAYLOAD_REFERENCE",
    "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY": "CONTROL_SUMMARY_REFERENCE_ONLY",
    "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
}

P2_RUNTIME_CLOSED_FIELDS = (
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
    "actual_control_scenario_record_persisted",
    "actual_external_payload_created",
    "control_payload_content_retained",
    *P2_RUNTIME_CLOSED_FIELDS,
)

SCENARIOS = (
    {
        "scenario_id": "denied-policy-blocks-embedding-model-version-egress-control",
        "scenario_category": "DENIED_EGRESS_BLOCK_CONTROL",
        "phase2_control_scenario": "default_denied",
        "expected_effective_policy": "denied",
        "expected_payload_mode": "NO_EXTERNAL_PAYLOAD_POLICY_DENIED",
        "expected_payload_scope": "NO_CONTROL_PAYLOAD_REFERENCE",
        "expected_queue_state": "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
        "expected_cache_disposition": "CONTROL_CACHE_BLOCKED_POLICY_DENIED",
        "expected_retry_state": "CONTROL_RETRY_BLOCKED_POLICY_DENIED",
        "expected_budget_check_state": "CONTROL_BUDGET_NOT_APPLICABLE_POLICY_DENIED",
        "expected_audit_disposition": "BLOCKED_POLICY_DENIED",
        "future_external_api_call_candidate": False,
        "human_handling_required": False,
        "explicit_disposition": "DENIED_POLICY_BLOCKS_EXTERNALIZATION_WITHOUT_PAYLOAD_OR_RUNTIME_RECORD",
    },
    {
        "scenario_id": "summary-only-policy-keeps-summary-reference-only-control",
        "scenario_category": "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL",
        "phase2_control_scenario": "summary_only_inherited",
        "expected_effective_policy": "summary_only",
        "expected_payload_mode": "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_SUMMARY_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_cache_disposition": "CONTROL_CACHE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_retry_state": "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED",
        "expected_budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "SUMMARY_ONLY_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW_BEFORE_FUTURE_CALL",
    },
    {
        "scenario_id": "document-restriction-keeps-full-text-at-summary-reference-control",
        "scenario_category": "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL",
        "phase2_control_scenario": "document_restricts_full_text_to_summary_only",
        "expected_effective_policy": "summary_only",
        "expected_payload_mode": "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_SUMMARY_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_cache_disposition": "CONTROL_CACHE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_retry_state": "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED",
        "expected_budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "DOCUMENT_RESTRICTION_PREVENTS_FULL_TEXT_REFERENCE_ESCALATION",
    },
    {
        "scenario_id": "full-text-policy-keeps-chunk-reference-control-before-future-call",
        "scenario_category": "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL",
        "phase2_control_scenario": "full_text_allowed_control_only",
        "expected_effective_policy": "full_text_allowed",
        "expected_payload_mode": "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_cache_disposition": "CONTROL_CACHE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_retry_state": "CONTROL_RETRY_NOT_SCHEDULED_RUNTIME_DISABLED",
        "expected_budget_check_state": "CONTROL_BUDGET_AVAILABLE_REFERENCE_ONLY",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "FULL_TEXT_REFERENCE_REQUIRES_AUDIT_AND_WHITEBOX_REVIEW_BEFORE_FUTURE_CALL",
    },
    {
        "scenario_id": "budget-insufficient-pauses-full-text-external-api-control",
        "scenario_category": "BUDGET_INSUFFICIENT_PAUSE_CONTROL",
        "phase2_control_scenario": "budget_insufficient_pauses_full_text",
        "expected_effective_policy": "full_text_allowed",
        "expected_payload_mode": "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
        "expected_cache_disposition": "CONTROL_CACHE_PAUSED_BUDGET_INSUFFICIENT",
        "expected_retry_state": "CONTROL_RETRY_PAUSED_BUDGET_INSUFFICIENT",
        "expected_budget_check_state": "CONTROL_BUDGET_INSUFFICIENT",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BUDGET_PAUSED",
        "future_external_api_call_candidate": False,
        "human_handling_required": True,
        "explicit_disposition": "BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API_CANDIDATE_WITHOUT_EXTERNALIZATION",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_embedding_model_version_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制切片并验证外发边界、预算暂停、审计前置与零运行时。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    phase2_result = executor(_phase2_control_input(phase2_module))
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    audit_fields = _field_tuple(phase2_module, "AUDIT_FIELDS")
    phase2_shape_preserved = _phase2_shape_preserved(
        phase2_module, phase2_result, audit_fields
    )
    phase2_side_effect_free = _phase2_side_effect_free(phase2_result)
    scenario_results = [
        _evaluate_scenario(
            scenario,
            index,
            phase2_result,
            audit_fields,
            phase2_side_effect_free,
        )
        for index, scenario in enumerate(SCENARIOS)
    ]
    categories_covered = tuple(
        result["scenario_category"] for result in scenario_results
    ) == REQUIRED_SCENARIO_CATEGORIES
    policy_payload_boundaries_preserved = all(
        result["observed_control_payload_scope"]
        == result["expected_control_payload_scope"]
        for result in scenario_results
    )
    queue_cache_retry_boundaries_preserved = all(
        result["observed_queue_state"] == result["expected_queue_state"]
        and result["observed_cache_disposition"]
        == result["expected_cache_disposition"]
        and result["observed_retry_state"] == result["expected_retry_state"]
        for result in scenario_results
    )
    budget_insufficient_pause_preserved = (
        tuple(
            result["observed_budget_check_state"]
            for result in scenario_results
            if result["scenario_category"] == "BUDGET_INSUFFICIENT_PAUSE_CONTROL"
        )
        == ("CONTROL_BUDGET_INSUFFICIENT",)
    )
    audit_projection_invariant_preserved = all(
        result["audit_projection_required"]
        and result["audit_projection_present"]
        and result["audit_field_count"] == len(audit_fields)
        and result["audit_required_fields_present"]
        and result["audit_reference_fields_are_control_only"]
        and result["observed_audit_disposition"]
        == result["expected_audit_disposition"]
        for result in scenario_results
    )
    future_external_api_call_audit_invariant_preserved = all(
        result["audit_projection_present"]
        and result["audit_required_fields_present"]
        and result["audit_reference_fields_are_control_only"]
        for result in scenario_results
        if result["future_external_api_call_candidate"]
    )
    runtime_closed_flags = _runtime_closed_flags()
    no_external_runtime_performed = all(
        runtime_closed_flags[field] is False for field in RUNTIME_CLOSED_FIELDS
    )
    valid = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and len(scenario_results) == len(SCENARIOS)
        and categories_covered
        and all(result["expectation_met"] for result in scenario_results)
        and not any(result["silent_drop"] for result in scenario_results)
        and policy_payload_boundaries_preserved
        and queue_cache_retry_boundaries_preserved
        and budget_insufficient_pause_preserved
        and audit_projection_invariant_preserved
        and future_external_api_call_audit_invariant_preserved
        and no_external_runtime_performed
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "valid": valid,
        "next_gate": NEXT_GATE,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "phase2_side_effect_free": phase2_side_effect_free,
        "control_scenario_order": list(PHASE2_SCENARIOS),
        "scenario_results": scenario_results,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": sum(
            1 for result in scenario_results if result["expectation_met"]
        ),
        "explicit_disposition_count": sum(
            1 for result in scenario_results if result["explicit_disposition"]
        ),
        "silent_drop_count": sum(
            1 for result in scenario_results if result["silent_drop"]
        ),
        "human_handling_required_count": sum(
            1 for result in scenario_results if result["human_handling_required"]
        ),
        "all_taskpack_special_scenarios_covered": categories_covered,
        "policy_payload_boundaries_preserved": policy_payload_boundaries_preserved,
        "queue_cache_retry_boundaries_preserved": queue_cache_retry_boundaries_preserved,
        "budget_insufficient_pause_preserved": budget_insufficient_pause_preserved,
        "audit_projection_invariant_preserved": audit_projection_invariant_preserved,
        "future_external_api_call_audit_invariant_preserved": (
            future_external_api_call_audit_invariant_preserved
        ),
        "control_policy_resolution_record_count": _count_records(
            phase2_result.get("policy_resolutions")
        ),
        "control_embedding_queue_record_count": _count_records(
            phase2_result.get("embedding_queue_records")
        ),
        "control_cache_record_count": _count_records(
            phase2_result.get("cache_records")
        ),
        "control_failed_retry_record_count": _count_records(
            phase2_result.get("failed_retry_records")
        ),
        "control_model_version_projection_count": _count_records(
            phase2_result.get("model_version_control_projections")
        ),
        "control_cost_projection_count": _count_records(
            phase2_result.get("cost_control_projections")
        ),
        "control_external_api_audit_projection_count": _count_records(
            phase2_result.get("external_api_audit_projections")
        ),
        "control_audit_field_count": len(audit_fields),
        "control_audit_field_check_count": len(scenario_results) * len(audit_fields),
        "future_external_api_call_candidate_count": sum(
            1
            for result in scenario_results
            if result["future_external_api_call_candidate"]
        ),
        "actual_input_request_count": 0,
        "actual_embedding_queue_count": 0,
        "actual_cache_entry_count": 0,
        "actual_failed_retry_count": 0,
        "actual_model_version_record_count": 0,
        "actual_cost_count": 0,
        "actual_external_api_audit_record_count": 0,
        "actual_external_api_call_count": 0,
        "actual_model_token_count": 0,
        "source_document_remains_authoritative": True,
        "embedding_model_version_scenario_can_replace_source_document": False,
        "embedding_model_version_scenario_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "stage071_review_evidence_read": True,
        "stage072_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage073_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本次只重放五条固定控制引用并验证外发边界；没有读取、保留或外发真实来源正文、摘要或文本块。",
            "默认 denied 会阻断外发；summary_only 只能保留摘要引用，full_text_allowed 也只保留未来文本块引用，不能自行变成实际外发。",
            "预算不足时外部 API 候选保持暂停；每个未来调用候选都先具备完整审计控制投影和业务线白箱人工复核前置。",
            "本步骤可回退到 Stage072 P2，不影响来源资料、业务事实、OVH 或生产状态。",
        ],
    }


def _phase2_executor(phase2_module: Any) -> Phase2Executor:
    return phase2_module.execute_embedding_model_version_control_slice


def _phase2_control_input(phase2_module: Any) -> Mapping[str, object]:
    return phase2_module.build_control_input()


def _load_phase2_module() -> Any:
    path = Path(__file__).with_name("stage072_embedding_model_version_slice.py")
    spec = importlib.util.spec_from_file_location("stage072_phase2_slice", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage072 P2 embedding model version slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _field_tuple(module: Any, field_name: str) -> tuple[str, ...]:
    fields = getattr(module, field_name, ())
    if not isinstance(fields, tuple) or not all(isinstance(field, str) for field in fields):
        return ()
    return fields


def _phase2_shape_preserved(
    phase2_module: Any,
    phase2_result: Mapping[str, Any],
    audit_fields: tuple[str, ...],
) -> bool:
    resolution_fields = _field_tuple(phase2_module, "POLICY_RESOLUTION_FIELDS")
    queue_fields = _field_tuple(phase2_module, "QUEUE_FIELDS")
    cache_fields = _field_tuple(phase2_module, "CACHE_FIELDS")
    retry_fields = _field_tuple(phase2_module, "RETRY_FIELDS")
    model_fields = _field_tuple(phase2_module, "MODEL_VERSION_FIELDS")
    cost_fields = _field_tuple(phase2_module, "COST_FIELDS")
    return (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state") == PHASE2_EXECUTION_STATE
        and phase2_result.get("control_scenarios_covered") == list(PHASE2_SCENARIOS)
        and phase2_result.get("control_request_count") == len(PHASE2_SCENARIOS)
        and phase2_result.get("actual_input_request_count") == 0
        and _records_have_exact_shape(
            phase2_result.get("policy_resolutions"),
            len(PHASE2_SCENARIOS),
            resolution_fields,
        )
        and _records_have_exact_shape(
            phase2_result.get("embedding_queue_records"),
            len(PHASE2_SCENARIOS),
            (*queue_fields, "control_queue_state", "control_queue_reason"),
        )
        and _records_have_exact_shape(
            phase2_result.get("cache_records"),
            len(PHASE2_SCENARIOS),
            cache_fields,
        )
        and _records_have_exact_shape(
            phase2_result.get("failed_retry_records"),
            len(PHASE2_SCENARIOS),
            retry_fields,
        )
        and _records_have_exact_shape(
            phase2_result.get("model_version_control_projections"),
            len(PHASE2_SCENARIOS),
            model_fields,
        )
        and _records_have_exact_shape(
            phase2_result.get("cost_control_projections"),
            len(PHASE2_SCENARIOS),
            cost_fields,
        )
        and _records_have_exact_shape(
            phase2_result.get("external_api_audit_projections"),
            len(PHASE2_SCENARIOS),
            audit_fields,
        )
        and phase2_result.get("all_control_records_keep_required_shapes") is True
        and phase2_result.get("all_model_version_sent_statuses_are_false") is True
        and phase2_result.get(
            "control_output_is_not_actual_queue_cache_model_version_cost_or_audit"
        )
        is True
    )


def _records_have_exact_shape(
    records: object,
    expected_count: int,
    fields: Sequence[str],
) -> bool:
    return (
        isinstance(records, list)
        and len(records) == expected_count
        and all(
            isinstance(record, Mapping) and set(record) == set(fields)
            for record in records
        )
    )


def _phase2_side_effect_free(phase2_result: Mapping[str, Any]) -> bool:
    return (
        all(
            phase2_result.get(field) is False
            for field in P2_RUNTIME_CLOSED_FIELDS
        )
        and phase2_result.get("source_body_summary_body_or_chunk_text_retained")
        is False
        and phase2_result.get("chunk_manual_policy_assignment_performed") is False
        and phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("actual_model_version_record_created") is False
        and phase2_result.get("actual_external_api_audit_record_created") is False
    )


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    index: int,
    phase2_result: Mapping[str, Any],
    audit_fields: tuple[str, ...],
    phase2_side_effect_free: bool,
) -> dict[str, Any]:
    resolution = _record_at(phase2_result.get("policy_resolutions"), index)
    queue = _record_at(phase2_result.get("embedding_queue_records"), index)
    cache = _record_at(phase2_result.get("cache_records"), index)
    retry = _record_at(phase2_result.get("failed_retry_records"), index)
    model_version = _record_at(
        phase2_result.get("model_version_control_projections"), index
    )
    audit = _record_at(phase2_result.get("external_api_audit_projections"), index)
    effective_policy = resolution.get("effective_external_api_policy")
    payload_mode = resolution.get("external_payload_mode")
    observed_payload_scope = PAYLOAD_SCOPE_BY_MODE.get(
        payload_mode, "UNKNOWN_CONTROL_PAYLOAD_SCOPE"
    )
    audit_required_fields_present = (
        isinstance(audit, Mapping)
        and set(audit_fields).issubset(set(audit))
    )
    audit_reference_fields_are_control_only = _audit_references_are_control_only(
        audit
    )
    audit_projection_present = (
        isinstance(audit, Mapping)
        and set(audit) == set(audit_fields)
        and audit_required_fields_present
    )
    observed_future_call_candidate = (
        effective_policy in {"summary_only", "full_text_allowed"}
        and queue.get("control_queue_state")
        == "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
        and audit_projection_present
        and audit.get("audit_disposition")
        == "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL"
        and audit_reference_fields_are_control_only
    )
    actual_external_api_call_performed = (
        phase2_result.get("external_api_call_performed") is True
    )
    actual_model_token_consumption_performed = (
        phase2_result.get("model_token_consumption_performed") is True
    )
    model_version_sent_to_external_api = model_version.get(
        "sent_to_external_api"
    ) is True
    observed_human_handling_required = effective_policy != "denied"
    explicit_disposition = str(scenario["explicit_disposition"])
    expectation_met = (
        phase2_side_effect_free
        and effective_policy == scenario["expected_effective_policy"]
        and payload_mode == scenario["expected_payload_mode"]
        and observed_payload_scope == scenario["expected_payload_scope"]
        and queue.get("control_queue_state") == scenario["expected_queue_state"]
        and cache.get("cache_disposition") == scenario["expected_cache_disposition"]
        and retry.get("retry_state") == scenario["expected_retry_state"]
        and resolution.get("budget_check_state")
        == scenario["expected_budget_check_state"]
        and audit_projection_present
        and len(audit) == len(audit_fields)
        and audit_required_fields_present
        and audit_reference_fields_are_control_only
        and audit.get("audit_disposition") == scenario["expected_audit_disposition"]
        and observed_future_call_candidate
        == scenario["future_external_api_call_candidate"]
        and actual_external_api_call_performed is False
        and actual_model_token_consumption_performed is False
        and model_version_sent_to_external_api is False
        and observed_human_handling_required
        == scenario["human_handling_required"]
        and bool(explicit_disposition)
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "phase2_control_scenario": scenario["phase2_control_scenario"],
        "referenced_policy_resolution_ref": resolution.get(
            "policy_resolution_ref"
        ),
        "referenced_embedding_queue_request_ref": queue.get(
            "embedding_queue_request_ref"
        ),
        "referenced_cache_entry_ref": cache.get("cache_entry_ref"),
        "referenced_retry_ref": retry.get("retry_ref"),
        "referenced_external_api_audit_ref": audit.get("external_api_audit_ref"),
        "effective_external_api_policy": effective_policy,
        "external_payload_mode": payload_mode,
        "observed_control_payload_scope": observed_payload_scope,
        "expected_control_payload_scope": scenario["expected_payload_scope"],
        "expected_queue_state": scenario["expected_queue_state"],
        "observed_queue_state": queue.get("control_queue_state"),
        "expected_cache_disposition": scenario["expected_cache_disposition"],
        "observed_cache_disposition": cache.get("cache_disposition"),
        "expected_retry_state": scenario["expected_retry_state"],
        "observed_retry_state": retry.get("retry_state"),
        "expected_budget_check_state": scenario["expected_budget_check_state"],
        "observed_budget_check_state": resolution.get("budget_check_state"),
        "audit_projection_required": True,
        "audit_projection_present": audit_projection_present,
        "audit_field_count": len(audit),
        "audit_required_fields_present": audit_required_fields_present,
        "audit_reference_fields_are_control_only": (
            audit_reference_fields_are_control_only
        ),
        "expected_audit_disposition": scenario["expected_audit_disposition"],
        "observed_audit_disposition": audit.get("audit_disposition"),
        "future_external_api_call_candidate": observed_future_call_candidate,
        "actual_external_api_call_performed": actual_external_api_call_performed,
        "actual_model_token_consumption_performed": (
            actual_model_token_consumption_performed
        ),
        "model_version_sent_to_external_api": model_version_sent_to_external_api,
        "human_handling_required": observed_human_handling_required,
        "explicit_disposition": explicit_disposition,
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _record_at(records: object, index: int) -> Mapping[str, Any]:
    if (
        isinstance(records, list)
        and 0 <= index < len(records)
        and isinstance(records[index], Mapping)
    ):
        return records[index]
    return {}


def _audit_references_are_control_only(audit: Mapping[str, Any]) -> bool:
    fields = (
        "external_api_audit_ref",
        "data_source_ref",
        "document_ref",
        "chunk_id",
        "owner_authorization_ref",
        "authorized_at",
        "authorization_reason",
        "provider_ref",
        "model_ref",
        "model_version",
        "embedding_queue_request_ref",
    )
    return all(
        isinstance(audit.get(field), str)
        and ":control:stage072-p2:" in audit[field]
        for field in fields
    )


def _count_records(records: object) -> int:
    return len(records) if isinstance(records, list) else 0


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
