"""Stage097 P2 的纯内存回答合同受控切片。

模块只投影自身定义的固定、非业务、reference-only 控制输入。它承接
Stage097 P1 静态回答合同和 Stage096 Review 已复审控制工件，不读取真实资料、
检索结果、提示词、模型配置或 evidence，不连接数据库，不调用模型，不消费
模型 Token，也不写入持久化记录。
"""

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage097.answer_contract.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_ANSWER_CONTRACT"
CONTROL_ADAPTER_VERSION = "ids.answer_contract.control_adapter.v0_1.stage097.p2"
CONTROL_PREFIX = ":control:stage097-p2:"
CONTROL_FIELDS = ("answer_contract_control_requests",)
PHASE1_ANSWER_CONTRACT_CONTROL_REF = (
    ":control:stage097-p2:stage097-phase1-answer-contract:reference-only"
)
STAGE096_REVIEW_CONTROL_REF = (
    ":control:stage097-p2:stage096-reviewed-knowledge-base-poisoning-defense:reference-only"
)

ANSWER_CONTRACT_BINDING_FIELDS = (
    "stage097_phase1_answer_contract_ref",
    "stage096_review_control_ref",
    "answer_structure_ref",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "control_slice_state",
)
VERSION_AND_SELECTED_EVIDENCE_RECORD_FIELDS = (
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "record_shape_state",
)
SOURCE_TYPE_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS = (
    "source_type_ref",
    "source_type_separation_state",
    "internal_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "evidence_gap_ref",
    "internal_evidence_source_type",
    "external_public_reference_source_type",
    "model_reasoning_source_type",
    "evidence_gap_source_type",
    "external_augmentation_display_ref",
    "external_augmentation_display_state",
    "display_does_not_replace_source_type_state",
)
PROMPT_INJECTION_AND_OUTPUT_PERMISSION_FIELDS = (
    "citation_structure_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "output_permission_state",
    "final_conclusion_state",
)
INPUT_FIELDS = (
    "control_scenario",
    "answer_structure_ref",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "citation_structure_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "output_permission_state",
    "external_augmentation_display_ref",
    "source_type_separation_state",
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

CONTROL_SCENARIOS = (
    "internal_evidence_with_external_augmentation_reference_only",
    "evidence_gap_with_external_augmentation_reference_only",
    "retrieval_document_instruction_rejected_reference_only",
    "high_risk_engineering_advice_confirmation_required_reference_only",
    "contract_commitment_confirmation_required_reference_only",
    "production_writeback_confirmation_required_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "internal_evidence_with_external_augmentation_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_classification": "informational_answer",
        "prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "output_permission_state": "CONTROL_INFORMATIONAL_OUTPUT_REMAINS_REFERENCE_ONLY",
    },
    "evidence_gap_with_external_augmentation_reference_only": {
        "include_internal_evidence_ref": False,
        "include_evidence_gap_ref": True,
        "output_classification": "evidence_gap_answer",
        "prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "output_permission_state": "CONTROL_EVIDENCE_GAP_REQUIRES_HUMAN_WHITEBOX_CONFIRMATION",
    },
    "retrieval_document_instruction_rejected_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_classification": "prompt_injection_rejected",
        "prompt_injection_defense_state": "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
        "output_permission_state": "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
    },
    "high_risk_engineering_advice_confirmation_required_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_classification": "high_risk_engineering_advice",
        "prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
    },
    "contract_commitment_confirmation_required_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_classification": "contract_commitment",
        "prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
    },
    "production_writeback_confirmation_required_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_classification": "production_writeback",
        "prompt_injection_defense_state": "CONTROL_PROMPT_INJECTION_DEFENSE_DECLARED",
        "output_permission_state": "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
    },
}
PROJECTION_FIELDS = (
    ("answer_contract_binding", ANSWER_CONTRACT_BINDING_FIELDS),
    (
        "version_and_selected_evidence_record",
        VERSION_AND_SELECTED_EVIDENCE_RECORD_FIELDS,
    ),
    (
        "source_type_and_external_augmentation_display",
        SOURCE_TYPE_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS,
    ),
    (
        "prompt_injection_and_output_permission",
        PROMPT_INJECTION_AND_OUTPUT_PERMISSION_FIELDS,
    ),
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条不包含业务事实的固定回答合同控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    internal_evidence_ref = (
        _control_ref("internal-evidence", scenario)
        if configuration["include_internal_evidence_ref"]
        else None
    )
    evidence_gap_ref = (
        _control_ref("evidence-gap", scenario)
        if configuration["include_evidence_gap_ref"]
        else None
    )
    return {
        "control_scenario": scenario,
        "answer_structure_ref": _control_ref("answer-structure", scenario),
        "query_ref": _control_ref("query", scenario),
        "index_version_ref": _control_ref("index-version", scenario),
        "prompt_version_ref": _control_ref("prompt-version", scenario),
        "model_version_ref": _control_ref("model-version", scenario),
        "selected_evidence_ref": _control_ref("selected-evidence", scenario),
        "internal_evidence_ref": internal_evidence_ref,
        "external_public_reference_ref": _control_ref(
            "external-public-reference", scenario
        ),
        "model_reasoning_ref": _control_ref("model-reasoning", scenario),
        "evidence_gap_ref": evidence_gap_ref,
        "source_type_ref": _control_ref("source-type", scenario),
        "citation_structure_ref": _control_ref("citation-structure", scenario),
        "output_classification_ref": _control_ref(
            f"output-classification-{configuration['output_classification']}", scenario
        ),
        "human_confirmation_gate_ref": _control_ref(
            "human-confirmation-gate", scenario
        ),
        "retrieval_document_instruction_precedence_state": (
            "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        ),
        "prompt_injection_defense_state": configuration[
            "prompt_injection_defense_state"
        ],
        "output_permission_state": configuration["output_permission_state"],
        "external_augmentation_display_ref": _control_ref(
            "external-augmentation-display", scenario
        ),
        "source_type_separation_state": (
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        ),
    }


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的六条固定控制输入。"""

    return {
        CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    }


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _empty_projection_result() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prefix, _fields in PROJECTION_FIELDS:
        result[f"{prefix}_control_projections"] = []
        result[f"{prefix}_control_projection_count"] = 0
    return result


def _zero_actual_counts() -> dict[str, int]:
    return {
        "actual_input_request_count": 0,
        "actual_query_record_count": 0,
        "actual_index_version_record_count": 0,
        "actual_prompt_version_record_count": 0,
        "actual_model_version_record_count": 0,
        "actual_selected_evidence_record_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_prompt_execution_count": 0,
        "actual_model_reasoning_count": 0,
        "actual_model_output_classification_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_answer_publication_count": 0,
        "actual_production_writeback_count": 0,
        "actual_audit_log_write_count": 0,
    }


def _rejected_result() -> dict[str, Any]:
    """固定输入之外的内容保持拒绝状态，且不产生任何投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_IN_MEMORY_ANSWER_CONTRACT_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _project(
    request: Mapping[str, Optional[str]],
) -> dict[str, dict[str, Optional[str]]]:
    answer_contract_binding = {
        "stage097_phase1_answer_contract_ref": PHASE1_ANSWER_CONTRACT_CONTROL_REF,
        "stage096_review_control_ref": STAGE096_REVIEW_CONTROL_REF,
        "answer_structure_ref": request["answer_structure_ref"],
        "query_ref": request["query_ref"],
        "index_version_ref": request["index_version_ref"],
        "prompt_version_ref": request["prompt_version_ref"],
        "model_version_ref": request["model_version_ref"],
        "selected_evidence_ref": request["selected_evidence_ref"],
        "control_slice_state": "CONTROL_REFERENCE_ONLY_IN_MEMORY",
    }
    version_and_selected_evidence_record = {
        field: request[field]
        for field in VERSION_AND_SELECTED_EVIDENCE_RECORD_FIELDS
        if field != "record_shape_state"
    }
    version_and_selected_evidence_record["record_shape_state"] = (
        "CONTROL_VERSION_AND_SELECTED_EVIDENCE_RECORDS_REFERENCE_ONLY"
    )
    source_type_and_external_augmentation_display = {
        "source_type_ref": request["source_type_ref"],
        "source_type_separation_state": request["source_type_separation_state"],
        "internal_evidence_ref": request["internal_evidence_ref"],
        "external_public_reference_ref": request["external_public_reference_ref"],
        "model_reasoning_ref": request["model_reasoning_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "internal_evidence_source_type": "internal_evidence",
        "external_public_reference_source_type": "external_public_reference",
        "model_reasoning_source_type": "model_reasoning",
        "evidence_gap_source_type": "evidence_gap",
        "external_augmentation_display_ref": request[
            "external_augmentation_display_ref"
        ],
        "external_augmentation_display_state": (
            "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        ),
        "display_does_not_replace_source_type_state": (
            "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
        ),
    }
    prompt_injection_and_output_permission = {
        "citation_structure_ref": request["citation_structure_ref"],
        "output_classification_ref": request["output_classification_ref"],
        "human_confirmation_gate_ref": request["human_confirmation_gate_ref"],
        "retrieval_document_instruction_precedence_state": request[
            "retrieval_document_instruction_precedence_state"
        ],
        "prompt_injection_defense_state": request["prompt_injection_defense_state"],
        "output_permission_state": request["output_permission_state"],
        "final_conclusion_state": "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
    }
    return {
        "answer_contract_binding": answer_contract_binding,
        "version_and_selected_evidence_record": version_and_selected_evidence_record,
        "source_type_and_external_augmentation_display": (
            source_type_and_external_augmentation_display
        ),
        "prompt_injection_and_output_permission": prompt_injection_and_output_permission,
    }


def execute_answer_contract_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """投影固定控制引用并返回临时结果。"""

    expected_input = build_control_input()
    if not isinstance(control_input, Mapping) or dict(control_input) != expected_input:
        return _rejected_result()

    projections = _empty_projection_result()
    requests = expected_input[CONTROL_FIELDS[0]]
    for request in requests:
        projected = _project(request)
        for prefix, _fields in PROJECTION_FIELDS:
            projections[f"{prefix}_control_projections"].append(projected[prefix])
            projections[f"{prefix}_control_projection_count"] += 1

    projection_field_total_per_request = sum(
        len(fields) for _prefix, fields in PROJECTION_FIELDS
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "PASS_IN_MEMORY_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
        "failure_state": None,
        "control_input_count": len(requests),
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": projection_field_total_per_request,
        "control_projection_field_total": (
            projection_field_total_per_request * len(requests)
        ),
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **projections,
    }
