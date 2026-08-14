"""Stage066 的只读整阶段机械复审，不读取真实资料或启动 Stage067。"""

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
    / "STAGE-066_Chunk覆盖率指标.md"
)
P1_CONTRACT = BASE / "stage066_chunk_coverage_metrics_contract.json"
P2_CONTRACT = BASE / "stage066_chunk_coverage_metrics_slice_contract.json"
P3_CONTRACT = BASE / "stage066_chunk_coverage_metrics_scenarios_contract.json"
P4_CONTRACT = BASE / "stage066_chunk_coverage_metrics_delivery_contract.json"

SCHEMA_VERSION = "ids.stage066.chunk_coverage_metrics.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE066-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-066"
PASS_RESULT = "PASS_REVIEWED_LOCAL_CHUNK_COVERAGE_METRICS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_CHUNK_COVERAGE_METRICS_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE066-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE067-P1-GATE"
RETURN_STATE = "PHASE4_CHUNK_COVERAGE_METRICS_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P3_RETURN_STATE = "PHASE3_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_PASS_RESULT = "PASS_PHASE3_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PHASE4_CHUNK_COVERAGE_METRICS_DELIVERY_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "long-document-coverage-control-human-review",
    "cross-page-table-coverage-control-human-handling",
    "engineering-procedure-coverage-control-human-review",
    "parameter-table-coverage-control-human-review",
    "citation-page-coverage-control-human-confirmation",
    "duplicate-chunk-coverage-control-human-review",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
