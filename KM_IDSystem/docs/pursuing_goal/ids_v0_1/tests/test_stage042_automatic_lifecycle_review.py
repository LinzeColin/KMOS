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
RUNTIME_CHECKER = ROOT / "scripts" / "check_automatic_lifecycle_runtime.py"
REVIEW_CHECKER = ROOT / "scripts" / "check_automatic_lifecycle_stage_review.py"
REVIEW = PURSUE_ROOT / "STAGE042_STAGE_REVIEW.md"
CONTRACT = (
    PURSUE_ROOT
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_runtime_contract.json"
)
BATCH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"
PHASE4_COMMIT = "2c489d049d73cd632e905c7af1b39ba662a2139b"
PHASE4_KMIDS_TREE = "7d77abfd6c00ea3b663d899335d971342ac40384"


class Stage042AutomaticLifecycleStageReviewTests(unittest.TestCase):
    _cached_review_checker = None

    def _load_module(self, path: Path, name: str):
        self.assertTrue(path.is_file(), f"missing module: {path}")
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def _runtime(self):
        return self._load_module(RUNTIME_CHECKER, "stage042_review_runtime")

    def _review_checker(self):
        if self.__class__._cached_review_checker is None:
            self.__class__._cached_review_checker = self._load_module(
                REVIEW_CHECKER, "stage042_automatic_lifecycle_review"
            )
        return self.__class__._cached_review_checker

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_review_artifacts_exist(self):
        self.assertTrue(REVIEW.is_file(), f"missing review artifact: {REVIEW}")
        self.assertTrue(
            REVIEW_CHECKER.is_file(), f"missing review checker: {REVIEW_CHECKER}"
        )

    def test_canonical_request_id_cannot_be_forged_or_replayed_as_new(self):
        module = self._runtime()
        ledger = module.IsolatedLifecycleDecisionLedger()
        original = module.build_control_request("AUTO_START")
        first = module.evaluate_lifecycle(original, ledger=ledger)
        replay = module.evaluate_lifecycle(original, ledger=ledger)
        self.assertEqual("AUTO_START_CANDIDATE", first["decision_action"])
        self.assertEqual(first, replay)
        self.assertEqual(1, ledger.record_count)

        forged = module.build_control_request("AUTO_START")
        forged["lifecycle_request_id"] = f"lifecycle:stage042:{'f' * 64}"
        forged_ledger = module.IsolatedLifecycleDecisionLedger()
        rejected = module.evaluate_lifecycle(forged, ledger=forged_ledger)
        self.assertEqual(
            "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH",
            rejected["decision_action"],
        )
        self.assertEqual("error:LIFECYCLE_REQUEST_ID_MISMATCH", rejected["error_ref"])
        self.assertEqual(0, forged_ledger.record_count)

        changed = copy.deepcopy(original)
        changed["expected_state_version"] += 1
        conflict = module.evaluate_lifecycle(changed, ledger=ledger)
        self.assertEqual(
            "REJECT_LIFECYCLE_REQUEST_CONFLICT", conflict["decision_action"]
        )
        self.assertEqual(1, ledger.record_count)

    def test_request_version_and_reason_semantics_fail_closed(self):
        module = self._runtime()
        for value in (0, -1, True, 1.0):
            with self.subTest(expected_state_version=value):
                request = module.build_control_request(
                    "AUTO_START", expected_state_version=value
                )
                self.assertFalse(module.validate_control_request(request))
                result = module.evaluate_lifecycle(request)
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
                self.assertEqual("error:INVALID_LIFECYCLE_REQUEST", result["error_ref"])

        mismatched = module.build_control_request(
            "AUTO_START", reason_code="CLEANUP_SCAN_DUE"
        )
        self.assertFalse(module.validate_control_request(mismatched))
        result = module.evaluate_lifecycle(mismatched)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("error:INVALID_LIFECYCLE_REQUEST", result["error_ref"])

        request_contract = self._contract()["request_contract"]
        self.assertTrue(request_contract["expected_state_version_must_be_positive"])
        self.assertEqual(
            {
                "AUTO_START": "ELIGIBLE_CONTROL_START",
                "AUTO_PAUSE": "RESOURCE_PAUSE_REQUIRED",
                "AUTO_RESUME": "RESOURCE_STABILITY_REVALIDATED",
                "SAFE_SHUTDOWN": "ORDERLY_CONTROL_SHUTDOWN",
                "CLEANUP_CANDIDATE_SCAN": "CLEANUP_SCAN_DUE",
            },
            request_contract["reason_code_by_action"],
        )

    def test_resume_stability_requires_temporally_consistent_evidence(self):
        module = self._runtime()
        valid = module.build_control_request("AUTO_RESUME")
        evidence = valid["evidence"]
        self.assertEqual(940, evidence["resource_stability_started_at_epoch_seconds"])
        self.assertEqual(
            evidence["resource_stable_for_seconds"],
            evidence["evaluated_at_epoch_seconds"]
            - evidence["resource_stability_started_at_epoch_seconds"],
        )
        self.assertEqual(
            "AUTO_RESUME_CANDIDATE",
            module.evaluate_lifecycle(valid)["decision_action"],
        )

        for started_at, duration in ((1000, 60), (1001, 60), (940, 59)):
            with self.subTest(started_at=started_at, duration=duration):
                request = module.build_control_request("AUTO_RESUME")
                request["evidence"][
                    "resource_stability_started_at_epoch_seconds"
                ] = started_at
                request["evidence"]["resource_stable_for_seconds"] = duration
                request["lifecycle_request_id"] = module.derive_lifecycle_request_id(
                    request
                )
                result = module.evaluate_lifecycle(request)
                self.assertNotEqual("AUTO_RESUME_CANDIDATE", result["decision_action"])
                self.assertEqual([], result["transition_candidates"])

    def test_cleanup_candidate_requires_paused_writer_quiescence(self):
        module = self._runtime()
        paused = module.build_control_request("CLEANUP_CANDIDATE_SCAN")
        self.assertEqual(
            "CLEANUP_CANDIDATE_ONLY",
            module.evaluate_lifecycle(paused)["decision_action"],
        )
        for state in ("CREATED", "QUEUED", "RUNNING", "RETRY_WAIT"):
            with self.subTest(state=state):
                request = module.build_control_request(
                    "CLEANUP_CANDIDATE_SCAN",
                    expected_state=state,
                    active_claim_or_lock=False,
                )
                result = module.evaluate_lifecycle(request)
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
                self.assertEqual([], result["transition_candidates"])
        self.assertEqual(
            ["PAUSED"],
            self._contract()["decision_contract"]["CLEANUP_CANDIDATE_SCAN"][
                "eligible_states"
            ],
        )

    def test_review_reverifies_sources_phase4_commit_and_all_four_phases(self):
        report = self._review_checker().build_stage042_review_report()
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
        checker = self._review_checker()
        report = checker.build_stage042_review_report()
        self.assertEqual(5, report["finding_count"])
        self.assertEqual(
            {"Critical": 1, "Important": 4, "Minor": 0},
            report["finding_counts"],
        )
        self.assertTrue(all(report["finding_checks"].values()), report)

        tampered = dict(report["finding_checks"])
        tampered["canonical_request_id_enforced"] = False
        blocked = checker.build_stage042_review_report(finding_checks=tampered)
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual("IDS-STAGE042-REVIEW-GATE", blocked["next_gate"])
        self.assertFalse(blocked["github_upload_allowed"])

    def test_governance_closes_stage_only_to_stage043_separate_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn('status: "stage042_completed_reviewed_local"', batch)
        self.assertIn('review_status: "passed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE042-REVIEW"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE043-P1"', batch)
        self.assertIn('push_allowed: false', batch)
        self.assertIn('stage043_entry_allowed: false', batch)
        self.assertIn('current_phase_id: "IDS-STAGE042-REVIEW"', roadmap)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE042-REVIEW"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE043-P1-GATE"', roadmap)
        handoff_top = "\n".join(handoff.splitlines()[:28])
        self.assertTrue(
            (
                "Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE043-P1`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P1`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE043-P2`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P2`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE043-P3`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P3`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE043-P4`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P4`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE043-REVIEW`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-REVIEW`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE044-P1`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P1`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE044-P2`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P2`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE044-P3`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P3`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE044-P4`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P4`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE045-P1`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE045-P1`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE045-P2`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE045-P2`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE045-P3`"
                in handoff_top
            )
        )
        staged_section = handoff.split("## IDS v0.1 Staged Development", 1)[1]
        staged_head = "\n".join(staged_section.splitlines()[:18])
        self.assertTrue(
            "`STAGE-041`, `STAGE-042` and `STAGE-043` are locally reviewed"
            in staged_head
            or "`STAGE-041..STAGE-044` are locally reviewed" in staged_head,
            staged_head,
        )
        self.assertTrue(
            "Current task: `IDS-V0_1-STAGE044-P3`" in staged_head
            or "Current task: `IDS-V0_1-STAGE044-P4`" in staged_head
            or "Current task: `IDS-V0_1-STAGE044-REVIEW`" in staged_head
            or "Current task: `IDS-V0_1-STAGE045-P1`" in staged_head
            or "Current task: `IDS-V0_1-STAGE045-P2`" in staged_head
        )

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matching = [
            event
            for event in events
            if event.get("event_id")
            == "EVT-IDS-V0_1-STAGE042-REVIEW-20260718-001"
        ]
        self.assertEqual(1, len(matching), matching)
        self.assertEqual("stage_review", matching[0]["event_type"])
        self.assertEqual("IDS-V0_1-STAGE042-REVIEW", matching[0]["task_id"])

    def test_review_document_and_report_preserve_safety_boundaries(self):
        text = REVIEW.read_text(encoding="utf-8")
        for term in (
            "STAGE042-REVIEW-F1",
            "STAGE042-REVIEW-F2",
            "STAGE042-REVIEW-F3",
            "STAGE042-REVIEW-F4",
            "STAGE042-REVIEW-F5",
            "NO_STAGE043_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
            "NO_RAW_METADATA_ACCESS",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

        report = self._review_checker().build_stage042_review_report()
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED", report["result"]
        )
        self.assertEqual("completed_reviewed_local", report["stage_review_status"])
        self.assertEqual("IDS-STAGE043-P1-GATE", report["next_gate"])
        for field in (
            "production_runtime_activation_performed",
            "raw_metadata_content_accessed",
            "fake_ids_business_data_used",
            "stage043_started",
            "batch_review_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_cli_emits_reviewed_local_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(REVIEW_CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0, completed.returncode, completed.stderr or completed.stdout
        )
        self.assertEqual("", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["review_valid"], report)
        self.assertEqual("IDS-STAGE043-P1-GATE", report["next_gate"])


if __name__ == "__main__":
    unittest.main()
