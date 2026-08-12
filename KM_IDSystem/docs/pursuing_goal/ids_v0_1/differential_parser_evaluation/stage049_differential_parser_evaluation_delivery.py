"""Stage049 P4 的非运行时差异化解析评估交付投影。

本模块只重放 P3 的格式标签化 control 场景，派生候选解析产物结构样例、
非运行时处置记录、质量指标和失败分类。它不读取文件、不比较解析正文、
不执行 parser 或 fallback，也不会写入任何运行态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage049.differential_parser_evaluation.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_DIFFERENTIAL_PARSER_EVALUATION_CLOSEOUT_REPORT"
OUTPUT_SAMPLE_KIND = "SCHEMA_ONLY_CANDIDATE_PARSE_PRODUCT_SAMPLE_NOT_EXECUTED"
FALLBACK_LOG_KIND = "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME"
PASS_RESULT = "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE049-REVIEW-GATE"
CONTROL_FORMAT_LABELS = ("PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF")

FAILURE_CLASSIFICATIONS = {
    "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW": {
        "scenario_ids": {
            "pdf-control-candidates",
            "docx-control-candidates",
            "xlsx-control-candidates",
            "png-control-candidates",
            "jpeg-control-candidates",
            "tiff-control-candidates",
        },
        "fallback_state": "QUALITY_REVIEW_BOUNDARY_RETAINED_NOT_QUEUED",
    },
    "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED": {
        "scenario_ids": {
            "csv-low-quality-review",
            "txt-low-quality-review",
        },
        "fallback_state": "CONTROL_REVIEW_REQUIRED_NOT_QUEUED",
    },
    "UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY": {
        "scenario_ids": {"instruction-like-txt-review"},
        "fallback_state": "CONTROL_REVIEW_REQUIRED_NOT_QUEUED",
    },
    "CONTROL_CONTEXT_MISMATCH_NOT_ELIGIBLE": {
        "scenario_ids": {"unknown-context-mismatch"},
        "fallback_state": "NO_COMPARISON_OR_FALLBACK_FOR_CONTEXT_MISMATCH",
    },
    "INVALID_CONTROL_REJECTED": {
        "scenario_ids": {"corrupt-invalid-control"},
        "fallback_state": "NO_COMPARISON_OR_FALLBACK_FOR_INVALID_CONTROL",
    },
}


def build_phase4_delivery_report() -> dict[str, Any]:
    """从 P3 受控场景派生 P4 交付证据，不产生外部副作用。"""

    phase3 = _load_phase3_module().build_phase3_scenario_report()
    scenarios = phase3["scenario_results"]
    samples = _build_candidate_parse_product_samples(scenarios)
    logs = _build_control_disposition_logs(scenarios)
    metrics = _build_quality_metrics(scenarios, samples, logs)
    classifications = _build_failure_classifications(scenarios)
    valid = (
        phase3["valid"]
        and len(samples) == 20
        and len(logs) == len(scenarios)
        and metrics["scenario_count"] == len(scenarios)
        and metrics["passed_scenario_count"] == len(scenarios)
        and metrics["explicit_disposition_count"] == len(scenarios)
        and metrics["silent_drop_count"] == 0
        and metrics["parser_execution_count"] == 0
        and metrics["fallback_execution_count"] == 0
        and metrics["quality_gate_evaluation_count"] == 0
        and _classification_coverage_is_complete(classifications, scenarios)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "phase3_result": phase3["result"],
        "candidate_parse_product_samples": samples,
        "fallback_log_samples": logs,
        "quality_metrics": metrics,
        "failure_classification": classifications,
        "support_boundary": {
            "control_format_labels": list(CONTROL_FORMAT_LABELS),
            "format_label_is_runtime_file_detection": False,
            "runtime_supported_formats": [],
            "unsupported_or_exception_labels": ["UNKNOWN", "CORRUPT_OR_UNREADABLE"],
            "parser_runtime_available": False,
            "differential_comparison_runtime_available": False,
            "fallback_runtime_available": False,
            "control_format_labels_do_not_imply_runtime_support": True,
            "generic_parser_allowed": False,
        },
        "version_evidence": {
            "control_candidate_parser_version_family": "ids.parser.control_fixture.v0_1.stage049.p2",
            "control_candidate_versions_per_non_invalid_scenario": 2,
            "control_candidate_parser_versions_are_runtime_versions": False,
            "parser_configuration_change_performed": False,
            "parser_configuration_file_created": False,
            "fallback_runtime_owner": "STAGE048",
            "differential_evaluation_owner": "STAGE049",
            "prompt_injection_marker_owner": "STAGE050",
        },
        "configuration_rollback": {
            "rollback_target_state": "PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED",
            "configuration_change_performed": False,
            "parser_configuration_file_created": False,
            "steps": [
                "RESTORE_PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS",
                "DISCARD_PHASE4_SCHEMA_SAMPLES_NON_RUNTIME_LOGS_METRICS_AND_CLASSIFICATIONS",
                "PRESERVE_STAGE049_PHASE1_TO_PHASE3_EVIDENCE",
                "KEEP_PARSER_FALLBACK_QUALITY_AND_PERSISTENCE_DISABLED",
                "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_LEDGER_AUDIT_AND_REPORTS",
            ],
        },
        "owner_feedback_zh": (
            "Stage049 步骤四已交付受控候选解析产物结构样例、非运行时处置记录、"
            "质量指标、失败分类、格式边界和回滚说明；未执行真实解析或候选正文比较。"
        ),
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_DIFFERENTIAL_EVALUATION_CLOSEOUT_EVIDENCE",
        "next_gate": NEXT_GATE,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_selection_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "parser_output_produced": False,
        "actual_parse_product_comparison_performed": False,
        "fallback_execution_performed": False,
        "runtime_fallback_log_produced": False,
        "human_review_queue_write_performed": False,
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


def _load_phase3_module():
    path = Path(__file__).with_name("stage049_differential_parser_evaluation_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage049_p3_scenarios", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_candidate_parse_product_samples(
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    samples = []
    for scenario in scenarios:
        versions = scenario["candidate_parser_versions"]
        confidences = scenario["candidate_parser_confidences"]
        for position, (version, confidence) in enumerate(zip(versions, confidences), 1):
            samples.append(
                {
                    "sample_id": f"schema-sample-{scenario['scenario_id']}-{position}",
                    "sample_kind": OUTPUT_SAMPLE_KIND,
                    "scenario_id": scenario["scenario_id"],
                    "format_label": scenario["format_label"],
                    "candidate_position": position,
                    "parser_version": version,
                    "confidence": confidence,
                    "comparison_disposition": scenario["comparison_disposition"],
                    "parser_product_fact_level": scenario["parser_product_fact_level"],
                    "quality_gate_state": scenario["quality_gate_state"],
                    "text": None,
                    "tables": [],
                    "pages": [],
                    "sections": [],
                    "errors": ["CONTROL_SAMPLE_NOT_EXECUTED"],
                    "source_content_retained": False,
                    "source_reference_retained": False,
                    "runtime_output_produced": False,
                }
            )
    return samples


def _build_control_disposition_logs(
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": item["scenario_id"],
            "sample_kind": FALLBACK_LOG_KIND,
            "format_label": item["format_label"],
            "scenario_class": item["scenario_class"],
            "comparison_disposition": item["comparison_disposition"],
            "human_feedback_code": item["human_feedback_code"],
            "failure_classification": _classification_for(item["scenario_id"]),
            "fallback_owner": item["fallback_owner"],
            "fallback_state": FAILURE_CLASSIFICATIONS[
                _classification_for(item["scenario_id"])
            ]["fallback_state"],
            "attempted": False,
            "attempt_count": 0,
            "silent_drop": False,
            "parser_switch_performed": False,
            "human_review_queue_write_performed": False,
            "quality_gate_state": item["quality_gate_state"],
            "runtime_log_written": False,
        }
        for item in scenarios
    ]


def _build_quality_metrics(
    scenarios: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_count": len(scenarios),
        "passed_scenario_count": sum(item["expectation_met"] for item in scenarios),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] for item in scenarios
        ),
        "silent_drop_count": sum(item["silent_drop"] for item in scenarios),
        "control_format_label_count": len(CONTROL_FORMAT_LABELS),
        "control_format_label_coverage_ratio": len(
            {item["format_label"] for item in scenarios if item["format_label"] in CONTROL_FORMAT_LABELS}
        )
        / len(CONTROL_FORMAT_LABELS),
        "runtime_supported_format_count": 0,
        "eligible_control_scenario_count": sum(
            item["comparison_disposition"]
            in {
                "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
                "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
            }
            for item in scenarios
        ),
        "control_context_mismatch_count": sum(
            item["comparison_disposition"]
            == "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH"
            for item in scenarios
        ),
        "invalid_control_count": sum(
            item["comparison_disposition"] == "COMPARISON_INVALID_CONTROL_REJECTED"
            for item in scenarios
        ),
        "candidate_parse_product_sample_count": len(samples),
        "fallback_log_sample_count": len(logs),
        "candidate_confidence_counts": _count_by(samples, "confidence"),
        "comparison_disposition_counts": _count_by(
            scenarios, "comparison_disposition"
        ),
        "failure_classification_counts": _count_by(logs, "failure_classification"),
        "parser_execution_count": 0,
        "actual_parse_product_comparison_count": 0,
        "fallback_execution_count": 0,
        "quality_gate_evaluation_count": 0,
        "persistent_write_count": 0,
    }


def _build_failure_classifications(
    scenarios: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    classifications = {}
    for name, specification in FAILURE_CLASSIFICATIONS.items():
        scenario_ids = [
            item["scenario_id"]
            for item in scenarios
            if item["scenario_id"] in specification["scenario_ids"]
        ]
        classifications[name] = {
            "scenario_ids": scenario_ids,
            "fallback_state": specification["fallback_state"],
            "fail_closed": True,
            "fallback_execution_performed": False,
        }
    return classifications


def _classification_for(scenario_id: str) -> str:
    return next(
        name
        for name, specification in FAILURE_CLASSIFICATIONS.items()
        if scenario_id in specification["scenario_ids"]
    )


def _classification_coverage_is_complete(
    classifications: dict[str, dict[str, Any]], scenarios: list[dict[str, Any]]
) -> bool:
    covered = [
        scenario_id
        for item in classifications.values()
        for scenario_id in item["scenario_ids"]
    ]
    return set(covered) == {item["scenario_id"] for item in scenarios} and len(
        covered
    ) == len(scenarios)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item[key]
        counts[value] = counts.get(value, 0) + 1
    return counts
