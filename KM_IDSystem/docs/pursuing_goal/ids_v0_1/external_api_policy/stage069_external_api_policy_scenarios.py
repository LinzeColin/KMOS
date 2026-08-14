"""Stage069 P3 的外部 API 策略继承受控专项场景。

本模块只重放 Stage069 P2 的五条固定、非业务、reference-only 控制记录，验证
denied、summary_only、full_text_allowed、document 收紧与预算不足暂停的边界。
所有“载荷”只保留 :control: 引用类别，绝不创建摘要正文、文本块、provider 客户端、
队列、缓存、审计记录或任何真实外部 API 调用。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage069.external_api_policy.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_EXTERNAL_API_POLICY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_EXTERNAL_API_POLICY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EXTERNAL_API_POLICY_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE069-P4-GATE"
PHASE2_EXECUTION_STATE = (
    "COMPLETED_IN_MEMORY_EXTERNAL_API_POLICY_INHERITANCE_CONTROL_SLICE"
)
PHASE2_SCENARIOS = (
    "default_denied",
    "summary_only_inherited",
    "document_restricts_full_text_to_summary_only",
    "full_text_allowed_control_only",
    "budget_insufficient_pauses_full_text",
)
REQUIRED_SCENARIO_CATEGORIES = (
    "DENIED_NO_EXTERNALIZATION_CONTROL",
    "SUMMARY_ONLY_PAYLOAD_BOUNDARY_CONTROL",
    "DOCUMENT_RESTRICTION_PAYLOAD_BOUNDARY_CONTROL",
    "FULL_TEXT_PAYLOAD_BOUNDARY_CONTROL",
    "BUDGET_PAUSE_CONTROL",
)
SCENARIO_RESULT_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "referenced_policy_resolution_ref",
    "referenced_embedding_queue_request_ref",
    "referenced_external_api_audit_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "observed_control_payload_scope",
    "expected_control_payload_scope",
    "expected_queue_state",
    "observed_queue_state",
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
PAYLOAD_SCOPE_BY_MODE = {
    "NO_EXTERNAL_PAYLOAD_POLICY_DENIED": "NO_CONTROL_PAYLOAD_REFERENCE",
    "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY": "CONTROL_SUMMARY_REFERENCE_ONLY",
    "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
}
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
    "actual_cache_read_or_write_performed",
    "actual_cost_recorded",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "external_payload_created",
    "actual_external_payload_created",
    "control_payload_content_retained",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
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

SCENARIOS = (
    {
        "scenario_id": "denied-policy-blocks-externalization-control",
        "scenario_category": "DENIED_NO_EXTERNALIZATION_CONTROL",
        "phase2_control_scenario": "default_denied",
        "expected_source_policy": "denied",
        "expected_document_policy": None,
        "expected_effective_policy": "denied",
        "expected_payload_mode": "NO_EXTERNAL_PAYLOAD_POLICY_DENIED",
        "expected_payload_scope": "NO_CONTROL_PAYLOAD_REFERENCE",
        "expected_queue_state": "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
        "expected_audit_disposition": "BLOCKED_POLICY_DENIED",
        "future_external_api_call_candidate": False,
        "human_handling_required": False,
        "explicit_disposition": "DENIED_POLICY_BLOCKS_EXTERNALIZATION_WITHOUT_PAYLOAD",
    },
    {
        "scenario_id": "summary-only-policy-limits-control-payload",
        "scenario_category": "SUMMARY_ONLY_PAYLOAD_BOUNDARY_CONTROL",
        "phase2_control_scenario": "summary_only_inherited",
        "expected_source_policy": "summary_only",
        "expected_document_policy": None,
        "expected_effective_policy": "summary_only",
        "expected_payload_mode": "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_SUMMARY_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "SUMMARY_ONLY_CONTROL_REQUIRES_WHITEBOX_REVIEW_AND_AUDIT_BEFORE_FUTURE_CALL",
    },
    {
        "scenario_id": "document-restriction-limits-full-text-to-summary-control",
        "scenario_category": "DOCUMENT_RESTRICTION_PAYLOAD_BOUNDARY_CONTROL",
        "phase2_control_scenario": "document_restricts_full_text_to_summary_only",
        "expected_source_policy": "full_text_allowed",
        "expected_document_policy": "summary_only",
        "expected_effective_policy": "summary_only",
        "expected_payload_mode": "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_SUMMARY_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "DOCUMENT_RESTRICTION_PREVENTS_FULL_TEXT_CONTROL_PAYLOAD",
    },
    {
        "scenario_id": "full-text-policy-allows-only-control-text-reference",
        "scenario_category": "FULL_TEXT_PAYLOAD_BOUNDARY_CONTROL",
        "phase2_control_scenario": "full_text_allowed_control_only",
        "expected_source_policy": "full_text_allowed",
        "expected_document_policy": None,
        "expected_effective_policy": "full_text_allowed",
        "expected_payload_mode": "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": True,
        "human_handling_required": True,
        "explicit_disposition": "FULL_TEXT_CONTROL_REFERENCE_REQUIRES_WHITEBOX_REVIEW_AND_AUDIT_BEFORE_FUTURE_CALL",
    },
    {
        "scenario_id": "budget-insufficient-pauses-full-text-control",
        "scenario_category": "BUDGET_PAUSE_CONTROL",
        "phase2_control_scenario": "budget_insufficient_pauses_full_text",
        "expected_source_policy": "full_text_allowed",
        "expected_document_policy": None,
        "expected_effective_policy": "full_text_allowed",
        "expected_payload_mode": "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_payload_scope": "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
        "expected_queue_state": "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
        "expected_audit_disposition": "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
        "future_external_api_call_candidate": False,
        "human_handling_required": True,
        "explicit_disposition": "BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API_TASK_WITHOUT_EXTERNALIZATION",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_external_api_policy_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制切片并验证策略、审计和异常处置边界。"""

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
            phase2_result,
            audit_fields,
            phase2_side_effect_free,
        )
        for scenario in SCENARIOS
    ]
    categories_covered = tuple(
        result["scenario_category"] for result in scenario_results
    ) == REQUIRED_SCENARIO_CATEGORIES
    audit_projection_invariant_preserved = all(
        result["audit_projection_required"]
        and result["audit_projection_present"]
        and result["audit_field_count"] == len(audit_fields)
        for result in scenario_results
    )
    future_call_audit_invariant_preserved = all(
        result["audit_projection_present"]
        for result in scenario_results
        if result["future_external_api_call_candidate"]
    )
    payload_boundaries_preserved = all(
        result["observed_control_payload_scope"]
        == result["expected_control_payload_scope"]
        for result in scenario_results
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
        and payload_boundaries_preserved
        and audit_projection_invariant_preserved
        and future_call_audit_invariant_preserved
        and no_external_runtime_performed
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "phase2_side_effect_free": phase2_side_effect_free,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": sum(
            result["expectation_met"] for result in scenario_results
        ),
        "explicit_disposition_count": sum(
            bool(result["explicit_disposition"]) for result in scenario_results
        ),
        "silent_drop_count": sum(result["silent_drop"] for result in scenario_results),
        "human_handling_required_count": sum(
            result["human_handling_required"] for result in scenario_results
        ),
        "all_taskpack_special_scenarios_covered": categories_covered,
        "scenario_results": scenario_results,
        "control_policy_resolution_record_count": len(
            _mapping_sequence(phase2_result.get("policy_resolutions"))
        ),
        "control_external_api_audit_projection_count": len(
            _mapping_sequence(phase2_result.get("external_api_audit_projections"))
        ),
        "control_audit_field_count": len(audit_fields),
        "control_audit_field_check_count": sum(
            result["audit_field_count"] for result in scenario_results
        ),
        "audit_projection_required_count": sum(
            result["audit_projection_required"] for result in scenario_results
        ),
        "audit_projection_present_count": sum(
            result["audit_projection_present"] for result in scenario_results
        ),
        "future_external_api_call_candidate_count": sum(
            result["future_external_api_call_candidate"] for result in scenario_results
        ),
        "future_external_api_call_audit_invariant_preserved": (
            future_call_audit_invariant_preserved
        ),
        "denied_control_blocked_count": sum(
            result["observed_queue_state"] == "CONTROL_QUEUE_BLOCKED_POLICY_DENIED"
            for result in scenario_results
        ),
        "summary_only_control_scope_count": sum(
            result["observed_control_payload_scope"]
            == "CONTROL_SUMMARY_REFERENCE_ONLY"
            for result in scenario_results
        ),
        "full_text_control_scope_count": sum(
            result["observed_control_payload_scope"]
            == "CONTROL_CHUNK_TEXT_REFERENCE_ONLY"
            and result["observed_queue_state"]
            == "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED"
            for result in scenario_results
        ),
        "budget_insufficient_paused_count": sum(
            result["observed_queue_state"] == "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT"
            for result in scenario_results
        ),
        "control_payload_content_retained": False,
        "actual_input_request_count": 0,
        "actual_external_api_call_count": 0,
        "actual_model_token_count": 0,
        "actual_external_api_audit_record_count": 0,
        "source_document_remains_authoritative": True,
        "external_api_policy_scenario_can_replace_source_document": False,
        "external_api_policy_scenario_can_become_business_fact_authority": False,
        "model_direct_text_guessing_allowed": False,
        "automatic_business_recommendation_allowed": False,
        **runtime_closed_flags,
        "stage069_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage070_started": False,
        "stage070_entry_allowed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "chinese_feedback": [
            "已重放五条固定外部 API 策略控制场景；结果只验证策略、队列意图、审计投影和异常处置，不代表真实资料、摘要正文、文本块或外部调用。",
            "denied 固定不形成外发载荷；summary_only 只保留受控摘要引用类别；full_text_allowed 只保留受控文本块引用类别，均没有创建实际载荷。",
            "预算不足的全文控制记录固定暂停，未创建队列、缓存、provider 客户端或外部任务；策略例外仍需业务线白箱人工复核。",
            "每条控制场景均有十八字段审计投影；未来可能调用的控制情形必须先有审计投影，本轮没有持久化审计记录、外部 API 调用或模型 Token。",
        ],
    }


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage069_external_api_policy_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage069_external_api_policy_p2", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage069 P2 control slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_executor(module: Any) -> Phase2Executor:
    executor = getattr(module, "execute_external_api_policy_control_slice", None)
    if not callable(executor):
        raise RuntimeError("Stage069 P2 executor is unavailable")
    return executor


