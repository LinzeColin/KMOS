"""Stage068 的只读整阶段机械复审，不读取真实资料或启动 Stage069。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-068_质量降级而非只判失败.md"
)
P1_CONTRACT = BASE / "stage068_quality_degradation_contract.json"
P2_CONTRACT = BASE / "stage068_quality_degradation_slice_contract.json"
P3_CONTRACT = BASE / "stage068_quality_degradation_scenarios_contract.json"
P4_CONTRACT = BASE / "stage068_quality_degradation_delivery_contract.json"

SCHEMA_VERSION = "ids.stage068.quality_degradation.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE068-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-068"
PASS_RESULT = "PASS_REVIEWED_LOCAL_QUALITY_DEGRADATION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_QUALITY_DEGRADATION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE068-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE069-P1-GATE"
RETURN_STATE = "PHASE4_QUALITY_DEGRADATION_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED"
P3_PASS_RESULT = "PASS_PHASE3_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PHASE4_QUALITY_DEGRADATION_DELIVERY_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "long-document-quality-degradation-control-human-review",
    "cross-page-table-quality-degradation-control-human-handling",
    "engineering-procedure-quality-degradation-control-human-review",
    "parameter-table-quality-degradation-control-human-review",
    "citation-page-quality-degradation-control-human-confirmation",
    "duplicate-chunk-quality-degradation-control-human-review",
)
RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chapter_detection_performed",
    "chunking_execution_performed",
    "chunk_identity_generation_performed",
    "chunk_hash_computation_performed",
    "chunk_version_generation_performed",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "low_confidence_evidence_creation_performed",
    "source_traceability_binding_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)
P3_REPORT_RUNTIME_FALSE_FIELDS = tuple(
    field
    for field in RUNTIME_FALSE_FIELDS
    if field
    not in {
        "chunk_identity_generation_performed",
        "chunk_hash_computation_performed",
        "chunk_version_generation_performed",
    }
) + (
    "actual_chunk_id_generated",
    "actual_chunk_hash_computed",
    "actual_chunk_version_generated",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]
MISSING = object()


def build_stage068_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage068 P1--P4，只返回控制事实、门禁与回退结论。"""

    phase1 = _mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    scenario_report = _mapping(
        (phase3_report_provider or _load_report_provider(
            "stage068_quality_degradation_scenarios.py",
            "build_quality_degradation_phase3_report",
        ))()
    )
    delivery_report = _mapping(
        (phase4_report_provider or _load_report_provider(
            "stage068_quality_degradation_delivery.py",
            "build_quality_degradation_phase4_delivery_report",
        ))()
    )
    phase_results = {
        "P1": _p1_valid(phase1),
        "P2": _p2_valid(phase2),
        "P3": _p3_contract_valid(phase3) and _p3_report_valid(scenario_report),
        "P4": _p4_contract_valid(phase4) and _p4_report_valid(delivery_report),
    }
    replay = _controlled_replay(phase1, phase2, phase3, phase4, scenario_report, delivery_report)
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "quality_degradation_control_shape_preserved": _shape_valid(replay),
        "six_special_scenarios_require_whitebox_human_handling": _human_handling(
            scenario_report, delivery_report
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary(
            delivery_report
        ),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain(
            phase4, delivery_report
        ),
        "future_stage_ownership_preserved": _future_stage_boundary(
            phase1, phase2, phase3, phase4
        ),
        "runtime_actions_disabled": _runtime_closed(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "stage069_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE068_TASKPACK_AND_STAGE068_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "reviewed_phase_ids": ("P1", "P2", "P3", "P4"),
        "phase_results": phase_results,
        "controlled_replay": replay,
        "review_invariants": invariants,
        "review_finding_count": 0,
        "review_valid": False,
        "result": FAIL_RESULT,
        "rollback": {
            "return_to": RETURN_STATE,
            "revertable_artifacts": (
                "Stage068 review document",
                "Stage068 review module",
                "Stage068 review focused tests",
                "Stage068 review governance projection",
            ),
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": REVIEW_GATE,
        **{field: False for field in RUNTIME_FALSE_FIELDS},
        "actual_chunk_jsonl_written": False,
        "actual_quality_measurement_performed": False,
        "actual_quality_regression_performed": False,
        "actual_quality_degradation_performed": False,
        "actual_low_quality_chunk_observed": False,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "stage068_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage069_started": False,
        "stage069_entry_allowed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_performed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        report["review_invariants"]["runtime_actions_disabled"]
        and _all_false(report, RUNTIME_FALSE_FIELDS)
        and _all_false(
            report,
            (
                "actual_chunk_jsonl_written",
                "actual_quality_measurement_performed",
                "actual_quality_regression_performed",
                "actual_quality_degradation_performed",
                "actual_low_quality_chunk_observed",
                "actual_chunk_regeneration_performed",
                "actual_chunk_version_rollback_performed",
                "batch_review_performed",
                "stage069_started",
                "stage069_entry_allowed",
                "github_upload_performed",
                "github_upload_allowed",
                "push_performed",
                "push_allowed",
            ),
        )
    )
    report["review_valid"] = all(phase_results.values()) and all(invariants.values())
    report["review_finding_count"] = 0 if report["review_valid"] else 1
    report["result"] = PASS_RESULT if report["review_valid"] else FAIL_RESULT
    report["next_gate"] = NEXT_GATE if report["review_valid"] else REVIEW_GATE
    return report


def _p1_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase1.v1"),
            ("contract_state", "PHASE1_QUALITY_DEGRADATION_CONTRACT_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE068-P1"),
            ("next_gate", "IDS-STAGE068-P2-GATE"),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("reference_only_quality_degradation_input_contract.field_count", 13),
            ("reference_only_quality_degradation_input_contract.actual_input_request_count", 0),
            ("reference_only_quality_degradation_input_contract.document_body_allowed", False),
            ("future_quality_degradation_output_contract.field_count", 19),
            ("future_quality_degradation_output_contract.actual_quality_degradation_record_created", False),
            ("quality_degradation_definition_contract.declared_future_disposition_count", 2),
            ("quality_degradation_definition_contract.low_quality_is_not_automatically_complete_failure", True),
            ("quality_degradation_definition_contract.quality_degradation_is_future_control_only", True),
            ("protected_semantic_boundary_contract.protected_semantic_asset_type_count", 3),
            ("protected_semantic_boundary_contract.engineering_procedure_step_split_allowed", False),
            ("protected_semantic_boundary_contract.acceptance_clause_split_allowed", False),
            ("protected_semantic_boundary_contract.parameter_table_split_allowed", False),
            ("traceability_contract.traceability_field_count", 6),
            ("traceability_contract.actual_traceability_binding_count", 0),
            ("duplicate_embedding_index_boundary_contract.duplicate_chunk_must_not_repeat_embedding_or_index_write", True),
            ("duplicate_embedding_index_boundary_contract.duplicate_embedding_or_index_write_attempted", False),
            ("authority_and_decision_boundary.source_document_remains_authoritative", True),
            ("authority_and_decision_boundary.quality_degradation_can_replace_source_document", False),
            ("authority_and_decision_boundary.quality_degradation_can_become_business_fact_authority", False),
            ("failure_and_stop_contract.failure_state_count", 17),
            ("failure_and_stop_contract.automatic_business_write_allowed", False),
            ("future_stage_interface_boundary.quality_degradation_execution_owner", "STAGE-068"),
            ("future_stage_interface_boundary.external_api_strategy_owner", "STAGE-069"),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p2_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase2.v1"),
            ("contract_state", "PHASE2_QUALITY_DEGRADATION_CONTROL_SLICE_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE068-P2"),
            ("next_gate", "IDS-STAGE068-P3-GATE"),
            ("slice_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("reference_only_quality_degradation_input_control_contract.field_count", 13),
            ("reference_only_quality_degradation_input_control_contract.control_request_count", 4),
            ("reference_only_quality_degradation_input_control_contract.actual_input_request_count", 0),
            ("control_quality_degradation_record_contract.field_count", 19),
            ("control_quality_degradation_record_contract.control_record_count", 4),
            ("control_quality_degradation_record_contract.actual_quality_degradation_record_created", False),
            ("control_quality_degradation_record_contract.business_line_whitebox_review_record_count", 3),
            ("control_quality_degradation_record_contract.low_confidence_evidence_review_record_count", 1),
            ("quality_protection_and_duplicate_boundary_contract.protected_semantic_asset_type_count", 3),
            ("quality_protection_and_duplicate_boundary_contract.protected_surface_split_allowed", False),
            ("quality_protection_and_duplicate_boundary_contract.duplicate_chunk_must_not_repeat_embedding_or_index_write", True),
            ("traceability_contract.traceability_field_count", 6),
            ("traceability_contract.control_traceability_reference_count", 24),
            ("traceability_contract.actual_traceability_binding_count", 0),
            ("authority_and_decision_boundary.source_document_remains_authoritative", True),
            ("authority_and_decision_boundary.quality_degradation_can_become_business_fact_authority", False),
            ("failure_and_stop_contract.failure_state_count", 15),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase3.controlled_scenarios_contract.v1"),
            ("contract_state", "PHASE3_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE068-P3"),
            ("next_gate", "IDS-STAGE068-P4-GATE"),
            ("scenario_executable", True),
            ("execution_ready", False),
            ("source_authority.source_document_remains_authoritative", True),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.control_references_are_not_business_facts", True),
            ("scenario_input_boundary.phase2_control_record_count", 4),
            ("scenario_input_boundary.phase2_control_record_field_count", 19),
            ("scenario_input_boundary.scenario_count", 6),
            ("scenario_input_boundary.scenario_category_is_control_metadata", True),
            ("scenario_input_boundary.actual_input_request_count", 0),
            ("scenario_validation.all_taskpack_special_scenarios_covered", True),
            ("scenario_validation.explicit_disposition_required", True),
            ("scenario_validation.silent_drop_allowed", False),
            ("scenario_validation.business_line_human_handling_required", True),
            ("scenario_validation.low_quality_is_not_automatic_complete_failure", True),
            ("scenario_validation.control_traceability_field_count", 6),
            ("scenario_validation.control_traceability_reference_check_count", 36),
            ("scenario_validation.unique_control_quality_degradation_record_count", 4),
            ("scenario_validation.actual_quality_degradation_validated", False),
            ("duplicate_embedding_and_index_boundary.control_duplicate_write_prohibition_asserted", True),
            ("duplicate_embedding_and_index_boundary.embedding_or_index_write_attempted", False),
            ("duplicate_embedding_and_index_boundary.deduplication_effect_claim_allowed", False),
            ("authority_and_decision_boundary.source_document_remains_authoritative", True),
            ("authority_and_decision_boundary.quality_degradation_control_record_can_replace_source_document", False),
            ("authority_and_decision_boundary.quality_degradation_control_record_can_become_business_fact_authority", False),
            ("rollback_contract.return_to", "PHASE2_QUALITY_DEGRADATION_CONTROL_SLICE_RUNTIME_DISABLED"),
            ("rollback_contract.phase1_and_phase2_artifacts_preserved", True),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase4.delivery_contract.v1"),
            ("contract_state", "PHASE4_QUALITY_DEGRADATION_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE068-P4"),
            ("entry_gate", "IDS-STAGE068-P4-GATE"),
            ("next_gate", REVIEW_GATE),
            ("delivery_executable", True),
            ("execution_ready", False),
            ("source_authority.source_document_remains_authoritative", True),
            ("source_authority.business_line_white_box_human_review_remains_authoritative", True),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.delivery_control_metadata_can_replace_source_document", False),
            ("source_authority.delivery_control_metadata_can_become_business_fact_authority", False),
            ("source_authority.real_source_content_retained", False),
            ("predecessor_boundary.phase3_controlled_scenarios_reused_as_reference_only", True),
            ("predecessor_boundary.phase3_result_required", P3_PASS_RESULT),
            ("predecessor_boundary.expected_control_scenario_count", 6),
            ("predecessor_boundary.expected_unique_control_quality_degradation_record_count", 4),
            ("predecessor_boundary.expected_control_traceability_field_count", 6),
            ("predecessor_boundary.expected_control_traceability_reference_check_count", 36),
            ("delivery_artifacts.chunk_jsonl_samples.sample_count", 6),
            ("delivery_artifacts.chunk_jsonl_samples.metadata_only", True),
            ("delivery_artifacts.chunk_jsonl_samples.actual_jsonl_file_written", False),
            ("delivery_artifacts.coverage_report.control_scenario_count", 6),
            ("delivery_artifacts.coverage_report.control_traceability_reference_check_count", 36),
            ("delivery_artifacts.coverage_report.coverage_can_support_real_quality_claim", False),
            ("delivery_artifacts.low_quality_chunk_list.control_item_count", 6),
            ("delivery_artifacts.low_quality_chunk_list.all_items_require_human_review", True),
            ("delivery_artifacts.low_quality_chunk_list.actual_low_quality_chunk_observed", False),
            ("delivery_artifacts.regression_test_results.control_scenario_count", 6),
            ("delivery_artifacts.regression_test_results.silent_drop_count", 0),
            ("delivery_artifacts.regression_test_results.actual_quality_regression_performed", False),
            ("chunking_strategy_applicability_boundary.strategy_boundary_is_control_metadata_only", True),
            ("chunking_strategy_applicability_boundary.unverified_boundary_cannot_trigger_automatic_chunk_write", True),
            ("chunking_strategy_applicability_boundary.unverified_boundary_cannot_trigger_automatic_quality_degradation", True),
            ("chunking_strategy_applicability_boundary.actual_production_quality_claim_allowed", False),
            ("regeneration_and_version_rollback.rollback_target_result", P3_PASS_RESULT),
            ("regeneration_and_version_rollback.in_memory_control_replay_only", True),
            ("regeneration_and_version_rollback.phase1_phase2_phase3_artifacts_preserved", True),
            ("regeneration_and_version_rollback.actual_chunk_regeneration_performed", False),
            ("regeneration_and_version_rollback.actual_chunk_version_rollback_performed", False),
            ("regeneration_and_version_rollback.github_or_ovh_change_allowed", False),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("failure_and_stop_contract.automatic_business_write_allowed", False),
        ),
    ) and tuple(_get(contract, "predecessor_boundary.expected_scenario_ids", ())) == EXPECTED_SCENARIO_IDS and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _sequence(report.get("scenario_results"))
    return _checks(
        report,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase3.controlled_scenarios.v1"),
            ("valid", True),
            ("result", P3_PASS_RESULT),
            ("next_gate", "IDS-STAGE068-P4-GATE"),
            ("scenario_count", 6),
            ("passed_scenario_count", 6),
            ("explicit_disposition_count", 6),
            ("silent_drop_count", 0),
            ("human_handling_required_count", 6),
            ("all_taskpack_special_scenarios_covered", True),
            ("phase2_control_slice_reexecuted", True),
            ("phase2_shape_preserved", True),
            ("unique_control_quality_degradation_record_count", 4),
            ("control_traceability_field_count", 6),
            ("control_traceability_reference_check_count", 36),
            ("control_traceability_reference_shape_preserved", True),
            ("low_quality_is_not_automatic_complete_failure", True),
            ("source_document_remains_authoritative", True),
            ("quality_degradation_control_record_can_replace_source_document", False),
            ("quality_degradation_control_record_can_become_business_fact_authority", False),
        ),
    ) and _scenario_ids(scenarios) == EXPECTED_SCENARIO_IDS and _all_false(
        report, P3_REPORT_RUNTIME_FALSE_FIELDS
    )


