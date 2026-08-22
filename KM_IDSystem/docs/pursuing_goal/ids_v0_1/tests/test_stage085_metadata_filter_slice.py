import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE085_PHASE2_METADATA_FILTER_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_slice_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage085_metadata_filter_control_slice.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-085_元数据过滤.md"
)
P1_SCOPE = BASE / "STAGE085_PHASE1_METADATA_FILTER_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage085_metadata_filter_contract.json"
STAGE084_REVIEW = BASE / "STAGE084_STAGE_REVIEW.md"


def load_module():
    spec = importlib.util.spec_from_file_location("stage085_slice", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


slice_module = load_module()


class Stage085MetadataFilterPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = slice_module.build_control_input()
        cls.result = slice_module.execute_metadata_filter_control_slice(
            cls.control_input
        )

    def test_frozen_sources_identity_and_single_authority_are_explicit(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P1_SCOPE,
            P1_CONTRACT,
            STAGE084_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage085.metadata_filter.phase2.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-085", self.contract["stage"])
        self.assertEqual("IDS-STAGE085-P2", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE085-P2", self.contract["task_id"])
        self.assertEqual("ACC-STAGE-085", self.contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_METADATA_FILTER_CONTROL_SLICE_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE085-P3-GATE", self.contract["next_gate"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(self.contract["source_authority"][field])

    def test_fixed_control_input_has_exact_shape_and_six_filter_coverage(self):
        input_contract = self.contract["reference_only_control_input_contract"]
        requests = self.control_input[slice_module.CONTROL_FIELDS[0]]
        self.assertEqual(input_contract["control_request_count"], len(requests))
        self.assertEqual(
            input_contract["fixed_control_scenarios"],
            list(slice_module.CONTROL_SCENARIOS),
        )
        self.assertEqual(input_contract["input_fields"], list(slice_module.INPUT_FIELDS))
        self.assertEqual(
            input_contract["input_field_count"], len(slice_module.INPUT_FIELDS)
        )
        self.assertEqual(input_contract["query_fields"], list(slice_module.QUERY_FIELDS))
        self.assertEqual(
            input_contract["metadata_filter_fields"],
            list(slice_module.METADATA_FILTER_CONTRACT_FIELDS),
        )
        covered_dimensions = set()
        for request in requests:
            scenario = request["control_scenario"]
            with self.subTest(scenario=scenario):
                self.assertEqual(set(slice_module.INPUT_FIELDS), set(request))
                self.assertIn(input_contract["control_prefix"], request["query_ref"])
                self.assertIn(
                    input_contract["control_prefix"], request["evidence_ledger_ref"]
                )
                self.assertIn(request["query_kind"], {"keyword", "hybrid"})
                self.assertNotEqual("vector", request["query_kind"])
                self.assertIn("declared-reference-only", request["requested_top_k"])
                for field in (
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                    "active_index_version_ref",
                    "metadata_status_filter_ref",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(request[field])
                covered_dimensions.add(
                    slice_module.CONTROL_SCENARIO_CONFIGURATION[scenario][
                        "active_filter_field"
                    ]
                )
        self.assertEqual(
            set(slice_module.METADATA_FILTER_CONTRACT_FIELDS[:-1]),
            covered_dimensions,
        )

    def test_control_outputs_have_exact_contract_fields_and_counts(self):
        projection = self.contract["control_projection_contract"]
        self.assertTrue(self.result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_METADATA_FILTER_CONTROL_SLICE",
            self.result["execution_state"],
        )
        self.assertEqual(0, self.result["actual_input_request_count"])
        for output_key, count_key, field_key, field_names in (
            (
                "query_control_projections",
                "query_control_projection_count",
                "query_projection_fields",
                slice_module.QUERY_FIELDS,
            ),
            (
                "metadata_filter_control_projections",
                "metadata_filter_control_projection_count",
                "metadata_filter_projection_fields",
                slice_module.METADATA_FILTER_PROJECTION_FIELDS,
            ),
            (
                "candidate_control_projections",
                "candidate_control_projection_count",
                "candidate_fields",
                slice_module.CANDIDATE_FIELDS,
            ),
            (
                "hybrid_score_control_projections",
                "hybrid_score_control_projection_count",
                "hybrid_score_fields",
                slice_module.HYBRID_SCORE_FIELDS,
            ),
            (
                "selected_result_control_projections",
                "selected_result_control_projection_count",
                "selected_result_fields",
                slice_module.SELECTED_RESULT_FIELDS,
            ),
            (
                "retrieval_trace_control_projections",
                "retrieval_trace_control_projection_count",
                "retrieval_trace_fields",
                slice_module.RETRIEVAL_TRACE_FIELDS,
            ),
            (
                "future_integration_control_projections",
                "future_integration_control_projection_count",
                "future_integration_projection_fields",
                slice_module.FUTURE_INTEGRATION_FIELDS,
            ),
        ):
            with self.subTest(output_key=output_key):
                self.assertEqual(
                    projection["each_projection_count"], self.result[count_key]
                )
                self.assertEqual(list(field_names), projection[field_key])
                for record in self.result[output_key]:
                    self.assertEqual(set(field_names), set(record))
        total_fields = sum(
            len(fields)
            for fields in (
                slice_module.QUERY_FIELDS,
                slice_module.METADATA_FILTER_PROJECTION_FIELDS,
                slice_module.CANDIDATE_FIELDS,
                slice_module.HYBRID_SCORE_FIELDS,
                slice_module.SELECTED_RESULT_FIELDS,
                slice_module.RETRIEVAL_TRACE_FIELDS,
                slice_module.FUTURE_INTEGRATION_FIELDS,
            )
        )
        self.assertEqual(
            projection["control_projection_field_total_per_request"], total_fields
        )
        self.assertEqual(
            projection["control_projection_field_total"],
            total_fields * projection["each_projection_count"],
        )

    def test_keyword_vector_filter_and_future_route_controls_hold(self):
        projection = self.contract["control_projection_contract"]
        for field in (
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
        ):
            with self.subTest(field=field):
                self.assertTrue(projection[field])
        for field in (
            "all_keyword_baselines_declared",
            "all_vector_baselines_declared",
            "all_vector_similarity_only_routes_rejected",
            "all_six_metadata_filter_dimensions_covered",
            "all_metadata_status_filter_references_declared",
        ):
            with self.subTest(field=field):
                self.assertTrue(self.result[field])
        for integration in self.result["future_integration_control_projections"]:
            with self.subTest(integration=integration["postgresql_fts_bm25_route_ref"]):
                self.assertIn(
                    "future-only", integration["postgresql_fts_bm25_route_ref"]
                )
                self.assertIn("future-only", integration["pgvector_route_ref"])
                self.assertEqual(
                    "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
                    integration["integration_state"],
                )

    def test_candidate_selected_trace_and_metadata_bindings_match(self):
        for request, filter_record, candidate, score, selected, trace in zip(
            self.control_input[slice_module.CONTROL_FIELDS[0]],
            self.result["metadata_filter_control_projections"],
            self.result["candidate_control_projections"],
            self.result["hybrid_score_control_projections"],
            self.result["selected_result_control_projections"],
            self.result["retrieval_trace_control_projections"],
        ):
            with self.subTest(query=request["query_ref"]):
                self.assertEqual(
                    request["active_index_version_ref"],
                    candidate["active_index_version_ref"],
                )
                self.assertEqual(
                    request["embedding_model_version_ref"],
                    candidate["embedding_model_version_ref"],
                )
                self.assertEqual(
                    request["similarity_metric_ref"],
                    candidate["similarity_metric_ref"],
                )
                self.assertEqual(
                    filter_record["filter_ref"], candidate["metadata_filter_ref"]
                )
                self.assertEqual(candidate["candidate_ref"], selected["candidate_ref"])
                self.assertEqual(
                    candidate["metadata_filter_ref"], selected["metadata_filter_ref"]
                )
                self.assertEqual(
                    score["hybrid_score_ref"], selected["hybrid_score_ref"]
                )
                self.assertEqual(
                    score["score_explanation_ref"], selected["score_explanation_ref"]
                )
                self.assertEqual(
                    request["evidence_ledger_ref"], selected["evidence_ledger_ref"]
                )
                self.assertEqual(request["query_ref"], trace["query_ref"])
                self.assertEqual(filter_record["filter_ref"], trace["filter_ref"])
                self.assertEqual(
                    request["active_index_version_ref"],
                    trace["active_index_version_ref"],
                )
                self.assertEqual(
                    request["embedding_model_version_ref"],
                    trace["embedding_model_version_ref"],
                )
                self.assertEqual(
                    request["similarity_metric_ref"], trace["similarity_metric_ref"]
                )
                self.assertEqual(
                    request["evidence_ledger_ref"], trace["evidence_ledger_ref"]
                )
        for field in (
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
        ):
            with self.subTest(field=field):
                self.assertTrue(self.result[field])

    def test_non_fixed_input_and_vector_only_are_fail_closed(self):
        tampered = copy.deepcopy(self.control_input)
        tampered[slice_module.CONTROL_FIELDS[0]][0]["query_kind"] = "vector"
        rejected = slice_module.execute_metadata_filter_control_slice(tampered)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["actual_input_request_count"])
        self.assertEqual([], rejected["candidate_control_projections"])
        self.assertEqual([], rejected["retrieval_trace_control_projections"])
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "VECTOR_SIMILARITY_ONLY_NOT_ALLOWED",
            "METADATA_FILTER_DIMENSION_MISSING",
            "METADATA_STATUS_FILTER_REFERENCE_MISSING",
            "METADATA_FILTER_REFERENCE_MISSING",
            "CANDIDATE_METADATA_FILTER_REFERENCE_MISMATCH",
            "SELECTED_RESULT_METADATA_FILTER_REFERENCE_MISMATCH",
            "EMBEDDING_MODEL_VERSION_REFERENCE_MISSING",
            "VECTOR_DIMENSION_REFERENCE_MISSING",
            "SIMILARITY_METRIC_REFERENCE_MISSING",
            "ACTIVE_INDEX_VERSION_REFERENCE_MISSING",
            "SCORE_EXPLANATION_REFERENCE_MISSING",
            "EVIDENCE_LEDGER_REFERENCE_MISSING",
            "RETRIEVAL_TRACE_REFERENCE_MISSING",
            "PHASE2_METADATA_FILTER_CONTROL_INPUT_REJECTED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])

    def test_all_runtime_and_protected_boundaries_remain_zero(self):
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        for field in slice_module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(self.result["runtime_boundary"][field])
        local_code = self.contract["local_code"]
        for field in ("control_slice_created", "pure_in_memory_only"):
            with self.subTest(field=field):
                self.assertTrue(local_code[field])
        for field, value in local_code.items():
            if field not in {"control_slice_created", "pure_in_memory_only"}:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_stage_boundary_scope_and_rollback_stop_before_phase3(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage084_review_evidence_declared",
            "stage085_started",
            "stage085_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage086_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_METADATA_FILTER_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage085_phase1_evidence"])
        self.assertTrue(rollback["preserve_stage084_review_evidence"])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "六条固定控制请求",
            "资料状态",
            "模型／版本／维度／相似度度量",
            "IDS-STAGE085-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
