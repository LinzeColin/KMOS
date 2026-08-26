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
CHECKER = ROOT / "scripts" / "check_batch051_060_review.py"
CONTRACT = PURSUE_ROOT / "batch_review" / "stage051_060_batch_review_contract.json"
REVIEW = PURSUE_ROOT / "BATCH051_060_REVIEW_GATE.md"
HUMAN_ACCEPTANCE = ROOT / "文档" / "05_执行与验收.md"


class Batch051060ReviewGateTests(unittest.TestCase):
    def _load_checker(self):
        spec = importlib.util.spec_from_file_location("batch051_060_review_checker", CHECKER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_required_review_artifacts_exist(self):
        self.assertTrue(REVIEW.is_file())
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(CHECKER.is_file())

    def test_contract_binds_exact_ten_stage_review_matrix(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual("ids.v0_1.batch051_060.review_contract.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-BATCH-051-060-REVIEW-GATE", contract["task_id"])
        self.assertEqual(
            [f"STAGE-{number:03d}" for number in range(51, 61)],
            [stage["stage_id"] for stage in contract["stage_reviews"]],
        )
        self.assertEqual([], contract["findings"])

    def test_checker_confirms_local_review_and_global_upload_lock(self):
        report = self._load_checker().build_batch051_060_review_report()
        self.assertTrue(report["review_valid"], report)
        for key in (
            "contract_shape_checks",
            "artifact_checks",
            "stage_checks",
            "governance_checks",
            "projection_checks",
            "truth_checks",
        ):
            self.assertTrue(all(report[key].values()), report)
        self.assertEqual("PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED", report["result"])
        self.assertEqual("IDS-STAGE061-P1-GATE", report["next_gate"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_unknown_contract_field_or_failed_stage_fails_closed(self):
        checker = self._load_checker()
        tampered = copy.deepcopy(checker.load_contract())
        tampered["runtime_execution_allowed"] = True
        failed = checker.build_batch051_060_review_report(contract=tampered)
        self.assertFalse(failed["review_valid"], failed)
        self.assertEqual("FAIL_CLOSED", failed["result"])
        forced = checker.build_batch051_060_review_report(
            stage_result_overrides={"STAGE-058": False}
        )
        self.assertFalse(forced["review_valid"], forced)
        self.assertFalse(forced["stage_checks"]["STAGE-058"])

    def test_document_declares_stage061_as_separate_run(self):
        text = REVIEW.read_text(encoding="utf-8")
        for term in (
            "IDS-V0_1-BATCH-051-060-REVIEW-GATE",
            "STAGE-051..STAGE-060",
            "ACC-STAGE-051..ACC-STAGE-060",
            "IDS-STAGE061-P1-GATE",
            "NO_STAGE061_THIS_RUN",
            "push_allowed=false",
            "/Users/linzezhang/Downloads/IDS_MetaData",
            "ACC-STAGE-168",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_human_projection_shows_review_or_legal_successor_acceptance_and_run(self):
        text = HUMAN_ACCEPTANCE.read_text(encoding="utf-8")
        predecessor_visible = (
            "ACC-BATCH051-060-REVIEW-01" in text
            and "RUN-IDS-V0_1-BATCH-051-060-REVIEW-20260814-001" in text
        )
        successor_visible = (
            "ACC-STAGE061-P1-01" in text
            and "RUN-IDS-STAGE061-P1-LOCAL-20260814-001" in text
        )
        phase2_visible = (
            "ACC-STAGE061-P2-01" in text
            and "RUN-IDS-STAGE061-P2-LOCAL-20260814-001" in text
        )
        phase3_visible = (
            "ACC-STAGE061-P3-01" in text
            and "RUN-IDS-STAGE061-P3-LOCAL-20260814-001" in text
        )
        phase4_visible = (
            "ACC-STAGE061-P4-01" in text
            and "RUN-IDS-STAGE061-P4-LOCAL-20260814-001" in text
        )
        stage062_phase1_visible = (
            "ACC-STAGE062-P1-01" in text
            and "RUN-IDS-STAGE062-P1-LOCAL-20260814-001" in text
        )
        stage062_phase2_visible = (
            "ACC-STAGE062-P2-01" in text
            and "RUN-IDS-STAGE062-P2-LOCAL-20260814-001" in text
        )
        stage062_phase3_visible = (
            "ACC-STAGE062-P3-01" in text
            and "RUN-IDS-STAGE062-P3-LOCAL-20260814-001" in text
        )
        stage062_review_visible = (
            "ACC-STAGE062-REVIEW-01" in text
            and "RUN-IDS-STAGE062-REVIEW-LOCAL-20260814-001" in text
        )
        stage063_phase1_visible = (
            "ACC-STAGE063-P1-01" in text
            and "RUN-IDS-STAGE063-P1-LOCAL-20260814-001" in text
        )
        stage064_phase1_visible = (
            "ACC-STAGE064-P1-01" in text
            and "RUN-IDS-STAGE064-P1-LOCAL-20260814-001" in text
        )
        stage064_phase2_visible = (
            "ACC-STAGE064-P2-01" in text
            and "RUN-IDS-STAGE064-P2-LOCAL-20260814-001" in text
        )
        stage065_phase1_visible = (
            "ACC-STAGE065-P1-01" in text
            and "RUN-IDS-STAGE065-P1-LOCAL-20260814-001" in text
        )
        stage095_phase2_visible = (
            "ACC-STAGE095-P2-01" in text
            and "RUN-IDS-STAGE095-P2-LOCAL-20260824-001" in text
        )
        stage095_phase3_visible = (
            "ACC-STAGE095-P3-01" in text
            and "RUN-IDS-STAGE095-P3-LOCAL-20260824-001" in text
        )
        stage095_phase4_visible = (
            "ACC-STAGE095-P4-01" in text
            and "RUN-IDS-STAGE095-P4-LOCAL-20260824-001" in text
        )
        stage095_review_visible = (
            "ACC-STAGE095-REVIEW-01" in text
            and "RUN-IDS-V0_1-STAGE095-REVIEW-20260824-001" in text
        )
        stage107_review_visible = (
            "ACC-STAGE107-REVIEW-01" in text
            and "RUN-IDS-V0_1-STAGE107-REVIEW-20260826-001" in text
        )
        stage108_phase1_visible = (
            "ACC-STAGE108-P1-01" in text
            and "IDS-V0_1-STAGE108-P1-20260826-001" in text
        )
        stage108_phase2_visible = (
            "ACC-STAGE108-P2-01" in text
            and "EVT-IDS-V0_1-STAGE108-P2-20260826-001" in text
        )
        stage108_phase3_visible = (
            "ACC-STAGE108-P3-01" in text
            and "EVT-IDS-V0_1-STAGE108-P3-20260826-001" in text
        )
        stage108_phase4_visible = (
            "ACC-STAGE108-P4-01" in text
            and "EVT-IDS-V0_1-STAGE108-P4-20260826-001" in text
        )
        stage108_review_visible = (
            "ACC-STAGE108-REVIEW-01" in text
            and "EVT-IDS-V0_1-STAGE108-REVIEW-20260826-001" in text
        )
        stage109_phase1_visible = (
            "ACC-STAGE109-P1-01" in text
            and "RUN-IDS-V0_1-STAGE109-P1-20260826-001" in text
        )
        stage109_phase2_visible = (
            "ACC-STAGE109-P2-01" in text
            and "RUN-IDS-V0_1-STAGE109-P2-20260826-001" in text
        )
        stage109_phase3_visible = (
            "ACC-STAGE109-P3-01" in text
            and "RUN-IDS-V0_1-STAGE109-P3-20260826-001" in text
        )
        stage109_phase4_visible = (
            "ACC-STAGE109-P4-01" in text
            and "RUN-IDS-V0_1-STAGE109-P4-20260826-001" in text
        )
        self.assertTrue(
            predecessor_visible
            or successor_visible
            or phase2_visible
            or phase3_visible
            or phase4_visible
            or stage062_phase1_visible
            or stage062_phase2_visible
            or stage062_phase3_visible
            or stage062_review_visible
            or stage063_phase1_visible
            or stage064_phase1_visible
            or stage064_phase2_visible
            or stage065_phase1_visible
            or stage095_phase2_visible
            or stage095_phase3_visible
            or stage095_phase4_visible
            or stage095_review_visible
            or stage107_review_visible
            or stage108_phase1_visible
            or stage108_phase2_visible
            or stage108_phase3_visible
            or stage108_phase4_visible
            or stage108_review_visible
            or stage109_phase1_visible
            or stage109_phase2_visible
            or stage109_phase3_visible
            or stage109_phase4_visible,
            text,
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
        report = json.loads(completed.stdout)
        self.assertTrue(report["review_valid"], report)
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])


if __name__ == "__main__":
    unittest.main()
