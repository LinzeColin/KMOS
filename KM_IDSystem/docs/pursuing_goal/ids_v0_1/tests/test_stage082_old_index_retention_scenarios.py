import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE082_PHASE3_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage082_old_index_retention_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage082_old_index_retention_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-082_旧索引保留策略.md"
)
P1_SCOPE = BASE / "STAGE082_PHASE1_OLD_INDEX_RETENTION_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage082_old_index_retention_contract.json"
P2_SCOPE = BASE / "STAGE082_PHASE2_OLD_INDEX_RETENTION_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage082_old_index_retention_slice_contract.json"
)
P2_SLICE = (
    BASE / "index_version_schema" / "stage082_old_index_retention_control_slice.py"
)
STAGE081_REVIEW = BASE / "STAGE081_STAGE_REVIEW.md"
STAGE081_P2_CONTRACT = (
    BASE / "index_version_schema" / "stage081_shadow_index_slice_contract.json"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("stage082_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage082 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage082OldIndexRetentionPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_old_index_retention_phase3_report()

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
            STAGE081_REVIEW,
            STAGE081_P2_CONTRACT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage082.old_index_retention.phase3.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-082", self.contract["stage"])
        self.assertEqual("IDS-STAGE082-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE082-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["scenario_executable"])
        self.assertFalse(self.contract["execution_ready"])
        self.assertEqual("IDS-STAGE082-P4-GATE", self.contract["next_gate"])

    def test_contract_preserves_authority_replay_and_runtime_boundaries(self):
        authority = self.contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertFalse(authority["control_scenario_can_replace_source_document"])
        self.assertFalse(authority["control_view_can_become_business_fact_authority"])
        self.assertFalse(authority["new_business_fact_source_created"])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            list(self.module.P2_SCENARIOS), replay["required_control_scenarios"]
        )
        self.assertEqual(5, replay["required_control_request_count"])
        self.assertEqual(305, replay["expected_phase2_field_check_count"])
        scenario_contract = self.contract["scenario_result_contract"]
        self.assertEqual(6, len(scenario_contract["required_scenarios"]))
        self.assertEqual(31, scenario_contract["scenario_field_count"])
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
        self.assertEqual(305, report["phase2_control_record_field_check_count"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(31, report["scenario_field_count"])
        self.assertEqual(186, report["scenario_field_check_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(6, report["human_handling_required_count"])
        self.assertEqual(5, report["operations_version_control_view_count"])
        self.assertEqual(5, report["report_snapshot_version_control_view_count"])
        self.assertTrue(report["control_views_preserved"])
        self.assertTrue(report["all_control_references_opaque"])

    def test_each_required_exception_and_visibility_scenario_is_explicit(self):
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
                self.assertTrue(scenario["old_active_continues"])
                self.assertTrue(scenario["rollback_target_is_retained_previous_active"])
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
                    "referenced_retention_policy_ref",
                    "referenced_cleanup_eligibility_ref",
                    "referenced_operations_view_ref",
                    "referenced_report_snapshot_ref",
                    "active_version_before_ref",
                    "observed_active_version_after_ref",
                ):
                    self.assertIn(":control:stage082-p2:", scenario[field])

    def test_build_and_shadow_smoke_failures_keep_old_active_version(self):
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

    def test_switch_failure_rollback_window_and_concurrent_retrieval_controls_hold(self):
        report = self._report()
        scenarios = {item["scenario_id"]: item for item in report["scenario_results"]}
        switch_failure = scenarios["switch_failure_preserves_active"]
        rollback_window = scenarios[
            "rollback_window_unconfigured_preserves_previous_active"
        ]
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
            "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
            rollback_window["observed_rollback_eligibility"],
        )
        self.assertEqual(
            "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY",
            rollback_window["observed_cleanup_eligibility"],
        )
        self.assertTrue(rollback_window["rollback_target_is_retained_previous_active"])
        self.assertTrue(concurrent["concurrent_retrieval_isolated"])
        self.assertTrue(report["build_not_complete_preserved"])
        self.assertTrue(report["smoke_test_failure_preserved"])
        self.assertTrue(report["switch_failure_preserved"])
        self.assertTrue(report["rollback_window_unconfigured_preserved"])
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
                self.assertIn(":control:stage082-p2:", view["operations_view_ref"])
        for view in report["report_snapshot_version_control_views"]:
            with self.subTest(view=view["control_scenario"]):
                self.assertEqual(set(self.module.REPORT_SNAPSHOT_FIELDS), set(view))
                self.assertEqual(
                    "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
                    view["snapshot_state"],
                )
                self.assertIn(":control:stage082-p2:", view["report_snapshot_ref"])
        self.assertEqual(0, report["actual_operations_display_count"])
        self.assertEqual(0, report["actual_report_snapshot_count"])

    def test_invalid_or_malformed_phase2_fails_closed(self):
        invalid = self.module.build_old_index_retention_phase3_report(
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
                phase2.execute_old_index_retention_control_slice(
                    phase2.build_control_input()
                )
            )
            result["cleanup_eligibility_control_projections"][0].pop(
                "cleanup_eligibility"
            )
            return result

        malformed_report = self.module.build_old_index_retention_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_phase2_runtime_signal_fails_closed(self):
        phase2 = self._phase2()

        def runtime_signal(_control):
            result = copy.deepcopy(
                phase2.execute_old_index_retention_control_slice(
                    phase2.build_control_input()
                )
            )
            result["retrieval_query_performed"] = True
            return result

        report = self.module.build_old_index_retention_phase3_report(
            phase2_executor=runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])

    def test_report_is_control_only_and_stops_at_phase4_gate(self):
        report = self._report()
        for field in (
            "actual_input_request_count",
            "actual_background_build_count",
            "actual_index_build_count",
            "actual_smoke_test_count",
            "actual_retrieval_query_count",
            "actual_concurrent_retrieval_count",
            "actual_index_rollback_count",
            "actual_old_index_cleanup_count",
            "actual_operations_display_count",
            "actual_report_snapshot_count",
        ):
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(report["control_scenario_can_replace_source_document"])
        self.assertFalse(report["control_view_can_become_business_fact_authority"])
        self.assertFalse(report["business_line_whitebox_human_approval_recorded"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        self.assertTrue(report["stage082_started"])
        self.assertTrue(report["phase1_completed"])
        self.assertTrue(report["phase2_completed"])
        self.assertTrue(report["phase3_started"])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage083_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
