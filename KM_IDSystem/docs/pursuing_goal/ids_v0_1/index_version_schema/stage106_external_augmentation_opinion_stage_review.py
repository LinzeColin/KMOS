"""Stage106 外部增强意见章节的纯内存整阶段机械复审。

本模块只复审冻结任务包和 Stage106 P1--P4 已提交的控制合同与纯内存报告。
它不读取业务资料、真实报告、PDF、证据账本、审计或数据库，不调用模型、Agent、
OVH 或生产服务，也不创建持久化记录。
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_EXTERNAL_AUGMENTATION_OPINION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_EXTERNAL_AUGMENTATION_OPINION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE106-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE107-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase1.v1"
P1_CONTRACT_STATE = "EXTERNAL_AUGMENTATION_OPINION_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION"
P2_PASS_RESULT = "PASS_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_SCENARIOS"
P3_PASS_RESULT = "PASS_EXTERNAL_AUGMENTATION_OPINION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage106.external_augmentation_opinion.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P2_CONTROL_PREFIX = ":control:stage106-p2:"
P4_DELIVERY_PREFIX = ":control:stage106-p4:"

P1_REFERENCE_FIELDS = (
    "report_id_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_item_ref",
    "external_augmentation_display_label_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "citation_source_ref",
    "citation_page_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_and_withdrawal_ref",
    "audit_boundary_ref",
)
P1_SNAPSHOT_COMPONENTS = (
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
)
P3_SCENARIO_IDS = (
    "critical_conclusion_evidence_id_binding_integrity_control",
    "critical_conclusion_evidence_gap_binding_integrity_control",
    "external_augmentation_retains_external_source_type_control",
    "human_confirmation_gate_keeps_final_conclusion_unpublished_control",
    "withdrawal_downgrade_and_index_change_impact_report_status_control",
)
P3_HUMAN_HANDLING_FIELDS = (
    "scenario_id",
    "scenario_category",
    "business_line_whitebox_handling_code",
    "whitebox_confirmation_required",
    "human_confirmation_recorded",
    "final_conclusion_state",
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 27,
    "phase1_snapshot_component_count": 5,
    "phase1_failure_state_count": 22,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_input_field_count": 30,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 74,
    "phase2_control_field_check_count": 370,
    "phase2_failure_state_count": 20,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 34,
    "phase3_scenario_field_check_count": 170,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 5,
    "phase3_failure_state_count": 15,
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

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "external_augmentation_opinion_performed",
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
    "stage106_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_report_or_pdf_access_count",
    "actual_evidence_ledger_access_count",
    "actual_external_augmentation_opinion_count",
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
    "RUNTIME_SIGNAL_OR_STAGE107_ENTRY_DETECTED",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage106_external_augmentation_opinion_contract.json"
P2_CONTRACT_PATH = BASE / "stage106_external_augmentation_opinion_control_slice_contract.json"
P3_CONTRACT_PATH = BASE / "stage106_external_augmentation_opinion_controlled_scenarios_contract.json"
P4_CONTRACT_PATH = BASE / "stage106_external_augmentation_opinion_delivery_contract.json"
P2_MODULE_PATH = BASE / "stage106_external_augmentation_opinion_control_slice.py"
P3_MODULE_PATH = BASE / "stage106_external_augmentation_opinion_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage106_external_augmentation_opinion_delivery.py"


def _load_module(module_name: str, source: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {source.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(source: Path) -> Mapping[str, Any]:
    value = json.loads(source.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in REVIEW_ZERO_COUNT_FIELDS}


def _closed_runtime(value: object) -> bool:
    boundary = _mapping(value)
    return bool(boundary) and all(item is False for item in boundary.values())


def _zero_actual_counts_in(value: Mapping[str, Any]) -> bool:
    return all(
        item == 0
        for key, item in value.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _opaque_p2(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P2_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _opaque_p4(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P4_DELIVERY_PREFIX)
        and value.endswith(":reference-only")
    )


def _opaque_reference(value: object) -> bool:
    return _opaque_p2(value) or _opaque_p4(value)


def _records_have_shape(
    records: object, fields: tuple[str, ...], count: int
) -> bool:
    return (
        isinstance(records, list)
        and len(records) == count
        and all(isinstance(record, Mapping) and set(record) == set(fields) for record in records)
    )


def _contract_boundary_closed(contract: Mapping[str, Any]) -> bool:
    return (
        _closed_runtime(contract.get("runtime_boundary"))
        and all(
            value is False
            for value in _mapping(contract.get("protected_surface_boundary")).values()
        )
    )


def _p1_shape_valid(contract: Mapping[str, Any]) -> bool:
    report = _mapping(contract.get("external_augmentation_opinion_contract"))
    snapshot = _mapping(contract.get("generation_snapshot_contract"))
    lifecycle = _mapping(contract.get("human_confirmation_and_lifecycle_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("schema_version") == P1_SCHEMA_VERSION
        and contract.get("stage") == "STAGE-106"
        and contract.get("phase") == "IDS-STAGE106-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE106-P1"
        and contract.get("contract_state")
        == "EXTERNAL_AUGMENTATION_OPINION_CHAPTER_CONTRACT_RUNTIME_DISABLED"
        and contract.get("entry_gate") == "IDS-STAGE106-P1-GATE"
        and contract.get("next_gate") == "IDS-STAGE106-P2-GATE"
        and tuple(report.get("future_control_reference_fields", ())) == P1_REFERENCE_FIELDS
        and report.get("future_control_reference_field_count") == 27
        and report.get(
            "critical_conclusion_requires_evidence_id_or_evidence_gap_independently"
        )
        is True
        and report.get("citation_source_and_page_required_in_future_pdf_report") is True
        and tuple(snapshot.get("required_future_snapshot_components", ()))
        == P1_SNAPSHOT_COMPONENTS
        and snapshot.get("required_future_snapshot_component_count") == 5
        and report.get(
            "external_augmentation_may_not_be_presented_as_internal_project_evidence"
        )
        is True
        and report.get("external_augmentation_may_not_close_evidence_gap") is True
        and report.get(
            "external_augmentation_may_not_replace_evidence_id_or_evidence_gap"
        )
        is True
        and lifecycle.get(
            "business_line_whitebox_human_confirmation_required_before_final_conclusion"
        )
        is True
        and lifecycle.get("external_augmentation_may_not_create_final_conclusion")
        is True
        and lifecycle.get(
            "evidence_revocation_or_grade_or_index_change_requires_future_report_impact_review"
        )
        is True
        and boundary.get("stage105_review_evidence_declared") is True
        and boundary.get("stage106_entry_authorized") is True
        and boundary.get("stage106_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage107_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
    )


def _p2_contract_valid(contract: Mapping[str, Any]) -> bool:
    slice_contract = _mapping(contract.get("control_slice_contract"))
    external = _mapping(
        contract.get("external_augmentation_and_human_confirmation_contract")
    )
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("schema_version") == P2_SCHEMA_VERSION
        and contract.get("phase") == "IDS-STAGE106-P2"
        and contract.get("task_id") == "IDS-V0_1-STAGE106-P2"
        and contract.get("contract_state")
        == "EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE_RUNTIME_DISABLED"
        and contract.get("entry_gate") == "IDS-STAGE106-P2-GATE"
        and contract.get("next_gate") == "IDS-STAGE106-P3-GATE"
        and slice_contract.get("control_request_count") == 5
        and slice_contract.get("control_input_field_count") == 30
        and slice_contract.get("projection_group_count") == 4
        and slice_contract.get("projection_field_total_per_request") == 74
        and slice_contract.get("projection_field_total") == 370
        and slice_contract.get(
            "critical_conclusion_requires_exactly_one_evidence_id_or_evidence_gap_reference"
        )
        is True
        and slice_contract.get("generation_snapshot_component_count") == 5
        and external.get("external_augmentation_may_not_be_internal_project_evidence")
        is True
        and external.get("business_line_whitebox_confirmation_required_before_final_conclusion")
        is True
        and external.get("final_conclusion_may_not_be_automated") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage107_started") is False
        and _contract_boundary_closed(contract)
    )


def _p3_contract_valid(contract: Mapping[str, Any]) -> bool:
    scenario = _mapping(contract.get("controlled_scenario_contract"))
    taskpack = _mapping(contract.get("taskpack_special_validation_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return (
        contract.get("schema_version") == P3_SCHEMA_VERSION
        and contract.get("phase") == "IDS-STAGE106-P3"
        and contract.get("task_id") == "IDS-V0_1-STAGE106-P3"
        and contract.get("contract_state")
        == "EXTERNAL_AUGMENTATION_OPINION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and contract.get("entry_gate") == "IDS-STAGE106-P3-GATE"
        and contract.get("next_gate") == "IDS-STAGE106-P4-GATE"
        and scenario.get("scenario_count") == 5
        and scenario.get("scenario_field_count") == 34
        and scenario.get("scenario_field_check_count") == 170
        and scenario.get("control_view_count") == 5
        and scenario.get("human_handling_count") == 5
        and taskpack.get("critical_conclusion_requires_exactly_one_evidence_id_or_evidence_gap")
        is True
        and taskpack.get("material_withdrawal_impacts_report_status_control") is True
        and taskpack.get("evidence_grade_downgrade_impacts_report_status_control")
        is True
        and taskpack.get("index_version_change_impacts_report_status_control") is True
        and taskpack.get("external_augmentation_may_not_be_internal_project_evidence")
        is True
        and taskpack.get("business_line_whitebox_confirmation_required_before_final_conclusion")
        is True
        and boundary.get("phase3_completed") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage107_started") is False
        and _contract_boundary_closed(contract)
    )


def _p4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    taskpack = _mapping(contract.get("taskpack_delivery_contract"))
    rollback = _mapping(contract.get("rollback_contract"))
    boundary = _mapping(contract.get("stage_boundary"))
    return (
        contract.get("schema_version") == P4_SCHEMA_VERSION
        and contract.get("phase") == "IDS-STAGE106-P4"
        and contract.get("task_id") == "IDS-V0_1-STAGE106-P4"
        and contract.get("contract_state")
        == "EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and contract.get("entry_gate") == "IDS-STAGE106-P4-GATE"
        and contract.get("next_gate") == REVIEW_GATE
        and delivery.get("report_sample_control_record_count") == 5
        and delivery.get("report_snapshot_control_record_count") == 5
        and delivery.get("report_quality_score_control_record_count") == 5
        and delivery.get("report_impact_analysis_control_record_count") == 5
        and delivery.get(
            "report_template_and_whitebox_confirmation_control_record_count"
        )
        == 5
        and delivery.get("regeneration_and_withdrawal_control_record_count") == 2
        and delivery.get("report_sample_field_count_per_record") == 17
        and delivery.get("report_snapshot_field_count_per_record") == 13
        and delivery.get("report_quality_score_field_count_per_record") == 13
        and delivery.get("report_impact_analysis_field_count_per_record") == 15
        and delivery.get(
            "report_template_and_whitebox_confirmation_field_count_per_record"
        )
        == 14
        and delivery.get("regeneration_and_withdrawal_field_count_per_record") == 14
        and delivery.get("delivery_field_check_count") == 388
        and delivery.get("failure_state_count") == 17
        and delivery.get("chinese_feedback_count") == 4
        and delivery.get("delivery_metadata_only") is True
        and taskpack.get(
            "critical_conclusion_requires_exactly_one_evidence_id_or_evidence_gap"
        )
        is True
        and taskpack.get("external_augmentation_may_not_be_internal_project_evidence")
        is True
        and taskpack.get("external_augmentation_may_not_close_evidence_gap") is True
        and taskpack.get("automatic_final_conclusion_allowed") is False
        and taskpack.get("human_confirmation_recorded") is False
        and taskpack.get("final_conclusion_published") is False
        and rollback.get("return_to") == P3_PASS_RESULT
        and rollback.get("preserve_stage106_phase3_evidence") is True
        and rollback.get("stage106_review_execution_allowed") is False
        and boundary.get("phase4_completed") is True
        and boundary.get("stage106_review_started") is False
        and boundary.get("stage107_started") is False
        and _contract_boundary_closed(contract)
    )


def _p2_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    control_input = module.build_control_input()
    requests = control_input.get(module.CONTROL_FIELDS[0])
    if (
        getattr(module, "SCHEMA_VERSION", None) != P2_SCHEMA_VERSION
        or getattr(module, "RECORD_KIND", None) != P2_RECORD_KIND
        or getattr(module, "PASS_RESULT", None) != P2_PASS_RESULT
        or getattr(module, "CONTROL_PREFIX", None) != P2_CONTROL_PREFIX
        or not isinstance(requests, list)
        or len(requests) != 5
        or any(set(item) != set(module.INPUT_FIELDS) for item in requests)
        or report.get("schema_version") != P2_SCHEMA_VERSION
        or report.get("record_kind") != P2_RECORD_KIND
        or report.get("execution_state") != P2_PASS_RESULT
        or report.get("failure_state") is not None
        or report.get("input_accepted") is not True
        or report.get("control_input_count") != 5
        or report.get("control_projection_group_count") != 4
        or report.get("control_projection_field_total_per_request") != 74
        or report.get("control_projection_field_total") != 370
        or report.get("persistent_record_created") is not False
    ):
        return False
    for request in requests:
        if request["control_scenario"] not in module.CONTROL_SCENARIOS:
            return False
        if (request["evidence_id_ref"] is None) == (request["evidence_gap_ref"] is None):
            return False
        if any(
            not _opaque_p2(value)
            for key, value in request.items()
            if key.endswith("_ref") and value is not None
        ):
            return False
    for prefix, fields in module.PROJECTION_FIELDS:
        if not _records_have_shape(
            report.get(f"{prefix}_control_projections"), fields, 5
        ):
            return False
    return _closed_runtime(report.get("runtime_boundary")) and _zero_actual_counts_in(
        report
    )


def _p3_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    scenarios = report.get("scenario_results")
    views = _mapping(report.get("control_views"))
    handlings = report.get("human_handlings")
    if (
        getattr(module, "SCHEMA_VERSION", None) != P3_SCHEMA_VERSION
        or getattr(module, "RECORD_KIND", None) != P3_RECORD_KIND
        or getattr(module, "PASS_RESULT", None) != P3_PASS_RESULT
        or getattr(module, "CURRENT_GATE", None) != "IDS-STAGE106-P3-GATE"
        or getattr(module, "NEXT_GATE", None) != "IDS-STAGE106-P4-GATE"
        or report.get("schema_version") != P3_SCHEMA_VERSION
        or report.get("record_kind") != P3_RECORD_KIND
        or report.get("result") != P3_PASS_RESULT
        or report.get("valid") is not True
        or report.get("failure_state") is not None
        or report.get("current_gate") != "IDS-STAGE106-P3-GATE"
        or report.get("next_gate") != "IDS-STAGE106-P4-GATE"
        or report.get("scenario_count") != 5
        or report.get("scenario_field_count") != 34
        or report.get("scenario_field_check_count") != 170
        or report.get("control_view_count") != 5
        or report.get("human_handling_count") != 5
        or report.get("control_references_opaque") is not True
        or report.get("second_authoritative_source_created") is not False
        or report.get("persistent_record_created") is not False
        or not _records_have_shape(scenarios, module.SCENARIO_FIELDS, 5)
        or not _records_have_shape(handlings, P3_HUMAN_HANDLING_FIELDS, 5)
    ):
        return False
    if tuple(item["scenario_id"] for item in scenarios) != P3_SCENARIO_IDS:
        return False
    if set(views) != set(module.CONTROL_VIEW_FIELDS):
        return False
    for name, fields in module.CONTROL_VIEW_FIELDS.items():
        if not _records_have_shape(views[name], fields, 5):
            return False
    for scenario in scenarios:
        if (scenario["evidence_id_ref"] is None) == (
            scenario["evidence_gap_ref"] is None
        ):
            return False
        if any(
            not _opaque_p2(value)
            for key, value in scenario.items()
            if key.endswith("_ref") and value is not None
        ):
            return False
        if (
            scenario["automatic_final_conclusion_allowed"] is not False
            or scenario["actual_report_status_impact_analysis_performed"] is not False
            or scenario["actual_external_augmentation_opinion_generated"] is not False
            or scenario["expectation_met"] is not True
        ):
            return False
    if any(
        item["human_confirmation_recorded"] is not False
        or item["final_conclusion_state"] != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        for item in handlings
    ):
        return False
    return _closed_runtime(report.get("runtime_boundary")) and _zero_actual_counts_in(
        report
    )


def _p4_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if (
        getattr(module, "SCHEMA_VERSION", None) != P4_SCHEMA_VERSION
        or getattr(module, "RECORD_KIND", None) != P4_RECORD_KIND
        or getattr(module, "PASS_RESULT", None) != P4_PASS_RESULT
        or getattr(module, "ENTRY_GATE", None) != "IDS-STAGE106-P4-GATE"
        or getattr(module, "NEXT_GATE", None) != REVIEW_GATE
        or report.get("schema_version") != P4_SCHEMA_VERSION
        or report.get("record_kind") != P4_RECORD_KIND
        or report.get("result") != P4_PASS_RESULT
        or report.get("valid") is not True
        or report.get("failure_state") is not None
        or report.get("current_gate") != "IDS-STAGE106-P4-GATE"
        or report.get("next_gate") != REVIEW_GATE
        or report.get("delivery_field_check_count") != 388
        or report.get("control_references_opaque") is not True
        or report.get("second_authoritative_source_created") is not False
        or report.get("persistent_record_created") is not False
        or report.get("stage106_review_started") is not False
        or len(report.get("chinese_feedback", ())) != 4
    ):
        return False
    for name, fields in module.DELIVERY_GROUPS:
        expected_count = 2 if name == "regeneration_and_withdrawal_control_records" else 5
        if not _records_have_shape(report.get(name), fields, expected_count):
            return False
        for record in report[name]:
            if any(
                not _opaque_reference(value)
                for key, value in record.items()
                if (
                    key.endswith("_ref")
                    or key in {"delivery_record_id", "instruction_id"}
                )
                and value is not None
            ):
                return False
            if any(
                value is not False
                for key, value in record.items()
                if key.startswith("actual_") or key == "persistent_state_write_performed"
            ):
                return False
    samples = report["report_sample_control_records"]
    if any(
        (item["evidence_id_ref"] is None) == (item["evidence_gap_ref"] is None)
        or item["automatic_final_conclusion_allowed"] is not False
        for item in samples
    ):
        return False
    templates = report["report_template_and_whitebox_confirmation_control_records"]
    if any(
        item["automatic_final_conclusion_allowed"] is not False
        or item["final_conclusion_state"] != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        for item in templates
    ):
        return False
    instructions = report["regeneration_and_withdrawal_control_records"]
    if (
        {item["control_domain"] for item in instructions}
        != {"report_regeneration", "report_withdrawal"}
        or any(
            item["rollback_target_result"] != P3_PASS_RESULT
            or item["business_line_whitebox_confirmation_required"] is not True
            or item["human_confirmation_required"] is not True
            or item["versioned_basis_required"] is not True
            or item["verifiable_rollback_target_required"] is not True
            for item in instructions
        )
    ):
        return False
    return _closed_runtime(report.get("runtime_boundary")) and _zero_actual_counts_in(
        report
    )


def _authority_boundary_closed(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    phase1_authority = _mapping(phase1.get("source_authority"))
    contract_authorities = (
        _mapping(phase2_contract.get("source_authority")),
        _mapping(phase3_contract.get("source_authority")),
        _mapping(phase4_contract.get("source_authority")),
    )
    return (
        phase1_authority.get("source_document_remains_authoritative") is True
        and phase1_authority.get(
            "business_line_whitebox_human_review_remains_authoritative"
        )
        is True
        and phase1_authority.get("second_authoritative_source_created") is False
        and all(
            authority.get("source_document_remains_authoritative") is True
            and authority.get(
                "business_line_whitebox_human_review_remains_authoritative"
            )
            is True
            and authority.get("second_authoritative_source_created") is False
            for authority in contract_authorities
        )
        and phase3_report.get("second_authoritative_source_created") is False
        and phase3_report.get("persistent_record_created") is False
        and phase4_report.get("second_authoritative_source_created") is False
        and phase4_report.get("persistent_record_created") is False
    )


def _evidence_and_source_semantics_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    samples = phase4_report.get("report_sample_control_records")
    if not isinstance(scenarios, list) or not isinstance(samples, list):
        return False
    external = next(
        (
            item
            for item in scenarios
            if item["scenario_id"]
            == "external_augmentation_retains_external_source_type_control"
        ),
        None,
    )
    if not isinstance(external, Mapping) or (
        external["external_augmentation_may_not_be_internal_project_evidence"] is not True
        or external["external_augmentation_may_not_close_evidence_gap"] is not True
        or external["actual_external_augmentation_opinion_generated"] is not False
    ):
        return False
    return all(
        (item["evidence_id_ref"] is None) != (item["evidence_gap_ref"] is None)
        and item["automatic_final_conclusion_allowed"] is False
        and item["actual_report_sample_rendered"] is False
        for item in samples
    )


def _lifecycle_and_whitebox_valid(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    scenarios = phase3_report.get("scenario_results")
    impacts = phase4_report.get("report_impact_analysis_control_records")
    quality = phase4_report.get("report_quality_score_control_records")
    templates = phase4_report.get(
        "report_template_and_whitebox_confirmation_control_records"
    )
    if not all(isinstance(value, list) for value in (scenarios, impacts, quality, templates)):
        return False
    lifecycle = next(
        (
            item
            for item in scenarios
            if item["scenario_id"]
            == "withdrawal_downgrade_and_index_change_impact_report_status_control"
        ),
        None,
    )
    if not isinstance(lifecycle, Mapping) or (
        lifecycle["actual_report_status_impact_analysis_performed"] is not False
        or lifecycle["automatic_final_conclusion_allowed"] is not False
    ):
        return False
    if any(
        item["actual_report_impact_analysis_performed"] is not False
        or item["actual_report_status_update_performed"] is not False
        for item in impacts
    ):
        return False
    if any(
        item["actual_report_quality_score_calculated"] is not False
        or item["actual_report_quality_score_persisted"] is not False
        or item["automatic_final_conclusion_allowed"] is not False
        for item in quality
    ):
        return False
    return all(
        item["actual_template_constraint_reviewed"] is False
        and item["actual_human_confirmation_performed"] is False
        and item["actual_final_conclusion_published"] is False
        and item["business_line_whitebox_confirmation_required"]
        in {True, False}
        for item in templates
    )


def _failure_report(failure_state: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": False,
        "result": FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": REVIEW_GATE,
        "next_gate": REVIEW_GATE,
        "phase1_static_contract_reviewed": False,
        "phase2_control_slice_reviewed": False,
        "phase3_controlled_scenarios_reviewed": False,
        "phase4_delivery_evidence_reviewed": False,
        "reviewed_control_shape": {},
        "reviewed_phase_results": {},
        "control_references_opaque": False,
        "single_authority_boundary_preserved": False,
        "business_line_whitebox_gate_preserved": False,
        "phase4_to_phase3_rollback_preserved": False,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "stage106_review_started": False,
        "whole_stage_review_completed_in_memory_only": False,
        "stage107_started": False,
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [],
    }


def build_external_augmentation_opinion_stage_review(
    phase1_contract_provider: Provider | None = None,
    phase2_provider: Provider | None = None,
    phase3_provider: Provider | None = None,
    phase4_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械复审 P1--P4 控制工件；任一漂移均返回零运行时失败关闭报告。"""

    try:
        phase1_contract = (
            phase1_contract_provider() if phase1_contract_provider else _load_json(P1_CONTRACT_PATH)
        )
        phase2_contract = _load_json(P2_CONTRACT_PATH)
        phase3_contract = _load_json(P3_CONTRACT_PATH)
        phase4_contract = _load_json(P4_CONTRACT_PATH)
    except Exception:
        return _failure_report("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _p1_shape_valid(phase1_contract):
        return _failure_report("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase2_module = _load_module("stage106_review_phase2", P2_MODULE_PATH)
        phase2_report = (
            phase2_provider()
            if phase2_provider
            else phase2_module.execute_external_augmentation_opinion_control_slice(
                phase2_module.build_control_input()
            )
        )
    except Exception:
        return _failure_report("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _p2_contract_valid(phase2_contract) or not _p2_report_valid(
        phase2_module, phase2_report
    ):
        return _failure_report("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase3_module = _load_module("stage106_review_phase3", P3_MODULE_PATH)
        phase3_report = (
            phase3_provider()
            if phase3_provider
            else phase3_module.build_external_augmentation_opinion_phase3_report()
        )
    except Exception:
        return _failure_report("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _p3_contract_valid(phase3_contract) or not _p3_report_valid(
        phase3_module, phase3_report
    ):
        return _failure_report("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase4_module = _load_module("stage106_review_phase4", P4_MODULE_PATH)
        phase4_report = (
            phase4_provider()
            if phase4_provider
            else phase4_module.build_external_augmentation_opinion_phase4_delivery_report()
        )
    except Exception:
        return _failure_report("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _p4_contract_valid(phase4_contract) or not _p4_report_valid(
        phase4_module, phase4_report
    ):
        return _failure_report("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    if not all(
        (
            _contract_boundary_closed(phase1_contract),
            _contract_boundary_closed(phase2_contract),
            _contract_boundary_closed(phase3_contract),
            _contract_boundary_closed(phase4_contract),
            _closed_runtime(phase2_report.get("runtime_boundary")),
            _closed_runtime(phase3_report.get("runtime_boundary")),
            _closed_runtime(phase4_report.get("runtime_boundary")),
            _zero_actual_counts_in(phase2_report),
            _zero_actual_counts_in(phase3_report),
            _zero_actual_counts_in(phase4_report),
        )
    ):
        return _failure_report("RUNTIME_SIGNAL_OR_STAGE107_ENTRY_DETECTED")
    if not _authority_boundary_closed(
        phase1_contract,
        phase2_contract,
        phase3_contract,
        phase4_contract,
        phase3_report,
        phase4_report,
    ):
        return _failure_report("SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not _evidence_and_source_semantics_valid(phase3_report, phase4_report):
        return _failure_report("EVIDENCE_BINDING_OR_SOURCE_SEMANTICS_MISMATCH")
    if not _lifecycle_and_whitebox_valid(phase3_report, phase4_report):
        return _failure_report("REPORT_LIFECYCLE_WHITEBOX_BOUNDARY_MISMATCH")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": True,
        "result": PASS_RESULT,
        "failure_state": None,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE,
        "phase1_static_contract_reviewed": True,
        "phase2_control_slice_reviewed": True,
        "phase3_controlled_scenarios_reviewed": True,
        "phase4_delivery_evidence_reviewed": True,
        "reviewed_control_shape": deepcopy(REVIEWED_CONTROL_SHAPE),
        "reviewed_phase_results": {
            "phase1_contract_state": P1_CONTRACT_STATE,
            "phase2_control_slice_result": P2_PASS_RESULT,
            "phase3_controlled_scenarios_result": P3_PASS_RESULT,
            "phase4_delivery_evidence_result": P4_PASS_RESULT,
        },
        "control_references_opaque": True,
        "single_authority_boundary_preserved": True,
        "business_line_whitebox_gate_preserved": True,
        "phase4_to_phase3_rollback_preserved": True,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "stage106_review_started": True,
        "whole_stage_review_completed_in_memory_only": True,
        "stage107_started": False,
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [
            "外部增强意见章节 P1--P4 已完成纯内存机械复审，来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。",
            "关键结论保持 evidence_id 或 evidence_gap 严格二选一，引用来源与页码、索引版本和五项生成快照保持控制引用形状。",
            "资料撤回、证据降级和索引版本变化保持未来报告状态影响控制；外部增强保留 external_public_reference 与 model_reasoning 的来源语义。",
            "报告模板限制、人工确认、最终结论与报告重新生成/撤回保持业务线白箱门禁，P4 可回退至可验证的 P3 控制场景。",
        ],
    }
    return deepcopy(report)
