"""Stage068 P2 的质量降级纯内存控制切片。

只接受四条固定、非业务、reference-only 控制请求，并投影四条低可信、待
业务线白箱人工复核的质量降级控制记录。本模块不会读取来源、解析或切分文本、
生成 chunk/hash/version、执行语义分类或覆盖率计算、计算真实质量或降级、
检测真实重复项、写入 embedding/index 或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage068.quality_degradation.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_QUALITY_DEGRADATION"
CONTROL_ADAPTER_VERSION = "ids.quality_degradation.control_adapter.v0_1.stage068.p2"
CONTROL_FIELDS = ("quality_degradation_requests",)
QUALITY_DEGRADATION_INPUT_FIELDS = (
    "quality_degradation_request_ref",
    "chapter_aware_chunk_ref",
    "chunk_identity_version_record_ref",
    "engineering_semantic_asset_catalog_ref",
    "chunk_coverage_metrics_record_ref",
    "chunk_quality_regression_record_ref",
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
    "duplicate_chunk_control_ref",
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
    "duplicate_chunk",
)
PROTECTED_SEMANTIC_SURFACE_BY_SCENARIO = {
    "procedure": "ENGINEERING_PROCEDURE_STEP",
    "acceptance": "ACCEPTANCE_CLAUSE",
    "parameter_table": "PARAMETER_TABLE",
    "duplicate_chunk": None,
}
CONTROL_REFERENCE_PREFIXES = {
    "quality_degradation_request_ref": "quality-degradation-request",
    "chapter_aware_chunk_ref": "chapter-aware-chunk",
    "chunk_identity_version_record_ref": "chunk-identity-version-record",
    "engineering_semantic_asset_catalog_ref": "engineering-semantic-asset-catalog",
    "chunk_coverage_metrics_record_ref": "chunk-coverage-metrics-record",
    "chunk_quality_regression_record_ref": "chunk-quality-regression-record",
    "document_ref": "document",
    "page_ref": "page",
    "section_ref": "section",
    "parser_output_ref": "parser-output",
    "table_context_ref": "table-context",
    "source_fragment_ref": "source-fragment",
    "duplicate_chunk_control_ref": "duplicate-chunk-control",
}
CONTROL_REFERENCE_ONLY_STATUS = "CONTROL_REFERENCE_ONLY_UNASSESSED_REQUIRES_HUMAN_REVIEW"
PROTECTED_SURFACE_STATUS = "CONTROL_PROTECTED_SEMANTIC_SURFACE_REQUIRES_HUMAN_HANDLING"
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
QUALITY_DEGRADATION_REASON_BY_SCENARIO = {
    "procedure": "CONTROL_PROTECTED_ENGINEERING_PROCEDURE_REQUIRES_HUMAN_REVIEW",
    "acceptance": "CONTROL_PROTECTED_ACCEPTANCE_CLAUSE_REQUIRES_HUMAN_REVIEW",
    "parameter_table": "CONTROL_PROTECTED_PARAMETER_TABLE_REQUIRES_HUMAN_REVIEW",
    "duplicate_chunk": "CONTROL_DUPLICATE_CHUNK_REQUIRES_LOW_CONFIDENCE_EVIDENCE_HUMAN_REVIEW",
}


def build_control_request(scenario: str) -> dict[str, str]:
    """返回固定控制请求；请求不包含来源内容或业务数据。"""

    if scenario not in CONTROL_SCENARIOS:
        raise ValueError("unknown quality degradation control scenario")
    return {
        field: f"{CONTROL_REFERENCE_PREFIXES[field]}:control:stage068-p2:{scenario}"
        for field in QUALITY_DEGRADATION_INPUT_FIELDS
    }


def execute_quality_degradation_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定质量降级控制请求的人工复核字段。"""

    requests = _accepted_control_requests(control_input)
    if requests is None:
        return _rejected_result()

    projected = [_quality_degradation_record(request) for request in requests]
    protected_types = [
        request["protected_semantic_surface"]
        for request in requests
        if request["protected_semantic_surface"] is not None
    ]
    duplicate_records = [
        record
        for record in projected
        if record["duplicate_embedding_index_status"] == DUPLICATE_BOUNDARY_STATUS
    ]
    whitebox_records = [
        record
        for record in projected
        if record["human_review_state"] == BUSINESS_LINE_WHITEBOX_REVIEW_STATE
    ]
    low_confidence_evidence_records = [
        record
        for record in projected
        if record["human_review_state"] == LOW_CONFIDENCE_EVIDENCE_REVIEW_STATE
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_QUALITY_DEGRADATION_CONTROL_SLICE",
        "control_quality_degradation_request_count": len(requests),
        "actual_input_request_count": 0,
        "quality_degradation_records": projected,
        "quality_degradation_record_count": len(projected),
        "control_scenarios_covered": list(CONTROL_SCENARIOS),
        "control_scenario_count": len(CONTROL_SCENARIOS),
        "one_control_record_per_scenario": len(projected) == len(CONTROL_SCENARIOS),
        "protected_semantic_asset_types_covered": protected_types,
        "protected_semantic_asset_type_count": len(protected_types),
        "one_control_record_per_protected_semantic_asset_type": len(protected_types)
        == 3,
        "duplicate_chunk_control_record_count": len(duplicate_records),
        "duplicate_control_never_requests_embedding_or_index_write": len(
            duplicate_records
        )
        == 1,
        "traceability_fields_covered": list(TRACEABILITY_FIELDS),
        "traceability_field_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_count": len(projected)
        * len(TRACEABILITY_FIELDS),
        "control_traceability_reference_shape_preserved": all(
            _traceability_references_preserved(record) for record in projected
        ),
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": True,
        "low_confidence_control_marker_count": len(projected),
        "all_control_records_low_confidence_requires_human_review": all(
            record["quality_degradation_status"] == QUALITY_DEGRADATION_STATUS
            and record["low_confidence_evidence_state"]
            == LOW_CONFIDENCE_EVIDENCE_STATE
            and record["human_review_state"]
            in {
                BUSINESS_LINE_WHITEBOX_REVIEW_STATE,
                LOW_CONFIDENCE_EVIDENCE_REVIEW_STATE,
            }
            for record in projected
        ),
        "business_line_whitebox_review_record_count": len(whitebox_records),
        "low_confidence_evidence_review_record_count": len(
            low_confidence_evidence_records
        ),
        "low_quality_is_not_automatic_complete_failure": True,
        "control_request_reference_validation_performed": True,
        "control_quality_degradation_record_projection_performed": True,
        "control_protected_semantic_boundary_label_projection_performed": True,
        "control_duplicate_embedding_index_boundary_label_projection_performed": True,
        "control_low_confidence_evidence_label_projection_performed": True,
        "control_business_line_whitebox_review_label_projection_performed": True,
        "control_output_is_not_actual_quality_degradation": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "当前只在内存中投影四条固定质量降级控制记录，未读取、打开、解析、切分、分类、计算、检测或创建任何真实资料、页面、chunk、质量、降级、低可信证据、重复项、来源内容或业务结论。",
            "工程步骤、验收条款和参数表控制记录保持受保护语义面；无法确认真实边界、质量或来源追溯时必须转业务线白箱人工复核。",
            "重复 chunk 控制记录只标记不得重复 embedding 或索引写入；它不是实际重复检测、去重、写入抑制或质量降级结论。",
            "低质量控制标签不等于完整失败：全部记录均为低可信待人工复核，不能形成生产状态、自动业务决策或模型输出。",
        ],
    }