def _p4_report_valid(report: Mapping[str, Any]) -> bool:
    samples = _sequence(report.get("chunk_jsonl_samples"))
    low_quality = _sequence(report.get("low_quality_chunk_list"))
    return _checks(
        report,
        (
            ("schema_version", "ids.stage068.quality_degradation.phase4.delivery.v1"),
            ("valid", True),
            ("result", P4_PASS_RESULT),
            ("entry_gate", "IDS-STAGE068-P4-GATE"),
            ("next_gate", REVIEW_GATE),
            ("phase3_controlled_scenarios_reused_as_reference_only", True),
            ("phase3_controlled_scenarios_report_valid", True),
            ("actual_jsonl_file_written", False),
            ("coverage_report.control_delivery_coverage_complete", True),
            ("coverage_report.control_delivery_coverage_only", True),
            ("coverage_report.control_scenario_count", 6),
            ("coverage_report.unique_control_quality_degradation_record_count", 4),
            ("coverage_report.control_traceability_reference_check_count", 36),
            ("regression_test_results.control_regression_consistent", True),
            ("regression_test_results.control_scenario_count", 6),
            ("regression_test_results.silent_drop_count", 0),
            ("chunking_strategy_applicability_boundary.strategy_boundary_is_control_metadata_only", True),
            ("chunking_strategy_applicability_boundary.actual_production_quality_claim_allowed", False),
            ("regeneration_and_version_rollback_instructions.rollback_target_result", P3_PASS_RESULT),
            ("regeneration_and_version_rollback_instructions.in_memory_control_replay_only", True),
            ("regeneration_and_version_rollback_instructions.phase1_phase2_phase3_artifacts_preserved", True),
            ("source_document_remains_authoritative", True),
            ("business_line_white_box_human_review_remains_authoritative", True),
            ("delivery_control_metadata_can_replace_source_document", False),
            ("delivery_control_metadata_can_become_business_fact_authority", False),
            ("real_source_content_retained", False),
        ),
    ) and len(samples) == 6 and len(low_quality) == 6 and _scenario_ids(samples) == EXPECTED_SCENARIO_IDS and all(_mapping(item).get("human_review_required") is True for item in samples) and _low_quality_items_require_human_review(low_quality) and len(_sequence(report.get("human_confirmation_prompts_zh"))) == 3 and _all_false(report, RUNTIME_FALSE_FIELDS)


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "phase1_reference_input_field_count": _get(phase1, "reference_only_quality_degradation_input_contract.field_count"),
        "phase1_future_output_field_count": _get(phase1, "future_quality_degradation_output_contract.field_count"),
        "phase1_protected_semantic_asset_type_count": _get(phase1, "protected_semantic_boundary_contract.protected_semantic_asset_type_count"),
        "phase1_traceability_field_count": _get(phase1, "traceability_contract.traceability_field_count"),
        "phase1_failure_state_count": _get(phase1, "failure_and_stop_contract.failure_state_count"),
        "phase2_control_request_count": _get(phase2, "reference_only_quality_degradation_input_control_contract.control_request_count"),
        "phase2_control_record_count": _get(phase2, "control_quality_degradation_record_contract.control_record_count"),
        "phase2_control_record_field_count": _get(phase2, "control_quality_degradation_record_contract.field_count"),
        "phase2_control_traceability_reference_count": _get(phase2, "traceability_contract.control_traceability_reference_count"),
        "phase3_scenario_count": scenario_report.get("scenario_count"),
        "phase3_explicit_disposition_count": scenario_report.get("explicit_disposition_count"),
        "phase3_silent_drop_count": scenario_report.get("silent_drop_count"),
        "phase3_unique_control_record_count": scenario_report.get("unique_control_quality_degradation_record_count"),
        "phase3_traceability_reference_check_count": scenario_report.get("control_traceability_reference_check_count"),
        "phase4_metadata_only_jsonl_sample_count": len(_sequence(delivery_report.get("chunk_jsonl_samples"))),
        "phase4_low_quality_human_review_item_count": len(_sequence(delivery_report.get("low_quality_chunk_list"))),
        "phase4_chinese_confirmation_count": len(_sequence(delivery_report.get("human_confirmation_prompts_zh"))),
        "phase4_failure_state_count": _get(phase4, "failure_and_stop_contract.failure_state_count"),
    }


def _shape_valid(replay: Mapping[str, Any]) -> bool:
    expected = {
        "phase1_reference_input_field_count": 13,
        "phase1_future_output_field_count": 19,
        "phase1_protected_semantic_asset_type_count": 3,
        "phase1_traceability_field_count": 6,
        "phase1_failure_state_count": 17,
        "phase2_control_request_count": 4,
        "phase2_control_record_count": 4,
        "phase2_control_record_field_count": 19,
        "phase2_control_traceability_reference_count": 24,
        "phase3_scenario_count": 6,
        "phase3_explicit_disposition_count": 6,
        "phase3_silent_drop_count": 0,
        "phase3_unique_control_record_count": 4,
        "phase3_traceability_reference_check_count": 36,
        "phase4_metadata_only_jsonl_sample_count": 6,
        "phase4_low_quality_human_review_item_count": 6,
        "phase4_chinese_confirmation_count": 3,
        "phase4_failure_state_count": 12,
    }
    return all(replay.get(key) == value for key, value in expected.items())


def _single_authority(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "source_authority.second_authoritative_source_created") is False,
            _get(phase2, "source_authority.second_authoritative_source_created") is False,
            _get(phase3, "source_authority.second_authoritative_source_created") is False,
            _get(phase4, "source_authority.second_authoritative_source_created") is False,
            scenario_report.get("source_document_remains_authoritative") is True,
            scenario_report.get("quality_degradation_control_record_can_become_business_fact_authority") is False,
            delivery_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("business_line_white_box_human_review_remains_authoritative") is True,
            delivery_report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
        )
    )


