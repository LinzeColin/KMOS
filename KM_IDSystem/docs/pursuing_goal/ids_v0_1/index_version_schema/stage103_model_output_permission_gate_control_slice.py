"""Stage103 P2 的纯内存模型输出权限门禁受控切片。

模块只投影自身定义的固定、非业务、reference-only 控制输入。它承接
Stage103 P1 静态合同与 Stage102 Review 控制工件，不读取文档内容、查询、
检索结果、提示词、模型配置或 evidence，不连接数据库，不调用模型，不消费
模型 Token，也不写入持久化记录。
"""

from copy import deepcopy
from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage103.model_output_permission_gate.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE"
CONTROL_ADAPTER_VERSION = (
    "ids.model_output_permission_gate.control_adapter.v0_1.stage103.p2"
)
CONTROL_PREFIX = ":control:stage103-p2:"
CONTROL_FIELDS = ("model_output_permission_gate_control_requests",)
PHASE1_MODEL_OUTPUT_PERMISSION_GATE_CONTRACT_REF = (
    ":control:stage103-p2:stage103-phase1-model-output-permission-gate-contract:reference-only"
)
STAGE102_REVIEW_CONTROL_REF = (
    ":control:stage103-p2:stage102-reviewed-document-prompt-injection-defense:reference-only"
)

REPRODUCIBILITY_RECORD_FIELDS = (
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
)
ANSWER_CONTRACT_AND_REPRODUCIBILITY_FIELDS = (
    "stage103_phase1_model_output_permission_gate_contract_ref",
    "stage102_review_control_ref",
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "output_classification_ref",
    "control_slice_state",
)
DOCUMENT_EVIDENCE_AND_OUTPUT_PERMISSION_DEFENSE_FIELDS = (
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "document_instruction_evidence_state",
    "ids_rule_ref",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "audit_boundary_ref",
    "document_instruction_may_not_override_ids_rule_state",
    "document_instruction_may_not_relax_output_permission_state",
    "document_instruction_may_not_bypass_human_confirmation_state",
)
SOURCE_SEMANTICS_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS = (
    "source_type_ref",
    "source_type_separation_state",
    "internal_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "external_augmentation_display_label",
    "internal_evidence_source_type",
    "external_public_reference_source_type",
    "model_reasoning_source_type",
    "evidence_gap_source_type",
    "external_augmentation_display_state",
    "display_label_is_not_source_type_state",
    "display_preserves_underlying_source_types_state",
    "display_does_not_close_evidence_gap_state",
)
OUTPUT_PERMISSION_AND_WHITEBOX_GATE_FIELDS = (
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "output_category",
    "output_permission_state",
    "human_confirmation_state",
    "final_conclusion_state",
    "automatic_publication_state",
    "production_writeback_state",
    "business_use_state",
)
INPUT_FIELDS = (
    "control_scenario",
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
    "output_permission_state",
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
    "prompt_execution_performed",
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
    "safe_summary_reference_only",
    "draft_recommendation_reference_only",
    "high_risk_engineering_advice_reference_only",
    "contractual_commitment_reference_only",
    "production_writeback_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "safe_summary_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "safe_summary",
        "output_permission_state": "CONTROL_SAFE_SUMMARY_REFERENCE_ONLY_NO_PUBLICATION",
    },
    "draft_recommendation_reference_only": {
        "include_internal_evidence_ref": False,
        "include_evidence_gap_ref": True,
        "output_category": "draft_recommendation",
        "output_permission_state": (
            "CONTROL_DRAFT_RECOMMENDATION_REFERENCE_ONLY_NO_PUBLICATION"
        ),
    },
    "high_risk_engineering_advice_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "high_risk_engineering_advice",
        "output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
    },
    "contractual_commitment_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "contractual_commitment",
        "output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
    },
    "production_writeback_reference_only": {
        "include_internal_evidence_ref": True,
        "include_evidence_gap_ref": False,
        "output_category": "production_writeback",
        "output_permission_state": (
            "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        ),
    },
}
HUMAN_CONFIRMATION_OUTPUT_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}
PROJECTION_FIELDS = (
    ("answer_contract_and_reproducibility", ANSWER_CONTRACT_AND_REPRODUCIBILITY_FIELDS),
    (
        "document_evidence_and_output_permission_defense",
        DOCUMENT_EVIDENCE_AND_OUTPUT_PERMISSION_DEFENSE_FIELDS,
    ),
    (
        "source_semantics_and_external_augmentation_display",
        SOURCE_SEMANTICS_AND_EXTERNAL_AUGMENTATION_DISPLAY_FIELDS,
    ),
    ("output_permission_and_whitebox_gate", OUTPUT_PERMISSION_AND_WHITEBOX_GATE_FIELDS),
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条不包含业务事实或运行时输入的固定控制请求。"""

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
        "rag_answer_structure_ref": _control_ref("rag-answer-structure", scenario),
        "prompt_version_ref": _control_ref("prompt-version", scenario),
        "internal_evidence_ref": internal_evidence_ref,
        "external_augmentation_ref": _control_ref(
            "external-augmentation-opinion", scenario
        ),
        "evidence_gap_ref": evidence_gap_ref,
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
        "output_category": (
            f"CONTROL_OUTPUT_CATEGORY_{configuration['output_category'].upper()}"
        ),
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
        "output_permission_state": configuration["output_permission_state"],
    }


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的五条模型输出权限控制输入。"""

    return {
        CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    }


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {
        "actual_input_request_count": 0,
        "actual_document_content_read_count": 0,
        "actual_document_instruction_detection_count": 0,
        "actual_document_instruction_handling_count": 0,
        "actual_query_record_count": 0,
        "actual_index_version_record_count": 0,
        "actual_prompt_version_record_count": 0,
        "actual_model_version_record_count": 0,
        "actual_selected_evidence_record_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_prompt_execution_count": 0,
        "actual_model_call_count": 0,
        "actual_source_type_binding_count": 0,
        "actual_external_augmentation_display_count": 0,
        "actual_model_output_classification_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_answer_publication_count": 0,
        "actual_production_writeback_count": 0,
        "actual_audit_log_write_count": 0,
    }


def _empty_projection_result() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prefix, _fields in PROJECTION_FIELDS:
        result[f"{prefix}_control_projections"] = []
        result[f"{prefix}_control_projection_count"] = 0
    return result


def _rejected_result() -> dict[str, Any]:
    """非固定控制输入保持拒绝状态，并且不产生投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": (
            "REJECTED_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE"
        ),
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


def _project(
    request: Mapping[str, Optional[str]],
) -> dict[str, dict[str, Optional[str]]]:
    output_category = str(request["output_category"]).removeprefix(
        "CONTROL_OUTPUT_CATEGORY_"
    ).lower()
    human_confirmation_required = (
        output_category in HUMAN_CONFIRMATION_OUTPUT_CATEGORIES
    )
    answer_contract_and_reproducibility = {
        "stage103_phase1_model_output_permission_gate_contract_ref": (
            PHASE1_MODEL_OUTPUT_PERMISSION_GATE_CONTRACT_REF
        ),
        "stage102_review_control_ref": STAGE102_REVIEW_CONTROL_REF,
        "rag_answer_structure_ref": request["rag_answer_structure_ref"],
        "prompt_version_ref": request["prompt_version_ref"],
        "query_ref": request["query_ref"],
        "index_version_ref": request["index_version_ref"],
        "model_version_ref": request["model_version_ref"],
        "selected_evidence_ref": request["selected_evidence_ref"],
        "output_classification_ref": request["output_classification_ref"],
        "control_slice_state": "CONTROL_REFERENCE_ONLY_IN_MEMORY",
    }
    document_evidence_and_output_permission_defense = {
        "document_evidence_ref": request["document_evidence_ref"],
        "document_instruction_candidate_ref": request[
            "document_instruction_candidate_ref"
        ],
        "document_instruction_evidence_state": request[
            "document_instruction_evidence_state"
        ],
        "ids_rule_ref": request["ids_rule_ref"],
        "ids_rule_precedence_state": request["ids_rule_precedence_state"],
        "injection_defense_state": request["injection_defense_state"],
        "audit_boundary_ref": request["audit_boundary_ref"],
        "document_instruction_may_not_override_ids_rule_state": (
            "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE"
        ),
        "document_instruction_may_not_relax_output_permission_state": (
            "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_RELAX_OUTPUT_PERMISSION"
        ),
        "document_instruction_may_not_bypass_human_confirmation_state": (
            "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_BYPASS_HUMAN_CONFIRMATION"
        ),
    }
    source_semantics_and_external_augmentation_display = {
        "source_type_ref": request["source_type_ref"],
        "source_type_separation_state": request["source_type_separation_state"],
        "internal_evidence_ref": request["internal_evidence_ref"],
        "external_public_reference_ref": request["external_public_reference_ref"],
        "model_reasoning_ref": request["model_reasoning_ref"],
        "external_augmentation_ref": request["external_augmentation_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "external_augmentation_display_label": "external_augmentation_opinion",
        "internal_evidence_source_type": "internal_evidence",
        "external_public_reference_source_type": "external_public_reference",
        "model_reasoning_source_type": "model_reasoning",
        "evidence_gap_source_type": "evidence_gap",
        "external_augmentation_display_state": (
            "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        ),
        "display_label_is_not_source_type_state": (
            "CONTROL_DISPLAY_LABEL_IS_NOT_SOURCE_TYPE"
        ),
        "display_preserves_underlying_source_types_state": (
            "CONTROL_DISPLAY_PRESERVES_UNDERLYING_SOURCE_TYPES"
        ),
        "display_does_not_close_evidence_gap_state": (
            "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP"
        ),
    }
    output_permission_and_whitebox_gate = {
        "model_output_permission_ref": request["model_output_permission_ref"],
        "output_classification_ref": request["output_classification_ref"],
        "human_confirmation_gate_ref": request["human_confirmation_gate_ref"],
        "output_category": request["output_category"],
        "output_permission_state": request["output_permission_state"],
        "human_confirmation_state": (
            "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED"
            if human_confirmation_required
            else "CONTROL_HUMAN_CONFIRMATION_NOT_EXECUTED"
        ),
        "final_conclusion_state": "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
        "automatic_publication_state": "CONTROL_AUTOMATIC_PUBLICATION_DISABLED",
        "production_writeback_state": (
            "CONTROL_PRODUCTION_WRITEBACK_REQUIRES_FUTURE_AUTHORIZATION"
            if output_category == "production_writeback"
            else "CONTROL_PRODUCTION_WRITEBACK_NOT_TRIGGERED"
        ),
        "business_use_state": "CONTROL_BUSINESS_USE_REQUIRES_WHITEBOX_OWNER",
    }
    return {
        "answer_contract_and_reproducibility": answer_contract_and_reproducibility,
        "document_evidence_and_output_permission_defense": (
            document_evidence_and_output_permission_defense
        ),
        "source_semantics_and_external_augmentation_display": (
            source_semantics_and_external_augmentation_display
        ),
        "output_permission_and_whitebox_gate": output_permission_and_whitebox_gate,
    }


def execute_model_output_permission_gate_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """投影唯一固定控制输入；真实模型输出仍属于后续授权阶段。"""

    expected_input = build_control_input()
    if not isinstance(control_input, Mapping) or dict(control_input) != expected_input:
        return _rejected_result()

    requests = control_input[CONTROL_FIELDS[0]]
    projections = [_project(request) for request in requests]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": (
            "PASS_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE_RUNTIME_DISABLED"
        ),
        "failure_state": None,
        "control_input_count": len(requests),
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": len(requests)
        * sum(len(fields) for _prefix, fields in PROJECTION_FIELDS),
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
    }
    for prefix, _fields in PROJECTION_FIELDS:
        values = [projection[prefix] for projection in projections]
        result[f"{prefix}_control_projections"] = values
        result[f"{prefix}_control_projection_count"] = len(values)
    return deepcopy(result)
