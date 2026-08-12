"""Stage048 P2 的纯内存解析器降级处置切片。

该模块只把已受控的 reference-only 控制记录映射为明确处置。它不读取文件、
不选择或执行解析器，也不执行实际 fallback、队列或持久化动作。
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


SCHEMA_VERSION = "ids.stage048.parser_fallback.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_FALLBACK_DISPOSITION"
CONTROL_ADAPTER_VERSION = "ids.parser.fallback_control_adapter.v0_1.stage048.p2"
CONTROL_PARSER_FAMILY = "CONTROL_FIXTURE_ADAPTER"
CONTROL_PARSER_VERSION = "ids.parser.control_fixture.v0_1.stage048.p2"
EVIDENCE_TEXT_LABEL = "UNTRUSTED_EVIDENCE_TEXT"
EVIDENCE_TEXT_INTERPRETATION = "EVIDENCE_ONLY"

REFERENCE_FIELDS = (
    "source_identity_ref",
    "route_action",
    "parser_output_status",
    "parser_family",
    "parser_version",
    "failure_class",
    "evidence_text_label",
)
CONTROL_FIELDS = ("fallback_reference", "parser_confidence")
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
SOURCE_REFERENCE = re.compile(r"^source:control:[a-z0-9][a-z0-9-]{0,47}$")

DISPOSITIONS = {
    "candidate": {
        "code": "NO_FALLBACK_CANDIDATE_RETAINED",
        "feedback_code": "FALLBACK_CANDIDATE_RETAINED",
        "feedback": "当前结果保持候选状态，不执行自动回退。",
    },
    "review": {
        "code": "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
        "feedback_code": "FALLBACK_HUMAN_REVIEW_REQUIRED",
        "feedback": "该结果需要人工复核，当前未创建复核任务。",
    },
    "failure": {
        "code": "EXPLICIT_FAILURE_RETAINED_NOT_DROPPED",
        "feedback_code": "FALLBACK_EXPLICIT_FAILURE",
        "feedback": "解析失败已保留，不执行自动回退或丢弃。",
    },
    "blocked": {
        "code": "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
        "feedback_code": "FALLBACK_BLOCKED_OR_UNSUPPORTED",
        "feedback": "不支持或受阻的路线不执行回退，请人工复核。",
    },
    "invalid": {
        "code": "INVALID_OUTPUT_REJECTED_NO_FALLBACK",
        "feedback_code": "FALLBACK_INVALID_INPUT",
        "feedback": "输入状态无效，不执行回退并请人工复核。",
    },
}

DISPOSITION_BY_REFERENCE = {
    (
        "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
        "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "NO_FAILURE",
    ): "candidate",
    (
        "ROUTE_REVIEW_REQUIRED",
        "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "REVIEW_REQUIRED",
    ): "review",
    (
        "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
        "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "PARTIAL_OUTPUT",
    ): "review",
    (
        "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
        "OUTPUT_FAILED_EXPLICIT",
        "PARSER_FAILURE",
    ): "failure",
    (
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "NO_OUTPUT",
        "PARSER_IMPLEMENTATION_UNAVAILABLE",
    ): "blocked",
    (
        "ROUTE_UNSUPPORTED",
        "NO_OUTPUT",
        "UNSUPPORTED_FORMAT",
    ): "blocked",
    (
        "ROUTE_BLOCKED",
        "NO_OUTPUT",
        "ROUTE_BLOCKED",
    ): "blocked",
}


def resolve_control_fallback(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """返回一个非运行时处置记录，不产生任何外部副作用。"""

    accepted = _accepted_control(control_input)
    if accepted is None:
        return _result("invalid", None, None)

    reference, parser_confidence = accepted
    disposition_key = DISPOSITION_BY_REFERENCE.get(
        (
            reference["route_action"],
            reference["parser_output_status"],
            reference["failure_class"],
        )
    )
    if disposition_key is None:
        return _result("invalid", None, None)
    return _result(disposition_key, reference, parser_confidence)


def _accepted_control(
    control_input: Mapping[str, object] | object,
) -> tuple[dict[str, str], str] | None:
    if (
        not isinstance(control_input, Mapping)
        or set(control_input) != set(CONTROL_FIELDS)
    ):
        return None

    reference = control_input.get("fallback_reference")
    parser_confidence = control_input.get("parser_confidence")
    if (
        not isinstance(reference, Mapping)
        or set(reference) != set(REFERENCE_FIELDS)
        or not isinstance(parser_confidence, str)
        or parser_confidence not in CONFIDENCE_LEVELS
    ):
        return None

    normalized = {field: reference.get(field) for field in REFERENCE_FIELDS}
    if not all(isinstance(value, str) for value in normalized.values()):
        return None
    if not SOURCE_REFERENCE.fullmatch(normalized["source_identity_ref"]):
        return None
    if normalized["parser_family"] != CONTROL_PARSER_FAMILY:
        return None
    if normalized["parser_version"] != CONTROL_PARSER_VERSION:
        return None
    if normalized["evidence_text_label"] != EVIDENCE_TEXT_LABEL:
        return None
    return normalized, parser_confidence


def _result(
    disposition_key: str,
    reference: dict[str, str] | None,
    parser_confidence: str | None,
) -> dict[str, Any]:
    disposition = DISPOSITIONS[disposition_key]
    accepted = reference is not None
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": accepted,
        "source_identity_ref": reference["source_identity_ref"] if accepted else None,
        "route_action": reference["route_action"] if accepted else None,
        "parser_output_status": reference["parser_output_status"] if accepted else None,
        "parser_family": reference["parser_family"] if accepted else None,
        "parser_version": reference["parser_version"] if accepted else None,
        "parser_confidence": parser_confidence if accepted else "UNKNOWN",
        "failure_class": reference["failure_class"] if accepted else None,
        "parser_version_recorded": accepted,
        "parser_confidence_recorded": accepted,
        "evidence_text_label": EVIDENCE_TEXT_LABEL,
        "evidence_text_interpretation": EVIDENCE_TEXT_INTERPRETATION,
        "system_instruction_allowed": False,
        "tool_authorization_allowed": False,
        "policy_override_allowed": False,
        "disposition": disposition["code"],
        "human_feedback_code": disposition["feedback_code"],
        "human_feedback": disposition["feedback"],
        "in_memory_disposition_evaluated": True,
        "runtime_execution_performed": False,
        "source_file_open_performed": False,
        "route_evaluation_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "automatic_parser_switch_performed": False,
        "human_review_queue_write_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
    }
