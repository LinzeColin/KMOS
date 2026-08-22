"""Stage085 的纯内存整阶段机械复审，不读取真实资料或启动 Stage086。"""

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
    / "STAGE-085_元数据过滤.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-086_混合排序.md"
)
P1_CONTRACT = BASE / "stage085_metadata_filter_contract.json"
P2_CONTRACT = BASE / "stage085_metadata_filter_slice_contract.json"
P3_CONTRACT = BASE / "stage085_metadata_filter_scenarios_contract.json"
P4_CONTRACT = BASE / "stage085_metadata_filter_delivery_contract.json"

SCHEMA_VERSION = "ids.stage085.metadata_filter.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE085-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-085"
PASS_RESULT = "PASS_REVIEWED_METADATA_FILTER_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_METADATA_FILTER_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE085-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE086-P1-GATE"
RETURN_STATE = "PASS_METADATA_FILTER_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_METADATA_FILTER_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_METADATA_FILTER_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_METADATA_FILTER_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage085-p2:"

EXPECTED_CONTROLLED_REPLAY = {
    "phase1_query_field_count": 11,
    "phase1_metadata_filter_field_count": 7,
    "phase1_candidate_field_count": 11,
    "phase1_selected_result_field_count": 8,
    "phase1_hybrid_score_field_count": 7,
    "phase1_retrieval_trace_field_count": 10,
    "phase1_failure_state_count": 21,
    "phase2_control_request_count": 6,
    "phase2_projection_set_count": 7,
    "phase2_control_field_check_count": 366,
    "phase2_failure_state_count": 22,
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
    "phase4_failure_state_count": 18,
}

P1_SHAPE_SPECS = (
    ("query_field_count", "future_query_fields", 11),
    ("metadata_filter_field_count", "future_metadata_filter_fields", 7),
    ("candidate_field_count", "future_candidate_fields", 11),
    ("selected_result_field_count", "future_selected_result_fields", 8),
    ("hybrid_score_field_count", "future_hybrid_score_fields", 7),
    ("retrieval_trace_field_count", "future_retrieval_trace_fields", 10),
)
P2_PROJECTION_FIELDS = (
    ("query_control_projections", "QUERY_FIELDS"),
    ("metadata_filter_control_projections", "METADATA_FILTER_PROJECTION_FIELDS"),
    ("candidate_control_projections", "CANDIDATE_FIELDS"),
    ("hybrid_score_control_projections", "HYBRID_SCORE_FIELDS"),
    ("selected_result_control_projections", "SELECTED_RESULT_FIELDS"),
    ("retrieval_trace_control_projections", "RETRIEVAL_TRACE_FIELDS"),
    ("future_integration_control_projections", "FUTURE_INTEGRATION_FIELDS"),
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
    "actual_chinese_feedback_published",
)


