#!/usr/bin/env python3
"""Validate the STAGE-041 Phase 4 lock-registry closeout contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_delivery.py"
CONTRACT = BASE / "lock_registry/stage041_lock_registry_delivery_contract.json"
EVIDENCE = BASE / "STAGE041_PHASE4_CLOSEOUT.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "03677aaec2fe7dbe6780736bf802e6ef555f383d"
PHASE3_KMIDS_TREE = "ac363a93c711ac8bf41d9cb3894e37f3b3f1a405"
OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "INDEX_SWITCH",
    "REPORT_GENERATION",
]
PRESSURE_SIGNALS = {
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
}
CLEANUP_CLASSES = {"TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"}
PROTECTED_CLASSES = {
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
}
AUTOMATIC_LOCK_DECISIONS = {
    "EXACT_IDEMPOTENT_REPLAY",
    "MATCHING_HOLDER_RENEWAL",
    "MATCHING_HOLDER_RELEASE",
}
MANUAL_CASES = {
    "STALE_OR_INCOMPLETE_CAS",
    "ACTIVE_SAME_SOURCE_CONFLICT",
    "RESOURCE_GATE_OWNER_REVALIDATION",
    "WORKER_PROCESS_CRASH",
    "PROTECTED_CLEANUP_REQUEST",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "PROCESS_EXIT_WITHOUT_PERSISTENT_STATE",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "process_termination_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "automatic_resume_performed",
    "process_crash_recovery_performed",
    "persistent_lock_write_performed",
    "state_registry_write_performed",
    "database_connection_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage041LockRegistryDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage041_lock_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage041_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_and_source_binding_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage041.lock_registry.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-041", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE041-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-041", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE041-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36",
            source["source_member_sha256"],
        )

    def test_phase3_commit_tree_and_upstream_hashes_are_current(self):
        contract = self._contract()
        self.assertEqual(
            {
                "commit": PHASE3_COMMIT,
                "km_ids_tree": PHASE3_KMIDS_TREE,
                "required_ancestor_of_head": True,
            },
            contract["phase3_commit_binding"],
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", PHASE3_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(0, ancestor.returncode)
        tree = subprocess.run(
            ["git", "rev-parse", f"{PHASE3_COMMIT}:KM_IDSystem"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(PHASE3_KMIDS_TREE, tree)
        checks = self._module().validate_delivery_contract(contract)
        self.assertTrue(all(checks.values()), checks)

    def test_contract_tampering_fails_closed_before_delivery_checks(self):
        module = self._module()
        mutations = []
        mutators = (
            lambda value: value.update({"unknown_root": True}),
            lambda value: value["phase3_commit_binding"].update(
                {"commit": "0" * 40}
            ),
            lambda value: value["cleanup_allowlist"][
                "cleanup_eligible_classes"
            ].append("FACT_SOURCE"),
            lambda value: value["recovery_handling"].update(
                {"successful_automatic_recovery_cases_observed": ["FAKE"]}
            ),
            lambda value: value["review_gate"].update(
                {"phase4_may_mark_stage_reviewed": True}
            ),
            lambda value: value["truth_flags"].update(
                {"production_runtime_activation_performed": True}
            ),
        )
        for mutate in mutators:
            candidate = copy.deepcopy(self._contract())
            mutate(candidate)
            mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                report = module.build_stage041_phase4_delivery_report(candidate)
                self.assertFalse(report["contract_valid"], report)
                self.assertFalse(report["delivery_checks_performed"], report)
                self.assertEqual("IDS-STAGE041-P4-GATE", report["next_gate"])

    def test_lock_lifecycle_evidence_is_exact_and_monotonic(self):
        lifecycle = self._report()["lock_lifecycle_evidence"]
        self.assertEqual(OPERATION_FAMILIES, lifecycle["operation_families"])
        self.assertEqual("SOURCE_PIPELINE", lifecycle["shared_lock_namespace"])
        self.assertEqual(5, lifecycle["primary_acquisition_count"])
        self.assertEqual(5, lifecycle["exact_replay_count"])
        self.assertEqual(25, lifecycle["resource_conflict_count"])
        self.assertTrue(lifecycle["canonical_all_or_none"])
        self.assertTrue(lifecycle["renewal_version_monotonic"])
        self.assertTrue(lifecycle["takeover_fence_and_version_monotonic"])
        self.assertTrue(lifecycle["stale_cas_and_fence_rejected"])
        self.assertTrue(lifecycle["release_tombstone_monotonic"])
        self.assertTrue(lifecycle["phase2_runtime_valid"])
        self.assertTrue(lifecycle["phase3_scenarios_valid"])

    def test_state_retry_and_backpressure_evidence_is_reviewed(self):
        evidence = self._report()["state_retry_backpressure_evidence"]
        graph = evidence["job_state_graph"]
        self.assertEqual("ids.job_state.v1", graph["state_model_version"])
        self.assertEqual(8, graph["job_type_count"])
        self.assertEqual(11, graph["job_state_count"])
        self.assertEqual(4, graph["terminal_state_count"])
        self.assertEqual(21, graph["allowed_transition_count"])
        failure = evidence["failure_retry_log"]
        self.assertEqual(3, failure["attempt_count"])
        self.assertEqual(2, failure["retry_count"])
        self.assertEqual("DEAD_LETTERED", failure["final_state"])
        self.assertFalse(failure["persisted"])
        self.assertEqual(PRESSURE_SIGNALS, set(evidence["backpressure_trigger_proof"]))
        self.assertTrue(evidence["reviewed_stage040_delivery_valid"])

    def test_cleanup_allowlist_is_narrow_and_protected(self):
        cleanup = self._report()["cleanup_allowlist"]
        self.assertEqual(CLEANUP_CLASSES, set(cleanup["cleanup_eligible_classes"]))
        self.assertEqual(
            PROTECTED_CLASSES, set(cleanup["protected_artifact_classes"])
        )
        self.assertEqual(5, cleanup["protected_ref_count"])
        self.assertTrue(all(cleanup["protected_ref_checks"].values()), cleanup)
        self.assertTrue(cleanup["cleanup_manifest_required"])
        self.assertEqual("STAGE-044", cleanup["runtime_owner"])
        self.assertFalse(cleanup["cleanup_runtime_performed"])
        self.assertFalse(cleanup["delete_attempt_performed"])

    def test_automatic_and_manual_handling_is_truthful(self):
        handling = self._report()["recovery_handling"]
        self.assertEqual(
            AUTOMATIC_LOCK_DECISIONS, set(handling["automatic_lock_decision_cases"])
        )
        self.assertEqual([], handling["automatic_recovery_eligible_cases"])
        self.assertEqual([], handling["successful_automatic_recovery_cases_observed"])
        self.assertEqual(MANUAL_CASES, set(handling["manual_action_required_cases"]))
        self.assertFalse(handling["automatic_resume_allowed"])
        self.assertFalse(handling["automatic_resume_performed"])
        self.assertEqual("STAGE-042", handling["automatic_resume_runtime_owner"])
        self.assertEqual("STAGE-043", handling["process_crash_recovery_runtime_owner"])

    def test_actual_isolated_orderly_release_leaves_no_active_lock(self):
        shutdown = self._report()["orderly_lock_shutdown"]
        self.assertTrue(shutdown["actual_isolated_orderly_release_performed"])
        self.assertEqual("LOCK_SET_ACQUIRED", shutdown["acquire_result_code"])
        self.assertEqual("LEASE_RENEWED", shutdown["renew_result_code"])
        self.assertEqual("LOCK_SET_RELEASED", shutdown["release_result_code"])
        self.assertEqual(0, shutdown["active_lock_count_after_release"])
        self.assertEqual(2, shutdown["tombstone_version_count"])
        self.assertTrue(shutdown["renew_versions_advanced_once"])
        self.assertTrue(shutdown["release_versions_advanced_once"])
        self.assertEqual("STALE_FENCING_TOKEN", shutdown["stale_commit_result_code"])
        self.assertFalse(shutdown["persistent_lock_write_performed"])

    def test_shutdown_recovery_rollback_and_limits_are_explicit(self):
        report = self._report()
        shutdown = report["safe_shutdown_and_recovery"]
        self.assertIn("STOP_NEW_LOCK_ACQUISITIONS", shutdown["shutdown_steps"])
        self.assertIn("VERIFY_ZERO_ACTIVE_LOCKS", shutdown["shutdown_steps"])
        self.assertIn(
            "REBUILD_ONLY_FROM_CURRENT_AUTHORIZED_EVIDENCE",
            shutdown["recovery_steps"],
        )
        self.assertFalse(shutdown["persistent_lock_state_available_after_exit"])
        self.assertFalse(shutdown["process_termination_performed"])
        self.assertFalse(shutdown["automatic_process_recovery_performed"])
        self.assertGreaterEqual(len(report["rollback_steps"]), 6)
        self.assertIn("REVERT_PHASE4_FILES_ONLY", report["rollback_steps"])
        self.assertIn("NO_PERSISTENT_LOCK_REGISTRY", report["known_limits"])
        self.assertIn(
            "NO_TRUSTED_PRODUCTION_CLOCK_SOURCE", report["known_limits"]
        )
        self.assertIn("STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS", report["known_limits"])

    def test_truth_feedback_and_next_gate_stop_at_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual("PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED", report["result"])
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE041-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未观察到自动恢复成功", report["owner_feedback_zh"])
        self.assertIn("不是生产运行或生产就绪证明", report["owner_feedback_zh"])

    def test_phase4_history_is_preserved_after_whole_stage_review(self):
        self.assertTrue(EVIDENCE.is_file(), f"missing closeout: {EVIDENCE}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn('status: "stage041_phase4_completed_review_pending"', batch)
        self.assertIn('      - "Phase 4"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE041-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE041-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE041-REVIEW-GATE"', roadmap)
        self.assertTrue(
            (
                status["phase"] == "IDS-STAGE041-REVIEW"
                and status["next_gate"] == "IDS-STAGE042-P1-GATE"
                and "IDS-V0_1-STAGE041-REVIEW" in handoff
                and "IDS-V0_1-STAGE042-P1" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-P1"
                and status["next_gate"] == "IDS-STAGE042-P2-GATE"
                and "IDS-V0_1-STAGE042-P1" in handoff
                and "IDS-V0_1-STAGE042-P2" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-P2"
                and status["next_gate"] == "IDS-STAGE042-P3-GATE"
                and "IDS-V0_1-STAGE042-P2" in handoff
                and "IDS-V0_1-STAGE042-P3" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-P3"
                and status["next_gate"] == "IDS-STAGE042-P4-GATE"
                and "IDS-V0_1-STAGE042-P3" in handoff
                and "IDS-V0_1-STAGE042-P4" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-P4"
                and status["next_gate"] == "IDS-STAGE042-REVIEW-GATE"
                and "IDS-V0_1-STAGE042-P4" in handoff
                and "IDS-V0_1-STAGE042-REVIEW" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-REVIEW"
                and status["next_gate"] == "IDS-STAGE043-P1-GATE"
                and "IDS-V0_1-STAGE042-REVIEW" in handoff
                and "IDS-V0_1-STAGE043-P1" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P1"
                and status["next_gate"] == "IDS-STAGE043-P2-GATE"
                and "IDS-V0_1-STAGE043-P1" in handoff
                and "IDS-V0_1-STAGE043-P2" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P2"
                and status["next_gate"] == "IDS-STAGE043-P3-GATE"
                and "IDS-V0_1-STAGE043-P2" in handoff
                and "IDS-V0_1-STAGE043-P3" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P3"
                and status["next_gate"] == "IDS-STAGE043-P4-GATE"
                and "IDS-V0_1-STAGE043-P3" in handoff
                and "IDS-V0_1-STAGE043-P4" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P4"
                and status["next_gate"] == "IDS-STAGE043-REVIEW-GATE"
                and "IDS-V0_1-STAGE043-P4" in handoff
                and "IDS-V0_1-STAGE043-REVIEW" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-REVIEW"
                and status["next_gate"] == "IDS-STAGE044-P1-GATE"
                and "IDS-V0_1-STAGE043-REVIEW" in handoff
                and "IDS-V0_1-STAGE044-P1" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P1"
                and status["next_gate"] == "IDS-STAGE044-P2-GATE"
                and "IDS-V0_1-STAGE044-P1" in handoff
                and "IDS-V0_1-STAGE044-P2" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P2"
                and status["next_gate"] == "IDS-STAGE044-P3-GATE"
                and "IDS-V0_1-STAGE044-P2" in handoff
                and "IDS-V0_1-STAGE044-P3" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P3"
                and status["next_gate"] == "IDS-STAGE044-P4-GATE"
                and "IDS-V0_1-STAGE044-P3" in handoff
                and "IDS-V0_1-STAGE044-P4" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P4"
                and status["next_gate"] == "IDS-STAGE044-REVIEW-GATE"
                and "IDS-V0_1-STAGE044-P4" in handoff
                and "IDS-V0_1-STAGE044-REVIEW" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-REVIEW"
                and status["next_gate"] == "IDS-STAGE045-P1-GATE"
                and "IDS-V0_1-STAGE044-REVIEW" in handoff
                and "IDS-V0_1-STAGE045-P1" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-P1"
                and status["next_gate"] == "IDS-STAGE045-P2-GATE"
                and "IDS-V0_1-STAGE045-P1" in handoff
                and "IDS-V0_1-STAGE045-P2" in handoff
            )
        )
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matching = [
            item
            for item in events
            if item.get("event_id")
            == "EVT-IDS-V0_1-STAGE041-P4-20260717-001"
        ]
        self.assertEqual(1, len(matching), matching)
        self.assertIn("whole_stage_review_performed=false", matching[0]["notes"])
        self.assertIn("stage042_entry_allowed=false", matching[0]["notes"])
        self.assertIn("push_allowed=false", matching[0]["notes"])

    def test_cli_emits_exact_machine_report(self):
        module = self._module()
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        self.assertEqual("", completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["delivery_contract_valid"], payload)
        self.assertEqual("IDS-STAGE041-REVIEW-GATE", payload["next_gate"])
        self.assertEqual(module.VALID_RESULT, payload["result"])


if __name__ == "__main__":
    unittest.main()
