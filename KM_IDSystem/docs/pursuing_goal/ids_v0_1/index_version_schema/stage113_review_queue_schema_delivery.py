"""Stage113 P4：复核队列 Schema 的 metadata-only 交付控制证据。

模块只从 Stage113 P3 固定、非业务、reference-only 专项场景派生复核队列样例、
复核审计日志样例、中文 UI 流程说明、人工判断边界、业务线白箱确认和回滚／重新复核
说明。它不读取真实资料、OCR、证据账本、报告或既有审计日志，不创建队列、UI、审计
或写回，也不调用模型、Agent、OVH 或生产服务。
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any, Optional


SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase4.delivery.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE"
PASS_RESULT = "PASS_REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE113-P4-GATE"
NEXT_GATE = "IDS-STAGE113-REVIEW-GATE"

P3_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_SCENARIOS"
P3_PASS_RESULT = "PASS_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_CURRENT_GATE = "IDS-STAGE113-P3-GATE"
P3_NEXT_GATE = "IDS-STAGE113-P4-GATE"
P2_CONTROL_PREFIX = ":control:stage113-p2:"
DELIVERY_PREFIX = ":control:stage113-p4:"

P3_SCENARIO_IDS = (
    "low_quality_ocr_review_operation_control",
    "conflicting_material_review_audit_control",
    "withdrawn_material_re_review_control",
    "evidence_trust_report_quality_impact_control",
    "external_augmentation_internal_evidence_replacement_control",
)
P3_SCENARIO_FIELD_COUNT = 52
P3_CONTROL_VIEW_COUNT = 5
P3_HUMAN_HANDLING_COUNT = 5
P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT = 5
P3_PHASE2_CONTROL_REQUEST_COUNT = 5
P3_PHASE2_INPUT_FIELD_COUNT = 32
P3_PHASE2_PHASE1_REFERENCE_FIELD_COUNT = 29
P3_PHASE2_PROJECTION_GROUP_COUNT = 4
P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST = 101
P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL = 505
P3_SCENARIO_FIELD_CHECK_COUNT = 260

REVIEW_QUEUE_SAMPLE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "review_queue_item_ref",
    "review_queue_schema_ref",
    "review_queue_entry_reason_ref",
    "review_trigger_type_ref",
    "review_status_ref",
    "source_document_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_risk_ref",
    "low_ocr_confidence_ref",
    "source_conflict_ref",
    "parsing_failure_ref",
    "review_queue_sample_state",
    "business_line_whitebox_confirmation_required",
    "actual_review_queue_sample_rendered",
)
REVIEW_AUDIT_LOG_SAMPLE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "review_audit_record_ref",
    "review_actor_ref",
    "review_time_ref",
    "review_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "re_review_reference_ref",
    "archive_reference_ref",
    "review_audit_sample_state",
    "actual_review_audit_log_written",
)
REVIEW_UI_FLOW_EXPLANATION_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "review_queue_item_ref",
    "review_status_ref",
    "review_reason_chinese_control_message",
    "review_ui_flow_step_ref",
    "review_ui_entry_control_ref",
    "review_ui_feedback_state",
    "screenshot_or_real_ui_rendered",
    "automatic_review_operation_allowed",
    "business_line_whitebox_confirmation_required",
    "actual_review_ui_rendered",
    "actual_user_feedback_delivered",
)
HUMAN_JUDGMENT_BOUNDARY_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "scenario_category",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "review_result_ref",
    "evidence_trust_level_before_ref",
    "evidence_trust_level_after_ref",
    "report_quality_score_before_ref",
    "report_quality_score_after_ref",
    "report_status_impact_ref",
    "human_judgment_boundary_state",
    "business_line_whitebox_confirmation_required",
    "automatic_evidence_or_report_writeback_allowed",
    "actual_human_confirmation_performed",
)
BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "handling_code",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "external_augmentation_source_separation_state",
    "whitebox_confirmation_state",
    "confirmation_required",
    "automatic_final_conclusion_allowed",
    "actual_human_confirmation_execution_performed",
    "actual_final_conclusion_published",
    "actual_review_state_transition_performed",
    "actual_evidence_or_report_writeback_execution_performed",
    "persistent_state_write_performed",
)
ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS = (
    "instruction_id",
    "control_domain",
    "trigger_state_ref",
    "rollback_target_ref",
    "rollback_target_result",
    "predecessor_phase_ref",
    "review_queue_schema_ref",
    "review_audit_record_ref",
    "business_line_whitebox_confirmation_required",
    "human_confirmation_required",
    "versioned_basis_required",
    "verifiable_rollback_target_required",
    "actual_review_queue_rollback_performed",
    "actual_re_review_performed",
)
DELIVERY_GROUPS = (
    ("review_queue_sample_control_records", REVIEW_QUEUE_SAMPLE_FIELDS),
    ("review_audit_log_sample_control_records", REVIEW_AUDIT_LOG_SAMPLE_FIELDS),
    ("review_ui_flow_explanation_control_records", REVIEW_UI_FLOW_EXPLANATION_FIELDS),
    ("human_judgment_boundary_control_records", HUMAN_JUDGMENT_BOUNDARY_FIELDS),
    (
        "business_line_whitebox_confirmation_control_records",
        BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS,
    ),
    (
        "rollback_and_re_review_instruction_control_records",
        ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS,
    ),
)
DELIVERY_FIELD_CHECK_COUNT = 388

P3_SCENARIO_CONTROL_REFERENCE_FIELDS = (
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

RUNTIME_CLOSED_FIELDS = (
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
    "phase2_control_slice_runtime_executed",
    "stage113_phase3_runtime_executed",
    "phase3_controlled_scenarios_runtime_executed",
    "review_queue_sample_rendered",
    "review_audit_log_sample_written",
    "review_ui_flow_explanation_rendered",
    "human_judgment_boundary_recorded",
    "business_line_whitebox_confirmation_recorded",
    "review_queue_rollback_performed",
    "re_review_performed",
    "stage113_phase4_runtime_executed",
)
ZERO_COUNTER_FIELDS = (
    "actual_phase3_control_replay_count",
    "actual_review_queue_sample_count",
    "actual_review_audit_log_sample_count",
    "actual_review_ui_flow_explanation_count",
    "actual_human_judgment_boundary_evaluation_count",
    "actual_business_line_whitebox_confirmation_count",
    "actual_review_queue_rollback_count",
    "actual_re_review_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_existing_audit_log_read_count",
    "actual_review_queue_or_ui_execution_count",
    "actual_review_audit_or_database_execution_count",
    "actual_evidence_or_report_writeback_execution_count",
    "actual_human_confirmation_execution_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)
FAILURE_STATES = (
    "PHASE3_CONTROL_REPLAY_UNAVAILABLE",
    "PHASE3_CONTROL_SHAPE_MISMATCH",
    "PHASE3_RUNTIME_BOUNDARY_BREACH",
    "NON_OPAQUE_CONTROL_REFERENCE",
    "REVIEW_QUEUE_SAMPLE_CONTROL_MISSING",
    "REVIEW_AUDIT_LOG_SAMPLE_CONTROL_MISSING",
    "REVIEW_UI_FLOW_EXPLANATION_CONTROL_MISSING",
    "HUMAN_JUDGMENT_BOUNDARY_CONTROL_MISSING",
    "BUSINESS_LINE_WHITEBOX_CONFIRMATION_CONTROL_MISSING",
    "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "REVIEW_QUEUE_ROLLBACK_AND_RE_REVIEW_CONTROL_MISSING",
    "AUTOMATIC_DELIVERY_OR_AUDIT_BOUNDARY_BREACH",
    "ACTUAL_REVIEW_QUEUE_OR_AUDIT_WRITE_SIGNAL_DETECTED",
    "CONTROLLED_SCENARIO_BINDING_INVALID",
    "SECOND_AUTHORITY_CREATED",
)
OPERATOR_FEEDBACK = (
    "复核队列样例、审计日志样例和中文 UI 流程说明保持 metadata-only 控制记录，等待业务线白箱确认。",
    "actor、time、reason、old value、new value 与 review result 保持审计控制引用，未写入真实审计日志。",
    "evidence trust level、报告质量和报告状态影响保持人工判断边界，自动写回保持关闭。",
    "回滚与重新复核说明固定指向可验证的 P3 回退目标，未执行队列回滚、重新复核或归档动作。",
)

Phase3Executor = Callable[[], Mapping[str, Any]]


def _load_phase3_module() -> Any:
    return importlib.import_module(
        "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
        "stage113_review_queue_schema_controlled_scenarios"
    )


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ZERO_COUNTER_FIELDS}


def _is_control_reference(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P2_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _delivery_ref(name: str) -> str:
    return f"{DELIVERY_PREFIX}{name}:reference-only"


def _is_delivery_reference(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(DELIVERY_PREFIX)
        and value.endswith(":reference-only")
    )


def _base_report(valid: bool, failure_state: Optional[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": ENTRY_GATE,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "phase3_control_shape_preserved": False,
        "phase3_side_effect_free": False,
        "control_references_opaque": False,
        "phase2_control_request_count": 0,
        "phase2_input_field_count": 0,
        "phase2_phase1_reference_field_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_projection_field_count_per_request": 0,
        "phase2_projection_field_count_total": 0,
        "scenario_count": 0,
        "scenario_field_count": P3_SCENARIO_FIELD_COUNT,
        "scenario_field_check_count": 0,
        "control_view_count": 0,
        "business_line_whitebox_handling_count": 0,
        "whitebox_confirmation_required_scenario_count": 0,
        "review_queue_sample_control_records": [],
        "review_audit_log_sample_control_records": [],
        "review_ui_flow_explanation_control_records": [],
        "human_judgment_boundary_control_records": [],
        "business_line_whitebox_confirmation_control_records": [],
        "rollback_and_re_review_instruction_control_records": [],
        "delivery_field_check_count": 0,
        "failure_state_count": len(FAILURE_STATES),
        "operator_feedback": [],
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _phase3_shape_is_preserved(phase3_module: Any, report: Mapping[str, Any]) -> bool:
    constants_match = (
        getattr(phase3_module, "SCHEMA_VERSION", None) == P3_SCHEMA_VERSION
        and getattr(phase3_module, "RECORD_KIND", None) == P3_RECORD_KIND
        and getattr(phase3_module, "PASS_RESULT", None) == P3_PASS_RESULT
        and getattr(phase3_module, "CURRENT_GATE", None) == P3_CURRENT_GATE
        and getattr(phase3_module, "NEXT_GATE", None) == P3_NEXT_GATE
        and getattr(phase3_module, "P2_CONTROL_REQUEST_COUNT", None)
        == P3_PHASE2_CONTROL_REQUEST_COUNT
        and getattr(phase3_module, "P2_INPUT_FIELD_COUNT", None)
        == P3_PHASE2_INPUT_FIELD_COUNT
        and getattr(phase3_module, "P2_PHASE1_REFERENCE_FIELD_COUNT", None)
        == P3_PHASE2_PHASE1_REFERENCE_FIELD_COUNT
        and getattr(phase3_module, "P2_PROJECTION_GROUP_COUNT", None)
        == P3_PHASE2_PROJECTION_GROUP_COUNT
        and getattr(phase3_module, "P2_PROJECTION_FIELD_COUNT_PER_REQUEST", None)
        == P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST
        and getattr(phase3_module, "P2_PROJECTION_FIELD_COUNT_TOTAL", None)
        == P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL
    )
    report_shape_matches = (
        report.get("schema_version") == P3_SCHEMA_VERSION
        and report.get("record_kind") == P3_RECORD_KIND
        and report.get("valid") is True
        and report.get("execution_state") == P3_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == P3_CURRENT_GATE
        and report.get("next_gate") == P3_NEXT_GATE
        and report.get("phase2_control_replay_request_count")
        == P3_PHASE2_CONTROL_REQUEST_COUNT
        and report.get("phase2_input_field_count") == P3_PHASE2_INPUT_FIELD_COUNT
        and report.get("phase2_phase1_reference_field_count")
        == P3_PHASE2_PHASE1_REFERENCE_FIELD_COUNT
        and report.get("phase2_projection_group_count")
        == P3_PHASE2_PROJECTION_GROUP_COUNT
        and report.get("phase2_projection_field_count_per_request")
        == P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST
        and report.get("phase2_projection_field_check_count")
        == P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL
        and report.get("scenario_count") == len(P3_SCENARIO_IDS)
        and report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT
        and report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT
        and report.get("control_view_count") == P3_CONTROL_VIEW_COUNT
        and report.get("business_line_whitebox_handling_count")
        == P3_HUMAN_HANDLING_COUNT
        and report.get("whitebox_confirmation_required_scenario_count")
        == P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
        and report.get("second_authoritative_source_created") is False
        and report.get("persistent_record_created") is False
    )
    if not constants_match or not report_shape_matches:
        return False

    scenario_fields = tuple(getattr(phase3_module, "SCENARIO_FIELDS", ()))
    scenarios = report.get("scenario_results")
    if (
        not isinstance(scenarios, list)
        or len(scenario_fields) != P3_SCENARIO_FIELD_COUNT
        or len(scenarios) != len(P3_SCENARIO_IDS)
        or tuple(
            scenario.get("scenario_id")
            for scenario in scenarios
            if isinstance(scenario, Mapping)
        )
        != P3_SCENARIO_IDS
    ):
        return False
    for scenario in scenarios:
        if not isinstance(scenario, Mapping) or set(scenario) != set(scenario_fields):
            return False
        evidence_id = scenario.get("evidence_id_ref")
        evidence_gap = scenario.get("evidence_gap_ref")
        if (
            scenario.get("expectation_met") is not True
            or (evidence_id is None) == (evidence_gap is None)
            or (evidence_id is not None and not _is_control_reference(evidence_id))
            or (evidence_gap is not None and not _is_control_reference(evidence_gap))
            or not all(
                _is_control_reference(scenario.get(field))
                for field in P3_SCENARIO_CONTROL_REFERENCE_FIELDS
            )
            or not isinstance(scenario.get("review_reason_chinese_control_message"), str)
            or not scenario["review_reason_chinese_control_message"]
            or scenario.get("external_augmentation_source_separation_state")
            != (
                "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
                "SEPARATE_FROM_INTERNAL_EVIDENCE"
            )
            or any(
                scenario.get(field) is not True
                for field in (
                    "external_augmentation_may_not_be_internal_project_evidence",
                    "external_augmentation_may_not_replace_evidence_binding",
                    "external_augmentation_may_not_close_evidence_gap",
                    "business_line_whitebox_confirmation_required",
                )
            )
            or any(
                scenario.get(field) is not False
                for field in (
                    "automatic_review_operation_allowed",
                    "automatic_evidence_or_report_writeback_allowed",
                    "actual_review_queue_or_ui_execution_performed",
                    "actual_review_audit_or_database_execution_performed",
                    "actual_evidence_or_report_writeback_execution_performed",
                    "actual_human_confirmation_execution_performed",
                )
            )
        ):
            return False

    expected_handling_fields = tuple(
        getattr(phase3_module, "BUSINESS_LINE_WHITEBOX_HANDLING_FIELDS", ())
    )
    handlings = report.get("business_line_whitebox_handlings")
    if (
        not isinstance(handlings, list)
        or len(expected_handling_fields) != 8
        or len(handlings) != P3_HUMAN_HANDLING_COUNT
        or tuple(
            handling.get("scenario_id")
            for handling in handlings
            if isinstance(handling, Mapping)
        )
        != P3_SCENARIO_IDS
    ):
        return False
    for handling in handlings:
        if (
            not isinstance(handling, Mapping)
            or set(handling) != set(expected_handling_fields)
            or not _is_control_reference(handling.get("human_confirmation_item_ref"))
            or not _is_control_reference(
                handling.get("business_line_whitebox_confirmation_gate_ref")
            )
            or handling.get("confirmation_required") is not True
            or handling.get("actual_human_confirmation_execution_performed") is not False
            or handling.get("handling_state")
            != "BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED"
        ):
            return False

    views = report.get("control_views")
    view_fields = getattr(phase3_module, "CONTROL_VIEW_FIELDS", {})
    return (
        isinstance(views, Mapping)
        and isinstance(view_fields, Mapping)
        and set(views) == set(view_fields)
        and all(
            isinstance(records, list)
            and len(records) == len(P3_SCENARIO_IDS)
            and all(
                isinstance(record, Mapping) and set(record) == set(view_fields[name])
                for record in records
            )
            for name, records in views.items()
        )
    )


def _phase3_runtime_is_closed(phase3_module: Any, report: Mapping[str, Any]) -> bool:
    boundary = report.get("runtime_boundary")
    expected_fields = tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
    return (
        isinstance(boundary, Mapping)
        and tuple(boundary) == expected_fields
        and all(value is False for value in boundary.values())
        and all(
            value == 0
            for key, value in report.items()
            if key.startswith("actual_") and isinstance(value, int)
        )
    )


def _phase3_control_replay_matches(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> bool:
    """只接受当前冻结 P3 的逐项控制投影。"""

    return all(
        expected.get(field) == actual.get(field)
        for field in (
            "scenario_results",
            "control_views",
            "business_line_whitebox_handlings",
            "runtime_boundary",
        )
    )


def _review_queue_sample_record(
    scenario: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"review-queue-sample-{index}"),
        "scenario_id": scenario["scenario_id"],
        "review_queue_item_ref": scenario["review_queue_item_ref"],
        "review_queue_schema_ref": scenario["review_queue_schema_ref"],
        "review_queue_entry_reason_ref": scenario["review_queue_entry_reason_ref"],
        "review_trigger_type_ref": scenario["review_trigger_type_ref"],
        "review_status_ref": scenario["review_status_ref"],
        "source_document_ref": scenario["source_document_ref"],
        "evidence_id_ref": scenario["evidence_id_ref"],
        "evidence_gap_ref": scenario["evidence_gap_ref"],
        "evidence_risk_ref": scenario["evidence_risk_ref"],
        "low_ocr_confidence_ref": scenario["low_ocr_confidence_ref"],
        "source_conflict_ref": scenario["source_conflict_ref"],
        "parsing_failure_ref": scenario["parsing_failure_ref"],
        "review_queue_sample_state": (
            "CONTROL_REVIEW_QUEUE_SAMPLE_REFERENCE_ONLY_NOT_RENDERED"
        ),
        "business_line_whitebox_confirmation_required": scenario[
            "business_line_whitebox_confirmation_required"
        ],
        "actual_review_queue_sample_rendered": False,
    }


def _review_audit_log_sample_record(
    scenario: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"review-audit-log-sample-{index}"),
        "scenario_id": scenario["scenario_id"],
        "review_audit_record_ref": scenario["review_audit_record_ref"],
        "review_actor_ref": scenario["review_actor_ref"],
        "review_time_ref": scenario["review_time_ref"],
        "review_reason_ref": scenario["review_reason_ref"],
        "old_value_ref": scenario["old_value_ref"],
        "new_value_ref": scenario["new_value_ref"],
        "review_result_ref": scenario["review_result_ref"],
        "re_review_reference_ref": scenario["re_review_reference_ref"],
        "archive_reference_ref": scenario["archive_reference_ref"],
        "review_audit_sample_state": (
            "CONTROL_REVIEW_AUDIT_LOG_SAMPLE_REFERENCE_ONLY_NOT_WRITTEN"
        ),
        "actual_review_audit_log_written": False,
    }


def _review_ui_flow_explanation_record(
    scenario: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"review-ui-flow-explanation-{index}"),
        "scenario_id": scenario["scenario_id"],
        "review_queue_item_ref": scenario["review_queue_item_ref"],
        "review_status_ref": scenario["review_status_ref"],
        "review_reason_chinese_control_message": scenario[
            "review_reason_chinese_control_message"
        ],
        "review_ui_flow_step_ref": _delivery_ref(f"review-ui-flow-step-{index}"),
        "review_ui_entry_control_ref": _delivery_ref(f"review-ui-entry-{index}"),
        "review_ui_feedback_state": (
            "CONTROL_CHINESE_UI_FLOW_EXPLANATION_REFERENCE_ONLY_NOT_RENDERED"
        ),
        "screenshot_or_real_ui_rendered": False,
        "automatic_review_operation_allowed": False,
        "business_line_whitebox_confirmation_required": scenario[
            "business_line_whitebox_confirmation_required"
        ],
        "actual_review_ui_rendered": False,
        "actual_user_feedback_delivered": False,
    }


def _human_judgment_boundary_record(
    scenario: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"human-judgment-boundary-{index}"),
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "human_confirmation_item_ref": scenario["human_confirmation_item_ref"],
        "business_line_whitebox_confirmation_gate_ref": scenario[
            "business_line_whitebox_confirmation_gate_ref"
        ],
        "review_result_ref": scenario["review_result_ref"],
        "evidence_trust_level_before_ref": scenario[
            "evidence_trust_level_before_ref"
        ],
        "evidence_trust_level_after_ref": scenario[
            "evidence_trust_level_after_ref"
        ],
        "report_quality_score_before_ref": scenario[
            "report_quality_score_before_ref"
        ],
        "report_quality_score_after_ref": scenario[
            "report_quality_score_after_ref"
        ],
        "report_status_impact_ref": scenario["report_status_impact_ref"],
        "human_judgment_boundary_state": (
            "CONTROL_BUSINESS_LINE_WHITEBOX_JUDGMENT_REQUIRED_NOT_RECORDED"
        ),
        "business_line_whitebox_confirmation_required": scenario[
            "business_line_whitebox_confirmation_required"
        ],
        "automatic_evidence_or_report_writeback_allowed": False,
        "actual_human_confirmation_performed": False,
    }


def _business_line_whitebox_confirmation_record(
    scenario: Mapping[str, Any], handling: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"whitebox-confirmation-{index}"),
        "scenario_id": scenario["scenario_id"],
        "handling_code": handling["handling_code"],
        "human_confirmation_item_ref": handling["human_confirmation_item_ref"],
        "business_line_whitebox_confirmation_gate_ref": handling[
            "business_line_whitebox_confirmation_gate_ref"
        ],
        "external_augmentation_source_separation_state": scenario[
            "external_augmentation_source_separation_state"
        ],
        "whitebox_confirmation_state": (
            "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
        ),
        "confirmation_required": handling["confirmation_required"],
        "automatic_final_conclusion_allowed": False,
        "actual_human_confirmation_execution_performed": False,
        "actual_final_conclusion_published": False,
        "actual_review_state_transition_performed": False,
        "actual_evidence_or_report_writeback_execution_performed": False,
        "persistent_state_write_performed": False,
    }


def _rollback_and_re_review_instruction_records() -> list[dict[str, Any]]:
    return [
        {
            "instruction_id": _delivery_ref("review-queue-rollback-instruction"),
            "control_domain": "REVIEW_QUEUE_ROLLBACK",
            "trigger_state_ref": _delivery_ref("review-queue-rollback-trigger"),
            "rollback_target_ref": _delivery_ref("stage113-p3-controlled-scenarios"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage113-p3"),
            "review_queue_schema_ref": _delivery_ref("review-queue-schema"),
            "review_audit_record_ref": _delivery_ref("review-audit-record"),
            "business_line_whitebox_confirmation_required": True,
            "human_confirmation_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_review_queue_rollback_performed": False,
            "actual_re_review_performed": False,
        },
        {
            "instruction_id": _delivery_ref("re-review-instruction"),
            "control_domain": "RE_REVIEW",
            "trigger_state_ref": _delivery_ref("re-review-trigger"),
            "rollback_target_ref": _delivery_ref("stage113-p3-controlled-scenarios"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage113-p3"),
            "review_queue_schema_ref": _delivery_ref("review-queue-schema"),
            "review_audit_record_ref": _delivery_ref("review-audit-record"),
            "business_line_whitebox_confirmation_required": True,
            "human_confirmation_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_review_queue_rollback_performed": False,
            "actual_re_review_performed": False,
        },
    ]


def _records_match_fields(
    report: Mapping[str, Any], name: str, fields: tuple[str, ...], count: int
) -> bool:
    records = report.get(name)
    return (
        isinstance(records, list)
        and len(records) == count
        and all(isinstance(record, Mapping) and set(record) == set(fields) for record in records)
    )


def _validate_delivery_groups(report: Mapping[str, Any]) -> Optional[str]:
    expected_counts = {
        "review_queue_sample_control_records": len(P3_SCENARIO_IDS),
        "review_audit_log_sample_control_records": len(P3_SCENARIO_IDS),
        "review_ui_flow_explanation_control_records": len(P3_SCENARIO_IDS),
        "human_judgment_boundary_control_records": len(P3_SCENARIO_IDS),
        "business_line_whitebox_confirmation_control_records": len(P3_SCENARIO_IDS),
        "rollback_and_re_review_instruction_control_records": 2,
    }
    for name, fields in DELIVERY_GROUPS:
        if not _records_match_fields(report, name, fields, expected_counts[name]):
            return "DELIVERY_RECORD_SHAPE_MISMATCH"

    for name, _fields in DELIVERY_GROUPS[:-1]:
        for record in report[name]:
            if not _is_delivery_reference(record["delivery_record_id"]):
                return "DELIVERY_REFERENCE_NOT_OPAQUE"
            if record["scenario_id"] not in P3_SCENARIO_IDS:
                return "CONTROLLED_SCENARIO_BINDING_INVALID"
            if any(
                value is not False
                for key, value in record.items()
                if key.startswith("actual_")
                or key.startswith("automatic_")
                or key in {"screenshot_or_real_ui_rendered", "persistent_state_write_performed"}
            ):
                return "ACTUAL_REVIEW_QUEUE_OR_AUDIT_WRITE_SIGNAL_DETECTED"

    for record in report["review_queue_sample_control_records"]:
        evidence_id = record["evidence_id_ref"]
        evidence_gap = record["evidence_gap_ref"]
        if (
            (evidence_id is None) == (evidence_gap is None)
            or (evidence_id is not None and not _is_control_reference(evidence_id))
            or (evidence_gap is not None and not _is_control_reference(evidence_gap))
            or not all(
                _is_control_reference(record[field])
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
            or record["review_queue_sample_state"]
            != "CONTROL_REVIEW_QUEUE_SAMPLE_REFERENCE_ONLY_NOT_RENDERED"
            or record["business_line_whitebox_confirmation_required"] is not True
            or record["actual_review_queue_sample_rendered"] is not False
        ):
            return "REVIEW_QUEUE_SAMPLE_CONTROL_MISSING"

    for record in report["review_audit_log_sample_control_records"]:
        if (
            not all(
                _is_control_reference(record[field])
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
            or record["review_audit_sample_state"]
            != "CONTROL_REVIEW_AUDIT_LOG_SAMPLE_REFERENCE_ONLY_NOT_WRITTEN"
            or record["actual_review_audit_log_written"] is not False
        ):
            return "REVIEW_AUDIT_LOG_SAMPLE_CONTROL_MISSING"

    for record in report["review_ui_flow_explanation_control_records"]:
        if (
            not _is_control_reference(record["review_queue_item_ref"])
            or not _is_control_reference(record["review_status_ref"])
            or not isinstance(record["review_reason_chinese_control_message"], str)
            or not record["review_reason_chinese_control_message"]
            or not _is_delivery_reference(record["review_ui_flow_step_ref"])
            or not _is_delivery_reference(record["review_ui_entry_control_ref"])
            or record["review_ui_feedback_state"]
            != "CONTROL_CHINESE_UI_FLOW_EXPLANATION_REFERENCE_ONLY_NOT_RENDERED"
            or record["screenshot_or_real_ui_rendered"] is not False
            or record["automatic_review_operation_allowed"] is not False
            or record["business_line_whitebox_confirmation_required"] is not True
            or record["actual_review_ui_rendered"] is not False
            or record["actual_user_feedback_delivered"] is not False
        ):
            return "REVIEW_UI_FLOW_EXPLANATION_CONTROL_MISSING"

    for record in report["human_judgment_boundary_control_records"]:
        if (
            not all(
                _is_control_reference(record[field])
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
            or record["human_judgment_boundary_state"]
            != "CONTROL_BUSINESS_LINE_WHITEBOX_JUDGMENT_REQUIRED_NOT_RECORDED"
            or record["business_line_whitebox_confirmation_required"] is not True
            or record["automatic_evidence_or_report_writeback_allowed"] is not False
            or record["actual_human_confirmation_performed"] is not False
        ):
            return "HUMAN_JUDGMENT_BOUNDARY_CONTROL_MISSING"

    external_state_seen = False
    for record in report["business_line_whitebox_confirmation_control_records"]:
        if (
            not _is_control_reference(record["human_confirmation_item_ref"])
            or not _is_control_reference(
                record["business_line_whitebox_confirmation_gate_ref"]
            )
            or not isinstance(record["handling_code"], str)
            or not record["handling_code"].startswith("BUSINESS_LINE_WHITEBOX_")
            or record["whitebox_confirmation_state"]
            != "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
            or record["confirmation_required"] is not True
            or record["automatic_final_conclusion_allowed"] is not False
        ):
            return "BUSINESS_LINE_WHITEBOX_CONFIRMATION_CONTROL_MISSING"
        if record["external_augmentation_source_separation_state"] == (
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
            "SEPARATE_FROM_INTERNAL_EVIDENCE"
        ):
            external_state_seen = True
        else:
            return "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING"
    if not external_state_seen:
        return "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING"

    instructions = report["rollback_and_re_review_instruction_control_records"]
    if any(
        not _is_delivery_reference(record["instruction_id"])
        or record["control_domain"]
        not in {"REVIEW_QUEUE_ROLLBACK", "RE_REVIEW"}
        or not _is_delivery_reference(record["trigger_state_ref"])
        or not _is_delivery_reference(record["rollback_target_ref"])
        or record["rollback_target_result"] != P3_PASS_RESULT
        or not _is_delivery_reference(record["predecessor_phase_ref"])
        or not _is_delivery_reference(record["review_queue_schema_ref"])
        or not _is_delivery_reference(record["review_audit_record_ref"])
        or record["business_line_whitebox_confirmation_required"] is not True
        or record["human_confirmation_required"] is not True
        or record["versioned_basis_required"] is not True
        or record["verifiable_rollback_target_required"] is not True
        or record["actual_review_queue_rollback_performed"] is not False
        or record["actual_re_review_performed"] is not False
        for record in instructions
    ):
        return "REVIEW_QUEUE_ROLLBACK_AND_RE_REVIEW_CONTROL_MISSING"

    if report.get("second_authoritative_source_created") is not False:
        return "SECOND_AUTHORITY_CREATED"
    if report.get("persistent_record_created") is not False:
        return "SECOND_AUTHORITY_CREATED"
    boundary = report.get("runtime_boundary")
    if (
        not isinstance(boundary, Mapping)
        or tuple(boundary) != RUNTIME_CLOSED_FIELDS
        or any(value is not False for value in boundary.values())
        or any(
            value != 0
            for key, value in report.items()
            if key.startswith("actual_") and isinstance(value, int)
        )
    ):
        return "ACTUAL_REVIEW_QUEUE_OR_AUDIT_WRITE_SIGNAL_DETECTED"
    return None


def build_review_queue_schema_phase4_delivery_report(
    phase3_executor: Optional[Phase3Executor] = None,
) -> dict[str, Any]:
    """从固定 P3 场景派生纯内存 P4 metadata-only 交付控制记录。"""

    try:
        phase3_module = _load_phase3_module()
        canonical_phase3_report = phase3_module.build_review_queue_schema_phase3_report()
        executor = (
            phase3_executor
            if phase3_executor is not None
            else lambda: canonical_phase3_report
        )
        phase3_report = executor()
    except Exception:
        return _base_report(False, "PHASE3_CONTROL_REPLAY_UNAVAILABLE")

    if not isinstance(phase3_report, Mapping) or not _phase3_shape_is_preserved(
        phase3_module, phase3_report
    ):
        return _base_report(False, "PHASE3_CONTROL_SHAPE_MISMATCH")
    if not _phase3_runtime_is_closed(phase3_module, phase3_report):
        return _base_report(False, "PHASE3_RUNTIME_BOUNDARY_BREACH")
    if not _phase3_control_replay_matches(canonical_phase3_report, phase3_report):
        return _base_report(False, "PHASE3_CONTROL_SHAPE_MISMATCH")

    scenarios = phase3_report["scenario_results"]
    handlings_by_scenario = {
        handling["scenario_id"]
        : handling
        for handling in phase3_report["business_line_whitebox_handlings"]
    }
    if set(handlings_by_scenario) != set(P3_SCENARIO_IDS):
        return _base_report(False, "BUSINESS_LINE_WHITEBOX_CONFIRMATION_CONTROL_MISSING")

    report = _base_report(True, None)
    report.update(
        {
            "phase3_control_shape_preserved": True,
            "phase3_side_effect_free": True,
            "control_references_opaque": True,
            "phase2_control_request_count": P3_PHASE2_CONTROL_REQUEST_COUNT,
            "phase2_input_field_count": P3_PHASE2_INPUT_FIELD_COUNT,
            "phase2_phase1_reference_field_count": (
                P3_PHASE2_PHASE1_REFERENCE_FIELD_COUNT
            ),
            "phase2_projection_group_count": P3_PHASE2_PROJECTION_GROUP_COUNT,
            "phase2_projection_field_count_per_request": (
                P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST
            ),
            "phase2_projection_field_count_total": (
                P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL
            ),
            "scenario_count": len(scenarios),
            "scenario_field_check_count": len(scenarios) * P3_SCENARIO_FIELD_COUNT,
            "control_view_count": P3_CONTROL_VIEW_COUNT,
            "business_line_whitebox_handling_count": P3_HUMAN_HANDLING_COUNT,
            "whitebox_confirmation_required_scenario_count": (
                P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
            ),
            "review_queue_sample_control_records": [
                _review_queue_sample_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "review_audit_log_sample_control_records": [
                _review_audit_log_sample_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "review_ui_flow_explanation_control_records": [
                _review_ui_flow_explanation_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "human_judgment_boundary_control_records": [
                _human_judgment_boundary_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "business_line_whitebox_confirmation_control_records": [
                _business_line_whitebox_confirmation_record(
                    scenario, handlings_by_scenario[scenario["scenario_id"]], index
                )
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "rollback_and_re_review_instruction_control_records": (
                _rollback_and_re_review_instruction_records()
            ),
            "delivery_field_check_count": DELIVERY_FIELD_CHECK_COUNT,
            "operator_feedback": list(OPERATOR_FEEDBACK),
        }
    )
    failure_state = _validate_delivery_groups(report)
    if failure_state is not None:
        return _base_report(False, failure_state)
    return report
