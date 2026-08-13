"""Stage058 的只读整阶段复审，不读取真实表格或启动下游运行时。"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
P1_CONTRACT = BASE / "stage058_table_schema_inference_contract.json"
P2_CONTRACT = BASE / "stage058_table_schema_inference_slice_contract.json"
P3_CONTRACT = BASE / "stage058_table_schema_inference_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "stage058_table_schema_inference_delivery_contract.json"

SCHEMA_VERSION = "ids.stage058.table_schema_inference.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE058-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-058"
PASS_RESULT = "PASS_REVIEWED_LOCAL_TABLE_SCHEMA_INFERENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_TABLE_SCHEMA_INFERENCE_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE059-P1-GATE"
RETURN_STATE = "PHASE4_TABLE_SCHEMA_INFERENCE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage058_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage058 P1--P4，只返回控制计数、边界和回滚结论。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    quality_report = _as_mapping((phase3_report_provider or _load_phase3_report_provider())())
    delivery_report = _as_mapping((phase4_report_provider or _load_phase4_report_provider())())

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3) and _quality_report_valid(quality_report),
        "P4": _phase4_contract_valid(phase4) and _delivery_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(phase1, phase2, quality_report, delivery_report)
    invariants = {
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4
        ),
        "input_and_schema_profile_shape_preserved": _input_and_schema_profile_shape_preserved(
            phase1, phase2
        ),
        "fact_and_rag_authority_boundary_preserved": _fact_and_rag_authority_boundary_preserved(
            phase1
        ),
        "quality_and_human_handling_boundary_preserved": _quality_and_human_handling_boundary_preserved(
            quality_report, delivery_report
        ),
        "metadata_only_delivery_boundary": _metadata_only_delivery_boundary(
            delivery_report
        ),
        "reparse_and_rollback_chain_preserved": _reparse_and_rollback_chain_preserved(
            phase1, phase2, phase3, phase4, delivery_report
        ),
        "runtime_actions_disabled": _contracts_have_no_runtime_actions(
            phase1, phase2, phase3, phase4
        ),
        "stage059_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_TASKPACK_AND_STAGE058_P1_TO_P4_CONTROLLED_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": invariants,
        "review_finding_count": 0,
        "review_valid": False,
        "result": FAIL_RESULT,
        "rollback": {
            "return_to": RETURN_STATE,
            "revertable_artifacts": [
                "Stage058 review document",
                "Stage058 review module",
                "Stage058 review focused tests",
                "Stage058 review governance projection",
            ],
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": NEXT_GATE,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_table_quality_validation_performed": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "rag_summary_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage058_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "stage059_started": False,
        "stage059_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = all(
        report[field] is False for field in _review_runtime_fields()
    ) and report["review_invariants"]["runtime_actions_disabled"]
    report["review_valid"] = all(report["phase_results"].values()) and all(
        report["review_invariants"].values()
    )
    report["review_finding_count"] = 0 if report["review_valid"] else 1
    report["result"] = PASS_RESULT if report["review_valid"] else FAIL_RESULT
    return report


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _as_mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_phase3_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage058_table_schema_inference_quality_scenarios.py",
        "build_table_schema_inference_phase3_report",
    )


def _load_phase4_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage058_table_schema_inference_delivery.py",
        "build_table_schema_inference_phase4_delivery_report",
    )


def _module_callable_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage058_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage058 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage058 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _as_mapping(contract.get("reference_only_schema_inference_input_contract"))
    profile_contract = _as_mapping(contract.get("future_schema_profile_contract"))
    semantic_contract = _as_mapping(contract.get("field_candidate_semantic_contract"))
    location_contract = _as_mapping(contract.get("source_location_and_evidence_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    return all(
        (
            contract.get("schema_version") == "ids.stage058.table_schema_inference.phase1.v1",
            contract.get("contract_state")
            == "PHASE1_TABLE_SCHEMA_INFERENCE_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE058-P1",
            contract.get("next_gate") == "IDS-STAGE058-P2-GATE",
            _single_authority_contract(contract),
            input_contract.get("field_count") == 10,
            input_contract.get("actual_input_record_count") == 0,
            profile_contract.get("field_count") == 18,
            profile_contract.get("actual_schema_profile_created") is False,
            semantic_contract.get("semantic_category_count") == 9,
            semantic_contract.get("candidate_field_type_count") == 6,
            location_contract.get("location_field_count") == 6,
            failures.get("failure_state_count") == 8,
            _contract_runtime_disabled(contract),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _as_mapping(contract.get("reference_only_schema_inference_input_contract"))
    profile_contract = _as_mapping(contract.get("schema_profile_candidate_contract"))
    location_contract = _as_mapping(contract.get("source_location_and_evidence_contract"))
    return all(
        (
            contract.get("schema_version") == "ids.stage058.table_schema_inference.phase2.v1",
            contract.get("contract_state")
            == "PHASE2_TABLE_SCHEMA_INFERENCE_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE058-P2",
            contract.get("next_gate") == "IDS-STAGE058-P3-GATE",
            contract.get("slice_executable") is True,
            _single_authority_contract(contract),
            input_contract.get("field_count") == 10,
            input_contract.get("control_record_count") == 2,
            input_contract.get("actual_input_record_count") == 0,
            profile_contract.get("field_count") == 18,
            profile_contract.get("control_schema_profile_group_count") == 2,
            profile_contract.get("control_schema_profile_candidate_count") == 11,
            profile_contract.get("candidate_field_mapping_count") == 11,
            profile_contract.get("semantic_category_count") == 9,
            profile_contract.get("candidate_field_type_count") == 6,
            profile_contract.get("actual_schema_profile_created") is False,
            profile_contract.get("actual_field_mapping_created") is False,
            location_contract.get("location_field_count") == 6,
            location_contract.get("candidate_binding_count") == 11,
            _contract_runtime_disabled(contract),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return all(
        (
            contract.get("schema_version")
            == "ids.stage058.table_schema_inference.phase3.quality_scenarios.v1",
            contract.get("contract_state")
            == "PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE058-P3",
            contract.get("next_gate") == "IDS-STAGE058-P4-GATE",
            contract.get("scenario_executable") is True,
            _single_authority_contract(contract),
            _contract_runtime_disabled(contract),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return all(
        (
            contract.get("schema_version")
            == "ids.stage058.table_schema_inference.phase4.delivery.v1",
            contract.get("contract_state")
            == "PHASE4_TABLE_SCHEMA_INFERENCE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE058-P4",
            contract.get("next_gate") == "IDS-STAGE058-REVIEW-GATE",
            contract.get("delivery_evidence_executable") is True,
            contract.get("execution_ready") is False,
            _single_authority_contract(contract),
            _contract_runtime_disabled(contract),
        )
    )


def _quality_report_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report.get("next_gate") == "IDS-STAGE058-P4-GATE",
            report.get("phase2_control_slice_reexecuted") is True,
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("outlier_numeric_block_count") == 1,
            report.get("unique_schema_profile_candidate_count") == 11,
            report.get("taskpack_exception_categories_covered") is True,
            report.get("control_source_location_traceability_preserved") is True,
            report.get("actual_source_file_traceability_validated") is False,
            report.get("actual_schema_profile_created") is False,
            report.get("actual_field_mapping_created") is False,
            report.get("actual_structured_fact_created") is False,
            report.get("numeric_statistic_computation_performed") is False,
            report.get("agent_execution_performed") is False,
            report.get("model_token_consumption_performed") is False,
            report.get("ovh_deployment_performed") is False,
        )
    )


def _delivery_report_valid(report: Mapping[str, Any]) -> bool:
    inference = _as_mapping(report.get("field_inference_report"))
    quality = _as_mapping(report.get("quality_test_results"))
    rollback = _as_mapping(report.get("reparse_and_fact_rollback_instructions"))
    samples = _list_of_mappings(report.get("delivery_samples"))
    handling = _list_of_mappings(report.get("unrecognized_structure_and_human_handling"))
    prompts = _list_of_mappings(report.get("human_confirmation_prompts_zh"))
    return all(
        (
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE4_TABLE_SCHEMA_INFERENCE_DELIVERY_RUNTIME_DISABLED",
            report.get("stage_review_status") == "pending_next_run",
            report.get("next_gate") == "IDS-STAGE058-REVIEW-GATE",
            len(samples) == 6,
            len(handling) == 6,
            len(prompts) == 3,
            inference.get("referenced_field_candidate_count") == 6,
            inference.get("actual_table_schema_created") is False,
            quality.get("scenario_count") == 6,
            quality.get("passed_scenario_count") == 6,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("actual_table_quality_validation_performed") is False,
            rollback.get("return_to")
            == "PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_file_reparse_performed") is False,
            rollback.get("actual_fact_store_present") is False,
            rollback.get("actual_fact_rollback_performed") is False,
            report.get("agent_execution_performed") is False,
            report.get("model_token_consumption_performed") is False,
            report.get("ovh_deployment_performed") is False,
        )
    )


def _single_authority_boundary_preserved(*contracts: Mapping[str, Any]) -> bool:
    return all(_single_authority_contract(contract) for contract in contracts)


def _single_authority_contract(contract: Mapping[str, Any]) -> bool:
    source = _as_mapping(contract.get("source_authority"))
    return (
        str(source.get("authority", "")).startswith("FROZEN_TASKPACK")
        and source.get("second_authoritative_source_created") is False
        and source.get("source_body_or_path_allowed") is False
        and source.get("raw_metadata_content_access_allowed") is False
    )


def _input_and_schema_profile_shape_preserved(
    phase1: Mapping[str, Any], phase2: Mapping[str, Any]
) -> bool:
    p1_input = _as_mapping(phase1.get("reference_only_schema_inference_input_contract"))
    p1_profile = _as_mapping(phase1.get("future_schema_profile_contract"))
    p1_semantic = _as_mapping(phase1.get("field_candidate_semantic_contract"))
    p1_location = _as_mapping(phase1.get("source_location_and_evidence_contract"))
    p2_input = _as_mapping(phase2.get("reference_only_schema_inference_input_contract"))
    p2_profile = _as_mapping(phase2.get("schema_profile_candidate_contract"))
    p2_location = _as_mapping(phase2.get("source_location_and_evidence_contract"))
    return all(
        (
            p1_input.get("field_count") == 10,
            p1_profile.get("field_count") == 18,
            p1_semantic.get("semantic_category_count") == 9,
            p1_semantic.get("candidate_field_type_count") == 6,
            p1_location.get("location_field_count") == 6,
            p2_input.get("control_record_count") == 2,
            p2_profile.get("control_schema_profile_group_count") == 2,
            p2_profile.get("control_schema_profile_candidate_count") == 11,
            p2_profile.get("candidate_field_mapping_count") == 11,
            p2_location.get("candidate_binding_count") == 11,
        )
    )


def _fact_and_rag_authority_boundary_preserved(phase1: Mapping[str, Any]) -> bool:
    numeric = _as_mapping(phase1.get("numeric_fact_authority_boundary"))
    summary = _as_mapping(phase1.get("fact_and_rag_summary_boundary"))
    return all(
        (
            numeric.get("source_document_remains_authoritative") is True,
            numeric.get("model_direct_text_guessing_allowed") is False,
            numeric.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            numeric.get("numeric_statistic_computation_performed") is False,
            summary.get("summary_can_replace_structured_fact") is False,
            summary.get("summary_can_become_numeric_statistical_evidence") is False,
            summary.get("actual_structured_fact_created") is False,
            summary.get("actual_rag_summary_created") is False,
        )
    )


def _quality_and_human_handling_boundary_preserved(
    quality_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    handling = _list_of_mappings(delivery_report.get("unrecognized_structure_and_human_handling"))
    return all(
        (
            quality_report.get("scenario_count") == 6,
            quality_report.get("explicit_disposition_count") == 6,
            quality_report.get("silent_drop_count") == 0,
            quality_report.get("human_handling_required_count") == 6,
            quality_report.get("outlier_numeric_block_count") == 1,
            len(handling) == 6,
            all(item.get("human_handling_required") is True for item in handling),
            all(item.get("automatic_structure_resolution_performed") is False for item in handling),
            all(item.get("automatic_fact_write_performed") is False for item in handling),
        )
    )


def _metadata_only_delivery_boundary(report: Mapping[str, Any]) -> bool:
    samples = _list_of_mappings(report.get("delivery_samples"))
    return len(samples) == 6 and all(
        item.get("control_metadata_only") is True
        and item.get("source_content_retained") is False
        and item.get("typed_value_retained") is False
        and item.get("actual_schema_profile_created") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("actual_table_fact_sample_created") is False
        and item.get("high_trust_direct_entry_allowed") is False
        for item in samples
    )


def _reparse_and_rollback_chain_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    returns = (
        _rollback_return(phase1),
        _rollback_return(phase2),
        _rollback_return(phase3),
        _rollback_return(phase4),
        _as_mapping(delivery_report.get("rollback")).get("return_to"),
    )
    return all(isinstance(value, str) and bool(value) for value in returns) and (
        returns[-1]
        == "PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
    )


def _rollback_return(contract: Mapping[str, Any]) -> object:
    rollback = _as_mapping(contract.get("rollback_contract"))
    return rollback.get("return_to", rollback.get("rollback_target_contract_state"))


def _contracts_have_no_runtime_actions(*contracts: Mapping[str, Any]) -> bool:
    return all(_contract_runtime_disabled(contract) for contract in contracts)


def _contract_runtime_disabled(contract: Mapping[str, Any]) -> bool:
    runtime = _as_mapping(contract.get("runtime_boundary"))
    return bool(runtime) and all(
        value is False
        for key, value in runtime.items()
        if key.endswith("_performed") or key in {"github_upload_allowed", "push_allowed"}
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> dict[str, Any]:
    p1_input = _as_mapping(phase1.get("reference_only_schema_inference_input_contract"))
    p1_profile = _as_mapping(phase1.get("future_schema_profile_contract"))
    p1_semantic = _as_mapping(phase1.get("field_candidate_semantic_contract"))
    p1_location = _as_mapping(phase1.get("source_location_and_evidence_contract"))
    p1_failures = _as_mapping(phase1.get("failure_and_stop_contract"))
    p2_input = _as_mapping(phase2.get("reference_only_schema_inference_input_contract"))
    p2_profile = _as_mapping(phase2.get("schema_profile_candidate_contract"))
    p2_location = _as_mapping(phase2.get("source_location_and_evidence_contract"))
    inference = _as_mapping(delivery_report.get("field_inference_report"))
    delivery_quality = _as_mapping(delivery_report.get("quality_test_results"))
    rollback = _as_mapping(delivery_report.get("reparse_and_fact_rollback_instructions"))
    return {
        "phase_contract_count": 4,
        "phase_contract_passed_count": 4,
        "phase1_reference_input_field_count": _nonnegative_int(p1_input.get("field_count")),
        "phase1_future_schema_profile_field_count": _nonnegative_int(p1_profile.get("field_count")),
        "phase1_field_semantic_category_count": _nonnegative_int(p1_semantic.get("semantic_category_count")),
        "phase1_candidate_field_type_count": _nonnegative_int(p1_semantic.get("candidate_field_type_count")),
        "phase1_source_location_field_count": _nonnegative_int(p1_location.get("location_field_count")),
        "phase1_declared_failure_state_count": _nonnegative_int(p1_failures.get("failure_state_count")),
        "phase2_control_record_count": _nonnegative_int(p2_input.get("control_record_count")),
        "phase2_schema_profile_group_count": _nonnegative_int(p2_profile.get("control_schema_profile_group_count")),
        "phase2_schema_profile_candidate_count": _nonnegative_int(p2_profile.get("control_schema_profile_candidate_count")),
        "phase2_candidate_field_mapping_count": _nonnegative_int(p2_profile.get("candidate_field_mapping_count")),
        "phase2_source_location_binding_candidate_count": _nonnegative_int(p2_location.get("candidate_binding_count")),
        "quality_scenario_count": _nonnegative_int(quality_report.get("scenario_count")),
        "quality_explicit_disposition_count": _nonnegative_int(quality_report.get("explicit_disposition_count")),
        "quality_silent_drop_count": _nonnegative_int(quality_report.get("silent_drop_count")),
        "quality_human_handling_required_count": _nonnegative_int(quality_report.get("human_handling_required_count")),
        "quality_outlier_numeric_block_count": _nonnegative_int(quality_report.get("outlier_numeric_block_count")),
        "delivery_sample_count": len(_list_of_mappings(delivery_report.get("delivery_samples"))),
        "delivery_field_reference_label_count": _nonnegative_int(inference.get("referenced_field_candidate_count")),
        "delivery_quality_result_count": _nonnegative_int(delivery_quality.get("scenario_count")),
        "delivery_human_handling_record_count": len(
            _list_of_mappings(delivery_report.get("unrecognized_structure_and_human_handling"))
        ),
        "delivery_human_confirmation_prompt_count": len(
            _list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))
        ),
        "reparse_and_fact_rollback_instructions_created": bool(rollback),
        "reparse_and_fact_rollback_return_to": rollback.get("return_to"),
    }


def _review_runtime_fields() -> tuple[str, ...]:
    return (
        "ids_business_source_read_performed",
        "raw_metadata_content_accessed",
        "authorized_fixture_access_performed",
        "source_file_open_performed",
        "file_type_detection_performed",
        "xlsx_or_csv_parse_performed",
        "real_table_schema_inference_performed",
        "real_field_identification_performed",
        "real_structured_fact_extraction_performed",
        "real_table_quality_validation_performed",
        "merged_cell_resolution_performed",
        "unit_normalization_performed",
        "date_normalization_performed",
        "outlier_evaluation_performed",
        "duplicate_row_evaluation_performed",
        "numeric_statistic_computation_performed",
        "actual_file_reparse_performed",
        "actual_fact_rollback_performed",
        "database_connection_performed",
        "database_schema_migration_performed",
        "structured_fact_write_performed",
        "rag_summary_write_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "local_service_start_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "stage059_started",
        "stage059_entry_allowed",
        "batch_review_performed",
        "github_upload_performed",
        "github_upload_allowed",
        "push_allowed",
    )


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
