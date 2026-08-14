"""Stage064 P3 的 Chunk 身份与版本受控专项场景。

本模块只重放 Stage064 P2 的三条固定、非业务、reference-only 控制记录。
长文档、跨页参数表、施工步骤、参数表、页码反查和重复写入只属于控制场景
标签；不会读取或切分真实文档、验证真实 chunk 质量、检测重复 chunk，或执行
embedding、索引及任何持久化写入。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage064.chunk_identity_and_version.phase3.controlled_scenarios.v1"
RECORD_KIND = "CONTROLLED_CHUNK_IDENTITY_AND_VERSION_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_CHUNK_IDENTITY_AND_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_CHUNK_IDENTITY_AND_VERSION_CONTROLLED_SCENARIOS"
NEXT_GATE = "IDS-STAGE064-P4-GATE"

IDENTITY_VERSION_RECORD_FIELDS = (
    "chunk_identity_version_record_ref",
    "chapter_aware_chunk_ref",
    "chunk_id",
    "chunk_hash",
    "document_id",
    "page",
    "section",
    "version",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "engineering_semantic_asset_type_ref",
    "coverage_reference_ref",
    "human_review_state",
)
TRACEABILITY_FIELDS = (
    "document_id",
    "page",
    "section",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
SIDE_EFFECT_FIELDS = (
    "actual_chapter_boundary_detected",
    "actual_protected_surface_split_detected",
    "actual_chunk_created",
    "actual_chunk_persisted",
    "actual_chunk_id_generated",
    "actual_chunk_hash_computed",
    "actual_document_id_bound",
    "actual_chunk_version_generated",
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
REQUIRED_SCENARIO_CATEGORIES = {
    "LONG_DOCUMENT_CONTROL",
    "CROSS_PAGE_PARAMETER_TABLE_CONTROL",
    "ENGINEERING_PROCEDURE_STEP_CONTROL",
    "PARAMETER_TABLE_CONTROL",
    "PAGE_REFERENCE_TRACEABILITY_CONTROL",
    "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
}
HUMAN_REVIEW_STATE = "REQUIRED_WHEN_TRACEABILITY_OR_VERSION_BASIS_UNVERIFIED"

SCENARIOS = (
    {
        "scenario_id": "long-document-identity-version-control-human-review",
        "scenario_category": "LONG_DOCUMENT_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "LONG_DOCUMENT_REFERENCE_REQUIRES_HUMAN_BOUNDARY_AND_VERSION_REVIEW",
    },
    {
        "scenario_id": "cross-page-parameter-table-identity-version-control-human-handling",
        "scenario_category": "CROSS_PAGE_PARAMETER_TABLE_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:parameter-table",
        "protected_semantic_asset_type": "PARAMETER_TABLE",
        "explicit_disposition": "CROSS_PAGE_PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_HANDLING",
    },
    {
        "scenario_id": "engineering-procedure-step-identity-version-control-human-review",
        "scenario_category": "ENGINEERING_PROCEDURE_STEP_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
        "explicit_disposition": "ENGINEERING_PROCEDURE_STEP_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "parameter-table-identity-version-control-human-review",
        "scenario_category": "PARAMETER_TABLE_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:parameter-table",
        "protected_semantic_asset_type": "PARAMETER_TABLE",
        "explicit_disposition": "PARAMETER_TABLE_REFERENCE_REQUIRES_HUMAN_BOUNDARY_REVIEW",
    },
    {
        "scenario_id": "page-reference-reverse-trace-identity-version-control-human-confirmation",
        "scenario_category": "PAGE_REFERENCE_TRACEABILITY_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
        "explicit_disposition": "PAGE_REFERENCE_CONTROL_REQUIRES_HUMAN_SOURCE_CONFIRMATION",
    },
    {
        "scenario_id": "duplicate-chunk-embedding-index-identity-version-control-human-review",
        "scenario_category": "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
        "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
        "explicit_disposition": "DUPLICATE_CHUNK_REFERENCE_REQUIRES_LATER_IDENTITY_AND_HUMAN_REVIEW",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_chunk_identity_version_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 控制记录，输出不含真实来源内容的专项场景处置报告。"""

    executor = phase2_executor or _load_phase2_executor()
    phase2_result = executor(_phase2_control_input())
    phase2_result = phase2_result if isinstance(phase2_result, Mapping) else {}
    records = _identity_version_records(phase2_result)
    side_effect_free = all(phase2_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    phase2_shape_preserved = (
        phase2_result.get("input_accepted") is True
        and phase2_result.get("execution_state")
        == "COMPLETED_IN_MEMORY_CHUNK_IDENTITY_AND_VERSION_CONTROL_SLICE"
        and phase2_result.get("control_identity_version_request_count") == 3
        and phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("chunk_identity_version_record_count") == 3
        and phase2_result.get("traceability_field_count") == len(TRACEABILITY_FIELDS)
        and phase2_result.get("control_traceability_reference_count") == 18
        and phase2_result.get("control_traceability_reference_shape_preserved") is True
        and phase2_result.get("all_protected_surfaces_atomic") is True
        and phase2_result.get("all_human_review_required") is True
        and len(records) == 3
        and all(_record_has_expected_control_shape(record) for record in records)
    )
    scenario_results = [
        _evaluate_scenario(scenario, records, side_effect_free) for scenario in SCENARIOS
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
        item["deduplication_control_prohibition_asserted"] for item in scenario_results
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
        "unique_chunk_identity_version_record_count": len(
            {
                item["referenced_chunk_identity_version_record_ref"]
                for item in scenario_results
                if isinstance(item["referenced_chunk_identity_version_record_ref"], str)
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
        "chunk_identity_version_record_can_replace_source_document": False,
        "chunk_identity_version_record_can_become_business_fact_authority": False,
        "model_direct_text_guessing_allowed": False,
        "model_decision_conclusion_authoritative": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "chapter_detection_performed": False,
        "chunking_execution_performed": False,
        "actual_chunk_id_generation_performed": False,
        "actual_chunk_hash_computation_performed": False,
        "actual_chunk_version_generation_performed": False,
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
        "stage064_started": True,
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
            "已完成六类固定 Chunk 身份与版本专项控制场景；结果只说明控制处置与引用形状，不代表真实切块质量或业务结论。",
            "长文档、跨页参数表、施工步骤、参数表和引用页码均保留业务线人工白箱复核，系统没有读取、切分或写入真实来源。",
            "重复 chunk 场景仅确认本控制模块没有发起 embedding 或索引写入；没有检测真实重复项，也没有形成真实去重效果结论。",
            "每个场景仅保留文档、页码、章节、解析输出、表格上下文和来源片段的控制引用，真实来源反查仍须人工确认。",
        ],
    }


def _load_phase2_executor() -> Phase2Executor:
    module_path = Path(__file__).with_name("stage064_chunk_identity_version_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage064_chunk_identity_version_slice", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage064 P2 chunk identity/version control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_chunk_identity_version_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结控制引用；它们不表示真实来源、页面、章节或 chunk。"""

    records: list[dict[str, object]] = []
    for suffix in ("procedure", "acceptance", "parameter-table"):
        records.append(
            {
                "chapter_aware_chunk_ref": f"chapter-aware-chunk:control:stage064-p2:{suffix}",
                "chunking_request_ref": f"chunking-request:control:stage064-p2:{suffix}",
                "document_ref": f"document:control:stage064-p2:{suffix}",
                "page_ref": f"page:control:stage064-p2:{suffix}",
                "section_ref": f"section:control:stage064-p2:{suffix}",
                "parser_output_ref": f"parser-output:control:stage064-p2:{suffix}",
                "table_context_ref": f"table-context:control:stage064-p2:{suffix}",
                "source_fragment_ref": f"source-fragment:control:stage064-p2:{suffix}",
                "chunk_identity_ref": f"chunk-identity-ref:control:stage064-p2:{suffix}",
                "chunk_version_ref": f"chunk-version-ref:control:stage064-p2:{suffix}",
            }
        )
    return {"chunk_identity_version_requests": records}


def _identity_version_records(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = result.get("chunk_identity_version_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _record_has_expected_control_shape(record: Mapping[str, Any]) -> bool:
    return (
        set(record) == set(IDENTITY_VERSION_RECORD_FIELDS)
        and record.get("human_review_state") == HUMAN_REVIEW_STATE
        and _control_traceability_preserved(record)
        and all(
            isinstance(record.get(field), str) and ":control:" in record[field]
            for field in IDENTITY_VERSION_RECORD_FIELDS
            if field != "human_review_state"
        )
    )


def _control_traceability_preserved(record: Mapping[str, Any]) -> bool:
    return all(
        isinstance(record.get(field), str) and ":control:" in record[field]
        for field in TRACEABILITY_FIELDS
    )


def _evaluate_scenario(
    scenario: Mapping[str, object],
    records: Sequence[Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    target_ref = scenario["chapter_aware_chunk_ref"]
    record = next(
        (
            item
            for item in records
            if item.get("chapter_aware_chunk_ref") == target_ref
        ),
        None,
    )
    expected_type = str(scenario["protected_semantic_asset_type"])
    expected_type_ref = (
        "engineering-semantic-asset-type:control:stage064-p2:" f"{expected_type}"
    )
    traceability_preserved = (
        isinstance(record, Mapping) and _control_traceability_preserved(record)
    )
    protected_surface_preserved = (
        isinstance(record, Mapping)
        and record.get("engineering_semantic_asset_type_ref") == expected_type_ref
    )
    duplicate_scenario = (
        scenario["scenario_category"] == "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL"
    )
    duplicate_write_prohibition_asserted = (
        duplicate_scenario
        and side_effect_free
        and traceability_preserved
        and protected_surface_preserved
    )
    explicit_disposition = str(scenario["explicit_disposition"])
    expectation_met = (
        isinstance(record, Mapping)
        and _record_has_expected_control_shape(record)
        and traceability_preserved
        and protected_surface_preserved
        and bool(explicit_disposition)
        and side_effect_free
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "referenced_chunk_identity_version_record_ref": (
            record.get("chunk_identity_version_record_ref")
            if isinstance(record, Mapping)
            else None
        ),
        "referenced_chapter_aware_chunk_ref": target_ref,
        "protected_semantic_asset_type": expected_type,
        "control_traceability_reference_count": len(TRACEABILITY_FIELDS)
        if traceability_preserved
        else 0,
        "control_traceability_reference_preserved": traceability_preserved,
        "protected_surface_preserved": protected_surface_preserved,
        "explicit_disposition": explicit_disposition,
        "human_handling_required": True,
        "silent_drop": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "deduplication_control_prohibition_asserted": duplicate_write_prohibition_asserted,
        "expectation_met": expectation_met,
    }
