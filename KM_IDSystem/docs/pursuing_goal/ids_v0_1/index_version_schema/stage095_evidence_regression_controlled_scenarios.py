"""Stage095 P3 的纯内存证据回归异常场景验证。

模块只重放 Stage095 P2 的固定、非业务、reference-only 控制投影。它不读取
来源资料、检索结果或真实证据账本，不连接数据库，不计算真实风险，不改变证据
等级，不执行撤回、降级、投毒处置或报告状态更新，也不写入持久化记录。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage095.evidence_regression.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EVIDENCE_REGRESSION_EXCEPTION_SCENARIOS"
PASS_RESULT = "PASS_EVIDENCE_REGRESSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EVIDENCE_REGRESSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CURRENT_GATE = "IDS-STAGE095-P3-GATE"
NEXT_GATE = "IDS-STAGE095-P4-GATE"
P2_EXECUTION_STATE = "CONTROL_EVIDENCE_REGRESSION_PROJECTIONS_DECLARED"
CONTROL_PREFIX = ":control:stage095-p2:"
P2_CONTROL_SCENARIOS = (
    "internal_material_insufficient_evidence_gap_reference_only",
    "low_ocr_evidence_degradation_reference_only",
    "old_version_evidence_degradation_reference_only",
    "conflict_evidence_degradation_reference_only",
    "revoked_evidence_report_review_reference_only",
    "suspected_poisoning_evidence_quarantined_reference_only",
)
P2_PROJECTION_SPECS = (
    (
        "evidence_regression_schema_binding",
        "EVIDENCE_REGRESSION_SCHEMA_BINDING_FIELDS",
    ),
    ("evidence_regression_relation", "EVIDENCE_REGRESSION_RELATION_FIELDS"),
    (
        "retrieval_evidence_capture_binding",
        "RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS",
    ),
    (
        "risk_and_evidence_grade_control",
        "RISK_AND_EVIDENCE_GRADE_CONTROL_FIELDS",
    ),
    (
        "revocation_and_poisoning_control",
        "REVOCATION_AND_POISONING_CONTROL_FIELDS",
    ),
    (
        "critical_conclusion_and_report_impact",
        "CRITICAL_CONCLUSION_AND_REPORT_IMPACT_FIELDS",
    ),
)
P2_ZERO_COUNTER_FIELDS = (
    "actual_input_request_count",
    "actual_evidence_regression_execution_count",
    "actual_retrieval_execution_count",
    "actual_retrieval_evidence_capture_count",
    "actual_evidence_ledger_access_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_degradation_execution_count",
    "actual_recovery_execution_count",
    "actual_poisoning_defense_execution_count",
    "actual_report_status_update_count",
    "actual_audit_log_write_count",
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
SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "evidence_id_ref",
    "evidence_gap_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "evidence_ledger_ref",
    "risk_score_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "revocation_status_ref",
    "poisoning_defense_status_ref",
    "critical_conclusion_ref",
    "retrieval_capture_state",
    "risk_assessment_state",
    "source_report_status_impact_state",
    "report_status_impact_state",
    "degradation_state",
    "control_action_state",
    "evidence_disposition_state",
    "conclusion_acceptance_state",
    "high_trust_conclusion_allowed",
    "human_whitebox_review_state",
    "business_line_whitebox_human_approval_recorded",
    "actual_report_status_updated",
    "human_handling_required",
    "expectation_met",
)
SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "no_internal_evidence_regression_control",
        "scenario_category": "NO_INTERNAL_EVIDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_evidence_id_present": False,
        "expected_grade": "E",
        "expected_degradation_state": "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
        "expected_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW"
        ),
        "expected_control_action_state": (
            "CONTROL_EVIDENCE_GAP_REFERENCE_PENDING_WHITEBOX_REVIEW"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_NO_INTERNAL_EVIDENCE_REQUIRES_GAP_AND_WHITEBOX_REVIEW"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "low_ocr_evidence_regression_degradation_control",
        "scenario_category": "LOW_OCR_EVIDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_evidence_id_present": True,
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
        "expected_report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_OCR",
        "expected_control_action_state": "CONTROL_LOW_OCR_DEGRADATION_REFERENCE_NOT_EXECUTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW",
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "old_version_evidence_regression_degradation_control",
        "scenario_category": "OLD_VERSION_EVIDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_evidence_id_present": True,
        "expected_grade": "C",
        "expected_degradation_state": "CONTROL_DEGRADED_OLD_VERSION_NOT_ACCEPTED",
        "expected_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_OLD_VERSION"
        ),
        "expected_control_action_state": (
            "CONTROL_OLD_VERSION_DEGRADATION_REFERENCE_NOT_EXECUTED"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW",
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "conflict_evidence_regression_degradation_control",
        "scenario_category": "CONFLICT_EVIDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_evidence_id_present": True,
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        "expected_report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
        "expected_control_action_state": "CONTROL_CONFLICT_DEGRADATION_REFERENCE_NOT_EXECUTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW",
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "revoked_evidence_report_impact_control",
        "scenario_category": "REVOKED_EVIDENCE_REPORT_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_evidence_id_present": True,
        "expected_grade": "E",
        "expected_degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        "expected_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_REVOKED_PENDING_WHITEBOX_REVIEW"
        ),
        "expected_control_action_state": "CONTROL_REVOCATION_REFERENCE_NOT_EXECUTED",
        "report_status_impact_state": (
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        ),
        "evidence_disposition_state": "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW",
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "malicious_evidence_regression_quarantine_control",
        "scenario_category": "MALICIOUS_EVIDENCE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[5],
        "expected_evidence_id_present": True,
        "expected_grade": "E",
        "expected_degradation_state": (
            "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED"
        ),
        "expected_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING"
        ),
        "expected_control_action_state": "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED"
        ),
        "conclusion_acceptance_state": "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW",
        "high_trust_conclusion_allowed": False,
    },
    {
        "scenario_id": "low_grade_high_trust_masquerade_control",
        "scenario_category": "LOW_GRADE_MASQUERADE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_evidence_id_present": True,
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
        "expected_report_status_impact_state": "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_OCR",
        "expected_control_action_state": "CONTROL_LOW_OCR_DEGRADATION_REFERENCE_NOT_EXECUTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_LOW_GRADE_EVIDENCE_CANNOT_MASQUERADE_AS_HIGH_TRUST"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
        ),
        "high_trust_conclusion_allowed": False,
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage095_evidence_regression_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage095_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage095 P2 evidence regression slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _control_ref(value: object) -> bool:
    return isinstance(value, str) and value.startswith(CONTROL_PREFIX)


def _phase2_records(
    result: Mapping[str, Any], scenario: str
) -> dict[str, Mapping[str, Any]] | None:
    try:
        index = P2_CONTROL_SCENARIOS.index(scenario)
    except ValueError:
        return None
    records: dict[str, Mapping[str, Any]] = {}
    for prefix, _field_constant in P2_PROJECTION_SPECS:
        projection = result.get(f"{prefix}_control_projections")
        if not isinstance(projection, list) or len(projection) != len(
            P2_CONTROL_SCENARIOS
        ):
            return None
        record = projection[index]
        if not isinstance(record, Mapping):
            return None
        records[prefix] = record
    return records


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    projection_names = tuple(prefix for prefix, _field_constant in P2_PROJECTION_SPECS)
    phase2_projection_names = tuple(
        item[0]
        for item in getattr(phase2_module, "PROJECTION_FIELDS", ())
        if isinstance(item, tuple) and len(item) == 2
    )
    if (
        result.get("schema_version") != getattr(phase2_module, "SCHEMA_VERSION", None)
        or result.get("record_kind") != getattr(phase2_module, "RECORD_KIND", None)
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or getattr(phase2_module, "CONTROL_PREFIX", None) != CONTROL_PREFIX
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
        != ("evidence_regression_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != 21
        or phase2_projection_names != projection_names
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("control_input_count") != len(P2_CONTROL_SCENARIOS)
        or result.get("persistent_record_created") is not False
    ):
        return False
    for prefix, field_constant in P2_PROJECTION_SPECS:
        fields = getattr(phase2_module, field_constant, ())
        records = result.get(f"{prefix}_control_projections")
        if (
            not isinstance(records, list)
            or len(records) != len(P2_CONTROL_SCENARIOS)
            or result.get(f"{prefix}_control_projection_count")
            != len(P2_CONTROL_SCENARIOS)
            or any(
                not isinstance(record, Mapping) or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return True


def _phase2_runtime_is_closed(result: Mapping[str, Any]) -> bool:
    if any(result.get(field) != 0 for field in P2_ZERO_COUNTER_FIELDS):
        return False
    boundary = result.get("runtime_boundary")
    return isinstance(boundary, Mapping) and all(
        boundary.get(field) is False for field in RUNTIME_CLOSED_FIELDS
    ) and all(value is False for value in boundary.values())


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for scenario in P2_CONTROL_SCENARIOS:
        records = _phase2_records(result, scenario)
        if records is None:
            return False
        for record in records.values():
            for field, value in record.items():
                if field.endswith("_ref") and value is not None and not _control_ref(value):
                    return False
    return True


def _phase2_semantic_failure(result: Mapping[str, Any]) -> str | None:
    records_by_scenario = {
        scenario: _phase2_records(result, scenario) for scenario in P2_CONTROL_SCENARIOS
    }
    if any(records is None for records in records_by_scenario.values()):
        return "PHASE2_CONTROL_SHAPE_MISMATCH"

    for records in records_by_scenario.values():
        assert records is not None
        relation = records["evidence_regression_relation"]
        risk = records["risk_and_evidence_grade_control"]
        revocation = records["revocation_and_poisoning_control"]
        conclusion = records["critical_conclusion_and_report_impact"]
        if (
            conclusion.get("evidence_id_ref") is None
            and conclusion.get("evidence_gap_ref") is None
        ) or conclusion.get("conclusion_binding_state") != (
            "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        ):
            return "CRITICAL_CONCLUSION_BINDING_MISSING"
        if any(
            not _control_ref(relation.get(field))
            for field in (
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
            )
        ):
            return "CRITICAL_CONCLUSION_BINDING_MISSING"
        if any(
            record.get("human_whitebox_review_state")
            != "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED"
            for record in (risk, revocation, conclusion)
        ):
            return "HUMAN_WHITEBOX_REVIEW_REQUIRED"

    no_internal = records_by_scenario[P2_CONTROL_SCENARIOS[0]]
    assert no_internal is not None
    no_internal_schema = no_internal["evidence_regression_schema_binding"]
    if (
        no_internal_schema.get("evidence_id_ref") is not None
        or not _control_ref(no_internal_schema.get("evidence_gap_ref"))
    ):
        return "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING"

    failure_by_scenario = (
        (
            P2_CONTROL_SCENARIOS[1],
            "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
            "LOW_OCR_EVIDENCE_NOT_DEGRADED",
        ),
        (
            P2_CONTROL_SCENARIOS[2],
            "CONTROL_DEGRADED_OLD_VERSION_NOT_ACCEPTED",
            "OLD_VERSION_EVIDENCE_NOT_DEGRADED",
        ),
        (
            P2_CONTROL_SCENARIOS[3],
            "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
            "CONFLICT_EVIDENCE_NOT_DEGRADED",
        ),
        (
            P2_CONTROL_SCENARIOS[4],
            "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
            "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
        ),
        (
            P2_CONTROL_SCENARIOS[5],
            "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
            "MALICIOUS_EVIDENCE_NOT_QUARANTINED",
        ),
    )
    for scenario, expected_state, failure_state in failure_by_scenario:
        records = records_by_scenario[scenario]
        assert records is not None
        risk = records["risk_and_evidence_grade_control"]
        if risk.get("degradation_state") != expected_state:
            return failure_state

    revoked = records_by_scenario[P2_CONTROL_SCENARIOS[4]]
    assert revoked is not None
    if revoked["critical_conclusion_and_report_impact"].get(
        "report_status_impact_state"
    ) != "CONTROL_REPORT_STATUS_REFERENCE_REVOKED_PENDING_WHITEBOX_REVIEW":
        return "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING"

    low_ocr = records_by_scenario[P2_CONTROL_SCENARIOS[1]]
    assert low_ocr is not None
    if (
        low_ocr["risk_and_evidence_grade_control"].get("evidence_grade_label")
        != "D"
        or "evidence-grade-D" not in str(
            low_ocr["critical_conclusion_and_report_impact"].get(
                "evidence_grade_ref"
            )
        )
    ):
        return "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_TRUST"
    return None


def _scenario_expectation_met(
    definition: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> bool:
    schema = records["evidence_regression_schema_binding"]
    relation = records["evidence_regression_relation"]
    capture = records["retrieval_evidence_capture_binding"]
    risk = records["risk_and_evidence_grade_control"]
    revocation = records["revocation_and_poisoning_control"]
    conclusion = records["critical_conclusion_and_report_impact"]
    evidence_id_valid = (
        _control_ref(schema.get("evidence_id_ref"))
        if definition["expected_evidence_id_present"]
        else schema.get("evidence_id_ref") is None
    )
    evidence_gap_valid = (
        schema.get("evidence_gap_ref") is None
        if definition["expected_evidence_id_present"]
        else _control_ref(schema.get("evidence_gap_ref"))
    )
    return (
        evidence_id_valid
        and evidence_gap_valid
        and all(
            _control_ref(relation.get(field))
            for field in (
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
            )
        )
        and capture.get("capture_state")
        == "CONTROL_EVIDENCE_CAPTURE_REFERENCE_DECLARED_NOT_EXECUTED"
        and risk.get("risk_assessment_state")
        == "CONTROL_RISK_REFERENCE_OWNER_FORMULA_REQUIRED_NOT_CALCULATED"
        and risk.get("evidence_grade_label") == definition["expected_grade"]
        and risk.get("degradation_state") == definition["expected_degradation_state"]
        and revocation.get("control_action_state")
        == definition["expected_control_action_state"]
        and conclusion.get("report_status_impact_state")
        == definition["expected_report_status_impact_state"]
        and conclusion.get("conclusion_binding_state")
        == "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        and conclusion.get("human_whitebox_review_state")
        == "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED"
    )


def _build_scenario(
    definition: Mapping[str, Any], phase2_result: Mapping[str, Any]
) -> dict[str, Any]:
    records = _phase2_records(phase2_result, definition["phase2_control_scenario"])
    if records is None:
        raise ValueError("Phase2 control records are unavailable")
    schema = records["evidence_regression_schema_binding"]
    relation = records["evidence_regression_relation"]
    capture = records["retrieval_evidence_capture_binding"]
    risk = records["risk_and_evidence_grade_control"]
    revocation = records["revocation_and_poisoning_control"]
    conclusion = records["critical_conclusion_and_report_impact"]
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "evidence_id_ref": schema["evidence_id_ref"],
        "evidence_gap_ref": schema["evidence_gap_ref"],
        "document_id_ref": relation["document_id_ref"],
        "chunk_id_ref": relation["chunk_id_ref"],
        "fact_id_ref": relation["fact_id_ref"],
        "query_ref": relation["query_ref"],
        "answer_ref": relation["answer_ref"],
        "report_id_ref": relation["report_id_ref"],
        "evidence_ledger_ref": relation["evidence_ledger_ref"],
        "risk_score_ref": relation["risk_score_ref"],
        "evidence_grade_ref": conclusion["evidence_grade_ref"],
        "evidence_grade_label": risk["evidence_grade_label"],
        "revocation_status_ref": relation["revocation_status_ref"],
        "poisoning_defense_status_ref": relation["poisoning_defense_status_ref"],
        "critical_conclusion_ref": conclusion["critical_conclusion_ref"],
        "retrieval_capture_state": capture["capture_state"],
        "risk_assessment_state": risk["risk_assessment_state"],
        "source_report_status_impact_state": conclusion[
            "report_status_impact_state"
        ],
        "report_status_impact_state": definition["report_status_impact_state"],
        "degradation_state": risk["degradation_state"],
        "control_action_state": revocation["control_action_state"],
        "evidence_disposition_state": definition["evidence_disposition_state"],
        "conclusion_acceptance_state": definition["conclusion_acceptance_state"],
        "high_trust_conclusion_allowed": definition[
            "high_trust_conclusion_allowed"
        ],
        "human_whitebox_review_state": conclusion["human_whitebox_review_state"],
        "business_line_whitebox_human_approval_recorded": False,
        "actual_report_status_updated": False,
        "human_handling_required": True,
        "expectation_met": _scenario_expectation_met(definition, records),
    }


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
        "second_authoritative_source_created": False,
        "actual_evidence_regression_execution_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_degradation_execution_count": 0,
        "actual_recovery_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }


def build_evidence_regression_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制投影并验证 Stage095 P3 固定异常场景。"""

    try:
        phase2_module = _load_phase2_module()
        executor = (
            phase2_executor
            or phase2_module.execute_evidence_regression_control_slice
        )
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
        "second_authoritative_source_created": False,
        "actual_evidence_regression_execution_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_revocation_execution_count": 0,
        "actual_degradation_execution_count": 0,
        "actual_recovery_execution_count": 0,
        "actual_poisoning_defense_execution_count": 0,
        "actual_report_status_update_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }
