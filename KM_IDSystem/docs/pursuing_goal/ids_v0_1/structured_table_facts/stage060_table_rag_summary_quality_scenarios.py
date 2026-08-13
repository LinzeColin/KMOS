"""Stage060 P3 的表格到 RAG 摘要受控异常场景验证。

模块只重放 Stage060 P2 的两条固定、非业务、reference-only 控制输入和两条
中文 RAG 摘要控制候选。空表、合并单元格、单位混乱、日期格式不一、异常值和重复行
仅是控制类别标签；不会打开、解析、规范化、统计或保存任何表格内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage060.table_rag_summary.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_TABLE_RAG_SUMMARY_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE060-P4-GATE"
SOURCE_IDENTITY_REF = "source:control:stage060-p2"

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
    "rag_summary_generation_performed",
    "numeric_statistic_computation_performed",
    "quality_gate_evaluation_performed",
    "actual_structured_fact_created",
    "actual_source_location_binding_created",
    "actual_evidence_record_created",
    "actual_rag_summary_created",
    "actual_summary_text_retained",
    "actual_rag_summary_persisted",
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
        "candidate_fact_type": "QUALITY_FACT",
        "quality_disposition": "REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "merged-cells-control-human-handling",
        "scenario_category": "MERGED_CELLS_CONTROL",
        "candidate_fact_type": "PRODUCTION_FACT",
        "quality_disposition": "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "unit-confusion-control-human-handling",
        "scenario_category": "UNIT_CONFUSION_CONTROL",
        "candidate_fact_type": "PRODUCTION_FACT",
        "quality_disposition": "UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "date-format-variation-control-human-handling",
        "scenario_category": "DATE_FORMAT_VARIATION_CONTROL",
        "candidate_fact_type": "PRODUCTION_FACT",
        "quality_disposition": "UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "outlier-control-numeric-block",
        "scenario_category": "OUTLIER_VALUE_CONTROL",
        "candidate_fact_type": "PRODUCTION_FACT",
        "quality_disposition": "UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": True,
    },
    {
        "scenario_id": "duplicate-row-control-human-handling",
        "scenario_category": "DUPLICATE_ROW_CONTROL",
        "candidate_fact_type": "QUALITY_FACT",
        "quality_disposition": "DUPLICATE_ROW_CANDIDATE_REQUIRES_HUMAN_HANDLING",
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_table_rag_summary_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制候选并输出无表格内容的异常场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    candidates = _summary_candidates(phase2_result)
    side_effect_free = all(
        phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS
    )
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_RAG_SUMMARY_CANDIDATE_CONTROL_SLICE"
        and phase2_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and phase2_result.get("control_summary_input_record_count") == 2
        and phase2_result.get("actual_summary_input_record_count") == 0
        and phase2_result.get("rag_summary_candidate_count") == 2
        and phase2_result.get("fact_reference_count") == 2
        and phase2_result.get("fact_types") == ["PRODUCTION_FACT", "QUALITY_FACT"]
        and phase2_result.get("source_location_binding_candidate_count") == 2
        and phase2_result.get("source_location_references_preserved") is True
        and phase2_result.get("all_summary_text_unset") is True
        and phase2_result.get("summary_can_replace_structured_fact") is False
        and phase2_result.get("summary_can_become_numeric_statistical_evidence")
        is False
        and phase2_result.get("model_direct_text_guessing_allowed") is False
        and phase2_result.get("unverified_numeric_value_as_definitive_fact_allowed")
        is False
        and len(candidates) == 2
        and all(_candidate_has_expected_control_shape(candidate) for candidate in candidates)
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
        "unique_rag_summary_candidate_count": len(
            {
                item["referenced_rag_summary_id"]
                for item in scenario_results
                if isinstance(item["referenced_rag_summary_id"], str)
            }
        ),
        "source_location_reference_check_count": len(scenario_results),
        "control_source_location_traceability_preserved": traceability_preserved,
        "all_summary_text_unset": all(
            item["summary_text_unset"] for item in scenario_results
        ),
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "all_taskpack_exception_categories_covered": categories_covered,
        "scenario_results": scenario_results,
        "source_document_remains_authoritative": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "numeric_statistical_conclusion_allowed": False,
        "model_direct_text_guessing_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_structured_fact_created": False,
        "actual_numeric_fact_created": False,
        "actual_rag_summary_created": False,
        "actual_summary_text_retained": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
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
        "rag_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
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
        "stage060_started": True,
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
            "已完成固定表格摘要控制候选的异常场景验证；结果只说明控制处置和引用形状，不代表真实表格、真实来源位置或业务摘要质量结论。",
            "空表、合并单元格、单位混乱、日期格式不一和重复行均需人工处理，系统不会自动修正、摘要或写入。",
            "未验证数值不得形成统计结论或模型确定性数值结论，须等待可追溯的结构化事实与证据流程。",
            "每个控制场景保留来源文档、工作簿、工作表、行列范围和 evidence 引用；这些是控制引用，不是已验证的真实文件位置。",
        ],
    }


def _load_phase2_executor() -> Phase2Executor:
    path = Path(__file__).with_name("stage060_table_rag_summary_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage060_table_rag_summary_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage060 P2 table RAG summary control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_table_rag_summary_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实表格、事实或业务摘要。"""

    return {
        "table_rag_summary_input_records": [
            {
                "summary_scope_ref": "summary-scope:control:stage060-p2:production",
                "fact_set_ref": "fact-set:control:stage060-p2:production",
                "fact_id_ref": "fact-ref:control:stage060-p2:production",
                "fact_type": "PRODUCTION_FACT",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage060-p2:production",
                "workbook_ref": "workbook:control:stage060-p2:production",
                "worksheet_ref": "worksheet:control:stage060-p2:production",
                "row_range_ref": "row-range:control:stage060-p2:production",
                "column_range_ref": "column-range:control:stage060-p2:production",
                "schema_profile_ref": "schema-profile:control:stage060-p2:production",
                "evidence_ref": "evidence:control:stage060-p2:production",
                "rag_summary_eligibility": (
                    "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
                ),
            },
            {
                "summary_scope_ref": "summary-scope:control:stage060-p2:quality",
                "fact_set_ref": "fact-set:control:stage060-p2:quality",
                "fact_id_ref": "fact-ref:control:stage060-p2:quality",
                "fact_type": "QUALITY_FACT",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_document_ref": "source-document:control:stage060-p2:quality",
                "workbook_ref": "workbook:control:stage060-p2:quality",
                "worksheet_ref": "worksheet:control:stage060-p2:quality",
                "row_range_ref": "row-range:control:stage060-p2:quality",
                "column_range_ref": "column-range:control:stage060-p2:quality",
                "schema_profile_ref": "schema-profile:control:stage060-p2:quality",
                "evidence_ref": "evidence:control:stage060-p2:quality",
                "rag_summary_eligibility": (
                    "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
                ),
            },
        ]
    }


