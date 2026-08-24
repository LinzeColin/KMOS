"""Stage092 P3 的纯内存证据风险评分异常场景控制验证。

模块只重放 Stage092 P2 的固定、非业务、reference-only 控制投影。它不读取
来源资料、检索结果或真实证据账本，不连接数据库，不计算真实风险分数，不执行
撤回、投毒处置或报告状态更新，也不写入持久化记录。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage092.evidence_risk_scoring.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EVIDENCE_RISK_SCORING_EXCEPTION_SCENARIOS"
PASS_RESULT = "PASS_EVIDENCE_RISK_SCORING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EVIDENCE_RISK_SCORING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CURRENT_GATE = "IDS-STAGE092-P3-GATE"
NEXT_GATE = "IDS-STAGE092-P4-GATE"
P2_EXECUTION_STATE = "CONTROL_EVIDENCE_RISK_SCORING_PROJECTIONS_DECLARED_NOT_CALCULATED"
CONTROL_PREFIX = ":control:stage092-p2:"
P2_CONTROL_SCENARIOS = (
    "internal_material_insufficient_risk_pending_whitebox_review_reference_only",
    "low_trust_evidence_degraded_reference_only",
    "conflict_evidence_degraded_reference_only",
    "expired_evidence_degraded_reference_only",
    "revoked_evidence_degraded_reference_only",
    "suspected_poisoning_evidence_quarantined_reference_only",
)
P2_PROJECTION_SPECS = (
    ("risk_schema_binding", "RISK_SCHEMA_BINDING_FIELDS"),
    ("evidence_risk_relation", "EVIDENCE_RISK_RELATION_FIELDS"),
    (
        "retrieval_evidence_capture_binding",
        "RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS",
    ),
    ("risk_factor_binding", "RISK_FACTOR_BINDING_FIELDS"),
    ("risk_score", "RISK_SCORE_FIELDS"),
    ("revocation", "REVOCATION_FIELDS"),
    ("poisoning_defense", "POISONING_DEFENSE_FIELDS"),
    ("critical_conclusion_binding", "CRITICAL_CONCLUSION_BINDING_FIELDS"),
    ("degradation", "DEGRADATION_FIELDS"),
    ("report_status_impact", "REPORT_STATUS_IMPACT_FIELDS"),
    ("future_integration", "FUTURE_INTEGRATION_FIELDS"),
)
P2_ZERO_COUNTER_FIELDS = (
    "actual_input_request_count",
    "actual_evidence_gap_detection_count",
    "actual_evidence_gap_resolution_count",
    "actual_retrieval_execution_count",
    "actual_retrieval_evidence_capture_count",
    "actual_evidence_ledger_access_count",
    "actual_evidence_capture_count",
    "actual_risk_factor_evaluation_count",
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
    "evidence_gap_detection_performed",
    "evidence_gap_resolution_performed",
    "retrieval_evidence_capture_performed",
    "risk_factor_evaluation_performed",
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
    "evidence_capture_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "ocr_confidence_indicator_ref",
    "conflict_status_indicator_ref",
    "version_status_indicator_ref",
    "revocation_ref",
    "poisoning_defense_ref",
    "critical_conclusion_ref",
    "report_status_impact_ref",
    "report_status_impact_state",
    "evidence_disposition_state",
    "conclusion_acceptance_state",
    "high_trust_conclusion_allowed",
    "human_whitebox_review_state",
    "business_line_whitebox_human_approval_recorded",
    "actual_report_status_updated",
    "human_handling_required",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)
SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "no_internal_evidence_risk_control",
        "scenario_category": "NO_INTERNAL_EVIDENCE_CONTROL",
        "phase2_control_scenario": (
            "internal_material_insufficient_risk_pending_whitebox_review_reference_only"
        ),
        "expected_evidence_id_present": False,
        "expected_grade": "E",
        "expected_degradation_state": (
            "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_NO_INTERNAL_EVIDENCE_REQUIRES_GAP_AND_WHITEBOX_REVIEW"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_EVIDENCE_GAP_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "low_ocr_evidence_risk_degradation_control",
        "scenario_category": "LOW_OCR_EVIDENCE_CONTROL",
        "phase2_control_scenario": "low_trust_evidence_degraded_reference_only",
        "expected_evidence_id_present": True,
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_TRUST"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_LOW_OCR_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "old_version_evidence_risk_degradation_control",
        "scenario_category": "OLD_VERSION_EVIDENCE_CONTROL",
        "phase2_control_scenario": "expired_evidence_degraded_reference_only",
        "expected_evidence_id_present": True,
        "expected_grade": "C",
        "expected_degradation_state": "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_EXPIRED"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_OLD_VERSION_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "conflict_evidence_risk_degradation_control",
        "scenario_category": "CONFLICT_EVIDENCE_CONTROL",
        "phase2_control_scenario": "conflict_evidence_degraded_reference_only",
        "expected_evidence_id_present": True,
        "expected_grade": "B",
        "expected_degradation_state": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_CONFLICT_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "revoked_evidence_risk_report_impact_control",
        "scenario_category": "REVOKED_EVIDENCE_REPORT_IMPACT_CONTROL",
        "phase2_control_scenario": "revoked_evidence_degraded_reference_only",
        "expected_evidence_id_present": True,
        "expected_grade": "A",
        "expected_degradation_state": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_REVOKED"
        ),
        "report_status_impact_state": (
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        ),
        "evidence_disposition_state": "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_REVOKED_EVIDENCE_REQUIRES_REPORT_REVIEW",
    },
    {
        "scenario_id": "malicious_evidence_risk_quarantine_control",
        "scenario_category": "MALICIOUS_EVIDENCE_CONTROL",
        "phase2_control_scenario": (
            "suspected_poisoning_evidence_quarantined_reference_only"
        ),
        "expected_evidence_id_present": True,
        "expected_grade": "E",
        "expected_degradation_state": (
            "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED"
        ),
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_NOT_ACCEPTED_PENDING_HUMAN_WHITEBOX_REVIEW"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_MALICIOUS_EVIDENCE_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "low_grade_high_trust_masquerade_risk_control",
        "scenario_category": "LOW_GRADE_MASQUERADE_CONTROL",
        "phase2_control_scenario": "low_trust_evidence_degraded_reference_only",
        "expected_evidence_id_present": True,
        "expected_grade": "D",
        "expected_degradation_state": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
        "source_report_status_impact_state": (
            "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_TRUST"
        ),
        "report_status_impact_state": "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
        "evidence_disposition_state": (
            "CONTROL_LOW_GRADE_EVIDENCE_CANNOT_MASQUERADE_AS_HIGH_TRUST"
        ),
        "conclusion_acceptance_state": (
            "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
        ),
        "high_trust_conclusion_allowed": False,
        "explicit_disposition": "CONTROL_LOW_GRADE_CANNOT_SUPPORT_HIGH_TRUST_CONCLUSION",
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage092_evidence_risk_scoring_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage092_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage092 P2 evidence risk scoring slice")
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
        != ("evidence_risk_scoring_control_requests",)
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != 27
        or phase2_projection_names != projection_names
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


def _reference_is_allowed(field: str, value: object, scenario: str) -> bool:
    return (
        field == "evidence_id_ref"
        and scenario
        == "internal_material_insufficient_risk_pending_whitebox_review_reference_only"
        and value is None
    ) or _control_ref(value)


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for index, scenario in enumerate(P2_CONTROL_SCENARIOS):
        for prefix, _field_constant in P2_PROJECTION_SPECS:
            records = result.get(f"{prefix}_control_projections")
            if not isinstance(records, list) or len(records) <= index:
                return False
            record = records[index]
            if not isinstance(record, Mapping):
                return False
            if any(
                field.endswith("_ref")
                and not _reference_is_allowed(field, value, scenario)
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
            raise ValueError(f"invalid Stage092 P2 {prefix} projection")
        records[prefix] = record
    return records


def _phase2_semantic_failure(result: Mapping[str, Any]) -> str | None:
    no_internal = _phase2_records(
        result,
        "internal_material_insufficient_risk_pending_whitebox_review_reference_only",
    )
    low_trust = _phase2_records(result, "low_trust_evidence_degraded_reference_only")
    conflict = _phase2_records(result, "conflict_evidence_degraded_reference_only")
    expired = _phase2_records(result, "expired_evidence_degraded_reference_only")
    revoked = _phase2_records(result, "revoked_evidence_degraded_reference_only")
    malicious = _phase2_records(
        result, "suspected_poisoning_evidence_quarantined_reference_only"
    )
    if (
        no_internal["risk_schema_binding"].get("evidence_id_ref") is not None
        or not _control_ref(no_internal["risk_schema_binding"].get("evidence_gap_ref"))
        or not _control_ref(
            no_internal["critical_conclusion_binding"].get("evidence_gap_ref")
        )
        or no_internal["critical_conclusion_binding"].get("conclusion_binding_state")
        != "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
    ):
        return "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING"
    if (
        low_trust["degradation"].get("evidence_grade_label") != "D"
        or low_trust["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED"
        or not _control_ref(
            low_trust["risk_score"].get("ocr_confidence_indicator_ref")
        )
    ):
        return "LOW_OCR_EVIDENCE_NOT_DEGRADED"
    if (
        expired["degradation"].get("evidence_grade_label") != "C"
        or expired["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED"
        or not _control_ref(
            expired["risk_score"].get("version_status_indicator_ref")
        )
    ):
        return "OLD_VERSION_EVIDENCE_NOT_DEGRADED"
    if (
        conflict["degradation"].get("evidence_grade_label") != "B"
        or conflict["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED"
        or not _control_ref(
            conflict["risk_score"].get("conflict_status_indicator_ref")
        )
    ):
        return "CONFLICT_EVIDENCE_NOT_DEGRADED"
    if (
        revoked["degradation"].get("degradation_state")
        != "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED"
        or revoked["revocation"].get("revocation_state")
        != "CONTROL_REVOCATION_ROUTE_NOT_EXECUTED"
        or not _control_ref(revoked["revocation"].get("affected_report_ref"))
        or revoked["report_status_impact"].get("report_status_impact_state")
        != "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_REVOKED"
    ):
        return "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING"
    if (
        malicious["degradation"].get("degradation_state")
        != "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED"
        or malicious["poisoning_defense"].get("defense_state")
        != "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED"
        or malicious["report_status_impact"].get("report_status_impact_state")
        != "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING"
    ):
        return "MALICIOUS_EVIDENCE_NOT_QUARANTINED"
    if (
        low_trust["degradation"].get("evidence_grade_label") != "D"
        or "evidence-grade-D"
        not in str(
            low_trust["critical_conclusion_binding"].get("evidence_grade_ref")
        )
    ):
        return "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_TRUST"
    for scenario in P2_CONTROL_SCENARIOS:
        records = _phase2_records(result, scenario)
        binding = records["critical_conclusion_binding"]
        defense = records["poisoning_defense"]
        expected_evidence_id = scenario != P2_CONTROL_SCENARIOS[0]
        if (
            bool(binding.get("evidence_id_ref")) != expected_evidence_id
            or not _control_ref(binding.get("evidence_gap_ref"))
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
    definition: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> bool:
    schema = records["risk_schema_binding"]
    relation = records["evidence_risk_relation"]
    capture = records["retrieval_evidence_capture_binding"]
    risk = records["risk_score"]
    revocation = records["revocation"]
    defense = records["poisoning_defense"]
    binding = records["critical_conclusion_binding"]
    degradation = records["degradation"]
    report_impact = records["report_status_impact"]
    future = records["future_integration"]
    scenario_id = definition["scenario_id"]
    evidence_id_expected = definition["expected_evidence_id_present"]
    evidence_id_valid = (
        _control_ref(schema.get("evidence_id_ref"))
        if evidence_id_expected
        else schema.get("evidence_id_ref") is None
    )
    scenario_specific = (
        schema.get("evidence_id_ref") is None
        and binding.get("evidence_id_ref") is None
        if scenario_id == "no_internal_evidence_risk_control"
        else True
    )
    scenario_specific = scenario_specific and (
        revocation.get("revocation_state") == "CONTROL_REVOCATION_ROUTE_NOT_EXECUTED"
        and _control_ref(revocation.get("affected_report_ref"))
        and report_impact.get("report_status_impact_state")
        == "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_REVOKED"
        if scenario_id == "revoked_evidence_risk_report_impact_control"
        else True
    )
    scenario_specific = scenario_specific and (
        defense.get("defense_state")
        == "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED"
        if scenario_id == "malicious_evidence_risk_quarantine_control"
        else True
    )
    scenario_specific = scenario_specific and (
        "evidence-grade-D" in str(binding.get("evidence_grade_ref"))
        and definition["high_trust_conclusion_allowed"] is False
        if scenario_id == "low_grade_high_trust_masquerade_risk_control"
        else True
    )
    return (
        evidence_id_valid
        and all(
            _control_ref(value)
            for value in (
                schema.get("evidence_gap_ref"),
                relation.get("document_id_ref"),
                relation.get("chunk_id_ref"),
                relation.get("fact_id_ref"),
                relation.get("query_ref"),
                relation.get("answer_ref"),
                relation.get("report_id_ref"),
                capture.get("evidence_capture_ref"),
                risk.get("ocr_confidence_indicator_ref"),
                risk.get("version_status_indicator_ref"),
                risk.get("conflict_status_indicator_ref"),
                revocation.get("revocation_status_ref"),
                defense.get("poisoning_defense_status_ref"),
                binding.get("critical_conclusion_ref"),
                report_impact.get("report_status_impact_ref"),
                future.get("report_status_update_route_ref"),
            )
        )
        and degradation.get("evidence_grade_label") == definition["expected_grade"]
        and degradation.get("degradation_state")
        == definition["expected_degradation_state"]
        and report_impact.get("report_status_impact_state")
        == definition["source_report_status_impact_state"]
        and binding.get("conclusion_binding_state")
        == "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP"
        and defense.get("human_whitebox_review_state")
        == "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED"
        and scenario_specific
    )


def _build_scenario(
    definition: Mapping[str, Any], phase2_result: Mapping[str, Any]
) -> dict[str, Any]:
    records = _phase2_records(phase2_result, definition["phase2_control_scenario"])
    schema = records["risk_schema_binding"]
    relation = records["evidence_risk_relation"]
    capture = records["retrieval_evidence_capture_binding"]
    risk = records["risk_score"]
    revocation = records["revocation"]
    defense = records["poisoning_defense"]
    binding = records["critical_conclusion_binding"]
    degradation = records["degradation"]
    report_impact = records["report_status_impact"]
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "evidence_id_ref": schema["evidence_id_ref"],
        "document_id_ref": relation["document_id_ref"],
        "chunk_id_ref": relation["chunk_id_ref"],
        "fact_id_ref": relation["fact_id_ref"],
        "query_ref": relation["query_ref"],
        "answer_ref": relation["answer_ref"],
        "report_id_ref": relation["report_id_ref"],
        "evidence_gap_ref": schema["evidence_gap_ref"],
        "evidence_capture_ref": capture["evidence_capture_ref"],
        "evidence_grade_ref": binding["evidence_grade_ref"],
        "evidence_grade_label": degradation["evidence_grade_label"],
        "ocr_confidence_indicator_ref": risk["ocr_confidence_indicator_ref"],
        "conflict_status_indicator_ref": risk["conflict_status_indicator_ref"],
        "version_status_indicator_ref": risk["version_status_indicator_ref"],
        "revocation_ref": revocation["revocation_status_ref"],
        "poisoning_defense_ref": defense["poisoning_defense_status_ref"],
        "critical_conclusion_ref": binding["critical_conclusion_ref"],
        "report_status_impact_ref": report_impact["report_status_impact_ref"],
        "report_status_impact_state": definition["report_status_impact_state"],
        "evidence_disposition_state": definition["evidence_disposition_state"],
        "conclusion_acceptance_state": definition["conclusion_acceptance_state"],
        "high_trust_conclusion_allowed": definition[
            "high_trust_conclusion_allowed"
        ],
        "human_whitebox_review_state": defense["human_whitebox_review_state"],
        "business_line_whitebox_human_approval_recorded": False,
        "actual_report_status_updated": False,
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
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_report_status_update_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }


def build_evidence_risk_scoring_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制投影并验证 Stage092 P3 固定异常场景。"""

    try:
        phase2_module = _load_phase2_module()
        executor = phase2_executor or phase2_module.execute_evidence_risk_scoring_control_slice
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
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
        "actual_risk_score_calculation_count": 0,
        "actual_report_status_update_count": 0,
        "actual_evidence_grade_change_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_database_connection_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
    }
