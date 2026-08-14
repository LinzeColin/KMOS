"""Stage066 P2 的 Chunk 覆盖率指标纯内存控制切片。

本模块只接受四条固定、非业务、reference-only 控制请求，并按 Stage066 P1
定义的十二字段输入与十七字段输出投影四条待人工复核控制记录。它不会读取文档、
运行 parser、切分文本、生成真实身份或版本、计算真实 hash 或覆盖率、识别真实
未覆盖页面、创建索引或写入持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage066.chunk_coverage_metrics.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_CHUNK_COVERAGE_METRICS"
CONTROL_ADAPTER_VERSION = "ids.chunk_coverage_metrics.control_adapter.v0_1.stage066.p2"
CONTROL_FIELDS = ("chunk_coverage_metric_requests",)
CHUNK_COVERAGE_INPUT_FIELDS = (
    "chunk_coverage_request_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "declared_document_page_set_ref",
    "parser_page_set_ref",
)
CHUNK_COVERAGE_METRIC_RECORD_FIELDS = (
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
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
CONTROL_SCENARIOS = (
    "procedure",
    "acceptance",
    "parameter_table",
    "unknown_denominator",
)
PROTECTED_SEMANTIC_SURFACE_BY_SCENARIO = {
    "procedure": "ENGINEERING_PROCEDURE_STEP",
    "acceptance": "ACCEPTANCE_CLAUSE",
    "parameter_table": "PARAMETER_TABLE",
    "unknown_denominator": None,
}
CONTROL_REFERENCE_PREFIXES = {
    "chunk_coverage_request_ref": "chunk-coverage-request",
    "chapter_aware_chunk_ref": "chapter-aware-chunk",
    "chunk_identity_version_record_ref": "chunk-identity-version-record",
    "engineering_semantic_asset_catalog_ref": "engineering-semantic-asset-catalog",
    "document_ref": "document",
    "page_ref": "page",
    "section_ref": "section",
    "parser_output_ref": "parser-output",
    "table_context_ref": "table-context",
    "source_fragment_ref": "source-fragment",
    "declared_document_page_set_ref": "declared-document-page-set",
    "parser_page_set_ref": "parser-page-set",
}
CONTROL_REFERENCE_ONLY_STATUS = "CONTROL_REFERENCE_ONLY_UNASSESSED_REQUIRES_HUMAN_REVIEW"
UNKNOWN_DENOMINATOR_STATUS = "CONTROL_DENOMINATOR_UNKNOWN_REQUIRES_HUMAN_REVIEW"
PROTECTED_SURFACE_STATUS = "CONTROL_PROTECTED_SEMANTIC_SURFACE_REQUIRES_HUMAN_HANDLING"
HUMAN_REVIEW_STATE = (
    "REQUIRED_WHEN_COVERAGE_DENOMINATOR_TRACEABILITY_OR_SEMANTIC_BOUNDARY_UNVERIFIED"
)


def build_control_request(scenario: str) -> dict[str, str]:
    """返回固定控制请求；该请求不包含来源内容或业务数据。"""

    if scenario not in CONTROL_SCENARIOS:
        raise ValueError("unknown chunk coverage metric control scenario")
    return {
        field: f"{CONTROL_REFERENCE_PREFIXES[field]}:control:stage066-p2:{scenario}"
        for field in CHUNK_COVERAGE_INPUT_FIELDS
    }


def execute_chunk_coverage_metrics_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制请求的覆盖率指标字段。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    projected = [_coverage_metric_record(request) for request in requests]
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
        "execution_state": "COMPLETED_IN_MEMORY_CHUNK_COVERAGE_METRICS_CONTROL_SLICE",
        "control_chunk_coverage_metric_request_count": len(requests),
        "actual_input_request_count": 0,
        "chunk_coverage_metric_records": projected,
        "chunk_coverage_metric_record_count": len(projected),
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "control_scenario_count": len(CONTROL_SCENARIOS),
        "one_control_record_per_scenario": len(projected) == len(CONTROL_SCENARIOS),
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
        "unknown_denominator_control_record_count": sum(
            record["parse_coverage_status"] == UNKNOWN_DENOMINATOR_STATUS
            for record in projected
        ),
        "low_confidence_control_marker_count": len(projected),
        "all_control_records_low_confidence_requires_human_review": all(
            record["human_review_state"] == HUMAN_REVIEW_STATE for record in projected
        ),
        "control_request_reference_validation_performed": True,
        "control_coverage_metric_record_projection_performed": True,
        "control_parse_coverage_label_projection_performed": True,
        "control_chunk_coverage_label_projection_performed": True,
        "control_uncovered_page_reference_label_projection_performed": True,
        "control_quality_degradation_marker_projection_performed": True,
        "control_metric_output_is_not_actual_coverage": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影四条固定 Chunk 覆盖率指标控制记录，未读取、打开、解析、切分、计算或创建任何真实资料、页面、chunk、hash、覆盖率、未覆盖页面或业务结论。",
            "解析覆盖率、Chunk 覆盖率和未覆盖页字段均为 :control: 标签；它们不包含实际分母、比率、页码、未覆盖页或来源验证，不能作为质量或业务事实。",
            "工程步骤、验收条款和参数表控制记录保持受保护语义面；未知分母、语义边界或来源追溯无法确认时，指标输出必须保持关闭并交由业务线白箱人工复核。",
            "全部控制记录均为低可信待人工复核；这不是实际低质量检测、质量回归、质量降级、索引写入或生产状态。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("chunk_coverage_metric_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    if len(requests) != len(CONTROL_SCENARIOS):
        return None

    accepted = [_accepted_control_request(request) for request in requests]
    if any(request is None for request in accepted):
        return None
    normalized = [request for request in accepted if request is not None]
    expected_request_refs = [
        build_control_request(scenario)["chunk_coverage_request_ref"]
        for scenario in CONTROL_SCENARIOS
    ]
    if [request["chunk_coverage_request_ref"] for request in normalized] != expected_request_refs:
        return None
    return normalized


def _accepted_control_request(request: object) -> dict[str, object] | None:
    if not isinstance(request, Mapping) or set(request) != set(CHUNK_COVERAGE_INPUT_FIELDS):
        return None
    normalized = {field: request.get(field) for field in CHUNK_COVERAGE_INPUT_FIELDS}
    request_ref = normalized["chunk_coverage_request_ref"]
    if not isinstance(request_ref, str):
        return None
    scenario = request_ref.rsplit(":", 1)[-1]
    if scenario not in CONTROL_SCENARIOS:
        return None
    if normalized != build_control_request(scenario):
        return None
    normalized["scenario"] = scenario
    normalized["protected_semantic_surface"] = PROTECTED_SEMANTIC_SURFACE_BY_SCENARIO[
        scenario
    ]
    return normalized


def _coverage_metric_record(request: Mapping[str, object]) -> dict[str, Any]:
    scenario = str(request["scenario"])
    protected_surface = request["protected_semantic_surface"]
    if scenario == "unknown_denominator":
        parse_status = UNKNOWN_DENOMINATOR_STATUS
        chunk_status = UNKNOWN_DENOMINATOR_STATUS
    elif protected_surface is not None:
        parse_status = PROTECTED_SURFACE_STATUS
        chunk_status = PROTECTED_SURFACE_STATUS
    else:
        parse_status = CONTROL_REFERENCE_ONLY_STATUS
        chunk_status = CONTROL_REFERENCE_ONLY_STATUS
    return {
        "chunk_coverage_metrics_record_ref": (
            "chunk-coverage-metrics-record:control:stage066-p2:" f"{scenario}"
        ),
        "chunk_coverage_request_ref": request["chunk_coverage_request_ref"],
        "chapter_aware_chunk_ref": request["chapter_aware_chunk_ref"],
        "chunk_identity_version_record_ref": request["chunk_identity_version_record_ref"],
        "engineering_semantic_asset_catalog_ref": request[
            "engineering_semantic_asset_catalog_ref"
        ],
        "document_ref": request["document_ref"],
        "parser_output_ref": request["parser_output_ref"],
        "parse_coverage_status": parse_status,
        "parse_coverage_ratio": (
            "parse-coverage-ratio:control:stage066-p2:" f"{scenario}"
        ),
        "chunk_coverage_status": chunk_status,
        "chunk_coverage_ratio": (
            "chunk-coverage-ratio:control:stage066-p2:" f"{scenario}"
        ),
        "uncovered_page_refs": (
            "uncovered-page-reference-set:control:stage066-p2:" f"{scenario}",
        ),
        "human_review_state": HUMAN_REVIEW_STATE,
        "page_ref": request["page_ref"],
        "section_ref": request["section_ref"],
        "table_context_ref": request["table_context_ref"],
        "source_fragment_ref": request["source_fragment_ref"],
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
        "actual_parse_coverage_calculated": False,
        "actual_chunk_coverage_calculated": False,
        "actual_uncovered_page_detected": False,
        "actual_low_quality_chunk_detected": False,
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
        "control_chunk_coverage_metric_request_count": 0,
        "actual_input_request_count": 0,
        "chunk_coverage_metric_records": [],
        "chunk_coverage_metric_record_count": 0,
        "control_scenarios_covered": [],
        "control_scenario_count": 0,
        "one_control_record_per_scenario": False,
        "protected_semantic_asset_types_covered": [],
        "protected_semantic_asset_type_count": 0,
        "one_control_record_per_protected_semantic_asset_type": False,
        "traceability_fields_covered": [],
        "traceability_field_count": 0,
        "control_traceability_reference_count": 0,
        "control_traceability_reference_shape_preserved": False,
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": False,
        "unknown_denominator_control_record_count": 0,
        "low_confidence_control_marker_count": 0,
        "all_control_records_low_confidence_requires_human_review": True,
        "control_request_reference_validation_performed": False,
        "control_coverage_metric_record_projection_performed": False,
        "control_parse_coverage_label_projection_performed": False,
        "control_chunk_coverage_label_projection_performed": False,
        "control_uncovered_page_reference_label_projection_performed": False,
        "control_quality_degradation_marker_projection_performed": False,
        "control_metric_output_is_not_actual_coverage": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "控制输入不符合固定 Chunk 覆盖率指标引用合同，已拒绝且未生成任何覆盖率、未覆盖页、追溯记录或业务内容。"
        ],
    }
