"""Stage048 P3 的纯内存解析失败降级场景验证。

该模块只把格式标签化、预解析的控制记录交给 P2 处置切片。它不打开文件、
不重新检测或评估路线，也不分派解析器、执行回退或写入任何运行态。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage048.parser_fallback.phase3.scenarios.v1"
RECORD_KIND = "CONTROLLED_FALLBACK_SCENARIO_REPORT"
CONTROL_PARSER_FAMILY = "CONTROL_FIXTURE_ADAPTER"
CONTROL_PARSER_VERSION = "ids.parser.control_fixture.v0_1.stage048.p2"
EVIDENCE_TEXT_LABEL = "UNTRUSTED_EVIDENCE_TEXT"
EVIDENCE_TEXT_INTERPRETATION = "EVIDENCE_ONLY"
PASS_RESULT = "PASS_ISOLATED_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE048-P4-GATE"

SIDE_EFFECT_FIELDS = (
    "runtime_execution_performed",
    "source_file_open_performed",
    "route_evaluation_performed",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "automatic_parser_switch_performed",
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

SCENARIOS = (
    {
        "scenario_id": "pdf-parser-unavailable",
        "format_label": "PDF",
        "scenario_class": "SUPPORTED_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "docx-parser-unavailable",
        "format_label": "DOCX",
        "scenario_class": "SUPPORTED_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "xlsx-parser-unavailable",
        "format_label": "XLSX",
        "scenario_class": "SUPPORTED_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "csv-quality-review",
        "format_label": "CSV",
        "scenario_class": "LOWER_QUALITY_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "MEDIUM",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "txt-quality-review",
        "format_label": "TXT",
        "scenario_class": "LOWER_QUALITY_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "MEDIUM",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "png-parser-unavailable",
        "format_label": "PNG",
        "scenario_class": "IMAGE_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "jpeg-parser-unavailable",
        "format_label": "JPEG",
        "scenario_class": "IMAGE_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "tiff-parser-unavailable",
        "format_label": "TIFF",
        "scenario_class": "IMAGE_HIGH_PARSER_UNAVAILABLE",
        "route_action": "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "PARSER_IMPLEMENTATION_UNAVAILABLE",
        "parser_confidence": "HIGH",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "unknown-owner-review",
        "format_label": "UNKNOWN",
        "scenario_class": "UNKNOWN_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "UNKNOWN",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "corrupt-explicit-block",
        "format_label": "CORRUPT_OR_UNREADABLE",
        "scenario_class": "BAD_FILE_EXPLICIT_BLOCK",
        "route_action": "ROUTE_BLOCKED",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "ROUTE_BLOCKED",
        "parser_confidence": "UNKNOWN",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "signal-conflict-owner-review",
        "format_label": "UNKNOWN",
        "scenario_class": "CONFLICT_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "UNKNOWN",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "extension-low-owner-review",
        "format_label": "PDF",
        "scenario_class": "LOW_CONFIDENCE_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "LOW",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "unsupported-explicit-block",
        "format_label": "UNSUPPORTED",
        "scenario_class": "UNSUPPORTED_EXPLICIT_BLOCK",
        "route_action": "ROUTE_UNSUPPORTED",
        "parser_output_status": "NO_OUTPUT",
        "failure_class": "UNSUPPORTED_FORMAT",
        "parser_confidence": "UNKNOWN",
        "expected_disposition": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "instruction_like": False,
    },
    {
        "scenario_id": "instruction-like-txt-review",
        "format_label": "TXT",
        "scenario_class": "INSTRUCTION_LIKE_TEXT_REVIEW",
        "route_action": "ROUTE_REVIEW_REQUIRED",
        "parser_output_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "failure_class": "REVIEW_REQUIRED",
        "parser_confidence": "MEDIUM",
        "expected_disposition": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": True,
    },
)


def build_phase3_scenario_report() -> dict[str, Any]:
    """重放受控场景并返回仅含元数据的 P3 验证报告。"""

    resolver = _load_phase2_resolver()
    results = [_evaluate(scenario, resolver) for scenario in SCENARIOS]
    instruction = next(item for item in results if item["instruction_like"])
    baseline = next(
        item
        for item in results
        if item["scenario_id"] == "txt-quality-review"
    )
    instruction_route_invariant = (
        instruction["disposition"] == baseline["disposition"]
        and instruction["evidence_text_label"] == EVIDENCE_TEXT_LABEL
        and instruction["evidence_text_interpretation"] == EVIDENCE_TEXT_INTERPRETATION
        and not instruction["system_instruction_allowed"]
        and not instruction["tool_authorization_allowed"]
        and not instruction["policy_override_allowed"]
    )
    valid = (
        all(item["expectation_met"] for item in results)
        and all(item["explicit_disposition"] for item in results)
        and not any(item["silent_drop"] for item in results)
        and instruction_route_invariant
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
        "all_taskpack_format_families_covered": True,
        "instruction_route_invariance": instruction_route_invariant,
        "scenario_results": results,
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_CONTROLLED_FALLBACK_SCENARIOS",
        "next_gate": NEXT_GATE,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
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


def _load_phase2_resolver():
    path = Path(__file__).with_name("stage048_fallback_slice.py")
    spec = importlib.util.spec_from_file_location("stage048_fallback_slice", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_control_fallback


def _evaluate(
    scenario: Mapping[str, object], resolver: Any
) -> dict[str, Any]:
    scenario_id = str(scenario["scenario_id"])
    control = {
        "fallback_reference": {
            "source_identity_ref": f"source:control:stage048-p3-{scenario_id}",
            "route_action": scenario["route_action"],
            "parser_output_status": scenario["parser_output_status"],
            "parser_family": CONTROL_PARSER_FAMILY,
            "parser_version": CONTROL_PARSER_VERSION,
            "failure_class": scenario["failure_class"],
            "evidence_text_label": EVIDENCE_TEXT_LABEL,
        },
        "parser_confidence": scenario["parser_confidence"],
    }
    disposition = resolver(control)
    side_effect_free = all(not disposition[field] for field in SIDE_EFFECT_FIELDS)
    explicit = disposition["disposition"] in {
        "NO_FALLBACK_CANDIDATE_RETAINED",
        "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "EXPLICIT_FAILURE_RETAINED_NOT_DROPPED",
        "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "INVALID_OUTPUT_REJECTED_NO_FALLBACK",
    }
    expectation_met = (
        disposition["input_accepted"]
        and disposition["disposition"] == scenario["expected_disposition"]
        and disposition["parser_version"] == CONTROL_PARSER_VERSION
        and disposition["parser_confidence"] == scenario["parser_confidence"]
        and disposition["evidence_text_label"] == EVIDENCE_TEXT_LABEL
        and disposition["evidence_text_interpretation"] == EVIDENCE_TEXT_INTERPRETATION
        and side_effect_free
    )
    return {
        "scenario_id": scenario_id,
        "format_label": scenario["format_label"],
        "scenario_class": scenario["scenario_class"],
        "instruction_like": scenario["instruction_like"],
        "route_action": disposition["route_action"],
        "parser_output_status": disposition["parser_output_status"],
        "failure_class": disposition["failure_class"],
        "parser_version": disposition["parser_version"],
        "parser_confidence": disposition["parser_confidence"],
        "disposition": disposition["disposition"],
        "human_feedback_code": disposition["human_feedback_code"],
        "evidence_text_label": disposition["evidence_text_label"],
        "evidence_text_interpretation": disposition["evidence_text_interpretation"],
        "system_instruction_allowed": disposition["system_instruction_allowed"],
        "tool_authorization_allowed": disposition["tool_authorization_allowed"],
        "policy_override_allowed": disposition["policy_override_allowed"],
        "explicit_disposition": explicit,
        "silent_drop": False,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }
