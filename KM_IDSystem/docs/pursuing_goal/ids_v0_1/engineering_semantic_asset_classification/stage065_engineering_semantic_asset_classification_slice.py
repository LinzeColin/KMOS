"""Stage065 P2 的工程语义资产分类纯内存控制切片。

本模块只接受七条固定、非业务、reference-only 控制请求，并按 Stage065 P1
定义的十二字段输入与十六字段输出投影七条待人工复核的控制记录。资产类型标签
只来自固定控制请求标识，不读取文档、切块或内容，不计算真实 hash，不形成真实
分类、低质量结论、覆盖率、索引或持久化状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage065.engineering_semantic_asset_classification.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION"
CONTROL_ADAPTER_VERSION = (
    "ids.engineering_semantic_asset_classification.control_adapter.v0_1.stage065.p2"
)
CONTROL_FIELDS = ("semantic_asset_classification_requests",)
SEMANTIC_ASSET_INPUT_FIELDS = (
    "semantic_asset_classification_request_ref",
    "chunk_identity_version_record_ref",
    "chapter_aware_chunk_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "engineering_procedure_ref",
    "acceptance_clause_ref",
    "parameter_table_ref",
)
SEMANTIC_ASSET_RECORD_FIELDS = (
    "semantic_asset_classification_record_ref",
    "chunk_identity_version_record_ref",
    "chapter_aware_chunk_ref",
    "semantic_asset_type",
    "semantic_asset_subtype",
    "classification_status",
    "human_review_state",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "chunk_id",
    "chunk_hash",
    "version",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
ENGINEERING_SEMANTIC_ASSET_TYPES = (
    "procedure",
    "risk",
    "acceptance",
    "material",
    "equipment",
    "case",
    "bid_response",
)
PROTECTED_SEMANTIC_SURFACE_BY_ASSET_TYPE = {
    "procedure": "ENGINEERING_PROCEDURE_STEP",
    "risk": None,
    "acceptance": "ACCEPTANCE_CLAUSE",
    "material": None,
    "equipment": "PARAMETER_TABLE",
    "case": None,
    "bid_response": None,
}
CONTROL_REFERENCE_PREFIXES = {
    "semantic_asset_classification_request_ref": "semantic-asset-classification-request",
    "chunk_identity_version_record_ref": "chunk-identity-version-record",
    "chapter_aware_chunk_ref": "chapter-aware-chunk",
    "document_ref": "document",
    "page_ref": "page",
    "section_ref": "section",
    "parser_output_ref": "parser-output",
    "table_context_ref": "table-context",
    "source_fragment_ref": "source-fragment",
    "engineering_procedure_ref": "engineering-procedure",
    "acceptance_clause_ref": "acceptance-clause",
    "parameter_table_ref": "parameter-table",
}
CLASSIFICATION_STATUS = "CONTROL_LABEL_PROJECTED_LOW_CONFIDENCE_REQUIRES_HUMAN_REVIEW"
HUMAN_REVIEW_STATE = (
    "REQUIRED_WHEN_SEMANTIC_BOUNDARY_TRACEABILITY_OR_CONTROL_QUALITY_UNVERIFIED"
)


def build_control_request(asset_type: str) -> dict[str, str]:
    """返回固定控制请求；该请求不包含来源内容或业务数据。"""

    if asset_type not in ENGINEERING_SEMANTIC_ASSET_TYPES:
        raise ValueError("unknown control semantic asset type")
    return {
        field: f"{CONTROL_REFERENCE_PREFIXES[field]}:control:stage065-p2:{asset_type}"
        for field in SEMANTIC_ASSET_INPUT_FIELDS
    }


def execute_engineering_semantic_asset_classification_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制请求的工程语义资产分类记录。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    projected = [_classification_record(request) for request in requests]
    protected_types = [
        request["protected_semantic_surface"]
        for request in requests
        if request["protected_semantic_surface"] is not None
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": (
            "COMPLETED_IN_MEMORY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROL_SLICE"
        ),
        "control_semantic_asset_classification_request_count": len(requests),
        "actual_input_request_count": 0,
        "semantic_asset_classification_records": projected,
        "semantic_asset_classification_record_count": len(projected),
        "engineering_semantic_asset_types_covered": list(
            ENGINEERING_SEMANTIC_ASSET_TYPES
        ),
        "engineering_semantic_asset_type_count": len(
            ENGINEERING_SEMANTIC_ASSET_TYPES
        ),
        "one_control_record_per_engineering_semantic_asset_type": len(projected)
        == len(ENGINEERING_SEMANTIC_ASSET_TYPES),
        "protected_semantic_asset_types_covered": protected_types,
        "protected_semantic_asset_type_count": len(protected_types),
        "one_control_record_per_protected_semantic_asset_type": len(protected_types)
        == 3,
        "traceability_fields_covered": list(TRACEABILITY_FIELDS),
        "traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_count": len(projected) * len(TRACEABILITY_FIELDS),
        "control_traceability_reference_shape_preserved": all(
            _traceability_references_preserved(record) for record in projected
        ),
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": True,
        "low_confidence_control_marker_count": len(projected),
        "all_control_records_low_confidence_requires_human_review": all(
            record["classification_status"] == CLASSIFICATION_STATUS
            and record["human_review_state"] == HUMAN_REVIEW_STATE
            for record in projected
        ),
        "control_request_reference_validation_performed": True,
        "control_semantic_asset_label_projection_performed": True,
        "control_chunk_identity_version_reference_projection_performed": True,
        "control_chunk_hash_label_projection_performed": True,
        "control_low_confidence_marker_projection_performed": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影七条固定工程语义资产分类控制记录，未读取、打开、解析、切分、计算或创建任何真实资料、chunk、分类记录或业务结论。",
            "procedure、risk、acceptance、material、equipment、case 和 bid_response 标签只来自固定控制请求标识；它们不是对真实文档、内容或业务事实的自动分类。",
            "控制记录保留页面、章节、表格上下文和来源片段的引用形状；chunk_id、chunk_hash 和 version 均为控制标签，未绑定真实来源，也未计算真实 hash。",
            "全部控制记录均标为低可信并要求业务线白箱人工复核；这不是低质量检测、覆盖率计算、质量降级、索引写入或生产状态。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("semantic_asset_classification_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    if len(requests) != len(ENGINEERING_SEMANTIC_ASSET_TYPES):
        return None

    accepted = [_accepted_control_request(request) for request in requests]
    if any(request is None for request in accepted):
        return None
    normalized = [request for request in accepted if request is not None]
    if [request["semantic_asset_type"] for request in normalized] != list(
        ENGINEERING_SEMANTIC_ASSET_TYPES
    ):
        return None
    return normalized


def _accepted_control_request(request: object) -> dict[str, object] | None:
    if not isinstance(request, Mapping) or set(request) != set(SEMANTIC_ASSET_INPUT_FIELDS):
        return None
    normalized = {field: request.get(field) for field in SEMANTIC_ASSET_INPUT_FIELDS}
    for asset_type in ENGINEERING_SEMANTIC_ASSET_TYPES:
        if normalized == build_control_request(asset_type):
            return {
                **normalized,
                "semantic_asset_type": asset_type,
                "protected_semantic_surface": (
                    PROTECTED_SEMANTIC_SURFACE_BY_ASSET_TYPE[asset_type]
                ),
            }
    return None


def _classification_record(request: Mapping[str, object]) -> dict[str, Any]:
    asset_type = str(request["semantic_asset_type"])
    return {
        "semantic_asset_classification_record_ref": (
            "semantic-asset-classification-record:control:stage065-p2:" f"{asset_type}"
        ),
        "chunk_identity_version_record_ref": request[
            "chunk_identity_version_record_ref"
        ],
        "chapter_aware_chunk_ref": request["chapter_aware_chunk_ref"],
        "semantic_asset_type": asset_type,
        "semantic_asset_subtype": "CONTROL_LABEL_ONLY_NOT_A_BUSINESS_SUBTYPE",
        "classification_status": CLASSIFICATION_STATUS,
        "human_review_state": HUMAN_REVIEW_STATE,
        "document_ref": request["document_ref"],
        "page_ref": request["page_ref"],
        "section_ref": request["section_ref"],
        "parser_output_ref": request["parser_output_ref"],
        "table_context_ref": request["table_context_ref"],
        "source_fragment_ref": request["source_fragment_ref"],
        "chunk_id": f"chunk-id:control:stage065-p2:{asset_type}",
        "chunk_hash": f"chunk-hash:control:stage065-p2:{asset_type}",
        "version": f"chunk-version:control:stage065-p2:{asset_type}",
    }


def _traceability_references_preserved(record: Mapping[str, object]) -> bool:
    return all(
        isinstance(record[field], str) and ":control:" in record[field]
        for field in TRACEABILITY_FIELDS
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {
        "actual_chapter_boundary_detected": False,
        "actual_protected_surface_split_detected": False,
        "actual_chunk_created": False,
        "actual_chunk_persisted": False,
        "actual_chunk_id_generated": False,
        "actual_chunk_hash_computed": False,
        "actual_chunk_version_generated": False,
        "actual_semantic_asset_classification_created": False,
        "semantic_asset_classification_performed": False,
        "actual_low_quality_chunk_detected": False,
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
        "control_semantic_asset_classification_request_count": 0,
        "actual_input_request_count": 0,
        "semantic_asset_classification_records": [],
        "semantic_asset_classification_record_count": 0,
        "engineering_semantic_asset_types_covered": [],
        "engineering_semantic_asset_type_count": 0,
        "one_control_record_per_engineering_semantic_asset_type": False,
        "protected_semantic_asset_types_covered": [],
        "protected_semantic_asset_type_count": 0,
        "one_control_record_per_protected_semantic_asset_type": False,
        "traceability_fields_covered": [],
        "traceability_field_count": 0,
        "control_traceability_reference_count": 0,
        "control_traceability_reference_shape_preserved": False,
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": False,
        "low_confidence_control_marker_count": 0,
        "all_control_records_low_confidence_requires_human_review": False,
        "control_request_reference_validation_performed": False,
        "control_semantic_asset_label_projection_performed": False,
        "control_chunk_identity_version_reference_projection_performed": False,
        "control_chunk_hash_label_projection_performed": False,
        "control_low_confidence_marker_projection_performed": False,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "控制输入不符合固定工程语义资产分类引用合同，已拒绝且未生成任何分类、chunk、追溯记录、低可信结论或业务内容。"
        ],
    }
