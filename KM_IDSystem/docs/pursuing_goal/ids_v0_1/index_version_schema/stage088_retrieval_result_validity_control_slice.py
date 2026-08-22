"""Stage088 P2 的纯内存检索结果有效性门禁控制切片。

本模块只处理自身定义的固定 reference-only 控制输入；它不读取业务资料，
不连接数据库，不执行检索或结果有效性判定，也不写入任何持久化记录。
"""

from typing import Any, Mapping


SCHEMA_VERSION = "ids.stage088.retrieval_result_validity.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY"
CONTROL_ADAPTER_VERSION = "ids.retrieval_result_validity.control_adapter.v0_1.stage088.p2"
CONTROL_PREFIX = ":control:stage088-p2:"
CONTROL_FIELDS = ("retrieval_result_validity_control_requests",)

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
METADATA_FILTER_PROJECTION_FIELDS = ("filter_ref", *METADATA_FILTER_CONTRACT_FIELDS)
ACTIVE_INDEX_VERSION_FIELDS = (
    "active_index_version_ref",
    "index_version_identity_ref",
    "index_build_status_ref",
    "metadata_filter_contract_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
    "activation_state",
)
CANDIDATE_FIELDS = (
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
SELECTED_FIELDS = (
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
RESULT_VALIDITY_GATE_FIELDS = (
    "validity_gate_ref",
    "query_ref",
    "filter_ref",
    "candidate_chunk_ref",
    "selected_chunk_ref",
    "requested_top_k_ref",
    "keyword_retrieval_baseline_ref",
    "vector_retrieval_baseline_ref",
    "hybrid_score_ref",
    "ranking_policy_ref",
    "score_explanation_ref",
    "active_index_version_ref",
    "retrieval_trace_ref",
    "evidence_ledger_ref",
    "observed_result_validity_state",
    "validity_gate_state",
)
FUTURE_INTEGRATION_FIELDS = (
    "postgresql_fts_bm25_route_ref",
    "pgvector_route_ref",
    "metadata_filter_route_ref",
    "hybrid_ranking_route_ref",
    "retrieval_trace_route_ref",
    "result_validity_gate_route_ref",
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
        "candidate_control_projections": [],
        "candidate_control_projection_count": 0,
        "score_control_projections": [],
        "score_control_projection_count": 0,
        "selected_control_projections": [],
        "selected_control_projection_count": 0,
        "retrieval_trace_control_projections": [],
        "retrieval_trace_control_projection_count": 0,
        "result_validity_gate_control_projections": [],
        "result_validity_gate_control_projection_count": 0,
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
        "execution_state": "REJECTED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE",
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "actual_input_request_count": 0,
        **_empty_projection_result(),
        "runtime_boundary": _runtime_boundary(),
        "persistent_record_created": False,
    }


def execute_retrieval_result_validity_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """投影固定 Stage088 P2 控制记录，并拒绝任何其他输入。"""

    expected_input = build_control_input()
    if control_input != expected_input:
        return _rejected_result()

    requests = expected_input[CONTROL_FIELDS[0]]
    query_projections: list[dict[str, Any]] = []
    filter_projections: list[dict[str, Any]] = []
    active_index_version_projections: list[dict[str, Any]] = []
    candidate_projections: list[dict[str, Any]] = []
    score_projections: list[dict[str, Any]] = []
    selected_projections: list[dict[str, Any]] = []
    retrieval_trace_projections: list[dict[str, Any]] = []
    result_validity_gate_projections: list[dict[str, Any]] = []
    future_integration_projections: list[dict[str, Any]] = []

    for request in requests:
        scenario = request["control_scenario"]
        marker = _marker(scenario)
        filter_ref = f"filter{marker}"
        candidate_chunk_set_ref = f"candidate-chunk-set{marker}"
        candidate_chunk_ref = f"candidate-chunk{marker}"
        selected_chunk_set_ref = f"selected-chunk-set{marker}"
        selected_chunk_ref = f"selected-chunk{marker}"
        hybrid_score_ref = f"hybrid-score{marker}"
        ranking_policy_ref = f"ranking-policy{marker}"
        score_explanation_ref = f"score-explanation{marker}"
        trace_ref = f"retrieval-trace{marker}"

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
        candidate_projections.append(
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
                "candidate_state": "CONTROL_CANDIDATE_DECLARED_NOT_RETRIEVED",
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
        selected_projections.append(
            {
                "selected_chunk_set_ref": selected_chunk_set_ref,
                "selected_chunk_ref": selected_chunk_ref,
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
                "trace_ref": trace_ref,
                "query_ref": request["query_ref"],
                "filter_ref": filter_ref,
                "candidate_chunk_set_ref": candidate_chunk_set_ref,
                "selected_chunk_set_ref": selected_chunk_set_ref,
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
        result_validity_gate_projections.append(
            {
                "validity_gate_ref": f"result-validity-gate{marker}",
                "query_ref": request["query_ref"],
                "filter_ref": filter_ref,
                "candidate_chunk_ref": candidate_chunk_ref,
                "selected_chunk_ref": selected_chunk_ref,
                "requested_top_k_ref": request["requested_top_k_ref"],
                "keyword_retrieval_baseline_ref": request[
                    "keyword_retrieval_baseline_ref"
                ],
                "vector_retrieval_baseline_ref": request[
                    "vector_retrieval_baseline_ref"
                ],
                "hybrid_score_ref": hybrid_score_ref,
                "ranking_policy_ref": ranking_policy_ref,
                "score_explanation_ref": score_explanation_ref,
                "active_index_version_ref": request["active_index_version_ref"],
                "retrieval_trace_ref": trace_ref,
                "evidence_ledger_ref": request["evidence_ledger_ref"],
                "observed_result_validity_state": "CONTROL_RESULT_VALIDITY_NOT_EVALUATED",
                "validity_gate_state": "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW",
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
                "result_validity_gate_route_ref": (
                    f"result-validity-gate-route{marker}:future-only"
                ),
                "integration_state": "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": "COMPLETED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE",
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
        "candidate_control_projections": candidate_projections,
        "candidate_control_projection_count": len(candidate_projections),
        "score_control_projections": score_projections,
        "score_control_projection_count": len(score_projections),
        "selected_control_projections": selected_projections,
        "selected_control_projection_count": len(selected_projections),
        "retrieval_trace_control_projections": retrieval_trace_projections,
        "retrieval_trace_control_projection_count": len(retrieval_trace_projections),
        "result_validity_gate_control_projections": result_validity_gate_projections,
        "result_validity_gate_control_projection_count": len(
            result_validity_gate_projections
        ),
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
            for request, candidate in zip(requests, candidate_projections)
        ),
        "all_candidate_metadata_filter_references_match": all(
            candidate["metadata_filter_ref"] == filter_record["filter_ref"]
            for candidate, filter_record in zip(candidate_projections, filter_projections)
        ),
        "all_candidate_score_references_declared": all(
            all(
                candidate[field]
                for field in (
                    "keyword_score_ref",
                    "vector_score_ref",
                    "hybrid_score_ref",
                )
            )
            for candidate in candidate_projections
        ),
        "all_selected_match_candidates": all(
            selected["candidate_chunk_ref"] == candidate["candidate_chunk_ref"]
            for selected, candidate in zip(selected_projections, candidate_projections)
        ),
        "all_selected_active_index_versions_match": all(
            selected["active_index_version_ref"] == candidate["active_index_version_ref"]
            for selected, candidate in zip(selected_projections, candidate_projections)
        ),
        "all_selected_metadata_filter_references_match": all(
            selected["metadata_filter_ref"] == candidate["metadata_filter_ref"]
            for selected, candidate in zip(selected_projections, candidate_projections)
        ),
        "all_selected_ranking_policies_match": all(
            selected["ranking_policy_ref"] == score["ranking_policy_ref"]
            for selected, score in zip(selected_projections, score_projections)
        ),
        "all_score_explanations_declared": all(
            selected["score_explanation_ref"] == score["score_explanation_ref"]
            for selected, score in zip(selected_projections, score_projections)
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
                candidate_projections,
                selected_projections,
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
        "all_result_validity_gate_reference_chains_match": all(
            gate["query_ref"] == request["query_ref"]
            and gate["filter_ref"] == filter_record["filter_ref"]
            and gate["candidate_chunk_ref"] == candidate["candidate_chunk_ref"]
            and gate["selected_chunk_ref"] == selected["selected_chunk_ref"]
            and gate["hybrid_score_ref"] == score["hybrid_score_ref"]
            and gate["ranking_policy_ref"] == score["ranking_policy_ref"]
            and gate["score_explanation_ref"] == score["score_explanation_ref"]
            and gate["active_index_version_ref"] == request["active_index_version_ref"]
            and gate["retrieval_trace_ref"] == trace["trace_ref"]
            and gate["evidence_ledger_ref"] == request["evidence_ledger_ref"]
            for request, filter_record, candidate, score, selected, trace, gate in zip(
                requests,
                filter_projections,
                candidate_projections,
                score_projections,
                selected_projections,
                retrieval_trace_projections,
                result_validity_gate_projections,
            )
        ),
        "all_result_validity_gates_pending_human_whitebox_review": all(
            gate["observed_result_validity_state"]
            == "CONTROL_RESULT_VALIDITY_NOT_EVALUATED"
            and gate["validity_gate_state"]
            == "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW"
            for gate in result_validity_gate_projections
        ),
        "all_system_output_only_acceptance_rejected": True,
        "runtime_boundary": _runtime_boundary(),
        "persistent_record_created": False,
    }
