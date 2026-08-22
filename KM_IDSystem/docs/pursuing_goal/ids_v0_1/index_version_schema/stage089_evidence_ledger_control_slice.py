"""Stage089 P2 的纯内存证据账本控制切片。

本模块只投影自身定义的固定、非业务、reference-only 控制输入。它不读取
资料或真实证据账本，不连接数据库，不计算真实风险分数，不执行撤回或投毒
处置，也不写入任何持久化记录。
"""

from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage089.evidence_ledger_schema.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EVIDENCE_LEDGER_SCHEMA"
CONTROL_ADAPTER_VERSION = "ids.evidence_ledger.control_adapter.v0_1.stage089.p2"
CONTROL_PREFIX = ":control:stage089-p2:"
CONTROL_FIELDS = ("evidence_ledger_control_requests",)

EVIDENCE_SCHEMA_FIELDS = (
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "report_id_ref",
    "source_type_ref",
    "evidence_grade_ref",
    "source_version_ref",
    "retrieval_trace_ref",
    "evidence_state",
)
EVIDENCE_RELATION_FIELDS = (
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "relation_state",
)
EVIDENCE_GAP_FIELDS = (
    "evidence_gap_ref",
    "critical_conclusion_ref",
    "missing_evidence_dimension_ref",
    "gap_reason_ref",
    "gap_state",
)
EVIDENCE_CAPTURE_FIELDS = (
    "capture_ref",
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "retrieval_trace_ref",
    "capture_state",
)
RISK_SCORE_FIELDS = (
    "risk_score_ref",
    "evidence_id_ref",
    "evidence_grade_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "ocr_quality_indicator_ref",
    "revocation_indicator_ref",
    "risk_state",
)
REVOCATION_FIELDS = (
    "revocation_ref",
    "evidence_id_ref",
    "revocation_reason_ref",
    "affected_fact_ref",
    "affected_report_ref",
    "revocation_state",
    "recovery_state",
)
POISONING_DEFENSE_FIELDS = (
    "poisoning_defense_ref",
    "evidence_id_ref",
    "source_provenance_ref",
    "conflict_indicator_ref",
    "anomaly_indicator_ref",
    "quarantine_state",
    "human_whitebox_review_state",
    "defense_state",
)
CRITICAL_CONCLUSION_BINDING_FIELDS = (
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "risk_score_ref",
    "revocation_state_ref",
    "conclusion_binding_state",
)
DEGRADATION_FIELDS = (
    "evidence_id_ref",
    "evidence_grade_label",
    "risk_score_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "revocation_ref",
    "poisoning_defense_ref",
    "degradation_state",
)
FUTURE_INTEGRATION_FIELDS = (
    "evidence_schema_route_ref",
    "retrieval_evidence_capture_route_ref",
    "risk_scoring_route_ref",
    "revocation_route_ref",
    "poisoning_defense_route_ref",
    "report_status_update_route_ref",
    "integration_state",
)
INPUT_FIELDS = (
    "control_scenario",
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "source_type_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "source_version_ref",
    "retrieval_trace_ref",
    "evidence_gap_ref",
    "risk_score_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "ocr_quality_indicator_ref",
    "revocation_ref",
    "poisoning_defense_ref",
    "critical_conclusion_ref",
    "human_whitebox_review_state",
    "evidence_state",
    "degradation_state",
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "retrieval_evidence_capture_performed",
    "risk_score_calculation_performed",
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
    "grade_a_pending_whitebox_review_reference_only",
    "low_grade_evidence_degraded_reference_only",
    "conflict_evidence_degraded_reference_only",
    "expired_evidence_degraded_reference_only",
    "revoked_evidence_degraded_reference_only",
    "suspected_poisoning_quarantined_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "grade_a_pending_whitebox_review_reference_only": {
        "evidence_grade_label": "A",
        "degradation_state": "CONTROL_PENDING_HUMAN_WHITEBOX_REVIEW",
    },
    "low_grade_evidence_degraded_reference_only": {
        "evidence_grade_label": "D",
        "degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
    },
    "conflict_evidence_degraded_reference_only": {
        "evidence_grade_label": "B",
        "degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
    },
    "expired_evidence_degraded_reference_only": {
        "evidence_grade_label": "C",
        "degradation_state": "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
    },
    "revoked_evidence_degraded_reference_only": {
        "evidence_grade_label": "A",
        "degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
    },
    "suspected_poisoning_quarantined_reference_only": {
        "evidence_grade_label": "E",
        "degradation_state": "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
    },
}
PROJECTION_FIELDS = (
    ("evidence_schema", EVIDENCE_SCHEMA_FIELDS),
    ("evidence_relation", EVIDENCE_RELATION_FIELDS),
    ("evidence_gap", EVIDENCE_GAP_FIELDS),
    ("evidence_capture", EVIDENCE_CAPTURE_FIELDS),
    ("risk_score", RISK_SCORE_FIELDS),
    ("revocation", REVOCATION_FIELDS),
    ("poisoning_defense", POISONING_DEFENSE_FIELDS),
    ("critical_conclusion_binding", CRITICAL_CONCLUSION_BINDING_FIELDS),
    ("degradation", DEGRADATION_FIELDS),
    ("future_integration", FUTURE_INTEGRATION_FIELDS),
)


