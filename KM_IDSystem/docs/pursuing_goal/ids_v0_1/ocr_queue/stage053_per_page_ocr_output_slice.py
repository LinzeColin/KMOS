"""Stage053 P2 的纯内存按页 OCR 输出受控切片。

模块只将固定、非业务的控制页标记映射为十一字段逐页结构与可解释状态。
它不读取文件、页面或图片，不选择或调用 OCR 引擎，也不写入队列、缓存或持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


SCHEMA_VERSION = "ids.stage053.per_page_ocr_output.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_PER_PAGE_OCR_OUTPUT"
CONTROL_ADAPTER_VERSION = "ids.per_page_ocr_output.control_adapter.v0_1.stage053.p2"
SOURCE_IDENTITY_REF = "source:control:stage053-p2"
JOB_REF = "ocr-job:control:stage053-p2"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
NO_REVIEW_ROUTE = "NO_REVIEW_QUEUE_CREATED"
HIGH_TRUST_BLOCK = "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY"
CANDIDATE_ONLY = "CANDIDATE_ONLY_QUALITY_UNASSESSED"
SYMBOLIC_OUTPUT_KIND = "CONTROL_SYMBOLIC_OUTPUT_NOT_REAL_OCR_TEXT"
SYMBOLIC_IMAGE_REF_KIND = "CONTROL_SYMBOLIC_PAGE_IMAGE_REFERENCE_NOT_REAL_IMAGE"
CONTROL_FAILURE_KIND = "CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD"

OCR_INPUT_FIELDS = (
    "source_identity_ref",
    "input_kind_hint",
    "parser_output_status",
    "source_page_count_ref",
    "language_profile",
    "ocr_request_reason",
    "cache_policy_ref",
)
CONTROL_FIELDS = ("ocr_input_reference", "page_controls")
PAGE_CONTROL_FIELDS = (
    "page_number",
    "control_output_token",
    "control_page_image_token",
    "language_profile",
    "confidence_level",
    "page_outcome",
    "failure_reason",
)
ALLOWED_INPUT_KINDS = {"SCANNED_PDF", "IMAGE", "LOW_TEXT_COVERAGE_PDF"}
ALLOWED_PROFILES = {
    "SIMPLIFIED_CHINESE",
    "ENGLISH",
    "SIMPLIFIED_CHINESE_AND_ENGLISH",
    "UNKNOWN",
}
ALLOWED_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
ALLOWED_OUTCOMES = {"OCR_OUTPUT_CONTROL_READY", "OCR_PAGE_FAILED"}
ALLOWED_FAILURE_REASONS = {
    "OCR_EXECUTION_NOT_STARTED",
    "PAGE_IMAGE_REFERENCE_UNAVAILABLE",
    "OCR_ENGINE_UNAVAILABLE",
    "LOW_CONFIDENCE_REVIEW_REQUIRED",
    "MIXED_LANGUAGE_REVIEW_REQUIRED",
}
SOURCE_REF_PATTERN = re.compile(r"^source:control:stage053-p2$")
CONTROL_OUTPUT_PROFILES = {
    "CONTROL_ZH_PAGE": "SIMPLIFIED_CHINESE",
    "CONTROL_EN_LOW_CONFIDENCE_PAGE": "ENGLISH",
    "CONTROL_MIXED_ZH_EN_PAGE": "SIMPLIFIED_CHINESE_AND_ENGLISH",
}
CONTROL_PAGE_IMAGE_TOKENS = {
    1: "CONTROL_PAGE_IMAGE_REFERENCE_1",
    2: "CONTROL_PAGE_IMAGE_REFERENCE_2",
    3: "CONTROL_PAGE_IMAGE_REFERENCE_3",
}


def execute_per_page_controlled_ocr_output(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """执行受控内存切片，返回不含真实来源内容的十一字段逐页结构。"""

    accepted = _accepted_control(control_input)
    if accepted is None:
        return _rejected_result()

    reference, pages = accepted
    page_outputs = [_page_output(reference, page) for page in pages]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "job_ref": JOB_REF,
        "job_state": "COMPLETED",
        "job_state_history": ["QUEUED", "PROCESSING", "COMPLETED"],
        "source_identity_ref": reference["source_identity_ref"],
        "input_kind_hint": reference["input_kind_hint"],
        "source_page_count_ref": reference["source_page_count_ref"],
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
        "low_confidence_page_count": sum(
            item["page_state"]
            == "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in page_outputs
        ),
        "failed_page_count": sum(
            item["page_state"] == "OCR_PAGE_FAILED_EXPLICIT"
            for item in page_outputs
        ),
        "mixed_language_page_count": sum(
            item["page_state"]
            == "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED"
            for item in page_outputs
        ),
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "in_memory_queue_record_created": True,
        "in_memory_page_output_created": True,
        "source_page_reference_derived": True,
        "control_page_image_reference_derived": True,
        "control_failure_classification_created": True,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "low_confidence_state_recorded": True,
        "failed_page_state_recorded": True,
        "mixed_language_state_recorded": True,
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
        "page_image_reference_write_performed": False,
        "failure_record_write_performed": False,
        "cache_write_performed": False,
        "review_queue_write_performed": False,
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


def _accepted_control(
    control_input: Mapping[str, object] | object,
) -> tuple[dict[str, str], list[dict[str, object]]] | None:
    if not isinstance(control_input, Mapping) or set(control_input) != set(CONTROL_FIELDS):
        return None

    reference = control_input.get("ocr_input_reference")
    pages = control_input.get("page_controls")
    if not isinstance(reference, Mapping) or not isinstance(pages, Sequence) or isinstance(
        pages, (str, bytes)
    ):
        return None
    if set(reference) != set(OCR_INPUT_FIELDS) or len(pages) != 4:
        return None

    normalized = {field: reference.get(field) for field in OCR_INPUT_FIELDS}
    if not all(isinstance(value, str) for value in normalized.values()):
        return None
    if not SOURCE_REF_PATTERN.fullmatch(normalized["source_identity_ref"]):
        return None
    if normalized["input_kind_hint"] not in ALLOWED_INPUT_KINDS:
        return None
    if normalized["parser_output_status"] != "CONTROL_PER_PAGE_OCR_OUTPUT_CANDIDATE":
        return None
    if normalized["source_page_count_ref"] != "page-count:control:4":
        return None
    if normalized["language_profile"] != "SIMPLIFIED_CHINESE_AND_ENGLISH":
        return None
    if normalized["ocr_request_reason"] != "CONTROL_PER_PAGE_OUTPUT_SHAPE":
        return None
    if normalized["cache_policy_ref"] != "cache-policy:stage053-p2:in-memory":
        return None

    accepted_pages = [_accepted_page(page) for page in pages]
    if any(page is None for page in accepted_pages):
        return None
    normalized_pages = [page for page in accepted_pages if page is not None]
    if [page["page_number"] for page in normalized_pages] != [1, 2, 3, 4]:
        return None
    return normalized, normalized_pages


def _accepted_page(page: object) -> dict[str, object] | None:
    if not isinstance(page, Mapping) or set(page) != set(PAGE_CONTROL_FIELDS):
        return None

    page_number = page.get("page_number")
    control_output_token = page.get("control_output_token")
    control_page_image_token = page.get("control_page_image_token")
    language_profile = page.get("language_profile")
    confidence_level = page.get("confidence_level")
    page_outcome = page.get("page_outcome")
    failure_reason = page.get("failure_reason")
    if (
        not isinstance(page_number, int)
        or isinstance(page_number, bool)
        or page_number < 1
        or not isinstance(language_profile, str)
        or language_profile not in ALLOWED_PROFILES
        or not isinstance(confidence_level, str)
        or confidence_level not in ALLOWED_CONFIDENCE
        or not isinstance(page_outcome, str)
        or page_outcome not in ALLOWED_OUTCOMES
    ):
        return None
    if page_outcome == "OCR_PAGE_FAILED":
        if (
            control_output_token is not None
            or control_page_image_token is not None
            or language_profile != "UNKNOWN"
            or confidence_level != "UNKNOWN"
            or failure_reason != "OCR_EXECUTION_NOT_STARTED"
        ):
            return None
    elif (
        not isinstance(control_output_token, str)
        or CONTROL_OUTPUT_PROFILES.get(control_output_token) != language_profile
        or control_page_image_token != CONTROL_PAGE_IMAGE_TOKENS.get(page_number)
        or confidence_level == "UNKNOWN"
        or failure_reason is not None
    ):
        return None
    return {
        "page_number": page_number,
        "control_output_token": control_output_token,
        "control_page_image_token": control_page_image_token,
        "language_profile": language_profile,
        "confidence_level": confidence_level,
        "page_outcome": page_outcome,
        "failure_reason": failure_reason,
    }


def _page_output(
    reference: Mapping[str, str], page: Mapping[str, object]
) -> dict[str, Any]:
    page_number = page["page_number"]
    page_outcome = page["page_outcome"]
    language_profile = page["language_profile"]
    confidence_level = page["confidence_level"]
    if page_outcome == "OCR_PAGE_FAILED":
        state = "OCR_PAGE_FAILED_EXPLICIT"
        feedback_code = "OCR_PAGE_FAILURE_RECORDED"
        feedback = "控制页失败状态已明确记录，未丢弃或创建高可信证据。"
        eligibility = HIGH_TRUST_BLOCK
        review_route = REVIEW_ROUTE
        ocr_text = None
        page_image_ref = None
        failure_reason = page["failure_reason"]
    elif language_profile == "SIMPLIFIED_CHINESE_AND_ENGLISH":
        state = "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED"
        feedback_code = "OCR_MIXED_LANGUAGE_REVIEW_REQUIRED"
        feedback = "中英文混合控制页已记录，当前未创建复核任务。"
        eligibility = HIGH_TRUST_BLOCK
        review_route = REVIEW_ROUTE
        ocr_text = page["control_output_token"]
        page_image_ref = _control_page_image_ref(page_number)
        failure_reason = None
    elif confidence_level == "LOW":
        state = "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
        feedback_code = "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED"
        feedback = "英文低置信控制页需要后续复核，当前未创建复核任务。"
        eligibility = HIGH_TRUST_BLOCK
        review_route = REVIEW_ROUTE
        ocr_text = page["control_output_token"]
        page_image_ref = _control_page_image_ref(page_number)
        failure_reason = None
    else:
        state = "OCR_PAGE_CANDIDATE_RETAINED"
        feedback_code = "OCR_PAGE_CANDIDATE_RETAINED"
        feedback = "当前控制页已形成候选逐页结构，尚未进行质量评估。"
        eligibility = CANDIDATE_ONLY
        review_route = NO_REVIEW_ROUTE
        ocr_text = page["control_output_token"]
        page_image_ref = _control_page_image_ref(page_number)
        failure_reason = None
    return {
        "source_identity_ref": reference["source_identity_ref"],
        "source_page_ref": f"source-page:control:stage053-p2:{page_number}",
        "page_image_ref": page_image_ref,
        "ocr_text": ocr_text,
        "language_profile": language_profile,
        "confidence_level": confidence_level,
        "failure_reason": failure_reason,
        "output_status": page_outcome,
        "evidence_eligibility": eligibility,
        "cache_ref": None,
        "review_route": review_route,
        "page_state": state,
        "quality_state": "UNASSESSED",
        "text_output_kind": SYMBOLIC_OUTPUT_KIND if ocr_text is not None else "NO_OUTPUT",
        "page_image_reference_kind": (
            SYMBOLIC_IMAGE_REF_KIND if page_image_ref is not None else "NO_IMAGE_REFERENCE"
        ),
        "failure_reason_kind": (
            CONTROL_FAILURE_KIND if failure_reason is not None else "NO_FAILURE_REASON"
        ),
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "human_feedback_code": feedback_code,
        "human_feedback": feedback,
        "high_trust_direct_entry_allowed": False,
        "review_queue_record_created": False,
    }


def _control_page_image_ref(page_number: object) -> str:
    return f"page-image-ref:control:stage053-p2:{page_number}"


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "job_ref": None,
        "job_state": "REJECTED",
        "job_state_history": ["REJECTED"],
        "source_identity_ref": None,
        "input_kind_hint": None,
        "source_page_count_ref": None,
        "page_outputs": [],
        "page_output_count": 0,
        "symbolic_control_output_count": 0,
        "symbolic_control_page_image_reference_count": 0,
        "control_failure_reason_count": 0,
        "low_confidence_page_count": 0,
        "failed_page_count": 0,
        "mixed_language_page_count": 0,
        "cache_policy": CACHE_POLICY,
        "cache_created": False,
        "cache_ref": None,
        "in_memory_queue_record_created": False,
        "in_memory_page_output_created": False,
        "source_page_reference_derived": False,
        "control_page_image_reference_derived": False,
        "control_failure_classification_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "low_confidence_state_recorded": False,
        "failed_page_state_recorded": False,
        "mixed_language_state_recorded": False,
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
        "page_image_reference_write_performed": False,
        "failure_record_write_performed": False,
        "cache_write_performed": False,
        "review_queue_write_performed": False,
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
