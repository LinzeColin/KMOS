"""Stage054 P3 的低置信度复核路由受控场景。

模块只重放 P2 的四条固定、非业务 reference-only 控制记录。五类场景是标量类别，
不是 PDF、图片、表格、页面或真实 OCR 结果；模块不打开来源，不调用 OCR，也不创建人工任务或缓存。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage054.low_confidence_review_route.phase3.quality_scenarios.v1"
RECORD_KIND = "CONTROLLED_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIO_REPORT"
PASS_RESULT = "PASS_PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS"
NEXT_GATE = "IDS-STAGE054-P4-GATE"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
NO_TEMPORARY_ARTIFACTS = "NO_TEMPORARY_ARTIFACT_CREATED"
REVIEW_ROUTE_STATES = {
    "LOW_CONFIDENCE_REVIEW_REQUIRED",
    "MIXED_LANGUAGE_REVIEW_REQUIRED",
    "FAILED_PAGE_REVIEW_REQUIRED",
}

SIDE_EFFECT_FIELDS = (
    "actual_review_request_created",
    "actual_review_request_persisted",
    "review_queue_record_created",
    "human_review_task_created",
    "human_review_result_created",
    "actual_ocr_text_created",
    "actual_page_image_reference_created",
    "actual_failure_record_created",
    "source_file_open_performed",
    "file_type_detection_performed",
    "route_evaluation_performed",
    "parser_execution_performed",
    "pdf_rasterization_performed",
    "image_processing_performed",
    "language_detection_performed",
    "ocr_engine_selected",
    "ocr_engine_configuration_performed",
    "ocr_engine_invocation_performed",
    "persistent_queue_write_performed",
    "persistent_page_output_write_performed",
    "cache_write_performed",
    "cache_cleanup_performed",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "audit_write_performed",
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
        "scenario_id": "scanned-pdf-control-unassessed",
        "scenario_category": "SCANNED_PDF_CONTROL",
        "control_source_page_ref": "source-page:control:stage054-p2:4",
        "expected_route_state": None,
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "HIGH",
        "expected_quality_disposition": "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
    },
    {
        "scenario_id": "blurred-image-control-degraded",
        "scenario_category": "BLURRED_IMAGE_CONTROL",
        "control_source_page_ref": "source-page:control:stage054-p2:1",
        "expected_route_state": "LOW_CONFIDENCE_REVIEW_REQUIRED",
        "expected_language_profile": "ENGLISH",
        "expected_confidence_level": "LOW",
        "expected_quality_disposition": (
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_CANDIDATE_ONLY"
        ),
    },
    {
        "scenario_id": "table-image-control-unassessed",
        "scenario_category": "TABLE_IMAGE_CONTROL",
        "control_source_page_ref": "source-page:control:stage054-p2:4",
        "expected_route_state": None,
        "expected_language_profile": "SIMPLIFIED_CHINESE",
        "expected_confidence_level": "HIGH",
        "expected_quality_disposition": (
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED"
        ),
    },
    {
        "scenario_id": "mixed-zh-en-control-degraded",
        "scenario_category": "MIXED_ZH_EN_CONTROL",
        "control_source_page_ref": "source-page:control:stage054-p2:2",
        "expected_route_state": "MIXED_LANGUAGE_REVIEW_REQUIRED",
        "expected_language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
        "expected_confidence_level": "MEDIUM",
        "expected_quality_disposition": (
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_CANDIDATE_ONLY"
        ),
    },
    {
        "scenario_id": "low-quality-control-failed",
        "scenario_category": "LOW_QUALITY_CONTROL",
        "control_source_page_ref": "source-page:control:stage054-p2:3",
        "expected_route_state": "FAILED_PAGE_REVIEW_REQUIRED",
        "expected_language_profile": "UNKNOWN",
        "expected_confidence_level": "UNKNOWN",
        "expected_quality_disposition": "FAILED_PAGE_DEGRADED_EVIDENCE_CANDIDATE_ONLY",
    },
)

RouteExecutor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_low_confidence_review_route_phase3_report(
    route_executor: RouteExecutor | None = None,
) -> dict[str, Any]:
    """重放 P2 路由结果，返回不含 OCR 或样本内容的 P3 场景处置报告。"""

    executor = route_executor or _load_phase2_executor()
    route_result = executor(_phase2_control_input())
    routes_by_page = _routes_by_page(route_result)
    side_effect_free = all(route_result.get(field) is False for field in SIDE_EFFECT_FIELDS)
    cache_boundary_preserved = (
        route_result.get("cache_policy") == CACHE_POLICY
        and route_result.get("cache_created") is False
        and route_result.get("cache_ref") is None
        and route_result.get("cache_write_performed") is False
        and route_result.get("cache_cleanup_performed") is False
    )
    scenario_results = [
        _evaluate_scenario(scenario, routes_by_page, side_effect_free)
        for scenario in SCENARIOS
    ]
    categories_covered = {
        str(item["scenario_category"]) for item in SCENARIOS
    } == REQUIRED_SCENARIO_CATEGORIES
    route_shape_preserved = (
        route_result.get("input_accepted") is True
        and route_result.get("route_state") == "COMPLETED"
        and route_result.get("route_result_count") == 4
        and len(routes_by_page) == 4
        and route_result.get("source_identity_ref") == "source:control:stage054-p2"
    )
    valid = (
        route_shape_preserved
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
        "phase2_control_route_reexecuted": True,
        "control_route_shape_preserved": route_shape_preserved,
        "automatic_review_route_candidate_count": sum(
            item["automatic_review_route_state_created_in_memory"]
            for item in scenario_results
        ),
        "degraded_evidence_candidate_count": sum(
            item["degraded_evidence_candidate_only"] for item in scenario_results
        ),
        "candidate_retained_unassessed_count": sum(
            item["quality_disposition"]
            in {
                "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
                "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            }
            for item in scenario_results
        ),
        "failed_page_degraded_candidate_count": sum(
            item["quality_disposition"]
            == "FAILED_PAGE_DEGRADED_EVIDENCE_CANDIDATE_ONLY"
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
        "automatic_human_review_assignment_performed": False,
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


def _load_phase2_executor() -> RouteExecutor:
    path = Path(__file__).with_name("stage054_low_confidence_review_route_slice.py")
    spec = importlib.util.spec_from_file_location(
        "stage054_low_confidence_review_route_slice", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage054 P2 low-confidence review route slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.route_low_confidence_controlled_reviews


def _phase2_control_input() -> dict[str, object]:
    """返回 P2 固定九字段控制输入，不表示页面、图像或 OCR 内容。"""

    return {
        "review_input_records": [
            {
                "source_identity_ref": "source:control:stage054-p2",
                "source_page_ref": "source-page:control:stage054-p2:1",
                "language_profile": "ENGLISH",
                "confidence_level": "LOW",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
            },
            {
                "source_identity_ref": "source:control:stage054-p2",
                "source_page_ref": "source-page:control:stage054-p2:2",
                "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                "confidence_level": "MEDIUM",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
            },
            {
                "source_identity_ref": "source:control:stage054-p2",
                "source_page_ref": "source-page:control:stage054-p2:3",
                "language_profile": "UNKNOWN",
                "confidence_level": "UNKNOWN",
                "output_status": "OCR_PAGE_FAILED",
                "failure_reason": "OCR_EXECUTION_NOT_STARTED",
                "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
            },
            {
                "source_identity_ref": "source:control:stage054-p2",
                "source_page_ref": "source-page:control:stage054-p2:4",
                "language_profile": "SIMPLIFIED_CHINESE",
                "confidence_level": "HIGH",
                "output_status": "OCR_OUTPUT_CONTROL_READY",
                "failure_reason": None,
                "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                "review_route": "NO_REVIEW_QUEUE_CREATED",
                "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
            },
        ]
    }


def _routes_by_page(
    route_result: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    routes = route_result.get("route_results")
    if not isinstance(routes, list):
        return {}
    return {
        route["source_page_ref"]: route
        for route in routes
        if isinstance(route, Mapping)
        and isinstance(route.get("source_page_ref"), str)
    }


def _evaluate_scenario(
    scenario: Mapping[str, object],
    routes_by_page: Mapping[str, Mapping[str, Any]],
    side_effect_free: bool,
) -> dict[str, Any]:
    source_page_ref = str(scenario["control_source_page_ref"])
    route = routes_by_page.get(source_page_ref, {})
    route_present = bool(route)
    route_state = route.get("route_state")
    candidate_created = route.get("review_request_candidate_created_in_memory") is True
    review_required = route_state in REVIEW_ROUTE_STATES
    quality_disposition = _quality_disposition(scenario, route_state)
    expected_review_candidate = scenario["expected_route_state"] is not None
    candidate_is_reference_only = _candidate_is_reference_only(
        route.get("review_request_candidate")
    )
    candidate_expectation_met = (
        candidate_created
        and candidate_is_reference_only
        and _candidate_language(route.get("review_request_candidate"))
        == scenario["expected_language_profile"]
        and _candidate_confidence(route.get("review_request_candidate"))
        == scenario["expected_confidence_level"]
        if expected_review_candidate
        else not candidate_created and route.get("review_request_candidate") is None
    )
    expectation_met = (
        route_present
        and route.get("source_page_ref") == source_page_ref
        and route_state == scenario["expected_route_state"]
        and route.get("source_page_reference_preserved") is True
        and route.get("initial_fact_level") == "CANDIDATE"
        and route.get("quality_state") == "UNASSESSED"
        and route.get("high_trust_direct_entry_allowed") is False
        and candidate_expectation_met
        and route.get("actual_review_request_created") is False
        and route.get("review_queue_record_created") is False
        and route.get("human_review_task_created") is False
        and route.get("human_review_result_created") is False
        and quality_disposition == scenario["expected_quality_disposition"]
        and side_effect_free
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "scenario_category": str(scenario["scenario_category"]),
        "control_scenario_metadata_only": True,
        "source_page_ref": source_page_ref,
        "route_state": route_state,
        "expected_confidence_level": scenario["expected_confidence_level"],
        "expected_language_profile": scenario["expected_language_profile"],
        "quality_disposition": quality_disposition,
        "initial_fact_level": route.get("initial_fact_level"),
        "quality_state": route.get("quality_state"),
        "high_trust_direct_entry_allowed": route.get(
            "high_trust_direct_entry_allowed"
        ),
        "automatic_review_route_state_created_in_memory": review_required
        and candidate_created,
        "degraded_evidence_candidate_only": review_required,
        "actual_human_review_assignment_performed": False,
        "human_review_task_created": route.get("human_review_task_created") is True,
        "review_queue_record_created": route.get("review_queue_record_created") is True,
        "actual_ocr_text_created": False,
        "actual_pdf_or_image_opened": False,
        "table_structure_extraction_performed": False,
        "recognition_accuracy_evaluated": False,
        "explicit_disposition": route_present
        and quality_disposition
        in {
            "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_CANDIDATE_ONLY",
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_CANDIDATE_ONLY",
            "FAILED_PAGE_DEGRADED_EVIDENCE_CANDIDATE_ONLY",
        },
        "silent_drop": not route_present,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }


def _candidate_is_reference_only(candidate: object) -> bool:
    if not isinstance(candidate, Mapping):
        return False
    return set(candidate) == {
        "source_identity_ref",
        "source_page_ref",
        "language_profile",
        "confidence_level",
        "output_status",
        "failure_reason",
        "evidence_eligibility",
        "review_route",
        "cache_policy_ref",
        "feedback_code",
    }


def _candidate_language(candidate: object) -> object:
    return candidate.get("language_profile") if isinstance(candidate, Mapping) else None


def _candidate_confidence(candidate: object) -> object:
    return candidate.get("confidence_level") if isinstance(candidate, Mapping) else None


def _quality_disposition(scenario: Mapping[str, object], route_state: object) -> str:
    if scenario["scenario_category"] == "TABLE_IMAGE_CONTROL":
        return "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED"
    if route_state == "LOW_CONFIDENCE_REVIEW_REQUIRED":
        return "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_CANDIDATE_ONLY"
    if route_state == "MIXED_LANGUAGE_REVIEW_REQUIRED":
        return "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_CANDIDATE_ONLY"
    if route_state == "FAILED_PAGE_REVIEW_REQUIRED":
        return "FAILED_PAGE_DEGRADED_EVIDENCE_CANDIDATE_ONLY"
    if route_state is None:
        return "CANDIDATE_RETAINED_QUALITY_UNASSESSED"
    return "CONTROL_SCENARIO_NOT_EVALUABLE"