def _phase2_control_input(module: Any) -> dict[str, object]:
    builder = getattr(module, "build_control_input", None)
    if not callable(builder):
        raise RuntimeError("Stage069 P2 control input builder is unavailable")
    control_input = builder()
    if not isinstance(control_input, Mapping):
        raise RuntimeError("Stage069 P2 control input is invalid")
    return dict(control_input)


def _field_tuple(module: Any, name: str) -> tuple[str, ...]:
    value = getattr(module, name, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _phase2_shape_preserved(
    phase2_module: Any,
    phase2_result: Mapping[str, Any],
    audit_fields: Sequence[str],
) -> bool:
    resolution_fields = _field_tuple(phase2_module, "POLICY_RESOLUTION_FIELDS")
    resolutions = _mapping_sequence(phase2_result.get("policy_resolutions"))
    queue_intents = _mapping_sequence(phase2_result.get("embedding_queue_intents"))
    queue_dispositions = _mapping_sequence(
        phase2_result.get("queue_intent_dispositions")
    )
    cost_records = _mapping_sequence(phase2_result.get("cost_model_records"))
    audit_projections = _mapping_sequence(
        phase2_result.get("external_api_audit_projections")
    )
    return (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state") == PHASE2_EXECUTION_STATE
        and phase2_result.get("control_policy_request_count") == 5
        and phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("control_scenarios_covered") == list(PHASE2_SCENARIOS)
        and phase2_result.get("policy_resolution_count") == 5
        and len(resolutions) == 5
        and all(set(item) == set(resolution_fields) for item in resolutions)
        and phase2_result.get("embedding_queue_intent_count") == 5
        and len(queue_intents) == 5
        and len(queue_dispositions) == 5
        and phase2_result.get("cost_model_record_count") == 5
        and len(cost_records) == 5
        and phase2_result.get("external_api_audit_projection_count") == 5
        and len(audit_projections) == 5
        and len(audit_fields) == 18
        and all(set(item) == set(audit_fields) for item in audit_projections)
        and phase2_result.get("control_cache_state")
        == "CONTROL_CACHE_DISABLED_NO_READ_OR_WRITE"
        and phase2_result.get("control_queue_blocked_policy_denied_count") == 1
        and phase2_result.get("control_queue_paused_budget_insufficient_count") == 1
        and phase2_result.get("control_queue_eligible_but_not_persisted_count") == 3
    )


def _phase2_side_effect_free(phase2_result: Mapping[str, Any]) -> bool:
    return all(phase2_result.get(field, False) is False for field in RUNTIME_CLOSED_FIELDS)


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    phase2_result: Mapping[str, Any],
    audit_fields: Sequence[str],
    phase2_side_effect_free: bool,
) -> dict[str, Any]:
    phase2_scenario = str(scenario["phase2_control_scenario"])
    resolution = _resolution_for_scenario(phase2_scenario, phase2_result)
    queue_disposition = _queue_disposition_for_resolution(resolution, phase2_result)
    audit_projection = _audit_projection_for_resolution(resolution, phase2_result)
    observed_mode = (
        resolution.get("external_payload_mode") if resolution is not None else None
    )
    observed_scope = PAYLOAD_SCOPE_BY_MODE.get(
        observed_mode, "INVALID_CONTROL_PAYLOAD_MODE_FAIL_CLOSED"
    )
    observed_queue_state = (
        queue_disposition.get("control_queue_state")
        if queue_disposition is not None
        else None
    )
    audit_projection_present = _audit_projection_preserved(
        audit_projection, audit_fields, resolution
    )
    audit_field_count = len(audit_projection) if audit_projection_present else 0
    resolution_matches = (
        resolution is not None
        and resolution.get("source_external_api_policy")
        == scenario["expected_source_policy"]
        and resolution.get("document_external_api_policy")
        == scenario["expected_document_policy"]
        and resolution.get("effective_external_api_policy")
        == scenario["expected_effective_policy"]
        and observed_mode == scenario["expected_payload_mode"]
    )
    expectation_met = (
        resolution_matches
        and observed_scope == scenario["expected_payload_scope"]
        and observed_queue_state == scenario["expected_queue_state"]
        and audit_projection_present
        and audit_projection.get("audit_disposition")
        == scenario["expected_audit_disposition"]
        and phase2_side_effect_free
    )
    explicit_disposition = (
        str(scenario["explicit_disposition"])
        if resolution is not None and audit_projection_present
        else "CONTROL_SCENARIO_INVALID_FAIL_CLOSED"
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "phase2_control_scenario": phase2_scenario,
        "referenced_policy_resolution_ref": (
            resolution.get("policy_resolution_ref") if resolution else None
        ),
        "referenced_embedding_queue_request_ref": (
            resolution.get("embedding_queue_request_ref") if resolution else None
        ),
        "referenced_external_api_audit_ref": (
            resolution.get("external_api_audit_ref") if resolution else None
        ),
        "effective_external_api_policy": (
            resolution.get("effective_external_api_policy") if resolution else None
        ),
        "external_payload_mode": observed_mode,
        "observed_control_payload_scope": observed_scope,
        "expected_control_payload_scope": scenario["expected_payload_scope"],
        "expected_queue_state": scenario["expected_queue_state"],
        "observed_queue_state": observed_queue_state,
        "audit_projection_required": True,
        "audit_projection_present": audit_projection_present,
        "audit_field_count": audit_field_count,
        "audit_disposition": (
            audit_projection.get("audit_disposition") if audit_projection else None
        ),
        "future_external_api_call_candidate": scenario[
            "future_external_api_call_candidate"
        ],
        "actual_external_api_call_performed": False,
        "actual_model_token_consumption_performed": False,
        "human_handling_required": scenario["human_handling_required"],
        "explicit_disposition": explicit_disposition,
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _resolution_for_scenario(
    scenario: str, phase2_result: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    expected_ref = f"policy-resolution:control:stage069-p2:{scenario}"
    for resolution in _mapping_sequence(phase2_result.get("policy_resolutions")):
        if resolution.get("policy_resolution_ref") == expected_ref:
            return resolution
    return None


def _queue_disposition_for_resolution(
    resolution: Mapping[str, Any] | None, phase2_result: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    if resolution is None:
        return None
    expected_ref = resolution.get("embedding_queue_request_ref")
    for disposition in _mapping_sequence(
        phase2_result.get("queue_intent_dispositions")
    ):
        if disposition.get("embedding_queue_request_ref") == expected_ref:
            return disposition
    return None


def _audit_projection_for_resolution(
    resolution: Mapping[str, Any] | None, phase2_result: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    if resolution is None:
        return None
    expected_ref = resolution.get("external_api_audit_ref")
    for projection in _mapping_sequence(
        phase2_result.get("external_api_audit_projections")
    ):
        if projection.get("external_api_audit_ref") == expected_ref:
            return projection
    return None


def _audit_projection_preserved(
    audit_projection: Mapping[str, Any] | None,
    audit_fields: Sequence[str],
    resolution: Mapping[str, Any] | None,
) -> bool:
    if audit_projection is None or resolution is None:
        return False
    return (
        set(audit_projection) == set(audit_fields)
        and audit_projection.get("external_api_audit_ref")
        == resolution.get("external_api_audit_ref")
        and audit_projection.get("policy_inheritance_reason")
        == resolution.get("policy_inheritance_reason")
        and audit_projection.get("embedding_queue_request_ref")
        == resolution.get("embedding_queue_request_ref")
        and audit_projection.get("effective_external_api_policy")
        == resolution.get("effective_external_api_policy")
        and audit_projection.get("external_payload_mode")
        == resolution.get("external_payload_mode")
        and audit_projection.get("token_count") == 0
        and audit_projection.get("cost_estimate") == 0
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
