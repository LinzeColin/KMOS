"""Stage099 P3 的纯内存内部依据与外部增强异常场景验证。

模块只重放 Stage099 P2 固定、非业务、reference-only 控制投影。它验证检索
文档内提示词不能覆盖 IDS 规则、evidence_gap 保持证据缺口身份，并且三类高风险
输出保留业务线白箱人工处理门禁。模块不读取真实资料或运行时记录，不调用模型，
不消费模型 Token，也不创建持久化记录。
"""

import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase3.v1"
)
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SCENARIOS"
CURRENT_GATE = "IDS-STAGE099-P3-GATE"
NEXT_GATE = "IDS-STAGE099-P4-GATE"
PASS_RESULT = (
    "PASS_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
)
FAIL_RESULT = (
    "FAIL_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
)
P2_SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase2.v1"
)
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION"
P2_EXECUTION_STATE = (
    "PASS_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED"
)
P2_CONTROL_PREFIX = ":control:stage099-p2:"

P2_CONTROL_SCENARIOS = (
    "internal_evidence_with_external_augmentation_opinion_reference_only",
    "evidence_gap_with_external_augmentation_opinion_reference_only",
    "retrieval_document_instruction_rejected_reference_only",
    "high_risk_engineering_advice_confirmation_required_reference_only",
    "contract_commitment_confirmation_required_reference_only",
    "production_writeback_confirmation_required_reference_only",
)
P2_PROJECTION_SPECS = (
    (
        "answer_contract_and_prompt_binding",
        "ANSWER_CONTRACT_AND_PROMPT_BINDING_FIELDS",
    ),
    (
        "query_index_version_and_selected_evidence_record",
        "QUERY_INDEX_VERSION_AND_SELECTED_EVIDENCE_RECORD_FIELDS",
    ),
    (
        "source_type_and_external_augmentation_opinion_display",
        "SOURCE_TYPE_AND_EXTERNAL_AUGMENTATION_OPINION_DISPLAY_FIELDS",
    ),
    (
        "prompt_injection_and_output_permission",
        "PROMPT_INJECTION_AND_OUTPUT_PERMISSION_FIELDS",
    ),
)
P2_ZERO_COUNTER_FIELDS = (
    "actual_input_request_count",
    "actual_query_record_count",
    "actual_index_version_record_count",
    "actual_prompt_version_record_count",
    "actual_model_version_record_count",
    "actual_selected_evidence_record_count",
    "actual_retrieval_execution_count",
    "actual_prompt_execution_count",
    "actual_model_reasoning_count",
    "actual_model_output_classification_count",
    "actual_human_confirmation_count",
    "actual_answer_publication_count",
    "actual_production_writeback_count",
    "actual_audit_log_write_count",
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "retrieval_execution_performed",
    "retrieval_document_instruction_processed",
    "prompt_execution_performed",
    "prompt_injection_defense_execution_performed",
    "query_recorded",
    "index_version_recorded",
    "prompt_version_recorded",
    "model_version_recorded",
    "selected_evidence_recorded",
    "source_type_binding_performed",
    "external_augmentation_displayed",
    "model_output_classification_performed",
    "human_confirmation_performed",
    "answer_publication_performed",
    "production_writeback_performed",
    "database_schema_migration_performed",
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
)
ZERO_COUNTER_FIELDS = (
    "actual_prompt_injection_defense_execution_count",
    "actual_source_type_binding_count",
    "actual_output_classification_count",
    "actual_human_confirmation_count",
    "actual_answer_publication_count",
    "actual_production_writeback_count",
    "actual_database_connection_count",
    "actual_model_token_count",
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
    "model_version_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "evidence_gap_ref",
    "human_confirmation_gate_ref",
    "external_augmentation_ref",
    "external_augmentation_display_label",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "output_permission_state",
    "final_conclusion_state",
    "source_type_separation_state",
    "external_augmentation_display_state",
    "display_label_is_not_source_type_state",
    "display_preserves_underlying_source_types_state",
    "internal_evidence_present",
    "evidence_gap_present",
    "business_line_whitebox_human_approval_recorded",
    "human_handling_required",
    "expectation_met",
)
CONTROL_VIEW_FIELDS = {
    "answer_contract_and_prompt_binding_control_view": (
        "scenario_id",
        "phase2_control_scenario",
        "prompt_version_ref",
        "model_version_ref",
        "human_confirmation_gate_ref",
    ),
    "query_index_version_and_selected_evidence_control_view": (
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
    ),
    "source_type_and_external_augmentation_opinion_control_view": (
        "scenario_id",
        "internal_evidence_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "evidence_gap_ref",
        "external_augmentation_ref",
        "external_augmentation_display_label",
        "source_type_separation_state",
        "external_augmentation_display_state",
        "display_label_is_not_source_type_state",
        "display_preserves_underlying_source_types_state",
    ),
    "prompt_injection_control_view": (
        "scenario_id",
        "retrieval_document_instruction_precedence_state",
        "prompt_injection_defense_state",
    ),
    "output_permission_control_view": (
        "scenario_id",
        "human_confirmation_gate_ref",
        "output_permission_state",
        "final_conclusion_state",
        "human_handling_required",
    ),
}
SCENARIO_DEFINITIONS = (
    {
        "scenario_id": (
            "external_augmentation_opinion_preserves_source_type_separation_control"
        ),
        "scenario_category": "SOURCE_TYPE_SEPARATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": (
            "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED"
        ),
        "expected_output_permission_state": (
            "CONTROL_INFORMATIONAL_OUTPUT_REMAINS_REFERENCE_ONLY"
        ),
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EXTERNAL_AUGMENTATION_SOURCE_TYPES"
        ),
    },
    {
        "scenario_id": (
            "evidence_gap_cannot_masquerade_as_internal_experience_separation_control"
        ),
        "scenario_category": "EVIDENCE_GAP_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_internal_evidence_present": False,
        "expected_evidence_gap_present": True,
        "expected_prompt_injection_defense_state": (
            "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED"
        ),
        "expected_output_permission_state": (
            "CONTROL_EVIDENCE_GAP_REQUIRES_HUMAN_WHITEBOX_CONFIRMATION"
        ),
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_GAP_BEFORE_BUSINESS_USE"
        ),
    },
    {
        "scenario_id": "retrieval_document_cannot_override_ids_rule_separation_control",
        "scenario_category": "PROMPT_INJECTION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": (
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        ),
        "expected_output_permission_state": (
            "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW"
        ),
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_UNTRUSTED_DOCUMENT_INSTRUCTION"
        ),
    },
    {
        "scenario_id": (
            "high_risk_engineering_advice_requires_whitebox_confirmation_separation_control"
        ),
        "scenario_category": "HIGH_RISK_ENGINEERING_ADVICE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": (
            "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED"
        ),
        "expected_output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_HIGH_RISK_ENGINEERING_ADVICE"
        ),
        "auto_finalization_failure_state": "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
    },
    {
        "scenario_id": (
            "contract_commitment_requires_whitebox_confirmation_separation_control"
        ),
        "scenario_category": "CONTRACT_COMMITMENT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": (
            "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED"
        ),
        "expected_output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_CONTRACT_COMMITMENT",
        "auto_finalization_failure_state": "CONTRACT_COMMITMENT_AUTO_FINALIZED",
    },
    {
        "scenario_id": (
            "production_writeback_requires_whitebox_confirmation_separation_control"
        ),
        "scenario_category": "PRODUCTION_WRITEBACK_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[5],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_prompt_injection_defense_state": (
            "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED"
        ),
        "expected_output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_PRODUCTION_WRITEBACK",
        "auto_finalization_failure_state": "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage099_internal_evidence_external_augmentation_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage099_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage099 P2 control slice")
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
        "second_authoritative_source_created": False,
        "phase2_control_request_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_field_check_count": 0,
        "scenario_count": 0,
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": 0,
        "scenario_results": [],
        "control_view_count": 0,
        "control_views": {},
        "human_handling_count": 0,
        "human_handlings": [],
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
    if all(isinstance(item, Mapping) for item in records.values()):
        return records
    return None


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        getattr(phase2_module, "SCHEMA_VERSION", None) != P2_SCHEMA_VERSION
        or getattr(phase2_module, "RECORD_KIND", None) != P2_RECORD_KIND
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
        != ("internal_evidence_external_augmentation_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != 19
        or result.get("schema_version") != P2_SCHEMA_VERSION
        or result.get("record_kind") != P2_RECORD_KIND
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("control_input_count") != len(P2_CONTROL_SCENARIOS)
        or result.get("control_projection_group_count") != len(P2_PROJECTION_SPECS)
        or result.get("control_projection_field_total_per_request") != 35
        or result.get("control_projection_field_total") != 210
    ):
        return False
    for prefix, field_constant in P2_PROJECTION_SPECS:
        fields = tuple(getattr(phase2_module, field_constant, ()))
        projections = result.get(f"{prefix}_control_projections")
        if (
            not fields
            or not isinstance(projections, list)
            or len(projections) != len(P2_CONTROL_SCENARIOS)
            or result.get(f"{prefix}_control_projection_count")
            != len(P2_CONTROL_SCENARIOS)
            or any(
                not isinstance(item, Mapping) or set(item) != set(fields)
                for item in projections
            )
        ):
            return False
    return True


