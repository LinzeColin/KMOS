"""Stage063 P3 的章节感知切块受控专项场景。

本模块只重放 Stage063 P2 的三条固定、非业务、reference-only 控制候选。
长文档、跨页参数表、施工步骤、参数表、页码追溯和重复写入仅是控制场景
标签；不会读取或切分真实文档、检测重复 chunk，或执行 embedding、索引及
任何持久化写入。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage063.chapter_aware_chunking.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_CHAPTER_AWARE_CHUNKING_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE063-P4-GATE"

CHUNK_CANDIDATE_FIELDS = (
    "chapter_aware_chunk_ref",
    "chunking_request_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "chunk_identity_ref",
    "chunk_version_ref",
    "semantic_asset_type_ref",
    "coverage_reference_ref",
    "quality_disposition_ref",
    "human_review_state",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
SIDE_EFFECT_FIELDS = (
    "actual_chapter_boundary_detected",
    "actual_protected_surface_split_detected",
    "chunk_identity_or_version_implementation_performed",
    "chunk_hash_computation_performed",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "source_traceability_binding_performed",
    "actual_chunk_created",
    "actual_chunk_persisted",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)
REQUIRED_SCENARIO_CATEGORIES = {
    "LONG_DOCUMENT_CONTROL",
    "CROSS_PAGE_PARAMETER_TABLE_CONTROL",
    "ENGINEERING_PROCEDURE_STEP_CONTROL",
    "PARAMETER_TABLE_CONTROL",
    "PAGE_REFERENCE_TRACEABILITY_CONTROL",
    "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
}
SCENARIOS = (
    {
        "scenario_id": "long-document-chunking-control-human-review",
        "scenario_category": "LONG_DOCUMENT_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "LONG_DOCUMENT_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "cross-page-parameter-table-control-human-handling",
        "scenario_category": "CROSS_PAGE_PARAMETER_TABLE_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:parameter-table",
        "protected_semantic_asset_type": "PARAMETER_TABLE",
        "explicit_disposition": "CROSS_PAGE_PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_HANDLING",
    },
    {
        "scenario_id": "engineering-procedure-step-control-human-review",
        "scenario_category": "ENGINEERING_PROCEDURE_STEP_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "ENGINEERING_PROCEDURE_STEP_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "parameter-table-control-human-review",
        "scenario_category": "PARAMETER_TABLE_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:parameter-table",
        "protected_semantic_asset_type": "PARAMETER_TABLE",
        "explicit_disposition": "PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "page-reference-reverse-trace-control-human-confirmation",
        "scenario_category": "PAGE_REFERENCE_TRACEABILITY_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
        "explicit_disposition": "PAGE_REFERENCE_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION",
    },
    {
        "scenario_id": "duplicate-chunk-embedding-index-control-human-review",
        "scenario_category": "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
        "chunking_request_ref": "chunking-request:control:stage063-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
        "explicit_disposition": "DUPLICATE_CHUNK_REFERENCE_REQUIRES_LATER_IDENTITY_AND_HUMAN_REVIEW",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_chapter_aware_chunking_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制候选，输出不含真实文档内容的专项场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    candidates = _chunk_candidates(phase2_result)
    side_effect_free = all(phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_CHAPTER_AWARE_CHUNKING_CANDIDATE_CONTROL_SLICE"
        and phase2_result.get("control_chunking_request_count") == 3
        and phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("chapter_aware_chunk_candidate_count") == 3
        and phase2_result.get("traceability_field_count") == len(TRACEABILITY_FIELDS)
        and phase2_result.get("control_traceability_reference_count") == 18
        and phase2_result.get("control_traceability_reference_shape_preserved") is True
        and phase2_result.get("all_protected_surfaces_atomic") is True
        and phase2_result.get("all_human_review_required") is True
        and len(candidates) == 3
        and all(_candidate_has_expected_control_shape(candidate) for candidate in candidates)
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates, side_effect_free) for scenario in SCENARIOS
    ]
    categories_covered = {
        str(scenario["scenario_category"]) for scenario in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    traceability_preserved = all(
        item["control_traceability_reference_preserved"] for item in scenario_results
    )
    duplicate_boundary_preserved = all(
        item["duplicate_embedding_or_index_write_attempted"] is False
        for item in scenario_results
    ) and any(
        item["deduplication_control_prohibition_asserted"]
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
        "unique_chapter_aware_chunk_candidate_count": len(
            {
                item["referenced_chapter_aware_chunk_ref"]
                for item in scenario_results
                if isinstance(item["referenced_chapter_aware_chunk_ref"], str)
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
        "source_document_remains_authoritative": True,
        "chunk_candidate_can_replace_source_document": False,
        "chunk_candidate_can_become_business_fact_authority": False,
        "model_direct_text_guessing_allowed": False,
        "model_decision_conclusion_authoritative": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "chapter_detection_performed": False,
        "chunking_execution_performed": False,
        "chunk_hash_computation_performed": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage063_started": True,
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
            "已完成六类固定章节感知切块专项控制场景；结果只说明控制处置与引用形状，不代表真实切块质量或业务结论。",
            "长文档、跨页参数表、施工步骤、参数表和引用页码均保留业务线人工白箱复核，系统没有读取、切分或写入真实来源。",
            "重复 chunk 场景仅确认本控制模块没有发起 embedding 或索引写入；没有检测真实重复项，也没有形成真实去重效果结论。",
            "每个场景仅保留文档、页码、章节、解析输出、表格上下文和来源片段的控制引用，真实来源反查仍须人工确认。",
        ],
    }


def _load_phase2_executor() -> Phase2Executor:
    module_path = Path(__file__).with_name("stage063_chapter_aware_chunking_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage063_chapter_aware_chunking_slice", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage063 P2 chapter-aware chunking control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_chapter_aware_chunking_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实文档、章节、页面或表格内容。"""

    records: list[dict[str, object]] = []
    for suffix, protected_type in (
        ("procedure", "ENGINEERING_PROCEDURE_STEP"),
        ("acceptance", "ACCEPTANCE_CLAUSE"),
        ("parameter-table", "PARAMETER_TABLE"),
    ):
        records.append(
            {
                "chunking_request_ref": f"chunking-request:control:stage063-p2:{suffix}",
                "document_ref": f"document:control:stage063-p2:{suffix}",
                "page_ref": f"page:control:stage063-p2:{suffix}",
                "section_ref": f"section:control:stage063-p2:{suffix}",
                "parser_output_ref": f"parser-output:control:stage063-p2:{suffix}",
                "table_context_ref": f"table-context:control:stage063-p2:{suffix}",
                "engineering_semantic_asset_ref": (
                    "engineering-semantic-asset:control:stage063-p2:"
                    f"{protected_type}"
                ),
                "source_fragment_ref": f"source-fragment:control:stage063-p2:{suffix}",
            }
        )
    return {"chapter_aware_chunking_requests": records}


