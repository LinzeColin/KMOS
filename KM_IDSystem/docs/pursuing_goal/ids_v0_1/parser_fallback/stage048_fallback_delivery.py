"""Stage048 P4 的非运行时解析失败降级交付投影。

本模块重放 P3 的受控场景报告，派生仅结构的 parser 输出样例、非运行时
处置记录、质量指标和失败分类。它不读取文件、不执行 parser 或 fallback，
也不写入任何运行态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage048.parser_fallback.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_FALLBACK_CLOSEOUT_REPORT"
OUTPUT_SAMPLE_KIND = "SCHEMA_ONLY_PARSER_OUTPUT_SAMPLE_NOT_EXECUTED"
FALLBACK_LOG_KIND = "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME"
PASS_RESULT = "PASS_ISOLATED_FALLBACK_CLOSEOUT_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE048-REVIEW-GATE"
SUPPORTED_FORMATS = ("PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF")

FAILURE_CLASSIFICATIONS = {
    "PARSER_IMPLEMENTATION_UNAVAILABLE": {
        "scenario_ids": {
            "pdf-parser-unavailable",
            "docx-parser-unavailable",
            "xlsx-parser-unavailable",
            "png-parser-unavailable",
            "jpeg-parser-unavailable",
            "tiff-parser-unavailable",
        },
        "disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "fallback_state": "NO_RUNTIME_PARSER_OR_FALLBACK",
    },
    "QUALITY_REVIEW_REQUIRED": {
        "scenario_ids": {"csv-quality-review", "txt-quality-review"},
        "disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "fallback_state": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
    },
    "OWNER_REVIEW_REQUIRED": {
        "scenario_ids": {
            "unknown-owner-review",
            "signal-conflict-owner-review",
            "extension-low-owner-review",
        },
        "disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "fallback_state": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
    },
    "EXPLICIT_INPUT_BLOCKED": {
        "scenario_ids": {"corrupt-explicit-block"},
        "disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "fallback_state": "NO_FALLBACK_EXPLICITLY_RETAINED",
    },
    "UNSUPPORTED_FORMAT": {
        "scenario_ids": {"unsupported-explicit-block"},
        "disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "fallback_state": "NO_FALLBACK_EXPLICITLY_RETAINED",
    },
    "UNTRUSTED_INSTRUCTION_TEXT_REVIEW": {
        "scenario_ids": {"instruction-like-txt-review"},
        "disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "fallback_state": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
    },
}


def build_phase4_delivery_report() -> dict[str, Any]:
    """从 P3 受控场景派生 P4 交付证据，不产生外部副作用。"""

    phase3 = _load_phase3_module().build_phase3_scenario_report()
    scenarios = phase3["scenario_results"]
    samples = _build_parser_output_samples(scenarios)
    logs = _build_fallback_logs(scenarios)
    metrics = _build_quality_metrics(scenarios, samples, logs)
    classifications = _build_failure_classifications(scenarios)
    valid = (
        phase3["valid"]
        and len(samples) == len(SUPPORTED_FORMATS)
        and len(logs) == len(scenarios)
        and metrics["scenario_count"] == len(scenarios)
        and metrics["passed_scenario_count"] == len(scenarios)
        and metrics["explicit_disposition_count"] == len(scenarios)
        and metrics["silent_drop_count"] == 0
        and metrics["parser_execution_count"] == 0
        and metrics["fallback_execution_count"] == 0
        and _classification_coverage_is_complete(classifications, scenarios)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "phase3_result": phase3["result"],
        "parser_output_samples": samples,
        "fallback_log_samples": logs,
        "quality_metrics": metrics,
        "failure_classification": classifications,
        "support_boundary": {
            "control_supported_formats": list(SUPPORTED_FORMATS),
            "runtime_supported_formats": [],
            "unsupported_or_exception_labels": [
                "UNKNOWN",
                "CORRUPT_OR_UNREADABLE",
                "UNSUPPORTED",
            ],
            "parser_runtime_available": False,
            "fallback_runtime_available": False,
            "control_support_does_not_imply_runtime_support": True,
            "generic_parser_allowed": False,
        },
        "version_evidence": {
            "phase3_scenario_schema_version": phase3["schema_version"],
            "control_parser_version": "ids.parser.control_fixture.v0_1.stage048.p2",
            "control_parser_versions_are_runtime_versions": False,
            "parser_configuration_change_performed": False,
            "fallback_runtime_owner": "STAGE-048",
            "differential_evaluation_owner": "STAGE-049",
            "prompt_injection_marker_owner": "STAGE-050",
        },
        "configuration_rollback": {
            "rollback_target_state": "PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED",
            "configuration_change_performed": False,
            "parser_configuration_file_created": False,
            "steps": [
                "RESTORE_PHASE3_CONTROLLED_SCENARIOS",
                "DISCARD_PHASE4_SCHEMA_SAMPLES_NON_RUNTIME_LOGS_METRICS_AND_CLASSIFICATIONS",
                "PRESERVE_STAGE048_PHASE1_TO_PHASE3_EVIDENCE",
                "KEEP_PARSER_FALLBACK_QUALITY_AND_PERSISTENCE_DISABLED",
                "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_LEDGER_AUDIT_AND_REPORTS",
            ],
        },
        "owner_feedback_zh": (
            "Stage048 步骤四已交付受控场景的结构样例、非运行时处置记录、"
            "质量指标、失败分类、格式边界和回滚说明；未执行真实解析器或回退。"
        ),
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_FALLBACK_CLOSEOUT_EVIDENCE",
        "next_gate": NEXT_GATE,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "parser_output_produced": False,
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
    path = Path(__file__).with_name("stage048_fallback_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage048_fallback_scenarios", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser_output_samples(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples = []
    for format_label in SUPPORTED_FORMATS:
        scenario = next(
            item for item in scenarios if item["format_label"] == format_label
        )
        samples.append(
            {
                "sample_id": f"schema-sample-{format_label.lower()}",
                "sample_kind": OUTPUT_SAMPLE_KIND,
                "format_label": format_label,
                "scenario_id": scenario["scenario_id"],
                "parser_version": scenario["parser_version"],
                "parser_output_status": scenario["parser_output_status"],
                "text": None,
                "tables": [],
                "pages": [],
                "sections": [],
                "confidence": scenario["parser_confidence"],
                "errors": ["CONTROL_SAMPLE_NOT_EXECUTED"],
                "runtime_output_produced": False,
                "source_content_retained": False,
            }
        )
    return samples


def _build_fallback_logs(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": item["scenario_id"],
            "sample_kind": FALLBACK_LOG_KIND,
            "format_label": item["format_label"],
            "scenario_class": item["scenario_class"],
            "parser_output_status": item["parser_output_status"],
            "parser_version": item["parser_version"],
            "parser_confidence": item["parser_confidence"],
            "disposition": item["disposition"],
            "human_feedback_code": item["human_feedback_code"],
            "failure_classification": _classification_for(item["scenario_id"]),
            "fallback_state": FAILURE_CLASSIFICATIONS[
                _classification_for(item["scenario_id"])
            ]["fallback_state"],
            "attempted": False,
            "attempt_count": 0,
            "silent_drop": False,
            "parser_switch_performed": False,
            "human_review_queue_write_performed": False,
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
        "control_supported_format_count": len(SUPPORTED_FORMATS),
        "control_supported_format_coverage_ratio": len(samples) / len(SUPPORTED_FORMATS),
        "runtime_supported_format_count": 0,
        "parser_output_sample_count": len(samples),
        "fallback_log_sample_count": len(logs),
        "confidence_counts": _count_by(scenarios, "parser_confidence"),
        "disposition_counts": _count_by(scenarios, "disposition"),
        "failure_classification_counts": _count_by(
            logs, "failure_classification"
        ),
        "parser_execution_count": 0,
        "fallback_execution_count": 0,
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
            "disposition": specification["disposition"],
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
