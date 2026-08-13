"""Stage058 P3 的表格 Schema 推断受控异常场景验证。

模块只重放 Stage058 P2 的两条固定、非业务、reference-only 控制记录和
Schema profile 候选。空表、合并单元格、单位混乱、日期格式不一、异常值和
重复行仅是控制类别标签；不会打开、解析、规范化、统计或保存任何表格内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage058.table_schema_inference.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_TABLE_SCHEMA_INFERENCE_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE058-P4-GATE"
SOURCE_IDENTITY_REF = "source:control:stage058-p2"

SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "real_table_schema_inference_performed",
    "real_field_identification_performed",
    "real_structured_fact_extraction_performed",
    "actual_schema_profile_created",
    "actual_schema_profile_persisted",
    "actual_field_mapping_created",
    "actual_source_location_binding_created",
    "actual_evidence_record_created",
    "numeric_statistic_computation_performed",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "rag_summary_write_performed",
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
        "candidate_selector_field": "candidate_quality_result_ref",
        "candidate_selector_value": "quality-result-ref:control:stage058-p2",
        "quality_disposition": "REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "merged-cells-control-human-handling",
        "scenario_category": "MERGED_CELLS_CONTROL",
        "candidate_selector_field": "candidate_equipment_ref",
        "candidate_selector_value": "equipment-ref:control:stage058-p2:production",
        "quality_disposition": "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "unit-confusion-control-human-handling",
        "scenario_category": "UNIT_CONFUSION_CONTROL",
        "candidate_selector_field": "candidate_unit_ref",
        "candidate_selector_value": "unit-ref:control:stage058-p2:production",
        "quality_disposition": "UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "date-format-variation-control-human-handling",
        "scenario_category": "DATE_FORMAT_VARIATION_CONTROL",
        "candidate_selector_field": "candidate_date_format_ref",
        "candidate_selector_value": "date-format:control:stage058-p2:yyyy-mm-dd",
        "quality_disposition": "UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "outlier-control-numeric-block",
        "scenario_category": "OUTLIER_VALUE_CONTROL",
        "candidate_selector_field": "candidate_field_type",
        "candidate_selector_value": "DECIMAL_OR_INTEGER",
        "quality_disposition": "UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": True,
    },
    {
        "scenario_id": "duplicate-row-control-human-handling",
        "scenario_category": "DUPLICATE_ROW_CONTROL",
        "candidate_selector_field": "candidate_fact_type",
        "candidate_selector_value": "QUALITY_RESULT",
        "quality_disposition": "DUPLICATE_ROW_CANDIDATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_table_schema_inference_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制候选并输出无表格内容的异常场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    candidates = _schema_profile_candidates(phase2_result)
    side_effect_free = all(
        phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS
    )
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_SCHEMA_PROFILE_CANDIDATE_SLICE"
        and phase2_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and phase2_result.get("schema_inference_input_record_count") == 2
        and phase2_result.get("schema_profile_group_count") == 2
        and phase2_result.get("schema_profile_candidate_count") == 11
        and phase2_result.get("candidate_field_mapping_count") == 11
        and phase2_result.get("semantic_category_count") == 9
        and phase2_result.get("candidate_field_type_count") == 6
        and phase2_result.get("source_location_binding_candidate_count") == 11
        and phase2_result.get("source_location_references_preserved") is True
        and phase2_result.get("structured_fact_candidate_count") == 0
        and phase2_result.get("rag_summary_candidate_count") == 0
        and len(candidates) == 11
        and all(
            candidate.get("inference_state")
            == "CANDIDATE_CONTROL_REFERENCE_ONLY"
            for candidate in candidates
        )
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates, side_effect_free)
        for scenario in SCENARIOS
    ]
    categories_covered = {
        str(item["scenario_category"]) for item in SCENARIOS
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
        "passed_scenario_count": sum(
            item["expectation_met"] for item in scenario_results
        ),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] for item in scenario_results
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in scenario_results),
        "human_handling_required_count": sum(
            item["human_handling_required"] for item in scenario_results
        ),
        "taskpack_exception_categories_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "unique_schema_profile_candidate_count": len(candidates),
        "scenario_results": scenario_results,
        "control_source_location_field_count": 6,
        "source_location_reference_check_count": sum(
            item["source_location_reference_preserved"] for item in scenario_results
        ),
        "control_source_location_traceability_preserved": traceability_preserved,
        "actual_source_file_traceability_validated": False,
        "actual_evidence_record_created": False,
        "actual_schema_profile_created": False,
        "actual_field_mapping_created": False,
        "actual_structured_fact_created": False,
        "actual_rag_summary_created": False,
        "actual_input_record_count": 0,
        "actual_schema_profile_count": 0,
        "actual_field_mapping_count": 0,
        "actual_structured_fact_count": 0,
        "actual_numeric_fact_count": 0,
        "actual_source_location_binding_count": 0,
        "actual_evidence_record_count": 0,
        "empty_table_human_handling_count": sum(
            item["scenario_category"] == "EMPTY_TABLE_CONTROL"
            and item["human_handling_required"]
            for item in scenario_results
        ),
        "merged_cell_human_handling_count": sum(
            item["scenario_category"] == "MERGED_CELLS_CONTROL"
            and item["human_handling_required"]
            for item in scenario_results
        ),
        "unit_confusion_human_handling_count": sum(
            item["scenario_category"] == "UNIT_CONFUSION_CONTROL"
            and item["human_handling_required"]
            for item in scenario_results
        ),
        "date_variation_human_handling_count": sum(
            item["scenario_category"] == "DATE_FORMAT_VARIATION_CONTROL"
            and item["human_handling_required"]
            for item in scenario_results
        ),
        "outlier_numeric_block_count": sum(
            item["unverified_numeric_blocks_statistical_conclusion"]
            for item in scenario_results
        ),
        "duplicate_row_human_handling_count": sum(
            item["scenario_category"] == "DUPLICATE_ROW_CONTROL"
            and item["human_handling_required"]
            for item in scenario_results
        ),
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "numeric_statistical_conclusion_allowed": False,
        "model_direct_text_guessing_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "structured_fact_candidate_count": 0,
        "rag_summary_candidate_count": 0,
        "fact_extraction_deferred_to_stage059": True,
        "rag_summary_deferred_to_stage060": True,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_table_content_evaluated": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "rag_summary_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage058_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "github_upload_performed": False,
        "push_performed": False,
    }


def _load_phase2_executor() -> Phase2Executor:
    path = Path(__file__).with_name("stage058_table_schema_inference_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage058_table_schema_inference_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage058 P2 table Schema control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_table_schema_inference_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实表格、列名或单元格内容。"""

    return {
        "schema_inference_input_records": [
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage058-p2:production",
                "file_format": "XLSX",
                "workbook_ref": "workbook:control:stage058-p2:production",
                "worksheet_ref": "worksheet:control:stage058-p2:production",
                "header_row_ref": "header-row:control:stage058-p2:production",
                "row_range_ref": "row-range:control:stage058-p2:production",
                "column_range_ref": "column-range:control:stage058-p2:production",
                "record_type": "PRODUCTION_RECORD",
                "evidence_ref": "evidence:control:stage058-p2:production",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage058-p2:quality",
                "file_format": "CSV",
                "workbook_ref": "workbook:control:stage058-p2:quality",
                "worksheet_ref": "worksheet:control:stage058-p2:quality",
                "header_row_ref": "header-row:control:stage058-p2:quality",
                "row_range_ref": "row-range:control:stage058-p2:quality",
                "column_range_ref": "column-range:control:stage058-p2:quality",
                "record_type": "QUALITY_INSPECTION_RECORD",
                "evidence_ref": "evidence:control:stage058-p2:quality",
            },
        ]
    }


