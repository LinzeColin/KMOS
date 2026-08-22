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
    / "STAGE-080_索引回滚.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-081_影子索引合同.md"
)
REVIEW_DOCUMENT = BASE / "STAGE080_STAGE_REVIEW.md"
MODULE = BASE / "index_version_schema" / "stage080_index_rollback_stage_review.py"
P1_CONTRACT = BASE / "index_version_schema" / "stage080_index_rollback_contract.json"
P2_CONTRACT = BASE / "index_version_schema" / "stage080_index_rollback_slice_contract.json"
P3_CONTRACT = BASE / "index_version_schema" / "stage080_index_rollback_scenarios_contract.json"
P4_CONTRACT = BASE / "index_version_schema" / "stage080_index_rollback_delivery_contract.json"
P2_MODULE = BASE / "index_version_schema" / "stage080_index_rollback_control_slice.py"
P3_MODULE = BASE / "index_version_schema" / "stage080_index_rollback_scenarios.py"
P4_MODULE = BASE / "index_version_schema" / "stage080_index_rollback_delivery.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-22-stage080-review-local.json"


class Stage080ReviewTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("stage080_review_test", MODULE)
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
        report = self._module().build_index_rollback_stage080_review_report()
        self.assertTrue(report["review_valid"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])
        self.assertEqual("PASS_REVIEWED_INDEX_ROLLBACK_RUNTIME_DISABLED", report["result"])
        self.assertEqual("IDS-STAGE081-P1-GATE", report["next_gate"])

    def test_controlled_replay_has_exact_frozen_shapes(self):
        report = self._module().build_index_rollback_stage080_review_report()
        self.assertEqual(self._module().EXPECTED_CONTROLLED_REPLAY, report["controlled_replay"])

    def test_authority_rollback_and_runtime_are_closed(self):
        module = self._module()
        report = module.build_index_rollback_stage080_review_report()
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])
        self.assertTrue(report["review_invariants"]["failure_stop_and_rollback_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["delivery_and_whitebox_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertEqual("PASS_INDEX_ROLLBACK_DELIVERY_EVIDENCE_RUNTIME_DISABLED", report["rollback"]["return_to"])
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(all(report[field] is False for field in module.REVIEW_RUNTIME_FALSE_FIELDS))

    def test_next_stage_stays_closed_except_for_gate(self):
        report = self._module().build_index_rollback_stage080_review_report()
        self.assertTrue(report["review_invariants"]["next_stage_taskpack_available_but_not_started"])
        self.assertTrue(report["review_invariants"]["stage081_gate_only_opens_after_review"])
        self.assertFalse(report["stage081_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_index_rollback_stage080_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE080-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_index_rollback_stage080_review_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE080-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_index_rollback_stage080_review_report(
            phase2_report_provider=lambda: {"input_accepted": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE080-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_index_rollback_stage080_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual("IDS-STAGE080-REVIEW-GATE", report["next_gate"])

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
            "IDS-STAGE080",
            "IDS-STAGE080-REVIEW",
            "IDS-V0_1-STAGE080-REVIEW",
            "IDS-STAGE081-P1-GATE",
        ):
            self.assertTrue(REVIEW_RUN.is_file())
            run = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-080"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE080-REVIEW-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE080-REVIEW-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE080-REVIEW-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE080-REVIEW-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE080-REVIEW-20260822-001", event_ids)
            self.assertEqual("IDS-STAGE081-P1-GATE", run["next_gate"])
            self.assertEqual("PASS_REVIEWED_INDEX_ROLLBACK_RUNTIME_DISABLED", run["result"])
            self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE080-REVIEW", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn('current_phase_id: "IDS-STAGE080-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE081-P1-GATE"', roadmap_text)
        else:
            self.assertIn(
                current,
                (
                    (
                        "IDS-STAGE080",
                        "IDS-V0_1-STAGE080-P4",
                        "IDS-V0_1-STAGE080-P4",
                        "IDS-STAGE080-REVIEW-GATE",
                    ),
                 ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                    ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE")),
            )


if __name__ == "__main__":
    unittest.main()
