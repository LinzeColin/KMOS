"""Stage090 P2 的纯内存检索证据捕获控制切片。

本模块只投影自身定义的固定、非业务、reference-only 控制输入。它只绑定
前序 evidence schema 合同，不读取资料、检索结果或真实证据账本，不连接
数据库，不计算真实风险分数，不执行撤回或投毒处置，也不写入持久化记录。
"""

from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage090.retrieval_evidence_capture.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_EVIDENCE_CAPTURE"
CONTROL_ADAPTER_VERSION = "ids.retrieval_evidence_capture.control_adapter.v0_1.stage090.p2"
CONTROL_PREFIX = ":control:stage090-p2:"
CONTROL_FIELDS = ("retrieval_evidence_capture_control_requests",)
PREDECESSOR_SCHEMA_CONTRACT_CONTROL_REF = (
    ":control:stage090-p2:stage089-evidence-schema-contract:reference-only"
)

EVIDENCE_SCHEMA_BINDING_FIELDS = (
    "predecessor_evidence_schema_contract_ref",
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "schema_binding_state",
)
RETRIEVAL_CAPTURE_FIELDS = (
    "retrieval_trace_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "source_type_ref",
    "source_version_ref",
    "capture_request_state",
)
EVIDENCE_LEDGER_CAPTURE_FIELDS = (
    "evidence_capture_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "risk_score_ref",
    "revocation_state_ref",
    "poisoning_defense_state_ref",
    "critical_conclusion_ref",
    "capture_state",
)
CAPTURE_RELATION_FIELDS = (
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
)
RISK_SCORE_FIELDS = (
    "risk_score_ref",
    "evidence_id_ref",
    "evidence_grade_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "ocr_quality_indicator_ref",
    "revocation_state_ref",
    "risk_state",
)
REVOCATION_FIELDS = (
    "revocation_state_ref",
    "evidence_id_ref",
    "revocation_reason_ref",
    "affected_fact_ref",
    "affected_report_ref",
    "recovery_state_ref",
    "revocation_state",
)
POISONING_DEFENSE_FIELDS = (
    "poisoning_defense_state_ref",
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
    "revocation_state_ref",
    "poisoning_defense_state_ref",
    "degradation_state",
)
FUTURE_INTEGRATION_FIELDS = (
    "predecessor_evidence_schema_route_ref",
    "retrieval_evidence_capture_route_ref",
    "risk_scoring_route_ref",
    "revocation_route_ref",
    "poisoning_defense_route_ref",
    "report_status_update_route_ref",
    "integration_state",
)
INPUT_FIELDS = (
    "control_scenario",
    "retrieval_trace_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "source_type_ref",
    "source_version_ref",
    "capture_request_state",
    "evidence_capture_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "risk_score_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "ocr_quality_indicator_ref",
    "revocation_state_ref",
    "poisoning_defense_state_ref",
    "critical_conclusion_ref",
    "human_whitebox_review_state",
    "capture_state",
    "degradation_state",
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
    ("evidence_schema_binding", EVIDENCE_SCHEMA_BINDING_FIELDS),
    ("retrieval_capture", RETRIEVAL_CAPTURE_FIELDS),
    ("evidence_ledger_capture", EVIDENCE_LEDGER_CAPTURE_FIELDS),
    ("capture_relation", CAPTURE_RELATION_FIELDS),
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
    """构造一条不包含业务事实的固定检索证据捕获控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    grade = configuration["evidence_grade_label"]
    return {
        "control_scenario": scenario,
        "retrieval_trace_ref": _control_ref("retrieval-trace", scenario),
        "query_ref": _control_ref("query", scenario),
        "answer_ref": _control_ref("answer", scenario),
        "report_id_ref": _control_ref("report", scenario),
        "document_id_ref": _control_ref("document", scenario),
        "chunk_id_ref": _control_ref("chunk", scenario),
        "fact_id_ref": _control_ref("fact", scenario),
        "source_type_ref": _control_ref("source-type", scenario),
        "source_version_ref": _control_ref("source-version", scenario),
        "capture_request_state": "CONTROL_CAPTURE_REQUEST_DECLARED_NOT_EXECUTED",
        "evidence_capture_ref": _control_ref("evidence-capture", scenario),
        "evidence_id_ref": _control_ref("evidence", scenario),
        "evidence_gap_ref": _control_ref("evidence-gap", scenario),
        "evidence_grade_ref": _control_ref(f"evidence-grade-{grade}", scenario),
        "evidence_grade_label": grade,
        "risk_score_ref": _control_ref("risk-score", scenario),
        "conflict_indicator_ref": _control_ref("conflict-indicator", scenario),
        "freshness_indicator_ref": _control_ref("freshness-indicator", scenario),
        "ocr_quality_indicator_ref": _control_ref("ocr-quality-indicator", scenario),
        "revocation_state_ref": _control_ref("revocation-state", scenario),
        "poisoning_defense_state_ref": _control_ref(
            "poisoning-defense-state", scenario
        ),
        "critical_conclusion_ref": _control_ref("critical-conclusion", scenario),
        "human_whitebox_review_state": "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
        "capture_state": "CONTROL_EVIDENCE_CAPTURE_DECLARED_NOT_EXECUTED",
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
        "execution_state": "REJECTED_IN_MEMORY_RETRIEVAL_EVIDENCE_CAPTURE_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "actual_input_request_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_retrieval_evidence_capture_count": 0,
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
    evidence_schema_binding = {
        "predecessor_evidence_schema_contract_ref": PREDECESSOR_SCHEMA_CONTRACT_CONTROL_REF,
        "evidence_id_ref": request["evidence_id_ref"],
        "document_id_ref": request["document_id_ref"],
        "chunk_id_ref": request["chunk_id_ref"],
        "fact_id_ref": request["fact_id_ref"],
        "schema_binding_state": "CONTROL_PREDECESSOR_SCHEMA_BOUND_NOT_REDEFINED",
    }
    retrieval_capture = {
        field: request[field] for field in RETRIEVAL_CAPTURE_FIELDS
    }
    evidence_ledger_capture = {
        field: request[field] for field in EVIDENCE_LEDGER_CAPTURE_FIELDS
    }
    capture_relation = {field: request[field] for field in CAPTURE_RELATION_FIELDS}
    risk_score = {
        "risk_score_ref": request["risk_score_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "conflict_indicator_ref": request["conflict_indicator_ref"],
        "freshness_indicator_ref": request["freshness_indicator_ref"],
        "ocr_quality_indicator_ref": request["ocr_quality_indicator_ref"],
        "revocation_state_ref": request["revocation_state_ref"],
        "risk_state": "CONTROL_RISK_REFERENCE_DECLARED_NOT_CALCULATED",
    }
    revocation = {
        "revocation_state_ref": request["revocation_state_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "revocation_reason_ref": _control_ref("revocation-reason", scenario),
        "affected_fact_ref": request["fact_id_ref"],
        "affected_report_ref": request["report_id_ref"],
        "recovery_state_ref": _control_ref("recovery-state", scenario),
        "revocation_state": "CONTROL_REVOCATION_ROUTE_NOT_EXECUTED",
    }
    poisoning_defense = {
        "poisoning_defense_state_ref": request["poisoning_defense_state_ref"],
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
        "revocation_state_ref": request["revocation_state_ref"],
        "conclusion_binding_state": "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP",
    }
    degradation = {
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_grade_label": request["evidence_grade_label"],
        "risk_score_ref": request["risk_score_ref"],
        "conflict_indicator_ref": request["conflict_indicator_ref"],
        "freshness_indicator_ref": request["freshness_indicator_ref"],
        "revocation_state_ref": request["revocation_state_ref"],
        "poisoning_defense_state_ref": request["poisoning_defense_state_ref"],
        "degradation_state": request["degradation_state"],
    }
    future_integration = {
        "predecessor_evidence_schema_route_ref": PREDECESSOR_SCHEMA_CONTRACT_CONTROL_REF,
        "retrieval_evidence_capture_route_ref": _control_ref(
            "retrieval-evidence-capture-route", scenario
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
        "evidence_schema_binding": evidence_schema_binding,
        "retrieval_capture": retrieval_capture,
        "evidence_ledger_capture": evidence_ledger_capture,
        "capture_relation": capture_relation,
        "risk_score": risk_score,
        "revocation": revocation,
        "poisoning_defense": poisoning_defense,
        "critical_conclusion_binding": critical_conclusion_binding,
        "degradation": degradation,
        "future_integration": future_integration,
    }


def execute_retrieval_evidence_capture_control_slice(
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
        "execution_state": "CONTROL_RETRIEVAL_EVIDENCE_CAPTURE_PROJECTIONS_DECLARED_NOT_EXECUTED",
        "failure_state": None,
        "control_input_count": len(requests),
        "actual_input_request_count": 0,
        "actual_retrieval_execution_count": 0,
        "actual_retrieval_evidence_capture_count": 0,
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
