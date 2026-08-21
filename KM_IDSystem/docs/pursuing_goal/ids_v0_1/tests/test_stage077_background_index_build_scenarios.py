import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE077_PHASE3_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage077_background_index_build_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage077_background_index_build_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-077_后台索引构建.md"
)
PHASE1_SCOPE = BASE / "STAGE077_PHASE1_BACKGROUND_INDEX_BUILD_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage077_background_index_build_contract.json"
)
PHASE2_SCOPE = BASE / "STAGE077_PHASE2_BACKGROUND_INDEX_BUILD_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage077_background_index_build_slice_contract.json"
)
PHASE2_SLICE = (
    BASE / "index_version_schema" / "stage077_background_index_build_slice.py"
)
PREDECESSOR_REVIEW = BASE / "STAGE076_STAGE_REVIEW.md"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage077-p3-local.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage077_p3", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage077 P3 controlled scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage077BackgroundIndexBuildPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _report(self):
        return self.module.build_background_index_build_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def test_control_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            PREDECESSOR_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_declares_fixed_control_only_phase3_boundary(self):
        self.assertEqual(
            "ids.stage077.background_index_build.phase3.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE077-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["scenario_executable"])
        self.assertFalse(self.contract["execution_ready"])
        self.assertEqual("IDS-STAGE077-P4-GATE", self.contract["next_gate"])
        authority = self.contract["source_authority"]
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["phase2_control_slice_replay_contract"]
        self.assertEqual(5, replay["control_request_count"])
        self.assertEqual(255, replay["phase2_control_field_check_count"])
        self.assertEqual(6, self.contract["controlled_scenario_contract"]["scenario_count"])
        self.assertEqual(26, self.contract["controlled_scenario_contract"]["field_count"])
        self.assertEqual(
            5,
            self.contract["control_view_projection_contract"][
                "operations_view_projection_count"
            ],
        )
        self.assertEqual(
            5,
            self.contract["control_view_projection_contract"][
                "report_snapshot_projection_count"
            ],
        )
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
        self.assertEqual(255, report["phase2_control_record_field_check_count"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(6, report["human_handling_required_count"])
        self.assertEqual(26, report["scenario_field_count"])
        self.assertEqual(156, report["scenario_field_check_count"])
        self.assertEqual(5, report["operations_version_control_view_count"])
        self.assertEqual(5, report["report_snapshot_version_control_view_count"])
        self.assertTrue(report["control_views_preserved"])
        self.assertTrue(report["all_control_references_opaque"])

    def test_each_required_exception_and_visibility_scenario_is_explicit(self):
        report = self._report()
        required_fields = set(self.contract["controlled_scenario_contract"]["required_fields"])
        expected_categories = self.contract["controlled_scenario_contract"][
            "scenario_order"
        ]
        self.assertEqual(
            expected_categories,
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(required_fields, set(scenario))
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
                    "referenced_building_version_ref",
                    "referenced_smoke_test_ref",
                    "referenced_switch_ref",
                    "referenced_rollback_ref",
                    "referenced_operations_view_ref",
                    "referenced_report_snapshot_ref",
                    "active_version_before_ref",
                    "observed_active_version_after_ref",
                ):
                    self.assertIn(":control:stage077-p2:", scenario[field])

    def test_build_not_complete_and_smoke_failure_both_keep_old_active_version(self):
        scenarios = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        build_not_complete = scenarios["build_not_complete_old_active_continues"]
        smoke_failure = scenarios["smoke_test_failure_blocks_switch"]
        self.assertEqual(
            "vector_background_building_keeps_active",
            build_not_complete["phase2_control_scenario"],
        )
        self.assertEqual(
            "hybrid_smoke_test_failure_blocks_switch",
            smoke_failure["phase2_control_scenario"],
        )
        self.assertEqual(
            "CONTROL_BACKGROUND_BUILD_NOT_STARTED",
            build_not_complete["observed_build_state"],
        )
        self.assertEqual("PENDING", build_not_complete["observed_smoke_test_status"])
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_BUILDING",
            build_not_complete["observed_switch_outcome"],
        )
        self.assertEqual("FAILED", smoke_failure["observed_smoke_test_status"])
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
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
            "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
            switch_failure["observed_switch_outcome"],
        )
        self.assertEqual(
            switch_failure["active_version_before_ref"],
            switch_failure["observed_active_version_after_ref"],
        )
        self.assertEqual(
            "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
            rollback["observed_rollback_state"],
        )
        self.assertEqual(
            "CONTROL_BACKGROUND_BUILD_NOT_STARTED", concurrent["observed_build_state"]
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
                self.assertIn(":control:stage077-p2:", view["operations_view_ref"])
        for view in report["report_snapshot_version_control_views"]:
            with self.subTest(view=view["control_scenario"]):
                self.assertEqual(set(self.module.REPORT_SNAPSHOT_FIELDS), set(view))
                self.assertEqual(
                    "CONTROL_REPORT_SNAPSHOT_INDEX_VERSION_VISIBLE_NOT_WRITTEN",
                    view["snapshot_state"],
                )
                self.assertIn(":control:stage077-p2:", view["report_snapshot_ref"])
        self.assertEqual(0, report["actual_operations_display_count"])
        self.assertEqual(0, report["actual_report_snapshot_count"])

    def test_invalid_or_malformed_phase2_fails_closed(self):
        invalid = self.module.build_background_index_build_phase3_report(
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
                phase2.execute_background_index_build_control_slice(
                    phase2.build_control_input()
                )
            )
            result["smoke_test_control_projections"][0].pop("smoke_test_ref")
            return result

        malformed_report = self.module.build_background_index_build_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_phase2_runtime_signal_fails_closed(self):
        phase2 = self._phase2()

        def runtime_signal(_control):
            result = copy.deepcopy(
                phase2.execute_background_index_build_control_slice(
                    phase2.build_control_input()
                )
            )
            result["actual_retrieval_query_performed"] = True
            return result

        report = self.module.build_background_index_build_phase3_report(
            phase2_executor=runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])

    def test_report_is_control_only_and_has_no_runtime_side_effect_flags(self):
        report = self._report()
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_background_build_count"])
        self.assertEqual(0, report["actual_index_build_count"])
        self.assertEqual(0, report["actual_smoke_test_count"])
        self.assertEqual(0, report["actual_retrieval_query_count"])
        self.assertEqual(0, report["actual_concurrent_retrieval_count"])
        self.assertEqual(0, report["actual_index_rollback_count"])
        self.assertEqual(0, report["actual_operations_display_count"])
        self.assertEqual(0, report["actual_report_snapshot_count"])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_current_machine_and_governance_projection_preserves_phase3_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P3",
                    "IDS-V0_1-STAGE077-P3",
                    "IDS-STAGE077-P4-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P4",
                    "IDS-V0_1-STAGE077-P4",
                    "IDS-STAGE077-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-REVIEW",
                    "IDS-V0_1-STAGE077-REVIEW",
                    "IDS-STAGE078-P1-GATE",
                ),
             ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE')),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE077-P3",
                "IDS-V0_1-STAGE077-P4",
                "IDS-V0_1-STAGE077-REVIEW",
             "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3"),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE077-P1-01",
                "ACC-STAGE077-P1-02",
                "ACC-STAGE077-P1-03",
                "ACC-STAGE077-P1-04",
                "ACC-STAGE077-P2-01",
                "ACC-STAGE077-P2-02",
                "ACC-STAGE077-P2-03",
                "ACC-STAGE077-P2-04",
                "ACC-STAGE077-P3-01",
                "ACC-STAGE077-P3-02",
                "ACC-STAGE077-P3-03",
                "ACC-STAGE077-P3-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE077-P3", run["task_id"])
        self.assertEqual(
            "PASS_BACKGROUND_INDEX_BUILD_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual(0, run["runtime_counts"]["actual_background_build_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_concurrent_retrieval_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["concurrent_retrieval_performed"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertFalse(run["runtime_actions"]["push_performed"])
        self.assertIn("EVT-IDS-V0_1-STAGE077-P3-20260821-001", event_ids)
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE077"', roadmap_text)
        self.assertTrue(
            'current_phase_id: "IDS-STAGE077-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE077-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE077-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE077-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE077-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE077-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P1-GATE"' in roadmap_text
        )


if __name__ == "__main__":
    unittest.main()
