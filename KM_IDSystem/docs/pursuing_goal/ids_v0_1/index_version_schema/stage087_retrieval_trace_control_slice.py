"""Stage087 P2 的纯内存检索轨迹控制切片。

模块只接受六条固定、非业务、reference-only 控制请求，并在内存中投影未来关键词／
向量基线、六类元数据过滤、活动索引版本、candidate chunks、score、selected chunks、
检索轨迹和未来运行路线。它不读取业务资料，不连接数据库，不建立 FTS 或 pgvector
索引，不生成 embedding，不执行查询、过滤、评分、排序、Top-K、轨迹或证据账本读写，
也不选择或调用模型。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "ids.stage087.retrieval_trace.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_TRACE"
CONTROL_ADAPTER_VERSION = "ids.retrieval_trace.control_adapter.v0_1.stage087.p2"
CONTROL_PREFIX = ":control:stage087-p2:"
CONTROL_FIELDS = ("retrieval_trace_control_requests",)

QUERY_FIELDS = (
    "query_ref",
    "query_text_ref",
    "query_language_ref",
    "query_kind",
    "requested_top_k_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
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
ACTIVE_INDEX_VERSION_FIELDS = (
    "active_index_version_ref",
    "index_version_identity_ref",
    "index_build_status_ref",
    "metadata_filter_contract_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
    "activation_state",
)
CANDIDATE_CHUNK_FIELDS = (
    "candidate_chunk_set_ref",
    "candidate_chunk_ref",
    "candidate_rank_ref",
    "document_ref",
    "metadata_filter_ref",
    "keyword_score_ref",
    "vector_score_ref",
    "hybrid_score_ref",
    "active_index_version_ref",
    "candidate_state",
)
SCORE_FIELDS = (
    "keyword_score_ref",
    "vector_score_ref",
    "metadata_filter_match_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
    "score_state",
)
SELECTED_CHUNK_FIELDS = (
    "selected_chunk_set_ref",
    "selected_chunk_ref",
    "selected_rank_ref",
    "candidate_chunk_ref",
    "metadata_filter_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
    "active_index_version_ref",
    "selection_state",
)
RETRIEVAL_TRACE_FIELDS = (
    "trace_ref",
    "query_ref",
    "filter_ref",
    "candidate_chunk_set_ref",
    "selected_chunk_set_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
    "metadata_filter_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
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
    return f"{CONTROL_PREFIX}{scenario}:reference-only"


def _control_ref(kind: str, scenario: str) -> str:
    return f"{kind}{_marker(scenario)}"


def _control_request(scenario: str) -> dict[str, str]:
    """构造一条不含业务事实的固定控制请求。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    return {
        "control_scenario": scenario,
        "query_ref": _control_ref("query", scenario),
        "query_text_ref": _control_ref("query-text", scenario),
        "query_language_ref": _control_ref("query-language", scenario),
        "query_kind": configuration["query_kind"],
        "requested_top_k_ref": _control_ref(
            "requested-top-k:declared-reference-only", scenario
        ),
        "keyword_retrieval_baseline_ref": _control_ref(
            "keyword-retrieval-baseline", scenario
        ),
        "vector_retrieval_baseline_ref": _control_ref(
            "vector-retrieval-baseline", scenario
        ),
        "active_index_version_ref": _control_ref("active-index-version", scenario),
        "query_state": "CONTROL_QUERY_DECLARED_NOT_EXECUTED",
        "document_type_filter_ref": _control_ref("document-type-filter", scenario),
        "year_filter_ref": _control_ref("year-filter", scenario),
        "project_filter_ref": _control_ref("project-filter", scenario),
        "equipment_filter_ref": _control_ref("equipment-filter", scenario),
        "metadata_status_filter_ref": _control_ref(
            "metadata-status-filter", scenario
        ),
        "evidence_level_filter_ref": _control_ref(
            "evidence-level-filter", scenario
        ),
        "filter_state": "CONTROL_FILTER_DECLARED_NOT_EVALUATED",
        "evidence_ledger_ref": _control_ref("evidence-ledger", scenario),
    }


def build_control_input() -> dict[str, list[dict[str, str]]]:
    """返回唯一允许的六条固定控制输入。"""

    return {CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]}


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _empty_projection_result() -> dict[str, Any]:
    return {
        "query_control_projections": [],
        "query_control_projection_count": 0,
        "metadata_filter_control_projections": [],
        "metadata_filter_control_projection_count": 0,
        "active_index_version_control_projections": [],
        "active_index_version_control_projection_count": 0,
        "candidate_chunk_control_projections": [],
        "candidate_chunk_control_projection_count": 0,
        "score_control_projections": [],
        "score_control_projection_count": 0,
        "selected_chunk_control_projections": [],
        "selected_chunk_control_projection_count": 0,
        "retrieval_trace_control_projections": [],
        "retrieval_trace_control_projection_count": 0,
        "future_integration_control_projections": [],
        "future_integration_control_projection_count": 0,
    }


def _rejected_result() -> dict[str, Any]:
    """返回不读取业务输入内容、不产生投影的失败关闭结果。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": "REJECTED_IN_MEMORY_RETRIEVAL_TRACE_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "actual_input_request_count": 0,
        **_empty_projection_result(),
        "runtime_boundary": _runtime_boundary(),
        "persistent_record_created": False,
    }


def execute_retrieval_trace_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """投影固定 Stage087 P2 控制记录，并拒绝任何其他输入。"""

    expected_input = build_control_input()
    if control_input != expected_input:
        return _rejected_result()

    requests = expected_input[CONTROL_FIELDS[0]]
    query_projections: list[dict[str, Any]] = []
    filter_projections: list[dict[str, Any]] = []
    active_index_version_projections: list[dict[str, Any]] = []
    candidate_chunk_projections: list[dict[str, Any]] = []
    score_projections: list[dict[str, Any]] = []
    selected_chunk_projections: list[dict[str, Any]] = []
    retrieval_trace_projections: list[dict[str, Any]] = []
    future_integration_projections: list[dict[str, Any]] = []

    for request in requests:
        scenario = request["control_scenario"]
        marker = _marker(scenario)
        filter_ref = f"filter{marker}"
        candidate_chunk_set_ref = f"candidate-chunk-set{marker}"
        candidate_chunk_ref = f"candidate-chunk{marker}"
        hybrid_score_ref = f"hybrid-score{marker}"
        ranking_policy_ref = f"ranking-policy{marker}"
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
        active_index_version_projections.append(
            {
                "active_index_version_ref": request["active_index_version_ref"],
                "index_version_identity_ref": f"index-version-identity{marker}",
                "index_build_status_ref": f"index-build-status{marker}:not-built",
                "metadata_filter_contract_ref": f"metadata-filter-contract{marker}",
                "keyword_retrieval_baseline_ref": request[
                    "keyword_retrieval_baseline_ref"
                ],
                "vector_retrieval_baseline_ref": request[
                    "vector_retrieval_baseline_ref"
                ],
                "activation_state": "CONTROL_ACTIVE_INDEX_VERSION_DECLARED_NOT_ACTIVATED",
            }
        )
        candidate_chunk_projections.append(
            {
                "candidate_chunk_set_ref": candidate_chunk_set_ref,
                "candidate_chunk_ref": candidate_chunk_ref,
                "candidate_rank_ref": f"candidate-rank{marker}:reference-only",
                "document_ref": f"document{marker}",
                "metadata_filter_ref": filter_ref,
                "keyword_score_ref": f"keyword-score{marker}",
                "vector_score_ref": f"vector-score{marker}",
                "hybrid_score_ref": hybrid_score_ref,
                "active_index_version_ref": request["active_index_version_ref"],
                "candidate_state": "CONTROL_CANDIDATE_CHUNK_DECLARED_NOT_RETRIEVED",
            }
        )
        score_projections.append(
            {
                "keyword_score_ref": f"keyword-score{marker}",
                "vector_score_ref": f"vector-score{marker}",
                "metadata_filter_match_ref": f"filter-match{marker}",
                "hybrid_score_ref": hybrid_score_ref,
                "ranking_policy_ref": ranking_policy_ref,
                "score_explanation_ref": score_explanation_ref,
                "score_state": "CONTROL_SCORE_DECLARED_NOT_CALCULATED",
            }
        )
        selected_chunk_projections.append(
            {
                "selected_chunk_set_ref": f"selected-chunk-set{marker}",
                "selected_chunk_ref": f"selected-chunk{marker}",
                "selected_rank_ref": f"selected-rank{marker}:reference-only",
                "candidate_chunk_ref": candidate_chunk_ref,
                "metadata_filter_ref": filter_ref,
                "hybrid_score_ref": hybrid_score_ref,
                "ranking_policy_ref": ranking_policy_ref,
                "score_explanation_ref": score_explanation_ref,
                "active_index_version_ref": request["active_index_version_ref"],
                "selection_state": "CONTROL_SELECTION_DECLARED_NOT_APPLIED",
            }
        )
        retrieval_trace_projections.append(
            {
                "trace_ref": f"retrieval-trace{marker}",
                "query_ref": request["query_ref"],
                "filter_ref": filter_ref,
                "candidate_chunk_set_ref": candidate_chunk_set_ref,
                "selected_chunk_set_ref": f"selected-chunk-set{marker}",
                "keyword_retrieval_baseline_ref": request[
                    "keyword_retrieval_baseline_ref"
                ],
                "vector_retrieval_baseline_ref": request[
                    "vector_retrieval_baseline_ref"
                ],
                "metadata_filter_ref": filter_ref,
                "hybrid_score_ref": hybrid_score_ref,
                "ranking_policy_ref": ranking_policy_ref,
                "score_explanation_ref": score_explanation_ref,
                "active_index_version_ref": request["active_index_version_ref"],
                "evidence_ledger_ref": request["evidence_ledger_ref"],
                "trace_state": "CONTROL_RETRIEVAL_TRACE_DECLARED_NOT_WRITTEN",
            }
        )
        future_integration_projections.append(
            {
                "postgresql_fts_bm25_route_ref": (
                    f"postgresql-fts-bm25-route{marker}:future-only"
                ),
                "pgvector_route_ref": f"pgvector-route{marker}:future-only",
                "metadata_filter_route_ref": (
                    f"metadata-filter-route{marker}:future-only"
                ),
                "hybrid_ranking_route_ref": (
                    f"hybrid-ranking-route{marker}:future-only"
                ),
                "retrieval_trace_route_ref": (
                    f"retrieval-trace-route{marker}:future-only"
                ),
                "integration_state": "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_RETRIEVAL_TRACE_CONTROL_SLICE",
        "failure_state": None,
        "actual_input_request_count": 0,
        "query_control_projections": query_projections,
        "query_control_projection_count": len(query_projections),
        "metadata_filter_control_projections": filter_projections,
        "metadata_filter_control_projection_count": len(filter_projections),
        "active_index_version_control_projections": active_index_version_projections,
        "active_index_version_control_projection_count": len(
            active_index_version_projections
        ),
        "candidate_chunk_control_projections": candidate_chunk_projections,
        "candidate_chunk_control_projection_count": len(candidate_chunk_projections),
        "score_control_projections": score_projections,
        "score_control_projection_count": len(score_projections),
        "selected_chunk_control_projections": selected_chunk_projections,
        "selected_chunk_control_projection_count": len(selected_chunk_projections),
        "retrieval_trace_control_projections": retrieval_trace_projections,
        "retrieval_trace_control_projection_count": len(retrieval_trace_projections),
        "future_integration_control_projections": future_integration_projections,
        "future_integration_control_projection_count": len(
            future_integration_projections
        ),
        "all_keyword_baselines_declared": all(
            bool(request["keyword_retrieval_baseline_ref"]) for request in requests
        ),
        "all_vector_baselines_declared": all(
            bool(request["vector_retrieval_baseline_ref"]) for request in requests
        ),
        "all_vector_similarity_only_routes_rejected": all(
            request["query_kind"] != "vector" for request in requests
        ),
        "all_six_metadata_filter_dimensions_covered": {
            configuration["active_filter_field"]
            for configuration in CONTROL_SCENARIO_CONFIGURATION.values()
        }
        == set(METADATA_FILTER_CONTRACT_FIELDS[:-1]),
        "all_active_index_version_contracts_match": all(
            version["active_index_version_ref"] == request["active_index_version_ref"]
            and version["keyword_retrieval_baseline_ref"]
            == request["keyword_retrieval_baseline_ref"]
            and version["vector_retrieval_baseline_ref"]
            == request["vector_retrieval_baseline_ref"]
            for request, version in zip(requests, active_index_version_projections)
        ),
        "all_candidate_active_index_versions_match": all(
            candidate["active_index_version_ref"] == request["active_index_version_ref"]
            for request, candidate in zip(requests, candidate_chunk_projections)
        ),
        "all_candidate_metadata_filter_references_match": all(
            candidate["metadata_filter_ref"] == filter_record["filter_ref"]
            for candidate, filter_record in zip(candidate_chunk_projections, filter_projections)
        ),
        "all_candidate_score_references_declared": all(
            all(candidate[field] for field in ("keyword_score_ref", "vector_score_ref", "hybrid_score_ref"))
            for candidate in candidate_chunk_projections
        ),
        "all_selected_chunks_match_candidates": all(
            selected["candidate_chunk_ref"] == candidate["candidate_chunk_ref"]
            for selected, candidate in zip(
                selected_chunk_projections, candidate_chunk_projections
            )
        ),
        "all_selected_active_index_versions_match": all(
            selected["active_index_version_ref"] == candidate["active_index_version_ref"]
            for selected, candidate in zip(
                selected_chunk_projections, candidate_chunk_projections
            )
        ),
        "all_selected_metadata_filter_references_match": all(
            selected["metadata_filter_ref"] == candidate["metadata_filter_ref"]
            for selected, candidate in zip(
                selected_chunk_projections, candidate_chunk_projections
            )
        ),
        "all_selected_ranking_policies_match": all(
            selected["ranking_policy_ref"] == score["ranking_policy_ref"]
            for selected, score in zip(selected_chunk_projections, score_projections)
        ),
        "all_score_explanations_declared": all(
            selected["score_explanation_ref"] == score["score_explanation_ref"]
            for selected, score in zip(selected_chunk_projections, score_projections)
        ),
        "all_trace_active_index_versions_match": all(
            trace["active_index_version_ref"] == request["active_index_version_ref"]
            for trace, request in zip(retrieval_trace_projections, requests)
        ),
        "all_trace_metadata_filter_references_match": all(
            trace["filter_ref"] == filter_record["filter_ref"]
            and trace["metadata_filter_ref"] == filter_record["filter_ref"]
            for trace, filter_record in zip(retrieval_trace_projections, filter_projections)
        ),
        "all_trace_candidate_and_selected_sets_match": all(
            trace["candidate_chunk_set_ref"] == candidate["candidate_chunk_set_ref"]
            and trace["selected_chunk_set_ref"] == selected["selected_chunk_set_ref"]
            for trace, candidate, selected in zip(
                retrieval_trace_projections,
                candidate_chunk_projections,
                selected_chunk_projections,
            )
        ),
        "all_trace_score_references_match": all(
            trace["hybrid_score_ref"] == score["hybrid_score_ref"]
            and trace["ranking_policy_ref"] == score["ranking_policy_ref"]
            and trace["score_explanation_ref"] == score["score_explanation_ref"]
            for trace, score in zip(retrieval_trace_projections, score_projections)
        ),
        "all_evidence_ledger_bindings_declared": all(
            trace["evidence_ledger_ref"] == request["evidence_ledger_ref"]
            for request, trace in zip(requests, retrieval_trace_projections)
        ),
        "runtime_boundary": _runtime_boundary(),
        "persistent_record_created": False,
    }
