import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE079_PHASE2_ATOMIC_INDEX_SWITCH_CONTROL_SLICE.md"
CONTRACT = BASE / "index_version_schema" / "stage079_atomic_index_switch_slice_contract.json"
MODULE = BASE / "index_version_schema" / "stage079_atomic_index_switch_control_slice.py"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-079_索引原子切换.md"
P1_SCOPE = BASE / "STAGE079_PHASE1_ATOMIC_INDEX_SWITCH_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage079_atomic_index_switch_contract.json"
STAGE078_REVIEW = BASE / "STAGE078_STAGE_REVIEW.md"


def load_module():
    spec = importlib.util.spec_from_file_location("stage079_slice", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


slice_module = load_module()


class Stage079AtomicIndexSwitchPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = slice_module.build_control_input()
        cls.result = slice_module.execute_atomic_index_switch_control_slice(
            cls.control_input
        )

    def test_frozen_sources_and_phase_identity_are_explicit(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P1_SCOPE,
            P1_CONTRACT,
            STAGE078_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage079.atomic_index_switch.phase2.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-079", self.contract["stage"])
        self.assertEqual("IDS-STAGE079-P2", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE079-P2", self.contract["task_id"])
        self.assertEqual("ACC-STAGE-079", self.contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_ATOMIC_INDEX_SWITCH_CONTROL_SLICE_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE079-P3-GATE", self.contract["next_gate"])
        self.assertTrue(self.contract["slice_executable"])
        source = self.contract["source_authority"]
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_fixed_non_business_control_input_has_exact_shape(self):
        input_contract = self.contract["reference_only_control_input_contract"]
        requests = self.control_input[slice_module.CONTROL_FIELDS[0]]
        self.assertEqual(input_contract["control_request_count"], len(requests))
        self.assertEqual(
            input_contract["fixed_control_scenarios"],
            list(slice_module.CONTROL_SCENARIOS),
        )
        self.assertEqual(input_contract["input_field_count"], len(slice_module.INPUT_FIELDS))
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(slice_module.INPUT_FIELDS), set(request))
                self.assertEqual(0, request["chunk_count"])
                self.assertIn(
                    input_contract["control_prefix"],
                    request["candidate_index_version_ref"],
                )
                self.assertNotEqual(
                    request["candidate_index_version_ref"],
                    request["active_index_version_ref"],
                )
                self.assertNotEqual(
                    request["previous_active_index_version_ref"],
                    request["active_index_version_ref"],
                )

    def test_control_output_fields_and_counts_are_fixed(self):
        output = self.result
        projection = self.contract["control_projection_contract"]
        self.assertTrue(output["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_ATOMIC_INDEX_SWITCH_CONTROL_SLICE",
            output["execution_state"],
        )
        self.assertEqual(0, output["actual_input_request_count"])
        for output_key, count_key, field_key, field_names in (
            (
                "index_version_control_records",
                "index_version_control_record_count",
                "index_version_record_fields",
                slice_module.INDEX_VERSION_RECORD_FIELDS,
            ),
            (
                "candidate_build_control_projections",
                "candidate_build_control_projection_count",
                "candidate_build_fields",
                slice_module.CANDIDATE_BUILD_FIELDS,
            ),
            (
                "active_pointer_control_projections",
                "active_pointer_control_projection_count",
                "active_pointer_fields",
                slice_module.ACTIVE_POINTER_FIELDS,
            ),
            (
                "smoke_test_control_projections",
                "smoke_test_control_projection_count",
                "smoke_test_fields",
                slice_module.SMOKE_TEST_PROJECTION_FIELDS,
            ),
            (
                "switch_control_projections",
                "switch_control_projection_count",
                "switch_projection_fields",
                slice_module.SWITCH_PROJECTION_FIELDS,
            ),
            (
                "rollback_control_projections",
                "rollback_control_projection_count",
                "rollback_projection_fields",
                slice_module.ROLLBACK_PROJECTION_FIELDS,
            ),
        ):
            with self.subTest(output_key=output_key):
                self.assertEqual(5, output[count_key])
                self.assertEqual(list(field_names), projection[field_key])
                for record in output[output_key]:
                    self.assertEqual(set(field_names), set(record))

    def test_candidate_isolation_and_active_service_continuity_hold(self):
        self.assertTrue(self.result["all_candidate_versions_are_isolated"])
        self.assertTrue(self.result["all_old_active_versions_continue_serving"])
        self.assertTrue(self.result["all_active_pointer_projections_unchanged"])
        for build, pointer in zip(
            self.result["candidate_build_control_projections"],
            self.result["active_pointer_control_projections"],
        ):
            with self.subTest(candidate=build["candidate_index_version_ref"]):
                self.assertTrue(build["candidate_isolated_from_active_service"])
                self.assertTrue(build["active_service_continuity_asserted"])
                self.assertEqual(
                    "CONTROL_ACTIVE_POINTER_UNCHANGED_RUNTIME_DISABLED",
                    pointer["pointer_state"],
                )

    def test_build_and_smoke_failures_block_switch_without_mutation(self):
        switches = {
            item["control_scenario"]: item
            for item in self.result["switch_control_projections"]
        }
        smoke = {
            item["control_scenario"]: item
            for item in self.result["smoke_test_control_projections"]
        }
        incomplete = "vector_build_incomplete_preserves_active"
        failed = "hybrid_smoke_test_failure_blocks_switch"
        self.assertFalse(smoke[incomplete]["switch_eligible"])
        self.assertFalse(smoke[failed]["switch_eligible"])
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_BUILD_NOT_COMPLETE",
            switches[incomplete]["switch_outcome"],
        )
        self.assertEqual(
            "CONTROL_SWITCH_BLOCKED_SMOKE_TEST_FAILED",
            switches[failed]["switch_outcome"],
        )
        for scenario in (incomplete, failed):
            with self.subTest(scenario=scenario):
                self.assertFalse(switches[scenario]["switch_applied"])
                self.assertEqual(
                    switches[scenario]["active_index_version_ref"],
                    switches[scenario]["resulting_active_index_version_ref"],
                )

    def test_success_candidate_and_switch_failure_are_unapplied(self):
        switches = {
            item["control_scenario"]: item
            for item in self.result["switch_control_projections"]
        }
        candidate = switches["fulltext_smoke_passed_switch_candidate"]
        failure = switches["fulltext_switch_failure_preserves_active"]
        self.assertTrue(candidate["switch_eligible"])
        self.assertEqual(
            "CONTROL_ATOMIC_SWITCH_CANDIDATE_NOT_APPLIED",
            candidate["switch_outcome"],
        )
        self.assertTrue(failure["switch_eligible"])
        self.assertEqual(
            "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
            failure["switch_outcome"],
        )
        self.assertFalse(candidate["switch_applied"])
        self.assertFalse(failure["switch_applied"])

    def test_rollback_only_references_retained_previous_active_version(self):
        rollback = {
            item["control_scenario"]: item
            for item in self.result["rollback_control_projections"]
        }["hybrid_rollback_candidate_retains_previous"]
        self.assertEqual(
            "CONTROL_ROLLBACK_TO_RETAINED_PREVIOUS_ACTIVE_PROJECTED",
            rollback["rollback_state"],
        )
        self.assertEqual(
            rollback["previous_active_index_version_ref"],
            rollback["rollback_target_index_version_ref"],
        )
        self.assertFalse(rollback["rollback_applied"])
        self.assertTrue(
            self.result["all_rollback_targets_reference_retained_previous_active"]
        )

    def test_rejected_input_and_all_runtime_boundaries_remain_closed(self):
        rejected = slice_module.execute_atomic_index_switch_control_slice({})
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_CONTROL_INPUT_RUNTIME_DISABLED",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_REJECTED", rejected["rejection_reason"])
        self.assertTrue(
            all(rejected[field] is False for field in slice_module.RUNTIME_CLOSED_FIELDS)
        )
        self.assertEqual(
            set(slice_module.RUNTIME_CLOSED_FIELDS),
            set(self.contract["runtime_boundary"]),
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        self.assertTrue(boundary["stage079_phase1_completed"])
        self.assertTrue(boundary["stage079_phase2_started"])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage080_started",
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

