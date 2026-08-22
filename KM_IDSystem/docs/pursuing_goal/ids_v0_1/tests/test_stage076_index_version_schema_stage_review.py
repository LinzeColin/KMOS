import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-076_索引版本Schema.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-077_后台索引构建.md"
)
REVIEW_DOCUMENT = BASE / "STAGE076_STAGE_REVIEW.md"
MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_stage_review.py"
P1_CONTRACT = BASE / "index_version_schema" / "stage076_index_version_schema_contract.json"
P2_CONTRACT = BASE / "index_version_schema" / "stage076_index_version_schema_slice_contract.json"
P3_CONTRACT = BASE / "index_version_schema" / "stage076_index_version_schema_scenarios_contract.json"
P4_CONTRACT = BASE / "index_version_schema" / "stage076_index_version_schema_delivery_contract.json"
P2_MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_slice.py"
P3_MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_scenarios.py"
P4_MODULE = BASE / "index_version_schema" / "stage076_index_version_schema_delivery.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-21-stage076-review-local.json"
P4_RUN = ROOT / "machine" / "runs" / "2026-08-21-stage076-p4-local.json"


class Stage076ReviewTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("stage076_review_test", MODULE)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_required_phase_artifacts_exist(self):
        for path in (
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_DOCUMENT,
            MODULE,
            P1_CONTRACT,
            P2_CONTRACT,
            P3_CONTRACT,
            P4_CONTRACT,
            P2_MODULE,
            P3_MODULE,
            P4_MODULE,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
        ):
            self.assertTrue(path.is_file(), path)

    def test_phase_contracts_and_control_reports_pass(self):
        report = self._module().build_index_version_schema_stage076_review_report()
        self.assertTrue(report["review_valid"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])
        self.assertEqual("PASS_REVIEWED_INDEX_VERSION_SCHEMA_RUNTIME_DISABLED", report["result"])
        self.assertEqual("IDS-STAGE077-P1-GATE", report["next_gate"])

    def test_controlled_replay_has_exact_frozen_shapes(self):
        report = self._module().build_index_version_schema_stage076_review_report()
        self.assertEqual(
            {
                "phase1_supported_index_kind_count": 3,
                "phase1_index_version_field_count": 8,
                "phase1_active_pointer_field_count": 5,
                "phase1_building_version_field_count": 5,
                "phase1_verification_condition_count": 6,
                "phase1_lifecycle_state_count": 7,
                "phase1_failure_state_count": 8,
                "phase2_control_request_count": 5,
                "phase2_index_version_record_count": 5,
                "phase2_building_version_record_count": 5,
                "phase2_active_pointer_projection_count": 5,
                "phase2_verification_projection_count": 5,
                "phase2_switch_projection_count": 5,
                "phase2_rollback_projection_count": 5,
                "phase2_control_field_check_count": 225,
                "phase3_scenario_count": 6,
                "phase3_scenario_field_count": 26,
                "phase3_scenario_field_check_count": 156,
                "phase3_operations_view_count": 5,
                "phase3_report_snapshot_view_count": 5,
                "phase3_human_handling_required_count": 6,
                "phase4_index_manifest_sample_count": 5,
                "phase4_smoke_log_sample_count": 6,
                "phase4_switch_record_sample_count": 5,
                "phase4_rollback_proof_sample_count": 5,
                "phase4_old_index_retention_count": 1,
                "phase4_operational_instruction_count": 3,
                "phase4_chinese_feedback_count": 4,
                "phase4_failure_state_count": 13,
            },
            report["controlled_replay"],
        )

    def test_authority_rollback_and_runtime_are_closed(self):
        report = self._module().build_index_version_schema_stage076_review_report()
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])
        self.assertTrue(report["review_invariants"]["failure_stop_and_rollback_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["delivery_and_whitebox_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertEqual("PASS_INDEX_VERSION_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED", report["rollback"]["return_to"])
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(all(report[field] is False for field in self._module().REVIEW_RUNTIME_FALSE_FIELDS))

    def test_next_stage_stays_closed_except_for_gate(self):
        report = self._module().build_index_version_schema_stage076_review_report()
        self.assertTrue(report["review_invariants"]["next_stage_taskpack_available_but_not_started"])
        self.assertTrue(report["review_invariants"]["stage077_gate_only_opens_after_review"])
        self.assertFalse(report["stage077_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_index_version_schema_stage076_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_index_version_schema_stage076_review_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_index_version_schema_stage076_review_report(
            phase2_report_provider=lambda: {"input_accepted": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_index_version_schema_stage076_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual("IDS-STAGE076-REVIEW-GATE", report["next_gate"])

    def test_governance_projection_records_stage_review_when_current(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        if current == (
            "IDS-STAGE076",
            "IDS-V0_1-STAGE076-REVIEW",
            "IDS-V0_1-STAGE076-REVIEW",
            "IDS-STAGE077-P1-GATE",
        ):
            self.assertTrue(REVIEW_RUN.is_file())
            run = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-076"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE076-REVIEW-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE076-REVIEW-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE076-REVIEW-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE076-REVIEW-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE076-REVIEW-20260821-001", event_ids)
            self.assertEqual("IDS-STAGE077-P1-GATE", run["next_gate"])
            self.assertEqual("PASS_REVIEWED_INDEX_VERSION_SCHEMA_RUNTIME_DISABLED", run["result"])
            self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))
            self.assertIn('current_phase_id: "IDS-STAGE076-REVIEW"', ROADMAP.read_text(encoding="utf-8"))
            self.assertIn('next_gate_id: "IDS-STAGE077-P1-GATE"', ROADMAP.read_text(encoding="utf-8"))
        else:
            self.assertIn(
                current,
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
                    ), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),

                    ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                        ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                    ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                    ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                    ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE")),
            )
            self.assertTrue(P4_RUN.is_file())
            self.assertIn(
                (plan["stage"], plan["phase"], plan["task"]),
                (
                    ("IDS-STAGE076", "IDS-V0_1-STAGE076-P4", "IDS-V0_1-STAGE076-P4"),
                    ("IDS-STAGE076", "IDS-V0_1-STAGE076-REVIEW", "IDS-V0_1-STAGE076-REVIEW"),
                    ("IDS-STAGE077", "IDS-V0_1-STAGE077-P1", "IDS-V0_1-STAGE077-P1"),
                    ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'),
                 ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                    ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4"),
                        ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW'),

                    ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1'),
                    ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW'), ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1'), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1"),
                    ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1")),
            )


if __name__ == "__main__":
    unittest.main()
