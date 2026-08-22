"""Stage087 的纯内存整阶段机械复审，不读取真实资料或启动 Stage088。"""

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
    / "STAGE-087_检索轨迹.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-088_检索结果有效性门禁.md"
)
P1_CONTRACT = BASE / "stage087_retrieval_trace_contract.json"
P2_CONTRACT = BASE / "stage087_retrieval_trace_slice_contract.json"
P3_CONTRACT = BASE / "stage087_retrieval_trace_scenarios_contract.json"
P4_CONTRACT = BASE / "stage087_retrieval_trace_delivery_contract.json"

SCHEMA_VERSION = "ids.stage087.retrieval_trace.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE087-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-087"
PASS_RESULT = "PASS_REVIEWED_RETRIEVAL_TRACE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_RETRIEVAL_TRACE_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE087-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE088-P1-GATE"
RETURN_STATE = "PASS_RETRIEVAL_TRACE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_RETRIEVAL_TRACE_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_RETRIEVAL_TRACE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_RETRIEVAL_TRACE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage087-p2:"

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_query_field_count": 9,
    "phase1_filter_field_count": 7,
    "phase1_candidate_chunk_field_count": 10,
    "phase1_selected_chunk_field_count": 10,
    "phase1_score_field_count": 7,
    "phase1_active_index_version_field_count": 7,
    "phase1_retrieval_trace_field_count": 14,
    "phase1_failure_state_count": 21,
    "phase2_control_request_count": 6,
    "phase2_projection_set_count": 8,
    "phase2_control_field_check_count": 426,
    "phase2_failure_state_count": 27,
    "phase3_scenario_count": 8,
    "phase3_scenario_field_count": 31,
    "phase3_scenario_field_check_count": 248,
    "phase3_human_handling_required_count": 8,
    "phase4_retrieval_sample_count": 8,
    "phase4_trace_log_count": 8,
    "phase4_filter_result_count": 8,
    "phase4_validity_test_report_count": 8,
    "phase4_evidence_gap_count": 8,
    "phase4_parameter_rollback_instruction_count": 4,
    "phase4_delivery_field_check_count": 572,
    "phase4_chinese_feedback_count": 4,
    "phase4_failure_state_count": 20,
}

P1_SHAPE_SPECS = (
    ("query_record_field_count", "future_query_record_fields", 9),
    ("filter_record_field_count", "future_filter_record_fields", 7),
    (
        "candidate_chunk_record_field_count",
        "future_candidate_chunk_record_fields",
        10,
    ),
    (
        "selected_chunk_record_field_count",
        "future_selected_chunk_record_fields",
        10,
    ),
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
)
P2_PROJECTION_FIELDS = (
    ("query_control_projections", "query_control_projection_count", "QUERY_FIELDS"),
    (
        "metadata_filter_control_projections",
        "metadata_filter_control_projection_count",
        "METADATA_FILTER_PROJECTION_FIELDS",
    ),
    (
        "active_index_version_control_projections",
        "active_index_version_control_projection_count",
        "ACTIVE_INDEX_VERSION_FIELDS",
    ),
    (
        "candidate_chunk_control_projections",
        "candidate_chunk_control_projection_count",
        "CANDIDATE_CHUNK_FIELDS",
    ),
    ("score_control_projections", "score_control_projection_count", "SCORE_FIELDS"),
    (
        "selected_chunk_control_projections",
        "selected_chunk_control_projection_count",
        "SELECTED_CHUNK_FIELDS",
    ),
    (
        "retrieval_trace_control_projections",
        "retrieval_trace_control_projection_count",
        "RETRIEVAL_TRACE_FIELDS",
    ),
    (
        "future_integration_control_projections",
        "future_integration_control_projection_count",
        "FUTURE_INTEGRATION_FIELDS",
    ),
)
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
    "metadata_filter_evaluation_performed",
    "hybrid_ranking_performed",
    "top_k_selection_performed",
    "retrieval_trace_read_performed",
    "retrieval_trace_write_performed",
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


