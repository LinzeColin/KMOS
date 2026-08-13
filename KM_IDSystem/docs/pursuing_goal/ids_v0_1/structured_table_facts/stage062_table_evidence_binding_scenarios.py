"""Stage062 P3 的表格证据绑定受控异常场景验证。

本模块只重放 Stage062 P2 的两条固定、非业务、reference-only 控制请求及其
两个未绑定候选。空表、合并单元格、单位混乱、日期格式不一、异常值和重复行
只是控制类别标签；不会读取、打开、解析、统计、绑定或保存任何真实表格内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage062.table_evidence_binding.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_TABLE_EVIDENCE_BINDING_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE062-P4-GATE"

BINDING_CANDIDATE_FIELDS = (
    "table_evidence_binding_ref",
    "binding_request_ref",
    "fact_ref",
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
    "field_candidate_ref",
    "schema_profile_ref",
    "quality_result_ref",
    "fact_type",
    "binding_state",
    "human_review_state",
    "numeric_authority_state",
    "remediation_state",
)
BINDING_DIMENSIONS = (
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
)
SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "table_schema_inference_performed",
    "field_identification_performed",
    "structured_fact_extraction_performed",
    "typed_value_extraction_performed",
    "table_summary_generation_performed",
    "numeric_statistic_computation_performed",
    "quality_gate_evaluation_performed",
    "source_location_binding_performed",
    "evidence_binding_performed",
    "actual_structured_fact_created",
    "actual_table_evidence_binding_created",
    "actual_table_evidence_binding_persisted",
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
        "scenario_id": "empty-table-binding-control-human-handling",
        "scenario_category": "EMPTY_TABLE_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:production",
        "fact_type": "MEASUREMENT_FACT",
        "explicit_disposition": "EMPTY_TABLE_REFERENCE_REQUIRES_HUMAN_HANDLING",
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "merged-cells-binding-control-human-handling",
        "scenario_category": "MERGED_CELLS_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:quality",
        "fact_type": "QUALITY_RESULT_FACT",
        "explicit_disposition": "MERGED_CELL_REFERENCE_REQUIRES_HUMAN_HANDLING",
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "unit-confusion-binding-control-human-handling",
        "scenario_category": "UNIT_CONFUSION_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:production",
        "fact_type": "MEASUREMENT_FACT",
        "explicit_disposition": "UNVERIFIED_UNIT_REFERENCE_REQUIRES_HUMAN_HANDLING",
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "date-variation-binding-control-human-handling",
        "scenario_category": "DATE_FORMAT_VARIATION_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:quality",
        "fact_type": "QUALITY_RESULT_FACT",
        "explicit_disposition": "UNVERIFIED_DATE_REFERENCE_REQUIRES_HUMAN_HANDLING",
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
    {
        "scenario_id": "outlier-binding-control-numeric-block",
        "scenario_category": "OUTLIER_VALUE_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:production",
        "fact_type": "MEASUREMENT_FACT",
        "explicit_disposition": "UNVERIFIED_NUMERIC_REFERENCE_BLOCKS_STATISTICAL_CONCLUSION",
        "unverified_numeric_blocks_statistical_conclusion": True,
    },
    {
        "scenario_id": "duplicate-row-binding-control-human-handling",
        "scenario_category": "DUPLICATE_ROW_CONTROL",
        "binding_request_ref": "binding-request:control:stage062-p2:quality",
        "fact_type": "QUALITY_RESULT_FACT",
        "explicit_disposition": "DUPLICATE_ROW_REFERENCE_REQUIRES_HUMAN_HANDLING",
        "unverified_numeric_blocks_statistical_conclusion": False,
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_table_evidence_binding_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制候选，输出不含真实表格内容的异常场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    candidates = _binding_candidates(phase2_result)
    side_effect_free = all(phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_TABLE_EVIDENCE_BINDING_CANDIDATE_CONTROL_SLICE"
        and phase2_result.get("control_binding_request_count") == 2
        and phase2_result.get("actual_input_record_count") == 0
        and phase2_result.get("table_evidence_binding_candidate_count") == 2
        and phase2_result.get("binding_dimension_count") == len(BINDING_DIMENSIONS)
        and phase2_result.get("control_binding_dimension_reference_count") == 12
        and phase2_result.get("source_location_reference_shape_preserved") is True
        and phase2_result.get("all_binding_states_unbound") is True
        and phase2_result.get("all_human_review_required") is True
        and phase2_result.get("all_numeric_authority_blocked") is True
        and len(candidates) == 2
        and all(_candidate_has_expected_control_shape(candidate) for candidate in candidates)
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates, side_effect_free) for scenario in SCENARIOS
    ]
    categories_covered = {
        str(scenario["scenario_category"]) for scenario in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    traceability_preserved = all(
        item["control_source_location_reference_preserved"] for item in scenario_results
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
            bool(item["explicit_disposition"]) for item in scenario_results
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in scenario_results),
        "human_handling_required_count": sum(
            item["human_handling_required"] for item in scenario_results
        ),
        "all_taskpack_exception_categories_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "unique_table_evidence_binding_candidate_count": len(
            {
                item["referenced_table_evidence_binding_ref"]
                for item in scenario_results
                if isinstance(item["referenced_table_evidence_binding_ref"], str)
            }
        ),
        "scenario_results": scenario_results,
        "control_source_location_field_count": len(BINDING_DIMENSIONS),
        "control_source_location_reference_check_count": sum(
            item["control_source_location_reference_preserved"]
            for item in scenario_results
        ),
        "control_source_location_traceability_preserved": traceability_preserved,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_structured_fact_created": False,
        "actual_table_evidence_binding_created": False,
        "actual_table_evidence_binding_persisted": False,
        "actual_input_record_count": 0,
        "actual_structured_fact_count": 0,
        "actual_numeric_fact_count": 0,
        "actual_source_location_binding_count": 0,
        "actual_evidence_binding_count": 0,
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
        "source_document_remains_authoritative": True,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "numeric_statistical_conclusion_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "source_location_binding_performed": False,
        "evidence_binding_performed": False,
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
        "stage062_started": True,
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
            "已完成六类固定异常场景的控制验证；结果只说明控制处置和六维引用形状，不代表真实表格、真实来源位置或业务结论。",
            "空表、合并单元格、单位混乱、日期格式不一和重复行均需人工处理，系统不会自动修正、绑定或写入。",
            "异常值控制场景和全部未验证数值均不得形成统计结论或模型确定性数值结论，必须等待可追溯的结构化事实与证据流程。",
            "每个场景只保留 evidence_id、document_id、sheet、row、column 和 source_uri 的控制引用；这些不是已验证的真实文件位置。",
        ],
    }


def _load_phase2_executor() -> Phase2Executor:
    path = Path(__file__).with_name("stage062_table_evidence_binding_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage062_table_evidence_binding_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage062 P2 table-evidence binding control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_table_evidence_binding_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实表格、行列或单元格内容。"""

    records: list[dict[str, object]] = []
    for suffix, file_format, record_type, fact_type in (
        ("production", "XLSX", "PRODUCTION_RECORD", "MEASUREMENT_FACT"),
        ("quality", "CSV", "QUALITY_INSPECTION_RECORD", "QUALITY_RESULT_FACT"),
    ):
        records.append(
            {
                "binding_request_ref": f"binding-request:control:stage062-p2:{suffix}",
                "fact_ref": f"fact:control:stage062-p2:{suffix}",
                "evidence_id": f"evidence-id:control:stage062-p2:{suffix}",
                "document_id": f"document-id:control:stage062-p2:{suffix}",
                "sheet": f"sheet:control:stage062-p2:{suffix}",
                "row": f"row:control:stage062-p2:{suffix}",
                "column": f"column:control:stage062-p2:{suffix}",
                "source_uri": f"source-uri:control:stage062-p2:{suffix}",
                "file_format": file_format,
                "record_type": record_type,
                "workbook_ref": f"workbook:control:stage062-p2:{suffix}",
                "schema_profile_ref": f"schema-profile:control:stage062-p2:{suffix}",
                "field_candidate_ref": f"field-candidate:control:stage062-p2:{suffix}",
                "primary_key_ref": f"primary-key:control:stage062-p2:{suffix}",
                "quality_result_ref": f"quality-result:control:stage062-p2:{suffix}",
                "measurement_value_ref": f"measurement-value:control:stage062-p2:{suffix}",
                "unit_ref": f"unit:control:stage062-p2:{suffix}",
                "record_date_ref": f"record-date:control:stage062-p2:{suffix}",
                "fact_type": fact_type,
            }
        )
    return {"table_evidence_binding_requests": records}


