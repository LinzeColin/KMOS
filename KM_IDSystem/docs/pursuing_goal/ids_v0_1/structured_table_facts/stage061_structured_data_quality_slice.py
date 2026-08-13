"""Stage061 P2 的结构化数据质量纯内存控制切片。

本模块只接受两条固定、非业务、reference-only 控制记录，并按 Stage061 P1
定义的输入与结果字段投影十条待人工确认的质量结果候选。不会打开或解析
XLSX/CSV，不会读取实际表格值，不会计算完整性、单位、日期、重复或异常，
也不会创建事实、证据、质量结果或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage061.structured_data_quality.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_STRUCTURED_DATA_QUALITY"
CONTROL_ADAPTER_VERSION = "ids.structured_data_quality.control_adapter.v0_1.stage061.p2"
SOURCE_IDENTITY_REF = "source:control:stage061-p2"
CONTROL_FIELDS = ("structured_data_quality_input_records",)
QUALITY_INPUT_FIELDS = (
    "quality_request_ref",
    "source_identity_ref",
    "source_document_ref",
    "file_format",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "schema_profile_ref",
    "fact_set_ref",
    "field_candidate_ref",
    "primary_key_ref",
    "record_type",
    "evidence_ref",
    "quality_profile_ref",
)
QUALITY_RESULT_FIELDS = (
    "quality_result_ref",
    "quality_request_ref",
    "quality_dimension",
    "quality_state",
    "field_candidate_ref",
    "primary_key_ref",
    "source_identity_ref",
    "source_document_ref",
    "workbook_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "fact_set_ref",
    "evidence_ref",
    "human_review_state",
    "statistical_conclusion_state",
    "remediation_state",
)
QUALITY_DIMENSIONS = (
    "FIELD_COMPLETENESS",
    "UNIT_CONSISTENCY",
    "DATE_VALIDITY",
    "PRIMARY_KEY_DUPLICATION",
    "OUTLIER_REVIEW",
)
SOURCE_LOCATION_FIELDS = (
    "source_document_ref",
    "worksheet_ref",
    "header_row_ref",
    "row_range_ref",
    "column_range_ref",
    "evidence_ref",
)

CONTROL_RECORD_EXPECTATIONS = {
    "source-document:control:stage061-p2:production": {
        "quality_request_ref": "quality-request:control:stage061-p2:production",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "XLSX",
        "workbook_ref": "workbook:control:stage061-p2:production",
        "worksheet_ref": "worksheet:control:stage061-p2:production",
        "header_row_ref": "header-row:control:stage061-p2:production",
        "row_range_ref": "row-range:control:stage061-p2:production",
        "column_range_ref": "column-range:control:stage061-p2:production",
        "schema_profile_ref": "schema-profile:control:stage061-p2:production",
        "fact_set_ref": "fact-set:control:stage061-p2:production",
        "field_candidate_ref": "field-candidate:control:stage061-p2:production",
        "primary_key_ref": "primary-key:control:stage061-p2:production",
        "record_type": "PRODUCTION_RECORD",
        "evidence_ref": "evidence:control:stage061-p2:production",
        "quality_profile_ref": "quality-profile:control:stage061-p2:production",
    },
    "source-document:control:stage061-p2:quality": {
        "quality_request_ref": "quality-request:control:stage061-p2:quality",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "file_format": "CSV",
        "workbook_ref": "workbook:control:stage061-p2:quality",
        "worksheet_ref": "worksheet:control:stage061-p2:quality",
        "header_row_ref": "header-row:control:stage061-p2:quality",
        "row_range_ref": "row-range:control:stage061-p2:quality",
        "column_range_ref": "column-range:control:stage061-p2:quality",
        "schema_profile_ref": "schema-profile:control:stage061-p2:quality",
        "fact_set_ref": "fact-set:control:stage061-p2:quality",
        "field_candidate_ref": "field-candidate:control:stage061-p2:quality",
        "primary_key_ref": "primary-key:control:stage061-p2:quality",
        "record_type": "QUALITY_INSPECTION_RECORD",
        "evidence_ref": "evidence:control:stage061-p2:quality",
        "quality_profile_ref": "quality-profile:control:stage061-p2:quality",
    },
}


def execute_structured_data_quality_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定控制记录的质量结果候选接口。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [
        candidate
        for record in records
        for candidate in _quality_result_candidates(record)
    ]
    dimension_counts = {
        dimension: sum(
            candidate["quality_dimension"] == dimension for candidate in candidates
        )
        for dimension in QUALITY_DIMENSIONS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_STRUCTURED_DATA_QUALITY_CANDIDATE_CONTROL_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "control_quality_input_record_count": len(records),
        "actual_quality_input_record_count": 0,
        "quality_result_candidates": candidates,
        "quality_result_candidate_count": len(candidates),
        "quality_dimensions_covered": list(QUALITY_DIMENSIONS),
        "quality_dimension_count": len(QUALITY_DIMENSIONS),
        "quality_dimension_candidate_counts": dimension_counts,
        "source_location_binding_candidate_count": len(candidates),
        "source_location_references_preserved": all(
            _source_location_preserved(candidate) for candidate in candidates
        ),
        "source_body_or_header_or_cell_content_retained": False,
        "all_quality_states_unassessed": all(
            candidate["quality_state"] == "UNASSESSED" for candidate in candidates
        ),
        "all_human_review_required": all(
            candidate["human_review_state"] == "REQUIRED_WHEN_UNVERIFIED"
            for candidate in candidates
        ),
        "all_statistical_conclusions_blocked": all(
            candidate["statistical_conclusion_state"]
            == "BLOCKED_UNVERIFIED_REFERENCE_ONLY"
            for candidate in candidates
        ),
        "control_quality_input_reference_validation_performed": True,
        "control_source_location_reference_validation_performed": True,
        "control_quality_result_candidate_projection_performed": True,
        "field_completeness_evaluation_performed": False,
        "unit_consistency_evaluation_performed": False,
        "date_validity_evaluation_performed": False,
        "primary_key_duplication_evaluation_performed": False,
        "outlier_evaluation_performed": False,
        "quality_gate_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
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
        "actual_structured_fact_created": False,
        "actual_quality_result_created": False,
        "actual_quality_result_persisted": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "当前仅在内存中投影固定质量结果控制候选，未读取、打开或解析任何真实 XLSX、CSV、生产记录、质检记录、工作表或单元格。",
            "五类质量候选只保留字段、主键、事实集、来源位置和证据的控制引用，未创建真实质量结果、事实、来源绑定或证据记录。",
            "候选均为未评估且必须人工确认；未验证数值不能形成异常值、统计或确定性质量结论。",
            "真实输入、字段、单位、日期、主键、来源位置或证据无法确认时必须停止并交由人工处理，不能自动写入质量层。",
        ],
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("structured_data_quality_input_records")
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
    if not isinstance(record, Mapping) or set(record) != set(QUALITY_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in QUALITY_INPUT_FIELDS}
    source_document_ref = normalized["source_document_ref"]
    if not isinstance(source_document_ref, str):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_document_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _quality_result_candidates(record: Mapping[str, object]) -> list[dict[str, Any]]:
    source_suffix = str(record["source_document_ref"]).rsplit(":", 1)[1]
    return [
        {
            "quality_result_ref": (
                "quality-result-candidate:control:stage061-p2:"
                f"{source_suffix}:{dimension.lower()}"
            ),
            "quality_request_ref": record["quality_request_ref"],
            "quality_dimension": dimension,
            "quality_state": "UNASSESSED",
            "field_candidate_ref": record["field_candidate_ref"],
            "primary_key_ref": record["primary_key_ref"],
            "source_identity_ref": record["source_identity_ref"],
            "source_document_ref": record["source_document_ref"],
            "workbook_ref": record["workbook_ref"],
            "worksheet_ref": record["worksheet_ref"],
            "header_row_ref": record["header_row_ref"],
            "row_range_ref": record["row_range_ref"],
            "column_range_ref": record["column_range_ref"],
            "fact_set_ref": record["fact_set_ref"],
            "evidence_ref": record["evidence_ref"],
            "human_review_state": "REQUIRED_WHEN_UNVERIFIED",
            "statistical_conclusion_state": "BLOCKED_UNVERIFIED_REFERENCE_ONLY",
            "remediation_state": "PENDING_HUMAN_DECISION_REFERENCE_ONLY",
        }
        for dimension in QUALITY_DIMENSIONS
    ]


def _source_location_preserved(candidate: Mapping[str, object]) -> bool:
    return all(
        isinstance(candidate[field], str) and ":control:" in candidate[field]
        for field in SOURCE_LOCATION_FIELDS
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "source_identity_ref": None,
        "control_quality_input_record_count": 0,
        "actual_quality_input_record_count": 0,
        "quality_result_candidates": [],
        "quality_result_candidate_count": 0,
        "quality_dimensions_covered": [],
        "quality_dimension_count": 0,
        "quality_dimension_candidate_counts": {},
        "source_location_binding_candidate_count": 0,
        "source_location_references_preserved": False,
        "source_body_or_header_or_cell_content_retained": False,
        "all_quality_states_unassessed": True,
        "all_human_review_required": True,
        "all_statistical_conclusions_blocked": True,
        "control_quality_input_reference_validation_performed": False,
        "control_source_location_reference_validation_performed": False,
        "control_quality_result_candidate_projection_performed": False,
        "field_completeness_evaluation_performed": False,
        "unit_consistency_evaluation_performed": False,
        "date_validity_evaluation_performed": False,
        "primary_key_duplication_evaluation_performed": False,
        "outlier_evaluation_performed": False,
        "quality_gate_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
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
        "actual_structured_fact_created": False,
        "actual_quality_result_created": False,
        "actual_quality_result_persisted": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "chinese_feedback": [
            "控制输入不符合固定引用合同，已拒绝且未生成任何质量结果候选、来源引用或业务内容。"
        ],
    }
