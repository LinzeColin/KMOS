"""Stage065 的只读整阶段机械复审，不读取真实资料或启动 Stage066。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
    / "STAGE-065_工程语义资产分类.md"
)
P1_CONTRACT = BASE / "stage065_engineering_semantic_asset_classification_contract.json"
P2_CONTRACT = BASE / "stage065_engineering_semantic_asset_classification_slice_contract.json"
P3_CONTRACT = BASE / "stage065_engineering_semantic_asset_classification_scenarios_contract.json"
P4_CONTRACT = BASE / "stage065_engineering_semantic_asset_classification_delivery_contract.json"

SCHEMA_VERSION = "ids.stage065.engineering_semantic_asset_classification.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE065-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-065"
PASS_RESULT = "PASS_REVIEWED_LOCAL_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE065-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE066-P1-GATE"
RETURN_STATE = "PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P3_RETURN_STATE = "PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

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

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage065_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage065 P1--P4，返回控制事实、门禁与回退结论。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    scenario_report = _as_mapping(
        (phase3_report_provider or _load_report_provider(
            "stage065_engineering_semantic_asset_classification_scenarios.py",
            "build_engineering_semantic_asset_classification_phase3_report",
        ))()
    )
    delivery_report = _as_mapping(
        (phase4_report_provider or _load_report_provider(
            "stage065_engineering_semantic_asset_classification_delivery.py",
            "build_engineering_semantic_asset_classification_phase4_delivery_report",
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
        "semantic_asset_classification_shape_preserved": (
            _semantic_asset_classification_shape_preserved(
                phase1, phase2, phase3, scenario_report
            )
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
            phase1, phase4
        ),
        "runtime_actions_disabled": _contracts_runtime_disabled(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "stage066_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE065_TASKPACK_AND_STAGE065_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
                "Stage065 review document",
                "Stage065 review module",
                "Stage065 review focused tests",
                "Stage065 review governance projection",
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
        "stage065_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage066_started": False,
        "stage066_entry_allowed": False,
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
    spec = importlib.util.spec_from_file_location(f"stage065_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage065 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage065 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_semantic_asset_classification_input_contract"))
    outputs = _as_mapping(contract.get("future_semantic_asset_classification_output_contract"))
    catalog = _as_mapping(contract.get("engineering_semantic_asset_type_catalog"))
    protected = _as_mapping(contract.get("protected_semantic_boundary_contract"))
    traceability = _as_mapping(contract.get("traceability_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase1.v1",
            contract.get("contract_state")
            == "PHASE1_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE065-P1",
            contract.get("next_gate") == "IDS-STAGE065-P2-GATE",
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            authority.get("raw_metadata_content_access_allowed") is False,
            inputs.get("field_count") == 12,
            inputs.get("actual_input_request_count") == 0,
            inputs.get("document_body_allowed") is False,
            outputs.get("field_count") == 16,
            outputs.get("actual_semantic_asset_record_created") is False,
            outputs.get("actual_semantic_asset_record_persisted") is False,
            catalog.get("asset_type_count") == 7,
            catalog.get("actual_asset_classification_count") == 0,
            protected.get("protected_semantic_asset_type_count") == 3,
            protected.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("actual_traceability_binding_count") == 0,
            failures.get("failure_state_count") == 10,
            failures.get("automatic_business_write_allowed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_semantic_asset_classification_input_control_contract"))
    records = _as_mapping(contract.get("control_semantic_asset_classification_record_contract"))
    protected = _as_mapping(contract.get("protected_semantic_boundary_control_contract"))
    traceability = _as_mapping(contract.get("traceability_control_contract"))
    markers = _as_mapping(contract.get("low_confidence_control_marker_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase2.v1",
            contract.get("contract_state")
            == "PHASE2_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE065-P2",
            contract.get("next_gate") == "IDS-STAGE065-P3-GATE",
            contract.get("slice_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            inputs.get("field_count") == 12,
            inputs.get("control_request_count") == 7,
            inputs.get("engineering_semantic_asset_type_count") == 7,
            inputs.get("actual_input_request_count") == 0,
            records.get("field_count") == 16,
            records.get("control_record_count") == 7,
            records.get("actual_semantic_asset_record_created") is False,
            records.get("actual_semantic_asset_record_persisted") is False,
            protected.get("protected_semantic_asset_type_count") == 3,
            protected.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("control_traceability_reference_count") == 42,
            traceability.get("actual_traceability_binding_count") == 0,
            markers.get("low_confidence_control_marker_count") == 7,
            markers.get("all_control_records_require_business_line_human_review") is True,
            markers.get("control_marker_is_not_actual_low_quality_detection") is True,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("scenario_input_boundary"))
    validation = _as_mapping(contract.get("scenario_validation"))
    duplicate = _as_mapping(contract.get("duplicate_embedding_and_index_boundary"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase3.controlled_scenarios_contract.v1",
            contract.get("contract_state") == P3_RETURN_STATE,
            contract.get("task_id") == "IDS-V0_1-STAGE065-P3",
            contract.get("next_gate") == "IDS-STAGE065-P4-GATE",
            contract.get("scenario_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("control_references_are_not_business_facts") is True,
            inputs.get("phase2_control_record_count") == 7,
            inputs.get("scenario_count") == 6,
            inputs.get("actual_input_request_count") == 0,
            validation.get("all_taskpack_special_scenarios_covered") is True,
            validation.get("explicit_disposition_required") is True,
            validation.get("silent_drop_allowed") is False,
            validation.get("business_line_human_handling_required") is True,
            validation.get("control_traceability_field_count") == 6,
            validation.get("control_traceability_reference_check_count") == 36,
            duplicate.get("control_duplicate_write_prohibition_asserted") is True,
            duplicate.get("embedding_or_index_write_attempted") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _as_mapping(contract.get("delivery_boundary"))
    strategy = _as_mapping(contract.get("strategy_applicability_boundary"))
    rollback = _as_mapping(contract.get("rollback_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase4.delivery.v1",
            contract.get("contract_state") == RETURN_STATE,
            contract.get("task_id") == "IDS-V0_1-STAGE065-P4",
            contract.get("next_gate") == REVIEW_GATE,
            contract.get("delivery_evidence_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("delivery_evidence_is_not_business_fact") is True,
            delivery.get("control_scenario_count") == 6,
            delivery.get("chunk_jsonl_sample_count") == 6,
            delivery.get("unique_control_semantic_asset_record_count") == 4,
            delivery.get("control_traceability_field_count") == 6,
            delivery.get("control_traceability_reference_check_count") == 36,
            delivery.get("low_quality_control_record_count") == 6,
            delivery.get("human_confirmation_prompt_count") == 3,
            delivery.get("chunk_jsonl_samples_are_metadata_only") is True,
            delivery.get("coverage_report_is_control_only") is True,
            delivery.get("actual_chunk_jsonl_written") is False,
            strategy.get("fixed_control_scenarios_only") is True,
            strategy.get(
                "long_document_cross_page_table_engineering_procedure_parameter_table_and_citation_page_require_human_review"
            )
            is True,
            strategy.get("actual_production_acceptance_claim_allowed") is False,
            failures.get("failure_state_count") == 11,
            failures.get("automatic_business_write_allowed") is False,
            rollback.get("return_to") == P3_RETURN_STATE,
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase3.controlled_scenarios.v1",
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report.get("next_gate") == "IDS-STAGE065-P4-GATE",
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("all_taskpack_special_scenarios_covered") is True,
            report.get("phase2_shape_preserved") is True,
            report.get("unique_control_semantic_asset_record_count") == 4,
            report.get("control_traceability_field_count") == 6,
            report.get("control_traceability_reference_check_count") == 36,
            report.get("control_traceability_reference_shape_preserved") is True,
            report.get("control_duplicate_write_prohibition_asserted") is True,
            report.get("actual_input_request_count") == 0,
            report.get("actual_chunk_count") == 0,
            report.get("source_document_remains_authoritative") is True,
            _report_runtime_boundary_disabled(report),
        )
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    coverage = _as_mapping(report.get("coverage_report"))
    regression = _as_mapping(report.get("regression_test_results"))
    instructions = _as_mapping(report.get("regeneration_and_version_rollback_instructions"))
    prompts = report.get("human_confirmation_prompts_zh")
    low_quality = report.get("low_quality_chunk_list")
    return all(
        (
            report.get("schema_version")
            == "ids.stage065.engineering_semantic_asset_classification.phase4.delivery.v1",
            report.get("valid") is True,
            report.get("result")
            == "PASS_PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_RUNTIME_DISABLED",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_control_scenarios_reused_as_reference_only") is True,
            report.get("chunk_jsonl_sample_count") == 6,
            isinstance(report.get("chunk_jsonl_samples"), list),
            len(report.get("chunk_jsonl_samples")) == 6,
            coverage.get("control_coverage_complete") is True,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            coverage.get("unique_control_semantic_asset_record_count") == 4,
            isinstance(low_quality, list),
            len(low_quality) == 6,
            all(
                isinstance(item, Mapping)
                and item.get("human_handling_required") is True
                and item.get("control_metadata_only") is True
                and item.get("actual_low_quality_chunk_observed") is False
                for item in low_quality
            ),
            regression.get("control_regression_consistent") is True,
            regression.get("actual_quality_regression_performed") is False,
            isinstance(prompts, list),
            len(prompts) == 3,
            instructions.get("return_to") == P3_RETURN_STATE,
            instructions.get("in_memory_control_replay_only") is True,
            instructions.get("actual_chunk_regeneration_performed") is False,
            instructions.get("actual_chunk_version_rollback_performed") is False,
            report.get("source_document_remains_authoritative") is True,
            report.get("delivery_evidence_can_become_business_fact_authority") is False,
            report.get("actual_chunk_jsonl_written") is False,
            report.get("actual_low_quality_chunk_observed") is False,
            _report_runtime_boundary_disabled(report),
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
    phase1_inputs = _as_mapping(phase1.get("reference_only_semantic_asset_classification_input_contract"))
    phase1_outputs = _as_mapping(phase1.get("future_semantic_asset_classification_output_contract"))
    phase1_catalog = _as_mapping(phase1.get("engineering_semantic_asset_type_catalog"))
    phase2_inputs = _as_mapping(phase2.get("reference_only_semantic_asset_classification_input_control_contract"))
    phase2_records = _as_mapping(phase2.get("control_semantic_asset_classification_record_contract"))
    phase2_protected = _as_mapping(phase2.get("protected_semantic_boundary_control_contract"))
    phase2_traceability = _as_mapping(phase2.get("traceability_control_contract"))
    phase3_inputs = _as_mapping(phase3.get("scenario_input_boundary"))
    phase4_delivery = _as_mapping(phase4.get("delivery_boundary"))
    phase4_rollback = _as_mapping(phase4.get("rollback_contract"))
    return {
        "phase1_reference_only_input_field_count": phase1_inputs.get("field_count"),
        "phase1_future_output_field_count": phase1_outputs.get("field_count"),
        "phase1_engineering_semantic_asset_type_count": phase1_catalog.get("asset_type_count"),
        "phase2_control_request_count": phase2_inputs.get("control_request_count"),
        "phase2_control_record_count": phase2_records.get("control_record_count"),
        "protected_semantic_asset_type_count": phase2_protected.get("protected_semantic_asset_type_count"),
        "traceability_field_count": phase2_traceability.get("traceability_field_count"),
        "phase2_control_traceability_reference_count": phase2_traceability.get("control_traceability_reference_count"),
        "scenario_count": scenario_report.get("scenario_count"),
        "explicit_disposition_count": scenario_report.get("explicit_disposition_count"),
        "silent_drop_count": scenario_report.get("silent_drop_count"),
        "human_handling_required_count": scenario_report.get("human_handling_required_count"),
        "scenario_traceability_reference_check_count": scenario_report.get(
            "control_traceability_reference_check_count"
        ),
        "metadata_only_jsonl_sample_count": delivery_report.get("chunk_jsonl_sample_count"),
        "unique_control_semantic_asset_record_count": phase4_delivery.get(
            "unique_control_semantic_asset_record_count"
        ),
        "low_quality_control_record_count": phase4_delivery.get("low_quality_control_record_count"),
        "human_confirmation_prompt_count": phase4_delivery.get("human_confirmation_prompt_count"),
        "phase3_contract_scenario_count": phase3_inputs.get("scenario_count"),
        "phase4_return_to": phase4_rollback.get("return_to"),
    }


def _single_authority_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase1_authority = _as_mapping(phase1.get("source_authority"))
    phase2_authority = _as_mapping(phase2.get("source_authority"))
    phase3_authority = _as_mapping(phase3.get("source_authority"))
    phase4_authority = _as_mapping(phase4.get("source_authority"))
    return all(
        (
            phase1_authority.get("second_authoritative_source_created") is False,
            phase2_authority.get("second_authoritative_source_created") is False,
            phase3_authority.get("second_authoritative_source_created") is False,
            phase4_authority.get("second_authoritative_source_created") is False,
            phase3_authority.get("source_document_remains_authoritative") is True,
            phase4_authority.get("source_document_remains_authoritative") is True,
            scenario_report.get("source_document_remains_authoritative") is True,
            scenario_report.get("semantic_asset_control_record_can_become_business_fact_authority")
            is False,
            delivery_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("delivery_evidence_can_become_business_fact_authority")
            is False,
        )
    )


def _semantic_asset_classification_shape_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
) -> bool:
    phase1_inputs = _as_mapping(phase1.get("reference_only_semantic_asset_classification_input_contract"))
    phase1_outputs = _as_mapping(phase1.get("future_semantic_asset_classification_output_contract"))
    phase1_catalog = _as_mapping(phase1.get("engineering_semantic_asset_type_catalog"))
    phase2_inputs = _as_mapping(phase2.get("reference_only_semantic_asset_classification_input_control_contract"))
    phase2_records = _as_mapping(phase2.get("control_semantic_asset_classification_record_contract"))
    phase3_inputs = _as_mapping(phase3.get("scenario_input_boundary"))
    return all(
        (
            phase1_inputs.get("field_count") == 12,
            phase1_outputs.get("field_count") == 16,
            phase1_catalog.get("asset_type_count") == 7,
            phase2_inputs.get("control_request_count") == 7,
            phase2_records.get("control_record_count") == 7,
            phase3_inputs.get("scenario_count") == 6,
            scenario_report.get("unique_control_semantic_asset_record_count") == 4,
            scenario_report.get("control_traceability_field_count") == 6,
        )
    )


def _human_handling_boundary_preserved(
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase2_markers = _as_mapping(phase2.get("low_confidence_control_marker_contract"))
    phase3_validation = _as_mapping(phase3.get("scenario_validation"))
    low_quality = delivery_report.get("low_quality_chunk_list")
    return all(
        (
            phase2_markers.get("all_control_records_require_business_line_human_review") is True,
            phase3_validation.get("business_line_human_handling_required") is True,
            scenario_report.get("human_handling_required_count") == 6,
            scenario_report.get("silent_drop_count") == 0,
            isinstance(low_quality, list),
            len(low_quality) == 6,
            all(
                isinstance(item, Mapping)
                and item.get("human_handling_required") is True
                for item in low_quality
            ),
        )
    )


def _delivery_boundary_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    delivery = _as_mapping(phase4.get("delivery_boundary"))
    coverage = _as_mapping(delivery_report.get("coverage_report"))
    regression = _as_mapping(delivery_report.get("regression_test_results"))
    return all(
        (
            delivery.get("chunk_jsonl_samples_are_metadata_only") is True,
            delivery.get("coverage_report_is_control_only") is True,
            delivery.get("low_quality_list_is_not_actual_quality_measurement") is True,
            delivery.get("regression_result_is_not_actual_quality_regression") is True,
            delivery_report.get("actual_chunk_jsonl_written") is False,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            regression.get("actual_quality_regression_performed") is False,
        )
    )


def _rollback_chain_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    rollback = _as_mapping(phase4.get("rollback_contract"))
    instructions = _as_mapping(delivery_report.get("regeneration_and_version_rollback_instructions"))
    return all(
        (
            rollback.get("return_to") == P3_RETURN_STATE,
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            instructions.get("return_to") == P3_RETURN_STATE,
            instructions.get("in_memory_control_replay_only") is True,
            instructions.get("actual_chunk_regeneration_performed") is False,
            instructions.get("actual_chunk_version_rollback_performed") is False,
        )
    )


def _future_stage_ownership_preserved(
    phase1: Mapping[str, Any], phase4: Mapping[str, Any]
) -> bool:
    phase1_future = _as_mapping(phase1.get("future_stage_interface_boundary"))
    phase4_ownership = _as_mapping(phase4.get("ownership_boundary"))
    return all(
        (
            phase1_future.get("semantic_asset_classification_owner") == "STAGE-065",
            phase1_future.get("coverage_calculation_owner") == "STAGE-066",
            phase1_future.get("quality_regression_execution_owner") == "STAGE-067",
            phase1_future.get("quality_degradation_execution_owner") == "STAGE-068",
            phase4_ownership.get("engineering_semantic_asset_classification_control_owner")
            == "STAGE-065",
            phase4_ownership.get("coverage_calculation_owner") == "STAGE-066",
            phase4_ownership.get("quality_regression_owner") == "STAGE-067",
            phase4_ownership.get("quality_degradation_owner") == "STAGE-068",
        )
    )


def _contracts_runtime_disabled(*values: Mapping[str, Any]) -> bool:
    for value in values:
        boundary = _as_mapping(value.get("runtime_boundary"))
        if boundary:
            if not _runtime_boundary_disabled(boundary):
                return False
        elif not _report_runtime_boundary_disabled(value):
            return False
    return True


def _runtime_boundary_disabled(boundary: Mapping[str, Any]) -> bool:
    return all(boundary.get(field) is False for field in RUNTIME_ACTION_FIELDS)


def _report_runtime_boundary_disabled(report: Mapping[str, Any]) -> bool:
    return all(report.get(field) is False for field in RUNTIME_ACTION_FIELDS)


def _review_runtime_actions_disabled(report: Mapping[str, Any]) -> bool:
    return all(
        report.get(field) is False
        for field in (
            *RUNTIME_ACTION_FIELDS,
            "actual_chunk_jsonl_written",
            "actual_document_coverage_calculated",
            "actual_chunk_coverage_calculated",
            "actual_low_quality_chunk_observed",
            "actual_quality_measurement_performed",
            "actual_quality_regression_performed",
            "actual_chunk_regeneration_performed",
            "actual_chunk_version_rollback_performed",
            "stage066_started",
            "stage066_entry_allowed",
            "github_upload_performed",
            "push_performed",
        )
    )


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