def build_retrieval_trace_stage087_review_report(
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
    phase2_module = _load_module(
        "stage087_review_phase2", "stage087_retrieval_trace_control_slice.py"
    )
    phase3_module = _load_module(
        "stage087_review_phase3", "stage087_retrieval_trace_controlled_scenarios.py"
    )
    phase4_module = _load_module(
        "stage087_review_phase4", "stage087_retrieval_trace_delivery.py"
    )
    phase2 = _provider_result(phase2_report_provider or _default_phase2_report)
    phase3 = _provider_result(phase3_report_provider or _default_phase3_report)
    phase4 = _provider_result(phase4_report_provider or _default_phase4_report)

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2_contract)
        and _phase2_report_valid(phase2_module, phase2),
        "P3": _phase3_contract_valid(phase3_contract)
        and _phase3_report_valid(phase3_module, phase3),
        "P4": _phase4_contract_valid(phase4_contract)
        and _phase4_report_valid(phase4_module, phase4),
    }
    controlled_replay = _controlled_replay(
        phase1, phase2_contract, phase2, phase3, phase4_contract, phase4
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
        and all(phase_results.values())
        and fixed_shapes
        and authority_preserved
        and failure_and_rollback_preserved
        and delivery_and_whitebox_preserved
        and nested_runtime_closed
        and next_stage_available_but_not_started
        and all(value is False for value in runtime_flags.values())
    )
    next_gate = NEXT_GATE if review_valid else REVIEW_GATE
    review_invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
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
        "stage088_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE087_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "reviewed_phase_ids": [
            "IDS-STAGE087-P1",
            "IDS-STAGE087-P2",
            "IDS-STAGE087-P3",
            "IDS-STAGE087-P4",
        ],
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": review_invariants,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": next_gate,
        "source_document_remains_authoritative": authority_preserved,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "business_line_whitebox_human_review_remains_authoritative": (
            _mapping(phase4_contract.get("source_authority")).get(
                "business_line_whitebox_human_review_remains_authoritative"
            )
            is True
        ),
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_completed": True,
        "stage087_started": True,
        "stage088_started": False,
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
            "scope": "STAGE087_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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
        "stage087_review_phase2_provider", "stage087_retrieval_trace_control_slice.py"
    )
    if module is None:
        return {}
    return module.execute_retrieval_trace_control_slice(module.build_control_input())


def _default_phase3_report() -> Mapping[str, Any]:
    module = _load_module(
        "stage087_review_phase3_provider",
        "stage087_retrieval_trace_controlled_scenarios.py",
    )
    return {} if module is None else module.build_retrieval_trace_phase3_report()


