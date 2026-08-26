"""Stage110 报告质量评分的纯内存整阶段机械复审。

模块只复审冻结任务包与 Stage110 P1--P4 已提交的控制合同和纯内存报告。
它不读取业务资料、真实报告、PDF、证据账本、审计或数据库，不调用模型、Agent、
OVH 或生产服务，也不创建持久化记录。
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage110.report_quality_score.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REPORT_QUALITY_SCORE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REPORT_QUALITY_SCORE_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE110-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE111-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage110.report_quality_score.phase1.v1"
P1_CONTRACT_STATE = "REPORT_QUALITY_SCORE_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage110.report_quality_score.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE"
P2_PASS_RESULT = "PASS_IN_MEMORY_REPORT_QUALITY_SCORE_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage110.report_quality_score.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_SCENARIOS"
P3_PASS_RESULT = "PASS_REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage110.report_quality_score.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage110_report_quality_score_contract.json")
P2_MODULE_PATH = Path(__file__).with_name("stage110_report_quality_score_control_slice.py")
P3_MODULE_PATH = Path(__file__).with_name(
    "stage110_report_quality_score_controlled_scenarios.py"
)
P4_MODULE_PATH = Path(__file__).with_name("stage110_report_quality_score_delivery.py")

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 40,
    "phase1_snapshot_component_count": 5,
    "phase1_quality_metric_control_field_count": 10,
    "phase1_failure_state_count": 30,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 42,
    "phase2_phase1_reference_field_count": 40,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 126,
    "phase2_control_field_check_count": 630,
    "phase2_failure_state_count": 42,
    "phase2_chinese_feedback_count": 4,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 52,
    "phase3_scenario_field_check_count": 260,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 5,
    "phase3_whitebox_confirmation_required_count": 2,
    "phase3_quality_whitebox_confirmation_required_count": 1,
    "phase3_failure_state_count": 21,
    "phase3_chinese_feedback_count": 4,
    "phase4_delivery_shape": "5/5/5/5/5/2",
    "phase4_delivery_field_shape": "17/13/13/15/14/14",
    "phase4_delivery_field_check_count": 388,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 17,
    "critical_conclusion_evidence_binding_required": True,
    "citation_source_and_page_control_required": True,
    "generation_snapshot_control_required": True,
    "quality_metric_control_required": True,
    "external_augmentation_source_separation_required": True,
    "report_status_impact_control_required": True,
    "business_line_whitebox_confirmation_required": True,
    "phase4_to_phase3_rollback_required": True,
}

FAILURE_STATES = (
    "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "CONTROLLED_REVIEW_SHAPE_MISMATCH",
    "SINGLE_AUTHORITY_BOUNDARY_BREACH",
    "EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH",
    "REPORT_STATUS_AND_QUALITY_SEMANTICS_MISMATCH",
    "REPORT_LIFECYCLE_WHITEBOX_BOUNDARY_MISMATCH",
    "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_STAGE111_ENTRY_DETECTED",
)

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "model_reasoning_evaluated",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "cited_material_update_evaluated",
    "source_withdrawal_evaluated",
    "evidence_downgrade_evaluated",
    "index_version_change_evaluated",
    "affected_report_identification_performed",
    "internal_evidence_coverage_calculation_performed",
    "citation_completeness_calculation_performed",
    "external_augmentation_ratio_calculation_performed",
    "evidence_gap_count_calculation_performed",
    "quality_formula_weight_threshold_evaluated",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "snapshot_persistence_performed",
    "report_status_impact_analysis_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_or_withdrawal_performed",
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
    "stage110_review_runtime_executed",
    "stage111_runtime_started",
)

REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_external_reference_access_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_report_generation_count",
    "actual_snapshot_persistence_count",
    "actual_report_status_impact_analysis_count",
    "actual_internal_evidence_coverage_calculation_count",
    "actual_citation_completeness_calculation_count",
    "actual_external_augmentation_ratio_calculation_count",
    "actual_evidence_gap_count_calculation_count",
    "actual_report_quality_score_calculation_count",
    "actual_report_export_audit_write_count",
    "actual_report_regeneration_count",
    "actual_report_withdrawal_count",
    "actual_human_confirmation_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

P2_PROJECTION_GROUPS = (
    ("report_evidence_binding_and_section_control_projections", 5, 22),
    ("generation_snapshot_control_projections", 5, 11),
    ("report_quality_score_and_lifecycle_control_projections", 5, 69),
    ("external_augmentation_and_whitebox_gate_control_projections", 5, 24),
)

P4_DELIVERY_GROUPS = (
    ("report_sample_control_records", 5, 17),
    ("report_snapshot_control_records", 5, 13),
    ("report_quality_score_control_records", 5, 13),
    ("report_impact_analysis_control_records", 5, 15),
    ("report_template_and_whitebox_confirmation_control_records", 5, 14),
    ("regeneration_and_withdrawal_control_records", 2, 14),
)

OPERATOR_FEEDBACK = (
    "报告质量评分整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "关键结论继续保持 evidence_id 或 evidence_gap 的严格二选一。",
    "质量指标、报告状态影响、人工确认和最终结论保持业务线白箱门禁。",
    "真实资料、报告、模型、Agent、OVH、生产和正式上传保持未执行。",
)

Phase1Provider = Callable[[], Mapping[str, Any]]
PhaseProvider = Callable[[], Mapping[str, Any]]


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_phase1_contract() -> Mapping[str, Any]:
    return json.loads(P1_CONTRACT_PATH.read_text(encoding="utf-8"))


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module(P2_MODULE_PATH, "stage110_phase2_for_stage_review")
    return module.execute_report_quality_score_control_slice(module.build_control_input())


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module(P3_MODULE_PATH, "stage110_phase3_for_stage_review")
    return module.build_report_quality_score_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module(P4_MODULE_PATH, "stage110_phase4_for_stage_review")
    return module.build_report_quality_score_phase4_delivery_report()


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in REVIEW_ZERO_COUNT_FIELDS}


def _base_report(valid: bool, failure_state: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if valid else REVIEW_GATE,
        "phase1_static_contract_reviewed": False,
        "phase2_control_slice_reviewed": False,
        "phase3_controlled_scenarios_reviewed": False,
        "phase4_delivery_evidence_reviewed": False,
        "control_references_opaque": False,
        "single_authority_boundary_preserved": False,
        "report_quality_semantics_preserved": False,
        "business_line_whitebox_gate_preserved": False,
        "phase4_to_phase3_rollback_preserved": False,
        "stage110_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "stage111_started": False,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "reviewed_control_shape": {},
        "reviewed_phase_results": {},
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
        "chinese_feedback": [],
    }


def _all_false(mapping: object) -> bool:
    return (
        isinstance(mapping, Mapping)
        and bool(mapping)
        and all(value is False for value in mapping.values())
    )


def _all_runtime_closed(report: Mapping[str, Any]) -> bool:
    return _all_false(report.get("runtime_boundary")) and all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _phase1_valid(contract: Mapping[str, Any]) -> bool:
    source = contract.get("source_authority")
    quality = contract.get("quality_metric_definition_contract")
    snapshot = contract.get("generation_snapshot_contract")
    score = contract.get("report_quality_score_control_contract")
    failure = contract.get("failure_and_stop_contract")
    feedback = contract.get("chinese_feedback_contract")
    boundary = contract.get("stage_and_phase_boundary")
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("phase") == "IDS-STAGE110-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE110-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE110-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE110-P2-GATE",
            isinstance(source, Mapping),
            source.get("source_document_remains_authoritative") is True,
            source.get("evidence_ledger_remains_authoritative") is True,
            source.get("delivered_report_remains_authoritative") is True,
            source.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            source.get("second_authoritative_source_created") is False,
            isinstance(score, Mapping),
            score.get("future_control_reference_field_count") == 40,
            score.get(
                "critical_conclusion_requires_evidence_id_or_evidence_gap_independently"
            )
            is True,
            score.get("evidence_grade_required_for_future_quality_control") is True,
            score.get("citation_source_and_page_required_in_future_pdf_report") is True,
            score.get("external_augmentation_retains_underlying_source_types") is True,
            score.get(
                "external_augmentation_may_not_be_presented_as_internal_project_evidence"
            )
            is True,
            score.get("external_augmentation_may_not_close_evidence_gap") is True,
            isinstance(snapshot, Mapping),
            snapshot.get("required_future_snapshot_component_count") == 5,
            isinstance(quality, Mapping),
            quality.get("required_quality_metric_control_field_count") == 10,
            isinstance(failure, Mapping),
            failure.get("failure_state_count") == 30,
            isinstance(feedback, Mapping),
            feedback.get("feedback_count") == 4,
            _all_false(contract.get("runtime_boundary")),
            isinstance(boundary, Mapping),
            boundary.get("phase1_completed") is True,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage111_started") is False,
            boundary.get("github_upload_allowed") is False,
            boundary.get("push_allowed") is False,
        )
    )


def _phase2_valid(report: Mapping[str, Any]) -> bool:
    groups_valid = all(
        isinstance(report.get(name), list)
        and len(report[name]) == expected_count
        and all(
            isinstance(record, Mapping) and len(record) == expected_fields
            for record in report[name]
        )
        for name, expected_count, expected_fields in P2_PROJECTION_GROUPS
    )
    return all(
        (
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("control_input_count") == 5,
            report.get("control_projection_group_count") == 4,
            report.get("control_projection_field_total_per_request") == 126,
            report.get("control_projection_field_total") == 630,
            report.get("persistent_record_created") is False,
            groups_valid,
            _all_runtime_closed(report),
        )
    )


def _scenario_semantics_valid(scenario: Mapping[str, Any]) -> bool:
    evidence_id = scenario.get("evidence_id_ref")
    evidence_gap = scenario.get("evidence_gap_ref")
    return all(
        (
            (evidence_id is None) != (evidence_gap is None),
            scenario.get("evidence_binding_integrity_state")
            == "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
            scenario.get("source_withdrawal_report_status_impact_state")
            in {
                "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_SOURCE_WITHDRAWAL_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            },
            scenario.get("evidence_downgrade_report_status_impact_state")
            in {
                "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_EVIDENCE_DOWNGRADE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            },
            scenario.get("index_version_change_report_status_impact_state")
            in {
                "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
                "CONTROL_INDEX_VERSION_CHANGE_NOT_TRIGGERED_IN_THIS_CONTROL_SCENARIO",
            },
            scenario.get("quality_metric_boundary_state")
            == "CONTROL_QUALITY_METRICS_REFERENCE_ONLY_NOT_CALCULATED",
            scenario.get("quality_score_boundary_state")
            in {
                "CONTROL_QUALITY_SCORE_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED",
                "CONTROL_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED",
            },
            scenario.get("external_augmentation_source_separation_state")
            == "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
            "SEPARATE_FROM_INTERNAL_EVIDENCE",
            scenario.get("external_augmentation_may_not_be_internal_project_evidence")
            is True,
            scenario.get("external_augmentation_may_not_replace_evidence_binding")
            is True,
            scenario.get("external_augmentation_may_not_close_evidence_gap") is True,
            scenario.get("human_confirmation_state")
            in {
                "CONTROL_WHITEBOX_GATE_PRESENT_NOT_EXECUTED",
                "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED",
            },
            scenario.get("automatic_final_conclusion_allowed") is False,
            scenario.get("actual_report_quality_scored") is False,
            scenario.get("actual_report_status_impact_updated") is False,
            scenario.get("actual_external_augmentation_displayed") is False,
            scenario.get("actual_human_confirmation_recorded") is False,
            scenario.get("actual_final_conclusion_published") is False,
            scenario.get("expectation_met") is True,
        )
    )


def _phase3_valid(report: Mapping[str, Any]) -> bool:
    scenarios = report.get("scenario_results")
    views = report.get("control_views")
    handlings = report.get("human_handlings")
    return all(
        (
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE110-P3-GATE",
            report.get("next_gate") == "IDS-STAGE110-P4-GATE",
            report.get("phase2_control_request_count") == 5,
            report.get("phase2_input_field_count") == 42,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 126,
            report.get("phase2_projection_field_count_total") == 630,
            report.get("scenario_count") == 5,
            report.get("scenario_field_count") == 52,
            report.get("scenario_field_check_count") == 260,
            report.get("control_view_count") == 5,
            report.get("human_handling_count") == 5,
            isinstance(scenarios, list),
            len(scenarios) == 5,
            all(isinstance(item, Mapping) and len(item) == 52 for item in scenarios),
            all(_scenario_semantics_valid(item) for item in scenarios),
            isinstance(views, Mapping),
            len(views) == 5,
            all(isinstance(items, list) and len(items) == 5 for items in views.values()),
            isinstance(handlings, list),
            len(handlings) == 5,
            sum(
                item.get("whitebox_confirmation_required") is True
                for item in handlings
            )
            == 2,
            sum(
                item.get("quality_whitebox_confirmation_required") is True
                for item in handlings
            )
            == 1,
            all(
                item.get("human_confirmation_recorded") is False
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                for item in handlings
            ),
            report.get("phase2_control_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _all_runtime_closed(report),
        )
    )


def _report_quality_semantics_valid(scenarios: list[Mapping[str, Any]]) -> bool:
    return all(
        (
            "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED"
            in {item.get("source_withdrawal_report_status_impact_state") for item in scenarios},
            "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED"
            in {item.get("evidence_downgrade_report_status_impact_state") for item in scenarios},
            "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED"
            in {item.get("index_version_change_report_status_impact_state") for item in scenarios},
            "CONTROL_QUALITY_SCORE_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
            in {item.get("quality_score_boundary_state") for item in scenarios},
        )
    )


def _delivery_semantics_valid(report: Mapping[str, Any]) -> bool:
    samples = report.get("report_sample_control_records")
    quality_records = report.get("report_quality_score_control_records")
    templates = report.get(
        "report_template_and_whitebox_confirmation_control_records"
    )
    lifecycle = report.get("regeneration_and_withdrawal_control_records")
    return all(
        (
            isinstance(samples, list),
            all(
                (item.get("evidence_id_ref") is None)
                != (item.get("evidence_gap_ref") is None)
                and item.get("automatic_final_conclusion_allowed") is False
                and item.get("actual_report_sample_rendered") is False
                for item in samples
            ),
            isinstance(quality_records, list),
            sum(
                item.get("quality_whitebox_confirmation_required") is True
                for item in quality_records
            )
            == 1,
            all(
                item.get("quality_score_delivery_state")
                == "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED"
                and item.get("actual_report_quality_score_calculated") is False
                for item in quality_records
            ),
            isinstance(templates, list),
            sum(
                item.get("business_line_whitebox_confirmation_required") is True
                for item in templates
            )
            == 2,
            all(
                item.get("automatic_final_conclusion_allowed") is False
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and item.get("actual_human_confirmation_performed") is False
                for item in templates
            ),
            isinstance(lifecycle, list),
            {item.get("control_domain") for item in lifecycle}
            == {"REPORT_REGENERATION", "REPORT_WITHDRAWAL"},
            all(
                item.get("rollback_target_result") == P3_PASS_RESULT
                and item.get("business_line_whitebox_confirmation_required") is True
                and item.get("human_confirmation_required") is True
                and item.get("versioned_basis_required") is True
                and item.get("verifiable_rollback_target_required") is True
                and item.get("actual_report_regeneration_performed") is False
                and item.get("actual_report_withdrawal_performed") is False
                and item.get("persistent_state_write_performed") is False
                for item in lifecycle
            ),
        )
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    groups_valid = all(
        isinstance(report.get(name), list)
        and len(report[name]) == expected_count
        and all(
            isinstance(record, Mapping) and len(record) == expected_fields
            for record in report[name]
        )
        for name, expected_count, expected_fields in P4_DELIVERY_GROUPS
    )
    return all(
        (
            report.get("schema_version") == P4_SCHEMA_VERSION,
            report.get("record_kind") == P4_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE110-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase2_control_request_count") == 5,
            report.get("phase2_input_field_count") == 42,
            report.get("phase2_phase1_reference_field_count") == 40,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 126,
            report.get("phase2_projection_field_count_total") == 630,
            report.get("scenario_count") == 5,
            report.get("scenario_field_count") == 52,
            report.get("scenario_field_check_count") == 260,
            report.get("control_view_count") == 5,
            report.get("human_handling_count") == 5,
            report.get("whitebox_confirmation_required_scenario_count") == 2,
            report.get("quality_whitebox_confirmation_required_scenario_count") == 1,
            report.get("delivery_field_check_count") == 388,
            report.get("failure_state_count") == 17,
            isinstance(report.get("operator_feedback"), list),
            len(report["operator_feedback"]) == 4,
            report.get("phase3_control_shape_preserved") is True,
            report.get("phase3_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            groups_valid,
            _delivery_semantics_valid(report),
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _all_runtime_closed(report),
        )
    )


def build_report_quality_score_stage_review(
    phase1_contract_provider: Phase1Provider | None = None,
    phase2_provider: PhaseProvider | None = None,
    phase3_provider: PhaseProvider | None = None,
    phase4_provider: PhaseProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage110 P1--P4 控制工件，漂移时保持失败关闭。"""

    providers = (
        (
            phase1_contract_provider or _default_phase1_contract,
            _phase1_valid,
            "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        ),
        (
            phase2_provider or _default_phase2_report,
            _phase2_valid,
            "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        ),
        (
            phase3_provider or _default_phase3_report,
            _phase3_valid,
            "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        ),
        (
            phase4_provider or _default_phase4_report,
            _phase4_valid,
            "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        ),
    )
    outputs: list[Mapping[str, Any]] = []
    for provider, validator, failure_state in providers:
        try:
            output = provider()
        except Exception:
            return _base_report(False, failure_state)
        if not isinstance(output, Mapping) or not validator(output):
            return _base_report(False, failure_state)
        outputs.append(output)

    phase1, _phase2, phase3, phase4 = outputs
    source = phase1["source_authority"]
    if not all(
        (
            source["source_document_remains_authoritative"],
            source["evidence_ledger_remains_authoritative"],
            source["delivered_report_remains_authoritative"],
            source["business_line_whitebox_human_review_remains_authoritative"],
            source["second_authoritative_source_created"] is False,
            phase4["control_references_opaque"],
        )
    ):
        return _base_report(False, "SINGLE_AUTHORITY_BOUNDARY_BREACH")
    scenarios = phase3["scenario_results"]
    if not all(_scenario_semantics_valid(item) for item in scenarios):
        return _base_report(False, "EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH")
    if not _report_quality_semantics_valid(scenarios):
        return _base_report(False, "REPORT_STATUS_AND_QUALITY_SEMANTICS_MISMATCH")
    if not _delivery_semantics_valid(phase4):
        return _base_report(False, "REPORT_LIFECYCLE_WHITEBOX_BOUNDARY_MISMATCH")
    if any(
        item["rollback_target_result"] != P3_PASS_RESULT
        for item in phase4["regeneration_and_withdrawal_control_records"]
    ):
        return _base_report(False, "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH")

    report = _base_report(True, None)
    report.update(
        {
            "phase1_static_contract_reviewed": True,
            "phase2_control_slice_reviewed": True,
            "phase3_controlled_scenarios_reviewed": True,
            "phase4_delivery_evidence_reviewed": True,
            "control_references_opaque": True,
            "single_authority_boundary_preserved": True,
            "report_quality_semantics_preserved": True,
            "business_line_whitebox_gate_preserved": True,
            "phase4_to_phase3_rollback_preserved": True,
            "stage110_review_started": True,
            "whole_stage_review_completed_in_memory_only": True,
            "reviewed_control_shape": dict(REVIEWED_CONTROL_SHAPE),
            "reviewed_phase_results": {
                "phase1_contract_state": P1_CONTRACT_STATE,
                "phase2_control_slice_result": P2_PASS_RESULT,
                "phase3_controlled_scenarios_result": P3_PASS_RESULT,
                "phase4_delivery_evidence_result": P4_PASS_RESULT,
            },
            "chinese_feedback": list(OPERATOR_FEEDBACK),
        }
    )
    return report
