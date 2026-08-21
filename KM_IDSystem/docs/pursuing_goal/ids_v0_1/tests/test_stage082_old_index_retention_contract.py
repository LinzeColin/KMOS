import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE082_PHASE1_OLD_INDEX_RETENTION_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage082_old_index_retention_contract.json"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-082_旧索引保留策略.md"
PREDECESSOR_REVIEW = BASE / "STAGE081_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = BASE / "index_version_schema" / "stage081_shadow_index_contract.json"
PREDECESSOR_DELIVERY = BASE / "index_version_schema" / "stage081_shadow_index_delivery_contract.json"


class Stage082OldIndexRetentionPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_DELIVERY,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage082.old_index_retention_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-082", contract["stage"])
        self.assertEqual("IDS-STAGE082-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE082-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-082", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_OLD_INDEX_RETENTION_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE082-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE082_TASKPACK_AND_STAGE081_REVIEWED_SHADOW_INDEX_CONTRACTS_ONLY",
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

    def test_index_pointer_build_and_smoke_shapes_are_fixed(self):
        shape = self.contract["index_version_active_pointer_build_and_smoke_contract"]
        self.assertEqual(shape["index_version_field_count"], len(shape["future_index_version_fields"]))
        self.assertEqual(shape["active_pointer_field_count"], len(shape["future_active_pointer_fields"]))
        self.assertEqual(
            shape["building_and_shadow_field_count"],
            len(shape["future_building_and_shadow_fields"]),
        )
        self.assertEqual(
            shape["smoke_test_input_field_count"],
            len(shape["future_smoke_test_input_fields"]),
        )
        self.assertEqual(
            shape["smoke_test_output_field_count"],
            len(shape["future_smoke_test_output_fields"]),
        )
        for field in (
            "one_active_version_per_index_kind_required",
            "new_candidate_required_after_each_bulk_import",
            "candidate_must_not_overwrite_active_version",
            "shadow_index_must_remain_isolated_before_smoke_test",
            "old_active_index_must_continue_serving_during_build_smoke_switch_rollback_and_retention_confirmation",
            "failed_or_missing_smoke_test_blocks_switch",
            "active_pointer_must_remain_unchanged_when_build_or_smoke_fails",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])

    def test_retention_cleanup_and_rollback_window_are_fail_closed(self):
        retention = self.contract["old_index_retention_cleanup_and_rollback_window_contract"]
        self.assertEqual(
            retention["retention_policy_field_count"],
            len(retention["future_retention_policy_fields"]),
        )
        self.assertEqual(
            retention["cleanup_eligibility_field_count"],
            len(retention["future_cleanup_eligibility_fields"]),
        )
        self.assertEqual(1, retention["minimum_retained_previous_active_version_count"])
        self.assertTrue(retention["minimum_retention_is_derived_from_predecessor_rollback_target"])
        for field in (
            "additional_retained_version_count_configured",
            "rollback_window_duration_configured",
            "cleanup_timing_configured",
            "business_line_whitebox_approval_recorded",
            "actual_retention_policy_persisted",
            "actual_old_index_cleanup_performed",
            "actual_space_impact_measurement_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(retention[field])
        for field in (
            "unconfigured_policy_values_fail_closed",
            "old_index_cleanup_requires_explicit_retention_quantity",
            "old_index_cleanup_requires_explicit_rollback_window",
            "old_index_cleanup_requires_explicit_cleanup_timing",
            "old_index_cleanup_requires_business_line_whitebox_approval",
            "old_index_cleanup_must_not_occur_before_approved_rollback_window",
            "future_rollback_target_must_be_retained_previous_active_index_version",
            "future_cleanup_is_not_a_substitute_for_rollback",
            "retention_policy_value_may_not_be_inferred_from_control_labels",
        ):
            with self.subTest(field=field):
                self.assertTrue(retention[field])

    def test_failure_and_runtime_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "ADDITIONAL_RETENTION_QUANTITY_UNCONFIGURED",
            "ROLLBACK_WINDOW_UNCONFIGURED",
            "CLEANUP_TIMING_UNCONFIGURED",
            "OLD_INDEX_CLEANUP_BEFORE_APPROVED_ROLLBACK_WINDOW",
            "OLD_INDEX_CLEANUP_WITHOUT_WHITEBOX_APPROVAL",
            "PHASE1_OLD_INDEX_RETENTION_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
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

    def test_stage_boundary_and_scope_keep_next_gate_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage081_review_evidence_declared",
            "stage082_started",
            "stage082_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage083_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "至少保留一个上一活动版本",
            "旧索引不得清理",
            "新索引未通过、缺失或未记录未来冒烟测试不得切换",
            "IDS-STAGE082-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