def build_metadata_filter_stage085_review_report(
    *,
    phase1_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_report_provider: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """只重放冻结 P1--P4 控制工件，返回失败关闭的复审结论。"""

    phase1 = _provider_result(
        phase1_contract_provider or _default_phase1_contract_provider
    )
    phase2_contract = _provider_result(
        phase2_contract_provider or _default_phase2_contract_provider
    )
    phase3_contract = _provider_result(
        phase3_contract_provider or _default_phase3_contract_provider
    )
    phase4_contract = _provider_result(
        phase4_contract_provider or _default_phase4_contract_provider
    )
    phase2_module = _load_module(
        "stage085_review_phase2", "stage085_metadata_filter_control_slice.py"
    )
    phase3_module = _load_module(
        "stage085_review_phase3", "stage085_metadata_filter_controlled_scenarios.py"
    )
    phase4_module = _load_module(
        "stage085_review_phase4", "stage085_metadata_filter_delivery.py"
    )
    phase2 = _provider_result(phase2_report_provider or _default_phase2_report_provider)
    phase3 = _provider_result(phase3_report_provider or _default_phase3_report_provider)
    phase4 = _provider_result(phase4_report_provider or _default_phase4_report_provider)

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
    all_phases_pass = all(phase_results.values())
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
        phase1, phase2_contract, phase3_contract, phase4_contract, phase2, phase3, phase4
    )
    next_stage_available_but_not_started = _next_stage_available_but_not_started(
        phase1, phase2_contract, phase3_contract, phase4_contract, phase3, phase4
    )
    runtime_flags = _runtime_closed_flags()
    review_valid = (
        TASKPACK.is_file()
        and all_phases_pass
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
        "all_phase_contracts_and_control_reports_pass": all_phases_pass,
        "fixed_control_shapes_preserved": fixed_shapes,
        "single_authority_boundary_preserved": authority_preserved,
        "failure_stop_and_rollback_boundaries_preserved": failure_and_rollback_preserved,
        "delivery_and_whitebox_boundaries_preserved": delivery_and_whitebox_preserved,
        "runtime_actions_disabled": nested_runtime_closed
        and all(value is False for value in runtime_flags.values()),
        "next_stage_taskpack_available_but_not_started": next_stage_available_but_not_started,
        "stage086_gate_only_opens_after_review": review_valid and next_gate == NEXT_GATE,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE085_TASKPACK_AND_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "reviewed_phase_ids": [
            "IDS-STAGE085-P1",
            "IDS-STAGE085-P2",
            "IDS-STAGE085-P3",
            "IDS-STAGE085-P4",
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
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "stage085_started": True,
        "stage086_started": False,
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
            "scope": "STAGE085_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
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


def _default_phase1_contract_provider() -> Mapping[str, Any]:
    return _read_json(P1_CONTRACT)


def _default_phase2_contract_provider() -> Mapping[str, Any]:
    return _read_json(P2_CONTRACT)


def _default_phase3_contract_provider() -> Mapping[str, Any]:
    return _read_json(P3_CONTRACT)


def _default_phase4_contract_provider() -> Mapping[str, Any]:
    return _read_json(P4_CONTRACT)


def _default_phase2_report_provider() -> Mapping[str, Any]:
    module = _load_module(
        "stage085_review_phase2_provider", "stage085_metadata_filter_control_slice.py"
    )
    if module is None:
        return {}
    return module.execute_metadata_filter_control_slice(module.build_control_input())


def _default_phase3_report_provider() -> Mapping[str, Any]:
    module = _load_module(
        "stage085_review_phase3_provider", "stage085_metadata_filter_controlled_scenarios.py"
    )
    if module is None:
        return {}
    return module.build_metadata_filter_phase3_report()


def _default_phase4_report_provider() -> Mapping[str, Any]:
    module = _load_module(
        "stage085_review_phase4_provider", "stage085_metadata_filter_delivery.py"
    )
    if module is None:
        return {}
    return module.build_metadata_filter_phase4_delivery_report()


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    shape = _mapping(contract.get("query_filter_candidate_selected_score_and_trace_contract"))
    authority = _mapping(contract.get("source_authority"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    rollback = _mapping(contract.get("rollback_contract"))
    required_flags = (
        "keyword_retrieval_baseline_required",
        "vector_retrieval_baseline_required",
        "vector_similarity_only_prohibited",
        "embedding_model_version_contract_required",
        "similarity_metric_contract_required",
        "metadata_filter_contract_required",
        "all_six_metadata_filter_dimensions_required",
        "metadata_status_filter_contract_required",
        "hybrid_ranking_contract_required",
        "retrieval_trace_contract_required",
        "requested_top_k_must_be_declared",
        "candidate_selected_and_trace_must_reference_active_index_version",
        "candidate_selected_and_trace_must_reference_metadata_filter_contract",
        "candidate_and_trace_must_reference_embedding_model_version_and_similarity_metric",
        "selected_result_must_include_score_explanation_ref",
        "selected_result_and_trace_must_include_evidence_ledger_ref",
        "all_values_are_control_labels_only",
    )
    no_phase1_runtime = (
        "actual_query_text_read_performed",
        "actual_embedding_created",
        "actual_metadata_filter_evaluated",
        "actual_candidate_record_created",
        "actual_selected_result_created",
        "actual_score_calculated",
        "actual_retrieval_trace_created",
    )
    return (
        contract.get("schema_version") == "ids.stage085.metadata_filter_contract.phase1.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE085-P1"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-085"
        and contract.get("phase") == "IDS-STAGE085-P1"
        and contract.get("next_gate") == "IDS-STAGE085-P2-GATE"
        and all(
            shape.get(count_field) == expected_count
            and _sequence_length(shape.get(fields_field)) == expected_count
            for count_field, fields_field, expected_count in P1_SHAPE_SPECS
        )
        and all(shape.get(field) is True for field in required_flags)
        and all(shape.get(field) is False for field in no_phase1_runtime)
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and authority.get("raw_metadata_content_access_allowed") is False
        and authority.get("live_source_read_performed") is False
        and authority.get("authorized_fixture_access_performed") is False
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage084_review_evidence_declared") is True
        and boundary.get("stage085_started") is True
        and boundary.get("stage085_entry_authorized") is True
        and boundary.get("phase1_started") is True
        and boundary.get("phase2_started") is False
        and boundary.get("phase3_started") is False
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage086_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
        and rollback.get("return_to")
        == "PASS_REVIEWED_VECTOR_RETRIEVAL_BASELINE_RUNTIME_DISABLED"
        and _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
        == 21
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    inputs = _mapping(contract.get("reference_only_control_input_contract"))
    projection = _mapping(contract.get("control_projection_contract"))
    authority = _mapping(contract.get("source_authority"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    required_projection_flags = (
        "keyword_retrieval_baseline_required",
        "vector_retrieval_baseline_required",
        "vector_similarity_only_prohibited",
        "all_six_metadata_filter_dimensions_required",
        "metadata_status_filter_required",
        "embedding_model_version_dimension_and_similarity_metric_required",
        "candidate_selected_and_trace_active_index_version_chain_required",
        "candidate_selected_and_trace_metadata_filter_chain_required",
        "candidate_and_trace_vector_contract_chain_required",
        "score_explanation_required",
        "selected_result_and_trace_evidence_ledger_binding_required",
        "future_postgresql_fts_bm25_route_declared",
        "future_pgvector_route_declared",
    )
    expected_projection_lengths = (
        ("query_projection_fields", 11),
        ("metadata_filter_projection_fields", 8),
        ("candidate_fields", 11),
        ("hybrid_score_fields", 7),
        ("selected_result_fields", 8),
        ("retrieval_trace_fields", 10),
        ("future_integration_projection_fields", 6),
    )
    return (
        contract.get("schema_version") == "ids.stage085.metadata_filter.phase2.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE085-P2"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-085"
        and contract.get("phase") == "IDS-STAGE085-P2"
        and contract.get("next_gate") == "IDS-STAGE085-P3-GATE"
        and inputs.get("control_request_count") == 6
        and inputs.get("control_prefix") == CONTROL_PREFIX
        and inputs.get("input_field_count") == 20
        and inputs.get("all_values_are_opaque_control_labels_only") is True
        and inputs.get("actual_input_request_count") == 0
        and projection.get("each_projection_count") == 6
        and projection.get("control_projection_field_total_per_request") == 61
        and projection.get("control_projection_field_total") == 366
        and all(
            _sequence_length(projection.get(field)) == expected_length
            for field, expected_length in expected_projection_lengths
        )
        and all(projection.get(field) is True for field in required_projection_flags)
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and authority.get("raw_metadata_content_access_allowed") is False
        and authority.get("live_source_read_performed") is False
        and authority.get("authorized_fixture_access_performed") is False
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage085_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_started") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is False
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage086_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
        and _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
        == 22
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase2_replay_contract"))
    scenarios = _mapping(contract.get("scenario_result_contract"))
    authority = _mapping(contract.get("source_authority"))
    boundary = _mapping(contract.get("stage_boundary"))
    failure = _mapping(contract.get("failure_and_stop_contract"))
    return (
        contract.get("schema_version") == "ids.stage085.metadata_filter.phase3.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE085-P3"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-085"
        and contract.get("phase") == "IDS-STAGE085-P3"
        and contract.get("next_gate") == "IDS-STAGE085-P4-GATE"
        and replay.get("required_control_request_count") == 6
        and replay.get("control_prefix") == CONTROL_PREFIX
        and replay.get("expected_phase2_field_check_count") == 366
        and replay.get("six_metadata_filter_dimensions_required") is True
        and replay.get("metadata_status_filter_reference_required") is True
        and replay.get("candidate_selected_and_trace_metadata_filter_chain_required")
        is True
        and scenarios.get("scenario_count") == 8
        and scenarios.get("scenario_field_count") == 31
        and scenarios.get("expected_scenario_field_check_count") == 248
        and scenarios.get("silent_drop_allowed") is False
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("control_scenario_can_replace_source_document") is False
        and authority.get("control_result_can_become_business_fact_authority") is False
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage085_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_started") is True
        and boundary.get("phase4_started") is False
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage086_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
        and failure.get("failure_state_count") == 14
        and failure.get("failure_closed") is True
        and failure.get("automatic_business_recommendation_allowed") is False
        and failure.get("automatic_business_write_allowed") is False
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    replay = _mapping(contract.get("phase3_controlled_scenario_replay_contract"))
    delivery = _mapping(contract.get("delivery_evidence_contract"))
    authority = _mapping(contract.get("source_authority"))
    boundary = _mapping(contract.get("stage_and_phase_boundary"))
    rollback = _mapping(contract.get("rollback_contract"))
    expected_delivery_shapes = (
        ("retrieval_sample_control_record_count", 8),
        ("retrieval_sample_field_count", 14),
        ("trace_log_control_record_count", 8),
        ("trace_log_field_count", 14),
        ("filter_result_control_record_count", 8),
        ("filter_result_field_count", 10),
        ("validity_test_report_control_record_count", 8),
        ("validity_test_report_field_count", 15),
        ("evidence_gap_control_record_count", 8),
        ("evidence_gap_field_count", 14),
        ("parameter_rollback_instruction_count", 4),
        ("parameter_rollback_instruction_field_count", 9),
        ("delivery_field_check_count", 572),
        ("chinese_feedback_count", 4),
    )
    return (
        contract.get("schema_version")
        == "ids.stage085.metadata_filter.phase4.delivery.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE085-P4"
        and contract.get("acceptance_id") == ACCEPTANCE_ID
        and contract.get("stage") == "STAGE-085"
        and contract.get("phase") == "IDS-STAGE085-P4"
        and contract.get("next_gate") == REVIEW_GATE
        and replay.get("required_control_request_count") == 6
        and replay.get("control_prefix") == CONTROL_PREFIX
        and replay.get("phase2_control_field_check_count") == 366
        and replay.get("scenario_count") == 8
        and replay.get("scenario_field_count") == 31
        and replay.get("scenario_field_check_count") == 248
        and delivery.get("metadata_only") is True
        and all(delivery.get(field) == expected for field, expected in expected_delivery_shapes)
        and authority.get("source_document_remains_authoritative") is True
        and authority.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and authority.get("delivery_control_metadata_can_replace_source_document")
        is False
        and authority.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and authority.get("second_authoritative_source_created") is False
        and authority.get("source_body_or_path_allowed") is False
        and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))
        and boundary.get("stage085_started") is True
        and boundary.get("phase1_completed") is True
        and boundary.get("phase2_completed") is True
        and boundary.get("phase3_completed") is True
        and boundary.get("phase4_started") is True
        and boundary.get("whole_stage_review_performed") is False
        and boundary.get("stage086_started") is False
        and boundary.get("github_upload_allowed") is False
        and boundary.get("push_allowed") is False
        and rollback.get("fallback_result") == P3_PASS_RESULT
        and _mapping(contract.get("failure_and_stop_contract")).get("failure_state_count")
        == 18
    )


def _phase2_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    projection_shapes_valid = all(
        _records_have_exact_shape(report.get(records_key), 6, getattr(module, field_name, ()))
        for records_key, field_name in P2_PROJECTION_FIELDS
    )
    counts_valid = all(
        report.get(f"{records_key.removesuffix('s')}_count") == 6
        for records_key, _field_name in P2_PROJECTION_FIELDS
    )
    required_flags = (
        "all_keyword_baselines_declared",
        "all_vector_baselines_declared",
        "all_vector_similarity_only_routes_rejected",
        "all_six_metadata_filter_dimensions_covered",
        "all_metadata_status_filter_references_declared",
        "all_candidate_active_index_versions_match",
        "all_candidate_metadata_filter_references_match",
        "all_candidate_vector_contracts_match",
        "all_selected_results_match_candidates",
        "all_selected_metadata_filter_references_match",
        "all_score_explanations_declared",
        "all_trace_active_index_versions_match",
        "all_trace_metadata_filter_references_match",
        "all_trace_vector_contracts_match",
        "all_evidence_ledger_bindings_declared",
    )
    return (
        report.get("schema_version") == "ids.stage085.metadata_filter.phase2.v1"
        and report.get("record_kind") == "CONTROL_ONLY_IN_MEMORY_METADATA_FILTER"
        and report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_input_request_count") == 6
        and report.get("actual_input_request_count") == 0
        and projection_shapes_valid
        and counts_valid
        and all(report.get(field) is True for field in required_flags)
        and _runtime_boundary_closed(_mapping(report.get("runtime_boundary")))
    )


def _phase3_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    expected_ids = [item.get("scenario_id") for item in getattr(module, "SCENARIOS", ())]
    scenarios = _sequence(report.get("scenario_results"))
    required_flags = (
        "keyword_and_domain_coverage_preserved",
        "vector_contract_chain_preserved",
        "six_dimension_filter_combination_preserved",
        "metadata_status_filter_reference_preserved",
        "top_k_ranking_and_validity_preserved",
        "old_index_trace_version_preserved",
        "all_control_references_opaque",
    )
    return (
        report.get("schema_version") == "ids.stage085.metadata_filter.phase3.v1"
        and report.get("record_kind")
        == "CONTROL_ONLY_IN_MEMORY_METADATA_FILTER_SCENARIOS"
        and report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE085-P4-GATE"
        and report.get("phase2_control_slice_reexecuted") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("phase2_control_record_field_check_count") == 366
        and report.get("scenario_count") == 8
        and report.get("scenario_field_count") == 31
        and report.get("scenario_field_check_count") == 248
        and report.get("passed_scenario_count") == 8
        and report.get("explicit_disposition_count") == 8
        and report.get("silent_drop_count") == 0
        and report.get("human_handling_required_count") == 8
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and _records_have_exact_shape(scenarios, 8, getattr(module, "SCENARIO_RESULT_FIELDS", ()))
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("human_handling_required") is True for item in scenarios)
        and all(item.get("silent_drop") is False for item in scenarios)
        and all(item.get("observed_vector_only_rejected") is True for item in scenarios)
        and all(report.get(field) is True for field in required_flags)
        and all(report.get(field) is False for field in getattr(module, "RUNTIME_CLOSED_FIELDS", ()))
        and report.get("stage085_started") is True
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("stage086_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
    )


def _phase4_report_valid(module: Any, report: Mapping[str, Any]) -> bool:
    if module is None:
        return False
    shape_specs = (
        ("retrieval_sample_control_records", "RETRIEVAL_SAMPLE_FIELDS", 8),
        ("trace_log_control_records", "TRACE_LOG_FIELDS", 8),
        ("filter_result_control_records", "FILTER_RESULT_FIELDS", 8),
        ("validity_test_report_control_records", "VALIDITY_TEST_REPORT_FIELDS", 8),
        ("evidence_gap_control_records", "EVIDENCE_GAP_FIELDS", 8),
        (
            "parameter_rollback_instruction_control_records",
            "PARAMETER_ROLLBACK_INSTRUCTION_FIELDS",
            4,
        ),
    )
    return (
        report.get("schema_version") == "ids.stage085.metadata_filter.phase4.delivery.v1"
        and report.get("record_kind") == "METADATA_FILTER_DELIVERY_EVIDENCE_REPORT"
        and report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and report.get("phase3_controlled_scenarios_reexecuted_in_memory_only") is True
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("delivery_evidence_metadata_only") is True
        and all(
            _records_have_exact_shape(
                report.get(records_key), count, getattr(module, field_name, ())
            )
            for records_key, field_name, count in shape_specs
        )
        and report.get("retrieval_sample_control_record_count") == 8
        and report.get("retrieval_sample_field_count") == 14
        and report.get("trace_log_control_record_count") == 8
        and report.get("trace_log_field_count") == 14
        and report.get("filter_result_control_record_count") == 8
        and report.get("filter_result_field_count") == 10
        and report.get("validity_test_report_control_record_count") == 8
        and report.get("validity_test_report_field_count") == 15
        and report.get("evidence_gap_control_record_count") == 8
        and report.get("evidence_gap_field_count") == 14
        and report.get("parameter_rollback_instruction_count") == 4
        and report.get("parameter_rollback_instruction_field_count") == 9
        and report.get("delivery_field_check_count") == 572
        and _sequence_length(report.get("chinese_feedback")) == 4
        and report.get("all_delivery_references_control_only") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document") is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and report.get("automatic_gap_resolution_allowed") is False
        and report.get("automatic_business_recommendation_allowed") is False
        and report.get("automatic_parameter_rollback_allowed") is False
        and all(report.get(field) is False for field in getattr(module, "RUNTIME_CLOSED_FIELDS", ()))
        and report.get("stage085_started") is True
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_completed") is True
        and report.get("phase4_started") is True
        and report.get("whole_stage_review_performed") is False
        and report.get("stage086_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> dict[str, int]:
    p1_shape = _mapping(phase1.get("query_filter_candidate_selected_score_and_trace_contract"))
    return {
        "phase1_query_field_count": _integer(p1_shape.get("query_field_count")),
        "phase1_metadata_filter_field_count": _integer(
            p1_shape.get("metadata_filter_field_count")
        ),
        "phase1_candidate_field_count": _integer(p1_shape.get("candidate_field_count")),
        "phase1_selected_result_field_count": _integer(
            p1_shape.get("selected_result_field_count")
        ),
        "phase1_hybrid_score_field_count": _integer(
            p1_shape.get("hybrid_score_field_count")
        ),
        "phase1_retrieval_trace_field_count": _integer(
            p1_shape.get("retrieval_trace_field_count")
        ),
        "phase1_failure_state_count": _integer(
            _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count")
        ),
        "phase2_control_request_count": _integer(phase2.get("control_input_request_count")),
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
        "phase4_chinese_feedback_count": _sequence_length(phase4.get("chinese_feedback")),
        "phase4_failure_state_count": _integer(
            _mapping(phase4_contract.get("failure_and_stop_contract")).get(
                "failure_state_count"
            )
        ),
    }


def _phase2_field_check_count(report: Mapping[str, Any]) -> int:
    return sum(
        sum(len(item) for item in _sequence(report.get(records_key)))
        for records_key, _field_name in P2_PROJECTION_FIELDS
    )


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2_contract: Mapping[str, Any],
    phase3_contract: Mapping[str, Any],
    phase4_contract: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    p1_authority = _mapping(phase1.get("source_authority"))
    p2_authority = _mapping(phase2_contract.get("source_authority"))
    p3_authority = _mapping(phase3_contract.get("source_authority"))
    p4_authority = _mapping(phase4_contract.get("source_authority"))
    return (
        p1_authority.get("second_authoritative_source_created") is False
        and p1_authority.get("source_body_or_path_allowed") is False
        and p2_authority.get("second_authoritative_source_created") is False
        and p2_authority.get("source_body_or_path_allowed") is False
        and p3_authority.get("source_document_remains_authoritative") is True
        and p3_authority.get("control_scenario_can_replace_source_document") is False
        and p3_authority.get("control_result_can_become_business_fact_authority")
        is False
        and p4_authority.get("source_document_remains_authoritative") is True
        and p4_authority.get("delivery_control_metadata_can_replace_source_document")
        is False
        and p4_authority.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
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
        _mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count") == 21
        and _mapping(phase2_contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 22
        and _mapping(phase3_contract.get("scenario_result_contract")).get(
            "silent_drop_allowed"
        )
        is False
        and _mapping(phase3_contract.get("failure_and_stop_contract")).get(
            "failure_closed"
        )
        is True
        and _mapping(phase4_contract.get("failure_and_stop_contract")).get(
            "failure_state_count"
        )
        == 18
        and _mapping(phase4_contract.get("failure_and_stop_contract")).get(
            "whole_stage_review_must_not_start"
        )
        is True
        and phase3.get("silent_drop_count") == 0
        and phase3.get("old_index_trace_version_preserved") is True
        and phase4.get("automatic_gap_resolution_allowed") is False
        and phase4.get("automatic_business_recommendation_allowed") is False
        and phase4.get("automatic_parameter_rollback_allowed") is False
        and _mapping(phase4_contract.get("rollback_contract")).get("fallback_result")
        == P3_PASS_RESULT
        and phase4.get("phase3_controlled_scenarios_report_valid") is True
    )


def _delivery_and_whitebox_boundary(
    phase3: Mapping[str, Any], phase4_contract: Mapping[str, Any], phase4: Mapping[str, Any]
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
        and _mapping(phase1.get("stage_and_phase_boundary")).get("stage086_started")
        is False
        and _mapping(phase2_contract.get("stage_and_phase_boundary")).get(
            "stage086_started"
        )
        is False
        and _mapping(phase3_contract.get("stage_boundary")).get("stage086_started")
        is False
        and _mapping(phase4_contract.get("stage_and_phase_boundary")).get(
            "stage086_started"
        )
        is False
        and phase3.get("stage086_started") is False
        and phase4.get("stage086_started") is False
    )


def _nested_runtime_closed(*items: Mapping[str, Any]) -> bool:
    return all(_value_runtime_closed(item) for item in items)


def _value_runtime_closed(value: object, field_name: str = "") -> bool:
    if isinstance(value, Mapping):
        return all(_value_runtime_closed(item, str(key)) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return all(_value_runtime_closed(item, field_name) for item in value)
    if field_name.startswith("actual_") and field_name.endswith("_count"):
        return value == 0
    if field_name in REVIEW_RUNTIME_FALSE_FIELDS:
        return value is False
    if field_name.startswith("actual_") and field_name.endswith(
        ("_performed", "_written", "_published", "_created", "_changed")
    ):
        return value is False
    return True


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _load_module(module_name: str, file_name: str) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location(module_name, BASE / file_name)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ImportError, OSError, SyntaxError, ValueError):
        return None


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        result = provider()
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        json.JSONDecodeError,
    ):
        return {}
    return result if isinstance(result, Mapping) else {}


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, Mapping) else {}


def _records_have_exact_shape(value: object, count: int, fields: Sequence[str]) -> bool:
    records = _sequence(value)
    return len(records) == count and all(
        isinstance(record, Mapping) and set(record) == set(fields) for record in records
    )


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence_length(value: object) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return 0
    return len(value)


def _runtime_boundary_closed(mapping: Mapping[str, Any]) -> bool:
    return bool(mapping) and all(
        value == 0 if key.startswith("actual_") and key.endswith("_count") else value is False
        for key, value in mapping.items()
    )


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1
