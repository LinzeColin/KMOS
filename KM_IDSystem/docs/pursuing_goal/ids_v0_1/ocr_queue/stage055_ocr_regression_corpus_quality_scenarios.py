"""Stage055 P3 的 OCR 回归语料受控专项场景。

模块只重放 P2 的五条固定、非业务 control 记录。扫描 PDF、模糊图片、表格图片、
中英文混合和低质量样例在这里都是类别标签，不是文件、图像、页面或 OCR 结果；
模块不读取样本、不调用 OCR 引擎，也不创建缓存或人工复核任务。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage055.ocr_regression_corpus.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_OCR_REGRESSION_CORPUS_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE055-P4-GATE"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
NO_TEMPORARY_ARTIFACTS = "NO_TEMPORARY_ARTIFACT_CREATED"
SOURCE_IDENTITY_REF = "source:control:stage055-p2"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
NO_REVIEW_ROUTE = "NO_REVIEW_QUEUE_CREATED"
SYMBOLIC_OUTPUT_KIND = "CONTROL_SYMBOLIC_OUTPUT_NOT_REAL_OCR_TEXT"
SYMBOLIC_IMAGE_REF_KIND = "CONTROL_SYMBOLIC_PAGE_IMAGE_REFERENCE_NOT_REAL_IMAGE"
CONTROL_FAILURE_KIND = "CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD"

SIDE_EFFECT_FIELDS = (
    "source_file_open_performed",
    "file_type_detection_performed",
    "route_evaluation_performed",
    "parser_execution_performed",
    "pdf_rasterization_performed",
    "image_processing_performed",
    "table_structure_extraction_performed",
    "language_detection_performed",
    "confidence_evaluation_performed",
    "ocr_engine_selected",
    "ocr_engine_configuration_performed",
    "ocr_engine_invocation_performed",
    "ocr_engine_comparison_performed",
    "regression_execution_performed",
    "recognition_accuracy_evaluated",
    "persistent_queue_write_performed",
    "persistent_page_output_write_performed",
    "page_image_reference_write_performed",
    "failure_record_write_performed",
    "cache_write_performed",
    "cache_cleanup_performed",
    "review_queue_write_performed",
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
        "scenario_id": "scanned-pdf-control-candidate",
        "scenario_category": "SCANNED_PDF_CONTROL",
        "control_input_class": "SCANNED_DOCUMENT_CONTROL",
        "source_page_ref": "source-page:control:stage055-p2:1",
        "expected_page_state": "OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED",
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "HIGH",
        "expected_quality_disposition": "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
        "expected_review_route": NO_REVIEW_ROUTE,
    },
    {
        "scenario_id": "blurred-image-control-degraded",
        "scenario_category": "BLURRED_IMAGE_CONTROL",
        "control_input_class": "BLURRED_DOCUMENT_CONTROL",
        "source_page_ref": "source-page:control:stage055-p2:2",
        "expected_page_state": "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "LOW",
        "expected_quality_disposition": "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_review_route": REVIEW_ROUTE,
    },
    {
        "scenario_id": "table-image-control-unassessed",
        "scenario_category": "TABLE_IMAGE_CONTROL",
        "control_input_class": "TABLE_DOCUMENT_CONTROL",
        "source_page_ref": "source-page:control:stage055-p2:3",
        "expected_page_state": "OCR_TABLE_DOCUMENT_CANDIDATE_UNASSESSED",
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "MEDIUM",
        "expected_quality_disposition": "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
        "expected_review_route": NO_REVIEW_ROUTE,
    },
    {
        "scenario_id": "mixed-zh-en-control-degraded",
        "scenario_category": "MIXED_ZH_EN_CONTROL",
        "control_input_class": "MIXED_ZH_EN_DOCUMENT_CONTROL",
        "source_page_ref": "source-page:control:stage055-p2:4",
        "expected_page_state": "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "expected_confidence_level": "MEDIUM",
        "expected_quality_disposition": "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_review_route": REVIEW_ROUTE,
    },
    {
        "scenario_id": "low-quality-control-failed",
        "scenario_category": "LOW_QUALITY_CONTROL",
        "control_input_class": "LOW_QUALITY_DOCUMENT_CONTROL",
        "source_page_ref": "source-page:control:stage055-p2:5",
        "expected_page_state": "OCR_PAGE_FAILED_EXPLICIT",
        "expected_language_profile": "UNKNOWN",
        "expected_confidence_level": "UNKNOWN",
        "expected_quality_disposition": "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
        "expected_review_route": REVIEW_ROUTE,
    },
)

CorpusExecutor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_ocr_regression_corpus_phase3_report(
    corpus_executor: CorpusExecutor | None = None,
) -> dict[str, Any]:
    """重放 P2 control 输出并返回不含样本或 OCR 内容的专项验证报告。"""

    executor = corpus_executor or _load_phase2_executor()
    corpus_result = executor(_phase2_control_input())
    pages_by_ref = _pages_by_ref(corpus_result)
    side_effect_free = all(corpus_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    cache_boundary_preserved = (
        corpus_result.get("cache_policy") == CACHE_POLICY
        and corpus_result.get("cache_created") is False
        and corpus_result.get("cache_ref") is None
        and corpus_result.get("cache_write_performed") is False
        and corpus_result.get("cache_cleanup_performed") is False
    )
    scenario_results = [
        _evaluate_scenario(scenario, pages_by_ref, side_effect_free)
        for scenario in SCENARIOS
    ]
    categories_covered = {
        str(item["scenario_category"]) for item in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    queue_shape_preserved = (
        corpus_result.get("input_accepted") is True
        and corpus_result.get("queue_state") == "COMPLETED"
        and corpus_result.get("queue_state_history")
        == ["QUEUED", "PROCESSING", "COMPLETED"]
        and corpus_result.get("queue_record", {}).get("input_record_count") == 5
        and corpus_result.get("page_output_count") == 5
        and len(pages_by_ref) == 5
        and corpus_result.get("source_identity_ref") == SOURCE_IDENTITY_REF
    )
    valid = (
        queue_shape_preserved
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
        "control_queue_shape_preserved": queue_shape_preserved,
        "source_page_reference_preserved": all(
            item["source_page_reference_preserved"] for item in scenario_results
        ),
        "candidate_retained_unassessed_count": sum(
            item["quality_disposition"]
            in {
                "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
                "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
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
            item["review_route_declared"] == REVIEW_ROUTE
            for item in scenario_results
        ),
        "failed_page_quality_scenario_count": sum(
            item["quality_disposition"] == "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
            for item in scenario_results
        ),
        "scenario_results": scenario_results,
        "cache_boundary_preserved": cache_boundary_preserved,
        "temporary_artifact_count": 0,
        "cache_cleanup_action": NO_TEMPORARY_ARTIFACTS,
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


def _load_phase2_executor() -> CorpusExecutor:
    path = Path(__file__).with_name("stage055_ocr_regression_corpus_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage055_ocr_regression_corpus_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage055 P2 OCR regression corpus slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_ocr_regression_corpus_control_slice


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 已冻结的五条 control 输入，不表示真实样本或页面。"""

    return {
        "regression_input_records": [
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage055-p2:1",
                "input_class": "SCANNED_DOCUMENT_CONTROL",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "HIGH",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                "review_route": NO_REVIEW_ROUTE,
                "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage055-p2:2",
                "input_class": "BLURRED_DOCUMENT_CONTROL",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "LOW",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
                "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage055-p2:3",
                "input_class": "TABLE_DOCUMENT_CONTROL",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "MEDIUM",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                "review_route": NO_REVIEW_ROUTE,
                "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage055-p2:4",
                "input_class": "MIXED_ZH_EN_DOCUMENT_CONTROL",
                "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                "confidence_level": "MEDIUM",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
                "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
            },
            {
                "source_identity_ref": SOURCE_IDENTITY_REF,
                "source_page_ref": "source-page:control:stage055-p2:5",
                "input_class": "LOW_QUALITY_DOCUMENT_CONTROL",
                "language_profile": "UNKNOWN",
                "confidence_level": "UNKNOWN",
                "output_status": "OCR_PAGE_FAILED",
                "failure_reason": "OCR_EXECUTION_NOT_STARTED",
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": REVIEW_ROUTE,
                "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
            },
        ]
    }


