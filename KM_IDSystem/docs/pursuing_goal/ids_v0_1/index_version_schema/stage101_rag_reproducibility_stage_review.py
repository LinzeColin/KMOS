"""Stage101 RAG 可复现的纯内存整阶段机械复审。

本模块只复核冻结任务包与 Stage101 P1--P4 已存在的控制工件。它不读取业务资料、
提示词正文、检索结果、回答、审计或数据库，不执行 RAG、模型、Agent、OVH 或生产动作，
也不创建持久化记录。
"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage101.rag_reproducibility.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_RAG_REPRODUCIBILITY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_RAG_REPRODUCIBILITY_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE101-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE102-P1-GATE"

P1_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase1.v1"
P1_CONTRACT_STATE = "PHASE1_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase2.v1"
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY"
P2_PASS_RESULT = "PASS_IN_MEMORY_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED"
P3_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase3.v1"
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_SCENARIOS"
P3_PASS_RESULT = "PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_SCHEMA_VERSION = "ids.stage101.rag_reproducibility.phase4.delivery.v1"
P4_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE"
P4_PASS_RESULT = "PASS_RAG_REPRODUCIBILITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_REFERENCE_FIELDS = (
    "rag_answer_structure_ref",
    "query_ref",
    "index_version_ref",
    "prompt_version_ref",
    "model_provider_ref",
    "model_version_ref",
    "temperature_ref",
    "retrieval_context_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "model_output_permission_ref",
    "human_confirmation_gate_ref",
)
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
P1_REFERENCE_FIELD_COUNT = 15
P1_SOURCE_TYPE_COUNT = 4
P1_ANSWER_SECTION_COUNT = 5
P1_OUTPUT_CATEGORY_COUNT = 5
P1_HIGH_RISK_OUTPUT_COUNT = 3
P1_FAILURE_STATE_COUNT = 22
P1_CHINESE_FEEDBACK_COUNT = 4
P2_CONTROL_REQUEST_COUNT = 6
P2_INPUT_FIELD_COUNT = 23
P2_PROJECTION_GROUP_COUNT = 4
P2_PROJECTION_FIELD_COUNT_PER_REQUEST = 45
P2_CONTROL_FIELD_CHECK_COUNT = 270
P2_FAILURE_STATE_COUNT = 19
P3_SCENARIO_COUNT = 6
P3_SCENARIO_FIELD_COUNT = 32
P3_SCENARIO_FIELD_CHECK_COUNT = 192
P3_CONTROL_VIEW_COUNT = 5
P3_HUMAN_HANDLING_COUNT = 6
P3_FAILURE_STATE_COUNT = 16
P4_DELIVERY_SHAPE = "6/6/6/6/6/2"
P4_DELIVERY_FIELD_SHAPE = "17/12/14/17/12/12"
P4_DELIVERY_FIELD_CHECK_COUNT = 456
P4_CHINESE_FEEDBACK_COUNT = 4
P4_FAILURE_STATE_COUNT = 16
P2_CONTROL_PREFIX = ":control:stage101-p2:"
P4_DELIVERY_PREFIX = ":control:stage101-p4:"

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": P1_REFERENCE_FIELD_COUNT,
    "phase1_source_type_count": P1_SOURCE_TYPE_COUNT,
    "phase1_answer_section_count": P1_ANSWER_SECTION_COUNT,
    "phase1_output_category_count": P1_OUTPUT_CATEGORY_COUNT,
    "phase1_high_risk_output_count": P1_HIGH_RISK_OUTPUT_COUNT,
    "phase1_failure_state_count": P1_FAILURE_STATE_COUNT,
    "phase1_chinese_feedback_count": P1_CHINESE_FEEDBACK_COUNT,
    "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
    "phase2_control_input_field_count": P2_INPUT_FIELD_COUNT,
    "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
    "phase2_projection_field_count_per_request": P2_PROJECTION_FIELD_COUNT_PER_REQUEST,
    "phase2_control_field_check_count": P2_CONTROL_FIELD_CHECK_COUNT,
    "phase2_failure_state_count": P2_FAILURE_STATE_COUNT,
    "phase3_scenario_count": P3_SCENARIO_COUNT,
    "phase3_scenario_field_count": P3_SCENARIO_FIELD_COUNT,
    "phase3_scenario_field_check_count": P3_SCENARIO_FIELD_CHECK_COUNT,
    "phase3_control_view_count": P3_CONTROL_VIEW_COUNT,
    "phase3_human_handling_count": P3_HUMAN_HANDLING_COUNT,
    "phase3_failure_state_count": P3_FAILURE_STATE_COUNT,
    "phase4_delivery_shape": P4_DELIVERY_SHAPE,
    "phase4_delivery_field_shape": P4_DELIVERY_FIELD_SHAPE,
    "phase4_delivery_field_check_count": P4_DELIVERY_FIELD_CHECK_COUNT,
    "phase4_chinese_feedback_count": P4_CHINESE_FEEDBACK_COUNT,
    "phase4_failure_state_count": P4_FAILURE_STATE_COUNT,
}

REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
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
    "stage101_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
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
    "SOURCE_TYPE_OR_PROMPT_INJECTION_BOUNDARY_MISMATCH",
    "OWNER_WHITEBOX_BOUNDARY_MISMATCH",
    "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH",
    "RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage101_rag_reproducibility_contract.json"
P2_MODULE_PATH = BASE / "stage101_rag_reproducibility_control_slice.py"
P3_MODULE_PATH = BASE / "stage101_rag_reproducibility_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage101_rag_reproducibility_delivery.py"
NEXT_TASKPACK_PATH = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-102_文档内提示注入防护.md"
)


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
    module = _load_module("stage101_review_phase2", P2_MODULE_PATH)
    return module.execute_rag_reproducibility_control_slice(module.build_control_input())


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage101_review_phase3", P3_MODULE_PATH)
    return module.build_rag_reproducibility_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage101_review_phase4", P4_MODULE_PATH)
    return module.build_rag_reproducibility_phase4_delivery_report()


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
    reproducibility = _mapping(contract.get("reproducible_rag_answer_contract"))
    answer_structure = _mapping(reproducibility.get("answer_structure_contract"))
    tuple_contract = _mapping(reproducibility.get("reproducibility_tuple_contract"))
    prompt_context = _mapping(reproducibility.get("prompt_and_model_context_contract"))
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
            contract.get("stage") == "STAGE-101",
            contract.get("phase") == "IDS-STAGE101-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE101-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE101-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE101-P2-GATE",
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            all(
                authority.get(field) is False
                for field in (
                    "stage101_contract_can_replace_source_document",
                    "stage101_contract_can_become_business_fact_authority",
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
            tuple(reproducibility.get("future_reproducibility_record_reference_fields", ()))
            == P1_REFERENCE_FIELDS,
            reproducibility.get("reproducibility_reference_field_count")
            == P1_REFERENCE_FIELD_COUNT,
            answer_structure.get("required_future_section_count")
            == P1_ANSWER_SECTION_COUNT,
            all(
                answer_structure.get(field) is False
                for field in (
                    "answer_content_generated",
                    "answer_structure_persisted",
                    "answer_publication_performed",
                )
            ),
            tuple(tuple_contract.get("record_key_reference_fields", ()))
            == REPRODUCIBILITY_TUPLE_FIELDS,
            tuple_contract.get("record_key_reference_field_count")
            == len(REPRODUCIBILITY_TUPLE_FIELDS),
            all(
                tuple_contract.get(field) is True
                for field in (
                    "future_replay_requires_all_record_key_references",
                    "future_replay_requires_source_type_retention",
                    "future_replay_requires_evidence_gap_retention",
                    "future_replay_requires_output_permission_and_human_confirmation_gate",
                )
            ),
            all(
                tuple_contract.get(field) is False
                for field in (
                    "actual_reproducibility_record_created",
                    "actual_replay_executed",
                    "actual_replay_comparison_performed",
                )
            ),
            prompt_context.get("future_prompt_context_reference_field_count") == 5,
            all(
                prompt_context.get(field) is False
                for field in (
                    "prompt_body_read",
                    "prompt_version_created",
                    "provider_selected",
                    "model_selected",
                    "model_parameter_applied",
                    "retrieval_context_built",
                    "prompt_executed",
                    "model_called",
                )
            ),
            source.get("underlying_source_types")
            == [
                "internal_evidence",
                "external_public_reference",
                "model_reasoning",
                "evidence_gap",
            ],
            source.get("underlying_source_type_count") == P1_SOURCE_TYPE_COUNT,
            all(
                source.get(field) is True
                for field in (
                    "internal_evidence_and_external_augmentation_must_remain_separated",
                    "external_augmentation_may_not_be_presented_as_internal_evidence",
                    "evidence_gap_must_be_declared_when_internal_evidence_is_insufficient",
                    "evidence_gap_may_not_be_presented_as_internal_experience",
                    "retrieval_document_is_evidence_not_system_instruction",
                    "retrieval_document_cannot_override_ids_rule",
                    "retrieval_document_cannot_be_system_instruction",
                )
            ),
            all(
                source.get(field) is False
                for field in (
                    "source_type_assignment_performed",
                    "external_augmentation_displayed",
                    "retrieval_document_read",
                    "instruction_override_evaluated",
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
            len(_mapping(permission.get("classified_output_types")))
            == P1_OUTPUT_CATEGORY_COUNT,
            permission.get("output_classification_count") == P1_OUTPUT_CATEGORY_COUNT,
            permission.get(
                "business_line_whitebox_human_confirmation_required_before_final_conclusion"
            )
            is True,
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
            failure.get("failure_state_count") == P1_FAILURE_STATE_COUNT,
            isinstance(failure.get("declared_failure_states"), list),
            len(failure.get("declared_failure_states", [])) == P1_FAILURE_STATE_COUNT,
            all(value is False for key, value in failure.items() if key.endswith("_allowed")),
            failure.get("actual_failure_record_created") is False,
            feedback.get("feedback_count") == P1_CHINESE_FEEDBACK_COUNT,
            len(feedback.get("feedbacks", [])) == P1_CHINESE_FEEDBACK_COUNT,
            feedback.get("actual_user_feedback_emitted") is False,
            local.get("static_contract_only") is True,
            all(
                value is False
                for key, value in local.items()
                if key != "static_contract_only"
            ),
            _closed_runtime(contract),
            boundary.get("stage100_review_evidence_declared") is True,
            boundary.get("stage101_started") is True,
            boundary.get("phase1_completed") is True,
            all(
                boundary.get(field) is False
                for field in (
                    "phase2_started",
                    "phase3_started",
                    "phase4_started",
                    "whole_stage_review_performed",
                    "github_upload_allowed",
                    "push_allowed",
                )
            ),
        )
    )


def _phase2_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage101_review_phase2_shape", P2_MODULE_PATH)
    except Exception:
        return False
    projections = tuple(getattr(module, "PROJECTION_FIELDS", ()))
    scenarios = tuple(getattr(module, "CONTROL_SCENARIOS", ()))
    if not all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P2_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P2_RECORD_KIND,
            len(getattr(module, "INPUT_FIELDS", ())) == P2_INPUT_FIELD_COUNT,
            len(scenarios) == P2_CONTROL_REQUEST_COUNT,
            len(projections) == P2_PROJECTION_GROUP_COUNT,
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("control_input_count") == P2_CONTROL_REQUEST_COUNT,
            report.get("control_projection_group_count") == P2_PROJECTION_GROUP_COUNT,
            report.get("control_projection_field_total_per_request")
            == P2_PROJECTION_FIELD_COUNT_PER_REQUEST,
            report.get("control_projection_field_total")
            == P2_CONTROL_FIELD_CHECK_COUNT,
            report.get("persistent_record_created") is False,
            _actual_counts_closed(report),
            _closed_runtime(report),
        )
    ):
        return False
    records_by_name: dict[str, list[Mapping[str, Any]]] = {}
    for prefix, fields in projections:
        records = report.get(f"{prefix}_control_projections")
        if not _records_have_shape(records, P2_CONTROL_REQUEST_COUNT, fields):
            return False
        if report.get(f"{prefix}_control_projection_count") != P2_CONTROL_REQUEST_COUNT:
            return False
        records_by_name[prefix] = list(records)
    reproducibility_records = records_by_name["reproducibility_record"]
    source_records = records_by_name[
        "source_semantics_and_external_augmentation_display"
    ]
    permission_records = records_by_name["prompt_injection_and_output_permission"]
    if not all(
        _control_ref(record.get(field))
        for record in reproducibility_records
        for field in REPRODUCIBILITY_TUPLE_FIELDS
    ):
        return False
    source_ok = all(
        record.get("source_type_separation_state")
        == "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED"
        and record.get("internal_evidence_source_type") == "internal_evidence"
        and record.get("external_public_reference_source_type")
        == "external_public_reference"
        and record.get("model_reasoning_source_type") == "model_reasoning"
        and record.get("evidence_gap_source_type") == "evidence_gap"
        and record.get("external_augmentation_display_label")
        == "external_augmentation_opinion"
        and record.get("display_label_is_not_source_type_state")
        == "CONTROL_DISPLAY_LABEL_IS_NOT_SOURCE_TYPE"
        and record.get("display_preserves_underlying_source_types_state")
        == "CONTROL_DISPLAY_PRESERVES_UNDERLYING_SOURCE_TYPES"
        and record.get("display_does_not_close_evidence_gap_state")
        == "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP"
        and all(
            _control_ref(
                record.get(field),
                optional=field in {"internal_evidence_ref", "evidence_gap_ref"},
            )
            for field in (
                "internal_evidence_ref",
                "external_public_reference_ref",
                "model_reasoning_ref",
                "evidence_gap_ref",
                "external_augmentation_ref",
                "source_type_ref",
            )
        )
        for record in source_records
    )
    injection = permission_records[2]
    permission_ok = all(
        record.get("retrieval_document_instruction_precedence_state")
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and record.get("final_conclusion_state")
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        for record in permission_records
    )
    return source_ok and permission_ok and all(
        (
            source_records[1].get("internal_evidence_ref") is None,
            _control_ref(source_records[1].get("evidence_gap_ref")),
            injection.get("prompt_injection_defense_state")
            == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            injection.get("output_permission_state")
            == "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
            all(
                record.get("output_permission_state")
                == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
                for record in permission_records[3:]
            ),
        )
    )


def _phase3_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage101_review_phase3_shape", P3_MODULE_PATH)
    except Exception:
        return False
    scenario_ids = tuple(item["scenario_id"] for item in module.SCENARIO_DEFINITIONS)
    scenarios = report.get("scenario_results")
    views = _mapping(report.get("control_views"))
    handlings = report.get("human_handlings")
    if not all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P3_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P3_RECORD_KIND,
            getattr(module, "PASS_RESULT", None) == P3_PASS_RESULT,
            len(getattr(module, "SCENARIO_FIELDS", ())) == P3_SCENARIO_FIELD_COUNT,
            report.get("schema_version") == P3_SCHEMA_VERSION,
            report.get("record_kind") == P3_RECORD_KIND,
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("failure_state") is None,
            report.get("current_gate") == "IDS-STAGE101-P3-GATE",
            report.get("next_gate") == "IDS-STAGE101-P4-GATE",
            report.get("phase2_control_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            report.get("phase2_control_request_count") == P2_CONTROL_REQUEST_COUNT,
            report.get("phase2_input_field_count") == P2_INPUT_FIELD_COUNT,
            report.get("phase2_projection_group_count") == P2_PROJECTION_GROUP_COUNT,
            report.get("phase2_projection_field_count_per_request")
            == P2_PROJECTION_FIELD_COUNT_PER_REQUEST,
            report.get("phase2_projection_field_count_total")
            == P2_CONTROL_FIELD_CHECK_COUNT,
            report.get("scenario_count") == P3_SCENARIO_COUNT,
            report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT,
            report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT,
            report.get("control_view_count") == P3_CONTROL_VIEW_COUNT,
            report.get("human_handling_count") == P3_HUMAN_HANDLING_COUNT,
            report.get("future_model_reasoning_candidate_count") == P3_SCENARIO_COUNT,
            _actual_counts_closed(report),
            _closed_runtime(report),
        )
    ):
        return False
    if not _records_have_shape(scenarios, P3_SCENARIO_COUNT, module.SCENARIO_FIELDS):
        return False
    if tuple(item.get("scenario_id") for item in scenarios) != scenario_ids:
        return False
    if set(views) != set(module.CONTROL_VIEW_FIELDS):
        return False
    if any(
        not isinstance(views.get(name), list)
        or len(views.get(name, [])) != P3_SCENARIO_COUNT
        for name in module.CONTROL_VIEW_FIELDS
    ):
        return False
    if not isinstance(handlings, list) or len(handlings) != P3_HUMAN_HANDLING_COUNT:
        return False
    injection = scenarios[2]
    high_risk = scenarios[3:]
    return all(
        item.get("expectation_met") is True
        and item.get("human_handling_required") is True
        and item.get("business_line_whitebox_human_approval_recorded") is False
        and item.get("automatic_final_conclusion_allowed") is False
        and item.get("final_conclusion_state")
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        and all(
            _control_ref(item.get(field), optional=field in {"internal_evidence_ref", "evidence_gap_ref"})
            for field in (
                *REPRODUCIBILITY_TUPLE_FIELDS,
                "internal_evidence_ref",
                "external_public_reference_ref",
                "model_reasoning_ref",
                "external_augmentation_ref",
                "evidence_gap_ref",
            )
        )
        for item in scenarios
    ) and all(
        (
            injection.get("retrieval_document_instruction_precedence_state")
            == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            injection.get("prompt_injection_defense_state")
            == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            scenarios[1].get("internal_evidence_present") is False,
            scenarios[1].get("evidence_gap_present") is True,
            scenarios[1].get("internal_evidence_ref") is None,
            _control_ref(scenarios[1].get("evidence_gap_ref")),
            all(
                item.get("output_permission_state")
                == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
                for item in high_risk
            ),
        )
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage101_review_phase4_shape", P4_MODULE_PATH)
    except Exception:
        return False
    groups = tuple(getattr(module, "DELIVERY_GROUPS", ()))
    expected_counts = {
        "answer_sample_control_records": P3_SCENARIO_COUNT,
        "negative_test_result_control_records": P3_SCENARIO_COUNT,
        "prompt_version_control_records": P3_SCENARIO_COUNT,
        "reproducible_log_control_records": P3_SCENARIO_COUNT,
        "output_permission_boundary_control_records": P3_SCENARIO_COUNT,
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
            report.get("current_gate") == "IDS-STAGE101-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True,
            report.get("phase3_side_effect_free") is True,
            report.get("delivery_evidence_metadata_only") is True,
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            report.get("delivery_field_check_count") == P4_DELIVERY_FIELD_CHECK_COUNT,
            len(report.get("chinese_feedback", [])) == P4_CHINESE_FEEDBACK_COUNT,
            _actual_counts_closed(report),
            _closed_runtime(report),
            tuple(name for name, _fields in groups) == tuple(expected_counts),
        )
    ):
        return False
    if any(
        not _records_have_shape(report.get(name), expected_counts[name], fields)
        for name, fields in groups
    ):
        return False
    answers = report["answer_sample_control_records"]
    negatives = {
        item["scenario_id"]: item
        for item in report["negative_test_result_control_records"]
    }
    logs = report["reproducible_log_control_records"]
    permissions = {
        item["scenario_id"]: item
        for item in report["output_permission_boundary_control_records"]
    }
    rollbacks = report["rollback_and_fallback_control_records"]
    high_risk_ids = (
        "high_risk_engineering_advice_requires_whitebox_confirmation_control",
        "contractual_commitment_requires_whitebox_confirmation_control",
        "production_writeback_requires_whitebox_confirmation_control",
    )
    injection = negatives["retrieval_document_cannot_override_ids_rule_control"]
    return all(
        _delivery_ref(item.get("delivery_record_id"))
        and item.get("answer_sample_state")
        == "CONTROL_RAG_REPRODUCIBILITY_ANSWER_SAMPLE_REFERENCE_ONLY_NOT_EXECUTED"
        and item.get("actual_answer_published") is False
        and item.get("business_line_whitebox_human_handling_required") is True
        and all(_control_ref(item.get(field)) for field in REPRODUCIBILITY_TUPLE_FIELDS)
        for item in answers
    ) and all(
        _delivery_ref(item.get("delivery_record_id"))
        and item.get("actual_log_written") is False
        and item.get("actual_runtime_execution_performed") is False
        and all(_control_ref(item.get(field)) for field in REPRODUCIBILITY_TUPLE_FIELDS)
        for item in logs
    ) and all(
        (
            injection.get("retrieval_document_instruction_precedence_state")
            == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            injection.get("prompt_injection_defense_state")
            == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            all(
                permissions[scenario_id].get("output_permission_state")
                == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
                and permissions[scenario_id].get("final_conclusion_state")
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                and permissions[scenario_id].get("human_handling_required") is True
                and permissions[scenario_id].get(
                    "business_line_whitebox_human_approval_recorded"
                )
                is False
                and permissions[scenario_id].get("automatic_final_conclusion_allowed")
                is False
                and permissions[scenario_id].get("actual_human_confirmation_performed")
                is False
                and permissions[scenario_id].get("actual_answer_published") is False
                for scenario_id in high_risk_ids
            ),
            {item.get("control_domain") for item in rollbacks}
            == {"prompt_rollback", "model_configuration_fallback"},
            all(
                _delivery_ref(item.get("instruction_id"))
                and item.get("rollback_target_result") == P3_PASS_RESULT
                and item.get("business_line_whitebox_approval_required") is True
                and item.get("versioned_basis_required") is True
                and item.get("verifiable_rollback_target_required") is True
                and item.get("actual_prompt_rollback_performed") is False
                and item.get("actual_model_configuration_fallback_performed") is False
                and item.get("persistent_state_write_performed") is False
                for item in rollbacks
            ),
        )
    )


def build_rag_reproducibility_stage101_review_report(
    phase1_contract_provider: Provider | None = None,
    phase2_report_provider: Provider | None = None,
    phase3_report_provider: Provider | None = None,
    phase4_report_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage101 P1--P4，任何结构或语义漂移保持失败关闭。"""

    phase1 = _provider_value(phase1_contract_provider, _default_phase1_contract)
    phase2 = _provider_value(phase2_report_provider, _default_phase2_report)
    phase3 = _provider_value(phase3_report_provider, _default_phase3_report)
    phase4 = _provider_value(phase4_report_provider, _default_phase4_report)
    phase_results = {
        "P1": _phase1_valid(phase1),
        "P2": _phase2_valid(phase2),
        "P3": _phase3_valid(phase3),
        "P4": _phase4_valid(phase4),
    }
    authority = _mapping(phase1.get("source_authority"))
    phase3_scenarios = phase3.get("scenario_results")
    phase4_permissions = phase4.get("output_permission_boundary_control_records")
    phase4_rollbacks = phase4.get("rollback_and_fallback_control_records")
    source_boundary = all(
        (
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            phase3.get("second_authoritative_source_created") is False,
            phase4.get("second_authoritative_source_created") is False,
        )
    )
    semantic_boundary = all(phase_results.values())
    owner_whitebox_boundary = (
        isinstance(phase3_scenarios, list)
        and len(phase3_scenarios) == P3_SCENARIO_COUNT
        and isinstance(phase4_permissions, list)
        and len(phase4_permissions) == P3_SCENARIO_COUNT
        and all(
            _mapping(item).get("human_handling_required") is True
            and _mapping(item).get("business_line_whitebox_human_approval_recorded")
            is False
            and _mapping(item).get("automatic_final_conclusion_allowed") is False
            for item in phase3_scenarios
        )
        and all(
            _mapping(item).get("human_handling_required") is True
            and _mapping(item).get("business_line_whitebox_human_approval_recorded")
            is False
            and _mapping(item).get("automatic_final_conclusion_allowed") is False
            for item in phase4_permissions
        )
    )
    rollback_boundary = (
        phase4.get("result") == P4_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and isinstance(phase4_rollbacks, list)
        and len(phase4_rollbacks) == 2
        and all(
            _mapping(item).get("rollback_target_result") == P3_PASS_RESULT
            and _mapping(item).get("business_line_whitebox_approval_required")
            is True
            and _mapping(item).get("versioned_basis_required") is True
            and _mapping(item).get("verifiable_rollback_target_required") is True
            and _mapping(item).get("actual_prompt_rollback_performed") is False
            and _mapping(item).get("actual_model_configuration_fallback_performed")
            is False
            and _mapping(item).get("persistent_state_write_performed") is False
            for item in phase4_rollbacks
        )
    )
    runtime_actions_disabled = all(
        (
            _closed_runtime(phase1),
            _closed_runtime(phase2),
            _closed_runtime(phase3),
            _closed_runtime(phase4),
            _actual_counts_closed(phase2),
            _actual_counts_closed(phase3),
            _actual_counts_closed(phase4),
        )
    )
    review_invariants = {
        "controlled_replay_exact": all(phase_results.values()),
        "single_authority_boundary_preserved": source_boundary,
        "source_type_and_prompt_injection_boundary_preserved": semantic_boundary,
        "owner_whitebox_boundary_preserved": owner_whitebox_boundary,
        "failure_stop_and_rollback_boundaries_preserved": rollback_boundary,
        "runtime_actions_disabled": runtime_actions_disabled,
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK_PATH.is_file(),
        "stage102_gate_only_opens_after_review": False,
    }
    review_valid = all(
        value
        for key, value in review_invariants.items()
        if key != "stage102_gate_only_opens_after_review"
    )
    review_invariants["stage102_gate_only_opens_after_review"] = review_valid
    failure_reasons: list[str] = []
    for phase_name in ("P1", "P2", "P3", "P4"):
        if not phase_results[phase_name]:
            failure_reasons.append(f"{phase_name}_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not review_invariants["controlled_replay_exact"]:
        failure_reasons.append("CONTROLLED_REPLAY_SHAPE_MISMATCH")
    if not source_boundary:
        failure_reasons.append("SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not semantic_boundary:
        failure_reasons.append("SOURCE_TYPE_OR_PROMPT_INJECTION_BOUNDARY_MISMATCH")
    if not owner_whitebox_boundary:
        failure_reasons.append("OWNER_WHITEBOX_BOUNDARY_MISMATCH")
    if not rollback_boundary:
        failure_reasons.append("FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH")
    if not runtime_actions_disabled or not NEXT_TASKPACK_PATH.is_file():
        failure_reasons.append("RUNTIME_SIGNAL_OR_NEXT_STAGE_ENTRY_DETECTED")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "failure_state": None if review_valid else failure_reasons[0],
        "failure_reasons": failure_reasons,
        "current_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "phase_results": phase_results,
        "controlled_replay": copy.deepcopy(REVIEWED_CONTROL_SHAPE),
        "review_invariants": review_invariants,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "stage100_review_evidence_declared": True,
        "stage101_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage101_review_control_report_generated_in_memory_only": True,
        "stage102_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "chinese_feedback": [
            "Stage101 P1 至 P4 的可复现控制形状、八元记录键、来源类型、提示注入防护、输出权限和回退前置保持一致，复审结果只承载控制结论。",
            "来源文档与业务线白箱人工复核继续承担业务事实权威；内部依据不足保持 evidence_gap，外部增强意见不能替代或伪装内部依据。",
            "高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。",
            "Stage102 只开放下一门禁；真实资料、检索、提示词、模型、模型 Token、Agent、OVH、生产与正式上传保持后续授权边界。",
        ],
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "runtime_boundary": {
            field: False
            for field in REVIEW_RUNTIME_FALSE_FIELDS
            if field != "stage101_review_runtime_executed"
        },
        "rollback": {
            "return_to": P4_PASS_RESULT,
            "preserve_stage101_phase1_to_phase4_evidence": True,
            "preserve_stage100_review_evidence": True,
            "preserve_frozen_taskpack": True,
            "preserve_business_source_authority": True,
            "business_source_or_runtime_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
    }
