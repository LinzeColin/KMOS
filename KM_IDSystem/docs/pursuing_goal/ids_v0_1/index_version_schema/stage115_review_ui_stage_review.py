"""Stage115 复核 UI 整阶段纯内存机械复审。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


Provider = Callable[[], Any]

SCHEMA_VERSION = "ids.stage115.review_ui.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_UI_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REVIEW_UI_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REVIEW_UI_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE115-REVIEW-GATE"
NEXT_GATE = "UNASSIGNED_SUCCESSOR_GATE"

P1_SCHEMA_VERSION = "ids.stage115.review_ui.phase1.v1"
P1_CONTRACT_STATE = "REVIEW_UI_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage115.review_ui.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_UI"
P2_PASS_RESULT = "PASS_IN_MEMORY_REVIEW_UI_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage115.review_ui.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_UI_SCENARIOS"
P3_PASS_RESULT = "PASS_IN_MEMORY_REVIEW_UI_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage115.review_ui.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_UI_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REVIEW_UI_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage115_review_ui_contract.json")

P1_REQUIRED_REVIEW_TRIGGER_TYPES = (
    "low_ocr_confidence",
    "source_conflict",
    "parsing_failure",
    "evidence_risk",
)
P1_FIXED_REVIEW_STATUSES = (
    "pending_review",
    "confirmed",
    "rejected",
    "needs_more_material",
    "archived",
)
P1_FIXED_REVIEW_ACTIONS = (
    "submit_for_review",
    "confirm",
    "reject",
    "request_more_material",
    "archive",
)
P1_AUDIT_REFERENCE_FIELDS = (
    "review_actor_ref",
    "review_time_ref",
    "review_transition_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "review_audit_record_ref",
)

P3_SCENARIO_IDS = (
    "low_quality_ocr_review_operation_control",
    "conflicting_material_review_audit_control",
    "withdrawn_material_re_review_control",
    "evidence_trust_report_quality_impact_control",
    "external_augmentation_internal_evidence_replacement_control",
)

P4_DELIVERY_GROUPS = (
    ("review_queue_sample_control_records", 5, 17),
    ("review_audit_log_sample_control_records", 5, 13),
    ("review_ui_flow_explanation_control_records", 5, 13),
    ("human_judgment_boundary_control_records", 5, 15),
    ("business_line_whitebox_confirmation_control_records", 5, 14),
    ("rollback_and_re_review_instruction_control_records", 2, 14),
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 19,
    "phase1_review_trigger_type_count": 4,
    "phase1_review_status_count": 5,
    "phase1_ui_action_label_count": 5,
    "phase1_chinese_ui_section_count": 5,
    "phase1_review_audit_reference_field_count": 7,
    "phase1_failure_state_count": 20,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 23,
    "phase2_phase1_reference_field_count": 19,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 117,
    "phase2_control_field_check_count": 585,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 47,
    "phase3_scenario_field_check_count": 235,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 5,
    "phase3_whitebox_confirmation_required_count": 5,
    "phase3_failure_state_count": 15,
    "phase3_chinese_feedback_count": 5,
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
    "RUNTIME_SIGNAL_OR_UNASSIGNED_SUCCESSOR_ENTRY_DETECTED",
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
    "withdrawn_material_evaluation_performed",
    "evidence_risk_evaluation_performed",
    "review_queue_entry_created",
    "review_workflow_execution_performed",
    "review_ui_rendered",
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
    "formal_global_upload_performed",
    "github_upload_performed",
    "push_performed",
    "stage115_review_runtime_executed",
    "unassigned_successor_started",
)

REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_business_source_access_count",
    "actual_external_reference_access_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_existing_audit_log_access_count",
    "actual_review_workflow_execution_count",
    "actual_review_queue_entry_count",
    "actual_review_status_transition_count",
    "actual_review_ui_render_count",
    "actual_review_audit_write_count",
    "actual_evidence_risk_writeback_count",
    "actual_evidence_trust_level_change_count",
    "actual_report_quality_score_change_count",
    "actual_report_status_update_count",
    "actual_human_confirmation_count",
    "actual_review_ui_rollback_count",
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
    "复核 UI 整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "actor、time、reason、old value、new value 与 review result 保持审计控制引用，证据可信等级和报告质量／状态影响保持未来控制。",
    "复核队列、审计、影响、人工判断与业务线白箱确认继续由后续授权处理，外部增强保持与内部证据分离。",
    "真实资料、OCR、复核 UI、队列、审计、数据库、模型、Agent、OVH、生产、未分配后继和正式全局上传保持未执行。",
)


def _load_phase_modules() -> tuple[Any, Any, Any]:
    if __package__ is None:
        raise RuntimeError("stage review package unavailable")
    package = __package__
    return (
        importlib.import_module(f"{package}.stage115_review_ui_control_slice"),
        importlib.import_module(
            f"{package}.stage115_review_ui_controlled_scenarios"
        ),
        importlib.import_module(f"{package}.stage115_review_ui_delivery"),
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
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "stage115_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "unassigned_successor_started": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _closed_runtime_mapping(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(item is False for item in value.values())
    )


def _zero_actual_counts_in(value: Mapping[str, Any]) -> bool:
    actual_counts = [
        item
        for key, item in value.items()
        if key.startswith("actual_") and key.endswith("_count")
    ]
    return bool(actual_counts) and all(
        type(item) is int and item == 0 for item in actual_counts
    )


def _control_runtime_closed(value: Mapping[str, Any]) -> bool:
    return all(
        (
            value.get("persistent_record_created") is False,
            _closed_runtime_mapping(value.get("runtime_boundary")),
            _zero_actual_counts_in(value),
        )
    )


def _authority_preserved(authority: object) -> bool:
    if not isinstance(authority, Mapping):
        return False
    true_fields = (
        "source_document_remains_authoritative",
        "evidence_ledger_remains_authoritative",
        "delivered_report_remains_authoritative",
        "existing_audit_log_remains_authoritative",
        "business_line_whitebox_human_review_remains_authoritative",
        "control_artifacts_are_engineering_context_only",
    )
    false_fields = (
        "second_authoritative_source_created",
        "actual_source_document_read_performed",
        "actual_external_reference_read_performed",
        "actual_evidence_ledger_read_performed",
        "actual_report_or_pdf_read_performed",
        "actual_business_line_decision_performed",
    )
    return (
        authority.get("authority")
        == "FROZEN_STAGE115_TASKPACK_AND_STAGE114_REVIEWED_REVIEW_WORKFLOW_CONTROL_ARTIFACTS_ONLY"
        and all(authority.get(field) is True for field in true_fields)
        and all(authority.get(field) is False for field in false_fields)
        and authority.get(
            "actual_existing_audit_log_read_performed",
            authority.get("actual_audit_log_read_performed"),
        )
        is False
    )


def _phase1_contract_valid(contract: object) -> bool:
    if not isinstance(contract, Mapping):
        return False
    review = contract.get("review_ui_control_contract")
    audit = contract.get("review_audit_and_impact_control_contract")
    predecessor = contract.get("predecessor_review_contract")
    failure = contract.get("failure_and_stop_contract")
    boundary = contract.get("stage_and_phase_boundary")
    feedback = contract.get("chinese_feedback_contract")
    if not all(
        isinstance(value, Mapping)
        for value in (review, audit, predecessor, failure, boundary, feedback)
    ):
        return False
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("record_kind") == "CONTROL_ONLY_REVIEW_UI_PHASE1_CONTRACT",
            contract.get("stage") == "STAGE-115",
            contract.get("phase") == "IDS-STAGE115-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE115-P1",
            contract.get("entry_gate") == "IDS-STAGE115-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE115-P2-GATE",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            _authority_preserved(contract.get("source_authority")),
            review.get("future_control_reference_field_count") == 19,
            tuple(review.get("required_review_trigger_types", ()))
            == P1_REQUIRED_REVIEW_TRIGGER_TYPES,
            review.get("required_review_trigger_type_count") == 4,
            tuple(review.get("fixed_review_statuses", ()))
            == P1_FIXED_REVIEW_STATUSES,
            review.get("fixed_review_status_count") == 5,
            tuple(review.get("future_ui_action_labels", ()))
            == P1_FIXED_REVIEW_ACTIONS,
            review.get("future_ui_action_label_count") == 5,
            review.get("static_chinese_ui_section_count") == 5,
            review.get("control_references_are_labels_only") is True,
            review.get(
                "future_ui_interaction_rules_are_business_line_whitebox_authorized_work_only"
            )
            is True,
            review.get("actual_review_ui_rendered") is False,
            review.get("actual_review_queue_displayed") is False,
            review.get("actual_review_action_executed") is False,
            tuple(audit.get("required_future_audit_reference_fields", ()))
            == P1_AUDIT_REFERENCE_FIELDS,
            audit.get("required_future_audit_reference_field_count") == 7,
            audit.get("actor_time_reason_old_new_controls_required") is True,
            audit.get(
                "future_evidence_trust_level_before_after_references_required"
            )
            is True,
            audit.get(
                "future_report_quality_score_before_after_references_required"
            )
            is True,
            audit.get("future_report_status_impact_reference_required") is True,
            audit.get("review_result_does_not_create_business_fact_or_final_verdict")
            is True,
            audit.get("external_augmentation_is_not_internal_project_evidence")
            is True,
            audit.get("business_line_whitebox_confirmation_required") is True,
            all(
                value is False for key, value in audit.items() if key.startswith("actual_")
            ),
            predecessor.get("stage114_review_required") is True,
            predecessor.get("stage114_review_result")
            == "PASS_REVIEWED_REVIEW_WORKFLOW_RUNTIME_DISABLED",
            predecessor.get("phase4_to_phase3_rollback_preserved") is True,
            failure.get("failure_state_count") == 20,
            len(failure.get("declared_failure_states", ())) == 20,
            _closed_runtime_mapping(contract.get("runtime_boundary")),
            isinstance(contract.get("runtime_counts"), Mapping),
            _zero_actual_counts_in(contract["runtime_counts"]),
            feedback.get("feedback_count") == 4,
            len(feedback.get("feedbacks", ())) == 4,
            boundary.get("stage114_review_evidence_declared") is True,
            boundary.get("stage115_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("phase2_started") is False,
            boundary.get("phase3_started") is False,
            boundary.get("phase4_started") is False,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("github_upload_allowed") is False,
            boundary.get("push_allowed") is False,
        )
    )


def _phase2_report_valid(phase2_module: Any, report: object) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = {
        "schema_version": P2_SCHEMA_VERSION,
        "record_kind": P2_RECORD_KIND,
        "execution_state": P2_PASS_RESULT,
        "input_accepted": True,
        "control_input_count": 5,
        "control_projection_group_count": 4,
        "control_projection_field_total_per_request": 117,
        "control_projection_field_total": 585,
        "review_ui_queue_and_action_control_projection_count": 5,
        "review_audit_control_projection_count": 5,
        "evidence_trust_and_report_impact_control_projection_count": 5,
        "human_reason_and_source_boundary_control_projection_count": 5,
    }
    return all(
        (
            all(report.get(key) == value for key, value in expected.items()),
            _control_runtime_closed(report),
            all(
                len(report.get(name, ())) == 5
                for name in (
                    "review_ui_queue_and_action_control_projections",
                    "review_audit_control_projections",
                    "evidence_trust_and_report_impact_control_projections",
                    "human_reason_and_source_boundary_control_projections",
                )
            ),
            report.get("control_adapter_version")
            == phase2_module.CONTROL_ADAPTER_VERSION,
        )
    )


def _phase3_report_valid(phase3_module: Any, report: object) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = {
        "schema_version": P3_SCHEMA_VERSION,
        "record_kind": P3_RECORD_KIND,
        "execution_state": P3_PASS_RESULT,
        "input_accepted": True,
        "controlled_scenario_count": 5,
        "controlled_scenario_field_count": 47,
        "controlled_scenario_field_check_count": 235,
        "control_view_count": 5,
        "business_line_whitebox_handling_count": 5,
        "phase2_control_request_count": 5,
        "phase2_control_input_field_count": 23,
        "phase2_phase1_reference_field_count": 19,
        "phase2_projection_group_count": 4,
        "phase2_projection_field_total_per_request": 117,
        "phase2_projection_field_check_count": 585,
    }
    return all(
        (
            all(report.get(key) == value for key, value in expected.items()),
            _control_runtime_closed(report),
            report.get("control_adapter_version")
            == phase3_module.CONTROL_ADAPTER_VERSION,
            tuple(
                item.get("controlled_scenario_id")
                for item in report.get("controlled_scenarios", ())
                if isinstance(item, Mapping)
            )
            == P3_SCENARIO_IDS,
            len(report.get("control_views", ())) == 5,
            len(report.get("business_line_whitebox_handlings", ())) == 5,
            len(phase3_module.FAILURE_STATES) == 15,
            len(phase3_module.CHINESE_FEEDBACK) == 5,
        )
    )


def _phase4_report_valid(phase4_module: Any, report: object) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = {
        "schema_version": P4_SCHEMA_VERSION,
        "record_kind": P4_RECORD_KIND,
        "valid": True,
        "result": P4_PASS_RESULT,
        "failure_state": None,
        "current_gate": "IDS-STAGE115-P4-GATE",
        "next_gate": REVIEW_GATE,
        "phase2_control_request_count": 5,
        "phase2_input_field_count": 23,
        "phase2_phase1_reference_field_count": 19,
        "phase2_projection_group_count": 4,
        "phase2_projection_field_count_per_request": 117,
        "phase2_projection_field_count_total": 585,
        "scenario_count": 5,
        "scenario_field_count": 47,
        "scenario_field_check_count": 235,
        "control_view_count": 5,
        "business_line_whitebox_handling_count": 5,
        "whitebox_confirmation_required_scenario_count": 5,
        "delivery_field_check_count": 388,
        "failure_state_count": 17,
        "control_references_opaque": True,
        "phase3_control_shape_preserved": True,
        "phase3_side_effect_free": True,
        "second_authoritative_source_created": False,
    }
    groups_valid = all(
        isinstance(report.get(name), list)
        and len(report.get(name, ())) == count
        and all(
            isinstance(record, Mapping) and len(record) == field_count
            for record in report.get(name, ())
        )
        for name, count, field_count in P4_DELIVERY_GROUPS
    )
    expected_group_definitions = (
        (
            "review_queue_sample_control_records",
            phase4_module.REVIEW_QUEUE_SAMPLE_FIELDS,
        ),
        (
            "review_audit_log_sample_control_records",
            phase4_module.REVIEW_AUDIT_LOG_SAMPLE_FIELDS,
        ),
        (
            "review_ui_flow_explanation_control_records",
            phase4_module.REVIEW_UI_FLOW_EXPLANATION_FIELDS,
        ),
        (
            "human_judgment_boundary_control_records",
            phase4_module.HUMAN_JUDGMENT_BOUNDARY_FIELDS,
        ),
        (
            "business_line_whitebox_confirmation_control_records",
            phase4_module.BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS,
        ),
        (
            "rollback_and_re_review_instruction_control_records",
            phase4_module.ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS,
        ),
    )
    return all(
        (
            all(report.get(key) == value for key, value in expected.items()),
            _control_runtime_closed(report),
            groups_valid,
            tuple(phase4_module.DELIVERY_GROUPS) == expected_group_definitions,
            len(report.get("operator_feedback", ())) == 4,
        )
    )


def _is_control_reference(value: object) -> bool:
    return isinstance(value, str) and value.startswith(":control:")


def _record_references_are_opaque(record: Mapping[str, Any]) -> bool:
    references = [
        value
        for key, value in record.items()
        if key.endswith("_ref") and value is not None
    ]
    return all(_is_control_reference(value) for value in references)


def _control_references_remain_opaque(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    records: list[Mapping[str, Any]] = []
    for name in (
        "controlled_scenarios",
        "control_views",
        "business_line_whitebox_handlings",
    ):
        records.extend(
            item
            for item in phase3_report.get(name, ())
            if isinstance(item, Mapping)
        )
    for name, _count, _field_count in P4_DELIVERY_GROUPS:
        records.extend(
            item
            for item in phase4_report.get(name, ())
            if isinstance(item, Mapping)
        )
    references = [
        value
        for record in records
        for key, value in record.items()
        if key.endswith("_ref") and value is not None
    ]
    return bool(records) and bool(references) and all(
        _record_references_are_opaque(record) for record in records
    )


def _audit_impact_and_whitebox_semantics_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("controlled_scenarios")
    handlings = phase3_report.get("business_line_whitebox_handlings")
    boundaries = phase4_report.get("human_judgment_boundary_control_records")
    confirmations = phase4_report.get(
        "business_line_whitebox_confirmation_control_records"
    )
    if not all(
        isinstance(items, list) and items
        for items in (scenarios, handlings, boundaries, confirmations)
    ):
        return False
    scenario_fields = (
        "review_actor_ref",
        "review_time_ref",
        "review_transition_reason_ref",
        "old_value_ref",
        "new_value_ref",
        "review_result_ref",
        "review_audit_record_ref",
        "evidence_trust_level_before_ref",
        "evidence_trust_level_after_ref",
        "report_quality_score_before_ref",
        "report_quality_score_after_ref",
        "report_status_impact_ref",
    )
    scenarios_valid = all(
        isinstance(item, Mapping)
        and all(_is_control_reference(item.get(field)) for field in scenario_fields)
        and isinstance(item.get("controlled_scenario_id"), str)
        and _is_control_reference(
            item.get("external_augmentation_and_whitebox_control_ref")
        )
        for item in scenarios
    )
    handlings_valid = all(
        isinstance(item, Mapping)
        and item.get("business_line_whitebox_confirmation_required") is True
        and item.get("actual_human_confirmation_execution_performed") is False
        and item.get("actual_final_business_conclusion_recorded") is False
        for item in handlings
    )
    boundaries_valid = all(
        isinstance(item, Mapping)
        and item.get("business_line_whitebox_confirmation_required") is True
        and item.get("automatic_evidence_or_report_writeback_allowed") is False
        and item.get("actual_human_confirmation_performed") is False
        for item in boundaries
    )
    confirmations_valid = all(
        isinstance(item, Mapping)
        and item.get("external_augmentation_source_separation_state")
        == "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE"
        and item.get("confirmation_required") is True
        and item.get("automatic_final_conclusion_allowed") is False
        for item in confirmations
    )
    return all((scenarios_valid, handlings_valid, boundaries_valid, confirmations_valid))


def _phase4_lifecycle_and_rollback_valid(report: Mapping[str, Any]) -> bool:
    lifecycle = report.get("rollback_and_re_review_instruction_control_records")
    if not isinstance(lifecycle, list) or len(lifecycle) != 2:
        return False
    return all(
        (
            {
                item.get("control_domain")
                for item in lifecycle
                if isinstance(item, Mapping)
            }
            == {"REVIEW_UI_ROLLBACK", "RE_REVIEW"},
            all(
                isinstance(item, Mapping)
                and item.get("rollback_target_result") == P3_PASS_RESULT
                and item.get("business_line_whitebox_confirmation_required") is True
                and item.get("human_confirmation_required") is True
                and item.get("versioned_basis_required") is True
                and item.get("verifiable_rollback_target_required") is True
                and item.get("actual_review_ui_rollback_performed") is False
                and item.get("actual_re_review_performed") is False
                for item in lifecycle
            ),
        )
    )


def build_review_ui_stage_review(
    phase1_contract_provider: Optional[Provider] = None,
    phase2_provider: Optional[Provider] = None,
    phase3_provider: Optional[Provider] = None,
    phase4_provider: Optional[Provider] = None,
) -> dict[str, Any]:
    """机械复审 Stage115 P1--P4，任一控制漂移均以零运行时状态失败关闭。"""

    try:
        phase2_module, phase3_module, phase4_module = _load_phase_modules()
        canonical_phase1 = _default_phase1_contract()
        phase1_contract = (
            phase1_contract_provider()
            if phase1_contract_provider is not None
            else canonical_phase1
        )
    except Exception:
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase1_contract_valid(phase1_contract):
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        canonical_phase2 = phase2_module.project_review_ui_control_slice(
            phase2_module.build_control_input()
        )
        phase2_report = (
            phase2_provider() if phase2_provider is not None else canonical_phase2
        )
    except Exception:
        return _base_report(False, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase2_report_valid(phase2_module, phase2_report):
        return _base_report(False, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        canonical_phase3 = phase3_module.project_review_ui_controlled_scenarios(
            phase3_module.build_controlled_scenario_input()
        )
        phase3_report = (
            phase3_provider() if phase3_provider is not None else canonical_phase3
        )
    except Exception:
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase3_report_valid(phase3_module, phase3_report):
        return _base_report(False, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        canonical_phase4 = phase4_module.build_review_ui_phase4_delivery_report()
        phase4_report = (
            phase4_provider() if phase4_provider is not None else canonical_phase4
        )
    except Exception:
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase4_report_valid(phase4_module, phase4_report):
        return _base_report(False, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    if not _control_references_remain_opaque(phase3_report, phase4_report):
        return _base_report(False, "CONTROL_REFERENCE_OPAQUENESS_MISMATCH")
    if not _audit_impact_and_whitebox_semantics_valid(phase3_report, phase4_report):
        return _base_report(
            False, "REVIEW_AUDIT_IMPACT_AND_WHITEBOX_SEMANTICS_MISMATCH"
        )
    if not _phase4_lifecycle_and_rollback_valid(phase4_report):
        return _base_report(False, "DELIVERY_AND_ROLLBACK_BOUNDARY_MISMATCH")
    if (
        phase1_contract != canonical_phase1
        or phase2_report != canonical_phase2
        or phase3_report != canonical_phase3
        or phase4_report != canonical_phase4
    ):
        return _base_report(False, "CONTROLLED_REVIEW_SHAPE_MISMATCH")
    if not all(
        (
            _control_runtime_closed(phase2_report),
            _control_runtime_closed(phase3_report),
            _control_runtime_closed(phase4_report),
        )
    ):
        return _base_report(
            False, "RUNTIME_SIGNAL_OR_UNASSIGNED_SUCCESSOR_ENTRY_DETECTED"
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
            "stage115_review_started": True,
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