def _binding_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("table_evidence_binding_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _candidate_has_expected_control_shape(candidate: Mapping[str, Any]) -> bool:
    return (
        set(candidate) == set(BINDING_CANDIDATE_FIELDS)
        and candidate.get("binding_state") == "UNBOUND_REFERENCE_ONLY"
        and candidate.get("human_review_state") == "REQUIRED_WHEN_UNVERIFIED"
        and candidate.get("numeric_authority_state")
        == "BLOCKED_UNVERIFIED_REFERENCE_ONLY"
        and candidate.get("remediation_state")
        == "HUMAN_SOURCE_AND_EVIDENCE_CONFIRMATION_REQUIRED"
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
    disposition = scenario["explicit_disposition"]
    numeric_block = bool(scenario["unverified_numeric_blocks_statistical_conclusion"])
    expected_candidate = (
        candidate is not None
        and candidate.get("binding_request_ref") == scenario["binding_request_ref"]
        and candidate.get("fact_type") == scenario["fact_type"]
        and _candidate_has_expected_control_shape(candidate)
    )
    expectation_met = (
        expected_candidate
        and location_preserved
        and control_reference_only
        and isinstance(disposition, str)
        and bool(disposition)
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "referenced_table_evidence_binding_ref": (
            candidate.get("table_evidence_binding_ref") if candidate else None
        ),
        "referenced_binding_request_ref": scenario["binding_request_ref"],
        "referenced_fact_ref": candidate.get("fact_ref") if candidate else None,
        "evidence_id": candidate.get("evidence_id") if candidate else None,
        "document_id": candidate.get("document_id") if candidate else None,
        "sheet": candidate.get("sheet") if candidate else None,
        "row": candidate.get("row") if candidate else None,
        "column": candidate.get("column") if candidate else None,
        "source_uri": candidate.get("source_uri") if candidate else None,
        "fact_type": scenario["fact_type"],
        "explicit_disposition": disposition,
        "human_handling_required": True,
        "unverified_numeric_blocks_statistical_conclusion": numeric_block,
        "numeric_statistical_conclusion_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "control_source_location_reference_preserved": location_preserved,
        "control_reference_only": control_reference_only,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "control_scenario_metadata_only": True,
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _candidate_for_scenario(
    scenario: Mapping[str, object], candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    return next(
        (
            candidate
            for candidate in candidates
            if candidate.get("binding_request_ref") == scenario["binding_request_ref"]
        ),
        None,
    )


def _source_location_preserved(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(candidate.get(field), str) and ":control:" in candidate[field]
        for field in BINDING_DIMENSIONS
    )


def _control_reference_only(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(value, str) and ":control:" in value
        for value in (
            candidate.get("table_evidence_binding_ref"),
            candidate.get("binding_request_ref"),
            candidate.get("fact_ref"),
            candidate.get("field_candidate_ref"),
            candidate.get("schema_profile_ref"),
            candidate.get("quality_result_ref"),
            *[candidate.get(field) for field in BINDING_DIMENSIONS],
        )
    )


def _human_count(
    results: Sequence[Mapping[str, Any]], scenario_category: str
) -> int:
    return sum(
        item["human_handling_required"]
        for item in results
        if item["scenario_category"] == scenario_category
    )