def _accepted_control_requests(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    requests = control_input.get("quality_degradation_requests")
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)):
        return None
    if len(requests) != len(CONTROL_SCENARIOS):
        return None

    accepted = [_accepted_control_request(request) for request in requests]
    if any(request is None for request in accepted):
        return None
    normalized = [request for request in accepted if request is not None]
    expected_request_refs = [
        build_control_request(scenario)["quality_degradation_request_ref"]
        for scenario in CONTROL_SCENARIOS
    ]
    if [request["quality_degradation_request_ref"] for request in normalized] != (
        expected_request_refs
    ):
        return None
    return normalized


def _accepted_control_request(request: object) -> dict[str, object] | None:
    if not isinstance(request, Mapping) or set(request) != set(
        QUALITY_DEGRADATION_INPUT_FIELDS
    ):
        return None
    normalized = {
        field: request.get(field) for field in QUALITY_DEGRADATION_INPUT_FIELDS
    }
    request_ref = normalized["quality_degradation_request_ref"]
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


def _quality_degradation_record(request: Mapping[str, object]) -> dict[str, Any]:
    scenario = str(request["scenario"])
    protected_surface = request["protected_semantic_surface"]
    protected_status = (
        PROTECTED_SURFACE_STATUS
        if protected_surface is not None
        else CONTROL_REFERENCE_ONLY_STATUS
    )
    duplicate_status = (
        DUPLICATE_BOUNDARY_STATUS
        if scenario == "duplicate_chunk"
        else CONTROL_REFERENCE_ONLY_STATUS
    )
    human_review_state = (
        LOW_CONFIDENCE_EVIDENCE_REVIEW_STATE
        if scenario == "duplicate_chunk"
        else BUSINESS_LINE_WHITEBOX_REVIEW_STATE
    )
    return {
        "quality_degradation_record_ref": (
            "quality-degradation-record:control:stage068-p2:" f"{scenario}"
        ),
        "quality_degradation_request_ref": request["quality_degradation_request_ref"],
        "chunk_quality_regression_record_ref": request[
            "chunk_quality_regression_record_ref"
        ],
        "chapter_aware_chunk_ref": request["chapter_aware_chunk_ref"],
        "chunk_identity_version_record_ref": request["chunk_identity_version_record_ref"],
        "engineering_semantic_asset_catalog_ref": request[
            "engineering_semantic_asset_catalog_ref"
        ],
        "chunk_coverage_metrics_record_ref": request[
            "chunk_coverage_metrics_record_ref"
        ],
        "document_ref": request["document_ref"],
        "page_ref": request["page_ref"],
        "section_ref": request["section_ref"],
        "parser_output_ref": request["parser_output_ref"],
        "table_context_ref": request["table_context_ref"],
        "source_fragment_ref": request["source_fragment_ref"],
        "protected_semantic_boundary_status": protected_status,
        "duplicate_embedding_index_status": duplicate_status,
        "quality_degradation_status": QUALITY_DEGRADATION_STATUS,
        "low_confidence_evidence_state": LOW_CONFIDENCE_EVIDENCE_STATE,
        "human_review_state": human_review_state,
        "quality_degradation_reason_code": QUALITY_DEGRADATION_REASON_BY_SCENARIO[
            scenario
        ],
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
        "actual_engineering_semantic_asset_classified": False,
        "actual_coverage_metric_calculated": False,
        "actual_quality_regression_record_created": False,
        "actual_quality_measurement_performed": False,
        "actual_quality_regression_performed": False,
        "actual_quality_degradation_record_created": False,
        "actual_quality_degradation_performed": False,
        "actual_low_confidence_evidence_created": False,
        "actual_low_quality_chunk_detected": False,
        "actual_duplicate_chunk_detected": False,
        "actual_duplicate_chunk_identity_or_hash_validated": False,
        "actual_duplicate_embedding_prevented": False,
        "actual_duplicate_index_prevented": False,
        "duplicate_embedding_or_index_write_attempted": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "low_confidence_evidence_creation_performed": False,
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
        "control_quality_degradation_request_count": 0,
        "actual_input_request_count": 0,
        "quality_degradation_records": [],
        "quality_degradation_record_count": 0,
        "control_scenarios_covered": [],
        "control_scenario_count": 0,
        "one_control_record_per_scenario": False,
        "protected_semantic_asset_types_covered": [],
        "protected_semantic_asset_type_count": 0,
        "one_control_record_per_protected_semantic_asset_type": False,
        "duplicate_chunk_control_record_count": 0,
        "duplicate_control_never_requests_embedding_or_index_write": False,
        "traceability_fields_covered": [],
        "traceability_field_count": 0,
        "control_traceability_reference_count": 0,
        "control_traceability_reference_shape_preserved": False,
        "source_body_or_parser_output_or_fragment_content_retained": False,
        "all_protected_surfaces_atomic": False,
        "low_confidence_control_marker_count": 0,
        "all_control_records_low_confidence_requires_human_review": True,
        "business_line_whitebox_review_record_count": 0,
        "low_confidence_evidence_review_record_count": 0,
        "low_quality_is_not_automatic_complete_failure": True,
        "control_request_reference_validation_performed": False,
        "control_quality_degradation_record_projection_performed": False,
        "control_protected_semantic_boundary_label_projection_performed": False,
        "control_duplicate_embedding_index_boundary_label_projection_performed": False,
        "control_low_confidence_evidence_label_projection_performed": False,
        "control_business_line_whitebox_review_label_projection_performed": False,
        "control_output_is_not_actual_quality_degradation": True,
        **_runtime_closed_flags(),
        "chinese_feedback": [
            "控制输入不符合固定质量降级引用合同，已拒绝且未生成任何质量、降级、低可信证据、重复写入、追溯或业务内容。"
        ],
    }
