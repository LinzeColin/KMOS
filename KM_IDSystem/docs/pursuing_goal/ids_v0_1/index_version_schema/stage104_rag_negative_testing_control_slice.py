"""Stage104 P2：RAG 负向测试的纯内存受控最小切片。

本模块只机械投影冻结控制引用。它不读取资料、文档、Prompt 或回答，
不连接索引、数据库或外部服务，也不选择或调用模型。
"""

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage104.rag_negative_testing.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST"
CONTROL_ADAPTER_VERSION = "stage104-p2-control-slice-v1"
PASS_RESULT = "PASS_IN_MEMORY_RAG_NEGATIVE_TEST_CONTROL_SLICE_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_RAG_NEGATIVE_TEST_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage104-p2:"
CONTROL_FIELDS = ("control_requests",)

NEGATIVE_TEST_CASES = (
    "DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
    "EVIDENCE_GAP_CANNOT_PRESENT_AS_INTERNAL_EXPERIENCE",
    "HIGH_RISK_ENGINEERING_ADVICE_CANNOT_AUTO_FINALIZE",
    "CONTRACTUAL_COMMITMENT_CANNOT_AUTO_FINALIZE",
    "PRODUCTION_WRITEBACK_CANNOT_AUTO_FINALIZE",
)
CONTROL_SCENARIOS = (
    "document_instruction_rule_precedence_reference_only",
    "evidence_gap_truthfulness_reference_only",
    "high_risk_engineering_advice_reference_only",
    "contractual_commitment_reference_only",
    "production_writeback_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "document_instruction_rule_precedence_reference_only": {
        "negative_test_case_id": NEGATIVE_TEST_CASES[0],
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "safe_summary",
    },
    "evidence_gap_truthfulness_reference_only": {
        "negative_test_case_id": NEGATIVE_TEST_CASES[1],
        "include_internal_evidence_ref": False,
        "include_evidence_gap_ref": True,
        "output_category": "draft_recommendation",
    },
    "high_risk_engineering_advice_reference_only": {
        "negative_test_case_id": NEGATIVE_TEST_CASES[2],
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "high_risk_engineering_advice",
    },
    "contractual_commitment_reference_only": {
        "negative_test_case_id": NEGATIVE_TEST_CASES[3],
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "contractual_commitment",
    },
    "production_writeback_reference_only": {
        "negative_test_case_id": NEGATIVE_TEST_CASES[4],
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "production_writeback",
    },
}
HUMAN_CONFIRMATION_OUTPUT_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}