def _human_handling(
    scenario_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    samples = _sequence(delivery_report.get("chunk_jsonl_samples"))
    low_quality = _sequence(delivery_report.get("low_quality_chunk_list"))
    return all(
        (
            scenario_report.get("human_handling_required_count") == 6,
            scenario_report.get("explicit_disposition_count") == 6,
            scenario_report.get("silent_drop_count") == 0,
            len(samples) == 6,
            all(_mapping(item).get("human_review_required") is True for item in samples),
            len(low_quality) == 6,
            _low_quality_items_require_human_review(low_quality),
        )
    )


def _delivery_boundary(report: Mapping[str, Any]) -> bool:
    samples = _sequence(report.get("chunk_jsonl_samples"))
    return all(
        (
            report.get("actual_jsonl_file_written") is False,
            report.get("actual_delivery_file_written") is False,
            report.get("actual_quality_degradation_delivery_implementation_performed") is False,
            len(samples) == 6,
            all(_mapping(item).get("control_metadata_only") is True for item in samples),
            _get(report, "coverage_report.control_delivery_coverage_only") is True,
            _get(report, "coverage_report.coverage_can_support_real_quality_claim") is False,
            _get(report, "regression_test_results.control_regression_consistent") is True,
            _get(report, "regression_test_results.actual_quality_regression_performed") is False,
        )
    )


def _rollback_chain(phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]) -> bool:
    return all(
        (
            _get(phase4, "regeneration_and_version_rollback.rollback_target_result") == P3_PASS_RESULT,
            _get(phase4, "regeneration_and_version_rollback.in_memory_control_replay_only") is True,
            _get(phase4, "regeneration_and_version_rollback.phase1_phase2_phase3_artifacts_preserved") is True,
            _get(delivery_report, "regeneration_and_version_rollback_instructions.rollback_target_result") == P3_PASS_RESULT,
            _get(delivery_report, "regeneration_and_version_rollback_instructions.in_memory_control_replay_only") is True,
            _get(delivery_report, "regeneration_and_version_rollback_instructions.phase1_phase2_phase3_artifacts_preserved") is True,
            _get(delivery_report, "regeneration_and_version_rollback_instructions.actual_chunk_regeneration_performed") is False,
            _get(delivery_report, "regeneration_and_version_rollback_instructions.actual_chunk_version_rollback_performed") is False,
        )
    )


