"""Stage064 P2 的 Chunk 身份与版本纯内存控制切片。

本模块只接受三条固定、非业务、reference-only 控制请求，并按 Stage064 P1
定义的十字段输入与十四字段输出投影三个待人工复核控制记录。它不会读取文档、
运行 parser、切分文本、生成真实身份或版本、计算真实 hash、创建索引或写入持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage064.chunk_identity_and_version.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_CHUNK_IDENTITY_AND_VERSION"
CONTROL_ADAPTER_VERSION = "ids.chunk_identity_and_version.control_adapter.v0_1.stage064.p2"
CONTROL_FIELDS = ("chunk_identity_version_requests",)
IDENTITY_VERSION_INPUT_FIELDS = (
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
)
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
HUMAN_REVIEW_STATE = "REQUIRED_WHEN_TRACEABILITY_OR_VERSION_BASIS_UNVERIFIED"


CONTROL_RECORD_EXPECTATIONS = {
    "chapter-aware-chunk:control:stage064-p2:procedure": {
        "chunking_request_ref": "chunking-request:control:stage064-p2:procedure",
        "document_ref": "document:control:stage064-p2:procedure",
        "page_ref": "page:control:stage064-p2:procedure",
        "section_ref": "section:control:stage064-p2:procedure",
        "parser_output_ref": "parser-output:control:stage064-p2:procedure",
        "table_context_ref": "table-context:control:stage064-p2:procedure",
        "source_fragment_ref": "source-fragment:control:stage064-p2:procedure",
        "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:procedure",
        "chunk_version_ref": "chunk-version-ref:control:stage064-p2:procedure",
        "protected_semantic_asset_type": "ENGINEERING_PROCEDURE_STEP",
    },
    "chapter-aware-chunk:control:stage064-p2:acceptance": {
        "chunking_request_ref": "chunking-request:control:stage064-p2:acceptance",
        "document_ref": "document:control:stage064-p2:acceptance",
        "page_ref": "page:control:stage064-p2:acceptance",
        "section_ref": "section:control:stage064-p2:acceptance",
        "parser_output_ref": "parser-output:control:stage064-p2:acceptance",
        "table_context_ref": "table-context:control:stage064-p2:acceptance",
        "source_fragment_ref": "source-fragment:control:stage064-p2:acceptance",
        "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:acceptance",
        "chunk_version_ref": "chunk-version-ref:control:stage064-p2:acceptance",
        "protected_semantic_asset_type": "ACCEPTANCE_CLAUSE",
    },
    "chapter-aware-chunk:control:stage064-p2:parameter-table": {
        "chunking_request_ref": "chunking-request:control:stage064-p2:parameter-table",
        "document_ref": "document:control:stage064-p2:parameter-table",
        "page_ref": "page:control:stage064-p2:parameter-table",
        "section_ref": "section:control:stage064-p2:parameter-table",
        "parser_output_ref": "parser-output:control:stage064-p2:parameter-table",
        "table_context_ref": "table-context:control:stage064-p2:parameter-table",
        "source_fragment_ref": "source-fragment:control:stage064-p2:parameter-table",
        "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:parameter-table",
        "chunk_version_ref": "chunk-version-ref:control:stage064-p2:parameter-table",
        "protected_semantic_asset_type": "PARAMETER_TABLE",
    },
}


def execute_chunk_identity_version_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制请求的身份与版本记录。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    projected = [_identity_version_record(record) for record in records]
    protected_types = [record["protected_semantic_asset_type"] for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_CHUNK_IDENTITY_AND_VERSION_CONTROL_SLICE",
        "control_identity_version_request_count": len(records),
        "actual_input_request_count": 0,
        "chunk_identity_version_records": projected,
        "chunk_identity_version_record_count": len(projected),
        "protected_semantic_asset_types_covered": protected_types,
        "protected_semantic_asset_type_count": len(protected_types),
        "one_control_record_per_protected_semantic_asset_type": len(projected)
        == len(protected_types),
        "traceability_fields_covered": list(TRACEABILITY_FIELDS),
        "traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_count": len(projected) * len(TRACEABILITY_FIELDS),
        "control_traceability_reference_shape_preserved": all(
            _traceability_references_preserved(record) for record in projected
        ),
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": True,
        "all_human_review_required": all(
            record["human_review_state"] == HUMAN_REVIEW_STATE for record in projected
        ),
        "control_identity_version_request_reference_validation_performed": True,
        "control_identity_version_record_projection_performed": True,
        "control_chunk_id_label_projection_performed": True,
        "control_chunk_hash_label_projection_performed": True,
        "control_version_label_projection_performed": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影固定 chunk 身份与版本控制记录，未读取、打开、解析、切分、计算或创建任何真实 chunk、chunk_id、chunk_hash、document_id、页码、章节或版本。",
            "记录只保留文档、页面、章节、解析输出、表格上下文和来源片段的控制引用；十四字段中的身份、哈希和版本均为控制标签，未绑定真实来源或业务事实。",
            "工程步骤、验收条款和参数表控制记录均保持原子且待人工复核；固定映射不构成真实语义分类、覆盖率计算、质量结论或来源追溯绑定。",
            "无法确认章节边界、来源追溯或版本依据时，不能自动写入索引、数据库、业务结论或生产状态，必须交由业务线白箱人工复核。",
        ],
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("chunk_identity_version_requests")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != len(CONTROL_RECORD_EXPECTATIONS):
        return None

    accepted = [_accepted_control_record(record) for record in records]
    if any(record is None for record in accepted):
        return None
    normalized = [record for record in accepted if record is not None]
    if [record["chapter_aware_chunk_ref"] for record in normalized] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return normalized


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(IDENTITY_VERSION_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in IDENTITY_VERSION_INPUT_FIELDS}
    chapter_aware_chunk_ref = normalized["chapter_aware_chunk_ref"]
    if not isinstance(chapter_aware_chunk_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(chapter_aware_chunk_ref)
    if expectation is None:
        return None
    if any(
        normalized[field] != value
        for field, value in expectation.items()
        if field in normalized
    ):
        return None
    normalized["protected_semantic_asset_type"] = expectation[
        "protected_semantic_asset_type"
    ]
    return normalized


def _identity_version_record(record: Mapping[str, object]) -> dict[str, Any]:
    suffix = str(record["chapter_aware_chunk_ref"]).rsplit(":", 1)[1]
    protected_type = str(record["protected_semantic_asset_type"])
    return {
        "chunk_identity_version_record_ref": (
            "chunk-identity-version-record:control:stage064-p2:" f"{suffix}"
        ),
        "chapter_aware_chunk_ref": record["chapter_aware_chunk_ref"],
        "chunk_id": "chunk-id:control:stage064-p2:" f"{suffix}",
        "chunk_hash": "chunk-hash:control:stage064-p2:" f"{suffix}",
        "document_id": "document-id:control:stage064-p2:" f"{suffix}",
        "page": record["page_ref"],
        "section": record["section_ref"],
        "version": "chunk-version:control:stage064-p2:" f"{suffix}",
        "parser_output_ref": record["parser_output_ref"],
        "table_context_ref": record["table_context_ref"],
        "source_fragment_ref": record["source_fragment_ref"],
        "engineering_semantic_asset_type_ref": (
            "engineering-semantic-asset-type:control:stage064-p2:" f"{protected_type}"
        ),
        "coverage_reference_ref": "coverage-reference:control:stage064-p2:" f"{suffix}",
        "human_review_state": HUMAN_REVIEW_STATE,
    }


def _traceability_references_preserved(record: Mapping[str, object]) -> bool:
    return all(
        isinstance(record[field], str) and ":control:" in record[field]
        for field in (
            "document_id",
            "page",
            "section",
            "parser_output_ref",
            "table_context_ref",
            "source_fragment_ref",
        )
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {
        "actual_chapter_boundary_detected": False,
        "actual_protected_surface_split_detected": False,
        "actual_chunk_created": False,
        "actual_chunk_persisted": False,
        "actual_chunk_id_generated": False,
        "actual_chunk_hash_computed": False,
        "actual_document_id_bound": False,
        "actual_chunk_version_generated": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "model_direct_text_guessing_allowed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "chapter_detection_performed": False,
        "chunking_execution_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "control_identity_version_request_count": 0,
        "actual_input_request_count": 0,
        "chunk_identity_version_records": [],
        "chunk_identity_version_record_count": 0,
        "protected_semantic_asset_types_covered": [],
        "protected_semantic_asset_type_count": 0,
        "one_control_record_per_protected_semantic_asset_type": False,
        "traceability_fields_covered": [],
        "traceability_field_count": 0,
        "control_traceability_reference_count": 0,
        "control_traceability_reference_shape_preserved": False,
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": False,
        "all_human_review_required": True,
        "control_identity_version_request_reference_validation_performed": False,
        "control_identity_version_record_projection_performed": False,
        "control_chunk_id_label_projection_performed": False,
        "control_chunk_hash_label_projection_performed": False,
        "control_version_label_projection_performed": False,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "控制输入不符合固定身份与版本引用合同，已拒绝且未生成任何 chunk 身份、哈希、版本、追溯记录或业务内容。"
        ],
    }
