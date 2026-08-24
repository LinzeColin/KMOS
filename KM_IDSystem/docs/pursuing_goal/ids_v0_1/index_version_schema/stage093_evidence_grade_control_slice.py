"""Stage093 P2 的纯内存证据可信等级控制切片。

模块只投影自身定义的固定、非业务、reference-only 控制输入。它绑定
Stage093 P1 的可信等级合同和已复审的 Stage092 控制链，不读取资料、检索结果
或真实证据账本，不连接数据库，不计算真实风险，不分配真实等级，不执行撤回、
投毒处置或报告状态更新，也不写入持久化记录。
"""

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage093.evidence_grade.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EVIDENCE_GRADE"
CONTROL_ADAPTER_VERSION = "ids.evidence_grade.control_adapter.v0_1.stage093.p2"
CONTROL_PREFIX = ":control:stage093-p2:"
CONTROL_FIELDS = ("evidence_grade_control_requests",)
PHASE1_EVIDENCE_GRADE_CONTRACT_CONTROL_REF = (
    ":control:stage093-p2:stage093-phase1-evidence-grade-contract:reference-only"
)
STAGE092_REVIEW_CONTROL_REF = (
    ":control:stage093-p2:stage092-reviewed-evidence-risk-scoring:reference-only"
)

EVIDENCE_GRADE_SCHEMA_BINDING_FIELDS = (
    "phase1_evidence_grade_contract_ref",
    "stage092_review_control_ref",
    "evidence_grade_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "grade_assignment_state",
    "schema_binding_state",
)
EVIDENCE_GRADE_RELATION_FIELDS = (
    "evidence_grade_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
)
RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS = (
    "evidence_ledger_ref",
    "evidence_capture_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "capture_state",
)
RISK_REFERENCE_BINDING_FIELDS = (
    "source_provenance_indicator_ref",
    "ocr_confidence_indicator_ref",
    "version_status_indicator_ref",
    "review_status_indicator_ref",
    "conflict_status_indicator_ref",
    "risk_score_ref",
)
EVIDENCE_GRADE_ASSIGNMENT_FIELDS = (
    "evidence_grade_ref",
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
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "grade_assignment_state",
)
REVOCATION_FIELDS = (
    "revocation_status_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "affected_fact_ref",
    "affected_report_ref",
    "recovery_state_ref",
    "report_status_impact_ref",
    "revocation_state",
)
POISONING_DEFENSE_FIELDS = (
    "poisoning_defense_status_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "source_provenance_indicator_ref",
    "conflict_status_indicator_ref",
    "anomaly_indicator_ref",
    "human_whitebox_review_state",
    "defense_state",
)
CRITICAL_CONCLUSION_BINDING_FIELDS = (
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "risk_score_ref",
    "revocation_status_ref",
    "conclusion_binding_state",
)
DEGRADATION_FIELDS = (
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_label",
    "risk_score_ref",
    "source_provenance_indicator_ref",
    "ocr_confidence_indicator_ref",
    "version_status_indicator_ref",
    "review_status_indicator_ref",
    "conflict_status_indicator_ref",
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "degradation_state",
)
REPORT_STATUS_IMPACT_FIELDS = (
    "report_id_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "revocation_status_ref",
    "risk_score_ref",
    "report_status_impact_ref",
    "report_status_impact_state",
    "human_whitebox_review_state",
)
FUTURE_INTEGRATION_FIELDS = (
    "phase1_evidence_grade_route_ref",
    "stage092_evidence_risk_scoring_route_ref",
    "evidence_ledger_capture_route_ref",
    "evidence_grade_assignment_route_ref",
    "risk_scoring_route_ref",
    "revocation_route_ref",
    "poisoning_defense_route_ref",
    "report_status_update_route_ref",
)
INPUT_FIELDS = (
    "control_scenario",
    "evidence_ledger_ref",
    "evidence_capture_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "source_provenance_indicator_ref",
    "ocr_confidence_indicator_ref",
    "version_status_indicator_ref",
    "review_status_indicator_ref",
    "conflict_status_indicator_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "risk_score_ref",
    "grade_assignment_state",
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "degradation_state",
    "report_status_impact_ref",
    "human_whitebox_review_state",
    "capture_state",
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "retrieval_execution_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "evidence_gap_detection_performed",
    "evidence_gap_resolution_performed",
    "retrieval_evidence_capture_performed",
    "risk_factor_evaluation_performed",
    "risk_score_calculation_performed",
    "evidence_grade_assignment_performed",
    "evidence_grade_change_performed",
    "revocation_execution_performed",
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
    "internal_material_insufficient_grade_pending_whitebox_review_reference_only",
    "low_trust_evidence_grade_degraded_reference_only",
    "conflict_evidence_grade_degraded_reference_only",
    "expired_evidence_grade_degraded_reference_only",
    "revoked_evidence_grade_degraded_reference_only",
    "suspected_poisoning_grade_quarantined_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "internal_material_insufficient_grade_pending_whitebox_review_reference_only": {
        "evidence_grade_label": "E",
        "include_evidence_id_ref": False,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_E_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW",
    },
    "low_trust_evidence_grade_degraded_reference_only": {
        "evidence_grade_label": "D",
        "include_evidence_id_ref": True,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_D_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_TRUST",
    },
    "conflict_evidence_grade_degraded_reference_only": {
        "evidence_grade_label": "B",
        "include_evidence_id_ref": True,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_B_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
    },
    "expired_evidence_grade_degraded_reference_only": {
        "evidence_grade_label": "C",
        "include_evidence_id_ref": True,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_C_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_EXPIRED",
    },
    "revoked_evidence_grade_degraded_reference_only": {
        "evidence_grade_label": "A",
        "include_evidence_id_ref": True,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_A_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_REVOKED",
    },
    "suspected_poisoning_grade_quarantined_reference_only": {
        "evidence_grade_label": "E",
        "include_evidence_id_ref": True,
        "grade_assignment_state": "CONTROL_GRADE_ASSIGNMENT_ROUTE_E_OWNER_RULE_REQUIRED",
        "degradation_state": "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING",
    },
}
PROJECTION_FIELDS = (
    ("evidence_grade_schema_binding", EVIDENCE_GRADE_SCHEMA_BINDING_FIELDS),
    ("evidence_grade_relation", EVIDENCE_GRADE_RELATION_FIELDS),
    ("retrieval_evidence_capture_binding", RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS),
    ("risk_reference_binding", RISK_REFERENCE_BINDING_FIELDS),
    ("evidence_grade_assignment", EVIDENCE_GRADE_ASSIGNMENT_FIELDS),
    ("revocation", REVOCATION_FIELDS),
    ("poisoning_defense", POISONING_DEFENSE_FIELDS),
    ("critical_conclusion_binding", CRITICAL_CONCLUSION_BINDING_FIELDS),
    ("degradation", DEGRADATION_FIELDS),
    ("report_status_impact", REPORT_STATUS_IMPACT_FIELDS),
    ("future_integration", FUTURE_INTEGRATION_FIELDS),
)


