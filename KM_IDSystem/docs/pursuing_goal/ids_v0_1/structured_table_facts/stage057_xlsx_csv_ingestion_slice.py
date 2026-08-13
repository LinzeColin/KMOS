"""Stage057 P2 的 XLSX/CSV 结构化接入纯内存控制切片。

模块只接受两条固定、非业务、reference-only 控制记录，并把 P1 已定义的
字段语义投影为 schema、事实候选与 RAG 摘要候选。它不会打开、解析或保留
任何 XLSX/CSV、工作表、单元格、公式或业务事实，也不会写入数据库或运行面。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage057.xlsx_csv_ingestion.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_XLSX_CSV_INGESTION"
CONTROL_ADAPTER_VERSION = "ids.xlsx_csv_ingestion.control_adapter.v0_1.stage057.p2"
SOURCE_IDENTITY_REF = "source:control:stage057-p2"
CONTROL_FIELDS = ("table_input_records",)
TABLE_INPUT_FIELDS = (
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "workbook_ref",
    "worksheet_ref",
    "row_range_ref",
    "column_range_ref",
    "record_type",
    "schema_profile_ref",
    "fact_type",
    "evidence_ref",
    "ingestion_state",
)
FUTURE_FACT_FIELDS = (
    "fact_id",
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "worksheet_ref",
    "row_range_ref",
    "column_range_ref",
    "field_name",
    "field_type",
    "typed_value",
    "unit_ref",
    "record_date",
    "equipment_ref",
    "material_ref",
    "quality_result",
    "fact_type",
    "quality_state",
    "evidence_ref",
    "rag_summary_eligibility",
)
FIELD_TYPES = {
    "measurement_value": "DECIMAL_OR_INTEGER",
    "unit_ref": "UNIT_REFERENCE",
    "record_date": "DATE_OR_DATETIME",
    "equipment_ref": "IDENTIFIER_REFERENCE",
    "material_ref": "IDENTIFIER_REFERENCE",
    "quality_result": "ENUMERATED_QUALITY_RESULT",
    "fact_type": "ENUMERATED_FACT_TYPE",
}
RAG_SUMMARY_ELIGIBILITY = "METADATA_ONLY_SUMMARY_CANDIDATE_REQUIRES_FACT_REFERENCES"

CONTROL_PROFILES = {
    "schema-profile:control:stage057-p2:production": (
        "record_date",
        "equipment_ref",
        "material_ref",
        "measurement_value",
        "unit_ref",
        "fact_type",
    ),
    "schema-profile:control:stage057-p2:quality": (
        "record_date",
        "equipment_ref",
        "quality_result",
        "fact_type",
    ),
}

CONTROL_RECORD_EXPECTATIONS = {
    "source-document:control:stage057-p2:1": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "XLSX",
        "workbook_ref": "workbook:control:stage057-p2:1",
        "worksheet_ref": "worksheet:control:stage057-p2:1",
        "row_range_ref": "row-range:control:stage057-p2:1",
        "column_range_ref": "column-range:control:stage057-p2:1",
        "record_type": "PRODUCTION_RECORD",
        "schema_profile_ref": "schema-profile:control:stage057-p2:production",
        "fact_type": "PRODUCTION_MEASUREMENT",
        "evidence_ref": "evidence:control:stage057-p2:1",
        "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
    },
    "source-document:control:stage057-p2:2": {
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "CSV",
        "workbook_ref": "workbook:control:stage057-p2:csv-reference",
        "worksheet_ref": "worksheet:control:stage057-p2:2",
        "row_range_ref": "row-range:control:stage057-p2:2",
        "column_range_ref": "column-range:control:stage057-p2:2",
        "record_type": "QUALITY_INSPECTION_RECORD",
        "schema_profile_ref": "schema-profile:control:stage057-p2:quality",
        "fact_type": "QUALITY_RESULT",
        "evidence_ref": "evidence:control:stage057-p2:2",
        "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
    },
}


def execute_xlsx_csv_ingestion_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制记录的 schema、事实候选与摘要候选。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    schema_profiles = [_schema_profile_candidate(record) for record in records]
    fact_candidates = [
        candidate
        for record in records
        for candidate in _structured_fact_candidates(record)
    ]
    rag_candidates = [
        _rag_summary_candidate(record, schema, fact_candidates)
        for record, schema in zip(records, schema_profiles)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_SCHEMA_AND_FACT_CANDIDATE_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "table_input_record_count": len(records),
        "schema_profile_candidates": schema_profiles,
        "schema_profile_candidate_count": len(schema_profiles),
        "structured_fact_candidates": fact_candidates,
        "structured_fact_candidate_count": len(fact_candidates),
        "rag_summary_candidates": rag_candidates,
        "rag_summary_candidate_count": len(rag_candidates),
        "source_location_binding_candidate_count": len(fact_candidates),
        "numeric_field_candidate_count": sum(
            item["field_name"] == "measurement_value" for item in fact_candidates
        ),
        "source_location_references_preserved": all(
            _source_location_preserved(candidate) for candidate in fact_candidates
        ),
        "source_body_or_cell_content_retained": False,
        "control_schema_profile_inference_performed": True,
        "control_field_identification_performed": True,
        "in_memory_structured_fact_candidate_projection_created": True,
        "rag_summary_candidates_separated_from_facts": True,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "actual_structured_fact_created": False,
        "actual_structured_fact_persisted": False,
        "actual_typed_value_retained": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "numeric_statistic_computation_performed": False,
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
    records = control_input.get("table_input_records")
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


def _schema_profile_candidate(record: Mapping[str, object]) -> dict[str, Any]:
    field_names = CONTROL_PROFILES[record["schema_profile_ref"]]
    return {
        "source_identity_ref": record["source_identity_ref"],
        "source_document_ref": record["source_document_ref"],
        "file_format": record["file_format"],
        "workbook_ref": record["workbook_ref"],
        "worksheet_ref": record["worksheet_ref"],
        "row_range_ref": record["row_range_ref"],
        "column_range_ref": record["column_range_ref"],
        "record_type": record["record_type"],
        "schema_profile_ref": record["schema_profile_ref"],
        "identified_field_names": list(field_names),
        "identified_field_count": len(field_names),
        "schema_profile_kind": "CONTROL_REFERENCE_ONLY_NOT_SOURCE_SCHEMA",
        "actual_table_schema_created": False,
        "source_body_or_cell_content_retained": False,
    }


def _structured_fact_candidates(record: Mapping[str, object]) -> list[dict[str, Any]]:
    field_names = CONTROL_PROFILES[record["schema_profile_ref"]]
    return [
        {
            "fact_id": (
                f"fact-candidate:control:stage057-p2:{record['source_document_ref'].rsplit(':', 1)[1]}:{index}"
            ),
            "source_identity_ref": record["source_identity_ref"],
            "source_document_ref": record["source_document_ref"],
            "file_format": record["file_format"],
            "worksheet_ref": record["worksheet_ref"],
            "row_range_ref": record["row_range_ref"],
            "column_range_ref": record["column_range_ref"],
            "field_name": field_name,
            "field_type": FIELD_TYPES[field_name],
            "typed_value": None,
            "unit_ref": None,
            "record_date": None,
            "equipment_ref": None,
            "material_ref": None,
            "quality_result": None,
            "fact_type": record["fact_type"],
            "quality_state": "UNASSESSED",
            "evidence_ref": record["evidence_ref"],
            "rag_summary_eligibility": RAG_SUMMARY_ELIGIBILITY,
        }
        for index, field_name in enumerate(field_names, start=1)
    ]


def _rag_summary_candidate(
    record: Mapping[str, object],
    schema: Mapping[str, object],
    candidates: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    matching_refs = [
        candidate["fact_id"]
        for candidate in candidates
        if candidate["source_document_ref"] == record["source_document_ref"]
    ]
    return {
        "summary_ref": (
            f"rag-summary-candidate:control:stage057-p2:{record['source_document_ref'].rsplit(':', 1)[1]}"
        ),
        "source_identity_ref": record["source_identity_ref"],
        "source_document_ref": record["source_document_ref"],
        "worksheet_ref": record["worksheet_ref"],
        "row_range_ref": record["row_range_ref"],
        "column_range_ref": record["column_range_ref"],
        "evidence_ref": record["evidence_ref"],
        "record_type": record["record_type"],
        "schema_profile_ref": schema["schema_profile_ref"],
        "structured_fact_candidate_refs": matching_refs,
        "summary_mode": "METADATA_ONLY_SUMMARY_CANDIDATE_REQUIRES_FACT_REFERENCES",
        "fact_candidate_references_required": True,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "actual_rag_summary_created": False,
        "actual_summary_write_performed": False,
    }


def _source_location_preserved(candidate: Mapping[str, object]) -> bool:
    return all(
        isinstance(candidate[field], str) and candidate[field]
        for field in (
            "source_document_ref",
            "worksheet_ref",
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
        "table_input_record_count": 0,
        "schema_profile_candidates": [],
        "schema_profile_candidate_count": 0,
        "structured_fact_candidates": [],
        "structured_fact_candidate_count": 0,
        "rag_summary_candidates": [],
        "rag_summary_candidate_count": 0,
        "source_location_binding_candidate_count": 0,
        "numeric_field_candidate_count": 0,
        "source_location_references_preserved": False,
        "source_body_or_cell_content_retained": False,
        "control_schema_profile_inference_performed": False,
        "control_field_identification_performed": False,
        "in_memory_structured_fact_candidate_projection_created": False,
        "rag_summary_candidates_separated_from_facts": False,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "actual_structured_fact_created": False,
        "actual_structured_fact_persisted": False,
        "actual_typed_value_retained": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "numeric_statistic_computation_performed": False,
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
