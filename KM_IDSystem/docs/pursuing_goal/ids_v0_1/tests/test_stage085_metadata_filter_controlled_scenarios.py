import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE085_PHASE3_METADATA_FILTER_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage085_metadata_filter_controlled_scenarios.py"
)
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
P2_SCOPE = BASE / "STAGE085_PHASE2_METADATA_FILTER_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_slice_contract.json"
)
P2_SLICE = BASE / "index_version_schema" / "stage085_metadata_filter_control_slice.py"
STAGE084_REVIEW = BASE / "STAGE084_STAGE_REVIEW.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage085_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage085 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage085MetadataFilterPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_metadata_filter_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def test_control_artifacts_phase_identity_and_gate_are_explicit(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P1_SCOPE,
            P1_CONTRACT,
            P2_SCOPE,
            P2_CONTRACT,
            P2_SLICE,
            STAGE084_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage085.metadata_filter.phase3.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-085", self.contract["stage"])
        self.assertEqual("IDS-STAGE085-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE085-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_METADATA_FILTER_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE085-P4-GATE", self.contract["next_gate"])

    def test_contract_preserves_authority_replay_and_runtime_boundaries(self):
        authority = self.contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        for field in (
            "control_scenario_can_replace_source_document",
            "control_result_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            list(self.module.P2_SCENARIOS), replay["required_control_scenarios"]
        )
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(366, replay["expected_phase2_field_check_count"])
        for field in (
            "keyword_baseline_required",
            "vector_baseline_required",
            "vector_similarity_only_rejected",
            "six_metadata_filter_dimensions_required",
            "metadata_status_filter_reference_required",
            "candidate_selected_and_trace_metadata_filter_chain_required",
            "candidate_and_trace_vector_contract_chain_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(replay[field])
        scenario_contract = self.contract["scenario_result_contract"]
        self.assertTrue(scenario_contract["scenario_executable"])
        self.assertFalse(scenario_contract["execution_ready"])
        self.assertEqual(8, scenario_contract["scenario_count"])
        self.assertEqual(31, scenario_contract["scenario_field_count"])
        self.assertEqual(248, scenario_contract["expected_scenario_field_check_count"])
        self.assertEqual(
            list(self.module.SCENARIO_RESULT_FIELDS),
            scenario_contract["scenario_result_fields"],
        )
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertIn(value, (False, 0))

    def test_report_replays_p2_and_preserves_all_control_shapes(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(366, report["phase2_control_record_field_check_count"])
        self.assertEqual(8, report["scenario_count"])
        self.assertEqual(31, report["scenario_field_count"])
        self.assertEqual(248, report["scenario_field_check_count"])
        self.assertEqual(8, report["passed_scenario_count"])
        self.assertEqual(8, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(8, report["human_handling_required_count"])
        for field in (
            "keyword_and_domain_coverage_preserved",
            "vector_contract_chain_preserved",
            "six_dimension_filter_combination_preserved",
            "metadata_status_filter_reference_preserved",
            "top_k_ranking_and_validity_preserved",
            "old_index_trace_version_preserved",
            "all_control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])

    def test_each_required_scenario_is_explicit_control_only_and_whitebox_gated(self):
        report = self._report()
        self.assertEqual(
            [item["scenario_category"] for item in self.module.SCENARIOS],
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        source_scenarios = {
            control
            for scenario in report["scenario_results"]
            for control in scenario["phase2_control_scenarios"]
        }
        self.assertEqual(set(self.module.P2_SCENARIOS), source_scenarios)
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(
                    set(self.module.SCENARIO_RESULT_FIELDS), set(scenario)
                )
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(scenario["silent_drop"])
                self.assertTrue(scenario["explicit_disposition"])
                for field in (
                    "query_ref",
                    "candidate_ref",
                    "selected_result_ref",
                    "retrieval_trace_ref",
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                    "active_index_version_ref",
                    "evidence_ledger_ref",
                ):
                    with self.subTest(field=field):
                        self.assertIn(self.module.CONTROL_PREFIX, scenario[field])
                self.assertTrue(
                    all(
                        self.module.CONTROL_PREFIX in item
                        for item in scenario["metadata_filter_refs"]
                    )
                )

    def test_taskpack_scenario_categories_and_six_filters_hold_without_values(self):
        report = self._report()
        scenarios = {
            item["scenario_id"]: item for item in report["scenario_results"]
        }
        for scenario_id in (
            "keyword_baseline_control",
            "material_grade_keyword_control",
            "equipment_model_hybrid_control",
            "standard_number_hybrid_control",
            "semantic_similarity_hybrid_control",
        ):
            with self.subTest(scenario_id=scenario_id):
                self.assertTrue(scenarios[scenario_id]["expectation_met"])
                self.assertTrue(scenarios[scenario_id]["observed_vector_only_rejected"])
                self.assertEqual(
                    "CONTROL_VECTOR_BASELINE_DECLARED_NOT_EXECUTED",
                    scenarios[scenario_id]["observed_vector_baseline_state"],
                )
        self.assertEqual(
            "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED",
            scenarios["semantic_similarity_hybrid_control"][
                "observed_semantic_similarity_state"
            ],
        )
        self.assertEqual(
            "CONTROL_SIX_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED",
            scenarios["six_dimension_filter_combination_control"][
                "observed_filter_combination_state"
            ],
        )
        for scenario_id in (
            "top_k_ranking_explanation_result_validity_control",
            "old_index_service_trace_version_control",
        ):
            with self.subTest(scenario_id=scenario_id):
                self.assertTrue(scenarios[scenario_id]["expectation_met"])

    def test_invalid_or_side_effecting_phase2_replay_is_fail_closed(self):
        def missing_metadata_status(control_input):
            result = self._phase2().execute_metadata_filter_control_slice(control_input)
            altered = copy.deepcopy(result)
            altered["all_metadata_status_filter_references_declared"] = False
            return altered

        failed = self.module.build_metadata_filter_phase3_report(missing_metadata_status)
        self.assertFalse(failed["valid"])
        self.assertEqual(self.module.FAIL_RESULT, failed["result"])
        self.assertEqual("IDS-STAGE085-P3-GATE", failed["next_gate"])

        def runtime_signal(control_input):
            result = self._phase2().execute_metadata_filter_control_slice(control_input)
            altered = copy.deepcopy(result)
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_metadata_filter_phase3_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, failed["result"])

    def test_report_is_zero_runtime_and_stops_before_phase4(self):
        report = self._report()
        for field in (
            "actual_input_request_count",
            "actual_keyword_retrieval_query_count",
            "actual_vector_retrieval_query_count",
            "actual_embedding_generation_count",
            "actual_material_grade_lookup_count",
            "actual_equipment_model_lookup_count",
            "actual_standard_number_lookup_count",
            "actual_semantic_similarity_calculation_count",
            "actual_metadata_filter_evaluation_count",
            "actual_top_k_selection_count",
            "actual_hybrid_ranking_count",
            "actual_retrieval_trace_access_count",
            "actual_evidence_ledger_access_count",
            "actual_old_index_service_access_count",
        ):
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(report["control_scenario_can_replace_source_document"])
        self.assertFalse(report["control_result_can_become_business_fact_authority"])
        self.assertFalse(report["business_line_whitebox_human_approval_recorded"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        self.assertFalse(report["automatic_business_write_allowed"])
        self.assertFalse(report["automatic_index_switch_allowed"])
        self.assertFalse(report["automatic_parameter_write_allowed"])
        self.assertTrue(report["stage084_review_evidence_declared"])
        self.assertTrue(report["stage085_started"])
        self.assertTrue(report["phase1_completed"])
        self.assertTrue(report["phase2_completed"])
        self.assertTrue(report["phase3_started"])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage086_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
