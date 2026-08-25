"""Stage104 RAG 负向测试的纯内存整阶段机械复审。

本模块只复审冻结任务包和 Stage104 P1--P4 已存在的控制工件。它不读取业务资料、
文档正文、提示词、检索结果、回答、审计或数据库，不执行模型、Agent、OVH 或生产动作，
也不创建持久化记录。
"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage104.rag_negative_testing.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE104-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE105-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage104.rag_negative_testing.phase1.v1"
P1_CONTRACT_STATE = "RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage104.rag_negative_testing.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST"
P2_PASS_RESULT = "PASS_IN_MEMORY_RAG_NEGATIVE_TEST_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage104.rag_negative_testing.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST_SCENARIOS"
P3_PASS_RESULT = "PASS_RAG_NEGATIVE_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage104.rag_negative_testing.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_RAG_NEGATIVE_TEST_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

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
HIGH_RISK_OUTPUT_CATEGORIES = OUTPUT_CATEGORIES[2:]
P1_CONTROL_REFERENCE_FIELDS = (
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
)
NEGATIVE_TEST_IDS = (
    "DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
    "EVIDENCE_GAP_CANNOT_PRESENT_AS_INTERNAL_EXPERIENCE",
    "HIGH_RISK_ENGINEERING_ADVICE_CANNOT_AUTO_FINALIZE",
    "CONTRACTUAL_COMMITMENT_CANNOT_AUTO_FINALIZE",
    "PRODUCTION_WRITEBACK_CANNOT_AUTO_FINALIZE",
)
P3_EVIDENCE_GAP_SCENARIO_ID = (
    "evidence_gap_cannot_masquerade_as_internal_experience_control"
)
P3_HUMAN_HANDLING_FIELDS = (
    "scenario_id",
    "output_category",
    "business_line_whitebox_handling_code",
    "high_risk_human_confirmation_required",
    "human_approval_recorded",
    "final_conclusion_state",
)

REVIEWED_CONTROL_SHAPE = {
    "phase1_static_shape": "13/5/4/5/19/4",
    "phase1_reference_field_count": 13,
    "phase1_answer_structure_section_count": 5,
    "phase1_source_type_count": 4,
    "phase1_output_category_count": 5,
    "phase1_negative_test_case_count": 5,
    "phase1_failure_state_count": 19,
    "phase1_chinese_feedback_count": 4,
    "phase2_control_request_count": 5,
    "phase2_control_input_field_count": 29,
    "phase2_projection_group_count": 4,
    "phase2_projection_field_count_per_request": 57,
    "phase2_control_field_check_count": 285,
    "phase2_failure_state_count": 17,
    "phase3_scenario_count": 5,
    "phase3_scenario_field_count": 34,
    "phase3_scenario_field_check_count": 170,
    "phase3_control_view_count": 5,
    "phase3_human_handling_required_count": 5,
    "phase3_failure_state_count": 28,
    "phase4_delivery_shape": "5/5/5/5/5/2",
    "phase4_delivery_field_shape": "17/12/14/17/12/12",
    "phase4_delivery_field_check_count": 384,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 16,
    "reproducibility_tuple_field_count": 8,
    "retrieval_document_evidence_only_required": True,
    "ids_rule_precedence_required": True,
    "evidence_gap_not_internal_experience_required": True,
    "source_type_separation_required": True,
    "untrusted_document_instruction_rejection_required": True,
    "high_risk_output_whitebox_confirmation_required": True,
    "phase4_to_phase3_rollback_required": True,
}

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "document_content_read_performed",
    "document_instruction_detection_performed",
    "document_instruction_handling_performed",
    "query_execution_performed",
    "retrieval_execution_performed",
    "prompt_execution_performed",
    "prompt_or_model_configuration_access_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
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
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
    "stage104_review_runtime_executed",
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
    "DOCUMENT_OR_SOURCE_SEMANTICS_MISMATCH",
    "OUTPUT_PERMISSION_WHITEBOX_BOUNDARY_MISMATCH",
    "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage104_rag_negative_testing_contract.json"
P2_MODULE_PATH = BASE / "stage104_rag_negative_testing_control_slice.py"
P3_MODULE_PATH = BASE / "stage104_rag_negative_testing_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage104_rag_negative_testing_delivery.py"


def _load_module(module_name: str, source: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {source.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(source: Path) -> Mapping[str, Any]:
    return json.loads(source.read_text(encoding="utf-8"))


def _default_phase1_contract() -> Mapping[str, Any]:
    return _load_json(P1_CONTRACT_PATH)


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module("stage104_review_phase2", P2_MODULE_PATH)
    return module.execute_rag_negative_testing_control_slice(module.build_control_input())


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage104_review_phase3", P3_MODULE_PATH)
    return module.build_rag_negative_testing_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage104_review_phase4", P4_MODULE_PATH)
    return module.build_rag_negative_testing_phase4_delivery_report()


def _provider_value(provider: Provider | None, fallback: Provider) -> Mapping[str, Any]:
    value = (provider or fallback)()
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _runtime_closed(value: Mapping[str, Any]) -> bool:
    return bool(value) and all(item is False for item in value.values())


def _actual_counts_closed(value: Mapping[str, Any]) -> bool:
    return all(
        item == 0
        for key, item in value.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _records_have_shape(records: object, fields: tuple[str, ...], count: int) -> bool:
    return (
        isinstance(records, list)
        and len(records) == count
        and all(isinstance(record, Mapping) and set(record) == set(fields) for record in records)
    )


def _phase1_valid(contract: Mapping[str, Any]) -> bool:
    authority = _mapping(contract.get("source_authority"))
    future = _mapping(contract.get("future_rag_control_contract"))
    answer = _mapping(future.get("answer_structure_contract"))
    prompt = _mapping(future.get("prompt_version_contract"))
    semantics = _mapping(contract.get("document_and_source_semantics_contract"))
    gap = _mapping(semantics.get("no_internal_evidence_strategy"))
    negative = _mapping(contract.get("negative_test_contract"))
    output = _mapping(contract.get("output_permission_contract"))
    human = _mapping(contract.get("human_confirmation_contract"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    runtime = _mapping(contract.get("runtime_boundary"))
    protected = _mapping(contract.get("protected_surface_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("phase") == "IDS-STAGE104-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE104-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE104-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE104-P2-GATE",
            authority.get("authority")
            == "FROZEN_STAGE104_TASKPACK_AND_STAGE103_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_ARTIFACTS_ONLY",
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("actual_source_document_read_performed") is False,
            authority.get("actual_business_line_decision_performed") is False,
            future.get("future_control_reference_field_count") == 13,
            tuple(future.get("future_control_reference_fields", ()))
            == P1_CONTROL_REFERENCE_FIELDS,
            future.get("control_references_are_labels_only") is True,
            answer.get("required_future_section_count") == 5,
            answer.get("actual_answer_generated") is False,
            answer.get("actual_answer_persisted") is False,
            answer.get("actual_final_conclusion_generated") is False,
            prompt.get("prompt_version_is_future_control_reference_only") is True,
            prompt.get("prompt_text_read_performed") is False,
            prompt.get("prompt_execution_performed") is False,
            semantics.get("document_evidence_state") == "UNTRUSTED_EVIDENCE_ONLY_REFERENCE",
            semantics.get("document_instruction_candidate_state")
            == "UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            semantics.get("ids_rule_precedence_state") == "IDS_RULES_PRECEDENCE_FIXED",
            semantics.get("underlying_source_types") == list(SOURCE_TYPES),
            semantics.get("underlying_source_type_count") == len(SOURCE_TYPES),
            gap.get("evidence_gap_may_not_be_presented_as_internal_experience")
            is True,
            gap.get("external_augmentation_may_not_close_evidence_gap") is True,
            tuple(negative.get("future_negative_test_case_ids", ())) == NEGATIVE_TEST_IDS,
            negative.get("future_negative_test_case_count") == len(NEGATIVE_TEST_IDS),
            negative.get("actual_negative_test_case_executed") is False,
            output.get("output_classification_count") == len(OUTPUT_CATEGORIES),
            set(output.get("classified_output_types", {})) == set(OUTPUT_CATEGORIES),
            output.get("business_line_whitebox_human_confirmation_required_before_final_conclusion")
            is True,
            output.get("automatic_answer_publication_allowed") is False,
            output.get("automatic_production_writeback_allowed") is False,
            human.get("human_confirmation_may_not_be_automated") is True,
            human.get("final_conclusion_may_not_be_automated") is True,
            human.get("actual_human_confirmation_performed") is False,
            failure.get("failure_state_count") == 19,
            len(failure.get("declared_failure_states", [])) == 19,
            feedback.get("feedback_count") == 4,
            _runtime_closed(runtime),
            all(value is False for value in protected.values()),
            boundary.get("stage103_review_evidence_declared") is True,
            boundary.get("stage104_started") is True,
            boundary.get("phase1_completed") is True,
            boundary.get("phase2_started") is False,
            boundary.get("phase3_started") is False,
            boundary.get("phase4_started") is False,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage105_started") is False,
        )
    )


def _phase2_valid(module: Any, report: Mapping[str, Any]) -> bool:
    runtime = _mapping(report.get("runtime_boundary"))
    projections = tuple(getattr(module, "PROJECTION_FIELDS", ()))
    return all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P2_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P2_RECORD_KIND,
            len(getattr(module, "INPUT_FIELDS", ())) == 29,
            len(projections) == 4,
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("control_input_count") == 5,
            report.get("control_projection_group_count") == 4,
            report.get("control_projection_field_total_per_request") == 57,
            report.get("control_projection_field_total") == 285,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _runtime_closed(runtime),
            all(
                _records_have_shape(
                    report.get(f"{prefix}_control_projections"), tuple(fields), 5
                )
                for prefix, fields in projections
            ),
        )
    )


def _phase3_valid(module: Any, report: Mapping[str, Any]) -> bool:
    runtime = _mapping(report.get("runtime_boundary"))
    scenarios = report.get("scenario_results")
    scenario_fields = tuple(getattr(module, "SCENARIO_FIELDS", ()))
    control_views = _mapping(report.get("control_views"))
    if not all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P3_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P3_RECORD_KIND,
            getattr(module, "PASS_RESULT", None) == P3_PASS_RESULT,
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE104-P3-GATE",
            report.get("next_gate") == "IDS-STAGE104-P4-GATE",
            report.get("phase2_control_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            report.get("phase2_control_request_count") == 5,
            report.get("phase2_input_field_count") == 29,
            report.get("phase2_projection_group_count") == 4,
            report.get("phase2_projection_field_count_per_request") == 57,
            report.get("phase2_projection_field_count_total") == 285,
            report.get("scenario_count") == 5,
            report.get("scenario_field_count") == 34,
            report.get("scenario_field_check_count") == 170,
            report.get("control_view_count") == 5,
            report.get("human_handling_count") == 5,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _runtime_closed(runtime),
            _records_have_shape(scenarios, scenario_fields, 5),
            _records_have_shape(
                report.get("human_handlings"), P3_HUMAN_HANDLING_FIELDS, 5
            ),
            all(
                _records_have_shape(control_views.get(name), tuple(fields), 5)
                for name, fields in _mapping(getattr(module, "CONTROL_VIEW_FIELDS", {})).items()
            ),
        )
    ):
        return False

    scenario_by_id = {record["scenario_id"]: record for record in scenarios}
    expected_scenario_ids = {
        definition.get("scenario_id")
        for definition in getattr(module, "SCENARIO_DEFINITIONS", ())
        if isinstance(definition, Mapping)
    }
    if set(scenario_by_id) != expected_scenario_ids:
        return False
    for record in scenario_by_id.values():
        if not all(
            (
                record.get("document_instruction_evidence_state")
                == "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
                record.get("ids_rule_precedence_state") == "CONTROL_IDS_RULES_PREVAIL",
                record.get("injection_defense_state")
                == "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
                record.get("source_type_separation_state")
                == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
                record.get("external_augmentation_display_label")
                == "external_augmentation_opinion",
                record.get("automatic_final_conclusion_allowed") is False,
                record.get("business_line_whitebox_human_approval_recorded")
                is False,
                record.get("actual_model_call_performed") is False,
                record.get("actual_answer_publication_performed") is False,
                record.get("actual_production_writeback_performed") is False,
                record.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                record.get("expectation_met") is True,
            )
        ):
            return False
    gap = scenario_by_id.get(P3_EVIDENCE_GAP_SCENARIO_ID, {})
    if not all(
        (
            gap.get("internal_evidence_ref") is None,
            gap.get("internal_evidence_present") is False,
            gap.get("evidence_gap_present") is True,
        )
    ):
        return False
    for category in HIGH_RISK_OUTPUT_CATEGORIES:
        record = next(
            (item for item in scenario_by_id.values() if item.get("output_category") == category),
            {},
        )
        if not all(
            (
                record.get("output_permission_state")
                == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                record.get("human_confirmation_state")
                == "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED",
                record.get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
            )
        ):
            return False
    return True


def _phase4_valid(module: Any, report: Mapping[str, Any]) -> bool:
    runtime = _mapping(report.get("runtime_boundary"))
    groups = tuple(getattr(module, "DELIVERY_GROUPS", ()))
    expected_counts = {
        "answer_sample_control_records": 5,
        "negative_test_result_control_records": 5,
        "prompt_version_control_records": 5,
        "reproducible_log_control_records": 5,
        "output_permission_boundary_control_records": 5,
        "rollback_and_fallback_control_records": 2,
    }
    if not all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P4_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P4_RECORD_KIND,
            getattr(module, "PASS_RESULT", None) == P4_PASS_RESULT,
            report.get("schema_version") == P4_SCHEMA_VERSION,
            report.get("record_kind") == P4_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE104-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True,
            report.get("phase3_side_effect_free") is True,
            report.get("delivery_evidence_metadata_only") is True,
            report.get("control_references_opaque") is True,
            report.get("delivery_field_check_count") == 384,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _runtime_closed(runtime),
            len(report.get("chinese_feedback", [])) == 4,
            all(
                _records_have_shape(
                    report.get(name), tuple(fields), expected_counts.get(name, 0)
                )
                for name, fields in groups
            ),
        )
    ):
        return False
    return all(
        record.get("rollback_target_result") == P3_PASS_RESULT
        and record.get("business_line_whitebox_approval_required") is True
        and record.get("versioned_basis_required") is True
        and record.get("verifiable_rollback_target_required") is True
        and record.get("actual_prompt_rollback_performed") is False
        and record.get("actual_model_configuration_fallback_performed") is False
        and record.get("persistent_state_write_performed") is False
        for record in report.get("rollback_and_fallback_control_records", [])
    )


def _base_report(valid: bool, failure_state: str | None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if valid else REVIEW_GATE,
        "reviewed_control_shape": copy.deepcopy(REVIEWED_CONTROL_SHAPE),
        "reviewed_phase_artifact_identity": {
            "phase1_schema_version": P1_SCHEMA_VERSION,
            "phase1_contract_state": P1_CONTRACT_STATE,
            "phase2_schema_version": P2_SCHEMA_VERSION,
            "phase2_execution_state": P2_PASS_RESULT,
            "phase3_schema_version": P3_SCHEMA_VERSION,
            "phase3_result": P3_PASS_RESULT,
            "phase4_schema_version": P4_SCHEMA_VERSION,
            "phase4_result": P4_PASS_RESULT,
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
            "stage105_must_remain_not_started": True,
        },
        "stage_and_phase_boundary": {
            "stage103_review_evidence_declared": True,
            "stage104_started": True,
            "phase1_completed": True,
            "phase2_completed": True,
            "phase3_completed": True,
            "phase4_completed": True,
            "stage104_review_started": True,
            "whole_stage_review_completed_in_memory_only": valid,
            "stage105_started": False,
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
            "Stage104 P1--P4 控制工件已完成纯内存机械复审，来源文档与业务线白箱人工复核继续承担业务事实权威。",
            "文档内潜在指令保持不可信 evidence，IDS 规则保持优先；内部依据不足保持 evidence_gap，不作为内部经验呈现。",
            "高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。",
            "P4 交付证据保持 P4→P3 的版本化、白箱批准和可验证回退目标；Stage105 保持下一独立 run 门禁。",
        ],
        "control_references_opaque": False,
        "persistent_record_created": False,
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        "runtime_boundary": {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
    }


def _failure_report(failure_state: str) -> dict[str, Any]:
    return _base_report(False, failure_state)


def build_rag_negative_testing_stage104_review_report(
    phase1_provider: Provider | None = None,
    phase2_provider: Provider | None = None,
    phase3_provider: Provider | None = None,
    phase4_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage104 P1--P4；控制工件漂移时保持失败关闭。"""

    try:
        phase1 = _provider_value(phase1_provider, _default_phase1_contract)
    except Exception:
        return _failure_report("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase1_valid(phase1):
        return _failure_report("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase2_module = _load_module("stage104_review_phase2_validation", P2_MODULE_PATH)
        phase2 = _provider_value(phase2_provider, _default_phase2_report)
    except Exception:
        return _failure_report("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase2_valid(phase2_module, phase2):
        return _failure_report("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase3_module = _load_module("stage104_review_phase3_validation", P3_MODULE_PATH)
        phase3 = _provider_value(phase3_provider, _default_phase3_report)
    except Exception:
        return _failure_report("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase3_valid(phase3_module, phase3):
        return _failure_report("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    try:
        phase4_module = _load_module("stage104_review_phase4_validation", P4_MODULE_PATH)
        phase4 = _provider_value(phase4_provider, _default_phase4_report)
    except Exception:
        return _failure_report("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not _phase4_valid(phase4_module, phase4):
        return _failure_report("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID")

    report = _base_report(True, None)
    report.update(
        {
            "control_references_opaque": True,
            "phase1_contract_replayed_in_memory_only": True,
            "phase2_control_slice_replayed_in_memory_only": True,
            "phase3_controlled_scenarios_replayed_in_memory_only": True,
            "phase4_delivery_evidence_replayed_in_memory_only": True,
            "reviewed_phase_results": {
                "phase1_contract_state": phase1["contract_state"],
                "phase2_execution_state": phase2["execution_state"],
                "phase3_result": phase3["result"],
                "phase4_result": phase4["result"],
            },
        }
    )
    return copy.deepcopy(report)
