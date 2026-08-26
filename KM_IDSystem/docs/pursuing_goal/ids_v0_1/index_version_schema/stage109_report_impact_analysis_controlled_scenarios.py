"""Stage109 P3：报告影响分析的纯内存专项场景验证。

模块只重放 Stage109 P2 的固定、非业务、reference-only 控制投影。它验证关键
结论始终关联 evidence_id_ref 或 evidence_gap_ref，资料撤回、证据降级和索引
版本变化保持未来报告状态复核形状，外部增强保持来源分离并受业务线白箱确认门禁
约束。模块不读取真实资料、报告、PDF 或证据账本，不调用模型、Agent、OVH 或
生产服务，也不写入数据库、审计或持久化状态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = "ids.stage109.report_impact_analysis.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_IMPACT_ANALYSIS_SCENARIOS"
CURRENT_GATE = "IDS-STAGE109-P3-GATE"
NEXT_GATE = "IDS-STAGE109-P4-GATE"
PASS_RESULT = "PASS_REPORT_IMPACT_ANALYSIS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REPORT_IMPACT_ANALYSIS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

P2_SCHEMA_VERSION = "ids.stage109.report_impact_analysis.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_IMPACT_ANALYSIS"
P2_EXECUTION_STATE = (
    "PASS_IN_MEMORY_REPORT_IMPACT_ANALYSIS_CONTROL_SLICE_RUNTIME_DISABLED"
)
P2_CONTROL_PREFIX = ":control:stage109-p2:"
P2_CONTROL_FIELDS = ("report_impact_analysis_control_requests",)
P2_CONTROL_REQUEST_COUNT = 5
P2_INPUT_FIELD_COUNT = 35
P2_PHASE1_REFERENCE_FIELD_COUNT = 33
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 101
P2_PROJECTION_FIELD_COUNT_TOTAL = 505
P2_CONTROL_SCENARIOS = (
    "cited_material_update_reference_only",
    "source_withdrawal_reference_only",
    "evidence_downgrade_reference_only",
    "index_version_change_reference_only",
    "affected_report_impact_lifecycle_reference_only",
)
P2_PROJECTION_PREFIXES = (
    "report_evidence_binding_and_section",
    "generation_snapshot",
    "report_impact_analysis_and_lifecycle",
    "external_augmentation_and_whitebox_gate",
)

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "phase2_control_slice_runtime_executed",
    "human_confirmation_performed",
    "report_evidence_binding_performed",
    "report_section_output_performed",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "snapshot_persistence_performed",
    "cited_material_update_evaluated",
    "source_withdrawal_evaluated",
    "evidence_downgrade_evaluated",
    "index_version_change_evaluated",
    "affected_report_identification_performed",
    "report_impact_analysis_performed",
    "report_status_impact_update_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_or_withdrawal_performed",
    "external_augmentation_displayed",
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
    "stage109_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_evidence_ledger_write_count",
    "actual_human_confirmation_count",
    "actual_report_evidence_binding_count",
    "actual_report_section_output_count",
    "actual_report_generation_count",
    "actual_pdf_generation_count",
    "actual_citation_generation_count",
    "actual_snapshot_persistence_count",
    "actual_cited_material_update_evaluation_count",
    "actual_source_withdrawal_evaluation_count",
    "actual_evidence_downgrade_evaluation_count",
    "actual_index_version_change_evaluation_count",
    "actual_affected_report_identification_count",
    "actual_report_impact_analysis_count",
    "actual_report_status_impact_update_count",
    "actual_report_quality_score_count",
    "actual_report_export_audit_write_count",
    "actual_template_limit_application_count",
    "actual_report_regeneration_count",
    "actual_report_withdrawal_count",
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
    "report_id_ref",
    "report_evidence_binding_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "report_snapshot_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "index_version_change_ref",
    "impact_trigger_ref",
    "impact_scope_ref",
    "affected_report_ref",
    "affected_critical_conclusion_ref",
    "report_status_impact_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
    "evidence_binding_integrity_state",
    "source_withdrawal_report_status_impact_state",
    "evidence_downgrade_report_status_impact_state",
    "index_version_change_report_status_impact_state",
    "affected_report_control_state",
    "external_augmentation_source_separation_state",
    "external_augmentation_may_not_be_internal_project_evidence",
    "external_augmentation_may_not_replace_evidence_binding",
    "external_augmentation_may_not_close_evidence_gap",
    "human_confirmation_state",
    "automatic_final_conclusion_allowed",
    "actual_report_impact_analysis_performed",
    "actual_report_status_impact_updated",
    "actual_external_augmentation_displayed",
    "actual_human_confirmation_recorded",
    "actual_final_conclusion_published",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "evidence_binding_integrity_control_view": (
        "scenario_id",
        "report_evidence_binding_ref",
        "critical_conclusion_ref",
        "evidence_id_ref",
        "evidence_gap_ref",
        "evidence_grade_ref",
        "citation_source_ref",
        "citation_page_ref",
        "evidence_binding_integrity_state",
    ),
    "report_status_impact_control_view": (
        "scenario_id",
        "report_id_ref",
        "report_snapshot_ref",
        "source_withdrawal_ref",
        "evidence_downgrade_ref",
        "index_version_change_ref",
        "impact_trigger_ref",
        "impact_scope_ref",
        "report_status_impact_ref",
        "source_withdrawal_report_status_impact_state",
        "evidence_downgrade_report_status_impact_state",
        "index_version_change_report_status_impact_state",
    ),
    "affected_report_control_view": (
        "scenario_id",
        "affected_report_ref",
        "affected_critical_conclusion_ref",
        "impact_trigger_ref",
        "impact_scope_ref",
        "report_status_impact_ref",
        "affected_report_control_state",
    ),
    "external_augmentation_source_separation_control_view": (
        "scenario_id",
        "external_augmentation_opinion_section_ref",
        "external_augmentation_underlying_source_type_ref",
        "internal_evidence_boundary_ref",
        "external_public_reference_control_label",
        "model_reasoning_control_label",
        "external_augmentation_source_separation_state",
        "external_augmentation_may_not_be_internal_project_evidence",
        "external_augmentation_may_not_replace_evidence_binding",
        "external_augmentation_may_not_close_evidence_gap",
    ),
    "human_confirmation_and_execution_boundary_control_view": (
        "scenario_id",
        "human_confirmation_state",
        "automatic_final_conclusion_allowed",
        "actual_report_impact_analysis_performed",
        "actual_report_status_impact_updated",
        "actual_human_confirmation_recorded",
        "actual_final_conclusion_published",
        "expectation_met",
    ),
}

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "cited_material_update_evidence_id_binding_integrity_control",
        "scenario_category": "CITED_MATERIAL_UPDATE_EVIDENCE_ID_BINDING_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
        "affected_report_review_required": False,
        "human_confirmation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_CITED_MATERIAL_EVIDENCE_BINDING"
        ),
    },
    {
        "scenario_id": "source_withdrawal_evidence_gap_report_status_impact_control",
        "scenario_category": "SOURCE_WITHDRAWAL_REPORT_STATUS_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_binding_mode": "evidence_gap",
        "source_withdrawal_impact_required": True,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
        "affected_report_review_required": False,
        "human_confirmation_required": True,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_SOURCE_WITHDRAWAL_REPORT_STATUS"
        ),
    },
    {
        "scenario_id": "evidence_downgrade_evidence_id_report_status_impact_control",
        "scenario_category": "EVIDENCE_DOWNGRADE_REPORT_STATUS_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": True,
        "index_version_change_impact_required": False,
        "affected_report_review_required": False,
        "human_confirmation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_DOWNGRADE_REPORT_STATUS"
        ),
    },
    {
        "scenario_id": "index_version_change_evidence_gap_report_status_impact_control",
        "scenario_category": "INDEX_VERSION_CHANGE_REPORT_STATUS_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_binding_mode": "evidence_gap",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": True,
        "affected_report_review_required": False,
        "human_confirmation_required": False,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_INDEX_VERSION_REPORT_STATUS"
        ),
    },
    {
        "scenario_id": "affected_report_lifecycle_external_augmentation_whitebox_control",
        "scenario_category": "AFFECTED_REPORT_EXTERNAL_AUGMENTATION_WHITEBOX_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_binding_mode": "evidence_id",
        "source_withdrawal_impact_required": False,
        "evidence_downgrade_impact_required": False,
        "index_version_change_impact_required": False,
        "affected_report_review_required": True,
        "human_confirmation_required": True,
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_AFFECTED_REPORT_AND_EXTERNAL_AUGMENTATION"
        ),
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage109_report_impact_analysis_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location(
        "stage109_phase2_report_impact_analysis_slice", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage109 P2 报告影响分析受控最小切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": CURRENT_GATE,
        "next_gate": NEXT_GATE if valid else CURRENT_GATE,
        "phase2_control_shape_preserved": False,
        "phase2_side_effect_free": False,
        "control_references_opaque": False,
        "phase2_control_request_count": 0,
        "phase2_input_field_count": 0,
        "phase2_projection_group_count": 0,
        "phase2_projection_field_count_per_request": 0,
        "phase2_projection_field_count_total": 0,
        "scenario_count": 0,
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": 0,
        "scenario_results": [],
        "control_view_count": 0,
        "control_views": {},
        "human_handling_count": 0,
        "human_handlings": [],
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _phase2_shape_is_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        getattr(phase2_module, "SCHEMA_VERSION", None) != P2_SCHEMA_VERSION
        or getattr(phase2_module, "RECORD_KIND", None) != P2_RECORD_KIND
        or tuple(getattr(phase2_module, "CONTROL_FIELDS", ())) != P2_CONTROL_FIELDS
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ()))
        != P2_CONTROL_SCENARIOS
        or len(getattr(phase2_module, "INPUT_FIELDS", ()))
        != P2_INPUT_FIELD_COUNT
        or len(getattr(phase2_module, "PHASE1_CONTROL_REFERENCE_FIELDS", ()))
        != P2_PHASE1_REFERENCE_FIELD_COUNT
        or result.get("schema_version") != P2_SCHEMA_VERSION
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

    projection_fields = dict(getattr(phase2_module, "PROJECTION_FIELDS", ()))
    if tuple(projection_fields) != P2_PROJECTION_PREFIXES:
        return False
    for prefix in P2_PROJECTION_PREFIXES:
        projections = result.get(f"{prefix}_control_projections")
        fields = projection_fields.get(prefix, ())
        if (
            not isinstance(projections, list)
            or len(projections) != P2_CONTROL_REQUEST_COUNT
            or result.get(f"{prefix}_control_projection_count")
            != P2_CONTROL_REQUEST_COUNT
            or any(
                not isinstance(item, Mapping) or set(item) != set(fields)
                for item in projections
            )
        ):
            return False
    return True


def _phase2_runtime_is_closed(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    expected_fields = tuple(getattr(phase2_module, "RUNTIME_CLOSED_FIELDS", ()))
    expected_counts = getattr(phase2_module, "_zero_actual_counts", lambda: {})()
    actual_counts = {
        field: value
        for field, value in result.items()
        if field.startswith("actual_") and field.endswith("_count")
    }
    return (
        result.get("persistent_record_created") is False
        and isinstance(boundary, Mapping)
        and tuple(boundary) == expected_fields
        and all(value is False for value in boundary.values())
        and actual_counts == expected_counts
    )


def _control_input_is_opaque(phase2_module: Any, control_input: Mapping[str, Any]) -> bool:
    fields = tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
    input_fields = tuple(getattr(phase2_module, "INPUT_FIELDS", ()))
    reference_fields = tuple(
        getattr(phase2_module, "PHASE1_CONTROL_REFERENCE_FIELDS", ())
    )
    requests = control_input.get(P2_CONTROL_FIELDS[0])
    configurations = getattr(phase2_module, "CONTROL_SCENARIO_CONFIGURATION", {})
    if (
        fields != P2_CONTROL_FIELDS
        or len(input_fields) != P2_INPUT_FIELD_COUNT
        or len(reference_fields) != P2_PHASE1_REFERENCE_FIELD_COUNT
        or not isinstance(requests, list)
        or len(requests) != P2_CONTROL_REQUEST_COUNT
    ):
        return False

    for scenario, request in zip(P2_CONTROL_SCENARIOS, requests):
        if not isinstance(request, Mapping) or set(request) != set(input_fields):
            return False
        expected_binding = configurations.get(scenario, {}).get("binding_mode")
        if (
            request.get("control_scenario") != scenario
            or request.get("binding_mode")
            != f"CONTROL_BINDING_{str(expected_binding).upper()}"
        ):
            return False
        if (request.get("evidence_id_ref") is None) == (
            request.get("evidence_gap_ref") is None
        ):
            return False
        for field in reference_fields:
            value = request.get(field)
            if value is None:
                if field not in {"evidence_id_ref", "evidence_gap_ref"}:
                    return False
            elif not _is_control_reference(value):
                return False
    return True


def _projection_record(
    result: Mapping[str, Any], prefix: str, index: int
) -> Optional[Mapping[str, Any]]:
    records = result.get(f"{prefix}_control_projections")
    if not isinstance(records, list) or index >= len(records):
        return None
    record = records[index]
    return record if isinstance(record, Mapping) else None


def _binding_mode(request: Mapping[str, Any]) -> Optional[str]:
    evidence_id = request.get("evidence_id_ref")
    evidence_gap = request.get("evidence_gap_ref")
    if (evidence_id is None) == (evidence_gap is None):
        return None
    return "evidence_id" if evidence_id is not None else "evidence_gap"


def _all_control_references(
    mapping: Mapping[str, Any], fields: tuple[str, ...]
) -> bool:
    return all(_is_control_reference(mapping.get(field)) for field in fields)


def _failure_for_projection(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    section: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    external: Mapping[str, Any],
) -> Optional[str]:
    if request.get("control_scenario") != definition["phase2_control_scenario"]:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    binding_mode = _binding_mode(request)
    if binding_mode is None:
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID"
    if binding_mode != definition["expected_binding_mode"]:
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"

    request_reference_fields = (
        "report_id_ref",
        "report_evidence_binding_ref",
        "critical_conclusion_ref",
        "evidence_grade_ref",
        "citation_source_ref",
        "citation_page_ref",
        "report_snapshot_ref",
        "source_withdrawal_ref",
        "evidence_downgrade_ref",
        "index_version_change_ref",
        "impact_trigger_ref",
        "impact_scope_ref",
        "affected_report_ref",
        "affected_critical_conclusion_ref",
        "report_status_impact_ref",
        "external_augmentation_opinion_section_ref",
        "external_augmentation_underlying_source_type_ref",
        "internal_evidence_boundary_ref",
        "human_confirmation_item_ref",
        "business_line_whitebox_confirmation_gate_ref",
    )
    if not _all_control_references(request, request_reference_fields):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    expected_binding_state = (
        "CONTROL_EVIDENCE_ID_BINDING_REFERENCE_ONLY"
        if binding_mode == "evidence_id"
        else "CONTROL_EVIDENCE_GAP_BINDING_REFERENCE_ONLY"
    )
    if section.get("report_evidence_binding_control_state") != expected_binding_state:
        return "REPORT_EVIDENCE_BINDING_CONTROL_MISSING"
    if (
        section.get("evidence_id_ref") != request.get("evidence_id_ref")
        or section.get("evidence_gap_ref") != request.get("evidence_gap_ref")
        or not _all_control_references(
            section,
            (
                "report_id_ref",
                "report_evidence_binding_ref",
                "critical_conclusion_ref",
                "evidence_grade_ref",
                "citation_source_ref",
                "citation_page_ref",
            ),
        )
    ):
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"
    if any(
        section.get(field) is not False
        for field in (
            "actual_report_evidence_binding_performed",
            "actual_report_section_output_performed",
            "actual_pdf_citation_rendered",
        )
    ):
        return "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH"

    if (
        snapshot.get("generation_snapshot_control_state")
        != "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED"
        or snapshot.get("actual_generation_snapshot_persisted") is not False
    ):
        return "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH"

    lifecycle_states = {
        "report_impact_control_state": "CONTROL_REPORT_IMPACT_REFERENCE_ONLY_NOT_ANALYZED",
        "cited_material_update_control_state": (
            "CONTROL_CITED_MATERIAL_UPDATE_REFERENCE_ONLY_NOT_EVALUATED"
        ),
        "source_withdrawal_control_state": (
            "CONTROL_SOURCE_WITHDRAWAL_REFERENCE_ONLY_NOT_EVALUATED"
        ),
        "evidence_downgrade_control_state": (
            "CONTROL_EVIDENCE_DOWNGRADE_REFERENCE_ONLY_NOT_EVALUATED"
        ),
        "index_version_change_control_state": (
            "CONTROL_INDEX_VERSION_CHANGE_REFERENCE_ONLY_NOT_EVALUATED"
        ),
        "affected_report_control_state": (
            "CONTROL_AFFECTED_REPORT_REFERENCE_ONLY_NOT_IDENTIFIED"
        ),
        "affected_critical_conclusion_control_state": (
            "CONTROL_AFFECTED_CRITICAL_CONCLUSION_REFERENCE_ONLY_NOT_IDENTIFIED"
        ),
        "report_status_impact_control_state": (
            "CONTROL_REPORT_STATUS_IMPACT_REFERENCE_ONLY_NOT_UPDATED"
        ),
    }
    if any(lifecycle.get(field) != value for field, value in lifecycle_states.items()):
        return "REPORT_STATUS_IMPACT_CONTROL_MISSING"
    if any(
        lifecycle.get(field) is not False
        for field in (
            "automatic_report_impact_update_allowed",
            "automatic_report_quality_scoring_allowed",
            "automatic_report_export_audit_write_allowed",
            "automatic_report_regeneration_allowed",
            "automatic_report_withdrawal_allowed",
            "actual_report_snapshot_created",
            "actual_report_impact_analysis_performed",
            "actual_report_status_impact_updated",
            "actual_report_quality_scored",
            "actual_report_export_audit_written",
            "actual_template_limit_applied",
            "actual_report_regenerated",
            "actual_report_withdrawn",
        )
    ):
        return "REPORT_STATUS_AUTOMATIC_UPDATE_BOUNDARY_BREACH"
    if not _all_control_references(
        lifecycle,
        (
            "report_snapshot_ref",
            "source_withdrawal_ref",
            "evidence_downgrade_ref",
            "index_version_change_ref",
            "impact_trigger_ref",
            "impact_scope_ref",
            "affected_report_ref",
            "affected_critical_conclusion_ref",
            "report_status_impact_ref",
        ),
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    if external.get("external_augmentation_representation_state") != (
        "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
        "SEPARATE_FROM_INTERNAL_EVIDENCE"
    ):
        return "EXTERNAL_AUGMENTATION_SOURCE_TYPE_DRIFT"
    if external.get("external_augmentation_may_not_be_internal_project_evidence") is not True:
        return "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE"
    if external.get("external_augmentation_may_not_replace_evidence_binding") is not True:
        return "EXTERNAL_AUGMENTATION_REPLACES_EVIDENCE_BINDING"
    if external.get("external_augmentation_may_not_close_evidence_gap") is not True:
        return "EXTERNAL_AUGMENTATION_CLOSES_EVIDENCE_GAP"
    if external.get("business_line_whitebox_confirmation_required") is not True:
        return "BUSINESS_WHITEBOX_CONFIRMATION_GATE_MISSING"
    if any(
        external.get(field) is not False
        for field in (
            "automatic_human_confirmation_allowed",
            "automatic_final_conclusion_allowed",
            "actual_external_augmentation_displayed",
            "actual_human_confirmation_recorded",
            "actual_final_conclusion_published",
        )
    ):
        return "HUMAN_CONFIRMATION_OR_FINAL_CONCLUSION_BOUNDARY_BREACH"
    if not _all_control_references(
        external,
        (
            "external_augmentation_opinion_section_ref",
            "external_augmentation_underlying_source_type_ref",
            "internal_evidence_boundary_ref",
            "external_public_reference_control_label",
            "model_reasoning_control_label",
        ),
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"
    return None


def _impact_state(required: bool, required_state: str, absent_state: str) -> str:
    return required_state if required else absent_state


def _scenario_record(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    external: Mapping[str, Any],
) -> dict[str, Any]:
    human_confirmation_state = (
        "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
        if definition["human_confirmation_required"]
        else "CONTROL_WHITEBOX_GATE_PRESENT_NOT_EXECUTED"
    )
    return {
        "scenario_id": definition["scenario_id"],
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenario": request["control_scenario"],
        "report_id_ref": request["report_id_ref"],
        "report_evidence_binding_ref": request["report_evidence_binding_ref"],
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "citation_source_ref": request["citation_source_ref"],
        "citation_page_ref": request["citation_page_ref"],
        "report_snapshot_ref": request["report_snapshot_ref"],
        "source_withdrawal_ref": request["source_withdrawal_ref"],
        "evidence_downgrade_ref": request["evidence_downgrade_ref"],
        "index_version_change_ref": request["index_version_change_ref"],
        "impact_trigger_ref": request["impact_trigger_ref"],
        "impact_scope_ref": request["impact_scope_ref"],
        "affected_report_ref": request["affected_report_ref"],
        "affected_critical_conclusion_ref": request[
            "affected_critical_conclusion_ref"
        ],
        "report_status_impact_ref": request["report_status_impact_ref"],
        "external_augmentation_opinion_section_ref": request[
            "external_augmentation_opinion_section_ref"
        ],
        "external_augmentation_underlying_source_type_ref": request[
            "external_augmentation_underlying_source_type_ref"
        ],
        "internal_evidence_boundary_ref": request["internal_evidence_boundary_ref"],
        "external_public_reference_control_label": external[
            "external_public_reference_control_label"
        ],
        "model_reasoning_control_label": external["model_reasoning_control_label"],
        "evidence_binding_integrity_state": (
            "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED"
        ),
        "source_withdrawal_report_status_impact_state": _impact_state(
            definition["source_withdrawal_impact_required"],
            "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            "CONTROL_SOURCE_WITHDRAWAL_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
        ),
        "evidence_downgrade_report_status_impact_state": _impact_state(
            definition["evidence_downgrade_impact_required"],
            "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            "CONTROL_EVIDENCE_DOWNGRADE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
        ),
        "index_version_change_report_status_impact_state": _impact_state(
            definition["index_version_change_impact_required"],
            "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            "CONTROL_INDEX_VERSION_CHANGE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
        ),
        "affected_report_control_state": _impact_state(
            definition["affected_report_review_required"],
            "CONTROL_AFFECTED_REPORT_AND_CRITICAL_CONCLUSION_FUTURE_REVIEW_REQUIRED",
            "CONTROL_AFFECTED_REPORT_REFERENCE_ONLY_NOT_IDENTIFIED",
        ),
        "external_augmentation_source_separation_state": (
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
            "SEPARATE_FROM_INTERNAL_EVIDENCE"
        ),
        "external_augmentation_may_not_be_internal_project_evidence": external[
            "external_augmentation_may_not_be_internal_project_evidence"
        ],
        "external_augmentation_may_not_replace_evidence_binding": external[
            "external_augmentation_may_not_replace_evidence_binding"
        ],
        "external_augmentation_may_not_close_evidence_gap": external[
            "external_augmentation_may_not_close_evidence_gap"
        ],
        "human_confirmation_state": human_confirmation_state,
        "automatic_final_conclusion_allowed": False,
        "actual_report_impact_analysis_performed": lifecycle[
            "actual_report_impact_analysis_performed"
        ],
        "actual_report_status_impact_updated": lifecycle[
            "actual_report_status_impact_updated"
        ],
        "actual_external_augmentation_displayed": external[
            "actual_external_augmentation_displayed"
        ],
        "actual_human_confirmation_recorded": external[
            "actual_human_confirmation_recorded"
        ],
        "actual_final_conclusion_published": external[
            "actual_final_conclusion_published"
        ],
        "expectation_met": True,
    }


def _human_handling(
    definition: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "business_line_whitebox_handling_code": definition[
            "business_line_whitebox_handling_code"
        ],
        "whitebox_confirmation_required": definition["human_confirmation_required"],
        "human_confirmation_recorded": False,
        "final_conclusion_state": "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
    }


def _control_views(
    scenarios: list[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        name: [{field: scenario[field] for field in fields} for scenario in scenarios]
        for name, fields in CONTROL_VIEW_FIELDS.items()
    }


def build_report_impact_analysis_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """机械重放固定 P2 控制投影并生成纯内存 P3 专项场景报告。"""

    try:
        phase2_module = _load_phase2_module()
        control_input = phase2_module.build_control_input()
        executor = (
            phase2_executor
            if phase2_executor is not None
            else phase2_module.execute_report_impact_analysis_control_slice
        )
        phase2_result = executor(control_input)
    except Exception:
        return _base_report(False, "PHASE2_CONTROL_REPLAY_UNAVAILABLE")

    if not isinstance(phase2_result, Mapping) or not _phase2_shape_is_preserved(
        phase2_module, phase2_result
    ):
        return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
    if not _phase2_runtime_is_closed(phase2_module, phase2_result):
        return _base_report(False, "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH")
    if not _control_input_is_opaque(phase2_module, control_input):
        return _base_report(False, "PHASE2_CONTROL_INPUT_NOT_OPAQUE")

    requests = control_input[P2_CONTROL_FIELDS[0]]
    scenarios: list[dict[str, Any]] = []
    for index, definition in enumerate(SCENARIO_DEFINITIONS):
        request = requests[index]
        section = _projection_record(
            phase2_result, "report_evidence_binding_and_section", index
        )
        snapshot = _projection_record(phase2_result, "generation_snapshot", index)
        lifecycle = _projection_record(
            phase2_result, "report_impact_analysis_and_lifecycle", index
        )
        external = _projection_record(
            phase2_result, "external_augmentation_and_whitebox_gate", index
        )
        if any(value is None for value in (section, snapshot, lifecycle, external)):
            return _base_report(False, "PHASE2_CONTROL_SHAPE_MISMATCH")
        failure = _failure_for_projection(
            definition, request, section, snapshot, lifecycle, external
        )
        if failure is not None:
            return _base_report(False, failure)
        scenarios.append(_scenario_record(definition, request, lifecycle, external))

    views = _control_views(scenarios)
    handlings = [
        _human_handling(definition, scenario)
        for definition, scenario in zip(SCENARIO_DEFINITIONS, scenarios)
    ]
    report = _base_report(True, None)
    report.update(
        {
            "phase2_control_shape_preserved": True,
            "phase2_side_effect_free": True,
            "control_references_opaque": True,
            "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
            "phase2_input_field_count": P2_INPUT_FIELD_COUNT,
            "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
            "phase2_projection_field_count_per_request": (
                P2_PROJECTION_FIELD_COUNT_PER_REQUEST
            ),
            "phase2_projection_field_count_total": P2_PROJECTION_FIELD_COUNT_TOTAL,
            "scenario_count": len(scenarios),
            "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
            "scenario_results": scenarios,
            "control_view_count": len(views),
            "control_views": views,
            "human_handling_count": len(handlings),
            "human_handlings": handlings,
        }
    )
    return report
