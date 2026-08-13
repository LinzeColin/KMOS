"""Stage056 P4 的 OCR 缓存保留策略 metadata-only 交付证据。

模块只从 P3 的五类固定、非业务 control 场景派生交付元数据。它不读取 PDF、图片、
页面、表格、OCR 文本、缓存目录或磁盘信息，不调用 OCR 引擎，也不创建人工任务、缓存
或运行时状态。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage056.ocr_cache_retention_policy.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_OCR_CACHE_RETENTION_POLICY_DELIVERY_REPORT"
OUTPUT_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_OCR_CACHE_RETENTION_POLICY_SAMPLE_NOT_REAL_OCR"
)
FAILURE_RECORD_KIND = (
    "CONTROLLED_OCR_CACHE_RETENTION_POLICY_FAILURE_LIST_ENTRY_NOT_RUNTIME"
)
REVIEW_ROUTE_PROOF_KIND = (
    "DECLARED_OCR_CACHE_RETENTION_POLICY_REVIEW_ROUTE_PROOF_CANDIDATE_ONLY_NOT_QUEUED"
)
PASS_RESULT = "PASS_PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_OCR_CACHE_RETENTION_POLICY_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE056-REVIEW-GATE"
P3_PASS_RESULT = (
    "PASS_PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_"
    "RUNTIME_DISABLED"
)
CACHE_POLICY = "IN_MEMORY_CONTROLLED_CANDIDATE_NOT_PERSISTED"
CACHE_CLEANUP_ACTION = "NO_PHYSICAL_CACHE_CREATED_NO_CLEANUP_EXECUTED"
REVIEW_ROUTE = "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED"
FAILURE_DISPOSITION = (
    "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION"
)

EXPECTED_SCENARIO_IDS = (
    "scanned-pdf-cache-policy-control-candidate",
    "blurred-image-cache-policy-control-degraded",
    "table-image-cache-policy-control-unassessed",
    "mixed-zh-en-cache-policy-control-degraded",
    "low-quality-cache-policy-control-failed",
)
REVIEW_ROUTE_SCENARIO_IDS = (
    "blurred-image-cache-policy-control-degraded",
    "mixed-zh-en-cache-policy-control-degraded",
    "low-quality-cache-policy-control-failed",
)
FAILURE_SCENARIO_ID = "low-quality-cache-policy-control-failed"
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
SIDE_EFFECT_FIELDS = (
    "authorized_fixture_access_performed",
    "real_pdf_or_image_opened",
    "source_file_open_performed",
    "file_type_detection_performed",
    "route_evaluation_performed",
    "parser_execution_performed",
    "pdf_rasterization_performed",
    "image_processing_performed",
    "table_structure_extraction_performed",
    "language_detection_performed",
    "confidence_evaluation_performed",
    "recognition_accuracy_evaluated",
    "ocr_engine_selected",
    "ocr_engine_invocation_performed",
    "human_review_queue_write_performed",
    "human_review_task_created",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "phase4_started",
    "github_upload_performed",
)

QualityReportProvider = Callable[[], Mapping[str, Any]]


def build_ocr_cache_retention_policy_phase4_delivery_report(
    quality_report_provider: QualityReportProvider | None = None,
) -> dict[str, Any]:
    """派生可复核的 P4 交付证据；返回值只保留固定 control 元数据。"""

    provider = quality_report_provider or _load_phase3_report_provider()
    predecessor = provider()
    predecessor = predecessor if isinstance(predecessor, Mapping) else {}
    scenarios = _scenario_map(predecessor.get("scenario_results"))
    delivery_samples = _build_delivery_samples(scenarios)
    confidence_report = _build_confidence_report(scenarios)
    failure_list = _build_failure_list(scenarios)
    review_route_proofs = _build_review_route_proofs(scenarios)
    cache_rerun_instructions = _cache_rerun_instructions()
    valid = _is_valid(
        predecessor,
        scenarios,
        delivery_samples,
        confidence_report,
        failure_list,
        review_route_proofs,
        cache_rerun_instructions,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "predecessor_result": predecessor.get("result"),
        "delivery_samples": delivery_samples,
        "confidence_report": confidence_report,
        "failure_list": failure_list,
        "review_route_proofs": review_route_proofs,
        "quality_limitations_zh": [
            "本交付只来自五类固定非业务 control，不能代表真实 OCR 输出、实际缓存状态、识别准确率或业务资料质量。",
            "扫描 PDF、图片和表格类别均未打开；候选、降级和失败处置不能直接进入高可信证据层。",
            "复核路由证明只保留既有 Stage054 路由的纯内存候选状态，不代表已创建人工任务、队列、意见或结论。",
        ],
        "human_confirmation_prompts_zh": [
            {
                "prompt_id": "confirm-ocr-cache-policy-delivery-boundary",
                "text": "请业务线确认：本交付仅为 OCR 缓存保留策略 control 元数据，不可替代真实 OCR 输出、实际缓存状态或高可信证据。",
                "automatic_confirmation_performed": False,
            },
            {
                "prompt_id": "confirm-ocr-cache-policy-review-route-boundary",
                "text": "请业务线确认：低置信、中英文混合和失败 control 只保留候选复核路由，尚未创建实际人工任务。",
                "automatic_confirmation_performed": False,
            },
            {
                "prompt_id": "confirm-ocr-cache-policy-cache-boundary",
                "text": "请业务线确认：当前没有物理缓存、缓存路径或磁盘容量证明；不得以本说明触发目录扫描、删除或移动。",
                "automatic_confirmation_performed": False,
            },
        ],
        "cache_rerun_instructions": cache_rerun_instructions,
        "rollback": {
            "return_to": (
                "PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_"
                "QUALITY_SCENARIOS_RUNTIME_DISABLED"
            ),
            "revertable_artifacts": [
                "Stage056 Phase4 OCR cache retention policy delivery module",
                "Stage056 Phase4 delivery contract",
                "Stage056 Phase4 focused tests",
                "Stage056 Phase4 governance projection",
            ],
            "preserve_predecessor_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "physical_cache_change_allowed": False,
            "persistent_runtime_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
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
        "review_queue_created": False,
        "human_review_queue_write_performed": False,
        "human_review_task_created": False,
        "human_review_result_created": False,
        "actual_ocr_text_created": False,
        "actual_page_image_reference_created": False,
        "actual_failure_record_created": False,
        "cache_created": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "cache_cleanup_execution_performed": False,
        "disk_scan_performed": False,
        "cache_capacity_evaluation_performed": False,
        "actual_disk_capacity_proof_produced": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
    }


def _load_phase3_report_provider() -> QualityReportProvider:
    path = Path(__file__).with_name(
        "stage056_ocr_cache_retention_policy_quality_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage056_p3_quality_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage056 P3 quality scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_ocr_cache_retention_policy_phase3_report


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
                "artifact_class": scenario.get("artifact_class"),
                "language_profile": scenario.get("language_profile"),
                "confidence_level": scenario.get("confidence_level"),
                "cache_policy_state": scenario.get("cache_policy_state"),
                "quality_disposition": scenario.get("quality_disposition"),
                "source_content_retained": False,
                "ocr_text_retained": False,
                "actual_ocr_output_produced": False,
                "actual_cache_item_created": False,
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
        "report_kind": (
            "CONTROLLED_OCR_CACHE_RETENTION_POLICY_CONFIDENCE_SUMMARY_"
            "NOT_REAL_OCR_ACCURACY"
        ),
        "scenario_count": len(ordered),
        "confidence_counts": counts,
        "candidate_sample_count": sum(
            str(item.get("quality_disposition", "")).startswith("CANDIDATE_RETAINED")
            for item in ordered
        ),
        "declared_review_route_count": sum(
            item.get("review_route_declared") == REVIEW_ROUTE for item in ordered
        ),
        "explicit_failure_count": sum(
            item.get("quality_disposition") == FAILURE_DISPOSITION for item in ordered
        ),
        "temporary_cleanup_policy_candidate_count": len(
            {
                item.get("policy_candidate_ref")
                for item in ordered
                if item.get("temporary_cleanup_policy_candidate") is True
                and isinstance(item.get("policy_candidate_ref"), str)
            }
        ),
        "failure_automatic_cleanup_block_count": sum(
            item.get("automatic_cleanup_blocked") is True for item in ordered
        ),
        "recognition_accuracy_evaluated": False,
        "quality_gate_evaluated": False,
        "high_trust_evidence_promoted": False,
        "actual_disk_capacity_proof_produced": False,
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
            "artifact_class": scenario.get("artifact_class"),
            "quality_disposition": scenario.get("quality_disposition"),
            "failure_is_control_metadata_only": True,
            "automatic_cleanup_blocked": scenario.get("automatic_cleanup_blocked"),
            "actual_failure_record_created": False,
            "evidence_promotion_performed": False,
            "review_queue_write_performed": False,
            "silent_drop": False,
        }
    ]


def _build_review_route_proofs(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    proofs: list[dict[str, Any]] = []
    for scenario_id in REVIEW_ROUTE_SCENARIO_IDS:
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
                "human_review_task_created": False,
            }
        )
    return proofs


def _cache_rerun_instructions() -> dict[str, Any]:
    return {
        "cache_policy": CACHE_POLICY,
        "physical_cache_item_count": 0,
        "cache_storage_location_assigned": False,
        "temporary_cleanup_policy_candidate_count": 3,
        "failure_automatic_cleanup_block_count": 1,
        "cleanup_action": CACHE_CLEANUP_ACTION,
        "actual_cleanup_performed": False,
        "actual_disk_capacity_proof_produced": False,
        "cleanup_instructions_zh": [
            "当前物理缓存条目数为 0；不得扫描、删除或移动任何目录。",
            "无需执行缓存清理；三条临时候选仍需未来明确标识、owner 批准和容量批准，失败候选不得自动清理。",
        ],
        "rerun_instructions_zh": [
            "仅重放 P3 的五类固定非业务 OCR 缓存保留策略 control 报告。",
            "确认五个 metadata-only 样例、置信度汇总、失败清单和三条候选复核路由证明。",
            "不得打开真实文件、调用 OCR 引擎、扫描磁盘、写入或清理缓存、队列、审计、证据或生产状态。",
        ],
        "rerun_is_in_memory_only": True,
        "cache_retention_owner": "STAGE-056",
    }


def _is_valid(
    predecessor: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
    delivery_samples: list[Mapping[str, Any]],
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
        and predecessor.get("unique_policy_candidate_count") == 4
        and predecessor.get("cache_boundary_preserved") is True
        and predecessor.get("physical_cache_item_count") == 0
        and predecessor.get("cache_cleanup_action") == CACHE_CLEANUP_ACTION
        and predecessor.get("actual_disk_capacity_proof_produced") is False
        and predecessor.get("temporary_cleanup_policy_candidate_count") == 3
        and predecessor.get("failure_automatic_cleanup_block_count") == 1
        and all(item.get("expectation_met") is True for item in scenarios.values())
        and all(item.get("explicit_disposition") is True for item in scenarios.values())
        and not any(item.get("silent_drop") is True for item in scenarios.values())
        and all(item.get("actual_ocr_text_created") is False for item in scenarios.values())
        and all(item.get("actual_pdf_or_image_opened") is False for item in scenarios.values())
        and all(item.get("actual_cache_created") is False for item in scenarios.values())
        and all(item.get("physical_cleanup_executed") is False for item in scenarios.values())
    )
    samples_safe = (
        len(delivery_samples) == len(EXPECTED_SCENARIO_IDS)
        and all(item.get("sample_kind") == OUTPUT_SAMPLE_KIND for item in delivery_samples)
        and all(item.get("source_page_ref") is not None for item in delivery_samples)
        and all(item.get("source_content_retained") is False for item in delivery_samples)
        and all(item.get("ocr_text_retained") is False for item in delivery_samples)
        and all(item.get("actual_ocr_output_produced") is False for item in delivery_samples)
        and all(item.get("actual_cache_item_created") is False for item in delivery_samples)
        and all(
            item.get("high_trust_direct_entry_allowed") is False
            for item in delivery_samples
        )
    )
    confidence_exact = (
        confidence_report.get("scenario_count") == 5
        and confidence_report.get("confidence_counts")
        == {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1}
        and confidence_report.get("candidate_sample_count") == 2
        and confidence_report.get("declared_review_route_count") == 3
        and confidence_report.get("explicit_failure_count") == 1
        and confidence_report.get("temporary_cleanup_policy_candidate_count") == 3
        and confidence_report.get("failure_automatic_cleanup_block_count") == 1
        and confidence_report.get("recognition_accuracy_evaluated") is False
        and confidence_report.get("quality_gate_evaluated") is False
        and confidence_report.get("high_trust_evidence_promoted") is False
        and confidence_report.get("actual_disk_capacity_proof_produced") is False
    )
    failure_exact = (
        len(failure_list) == 1
        and failure_list[0].get("failure_id") == FAILURE_SCENARIO_ID
        and failure_list[0].get("record_kind") == FAILURE_RECORD_KIND
        and failure_list[0].get("quality_disposition") == FAILURE_DISPOSITION
        and failure_list[0].get("automatic_cleanup_blocked") is True
        and failure_list[0].get("actual_failure_record_created") is False
        and failure_list[0].get("evidence_promotion_performed") is False
        and failure_list[0].get("review_queue_write_performed") is False
        and failure_list[0].get("silent_drop") is False
    )
    routes_exact = (
        [item.get("scenario_id") for item in review_route_proofs]
        == list(REVIEW_ROUTE_SCENARIO_IDS)
        and all(
            item.get("record_kind") == REVIEW_ROUTE_PROOF_KIND
            for item in review_route_proofs
        )
        and all(
            item.get("review_route_declared") == REVIEW_ROUTE
            for item in review_route_proofs
        )
        and all(
            item.get("review_required_not_queued") is True
            for item in review_route_proofs
        )
        and all(
            item.get("review_queue_created") is False for item in review_route_proofs
        )
        and all(
            item.get("review_queue_write_performed") is False
            for item in review_route_proofs
        )
        and all(
            item.get("human_review_task_created") is False
            for item in review_route_proofs
        )
    )
    cache_exact = (
        cache_rerun_instructions.get("cache_policy") == CACHE_POLICY
        and cache_rerun_instructions.get("physical_cache_item_count") == 0
        and cache_rerun_instructions.get("cache_storage_location_assigned") is False
        and cache_rerun_instructions.get("temporary_cleanup_policy_candidate_count") == 3
        and cache_rerun_instructions.get("failure_automatic_cleanup_block_count") == 1
        and cache_rerun_instructions.get("cleanup_action") == CACHE_CLEANUP_ACTION
        and cache_rerun_instructions.get("actual_cleanup_performed") is False
        and cache_rerun_instructions.get("actual_disk_capacity_proof_produced") is False
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
