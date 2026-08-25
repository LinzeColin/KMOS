"""Stage100 P3 无内部依据策略的纯内存异常场景控制报告。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = "ids.stage100.no_internal_evidence_strategy.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_NO_INTERNAL_EVIDENCE_STRATEGY_SCENARIOS"
CURRENT_GATE = "IDS-STAGE100-P3-GATE"
NEXT_GATE = "IDS-STAGE100-P4-GATE"
PASS_RESULT = "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_CONTROL_PREFIX = ":control:stage100-p2:"
P2_CONTROL_REQUEST_COUNT = 6
P2_INPUT_FIELD_COUNT = 21
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 38
P2_PROJECTION_FIELD_COUNT_TOTAL = 228

P2_CONTROL_SCENARIOS = (
    "internal_evidence_with_external_augmentation_opinion_reference_only",
    "evidence_gap_with_external_augmentation_opinion_reference_only",
    "retrieval_document_instruction_rejected_reference_only",
    "high_risk_engineering_advice_confirmation_required_reference_only",
    "contract_commitment_confirmation_required_reference_only",
    "production_writeback_confirmation_required_reference_only",
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
    "no_internal_evidence_policy_evaluated",
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
    "stage100_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_query_record_count",
    "actual_index_version_record_count",
    "actual_prompt_version_record_count",
    "actual_model_version_record_count",
    "actual_selected_evidence_record_count",
    "actual_retrieval_execution_count",
    "actual_prompt_execution_count",
    "actual_model_reasoning_count",
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
    "model_version_ref",
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
    "output_classification",
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

CONTROL_VIEW_NAMES = (
    "retrieval_document_precedence_view",
    "no_internal_evidence_declaration_view",
    "source_type_separation_view",
    "output_permission_view",
    "future_candidate_and_actual_execution_view",
)

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "internal_evidence_external_augmentation_source_types_preserved_control",
        "scenario_category": "SOURCE_TYPE_SEPARATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "output_classification": "ordinary_decision_support",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_SOURCE_TYPE_SEPARATION",
    },
    {
        "scenario_id": "evidence_gap_cannot_masquerade_as_internal_experience_control",
        "scenario_category": "NO_INTERNAL_EVIDENCE_DECLARATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "output_classification": "evidence_gap_declaration",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_EVIDENCE_GAP_DECLARATION",
    },
    {
        "scenario_id": "retrieval_document_cannot_override_ids_rule_control",
        "scenario_category": "PROMPT_INJECTION_REJECTION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "output_classification": "prompt_injection_review",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_PROMPT_INJECTION_REJECTION",
    },
    {
        "scenario_id": "high_risk_engineering_advice_requires_whitebox_confirmation_control",
        "scenario_category": "HIGH_RISK_ENGINEERING_ADVICE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "output_classification": "high_risk_engineering_advice",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_HIGH_RISK_ENGINEERING_ADVICE",
    },
    {
        "scenario_id": "contract_commitment_requires_whitebox_confirmation_control",
        "scenario_category": "CONTRACT_COMMITMENT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "output_classification": "contract_commitment",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_CONTRACT_COMMITMENT",
    },
    {
        "scenario_id": "production_writeback_requires_whitebox_confirmation_control",
        "scenario_category": "PRODUCTION_WRITEBACK_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[5],
        "output_classification": "production_writeback",
        "human_handling_code": "BUSINESS_LINE_WHITEBOX_CONFIRM_PRODUCTION_WRITEBACK",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage100_no_internal_evidence_strategy_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage100_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage100 P2 control slice")
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
        "next_gate": NEXT_GATE,
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
        "control_view_count": len(CONTROL_VIEW_NAMES),
        "control_views": {name: [] for name in CONTROL_VIEW_NAMES},
        "human_handling_count": 0,
        "human_handlings": [],
        "future_model_reasoning_candidate_count": 0,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "scenario_results": [],
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
    }


def _phase2_failure_state(
    phase2_module: Any,
    control_input: Mapping[str, Any],
    phase2_output: Mapping[str, Any],
) -> Optional[str]:
    expected_input = phase2_module.build_control_input()
    if dict(control_input) != expected_input:
        return "PHASE2_CONTROL_INPUT_MISMATCH"
    if phase2_output.get("input_accepted") is not True:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if phase2_output.get("execution_state") != (
        "PASS_IN_MEMORY_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED"
    ):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if phase2_output.get("failure_state") is not None:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if phase2_output.get("persistent_record_created") is not False:
        return "PERSISTENT_RECORD_CREATED"
    runtime_boundary = phase2_output.get("runtime_boundary")
    if not isinstance(runtime_boundary, Mapping) or any(runtime_boundary.values()):
        return "PHASE2_RUNTIME_BOUNDARY_BREACH"
    if any(
        value != 0
        for field, value in phase2_output.items()
        if field.startswith("actual_") and field.endswith("_count")
    ):
        return "PHASE2_RUNTIME_BOUNDARY_BREACH"
    requests = control_input.get(phase2_module.CONTROL_FIELDS[0])
    if not isinstance(requests, list) or len(requests) != P2_CONTROL_REQUEST_COUNT:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if [request.get("control_scenario") for request in requests] != list(
        P2_CONTROL_SCENARIOS
    ):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if phase2_output.get("control_input_count") != P2_CONTROL_REQUEST_COUNT:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if phase2_output.get("control_projection_group_count") != P2_PROJECTION_GROUP_COUNT:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if (
        phase2_output.get("control_projection_field_total_per_request")
        != P2_PROJECTION_FIELD_COUNT_PER_REQUEST
    ):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if (
        phase2_output.get("control_projection_field_total")
        != P2_PROJECTION_FIELD_COUNT_TOTAL
    ):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    for prefix, fields in phase2_module.PROJECTION_FIELDS:
        projections = phase2_output.get(f"{prefix}_control_projections")
        if not isinstance(projections, list) or len(projections) != P2_CONTROL_REQUEST_COUNT:
            return "PHASE2_CONTROL_SHAPE_MISMATCH"
        if phase2_output.get(f"{prefix}_control_projection_count") != P2_CONTROL_REQUEST_COUNT:
            return "PHASE2_CONTROL_SHAPE_MISMATCH"
        if any(not isinstance(item, Mapping) or set(item) != set(fields) for item in projections):
            return "PHASE2_CONTROL_SHAPE_MISMATCH"
    source_projections = phase2_output.get(
        "source_type_and_external_augmentation_opinion_display_control_projections"
    )
    permission_projections = phase2_output.get(
        "prompt_injection_and_output_permission_control_projections"
    )
    if not isinstance(source_projections, list) or not isinstance(permission_projections, list):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    injection_index = P2_CONTROL_SCENARIOS.index(
        "retrieval_document_instruction_rejected_reference_only"
    )
    injection = permission_projections[injection_index]
    if injection.get("retrieval_document_instruction_precedence_state") != (
        "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
    ):
        return "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE"
    if injection.get("prompt_injection_defense_state") != (
        "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
    ):
        return "PROMPT_INJECTION_DEFENSE_MISSING"
    if injection.get("output_permission_state") != (
        "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW"
    ):
        return "PROMPT_INJECTION_OUTPUT_WITHHELD_STATE_MISSING"
    gap_index = P2_CONTROL_SCENARIOS.index(
        "evidence_gap_with_external_augmentation_opinion_reference_only"
    )
    gap_request = requests[gap_index]
    gap_projection = source_projections[gap_index]
    if gap_request.get("internal_evidence_ref") is not None or not _control_ref(
        gap_request.get("evidence_gap_ref")
    ):
        return "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE"
    if gap_projection.get("external_augmentation_does_not_close_evidence_gap_state") != (
        "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP"
    ):
        return "EXTERNAL_AUGMENTATION_USED_TO_ERASE_EVIDENCE_GAP"
    if gap_projection.get("display_preserves_underlying_source_types_state") != (
        "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
    ):
        return "SOURCE_TYPE_SEPARATION_BREACH"
    for scenario in (
        "high_risk_engineering_advice_confirmation_required_reference_only",
        "contract_commitment_confirmation_required_reference_only",
        "production_writeback_confirmation_required_reference_only",
    ):
        projection = permission_projections[P2_CONTROL_SCENARIOS.index(scenario)]
        if projection.get("output_permission_state") != (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ):
            return "HIGH_RISK_OUTPUT_AUTO_FINALIZED"
        if projection.get("final_conclusion_state") != (
            "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ):
            return "HIGH_RISK_FINAL_CONCLUSION_PUBLISHED"
    for request in requests:
        if any(
            not _control_ref(value)
            for field, value in request.items()
            if field.endswith("_ref") and value is not None
        ):
            return "CONTROL_REFERENCE_NOT_OPAQUE"
    return None


def _scenario_result(
    definition: Mapping[str, str],
    request: Mapping[str, Any],
    source_projection: Mapping[str, Any],
    permission_projection: Mapping[str, Any],
) -> dict[str, Any]:
    internal_evidence_present = request["internal_evidence_ref"] is not None
    evidence_gap_present = request["evidence_gap_ref"] is not None
    output_permission_state = permission_projection["output_permission_state"]
    result = {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "query_ref": request["query_ref"],
        "index_version_ref": request["index_version_ref"],
        "prompt_version_ref": request["prompt_version_ref"],
        "model_version_ref": request["model_version_ref"],
        "selected_evidence_ref": request["selected_evidence_ref"],
        "retrieval_document_instruction_precedence_state": permission_projection[
            "retrieval_document_instruction_precedence_state"
        ],
        "prompt_injection_defense_state": permission_projection[
            "prompt_injection_defense_state"
        ],
        "source_type_separation_state": source_projection[
            "source_type_separation_state"
        ],
        "internal_evidence_ref": request["internal_evidence_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "internal_evidence_present": internal_evidence_present,
        "evidence_gap_present": evidence_gap_present,
        "external_public_reference_ref": request["external_public_reference_ref"],
        "model_reasoning_ref": request["model_reasoning_ref"],
        "external_augmentation_ref": request["external_augmentation_ref"],
        "external_augmentation_display_label": source_projection[
            "external_augmentation_display_label"
        ],
        "output_classification": definition["output_classification"],
        "output_permission_state": output_permission_state,
        "final_conclusion_state": permission_projection["final_conclusion_state"],
        "human_handling_required": True,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_final_conclusion_allowed": False,
        "future_model_reasoning_candidate_declared": _control_ref(
            request["model_reasoning_ref"]
        ),
        "actual_model_call_performed": False,
        "actual_answer_publication_performed": False,
        "expectation_met": False,
    }
    result["expectation_met"] = (
        result["phase2_control_scenario"] == request["control_scenario"]
        and _control_ref(result["query_ref"])
        and _control_ref(result["index_version_ref"])
        and _control_ref(result["prompt_version_ref"])
        and _control_ref(result["model_version_ref"])
        and _control_ref(result["selected_evidence_ref"])
        and result["retrieval_document_instruction_precedence_state"]
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and result["source_type_separation_state"]
        == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        and result["external_augmentation_display_label"]
        == "external_augmentation_opinion"
        and result["final_conclusion_state"]
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        and result["human_handling_required"]
        and result["future_model_reasoning_candidate_declared"]
        and not result["business_line_whitebox_human_approval_recorded"]
        and not result["automatic_final_conclusion_allowed"]
        and not result["actual_model_call_performed"]
        and not result["actual_answer_publication_performed"]
    )
    return result


def _control_views(scenarios: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    def select(*fields: str) -> list[dict[str, Any]]:
        return [
            {"scenario_id": item["scenario_id"], **{field: item[field] for field in fields}}
            for item in scenarios
        ]

    return {
        "retrieval_document_precedence_view": select(
            "retrieval_document_instruction_precedence_state",
            "prompt_injection_defense_state",
            "final_conclusion_state",
        ),
        "no_internal_evidence_declaration_view": select(
            "internal_evidence_present",
            "evidence_gap_present",
            "internal_evidence_ref",
            "evidence_gap_ref",
        ),
        "source_type_separation_view": select(
            "source_type_separation_state",
            "external_augmentation_display_label",
            "external_public_reference_ref",
            "model_reasoning_ref",
        ),
        "output_permission_view": select(
            "output_classification",
            "output_permission_state",
            "human_handling_required",
            "automatic_final_conclusion_allowed",
        ),
        "future_candidate_and_actual_execution_view": select(
            "future_model_reasoning_candidate_declared",
            "actual_model_call_performed",
            "actual_answer_publication_performed",
        ),
    }


def _human_handlings(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    definition_by_id = {
        definition["scenario_id"]: definition for definition in SCENARIO_DEFINITIONS
    }
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "output_classification": scenario["output_classification"],
            "human_handling_code": definition_by_id[scenario["scenario_id"]][
                "human_handling_code"
            ],
            "business_line_whitebox_review_required": True,
            "business_line_whitebox_human_approval_recorded": False,
            "automatic_final_conclusion_allowed": False,
            "actual_human_confirmation_performed": False,
            "actual_final_conclusion_published": False,
        }
        for scenario in scenarios
    ]


def build_no_internal_evidence_strategy_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """重放唯一允许的 P2 控制投影，生成不可持久化 P3 场景报告。"""

    phase2_module = _load_phase2_module()
    control_input = phase2_module.build_control_input()
    executor = phase2_executor or phase2_module.execute_no_internal_evidence_strategy_control_slice
    phase2_output = executor(control_input)
    if not isinstance(phase2_output, Mapping):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    failure_state = _phase2_failure_state(phase2_module, control_input, phase2_output)
    if failure_state is not None:
        return _base_report(False, failure_state)

    requests = control_input[phase2_module.CONTROL_FIELDS[0]]
    source_projections = phase2_output[
        "source_type_and_external_augmentation_opinion_display_control_projections"
    ]
    permission_projections = phase2_output[
        "prompt_injection_and_output_permission_control_projections"
    ]
    requests_by_scenario = {
        request["control_scenario"]: request for request in requests
    }
    source_by_scenario = dict(zip(P2_CONTROL_SCENARIOS, source_projections))
    permission_by_scenario = dict(zip(P2_CONTROL_SCENARIOS, permission_projections))
    scenarios = [
        _scenario_result(
            definition,
            requests_by_scenario[definition["phase2_control_scenario"]],
            source_by_scenario[definition["phase2_control_scenario"]],
            permission_by_scenario[definition["phase2_control_scenario"]],
        )
        for definition in SCENARIO_DEFINITIONS
    ]
    if any(set(scenario) != set(SCENARIO_FIELDS) or not scenario["expectation_met"] for scenario in scenarios):
        return _base_report(False, "CONTROLLED_SCENARIO_EXPECTATION_MISMATCH")
    human_handlings = _human_handlings(scenarios)
    if len(human_handlings) != len(scenarios):
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
            "phase2_projection_field_count_per_request": P2_PROJECTION_FIELD_COUNT_PER_REQUEST,
            "phase2_projection_field_count_total": P2_PROJECTION_FIELD_COUNT_TOTAL,
            "scenario_count": len(scenarios),
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "control_views": _control_views(scenarios),
            "human_handling_count": len(human_handlings),
            "human_handlings": human_handlings,
            "future_model_reasoning_candidate_count": sum(
                item["future_model_reasoning_candidate_declared"] for item in scenarios
            ),
            "scenario_results": scenarios,
        }
    )
    return report
