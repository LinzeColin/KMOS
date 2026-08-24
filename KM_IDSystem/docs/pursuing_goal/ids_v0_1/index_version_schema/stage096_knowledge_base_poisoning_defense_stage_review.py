"""Stage096 知识库投毒防护整阶段纯内存机械复审。"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage096.knowledge_base_poisoning_defense.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_KNOWLEDGE_BASE_POISONING_DEFENSE_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE096-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE097-P1-GATE"
P3_PASS_RESULT = "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
CONTROL_PREFIXES = (":control:stage096-p2:", ":control:stage096-p4:")

P1_STATIC_SHAPE = "8/6/5/14"
P1_FAILURE_STATE_COUNT = 14
P2_CONTROL_REQUEST_COUNT = 6
P2_CONTROL_INPUT_FIELD_COUNT = 21
P2_PROJECTION_GROUP_COUNT = 6
P2_FIELDS_PER_REQUEST = 58
P2_CONTROL_FIELD_CHECK_COUNT = 348
P3_SCENARIO_COUNT = 7
P3_SCENARIO_FIELD_COUNT = 32
P3_SCENARIO_FIELD_CHECK_COUNT = 224
P3_FAILURE_STATE_COUNT = 15
P4_DELIVERY_SHAPE = "7/7/7/7/7/4/2"
P4_DELIVERY_FIELD_CHECK_COUNT = 517
P4_CHINESE_FEEDBACK_COUNT = 4
P4_FAILURE_STATE_COUNT = 18

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_static_shape": P1_STATIC_SHAPE,
    "phase1_failure_state_count": P1_FAILURE_STATE_COUNT,
    "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
    "phase2_control_input_field_count": P2_CONTROL_INPUT_FIELD_COUNT,
    "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
    "phase2_fields_per_request": P2_FIELDS_PER_REQUEST,
    "phase2_control_field_check_count": P2_CONTROL_FIELD_CHECK_COUNT,
    "phase3_scenario_count": P3_SCENARIO_COUNT,
    "phase3_scenario_field_count": P3_SCENARIO_FIELD_COUNT,
    "phase3_scenario_field_check_count": P3_SCENARIO_FIELD_CHECK_COUNT,
    "phase3_failure_state_count": P3_FAILURE_STATE_COUNT,
    "phase4_delivery_shape": P4_DELIVERY_SHAPE,
    "phase4_delivery_field_check_count": P4_DELIVERY_FIELD_CHECK_COUNT,
    "phase4_chinese_feedback_count": P4_CHINESE_FEEDBACK_COUNT,
    "phase4_failure_state_count": P4_FAILURE_STATE_COUNT,
}

REVIEW_RUNTIME_FALSE_FIELDS = (
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
    "stage096_review_runtime_executed",
)

REVIEW_ZERO_COUNT_FIELDS = (
    "actual_input_request_count",
    "actual_knowledge_base_poisoning_defense_execution_count",
    "actual_retrieval_execution_count",
    "actual_retrieval_evidence_capture_count",
    "actual_evidence_ledger_access_count",
    "actual_evidence_gap_detection_count",
    "actual_evidence_gap_resolution_count",
    "actual_risk_score_calculation_count",
    "actual_evidence_grade_change_count",
    "actual_revocation_execution_count",
    "actual_degradation_execution_count",
    "actual_recovery_execution_count",
    "actual_poisoning_defense_execution_count",
    "actual_report_status_update_count",
    "actual_audit_log_write_count",
    "actual_evidence_ledger_sample_write_count",
    "actual_evidence_grade_report_write_count",
    "actual_revocation_impact_list_write_count",
    "actual_regression_test_record_write_count",
    "actual_non_conclusion_type_record_write_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage096_knowledge_base_poisoning_defense_contract.json"
P2_MODULE_PATH = BASE / "stage096_knowledge_base_poisoning_defense_control_slice.py"
P3_MODULE_PATH = BASE / "stage096_knowledge_base_poisoning_defense_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage096_knowledge_base_poisoning_defense_delivery.py"
NEXT_TASKPACK_PATH = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)


def _load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _default_phase1_contract() -> Mapping[str, Any]:
    return _load_json(P1_CONTRACT_PATH)


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module("stage096_review_phase2", P2_MODULE_PATH)
    return module.execute_knowledge_base_poisoning_defense_control_slice(
        module.build_control_input()
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage096_review_phase3", P3_MODULE_PATH)
    return module.build_knowledge_base_poisoning_defense_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage096_review_phase4", P4_MODULE_PATH)
    return module.build_knowledge_base_poisoning_defense_phase4_delivery_report()


def _provider_value(provider: Provider | None, fallback: Provider) -> Mapping[str, Any]:
    try:
        value = (provider or fallback)()
    except Exception:
        return {}
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _runtime_closed(value: Mapping[str, Any]) -> bool:
    boundary = value.get("runtime_boundary")
    return isinstance(boundary, Mapping) and bool(boundary) and all(
        item is False for item in boundary.values()
    )


def _actual_counts_closed(value: Mapping[str, Any]) -> bool:
    counts = [
        item
        for key, item in value.items()
        if key.startswith("actual_") and key.endswith("_count")
    ]
    return bool(counts) and all(item == 0 for item in counts)


def _control_reference(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and value.startswith(CONTROL_PREFIXES)
    )


def _records_have_shape(
    records: object, expected_count: int, fields: Sequence[str]
) -> bool:
    return isinstance(records, list) and len(records) == expected_count and all(
        isinstance(record, Mapping) and set(record) == set(fields) for record in records
    )


def _phase1_valid(contract: Mapping[str, Any]) -> bool:
    authority = _mapping(contract.get("source_authority"))
    control = _mapping(contract.get("knowledge_base_poisoning_defense_contract"))
    grade = _mapping(control.get("evidence_grade_definition_reference"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    runtime = _mapping(contract.get("runtime_boundary"))
    return (
        contract.get("phase") == "IDS-STAGE096-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE096-P1"
        and contract.get("next_gate") == "IDS-STAGE096-P2-GATE"
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and authority.get("raw_metadata_content_access_allowed") is False
        and len(_mapping(control.get("control_definitions"))) == 6
        and control.get("knowledge_base_poisoning_defense_field_count") == 8
        and grade.get("grade_labels") == ["A", "B", "C", "D", "E"]
        and grade.get("grade_assignment_defined") is False
        and grade.get("grade_threshold_defined") is False
        and control.get("critical_conclusion_requires_evidence_id_or_evidence_gap")
        is True
        and control.get("business_line_whitebox_human_review_required_before_business_use")
        is True
        and control.get("all_values_are_control_labels_only") is True
        and all(
            control.get(field) is False
            for field in (
                "actual_evidence_ledger_read_or_written",
                "actual_risk_score_calculated",
                "actual_evidence_grade_assigned_or_changed",
                "actual_evidence_revocation_processed",
                "actual_poisoning_defense_evaluated",
                "actual_poisoning_isolation_processed",
                "actual_high_trust_admission_processed",
                "actual_report_status_updated",
            )
        )
        and failures.get("failure_state_count") == P1_FAILURE_STATE_COUNT
        and bool(runtime)
        and all(item is False for item in runtime.values())
    )


def _phase2_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage096_review_phase2_shape", P2_MODULE_PATH)
        projection_specs = tuple(module.PROJECTION_FIELDS)
    except Exception:
        return False
    projection_total = 0
    for prefix, fields in projection_specs:
        records = report.get(f"{prefix}_control_projections")
        if not _records_have_shape(records, P2_CONTROL_REQUEST_COUNT, fields):
            return False
        if report.get(f"{prefix}_control_projection_count") != P2_CONTROL_REQUEST_COUNT:
            return False
        projection_total += len(fields) * P2_CONTROL_REQUEST_COUNT
        if any(
            field.endswith("_ref") and not _control_reference(value)
            for record in records
            for field, value in record.items()
        ):
            return False
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("input_accepted") is True
        and report.get("execution_state")
        == "CONTROL_KNOWLEDGE_BASE_POISONING_DEFENSE_PROJECTIONS_DECLARED"
        and report.get("failure_state") is None
        and report.get("control_input_count") == P2_CONTROL_REQUEST_COUNT
        and len(getattr(module, "INPUT_FIELDS", ())) == P2_CONTROL_INPUT_FIELD_COUNT
        and len(projection_specs) == P2_PROJECTION_GROUP_COUNT
        and projection_total == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("persistent_record_created") is False
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def _phase3_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage096_review_phase3_shape", P3_MODULE_PATH)
    except Exception:
        return False
    scenarios = report.get("scenario_results")
    if not _records_have_shape(scenarios, P3_SCENARIO_COUNT, module.SCENARIO_FIELDS):
        return False
    scenario_by_id = {item["scenario_id"]: item for item in scenarios}
    expected_ids = [item["scenario_id"] for item in module.SCENARIO_DEFINITIONS]
    no_internal = scenario_by_id.get("no_internal_evidence_poisoning_defense_control", {})
    revoked = scenario_by_id.get("revoked_evidence_report_impact_control", {})
    malicious = scenario_by_id.get("malicious_evidence_quarantine_control", {})
    low_grade = scenario_by_id.get("low_grade_high_trust_masquerade_control", {})
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE096-P3-GATE"
        and report.get("next_gate") == "IDS-STAGE096-P4-GATE"
        and report.get("phase2_control_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and report.get("phase2_control_request_count") == P2_CONTROL_REQUEST_COUNT
        and report.get("phase2_projection_group_count") == P2_PROJECTION_GROUP_COUNT
        and report.get("phase2_field_check_count") == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("scenario_count") == P3_SCENARIO_COUNT
        and report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT
        and report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT
        and [item["scenario_id"] for item in scenarios] == expected_ids
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("human_handling_required") is True for item in scenarios)
        and all(
            item.get("business_line_whitebox_human_approval_recorded") is False
            for item in scenarios
        )
        and all(
            field.endswith("_ref") is False or _control_reference(value)
            for item in scenarios
            for field, value in item.items()
        )
        and no_internal.get("evidence_id_ref") is None
        and _control_reference(no_internal.get("evidence_gap_ref"))
        and revoked.get("actual_report_status_updated") is False
        and str(revoked.get("report_status_impact_state", "")).endswith(
            "DECLARED_NOT_APPLIED"
        )
        and "QUARANTINED" in str(malicious.get("evidence_disposition_state", ""))
        and low_grade.get("high_trust_conclusion_allowed") is False
        and report.get("second_authoritative_source_created") is False
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage096_review_phase4_shape", P4_MODULE_PATH)
    except Exception:
        return False
    specs = (
        (
            "evidence_ledger_sample_control_records",
            "evidence_ledger_sample_control_record_count",
            "evidence_ledger_sample_field_count",
            module.EVIDENCE_LEDGER_SAMPLE_FIELDS,
            7,
        ),
        (
            "evidence_grade_report_control_records",
            "evidence_grade_report_control_record_count",
            "evidence_grade_report_field_count",
            module.EVIDENCE_GRADE_REPORT_FIELDS,
            7,
        ),
        (
            "revocation_impact_control_records",
            "revocation_impact_control_record_count",
            "revocation_impact_field_count",
            module.REVOCATION_IMPACT_FIELDS,
            7,
        ),
        (
            "regression_test_control_records",
            "regression_test_control_record_count",
            "regression_test_record_field_count",
            module.REGRESSION_TEST_RECORD_FIELDS,
            7,
        ),
        (
            "non_conclusion_evidence_type_control_records",
            "non_conclusion_evidence_type_control_record_count",
            "non_conclusion_evidence_type_field_count",
            module.NON_CONCLUSION_EVIDENCE_TYPE_FIELDS,
            7,
        ),
        (
            "degradation_instruction_control_records",
            "degradation_instruction_count",
            "degradation_instruction_field_count",
            module.DEGRADATION_INSTRUCTION_FIELDS,
            4,
        ),
        (
            "revocation_recovery_instruction_control_records",
            "revocation_recovery_instruction_count",
            "revocation_recovery_instruction_field_count",
            module.REVOCATION_RECOVERY_INSTRUCTION_FIELDS,
            2,
        ),
    )
    for records_key, count_key, fields_key, fields, count in specs:
        records = report.get(records_key)
        if (
            not _records_have_shape(records, count, fields)
            or report.get(count_key) != count
            or report.get(fields_key) != len(fields)
            or any(
                field.endswith("_ref") and not _control_reference(value)
                for record in records
                for field, value in record.items()
            )
        ):
            return False
    revoked = next(
        (
            record
            for record in report.get("revocation_impact_control_records", [])
            if record.get("scenario_id") == "revoked_evidence_report_impact_control"
        ),
        {},
    )
    non_conclusion = report.get("non_conclusion_evidence_type_control_records", [])
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE096-P4-GATE"
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("phase3_control_shape_preserved") is True
        and report.get("phase3_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and report.get("all_delivery_references_control_only") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("delivery_field_check_count") == P4_DELIVERY_FIELD_CHECK_COUNT
        and len(report.get("chinese_feedback", [])) == P4_CHINESE_FEEDBACK_COUNT
        and revoked.get("actual_report_status_updated") is False
        and str(revoked.get("report_status_impact_state", "")).endswith(
            "NOT_APPLIED"
        )
        and all(
            item.get("automatic_conclusion_allowed") is False
            and item.get("human_handling_required") is True
            for item in non_conclusion
        )
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document")
        is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and report.get("second_authoritative_source_created") is False
        and all(
            report.get(field) is False
            for field in (
                "automatic_conclusion_allowed",
                "automatic_degradation_allowed",
                "automatic_revocation_allowed",
                "automatic_recovery_allowed",
                "automatic_report_status_update_allowed",
                "stage096_review_started",
                "stage097_started",
                "github_upload_allowed",
                "push_allowed",
            )
        )
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def build_knowledge_base_poisoning_defense_stage096_review_report(
    phase1_contract_provider: Provider | None = None,
    phase2_report_provider: Provider | None = None,
    phase3_report_provider: Provider | None = None,
    phase4_report_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械聚合 Stage096 P1--P4 控制工件，漂移保持失败关闭。"""

    phase1 = _provider_value(phase1_contract_provider, _default_phase1_contract)
    phase2 = _provider_value(phase2_report_provider, _default_phase2_report)
    phase3 = _provider_value(phase3_report_provider, _default_phase3_report)
    phase4 = _provider_value(phase4_report_provider, _default_phase4_report)
    phase_results = {
        "P1": _phase1_valid(phase1),
        "P2": _phase2_valid(phase2),
        "P3": _phase3_valid(phase3),
        "P4": _phase4_valid(phase4),
    }
    phase1_authority = _mapping(phase1.get("source_authority"))
    phase1_control = _mapping(phase1.get("knowledge_base_poisoning_defense_contract"))
    source_boundary = all(
        (
            phase1_authority.get("second_authoritative_source_created") is False,
            phase3.get("second_authoritative_source_created") is False,
            phase4.get("second_authoritative_source_created") is False,
            phase4.get("delivery_control_metadata_can_replace_source_document")
            is False,
            phase4.get("delivery_control_metadata_can_become_business_fact_authority")
            is False,
        )
    )
    owner_whitebox_boundary = (
        phase1_control.get("business_line_whitebox_human_review_required_before_business_use")
        is True
        and phase1_control.get("actual_poisoning_defense_evaluated") is False
        and phase1_control.get("actual_high_trust_admission_processed") is False
        and all(
            item.get("human_handling_required") is True
            for item in phase3.get("scenario_results", [])
        )
        and phase4.get("business_line_whitebox_human_review_remains_authoritative")
        is True
    )
    delivery_boundary = (
        phase4.get("all_delivery_references_control_only") is True
        and phase4.get("automatic_conclusion_allowed") is False
        and phase4.get("automatic_degradation_allowed") is False
        and phase4.get("automatic_revocation_allowed") is False
        and phase4.get("automatic_recovery_allowed") is False
        and phase4.get("automatic_report_status_update_allowed") is False
    )
    runtime_actions_disabled = all(
        (
            _runtime_closed(phase1),
            _runtime_closed(phase2),
            _runtime_closed(phase3),
            _runtime_closed(phase4),
            _actual_counts_closed(phase2),
            _actual_counts_closed(phase3),
            _actual_counts_closed(phase4),
        )
    )
    rollback_boundary = (
        phase4.get("result") == P4_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_report_valid") is True
        and phase4.get("phase3_control_shape_preserved") is True
        and phase4.get("stage096_review_started") is False
        and phase4.get("stage097_started") is False
    )
    controlled_replay_exact = all(phase_results.values())
    review_invariants = {
        "controlled_replay_exact": controlled_replay_exact,
        "single_authority_boundary_preserved": source_boundary,
        "owner_whitebox_boundary_preserved": owner_whitebox_boundary,
        "failure_stop_and_rollback_boundaries_preserved": rollback_boundary,
        "delivery_and_whitebox_boundaries_preserved": delivery_boundary,
        "runtime_actions_disabled": runtime_actions_disabled,
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK_PATH.is_file(),
        "stage097_gate_only_opens_after_review": False,
    }
    review_valid = all(phase_results.values()) and all(
        value
        for key, value in review_invariants.items()
        if key != "stage097_gate_only_opens_after_review"
    )
    review_invariants["stage097_gate_only_opens_after_review"] = review_valid
    failure_reasons: list[str] = []
    for phase_name in ("P1", "P2", "P3", "P4"):
        if not phase_results[phase_name]:
            failure_reasons.append(f"{phase_name}_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not controlled_replay_exact:
        failure_reasons.append("CONTROLLED_REPLAY_SHAPE_MISMATCH")
    if not source_boundary:
        failure_reasons.append("SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not owner_whitebox_boundary:
        failure_reasons.append("OWNER_WHITEBOX_BOUNDARY_MISMATCH")
    if not rollback_boundary:
        failure_reasons.append("FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH")
    if not delivery_boundary:
        failure_reasons.append("DELIVERY_OR_WHITEBOX_BOUNDARY_MISMATCH")
    if not runtime_actions_disabled:
        failure_reasons.append("RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "failure_state": None if review_valid else failure_reasons[0],
        "failure_reasons": failure_reasons,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "phase_results": phase_results,
        "controlled_replay": copy.deepcopy(EXPECTED_CONTROLLED_REPLAY),
        "review_invariants": review_invariants,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "stage095_review_evidence_declared": True,
        "stage096_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage096_review_started": True,
        "whole_stage_review_performed": False,
        "stage097_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "runtime_boundary": {
            field: False
            for field in REVIEW_RUNTIME_FALSE_FIELDS
            if field != "stage096_review_runtime_executed"
        },
        "rollback": {
            "return_to": P4_PASS_RESULT,
            "preserve_stage096_phase1_to_phase4_evidence": True,
            "preserve_stage095_review_evidence": True,
            "business_source_or_runtime_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
    }
