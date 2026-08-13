"""Stage061 P3 的结构化数据质量受控异常场景验证。

模块仅重放 Stage061 P2 的两条固定、非业务、reference-only 控制输入与十条
未评估质量候选。空表、合并单元格、单位混乱、日期格式不一、异常值和重复行
只是受控类别标签；不会打开、解析、规范化、统计或保存任何表格内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage061.structured_data_quality.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_STRUCTURED_DATA_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE061-P4-GATE"
SOURCE_IDENTITY_REF = "source:control:stage061-p2"

QUALITY_RESULT_FIELDS = (
    "quality_result_ref",
    "quality_request_ref",
    "quality_dimension",
    "quality_state",
    "field_candidate_ref",
    "primary_key_ref",
    "source_identity_ref",
    "source_document_ref",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "fact_set_ref",
    "evidence_ref",
    "human_review_state",
    "statistical_conclusion_state",
    "remediation_state",
)
SOURCE_LOCATION_FIELDS = (
    "source_document_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "evidence_ref",
)
SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "table_schema_inference_performed",
    "field_identification_performed",
    "structured_fact_extraction_performed",
    "typed_value_extraction_performed",
    "table_summary_generation_performed",
    "field_completeness_evaluation_performed",
    "unit_consistency_evaluation_performed",
    "date_validity_evaluation_performed",
    "primary_key_duplication_evaluation_performed",
    "outlier_evaluation_performed",
    "quality_gate_evaluation_performed",
    "numeric_statistic_computation_performed",
    "actual_structured_fact_created",
    "actual_quality_result_created",
    "actual_quality_result_persisted",
    "actual_source_location_binding_created",
    "actual_evidence_record_created",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "quality_result_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)
REQUIRED_SCENARIO_CATEGORIES = {
    "EMPTY_TABLE_CONTROL",
    "MERGED_CELLS_CONTROL",
    "UNIT_CONFUSION_CONTROL",
    "DATE_FORMAT_VARIATION_CONTROL",
    "OUTLIER_VALUE_CONTROL",
    "DUPLICATE_ROW_CONTROL",
}
SCENARIOS = (
    {
        "scenario_id": "empty-table-control-explicit-closed",
        "scenario_category": "EMPTY_TABLE_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:production",
        "quality_dimension": "FIELD_COMPLETENESS",
        "quality_disposition": "REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "merged-cells-control-human-handling",
        "scenario_category": "MERGED_CELLS_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:quality",
        "quality_dimension": "FIELD_COMPLETENESS",
        "quality_disposition": "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "unit-confusion-control-human-handling",
        "scenario_category": "UNIT_CONFUSION_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:production",
        "quality_dimension": "UNIT_CONSISTENCY",
        "quality_disposition": "UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "date-format-variation-control-human-handling",
        "scenario_category": "DATE_FORMAT_VARIATION_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:quality",
        "quality_dimension": "DATE_VALIDITY",
        "quality_disposition": "UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "outlier-control-numeric-block",
        "scenario_category": "OUTLIER_VALUE_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:production",
        "quality_dimension": "OUTLIER_REVIEW",
        "quality_disposition": "UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": True,
    },
    {
        "scenario_id": "duplicate-row-control-human-handling",
        "scenario_category": "DUPLICATE_ROW_CONTROL",
        "source_document_ref": "source-document:control:stage061-p2:quality",
        "quality_dimension": "PRIMARY_KEY_DUPLICATION",
        "quality_disposition": "DUPLICATE_PRIMARY_KEY_CANDIDATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_structured_data_quality_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制候选并输出不含表格内容的异常场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    candidates = _quality_candidates(phase2_result)
    side_effect_free = all(phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_STRUCTURED_DATA_QUALITY_CANDIDATE_CONTROL_SLICE"
        and phase2_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and phase2_result.get("control_quality_input_record_count") == 2
        and phase2_result.get("actual_quality_input_record_count") == 0
        and phase2_result.get("quality_result_candidate_count") == 10
        and phase2_result.get("quality_dimension_count") == 5
        and phase2_result.get("source_location_binding_candidate_count") == 10
        and phase2_result.get("source_location_references_preserved") is True
        and phase2_result.get("all_quality_states_unassessed") is True
        and phase2_result.get("all_human_review_required") is True
        and phase2_result.get("all_statistical_conclusions_blocked") is True
        and len(candidates) == 10
        and all(_candidate_has_expected_control_shape(candidate) for candidate in candidates)
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates, side_effect_free) for scenario in SCENARIOS
    ]
    categories_covered = {
        str(scenario["scenario_category"]) for scenario in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    traceability_preserved = all(
        item["source_location_reference_preserved"] for item in scenario_results
    )
    valid = (
        phase2_shape_preserved
        and categories_covered
        and len(scenario_results) == len(REQUIRED_SCENARIO_CATEGORIES)
        and all(item["expectation_met"] for item in scenario_results)
        and all(item["explicit_disposition"] for item in scenario_results)
        and not any(item["silent_drop"] for item in scenario_results)
        and traceability_preserved
        and side_effect_free
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": sum(item["expectation_met"] for item in scenario_results),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] for item in scenario_results
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in scenario_results),
        "human_handling_required_count": sum(
            item["human_handling_required"] for item in scenario_results
        ),
        "all_taskpack_exception_categories_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "unique_quality_result_candidate_count": len(
            {
                item["referenced_quality_result_ref"]
                for item in scenario_results
                if isinstance(item["referenced_quality_result_ref"], str)
            }
        ),
        "scenario_results": scenario_results,
        "control_source_location_field_count": len(SOURCE_LOCATION_FIELDS),
        "source_location_reference_check_count": sum(
            item["source_location_reference_preserved"] for item in scenario_results
        ),
        "control_source_location_traceability_preserved": traceability_preserved,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_structured_fact_created": False,
        "actual_quality_result_created": False,
        "actual_quality_result_persisted": False,
        "actual_input_record_count": 0,
        "actual_structured_fact_count": 0,
        "actual_numeric_fact_count": 0,
        "actual_quality_result_count": 0,
        "actual_source_location_binding_count": 0,
        "actual_evidence_record_count": 0,
        "empty_table_human_handling_count": _human_count(
            scenario_results, "EMPTY_TABLE_CONTROL"
        ),
        "merged_cell_human_handling_count": _human_count(
            scenario_results, "MERGED_CELLS_CONTROL"
        ),
        "unit_confusion_human_handling_count": _human_count(
            scenario_results, "UNIT_CONFUSION_CONTROL"
        ),
        "date_variation_human_handling_count": _human_count(
            scenario_results, "DATE_FORMAT_VARIATION_CONTROL"
        ),
        "outlier_numeric_block_count": sum(
            item["unverified_numeric_blocks_statistical_conclusion"]
            for item in scenario_results
        ),
        "duplicate_row_human_handling_count": _human_count(
            scenario_results, "DUPLICATE_ROW_CONTROL"
        ),
        "all_quality_states_unassessed": all(
            item["quality_state"] == "UNASSESSED" for item in scenario_results
        ),
        "all_human_review_required": all(
            item["human_handling_required"] for item in scenario_results
        ),
        "all_statistical_conclusions_blocked": all(
            not item["numeric_statistical_conclusion_allowed"] for item in scenario_results
        ),
        "source_document_remains_authoritative": True,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "numeric_statistical_conclusion_allowed": False,
        "model_direct_text_guessing_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "field_completeness_evaluation_performed": False,
        "unit_consistency_evaluation_performed": False,
        "date_validity_evaluation_performed": False,
        "primary_key_duplication_evaluation_performed": False,
        "outlier_evaluation_performed": False,
        "quality_gate_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage061_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "github_upload_performed": False,
        "push_performed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "chinese_feedback": [
            "已完成固定质量候选的异常场景验证；结果只说明控制处置和引用形状，不代表真实表格、真实来源位置或业务质量结论。",
            "空表、合并单元格、单位混乱、日期格式不一和重复行均需人工处理，系统不会自动修正或写入。",
            "未验证数值不得形成统计结论或模型确定性数值结论，须等待可追溯的结构化事实与证据流程。",
            "每个控制场景保留来源文档、工作表、表头行、行列范围和 evidence 引用；这些是控制引用，不是已验证的真实文件位置。",
        ],
    }


def _load_phase2_executor() -> Phase2Executor:
    path = Path(__file__).with_name("stage061_structured_data_quality_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage061_structured_data_quality_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage061 P2 structured-data quality control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_structured_data_quality_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实表格、字段或单元格内容。"""

    return {
        "structured_data_quality_input_records": [
            {
                "quality_request_ref": "quality-request:control:stage061-p2:production",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage061-p2:production",
                "file_format": "XLSX",
                "workbook_ref": "workbook:control:stage061-p2:production",
                "worksheet_ref": "worksheet:control:stage061-p2:production",
                "header_row_ref": "header-row:control:stage061-p2:production",
                "row_range_ref": "row-range:control:stage061-p2:production",
                "column_range_ref": "column-range:control:stage061-p2:production",
                "schema_profile_ref": "schema-profile:control:stage061-p2:production",
                "fact_set_ref": "fact-set:control:stage061-p2:production",
                "field_candidate_ref": "field-candidate:control:stage061-p2:production",
                "primary_key_ref": "primary-key:control:stage061-p2:production",
                "record_type": "PRODUCTION_RECORD",
                "evidence_ref": "evidence:control:stage061-p2:production",
                "quality_profile_ref": "quality-profile:control:stage061-p2:production",
            },
            {
                "quality_request_ref": "quality-request:control:stage061-p2:quality",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage061-p2:quality",
                "file_format": "CSV",
                "workbook_ref": "workbook:control:stage061-p2:quality",
                "worksheet_ref": "worksheet:control:stage061-p2:quality",
                "header_row_ref": "header-row:control:stage061-p2:quality",
                "row_range_ref": "row-range:control:stage061-p2:quality",
                "column_range_ref": "column-range:control:stage061-p2:quality",
                "schema_profile_ref": "schema-profile:control:stage061-p2:quality",
                "fact_set_ref": "fact-set:control:stage061-p2:quality",
                "field_candidate_ref": "field-candidate:control:stage061-p2:quality",
                "primary_key_ref": "primary-key:control:stage061-p2:quality",
                "record_type": "QUALITY_INSPECTION_RECORD",
                "evidence_ref": "evidence:control:stage061-p2:quality",
                "quality_profile_ref": "quality-profile:control:stage061-p2:quality",
            },
        ]
    }


