import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE079_PHASE1_ATOMIC_INDEX_SWITCH_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage079_atomic_index_switch_contract.json"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-079_索引原子切换.md"
PREDECESSOR_REVIEW = BASE / "STAGE078_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = BASE / "index_version_schema" / "stage078_index_smoke_test_contract.json"


class Stage079AtomicIndexSwitchPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (SCOPE, CONTRACT, TASKPACK, PREDECESSOR_REVIEW, PREDECESSOR_CONTRACT):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual("ids.stage079.atomic_index_switch.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-079", contract["stage"])
        self.assertEqual("IDS-STAGE079-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE079-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-079", contract["acceptance_id"])
        self.assertEqual("PHASE1_ATOMIC_INDEX_SWITCH_CONTRACT_RUNTIME_DISABLED", contract["contract_state"])
        self.assertEqual("IDS-STAGE079-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual("FROZEN_STAGE079_TASKPACK_AND_STAGE078_REVIEWED_INDEX_SMOKE_TEST_CONTRACTS_ONLY", source["authority"])
        for field in ("second_authoritative_source_created", "source_body_or_path_allowed", "raw_metadata_content_access_allowed", "live_source_read_performed", "authorized_fixture_access_performed"):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_index_pointer_build_shadow_and_smoke_shapes_are_fixed(self):
        pointer = self.contract["index_version_and_active_pointer_contract"]
        self.assertEqual(pointer["index_version_field_count"], len(pointer["future_index_version_fields"]))
        self.assertEqual(pointer["active_pointer_field_count"], len(pointer["future_active_pointer_fields"]))
        self.assertTrue(pointer["one_active_version_per_index_kind_required"])
        self.assertTrue(pointer["reuses_stage078_control_field_shapes_only"])
        self.assertTrue(pointer["all_values_are_control_labels_only"])
        self.assertFalse(pointer["active_pointer_read_allowed_in_phase1"])
        self.assertFalse(pointer["active_pointer_write_allowed_in_phase1"])
        build = self.contract["building_version_shadow_and_smoke_contract"]
        self.assertEqual(build["building_and_shadow_field_count"], len(build["future_building_and_shadow_fields"]))
        self.assertEqual(build["smoke_test_input_field_count"], len(build["future_smoke_test_input_fields"]))
        self.assertEqual(build["smoke_test_output_field_count"], len(build["future_smoke_test_output_fields"]))
        self.assertTrue(build["new_candidate_required_after_each_bulk_import"])
        self.assertTrue(build["candidate_must_not_overwrite_active_version"])
        self.assertTrue(build["candidate_must_remain_isolated_before_smoke_test"])
        self.assertTrue(build["old_active_index_must_continue_serving_during_build_smoke_and_switch"])

    def test_atomic_switch_rollback_and_fail_closed_rules_are_explicit(self):
        switch = self.contract["atomic_switch_and_rollback_contract"]
        self.assertEqual(switch["switch_record_field_count"], len(switch["future_switch_record_fields"]))
        self.assertEqual(switch["rollback_proof_field_count"], len(switch["future_rollback_proof_fields"]))
        self.assertEqual(switch["condition_count"], len(switch["required_conditions"]))
        for field in ("future_atomic_switch_required", "failed_or_missing_smoke_test_blocks_switch", "active_pointer_must_remain_unchanged_on_failure", "previous_active_index_version_must_be_retained", "future_rollback_target_must_be_previous_active_index_version"):
            with self.subTest(field=field):
                self.assertTrue(switch[field])
        for field in ("switch_record_write_allowed_in_phase1", "rollback_proof_write_allowed_in_phase1", "active_pointer_switch_allowed_in_phase1", "automatic_rollback_execution_allowed", "actual_atomic_switch_performed", "actual_index_rollback_performed"):
            with self.subTest(field=field):
                self.assertFalse(switch[field])
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in ("SMOKE_TEST_FAILED", "SMOKE_TEST_RESULT_MISSING", "ACTIVE_POINTER_SWITCH_WITHOUT_PASSED_SMOKE_TEST", "ROLLBACK_TARGET_NOT_RETAINED", "PHASE1_ATOMIC_SWITCH_OR_ROLLBACK_NOT_AUTHORIZED"):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])

    def test_runtime_protected_surface_and_later_phase_boundaries_remain_zero(self):
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in ("stage078_review_evidence_declared", "stage079_started", "stage079_entry_authorized", "phase1_started"):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in ("phase2_started", "phase3_started", "phase4_started", "whole_stage_review_performed", "stage080_started", "github_upload_allowed", "push_allowed"):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_scope_keeps_active_service_and_next_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in ("不建立第二权威事实源", "旧活动索引在构建、未来冒烟测试和未来切换前继续服务", "活动指针保持不变", "IDS-STAGE079-P2-GATE"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
