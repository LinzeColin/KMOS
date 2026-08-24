"""Stage097 P3 的纯内存回答合同异常场景验证。

模块只重放 Stage097 P2 固定、非业务、reference-only 控制投影，用于验证
检索文档不能覆盖 IDS 规则、evidence gap 不会伪装为内部经验，以及高风险工程
建议、合同承诺和生产写回不会自动进入最终结论。它不读取真实资料、提示词、
检索结果、模型配置、evidence、回答或报告，不调用模型，不消费模型 Token，
也不连接或写入任何持久化系统。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage097.answer_contract.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_ANSWER_CONTRACT_EXCEPTION_SCENARIOS"
PASS_RESULT = "PASS_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CURRENT_GATE = "IDS-STAGE097-P3-GATE"
NEXT_GATE = "IDS-STAGE097-P4-GATE"
P2_EXECUTION_STATE = "PASS_IN_MEMORY_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage097-p2:"
P2_CONTROL_SCENARIOS = (
    "internal_evidence_with_external_augmentation_reference_only",
    "evidence_gap_with_external_augmentation_reference_only",
    "retrieval_document_instruction_rejected_reference_only",
    "high_risk_engineering_advice_confirmation_required_reference_only",
    "contract_commitment_confirmation_required_reference_only",
    "production_writeback_confirmation_required_reference_only",
)
P2_PROJECTION_SPECS = (
    ("answer_contract_binding", "ANSWER_CONTRACT_BINDING_FIELDS"),
    (
        "version_and_selected_evidence_record",
        "VERSION_AND_SELECTED_EVIDENCE_RECORD_FIELDS",
    ),
    (
        "source_type_and_external_augmentation_display",
        "SOURCE_TYPE_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS",
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
    "citation_structure_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "external_augmentation_display_ref",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "output_permission_state",
    "final_conclusion_state",
    "source_type_separation_state",
    "external_augmentation_display_state",
    "display_does_not_replace_source_type_state",
    "internal_evidence_present",
    "evidence_gap_present",
    "business_line_whitebox_human_approval_recorded",
    "human_handling_required",
    "expectation_met",
)
SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "external_augmentation_preserves_source_type_control",
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
        "scenario_id": "evidence_gap_cannot_masquerade_as_internal_experience_control",
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
        "scenario_id": "retrieval_document_cannot_override_ids_rule_control",
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
        "scenario_id": "high_risk_engineering_advice_requires_whitebox_confirmation_control",
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
    },
    {
        "scenario_id": "contract_commitment_requires_whitebox_confirmation_control",
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
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_CONTRACT_COMMITMENT"
        ),
    },
    {
        "scenario_id": "production_writeback_requires_whitebox_confirmation_control",
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
        "human_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_PRODUCTION_WRITEBACK"
        ),
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage097_answer_contract_control_slice.py")
    spec = importlib.util.spec_from_file_location("stage097_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage097 P2 control slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _control_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _phase2_projection_records(
    result: Mapping[str, Any], scenario: str
) -> dict[str, Mapping[str, Any]] | None:
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
        getattr(phase2_module, "SCHEMA_VERSION", None)
        != "ids.stage097.answer_contract.phase2.v1"
        or getattr(phase2_module, "RECORD_KIND", None)
        != "CONTROL_ONLY_IN_MEMORY_ANSWER_CONTRACT"
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
        != ("answer_contract_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != 20
        or result.get("schema_version") != "ids.stage097.answer_contract.phase2.v1"
        or result.get("record_kind") != "CONTROL_ONLY_IN_MEMORY_ANSWER_CONTRACT"
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
            or any(not isinstance(item, Mapping) or set(item) != set(fields) for item in projections)
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
        binding = records["answer_contract_binding"]
        version = records["version_and_selected_evidence_record"]
        source = records["source_type_and_external_augmentation_display"]
        permission = records["prompt_injection_and_output_permission"]
        if not all(
            _control_ref(binding.get(field))
            for field in (
                "stage097_phase1_answer_contract_ref",
                "stage096_review_control_ref",
                "answer_structure_ref",
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_version_ref",
                "selected_evidence_ref",
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
                "external_augmentation_display_ref",
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
            for field in (
                "citation_structure_ref",
                "output_classification_ref",
                "human_confirmation_gate_ref",
            )
        ):
            return False
    return True


def _phase2_semantic_failure(result: Mapping[str, Any]) -> str | None:
    records_by_scenario = {
        scenario: _phase2_projection_records(result, scenario)
        for scenario in P2_CONTROL_SCENARIOS
    }
    if any(records is None for records in records_by_scenario.values()):
        return "PHASE2_CONTROL_OUTPUT_INVALID"

    source = records_by_scenario[P2_CONTROL_SCENARIOS[0]][
        "source_type_and_external_augmentation_display"
    ]
    if (
        source.get("internal_evidence_source_type") != "internal_evidence"
        or source.get("external_public_reference_source_type")
        != "external_public_reference"
        or source.get("model_reasoning_source_type") != "model_reasoning"
        or source.get("evidence_gap_source_type") != "evidence_gap"
        or source.get("external_augmentation_display_state")
        != "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        or source.get("display_does_not_replace_source_type_state")
        != "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
    ):
        return "EXTERNAL_AUGMENTATION_SOURCE_TYPE_LOST"

    evidence_gap_source = records_by_scenario[P2_CONTROL_SCENARIOS[1]][
        "source_type_and_external_augmentation_display"
    ]
    if (
        evidence_gap_source.get("internal_evidence_ref") is not None
        or not _control_ref(evidence_gap_source.get("evidence_gap_ref"))
        or evidence_gap_source.get("evidence_gap_source_type") != "evidence_gap"
    ):
        return "EVIDENCE_GAP_PRESENTED_AS_INTERNAL_EXPERIENCE"

    injection = records_by_scenario[P2_CONTROL_SCENARIOS[2]][
        "prompt_injection_and_output_permission"
    ]
    if (
        injection.get("retrieval_document_instruction_precedence_state")
        != "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        or injection.get("prompt_injection_defense_state")
        != "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        or injection.get("output_permission_state")
        != "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW"
    ):
        return "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE"

    for scenario, failure in (
        (
            P2_CONTROL_SCENARIOS[3],
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
        ),
        (P2_CONTROL_SCENARIOS[4], "CONTRACT_COMMITMENT_AUTO_FINALIZED"),
        (P2_CONTROL_SCENARIOS[5], "PRODUCTION_WRITEBACK_AUTO_FINALIZED"),
    ):
        permission = records_by_scenario[scenario][
            "prompt_injection_and_output_permission"
        ]
        if (
            permission.get("output_permission_state")
            != "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
            or permission.get("final_conclusion_state")
            != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ):
            return failure
    return None


def _scenario_expectation_met(
    definition: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> bool:
    binding = records["answer_contract_binding"]
    version = records["version_and_selected_evidence_record"]
    source = records["source_type_and_external_augmentation_display"]
    permission = records["prompt_injection_and_output_permission"]
    internal_evidence_present = source.get("internal_evidence_ref") is not None
    evidence_gap_present = source.get("evidence_gap_ref") is not None
    return (
        all(
            _control_ref(binding.get(field))
            for field in (
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_version_ref",
                "selected_evidence_ref",
            )
        )
        and all(
            _control_ref(version.get(field))
            for field in (
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_version_ref",
                "selected_evidence_ref",
            )
        )
        and all(
            _control_ref(source.get(field))
            for field in (
                "external_public_reference_ref",
                "model_reasoning_ref",
                "external_augmentation_display_ref",
            )
        )
        and internal_evidence_present
        == definition["expected_internal_evidence_present"]
        and evidence_gap_present == definition["expected_evidence_gap_present"]
        and source.get("source_type_separation_state")
        == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        and source.get("external_augmentation_display_state")
        == "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        and source.get("display_does_not_replace_source_type_state")
        == "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
        and _control_ref(permission.get("citation_structure_ref"))
        and _control_ref(permission.get("output_classification_ref"))
        and _control_ref(permission.get("human_confirmation_gate_ref"))
        and permission.get("retrieval_document_instruction_precedence_state")
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and permission.get("prompt_injection_defense_state")
        == definition["expected_prompt_injection_defense_state"]
        and permission.get("output_permission_state")
        == definition["expected_output_permission_state"]
        and permission.get("final_conclusion_state")
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
    )


def _build_scenario(
    definition: Mapping[str, Any], phase2_result: Mapping[str, Any]
) -> dict[str, Any]:
    records = _phase2_projection_records(
        phase2_result, definition["phase2_control_scenario"]
    )
    if records is None:
        raise ValueError("Phase2 control records are unavailable")
    binding = records["answer_contract_binding"]
    source = records["source_type_and_external_augmentation_display"]
    permission = records["prompt_injection_and_output_permission"]
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "query_ref": binding["query_ref"],
        "index_version_ref": binding["index_version_ref"],
        "prompt_version_ref": binding["prompt_version_ref"],
        "model_version_ref": binding["model_version_ref"],
        "selected_evidence_ref": binding["selected_evidence_ref"],
        "internal_evidence_ref": source["internal_evidence_ref"],
        "external_public_reference_ref": source["external_public_reference_ref"],
        "model_reasoning_ref": source["model_reasoning_ref"],
        "evidence_gap_ref": source["evidence_gap_ref"],
        "citation_structure_ref": permission["citation_structure_ref"],
        "output_classification_ref": permission["output_classification_ref"],
        "human_confirmation_gate_ref": permission["human_confirmation_gate_ref"],
        "external_augmentation_display_ref": source[
            "external_augmentation_display_ref"
        ],
        "retrieval_document_instruction_precedence_state": permission[
            "retrieval_document_instruction_precedence_state"
        ],
        "prompt_injection_defense_state": permission[
            "prompt_injection_defense_state"
        ],
        "output_permission_state": permission["output_permission_state"],
        "final_conclusion_state": permission["final_conclusion_state"],
        "source_type_separation_state": source["source_type_separation_state"],
        "external_augmentation_display_state": source[
            "external_augmentation_display_state"
        ],
        "display_does_not_replace_source_type_state": source[
            "display_does_not_replace_source_type_state"
        ],
        "internal_evidence_present": source["internal_evidence_ref"] is not None,
        "evidence_gap_present": source["evidence_gap_ref"] is not None,
        "business_line_whitebox_human_approval_recorded": False,
        "human_handling_required": True,
        "expectation_met": _scenario_expectation_met(definition, records),
    }


def _build_control_views(scenarios: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "answer_contract_binding_control_view": [
            {
                key: scenario[key]
                for key in (
                    "scenario_id",
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                )
            }
            for scenario in scenarios
        ],
        "version_and_selected_evidence_control_view": [
            {
                key: scenario[key]
                for key in (
                    "scenario_id",
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                )
            }
            for scenario in scenarios
        ],
        "source_type_and_external_augmentation_control_view": [
            {
                key: scenario[key]
                for key in (
                    "scenario_id",
                    "internal_evidence_ref",
                    "external_public_reference_ref",
                    "model_reasoning_ref",
                    "evidence_gap_ref",
                    "external_augmentation_display_ref",
                    "source_type_separation_state",
                    "external_augmentation_display_state",
                    "display_does_not_replace_source_type_state",
                )
            }
            for scenario in scenarios
        ],
        "prompt_injection_control_view": [
            {
                key: scenario[key]
                for key in (
                    "scenario_id",
                    "retrieval_document_instruction_precedence_state",
                    "prompt_injection_defense_state",
                )
            }
            for scenario in scenarios
        ],
        "output_permission_control_view": [
            {
                key: scenario[key]
                for key in (
                    "scenario_id",
                    "output_classification_ref",
                    "human_confirmation_gate_ref",
                    "output_permission_state",
                    "final_conclusion_state",
                    "human_handling_required",
                )
            }
            for scenario in scenarios
        ],
    }


def _build_human_handlings() -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": definition["scenario_id"],
            "handling_code": definition["human_handling_code"],
            "business_line_whitebox_review_required": True,
            "business_line_whitebox_human_approval_recorded": False,
            "automatic_final_conclusion_allowed": False,
            "actual_human_confirmation_performed": False,
        }
        for definition in SCENARIO_DEFINITIONS
    ]


def _failure_report(failure_state: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": False,
        "result": FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": CURRENT_GATE,
        "next_gate": CURRENT_GATE,
        "phase2_control_shape_preserved": False,
        "phase2_side_effect_free": False,
        "control_references_opaque": False,
        "phase2_control_request_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_field_check_count": 0,
        "scenario_results": [],
        "scenario_count": 0,
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": 0,
        "control_views": {},
        "control_view_count": 0,
        "human_handlings": [],
        "human_handling_count": 0,
        "second_authoritative_source_created": False,
        "actual_prompt_injection_defense_execution_count": 0,
        "actual_source_type_binding_count": 0,
        "actual_output_classification_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_answer_publication_count": 0,
        "actual_production_writeback_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }


def build_answer_contract_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制投影并验证 Stage097 P3 固定异常场景。"""

    try:
        phase2_module = _load_phase2_module()
        executor = phase2_executor or phase2_module.execute_answer_contract_control_slice
        phase2_result = executor(phase2_module.build_control_input())
    except Exception:
        return _failure_report("PHASE2_CONTROL_OUTPUT_INVALID")
    if not isinstance(phase2_result, Mapping):
        return _failure_report("PHASE2_CONTROL_OUTPUT_INVALID")
    if not _phase2_shape_is_preserved(phase2_module, phase2_result):
        return _failure_report("PHASE2_CONTROL_SHAPE_MISMATCH")
    if not _phase2_runtime_is_closed(phase2_result):
        return _failure_report("PHASE2_RUNTIME_SIGNAL_DETECTED")
    if not _phase2_control_references_are_opaque(phase2_result):
        return _failure_report("CONTROL_REFERENCE_NOT_OPAQUE")
    semantic_failure = _phase2_semantic_failure(phase2_result)
    if semantic_failure is not None:
        return _failure_report(semantic_failure)

    scenarios = [
        _build_scenario(definition, phase2_result)
        for definition in SCENARIO_DEFINITIONS
    ]
    if any(set(scenario) != set(SCENARIO_FIELDS) for scenario in scenarios) or any(
        scenario["expectation_met"] is not True for scenario in scenarios
    ):
        return _failure_report("SCENARIO_EXPECTATION_MISMATCH")
    control_views = _build_control_views(scenarios)
    if len(control_views) != 5 or any(
        len(view) != len(scenarios) for view in control_views.values()
    ):
        return _failure_report("CONTROL_VIEW_SHAPE_MISMATCH")
    human_handlings = _build_human_handlings()
    if len(human_handlings) != len(scenarios):
        return _failure_report("HUMAN_HANDLING_SHAPE_MISMATCH")

    field_check_count = sum(
        len(phase2_result[f"{prefix}_control_projections"])
        * len(getattr(phase2_module, field_constant))
        for prefix, field_constant in P2_PROJECTION_SPECS
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": True,
        "result": PASS_RESULT,
        "failure_state": None,
        "current_gate": CURRENT_GATE,
        "next_gate": NEXT_GATE,
        "phase2_control_shape_preserved": True,
        "phase2_side_effect_free": True,
        "control_references_opaque": True,
        "phase2_control_request_count": len(P2_CONTROL_SCENARIOS),
        "phase2_projection_group_count": len(P2_PROJECTION_SPECS),
        "phase2_field_check_count": field_check_count,
        "scenario_results": scenarios,
        "scenario_count": len(scenarios),
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
        "control_views": control_views,
        "control_view_count": len(control_views),
        "human_handlings": human_handlings,
        "human_handling_count": len(human_handlings),
        "second_authoritative_source_created": False,
        "actual_prompt_injection_defense_execution_count": 0,
        "actual_source_type_binding_count": 0,
        "actual_output_classification_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_answer_publication_count": 0,
        "actual_production_writeback_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }
