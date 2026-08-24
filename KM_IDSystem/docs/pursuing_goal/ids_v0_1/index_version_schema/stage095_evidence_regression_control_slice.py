"""Stage095 P2 的纯内存证据回归控制切片。

模块只投影自身定义的固定、非业务、reference-only 控制输入。它承接
Stage095 P1 静态合同和 Stage094 已复审证据撤回控制工件，不读取真实资料、
检索结果或证据账本，不连接数据库，不计算真实风险，不执行撤回、降级、投毒
处置或报告状态更新，也不写入持久化记录。
"""

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage095.evidence_regression.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EVIDENCE_REGRESSION"
CONTROL_ADAPTER_VERSION = "ids.evidence_regression.control_adapter.v0_1.stage095.p2"
CONTROL_PREFIX = ":control:stage095-p2:"
CONTROL_FIELDS = ("evidence_regression_control_requests",)
PHASE1_EVIDENCE_REGRESSION_CONTRACT_CONTROL_REF = (
    ":control:stage095-p2:stage095-phase1-evidence-regression-contract:reference-only"
)
STAGE094_REVIEW_CONTROL_REF = (
    ":control:stage095-p2:stage094-reviewed-evidence-revocation:reference-only"
)

EVIDENCE_REGRESSION_SCHEMA_BINDING_FIELDS = (
    "phase1_evidence_regression_contract_ref",
    "stage094_review_control_ref",
    "evidence_ledger_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "schema_binding_state",
    "control_slice_state",
)
EVIDENCE_REGRESSION_RELATION_FIELDS = (
    "evidence_ledger_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "risk_score_ref",
    "evidence_grade_ref",
    "revocation_status_ref",
    "poisoning_defense_status_ref",
)
RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS = (
    "evidence_ledger_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "capture_state",
)
RISK_AND_EVIDENCE_GRADE_CONTROL_FIELDS = (
    "risk_score_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "evidence_id_ref",
    "evidence_gap_ref",
    "risk_assessment_state",
    "degradation_state",
    "human_whitebox_review_state",
)
REVOCATION_AND_POISONING_CONTROL_FIELDS = (
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "evidence_ledger_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "degradation_state",
    "human_whitebox_review_state",
    "control_action_state",
)
CRITICAL_CONCLUSION_AND_REPORT_IMPACT_FIELDS = (
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "risk_score_ref",
    "evidence_grade_ref",
    "revocation_status_ref",
    "report_id_ref",
    "report_status_impact_state",
    "human_whitebox_review_state",
    "conclusion_binding_state",
)
INPUT_FIELDS = (
    "control_scenario",
    "evidence_ledger_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "risk_score_ref",
    "evidence_grade_ref",
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "evidence_grade_label",
    "capture_state",
    "risk_assessment_state",
    "degradation_state",
    "report_status_impact_state",
    "human_whitebox_review_state",
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "retrieval_execution_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "evidence_regression_execution_performed",
    "risk_score_calculation_performed",
    "evidence_grade_change_performed",
    "revocation_execution_performed",
    "degradation_execution_performed",
    "recovery_execution_performed",
    "poisoning_defense_execution_performed",
    "report_status_update_performed",
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
    "internal_material_insufficient_evidence_gap_reference_only",
    "low_ocr_evidence_degradation_reference_only",
    "old_version_evidence_degradation_reference_only",
    "conflict_evidence_degradation_reference_only",
    "revoked_evidence_report_review_reference_only",
    "suspected_poisoning_evidence_quarantined_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "internal_material_insufficient_evidence_gap_reference_only": {
        "evidence_grade_label": "E",
        "include_evidence_id_ref": False,
        "include_evidence_gap_ref": True,
        "degradation_state": "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
        "report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW"
        ),
        "control_action_state": (
            "CONTROL_EVIDENCE_GAP_REFERENCE_PENDING_WHITEBOX_REVIEW"
        ),
    },
    "low_ocr_evidence_degradation_reference_only": {
        "evidence_grade_label": "D",
        "include_evidence_id_ref": True,
        "include_evidence_gap_ref": False,
        "degradation_state": "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_OCR",
        "control_action_state": "CONTROL_LOW_OCR_DEGRADATION_REFERENCE_NOT_EXECUTED",
    },
    "old_version_evidence_degradation_reference_only": {
        "evidence_grade_label": "C",
        "include_evidence_id_ref": True,
        "include_evidence_gap_ref": False,
        "degradation_state": "CONTROL_DEGRADED_OLD_VERSION_NOT_ACCEPTED",
        "report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_OLD_VERSION"
        ),
        "control_action_state": (
            "CONTROL_OLD_VERSION_DEGRADATION_REFERENCE_NOT_EXECUTED"
        ),
    },
    "conflict_evidence_degradation_reference_only": {
        "evidence_grade_label": "D",
        "include_evidence_id_ref": True,
        "include_evidence_gap_ref": False,
        "degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
        "control_action_state": "CONTROL_CONFLICT_DEGRADATION_REFERENCE_NOT_EXECUTED",
    },
    "revoked_evidence_report_review_reference_only": {
        "evidence_grade_label": "E",
        "include_evidence_id_ref": True,
        "include_evidence_gap_ref": False,
        "degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        "report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_REVOKED_PENDING_WHITEBOX_REVIEW"
        ),
        "control_action_state": "CONTROL_REVOCATION_REFERENCE_NOT_EXECUTED",
    },
    "suspected_poisoning_evidence_quarantined_reference_only": {
        "evidence_grade_label": "E",
        "include_evidence_id_ref": True,
        "include_evidence_gap_ref": False,
        "degradation_state": "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
        "report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING"
        ),
        "control_action_state": "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED",
    },
}
PROJECTION_FIELDS = (
    ("evidence_regression_schema_binding", EVIDENCE_REGRESSION_SCHEMA_BINDING_FIELDS),
    ("evidence_regression_relation", EVIDENCE_REGRESSION_RELATION_FIELDS),
    (
        "retrieval_evidence_capture_binding",
        RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS,
    ),
    ("risk_and_evidence_grade_control", RISK_AND_EVIDENCE_GRADE_CONTROL_FIELDS),
    ("revocation_and_poisoning_control", REVOCATION_AND_POISONING_CONTROL_FIELDS),
    (
        "critical_conclusion_and_report_impact",
        CRITICAL_CONCLUSION_AND_REPORT_IMPACT_FIELDS,
    ),
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条不包含业务事实的固定证据回归控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    evidence_id_ref = (
        _control_ref("evidence", scenario)
        if configuration["include_evidence_id_ref"]
        else None
    )
    evidence_gap_ref = (
        _control_ref("evidence-gap", scenario)
        if configuration["include_evidence_gap_ref"]
        else None
    )
    return {
        "control_scenario": scenario,
        "evidence_ledger_ref": _control_ref("evidence-ledger", scenario),
        "evidence_id_ref": evidence_id_ref,
        "evidence_gap_ref": evidence_gap_ref,
        "critical_conclusion_ref": _control_ref("critical-conclusion", scenario),
        "document_id_ref": _control_ref("document", scenario),
        "chunk_id_ref": _control_ref("chunk", scenario),
        "fact_id_ref": _control_ref("fact", scenario),
        "query_ref": _control_ref("query", scenario),
        "answer_ref": _control_ref("answer", scenario),
        "report_id_ref": _control_ref("report", scenario),
        "risk_score_ref": _control_ref("risk-score", scenario),
        "evidence_grade_ref": _control_ref(
            f"evidence-grade-{configuration['evidence_grade_label']}", scenario
        ),
        "revocation_status_ref": _control_ref("revocation-status", scenario),
        "poisoning_defense_status_ref": _control_ref(
            "poisoning-defense-status", scenario
        ),
        "evidence_grade_label": configuration["evidence_grade_label"],
        "capture_state": "CONTROL_EVIDENCE_CAPTURE_REFERENCE_DECLARED_NOT_EXECUTED",
        "risk_assessment_state": (
            "CONTROL_RISK_REFERENCE_OWNER_FORMULA_REQUIRED_NOT_CALCULATED"
        ),
        "degradation_state": configuration["degradation_state"],
        "report_status_impact_state": configuration["report_status_impact_state"],
        "human_whitebox_review_state": "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
    }


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的六条固定控制输入。"""

    return {CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]}


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
        "actual_evidence_regression_execution_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_retrieval_evidence_capture_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_degradation_execution_count": 0,
        "actual_recovery_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_audit_log_write_count": 0,
    }


def _rejected_result() -> dict[str, Any]:
    """固定输入之外的内容保持拒绝状态，且不产生任何投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_IN_MEMORY_EVIDENCE_REGRESSION_CONTROL_SLICE",
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
    scenario = str(request["control_scenario"])
    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    schema_binding = {
        "phase1_evidence_regression_contract_ref": (
            PHASE1_EVIDENCE_REGRESSION_CONTRACT_CONTROL_REF
        ),
        "stage094_review_control_ref": STAGE094_REVIEW_CONTROL_REF,
        "evidence_ledger_ref": request["evidence_ledger_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "schema_binding_state": "CONTROL_PHASE1_EVIDENCE_REGRESSION_SHAPE_BOUND",
        "control_slice_state": "CONTROL_REFERENCE_ONLY_IN_MEMORY",
    }
    relation = {
        field: request[field] for field in EVIDENCE_REGRESSION_RELATION_FIELDS
    }
    retrieval_capture = {
        field: request[field]
        for field in RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS
    }
    risk_and_grade = {
        field: request[field] for field in RISK_AND_EVIDENCE_GRADE_CONTROL_FIELDS
    }
    revocation_and_poisoning = {
        "revocation_status_ref": request["revocation_status_ref"],
        "poisoning_defense_status_ref": request["poisoning_defense_status_ref"],
        "evidence_ledger_ref": request["evidence_ledger_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "degradation_state": request["degradation_state"],
        "human_whitebox_review_state": request["human_whitebox_review_state"],
        "control_action_state": configuration["control_action_state"],
    }
    conclusion_and_impact = {
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "risk_score_ref": request["risk_score_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "revocation_status_ref": request["revocation_status_ref"],
        "report_id_ref": request["report_id_ref"],
        "report_status_impact_state": request["report_status_impact_state"],
        "human_whitebox_review_state": request["human_whitebox_review_state"],
        "conclusion_binding_state": (
            "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        ),
    }
    return {
        "evidence_regression_schema_binding": schema_binding,
        "evidence_regression_relation": relation,
        "retrieval_evidence_capture_binding": retrieval_capture,
        "risk_and_evidence_grade_control": risk_and_grade,
        "revocation_and_poisoning_control": revocation_and_poisoning,
        "critical_conclusion_and_report_impact": conclusion_and_impact,
    }


def execute_evidence_regression_control_slice(
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
    for prefix, _fields in PROJECTION_FIELDS:
        projections[f"{prefix}_control_projection_count"] = len(
            projections[f"{prefix}_control_projections"]
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "CONTROL_EVIDENCE_REGRESSION_PROJECTIONS_DECLARED",
        "failure_state": None,
        "control_input_count": len(requests),
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **projections,
    }
