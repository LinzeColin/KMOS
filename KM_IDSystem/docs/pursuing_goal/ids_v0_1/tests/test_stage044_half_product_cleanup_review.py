import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
RUNTIME_CHECKER = PROJECT_ROOT / "scripts" / "check_half_product_cleanup_runtime.py"
REVIEW_CHECKER = PROJECT_ROOT / "scripts" / "check_half_product_cleanup_stage_review.py"
REVIEW_ARTIFACT = BASE / "STAGE044_STAGE_REVIEW.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = PROJECT_ROOT / "docs" / "HANDOFF.md"

PHASE4_COMMIT = "5da8fdf64cab35545e717900e71ccbbb5dacb11c"
PHASE4_KMIDS_TREE = "4df0d01406b2021ef0c4968373b9649733a5f857"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE044-REVIEW-20260719-001"


def _load(path: Path, name: str):
    if not path.is_file():
        raise AssertionError(f"missing checker: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load checker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage044HalfProductCleanupReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = _load(RUNTIME_CHECKER, "stage044_review_runtime_tests")
        cls.review = _load(REVIEW_CHECKER, "stage044_review_checker_tests")

    def _review(self):
        return self.review

    def test_review_artifacts_and_identity_exist(self):
        self.assertTrue(REVIEW_ARTIFACT.is_file())
        self.assertTrue(REVIEW_CHECKER.is_file())
        report = self._review().build_stage044_review_report()
        self.assertEqual(
            "ids.stage044.half_product_cleanup.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE044-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-044", report["acceptance_id"])
        self.assertEqual("PASS_REVIEWED_LOCAL_DELETE_DISABLED", report["result"])

    def test_recoverable_nonterminal_states_never_become_cleanup_candidates(self):
        contract = self.runtime._load_contract()
        self.assertEqual(
            ["FAILED", "DEAD_LETTERED", "CANCELLED"],
            self.runtime.CANDIDATE_STATES,
        )
        for state in ("PAUSED", "RETRY_WAIT"):
            with self.subTest(state=state):
                request = self.runtime.build_cleanup_request(observed_job_state=state)
                result = self.runtime.evaluate_cleanup_candidate(
                    request,
                    contract=contract,
                )
                self.assertEqual(
                    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                    result["decision_action"],
                )
                self.assertEqual("JOB_ACTIVE_SUCCEEDED_OR_UNKNOWN", result["reason_code"])
                self.assertFalse(result["delete_allowed"])

    def test_candidate_identity_and_provenance_are_canonically_bound(self):
        contract = self.runtime._load_contract()
        valid = self.runtime.build_cleanup_request()
        self.assertTrue(self.runtime.validate_cleanup_request(valid))
        self.assertEqual(
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED",
            self.runtime.evaluate_cleanup_candidate(valid, contract=contract)[
                "decision_action"
            ],
        )

        invalid_requests = (
            self.runtime.build_cleanup_request(
                input_refs=["KM_IDSystem/README.md"],
            ),
            self.runtime.build_cleanup_request(
                creator_job_id="control:stage044:job:another",
            ),
            self.runtime.build_cleanup_request(
                approved_root_canonical_identity="root:sha256:" + "f" * 64,
            ),
            self.runtime.build_cleanup_request(
                cleanup_manifest_ref="manifest:sha256:" + "0" * 64,
            ),
            self.runtime.build_cleanup_request(
                writer_quiescence_evidence_ref="evidence:stage044:writer-forged",
            ),
            self.runtime.build_cleanup_request(
                resource_gate_evidence_ref="evidence:stage044:resource-forged",
            ),
        )
        for request in invalid_requests:
            with self.subTest(request=request):
                self.assertFalse(self.runtime.validate_cleanup_request(request))
                result = self.runtime.evaluate_cleanup_candidate(
                    request,
                    contract=contract,
                )
                self.assertEqual(
                    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                    result["decision_action"],
                )
                self.assertFalse(result["delete_allowed"])

    def test_paths_require_one_canonical_lexical_representation(self):
        contract = self.runtime._load_contract()
        for path in (
            "control/stage044/./attempt-output.partial",
            "control//stage044/attempt-output.partial",
        ):
            with self.subTest(path=path):
                request = self.runtime.build_cleanup_request(root_relative_path=path)
                self.assertFalse(self.runtime.validate_cleanup_request(request))
                result = self.runtime.evaluate_cleanup_candidate(
                    request,
                    contract=contract,
                )
                self.assertEqual(
                    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                    result["decision_action"],
                )

    def test_full_contract_and_human_status_are_exact_and_fail_closed(self):
        contract = self.runtime._load_contract()
        tampered_contracts = []
        path_tamper = copy.deepcopy(contract)
        path_tamper["path_and_identity_contract"]["file_type_allowlist"] = [
            "DIRECTORY"
        ]
        tampered_contracts.append(path_tamper)
        source_tamper = copy.deepcopy(contract)
        source_tamper["source_binding"]["source_member_match_count"] = 2
        tampered_contracts.append(source_tamper)
        status_tamper = copy.deepcopy(contract)
        status_tamper["human_status_projection"][
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        ]["label_zh"] = "文件已自动删除"
        tampered_contracts.append(status_tamper)

        for tampered in tampered_contracts:
            with self.subTest(tampered=tampered):
                self.assertFalse(all(self.runtime.evaluate_contract(tampered).values()))
                self.assertFalse(self.runtime._contract_fast_valid(tampered))
                result = self.runtime.evaluate_cleanup_candidate(
                    self.runtime.build_cleanup_request(),
                    contract=tampered,
                )
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
                self.assertEqual("CLEANUP_CONTRACT_INVALID", result["reason_code"])

    def test_review_reverifies_sources_phase4_commit_and_all_phases(self):
        report = self._review().build_stage044_review_report()
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
        report = review.build_stage044_review_report()
        self.assertEqual(6, report["finding_count"])
        self.assertEqual(
            {"Critical": 1, "Important": 5, "Minor": 0},
            report["finding_counts"],
        )
        self.assertTrue(all(report["finding_checks"].values()), report)
        tampered = copy.deepcopy(report["finding_checks"])
        tampered["recoverable_states_excluded"] = False
        blocked = review.build_stage044_review_report(finding_checks=tampered)
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual("IDS-STAGE044-REVIEW-GATE", blocked["next_gate"])
        self.assertFalse(blocked["stage045_entry_allowed"])
        self.assertFalse(blocked["github_upload_allowed"])

    def test_governance_closes_stage_only_to_stage045_separate_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        for marker in (
            'status: "stage044_completed_reviewed_local"',
            'review_status: "passed"',
            'current_task_id: "IDS-V0_1-STAGE044-REVIEW"',
            'next_allowed_task_id: "IDS-V0_1-STAGE045-P1"',
            'push_allowed: false',
            'stage045_entry_allowed: false',
        ):
            self.assertIn(marker, batch)
        for marker in (
            'current_phase_id: "IDS-STAGE044-REVIEW"',
            'current_task_id: "IDS-V0_1-STAGE044-REVIEW"',
            'next_gate_id: "IDS-STAGE045-P1-GATE"',
            'status: "completed_reviewed_local"',
        ):
            self.assertIn(marker, roadmap)
        self.assertIn(REVIEW_EVENT_ID, events)
        top = "\n".join(handoff.splitlines()[:32])
        self.assertTrue(
            (
                "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`" in top
                and "Next allowed task: `IDS-V0_1-STAGE045-P1`" in top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P2`" in top
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in top
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P3`" in top
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in top
            )
        )

    def test_review_preserves_delete_and_external_effect_prohibitions(self):
        report = self._review().build_stage044_review_report()
        for field in (
            "cleanup_runtime_performed",
            "filesystem_probe_performed",
            "filesystem_traversal_performed",
            "delete_operation_started",
            "unlinkat_called",
            "move_or_overwrite_performed",
            "persistent_state_write_performed",
            "audit_write_performed",
            "database_connection_performed",
            "raw_metadata_content_accessed",
            "production_runtime_activation_performed",
            "stage045_started",
            "batch_review_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        review_text = REVIEW_ARTIFACT.read_text(encoding="utf-8")
        for marker in (
            "NO_STAGE045_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
            "NO_RAW_METADATA_ACCESS",
            "NO_CLEANUP_OR_DELETE_RUNTIME",
        ):
            self.assertIn(marker, review_text)

    def test_cli_emits_exact_review_report(self):
        expected = self._review().build_stage044_review_report()
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
