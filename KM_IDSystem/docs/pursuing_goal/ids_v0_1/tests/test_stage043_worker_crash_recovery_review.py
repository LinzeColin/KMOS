import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CHECKER = PROJECT_ROOT / "scripts" / "check_worker_crash_recovery.py"
RUNTIME_CHECKER = PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_runtime.py"
REVIEW_CHECKER = PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_stage_review.py"
REVIEW_ARTIFACT = BASE / "STAGE043_STAGE_REVIEW.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = PROJECT_ROOT / "docs" / "HANDOFF.md"

PHASE4_COMMIT = "641009f26df2119cf21bf33640789f4928d94037"
PHASE4_KMIDS_TREE = "da8e19520b72cea9db76656c12ae7ba0a1787287"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE043-REVIEW-20260719-001"


def _load(path: Path, name: str):
    if not path.is_file():
        raise AssertionError(f"missing checker: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load checker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage043WorkerCrashRecoveryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phase1 = _load(PHASE1_CHECKER, "stage043_review_phase1_tests")
        cls.runtime = _load(RUNTIME_CHECKER, "stage043_review_runtime_tests")

    def _review(self):
        return _load(REVIEW_CHECKER, "stage043_review_checker_tests")

    def test_review_artifacts_and_identity_exist(self):
        self.assertTrue(REVIEW_ARTIFACT.is_file())
        self.assertTrue(REVIEW_CHECKER.is_file())
        report = self._review().build_stage043_review_report()
        self.assertEqual("ids.stage043.worker_crash_recovery.stage_review.v1", report["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE043-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-043", report["acceptance_id"])
        self.assertEqual("PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED", report["result"])

    def test_recovery_identity_binds_worker_and_digest_refs(self):
        valid = self.runtime.build_recovery_request("CHECKPOINT_RESUME")
        self.assertEqual(
            "CHECKPOINT_RESUME_CANDIDATE",
            self.runtime.evaluate_recovery(valid)["decision_action"],
        )

        mismatched_owner = self.runtime.build_recovery_request(
            "CHECKPOINT_RESUME",
            lease_owner_ref="control:stage043:another-worker",
        )
        forged_checkpoint = self.runtime.build_recovery_request(
            "CHECKPOINT_RESUME",
            checkpoint_ref="checkpoint:sha256:" + "0" * 64,
        )
        forged_quarantine = self.runtime.build_recovery_request(
            "CHECKPOINT_RESUME",
            quarantine_ref="quarantine:sha256:" + "f" * 64,
        )
        for request in (mismatched_owner, forged_checkpoint, forged_quarantine):
            with self.subTest(request=request):
                result = self.runtime.evaluate_recovery(request)
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
                self.assertEqual([], result["transition_candidates"])

    def test_crash_detection_requires_thresholds_at_detection_time(self):
        valid = self.runtime.build_recovery_request("CHECKPOINT_RESUME")
        self.assertEqual(
            "CHECKPOINT_RESUME_CANDIDATE",
            self.runtime.evaluate_recovery(valid)["decision_action"],
        )
        detected_before_grace = self.runtime.build_recovery_request(
            "CHECKPOINT_RESUME",
            crash_detected_at_epoch_seconds=999,
        )
        result = self.runtime.evaluate_recovery(detected_before_grace)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN", result["reason_code"])

    def test_resource_gate_and_pressure_signal_are_consistent(self):
        contradictory = self.runtime.build_recovery_request(
            "CHECKPOINT_RESUME",
            resource_gates_passed=True,
            resource_pressure_signal="DISK_SPACE_INSUFFICIENT",
        )
        result = self.runtime.evaluate_recovery(contradictory)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual([], result["transition_candidates"])

        pause = self.runtime.build_recovery_request(
            "RESOURCE_PAUSE",
            resource_gates_passed=False,
            resource_pressure_signal="EXTERNAL_DRIVE_OFFLINE",
        )
        self.assertEqual(
            "RESOURCE_PAUSE_CANDIDATE",
            self.runtime.evaluate_recovery(pause)["decision_action"],
        )

    def test_error_refs_are_bound_to_stage039_classification(self):
        retry = self.runtime.build_recovery_request("STAGE039_RETRY")
        self.assertEqual(
            "STAGE039_RETRY_CANDIDATE",
            self.runtime.evaluate_recovery(retry)["decision_action"],
        )
        wrong_retry = self.runtime.build_recovery_request(
            "STAGE039_RETRY",
            error_ref="error:PERMANENT_DATA_CORRUPTION",
        )
        wrong_failure = self.runtime.build_recovery_request(
            "SAFE_FAILURE",
            error_ref="error:TRANSIENT_OPERATION_TIMEOUT",
        )
        for request in (wrong_retry, wrong_failure):
            with self.subTest(request=request):
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    self.runtime.evaluate_recovery(request)["decision_action"],
                )

    def test_phase1_checker_is_structured_fail_closed_for_non_mapping(self):
        checks = self.phase1.evaluate_contract([])
        self.assertTrue(checks)
        self.assertFalse(checks["root_exact_shape"])
        self.assertFalse(checks["nested_exact_shapes"])
        self.assertFalse(all(checks.values()))

    def test_review_reverifies_sources_phase4_commit_and_all_phases(self):
        report = self._review().build_stage043_review_report()
        self.assertTrue(report["source_integrity_valid"], report)
        self.assertTrue(all(report["source_integrity_checks"].values()), report)
        self.assertEqual(
            {
                "commit": PHASE4_COMMIT,
                "km_ids_tree": PHASE4_KMIDS_TREE,
                "required_ancestor_of_head": True,
            },
            report["phase4_commit_binding"],
        )
        self.assertTrue(report["phase4_commit_binding_valid"], report)
        self.assertEqual(
            {
                "phase1_contract_valid": True,
                "phase2_slice_valid": True,
                "phase3_scenarios_valid": True,
                "phase4_delivery_valid": True,
            },
            report["phase_results"],
        )

    def test_review_findings_are_machine_checked_and_fail_closed(self):
        review = self._review()
        report = review.build_stage043_review_report()
        self.assertEqual(6, report["finding_count"])
        self.assertEqual(
            {"Critical": 1, "Important": 5, "Minor": 0},
            report["finding_counts"],
        )
        self.assertTrue(all(report["finding_checks"].values()), report)
        tampered = copy.deepcopy(report["finding_checks"])
        tampered["recovery_identity_evidence_bound"] = False
        blocked = review.build_stage043_review_report(finding_checks=tampered)
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual("IDS-STAGE043-REVIEW-GATE", blocked["next_gate"])
        self.assertFalse(blocked["github_upload_allowed"])

    def test_governance_closes_stage_only_to_stage044_separate_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        for marker in (
            'status: "stage043_completed_reviewed_local"',
            'review_status: "passed"',
            'current_task_id: "IDS-V0_1-STAGE043-REVIEW"',
            'next_allowed_task_id: "IDS-V0_1-STAGE044-P1"',
            'push_allowed: false',
            'stage044_entry_allowed: false',
        ):
            self.assertIn(marker, batch)
        for marker in (
            'current_phase_id: "IDS-STAGE043-REVIEW"',
            'current_task_id: "IDS-V0_1-STAGE043-REVIEW"',
            'next_gate_id: "IDS-STAGE044-P1-GATE"',
            'status: "completed_reviewed_local"',
        ):
            self.assertIn(marker, roadmap)
        self.assertIn(REVIEW_EVENT_ID, events)
        top = "\n".join(handoff.splitlines()[:32])
        self.assertTrue(
            (
                "Completed task in this run: `IDS-V0_1-STAGE043-REVIEW`" in top
                and "Next allowed task: `IDS-V0_1-STAGE044-P1`" in top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P1`" in top
                and "Next allowed task: `IDS-V0_1-STAGE044-P2`" in top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P2`" in top
                and "Next allowed task: `IDS-V0_1-STAGE044-P3`" in top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P3`" in top
                and "Next allowed task: `IDS-V0_1-STAGE044-P4`" in top
            )
        )
        self.assertIn("NO_STAGE044_THIS_RUN", REVIEW_ARTIFACT.read_text(encoding="utf-8"))

    def test_cli_emits_exact_review_report(self):
        expected = self._review().build_stage043_review_report()
        completed = subprocess.run(
            ["python3", "-B", str(REVIEW_CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(expected, json.loads(completed.stdout))
        self.assertEqual("", completed.stderr)


if __name__ == "__main__":
    unittest.main()
