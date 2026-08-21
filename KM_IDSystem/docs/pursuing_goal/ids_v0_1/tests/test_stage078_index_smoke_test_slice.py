import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage078_index_smoke_test_slice as slice_module,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-078_索引冒烟测试.md"
)
P1_SCOPE = BASE / "STAGE078_PHASE1_INDEX_SMOKE_TEST_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage078_index_smoke_test_contract.json"
P2_SCOPE = BASE / "STAGE078_PHASE2_INDEX_SMOKE_TEST_CONTROL_SLICE.md"
P2_CONTRACT = BASE / "index_version_schema" / "stage078_index_smoke_test_slice_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE077_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage077_background_index_build_contract.json"
)


class Stage078IndexSmokeTestPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(P2_CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = slice_module.build_control_input()
        cls.result = slice_module.execute_index_smoke_test_control_slice(
            cls.control_input
        )

    def test_phase2_artifacts_and_identity_are_fixed(self):
        for artifact in (
            TASKPACK,
            P1_SCOPE,
            P1_CONTRACT,
            P2_SCOPE,
            P2_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

        self.assertEqual(
            "ids.stage078.index_smoke_test.phase2.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("IDS-STAGE078-P2", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE078-P2", self.contract["task_id"])
        self.assertEqual(
            "PHASE2_INDEX_SMOKE_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["slice_executable"])
        self.assertFalse(self.contract["execution_ready"])
        self.assertEqual("IDS-STAGE078-P3-GATE", self.contract["next_gate"])

    def test_single_authority_and_phase1_reuse_boundaries_are_explicit(self):
        source = self.contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE078_TASKPACK_AND_STAGE078_PHASE1_AND_STAGE077_REVIEWED_BACKGROUND_INDEX_BUILD_CONTRACTS_ONLY",
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

        reuse = self.contract["phase1_reuse_contract"]
        self.assertTrue(reuse["stage078_phase1_contract_required"])
        self.assertEqual(
            "PHASE1_INDEX_SMOKE_TEST_CONTRACT_RUNTIME_DISABLED",
            reuse["stage078_phase1_contract_state"],
        )
        self.assertTrue(
            reuse["stage077_reviewed_background_index_build_contract_remains_authoritative"]
        )
        self.assertTrue(reuse["stage078_may_not_replace_predecessor_contract"])

    def test_fixed_control_input_is_exact_reference_only_and_zero_count(self):
        input_contract = self.contract["reference_only_control_input_contract"]
        self.assertEqual(
            (input_contract["control_input_field"],), slice_module.CONTROL_FIELDS
        )
        self.assertEqual(
            input_contract["control_request_order"],
            list(slice_module.CONTROL_SCENARIOS),
        )
        self.assertEqual(
            input_contract["control_request_count"], len(slice_module.CONTROL_SCENARIOS)
        )
        self.assertEqual(input_contract["input_fields"], list(slice_module.INPUT_FIELDS))
        self.assertEqual(input_contract["input_field_count"], len(slice_module.INPUT_FIELDS))

        requests = self.control_input[input_contract["control_input_field"]]
        self.assertEqual(len(slice_module.CONTROL_SCENARIOS), len(requests))
        for scenario, request in zip(slice_module.CONTROL_SCENARIOS, requests):
            with self.subTest(scenario=scenario):
                self.assertEqual(slice_module.build_control_request(scenario), request)
                self.assertEqual(set(slice_module.INPUT_FIELDS), set(request))
                self.assertEqual(0, request["chunk_count"])
                for field in (
                    "source_import_ref",
                    "document_scope_ref",
                    "embedding_model_ref",
                    "candidate_index_version_ref",
                    "active_index_version_ref",
                    "previous_active_index_version_ref",
                    "shadow_index_ref",
                ):
                    self.assertIn(":control:stage078-p2:", request[field])

    def test_control_projection_shapes_counts_and_required_index_fields(self):
        result = self.result
        projection = self.contract["control_projection_contract"]
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_INDEX_SMOKE_TEST_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(5, result["control_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(5, result["index_version_control_record_count"])
        self.assertEqual(5, result["candidate_build_control_projection_count"])
        self.assertEqual(5, result["active_pointer_control_projection_count"])
        self.assertEqual(5, result["smoke_test_control_projection_count"])
        self.assertEqual(5, result["switch_control_projection_count"])
        self.assertEqual(5, result["rollback_control_projection_count"])
        self.assertTrue(result["all_control_records_keep_required_shapes"])
        self.assertEqual(
            projection["index_version_control_record_fields"],
            list(slice_module.INDEX_VERSION_RECORD_FIELDS),
        )
        self.assertEqual(
            projection["candidate_build_control_projection_fields"],
            list(slice_module.CANDIDATE_BUILD_FIELDS),
        )
        self.assertEqual(
            projection["active_pointer_control_projection_fields"],
            list(slice_module.ACTIVE_POINTER_FIELDS),
        )
        self.assertEqual(
            projection["smoke_test_control_projection_fields"],
            list(slice_module.SMOKE_TEST_PROJECTION_FIELDS),
        )
        for record in result["index_version_control_records"]:
            with self.subTest(index_version=record["index_version"]):
                self.assertEqual(0, record["chunk_count"])
                self.assertIn(":control:stage078-p2:", record["document_scope_ref"])
                self.assertIn(":control:stage078-p2:", record["embedding_model_ref"])

    def test_passed_smoke_test_only_projects_a_future_switch_candidate(self):
        result = self.result
        passed = next(
            record
            for record in result["smoke_test_control_projections"]
            if record["control_scenario"] == "fulltext_smoke_passed_switch_candidate"
        )
        switch = next(
            record
            for record in result["switch_control_projections"]
            if record["control_scenario"] == passed["control_scenario"]
        )
        self.assertEqual("PASSED", passed["smoke_test_status"])
        self.assertTrue(passed["switch_eligible"])
        self.assertEqual(
            "CONTROL_ATOMIC_SWITCH_CANDIDATE_NOT_APPLIED", switch["switch_outcome"]
        )
        self.assertFalse(switch["switch_applied"])
        self.assertTrue(switch["active_service_continues"])
        self.assertTrue(result["all_switch_projections_keep_active_pointer_unchanged"])

    def test_build_not_complete_and_smoke_failures_block_switch(self):
        result = self.result
        projections = {
            record["control_scenario"]: record
            for record in result["smoke_test_control_projections"]
        }
        switches = {
            record["control_scenario"]: record
            for record in result["switch_control_projections"]
        }
        for scenario, outcome in (
            (
                "vector_build_incomplete_keeps_active",
                "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
            ),
            (
                "hybrid_smoke_test_failure_blocks_switch",
                "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
            ),
        ):
            with self.subTest(scenario=scenario):
                self.assertFalse(projections[scenario]["switch_eligible"])
                self.assertEqual(outcome, switches[scenario]["switch_outcome"])
                self.assertFalse(switches[scenario]["switch_applied"])
                self.assertTrue(switches[scenario]["active_service_continues"])
        self.assertTrue(result["all_nonpassed_smoke_tests_block_switch"])
        self.assertEqual(1, result["control_build_not_complete_count"])
        self.assertEqual(1, result["control_smoke_test_not_run_count"])
        self.assertEqual(1, result["control_smoke_test_failed_count"])

    def test_switch_failure_rollback_retention_and_rejected_input_are_fail_closed(self):
        result = self.result
        switch_failure = next(
            record
            for record in result["switch_control_projections"]
            if record["control_scenario"] == "fulltext_switch_failure_preserves_active"
        )
        rollback = next(
            record
            for record in result["rollback_control_projections"]
            if record["control_scenario"] == "hybrid_rollback_candidate_retains_previous"
        )
        self.assertEqual(
            "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED", switch_failure["switch_outcome"]
        )
        self.assertFalse(switch_failure["switch_applied"])
        self.assertEqual(
            "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
            rollback["rollback_state"],
        )
        self.assertEqual(
            rollback["previous_active_index_version_ref"],
            rollback["rollback_target_index_version_ref"],
        )
        self.assertFalse(rollback["rollback_applied"])
        self.assertTrue(result["all_rollback_targets_reference_retained_previous_active"])

        rejected = slice_module.execute_index_smoke_test_control_slice({})
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_CONTROL_INPUT_RUNTIME_DISABLED", rejected["execution_state"]
        )
        self.assertEqual("CONTROL_INPUT_REJECTED", rejected["rejection_reason"])
        self.assertTrue(
            all(rejected[field] is False for field in slice_module.RUNTIME_CLOSED_FIELDS)
        )

    def test_runtime_stage_and_protected_boundaries_remain_closed(self):
        self.assertTrue(
            all(self.result[field] is False for field in slice_module.RUNTIME_CLOSED_FIELDS)
        )
        self.assertEqual(
            set(slice_module.RUNTIME_CLOSED_FIELDS),
            set(self.contract["runtime_boundary"]),
        )
        for section in (
            "runtime_boundary",
            "protected_surface_boundary",
        ):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        self.assertTrue(boundary["stage078_phase1_completed"])
        self.assertTrue(boundary["stage078_phase2_started"])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage079_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertEqual(
            self.contract["chinese_feedback_contract"]["feedbacks"],
            self.result["chinese_feedback"],
        )


if __name__ == "__main__":
    unittest.main()