def _schema_profile_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("schema_profile_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    candidate = _candidate_for_selector(scenario, candidates)
    location_preserved = _source_location_preserved(candidate)
    explicit_disposition = isinstance(scenario["quality_disposition"], str)
    numeric_block = bool(
        scenario["unverified_numeric_blocks_statistical_conclusion"]
    )
    expectation_met = (
        candidate is not None
        and location_preserved
        and explicit_disposition
        and bool(scenario["human_handling_required"])
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "control_scenario_metadata_only": True,
        "candidate_selector_field": scenario["candidate_selector_field"],
        "candidate_selector_value": scenario["candidate_selector_value"],
        "referenced_schema_profile_id": _value(candidate, "schema_profile_id"),
        "referenced_candidate_column_handle": _value(
            candidate, "candidate_column_name"
        ),
        "source_document_ref": _value(candidate, "source_document_ref"),
        "worksheet_ref": _value(candidate, "worksheet_ref"),
        "header_row_ref": _value(candidate, "header_row_ref"),
        "row_range_ref": _value(candidate, "row_range_ref"),
        "column_range_ref": _value(candidate, "column_range_ref"),
        "evidence_ref": _value(candidate, "evidence_ref"),
        "source_location_reference_preserved": location_preserved,
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
        "actual_evidence_record_created": False,
        "actual_schema_profile_created": False,
        "actual_structured_fact_created": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
    }


def _candidate_for_selector(
    scenario: Mapping[str, object], candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    field = scenario.get("candidate_selector_field")
    expected = scenario.get("candidate_selector_value")
    if not isinstance(field, str) or not isinstance(expected, str):
        return None
    return next((item for item in candidates if item.get(field) == expected), None)


def _source_location_preserved(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(candidate.get(field), str) and candidate.get(field)
        for field in (
            "source_document_ref",
            "worksheet_ref",
            "header_row_ref",
            "row_range_ref",
            "column_range_ref",
            "evidence_ref",
        )
    )


def _value(candidate: Mapping[str, Any] | None, field: str) -> str | None:
    if candidate is None:
        return None
    value = candidate.get(field)
    return value if isinstance(value, str) else None
