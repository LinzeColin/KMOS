import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE077_PHASE1_BACKGROUND_INDEX_BUILD_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage077_background_index_build_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-077_后台索引构建.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE076_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = BASE / "index_version_schema" / "stage076_index_version_schema_contract.json"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage077-p1-local.json"


class Stage077BackgroundIndexBuildPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual("ids.stage077.background_index_build.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-077", contract["stage"])
        self.assertEqual("IDS-STAGE077-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE077-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-077", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_BACKGROUND_INDEX_BUILD_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE077-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE077_TASKPACK_AND_STAGE076_REVIEWED_INDEX_VERSION_CONTRACTS_ONLY",
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
        self.assertTrue(predecessor["stage076_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_INDEX_VERSION_SCHEMA_RUNTIME_DISABLED",
            predecessor["stage076_review_result"],
        )
        self.assertTrue(predecessor["reviewed_index_version_schema_remains_authoritative"])
        self.assertTrue(predecessor["stage077_may_not_replace_predecessor_contract"])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_background_build_input_output_and_lifecycle_are_fixed(self):
        contract = self.contract["background_build_input_output_contract"]
        self.assertEqual("FUTURE_BULK_IMPORT_COMPLETED", contract["future_trigger"])
        self.assertEqual(contract["input_field_count"], len(contract["future_required_input_fields"]))
        self.assertEqual(contract["output_field_count"], len(contract["future_required_output_fields"]))
        for field in (
            "source_import_ref",
            "document_scope_ref",
            "chunk_count",
            "embedding_model_ref",
            "index_kind",
            "candidate_index_version_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(field, contract["future_required_input_fields"])
        self.assertTrue(contract["all_values_are_control_labels_only"])
        self.assertFalse(contract["background_build_execution_allowed_in_phase1"])
        for field, value in contract.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        lifecycle = self.contract["background_build_lifecycle_contract"]
        self.assertEqual(lifecycle["state_count"], len(lifecycle["declared_states"]))
        self.assertIn("BUILDING", lifecycle["declared_states"])
        self.assertIn("FAILED", lifecycle["declared_states"])
        self.assertTrue(lifecycle["new_candidate_required_after_each_bulk_import"])
        self.assertTrue(lifecycle["candidate_must_not_overwrite_active_version"])
        self.assertTrue(lifecycle["active_index_must_continue_serving_during_build"])
        self.assertTrue(lifecycle["candidate_must_remain_isolated_before_switch"])
        for field, value in lifecycle.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_smoke_switch_rollback_and_fail_closed_rules_are_explicit(self):
        switch = self.contract["smoke_and_atomic_switch_contract"]
        self.assertEqual(switch["condition_count"], len(switch["required_conditions"]))
        self.assertTrue(switch["passed_smoke_test_required_before_switch"])
        self.assertTrue(switch["failed_or_missing_smoke_test_blocks_switch"])
        self.assertTrue(switch["future_atomic_switch_required"])
        self.assertTrue(switch["active_pointer_must_remain_unchanged_on_failure"])
        self.assertFalse(switch["smoke_test_execution_allowed_in_phase1"])
        self.assertFalse(switch["active_pointer_switch_allowed_in_phase1"])
        for field, value in switch.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        rollback = self.contract["rollback_and_retention_contract"]
        self.assertTrue(rollback["previous_active_index_version_must_be_retained"])
        self.assertTrue(rollback["future_rollback_target_must_be_previous_active_index_version"])
        self.assertTrue(rollback["old_active_index_must_continue_serving_until_successful_switch"])
        self.assertFalse(rollback["automatic_rollback_execution_allowed"])
        self.assertFalse(rollback["actual_old_index_retention_record_created"])
        self.assertFalse(rollback["actual_index_rollback_performed"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "BACKGROUND_BUILD_FAILED",
            "SMOKE_TEST_FAILED",
            "ACTIVE_POINTER_SWITCH_WITHOUT_PASSED_SMOKE_TEST",
            "ROLLBACK_TARGET_NOT_RETAINED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["automatic_active_pointer_switch_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_chinese_feedback_runtime_and_phase_boundaries_remain_zero(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertEqual(feedback["feedback_count"], len(feedback["feedbacks"]))
        self.assertTrue(feedback["business_line_whitebox_human_review_required_for_future_exception"])
        self.assertFalse(feedback["actual_user_feedback_emitted"])

        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)

        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage076_review_evidence_declared",
            "stage077_started",
            "stage077_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage078_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

        for field, value in self.contract["protected_surface_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_governance_projection_preserves_phase1_evidence(self):
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
                    "IDS-V0_1-STAGE077-P1",
                    "IDS-V0_1-STAGE077-P1",
                    "IDS-STAGE077-P2-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P2",
                    "IDS-V0_1-STAGE077-P2",
                    "IDS-STAGE077-P3-GATE",
                ),
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
             ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE077-P1",
                "IDS-V0_1-STAGE077-P2",
                "IDS-V0_1-STAGE077-P3",
                "IDS-V0_1-STAGE077-P4",
                "IDS-V0_1-STAGE077-REVIEW",
             "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3"),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE077-P1-01",
                "ACC-STAGE077-P1-02",
                "ACC-STAGE077-P1-03",
                "ACC-STAGE077-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE077-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_background_build_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_index_build_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_smoke_test_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE077"', roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE077-P1"', roadmap_text)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE077-P1"', roadmap_text)
        self.assertIn("EVT-IDS-V0_1-STAGE077-P1-20260821-001", event_ids)


if __name__ == "__main__":
    unittest.main()
