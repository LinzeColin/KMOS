"""Stage049 P2 的仅内存差异化解析器资格评估切片。

该模块只评估两个受控 reference-only 候选记录是否具备后续质量复核资格。它不读取
文件、不比较解析正文、不选择或执行 parser，也不触发 fallback、队列或持久化动作。
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


SCHEMA_VERSION = "ids.stage049.differential_parser_evaluation.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_DIFFERENTIAL_ELIGIBILITY"
CONTROL_ADAPTER_VERSION = "ids.parser.differential_control_adapter.v0_1.stage049.p2"
CONTROL_PARSER_FAMILY = "CONTROL_DIFFERENTIAL_FIXTURE_ADAPTER"
CONTROL_PARSER_VERSION = re.compile(
    r"^ids\.parser\.control_fixture\.v0_1\.stage049\.p2\.[a-z0-9-]{1,24}$"
)
OUTPUT_SCHEMA_VERSION = "ids.parser_output.v0_1.stage047.p1"
EVIDENCE_TEXT_LABEL = "UNTRUSTED_EVIDENCE_TEXT"
EVIDENCE_TEXT_INTERPRETATION = "EVIDENCE_ONLY"
CONTROL_ROUTE_ACTION = "ROUTE_CANDIDATE_READY_NOT_EXECUTED"

REFERENCE_FIELDS = (
    "source_identity_ref",
    "route_action",
    "parser_output_status",
    "parser_family",
    "parser_version",
    "output_schema_version",
    "evidence_text_label",
)
CONTROL_FIELDS = ("candidate_controls",)
CANDIDATE_CONTROL_FIELDS = ("candidate_reference", "parser_confidence")
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
OUTPUT_STATUSES = {
    "OUTPUT_CANDIDATE_NOT_VALIDATED",
    "OUTPUT_PARTIAL_REVIEW_REQUIRED",
}
SOURCE_REFERENCE = re.compile(r"^source:control:[a-z0-9][a-z0-9-]{0,47}$")

DISPOSITIONS = {
    "eligible": {
        "code": "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
        "eligibility": "ELIGIBLE_FOR_METADATA_COMPARISON",
        "feedback_code": "DIFFERENTIAL_CONTROL_QUALITY_REVIEW_REQUIRED",
        "feedback": "两个候选版本已完成受控资格检查，仍需质量复核，当前未创建复核任务。",
    },
    "review": {
        "code": "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
        "eligibility": "METADATA_DIVERGENCE_REVIEW_REQUIRED",
        "feedback_code": "DIFFERENTIAL_CONTROL_METADATA_REVIEW_REQUIRED",
        "feedback": "候选解析状态不一致，需要质量复核，当前未创建复核任务。",
    },
    "insufficient_versions": {
        "code": "COMPARISON_NOT_ELIGIBLE_INSUFFICIENT_DISTINCT_VERSIONS",
        "eligibility": "NOT_ELIGIBLE_INSUFFICIENT_DISTINCT_VERSIONS",
        "feedback_code": "DIFFERENTIAL_CONTROL_VERSION_COUNT_INSUFFICIENT",
        "feedback": "候选版本数量不足，当前不具备差异化比较条件。",
    },
    "context_mismatch": {
        "code": "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
        "eligibility": "NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
        "feedback_code": "DIFFERENTIAL_CONTROL_CONTEXT_MISMATCH",
        "feedback": "候选控制上下文不一致，当前不具备比较条件，请保留受控处置。",
    },
    "invalid": {
        "code": "COMPARISON_INVALID_CONTROL_REJECTED",
        "eligibility": "NOT_ELIGIBLE_INVALID_CONTROL",
        "feedback_code": "DIFFERENTIAL_CONTROL_INVALID_INPUT",
        "feedback": "候选控制输入无效，未执行差异化比较。",
    },
}


def evaluate_controlled_differential_eligibility(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """返回可直接测试的控制资格记录，不产生任何外部副作用。"""

    candidates = _accepted_control(control_input)
    if candidates is None:
        return _result("invalid", None)

    if not _shared_control_context(candidates):
        return _result("context_mismatch", candidates)
    if len({candidate["parser_version"] for candidate in candidates}) < 2:
        return _result("insufficient_versions", candidates)
    if any(
        candidate["parser_output_status"] == "OUTPUT_PARTIAL_REVIEW_REQUIRED"
        for candidate in candidates
    ):
        return _result("review", candidates)
    return _result("eligible", candidates)


def _accepted_control(
    control_input: Mapping[str, object] | object,
) -> list[dict[str, str]] | None:
    if (
        not isinstance(control_input, Mapping)
        or set(control_input) != set(CONTROL_FIELDS)
        or not isinstance(control_input.get("candidate_controls"), list)
    ):
        return None

    controls = control_input["candidate_controls"]
    if len(controls) != 2:
        return None

    candidates: list[dict[str, str]] = []
    for control in controls:
        candidate = _accepted_candidate(control)
        if candidate is None:
            return None
        candidates.append(candidate)
    return candidates


def _accepted_candidate(control: object) -> dict[str, str] | None:
    if not isinstance(control, Mapping) or set(control) != set(CANDIDATE_CONTROL_FIELDS):
        return None

    reference = control.get("candidate_reference")
    confidence = control.get("parser_confidence")
    if (
        not isinstance(reference, Mapping)
        or set(reference) != set(REFERENCE_FIELDS)
        or not isinstance(confidence, str)
        or confidence not in CONFIDENCE_LEVELS
    ):
        return None

    normalized = {field: reference.get(field) for field in REFERENCE_FIELDS}
    if not all(isinstance(value, str) for value in normalized.values()):
        return None
    if not SOURCE_REFERENCE.fullmatch(normalized["source_identity_ref"]):
        return None
    if normalized["route_action"] != CONTROL_ROUTE_ACTION:
        return None
    if normalized["parser_output_status"] not in OUTPUT_STATUSES:
        return None
    if normalized["parser_family"] != CONTROL_PARSER_FAMILY:
        return None
    if not CONTROL_PARSER_VERSION.fullmatch(normalized["parser_version"]):
        return None
    if normalized["output_schema_version"] != OUTPUT_SCHEMA_VERSION:
        return None
    if normalized["evidence_text_label"] != EVIDENCE_TEXT_LABEL:
        return None
    normalized["parser_confidence"] = confidence
    return normalized


def _shared_control_context(candidates: list[dict[str, str]]) -> bool:
    return all(
        len({candidate[field] for candidate in candidates}) == 1
        for field in (
            "source_identity_ref",
            "route_action",
            "output_schema_version",
            "evidence_text_label",
        )
    )


def _result(
    disposition_key: str,
    candidates: list[dict[str, str]] | None,
) -> dict[str, Any]:
    disposition = DISPOSITIONS[disposition_key]
    accepted = candidates is not None
    shared_context = accepted and _shared_control_context(candidates)
    versions = [candidate["parser_version"] for candidate in candidates] if accepted else []
    confidences = [candidate["parser_confidence"] for candidate in candidates] if accepted else []
    statuses = [candidate["parser_output_status"] for candidate in candidates] if accepted else []
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": accepted,
        "candidate_count": len(candidates) if accepted else 0,
        "source_identity_ref": candidates[0]["source_identity_ref"] if shared_context else None,
        "route_action": candidates[0]["route_action"] if shared_context else None,
        "output_schema_version": (
            candidates[0]["output_schema_version"] if shared_context else None
        ),
        "candidate_parser_versions": versions,
        "candidate_parser_confidences": confidences,
        "candidate_parser_output_statuses": statuses,
        "distinct_parser_version_count": len(set(versions)),
        "parser_versions_recorded": accepted,
        "parser_confidences_recorded": accepted,
        "shared_control_context": shared_context,
        "evidence_text_label": EVIDENCE_TEXT_LABEL,
        "evidence_text_interpretation": EVIDENCE_TEXT_INTERPRETATION,
        "system_instruction_allowed": False,
        "tool_authorization_allowed": False,
        "policy_override_allowed": False,
        "comparison_disposition": disposition["code"],
        "comparison_eligibility": disposition["eligibility"],
        "human_feedback_code": disposition["feedback_code"],
        "human_feedback": disposition["feedback"],
        "in_memory_controlled_differential_eligibility_evaluated": accepted,
        "metadata_consistency_evaluated": accepted,
        "actual_parse_product_comparison_performed": False,
        "actual_candidate_parse_product_created": False,
        "comparison_result_persisted": False,
        "source_file_open_performed": False,
        "file_type_redetection_performed": False,
        "route_evaluation_performed": False,
        "parser_selection_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "automatic_parser_switch_performed": False,
        "human_review_queue_write_performed": False,
        "prompt_injection_marker_application_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }
