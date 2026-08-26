"""Stage112 报告导出审计的纯内存整阶段机械复审。

模块只复审冻结 Stage112 P1--P4 控制工件。它不读取真实业务资料、报告、PDF、
证据账本、审计或数据库，不调用模型、Agent、OVH 或生产服务，也不写入持久化状态。
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "ids.stage112.report_export_audit.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE112-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE113-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage112.report_export_audit.phase1.v1"
P1_RECORD_KIND = "CONTROL_ONLY_REPORT_EXPORT_AUDIT_PHASE1_CONTRACT"
P1_CONTRACT_STATE = "REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage112.report_export_audit.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT"
P2_PASS_RESULT = "PASS_IN_MEMORY_REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage112.report_export_audit.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT_SCENARIOS"
P3_PASS_RESULT = "PASS_REPORT_EXPORT_AUDIT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage112.report_export_audit.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REPORT_EXPORT_AUDIT_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage112_report_export_audit_contract.json")
P3_SCENARIO_IDS = (
    "export_audit_identity_evidence_id_binding_control",
    "source_withdrawal_evidence_gap_report_status_audit_control",
    "evidence_downgrade_evidence_id_report_status_quality_audit_control",
    "index_version_change_evidence_gap_report_snapshot_audit_control",
    "external_augmentation_source_separation_whitebox_control",
)
P3_CONTROL_VIEW_NAMES = {
    "export_audit_identity_and_evidence_binding_control_view",
    "report_and_generation_snapshot_control_view",
    "report_status_quality_and_export_audit_control_view",
    "external_augmentation_source_separation_control_view",
    "business_line_whitebox_and_execution_boundary_control_view",
}
P4_DELIVERY_GROUPS = (
    ("report_sample_control_records", 5, 17),
    ("report_snapshot_control_records", 5, 13),
    ("report_quality_score_control_records", 5, 13),
    ("report_impact_analysis_control_records", 5, 15),
    ("report_template_and_whitebox_confirmation_control_records", 5, 14),
    ("regeneration_and_withdrawal_control_records", 2, 14),
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 32,
    "phase1_snapshot_component_count": 5,
    "phase1_failure_state_count": 20,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 34,
    "phase2_phase1_reference_field_count": 32,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 100,
    "phase2_control_field_check_count": 500,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 53,
    "phase3_scenario_field_check_count": 265,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 5,
    "phase3_whitebox_confirmation_required_count": 5,
    "phase3_failure_state_count": 15,
    "phase3_chinese_feedback_count": 4,
    "phase4_delivery_shape": "5/5/5/5/5/2",
    "phase4_delivery_field_shape": "17/13/13/15/14/14",
    "phase4_delivery_field_check_count": 388,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 17,
    "critical_conclusion_evidence_binding_required": True,
    "actor_time_report_id_evidence_snapshot_controls_required": True,
    "citation_source_and_page_control_required": True,
    "generation_snapshot_control_required": True,
    "external_augmentation_source_separation_required": True,
    "report_status_quality_and_audit_control_required": True,
    "business_line_whitebox_confirmation_required": True,
    "phase4_to_phase3_rollback_required": True,
}

FAILURE_STATES = (
    "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "CONTROLLED_REVIEW_SHAPE_MISMATCH",
    "SINGLE_AUTHORITY_BOUNDARY_BREACH",
    "EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH",
    "REPORT_STATUS_AUDIT_AND_WHITEBOX_SEMANTICS_MISMATCH",
    "REPORT_LIFECYCLE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_STAGE113_ENTRY_DETECTED",
)

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "existing_audit_log_read_performed",
    "report_export_performed",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "snapshot_persistence_performed",
    "report_status_impact_analysis_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_performed",
    "report_withdrawal_performed",
    "human_confirmation_performed",
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
    "stage112_review_runtime_executed",
    "stage113_runtime_started",
)

REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_external_reference_access_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_report_generation_count",
    "actual_snapshot_persistence_count",
    "actual_report_status_impact_analysis_count",
    "actual_report_quality_score_calculation_count",
    "actual_report_export_audit_write_count",
    "actual_report_regeneration_count",
    "actual_report_withdrawal_count",
    "actual_human_confirmation_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

OPERATOR_FEEDBACK = (
    "报告导出审计整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "关键结论保持 evidence_id 或 evidence_gap 的严格二选一，actor、time、report_id 与 evidence_snapshot 保持控制引用。",
    "报告状态、质量、快照、导出审计、模板限制、人工确认、最终结论和重新生成／撤回保持业务线白箱门禁。",
    "真实资料、报告、PDF、审计、数据库、模型、Agent、OVH、生产、Stage113 和正式上传保持未执行。",
)

Provider = Callable[[], Mapping[str, Any]]


def _load_phase_modules() -> tuple[Any, Any, Any]:
    base = "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
    return (
        importlib.import_module(f"{base}stage112_report_export_audit_control_slice"),
        importlib.import_module(f"{base}stage112_report_export_audit_controlled_scenarios"),
        importlib.import_module(f"{base}stage112_report_export_audit_delivery"),
    )


def _default_phase1_contract() -> Mapping[str, Any]:
    return json.loads(P1_CONTRACT_PATH.read_text(encoding="utf-8"))


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in REVIEW_ZERO_COUNT_FIELDS}


def _base_report(valid: bool, failure_state: Optional[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if valid else REVIEW_GATE,
        "phase1_static_contract_reviewed": False,
        "phase2_control_slice_reviewed": False,
        "phase3_controlled_scenarios_reviewed": False,
        "phase4_delivery_evidence_reviewed": False,
        "control_references_opaque": False,
        "single_authority_boundary_preserved": False,
        "report_export_audit_semantics_preserved": False,
        "business_line_whitebox_gate_preserved": False,
        "phase4_to_phase3_rollback_preserved": False,
        "stage112_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "stage113_started": False,
        "reviewed_control_shape": {},
        "reviewed_phase_results": {},
        "chinese_feedback": list(OPERATOR_FEEDBACK),
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _all_false(value: object) -> bool:
    return isinstance(value, Mapping) and all(item is False for item in value.values())


def _all_actual_counts_zero(report: Mapping[str, Any]) -> bool:
    return all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and isinstance(value, int)
    )


def _is_control_reference(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(":control:stage112-")
        and value.endswith(":reference-only")
    )


def _phase1_structural_valid(contract: Mapping[str, Any], phase2: Any) -> bool:
    if not isinstance(contract, Mapping):
        return False
    control = contract.get("report_export_audit_control_contract")
    snapshots = contract.get("generation_snapshot_contract")
    delivery = contract.get("report_delivery_and_whitebox_control_contract")
    failure = contract.get("failure_and_stop_contract")
    boundary = contract.get("stage_and_phase_boundary")
    local_code = contract.get("local_code")
    if not all(
        isinstance(value, Mapping)
        for value in (control, snapshots, delivery, failure, boundary, local_code)
    ):
        return False
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("record_kind") == P1_RECORD_KIND,
            contract.get("stage") == "STAGE-112",
            contract.get("phase") == "IDS-STAGE112-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE112-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE112-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE112-P2-GATE",
            tuple(control.get("future_control_reference_fields", ()))
            == tuple(phase2.PHASE1_CONTROL_REFERENCE_FIELDS),
            control.get("future_control_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase1_reference_field_count"],
            control.get("critical_conclusion_requires_evidence_id_or_evidence_gap_independently")
            is True,
            control.get("future_actor_reference_required") is True,
            control.get("future_export_time_reference_required") is True,
            control.get("future_report_id_reference_required") is True,
            control.get("future_evidence_snapshot_reference_required") is True,
            control.get("future_human_confirmation_item_required") is True,
            control.get("business_line_whitebox_confirmation_required") is True,
            snapshots.get("required_future_snapshot_component_count")
            == REVIEWED_CONTROL_SHAPE["phase1_snapshot_component_count"],
            snapshots.get("snapshot_components_are_control_references_only") is True,
            delivery.get("external_augmentation_source_separation_required") is True,
            delivery.get("report_export_audit_control_required") is True,
            failure.get("failure_state_count")
            == REVIEWED_CONTROL_SHAPE["phase1_failure_state_count"],
            local_code.get("static_contract_only") is True,
            local_code.get("report_export_runtime_implemented") is False,
            local_code.get("audit_or_database_write_implemented") is False,
            boundary.get("stage112_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("phase2_started") is False,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage113_started") is False,
        )
    )


def _phase1_authority_and_runtime_closed(contract: Mapping[str, Any]) -> bool:
    authority = contract.get("source_authority")
    runtime = contract.get("runtime_boundary")
    counts = contract.get("runtime_counts")
    prerequisite = contract.get("future_runtime_prerequisite_contract")
    if not all(
        isinstance(value, Mapping)
        for value in (authority, runtime, counts, prerequisite)
    ):
        return False
    authority_fields = (
        "source_document_remains_authoritative",
        "evidence_ledger_remains_authoritative",
        "delivered_report_remains_authoritative",
        "existing_audit_log_remains_authoritative",
        "business_line_whitebox_human_review_remains_authoritative",
        "control_artifacts_are_engineering_context_only",
    )
    return all(
        (
            all(authority.get(field) is True for field in authority_fields),
            authority.get("second_authoritative_source_created") is False,
            all(
                value is False
                for key, value in authority.items()
                if key.startswith("actual_")
            ),
            _all_false(runtime),
            all(value == 0 for value in counts.values()),
            all(value is True for value in prerequisite.values()),
        )
    )


def _phase2_structural_valid(phase2: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected_groups = {
        f"{name}_control_projections": tuple(fields)
        for name, fields in phase2.PROJECTION_FIELDS
    }
    group_shapes_valid = all(
        isinstance(report.get(name), list)
        and len(report[name]) == REVIEWED_CONTROL_SHAPE["phase2_control_request_count"]
        and all(set(record) == set(fields) for record in report[name])
        for name, fields in expected_groups.items()
    )
    return all(
        (
            phase2.SCHEMA_VERSION == P2_SCHEMA_VERSION,
            phase2.RECORD_KIND == P2_RECORD_KIND,
            phase2.PASS_RESULT == P2_PASS_RESULT,
            tuple(phase2.CONTROL_FIELDS)
            == ("report_export_audit_control_requests",),
            len(phase2.CONTROL_SCENARIOS)
            == REVIEWED_CONTROL_SHAPE["phase2_control_request_count"],
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("input_accepted") is True,
            report.get("control_input_count")
            == REVIEWED_CONTROL_SHAPE["phase2_control_request_count"],
            report.get("control_projection_group_count")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_group_count"],
            report.get("control_projection_field_total_per_request")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_field_count_per_request"],
            report.get("control_projection_field_total")
            == REVIEWED_CONTROL_SHAPE["phase2_control_field_check_count"],
            len(phase2.INPUT_FIELDS)
            == REVIEWED_CONTROL_SHAPE["phase2_input_field_count"],
            len(phase2.PHASE1_CONTROL_REFERENCE_FIELDS)
            == REVIEWED_CONTROL_SHAPE["phase2_phase1_reference_field_count"],
            group_shapes_valid,
            report.get("persistent_record_created") is False,
        )
    )


def _phase2_runtime_closed(report: Mapping[str, Any]) -> bool:
    return all(
        (
            _all_false(report.get("runtime_boundary")),
            _all_actual_counts_zero(report),
            report.get("persistent_record_created") is False,
        )
    )


def _phase3_structural_valid(phase3: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    scenarios = report.get("scenario_results")
    views = report.get("control_views")
    handlings = report.get("business_line_whitebox_handlings")
    return all(
        (
            phase3.SCHEMA_VERSION == P3_SCHEMA_VERSION,
            phase3.RECORD_KIND == P3_RECORD_KIND,
            phase3.PASS_RESULT == P3_PASS_RESULT,
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("execution_state") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE112-P3-GATE",
            report.get("next_gate") == "IDS-STAGE112-P4-GATE",
            report.get("phase2_control_replay_request_count")
            == REVIEWED_CONTROL_SHAPE["phase2_control_request_count"],
            report.get("phase2_input_field_count")
            == REVIEWED_CONTROL_SHAPE["phase2_input_field_count"],
            report.get("phase2_phase1_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase2_phase1_reference_field_count"],
            report.get("phase2_projection_group_count")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_group_count"],
            report.get("phase2_projection_field_count_per_request")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_field_count_per_request"],
            report.get("phase2_projection_field_check_count")
            == REVIEWED_CONTROL_SHAPE["phase2_control_field_check_count"],
            report.get("scenario_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_count"],
            report.get("scenario_field_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_field_count"],
            report.get("scenario_field_check_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_field_check_count"],
            isinstance(scenarios, list) and len(scenarios) == 5,
            all(set(record) == set(phase3.SCENARIO_FIELDS) for record in scenarios),
            report.get("control_view_count")
            == REVIEWED_CONTROL_SHAPE["phase3_control_view_count"],
            isinstance(views, Mapping) and set(views) == P3_CONTROL_VIEW_NAMES,
            all(
                isinstance(records, list)
                and len(records) == 5
                and all(
                    set(record) == set(phase3.CONTROL_VIEW_FIELDS[name])
                    for record in records
                )
                for name, records in views.items()
            ),
            report.get("business_line_whitebox_handling_count")
            == REVIEWED_CONTROL_SHAPE["phase3_human_handling_count"],
            isinstance(handlings, list) and len(handlings) == 5,
            report.get("whitebox_confirmation_required_scenario_count")
            == REVIEWED_CONTROL_SHAPE["phase3_whitebox_confirmation_required_count"],
            len(phase3.FAILURE_STATES)
            == REVIEWED_CONTROL_SHAPE["phase3_failure_state_count"],
            len(report.get("chinese_feedback", []))
            == REVIEWED_CONTROL_SHAPE["phase3_chinese_feedback_count"],
            report.get("control_references_opaque") is True,
            report.get("persistent_record_created") is False,
        )
    )


def _phase3_runtime_closed(report: Mapping[str, Any]) -> bool:
    return all(
        (
            _all_false(report.get("runtime_boundary")),
            _all_actual_counts_zero(report),
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
        )
    )


def _observed_reviewed_control_shape(
    phase1_contract: Mapping[str, Any],
    phase2: Any,
    phase2_report: Mapping[str, Any],
    phase3: Any,
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, Any]:
    control = phase1_contract.get("report_export_audit_control_contract", {})
    snapshots = phase1_contract.get("generation_snapshot_contract", {})
    failure = phase1_contract.get("failure_and_stop_contract", {})
    feedback = phase1_contract.get("chinese_feedback_contract", {})

    delivery_counts = [
        len(phase4_report.get(name, []))
        for name, _, _ in P4_DELIVERY_GROUPS
    ]
    delivery_field_counts = [
        len(records[0]) if isinstance(records, list) and records else 0
        for records in (phase4_report.get(name, []) for name, _, _ in P4_DELIVERY_GROUPS)
    ]
    observed = {
        "phase1_reference_field_count": control.get(
            "future_control_reference_field_count"
        ),
        "phase1_snapshot_component_count": snapshots.get(
            "required_future_snapshot_component_count"
        ),
        "phase1_failure_state_count": failure.get("failure_state_count"),
        "phase1_chinese_feedback_count": feedback.get("feedback_count"),
        "phase2_control_request_count": phase2_report.get("control_input_count"),
        "phase2_input_field_count": len(phase2.INPUT_FIELDS),
        "phase2_phase1_reference_field_count": len(
            phase2.PHASE1_CONTROL_REFERENCE_FIELDS
        ),
        "phase2_projection_group_count": phase2_report.get(
            "control_projection_group_count"
        ),
        "phase2_projection_field_count_per_request": phase2_report.get(
            "control_projection_field_total_per_request"
        ),
        "phase2_control_field_check_count": phase2_report.get(
            "control_projection_field_total"
        ),
        "phase3_scenario_count": phase3_report.get("scenario_count"),
        "phase3_scenario_field_count": phase3_report.get("scenario_field_count"),
        "phase3_scenario_field_check_count": phase3_report.get(
            "scenario_field_check_count"
        ),
        "phase3_control_view_count": phase3_report.get("control_view_count"),
        "phase3_human_handling_count": phase3_report.get(
            "business_line_whitebox_handling_count"
        ),
        "phase3_whitebox_confirmation_required_count": phase3_report.get(
            "whitebox_confirmation_required_scenario_count"
        ),
        "phase3_failure_state_count": len(phase3.FAILURE_STATES),
        "phase3_chinese_feedback_count": len(
            phase3_report.get("chinese_feedback", ())
        ),
        "phase4_delivery_shape": "/".join(map(str, delivery_counts)),
        "phase4_delivery_field_shape": "/".join(map(str, delivery_field_counts)),
        "phase4_delivery_field_check_count": phase4_report.get(
            "delivery_field_check_count"
        ),
        "phase4_chinese_feedback_count": len(
            phase4_report.get("operator_feedback", ())
        ),
        "phase4_failure_state_count": phase4_report.get("failure_state_count"),
    }
    return observed


def _observed_reviewed_control_shape_matches(
    phase1_contract: Mapping[str, Any],
    phase2: Any,
    phase2_report: Mapping[str, Any],
    phase3: Any,
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    observed = _observed_reviewed_control_shape(
        phase1_contract,
        phase2,
        phase2_report,
        phase3,
        phase3_report,
        phase4_report,
    )
    return all(
        observed[key] == REVIEWED_CONTROL_SHAPE[key]
        for key in observed
    )


def _evidence_binding_and_source_semantics_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    samples = phase4_report.get("report_sample_control_records")
    if not isinstance(scenarios, list) or not isinstance(samples, list):
        return False
    if {item.get("scenario_id") for item in scenarios} != set(P3_SCENARIO_IDS):
        return False
    return all(
        (
            all(
                (
                    bool(item.get("evidence_id_ref"))
                    ^ bool(item.get("evidence_gap_ref")),
                    item.get("evidence_binding_integrity_state")
                    == "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
                    item.get("external_augmentation_source_separation_state")
                    == "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE",
                    item.get("external_augmentation_may_not_be_internal_project_evidence")
                    is True,
                    item.get("external_augmentation_may_not_replace_evidence_binding")
                    is True,
                    item.get("external_augmentation_may_not_close_evidence_gap")
                    is True,
                )
                == (True,) * 6
                for item in scenarios
            ),
            all(
                (
                    bool(item.get("evidence_id_ref"))
                    ^ bool(item.get("evidence_gap_ref")),
                    item.get("evidence_binding_integrity_state")
                    == "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
                    item.get("actual_report_sample_rendered") is False,
                )
                == (True,) * 3
                for item in samples
            ),
        )
    )


def _phase4_structural_valid(phase4: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    fields_by_group = {
        "report_sample_control_records": phase4.REPORT_SAMPLE_FIELDS,
        "report_snapshot_control_records": phase4.REPORT_SNAPSHOT_FIELDS,
        "report_quality_score_control_records": phase4.REPORT_QUALITY_SCORE_FIELDS,
        "report_impact_analysis_control_records": phase4.REPORT_IMPACT_ANALYSIS_FIELDS,
        "report_template_and_whitebox_confirmation_control_records": (
            phase4.REPORT_TEMPLATE_AND_WHITEBOX_CONFIRMATION_FIELDS
        ),
        "regeneration_and_withdrawal_control_records": (
            phase4.REGENERATION_AND_WITHDRAWAL_FIELDS
        ),
    }
    group_shapes_valid = all(
        isinstance(report.get(name), list)
        and len(report[name]) == expected_count
        and all(set(record) == set(fields_by_group[name]) for record in report[name])
        and all(len(record) == expected_fields for record in report[name])
        for name, expected_count, expected_fields in P4_DELIVERY_GROUPS
    )
    return all(
        (
            phase4.SCHEMA_VERSION == P4_SCHEMA_VERSION,
            phase4.RECORD_KIND == P4_RECORD_KIND,
            phase4.PASS_RESULT == P4_PASS_RESULT,
            report.get("schema_version") == P4_SCHEMA_VERSION,
            report.get("record_kind") == P4_RECORD_KIND,
            report.get("result") == P4_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE112-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase2_control_request_count")
            == REVIEWED_CONTROL_SHAPE["phase2_control_request_count"],
            report.get("phase2_input_field_count")
            == REVIEWED_CONTROL_SHAPE["phase2_input_field_count"],
            report.get("phase2_phase1_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase2_phase1_reference_field_count"],
            report.get("phase2_projection_group_count")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_group_count"],
            report.get("phase2_projection_field_count_per_request")
            == REVIEWED_CONTROL_SHAPE["phase2_projection_field_count_per_request"],
            report.get("phase2_projection_field_count_total")
            == REVIEWED_CONTROL_SHAPE["phase2_control_field_check_count"],
            report.get("scenario_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_count"],
            report.get("scenario_field_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_field_count"],
            report.get("scenario_field_check_count")
            == REVIEWED_CONTROL_SHAPE["phase3_scenario_field_check_count"],
            report.get("control_view_count")
            == REVIEWED_CONTROL_SHAPE["phase3_control_view_count"],
            report.get("business_line_whitebox_handling_count")
            == REVIEWED_CONTROL_SHAPE["phase3_human_handling_count"],
            report.get("whitebox_confirmation_required_scenario_count")
            == REVIEWED_CONTROL_SHAPE["phase3_whitebox_confirmation_required_count"],
            report.get("delivery_field_check_count")
            == REVIEWED_CONTROL_SHAPE["phase4_delivery_field_check_count"],
            report.get("failure_state_count")
            == REVIEWED_CONTROL_SHAPE["phase4_failure_state_count"],
            len(report.get("operator_feedback", []))
            == REVIEWED_CONTROL_SHAPE["phase4_chinese_feedback_count"],
            group_shapes_valid,
            report.get("control_references_opaque") is True,
            report.get("persistent_record_created") is False,
        )
    )


def _phase4_runtime_closed(report: Mapping[str, Any]) -> bool:
    return all(
        (
            _all_false(report.get("runtime_boundary")),
            _all_actual_counts_zero(report),
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
        )
    )


def _report_status_audit_and_whitebox_semantics_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    handlings = phase3_report.get("business_line_whitebox_handlings")
    impacts = phase4_report.get("report_impact_analysis_control_records")
    templates = phase4_report.get(
        "report_template_and_whitebox_confirmation_control_records"
    )
    if not all(
        isinstance(value, list)
        for value in (scenarios, handlings, impacts, templates)
    ):
        return False
    required_impact_fields = {
        "source_withdrawal_evidence_gap_report_status_audit_control": (
            "source_withdrawal_report_status_impact_state"
        ),
        "evidence_downgrade_evidence_id_report_status_quality_audit_control": (
            "evidence_downgrade_report_status_impact_state"
        ),
        "index_version_change_evidence_gap_report_snapshot_audit_control": (
            "index_version_change_report_status_impact_state"
        ),
    }
    scenario_by_id = {item.get("scenario_id"): item for item in scenarios}
    impact_by_scenario = {item.get("scenario_id"): item for item in impacts}
    return all(
        (
            {item.get("scenario_id") for item in handlings} == set(P3_SCENARIO_IDS),
            all(
                "REQUIRED" in str(scenario_by_id.get(scenario_id, {}).get(field))
                for scenario_id, field in required_impact_fields.items()
            ),
            all(
                (
                    item.get("automatic_final_conclusion_allowed") is False,
                    item.get("actual_report_status_impact_analysis_performed") is False,
                    item.get("actual_report_status_updated") is False,
                    item.get("actual_report_export_audit_updated") is False,
                )
                == (True,) * 4
                for item in scenarios
            ),
            all(
                (
                    item.get("whitebox_confirmation_required") is True,
                    item.get("human_confirmation_recorded") is False,
                    item.get("final_conclusion_state")
                    == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    _is_control_reference(item.get("report_id_ref")),
                )
                == (True,) * 4
                for item in handlings
            ),
            all(
                "REQUIRED" in str(impact_by_scenario.get(scenario_id, {}).get(field))
                for scenario_id, field in required_impact_fields.items()
            ),
            all(
                (
                    "SEPARATE_FROM_INTERNAL_EVIDENCE"
                    in str(item.get("external_augmentation_source_separation_state")),
                    item.get("business_line_whitebox_confirmation_required") is True,
                    item.get("automatic_final_conclusion_allowed") is False,
                    item.get("actual_human_confirmation_performed") is False,
                    item.get("actual_final_conclusion_published") is False,
                )
                == (True,) * 5
                for item in templates
            ),
        )
    )


def _phase4_lifecycle_and_rollback_valid(
    phase4: Any, report: Mapping[str, Any]
) -> bool:
    lifecycle = report.get("regeneration_and_withdrawal_control_records")
    if not isinstance(lifecycle, list):
        return False
    return all(
        (
            {item.get("control_domain") for item in lifecycle}
            == {"REPORT_REGENERATION", "REPORT_WITHDRAWAL"},
            all(
                (
                    item.get("rollback_target_result") == phase4.P3_PASS_RESULT,
                    item.get("business_line_whitebox_confirmation_required") is True,
                    item.get("human_confirmation_required") is True,
                    item.get("versioned_basis_required") is True,
                    item.get("verifiable_rollback_target_required") is True,
                    item.get("actual_report_regeneration_performed") is False,
                    item.get("actual_report_withdrawal_performed") is False,
                    item.get("persistent_state_write_performed") is False,
                )
                == (True,) * 8
                for item in lifecycle
            ),
        )
    )


def build_report_export_audit_stage_review(
    phase1_contract_provider: Optional[Provider] = None,
    phase2_provider: Optional[Provider] = None,
    phase3_provider: Optional[Provider] = None,
    phase4_provider: Optional[Provider] = None,
) -> dict[str, Any]:
    """机械复审 Stage112 P1--P4 冻结控制工件，任何漂移均关闭为零运行时失败。"""

    try:
        phase2_module, phase3_module, phase4_module = _load_phase_modules()
        phase1_contract = (
            phase1_contract_provider()
            if phase1_contract_provider is not None
            else _default_phase1_contract()
        )
    except Exception:
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase1_structural_valid(phase1_contract, phase2_module):
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase2_report = (
            phase2_provider()
            if phase2_provider is not None
            else phase2_module.execute_report_export_audit_control_slice(
                phase2_module.build_control_input()
            )
        )
    except Exception:
        return _base_report(False, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase2_structural_valid(phase2_module, phase2_report):
        return _base_report(False, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase3_report = (
            phase3_provider()
            if phase3_provider is not None
            else phase3_module.build_report_export_audit_phase3_report()
        )
    except Exception:
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase3_structural_valid(phase3_module, phase3_report):
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase4_report = (
            phase4_provider()
            if phase4_provider is not None
            else phase4_module.build_report_export_audit_phase4_delivery_report()
        )
    except Exception:
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase4_structural_valid(phase4_module, phase4_report):
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _observed_reviewed_control_shape_matches(
        phase1_contract,
        phase2_module,
        phase2_report,
        phase3_module,
        phase3_report,
        phase4_report,
    ):
        return _base_report(False, "CONTROLLED_REVIEW_SHAPE_MISMATCH")

    if not all(
        (
            _phase1_authority_and_runtime_closed(phase1_contract),
            _phase2_runtime_closed(phase2_report),
            _phase3_runtime_closed(phase3_report),
            _phase4_runtime_closed(phase4_report),
        )
    ):
        return _base_report(False, "RUNTIME_SIGNAL_OR_STAGE113_ENTRY_DETECTED")

    authority = phase1_contract["source_authority"]
    if not all(
        (
            authority["source_document_remains_authoritative"],
            authority["evidence_ledger_remains_authoritative"],
            authority["delivered_report_remains_authoritative"],
            authority["existing_audit_log_remains_authoritative"],
            authority["business_line_whitebox_human_review_remains_authoritative"],
            authority["second_authoritative_source_created"] is False,
            phase3_report["second_authoritative_source_created"] is False,
            phase4_report["second_authoritative_source_created"] is False,
        )
    ):
        return _base_report(False, "SINGLE_AUTHORITY_BOUNDARY_BREACH")

    if not _evidence_binding_and_source_semantics_valid(
        phase3_report, phase4_report
    ):
        return _base_report(False, "EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH")
    if not _report_status_audit_and_whitebox_semantics_valid(
        phase3_report, phase4_report
    ):
        return _base_report(False, "REPORT_STATUS_AUDIT_AND_WHITEBOX_SEMANTICS_MISMATCH")
    if not _phase4_lifecycle_and_rollback_valid(phase4_module, phase4_report):
        return _base_report(False, "REPORT_LIFECYCLE_OR_ROLLBACK_BOUNDARY_MISMATCH")

    report = _base_report(True, None)
    report.update(
        {
            "phase1_static_contract_reviewed": True,
            "phase2_control_slice_reviewed": True,
            "phase3_controlled_scenarios_reviewed": True,
            "phase4_delivery_evidence_reviewed": True,
            "control_references_opaque": True,
            "single_authority_boundary_preserved": True,
            "report_export_audit_semantics_preserved": True,
            "business_line_whitebox_gate_preserved": True,
            "phase4_to_phase3_rollback_preserved": True,
            "stage112_review_started": True,
            "whole_stage_review_completed_in_memory_only": True,
            "reviewed_control_shape": dict(REVIEWED_CONTROL_SHAPE),
            "reviewed_phase_results": {
                "phase1_contract_state": P1_CONTRACT_STATE,
                "phase2_control_slice_result": P2_PASS_RESULT,
                "phase3_controlled_scenarios_result": P3_PASS_RESULT,
                "phase4_delivery_evidence_result": P4_PASS_RESULT,
            },
            "chinese_feedback": list(OPERATOR_FEEDBACK),
        }
    )
    return report
