"""Stage061 的只读整阶段复审，不读取真实表格或启动 Stage062。"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
P1_CONTRACT = BASE / "stage061_structured_data_quality_contract.json"
P2_CONTRACT = BASE / "stage061_structured_data_quality_slice_contract.json"
P3_CONTRACT = BASE / "stage061_structured_data_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "stage061_structured_data_quality_delivery_contract.json"

SCHEMA_VERSION = "ids.stage061.structured_data_quality.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE061-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-061"
PASS_RESULT = "PASS_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE061-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE062-P1-GATE"
RETURN_STATE = "PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage061_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage061 P1--P4，只返回 control 计数、边界与回滚结论。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    quality_report = _as_mapping((phase3_report_provider or _load_phase3_report_provider())())
    delivery_report = _as_mapping((phase4_report_provider or _load_phase4_report_provider())())

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3)
        and _quality_report_valid(quality_report),
        "P4": _phase4_contract_valid(phase4)
        and _delivery_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2, quality_report, delivery_report, phase_results
    )
    invariants = {
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4
        ),
        "structured_fact_and_numeric_authority_boundary_preserved": (
            _structured_fact_and_numeric_authority_boundary_preserved(
                phase1, phase2, phase3, phase4
            )
        ),
        "chinese_feedback_boundary_preserved": _chinese_feedback_boundary_preserved(
            phase1, phase2, phase3, phase4, delivery_report
        ),
        "source_location_and_evidence_boundary_preserved": (
            _source_location_and_evidence_boundary_preserved(phase1, phase2, phase3)
        ),
        "quality_and_human_handling_boundary_preserved": (
            _quality_and_human_handling_boundary_preserved(
                quality_report, delivery_report
            )
        ),
        "metadata_only_delivery_boundary_preserved": _metadata_only_delivery_boundary(
            delivery_report
        ),
        "reparse_and_rollback_chain_preserved": _reparse_and_rollback_chain_preserved(
            phase1, phase2, phase3, phase4, delivery_report
        ),
        "runtime_actions_disabled": _contracts_have_no_runtime_actions(
            phase1, phase2, phase3, phase4
        ),
        "stage062_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": (
            "FROZEN_TASKPACK_AND_STAGE061_P1_TO_P4_AND_BATCH051_060_REVIEW_ARTIFACTS_ONLY"
        ),
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
                "Stage061 review document",
                "Stage061 review module",
                "Stage061 review focused tests",
                "Stage061 review governance projection",
            ],
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": REVIEW_GATE,
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
        "real_table_content_evaluated": False,
        "typed_value_extraction_performed": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_rollback_performed": False,
        "actual_quality_result_rollback_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage061_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage062_started": False,
        "stage062_entry_allowed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_performed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        _report_runtime_disabled(report)
        and report["review_invariants"]["runtime_actions_disabled"]
    )
    report["review_valid"] = all(report["phase_results"].values()) and all(
        report["review_invariants"].values()
    )
    report["review_finding_count"] = 0 if report["review_valid"] else 1
    report["result"] = PASS_RESULT if report["review_valid"] else FAIL_RESULT
    report["next_gate"] = NEXT_GATE if report["review_valid"] else REVIEW_GATE
    return report


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _as_mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_phase3_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage061_structured_data_quality_scenarios.py",
        "build_structured_data_quality_phase3_report",
    )


def _load_phase4_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage061_structured_data_quality_delivery.py",
        "build_structured_data_quality_phase4_delivery_report",
    )


def _module_callable_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage061_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage061 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage061 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_quality_input_contract"))
    outputs = _as_mapping(contract.get("future_quality_result_output_contract"))
    dimensions = _as_mapping(contract.get("quality_dimension_contract"))
    semantics = _as_mapping(contract.get("field_semantic_contract"))
    numeric = _as_mapping(contract.get("numeric_fact_authority_boundary"))
    summary = _as_mapping(contract.get("fact_and_rag_summary_boundary"))
    location = _as_mapping(contract.get("source_location_and_evidence_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage061.structured_data_quality.phase1.v1",
            contract.get("contract_state")
            == "PHASE1_STRUCTURED_DATA_QUALITY_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE061-P1",
            contract.get("next_gate") == "IDS-STAGE061-P2-GATE",
            _single_authority_contract(_as_mapping(contract.get("source_authority"))),
            inputs.get("field_count") == 16,
            inputs.get("actual_input_record_count") == 0,
            outputs.get("field_count") == 18,
            outputs.get("actual_quality_result_created") is False,
            outputs.get("actual_quality_result_persisted") is False,
            dimensions.get("quality_dimension_count") == 5,
            dimensions.get("automatic_quality_pass_allowed") is False,
            semantics.get("semantic_field_count") == 8,
            semantics.get("field_identification_performed") is False,
            numeric.get("source_document_remains_authoritative") is True,
            numeric.get("model_direct_text_guessing_allowed") is False,
            numeric.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            numeric.get("actual_structured_fact_count") == 0,
            numeric.get("actual_numeric_fact_count") == 0,
            summary.get("summary_can_replace_structured_fact") is False,
            summary.get("summary_can_become_numeric_statistical_evidence") is False,
            location.get("location_field_count") == 6,
            location.get("actual_source_location_binding_count") == 0,
            location.get("actual_evidence_record_created") is False,
            failures.get("failure_state_count") == 11,
            failures.get("unrecognized_structure_requires_human_handling") is True,
            failures.get("unverified_numeric_value_blocks_statistical_conclusion")
            is True,
            _contract_runtime_disabled(contract),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_quality_input_control_contract"))
    candidates = _as_mapping(contract.get("quality_result_candidate_contract"))
    dimensions = _as_mapping(contract.get("quality_dimension_control_contract"))
    location = _as_mapping(contract.get("source_location_and_evidence_control_contract"))
    numeric = _as_mapping(contract.get("numeric_fact_authority_boundary"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage061.structured_data_quality.phase2.v1",
            contract.get("contract_state")
            == "PHASE2_STRUCTURED_DATA_QUALITY_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE061-P2",
            contract.get("next_gate") == "IDS-STAGE061-P3-GATE",
            contract.get("slice_executable") is True,
            _single_authority_contract(_as_mapping(contract.get("source_authority"))),
            inputs.get("field_count") == 16,
            inputs.get("control_record_count") == 2,
            inputs.get("actual_input_record_count") == 0,
            candidates.get("field_count") == 18,
            candidates.get("control_quality_result_candidate_count") == 10,
            candidates.get("actual_quality_result_created") is False,
            candidates.get("actual_quality_result_persisted") is False,
            dimensions.get("quality_dimension_count") == 5,
            dimensions.get("control_candidates_per_dimension") == 2,
            dimensions.get("automatic_quality_pass_allowed") is False,
            location.get("location_field_count") == 6,
            location.get("candidate_binding_count") == 10,
            location.get("actual_source_location_binding_created") is False,
            location.get("actual_evidence_record_created") is False,
            numeric.get("source_document_remains_authoritative") is True,
            numeric.get("model_direct_text_guessing_allowed") is False,
            numeric.get("unverified_numeric_value_as_definitive_fact_allowed")
            is False,
            numeric.get("actual_structured_fact_count") == 0,
            numeric.get("actual_numeric_fact_count") == 0,
            _contract_runtime_disabled(contract),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("scenario_input_boundary"))
    quality = _as_mapping(contract.get("quality_scenario_validation"))
    traceability = _as_mapping(contract.get("traceability_boundary"))
    numeric = _as_mapping(contract.get("numeric_and_model_authority_boundary"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage061.structured_data_quality.phase3.quality_scenarios.v1",
            contract.get("contract_state")
            == "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE061-P3",
            contract.get("next_gate") == "IDS-STAGE061-P4-GATE",
            contract.get("scenario_executable") is True,
            _single_authority_contract(_as_mapping(contract.get("source_authority"))),
            inputs.get("scenario_count") == 6,
            inputs.get("phase2_control_record_count") == 2,
            inputs.get("phase2_quality_result_candidate_count") == 10,
            inputs.get("phase2_quality_dimension_count") == 5,
            inputs.get("actual_input_record_count") == 0,
            inputs.get("actual_table_count") == 0,
            quality.get("all_taskpack_exception_categories_covered") is True,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("human_handling_required_count") == 6,
            quality.get("outlier_numeric_block_count") == 1,
            quality.get("actual_table_quality_validation_performed") is False,
            traceability.get("control_source_location_field_count") == 6,
            traceability.get("control_source_location_reference_check_count") == 6,
            traceability.get("control_source_location_traceability_preserved") is True,
            traceability.get("actual_source_file_traceability_validated") is False,
            traceability.get("actual_evidence_record_created") is False,
            numeric.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            numeric.get("numeric_statistical_conclusion_allowed") is False,
            numeric.get("model_direct_text_guessing_allowed") is False,
            numeric.get("model_definitive_numeric_conclusion_allowed") is False,
            numeric.get("summary_can_replace_structured_fact") is False,
            numeric.get("summary_can_become_numeric_statistical_evidence") is False,
            _contract_runtime_disabled(contract),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("delivery_input_boundary"))
    delivery = _as_mapping(contract.get("delivery_evidence"))
    feedback = _as_mapping(contract.get("chinese_feedback_contract"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage061.structured_data_quality.phase4.delivery.v1",
            contract.get("contract_state")
            == "PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE061-P4",
            contract.get("next_gate") == REVIEW_GATE,
            contract.get("delivery_evidence_executable") is True,
            contract.get("execution_ready") is False,
            _single_authority_contract(_as_mapping(contract.get("source_authority"))),
            inputs.get("reference_only_quality_input_field_count") == 16,
            inputs.get("future_quality_result_output_field_count") == 18,
            inputs.get("control_quality_input_record_count") == 2,
            inputs.get("control_quality_result_candidate_count") == 10,
            inputs.get("quality_dimension_count") == 5,
            inputs.get("control_quality_scenario_count") == 6,
            inputs.get("metadata_only_quality_delivery_sample_count") == 6,
            inputs.get("field_reference_label_count") == 6,
            inputs.get("quality_test_result_delivery_count") == 6,
            inputs.get("silent_drop_count") == 0,
            inputs.get("human_handling_recommendation_count") == 6,
            inputs.get("human_confirmation_prompt_count") == 3,
            inputs.get("actual_table_count") == 0,
            delivery.get("metadata_only_quality_delivery_samples_derived") is True,
            delivery.get("field_inference_report_derived") is True,
            delivery.get("control_quality_test_results_derived") is True,
            delivery.get("unrecognized_structure_and_human_handling_recorded") is True,
            delivery.get("table_reparse_and_fact_rollback_instructions_created")
            is True,
            delivery.get("actual_structured_fact_created") is False,
            delivery.get("actual_quality_result_created") is False,
            delivery.get("summary_can_replace_structured_fact") is False,
            delivery.get("summary_can_become_numeric_statistical_evidence") is False,
            feedback.get("message_count") == 3,
            feedback.get("all_messages_chinese") is True,
            feedback.get("automatic_confirmation_performed") is False,
            _contract_runtime_disabled(contract),
        )
    )


def _quality_report_valid(report: Mapping[str, Any]) -> bool:
    results = _list_of_mappings(report.get("scenario_results"))
    outlier_count = sum(
        item.get("unverified_numeric_blocks_statistical_conclusion") is True
        for item in results
    )
    return all(
        (
            report.get("schema_version")
            == "ids.stage061.structured_data_quality.phase3.quality_scenarios.v1",
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report.get("next_gate") == "IDS-STAGE061-P4-GATE",
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("unique_quality_result_candidate_count") == 6,
            report.get("source_location_reference_check_count") == 6,
            report.get("control_source_location_traceability_preserved") is True,
            report.get("all_quality_states_unassessed") is True,
            report.get("all_human_review_required") is True,
            report.get("all_statistical_conclusions_blocked") is True,
            len(results) == 6,
            outlier_count == 1,
            all(
                item.get("expectation_met") is True
                and item.get("explicit_disposition") is True
                and item.get("silent_drop") is False
                and item.get("human_handling_required") is True
                and item.get("control_scenario_metadata_only") is True
                and item.get("actual_quality_result_created") is False
                and item.get("actual_structured_fact_created") is False
                for item in results
            ),
            _report_runtime_disabled(report),
        )
    )


def _delivery_report_valid(report: Mapping[str, Any]) -> bool:
    samples = _list_of_mappings(report.get("delivery_samples"))
    inference = _as_mapping(report.get("field_inference_report"))
    quality = _as_mapping(report.get("quality_test_results"))
    handling = _list_of_mappings(report.get("unrecognized_structure_and_human_handling"))
    prompts = _list_of_mappings(report.get("human_confirmation_prompts_zh"))
    rollback = _as_mapping(report.get("reparse_and_fact_rollback_instructions"))
    return all(
        (
            report.get("schema_version")
            == "ids.stage061.structured_data_quality.phase4.delivery.v1",
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_RUNTIME_DISABLED",
            report.get("next_gate") == REVIEW_GATE,
            len(samples) == 6,
            all(
                item.get("sample_kind")
                == "DELIVERY_METADATA_ONLY_STRUCTURED_DATA_QUALITY_SAMPLE_NOT_REAL_QUALITY_RESULT"
                and item.get("control_metadata_only") is True
                and item.get("source_content_retained") is False
                and item.get("typed_value_retained") is False
                and item.get("actual_field_mapping_created") is False
                and item.get("actual_quality_result_created") is False
                and item.get("actual_structured_fact_created") is False
                for item in samples
            ),
            inference.get("referenced_field_label_count") == 6,
            inference.get("actual_field_mapping_created") is False,
            inference.get("real_table_schema_inference_performed") is False,
            quality.get("scenario_count") == 6,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("human_handling_required_count") == 6,
            quality.get("actual_table_quality_validation_performed") is False,
            len(handling) == 6,
            all(item.get("human_handling_required") is True for item in handling),
            len(prompts) == 3,
            all(item.get("automatic_confirmation_performed") is False for item in prompts),
            rollback.get("return_to")
            == "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("actual_file_reparse_performed") is False,
            rollback.get("actual_fact_rollback_performed") is False,
            rollback.get("actual_quality_result_rollback_performed") is False,
            _report_runtime_disabled(report),
        )
    )


def _single_authority_contract(authority: Mapping[str, Any]) -> bool:
    return bool(authority) and all(
        (
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            authority.get("raw_metadata_content_access_allowed", False) is False,
            authority.get("live_source_read_performed", False) is False,
            authority.get("authorized_fixture_access_performed", False) is False,
        )
    )


def _single_authority_boundary_preserved(*contracts: Mapping[str, Any]) -> bool:
    return all(
        _single_authority_contract(_as_mapping(contract.get("source_authority")))
        for contract in contracts
    )


def _structured_fact_and_numeric_authority_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    p1 = _as_mapping(phase1.get("numeric_fact_authority_boundary"))
    p1_summary = _as_mapping(phase1.get("fact_and_rag_summary_boundary"))
    p2 = _as_mapping(phase2.get("numeric_fact_authority_boundary"))
    p3 = _as_mapping(phase3.get("numeric_and_model_authority_boundary"))
    p4 = _as_mapping(phase4.get("delivery_evidence"))
    return all(
        (
            p1.get("source_document_remains_authoritative") is True,
            p1.get("model_direct_text_guessing_allowed") is False,
            p1.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            p1_summary.get("summary_can_replace_structured_fact") is False,
            p1_summary.get("summary_can_become_numeric_statistical_evidence")
            is False,
            p2.get("source_document_remains_authoritative") is True,
            p2.get("model_direct_text_guessing_allowed") is False,
            p2.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            p2.get("summary_can_replace_structured_fact") is False,
            p2.get("summary_can_become_numeric_statistical_evidence") is False,
            p3.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            p3.get("numeric_statistical_conclusion_allowed") is False,
            p3.get("model_direct_text_guessing_allowed") is False,
            p3.get("model_definitive_numeric_conclusion_allowed") is False,
            p3.get("summary_can_replace_structured_fact") is False,
            p3.get("summary_can_become_numeric_statistical_evidence") is False,
            p4.get("unverified_numeric_value_as_definitive_fact_allowed") is False,
            p4.get("numeric_statistical_conclusion_allowed") is False,
            p4.get("model_direct_text_guessing_allowed") is False,
            p4.get("model_definitive_numeric_conclusion_allowed") is False,
            p4.get("summary_can_replace_structured_fact") is False,
            p4.get("summary_can_become_numeric_statistical_evidence") is False,
        )
    )


def _source_location_and_evidence_boundary_preserved(
    phase1: Mapping[str, Any], phase2: Mapping[str, Any], phase3: Mapping[str, Any]
) -> bool:
    p1_inputs = _as_mapping(phase1.get("reference_only_quality_input_contract"))
    p1_location = _as_mapping(phase1.get("source_location_and_evidence_contract"))
    p2_refs = _as_mapping(phase2.get("source_location_and_evidence_control_contract"))
    p3_traceability = _as_mapping(phase3.get("traceability_boundary"))
    return all(
        (
            p1_inputs.get("actual_input_record_count") == 0,
            p1_location.get("location_field_count") == 6,
            p1_location.get("actual_source_location_binding_count") == 0,
            p1_location.get("actual_evidence_record_created") is False,
            p2_refs.get("location_field_count") == 6,
            p2_refs.get("candidate_binding_count") == 10,
            p2_refs.get("actual_source_location_binding_created") is False,
            p2_refs.get("actual_evidence_record_created") is False,
            p3_traceability.get("control_source_location_traceability_preserved")
            is True,
            p3_traceability.get("actual_source_file_traceability_validated") is False,
            p3_traceability.get("actual_evidence_record_created") is False,
        )
    )


def _chinese_feedback_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    contracts = (phase1, phase2, phase3, phase4)
    prompts = _list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))
    return all(
        _as_mapping(contract.get("chinese_feedback_contract")).get(
            "all_messages_chinese"
        )
        is True
        and _as_mapping(contract.get("chinese_feedback_contract")).get(
            "automation_claim_allowed"
        )
        is False
        and _as_mapping(contract.get("chinese_feedback_contract")).get(
            "production_availability_claim_allowed"
        )
        is False
        for contract in contracts
    ) and len(prompts) == 3 and all(
        "请" in str(item.get("text"))
        and item.get("automatic_confirmation_performed") is False
        for item in prompts
    )


def _quality_and_human_handling_boundary_preserved(
    quality_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    quality = _as_mapping(delivery_report.get("quality_test_results"))
    handling = _list_of_mappings(delivery_report.get("unrecognized_structure_and_human_handling"))
    prompts = _list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))
    return all(
        (
            quality_report.get("scenario_count") == 6,
            quality_report.get("explicit_disposition_count") == 6,
            quality_report.get("silent_drop_count") == 0,
            quality_report.get("human_handling_required_count") == 6,
            quality_report.get("outlier_numeric_block_count") == 1,
            quality.get("scenario_count") == 6,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("human_handling_required_count") == 6,
            len(handling) == 6,
            all(item.get("human_handling_required") is True for item in handling),
            len(prompts) == 3,
            all("请" in str(item.get("text")) for item in prompts),
            all(item.get("automatic_confirmation_performed") is False for item in prompts),
        )
    )


def _metadata_only_delivery_boundary(report: Mapping[str, Any]) -> bool:
    samples = _list_of_mappings(report.get("delivery_samples"))
    inference = _as_mapping(report.get("field_inference_report"))
    quality = _as_mapping(report.get("quality_test_results"))
    return all(
        (
            len(samples) == 6,
            all(
                item.get("control_metadata_only") is True
                and item.get("source_content_retained") is False
                and item.get("typed_value_retained") is False
                and item.get("actual_field_mapping_created") is False
                and item.get("actual_quality_result_created") is False
                and item.get("actual_structured_fact_created") is False
                for item in samples
            ),
            inference.get("control_reference_only") is True,
            inference.get("actual_field_mapping_created") is False,
            quality.get("actual_table_quality_validation_performed") is False,
            quality.get("actual_evidence_record_created") is False,
        )
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
        _as_mapping(delivery_report.get("reparse_and_fact_rollback_instructions")).get(
            "return_to"
        ),
    )
    return all(isinstance(value, str) and bool(value) for value in returns) and (
        returns[-1]
        == "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
    )


def _rollback_return(contract: Mapping[str, Any]) -> object:
    return _as_mapping(contract.get("rollback_contract")).get("return_to")


def _contracts_have_no_runtime_actions(*contracts: Mapping[str, Any]) -> bool:
    return all(_contract_runtime_disabled(contract) for contract in contracts)


def _contract_runtime_disabled(contract: Mapping[str, Any]) -> bool:
    runtime = _as_mapping(contract.get("runtime_boundary"))
    return bool(runtime) and all(
        value is False
        for key, value in runtime.items()
        if key.endswith("_performed") or key in {"github_upload_allowed", "push_allowed"}
    )


def _report_runtime_disabled(report: Mapping[str, Any]) -> bool:
    runtime_values = [
        value
        for key, value in report.items()
        if (
            key.endswith("_performed")
            and key not in {"whole_stage_review_performed"}
        )
        or key in {"github_upload_allowed", "push_allowed"}
    ]
    return bool(runtime_values) and all(value is False for value in runtime_values)


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
    phase_results: Mapping[str, bool],
) -> dict[str, Any]:
    p1_inputs = _as_mapping(phase1.get("reference_only_quality_input_contract"))
    p1_outputs = _as_mapping(phase1.get("future_quality_result_output_contract"))
    p1_dimensions = _as_mapping(phase1.get("quality_dimension_contract"))
    p1_semantics = _as_mapping(phase1.get("field_semantic_contract"))
    p1_location = _as_mapping(phase1.get("source_location_and_evidence_contract"))
    p1_failures = _as_mapping(phase1.get("failure_and_stop_contract"))
    p2_inputs = _as_mapping(phase2.get("reference_only_quality_input_control_contract"))
    p2_candidates = _as_mapping(phase2.get("quality_result_candidate_contract"))
    p2_dimensions = _as_mapping(phase2.get("quality_dimension_control_contract"))
    p2_location = _as_mapping(phase2.get("source_location_and_evidence_control_contract"))
    delivery_inference = _as_mapping(delivery_report.get("field_inference_report"))
    delivery_quality = _as_mapping(delivery_report.get("quality_test_results"))
    delivery_rollback = _as_mapping(
        delivery_report.get("reparse_and_fact_rollback_instructions")
    )
    quality_results = _list_of_mappings(quality_report.get("scenario_results"))
    return {
        "phase_contract_count": 4,
        "phase_contract_passed_count": sum(phase_results.values()),
        "phase1_reference_input_field_count": _nonnegative_int(
            p1_inputs.get("field_count")
        ),
        "phase1_future_quality_result_output_field_count": _nonnegative_int(
            p1_outputs.get("field_count")
        ),
        "phase1_quality_dimension_count": _nonnegative_int(
            p1_dimensions.get("quality_dimension_count")
        ),
        "phase1_semantic_field_count": _nonnegative_int(
            p1_semantics.get("semantic_field_count")
        ),
        "phase1_source_location_field_count": _nonnegative_int(
            p1_location.get("location_field_count")
        ),
        "phase1_declared_failure_state_count": _nonnegative_int(
            p1_failures.get("failure_state_count")
        ),
        "phase2_control_record_count": _nonnegative_int(
            p2_inputs.get("control_record_count")
        ),
        "phase2_quality_result_candidate_count": _nonnegative_int(
            p2_candidates.get("control_quality_result_candidate_count")
        ),
        "phase2_quality_dimension_count": _nonnegative_int(
            p2_dimensions.get("quality_dimension_count")
        ),
        "phase2_source_location_field_count": _nonnegative_int(
            p2_location.get("location_field_count")
        ),
        "phase2_source_location_binding_candidate_count": _nonnegative_int(
            p2_location.get("candidate_binding_count")
        ),
        "quality_scenario_count": _nonnegative_int(quality_report.get("scenario_count")),
        "quality_explicit_disposition_count": _nonnegative_int(
            quality_report.get("explicit_disposition_count")
        ),
        "quality_silent_drop_count": _nonnegative_int(
            quality_report.get("silent_drop_count")
        ),
        "quality_human_handling_required_count": _nonnegative_int(
            quality_report.get("human_handling_required_count")
        ),
        "quality_outlier_numeric_block_count": sum(
            item.get("unverified_numeric_blocks_statistical_conclusion") is True
            for item in quality_results
        ),
        "delivery_sample_count": len(
            _list_of_mappings(delivery_report.get("delivery_samples"))
        ),
        "delivery_field_reference_label_count": _nonnegative_int(
            delivery_inference.get("referenced_field_label_count")
        ),
        "delivery_quality_result_count": _nonnegative_int(
            delivery_quality.get("scenario_count")
        ),
        "delivery_human_handling_record_count": len(
            _list_of_mappings(
                delivery_report.get("unrecognized_structure_and_human_handling")
            )
        ),
        "delivery_human_confirmation_prompt_count": len(
            _list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))
        ),
        "reparse_and_fact_rollback_instructions_created": bool(delivery_rollback),
        "reparse_and_fact_rollback_return_to": delivery_rollback.get("return_to"),
    }


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
