"""Stage112 P2 报告导出审计的纯内存受控最小切片。

模块只机械投影冻结控制引用。它不读取业务资料、外部参考、证据账本、报告、PDF 或
既有审计日志，不保存快照、不写导出审计、不连接数据库、外部服务、模型或 OVH。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage112.report_export_audit.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT"
CONTROL_ADAPTER_VERSION = "stage112-p2-control-slice-v1"
PASS_RESULT = "PASS_IN_MEMORY_REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_REPORT_EXPORT_AUDIT_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage112-p2:"
CONTROL_FIELDS = ("report_export_audit_control_requests",)

CONTROL_SCENARIOS = (
    "report_export_audit_identity_reference_only",
    "source_withdrawal_reference_only",
    "evidence_downgrade_reference_only",
    "index_version_change_reference_only",
    "external_augmentation_whitebox_reference_only",
)

CONTROL_SCENARIO_CONFIGURATION = {
    "report_export_audit_identity_reference_only": {"binding_mode": "evidence_id"},
    "source_withdrawal_reference_only": {"binding_mode": "evidence_gap"},
    "evidence_downgrade_reference_only": {"binding_mode": "evidence_id"},
    "index_version_change_reference_only": {"binding_mode": "evidence_gap"},
    "external_augmentation_whitebox_reference_only": {"binding_mode": "evidence_id"},
}

PHASE1_CONTROL_REFERENCE_FIELDS = (
    "report_export_audit_record_ref",
    "actor_ref",
    "export_time_ref",
    "report_id_ref",
    "evidence_snapshot_ref",
    "report_evidence_binding_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "export_destination_control_ref",
    "export_format_control_ref",
    "report_export_audit_state_ref",
    "report_export_audit_failure_reason_ref",
    "report_export_audit_retention_ref",
    "report_regeneration_reference_ref",
    "report_withdrawal_reference_ref",
)

INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    *PHASE1_CONTROL_REFERENCE_FIELDS,
)

REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_export_audit_record_ref",
    "actor_ref",
    "export_time_ref",
    "report_id_ref",
    "evidence_snapshot_ref",
    "report_evidence_binding_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "export_destination_control_ref",
    "export_format_control_ref",
)

REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_STATES = {
    "report_export_audit_identity_control_state": (
        "CONTROL_ACTOR_TIME_REPORT_ID_EVIDENCE_SNAPSHOT_REFERENCE_ONLY_NOT_RECORDED"
    ),
    "report_evidence_binding_control_state": (
        "CONTROL_EVIDENCE_BINDING_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "report_section_output_control_state": (
        "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED"
    ),
    "report_export_destination_and_format_control_state": (
        "CONTROL_EXPORT_DESTINATION_AND_FORMAT_REFERENCE_ONLY_NOT_APPLIED"
    ),
    "future_pdf_citation_control_state": (
        "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED"
    ),
    "automatic_report_write_allowed": False,
    "automatic_report_export_allowed": False,
    "actual_actor_time_report_id_evidence_snapshot_recorded": False,
    "actual_report_evidence_binding_performed": False,
    "actual_report_section_output_performed": False,
    "actual_pdf_citation_rendered": False,
}

GENERATION_SNAPSHOT_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_id_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "report_snapshot_ref",
)

GENERATION_SNAPSHOT_STATES = {
    "generation_snapshot_control_state": (
        "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED"
    ),
    "actual_generation_snapshot_persisted": False,
}

REPORT_IMPACT_QUALITY_AND_AUDIT_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_export_audit_record_ref",
    "report_id_ref",
    "evidence_snapshot_ref",
    "report_snapshot_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_state_ref",
    "report_export_audit_failure_reason_ref",
    "report_export_audit_retention_ref",
    "report_regeneration_reference_ref",
    "report_withdrawal_reference_ref",
)

REPORT_IMPACT_QUALITY_AND_AUDIT_DYNAMIC_FIELDS = (
    "report_export_audit_control_label",
)

REPORT_IMPACT_QUALITY_AND_AUDIT_STATES = {
    "report_impact_control_state": "CONTROL_REPORT_IMPACT_REFERENCE_ONLY_NOT_ANALYZED",
    "report_quality_score_control_state": (
        "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED"
    ),
    "report_export_audit_state_control_state": (
        "CONTROL_REPORT_EXPORT_AUDIT_STATE_REFERENCE_ONLY_NOT_UPDATED"
    ),
    "report_export_audit_failure_reason_control_state": (
        "CONTROL_REPORT_EXPORT_AUDIT_FAILURE_REASON_REFERENCE_ONLY_NOT_RECORDED"
    ),
    "report_export_audit_retention_control_state": (
        "CONTROL_REPORT_EXPORT_AUDIT_RETENTION_REFERENCE_ONLY_NOT_RECORDED"
    ),
    "report_regeneration_control_state": (
        "CONTROL_REPORT_REGENERATION_REFERENCE_ONLY_NOT_EXECUTED"
    ),
    "report_withdrawal_control_state": (
        "CONTROL_REPORT_WITHDRAWAL_REFERENCE_ONLY_NOT_EXECUTED"
    ),
    "automatic_report_status_impact_update_allowed": False,
    "automatic_report_quality_score_allowed": False,
    "automatic_report_export_audit_write_allowed": False,
    "automatic_report_regeneration_allowed": False,
    "automatic_report_withdrawal_allowed": False,
    "actual_report_impact_analysis_performed": False,
    "actual_report_quality_score_calculated": False,
    "actual_report_export_audit_written": False,
    "actual_report_export_audit_state_updated": False,
    "actual_report_export_audit_failure_recorded": False,
    "actual_report_export_audit_retention_recorded": False,
    "actual_report_regeneration_performed": False,
    "actual_report_withdrawal_performed": False,
}

EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_id_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
)

EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_DYNAMIC_FIELDS = (
    "external_public_reference_control_label",
    "model_reasoning_control_label",
)

EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_STATES = {
    "external_augmentation_representation_state": (
        "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
        "SEPARATE_FROM_INTERNAL_EVIDENCE"
    ),
    "external_augmentation_may_not_be_internal_project_evidence": True,
    "external_augmentation_may_not_replace_evidence_binding": True,
    "external_augmentation_may_not_close_evidence_gap": True,
    "human_confirmation_control_state": (
        "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
    ),
    "business_line_whitebox_confirmation_required": True,
    "automatic_human_confirmation_allowed": False,
    "automatic_final_conclusion_allowed": False,
    "actual_external_augmentation_displayed": False,
    "actual_human_confirmation_recorded": False,
    "actual_final_conclusion_published": False,
}

PROJECTION_SPECS = (
    (
        "report_export_audit_identity_and_binding",
        REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_INPUT_FIELDS,
        REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_STATES,
    ),
    (
        "generation_snapshot",
        GENERATION_SNAPSHOT_INPUT_FIELDS,
        GENERATION_SNAPSHOT_STATES,
    ),
    (
        "report_impact_quality_and_audit",
        REPORT_IMPACT_QUALITY_AND_AUDIT_INPUT_FIELDS,
        REPORT_IMPACT_QUALITY_AND_AUDIT_STATES,
    ),
    (
        "external_augmentation_and_whitebox_gate",
        EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_INPUT_FIELDS,
        EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_STATES,
    ),
)

PROJECTION_FIELDS = (
    (
        "report_export_audit_identity_and_binding",
        (
            *REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_INPUT_FIELDS,
            *REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_STATES,
        ),
    ),
    (
        "generation_snapshot",
        (*GENERATION_SNAPSHOT_INPUT_FIELDS, *GENERATION_SNAPSHOT_STATES),
    ),
    (
        "report_impact_quality_and_audit",
        (
            *REPORT_IMPACT_QUALITY_AND_AUDIT_INPUT_FIELDS,
            *REPORT_IMPACT_QUALITY_AND_AUDIT_DYNAMIC_FIELDS,
            *REPORT_IMPACT_QUALITY_AND_AUDIT_STATES,
        ),
    ),
    (
        "external_augmentation_and_whitebox_gate",
        (
            *EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_INPUT_FIELDS,
            *EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_DYNAMIC_FIELDS,
            *EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_STATES,
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
    "report_export_performed",
    "report_evidence_binding_performed",
    "report_section_output_performed",
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
)


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造固定控制请求，不包含业务事实或可执行运行时输入。"""

    binding_mode = CONTROL_SCENARIO_CONFIGURATION[scenario]["binding_mode"]
    request: dict[str, Optional[str]] = {
        "control_scenario": scenario,
        "binding_mode": f"CONTROL_BINDING_{binding_mode.upper()}",
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
    """返回唯一允许的五条 Stage112 P2 非业务控制请求。"""

    return {
        CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]
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
        "actual_evidence_ledger_write_count": 0,
        "actual_existing_audit_log_read_count": 0,
        "actual_report_export_count": 0,
        "actual_report_evidence_binding_count": 0,
        "actual_report_section_output_count": 0,
        "actual_report_generation_count": 0,
        "actual_pdf_generation_count": 0,
        "actual_citation_generation_count": 0,
        "actual_snapshot_persistence_count": 0,
        "actual_report_impact_analysis_count": 0,
        "actual_report_quality_score_count": 0,
        "actual_report_export_audit_write_count": 0,
        "actual_report_regeneration_count": 0,
        "actual_report_withdrawal_count": 0,
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
        if prefix == "report_impact_quality_and_audit":
            record["report_export_audit_control_label"] = _control_ref(
                "report-export-audit", scenario
            )
        if prefix == "external_augmentation_and_whitebox_gate":
            record.update(
                {
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


def execute_report_export_audit_control_slice(
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
