"""Stage112 P3 报告导出审计的纯内存专项异常场景验证。

模块只重放 Stage112 P2 的固定、非业务、reference-only 控制投影。它验证关键
结论始终关联 evidence_id_ref 或 evidence_gap_ref，资料撤回、证据降级和索引版本
变化保持未来报告状态／质量／导出审计复核形状，外部增强保持来源分离并受业务线
白箱确认门禁约束。模块不读取真实资料、报告、PDF、证据账本或审计日志，不调用
模型、Agent、OVH 或生产服务，也不写入数据库、审计或持久化状态。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from . import stage112_report_export_audit_control_slice as phase2


SCHEMA_VERSION = "ids.stage112.report_export_audit.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT_SCENARIOS"
CURRENT_GATE = "IDS-STAGE112-P3-GATE"
NEXT_GATE = "IDS-STAGE112-P4-GATE"
PASS_RESULT = "PASS_REPORT_EXPORT_AUDIT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REPORT_EXPORT_AUDIT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

P2_SCHEMA_VERSION = "ids.stage112.report_export_audit.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EXPORT_AUDIT"
P2_EXECUTION_STATE = "PASS_IN_MEMORY_REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED"
P2_CONTROL_PREFIX = ":control:stage112-p2:"
P2_CONTROL_FIELDS = ("report_export_audit_control_requests",)
P2_CONTROL_REQUEST_COUNT = 5
P2_INPUT_FIELD_COUNT = 34
P2_PHASE1_REFERENCE_FIELD_COUNT = 32
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 100
P2_PROJECTION_FIELD_COUNT_TOTAL = 500
P2_CONTROL_SCENARIOS = (
    "report_export_audit_identity_reference_only",
    "source_withdrawal_reference_only",
    "evidence_downgrade_reference_only",
    "index_version_change_reference_only",
    "external_augmentation_whitebox_reference_only",
)
P2_PROJECTION_PREFIXES = (
    "report_export_audit_identity_and_binding",
    "generation_snapshot",
    "report_impact_quality_and_audit",
    "external_augmentation_and_whitebox_gate",
)

RUNTIME_CLOSED_FIELDS = (
    *phase2.RUNTIME_CLOSED_FIELDS,
    "phase2_control_slice_runtime_executed",
    "stage112_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_existing_audit_log_read_count",
    "actual_report_export_count",
    "actual_report_generation_count",
    "actual_snapshot_persistence_count",
    "actual_report_impact_analysis_count",
    "actual_report_quality_score_count",
    "actual_report_export_audit_write_count",
    "actual_report_status_update_count",
    "actual_report_regeneration_count",
    "actual_report_withdrawal_count",
    "actual_external_augmentation_display_count",
    "actual_human_confirmation_count",
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
    "report_snapshot_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "index_version_change_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_state_ref",
    "report_export_audit_failure_reason_ref",
    "report_export_audit_retention_ref",
    "report_regeneration_reference_ref",
    "report_withdrawal_reference_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
    "evidence_binding_integrity_state",
    "source_withdrawal_report_status_impact_state",
    "evidence_downgrade_report_status_impact_state",
    "index_version_change_report_status_impact_state",
    "external_augmentation_source_separation_state",
    "external_augmentation_may_not_be_internal_project_evidence",
    "external_augmentation_may_not_replace_evidence_binding",
    "external_augmentation_may_not_close_evidence_gap",
    "human_confirmation_state",
    "automatic_final_conclusion_allowed",
    "actual_report_status_impact_analysis_performed",
    "actual_report_status_updated",
    "actual_report_export_audit_updated",
    "actual_external_augmentation_displayed",
    "actual_human_confirmation_recorded",
    "actual_final_conclusion_published",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "export_audit_identity_and_evidence_binding_control_view": (
        "scenario_id",
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
        "evidence_binding_integrity_state",
    ),
    "report_and_generation_snapshot_control_view": (
        "scenario_id",
        "report_id_ref",
        "report_snapshot_ref",
        "data_snapshot_ref",
        "index_version_ref",
        "evidence_snapshot_ref",
        "model_snapshot_ref",
        "generated_at_ref",
    ),
    "report_status_quality_and_export_audit_control_view": (
        "scenario_id",
        "source_withdrawal_ref",
        "evidence_downgrade_ref",
        "index_version_change_ref",
        "impact_analysis_ref",
        "affected_report_ref",
        "report_status_impact_ref",
        "report_quality_score_ref",
        "report_export_audit_state_ref",
        "report_export_audit_failure_reason_ref",
        "report_export_audit_retention_ref",
        "report_regeneration_reference_ref",
        "report_withdrawal_reference_ref",
        "source_withdrawal_report_status_impact_state",
        "evidence_downgrade_report_status_impact_state",
        "index_version_change_report_status_impact_state",
    ),
    "external_augmentation_source_separation_control_view": (
        "scenario_id",
        "external_augmentation_opinion_section_ref",
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
        "human_confirmation_state",
        "automatic_final_conclusion_allowed",
        "actual_report_status_impact_analysis_performed",
        "actual_report_status_updated",
        "actual_report_export_audit_updated",
        "actual_external_augmentation_displayed",
        "actual_human_confirmation_recorded",
        "actual_final_conclusion_published",
        "expectation_met",
    ),
}

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "export_audit_identity_evidence_id_binding_control",
        "scenario_category": "EXPORT_AUDIT_IDENTITY_EVIDENCE_ID_BINDING_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EXPORT_AUDIT_IDENTITY_AND_EVIDENCE"
        ),
    },
    {
        "scenario_id": "source_withdrawal_evidence_gap_report_status_audit_control",
        "scenario_category": "SOURCE_WITHDRAWAL_REPORT_STATUS_AND_AUDIT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_binding_mode": "evidence_gap",
        "source_withdrawal_impact_required": True,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_SOURCE_WITHDRAWAL_REPORT_STATUS_AND_AUDIT"
        ),
    },
    {
        "scenario_id": "evidence_downgrade_evidence_id_report_status_quality_audit_control",
        "scenario_category": "EVIDENCE_DOWNGRADE_REPORT_STATUS_QUALITY_AND_AUDIT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": True,
        "index_version_change_impact_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_DOWNGRADE_REPORT_STATUS_AND_QUALITY"
        ),
    },
    {
        "scenario_id": "index_version_change_evidence_gap_report_snapshot_audit_control",
        "scenario_category": "INDEX_VERSION_CHANGE_REPORT_SNAPSHOT_AND_AUDIT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_binding_mode": "evidence_gap",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": True,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_INDEX_VERSION_REPORT_SNAPSHOT_AND_AUDIT"
        ),
    },
    {
        "scenario_id": "external_augmentation_source_separation_whitebox_control",
        "scenario_category": "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_WHITEBOX_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
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
    "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID",
    "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT",
    "REPORT_EXPORT_AUDIT_IDENTITY_OR_CITATION_CONTROL_MISSING",
    "GENERATION_SNAPSHOT_CONTROL_MISSING",
    "SOURCE_WITHDRAWAL_REPORT_STATUS_CONTROL_MISSING",
    "EVIDENCE_DOWNGRADE_REPORT_STATUS_CONTROL_MISSING",
    "INDEX_VERSION_CHANGE_REPORT_STATUS_CONTROL_MISSING",
    "REPORT_IMPACT_QUALITY_OR_AUDIT_CONTROL_MISSING",
    "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
    "BUSINESS_LINE_WHITEBOX_CONFIRMATION_GATE_MISSING",
    "AUTOMATIC_REPORT_OR_AUDIT_BOUNDARY_BREACH",
)

CHINESE_FEEDBACK = (
    "报告导出审计专项场景已验证，关键结论保持 evidence_id 或 evidence_gap 控制引用。",
    "资料撤回、证据降级和索引版本变化保持未来报告状态、质量和导出审计复核控制。",
    "外部增强保持外部来源身份，最终结论继续由业务线白箱人工确认门禁承接。",
    "真实报告导出、审计写入、数据库、模型、Agent、OVH、生产和正式上传保持未执行。",
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
            or any(not isinstance(record, Mapping) or set(record) != set(fields) for record in records)
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
        if request.get("binding_mode") not in {
            "CONTROL_BINDING_EVIDENCE_ID",
            "CONTROL_BINDING_EVIDENCE_GAP",
        }:
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


def _record_has_closed_runtime_flags(record: Mapping[str, Any]) -> bool:
    return all(
        value is False
        for key, value in record.items()
        if key.startswith("actual_") or key.startswith("automatic_")
    )


def _impact_state(required: bool, label: str) -> str:
    return (
        f"CONTROL_{label}_FUTURE_REPORT_STATUS_QUALITY_AND_AUDIT_REVIEW_REQUIRED"
        if required
        else f"CONTROL_{label}_NOT_APPLICABLE"
    )


def _failure_for_projection(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    identity: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    audit: Mapping[str, Any],
    external: Mapping[str, Any],
) -> Optional[str]:
    if request.get("control_scenario") != definition["phase2_control_scenario"]:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    binding_mode = _binding_mode(request)
    if binding_mode is None:
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID"
    if binding_mode != definition["expected_binding_mode"]:
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"
    if (
        identity.get("evidence_id_ref") != request.get("evidence_id_ref")
        or identity.get("evidence_gap_ref") != request.get("evidence_gap_ref")
    ):
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"
    if (
        definition["evidence_downgrade_impact_required"]
        and identity.get("evidence_grade_ref") != request.get("evidence_grade_ref")
    ):
        return "EVIDENCE_DOWNGRADE_REPORT_STATUS_CONTROL_MISSING"
    if any(
        identity.get(field) != request.get(field)
        for field in phase2.REPORT_EXPORT_AUDIT_IDENTITY_AND_BINDING_INPUT_FIELDS
    ):
        return "REPORT_EXPORT_AUDIT_IDENTITY_OR_CITATION_CONTROL_MISSING"
    if (
        definition["index_version_change_impact_required"]
        and snapshot.get("index_version_ref") != request.get("index_version_ref")
    ):
        return "INDEX_VERSION_CHANGE_REPORT_STATUS_CONTROL_MISSING"
    if any(
        snapshot.get(field) != request.get(field)
        for field in phase2.GENERATION_SNAPSHOT_INPUT_FIELDS
    ):
        return "GENERATION_SNAPSHOT_CONTROL_MISSING"
    if (
        definition["source_withdrawal_impact_required"]
        and audit.get("report_withdrawal_reference_ref")
        != request.get("report_withdrawal_reference_ref")
    ):
        return "SOURCE_WITHDRAWAL_REPORT_STATUS_CONTROL_MISSING"
    if any(
        audit.get(field) != request.get(field)
        for field in phase2.REPORT_IMPACT_QUALITY_AND_AUDIT_INPUT_FIELDS
    ):
        return "REPORT_IMPACT_QUALITY_OR_AUDIT_CONTROL_MISSING"
    if any(
        external.get(field) != request.get(field)
        for field in phase2.EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_INPUT_FIELDS
    ):
        return "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE"
    if not _all_control_references(
        identity,
        (
            "report_export_audit_record_ref",
            "actor_ref",
            "export_time_ref",
            "report_id_ref",
            "evidence_snapshot_ref",
            "report_evidence_binding_ref",
            "critical_conclusion_ref",
            "evidence_grade_ref",
            "citation_source_ref",
            "citation_page_ref",
        ),
    ) or identity.get("report_export_audit_identity_control_state") != (
        "CONTROL_ACTOR_TIME_REPORT_ID_EVIDENCE_SNAPSHOT_REFERENCE_ONLY_NOT_RECORDED"
    ) or identity.get("report_evidence_binding_control_state") != (
        "CONTROL_EVIDENCE_BINDING_REFERENCE_ONLY_NOT_WRITTEN"
    ) or identity.get("future_pdf_citation_control_state") != (
        "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED"
    ):
        return "REPORT_EXPORT_AUDIT_IDENTITY_OR_CITATION_CONTROL_MISSING"
    if not _all_control_references(
        snapshot,
        (
            "report_id_ref",
            "data_snapshot_ref",
            "index_version_ref",
            "evidence_snapshot_ref",
            "model_snapshot_ref",
            "generated_at_ref",
            "report_snapshot_ref",
        ),
    ) or snapshot.get("generation_snapshot_control_state") != (
        "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED"
    ):
        return "GENERATION_SNAPSHOT_CONTROL_MISSING"
    if definition["source_withdrawal_impact_required"] and (
        not _is_control_reference(audit.get("report_withdrawal_reference_ref"))
        or audit.get("report_withdrawal_control_state")
        != "CONTROL_REPORT_WITHDRAWAL_REFERENCE_ONLY_NOT_EXECUTED"
    ):
        return "SOURCE_WITHDRAWAL_REPORT_STATUS_CONTROL_MISSING"
    if definition["evidence_downgrade_impact_required"] and not _is_control_reference(
        identity.get("evidence_grade_ref")
    ):
        return "EVIDENCE_DOWNGRADE_REPORT_STATUS_CONTROL_MISSING"
    if definition["index_version_change_impact_required"] and not _is_control_reference(
        snapshot.get("index_version_ref")
    ):
        return "INDEX_VERSION_CHANGE_REPORT_STATUS_CONTROL_MISSING"
    if not _all_control_references(
        audit,
        (
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
            "report_export_audit_control_label",
        ),
    ) or any(
        "REFERENCE_ONLY" not in str(audit.get(field, ""))
        for field in (
            "report_impact_control_state",
            "report_quality_score_control_state",
            "report_export_audit_state_control_state",
            "report_export_audit_failure_reason_control_state",
            "report_export_audit_retention_control_state",
            "report_regeneration_control_state",
            "report_withdrawal_control_state",
        )
    ):
        return "REPORT_IMPACT_QUALITY_OR_AUDIT_CONTROL_MISSING"
    if (
        external.get("external_augmentation_representation_state")
        != "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE"
        or external.get("external_augmentation_may_not_be_internal_project_evidence")
        is not True
        or external.get("external_augmentation_may_not_replace_evidence_binding")
        is not True
        or external.get("external_augmentation_may_not_close_evidence_gap") is not True
    ):
        return "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE"
    if (
        external.get("business_line_whitebox_confirmation_required") is not True
        or external.get("human_confirmation_control_state")
        != "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
    ):
        return "BUSINESS_LINE_WHITEBOX_CONFIRMATION_GATE_MISSING"
    if not all(
        _record_has_closed_runtime_flags(record)
        for record in (identity, snapshot, audit, external)
    ):
        return "AUTOMATIC_REPORT_OR_AUDIT_BOUNDARY_BREACH"
    return None


def _scenario_record(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    external: Mapping[str, Any],
) -> dict[str, Any]:
    source_required = definition["source_withdrawal_impact_required"]
    downgrade_required = definition["evidence_downgrade_impact_required"]
    index_required = definition["index_version_change_impact_required"]
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": definition["phase2_control_scenario"],
        "report_export_audit_record_ref": request["report_export_audit_record_ref"],
        "actor_ref": request["actor_ref"],
        "export_time_ref": request["export_time_ref"],
        "report_id_ref": request["report_id_ref"],
        "evidence_snapshot_ref": request["evidence_snapshot_ref"],
        "report_evidence_binding_ref": request["report_evidence_binding_ref"],
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "citation_source_ref": request["citation_source_ref"],
        "citation_page_ref": request["citation_page_ref"],
        "report_snapshot_ref": request["report_snapshot_ref"],
        "data_snapshot_ref": request["data_snapshot_ref"],
        "index_version_ref": request["index_version_ref"],
        "model_snapshot_ref": request["model_snapshot_ref"],
        "generated_at_ref": request["generated_at_ref"],
        "source_withdrawal_ref": request["report_withdrawal_reference_ref"],
        "evidence_downgrade_ref": request["evidence_grade_ref"],
        "index_version_change_ref": request["index_version_ref"],
        "impact_analysis_ref": request["impact_analysis_ref"],
        "affected_report_ref": request["affected_report_ref"],
        "report_status_impact_ref": request["report_status_impact_ref"],
        "report_quality_score_ref": request["report_quality_score_ref"],
        "report_export_audit_state_ref": request["report_export_audit_state_ref"],
        "report_export_audit_failure_reason_ref": request[
            "report_export_audit_failure_reason_ref"
        ],
        "report_export_audit_retention_ref": request[
            "report_export_audit_retention_ref"
        ],
        "report_regeneration_reference_ref": request[
            "report_regeneration_reference_ref"
        ],
        "report_withdrawal_reference_ref": request["report_withdrawal_reference_ref"],
        "external_augmentation_opinion_section_ref": request[
            "external_augmentation_opinion_section_ref"
        ],
        "external_augmentation_underlying_source_type_ref": request[
            "external_augmentation_underlying_source_type_ref"
        ],
        "external_public_reference_control_label": external[
            "external_public_reference_control_label"
        ],
        "model_reasoning_control_label": external["model_reasoning_control_label"],
        "evidence_binding_integrity_state": (
            "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED"
        ),
        "source_withdrawal_report_status_impact_state": _impact_state(
            source_required, "SOURCE_WITHDRAWAL"
        ),
        "evidence_downgrade_report_status_impact_state": _impact_state(
            downgrade_required, "EVIDENCE_DOWNGRADE"
        ),
        "index_version_change_report_status_impact_state": _impact_state(
            index_required, "INDEX_VERSION_CHANGE"
        ),
        "external_augmentation_source_separation_state": external[
            "external_augmentation_representation_state"
        ],
        "external_augmentation_may_not_be_internal_project_evidence": external[
            "external_augmentation_may_not_be_internal_project_evidence"
        ],
        "external_augmentation_may_not_replace_evidence_binding": external[
            "external_augmentation_may_not_replace_evidence_binding"
        ],
        "external_augmentation_may_not_close_evidence_gap": external[
            "external_augmentation_may_not_close_evidence_gap"
        ],
        "human_confirmation_state": (
            "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
        ),
        "automatic_final_conclusion_allowed": False,
        "actual_report_status_impact_analysis_performed": False,
        "actual_report_status_updated": False,
        "actual_report_export_audit_updated": False,
        "actual_external_augmentation_displayed": False,
        "actual_human_confirmation_recorded": False,
        "actual_final_conclusion_published": False,
        "expectation_met": True,
    }


def _human_handling(
    definition: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "business_line_whitebox_handling_code": definition[
            "business_line_whitebox_handling_code"
        ],
        "whitebox_confirmation_required": True,
        "human_confirmation_recorded": False,
        "final_conclusion_state": "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
        "report_id_ref": scenario["report_id_ref"],
    }


def _control_views(scenarios: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        name: [{field: scenario[field] for field in fields} for scenario in scenarios]
        for name, fields in CONTROL_VIEW_FIELDS.items()
    }


def build_report_export_audit_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """机械重放 P2 控制投影，并将所有漂移关闭为零运行时失败报告。"""

    control_input = phase2.build_control_input()
    executor = phase2_executor or phase2.execute_report_export_audit_control_slice
    try:
        phase2_result = executor(control_input)
    except Exception:
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if not isinstance(phase2_result, Mapping) or not _phase2_shape_is_preserved(
        phase2_result
    ):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if phase2_result.get("persistent_record_created") is not False:
        return _base_report(False, "P2_PERSISTENT_RECORD_BOUNDARY_BREACH")
    if not _phase2_runtime_is_closed(phase2_result):
        return _base_report(False, "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH")
    if not _control_input_is_opaque(control_input):
        return _base_report(False, "P2_CONTROL_REFERENCE_OPAQUENESS_BREACH")

    requests = control_input[P2_CONTROL_FIELDS[0]]
    projections = {
        prefix: phase2_result[f"{prefix}_control_projections"]
        for prefix in P2_PROJECTION_PREFIXES
    }
    scenarios: list[dict[str, Any]] = []
    handlings: list[dict[str, Any]] = []
    for index, definition in enumerate(SCENARIO_DEFINITIONS):
        request = requests[index]
        identity = projections["report_export_audit_identity_and_binding"][index]
        snapshot = projections["generation_snapshot"][index]
        audit = projections["report_impact_quality_and_audit"][index]
        external = projections["external_augmentation_and_whitebox_gate"][index]
        failure = _failure_for_projection(
            definition, request, identity, snapshot, audit, external
        )
        if failure is not None:
            return _base_report(False, failure)
        scenario = _scenario_record(definition, request, external)
        if set(scenario) != set(SCENARIO_FIELDS):
            return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
        scenarios.append(scenario)
        handlings.append(_human_handling(definition, scenario))

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
            "control_view_count": len(CONTROL_VIEW_FIELDS),
            "control_views": _control_views(scenarios),
            "business_line_whitebox_handling_count": len(handlings),
            "business_line_whitebox_handlings": handlings,
            "whitebox_confirmation_required_scenario_count": len(handlings),
        }
    )
    return report
