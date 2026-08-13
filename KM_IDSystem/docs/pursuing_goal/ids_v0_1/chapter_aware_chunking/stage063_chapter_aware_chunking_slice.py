"""Stage063 P2 的章节感知切块纯内存控制切片。

本模块只接受三条固定、非业务、reference-only 控制请求，并按 Stage063 P1
定义的八字段输入与十四字段输出投影三个待人工复核候选。它不会读取文档、
运行 parser、检测章节、切分文本、计算哈希或覆盖率、分类语义资产、创建索引
或写入任何持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage063.chapter_aware_chunking.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_CHAPTER_AWARE_CHUNKING"
CONTROL_ADAPTER_VERSION = "ids.chapter_aware_chunking.control_adapter.v0_1.stage063.p2"
CONTROL_FIELDS = ("chapter_aware_chunking_requests",)
CHUNKING_INPUT_FIELDS = (
    "chunking_request_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "engineering_semantic_asset_ref",
    "source_fragment_ref",
)
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
PROTECTED_SEMANTIC_ASSET_TYPES = (
    "ENGINEERING_PROCEDURE_STEP",
    "ACCEPTANCE_CLAUSE",
    "PARAMETER_TABLE",
)
HUMAN_REVIEW_STATE = "REQUIRED_WHEN_TRACEABILITY_OR_BOUNDARY_UNVERIFIED"


CONTROL_RECORD_EXPECTATIONS = {
    "chunking-request:control:stage063-p2:procedure": {
        "document_ref": "document:control:stage063-p2:procedure",
        "page_ref": "page:control:stage063-p2:procedure",
        "section_ref": "section:control:stage063-p2:procedure",
        "parser_output_ref": "parser-output:control:stage063-p2:procedure",
        "table_context_ref": "table-context:control:stage063-p2:procedure",
        "engineering_semantic_asset_ref": (
            "engineering-semantic-asset:control:stage063-p2:"
            "ENGINEERING_PROCEDURE_STEP"
        ),
        "source_fragment_ref": "source-fragment:control:stage063-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
    },
    "chunking-request:control:stage063-p2:acceptance": {
        "document_ref": "document:control:stage063-p2:acceptance",
        "page_ref": "page:control:stage063-p2:acceptance",
        "section_ref": "section:control:stage063-p2:acceptance",
        "parser_output_ref": "parser-output:control:stage063-p2:acceptance",
        "table_context_ref": "table-context:control:stage063-p2:acceptance",
        "engineering_semantic_asset_ref": (
            "engineering-semantic-asset:control:stage063-p2:ACCEPTANCE_CLAUSE"
        ),
        "source_fragment_ref": "source-fragment:control:stage063-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
    },
    "chunking-request:control:stage063-p2:parameter-table": {
        "document_ref": "document:control:stage063-p2:parameter-table",
        "page_ref": "page:control:stage063-p2:parameter-table",
        "section_ref": "section:control:stage063-p2:parameter-table",
        "parser_output_ref": "parser-output:control:stage063-p2:parameter-table",
        "table_context_ref": "table-context:control:stage063-p2:parameter-table",
        "engineering_semantic_asset_ref": (
            "engineering-semantic-asset:control:stage063-p2:PARAMETER_TABLE"
        ),
        "source_fragment_ref": (
            "source-fragment:control:stage063-p2:parameter-table"
        ),
        "protected_semantic_asset_type": "PARAMETER_TABLE",
    },
}


def execute_chapter_aware_chunking_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制请求的章节感知切块候选。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [_chapter_aware_chunk_candidate(record) for record in records]
    protected_types = [record["protected_semantic_asset_type"] for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_CHAPTER_AWARE_CHUNKING_CANDIDATE_CONTROL_SLICE",
        "control_chunking_request_count": len(records),
        "actual_input_request_count": 0,
        "chapter_aware_chunk_candidates": candidates,
        "chapter_aware_chunk_candidate_count": len(candidates),
        "protected_semantic_asset_types_covered": protected_types,
        "protected_semantic_asset_type_count": len(protected_types),
        "one_control_candidate_per_protected_semantic_asset_type": len(candidates)
        == len(protected_types),
        "traceability_fields_covered": list(TRACEABILITY_FIELDS),
        "traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_count": len(candidates) * len(TRACEABILITY_FIELDS),
        "control_traceability_reference_shape_preserved": all(
            _traceability_references_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": True,
        "all_human_review_required": all(
            candidate["human_review_state"] == HUMAN_REVIEW_STATE
            for candidate in candidates
        ),
        "control_chunking_request_reference_validation_performed": True,
        "control_chapter_aware_chunk_candidate_projection_performed": True,
        "actual_chapter_boundary_detected": False,
        "actual_protected_surface_split_detected": False,
        "chunk_identity_or_version_implementation_performed": False,
        "chunk_hash_computation_performed": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "actual_chunk_created": False,
        "actual_chunk_persisted": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "model_direct_text_guessing_allowed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "当前只在内存中投影固定章节感知切块控制候选，未读取、打开、解析、检测或切分任何真实文档、页面、章节、表格、来源片段或 parser 输出。",
            "候选只保留文档、页面、章节、解析输出、表格上下文和来源片段的控制引用，未创建真实 chunk、追溯绑定、索引或业务事实。",
            "工程步骤、验收条款和参数表控制候选均保持原子且待人工复核；控制标签不构成真实章节检测或语义分类。",
            "chunk 身份、版本、哈希、真实语义分类、覆盖率、质量回归和质量降级仍由后续阶段负责；无法确认边界或追溯时必须交由人工处理。",
        ],
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("chapter_aware_chunking_requests")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != len(CONTROL_RECORD_EXPECTATIONS):
        return None

    accepted = [_accepted_control_record(record) for record in records]
    if any(record is None for record in accepted):
        return None
    normalized = [record for record in accepted if record is not None]
    if [record["chunking_request_ref"] for record in normalized] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return normalized


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(CHUNKING_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in CHUNKING_INPUT_FIELDS}
    chunking_request_ref = normalized["chunking_request_ref"]
    if not isinstance(chunking_request_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(chunking_request_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items() if field in normalized):
        return None
    normalized["protected_semantic_asset_type"] = expectation[
        "protected_semantic_asset_type"
    ]
    return normalized


def _chapter_aware_chunk_candidate(record: Mapping[str, object]) -> dict[str, Any]:
    suffix = str(record["chunking_request_ref"]).rsplit(":", 1)[1]
    protected_type = str(record["protected_semantic_asset_type"])
    return {
        "chapter_aware_chunk_ref": (
            "chapter-aware-chunk-candidate:control:stage063-p2:" f"{suffix}"
        ),
        "chunking_request_ref": record["chunking_request_ref"],
        "document_ref": record["document_ref"],
        "page_ref": record["page_ref"],
        "section_ref": record["section_ref"],
        "parser_output_ref": record["parser_output_ref"],
        "table_context_ref": record["table_context_ref"],
        "source_fragment_ref": record["source_fragment_ref"],
        "chunk_identity_ref": "chunk-identity:control:stage063-p2:" f"{suffix}",
        "chunk_version_ref": "chunk-version:control:stage063-p2:" f"{suffix}",
        "semantic_asset_type_ref": (
            "semantic-asset-type:control:stage063-p2:" f"{protected_type}"
        ),
        "coverage_reference_ref": "coverage-reference:control:stage063-p2:" f"{suffix}",
        "quality_disposition_ref": (
            "quality-disposition:control:stage063-p2:" f"{suffix}"
        ),
        "human_review_state": HUMAN_REVIEW_STATE,
    }


def _traceability_references_preserved(candidate: Mapping[str, object]) -> bool:
    return all(
        isinstance(candidate[field], str) and ":control:" in candidate[field]
        for field in TRACEABILITY_FIELDS
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "control_chunking_request_count": 0,
        "actual_input_request_count": 0,
        "chapter_aware_chunk_candidates": [],
        "chapter_aware_chunk_candidate_count": 0,
        "protected_semantic_asset_types_covered": [],
        "protected_semantic_asset_type_count": 0,
        "one_control_candidate_per_protected_semantic_asset_type": False,
        "traceability_fields_covered": [],
        "traceability_field_count": 0,
        "control_traceability_reference_count": 0,
        "control_traceability_reference_shape_preserved": False,
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": False,
        "all_human_review_required": True,
        "control_chunking_request_reference_validation_performed": False,
        "control_chapter_aware_chunk_candidate_projection_performed": False,
        "actual_chapter_boundary_detected": False,
        "actual_protected_surface_split_detected": False,
        "chunk_identity_or_version_implementation_performed": False,
        "chunk_hash_computation_performed": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "actual_chunk_created": False,
        "actual_chunk_persisted": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "model_direct_text_guessing_allowed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "控制输入不符合固定引用合同，已拒绝且未生成任何章节感知切块候选、追溯引用或业务内容。"
        ],
    }
