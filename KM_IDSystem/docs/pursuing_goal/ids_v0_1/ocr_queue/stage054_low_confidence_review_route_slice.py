"""Stage054 P2 的纯内存低置信度复核路由受控切片。

模块只处理四条固定、非业务的 reference-only 控制记录，形成候选复核请求与可解释路由状态。
它不读取文件、页面、图片或 OCR 文本，不创建持久队列、人工任务、缓存或运行状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


SCHEMA_VERSION = "ids.stage054.low_confidence_review_route.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_LOW_CONFIDENCE_REVIEW_ROUTE"
CONTROL_ADAPTER_VERSION = "ids.low_confidence_review_route.control_adapter.v0_1.stage054.p2"
CONTROL_SOURCE_IDENTITY_REF = "source:control:stage054-p2"
ROUTE_BATCH_REF = "review-route-batch:control:stage054-p2"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
CACHE_POLICY_REF = "cache-policy:stage054-p2:in-memory"
HIGH_TRUST_BLOCK = "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY"
CANDIDATE_ONLY = "CANDIDATE_ONLY_QUALITY_UNASSESSED"
CONTROL_RECORD_KIND = "CONTROL_REFERENCE_ONLY_NOT_REAL_OCR_OUTPUT"
CONTROL_FAILURE_KIND = "CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD"

CONTROL_FIELDS = ("review_input_records",)
REVIEW_INPUT_FIELDS = (
    "source_identity_ref",
    "source_page_ref",
    "language_profile",
    "confidence_level",
    "output_status",
    "failure_reason",
    "evidence_eligibility",
    "review_route",
    "cache_policy_ref",
)
REVIEW_REQUEST_FIELDS = REVIEW_INPUT_FIELDS + ("feedback_code",)
SOURCE_IDENTITY_PATTERN = re.compile(r"^source:control:stage054-p2$")
SOURCE_PAGE_PATTERN = re.compile(r"^source-page:control:stage054-p2:[1-4]$")

CONTROL_RECORD_EXPECTATIONS = {
    "source-page:control:stage054-p2:1": {
        "language_profile": "ENGLISH",
        "confidence_level": "LOW",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
    },
    "source-page:control:stage054-p2:2": {
        "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "confidence_level": "MEDIUM",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
    },
    "source-page:control:stage054-p2:3": {
        "language_profile": "UNKNOWN",
        "confidence_level": "UNKNOWN",
        "output_status": "OCR_PAGE_FAILED",
        "failure_reason": "OCR_EXECUTION_NOT_STARTED",
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
    },
    "source-page:control:stage054-p2:4": {
        "language_profile": "SIMPLIFIED_CHINESE",
        "confidence_level": "HIGH",
        "output_status": "OCR_OUTPUT_CONTROL_READY",
        "failure_reason": None,
        "evidence_eligibility": CANDIDATE_ONLY,
        "review_route": "NO_REVIEW_QUEUE_CREATED",
    },
}


def route_low_confidence_controlled_reviews(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """返回不含业务内容的低置信度复核路由控制结果。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    route_results = [_route_control_record(record) for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "route_batch_ref": ROUTE_BATCH_REF,
        "route_state": "COMPLETED",
        "route_state_history": ["RECEIVED", "CLASSIFIED", "ROUTE_DECIDED"],
        "source_identity_ref": CONTROL_SOURCE_IDENTITY_REF,
        "route_results": route_results,
        "route_result_count": len(route_results),
        "review_request_candidate_count": sum(
            item["review_request_candidate"] is not None for item in route_results
        ),
        "low_confidence_route_count": sum(
            item["route_state"] == "LOW_CONFIDENCE_REVIEW_REQUIRED"
            for item in route_results
        ),
        "mixed_language_route_count": sum(
            item["route_state"] == "MIXED_LANGUAGE_REVIEW_REQUIRED"
            for item in route_results
        ),
        "failed_page_route_count": sum(
            item["route_state"] == "FAILED_PAGE_REVIEW_REQUIRED"
            for item in route_results
        ),
        "no_review_route_required_count": sum(
            item["route_state"] is None for item in route_results
        ),
        "source_page_reference_preserved": True,
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "in_memory_controlled_route_result_created": True,
        "in_memory_review_request_candidate_created": True,
        "actual_review_request_created": False,
        "actual_review_request_persisted": False,
        "review_queue_record_created": False,
        "human_review_task_created": False,
        "human_review_result_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "language_detection_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "persistent_queue_write_performed": False,
        "persistent_page_output_write_performed": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "audit_write_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }


def _accepted_control_records(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, object]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None
    records = control_input.get("review_input_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return None
    if len(records) != 4:
        return None

    normalized = [_accepted_control_record(record) for record in records]
    if any(record is None for record in normalized):
        return None
    accepted = [record for record in normalized if record is not None]
    if [record["source_page_ref"] for record in accepted] != list(
        CONTROL_RECORD_EXPECTATIONS
    ):
        return None
    return accepted


def _accepted_control_record(record: object) -> dict[str, object] | None:
    if not isinstance(record, Mapping) or set(record) != set(REVIEW_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in REVIEW_INPUT_FIELDS}
    source_identity_ref = normalized["source_identity_ref"]
    source_page_ref = normalized["source_page_ref"]
    if (
        not isinstance(source_identity_ref, str)
        or not SOURCE_IDENTITY_PATTERN.fullmatch(source_identity_ref)
        or not isinstance(source_page_ref, str)
        or not SOURCE_PAGE_PATTERN.fullmatch(source_page_ref)
        or normalized["cache_policy_ref"] != CACHE_POLICY_REF
    ):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_page_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _route_control_record(record: Mapping[str, object]) -> dict[str, Any]:
    route_state, feedback_code, feedback = _route_decision(record)
    candidate = (
        _review_request_candidate(record, feedback_code)
        if route_state is not None
        else None
    )
    return {
        "source_identity_ref": record["source_identity_ref"],
        "source_page_ref": record["source_page_ref"],
        "route_state": route_state,
        "review_request_candidate": candidate,
        "review_request_candidate_created_in_memory": candidate is not None,
        "source_page_reference_preserved": True,
        "control_record_kind": CONTROL_RECORD_KIND,
        "failure_reason_kind": (
            CONTROL_FAILURE_KIND
            if record["failure_reason"] is not None
            else "NO_FAILURE_REASON"
        ),
        "initial_fact_level": "CANDIDATE",
        "quality_state": "UNASSESSED",
        "high_trust_direct_entry_allowed": False,
        "actual_review_request_created": False,
        "review_queue_record_created": False,
        "human_review_task_created": False,
        "human_review_result_created": False,
        "human_feedback_code": feedback_code,
        "human_feedback": feedback,
    }


def _route_decision(record: Mapping[str, object]) -> tuple[str | None, str, str]:
    if record["output_status"] == "OCR_PAGE_FAILED":
        return (
            "FAILED_PAGE_REVIEW_REQUIRED",
            "FAILED_PAGE_REVIEW_REQUIRED",
            "失败控制页已形成候选复核请求，未创建人工任务。",
        )
    if record["language_profile"] == "SIMPLIFIED_CHINESE_AND_ENGLISH":
        return (
            "MIXED_LANGUAGE_REVIEW_REQUIRED",
            "MIXED_LANGUAGE_REVIEW_REQUIRED",
            "中英文混合控制页已形成候选复核请求，未创建人工任务。",
        )
    if record["confidence_level"] in {"LOW", "UNKNOWN"}:
        return (
            "LOW_CONFIDENCE_REVIEW_REQUIRED",
            "LOW_CONFIDENCE_REVIEW_REQUIRED",
            "英文低置信控制页已形成候选复核请求，未创建人工任务。",
        )
    return (
        None,
        "NO_REVIEW_ROUTE_REQUIRED",
        "当前控制页无需复核路由，仍未进行质量评估或高可信证据提升。",
    )


def _review_request_candidate(
    record: Mapping[str, object], feedback_code: str
) -> dict[str, object]:
    return {
        **{field: record[field] for field in REVIEW_INPUT_FIELDS},
        "feedback_code": feedback_code,
    }


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "route_batch_ref": None,
        "route_state": "REJECTED",
        "route_state_history": ["REJECTED"],
        "source_identity_ref": None,
        "route_results": [],
        "route_result_count": 0,
        "review_request_candidate_count": 0,
        "low_confidence_route_count": 0,
        "mixed_language_route_count": 0,
        "failed_page_route_count": 0,
        "no_review_route_required_count": 0,
        "source_page_reference_preserved": False,
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "in_memory_controlled_route_result_created": False,
        "in_memory_review_request_candidate_created": False,
        "actual_review_request_created": False,
        "actual_review_request_persisted": False,
        "review_queue_record_created": False,
        "human_review_task_created": False,
        "human_review_result_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "language_detection_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "persistent_queue_write_performed": False,
        "persistent_page_output_write_performed": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "audit_write_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }
