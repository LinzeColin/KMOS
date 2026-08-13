"""Stage057 P3 的 XLSX/CSV 接入合同受控质量场景。

模块只重放 Stage057 P2 的两条固定、非业务、reference-only 控制记录。
空表、合并单元格、单位混乱、日期格式不一、异常值和重复行在这里均为
控制类别标签，不是实际 XLSX/CSV、工作表、单元格、数值、日期或行记录。
模块不打开、解析、规范化、统计或保存任何表格内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage057.xlsx_csv_ingestion.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_XLSX_CSV_INGESTION_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE057-P4-GATE"
SOURCE_IDENTITY_REF = "source:control:stage057-p2"

SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "real_table_schema_inference_performed",
    "real_field_identification_performed",
    "real_structured_fact_extraction_performed",
    "actual_structured_fact_created",
    "actual_structured_fact_persisted",
    "actual_typed_value_retained",
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
        "candidate_selector": "quality_result",
        "quality_disposition": "REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "merged-cells-control-human-handling",
        "scenario_category": "MERGED_CELLS_CONTROL",
        "candidate_selector": "equipment_ref",
        "quality_disposition": "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "unit-confusion-control-human-handling",
        "scenario_category": "UNIT_CONFUSION_CONTROL",
        "candidate_selector": "unit_ref",
        "quality_disposition": "UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "date-format-variation-control-human-handling",
        "scenario_category": "DATE_FORMAT_VARIATION_CONTROL",
        "candidate_selector": "record_date",
        "quality_disposition": "UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "outlier-control-numeric-block",
        "scenario_category": "OUTLIER_VALUE_CONTROL",
        "candidate_selector": "measurement_value",
        "quality_disposition": "UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": True,
    },
    {
        "scenario_id": "duplicate-row-control-human-handling",
        "scenario_category": "DUPLICATE_ROW_CONTROL",
        "candidate_selector": "quality_result",
        "quality_disposition": "DUPLICATE_ROW_CANDIDATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_xlsx_csv_ingestion_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 固定候选并输出无表格内容的异常场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    candidates = _fact_candidates(phase2_result)
    candidates_by_field = _candidates_by_field(candidates)
    side_effect_free = all(phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_SCHEMA_AND_FACT_CANDIDATE_SLICE"
        and phase2_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and phase2_result.get("table_input_record_count") == 2
        and phase2_result.get("schema_profile_candidate_count") == 2
        and phase2_result.get("structured_fact_candidate_count") == 10
        and phase2_result.get("rag_summary_candidate_count") == 2
        and len(candidates) == 10
        and phase2_result.get("source_location_references_preserved") is True
        and all(candidate.get("typed_value") is None for candidate in candidates)
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates_by_field, side_effect_free)
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
        "taskpack_exception_categories_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "unique_fact_candidate_count": len(candidates),
        "phase2_shape_preserved": phase2_shape_preserved,
        "scenario_results": scenario_results,
        "source_location_reference_check_count": sum(
            item["source_location_reference_preserved"] for item in scenario_results
        ),
        "control_source_location_traceability_preserved": traceability_preserved,
        "actual_source_file_traceability_validated": False,
        "actual_evidence_record_created": False,
        "actual_typed_value_created": False,
        "actual_structured_fact_created": False,
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
        "phase4_started": False,
        "github_upload_performed": False,
        "push_performed": False,
    }


def _load_phase2_executor() -> Phase2Executor:
    path = Path(__file__).with_name("stage057_xlsx_csv_ingestion_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage057_xlsx_csv_ingestion_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage057 P2 XLSX/CSV control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_xlsx_csv_ingestion_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结引用输入；它们不表示真实表格、行列或单元格内容。"""

    return {
        "table_input_records": [
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage057-p2:1",
                "file_format": "XLSX",
                "workbook_ref": "workbook:control:stage057-p2:1",
                "worksheet_ref": "worksheet:control:stage057-p2:1",
                "row_range_ref": "row-range:control:stage057-p2:1",
                "column_range_ref": "column-range:control:stage057-p2:1",
                "record_type": "PRODUCTION_RECORD",
                "schema_profile_ref": "schema-profile:control:stage057-p2:production",
                "fact_type": "PRODUCTION_MEASUREMENT",
                "evidence_ref": "evidence:control:stage057-p2:1",
                "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage057-p2:2",
                "file_format": "CSV",
                "workbook_ref": "workbook:control:stage057-p2:csv-reference",
                "worksheet_ref": "worksheet:control:stage057-p2:2",
                "row_range_ref": "row-range:control:stage057-p2:2",
                "column_range_ref": "column-range:control:stage057-p2:2",
                "record_type": "QUALITY_INSPECTION_RECORD",
                "schema_profile_ref": "schema-profile:control:stage057-p2:quality",
                "fact_type": "QUALITY_RESULT",
                "evidence_ref": "evidence:control:stage057-p2:2",
                "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
            },
        ]
    }


def _fact_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("structured_fact_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _candidates_by_field(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    by_field: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        field_name = candidate.get("field_name")
        if isinstance(field_name, str) and field_name not in by_field:
            by_field[field_name] = candidate
    return by_field


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates_by_field: Mapping[str, Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    selector = scenario["candidate_selector"]
    candidate = candidates_by_field.get(selector) if isinstance(selector, str) else None
    location_preserved = _source_location_preserved(candidate)
    references = [candidate["fact_id"]] if candidate and isinstance(candidate.get("fact_id"), str) else []
    numeric_block = bool(scenario["unverified_numeric_blocks_statistical_conclusion"])
    expectation_met = (
        candidate is not None
        and location_preserved
        and candidate.get("typed_value") is None
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "control_scenario_metadata_only": True,
        "quality_disposition": scenario["quality_disposition"],
        "explicit_disposition": True,
        "silent_drop": False,
        "human_handling_required": scenario["human_handling_required"],
        "referenced_fact_candidate_ids": references,
        "source_identity_ref": candidate.get("source_identity_ref") if candidate else None,
        "source_document_ref": candidate.get("source_document_ref") if candidate else None,
        "worksheet_ref": candidate.get("worksheet_ref") if candidate else None,
        "row_range_ref": candidate.get("row_range_ref") if candidate else None,
        "column_range_ref": candidate.get("column_range_ref") if candidate else None,
        "evidence_ref": candidate.get("evidence_ref") if candidate else None,
        "source_location_reference_preserved": location_preserved,
        "real_table_content_evaluated": False,
        "actual_source_file_traceability_validated": False,
        "actual_evidence_record_created": False,
        "actual_structured_fact_created": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
        "unverified_numeric_blocks_statistical_conclusion": numeric_block,
        "numeric_statistical_conclusion_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "expectation_met": expectation_met,
    }


def _source_location_preserved(candidate: Mapping[str, Any] | None) -> bool:
    if candidate is None:
        return False
    return all(
        isinstance(candidate.get(field), str) and candidate[field]
        for field in (
            "source_document_ref",
            "worksheet_ref",
            "row_range_ref",
            "column_range_ref",
            "evidence_ref",
        )
    )
