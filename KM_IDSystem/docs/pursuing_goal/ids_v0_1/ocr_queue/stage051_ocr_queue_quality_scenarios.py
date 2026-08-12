"""Stage051 P3 的 OCR 质量受控场景。

本模块只重放 P2 的固定四页纯内存 control 队列。五类场景是标量类别，
不是文件、页面、图像、表格或真实 OCR 结果；模块不打开来源，也不调用 OCR 引擎。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage051.ocr_queue.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_OCR_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_CONTROLLED_OCR_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_CONTROLLED_OCR_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE051-P4-GATE"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
NO_TEMPORARY_ARTIFACTS = "NO_TEMPORARY_ARTIFACT_CREATED"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"

SIDE_EFFECT_FIELDS = (
    "source_file_open_performed",
    "file_type_detection_performed",
    "route_evaluation_performed",
    "parser_execution_performed",
    "pdf_rasterization_performed",
    "image_processing_performed",
    "ocr_engine_selected",
    "ocr_engine_configuration_performed",
    "ocr_engine_invocation_performed",
    "persistent_queue_write_performed",
    "persistent_page_output_write_performed",
    "cache_write_performed",
    "review_queue_write_performed",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
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
        "scenario_id": "scanned-pdf-control-baseline",
        "scenario_category": "SCANNED_PDF_CONTROL",
        "control_page_number": 1,
        "expected_page_state": "OCR_PAGE_CANDIDATE_RETAINED",
        "expected_confidence": "HIGH",
        "expected_language": "SIMPLIFIED_CHINESE",
        "expected_quality_disposition": "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
    },
    {
        "scenario_id": "blurred-image-control-degraded",
        "scenario_category": "BLURRED_IMAGE_CONTROL",
        "control_page_number": 2,
        "expected_page_state": "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_confidence": "LOW",
        "expected_language": "ENGLISH",
        "expected_quality_disposition": "DEGRADED_EVIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
    },
    {
        "scenario_id": "table-image-control-unassessed",
        "scenario_category": "TABLE_IMAGE_CONTROL",
        "control_page_number": 1,
        "expected_page_state": "OCR_PAGE_CANDIDATE_RETAINED",
        "expected_confidence": "HIGH",
        "expected_language": "SIMPLIFIED_CHINESE",
        "expected_quality_disposition": "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
    },
    {
        "scenario_id": "mixed-zh-en-control-degraded",
        "scenario_category": "MIXED_ZH_EN_CONTROL",
        "control_page_number": 3,
        "expected_page_state": "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED",
        "expected_confidence": "MEDIUM",
        "expected_language": "MIXED_ZH_EN",
        "expected_quality_disposition": (
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
        ),
    },
    {
        "scenario_id": "low-quality-control-failed",
        "scenario_category": "LOW_QUALITY_CONTROL",
        "control_page_number": 4,
        "expected_page_state": "OCR_PAGE_FAILED_EXPLICIT",
        "expected_confidence": "UNKNOWN",
        "expected_language": "UNKNOWN",
        "expected_quality_disposition": "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
    },
)

QueueExecutor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_phase3_quality_report(
    queue_executor: QueueExecutor | None = None,
) -> dict[str, Any]:
    """重放 P2 control 队列，返回不含 OCR 文本或来源内容的 P3 质量处置报告。"""

    executor = queue_executor or _load_phase2_executor()
    queue_result = executor(_phase2_control_input())
    pages_by_number = _pages_by_number(queue_result)
    side_effect_free = all(queue_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    cache_boundary_preserved = (
        queue_result.get("cache_policy") == CACHE_POLICY
        and queue_result.get("cache_created") is False
        and queue_result.get("cache_ref") is None
        and queue_result.get("cache_write_performed") is False
    )
    results = [
        _evaluate_scenario(scenario, pages_by_number, side_effect_free)
        for scenario in SCENARIOS
    ]
    coverage_preserved = {
        str(item["scenario_category"]) for item in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    queue_shape_preserved = (
        queue_result.get("input_accepted") is True
        and queue_result.get("job_state") == "COMPLETED"
        and queue_result.get("page_output_count") == 4
        and len(pages_by_number) == 4
    )
    valid = (
        queue_shape_preserved
        and coverage_preserved
        and cache_boundary_preserved
        and all(item["expectation_met"] for item in results)
        and all(item["explicit_disposition"] for item in results)
        and not any(item["silent_drop"] for item in results)
        and side_effect_free
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "scenario_count": len(results),
        "passed_scenario_count": sum(item["expectation_met"] for item in results),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] for item in results
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in results),
        "taskpack_quality_categories_covered": coverage_preserved,
        "control_queue_reexecuted": True,
        "control_queue_shape_preserved": queue_shape_preserved,
        "cache_boundary_preserved": cache_boundary_preserved,
        "temporary_artifact_count": 0,
        "cache_cleanup_action": NO_TEMPORARY_ARTIFACTS,
        "low_confidence_degraded_not_queued_count": sum(
            item["quality_disposition"]
            == "DEGRADED_EVIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in results
        ),
        "mixed_language_degraded_not_queued_count": sum(
            item["quality_disposition"]
            == "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in results
        ),
        "failed_page_count": sum(
            item["quality_disposition"] == "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
            for item in results
        ),
        "scenario_results": results,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "real_pdf_or_image_opened": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "table_structure_extraction_performed": False,
        "recognition_accuracy_evaluated": False,
        "ocr_engine_selected": False,
        "ocr_engine_invocation_performed": False,
        "human_review_queue_write_performed": False,
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


def _load_phase2_executor() -> QueueExecutor:
    path = Path(__file__).with_name("stage051_ocr_queue_slice.py")
    spec = importlib.util.spec_from_file_location("stage051_ocr_queue_slice", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage051 P2 control queue slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_controlled_ocr_queue


def _phase2_control_input() -> dict[str, object]:
    """仅返回 P2 已固定的四页 control 输入，不表示文件或页面。"""

    return {
        "ocr_input_reference": {
            "source_identity_ref": "source:control:stage051-p2",
            "input_kind_hint": "SCANNED_PDF",
            "parser_output_status": "CONTROL_OCR_QUEUE_CANDIDATE",
            "source_page_count_ref": "page-count:control:4",
            "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
            "ocr_request_reason": "CONTROL_LOW_TEXT_COVERAGE_BASELINE",
            "cache_policy_ref": "cache-policy:stage051-p2:in-memory",
        },
        "page_controls": [
            {
                "page_number": 1,
                "control_text": "中文控制页",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "HIGH",
                "page_outcome": "OCR_OUTPUT_READY",
            },
            {
                "page_number": 2,
                "control_text": "English control page",
                "language_profile": "ENGLISH",
                "confidence_level": "LOW",
                "page_outcome": "OCR_OUTPUT_READY",
            },
            {
                "page_number": 3,
                "control_text": "中英 mixed control page",
                "language_profile": "MIXED_ZH_EN",
                "confidence_level": "MEDIUM",
                "page_outcome": "OCR_OUTPUT_READY",
            },
            {
                "page_number": 4,
                "control_text": None,
                "language_profile": "UNKNOWN",
                "confidence_level": "UNKNOWN",
                "page_outcome": "OCR_PAGE_FAILED",
            },
        ],
    }


def _pages_by_number(queue_result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    pages = queue_result.get("page_outputs")
    if not isinstance(pages, list):
        return {}
    return {
        page["source_page_ref"].rsplit(":", 1)[-1]: page
        for page in pages
        if isinstance(page, Mapping)
        and isinstance(page.get("source_page_ref"), str)
        and page["source_page_ref"].rsplit(":", 1)[-1].isdigit()
    }


def _evaluate_scenario(
    scenario: Mapping[str, object],
    pages_by_number: Mapping[str, Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    page_number = int(scenario["control_page_number"])
    page = pages_by_number.get(str(page_number), {})
    page_state = page.get("page_state")
    quality_disposition = _quality_disposition(scenario, page_state)
    expected_page_ref = f"source-page:control:stage051-p2:{page_number}"
    review_required = quality_disposition.startswith("DEGRADED_EVIDENCE")
    expectation_met = (
        page.get("source_page_ref") == expected_page_ref
        and page_state == scenario["expected_page_state"]
        and page.get("confidence_level") == scenario["expected_confidence"]
        and page.get("language_profile") == scenario["expected_language"]
        and quality_disposition == scenario["expected_quality_disposition"]
        and page.get("quality_state") == "UNASSESSED"
        and page.get("high_trust_direct_entry_allowed") is False
        and (not review_required or page.get("review_route") == REVIEW_ROUTE)
        and side_effect_free
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "scenario_category": str(scenario["scenario_category"]),
        "control_scenario_metadata_only": True,
        "control_page_number": page_number,
        "source_page_ref": page.get("source_page_ref"),
        "page_state": page_state,
        "language_profile": page.get("language_profile"),
        "confidence_level": page.get("confidence_level"),
        "quality_disposition": quality_disposition,
        "quality_state": page.get("quality_state"),
        "high_trust_direct_entry_allowed": page.get(
            "high_trust_direct_entry_allowed"
        ),
        "review_required_not_queued": review_required,
        "review_route_declared": page.get("review_route"),
        "recognition_text_retained": False,
        "actual_pdf_or_image_opened": False,
        "table_structure_extraction_performed": False,
        "recognition_accuracy_evaluated": False,
        "explicit_disposition": quality_disposition
        in {
            "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            "DEGRADED_EVIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
            "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
        },
        "silent_drop": False,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }


def _quality_disposition(
    scenario: Mapping[str, object], page_state: object
) -> str:
    if scenario["scenario_category"] == "TABLE_IMAGE_CONTROL":
        return "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED"
    if page_state == "OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_REVIEW_REQUIRED_NOT_QUEUED"
    if page_state == "OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED":
        return "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED"
    if page_state == "OCR_PAGE_FAILED_EXPLICIT":
        return "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
    if page_state == "OCR_PAGE_CANDIDATE_RETAINED":
        return "CANDIDATE_RETAINED_QUALITY_UNASSESSED"
    return "CONTROL_SCENARIO_NOT_EVALUABLE"