def _default_phase4_report() -> Mapping[str, Any]:
    module = _load_module(
        "stage087_review_phase4_provider", "stage087_retrieval_trace_delivery.py"
    )
    return {} if module is None else module.build_retrieval_trace_phase4_delivery_report()


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    shape = _mapping(contract.get("retrieval_trace_control_contract"))
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
        "all_values_are_control_labels_only",
    )
    return (
        contract.get("schema_version")
        == "ids.stage087.retrieval_trace_contract.phase1.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE087-P1"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-087"
        and contract.get("phase") == "IDS-STAGE087-P1"
        and contract.get("next_gate") == "IDS-STAGE087-P2-GATE"
        and _shapes_match(shape, P1_SHAPE_SPECS)
        and all(shape.get(field) is True for field in required_flags)
        and _nested_runtime_closed(shape)
        and _authority_closed(_mapping(contract.get("source_authority")))
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage086_review_evidence_declared") is True
        and boundary.get("stage087_started") is True
        and boundary.get("stage087_entry_authorized") is True
        and boundary.get("phase1_started") is True
        and all(
            boundary.get(field) is False
            for field in (
                "phase2_started",
                "phase3_started",
                "phase4_started",
                "whole_stage_review_performed",
                "stage088_started",
                "github_upload_allowed",
                "push_allowed",
            )
        )
        and _mapping(contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 21
        and _mapping(contract.get("rollback_contract")).get("return_to")
        == "PASS_REVIEWED_HYBRID_RANKING_RUNTIME_DISABLED"
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _mapping(contract.get("reference_only_control_input_contract"))
    projection = _mapping(contract.get("control_projection_contract"))
    boundary = _mapping(contract.get("stage_boundary"))
    required_flags = (
        "keyword_retrieval_baseline_required",
        "vector_retrieval_baseline_required",
        "vector_similarity_only_prohibited",
        "all_six_metadata_filter_dimensions_required",
        "metadata_status_filter_required",
        "active_index_version_contract_required",
        "candidate_selected_and_trace_active_index_version_chain_required",
        "candidate_selected_and_trace_metadata_filter_chain_required",
        "candidate_selected_score_and_explanation_chain_required",
        "trace_query_filter_candidate_selected_score_and_evidence_ledger_chain_required",
        "future_postgresql_fts_bm25_route_declared",
        "future_pgvector_route_declared",
        "future_metadata_filter_route_declared",
        "future_hybrid_ranking_and_trace_routes_declared",
    )
    projection_lengths = (
        ("query_projection_fields", 9),
        ("metadata_filter_projection_fields", 8),
        ("active_index_version_projection_fields", 7),
        ("candidate_chunk_fields", 10),
        ("score_fields", 7),
        ("selected_chunk_fields", 10),
        ("retrieval_trace_fields", 14),
        ("future_integration_projection_fields", 6),
    )
    return (
        contract.get("schema_version") == "ids.stage087.retrieval_trace.phase2.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE087-P2"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-087"
        and contract.get("phase") == "IDS-STAGE087-P2"
        and contract.get("next_gate") == "IDS-STAGE087-P3-GATE"
        and inputs.get("control_prefix") == CONTROL_PREFIX
        and inputs.get("control_request_count") == 6
        and inputs.get("input_field_count") == 18
        and inputs.get("query_field_count") == 9
        and inputs.get("metadata_filter_field_count") == 7
        and inputs.get("only_fixed_control_input_accepted") is True
        and inputs.get("vector_only_control_input_prohibited") is True
        and inputs.get("six_filter_dimensions_required") is True
        and inputs.get("metadata_status_filter_required") is True
        and inputs.get("evidence_ledger_reference_required") is True
        and projection.get("each_projection_count") == 6
        and projection.get("control_projection_field_total_per_request") == 71
        and projection.get("control_projection_field_total") == 426
        and all(
            _sequence_length(projection.get(key)) == size
            for key, size in projection_lengths
        )
        and all(projection.get(field) is True for field in required_flags)
        and _nested_runtime_closed(inputs, projection)
        and _authority_closed(_mapping(contract.get("source_authority")))
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage086_review_evidence_declared") is True
        and boundary.get("stage087_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_started") is True
        and boundary.get("phase2_completed") is True
        and all(
            boundary.get(field) is False
            for field in (
                "phase3_started",
                "phase4_started",
                "whole_stage_review_started",
                "stage088_started",
                "ovh_started",
                "production_started",
                "upload_or_push_started",
            )
        )
        and _mapping(contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 27
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenario = _mapping(contract.get("scenario_result_contract"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    boundary = _mapping(contract.get("stage_boundary"))
    required_replay_flags = (
        "input_accepted_required",
        "keyword_baseline_required",
        "vector_baseline_required",
        "vector_similarity_only_rejected",
        "six_metadata_filter_dimensions_required",
        "metadata_status_filter_reference_required",
        "standalone_active_index_version_record_required",
        "candidate_selected_and_trace_active_index_version_chain_required",
        "candidate_selected_and_trace_metadata_filter_chain_required",
        "trace_query_filter_candidate_selected_score_and_evidence_ledger_chain_required",
        "candidate_selected_score_explanation_chain_required",
    )
    return (
        contract.get("schema_version") == "ids.stage087.retrieval_trace.phase3.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE087-P3"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-087"
        and contract.get("phase") == "IDS-STAGE087-P3"
        and contract.get("next_gate") == "IDS-STAGE087-P4-GATE"
        and replay.get("required_control_request_count") == 6
        and replay.get("control_prefix") == CONTROL_PREFIX
        and replay.get("expected_phase2_field_check_count") == 426
        and replay.get("execution_state_required") == P2_EXECUTION_STATE
        and all(replay.get(field) is True for field in required_replay_flags)
        and scenario.get("scenario_executable") is True
        and scenario.get("execution_ready") is False
        and scenario.get("scenario_count") == 8
        and scenario.get("scenario_field_count") == 31
        and scenario.get("expected_scenario_field_check_count") == 248
        and _sequence_length(scenario.get("scenario_result_fields")) == 31
        and scenario.get("human_handling_required") is True
        and scenario.get("silent_drop_allowed") is False
        and failure.get("failure_state_count") == 14
        and failure.get("failure_closed") is True
        and _scenario_authority_closed(_mapping(contract.get("source_authority")))
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage086_review_evidence_declared") is True
        and boundary.get("stage087_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is True
        and all(
            boundary.get(field) is False
            for field in (
                "phase4_started",
                "whole_stage_review_performed",
                "stage088_started",
                "github_upload_allowed",
                "push_allowed",
            )
        )
        and _mapping(contract.get("rollback_contract")).get("fallback_result")
        == "PASS_RETRIEVAL_TRACE_CONTROL_SLICE_RUNTIME_DISABLED"
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase3_controlled_scenario_replay_contract"))
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    required_replay_flags = (
        "keyword_and_domain_coverage_required",
        "vector_contract_chain_required",
        "vector_only_rejection_required",
        "six_dimension_filter_combination_required",
        "active_index_version_contract_required",
        "candidate_selected_score_trace_evidence_chain_required",
        "top_k_ranking_and_validity_required",
        "old_index_trace_version_required",
    )
    delivery_shape = (
        ("retrieval_sample_control_record_count", "retrieval_sample_field_count", 8, 14),
        ("trace_log_control_record_count", "trace_log_field_count", 8, 14),
        ("filter_result_control_record_count", "filter_result_field_count", 8, 10),
        (
            "validity_test_report_control_record_count",
            "validity_test_report_field_count",
            8,
            15,
        ),
        ("evidence_gap_control_record_count", "evidence_gap_field_count", 8, 14),
        (
            "parameter_rollback_instruction_count",
            "parameter_rollback_instruction_field_count",
            4,
            9,
        ),
    )
    return (
        contract.get("schema_version")
        == "ids.stage087.retrieval_trace.phase4.delivery.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE087-P4"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-087"
        and contract.get("phase") == "IDS-STAGE087-P4"
        and contract.get("entry_gate") == "IDS-STAGE087-P4-GATE"
        and contract.get("next_gate") == REVIEW_GATE
        and replay.get("control_prefix") == CONTROL_PREFIX
        and replay.get("required_control_request_count") == 6
        and replay.get("phase2_control_field_check_count") == 426
        and replay.get("scenario_count") == 8
        and replay.get("scenario_field_count") == 31
        and replay.get("scenario_field_check_count") == 248
        and all(replay.get(field) is True for field in required_replay_flags)
        and delivery.get("delivery_executable") is True
        and delivery.get("execution_ready") is False
        and delivery.get("metadata_only") is True
        and delivery.get("delivery_field_check_count") == 572
        and delivery.get("chinese_feedback_count") == 4
        and all(
            delivery.get(count_key) == count and delivery.get(field_key) == field_count
            for count_key, field_key, count, field_count in delivery_shape
        )
        and failure.get("failure_state_count") == 20
        and failure.get("whole_stage_review_must_not_start") is True
        and _delivery_authority_closed(_mapping(contract.get("source_authority")))
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage086_review_evidence_declared") is True
        and boundary.get("stage087_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_completed") is True
        and boundary.get("phase4_started") is True
        and all(
            boundary.get(field) is False
            for field in (
                "whole_stage_review_performed",
                "stage088_started",
                "github_upload_allowed",
                "push_allowed",
            )
        )
        and _mapping(contract.get("rollback_contract")).get("fallback_result")
        == P3_PASS_RESULT
    )


def _phase2_report_valid(module: Any | None, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    if (
        report.get("schema_version") != module.SCHEMA_VERSION
        or report.get("input_accepted") is not True
        or report.get("execution_state") != P2_EXECUTION_STATE
        or report.get("actual_input_request_count") != 0
        or report.get("persistent_record_created") is not False
        or not _runtime_boundary_closed(_mapping(report.get("runtime_boundary")))
    ):
        return False
    for records_key, count_key, fields_name in P2_PROJECTION_FIELDS:
        records = _records(report.get(records_key))
        fields = getattr(module, fields_name)
        if (
            len(records) != 6
            or report.get(count_key) != 6
            or any(set(record) != set(fields) for record in records)
        ):
            return False
    return (
        _phase2_field_check_count(report) == 426
        and all(
            report.get(field) is True
            for field in (
                "all_keyword_baselines_declared",
                "all_vector_baselines_declared",
                "all_vector_similarity_only_routes_rejected",
                "all_six_metadata_filter_dimensions_covered",
                "all_active_index_version_contracts_match",
                "all_candidate_active_index_versions_match",
                "all_candidate_metadata_filter_references_match",
                "all_candidate_score_references_declared",
                "all_selected_chunks_match_candidates",
                "all_selected_active_index_versions_match",
                "all_selected_metadata_filter_references_match",
                "all_selected_ranking_policies_match",
                "all_score_explanations_declared",
                "all_trace_active_index_versions_match",
                "all_trace_metadata_filter_references_match",
                "all_trace_candidate_and_selected_sets_match",
                "all_trace_score_references_match",
                "all_evidence_ledger_bindings_declared",
            )
        )
        and _nested_runtime_closed(report)
    )


def _phase3_report_valid(module: Any | None, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    scenarios = _records(report.get("scenario_results"))
    expected_ids = [item["scenario_id"] for item in module.SCENARIOS]
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE087-P4-GATE"
        and report.get("phase2_control_slice_replayed") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("phase2_control_record_field_check_count") == 426
        and report.get("scenario_count") == 8
        and report.get("scenario_field_count") == 31
        and report.get("scenario_field_check_count") == 248
        and report.get("passed_scenario_count") == 8
        and report.get("explicit_disposition_count") == 8
        and report.get("silent_drop_count") == 0
        and report.get("human_handling_required_count") == 8
        and all(
            report.get(field) is True
            for field in (
                "keyword_and_domain_coverage_preserved",
                "vector_contract_chain_preserved",
                "six_dimension_filter_combination_preserved",
                "active_index_version_chain_preserved",
                "top_k_ranking_and_validity_preserved",
                "old_index_trace_version_preserved",
                "all_control_references_opaque",
            )
        )
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and _records_have_exact_shape(scenarios, 8, module.SCENARIO_RESULT_FIELDS)
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("silent_drop") is False for item in scenarios)
        and all(item.get("human_handling_required") is True for item in scenarios)
        and all(
            item.get("business_line_whitebox_human_approval_recorded") is False
            for item in scenarios
        )
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
        and report.get("stage086_review_evidence_declared") is True
        and report.get("stage087_started") is True
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("stage088_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
        and _nested_runtime_closed(report)
    )


def _phase4_report_valid(module: Any | None, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    groups = (
        ("retrieval_sample_control_records", 8, module.RETRIEVAL_SAMPLE_FIELDS),
        ("trace_log_control_records", 8, module.TRACE_LOG_FIELDS),
        ("filter_result_control_records", 8, module.FILTER_RESULT_FIELDS),
        (
            "validity_test_report_control_records",
            8,
            module.VALIDITY_TEST_REPORT_FIELDS,
        ),
        ("evidence_gap_control_records", 8, module.EVIDENCE_GAP_FIELDS),
        (
            "parameter_rollback_instruction_control_records",
            4,
            module.PARAMETER_ROLLBACK_INSTRUCTION_FIELDS,
        ),
    )
    return (
        report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_replayed_in_memory_only") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("delivery_field_check_count") == 572
        and all(
            _records_have_exact_shape(_records(report.get(key)), count, fields)
            for key, count, fields in groups
        )
        and report.get("all_delivery_references_control_only") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document") is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and all(
            report.get(field) is False
            for field in (
                "automatic_gap_resolution_allowed",
                "automatic_business_recommendation_allowed",
                "automatic_parameter_rollback_allowed",
                "automatic_index_switch_allowed",
            )
        )
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
        and report.get("stage086_review_evidence_declared") is True
        and report.get("stage087_started") is True
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_completed") is True
        and report.get("phase4_started") is True
        and report.get("whole_stage_review_performed") is False
        and report.get("stage087_review_started") is False
        and report.get("stage088_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
        and _nested_runtime_closed(report)
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> dict[str, int]:
    shape = _mapping(phase1.get("retrieval_trace_control_contract"))
    return {
        "phase1_query_field_count": _integer(shape.get("query_record_field_count")),
        "phase1_filter_field_count": _integer(shape.get("filter_record_field_count")),
        "phase1_candidate_chunk_field_count": _integer(
            shape.get("candidate_chunk_record_field_count")
        ),
        "phase1_selected_chunk_field_count": _integer(
            shape.get("selected_chunk_record_field_count")
        ),
        "phase1_score_field_count": _integer(shape.get("score_record_field_count")),
        "phase1_active_index_version_field_count": _integer(
            shape.get("active_index_version_record_field_count")
        ),
        "phase1_retrieval_trace_field_count": _integer(
            shape.get("retrieval_trace_record_field_count")
        ),
        "phase1_failure_state_count": _integer(
            _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase2_control_request_count": _sequence_length(
            phase2.get("query_control_projections")
        ),
        "phase2_projection_set_count": len(P2_PROJECTION_FIELDS),
        "phase2_control_field_check_count": _phase2_field_check_count(phase2),
        "phase2_failure_state_count": _integer(
            _mapping(phase2_contract.get("failure_and_stop_contract")).get(
                "failure_state_count"
            )
        ),
        "phase3_scenario_count": _integer(phase3.get("scenario_count")),
        "phase3_scenario_field_count": _integer(phase3.get("scenario_field_count")),
        "phase3_scenario_field_check_count": _integer(
            phase3.get("scenario_field_check_count")
        ),
        "phase3_human_handling_required_count": _integer(
            phase3.get("human_handling_required_count")
        ),
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
        "phase4_delivery_field_check_count": _integer(
            phase4.get("delivery_field_check_count")
        ),
        "phase4_chinese_feedback_count": _sequence_length(
            phase4.get("chinese_feedback")
        ),
        "phase4_failure_state_count": _integer(
            _mapping(phase4_contract.get("failure_and_stop_contract")).get(
                "failure_state_count"
            )
        ),
    }


def _phase2_field_check_count(report: Mapping[str, Any]) -> int:
    return sum(
        sum(len(record) for record in _records(report.get(records_key)))
        for records_key, _count_key, _fields_name in P2_PROJECTION_FIELDS
    )


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        _authority_closed(_mapping(phase1.get("source_authority")))
        and _authority_closed(_mapping(phase2_contract.get("source_authority")))
        and _scenario_authority_closed(_mapping(phase3_contract.get("source_authority")))
        and _delivery_authority_closed(_mapping(phase4_contract.get("source_authority")))
        and phase3.get("source_document_remains_authoritative") is True
        and phase3.get("control_scenario_can_replace_source_document") is False
        and phase3.get("control_result_can_become_business_fact_authority") is False
        and phase4.get("source_document_remains_authoritative") is True
        and phase4.get("delivery_control_metadata_can_replace_source_document")
        is False
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
        _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        == 21
        and _mapping(phase2_contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 27
        and _mapping(phase3_contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 14
        and _mapping(phase3_contract.get("failure_and_stop_contract")).get(
            "failure_closed"
        )
        is True
        and _mapping(phase3_contract.get("scenario_result_contract")).get(
            "silent_drop_allowed"
        )
        is False
        and _mapping(phase4_contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 20
        and _mapping(phase4_contract.get("failure_and_stop_contract")).get(
            "whole_stage_review_must_not_start"
        )
        is True
        and phase3.get("silent_drop_count") == 0
        and phase3.get("old_index_trace_version_preserved") is True
        and all(
            phase4.get(field) is False
            for field in (
                "automatic_gap_resolution_allowed",
                "automatic_business_recommendation_allowed",
                "automatic_parameter_rollback_allowed",
                "automatic_index_switch_allowed",
            )
        )
        and _mapping(phase4_contract.get("rollback_contract")).get("fallback_result")
        == P3_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_report_valid") is True
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    authority = _mapping(phase4_contract.get("source_authority"))
    return (
        phase3.get("human_handling_required_count") == 8
        and phase4.get("delivery_evidence_metadata_only") is True
        and phase4.get("all_delivery_references_control_only") is True
        and phase4.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and phase4.get("automatic_business_recommendation_allowed") is False
    )


def _next_stage_available_but_not_started(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        NEXT_TASKPACK.is_file()
        and _mapping(phase1.get("stage_and_phase_boundary")).get("stage088_started")
        is False
        and _mapping(phase2_contract.get("stage_boundary")).get("stage088_started")
        is False
        and _mapping(phase3_contract.get("stage_boundary")).get("stage088_started")
        is False
        and _mapping(phase4_contract.get("stage_and_phase_boundary")).get(
            "stage088_started"
        )
        is False
        and phase3.get("stage088_started") is False
        and phase4.get("stage088_started") is False
    )


def _authority_closed(authority: Mapping[str, Any]) -> bool:
    return (
        authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and authority.get("raw_metadata_content_access_allowed") is False
        and authority.get("live_source_read_performed") is False
        and authority.get("authorized_fixture_access_performed") is False
    )


def _scenario_authority_closed(authority: Mapping[str, Any]) -> bool:
    return (
        _authority_closed(authority)
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("control_scenario_can_replace_source_document") is False
        and authority.get("control_result_can_become_business_fact_authority") is False
    )


def _delivery_authority_closed(authority: Mapping[str, Any]) -> bool:
    return (
        _authority_closed(authority)
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and authority.get("delivery_control_metadata_can_replace_source_document")
        is False
        and authority.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
    )


def _nested_runtime_closed(*items: Mapping[str, Any]) -> bool:
    return all(_value_runtime_closed(item) for item in items)


def _value_runtime_closed(value: object, field_name: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_value_runtime_closed(item, str(key)) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return all(_value_runtime_closed(item, field_name) for item in value)
    if field_name.startswith("actual_"):
        return _zero(value) if field_name.endswith("_count") else value is False
    if field_name in REVIEW_RUNTIME_FALSE_FIELDS:
        return value is False
    return True


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _load_module(module_name: str, file_name: str) -> Any | None:
    spec = importlib.util.spec_from_file_location(module_name, BASE / file_name)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _read_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _shapes_match(
    shape: Mapping[str, Any], specs: Sequence[tuple[str, str, int]]
) -> bool:
    return all(
        shape.get(count_key) == expected_count
        and _sequence_length(shape.get(fields_key)) == expected_count
        for count_key, fields_key, expected_count in specs
    )


def _records_have_exact_shape(
    value: object, count: int, fields: Sequence[str]
) -> bool:
    records = _records(value)
    return len(records) == count and all(set(record) == set(fields) for record in records)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence_length(value: object) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return 0
    return len(value)


def _runtime_boundary_closed(mapping: Mapping[str, Any]) -> bool:
    return bool(mapping) and all(
        _zero(value)
        if key.startswith("actual_") and key.endswith("_count")
        else value is False
        for key, value in mapping.items()
    )


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _zero(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0
