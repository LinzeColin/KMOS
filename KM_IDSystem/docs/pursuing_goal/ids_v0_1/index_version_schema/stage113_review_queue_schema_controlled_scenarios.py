"""Stage113 P3 复核队列 Schema 的纯内存专项异常场景验证。

模块只重放 Stage113 P2 固定、非业务、reference-only 控制投影。它把低质量
OCR、资料冲突、撤回资料、证据可信等级与报告质量影响，以及外部增强不能替代内部
证据，表达为可审阅的未来控制记录。模块不读取真实资料、OCR、证据账本、报告或
审计日志，不创建队列、UI、审计或写回，也不调用模型、Agent、OVH 或生产服务。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from . import stage113_review_queue_schema_control_slice as phase2


SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA_SCENARIOS"
CURRENT_GATE = "IDS-STAGE113-P3-GATE"
NEXT_GATE = "IDS-STAGE113-P4-GATE"
PASS_RESULT = "PASS_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

P2_SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA"
P2_EXECUTION_STATE = "PASS_IN_MEMORY_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED"
P2_CONTROL_PREFIX = ":control:stage113-p2:"
P2_CONTROL_FIELDS = ("review_queue_schema_control_requests",)
P2_CONTROL_REQUEST_COUNT = 5
P2_INPUT_FIELD_COUNT = 32
P2_PHASE1_REFERENCE_FIELD_COUNT = 29
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 101
P2_PROJECTION_FIELD_COUNT_TOTAL = 505
P2_CONTROL_SCENARIOS = (
    "low_ocr_pending_review_reference_only",
    "source_conflict_confirmed_reference_only",
    "parsing_failure_needs_more_material_reference_only",
    "evidence_risk_rejected_reference_only",
    "external_augmentation_archived_reference_only",
)
P2_PROJECTION_PREFIXES = (
    "review_queue_schema_and_workflow",
    "review_audit",
    "evidence_risk_and_report_status_writeback",
    "human_reason_and_source_boundary",
)

RUNTIME_CLOSED_FIELDS = (
    *phase2.RUNTIME_CLOSED_FIELDS,
    "phase2_control_slice_runtime_executed",
    "stage113_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_existing_audit_log_read_count",
    "actual_low_ocr_evaluation_count",
    "actual_source_conflict_evaluation_count",
    "actual_withdrawn_material_evaluation_count",
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

SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
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
    "review_reason_chinese_control_message",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
    "review_operation_audit_state",
    "review_result_evidence_trust_impact_state",
    "review_result_report_quality_impact_state",
    "withdrawn_material_re_review_state",
    "external_augmentation_source_separation_state",
    "external_augmentation_may_not_be_internal_project_evidence",
    "external_augmentation_may_not_replace_evidence_binding",
    "external_augmentation_may_not_close_evidence_gap",
    "business_line_whitebox_confirmation_required",
    "automatic_review_operation_allowed",
    "automatic_evidence_or_report_writeback_allowed",
    "actual_review_queue_or_ui_execution_performed",
    "actual_review_audit_or_database_execution_performed",
    "actual_evidence_or_report_writeback_execution_performed",
    "actual_human_confirmation_execution_performed",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "review_queue_trigger_and_status_control_view": (
        "scenario_id",
        "scenario_category",
        "phase2_control_scenario",
        "review_queue_item_ref",
        "review_queue_schema_ref",
        "review_queue_entry_reason_ref",
        "review_trigger_type_ref",
        "review_status_ref",
        "low_ocr_confidence_ref",
        "source_conflict_ref",
        "parsing_failure_ref",
        "evidence_risk_ref",
        "withdrawn_material_re_review_state",
    ),
    "review_operation_audit_control_view": (
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
        "review_operation_audit_state",
    ),
    "evidence_trust_and_report_quality_impact_control_view": (
        "scenario_id",
        "evidence_id_ref",
        "evidence_gap_ref",
        "evidence_trust_level_before_ref",
        "evidence_trust_level_after_ref",
        "report_quality_score_before_ref",
        "report_quality_score_after_ref",
        "report_status_impact_ref",
        "review_queue_writeback_control_label",
        "review_result_evidence_trust_impact_state",
        "review_result_report_quality_impact_state",
    ),
    "external_augmentation_source_separation_control_view": (
        "scenario_id",
        "external_augmentation_underlying_source_type_ref",
        "external_public_reference_control_label",
        "model_reasoning_control_label",
        "external_augmentation_source_separation_state",
        "external_augmentation_may_not_be_internal_project_evidence",
        "external_augmentation_may_not_replace_evidence_binding",
        "external_augmentation_may_not_close_evidence_gap",
    ),
    "business_line_whitebox_and_execution_boundary_control_view": (
        "scenario_id",
        "human_confirmation_item_ref",
        "business_line_whitebox_confirmation_gate_ref",
        "business_line_whitebox_confirmation_required",
        "automatic_review_operation_allowed",
        "automatic_evidence_or_report_writeback_allowed",
        "actual_review_queue_or_ui_execution_performed",
        "actual_review_audit_or_database_execution_performed",
        "actual_evidence_or_report_writeback_execution_performed",
        "actual_human_confirmation_execution_performed",
        "expectation_met",
    ),
}

BUSINESS_LINE_WHITEBOX_HANDLING_FIELDS = (
    "scenario_id",
    "scenario_category",
    "handling_code",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "confirmation_required",
    "actual_human_confirmation_execution_performed",
    "handling_state",
)

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "low_quality_ocr_review_operation_control",
        "scenario_category": "LOW_QUALITY_OCR_REVIEW_OPERATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_binding_mode": "evidence_id",
        "expected_review_status": "pending_review",
        "low_ocr_required": True,
        "source_conflict_required": False,
        "withdrawn_material_required": False,
        "impact_required": False,
        "external_augmentation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_LOW_QUALITY_OCR"
        ),
    },
    {
        "scenario_id": "conflicting_material_review_audit_control",
        "scenario_category": "CONFLICTING_MATERIAL_REVIEW_AUDIT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_binding_mode": "evidence_gap",
        "expected_review_status": "confirmed",
        "low_ocr_required": False,
        "source_conflict_required": True,
        "withdrawn_material_required": False,
        "impact_required": False,
        "external_augmentation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_CONFLICTING_MATERIAL"
        ),
    },
    {
        "scenario_id": "withdrawn_material_re_review_control",
        "scenario_category": "WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_binding_mode": "evidence_gap",
        "expected_review_status": "needs_more_material",
        "low_ocr_required": False,
        "source_conflict_required": False,
        "withdrawn_material_required": True,
        "impact_required": False,
        "external_augmentation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_WITHDRAWN_MATERIAL_RE_REVIEW"
        ),
    },
    {
        "scenario_id": "evidence_trust_report_quality_impact_control",
        "scenario_category": "EVIDENCE_TRUST_AND_REPORT_QUALITY_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_binding_mode": "evidence_id",
        "expected_review_status": "rejected",
        "low_ocr_required": False,
        "source_conflict_required": False,
        "withdrawn_material_required": False,
        "impact_required": True,
        "external_augmentation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_TRUST_AND_REPORT_QUALITY"
        ),
    },
    {
        "scenario_id": "external_augmentation_internal_evidence_replacement_control",
        "scenario_category": (
            "EXTERNAL_AUGMENTATION_INTERNAL_EVIDENCE_REPLACEMENT_CONTROL"
        ),
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_binding_mode": "evidence_id",
        "expected_review_status": "archived",
        "low_ocr_required": False,
        "source_conflict_required": False,
        "withdrawn_material_required": False,
        "impact_required": False,
        "external_augmentation_required": True,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EXTERNAL_AUGMENTATION_SOURCE_SEPARATION"
        ),
    },
)

FAILURE_STATES = (
    "PHASE2_CONTROL_SHAPE_MISMATCH",
    "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH",
    "P2_PERSISTENT_RECORD_BOUNDARY_BREACH",
    "P2_CONTROL_REFERENCE_OPAQUENESS_BREACH",
    "SCENARIO_BINDING_CONTROL_INVALID",
    "LOW_QUALITY_OCR_CONTROL_MISSING",
    "CONFLICTING_MATERIAL_CONTROL_MISSING",
    "WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL_MISSING",
    "REVIEW_AUDIT_CONTROL_MISSING",
    "REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_CONTROL_MISSING",
    "REVIEW_RESULT_CONTROL_MISSING",
    "EVIDENCE_TRUST_OR_REPORT_QUALITY_CONTROL_MISSING",
    "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
    "BUSINESS_LINE_WHITEBOX_CONFIRMATION_GATE_MISSING",
    "AUTOMATIC_REVIEW_OR_WRITEBACK_BOUNDARY_BREACH",
)

CHINESE_FEEDBACK = (
    "复核队列专项场景已验证，低质量 OCR、资料冲突和撤回资料保持 reference-only 控制记录。",
    "复核操作保留 actor、time、reason、old value、new value 与复核结果的未来审计引用。",
    "复核结果对 evidence trust level 与报告质量分的影响保持未来写回控制，业务线白箱确认仍为前置。",
    "外部增强保持外部来源身份，不能替代内部证据；真实队列、审计、写回、模型、Agent、OVH 与生产保持未执行。",
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


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


def _base_report(valid: bool, failure_state: Optional[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "execution_state": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": CURRENT_GATE,
        "next_gate": NEXT_GATE if valid else CURRENT_GATE,
        "phase2_control_shape_preserved": False,
        "phase2_side_effect_free": False,
        "control_references_opaque": False,
        "phase2_control_replay_request_count": 0,
        "phase2_input_field_count": 0,
        "phase2_phase1_reference_field_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_projection_field_count_per_request": 0,
        "phase2_projection_field_check_count": 0,
        "scenario_count": 0,
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": 0,
        "scenario_results": [],
        "control_view_count": 0,
        "control_views": {},
        "business_line_whitebox_handling_count": 0,
        "business_line_whitebox_handlings": [],
        "whitebox_confirmation_required_scenario_count": 0,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": list(CHINESE_FEEDBACK),
        **_zero_actual_counts(),
    }


def _phase2_shape_is_preserved(result: Mapping[str, Any]) -> bool:
    if (
        phase2.SCHEMA_VERSION != P2_SCHEMA_VERSION
        or phase2.RECORD_KIND != P2_RECORD_KIND
        or phase2.PASS_RESULT != P2_EXECUTION_STATE
        or tuple(phase2.CONTROL_FIELDS) != P2_CONTROL_FIELDS
        or tuple(phase2.CONTROL_SCENARIOS) != P2_CONTROL_SCENARIOS
        or len(phase2.INPUT_FIELDS) != P2_INPUT_FIELD_COUNT
        or len(phase2.PHASE1_CONTROL_REFERENCE_FIELDS)
        != P2_PHASE1_REFERENCE_FIELD_COUNT
        or len(phase2.PROJECTION_FIELDS) != P2_PROJECTION_GROUP_COUNT
        or tuple(prefix for prefix, _fields in phase2.PROJECTION_FIELDS)
        != P2_PROJECTION_PREFIXES
    ):
        return False
    if (
        result.get("schema_version") != P2_SCHEMA_VERSION
        or result.get("record_kind") != P2_RECORD_KIND
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("control_input_count") != P2_CONTROL_REQUEST_COUNT
        or result.get("control_projection_group_count") != P2_PROJECTION_GROUP_COUNT
        or result.get("control_projection_field_total_per_request")
        != P2_PROJECTION_FIELD_COUNT_PER_REQUEST
        or result.get("control_projection_field_total")
        != P2_PROJECTION_FIELD_COUNT_TOTAL
    ):
        return False
    for prefix, fields in phase2.PROJECTION_FIELDS:
        records = result.get(f"{prefix}_control_projections")
        if (
            result.get(f"{prefix}_control_projection_count")
            != P2_CONTROL_REQUEST_COUNT
            or not isinstance(records, list)
            or len(records) != P2_CONTROL_REQUEST_COUNT
            or any(
                not isinstance(record, Mapping) or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return True


def _phase2_runtime_is_closed(result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    return (
        result.get("persistent_record_created") is False
        and isinstance(boundary, Mapping)
        and set(boundary) == set(phase2.RUNTIME_CLOSED_FIELDS)
        and all(value is False for value in boundary.values())
        and all(
            value == 0
            for key, value in result.items()
            if key.startswith("actual_") and isinstance(value, int)
        )
    )


def _control_input_is_opaque(control_input: Mapping[str, Any]) -> bool:
    requests = control_input.get(P2_CONTROL_FIELDS[0])
    if not isinstance(requests, list) or len(requests) != P2_CONTROL_REQUEST_COUNT:
        return False
    for request in requests:
        if not isinstance(request, Mapping) or set(request) != set(phase2.INPUT_FIELDS):
            return False
        if request.get("control_scenario") not in P2_CONTROL_SCENARIOS:
            return False
        if request.get("binding_mode") not in {
            "CONTROL_BINDING_EVIDENCE_ID",
            "CONTROL_BINDING_EVIDENCE_GAP",
        }:
            return False
        if (
            request.get("fixed_review_status_control_value")
            not in phase2.FIXED_REVIEW_STATUSES
        ):
            return False
        if bool(request.get("evidence_id_ref")) == bool(request.get("evidence_gap_ref")):
            return False
        for field in phase2.PHASE1_CONTROL_REFERENCE_FIELDS:
            value = request.get(field)
            if value is not None and not _is_control_reference(value):
                return False
    return True


def _binding_mode(request: Mapping[str, Any]) -> Optional[str]:
    if bool(request.get("evidence_id_ref")) == bool(request.get("evidence_gap_ref")):
        return None
    return "evidence_id" if request.get("evidence_id_ref") else "evidence_gap"


def _all_control_references(record: Mapping[str, Any], fields: tuple[str, ...]) -> bool:
    return all(_is_control_reference(record.get(field)) for field in fields)


def _automatic_execution_boundary_is_closed(
    workflow: Mapping[str, Any],
    audit: Mapping[str, Any],
    writeback: Mapping[str, Any],
    source_boundary: Mapping[str, Any],
) -> bool:
    checks = (
        *(workflow.get(field) is False for field in (
            "automatic_review_queue_schema_migration_allowed",
            "automatic_review_queue_entry_allowed",
            "automatic_review_status_transition_allowed",
            "actual_review_queue_schema_migration_performed",
            "actual_review_queue_entry_created",
            "actual_review_status_transition_performed",
        )),
        *(audit.get(field) is False for field in (
            "automatic_review_audit_write_allowed",
            "automatic_human_confirmation_allowed",
            "actual_review_audit_written",
            "actual_actor_time_reason_old_new_recorded",
            "actual_human_confirmation_recorded",
        )),
        *(writeback.get(field) is False for field in (
            "automatic_evidence_risk_writeback_allowed",
            "automatic_evidence_trust_level_change_allowed",
            "automatic_report_quality_score_change_allowed",
            "automatic_report_status_change_allowed",
            "actual_evidence_risk_writeback_performed",
            "actual_evidence_trust_level_changed",
            "actual_report_quality_score_changed",
            "actual_report_status_changed",
        )),
        *(source_boundary.get(field) is False for field in (
            "automatic_user_feedback_delivery_allowed",
            "automatic_human_confirmation_allowed",
            "automatic_final_conclusion_allowed",
            "actual_review_ui_rendered",
            "actual_external_augmentation_displayed",
            "actual_human_confirmation_recorded",
            "actual_final_conclusion_published",
        )),
    )
    return all(checks)


def _failure_for_projection(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    audit: Mapping[str, Any],
    writeback: Mapping[str, Any],
    source_boundary: Mapping[str, Any],
) -> Optional[str]:
    if (
        request.get("control_scenario") != definition["phase2_control_scenario"]
        or workflow.get("control_scenario") != definition["phase2_control_scenario"]
        or audit.get("control_scenario") != definition["phase2_control_scenario"]
        or writeback.get("control_scenario") != definition["phase2_control_scenario"]
        or source_boundary.get("control_scenario") != definition["phase2_control_scenario"]
        or _binding_mode(request) != definition["expected_binding_mode"]
        or request.get("fixed_review_status_control_value")
        != definition["expected_review_status"]
    ):
        return "SCENARIO_BINDING_CONTROL_INVALID"
    if definition["low_ocr_required"] and not _is_control_reference(
        request.get("low_ocr_confidence_ref")
    ):
        return "LOW_QUALITY_OCR_CONTROL_MISSING"
    if definition["source_conflict_required"] and not _is_control_reference(
        request.get("source_conflict_ref")
    ):
        return "CONFLICTING_MATERIAL_CONTROL_MISSING"
    if definition["withdrawn_material_required"] and not _all_control_references(
        audit, ("re_review_reference_ref", "archive_reference_ref")
    ):
        return "WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL_MISSING"
    if not _all_control_references(
        audit,
        (
            "review_audit_record_ref",
            "review_actor_ref",
            "review_time_ref",
            "review_reason_ref",
            "old_value_ref",
            "new_value_ref",
        ),
    ):
        return "REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_CONTROL_MISSING"
    if not _is_control_reference(audit.get("review_result_ref")):
        return "REVIEW_RESULT_CONTROL_MISSING"
    if audit.get("review_audit_control_state") != (
        "CONTROL_REVIEW_AUDIT_REFERENCE_ONLY_NOT_WRITTEN"
    ):
        return "REVIEW_AUDIT_CONTROL_MISSING"
    if definition["impact_required"] and not (
        _all_control_references(
            writeback,
            (
                "evidence_trust_level_before_ref",
                "evidence_trust_level_after_ref",
                "report_quality_score_before_ref",
                "report_quality_score_after_ref",
                "report_status_impact_ref",
            ),
        )
        and writeback.get("evidence_trust_level_control_state")
        == "CONTROL_EVIDENCE_TRUST_LEVEL_REFERENCE_ONLY_NOT_CHANGED"
        and writeback.get("report_quality_score_control_state")
        == "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CHANGED"
    ):
        return "EVIDENCE_TRUST_OR_REPORT_QUALITY_CONTROL_MISSING"
    if definition["external_augmentation_required"] and not (
        _is_control_reference(
            source_boundary.get("external_public_reference_control_label")
        )
        and _is_control_reference(source_boundary.get("model_reasoning_control_label"))
        and source_boundary.get(
            "external_augmentation_may_not_be_internal_project_evidence"
        )
        is True
        and source_boundary.get(
            "external_augmentation_may_not_replace_evidence_binding"
        )
        is True
        and source_boundary.get("external_augmentation_may_not_close_evidence_gap")
        is True
    ):
        return "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE"
    if not (
        _all_control_references(
            source_boundary,
            (
                "human_confirmation_item_ref",
                "business_line_whitebox_confirmation_gate_ref",
            ),
        )
        and source_boundary.get("business_line_whitebox_confirmation_required")
        is True
    ):
        return "BUSINESS_LINE_WHITEBOX_CONFIRMATION_GATE_MISSING"
    if not _automatic_execution_boundary_is_closed(
        workflow, audit, writeback, source_boundary
    ):
        return "AUTOMATIC_REVIEW_OR_WRITEBACK_BOUNDARY_BREACH"
    return None


def _scenario_record(
    definition: Mapping[str, Any],
    workflow: Mapping[str, Any],
    audit: Mapping[str, Any],
    writeback: Mapping[str, Any],
    source_boundary: Mapping[str, Any],
) -> dict[str, Any]:
    scenario = definition["phase2_control_scenario"]
    withdrawn_material_state = (
        "CONTROL_WITHDRAWN_MATERIAL_RE_REVIEW_REFERENCE_ONLY_REQUIRED"
        if definition["withdrawn_material_required"]
        else "CONTROL_WITHDRAWN_MATERIAL_RE_REVIEW_REFERENCE_ONLY_NOT_TRIGGERED"
    )
    record = {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": scenario,
        "review_queue_item_ref": workflow["review_queue_item_ref"],
        "review_queue_schema_ref": workflow["review_queue_schema_ref"],
        "review_queue_entry_reason_ref": workflow["review_queue_entry_reason_ref"],
        "review_trigger_type_ref": workflow["review_trigger_type_ref"],
        "review_status_ref": workflow["review_status_ref"],
        "source_document_ref": workflow["source_document_ref"],
        "evidence_id_ref": workflow["evidence_id_ref"],
        "evidence_gap_ref": workflow["evidence_gap_ref"],
        "evidence_risk_ref": workflow["evidence_risk_ref"],
        "low_ocr_confidence_ref": workflow["low_ocr_confidence_ref"],
        "source_conflict_ref": workflow["source_conflict_ref"],
        "parsing_failure_ref": workflow["parsing_failure_ref"],
        "external_augmentation_underlying_source_type_ref": (
            source_boundary["external_augmentation_underlying_source_type_ref"]
        ),
        "evidence_trust_level_before_ref": (
            writeback["evidence_trust_level_before_ref"]
        ),
        "evidence_trust_level_after_ref": (
            writeback["evidence_trust_level_after_ref"]
        ),
        "report_quality_score_before_ref": (
            writeback["report_quality_score_before_ref"]
        ),
        "report_quality_score_after_ref": (
            writeback["report_quality_score_after_ref"]
        ),
        "report_status_impact_ref": writeback["report_status_impact_ref"],
        "review_audit_record_ref": audit["review_audit_record_ref"],
        "review_actor_ref": audit["review_actor_ref"],
        "review_time_ref": audit["review_time_ref"],
        "review_reason_ref": audit["review_reason_ref"],
        "old_value_ref": audit["old_value_ref"],
        "new_value_ref": audit["new_value_ref"],
        "review_result_ref": audit["review_result_ref"],
        "re_review_reference_ref": audit["re_review_reference_ref"],
        "archive_reference_ref": audit["archive_reference_ref"],
        "human_confirmation_item_ref": source_boundary["human_confirmation_item_ref"],
        "business_line_whitebox_confirmation_gate_ref": (
            source_boundary["business_line_whitebox_confirmation_gate_ref"]
        ),
        "review_queue_writeback_control_label": (
            writeback["review_queue_writeback_control_label"]
        ),
        "review_reason_chinese_control_message": (
            source_boundary["review_reason_chinese_control_message"]
        ),
        "external_public_reference_control_label": (
            source_boundary["external_public_reference_control_label"]
        ),
        "model_reasoning_control_label": source_boundary["model_reasoning_control_label"],
        "review_operation_audit_state": (
            "CONTROL_REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_REFERENCE_ONLY_"
            "NOT_RECORDED"
        ),
        "review_result_evidence_trust_impact_state": (
            "CONTROL_REVIEW_RESULT_EVIDENCE_TRUST_REFERENCE_ONLY_NOT_APPLIED"
        ),
        "review_result_report_quality_impact_state": (
            "CONTROL_REVIEW_RESULT_REPORT_QUALITY_REFERENCE_ONLY_NOT_APPLIED"
        ),
        "withdrawn_material_re_review_state": withdrawn_material_state,
        "external_augmentation_source_separation_state": (
            source_boundary["external_augmentation_representation_state"]
        ),
        "external_augmentation_may_not_be_internal_project_evidence": (
            source_boundary["external_augmentation_may_not_be_internal_project_evidence"]
        ),
        "external_augmentation_may_not_replace_evidence_binding": (
            source_boundary["external_augmentation_may_not_replace_evidence_binding"]
        ),
        "external_augmentation_may_not_close_evidence_gap": (
            source_boundary["external_augmentation_may_not_close_evidence_gap"]
        ),
        "business_line_whitebox_confirmation_required": (
            source_boundary["business_line_whitebox_confirmation_required"]
        ),
        "automatic_review_operation_allowed": False,
        "automatic_evidence_or_report_writeback_allowed": False,
        "actual_review_queue_or_ui_execution_performed": False,
        "actual_review_audit_or_database_execution_performed": False,
        "actual_evidence_or_report_writeback_execution_performed": False,
        "actual_human_confirmation_execution_performed": False,
        "expectation_met": True,
    }
    if set(record) != set(SCENARIO_FIELDS):
        raise ValueError("Stage113 P3 scenario field shape drift")
    return record


def _human_handling(
    definition: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "handling_code": definition["business_line_whitebox_handling_code"],
        "human_confirmation_item_ref": scenario["human_confirmation_item_ref"],
        "business_line_whitebox_confirmation_gate_ref": (
            scenario["business_line_whitebox_confirmation_gate_ref"]
        ),
        "confirmation_required": True,
        "actual_human_confirmation_execution_performed": False,
        "handling_state": "BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED",
    }


def _control_views(scenarios: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        name: [{field: scenario[field] for field in fields} for scenario in scenarios]
        for name, fields in CONTROL_VIEW_FIELDS.items()
    }


def build_review_queue_schema_phase3_report(
    control_input: Optional[Mapping[str, Any]] = None,
    phase2_executor: Phase2Executor = phase2.execute_review_queue_schema_control_slice,
) -> dict[str, Any]:
    """重放 P2 控制投影并输出 P3 专项场景；任何漂移均关闭失败。"""

    input_to_replay = control_input if control_input is not None else phase2.build_control_input()
    phase2_result = phase2_executor(input_to_replay)
    if not isinstance(phase2_result, Mapping) or not _phase2_shape_is_preserved(
        phase2_result
    ):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if phase2_result.get("persistent_record_created") is not False:
        return _base_report(False, "P2_PERSISTENT_RECORD_BOUNDARY_BREACH")
    if not _phase2_runtime_is_closed(phase2_result):
        return _base_report(False, "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH")
    if not _control_input_is_opaque(input_to_replay):
        return _base_report(False, "P2_CONTROL_REFERENCE_OPAQUENESS_BREACH")

    projection_records = {
        prefix: phase2_result[f"{prefix}_control_projections"]
        for prefix in P2_PROJECTION_PREFIXES
    }
    scenarios: list[dict[str, Any]] = []
    handlings: list[dict[str, Any]] = []
    for index, definition in enumerate(SCENARIO_DEFINITIONS):
        request = input_to_replay[P2_CONTROL_FIELDS[0]][index]
        workflow = projection_records["review_queue_schema_and_workflow"][index]
        audit = projection_records["review_audit"][index]
        writeback = projection_records["evidence_risk_and_report_status_writeback"][index]
        source_boundary = projection_records["human_reason_and_source_boundary"][index]
        failure = _failure_for_projection(
            definition, request, workflow, audit, writeback, source_boundary
        )
        if failure is not None:
            return _base_report(False, failure)
        scenario = _scenario_record(
            definition, workflow, audit, writeback, source_boundary
        )
        scenarios.append(scenario)
        handlings.append(_human_handling(definition, scenario))

    views = _control_views(scenarios)
    report = _base_report(True, None)
    report.update(
        {
            "phase2_control_shape_preserved": True,
            "phase2_side_effect_free": True,
            "control_references_opaque": True,
            "phase2_control_replay_request_count": P2_CONTROL_REQUEST_COUNT,
            "phase2_input_field_count": P2_INPUT_FIELD_COUNT,
            "phase2_phase1_reference_field_count": P2_PHASE1_REFERENCE_FIELD_COUNT,
            "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
            "phase2_projection_field_count_per_request": (
                P2_PROJECTION_FIELD_COUNT_PER_REQUEST
            ),
            "phase2_projection_field_check_count": P2_PROJECTION_FIELD_COUNT_TOTAL,
            "scenario_count": len(scenarios),
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "scenario_results": scenarios,
            "control_view_count": len(views),
            "control_views": views,
            "business_line_whitebox_handling_count": len(handlings),
            "business_line_whitebox_handlings": handlings,
            "whitebox_confirmation_required_scenario_count": len(handlings),
        }
    )
    return report
