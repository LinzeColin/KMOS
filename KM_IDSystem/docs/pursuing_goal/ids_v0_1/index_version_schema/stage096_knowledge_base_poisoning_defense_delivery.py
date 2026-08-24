"""Stage096 P4 的纯内存知识库投毒防护交付证据。

模块只从 Stage096 P3 已验收的固定、非业务、reference-only 异常场景派生
进程内控制记录。来源文档、真实证据账本、报告和业务事实继续由既有权威与
业务线白箱人工复核裁定；本模块不读取或写入任何真实业务表面。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage096.knowledge_base_poisoning_defense.phase4.delivery.v1"
RECORD_KIND = "KNOWLEDGE_BASE_POISONING_DEFENSE_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_KNOWLEDGE_BASE_POISONING_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE096-P4-GATE"
NEXT_GATE = "IDS-STAGE096-REVIEW-GATE"
P3_PASS_RESULT = "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage096-p2:"
DELIVERY_PREFIX = ":control:stage096-p4:"

P2_CONTROL_REQUEST_COUNT = 6
P2_CONTROL_INPUT_FIELD_COUNT = 21
P2_PROJECTION_GROUP_COUNT = 6
P2_CONTROL_FIELD_CHECK_COUNT = 348
P3_SCENARIO_COUNT = 7
P3_SCENARIO_FIELD_COUNT = 32
P3_SCENARIO_FIELD_CHECK_COUNT = 224
DELIVERY_FIELD_CHECK_COUNT = 517

EVIDENCE_LEDGER_SAMPLE_FIELDS = (
    "scenario_id",
    "evidence_ledger_sample_ref",
    "evidence_id_ref",
    "document_id_ref",
    "chunk_id_ref",
    "fact_id_ref",
    "query_ref",
    "answer_ref",
    "report_id_ref",
    "sample_state",
    "actual_evidence_ledger_sample_written",
    "human_handling_required",
    "explicit_disposition",
    "expectation_met",
)
EVIDENCE_GRADE_REPORT_FIELDS = (
    "scenario_id",
    "evidence_grade_report_ref",
    "evidence_id_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "evidence_disposition_state",
    "conclusion_acceptance_state",
    "critical_conclusion_ref",
    "grade_report_state",
    "actual_evidence_grade_report_written",
    "human_handling_required",
    "explicit_disposition",
    "expectation_met",
)
REVOCATION_IMPACT_FIELDS = (
    "scenario_id",
    "revocation_impact_item_ref",
    "evidence_id_ref",
    "report_id_ref",
    "revocation_ref",
    "report_status_impact_ref",
    "report_status_impact_state",
    "impact_list_state",
    "actual_report_status_updated",
    "actual_revocation_impact_list_written",
    "human_handling_required",
    "explicit_disposition",
    "expectation_met",
)
REGRESSION_TEST_RECORD_FIELDS = (
    "scenario_id",
    "regression_test_record_ref",
    "evidence_gap_ref",
    "ocr_confidence_indicator_ref",
    "version_status_indicator_ref",
    "conflict_status_indicator_ref",
    "revocation_ref",
    "poisoning_defense_ref",
    "critical_conclusion_ref",
    "regression_state",
    "actual_regression_test_executed",
    "human_handling_required",
    "explicit_disposition",
    "expectation_met",
)
NON_CONCLUSION_EVIDENCE_TYPE_FIELDS = (
    "scenario_id",
    "non_conclusion_type_ref",
    "evidence_grade_ref",
    "evidence_grade_label",
    "evidence_disposition_state",
    "conclusion_acceptance_state",
    "non_conclusion_state",
    "actual_non_conclusion_type_record_written",
    "automatic_conclusion_allowed",
    "human_handling_required",
    "explicit_disposition",
)
DEGRADATION_INSTRUCTION_FIELDS = (
    "instruction_id",
    "evidence_condition_ref",
    "evidence_grade_ref",
    "degradation_target_state",
    "instruction_state",
    "actual_evidence_degradation_performed",
    "human_handling_required",
    "automatic_degradation_allowed",
    "explicit_disposition",
    "recovery_precondition_ref",
)
REVOCATION_RECOVERY_INSTRUCTION_FIELDS = (
    "instruction_id",
    "workflow_scope_ref",
    "revocation_ref",
    "report_status_impact_ref",
    "recovery_target_ref",
    "entry_precondition",
    "instruction_state",
    "actual_revocation_execution_performed",
    "actual_recovery_execution_performed",
    "human_handling_required",
    "explicit_disposition",
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
    "knowledge_base_poisoning_defense_execution_performed",
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
    "actual_evidence_ledger_sample_written",
    "actual_evidence_grade_report_written",
    "actual_revocation_impact_list_written",
    "actual_regression_test_record_written",
    "actual_non_conclusion_type_record_written",
    "actual_chinese_feedback_published",
)
P3_RUNTIME_COUNTER_FIELDS = (
    "actual_knowledge_base_poisoning_defense_execution_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_degradation_execution_count",
    "actual_recovery_execution_count",
    "actual_poisoning_defense_execution_count",
    "actual_report_status_update_count",
    "actual_evidence_ledger_access_count",
    "actual_database_connection_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)
FAILURE_STATES = (
    "PHASE3_CONTROL_OUTPUT_INVALID",
    "PHASE3_CONTROL_SHAPE_MISMATCH",
    "PHASE3_RUNTIME_SIGNAL_DETECTED",
    "CONTROL_REFERENCE_NOT_OPAQUE",
    "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING",
    "EVIDENCE_DEGRADATION_DISPOSITION_MISSING",
    "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
    "MALICIOUS_EVIDENCE_QUARANTINE_MISSING",
    "LOW_GRADE_MASQUERADE_REJECTION_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "EVIDENCE_LEDGER_SAMPLE_WRITE_SIGNAL_DETECTED",
    "REPORT_STATUS_UPDATE_SIGNAL_DETECTED",
    "AUTOMATIC_CONCLUSION_ALLOWED",
    "AUTOMATIC_DEGRADATION_ALLOWED",
    "AUTOMATIC_REVOCATION_OR_RECOVERY_ALLOWED",
    "STAGE_REVIEW_STARTED",
    "DELIVERY_EXPECTATION_MISMATCH",
)

DEGRADATION_INSTRUCTION_DEFINITIONS = (
    {
        "instruction_id": "low_ocr_poisoning_defense_degradation_instruction",
        "scenario_id": "low_ocr_poisoning_defense_degradation_control",
        "condition_field": "evidence_ledger_ref",
        "target_state": "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
    },
    {
        "instruction_id": "old_version_poisoning_defense_degradation_instruction",
        "scenario_id": "old_version_poisoning_defense_degradation_control",
        "condition_field": "evidence_ledger_ref",
        "target_state": "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
    },
    {
        "instruction_id": "conflict_poisoning_defense_degradation_instruction",
        "scenario_id": "conflict_poisoning_defense_degradation_control",
        "condition_field": "evidence_ledger_ref",
        "target_state": "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
    },
    {
        "instruction_id": "revoked_evidence_poisoning_defense_degradation_instruction",
        "scenario_id": "revoked_evidence_report_impact_control",
        "condition_field": "revocation_status_ref",
        "target_state": "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
    },
)
REVOCATION_RECOVERY_INSTRUCTION_DEFINITIONS = (
    {
        "instruction_id": "revoked_evidence_future_recovery_instruction",
        "scenario_id": "revoked_evidence_report_impact_control",
        "scope": "CONTROL_REVOKED_EVIDENCE_FUTURE_WHITEBOX_REVIEW",
    },
    {
        "instruction_id": "malicious_evidence_future_recovery_instruction",
        "scenario_id": "malicious_evidence_quarantine_control",
        "scope": "CONTROL_QUARANTINED_EVIDENCE_FUTURE_WHITEBOX_REVIEW",
    },
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]


def build_knowledge_base_poisoning_defense_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
) -> dict[str, Any]:
    """从固定 P3 场景派生未持久化的 Stage096 P4 交付控制记录。"""

    try:
        phase3_module = _load_phase3_module()
        provider = phase3_report_provider or _default_phase3_report_provider
        phase3_report = _provider_result(provider)
    except Exception:
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")
    if not phase3_report:
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")
    if not _phase3_runtime_is_closed(phase3_module, phase3_report):
        return _failure_report("PHASE3_RUNTIME_SIGNAL_DETECTED")
    if not _phase3_shape_is_preserved(phase3_module, phase3_report):
        return _failure_report("PHASE3_CONTROL_SHAPE_MISMATCH")
    if not _phase3_control_references_are_opaque(phase3_report):
        return _failure_report("CONTROL_REFERENCE_NOT_OPAQUE")
    semantic_failure = _phase3_semantic_failure(phase3_report)
    if semantic_failure is not None:
        return _failure_report(semantic_failure)

    scenarios = _as_records(phase3_report.get("scenario_results"))
    samples = _evidence_ledger_samples(scenarios)
    grade_reports = _evidence_grade_reports(scenarios)
    revocation_impacts = _revocation_impacts(scenarios)
    regression_records = _regression_test_records(scenarios)
    non_conclusion_types = _non_conclusion_evidence_types(scenarios)
    degradation_instructions = _degradation_instructions(scenarios)
    recovery_instructions = _revocation_recovery_instructions(scenarios)
    runtime_boundary = _runtime_boundary()
    field_check_count = _delivery_field_check_count(
        samples,
        grade_reports,
        revocation_impacts,
        regression_records,
        non_conclusion_types,
        degradation_instructions,
        recovery_instructions,
    )
    failure_state = _delivery_failure_state(
        samples,
        grade_reports,
        revocation_impacts,
        regression_records,
        non_conclusion_types,
        degradation_instructions,
        recovery_instructions,
        field_check_count,
        runtime_boundary,
    )
    if failure_state is not None:
        return _failure_report(failure_state)

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": True,
        "result": PASS_RESULT,
        "failure_state": None,
        "current_gate": ENTRY_GATE,
        "next_gate": NEXT_GATE,
        "phase3_controlled_scenarios_replayed_in_memory_only": True,
        "phase3_controlled_scenarios_report_valid": True,
        "phase3_control_shape_preserved": True,
        "phase3_side_effect_free": True,
        "control_references_opaque": True,
        "delivery_evidence_metadata_only": True,
        "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
        "phase2_control_input_field_count": P2_CONTROL_INPUT_FIELD_COUNT,
        "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
        "phase2_control_field_check_count": P2_CONTROL_FIELD_CHECK_COUNT,
        "phase3_scenario_count": P3_SCENARIO_COUNT,
        "phase3_scenario_field_count": P3_SCENARIO_FIELD_COUNT,
        "phase3_scenario_field_check_count": P3_SCENARIO_FIELD_CHECK_COUNT,
        "evidence_ledger_sample_control_records": samples,
        "evidence_ledger_sample_control_record_count": len(samples),
        "evidence_ledger_sample_field_count": len(EVIDENCE_LEDGER_SAMPLE_FIELDS),
        "evidence_grade_report_control_records": grade_reports,
        "evidence_grade_report_control_record_count": len(grade_reports),
        "evidence_grade_report_field_count": len(EVIDENCE_GRADE_REPORT_FIELDS),
        "revocation_impact_control_records": revocation_impacts,
        "revocation_impact_control_record_count": len(revocation_impacts),
        "revocation_impact_field_count": len(REVOCATION_IMPACT_FIELDS),
        "regression_test_control_records": regression_records,
        "regression_test_control_record_count": len(regression_records),
        "regression_test_record_field_count": len(REGRESSION_TEST_RECORD_FIELDS),
        "non_conclusion_evidence_type_control_records": non_conclusion_types,
        "non_conclusion_evidence_type_control_record_count": len(non_conclusion_types),
        "non_conclusion_evidence_type_field_count": len(
            NON_CONCLUSION_EVIDENCE_TYPE_FIELDS
        ),
        "degradation_instruction_control_records": degradation_instructions,
        "degradation_instruction_count": len(degradation_instructions),
        "degradation_instruction_field_count": len(DEGRADATION_INSTRUCTION_FIELDS),
        "revocation_recovery_instruction_control_records": recovery_instructions,
        "revocation_recovery_instruction_count": len(recovery_instructions),
        "revocation_recovery_instruction_field_count": len(
            REVOCATION_RECOVERY_INSTRUCTION_FIELDS
        ),
        "delivery_field_check_count": field_check_count,
        "all_delivery_references_control_only": True,
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "second_authoritative_source_created": False,
        "automatic_conclusion_allowed": False,
        "automatic_degradation_allowed": False,
        "automatic_revocation_allowed": False,
        "automatic_recovery_allowed": False,
        "automatic_report_status_update_allowed": False,
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
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
        "actual_evidence_ledger_sample_write_count": 0,
        "actual_evidence_grade_report_write_count": 0,
        "actual_revocation_impact_list_write_count": 0,
        "actual_regression_test_record_write_count": 0,
        "actual_non_conclusion_type_record_write_count": 0,
        "stage095_review_evidence_declared": True,
        "stage096_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "stage096_review_started": False,
        "stage097_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "runtime_boundary": runtime_boundary,
        "chinese_feedback": [
            "交付样例、等级报告、撤回影响和回归记录均为进程内控制投影，来源文档与真实证据账本继续承担业务事实权威。",
            "无内部证据、低 OCR、旧版本、冲突、撤回、恶意资料与低等级伪装均处于控制拒绝状态，业务线白箱人工处理为必经步骤。",
            "证据降级、撤回和恢复控制说明保留未来授权、白箱批准、版本化依据与可验证回退目标作为进入条件。",
            "Stage096 P4 控制只开放整阶段机械复审门，Review、Stage097、OVH、生产与正式上传保持后续阶段。",
        ],
    }


def _default_phase3_report_provider() -> Mapping[str, Any]:
    return _load_phase3_module().build_knowledge_base_poisoning_defense_phase3_report()


def _provider_result(provider: Phase3ReportProvider) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _load_phase3_module() -> Any:
    path = Path(__file__).with_name(
        "stage096_knowledge_base_poisoning_defense_controlled_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage096_phase3_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage096 P3 knowledge base poisoning scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _inherited_control_ref(value: object) -> bool:
    return isinstance(value, str) and value.startswith(CONTROL_PREFIX)


def _control_ref(value: object) -> bool:
    return isinstance(value, str) and (
        value.startswith(CONTROL_PREFIX) or value.startswith(DELIVERY_PREFIX)
    )


def _delivery_ref(scenario_id: str, suffix: str) -> str:
    return f"{DELIVERY_PREFIX}{scenario_id}:{suffix}"


def _explicit_disposition(scenario: Mapping[str, Any]) -> str:
    return (
        f"{scenario['evidence_disposition_state']}|"
        f"{scenario['conclusion_acceptance_state']}"
    )


def _report_status_impact_ref(scenario: Mapping[str, Any]) -> str:
    return _delivery_ref(str(scenario["scenario_id"]), "report-status-impact")


def _as_records(value: object) -> list[Mapping[str, Any]]:
    return (
        list(value)
        if isinstance(value, list) and all(isinstance(item, Mapping) for item in value)
        else []
    )


def _records_have_exact_shape(
    records: Sequence[Mapping[str, Any]], expected_count: int, fields: Sequence[str]
) -> bool:
    return len(records) == expected_count and all(
        set(record) == set(fields) for record in records
    )


def _phase3_runtime_is_closed(module: Any, report: Mapping[str, Any]) -> bool:
    boundary = report.get("runtime_boundary")
    fields = tuple(getattr(module, "RUNTIME_CLOSED_FIELDS", ()))
    return (
        isinstance(boundary, Mapping)
        and bool(fields)
        and all(boundary.get(field) is False for field in fields)
        and all(value is False for value in boundary.values())
        and all(report.get(field) == 0 for field in P3_RUNTIME_COUNTER_FIELDS)
    )


def _phase3_shape_is_preserved(module: Any, report: Mapping[str, Any]) -> bool:
    scenarios = _as_records(report.get("scenario_results"))
    expected_ids = [item["scenario_id"] for item in module.SCENARIO_DEFINITIONS]
    return (
        report.get("schema_version") == getattr(module, "SCHEMA_VERSION", None)
        and report.get("record_kind") == getattr(module, "RECORD_KIND", None)
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == getattr(module, "CURRENT_GATE", None)
        and report.get("next_gate") == ENTRY_GATE
        and report.get("phase2_control_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and tuple(getattr(module, "P2_CONTROL_SCENARIOS", ()))
        and len(getattr(module, "P2_CONTROL_SCENARIOS", ()))
        == P2_CONTROL_REQUEST_COUNT
        and len(getattr(module, "P2_PROJECTION_SPECS", ()))
        == P2_PROJECTION_GROUP_COUNT
        and len(getattr(module, "SCENARIO_FIELDS", ())) == P3_SCENARIO_FIELD_COUNT
        and report.get("phase2_control_request_count") == P2_CONTROL_REQUEST_COUNT
        and report.get("phase2_projection_group_count") == P2_PROJECTION_GROUP_COUNT
        and report.get("phase2_field_check_count") == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("scenario_count") == P3_SCENARIO_COUNT
        and report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT
        and report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT
        and len(scenarios) == P3_SCENARIO_COUNT
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and all(set(item) == set(module.SCENARIO_FIELDS) for item in scenarios)
    )


def _phase3_control_references_are_opaque(report: Mapping[str, Any]) -> bool:
    for scenario in _as_records(report.get("scenario_results")):
        for field, value in scenario.items():
            if field.endswith("_ref") and value is not None and not _inherited_control_ref(
                value
            ):
                return False
    return True


def _phase3_semantic_failure(report: Mapping[str, Any]) -> str | None:
    scenarios = {
        item.get("scenario_id"): item for item in _as_records(report.get("scenario_results"))
    }
    no_internal = scenarios.get("no_internal_evidence_poisoning_defense_control", {})
    if (
        no_internal.get("evidence_id_ref") is not None
        or not _inherited_control_ref(no_internal.get("evidence_gap_ref"))
        or no_internal.get("conclusion_acceptance_state")
        != "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW"
    ):
        return "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING"
    for scenario_id, expected_state in (
        (
            "low_ocr_poisoning_defense_degradation_control",
            "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
        ),
        (
            "old_version_poisoning_defense_degradation_control",
            "CONTROL_DEGRADED_OLD_VERSION_NOT_ACCEPTED",
        ),
        (
            "conflict_poisoning_defense_degradation_control",
            "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
        ),
        (
            "revoked_evidence_report_impact_control",
            "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
        ),
    ):
        if scenarios.get(scenario_id, {}).get("degradation_state") != expected_state:
            return "EVIDENCE_DEGRADATION_DISPOSITION_MISSING"
    revoked = scenarios.get("revoked_evidence_report_impact_control", {})
    if (
        revoked.get("report_status_impact_state")
        != "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED"
        or revoked.get("actual_report_status_updated") is not False
    ):
        return "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING"
    malicious = scenarios.get("malicious_evidence_quarantine_control", {})
    if (
        malicious.get("evidence_disposition_state")
        != "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED"
    ):
        return "MALICIOUS_EVIDENCE_QUARANTINE_MISSING"
    masquerade = scenarios.get("low_grade_high_trust_masquerade_control", {})
    if (
        masquerade.get("evidence_grade_label") != "D"
        or masquerade.get("conclusion_acceptance_state")
        != "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED"
        or masquerade.get("high_trust_conclusion_allowed") is not False
    ):
        return "LOW_GRADE_MASQUERADE_REJECTION_MISSING"
    return None


def _evidence_ledger_samples(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "evidence_ledger_sample_ref": _delivery_ref(
                str(scenario["scenario_id"]), "evidence-ledger-sample"
            ),
            "evidence_id_ref": scenario["evidence_id_ref"],
            "document_id_ref": scenario["document_id_ref"],
            "chunk_id_ref": scenario["chunk_id_ref"],
            "fact_id_ref": scenario["fact_id_ref"],
            "query_ref": scenario["query_ref"],
            "answer_ref": scenario["answer_ref"],
            "report_id_ref": scenario["report_id_ref"],
            "sample_state": "CONTROL_EVIDENCE_LEDGER_SAMPLE_DECLARED_NOT_WRITTEN",
            "actual_evidence_ledger_sample_written": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(scenario),
            "expectation_met": scenario["expectation_met"],
        }
        for scenario in scenarios
    ]


def _evidence_grade_reports(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "evidence_grade_report_ref": _delivery_ref(
                str(scenario["scenario_id"]), "evidence-grade-report"
            ),
            "evidence_id_ref": scenario["evidence_id_ref"],
            "evidence_grade_ref": scenario["evidence_grade_ref"],
            "evidence_grade_label": scenario["evidence_grade_label"],
            "evidence_disposition_state": scenario["evidence_disposition_state"],
            "conclusion_acceptance_state": scenario["conclusion_acceptance_state"],
            "critical_conclusion_ref": scenario["critical_conclusion_ref"],
            "grade_report_state": "CONTROL_EVIDENCE_GRADE_REPORT_DECLARED_NOT_PUBLISHED",
            "actual_evidence_grade_report_written": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(scenario),
            "expectation_met": scenario["expectation_met"],
        }
        for scenario in scenarios
    ]


def _revocation_impacts(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "revocation_impact_item_ref": _delivery_ref(
                str(scenario["scenario_id"]), "revocation-impact"
            ),
            "evidence_id_ref": scenario["evidence_id_ref"],
            "report_id_ref": scenario["report_id_ref"],
            "revocation_ref": scenario["revocation_status_ref"],
            "report_status_impact_ref": _report_status_impact_ref(scenario),
            "report_status_impact_state": scenario["report_status_impact_state"],
            "impact_list_state": "CONTROL_REVOCATION_IMPACT_LIST_DECLARED_NOT_WRITTEN",
            "actual_report_status_updated": False,
            "actual_revocation_impact_list_written": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(scenario),
            "expectation_met": scenario["expectation_met"],
        }
        for scenario in scenarios
    ]


def _regression_test_records(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "regression_test_record_ref": _delivery_ref(
                str(scenario["scenario_id"]), "regression-test"
            ),
            "evidence_gap_ref": scenario["evidence_gap_ref"]
            or _delivery_ref(str(scenario["scenario_id"]), "evidence-gap-route"),
            "ocr_confidence_indicator_ref": _delivery_ref(
                str(scenario["scenario_id"]), "ocr-confidence-indicator"
            ),
            "version_status_indicator_ref": _delivery_ref(
                str(scenario["scenario_id"]), "version-status-indicator"
            ),
            "conflict_status_indicator_ref": _delivery_ref(
                str(scenario["scenario_id"]), "conflict-status-indicator"
            ),
            "revocation_ref": scenario["revocation_status_ref"],
            "poisoning_defense_ref": scenario["poisoning_defense_status_ref"],
            "critical_conclusion_ref": scenario["critical_conclusion_ref"],
            "regression_state": "CONTROL_P3_EXCEPTION_REGRESSION_DECLARED_NOT_EXECUTED",
            "actual_regression_test_executed": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(scenario),
            "expectation_met": scenario["expectation_met"],
        }
        for scenario in scenarios
    ]


def _non_conclusion_evidence_types(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "non_conclusion_type_ref": _delivery_ref(
                str(scenario["scenario_id"]), "not-a-conclusion-basis"
            ),
            "evidence_grade_ref": scenario["evidence_grade_ref"],
            "evidence_grade_label": scenario["evidence_grade_label"],
            "evidence_disposition_state": scenario["evidence_disposition_state"],
            "conclusion_acceptance_state": scenario["conclusion_acceptance_state"],
            "non_conclusion_state": "CONTROL_NOT_A_CONCLUSION_BASIS",
            "actual_non_conclusion_type_record_written": False,
            "automatic_conclusion_allowed": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(scenario),
        }
        for scenario in scenarios
    ]


def _degradation_instructions(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {scenario["scenario_id"]: scenario for scenario in scenarios}
    return [
        {
            "instruction_id": definition["instruction_id"],
            "evidence_condition_ref": by_id[definition["scenario_id"]][
                definition["condition_field"]
            ],
            "evidence_grade_ref": by_id[definition["scenario_id"]][
                "evidence_grade_ref"
            ],
            "degradation_target_state": definition["target_state"],
            "instruction_state": "CONTROL_DEGRADATION_INSTRUCTION_DECLARED_NOT_EXECUTED",
            "actual_evidence_degradation_performed": False,
            "human_handling_required": True,
            "automatic_degradation_allowed": False,
            "explicit_disposition": _explicit_disposition(by_id[definition["scenario_id"]]),
            "recovery_precondition_ref": _delivery_ref(
                definition["scenario_id"], "recovery-precondition"
            ),
        }
        for definition in DEGRADATION_INSTRUCTION_DEFINITIONS
    ]


def _revocation_recovery_instructions(
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {scenario["scenario_id"]: scenario for scenario in scenarios}
    return [
        {
            "instruction_id": definition["instruction_id"],
            "workflow_scope_ref": _delivery_ref(
                definition["scenario_id"], definition["scope"]
            ),
            "revocation_ref": by_id[definition["scenario_id"]]["revocation_status_ref"],
            "report_status_impact_ref": _report_status_impact_ref(
                by_id[definition["scenario_id"]]
            ),
            "recovery_target_ref": _delivery_ref(
                definition["scenario_id"], "future-recovery-target"
            ),
            "entry_precondition": "CONTROL_FUTURE_AUTHORIZATION_AND_WHITEBOX_APPROVAL_REQUIRED",
            "instruction_state": "CONTROL_REVOCATION_AND_RECOVERY_DECLARED_NOT_EXECUTED",
            "actual_revocation_execution_performed": False,
            "actual_recovery_execution_performed": False,
            "human_handling_required": True,
            "explicit_disposition": _explicit_disposition(by_id[definition["scenario_id"]]),
        }
        for definition in REVOCATION_RECOVERY_INSTRUCTION_DEFINITIONS
    ]


def _delivery_field_check_count(
    samples: Sequence[Mapping[str, Any]],
    grade_reports: Sequence[Mapping[str, Any]],
    revocation_impacts: Sequence[Mapping[str, Any]],
    regression_records: Sequence[Mapping[str, Any]],
    non_conclusion_types: Sequence[Mapping[str, Any]],
    degradation_instructions: Sequence[Mapping[str, Any]],
    recovery_instructions: Sequence[Mapping[str, Any]],
) -> int:
    return sum(
        len(group) * len(fields)
        for group, fields in (
            (samples, EVIDENCE_LEDGER_SAMPLE_FIELDS),
            (grade_reports, EVIDENCE_GRADE_REPORT_FIELDS),
            (revocation_impacts, REVOCATION_IMPACT_FIELDS),
            (regression_records, REGRESSION_TEST_RECORD_FIELDS),
            (non_conclusion_types, NON_CONCLUSION_EVIDENCE_TYPE_FIELDS),
            (degradation_instructions, DEGRADATION_INSTRUCTION_FIELDS),
            (recovery_instructions, REVOCATION_RECOVERY_INSTRUCTION_FIELDS),
        )
    )


def _delivery_reference_is_allowed(
    record: Mapping[str, Any], field: str, value: object
) -> bool:
    return _control_ref(value) or (
        field == "evidence_id_ref"
        and record.get("scenario_id")
        == "no_internal_evidence_poisoning_defense_control"
        and value is None
    )


def _records_are_control_only(records: Sequence[Mapping[str, Any]]) -> bool:
    return all(
        _delivery_reference_is_allowed(record, field, value)
        for record in records
        for field, value in record.items()
        if field.endswith("_ref")
    )


def _delivery_failure_state(
    samples: Sequence[Mapping[str, Any]],
    grade_reports: Sequence[Mapping[str, Any]],
    revocation_impacts: Sequence[Mapping[str, Any]],
    regression_records: Sequence[Mapping[str, Any]],
    non_conclusion_types: Sequence[Mapping[str, Any]],
    degradation_instructions: Sequence[Mapping[str, Any]],
    recovery_instructions: Sequence[Mapping[str, Any]],
    field_check_count: int,
    runtime_boundary: Mapping[str, bool],
) -> str | None:
    groups = (
        (samples, P3_SCENARIO_COUNT, EVIDENCE_LEDGER_SAMPLE_FIELDS),
        (grade_reports, P3_SCENARIO_COUNT, EVIDENCE_GRADE_REPORT_FIELDS),
        (revocation_impacts, P3_SCENARIO_COUNT, REVOCATION_IMPACT_FIELDS),
        (regression_records, P3_SCENARIO_COUNT, REGRESSION_TEST_RECORD_FIELDS),
        (non_conclusion_types, P3_SCENARIO_COUNT, NON_CONCLUSION_EVIDENCE_TYPE_FIELDS),
        (degradation_instructions, 4, DEGRADATION_INSTRUCTION_FIELDS),
        (recovery_instructions, 2, REVOCATION_RECOVERY_INSTRUCTION_FIELDS),
    )
    if not all(
        _records_have_exact_shape(records, count, fields)
        for records, count, fields in groups
    ) or field_check_count != DELIVERY_FIELD_CHECK_COUNT:
        return "DELIVERY_RECORD_SHAPE_MISMATCH"
    if not all(_records_are_control_only(records) for records, _, _ in groups):
        return "DELIVERY_REFERENCE_NOT_OPAQUE"
    if not all(
        item["actual_evidence_ledger_sample_written"] is False
        and item["human_handling_required"] is True
        and item["expectation_met"] is True
        for item in samples
    ):
        return "EVIDENCE_LEDGER_SAMPLE_WRITE_SIGNAL_DETECTED"
    if not all(
        item["actual_evidence_grade_report_written"] is False
        and item["human_handling_required"] is True
        and item["expectation_met"] is True
        for item in grade_reports
    ):
        return "DELIVERY_EXPECTATION_MISMATCH"
    if not all(
        item["actual_report_status_updated"] is False
        and item["actual_revocation_impact_list_written"] is False
        and item["human_handling_required"] is True
        and item["expectation_met"] is True
        for item in revocation_impacts
    ):
        return "REPORT_STATUS_UPDATE_SIGNAL_DETECTED"
    if not all(
        item["actual_regression_test_executed"] is False
        and item["human_handling_required"] is True
        and item["expectation_met"] is True
        for item in regression_records
    ):
        return "DELIVERY_EXPECTATION_MISMATCH"
    if not all(
        item["non_conclusion_state"] == "CONTROL_NOT_A_CONCLUSION_BASIS"
        and item["actual_non_conclusion_type_record_written"] is False
        and item["automatic_conclusion_allowed"] is False
        and item["human_handling_required"] is True
        for item in non_conclusion_types
    ):
        return "AUTOMATIC_CONCLUSION_ALLOWED"
    if not all(
        item["actual_evidence_degradation_performed"] is False
        and item["automatic_degradation_allowed"] is False
        and item["human_handling_required"] is True
        for item in degradation_instructions
    ):
        return "AUTOMATIC_DEGRADATION_ALLOWED"
    if not all(
        item["actual_revocation_execution_performed"] is False
        and item["actual_recovery_execution_performed"] is False
        and item["human_handling_required"] is True
        for item in recovery_instructions
    ):
        return "AUTOMATIC_REVOCATION_OR_RECOVERY_ALLOWED"
    if any(value is not False for value in runtime_boundary.values()):
        return "STAGE_REVIEW_STARTED"
    return None


def _failure_report(failure_state: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": False,
        "result": FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": ENTRY_GATE,
        "next_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_replayed_in_memory_only": False,
        "phase3_controlled_scenarios_report_valid": False,
        "phase3_control_shape_preserved": False,
        "phase3_side_effect_free": False,
        "control_references_opaque": False,
        "delivery_evidence_metadata_only": True,
        "phase2_control_request_count": 0,
        "phase2_control_input_field_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_control_field_check_count": 0,
        "phase3_scenario_count": 0,
        "phase3_scenario_field_count": P3_SCENARIO_FIELD_COUNT,
        "phase3_scenario_field_check_count": 0,
        "evidence_ledger_sample_control_records": [],
        "evidence_grade_report_control_records": [],
        "revocation_impact_control_records": [],
        "regression_test_control_records": [],
        "non_conclusion_evidence_type_control_records": [],
        "degradation_instruction_control_records": [],
        "revocation_recovery_instruction_control_records": [],
        "delivery_field_check_count": 0,
        "all_delivery_references_control_only": False,
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "second_authoritative_source_created": False,
        "automatic_conclusion_allowed": False,
        "automatic_degradation_allowed": False,
        "automatic_revocation_allowed": False,
        "automatic_recovery_allowed": False,
        "automatic_report_status_update_allowed": False,
        "actual_evidence_gap_detection_count": 0,
        "actual_evidence_gap_resolution_count": 0,
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
        "actual_evidence_ledger_sample_write_count": 0,
        "actual_evidence_grade_report_write_count": 0,
        "actual_revocation_impact_list_write_count": 0,
        "actual_regression_test_record_write_count": 0,
        "actual_non_conclusion_type_record_write_count": 0,
        "stage095_review_evidence_declared": True,
        "stage096_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "stage096_review_started": False,
        "stage097_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [],
    }
