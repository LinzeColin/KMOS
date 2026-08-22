import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE088_PHASE3_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage088_retrieval_result_validity_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage088_retrieval_result_validity_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-088_检索结果有效性门禁.md"
)
P1_SCOPE = BASE / "STAGE088_PHASE1_RETRIEVAL_RESULT_VALIDITY_SCOPE_BOUNDARY.md"
P1_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage088_retrieval_result_validity_contract.json"
)
P2_SCOPE = BASE / "STAGE088_PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage088_retrieval_result_validity_slice_contract.json"
)
P2_SLICE = (
    BASE
    / "index_version_schema"
    / "stage088_retrieval_result_validity_control_slice.py"
)
STAGE087_REVIEW = BASE / "STAGE087_STAGE_REVIEW.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage088_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage088 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage088RetrievalResultValidityPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_retrieval_result_validity_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def _phase2_result(self):
        phase2 = self._phase2()
        return phase2.execute_retrieval_result_validity_control_slice(
            phase2.build_control_input()
        )

    def test_control_artifacts_phase_identity_scope_and_gate_are_explicit(self):
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
            STAGE087_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage088.retrieval_result_validity.phase3.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-088", self.contract["stage"])
        self.assertEqual("IDS-STAGE088-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE088-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE088-P4-GATE", self.contract["next_gate"])
        scope = SCOPE.read_text(encoding="utf-8")
        for text in (
            "不建立第二权威事实源",
            "八个",
            "纯内存",
            "材料牌号",
            "设备型号",
            "标准号",
            "语义相似",
            "结果有效性保持",
            "业务线白箱人工复核",
            "不读取真实资料",
            "不消耗模型 Token",
            "不进入 Stage088 P4",
            "IDS-STAGE088-P4-GATE",
        ):
            with self.subTest(text=text):
                self.assertIn(text, scope)

    def test_contract_preserves_authority_replay_runtime_and_phase_boundary(self):
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
            "evidence_ledger_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            list(self.module.P2_SCENARIOS), replay["required_control_scenarios"]
        )
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(9, replay["required_projection_group_count"])
        self.assertEqual(528, replay["expected_phase2_field_check_count"])
        for field in (
            "keyword_baseline_required",
            "vector_baseline_required",
            "vector_similarity_only_rejected",
            "six_metadata_filter_dimensions_required",
            "result_validity_gate_reference_chain_required",
            "result_validity_state_must_remain_not_evaluated",
            "validity_gate_must_remain_pending_human_whitebox_review",
        ):
            with self.subTest(field=field):
                self.assertTrue(replay[field])
        scenario_contract = self.contract["scenario_result_contract"]
        self.assertTrue(scenario_contract["scenario_executable"])
        self.assertFalse(scenario_contract["execution_ready"])
        self.assertEqual(8, scenario_contract["scenario_count"])
        self.assertEqual(33, scenario_contract["scenario_field_count"])
        self.assertEqual(
            264, scenario_contract["expected_scenario_field_check_count"]
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertIn(value, (False, 0))
        boundary = self.contract["stage_boundary"]
        for field in (
            "stage087_review_evidence_declared",
            "stage088_started",
            "stage088_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_started",
            "stage089_started",
            "ovh_started",
            "production_started",
            "upload_or_push_started",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_report_replays_p2_and_preserves_all_control_shapes(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_slice_replayed"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["phase2_control_references_opaque"])
        self.assertEqual(528, report["phase2_control_record_field_check_count"])
        self.assertEqual(528, report["phase2_control_projection_field_total"])
        self.assertEqual(8, report["scenario_count"])
        self.assertEqual(33, report["scenario_field_count"])
        self.assertEqual(264, report["scenario_field_check_count"])
        self.assertEqual(8, report["passed_scenario_count"])
        self.assertEqual(8, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(8, report["human_handling_required_count"])
        for field in (
            "keyword_and_domain_coverage_preserved",
            "six_dimension_filter_combination_preserved",
            "active_index_version_chain_preserved",
            "top_k_ranking_and_validity_preserved",
            "result_validity_gate_chain_preserved",
            "old_index_trace_version_preserved",
            "all_result_validity_states_not_evaluated",
            "all_validity_gates_pending_human_whitebox",
            "all_business_line_handling_required",
            "all_scenarios_expectations_met",
            "all_control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
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
            "actual_result_validity_evaluation_count",
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
        for field in (
            "stage087_review_evidence_declared",
            "stage088_started",
            "stage088_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        for field in (
            "phase4_started",
            "whole_stage_review_started",
            "whole_stage_review_performed",
            "stage089_started",
            "ovh_started",
            "production_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

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
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
                self.assertFalse(scenario["silent_drop"])
                self.assertTrue(scenario["explicit_disposition"])
                self.assertEqual(
                    "CONTROL_RESULT_VALIDITY_NOT_EVALUATED",
                    scenario["observed_result_validity_state"],
                )
                self.assertEqual(
                    "CONTROL_VALIDITY_GATE_PENDING_HUMAN_WHITEBOX_REVIEW",
                    scenario["observed_validity_gate_state"],
                )
                for field in (
                    "query_ref",
                    "candidate_chunk_ref",
                    "selected_chunk_ref",
                    "retrieval_trace_ref",
                    "validity_gate_ref",
                    "keyword_retrieval_baseline_ref",
                    "vector_retrieval_baseline_ref",
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

    def test_taskpack_categories_and_special_control_states_hold_without_values(self):
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
        top_k = scenarios["top_k_ranking_explanation_result_validity_control"]
        self.assertEqual(
            "CONTROL_TOP_K_REFERENCE_DECLARED_NOT_APPLIED",
            top_k["observed_top_k_state"],
        )
        self.assertEqual(
            "CONTROL_RANKING_EXPLANATION_DECLARED_NOT_APPLIED",
            top_k["observed_ranking_explanation_state"],
        )
        self.assertEqual(
            "CONTROL_OLD_INDEX_VERSION_TRACE_DECLARED_NOT_READ_OR_WRITTEN",
            scenarios["old_index_service_trace_version_control"][
                "observed_old_index_trace_state"
            ],
        )

    def test_invalid_phase2_output_fails_closed_without_scenarios(self):
        failed = self.module.build_retrieval_result_validity_phase3_report(
            lambda _control_input: ["invalid-control-output"]
        )
        self.assertFalse(failed["valid"])
        self.assertEqual(self.module.FAIL_RESULT, failed["result"])
        self.assertEqual("PHASE2_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, failed["next_gate"])
        self.assertEqual([], failed["scenario_results"])
        self.assertEqual(0, failed["scenario_count"])
        self.assertEqual(0, failed["scenario_field_check_count"])

    def test_runtime_signal_in_phase2_fails_closed_without_scenarios(self):
        def runtime_signal(_control_input):
            altered = copy.deepcopy(self._phase2_result())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_retrieval_result_validity_phase3_report(
            runtime_signal
        )
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase2_side_effect_free"])
        self.assertEqual("PHASE2_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, failed["next_gate"])
        self.assertEqual([], failed["scenario_results"])

    def test_nonopaque_reference_or_gate_state_fails_closed_without_leaking_scenarios(
        self,
    ):
        def nonopaque_reference(_control_input):
            altered = copy.deepcopy(self._phase2_result())
            altered["candidate_control_projections"][0]["candidate_chunk_ref"] = (
                "non-control-reference"
            )
            return altered

        failed_reference = (
            self.module.build_retrieval_result_validity_phase3_report(
                nonopaque_reference
            )
        )
        self.assertFalse(failed_reference["valid"])
        self.assertEqual(
            "CONTROL_REFERENCE_NOT_OPAQUE", failed_reference["failure_state"]
        )
        self.assertEqual([], failed_reference["scenario_results"])

        def invalid_gate_state(_control_input):
            altered = copy.deepcopy(self._phase2_result())
            altered["result_validity_gate_control_projections"][0][
                "validity_gate_state"
            ] = "CONTROL_VALIDITY_GATE_NOT_PENDING"
            return altered

        failed_gate = self.module.build_retrieval_result_validity_phase3_report(
            invalid_gate_state
        )
        self.assertFalse(failed_gate["valid"])
        self.assertEqual(
            "VALIDITY_GATE_NOT_PENDING_HUMAN_WHITEBOX",
            failed_gate["failure_state"],
        )
        self.assertEqual([], failed_gate["scenario_results"])

if __name__ == "__main__":
    unittest.main()
