"""Stage062 P2 的表格证据绑定纯内存控制切片。

本模块只接受两条固定、非业务、reference-only 控制请求，并依据 Stage062 P1
的十九字段输入与十七字段输出投影两个未绑定候选。它不会读取表格、解析
XLSX/CSV、识别字段、抽取事实、计算数值、创建证据或写入任何持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage062.table_evidence_binding.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_TABLE_EVIDENCE_BINDING"
CONTROL_ADAPTER_VERSION = "ids.table_evidence_binding.control_adapter.v0_1.stage062.p2"
CONTROL_FIELDS = ("table_evidence_binding_requests",)
BINDING_INPUT_FIELDS = (
    "binding_request_ref",
    "fact_ref",
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
    "file_format",
    "record_type",
    "workbook_ref",
    "schema_profile_ref",
    "field_candidate_ref",
    "primary_key_ref",
    "quality_result_ref",
    "measurement_value_ref",
    "unit_ref",
    "record_date_ref",
    "fact_type",
)
BINDING_CANDIDATE_FIELDS = (
    "table_evidence_binding_ref",
    "binding_request_ref",
    "fact_ref",
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
    "field_candidate_ref",
    "schema_profile_ref",
    "quality_result_ref",
    "fact_type",
    "binding_state",
    "human_review_state",
    "numeric_authority_state",
    "remediation_state",
)
BINDING_DIMENSIONS = (
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
)


CONTROL_RECORD_EXPECTATIONS = {
    "binding-request:control:stage062-p2:production": {
        "fact_ref": "fact:control:stage062-p2:production",
        "evidence_id": "evidence-id:control:stage062-p2:production",
        "document_id": "document-id:control:stage062-p2:production",
        "sheet": "sheet:control:stage062-p2:production",
        "row": "row:control:stage062-p2:production",
        "column": "column:control:stage062-p2:production",
        "source_uri": "source-uri:control:stage062-p2:production",
        "file_format": "XLSX",
        "record_type": "PRODUCTION_RECORD",
        "workbook_ref": "workbook:control:stage062-p2:production",
        "schema_profile_ref": "schema-profile:control:stage062-p2:production",
        "field_candidate_ref": "field-candidate:control:stage062-p2:production",
        "primary_key_ref": "primary-key:control:stage062-p2:production",
        "quality_result_ref": "quality-result:control:stage062-p2:production",
        "measurement_value_ref": "measurement-value:control:stage062-p2:production",
        "unit_ref": "unit:control:stage062-p2:production",
        "record_date_ref": "record-date:control:stage062-p2:production",
        "fact_type": "MEASUREMENT_FACT",
    },
    "binding-request:control:stage062-p2:quality": {
        "fact_ref": "fact:control:stage062-p2:quality",
        "evidence_id": "evidence-id:control:stage062-p2:quality",
        "document_id": "document-id:control:stage062-p2:quality",
        "sheet": "sheet:control:stage062-p2:quality",
        "row": "row:control:stage062-p2:quality",
        "column": "column:control:stage062-p2:quality",
        "source_uri": "source-uri:control:stage062-p2:quality",
        "file_format": "CSV",
        "record_type": "QUALITY_INSPECTION_RECORD",
        "workbook_ref": "workbook:control:stage062-p2:quality",
        "schema_profile_ref": "schema-profile:control:stage062-p2:quality",
        "field_candidate_ref": "field-candidate:control:stage062-p2:quality",
        "primary_key_ref": "primary-key:control:stage062-p2:quality",
        "quality_result_ref": "quality-result:control:stage062-p2:quality",
        "measurement_value_ref": "measurement-value:control:stage062-p2:quality",
        "unit_ref": "unit:control:stage062-p2:quality",
        "record_date_ref": "record-date:control:stage062-p2:quality",
        "fact_type": "QUALITY_RESULT_FACT",
    },
}


def execute_table_evidence_binding_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制请求的表格证据绑定候选。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [_binding_candidate(record) for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_TABLE_EVIDENCE_BINDING_CANDIDATE_CONTROL_SLICE",
        "control_binding_request_count": len(records),
        "actual_input_record_count": 0,
        "table_evidence_binding_candidates": candidates,
        "table_evidence_binding_candidate_count": len(candidates),
        "binding_dimensions_covered": list(BINDING_DIMENSIONS),
        "binding_dimension_count": len(BINDING_DIMENSIONS),
        "control_binding_dimension_reference_count": len(candidates)
        * len(BINDING_DIMENSIONS),
        "record_types_covered": [record["record_type"] for record in records],
        "file_formats_covered": [record["file_format"] for record in records],
        "source_location_reference_shape_preserved": all(
            _binding_dimensions_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_header_or_cell_content_retained": False,
        "all_binding_states_unbound": all(
            candidate["binding_state"] == "UNBOUND_REFERENCE_ONLY"
            for candidate in candidates
        ),
        "all_human_review_required": all(
            candidate["human_review_state"] == "REQUIRED_WHEN_UNVERIFIED"
            for candidate in candidates
        ),
        "all_numeric_authority_blocked": all(
            candidate["numeric_authority_state"]
            == "BLOCKED_UNVERIFIED_REFERENCE_ONLY"
            for candidate in candidates
        ),
        "control_binding_request_reference_validation_performed": True,
        "control_binding_candidate_projection_performed": True,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "source_location_binding_performed": False,
        "evidence_binding_performed": False,
        "actual_structured_fact_created": False,
        "actual_table_evidence_binding_created": False,
        "actual_table_evidence_binding_persisted": False,
        "actual_evidence_record_created": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "当前只在内存中投影固定表格证据绑定控制候选，未读取、打开或解析任何真实 XLSX、CSV、生产记录、质检记录、工作表或单元格。",
            "候选只保留 evidence_id、document_id、sheet、row、column 和 source_uri 的控制引用，未创建真实表格事实、来源位置绑定、证据记录或数据库状态。",
            "候选均为未绑定且必须人工确认；未验证的来源和数值不能形成统计或确定性结论，模型文本和摘要不能替代结构化事实。",
            "真实来源、行列位置、字段、单位、日期、质量结果或证据无法确认时必须停止并交由人工处理，不能自动写入业务层。",
        ],
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("table_evidence_binding_requests")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != len(CONTROL_RECORD_EXPECTATIONS):
        return None

    accepted = [_accepted_control_record(record) for record in records]
    if any(record is None for record in accepted):
        return None
    normalized = [record for record in accepted if record is not None]
    if [record["binding_request_ref"] for record in normalized] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return normalized


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(BINDING_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in BINDING_INPUT_FIELDS}
    binding_request_ref = normalized["binding_request_ref"]
    if not isinstance(binding_request_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(binding_request_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _binding_candidate(record: Mapping[str, object]) -> dict[str, Any]:
    source_suffix = str(record["binding_request_ref"]).rsplit(":", 1)[1]
    return {
        "table_evidence_binding_ref": (
            "table-evidence-binding-candidate:control:stage062-p2:"
            f"{source_suffix}"
        ),
        "binding_request_ref": record["binding_request_ref"],
        "fact_ref": record["fact_ref"],
        "evidence_id": record["evidence_id"],
        "document_id": record["document_id"],
        "sheet": record["sheet"],
        "row": record["row"],
        "column": record["column"],
        "source_uri": record["source_uri"],
        "field_candidate_ref": record["field_candidate_ref"],
        "schema_profile_ref": record["schema_profile_ref"],
        "quality_result_ref": record["quality_result_ref"],
        "fact_type": record["fact_type"],
        "binding_state": "UNBOUND_REFERENCE_ONLY",
        "human_review_state": "REQUIRED_WHEN_UNVERIFIED",
        "numeric_authority_state": "BLOCKED_UNVERIFIED_REFERENCE_ONLY",
        "remediation_state": "HUMAN_SOURCE_AND_EVIDENCE_CONFIRMATION_REQUIRED",
    }


def _binding_dimensions_preserved(candidate: Mapping[str, object]) -> bool:
    return all(
        isinstance(candidate[field], str) and ":control:" in candidate[field]
        for field in BINDING_DIMENSIONS
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "control_binding_request_count": 0,
        "actual_input_record_count": 0,
        "table_evidence_binding_candidates": [],
        "table_evidence_binding_candidate_count": 0,
        "binding_dimensions_covered": [],
        "binding_dimension_count": 0,
        "control_binding_dimension_reference_count": 0,
        "record_types_covered": [],
        "file_formats_covered": [],
        "source_location_reference_shape_preserved": False,
        "source_body_or_header_or_cell_content_retained": False,
        "all_binding_states_unbound": True,
        "all_human_review_required": True,
        "all_numeric_authority_blocked": True,
        "control_binding_request_reference_validation_performed": False,
        "control_binding_candidate_projection_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "source_location_binding_performed": False,
        "evidence_binding_performed": False,
        "actual_structured_fact_created": False,
        "actual_table_evidence_binding_created": False,
        "actual_table_evidence_binding_persisted": False,
        "actual_evidence_record_created": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "控制输入不符合固定引用合同，已拒绝且未生成任何表格证据绑定候选、来源引用或业务内容。"
        ],
    }
