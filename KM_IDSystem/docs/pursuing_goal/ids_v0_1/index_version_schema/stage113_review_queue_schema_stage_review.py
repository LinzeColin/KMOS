"""Stage113 复核队列 Schema 的纯内存整阶段机械复审。

模块只复审冻结 Stage113 P1--P4 控制工件。它不读取真实业务资料、OCR、证据账本、
报告、审计或数据库，不创建复核队列、UI 或审计，不写入持久化状态，也不调用模型、
Agent、OVH 或生产服务。
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "ids.stage113.review_queue_schema.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REVIEW_QUEUE_SCHEMA_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REVIEW_QUEUE_SCHEMA_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE113-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE114-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase1.v1"
P1_RECORD_KIND = "CONTROL_ONLY_REVIEW_QUEUE_SCHEMA_PHASE1_CONTRACT"
P1_CONTRACT_STATE = "REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA"
P2_PASS_RESULT = "PASS_IN_MEMORY_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_SCENARIOS"
P3_PASS_RESULT = "PASS_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage113_review_queue_schema_contract.json")
P3_SCENARIO_IDS = (
    "low_quality_ocr_review_operation_control",
    "conflicting_material_review_audit_control",
    "withdrawn_material_re_review_control",
    "evidence_trust_report_quality_impact_control",
    "external_augmentation_internal_evidence_replacement_control",
)
P3_CONTROL_VIEW_NAMES = {
    "review_queue_trigger_and_status_control_view",
    "review_operation_audit_control_view",
    "evidence_trust_and_report_quality_impact_control_view",
    "external_augmentation_source_separation_control_view",
    "business_line_whitebox_and_execution_boundary_control_view",
}
P4_DELIVERY_GROUPS = (
    ("review_queue_sample_control_records", 5, 17),
    ("review_audit_log_sample_control_records", 5, 13),
    ("review_ui_flow_explanation_control_records", 5, 13),
    ("human_judgment_boundary_control_records", 5, 15),
    ("business_line_whitebox_confirmation_control_records", 5, 14),
    ("rollback_and_re_review_instruction_control_records", 2, 14),
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 29,
    "phase1_review_trigger_type_count": 4,
    "phase1_review_status_count": 5,
    "phase1_review_audit_reference_field_count": 7,
    "phase1_evidence_and_report_impact_control_count": 4,
    "phase1_failure_state_count": 19,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 32,
    "phase2_phase1_reference_field_count": 29,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 101,
    "phase2_control_field_check_count": 505,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 52,
    "phase3_scenario_field_check_count": 260,
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
    "actor_time_reason_old_new_review_audit_controls_required": True,
    "evidence_trust_and_report_quality_impact_controls_required": True,
    "external_augmentation_source_separation_required": True,
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
    "REVIEW_AUDIT_IMPACT_AND_WHITEBOX_SEMANTICS_MISMATCH",
    "DELIVERY_AND_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_STAGE114_ENTRY_DETECTED",
    "CONTROL_REFERENCE_OPAQUENESS_MISMATCH",
)

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "existing_audit_log_read_performed",
    "low_ocr_evaluation_performed",
    "source_conflict_evaluation_performed",
    "parsing_failure_evaluation_performed",
    "evidence_risk_evaluation_performed",
    "review_queue_schema_migration_performed",
    "review_queue_workflow_execution_performed",
    "review_ui_rendered",
    "review_queue_entry_created",
    "review_status_transition_performed",
    "review_audit_write_performed",
    "evidence_risk_writeback_performed",
    "evidence_trust_level_change_performed",
    "report_quality_score_change_performed",
    "report_status_update_performed",
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
    "stage113_review_runtime_executed",
    "stage114_runtime_started",
)

REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_business_source_access_count",
    "actual_external_reference_access_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_existing_audit_log_access_count",
    "actual_review_queue_schema_migration_count",
    "actual_review_queue_entry_count",
    "actual_review_status_transition_count",
    "actual_review_audit_write_count",
    "actual_evidence_risk_writeback_count",
    "actual_evidence_trust_level_change_count",
    "actual_report_quality_score_change_count",
    "actual_report_status_update_count",
    "actual_review_ui_render_count",
    "actual_human_confirmation_count",
    "actual_review_queue_rollback_count",
    "actual_re_review_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

OPERATOR_FEEDBACK = (
    "复核队列 Schema 整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "actor、time、reason、old value、new value 与 review result 保持审计控制引用，证据可信等级和报告质量影响保持未来控制。",
    "复核状态、审计、证据与报告影响、人工判断和业务线白箱确认保持后续授权，外部增强继续与内部证据分离。",
    "真实资料、OCR、复核队列、UI、审计、数据库、模型、Agent、OVH、生产、Stage114 和正式上传保持未执行。",
)

Provider = Callable[[], Mapping[str, Any]]


def _load_phase_modules() -> tuple[Any, Any, Any]:
    base = "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
    return (
        importlib.import_module(f"{base}stage113_review_queue_schema_control_slice"),
        importlib.import_module(
            f"{base}stage113_review_queue_schema_controlled_scenarios"
        ),
        importlib.import_module(f"{base}stage113_review_queue_schema_delivery"),
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
        "review_audit_impact_and_whitebox_semantics_preserved": False,
        "phase4_to_phase3_rollback_preserved": False,
        "stage113_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "stage114_started": False,
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
        and value.startswith(":control:stage113-p2:")
        and value.endswith(":reference-only")
    )


def _phase1_structural_valid(contract: Mapping[str, Any], phase2: Any) -> bool:
    if not isinstance(contract, Mapping):
        return False
    control = contract.get("review_queue_schema_control_contract")
    audit = contract.get("review_audit_control_contract")
    impact = contract.get("evidence_and_report_impact_control_contract")
    failure = contract.get("failure_and_stop_contract")
    feedback = contract.get("chinese_feedback_contract")
    boundary = contract.get("stage_and_phase_boundary")
    predecessor = contract.get("predecessor_review_contract")
    local_code = contract.get("local_code")
    if not all(
        isinstance(value, Mapping)
        for value in (
            control,
            audit,
            impact,
            failure,
            feedback,
            boundary,
            predecessor,
            local_code,
        )
    ):
        return False
    expected_audit_fields = (
        "review_actor_ref",
        "review_time_ref",
        "review_reason_ref",
        "old_value_ref",
        "new_value_ref",
        "review_result_ref",
        "review_audit_record_ref",
    )
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("record_kind") == P1_RECORD_KIND,
            contract.get("stage") == "STAGE-113",
            contract.get("phase") == "IDS-STAGE113-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE113-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE113-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE113-P2-GATE",
            tuple(control.get("future_control_reference_fields", ()))
            == tuple(phase2.PHASE1_CONTROL_REFERENCE_FIELDS),
            control.get("future_control_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase1_reference_field_count"],
            tuple(control.get("required_review_trigger_types", ()))
            == (
                "low_ocr_confidence",
                "source_conflict",
                "parsing_failure",
                "evidence_risk",
            ),
            control.get("required_review_trigger_type_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_trigger_type_count"],
            tuple(control.get("fixed_review_statuses", ()))
            == tuple(phase2.FIXED_REVIEW_STATUSES),
            control.get("fixed_review_status_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_status_count"],
            control.get("control_references_are_labels_only") is True,
            control.get("all_required_review_triggers_must_enter_future_review_queue")
            is True,
            control.get(
                "review_status_transition_rules_are_future_business_line_whitebox_authorized_work_only"
            )
            is True,
            control.get(
                "review_result_can_only_affect_future_evidence_trust_and_report_quality_controls"
            )
            is True,
            control.get("external_augmentation_is_not_internal_project_evidence") is True,
            tuple(audit.get("required_future_audit_reference_fields", ()))
            == expected_audit_fields,
            audit.get("required_future_audit_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_audit_reference_field_count"],
            all(
                audit.get(field) is True
                for field in (
                    "actor_time_reason_old_new_controls_required",
                    "review_result_reference_required",
                    "re_review_reference_required",
                    "archive_reference_required",
                    "human_confirmation_item_required",
                    "business_line_whitebox_confirmation_required",
                )
            ),
            all(
                impact.get(field) is True
                for field in (
                    "evidence_id_or_evidence_gap_reference_required",
                    "future_evidence_trust_level_before_after_references_required",
                    "future_report_quality_score_before_after_references_required",
                    "future_report_status_impact_reference_required",
                    "review_result_does_not_create_business_fact_or_final_verdict",
                )
            ),
            failure.get("failure_state_count")
            == REVIEWED_CONTROL_SHAPE["phase1_failure_state_count"],
            predecessor.get("stage112_review_required") is True,
            predecessor.get("stage112_review_result")
            == "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED",
            all(
                predecessor.get(field) is True
                for field in (
                    "report_evidence_binding_control_preserved",
                    "report_status_quality_snapshot_and_audit_semantics_preserved",
                    "external_augmentation_source_separation_preserved",
                    "business_line_whitebox_gate_preserved",
                    "phase4_to_phase3_rollback_preserved",
                )
            ),
            local_code.get("static_contract_only") is True,
            all(
                local_code.get(field) is False
                for field in (
                    "review_queue_runtime_implemented",
                    "review_queue_schema_migration_implemented",
                    "review_ui_implemented",
                    "review_audit_write_implemented",
                    "evidence_or_report_impact_runtime_implemented",
                    "database_connection_implemented",
                )
            ),
            boundary.get("stage112_review_evidence_declared") is True,
            boundary.get("stage113_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("phase2_started") is False,
            boundary.get("phase3_started") is False,
            boundary.get("phase4_started") is False,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage114_started") is False,
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
            tuple(phase2.CONTROL_FIELDS) == ("review_queue_schema_control_requests",),
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
            report.get("valid") is True,
            report.get("execution_state") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE113-P3-GATE",
            report.get("next_gate") == "IDS-STAGE113-P4-GATE",
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
            isinstance(scenarios, list)
            and len(scenarios) == REVIEWED_CONTROL_SHAPE["phase3_scenario_count"],
            tuple(item.get("scenario_id") for item in scenarios) == P3_SCENARIO_IDS,
            all(set(record) == set(phase3.SCENARIO_FIELDS) for record in scenarios),
            report.get("control_view_count")
            == REVIEWED_CONTROL_SHAPE["phase3_control_view_count"],
            isinstance(views, Mapping) and set(views) == P3_CONTROL_VIEW_NAMES,
            all(
                isinstance(records, list)
                and len(records) == REVIEWED_CONTROL_SHAPE["phase3_scenario_count"]
                and all(
                    set(record) == set(phase3.CONTROL_VIEW_FIELDS[name])
                    for record in records
                )
                for name, records in views.items()
            ),
            report.get("business_line_whitebox_handling_count")
            == REVIEWED_CONTROL_SHAPE["phase3_human_handling_count"],
            isinstance(handlings, list)
            and len(handlings) == REVIEWED_CONTROL_SHAPE["phase3_human_handling_count"],
            all(
                set(record) == set(phase3.BUSINESS_LINE_WHITEBOX_HANDLING_FIELDS)
                for record in handlings
            ),
            report.get("whitebox_confirmation_required_scenario_count")
            == REVIEWED_CONTROL_SHAPE[
                "phase3_whitebox_confirmation_required_count"
            ],
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
    control = phase1_contract.get("review_queue_schema_control_contract", {})
    audit = phase1_contract.get("review_audit_control_contract", {})
    impact = phase1_contract.get("evidence_and_report_impact_control_contract", {})
    failure = phase1_contract.get("failure_and_stop_contract", {})
    feedback = phase1_contract.get("chinese_feedback_contract", {})
    delivery_counts = [
        len(phase4_report.get(name, [])) for name, _count, _fields in P4_DELIVERY_GROUPS
    ]
    delivery_field_counts = [
        len(records[0]) if isinstance(records, list) and records else 0
        for records in (
            phase4_report.get(name, []) for name, _count, _fields in P4_DELIVERY_GROUPS
        )
    ]
    return {
        "phase1_reference_field_count": control.get(
            "future_control_reference_field_count"
        ),
        "phase1_review_trigger_type_count": control.get(
            "required_review_trigger_type_count"
        ),
        "phase1_review_status_count": control.get("fixed_review_status_count"),
        "phase1_review_audit_reference_field_count": audit.get(
            "required_future_audit_reference_field_count"
        ),
        "phase1_evidence_and_report_impact_control_count": sum(
            impact.get(field) is True
            for field in (
                "evidence_id_or_evidence_gap_reference_required",
                "future_evidence_trust_level_before_after_references_required",
                "future_report_quality_score_before_after_references_required",
                "future_report_status_impact_reference_required",
            )
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
        "actor_time_reason_old_new_review_audit_controls_required": all(
            audit.get(field) is True
            for field in (
                "actor_time_reason_old_new_controls_required",
                "review_result_reference_required",
                "re_review_reference_required",
                "archive_reference_required",
            )
        ),
        "evidence_trust_and_report_quality_impact_controls_required": all(
            impact.get(field) is True
            for field in (
                "future_evidence_trust_level_before_after_references_required",
                "future_report_quality_score_before_after_references_required",
                "future_report_status_impact_reference_required",
            )
        ),
        "external_augmentation_source_separation_required": control.get(
            "external_augmentation_is_not_internal_project_evidence"
        ),
        "business_line_whitebox_confirmation_required": audit.get(
            "business_line_whitebox_confirmation_required"
        ),
        "phase4_to_phase3_rollback_required": all(
            record.get("rollback_target_result") == P3_PASS_RESULT
            for record in phase4_report.get(
                "rollback_and_re_review_instruction_control_records", []
            )
        ),
    }


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
    return all(observed.get(key) == value for key, value in REVIEWED_CONTROL_SHAPE.items())


def _phase4_structural_valid(phase4: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    fields_by_group = {
        "review_queue_sample_control_records": phase4.REVIEW_QUEUE_SAMPLE_FIELDS,
        "review_audit_log_sample_control_records": phase4.REVIEW_AUDIT_LOG_SAMPLE_FIELDS,
        "review_ui_flow_explanation_control_records": (
            phase4.REVIEW_UI_FLOW_EXPLANATION_FIELDS
        ),
        "human_judgment_boundary_control_records": (
            phase4.HUMAN_JUDGMENT_BOUNDARY_FIELDS
        ),
        "business_line_whitebox_confirmation_control_records": (
            phase4.BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS
        ),
        "rollback_and_re_review_instruction_control_records": (
            phase4.ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS
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
            report.get("current_gate") == "IDS-STAGE113-P4-GATE",
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
            == REVIEWED_CONTROL_SHAPE[
                "phase3_whitebox_confirmation_required_count"
            ],
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


def _control_references_remain_opaque(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    samples = phase4_report.get("review_queue_sample_control_records")
    audits = phase4_report.get("review_audit_log_sample_control_records")
    flows = phase4_report.get("review_ui_flow_explanation_control_records")
    judgments = phase4_report.get("human_judgment_boundary_control_records")
    whitebox = phase4_report.get(
        "business_line_whitebox_confirmation_control_records"
    )
    lifecycle = phase4_report.get("rollback_and_re_review_instruction_control_records")
    if not all(
        isinstance(value, list)
        for value in (scenarios, samples, audits, flows, judgments, whitebox, lifecycle)
    ):
        return False
    scenario_reference_fields = (
        "review_queue_item_ref",
        "review_queue_schema_ref",
        "review_queue_entry_reason_ref",
        "review_trigger_type_ref",
        "review_status_ref",
        "source_document_ref",
        "evidence_risk_ref",
        "low_ocr_confidence_ref",
        "source_conflict_ref",
        "parsing_failure_ref",
        "external_augmentation_underlying_source_type_ref",
        "evidence_trust_level_before_ref",
        "evidence_trust_level_after_ref",
        "report_quality_score_before_ref",
        "report_quality_score_after_ref",
        "report_status_impact_ref",
        "review_audit_record_ref",
        "review_actor_ref",
        "review_time_ref",
        "review_reason_ref",
        "old_value_ref",
        "new_value_ref",
        "review_result_ref",
        "re_review_reference_ref",
        "archive_reference_ref",
        "human_confirmation_item_ref",
        "business_line_whitebox_confirmation_gate_ref",
        "review_queue_writeback_control_label",
        "external_public_reference_control_label",
        "model_reasoning_control_label",
    )
    delivery_reference = lambda value: (
        isinstance(value, str)
        and value.startswith(":control:stage113-p4:")
        and value.endswith(":reference-only")
    )
    return all(
        (
            all(
                (
                    bool(item.get("evidence_id_ref"))
                    ^ bool(item.get("evidence_gap_ref")),
                    all(
                        _is_control_reference(item.get(field))
                        for field in scenario_reference_fields
                    ),
                    item.get("evidence_id_ref") is None
                    or _is_control_reference(item.get("evidence_id_ref")),
                    item.get("evidence_gap_ref") is None
                    or _is_control_reference(item.get("evidence_gap_ref")),
                )
                == (True,) * 4
                for item in scenarios
            ),
            all(
                delivery_reference(item.get("delivery_record_id"))
                and all(
                    _is_control_reference(item.get(field))
                    for field in (
                        "review_queue_item_ref",
                        "review_queue_schema_ref",
                        "review_queue_entry_reason_ref",
                        "review_trigger_type_ref",
                        "review_status_ref",
                        "source_document_ref",
                        "evidence_risk_ref",
                        "low_ocr_confidence_ref",
                        "source_conflict_ref",
                        "parsing_failure_ref",
                    )
                )
                and (
                    item.get("evidence_id_ref") is None
                    or _is_control_reference(item.get("evidence_id_ref"))
                )
                and (
                    item.get("evidence_gap_ref") is None
                    or _is_control_reference(item.get("evidence_gap_ref"))
                )
                for item in samples
            ),
            all(
                delivery_reference(item.get("delivery_record_id"))
                and all(
                    _is_control_reference(item.get(field))
                    for field in (
                        "review_audit_record_ref",
                        "review_actor_ref",
                        "review_time_ref",
                        "review_reason_ref",
                        "old_value_ref",
                        "new_value_ref",
                        "review_result_ref",
                        "re_review_reference_ref",
                        "archive_reference_ref",
                    )
                )
                for item in audits
            ),
            all(
                delivery_reference(item.get("delivery_record_id"))
                and _is_control_reference(item.get("review_queue_item_ref"))
                and _is_control_reference(item.get("review_status_ref"))
                and delivery_reference(item.get("review_ui_flow_step_ref"))
                and delivery_reference(item.get("review_ui_entry_control_ref"))
                for item in flows
            ),
            all(
                delivery_reference(item.get("delivery_record_id"))
                and all(
                    _is_control_reference(item.get(field))
                    for field in (
                        "human_confirmation_item_ref",
                        "business_line_whitebox_confirmation_gate_ref",
                        "review_result_ref",
                        "evidence_trust_level_before_ref",
                        "evidence_trust_level_after_ref",
                        "report_quality_score_before_ref",
                        "report_quality_score_after_ref",
                        "report_status_impact_ref",
                    )
                )
                for item in judgments
            ),
            all(
                delivery_reference(item.get("delivery_record_id"))
                and _is_control_reference(item.get("human_confirmation_item_ref"))
                and _is_control_reference(
                    item.get("business_line_whitebox_confirmation_gate_ref")
                )
                for item in whitebox
            ),
            all(
                all(
                    delivery_reference(item.get(field))
                    for field in (
                        "instruction_id",
                        "trigger_state_ref",
                        "rollback_target_ref",
                        "predecessor_phase_ref",
                        "review_queue_schema_ref",
                        "review_audit_record_ref",
                    )
                )
                for item in lifecycle
            ),
        )
    )


def _audit_impact_and_whitebox_semantics_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    handlings = phase3_report.get("business_line_whitebox_handlings")
    samples = phase4_report.get("review_queue_sample_control_records")
    audits = phase4_report.get("review_audit_log_sample_control_records")
    judgments = phase4_report.get("human_judgment_boundary_control_records")
    whitebox = phase4_report.get(
        "business_line_whitebox_confirmation_control_records"
    )
    if not all(
        isinstance(value, list)
        for value in (scenarios, handlings, samples, audits, judgments, whitebox)
    ):
        return False
    expected_external_state = (
        "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
        "SEPARATE_FROM_INTERNAL_EVIDENCE"
    )
    audit_reference_fields = (
        "review_audit_record_ref",
        "review_actor_ref",
        "review_time_ref",
        "review_reason_ref",
        "old_value_ref",
        "new_value_ref",
        "review_result_ref",
        "re_review_reference_ref",
        "archive_reference_ref",
    )
    impact_reference_fields = (
        "evidence_trust_level_before_ref",
        "evidence_trust_level_after_ref",
        "report_quality_score_before_ref",
        "report_quality_score_after_ref",
        "report_status_impact_ref",
    )
    return all(
        (
            {item.get("scenario_id") for item in scenarios} == set(P3_SCENARIO_IDS),
            {item.get("scenario_id") for item in handlings} == set(P3_SCENARIO_IDS),
            {item.get("scenario_id") for item in samples} == set(P3_SCENARIO_IDS),
            {item.get("scenario_id") for item in audits} == set(P3_SCENARIO_IDS),
            {item.get("scenario_id") for item in judgments} == set(P3_SCENARIO_IDS),
            {item.get("scenario_id") for item in whitebox} == set(P3_SCENARIO_IDS),
            all(
                (
                    bool(item.get("evidence_id_ref"))
                    ^ bool(item.get("evidence_gap_ref")),
                    all(_is_control_reference(item.get(field)) for field in audit_reference_fields),
                    all(
                        _is_control_reference(item.get(field))
                        for field in impact_reference_fields
                    ),
                    item.get("review_operation_audit_state")
                    == "CONTROL_REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_REFERENCE_ONLY_NOT_RECORDED",
                    item.get("review_result_evidence_trust_impact_state")
                    == "CONTROL_REVIEW_RESULT_EVIDENCE_TRUST_REFERENCE_ONLY_NOT_APPLIED",
                    item.get("review_result_report_quality_impact_state")
                    == "CONTROL_REVIEW_RESULT_REPORT_QUALITY_REFERENCE_ONLY_NOT_APPLIED",
                    item.get("external_augmentation_source_separation_state")
                    == expected_external_state,
                    all(
                        item.get(field) is True
                        for field in (
                            "external_augmentation_may_not_be_internal_project_evidence",
                            "external_augmentation_may_not_replace_evidence_binding",
                            "external_augmentation_may_not_close_evidence_gap",
                            "business_line_whitebox_confirmation_required",
                        )
                    ),
                    item.get("automatic_review_operation_allowed") is False,
                    item.get("automatic_evidence_or_report_writeback_allowed") is False,
                    all(
                        item.get(field) is False
                        for field in (
                            "actual_review_queue_or_ui_execution_performed",
                            "actual_review_audit_or_database_execution_performed",
                            "actual_evidence_or_report_writeback_execution_performed",
                            "actual_human_confirmation_execution_performed",
                        )
                    ),
                )
                == (True,) * 11
                for item in scenarios
            ),
            all(
                (
                    item.get("confirmation_required") is True,
                    item.get("actual_human_confirmation_execution_performed") is False,
                    item.get("handling_state")
                    == "BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED",
                )
                == (True,) * 3
                for item in handlings
            ),
            all(
                (
                    bool(item.get("evidence_id_ref"))
                    ^ bool(item.get("evidence_gap_ref")),
                    item.get("review_queue_sample_state")
                    == "CONTROL_REVIEW_QUEUE_SAMPLE_REFERENCE_ONLY_NOT_RENDERED",
                    item.get("business_line_whitebox_confirmation_required") is True,
                    item.get("actual_review_queue_sample_rendered") is False,
                )
                == (True,) * 4
                for item in samples
            ),
            all(
                all(_is_control_reference(item.get(field)) for field in audit_reference_fields)
                and item.get("review_audit_sample_state")
                == "CONTROL_REVIEW_AUDIT_LOG_SAMPLE_REFERENCE_ONLY_NOT_WRITTEN"
                and item.get("actual_review_audit_log_written") is False
                for item in audits
            ),
            all(
                all(
                    _is_control_reference(item.get(field))
                    for field in (
                        "human_confirmation_item_ref",
                        "business_line_whitebox_confirmation_gate_ref",
                        "review_result_ref",
                        *impact_reference_fields,
                    )
                )
                and item.get("human_judgment_boundary_state")
                == "CONTROL_BUSINESS_LINE_WHITEBOX_JUDGMENT_REQUIRED_NOT_RECORDED"
                and item.get("business_line_whitebox_confirmation_required") is True
                and item.get("automatic_evidence_or_report_writeback_allowed") is False
                and item.get("actual_human_confirmation_performed") is False
                for item in judgments
            ),
            all(
                (
                    item.get("external_augmentation_source_separation_state")
                    == expected_external_state,
                    item.get("confirmation_required") is True,
                    item.get("automatic_final_conclusion_allowed") is False,
                    item.get("actual_human_confirmation_execution_performed") is False,
                    item.get("actual_final_conclusion_published") is False,
                    item.get("actual_review_state_transition_performed") is False,
                    item.get("actual_evidence_or_report_writeback_execution_performed")
                    is False,
                    item.get("persistent_state_write_performed") is False,
                )
                == (True,) * 8
                for item in whitebox
            ),
        )
    )


def _phase4_lifecycle_and_rollback_valid(phase4: Any, report: Mapping[str, Any]) -> bool:
    lifecycle = report.get("rollback_and_re_review_instruction_control_records")
    if not isinstance(lifecycle, list):
        return False
    return all(
        (
            {item.get("control_domain") for item in lifecycle}
            == {"REVIEW_QUEUE_ROLLBACK", "RE_REVIEW"},
            all(
                (
                    item.get("rollback_target_result") == phase4.P3_PASS_RESULT,
                    item.get("business_line_whitebox_confirmation_required") is True,
                    item.get("human_confirmation_required") is True,
                    item.get("versioned_basis_required") is True,
                    item.get("verifiable_rollback_target_required") is True,
                    item.get("actual_review_queue_rollback_performed") is False,
                    item.get("actual_re_review_performed") is False,
                )
                == (True,) * 7
                for item in lifecycle
            ),
        )
    )


def build_review_queue_schema_stage_review(
    phase1_contract_provider: Optional[Provider] = None,
    phase2_provider: Optional[Provider] = None,
    phase3_provider: Optional[Provider] = None,
    phase4_provider: Optional[Provider] = None,
) -> dict[str, Any]:
    """机械复审 Stage113 P1--P4 冻结控制工件，任何漂移均关闭为零运行时失败。"""

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
            else phase2_module.execute_review_queue_schema_control_slice(
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
            else phase3_module.build_review_queue_schema_phase3_report()
        )
    except Exception:
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase3_structural_valid(phase3_module, phase3_report):
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase4_report = (
            phase4_provider()
            if phase4_provider is not None
            else phase4_module.build_review_queue_schema_phase4_delivery_report()
        )
    except Exception:
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase4_structural_valid(phase4_module, phase4_report):
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase4_lifecycle_and_rollback_valid(phase4_module, phase4_report):
        return _base_report(False, "DELIVERY_AND_ROLLBACK_BOUNDARY_MISMATCH")
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
        return _base_report(False, "RUNTIME_SIGNAL_OR_STAGE114_ENTRY_DETECTED")

    authority = phase1_contract["source_authority"]
    if not all(
        (
            authority["source_document_remains_authoritative"],
            authority["evidence_ledger_remains_authoritative"],
            authority["delivered_report_remains_authoritative"],
            authority["existing_audit_log_remains_authoritative"],
            authority["business_line_whitebox_human_review_remains_authoritative"],
            authority["control_artifacts_are_engineering_context_only"],
            authority["second_authoritative_source_created"] is False,
            phase3_report["second_authoritative_source_created"] is False,
            phase4_report["second_authoritative_source_created"] is False,
        )
    ):
        return _base_report(False, "SINGLE_AUTHORITY_BOUNDARY_BREACH")

    if not _control_references_remain_opaque(phase3_report, phase4_report):
        return _base_report(False, "CONTROL_REFERENCE_OPAQUENESS_MISMATCH")

    if not _audit_impact_and_whitebox_semantics_valid(phase3_report, phase4_report):
        return _base_report(
            False, "REVIEW_AUDIT_IMPACT_AND_WHITEBOX_SEMANTICS_MISMATCH"
        )

    report = _base_report(True, None)
    report.update(
        {
            "phase1_static_contract_reviewed": True,
            "phase2_control_slice_reviewed": True,
            "phase3_controlled_scenarios_reviewed": True,
            "phase4_delivery_evidence_reviewed": True,
            "control_references_opaque": True,
            "single_authority_boundary_preserved": True,
            "review_audit_impact_and_whitebox_semantics_preserved": True,
            "phase4_to_phase3_rollback_preserved": True,
            "stage113_review_started": True,
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
