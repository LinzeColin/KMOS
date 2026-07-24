#!/usr/bin/env python3
"""Validate STAGE-043 Phase 4 worker-crash-recovery closeout evidence."""

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
CHECKER = PROJECT_ROOT / "scripts/check_worker_crash_recovery_delivery.py"
CONTRACT = (
    BASE
    / "worker_crash_recovery/stage043_worker_crash_recovery_delivery_contract.json"
)
EVIDENCE = BASE / "STAGE043_PHASE4_CLOSEOUT.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "6af57993b35bde3c3a215b08ee7e1ab65c204747"
PHASE3_KMIDS_TREE = "3461f0ac16efe01fb48e0eb589ac2a00b804e226"
PRESSURE_SIGNALS = {
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
}
AUTOMATIC_HANDLING_CANDIDATES = {
    "CHECKPOINT_RESUME_CANDIDATE_AFTER_ALL_GATES",
    "STAGE039_RETRY_CANDIDATE_AFTER_ALL_GATES",
    "SAFE_FAILURE_CANDIDATE_AFTER_ALL_GATES",
}
MANUAL_CASES = {
    "MISSING_OR_STALE_CRASH_EVIDENCE",
    "CHECKPOINT_INTEGRITY_UNKNOWN",
    "IDEMPOTENCY_CONFLICT",
    "STALE_STATE_VERSION",
    "LOST_WORKER_NOT_FENCED",
    "ACTIVE_LOCK_OR_CLAIM_PRESENT",
    "RESOURCE_OWNER_REVALIDATION_REQUIRED",
    "TERMINAL_HISTORY_REOPEN_REQUEST",
    "PROTECTED_CLEANUP_REQUEST",
    "SAFE_FAILURE_CONFIRMATION_REQUIRED",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "NO_PERSISTENT_JOB_OR_RECOVERY_STATE",
}
CLEANUP_CLASSES = {"TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"}
PROTECTED_CLASSES = {
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
}
FALSE_TRUTH_FLAGS = {
    "actual_worker_process_crash_performed",
    "process_probe_performed",
    "signal_or_kill_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "worker_restart_performed",
    "automatic_recovery_performed",
    "successful_automatic_recovery_observed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
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


class Stage043WorkerCrashRecoveryDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage043_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage043_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_and_source_binding_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage043.worker_crash_recovery.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-043", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE043-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-043", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE043-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b",
            source["source_member_sha256"],
        )

    def test_phase3_commit_tree_and_upstream_hashes_are_exact(self):
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
        mutators = (
            lambda value: value.update({"unknown_root": True}),
            lambda value: value["phase3_commit_binding"].update(
                {"commit": "0" * 40}
            ),
            lambda value: value["recovery_handling"].update(
                {"successful_automatic_recovery_cases_observed": ["FAKE"]}
            ),
            lambda value: value["cleanup_allowlist"][
                "cleanup_eligible_classes"
            ].append("FACT_SOURCE"),
            lambda value: value["review_gate"].update(
                {"phase4_may_mark_stage_reviewed": True}
            ),
            lambda value: value["truth_flags"].update(
                {"process_crash_recovery_performed": True}
            ),
        )
        for mutate in mutators:
            candidate = copy.deepcopy(self._contract())
            mutate(candidate)
            with self.subTest(candidate=candidate):
                report = module.build_stage043_phase4_delivery_report(candidate)
                self.assertFalse(report["contract_valid"], report)
                self.assertFalse(report["delivery_checks_performed"], report)
                self.assertEqual("IDS-STAGE043-P4-GATE", report["next_gate"])

    def test_job_graph_retry_log_and_pressure_proof_are_exact(self):
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
        proof = evidence["backpressure_trigger_proof"]
        self.assertEqual(PRESSURE_SIGNALS, set(proof))
        self.assertTrue(all(proof.values()), proof)

    def test_phase3_scenarios_and_process_exit_are_replayed_truthfully(self):
        evidence = self._report()["phase3_recovery_evidence"]
        self.assertEqual(13, evidence["scenario_count"])
        self.assertEqual(13, evidence["passed_scenario_count"])
        self.assertTrue(evidence["phase2_slice_valid"])
        self.assertTrue(evidence["phase3_scenarios_valid"])
        exit_evidence = evidence["isolated_process_exit"]
        self.assertEqual(73, exit_evidence["observed_exit_code"])
        self.assertTrue(exit_evidence["stdout_empty"])
        self.assertTrue(exit_evidence["stderr_empty"])
        self.assertFalse(exit_evidence["signal_or_kill_performed"])
        self.assertFalse(exit_evidence["worker_restart_performed"])
        self.assertFalse(exit_evidence["process_crash_recovery_performed"])

    def test_conditional_handling_and_manual_cases_are_explicit(self):
        handling = self._report()["recovery_handling"]
        self.assertEqual(
            AUTOMATIC_HANDLING_CANDIDATES,
            set(handling["conditional_automatic_handling_candidates"]),
        )
        self.assertEqual([], handling["automatic_recovery_eligible_cases"])
        self.assertEqual([], handling["successful_automatic_recovery_cases_observed"])
        self.assertEqual(MANUAL_CASES, set(handling["manual_action_required_cases"]))
        self.assertTrue(handling["persistent_state_required"])
        self.assertTrue(handling["lost_worker_fence_required"])
        self.assertTrue(handling["fresh_admission_claim_lock_cycle_required"])
        self.assertFalse(handling["automatic_recovery_performed"])

    def test_same_source_exclusion_and_cleanup_remain_fail_closed(self):
        report = self._report()
        exclusion = report["operation_exclusion_evidence"]
        self.assertEqual(4, exclusion["required_operation_family_count"])
        self.assertEqual(25, exclusion["source_full_conflict_count"])
        self.assertEqual(16, exclusion["selected_matrix_conflict_count"])
        self.assertEqual(0, exclusion["operation_invocation_count"])
        self.assertEqual(0, exclusion["queue_record_created_count"])
        self.assertEqual(0, exclusion["retry_budget_consumed_count"])
        self.assertTrue(exclusion["all_family_checks_passed"])
        cleanup = report["cleanup_allowlist"]
        self.assertEqual(CLEANUP_CLASSES, set(cleanup["cleanup_eligible_classes"]))
        self.assertEqual(PROTECTED_CLASSES, set(cleanup["protected_artifact_classes"]))
        self.assertEqual(5, cleanup["protected_ref_count"])
        self.assertTrue(all(cleanup["protected_ref_checks"].values()), cleanup)
        self.assertEqual("STAGE-044", cleanup["runtime_owner"])
        self.assertFalse(cleanup["cleanup_runtime_performed"])
        self.assertFalse(cleanup["delete_attempt_performed"])

    def test_safe_shutdown_recovery_rollback_and_limits_are_explicit(self):
        report = self._report()
        shutdown = report["safe_shutdown_and_recovery"]
        self.assertIn("STOP_NEW_RECOVERY_EVALUATIONS", shutdown["shutdown_steps"])
        self.assertIn(
            "PRESERVE_CRASH_CHECKPOINT_AND_AUDIT_EVIDENCE",
            shutdown["shutdown_steps"],
        )
        self.assertTrue(shutdown["reviewed_transport_orderly_shutdown_proved"])
        self.assertTrue(shutdown["reviewed_transport_queue_closed"])
        self.assertTrue(shutdown["reviewed_transport_resource_locks_released"])
        self.assertFalse(shutdown["persistent_recovery_state_available_after_exit"])
        self.assertIn(
            "REOBSERVE_CRASH_HEARTBEAT_LEASE_STATE_AND_CHECKPOINT",
            shutdown["recovery_steps"],
        )
        self.assertFalse(shutdown["process_termination_performed"])
        self.assertFalse(shutdown["automatic_process_recovery_performed"])
        self.assertIn("REVERT_PHASE4_FILES_ONLY", report["rollback_steps"])
        self.assertIn("NO_PERSISTENT_JOB_OR_RECOVERY_STATE", report["known_limits"])
        self.assertIn(
            "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS", report["known_limits"]
        )

    def test_truth_feedback_and_next_gate_stop_at_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual("PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED", report["result"])
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE043-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未观察到自动恢复成功", report["owner_feedback_zh"])
        self.assertIn("不是生产运行或生产就绪证明", report["owner_feedback_zh"])

    def test_governance_routes_phase4_to_separate_stage_review(self):
        for path in (BATCH, ROADMAP, EVENTS, HANDOFF, STATUS):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn('status: "stage043_phase4_completed_review_pending"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE043-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE043-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE043-REVIEW-GATE"', roadmap)
        self.assertIn("IDS-V0_1-STAGE043-P4", events)
        self.assertTrue(
            (
                status["phase"] == "IDS-STAGE043-P4"
                and status["next_gate"] == "IDS-STAGE043-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-REVIEW`"
                in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-REVIEW"
                and status["next_gate"] == "IDS-STAGE044-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P1"
                and status["next_gate"] == "IDS-STAGE044-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE044-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P2"
                and status["next_gate"] == "IDS-STAGE044-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE044-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P3"
                and status["next_gate"] == "IDS-STAGE044-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE044-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-P4"
                and status["next_gate"] == "IDS-STAGE044-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE044-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE044-REVIEW"
                and status["next_gate"] == "IDS-STAGE045-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-P1"
                and status["next_gate"] == "IDS-STAGE045-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE045-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-P2"
                and status["next_gate"] == "IDS-STAGE045-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE045-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-P3"
                and status["next_gate"] == "IDS-STAGE045-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE045-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-P4"
                and status["next_gate"] == "IDS-STAGE045-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE045-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE045-REVIEW"
                and status["next_gate"] == "IDS-STAGE046-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P1"
                and status["next_gate"] == "IDS-STAGE046-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P2"
                and status["next_gate"] == "IDS-STAGE046-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P3"
                and status["next_gate"] == "IDS-STAGE046-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P4"
                and status["next_gate"] == "IDS-STAGE046-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-REVIEW"
                and status["next_gate"] == "IDS-STAGE047-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-P1"
                and status["next_gate"] == "IDS-STAGE047-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-P2"
                and status["next_gate"] == "IDS-STAGE047-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-P3"
                and status["next_gate"] == "IDS-STAGE047-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-P4"
                and status["next_gate"] == "IDS-STAGE047-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-REVIEW"
                and status["next_gate"] == "IDS-STAGE048-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in handoff
            )
        )

    def test_cli_report_matches_in_process_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(self._report(), json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
