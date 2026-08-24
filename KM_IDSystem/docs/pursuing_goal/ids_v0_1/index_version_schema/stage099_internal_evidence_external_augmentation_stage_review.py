"""Stage099 内部依据与外部增强分离的纯内存整阶段复审。"""

from __future__ import annotations

import copy
import importlib.util
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.stage_review.v1"
)
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE099-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE100-P1-GATE"

P1_SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase1.v1"
)
P1_CONTRACT_STATE = "PHASE1_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SEPARATION_RUNTIME_DISABLED"
P2_SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase2.v1"
)
P2_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION"
P2_EXECUTION_STATE = (
    "PASS_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED"
)
P3_SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase3.v1"
)
P3_RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SCENARIOS"
P3_PASS_RESULT = (
    "PASS_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
)
P4_SCHEMA_VERSION = (
    "ids.stage099.internal_evidence_external_augmentation_separation.phase4.delivery.v1"
)
P4_RECORD_KIND = (
    "CONTROL_ONLY_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_DELIVERY_EVIDENCE"
)
P4_PASS_RESULT = (
    "PASS_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
)

P1_REFERENCE_FIELD_COUNT = 8
P1_SOURCE_TYPE_COUNT = 4
P1_HIGH_RISK_OUTPUT_COUNT = 3
P1_FAILURE_STATE_COUNT = 15
P1_CHINESE_FEEDBACK_COUNT = 4
P2_CONTROL_REQUEST_COUNT = 6
P2_CONTROL_INPUT_FIELD_COUNT = 19
P2_PROJECTION_GROUP_COUNT = 4
P2_FIELDS_PER_REQUEST = 35
P2_CONTROL_FIELD_CHECK_COUNT = 210
P3_SCENARIO_COUNT = 6
P3_SCENARIO_FIELD_COUNT = 28
P3_SCENARIO_FIELD_CHECK_COUNT = 168
P3_CONTROL_VIEW_COUNT = 5
P3_HUMAN_HANDLING_COUNT = 6
P3_FAILURE_STATE_COUNT = 15
P4_DELIVERY_SHAPE = "6/6/6/6/6/2"
P4_DELIVERY_FIELD_SHAPE = "14/12/11/11/12/12"
P4_DELIVERY_FIELD_CHECK_COUNT = 384
P4_CHINESE_FEEDBACK_COUNT = 4
P4_FAILURE_STATE_COUNT = 16

