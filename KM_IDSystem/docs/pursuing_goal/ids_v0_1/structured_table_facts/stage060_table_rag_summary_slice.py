"""Stage060 P2 的表格到 RAG 摘要纯内存控制切片。

本模块只接受两条固定、非业务、reference-only 控制记录，并把 Stage060 P1
定义的 10 字段未来 RAG 摘要接口投影为两条中文摘要控制候选。不会打开或解析
XLSX/CSV，不会读取实际表格或事实，不会生成摘要正文、数值结论、来源绑定或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage060.table_rag_summary.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_TABLE_RAG_SUMMARY"
CONTROL_ADAPTER_VERSION = "ids.table_rag_summary.control_adapter.v0_1.stage060.p2"
SOURCE_IDENTITY_REF = "source:control:stage060-p2"
CONTROL_FIELDS = ("table_rag_summary_input_records",)
SUMMARY_INPUT_FIELDS = (
    "summary_scope_ref",
    "fact_set_ref",
    "fact_id_ref",
    "fact_type",
    "source_identity_ref",
    "source_document_ref",
    "workbook_ref",
    "worksheet_ref",
    "row_range_ref",
    "column_range_ref",
    "schema_profile_ref",
    "evidence_ref",
    "rag_summary_eligibility",
)
RAG_SUMMARY_FIELDS = (
    "rag_summary_id",
    "summary_scope_ref",
    "fact_set_ref",
    "fact_reference_list",
    "source_location_ref_list",
    "summary_language",
    "summary_state",
    "numeric_claim_state",
    "human_review_state",
    "evidence_ref",
)
SOURCE_LOCATION_FIELDS = (
    "source_document_ref",
    "workbook_ref",
    "worksheet_ref",
    "row_range_ref",
    "column_range_ref",
    "evidence_ref",
)

CONTROL_RECORD_EXPECTATIONS = {
    "source-document:control:stage060-p2:production": {
        "summary_scope_ref": "summary-scope:control:stage060-p2:production",
        "fact_set_ref": "fact-set:control:stage060-p2:production",
        "fact_id_ref": "fact-ref:control:stage060-p2:production",
        "fact_type": "PRODUCTION_FACT",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "workbook_ref": "workbook:control:stage060-p2:production",
        "worksheet_ref": "worksheet:control:stage060-p2:production",
        "row_range_ref": "row-range:control:stage060-p2:production",
        "column_range_ref": "column-range:control:stage060-p2:production",
        "schema_profile_ref": "schema-profile:control:stage060-p2:production",
        "evidence_ref": "evidence:control:stage060-p2:production",
        "rag_summary_eligibility": (
            "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
        ),
    },
    "source-document:control:stage060-p2:quality": {
        "summary_scope_ref": "summary-scope:control:stage060-p2:quality",
        "fact_set_ref": "fact-set:control:stage060-p2:quality",
        "fact_id_ref": "fact-ref:control:stage060-p2:quality",
        "fact_type": "QUALITY_FACT",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "workbook_ref": "workbook:control:stage060-p2:quality",
        "worksheet_ref": "worksheet:control:stage060-p2:quality",
        "row_range_ref": "row-range:control:stage060-p2:quality",
        "column_range_ref": "column-range:control:stage060-p2:quality",
        "schema_profile_ref": "schema-profile:control:stage060-p2:quality",
        "evidence_ref": "evidence:control:stage060-p2:quality",
        "rag_summary_eligibility": (
            "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
        ),
    },
}


def execute_table_rag_summary_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制记录的中文 RAG 摘要候选接口。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [_rag_summary_candidate(record) for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_RAG_SUMMARY_CANDIDATE_CONTROL_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "control_summary_input_record_count": len(records),
        "actual_summary_input_record_count": 0,
        "rag_summary_candidates": candidates,
        "rag_summary_candidate_count": len(candidates),
        "fact_reference_count": sum(
            len(candidate["fact_reference_list"]) for candidate in candidates
        ),
        "fact_types": [record["fact_type"] for record in records],
        "source_location_binding_candidate_count": len(candidates),
        "source_location_references_preserved": all(
            _source_location_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_reference_validation_performed": True,
        "control_fact_reference_validation_performed": True,
        "control_table_summary_candidate_projection_performed": True,
        "all_summary_text_unset": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "summary_requires_fact_reference_before_future_use": True,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "rag_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "actual_structured_fact_created": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_rag_summary_created": False,
        "actual_summary_text_retained": False,
        "actual_rag_summary_persisted": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "rag_summary_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "当前仅在内存中投影固定表格摘要控制候选，未读取、打开或解析任何真实 XLSX、CSV、生产记录、质检记录、事实或摘要正文。",
            "候选只保留结构化事实、来源文档、工作簿、工作表、行列范围和证据引用，未创建真实来源绑定、证据记录或 RAG 摘要。",
            "数值统计只能依赖未来带来源位置和证据绑定的结构化事实，RAG 摘要候选不能替代事实或形成数值结论。",
            "真实表格、事实、来源位置、证据、摘要资格或数值无法确认时必须等待人工处理，不能自动写入摘要层。",
        ],
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("table_rag_summary_input_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != len(CONTROL_RECORD_EXPECTATIONS):
        return None

    accepted = [_accepted_control_record(record) for record in records]
    if any(record is None for record in accepted):
        return None
    normalized = [record for record in accepted if record is not None]
    if [record["source_document_ref"] for record in normalized] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return normalized


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(SUMMARY_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in SUMMARY_INPUT_FIELDS}
    source_document_ref = normalized["source_document_ref"]
    if not isinstance(source_document_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_document_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _rag_summary_candidate(record: Mapping[str, object]) -> dict[str, Any]:
    return {
        "rag_summary_id": (
            "rag-summary-candidate:control:stage060-p2:"
            f"{record['fact_type'].lower()}"
        ),
        "summary_scope_ref": record["summary_scope_ref"],
        "fact_set_ref": record["fact_set_ref"],
        "fact_reference_list": [record["fact_id_ref"]],
        "source_location_ref_list": [
            record[field] for field in SOURCE_LOCATION_FIELDS
        ],
        "summary_language": "zh-CN",
        "summary_state": "CANDIDATE_REFERENCE_ONLY_NOT_PERSISTED",
        "numeric_claim_state": "FACT_REFERENCE_ONLY_NO_NUMERIC_CLAIM",
        "human_review_state": "PENDING_HUMAN_CONFIRMATION",
        "evidence_ref": record["evidence_ref"],
    }


def _source_location_preserved(candidate: Mapping[str, object]) -> bool:
    locations = candidate["source_location_ref_list"]
    return (
        isinstance(locations, list)
        and len(locations) == len(SOURCE_LOCATION_FIELDS)
        and all(isinstance(value, str) and ":control:" in value for value in locations)
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "source_identity_ref": None,
        "control_summary_input_record_count": 0,
        "actual_summary_input_record_count": 0,
        "rag_summary_candidates": [],
        "rag_summary_candidate_count": 0,
        "fact_reference_count": 0,
        "fact_types": [],
        "source_location_binding_candidate_count": 0,
        "source_location_references_preserved": False,
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_reference_validation_performed": False,
        "control_fact_reference_validation_performed": False,
        "control_table_summary_candidate_projection_performed": False,
        "all_summary_text_unset": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "summary_requires_fact_reference_before_future_use": True,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "rag_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "actual_structured_fact_created": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_rag_summary_created": False,
        "actual_summary_text_retained": False,
        "actual_rag_summary_persisted": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "rag_summary_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "控制输入不符合固定引用合同，已拒绝且未生成任何摘要候选或来源引用。"
        ],
    }
