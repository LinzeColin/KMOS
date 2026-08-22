import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE076_PHASE4_INDEX_VERSION_SCHEMA_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage076_index_version_schema_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_delivery.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-076_索引版本Schema.md"
)
P3_SCOPE = BASE / "STAGE076_PHASE3_INDEX_VERSION_SCHEMA_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage076_index_version_schema_scenarios_contract.json"
)
P3_MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_scenarios.py"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage076_index_version_schema_slice_contract.json"
)
P2_MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_slice.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage076-p4-local.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage076_p4", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage076 P4 delivery module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_predecessor(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage076IndexVersionSchemaPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()
        cls.phase3 = _load_predecessor(P3_MODULE, "stage076_p3_for_p4_test")
        cls.phase2 = _load_predecessor(P2_MODULE, "stage076_p2_for_p4_test")

    def report(self):
        return self.module.build_index_version_schema_phase4_delivery_report()

    def test_control_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P2_CONTRACT,
            P2_MODULE,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_declares_only_control_delivery_evidence(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage076.index_version_schema.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE076-P4", contract["task_id"])
        self.assertEqual(
            "PHASE4_INDEX_VERSION_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE076-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", contract["next_gate"])
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
            (6, 26, 156, 5, 5),
            (
                contract["phase3_controlled_scenario_replay_contract"]["scenario_count"],
                contract["phase3_controlled_scenario_replay_contract"]["scenario_field_count"],
                contract["phase3_controlled_scenario_replay_contract"]["scenario_field_check_count"],
                contract["phase3_controlled_scenario_replay_contract"]["operations_version_control_view_count"],
                contract["phase3_controlled_scenario_replay_contract"]["report_snapshot_version_control_view_count"],
            ),
        )
        self.assertEqual(
            (5, 10, 6, 9, 5, 8, 5, 8, 1, 9, 3, 8, 4),
            (
                contract["delivery_evidence_contract"]["index_manifest_control_sample_count"],
                contract["delivery_evidence_contract"]["index_manifest_field_count"],
                contract["delivery_evidence_contract"]["smoke_test_log_control_sample_count"],
                contract["delivery_evidence_contract"]["smoke_test_log_field_count"],
                contract["delivery_evidence_contract"]["switch_record_control_sample_count"],
                contract["delivery_evidence_contract"]["switch_record_field_count"],
                contract["delivery_evidence_contract"]["rollback_proof_control_sample_count"],
                contract["delivery_evidence_contract"]["rollback_proof_field_count"],
                contract["delivery_evidence_contract"]["old_index_retention_projection_count"],
                contract["delivery_evidence_contract"]["old_index_retention_field_count"],
                contract["delivery_evidence_contract"]["operational_instruction_projection_count"],
                contract["delivery_evidence_contract"]["operational_instruction_field_count"],
                contract["delivery_evidence_contract"]["chinese_feedback_count"],
            ),
        )
        self.assertEqual(13, contract["failure_and_stop_contract"]["failure_state_count"])
        self.assertFalse(contract["stage_and_phase_boundary"]["whole_stage_review_performed"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

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
            (
                report["index_manifest_control_sample_count"],
                report["index_manifest_field_count"],
                report["smoke_test_log_control_sample_count"],
                report["smoke_test_log_field_count"],
                report["switch_record_control_sample_count"],
                report["switch_record_field_count"],
                report["rollback_proof_control_sample_count"],
                report["rollback_proof_field_count"],
                report["old_index_retention_projection_count"],
                report["old_index_retention_field_count"],
                report["operational_instruction_projection_count"],
                report["operational_instruction_field_count"],
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
                self.assertIn(":control:stage076-p2:", item["index_manifest_ref"])
        for item in report["smoke_test_log_control_samples"]:
            with self.subTest(smoke=item["scenario_id"]):
                self.assertEqual(set(self.module.SMOKE_TEST_LOG_FIELDS), set(item))
                self.assertTrue(item["old_active_continues"])
                self.assertEqual(
                    "CONTROL_SMOKE_TEST_LOG_NOT_PERSISTED", item["log_state"]
                )
                self.assertFalse(item["actual_smoke_test_log_written"])
                self.assertIn(":control:stage076-p2:", item["smoke_test_log_ref"])
        for item in report["switch_record_control_samples"]:
            with self.subTest(switch=item["control_scenario"]):
                self.assertEqual(set(self.module.SWITCH_RECORD_FIELDS), set(item))
                self.assertTrue(item["active_service_continues"])
                self.assertFalse(item["switch_applied"])
        for item in report["rollback_proof_control_samples"]:
            with self.subTest(rollback=item["control_scenario"]):
                self.assertEqual(set(self.module.ROLLBACK_PROOF_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_PREVIOUS_ACTIVE_RETAINED", item["retention_window_state"]
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
                self.assertIn(":control:stage076-p2:", item["target_ref"])
        self.assertEqual(4, len(report["chinese_feedback"]))

    def test_invalid_predecessor_or_runtime_signal_fails_closed(self):
        invalid = self.module.build_index_version_schema_phase4_delivery_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertEqual(0, invalid["index_manifest_control_sample_count"])

        def malformed_phase2():
            result = copy.deepcopy(
                self.phase2.execute_index_version_schema_control_slice(
                    self.phase2.build_control_input()
                )
            )
            result["index_version_control_records"][0].pop("index_kind")
            return result

        malformed = self.module.build_index_version_schema_phase4_delivery_report(
            phase2_report_provider=malformed_phase2
        )
        self.assertFalse(malformed["valid"])
        self.assertEqual(0, malformed["smoke_test_log_control_sample_count"])

        def phase3_runtime_signal():
            result = copy.deepcopy(self.phase3.build_index_version_schema_phase3_report())
            result["actual_retrieval_query_performed"] = True
            return result

        runtime_signal = self.module.build_index_version_schema_phase4_delivery_report(
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
        self.assertFalse(report["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_current_machine_and_governance_projection_preserves_phase4_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap = ROADMAP.read_text(encoding="utf-8")
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-P4",
                    "IDS-V0_1-STAGE076-P4",
                    "IDS-STAGE076-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-STAGE077-P1-GATE",
                ),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P1", "IDS-V0_1-STAGE077-P1", "IDS-STAGE077-P2-GATE"),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P2", "IDS-V0_1-STAGE077-P2", "IDS-STAGE077-P3-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P3", "IDS-V0_1-STAGE077-P3", "IDS-STAGE077-P4-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P4", "IDS-V0_1-STAGE077-P4", "IDS-STAGE077-REVIEW-GATE"), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),

                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-V0_1-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P2", "IDS-V0_1-STAGE084-P2", "IDS-STAGE084-P3-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-V0_1-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-V0_1-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-V0_1-STAGE084-REVIEW', 'IDS-STAGE085-P3-GATE'),

                ('IDS-STAGE085', 'IDS-STAGE085-P2', 'IDS-V0_1-STAGE085-P2', 'IDS-STAGE085-P3-GATE'),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            ("IDS-V0_1-STAGE076-P4", "IDS-V0_1-STAGE076-REVIEW",
                'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW", "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                    'IDS-V0_1-STAGE084-REVIEW',

                'IDS-V0_1-STAGE085-P2',
            ),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE076-P1-01",
                "ACC-STAGE076-P2-01",
                "ACC-STAGE076-P3-01",
                "ACC-STAGE076-P4-01",
                "ACC-STAGE076-P4-02",
                "ACC-STAGE076-P4-03",
                "ACC-STAGE076-P4-04",
            }.issubset(acceptance_ids)
        )
        self.assertIn("EVT-IDS-V0_1-STAGE076-P4-20260821-001", event_ids)
        self.assertEqual(self.module.PASS_RESULT, run["result"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", run["next_gate"])
        self.assertEqual(0, run["runtime_counters"]["model_tokens"])
        self.assertFalse(run["actions"]["ovh_deployment_performed"])
        self.assertFalse(run["actions"]["push_performed"])
        self.assertIn('current_stage_id: "IDS-STAGE076"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE076-P4"', roadmap)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE076-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE076-REVIEW-GATE"', roadmap)


if __name__ == "__main__":
    unittest.main()