def _pages_by_ref(corpus_result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    pages = corpus_result.get("page_outputs")
    if not isinstance(pages, list):
        return {}
    return {
        page["source_page_ref"]: page
        for page in pages
        if isinstance(page, Mapping)
        and isinstance(page.get("source_page_ref"), str)
    }


def _evaluate_scenario(
    scenario: Mapping[str, object],
    pages_by_ref: Mapping[str, Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    source_page_ref = str(scenario["source_page_ref"])
    page = pages_by_ref.get(source_page_ref, {})
    page_present = bool(page)
    page_state = page.get("page_state")
    quality_disposition = _quality_disposition(scenario, page_state)
    is_failed = page_state == "OCR_PAGE_FAILED_EXPLICIT"
    symbolic_output_shape_preserved = (
        page.get("text_output_kind") == "NO_OUTPUT"
        and page.get("page_image_reference_kind") == "NO_IMAGE_REFERENCE"
        and page.get("failure_reason_kind") == CONTROL_FAILURE_KIND
        if is_failed
        else page.get("text_output_kind") == SYMBOLIC_OUTPUT_KIND
        and page.get("page_image_reference_kind") == SYMBOLIC_IMAGE_REF_KIND
        and page.get("failure_reason_kind") == "NO_FAILURE_REASON"
    )
    failed_page_classification_preserved = (
        page.get("failure_reason_kind") == CONTROL_FAILURE_KIND
        and page.get("actual_failure_record_created") is False
        if is_failed
        else page.get("failure_reason_kind") == "NO_FAILURE_REASON"
    )
    expectation_met = (
        page_present
        and page.get("source_identity_ref") == SOURCE_IDENTITY_REF
        and page.get("source_page_ref") == source_page_ref
        and page.get("regression_category") == scenario["control_input_class"]
        and page_state == scenario["expected_page_state"]
        and page.get("language_profile") == scenario["expected_language_profile"]
        and page.get("confidence_level") == scenario["expected_confidence_level"]
        and page.get("review_route") == scenario["expected_review_route"]
        and page.get("quality_state") == "UNASSESSED"
        and page.get("evidence_eligibility")
        in {
            "CANDIDATE_ONLY_QUALITY_UNASSESSED",
            "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
        }
        and page.get("source_page_reference_preserved") is True
        and page.get("high_trust_direct_entry_allowed") is False
        and page.get("actual_ocr_text_created") is False
        and page.get("actual_page_image_reference_created") is False
        and symbolic_output_shape_preserved
        and failed_page_classification_preserved
        and quality_disposition == scenario["expected_quality_disposition"]
        and side_effect_free
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "scenario_category": str(scenario["scenario_category"]),
        "control_scenario_metadata_only": True,
        "control_input_class": str(scenario["control_input_class"]),
        "source_page_ref": source_page_ref,
        "source_page_reference_preserved": page.get(
            "source_page_reference_preserved"
        )
        is True,
        "page_state": page_state,
        "language_profile": page.get("language_profile"),
        "confidence_level": page.get("confidence_level"),
        "quality_disposition": quality_disposition,
        "quality_state": page.get("quality_state"),
        "review_route_declared": page.get("review_route"),
        "review_required_not_queued": page.get("review_route") == REVIEW_ROUTE,
        "high_trust_direct_entry_allowed": page.get(
            "high_trust_direct_entry_allowed"
        ),
        "symbolic_output_shape_preserved": symbolic_output_shape_preserved,
        "actual_ocr_text_created": False,
        "actual_pdf_or_image_opened": False,
        "table_structure_extraction_performed": False,
        "recognition_accuracy_evaluated": False,
        "explicit_disposition": page_present
        and quality_disposition
        in {
            "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
            "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
        },
        "silent_drop": not page_present,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }


def _quality_disposition(scenario: Mapping[str, object], page_state: object) -> str:
    if scenario["scenario_category"] == "TABLE_IMAGE_CONTROL":
        return "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED"
    if page_state == "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
    if page_state == "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
    if page_state == "OCR_PAGE_FAILED_EXPLICIT":
        return "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
    if page_state == "OCR_SCANNED_DOCUMENT_CANDIDATE_RETAINED":
        return "CANDIDATE_RETAINED_QUALITY_UNASSESSED"
    return "CONTROL_SCENARIO_NOT_EVALUABLE"
