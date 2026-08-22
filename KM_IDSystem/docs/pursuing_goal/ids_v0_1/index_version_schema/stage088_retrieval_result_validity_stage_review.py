"""Stage088 的纯内存整阶段机械复审，不读取真实资料或启动 Stage089。"""

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
    / "STAGE-088_检索结果有效性门禁.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-089_证据账本Schema.md"
)
P1_CONTRACT = BASE / "stage088_retrieval_result_validity_contract.json"
P2_CONTRACT = BASE / "stage088_retrieval_result_validity_slice_contract.json"
P3_CONTRACT = BASE / "stage088_retrieval_result_validity_scenarios_contract.json"
P4_CONTRACT = BASE / "stage088_retrieval_result_validity_delivery_contract.json"

SCHEMA_VERSION = "ids.stage088.retrieval_result_validity.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE088-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-088"
PASS_RESULT = "PASS_REVIEWED_RETRIEVAL_RESULT_VALIDITY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_RETRIEVAL_RESULT_VALIDITY_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE088-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE089-P1-GATE"
RETURN_STATE = "PASS_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P1_SHAPES = (
    ("query_record_field_count", "future_query_record_fields", 9),
    ("filter_record_field_count", "future_filter_record_fields", 7),
    ("candidate_record_field_count", "future_candidate_record_fields", 10),
    ("selected_record_field_count", "future_selected_record_fields", 10),
    ("score_record_field_count", "future_score_record_fields", 7),
    (
        "active_index_version_record_field_count",
        "future_active_index_version_record_fields",
        7,
    ),
    (
        "retrieval_trace_record_field_count",
        "future_retrieval_trace_record_fields",
        14,
    ),
    (
        "validity_gate_record_field_count",
        "future_validity_gate_record_fields",
        16,
    ),
)
P2_FIELD_COUNTS = {
    "query_projection_field_count": 9,
    "metadata_filter_projection_field_count": 8,
    "active_index_version_projection_field_count": 7,
    "candidate_projection_field_count": 10,
    "score_projection_field_count": 7,
    "selected_projection_field_count": 10,
    "retrieval_trace_projection_field_count": 14,
    "result_validity_gate_projection_field_count": 16,
    "future_integration_projection_field_count": 7,
}
P2_REPORT_COUNTS = (
    "query_control_projection_count",
    "metadata_filter_control_projection_count",
    "active_index_version_control_projection_count",
    "candidate_control_projection_count",
    "score_control_projection_count",
    "selected_control_projection_count",
    "retrieval_trace_control_projection_count",
    "result_validity_gate_control_projection_count",
    "future_integration_control_projection_count",
)
EXPECTED_CONTROLLED_REPLAY = {
    "phase1_query_field_count": 9,
    "phase1_filter_field_count": 7,
    "phase1_candidate_field_count": 10,
    "phase1_selected_field_count": 10,
    "phase1_score_field_count": 7,
    "phase1_active_index_version_field_count": 7,
    "phase1_retrieval_trace_field_count": 14,
    "phase1_validity_gate_field_count": 16,
    "phase1_failure_state_count": 28,
    "phase2_control_request_count": 6,
    "phase2_projection_set_count": 9,
    "phase2_control_field_check_count": 528,
    "phase2_failure_state_count": 34,
    "phase3_scenario_count": 8,
    "phase3_scenario_field_count": 33,
    "phase3_scenario_field_check_count": 264,
    "phase3_human_handling_required_count": 8,
    "phase3_failure_state_count": 16,
    "phase4_retrieval_sample_count": 8,
    "phase4_trace_log_count": 8,
    "phase4_filter_result_count": 8,
    "phase4_validity_test_report_count": 8,
    "phase4_evidence_gap_count": 8,
    "phase4_parameter_rollback_instruction_count": 4,
    "phase4_chinese_feedback_count": 4,
    "phase4_delivery_field_check_count": 572,
    "phase4_failure_state_count": 20,
}
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "postgresql_fts_index_build_performed",
    "pgvector_index_build_performed",
    "embedding_generation_performed",
    "keyword_retrieval_query_performed",
    "vector_retrieval_query_performed",
    "material_grade_lookup_performed",
    "equipment_model_lookup_performed",
    "standard_number_lookup_performed",
    "semantic_similarity_calculation_performed",
    "metadata_filter_evaluation_performed",
    "hybrid_ranking_performed",
    "top_k_selection_performed",
    "retrieval_trace_read_performed",
    "retrieval_trace_write_performed",
    "result_validity_evaluation_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
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
    "retrieval_sample_record_write_performed",
    "trace_log_record_write_performed",
    "filter_result_record_write_performed",
    "validity_test_report_write_performed",
    "evidence_gap_record_write_performed",
    "retrieval_parameter_rollback_performed",
    "chinese_feedback_published",
)


