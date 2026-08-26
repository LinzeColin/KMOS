"""Stage110 P4：报告质量评分的 metadata-only 交付控制证据。

模块只从 Stage110 P3 固定、非业务、reference-only 场景派生报告样例、
快照、质量评分、影响分析、模板限制、人工确认与生命周期说明的控制记录。
模块不读取真实资料、报告、PDF 或证据账本，不调用模型、Agent、OVH 或生产服务，
也不写入数据库、审计或持久化状态。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "ids.stage110.report_quality_score.phase4.delivery.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE"
PASS_RESULT = "PASS_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE110-P4-GATE"
NEXT_GATE = "IDS-STAGE110-REVIEW-GATE"

P3_SCHEMA_VERSION = "ids.stage110.report_quality_score.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_SCENARIOS"
P3_PASS_RESULT = "PASS_REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_CURRENT_GATE = "IDS-STAGE110-P3-GATE"
P3_NEXT_GATE = "IDS-STAGE110-P4-GATE"
P2_CONTROL_PREFIX = ":control:stage110-p2:"
DELIVERY_PREFIX = ":control:stage110-p4:"

P3_SCENARIO_IDS = (
    "cited_material_update_evidence_id_binding_integrity_control",
    "source_withdrawal_evidence_gap_report_status_impact_control",
    "evidence_downgrade_evidence_id_report_status_impact_control",
    "index_version_change_evidence_gap_report_status_impact_control",
    "quality_score_export_external_augmentation_whitebox_control",
)
P3_SCENARIO_FIELD_COUNT = 52
P3_CONTROL_VIEW_COUNT = 5
P3_HUMAN_HANDLING_COUNT = 5
P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT = 2
P3_QUALITY_WHITEBOX_CONFIRMATION_REQUIRED_COUNT = 1
P3_PHASE2_CONTROL_REQUEST_COUNT = 5
P3_PHASE2_INPUT_FIELD_COUNT = 42
P3_PHASE2_PHASE1_REFERENCE_FIELD_COUNT = 40
P3_PHASE2_PROJECTION_GROUP_COUNT = 4
P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST = 126
P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL = 630
P3_SCENARIO_FIELD_CHECK_COUNT = 260

REPORT_SAMPLE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "report_snapshot_ref",
    "report_sample_state",
    "evidence_binding_integrity_state",
    "external_augmentation_source_separation_state",
    "source_withdrawal_report_status_impact_state",
    "human_confirmation_state",
    "automatic_final_conclusion_allowed",
    "actual_report_sample_rendered",
)
REPORT_SNAPSHOT_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "report_snapshot_ref",
    "report_status_impact_ref",
    "impact_scope_ref",
    "affected_report_ref",
    "snapshot_reference_state",
    "snapshot_consistency_state",
    "snapshot_delivery_state",
    "actual_report_snapshot_persisted",
    "actual_report_or_pdf_accessed",
    "actual_report_status_impact_updated",
)
REPORT_QUALITY_SCORE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "quality_metric_definition_ref",
    "quality_formula_ref",
    "quality_weight_ref",
    "quality_threshold_ref",
    "report_quality_score_ref",
    "quality_score_explanation_ref",
    "quality_score_boundary_state",
    "quality_score_delivery_state",
    "quality_whitebox_confirmation_required",
    "actual_report_quality_score_calculated",
)
REPORT_IMPACT_ANALYSIS_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "report_status_impact_ref",
    "impact_scope_ref",
    "affected_report_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "index_version_change_ref",
    "source_withdrawal_report_status_impact_state",
    "evidence_downgrade_report_status_impact_state",
    "index_version_change_report_status_impact_state",
    "impact_analysis_delivery_state",
    "actual_report_impact_analysis_performed",
    "actual_report_status_impact_updated",
)
REPORT_TEMPLATE_AND_WHITEBOX_CONFIRMATION_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "report_template_limit_ref",
    "human_confirmation_gate_ref",
    "report_template_limit_delivery_state",
    "human_confirmation_state",
    "business_line_whitebox_confirmation_required",
    "automatic_final_conclusion_allowed",
    "final_conclusion_state",
    "actual_template_constraint_reviewed",
    "actual_human_confirmation_performed",
    "actual_final_conclusion_published",
    "actual_report_or_pdf_generated",
)
REGENERATION_AND_WITHDRAWAL_FIELDS = (
    "instruction_id",
    "control_domain",
    "trigger_state_ref",
    "rollback_target_ref",
    "rollback_target_result",
    "predecessor_phase_ref",
    "report_status_impact_ref",
    "business_line_whitebox_confirmation_required",
    "human_confirmation_required",
    "versioned_basis_required",
    "verifiable_rollback_target_required",
    "actual_report_regeneration_performed",
    "actual_report_withdrawal_performed",
    "persistent_state_write_performed",
)
DELIVERY_GROUPS = (
    ("report_sample_control_records", REPORT_SAMPLE_FIELDS),
    ("report_snapshot_control_records", REPORT_SNAPSHOT_FIELDS),
    ("report_quality_score_control_records", REPORT_QUALITY_SCORE_FIELDS),
    ("report_impact_analysis_control_records", REPORT_IMPACT_ANALYSIS_FIELDS),
    (
        "report_template_and_whitebox_confirmation_control_records",
        REPORT_TEMPLATE_AND_WHITEBOX_CONFIRMATION_FIELDS,
    ),
    ("regeneration_and_withdrawal_control_records", REGENERATION_AND_WITHDRAWAL_FIELDS),
)
DELIVERY_FIELD_CHECK_COUNT = 388

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "phase3_controlled_scenarios_runtime_executed",
    "report_sample_rendered",
    "report_snapshot_persistence_performed",
    "report_quality_score_calculation_performed",
    "report_status_impact_analysis_performed",
    "report_template_constraint_review_performed",
    "human_confirmation_performed",
    "report_regeneration_performed",
    "report_withdrawal_performed",
    "report_or_pdf_generation_performed",
    "citation_generation_performed",
    "report_export_audit_write_performed",
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
    "stage110_phase4_runtime_executed",
)
ZERO_COUNTER_FIELDS = (
    "actual_report_sample_count",
    "actual_report_snapshot_persistence_count",
    "actual_report_quality_score_calculation_count",
    "actual_report_impact_analysis_count",
    "actual_report_template_constraint_review_count",
    "actual_human_confirmation_count",
    "actual_report_regeneration_count",
    "actual_report_withdrawal_count",
    "actual_report_or_pdf_generation_count",
    "actual_report_status_update_count",
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
    "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID",
    "REPORT_STATUS_IMPACT_CONTROL_MISSING",
    "QUALITY_SCORE_BOUNDARY_MISSING",
    "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING",
    "WHITEBOX_CONFIRMATION_GATE_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "REPORT_TEMPLATE_AND_HUMAN_CONFIRMATION_CONTROL_MISSING",
    "REPORT_REGENERATION_AND_WITHDRAWAL_CONTROL_MISSING",
    "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED",
    "ACTUAL_REPORT_STATUS_OR_QUALITY_CHANGE_SIGNAL_DETECTED",
    "SECOND_AUTHORITY_CREATED",
    "STAGE110_REVIEW_STARTED",
)
OPERATOR_FEEDBACK = (
    "报告样例、快照、质量评分与影响分析保持 metadata-only 控制记录，等待业务线白箱确认。",
    "资料撤回、证据降级与索引版本变化保持报告状态复核要求，未更新真实报告状态。",
    "模板限制、人工确认与最终结论保持业务线白箱门禁，未记录人工确认。",
    "报告重新生成与撤回说明固定指向可验证的 P3 回退目标，未执行任何报告生命周期动作。",
)

Phase3Executor = Callable[[], Mapping[str, Any]]


def _load_phase3_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage110_report_quality_score_controlled_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location(
        "stage110_phase3_report_quality_score_scenarios", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage110 P3 报告质量评分专项场景")
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
        "human_handling_count": 0,
        "whitebox_confirmation_required_scenario_count": 0,
        "quality_whitebox_confirmation_required_scenario_count": 0,
        "report_sample_control_records": [],
        "report_snapshot_control_records": [],
        "report_quality_score_control_records": [],
        "report_impact_analysis_control_records": [],
        "report_template_and_whitebox_confirmation_control_records": [],
        "regeneration_and_withdrawal_control_records": [],
        "delivery_field_check_count": 0,
        "failure_state_count": len(FAILURE_STATES),
        "operator_feedback": [],
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
    }


def _phase3_shape_is_preserved(phase3_module: Any, report: Mapping[str, Any]) -> bool:
    if any(
        (
            getattr(phase3_module, "SCHEMA_VERSION", None) != P3_SCHEMA_VERSION,
            getattr(phase3_module, "RECORD_KIND", None) != P3_RECORD_KIND,
            getattr(phase3_module, "PASS_RESULT", None) != P3_PASS_RESULT,
            getattr(phase3_module, "CURRENT_GATE", None) != P3_CURRENT_GATE,
            getattr(phase3_module, "NEXT_GATE", None) != P3_NEXT_GATE,
            report.get("schema_version") != P3_SCHEMA_VERSION,
            report.get("record_kind") != P3_RECORD_KIND,
            report.get("valid") is not True,
            report.get("result") != P3_PASS_RESULT,
            report.get("failure_state") is not None,
            report.get("current_gate") != P3_CURRENT_GATE,
            report.get("next_gate") != P3_NEXT_GATE,
            report.get("phase2_control_request_count")
            != P3_PHASE2_CONTROL_REQUEST_COUNT,
            report.get("phase2_input_field_count") != P3_PHASE2_INPUT_FIELD_COUNT,
            report.get("phase2_projection_group_count")
            != P3_PHASE2_PROJECTION_GROUP_COUNT,
            report.get("phase2_projection_field_count_per_request")
            != P3_PHASE2_PROJECTION_FIELD_COUNT_PER_REQUEST,
            report.get("phase2_projection_field_count_total")
            != P3_PHASE2_PROJECTION_FIELD_COUNT_TOTAL,
            report.get("scenario_count") != len(P3_SCENARIO_IDS),
            report.get("scenario_field_count") != P3_SCENARIO_FIELD_COUNT,
            report.get("scenario_field_check_count")
            != P3_SCENARIO_FIELD_CHECK_COUNT,
            report.get("control_view_count") != P3_CONTROL_VIEW_COUNT,
            report.get("human_handling_count") != P3_HUMAN_HANDLING_COUNT,
            report.get("second_authoritative_source_created") is not False,
            report.get("persistent_record_created") is not False,
        )
    ):
        return False

    scenario_fields = tuple(getattr(phase3_module, "SCENARIO_FIELDS", ()))
    scenarios = report.get("scenario_results")
    if (
        not isinstance(scenarios, list)
        or len(scenario_fields) != P3_SCENARIO_FIELD_COUNT
        or len(scenarios) != len(P3_SCENARIO_IDS)
        or tuple(
            item.get("scenario_id") for item in scenarios if isinstance(item, Mapping)
        )
        != P3_SCENARIO_IDS
    ):
        return False

    for scenario in scenarios:
        if not isinstance(scenario, Mapping) or set(scenario) != set(scenario_fields):
            return False
        evidence_id = scenario.get("evidence_id_ref")
        evidence_gap = scenario.get("evidence_gap_ref")
        if any(
            (
                scenario.get("expectation_met") is not True,
                (evidence_id is None) == (evidence_gap is None),
                evidence_id is not None and not _is_control_reference(evidence_id),
                evidence_gap is not None and not _is_control_reference(evidence_gap),
                scenario.get("evidence_binding_integrity_state")
                != "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
                scenario.get("external_augmentation_source_separation_state")
                != "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE",
                scenario.get("external_augmentation_may_not_be_internal_project_evidence")
                is not True,
                scenario.get("external_augmentation_may_not_replace_evidence_binding")
                is not True,
                scenario.get("external_augmentation_may_not_close_evidence_gap")
                is not True,
                scenario.get("human_confirmation_state")
                not in {
                    "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED",
                    "CONTROL_WHITEBOX_GATE_PRESENT_NOT_EXECUTED",
                },
                any(
                    scenario.get(field) is not False
                    for field in (
                        "automatic_final_conclusion_allowed",
                        "actual_report_quality_scored",
                        "actual_report_status_impact_updated",
                        "actual_external_augmentation_displayed",
                        "actual_human_confirmation_recorded",
                        "actual_final_conclusion_published",
                    )
                ),
            )
        ):
            return False

    handlings = report.get("human_handlings")
    views = report.get("control_views")
    view_fields = getattr(phase3_module, "CONTROL_VIEW_FIELDS", {})
    return (
        isinstance(handlings, list)
        and len(handlings) == P3_HUMAN_HANDLING_COUNT
        and sum(
            item.get("whitebox_confirmation_required") is True
            for item in handlings
            if isinstance(item, Mapping)
        )
        == P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
        and sum(
            item.get("quality_whitebox_confirmation_required") is True
            for item in handlings
            if isinstance(item, Mapping)
        )
        == P3_QUALITY_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
        and all(
            isinstance(item, Mapping)
            and item.get("human_confirmation_recorded") is False
            and item.get("final_conclusion_state")
            == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
            for item in handlings
        )
        and isinstance(views, Mapping)
        and set(views) == set(view_fields)
        and all(
            isinstance(records, list) and len(records) == len(P3_SCENARIO_IDS)
            for records in views.values()
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


def _scenario_references_are_opaque(scenario: Mapping[str, Any]) -> bool:
    evidence_id = scenario.get("evidence_id_ref")
    evidence_gap = scenario.get("evidence_gap_ref")
    if (evidence_id is None) == (evidence_gap is None):
        return False
    return (
        (evidence_id is None or _is_control_reference(evidence_id))
        and (evidence_gap is None or _is_control_reference(evidence_gap))
        and all(
            _is_control_reference(scenario.get(field))
            for field in (
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
                "impact_scope_ref",
                "affected_report_ref",
                "report_status_impact_ref",
                "internal_evidence_coverage_rate_ref",
                "citation_completeness_rate_ref",
                "external_augmentation_ratio_ref",
                "evidence_gap_count_ref",
                "quality_metric_definition_ref",
                "quality_formula_ref",
                "quality_weight_ref",
                "quality_threshold_ref",
                "report_quality_score_ref",
                "quality_score_explanation_ref",
                "report_export_audit_ref",
                "external_augmentation_opinion_section_ref",
                "external_augmentation_underlying_source_type_ref",
                "internal_evidence_boundary_ref",
                "external_public_reference_control_label",
                "model_reasoning_control_label",
            )
        )
    )


def _report_sample_record(scenario: Mapping[str, Any], index: int) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"report-sample-{index}"),
        "scenario_id": scenario["scenario_id"],
        "report_id_ref": scenario["report_id_ref"],
        "critical_conclusion_ref": scenario["critical_conclusion_ref"],
        "evidence_id_ref": scenario["evidence_id_ref"],
        "evidence_gap_ref": scenario["evidence_gap_ref"],
        "evidence_grade_ref": scenario["evidence_grade_ref"],
        "citation_source_ref": scenario["citation_source_ref"],
        "citation_page_ref": scenario["citation_page_ref"],
        "report_snapshot_ref": scenario["report_snapshot_ref"],
        "report_sample_state": "CONTROL_REPORT_SAMPLE_REFERENCE_ONLY_NOT_RENDERED",
        "evidence_binding_integrity_state": scenario["evidence_binding_integrity_state"],
        "external_augmentation_source_separation_state": scenario[
            "external_augmentation_source_separation_state"
        ],
        "source_withdrawal_report_status_impact_state": scenario[
            "source_withdrawal_report_status_impact_state"
        ],
        "human_confirmation_state": scenario["human_confirmation_state"],
        "automatic_final_conclusion_allowed": False,
        "actual_report_sample_rendered": False,
    }


def _report_snapshot_record(scenario: Mapping[str, Any], index: int) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"report-snapshot-{index}"),
        "scenario_id": scenario["scenario_id"],
        "report_id_ref": scenario["report_id_ref"],
        "report_snapshot_ref": scenario["report_snapshot_ref"],
        "report_status_impact_ref": scenario["report_status_impact_ref"],
        "impact_scope_ref": scenario["impact_scope_ref"],
        "affected_report_ref": scenario["affected_report_ref"],
        "snapshot_reference_state": "CONTROL_REPORT_SNAPSHOT_REFERENCE_ONLY_NOT_PERSISTED",
        "snapshot_consistency_state": "CONTROL_SNAPSHOT_REQUIRES_REPORT_STATUS_AND_SCOPE_BINDING",
        "snapshot_delivery_state": "CONTROL_SNAPSHOT_DELIVERY_RECORD_ONLY",
        "actual_report_snapshot_persisted": False,
        "actual_report_or_pdf_accessed": False,
        "actual_report_status_impact_updated": False,
    }


def _report_quality_score_record(
    scenario: Mapping[str, Any], handling: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"report-quality-score-{index}"),
        "scenario_id": scenario["scenario_id"],
        "report_id_ref": scenario["report_id_ref"],
        "quality_metric_definition_ref": scenario["quality_metric_definition_ref"],
        "quality_formula_ref": scenario["quality_formula_ref"],
        "quality_weight_ref": scenario["quality_weight_ref"],
        "quality_threshold_ref": scenario["quality_threshold_ref"],
        "report_quality_score_ref": scenario["report_quality_score_ref"],
        "quality_score_explanation_ref": scenario["quality_score_explanation_ref"],
        "quality_score_boundary_state": scenario["quality_score_boundary_state"],
        "quality_score_delivery_state": "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED",
        "quality_whitebox_confirmation_required": handling[
            "quality_whitebox_confirmation_required"
        ],
        "actual_report_quality_score_calculated": False,
    }


def _report_impact_analysis_record(scenario: Mapping[str, Any], index: int) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"report-impact-analysis-{index}"),
        "scenario_id": scenario["scenario_id"],
        "report_id_ref": scenario["report_id_ref"],
        "report_status_impact_ref": scenario["report_status_impact_ref"],
        "impact_scope_ref": scenario["impact_scope_ref"],
        "affected_report_ref": scenario["affected_report_ref"],
        "source_withdrawal_ref": scenario["source_withdrawal_ref"],
        "evidence_downgrade_ref": scenario["evidence_downgrade_ref"],
        "index_version_change_ref": scenario["index_version_change_ref"],
        "source_withdrawal_report_status_impact_state": scenario[
            "source_withdrawal_report_status_impact_state"
        ],
        "evidence_downgrade_report_status_impact_state": scenario[
            "evidence_downgrade_report_status_impact_state"
        ],
        "index_version_change_report_status_impact_state": scenario[
            "index_version_change_report_status_impact_state"
        ],
        "impact_analysis_delivery_state": "CONTROL_IMPACT_ANALYSIS_REFERENCE_ONLY_NOT_EXECUTED",
        "actual_report_impact_analysis_performed": False,
        "actual_report_status_impact_updated": False,
    }


def _template_and_whitebox_record(
    scenario: Mapping[str, Any], handling: Mapping[str, Any], index: int
) -> dict[str, Any]:
    return {
        "delivery_record_id": _delivery_ref(f"template-and-whitebox-{index}"),
        "scenario_id": scenario["scenario_id"],
        "report_id_ref": scenario["report_id_ref"],
        "report_template_limit_ref": _delivery_ref(f"template-limit-{index}"),
        "human_confirmation_gate_ref": _delivery_ref(
            f"whitebox-confirmation-gate-{index}"
        ),
        "report_template_limit_delivery_state": "CONTROL_TEMPLATE_LIMIT_REFERENCE_ONLY_NOT_REVIEWED",
        "human_confirmation_state": scenario["human_confirmation_state"],
        "business_line_whitebox_confirmation_required": handling[
            "whitebox_confirmation_required"
        ],
        "automatic_final_conclusion_allowed": False,
        "final_conclusion_state": "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
        "actual_template_constraint_reviewed": False,
        "actual_human_confirmation_performed": False,
        "actual_final_conclusion_published": False,
        "actual_report_or_pdf_generated": False,
    }


def _regeneration_and_withdrawal_records() -> list[dict[str, Any]]:
    return [
        {
            "instruction_id": _delivery_ref("report-regeneration-instruction"),
            "control_domain": "REPORT_REGENERATION",
            "trigger_state_ref": _delivery_ref("regeneration-trigger"),
            "rollback_target_ref": _delivery_ref("stage110-p3-controlled-scenarios"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage110-p3"),
            "report_status_impact_ref": _delivery_ref("report-status-impact"),
            "business_line_whitebox_confirmation_required": True,
            "human_confirmation_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_report_regeneration_performed": False,
            "actual_report_withdrawal_performed": False,
            "persistent_state_write_performed": False,
        },
        {
            "instruction_id": _delivery_ref("report-withdrawal-instruction"),
            "control_domain": "REPORT_WITHDRAWAL",
            "trigger_state_ref": _delivery_ref("withdrawal-trigger"),
            "rollback_target_ref": _delivery_ref("stage110-p3-controlled-scenarios"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage110-p3"),
            "report_status_impact_ref": _delivery_ref("report-status-impact"),
            "business_line_whitebox_confirmation_required": True,
            "human_confirmation_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_report_regeneration_performed": False,
            "actual_report_withdrawal_performed": False,
            "persistent_state_write_performed": False,
        },
    ]


def _validate_delivery_groups(report: Mapping[str, Any]) -> Optional[str]:
    expected_counts = {
        "report_sample_control_records": len(P3_SCENARIO_IDS),
        "report_snapshot_control_records": len(P3_SCENARIO_IDS),
        "report_quality_score_control_records": len(P3_SCENARIO_IDS),
        "report_impact_analysis_control_records": len(P3_SCENARIO_IDS),
        "report_template_and_whitebox_confirmation_control_records": len(
            P3_SCENARIO_IDS
        ),
        "regeneration_and_withdrawal_control_records": 2,
    }
    for name, fields in DELIVERY_GROUPS:
        records = report.get(name)
        if (
            not isinstance(records, list)
            or len(records) != expected_counts[name]
            or any(
                not isinstance(record, Mapping) or set(record) != set(fields)
                for record in records
            )
        ):
            return "DELIVERY_RECORD_SHAPE_MISMATCH"

    for name, _fields in DELIVERY_GROUPS[:-1]:
        for record in report[name]:
            if (
                not _is_delivery_reference(record["delivery_record_id"])
                or record["scenario_id"] not in P3_SCENARIO_IDS
                or any(
                    value is True
                    for key, value in record.items()
                    if key.startswith("actual_")
                )
            ):
                return "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED"

    for record in report["report_sample_control_records"]:
        evidence_id = record["evidence_id_ref"]
        evidence_gap = record["evidence_gap_ref"]
        if (
            (evidence_id is None) == (evidence_gap is None)
            or (evidence_id is not None and not _is_control_reference(evidence_id))
            or (evidence_gap is not None and not _is_control_reference(evidence_gap))
            or any(
                not _is_control_reference(record[field])
                for field in (
                    "report_id_ref",
                    "critical_conclusion_ref",
                    "evidence_grade_ref",
                    "citation_source_ref",
                    "citation_page_ref",
                    "report_snapshot_ref",
                )
            )
            or record["automatic_final_conclusion_allowed"] is not False
        ):
            return "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID"

    for record in report["report_snapshot_control_records"]:
        if any(
            not _is_control_reference(record[field])
            for field in (
                "report_id_ref",
                "report_snapshot_ref",
                "report_status_impact_ref",
                "impact_scope_ref",
                "affected_report_ref",
            )
        ):
            return "REPORT_STATUS_IMPACT_CONTROL_MISSING"

    for record in report["report_quality_score_control_records"]:
        if (
            any(
                not _is_control_reference(record[field])
                for field in (
                    "report_id_ref",
                    "quality_metric_definition_ref",
                    "quality_formula_ref",
                    "quality_weight_ref",
                    "quality_threshold_ref",
                    "report_quality_score_ref",
                    "quality_score_explanation_ref",
                )
            )
            or record["quality_score_boundary_state"]
            not in {
                "CONTROL_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED",
                "CONTROL_QUALITY_SCORE_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED",
            }
            or record["actual_report_quality_score_calculated"] is not False
        ):
            return "QUALITY_SCORE_BOUNDARY_MISSING"

    for record in report["report_impact_analysis_control_records"]:
        if (
            any(
                not _is_control_reference(record[field])
                for field in (
                    "report_id_ref",
                    "report_status_impact_ref",
                    "impact_scope_ref",
                    "affected_report_ref",
                    "source_withdrawal_ref",
                    "evidence_downgrade_ref",
                    "index_version_change_ref",
                )
            )
            or record["source_withdrawal_report_status_impact_state"]
            not in {
                "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_SOURCE_WITHDRAWAL_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            }
            or record["evidence_downgrade_report_status_impact_state"]
            not in {
                "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_EVIDENCE_DOWNGRADE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            }
            or record["index_version_change_report_status_impact_state"]
            not in {
                "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_INDEX_VERSION_CHANGE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            }
        ):
            return "REPORT_STATUS_IMPACT_CONTROL_MISSING"

    for record in report["report_template_and_whitebox_confirmation_control_records"]:
        if (
            not _is_delivery_reference(record["report_template_limit_ref"])
            or not _is_delivery_reference(record["human_confirmation_gate_ref"])
            or record["automatic_final_conclusion_allowed"] is not False
            or record["final_conclusion_state"]
            != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ):
            return "REPORT_TEMPLATE_AND_HUMAN_CONFIRMATION_CONTROL_MISSING"

    records = report["regeneration_and_withdrawal_control_records"]
    if any(
        any(
            (
                not _is_delivery_reference(record["instruction_id"]),
                not _is_delivery_reference(record["trigger_state_ref"]),
                not _is_delivery_reference(record["rollback_target_ref"]),
                not _is_delivery_reference(record["predecessor_phase_ref"]),
                not _is_delivery_reference(record["report_status_impact_ref"]),
                record["rollback_target_result"] != P3_PASS_RESULT,
                record["business_line_whitebox_confirmation_required"] is not True,
                record["human_confirmation_required"] is not True,
                record["versioned_basis_required"] is not True,
                record["verifiable_rollback_target_required"] is not True,
                any(
                    value is not False
                    for key, value in record.items()
                    if key.startswith("actual_")
                    or key == "persistent_state_write_performed"
                ),
            )
        )
        for record in records
    ):
        return "REPORT_REGENERATION_AND_WITHDRAWAL_CONTROL_MISSING"

    if any(
        value is True
        for key, value in report.items()
        if key.startswith("actual_") and isinstance(value, bool)
    ):
        return "ACTUAL_REPORT_STATUS_OR_QUALITY_CHANGE_SIGNAL_DETECTED"
    return None


def build_report_quality_score_phase4_delivery_report(
    phase3_executor: Optional[Phase3Executor] = None,
) -> dict[str, Any]:
    """从固定 P3 场景派生纯内存 P4 metadata-only 交付控制记录。"""

    try:
        phase3_module = _load_phase3_module()
        executor = (
            phase3_executor
            if phase3_executor is not None
            else phase3_module.build_report_quality_score_phase3_report
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

    scenarios = phase3_report["scenario_results"]
    if not all(_scenario_references_are_opaque(scenario) for scenario in scenarios):
        return _base_report(False, "NON_OPAQUE_CONTROL_REFERENCE")
    handlings_by_scenario = {
        handling["scenario_id"]: handling
        for handling in phase3_report["human_handlings"]
    }
    if set(handlings_by_scenario) != set(P3_SCENARIO_IDS):
        return _base_report(False, "WHITEBOX_CONFIRMATION_GATE_MISSING")

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
            "human_handling_count": P3_HUMAN_HANDLING_COUNT,
            "whitebox_confirmation_required_scenario_count": (
                P3_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
            ),
            "quality_whitebox_confirmation_required_scenario_count": (
                P3_QUALITY_WHITEBOX_CONFIRMATION_REQUIRED_COUNT
            ),
            "report_sample_control_records": [
                _report_sample_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "report_snapshot_control_records": [
                _report_snapshot_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "report_quality_score_control_records": [
                _report_quality_score_record(
                    scenario, handlings_by_scenario[scenario["scenario_id"]], index
                )
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "report_impact_analysis_control_records": [
                _report_impact_analysis_record(scenario, index)
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "report_template_and_whitebox_confirmation_control_records": [
                _template_and_whitebox_record(
                    scenario, handlings_by_scenario[scenario["scenario_id"]], index
                )
                for index, scenario in enumerate(scenarios, start=1)
            ],
            "regeneration_and_withdrawal_control_records": (
                _regeneration_and_withdrawal_records()
            ),
            "delivery_field_check_count": DELIVERY_FIELD_CHECK_COUNT,
            "operator_feedback": list(OPERATOR_FEEDBACK),
        }
    )
    failure_state = _validate_delivery_groups(report)
    if failure_state is not None:
        return _base_report(False, failure_state)
    return report
