"""Stage058 P2 的表格 Schema 推断纯内存控制切片。

本模块只接受两条固定、非业务、reference-only 控制记录，并把 Stage058 P1
定义的 18 字段未来 Schema profile 投影为候选行。不会打开、检测或解析
XLSX/CSV，不会保留表头、单元格、公式或业务资料；事实抽取和 RAG 写入仍由
后续冻结 Stage059/060 处理。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage058.table_schema_inference.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_TABLE_SCHEMA_INFERENCE"
CONTROL_ADAPTER_VERSION = "ids.table_schema_inference.control_adapter.v0_1.stage058.p2"
SOURCE_IDENTITY_REF = "source:control:stage058-p2"
CONTROL_FIELDS = ("schema_inference_input_records",)
TABLE_INPUT_FIELDS = (
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "record_type",
    "evidence_ref",
)
SCHEMA_PROFILE_FIELDS = (
    "schema_profile_id",
    "source_document_ref",
    "file_format",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "candidate_column_name",
    "candidate_field_type",
    "candidate_unit_ref",
    "candidate_date_format_ref",
    "candidate_equipment_ref",
    "candidate_material_ref",
    "candidate_process_ref",
    "candidate_quality_result_ref",
    "candidate_fact_type",
    "evidence_ref",
    "inference_state",
)

CONTROL_RECORD_EXPECTATIONS = {
    "source-document:control:stage058-p2:production": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "XLSX",
        "workbook_ref": "workbook:control:stage058-p2:production",
        "worksheet_ref": "worksheet:control:stage058-p2:production",
        "header_row_ref": "header-row:control:stage058-p2:production",
        "row_range_ref": "row-range:control:stage058-p2:production",
        "column_range_ref": "column-range:control:stage058-p2:production",
        "record_type": "PRODUCTION_RECORD",
        "evidence_ref": "evidence:control:stage058-p2:production",
    },
    "source-document:control:stage058-p2:quality": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "CSV",
        "workbook_ref": "workbook:control:stage058-p2:quality",
        "worksheet_ref": "worksheet:control:stage058-p2:quality",
        "header_row_ref": "header-row:control:stage058-p2:quality",
        "row_range_ref": "row-range:control:stage058-p2:quality",
        "column_range_ref": "column-range:control:stage058-p2:quality",
        "record_type": "QUALITY_INSPECTION_RECORD",
        "evidence_ref": "evidence:control:stage058-p2:quality",
    },
}

CONTROL_SCHEMA_TEMPLATES = {
    "source-document:control:stage058-p2:production": (
        {
            "column_handle": "column-handle:control:stage058-p2:production:date",
            "field_type": "DATE_OR_DATETIME",
            "date_format_ref": "date-format:control:stage058-p2:yyyy-mm-dd",
            "fact_type": "PRODUCTION_DATE_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:production:equipment",
            "field_type": "IDENTIFIER_REFERENCE",
            "equipment_ref": "equipment-ref:control:stage058-p2:production",
            "fact_type": "PRODUCTION_EQUIPMENT_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:production:material",
            "field_type": "TEXT_REFERENCE",
            "material_ref": "material-ref:control:stage058-p2:production",
            "fact_type": "PRODUCTION_MATERIAL_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:production:process",
            "field_type": "TEXT_REFERENCE",
            "process_ref": "process-ref:control:stage058-p2:production",
            "fact_type": "PRODUCTION_PROCESS_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:production:measurement",
            "field_type": "DECIMAL_OR_INTEGER",
            "unit_ref": "unit-ref:control:stage058-p2:production",
            "fact_type": "PRODUCTION_MEASUREMENT",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:production:fact-type",
            "field_type": "ENUMERATED_FACT_TYPE",
            "fact_type": "PRODUCTION_MEASUREMENT",
        },
    ),
    "source-document:control:stage058-p2:quality": (
        {
            "column_handle": "column-handle:control:stage058-p2:quality:date",
            "field_type": "DATE_OR_DATETIME",
            "date_format_ref": "date-format:control:stage058-p2:yyyy-mm-dd",
            "fact_type": "QUALITY_DATE_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:quality:equipment",
            "field_type": "IDENTIFIER_REFERENCE",
            "equipment_ref": "equipment-ref:control:stage058-p2:quality",
            "fact_type": "QUALITY_EQUIPMENT_REFERENCE",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:quality:result",
            "field_type": "ENUMERATED_QUALITY_RESULT",
            "quality_result_ref": "quality-result-ref:control:stage058-p2",
            "fact_type": "QUALITY_RESULT",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:quality:fact-type",
            "field_type": "ENUMERATED_FACT_TYPE",
            "fact_type": "QUALITY_RESULT",
        },
        {
            "column_handle": "column-handle:control:stage058-p2:quality:unit",
            "field_type": "TEXT_REFERENCE",
            "unit_ref": "unit-ref:control:stage058-p2:quality",
            "fact_type": "QUALITY_MEASUREMENT_REFERENCE",
        },
    ),
}

SEMANTIC_CATEGORIES = (
    "candidate_column_name",
    "candidate_field_type",
    "candidate_date_format_ref",
    "candidate_unit_ref",
    "candidate_material_ref",
    "candidate_equipment_ref",
    "candidate_process_ref",
    "candidate_quality_result_ref",
    "candidate_fact_type",
)


def execute_table_schema_inference_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制记录的 Schema profile 与字段候选。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [
        candidate
        for record in records
        for candidate in _schema_profile_candidates(record)
    ]
    field_types = sorted({candidate["candidate_field_type"] for candidate in candidates})
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_SCHEMA_PROFILE_CANDIDATE_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "schema_inference_input_record_count": len(records),
        "schema_profile_candidates": candidates,
        "schema_profile_candidate_count": len(candidates),
        "schema_profile_group_count": len(records),
        "candidate_field_mapping_count": len(candidates),
        "candidate_field_types": field_types,
        "candidate_field_type_count": len(field_types),
        "semantic_categories_covered": list(SEMANTIC_CATEGORIES),
        "semantic_category_count": len(SEMANTIC_CATEGORIES),
        "source_location_binding_candidate_count": len(candidates),
        "source_location_references_preserved": all(
            _source_location_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_profile_inference_performed": True,
        "control_field_identification_performed": True,
        "control_field_type_inference_performed": True,
        "control_candidate_reference_projection_created": True,
        "structured_fact_candidate_count": 0,
        "rag_summary_candidate_count": 0,
        "fact_extraction_deferred_to_stage059": True,
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
        "actual_schema_profile_created": False,
        "actual_schema_profile_persisted": False,
        "actual_field_mapping_created": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "numeric_statistic_computation_performed": False,
        "actual_structured_fact_created": False,
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
    records = control_input.get("schema_inference_input_records")
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
    if not isinstance(record, Mapping) or set(record) != set(TABLE_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in TABLE_INPUT_FIELDS}
    source_document_ref = normalized["source_document_ref"]
    if not isinstance(source_document_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_document_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _schema_profile_candidates(record: Mapping[str, object]) -> list[dict[str, Any]]:
    templates = CONTROL_SCHEMA_TEMPLATES[record["source_document_ref"]]
    profile_id = (
        "schema-profile-candidate:control:stage058-p2:"
        + record["source_document_ref"].rsplit(":", 1)[1]
    )
    return [
        {
            "schema_profile_id": profile_id,
            "source_document_ref": record["source_document_ref"],
            "file_format": record["file_format"],
            "worksheet_ref": record["worksheet_ref"],
            "header_row_ref": record["header_row_ref"],
            "row_range_ref": record["row_range_ref"],
            "column_range_ref": record["column_range_ref"],
            "candidate_column_name": template["column_handle"],
            "candidate_field_type": template["field_type"],
            "candidate_unit_ref": template.get("unit_ref"),
            "candidate_date_format_ref": template.get("date_format_ref"),
            "candidate_equipment_ref": template.get("equipment_ref"),
            "candidate_material_ref": template.get("material_ref"),
            "candidate_process_ref": template.get("process_ref"),
            "candidate_quality_result_ref": template.get("quality_result_ref"),
            "candidate_fact_type": template["fact_type"],
            "evidence_ref": record["evidence_ref"],
            "inference_state": "CANDIDATE_CONTROL_REFERENCE_ONLY",
        }
        for template in templates
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
        "schema_inference_input_record_count": 0,
        "schema_profile_candidates": [],
        "schema_profile_candidate_count": 0,
        "schema_profile_group_count": 0,
        "candidate_field_mapping_count": 0,
        "candidate_field_types": [],
        "candidate_field_type_count": 0,
        "semantic_categories_covered": [],
        "semantic_category_count": 0,
        "source_location_binding_candidate_count": 0,
        "source_location_references_preserved": False,
        "source_body_or_header_or_cell_content_retained": False,
        "control_schema_profile_inference_performed": False,
        "control_field_identification_performed": False,
        "control_field_type_inference_performed": False,
        "control_candidate_reference_projection_created": False,
        "structured_fact_candidate_count": 0,
        "rag_summary_candidate_count": 0,
        "fact_extraction_deferred_to_stage059": True,
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
        "actual_schema_profile_created": False,
        "actual_schema_profile_persisted": False,
        "actual_field_mapping_created": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "numeric_statistic_computation_performed": False,
        "actual_structured_fact_created": False,
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
