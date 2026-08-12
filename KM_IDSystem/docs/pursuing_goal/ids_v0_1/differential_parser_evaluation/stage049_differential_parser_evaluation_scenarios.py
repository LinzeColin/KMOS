"""Stage049 P3 的格式标签化差异化评估受控场景。

本模块仅重放 Stage049 P2 的两个 reference-only control 候选资格处置。
格式标签是受控元数据，不能被视为文件、签名、路线或解析输出；模块不打开文件，
不重新评估路线，不执行 parser 或 fallback，也不比较解析正文。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage049.differential_parser_evaluation.phase3.scenarios.v1"
RECORD_KIND = "CONTROLLED_DIFFERENTIAL_PARSER_EVALUATION_SCENARIO_REPORT"
PARSER_PRODUCT_FACT_LEVEL = "CANDIDATE"
QUALITY_GATE_INITIAL_STATE = "UNASSESSED"
EVIDENCE_TEXT_LABEL = "UNTRUSTED_EVIDENCE_TEXT"
EVIDENCE_TEXT_INTERPRETATION = "EVIDENCE_ONLY"
PASS_RESULT = "PASS_ISOLATED_CONTROLLED_DIFFERENTIAL_EVALUATION_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE049-P4-GATE"

SIDE_EFFECT_FIELDS = (
    "actual_parse_product_comparison_performed",
    "actual_candidate_parse_product_created",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "route_evaluation_performed",
    "parser_selection_performed",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "automatic_parser_switch_performed",
    "human_review_queue_write_performed",
    "prompt_injection_marker_application_performed",
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
        "scenario_id": "pdf-control-candidates",
        "format_label": "PDF",
        "scenario_class": "FORMAT_LABELLED_HIGH_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "docx-control-candidates",
        "format_label": "DOCX",
        "scenario_class": "FORMAT_LABELLED_HIGH_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "xlsx-control-candidates",
        "format_label": "XLSX",
        "scenario_class": "FORMAT_LABELLED_HIGH_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "csv-low-quality-review",
        "format_label": "CSV",
        "scenario_class": "FORMAT_LABELLED_LOW_QUALITY_CONTROL",
        "first_confidence": "LOW",
        "second_confidence": "LOW",
        "first_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "second_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "txt-low-quality-review",
        "format_label": "TXT",
        "scenario_class": "FORMAT_LABELLED_LOW_QUALITY_CONTROL",
        "first_confidence": "MEDIUM",
        "second_confidence": "LOW",
        "first_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "second_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": False,
    },
    {
        "scenario_id": "png-control-candidates",
        "format_label": "PNG",
        "scenario_class": "FORMAT_LABELLED_IMAGE_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "jpeg-control-candidates",
        "format_label": "JPEG",
        "scenario_class": "FORMAT_LABELLED_IMAGE_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "tiff-control-candidates",
        "format_label": "TIFF",
        "scenario_class": "FORMAT_LABELLED_IMAGE_CONTROL",
        "first_confidence": "HIGH",
        "second_confidence": "HIGH",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "instruction_like": False,
    },
    {
        "scenario_id": "unknown-context-mismatch",
        "format_label": "UNKNOWN",
        "scenario_class": "FORMAT_LABELLED_UNKNOWN_CONTROL",
        "first_confidence": "UNKNOWN",
        "second_confidence": "UNKNOWN",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "CONTROL_CONTEXT_MISMATCH",
        "expected_disposition": "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
        "instruction_like": False,
    },
    {
        "scenario_id": "corrupt-invalid-control",
        "format_label": "CORRUPT_OR_UNREADABLE",
        "scenario_class": "FORMAT_LABELLED_BAD_CONTROL",
        "first_confidence": "UNKNOWN",
        "second_confidence": "UNKNOWN",
        "first_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "second_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "control_shape": "INVALID_CONTROL",
        "expected_disposition": "COMPARISON_INVALID_CONTROL_REJECTED",
        "instruction_like": False,
    },
    {
        "scenario_id": "instruction-like-txt-review",
        "format_label": "TXT",
        "scenario_class": "INSTRUCTION_LIKE_TEXT_CONTROL",
        "first_confidence": "MEDIUM",
        "second_confidence": "LOW",
        "first_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "second_status": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "control_shape": "VALID_SHARED_CONTEXT",
        "expected_disposition": "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "instruction_like": True,
    },
)


def build_phase3_scenario_report() -> dict[str, Any]:
    """重放 P2 受控资格处置并返回不含业务内容的 P3 报告。"""

    resolver = _load_phase2_resolver()
    results = [_evaluate(scenario, resolver) for scenario in SCENARIOS]
    instruction = next(item for item in results if item["instruction_like"])
    txt_baseline = next(
        item for item in results if item["scenario_id"] == "txt-low-quality-review"
    )
    instruction_disposition_invariance = (
        instruction["comparison_disposition"] == txt_baseline["comparison_disposition"]
        and instruction["human_feedback_code"] == txt_baseline["human_feedback_code"]
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
        and instruction_disposition_invariance
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
        "taskpack_format_families_covered": True,
        "image_variant_count": 3,
        "low_quality_review_scenario_count": sum(
            item["comparison_disposition"]
            == "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED"
            for item in results
        ),
        "ineligible_or_invalid_scenario_count": sum(
            item["comparison_disposition"]
            in {
                "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
                "COMPARISON_INVALID_CONTROL_REJECTED",
            }
            for item in results
        ),
        "instruction_disposition_invariance": instruction_disposition_invariance,
        "scenario_results": results,
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_CONTROLLED_DIFFERENTIAL_SCENARIOS",
        "next_gate": NEXT_GATE,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_selection_performed": False,
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
    path = Path(__file__).with_name("stage049_differential_parser_evaluation_slice.py")
    spec = importlib.util.spec_from_file_location("stage049_differential_slice", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage049 P2 control slice is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_controlled_differential_eligibility


def _evaluate(
    scenario: Mapping[str, object], resolver: Any
) -> dict[str, Any]:
    control = _control_input(scenario)
    disposition = resolver(control)
    side_effect_free = all(not disposition[field] for field in SIDE_EFFECT_FIELDS)
    explicit = disposition["comparison_disposition"] in {
        "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
        "COMPARISON_INVALID_CONTROL_REJECTED",
    }
    expectation_met = (
        disposition["comparison_disposition"] == scenario["expected_disposition"]
        and disposition["evidence_text_label"] == EVIDENCE_TEXT_LABEL
        and disposition["evidence_text_interpretation"] == EVIDENCE_TEXT_INTERPRETATION
        and side_effect_free
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "format_label": str(scenario["format_label"]),
        "scenario_class": str(scenario["scenario_class"]),
        "instruction_like": bool(scenario["instruction_like"]),
        "format_label_is_control_metadata": True,
        "control_shape": str(scenario["control_shape"]),
        "candidate_parser_versions": disposition["candidate_parser_versions"],
        "candidate_parser_confidences": disposition["candidate_parser_confidences"],
        "comparison_disposition": disposition["comparison_disposition"],
        "human_feedback_code": disposition["human_feedback_code"],
        "human_feedback": disposition["human_feedback"],
        "evidence_text_label": disposition["evidence_text_label"],
        "evidence_text_interpretation": disposition["evidence_text_interpretation"],
        "system_instruction_allowed": disposition["system_instruction_allowed"],
        "tool_authorization_allowed": disposition["tool_authorization_allowed"],
        "policy_override_allowed": disposition["policy_override_allowed"],
        "parser_product_fact_level": PARSER_PRODUCT_FACT_LEVEL,
        "quality_gate_state": QUALITY_GATE_INITIAL_STATE,
        "fallback_owner": "STAGE048",
        "fallback_execution_performed": disposition["fallback_execution_performed"],
        "actual_route_validation_performed": False,
        "actual_parse_product_comparison_performed": disposition[
            "actual_parse_product_comparison_performed"
        ],
        "explicit_disposition": explicit,
        "silent_drop": False,
        "side_effect_free": side_effect_free,
        "expectation_met": expectation_met,
    }


def _control_input(scenario: Mapping[str, object]) -> dict[str, object]:
    if scenario["control_shape"] == "INVALID_CONTROL":
        return {"candidate_controls": [], "invalid_control_marker": "P3_CONTROL"}

    scenario_id = str(scenario["scenario_id"])
    first_source = f"source:control:stage049-p3-{scenario_id}"
    second_source = first_source
    if scenario["control_shape"] == "CONTROL_CONTEXT_MISMATCH":
        second_source = f"source:control:stage049-p3-{scenario_id}-other"
    return {
        "candidate_controls": [
            _candidate(
                source_ref=first_source,
                parser_version="ids.parser.control_fixture.v0_1.stage049.p2.alpha",
                confidence=str(scenario["first_confidence"]),
                output_status=str(scenario["first_status"]),
            ),
            _candidate(
                source_ref=second_source,
                parser_version="ids.parser.control_fixture.v0_1.stage049.p2.beta",
                confidence=str(scenario["second_confidence"]),
                output_status=str(scenario["second_status"]),
            ),
        ]
    }


def _candidate(
    *, source_ref: str, parser_version: str, confidence: str, output_status: str
) -> dict[str, object]:
    return {
        "candidate_reference": {
            "source_identity_ref": source_ref,
            "route_action": "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
            "parser_output_status": output_status,
            "parser_family": "CONTROL_DIFFERENTIAL_FIXTURE_ADAPTER",
            "parser_version": parser_version,
            "output_schema_version": "ids.parser_output.v0_1.stage047.p1",
            "evidence_text_label": EVIDENCE_TEXT_LABEL,
        },
        "parser_confidence": confidence,
    }
