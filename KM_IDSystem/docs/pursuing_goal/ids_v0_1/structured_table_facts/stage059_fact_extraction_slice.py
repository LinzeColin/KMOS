"""Stage059 P2 的事实抽取纯内存控制切片。

本模块只接受两条固定、非业务、reference-only 控制记录，并把 Stage059 P1
定义的 25 字段未来 typed fact 形状投影为三条控制候选。不会打开或解析
XLSX/CSV，不会读取实际表格值，不会创建业务事实、RAG 摘要、来源绑定或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage059.fact_extraction.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_FACT_EXTRACTION"
CONTROL_ADAPTER_VERSION = "ids.fact_extraction.control_adapter.v0_1.stage059.p2"
SOURCE_IDENTITY_REF = "source:control:stage059-p2"
CONTROL_FIELDS = ("fact_extraction_input_records",)
FACT_EXTRACTION_INPUT_FIELDS = (
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "schema_profile_ref",
    "field_candidate_ref",
    "record_type",
    "evidence_ref",
)
TYPED_FACT_FIELDS = (
    "fact_id",
    "fact_type",
    "record_type",
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "schema_profile_ref",
    "field_candidate_ref",
    "field_name_ref",
    "field_type",
    "typed_value",
    "unit_ref",
    "record_date_ref",
    "equipment_ref",
    "material_ref",
    "quality_result_ref",
    "quality_state",
    "evidence_ref",
    "extraction_state",
    "rag_summary_eligibility",
)
TYPED_SEMANTIC_CATEGORIES = (
    "measurement_value",
    "unit_ref",
    "record_date_ref",
    "equipment_ref",
    "material_ref",
    "quality_result_ref",
    "fact_type",
)
RAG_SUMMARY_ELIGIBILITY = "DEFERRED_TO_STAGE060_REQUIRES_FUTURE_VERIFIED_FACT_REFERENCE"

CONTROL_RECORD_EXPECTATIONS = {
    "source-document:control:stage059-p2:production": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "XLSX",
        "workbook_ref": "workbook:control:stage059-p2:production",
        "worksheet_ref": "worksheet:control:stage059-p2:production",
        "header_row_ref": "header-row:control:stage059-p2:production",
        "row_range_ref": "row-range:control:stage059-p2:production",
        "column_range_ref": "column-range:control:stage059-p2:production",
        "schema_profile_ref": "schema-profile:control:stage059-p2:production",
        "field_candidate_ref": "field-candidate:control:stage059-p2:production",
        "record_type": "PRODUCTION_RECORD",
        "evidence_ref": "evidence:control:stage059-p2:production",
    },
    "source-document:control:stage059-p2:quality": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "CSV",
        "workbook_ref": "workbook:control:stage059-p2:quality",
        "worksheet_ref": "worksheet:control:stage059-p2:quality",
        "header_row_ref": "header-row:control:stage059-p2:quality",
        "row_range_ref": "row-range:control:stage059-p2:quality",
        "column_range_ref": "column-range:control:stage059-p2:quality",
        "schema_profile_ref": "schema-profile:control:stage059-p2:quality",
        "field_candidate_ref": "field-candidate:control:stage059-p2:quality",
        "record_type": "QUALITY_INSPECTION_RECORD",
        "evidence_ref": "evidence:control:stage059-p2:quality",
    },
}

FACT_CANDIDATE_TEMPLATES = {
    "source-document:control:stage059-p2:production": (
        {
            "fact_id": "fact-candidate:control:stage059-p2:production",
            "fact_type": "PRODUCTION_FACT",
            "field_name_ref": "field-name:control:stage059-p2:production:measurement",
            "field_type": "DECIMAL_OR_INTEGER",
            "unit_ref": "unit-ref:control:stage059-p2:production",
            "record_date_ref": "record-date-ref:control:stage059-p2:production",
            "equipment_ref": "equipment-ref:control:stage059-p2:production",
            "material_ref": "material-ref:control:stage059-p2:production",
        },
    ),
    "source-document:control:stage059-p2:quality": (
        {
            "fact_id": "fact-candidate:control:stage059-p2:quality",
            "fact_type": "QUALITY_FACT",
            "field_name_ref": "field-name:control:stage059-p2:quality:result",
            "field_type": "ENUMERATED_QUALITY_RESULT_REFERENCE",
            "record_date_ref": "record-date-ref:control:stage059-p2:quality",
            "equipment_ref": "equipment-ref:control:stage059-p2:quality",
            "quality_result_ref": "quality-result-ref:control:stage059-p2:quality",
        },
        {
            "fact_id": "fact-candidate:control:stage059-p2:inspection",
            "fact_type": "INSPECTION_FACT",
            "field_name_ref": "field-name:control:stage059-p2:quality:inspection",
            "field_type": "ENUMERATED_FACT_TYPE",
            "record_date_ref": "record-date-ref:control:stage059-p2:inspection",
            "equipment_ref": "equipment-ref:control:stage059-p2:inspection",
            "quality_result_ref": "quality-result-ref:control:stage059-p2:inspection",
        },
    ),
}


def execute_fact_extraction_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制记录的 typed fact 候选。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [
        candidate
        for record in records
        for candidate in _fact_candidates(record)
    ]
    field_types = sorted({candidate["field_type"] for candidate in candidates})
    fact_categories = sorted({candidate["fact_type"] for candidate in candidates})
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_FACT_CANDIDATE_CONTROL_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "fact_extraction_input_record_count": len(records),
        "structured_fact_candidates": candidates,
        "structured_fact_candidate_count": len(candidates),
        "fact_category_count": len(fact_categories),
        "fact_categories": fact_categories,
        "candidate_field_types": field_types,
        "candidate_field_type_count": len(field_types),
        "typed_semantic_categories_covered": list(TYPED_SEMANTIC_CATEGORIES),
        "typed_semantic_category_count": len(TYPED_SEMANTIC_CATEGORIES),
        "numeric_field_candidate_count": sum(
            candidate["field_type"] == "DECIMAL_OR_INTEGER" for candidate in candidates
        ),
        "all_control_typed_values_unset": all(
            candidate["typed_value"] is None for candidate in candidates
        ),
        "source_location_binding_candidate_count": len(candidates),
        "source_location_references_preserved": all(
            _source_location_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_reference_validation_performed": True,
        "control_field_reference_validation_performed": True,
        "control_fact_candidate_projection_performed": True,
        "rag_summary_candidate_count": 0,
        "rag_summary_deferred_to_stage060": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "numeric_statistic_computation_performed": False,
        "actual_structured_fact_created": False,
        "actual_structured_fact_persisted": False,
        "actual_typed_value_retained": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_rag_summary_created": False,
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
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("fact_extraction_input_records")
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
    if not isinstance(record, Mapping) or set(record) != set(FACT_EXTRACTION_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in FACT_EXTRACTION_INPUT_FIELDS}
    source_document_ref = normalized["source_document_ref"]
    if not isinstance(source_document_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_document_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _fact_candidates(record: Mapping[str, object]) -> list[dict[str, Any]]:
    return [
        {
            "fact_id": template["fact_id"],
            "fact_type": template["fact_type"],
            "record_type": record["record_type"],
            "source_identity_ref": record["source_identity_ref"],
            "source_document_ref": record["source_document_ref"],
            "file_format": record["file_format"],
            "workbook_ref": record["workbook_ref"],
            "worksheet_ref": record["worksheet_ref"],
            "header_row_ref": record["header_row_ref"],
            "row_range_ref": record["row_range_ref"],
            "column_range_ref": record["column_range_ref"],
            "schema_profile_ref": record["schema_profile_ref"],
            "field_candidate_ref": record["field_candidate_ref"],
            "field_name_ref": template["field_name_ref"],
            "field_type": template["field_type"],
            "typed_value": None,
            "unit_ref": template.get("unit_ref"),
            "record_date_ref": template.get("record_date_ref"),
            "equipment_ref": template.get("equipment_ref"),
            "material_ref": template.get("material_ref"),
            "quality_result_ref": template.get("quality_result_ref"),
            "quality_state": "UNASSESSED",
            "evidence_ref": record["evidence_ref"],
            "extraction_state": "CANDIDATE_CONTROL_REFERENCE_ONLY",
            "rag_summary_eligibility": RAG_SUMMARY_ELIGIBILITY,
        }
        for template in FACT_CANDIDATE_TEMPLATES[record["source_document_ref"]]
    ]


def _source_location_preserved(candidate: Mapping[str, object]) -> bool:
    return all(
        isinstance(candidate[field], str) and candidate[field]
        for field in (
            "source_document_ref",
            "worksheet_ref",
            "header_row_ref",
            "row_range_ref",
            "column_range_ref",
            "evidence_ref",
        )
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "source_identity_ref": None,
        "fact_extraction_input_record_count": 0,
        "structured_fact_candidates": [],
        "structured_fact_candidate_count": 0,
        "fact_category_count": 0,
        "fact_categories": [],
        "candidate_field_types": [],
        "candidate_field_type_count": 0,
        "typed_semantic_categories_covered": [],
        "typed_semantic_category_count": 0,
        "numeric_field_candidate_count": 0,
        "all_control_typed_values_unset": True,
        "source_location_binding_candidate_count": 0,
        "source_location_references_preserved": False,
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_reference_validation_performed": False,
        "control_field_reference_validation_performed": False,
        "control_fact_candidate_projection_performed": False,
        "rag_summary_candidate_count": 0,
        "rag_summary_deferred_to_stage060": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "numeric_statistic_computation_performed": False,
        "actual_structured_fact_created": False,
        "actual_structured_fact_persisted": False,
        "actual_typed_value_retained": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "actual_rag_summary_created": False,
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
    }