RUNTIME_ACTION_FIELDS = (
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
    "github_upload_allowed",
    "push_allowed",
)
P3_REPORT_FALSE_FIELDS = (
    "actual_source_document_read_performed",
    "actual_page_traceability_validated",
    "actual_source_traceability_binding_created",
    "actual_duplicate_chunk_detected",
    "actual_duplicate_chunk_identity_or_hash_validated",
    "actual_duplicate_embedding_prevented",
    "actual_duplicate_index_prevented",
    "duplicate_embedding_or_index_write_attempted",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chapter_detection_performed",
    "chunking_execution_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "phase4_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
)
P4_REPORT_FALSE_FIELDS = (
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
REVIEW_RUNTIME_FALSE_FIELDS = (
    *P4_REPORT_FALSE_FIELDS,
    "actual_chunk_jsonl_written",
    "actual_document_coverage_calculated",
    "actual_chunk_coverage_calculated",
    "actual_low_quality_chunk_observed",
    "actual_quality_measurement_performed",
    "actual_quality_regression_performed",
    "actual_chunk_regeneration_performed",
    "actual_chunk_version_rollback_performed",
    "stage067_started",
    "stage067_entry_allowed",
    "github_upload_performed",
    "push_performed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage066_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage066 P1--P4，返回控制事实、门禁与回退结论。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    scenario_report = _as_mapping(
        (phase3_report_provider or _load_report_provider(
            "stage066_chunk_coverage_metrics_scenarios.py",
            "build_chunk_coverage_metrics_phase3_report",
        ))()
    )
    delivery_report = _as_mapping(
        (phase4_report_provider or _load_report_provider(
            "stage066_chunk_coverage_metrics_delivery.py",
            "build_chunk_coverage_metrics_phase4_delivery_report",
        ))()
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3) and _phase3_report_valid(scenario_report),
        "P4": _phase4_contract_valid(phase4) and _phase4_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2, phase3, phase4, scenario_report, delivery_report
    )
    review_invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "chunk_coverage_metrics_shape_preserved": _coverage_shape_preserved(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "six_special_scenarios_require_whitebox_human_handling": (
            _human_handling_boundary_preserved(phase2, phase3, scenario_report, delivery_report)
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary_preserved(
            phase4, delivery_report
        ),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain_preserved(
            phase4, delivery_report
        ),
        "future_stage_ownership_preserved": _future_stage_ownership_preserved(
            phase1, phase2, phase3
        ),
        "runtime_actions_disabled": _contracts_runtime_disabled(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "stage067_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE066_TASKPACK_AND_STAGE066_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": review_invariants,
        "review_finding_count": 0,
        "review_valid": False,
        "result": FAIL_RESULT,
        "rollback": {
            "return_to": RETURN_STATE,
            "revertable_artifacts": [
                "Stage066 review document",
                "Stage066 review module",
                "Stage066 review focused tests",
                "Stage066 review governance projection",
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
        "parser_execution_performed": False,
        "chapter_detection_performed": False,
        "chunking_execution_performed": False,
        "chunk_identity_generation_performed": False,
        "chunk_hash_computation_performed": False,
        "chunk_version_generation_performed": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "actual_chunk_jsonl_written": False,
        "actual_document_coverage_calculated": False,
        "actual_chunk_coverage_calculated": False,
        "actual_low_quality_chunk_observed": False,
        "actual_quality_measurement_performed": False,
        "actual_quality_regression_performed": False,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "stage066_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage067_started": False,
        "stage067_entry_allowed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_performed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        _review_runtime_actions_disabled(report)
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


def _load_report_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage066_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage066 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, callable_name, None)
    if not callable(provider):
        raise RuntimeError(f"Stage066 review dependency is invalid: {filename}")
    return provider


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _as_mapping(contract.get("source_authority"))
    authority = _as_mapping(contract.get("authority_and_decision_boundary"))
    inputs = _as_mapping(contract.get("reference_only_chunk_coverage_input_contract"))
    outputs = _as_mapping(contract.get("future_chunk_coverage_output_contract"))
    coverage = _as_mapping(contract.get("coverage_metric_definition_contract"))
    protected = _as_mapping(contract.get("protected_semantic_boundary_contract"))
    traceability = _as_mapping(contract.get("traceability_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    future = _as_mapping(contract.get("future_stage_interface_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage066.chunk_coverage_metrics.phase1.v1",
            contract.get("contract_state") == "PHASE1_CHUNK_COVERAGE_METRICS_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE066-P1",
            contract.get("next_gate") == "IDS-STAGE066-P2-GATE",
            source.get("second_authoritative_source_created") is False,
            source.get("source_body_or_path_allowed") is False,
            source.get("raw_metadata_content_access_allowed") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("coverage_metrics_can_replace_source_document") is False,
            authority.get("coverage_metrics_can_become_business_fact_authority") is False,
            inputs.get("field_count") == 12,
            inputs.get("actual_input_request_count") == 0,
            inputs.get("document_body_allowed") is False,
            outputs.get("field_count") == 17,
            outputs.get("actual_chunk_coverage_metrics_record_created") is False,
            outputs.get("actual_chunk_coverage_metrics_record_persisted") is False,
            coverage.get("actual_parse_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            coverage.get("unknown_or_zero_denominator_blocks_metric_output") is True,
            protected.get("protected_semantic_asset_type_count") == 3,
            protected.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("actual_traceability_binding_count") == 0,
            failures.get("failure_state_count") == 14,
            failures.get("automatic_business_write_allowed") is False,
            future.get("coverage_calculation_owner") == "STAGE-066",
            future.get("quality_regression_execution_owner") == "STAGE-067",
            future.get("quality_degradation_execution_owner") == "STAGE-068",
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _as_mapping(contract.get("source_authority"))
    authority = _as_mapping(contract.get("authority_and_decision_boundary"))
    inputs = _as_mapping(contract.get("reference_only_chunk_coverage_input_control_contract"))
    records = _as_mapping(contract.get("control_chunk_coverage_metrics_record_contract"))
    coverage = _as_mapping(contract.get("coverage_metric_control_contract"))
    protected = _as_mapping(contract.get("protected_semantic_boundary_control_contract"))
    traceability = _as_mapping(contract.get("traceability_control_contract"))
    markers = _as_mapping(contract.get("low_confidence_control_marker_contract"))
    return all(
        (
            contract.get("schema_version") == "ids.stage066.chunk_coverage_metrics.phase2.v1",
            contract.get("contract_state") == "PHASE2_CHUNK_COVERAGE_METRICS_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE066-P2",
            contract.get("next_gate") == "IDS-STAGE066-P3-GATE",
            contract.get("slice_executable") is True,
            contract.get("execution_ready") is False,
            source.get("second_authoritative_source_created") is False,
            source.get("source_body_or_path_allowed") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("control_coverage_metrics_can_replace_source_document") is False,
            authority.get("control_coverage_metrics_can_become_business_fact_authority") is False,
            inputs.get("field_count") == 12,
            inputs.get("control_request_count") == 4,
            inputs.get("actual_input_request_count") == 0,
            records.get("field_count") == 17,
            records.get("control_record_count") == 4,
            records.get("actual_chunk_coverage_metrics_record_created") is False,
            records.get("actual_chunk_coverage_metrics_record_persisted") is False,
            coverage.get("control_parse_coverage_label_projection_count") == 4,
            coverage.get("control_chunk_coverage_label_projection_count") == 4,
            coverage.get("control_uncovered_page_reference_label_projection_count") == 4,
            coverage.get("unknown_denominator_control_record_count") == 1,
            coverage.get("actual_parse_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            protected.get("protected_semantic_asset_type_count") == 3,
            protected.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("control_traceability_reference_count") == 24,
            traceability.get("actual_traceability_binding_count") == 0,
            markers.get("low_confidence_control_marker_count") == 4,
            markers.get("all_control_records_require_business_line_human_review") is True,
            markers.get("control_marker_is_not_actual_low_quality_detection") is True,
            markers.get("quality_regression_owner") == "STAGE-067",
            markers.get("quality_degradation_owner") == "STAGE-068",
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("scenario_input_boundary"))
    validation = _as_mapping(contract.get("scenario_validation"))
    duplicate = _as_mapping(contract.get("duplicate_embedding_and_index_boundary"))
    authority = _as_mapping(contract.get("authority_and_decision_boundary"))
    source = _as_mapping(contract.get("source_authority"))
    ownership = _as_mapping(contract.get("ownership_boundary"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage066.chunk_coverage_metrics.phase3.controlled_scenarios_contract.v1",
            contract.get("contract_state")
            == "PHASE3_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE066-P3",
            contract.get("next_gate") == "IDS-STAGE066-P4-GATE",
            contract.get("scenario_executable") is True,
            contract.get("execution_ready") is False,
            inputs.get("phase2_control_record_count") == 4,
            inputs.get("phase2_control_record_field_count") == 17,
            inputs.get("scenario_count") == 6,
            inputs.get("actual_input_request_count") == 0,
            validation.get("all_taskpack_special_scenarios_covered") is True,
            validation.get("business_line_human_handling_required") is True,
            validation.get("control_traceability_field_count") == 6,
            validation.get("control_traceability_reference_check_count") == 36,
            validation.get("silent_drop_allowed") is False,
            validation.get("unique_control_metric_record_count") == 4,
            duplicate.get("control_duplicate_write_prohibition_asserted") is True,
            duplicate.get("embedding_or_index_write_attempted") is False,
            duplicate.get("deduplication_effect_claim_allowed") is False,
            source.get("second_authoritative_source_created") is False,
            source.get("actual_source_document_read_performed") is False,
            source.get("source_document_remains_authoritative") is True,
            authority.get("coverage_metric_control_record_can_replace_source_document") is False,
            authority.get("coverage_metric_control_record_can_become_business_fact_authority") is False,
            ownership.get("chunk_quality_regression_owner") == "STAGE-067",
            ownership.get("quality_degradation_and_human_review_owner") == "STAGE-068",
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _as_mapping(contract.get("delivery_artifacts"))
    samples = _as_mapping(delivery.get("chunk_jsonl_samples"))
    coverage = _as_mapping(delivery.get("coverage_report"))
    low_quality = _as_mapping(delivery.get("low_quality_chunk_list"))
    regression = _as_mapping(delivery.get("regression_test_results"))
    boundary = _as_mapping(contract.get("chunking_strategy_applicability_boundary"))
    rollback = _as_mapping(contract.get("regeneration_and_version_rollback"))
    authority = _as_mapping(contract.get("source_authority"))
    failures = contract.get("failure_states")
    return all(
        (
            contract.get("schema_version")
            == "ids.stage066.chunk_coverage_metrics.phase4.delivery_contract.v1",
            contract.get("task_id") == "IDS-V0_1-STAGE066-P4",
            contract.get("entry_gate") == "IDS-STAGE066-P4-GATE",
            contract.get("next_gate") == REVIEW_GATE,
            contract.get("delivery_executable") is True,
            contract.get("execution_ready") is False,
            samples.get("sample_count") == 6,
            samples.get("metadata_only") is True,
            samples.get("actual_jsonl_file_written") is False,
            coverage.get("control_scenario_count") == 6,
            coverage.get("control_traceability_reference_check_count") == 36,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            low_quality.get("control_item_count") == 6,
            low_quality.get("all_items_require_human_review") is True,
            low_quality.get("actual_quality_measurement_performed") is False,
            regression.get("control_scenario_count") == 6,
            regression.get("silent_drop_count") == 0,
            regression.get("actual_quality_regression_performed") is False,
            boundary.get("strategy_boundary_is_control_metadata_only") is True,
            boundary.get("actual_strategy_applicability_validated") is False,
            boundary.get("actual_production_quality_claim_allowed") is False,
            rollback.get("rollback_target_result") == P3_PASS_RESULT,
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("phase1_phase2_phase3_artifacts_preserved") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("business_line_white_box_human_review_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("delivery_control_metadata_can_replace_source_document") is False,
            authority.get("delivery_control_metadata_can_become_business_fact_authority") is False,
            isinstance(failures, list) and len(failures) == 11,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _mapping_sequence(report.get("scenario_results"))
    return all(
        (
            report.get("schema_version")
            == "ids.stage066.chunk_coverage_metrics.phase3.controlled_scenarios.v1",
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("unique_control_metric_record_count") == 4,
            report.get("control_traceability_field_count") == 6,
            report.get("control_traceability_reference_check_count") == 36,
            report.get("control_traceability_reference_shape_preserved") is True,
            report.get("control_duplicate_write_prohibition_asserted") is True,
            report.get("source_document_remains_authoritative") is True,
            report.get("coverage_metric_control_record_can_replace_source_document") is False,
            report.get("coverage_metric_control_record_can_become_business_fact_authority") is False,
            tuple(item.get("scenario_id") for item in scenarios) == EXPECTED_SCENARIO_IDS,
            all(_scenario_is_control_only(item) for item in scenarios),
            _all_false(report, P3_REPORT_FALSE_FIELDS),
        )
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    samples = _mapping_sequence(report.get("chunk_jsonl_samples"))
    lines = report.get("chunk_jsonl_sample_lines")
    coverage = _as_mapping(report.get("coverage_report"))
    low_quality = _mapping_sequence(report.get("low_quality_chunk_list"))
    regression = _as_mapping(report.get("regression_test_results"))
    boundary = _as_mapping(report.get("chunking_strategy_applicability_boundary"))
    rollback = _as_mapping(report.get("regeneration_and_version_rollback_instructions"))
    prompts = report.get("human_confirmation_prompts_zh")
    return all(
        (
            report.get("schema_version") == "ids.stage066.chunk_coverage_metrics.phase4.delivery.v1",
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_controlled_scenarios_reused_as_reference_only") is True,
            report.get("phase3_controlled_scenarios_report_valid") is True,
            len(samples) == 6,
            isinstance(lines, Sequence) and not isinstance(lines, (str, bytes)) and len(lines) == 6,
            tuple(item.get("scenario_id") for item in samples) == EXPECTED_SCENARIO_IDS,
            all(_sample_is_metadata_only(item) for item in samples),
            report.get("actual_jsonl_file_written") is False,
            coverage.get("control_scenario_count") == 6,
            coverage.get("chunk_jsonl_sample_count") == 6,
            coverage.get("unique_control_metric_record_count") == 4,
            coverage.get("control_traceability_field_count") == 6,
            coverage.get("control_traceability_reference_check_count") == 36,
            coverage.get("control_coverage_complete") is True,
            coverage.get("control_coverage_only") is True,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            len(low_quality) == 6,
            all(_low_quality_is_control_only(item) for item in low_quality),
            regression.get("control_scenario_count") == 6,
            regression.get("low_quality_control_item_count") == 6,
            regression.get("silent_drop_count") == 0,
            regression.get("control_regression_consistent") is True,
            regression.get("actual_quality_regression_performed") is False,
            boundary.get("strategy_boundary_is_control_metadata_only") is True,
            boundary.get("unverified_boundary_cannot_trigger_automatic_chunk_write") is True,
            boundary.get("actual_strategy_applicability_validated") is False,
            rollback.get("rollback_target_result") == P3_PASS_RESULT,
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("phase1_phase2_phase3_artifacts_preserved") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            isinstance(prompts, Sequence) and not isinstance(prompts, (str, bytes)) and len(prompts) == 3,
            report.get("source_document_remains_authoritative") is True,
            report.get("business_line_white_box_human_review_remains_authoritative") is True,
            report.get("delivery_control_metadata_can_replace_source_document") is False,
            report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
            report.get("real_source_content_retained") is False,
            report.get("actual_input_document_count") == 0,
            report.get("actual_chunk_count") == 0,
            report.get("actual_chunk_coverage_metrics_record_count") == 0,
            report.get("actual_traceability_binding_count") == 0,
            report.get("actual_chunk_regeneration_performed") is False,
            report.get("actual_chunk_version_rollback_performed") is False,
            report.get("actual_coverage_metrics_implementation_performed") is False,
            report.get("whole_stage_review_performed") is False,
            report.get("batch_review_performed") is False,
            report.get("github_upload_performed") is False,
            report.get("push_performed") is False,
            _all_false(report, P4_REPORT_FALSE_FIELDS),
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
    phase1_inputs = _as_mapping(phase1.get("reference_only_chunk_coverage_input_contract"))
    phase1_outputs = _as_mapping(phase1.get("future_chunk_coverage_output_contract"))
    phase1_protected = _as_mapping(phase1.get("protected_semantic_boundary_contract"))
    phase1_traceability = _as_mapping(phase1.get("traceability_contract"))
    phase1_failures = _as_mapping(phase1.get("failure_and_stop_contract"))
    phase2_inputs = _as_mapping(phase2.get("reference_only_chunk_coverage_input_control_contract"))
    phase2_records = _as_mapping(phase2.get("control_chunk_coverage_metrics_record_contract"))
    phase2_coverage = _as_mapping(phase2.get("coverage_metric_control_contract"))
    phase2_traceability = _as_mapping(phase2.get("traceability_control_contract"))
    phase2_markers = _as_mapping(phase2.get("low_confidence_control_marker_contract"))
    phase4_delivery = _as_mapping(phase4.get("delivery_artifacts"))
    phase4_samples = _as_mapping(phase4_delivery.get("chunk_jsonl_samples"))
    phase4_low_quality = _as_mapping(phase4_delivery.get("low_quality_chunk_list"))
    phase4_failures = phase4.get("failure_states")
    return {
        "phase1_reference_only_input_field_count": phase1_inputs.get("field_count"),
        "phase1_future_output_field_count": phase1_outputs.get("field_count"),
        "protected_semantic_asset_type_count": phase1_protected.get("protected_semantic_asset_type_count"),
        "traceability_field_count": phase1_traceability.get("traceability_field_count"),
        "phase1_declared_failure_state_count": phase1_failures.get("failure_state_count"),
        "phase2_control_request_count": phase2_inputs.get("control_request_count"),
        "phase2_control_record_count": phase2_records.get("control_record_count"),
        "phase2_control_traceability_reference_count": phase2_traceability.get("control_traceability_reference_count"),
        "unknown_denominator_control_record_count": phase2_coverage.get("unknown_denominator_control_record_count"),
        "low_confidence_control_marker_count": phase2_markers.get("low_confidence_control_marker_count"),
        "scenario_count": scenario_report.get("scenario_count"),
        "explicit_disposition_count": scenario_report.get("explicit_disposition_count"),
        "silent_drop_count": scenario_report.get("silent_drop_count"),
        "human_handling_required_count": scenario_report.get("human_handling_required_count"),
        "unique_control_metric_record_count": scenario_report.get("unique_control_metric_record_count"),
        "scenario_traceability_reference_check_count": scenario_report.get("control_traceability_reference_check_count"),
        "metadata_only_jsonl_sample_count": phase4_samples.get("sample_count"),
        "low_quality_control_record_count": phase4_low_quality.get("control_item_count"),
        "human_confirmation_prompt_count": len(delivery_report.get("human_confirmation_prompts_zh", [])),
        "phase4_declared_failure_state_count": len(phase4_failures) if isinstance(phase4_failures, list) else 0,
        "phase4_return_to": _as_mapping(phase4.get("regeneration_and_version_rollback")).get("rollback_target_result"),
    }


def _single_authority_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase1_authority = _as_mapping(phase1.get("authority_and_decision_boundary"))
    phase2_authority = _as_mapping(phase2.get("authority_and_decision_boundary"))
    phase3_authority = _as_mapping(phase3.get("authority_and_decision_boundary"))
    phase4_authority = _as_mapping(phase4.get("source_authority"))
    return all(
        (
            phase1_authority.get("source_document_remains_authoritative") is True,
            phase1_authority.get("coverage_metrics_can_replace_source_document") is False,
            phase1_authority.get("coverage_metrics_can_become_business_fact_authority") is False,
            phase2_authority.get("source_document_remains_authoritative") is True,
            phase2_authority.get("control_coverage_metrics_can_replace_source_document") is False,
            phase2_authority.get("control_coverage_metrics_can_become_business_fact_authority") is False,
            phase3_authority.get("source_document_remains_authoritative") is True,
            phase3_authority.get("coverage_metric_control_record_can_replace_source_document") is False,
            phase3_authority.get("coverage_metric_control_record_can_become_business_fact_authority") is False,
            phase4_authority.get("source_document_remains_authoritative") is True,
            phase4_authority.get("second_authoritative_source_created") is False,
            phase4_authority.get("delivery_control_metadata_can_replace_source_document") is False,
            phase4_authority.get("delivery_control_metadata_can_become_business_fact_authority") is False,
            scenario_report.get("source_document_remains_authoritative") is True,
            scenario_report.get("coverage_metric_control_record_can_become_business_fact_authority") is False,
            delivery_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
        )
    )


def _coverage_shape_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    replay = _controlled_replay(phase1, phase2, phase3, phase4, scenario_report, delivery_report)
    return replay == {
        "phase1_reference_only_input_field_count": 12,
        "phase1_future_output_field_count": 17,
        "protected_semantic_asset_type_count": 3,
        "traceability_field_count": 6,
        "phase1_declared_failure_state_count": 14,
        "phase2_control_request_count": 4,
        "phase2_control_record_count": 4,
        "phase2_control_traceability_reference_count": 24,
        "unknown_denominator_control_record_count": 1,
        "low_confidence_control_marker_count": 4,
        "scenario_count": 6,
        "explicit_disposition_count": 6,
        "silent_drop_count": 0,
        "human_handling_required_count": 6,
        "unique_control_metric_record_count": 4,
        "scenario_traceability_reference_check_count": 36,
        "metadata_only_jsonl_sample_count": 6,
        "low_quality_control_record_count": 6,
        "human_confirmation_prompt_count": 3,
        "phase4_declared_failure_state_count": 11,
        "phase4_return_to": P3_PASS_RESULT,
    }


def _human_handling_boundary_preserved(
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase2_markers = _as_mapping(phase2.get("low_confidence_control_marker_contract"))
    phase3_validation = _as_mapping(phase3.get("scenario_validation"))
    low_quality = _mapping_sequence(delivery_report.get("low_quality_chunk_list"))
    return all(
        (
            phase2_markers.get("all_control_records_require_business_line_human_review") is True,
            phase2_markers.get("control_marker_is_not_actual_low_quality_detection") is True,
            phase3_validation.get("all_taskpack_special_scenarios_covered") is True,
            phase3_validation.get("business_line_human_handling_required") is True,
            scenario_report.get("human_handling_required_count") == 6,
            scenario_report.get("silent_drop_count") == 0,
            len(low_quality) == 6,
            all(item.get("quality_disposition") == "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW" for item in low_quality),
            all(item.get("actual_low_quality_chunk_observed") is False for item in low_quality),
        )
    )


def _delivery_boundary_preserved(phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]) -> bool:
    contract_delivery = _as_mapping(phase4.get("delivery_artifacts"))
    samples = _as_mapping(contract_delivery.get("chunk_jsonl_samples"))
    return all(
        (
            samples.get("metadata_only") is True,
            samples.get("actual_jsonl_file_written") is False,
            delivery_report.get("actual_jsonl_file_written") is False,
            delivery_report.get("actual_delivery_file_written") is False,
            delivery_report.get("actual_chunk_count") == 0,
            delivery_report.get("actual_chunk_coverage_metrics_record_count") == 0,
            delivery_report.get("actual_coverage_metrics_implementation_performed") is False,
            delivery_report.get("delivery_control_metadata_can_replace_source_document") is False,
            delivery_report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
        )
    )


def _rollback_chain_preserved(phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]) -> bool:
    contract_rollback = _as_mapping(phase4.get("regeneration_and_version_rollback"))
    delivery_rollback = _as_mapping(delivery_report.get("regeneration_and_version_rollback_instructions"))
    return all(
        (
            contract_rollback.get("rollback_target_result") == P3_PASS_RESULT,
            contract_rollback.get("in_memory_control_replay_only") is True,
            contract_rollback.get("phase1_phase2_phase3_artifacts_preserved") is True,
            contract_rollback.get("actual_chunk_regeneration_performed") is False,
            contract_rollback.get("actual_chunk_version_rollback_performed") is False,
            delivery_rollback.get("rollback_target_result") == P3_PASS_RESULT,
            delivery_rollback.get("in_memory_control_replay_only") is True,
            delivery_rollback.get("phase1_phase2_phase3_artifacts_preserved") is True,
            delivery_rollback.get("source_or_raw_data_change_allowed") is False,
            delivery_rollback.get("database_schema_change_allowed") is False,
            delivery_rollback.get("github_or_ovh_change_allowed") is False,
        )
    )


def _future_stage_ownership_preserved(
    phase1: Mapping[str, Any], phase2: Mapping[str, Any], phase3: Mapping[str, Any]
) -> bool:
    phase1_future = _as_mapping(phase1.get("future_stage_interface_boundary"))
    phase2_markers = _as_mapping(phase2.get("low_confidence_control_marker_contract"))
    phase3_ownership = _as_mapping(phase3.get("ownership_boundary"))
    return all(
        (
            phase1_future.get("coverage_calculation_owner") == "STAGE-066",
            phase1_future.get("quality_regression_execution_owner") == "STAGE-067",
            phase1_future.get("quality_degradation_execution_owner") == "STAGE-068",
            phase1_future.get("quality_regression_performed") is False,
            phase1_future.get("quality_degradation_performed") is False,
            phase2_markers.get("quality_regression_owner") == "STAGE-067",
            phase2_markers.get("quality_degradation_owner") == "STAGE-068",
            phase2_markers.get("quality_regression_performed") is False,
            phase2_markers.get("quality_degradation_performed") is False,
            phase3_ownership.get("chunk_quality_regression_owner") == "STAGE-067",
            phase3_ownership.get("quality_degradation_and_human_review_owner") == "STAGE-068",
            phase3_ownership.get("cross_stage_owner_override_allowed") is False,
        )
    )


def _contracts_runtime_disabled(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _runtime_boundary_disabled(_as_mapping(phase1.get("runtime_boundary"))),
            _runtime_boundary_disabled(_as_mapping(phase2.get("runtime_boundary"))),
            _runtime_boundary_disabled(_as_mapping(phase3.get("runtime_boundary"))),
            _runtime_boundary_disabled(_as_mapping(phase4.get("runtime_boundary"))),
            _all_false(scenario_report, P3_REPORT_FALSE_FIELDS),
            _all_false(delivery_report, P4_REPORT_FALSE_FIELDS),
            delivery_report.get("actual_jsonl_file_written") is False,
            delivery_report.get("actual_chunk_regeneration_performed") is False,
            delivery_report.get("actual_chunk_version_rollback_performed") is False,
        )
    )


def _runtime_boundary_disabled(boundary: Mapping[str, Any]) -> bool:
    return _all_false(boundary, RUNTIME_ACTION_FIELDS)


def _review_runtime_actions_disabled(report: Mapping[str, Any]) -> bool:
    return _all_false(report, REVIEW_RUNTIME_FALSE_FIELDS)


def _scenario_is_control_only(item: Mapping[str, Any]) -> bool:
    return all(
        (
            item.get("expectation_met") is True,
            item.get("human_handling_required") is True,
            item.get("control_reference_only") is True,
            item.get("control_scenario_metadata_only") is True,
            item.get("control_traceability_reference_preserved") is True,
            item.get("control_traceability_reference_count") == 6,
            item.get("silent_drop") is False,
            all(isinstance(item.get(field), str) and ":control:" in item[field] for field in TRACEABILITY_FIELDS),
        )
    )


def _sample_is_metadata_only(item: Mapping[str, Any]) -> bool:
    return all(
        (
            item.get("control_metadata_only") is True,
            item.get("human_review_required") is True,
            item.get("source_content_retained") is False,
            item.get("actual_chunk_created") is False,
            item.get("actual_chunk_identifier_generated") is False,
            item.get("actual_chunk_hash_computed") is False,
            item.get("actual_chunk_version_generated") is False,
            item.get("actual_chunk_coverage_metrics_created") is False,
            item.get("actual_parse_coverage_calculated") is False,
            item.get("actual_chunk_coverage_calculated") is False,
            item.get("actual_embedding_written") is False,
            item.get("actual_index_written") is False,
        )
    )


def _low_quality_is_control_only(item: Mapping[str, Any]) -> bool:
    return all(
        (
            item.get("quality_disposition") == "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW",
            item.get("control_metadata_only") is True,
            item.get("actual_low_quality_chunk_observed") is False,
            item.get("actual_quality_measurement_performed") is False,
            item.get("automatic_quality_degradation_action_performed") is False,
        )
    )


def _all_false(mapping: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(mapping.get(field) is False for field in fields)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]
