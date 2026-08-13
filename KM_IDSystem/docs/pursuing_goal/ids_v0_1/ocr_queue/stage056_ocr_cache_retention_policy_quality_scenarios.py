"""Stage056 P3 的 OCR 缓存保留策略受控专项场景。

模块只重放 Stage056 P2 的四条固定、非业务、reference-only 缓存策略候选。
扫描 PDF、模糊图片、表格图片、中英文混合和低质量在这里均为场景类别标签，
不是文件、图像、页面、OCR 结果或磁盘对象。模块不读取样本、不调用 OCR、
不扫描磁盘，也不创建、写入或清理任何物理缓存。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage056.ocr_cache_retention_policy.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_OCR_CACHE_RETENTION_POLICY_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE056-P4-GATE"
SOURCE_IDENTITY_REF = "source:control:stage056-p2"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
NO_REVIEW_ROUTE = "NO_REVIEW_QUEUE_CREATED"
TEMPORARY_CLEANUP = (
    "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED"
)
FAILURE_CLEANUP = "NOT_ELIGIBLE_FOR_AUTOMATIC_CLEANUP"

SIDE_EFFECT_FIELDS = (
    "actual_cache_decision_created",
    "actual_cache_decision_persisted",
    "cache_created",
    "cache_write_performed",
    "cache_cleanup_performed",
    "physical_storage_path_created",
    "artifact_content_retained",
    "cleanup_action_created",
    "disk_scan_performed",
    "cache_capacity_evaluation_performed",
    "source_file_open_performed",
    "ocr_engine_selected",
    "ocr_engine_configuration_performed",
    "ocr_engine_invocation_performed",
    "language_detection_performed",
    "confidence_evaluation_performed",
    "actual_ocr_queue_created",
    "actual_page_output_created",
    "actual_ocr_text_created",
    "actual_page_image_reference_created",
    "actual_failure_record_created",
    "review_queue_created",
    "human_review_task_created",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "report_write_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

REQUIRED_SCENARIO_CATEGORIES = {
    "SCANNED_PDF_CONTROL",
    "BLURRED_IMAGE_CONTROL",
    "TABLE_IMAGE_CONTROL",
    "MIXED_ZH_EN_CONTROL",
    "LOW_QUALITY_CONTROL",
}

SCENARIOS = (
    {
        "scenario_id": "scanned-pdf-cache-policy-control-candidate",
        "scenario_category": "SCANNED_PDF_CONTROL",
        "policy_candidate_ref": "source-page:control:stage056-p2:1",
        "expected_artifact_class": "TEMPORARY_PAGE_IMAGE",
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "HIGH",
        "expected_policy_state": "TEMPORARY_CACHE_POLICY_CANDIDATE_OWNER_AND_CAPACITY_REQUIRED",
        "expected_disposition": "CANDIDATE_RETAINED_NOT_REAL_OCR_QUALITY_UNASSESSED",
        "expected_review_route": NO_REVIEW_ROUTE,
    },
    {
        "scenario_id": "blurred-image-cache-policy-control-degraded",
        "scenario_category": "BLURRED_IMAGE_CONTROL",
        "policy_candidate_ref": "source-page:control:stage056-p2:2",
        "expected_artifact_class": "INTERMEDIATE_OCR_TEXT",
        "expected_language_profile": "ENGLISH",
        "expected_confidence_level": "LOW",
        "expected_policy_state": "LOW_CONFIDENCE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_disposition": "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_review_route": REVIEW_ROUTE,
    },
    {
        "scenario_id": "table-image-cache-policy-control-unassessed",
        "scenario_category": "TABLE_IMAGE_CONTROL",
        "policy_candidate_ref": "source-page:control:stage056-p2:1",
        "expected_artifact_class": "TEMPORARY_PAGE_IMAGE",
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "HIGH",
        "expected_policy_state": "TEMPORARY_CACHE_POLICY_CANDIDATE_OWNER_AND_CAPACITY_REQUIRED",
        "expected_disposition": "CANDIDATE_RETAINED_TABLE_EXTRACTION_UNASSESSED",
        "expected_review_route": NO_REVIEW_ROUTE,
    },
    {
        "scenario_id": "mixed-zh-en-cache-policy-control-degraded",
        "scenario_category": "MIXED_ZH_EN_CONTROL",
        "policy_candidate_ref": "source-page:control:stage056-p2:3",
        "expected_artifact_class": "INTERMEDIATE_OCR_TEXT",
        "expected_language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "expected_confidence_level": "MEDIUM",
        "expected_policy_state": "MIXED_LANGUAGE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_disposition": "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_review_route": REVIEW_ROUTE,
    },
    {
        "scenario_id": "low-quality-cache-policy-control-failed",
        "scenario_category": "LOW_QUALITY_CONTROL",
        "policy_candidate_ref": "source-page:control:stage056-p2:4",
        "expected_artifact_class": "FAILURE_ARTIFACT",
        "expected_language_profile": "UNKNOWN",
        "expected_confidence_level": "UNKNOWN",
        "expected_policy_state": "FAILURE_ARTIFACT_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
        "expected_disposition": "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION",
        "expected_review_route": REVIEW_ROUTE,
    },
)

PolicyExecutor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_ocr_cache_retention_policy_phase3_report(
    policy_executor: PolicyExecutor | None = None,
) -> dict[str, Any]:
    """重放 P2 固定候选并返回不含样本、OCR 或缓存内容的专项报告。"""

    executor = policy_executor or _load_phase2_executor()
    policy_result = executor(_phase2_control_input())
    candidates_by_ref = _candidates_by_ref(policy_result)
    side_effect_free = all(policy_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    policy_shape_preserved = (
        policy_result.get("input_accepted") is True
        and policy_result.get("execution_state") == "COMPLETED_IN_MEMORY_CONTROL_SLICE"
        and policy_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and policy_result.get("cache_policy_input_record_count") == 4
        and policy_result.get("cache_policy_candidate_count") == 4
        and len(candidates_by_ref) == 4
        and policy_result.get("source_page_reference_preserved") is True
    )
    cache_boundary_preserved = (
        policy_result.get("in_memory_candidate_policy_output_created") is True
        and policy_result.get("actual_cache_decision_created") is False
        and policy_result.get("actual_cache_decision_persisted") is False
        and policy_result.get("cache_created") is False
        and policy_result.get("cache_write_performed") is False
        and policy_result.get("cache_cleanup_performed") is False
        and policy_result.get("physical_storage_path_created") is False
        and policy_result.get("disk_scan_performed") is False
        and policy_result.get("cache_capacity_evaluation_performed") is False
    )
    scenario_results = [
        _evaluate_scenario(scenario, candidates_by_ref, side_effect_free)
        for scenario in SCENARIOS
    ]
    categories_covered = {
        str(item["scenario_category"]) for item in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    valid = (
        policy_shape_preserved
        and categories_covered
        and cache_boundary_preserved
        and all(item["expectation_met"] for item in scenario_results)
        and all(item["explicit_disposition"] for item in scenario_results)
        and not any(item["silent_drop"] for item in scenario_results)
        and side_effect_free
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": sum(
            item["expectation_met"] for item in scenario_results
        ),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] for item in scenario_results
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in scenario_results),
        "taskpack_quality_categories_covered": categories_covered,
        "phase2_control_slice_reexecuted": True,
        "unique_policy_candidate_count": len(candidates_by_ref),
        "policy_shape_preserved": policy_shape_preserved,
        "source_page_reference_preserved": all(
            item["source_page_reference_preserved"] for item in scenario_results
        ),
        "candidate_retained_unassessed_count": sum(
            item["quality_disposition"]
            in {
                "CANDIDATE_RETAINED_NOT_REAL_OCR_QUALITY_UNASSESSED",
                "CANDIDATE_RETAINED_TABLE_EXTRACTION_UNASSESSED",
            }
            for item in scenario_results
        ),
        "low_confidence_degraded_not_queued_count": sum(
            item["quality_disposition"]
            == "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in scenario_results
        ),
        "mixed_language_degraded_not_queued_count": sum(
            item["quality_disposition"]
            == "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in scenario_results
        ),
        "declared_review_route_count": sum(
            item["review_route_declared"] == REVIEW_ROUTE for item in scenario_results
        ),
        "failed_page_quality_scenario_count": sum(
            item["quality_disposition"]
            == "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION"
            for item in scenario_results
        ),
        "temporary_cleanup_policy_candidate_count": policy_result.get(
            "temporary_artifact_policy_candidate_count", 0
        ),
        "failure_automatic_cleanup_block_count": policy_result.get(
            "failure_artifact_policy_candidate_count", 0
        ),
        "scenario_results": scenario_results,
        "cache_boundary_preserved": cache_boundary_preserved,
        "physical_cache_item_count": 0,
        "cache_cleanup_action": "NO_PHYSICAL_CACHE_CREATED_NO_CLEANUP_EXECUTED",
        "actual_disk_capacity_proof_produced": False,
        "cache_capacity_evaluation_performed": False,
        "cache_cleanup_execution_performed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "authorized_fixture_access_performed": False,
        "real_pdf_or_image_opened": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "table_structure_extraction_performed": False,
        "language_detection_performed": False,
        "confidence_evaluation_performed": False,
        "recognition_accuracy_evaluated": False,
        "ocr_engine_selected": False,
        "ocr_engine_invocation_performed": False,
        "human_review_queue_write_performed": False,
        "human_review_task_created": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "phase4_started": False,
        "github_upload_performed": False,
    }


def _load_phase2_executor() -> PolicyExecutor:
    path = Path(__file__).with_name("stage056_ocr_cache_retention_policy_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage056_ocr_cache_retention_policy_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage056 P2 OCR cache retention policy slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_ocr_cache_retention_policy_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 冻结输入；它们是固定控制引用，不表示任何真实缓存或样本。"""

    return {
        "cache_policy_input_records": [
            {
                "cache_entry_ref": "cache-entry:control:stage056-p2:1",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage056-p2:1",
                "artifact_class": "TEMPORARY_PAGE_IMAGE",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "HIGH",
                "cache_state": "CANDIDATE_NOT_PERSISTED",
                "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                "cleanup_eligibility": TEMPORARY_CLEANUP,
                "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                "review_route": NO_REVIEW_ROUTE,
            },
            {
                "cache_entry_ref": "cache-entry:control:stage056-p2:2",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage056-p2:2",
                "artifact_class": "INTERMEDIATE_OCR_TEXT",
                "language_profile": "ENGLISH",
                "confidence_level": "LOW",
                "cache_state": "CANDIDATE_NOT_PERSISTED",
                "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                "cleanup_eligibility": TEMPORARY_CLEANUP,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
            },
            {
                "cache_entry_ref": "cache-entry:control:stage056-p2:3",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage056-p2:3",
                "artifact_class": "INTERMEDIATE_OCR_TEXT",
                "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                "confidence_level": "MEDIUM",
                "cache_state": "CANDIDATE_NOT_PERSISTED",
                "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                "cleanup_eligibility": TEMPORARY_CLEANUP,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
            },
            {
                "cache_entry_ref": "cache-entry:control:stage056-p2:4",
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage056-p2:4",
                "artifact_class": "FAILURE_ARTIFACT",
                "language_profile": "UNKNOWN",
                "confidence_level": "UNKNOWN",
                "cache_state": "CANDIDATE_NOT_PERSISTED",
                "retention_class": "FUTURE_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
                "cleanup_eligibility": FAILURE_CLEANUP,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
            },
        ]
    }