def _marker(scenario: str) -> str:
    return f"{CONTROL_PREFIX}{scenario}:reference-only"


def _control_ref(kind: str, scenario: str) -> str:
    return f"{kind}{_marker(scenario)}"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条不包含业务事实的固定可信等级控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    grade = configuration["evidence_grade_label"]
    evidence_id_ref = (
        _control_ref("evidence", scenario)
        if configuration["include_evidence_id_ref"]
        else None
    )
    return {
        "control_scenario": scenario,
        "evidence_ledger_ref": _control_ref("evidence-ledger", scenario),
        "evidence_capture_ref": _control_ref("evidence-capture", scenario),
        "evidence_id_ref": evidence_id_ref,
        "evidence_gap_ref": _control_ref("evidence-gap", scenario),
        "critical_conclusion_ref": _control_ref("critical-conclusion", scenario),
        "document_id_ref": _control_ref("document", scenario),
        "chunk_id_ref": _control_ref("chunk", scenario),
        "fact_id_ref": _control_ref("fact", scenario),
        "query_ref": _control_ref("query", scenario),
        "answer_ref": _control_ref("answer", scenario),
        "report_id_ref": _control_ref("report", scenario),
        "source_provenance_indicator_ref": _control_ref("source-provenance", scenario),
        "ocr_confidence_indicator_ref": _control_ref("ocr-confidence", scenario),
        "version_status_indicator_ref": _control_ref("version-status", scenario),
        "review_status_indicator_ref": _control_ref("review-status", scenario),
        "conflict_status_indicator_ref": _control_ref("conflict-status", scenario),
        "evidence_grade_ref": _control_ref(f"evidence-grade-{grade}", scenario),
        "evidence_grade_label": grade,
        "risk_score_ref": _control_ref("risk-score", scenario),
        "grade_assignment_state": configuration["grade_assignment_state"],
        "revocation_status_ref": _control_ref("revocation-status", scenario),
        "poisoning_defense_status_ref": _control_ref("poisoning-defense-status", scenario),
        "degradation_state": configuration["degradation_state"],
        "report_status_impact_ref": _control_ref("report-status-impact", scenario),
        "human_whitebox_review_state": "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
        "capture_state": "CONTROL_EVIDENCE_CAPTURE_REFERENCE_DECLARED_NOT_EXECUTED",
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


def _rejected_result() -> dict[str, Any]:
    """固定输入之外的内容保持在拒绝状态，且不产生投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_IN_MEMORY_EVIDENCE_GRADE_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "actual_input_request_count": 0,
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_retrieval_evidence_capture_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_evidence_capture_count": 0,
        "actual_risk_factor_evaluation_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_assignment_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_audit_log_write_count": 0,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _project(
    request: Mapping[str, Optional[str]],
) -> dict[str, dict[str, Optional[str]]]:
    scenario = str(request["control_scenario"])
    evidence_grade_schema_binding = {
        "phase1_evidence_grade_contract_ref": PHASE1_EVIDENCE_GRADE_CONTRACT_CONTROL_REF,
        "stage092_review_control_ref": STAGE092_REVIEW_CONTROL_REF,
        "evidence_grade_ref": request["evidence_grade_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "grade_assignment_state": request["grade_assignment_state"],
        "schema_binding_state": "CONTROL_PHASE1_EVIDENCE_GRADE_SHAPE_BOUND",
    }
    evidence_grade_relation = {
        field: request[field] for field in EVIDENCE_GRADE_RELATION_FIELDS
    }
    retrieval_evidence_capture_binding = {
        field: request[field] for field in RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS
    }
    risk_reference_binding = {
        field: request[field] for field in RISK_REFERENCE_BINDING_FIELDS
    }
    evidence_grade_assignment = {
        field: request[field] for field in EVIDENCE_GRADE_ASSIGNMENT_FIELDS
    }
    revocation = {
        "revocation_status_ref": request["revocation_status_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "affected_fact_ref": request["fact_id_ref"],
        "affected_report_ref": request["report_id_ref"],
        "recovery_state_ref": _control_ref("recovery-state", scenario),
        "report_status_impact_ref": request["report_status_impact_ref"],
        "revocation_state": "CONTROL_REVOCATION_ROUTE_DECLARED",
    }
    poisoning_defense = {
        "poisoning_defense_status_ref": request["poisoning_defense_status_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "source_provenance_indicator_ref": request["source_provenance_indicator_ref"],
        "conflict_status_indicator_ref": request["conflict_status_indicator_ref"],
        "anomaly_indicator_ref": _control_ref("anomaly-indicator", scenario),
        "human_whitebox_review_state": request["human_whitebox_review_state"],
        "defense_state": "CONTROL_POISONING_DEFENSE_ROUTE_DECLARED",
    }
    critical_conclusion_binding = {
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "risk_score_ref": request["risk_score_ref"],
        "revocation_status_ref": request["revocation_status_ref"],
        "conclusion_binding_state": "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP",
    }
    degradation = {field: request[field] for field in DEGRADATION_FIELDS}
    report_status_impact = {
        "report_id_ref": request["report_id_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "revocation_status_ref": request["revocation_status_ref"],
        "risk_score_ref": request["risk_score_ref"],
        "report_status_impact_ref": request["report_status_impact_ref"],
        "report_status_impact_state": CONTROL_SCENARIO_CONFIGURATION[scenario][
            "report_status_impact_state"
        ],
        "human_whitebox_review_state": request["human_whitebox_review_state"],
    }
    future_integration = {
        "phase1_evidence_grade_route_ref": PHASE1_EVIDENCE_GRADE_CONTRACT_CONTROL_REF,
        "stage092_evidence_risk_scoring_route_ref": STAGE092_REVIEW_CONTROL_REF,
        "evidence_ledger_capture_route_ref": _control_ref(
            "evidence-ledger-capture-route", scenario
        ),
        "evidence_grade_assignment_route_ref": _control_ref(
            "evidence-grade-assignment-route", scenario
        ),
        "risk_scoring_route_ref": _control_ref("risk-scoring-route", scenario),
        "revocation_route_ref": _control_ref("revocation-route", scenario),
        "poisoning_defense_route_ref": _control_ref(
            "poisoning-defense-route", scenario
        ),
        "report_status_update_route_ref": _control_ref(
            "report-status-update-route", scenario
        ),
    }
    return {
        "evidence_grade_schema_binding": evidence_grade_schema_binding,
        "evidence_grade_relation": evidence_grade_relation,
        "retrieval_evidence_capture_binding": retrieval_evidence_capture_binding,
        "risk_reference_binding": risk_reference_binding,
        "evidence_grade_assignment": evidence_grade_assignment,
        "revocation": revocation,
        "poisoning_defense": poisoning_defense,
        "critical_conclusion_binding": critical_conclusion_binding,
        "degradation": degradation,
        "report_status_impact": report_status_impact,
        "future_integration": future_integration,
    }


def execute_evidence_grade_control_slice(
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
        "execution_state": "CONTROL_EVIDENCE_GRADE_PROJECTIONS_DECLARED",
        "failure_state": None,
        "control_input_count": len(requests),
        "actual_input_request_count": 0,
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_retrieval_evidence_capture_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_evidence_capture_count": 0,
        "actual_risk_factor_evaluation_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_assignment_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_audit_log_write_count": 0,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **projections,
    }