INPUT_FIELDS = (
    "control_scenario",
    "negative_test_case_id",
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "output_category",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "source_type_separation_state",
    "external_augmentation_display_label",
    "output_permission_state",
    "negative_test_execution_state",
)
REPRODUCIBILITY_RECORD_FIELDS = (
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
)
ANSWER_CONTRACT_AND_REPRODUCIBILITY_FIELDS = (
    "control_scenario",
    "negative_test_case_id",
    "stage104_phase1_rag_negative_test_contract_ref",
    "rag_answer_structure_ref",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "answer_structure_section_count",
    "answer_structure_reference_state",
    "prompt_version_reference_state",
    "control_slice_state",
)
DOCUMENT_EVIDENCE_AND_RULE_DEFENSE_FIELDS = (
    "control_scenario",
    "negative_test_case_id",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "document_instruction_cannot_override_ids_rule_state",
    "document_instruction_cannot_relax_output_permission_state",
    "document_instruction_cannot_bypass_human_confirmation_state",
    "actual_document_content_read_performed",
    "actual_document_instruction_processed",
)
SOURCE_SEMANTICS_AND_EXTERNAL_AUGMENTATION_FIELDS = (
    "control_scenario",
    "negative_test_case_id",
    "internal_evidence_ref",
    "evidence_gap_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "external_augmentation_ref",
    "source_type_ref",
    "source_type_separation_state",
    "external_augmentation_display_label",
    "external_augmentation_display_composition_state",
    "evidence_gap_presentation_state",
    "external_augmentation_may_not_replace_internal_evidence",
    "actual_source_type_bound",
    "actual_external_augmentation_displayed",
)
OUTPUT_PERMISSION_AND_WHITEBOX_GATE_FIELDS = (
    "control_scenario",
    "negative_test_case_id",
    "output_category",
    "output_classification_ref",
    "model_output_permission_ref",
    "human_confirmation_gate_ref",
    "output_permission_state",
    "business_line_whitebox_human_confirmation_required",
    "automatic_final_conclusion_allowed",
    "automatic_answer_publication_allowed",
    "automatic_production_writeback_allowed",
    "actual_output_classified",
    "actual_human_confirmation_recorded",
    "actual_final_conclusion_published",
    "actual_production_writeback_performed",
    "negative_test_execution_state",
)
PROJECTION_FIELDS = (
    (
        "answer_contract_and_reproducibility",
        ANSWER_CONTRACT_AND_REPRODUCIBILITY_FIELDS,
    ),
    (
        "document_evidence_and_rule_defense",
        DOCUMENT_EVIDENCE_AND_RULE_DEFENSE_FIELDS,
    ),
    (
        "source_semantics_and_external_augmentation",
        SOURCE_SEMANTICS_AND_EXTERNAL_AUGMENTATION_FIELDS,
    ),
    (
        "output_permission_and_whitebox_gate",
        OUTPUT_PERMISSION_AND_WHITEBOX_GATE_FIELDS,
    ),
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "document_content_read_performed",
    "document_instruction_detection_performed",
    "document_instruction_handling_performed",
    "query_execution_performed",
    "retrieval_execution_performed",
    "prompt_or_answer_access_performed",
    "prompt_execution_performed",
    "provider_or_model_selected",
    "model_call_performed",
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
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _output_permission_state(output_category: str) -> str:
    if output_category in HUMAN_CONFIRMATION_OUTPUT_CATEGORIES:
        return "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
    return "CONTROL_NO_AUTO_PUBLICATION_NO_AUTO_FINALIZATION"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条固定控制请求，不包含业务事实或可执行运行时输入。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    output_category = configuration["output_category"]
    return {
        "control_scenario": scenario,
        "negative_test_case_id": configuration["negative_test_case_id"],
        "rag_answer_structure_ref": _control_ref("rag-answer-structure", scenario),
        "prompt_version_ref": _control_ref("prompt-version", scenario),
        "internal_evidence_ref": (
            _control_ref("internal-evidence", scenario)
            if configuration["include_internal_evidence_ref"]
            else None
        ),
        "external_augmentation_ref": _control_ref(
            "external-augmentation-opinion", scenario
        ),
        "evidence_gap_ref": (
            _control_ref("evidence-gap", scenario)
            if configuration["include_evidence_gap_ref"]
            else None
        ),
        "source_type_ref": _control_ref("source-type", scenario),
        "document_evidence_ref": _control_ref("document-evidence", scenario),
        "document_instruction_candidate_ref": _control_ref(
            "document-instruction-candidate", scenario
        ),
        "ids_rule_ref": _control_ref("ids-rule", scenario),
        "model_output_permission_ref": _control_ref(
            "model-output-permission", scenario
        ),
        "output_classification_ref": _control_ref("output-classification", scenario),
        "human_confirmation_gate_ref": _control_ref(
            "human-confirmation-gate", scenario
        ),
        "audit_boundary_ref": _control_ref("audit-boundary", scenario),
        "query_ref": _control_ref("query", scenario),
        "index_version_ref": _control_ref("index-version", scenario),
        "model_version_ref": _control_ref("model-version", scenario),
        "selected_evidence_ref": _control_ref("selected-evidence", scenario),
        "external_public_reference_ref": _control_ref(
            "external-public-reference", scenario
        ),
        "model_reasoning_ref": _control_ref("model-reasoning", scenario),
        "output_category": f"CONTROL_OUTPUT_CATEGORY_{output_category.upper()}",
        "document_instruction_evidence_state": (
            "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
        ),
        "ids_rule_precedence_state": "CONTROL_IDS_RULES_PREVAIL",
        "injection_defense_state": (
            "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
        ),
        "source_type_separation_state": (
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        ),
        "external_augmentation_display_label": "external_augmentation_opinion",
        "output_permission_state": _output_permission_state(output_category),
        "negative_test_execution_state": (
            "CONTROL_NEGATIVE_TEST_LABEL_ONLY_NO_RUNTIME_EXECUTION"
        ),
    }


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的五条 Stage104 P2 非业务控制请求。"""

    return {
        CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    }


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {
        "actual_document_content_read_count": 0,
        "actual_document_instruction_detection_count": 0,
        "actual_query_execution_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_prompt_execution_count": 0,
        "actual_model_call_count": 0,
        "actual_negative_test_case_execution_count": 0,
        "actual_model_output_classification_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_answer_publication_count": 0,
        "actual_production_writeback_count": 0,
        "actual_audit_log_write_count": 0,
        "actual_persistent_state_write_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
    }


def _empty_projection_result() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prefix, _fields in PROJECTION_FIELDS:
        result[f"{prefix}_control_projections"] = []
        result[f"{prefix}_control_projection_count"] = 0
    return result


def _rejected_result() -> dict[str, Any]:
    """非固定控制输入保持拒绝状态，并且不产生控制投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": REJECTED_RESULT,
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": 0,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _output_category(request: Mapping[str, Optional[str]]) -> str:
    return str(request["output_category"]).replace("CONTROL_OUTPUT_CATEGORY_", "").lower()


def _project(request: Mapping[str, Optional[str]]) -> dict[str, dict[str, Any]]:
    output_category = _output_category(request)
    human_confirmation_required = output_category in HUMAN_CONFIRMATION_OUTPUT_CATEGORIES
    evidence_gap_present = request["evidence_gap_ref"] is not None
    scenario = str(request["control_scenario"])
    negative_test_case_id = str(request["negative_test_case_id"])

    return {
        "answer_contract_and_reproducibility": {
            "control_scenario": scenario,
            "negative_test_case_id": negative_test_case_id,
            "stage104_phase1_rag_negative_test_contract_ref": _control_ref(
                "stage104-phase1-contract", scenario
            ),
            "rag_answer_structure_ref": request["rag_answer_structure_ref"],
            "query_ref": request["query_ref"],
            "index_version_ref": request["index_version_ref"],
            "prompt_version_ref": request["prompt_version_ref"],
            "model_version_ref": request["model_version_ref"],
            "selected_evidence_ref": request["selected_evidence_ref"],
            "answer_structure_section_count": 5,
            "answer_structure_reference_state": "CONTROL_FIVE_SECTION_REFERENCE_ONLY",
            "prompt_version_reference_state": "CONTROL_OPAQUE_REFERENCE_ONLY",
            "control_slice_state": "CONTROL_REFERENCE_ONLY_IN_MEMORY",
        },
        "document_evidence_and_rule_defense": {
            "control_scenario": scenario,
            "negative_test_case_id": negative_test_case_id,
            "document_evidence_ref": request["document_evidence_ref"],
            "document_instruction_candidate_ref": request[
                "document_instruction_candidate_ref"
            ],
            "ids_rule_ref": request["ids_rule_ref"],
            "document_instruction_evidence_state": request[
                "document_instruction_evidence_state"
            ],
            "ids_rule_precedence_state": request["ids_rule_precedence_state"],
            "injection_defense_state": request["injection_defense_state"],
            "document_instruction_cannot_override_ids_rule_state": (
                "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE"
            ),
            "document_instruction_cannot_relax_output_permission_state": (
                "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_RELAX_OUTPUT_PERMISSION"
            ),
            "document_instruction_cannot_bypass_human_confirmation_state": (
                "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_BYPASS_HUMAN_CONFIRMATION"
            ),
            "actual_document_content_read_performed": False,
            "actual_document_instruction_processed": False,
        },
        "source_semantics_and_external_augmentation": {
            "control_scenario": scenario,
            "negative_test_case_id": negative_test_case_id,
            "internal_evidence_ref": request["internal_evidence_ref"],
            "evidence_gap_ref": request["evidence_gap_ref"],
            "external_public_reference_ref": request["external_public_reference_ref"],
            "model_reasoning_ref": request["model_reasoning_ref"],
            "external_augmentation_ref": request["external_augmentation_ref"],
            "source_type_ref": request["source_type_ref"],
            "source_type_separation_state": request["source_type_separation_state"],
            "external_augmentation_display_label": request[
                "external_augmentation_display_label"
            ],
            "external_augmentation_display_composition_state": (
                "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED"
            ),
            "evidence_gap_presentation_state": (
                "CONTROL_EVIDENCE_GAP_NOT_INTERNAL_EXPERIENCE"
                if evidence_gap_present
                else "CONTROL_INTERNAL_EVIDENCE_REFERENCE_PRESENT"
            ),
            "external_augmentation_may_not_replace_internal_evidence": True,
            "actual_source_type_bound": False,
            "actual_external_augmentation_displayed": False,
        },
        "output_permission_and_whitebox_gate": {
            "control_scenario": scenario,
            "negative_test_case_id": negative_test_case_id,
            "output_category": output_category,
            "output_classification_ref": request["output_classification_ref"],
            "model_output_permission_ref": request["model_output_permission_ref"],
            "human_confirmation_gate_ref": request["human_confirmation_gate_ref"],
            "output_permission_state": request["output_permission_state"],
            "business_line_whitebox_human_confirmation_required": (
                human_confirmation_required
            ),
            "automatic_final_conclusion_allowed": False,
            "automatic_answer_publication_allowed": False,
            "automatic_production_writeback_allowed": False,
            "actual_output_classified": False,
            "actual_human_confirmation_recorded": False,
            "actual_final_conclusion_published": False,
            "actual_production_writeback_performed": False,
            "negative_test_execution_state": request["negative_test_execution_state"],
        },
    }


def execute_rag_negative_testing_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """机械投影固定控制输入；任何漂移均返回零运行时拒绝结果。"""

    if control_input != build_control_input():
        return _rejected_result()

    projections = [_project(request) for request in control_input[CONTROL_FIELDS[0]]]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": PASS_RESULT,
        "failure_state": None,
        "control_input_count": len(projections),
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": len(projections)
        * sum(len(fields) for _prefix, fields in PROJECTION_FIELDS),
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
    }
    for prefix, _fields in PROJECTION_FIELDS:
        records = [projection[prefix] for projection in projections]
        result[f"{prefix}_control_projections"] = records
        result[f"{prefix}_control_projection_count"] = len(records)
    return result
