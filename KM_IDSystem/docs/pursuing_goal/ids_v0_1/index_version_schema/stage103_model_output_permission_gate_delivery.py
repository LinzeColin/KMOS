"""Stage103 P4 模型输出权限门禁的纯内存交付证据。

本模块只从 Stage103 P3 已固定的非业务、reference-only 场景派生控制记录。
它不读取真实资料、文档正文、提示词、模型配置、检索证据、回答或日志，
也不执行模型、Agent、OVH、生产或任何持久化动作。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage103.model_output_permission_gate.phase4.delivery.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_DELIVERY_EVIDENCE"
PASS_RESULT = "PASS_MODEL_OUTPUT_PERMISSION_GATE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_MODEL_OUTPUT_PERMISSION_GATE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE103-P4-GATE"
NEXT_GATE = "IDS-STAGE103-REVIEW-GATE"
P3_SCHEMA_VERSION = "ids.stage103.model_output_permission_gate.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_SCENARIOS"
P3_PASS_RESULT = "PASS_MODEL_OUTPUT_PERMISSION_GATE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_CURRENT_GATE = "IDS-STAGE103-P3-GATE"
P3_NEXT_GATE = "IDS-STAGE103-P4-GATE"
P3_CONTROL_PREFIX = ":control:stage103-p2:"
DELIVERY_PREFIX = ":control:stage103-p4:"

P3_SCENARIO_IDS = (
    "document_instruction_cannot_override_ids_rule_control",
    "evidence_gap_cannot_masquerade_as_internal_experience_control",
    "high_risk_engineering_advice_requires_whitebox_confirmation_control",
    "contractual_commitment_requires_whitebox_confirmation_control",
    "production_writeback_requires_whitebox_confirmation_control",
)
HIGH_RISK_SCENARIO_IDS = (
    "high_risk_engineering_advice_requires_whitebox_confirmation_control",
    "contractual_commitment_requires_whitebox_confirmation_control",
    "production_writeback_requires_whitebox_confirmation_control",
)
REPRODUCIBILITY_TUPLE_FIELDS = (
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
)
P3_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
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
    "human_confirmation_state",
    "final_conclusion_state",
    "automatic_final_conclusion_allowed",
    "business_line_whitebox_human_approval_recorded",
    "actual_model_call_performed",
    "actual_answer_publication_performed",
    "actual_production_writeback_performed",
    "expectation_met",
)
P3_HUMAN_HANDLING_FIELDS = (
    "scenario_id",
    "output_category",
    "business_line_whitebox_handling_code",
    "high_risk_human_confirmation_required",
    "human_approval_recorded",
    "final_conclusion_state",
)

ANSWER_SAMPLE_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    *REPRODUCIBILITY_TUPLE_FIELDS,
    "ids_rule_precedence_state",
    "injection_defense_state",
    "evidence_gap_ref",
    "output_permission_state",
    "final_conclusion_state",
    "answer_sample_state",
    "actual_answer_published",
)
NEGATIVE_TEST_RESULT_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "negative_test_case_ref",
    "expected_prevention_state",
    "negative_test_result_state",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "source_type_separation_state",
    "output_permission_state",
    "final_conclusion_state",
    "actual_negative_test_result_persisted",
)
PROMPT_VERSION_RECORD_FIELDS = (
    "delivery_record_id",
    "scenario_id",
    "prompt_version_ref",
    "model_version_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "injection_defense_state",
    "future_model_reasoning_candidate_declared",
    "actual_model_call_performed",
    "prompt_rollback_target_ref",
    "model_configuration_fallback_ref",
    "version_record_state",
    "actual_prompt_or_model_configuration_accessed",
    "actual_model_token_consumption_performed",
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
DELIVERY_FIELD_CHECK_COUNT = 384
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "phase3_controlled_scenarios_runtime_executed",
    "document_content_read_performed",
    "document_instruction_detection_performed",
    "document_instruction_handling_performed",
    "query_execution_performed",
    "retrieval_execution_performed",
    "prompt_execution_performed",
    "source_type_binding_performed",
    "external_augmentation_displayed",
    "model_output_classification_performed",
    "human_confirmation_performed",
    "answer_publication_performed",
    "production_writeback_performed",
    "prompt_rollback_performed",
    "model_configuration_fallback_performed",
    "log_write_performed",
    "database_connection_performed",
    "audit_log_write_performed",
    "persistent_state_write_performed",
    "external_api_call_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage103_phase4_runtime_executed",
)
ACTUAL_COUNTER_FIELDS = (
    "actual_answer_sample_count",
    "actual_negative_test_execution_count",
    "actual_prompt_version_record_count",
    "actual_reproducible_log_write_count",
    "actual_output_permission_record_count",
    "actual_prompt_rollback_count",
    "actual_model_configuration_fallback_count",
    "actual_persistent_state_write_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)
FAILURE_STATES = (
    "PHASE3_CONTROL_OUTPUT_INVALID",
    "PHASE3_CONTROL_SHAPE_MISMATCH",
    "PHASE3_RUNTIME_SIGNAL_DETECTED",
    "CONTROL_REFERENCE_NOT_OPAQUE",
    "DOCUMENT_INSTRUCTION_PRECEDENCE_PROTECTION_MISSING",
    "EVIDENCE_GAP_SEMANTICS_MISSING",
    "HIGH_RISK_OUTPUT_PERMISSION_MISSING",
    "DELIVERY_RECORD_SHAPE_MISMATCH",
    "DELIVERY_REFERENCE_NOT_OPAQUE",
    "PROMPT_ROLLBACK_OR_MODEL_FALLBACK_MISSING",
    "ACTUAL_ANSWER_OR_LOG_WRITE_SIGNAL_DETECTED",
    "ACTUAL_PROMPT_OR_MODEL_CONFIGURATION_ACCESS_SIGNAL_DETECTED",
    "AUTOMATIC_FINAL_CONCLUSION_ALLOWED",
    "SECOND_AUTHORITY_CREATED",
    "STAGE103_REVIEW_STARTED",
    "DELIVERY_EXPECTATION_MISMATCH",
)

Phase3Executor = Callable[[], Mapping[str, Any]]


def _load_phase3_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage103_model_output_permission_gate_controlled_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage103_phase3_scenarios", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage103 P3 模型输出权限门禁场景模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ACTUAL_COUNTER_FIELDS}


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
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [],
    }
    for group_name, _ in DELIVERY_GROUPS:
        report[group_name] = []
    return report


def _phase3_shape_failure(phase3_module: Any, report: Mapping[str, Any]) -> str | None:
    expected_boundary = tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
    if (
        getattr(phase3_module, "SCHEMA_VERSION", None) != P3_SCHEMA_VERSION
        or getattr(phase3_module, "RECORD_KIND", None) != P3_RECORD_KIND
        or getattr(phase3_module, "PASS_RESULT", None) != P3_PASS_RESULT
        or tuple(getattr(phase3_module, "SCENARIO_FIELDS", ())) != P3_SCENARIO_FIELDS
        or tuple(getattr(phase3_module, "SCENARIO_DEFINITIONS", ())) == ()
        or report.get("schema_version") != P3_SCHEMA_VERSION
        or report.get("record_kind") != P3_RECORD_KIND
        or report.get("result") != P3_PASS_RESULT
        or report.get("valid") is not True
        or report.get("failure_state") is not None
        or report.get("current_gate") != P3_CURRENT_GATE
        or report.get("next_gate") != P3_NEXT_GATE
        or report.get("phase2_control_shape_preserved") is not True
        or report.get("phase2_side_effect_free") is not True
        or report.get("control_references_opaque") is not True
        or report.get("phase2_control_request_count") != 5
        or report.get("phase2_input_field_count") != 26
        or report.get("phase2_projection_group_count") != 4
        or report.get("phase2_projection_field_count_per_request") != 46
        or report.get("phase2_projection_field_count_total") != 230
        or report.get("scenario_count") != len(P3_SCENARIO_IDS)
        or report.get("scenario_field_count") != len(P3_SCENARIO_FIELDS)
        or report.get("scenario_field_check_count")
        != len(P3_SCENARIO_IDS) * len(P3_SCENARIO_FIELDS)
        or report.get("control_view_count") != 5
        or report.get("human_handling_count") != len(P3_SCENARIO_IDS)
        or not isinstance(report.get("runtime_boundary"), Mapping)
        or tuple(report["runtime_boundary"]) != expected_boundary
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    scenarios = report.get("scenario_results")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != len(P3_SCENARIO_IDS)
        or tuple(item.get("scenario_id") for item in scenarios)
        != P3_SCENARIO_IDS
        or any(
            not isinstance(item, Mapping) or set(item) != set(P3_SCENARIO_FIELDS)
            for item in scenarios
        )
    ):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    views = report.get("control_views")
    expected_views = getattr(phase3_module, "CONTROL_VIEW_FIELDS", {})
    if not isinstance(views, Mapping) or set(views) != set(expected_views):
        return "PHASE3_CONTROL_SHAPE_MISMATCH"
    human_handlings = report.get("human_handlings")
    if (
        not isinstance(human_handlings, list)
        or len(human_handlings) != len(P3_SCENARIO_IDS)
        or any(
            not isinstance(item, Mapping) or set(item) != set(P3_HUMAN_HANDLING_FIELDS)
            for item in human_handlings
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
    scenarios = {item["scenario_id"]: item for item in report["scenario_results"]}
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
            scenario.get("document_instruction_evidence_state")
            != "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
            or scenario.get("ids_rule_precedence_state") != "CONTROL_IDS_RULES_PREVAIL"
            or scenario.get("injection_defense_state")
            != "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
        ):
            return "DOCUMENT_INSTRUCTION_PRECEDENCE_PROTECTION_MISSING"
        if (
            scenario.get("source_type_separation_state")
            != "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
            or scenario.get("external_augmentation_display_label")
            != "external_augmentation_opinion"
            or scenario.get("internal_evidence_present")
            is not (scenario.get("internal_evidence_ref") is not None)
            or scenario.get("evidence_gap_present")
            is not (scenario.get("evidence_gap_ref") is not None)
        ):
            return "EVIDENCE_GAP_SEMANTICS_MISSING"
        if (
            scenario.get("expectation_met") is not True
            or scenario.get("business_line_whitebox_human_approval_recorded")
            is not False
            or scenario.get("automatic_final_conclusion_allowed") is not False
            or scenario.get("actual_model_call_performed") is not False
            or scenario.get("actual_answer_publication_performed") is not False
            or scenario.get("actual_production_writeback_performed") is not False
        ):
            return "DELIVERY_EXPECTATION_MISMATCH"
        if scenario.get("final_conclusion_state") != "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED":
            if scenario["scenario_id"] in HIGH_RISK_SCENARIO_IDS:
                return "HIGH_RISK_OUTPUT_PERMISSION_MISSING"
            return "AUTOMATIC_FINAL_CONCLUSION_ALLOWED"

    gap = scenarios[
        "evidence_gap_cannot_masquerade_as_internal_experience_control"
    ]
    if (
        gap.get("internal_evidence_ref") is not None
        or gap.get("internal_evidence_present") is not False
        or gap.get("evidence_gap_present") is not True
        or not _control_ref(gap.get("evidence_gap_ref"))
    ):
        return "EVIDENCE_GAP_SEMANTICS_MISSING"

    for scenario_id in HIGH_RISK_SCENARIO_IDS:
        scenario = scenarios[scenario_id]
        if (
            scenario.get("output_permission_state")
            != "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
            or scenario.get("human_confirmation_state")
            != "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED"
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
            "ids_rule_precedence_state": item["ids_rule_precedence_state"],
            "injection_defense_state": item["injection_defense_state"],
            "evidence_gap_ref": item["evidence_gap_ref"],
            "output_permission_state": item["output_permission_state"],
            "final_conclusion_state": item["final_conclusion_state"],
            "answer_sample_state": (
                "CONTROL_MODEL_OUTPUT_PERMISSION_GATE_ANSWER_SAMPLE_REFERENCE_ONLY_NOT_EXECUTED"
            ),
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
            "expected_prevention_state": item["injection_defense_state"],
            "negative_test_result_state": (
                "CONTROL_MODEL_OUTPUT_PERMISSION_GATE_NEGATIVE_RESULT_REFERENCE_ONLY"
            ),
            "document_instruction_evidence_state": item[
                "document_instruction_evidence_state"
            ],
            "ids_rule_precedence_state": item["ids_rule_precedence_state"],
            "injection_defense_state": item["injection_defense_state"],
            "source_type_separation_state": item["source_type_separation_state"],
            "output_permission_state": item["output_permission_state"],
            "final_conclusion_state": item["final_conclusion_state"],
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
            "model_version_ref": item["model_version_ref"],
            "document_instruction_candidate_ref": item[
                "document_instruction_candidate_ref"
            ],
            "ids_rule_ref": item["ids_rule_ref"],
            "injection_defense_state": item["injection_defense_state"],
            "future_model_reasoning_candidate_declared": True,
            "actual_model_call_performed": False,
            "prompt_rollback_target_ref": _delivery_ref("prompt-rollback-to-phase3"),
            "model_configuration_fallback_ref": _delivery_ref(
                "model-configuration-fallback-to-phase3"
            ),
            "version_record_state": (
                "CONTROL_PROMPT_MODEL_AND_OUTPUT_PERMISSION_REFERENCE_ONLY"
            ),
            "actual_prompt_or_model_configuration_accessed": False,
            "actual_model_token_consumption_performed": False,
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
                "CONTROL_MODEL_OUTPUT_PERMISSION_GATE_TUPLE_REFERENCE_ONLY"
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
            "human_handling_required": item["scenario_id"] in HIGH_RISK_SCENARIO_IDS,
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
            "predecessor_phase_ref": _delivery_ref("stage103-phase3"),
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
            "predecessor_phase_ref": _delivery_ref("stage103-phase3"),
            "business_line_whitebox_approval_required": True,
            "versioned_basis_required": True,
            "verifiable_rollback_target_required": True,
            "actual_prompt_rollback_performed": False,
            "actual_model_configuration_fallback_performed": False,
            "persistent_state_write_performed": False,
        },
    ]


def _delivery_shape_is_valid(report: Mapping[str, Any]) -> bool:
    for group_name, fields in DELIVERY_GROUPS:
        records = report.get(group_name)
        expected_count = (
            2 if group_name == "rollback_and_fallback_control_records" else len(P3_SCENARIO_IDS)
        )
        if (
            not isinstance(records, list)
            or len(records) != expected_count
            or any(
                not isinstance(record, Mapping) or set(record) != set(fields)
                for record in records
            )
        ):
            return False
    return report.get("delivery_field_check_count") == DELIVERY_FIELD_CHECK_COUNT


def _delivery_references_are_opaque(report: Mapping[str, Any]) -> bool:
    for group_name, fields in DELIVERY_GROUPS:
        records = report[group_name]
        for record in records:
            for field in fields:
                value = record[field]
                if field == "evidence_gap_ref" and value is None:
                    continue
                if field.endswith("_ref") or field in {
                    "delivery_record_id",
                    "instruction_id",
                }:
                    if not (_control_ref(value) or _delivery_ref_is_opaque(value)):
                        return False
    return True


def _rollback_and_fallback_is_valid(report: Mapping[str, Any]) -> bool:
    records = report["rollback_and_fallback_control_records"]
    if {record["control_domain"] for record in records} != {
        "prompt_rollback",
        "model_configuration_fallback",
    }:
        return False
    return all(
        record["rollback_target_result"] == P3_PASS_RESULT
        and record["business_line_whitebox_approval_required"] is True
        and record["versioned_basis_required"] is True
        and record["verifiable_rollback_target_required"] is True
        and record["actual_prompt_rollback_performed"] is False
        and record["actual_model_configuration_fallback_performed"] is False
        and record["persistent_state_write_performed"] is False
        for record in records
    )


def build_model_output_permission_gate_phase4_delivery_report(
    phase3_executor: Phase3Executor | None = None,
) -> dict[str, Any]:
    """派生 P4 交付控制记录；任一 P3 漂移均失败关闭。"""

    try:
        phase3_module = _load_phase3_module()
        executor = phase3_executor or phase3_module.build_model_output_permission_gate_phase3_report
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
        "control_references_opaque": False,
        "second_authoritative_source_created": False,
        "persistent_record_created": False,
        **_zero_actual_counts(),
        "runtime_boundary": _runtime_boundary(),
        "chinese_feedback": [
            "回答样例、负向测试结果、prompt/version 记录和可复现日志均为纯内存控制投影，来源文档与业务线白箱人工复核继续承担业务事实权威。",
            "文档内指令保持 evidence 候选，IDS 规则保持优先；无内部依据保持 evidence_gap，不作为内部经验呈现。",
            "高风险工程建议、合同承诺和生产写回均保持业务线白箱人工处理、人工确认未记录与最终结论未发布。",
            "prompt 回滚和模型配置回退说明只提供未来控制目标；版本化依据、白箱批准和可验证回退目标是实际执行前置条件。",
        ],
    }
    report["answer_sample_control_records"] = _answer_samples(scenarios)
    report["negative_test_result_control_records"] = _negative_test_results(scenarios)
    report["prompt_version_control_records"] = _prompt_version_records(scenarios)
    report["reproducible_log_control_records"] = _reproducible_logs(scenarios)
    report["output_permission_boundary_control_records"] = _output_permission_boundaries(
        scenarios
    )
    report["rollback_and_fallback_control_records"] = _rollback_and_fallback_records()
    report["delivery_field_check_count"] = sum(
        len(report[group_name]) * len(fields) for group_name, fields in DELIVERY_GROUPS
    )
    if not _delivery_shape_is_valid(report):
        return _failure_report("DELIVERY_RECORD_SHAPE_MISMATCH")
    if not _delivery_references_are_opaque(report):
        return _failure_report("DELIVERY_REFERENCE_NOT_OPAQUE")
    if not _rollback_and_fallback_is_valid(report):
        return _failure_report("PROMPT_ROLLBACK_OR_MODEL_FALLBACK_MISSING")
    report["control_references_opaque"] = True
    return deepcopy(report)
