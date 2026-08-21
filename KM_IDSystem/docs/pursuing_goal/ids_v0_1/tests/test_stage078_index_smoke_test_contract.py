import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE078_PHASE1_INDEX_SMOKE_TEST_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage078_index_smoke_test_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-078_索引冒烟测试.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE077_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage077_background_index_build_contract.json"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage078-p1-local.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
EVENT_ID = "EVT-IDS-V0_1-STAGE078-P1-20260821-001"


class Stage078IndexSmokeTestPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_and_predecessor_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            ROADMAP,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
            EVENTS,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual("ids.stage078.index_smoke_test.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-078", contract["stage"])
        self.assertEqual("IDS-STAGE078-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE078-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-078", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_INDEX_SMOKE_TEST_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE078-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE078_TASKPACK_AND_STAGE077_REVIEWED_BACKGROUND_INDEX_BUILD_CONTRACTS_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage077_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_BACKGROUND_INDEX_BUILD_RUNTIME_DISABLED",
            predecessor["stage077_review_result"],
        )
        self.assertTrue(predecessor["reviewed_background_index_build_contract_remains_authoritative"])
        self.assertTrue(predecessor["stage078_may_not_replace_predecessor_contract"])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_index_build_shadow_and_active_service_contracts_are_fixed(self):
        version_and_pointer = self.contract["index_version_and_active_pointer_contract"]
        self.assertEqual(
            version_and_pointer["index_version_field_count"],
            len(version_and_pointer["future_index_version_fields"]),
        )
        self.assertEqual(
            version_and_pointer["active_pointer_field_count"],
            len(version_and_pointer["future_active_pointer_fields"]),
        )
        self.assertTrue(version_and_pointer["one_active_version_per_index_kind_required"])
        self.assertTrue(version_and_pointer["all_values_are_control_labels_only"])
        self.assertFalse(version_and_pointer["active_pointer_read_allowed_in_phase1"])
        self.assertFalse(version_and_pointer["active_pointer_write_allowed_in_phase1"])

        building = self.contract["building_version_and_shadow_index_contract"]
        self.assertEqual(building["field_count"], len(building["future_required_fields"]))
        self.assertTrue(building["new_candidate_required_after_each_bulk_import"])
        self.assertTrue(building["candidate_must_not_overwrite_active_version"])
        self.assertTrue(building["candidate_must_remain_isolated_before_smoke_test"])
        self.assertTrue(building["old_active_index_must_continue_serving_during_build_and_smoke_test"])
        for field, value in building.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_smoke_switch_rollback_and_fail_closed_rules_are_explicit(self):
        smoke = self.contract["smoke_test_contract"]
        self.assertEqual(smoke["input_field_count"], len(smoke["future_required_input_fields"]))
        self.assertEqual(smoke["output_field_count"], len(smoke["future_required_output_fields"]))
        self.assertTrue(smoke["passed_smoke_test_required_before_switch"])
        self.assertTrue(smoke["failed_or_missing_smoke_test_blocks_switch"])
        self.assertTrue(smoke["failed_smoke_test_must_not_replace_active_version"])
        self.assertFalse(smoke["smoke_test_execution_allowed_in_phase1"])

        switch = self.contract["future_switch_and_rollback_contract"]
        self.assertEqual(switch["condition_count"], len(switch["required_conditions"]))
        self.assertTrue(switch["future_atomic_switch_required"])
        self.assertTrue(switch["active_pointer_must_remain_unchanged_on_failure"])
        self.assertTrue(switch["previous_active_index_version_must_be_retained"])
        self.assertTrue(switch["future_rollback_target_must_be_previous_active_index_version"])
        self.assertFalse(switch["automatic_rollback_execution_allowed"])
        self.assertFalse(switch["active_pointer_switch_allowed_in_phase1"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "SMOKE_TEST_FAILED",
            "SMOKE_TEST_RESULT_MISSING",
            "ACTIVE_POINTER_SWITCH_WITHOUT_PASSED_SMOKE_TEST",
            "ROLLBACK_TARGET_NOT_RETAINED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["automatic_active_pointer_switch_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_runtime_and_phase_boundaries_remain_zero(self):
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)

        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage077_review_evidence_declared",
            "stage078_started",
            "stage078_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage079_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        for field, value in self.contract["protected_surface_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_governance_projection_and_scope_preserve_p1_history_or_successor_boundary(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current_route = (
            status["stage"],
            status["phase"],
            status["task"],
            status["next_gate"],
        )
        self.assertIn(
            current_route,
            {
                (
                    "IDS-STAGE078",
                    "IDS-V0_1-STAGE078-P1",
                    "IDS-V0_1-STAGE078-P1",
                    "IDS-STAGE078-P2-GATE",
                ),
                (
                    "IDS-STAGE078",
                    "IDS-V0_1-STAGE078-P2",
                    "IDS-V0_1-STAGE078-P2",
                    "IDS-STAGE078-P3-GATE",
                ),
                (
                    "IDS-STAGE078",
                    "IDS-V0_1-STAGE078-P3",
                    "IDS-V0_1-STAGE078-P3",
                    "IDS-STAGE078-P4-GATE",
                ),
                (
                    "IDS-STAGE078",
                    "IDS-V0_1-STAGE078-P4",
                    "IDS-V0_1-STAGE078-P4",
                    "IDS-STAGE078-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE078",
                    "IDS-STAGE078-REVIEW",
                    "IDS-V0_1-STAGE078-REVIEW",
                    "IDS-STAGE079-P1-GATE",
                ),

                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"),},
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertEqual(current_route[2], plan["task"])
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE-078",
                "ACC-STAGE078-P1-01",
                "ACC-STAGE078-P1-02",
                "ACC-STAGE078-P1-03",
                "ACC-STAGE078-P1-04",
            }.issubset(acceptance_ids)
        )
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE078-P1", run["task_id"])
        self.assertEqual(
            "PASS_INDEX_SMOKE_TEST_CONTRACT_RUNTIME_DISABLED", run["result"]
        )
        self.assertTrue(
            all(value == 0 for value in run["runtime_counts"].values())
        )
        self.assertTrue(
            all(value is False for value in run["runtime_actions"].values())
        )
        self.assertFalse(run["validation"]["second_authoritative_source_created"])
        self.assertFalse(run["validation"]["stage078_phase2_started"])
        self.assertEqual("IDS-STAGE078-P2-GATE", run["next_gate"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            (item for item in events if item.get("event_id") == EVENT_ID), None
        )
        self.assertIsNotNone(event)
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE078-P1", event["task_id"])
        event_refs = {item["ref"] for item in event["evidence_refs"]}
        self.assertTrue(
            {
                f"{ROOT.name}/{TASKPACK.relative_to(ROOT)}",
                f"{ROOT.name}/{SCOPE.relative_to(ROOT)}",
                f"{ROOT.name}/{CONTRACT.relative_to(ROOT)}",
                f"{ROOT.name}/{RUN.relative_to(ROOT)}",
            }.issubset(event_refs)
        )
        self.assertIn("actual_smoke_test_count=0", event["notes"])
        self.assertIn("stage078_phase2_started=false", event["notes"])
        self.assertIn("next_gate=IDS-STAGE078-P2-GATE", event["notes"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for phrase in (
            'current_stage_id: "IDS-STAGE078"',
            'stage_id: "IDS-STAGE078"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)
        if current_route[1] == "IDS-V0_1-STAGE078-P1":
            expected_roadmap_route = (
                'current_phase_id: "IDS-STAGE078-P1"',
                'current_task_id: "IDS-V0_1-STAGE078-P1"',
                'next_gate_id: "IDS-STAGE078-P2-GATE"',
            )
        elif current_route[1] == "IDS-V0_1-STAGE078-P2":
            expected_roadmap_route = (
                'current_phase_id: "IDS-STAGE078-P2"',
                'current_task_id: "IDS-V0_1-STAGE078-P2"',
                'next_gate_id: "IDS-STAGE078-P3-GATE"',
            )
        elif current_route[1] == "IDS-V0_1-STAGE078-P3":
            expected_roadmap_route = (
                'current_phase_id: "IDS-STAGE078-P3"',
                'current_task_id: "IDS-V0_1-STAGE078-P3"',
                'next_gate_id: "IDS-STAGE078-P4-GATE"',
            )
        elif current_route[1] == "IDS-V0_1-STAGE078-P4":
            expected_roadmap_route = (
                'current_phase_id: "IDS-STAGE078-P4"',
                'current_task_id: "IDS-V0_1-STAGE078-P4"',
                'next_gate_id: "IDS-STAGE078-REVIEW-GATE"',
            )
        else:
            expected_roadmap_route = (
                'current_phase_id: "IDS-STAGE078-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE078-REVIEW"',
                'next_gate_id: "IDS-STAGE079-P1-GATE"',
            )
        for phrase in expected_roadmap_route:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)

        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "旧活动索引在构建与未来测试期间继续服务",
            "活动指针保持不变",
            "IDS-STAGE078-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
