"""Stage108 报告快照的纯内存整阶段机械复审。

本模块只复审冻结任务包和 Stage108 P1--P4 已提交的控制合同与纯内存报告。
它不读取业务资料、真实报告、PDF、证据账本、审计或数据库，不调用模型、Agent、
OVH 或生产服务，也不创建持久化记录。
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage108.report_snapshot.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_SNAPSHOT_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_REPORT_SNAPSHOT_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_REPORT_SNAPSHOT_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE108-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE109-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage108.report_snapshot.phase1.v1"
P1_CONTRACT_STATE = "REPORT_SNAPSHOT_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage108.report_snapshot.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_SNAPSHOT"
P2_PASS_RESULT = "PASS_IN_MEMORY_REPORT_SNAPSHOT_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage108.report_snapshot.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_SNAPSHOT_SCENARIOS"
P3_PASS_RESULT = "PASS_REPORT_SNAPSHOT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage108.report_snapshot.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_SNAPSHOT_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_REPORT_SNAPSHOT_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_CONTRACT_PATH = Path(__file__).with_name("stage108_report_snapshot_contract.json")
P2_MODULE_PATH = Path(__file__).with_name("stage108_report_snapshot_control_slice.py")
P3_MODULE_PATH = Path(__file__).with_name("stage108_report_snapshot_controlled_scenarios.py")
P4_MODULE_PATH = Path(__file__).with_name("stage108_report_snapshot_delivery.py")

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 24,
    "phase1_snapshot_component_count": 5,
    "phase1_failure_state_count": 23,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 26,
    "phase2_phase1_reference_field_count": 24,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 82,
    "phase2_control_field_check_count": 410,
    "phase2_failure_state_count": 22,
    "phase2_chinese_feedback_count": 4,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 39,
    "phase3_scenario_field_check_count": 195,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 5,
    "phase3_whitebox_confirmation_required_count": 2,
    "phase3_failure_state_count": 15,
    "phase3_chinese_feedback_count": 4,
    "phase4_delivery_shape": "5/5/5/5/5/2",
    "phase4_delivery_field_shape": "17/13/13/15/14/14",
    "phase4_delivery_field_check_count": 388,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 17,
    "critical_conclusion_evidence_binding_required": True,
    "citation_source_and_page_control_required": True,
    "generation_snapshot_control_required": True,
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
    "REPORT_LIFECYCLE_WHITEBOX_BOUNDARY_MISMATCH",
    "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_STAGE109_ENTRY_DETECTED",
)

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "model_reasoning_evaluated",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
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
    "stage108_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_external_reference_access_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_report_generation_count",
    "actual_snapshot_persistence_count",
    "actual_report_status_impact_analysis_count",
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
    ("report_lifecycle_control_projections", 5, 25),
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
    "报告快照整阶段复审完成：当前只确认冻结控制工件的一致性。",
    "关键结论继续保持 evidence_id 或 evidence_gap 的严格二选一。",
    "报告状态影响、人工确认、最终结论和重新生成保持业务线白箱门禁。",
    "真实资料、报告、模型、Agent、OVH、生产和正式上传保持未执行。",
)

Phase1Provider = Callable[[], Mapping[str, Any]]
PhaseProvider = Callable[[], Mapping[str, Any]]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_phase1_contract() -> Mapping[str, Any]:
    return json.loads(P1_CONTRACT_PATH.read_text(encoding="utf-8"))


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module(P2_MODULE_PATH, "stage108_phase2_for_stage_review")
    return module.execute_report_snapshot_control_slice(module.build_control_input())


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module(P3_MODULE_PATH, "stage108_phase3_for_stage_review")
    return module.build_report_snapshot_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module(P4_MODULE_PATH, "stage108_phase4_for_stage_review")
    return module.build_report_snapshot_phase4_delivery_report()


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
        "business_line_whitebox_gate_preserved": False,
        "phase4_to_phase3_rollback_preserved": False,
        "stage108_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "stage109_started": False,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "reviewed_control_shape": {},
        "reviewed_phase_results": {},
        "runtime_boundary": _runtime_boundary(),
        **_zero_actual_counts(),
        "chinese_feedback": [],
    }


def _all_runtime_closed(report: Mapping[str, Any]) -> bool:
    boundary = report.get("runtime_boundary")
    return (
        isinstance(boundary, Mapping)
        and bool(boundary)
        and all(value is False for value in boundary.values())
        and all(
            value == 0
            for key, value in report.items()
            if key.startswith("actual_") and key.endswith("_count")
        )
    )


def _all_false(mapping: object) -> bool:
    return (
        isinstance(mapping, Mapping)
        and bool(mapping)
        and all(value is False for value in mapping.values())
    )


def _phase1_valid(contract: Mapping[str, Any]) -> bool:
    source = contract.get("source_authority")
    snapshot = contract.get("generation_snapshot_contract")
    report_snapshot = contract.get("report_snapshot_contract")
    delivery = contract.get("report_delivery_control_contract")
    failure = contract.get("failure_and_stop_contract")
    feedback = contract.get("chinese_feedback_contract")
    boundary = contract.get("stage_and_phase_boundary")
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("phase") == "IDS-STAGE108-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE108-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE108-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE108-P2-GATE",
            isinstance(source, Mapping),
            source.get("source_document_remains_authoritative") is True,
            source.get("evidence_ledger_remains_authoritative") is True,
            source.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            source.get("second_authoritative_source_created") is False,
            isinstance(report_snapshot, Mapping),
            report_snapshot.get("future_control_reference_field_count") == 24,
            report_snapshot.get(
                "critical_conclusion_requires_evidence_id_or_evidence_gap_independently"
            )
            is True,
            report_snapshot.get("citation_source_and_page_required_in_future_pdf_report")
            is True,
            report_snapshot.get(
                "external_augmentation_may_not_be_presented_as_internal_project_evidence"
            )
            is True,
            report_snapshot.get("external_augmentation_may_not_close_evidence_gap")
            is True,
            isinstance(snapshot, Mapping),
            snapshot.get("required_future_snapshot_component_count") == 5,
            isinstance(delivery, Mapping),
            delivery.get("human_confirmation_required_before_future_final_conclusion")
            is True,
            isinstance(failure, Mapping),
            failure.get("failure_state_count") == 23,
            isinstance(feedback, Mapping),
            feedback.get("feedback_count") == 4,
            _all_false(contract.get("runtime_boundary")),
            isinstance(boundary, Mapping),
            boundary.get("phase1_completed") is True,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage109_started") is False,
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
            report.get("control_projection_field_total_per_request") == 82,
            report.get("control_projection_field_total") == 410,
            report.get("persistent_record_created") is False,
            groups_valid,
            _all_runtime_closed(report),
        )
    )


def _scenario_semantics_valid(scenario: Mapping[str, Any]) -> bool:
    evidence_id = scenario.get("evidence_id_ref")
    evidence_gap = scenario.get("evidence_gap_ref")
    status_trigger = scenario.get("report_status_impact_trigger")
    status_values = (
        (
            status_trigger
            == "CONTROL_MATERIAL_WITHDRAWAL_EVIDENCE_DOWNGRADE_INDEX_VERSION_CHANGE"
            and scenario.get("report_status_impact_state")
            == "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED"
            and scenario.get("material_withdrawal_state")
            == "CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS"
            and scenario.get("evidence_grade_downgrade_state")
            == "CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS"
            and scenario.get("index_version_change_state")
            == "CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS"
        )
        or (
            status_trigger == "CONTROL_REPORT_STATUS_IMPACT_NOT_EVALUATED"
            and scenario.get("report_status_impact_state")
            == "CONTROL_FUTURE_REPORT_STATUS_REMAINS_UNCHANGED"
            and scenario.get("material_withdrawal_state")
            == "CONTROL_MATERIAL_WITHDRAWAL_NOT_APPLICABLE"
            and scenario.get("evidence_grade_downgrade_state")
            == "CONTROL_EVIDENCE_GRADE_DOWNGRADE_NOT_APPLICABLE"
            and scenario.get("index_version_change_state")
            == "CONTROL_INDEX_VERSION_CHANGE_NOT_APPLICABLE"
        )
    )
    return all(
        (
            (evidence_id is None) != (evidence_gap is None),
            scenario.get("evidence_binding_integrity_state")
            == "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
            status_values,
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
            scenario.get("actual_report_status_impact_analysis_performed") is False,
            scenario.get("actual_external_augmentation_displayed") is False,
            scenario.get("actual_human_confirmation_recorded") is False,
            scenario.get("actual_final_conclusion_published") is False,
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
            report.get("current_gate") == "IDS-STAGE108-P3-GATE",
            report.get("next_gate") == "IDS-STAGE108-P4-GATE",
            report.get("phase2_control_request_count") == 5,
            report.get("phase2_input_field_count") == 26,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 82,
            report.get("phase2_projection_field_count_total") == 410,
            report.get("scenario_count") == 5,
            report.get("scenario_field_count") == 39,
            report.get("scenario_field_check_count") == 195,
            report.get("control_view_count") == 5,
            report.get("human_handling_count") == 5,
            isinstance(scenarios, list),
            len(scenarios) == 5,
            all(isinstance(item, Mapping) and len(item) == 39 for item in scenarios),
            all(_scenario_semantics_valid(item) for item in scenarios),
            isinstance(views, Mapping),
            len(views) == 5,
            isinstance(handlings, list),
            len(handlings) == 5,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _all_runtime_closed(report),
        )
    )


def _delivery_semantics_valid(report: Mapping[str, Any]) -> bool:
    samples = report.get("report_sample_control_records")
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
            isinstance(templates, list),
            all(
                item.get("business_line_whitebox_confirmation_required") is True
                and item.get("automatic_final_conclusion_allowed") is False
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
            report.get("current_gate") == "IDS-STAGE108-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase2_control_request_count") == 5,
            report.get("phase2_input_field_count") == 26,
            report.get("phase2_phase1_reference_field_count") == 24,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 82,
            report.get("phase2_projection_field_count_total") == 410,
            report.get("scenario_count") == 5,
            report.get("scenario_field_count") == 39,
            report.get("scenario_field_check_count") == 195,
            report.get("control_view_count") == 5,
            report.get("human_handling_count") == 5,
            report.get("whitebox_confirmation_required_scenario_count") == 2,
            report.get("delivery_field_check_count") == 388,
            report.get("failure_state_count") == 17,
            isinstance(report.get("operator_feedback"), list),
            len(report["operator_feedback"]) == 4,
            report.get("phase3_controlled_scenarios_replayed_in_memory_only")
            is True,
            report.get("phase3_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            groups_valid,
            _delivery_semantics_valid(report),
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _all_runtime_closed(report),
        )
    )


def build_report_snapshot_stage_review(
    phase1_contract_provider: Phase1Provider | None = None,
    phase2_provider: PhaseProvider | None = None,
    phase3_provider: PhaseProvider | None = None,
    phase4_provider: PhaseProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage108 P1--P4 控制工件，漂移时保持失败关闭。"""

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
            source["business_line_whitebox_human_review_remains_authoritative"],
            source["second_authoritative_source_created"] is False,
            phase4["control_references_opaque"],
        )
    ):
        return _base_report(False, "SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not all(_scenario_semantics_valid(item) for item in phase3["scenario_results"]):
        return _base_report(False, "EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH")
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
            "business_line_whitebox_gate_preserved": True,
            "phase4_to_phase3_rollback_preserved": True,
            "stage108_review_started": True,
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