def _summary_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("rag_summary_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _candidate_has_expected_control_shape(candidate: Mapping[str, Any]) -> bool:
    fact_references = candidate.get("fact_reference_list")
    return (
        len(candidate) == 10
        and "summary_text" not in candidate
        and isinstance(fact_references, list)
        and len(fact_references) == 1
        and all(isinstance(value, str) and ":control:" in value for value in fact_references)
        and _source_location_preserved(candidate)
        and candidate.get("summary_language") == "zh-CN"
        and candidate.get("summary_state")
        == "CANDIDATE_REFERENCE_ONLY_NOT_PERSISTED"
        and candidate.get("numeric_claim_state") == "FACT_REFERENCE_ONLY_NO_NUMERIC_CLAIM"
        and candidate.get("human_review_state") == "PENDING_HUMAN_CONFIRMATION"
    )


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    candidate = _candidate_for_fact_type(scenario, candidates)
    location_preserved = _source_location_preserved(candidate)
    control_reference_only = _control_reference_only(candidate)
    summary_text_unset = candidate is not None and "summary_text" not in candidate
    explicit_disposition = isinstance(scenario["quality_disposition"], str)
    numeric_block = bool(
        scenario["unverified_numeric_blocks_statistical_conclusion"]
    )
    expectation_met = (
        candidate is not None
        and location_preserved
        and control_reference_only
        and summary_text_unset
        and explicit_disposition
        and bool(scenario["human_handling_required"])
        and side_effect_free
    )
    source_references = _source_references(candidate)
    fact_references = (
        candidate.get("fact_reference_list")
        if isinstance(candidate, Mapping)
        else []
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "control_scenario_metadata_only": True,
        "candidate_selector_field": "fact_type",
        "candidate_selector_value": scenario["candidate_fact_type"],
        "referenced_rag_summary_id": _value(candidate, "rag_summary_id"),
        "referenced_fact_id": (
            fact_references[0]
            if isinstance(fact_references, list) and len(fact_references) == 1
            else None
        ),
        "source_document_ref": source_references.get("source_document_ref"),
        "workbook_ref": source_references.get("workbook_ref"),
        "worksheet_ref": source_references.get("worksheet_ref"),
        "row_range_ref": source_references.get("row_range_ref"),
        "column_range_ref": source_references.get("column_range_ref"),
        "evidence_ref": source_references.get("evidence_ref"),
        "source_location_reference_preserved": location_preserved,
        "control_reference_only": control_reference_only,
        "summary_text_unset": summary_text_unset,
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
        "actual_structured_fact_created": False,
        "actual_rag_summary_created": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
    }


def _candidate_for_fact_type(
    scenario: Mapping[str, object], candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    fact_type = scenario.get("candidate_fact_type")
    if not isinstance(fact_type, str):
        return None
    return next(
        (
            item
            for item in candidates
            if isinstance(item.get("rag_summary_id"), str)
            and fact_type.lower() in str(item.get("rag_summary_id")).lower()
        ),
        None,
    )


def _source_location_preserved(candidate: Mapping[str, Any] | None) -> bool:
    if candidate is None:
        return False
    locations = candidate.get("source_location_ref_list")
    return (
        isinstance(locations, list)
        and len(locations) == 6
        and all(isinstance(value, str) and ":control:" in value for value in locations)
        and isinstance(candidate.get("evidence_ref"), str)
        and ":control:" in str(candidate.get("evidence_ref"))
    )


def _source_references(candidate: Mapping[str, Any] | None) -> dict[str, object]:
    if candidate is None:
        return {}
    locations = candidate.get("source_location_ref_list")
    if not isinstance(locations, list) or len(locations) != 6:
        return {}
    return {
        "source_document_ref": locations[0],
        "workbook_ref": locations[1],
        "worksheet_ref": locations[2],
        "row_range_ref": locations[3],
        "column_range_ref": locations[4],
        "evidence_ref": locations[5],
    }


def _control_reference_only(candidate: Mapping[str, Any] | None) -> bool:
    if candidate is None:
        return False
    values = [
        candidate.get("rag_summary_id"),
        candidate.get("summary_scope_ref"),
        candidate.get("fact_set_ref"),
        candidate.get("evidence_ref"),
    ]
    fact_references = candidate.get("fact_reference_list")
    locations = candidate.get("source_location_ref_list")
    return (
        all(isinstance(value, str) and ":control:" in value for value in values)
        and isinstance(fact_references, list)
        and all(
            isinstance(value, str) and ":control:" in value for value in fact_references
        )
        and isinstance(locations, list)
        and all(isinstance(value, str) and ":control:" in value for value in locations)
    )


def _value(candidate: Mapping[str, Any] | None, field: str) -> object | None:
    return candidate.get(field) if candidate is not None else None
