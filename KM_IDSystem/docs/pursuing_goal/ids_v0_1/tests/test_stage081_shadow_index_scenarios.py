import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE081_PHASE3_SHADOW_INDEX_CONTROLLED_SCENARIOS.md"
CONTRACT = BASE / "index_version_schema" / "stage081_shadow_index_scenarios_contract.json"
MODULE = BASE / "index_version_schema" / "stage081_shadow_index_scenarios.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-081_影子索引合同.md"
)
P1_SCOPE = BASE / "STAGE081_PHASE1_SHADOW_INDEX_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage081_shadow_index_contract.json"
P2_SCOPE = BASE / "STAGE081_PHASE2_SHADOW_INDEX_CONTROL_SLICE.md"
P2_CONTRACT = BASE / "index_version_schema" / "stage081_shadow_index_slice_contract.json"
P2_SLICE = BASE / "index_version_schema" / "stage081_shadow_index_control_slice.py"
STAGE080_REVIEW = BASE / "STAGE080_STAGE_REVIEW.md"
STAGE080_P2_CONTRACT = (
    BASE / "index_version_schema" / "stage080_index_rollback_slice_contract.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("stage081_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage081 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage081ShadowIndexPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_shadow_index_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def test_control_artifacts_exist(self):
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
            STAGE080_REVIEW,
            STAGE080_P2_CONTRACT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_declares_fixed_control_only_phase3_boundary(self):
        self.assertEqual(
            "ids.stage081.shadow_index.phase3.v1", self.contract["schema_version"]
        )
        self.assertEqual("IDS-STAGE081", self.contract["stage_id"])
        self.assertEqual("IDS-STAGE081-P3", self.contract["phase_id"])
        self.assertEqual("IDS-V0_1-STAGE081-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_SHADOW_INDEX_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["scenario_executable"])
        self.assertFalse(self.contract["execution_ready"])
        self.assertEqual("IDS-STAGE081-P4-GATE", self.contract["next_gate"])
        authority = self.contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertFalse(authority["control_scenario_can_replace_source_document"])
        self.assertFalse(authority["control_view_can_become_business_fact_authority"])
        self.assertFalse(authority["new_business_fact_source_created"])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(5, replay["required_control_request_count"])
        self.assertEqual(225, replay["expected_phase2_field_check_count"])
        scenarios = self.contract["scenario_result_contract"]
        self.assertEqual(6, len(scenarios["required_scenarios"]))
        self.assertEqual(28, scenarios["scenario_field_count"])
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_report_replays_p2_and_preserves_all_control_shapes(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(225, report["phase2_control_record_field_check_count"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(6, report["human_handling_required_count"])
        self.assertEqual(28, report["scenario_field_count"])
        self.assertEqual(168, report["scenario_field_check_count"])
        self.assertEqual(5, report["operations_version_control_view_count"])
        self.assertEqual(5, report["report_snapshot_version_control_view_count"])
        self.assertTrue(report["control_views_preserved"])
        self.assertTrue(report["all_control_references_opaque"])

    def test_each_required_exception_and_visibility_scenario_is_explicit(self):
        report = self._report()
        expected_categories = [
            scenario["scenario_category"] for scenario in self.module.SCENARIOS
        ]
        self.assertEqual(
            expected_categories,
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_RESULT_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["old_active_continues"])
                self.assertTrue(scenario["operations_version_visible"])
                self.assertTrue(scenario["report_snapshot_version_visible"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(scenario["silent_drop"])
                self.assertTrue(scenario["explicit_disposition"])
                for field in (
                    "referenced_index_version_ref",
                    "referenced_active_pointer_ref",
                    "referenced_candidate_index_version_ref",
                    "referenced_shadow_index_ref",
                    "referenced_smoke_test_ref",
                    "referenced_switch_ref",
                    "referenced_rollback_request_ref",
                    "referenced_operations_view_ref",
                    "referenced_report_snapshot_ref",
                    "active_version_before_ref",
                    "observed_active_version_after_ref",
                ):
                    self.assertIn(":control:stage081-p2:", scenario[field])

    def test_build_not_complete_and_shadow_smoke_failure_keep_old_active_version(self):
        scenarios = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        build_not_complete = scenarios["build_not_complete_old_active_continues"]
        smoke_failure = scenarios["smoke_test_failure_blocks_switch"]
        self.assertEqual(
            "vector_background_build_incomplete_preserves_active",
            build_not_complete["phase2_control_scenario"],
        )
        self.assertEqual(
            "hybrid_shadow_smoke_failure_blocks_switch",
            smoke_failure["phase2_control_scenario"],
        )
        self.assertEqual(
            "CONTROL_BACKGROUND_BUILD_INCOMPLETE_REFERENCE_ONLY",
            build_not_complete["observed_build_state"],
        )
        self.assertEqual("NOT_RUN", build_not_complete["observed_smoke_test_status"])
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
            build_not_complete["observed_switch_outcome"],
        )
        self.assertEqual("FAILED", smoke_failure["observed_smoke_test_status"])
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_SHADOW_SMOKE_TEST_FAILED",
            smoke_failure["observed_switch_outcome"],
        )
        for scenario in (build_not_complete, smoke_failure):
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(
                    scenario["active_version_before_ref"],
                    scenario["observed_active_version_after_ref"],
                )
                self.assertTrue(scenario["old_active_continues"])

    def test_switch_failure_rollback_and_concurrent_retrieval_controls_are_preserved(self):
        report = self._report()
        scenarios = {item["scenario_id"]: item for item in report["scenario_results"]}
        switch_failure = scenarios["switch_failure_preserves_active"]
        rollback = scenarios["rollback_retains_previous_active"]
        concurrent = scenarios["background_build_concurrent_retrieval_isolated"]
        self.assertEqual(
            "CONTROL_ATOMIC_SWITCH_FAILED_ACTIVE_UNCHANGED",
            switch_failure["observed_switch_outcome"],
        )
        self.assertEqual(
            switch_failure["active_version_before_ref"],
            switch_failure["observed_active_version_after_ref"],
        )
        self.assertEqual(
            "CONTROL_ELIGIBLE_REFERENCE_ONLY",
            rollback["observed_rollback_eligibility"],
        )
        self.assertTrue(rollback["rollback_target_is_retained_previous_active"])
        self.assertEqual(
            "CONTROL_BACKGROUND_BUILD_INCOMPLETE_REFERENCE_ONLY",
            concurrent["observed_build_state"],
        )
        self.assertTrue(concurrent["concurrent_retrieval_isolated"])
        self.assertTrue(report["build_not_complete_preserved"])
        self.assertTrue(report["smoke_test_failure_preserved"])
        self.assertTrue(report["switch_failure_preserved"])
        self.assertTrue(report["rollback_preserved"])
        self.assertTrue(report["concurrent_retrieval_isolation_preserved"])

    def test_operations_and_report_snapshot_views_remain_control_only(self):
        report = self._report()
        self.assertTrue(report["operations_and_report_snapshot_visibility_preserved"])
        self.assertEqual(5, len(report["operations_version_control_views"]))
        self.assertEqual(5, len(report["report_snapshot_version_control_views"]))
        for view in report["operations_version_control_views"]:
            with self.subTest(view=view["control_scenario"]):
                self.assertEqual(set(self.module.OPERATIONS_VIEW_FIELDS), set(view))
                self.assertEqual(
                    "CONTROL_OPERATIONS_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
                    view["view_state"],
                )
                self.assertIn(":control:stage081-p2:", view["operations_view_ref"])
        for view in report["report_snapshot_version_control_views"]:
            with self.subTest(view=view["control_scenario"]):
                self.assertEqual(set(self.module.REPORT_SNAPSHOT_FIELDS), set(view))
                self.assertEqual(
                    "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
                    view["snapshot_state"],
                )
                self.assertIn(":control:stage081-p2:", view["report_snapshot_ref"])
        self.assertEqual(0, report["actual_operations_display_count"])
        self.assertEqual(0, report["actual_report_snapshot_count"])

    def test_invalid_or_malformed_phase2_fails_closed(self):
        invalid = self.module.build_shadow_index_phase3_report(
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
                phase2.execute_shadow_index_control_slice(phase2.build_control_input())
            )
            result["smoke_test_output_control_projections"][0].pop("smoke_test_ref")
            return result

        malformed_report = self.module.build_shadow_index_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_phase2_runtime_signal_fails_closed(self):
        phase2 = self._phase2()

        def runtime_signal(_control):
            result = copy.deepcopy(
                phase2.execute_shadow_index_control_slice(phase2.build_control_input())
            )
            result["retrieval_query_performed"] = True
            return result

        report = self.module.build_shadow_index_phase3_report(
            phase2_executor=runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])

    def test_report_is_control_only_and_has_no_runtime_side_effect_flags(self):
        report = self._report()
        for field in (
            "actual_input_request_count",
            "actual_background_build_count",
            "actual_index_build_count",
            "actual_smoke_test_count",
            "actual_retrieval_query_count",
            "actual_concurrent_retrieval_count",
            "actual_index_rollback_count",
            "actual_operations_display_count",
            "actual_report_snapshot_count",
        ):
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
