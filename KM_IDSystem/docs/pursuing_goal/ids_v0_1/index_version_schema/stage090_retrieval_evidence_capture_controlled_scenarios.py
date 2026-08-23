"""Stage090 P3 的纯内存检索证据捕获异常场景控制验证。

模块重放 Stage090 P2 的六条固定、非业务、reference-only 控制投影。
场景由控制标签表达，来源文档、真实证据账本、报告、数据库与运行时保持原状。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage090.retrieval_evidence_capture.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_EVIDENCE_CAPTURE_EXCEPTION_SCENARIOS"
PASS_RESULT = "PASS_RETRIEVAL_EVIDENCE_CAPTURE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_RETRIEVAL_EVIDENCE_CAPTURE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CURRENT_GATE = "IDS-STAGE090-P3-GATE"
NEXT_GATE = "IDS-STAGE090-P4-GATE"
P2_EXECUTION_STATE = (
    "CONTROL_RETRIEVAL_EVIDENCE_CAPTURE_PROJECTIONS_DECLARED_NOT_EXECUTED"
)
CONTROL_PREFIX = ":control:stage090-p2:"
P2_CONTROL_SCENARIOS = (
    "grade_a_pending_whitebox_review_reference_only",
    "low_grade_evidence_degraded_reference_only",
    "conflict_evidence_degraded_reference_only",
    "expired_evidence_degraded_reference_only",
    "revoked_evidence_degraded_reference_only",
    "suspected_poisoning_quarantined_reference_only",
)
P2_PROJECTION_SPECS = (
    ("evidence_schema_binding", "EVIDENCE_SCHEMA_BINDING_FIELDS"),
    ("retrieval_capture", "RETRIEVAL_CAPTURE_FIELDS"),
    ("evidence_ledger_capture", "EVIDENCE_LEDGER_CAPTURE_FIELDS"),
    ("capture_relation", "CAPTURE_RELATION_FIELDS"),
    ("risk_score", "RISK_SCORE_FIELDS"),
    ("revocation", "REVOCATION_FIELDS"),
    ("poisoning_defense", "POISONING_DEFENSE_FIELDS"),
    ("critical_conclusion_binding", "CRITICAL_CONCLUSION_BINDING_FIELDS"),
    ("degradation", "DEGRADATION_FIELDS"),
    ("future_integration", "FUTURE_INTEGRATION_FIELDS"),
)
P2_ZERO_COUNTER_FIELDS = (
    "actual_input_request_count",
    "actual_retrieval_execution_count",
    "actual_retrieval_evidence_capture_count",
    "actual_evidence_ledger_access_count",
    "actual_evidence_capture_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_poisoning_defense_execution_count",
    "actual_report_status_update_count",
    "actual_audit_log_write_count",
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
SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "source_version_ref",
    "ocr_quality_indicator_ref",
    "conflict_indicator_ref",
    "freshness_indicator_ref",
    "revocation_ref",
    "poisoning_defense_ref",
    "critical_conclusion_ref",
    "report_status_impact_ref",
    "report_status_impact_state",
    "evidence_disposition_state",
    "conclusion_acceptance_state",
    "human_whitebox_review_state",
    "business_line_whitebox_human_approval_recorded",
    "actual_report_status_updated",
    "actual_evidence_grade_changed",
    "human_handling_required",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)
SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "no_internal_evidence_gap_control",
        "scenario_category": "NO_INTERNAL_EVIDENCE_CONTROL",
        "phase2_control_scenario": "grade_a_pending_whitebox_review_reference_only",
        "expected_grade": "A",
        "expected_degradation_state": "CONTROL_PENDING_HUMAN_WHITEBOX_REVIEW",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_NO_INTERNAL_EVIDENCE_REQUIRES_GAP_AND_WHITEBOX_REVIEW"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_EVIDENCE_GAP_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "low_ocr_evidence_degradation_control",
        "scenario_category": "LOW_OCR_EVIDENCE_CONTROL",
        "phase2_control_scenario": "low_grade_evidence_degraded_reference_only",
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_LOW_OCR_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "old_version_evidence_degradation_control",
        "scenario_category": "OLD_VERSION_EVIDENCE_CONTROL",
        "phase2_control_scenario": "expired_evidence_degraded_reference_only",
        "expected_grade": "C",
        "expected_degradation_state": "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_OLD_VERSION_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "conflict_evidence_degradation_control",
        "scenario_category": "CONFLICT_EVIDENCE_CONTROL",
        "phase2_control_scenario": "conflict_evidence_degraded_reference_only",
        "expected_grade": "B",
        "expected_degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_CONFLICT_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "revoked_evidence_report_impact_control",
        "scenario_category": "REVOKED_EVIDENCE_REPORT_IMPACT_CONTROL",
        "phase2_control_scenario": "revoked_evidence_degraded_reference_only",
        "expected_grade": "A",
        "expected_degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        "report_status_impact_state": (
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        ),
        "evidence_disposition_state": "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_REVOKED_EVIDENCE_REQUIRES_REPORT_REVIEW",
    },
    {
        "scenario_id": "malicious_evidence_quarantine_control",
        "scenario_category": "MALICIOUS_EVIDENCE_CONTROL",
        "phase2_control_scenario": "suspected_poisoning_quarantined_reference_only",
        "expected_grade": "E",
        "expected_degradation_state": (
            "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "explicit_disposition": "CONTROL_MALICIOUS_EVIDENCE_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "low_grade_high_trust_masquerade_control",
        "scenario_category": "LOW_GRADE_MASQUERADE_CONTROL",
        "phase2_control_scenario": "low_grade_evidence_degraded_reference_only",
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_LOW_GRADE_EVIDENCE_CANNOT_MASQUERADE_AS_HIGH_TRUST"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
        ),
        "explicit_disposition": "CONTROL_LOW_GRADE_CANNOT_SUPPORT_HIGH_TRUST_CONCLUSION",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage090_retrieval_evidence_capture_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage090_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage090 P2 retrieval evidence capture slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _control_ref(value: object) -> bool:
    return isinstance(value, str) and CONTROL_PREFIX in value


def _phase2_runtime_is_closed(result: Mapping[str, Any]) -> bool:
    if any(result.get(field) != 0 for field in P2_ZERO_COUNTER_FIELDS):
        return False
    boundary = result.get("runtime_boundary")
    return isinstance(boundary, Mapping) and all(
        boundary.get(field) is False for field in RUNTIME_CLOSED_FIELDS
    ) and all(value is False for value in boundary.values())


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        result.get("schema_version") != getattr(phase2_module, "SCHEMA_VERSION", None)
        or result.get("record_kind") != getattr(phase2_module, "RECORD_KIND", None)
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or getattr(phase2_module, "CONTROL_PREFIX", None) != CONTROL_PREFIX
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
        != ("retrieval_evidence_capture_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != 26
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("control_input_count") != len(P2_CONTROL_SCENARIOS)
        or result.get("persistent_record_created") is not False
    ):
        return False
    for prefix, field_constant in P2_PROJECTION_SPECS:
        expected_fields = getattr(phase2_module, field_constant, ())
        records = result.get(f"{prefix}_control_projections")
        if (
            not isinstance(records, list)
            or len(records) != len(P2_CONTROL_SCENARIOS)
            or result.get(f"{prefix}_control_projection_count")
            != len(P2_CONTROL_SCENARIOS)
            or any(
                not isinstance(record, Mapping)
                or set(record) != set(expected_fields)
                for record in records
            )
        ):
            return False
    return True


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for prefix, _field_constant in P2_PROJECTION_SPECS:
        records = result.get(f"{prefix}_control_projections")
        if not isinstance(records, list):
            return False
        for record in records:
            if not isinstance(record, Mapping):
                return False
            if any(
                field.endswith("_ref") and not _control_ref(value)
                for field, value in record.items()
            ):
                return False
    return True


def _phase2_records(
    result: Mapping[str, Any], scenario: str
) -> dict[str, Mapping[str, Any]]:
    index = P2_CONTROL_SCENARIOS.index(scenario)
    records: dict[str, Mapping[str, Any]] = {}
    for prefix, _field_constant in P2_PROJECTION_SPECS:
        record = result[f"{prefix}_control_projections"][index]
        if not isinstance(record, Mapping):
            raise ValueError(f"invalid Stage090 P2 {prefix} projection")
        records[prefix] = record
    return records


def _phase2_semantic_failure(result: Mapping[str, Any]) -> str | None:
    grade_a = _phase2_records(
        result, "grade_a_pending_whitebox_review_reference_only"
    )
    low_grade = _phase2_records(
        result, "low_grade_evidence_degraded_reference_only"
    )
    conflict = _phase2_records(
        result, "conflict_evidence_degraded_reference_only"
    )
    expired = _phase2_records(
        result, "expired_evidence_degraded_reference_only"
    )
    revoked = _phase2_records(
        result, "revoked_evidence_degraded_reference_only"
    )
    malicious = _phase2_records(
        result, "suspected_poisoning_quarantined_reference_only"
    )
    if (
        not _control_ref(grade_a["evidence_ledger_capture"]["evidence_gap_ref"])
        or not _control_ref(
            grade_a["critical_conclusion_binding"]["evidence_gap_ref"]
        )
        or grade_a["critical_conclusion_binding"].get("conclusion_binding_state")
        != "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
    ):
        return "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING"
    if (
        low_grade["degradation"].get("evidence_grade_label") != "D"
        or low_grade["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED"
        or not _control_ref(low_grade["risk_score"]["ocr_quality_indicator_ref"])
    ):
        return "LOW_OCR_EVIDENCE_NOT_DEGRADED"
    if (
        expired["degradation"].get("evidence_grade_label") != "C"
        or expired["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED"
        or not _control_ref(expired["retrieval_capture"]["source_version_ref"])
    ):
        return "OLD_VERSION_EVIDENCE_NOT_DEGRADED"
    if (
        conflict["degradation"].get("evidence_grade_label") != "B"
        or conflict["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED"
        or not _control_ref(conflict["risk_score"]["conflict_indicator_ref"])
    ):
        return "CONFLICT_EVIDENCE_NOT_DEGRADED"
    if (
        revoked["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED"
        or revoked["revocation"].get("revocation_state")
        != "CONTROL_REVOCATION_ROUTE_NOT_EXECUTED"
        or not _control_ref(revoked["revocation"]["affected_report_ref"])
        or not _control_ref(
            revoked["future_integration"]["report_status_update_route_ref"]
        )
    ):
        return "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING"
    if (
        malicious["degradation"].get("degradation_state")
        != "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED"
        or malicious["poisoning_defense"].get("quarantine_state")
        != "CONTROL_QUARANTINE_ROUTE_NOT_EXECUTED"
    ):
        return "MALICIOUS_EVIDENCE_NOT_QUARANTINED"
    if (
        low_grade["degradation"].get("evidence_grade_label") != "D"
        or "evidence-grade-D"
        not in str(low_grade["evidence_ledger_capture"]["evidence_grade_ref"])
    ):
        return "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_TRUST"
    for scenario in P2_CONTROL_SCENARIOS:
        records = _phase2_records(result, scenario)
        binding = records["critical_conclusion_binding"]
        defense = records["poisoning_defense"]
        if (
            not _control_ref(binding["evidence_id_ref"])
            or not _control_ref(binding["evidence_gap_ref"])
            or binding.get("conclusion_binding_state")
            != "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        ):
            return "CRITICAL_CONCLUSION_BINDING_MISSING"
        if (
            defense.get("human_whitebox_review_state")
            != "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED"
        ):
            return "HUMAN_WHITEBOX_REVIEW_REQUIRED"
    return None


def _scenario_expectation_met(
    definition: Mapping[str, str], records: Mapping[str, Mapping[str, Any]]
) -> bool:
    schema = records["evidence_schema_binding"]
    retrieval = records["retrieval_capture"]
    ledger = records["evidence_ledger_capture"]
    relation = records["capture_relation"]
    risk = records["risk_score"]
    revocation = records["revocation"]
    defense = records["poisoning_defense"]
    binding = records["critical_conclusion_binding"]
    degradation = records["degradation"]
    future = records["future_integration"]
    scenario_id = definition["scenario_id"]
    scenario_specific = (
        _control_ref(ledger.get("evidence_gap_ref"))
        and _control_ref(binding.get("evidence_gap_ref"))
        if scenario_id == "no_internal_evidence_gap_control"
        else True
    )
    scenario_specific = scenario_specific and (
        revocation.get("revocation_state") == "CONTROL_REVOCATION_ROUTE_NOT_EXECUTED"
        and _control_ref(revocation.get("affected_report_ref"))
        if scenario_id == "revoked_evidence_report_impact_control"
        else True
    )
    scenario_specific = scenario_specific and (
        defense.get("quarantine_state") == "CONTROL_QUARANTINE_ROUTE_NOT_EXECUTED"
        if scenario_id == "malicious_evidence_quarantine_control"
        else True
    )
    scenario_specific = scenario_specific and (
        "evidence-grade-D" in str(ledger.get("evidence_grade_ref"))
        if scenario_id == "low_grade_high_trust_masquerade_control"
        else True
    )
    return (
        all(
            _control_ref(value)
            for value in (
                schema.get("evidence_id_ref"),
                schema.get("document_id_ref"),
                schema.get("chunk_id_ref"),
                schema.get("fact_id_ref"),
                retrieval.get("query_ref"),
                retrieval.get("answer_ref"),
                retrieval.get("report_id_ref"),
                relation.get("query_ref"),
                ledger.get("evidence_gap_ref"),
                ledger.get("evidence_grade_ref"),
                risk.get("ocr_quality_indicator_ref"),
                risk.get("conflict_indicator_ref"),
                risk.get("freshness_indicator_ref"),
                revocation.get("revocation_state_ref"),
                defense.get("poisoning_defense_state_ref"),
                binding.get("critical_conclusion_ref"),
                future.get("report_status_update_route_ref"),
            )
        )
        and degradation.get("evidence_grade_label") == definition["expected_grade"]
        and degradation.get("degradation_state")
        == definition["expected_degradation_state"]
        and binding.get("conclusion_binding_state")
        == "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        and defense.get("human_whitebox_review_state")
        == "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED"
        and scenario_specific
    )


def _build_scenario(
    definition: Mapping[str, str], phase2_result: Mapping[str, Any]
) -> dict[str, Any]:
    records = _phase2_records(phase2_result, definition["phase2_control_scenario"])
    schema = records["evidence_schema_binding"]
    retrieval = records["retrieval_capture"]
    ledger = records["evidence_ledger_capture"]
    relation = records["capture_relation"]
    risk = records["risk_score"]
    revocation = records["revocation"]
    defense = records["poisoning_defense"]
    binding = records["critical_conclusion_binding"]
    degradation = records["degradation"]
    future = records["future_integration"]
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "evidence_id_ref": schema["evidence_id_ref"],
        "document_id_ref": schema["document_id_ref"],
        "chunk_id_ref": schema["chunk_id_ref"],
        "fact_id_ref": schema["fact_id_ref"],
        "query_ref": relation["query_ref"],
        "answer_ref": relation["answer_ref"],
        "report_id_ref": relation["report_id_ref"],
        "evidence_gap_ref": ledger["evidence_gap_ref"],
        "evidence_grade_ref": ledger["evidence_grade_ref"],
        "evidence_grade_label": degradation["evidence_grade_label"],
        "source_version_ref": retrieval["source_version_ref"],
        "ocr_quality_indicator_ref": risk["ocr_quality_indicator_ref"],
        "conflict_indicator_ref": risk["conflict_indicator_ref"],
        "freshness_indicator_ref": risk["freshness_indicator_ref"],
        "revocation_ref": revocation["revocation_state_ref"],
        "poisoning_defense_ref": defense["poisoning_defense_state_ref"],
        "critical_conclusion_ref": binding["critical_conclusion_ref"],
        "report_status_impact_ref": future["report_status_update_route_ref"],
        "report_status_impact_state": definition["report_status_impact_state"],
        "evidence_disposition_state": definition["evidence_disposition_state"],
        "conclusion_acceptance_state": definition["conclusion_acceptance_state"],
        "human_whitebox_review_state": defense["human_whitebox_review_state"],
        "business_line_whitebox_human_approval_recorded": False,
        "actual_report_status_updated": False,
        "actual_evidence_grade_changed": False,
        "human_handling_required": True,
        "explicit_disposition": definition["explicit_disposition"],
        "silent_drop": False,
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
        "actual_report_status_update_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }


def build_retrieval_evidence_capture_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制投影并验证 P3 固定异常场景。"""

    phase2_module = _load_phase2_module()
    executor = (
        phase2_executor
        or phase2_module.execute_retrieval_evidence_capture_control_slice
    )
    try:
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
        "actual_report_status_update_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }
