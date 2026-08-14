"""Stage068 P3 的质量降级受控专项场景。

本模块只重放 Stage068 P2 的四条固定、非业务、reference-only 控制记录。长文档、
跨页表格、施工步骤、参数表、引用页码与重复 chunk 写入边界仅是控制场景标签；
不会读取来源、验证真实质量或质量降级、检测真实重复项，或执行 embedding、索引
及任何持久化写入。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage068.quality_degradation.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_QUALITY_DEGRADATION_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE068-P4-GATE"
PHASE2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_QUALITY_DEGRADATION_CONTROL_SLICE"
PHASE2_SCENARIOS = (
    "procedure",
    "acceptance",
    "parameter_table",
    "duplicate_chunk",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
QUALITY_DEGRADATION_RECORD_FIELDS = (
    "quality_degradation_record_ref",
    "quality_degradation_request_ref",
    "chunk_quality_regression_record_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "chunk_coverage_metrics_record_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "protected_semantic_boundary_status",
    "duplicate_embedding_index_status",
    "quality_degradation_status",
    "low_confidence_evidence_state",
    "human_review_state",
    "quality_degradation_reason_code",
)
CONTROL_REFERENCE_RECORD_FIELDS = (
    "quality_degradation_record_ref",
    "quality_degradation_request_ref",
    "chunk_quality_regression_record_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "chunk_coverage_metrics_record_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
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
    "actual_engineering_semantic_asset_classified",
    "actual_coverage_metric_calculated",
    "actual_quality_regression_record_created",
    "actual_quality_measurement_performed",
    "actual_quality_regression_performed",
    "actual_quality_degradation_record_created",
    "actual_quality_degradation_performed",
    "actual_low_confidence_evidence_created",
    "actual_low_quality_chunk_detected",
    "actual_duplicate_chunk_detected",
    "actual_duplicate_chunk_identity_or_hash_validated",
    "actual_duplicate_embedding_prevented",
    "actual_duplicate_index_prevented",
    "duplicate_embedding_or_index_write_attempted",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "low_confidence_evidence_creation_performed",
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
PROTECTED_SURFACE_STATUS = "CONTROL_PROTECTED_SEMANTIC_SURFACE_REQUIRES_HUMAN_HANDLING"
CONTROL_REFERENCE_ONLY_STATUS = "CONTROL_REFERENCE_ONLY_UNASSESSED_REQUIRES_HUMAN_REVIEW"
DUPLICATE_BOUNDARY_STATUS = (
    "CONTROL_DUPLICATE_CHUNK_NO_EMBEDDING_OR_INDEX_WRITE_REQUIRES_HUMAN_REVIEW"
)
QUALITY_DEGRADATION_STATUS = (
    "CONTROL_DEGRADED_NOT_COMPLETE_FAILURE_REQUIRES_HUMAN_REVIEW"
)
LOW_CONFIDENCE_EVIDENCE_STATE = (
    "CONTROL_LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW"
)
BUSINESS_LINE_WHITEBOX_REVIEW_STATE = "REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW"
LOW_CONFIDENCE_EVIDENCE_REVIEW_STATE = "LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW"
SCENARIOS = (
    {
        "scenario_id": "long-document-quality-degradation-control-human-review",
        "scenario_category": "LONG_DOCUMENT_CONTROL",
        "record_scenario": "procedure",
        "protected_semantic_surface": "ENGINEERING_PROCEDURE_STEP",
        "required_review_state": BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
        "explicit_disposition": (
            "LONG_DOCUMENT_QUALITY_DEGRADATION_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW"
        ),
    },
    {
        "scenario_id": "cross-page-table-quality-degradation-control-human-handling",
        "scenario_category": "CROSS_PAGE_TABLE_CONTROL",
        "record_scenario": "parameter_table",
        "protected_semantic_surface": "PARAMETER_TABLE",
        "required_review_state": BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
        "explicit_disposition": (
            "CROSS_PAGE_TABLE_QUALITY_DEGRADATION_CONTROL_REQUIRES_HUMAN_HANDLING"
        ),
    },
    {
        "scenario_id": "engineering-procedure-quality-degradation-control-human-review",
        "scenario_category": "ENGINEERING_PROCEDURE_CONTROL",
        "record_scenario": "procedure",
        "protected_semantic_surface": "ENGINEERING_PROCEDURE_STEP",
        "required_review_state": BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
        "explicit_disposition": (
            "ENGINEERING_PROCEDURE_QUALITY_DEGRADATION_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW"
        ),
    },
    {
        "scenario_id": "parameter-table-quality-degradation-control-human-review",
        "scenario_category": "PARAMETER_TABLE_CONTROL",
        "record_scenario": "parameter_table",
        "protected_semantic_surface": "PARAMETER_TABLE",
        "required_review_state": BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
        "explicit_disposition": (
            "PARAMETER_TABLE_QUALITY_DEGRADATION_CONTROL_REQUIRES_HUMAN_BOUNDARY_REVIEW"
        ),
    },
    {
        "scenario_id": "citation-page-quality-degradation-control-human-confirmation",
        "scenario_category": "CITATION_PAGE_TRACEABILITY_CONTROL",
        "record_scenario": "acceptance",
        "protected_semantic_surface": "ACCEPTANCE_CLAUSE",
        "required_review_state": BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
        "explicit_disposition": (
            "CITATION_PAGE_QUALITY_DEGRADATION_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION"
        ),
    },
    {
        "scenario_id": "duplicate-chunk-quality-degradation-control-human-review",
        "scenario_category": "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
        "record_scenario": "duplicate_chunk",
        "protected_semantic_surface": None,
        "required_review_state": LOW_CONFIDENCE_EVIDENCE_REVIEW_STATE,
        "explicit_disposition": (
            "DUPLICATE_CHUNK_QUALITY_DEGRADATION_CONTROL_REQUIRES_LOW_CONFIDENCE_EVIDENCE_HUMAN_REVIEW"
        ),
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_quality_degradation_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制记录并输出不含真实来源内容的专项场景报告。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    phase2_result = executor(_phase2_control_input(phase2_module))
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    records = _quality_degradation_records(phase2_result)
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
    low_quality_boundary_preserved = all(
        item["low_quality_is_not_automatic_complete_failure"]
        for item in scenario_results
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
        and low_quality_boundary_preserved
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
        "unique_control_quality_degradation_record_count": len(
            {
                item["referenced_quality_degradation_record_ref"]
                for item in scenario_results
                if isinstance(
                    item["referenced_quality_degradation_record_ref"], str
                )
            }
        ),
        "scenario_results": scenario_results,
        "control_traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_check_count": sum(
            item["control_traceability_reference_count"] for item in scenario_results
        ),
        "control_traceability_reference_shape_preserved": traceability_preserved,
        "low_quality_is_not_automatic_complete_failure": low_quality_boundary_preserved,
        "actual_source_document_read_performed": False,
        "actual_long_document_quality_validated": False,
        "actual_cross_page_table_relation_validated": False,
        "actual_protected_semantic_boundary_validated": False,
        "actual_page_traceability_validated": False,
        "actual_source_traceability_binding_created": False,
        "actual_quality_degradation_validated": False,
        "actual_low_confidence_evidence_created": False,
        "actual_duplicate_chunk_detected": False,
        "actual_duplicate_chunk_identity_or_hash_validated": False,
        "control_duplicate_write_prohibition_asserted": duplicate_boundary_preserved,
        "actual_duplicate_embedding_prevented": False,
        "actual_duplicate_index_prevented": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "actual_input_request_count": 0,
        "actual_chunk_count": 0,
        "actual_quality_degradation_record_count": 0,
        "actual_traceability_binding_count": 0,
        "source_document_remains_authoritative": True,
        "quality_degradation_control_record_can_replace_source_document": False,
        "quality_degradation_control_record_can_become_business_fact_authority": False,
        "model_direct_text_guessing_allowed": False,
        "model_decision_conclusion_authoritative": False,
        **_runtime_closed_flags(),
        "stage068_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage069_started": False,
        "stage069_entry_allowed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "github_upload_performed": False,
        "push_performed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "chinese_feedback": [
            "已完成六类固定质量降级专项控制场景；结果只说明控制处置与引用形状，不代表真实长文档、跨页表格、工程步骤、参数表、引用页码、质量或业务结论。",
            "长文档、跨页表格、施工步骤、参数表和引用页码均保留业务线白箱人工复核，系统没有读取、切分、计算、降级或写入真实来源。",
            "低质量控制标签不等于完整失败；每个控制场景均保留低可信与人工处置，不能形成自动业务决策、生产状态或模型输出。",
            "重复 chunk 场景仅确认本控制模块没有发起 embedding 或索引写入；没有检测真实重复项，也没有形成真实去重效果结论。",
        ],
    }


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage068_quality_degradation_slice.py")
    spec = importlib.util.spec_from_file_location("stage068_quality_degradation_p2", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage068 P2 control slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_executor(module: Any) -> Phase2Executor:
    executor = getattr(module, "execute_quality_degradation_control_slice", None)
    if not callable(executor):
        raise RuntimeError("Stage068 P2 executor is unavailable")
    return executor


def _phase2_control_input(module: Any) -> dict[str, object]:
    build_request = getattr(module, "build_control_request", None)
    if not callable(build_request):
        raise RuntimeError("Stage068 P2 request builder is unavailable")
    return {
        "quality_degradation_requests": [
            build_request(scenario) for scenario in PHASE2_SCENARIOS
        ]
    }


def _quality_degradation_records(
    phase2_result: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    records = phase2_result.get("quality_degradation_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _phase2_shape_preserved(
    phase2_result: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> bool:
    expected_request_refs = [
        f"quality-degradation-request:control:stage068-p2:{scenario}"
        for scenario in PHASE2_SCENARIOS
    ]
    return (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state") == PHASE2_EXECUTION_STATE
        and phase2_result.get("control_quality_degradation_request_count") == 4
        and phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("quality_degradation_record_count") == 4
        and len(records) == 4
        and all(set(record) == set(QUALITY_DEGRADATION_RECORD_FIELDS) for record in records)
        and [record.get("quality_degradation_request_ref") for record in records]
        == expected_request_refs
        and phase2_result.get("protected_semantic_asset_type_count") == 3
        and phase2_result.get("duplicate_chunk_control_record_count") == 1
        and phase2_result.get("traceability_field_count") == 6
        and phase2_result.get("control_traceability_reference_count") == 24
        and phase2_result.get("business_line_whitebox_review_record_count") == 3
        and phase2_result.get("low_confidence_evidence_review_record_count") == 1
        and phase2_result.get("low_quality_is_not_automatic_complete_failure") is True
    )


def _evaluate_scenario(
    scenario: Mapping[str, str | None],
    records: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    record = _record_for_scenario(str(scenario["record_scenario"]), records)
    protected_surface_expected = scenario["protected_semantic_surface"]
    traceability_preserved = _control_traceability_preserved(record)
    control_reference_only = _control_reference_only(record)
    duplicate_category = (
        scenario["scenario_category"] == "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL"
    )
    protected_surface_preserved = (
        record is not None
        and (
            (
                protected_surface_expected is None
                and record.get("protected_semantic_boundary_status")
                == CONTROL_REFERENCE_ONLY_STATUS
            )
            or (
                protected_surface_expected is not None
                and record.get("protected_semantic_boundary_status")
                == PROTECTED_SURFACE_STATUS
            )
        )
    )
    duplicate_boundary_preserved = (
        record is not None
        and (
            (
                duplicate_category
                and record.get("duplicate_embedding_index_status")
                == DUPLICATE_BOUNDARY_STATUS
            )
            or (
                not duplicate_category
                and record.get("duplicate_embedding_index_status")
                == CONTROL_REFERENCE_ONLY_STATUS
            )
        )
    )
    review_state_preserved = (
        record is not None
        and record.get("human_review_state") == scenario["required_review_state"]
        and record.get("low_confidence_evidence_state") == LOW_CONFIDENCE_EVIDENCE_STATE
        and record.get("quality_degradation_status") == QUALITY_DEGRADATION_STATUS
    )
    expectation_met = (
        record is not None
        and traceability_preserved
        and control_reference_only
        and protected_surface_preserved
        and duplicate_boundary_preserved
        and review_state_preserved
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "referenced_quality_degradation_record_ref": (
            record.get("quality_degradation_record_ref") if record else None
        ),
        "referenced_quality_degradation_request_ref": (
            record.get("quality_degradation_request_ref") if record else None
        ),
        "referenced_chunk_quality_regression_record_ref": (
            record.get("chunk_quality_regression_record_ref") if record else None
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
        "referenced_chunk_coverage_metrics_record_ref": (
            record.get("chunk_coverage_metrics_record_ref") if record else None
        ),
        "document_ref": record.get("document_ref") if record else None,
        "page_ref": record.get("page_ref") if record else None,
        "section_ref": record.get("section_ref") if record else None,
        "parser_output_ref": record.get("parser_output_ref") if record else None,
        "table_context_ref": record.get("table_context_ref") if record else None,
        "source_fragment_ref": record.get("source_fragment_ref") if record else None,
        "protected_semantic_surface": protected_surface_expected,
        "explicit_disposition": scenario["explicit_disposition"],
        "human_handling_required": True,
        "quality_degradation_status": record.get("quality_degradation_status") if record else None,
        "low_confidence_evidence_state": (
            record.get("low_confidence_evidence_state") if record else None
        ),
        "human_review_state": record.get("human_review_state") if record else None,
        "low_quality_is_not_automatic_complete_failure": (
            record is not None
            and record.get("quality_degradation_status") == QUALITY_DEGRADATION_STATUS
        ),
        "control_traceability_reference_count": (
            len(TRACEABILITY_FIELDS) if traceability_preserved else 0
        ),
        "control_traceability_reference_preserved": traceability_preserved,
        "control_reference_only": control_reference_only,
        "actual_long_document_quality_validated": False,
        "actual_cross_page_table_relation_validated": False,
        "actual_protected_semantic_boundary_validated": False,
        "actual_page_traceability_validated": False,
        "actual_source_traceability_binding_created": False,
        "actual_quality_degradation_validated": False,
        "actual_low_confidence_evidence_created": False,
        "actual_duplicate_chunk_detected": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "deduplication_control_prohibition_asserted": duplicate_category,
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
            if isinstance(record.get("quality_degradation_request_ref"), str)
            and record["quality_degradation_request_ref"].endswith(
                f":{record_scenario}"
            )
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
