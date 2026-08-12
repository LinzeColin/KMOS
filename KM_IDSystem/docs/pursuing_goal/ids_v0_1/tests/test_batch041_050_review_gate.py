import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
PURSUE_ROOT = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CHECKER = ROOT / "scripts" / "check_batch041_050_review.py"
CONTRACT = PURSUE_ROOT / "batch_review" / "stage041_050_batch_review_contract.json"
REVIEW = PURSUE_ROOT / "BATCH041_050_REVIEW_GATE.md"
BATCH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Batch041050ReviewGateTests(unittest.TestCase):
    def _load_checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing batch checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "batch041_050_review_checker", CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_batch_review_artifacts_exist(self):
        self.assertTrue(REVIEW.is_file(), f"missing review evidence: {REVIEW}")
        self.assertTrue(CONTRACT.is_file(), f"missing review contract: {CONTRACT}")
        self.assertTrue(CHECKER.is_file(), f"missing review checker: {CHECKER}")

    def test_contract_binds_exact_ten_stage_review_matrix(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            "ids.v0_1.batch041_050.review_contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-BATCH-041-050", contract["batch_id"])
        self.assertEqual(
            "IDS-V0_1-BATCH-041-050-REVIEW-GATE", contract["task_id"]
        )
        stages = contract["stage_reviews"]
        self.assertEqual(
            [f"STAGE-{stage:03d}" for stage in range(41, 51)],
            [stage["stage_id"] for stage in stages],
        )
        self.assertEqual(
            [f"ACC-STAGE-{stage:03d}" for stage in range(41, 51)],
            [stage["acceptance_id"] for stage in stages],
        )
        for stage in stages:
            with self.subTest(stage=stage["stage_id"]):
                self.assertTrue(stage["taskpack_ref"].startswith("KM_IDSystem/"))
                self.assertTrue(stage["review_artifact_ref"].endswith("_STAGE_REVIEW.md"))
                self.assertTrue(stage["checker_ref"].endswith(".py"))
                self.assertTrue(stage["test_ref"].endswith(".py"))
                self.assertTrue(stage["machine_run_ref"].endswith(".json"))

    def test_checker_confirms_batch_review_and_global_upload_lock(self):
        report = self._load_checker().build_batch041_050_review_report()
        self.assertTrue(report["review_valid"], report)
        self.assertTrue(all(report["contract_shape_checks"].values()), report)
        self.assertTrue(all(report["artifact_checks"].values()), report)
        self.assertTrue(all(report["stage_checks"].values()), report)
        self.assertTrue(all(report["cross_stage_checks"].values()), report)
        self.assertTrue(all(report["governance_checks"].values()), report)
        self.assertTrue(all(report["projection_checks"].values()), report)
        self.assertTrue(all(report["truth_checks"].values()), report)
        self.assertEqual(10, report["reviewed_stage_count"])
        self.assertEqual(
            "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED", report["result"]
        )
        self.assertEqual("IDS-STAGE051-P1-GATE", report["next_gate"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_unknown_contract_field_or_failed_stage_fails_closed(self):
        checker = self._load_checker()
        contract = checker.load_contract()
        tampered = copy.deepcopy(contract)
        tampered["runtime_execution_allowed"] = True
        blocked = checker.build_batch041_050_review_report(contract=tampered)
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual(
            "IDS-V0_1-BATCH-041-050-REVIEW-GATE", blocked["next_gate"]
        )
        self.assertFalse(blocked["github_upload_allowed"])

        stage_results = {f"STAGE-{stage:03d}": True for stage in range(41, 51)}
        stage_results["STAGE-046"] = False
        blocked_stage = checker.build_batch041_050_review_report(
            stage_result_overrides=stage_results
        )
        self.assertFalse(blocked_stage["review_valid"], blocked_stage)
        self.assertFalse(blocked_stage["stage_checks"]["STAGE-046"])
        self.assertFalse(blocked_stage["push_allowed"])

    def test_document_and_governance_route_to_stage051_without_upload(self):
        text = REVIEW.read_text(encoding="utf-8")
        for term in (
            "IDS-V0_1-BATCH-041-050-REVIEW-GATE",
            "STAGE-041..STAGE-050",
            "ACC-STAGE-041..ACC-STAGE-050",
            "BATCH041-050-REVIEW-F1",
            "IDS-STAGE051-P1-GATE",
            "push_allowed=false",
            "NO_STAGE051_THIS_RUN",
            "/Users/linzezhang/Downloads/IDS_MetaData",
            "ACC-STAGE-168",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn(
            'status: "batch041_050_reviewed_local_global_upload_locked"', batch
        )
        self.assertIn('push_allowed: false', batch)
        self.assertIn('github_upload_allowed: false', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE051-P1"', batch)
        self.assertTrue(
            (
                'current_phase_id: "IDS-V0_1-BATCH-041-050-REVIEW-GATE"'
                in roadmap
                and 'next_gate_id: "IDS-STAGE051-P1-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE051-REVIEW"' in roadmap
                and 'next_gate_id: "IDS-STAGE052-P1-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE052-P1"' in roadmap
                and 'next_gate_id: "IDS-STAGE052-P2-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE052-P2"' in roadmap
                and 'next_gate_id: "IDS-STAGE052-P3-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE052-P3"' in roadmap
                and 'next_gate_id: "IDS-STAGE052-P4-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE052-P4"' in roadmap
                and 'next_gate_id: "IDS-STAGE052-REVIEW-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE052-REVIEW"' in roadmap
                and 'next_gate_id: "IDS-STAGE053-P1-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE053-P1"' in roadmap
                and 'next_gate_id: "IDS-STAGE053-P2-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE053-P2"' in roadmap
                and 'next_gate_id: "IDS-STAGE053-P3-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE053-P3"' in roadmap
                and 'next_gate_id: "IDS-STAGE053-P4-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE053-P4"' in roadmap
                and 'next_gate_id: "IDS-STAGE053-REVIEW-GATE"' in roadmap
            )
            or (
                'current_phase_id: "IDS-STAGE053-REVIEW"' in roadmap
                and 'next_gate_id: "IDS-STAGE054-P1-GATE"' in roadmap
            )
        )

    def test_cli_emits_local_review_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        self.assertEqual("", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["review_valid"], report)
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        self.assertFalse(report["app_reinstall_allowed"])


if __name__ == "__main__":
    unittest.main()
