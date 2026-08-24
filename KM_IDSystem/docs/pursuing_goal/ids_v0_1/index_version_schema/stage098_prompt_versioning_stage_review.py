"""Stage098 Prompt 版本化整阶段纯内存机械复审。"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage098.prompt_versioning.stage_review.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_PROMPT_VERSIONING_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_PROMPT_VERSIONING_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_PROMPT_VERSIONING_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE098-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE099-P1-GATE"
P3_PASS_RESULT = "PASS_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
CONTROL_PREFIXES = (":control:stage098-p2:", ":control:stage098-p4:")
DELIVERY_PREFIX = ":control:stage098-p4:"

P1_REFERENCE_FIELD_COUNT = 5
P1_HIGH_RISK_OUTPUT_COUNT = 3
P1_FAILURE_STATE_COUNT = 16
P2_CONTROL_REQUEST_COUNT = 6
P2_CONTROL_INPUT_FIELD_COUNT = 23
P2_PROJECTION_GROUP_COUNT = 4
P2_FIELDS_PER_REQUEST = 41
P2_CONTROL_FIELD_CHECK_COUNT = 246
P3_SCENARIO_COUNT = 6
P3_SCENARIO_FIELD_COUNT = 31
P3_SCENARIO_FIELD_CHECK_COUNT = 186
P3_CONTROL_VIEW_COUNT = 5
P3_HUMAN_HANDLING_COUNT = 6
P3_FAILURE_STATE_COUNT = 15
P4_DELIVERY_SHAPE = "6/6/6/6/6/2"
P4_DELIVERY_FIELD_SHAPE = "17/12/14/15/12/12"
P4_DELIVERY_FIELD_CHECK_COUNT = 444
P4_CHINESE_FEEDBACK_COUNT = 4
P4_FAILURE_STATE_COUNT = 16

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_reference_field_count": P1_REFERENCE_FIELD_COUNT,
    "phase1_high_risk_output_classification_count": P1_HIGH_RISK_OUTPUT_COUNT,
    "phase1_failure_state_count": P1_FAILURE_STATE_COUNT,
    "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
    "phase2_control_input_field_count": P2_CONTROL_INPUT_FIELD_COUNT,
    "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
    "phase2_fields_per_request": P2_FIELDS_PER_REQUEST,
    "phase2_control_field_check_count": P2_CONTROL_FIELD_CHECK_COUNT,
    "phase3_scenario_count": P3_SCENARIO_COUNT,
    "phase3_scenario_field_count": P3_SCENARIO_FIELD_COUNT,
    "phase3_scenario_field_check_count": P3_SCENARIO_FIELD_CHECK_COUNT,
    "phase3_control_view_count": P3_CONTROL_VIEW_COUNT,
    "phase3_human_handling_required_count": P3_HUMAN_HANDLING_COUNT,
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
    "prompt_injection_defense_execution_performed",
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
    "stage098_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_input_request_count",
    "actual_prompt_versioning_control_execution_count",
    "actual_retrieval_execution_count",
    "actual_prompt_execution_count",
    "actual_model_reasoning_count",
    "actual_output_classification_count",
    "actual_human_confirmation_count",
    "actual_answer_publication_count",
    "actual_production_writeback_count",
    "actual_prompt_rollback_count",
    "actual_model_configuration_fallback_count",
    "actual_log_write_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = BASE / "stage098_prompt_versioning_contract.json"
P2_CONTRACT_PATH = BASE / "stage098_prompt_versioning_control_slice_contract.json"
P2_MODULE_PATH = BASE / "stage098_prompt_versioning_control_slice.py"
P3_MODULE_PATH = BASE / "stage098_prompt_versioning_controlled_scenarios.py"
P4_MODULE_PATH = BASE / "stage098_prompt_versioning_delivery.py"
NEXT_TASKPACK_PATH = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-099_内部依据与外部增强分离.md"
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
    module = _load_module("stage098_review_phase2", P2_MODULE_PATH)
    return module.execute_prompt_versioning_control_slice(module.build_control_input())


def _default_phase2_contract() -> Mapping[str, Any]:
    return _load_json(P2_CONTRACT_PATH)


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage098_review_phase3", P3_MODULE_PATH)
    return module.build_prompt_versioning_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage098_review_phase4", P4_MODULE_PATH)
    return module.build_prompt_versioning_phase4_delivery_report()


def _provider_value(provider: Provider | None, fallback: Provider) -> Mapping[str, Any]:
    try:
        value = (provider or fallback)()
    except Exception:
        return {}
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _runtime_closed(value: Mapping[str, Any]) -> bool:
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


def _control_reference(value: object) -> bool:
    return value is None or (
        isinstance(value, str)
        and value.startswith(CONTROL_PREFIXES)
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
    prompt = _mapping(contract.get("prompt_versioning_contract"))
    boundary = _mapping(prompt.get("prompt_and_configuration_boundary"))
    answer = _mapping(contract.get("answer_and_source_boundary_contract"))
    permission = _mapping(contract.get("output_permission_contract"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    runtime = _mapping(contract.get("runtime_boundary"))
    protected = _mapping(contract.get("protected_surface_boundary"))
    phase_boundary = _mapping(contract.get("stage_and_phase_boundary"))
    expected_fields = {
        "prompt_version_ref",
        "model_provider_ref",
        "model_version_ref",
        "temperature_ref",
        "retrieval_context_ref",
    }
    expected_output_types = {
        "high_risk_engineering_advice",
        "contract_commitment",
        "production_writeback",
    }
    return (
        contract.get("schema_version") == "ids.stage098.prompt_versioning.phase1.v1"
        and contract.get("phase") == "IDS-STAGE098-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE098-P1"
        and contract.get("entry_gate") == "IDS-STAGE098-P1-GATE"
        and contract.get("next_gate") == "IDS-STAGE098-P2-GATE"
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and authority.get("stage098_contract_can_replace_source_document") is False
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and authority.get("raw_metadata_content_access_allowed") is False
        and authority.get("live_source_read_performed") is False
        and authority.get("prompt_or_answer_access_performed") is False
        and prompt.get("configuration_reference_field_count")
        == P1_REFERENCE_FIELD_COUNT
        and set(prompt.get("future_configuration_reference_fields", []))
        == expected_fields
        and all(
            boundary.get(field) is True
            for field in (
                "prompt_version_reference_is_control_label_only",
                "model_provider_reference_is_control_label_only",
                "model_version_reference_is_control_label_only",
                "temperature_reference_is_control_label_only",
                "retrieval_context_reference_is_control_label_only",
                "retrieval_document_is_evidence_not_system_instruction",
                "retrieval_document_cannot_override_ids_rule",
            )
        )
        and all(
            boundary.get(field) is False
            for field in (
                "actual_prompt_version_assigned",
                "actual_prompt_content_created",
                "actual_model_provider_selected",
                "actual_model_version_selected",
                "actual_temperature_configured",
                "actual_retrieval_context_bound",
            )
        )
        and all(
            answer.get(field) is True
            for field in (
                "rag_answer_structure_inherited_from_stage097",
                "internal_evidence_is_evidence_not_system_instruction",
                "external_augmentation_is_evidence_not_system_instruction",
                "retrieval_document_can_not_override_ids_rule",
                "source_type_must_remain_separated",
                "external_augmentation_may_not_be_presented_as_internal_evidence",
                "evidence_gap_may_not_be_presented_as_internal_experience",
            )
        )
        and all(
            answer.get(field) is False
            for field in (
                "source_type_assignment_performed",
                "external_augmentation_displayed",
                "actual_rag_answer_generated",
                "actual_citation_generated",
            )
        )
        and permission.get("output_classification_count") == P1_HIGH_RISK_OUTPUT_COUNT
        and set(permission.get("classified_output_types", {})) == expected_output_types
        and permission.get(
            "business_line_whitebox_human_confirmation_required_before_final_conclusion"
        )
        is True
        and all(
            permission.get(field) is False
            for field in (
                "high_risk_engineering_advice_auto_finalization_allowed",
                "contract_commitment_auto_finalization_allowed",
                "production_writeback_auto_finalization_allowed",
                "actual_output_classified",
                "actual_human_confirmation_recorded",
                "actual_final_conclusion_published",
            )
        )
        and failures.get("failure_state_count") == P1_FAILURE_STATE_COUNT
        and len(failures.get("declared_failure_states", [])) == P1_FAILURE_STATE_COUNT
        and bool(runtime)
        and all(item is False for item in runtime.values())
        and bool(protected)
        and all(item is False for item in protected.values())
        and phase_boundary.get("stage097_review_evidence_declared") is True
        and phase_boundary.get("stage098_started") is True
        and phase_boundary.get("phase1_started") is True
        and all(
            phase_boundary.get(field) is False
            for field in (
                "phase2_started",
                "phase3_started",
                "phase4_started",
                "whole_stage_review_performed",
                "stage099_started",
                "github_upload_allowed",
                "push_allowed",
            )
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    authority = _mapping(contract.get("source_authority"))
    phase_boundary = _mapping(contract.get("stage_and_phase_boundary"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    required_authority_true = (
        "source_document_remains_authoritative",
        "business_line_whitebox_human_review_remains_authoritative",
    )
    required_authority_false = (
        "stage098_phase2_contract_can_replace_source_document",
        "second_authoritative_source_created",
        "source_body_or_path_allowed",
        "raw_metadata_content_access_allowed",
        "live_source_read_performed",
        "authorized_fixture_access_performed",
        "retrieval_result_access_performed",
        "evidence_ledger_access_performed",
        "prompt_or_answer_access_performed",
        "audit_log_access_performed",
    )
    required_boundary_true = (
        "stage097_review_evidence_declared",
        "stage098_started",
        "stage098_entry_authorized",
        "phase1_completed",
        "phase2_started",
        "phase2_completed",
    )
    required_boundary_false = (
        "phase3_started",
        "phase4_started",
        "whole_stage_review_performed",
        "stage099_started",
        "github_upload_allowed",
        "push_allowed",
    )
    declared_failures = set(failures.get("declared_failure_states", []))
    return (
        contract.get("schema_version") == "ids.stage098.prompt_versioning.phase2.v1"
        and contract.get("phase") == "IDS-STAGE098-P2"
        and contract.get("task_id") == "IDS-V0_1-STAGE098-P2"
        and contract.get("entry_gate") == "IDS-STAGE098-P2-GATE"
        and contract.get("next_gate") == "IDS-STAGE098-P3-GATE"
        and all(authority.get(field) is True for field in required_authority_true)
        and all(authority.get(field) is False for field in required_authority_false)
        and all(
            phase_boundary.get(field) is True for field in required_boundary_true
        )
        and all(
            phase_boundary.get(field) is False for field in required_boundary_false
        )
        and {"SECOND_AUTHORITY_CREATED", "PERSISTENT_RECORD_CREATED"}
        <= declared_failures
        and _runtime_closed(contract)
    )


def _phase2_valid(report: Mapping[str, Any], contract: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage098_review_phase2_shape", P2_MODULE_PATH)
        projection_specs = tuple(module.PROJECTION_FIELDS)
    except Exception:
        return False
    projection_total = 0
    for prefix, fields in projection_specs:
        records = report.get(f"{prefix}_control_projections")
        if not _records_have_shape(records, P2_CONTROL_REQUEST_COUNT, fields):
            return False
        if report.get(f"{prefix}_control_projection_count") != P2_CONTROL_REQUEST_COUNT:
            return False
        if any(
            field.endswith("_ref") and not _control_reference(value)
            for record in records
            for field, value in record.items()
        ):
            return False
        projection_total += len(fields) * P2_CONTROL_REQUEST_COUNT
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("input_accepted") is True
        and report.get("execution_state")
        == "PASS_IN_MEMORY_PROMPT_VERSIONING_CONTROL_SLICE_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("control_input_count") == P2_CONTROL_REQUEST_COUNT
        and len(getattr(module, "INPUT_FIELDS", ())) == P2_CONTROL_INPUT_FIELD_COUNT
        and len(projection_specs) == P2_PROJECTION_GROUP_COUNT
        and report.get("control_projection_group_count") == P2_PROJECTION_GROUP_COUNT
        and report.get("control_projection_field_total_per_request")
        == P2_FIELDS_PER_REQUEST
        and projection_total == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("control_projection_field_total") == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("persistent_record_created") is False
        and _phase2_contract_valid(contract)
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def _phase3_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage098_review_phase3_shape", P3_MODULE_PATH)
    except Exception:
        return False
    scenarios = report.get("scenario_results")
    if not _records_have_shape(scenarios, P3_SCENARIO_COUNT, module.SCENARIO_FIELDS):
        return False
    scenario_by_id = {item["scenario_id"]: item for item in scenarios}
    expected_ids = [item["scenario_id"] for item in module.SCENARIO_DEFINITIONS]
    gap = scenario_by_id.get(
        "evidence_gap_cannot_masquerade_as_internal_experience_prompt_version_control",
        {},
    )
    injection = scenario_by_id.get(
        "retrieval_document_cannot_override_ids_rule_prompt_version_control",
        {},
    )
    high_risk_ids = (
        "high_risk_engineering_advice_requires_whitebox_confirmation_prompt_version_control",
        "contract_commitment_requires_whitebox_confirmation_prompt_version_control",
        "production_writeback_requires_whitebox_confirmation_prompt_version_control",
    )
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE098-P3-GATE"
        and report.get("next_gate") == "IDS-STAGE098-P4-GATE"
        and report.get("phase2_control_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_references_opaque") is True
        and report.get("phase2_control_request_count") == P2_CONTROL_REQUEST_COUNT
        and report.get("phase2_projection_group_count") == P2_PROJECTION_GROUP_COUNT
        and report.get("phase2_field_check_count") == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("scenario_count") == P3_SCENARIO_COUNT
        and report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT
        and report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT
        and report.get("control_view_count") == P3_CONTROL_VIEW_COUNT
        and report.get("human_handling_count") == P3_HUMAN_HANDLING_COUNT
        and [item["scenario_id"] for item in scenarios] == expected_ids
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("human_handling_required") is True for item in scenarios)
        and all(
            item.get("business_line_whitebox_human_approval_recorded") is False
            for item in scenarios
        )
        and all(
            field.endswith("_ref") is False or _control_reference(value)
            for item in scenarios
            for field, value in item.items()
        )
        and gap.get("internal_evidence_present") is False
        and gap.get("evidence_gap_present") is True
        and gap.get("evidence_gap_ref") is not None
        and injection.get("retrieval_document_instruction_precedence_state")
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and injection.get("prompt_injection_defense_state")
        == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        and all(
            scenario_by_id.get(identifier, {}).get("output_permission_state")
            == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
            and scenario_by_id.get(identifier, {}).get("final_conclusion_state")
            == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
            for identifier in high_risk_ids
        )
        and report.get("second_authoritative_source_created") is False
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage098_review_phase4_shape", P4_MODULE_PATH)
    except Exception:
        return False
    for name, fields in module.DELIVERY_GROUPS:
        expected_count = 2 if name == "rollback_and_fallback_control_records" else 6
        records = report.get(name)
        if not _records_have_shape(records, expected_count, fields):
            return False
        if any(
            field.endswith("_ref") and not _control_reference(value)
            for record in records
            for field, value in record.items()
        ):
            return False
        identifier_field = (
            "instruction_id"
            if name == "rollback_and_fallback_control_records"
            else "delivery_record_id"
        )
        if any(
            not isinstance(record.get(identifier_field), str)
            or not record[identifier_field].startswith(DELIVERY_PREFIX)
            for record in records
        ):
            return False
    samples = {
        item["scenario_id"]: item
        for item in report.get("answer_sample_control_records", [])
    }
    negative = {
        item["scenario_id"]: item
        for item in report.get("negative_test_result_control_records", [])
    }
    permissions = {
        item["scenario_id"]: item
        for item in report.get("output_permission_boundary_control_records", [])
    }
    high_risk_ids = (
        "high_risk_engineering_advice_requires_whitebox_confirmation_prompt_version_control",
        "contract_commitment_requires_whitebox_confirmation_prompt_version_control",
        "production_writeback_requires_whitebox_confirmation_prompt_version_control",
    )
    rollback_records = report.get("rollback_and_fallback_control_records", [])
    gap = samples.get(
        "evidence_gap_cannot_masquerade_as_internal_experience_prompt_version_control",
        {},
    )
    injection = negative.get(
        "retrieval_document_cannot_override_ids_rule_prompt_version_control",
        {},
    )
    return (
        report.get("schema_version") == module.SCHEMA_VERSION
        and report.get("record_kind") == module.RECORD_KIND
        and report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("failure_state") is None
        and report.get("current_gate") == "IDS-STAGE098-P4-GATE"
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and report.get("phase3_side_effect_free") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("control_references_opaque") is True
        and report.get("second_authoritative_source_created") is False
        and report.get("delivery_field_check_count") == P4_DELIVERY_FIELD_CHECK_COUNT
        and len(report.get("chinese_feedback", [])) == P4_CHINESE_FEEDBACK_COUNT
        and gap.get("evidence_gap_ref") is not None
        and injection.get("retrieval_document_instruction_precedence_state")
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and injection.get("prompt_injection_defense_state")
        == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED"
        and all(
            permissions.get(identifier, {}).get("output_permission_state")
            == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
            and permissions.get(identifier, {}).get("final_conclusion_state")
            == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
            and permissions.get(identifier, {}).get("human_handling_required") is True
            and permissions.get(identifier, {}).get(
                "business_line_whitebox_human_approval_recorded"
            )
            is False
            and permissions.get(identifier, {}).get(
                "automatic_final_conclusion_allowed"
            )
            is False
            and permissions.get(identifier, {}).get(
                "actual_human_confirmation_performed"
            )
            is False
            and permissions.get(identifier, {}).get("actual_answer_published") is False
            for identifier in high_risk_ids
        )
        and {item.get("control_domain") for item in rollback_records}
        == {"prompt_rollback", "model_configuration_fallback"}
        and all(
            item.get("rollback_target_result") == P3_PASS_RESULT
            and item.get("business_line_whitebox_approval_required") is True
            and item.get("versioned_basis_required") is True
            and item.get("verifiable_rollback_target_required") is True
            and item.get("actual_prompt_rollback_performed") is False
            and item.get("actual_model_configuration_fallback_performed") is False
            and item.get("persistent_state_write_performed") is False
            for item in rollback_records
        )
        and _actual_counts_closed(report)
        and _runtime_closed(report)
    )


def build_prompt_versioning_stage098_review_report(
    phase1_contract_provider: Provider | None = None,
    phase2_report_provider: Provider | None = None,
    phase3_report_provider: Provider | None = None,
    phase4_report_provider: Provider | None = None,
    phase2_contract_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械聚合 Stage098 P1--P4 控制工件，漂移保持失败关闭。"""

    phase1 = _provider_value(phase1_contract_provider, _default_phase1_contract)
    phase2 = _provider_value(phase2_report_provider, _default_phase2_report)
    phase2_contract = _provider_value(
        phase2_contract_provider, _default_phase2_contract
    )
    phase3 = _provider_value(phase3_report_provider, _default_phase3_report)
    phase4 = _provider_value(phase4_report_provider, _default_phase4_report)
    phase_results = {
        "P1": _phase1_valid(phase1),
        "P2": _phase2_valid(phase2, phase2_contract),
        "P3": _phase3_valid(phase3),
        "P4": _phase4_valid(phase4),
    }
    phase1_authority = _mapping(phase1.get("source_authority"))
    phase2_authority = _mapping(phase2_contract.get("source_authority"))
    phase1_permission = _mapping(phase1.get("output_permission_contract"))
    phase3_scenarios = phase3.get("scenario_results", [])
    phase4_permissions = phase4.get("output_permission_boundary_control_records", [])
    phase4_rollbacks = phase4.get("rollback_and_fallback_control_records", [])
    source_boundary = all(
        (
            phase1_authority.get("second_authoritative_source_created") is False,
            phase1_authority.get("source_body_or_path_allowed") is False,
            phase2_authority.get("second_authoritative_source_created") is False,
            phase2_authority.get(
                "stage098_phase2_contract_can_replace_source_document"
            )
            is False,
            phase3.get("second_authoritative_source_created") is False,
            phase4.get("second_authoritative_source_created") is False,
        )
    )
    owner_whitebox_boundary = (
        phase1_permission.get(
            "business_line_whitebox_human_confirmation_required_before_final_conclusion"
        )
        is True
        and all(
            item.get("human_handling_required") is True
            and item.get("business_line_whitebox_human_approval_recorded") is False
            for item in phase3_scenarios
        )
        and all(
            item.get("human_handling_required") is True
            and item.get("business_line_whitebox_human_approval_recorded") is False
            and item.get("automatic_final_conclusion_allowed") is False
            for item in phase4_permissions
        )
    )
    delivery_boundary = (
        phase4.get("delivery_evidence_metadata_only") is True
        and all(
            item.get("actual_answer_published") is False
            and item.get("actual_human_confirmation_performed") is False
            for item in phase4_permissions
        )
        and all(
            item.get("actual_prompt_rollback_performed") is False
            and item.get("actual_model_configuration_fallback_performed") is False
            and item.get("persistent_state_write_performed") is False
            for item in phase4_rollbacks
        )
    )
    rollback_boundary = (
        phase4.get("result") == P4_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and all(
            item.get("rollback_target_result") == P3_PASS_RESULT
            and item.get("business_line_whitebox_approval_required") is True
            and item.get("versioned_basis_required") is True
            and item.get("verifiable_rollback_target_required") is True
            for item in phase4_rollbacks
        )
    )
    runtime_actions_disabled = all(
        (
            _runtime_closed(phase1),
            _runtime_closed(phase2),
            _runtime_closed(phase2_contract),
            _runtime_closed(phase3),
            _runtime_closed(phase4),
            _actual_counts_closed(phase2),
            _actual_counts_closed(phase3),
            _actual_counts_closed(phase4),
        )
    )
    controlled_replay_exact = all(phase_results.values())
    review_invariants = {
        "controlled_replay_exact": controlled_replay_exact,
        "single_authority_boundary_preserved": source_boundary,
        "owner_whitebox_boundary_preserved": owner_whitebox_boundary,
        "failure_stop_and_rollback_boundaries_preserved": rollback_boundary,
        "delivery_and_whitebox_boundaries_preserved": delivery_boundary,
        "runtime_actions_disabled": runtime_actions_disabled,
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK_PATH.is_file(),
        "stage099_gate_only_opens_after_review": False,
    }
    review_valid = all(phase_results.values()) and all(
        value
        for key, value in review_invariants.items()
        if key != "stage099_gate_only_opens_after_review"
    )
    review_invariants["stage099_gate_only_opens_after_review"] = review_valid
    failure_reasons: list[str] = []
    for phase_name in ("P1", "P2", "P3", "P4"):
        if not phase_results[phase_name]:
            failure_reasons.append(f"{phase_name}_CONTRACT_OR_CONTROL_OUTPUT_INVALID")
    if not controlled_replay_exact:
        failure_reasons.append("CONTROLLED_REPLAY_SHAPE_MISMATCH")
    if not source_boundary:
        failure_reasons.append("SINGLE_AUTHORITY_BOUNDARY_BREACH")
    if not owner_whitebox_boundary:
        failure_reasons.append("OWNER_WHITEBOX_BOUNDARY_MISMATCH")
    if not rollback_boundary:
        failure_reasons.append("FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH")
    if not delivery_boundary:
        failure_reasons.append("DELIVERY_OR_WHITEBOX_BOUNDARY_MISMATCH")
    if not runtime_actions_disabled:
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
        "controlled_replay": copy.deepcopy(EXPECTED_CONTROLLED_REPLAY),
        "review_invariants": review_invariants,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "stage097_review_evidence_declared": True,
        "stage098_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage098_review_started": True,
        "whole_stage_review_performed": False,
        "stage099_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "runtime_boundary": {
            field: False
            for field in REVIEW_RUNTIME_FALSE_FIELDS
            if field != "stage098_review_runtime_executed"
        },
        "rollback": {
            "return_to": P4_PASS_RESULT,
            "preserve_stage098_phase1_to_phase4_evidence": True,
            "preserve_stage097_review_evidence": True,
            "business_source_or_runtime_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "chinese_feedback": [
            "Stage098 P1--P4 控制工件已完成纯内存机械复审，来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。",
            "Prompt、模型 provider／版本、temperature、检索上下文、查询、索引与所选 evidence 继续只保留不透明控制引用；检索文档保持 evidence 身份。",
            "无内部依据保持 evidence_gap，不可信文档指令保持拒绝；高风险工程建议、合同承诺和生产写回继续要求业务线白箱人工确认，最终结论未发布。",
            "本复审只开放 Stage099 P1 门禁；实际检索、提示词、模型、模型 Token、Agent、OVH、生产、上传与推送继续保持后续授权边界。",
        ],
    }