def _chunk_candidates(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = result.get("chapter_aware_chunk_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _candidate_has_expected_control_shape(candidate: Mapping[str, Any]) -> bool:
    return (
        set(candidate) == set(CHUNK_CANDIDATE_FIELDS)
        and candidate.get("human_review_state")
        == "REQUIRED_WHEN_TRACEABILITY_OR_BOUNDARY_UNVERIFIED"
        and _control_traceability_preserved(candidate)
        and _control_reference_only(candidate)
    )


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    candidate = _candidate_for_scenario(scenario, candidates)
    traceability_preserved = _control_traceability_preserved(candidate)
    control_reference_only = _control_reference_only(candidate)
    category = str(scenario["scenario_category"])
    expected_candidate = (
        candidate is not None
        and candidate.get("chunking_request_ref") == scenario["chunking_request_ref"]
        and candidate.get("semantic_asset_type_ref")
        == "semantic-asset-type:control:stage063-p2:"
        f"{scenario['protected_semantic_asset_type']}"
        and _candidate_has_expected_control_shape(candidate)
    )
    disposition = scenario["explicit_disposition"]
    expectation_met = (
        expected_candidate
        and traceability_preserved
        and control_reference_only
        and isinstance(disposition, str)
        and bool(disposition)
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": category,
        "referenced_chapter_aware_chunk_ref": (
            candidate.get("chapter_aware_chunk_ref") if candidate else None
        ),
        "referenced_chunking_request_ref": scenario["chunking_request_ref"],
        "document_ref": candidate.get("document_ref") if candidate else None,
        "page_ref": candidate.get("page_ref") if candidate else None,
        "section_ref": candidate.get("section_ref") if candidate else None,
        "parser_output_ref": candidate.get("parser_output_ref") if candidate else None,
        "table_context_ref": candidate.get("table_context_ref") if candidate else None,
        "source_fragment_ref": candidate.get("source_fragment_ref") if candidate else None,
        "protected_semantic_asset_type": scenario["protected_semantic_asset_type"],
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


def _candidate_for_scenario(
    scenario: Mapping[str, object], candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    return next(
        (
            candidate
            for candidate in candidates
            if candidate.get("chunking_request_ref") == scenario["chunking_request_ref"]
        ),
        None,
    )


def _control_traceability_preserved(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(candidate.get(field), str) and ":control:" in candidate[field]
        for field in TRACEABILITY_FIELDS
    )


def _control_reference_only(candidate: Mapping[str, Any] | None) -> bool:
    return candidate is not None and all(
        isinstance(value, str) and ":control:" in value
        for value in (
            candidate.get("chapter_aware_chunk_ref"),
            candidate.get("chunking_request_ref"),
            candidate.get("chunk_identity_ref"),
            candidate.get("chunk_version_ref"),
            candidate.get("semantic_asset_type_ref"),
            candidate.get("coverage_reference_ref"),
            candidate.get("quality_disposition_ref"),
            *[candidate.get(field) for field in TRACEABILITY_FIELDS],
        )
    )