def _marker(scenario: str) -> str:
    return f"{CONTROL_PREFIX}{scenario}:reference-only"


def _control_ref(kind: str, scenario: str) -> str:
    return f"{kind}{_marker(scenario)}"


def _control_request(scenario: str) -> dict[str, str]:
    """构造一条不包含业务事实的固定控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    grade = configuration["evidence_grade_label"]
    return {
        "control_scenario": scenario,
        "evidence_id_ref": _control_ref("evidence", scenario),
        "document_id_ref": _control_ref("document", scenario),
        "chunk_id_ref": _control_ref("chunk", scenario),
        "fact_id_ref": _control_ref("fact", scenario),
        "query_ref": _control_ref("query", scenario),
        "answer_ref": _control_ref("answer", scenario),
        "report_id_ref": _control_ref("report", scenario),
        "source_type_ref": _control_ref("source-type", scenario),
        "evidence_grade_ref": _control_ref(f"evidence-grade-{grade}", scenario),
        "evidence_grade_label": grade,
        "source_version_ref": _control_ref("source-version", scenario),
        "retrieval_trace_ref": _control_ref("retrieval-trace", scenario),
        "evidence_gap_ref": _control_ref("evidence-gap", scenario),
        "risk_score_ref": _control_ref("risk-score", scenario),
        "conflict_indicator_ref": _control_ref("conflict-indicator", scenario),
        "freshness_indicator_ref": _control_ref("freshness-indicator", scenario),
        "ocr_quality_indicator_ref": _control_ref("ocr-quality-indicator", scenario),
        "revocation_ref": _control_ref("revocation", scenario),
        "poisoning_defense_ref": _control_ref("poisoning-defense", scenario),
        "critical_conclusion_ref": _control_ref("critical-conclusion", scenario),
        "human_whitebox_review_state": "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
        "evidence_state": "CONTROL_EVIDENCE_DECLARED_NOT_CAPTURED",
        "degradation_state": configuration["degradation_state"],
    }


def build_control_input() -> dict[str, list[dict[str, str]]]:
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
    """失败关闭：不读取输入内容，也不产生任何投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_IN_MEMORY_EVIDENCE_LEDGER_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "actual_input_request_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_evidence_capture_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_audit_log_write_count": 0,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _project(request: Mapping[str, str]) -> dict[str, dict[str, str]]:
    scenario = request["control_scenario"]
    evidence_schema = {field: request[field] for field in EVIDENCE_SCHEMA_FIELDS}
    evidence_relation = {
        "evidence_id_ref": request["evidence_id_ref"],
        "document_id_ref": request["document_id_ref"],
        "chunk_id_ref": request["chunk_id_ref"],
        "fact_id_ref": request["fact_id_ref"],
        "query_ref": request["query_ref"],
        "answer_ref": request["answer_ref"],
        "report_id_ref": request["report_id_ref"],
        "relation_state": "CONTROL_RELATION_DECLARED_NOT_PERSISTED",
    }
    evidence_gap = {
        "evidence_gap_ref": request["evidence_gap_ref"],
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "missing_evidence_dimension_ref": _control_ref(
            "missing-evidence-dimension", scenario
        ),
        "gap_reason_ref": _control_ref("evidence-gap-reason", scenario),
        "gap_state": "CONTROL_GAP_REFERENCE_DECLARED_NOT_EVALUATED",
    }
    evidence_capture = {
        "capture_ref": _control_ref("evidence-capture", scenario),
        "evidence_id_ref": request["evidence_id_ref"],
        "document_id_ref": request["document_id_ref"],
        "chunk_id_ref": request["chunk_id_ref"],
        "retrieval_trace_ref": request["retrieval_trace_ref"],
        "capture_state": "CONTROL_CAPTURE_ROUTE_DECLARED_NOT_EXECUTED",
    }
    risk_score = {
        "risk_score_ref": request["risk_score_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "conflict_indicator_ref": request["conflict_indicator_ref"],
        "freshness_indicator_ref": request["freshness_indicator_ref"],
        "ocr_quality_indicator_ref": request["ocr_quality_indicator_ref"],
        "revocation_indicator_ref": request["revocation_ref"],
        "risk_state": "CONTROL_RISK_REFERENCE_DECLARED_NOT_CALCULATED",
    }
    revocation = {
        "revocation_ref": request["revocation_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "revocation_reason_ref": _control_ref("revocation-reason", scenario),
        "affected_fact_ref": request["fact_id_ref"],
        "affected_report_ref": request["report_id_ref"],
        "revocation_state": "CONTROL_REVOCATION_REFERENCE_NOT_EXECUTED",
        "recovery_state": "CONTROL_RECOVERY_ROUTE_NOT_EXECUTED",
    }
    poisoning_defense = {
        "poisoning_defense_ref": request["poisoning_defense_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "source_provenance_ref": _control_ref("source-provenance", scenario),
        "conflict_indicator_ref": request["conflict_indicator_ref"],
        "anomaly_indicator_ref": _control_ref("anomaly-indicator", scenario),
        "quarantine_state": "CONTROL_QUARANTINE_ROUTE_NOT_EXECUTED",
        "human_whitebox_review_state": request["human_whitebox_review_state"],
        "defense_state": "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED",
    }
    critical_conclusion_binding = {
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "risk_score_ref": request["risk_score_ref"],
        "revocation_state_ref": _control_ref("revocation-state", scenario),
        "conclusion_binding_state": "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP",
    }
    degradation = {
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_grade_label": request["evidence_grade_label"],
        "risk_score_ref": request["risk_score_ref"],
        "conflict_indicator_ref": request["conflict_indicator_ref"],
        "freshness_indicator_ref": request["freshness_indicator_ref"],
        "revocation_ref": request["revocation_ref"],
        "poisoning_defense_ref": request["poisoning_defense_ref"],
        "degradation_state": request["degradation_state"],
    }
    future_integration = {
        "evidence_schema_route_ref": _control_ref("evidence-schema-route", scenario),
        "retrieval_evidence_capture_route_ref": _control_ref(
            "evidence-capture-route", scenario
        ),
        "risk_scoring_route_ref": _control_ref("risk-scoring-route", scenario),
        "revocation_route_ref": _control_ref("revocation-route", scenario),
        "poisoning_defense_route_ref": _control_ref(
            "poisoning-defense-route", scenario
        ),
        "report_status_update_route_ref": _control_ref(
            "report-status-update-route", scenario
        ),
        "integration_state": "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
    }
    return {
        "evidence_schema": evidence_schema,
        "evidence_relation": evidence_relation,
        "evidence_gap": evidence_gap,
        "evidence_capture": evidence_capture,
        "risk_score": risk_score,
        "revocation": revocation,
        "poisoning_defense": poisoning_defense,
        "critical_conclusion_binding": critical_conclusion_binding,
        "degradation": degradation,
        "future_integration": future_integration,
    }


def execute_evidence_ledger_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """投影固定控制引用；非固定输入一律失败关闭。"""

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
        "execution_state": "CONTROL_EVIDENCE_LEDGER_PROJECTIONS_DECLARED_NOT_EXECUTED",
        "failure_state": None,
        "control_input_count": len(requests),
        "actual_input_request_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_evidence_capture_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_audit_log_write_count": 0,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **projections,
    }
