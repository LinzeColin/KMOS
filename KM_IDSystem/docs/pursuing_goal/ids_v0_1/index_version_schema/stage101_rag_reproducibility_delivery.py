"""Stage101 P4 的纯内存 RAG 可复现交付证据。

本模块仅从 Stage101 P3 的固定、非业务、reference-only 场景派生受控交付记录。
它不读取真实资料、提示词、模型配置、检索证据、回答或日志，不执行 RAG、模型、
Agent 或生产动作，也不创建持久化记录。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase4.delivery.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE"
PASS_RESULT = "PASS_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE101-P4-GATE"
NEXT_GATE = "IDS-STAGE101-REVIEW-GATE"
P3_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_SCENARIOS"
P3_PASS_RESULT = "PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_CURRENT_GATE = "IDS-STAGE101-P3-GATE"
P3_NEXT_GATE = "IDS-STAGE101-P4-GATE"
P3_CONTROL_PREFIX = ":control:stage101-p2:"
DELIVERY_PREFIX = ":control:stage101-p4:"

P3_SCENARIO_IDS = (
    "safe_summary_source_types_preserved_control",
    "draft_recommendation_evidence_gap_remains_declared_control",
    "retrieval_document_cannot_override_ids_rule_control",
    "high_risk_engineering_advice_requires_whitebox_confirmation_control",
    "contractual_commitment_requires_whitebox_confirmation_control",
    "production_writeback_requires_whitebox_confirmation_control",
)
HIGH_RISK_SCENARIO_IDS = P3_SCENARIO_IDS[3:]
REPRODUCIBILITY_TUPLE_FIELDS = (
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_provider_ref",
    "model_version_ref",
    "temperature_ref",
    "retrieval_context_ref",
    "selected_evidence_ref",
)
P3_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    *REPRODUCIBILITY_TUPLE_FIELDS,
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "source_type_separation_state",
    "internal_evidence_ref",
    "evidence_gap_ref",
    "internal_evidence_present",
    "evidence_gap_present",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "external_augmentation_ref",
    "external_augmentation_display_label",
    "output_category",
    "output_permission_state",
    "final_conclusion_state",
    "human_handling_required",
    "business_line_whitebox_human_approval_recorded",
    "automatic_final_conclusion_allowed",
    "future_model_reasoning_candidate_declared",
    "actual_model_call_performed",
    "actual_answer_publication_performed",
    "expectation_met",
)

ANSWER_SAMPLE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    *REPRODUCIBILITY_TUPLE_FIELDS,
    "source_type_separation_state",
    "evidence_gap_ref",
    "output_permission_state",
    "final_conclusion_state",
    "answer_sample_state",
    "business_line_whitebox_human_handling_required",
    "actual_answer_published",
)
NEGATIVE_TEST_RESULT_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "negative_test_case_ref",
    "expected_prevention_state",
    "negative_test_result_state",
    "retrieval_document_instruction_precedence_state",
    "prompt_injection_defense_state",
    "source_type_separation_state",
    "output_permission_state",
    "final_conclusion_state",
    "actual_rag_execution_performed",
    "actual_negative_test_result_persisted",
)
PROMPT_VERSION_RECORD_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "prompt_version_ref",
    "model_provider_ref",
    "model_version_ref",
    "temperature_ref",
    "retrieval_context_ref",
    "model_reasoning_ref",
    "future_model_reasoning_candidate_declared",
    "actual_model_call_performed",
    "prompt_rollback_target_ref",
    "model_configuration_fallback_ref",
    "version_record_state",
    "actual_prompt_or_model_configuration_accessed",
)
REPRODUCIBLE_LOG_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "phase3_report_ref",
    "delivery_module_ref",
    "focused_test_ref",
    *REPRODUCIBILITY_TUPLE_FIELDS,
    "expected_result_ref",
    "reproducible_log_state",
    "actual_log_written",
    "actual_runtime_execution_performed",
)
OUTPUT_PERMISSION_BOUNDARY_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "human_confirmation_gate_ref",
    "source_type_separation_state",
    "output_permission_state",
    "final_conclusion_state",
    "human_handling_required",
    "business_line_whitebox_human_approval_recorded",
    "automatic_final_conclusion_allowed",
    "actual_output_classification_performed",
    "actual_human_confirmation_performed",
    "actual_answer_published",
)
ROLLBACK_AND_FALLBACK_FIELDS = (
    "instruction_id",
    "control_domain",
    "trigger_state_ref",
    "rollback_target_ref",
    "rollback_target_result",
    "predecessor_phase_ref",
    "business_line_whitebox_approval_required",
    "versioned_basis_required",
    "verifiable_rollback_target_required",
    "actual_prompt_rollback_performed",
    "actual_model_configuration_fallback_performed",
    "persistent_state_write_performed",
)
DELIVERY_GROUPS = (
    ("answer_sample_control_records", ANSWER_SAMPLE_FIELDS),
    ("negative_test_result_control_records", NEGATIVE_TEST_RESULT_FIELDS),
    ("prompt_version_control_records", PROMPT_VERSION_RECORD_FIELDS),
    ("reproducible_log_control_records", REPRODUCIBLE_LOG_FIELDS),
    ("output_permission_boundary_control_records", OUTPUT_PERMISSION_BOUNDARY_FIELDS),
    ("rollback_and_fallback_control_records", ROLLBACK_AND_FALLBACK_FIELDS),
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "retrieval_execution_performed",
    "prompt_execution_performed",
    "prompt_or_model_configuration_access_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "answer_publication_performed",
    "model_output_classification_performed",
    "human_confirmation_performed",
    "prompt_rollback_performed",
    "model_configuration_fallback_performed",
    "log_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "external_api_call_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage101_phase4_runtime_executed",
)
FAILURE_STATES = (
    "PHASE3_CONTROL_OUTPUT_INVALID",
    "PHASE3_CONTROL_SHAPE_MISMATCH",
    "PHASE3_RUNTIME_SIGNAL_DETECTED",
    "CONTROL_REFERENCE_NOT_OPAQUE",
    "PROMPT_INJECTION_PROTECTION_MISSING",
    "EVIDENCE_GAP_SOURCE_TYPE_SEPARATION_MISSING",
    "HIGH_RISK_OUTPUT_PERMISSION_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "PROMPT_ROLLBACK_OR_MODEL_FALLBACK_MISSING",
    "ACTUAL_ANSWER_OR_LOG_WRITE_SIGNAL_DETECTED",
    "ACTUAL_PROMPT_OR_MODEL_CONFIGURATION_ACCESS_SIGNAL_DETECTED",
    "AUTOMATIC_FINAL_CONCLUSION_ALLOWED",
    "SECOND_AUTHORITY_CREATED",
    "STAGE101_REVIEW_STARTED",
    "DELIVERY_EXPECTATION_MISMATCH",
)

Phase3Executor = Callable[[], Mapping[str, Any]]


def _load_phase3_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage101_rag_reproducibility_controlled_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage101_phase3_scenarios", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage101 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _control_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P3_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _delivery_ref(name: str) -> str:
    return f"{DELIVERY_PREFIX}{name}:reference-only"


def _delivery_ref_is_opaque(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(DELIVERY_PREFIX)
        and value.endswith(":reference-only")
    )


def _failure_report(failure_state: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": False,
        "result": FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": ENTRY_GATE,
        "next_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_replayed_in_memory_only": False,
        "phase3_side_effect_free": False,
        "delivery_evidence_metadata_only": False,
        "control_references_opaque": False,
        "delivery_field_check_count": 0,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "actual_answer_sample_count": 0,
        "actual_negative_test_execution_count": 0,
        "actual_prompt_version_record_count": 0,
        "actual_reproducible_log_write_count": 0,
        "actual_output_permission_record_count": 0,
        "actual_prompt_rollback_count": 0,
        "actual_model_configuration_fallback_count": 0,
        "actual_persistent_state_write_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [],
    }
    for name, _fields in DELIVERY_GROUPS:
        report[name] = []
    return report


def _phase3_shape_failure(phase3_module: Any, report: Mapping[str, Any]) -> str | None:
    if (
        getattr(phase3_module, "SCHEMA_VERSION", None) != P3_SCHEMA_VERSION
        or getattr(phase3_module, "RECORD_KIND", None) != P3_RECORD_KIND
        or getattr(phase3_module, "PASS_RESULT", None) != P3_PASS_RESULT
        or tuple(getattr(phase3_module, "SCENARIO_FIELDS", ())) != P3_SCENARIO_FIELDS
        or report.get("schema_version") != P3_SCHEMA_VERSION
        or report.get("record_kind") != P3_RECORD_KIND
        or report.get("result") != P3_PASS_RESULT
        or report.get("valid") is not True
        or report.get("failure_state") is not None
        or report.get("current_gate") != P3_CURRENT_GATE
        or report.get("next_gate") != P3_NEXT_GATE
        or report.get("phase2_control_request_count") != 6
        or report.get("phase2_input_field_count") != 23
        or report.get("phase2_projection_group_count") != 4
        or report.get("phase2_projection_field_count_per_request") != 45
        or report.get("phase2_projection_field_count_total") != 270
        or report.get("scenario_count") != len(P3_SCENARIO_IDS)
        or report.get("scenario_field_count") != len(P3_SCENARIO_FIELDS)
        or report.get("scenario_field_check_count")
        != len(P3_SCENARIO_IDS) * len(P3_SCENARIO_FIELDS)
        or report.get("control_view_count") != 5
        or report.get("human_handling_count") != len(P3_SCENARIO_IDS)
        or report.get("future_model_reasoning_candidate_count") != len(P3_SCENARIO_IDS)
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    scenarios = report.get("scenario_results")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != len(P3_SCENARIO_IDS)
        or tuple(
            item.get("scenario_id") for item in scenarios if isinstance(item, Mapping)
        )
        != P3_SCENARIO_IDS
        or any(
            not isinstance(item, Mapping) or set(item) != set(P3_SCENARIO_FIELDS)
            for item in scenarios
        )
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    return None


def _phase3_runtime_failure(report: Mapping[str, Any]) -> str | None:
    if report.get("second_authoritative_source_created") is not False:
        return "SECOND_AUTHORITY_CREATED"
    boundary = report.get("runtime_boundary")
    if (
        report.get("persistent_record_created") is not False
        or not isinstance(boundary, Mapping)
        or any(value is not False for value in boundary.values())
        or any(
            value != 0
            for key, value in report.items()
            if key.startswith("actual_") and key.endswith("_count")
        )
    ):
        return "PHASE3_RUNTIME_SIGNAL_DETECTED"
    return None


def _phase3_semantic_failure(report: Mapping[str, Any]) -> str | None:
    scenarios = {
        item["scenario_id"]: item
        for item in report["scenario_results"]
        if isinstance(item, Mapping)
    }
    for scenario in scenarios.values():
        for field in (
            *REPRODUCIBILITY_TUPLE_FIELDS,
            "external_public_reference_ref",
            "model_reasoning_ref",
            "external_augmentation_ref",
        ):
            if not _control_ref(scenario.get(field)):
                return "CONTROL_REFERENCE_NOT_OPAQUE"
        for field in ("internal_evidence_ref", "evidence_gap_ref"):
            if scenario.get(field) is not None and not _control_ref(scenario.get(field)):
                return "CONTROL_REFERENCE_NOT_OPAQUE"
        if (
            scenario.get("expectation_met") is not True
            or scenario.get("human_handling_required") is not True
            or scenario.get("business_line_whitebox_human_approval_recorded") is not False
            or scenario.get("automatic_final_conclusion_allowed") is not False
            or scenario.get("future_model_reasoning_candidate_declared") is not True
            or scenario.get("actual_model_call_performed") is not False
            or scenario.get("actual_answer_publication_performed") is not False
        ):
            return "DELIVERY_EXPECTATION_MISMATCH"

    injection = scenarios[P3_SCENARIO_IDS[2]]
    if (
        injection.get("retrieval_document_instruction_precedence_state")
        != "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        or injection.get("prompt_injection_defense_state")
        != "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        or injection.get("output_permission_state")
        != "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW"
        or injection.get("final_conclusion_state")
        != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
    ):
        return "PROMPT_INJECTION_PROTECTION_MISSING"

    gap = scenarios[P3_SCENARIO_IDS[1]]
    if (
        gap.get("internal_evidence_ref") is not None
        or gap.get("internal_evidence_present") is not False
        or gap.get("evidence_gap_present") is not True
        or not _control_ref(gap.get("evidence_gap_ref"))
        or gap.get("source_type_separation_state")
        != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
    ):
        return "EVIDENCE_GAP_SOURCE_TYPE_SEPARATION_MISSING"

    safe_summary = scenarios[P3_SCENARIO_IDS[0]]
    if (
        safe_summary.get("source_type_separation_state")
        != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        or safe_summary.get("external_augmentation_display_label")
        != "external_augmentation_opinion"
    ):
        return "EVIDENCE_GAP_SOURCE_TYPE_SEPARATION_MISSING"

    for scenario_id in HIGH_RISK_SCENARIO_IDS:
        scenario = scenarios[scenario_id]
        if (
            scenario.get("output_permission_state")
            != "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
            or scenario.get("final_conclusion_state")
            != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        ):
            return "HIGH_RISK_OUTPUT_PERMISSION_MISSING"
    return None


def _answer_samples(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(f"answer-sample-{item['scenario_id']}"),
            "scenario_id": item["scenario_id"],
            **{field: item[field] for field in REPRODUCIBILITY_TUPLE_FIELDS},
            "source_type_separation_state": item["source_type_separation_state"],
            "evidence_gap_ref": item["evidence_gap_ref"],
            "output_permission_state": item["output_permission_state"],
            "final_conclusion_state": item["final_conclusion_state"],
            "answer_sample_state": (
                "CONTROL_RAG_REPRODUCIBILITY_ANSWER_SAMPLE_REFERENCE_ONLY_NOT_EXECUTED"
            ),
            "business_line_whitebox_human_handling_required": item[
                "human_handling_required"
            ],
            "actual_answer_published": False,
        }
        for item in scenarios
    ]


def _negative_test_results(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(f"negative-test-{item['scenario_id']}"),
            "scenario_id": item["scenario_id"],
            "negative_test_case_ref": _delivery_ref(
                f"negative-case-{item['scenario_id']}"
            ),
            "expected_prevention_state": item["output_permission_state"],
            "negative_test_result_state": (
                "CONTROL_NEGATIVE_TEST_RESULT_RECORDED_FROM_IN_MEMORY_GUARD"
            ),
            "retrieval_document_instruction_precedence_state": item[
                "retrieval_document_instruction_precedence_state"
            ],
            "prompt_injection_defense_state": item["prompt_injection_defense_state"],
            "source_type_separation_state": item["source_type_separation_state"],
            "output_permission_state": item["output_permission_state"],
            "final_conclusion_state": item["final_conclusion_state"],
            "actual_rag_execution_performed": False,
            "actual_negative_test_result_persisted": False,
        }
        for item in scenarios
    ]


def _prompt_version_records(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(f"prompt-version-{item['scenario_id']}"),
            "scenario_id": item["scenario_id"],
            "prompt_version_ref": item["prompt_version_ref"],
            "model_provider_ref": item["model_provider_ref"],
            "model_version_ref": item["model_version_ref"],
            "temperature_ref": item["temperature_ref"],
            "retrieval_context_ref": item["retrieval_context_ref"],
            "model_reasoning_ref": item["model_reasoning_ref"],
            "future_model_reasoning_candidate_declared": item[
                "future_model_reasoning_candidate_declared"
            ],
            "actual_model_call_performed": item["actual_model_call_performed"],
            "prompt_rollback_target_ref": _delivery_ref("prompt-rollback-to-phase3"),
            "model_configuration_fallback_ref": _delivery_ref(
                "model-configuration-fallback-to-phase3"
            ),
            "version_record_state": (
                "CONTROL_PROMPT_PROVIDER_MODEL_TEMPERATURE_AND_FUTURE_CANDIDATE_REFERENCE_ONLY"
            ),
            "actual_prompt_or_model_configuration_accessed": False,
        }
        for item in scenarios
    ]


def _reproducible_logs(scenarios: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"reproducible-log-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "phase3_report_ref": _delivery_ref("phase3-report-control"),
            "delivery_module_ref": _delivery_ref("phase4-delivery-module"),
            "focused_test_ref": _delivery_ref("phase4-focused-test"),
            **{field: item[field] for field in REPRODUCIBILITY_TUPLE_FIELDS},
            "expected_result_ref": _delivery_ref("delivery-pass-result"),
            "reproducible_log_state": (
                "CONTROL_REPRODUCIBILITY_TUPLE_LOCAL_RECEIPT_REFERENCE_ONLY"
            ),
            "actual_log_written": False,
            "actual_runtime_execution_performed": False,
        }
        for item in scenarios
    ]


def _output_permission_boundaries(
    scenarios: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "delivery_record_id": _delivery_ref(
                f"output-permission-{item['scenario_id']}"
            ),
            "scenario_id": item["scenario_id"],
            "human_confirmation_gate_ref": _delivery_ref(
                f"human-confirmation-{item['scenario_id']}"
            ),
            "source_type_separation_state": item["source_type_separation_state"],
            "output_permission_state": item["output_permission_state"],
            "final_conclusion_state": item["final_conclusion_state"],
            "human_handling_required": item["human_handling_required"],
            "business_line_whitebox_human_approval_recorded": item[
                "business_line_whitebox_human_approval_recorded"
            ],
            "automatic_final_conclusion_allowed": False,
            "actual_output_classification_performed": False,
            "actual_human_confirmation_performed": False,
            "actual_answer_published": False,
        }
        for item in scenarios
    ]


def _rollback_and_fallback_records() -> list[dict[str, Any]]:
    return [
        {
            "instruction_id": _delivery_ref("prompt-rollback"),
            "control_domain": "prompt_rollback",
            "trigger_state_ref": _delivery_ref("prompt-rollback-trigger"),
            "rollback_target_ref": _delivery_ref("prompt-rollback-to-phase3"),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage101-phase3"),
            "business_line_whitebox_approval_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_prompt_rollback_performed": False,
            "actual_model_configuration_fallback_performed": False,
            "persistent_state_write_performed": False,
        },
        {
            "instruction_id": _delivery_ref("model-configuration-fallback"),
            "control_domain": "model_configuration_fallback",
            "trigger_state_ref": _delivery_ref("model-configuration-fallback-trigger"),
            "rollback_target_ref": _delivery_ref(
                "model-configuration-fallback-to-phase3"
            ),
            "rollback_target_result": P3_PASS_RESULT,
            "predecessor_phase_ref": _delivery_ref("stage101-phase3"),
            "business_line_whitebox_approval_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_prompt_rollback_performed": False,
            "actual_model_configuration_fallback_performed": False,
            "persistent_state_write_performed": False,
        },
    ]


def _delivery_references_are_opaque(report: Mapping[str, Any]) -> bool:
    for group_name, fields in DELIVERY_GROUPS:
        records = report[group_name]
        if not isinstance(records, list):
            return False
        for record in records:
            if not isinstance(record, Mapping) or set(record) != set(fields):
                return False
            for field, value in record.items():
                if field == "evidence_gap_ref" and value is None:
                    continue
                if field.endswith("_ref") or field in {
                    "delivery_record_id",
                    "instruction_id",
                }:
                    if not (_control_ref(value) or _delivery_ref_is_opaque(value)):
                        return False
    return True


def build_rag_reproducibility_phase4_delivery_report(
    phase3_executor: Phase3Executor | None = None,
) -> dict[str, Any]:
    """派生 Stage101 P4 受控交付证据，不执行任何业务或运行时动作。"""

    try:
        phase3_module = _load_phase3_module()
        executor = (
            phase3_executor
            or phase3_module.build_rag_reproducibility_phase3_report
        )
        phase3_report = executor()
    except Exception:
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")
    if not phase3_report or not isinstance(phase3_report, Mapping):
        return _failure_report("PHASE3_CONTROL_OUTPUT_INVALID")
    shape_failure = _phase3_shape_failure(phase3_module, phase3_report)
    if shape_failure is not None:
        return _failure_report(shape_failure)
    runtime_failure = _phase3_runtime_failure(phase3_report)
    if runtime_failure is not None:
        return _failure_report(runtime_failure)
    semantic_failure = _phase3_semantic_failure(phase3_report)
    if semantic_failure is not None:
        return _failure_report(semantic_failure)

    scenarios = list(phase3_report["scenario_results"])
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": True,
        "result": PASS_RESULT,
        "failure_state": None,
        "current_gate": ENTRY_GATE,
        "next_gate": NEXT_GATE,
        "phase3_controlled_scenarios_replayed_in_memory_only": True,
        "phase3_side_effect_free": True,
        "delivery_evidence_metadata_only": True,
        "control_references_opaque": True,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        "actual_answer_sample_count": 0,
        "actual_negative_test_execution_count": 0,
        "actual_prompt_version_record_count": 0,
        "actual_reproducible_log_write_count": 0,
        "actual_output_permission_record_count": 0,
        "actual_prompt_rollback_count": 0,
        "actual_model_configuration_fallback_count": 0,
        "actual_persistent_state_write_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [
            "回答样例、负向结果、完整可复现元组记录和可复现日志均为纯内存控制投影，来源文档与业务线白箱人工复核继续承担业务事实权威。",
            "检索文档保持 evidence 身份，无内部依据保持 evidence_gap；不可信文档指令、伪装内部经验和自动最终结论均保持拒绝状态。",
            "高风险工程建议、合同承诺和生产写回均保持业务线白箱人工处理、人工确认未记录与最终结论未发布。",
            "prompt 回滚和模型配置回退说明只提供未来控制目标；版本化依据、白箱批准和可验证回退目标是实际执行前置条件。",
        ],
    }
    report["answer_sample_control_records"] = _answer_samples(scenarios)
    report["negative_test_result_control_records"] = _negative_test_results(scenarios)
    report["prompt_version_control_records"] = _prompt_version_records(scenarios)
    report["reproducible_log_control_records"] = _reproducible_logs(scenarios)
    report["output_permission_boundary_control_records"] = (
        _output_permission_boundaries(scenarios)
    )
    report["rollback_and_fallback_control_records"] = _rollback_and_fallback_records()
    report["delivery_field_check_count"] = sum(
        len(report[name]) * len(fields) for name, fields in DELIVERY_GROUPS
    )
    if not _delivery_references_are_opaque(report):
        return _failure_report("DELIVERY_REFERENCE_NOT_OPAQUE")
    if any(
        len(report[name]) != (2 if name == "rollback_and_fallback_control_records" else 6)
        for name, _fields in DELIVERY_GROUPS
    ):
        return _failure_report("DELIVERY_RECORD_SHAPE_MISMATCH")
    if any(
        record["business_line_whitebox_approval_required"] is not True
        or record["versioned_basis_required"] is not True
        or record["verifiable_rollback_target_required"] is not True
        for record in report["rollback_and_fallback_control_records"]
    ):
        return _failure_report("PROMPT_ROLLBACK_OR_MODEL_FALLBACK_MISSING")
    if any(
        record["future_model_reasoning_candidate_declared"] is not True
        or record["actual_model_call_performed"] is not False
        or record["actual_prompt_or_model_configuration_accessed"] is not False
        for record in report["prompt_version_control_records"]
    ):
        return _failure_report(
            "ACTUAL_PROMPT_OR_MODEL_CONFIGURATION_ACCESS_SIGNAL_DETECTED"
        )
    if any(
        record["automatic_final_conclusion_allowed"] is not False
        or record["actual_answer_published"] is not False
        or record["actual_human_confirmation_performed"] is not False
        for record in report["output_permission_boundary_control_records"]
    ):
        return _failure_report("AUTOMATIC_FINAL_CONCLUSION_ALLOWED")
    if any(
        record["actual_answer_published"] is not False
        for record in report["answer_sample_control_records"]
    ) or any(
        record["actual_log_written"] is not False
        or record["actual_runtime_execution_performed"] is not False
        for record in report["reproducible_log_control_records"]
    ):
        return _failure_report("ACTUAL_ANSWER_OR_LOG_WRITE_SIGNAL_DETECTED")
    return report