REVIEWED_CONTROL_SHAPE = {
    "phase1_reference_field_count": P1_REFERENCE_FIELD_COUNT,
    "phase1_source_type_count": P1_SOURCE_TYPE_COUNT,
    "phase1_high_risk_output_count": P1_HIGH_RISK_OUTPUT_COUNT,
    "phase1_failure_state_count": P1_FAILURE_STATE_COUNT,
    "phase1_chinese_feedback_count": P1_CHINESE_FEEDBACK_COUNT,
    "phase2_control_request_count": P2_CONTROL_REQUEST_COUNT,
    "phase2_control_input_field_count": P2_CONTROL_INPUT_FIELD_COUNT,
    "phase2_projection_group_count": P2_PROJECTION_GROUP_COUNT,
    "phase2_fields_per_request": P2_FIELDS_PER_REQUEST,
    "phase2_control_field_check_count": P2_CONTROL_FIELD_CHECK_COUNT,
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
    "stage099_review_runtime_executed",
)
REVIEW_ZERO_COUNT_FIELDS = (
    "actual_control_review_execution_count",
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
CONTROL_PREFIX = ":control:stage099-p2:"
DELIVERY_PREFIX = ":control:stage099-p4:"

Provider = Callable[[], Mapping[str, Any]]
BASE = Path(__file__).resolve().parent
P1_CONTRACT_PATH = (
    BASE / "stage099_internal_evidence_external_augmentation_separation_contract.json"
)
P2_MODULE_PATH = BASE / "stage099_internal_evidence_external_augmentation_control_slice.py"
P3_MODULE_PATH = (
    BASE / "stage099_internal_evidence_external_augmentation_controlled_scenarios.py"
)
P4_MODULE_PATH = BASE / "stage099_internal_evidence_external_augmentation_delivery.py"
NEXT_TASKPACK_PATH = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-100_无内部依据策略.md"
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
    module = _load_module("stage099_review_phase2", P2_MODULE_PATH)
    return module.execute_internal_evidence_external_augmentation_control_slice(
        module.build_control_input()
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module("stage099_review_phase3", P3_MODULE_PATH)
    return module.build_internal_evidence_external_augmentation_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module("stage099_review_phase4", P4_MODULE_PATH)
    return module.build_internal_evidence_external_augmentation_phase4_delivery_report()


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
        and value.startswith(CONTROL_PREFIX)
        and value.endswith(":reference-only")
    )


def _delivery_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(DELIVERY_PREFIX)
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
    separation = _mapping(contract.get("answer_separation_contract"))
    source_types = _mapping(separation.get("source_type_contract"))
    display = _mapping(source_types.get("external_augmentation_display_composition"))
    retrieval = _mapping(separation.get("retrieval_document_boundary"))
    gap = _mapping(separation.get("no_internal_evidence_strategy"))
    permission = _mapping(contract.get("output_permission_contract"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    feedback = _mapping(contract.get("chinese_feedback_contract"))
    local_code = _mapping(contract.get("local_code"))
    future = _mapping(contract.get("future_runtime_prerequisite_contract"))
    protected = _mapping(contract.get("protected_surface_boundary"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    return all(
        (
            contract.get("schema_version") == P1_SCHEMA_VERSION,
            contract.get("stage") == "STAGE-099",
            contract.get("phase") == "IDS-STAGE099-P1",
            contract.get("task_id") == "IDS-V0_1-STAGE099-P1",
            contract.get("contract_state") == P1_CONTRACT_STATE,
            contract.get("entry_gate") == "IDS-STAGE099-P1-GATE",
            contract.get("next_gate") == "IDS-STAGE099-P2-GATE",
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_whitebox_human_review_remains_authoritative")
            is True,
            all(
                authority.get(field) is False
                for field in (
                    "stage099_contract_can_replace_source_document",
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
            ),
            separation.get("answer_separation_reference_field_count")
            == P1_REFERENCE_FIELD_COUNT,
            isinstance(separation.get("future_answer_separation_reference_fields"), list),
            len(separation.get("future_answer_separation_reference_fields", []))
            == P1_REFERENCE_FIELD_COUNT,
            source_types.get("underlying_source_types")
            == [
                "internal_evidence",
                "external_public_reference",
                "model_reasoning",
                "evidence_gap",
            ],
            source_types.get("underlying_source_type_count") == P1_SOURCE_TYPE_COUNT,
            source_types.get("internal_evidence_and_external_augmentation_must_remain_separated")
            is True,
            source_types.get("external_augmentation_may_not_be_presented_as_internal_evidence")
            is True,
            source_types.get("evidence_gap_may_not_be_presented_as_internal_experience")
            is True,
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
                )
            ),
            all(
                retrieval.get(field) is True
                for field in (
                    "retrieval_document_is_evidence_not_system_instruction",
                    "retrieval_document_cannot_override_ids_rule",
                    "retrieval_document_cannot_be_system_instruction",
                )
            ),
            all(
                retrieval.get(field) is False
                for field in (
                    "actual_retrieval_document_read",
                    "actual_instruction_override_evaluated",
                )
            ),
            all(
                gap.get(field) is True
                for field in (
                    "evidence_gap_required_when_internal_evidence_absent",
                    "evidence_gap_may_not_be_reclassified_as_internal_evidence",
                    "evidence_gap_may_not_support_final_conclusion_without_whitebox_confirmation",
                )
            ),
            all(
                gap.get(field) is False
                for field in (
                    "actual_evidence_gap_assigned",
                    "actual_final_conclusion_generated",
                )
            ),
            len(_mapping(permission.get("classified_output_types")))
            == P1_HIGH_RISK_OUTPUT_COUNT,
            permission.get(
                "business_line_whitebox_human_confirmation_required_before_final_conclusion"
            )
            is True,
            all(
                permission.get(field) is False
                for field in (
                    "high_risk_engineering_advice_auto_finalization_allowed",
                    "contract_commitment_auto_finalization_allowed",
                    "production_writeback_auto_finalization_allowed",
                    "actual_output_classified",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                )
            ),
            failure.get("failure_state_count") == P1_FAILURE_STATE_COUNT,
            isinstance(failure.get("declared_failure_states"), list),
            len(failure.get("declared_failure_states", [])) == P1_FAILURE_STATE_COUNT,
            all(value is False for key, value in failure.items() if key.endswith("_allowed")),
            feedback.get("feedback_count") == P1_CHINESE_FEEDBACK_COUNT,
            len(feedback.get("feedbacks", [])) == P1_CHINESE_FEEDBACK_COUNT,
            feedback.get("actual_user_feedback_emitted") is False,
            local_code.get("static_contract_only") is True,
            all(
                value is False
                for key, value in local_code.items()
                if key != "static_contract_only"
            ),
            all(
                future.get(field) is False
                for field in (
                    "database_schema_created",
                    "database_migration_performed",
                    "database_connection_performed",
                    "retrieval_execution_performed",
                    "prompt_execution_performed",
                    "model_call_performed",
                    "model_output_classification_performed",
                    "citation_generation_performed",
                    "answer_publication_performed",
                    "production_writeback_performed",
                    "audit_log_write_performed",
                )
            ),
            _closed_runtime(contract),
            bool(protected) and all(value is False for value in protected.values()),
            boundary.get("phase1_completed") is True,
            boundary.get("whole_stage_review_performed") is False,
            boundary.get("stage100_started") is False,
            boundary.get("github_upload_allowed") is False,
            boundary.get("push_allowed") is False,
        )
    )


def _phase2_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage099_review_phase2_shape", P2_MODULE_PATH)
    except Exception:
        return False
    projections = tuple(getattr(module, "PROJECTION_FIELDS", ()))
    scenarios = tuple(getattr(module, "CONTROL_SCENARIOS", ()))
    if not all(
        (
            getattr(module, "SCHEMA_VERSION", None) == P2_SCHEMA_VERSION,
            getattr(module, "RECORD_KIND", None) == P2_RECORD_KIND,
            tuple(getattr(module, "CONTROL_FIELDS", ()))
            == ("internal_evidence_external_augmentation_control_requests",),
            len(getattr(module, "INPUT_FIELDS", ())) == P2_CONTROL_INPUT_FIELD_COUNT,
            len(scenarios) == P2_CONTROL_REQUEST_COUNT,
            len(projections) == P2_PROJECTION_GROUP_COUNT,
            report.get("schema_version") == P2_SCHEMA_VERSION,
            report.get("record_kind") == P2_RECORD_KIND,
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_EXECUTION_STATE,
            report.get("failure_state") is None,
            report.get("control_input_count") == P2_CONTROL_REQUEST_COUNT,
            report.get("control_projection_group_count") == P2_PROJECTION_GROUP_COUNT,
            report.get("control_projection_field_total_per_request")
            == P2_FIELDS_PER_REQUEST,
            report.get("control_projection_field_total") == P2_CONTROL_FIELD_CHECK_COUNT,
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
    source_records = records_by_name[
        "source_type_and_external_augmentation_opinion_display"
    ]
    permission_records = records_by_name["prompt_injection_and_output_permission"]
    if not all(
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
        == "CONTROL_EXTERNAL_AUGMENTATION_OPINION_IS_DISPLAY_LABEL_ONLY"
        and record.get("display_preserves_underlying_source_types_state")
        == "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES"
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
    ):
        return False
    if not all(
        record.get("retrieval_document_instruction_precedence_state")
        == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL"
        and record.get("final_conclusion_state")
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        for record in permission_records
    ):
        return False
    gap = source_records[1]
    injection = permission_records[2]
    return all(
        (
            gap.get("internal_evidence_ref") is None,
            _control_ref(gap.get("evidence_gap_ref")),
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
        module = _load_module("stage099_review_phase3_shape", P3_MODULE_PATH)
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
            report.get("current_gate") == "IDS-STAGE099-P3-GATE",
            report.get("next_gate") == "IDS-STAGE099-P4-GATE",
            report.get("phase2_control_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("control_references_opaque") is True,
            report.get("second_authoritative_source_created") is False,
            report.get("persistent_record_created") is False,
            report.get("phase2_control_request_count") == P2_CONTROL_REQUEST_COUNT,
            report.get("phase2_projection_group_count") == P2_PROJECTION_GROUP_COUNT,
            report.get("phase2_field_check_count") == P2_CONTROL_FIELD_CHECK_COUNT,
            report.get("scenario_count") == P3_SCENARIO_COUNT,
            report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT,
            report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT,
            report.get("control_view_count") == P3_CONTROL_VIEW_COUNT,
            report.get("human_handling_count") == P3_HUMAN_HANDLING_COUNT,
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
        not _records_have_shape(
            views.get(name), P3_SCENARIO_COUNT, fields
        )
        for name, fields in module.CONTROL_VIEW_FIELDS.items()
    ):
        return False
    if not isinstance(handlings, list) or len(handlings) != P3_HUMAN_HANDLING_COUNT:
        return False
    by_id = {item["scenario_id"]: item for item in scenarios}
    if not all(
        item.get("expectation_met") is True
        and item.get("human_handling_required") is True
        and item.get("business_line_whitebox_human_approval_recorded") is False
        and item.get("final_conclusion_state")
        == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
        and all(
            _control_ref(item.get(field), optional=field in {"internal_evidence_ref", "evidence_gap_ref"})
            for field in (
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_version_ref",
                "selected_evidence_ref",
                "internal_evidence_ref",
                "external_public_reference_ref",
                "model_reasoning_ref",
                "evidence_gap_ref",
                "human_confirmation_gate_ref",
                "external_augmentation_ref",
            )
        )
        for item in scenarios
    ):
        return False
    external, gap, injection = (by_id[scenario_ids[index]] for index in range(3))
    if not all(
        (
            external.get("external_augmentation_display_label")
            == "external_augmentation_opinion",
            external.get("display_label_is_not_source_type_state")
            == "CONTROL_EXTERNAL_AUGMENTATION_OPINION_IS_DISPLAY_LABEL_ONLY",
            external.get("display_preserves_underlying_source_types_state")
            == "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES",
            gap.get("internal_evidence_ref") is None,
            gap.get("internal_evidence_present") is False,
            gap.get("evidence_gap_present") is True,
            _control_ref(gap.get("evidence_gap_ref")),
            injection.get("prompt_injection_defense_state")
            == "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            injection.get("output_permission_state")
            == "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
        )
    ):
        return False
    return all(
        by_id[scenario_id].get("output_permission_state")
        == "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION"
        for scenario_id in scenario_ids[3:]
    )


def _phase4_valid(report: Mapping[str, Any]) -> bool:
    try:
        module = _load_module("stage099_review_phase4_shape", P4_MODULE_PATH)
    except Exception:
        return False
    groups = tuple(getattr(module, "DELIVERY_GROUPS", ()))
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
            report.get("current_gate") == "IDS-STAGE099-P4-GATE",
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
        )
    ):
        return False
    expected_counts = {
        "answer_sample_control_records": P3_SCENARIO_COUNT,
        "negative_test_result_control_records": P3_SCENARIO_COUNT,
        "prompt_version_control_records": P3_SCENARIO_COUNT,
        "reproducible_log_control_records": P3_SCENARIO_COUNT,
        "output_permission_boundary_control_records": P3_SCENARIO_COUNT,
        "rollback_and_fallback_control_records": 2,
    }
    if tuple(name for name, _fields in groups) != tuple(expected_counts):
        return False
    if any(
        not _records_have_shape(report.get(name), expected_counts[name], fields)
        for name, fields in groups
    ):
        return False
    negatives = {
        item["scenario_id"]: item
        for item in report["negative_test_result_control_records"]
    }
    permissions = {
        item["scenario_id"]: item
        for item in report["output_permission_boundary_control_records"]
    }
    answer_samples = report["answer_sample_control_records"]
    rollbacks = report["rollback_and_fallback_control_records"]
    injection_id = (
        "retrieval_document_cannot_override_ids_rule_separation_control"
    )
    high_risk_ids = (
        "high_risk_engineering_advice_requires_whitebox_confirmation_separation_control",
        "contract_commitment_requires_whitebox_confirmation_separation_control",
        "production_writeback_requires_whitebox_confirmation_separation_control",
    )
    return all(
        _delivery_ref(item.get("delivery_record_id"))
        and item.get("answer_sample_state")
        == "CONTROL_RAG_ANSWER_SAMPLE_REFERENCE_ONLY_NOT_EXECUTED"
        and item.get("actual_answer_published") is False
        and item.get("business_line_whitebox_human_handling_required") is True
        for item in answer_samples
    ) and all(
        (
            negatives[injection_id].get("retrieval_document_instruction_precedence_state")
            == "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            negatives[injection_id].get("prompt_injection_defense_state")
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


def build_internal_evidence_external_augmentation_stage099_review_report(
    phase1_contract_provider: Provider | None = None,
    phase2_report_provider: Provider | None = None,
    phase3_report_provider: Provider | None = None,
    phase4_report_provider: Provider | None = None,
) -> dict[str, Any]:
    """机械聚合 Stage099 P1--P4 控制工件，任何漂移保持失败关闭。"""

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
    phase3_scenarios = phase3.get("scenario_results", [])
    phase4_permissions = phase4.get("output_permission_boundary_control_records", [])
    phase4_rollbacks = phase4.get("rollback_and_fallback_control_records", [])
    source_boundary = all(
        (
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            phase3.get("second_authoritative_source_created") is False,
            phase4.get("second_authoritative_source_created") is False,
        )
    )
    semantic_boundary = all(
        (
            phase_results["P1"],
            phase_results["P2"],
            phase_results["P3"],
            phase_results["P4"],
        )
    )
    owner_whitebox_boundary = (
        isinstance(phase3_scenarios, list)
        and bool(phase3_scenarios)
        and isinstance(phase4_permissions, list)
        and bool(phase4_permissions)
        and all(
            _mapping(item).get("human_handling_required") is True
            and _mapping(item).get("business_line_whitebox_human_approval_recorded")
            is False
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
            and _mapping(item).get("business_line_whitebox_approval_required") is True
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
        "stage100_gate_only_opens_after_review": False,
    }
    review_valid = all(
        value
        for key, value in review_invariants.items()
        if key != "stage100_gate_only_opens_after_review"
    )
    review_invariants["stage100_gate_only_opens_after_review"] = review_valid
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
        "controlled_replay": copy.deepcopy(REVIEWED_CONTROL_SHAPE),
        "review_invariants": review_invariants,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "stage098_review_evidence_declared": True,
        "stage099_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage099_review_control_report_generated_in_memory_only": True,
        "stage100_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "chinese_feedback": [
            "Stage099 P1 至 P4 的控制形状、来源类型、提示注入防护、输出权限和回退前置保持一致，复审结果只承载控制结论。",
            "来源文档与业务线白箱人工复核继续承担业务事实权威；检索文档保持 evidence 身份，无内部依据保持 evidence_gap。",
            "高风险工程建议、合同承诺和生产写回保持业务线白箱人工处理，人工确认未记录，最终结论未发布。",
            "Stage100 只开放下一门禁；真实资料、检索、提示词、模型、模型 Token、Agent、OVH、生产与上传保持后续授权边界。",
        ],
        **{field: 0 for field in REVIEW_ZERO_COUNT_FIELDS},
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "runtime_boundary": {
            field: False
            for field in REVIEW_RUNTIME_FALSE_FIELDS
            if field != "stage099_review_runtime_executed"
        },
        "rollback": {
            "return_to": P4_PASS_RESULT,
            "preserve_stage099_phase1_to_phase4_evidence": True,
            "preserve_stage098_review_evidence": True,
            "preserve_frozen_taskpack": True,
            "preserve_business_source_authority": True,
            "business_source_or_runtime_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
    }
