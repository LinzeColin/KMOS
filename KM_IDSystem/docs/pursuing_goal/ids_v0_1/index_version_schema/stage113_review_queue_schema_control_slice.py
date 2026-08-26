"""Stage113 P2 复核队列 Schema 的纯内存受控最小切片。

模块只机械投影冻结控制引用。它不读取业务资料、外部参考、证据账本、报告或审计日志，
不创建队列、不执行 schema migration、不渲染 UI、不写复核审计或证据／报告状态，
也不连接数据库、外部服务、模型或 OVH。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage113.review_queue_schema.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_QUEUE_SCHEMA"
CONTROL_ADAPTER_VERSION = "stage113-p2-control-slice-v1"
PASS_RESULT = "PASS_IN_MEMORY_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage113-p2:"
CONTROL_FIELDS = ("review_queue_schema_control_requests",)

CONTROL_SCENARIOS = (
    "low_ocr_pending_review_reference_only",
    "source_conflict_confirmed_reference_only",
    "parsing_failure_needs_more_material_reference_only",
    "evidence_risk_rejected_reference_only",
    "external_augmentation_archived_reference_only",
)

FIXED_REVIEW_STATUSES = (
    "pending_review",
    "confirmed",
    "rejected",
    "needs_more_material",
    "archived",
)

CONTROL_SCENARIO_CONFIGURATION = {
    "low_ocr_pending_review_reference_only": {
        "binding_mode": "evidence_id",
        "fixed_review_status": "pending_review",
    },
    "source_conflict_confirmed_reference_only": {
        "binding_mode": "evidence_gap",
        "fixed_review_status": "confirmed",
    },
    "parsing_failure_needs_more_material_reference_only": {
        "binding_mode": "evidence_gap",
        "fixed_review_status": "needs_more_material",
    },
    "evidence_risk_rejected_reference_only": {
        "binding_mode": "evidence_id",
        "fixed_review_status": "rejected",
    },
    "external_augmentation_archived_reference_only": {
        "binding_mode": "evidence_id",
        "fixed_review_status": "archived",
    },
}

HUMAN_REASON_MESSAGES = {
    "low_ocr_pending_review_reference_only": (
        "低 OCR 置信度：需业务线白箱复核后确认，当前仅为控制投影。"
    ),
    "source_conflict_confirmed_reference_only": (
        "资料冲突：需保留来源与差异说明后由业务线白箱复核，当前仅为控制投影。"
    ),
    "parsing_failure_needs_more_material_reference_only": (
        "解析失败：需补充可复核资料后再判断，当前仅为控制投影。"
    ),
    "evidence_risk_rejected_reference_only": (
        "证据风险：需复核证据风险与报告影响后再形成业务结论，当前仅为控制投影。"
    ),
    "external_augmentation_archived_reference_only": (
        "外部增强：保持外部来源身份，不能替代内部证据或绕过白箱确认。"
    ),
}

PHASE1_CONTROL_REFERENCE_FIELDS = (
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
    "review_actor_ref",
    "review_time_ref",
    "review_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "re_review_reference_ref",
    "archive_reference_ref",
    "review_audit_record_ref",
)

INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "fixed_review_status_control_value",
    *PHASE1_CONTROL_REFERENCE_FIELDS,
)

REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "fixed_review_status_control_value",
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
)

REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_STATES = {
    "review_queue_schema_control_state": (
        "CONTROL_REVIEW_QUEUE_SCHEMA_REFERENCE_ONLY_NOT_MIGRATED"
    ),
    "review_workflow_control_state": (
        "CONTROL_REVIEW_WORKFLOW_REFERENCE_ONLY_NOT_EXECUTED"
    ),
    "fixed_review_status_catalog": FIXED_REVIEW_STATUSES,
    "review_queue_entry_control_state": (
        "CONTROL_REVIEW_QUEUE_ENTRY_REFERENCE_ONLY_NOT_CREATED"
    ),
    "automatic_review_queue_schema_migration_allowed": False,
    "automatic_review_queue_entry_allowed": False,
    "automatic_review_status_transition_allowed": False,
    "actual_review_queue_schema_migration_performed": False,
    "actual_review_queue_entry_created": False,
    "actual_review_status_transition_performed": False,
}

REVIEW_AUDIT_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "fixed_review_status_control_value",
    "review_queue_item_ref",
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
)

REVIEW_AUDIT_STATES = {
    "review_audit_control_state": (
        "CONTROL_REVIEW_AUDIT_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "review_result_control_state": (
        "CONTROL_REVIEW_RESULT_REFERENCE_ONLY_NOT_APPLIED"
    ),
    "automatic_review_audit_write_allowed": False,
    "automatic_human_confirmation_allowed": False,
    "actual_review_audit_written": False,
    "actual_actor_time_reason_old_new_recorded": False,
    "actual_human_confirmation_recorded": False,
}

EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "fixed_review_status_control_value",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_risk_ref",
    "evidence_trust_level_before_ref",
    "evidence_trust_level_after_ref",
    "report_quality_score_before_ref",
    "report_quality_score_after_ref",
    "report_status_impact_ref",
    "review_result_ref",
    "review_audit_record_ref",
    "business_line_whitebox_confirmation_gate_ref",
)

EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_DYNAMIC_FIELDS = (
    "review_queue_writeback_control_label",
)

EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_STATES = {
    "evidence_risk_writeback_control_state": (
        "CONTROL_EVIDENCE_RISK_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "evidence_trust_level_control_state": (
        "CONTROL_EVIDENCE_TRUST_LEVEL_REFERENCE_ONLY_NOT_CHANGED"
    ),
    "report_quality_score_control_state": (
        "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CHANGED"
    ),
    "report_status_writeback_control_state": (
        "CONTROL_REPORT_STATUS_REFERENCE_ONLY_NOT_UPDATED"
    ),
    "automatic_evidence_risk_writeback_allowed": False,
    "automatic_evidence_trust_level_change_allowed": False,
    "automatic_report_quality_score_change_allowed": False,
    "automatic_report_status_change_allowed": False,
    "actual_evidence_risk_writeback_performed": False,
    "actual_evidence_trust_level_changed": False,
    "actual_report_quality_score_changed": False,
    "actual_report_status_changed": False,
}

HUMAN_REASON_AND_SOURCE_BOUNDARY_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "fixed_review_status_control_value",
    "review_queue_entry_reason_ref",
    "review_trigger_type_ref",
    "review_reason_ref",
    "external_augmentation_underlying_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
)

HUMAN_REASON_AND_SOURCE_BOUNDARY_DYNAMIC_FIELDS = (
    "review_reason_chinese_control_message",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
)

HUMAN_REASON_AND_SOURCE_BOUNDARY_STATES = {
    "human_readable_review_reason_control_state": (
        "CONTROL_CHINESE_REVIEW_REASON_REFERENCE_ONLY_NOT_DELIVERED"
    ),
    "external_augmentation_representation_state": (
        "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
        "SEPARATE_FROM_INTERNAL_EVIDENCE"
    ),
    "external_augmentation_may_not_be_internal_project_evidence": True,
    "external_augmentation_may_not_replace_evidence_binding": True,
    "external_augmentation_may_not_close_evidence_gap": True,
    "business_line_whitebox_confirmation_required": True,
    "automatic_user_feedback_delivery_allowed": False,
    "automatic_human_confirmation_allowed": False,
    "automatic_final_conclusion_allowed": False,
    "actual_review_ui_rendered": False,
    "actual_external_augmentation_displayed": False,
    "actual_human_confirmation_recorded": False,
    "actual_final_conclusion_published": False,
}

PROJECTION_SPECS = (
    (
        "review_queue_schema_and_workflow",
        REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_INPUT_FIELDS,
        REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_STATES,
    ),
    ("review_audit", REVIEW_AUDIT_INPUT_FIELDS, REVIEW_AUDIT_STATES),
    (
        "evidence_risk_and_report_status_writeback",
        EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_INPUT_FIELDS,
        EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_STATES,
    ),
    (
        "human_reason_and_source_boundary",
        HUMAN_REASON_AND_SOURCE_BOUNDARY_INPUT_FIELDS,
        HUMAN_REASON_AND_SOURCE_BOUNDARY_STATES,
    ),
)

PROJECTION_FIELDS = (
    (
        "review_queue_schema_and_workflow",
        (
            *REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_INPUT_FIELDS,
            *REVIEW_QUEUE_SCHEMA_AND_WORKFLOW_STATES,
        ),
    ),
    ("review_audit", (*REVIEW_AUDIT_INPUT_FIELDS, *REVIEW_AUDIT_STATES)),
    (
        "evidence_risk_and_report_status_writeback",
        (
            *EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_INPUT_FIELDS,
            *EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_DYNAMIC_FIELDS,
            *EVIDENCE_RISK_AND_REPORT_STATUS_WRITEBACK_STATES,
        ),
    ),
    (
        "human_reason_and_source_boundary",
        (
            *HUMAN_REASON_AND_SOURCE_BOUNDARY_INPUT_FIELDS,
            *HUMAN_REASON_AND_SOURCE_BOUNDARY_DYNAMIC_FIELDS,
            *HUMAN_REASON_AND_SOURCE_BOUNDARY_STATES,
        ),
    ),
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
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造固定控制请求，不包含业务事实或可执行运行时输入。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    binding_mode = configuration["binding_mode"]
    request: dict[str, Optional[str]] = {
        "control_scenario": scenario,
        "binding_mode": f"CONTROL_BINDING_{binding_mode.upper()}",
        "fixed_review_status_control_value": configuration["fixed_review_status"],
    }
    for field in PHASE1_CONTROL_REFERENCE_FIELDS:
        kind = field.removesuffix("_ref").replace("_", "-")
        request[field] = _control_ref(kind, scenario)
    request["evidence_id_ref"] = (
        _control_ref("evidence-id", scenario)
        if binding_mode == "evidence_id"
        else None
    )
    request["evidence_gap_ref"] = (
        _control_ref("evidence-gap", scenario)
        if binding_mode == "evidence_gap"
        else None
    )
    return request


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的五条 Stage113 P2 非业务控制请求。"""

    return {
        CONTROL_FIELDS[0]: [
            _control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {
        "actual_control_projection_execution_count": 0,
        "actual_business_source_read_count": 0,
        "actual_external_reference_read_count": 0,
        "actual_report_or_pdf_read_count": 0,
        "actual_evidence_ledger_read_count": 0,
        "actual_existing_audit_log_read_count": 0,
        "actual_review_queue_schema_migration_count": 0,
        "actual_review_queue_entry_count": 0,
        "actual_review_status_transition_count": 0,
        "actual_review_audit_write_count": 0,
        "actual_evidence_risk_writeback_count": 0,
        "actual_evidence_trust_level_change_count": 0,
        "actual_report_quality_score_change_count": 0,
        "actual_report_status_update_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_database_connection_count": 0,
        "actual_audit_log_write_count": 0,
        "actual_persistent_state_write_count": 0,
        "actual_model_call_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
    }


def _empty_projection_result() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prefix, _fields in PROJECTION_FIELDS:
        result[f"{prefix}_control_projections"] = []
        result[f"{prefix}_control_projection_count"] = 0
    return result


def _rejected_result() -> dict[str, Any]:
    """输入漂移保持拒绝状态，并且不产生控制投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": REJECTED_RESULT,
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": 0,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _project(request: Mapping[str, Optional[str]]) -> dict[str, dict[str, Any]]:
    scenario = str(request["control_scenario"])
    projections: dict[str, dict[str, Any]] = {}
    for prefix, input_fields, state_values in PROJECTION_SPECS:
        record: dict[str, Any] = {field: request[field] for field in input_fields}
        if prefix == "evidence_risk_and_report_status_writeback":
            record["review_queue_writeback_control_label"] = _control_ref(
                "review-queue-writeback", scenario
            )
        if prefix == "human_reason_and_source_boundary":
            record.update(
                {
                    "review_reason_chinese_control_message": HUMAN_REASON_MESSAGES[
                        scenario
                    ],
                    "external_public_reference_control_label": _control_ref(
                        "external-public-reference", scenario
                    ),
                    "model_reasoning_control_label": _control_ref(
                        "model-reasoning", scenario
                    ),
                }
            )
        record.update(state_values)
        projections[prefix] = record
    return projections


def execute_review_queue_schema_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """机械投影固定控制输入；输入漂移返回零运行时拒绝结果。"""

    if control_input != build_control_input():
        return _rejected_result()

    projections = [_project(request) for request in control_input[CONTROL_FIELDS[0]]]
    field_total_per_request = sum(len(fields) for _prefix, fields in PROJECTION_FIELDS)
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": PASS_RESULT,
        "failure_state": None,
        "control_input_count": len(projections),
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": field_total_per_request,
        "control_projection_field_total": len(projections) * field_total_per_request,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
    }
    for prefix, _fields in PROJECTION_FIELDS:
        records = [projection[prefix] for projection in projections]
        result[f"{prefix}_control_projections"] = records
        result[f"{prefix}_control_projection_count"] = len(records)
    return result