def _future_stage_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        _get(phase1, "future_stage_interface_boundary.external_api_strategy_owner")
        == "STAGE-069"
        and all(
            _get(contract, "runtime_boundary.stage069_started") is False
            and _get(contract, "runtime_boundary.stage069_entry_allowed") is False
            for contract in (phase1, phase2, phase3, phase4)
        )
    )


def _low_quality_items_require_human_review(items: Sequence[Any]) -> bool:
    return all(
        _mapping(item).get("quality_disposition")
        == "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW"
        and "人工" in str(_mapping(item).get("recommendation_zh", ""))
        and _mapping(item).get("control_metadata_only") is True
        and _mapping(item).get("automatic_quality_degradation_action_performed") is False
        for item in items
    )


def _runtime_closed(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _runtime_boundary_closed(_mapping(phase1.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase2.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase3.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase4.get("runtime_boundary"))),
            _all_false(scenario_report, P3_REPORT_RUNTIME_FALSE_FIELDS),
            _all_false(delivery_report, RUNTIME_FALSE_FIELDS),
        )
    )


def _runtime_boundary_closed(boundary: Mapping[str, Any]) -> bool:
    return _all_false(boundary, RUNTIME_FALSE_FIELDS)


def _checks(mapping: Mapping[str, Any], checks: Sequence[tuple[str, Any]]) -> bool:
    return all(_get(mapping, path) == expected for path, expected in checks)


def _get(mapping: Mapping[str, Any], path: str, default: Any = MISSING) -> Any:
    current: Any = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _all_false(mapping: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(mapping.get(field) is False for field in fields)


def _scenario_ids(items: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(_mapping(item).get("scenario_id") for item in items)


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_report_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage068_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage068 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, callable_name, None)
    if not callable(provider):
        raise RuntimeError(f"Stage068 review dependency is invalid: {filename}")
    return provider


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, (list, tuple)) else ()
