"""Stage062 的只读整阶段复审，不读取真实表格或启动 Stage063。"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-062_表格证据绑定.md"
)
P1_CONTRACT = BASE / "stage062_table_evidence_binding_contract.json"
P2_CONTRACT = BASE / "stage062_table_evidence_binding_slice_contract.json"
P3_CONTRACT = BASE / "stage062_table_evidence_binding_scenarios_contract.json"
P4_CONTRACT = BASE / "stage062_table_evidence_binding_delivery_contract.json"

SCHEMA_VERSION = "ids.stage062.table_evidence_binding.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE062-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-062"
PASS_RESULT = "PASS_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE062-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE063-P1-GATE"
RETURN_STATE = "PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "empty-table-binding-control-human-handling",
    "merged-cells-binding-control-human-handling",
    "unit-confusion-binding-control-human-handling",
    "date-variation-binding-control-human-handling",
    "outlier-binding-control-numeric-block",
    "duplicate-row-binding-control-human-handling",
)
CONTROL_REFERENCE_FIELDS = (
    "referenced_table_evidence_binding_ref",
    "referenced_binding_request_ref",
    "referenced_fact_ref",
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
)
RUNTIME_ACTION_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "table_schema_inference_performed",
    "field_identification_performed",
    "structured_fact_extraction_performed",
    "typed_value_extraction_performed",
    "table_summary_generation_performed",
    "numeric_statistic_computation_performed",
    "quality_gate_evaluation_performed",
    "source_location_binding_performed",
    "evidence_binding_performed",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "quality_result_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage062_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage062 P1--P4，只返回 control 计数、边界与回滚结论。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    scenario_report = _as_mapping(
        (phase3_report_provider or _load_phase3_report_provider())()
    )
    delivery_report = _as_mapping(
        (phase4_report_provider or _load_phase4_report_provider())()
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3)
        and _phase3_report_valid(scenario_report),
        "P4": _phase4_contract_valid(phase4)
        and _phase4_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2, phase3, phase4, scenario_report, delivery_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "binding_dimension_and_traceability_boundary_preserved": (
            _binding_dimension_and_traceability_boundary_preserved(
                phase1, phase2, phase3, scenario_report, delivery_report
            )
        ),
        "numeric_authority_boundary_preserved": _numeric_authority_boundary_preserved(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "six_exception_categories_require_human_handling": (
            _human_handling_boundary_preserved(scenario_report, delivery_report)
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary_preserved(
            phase4, delivery_report
        ),
        "reparse_and_rollback_chain_preserved": _reparse_and_rollback_chain_preserved(
            phase4, delivery_report
        ),
        "runtime_actions_disabled": _contracts_runtime_disabled(
            phase1, phase2, phase3, phase4
        ),
        "stage063_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": (
            "FROZEN_STAGE062_TASKPACK_AND_STAGE062_P1_TO_P4_CONTROL_ARTIFACTS_ONLY"
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
                "Stage062 review document",
                "Stage062 review module",
                "Stage062 review focused tests",
                "Stage062 review governance projection",
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
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "source_location_binding_performed": False,
        "evidence_binding_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_rollback_performed": False,
        "actual_table_evidence_binding_rollback_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage062_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage063_started": False,
        "stage063_entry_allowed": False,
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
        "stage062_table_evidence_binding_scenarios.py",
        "build_table_evidence_binding_phase3_report",
    )


def _load_phase4_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage062_table_evidence_binding_delivery.py",
        "build_table_evidence_binding_phase4_delivery_report",
    )


def _module_callable_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage062_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage062 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage062 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_binding_input_contract"))
    outputs = _as_mapping(contract.get("future_table_evidence_binding_output_contract"))
    dimensions = _as_mapping(contract.get("binding_dimension_contract"))
    semantics = _as_mapping(contract.get("field_semantic_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase1.v1",
            contract.get("contract_state")
            == "PHASE1_TABLE_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE062-P1",
            contract.get("next_gate") == "IDS-STAGE062-P2-GATE",
            _phase1_or_phase2_authority_valid(contract),
            inputs.get("field_count") == 19,
            inputs.get("binding_dimension_count") == 6,
            inputs.get("actual_input_record_count") == 0,
            inputs.get("source_uri_is_opaque_reference_only") is True,
            inputs.get("source_uri_physical_path_or_actual_uri_allowed") is False,
            outputs.get("field_count") == 17,
            outputs.get("actual_table_evidence_binding_created") is False,
            outputs.get("actual_table_evidence_binding_persisted") is False,
            outputs.get("actual_evidence_record_created") is False,
            dimensions.get("binding_dimension_count") == 6,
            dimensions.get("actual_source_location_binding_count") == 0,
            dimensions.get("actual_evidence_binding_count") == 0,
            semantics.get("semantic_field_count") == 8,
            semantics.get("field_identification_performed") is False,
            failures.get("failure_state_count") == 13,
            failures.get("unrecognized_structure_requires_human_handling") is True,
            failures.get("unverified_numeric_value_blocks_statistical_conclusion")
            is True,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_binding_input_control_contract"))
    candidates = _as_mapping(contract.get("table_evidence_binding_candidate_contract"))
    numeric = _as_mapping(contract.get("semantic_and_numeric_boundary"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase2.v1",
            contract.get("contract_state")
            == "PHASE2_TABLE_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE062-P2",
            contract.get("next_gate") == "IDS-STAGE062-P3-GATE",
            contract.get("slice_executable") is True,
            contract.get("execution_ready") is False,
            _phase1_or_phase2_authority_valid(contract),
            inputs.get("field_count") == 19,
            inputs.get("control_request_count") == 2,
            inputs.get("binding_dimension_count") == 6,
            inputs.get("control_binding_dimension_reference_count") == 12,
            inputs.get("actual_input_record_count") == 0,
            candidates.get("field_count") == 17,
            candidates.get("control_binding_candidate_count") == 2,
            candidates.get("binding_state") == "UNBOUND_REFERENCE_ONLY",
            candidates.get("actual_table_evidence_binding_created") is False,
            candidates.get("actual_table_evidence_binding_persisted") is False,
            numeric.get("field_semantic_category_count") == 8,
            numeric.get("all_control_candidates_require_human_review") is True,
            numeric.get("all_control_candidates_block_numeric_authority") is True,
            numeric.get("actual_structured_fact_count") == 0,
            numeric.get("actual_numeric_fact_count") == 0,
            failures.get("failure_state_count") == 13,
            failures.get("unknown_or_reordered_control_input_rejected") is True,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("scenario_input_boundary"))
    quality = _as_mapping(contract.get("quality_scenario_validation"))
    numeric = _as_mapping(contract.get("semantic_and_numeric_boundary"))
    ownership = _as_mapping(contract.get("ownership_boundary"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase3.controlled_scenarios_contract.v1",
            contract.get("contract_state")
            == "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE062-P3",
            contract.get("next_gate") == "IDS-STAGE062-P4-GATE",
            contract.get("scenario_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("control_references_are_not_business_facts") is True,
            inputs.get("control_binding_request_count") == 2,
            inputs.get("control_table_evidence_binding_candidate_count") == 2,
            inputs.get("scenario_count") == 6,
            inputs.get("binding_dimension_count") == 6,
            inputs.get("control_source_location_reference_check_count") == 6,
            inputs.get("actual_input_record_count") == 0,
            quality.get("all_taskpack_exception_categories_covered") is True,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("human_handling_required_count") == 6,
            quality.get("outlier_blocks_statistical_conclusion") is True,
            numeric.get("numeric_statistical_conclusion_allowed") is False,
            numeric.get("model_definitive_numeric_conclusion_allowed") is False,
            numeric.get("actual_structured_fact_count") == 0,
            numeric.get("actual_evidence_binding_count") == 0,
            ownership.get("business_line_whitebox_human_handling_required") is True,
            ownership.get("automatic_business_write_allowed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("delivery_input_boundary"))
    delivery = _as_mapping(contract.get("delivery_evidence"))
    feedback = _as_mapping(contract.get("chinese_feedback_contract"))
    rollback = _as_mapping(contract.get("rollback_contract"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase4.delivery.v1",
            contract.get("contract_state")
            == "PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE062-P4",
            contract.get("next_gate") == REVIEW_GATE,
            contract.get("delivery_evidence_executable") is True,
            contract.get("execution_ready") is False,
            _phase1_or_phase2_authority_valid(contract),
            inputs.get("reference_only_binding_input_field_count") == 19,
            inputs.get("future_table_evidence_binding_output_field_count") == 17,
            inputs.get("control_binding_request_count") == 2,
            inputs.get("control_table_evidence_binding_candidate_count") == 2,
            inputs.get("binding_dimension_count") == 6,
            inputs.get("control_binding_scenario_count") == 6,
            inputs.get("metadata_only_table_evidence_binding_delivery_sample_count")
            == 6,
            inputs.get("field_reference_label_count") == 6,
            inputs.get("quality_test_result_delivery_count") == 6,
            inputs.get("human_handling_recommendation_count") == 6,
            inputs.get("human_confirmation_prompt_count") == 3,
            inputs.get("actual_input_record_count") == 0,
            inputs.get("actual_table_evidence_binding_count") == 0,
            delivery.get("metadata_only_table_evidence_binding_delivery_samples_derived")
            is True,
            delivery.get("field_inference_report_derived") is True,
            delivery.get("control_quality_test_results_derived") is True,
            delivery.get("unrecognized_structure_and_human_handling_recorded")
            is True,
            delivery.get("actual_table_evidence_binding_created") is False,
            delivery.get("numeric_statistical_conclusion_allowed") is False,
            feedback.get("message_count") == 3,
            feedback.get("all_messages_chinese") is True,
            feedback.get("automatic_confirmation_performed") is False,
            rollback.get("return_to")
            == "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("source_or_raw_data_change_allowed") is False,
            rollback.get("database_or_persistent_state_change_allowed") is False,
            rollback.get("github_or_ovh_change_allowed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase1_or_phase2_authority_valid(contract: Mapping[str, Any]) -> bool:
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            authority.get("raw_metadata_content_access_allowed") is False,
            authority.get("live_source_read_performed") is False,
            authority.get("authorized_fixture_access_performed") is False,
        )
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = report.get("scenario_results")
    if not isinstance(scenarios, list):
        return False
    return all(
        (
            report.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase3.controlled_scenarios.v1",
            report.get("result")
            == "PASS_PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report.get("valid") is True,
            report.get("next_gate") == "IDS-STAGE062-P4-GATE",
            tuple(item.get("scenario_id") for item in scenarios if isinstance(item, Mapping))
            == EXPECTED_SCENARIO_IDS,
            len(scenarios) == len(EXPECTED_SCENARIO_IDS),
            all(_scenario_result_valid(item) for item in scenarios),
            sum(
                item.get("unverified_numeric_blocks_statistical_conclusion") is True
                for item in scenarios
                if isinstance(item, Mapping)
            )
            == 1,
        )
    )


def _scenario_result_valid(item: object) -> bool:
    scenario = _as_mapping(item)
    return all(
        (
            scenario.get("control_reference_only") is True,
            scenario.get("control_scenario_metadata_only") is True,
            scenario.get("control_source_location_reference_preserved") is True,
            scenario.get("expectation_met") is True,
            scenario.get("human_handling_required") is True,
            scenario.get("silent_drop") is False,
            scenario.get("actual_source_file_traceability_validated") is False,
            scenario.get("actual_source_location_binding_created") is False,
            scenario.get("actual_evidence_record_created") is False,
            scenario.get("numeric_statistical_conclusion_allowed") is False,
            scenario.get("model_definitive_numeric_conclusion_allowed") is False,
            _control_references_only(scenario),
        )
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    samples = report.get("delivery_samples")
    handling = report.get("unrecognized_structure_and_human_handling")
    field_report = _as_mapping(report.get("field_inference_report"))
    quality = _as_mapping(report.get("quality_test_results"))
    rollback = _as_mapping(report.get("reparse_and_fact_rollback_instructions"))
    prompts = report.get("human_confirmation_prompts_zh")
    if not isinstance(samples, list) or not isinstance(handling, list):
        return False
    return all(
        (
            report.get("schema_version")
            == "ids.stage062.table_evidence_binding.phase4.delivery.v1",
            report.get("result")
            == "PASS_PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_RUNTIME_DISABLED",
            report.get("valid") is True,
            report.get("next_gate") == REVIEW_GATE,
            len(samples) == 6,
            tuple(item.get("scenario_id") for item in samples if isinstance(item, Mapping))
            == EXPECTED_SCENARIO_IDS,
            all(_delivery_sample_valid(item) for item in samples),
            field_report.get("referenced_field_label_count") == 6,
            field_report.get("scenario_reference_count") == 6,
            field_report.get("control_reference_only") is True,
            field_report.get("actual_field_mapping_created") is False,
            quality.get("scenario_count") == 6,
            quality.get("passed_scenario_count") == 6,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("human_handling_required_count") == 6,
            quality.get("outlier_numeric_block_count") == 1,
            len(handling) == 6,
            all(_human_handling_record_valid(item) for item in handling),
            isinstance(prompts, list) and len(prompts) == 3,
            rollback.get("return_to")
            == "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_file_reparse_performed") is False,
            rollback.get("actual_fact_rollback_performed") is False,
            rollback.get("actual_table_evidence_binding_rollback_performed")
            is False,
        )
    )


def _delivery_sample_valid(item: object) -> bool:
    sample = _as_mapping(item)
    return all(
        (
            sample.get("control_metadata_only") is True,
            sample.get("source_content_retained") is False,
            sample.get("typed_value_retained") is False,
            sample.get("actual_field_mapping_created") is False,
            sample.get("actual_structured_fact_created") is False,
            sample.get("actual_table_evidence_binding_created") is False,
            sample.get("actual_evidence_record_created") is False,
            _control_references_only(sample),
        )
    )


def _human_handling_record_valid(item: object) -> bool:
    record = _as_mapping(item)
    return all(
        (
            record.get("control_reference_only") is True,
            record.get("human_handling_required") is True,
            record.get("actual_unrecognized_table_structure_observed") is False,
            record.get("automatic_structure_resolution_performed") is False,
            record.get("automatic_structured_fact_write_performed") is False,
            record.get("automatic_table_evidence_binding_performed") is False,
        )
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> dict[str, Any]:
    p1_input = _as_mapping(phase1.get("reference_only_binding_input_contract"))
    p1_output = _as_mapping(phase1.get("future_table_evidence_binding_output_contract"))
    p2_input = _as_mapping(phase2.get("reference_only_binding_input_control_contract"))
    p2_candidates = _as_mapping(phase2.get("table_evidence_binding_candidate_contract"))
    p3_input = _as_mapping(phase3.get("scenario_input_boundary"))
    p3_quality = _as_mapping(phase3.get("quality_scenario_validation"))
    p4_input = _as_mapping(phase4.get("delivery_input_boundary"))
    return {
        "phase1_reference_only_binding_input_field_count": p1_input.get("field_count"),
        "phase1_future_binding_output_field_count": p1_output.get("field_count"),
        "phase2_control_binding_request_count": p2_input.get("control_request_count"),
        "phase2_control_binding_candidate_count": p2_candidates.get(
            "control_binding_candidate_count"
        ),
        "phase2_control_binding_dimension_reference_count": p2_input.get(
            "control_binding_dimension_reference_count"
        ),
        "phase3_controlled_scenario_count": p3_input.get("scenario_count"),
        "phase3_explicit_disposition_count": p3_quality.get(
            "explicit_disposition_count"
        ),
        "phase3_silent_drop_count": p3_quality.get("silent_drop_count"),
        "phase3_report_scenario_count": len(
            scenario_report.get("scenario_results", [])
            if isinstance(scenario_report.get("scenario_results"), list)
            else []
        ),
        "phase4_delivery_sample_count": p4_input.get(
            "metadata_only_table_evidence_binding_delivery_sample_count"
        ),
        "phase4_field_reference_label_count": p4_input.get(
            "field_reference_label_count"
        ),
        "phase4_quality_test_result_delivery_count": p4_input.get(
            "quality_test_result_delivery_count"
        ),
        "phase4_human_handling_recommendation_count": p4_input.get(
            "human_handling_recommendation_count"
        ),
        "phase4_human_confirmation_prompt_count": p4_input.get(
            "human_confirmation_prompt_count"
        ),
        "phase4_report_delivery_sample_count": len(
            delivery_report.get("delivery_samples", [])
            if isinstance(delivery_report.get("delivery_samples"), list)
            else []
        ),
        "phase4_return_to": _as_mapping(
            delivery_report.get("reparse_and_fact_rollback_instructions")
        ).get("return_to"),
    }


def _single_authority_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase3_authority = _as_mapping(phase3.get("source_authority"))
    return all(
        (
            _phase1_or_phase2_authority_valid(phase1),
            _phase1_or_phase2_authority_valid(phase2),
            _phase1_or_phase2_authority_valid(phase4),
            phase3_authority.get("source_document_remains_authoritative") is True,
            phase3_authority.get("second_authoritative_source_created") is False,
            scenario_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("actual_structured_fact_count") == 0,
            delivery_report.get("actual_evidence_record_count") == 0,
        )
    )


def _binding_dimension_and_traceability_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    p1_dimensions = _as_mapping(phase1.get("binding_dimension_contract"))
    p2_input = _as_mapping(phase2.get("reference_only_binding_input_control_contract"))
    p3_input = _as_mapping(phase3.get("scenario_input_boundary"))
    scenarios = scenario_report.get("scenario_results")
    samples = delivery_report.get("delivery_samples")
    return all(
        (
            p1_dimensions.get("binding_dimension_count") == 6,
            p1_dimensions.get("actual_source_location_binding_count") == 0,
            p1_dimensions.get("actual_evidence_binding_count") == 0,
            p2_input.get("binding_dimension_count") == 6,
            p2_input.get("control_binding_dimension_reference_count") == 12,
            p3_input.get("control_source_location_reference_check_count") == 6,
            p3_input.get("control_source_location_traceability_preserved") is True,
            isinstance(scenarios, list) and all(_control_references_only(item) for item in scenarios),
            isinstance(samples, list) and all(_control_references_only(item) for item in samples),
        )
    )


def _numeric_authority_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    p2_numeric = _as_mapping(phase2.get("semantic_and_numeric_boundary"))
    p3_numeric = _as_mapping(phase3.get("semantic_and_numeric_boundary"))
    p4_delivery = _as_mapping(phase4.get("delivery_evidence"))
    scenarios = scenario_report.get("scenario_results")
    return all(
        (
            _as_mapping(phase1.get("failure_and_stop_contract")).get(
                "unverified_numeric_value_blocks_statistical_conclusion"
            )
            is True,
            p2_numeric.get("source_document_remains_authoritative") is True,
            p2_numeric.get("model_direct_text_guessing_allowed") is False,
            p2_numeric.get("unverified_numeric_value_as_definitive_fact_allowed")
            is False,
            p2_numeric.get("numeric_statistic_computation_performed") is False,
            p3_numeric.get("numeric_statistical_conclusion_allowed") is False,
            p3_numeric.get("model_definitive_numeric_conclusion_allowed") is False,
            p4_delivery.get("numeric_statistical_conclusion_allowed") is False,
            p4_delivery.get("model_definitive_numeric_conclusion_allowed") is False,
            isinstance(scenarios, list)
            and all(
                _as_mapping(item).get("numeric_statistical_conclusion_allowed") is False
                and _as_mapping(item).get("model_definitive_numeric_conclusion_allowed")
                is False
                for item in scenarios
            ),
            delivery_report.get("numeric_statistical_conclusion_allowed") is False,
            delivery_report.get("model_definitive_numeric_conclusion_allowed") is False,
        )
    )


def _human_handling_boundary_preserved(
    scenario_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    scenarios = scenario_report.get("scenario_results")
    handling = delivery_report.get("unrecognized_structure_and_human_handling")
    if not isinstance(scenarios, list) or not isinstance(handling, list):
        return False
    merged = [
        _as_mapping(item)
        for item in handling
        if _as_mapping(item).get("scenario_id")
        == "merged-cells-binding-control-human-handling"
    ]
    return all(
        (
            len(scenarios) == 6,
            len(handling) == 6,
            all(_as_mapping(item).get("human_handling_required") is True for item in scenarios),
            all(_as_mapping(item).get("silent_drop") is False for item in scenarios),
            all(_human_handling_record_valid(item) for item in handling),
            len(merged) == 1,
            merged[0].get("handling_disposition")
            == "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
        )
    )


def _delivery_boundary_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    inputs = _as_mapping(phase4.get("delivery_input_boundary"))
    samples = delivery_report.get("delivery_samples")
    if not isinstance(samples, list):
        return False
    return all(
        (
            inputs.get("metadata_only_table_evidence_binding_delivery_sample_count")
            == 6,
            inputs.get("actual_table_evidence_binding_count") == 0,
            len(samples) == 6,
            all(_delivery_sample_valid(item) for item in samples),
            delivery_report.get("actual_table_evidence_binding_count") == 0,
            delivery_report.get("actual_source_location_binding_count") == 0,
            delivery_report.get("actual_evidence_record_count") == 0,
        )
    )


def _reparse_and_rollback_chain_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    contract_rollback = _as_mapping(phase4.get("rollback_contract"))
    instructions = _as_mapping(
        delivery_report.get("reparse_and_fact_rollback_instructions")
    )
    return all(
        (
            contract_rollback.get("return_to")
            == "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract_rollback.get("source_or_raw_data_change_allowed") is False,
            contract_rollback.get("fixture_change_allowed") is False,
            contract_rollback.get("database_or_persistent_state_change_allowed") is False,
            contract_rollback.get("github_or_ovh_change_allowed") is False,
            instructions.get("return_to")
            == "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            instructions.get("in_memory_control_replay_only") is True,
            instructions.get("actual_file_reparse_performed") is False,
            instructions.get("actual_fact_rollback_performed") is False,
            instructions.get("actual_table_evidence_binding_rollback_performed")
            is False,
        )
    )


def _contracts_runtime_disabled(*contracts: Mapping[str, Any]) -> bool:
    return all(
        _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary")))
        for contract in contracts
    )


def _runtime_boundary_disabled(boundary: Mapping[str, Any]) -> bool:
    # 各 phase 只声明自己可触及的运行动作；未声明项同样保持未执行。
    return all(boundary.get(field, False) is False for field in RUNTIME_ACTION_FIELDS)


def _report_runtime_disabled(report: Mapping[str, Any]) -> bool:
    return all(
        report.get(field) is False
        for field in (
            *RUNTIME_ACTION_FIELDS,
            "actual_file_reparse_performed",
            "actual_fact_rollback_performed",
            "actual_table_evidence_binding_rollback_performed",
            "batch_review_performed",
            "stage063_started",
            "stage063_entry_allowed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_performed",
            "push_allowed",
        )
    )


def _control_references_only(item: object) -> bool:
    value = _as_mapping(item)
    return all(
        isinstance(value.get(field), str) and ":control:" in value[field]
        for field in CONTROL_REFERENCE_FIELDS
    )


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