def _quality_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("quality_result_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _candidate_has_expected_control_shape(candidate: Mapping[str, Any]) -> bool:
    return (
        set(candidate) == set(QUALITY_RESULT_FIELDS)
        and candidate.get("quality_state") == "UNASSESSED"
        and candidate.get("human_review_state") == "REQUIRED_WHEN_UNVERIFIED"
        and candidate.get("statistical_conclusion_state")
        == "BLOCKED_UNVERIFIED_REFERENCE_ONLY"
        and candidate.get("remediation_state")
        == "PENDING_HUMAN_DECISION_REFERENCE_ONLY"
        and _control_reference_only(candidate)
        and _source_location_preserved(candidate)
    )


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    candidate = _candidate_for_scenario(scenario, candidates)
    location_preserved = _source_location_preserved(candidate)
    control_reference_only = _control_reference_only(candidate)
    explicit_disposition = isinstance(scenario["quality_disposition"], str)
    numeric_block = bool(scenario["unverified_numeric_blocks_statistical_conclusion"])
    expectation_met = (
        candidate is not None
        and location_preserved
        and control_reference_only
        and explicit_disposition
        and bool(scenario["human_handling_required"])
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "control_scenario_metadata_only": True,
        "candidate_selector_field": "source_document_ref+quality_dimension",
        "candidate_selector_value": (
            f"{scenario['source_document_ref']}+{scenario['quality_dimension']}"
        ),
        "referenced_quality_result_ref": _value(candidate, "quality_result_ref"),
        "quality_request_ref": _value(candidate, "quality_request_ref"),
        "quality_dimension": _value(candidate, "quality_dimension"),
        "quality_state": _value(candidate, "quality_state"),
        "field_candidate_ref": _value(candidate, "field_candidate_ref"),
        "primary_key_ref": _value(candidate, "primary_key_ref"),
        "fact_set_ref": _value(candidate, "fact_set_ref"),
        "source_document_ref": _value(candidate, "source_document_ref"),
        "workbook_ref": _value(candidate, "workbook_ref"),
        "worksheet_ref": _value(candidate, "worksheet_ref"),
        "header_row_ref": _value(candidate, "header_row_ref"),
        "row_range_ref": _value(candidate, "row_range_ref"),
        "column_range_ref": _value(candidate, "column_range_ref"),
        "evidence_ref": _value(candidate, "evidence_ref"),
        "source_location_reference_preserved": location_preserved,
        "control_reference_only": control_reference_only,
        "quality_disposition": scenario["quality_disposition"],
        "human_handling_required": scenario["human_handling_required"],
        "unverified_numeric_blocks_statistical_conclusion": numeric_block,
        "numeric_statistical_conclusion_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "explicit_disposition": explicit_disposition,
        "silent_drop": False,
        "expectation_met": expectation_met,
        "real_table_content_evaluated": False,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_structured_fact_created": False,
        "actual_quality_result_created": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
    }


def _candidate_for_scenario(
    scenario: Mapping[str, object], candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    source_document_ref = scenario.get("source_document_ref")
    quality_dimension = scenario.get("quality_dimension")
    if not isinstance(source_document_ref, str) or not isinstance(quality_dimension, str):
        return None
    return next(
        (
            candidate
            for candidate in candidates
            if candidate.get("source_document_ref") == source_document_ref
            and candidate.get("quality_dimension") == quality_dimension
        ),
        None,
    )


def _source_location_preserved(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(candidate.get(field), str) and ":control:" in candidate[field]
        for field in SOURCE_LOCATION_FIELDS
    )


def _control_reference_only(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(value, str) and ":control:" in value
        for field, value in candidate.items()
        if field.endswith("_ref")
    )


def _human_count(
    scenario_results: Sequence[Mapping[str, Any]], category: str
) -> int:
    return sum(
        item["scenario_category"] == category and item["human_handling_required"]
        for item in scenario_results
    )


def _value(candidate: Mapping[str, Any] | None, field: str) -> object | None:
    return candidate.get(field) if candidate is not None else None
