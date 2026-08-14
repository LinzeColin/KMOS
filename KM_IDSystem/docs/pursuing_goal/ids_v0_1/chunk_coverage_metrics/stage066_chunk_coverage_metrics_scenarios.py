"""Stage066 P3 的 Chunk 覆盖率指标受控专项场景。

本模块只重放 Stage066 P2 的四条固定、非业务、reference-only 控制记录。长文档、
跨页表格、施工步骤、参数表、引用页码与重复 chunk 写入边界仅是控制场景标签；
不会读取来源、验证真实切块质量、检测真实重复项，或执行 embedding、索引及任何
持久化写入。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage066.chunk_coverage_metrics.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_CHUNK_COVERAGE_METRICS_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE066-P4-GATE"
PHASE2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_CHUNK_COVERAGE_METRICS_CONTROL_SLICE"
PHASE2_SCENARIOS = (
    "procedure",
    "acceptance",
    "parameter_table",
    "unknown_denominator",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
METRIC_RECORD_FIELDS = (
    "chunk_coverage_metrics_record_ref",
    "chunk_coverage_request_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "document_ref",
    "parser_output_ref",
    "parse_coverage_status",
    "parse_coverage_ratio",
    "chunk_coverage_status",
    "chunk_coverage_ratio",
    "uncovered_page_refs",
    "human_review_state",
    "page_ref",
    "section_ref",
    "table_context_ref",
    "source_fragment_ref",
)
CONTROL_REFERENCE_RECORD_FIELDS = (
    "chunk_coverage_metrics_record_ref",
    "chunk_coverage_request_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "document_ref",
    "parser_output_ref",
    "parse_coverage_ratio",
    "chunk_coverage_ratio",
    "page_ref",
    "section_ref",
    "table_context_ref",
    "source_fragment_ref",
)
REQUIRED_SCENARIO_CATEGORIES = (
    "LONG_DOCUMENT_CONTROL",
    "CROSS_PAGE_TABLE_CONTROL",
    "ENGINEERING_PROCEDURE_CONTROL",
    "PARAMETER_TABLE_CONTROL",
    "CITATION_PAGE_TRACEABILITY_CONTROL",
    "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
)
SIDE_EFFECT_FIELDS = (
    "actual_chapter_boundary_detected",
    "actual_protected_surface_split_detected",
    "actual_chunk_created",
    "actual_chunk_persisted",
    "actual_chunk_id_generated",
    "actual_chunk_hash_computed",
    "actual_chunk_version_generated",
    "actual_parse_coverage_calculated",
    "actual_chunk_coverage_calculated",
    "actual_uncovered_page_detected",
    "actual_low_quality_chunk_detected",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "source_traceability_binding_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chapter_detection_performed",
    "chunking_execution_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)
SCENARIOS = (
    {
        "scenario_id": "long-document-coverage-control-human-review",
        "scenario_category": "LONG_DOCUMENT_CONTROL",
        "record_scenario": "procedure",
        "protected_semantic_surface": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "LONG_DOCUMENT_COVERAGE_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "cross-page-table-coverage-control-human-handling",
        "scenario_category": "CROSS_PAGE_TABLE_CONTROL",
        "record_scenario": "parameter_table",
        "protected_semantic_surface": "PARAMETER_TABLE",
        "explicit_disposition": "CROSS_PAGE_TABLE_COVERAGE_CONTROL_REQUIRES_HUMAN_HANDLING",
    },
    {
        "scenario_id": "engineering-procedure-coverage-control-human-review",
        "scenario_category": "ENGINEERING_PROCEDURE_CONTROL",
        "record_scenario": "procedure",
        "protected_semantic_surface": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "ENGINEERING_PROCEDURE_COVERAGE_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "parameter-table-coverage-control-human-review",
        "scenario_category": "PARAMETER_TABLE_CONTROL",
        "record_scenario": "parameter_table",
        "protected_semantic_surface": "PARAMETER_TABLE",
        "explicit_disposition": "PARAMETER_TABLE_COVERAGE_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "citation-page-coverage-control-human-confirmation",
        "scenario_category": "CITATION_PAGE_TRACEABILITY_CONTROL",
        "record_scenario": "acceptance",
        "protected_semantic_surface": "ACCEPTANCE_CLAUSE",
        "explicit_disposition": "CITATION_PAGE_COVERAGE_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION",
    },
    {
        "scenario_id": "duplicate-chunk-coverage-control-human-review",
        "scenario_category": "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
        "record_scenario": "unknown_denominator",
        "protected_semantic_surface": None,
        "explicit_disposition": (
            "DUPLICATE_CHUNK_COVERAGE_CONTROL_REQUIRES_LATER_IDENTITY_AND_HUMAN_REVIEW"
        ),
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_chunk_coverage_metrics_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制记录并输出不含真实来源内容的专项场景报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    records = _coverage_metric_records(phase2_result)
    side_effect_free = all(
        phase2_result.get(field, False) is False for field in SIDE_EFFECT_FIELDS
    )
    phase2_shape_preserved = _phase2_shape_preserved(phase2_result, records)
    scenario_results = [
        _evaluate_scenario(scenario, records, side_effect_free) for scenario in SCENARIOS
    ]
    categories_covered = tuple(
        item["scenario_category"] for item in scenario_results
    ) == REQUIRED_SCENARIO_CATEGORIES
    traceability_preserved = all(
        item["control_traceability_reference_preserved"] for item in scenario_results
    )
    duplicate_boundary_preserved = (
        all(
            item["duplicate_embedding_or_index_write_attempted"] is False
            for item in scenario_results
        )
        and any(
            item["deduplication_control_prohibition_asserted"]
            for item in scenario_results
        )
    )
    valid = (
        phase2_shape_preserved
        and categories_covered
        and len(scenario_results) == len(REQUIRED_SCENARIO_CATEGORIES)
        and all(item["expectation_met"] for item in scenario_results)
        and all(item["explicit_disposition"] for item in scenario_results)
        and not any(item["silent_drop"] for item in scenario_results)
        and traceability_preserved
        and duplicate_boundary_preserved
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
        "all_taskpack_special_scenarios_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "unique_control_metric_record_count": len(
            {
                item["referenced_chunk_coverage_metrics_record_ref"]
                for item in scenario_results
                if isinstance(item["referenced_chunk_coverage_metrics_record_ref"], str)
            }
        ),
        "scenario_results": scenario_results,
        "control_traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_check_count": sum(
            item["control_traceability_reference_count"] for item in scenario_results
        ),
        "control_traceability_reference_shape_preserved": traceability_preserved,
        "actual_source_document_read_performed": False,
        "actual_page_traceability_validated": False,
        "actual_source_traceability_binding_created": False,
        "actual_duplicate_chunk_detected": False,
        "actual_duplicate_chunk_identity_or_hash_validated": False,
        "control_duplicate_write_prohibition_asserted": duplicate_boundary_preserved,
        "actual_duplicate_embedding_prevented": False,
        "actual_duplicate_index_prevented": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "actual_input_request_count": 0,
        "actual_chunk_count": 0,
        "actual_chunk_coverage_metrics_record_count": 0,
        "actual_traceability_binding_count": 0,
        "source_document_remains_authoritative": True,
        "coverage_metric_control_record_can_replace_source_document": False,
        "coverage_metric_control_record_can_become_business_fact_authority": False,
        "model_direct_text_guessing_allowed": False,
        "model_decision_conclusion_authoritative": False,
        **_runtime_closed_flags(),
        "stage066_started": True,
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
            "已完成六类固定 Chunk 覆盖率指标专项控制场景；结果只说明控制处置与引用形状，不代表真实切块质量、覆盖率质量或业务结论。",
            "长文档、跨页表格、施工步骤、参数表和引用页码均保留业务线白箱人工复核，系统没有读取、切分、计算或写入真实来源。",
            "重复 chunk 场景仅确认本控制模块没有发起 embedding 或索引写入；没有检测真实重复项，也没有形成真实去重效果结论。",
            "每个场景仅保留文档、页码、章节、解析输出、表格上下文和来源片段的控制引用，真实来源反查仍须人工确认。",
        ],
    }


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage066_chunk_coverage_metrics_slice.py")
    spec = importlib.util.spec_from_file_location("stage066_p2", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage066 P2 chunk coverage control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_phase2_executor() -> Phase2Executor:
    executor = _load_phase2_module().execute_chunk_coverage_metrics_control_slice
    if not callable(executor):
        raise RuntimeError("Stage066 P2 chunk coverage control executor is unavailable")
    return executor


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实文档、页面、章节或表格内容。"""

    module = _load_phase2_module()
    return {
        "chunk_coverage_metric_requests": [
            module.build_control_request(scenario)
            for scenario in module.CONTROL_SCENARIOS
        ]
    }


def _coverage_metric_records(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = result.get("chunk_coverage_metric_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _phase2_shape_preserved(
    result: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> bool:
    return (
        result.get("input_accepted") is True
        and result.get("execution_state") == PHASE2_EXECUTION_STATE
        and result.get("control_chunk_coverage_metric_request_count") == 4
        and result.get("actual_input_request_count") == 0
        and result.get("chunk_coverage_metric_record_count") == 4
        and result.get("control_scenarios_covered") == list(PHASE2_SCENARIOS)
        and result.get("protected_semantic_asset_types_covered")
        == ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"]
        and result.get("traceability_field_count") == len(TRACEABILITY_FIELDS)
        and result.get("control_traceability_reference_count") == 24
        and result.get("control_traceability_reference_shape_preserved") is True
        and result.get("all_protected_surfaces_atomic") is True
        and result.get("unknown_denominator_control_record_count") == 1
        and result.get("all_control_records_low_confidence_requires_human_review")
        is True
        and len(records) == 4
        and all(_record_has_expected_control_shape(record) for record in records)
    )


def _record_has_expected_control_shape(record: Mapping[str, Any]) -> bool:
    return (
        set(record) == set(METRIC_RECORD_FIELDS)
        and isinstance(record.get("parse_coverage_status"), str)
        and isinstance(record.get("chunk_coverage_status"), str)
        and isinstance(record.get("human_review_state"), str)
        and _control_traceability_preserved(record)
        and _control_reference_only(record)
        and isinstance(record.get("uncovered_page_refs"), tuple)
        and len(record["uncovered_page_refs"]) == 1
        and isinstance(record["uncovered_page_refs"][0], str)
        and ":control:" in record["uncovered_page_refs"][0]
    )


def _evaluate_scenario(
    scenario: Mapping[str, object],
    records: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    record_scenario = str(scenario["record_scenario"])
    record = _record_for_scenario(record_scenario, records)
    traceability_preserved = _control_traceability_preserved(record)
    control_reference_only = _control_reference_only(record)
    expected_record = (
        record is not None
        and _record_has_expected_control_shape(record)
        and record.get("chunk_coverage_request_ref", "").endswith(
            f":{record_scenario}"
        )
    )
    disposition = scenario["explicit_disposition"]
    expectation_met = (
        expected_record
        and traceability_preserved
        and control_reference_only
        and isinstance(disposition, str)
        and bool(disposition)
        and side_effect_free
    )
    category = str(scenario["scenario_category"])
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": category,
        "referenced_chunk_coverage_metrics_record_ref": (
            record.get("chunk_coverage_metrics_record_ref") if record else None
        ),
        "referenced_chunk_coverage_request_ref": (
            record.get("chunk_coverage_request_ref") if record else None
        ),
        "referenced_chapter_aware_chunk_ref": (
            record.get("chapter_aware_chunk_ref") if record else None
        ),
        "referenced_chunk_identity_version_record_ref": (
            record.get("chunk_identity_version_record_ref") if record else None
        ),
        "referenced_engineering_semantic_asset_catalog_ref": (
            record.get("engineering_semantic_asset_catalog_ref") if record else None
        ),
        "document_ref": record.get("document_ref") if record else None,
        "page_ref": record.get("page_ref") if record else None,
        "section_ref": record.get("section_ref") if record else None,
        "parser_output_ref": record.get("parser_output_ref") if record else None,
        "table_context_ref": record.get("table_context_ref") if record else None,
        "source_fragment_ref": record.get("source_fragment_ref") if record else None,
        "protected_semantic_surface": scenario["protected_semantic_surface"],
        "explicit_disposition": disposition,
        "human_handling_required": True,
        "control_traceability_reference_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_preserved": traceability_preserved,
        "control_reference_only": control_reference_only,
        "actual_long_document_quality_validated": False,
        "actual_cross_page_table_relation_validated": False,
        "actual_page_traceability_validated": False,
        "actual_source_traceability_binding_created": False,
        "actual_duplicate_chunk_detected": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "deduplication_control_prohibition_asserted": (
            category == "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL"
        ),
        "control_scenario_metadata_only": True,
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _record_for_scenario(
    record_scenario: str, records: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    return next(
        (
            record
            for record in records
            if isinstance(record.get("chunk_coverage_request_ref"), str)
            and record["chunk_coverage_request_ref"].endswith(f":{record_scenario}")
        ),
        None,
    )


def _control_traceability_preserved(record: Mapping[str, Any] | None) -> bool:
    return record is not None and all(
        isinstance(record.get(field), str) and ":control:" in record[field]
        for field in TRACEABILITY_FIELDS
    )


def _control_reference_only(record: Mapping[str, Any] | None) -> bool:
    return record is not None and all(
        isinstance(record.get(field), str) and ":control:" in record[field]
        for field in CONTROL_REFERENCE_RECORD_FIELDS
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in SIDE_EFFECT_FIELDS}
