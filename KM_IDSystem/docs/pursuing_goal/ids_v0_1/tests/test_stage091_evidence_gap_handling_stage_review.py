import copy
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
    / "STAGE-091_证据缺口处理.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-092_证据风险评分.md"
)
REVIEW_DOCUMENT = BASE / "STAGE091_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_stage_review_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage091_evidence_gap_handling_contract.json"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_control_slice_contract.json"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_controlled_scenarios_contract.json"
)
P4_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_delivery_contract.json"
)
P2_MODULE = BASE / "index_version_schema" / "stage091_evidence_gap_handling_control_slice.py"
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_controlled_scenarios.py"
)
P4_MODULE = BASE / "index_version_schema" / "stage091_evidence_gap_handling_delivery.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-24-stage091-review-local.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage091ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage091_review_test", MODULE)
        cls.report = cls.module.build_evidence_gap_handling_stage091_review_report()

    def test_required_phase_artifacts_exist(self):
        for path in (
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_DOCUMENT,
            CONTRACT,
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
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual("IDS-STAGE091-REVIEW", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE091-REVIEW", self.contract["task_id"])
        self.assertEqual("IDS-STAGE091-REVIEW-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE092-P1-GATE", self.contract["next_gate"])

    def test_contract_keeps_single_authority_runtime_and_stage092_closed(self):
        authority = self.contract["source_authority"]
        for field in (
            "review_can_replace_source_document",
            "review_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "evidence_ledger_access_performed",
            "report_or_audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["reviewed_phase_contract"]
        self.assertEqual("12/7/5", replay["phase1_static_shape"])
        self.assertEqual(468, replay["phase2_control_field_check_count"])
        self.assertEqual(224, replay["phase3_scenario_field_check_count"])
        self.assertEqual("7/7/7/7/7/4/2", replay["phase4_delivery_shape"])
        self.assertEqual(517, replay["phase4_delivery_field_check_count"])
        self.assertEqual(18, replay["phase4_failure_state_count"])
        runtime = self.contract["runtime_boundary"]
        self.assertTrue(
            all(value == 0 for key, value in runtime.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for key, value in runtime.items() if not key.startswith("actual_"))
        )
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage090_review_evidence_declared",
            "stage091_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_completed",
            "stage091_review_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage092_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase_contracts_and_control_reports_pass(self):
        report = self.report
        self.assertTrue(report["review_valid"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])

    def test_controlled_replay_has_exact_frozen_shapes(self):
        self.assertEqual(
            self.module.EXPECTED_CONTROLLED_REPLAY,
            self.report["controlled_replay"],
        )

    def test_authority_rollback_and_runtime_are_closed(self):
        report = self.report
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])
        self.assertTrue(
            report["review_invariants"]["failure_stop_and_rollback_boundaries_preserved"]
        )
        self.assertTrue(report["review_invariants"]["delivery_and_whitebox_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertEqual(
            "PASS_EVIDENCE_GAP_HANDLING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(
            all(report[field] is False for field in self.module.REVIEW_RUNTIME_FALSE_FIELDS)
        )

    def test_next_stage_stays_closed_except_for_gate(self):
        report = self.report
        self.assertTrue(
            report["review_invariants"]["next_stage_taskpack_available_but_not_started"]
        )
        self.assertTrue(report["review_invariants"]["stage092_gate_only_opens_after_review"])
        self.assertTrue(report["stage091_started"])
        self.assertTrue(report["stage091_review_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage092_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_invalid_phase4_report_fails_closed(self):
        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase4_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase2_report_provider=lambda: {"input_accepted": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_phase4_runtime_signal_fails_closed(self):
        baseline = self.module._default_phase4_report()

        def runtime_signal():
            altered = copy.deepcopy(baseline)
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase4_report_provider=runtime_signal
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

    def test_revocation_impact_drift_fails_closed(self):
        baseline = self.module._default_phase4_report()

        def revocation_drift():
            altered = copy.deepcopy(baseline)
            for record in altered["revocation_impact_control_records"]:
                if record["scenario_id"] == "revoked_evidence_report_impact_control":
                    record["report_status_impact_state"] = "CONTROL_REPORT_STATUS_APPLIED"
            return altered

        report = self.module.build_evidence_gap_handling_stage091_review_report(
            phase4_report_provider=revocation_drift
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

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
        stage095_phase1_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P1",
            "IDS-V0_1-STAGE095-P1",
            "IDS-STAGE095-P2-GATE",
        )
        stage095_phase2_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P2",
            "IDS-V0_1-STAGE095-P2",
            "IDS-STAGE095-P3-GATE",
        )
        stage095_phase3_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P3",
            "IDS-V0_1-STAGE095-P3",
            "IDS-STAGE095-P4-GATE",
        )
        stage095_phase4_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P4",
            "IDS-V0_1-STAGE095-P4",
            "IDS-STAGE095-REVIEW-GATE",
        )
        stage091_review_current = (
            "IDS-STAGE091",
            "IDS-STAGE091-REVIEW",
            "IDS-V0_1-STAGE091-REVIEW",
            "IDS-STAGE092-P1-GATE",
        )
        if current == stage091_review_current:
            self.assertTrue(REVIEW_RUN.is_file())
            run = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-091"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE091-REVIEW-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE091-REVIEW-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE091-REVIEW-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE091-REVIEW-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE091-REVIEW-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE092-P1-GATE", run["next_gate"])
            self.assertEqual(
                "PASS_REVIEWED_EVIDENCE_GAP_HANDLING_RUNTIME_DISABLED",
                run["result"],
            )
            self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE091-REVIEW", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage091_review_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE091-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE092-P1-GATE"', roadmap_text)
        else:
            self.assertIn(
                current,
                (
                    stage095_phase1_current,
                    stage095_phase2_current,
                    stage095_phase3_current,
                    stage095_phase4_current,
                    (
                        "IDS-STAGE095",
                        "IDS-STAGE095-REVIEW",
                        "IDS-V0_1-STAGE095-REVIEW",
                        "IDS-STAGE096-P1-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P1",
                        "IDS-V0_1-STAGE096-P1",
                        "IDS-STAGE096-P2-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P2",
                        "IDS-V0_1-STAGE096-P2",
                        "IDS-STAGE096-P3-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P3",
                        "IDS-V0_1-STAGE096-P3",
                        "IDS-STAGE096-P4-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P4",
                        "IDS-V0_1-STAGE096-P4",
                        "IDS-STAGE096-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE091",
                        "IDS-STAGE091-P1",
                        "IDS-V0_1-STAGE091-P1",
                        "IDS-STAGE091-P2-GATE",
                    ),
                    (
                        "IDS-STAGE091",
                        "IDS-STAGE091-P2",
                        "IDS-V0_1-STAGE091-P2",
                        "IDS-STAGE091-P3-GATE",
                    ),
                    (
                        "IDS-STAGE091",
                        "IDS-STAGE091-P3",
                        "IDS-V0_1-STAGE091-P3",
                        "IDS-STAGE091-P4-GATE",
                    ),
                    (
                        "IDS-STAGE091",
                        "IDS-STAGE091-P4",
                        "IDS-V0_1-STAGE091-P4",
                        "IDS-STAGE091-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P1",
                        "IDS-V0_1-STAGE092-P1",
                        "IDS-STAGE092-P2-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P2",
                        "IDS-V0_1-STAGE092-P2",
                        "IDS-STAGE092-P3-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P3",
                        "IDS-V0_1-STAGE092-P3",
                        "IDS-STAGE092-P4-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P4",
                        "IDS-V0_1-STAGE092-P4",
                        "IDS-STAGE092-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-REVIEW",
                        "IDS-V0_1-STAGE092-REVIEW",
                        "IDS-STAGE093-P1-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P1",
                        "IDS-V0_1-STAGE093-P1",
                        "IDS-STAGE093-P2-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P2",
                        "IDS-V0_1-STAGE093-P2",
                        "IDS-STAGE093-P3-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P3",
                        "IDS-V0_1-STAGE093-P3",
                        "IDS-STAGE093-P4-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P4",
                        "IDS-V0_1-STAGE093-P4",
                        "IDS-STAGE093-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-REVIEW",
                        "IDS-V0_1-STAGE093-REVIEW",
                        "IDS-STAGE094-P1-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P1",
                        "IDS-V0_1-STAGE094-P1",
                        "IDS-STAGE094-P2-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P2",
                        "IDS-V0_1-STAGE094-P2",
                        "IDS-STAGE094-P3-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P3",
                        "IDS-V0_1-STAGE094-P3",
                        "IDS-STAGE094-P4-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P4",
                        "IDS-V0_1-STAGE094-P4",
                        "IDS-STAGE094-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-REVIEW",
                        "IDS-V0_1-STAGE094-REVIEW",
                        "IDS-STAGE095-P1-GATE",
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
