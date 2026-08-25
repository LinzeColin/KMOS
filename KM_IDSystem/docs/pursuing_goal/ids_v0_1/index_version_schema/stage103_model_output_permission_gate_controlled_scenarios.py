"""Stage103 P3 模型输出权限门禁的纯内存专项异常场景验证。

模块只重放 Stage103 P2 的固定、非业务、reference-only 控制投影。它验证
文档内潜在指令无法覆盖 IDS 规则、evidence_gap 保持独立语义，以及高风险
工程建议、合同承诺和生产写回保持业务线白箱人工确认与最终结论未发布。
模块不读取真实资料、文档、Prompt、回答或检索结果，不调用模型、Agent、OVH
或生产服务，也不创建持久化记录。
"""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = "ids.stage103.model_output_permission_gate.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_SCENARIOS"
CURRENT_GATE = "IDS-STAGE103-P3-GATE"
NEXT_GATE = "IDS-STAGE103-P4-GATE"
PASS_RESULT = "PASS_MODEL_OUTPUT_PERMISSION_GATE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_MODEL_OUTPUT_PERMISSION_GATE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

P2_SCHEMA_VERSION = "ids.stage103.model_output_permission_gate.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE"
P2_EXECUTION_STATE = (
    "PASS_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE_RUNTIME_DISABLED"
)
P2_CONTROL_PREFIX = ":control:stage103-p2:"
P2_CONTROL_REQUEST_COUNT = 5
P2_INPUT_FIELD_COUNT = 26
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 46
P2_PROJECTION_FIELD_COUNT_TOTAL = 230
P2_CONTROL_SCENARIOS = (
    "safe_summary_reference_only",
    "draft_recommendation_reference_only",
    "high_risk_engineering_advice_reference_only",
    "contractual_commitment_reference_only",
    "production_writeback_reference_only",
)
P2_PROJECTION_PREFIXES = (
    "answer_contract_and_reproducibility",
    "document_evidence_and_output_permission_defense",
    "source_semantics_and_external_augmentation_display",
    "output_permission_and_whitebox_gate",
)

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "phase2_control_slice_runtime_executed",
    "document_content_read_performed",
    "document_instruction_detection_performed",
    "document_instruction_handling_performed",
    "query_execution_performed",
    "retrieval_execution_performed",
    "prompt_execution_performed",
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
    "stage103_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_document_instruction_detection_count",
    "actual_document_instruction_handling_count",
    "actual_query_record_count",
    "actual_index_version_record_count",
    "actual_prompt_version_record_count",
    "actual_model_version_record_count",
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
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
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
    "human_confirmation_state",
    "final_conclusion_state",
    "automatic_final_conclusion_allowed",
    "business_line_whitebox_human_approval_recorded",
    "actual_model_call_performed",
    "actual_answer_publication_performed",
    "actual_production_writeback_performed",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "reproducibility_record_control_view": (
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
    ),
    "document_instruction_precedence_control_view": (
        "scenario_id",
        "document_instruction_candidate_ref",
        "ids_rule_ref",
        "document_instruction_evidence_state",
        "ids_rule_precedence_state",
        "injection_defense_state",
    ),
    "source_semantics_and_evidence_gap_control_view": (
        "scenario_id",
        "internal_evidence_ref",
        "evidence_gap_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "external_augmentation_ref",
        "external_augmentation_display_label",
        "source_type_separation_state",
    ),
    "output_permission_and_whitebox_gate_control_view": (
        "scenario_id",
        "output_category",
        "output_permission_state",
        "human_confirmation_state",
        "final_conclusion_state",
        "automatic_final_conclusion_allowed",
        "business_line_whitebox_human_approval_recorded",
    ),
    "actual_execution_boundary_control_view": (
        "scenario_id",
        "actual_model_call_performed",
        "actual_answer_publication_performed",
        "actual_production_writeback_performed",
    ),
}

HUMAN_CONFIRMATION_OUTPUT_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "document_instruction_cannot_override_ids_rule_control",
        "scenario_category": "IDS_RULE_PRECEDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_output_category": "safe_summary",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_IDS_RULE_PRECEDENCE"
        ),
    },
    {
        "scenario_id": "evidence_gap_cannot_masquerade_as_internal_experience_control",
        "scenario_category": "EVIDENCE_GAP_SEMANTICS_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_internal_evidence_present": False,
        "expected_evidence_gap_present": True,
        "expected_output_category": "draft_recommendation",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_GAP_SEMANTICS"
        ),
    },
    {
        "scenario_id": "high_risk_engineering_advice_requires_whitebox_confirmation_control",
        "scenario_category": "HIGH_RISK_ENGINEERING_ADVICE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_output_category": "high_risk_engineering_advice",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_HIGH_RISK_ENGINEERING_ADVICE"
        ),
        "auto_finalization_failure_state": "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
    },
    {
        "scenario_id": "contractual_commitment_requires_whitebox_confirmation_control",
        "scenario_category": "CONTRACTUAL_COMMITMENT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_output_category": "contractual_commitment",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_CONTRACTUAL_COMMITMENT"
        ),
        "auto_finalization_failure_state": "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
    },
    {
        "scenario_id": "production_writeback_requires_whitebox_confirmation_control",
        "scenario_category": "PRODUCTION_WRITEBACK_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_internal_evidence_present": True,
        "expected_evidence_gap_present": False,
        "expected_output_category": "production_writeback",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_PRODUCTION_WRITEBACK"
        ),
        "auto_finalization_failure_state": "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage103_model_output_permission_gate_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage103_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage103 P2 模型输出权限门禁控制切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ZERO_COUNTER_FIELDS}