def _phase2_runtime_is_closed(result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    return (
        result.get("persistent_record_created") is False
        and all(result.get(field) == 0 for field in P2_ZERO_COUNTER_FIELDS)
        and isinstance(boundary, Mapping)
        and all(boundary.get(field) is False for field in RUNTIME_CLOSED_FIELDS)
    )


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for scenario in P2_CONTROL_SCENARIOS:
        records = _phase2_projection_records(result, scenario)
        if records is None:
            return False
        binding = records["answer_contract_and_prompt_binding"]
        version = records["query_index_version_and_selected_evidence_record"]
        source = records["source_type_and_external_augmentation_opinion_display"]
        permission = records["prompt_injection_and_output_permission"]
        if not all(
            _control_ref(binding.get(field))
            for field in (
                "stage099_phase1_contract_ref",
                "stage098_review_prompt_versioning_control_ref",
                "rag_answer_structure_ref",
                "prompt_version_ref",
                "model_version_ref",
                "model_output_permission_ref",
                "human_confirmation_gate_ref",
            )
        ):
            return False
        if not all(
            _control_ref(version.get(field))
            for field in (
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_version_ref",
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
        if not all(
            _control_ref(permission.get(field))
            for field in ("model_output_permission_ref", "human_confirmation_gate_ref")
        ):
            return False
    return True


def _scenario_from_phase2(
    result: Mapping[str, Any], definition: Mapping[str, Any]
) -> Optional[dict[str, Any]]:
    records = _phase2_projection_records(result, definition["phase2_control_scenario"])
    if records is None:
        return None
    binding = records["answer_contract_and_prompt_binding"]
    version = records["query_index_version_and_selected_evidence_record"]
    source = records["source_type_and_external_augmentation_opinion_display"]
    permission = records["prompt_injection_and_output_permission"]
    internal_evidence_present = source["internal_evidence_ref"] is not None
    evidence_gap_present = source["evidence_gap_ref"] is not None
    scenario = {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "query_ref": version["query_ref"],
        "index_version_ref": version["index_version_ref"],
        "prompt_version_ref": binding["prompt_version_ref"],
        "model_version_ref": binding["model_version_ref"],
        "selected_evidence_ref": version["selected_evidence_ref"],
        "internal_evidence_ref": source["internal_evidence_ref"],
        "external_public_reference_ref": source["external_public_reference_ref"],
        "model_reasoning_ref": source["model_reasoning_ref"],
        "evidence_gap_ref": source["evidence_gap_ref"],
        "human_confirmation_gate_ref": permission["human_confirmation_gate_ref"],
        "external_augmentation_ref": source["external_augmentation_ref"],
        "external_augmentation_display_label": source[
            "external_augmentation_display_label"
        ],
        "retrieval_document_instruction_precedence_state": permission[
            "retrieval_document_instruction_precedence_state"
        ],
        "prompt_injection_defense_state": permission["prompt_injection_defense_state"],
        "output_permission_state": permission["output_permission_state"],
        "final_conclusion_state": permission["final_conclusion_state"],
        "source_type_separation_state": source["source_type_separation_state"],
        "external_augmentation_display_state": source[
            "external_augmentation_display_state"
        ],
        "display_label_is_not_source_type_state": source[
            "display_label_is_not_source_type_state"
        ],
        "display_preserves_underlying_source_types_state": source[
            "display_preserves_underlying_source_types_state"
        ],
        "internal_evidence_present": internal_evidence_present,
        "evidence_gap_present": evidence_gap_present,
        "business_line_whitebox_human_approval_recorded": False,
        "human_handling_required": True,
        "expectation_met": (
            internal_evidence_present
            is definition["expected_internal_evidence_present"]
            and evidence_gap_present is definition["expected_evidence_gap_present"]
            and permission["prompt_injection_defense_state"]
            == definition["expected_prompt_injection_defense_state"]
            and permission["output_permission_state"]
            == definition["expected_output_permission_state"]
            and permission["final_conclusion_state"]
            == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ),
    }
    if set(scenario) == set(SCENARIO_FIELDS):
        return scenario
    return None


def _scenario_failure_state(
    scenario: Mapping[str, Any], definition: Mapping[str, Any]
) -> Optional[str]:
    if (
        scenario["source_type_separation_state"]
        != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        or scenario["external_augmentation_display_label"]
        != "external_augmentation_opinion"
        or scenario["external_augmentation_display_state"]
        != "CONTROL_EXTERNAL_AUGMENTATION_OPINION_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        or scenario["display_label_is_not_source_type_state"]
        != "CONTROL_EXTERNAL_AUGMENTATION_OPINION_IS_DISPLAY_LABEL_ONLY"
        or scenario["display_preserves_underlying_source_types_state"]
        != "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
    ):
        return "EXTERNAL_AUGMENTATION_OPINION_SOURCE_TYPE_LOST"
    if definition["scenario_category"] == "EVIDENCE_GAP_CONTROL" and (
        scenario["internal_evidence_present"] or not scenario["evidence_gap_present"]
    ):
        return "EVIDENCE_GAP_PRESENTED_AS_INTERNAL_EXPERIENCE"
    if definition["scenario_category"] == "PROMPT_INJECTION_CONTROL" and (
        scenario["retrieval_document_instruction_precedence_state"]
        != "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        or scenario["prompt_injection_defense_state"]
        != "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        or scenario["output_permission_state"]
        != "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW"
        or scenario["final_conclusion_state"]
        != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
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
    if scenario["final_conclusion_state"] != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED":
        return "OUTPUT_PERMISSION_GATE_MISSING"
    if not scenario["expectation_met"]:
        return "SCENARIO_EXPECTATION_MISMATCH"
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


def build_internal_evidence_external_augmentation_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """重放 P2 固定控制投影并返回未持久化的 Stage099 P3 验证报告。"""

    try:
        phase2_module = _load_phase2_module()
        control_input = phase2_module.build_control_input()
        phase2_result = (
            phase2_executor(control_input)
            if phase2_executor is not None
            else phase2_module.execute_internal_evidence_external_augmentation_control_slice(
                control_input
            )
        )
    except Exception:
        return _base_report(False, "PHASE2_CONTROL_OUTPUT_INVALID")
    if not isinstance(phase2_result, Mapping):
        return _base_report(False, "PHASE2_CONTROL_OUTPUT_INVALID")
    if not _phase2_shape_is_preserved(phase2_module, phase2_result):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if not _phase2_runtime_is_closed(phase2_result):
        return _base_report(False, "PHASE2_RUNTIME_SIGNAL_DETECTED")
    if not _phase2_control_references_are_opaque(phase2_result):
        return _base_report(False, "CONTROL_REFERENCE_NOT_OPAQUE")

    scenarios: list[dict[str, Any]] = []
    for definition in SCENARIO_DEFINITIONS:
        scenario = _scenario_from_phase2(phase2_result, definition)
        if scenario is None:
            return _base_report(
                False,
                "PHASE3_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SCENARIOS_REJECTED",
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
        return _base_report(False, "HUMAN_HANDLING_SHAPE_MISMATCH")

    report = _base_report(True, None)
    report.update(
        {
            "phase2_control_shape_preserved": True,
            "phase2_side_effect_free": True,
            "control_references_opaque": True,
            "phase2_control_request_count": len(P2_CONTROL_SCENARIOS),
            "phase2_projection_group_count": len(P2_PROJECTION_SPECS),
            "phase2_field_check_count": 210,
            "scenario_count": len(scenarios),
            "scenario_field_count": len(SCENARIO_FIELDS),
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "scenario_results": scenarios,
            "control_view_count": len(views),
            "control_views": views,
            "human_handling_count": len(handlings),
            "human_handlings": handlings,
        }
    )
    return report
