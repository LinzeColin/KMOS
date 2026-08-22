"""Stage088 P3 的纯内存检索结果有效性门禁受控场景。

模块只重放 Stage088 P2 的六条固定控制投影。材料牌号、设备型号、标准号、
语义相似、Top-K、旧索引服务与结果有效性均只是验证场景类别；它们不携带、
读取、计算或写入业务内容。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage088.retrieval_result_validity.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_SCENARIOS"
PASS_RESULT = "PASS_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE088-P4-GATE"
CURRENT_GATE = "IDS-STAGE088-P3-GATE"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage088-p2:"
P2_SCENARIOS = (
    "keyword_document_type_filter_reference_only",
    "keyword_year_filter_reference_only",
    "hybrid_project_filter_reference_only",
    "hybrid_equipment_filter_reference_only",
    "hybrid_metadata_status_filter_reference_only",
    "hybrid_evidence_level_filter_reference_only",
)

P2_RECORD_SPECS = (
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
        "candidate_control_projections",
        "candidate_control_projection_count",
        "CANDIDATE_FIELDS",
    ),
    ("score_control_projections", "score_control_projection_count", "SCORE_FIELDS"),
    (
        "selected_control_projections",
        "selected_control_projection_count",
        "SELECTED_FIELDS",
    ),
    (
        "retrieval_trace_control_projections",
        "retrieval_trace_control_projection_count",
        "RETRIEVAL_TRACE_FIELDS",
    ),
    (
        "result_validity_gate_control_projections",
        "result_validity_gate_control_projection_count",
        "RESULT_VALIDITY_GATE_FIELDS",
    ),
    (
        "future_integration_control_projections",
        "future_integration_control_projection_count",
        "FUTURE_INTEGRATION_FIELDS",
    ),
)

RUNTIME_CLOSED_FIELDS = (
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
)

P2_CHAIN_FLAGS = (
    "all_keyword_baselines_declared",
    "all_vector_baselines_declared",
    "all_vector_similarity_only_routes_rejected",
    "all_six_metadata_filter_dimensions_covered",
    "all_active_index_version_contracts_match",
    "all_candidate_active_index_versions_match",
    "all_candidate_metadata_filter_references_match",
    "all_candidate_score_references_declared",
    "all_selected_match_candidates",
    "all_selected_active_index_versions_match",
    "all_selected_metadata_filter_references_match",
    "all_selected_ranking_policies_match",
    "all_score_explanations_declared",
    "all_trace_active_index_versions_match",
    "all_trace_metadata_filter_references_match",
    "all_trace_candidate_and_selected_sets_match",
    "all_trace_score_references_match",
    "all_evidence_ledger_bindings_declared",
    "all_result_validity_gate_reference_chains_match",
    "all_result_validity_gates_pending_human_whitebox_review",
    "all_system_output_only_acceptance_rejected",
)

SCENARIO_RESULT_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenarios",
    "query_ref",
    "query_kind",
    "requested_top_k_ref",
    "metadata_filter_refs",
    "candidate_chunk_ref",
    "selected_chunk_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
    "retrieval_trace_ref",
    "validity_gate_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
    "active_index_version_ref",
    "evidence_ledger_ref",
    "observed_keyword_baseline_state",
    "observed_vector_baseline_state",
    "observed_vector_only_rejected",
    "observed_semantic_similarity_state",
    "observed_filter_combination_state",
    "observed_top_k_state",
    "observed_ranking_explanation_state",
    "observed_result_validity_state",
    "observed_validity_gate_state",
    "observed_old_index_trace_state",
    "human_handling_required",
    "business_line_whitebox_human_approval_recorded",
    "explicit_disposition",
    "silent_drop",
    "expectation_met",
)

SCENARIOS = (
    {
        "scenario_id": "keyword_baseline_control",
        "scenario_category": "KEYWORD_BASELINE_CONTROL",
        "phase2_control_scenarios": (
            "keyword_document_type_filter_reference_only",
        ),
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_KEYWORD_BASELINE_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "material_grade_keyword_control",
        "scenario_category": "MATERIAL_GRADE_KEYWORD_CONTROL",
        "phase2_control_scenarios": ("keyword_year_filter_reference_only",),
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_MATERIAL_GRADE_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "equipment_model_hybrid_control",
        "scenario_category": "EQUIPMENT_MODEL_HYBRID_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_equipment_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_EQUIPMENT_MODEL_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "standard_number_hybrid_control",
        "scenario_category": "STANDARD_NUMBER_HYBRID_CONTROL",
        "phase2_control_scenarios": ("hybrid_project_filter_reference_only",),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_STANDARD_NUMBER_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "semantic_similarity_hybrid_control",
        "scenario_category": "SEMANTIC_SIMILARITY_HYBRID_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_evidence_level_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_SEMANTIC_SIMILARITY_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "six_dimension_filter_combination_control",
        "scenario_category": "SIX_DIMENSION_FILTER_COMBINATION_CONTROL",
        "phase2_control_scenarios": P2_SCENARIOS,
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 6,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_SIX_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_SIX_DIMENSION_FILTER_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "top_k_ranking_explanation_result_validity_control",
        "scenario_category": "TOP_K_RANKING_EXPLANATION_VALIDITY_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_metadata_status_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_REFERENCE_DECLARED_NOT_APPLIED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_DECLARED_NOT_APPLIED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED",
        "explicit_disposition": "CONTROL_TOP_K_RANKING_VALIDITY_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
    {
        "scenario_id": "old_index_service_trace_version_control",
        "scenario_category": "OLD_INDEX_SERVICE_TRACE_VERSION_CONTROL",
        "phase2_control_scenarios": ("keyword_year_filter_reference_only",),
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED",
        "expected_filter_combination_state": "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED",
        "expected_top_k_state": "CONTROL_TOP_K_NOT_REQUESTED",
        "expected_ranking_explanation_state": "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED",
        "expected_old_index_trace_state": "CONTROL_OLD_INDEX_VERSION_TRACE_DECLARED_NOT_READ_OR_WRITTEN",
        "explicit_disposition": "CONTROL_OLD_INDEX_TRACE_REQUIRES_BUSINESS_LINE_WHITEBOX",
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name(
        "stage088_retrieval_result_validity_control_slice.py"
    )
    spec = importlib.util.spec_from_file_location("stage088_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage088 P2 retrieval result validity slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_executor(phase2_module: Any) -> Phase2Executor:
    return phase2_module.execute_retrieval_result_validity_control_slice


def _phase2_control_input(phase2_module: Any) -> Mapping[str, object]:
    return phase2_module.build_control_input()


def _runtime_boundary_is_closed(result: Mapping[str, Any]) -> bool:
    boundary = result.get("runtime_boundary")
    return isinstance(boundary, Mapping) and all(
        boundary.get(field) is False for field in RUNTIME_CLOSED_FIELDS
    )


def _phase2_shape_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        result.get("schema_version") != getattr(phase2_module, "SCHEMA_VERSION", None)
        or result.get("record_kind")
        != getattr(phase2_module, "RECORD_KIND", None)
        or getattr(phase2_module, "CONTROL_PREFIX", None) != CONTROL_PREFIX
        or tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ())) != P2_SCENARIOS
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("actual_input_request_count") != 0
        or result.get("persistent_record_created") is not False
        or not _runtime_boundary_is_closed(result)
    ):
        return False
    for output_key, count_key, field_constant in P2_RECORD_SPECS:
        records = result.get(output_key)
        expected_fields = getattr(phase2_module, field_constant, ())
        if (
            not isinstance(records, list)
            or len(records) != len(P2_SCENARIOS)
            or result.get(count_key) != len(P2_SCENARIOS)
            or any(
                not isinstance(record, Mapping)
                or set(record) != set(expected_fields)
                for record in records
            )
        ):
            return False
    return all(result.get(field) is True for field in P2_CHAIN_FLAGS)


def _phase2_field_check_count(phase2_module: Any, result: Mapping[str, Any]) -> int:
    total = 0
    for output_key, _count_key, field_constant in P2_RECORD_SPECS:
        records = result.get(output_key)
        fields = getattr(phase2_module, field_constant, ())
        if not isinstance(records, list):
            return 0
        total += len(records) * len(fields)
    return total


def _control_ref(value: object) -> bool:
    return isinstance(value, str) and CONTROL_PREFIX in value


def _phase2_control_references_are_opaque(result: Mapping[str, Any]) -> bool:
    for output_key, _count_key, _field_constant in P2_RECORD_SPECS:
        records = result.get(output_key)
        if not isinstance(records, list):
            return False
        for record in records:
            if not isinstance(record, Mapping):
                return False
            if any(
                field.endswith("_ref") and not _control_ref(value)
                for field, value in record.items()
            ):
                return False
    return True


def _phase2_result_validity_gate_states_preserved(
    result: Mapping[str, Any],
) -> bool:
    gates = result.get("result_validity_gate_control_projections")
    return isinstance(gates, list) and len(gates) == len(P2_SCENARIOS) and all(
        isinstance(gate, Mapping)
        and gate.get("observed_result_validity_state")
        == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
        and gate.get("validity_gate_state")
        == "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW"
        for gate in gates
    )


def _scenario_records(
    result: Mapping[str, Any], scenario: str
) -> dict[str, Mapping[str, Any]]:
    index = P2_SCENARIOS.index(scenario)
    records: dict[str, Mapping[str, Any]] = {}
    for output_key, _count_key, _field_constant in P2_RECORD_SPECS:
        projection = result[output_key][index]
        if not isinstance(projection, Mapping):
            raise ValueError(f"invalid {output_key} projection")
        records[output_key] = projection
    return records


def _build_scenario(
    definition: Mapping[str, Any], phase2_result: Mapping[str, Any]
) -> dict[str, Any]:
    source_scenarios = tuple(definition["phase2_control_scenarios"])
    source_records = [
        _scenario_records(phase2_result, item) for item in source_scenarios
    ]
    primary = source_records[-1]
    query = primary["query_control_projections"]
    candidate = primary["candidate_control_projections"]
    score = primary["score_control_projections"]
    selected = primary["selected_control_projections"]
    trace = primary["retrieval_trace_control_projections"]
    active_index = primary["active_index_version_control_projections"]
    gate = primary["result_validity_gate_control_projections"]
    metadata_filter_refs = [
        records["metadata_filter_control_projections"]["filter_ref"]
        for records in source_records
    ]

    scenario_id = definition["scenario_id"]
    is_semantic = scenario_id == "semantic_similarity_hybrid_control"
    is_filter_combination = scenario_id == "six_dimension_filter_combination_control"
    is_top_k = scenario_id == "top_k_ranking_explanation_result_validity_control"
    is_old_index = scenario_id == "old_index_service_trace_version_control"
    result = {
        "scenario_id": scenario_id,
        "scenario_category": definition["scenario_category"],
        "phase2_control_scenarios": list(source_scenarios),
        "query_ref": query["query_ref"],
        "query_kind": query["query_kind"],
        "requested_top_k_ref": query["requested_top_k_ref"],
        "metadata_filter_refs": metadata_filter_refs,
        "candidate_chunk_ref": candidate["candidate_chunk_ref"],
        "selected_chunk_ref": selected["selected_chunk_ref"],
        "hybrid_score_ref": score["hybrid_score_ref"],
        "ranking_policy_ref": score["ranking_policy_ref"],
        "score_explanation_ref": score["score_explanation_ref"],
        "retrieval_trace_ref": trace["trace_ref"],
        "validity_gate_ref": gate["validity_gate_ref"],
        "keyword_retrieval_baseline_ref": query["keyword_retrieval_baseline_ref"],
        "vector_retrieval_baseline_ref": query["vector_retrieval_baseline_ref"],
        "active_index_version_ref": active_index["active_index_version_ref"],
        "evidence_ledger_ref": trace["evidence_ledger_ref"],
        "observed_keyword_baseline_state": (
            "CONTROL_KEYWORD_BASELINE_DECLARED_NOT_EXECUTED"
        ),
        "observed_vector_baseline_state": (
            "CONTROL_VECTOR_BASELINE_DECLARED_NOT_EXECUTED"
        ),
        "observed_vector_only_rejected": True,
        "observed_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED"
            if is_semantic
            else "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "observed_filter_combination_state": (
            "CONTROL_SIX_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED"
            if is_filter_combination
            else "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "observed_top_k_state": (
            "CONTROL_TOP_K_REFERENCE_DECLARED_NOT_APPLIED"
            if is_top_k
            else "CONTROL_TOP_K_NOT_REQUESTED"
        ),
        "observed_ranking_explanation_state": (
            "CONTROL_RANKING_EXPLANATION_DECLARED_NOT_APPLIED"
            if is_top_k
            else "CONTROL_RANKING_EXPLANATION_NOT_REQUESTED"
        ),
        "observed_result_validity_state": gate["observed_result_validity_state"],
        "observed_validity_gate_state": gate["validity_gate_state"],
        "observed_old_index_trace_state": (
            "CONTROL_OLD_INDEX_VERSION_TRACE_DECLARED_NOT_READ_OR_WRITTEN"
            if is_old_index
            else "CONTROL_OLD_INDEX_TRACE_NOT_REQUESTED"
        ),
        "human_handling_required": True,
        "business_line_whitebox_human_approval_recorded": False,
        "explicit_disposition": definition["explicit_disposition"],
        "silent_drop": False,
        "expectation_met": False,
    }
    opaque_references = (
        result["query_ref"],
        result["requested_top_k_ref"],
        result["candidate_chunk_ref"],
        result["selected_chunk_ref"],
        result["hybrid_score_ref"],
        result["ranking_policy_ref"],
        result["score_explanation_ref"],
        result["retrieval_trace_ref"],
        result["validity_gate_ref"],
        result["keyword_retrieval_baseline_ref"],
        result["vector_retrieval_baseline_ref"],
        result["active_index_version_ref"],
        result["evidence_ledger_ref"],
        *result["metadata_filter_refs"],
    )
    result["expectation_met"] = (
        result["query_kind"] == definition["expected_query_kind"]
        and len(result["metadata_filter_refs"])
        == definition["expected_filter_reference_count"]
        and all(_control_ref(value) for value in opaque_references)
        and result["observed_vector_only_rejected"] is True
        and result["observed_semantic_similarity_state"]
        == definition["expected_semantic_similarity_state"]
        and result["observed_filter_combination_state"]
        == definition["expected_filter_combination_state"]
        and result["observed_top_k_state"] == definition["expected_top_k_state"]
        and result["observed_ranking_explanation_state"]
        == definition["expected_ranking_explanation_state"]
        and result["observed_result_validity_state"]
        == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
        and result["observed_validity_gate_state"]
        == "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW"
        and result["observed_old_index_trace_state"]
        == definition["expected_old_index_trace_state"]
        and result["human_handling_required"] is True
        and result["business_line_whitebox_human_approval_recorded"] is False
        and bool(result["explicit_disposition"])
        and result["silent_drop"] is False
    )
    return result


def _all_control_references_opaque(scenarios: list[Mapping[str, Any]]) -> bool:
    reference_fields = (
        "query_ref",
        "requested_top_k_ref",
        "candidate_chunk_ref",
        "selected_chunk_ref",
        "hybrid_score_ref",
        "ranking_policy_ref",
        "score_explanation_ref",
        "retrieval_trace_ref",
        "validity_gate_ref",
        "keyword_retrieval_baseline_ref",
        "vector_retrieval_baseline_ref",
        "active_index_version_ref",
        "evidence_ledger_ref",
    )
    return all(
        all(_control_ref(scenario[field]) for field in reference_fields)
        and isinstance(scenario["metadata_filter_refs"], list)
        and all(_control_ref(value) for value in scenario["metadata_filter_refs"])
        for scenario in scenarios
    )


def _failure_state(
    phase2_is_mapping: bool,
    phase2_result: Mapping[str, Any],
    phase2_shape_preserved: bool,
    phase2_side_effect_free: bool,
    phase2_control_references_opaque: bool,
    phase2_gate_states_preserved: bool,
    scenario_results: list[Mapping[str, Any]],
) -> str:
    if not phase2_is_mapping:
        return "PHASE2_CONTROL_OUTPUT_INVALID"
    if not phase2_side_effect_free:
        return "PHASE2_RUNTIME_SIGNAL_DETECTED"
    if (
        phase2_result.get("all_result_validity_gate_reference_chains_match")
        is not True
    ):
        return "RESULT_VALIDITY_CHAIN_MISSING"
    if (
        phase2_result.get("all_result_validity_gates_pending_human_whitebox_review")
        is not True
        or not phase2_gate_states_preserved
    ):
        return "VALIDITY_GATE_NOT_PENDING_HUMAN_WHITEBOX"
    if not phase2_shape_preserved:
        return "PHASE2_CONTROL_SHAPE_MISMATCH"
    if not phase2_control_references_opaque:
        return "CONTROL_REFERENCE_NOT_OPAQUE"
    if phase2_result.get("all_keyword_baselines_declared") is not True:
        return "KEYWORD_BASELINE_MISSING"
    if phase2_result.get("all_vector_baselines_declared") is not True:
        return "VECTOR_BASELINE_MISSING"
    if phase2_result.get("all_vector_similarity_only_routes_rejected") is not True:
        return "VECTOR_ONLY_ROUTE_DETECTED"
    if phase2_result.get("all_six_metadata_filter_dimensions_covered") is not True:
        return "SIX_DIMENSION_FILTER_COMBINATION_INCOMPLETE"
    if phase2_result.get("all_active_index_version_contracts_match") is not True:
        return "ACTIVE_INDEX_VERSION_CONTRACT_MISMATCH"
    if (
        phase2_result.get("all_selected_ranking_policies_match") is not True
        or phase2_result.get("all_score_explanations_declared") is not True
    ):
        return "TOP_K_OR_RANKING_EXPLANATION_MISSING"
    if phase2_result.get("all_trace_active_index_versions_match") is not True:
        return "OLD_INDEX_TRACE_VERSION_MISMATCH"
    if not all(item.get("expectation_met") is True for item in scenario_results):
        return "SCENARIO_EXPECTATION_MISMATCH"
    return "PHASE3_CONTROLLED_SCENARIOS_NOT_AUTHORIZED"


def build_retrieval_result_validity_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2 固定控制投影；任何偏离均保持在 P3 门失败关闭。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    phase2_output = executor(_phase2_control_input(phase2_module))
    phase2_is_mapping = isinstance(phase2_output, Mapping)
    phase2_result: Mapping[str, Any] = phase2_output if phase2_is_mapping else {}
    phase2_shape_preserved = _phase2_shape_preserved(phase2_module, phase2_result)
    phase2_side_effect_free = _runtime_boundary_is_closed(phase2_result) and (
        phase2_result.get("actual_input_request_count") == 0
        and phase2_result.get("persistent_record_created") is False
    )
    phase2_control_references_opaque = _phase2_control_references_are_opaque(
        phase2_result
    )
    phase2_gate_states_preserved = _phase2_result_validity_gate_states_preserved(
        phase2_result
    )
    prerequisites_hold = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and phase2_control_references_opaque
        and phase2_gate_states_preserved
    )
    scenario_results = (
        [_build_scenario(definition, phase2_result) for definition in SCENARIOS]
        if prerequisites_hold
        else []
    )
    source_scenarios = {
        source
        for scenario in scenario_results
        for source in scenario["phase2_control_scenarios"]
    }
    all_control_references_opaque = _all_control_references_opaque(scenario_results)
    keyword_and_domain_coverage_preserved = (
        source_scenarios == set(P2_SCENARIOS)
        and phase2_result.get("all_keyword_baselines_declared") is True
        and phase2_result.get("all_vector_baselines_declared") is True
        and phase2_result.get("all_vector_similarity_only_routes_rejected") is True
    )
    six_dimension_filter_combination_preserved = (
        phase2_result.get("all_six_metadata_filter_dimensions_covered") is True
        and phase2_result.get("all_candidate_metadata_filter_references_match") is True
        and phase2_result.get("all_selected_metadata_filter_references_match") is True
        and phase2_result.get("all_trace_metadata_filter_references_match") is True
    )
    active_index_version_chain_preserved = (
        phase2_result.get("all_active_index_version_contracts_match") is True
        and phase2_result.get("all_candidate_active_index_versions_match") is True
        and phase2_result.get("all_selected_active_index_versions_match") is True
        and phase2_result.get("all_trace_active_index_versions_match") is True
    )
    top_k_ranking_and_validity_preserved = (
        phase2_result.get("all_selected_match_candidates") is True
        and phase2_result.get("all_selected_ranking_policies_match") is True
        and phase2_result.get("all_score_explanations_declared") is True
        and all(
            item["observed_top_k_state"]
            == definition["expected_top_k_state"]
            and item["observed_ranking_explanation_state"]
            == definition["expected_ranking_explanation_state"]
            for item, definition in zip(scenario_results, SCENARIOS)
        )
    )
    result_validity_gate_chain_preserved = (
        phase2_result.get("all_result_validity_gate_reference_chains_match") is True
        and phase2_result.get("all_result_validity_gates_pending_human_whitebox_review")
        is True
        and all(
            item["observed_result_validity_state"]
            == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
            and item["observed_validity_gate_state"]
            == "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW"
            for item in scenario_results
        )
    )
    old_index_trace_version_preserved = (
        active_index_version_chain_preserved
        and phase2_result.get("all_trace_candidate_and_selected_sets_match") is True
        and all(
            item["observed_old_index_trace_state"]
            == definition["expected_old_index_trace_state"]
            for item, definition in zip(scenario_results, SCENARIOS)
        )
    )
    all_result_validity_states_not_evaluated = all(
        item["observed_result_validity_state"]
        == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
        for item in scenario_results
    )
    all_validity_gates_pending_human_whitebox = all(
        item["observed_validity_gate_state"]
        == "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW"
        for item in scenario_results
    )
    all_business_line_handling_required = all(
        item["human_handling_required"] is True
        and item["business_line_whitebox_human_approval_recorded"] is False
        and item["silent_drop"] is False
        and bool(item["explicit_disposition"])
        for item in scenario_results
    )
    all_scenarios_expectations_met = all(
        item["expectation_met"] is True for item in scenario_results
    )
    valid = (
        prerequisites_hold
        and len(scenario_results) == len(SCENARIOS)
        and keyword_and_domain_coverage_preserved
        and six_dimension_filter_combination_preserved
        and active_index_version_chain_preserved
        and top_k_ranking_and_validity_preserved
        and result_validity_gate_chain_preserved
        and old_index_trace_version_preserved
        and all_result_validity_states_not_evaluated
        and all_validity_gates_pending_human_whitebox
        and all_business_line_handling_required
        and all_scenarios_expectations_met
        and all_control_references_opaque
    )
    failure_state = (
        None
        if valid
        else _failure_state(
            phase2_is_mapping,
            phase2_result,
            phase2_shape_preserved,
            phase2_side_effect_free,
            phase2_control_references_opaque,
            phase2_gate_states_preserved,
            scenario_results,
        )
    )
    runtime_closed_flags = {field: False for field in RUNTIME_CLOSED_FIELDS}
    phase2_field_check_count = _phase2_field_check_count(phase2_module, phase2_result)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "failure_state": failure_state,
        "next_gate": NEXT_GATE if valid else CURRENT_GATE,
        "phase2_control_slice_replayed": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "phase2_side_effect_free": phase2_side_effect_free,
        "phase2_control_references_opaque": phase2_control_references_opaque,
        "phase2_control_record_field_check_count": phase2_field_check_count,
        "phase2_control_projection_field_total": phase2_field_check_count,
        "scenario_results": scenario_results,
        "scenario_count": len(scenario_results),
        "scenario_field_count": len(SCENARIO_RESULT_FIELDS),
        "scenario_field_check_count": len(SCENARIO_RESULT_FIELDS)
        * len(scenario_results),
        "passed_scenario_count": sum(
            1 for scenario in scenario_results if scenario["expectation_met"]
        ),
        "explicit_disposition_count": sum(
            1 for scenario in scenario_results if scenario["explicit_disposition"]
        ),
        "silent_drop_count": sum(
            1 for scenario in scenario_results if scenario["silent_drop"]
        ),
        "human_handling_required_count": sum(
            1 for scenario in scenario_results if scenario["human_handling_required"]
        ),
        "keyword_and_domain_coverage_preserved": keyword_and_domain_coverage_preserved,
        "six_dimension_filter_combination_preserved": (
            six_dimension_filter_combination_preserved
        ),
        "active_index_version_chain_preserved": active_index_version_chain_preserved,
        "top_k_ranking_and_validity_preserved": top_k_ranking_and_validity_preserved,
        "result_validity_gate_chain_preserved": result_validity_gate_chain_preserved,
        "old_index_trace_version_preserved": old_index_trace_version_preserved,
        "all_result_validity_states_not_evaluated": (
            all_result_validity_states_not_evaluated
        ),
        "all_validity_gates_pending_human_whitebox": (
            all_validity_gates_pending_human_whitebox
        ),
        "all_business_line_handling_required": all_business_line_handling_required,
        "all_scenarios_expectations_met": all_scenarios_expectations_met,
        "all_control_references_opaque": all_control_references_opaque,
        "actual_input_request_count": 0,
        "actual_keyword_retrieval_query_count": 0,
        "actual_vector_retrieval_query_count": 0,
        "actual_embedding_generation_count": 0,
        "actual_material_grade_lookup_count": 0,
        "actual_equipment_model_lookup_count": 0,
        "actual_standard_number_lookup_count": 0,
        "actual_semantic_similarity_calculation_count": 0,
        "actual_metadata_filter_evaluation_count": 0,
        "actual_top_k_selection_count": 0,
        "actual_hybrid_ranking_count": 0,
        "actual_retrieval_trace_access_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_old_index_service_access_count": 0,
        "actual_result_validity_evaluation_count": 0,
        "source_document_remains_authoritative": True,
        "control_scenario_can_replace_source_document": False,
        "control_result_can_become_business_fact_authority": False,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_business_recommendation_allowed": False,
        "automatic_business_write_allowed": False,
        "automatic_index_switch_allowed": False,
        "automatic_parameter_write_allowed": False,
        "stage087_review_evidence_declared": True,
        "stage088_started": True,
        "stage088_entry_authorized": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_started": False,
        "whole_stage_review_performed": False,
        "stage089_started": False,
        "ovh_started": False,
        "production_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本次只重放固定控制引用，未读取业务资料或执行真实检索、排序、结果有效性判定。",
            "材料牌号、设备型号、标准号与语义相似只作为场景类别；所有 query、filter、chunk、评分、版本、trace 和结果有效性门禁均为控制标签。",
            "结果有效性保持未评估，所有门禁保持待业务线白箱人工复核；不形成自动业务结论。",
            "Top-K、旧索引服务版本轨迹、自动切换、参数写入、OVH、生产和上传均未启动。",
        ],
    }
