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
RUNTIME_CHECKER = ROOT / "scripts" / "check_lock_registry_runtime.py"
REVIEW_CHECKER = ROOT / "scripts" / "check_lock_registry_stage_review.py"
REVIEW = PURSUE_ROOT / "STAGE041_STAGE_REVIEW.md"
CONTRACT = (
    PURSUE_ROOT
    / "lock_registry"
    / "stage041_lock_registry_runtime_contract.json"
)
BATCH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"
CONTROL_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
)


class Stage041LockRegistryStageReviewTests(unittest.TestCase):
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
        return self._load_module(RUNTIME_CHECKER, "stage041_review_runtime")

    def _review_checker(self):
        if self.__class__._cached_review_checker is None:
            self.__class__._cached_review_checker = self._load_module(
                REVIEW_CHECKER, "stage041_lock_registry_review"
            )
        return self.__class__._cached_review_checker

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _request(self, module, *, role="primary", now=1000):
        return module.build_control_request(
            CONTROL_REF,
            operation_family="FILE_PROCESSING",
            holder_role=role,
            requested_at_epoch_seconds=now,
        )

    def test_review_artifacts_exist(self):
        self.assertTrue(REVIEW.is_file(), f"missing review artifact: {REVIEW}")
        self.assertTrue(
            REVIEW_CHECKER.is_file(), f"missing review checker: {REVIEW_CHECKER}"
        )

    def test_cas_versions_require_strict_positive_integers(self):
        module = self._runtime()
        registry = module.IsolatedLockRegistry(self._contract())
        acquired = registry.acquire(self._request(module))

        for value in (True, 1.0):
            with self.subTest(value=value):
                evidence = copy.deepcopy(acquired)
                evidence["lock_versions"] = {
                    key: value for key in acquired["lock_keys"]
                }
                commit = registry.can_commit(
                    self._request(module, now=1001), evidence
                )
                self.assertEqual("STALE_FENCING_TOKEN", commit["result_code"])
                self.assertEqual("REJECT_COMMIT", commit["decision_action"])

        takeover_evidence = copy.deepcopy(acquired)
        takeover_evidence["lock_versions"] = {
            key: True for key in acquired["lock_keys"]
        }
        takeover = registry.takeover(
            self._request(module, role="successor", now=1035),
            takeover_evidence,
        )
        self.assertEqual("STALE_TAKEOVER_EVIDENCE", takeover["result_code"])

    def test_logical_time_and_live_lease_mutations_fail_closed(self):
        module = self._runtime()
        contract = self._contract()

        negative_registry = module.IsolatedLockRegistry(contract)
        negative = negative_registry.acquire(self._request(module, now=-1))
        self.assertEqual("INVALID_CONTROL_REQUEST", negative["result_code"])
        self.assertEqual({}, negative_registry.snapshot()["locks"])

        registry = module.IsolatedLockRegistry(contract)
        acquired = registry.acquire(self._request(module, now=1000))
        backward_commit = registry.can_commit(
            self._request(module, now=999), acquired
        )
        self.assertEqual(
            "NON_MONOTONIC_LOGICAL_TIME", backward_commit["result_code"]
        )
        self.assertEqual("REJECT_COMMIT", backward_commit["decision_action"])

        backward_renew = registry.renew(self._request(module, now=999), acquired)
        self.assertEqual(
            "NON_MONOTONIC_LOGICAL_TIME", backward_renew["result_code"]
        )
        same_time_renew = registry.renew(
            self._request(module, now=1000), acquired
        )
        self.assertEqual("LEASE_NOT_EXTENDED", same_time_renew["result_code"])

        expired_release = registry.release(
            self._request(module, now=1030), acquired
        )
        self.assertEqual("LEASE_EXPIRED", expired_release["result_code"])
        self.assertEqual(2, len(registry.snapshot()["locks"]))

    def test_runtime_contract_semantics_are_exact_and_tamper_evident(self):
        module = self._runtime()
        contract = self._contract()
        self.assertTrue(all(module.evaluate_contract(contract).values()))
        request_contract = contract["request_contract"]
        self.assertTrue(request_contract["requested_at_must_be_non_negative"])
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            request_contract["logical_time_regression_action"],
        )
        self.assertTrue(request_contract["renewal_must_strictly_extend_expiry"])
        self.assertTrue(request_contract["release_requires_live_lease"])

        wrong_scope = copy.deepcopy(contract)
        wrong_scope["operation_scope_contract"]["FILE_PROCESSING"][
            "job_types"
        ] = ["REPORT"]
        self.assertFalse(
            module.evaluate_contract(wrong_scope)["operation_scope_exact"]
        )

        blank_provenance = copy.deepcopy(contract)
        provenance = blank_provenance["policy"]["parameter_provenance"][
            "lease_duration_seconds"
        ]
        provenance["source"] = ""
        provenance["validation_evidence"] = ""
        provenance["rollback"] = ""
        self.assertFalse(
            module.evaluate_contract(blank_provenance)[
                "parameter_provenance_complete"
            ]
        )

        wrong_relationships = copy.deepcopy(contract)
        wrong_relationships["policy"]["parameter_relationships"] = ["anything"]
        checks = module.evaluate_contract(wrong_relationships)
        self.assertFalse(checks["parameter_relationships_exact"])

    def test_review_reverifies_sources_and_all_four_phases(self):
        report = self._review_checker().build_stage041_review_report()
        self.assertTrue(report["source_integrity_valid"], report)
        self.assertTrue(all(report["source_integrity_checks"].values()), report)
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
        report = checker.build_stage041_review_report()
        self.assertEqual(4, report["finding_count"])
        self.assertEqual(
            {"Critical": 1, "Important": 3, "Minor": 0},
            report["finding_counts"],
        )
        self.assertTrue(all(report["finding_checks"].values()), report)

        tampered = dict(report["finding_checks"])
        tampered["strict_integer_cas_versions"] = False
        blocked = checker.build_stage041_review_report(finding_checks=tampered)
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual("IDS-STAGE041-REVIEW-GATE", blocked["next_gate"])
        self.assertFalse(blocked["github_upload_allowed"])

    def test_governance_closes_stage_only_to_stage042_separate_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn('status: "stage041_completed_reviewed_local"', batch)
        self.assertIn('review_status: "passed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE041-REVIEW"', batch)
        self.assertIn(
            'next_allowed_task_id: "IDS-V0_1-STAGE042-P1"', batch
        )
        self.assertIn('push_allowed: false', batch)
        self.assertIn('stage042_entry_allowed: false', batch)
        self.assertIn('current_phase_id: "IDS-STAGE041-REVIEW"', roadmap)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE041-REVIEW"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE042-P1-GATE"', roadmap)
        handoff_top = "\n".join(handoff.splitlines()[:24])
        self.assertTrue(
            (
                "Completed task in this run: `IDS-V0_1-STAGE041-REVIEW`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE042-P1`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P1`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE042-P2`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P2`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE042-P3`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P3`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE042-P4`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P4`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE042-REVIEW`"
                in handoff_top
            )
            or (
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
                "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE046-P1`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P1`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`"
                in handoff_top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                in handoff_top
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`"
                in handoff_top
            )
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
            == "EVT-IDS-V0_1-STAGE041-REVIEW-20260718-001"
        ]
        self.assertEqual(1, len(matching), matching)
        self.assertEqual("stage_review", matching[0]["event_type"])
        self.assertEqual("IDS-V0_1-STAGE041-REVIEW", matching[0]["task_id"])

    def test_review_document_and_report_preserve_safety_boundaries(self):
        text = REVIEW.read_text(encoding="utf-8")
        for term in (
            "STAGE041-REVIEW-F1",
            "STAGE041-REVIEW-F2",
            "STAGE041-REVIEW-F3",
            "STAGE041-REVIEW-F4",
            "NO_STAGE042_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
            "NO_RAW_METADATA_ACCESS",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

        report = self._review_checker().build_stage041_review_report()
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED", report["result"]
        )
        self.assertEqual("completed_reviewed_local", report["stage_review_status"])
        self.assertEqual("IDS-STAGE042-P1-GATE", report["next_gate"])
        for field in (
            "production_runtime_activation_performed",
            "raw_metadata_content_accessed",
            "fake_ids_business_data_used",
            "stage042_started",
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
        self.assertEqual("IDS-STAGE042-P1-GATE", report["next_gate"])


if __name__ == "__main__":
    unittest.main()