def _is_control_reference(value: object) -> bool:
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
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        getattr(phase2_module, "SCHEMA_VERSION", None) != P2_SCHEMA_VERSION
        or getattr(phase2_module, "RECORD_KIND", None) != P2_RECORD_KIND
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
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

    projection_fields = dict(getattr(phase2_module, "PROJECTION_FIELDS", ()))
    if tuple(projection_fields) != P2_PROJECTION_PREFIXES:
        return False
    for prefix in P2_PROJECTION_PREFIXES:
        projections = result.get(f"{prefix}_control_projections")
        fields = projection_fields.get(prefix, ())
        if (
            not isinstance(projections, list)
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


def _phase2_runtime_is_closed(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    expected_boundary_fields = tuple(getattr(phase2_module, "RUNTIME_CLOSED_FIELDS", ()))
    expected_zero_counts = getattr(phase2_module, "_zero_actual_counts", lambda: {})()
    actual_counts = {
        field: value
        for field, value in result.items()
        if field.startswith("actual_") and field.endswith("_count")
    }
    return (
        result.get("persistent_record_created") is False
        and isinstance(boundary, Mapping)
        and tuple(boundary) == expected_boundary_fields
        and all(value is False for value in boundary.values())
        and actual_counts == expected_zero_counts
    )


def _control_input_is_opaque(phase2_module: Any, control_input: Mapping[str, Any]) -> bool:
    fields = tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
    if fields != ("model_output_permission_gate_control_requests",):
        return False
    requests = control_input.get(fields[0])
    if not isinstance(requests, list) or len(requests) != P2_CONTROL_REQUEST_COUNT:
        return False
    input_fields = tuple(getattr(phase2_module, "INPUT_FIELDS", ()))
    for scenario, request in zip(P2_CONTROL_SCENARIOS, requests):
        if not isinstance(request, Mapping) or set(request) != set(input_fields):
            return False
        if request.get("control_scenario") != scenario:
            return False
        for field, value in request.items():
            if field == "control_scenario":
                continue
            if value is None:
                if field not in {"internal_evidence_ref", "evidence_gap_ref"}:
                    return False
                continue
            if not (
                _is_control_reference(value)
                or (isinstance(value, str) and value.startswith("CONTROL_"))
            ):
                return False
    return True


def _projection_record(
    result: Mapping[str, Any], prefix: str, index: int
) -> Optional[Mapping[str, Any]]:
    values = result.get(f"{prefix}_control_projections")
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    return value if isinstance(value, Mapping) else None


def _failure_for_projection(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    answer: Mapping[str, Any],
    defense: Mapping[str, Any],
    source: Mapping[str, Any],
    permission: Mapping[str, Any],
) -> Optional[str]:
    if not all(
        _is_control_reference(answer.get(field))
        for field in (
            "rag_answer_structure_ref",
            "prompt_version_ref",
            "query_ref",
            "index_version_ref",
            "model_version_ref",
            "selected_evidence_ref",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"
    if not all(
        _is_control_reference(defense.get(field))
        for field in (
            "document_evidence_ref",
            "document_instruction_candidate_ref",
            "ids_rule_ref",
        )
    ):
        return "NON_OPAQUE_DOCUMENT_CONTROL_REFERENCE"
    if defense.get("document_instruction_evidence_state") != (
        "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
    ):
        return "DOCUMENT_INSTRUCTION_BECAME_EXECUTABLE"
    if defense.get("ids_rule_precedence_state") != "CONTROL_IDS_RULES_PREVAIL":
        return "DOCUMENT_INSTRUCTION_CAN_OVERRIDE_IDS_RULE"
    if defense.get("injection_defense_state") != (
        "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
    ):
        return "UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
    if source.get("source_type_separation_state") != (
        "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
    ):
        return "SOURCE_TYPE_SEPARATION_BREACH"
    if source.get("external_augmentation_display_label") != (
        "external_augmentation_opinion"
    ):
        return "EXTERNAL_AUGMENTATION_DISPLAY_DRIFT"
    if source.get("display_does_not_close_evidence_gap_state") != (
        "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP"
    ):
        return "EXTERNAL_AUGMENTATION_CLOSED_EVIDENCE_GAP"

    internal_evidence_present = source.get("internal_evidence_ref") is not None
    evidence_gap_present = source.get("evidence_gap_ref") is not None
    if evidence_gap_present and internal_evidence_present:
        return "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE"
    if internal_evidence_present != definition["expected_internal_evidence_present"]:
        return "INTERNAL_EVIDENCE_SEMANTIC_DRIFT"
    if evidence_gap_present != definition["expected_evidence_gap_present"]:
        return "EVIDENCE_GAP_SEMANTIC_DRIFT"
    if evidence_gap_present and not _is_control_reference(source.get("evidence_gap_ref")):
        return "NON_OPAQUE_EVIDENCE_GAP_REFERENCE"
    if internal_evidence_present and not _is_control_reference(
        source.get("internal_evidence_ref")
    ):
        return "NON_OPAQUE_INTERNAL_EVIDENCE_REFERENCE"

    output_category = str(permission.get("output_category", "")).removeprefix(
        "CONTROL_OUTPUT_CATEGORY_"
    ).lower()
    if output_category != definition["expected_output_category"]:
        return "OUTPUT_CATEGORY_DRIFT"
    if permission.get("final_conclusion_state") != (
        "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
    ):
        return definition.get(
            "auto_finalization_failure_state", "AUTOMATIC_FINAL_CONCLUSION_ALLOWED"
        )
    if permission.get("automatic_publication_state") != (
        "CONTROL_AUTOMATIC_PUBLICATION_DISABLED"
    ):
        return "AUTOMATIC_PUBLICATION_ENABLED"
    if permission.get("business_use_state") != (
        "CONTROL_BUSINESS_USE_REQUIRES_WHITEBOX_OWNER"
    ):
        return "BUSINESS_WHITEBOX_BOUNDARY_BREACH"
    if output_category in HUMAN_CONFIRMATION_OUTPUT_CATEGORIES:
        if permission.get("output_permission_state") != (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ):
            return "HIGH_RISK_OUTPUT_PERMISSION_BYPASS"
        if permission.get("human_confirmation_state") != (
            "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED"
        ):
            return "HIGH_RISK_HUMAN_CONFIRMATION_BYPASS"
    elif permission.get("human_confirmation_state") != (
        "CONTROL_HUMAN_CONFIRMATION_NOT_EXECUTED"
    ):
        return "NON_HIGH_RISK_HUMAN_CONFIRMATION_STATE_DRIFT"
    if output_category == "production_writeback" and permission.get(
        "production_writeback_state"
    ) != "CONTROL_PRODUCTION_WRITEBACK_REQUIRES_FUTURE_AUTHORIZATION":
        return "PRODUCTION_WRITEBACK_BOUNDARY_BREACH"
    return None


def _scenario_record(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    answer: Mapping[str, Any],
    defense: Mapping[str, Any],
    source: Mapping[str, Any],
    permission: Mapping[str, Any],
) -> dict[str, Any]:
    output_category = str(permission["output_category"]).removeprefix(
        "CONTROL_OUTPUT_CATEGORY_"
    ).lower()
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": request["control_scenario"],
        "rag_answer_structure_ref": answer["rag_answer_structure_ref"],
        "prompt_version_ref": answer["prompt_version_ref"],
        "query_ref": answer["query_ref"],
        "index_version_ref": answer["index_version_ref"],
        "model_version_ref": answer["model_version_ref"],
        "selected_evidence_ref": answer["selected_evidence_ref"],
        "document_evidence_ref": defense["document_evidence_ref"],
        "document_instruction_candidate_ref": defense[
            "document_instruction_candidate_ref"
        ],
        "ids_rule_ref": defense["ids_rule_ref"],
        "document_instruction_evidence_state": defense[
            "document_instruction_evidence_state"
        ],
        "ids_rule_precedence_state": defense["ids_rule_precedence_state"],
        "injection_defense_state": defense["injection_defense_state"],
        "source_type_separation_state": source["source_type_separation_state"],
        "internal_evidence_ref": source["internal_evidence_ref"],
        "evidence_gap_ref": source["evidence_gap_ref"],
        "internal_evidence_present": source["internal_evidence_ref"] is not None,
        "evidence_gap_present": source["evidence_gap_ref"] is not None,
        "external_public_reference_ref": source["external_public_reference_ref"],
        "model_reasoning_ref": source["model_reasoning_ref"],
        "external_augmentation_ref": source["external_augmentation_ref"],
        "external_augmentation_display_label": source[
            "external_augmentation_display_label"
        ],
        "output_category": output_category,
        "output_permission_state": permission["output_permission_state"],
        "human_confirmation_state": permission["human_confirmation_state"],
        "final_conclusion_state": permission["final_conclusion_state"],
        "automatic_final_conclusion_allowed": False,
        "business_line_whitebox_human_approval_recorded": False,
        "actual_model_call_performed": False,
        "actual_answer_publication_performed": False,
        "actual_production_writeback_performed": False,
        "expectation_met": True,
    }


def _human_handling(
    definition: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    output_category = scenario["output_category"]
    return {
        "scenario_id": scenario["scenario_id"],
        "output_category": output_category,
        "business_line_whitebox_handling_code": definition[
            "business_line_whitebox_handling_code"
        ],
        "high_risk_human_confirmation_required": (
            output_category in HUMAN_CONFIRMATION_OUTPUT_CATEGORIES
        ),
        "human_approval_recorded": False,
        "final_conclusion_state": scenario["final_conclusion_state"],
    }


def build_model_output_permission_gate_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """机械重放固定 P2 控制投影并生成纯内存 P3 场景报告。"""

    try:
        phase2_module = _load_phase2_module()
        control_input = phase2_module.build_control_input()
        executor = (
            phase2_executor
            if phase2_executor is not None
            else phase2_module.execute_model_output_permission_gate_control_slice
        )
        phase2_result = executor(control_input)
    except Exception:
        return _base_report(False, "PHASE2_CONTROL_REPLAY_UNAVAILABLE")

    if not isinstance(phase2_result, Mapping) or not _phase2_shape_is_preserved(
        phase2_module, phase2_result
    ):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if not _phase2_runtime_is_closed(phase2_module, phase2_result):
        return _base_report(False, "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH")
    if not _control_input_is_opaque(phase2_module, control_input):
        return _base_report(False, "PHASE2_CONTROL_INPUT_NOT_OPAQUE")

    requests = control_input[phase2_module.CONTROL_FIELDS[0]]
    scenarios: list[dict[str, Any]] = []
    human_handlings: list[dict[str, Any]] = []
    for index, definition in enumerate(SCENARIO_DEFINITIONS):
        request = requests[index]
        answer = _projection_record(
            phase2_result, "answer_contract_and_reproducibility", index
        )
        defense = _projection_record(
            phase2_result,
            "document_evidence_and_output_permission_defense",
            index,
        )
        source = _projection_record(
            phase2_result,
            "source_semantics_and_external_augmentation_display",
            index,
        )
        permission = _projection_record(
            phase2_result, "output_permission_and_whitebox_gate", index
        )
        if any(value is None for value in (answer, defense, source, permission)):
            return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
        failure_state = _failure_for_projection(
            definition, request, answer, defense, source, permission
        )
        if failure_state is not None:
            return _base_report(False, failure_state)
        scenario = _scenario_record(
            definition, request, answer, defense, source, permission
        )
        scenarios.append(scenario)
        human_handlings.append(_human_handling(definition, scenario))

    control_views = {
        name: [{field: scenario[field] for field in fields} for scenario in scenarios]
        for name, fields in CONTROL_VIEW_FIELDS.items()
    }
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
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "scenario_results": scenarios,
            "control_view_count": len(CONTROL_VIEW_FIELDS),
            "control_views": control_views,
            "human_handling_count": len(human_handlings),
            "human_handlings": human_handlings,
        }
    )
    return deepcopy(report)
