"""Stage106 P4：外部增强意见章节的纯内存交付证据。

模块只从 Stage106 P3 的固定、非业务、reference-only 专项场景派生交付
控制记录。它描述报告样例、报告快照、报告质量评分、影响分析、模板限制、
人工确认、重新生成和撤回的未来控制条件，不读取真实资料、报告、PDF 或
证据账本，不调用模型、Agent、OVH 或生产服务，也不写入数据库、审计或
持久化状态。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase4.delivery.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE"
PASS_RESULT = "PASS_EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE106-P4-GATE"
NEXT_GATE = "IDS-STAGE106-REVIEW-GATE"

P3_SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_SCENARIOS"
P3_PASS_RESULT = "PASS_EXTERNAL_AUGMENTATION_OPINION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_CURRENT_GATE = "IDS-STAGE106-P3-GATE"
P3_NEXT_GATE = "IDS-STAGE106-P4-GATE"
P3_CONTROL_PREFIX = ":control:stage106-p2:"
DELIVERY_PREFIX = ":control:stage106-p4:"

P3_SCENARIO_IDS = (
    "critical_conclusion_evidence_id_binding_integrity_control",
    "critical_conclusion_evidence_gap_binding_integrity_control",
    "external_augmentation_retains_external_source_type_control",
    "human_confirmation_gate_keeps_final_conclusion_unpublished_control",
    "withdrawal_downgrade_and_index_change_impact_report_status_control",
)
P3_SCENARIO_FIELDS = (
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
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "external_augmentation_opinion_section_ref",
    "underlying_source_type_ref",
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
    "external_augmentation_may_not_replace_evidence_binding",
    "external_augmentation_may_not_close_evidence_gap",
    "human_confirmation_state",
    "automatic_final_conclusion_allowed",
    "actual_report_status_impact_analysis_performed",
    "actual_external_augmentation_opinion_generated",
    "expectation_met",
)
P3_HUMAN_HANDLING_FIELDS = (
    "scenario_id",
    "scenario_category",
    "business_line_whitebox_handling_code",
    "whitebox_confirmation_required",
    "human_confirmation_recorded",
    "final_conclusion_state",
)
P3_RUNTIME_COUNTER_FIELDS = (
    "actual_phase2_control_replay_count",
    "actual_scenario_evaluation_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_model_reasoning_evaluation_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_evidence_ledger_write_count",
    "actual_external_augmentation_opinion_generation_count",
    "actual_report_evidence_binding_count",
    "actual_report_section_output_count",
    "actual_report_generation_count",
    "actual_pdf_generation_count",
    "actual_citation_generation_count",
    "actual_snapshot_persistence_count",
    "actual_report_status_impact_analysis_count",
    "actual_report_quality_score_count",
    "actual_report_export_audit_write_count",
    "actual_report_regeneration_or_withdrawal_count",
    "actual_external_augmentation_display_count",
    "actual_human_confirmation_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

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
    "index_version_ref",
    "report_sample_state",
    "evidence_binding_integrity_state",
    "external_augmentation_source_separation_state",
    "report_status_impact_state",
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
    "index_version_ref",
    "phase3_report_ref",
    "snapshot_reference_state",
    "snapshot_consistency_state",
    "snapshot_delivery_state",
    "actual_report_snapshot_persisted",
    "actual_report_or_pdf_accessed",
    "actual_report_status_impact_analysis_performed",
)
REPORT_QUALITY_SCORE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "report_quality_score_ref",
    "evidence_binding_integrity_state",
    "report_status_impact_state",
    "evidence_grade_downgrade_state",
    "quality_score_delivery_state",
    "quality_score_interpretation_state",
    "business_line_whitebox_confirmation_required",
    "automatic_final_conclusion_allowed",
    "actual_report_quality_score_calculated",
    "actual_report_quality_score_persisted",
)
REPORT_IMPACT_ANALYSIS_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "report_id_ref",
    "report_status_impact_ref",
    "report_impact_analysis_ref",
    "evidence_grade_ref",
    "index_version_ref",
    "report_status_impact_trigger",
    "report_status_impact_state",
    "evidence_grade_downgrade_state",
    "index_version_change_state",
    "material_withdrawal_state",
    "impact_analysis_delivery_state",
    "actual_report_impact_analysis_performed",
    "actual_report_status_update_performed",
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
    (
        "regeneration_and_withdrawal_control_records",
        REGENERATION_AND_WITHDRAWAL_FIELDS,
    ),
)
DELIVERY_FIELD_CHECK_COUNT = 388

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "model_reasoning_evaluated",
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
    "external_augmentation_opinion_displayed",
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
    "stage106_phase4_runtime_executed",
)
ACTUAL_COUNTER_FIELDS = (
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
    "PHASE3_CONTROL_OUTPUT_INVALID",
    "PHASE3_CONTROL_SHAPE_MISMATCH",
    "PHASE3_RUNTIME_SIGNAL_DETECTED",
    "CONTROL_REFERENCE_NOT_OPAQUE",
    "CRITICAL_CONCLUSION_BINDING_MISSING",
    "REPORT_STATUS_IMPACT_CONTROL_MISSING",
    "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING",
    "WHITEBOX_CONFIRMATION_GATE_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "REPORT_TEMPLATE_AND_HUMAN_CONFIRMATION_CONTROL_MISSING",
    "REPORT_REGENERATION_AND_WITHDRAWAL_CONTROL_MISSING",
    "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED",
    "ACTUAL_REPORT_STATUS_OR_QUALITY_CHANGE_SIGNAL_DETECTED",
    "SECOND_AUTHORITY_CREATED",
    "STAGE106_REVIEW_STARTED",
    "DELIVERY_EXPECTATION_MISMATCH",
)

Phase3Executor = Callable[[], Mapping[str, Any]]


def _load_phase3_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage106_external_augmentation_opinion_controlled_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage106_phase3_scenarios", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage106 P3 外部增强意见章节专项场景模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ACTUAL_COUNTER_FIELDS}


def _control_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P3_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _delivery_ref(name: str) -> str:
    return f"{DELIVERY_PREFIX}{name}:reference-only"


def _delivery_ref_is_opaque(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(DELIVERY_PREFIX)
        and value.endswith(":reference-only")
    )


def _requires_whitebox_confirmation(scenario: Mapping[str, Any]) -> bool:
    return (
        scenario["human_confirmation_state"]
        == "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
    )


def _failure_report(failure_state: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": False,
        "result": FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": ENTRY_GATE,
        "next_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_replayed_in_memory_only": False,
        "phase3_side_effect_free": False,
        "delivery_evidence_metadata_only": False,
        "control_references_opaque": False,
        "delivery_field_check_count": 0,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "stage106_review_started": False,
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [],
    }
    for group_name, _ in DELIVERY_GROUPS:
        report[group_name] = []
    return report


def _phase3_shape_failure(phase3_module: Any, report: Mapping[str, Any]) -> str | None:
    expected_boundary = tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
    definitions = tuple(getattr(phase3_module, "SCENARIO_DEFINITIONS", ()))
    definition_ids = tuple(
        item.get("scenario_id") if isinstance(item, Mapping) else None
        for item in definitions
    )
    if (
        getattr(phase3_module, "SCHEMA_VERSION", None) != P3_SCHEMA_VERSION
        or getattr(phase3_module, "RECORD_KIND", None) != P3_RECORD_KIND
        or getattr(phase3_module, "PASS_RESULT", None) != P3_PASS_RESULT
        or getattr(phase3_module, "CURRENT_GATE", None) != P3_CURRENT_GATE
        or getattr(phase3_module, "NEXT_GATE", None) != P3_NEXT_GATE
        or getattr(phase3_module, "P2_CONTROL_PREFIX", None) != P3_CONTROL_PREFIX
        or tuple(getattr(phase3_module, "SCENARIO_FIELDS", ())) != P3_SCENARIO_FIELDS
        or tuple(getattr(phase3_module, "ZERO_COUNTER_FIELDS", ()))
        != P3_RUNTIME_COUNTER_FIELDS
        or definition_ids != P3_SCENARIO_IDS
        or report.get("schema_version") != P3_SCHEMA_VERSION
        or report.get("record_kind") != P3_RECORD_KIND
        or report.get("result") != P3_PASS_RESULT
        or report.get("valid") is not True
        or report.get("failure_state") is not None
        or report.get("current_gate") != P3_CURRENT_GATE
        or report.get("next_gate") != P3_NEXT_GATE
        or report.get("phase2_control_shape_preserved") is not True
        or report.get("phase2_side_effect_free") is not True
        or report.get("control_references_opaque") is not True
        or report.get("phase2_control_request_count") != 5
        or report.get("phase2_input_field_count") != 30
        or report.get("phase2_projection_group_count") != 4
        or report.get("phase2_projection_field_count_per_request") != 74
        or report.get("phase2_projection_field_count_total") != 370
        or report.get("scenario_count") != len(P3_SCENARIO_IDS)
        or report.get("scenario_field_count") != len(P3_SCENARIO_FIELDS)
        or report.get("scenario_field_check_count")
        != len(P3_SCENARIO_IDS) * len(P3_SCENARIO_FIELDS)
        or report.get("control_view_count") != 5
        or report.get("human_handling_count") != len(P3_SCENARIO_IDS)
        or not isinstance(report.get("runtime_boundary"), Mapping)
        or tuple(report["runtime_boundary"]) != expected_boundary
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"

    scenarios = report.get("scenario_results")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != len(P3_SCENARIO_IDS)
        or tuple(item.get("scenario_id") for item in scenarios) != P3_SCENARIO_IDS
        or any(
            not isinstance(item, Mapping) or set(item) != set(P3_SCENARIO_FIELDS)
            for item in scenarios
        )
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"

    expected_views = getattr(phase3_module, "CONTROL_VIEW_FIELDS", {})
    views = report.get("control_views")
    if not isinstance(views, Mapping) or set(views) != set(expected_views):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    for name, fields in expected_views.items():
        records = views.get(name)
        if (
            not isinstance(records, list)
            or len(records) != len(P3_SCENARIO_IDS)
            or any(
                not isinstance(item, Mapping) or set(item) != set(fields)
                for item in records
            )
        ):
            return "PHASE3_CONTROL_SHAPE_MISMATCH"

    handlings = report.get("human_handlings")
    if (
        not isinstance(handlings, list)
        or len(handlings) != len(P3_SCENARIO_IDS)
        or tuple(item.get("scenario_id") for item in handlings) != P3_SCENARIO_IDS
        or any(
            not isinstance(item, Mapping) or set(item) != set(P3_HUMAN_HANDLING_FIELDS)
            for item in handlings
        )
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    return None


def _phase3_runtime_failure(phase3_module: Any, report: Mapping[str, Any]) -> str | None:
    if report.get("second_authoritative_source_created") is not False:
        return "SECOND_AUTHORITY_CREATED"
    boundary = report.get("runtime_boundary")
    actual_counts = {
        field: report.get(field)
        for field in P3_RUNTIME_COUNTER_FIELDS
    }
    if (
        report.get("persistent_record_created") is not False
        or not isinstance(boundary, Mapping)
        or tuple(boundary)
        != tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
        or any(value is not False for value in boundary.values())
        or actual_counts != {field: 0 for field in P3_RUNTIME_COUNTER_FIELDS}
    ):
        return "PHASE3_RUNTIME_SIGNAL_DETECTED"
    return None


def _phase3_semantic_failure(report: Mapping[str, Any]) -> str | None:
    scenarios = {item["scenario_id"]: item for item in report["scenario_results"]}
    handlings = {item["scenario_id"]: item for item in report["human_handlings"]}
    mandatory_references = (
        "report_id_ref",
        "critical_conclusion_ref",
        "evidence_grade_ref",
        "citation_source_ref",
        "citation_page_ref",
        "index_version_ref",
        "report_snapshot_ref",
        "report_status_impact_ref",
        "report_quality_score_ref",
        "report_export_audit_ref",
        "external_augmentation_opinion_section_ref",
        "underlying_source_type_ref",
        "external_public_reference_control_label",
        "model_reasoning_control_label",
    )
    confirmation_required_ids = {
        "human_confirmation_gate_keeps_final_conclusion_unpublished_control",
        "withdrawal_downgrade_and_index_change_impact_report_status_control",
    }
    for scenario_id in P3_SCENARIO_IDS:
        scenario = scenarios[scenario_id]
        handling = handlings[scenario_id]
        if not all(_control_ref(scenario.get(field)) for field in mandatory_references):
            return "CONTROL_REFERENCE_NOT_OPAQUE"
        evidence_id = scenario["evidence_id_ref"]
        evidence_gap = scenario["evidence_gap_ref"]
        if (
            (evidence_id is None) == (evidence_gap is None)
            or (evidence_id is not None and not _control_ref(evidence_id))
            or (evidence_gap is not None and not _control_ref(evidence_gap))
            or scenario["evidence_binding_integrity_state"]
            != "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED"
        ):
            return "CRITICAL_CONCLUSION_BINDING_MISSING"
        if (
            scenario["automatic_final_conclusion_allowed"] is not False
            or scenario["actual_report_status_impact_analysis_performed"] is not False
            or scenario["actual_external_augmentation_opinion_generated"] is not False
            or scenario["expectation_met"] is not True
            or handling["human_confirmation_recorded"] is not False
            or handling["final_conclusion_state"]
            != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ):
            return "DELIVERY_EXPECTATION_MISMATCH"
        requires_confirmation = scenario_id in confirmation_required_ids
        expected_confirmation_state = (
            "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
            if requires_confirmation
            else "CONTROL_WHITEBOX_GATE_PRESENT_NOT_EXECUTED"
        )
        if (
            scenario["human_confirmation_state"] != expected_confirmation_state
            or handling["whitebox_confirmation_required"] is not requires_confirmation
        ):
            return "WHITEBOX_CONFIRMATION_GATE_MISSING"

    external = scenarios[
        "external_augmentation_retains_external_source_type_control"
    ]
    if (
        external["external_augmentation_source_separation_state"]
        != (
            "CONTROL_EXTERNAL_AUGMENTATION_OPINION_RETAINS_EXTERNAL_PUBLIC_REFERENCE_"
            "AND_MODEL_REASONING_SEPARATE_FROM_INTERNAL_EVIDENCE"
        )
        or external["external_augmentation_may_not_be_internal_project_evidence"]
        is not True
        or external["external_augmentation_may_not_replace_evidence_binding"]
        is not True
        or external["external_augmentation_may_not_close_evidence_gap"] is not True
    ):
        return "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING"

    lifecycle = scenarios[
        "withdrawal_downgrade_and_index_change_impact_report_status_control"
    ]
    if (
        lifecycle["report_status_impact_trigger"]
        != "CONTROL_MATERIAL_WITHDRAWAL_EVIDENCE_DOWNGRADE_INDEX_VERSION_CHANGE"
        or lifecycle["report_status_impact_state"]
        != "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED"
        or lifecycle["evidence_grade_downgrade_state"]
        != "CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS"
        or lifecycle["index_version_change_state"]
        != "CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS"
        or lifecycle["material_withdrawal_state"]
        != "CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS"
    ):
        return "REPORT_STATUS_IMPACT_CONTROL_MISSING"
    return None


def _report_samples(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(f"report-sample-{item['scenario_id']}"),
            "scenario_id": item["scenario_id"],
            "report_id_ref": item["report_id_ref"],
            "critical_conclusion_ref": item["critical_conclusion_ref"],
            "evidence_id_ref": item["evidence_id_ref"],
            "evidence_gap_ref": item["evidence_gap_ref"],
            "evidence_grade_ref": item["evidence_grade_ref"],
            "citation_source_ref": item["citation_source_ref"],
            "citation_page_ref": item["citation_page_ref"],
            "index_version_ref": item["index_version_ref"],
            "report_sample_state": "CONTROL_REPORT_SAMPLE_REFERENCE_ONLY_NOT_RENDERED",
            "evidence_binding_integrity_state": item[
                "evidence_binding_integrity_state"
            ],
            "external_augmentation_source_separation_state": item[
                "external_augmentation_source_separation_state"
            ],
            "report_status_impact_state": item["report_status_impact_state"],
            "human_confirmation_state": item["human_confirmation_state"],
            "automatic_final_conclusion_allowed": False,
            "actual_report_sample_rendered": False,
        }
        for item in scenarios
    ]


def _report_snapshots(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"report-snapshot-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "report_id_ref": item["report_id_ref"],
            "report_snapshot_ref": item["report_snapshot_ref"],
            "report_status_impact_ref": item["report_status_impact_ref"],
            "index_version_ref": item["index_version_ref"],
            "phase3_report_ref": _delivery_ref("phase3-report-control"),
            "snapshot_reference_state": "CONTROL_REPORT_SNAPSHOT_REFERENCE_ONLY",
            "snapshot_consistency_state": (
                "CONTROL_REPORT_SNAPSHOT_BOUND_TO_INDEX_AND_STATUS_IMPACT_REFERENCE"
            ),
            "snapshot_delivery_state": (
                "CONTROL_REPORT_SNAPSHOT_REFERENCE_ONLY_NOT_PERSISTED"
            ),
            "actual_report_snapshot_persisted": False,
            "actual_report_or_pdf_accessed": False,
            "actual_report_status_impact_analysis_performed": False,
        }
        for item in scenarios
    ]


def _quality_scores(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"report-quality-score-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "report_id_ref": item["report_id_ref"],
            "report_quality_score_ref": item["report_quality_score_ref"],
            "evidence_binding_integrity_state": item[
                "evidence_binding_integrity_state"
            ],
            "report_status_impact_state": item["report_status_impact_state"],
            "evidence_grade_downgrade_state": item[
                "evidence_grade_downgrade_state"
            ],
            "quality_score_delivery_state": (
                "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED"
            ),
            "quality_score_interpretation_state": (
                "CONTROL_REPORT_QUALITY_SCORE_REQUIRES_EVIDENCE_AND_WHITEBOX_REVIEW"
            ),
            "business_line_whitebox_confirmation_required": (
                _requires_whitebox_confirmation(item)
            ),
            "automatic_final_conclusion_allowed": False,
            "actual_report_quality_score_calculated": False,
            "actual_report_quality_score_persisted": False,
        }
        for item in scenarios
    ]


def _impact_analyses(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"report-impact-analysis-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "report_id_ref": item["report_id_ref"],
            "report_status_impact_ref": item["report_status_impact_ref"],
            "report_impact_analysis_ref": _delivery_ref(
                f"report-impact-analysis-ref-{item['scenario_id']}"
            ),
            "evidence_grade_ref": item["evidence_grade_ref"],
            "index_version_ref": item["index_version_ref"],
            "report_status_impact_trigger": item["report_status_impact_trigger"],
            "report_status_impact_state": item["report_status_impact_state"],
            "evidence_grade_downgrade_state": item[
                "evidence_grade_downgrade_state"
            ],
            "index_version_change_state": item["index_version_change_state"],
            "material_withdrawal_state": item["material_withdrawal_state"],
            "impact_analysis_delivery_state": (
                "CONTROL_REPORT_IMPACT_ANALYSIS_REFERENCE_ONLY_NOT_EXECUTED"
            ),
            "actual_report_impact_analysis_performed": False,
            "actual_report_status_update_performed": False,
        }
        for item in scenarios
    ]


def _template_and_confirmation_records(
    scenarios: list[Mapping[str, Any]], handlings: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"report-template-and-whitebox-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "report_id_ref": item["report_id_ref"],
            "report_template_limit_ref": _delivery_ref(
                f"report-template-limit-{item['scenario_id']}"
            ),
            "human_confirmation_gate_ref": _delivery_ref(
                f"human-confirmation-gate-{item['scenario_id']}"
            ),
            "report_template_limit_delivery_state": (
                "CONTROL_REPORT_TEMPLATE_LIMIT_RECORDED_REFERENCE_ONLY"
            ),
            "human_confirmation_state": item["human_confirmation_state"],
            "business_line_whitebox_confirmation_required": (
                _requires_whitebox_confirmation(item)
            ),
            "automatic_final_conclusion_allowed": False,
            "final_conclusion_state": handlings[item["scenario_id"]][
                "final_conclusion_state"
            ],
            "actual_template_constraint_reviewed": False,
            "actual_human_confirmation_performed": False,
            "actual_final_conclusion_published": False,
            "actual_report_or_pdf_generated": False,
        }
        for item in scenarios
    ]


def _regeneration_and_withdrawal_records(
    scenarios: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lifecycle = next(
        item
        for item in scenarios
        if item["scenario_id"]
        == "withdrawal_downgrade_and_index_change_impact_report_status_control"
    )
    return [
        {
            "instruction_id": _delivery_ref(domain),
            "control_domain": domain,
            "trigger_state_ref": _delivery_ref(f"{domain}-trigger"),
            "rollback_target_ref": _delivery_ref(f"{domain}-to-phase3"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage106-phase3"),
            "report_status_impact_ref": lifecycle["report_status_impact_ref"],
            "business_line_whitebox_confirmation_required": True,
            "human_confirmation_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_report_regeneration_performed": False,
            "actual_report_withdrawal_performed": False,
            "persistent_state_write_performed": False,
        }
        for domain in ("report_regeneration", "report_withdrawal")
    ]


def _delivery_shape_is_valid(report: Mapping[str, Any]) -> bool:
    for group_name, fields in DELIVERY_GROUPS:
        records = report.get(group_name)
        expected_count = (
            2
            if group_name == "regeneration_and_withdrawal_control_records"
            else len(P3_SCENARIO_IDS)
        )
        if (
            not isinstance(records, list)
            or len(records) != expected_count
            or any(
                not isinstance(record, Mapping) or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return report.get("delivery_field_check_count") == DELIVERY_FIELD_CHECK_COUNT


def _delivery_references_are_opaque(report: Mapping[str, Any]) -> bool:
    for group_name, fields in DELIVERY_GROUPS:
        for record in report[group_name]:
            for field in fields:
                value = record[field]
                if field in {"evidence_id_ref", "evidence_gap_ref"} and value is None:
                    continue
                if field.endswith("_ref") or field in {
                    "delivery_record_id",
                    "instruction_id",
                }:
                    if not (_control_ref(value) or _delivery_ref_is_opaque(value)):
                        return False
    return True


def _template_and_confirmation_is_valid(
    report: Mapping[str, Any], scenarios: list[Mapping[str, Any]]
) -> bool:
    handlings = {
        item["scenario_id"]: item for item in report.get("phase3_human_handlings", [])
    }
    if set(handlings) != set(P3_SCENARIO_IDS):
        return False
    return report.get(
        "report_template_and_whitebox_confirmation_control_records"
    ) == _template_and_confirmation_records(scenarios, handlings)


def _regeneration_and_withdrawal_is_valid(
    report: Mapping[str, Any], scenarios: list[Mapping[str, Any]]
) -> bool:
    return report.get("regeneration_and_withdrawal_control_records") == (
        _regeneration_and_withdrawal_records(scenarios)
    )


def _delivery_execution_boundary_failure(report: Mapping[str, Any]) -> str | None:
    if report.get("second_authoritative_source_created") is not False:
        return "SECOND_AUTHORITY_CREATED"
    if report.get("stage106_review_started") is not False:
        return "STAGE106_REVIEW_STARTED"
    boundary = report.get("runtime_boundary")
    actual_counts = {field: report.get(field) for field in ACTUAL_COUNTER_FIELDS}
    if (
        report.get("persistent_record_created") is not False
        or not isinstance(boundary, Mapping)
        or tuple(boundary) != RUNTIME_CLOSED_FIELDS
        or any(value is not False for value in boundary.values())
        or actual_counts != _zero_actual_counts()
    ):
        return "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED"

    write_fields = {
        "actual_report_sample_rendered",
        "actual_report_snapshot_persisted",
        "actual_report_or_pdf_accessed",
        "actual_template_constraint_reviewed",
        "actual_human_confirmation_performed",
        "actual_final_conclusion_published",
        "actual_report_or_pdf_generated",
        "actual_report_regeneration_performed",
        "actual_report_withdrawal_performed",
        "persistent_state_write_performed",
    }
    status_or_quality_fields = {
        "actual_report_status_impact_analysis_performed",
        "actual_report_quality_score_calculated",
        "actual_report_quality_score_persisted",
        "actual_report_impact_analysis_performed",
        "actual_report_status_update_performed",
    }
    for group_name, fields in DELIVERY_GROUPS:
        for record in report.get(group_name, []):
            if not isinstance(record, Mapping):
                return "DELIVERY_RECORD_SHAPE_MISMATCH"
            if any(record.get(field) is not False for field in fields if field in write_fields):
                return "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED"
            if any(
                record.get(field) is not False
                for field in fields
                if field in status_or_quality_fields
            ):
                return "ACTUAL_REPORT_STATUS_OR_QUALITY_CHANGE_SIGNAL_DETECTED"
    return None


def build_external_augmentation_opinion_phase4_delivery_report(
    phase3_executor: Phase3Executor | None = None,
) -> dict[str, Any]:
    try:
        phase3_module = _load_phase3_module()
        phase3_report = (
            phase3_executor()
            if phase3_executor is not None
            else phase3_module.build_external_augmentation_opinion_phase3_report()
        )
    except Exception:
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")
    if not isinstance(phase3_report, Mapping):
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")

    failure = _phase3_shape_failure(phase3_module, phase3_report)
    if failure is not None:
        return _failure_report(failure)
    failure = _phase3_runtime_failure(phase3_module, phase3_report)
    if failure is not None:
        return _failure_report(failure)
    failure = _phase3_semantic_failure(phase3_report)
    if failure is not None:
        return _failure_report(failure)

    scenarios = list(phase3_report["scenario_results"])
    handlings = {
        item["scenario_id"]: item for item in phase3_report["human_handlings"]
    }
    report = _failure_report("DELIVERY_EXPECTATION_MISMATCH")
    report.update(
        {
            "valid": True,
            "result": PASS_RESULT,
            "failure_state": None,
            "next_gate": NEXT_GATE,
            "phase3_controlled_scenarios_replayed_in_memory_only": True,
            "phase3_side_effect_free": True,
            "delivery_evidence_metadata_only": True,
            "control_references_opaque": True,
            "delivery_field_check_count": DELIVERY_FIELD_CHECK_COUNT,
            "phase3_human_handlings": list(phase3_report["human_handlings"]),
            "report_sample_control_records": _report_samples(scenarios),
            "report_snapshot_control_records": _report_snapshots(scenarios),
            "report_quality_score_control_records": _quality_scores(scenarios),
            "report_impact_analysis_control_records": _impact_analyses(scenarios),
            "report_template_and_whitebox_confirmation_control_records": (
                _template_and_confirmation_records(scenarios, handlings)
            ),
            "regeneration_and_withdrawal_control_records": (
                _regeneration_and_withdrawal_records(scenarios)
            ),
            "chinese_feedback": [
                "报告样例、快照、质量评分和影响分析均为控制引用，等待业务线白箱复核。",
                "关键结论保持 evidence_id 或 evidence_gap 严格二选一，外部增强保持外部来源语义。",
                "报告模板限制、人工确认和最终结论保持受控，未生成真实报告或 PDF。",
                "重新生成与撤回说明固定返回 Stage106 P3 的可验证控制目标。",
            ],
        }
    )
    if not _delivery_shape_is_valid(report):
        return _failure_report("DELIVERY_RECORD_SHAPE_MISMATCH")
    if not _delivery_references_are_opaque(report):
        return _failure_report("DELIVERY_REFERENCE_NOT_OPAQUE")
    if not _template_and_confirmation_is_valid(report, scenarios):
        return _failure_report("REPORT_TEMPLATE_AND_HUMAN_CONFIRMATION_CONTROL_MISSING")
    if not _regeneration_and_withdrawal_is_valid(report, scenarios):
        return _failure_report("REPORT_REGENERATION_AND_WITHDRAWAL_CONTROL_MISSING")
    failure = _delivery_execution_boundary_failure(report)
    if failure is not None:
        return _failure_report(failure)
    return report
