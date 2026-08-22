import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE088_PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE.md"
CONTRACT = BASE / "index_version_schema" / "stage088_retrieval_result_validity_slice_contract.json"
MODULE = BASE / "index_version_schema" / "stage088_retrieval_result_validity_control_slice.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-088_检索结果有效性门禁.md"
)
P1_SCOPE = BASE / "STAGE088_PHASE1_RETRIEVAL_RESULT_VALIDITY_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage088_retrieval_result_validity_contract.json"
STAGE087_REVIEW = BASE / "STAGE087_STAGE_REVIEW.md"


def load_module():
    spec = importlib.util.spec_from_file_location("stage088_slice", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


slice_module = load_module()


class Stage088RetrievalResultValidityPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = slice_module.build_control_input()
        cls.result = slice_module.execute_retrieval_result_validity_control_slice(
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
            STAGE087_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage088.retrieval_result_validity.phase2.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-088", self.contract["stage"])
        self.assertEqual("IDS-STAGE088-P2", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE088-P2", self.contract["task_id"])
        self.assertEqual("ACC-STAGE-088", self.contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE088-P3-GATE", self.contract["next_gate"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "evidence_ledger_access_performed",
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
        self.assertEqual(input_contract["control_fields"], list(slice_module.CONTROL_FIELDS))
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
                self.assertIn("declared-reference-only", request["requested_top_k_ref"])
                for field in (
                    "keyword_retrieval_baseline_ref",
                    "vector_retrieval_baseline_ref",
                    "active_index_version_ref",
                    "metadata_status_filter_ref",
                    "evidence_level_filter_ref",
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
            "COMPLETED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE",
            self.result["execution_state"],
        )
        self.assertEqual(0, self.result["actual_input_request_count"])
        self.assertIsNone(self.result["failure_state"])
        groups = (
            (
                "query_control_projections",
                "query_control_projection_count",
                slice_module.QUERY_FIELDS,
                "query_projection_fields",
                "query_projection_field_count",
            ),
            (
                "metadata_filter_control_projections",
                "metadata_filter_control_projection_count",
                slice_module.METADATA_FILTER_PROJECTION_FIELDS,
                "metadata_filter_projection_fields",
                "metadata_filter_projection_field_count",
            ),
            (
                "active_index_version_control_projections",
                "active_index_version_control_projection_count",
                slice_module.ACTIVE_INDEX_VERSION_FIELDS,
                "active_index_version_projection_fields",
                "active_index_version_projection_field_count",
            ),
            (
                "candidate_control_projections",
                "candidate_control_projection_count",
                slice_module.CANDIDATE_FIELDS,
                "candidate_projection_fields",
                "candidate_projection_field_count",
            ),
            (
                "score_control_projections",
                "score_control_projection_count",
                slice_module.SCORE_FIELDS,
                "score_projection_fields",
                "score_projection_field_count",
            ),
            (
                "selected_control_projections",
                "selected_control_projection_count",
                slice_module.SELECTED_FIELDS,
                "selected_projection_fields",
                "selected_projection_field_count",
            ),
            (
                "retrieval_trace_control_projections",
                "retrieval_trace_control_projection_count",
                slice_module.RETRIEVAL_TRACE_FIELDS,
                "retrieval_trace_projection_fields",
                "retrieval_trace_projection_field_count",
            ),
            (
                "result_validity_gate_control_projections",
                "result_validity_gate_control_projection_count",
                slice_module.RESULT_VALIDITY_GATE_FIELDS,
                "result_validity_gate_projection_fields",
                "result_validity_gate_projection_field_count",
            ),
            (
                "future_integration_control_projections",
                "future_integration_control_projection_count",
                slice_module.FUTURE_INTEGRATION_FIELDS,
                "future_integration_projection_fields",
                "future_integration_projection_field_count",
            ),
        )
        total = 0
        for list_key, count_key, module_fields, contract_fields, count_field in groups:
            with self.subTest(list_key=list_key):
                records = self.result[list_key]
                self.assertEqual(projection["each_projection_count"], len(records))
                self.assertEqual(len(records), self.result[count_key])
                self.assertEqual(list(module_fields), projection[contract_fields])
                self.assertEqual(len(module_fields), projection[count_field])
                for record in records:
                    self.assertEqual(set(module_fields), set(record))
                total += sum(len(record) for record in records)
        self.assertEqual(projection["control_projection_field_total"], total)
        self.assertEqual(
            projection["control_projection_field_total_per_request"],
            total // projection["each_projection_count"],
        )

    def test_reference_chains_gate_and_future_routes_are_declared_not_executed(self):
        for field in (
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
        ):
            with self.subTest(field=field):
                self.assertTrue(self.result[field])
        for record in self.result["result_validity_gate_control_projections"]:
            with self.subTest(record=record):
                self.assertEqual(
                    "CONTROL_RESULT_VALIDITY_NOT_EVALUATED",
                    record["observed_result_validity_state"],
                )
                self.assertEqual(
                    "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW",
                    record["validity_gate_state"],
                )
        for record in self.result["future_integration_control_projections"]:
            with self.subTest(record=record):
                self.assertEqual(
                    "CONTROL_FUTURE_RUNTIME_ROUTE_NOT_EXECUTED",
                    record["integration_state"],
                )
                for field, value in record.items():
                    if field != "integration_state":
                        self.assertIn("future-only", value)

    def test_nonfixed_or_vector_only_input_fails_closed_without_projections(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[slice_module.CONTROL_FIELDS[0]][0]["query_kind"] = "vector"
        rejected = slice_module.execute_retrieval_result_validity_control_slice(
            invalid_input
        )
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["actual_input_request_count"])
        for key, value in rejected.items():
            if key.endswith("_projection_count"):
                with self.subTest(key=key):
                    self.assertEqual(0, value)
        self.assertFalse(rejected["persistent_record_created"])
        self.assertTrue(all(value is False for value in rejected["runtime_boundary"].values()))

    def test_failure_runtime_and_protected_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "CONTROL_INPUT_MISMATCH",
            "VECTOR_SIMILARITY_ONLY_NOT_ALLOWED",
            "CANDIDATE_REFERENCE_MISSING",
            "SELECTED_REFERENCE_MISSING",
            "SCORE_EXPLANATION_REFERENCE_MISSING",
            "EVIDENCE_LEDGER_REFERENCE_MISSING",
            "RETRIEVAL_TRACE_REFERENCE_MISSING",
            "RESULT_VALIDITY_GATE_REFERENCE_MISSING",
            "SYSTEM_OUTPUT_ONLY_NOT_SUFFICIENT",
            "PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_INPUT_REJECTED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        self.assertTrue(
            all(value is False for value in self.result["runtime_boundary"].values())
        )
        future = self.contract["future_runtime_prerequisite_contract"]
        for field, value in future.items():
            if field.endswith(
                ("_created", "_performed", "_executed", "_persisted", "_selected", "_generated", "_evaluated")
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        local_code = self.contract["local_code"]
        for field in (
            "control_slice_created",
            "pure_in_memory_only",
            "result_validity_gate_control_slice_created",
        ):
            with self.subTest(field=field):
                self.assertTrue(local_code[field])
        for field, value in local_code.items():
            if field not in {
                "control_slice_created",
                "pure_in_memory_only",
                "result_validity_gate_control_slice_created",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)
        self.assertFalse(self.result["persistent_record_created"])

    def test_scope_rolls_back_cleanly_and_only_p3_is_next(self):
        boundary = self.contract["stage_boundary"]
        for field in (
            "stage087_review_evidence_declared",
            "stage088_started",
            "stage088_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_started",
            "stage089_started",
            "ovh_started",
            "production_started",
            "upload_or_push_started",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "六条固定",
            "纯内存",
            "vector similarity",
            "系统有输出而接受结果",
            "不读取真实资料",
            "不消耗模型 Token",
            "不进入 Stage088 P3",
            "IDS-STAGE088-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)


if __name__ == "__main__":
    unittest.main()
