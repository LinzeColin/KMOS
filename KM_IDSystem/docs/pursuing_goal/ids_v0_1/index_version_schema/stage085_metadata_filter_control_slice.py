"""Stage085 P2 的纯内存元数据过滤控制切片。

模块只接受六条固定、非业务、reference-only 控制请求，并在内存中投影关键词／
向量基线、六类元数据过滤、候选、混合评分、选择结果、检索轨迹、向量模型版本、
维度、相似度度量和证据账本引用。它不读取业务资料，不连接数据库，不建立 FTS
或 pgvector 索引，不生成 embedding，不执行查询、过滤、排序、Top-K、轨迹或证据
账本读写，也不选择或调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "ids.stage085.metadata_filter.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_METADATA_FILTER"
CONTROL_ADAPTER_VERSION = "ids.metadata_filter.control_adapter.v0_1.stage085.p2"
CONTROL_FIELDS = ("metadata_filter_control_requests",)

QUERY_FIELDS = (
    "query_ref",
    "query_text_ref",
    "query_language_ref",
    "query_kind",
    "requested_top_k",
    "embedding_model_ref",
    "embedding_model_version_ref",
    "vector_dimension_ref",
    "similarity_metric_ref",
    "active_index_version_ref",
    "query_state",
)
METADATA_FILTER_CONTRACT_FIELDS = (
    "document_type_filter_ref",
    "year_filter_ref",
    "project_filter_ref",
    "equipment_filter_ref",
    "metadata_status_filter_ref",
    "evidence_level_filter_ref",
    "filter_state",
)
METADATA_FILTER_PROJECTION_FIELDS = (
    "filter_ref",
    *METADATA_FILTER_CONTRACT_FIELDS,
)
CANDIDATE_FIELDS = (
    "candidate_ref",
    "candidate_rank",
    "document_ref",
    "chunk_ref",
    "metadata_filter_ref",
    "keyword_score_ref",
    "vector_score_ref",
    "embedding_model_version_ref",
    "similarity_metric_ref",
    "active_index_version_ref",
    "candidate_state",
)
HYBRID_SCORE_FIELDS = (
    "keyword_score_ref",
    "vector_score_ref",
    "metadata_filter_match_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
    "ranking_state",
)
SELECTED_RESULT_FIELDS = (
    "selected_result_ref",
    "selected_rank",
    "candidate_ref",
    "metadata_filter_ref",
    "hybrid_score_ref",
    "score_explanation_ref",
    "evidence_ledger_ref",
    "selection_state",
)
RETRIEVAL_TRACE_FIELDS = (
    "trace_ref",
    "query_ref",
    "filter_ref",
    "candidate_set_ref",
    "selected_result_set_ref",
    "embedding_model_version_ref",
    "similarity_metric_ref",
    "active_index_version_ref",
    "evidence_ledger_ref",
    "trace_state",
)
FUTURE_INTEGRATION_FIELDS = (
    "postgresql_fts_bm25_route_ref",
    "pgvector_route_ref",
    "metadata_filter_route_ref",
    "hybrid_ranking_route_ref",
    "retrieval_trace_route_ref",
    "integration_state",
)
INPUT_FIELDS = (
    "control_scenario",
    *QUERY_FIELDS,
    *METADATA_FILTER_CONTRACT_FIELDS,
    "evidence_ledger_ref",
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

CONTROL_SCENARIOS = (
    "keyword_document_type_filter_reference_only",
    "keyword_year_filter_reference_only",
    "hybrid_project_filter_reference_only",
    "hybrid_equipment_filter_reference_only",
    "hybrid_metadata_status_filter_reference_only",
    "hybrid_evidence_level_filter_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "keyword_document_type_filter_reference_only": {
        "query_kind": "keyword",
        "active_filter_field": "document_type_filter_ref",
    },
    "keyword_year_filter_reference_only": {
        "query_kind": "keyword",
        "active_filter_field": "year_filter_ref",
    },
    "hybrid_project_filter_reference_only": {
        "query_kind": "hybrid",
        "active_filter_field": "project_filter_ref",
    },
    "hybrid_equipment_filter_reference_only": {
        "query_kind": "hybrid",
        "active_filter_field": "equipment_filter_ref",
    },
    "hybrid_metadata_status_filter_reference_only": {
        "query_kind": "hybrid",
        "active_filter_field": "metadata_status_filter_ref",
    },
    "hybrid_evidence_level_filter_reference_only": {
        "query_kind": "hybrid",
        "active_filter_field": "evidence_level_filter_ref",
    },
}


def _marker(scenario: str) -> str:
    return f":control:stage085-p2:{scenario}"


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def build_control_request(scenario: str) -> dict[str, Any]:
    """构造一条固定、无业务含义的 Stage085 P2 控制请求。"""

    config = CONTROL_SCENARIO_CONFIGURATION[scenario]
    marker = _marker(scenario)
    filter_values = {
        field: (
            f"{field.removesuffix('_ref').replace('_', '-')}{marker}:declared"
            if field == config["active_filter_field"]
            else f"{field.removesuffix('_ref').replace('_', '-')}{marker}:not-selected"
        )
        for field in METADATA_FILTER_CONTRACT_FIELDS[:-1]
    }
    return {
        "control_scenario": scenario,
        "query_ref": f"query{marker}",
        "query_text_ref": f"query-text{marker}",
        "query_language_ref": f"query-language{marker}",
        "query_kind": config["query_kind"],
        "requested_top_k": f"requested-top-k{marker}:declared-reference-only",
        "embedding_model_ref": f"embedding-model{marker}:declared-reference-only",
        "embedding_model_version_ref": (
            f"embedding-model-version{marker}:declared-reference-only"
        ),
        "vector_dimension_ref": (
            f"vector-dimension{marker}:declared-reference-only"
        ),
        "similarity_metric_ref": (
            f"similarity-metric{marker}:declared-reference-only"
        ),
        "active_index_version_ref": f"active-index-version{marker}",
        "query_state": "CONTROL_QUERY_DECLARED_NOT_EXECUTED",
        "document_type_filter_ref": filter_values["document_type_filter_ref"],
        "year_filter_ref": filter_values["year_filter_ref"],
        "project_filter_ref": filter_values["project_filter_ref"],
        "equipment_filter_ref": filter_values["equipment_filter_ref"],
        "metadata_status_filter_ref": filter_values["metadata_status_filter_ref"],
        "evidence_level_filter_ref": filter_values["evidence_level_filter_ref"],
        "filter_state": "CONTROL_METADATA_FILTER_DECLARED_NOT_EVALUATED",
        "evidence_ledger_ref": f"evidence-ledger{marker}",
    }


def build_control_input() -> dict[str, list[dict[str, Any]]]:
    """返回完整固定控制输入，供本地聚焦用例与回归使用。"""

    return {
        CONTROL_FIELDS[0]: [
            build_control_request(scenario) for scenario in CONTROL_SCENARIOS
        ]
    }


def _rejected_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "CONTROL_INPUT_REJECTED_METADATA_FILTER_RUNTIME_DISABLED",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_request_count": 0,
        "actual_input_request_count": 0,
        "query_control_projections": [],
        "query_control_projection_count": 0,
        "metadata_filter_control_projections": [],
        "metadata_filter_control_projection_count": 0,
        "candidate_control_projections": [],
        "candidate_control_projection_count": 0,
        "hybrid_score_control_projections": [],
        "hybrid_score_control_projection_count": 0,
        "selected_result_control_projections": [],
        "selected_result_control_projection_count": 0,
        "retrieval_trace_control_projections": [],
        "retrieval_trace_control_projection_count": 0,
        "future_integration_control_projections": [],
        "future_integration_control_projection_count": 0,
        "all_keyword_baselines_declared": False,
        "all_vector_baselines_declared": False,
        "all_vector_similarity_only_routes_rejected": True,
        "all_six_metadata_filter_dimensions_covered": False,
        "all_metadata_status_filter_references_declared": False,
        "all_candidate_active_index_versions_match": False,
        "all_candidate_metadata_filter_references_match": False,
        "all_candidate_vector_contracts_match": False,
        "all_selected_results_match_candidates": False,
        "all_selected_metadata_filter_references_match": False,
        "all_score_explanations_declared": False,
        "all_trace_active_index_versions_match": False,
        "all_trace_metadata_filter_references_match": False,
        "all_trace_vector_contracts_match": False,
        "all_evidence_ledger_bindings_declared": False,
        "runtime_boundary": _runtime_boundary(),
    }


def execute_metadata_filter_control_slice(
    control_input: Mapping[str, object] | object,
) -> dict[str, Any]:
    """在内存中投影固定 Stage085 P2 控制记录，并拒绝任何其他输入。"""

    expected_input = build_control_input()
    if control_input != expected_input:
        return _rejected_result()

    requests = expected_input[CONTROL_FIELDS[0]]
    query_projections: list[dict[str, Any]] = []
    filter_projections: list[dict[str, Any]] = []
    candidate_projections: list[dict[str, Any]] = []
    hybrid_score_projections: list[dict[str, Any]] = []
    selected_result_projections: list[dict[str, Any]] = []
    retrieval_trace_projections: list[dict[str, Any]] = []
    future_integration_projections: list[dict[str, Any]] = []

    for request in requests:
        scenario = request["control_scenario"]
        marker = _marker(scenario)
        filter_ref = f"filter{marker}"
        candidate_ref = f"candidate{marker}"
        candidate_set_ref = f"candidate-set{marker}"
        hybrid_score_ref = f"hybrid-score{marker}"
        score_explanation_ref = f"score-explanation{marker}"

        query_projections.append({field: request[field] for field in QUERY_FIELDS})
        filter_projections.append(
            {
                "filter_ref": filter_ref,
                **{
                    field: request[field]
                    for field in METADATA_FILTER_CONTRACT_FIELDS
                },
            }
        )
        candidate_projections.append(
            {
                "candidate_ref": candidate_ref,
                "candidate_rank": f"candidate-rank{marker}:reference-only",
                "document_ref": f"document{marker}",
                "chunk_ref": f"chunk{marker}",
                "metadata_filter_ref": filter_ref,
                "keyword_score_ref": f"keyword-score{marker}",
                "vector_score_ref": f"vector-score{marker}",
                "embedding_model_version_ref": request["embedding_model_version_ref"],
                "similarity_metric_ref": request["similarity_metric_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "candidate_state": "CONTROL_CANDIDATE_DECLARED_NOT_RETRIEVED",
            }
        )
        hybrid_score_projections.append(
            {
                "keyword_score_ref": f"keyword-score{marker}",
                "vector_score_ref": f"vector-score{marker}",
                "metadata_filter_match_ref": f"filter-match{marker}",
                "hybrid_score_ref": hybrid_score_ref,
                "ranking_policy_ref": f"ranking-policy{marker}",
                "score_explanation_ref": score_explanation_ref,
                "ranking_state": "CONTROL_HYBRID_RANKING_DECLARED_NOT_EXECUTED",
            }
        )
        selected_result_projections.append(
            {
                "selected_result_ref": f"selected-result{marker}",
                "selected_rank": f"selected-rank{marker}:reference-only",
                "candidate_ref": candidate_ref,
                "metadata_filter_ref": filter_ref,
                "hybrid_score_ref": hybrid_score_ref,
                "score_explanation_ref": score_explanation_ref,
                "evidence_ledger_ref": request["evidence_ledger_ref"],
                "selection_state": "CONTROL_SELECTION_DECLARED_NOT_APPLIED",
            }
        )
        retrieval_trace_projections.append(
            {
                "trace_ref": f"retrieval-trace{marker}",
                "query_ref": request["query_ref"],
                "filter_ref": filter_ref,
                "candidate_set_ref": candidate_set_ref,
                "selected_result_set_ref": f"selected-result-set{marker}",
                "embedding_model_version_ref": request["embedding_model_version_ref"],
                "similarity_metric_ref": request["similarity_metric_ref"],
                "active_index_version_ref": request["active_index_version_ref"],
                "evidence_ledger_ref": request["evidence_ledger_ref"],
                "trace_state": "CONTROL_RETRIEVAL_TRACE_DECLARED_NOT_WRITTEN",
            }
        )
        future_integration_projections.append(
            {
                "postgresql_fts_bm25_route_ref": (
                    f"postgresql-fts-bm25{marker}:future-only"
                ),
                "pgvector_route_ref": f"pgvector{marker}:future-only",
                "metadata_filter_route_ref": f"metadata-filter{marker}:future-only",
                "hybrid_ranking_route_ref": f"hybrid-ranking{marker}:future-only",
                "retrieval_trace_route_ref": f"retrieval-trace{marker}:future-only",
                "integration_state": "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
            }
        )

    active_filter_dimensions = {
        CONTROL_SCENARIO_CONFIGURATION[request["control_scenario"]][
            "active_filter_field"
        ]
        for request in requests
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_METADATA_FILTER_CONTROL_SLICE",
        "failure_state": "NONE",
        "control_input_request_count": len(requests),
        "actual_input_request_count": 0,
        "query_control_projections": query_projections,
        "query_control_projection_count": len(query_projections),
        "metadata_filter_control_projections": filter_projections,
        "metadata_filter_control_projection_count": len(filter_projections),
        "candidate_control_projections": candidate_projections,
        "candidate_control_projection_count": len(candidate_projections),
        "hybrid_score_control_projections": hybrid_score_projections,
        "hybrid_score_control_projection_count": len(hybrid_score_projections),
        "selected_result_control_projections": selected_result_projections,
        "selected_result_control_projection_count": len(selected_result_projections),
        "retrieval_trace_control_projections": retrieval_trace_projections,
        "retrieval_trace_control_projection_count": len(retrieval_trace_projections),
        "future_integration_control_projections": future_integration_projections,
        "future_integration_control_projection_count": len(
            future_integration_projections
        ),
        "all_keyword_baselines_declared": all(
            request["query_kind"] in {"keyword", "hybrid"} for request in requests
        ),
        "all_vector_baselines_declared": all(
            request["embedding_model_ref"]
            and request["embedding_model_version_ref"]
            and request["vector_dimension_ref"]
            and request["similarity_metric_ref"]
            for request in requests
        ),
        "all_vector_similarity_only_routes_rejected": True,
        "all_six_metadata_filter_dimensions_covered": active_filter_dimensions
        == set(METADATA_FILTER_CONTRACT_FIELDS[:-1]),
        "all_metadata_status_filter_references_declared": all(
            request["metadata_status_filter_ref"] for request in requests
        ),
        "all_candidate_active_index_versions_match": all(
            candidate["active_index_version_ref"]
            == request["active_index_version_ref"]
            for request, candidate in zip(requests, candidate_projections)
        ),
        "all_candidate_metadata_filter_references_match": all(
            candidate["metadata_filter_ref"] == filter_record["filter_ref"]
            for candidate, filter_record in zip(candidate_projections, filter_projections)
        ),
        "all_candidate_vector_contracts_match": all(
            candidate["embedding_model_version_ref"]
            == request["embedding_model_version_ref"]
            and candidate["similarity_metric_ref"] == request["similarity_metric_ref"]
            for request, candidate in zip(requests, candidate_projections)
        ),
        "all_selected_results_match_candidates": all(
            selected["candidate_ref"] == candidate["candidate_ref"]
            for candidate, selected in zip(
                candidate_projections, selected_result_projections
            )
        ),
        "all_selected_metadata_filter_references_match": all(
            selected["metadata_filter_ref"] == candidate["metadata_filter_ref"]
            for candidate, selected in zip(
                candidate_projections, selected_result_projections
            )
        ),
        "all_score_explanations_declared": all(
            selected["score_explanation_ref"] == score["score_explanation_ref"]
            for score, selected in zip(
                hybrid_score_projections, selected_result_projections
            )
        ),
        "all_trace_active_index_versions_match": all(
            trace["active_index_version_ref"] == request["active_index_version_ref"]
            for request, trace in zip(requests, retrieval_trace_projections)
        ),
        "all_trace_metadata_filter_references_match": all(
            trace["filter_ref"] == filter_record["filter_ref"]
            for trace, filter_record in zip(retrieval_trace_projections, filter_projections)
        ),
        "all_trace_vector_contracts_match": all(
            trace["embedding_model_version_ref"]
            == request["embedding_model_version_ref"]
            and trace["similarity_metric_ref"] == request["similarity_metric_ref"]
            for request, trace in zip(requests, retrieval_trace_projections)
        ),
        "all_evidence_ledger_bindings_declared": all(
            selected["evidence_ledger_ref"] == request["evidence_ledger_ref"]
            and trace["evidence_ledger_ref"] == request["evidence_ledger_ref"]
            for request, selected, trace in zip(
                requests, selected_result_projections, retrieval_trace_projections
            )
        ),
        "runtime_boundary": _runtime_boundary(),
    }