def _candidates_by_ref(policy_result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    candidates = policy_result.get("candidate_policy_outputs")
    if not isinstance(candidates, list):
        return {}
    return {
        candidate["source_page_ref"]: candidate
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and isinstance(candidate.get("source_page_ref"), str)
    }


def _evaluate_scenario(
    scenario: Mapping[str, object],
    candidates_by_ref: Mapping[str, Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    source_page_ref = str(scenario["policy_candidate_ref"])
    candidate = candidates_by_ref.get(source_page_ref, {})
    candidate_present = bool(candidate)
    quality_disposition = _quality_disposition(scenario, candidate)
    automatic_cleanup_blocked = candidate.get("cleanup_eligibility") == FAILURE_CLEANUP
    temporary_cleanup_policy_candidate = (
        candidate.get("cleanup_eligibility") == TEMPORARY_CLEANUP
    )
    expectation_met = (
        candidate_present
        and candidate.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and candidate.get("source_page_ref") == source_page_ref
        and candidate.get("artifact_class") == scenario["expected_artifact_class"]
        and candidate.get("language_profile") == scenario["expected_language_profile"]
        and candidate.get("confidence_level") == scenario["expected_confidence_level"]
        and candidate.get("cache_state") == "CANDIDATE_NOT_PERSISTED"
        and candidate.get("policy_state") == scenario["expected_policy_state"]
        and candidate.get("review_route") == scenario["expected_review_route"]
        and candidate.get("source_page_reference_preserved") is True
        and candidate.get("high_trust_direct_entry_allowed") is False
        and candidate.get("actual_cache_decision_created") is False
        and candidate.get("actual_cache_decision_persisted") is False
        and quality_disposition == scenario["expected_disposition"]
        and side_effect_free
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "scenario_category": str(scenario["scenario_category"]),
        "control_scenario_metadata_only": True,
        "policy_candidate_ref": source_page_ref,
        "source_page_ref": source_page_ref,
        "source_page_reference_preserved": candidate.get(
            "source_page_reference_preserved"
        )
        is True,
        "artifact_class": candidate.get("artifact_class"),
        "language_profile": candidate.get("language_profile"),
        "confidence_level": candidate.get("confidence_level"),
        "cache_policy_state": candidate.get("policy_state"),
        "quality_disposition": quality_disposition,
        "review_route_declared": candidate.get("review_route"),
        "review_required_not_queued": candidate.get("review_route") == REVIEW_ROUTE,
        "high_trust_direct_entry_allowed": candidate.get(
            "high_trust_direct_entry_allowed"
        ),
        "temporary_cleanup_policy_candidate": temporary_cleanup_policy_candidate,
        "automatic_cleanup_blocked": automatic_cleanup_blocked,
        "actual_ocr_text_created": False,
        "actual_pdf_or_image_opened": False,
        "actual_cache_created": False,
        "physical_cleanup_executed": False,
        "table_structure_extraction_performed": False,
        "recognition_accuracy_evaluated": False,
        "explicit_disposition": candidate_present
        and quality_disposition
        in {
            "CANDIDATE_RETAINED_NOT_REAL_OCR_QUALITY_UNASSESSED",
            "CANDIDATE_RETAINED_TABLE_EXTRACTION_UNASSESSED",
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
            "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION",
        },
        "silent_drop": not candidate_present,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }


def _quality_disposition(
    scenario: Mapping[str, object], candidate: Mapping[str, Any]
) -> str:
    if scenario["scenario_category"] == "TABLE_IMAGE_CONTROL":
        return "CANDIDATE_RETAINED_TABLE_EXTRACTION_UNASSESSED"
    policy_state = candidate.get("policy_state")
    if policy_state == "LOW_CONFIDENCE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
    if policy_state == "MIXED_LANGUAGE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
    if policy_state == "FAILURE_ARTIFACT_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP":
        return "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION"
    if policy_state == "TEMPORARY_CACHE_POLICY_CANDIDATE_OWNER_AND_CAPACITY_REQUIRED":
        return "CANDIDATE_RETAINED_NOT_REAL_OCR_QUALITY_UNASSESSED"
    return "CONTROL_SCENARIO_NOT_EVALUABLE"
