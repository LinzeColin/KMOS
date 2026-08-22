import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE083_PHASE3_KEYWORD_RETRIEVAL_BASELINE_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage083_keyword_retrieval_baseline_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage083_keyword_retrieval_baseline_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-083_关键词检索基线.md"
)
P1_SCOPE = BASE / "STAGE083_PHASE1_KEYWORD_RETRIEVAL_BASELINE_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage083_keyword_retrieval_baseline_contract.json"
P2_SCOPE = BASE / "STAGE083_PHASE2_KEYWORD_RETRIEVAL_BASELINE_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage083_keyword_retrieval_baseline_slice_contract.json"
)
P2_SLICE = (
    BASE / "index_version_schema" / "stage083_keyword_retrieval_baseline_control_slice.py"
)
STAGE082_REVIEW = BASE / "STAGE082_STAGE_REVIEW.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage083_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage083 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage083KeywordRetrievalPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_keyword_retrieval_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def test_control_artifacts_and_phase_identity_are_explicit(self):
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
            STAGE082_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage083.keyword_retrieval_baseline.phase3.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-083", self.contract["stage"])
        self.assertEqual("IDS-STAGE083-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE083-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_KEYWORD_RETRIEVAL_BASELINE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["scenario_result_contract"]["scenario_executable"])
        self.assertFalse(self.contract["scenario_result_contract"]["execution_ready"])
        self.assertEqual("IDS-STAGE083-P4-GATE", self.contract["next_gate"])

    def test_contract_preserves_authority_replay_and_runtime_boundaries(self):
        authority = self.contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertFalse(authority["control_scenario_can_replace_source_document"])
        self.assertFalse(authority["control_result_can_become_business_fact_authority"])
        self.assertFalse(authority["second_authoritative_source_created"])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            list(self.module.P2_SCENARIOS), replay["required_control_scenarios"]
        )
        self.assertEqual(5, replay["required_control_request_count"])
        self.assertEqual(250, replay["expected_phase2_field_check_count"])
        scenario_contract = self.contract["scenario_result_contract"]
        self.assertEqual(8, scenario_contract["scenario_count"])
        self.assertEqual(26, scenario_contract["scenario_field_count"])
        self.assertEqual(208, scenario_contract["expected_scenario_field_check_count"])
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
        self.assertEqual(250, report["phase2_control_record_field_check_count"])
        self.assertEqual(8, report["scenario_count"])
        self.assertEqual(26, report["scenario_field_count"])
        self.assertEqual(208, report["scenario_field_check_count"])
        self.assertEqual(8, report["passed_scenario_count"])
        self.assertEqual(8, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(8, report["human_handling_required_count"])

    def test_each_required_scenario_is_explicit_and_control_only(self):
        report = self._report()
        self.assertEqual(
            [item["scenario_category"] for item in self.module.SCENARIOS],
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(
                    set(self.module.SCENARIO_RESULT_FIELDS), set(scenario)
                )
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(scenario["silent_drop"])
                self.assertTrue(scenario["explicit_disposition"])
                self.assertIn(":control:stage083-p2:", scenario["query_ref"])
                self.assertIn(":control:stage083-p2:", scenario["candidate_ref"])
                self.assertIn(":control:stage083-p2:", scenario["selected_result_ref"])
                self.assertIn(":control:stage083-p2:", scenario["retrieval_trace_ref"])
                self.assertTrue(
                    all(
                        ":control:stage083-p2:" in item
                        for item in scenario["metadata_filter_refs"]
                    )
                )

    def test_keyword_material_equipment_standard_and_semantic_categories_hold(self):
        scenarios = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        self.assertEqual("keyword", scenarios["keyword_baseline_control"]["query_kind"])
        self.assertEqual(
            "keyword", scenarios["material_grade_keyword_control"]["query_kind"]
        )
        self.assertEqual(
            "hybrid", scenarios["equipment_model_keyword_control"]["query_kind"]
        )
        self.assertEqual(
            "keyword", scenarios["standard_number_keyword_control"]["query_kind"]
        )
        semantic = scenarios["semantic_similarity_hybrid_control"]
        self.assertEqual("hybrid", semantic["query_kind"])
        self.assertEqual(
            "CONTROL_SEMANTIC_SIMILARITY_REFERENCE_ONLY_NOT_CALCULATED",
            semantic["observed_semantic_similarity_state"],
        )
        for scenario_id in (
            "keyword_baseline_control",
            "material_grade_keyword_control",
            "equipment_model_keyword_control",
            "standard_number_keyword_control",
            "semantic_similarity_hybrid_control",
        ):
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    "CONTROL_KEYWORD_BASELINE_DECLARED_NOT_EXECUTED",
                    scenarios[scenario_id]["observed_keyword_baseline_state"],
                )
                self.assertTrue(scenarios[scenario_id]["observed_vector_only_rejected"])

    def test_filter_combination_top_k_ranking_and_validity_hold(self):
        scenarios = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        combination = scenarios["five_dimension_filter_combination_control"]
        self.assertEqual(5, len(combination["phase2_control_scenarios"]))
        self.assertEqual(5, len(combination["metadata_filter_refs"]))
        self.assertEqual(
            "CONTROL_FIVE_DIMENSION_FILTER_COMBINATION_DECLARED_NOT_EVALUATED",
            combination["observed_filter_combination_state"],
        )
        top_k = scenarios["top_k_ranking_explanation_result_validity_control"]
        self.assertEqual(
            "CONTROL_TOP_K_REFERENCE_DECLARED_NOT_APPLIED",
            top_k["observed_top_k_state"],
        )
        self.assertEqual(
            "CONTROL_RANKING_EXPLANATION_DECLARED_NOT_EXECUTED",
            top_k["observed_ranking_explanation_state"],
        )
        self.assertEqual(
            "CONTROL_RESULT_VALIDITY_DECLARED_NOT_EXECUTED",
            top_k["observed_result_validity_state"],
        )
        self.assertTrue(self._report()["filter_combination_preserved"])
        self.assertTrue(self._report()["top_k_ranking_and_validity_preserved"])

    def test_old_index_service_trace_keeps_the_control_version_chain(self):
        scenario = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }["old_index_service_trace_version_control"]
        self.assertEqual(
            "CONTROL_OLD_INDEX_TRACE_VERSION_MATCH_NOT_WRITTEN",
            scenario["observed_old_index_trace_state"],
        )
        self.assertIn(":control:stage083-p2:", scenario["active_index_version_ref"])
        self.assertIn(":control:stage083-p2:", scenario["retrieval_trace_ref"])
        self.assertTrue(self._report()["old_index_trace_version_preserved"])

    def test_invalid_or_malformed_phase2_fails_closed(self):
        invalid = self.module.build_keyword_retrieval_phase3_report(
            phase2_executor=lambda _control: {"input_accepted": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertFalse(invalid["phase2_shape_preserved"])
        self.assertFalse(invalid["phase2_side_effect_free"])
        self.assertEqual(0, invalid["passed_scenario_count"])

        phase2 = self._phase2()

        def malformed(_control):
            result = copy.deepcopy(
                phase2.execute_keyword_retrieval_control_slice(
                    phase2.build_control_input()
                )
            )
            result["retrieval_trace_control_projections"][0].pop("trace_state")
            return result

        malformed_report = self.module.build_keyword_retrieval_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_phase2_runtime_signal_fails_closed(self):
        phase2 = self._phase2()

        def runtime_signal(_control):
            result = copy.deepcopy(
                phase2.execute_keyword_retrieval_control_slice(
                    phase2.build_control_input()
                )
            )
            result["runtime_boundary"]["model_token_consumption_performed"] = True
            return result

        report = self.module.build_keyword_retrieval_phase3_report(
            phase2_executor=runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])

    def test_report_is_control_only_and_stops_at_phase4_gate(self):
        report = self._report()
        for field in (
            "actual_input_request_count",
            "actual_keyword_retrieval_query_count",
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
        self.assertTrue(report["stage083_started"])
        self.assertTrue(report["phase1_completed"])
        self.assertTrue(report["phase2_completed"])
        self.assertTrue(report["phase3_started"])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage084_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
