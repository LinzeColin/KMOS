"""Stage111 P2 报告重新生成队列的纯内存受控最小切片。

模块只机械投影冻结控制引用。它不读取业务资料、外部参考、证据账本、报告或 PDF，
不保存快照、不写导出审计、不创建队列、不连接数据库、外部服务、模型或 OVH。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage111.report_regeneration_queue.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_REGENERATION_QUEUE"
CONTROL_ADAPTER_VERSION = "stage111-p2-control-slice-v1"
PASS_RESULT = "PASS_IN_MEMORY_REPORT_REGENERATION_QUEUE_CONTROL_SLICE_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_REPORT_REGENERATION_QUEUE_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage111-p2:"
CONTROL_FIELDS = ("report_regeneration_queue_control_requests",)

CONTROL_SCENARIOS = (
    "cited_material_update_reference_only",
    "source_withdrawal_reference_only",
    "evidence_downgrade_reference_only",
    "evidence_conflict_reference_only",
    "index_version_change_reference_only",
)

CONTROL_SCENARIO_CONFIGURATION = {
    "cited_material_update_reference_only": {"binding_mode": "evidence_id"},
    "source_withdrawal_reference_only": {"binding_mode": "evidence_gap"},
    "evidence_downgrade_reference_only": {"binding_mode": "evidence_id"},
    "evidence_conflict_reference_only": {"binding_mode": "evidence_gap"},
    "index_version_change_reference_only": {"binding_mode": "evidence_id"},
}

PHASE1_CONTROL_REFERENCE_FIELDS = (
    "report_id_ref",
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
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "cited_material_update_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "evidence_conflict_ref",
    "index_version_change_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_regeneration_queue_entry_ref",
    "report_regeneration_reason_ref",
    "report_regeneration_queue_state_ref",
)

INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    *PHASE1_CONTROL_REFERENCE_FIELDS,
)

REPORT_EVIDENCE_BINDING_AND_SECTION_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_id_ref",
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
)

REPORT_EVIDENCE_BINDING_AND_SECTION_STATES = {
    "report_evidence_binding_control_state": (
        "CONTROL_EVIDENCE_BINDING_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "report_section_output_control_state": (
        "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED"
    ),
    "report_write_field_control_state": (
        "CONTROL_REPORT_FIELDS_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "future_pdf_citation_control_state": (
        "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED"
    ),
    "actual_report_evidence_binding_performed": False,
    "actual_report_section_output_performed": False,
    "actual_report_write_performed": False,
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

REPORT_IMPACT_QUEUE_AND_AUDIT_INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    "report_id_ref",
    "report_snapshot_ref",
    "cited_material_update_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "evidence_conflict_ref",
    "index_version_change_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_regeneration_queue_entry_ref",
    "report_regeneration_reason_ref",
    "report_regeneration_queue_state_ref",
)

REPORT_IMPACT_QUEUE_AND_AUDIT_DYNAMIC_FIELDS = (
    "report_export_audit_control_label",
)

REPORT_IMPACT_QUEUE_AND_AUDIT_STATES = {
    "report_impact_control_state": "CONTROL_REPORT_IMPACT_REFERENCE_ONLY_NOT_ANALYZED",
    "report_quality_score_control_state": (
        "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED"
    ),
    "report_export_audit_control_state": (
        "CONTROL_REPORT_EXPORT_AUDIT_REFERENCE_ONLY_NOT_WRITTEN"
    ),
    "report_regeneration_queue_entry_control_state": (
        "CONTROL_REPORT_REGENERATION_QUEUE_ENTRY_REFERENCE_ONLY_NOT_CREATED"
    ),
    "report_regeneration_reason_control_state": (
        "CONTROL_REPORT_REGENERATION_REASON_REFERENCE_ONLY_NOT_EVALUATED"
    ),
    "report_regeneration_queue_state_control_state": (
        "CONTROL_REPORT_REGENERATION_QUEUE_STATE_REFERENCE_ONLY_NOT_UPDATED"
    ),
    "automatic_report_status_update_allowed": False,
    "automatic_report_quality_score_allowed": False,
    "automatic_report_export_audit_write_allowed": False,
    "automatic_report_regeneration_queue_execution_allowed": False,
    "actual_report_impact_analysis_performed": False,
    "actual_report_quality_score_calculated": False,
    "actual_report_export_audit_written": False,
    "actual_queue_entry_created": False,
    "actual_report_status_updated": False,
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
    "business_line_whitebox_confirmation_required": True,
    "automatic_human_confirmation_allowed": False,
    "automatic_final_conclusion_allowed": False,
    "actual_external_augmentation_displayed": False,
    "actual_human_confirmation_recorded": False,
    "actual_final_conclusion_published": False,
}

PROJECTION_SPECS = (
    (
        "report_evidence_binding_and_section",
        REPORT_EVIDENCE_BINDING_AND_SECTION_INPUT_FIELDS,
        REPORT_EVIDENCE_BINDING_AND_SECTION_STATES,
    ),
    (
        "generation_snapshot",
        GENERATION_SNAPSHOT_INPUT_FIELDS,
        GENERATION_SNAPSHOT_STATES,
    ),
    (
        "report_impact_queue_and_audit",
        REPORT_IMPACT_QUEUE_AND_AUDIT_INPUT_FIELDS,
        REPORT_IMPACT_QUEUE_AND_AUDIT_STATES,
    ),
    (
        "external_augmentation_and_whitebox_gate",
        EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_INPUT_FIELDS,
        EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_STATES,
    ),
)

PROJECTION_FIELDS = (
    (
        "report_evidence_binding_and_section",
        (
            *REPORT_EVIDENCE_BINDING_AND_SECTION_INPUT_FIELDS,
            *REPORT_EVIDENCE_BINDING_AND_SECTION_STATES,
        ),
    ),
    (
        "generation_snapshot",
        (
            *GENERATION_SNAPSHOT_INPUT_FIELDS,
            *GENERATION_SNAPSHOT_STATES,
        ),
    ),
    (
        "report_impact_queue_and_audit",
        (
            *REPORT_IMPACT_QUEUE_AND_AUDIT_INPUT_FIELDS,
            *REPORT_IMPACT_QUEUE_AND_AUDIT_DYNAMIC_FIELDS,
            *REPORT_IMPACT_QUEUE_AND_AUDIT_STATES,
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
    "report_evidence_binding_performed",
    "report_section_output_performed",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "snapshot_persistence_performed",
    "report_status_impact_analysis_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_queue_execution_performed",
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
    """返回唯一允许的五条 Stage111 P2 非业务控制请求。"""

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
        "actual_report_evidence_binding_count": 0,
        "actual_report_section_output_count": 0,
        "actual_report_write_count": 0,
        "actual_snapshot_persistence_count": 0,
        "actual_report_impact_analysis_count": 0,
        "actual_report_quality_score_count": 0,
        "actual_report_export_audit_write_count": 0,
        "actual_queue_entry_creation_count": 0,
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
        if prefix == "report_impact_queue_and_audit":
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


def execute_report_regeneration_queue_control_slice(
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
