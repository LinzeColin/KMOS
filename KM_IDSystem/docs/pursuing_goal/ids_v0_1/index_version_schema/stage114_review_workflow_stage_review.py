"""Stage114 复核工作流整阶段纯内存机械复审。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


Provider = Callable[[], Any]

SCHEMA_VERSION = "ids.stage114.review_workflow.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_WORKFLOW_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REVIEW_WORKFLOW_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REVIEW_WORKFLOW_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE114-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE115-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage114.review_workflow.phase1.v1"
P1_CONTRACT_STATE = "REVIEW_WORKFLOW_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage114.review_workflow.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_WORKFLOW"
P2_PASS_RESULT = "PASS_IN_MEMORY_REVIEW_WORKFLOW_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage114.review_workflow.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_WORKFLOW_SCENARIOS"
P3_PASS_RESULT = "PASS_IN_MEMORY_REVIEW_WORKFLOW_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage114.review_workflow.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_WORKFLOW_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REVIEW_WORKFLOW_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage114_review_workflow_contract.json")

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
P1_FIXED_WORKFLOW_ACTIONS = (
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
    ("review_queue_sample_control_records", "REVIEW_QUEUE_SAMPLE_FIELDS", 5),
    ("review_audit_log_sample_control_records", "REVIEW_AUDIT_LOG_SAMPLE_FIELDS", 5),
    (
        "review_ui_flow_explanation_control_records",
        "REVIEW_UI_FLOW_EXPLANATION_FIELDS",
        5,
    ),
    (
        "human_judgment_boundary_control_records",
        "HUMAN_JUDGMENT_BOUNDARY_FIELDS",
        5,
    ),
    (
        "business_line_whitebox_confirmation_control_records",
        "BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS",
        5,
    ),
    (
        "rollback_and_re_review_instruction_control_records",
        "ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS",
        2,
    ),
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 26,
    "phase1_review_trigger_type_count": 4,
    "phase1_review_status_count": 5,
    "phase1_workflow_action_label_count": 5,
    "phase1_review_audit_reference_field_count": 7,
    "phase1_failure_state_count": 20,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 30,
    "phase2_phase1_reference_field_count": 26,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 132,
    "phase2_control_field_check_count": 660,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 54,
    "phase3_scenario_field_check_count": 270,
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
    "RUNTIME_SIGNAL_OR_STAGE115_ENTRY_DETECTED",
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
    "withdrawn_material_evaluation_performed",
    "evidence_risk_evaluation_performed",
    "review_workflow_execution_performed",
    "review_queue_entry_created",
    "review_status_transition_performed",
    "review_ui_rendered",
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
    "stage114_review_runtime_executed",
    "stage115_runtime_started",
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
    "actual_review_workflow_rollback_count",
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
    "复核工作流整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "actor、time、reason、old value、new value 与 review result 保持审计控制引用，证据可信等级和报告质量／状态影响保持未来控制。",
    "复核状态、审计、证据与报告影响、人工判断和业务线白箱确认保持后续授权，外部增强继续与内部证据分离。",
    "真实资料、OCR、复核工作流、队列、UI、审计、数据库、模型、Agent、OVH、生产、Stage115 和正式全局上传保持未执行。",
)


def _load_phase_modules() -> tuple[Any, Any, Any]:
    if __package__ is None:
        raise RuntimeError("stage review package unavailable")
    package = __package__
    return (
        importlib.import_module(f"{package}.stage114_review_workflow_control_slice"),
        importlib.import_module(
            f"{package}.stage114_review_workflow_controlled_scenarios"
        ),
        importlib.import_module(f"{package}.stage114_review_workflow_delivery"),
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
        "stage115_started": False,
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
    return bool(actual_counts) and all(type(item) is int and item == 0 for item in actual_counts)


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
        all(authority.get(field) is True for field in true_fields)
        and all(authority.get(field) is False for field in false_fields)
        and authority.get(
            "actual_existing_audit_log_read_performed",
            authority.get("actual_audit_log_read_performed"),
        )
        is False
    )


def _phase1_contract_valid(
    contract: Mapping[str, Any], phase2_module: Any
) -> bool:
    if not isinstance(contract, Mapping):
        return False
    if (
        contract.get("schema_version") != P1_SCHEMA_VERSION
        or contract.get("record_kind") != "CONTROL_ONLY_REVIEW_WORKFLOW_PHASE1_CONTRACT"
        or contract.get("stage") != "STAGE-114"
        or contract.get("phase") != "IDS-STAGE114-P1"
        or contract.get("task_id") != "IDS-V0_1-STAGE114-P1"
        or contract.get("contract_state") != P1_CONTRACT_STATE
    ):
        return False
    if not _authority_preserved(contract.get("source_authority")):
        return False
    input_output = contract.get("review_workflow_input_output_control_contract")
    audit = contract.get("review_audit_control_contract")
    impact = contract.get("evidence_and_report_impact_control_contract")
    failure = contract.get("failure_and_stop_contract")
    feedback = contract.get("chinese_feedback_contract")
    boundary = contract.get("stage_and_phase_boundary")
    local_code = contract.get("local_code")
    rollback = contract.get("rollback_contract")
    if not all(
        isinstance(value, Mapping)
        for value in (
            input_output,
            audit,
            impact,
            failure,
            feedback,
            boundary,
            local_code,
            rollback,
        )
    ):
        return False
    return all(
        (
            tuple(input_output.get("future_control_reference_fields", ()))
            == tuple(phase2_module.PHASE1_CONTROL_REFERENCE_FIELDS),
            input_output.get("future_control_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase1_reference_field_count"],
            tuple(input_output.get("required_review_trigger_types", ()))
            == P1_REQUIRED_REVIEW_TRIGGER_TYPES,
            input_output.get("required_review_trigger_type_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_trigger_type_count"],
            tuple(input_output.get("fixed_review_statuses", ()))
            == P1_FIXED_REVIEW_STATUSES,
            input_output.get("fixed_review_status_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_status_count"],
            tuple(input_output.get("future_workflow_action_labels", ()))
            == P1_FIXED_WORKFLOW_ACTIONS,
            input_output.get("future_workflow_action_label_count")
            == REVIEWED_CONTROL_SHAPE["phase1_workflow_action_label_count"],
            input_output.get(
                "each_future_action_requires_from_to_actor_time_reason_old_new_and_result_controls"
            )
            is True,
            tuple(audit.get("required_future_audit_reference_fields", ()))
            == P1_AUDIT_REFERENCE_FIELDS,
            audit.get("required_future_audit_reference_field_count")
            == REVIEWED_CONTROL_SHAPE["phase1_review_audit_reference_field_count"],
            audit.get("actor_time_reason_old_new_controls_required") is True,
            audit.get("review_result_reference_required") is True,
            audit.get("business_line_whitebox_confirmation_required") is True,
            impact.get("evidence_id_or_evidence_gap_reference_required") is True,
            impact.get("future_evidence_trust_level_before_after_references_required")
            is True,
            impact.get("future_report_quality_score_before_after_references_required")
            is True,
            impact.get("future_report_status_impact_reference_required") is True,
            impact.get("external_augmentation_is_not_internal_project_evidence")
            is True,
            failure.get("failure_state_count")
            == REVIEWED_CONTROL_SHAPE["phase1_failure_state_count"],
            len(failure.get("declared_failure_states", ()))
            == REVIEWED_CONTROL_SHAPE["phase1_failure_state_count"],
            feedback.get("feedback_count")
            == REVIEWED_CONTROL_SHAPE["phase1_chinese_feedback_count"],
            len(feedback.get("feedbacks", ()))
            == REVIEWED_CONTROL_SHAPE["phase1_chinese_feedback_count"],
            feedback.get("actual_user_feedback_emitted") is False,
            local_code.get("static_contract_only") is True,
            all(
                value is False
                for key, value in local_code.items()
                if key != "static_contract_only"
            ),
            _closed_runtime_mapping(contract.get("runtime_boundary")),
            isinstance(contract.get("runtime_counts"), Mapping)
            and all(value == 0 for value in contract["runtime_counts"].values()),
            boundary.get("stage113_review_evidence_declared") is True,
            boundary.get("stage114_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage115_started") is False,
            boundary.get("formal_global_upload_performed") is False,
            boundary.get("github_upload_allowed") is False,
            boundary.get("push_allowed") is False,
            rollback.get("fallback_result")
            == "PASS_REVIEWED_REVIEW_QUEUE_SCHEMA_RUNTIME_DISABLED",
            rollback.get("stage113_review_preserved") is True,
            rollback.get("business_source_or_runtime_change_allowed") is False,
            rollback.get("github_or_ovh_change_allowed") is False,
        )
    )


def _phase2_report_valid(phase2_module: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = REVIEWED_CONTROL_SHAPE
    if not all(
        (
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("control_input_count")
            == expected["phase2_control_request_count"],
            report.get("control_projection_group_count")
            == expected["phase2_projection_group_count"],
            report.get("control_projection_field_total_per_request")
            == expected["phase2_projection_field_count_per_request"],
            report.get("control_projection_field_total")
            == expected["phase2_control_field_check_count"],
            _control_runtime_closed(report),
        )
    ):
        return False
    for prefix, fields in phase2_module.PROJECTION_FIELDS:
        records = report.get(f"{prefix}_control_projections")
        if (
            not isinstance(records, list)
            or report.get(f"{prefix}_control_projection_count")
            != expected["phase2_control_request_count"]
            or len(records) != expected["phase2_control_request_count"]
            or any(
                not isinstance(record, Mapping)
                or len(record) != len(fields)
                or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return True


def _phase3_report_valid(phase3_module: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = REVIEWED_CONTROL_SHAPE
    if not all(
        (
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("phase2_control_request_count")
            == expected["phase2_control_request_count"],
            report.get("phase2_control_input_field_count")
            == expected["phase2_input_field_count"],
            report.get("phase2_phase1_reference_field_count")
            == expected["phase2_phase1_reference_field_count"],
            report.get("phase2_projection_group_count")
            == expected["phase2_projection_group_count"],
            report.get("phase2_projection_field_total_per_request")
            == expected["phase2_projection_field_count_per_request"],
            report.get("phase2_projection_field_check_count")
            == expected["phase2_control_field_check_count"],
            report.get("controlled_scenario_count")
            == expected["phase3_scenario_count"],
            report.get("controlled_scenario_field_count")
            == expected["phase3_scenario_field_count"],
            report.get("controlled_scenario_field_check_count")
            == expected["phase3_scenario_field_check_count"],
            report.get("control_view_count") == expected["phase3_control_view_count"],
            report.get("business_line_whitebox_handling_count")
            == expected["phase3_human_handling_count"],
            _control_runtime_closed(report),
        )
    ):
        return False
    scenarios = report.get("controlled_scenarios")
    views = report.get("control_views")
    handlings = report.get("business_line_whitebox_handlings")
    if (
        not isinstance(scenarios, list)
        or not isinstance(views, list)
        or not isinstance(handlings, list)
        or tuple(item.get("controlled_scenario_id") for item in scenarios)
        != P3_SCENARIO_IDS
        or len(views) != expected["phase3_control_view_count"]
        or len(handlings) != expected["phase3_human_handling_count"]
    ):
        return False
    if any(
        not isinstance(scenario, Mapping)
        or len(scenario) != expected["phase3_scenario_field_count"]
        or set(scenario) != set(phase3_module.SCENARIO_FIELDS)
        or (
            scenario.get("evidence_id_ref") is None
            == (scenario.get("evidence_gap_ref") is None)
        )
        for scenario in scenarios
    ):
        return False
    if any(
        not isinstance(view, Mapping)
        or view.get("scenario_control_record_count")
        != expected["phase3_scenario_count"]
        or view.get("actual_control_view_rendered") is not False
        for view in views
    ):
        return False
    return all(isinstance(handling, Mapping) for handling in handlings)


def _phase4_report_valid(phase4_module: Any, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    expected = REVIEWED_CONTROL_SHAPE
    if not all(
        (
            report.get("schema_version") == P4_SCHEMA_VERSION,
            report.get("record_kind") == P4_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE114-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase2_control_request_count")
            == expected["phase2_control_request_count"],
            report.get("phase2_input_field_count")
            == expected["phase2_input_field_count"],
            report.get("phase2_phase1_reference_field_count")
            == expected["phase2_phase1_reference_field_count"],
            report.get("phase2_projection_group_count")
            == expected["phase2_projection_group_count"],
            report.get("phase2_projection_field_count_per_request")
            == expected["phase2_projection_field_count_per_request"],
            report.get("phase2_projection_field_count_total")
            == expected["phase2_control_field_check_count"],
            report.get("scenario_count") == expected["phase3_scenario_count"],
            report.get("scenario_field_count")
            == expected["phase3_scenario_field_count"],
            report.get("scenario_field_check_count")
            == expected["phase3_scenario_field_check_count"],
            report.get("control_view_count") == expected["phase3_control_view_count"],
            report.get("business_line_whitebox_handling_count")
            == expected["phase3_human_handling_count"],
            report.get("whitebox_confirmation_required_scenario_count")
            == expected["phase3_whitebox_confirmation_required_count"],
            report.get("delivery_field_check_count")
            == expected["phase4_delivery_field_check_count"],
            report.get("failure_state_count")
            == expected["phase4_failure_state_count"],
            len(report.get("operator_feedback", ()))
            == expected["phase4_chinese_feedback_count"],
            report.get("second_authoritative_source_created") is False,
            _control_runtime_closed(report),
        )
    ):
        return False
    for group_name, field_name, expected_count in P4_DELIVERY_GROUPS:
        records = report.get(group_name)
        fields = getattr(phase4_module, field_name)
        if (
            not isinstance(records, list)
            or len(records) != expected_count
            or any(
                not isinstance(record, Mapping)
                or len(record) != len(fields)
                or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return True


def _is_control_reference(value: object) -> bool:
    return isinstance(value, str) and value.startswith(":control:stage114-")


def _record_references_are_opaque(record: Mapping[str, Any]) -> bool:
    for key, value in record.items():
        if key in {"evidence_id_ref", "evidence_gap_ref"} and value is None:
            continue
        if key.endswith("_ref") or key in {"delivery_record_id", "instruction_id"}:
            if not _is_control_reference(value):
                return False
    return True


def _control_references_remain_opaque(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenario_records = phase3_report.get("controlled_scenarios")
    if not isinstance(scenario_records, list) or not all(
        isinstance(record, Mapping) and _record_references_are_opaque(record)
        for record in scenario_records
    ):
        return False
    return all(
        isinstance(record, Mapping) and _record_references_are_opaque(record)
        for group_name, _field_name, _expected_count in P4_DELIVERY_GROUPS
        for record in phase4_report.get(group_name, [])
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
        isinstance(value, list)
        for value in (scenarios, handlings, boundaries, confirmations)
    ):
        return False
    audit_fields = (
        "review_actor_ref",
        "review_time_ref",
        "review_transition_reason_ref",
        "old_value_ref",
        "new_value_ref",
        "review_result_ref",
        "review_audit_record_ref",
    )
    if any(
        any(not _is_control_reference(scenario.get(field)) for field in audit_fields)
        for scenario in scenarios
    ):
        return False
    if any(
        handling.get("business_line_whitebox_confirmation_required") is not True
        or handling.get("actual_human_confirmation_execution_performed") is not False
        or handling.get("actual_final_business_conclusion_recorded") is not False
        for handling in handlings
    ):
        return False
    if any(
        boundary.get("business_line_whitebox_confirmation_required") is not True
        or boundary.get("automatic_evidence_or_report_writeback_allowed") is not False
        or boundary.get("actual_human_confirmation_performed") is not False
        for boundary in boundaries
    ):
        return False
    return all(
        confirmation.get("external_augmentation_source_separation_state")
        == "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE"
        and confirmation.get("confirmation_required") is True
        and confirmation.get("automatic_final_conclusion_allowed") is False
        and confirmation.get("actual_human_confirmation_execution_performed") is False
        and confirmation.get("actual_final_conclusion_published") is False
        and confirmation.get("actual_review_state_transition_performed") is False
        and confirmation.get(
            "actual_evidence_or_report_writeback_execution_performed"
        )
        is False
        and confirmation.get("persistent_state_write_performed") is False
        for confirmation in confirmations
    )


def _phase4_lifecycle_and_rollback_valid(report: Mapping[str, Any]) -> bool:
    instructions = report.get("rollback_and_re_review_instruction_control_records")
    if (
        not isinstance(instructions, list)
        or {item.get("control_domain") for item in instructions}
        != {"REVIEW_WORKFLOW_ROLLBACK", "RE_REVIEW"}
    ):
        return False
    required_true = (
        "business_line_whitebox_confirmation_required",
        "human_confirmation_required",
        "versioned_basis_required",
        "verifiable_rollback_target_required",
    )
    return all(
        isinstance(instruction, Mapping)
        and instruction.get("rollback_target_result") == P3_PASS_RESULT
        and all(instruction.get(field) is True for field in required_true)
        and instruction.get("actual_review_workflow_rollback_performed") is False
        and instruction.get("actual_re_review_performed") is False
        for instruction in instructions
    )


def build_review_workflow_stage_review(
    phase1_contract_provider: Optional[Provider] = None,
    phase2_provider: Optional[Provider] = None,
    phase3_provider: Optional[Provider] = None,
    phase4_provider: Optional[Provider] = None,
) -> dict[str, Any]:
    """机械复审 Stage114 P1--P4，任何控制漂移均返回零运行时失败。"""

    try:
        phase2_module, phase3_module, phase4_module = _load_phase_modules()
        phase1_contract = (
            phase1_contract_provider()
            if phase1_contract_provider is not None
            else _default_phase1_contract()
        )
    except Exception:
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase1_contract_valid(phase1_contract, phase2_module):
        return _base_report(False, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        canonical_phase2 = phase2_module.project_review_workflow_control_slice(
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
        canonical_phase3 = phase3_module.project_review_workflow_controlled_scenarios(
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
        canonical_phase4 = phase4_module.build_review_workflow_phase4_delivery_report()
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
        phase2_report != canonical_phase2
        or phase3_report != canonical_phase3
        or phase4_report != canonical_phase4
    ):
        return _base_report(False, "CONTROLLED_REVIEW_SHAPE_MISMATCH")
    if not _authority_preserved(phase1_contract.get("source_authority")):
        return _base_report(False, "SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not all(
        (
            _control_runtime_closed(phase2_report),
            _control_runtime_closed(phase3_report),
            _control_runtime_closed(phase4_report),
        )
    ):
        return _base_report(False, "RUNTIME_SIGNAL_OR_STAGE115_ENTRY_DETECTED")

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
            "stage114_review_started": True,
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