def build_retrieval_result_validity_stage088_review_report(
    *,
    phase1_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_report_provider: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """只重放冻结 P1--P4 控制工件，返回失败关闭的 Review 结论。"""

    phase1 = _provider_result(phase1_contract_provider or _default_phase1_contract)
    phase2_contract = _provider_result(
        phase2_contract_provider or _default_phase2_contract
    )
    phase3_contract = _provider_result(
        phase3_contract_provider or _default_phase3_contract
    )
    phase4_contract = _provider_result(
        phase4_contract_provider or _default_phase4_contract
    )
    phase2 = _provider_result(phase2_report_provider or _default_phase2_report)
    phase3 = _provider_result(phase3_report_provider or _default_phase3_report)
    phase4 = _provider_result(phase4_report_provider or _default_phase4_report)

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2_contract)
        and _phase2_report_valid(phase2),
        "P3": _phase3_contract_valid(phase3_contract)
        and _phase3_report_valid(phase3),
        "P4": _phase4_contract_valid(phase4_contract)
        and _phase4_report_valid(phase4),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    fixed_shapes = controlled_replay == EXPECTED_CONTROLLED_REPLAY
    authority_preserved = _single_authority_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    failure_and_rollback_preserved = _failure_and_rollback_boundary(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    delivery_and_whitebox_preserved = _delivery_and_whitebox_boundary(
        phase3, phase4_contract, phase4
    )
    nested_runtime_closed = _nested_runtime_closed(
        phase1,
        phase2_contract,
        phase3_contract,
        phase4_contract,
        phase2,
        phase3,
        phase4,
    )
    next_stage_available_but_not_started = _next_stage_available_but_not_started(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    runtime_flags = _runtime_closed_flags()
    review_valid = (
        TASKPACK.is_file()
        and NEXT_TASKPACK.is_file()
        and all(phase_results.values())
        and fixed_shapes
        and authority_preserved
        and failure_and_rollback_preserved
        and delivery_and_whitebox_preserved
        and nested_runtime_closed
        and next_stage_available_but_not_started
        and all(value is False for value in runtime_flags.values())
    )
    failure_reasons = _failure_reasons(
        phase_results,
        fixed_shapes,
        authority_preserved,
        failure_and_rollback_preserved,
        delivery_and_whitebox_preserved,
        nested_runtime_closed,
        next_stage_available_but_not_started,
    )
    next_gate = NEXT_GATE if review_valid else REVIEW_GATE
    review_invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "fixed_control_shapes_preserved": fixed_shapes,
        "single_authority_boundary_preserved": authority_preserved,
        "failure_stop_and_rollback_boundaries_preserved": (
            failure_and_rollback_preserved
        ),
        "delivery_and_whitebox_boundaries_preserved": (
            delivery_and_whitebox_preserved
        ),
        "runtime_actions_disabled": nested_runtime_closed
        and all(value is False for value in runtime_flags.values()),
        "next_stage_taskpack_available_but_not_started": (
            next_stage_available_but_not_started
        ),
        "stage089_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": (
            "FROZEN_STAGE088_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY"
        ),
        "reviewed_phase_ids": [
            "IDS-STAGE088-P1",
            "IDS-STAGE088-P2",
            "IDS-STAGE088-P3",
            "IDS-STAGE088-P4",
        ],
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": review_invariants,
        "review_valid": review_valid,
        "failure_reasons": failure_reasons,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": next_gate,
        "source_document_remains_authoritative": authority_preserved,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "business_line_whitebox_human_review_remains_authoritative": (
            delivery_and_whitebox_preserved
        ),
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage088_started": True,
        "stage089_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "automatic_business_recommendation_allowed": False,
        "actual_input_request_count": 0,
        "actual_keyword_retrieval_query_count": 0,
        "actual_vector_retrieval_query_count": 0,
        "actual_embedding_generation_count": 0,
        "actual_metadata_filter_evaluation_count": 0,
        "actual_hybrid_ranking_count": 0,
        "actual_top_k_selection_count": 0,
        "actual_retrieval_trace_access_count": 0,
        "actual_result_validity_evaluation_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_retrieval_sample_record_write_count": 0,
        "actual_trace_log_record_write_count": 0,
        "actual_filter_result_record_write_count": 0,
        "actual_validity_test_report_write_count": 0,
        "actual_evidence_gap_record_write_count": 0,
        "actual_retrieval_parameter_rollback_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
        "rollback": {
            "scope": "STAGE088_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
            "return_to": RETURN_STATE,
            "preserve_phase1_contract": True,
            "preserve_phase2_control_slice": True,
            "preserve_phase3_controlled_scenarios": True,
            "preserve_phase4_delivery_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        **runtime_flags,
    }


def _default_phase1_contract() -> Mapping[str, Any]:
    return _read_json(P1_CONTRACT)


def _default_phase2_contract() -> Mapping[str, Any]:
    return _read_json(P2_CONTRACT)


def _default_phase3_contract() -> Mapping[str, Any]:
    return _read_json(P3_CONTRACT)


def _default_phase4_contract() -> Mapping[str, Any]:
    return _read_json(P4_CONTRACT)


def _default_phase2_report() -> Mapping[str, Any]:
    module = _load_module(
        "stage088_review_phase2", "stage088_retrieval_result_validity_control_slice.py"
    )
    if module is None:
        return {}
    return module.execute_retrieval_result_validity_control_slice(
        module.build_control_input()
    )


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module(
        "stage088_review_phase3",
        "stage088_retrieval_result_validity_controlled_scenarios.py",
    )
    return {} if module is None else module.build_retrieval_result_validity_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module(
        "stage088_review_phase4", "stage088_retrieval_result_validity_delivery.py"
    )
    return (
        {}
        if module is None
        else module.build_retrieval_result_validity_phase4_delivery_report()
    )


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    shape = _mapping(contract.get("retrieval_result_validity_gate_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    required_flags = (
        "keyword_retrieval_baseline_required",
        "vector_retrieval_baseline_required",
        "vector_similarity_only_prohibited",
        "metadata_filter_contract_required",
        "all_six_metadata_filter_dimensions_required",
        "hybrid_ranking_contract_required",
        "ranking_policy_and_score_explanation_required",
        "active_index_version_record_contract_required",
        "retrieval_trace_contract_required",
        "requested_top_k_must_be_declared",
        "candidate_and_selected_chunks_must_reference_same_active_index_version",
        "candidate_and_selected_chunks_must_reference_metadata_filter_contract",
        "retrieval_trace_must_reference_query_filter_candidate_selected_score_and_active_index_version",
        "retrieval_trace_must_reference_evidence_ledger",
        "validity_gate_requires_complete_control_chain",
        "validity_gate_requires_human_whitebox_review_before_business_use",
        "system_output_alone_may_not_be_treated_as_valid_result",
        "all_values_are_control_labels_only",
    )
    expected_boundary = {
        "stage087_review_evidence_declared": True,
        "stage088_started": True,
        "stage088_entry_authorized": True,
        "phase1_started": True,
        "phase2_started": False,
        "phase3_started": False,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "stage089_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }
    return (
        contract.get("schema_version")
        == "ids.stage088.retrieval_result_validity_gate_contract.phase1.v1"
        and contract.get("stage") == "STAGE-088"
        and contract.get("phase") == "IDS-STAGE088-P1"
        and contract.get("task_id") == "IDS-V0_1-STAGE088-P1"
        and contract.get("contract_state")
        == "PHASE1_RETRIEVAL_RESULT_VALIDITY_GATE_CONTRACT_RUNTIME_DISABLED"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and all(
            shape.get(count_key) == expected
            and isinstance(shape.get(field_key), list)
            and len(shape[field_key]) == expected
            for count_key, field_key, expected in P1_SHAPES
        )
        and all(shape.get(flag) is True for flag in required_flags)
        and _failure_contract_valid(contract, 28)
        and _runtime_boundary_closed(contract)
        and all(boundary.get(key) is value for key, value in expected_boundary.items())
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    projection = _mapping(contract.get("control_projection_contract"))
    required_flags = (
        "keyword_retrieval_baseline_required",
        "vector_retrieval_baseline_required",
        "vector_similarity_only_prohibited",
        "system_output_only_acceptance_prohibited",
        "all_six_metadata_filter_dimensions_required",
        "metadata_status_filter_required",
        "active_index_version_contract_required",
        "candidate_selected_and_trace_active_index_version_chain_required",
        "candidate_selected_and_trace_metadata_filter_chain_required",
        "candidate_selected_score_and_explanation_chain_required",
        "trace_query_filter_candidate_selected_score_and_evidence_ledger_chain_required",
        "result_validity_gate_complete_control_chain_required",
        "result_validity_gate_human_whitebox_review_required",
    )
    return (
        contract.get("schema_version") == "ids.stage088.retrieval_result_validity.phase2.v1"
        and contract.get("stage") == "STAGE-088"
        and contract.get("phase") == "IDS-STAGE088-P2"
        and contract.get("task_id") == "IDS-V0_1-STAGE088-P2"
        and contract.get("contract_state")
        == "PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE_RUNTIME_DISABLED"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and projection.get("each_projection_count") == 6
        and projection.get("control_projection_field_total") == 528
        and all(projection.get(key) == value for key, value in P2_FIELD_COUNTS.items())
        and all(projection.get(flag) is True for flag in required_flags)
        and _failure_contract_valid(contract, 34)
        and _runtime_boundary_closed(contract)
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return (
        contract.get("schema_version") == "ids.stage088.retrieval_result_validity.phase3.v1"
        and contract.get("stage") == "STAGE-088"
        and contract.get("phase") == "IDS-STAGE088-P3"
        and contract.get("task_id") == "IDS-V0_1-STAGE088-P3"
        and contract.get("contract_state")
        == "PHASE3_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and _source_authority_closed(_mapping(contract.get("source_authority")))
        and _failure_contract_valid(contract, 16)
        and _runtime_boundary_closed(contract)
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    source = _mapping(contract.get("source_authority"))
    expected_shapes = (
        ("retrieval_sample_control_record_count", 8, "retrieval_sample_field_count", 14),
        ("trace_log_control_record_count", 8, "trace_log_field_count", 14),
        ("filter_result_control_record_count", 8, "filter_result_field_count", 10),
        ("validity_test_report_control_record_count", 8, "validity_test_report_field_count", 15),
        ("evidence_gap_control_record_count", 8, "evidence_gap_field_count", 14),
        (
            "parameter_rollback_instruction_count",
            4,
            "parameter_rollback_instruction_field_count",
            9,
        ),
    )
    return (
        contract.get("schema_version")
        == "ids.stage088.retrieval_result_validity.phase4.delivery.v1"
        and contract.get("stage") == "STAGE-088"
        and contract.get("phase") == "IDS-STAGE088-P4"
        and contract.get("task_id") == "IDS-V0_1-STAGE088-P4"
        and contract.get("contract_state")
        == "PHASE4_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and _source_authority_closed(source)
        and source.get("source_document_remains_authoritative") is True
        and source.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and delivery.get("delivery_executable") is True
        and delivery.get("execution_ready") is False
        and delivery.get("metadata_only") is True
        and delivery.get("validity_gate_control_reference_preserved") is True
        and delivery.get("delivery_field_check_count") == 572
        and delivery.get("chinese_feedback_count") == 4
        and all(
            delivery.get(count_key) == count
            and delivery.get(field_key) == field_count
            for count_key, count, field_key, field_count in expected_shapes
        )
        and _phase4_failure_contract_valid(contract)
        and _runtime_boundary_closed(contract)
    )


def _phase2_report_valid(report: Mapping[str, Any]) -> bool:
    required_flags = (
        "all_keyword_baselines_declared",
        "all_vector_baselines_declared",
        "all_vector_similarity_only_routes_rejected",
        "all_six_metadata_filter_dimensions_covered",
        "all_result_validity_gate_reference_chains_match",
        "all_result_validity_gates_pending_human_whitebox_review",
    )
    return (
        report.get("schema_version") == "ids.stage088.retrieval_result_validity.phase2.v1"
        and report.get("record_kind")
        == "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY"
        and report.get("execution_state")
        == "COMPLETED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE"
        and report.get("input_accepted") is True
        and report.get("failure_state") is None
        and all(report.get(key) == 6 for key in P2_REPORT_COUNTS)
        and all(report.get(key) is True for key in required_flags)
        and report.get("persistent_record_created") is False
        and _runtime_report_closed(report)
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    required_flags = (
        "all_control_references_opaque",
        "all_result_validity_states_not_evaluated",
        "all_validity_gates_pending_human_whitebox",
        "all_business_line_handling_required",
        "keyword_and_domain_coverage_preserved",
        "six_dimension_filter_combination_preserved",
        "top_k_ranking_and_validity_preserved",
        "old_index_trace_version_preserved",
        "result_validity_gate_chain_preserved",
    )
    return (
        report.get("schema_version") == "ids.stage088.retrieval_result_validity.phase3.v1"
        and report.get("record_kind")
        == "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_SCENARIOS"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("next_gate") == "IDS-STAGE088-P4-GATE"
        and report.get("scenario_count") == 8
        and report.get("scenario_field_count") == 33
        and report.get("scenario_field_check_count") == 264
        and report.get("passed_scenario_count") == 8
        and report.get("human_handling_required_count") == 8
        and all(report.get(flag) is True for flag in required_flags)
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_started") is False
        and report.get("stage089_started") is False
        and _runtime_report_closed(report)
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    groups = (
        ("retrieval_sample_control_record_count", "retrieval_sample_control_records", 8),
        ("trace_log_control_record_count", "trace_log_control_records", 8),
        ("filter_result_control_record_count", "filter_result_control_records", 8),
        (
            "validity_test_report_control_record_count",
            "validity_test_report_control_records",
            8,
        ),
        ("evidence_gap_control_record_count", "evidence_gap_control_records", 8),
    )
    validity_records = report.get("validity_test_report_control_records")
    return (
        report.get("schema_version")
        == "ids.stage088.retrieval_result_validity.phase4.delivery.v1"
        and report.get("record_kind")
        == "RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_REPORT"
        and report.get("valid") is True
        and report.get("result")
        == "PASS_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
        and report.get("failure_state") is None
        and report.get("next_gate") == REVIEW_GATE
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("all_delivery_references_control_only") is True
        and report.get("delivery_field_check_count") == 572
        and all(
            report.get(count_key) == expected
            and isinstance(report.get(record_key), list)
            and len(report[record_key]) == expected
            for count_key, record_key, expected in groups
        )
        and report.get("parameter_rollback_instruction_count") == 4
        and report.get("chinese_feedback") is not None
        and len(report["chinese_feedback"]) == 4
        and isinstance(validity_records, list)
        and all(
            record.get("observed_result_validity_state")
            == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
            and ":control:stage088-p2:" in str(record.get("validity_gate_ref", ""))
            for record in validity_records
        )
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_completed") is True
        and report.get("phase4_started") is True
        and report.get("whole_stage_review_performed") is False
        and report.get("stage088_review_started") is False
        and report.get("stage089_started") is False
        and _runtime_report_closed(report)
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> dict[str, int]:
    phase1_shape = _mapping(phase1.get("retrieval_result_validity_gate_contract"))
    phase2_shape = _mapping(phase2_contract.get("control_projection_contract"))
    phase3_failure = _mapping(phase3_contract.get("failure_and_stop_contract"))
    phase4_failure = _mapping(phase4_contract.get("failure_and_stop_contract"))
    return {
        "phase1_query_field_count": _integer(
            phase1_shape.get("query_record_field_count")
        ),
        "phase1_filter_field_count": _integer(
            phase1_shape.get("filter_record_field_count")
        ),
        "phase1_candidate_field_count": _integer(
            phase1_shape.get("candidate_record_field_count")
        ),
        "phase1_selected_field_count": _integer(
            phase1_shape.get("selected_record_field_count")
        ),
        "phase1_score_field_count": _integer(
            phase1_shape.get("score_record_field_count")
        ),
        "phase1_active_index_version_field_count": _integer(
            phase1_shape.get("active_index_version_record_field_count")
        ),
        "phase1_retrieval_trace_field_count": _integer(
            phase1_shape.get("retrieval_trace_record_field_count")
        ),
        "phase1_validity_gate_field_count": _integer(
            phase1_shape.get("validity_gate_record_field_count")
        ),
        "phase1_failure_state_count": _failure_count(phase1),
        "phase2_control_request_count": _integer(phase2_shape.get("each_projection_count")),
        "phase2_projection_set_count": len(P2_FIELD_COUNTS),
        "phase2_control_field_check_count": _integer(
            phase2_shape.get("control_projection_field_total")
        ),
        "phase2_failure_state_count": _failure_count(phase2_contract),
        "phase3_scenario_count": _integer(phase3.get("scenario_count")),
        "phase3_scenario_field_count": _integer(phase3.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _integer(
            phase3.get("scenario_field_check_count")
        ),
        "phase3_human_handling_required_count": _integer(
            phase3.get("human_handling_required_count")
        ),
        "phase3_failure_state_count": _integer(phase3_failure.get("failure_state_count")),
        "phase4_retrieval_sample_count": _integer(
            phase4.get("retrieval_sample_control_record_count")
        ),
        "phase4_trace_log_count": _integer(phase4.get("trace_log_control_record_count")),
        "phase4_filter_result_count": _integer(
            phase4.get("filter_result_control_record_count")
        ),
        "phase4_validity_test_report_count": _integer(
            phase4.get("validity_test_report_control_record_count")
        ),
        "phase4_evidence_gap_count": _integer(
            phase4.get("evidence_gap_control_record_count")
        ),
        "phase4_parameter_rollback_instruction_count": _integer(
            phase4.get("parameter_rollback_instruction_count")
        ),
        "phase4_chinese_feedback_count": _sequence_length(
            phase4.get("chinese_feedback")
        ),
        "phase4_delivery_field_check_count": _integer(
            phase4.get("delivery_field_check_count")
        ),
        "phase4_failure_state_count": _integer(phase4_failure.get("failure_state_count")),
    }


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        all(
            _source_authority_closed(_mapping(contract.get("source_authority")))
            for contract in (phase1, phase2_contract, phase3_contract, phase4_contract)
        )
        and phase3.get("source_document_remains_authoritative") is True
        and phase3.get("control_scenario_can_replace_source_document") is False
        and phase3.get("control_result_can_become_business_fact_authority") is False
        and phase4.get("source_document_remains_authoritative") is True
        and phase4.get("delivery_control_metadata_can_replace_source_document") is False
        and phase4.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
    )


def _failure_and_rollback_boundary(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        _failure_contract_valid(phase1, 28)
        and _failure_contract_valid(phase2_contract, 34)
        and _failure_contract_valid(phase3_contract, 16)
        and _phase4_failure_contract_valid(phase4_contract)
        and phase3.get("automatic_business_write_allowed") is False
        and phase3.get("automatic_business_recommendation_allowed") is False
        and phase3.get("automatic_parameter_write_allowed") is False
        and phase3.get("automatic_index_switch_allowed") is False
        and phase4.get("automatic_gap_resolution_allowed") is False
        and phase4.get("automatic_business_recommendation_allowed") is False
        and phase4.get("automatic_parameter_rollback_allowed") is False
        and phase4.get("automatic_index_switch_allowed") is False
        and _phase4_rollback_boundary(phase4)
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    source = _mapping(phase4_contract.get("source_authority"))
    return (
        phase3.get("all_result_validity_states_not_evaluated") is True
        and phase3.get("all_validity_gates_pending_human_whitebox") is True
        and phase3.get("all_business_line_handling_required") is True
        and phase3.get("business_line_whitebox_human_approval_recorded") is False
        and source.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and phase4.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and phase4.get("delivery_evidence_metadata_only") is True
        and phase4.get("all_delivery_references_control_only") is True
        and phase4.get("actual_retrieval_sample_written") is False
        and phase4.get("actual_trace_log_written") is False
        and phase4.get("actual_filter_result_written") is False
        and phase4.get("actual_validity_test_report_written") is False
        and phase4.get("actual_evidence_gap_record_written") is False
        and phase4.get("actual_retrieval_parameter_rollback_performed") is False
    )


def _nested_runtime_closed(*artifacts: Mapping[str, Any]) -> bool:
    return all(
        _runtime_boundary_closed(artifact)
        and _runtime_report_closed(artifact)
        for artifact in artifacts
    )


def _next_stage_available_but_not_started(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    boundaries = (
        _mapping(phase1.get("stage_and_phase_boundary")),
        _mapping(phase2_contract.get("stage_and_phase_boundary")),
        _mapping(phase3_contract.get("stage_and_phase_boundary")),
        _mapping(phase4_contract.get("stage_and_phase_boundary")),
    )
    return (
        NEXT_TASKPACK.is_file()
        and all(
            not boundary or boundary.get("stage089_started") is False
            for boundary in boundaries
        )
        and phase3.get("stage089_started") is False
        and phase4.get("stage089_started") is False
        and phase4.get("stage088_review_started") is False
    )


def _failure_reasons(
    phase_results: Mapping[str, bool],
    fixed_shapes: bool,
    authority_preserved: bool,
    failure_and_rollback_preserved: bool,
    delivery_and_whitebox_preserved: bool,
    nested_runtime_closed: bool,
    next_stage_available_but_not_started: bool,
) -> list[str]:
    reasons = [
        f"{phase}_CONTROL_ARTIFACT_INVALID"
        for phase, passed in phase_results.items()
        if passed is not True
    ]
    checks = (
        (fixed_shapes, "FIXED_CONTROL_SHAPE_MISMATCH"),
        (authority_preserved, "SECOND_AUTHORITY_OR_SOURCE_BOUNDARY_MISMATCH"),
        (failure_and_rollback_preserved, "FAILURE_OR_ROLLBACK_BOUNDARY_MISMATCH"),
        (delivery_and_whitebox_preserved, "DELIVERY_OR_WHITEBOX_BOUNDARY_MISMATCH"),
        (nested_runtime_closed, "RUNTIME_SIGNAL_DETECTED"),
        (next_stage_available_but_not_started, "NEXT_STAGE_BOUNDARY_MISMATCH"),
    )
    reasons.extend(reason for passed, reason in checks if passed is not True)
    return reasons


def _failure_contract_valid(contract: Mapping[str, Any], count: int) -> bool:
    failure = _mapping(contract.get("failure_and_stop_contract"))
    states = failure.get("declared_failure_states")
    return (
        failure.get("failure_state_count") == count
        and isinstance(states, list)
        and len(states) == count
        and all(isinstance(item, str) and item for item in states)
        and all(
            failure.get(key) is False
            for key in (
                "automatic_business_write_allowed",
                "automatic_query_execution_allowed",
                "automatic_embedding_generation_allowed",
                "automatic_metadata_filter_evaluation_allowed",
                "automatic_hybrid_ranking_allowed",
                "automatic_result_selection_allowed",
                "automatic_retrieval_trace_write_allowed",
                "automatic_result_validity_acceptance_allowed",
                "actual_failure_record_created",
            )
        )
    )


def _phase4_failure_contract_valid(contract: Mapping[str, Any]) -> bool:
    failure = _mapping(contract.get("failure_and_stop_contract"))
    states = failure.get("declared_failure_states")
    return (
        failure.get("failure_state_count") == 20
        and isinstance(states, list)
        and len(states) == 20
        and all(isinstance(item, str) and item for item in states)
        and failure.get("malformed_predecessor_fails_closed") is True
        and failure.get("runtime_signal_fails_closed") is True
        and failure.get("automatic_gap_resolution_allowed") is False
        and failure.get("automatic_business_recommendation_allowed") is False
        and failure.get("automatic_parameter_rollback_allowed") is False
        and failure.get("automatic_index_switch_allowed") is False
        and failure.get("whole_stage_review_must_not_start") is True
    )


def _phase4_rollback_boundary(report: Mapping[str, Any]) -> bool:
    instructions = report.get("parameter_rollback_instruction_control_records")
    return (
        report.get("parameter_rollback_instruction_count") == 4
        and isinstance(instructions, list)
        and len(instructions) == 4
        and all(
            instruction.get("entry_precondition")
            == "VERSIONED_PARAMETER_CHANGE_AND_BUSINESS_LINE_WHITEBOX_APPROVAL_REQUIRED"
            and instruction.get("rollback_state")
            == "CONTROL_NO_LIVE_RETRIEVAL_PARAMETER_TO_ROLLBACK"
            and instruction.get("actual_retrieval_parameter_rollback_performed")
            is False
            and instruction.get("human_handling_required") is True
            for instruction in instructions
            if isinstance(instruction, Mapping)
        )
        and all(isinstance(instruction, Mapping) for instruction in instructions)
    )


def _source_authority_closed(source: Mapping[str, Any]) -> bool:
    return bool(source) and all(
        source.get(key) is False
        for key in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        )
    ) and source.get("evidence_ledger_access_performed", False) is False


def _runtime_boundary_closed(artifact: Mapping[str, Any]) -> bool:
    boundary = _mapping(artifact.get("runtime_boundary"))
    return not boundary or all(_closed_runtime_value(value) for value in boundary.values())


def _runtime_report_closed(report: Mapping[str, Any]) -> bool:
    runtime_boundary = _mapping(report.get("runtime_boundary"))
    performed_fields_closed = all(
        value is False
        for key, value in report.items()
        if key.endswith("_performed")
    )
    actual_counts_zero = all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )
    gate_fields_closed = all(
        report.get(key) is False
        for key in (
            "github_upload_allowed",
            "push_allowed",
            "production_runtime_activation_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "agent_execution_performed",
            "ovh_deployment_performed",
        )
        if key in report
    )
    return (
        all(_closed_runtime_value(value) for value in runtime_boundary.values())
        and performed_fields_closed
        and actual_counts_zero
        and gate_fields_closed
    )


def _closed_runtime_value(value: Any) -> bool:
    return value is False or (
        isinstance(value, int) and not isinstance(value, bool) and value == 0
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _load_module(name: str, filename: str) -> Any | None:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        return _mapping(provider())
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return {}


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _integer(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _sequence_length(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _failure_count(contract: Mapping[str, Any]) -> int:
    return _integer(
        _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
    )
