"""Stage063 的只读整阶段复审，不读取真实文档或启动 Stage064。"""

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
    / "STAGE-063_章节感知切块.md"
)
P1_CONTRACT = BASE / "stage063_chapter_aware_chunking_contract.json"
P2_CONTRACT = BASE / "stage063_chapter_aware_chunking_slice_contract.json"
P3_CONTRACT = BASE / "stage063_chapter_aware_chunking_scenarios_contract.json"
P4_CONTRACT = BASE / "stage063_chapter_aware_chunking_delivery_contract.json"

SCHEMA_VERSION = "ids.stage063.chapter_aware_chunking.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE063-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-063"
PASS_RESULT = "PASS_REVIEWED_LOCAL_CHAPTER_AWARE_CHUNKING_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_CHAPTER_AWARE_CHUNKING_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE063-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE064-P1-GATE"
RETURN_STATE = "PHASE4_CHAPTER_AWARE_CHUNKING_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "long-document-chunking-control-human-review",
    "cross-page-parameter-table-control-human-handling",
    "engineering-procedure-step-control-human-review",
    "parameter-table-control-human-review",
    "page-reference-reverse-trace-control-human-confirmation",
    "duplicate-chunk-embedding-index-control-human-review",
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

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage063_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage063 P1--P4，仅返回控制事实、门禁与回退结论。"""

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
        "P3": _phase3_contract_valid(phase3) and _phase3_report_valid(scenario_report),
        "P4": _phase4_contract_valid(phase4) and _phase4_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2, phase3, phase4, scenario_report, delivery_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4, scenario_report, delivery_report
        ),
        "protected_semantic_and_traceability_boundary_preserved": (
            _protected_semantic_and_traceability_boundary_preserved(
                phase1, phase2, phase3, scenario_report, delivery_report
            )
        ),
        "six_special_scenarios_require_human_handling": (
            _human_handling_boundary_preserved(scenario_report, delivery_report)
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary_preserved(
            phase4, delivery_report
        ),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain_preserved(
            phase4, delivery_report
        ),
        "stage064_identity_and_version_remain_closed": _stage064_interface_remains_closed(
            phase1, phase2, phase3, phase4
        ),
        "runtime_actions_disabled": _contracts_runtime_disabled(
            phase1, phase2, phase3, phase4
        ),
        "stage064_not_started": True,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE063_TASKPACK_AND_STAGE063_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
                "Stage063 review document",
                "Stage063 review module",
                "Stage063 review focused tests",
                "Stage063 review governance projection",
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
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "stage063_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "stage064_started": False,
        "stage064_entry_allowed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_performed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        _report_actions_disabled(report)
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
        "stage063_chapter_aware_chunking_scenarios.py",
        "build_chapter_aware_chunking_phase3_report",
    )


def _load_phase4_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage063_chapter_aware_chunking_delivery.py",
        "build_chapter_aware_chunking_phase4_delivery_report",
    )


def _module_callable_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage063_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage063 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage063 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_chunking_input_contract"))
    outputs = _as_mapping(contract.get("future_chapter_aware_chunk_output_contract"))
    semantics = _as_mapping(contract.get("protected_semantic_boundary_contract"))
    traceability = _as_mapping(contract.get("traceability_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version") == "ids.stage063.chapter_aware_chunking.phase1.v1",
            contract.get("contract_state")
            == "PHASE1_CHAPTER_AWARE_CHUNKING_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE063-P1",
            contract.get("next_gate") == "IDS-STAGE063-P2-GATE",
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            authority.get("raw_metadata_content_access_allowed") is False,
            authority.get("live_source_read_performed") is False,
            inputs.get("field_count") == 8,
            inputs.get("actual_input_request_count") == 0,
            inputs.get("document_body_allowed") is False,
            outputs.get("field_count") == 14,
            outputs.get("actual_chunk_created") is False,
            outputs.get("actual_chunk_persisted") is False,
            semantics.get("protected_semantic_asset_type_count") == 3,
            semantics.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("actual_traceability_binding_count") == 0,
            failures.get("failure_state_count") == 8,
            failures.get("automatic_business_write_allowed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("reference_only_chunking_input_control_contract"))
    candidates = _as_mapping(contract.get("chapter_aware_chunk_candidate_contract"))
    traceability = _as_mapping(contract.get("traceability_control_contract"))
    protected = _as_mapping(contract.get("chapter_and_protected_surface_control_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version") == "ids.stage063.chapter_aware_chunking.phase2.v1",
            contract.get("contract_state")
            == "PHASE2_CHAPTER_AWARE_CHUNKING_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE063-P2",
            contract.get("next_gate") == "IDS-STAGE063-P3-GATE",
            contract.get("slice_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("second_authoritative_source_created") is False,
            authority.get("source_body_or_path_allowed") is False,
            authority.get("raw_metadata_content_access_allowed") is False,
            inputs.get("field_count") == 8,
            inputs.get("control_request_count") == 3,
            inputs.get("actual_input_request_count") == 0,
            candidates.get("field_count") == 14,
            candidates.get("control_candidate_count") == 3,
            candidates.get("actual_chunk_created") is False,
            candidates.get("actual_chunk_persisted") is False,
            protected.get("one_control_candidate_per_protected_semantic_asset_type") is True,
            protected.get("protected_surface_split_allowed") is False,
            traceability.get("traceability_field_count") == 6,
            traceability.get("control_traceability_reference_count") == 18,
            traceability.get("actual_traceability_binding_count") == 0,
            failures.get("failure_state_count") == 8,
            failures.get("unknown_or_reordered_control_input_rejected") is True,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _as_mapping(contract.get("scenario_input_boundary"))
    validation = _as_mapping(contract.get("scenario_validation"))
    duplicate = _as_mapping(contract.get("duplicate_embedding_and_index_boundary"))
    authority = _as_mapping(contract.get("source_authority"))
    ownership = _as_mapping(contract.get("ownership_boundary"))
    return all(
        (
            contract.get("schema_version")
            == "ids.stage063.chapter_aware_chunking.phase3.controlled_scenarios_contract.v1",
            contract.get("contract_state")
            == "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE063-P3",
            contract.get("next_gate") == "IDS-STAGE063-P4-GATE",
            contract.get("scenario_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("control_references_are_not_business_facts") is True,
            inputs.get("control_chunking_request_count") == 3,
            inputs.get("control_chapter_aware_chunk_candidate_count") == 3,
            inputs.get("scenario_count") == 6,
            inputs.get("traceability_field_count") == 6,
            inputs.get("control_traceability_reference_check_count") == 36,
            inputs.get("actual_chunk_count") == 0,
            validation.get("all_taskpack_special_scenarios_covered") is True,
            validation.get("explicit_disposition_count") == 6,
            validation.get("silent_drop_count") == 0,
            validation.get("human_handling_required_count") == 6,
            duplicate.get("control_duplicate_write_prohibition_asserted") is True,
            duplicate.get("embedding_or_index_write_performed") is False,
            ownership.get("business_line_whitebox_human_handling_required") is True,
            ownership.get("automatic_business_write_allowed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _as_mapping(contract.get("delivery_boundary"))
    strategy = _as_mapping(contract.get("strategy_applicability_boundary"))
    rollback = _as_mapping(contract.get("rollback_contract"))
    authority = _as_mapping(contract.get("source_authority"))
    return all(
        (
            contract.get("schema_version") == "ids.stage063.chapter_aware_chunking.phase4.delivery.v1",
            contract.get("contract_state") == RETURN_STATE,
            contract.get("task_id") == "IDS-V0_1-STAGE063-P4",
            contract.get("next_gate") == REVIEW_GATE,
            contract.get("delivery_evidence_executable") is True,
            contract.get("execution_ready") is False,
            authority.get("source_document_remains_authoritative") is True,
            authority.get("second_authoritative_source_created") is False,
            authority.get("delivery_evidence_is_not_business_fact") is True,
            delivery.get("control_scenario_count") == 6,
            delivery.get("chunk_jsonl_sample_count") == 6,
            delivery.get("control_traceability_field_count") == 6,
            delivery.get("control_traceability_reference_check_count") == 36,
            delivery.get("low_quality_control_record_count") == 6,
            delivery.get("human_confirmation_prompt_count") == 3,
            delivery.get("chunk_jsonl_samples_are_metadata_only") is True,
            delivery.get("actual_chunk_jsonl_written") is False,
            strategy.get("fixed_control_scenarios_only") is True,
            strategy.get("actual_production_acceptance_claim_allowed") is False,
            rollback.get("return_to")
            == "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary"))),
        )
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = report.get("scenario_results")
    if not isinstance(scenarios, list):
        return False
    return all(
        (
            report.get("schema_version")
            == "ids.stage063.chapter_aware_chunking.phase3.controlled_scenarios.v1",
            report.get("result")
            == "PASS_PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report.get("valid") is True,
            report.get("next_gate") == "IDS-STAGE063-P4-GATE",
            tuple(_as_mapping(item).get("scenario_id") for item in scenarios)
            == EXPECTED_SCENARIO_IDS,
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("control_traceability_reference_check_count") == 36,
            report.get("control_duplicate_write_prohibition_asserted") is True,
            all(_scenario_result_valid(item) for item in scenarios),
            _report_actions_disabled(report),
        )
    )


def _scenario_result_valid(item: object) -> bool:
    scenario = _as_mapping(item)
    return all(
        (
            scenario.get("control_reference_only") is True,
            scenario.get("control_scenario_metadata_only") is True,
            scenario.get("human_handling_required") is True,
            scenario.get("silent_drop") is False,
            scenario.get("expectation_met") is True,
            scenario.get("control_traceability_reference_preserved") is True,
            scenario.get("actual_source_traceability_binding_created") is False,
            scenario.get("actual_duplicate_chunk_detected") is False,
            scenario.get("duplicate_embedding_or_index_write_attempted") is False,
            _control_references_only(scenario, "referenced_chapter_aware_chunk_ref", "referenced_chunking_request_ref"),
            _traceability_references_only(scenario),
        )
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    samples = report.get("chunk_jsonl_samples")
    low_quality = report.get("low_quality_chunk_list")
    coverage = _as_mapping(report.get("coverage_report"))
    regression = _as_mapping(report.get("regression_test_results"))
    rollback = _as_mapping(report.get("regeneration_and_version_rollback_instructions"))
    prompts = report.get("human_confirmation_prompts_zh")
    if not isinstance(samples, list) or not isinstance(low_quality, list):
        return False
    return all(
        (
            report.get("schema_version") == "ids.stage063.chapter_aware_chunking.phase4.delivery.v1",
            report.get("result")
            == "PASS_PHASE4_CHAPTER_AWARE_CHUNKING_DELIVERY_RUNTIME_DISABLED",
            report.get("valid") is True,
            report.get("next_gate") == REVIEW_GATE,
            report.get("chunk_jsonl_sample_count") == 6,
            tuple(_as_mapping(item).get("scenario_id") for item in samples)
            == EXPECTED_SCENARIO_IDS,
            len(samples) == 6,
            all(_delivery_sample_valid(item) for item in samples),
            len(low_quality) == 6,
            all(_low_quality_record_valid(item) for item in low_quality),
            coverage.get("control_coverage_complete") is True,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            regression.get("control_regression_consistent") is True,
            regression.get("actual_quality_regression_performed") is False,
            rollback.get("return_to")
            == "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_chunk_regeneration_performed") is False,
            rollback.get("actual_chunk_version_rollback_performed") is False,
            isinstance(prompts, list) and len(prompts) == 3,
            _report_actions_disabled(report),
        )
    )


def _delivery_sample_valid(item: object) -> bool:
    sample = _as_mapping(item)
    return all(
        (
            sample.get("control_metadata_only") is True,
            sample.get("human_review_required") is True,
            sample.get("source_content_retained") is False,
            sample.get("actual_chunk_created") is False,
            sample.get("actual_chunk_persisted") is False,
            sample.get("actual_embedding_written") is False,
            sample.get("actual_index_written") is False,
            _control_references_only(sample, "chunk_ref", "chunking_request_ref"),
            _traceability_references_only(sample),
        )
    )


def _low_quality_record_valid(item: object) -> bool:
    record = _as_mapping(item)
    return all(
        (
            record.get("human_handling_required") is True,
            record.get("control_metadata_only") is True,
            record.get("actual_low_quality_chunk_observed") is False,
            record.get("actual_quality_measurement_performed") is False,
            record.get("automatic_quality_degradation_action_performed") is False,
            _control_references_only(record, "chunk_ref"),
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
    p1_inputs = _as_mapping(phase1.get("reference_only_chunking_input_contract"))
    p1_outputs = _as_mapping(phase1.get("future_chapter_aware_chunk_output_contract"))
    p2_inputs = _as_mapping(phase2.get("reference_only_chunking_input_control_contract"))
    p2_candidates = _as_mapping(phase2.get("chapter_aware_chunk_candidate_contract"))
    p3_inputs = _as_mapping(phase3.get("scenario_input_boundary"))
    p3_validation = _as_mapping(phase3.get("scenario_validation"))
    p4_delivery = _as_mapping(phase4.get("delivery_boundary"))
    return {
        "phase1_reference_only_input_field_count": p1_inputs.get("field_count"),
        "phase1_future_chunk_output_field_count": p1_outputs.get("field_count"),
        "phase2_control_request_count": p2_inputs.get("control_request_count"),
        "phase2_control_candidate_count": p2_candidates.get("control_candidate_count"),
        "phase2_control_traceability_reference_count": _as_mapping(
            phase2.get("traceability_control_contract")
        ).get("control_traceability_reference_count"),
        "phase3_controlled_scenario_count": p3_inputs.get("scenario_count"),
        "phase3_explicit_disposition_count": p3_validation.get("explicit_disposition_count"),
        "phase3_silent_drop_count": p3_validation.get("silent_drop_count"),
        "phase3_report_scenario_count": len(
            scenario_report.get("scenario_results", [])
            if isinstance(scenario_report.get("scenario_results"), list)
            else []
        ),
        "phase4_chunk_jsonl_sample_count": p4_delivery.get("chunk_jsonl_sample_count"),
        "phase4_low_quality_control_record_count": p4_delivery.get(
            "low_quality_control_record_count"
        ),
        "phase4_human_confirmation_prompt_count": p4_delivery.get(
            "human_confirmation_prompt_count"
        ),
        "phase4_report_chunk_jsonl_sample_count": delivery_report.get(
            "chunk_jsonl_sample_count"
        ),
        "phase4_return_to": _as_mapping(
            delivery_report.get("regeneration_and_version_rollback_instructions")
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
    p1_authority = _as_mapping(phase1.get("source_authority"))
    p2_authority = _as_mapping(phase2.get("source_authority"))
    p3_authority = _as_mapping(phase3.get("source_authority"))
    p4_authority = _as_mapping(phase4.get("source_authority"))
    return all(
        (
            p1_authority.get("second_authoritative_source_created") is False,
            p2_authority.get("second_authoritative_source_created") is False,
            p3_authority.get("source_document_remains_authoritative") is True,
            p3_authority.get("second_authoritative_source_created") is False,
            p4_authority.get("source_document_remains_authoritative") is True,
            p4_authority.get("second_authoritative_source_created") is False,
            scenario_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("source_document_remains_authoritative") is True,
            delivery_report.get("delivery_evidence_can_become_business_fact_authority")
            is False,
        )
    )


def _protected_semantic_and_traceability_boundary_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    scenario_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    p1_semantics = _as_mapping(phase1.get("protected_semantic_boundary_contract"))
    p1_traceability = _as_mapping(phase1.get("traceability_contract"))
    p2_traceability = _as_mapping(phase2.get("traceability_control_contract"))
    p3_inputs = _as_mapping(phase3.get("scenario_input_boundary"))
    scenarios = scenario_report.get("scenario_results")
    samples = delivery_report.get("chunk_jsonl_samples")
    return all(
        (
            p1_semantics.get("protected_semantic_asset_type_count") == 3,
            p1_semantics.get("protected_surface_split_allowed") is False,
            p1_traceability.get("traceability_field_count") == 6,
            p1_traceability.get("actual_traceability_binding_count") == 0,
            p2_traceability.get("traceability_field_count") == 6,
            p2_traceability.get("control_traceability_reference_count") == 18,
            p3_inputs.get("control_traceability_reference_check_count") == 36,
            isinstance(scenarios, list)
            and all(_traceability_references_only(_as_mapping(item)) for item in scenarios),
            isinstance(samples, list)
            and all(_traceability_references_only(_as_mapping(item)) for item in samples),
        )
    )


def _human_handling_boundary_preserved(
    scenario_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    scenarios = scenario_report.get("scenario_results")
    low_quality = delivery_report.get("low_quality_chunk_list")
    if not isinstance(scenarios, list) or not isinstance(low_quality, list):
        return False
    return all(
        (
            len(scenarios) == 6,
            len(low_quality) == 6,
            all(_scenario_result_valid(item) for item in scenarios),
            all(_low_quality_record_valid(item) for item in low_quality),
            any(
                _as_mapping(item).get("scenario_id")
                == "duplicate-chunk-embedding-index-control-human-review"
                and _as_mapping(item).get("deduplication_control_prohibition_asserted")
                is True
                for item in scenarios
            ),
        )
    )


def _delivery_boundary_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    delivery = _as_mapping(phase4.get("delivery_boundary"))
    samples = delivery_report.get("chunk_jsonl_samples")
    low_quality = delivery_report.get("low_quality_chunk_list")
    coverage = _as_mapping(delivery_report.get("coverage_report"))
    if not isinstance(samples, list) or not isinstance(low_quality, list):
        return False
    return all(
        (
            delivery.get("chunk_jsonl_sample_count") == 6,
            delivery.get("low_quality_control_record_count") == 6,
            delivery.get("actual_chunk_jsonl_written") is False,
            len(samples) == 6,
            len(low_quality) == 6,
            all(_delivery_sample_valid(item) for item in samples),
            all(_low_quality_record_valid(item) for item in low_quality),
            coverage.get("control_coverage_complete") is True,
            coverage.get("control_coverage_only") is True,
            coverage.get("actual_document_coverage_calculated") is False,
            coverage.get("actual_chunk_coverage_calculated") is False,
            delivery_report.get("actual_chunk_jsonl_written") is False,
            delivery_report.get("actual_low_quality_chunk_observed") is False,
        )
    )


def _rollback_chain_preserved(
    phase4: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    contract_rollback = _as_mapping(phase4.get("rollback_contract"))
    instructions = _as_mapping(
        delivery_report.get("regeneration_and_version_rollback_instructions")
    )
    return all(
        (
            contract_rollback.get("return_to")
            == "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract_rollback.get("in_memory_control_replay_only") is True,
            contract_rollback.get("actual_chunk_regeneration_performed") is False,
            contract_rollback.get("actual_chunk_version_rollback_performed") is False,
            contract_rollback.get("source_or_raw_data_change_allowed") is False,
            contract_rollback.get("database_or_persistent_state_change_allowed") is False,
            contract_rollback.get("github_or_ovh_change_allowed") is False,
            instructions.get("return_to")
            == "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            instructions.get("in_memory_control_replay_only") is True,
            instructions.get("actual_chunk_regeneration_performed") is False,
            instructions.get("actual_chunk_version_rollback_performed") is False,
            instructions.get("source_or_raw_data_change_allowed") is False,
            instructions.get("database_or_persistent_state_change_allowed") is False,
            instructions.get("github_or_ovh_change_allowed") is False,
        )
    )


def _stage064_interface_remains_closed(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    p1_owner = _as_mapping(phase1.get("ownership_boundary"))
    p2_owner = _as_mapping(phase2.get("ownership_boundary"))
    p3_owner = _as_mapping(phase3.get("ownership_boundary"))
    p4_owner = _as_mapping(phase4.get("ownership_boundary"))
    return all(
        (
            p1_owner.get("chunk_identity_and_version_owner") == "STAGE-064",
            p2_owner.get("chunk_identity_and_version_owner") == "STAGE-064",
            p3_owner.get("chunk_identity_and_version_owner") == "STAGE-064",
            p4_owner.get("chunk_identity_and_version_owner") == "STAGE-064",
            _as_mapping(phase2.get("future_stage_interface_boundary")).get(
                "chunk_identity_or_version_implementation_performed"
            )
            is False,
            p3_owner.get("actual_duplicate_detection_or_deduplication_implemented")
            is False,
            p4_owner.get("actual_chunk_regeneration_or_version_rollback_implemented")
            is False,
        )
    )


def _contracts_runtime_disabled(*contracts: Mapping[str, Any]) -> bool:
    return all(
        _runtime_boundary_disabled(_as_mapping(contract.get("runtime_boundary")))
        for contract in contracts
    )


def _runtime_boundary_disabled(boundary: Mapping[str, Any]) -> bool:
    return all(boundary.get(field, False) is False for field in RUNTIME_ACTION_FIELDS)


def _report_actions_disabled(report: Mapping[str, Any]) -> bool:
    return all(
        report.get(field, False) is False
        for field in (
            *RUNTIME_ACTION_FIELDS,
            "actual_chunk_regeneration_performed",
            "actual_chunk_version_rollback_performed",
            "batch_review_performed",
            "stage064_started",
            "stage064_entry_allowed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_performed",
            "push_allowed",
        )
    )


def _control_references_only(value: Mapping[str, Any], *fields: str) -> bool:
    return all(
        isinstance(value.get(field), str) and ":control:" in value[field]
        for field in fields
    )


def _traceability_references_only(value: Mapping[str, Any]) -> bool:
    return _control_references_only(value, *TRACEABILITY_FIELDS)


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
