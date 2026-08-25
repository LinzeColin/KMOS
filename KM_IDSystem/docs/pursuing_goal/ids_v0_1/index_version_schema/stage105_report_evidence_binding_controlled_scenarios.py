"""Stage105 P3：报告证据绑定的纯内存专项异常场景验证。

模块只重放 Stage105 P2 的固定、非业务、reference-only 控制投影。它验证
关键结论始终关联 evidence_id 或 evidence_gap，资料撤回、证据降级和索引
版本变化保持报告状态影响控制形状，外部增强保持外部来源语义并受业务线白箱
确认门禁约束。模块不读取真实资料、报告、PDF 或证据账本，也不调用模型、
Agent、OVH 或生产服务，不写入数据库、审计或持久化状态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


SCHEMA_VERSION = "ids.stage105.report_evidence_binding.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EVIDENCE_BINDING_SCENARIOS"
CURRENT_GATE = "IDS-STAGE105-P3-GATE"
NEXT_GATE = "IDS-STAGE105-P4-GATE"
PASS_RESULT = "PASS_REPORT_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REPORT_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

P2_SCHEMA_VERSION = "ids.stage105.report_evidence_binding.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EVIDENCE_BINDING"
P2_EXECUTION_STATE = "PASS_IN_MEMORY_REPORT_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED"
P2_CONTROL_PREFIX = ":control:stage105-p2:"
P2_CONTROL_FIELDS = ("report_evidence_binding_control_requests",)
P2_CONTROL_REQUEST_COUNT = 5
P2_INPUT_FIELD_COUNT = 26
P2_PHASE1_REFERENCE_FIELD_COUNT = 24
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 66
P2_PROJECTION_FIELD_COUNT_TOTAL = 330
P2_CONTROL_SCENARIOS = (
    "evidence_id_binding_reference_only",
    "evidence_gap_binding_reference_only",
    "external_augmentation_section_reference_only",
    "human_confirmation_item_reference_only",
    "report_lifecycle_reference_only",
)
P2_PROJECTION_PREFIXES = (
    "report_section_binding",
    "generation_snapshot",
    "report_lifecycle",
    "external_augmentation_and_whitebox_gate",
)

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "phase2_control_slice_runtime_executed",
    "report_evidence_binding_performed",
    "report_section_output_performed",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "snapshot_persistence_performed",
    "report_status_impact_analysis_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_or_withdrawal_performed",
    "external_augmentation_displayed",
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
    "stage105_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_business_source_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_evidence_ledger_write_count",
    "actual_report_evidence_binding_count",
    "actual_report_status_impact_analysis_count",
    "actual_report_quality_score_count",
    "actual_report_export_audit_write_count",
    "actual_external_augmentation_display_count",
    "actual_human_confirmation_count",
    "actual_report_status_update_count",
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
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "index_version_ref",
    "report_snapshot_ref",
    "report_status_ref",
    "report_impact_analysis_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "external_augmentation_section_ref",
    "external_augmentation_source_type_ref",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
    "evidence_binding_integrity_state",
    "report_status_impact_trigger",
    "report_status_impact_state",
    "evidence_grade_downgrade_state",
    "index_version_change_state",
    "material_withdrawal_state",
    "external_augmentation_source_separation_state",
    "external_augmentation_may_not_be_internal_project_evidence",
    "external_augmentation_may_not_close_evidence_gap",
    "human_confirmation_state",
    "automatic_final_conclusion_allowed",
    "actual_report_status_updated",
    "actual_external_augmentation_displayed",
    "expectation_met",
)

CONTROL_VIEW_FIELDS = {
    "evidence_binding_integrity_control_view": (
        "scenario_id",
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
        "report_status_ref",
        "report_snapshot_ref",
        "index_version_ref",
        "report_status_impact_trigger",
        "report_status_impact_state",
        "evidence_grade_downgrade_state",
        "index_version_change_state",
        "material_withdrawal_state",
    ),
    "external_augmentation_source_separation_control_view": (
        "scenario_id",
        "external_augmentation_section_ref",
        "external_augmentation_source_type_ref",
        "external_public_reference_control_label",
        "model_reasoning_control_label",
        "external_augmentation_source_separation_state",
        "external_augmentation_may_not_be_internal_project_evidence",
        "external_augmentation_may_not_close_evidence_gap",
    ),
    "human_confirmation_and_final_conclusion_gate_control_view": (
        "scenario_id",
        "human_confirmation_state",
        "automatic_final_conclusion_allowed",
        "actual_report_status_updated",
        "actual_external_augmentation_displayed",
        "expectation_met",
    ),
    "actual_execution_boundary_control_view": (
        "scenario_id",
        "actual_report_status_updated",
        "actual_external_augmentation_displayed",
        "automatic_final_conclusion_allowed",
    ),
}

SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "critical_conclusion_evidence_id_binding_integrity_control",
        "scenario_category": "EVIDENCE_ID_BINDING_INTEGRITY_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[0],
        "expected_binding_mode": "evidence_id",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_ID_BINDING_INTEGRITY"
        ),
        "report_status_impact_required": False,
        "human_confirmation_required": False,
    },
    {
        "scenario_id": "critical_conclusion_evidence_gap_binding_integrity_control",
        "scenario_category": "EVIDENCE_GAP_BINDING_INTEGRITY_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[1],
        "expected_binding_mode": "evidence_gap",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_GAP_BINDING_INTEGRITY"
        ),
        "report_status_impact_required": False,
        "human_confirmation_required": False,
    },
    {
        "scenario_id": "external_augmentation_retains_external_source_type_control",
        "scenario_category": "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[2],
        "expected_binding_mode": "evidence_id",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EXTERNAL_AUGMENTATION_SOURCE_TYPE"
        ),
        "report_status_impact_required": False,
        "human_confirmation_required": False,
    },
    {
        "scenario_id": "human_confirmation_gate_keeps_final_conclusion_unpublished_control",
        "scenario_category": "HUMAN_CONFIRMATION_FINAL_CONCLUSION_GATE_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[3],
        "expected_binding_mode": "evidence_id",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_CONFIRM_REPORT_CONCLUSION"
        ),
        "report_status_impact_required": False,
        "human_confirmation_required": True,
    },
    {
        "scenario_id": "withdrawal_downgrade_and_index_change_impact_report_status_control",
        "scenario_category": "REPORT_STATUS_IMPACT_CONTROL",
        "phase2_control_scenario": P2_CONTROL_SCENARIOS[4],
        "expected_binding_mode": "evidence_id",
        "business_line_whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_REPORT_STATUS_IMPACT"
        ),
        "report_status_impact_required": True,
        "human_confirmation_required": True,
    },
)

Phase2Executor = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage105_report_evidence_binding_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage105_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage105 P2 报告证据绑定受控最小切片")
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
        or len(getattr(phase2_module, "INPUT_FIELDS", ())) != P2_INPUT_FIELD_COUNT
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
    expected_boundary_fields = tuple(getattr(phase2_module, "RUNTIME_CLOSED_FIELDS", ()))
    expected_zero_counts = getattr(phase2_module, "_zero_actual_counts", lambda: {})()
    actual_counts = {
        field: value
        for field, value in result.items()
        if field.startswith("actual_") and field.endswith("_count")
    }
    return (
        result.get("persistent_record_created") is False
        and isinstance(boundary, Mapping)
        and tuple(boundary) == expected_boundary_fields
        and all(value is False for value in boundary.values())
        and actual_counts == expected_zero_counts
    )


def _control_input_is_opaque(phase2_module: Any, control_input: Mapping[str, Any]) -> bool:
    fields = tuple(getattr(phase2_module, "CONTROL_FIELDS", ()))
    if fields != P2_CONTROL_FIELDS:
        return False
    requests = control_input.get(fields[0])
    input_fields = tuple(getattr(phase2_module, "INPUT_FIELDS", ()))
    if (
        not isinstance(requests, list)
        or len(requests) != P2_CONTROL_REQUEST_COUNT
        or len(input_fields) != P2_INPUT_FIELD_COUNT
    ):
        return False
    for scenario, request in zip(P2_CONTROL_SCENARIOS, requests):
        if not isinstance(request, Mapping) or set(request) != set(input_fields):
            return False
        if request.get("control_scenario") != scenario:
            return False
        if not isinstance(request.get("binding_mode"), str) or not request[
            "binding_mode"
        ].startswith("CONTROL_BINDING_"):
            return False
        for field, value in request.items():
            if field in {"control_scenario", "binding_mode"}:
                continue
            if value is None:
                if field not in {"evidence_id_ref", "evidence_gap_ref"}:
                    return False
                continue
            if not _is_control_reference(value):
                return False
        if (request.get("evidence_id_ref") is None) == (
            request.get("evidence_gap_ref") is None
        ):
            return False
    return True


def _projection_record(
    result: Mapping[str, Any], prefix: str, index: int
) -> Optional[Mapping[str, Any]]:
    values = result.get(f"{prefix}_control_projections")
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    return value if isinstance(value, Mapping) else None


def _binding_mode(request: Mapping[str, Any]) -> Optional[str]:
    evidence_id = request.get("evidence_id_ref")
    evidence_gap = request.get("evidence_gap_ref")
    if (evidence_id is None) == (evidence_gap is None):
        return None
    return "evidence_id" if evidence_id is not None else "evidence_gap"


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
    if not all(
        _is_control_reference(request.get(field))
        for field in (
            "report_id_ref",
            "critical_conclusion_ref",
            "evidence_grade_ref",
            "citation_source_ref",
            "citation_page_ref",
            "index_version_ref",
            "report_snapshot_ref",
            "report_status_ref",
            "report_impact_analysis_ref",
            "report_quality_score_ref",
            "report_export_audit_ref",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    expected_binding_state = (
        "CONTROL_EVIDENCE_ID_BINDING_REFERENCE_ONLY"
        if binding_mode == "evidence_id"
        else "CONTROL_EVIDENCE_GAP_BINDING_REFERENCE_ONLY"
    )
    if section.get("report_evidence_binding_state") != expected_binding_state:
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"
    if (
        section.get("evidence_id_ref") != request.get("evidence_id_ref")
        or section.get("evidence_gap_ref") != request.get("evidence_gap_ref")
    ):
        return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT"
    if section.get("actual_report_section_written") is not False:
        return "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH"
    if not all(
        _is_control_reference(section.get(field))
        for field in (
            "report_id_ref",
            "critical_conclusion_ref",
            "evidence_grade_ref",
            "citation_source_ref",
            "citation_page_ref",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    if snapshot.get("generation_snapshot_control_state") != (
        "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED"
    ) or snapshot.get("actual_generation_snapshot_persisted") is not False:
        return "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH"
    if not all(
        _is_control_reference(snapshot.get(field))
        for field in (
            "data_snapshot_ref",
            "index_version_ref",
            "evidence_snapshot_ref",
            "model_snapshot_ref",
            "generated_at_ref",
            "report_snapshot_ref",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    if lifecycle.get("report_lifecycle_control_state") != (
        "CONTROL_REPORT_LIFECYCLE_REFERENCE_ONLY_NOT_EXECUTED"
    ):
        return "REPORT_STATUS_IMPACT_CONTROL_MISSING"
    if any(
        lifecycle.get(field) is not False
        for field in (
            "automatic_report_status_update_allowed",
            "automatic_report_quality_scoring_allowed",
            "automatic_report_export_audit_write_allowed",
            "actual_report_status_updated",
            "actual_report_impact_analysis_performed",
            "actual_report_quality_scored",
            "actual_report_export_audit_written",
        )
    ):
        return "REPORT_STATUS_AUTOMATIC_UPDATE_BOUNDARY_BREACH"
    if not all(
        _is_control_reference(lifecycle.get(field))
        for field in (
            "report_status_ref",
            "report_impact_analysis_ref",
            "report_quality_score_ref",
            "report_export_audit_ref",
            "report_template_limit_ref",
            "report_regeneration_and_withdrawal_ref",
            "audit_boundary_ref",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"

    if external.get("external_augmentation_representation_state") != (
        "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED"
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
    if not all(
        _is_control_reference(external.get(field))
        for field in (
            "external_augmentation_section_ref",
            "external_augmentation_source_type_ref",
            "external_public_reference_control_label",
            "model_reasoning_control_label",
        )
    ):
        return "NON_OPAQUE_CONTROL_REFERENCE"
    return None


def _status_impact_values(
    definition: Mapping[str, Any],
) -> tuple[str, str, str, str, str]:
    if definition["report_status_impact_required"]:
        return (
            "CONTROL_MATERIAL_WITHDRAWAL_EVIDENCE_DOWNGRADE_INDEX_VERSION_CHANGE",
            "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED",
            "CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS",
            "CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS",
            "CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS",
        )
    return (
        "CONTROL_REPORT_STATUS_IMPACT_NOT_EVALUATED",
        "CONTROL_FUTURE_REPORT_STATUS_REMAINS_UNCHANGED",
        "CONTROL_EVIDENCE_GRADE_DOWNGRADE_NOT_APPLICABLE",
        "CONTROL_INDEX_VERSION_CHANGE_NOT_APPLICABLE",
        "CONTROL_MATERIAL_WITHDRAWAL_NOT_APPLICABLE",
    )


def _scenario_record(
    definition: Mapping[str, Any],
    request: Mapping[str, Any],
    section: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    external: Mapping[str, Any],
) -> dict[str, Any]:
    (
        report_status_impact_trigger,
        report_status_impact_state,
        evidence_grade_downgrade_state,
        index_version_change_state,
        material_withdrawal_state,
    ) = _status_impact_values(definition)
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
        "critical_conclusion_ref": request["critical_conclusion_ref"],
        "evidence_id_ref": request["evidence_id_ref"],
        "evidence_gap_ref": request["evidence_gap_ref"],
        "evidence_grade_ref": request["evidence_grade_ref"],
        "citation_source_ref": request["citation_source_ref"],
        "citation_page_ref": request["citation_page_ref"],
        "index_version_ref": request["index_version_ref"],
        "report_snapshot_ref": request["report_snapshot_ref"],
        "report_status_ref": request["report_status_ref"],
        "report_impact_analysis_ref": request["report_impact_analysis_ref"],
        "report_quality_score_ref": request["report_quality_score_ref"],
        "report_export_audit_ref": request["report_export_audit_ref"],
        "external_augmentation_section_ref": request[
            "external_augmentation_section_ref"
        ],
        "external_augmentation_source_type_ref": request[
            "external_augmentation_source_type_ref"
        ],
        "external_public_reference_control_label": external[
            "external_public_reference_control_label"
        ],
        "model_reasoning_control_label": external["model_reasoning_control_label"],
        "evidence_binding_integrity_state": (
            "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED"
        ),
        "report_status_impact_trigger": report_status_impact_trigger,
        "report_status_impact_state": report_status_impact_state,
        "evidence_grade_downgrade_state": evidence_grade_downgrade_state,
        "index_version_change_state": index_version_change_state,
        "material_withdrawal_state": material_withdrawal_state,
        "external_augmentation_source_separation_state": (
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING"
        ),
        "external_augmentation_may_not_be_internal_project_evidence": external[
            "external_augmentation_may_not_be_internal_project_evidence"
        ],
        "external_augmentation_may_not_close_evidence_gap": external[
            "external_augmentation_may_not_close_evidence_gap"
        ],
        "human_confirmation_state": human_confirmation_state,
        "automatic_final_conclusion_allowed": False,
        "actual_report_status_updated": lifecycle["actual_report_status_updated"],
        "actual_external_augmentation_displayed": external[
            "actual_external_augmentation_displayed"
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


def build_report_evidence_binding_phase3_report(
    phase2_executor: Optional[Phase2Executor] = None,
) -> dict[str, Any]:
    """机械重放固定 P2 控制投影并生成纯内存 P3 场景报告。"""

    try:
        phase2_module = _load_phase2_module()
        control_input = phase2_module.build_control_input()
        executor = (
            phase2_executor
            if phase2_executor is not None
            else phase2_module.execute_report_evidence_binding_control_slice
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
        section = _projection_record(phase2_result, "report_section_binding", index)
        snapshot = _projection_record(phase2_result, "generation_snapshot", index)
        lifecycle = _projection_record(phase2_result, "report_lifecycle", index)
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
        scenarios.append(
            _scenario_record(definition, request, section, snapshot, lifecycle, external)
        )

    views = _control_views(scenarios)
    handlings = [
        _human_handling(definition, scenario)
        for definition, scenario in zip(SCENARIO_DEFINITIONS, scenarios)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": True,
        "result": PASS_RESULT,
        "failure_state": None,
        "current_gate": CURRENT_GATE,
        "next_gate": NEXT_GATE,
        "phase2_control_shape_preserved": True,
        "phase2_side_effect_free": True,
        "control_references_opaque": True,
        "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
        "phase2_input_field_count": P2_INPUT_FIELD_COUNT,
        "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
        "phase2_projection_field_count_per_request": P2_PROJECTION_FIELD_COUNT_PER_REQUEST,
        "phase2_projection_field_count_total": P2_PROJECTION_FIELD_COUNT_TOTAL,
        "scenario_count": len(scenarios),
        "scenario_field_count": len(SCENARIO_FIELDS),
        "scenario_field_check_count": len(scenarios) * len(SCENARIO_FIELDS),
        "scenario_results": scenarios,
        "control_view_count": len(views),
        "control_views": views,
        "human_handling_count": len(handlings),
        "human_handlings": handlings,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }
