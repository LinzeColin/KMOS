"""Stage086 P3 的纯内存混合排序受控场景重放。

模块只重放 Stage086 P2 的六条固定控制投影，验证关键词、材料牌号、设备型号、
标准号、语义相似、六维过滤、Top-K、排序解释、结果有效性与旧索引版本轨迹的
控制边界。资料质量、新鲜度和业务模块得分都只是控制标签，模块不读取或计算任何
业务内容。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage086.hybrid_ranking.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_HYBRID_RANKING_SCENARIOS"
PASS_RESULT = "PASS_HYBRID_RANKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_HYBRID_RANKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE086-P4-GATE"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_HYBRID_RANKING_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage086-p2:"
P2_SCENARIOS = (
    "keyword_document_type_filter_reference_only",
    "keyword_year_filter_reference_only",
    "hybrid_project_filter_reference_only",
    "hybrid_equipment_filter_reference_only",
    "hybrid_metadata_status_filter_reference_only",
    "hybrid_evidence_level_filter_reference_only",
)

P2_RECORD_SPECS = (
    (
        "query_control_projections",
        "query_control_projection_count",
        "QUERY_FIELDS",
    ),
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
    (
        "hybrid_score_control_projections",
        "hybrid_score_control_projection_count",
        "HYBRID_SCORE_FIELDS",
    ),
    (
        "selected_result_control_projections",
        "selected_result_control_projection_count",
        "SELECTED_RESULT_FIELDS",
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
    "material_quality_scoring_performed",
    "freshness_scoring_performed",
    "business_module_scoring_performed",
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
    "ovh_access_performed",
    "production_deployment_performed",
    "github_upload_or_push_performed",
)

METADATA_FILTER_REFERENCE_FIELDS = (
    "document_type_filter_ref",
    "year_filter_ref",
    "project_filter_ref",
    "equipment_filter_ref",
    "metadata_status_filter_ref",
    "evidence_level_filter_ref",
)
HYBRID_INPUT_SCORE_FIELDS = (
    "keyword_score_ref",
    "vector_score_ref",
    "material_quality_score_ref",
    "freshness_score_ref",
    "business_module_score_ref",
)

SCENARIO_RESULT_FIELDS = (
    "scenario_id",
    "scenario_category",
    "phase2_control_scenarios",
    "query_ref",
    "query_kind",
    "requested_top_k_ref",
    "metadata_filter_refs",
    "candidate_ref",
    "selected_result_ref",
    "hybrid_score_ref",
    "score_explanation_ref",
    "retrieval_trace_ref",
    "embedding_model_ref",
    "embedding_model_version_ref",
    "vector_dimension_ref",
    "similarity_metric_ref",
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
    "observed_old_index_trace_state",
    "human_handling_required",
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
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_KEYWORD_BASELINE_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "material_grade_keyword_control",
        "scenario_category": "MATERIAL_GRADE_KEYWORD_CONTROL",
        "phase2_control_scenarios": ("keyword_year_filter_reference_only",),
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_MATERIAL_GRADE_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "equipment_model_hybrid_control",
        "scenario_category": "EQUIPMENT_MODEL_HYBRID_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_equipment_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_EQUIPMENT_MODEL_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "standard_number_hybrid_control",
        "scenario_category": "STANDARD_NUMBER_HYBRID_CONTROL",
        "phase2_control_scenarios": ("hybrid_project_filter_reference_only",),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_STANDARD_NUMBER_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "semantic_similarity_hybrid_control",
        "scenario_category": "SEMANTIC_SIMILARITY_HYBRID_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_evidence_level_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_SEMANTIC_SIMILARITY_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "six_dimension_filter_combination_control",
        "scenario_category": "SIX_DIMENSION_FILTER_COMBINATION_CONTROL",
        "phase2_control_scenarios": P2_SCENARIOS,
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 6,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_SIX_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_FILTER_COMBINATION_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "top_k_ranking_explanation_result_validity_control",
        "scenario_category": "TOP_K_RANKING_EXPLANATION_VALIDITY_CONTROL",
        "phase2_control_scenarios": (
            "hybrid_metadata_status_filter_reference_only",
        ),
        "expected_query_kind": "hybrid",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_TOP_K_RANKING_VALIDITY_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
    {
        "scenario_id": "old_index_service_trace_version_control",
        "scenario_category": "OLD_INDEX_SERVICE_TRACE_VERSION_CONTROL",
        "phase2_control_scenarios": ("keyword_year_filter_reference_only",),
        "expected_query_kind": "keyword",
        "expected_filter_reference_count": 1,
        "expected_semantic_similarity_state": (
            "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
        ),
        "expected_filter_combination_state": (
            "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
        ),
        "explicit_disposition": (
            "CONTROL_OLD_INDEX_TRACE_REQUIRES_BUSINESS_LINE_WHITEBOX"
        ),
    },
)

Phase2Executor = Callable[[Mapping[str, object]], Mapping[str, Any]]


def build_hybrid_ranking_phase3_report(
    phase2_executor: Phase2Executor | None = None,
) -> dict[str, Any]:
    """重放 P2，并在内存中验证固定的 Stage086 P3 控制场景。"""

    phase2_module = _load_phase2_module()
    executor = phase2_executor or _phase2_executor(phase2_module)
    raw_phase2_result = executor(_phase2_control_input(phase2_module))
    phase2_result = raw_phase2_result if isinstance(raw_phase2_result, Mapping) else {}
    phase2_shape_preserved = _phase2_shape_preserved(phase2_module, phase2_result)
    phase2_side_effect_free = _phase2_side_effect_free(phase2_module, phase2_result)
    phase2_records = (
        _index_phase2_records(phase2_result) if phase2_shape_preserved else {}
    )
    scenario_results = [
        _evaluate_scenario(
            scenario,
            phase2_records,
            phase2_result,
            phase2_shape_preserved,
            phase2_side_effect_free,
        )
        for scenario in SCENARIOS
    ]
    runtime_closed_flags = _runtime_closed_flags()
    no_runtime_performed = all(
        runtime_closed_flags[field] is False for field in RUNTIME_CLOSED_FIELDS
    )
    category_order_preserved = [
        result["scenario_category"] for result in scenario_results
    ] == [scenario["scenario_category"] for scenario in SCENARIOS]
    all_control_references_opaque = all(
        _scenario_references_are_control_only(result) for result in scenario_results
    )
    keyword_and_domain_coverage_preserved = all(
        _scenario_expectation(scenario_results, scenario_id)
        for scenario_id in (
            "keyword_baseline_control",
            "material_grade_keyword_control",
            "equipment_model_hybrid_control",
            "standard_number_hybrid_control",
            "semantic_similarity_hybrid_control",
        )
    )
    vector_contract_chain_preserved = all(
        result["observed_vector_baseline_state"]
        == "CONTROL_VECTOR_BASELINE_DECLARED_NOT_EXECUTED"
        for result in scenario_results
    )
    six_dimension_filter_combination_preserved = _scenario_expectation(
        scenario_results, "six_dimension_filter_combination_control"
    )
    top_k_ranking_and_validity_preserved = _scenario_expectation(
        scenario_results, "top_k_ranking_explanation_result_validity_control"
    )
    old_index_trace_version_preserved = _scenario_expectation(
        scenario_results, "old_index_service_trace_version_control"
    )
    active_index_version_contract_preserved = (
        phase2_shape_preserved
        and all(
            _active_index_version_contract_declared(
                records["query"],
                records["active_index"],
                records["candidate"],
                records["selected"],
                records["trace"],
                phase2_result,
            )
            for records in phase2_records.values()
        )
    )
    hybrid_input_score_chain_preserved = (
        phase2_shape_preserved
        and all(
            _hybrid_input_score_references_declared(
                records["candidate"], records["score"]
            )
            for records in phase2_records.values()
        )
        and phase2_result.get("all_candidate_hybrid_input_refs_declared") is True
    )
    metadata_status_filter_reference_preserved = (
        phase2_result.get("all_metadata_status_filter_references_declared") is True
        and six_dimension_filter_combination_preserved
    )
    valid = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and no_runtime_performed
        and category_order_preserved
        and all_control_references_opaque
        and keyword_and_domain_coverage_preserved
        and vector_contract_chain_preserved
        and six_dimension_filter_combination_preserved
        and metadata_status_filter_reference_preserved
        and active_index_version_contract_preserved
        and hybrid_input_score_chain_preserved
        and top_k_ranking_and_validity_preserved
        and old_index_trace_version_preserved
        and all(result["expectation_met"] for result in scenario_results)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else "IDS-STAGE086-P3-GATE",
        "phase2_control_slice_reexecuted": True,
        "phase2_shape_preserved": phase2_shape_preserved,
        "phase2_side_effect_free": phase2_side_effect_free,
        "phase2_control_record_field_check_count": _phase2_field_check_count(
            phase2_module, phase2_result
        ),
        "scenario_results": scenario_results,
        "scenario_count": len(scenario_results),
        "scenario_field_count": len(SCENARIO_RESULT_FIELDS),
        "scenario_field_check_count": len(SCENARIO_RESULT_FIELDS)
        * len(scenario_results),
        "passed_scenario_count": sum(
            1 for result in scenario_results if result["expectation_met"]
        ),
        "explicit_disposition_count": sum(
            1 for result in scenario_results if result["explicit_disposition"]
        ),
        "silent_drop_count": sum(
            1 for result in scenario_results if result["silent_drop"]
        ),
        "human_handling_required_count": sum(
            1 for result in scenario_results if result["human_handling_required"]
        ),
        "keyword_and_domain_coverage_preserved": keyword_and_domain_coverage_preserved,
        "vector_contract_chain_preserved": vector_contract_chain_preserved,
        "six_dimension_filter_combination_preserved": (
            six_dimension_filter_combination_preserved
        ),
        "metadata_status_filter_reference_preserved": (
            metadata_status_filter_reference_preserved
        ),
        "active_index_version_contract_preserved": active_index_version_contract_preserved,
        "hybrid_input_score_chain_preserved": hybrid_input_score_chain_preserved,
        "top_k_ranking_and_validity_preserved": top_k_ranking_and_validity_preserved,
        "old_index_trace_version_preserved": old_index_trace_version_preserved,
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
        "actual_material_quality_scoring_count": 0,
        "actual_freshness_scoring_count": 0,
        "actual_business_module_scoring_count": 0,
        "actual_top_k_selection_count": 0,
        "actual_hybrid_ranking_count": 0,
        "actual_retrieval_trace_access_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_old_index_service_access_count": 0,
        "source_document_remains_authoritative": True,
        "control_scenario_can_replace_source_document": False,
        "control_result_can_become_business_fact_authority": False,
        "business_line_whitebox_human_approval_recorded": False,
        "automatic_business_recommendation_allowed": False,
        "automatic_business_write_allowed": False,
        "automatic_index_switch_allowed": False,
        "automatic_parameter_write_allowed": False,
        "stage085_review_evidence_declared": True,
        "stage086_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_started": True,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "stage087_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_closed_flags,
        "chinese_feedback": [
            "本次只重放固定控制引用，未读取业务资料、生成 embedding 或执行真实检索。",
            "材料牌号、设备型号、标准号与语义相似只作为场景类别，资料质量、新鲜度和业务模块得分仅作为控制标签。",
            "六维过滤、Top-K、排序解释、有效性和旧索引版本轨迹只核验控制引用形状，未过滤、评分、排序、选择或写入 trace。",
            "全部场景仍需业务线白箱人工处理，自动推荐、切换和发布保持关闭。",
        ],
    }


def _load_phase2_module() -> Any:
    module_path = Path(__file__).with_name("stage086_hybrid_ranking_control_slice.py")
    spec = importlib.util.spec_from_file_location("stage086_phase2_slice", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage086 P2 hybrid ranking slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_executor(phase2_module: Any) -> Phase2Executor:
    return phase2_module.execute_hybrid_ranking_control_slice


def _phase2_control_input(phase2_module: Any) -> Mapping[str, object]:
    return phase2_module.build_control_input()


def _phase2_shape_preserved(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    if (
        tuple(getattr(phase2_module, "CONTROL_SCENARIOS", ())) != P2_SCENARIOS
        or result.get("input_accepted") is not True
        or result.get("execution_state") != P2_EXECUTION_STATE
        or result.get("failure_state") is not None
        or result.get("actual_input_request_count") != 0
        or result.get("persistent_record_created") is not False
    ):
        return False
    for output_key, count_key, field_constant in P2_RECORD_SPECS:
        records = result.get(output_key)
        expected_fields = getattr(phase2_module, field_constant, ())
        if (
            not isinstance(records, list)
            or result.get(count_key) != len(P2_SCENARIOS)
            or len(records) != len(P2_SCENARIOS)
            or any(
                not isinstance(record, Mapping)
                or set(record) != set(expected_fields)
                for record in records
            )
        ):
            return False
    return all(
        result.get(field) is True
        for field in (
            "all_keyword_baselines_declared",
            "all_vector_baselines_declared",
            "all_vector_similarity_only_routes_rejected",
            "all_six_metadata_filter_dimensions_covered",
            "all_metadata_status_filter_references_declared",
            "all_active_index_version_contracts_match",
            "all_candidate_active_index_versions_match",
            "all_candidate_metadata_filter_references_match",
            "all_candidate_vector_contracts_match",
            "all_candidate_hybrid_input_refs_declared",
            "all_selected_results_match_candidates",
            "all_selected_active_index_versions_match",
            "all_selected_metadata_filter_references_match",
            "all_selected_ranking_policies_match",
            "all_score_explanations_declared",
            "all_trace_active_index_versions_match",
            "all_trace_metadata_filter_references_match",
            "all_trace_vector_contracts_match",
            "all_trace_ranking_policies_match",
            "all_evidence_ledger_bindings_declared",
        )
    )


def _phase2_side_effect_free(phase2_module: Any, result: Mapping[str, Any]) -> bool:
    runtime_boundary = result.get("runtime_boundary")
    return isinstance(runtime_boundary, Mapping) and all(
        runtime_boundary.get(field) is False
        for field in phase2_module.RUNTIME_CLOSED_FIELDS
    )


def _phase2_field_check_count(phase2_module: Any, result: Mapping[str, Any]) -> int:
    if not _phase2_shape_preserved(phase2_module, result):
        return 0
    return sum(
        len(getattr(phase2_module, field_constant)) * len(result[output_key])
        for output_key, _, field_constant in P2_RECORD_SPECS
    )


def _index_phase2_records(
    result: Mapping[str, Any],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    output_keys = {
        "query": "query_control_projections",
        "filter": "metadata_filter_control_projections",
        "active_index": "active_index_version_control_projections",
        "candidate": "candidate_control_projections",
        "score": "hybrid_score_control_projections",
        "selected": "selected_result_control_projections",
        "trace": "retrieval_trace_control_projections",
        "future": "future_integration_control_projections",
    }
    return {
        scenario: {
            record_name: result[output_key][index]
            for record_name, output_key in output_keys.items()
        }
        for index, scenario in enumerate(P2_SCENARIOS)
    }


def _evaluate_scenario(
    scenario: Mapping[str, Any],
    phase2_records: Mapping[str, Mapping[str, Mapping[str, Any]]],
    phase2_result: Mapping[str, Any],
    phase2_shape_preserved: bool,
    phase2_side_effect_free: bool,
) -> dict[str, Any]:
    source_scenarios = tuple(scenario["phase2_control_scenarios"])
    primary = phase2_records.get(source_scenarios[0], {}) if source_scenarios else {}
    query = primary.get("query", {})
    filter_record = primary.get("filter", {})
    active_index = primary.get("active_index", {})
    candidate = primary.get("candidate", {})
    score = primary.get("score", {})
    selected = primary.get("selected", {})
    trace = primary.get("trace", {})
    filter_refs = tuple(
        _text(phase2_records.get(source, {}).get("filter", {}), "filter_ref")
        for source in source_scenarios
    )
    query_ref = _text(query, "query_ref")
    query_kind = _text(query, "query_kind")
    requested_top_k_ref = _text(query, "requested_top_k")
    candidate_ref = _text(candidate, "candidate_ref")
    selected_result_ref = _text(selected, "selected_result_ref")
    hybrid_score_ref = _text(score, "hybrid_score_ref")
    score_explanation_ref = _text(score, "score_explanation_ref")
    retrieval_trace_ref = _text(trace, "trace_ref")
    embedding_model_ref = _text(query, "embedding_model_ref")
    embedding_model_version_ref = _text(query, "embedding_model_version_ref")
    vector_dimension_ref = _text(query, "vector_dimension_ref")
    similarity_metric_ref = _text(query, "similarity_metric_ref")
    active_index_version_ref = _text(query, "active_index_version_ref")
    evidence_ledger_ref = _text(selected, "evidence_ledger_ref")
    keyword_baseline_declared = (
        phase2_shape_preserved
        and phase2_result.get("all_keyword_baselines_declared") is True
        and query_kind in {"keyword", "hybrid"}
    )
    vector_baseline_declared = (
        phase2_shape_preserved
        and phase2_result.get("all_vector_baselines_declared") is True
        and _control_values_are_opaque(
            embedding_model_ref,
            embedding_model_version_ref,
            vector_dimension_ref,
            similarity_metric_ref,
        )
        and embedding_model_version_ref
        == _text(candidate, "embedding_model_version_ref")
        and similarity_metric_ref == _text(candidate, "similarity_metric_ref")
        and embedding_model_version_ref == _text(trace, "embedding_model_version_ref")
        and similarity_metric_ref == _text(trace, "similarity_metric_ref")
        and phase2_result.get("all_candidate_vector_contracts_match") is True
        and phase2_result.get("all_trace_vector_contracts_match") is True
    )
    vector_only_rejected = (
        phase2_shape_preserved
        and phase2_result.get("all_vector_similarity_only_routes_rejected") is True
        and query_kind != "vector"
    )
    metadata_status_filter_declared = (
        bool(_text(filter_record, "metadata_status_filter_ref"))
        and phase2_result.get("all_metadata_status_filter_references_declared")
        is True
    )
    all_six_filter_fields_declared = all(
        all(_text(records["filter"], field) for field in METADATA_FILTER_REFERENCE_FIELDS)
        for records in phase2_records.values()
    )
    semantic_similarity_state = (
        "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED"
        if scenario["scenario_id"] == "semantic_similarity_hybrid_control"
        and keyword_baseline_declared
        and vector_baseline_declared
        and vector_only_rejected
        else "CONTROL_SEMANTIC_SIMILARITY_NOT_REQUESTED"
    )
    filter_combination_state = (
        "CONTROL_SIX_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED"
        if len(filter_refs) == len(P2_SCENARIOS)
        and all(filter_refs)
        and all_six_filter_fields_declared
        and phase2_result.get("all_six_metadata_filter_dimensions_covered") is True
        and metadata_status_filter_declared
        else "CONTROL_FILTER_DIMENSION_DECLARED_NOT_EVALUATED"
    )
    top_k_declared = _control_values_are_opaque(requested_top_k_ref)
    hybrid_input_score_references_declared = _hybrid_input_score_references_declared(
        candidate, score
    ) and phase2_result.get("all_candidate_hybrid_input_refs_declared") is True
    active_index_version_contract_declared = _active_index_version_contract_declared(
        query,
        active_index,
        candidate,
        selected,
        trace,
        phase2_result,
    )
    ranking_explanation_declared = (
        _control_values_are_opaque(
            hybrid_score_ref,
            score_explanation_ref,
            _text(score, "ranking_policy_ref"),
        )
        and score_explanation_ref == _text(selected, "score_explanation_ref")
        and hybrid_score_ref == _text(selected, "hybrid_score_ref")
        and _text(score, "ranking_policy_ref")
        == _text(selected, "ranking_policy_ref")
        and _text(score, "ranking_policy_ref") == _text(trace, "ranking_policy_ref")
        and phase2_result.get("all_selected_ranking_policies_match") is True
        and phase2_result.get("all_trace_ranking_policies_match") is True
        and phase2_result.get("all_score_explanations_declared") is True
    )
    result_validity_declared = (
        candidate_ref == _text(selected, "candidate_ref")
        and _text(candidate, "metadata_filter_ref")
        == _text(selected, "metadata_filter_ref")
        and _text(candidate, "metadata_filter_ref") == _text(filter_record, "filter_ref")
        and _text(trace, "filter_ref") == _text(filter_record, "filter_ref")
        and evidence_ledger_ref == _text(trace, "evidence_ledger_ref")
        and active_index_version_contract_declared
        and hybrid_input_score_references_declared
        and vector_baseline_declared
        and phase2_result.get("all_selected_results_match_candidates") is True
        and phase2_result.get("all_selected_metadata_filter_references_match")
        is True
        and phase2_result.get("all_evidence_ledger_bindings_declared") is True
    )
    old_index_trace_version_declared = (
        _control_values_are_opaque(retrieval_trace_ref)
        and _text(trace, "query_ref") == query_ref
        and active_index_version_contract_declared
        and embedding_model_version_ref == _text(trace, "embedding_model_version_ref")
        and similarity_metric_ref == _text(trace, "similarity_metric_ref")
        and _text(trace, "trace_state")
        == "CONTROL_RETRIEVAL_TRACE_DECLARED_NOT_WRITTEN"
        and phase2_result.get("all_trace_active_index_versions_match") is True
        and phase2_result.get("all_trace_metadata_filter_references_match") is True
        and phase2_result.get("all_trace_vector_contracts_match") is True
        and phase2_result.get("all_trace_ranking_policies_match") is True
        and vector_baseline_declared
    )
    observed_keyword_baseline_state = (
        "CONTROL_KEYWORD_BASELINE_DECLARED_NOT_EXECUTED"
        if keyword_baseline_declared
        else "CONTROL_KEYWORD_BASELINE_MISSING"
    )
    observed_vector_baseline_state = (
        "CONTROL_VECTOR_BASELINE_DECLARED_NOT_EXECUTED"
        if vector_baseline_declared
        else "CONTROL_VECTOR_BASELINE_MISSING"
    )
    observed_top_k_state = (
        "CONTROL_TOP_K_REFERENCE_DECLARED_NOT_APPLIED"
        if top_k_declared
        else "CONTROL_TOP_K_REFERENCE_MISSING"
    )
    observed_ranking_explanation_state = (
        "CONTROL_RANKING_EXPLANATION_DECLARED_NOT_EXECUTED"
        if ranking_explanation_declared
        else "CONTROL_RANKING_EXPLANATION_MISSING"
    )
    observed_result_validity_state = (
        "CONTROL_RESULT_VALIDITY_DECLARED_NOT_EXECUTED"
        if result_validity_declared
        else "CONTROL_RESULT_VALIDITY_MISSING"
    )
    observed_old_index_trace_state = (
        "CONTROL_OLD_INDEX_TRACE_VERSION_MATCH_NOT_WRITTEN"
        if old_index_trace_version_declared
        else "CONTROL_OLD_INDEX_TRACE_VERSION_MISMATCH"
    )
    human_handling_required = phase2_shape_preserved and phase2_side_effect_free
    references_opaque = _scenario_values_are_control_only(
        query_ref,
        requested_top_k_ref,
        filter_refs,
        candidate_ref,
        selected_result_ref,
        hybrid_score_ref,
        score_explanation_ref,
        retrieval_trace_ref,
        embedding_model_ref,
        embedding_model_version_ref,
        vector_dimension_ref,
        similarity_metric_ref,
        active_index_version_ref,
        evidence_ledger_ref,
    )
    expectation_met = (
        phase2_shape_preserved
        and phase2_side_effect_free
        and query_kind == scenario["expected_query_kind"]
        and len(filter_refs) == scenario["expected_filter_reference_count"]
        and keyword_baseline_declared
        and vector_baseline_declared
        and vector_only_rejected
        and metadata_status_filter_declared
        and semantic_similarity_state == scenario["expected_semantic_similarity_state"]
        and filter_combination_state == scenario["expected_filter_combination_state"]
        and top_k_declared
        and hybrid_input_score_references_declared
        and active_index_version_contract_declared
        and ranking_explanation_declared
        and result_validity_declared
        and old_index_trace_version_declared
        and human_handling_required
        and references_opaque
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_category": scenario["scenario_category"],
        "phase2_control_scenarios": source_scenarios,
        "query_ref": query_ref,
        "query_kind": query_kind,
        "requested_top_k_ref": requested_top_k_ref,
        "metadata_filter_refs": filter_refs,
        "candidate_ref": candidate_ref,
        "selected_result_ref": selected_result_ref,
        "hybrid_score_ref": hybrid_score_ref,
        "score_explanation_ref": score_explanation_ref,
        "retrieval_trace_ref": retrieval_trace_ref,
        "embedding_model_ref": embedding_model_ref,
        "embedding_model_version_ref": embedding_model_version_ref,
        "vector_dimension_ref": vector_dimension_ref,
        "similarity_metric_ref": similarity_metric_ref,
        "active_index_version_ref": active_index_version_ref,
        "evidence_ledger_ref": evidence_ledger_ref,
        "observed_keyword_baseline_state": observed_keyword_baseline_state,
        "observed_vector_baseline_state": observed_vector_baseline_state,
        "observed_vector_only_rejected": vector_only_rejected,
        "observed_semantic_similarity_state": semantic_similarity_state,
        "observed_filter_combination_state": filter_combination_state,
        "observed_top_k_state": observed_top_k_state,
        "observed_ranking_explanation_state": observed_ranking_explanation_state,
        "observed_result_validity_state": observed_result_validity_state,
        "observed_old_index_trace_state": observed_old_index_trace_state,
        "human_handling_required": human_handling_required,
        "explicit_disposition": (
            scenario["explicit_disposition"] if human_handling_required else ""
        ),
        "silent_drop": False,
        "expectation_met": expectation_met,
    }


def _active_index_version_contract_declared(
    query: Mapping[str, Any],
    active_index: Mapping[str, Any],
    candidate: Mapping[str, Any],
    selected: Mapping[str, Any],
    trace: Mapping[str, Any],
    phase2_result: Mapping[str, Any],
) -> bool:
    active_index_version_ref = _text(query, "active_index_version_ref")
    index_version_identity_ref = _text(active_index, "index_version_identity_ref")
    index_build_status_ref = _text(active_index, "index_build_status_ref")
    metadata_filter_contract_ref = _text(active_index, "metadata_filter_contract_ref")
    embedding_model_version_ref = _text(query, "embedding_model_version_ref")
    similarity_metric_ref = _text(query, "similarity_metric_ref")
    return (
        _control_values_are_opaque(
            active_index_version_ref,
            index_version_identity_ref,
            index_build_status_ref,
            metadata_filter_contract_ref,
            embedding_model_version_ref,
            similarity_metric_ref,
        )
        and index_build_status_ref.endswith(":not-built")
        and _text(active_index, "activation_state")
        == "CONTROL_ACTIVE_INDEX_VERSION_DECLARED_NOT_ACTIVATED"
        and active_index_version_ref == _text(active_index, "active_index_version_ref")
        and active_index_version_ref == _text(candidate, "active_index_version_ref")
        and active_index_version_ref == _text(selected, "active_index_version_ref")
        and active_index_version_ref == _text(trace, "active_index_version_ref")
        and embedding_model_version_ref
        == _text(active_index, "embedding_model_version_ref")
        and embedding_model_version_ref
        == _text(candidate, "embedding_model_version_ref")
        and embedding_model_version_ref == _text(trace, "embedding_model_version_ref")
        and similarity_metric_ref == _text(active_index, "similarity_metric_ref")
        and similarity_metric_ref == _text(candidate, "similarity_metric_ref")
        and similarity_metric_ref == _text(trace, "similarity_metric_ref")
        and phase2_result.get("all_active_index_version_contracts_match") is True
        and phase2_result.get("all_candidate_active_index_versions_match") is True
        and phase2_result.get("all_selected_active_index_versions_match") is True
        and phase2_result.get("all_trace_active_index_versions_match") is True
    )


def _hybrid_input_score_references_declared(
    candidate: Mapping[str, Any], score: Mapping[str, Any]
) -> bool:
    return (
        all(
            _text(candidate, field) == _text(score, field)
            and _control_values_are_opaque(_text(candidate, field))
            for field in HYBRID_INPUT_SCORE_FIELDS
        )
        and _control_values_are_opaque(
            _text(score, "metadata_filter_match_ref"),
            _text(score, "hybrid_score_ref"),
            _text(score, "ranking_policy_ref"),
            _text(score, "score_explanation_ref"),
        )
    )


def _text(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    return value if isinstance(value, str) else ""


def _control_values_are_opaque(*values: str) -> bool:
    return all(CONTROL_PREFIX in value for value in values)


def _scenario_values_are_control_only(
    query_ref: str,
    requested_top_k_ref: str,
    filter_refs: tuple[str, ...],
    candidate_ref: str,
    selected_result_ref: str,
    hybrid_score_ref: str,
    score_explanation_ref: str,
    retrieval_trace_ref: str,
    embedding_model_ref: str,
    embedding_model_version_ref: str,
    vector_dimension_ref: str,
    similarity_metric_ref: str,
    active_index_version_ref: str,
    evidence_ledger_ref: str,
) -> bool:
    return _control_values_are_opaque(
        query_ref,
        requested_top_k_ref,
        *filter_refs,
        candidate_ref,
        selected_result_ref,
        hybrid_score_ref,
        score_explanation_ref,
        retrieval_trace_ref,
        embedding_model_ref,
        embedding_model_version_ref,
        vector_dimension_ref,
        similarity_metric_ref,
        active_index_version_ref,
        evidence_ledger_ref,
    )


def _scenario_references_are_control_only(result: Mapping[str, Any]) -> bool:
    filter_refs = result.get("metadata_filter_refs")
    return isinstance(filter_refs, tuple) and _scenario_values_are_control_only(
        _text(result, "query_ref"),
        _text(result, "requested_top_k_ref"),
        filter_refs,
        _text(result, "candidate_ref"),
        _text(result, "selected_result_ref"),
        _text(result, "hybrid_score_ref"),
        _text(result, "score_explanation_ref"),
        _text(result, "retrieval_trace_ref"),
        _text(result, "embedding_model_ref"),
        _text(result, "embedding_model_version_ref"),
        _text(result, "vector_dimension_ref"),
        _text(result, "similarity_metric_ref"),
        _text(result, "active_index_version_ref"),
        _text(result, "evidence_ledger_ref"),
    )


def _scenario_expectation(
    scenario_results: list[Mapping[str, Any]], scenario_id: str
) -> bool:
    return any(
        result["scenario_id"] == scenario_id and result["expectation_met"]
        for result in scenario_results
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
