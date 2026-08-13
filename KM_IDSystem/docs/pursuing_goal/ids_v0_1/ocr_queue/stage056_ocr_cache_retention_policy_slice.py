"""Stage056 P2 的纯内存 OCR 缓存保留策略受控切片。

模块只将四条固定、非业务、reference-only control 投影为缓存保留策略候选。
它不读取来源、页面、图片、文本或缓存，不调用 OCR，也不创建物理缓存、清理、
队列、人工任务或其他持久状态。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "ids.stage056.ocr_cache_retention_policy.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_OCR_CACHE_RETENTION_POLICY"
CONTROL_ADAPTER_VERSION = "ids.ocr_cache_retention_policy.control_adapter.v0_1.stage056.p2"
SOURCE_IDENTITY_REF = "source:control:stage056-p2"
CACHE_STATE = "CANDIDATE_NOT_PERSISTED"
HIGH_TRUST_BLOCK = "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
NO_REVIEW_ROUTE = "NO_REVIEW_QUEUE_CREATED"
TEMPORARY_RETENTION = "FUTURE_REBUILDABLE_TEMPORARY"
FAILURE_RETENTION = "FUTURE_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP"
TEMPORARY_CLEANUP = (
    "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED"
)
FAILURE_CLEANUP = "NOT_ELIGIBLE_FOR_AUTOMATIC_CLEANUP"

CONTROL_FIELDS = ("cache_policy_input_records",)
CACHE_POLICY_INPUT_FIELDS = (
    "cache_entry_ref",
    "source_identity_ref",
    "source_page_ref",
    "artifact_class",
    "language_profile",
    "confidence_level",
    "cache_state",
    "retention_class",
    "cleanup_eligibility",
    "evidence_eligibility",
    "review_route",
)
CACHE_POLICY_OUTPUT_FIELDS = (
    "cache_entry_ref",
    "artifact_class",
    "retention_class",
    "cleanup_eligibility",
    "rebuildability",
    "source_identity_ref",
    "source_page_ref",
    "language_profile",
    "confidence_level",
    "review_route",
)

CONTROL_RECORD_EXPECTATIONS = {
    "source-page:control:stage056-p2:1": {
        "cache_entry_ref": "cache-entry:control:stage056-p2:1",
        "artifact_class": "TEMPORARY_PAGE_IMAGE",
        "language_profile": "SIMPLIFIED_CHINESE",
        "confidence_level": "HIGH",
        "cache_state": CACHE_STATE,
        "retention_class": TEMPORARY_RETENTION,
        "cleanup_eligibility": TEMPORARY_CLEANUP,
        "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
        "review_route": NO_REVIEW_ROUTE,
    },
    "source-page:control:stage056-p2:2": {
        "cache_entry_ref": "cache-entry:control:stage056-p2:2",
        "artifact_class": "INTERMEDIATE_OCR_TEXT",
        "language_profile": "ENGLISH",
        "confidence_level": "LOW",
        "cache_state": CACHE_STATE,
        "retention_class": TEMPORARY_RETENTION,
        "cleanup_eligibility": TEMPORARY_CLEANUP,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
    "source-page:control:stage056-p2:3": {
        "cache_entry_ref": "cache-entry:control:stage056-p2:3",
        "artifact_class": "INTERMEDIATE_OCR_TEXT",
        "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "confidence_level": "MEDIUM",
        "cache_state": CACHE_STATE,
        "retention_class": TEMPORARY_RETENTION,
        "cleanup_eligibility": TEMPORARY_CLEANUP,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
    "source-page:control:stage056-p2:4": {
        "cache_entry_ref": "cache-entry:control:stage056-p2:4",
        "artifact_class": "FAILURE_ARTIFACT",
        "language_profile": "UNKNOWN",
        "confidence_level": "UNKNOWN",
        "cache_state": CACHE_STATE,
        "retention_class": FAILURE_RETENTION,
        "cleanup_eligibility": FAILURE_CLEANUP,
        "evidence_eligibility": HIGH_TRUST_BLOCK,
        "review_route": REVIEW_ROUTE,
    },
}


def execute_ocr_cache_retention_policy_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """投影固定 control 的内存缓存保留策略候选，绝不写入缓存。"""

    records = _accepted_control_records(control_input)
    if records is None:
        return _rejected_result()

    candidates = [_policy_candidate(record) for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_CONTROL_SLICE",
        "source_identity_ref": SOURCE_IDENTITY_REF,
        "cache_policy_input_record_count": len(records),
        "candidate_policy_outputs": candidates,
        "cache_policy_candidate_count": len(candidates),
        "temporary_artifact_policy_candidate_count": sum(
            item["artifact_class"] != "FAILURE_ARTIFACT" for item in candidates
        ),
        "failure_artifact_policy_candidate_count": sum(
            item["artifact_class"] == "FAILURE_ARTIFACT" for item in candidates
        ),
        "low_confidence_policy_candidate_count": sum(
            item["policy_state"]
            == "LOW_CONFIDENCE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in candidates
        ),
        "mixed_language_policy_candidate_count": sum(
            item["policy_state"]
            == "MIXED_LANGUAGE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in candidates
        ),
        "failed_page_policy_candidate_count": sum(
            item["policy_state"]
            == "FAILURE_ARTIFACT_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP"
            for item in candidates
        ),
        "source_page_reference_preserved": all(
            item["source_page_reference_preserved"] for item in candidates
        ),
        "in_memory_candidate_policy_output_created": True,
        "actual_cache_decision_created": False,
        "actual_cache_decision_persisted": False,
        "cache_created": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "physical_storage_path_created": False,
        "artifact_content_retained": False,
        "cleanup_action_created": False,
        "disk_scan_performed": False,
        "cache_capacity_evaluation_performed": False,
        "source_file_open_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "language_detection_performed": False,
        "confidence_evaluation_performed": False,
        "actual_ocr_queue_created": False,
        "actual_page_output_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "review_queue_created": False,
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
    records = control_input.get("cache_policy_input_records")
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
    if not isinstance(record, Mapping) or set(record) != set(CACHE_POLICY_INPUT_FIELDS):
        return None
    normalized = {field: record.get(field) for field in CACHE_POLICY_INPUT_FIELDS}
    source_page_ref = normalized["source_page_ref"]
    if (
        normalized["source_identity_ref"] != SOURCE_IDENTITY_REF
        or not isinstance(source_page_ref, str)
    ):
        return None
    expectation = CONTROL_RECORD_EXPECTATIONS.get(source_page_ref)
    if expectation is None:
        return None
    if any(normalized[field] != value for field, value in expectation.items()):
        return None
    return normalized


def _policy_candidate(record: Mapping[str, object]) -> dict[str, Any]:
    policy_state, feedback_code, feedback = _policy_state(record)
    artifact_class = record["artifact_class"]
    return {
        "cache_entry_ref": record["cache_entry_ref"],
        "artifact_class": artifact_class,
        "retention_class": record["retention_class"],
        "cleanup_eligibility": record["cleanup_eligibility"],
        "rebuildability": _rebuildability(artifact_class),
        "source_identity_ref": record["source_identity_ref"],
        "source_page_ref": record["source_page_ref"],
        "language_profile": record["language_profile"],
        "confidence_level": record["confidence_level"],
        "review_route": record["review_route"],
        "cache_state": record["cache_state"],
        "policy_state": policy_state,
        "quality_state": "UNASSESSED",
        "evidence_eligibility": record["evidence_eligibility"],
        "source_page_reference_preserved": True,
        "cache_entry_reference_kind": "CONTROL_REFERENCE_NOT_PHYSICAL_CACHE_ENTRY",
        "high_trust_direct_entry_allowed": False,
        "actual_cache_decision_created": False,
        "actual_cache_decision_persisted": False,
        "physical_storage_path_created": False,
        "artifact_content_retained": False,
        "cleanup_action_created": False,
        "human_feedback_code": feedback_code,
        "human_feedback": feedback,
    }


def _rebuildability(artifact_class: object) -> str:
    if artifact_class == "FAILURE_ARTIFACT":
        return "REVIEW_REQUIRED_NO_AUTOMATIC_REBUILD"
    return "REBUILDABLE_TEMPORARY_IF_FUTURE_WRITE_AUTHORIZED"


def _policy_state(record: Mapping[str, object]) -> tuple[str, str, str]:
    if record["artifact_class"] == "FAILURE_ARTIFACT":
        return (
            "FAILURE_ARTIFACT_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
            "OCR_CACHE_FAILURE_NO_AUTOMATIC_CLEANUP",
            "失败产物控制候选需要复核且不得自动清理；未创建失败记录、缓存或复核任务。",
        )
    if record["language_profile"] == "SIMPLIFIED_CHINESE_AND_ENGLISH":
        return (
            "MIXED_LANGUAGE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
            "OCR_CACHE_MIXED_LANGUAGE_REVIEW_REQUIRED",
            "中英文混合控制候选已标记为需复核且未排队，不能直接进入高可信证据层。",
        )
    if record["confidence_level"] == "LOW":
        return (
            "LOW_CONFIDENCE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
            "OCR_CACHE_LOW_CONFIDENCE_REVIEW_REQUIRED",
            "低置信控制候选已标记为需复核且未排队，不能直接进入高可信证据层。",
        )
    return (
        "TEMPORARY_CACHE_POLICY_CANDIDATE_OWNER_AND_CAPACITY_REQUIRED",
        "OCR_CACHE_TEMPORARY_OWNER_CAPACITY_REQUIRED",
        "可重建临时产物仅形成未来保留候选，仍需 owner 保留批准与容量批准。",
    )


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED",
        "source_identity_ref": None,
        "cache_policy_input_record_count": 0,
        "candidate_policy_outputs": [],
        "cache_policy_candidate_count": 0,
        "temporary_artifact_policy_candidate_count": 0,
        "failure_artifact_policy_candidate_count": 0,
        "low_confidence_policy_candidate_count": 0,
        "mixed_language_policy_candidate_count": 0,
        "failed_page_policy_candidate_count": 0,
        "source_page_reference_preserved": False,
        "in_memory_candidate_policy_output_created": False,
        "actual_cache_decision_created": False,
        "actual_cache_decision_persisted": False,
        "cache_created": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "physical_storage_path_created": False,
        "artifact_content_retained": False,
        "cleanup_action_created": False,
        "disk_scan_performed": False,
        "cache_capacity_evaluation_performed": False,
        "source_file_open_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_configuration_performed": False,
        "ocr_engine_invocation_performed": False,
        "language_detection_performed": False,
        "confidence_evaluation_performed": False,
        "actual_ocr_queue_created": False,
        "actual_page_output_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "review_queue_created": False,
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
