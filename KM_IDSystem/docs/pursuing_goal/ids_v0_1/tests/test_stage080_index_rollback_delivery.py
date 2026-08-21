import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE080_PHASE4_INDEX_ROLLBACK_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage080_index_rollback_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage080_index_rollback_delivery.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-080_索引回滚.md"
)
PHASE1_SCOPE = BASE / "STAGE080_PHASE1_INDEX_ROLLBACK_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage080_index_rollback_contract.json"
)
PHASE2_SCOPE = BASE / "STAGE080_PHASE2_INDEX_ROLLBACK_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage080_index_rollback_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage080_index_rollback_control_slice.py"
)
PHASE3_SCOPE = BASE / "STAGE080_PHASE3_INDEX_ROLLBACK_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE / "index_version_schema" / "stage080_index_rollback_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "index_version_schema" / "stage080_index_rollback_scenarios.py"
)
PREDECESSOR_REVIEW = BASE / "STAGE079_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage079_atomic_index_switch_slice_contract.json"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage080IndexRollbackPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module(MODULE, "stage080_p4")
        cls.phase3 = _load_module(PHASE3_MODULE, "stage080_p3_for_p4_test")
        cls.phase2 = _load_module(PHASE2_MODULE, "stage080_p2_for_p4_test")

    def report(self):
        return self.module.build_index_rollback_phase4_delivery_report()

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
            PHASE2_MODULE,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_declares_only_control_delivery_evidence(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage080.index_rollback.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE080-P4", contract["task_id"])
        self.assertEqual(
            "PHASE4_INDEX_ROLLBACK_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE080-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE080-REVIEW-GATE", contract["next_gate"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(contract["source_authority"][field])
        self.assertEqual(
            (6, 28, 168, 5, 5),
            tuple(
                contract["phase3_controlled_scenario_replay_contract"][field]
                for field in (
                    "scenario_count",
                    "scenario_field_count",
                    "scenario_field_check_count",
                    "operations_version_control_view_count",
                    "report_snapshot_version_control_view_count",
                )
            ),
        )
        self.assertEqual(
            (5, 7, 5, 5, 6, 5, 9, 8, 225),
            tuple(
                contract["phase2_control_slice_replay_contract"][field]
                for field in (
                    "control_request_count",
                    "index_version_record_field_count",
                    "building_and_shadow_projection_field_count",
                    "active_pointer_projection_field_count",
                    "smoke_test_input_projection_field_count",
                    "smoke_test_output_projection_field_count",
                    "switch_projection_field_count",
                    "rollback_request_projection_field_count",
                    "phase2_control_field_check_count",
                )
            ),
        )
        self.assertEqual(
            (5, 10, 6, 9, 5, 8, 5, 8, 1, 9, 3, 8, 4),
            tuple(
                contract["delivery_evidence_contract"][field]
                for field in (
                    "index_manifest_control_sample_count",
                    "index_manifest_field_count",
                    "smoke_test_log_control_sample_count",
                    "smoke_test_log_field_count",
                    "switch_record_control_sample_count",
                    "switch_record_field_count",
                    "rollback_proof_control_sample_count",
                    "rollback_proof_field_count",
                    "old_index_retention_projection_count",
                    "old_index_retention_field_count",
                    "operational_instruction_projection_count",
                    "operational_instruction_field_count",
                    "chinese_feedback_count",
                )
            ),
        )
        self.assertEqual(13, contract["failure_and_stop_contract"]["failure_state_count"])
        self.assertFalse(contract["stage_and_phase_boundary"]["whole_stage_review_performed"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_predecessor_replay_preserves_exact_control_shapes(self):
        phase2 = self.phase2.execute_index_rollback_control_slice(
            self.phase2.build_control_input()
        )
        phase3 = self.phase3.build_index_rollback_phase3_report()
        self.assertEqual(
            (True, "COMPLETED_IN_MEMORY_INDEX_ROLLBACK_CONTROL_SLICE", 5, 5),
            (
                phase2["input_accepted"],
                phase2["execution_state"],
                phase2["expected_control_request_count"],
                phase2["received_control_request_count"],
            ),
        )
        self.assertEqual(
            (225, 6, 28, 168, 5, 5),
            (
                phase3["phase2_control_record_field_check_count"],
                phase3["scenario_count"],
                phase3["scenario_field_count"],
                phase3["scenario_field_check_count"],
                phase3["operations_version_control_view_count"],
                phase3["report_snapshot_version_control_view_count"],
            ),
        )
        self.assertTrue(phase3["valid"], phase3)

    def test_delivery_evidence_reuses_p2_p3_without_runtime_writes(self):
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            (self.module.PASS_RESULT, self.module.NEXT_GATE),
            (report["result"], report["next_gate"]),
        )
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertTrue(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertEqual(
            (5, 10, 6, 9, 5, 8, 5, 8, 1, 9, 3, 8),
            tuple(
                report[field]
                for field in (
                    "index_manifest_control_sample_count",
                    "index_manifest_field_count",
                    "smoke_test_log_control_sample_count",
                    "smoke_test_log_field_count",
                    "switch_record_control_sample_count",
                    "switch_record_field_count",
                    "rollback_proof_control_sample_count",
                    "rollback_proof_field_count",
                    "old_index_retention_projection_count",
                    "old_index_retention_field_count",
                    "operational_instruction_projection_count",
                    "operational_instruction_field_count",
                )
            ),
        )
        self.assertTrue(report["all_delivery_references_control_only"])

    def test_manifest_smoke_switch_and_rollback_samples_are_control_only(self):
        report = self.report()
        for item in report["index_manifest_control_samples"]:
            with self.subTest(manifest=item["control_scenario"]):
                self.assertEqual(set(self.module.INDEX_MANIFEST_FIELDS), set(item))
                self.assertEqual(0, item["chunk_count_control_value"])
                self.assertEqual(
                    "CONTROL_INDEX_MANIFEST_NOT_PERSISTED", item["manifest_state"]
                )
                self.assertFalse(item["actual_index_manifest_written"])
                self.assertIn(":control:stage080-p2:", item["index_manifest_ref"])
        for item in report["smoke_test_log_control_samples"]:
            with self.subTest(smoke=item["scenario_id"]):
                self.assertEqual(set(self.module.SMOKE_TEST_LOG_FIELDS), set(item))
                self.assertTrue(item["old_active_continues"])
                self.assertEqual(
                    "CONTROL_SMOKE_TEST_LOG_NOT_PERSISTED", item["log_state"]
                )
                self.assertFalse(item["actual_smoke_test_log_written"])
                self.assertIn(":control:stage080-p2:", item["smoke_test_log_ref"])
        for item in report["switch_record_control_samples"]:
            with self.subTest(switch=item["control_scenario"]):
                self.assertEqual(set(self.module.SWITCH_RECORD_FIELDS), set(item))
                self.assertTrue(item["active_service_continues"])
                self.assertFalse(item["switch_applied"])
        for item in report["rollback_proof_control_samples"]:
            with self.subTest(rollback=item["control_scenario"]):
                self.assertEqual(set(self.module.ROLLBACK_PROOF_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_PREVIOUS_ACTIVE_RETAINED",
                    item["retention_window_state"],
                )
                self.assertEqual(
                    "CONTROL_ROLLBACK_PROOF_NOT_PERSISTED", item["rollback_state"]
                )
                self.assertFalse(item["rollback_applied"])

    def test_retention_space_and_operational_instructions_remain_control_only(self):
        report = self.report()
        retention = report["old_index_retention_projection"]
        self.assertEqual(set(self.module.OLD_INDEX_RETENTION_FIELDS), set(retention))
        self.assertEqual(5, retention["applies_to_control_scenario_count"])
        self.assertTrue(retention["retained_previous_active_required"])
        self.assertEqual(
            "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED",
            retention["space_impact_state"],
        )
        self.assertFalse(retention["actual_space_impact_measurement_performed"])
        self.assertFalse(retention["actual_index_deletion_performed"])
        self.assertTrue(retention["human_handling_required"])
        self.assertEqual(
            ("REBUILD", "PAUSE", "RECOVERY"),
            tuple(item["action"] for item in report["operational_instruction_projections"]),
        )
        for item in report["operational_instruction_projections"]:
            with self.subTest(instruction=item["instruction_id"]):
                self.assertEqual(
                    set(self.module.OPERATIONAL_INSTRUCTION_FIELDS), set(item)
                )
                self.assertFalse(item["actual_operation_performed"])
                self.assertTrue(item["human_handling_required"])
                self.assertIn(":control:stage080-p2:", item["target_ref"])
        self.assertEqual(4, len(report["chinese_feedback"]))

    def test_invalid_predecessor_or_runtime_signal_fails_closed(self):
        invalid = self.module.build_index_rollback_phase4_delivery_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertEqual(0, invalid["index_manifest_control_sample_count"])

        def malformed_phase2():
            result = copy.deepcopy(
                self.phase2.execute_index_rollback_control_slice(
                    self.phase2.build_control_input()
                )
            )
            result["index_version_control_records"][0].pop("index_kind")
            return result

        malformed = self.module.build_index_rollback_phase4_delivery_report(
            phase2_report_provider=malformed_phase2
        )
        self.assertFalse(malformed["valid"])
        self.assertEqual(0, malformed["smoke_test_log_control_sample_count"])

        def phase3_runtime_signal():
            result = copy.deepcopy(self.phase3.build_index_rollback_phase3_report())
            result["retrieval_query_performed"] = True
            return result

        runtime_signal = self.module.build_index_rollback_phase4_delivery_report(
            phase3_report_provider=phase3_runtime_signal
        )
        self.assertFalse(runtime_signal["valid"])

    def test_all_runtime_flags_and_authority_boundaries_stay_closed(self):
        report = self.report()
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertTrue(report["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(report["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(
            report["delivery_control_metadata_can_become_business_fact_authority"]
        )
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
