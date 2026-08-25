"""Stage102 文档内提示注入防护的纯内存整阶段机械复审。

模块只复核冻结任务包和 Stage102 P1--P4 已存在的控制工件。它不会读取业务资料、
文档正文、提示词、检索结果、回答、审计或数据库，不执行模型、Agent、OVH 或生产动作，
也不创建持久化记录。
"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage102.document_prompt_injection_defense.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE102-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE103-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage102.document_prompt_injection_defense.phase1.v1"
P1_CONTRACT_STATE = "PHASE1_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage102.document_prompt_injection_defense.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE"
P2_PASS_RESULT = "PASS_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage102.document_prompt_injection_defense.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_SCENARIOS"
P3_PASS_RESULT = "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage102.document_prompt_injection_defense.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_REFERENCE_FIELDS = (
    "rag_answer_structure_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "prompt_version_ref",
    "injection_defense_policy_ref",
    "query_ref",
    "index_version_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
)
P1_UNTRUSTED_INSTRUCTION_CATEGORIES = (
    "ids_rule_override_attempt",
    "system_instruction_or_role_redefinition_attempt",
    "tool_or_external_action_authorization_attempt",
    "prompt_or_model_configuration_override_attempt",
    "output_permission_or_human_gate_bypass_attempt",
    "publication_or_production_writeback_bypass_attempt",
    "source_or_secret_access_request",
)
SOURCE_TYPES = (
    "internal_evidence",
    "external_public_reference",
    "model_reasoning",
    "evidence_gap",
)
OUTPUT_CATEGORIES = (
    "safe_summary",
    "draft_recommendation",
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
)
P2_CONTROL_PREFIX = ":control:stage102-p2:"
P4_DELIVERY_PREFIX = ":control:stage102-p4:"

P2_PROJECTION_FIELDS = {
    "answer_contract_and_reproducibility_control_projections": (
        "stage102_phase1_document_prompt_injection_defense_contract_ref",
        "stage101_review_control_ref",
        "rag_answer_structure_ref",
        "document_evidence_ref",
        "document_instruction_candidate_ref",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
        "output_classification_ref",
        "control_slice_state",
    ),
    "document_instruction_defense_control_projections": (
        "document_instruction_candidate_ref",
        "untrusted_instruction_category",
        "document_instruction_evidence_state",
        "ids_rule_ref",
        "ids_rule_precedence_state",
        "injection_defense_policy_ref",
        "injection_defense_state",
        "audit_boundary_ref",
        "tool_or_external_action_authorization_state",
        "prompt_or_model_override_state",
        "publication_or_writeback_state",
    ),
    "source_semantics_and_external_augmentation_display_control_projections": (
        "source_type_ref",
        "source_type_separation_state",
        "internal_evidence_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "external_augmentation_ref",
        "evidence_gap_ref",
        "external_augmentation_display_label",
        "internal_evidence_source_type",
        "external_public_reference_source_type",
        "model_reasoning_source_type",
        "evidence_gap_source_type",
        "external_augmentation_display_state",
        "display_label_is_not_source_type_state",
        "display_preserves_underlying_source_types_state",
        "display_does_not_close_evidence_gap_state",
    ),
    "output_permission_and_whitebox_gate_control_projections": (
        "model_output_permission_ref",
        "output_classification_ref",
        "human_confirmation_gate_ref",
        "output_category",
        "output_permission_state",
        "document_instruction_may_not_relax_output_permission_state",
        "document_instruction_may_not_bypass_human_confirmation_state",
        "human_confirmation_state",
        "final_conclusion_state",
        "automatic_publication_state",
        "production_writeback_state",
    ),
}
P3_SCENARIO_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenario",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
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
    "final_conclusion_state",
    "human_handling_required",
    "business_line_whitebox_human_approval_recorded",
    "automatic_final_conclusion_allowed",
    "future_model_reasoning_candidate_declared",
    "actual_model_call_performed",
    "actual_answer_publication_performed",
    "actual_production_writeback_performed",
    "expectation_met",
)
P3_CONTROL_VIEW_FIELDS = {
    "reproducibility_record_control_view": (
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
    ),
    "document_prompt_injection_control_view": (
        "scenario_id",
        "document_instruction_candidate_ref",
        "document_instruction_evidence_state",
        "ids_rule_ref",
        "ids_rule_precedence_state",
        "injection_defense_state",
    ),
    "source_type_and_external_augmentation_control_view": (
        "scenario_id",
        "internal_evidence_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "evidence_gap_ref",
        "external_augmentation_display_label",
        "source_type_separation_state",
    ),
    "output_permission_control_view": (
        "scenario_id",
        "output_category",
        "output_permission_state",
        "human_handling_required",
        "automatic_final_conclusion_allowed",
        "final_conclusion_state",
    ),
    "future_candidate_and_actual_execution_control_view": (
        "scenario_id",
        "model_reasoning_ref",
        "future_model_reasoning_candidate_declared",
        "actual_model_call_performed",
        "actual_answer_publication_performed",
        "actual_production_writeback_performed",
    ),
}
P3_HUMAN_HANDLING_FIELDS = (
    "scenario_id",
    "human_handling_code",
    "business_line_whitebox_review_required",
    "high_risk_human_confirmation_required",
    "business_line_whitebox_human_approval_recorded",
    "automatic_final_conclusion_allowed",
    "actual_human_confirmation_performed",
)
P4_DELIVERY_FIELDS = {
    "answer_sample_control_records": (
        "delivery_record_id",
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
        "document_evidence_ref",
        "document_instruction_candidate_ref",
        "ids_rule_ref",
        "ids_rule_precedence_state",
        "injection_defense_state",
        "evidence_gap_ref",
        "output_permission_state",
        "final_conclusion_state",
        "answer_sample_state",
        "actual_answer_published",
    ),
    "negative_test_result_control_records": (
        "delivery_record_id",
        "scenario_id",
        "negative_test_case_ref",
        "document_instruction_evidence_state",
        "ids_rule_precedence_state",
        "injection_defense_state",
        "source_type_separation_state",
        "output_permission_state",
        "final_conclusion_state",
        "expected_prevention_state",
        "negative_test_result_state",
        "actual_negative_test_result_persisted",
    ),
    "prompt_version_control_records": (
        "delivery_record_id",
        "scenario_id",
        "prompt_version_ref",
        "model_version_ref",
        "document_instruction_candidate_ref",
        "ids_rule_ref",
        "injection_defense_state",
        "future_model_reasoning_candidate_declared",
        "prompt_rollback_target_ref",
        "model_configuration_fallback_ref",
        "version_record_state",
        "actual_prompt_or_model_configuration_accessed",
        "actual_model_call_performed",
        "actual_model_token_consumption_performed",
    ),
    "reproducible_log_control_records": (
        "delivery_record_id",
        "scenario_id",
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "document_evidence_ref",
        "document_instruction_candidate_ref",
        "ids_rule_ref",
        "selected_evidence_ref",
        "phase3_report_ref",
        "focused_test_ref",
        "delivery_module_ref",
        "expected_result_ref",
        "reproducible_log_state",
        "actual_runtime_execution_performed",
        "actual_log_written",
    ),
    "output_permission_boundary_control_records": (
        "delivery_record_id",
        "scenario_id",
        "output_permission_state",
        "human_confirmation_gate_ref",
        "human_handling_required",
        "business_line_whitebox_human_approval_recorded",
        "automatic_final_conclusion_allowed",
        "final_conclusion_state",
        "source_type_separation_state",
        "actual_output_classification_performed",
        "actual_human_confirmation_performed",
        "actual_answer_published",
    ),
    "rollback_and_fallback_control_records": (
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
    ),
}
P4_DELIVERY_COUNTS = {
    "answer_sample_control_records": 7,
    "negative_test_result_control_records": 7,
    "prompt_version_control_records": 7,
    "reproducible_log_control_records": 7,
    "output_permission_boundary_control_records": 7,
    "rollback_and_fallback_control_records": 2,
}
REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": 17,
    "phase1_untrusted_instruction_category_count": 7,
    "phase1_source_type_count": 4,
    "phase1_output_category_count": 5,
    "phase1_failure_state_count": 25,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 7,
    "phase2_control_input_field_count": 28,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 50,
    "phase2_control_field_check_count": 350,
    "phase3_scenario_count": 7,
    "phase3_scenario_field_count": 34,
    "phase3_scenario_field_check_count": 238,
    "phase3_control_view_count": 5,
    "phase3_human_handling_count": 7,
    "phase3_failure_state_count": 27,
    "phase4_delivery_shape": "7/7/7/7/7/2",
    "phase4_delivery_field_shape": "17/12/14/17/12/12",
    "phase4_delivery_field_check_count": 528,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 16,
    "reproducibility_tuple_field_count": 8,
}
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "document_content_read_performed",
    "document_instruction_detection_performed",
    "document_instruction_handling_performed",
    "retrieval_execution_performed",
    "prompt_execution_performed",
    "prompt_or_model_configuration_access_performed",
    "model_call_performed",
    "model_token_consumption_performed",
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
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage102_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
    "actual_document_instruction_detection_count",
    "actual_document_instruction_handling_count",
    "actual_retrieval_execution_count",
    "actual_prompt_execution_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_model_output_classification_count",
    "actual_human_confirmation_count",
    "actual_answer_publication_count",
    "actual_production_writeback_count",
    "actual_prompt_rollback_count",
    "actual_model_configuration_fallback_count",
    "actual_log_write_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)
FAILURE_STATES = (
    "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
    "CONTROLLED_REPLAY_SHAPE_MISMATCH",
    "SINGLE_AUTHORITY_BOUNDARY_BREACH",
    "DOCUMENT_PROMPT_INJECTION_OR_SOURCE_SEMANTICS_MISMATCH",
    "OUTPUT_PERMISSION_WHITEBOX_BOUNDARY_MISMATCH",
    "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage102_document_prompt_injection_defense_contract.json"
P2_MODULE_PATH = BASE / "stage102_document_prompt_injection_defense_control_slice.py"
P3_MODULE_PATH = BASE / "stage102_document_prompt_injection_defense_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage102_document_prompt_injection_defense_delivery.py"


def _load_module(module_name: str, source: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {source.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(source: Path) -> Mapping[str, Any]:
    value = json.loads(source.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _default_phase1_contract() -> Mapping[str, Any]:
    return _load_json(P1_CONTRACT_PATH)


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module("stage102_review_phase2", P2_MODULE_PATH)
    return module.execute_document_prompt_injection_defense_control_slice(
        module.build_control_input()
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage102_review_phase3", P3_MODULE_PATH)
    return module.build_document_prompt_injection_defense_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage102_review_phase4", P4_MODULE_PATH)
    return module.build_document_prompt_injection_defense_phase4_delivery_report()


def _provider_value(provider: Provider | None, fallback: Provider) -> Mapping[str, Any]:
    try:
        value = (provider or fallback)()
    except Exception:
        return {}
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _closed_runtime(value: Mapping[str, Any]) -> bool:
    boundary = value.get("runtime_boundary")
    return isinstance(boundary, Mapping) and bool(boundary) and all(
        item is False for item in boundary.values()
    )


def _actual_counts_closed(value: Mapping[str, Any]) -> bool:
    counts = [
        item
        for key, item in value.items()
        if key.startswith("actual_") and key.endswith("_count")
    ]
    return bool(counts) and all(item == 0 for item in counts)


def _control_ref(value: object, *, optional: bool = False) -> bool:
    if optional and value is None:
        return True
    return (
        isinstance(value, str)
        and value.startswith(P2_CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _delivery_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(P4_DELIVERY_PREFIX)
        and value.endswith(":reference-only")
    )


def _records_have_shape(
    records: object, expected_count: int, fields: Sequence[str]
) -> bool:
    return isinstance(records, list) and len(records) == expected_count and all(
        isinstance(record, Mapping) and set(record) == set(fields) for record in records
    )


def _phase1_valid(contract: Mapping[str, Any]) -> bool:
    authority = _mapping(contract.get("source_authority"))
    document = _mapping(contract.get("document_instruction_boundary_contract"))
    risk = _mapping(contract.get("document_instruction_risk_contract"))
    source = _mapping(contract.get("source_semantics_contract"))
    display = _mapping(source.get("external_augmentation_display_composition"))
    permission = _mapping(contract.get("output_permission_contract"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    local = _mapping(contract.get("local_code"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("stage") == "STAGE-102",
            contract.get("phase") == "IDS-STAGE102-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE102-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE102-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE102-P2-GATE",
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            all(
                authority.get(field) is False
                for field in (
                    "stage102_contract_can_replace_source_document",
                    "stage102_contract_can_become_business_fact_authority",
                    "second_authoritative_source_created",
                    "source_body_or_path_allowed",
                    "raw_metadata_content_access_allowed",
                    "live_source_read_performed",
                    "authorized_fixture_access_performed",
                    "retrieval_result_access_performed",
                    "prompt_or_answer_access_performed",
                    "evidence_ledger_access_performed",
                    "audit_log_access_performed",
                )
            ),
            tuple(document.get("future_control_reference_fields", ()))
            == P1_REFERENCE_FIELDS,
            document.get("future_control_reference_field_count") == 17,
            document.get("document_evidence_state")
            == "UNTRUSTED_EVIDENCE_ONLY_REFERENCE",
            document.get("document_instruction_candidate_state")
            == "UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            document.get("ids_rule_precedence_state") == "IDS_RULES_PRECEDENCE_FIXED",
            document.get("control_references_are_labels_only") is True,
            all(
                document.get(field) is False
                for field in (
                    "document_content_may_override_ids_rule",
                    "document_content_may_be_system_instruction",
                    "document_content_may_authorize_tool_or_external_action",
                    "document_content_may_override_prompt_or_model_configuration",
                    "document_content_may_override_output_permission_or_human_gate",
                    "document_content_may_trigger_publication_or_writeback",
                    "document_content_may_request_source_or_secret_access",
                    "actual_document_content_read",
                    "actual_document_instruction_identified",
                    "actual_instruction_override_evaluated",
                    "actual_injection_defense_applied",
                    "actual_document_handling_record_written",
                )
            ),
            tuple(risk.get("future_untrusted_instruction_categories", ()))
            == P1_UNTRUSTED_INSTRUCTION_CATEGORIES,
            risk.get("future_untrusted_instruction_category_count") == 7,
            all(
                risk.get(field) is True
                for field in (
                    "all_categories_require_ids_rule_precedence",
                    "all_categories_require_non_executable_evidence_treatment",
                    "all_categories_require_future_business_line_whitebox_handling",
                )
            ),
            all(
                risk.get(field) is False
                for field in (
                    "actual_risk_category_assigned",
                    "actual_document_content_classified",
                    "actual_document_instruction_suppressed",
                )
            ),
            tuple(source.get("underlying_source_types", ())) == SOURCE_TYPES,
            source.get("underlying_source_type_count") == 4,
            all(
                source.get(field) is True
                for field in (
                    "document_evidence_is_untrusted_evidence_not_system_instruction",
                    "internal_evidence_and_external_augmentation_must_remain_separated",
                    "external_augmentation_may_not_be_presented_as_internal_evidence",
                    "evidence_gap_must_be_declared_when_internal_evidence_is_insufficient",
                    "evidence_gap_may_not_be_presented_as_internal_experience",
                )
            ),
            all(
                source.get(field) is False
                for field in (
                    "source_type_assignment_performed",
                    "external_augmentation_displayed",
                    "actual_internal_evidence_sufficiency_evaluated",
                    "actual_evidence_gap_assigned",
                )
            ),
            display.get("display_label") == "external_augmentation_opinion",
            display.get("composed_from_source_types")
            == ["external_public_reference", "model_reasoning"],
            all(
                display.get(field) is True
                for field in (
                    "display_label_is_not_a_source_type",
                    "display_composition_is_future_only",
                    "underlying_source_types_must_be_retained",
                    "display_label_may_not_replace_internal_evidence",
                    "display_label_may_not_replace_evidence_gap",
                    "display_label_may_not_close_no_internal_evidence_gap",
                )
            ),
            tuple(permission.get("classified_output_types", {}).keys())
            == OUTPUT_CATEGORIES,
            permission.get("output_classification_count") == 5,
            permission.get(
                "business_line_whitebox_human_confirmation_required_before_final_conclusion"
            )
            is True,
            all(
                permission.get(field) is True
                for field in (
                    "document_instruction_may_not_relax_output_permission",
                    "document_instruction_may_not_bypass_human_confirmation",
                )
            ),
            all(
                permission.get(field) is False
                for field in (
                    "high_risk_engineering_advice_auto_finalization_allowed",
                    "contractual_commitment_auto_finalization_allowed",
                    "production_writeback_auto_finalization_allowed",
                    "automatic_answer_publication_allowed",
                    "actual_output_classified",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                    "actual_production_writeback_performed",
                )
            ),
            failure.get("failure_state_count") == 25,
            isinstance(failure.get("declared_failure_states"), list),
            len(failure.get("declared_failure_states", [])) == 25,
            all(value is False for key, value in failure.items() if key.endswith("_allowed")),
            failure.get("actual_failure_record_created") is False,
            feedback.get("feedback_count") == 4,
            len(feedback.get("feedbacks", [])) == 4,
            feedback.get("actual_user_feedback_emitted") is False,
            local.get("static_contract_only") is True,
            all(value is False for key, value in local.items() if key != "static_contract_only"),
            _closed_runtime(contract),
            boundary.get("stage101_review_evidence_declared") is True,
            boundary.get("stage102_started") is True,
            boundary.get("phase1_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("phase2_started") is False,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage103_started") is False,
            boundary.get("github_upload_allowed") is False,
            boundary.get("push_allowed") is False,
        )
    )


def _phase2_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("input_accepted") is True,
            report.get("failure_state") is None,
            report.get("control_input_count") == 7,
            report.get("control_projection_group_count") == 4,
            report.get("control_projection_field_total_per_request") == 50,
            report.get("control_projection_field_total") == 350,
            all(
                _records_have_shape(report.get(name), 7, fields)
                and report.get(name.removesuffix("s") + "_count") == 7
                for name, fields in P2_PROJECTION_FIELDS.items()
            ),
            all(
                record.get("document_instruction_evidence_state")
                == "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
                and record.get("ids_rule_precedence_state")
                == "CONTROL_IDS_RULES_PREVAIL"
                and record.get("injection_defense_state")
                == "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
                for record in report.get("document_instruction_defense_control_projections", [])
            ),
            all(
                record.get("source_type_separation_state")
                == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
                and record.get("external_augmentation_display_label")
                == "external_augmentation_opinion"
                for record in report.get(
                    "source_semantics_and_external_augmentation_display_control_projections", []
                )
            ),
            all(
                record.get("output_category", "")
                .removeprefix("CONTROL_OUTPUT_CATEGORY_")
                .lower()
                in OUTPUT_CATEGORIES
                and record.get("human_confirmation_state")
                in {
                    "CONTROL_HUMAN_CONFIRMATION_NOT_EXECUTED",
                    "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED",
                }
                and record.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                for record in report.get(
                    "output_permission_and_whitebox_gate_control_projections", []
                )
            ),
            sum(
                record.get("human_confirmation_state")
                == "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED"
                for record in report.get(
                    "output_permission_and_whitebox_gate_control_projections", []
                )
            )
            == 3,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _closed_runtime(report),
        )
    )


def _phase3_valid(report: Mapping[str, Any]) -> bool:
    scenarios = report.get("scenario_results")
    views = _mapping(report.get("control_views"))
    handlings = report.get("human_handlings")
    scenario_refs = (
        "query_ref",
        "index_version_ref",
        "prompt_version_ref",
        "model_version_ref",
        "selected_evidence_ref",
        "document_evidence_ref",
        "document_instruction_candidate_ref",
        "ids_rule_ref",
        "external_public_reference_ref",
        "model_reasoning_ref",
        "external_augmentation_ref",
    )
    return all(
        (
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE102-P3-GATE",
            report.get("next_gate") == "IDS-STAGE102-P4-GATE",
            report.get("phase2_control_request_count") == 7,
            report.get("phase2_input_field_count") == 28,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 50,
            report.get("phase2_projection_field_count_total") == 350,
            report.get("scenario_count") == 7,
            report.get("scenario_field_count") == 34,
            report.get("scenario_field_check_count") == 238,
            _records_have_shape(scenarios, 7, P3_SCENARIO_FIELDS),
            report.get("control_view_count") == 5,
            set(views) == set(P3_CONTROL_VIEW_FIELDS),
            all(
                _records_have_shape(views.get(name), 7, fields)
                for name, fields in P3_CONTROL_VIEW_FIELDS.items()
            ),
            report.get("human_handling_count") == 7,
            _records_have_shape(handlings, 7, P3_HUMAN_HANDLING_FIELDS),
            sum(
                item.get("high_risk_human_confirmation_required") is True
                for item in handlings if isinstance(item, Mapping)
            )
            == 3,
            all(
                item.get("business_line_whitebox_review_required") is True
                and item.get("business_line_whitebox_human_approval_recorded") is False
                and item.get("automatic_final_conclusion_allowed") is False
                and item.get("actual_human_confirmation_performed") is False
                for item in handlings
            ),
            all(
                all(_control_ref(item.get(field)) for field in scenario_refs)
                and _control_ref(item.get("internal_evidence_ref"), optional=True)
                and _control_ref(item.get("evidence_gap_ref"), optional=True)
                and item.get("document_instruction_evidence_state")
                == "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
                and item.get("ids_rule_precedence_state")
                == "CONTROL_IDS_RULES_PREVAIL"
                and item.get("injection_defense_state")
                == "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
                and item.get("source_type_separation_state")
                == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
                and item.get("external_augmentation_display_label")
                == "external_augmentation_opinion"
                and item.get("output_category") in OUTPUT_CATEGORIES
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and item.get("human_handling_required") is True
                and item.get("business_line_whitebox_human_approval_recorded") is False
                and item.get("automatic_final_conclusion_allowed") is False
                and item.get("future_model_reasoning_candidate_declared") is True
                and item.get("actual_model_call_performed") is False
                and item.get("actual_answer_publication_performed") is False
                and item.get("actual_production_writeback_performed") is False
                and item.get("expectation_met") is True
                for item in scenarios
            ),
            report.get("phase2_control_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _closed_runtime(report),
        )
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    answer_records = report.get("answer_sample_control_records")
    negative_records = report.get("negative_test_result_control_records")
    version_records = report.get("prompt_version_control_records")
    log_records = report.get("reproducible_log_control_records")
    output_records = report.get("output_permission_boundary_control_records")
    rollback_records = report.get("rollback_and_fallback_control_records")
    return all(
        (
            report.get("schema_version") == P4_SCHEMA_VERSION,
            report.get("record_kind") == P4_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE102-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True,
            report.get("phase3_side_effect_free") is True,
            report.get("delivery_evidence_metadata_only") is True,
            all(
                _records_have_shape(report.get(name), count, P4_DELIVERY_FIELDS[name])
                for name, count in P4_DELIVERY_COUNTS.items()
            ),
            report.get("delivery_field_check_count") == 528,
            all(
                _delivery_ref(item.get("delivery_record_id"))
                and all(
                    _control_ref(item.get(field))
                    for field in (
                        "query_ref",
                        "index_version_ref",
                        "prompt_version_ref",
                        "model_version_ref",
                        "selected_evidence_ref",
                        "document_evidence_ref",
                        "document_instruction_candidate_ref",
                        "ids_rule_ref",
                    )
                )
                and item.get("ids_rule_precedence_state")
                == "CONTROL_IDS_RULES_PREVAIL"
                and item.get("injection_defense_state")
                == "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and item.get("actual_answer_published") is False
                for item in answer_records
            ),
            all(
                _delivery_ref(item.get("delivery_record_id"))
                and item.get("document_instruction_evidence_state")
                == "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE"
                and item.get("ids_rule_precedence_state")
                == "CONTROL_IDS_RULES_PREVAIL"
                and item.get("injection_defense_state")
                == "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY"
                and item.get("source_type_separation_state")
                == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and item.get("actual_negative_test_result_persisted") is False
                for item in negative_records
            ),
            all(
                _delivery_ref(item.get("delivery_record_id"))
                and item.get("future_model_reasoning_candidate_declared") is True
                and item.get("actual_prompt_or_model_configuration_accessed") is False
                and item.get("actual_model_call_performed") is False
                and item.get("actual_model_token_consumption_performed") is False
                for item in version_records
            ),
            all(
                _delivery_ref(item.get("delivery_record_id"))
                and item.get("actual_runtime_execution_performed") is False
                and item.get("actual_log_written") is False
                for item in log_records
            ),
            all(
                _delivery_ref(item.get("delivery_record_id"))
                and item.get("human_handling_required") is True
                and item.get("business_line_whitebox_human_approval_recorded") is False
                and item.get("automatic_final_conclusion_allowed") is False
                and item.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and item.get("actual_output_classification_performed") is False
                and item.get("actual_human_confirmation_performed") is False
                and item.get("actual_answer_published") is False
                for item in output_records
            ),
            all(
                _delivery_ref(item.get("instruction_id"))
                and item.get("rollback_target_result") == P3_PASS_RESULT
                and item.get("business_line_whitebox_approval_required") is True
                and item.get("versioned_basis_required") is True
                and item.get("verifiable_rollback_target_required") is True
                and item.get("actual_prompt_rollback_performed") is False
                and item.get("actual_model_configuration_fallback_performed") is False
                and item.get("persistent_state_write_performed") is False
                for item in rollback_records
            ),
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            len(report.get("chinese_feedback", [])) == 4,
            _actual_counts_closed(report),
            _closed_runtime(report),
        )
    )


def _base_report(valid: bool, failure_state: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE,
        "reviewed_control_shape": copy.deepcopy(REVIEWED_CONTROL_SHAPE),
        "reviewed_phase_artifact_identity": {
            "phase1_schema_version": P1_SCHEMA_VERSION,
            "phase2_schema_version": P2_SCHEMA_VERSION,
            "phase2_pass_result": P2_PASS_RESULT,
            "phase3_schema_version": P3_SCHEMA_VERSION,
            "phase3_pass_result": P3_PASS_RESULT,
            "phase4_schema_version": P4_SCHEMA_VERSION,
            "phase4_pass_result": P4_PASS_RESULT,
        },
        "source_authority": {
            "frozen_control_artifacts_only": True,
            "source_document_remains_authoritative": True,
            "business_line_whitebox_human_review_remains_authoritative": True,
            "review_can_replace_source_document": False,
            "review_can_become_business_fact_authority": False,
            "second_authoritative_source_created": False,
            "source_body_or_path_allowed": False,
            "raw_metadata_content_access_allowed": False,
            "live_source_read_performed": False,
            "document_content_access_performed": False,
            "authorized_fixture_access_performed": False,
            "retrieval_result_access_performed": False,
            "prompt_or_answer_access_performed": False,
            "evidence_ledger_access_performed": False,
            "report_or_audit_log_access_performed": False,
        },
        "semantic_controls": {
            "document_instruction_remains_untrusted_evidence": True,
            "document_instruction_cannot_override_ids_rules": True,
            "evidence_gap_cannot_be_presented_as_internal_experience": True,
            "source_type_separation_preserved": True,
            "external_augmentation_display_preserves_bottom_source_types": True,
            "high_risk_engineering_advice_requires_business_line_whitebox_confirmation": True,
            "contractual_commitment_requires_business_line_whitebox_confirmation": True,
            "production_writeback_requires_business_line_whitebox_confirmation": True,
            "final_conclusion_published": False,
            "actual_human_confirmation_performed": False,
        },
        "failure_and_stop_contract": {
            "declared_failure_states": list(FAILURE_STATES),
            "failure_state_count": len(FAILURE_STATES),
            "automatic_business_recommendation_allowed": False,
            "automatic_answer_publication_allowed": False,
            "automatic_retrieval_execution_allowed": False,
            "automatic_prompt_execution_allowed": False,
            "automatic_model_execution_allowed": False,
            "automatic_human_confirmation_allowed": False,
            "automatic_production_writeback_allowed": False,
            "automatic_prompt_rollback_allowed": False,
            "automatic_model_configuration_fallback_allowed": False,
            "stage103_must_remain_not_started": True,
        },
        "stage_and_phase_boundary": {
            "stage101_review_evidence_declared": True,
            "stage102_started": True,
            "phase1_completed": True,
            "phase2_completed": True,
            "phase3_completed": True,
            "phase4_completed": True,
            "stage102_review_started": True,
            "whole_stage_review_completed_in_memory_only": valid,
            "stage103_started": False,
            "github_upload_allowed": False,
            "push_allowed": False,
        },
        "rollback_contract": {
            "rollback_target_result": P4_PASS_RESULT,
            "review_rollback_target_is_phase4_delivery_evidence": True,
            "phase4_to_phase3_rollback_preserved": True,
            "actual_prompt_rollback_performed": False,
            "actual_model_configuration_fallback_performed": False,
            "actual_runtime_or_production_state_changed": False,
        },
        "chinese_feedback": [
            "Stage102 P1--P4 控制工件已完成纯内存机械复审，来源文档与业务线白箱人工复核继续承担业务事实权威。",
            "文档内潜在指令保持不可信 evidence，IDS 规则保持优先；内部依据不足保持 evidence_gap，不作为内部经验呈现。",
            "高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。",
            "P4 交付证据保持 P4→P3 的版本化、白箱批准和可验证回退目标；Stage103 保持下一独立 run 门禁。",
        ],
        "control_references_opaque": False,
        "persistent_record_created": False,
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        "runtime_boundary": {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
    }


def _failure_report(failure_state: str) -> dict[str, Any]:
    return _base_report(False, failure_state)


def build_document_prompt_injection_defense_stage102_review_report(
    phase1_provider: Provider | None = None,
    phase2_provider: Provider | None = None,
    phase3_provider: Provider | None = None,
    phase4_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage102 P1--P4；任何漂移都保持失败关闭。"""

    phase1 = _provider_value(phase1_provider, _default_phase1_contract)
    if not _phase1_valid(phase1):
        return _failure_report("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    phase2 = _provider_value(phase2_provider, _default_phase2_report)
    if not _phase2_valid(phase2):
        return _failure_report("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    phase3 = _provider_value(phase3_provider, _default_phase3_report)
    if not _phase3_valid(phase3):
        return _failure_report("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    phase4 = _provider_value(phase4_provider, _default_phase4_report)
    if not _phase4_valid(phase4):
        return _failure_report("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    report = _base_report(True, None)
    report["control_references_opaque"] = True
    report["phase1_contract_replayed_in_memory_only"] = True
    report["phase2_control_slice_replayed_in_memory_only"] = True
    report["phase3_controlled_scenarios_replayed_in_memory_only"] = True
    report["phase4_delivery_evidence_replayed_in_memory_only"] = True
    report["reviewed_phase_results"] = {
        "phase1_contract_state": phase1["contract_state"],
        "phase2_execution_state": phase2["execution_state"],
        "phase3_result": phase3["result"],
        "phase4_result": phase4["result"],
    }
    return copy.deepcopy(report)
