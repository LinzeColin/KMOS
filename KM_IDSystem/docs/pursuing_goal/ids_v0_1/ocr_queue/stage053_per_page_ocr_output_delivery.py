"""Stage053 P4 的按页 OCR metadata-only 交付证据。

模块只从 P3 的固定非业务质量 control 报告派生交付元数据。它不读取 PDF、图片、
页面、表格或 OCR 文本，不选择或调用 OCR 引擎，也不创建队列、缓存、复核记录或运行时。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage053.per_page_ocr_output.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_PER_PAGE_OCR_DELIVERY_REPORT"
OUTPUT_SAMPLE_KIND = "DELIVERY_METADATA_ONLY_PER_PAGE_OCR_OUTPUT_SAMPLE_NOT_REAL_OCR"
FAILURE_RECORD_KIND = "CONTROLLED_PER_PAGE_OCR_FAILURE_LIST_ENTRY_NOT_RUNTIME"
REVIEW_ROUTE_PROOF_KIND = "DECLARED_PER_PAGE_OCR_REVIEW_ROUTE_PROOF_NOT_QUEUED"
PASS_RESULT = "PASS_PHASE4_PER_PAGE_OCR_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_PER_PAGE_OCR_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE053-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_PER_PAGE_CONTROLLED_OCR_QUALITY_SCENARIOS_RUNTIME_DISABLED"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
CACHE_CLEANUP_ACTION = "NO_TEMPORARY_ARTIFACT_CREATED"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"

EXPECTED_SCENARIO_IDS = (
    "scanned-pdf-control-baseline",
    "blurred-image-control-degraded",
    "table-image-control-unassessed",
    "mixed-zh-en-control-degraded",
    "low-quality-control-failed",
)
DEGRADED_SCENARIO_IDS = (
    "blurred-image-control-degraded",
    "mixed-zh-en-control-degraded",
)
FAILURE_SCENARIO_ID = "low-quality-control-failed"
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
SIDE_EFFECT_FIELDS = (
    "source_file_open_performed",
    "file_type_detection_performed",
    "route_evaluation_performed",
    "parser_execution_performed",
    "pdf_rasterization_performed",
    "image_processing_performed",
    "table_structure_extraction_performed",
    "recognition_accuracy_evaluated",
    "ocr_engine_selected",
    "ocr_engine_invocation_performed",
    "human_review_queue_write_performed",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

QualityReportProvider = Callable[[], Mapping[str, Any]]


def build_per_page_phase4_delivery_report(
    quality_report_provider: QualityReportProvider | None = None,
) -> dict[str, Any]:
    """派生可复核的 P4 交付证据；所有样例只保留 control 元数据。"""

    provider = quality_report_provider or _load_phase3_report_provider()
    predecessor = provider()
    predecessor = predecessor if isinstance(predecessor, Mapping) else {}
    scenarios = _scenario_map(predecessor.get("scenario_results"))
    samples = _build_delivery_samples(scenarios)
    confidence_report = _build_confidence_report(scenarios)
    failure_list = _build_failure_list(scenarios)
    review_route_proofs = _build_review_route_proofs(scenarios)
    cache_rerun_instructions = _cache_rerun_instructions()
    valid = _is_valid(
        predecessor,
        scenarios,
        samples,
        confidence_report,
        failure_list,
        review_route_proofs,
        cache_rerun_instructions,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "predecessor_result": predecessor.get("result"),
        "delivery_samples": samples,
        "confidence_report": confidence_report,
        "failure_list": failure_list,
        "review_route_proofs": review_route_proofs,
        "quality_limitations_zh": [
            "本交付只来自五类固定非业务 control，不能代表真实扫描件、真实 OCR 文本或识别准确率。",
            "表格图片 control 未执行表结构提取；候选、降级和失败处置不能直接进入高可信证据层。",
            "低置信和中英文混合情形只声明后续 Stage054 复核路由，不创建实际人工复核任务。",
        ],
        "human_confirmation_prompts_zh": [
            {
                "prompt_id": "confirm-per-page-control-evidence-boundary",
                "text": "请业务线确认：本页仅为按页 OCR control 交付元数据，不可替代真实 OCR 结果或高可信证据。",
                "automatic_confirmation_performed": False,
            },
            {
                "prompt_id": "confirm-per-page-degraded-review-ownership",
                "text": "请业务线确认：低置信和中英文混合 control 仅保留降级提示，实际复核仍由 Stage054 独立处理。",
                "automatic_confirmation_performed": False,
            },
            {
                "prompt_id": "confirm-per-page-cache-boundary",
                "text": "请业务线确认：当前没有缓存路径或临时产物；不得以本说明触发目录扫描或删除。",
                "automatic_confirmation_performed": False,
            },
        ],
        "cache_rerun_instructions": cache_rerun_instructions,
        "rollback": {
            "return_to": "PHASE3_PER_PAGE_OCR_CONTROLLED_QUALITY_SCENARIOS_ENGINE_DISABLED",
            "revertable_artifacts": [
                "Stage053 Phase4 per-page OCR delivery report module",
                "Stage053 Phase4 per-page OCR delivery contract",
                "Stage053 Phase4 focused tests",
                "Stage053 Phase4 governance projection",
            ],
            "preserve_predecessor_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "persistent_runtime_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
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
        "cache_created": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "github_upload_performed": False,
    }


def _load_phase3_report_provider() -> QualityReportProvider:
    path = Path(__file__).with_name("stage053_per_page_ocr_output_quality_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage053_p3_quality_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage053 P3 per-page OCR quality scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_per_page_phase3_quality_report


def _scenario_map(value: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        return {}
    mapped: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            return {}
        scenario_id = item.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id in mapped:
            return {}
        mapped[scenario_id] = item
    return mapped


def _build_delivery_samples(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        samples.append(
            {
                "sample_id": f"delivery-{scenario_id}",
                "sample_kind": OUTPUT_SAMPLE_KIND,
                "scenario_id": scenario_id,
                "scenario_category": scenario.get("scenario_category"),
                "source_page_ref": scenario.get("source_page_ref"),
                "page_state": scenario.get("page_state"),
                "language_profile": scenario.get("language_profile"),
                "confidence_level": scenario.get("confidence_level"),
                "quality_disposition": scenario.get("quality_disposition"),
                "quality_state": scenario.get("quality_state"),
                "ocr_text_retained": False,
                "source_content_retained": False,
                "actual_ocr_output_produced": False,
                "high_trust_direct_entry_allowed": False,
            }
        )
    return samples


def _build_confidence_report(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ordered = [scenarios[item] for item in EXPECTED_SCENARIO_IDS if item in scenarios]
    counts = {
        level: sum(item.get("confidence_level") == level for item in ordered)
        for level in CONFIDENCE_LEVELS
    }
    return {
        "report_kind": "CONTROLLED_PER_PAGE_OCR_CONFIDENCE_SUMMARY_NOT_REAL_OCR_ACCURACY",
        "scenario_count": len(ordered),
        "confidence_counts": counts,
        "candidate_sample_count": sum(
            str(item.get("quality_disposition", "")).startswith("CANDIDATE_RETAINED")
            for item in ordered
        ),
        "degraded_review_required_count": sum(
            str(item.get("quality_disposition", "")).startswith("DEGRADED_EVIDENCE")
            for item in ordered
        ),
        "explicit_failure_count": sum(
            item.get("quality_disposition")
            == "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
            for item in ordered
        ),
        "recognition_accuracy_evaluated": False,
        "quality_gate_evaluated": False,
        "high_trust_evidence_promoted": False,
    }


def _build_failure_list(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    scenario = scenarios.get(FAILURE_SCENARIO_ID)
    if scenario is None:
        return []
    return [
        {
            "failure_id": FAILURE_SCENARIO_ID,
            "record_kind": FAILURE_RECORD_KIND,
            "source_page_ref": scenario.get("source_page_ref"),
            "page_state": scenario.get("page_state"),
            "quality_disposition": scenario.get("quality_disposition"),
            "failure_is_control_metadata_only": True,
            "evidence_promotion_performed": False,
            "review_queue_write_performed": False,
            "silent_drop": False,
        }
    ]


def _build_review_route_proofs(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    proofs: list[dict[str, Any]] = []
    for scenario_id in DEGRADED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        proofs.append(
            {
                "scenario_id": scenario_id,
                "record_kind": REVIEW_ROUTE_PROOF_KIND,
                "source_page_ref": scenario.get("source_page_ref"),
                "quality_disposition": scenario.get("quality_disposition"),
                "review_route_declared": scenario.get("review_route_declared"),
                "review_required_not_queued": scenario.get("review_required_not_queued"),
                "human_confirmation_required": True,
                "review_queue_created": False,
                "review_queue_write_performed": False,
            }
        )
    return proofs


def _cache_rerun_instructions() -> dict[str, Any]:
    return {
        "cache_policy": CACHE_POLICY,
        "temporary_artifact_count": 0,
        "cache_storage_location_assigned": False,
        "cleanup_action": CACHE_CLEANUP_ACTION,
        "actual_cleanup_performed": False,
        "cleanup_instructions_zh": [
            "当前临时产物数为 0；不得扫描、删除或移动任何目录。",
            "无需执行缓存清理；保留原始资料和既有交付物不变。",
        ],
        "rerun_instructions_zh": [
            "仅重放 P3 的五类固定非业务按页 OCR control 报告。",
            "确认五个交付元数据样例、置信度汇总、失败清单和两条未排队复核路由证明。",
            "不得打开真实文件、调用 OCR 引擎、写入缓存、队列、证据或生产状态。",
        ],
        "rerun_is_in_memory_only": True,
        "cache_retention_owner": "STAGE-056",
    }


def _is_valid(
    predecessor: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
    samples: list[Mapping[str, Any]],
    confidence_report: Mapping[str, Any],
    failure_list: list[Mapping[str, Any]],
    review_route_proofs: list[Mapping[str, Any]],
    cache_rerun_instructions: Mapping[str, Any],
) -> bool:
    side_effect_free = all(predecessor.get(field) is False for field in SIDE_EFFECT_FIELDS)
    expected_ids = set(EXPECTED_SCENARIO_IDS)
    scenario_shape = (
        predecessor.get("valid") is True
        and predecessor.get("result") == P3_PASS_RESULT
        and set(scenarios) == expected_ids
        and predecessor.get("scenario_count") == 5
        and predecessor.get("passed_scenario_count") == 5
        and predecessor.get("explicit_disposition_count") == 5
        and predecessor.get("silent_drop_count") == 0
        and predecessor.get("cache_boundary_preserved") is True
        and predecessor.get("temporary_artifact_count") == 0
        and predecessor.get("cache_cleanup_action") == CACHE_CLEANUP_ACTION
        and all(item.get("expectation_met") is True for item in scenarios.values())
        and all(item.get("explicit_disposition") is True for item in scenarios.values())
        and not any(item.get("silent_drop") is True for item in scenarios.values())
        and all(item.get("symbolic_output_retained") is False for item in scenarios.values())
        and all(item.get("actual_ocr_text_created") is False for item in scenarios.values())
    )
    samples_safe = (
        len(samples) == len(EXPECTED_SCENARIO_IDS)
        and all(item.get("sample_kind") == OUTPUT_SAMPLE_KIND for item in samples)
        and all(item.get("source_page_ref") is not None for item in samples)
        and all(item.get("ocr_text_retained") is False for item in samples)
        and all(item.get("source_content_retained") is False for item in samples)
        and all(item.get("actual_ocr_output_produced") is False for item in samples)
        and all(item.get("high_trust_direct_entry_allowed") is False for item in samples)
    )
    confidence_exact = (
        confidence_report.get("scenario_count") == 5
        and confidence_report.get("confidence_counts")
        == {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1}
        and confidence_report.get("candidate_sample_count") == 2
        and confidence_report.get("degraded_review_required_count") == 2
        and confidence_report.get("explicit_failure_count") == 1
        and confidence_report.get("recognition_accuracy_evaluated") is False
        and confidence_report.get("quality_gate_evaluated") is False
        and confidence_report.get("high_trust_evidence_promoted") is False
    )
    failure_exact = (
        len(failure_list) == 1
        and failure_list[0].get("failure_id") == FAILURE_SCENARIO_ID
        and failure_list[0].get("record_kind") == FAILURE_RECORD_KIND
        and failure_list[0].get("quality_disposition")
        == "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION"
        and failure_list[0].get("evidence_promotion_performed") is False
        and failure_list[0].get("review_queue_write_performed") is False
        and failure_list[0].get("silent_drop") is False
    )
    routes_exact = (
        [item.get("scenario_id") for item in review_route_proofs]
        == list(DEGRADED_SCENARIO_IDS)
        and all(item.get("record_kind") == REVIEW_ROUTE_PROOF_KIND for item in review_route_proofs)
        and all(item.get("review_route_declared") == REVIEW_ROUTE for item in review_route_proofs)
        and all(item.get("review_required_not_queued") is True for item in review_route_proofs)
        and all(item.get("review_queue_created") is False for item in review_route_proofs)
        and all(item.get("review_queue_write_performed") is False for item in review_route_proofs)
    )
    cache_exact = (
        cache_rerun_instructions.get("cache_policy") == CACHE_POLICY
        and cache_rerun_instructions.get("temporary_artifact_count") == 0
        and cache_rerun_instructions.get("cache_storage_location_assigned") is False
        and cache_rerun_instructions.get("cleanup_action") == CACHE_CLEANUP_ACTION
        and cache_rerun_instructions.get("actual_cleanup_performed") is False
        and cache_rerun_instructions.get("rerun_is_in_memory_only") is True
        and cache_rerun_instructions.get("cache_retention_owner") == "STAGE-056"
    )
    return (
        scenario_shape
        and side_effect_free
        and samples_safe
        and confidence_exact
        and failure_exact
        and routes_exact
        and cache_exact
    )
