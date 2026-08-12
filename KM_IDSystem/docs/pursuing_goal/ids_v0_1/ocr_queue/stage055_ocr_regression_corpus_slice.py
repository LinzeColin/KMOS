"""Stage055 P2 的纯内存 OCR 回归语料受控切片。

模块只将五条固定、非业务的 reference-only 控制记录投影为内存队列状态、
十一字段逐页结构、置信度记录与可解释处置。它不读取样本、页面或图片，
不选择或调用 OCR 引擎，也不写入队列、缓存或其他持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage055.ocr_regression_corpus.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_OCR_REGRESSION_CORPUS"
CONTROL_ADAPTER_VERSION = "ids.ocr_regression_corpus.control_adapter.v0_1.stage055.p2"
SOURCE_IDENTITY_REF = "source:control:stage055-p2"
QUEUE_REF = "ocr-regression-queue:control:stage055-p2"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
CACHE_POLICY_REF = "cache-policy:stage055-p2:in-memory"
HIGH_TRUST_BLOCK = "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY"
CANDIDATE_ONLY = "CANDIDATE_ONLY_QUALITY_UNASSESSED"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
NO_REVIEW_ROUTE = "NO_REVIEW_QUEUE_CREATED"
SYMBOLIC_OUTPUT_KIND = "CONTROL_SYMBOLIC_OUTPUT_NOT_REAL_OCR_TEXT"
SYMBOLIC_IMAGE_REF_KIND = "CONTROL_SYMBOLIC_PAGE_IMAGE_REFERENCE_NOT_REAL_IMAGE"
CONTROL_FAILURE_KIND = "CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD"

CONTROL_FIELDS = ("regression_input_records",)
REGRESSION_INPUT_FIELDS = (
    "source_identity_ref",
    "source_page_ref",
    "input_class",
    "language_profile",
    "confidence_level",
    "output_status",
    "failure_reason",
    "evidence_eligibility",
    "review_route",
    "cache_policy_ref",
)
PER_PAGE_OUTPUT_FIELDS = (
    "source_identity_ref",
    "source_page_ref",
    "page_image_ref",
    "ocr_text",
    "language_profile",
    "confidence_level",
    "failure_reason",
    "output_status",
    "evidence_eligibility",
    "cache_ref",
    "review_route",
)

CONTROL_RECORD_EXPECTATIONS = {
    "source-page:control:stage055-p2:1": {
        "input_class": "SCANNED_DOCUMENT_CONTROL",
        "language_profile": "SIMPLIFIED_CHINESE",
        "confidence_level": "HIGH",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": CANDIDATE_ONLY,
        "review_route": NO_REVIEW_ROUTE,
    },
    "source-page:control:stage055-p2:2": {
        "input_class": "BLURRED_DOCUMENT_CONTROL",
        "language_profile": "SIMPLIFIED_CHINESE",
        "confidence_level": "LOW",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
    "source-page:control:stage055-p2:3": {
        "input_class": "TABLE_DOCUMENT_CONTROL",
        "language_profile": "SIMPLIFIED_CHINESE",
        "confidence_level": "MEDIUM",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": CANDIDATE_ONLY,
        "review_route": NO_REVIEW_ROUTE,
    },
    "source-page:control:stage055-p2:4": {
        "input_class": "MIXED_ZH_EN_DOCUMENT_CONTROL",
        "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "confidence_level": "MEDIUM",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
    "source-page:control:stage055-p2:5": {
        "input_class": "LOW_QUALITY_DOCUMENT_CONTROL",
        "language_profile": "UNKNOWN",
        "confidence_level": "UNKNOWN",
        "output_status": "OCR_PAGE_FAILED",
        "failure_reason": "OCR_EXECUTION_NOT_STARTED",
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
}
CONTROL_OUTPUT_TOKENS = {
    "SCANNED_DOCUMENT_CONTROL": "CONTROL_SCANNED_DOCUMENT_OUTPUT",
    "BLURRED_DOCUMENT_CONTROL": "CONTROL_BLURRED_DOCUMENT_OUTPUT",
    "TABLE_DOCUMENT_CONTROL": "CONTROL_TABLE_DOCUMENT_OUTPUT",
    "MIXED_ZH_EN_DOCUMENT_CONTROL": "CONTROL_MIXED_ZH_EN_DOCUMENT_OUTPUT",
}


def execute_ocr_regression_corpus_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """执行五类固定 control 的纯内存队列和按页输出投影。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    page_outputs = [_page_output(record) for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "queue_ref": QUEUE_REF,
        "queue_state": "COMPLETED",
        "queue_state_history": ["QUEUED", "PROCESSING", "COMPLETED"],
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "queue_record": {
            "source_identity_ref": SOURCE_IDENTITY_REF,
            "input_record_count": len(records),
            "input_classes": [record["input_class"] for record in records],
            "record_kind": "CONTROL_REFERENCE_ONLY_NOT_REAL_OCR_INPUT",
        },
        "page_outputs": page_outputs,
        "page_output_count": len(page_outputs),
        "symbolic_control_output_count": sum(
            item["ocr_text"] is not None for item in page_outputs
        ),
        "symbolic_control_page_image_reference_count": sum(
            item["page_image_ref"] is not None for item in page_outputs
        ),
        "control_failure_reason_count": sum(
            item["failure_reason"] is not None for item in page_outputs
        ),
        "candidate_page_count": sum(
            item["page_state"]
            in {
                "OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED",
                "OCR_TABLE_DOCUMENT_CANDIDATE_UNASSESSED",
            }
            for item in page_outputs
        ),
        "low_confidence_page_count": sum(
            item["page_state"] == "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in page_outputs
        ),
        "mixed_language_page_count": sum(
            item["page_state"]
            == "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED"
            for item in page_outputs
        ),
        "failed_page_count": sum(
            item["page_state"] == "OCR_PAGE_FAILED_EXPLICIT" for item in page_outputs
        ),
        "source_page_reference_preserved": True,
        "in_memory_ocr_regression_queue_record_created": True,
        "in_memory_per_page_output_created": True,
        "in_memory_confidence_record_created": True,
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "actual_ocr_queue_created": False,
        "actual_page_output_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "table_structure_extraction_performed": False,
        "language_detection_performed": False,
        "confidence_evaluation_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "ocr_engine_comparison_performed": False,
        "regression_execution_performed": False,
        "recognition_accuracy_evaluated": False,
        "persistent_queue_write_performed": False,
        "persistent_page_output_write_performed": False,
        "page_image_reference_write_performed": False,
        "failure_record_write_performed": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "review_queue_write_performed": False,
        "human_review_task_created": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "manifest_write_performed": False,
        "evidence_ledger_write_performed": False,
        "audit_write_performed": False,
        "report_write_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
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
    records = control_input.get("regression_input_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != len(CONTROL_RECORD_EXPECTATIONS):
        return None

    accepted = [_accepted_control_record(record) for record in records]
    if any(record is None for record in accepted):
        return None
    normalized = [record for record in accepted if record is not None]
    if [record["source_page_ref"] for record in normalized] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return normalized


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(REGRESSION_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in REGRESSION_INPUT_FIELDS}
    source_identity_ref = normalized["source_identity_ref"]
    source_page_ref = normalized["source_page_ref"]
    if (
        source_identity_ref != SOURCE_IDENTITY_REF
        or not isinstance(source_page_ref, str)
        or normalized["cache_policy_ref"] != CACHE_POLICY_REF
    ):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_page_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _page_output(record: Mapping[str, object]) -> dict[str, Any]:
    input_class = record["input_class"]
    failed = record["output_status"] == "OCR_PAGE_FAILED"
    if failed:
        page_image_ref = None
        ocr_text = None
        page_state = "OCR_PAGE_FAILED_EXPLICIT"
        feedback_code = "OCR_REGRESSION_FAILED_PAGE_RECORDED"
        feedback = "低质量控制页已记录为显式失败，未创建真实失败记录或复核任务。"
    else:
        page_image_ref = _symbolic_page_image_ref(record["source_page_ref"])
        ocr_text = CONTROL_OUTPUT_TOKENS[input_class]
        page_state, feedback_code, feedback = _ready_page_state(record)

    return {
        "source_identity_ref": record["source_identity_ref"],
        "source_page_ref": record["source_page_ref"],
        "page_image_ref": page_image_ref,
        "ocr_text": ocr_text,
        "language_profile": record["language_profile"],
        "confidence_level": record["confidence_level"],
        "failure_reason": record["failure_reason"],
        "output_status": record["output_status"],
        "evidence_eligibility": record["evidence_eligibility"],
        "cache_ref": None,
        "review_route": record["review_route"],
        "regression_category": input_class,
        "page_state": page_state,
        "quality_state": "UNASSESSED",
        "source_page_reference_preserved": True,
        "text_output_kind": (
            SYMBOLIC_OUTPUT_KIND if ocr_text is not None else "NO_OUTPUT"
        ),
        "page_image_reference_kind": (
            SYMBOLIC_IMAGE_REF_KIND
            if page_image_ref is not None
            else "NO_IMAGE_REFERENCE"
        ),
        "failure_reason_kind": (
            CONTROL_FAILURE_KIND
            if record["failure_reason"] is not None
            else "NO_FAILURE_REASON"
        ),
        "high_trust_direct_entry_allowed": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "human_feedback_code": feedback_code,
        "human_feedback": feedback,
    }


def _ready_page_state(record: Mapping[str, object]) -> tuple[str, str, str]:
    if record["input_class"] == "TABLE_DOCUMENT_CONTROL":
        return (
            "OCR_TABLE_DOCUMENT_CANDIDATE_UNASSESSED",
            "OCR_REGRESSION_TABLE_CANDIDATE_RETAINED",
            "表格控制页已形成候选逐页结构，未执行表格结构提取或质量评估。",
        )
    if record["language_profile"] == "SIMPLIFIED_CHINESE_AND_ENGLISH":
        return (
            "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED",
            "OCR_REGRESSION_MIXED_LANGUAGE_REVIEW_REQUIRED",
            "中英文混合控制页已记录为受控复核状态，未创建复核任务。",
        )
    if record["confidence_level"] == "LOW":
        return (
            "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            "OCR_REGRESSION_LOW_CONFIDENCE_REVIEW_REQUIRED",
            "模糊控制页以低置信状态保留，未创建复核任务。",
        )
    return (
        "OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED",
        "OCR_REGRESSION_CANDIDATE_RETAINED",
        "扫描件控制页已形成候选逐页结构，未执行 OCR 或质量评估。",
    )


def _symbolic_page_image_ref(source_page_ref: object) -> str:
    page_number = str(source_page_ref).rsplit(":", maxsplit=1)[-1]
    return f"page-image-ref:control:stage055-p2:{page_number}"


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "queue_ref": None,
        "queue_state": "REJECTED",
        "queue_state_history": ["REJECTED"],
        "source_identity_ref": None,
        "queue_record": None,
        "page_outputs": [],
        "page_output_count": 0,
        "symbolic_control_output_count": 0,
        "symbolic_control_page_image_reference_count": 0,
        "control_failure_reason_count": 0,
        "candidate_page_count": 0,
        "low_confidence_page_count": 0,
        "mixed_language_page_count": 0,
        "failed_page_count": 0,
        "source_page_reference_preserved": False,
        "in_memory_ocr_regression_queue_record_created": False,
        "in_memory_per_page_output_created": False,
        "in_memory_confidence_record_created": False,
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "actual_ocr_queue_created": False,
        "actual_page_output_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "table_structure_extraction_performed": False,
        "language_detection_performed": False,
        "confidence_evaluation_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "ocr_engine_comparison_performed": False,
        "regression_execution_performed": False,
        "recognition_accuracy_evaluated": False,
        "persistent_queue_write_performed": False,
        "persistent_page_output_write_performed": False,
        "page_image_reference_write_performed": False,
        "failure_record_write_performed": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "review_queue_write_performed": False,
        "human_review_task_created": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "manifest_write_performed": False,
        "evidence_ledger_write_performed": False,
        "audit_write_performed": False,
        "report_write_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }
