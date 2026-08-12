"""Stage050 P4 的非运行时提示注入标记交付投影。

本模块只重放 P3 的格式标签化 control 场景，派生结构化 parser 输出样例、
非运行时 fallback 处置记录、质量指标和失败分类。它不读取文件、不执行 parser
或 fallback，也不会写入任何运行态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage050.prompt_injection_marker.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_PROMPT_INJECTION_MARKER_CLOSEOUT_REPORT"
OUTPUT_SAMPLE_KIND = "SCHEMA_ONLY_PROMPT_MARKER_PARSE_PRODUCT_SAMPLE_NOT_EXECUTED"
FALLBACK_LOG_KIND = "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME"
PASS_RESULT = "PASS_ISOLATED_PROMPT_INJECTION_MARKER_CLOSEOUT_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE050-REVIEW-GATE"
CONTROL_FORMAT_LABELS = ("PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF")
OUTPUT_SAMPLE_SCENARIO_IDS = {
    "PDF": "pdf-ordinary-evidence",
    "DOCX": "docx-ordinary-evidence",
    "XLSX": "xlsx-ordinary-evidence",
    "CSV": "csv-low-quality-review",
    "TXT": "txt-low-quality-review",
    "PNG": "png-ordinary-evidence",
    "JPEG": "jpeg-ordinary-evidence",
    "TIFF": "tiff-ordinary-evidence",
}

FAILURE_CLASSIFICATIONS = {
    "CONTROL_CANDIDATE_EVIDENCE_ONLY": {
        "scenario_ids": {
            "pdf-ordinary-evidence",
            "docx-ordinary-evidence",
            "xlsx-ordinary-evidence",
            "png-ordinary-evidence",
            "jpeg-ordinary-evidence",
            "tiff-ordinary-evidence",
        },
        "fallback_state": "NO_RUNTIME_FALLBACK_FOR_CANDIDATE_MARKER",
    },
    "LOW_QUALITY_CONTROL_REVIEW_REQUIRED": {
        "scenario_ids": {"csv-low-quality-review", "txt-low-quality-review"},
        "fallback_state": "CONTROL_REVIEW_REQUIRED_NOT_QUEUED",
    },
    "UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY": {
        "scenario_ids": {"instruction-like-txt-evidence"},
        "fallback_state": "INSTRUCTION_TEXT_REMAINS_EVIDENCE_ONLY",
    },
    "UNKNOWN_FORMAT_NOT_ELIGIBLE": {
        "scenario_ids": {"unknown-format-not-eligible"},
        "fallback_state": "NO_RUNTIME_FALLBACK_FOR_UNKNOWN_FORMAT",
    },
    "INVALID_CONTROL_REJECTED": {
        "scenario_ids": {"bad-control-rejected"},
        "fallback_state": "NO_RUNTIME_FALLBACK_FOR_INVALID_CONTROL",
    },
}


def build_phase4_delivery_report() -> dict[str, Any]:
    """从 P3 受控场景派生 P4 交付证据，不产生外部副作用。"""

    phase3_module = _load_phase3_module()
    phase3 = phase3_module.build_phase3_scenario_report()
    scenarios = phase3["scenario_results"]
    definitions = {
        str(item["scenario_id"]): item for item in phase3_module.SCENARIOS
    }
    samples = _build_parser_output_samples(
        scenarios,
        definitions,
        phase3_module.CONTROL_PARSER_VERSION,
    )
    logs = _build_fallback_logs(scenarios, definitions)
    metrics = _build_quality_metrics(scenarios, definitions, samples, logs)
    classifications = _build_failure_classifications(scenarios)
    valid = (
        phase3["valid"]
        and len(samples) == len(CONTROL_FORMAT_LABELS)
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
        "parser_output_samples": samples,
        "fallback_log_samples": logs,
        "quality_metrics": metrics,
        "failure_classification": classifications,
        "support_boundary": {
            "control_format_labels": list(CONTROL_FORMAT_LABELS),
            "format_label_is_runtime_file_detection": False,
            "runtime_supported_formats": [],
            "unsupported_or_exception_labels": [
                "UNKNOWN",
                "CORRUPT_OR_UNREADABLE",
            ],
            "parser_runtime_available": False,
            "fallback_runtime_available": False,
            "control_format_labels_do_not_imply_runtime_support": True,
            "generic_parser_allowed": False,
        },
        "version_evidence": {
            "phase3_scenario_schema_version": phase3["schema_version"],
            "control_parser_version": phase3_module.CONTROL_PARSER_VERSION,
            "control_parser_version_is_runtime_version": False,
            "parser_configuration_change_performed": False,
            "parser_configuration_file_created": False,
            "fallback_runtime_owner": "STAGE048",
            "prompt_injection_marker_owner": "STAGE050",
        },
        "configuration_rollback": {
            "rollback_target_state": (
                "PHASE3_CONTROLLED_PROMPT_INJECTION_MARKER_SCENARIOS_RUNTIME_DISABLED"
            ),
            "configuration_change_performed": False,
            "parser_configuration_file_created": False,
            "steps": [
                "RESTORE_PHASE3_CONTROLLED_PROMPT_MARKER_SCENARIOS",
                "DISCARD_PHASE4_SCHEMA_SAMPLES_NON_RUNTIME_LOGS_METRICS_AND_CLASSIFICATIONS",
                "PRESERVE_STAGE050_PHASE1_TO_PHASE3_EVIDENCE",
                "KEEP_PARSER_FALLBACK_QUALITY_AND_PERSISTENCE_DISABLED",
                "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_LEDGER_AUDIT_AND_REPORTS",
            ],
        },
        "owner_feedback_zh": (
            "Stage050 步骤四已交付受控 parser 输出结构样例、非运行时处置记录、"
            "质量指标、失败分类、格式边界和回滚说明；未执行真实解析或提示注入标记。"
        ),
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_PROMPT_INJECTION_MARKER_CLOSEOUT_EVIDENCE",
        "next_gate": NEXT_GATE,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_selection_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "parser_output_produced": False,
        "fallback_execution_performed": False,
        "runtime_fallback_log_produced": False,
        "human_review_queue_write_performed": False,
        "runtime_prompt_injection_marker_application_performed": False,
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
    path = Path(__file__).with_name("stage050_prompt_injection_marker_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage050_p3_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage050 P3 controlled scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser_output_samples(
    scenarios: list[dict[str, Any]],
    definitions: Mapping[str, Mapping[str, object]],
    control_parser_version: str,
) -> list[dict[str, Any]]:
    by_id = {item["scenario_id"]: item for item in scenarios}
    samples = []
    for format_label in CONTROL_FORMAT_LABELS:
        scenario_id = OUTPUT_SAMPLE_SCENARIO_IDS[format_label]
        result = by_id[scenario_id]
        definition = definitions[scenario_id]
        samples.append(
            {
                "sample_id": f"schema-sample-{format_label.lower()}",
                "sample_kind": OUTPUT_SAMPLE_KIND,
                "scenario_id": scenario_id,
                "format_label": format_label,
                "control_parser_version": control_parser_version,
                "parser_output_status": definition["parser_output_status"],
                "text": None,
                "tables": [],
                "pages": [],
                "sections": [],
                "confidence": definition["parser_confidence"],
                "errors": ["CONTROL_SAMPLE_NOT_EXECUTED"],
                "parser_product_fact_level": result["parser_product_fact_level"],
                "quality_gate_state": result["quality_gate_state"],
                "source_content_retained": False,
                "source_reference_retained": False,
                "runtime_output_produced": False,
            }
        )
    return samples


def _build_fallback_logs(
    scenarios: list[dict[str, Any]],
    definitions: Mapping[str, Mapping[str, object]],
) -> list[dict[str, Any]]:
    logs = []
    for item in scenarios:
        scenario_id = item["scenario_id"]
        definition = definitions[scenario_id]
        classification = _classification_for(scenario_id)
        logs.append(
            {
                "scenario_id": scenario_id,
                "sample_kind": FALLBACK_LOG_KIND,
                "format_label": item["format_label"],
                "scenario_class": item["scenario_class"],
                "parser_output_status": definition["parser_output_status"],
                "parser_confidence": definition["parser_confidence"],
                "marker_disposition": item["marker_disposition"],
                "scenario_disposition": item["scenario_disposition"],
                "evidence_text_label": item["evidence_text_label"],
                "evidence_text_interpretation": item["evidence_text_interpretation"],
                "failure_classification": classification,
                "fallback_owner": item["fallback_owner"],
                "fallback_state": FAILURE_CLASSIFICATIONS[classification]["fallback_state"],
                "attempted": False,
                "attempt_count": 0,
                "silent_drop": False,
                "parser_switch_performed": False,
                "human_review_queue_write_performed": False,
                "runtime_log_written": False,
            }
        )
    return logs


def _build_quality_metrics(
    scenarios: list[dict[str, Any]],
    definitions: Mapping[str, Mapping[str, object]],
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
        "control_format_label_coverage_ratio": len(samples) / len(CONTROL_FORMAT_LABELS),
        "runtime_supported_format_count": 0,
        "parser_output_sample_count": len(samples),
        "fallback_log_sample_count": len(logs),
        "confidence_counts": _count_by(
            [definitions[item["scenario_id"]] for item in scenarios],
            "parser_confidence",
        ),
        "scenario_disposition_counts": _count_by(scenarios, "scenario_disposition"),
        "failure_classification_counts": _count_by(
            logs, "failure_classification"
        ),
        "parser_execution_count": 0,
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
    classifications: Mapping[str, Mapping[str, Any]],
    scenarios: list[dict[str, Any]],
) -> bool:
    covered = [
        scenario_id
        for item in classifications.values()
        for scenario_id in item["scenario_ids"]
    ]
    return set(covered) == {item["scenario_id"] for item in scenarios} and len(
        covered
    ) == len(scenarios)


def _count_by(items: list[Mapping[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item[key])
        counts[value] = counts.get(value, 0) + 1
    return counts
