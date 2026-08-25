"""Stage101 P3 RAG 可复现的纯内存专项异常场景验证。

本模块只重放 Stage101 P2 自身的固定、非业务、reference-only 控制投影。
它验证检索文档内指令无法覆盖 IDS 规则、内部依据不足保持 evidence_gap，
以及高风险工程建议、合同承诺和生产写回保持业务线白箱人工确认。模块不读取
真实资料、提示词、回答或检索结果，不调用模型、Agent、OVH 或生产服务，也不
创建持久化记录。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_SCENARIOS"
CURRENT_GATE = "IDS-STAGE101-P3-GATE"
NEXT_GATE = "IDS-STAGE101-P4-GATE"
PASS_RESULT = "PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY"
P2_EXECUTION_STATE = "PASS_IN_MEMORY_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED"
P2_CONTROL_PREFIX = ":control:stage101-p2:"
P2_CONTROL_REQUEST_COUNT = 6
P2_INPUT_FIELD_COUNT = 23
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 45
P2_PROJECTION_FIELD_COUNT_TOTAL = 270

P2_CONTROL_SCENARIOS = (
    "safe_summary_internal_evidence_with_external_augmentation_reference_only",
    "draft_recommendation_evidence_gap_with_external_augmentation_reference_only",
    "retrieval_document_instruction_rejected_reference_only",
    "high_risk_engineering_advice_confirmation_required_reference_only",
    "contractual_commitment_confirmation_required_reference_only",
    "production_writeback_confirmation_required_reference_only",
)

P2_PROJECTION_SPECS = (
    ("reproducibility_record_binding", "REPRODUCIBILITY_RECORD_BINDING_FIELDS"),
    ("reproducibility_record", "REPRODUCIBILITY_RECORD_FIELDS"),
    (
        "source_semantics_and_external_augmentation_display",
        "SOURCE_SEMANTICS_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS",
    ),
    (
        "prompt_injection_and_output_permission",
        "PROMPT_INJECTION_AND_OUTPUT_PERMISSION_FIELDS",
    ),
)

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "phase2_control_slice_runtime_executed",
    "retrieval_execution_performed",
    "retrieval_document_instruction_processed",
    "prompt_execution_performed",
    "prompt_injection_defense_execution_performed",
    "query_recorded",
    "index_version_recorded",
    "prompt_version_recorded",
    "model_provider_recorded",
    "model_version_recorded",
    "temperature_recorded",
    "retrieval_context_recorded",
    "selected_evidence_recorded",
    "source_type_binding_performed",
    "external_augmentation_displayed",
    "model_output_classification_performed",
    "human_confirmation_performed",
    "answer_publication_performed",
    "production_writeback_performed",
    "database_connection_performed",
    "audit_log_write_performed",
    "persistent_state_write_performed",
    "external_api_call_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage101_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_query_record_count",
    "actual_index_version_record_count",
    "actual_prompt_version_record_count",
    "actual_model_provider_record_count",
    "actual_model_version_record_count",
    "actual_temperature_record_count",
    "actual_retrieval_context_record_count",
    "actual_selected_evidence_record_count",
    "actual_retrieval_execution_count",
    "actual_prompt_execution_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_model_output_classification_count",
    "actual_human_confirmation_count",
    "actual_answer_publication_count",
    "actual_production_writeback_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_provider_ref",
    "model_version_ref",
    "temperature_ref",
    "retrieval_context_ref",
    "selected_evidence_ref",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "source_type_separation_state",
    "internal_evidence_ref",
    "evidence_gap_ref",
    "internal_evidence_present",
    "evidence_gap_present",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "external_augmentation_ref",
    "external_augmentation_display_label",
    "output_category",
    "output_permission_state",
    "final_conclusion_state",
    "human_handling_required",
    "business_line_whitebox_human_approval_recorded",
    "automatic_final_conclusion_allowed",
    "future_model_reasoning_candidate_declared",
    "actual_model_call_performed",
    "actual_answer_publication_performed",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "reproducibility_record_control_view": (
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_provider_ref",
        "model_version_ref",
        "temperature_ref",
        "retrieval_context_ref",
        "selected_evidence_ref",
    ),
    "source_type_and_external_augmentation_control_view": (
        "scenario_id",
        "internal_evidence_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "evidence_gap_ref",
        "source_type_separation_state",
        "external_augmentation_display_label",
    ),
    "prompt_injection_control_view": (
        "scenario_id",
        "retrieval_document_instruction_precedence_state",
        "prompt_injection_defense_state",
        "output_permission_state",
        "final_conclusion_state",
    ),
    "output_permission_control_view": (
        "scenario_id",
        "output_category",
        "output_permission_state",
        "final_conclusion_state",
        "human_handling_required",
    ),
    "future_candidate_and_actual_execution_control_view": (
        "scenario_id",
        "model_reasoning_ref",
        "future_model_reasoning_candidate_declared",
        "actual_model_call_performed",
        "actual_answer_publication_performed",
    ),
}

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "safe_summary_source_types_preserved_control",
        "scenario_category": "SOURCE_TYPE_AND_EXTERNAL_AUGMENTATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "expected_output_permission_state": "CONTROL_SAFE_SUMMARY_REFERENCE_ONLY",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_REVIEW_SAFE_SUMMARY_SOURCE_TYPES",
    },
    {
        "scenario_id": "draft_recommendation_evidence_gap_remains_declared_control",
        "scenario_category": "EVIDENCE_GAP_DECLARATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_internal_evidence_present": False,
        "expected_evidence_gap_present": True,
        "expected_prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "expected_output_permission_state": "CONTROL_DRAFT_RECOMMENDATION_REFERENCE_ONLY",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_GAP_DECLARATION",
    },
    {
        "scenario_id": "retrieval_document_cannot_override_ids_rule_control",
        "scenario_category": "PROMPT_INJECTION_REJECTION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
        "expected_output_permission_state": "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_REVIEW_UNTRUSTED_DOCUMENT_INSTRUCTION",
    },
    {
        "scenario_id": "high_risk_engineering_advice_requires_whitebox_confirmation_control",
        "scenario_category": "HIGH_RISK_ENGINEERING_ADVICE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "expected_output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_HIGH_RISK_ENGINEERING_ADVICE",
        "auto_finalization_failure_state": "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
    },
    {
        "scenario_id": "contractual_commitment_requires_whitebox_confirmation_control",
        "scenario_category": "CONTRACTUAL_COMMITMENT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "expected_output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_CONTRACTUAL_COMMITMENT",
        "auto_finalization_failure_state": "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
    },
    {
        "scenario_id": "production_writeback_requires_whitebox_confirmation_control",
        "scenario_category": "PRODUCTION_WRITEBACK_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[5],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "expected_output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_PRODUCTION_WRITEBACK",
        "auto_finalization_failure_state": "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage101_rag_reproducibility_control_slice.py")
    spec = importlib.util.spec_from_file_location("stage101_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage101 P2 RAG 可复现控制切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ZERO_COUNTER_FIELDS}


def _control_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P2_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _base_report(valid: bool, failure_state: Optional[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": CURRENT_GATE,
        "next_gate": NEXT_GATE if valid else CURRENT_GATE,
        "phase2_control_shape_preserved": False,
        "phase2_side_effect_free": False,
        "control_references_opaque": False,
        "phase2_control_request_count": 0,
        "phase2_input_field_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_projection_field_count_per_request": 0,
        "phase2_projection_field_count_total": 0,
        "scenario_count": 0,
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": 0,
        "scenario_results": [],
        "control_view_count": 0,
        "control_views": {},
        "human_handling_count": 0,
        "human_handlings": [],
        "future_model_reasoning_candidate_count": 0,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _phase2_projection_records(
    result: Mapping[str, Any], scenario: str
) -> Optional[dict[str, Mapping[str, Any]]]:
    try:
        index = P2_CONTROL_SCENARIOS.index(scenario)
        records = {
            prefix: result[f"{prefix}_control_projections"][index]
            for prefix, _field_constant in P2_PROJECTION_SPECS
        }
    except (IndexError, KeyError, TypeError):
        return None
    return records if all(isinstance(item, Mapping) for item in records.values()) else None


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        getattr(phase2_module, "SCHEMA_VERSION", None) != P2_SCHEMA_VERSION
        or getattr(phase2_module, "RECORD_KIND", None) != P2_RECORD_KIND
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
        != ("rag_reproducibility_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ()))
        != P2_INPUT_FIELD_COUNT
        or result.get("schema_version") != P2_SCHEMA_VERSION
        or result.get("record_kind") != P2_RECORD_KIND
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("control_input_count") != P2_CONTROL_REQUEST_COUNT
        or result.get("control_projection_group_count") != P2_PROJECTION_GROUP_COUNT
        or result.get("control_projection_field_total_per_request")
        != P2_PROJECTION_FIELD_COUNT_PER_REQUEST
        or result.get("control_projection_field_total")
        != P2_PROJECTION_FIELD_COUNT_TOTAL
    ):
        return False
    for prefix, field_constant in P2_PROJECTION_SPECS:
        fields = tuple(getattr(phase2_module, field_constant, ()))
        projections = result.get(f"{prefix}_control_projections")
        if (
            not fields
            or not isinstance(projections, list)
            or len(projections) != P2_CONTROL_REQUEST_COUNT
            or result.get(f"{prefix}_control_projection_count")
            != P2_CONTROL_REQUEST_COUNT
            or any(
                not isinstance(item, Mapping) or set(item) != set(fields)
                for item in projections
            )
        ):
            return False
    return True


def _phase2_runtime_is_closed(result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    actual_counts = [
        value
        for field, value in result.items()
        if field.startswith("actual_") and field.endswith("_count")
    ]
    return (
        result.get("persistent_record_created") is False
        and all(value == 0 for value in actual_counts)
        and isinstance(boundary, Mapping)
        and all(value is False for value in boundary.values())
    )


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for scenario in P2_CONTROL_SCENARIOS:
        records = _phase2_projection_records(result, scenario)
        if records is None:
            return False
        binding = records["reproducibility_record_binding"]
        reproducibility = records["reproducibility_record"]
        source = records["source_semantics_and_external_augmentation_display"]
        permission = records["prompt_injection_and_output_permission"]
        if not all(
            _control_ref(binding.get(field))
            for field in (
                "stage101_phase1_rag_reproducibility_contract_ref",
                "stage100_review_control_ref",
                "rag_answer_structure_ref",
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
                "selected_evidence_ref",
            )
        ):
            return False
        if not all(
            _control_ref(reproducibility.get(field))
            for field in (
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
                "selected_evidence_ref",
            )
        ):
            return False
        if not all(
            _control_ref(source.get(field))
            for field in (
                "source_type_ref",
                "external_public_reference_ref",
                "model_reasoning_ref",
                "external_augmentation_ref",
            )
        ):
            return False
        if source.get("internal_evidence_ref") is not None and not _control_ref(
            source.get("internal_evidence_ref")
        ):
            return False
        if source.get("evidence_gap_ref") is not None and not _control_ref(
            source.get("evidence_gap_ref")
        ):
            return False
        if (
            source.get("source_type_separation_state")
            != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
            or source.get("external_augmentation_display_label")
            != "external_augmentation_opinion"
            or source.get("external_augmentation_display_state")
            != "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
            or source.get("display_preserves_underlying_source_types_state")
            != "CONTROL_DISPLAY_PRESERVES_UNDERLYING_SOURCE_TYPES"
            or source.get("display_does_not_close_evidence_gap_state")
            != "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP"
        ):
            return False
        if not all(
            _control_ref(permission.get(field))
            for field in (
                "model_output_permission_ref",
                "human_confirmation_gate_ref",
            )
        ):
            return False
        if (
            not isinstance(permission.get("output_category"), str)
            or not permission["output_category"].startswith("CONTROL_OUTPUT_CATEGORY_")
            or permission.get("final_conclusion_state")
            != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
            or permission.get("automatic_publication_state")
            != "CONTROL_AUTOMATIC_PUBLICATION_DISABLED"
        ):
            return False
    return True


def _scenario_from_phase2(
    result: Mapping[str, Any], definition: Mapping[str, Any]
) -> Optional[dict[str, Any]]:
    records = _phase2_projection_records(result, definition["phase2_control_scenario"])
    if records is None:
        return None
    binding = records["reproducibility_record_binding"]
    source = records["source_semantics_and_external_augmentation_display"]
    permission = records["prompt_injection_and_output_permission"]
    internal_evidence_present = source["internal_evidence_ref"] is not None
    evidence_gap_present = source["evidence_gap_ref"] is not None
    scenario = {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "query_ref": binding["query_ref"],
        "index_version_ref": binding["index_version_ref"],
        "prompt_version_ref": binding["prompt_version_ref"],
        "model_provider_ref": binding["model_provider_ref"],
        "model_version_ref": binding["model_version_ref"],
        "temperature_ref": binding["temperature_ref"],
        "retrieval_context_ref": binding["retrieval_context_ref"],
        "selected_evidence_ref": binding["selected_evidence_ref"],
        "retrieval_document_instruction_precedence_state": permission[
            "retrieval_document_instruction_precedence_state"
        ],
        "prompt_injection_defense_state": permission["prompt_injection_defense_state"],
        "source_type_separation_state": source["source_type_separation_state"],
        "internal_evidence_ref": source["internal_evidence_ref"],
        "evidence_gap_ref": source["evidence_gap_ref"],
        "internal_evidence_present": internal_evidence_present,
        "evidence_gap_present": evidence_gap_present,
        "external_public_reference_ref": source["external_public_reference_ref"],
        "model_reasoning_ref": source["model_reasoning_ref"],
        "external_augmentation_ref": source["external_augmentation_ref"],
        "external_augmentation_display_label": source[
            "external_augmentation_display_label"
        ],
        "output_category": permission["output_category"],
        "output_permission_state": permission["output_permission_state"],
        "final_conclusion_state": permission["final_conclusion_state"],
        "human_handling_required": True,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_final_conclusion_allowed": False,
        "future_model_reasoning_candidate_declared": _control_ref(
            source["model_reasoning_ref"]
        ),
        "actual_model_call_performed": False,
        "actual_answer_publication_performed": False,
        "expectation_met": False,
    }
    scenario["expectation_met"] = (
        set(scenario) == set(SCENARIO_FIELDS)
        and internal_evidence_present
        is definition["expected_internal_evidence_present"]
        and evidence_gap_present is definition["expected_evidence_gap_present"]
        and scenario["prompt_injection_defense_state"]
        == definition["expected_prompt_injection_defense_state"]
        and scenario["output_permission_state"]
        == definition["expected_output_permission_state"]
        and scenario["final_conclusion_state"]
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        and scenario["source_type_separation_state"]
        == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        and scenario["external_augmentation_display_label"]
        == "external_augmentation_opinion"
        and scenario["human_handling_required"]
        and not scenario["business_line_whitebox_human_approval_recorded"]
        and not scenario["automatic_final_conclusion_allowed"]
        and scenario["future_model_reasoning_candidate_declared"]
        and not scenario["actual_model_call_performed"]
        and not scenario["actual_answer_publication_performed"]
    )
    return scenario if set(scenario) == set(SCENARIO_FIELDS) else None


def _scenario_failure_state(
    scenario: Mapping[str, Any], definition: Mapping[str, Any]
) -> Optional[str]:
    if (
        scenario["source_type_separation_state"]
        != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        or scenario["external_augmentation_display_label"]
        != "external_augmentation_opinion"
    ):
        return "EXTERNAL_AUGMENTATION_SOURCE_TYPE_LOST"
    if scenario["evidence_gap_present"] and scenario["internal_evidence_present"]:
        return "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE"
    if definition["scenario_category"] == "PROMPT_INJECTION_REJECTION_CONTROL" and (
        scenario["retrieval_document_instruction_precedence_state"]
        != "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        or scenario["prompt_injection_defense_state"]
        != "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
    ):
        return "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE"
    auto_failure = definition.get("auto_finalization_failure_state")
    if auto_failure and (
        scenario["output_permission_state"]
        != "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        or scenario["final_conclusion_state"]
        != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
    ):
        return str(auto_failure)
    if not scenario["expectation_met"]:
        return "CONTROLLED_SCENARIO_EXPECTATION_MISMATCH"
    return None


def _control_views(scenarios: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        name: [{field: scenario[field] for field in fields} for scenario in scenarios]
        for name, fields in CONTROL_VIEW_FIELDS.items()
    }


def _views_shape_is_valid(views: Mapping[str, Any]) -> bool:
    return (
        set(views) == set(CONTROL_VIEW_FIELDS)
        and all(
            isinstance(views[name], list)
            and len(views[name]) == len(SCENARIO_DEFINITIONS)
            and all(set(item) == set(fields) for item in views[name])
            for name, fields in CONTROL_VIEW_FIELDS.items()
        )
    )


def _human_handlings(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    definitions = {item["scenario_id"]: item for item in SCENARIO_DEFINITIONS}
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "scenario_category": scenario["scenario_category"],
            "human_handling_code": definitions[scenario["scenario_id"]][
                "human_handling_code"
            ],
            "business_line_whitebox_review_required": True,
            "business_line_whitebox_human_approval_recorded": False,
            "automatic_final_conclusion_allowed": False,
            "actual_human_confirmation_performed": False,
        }
        for scenario in scenarios
    ]


def _human_handlings_shape_is_valid(handlings: list[Mapping[str, Any]]) -> bool:
    required_fields = {
        "scenario_id",
        "scenario_category",
        "human_handling_code",
        "business_line_whitebox_review_required",
        "business_line_whitebox_human_approval_recorded",
        "automatic_final_conclusion_allowed",
        "actual_human_confirmation_performed",
    }
    return (
        len(handlings) == len(SCENARIO_DEFINITIONS)
        and all(set(item) == required_fields for item in handlings)
        and all(item["business_line_whitebox_review_required"] for item in handlings)
        and all(
            item["business_line_whitebox_human_approval_recorded"] is False
            and item["automatic_final_conclusion_allowed"] is False
            and item["actual_human_confirmation_performed"] is False
            for item in handlings
        )
    )


def build_rag_reproducibility_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """重放 P2 固定控制投影，返回未持久化的 P3 专项验证报告。"""

    phase2_module = _load_phase2_module()
    control_input = phase2_module.build_control_input()
    phase2_result = (
        phase2_executor(control_input)
        if phase2_executor is not None
        else phase2_module.execute_rag_reproducibility_control_slice(control_input)
    )
    if not isinstance(phase2_result, Mapping):
        return _base_report(False, "PHASE2_CONTROL_OUTPUT_INVALID")
    if not _phase2_shape_is_preserved(phase2_module, phase2_result):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if not _phase2_runtime_is_closed(phase2_result):
        return _base_report(False, "PHASE2_RUNTIME_BOUNDARY_BREACH")
    if phase2_result.get("persistent_record_created") is not False:
        return _base_report(False, "PERSISTENT_RECORD_CREATED")
    if phase2_result.get("second_authoritative_source_created") is True:
        return _base_report(False, "SECOND_AUTHORITY_CREATED")
    if not _phase2_control_references_are_opaque(phase2_result):
        return _base_report(False, "CONTROL_REFERENCE_NOT_OPAQUE")

    scenarios: list[dict[str, Any]] = []
    for definition in SCENARIO_DEFINITIONS:
        scenario = _scenario_from_phase2(phase2_result, definition)
        if scenario is None:
            return _base_report(
                False, "RAG_REPRODUCIBILITY_CONTROLLED_SCENARIO_REJECTED"
            )
        failure_state = _scenario_failure_state(scenario, definition)
        if failure_state is not None:
            return _base_report(False, failure_state)
        scenarios.append(scenario)

    views = _control_views(scenarios)
    if not _views_shape_is_valid(views):
        return _base_report(False, "CONTROL_VIEW_SHAPE_MISMATCH")
    handlings = _human_handlings(scenarios)
    if not _human_handlings_shape_is_valid(handlings):
        return _base_report(False, "BUSINESS_LINE_WHITEBOX_HANDLING_MISSING")

    report = _base_report(True, None)
    report.update(
        {
            "phase2_control_shape_preserved": True,
            "phase2_side_effect_free": True,
            "control_references_opaque": True,
            "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
            "phase2_input_field_count": P2_INPUT_FIELD_COUNT,
            "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
            "phase2_projection_field_count_per_request": (
                P2_PROJECTION_FIELD_COUNT_PER_REQUEST
            ),
            "phase2_projection_field_count_total": P2_PROJECTION_FIELD_COUNT_TOTAL,
            "scenario_count": len(scenarios),
            "scenario_field_count": len(SCENARIO_FIELDS),
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "scenario_results": scenarios,
            "control_view_count": len(views),
            "control_views": views,
            "human_handling_count": len(handlings),
            "human_handlings": handlings,
            "future_model_reasoning_candidate_count": sum(
                item["future_model_reasoning_candidate_declared"]
                for item in scenarios
            ),
        }
    )
    return report
