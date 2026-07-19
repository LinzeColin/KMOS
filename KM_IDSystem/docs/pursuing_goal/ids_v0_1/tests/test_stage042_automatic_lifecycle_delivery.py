#!/usr/bin/env python3
"""Validate STAGE-042 Phase 4 automatic-lifecycle closeout evidence."""

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
CHECKER = PROJECT_ROOT / "scripts/check_automatic_lifecycle_delivery.py"
CONTRACT = (
    BASE
    / "automatic_lifecycle/stage042_automatic_lifecycle_delivery_contract.json"
)
EVIDENCE = BASE / "STAGE042_PHASE4_CLOSEOUT.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "d8773ac03d10d877b0b9c439bfce91fe85f8fdfe"
PHASE3_KMIDS_TREE = "51a990dbb6563197d7a16d97c7cf2af201a7224e"
PRESSURE_SIGNALS = {
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
}
RESOURCE_RECOVERY_CASES = {
    "EXTERNAL_DRIVE_PAUSE_THEN_GUARDED_REQUEUE",
    "LOW_DISK_PAUSE_THEN_GUARDED_REQUEUE",
    "API_BUDGET_PAUSE_THEN_GUARDED_REQUEUE",
}
MANUAL_CASES = {
    "CHANGED_INPUT_IDEMPOTENCY_CONFLICT",
    "STALE_OR_INCOMPLETE_START_OBSERVATION",
    "RESOURCE_OWNER_OR_STABILITY_REVALIDATION_MISSING",
    "ACTIVE_CLAIM_OR_LOCK_PRESENT",
    "SHUTDOWN_GUARD_OR_TIMEOUT",
    "WORKER_PROCESS_CRASH",
    "PROTECTED_CLEANUP_REQUEST",
    "TERMINAL_HISTORY_REOPEN_REQUEST",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "PROCESS_EXIT_WITHOUT_PERSISTENT_LIFECYCLE_STATE",
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
    "automatic_lifecycle_runtime_performed",
    "automatic_start_performed",
    "automatic_pause_performed",
    "automatic_resume_performed",
    "automatic_shutdown_performed",
    "state_registry_write_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "production_lock_runtime_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "crash_recovery_runtime_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_decision_write_performed",
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


class Stage042AutomaticLifecycleDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage042_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage042_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_and_source_binding_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage042.automatic_lifecycle.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-042", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE042-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-042", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE042-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08",
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
                {"automatic_resume_performed": True}
            ),
        )
        for mutate in mutators:
            candidate = copy.deepcopy(self._contract())
            mutate(candidate)
            with self.subTest(candidate=candidate):
                report = module.build_stage042_phase4_delivery_report(candidate)
                self.assertFalse(report["contract_valid"], report)
                self.assertFalse(report["delivery_checks_performed"], report)
                self.assertEqual("IDS-STAGE042-P4-GATE", report["next_gate"])

    def test_job_graph_and_failure_retry_log_are_exact_and_reviewed(self):
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
        self.assertTrue(evidence["reviewed_stage040_delivery_valid"])

    def test_backpressure_trigger_proof_covers_all_signals(self):
        evidence = self._report()["state_retry_backpressure_evidence"]
        proof = evidence["backpressure_trigger_proof"]
        self.assertEqual(PRESSURE_SIGNALS, set(proof))
        self.assertTrue(all(proof.values()), proof)

    def test_phase3_scenarios_and_same_source_exclusion_are_replayed(self):
        report = self._report()
        scenarios = report["automatic_lifecycle_evidence"]
        self.assertEqual(12, scenarios["scenario_count"])
        self.assertEqual(12, scenarios["passed_scenario_count"])
        self.assertTrue(scenarios["phase2_lifecycle_decisions_valid"])
        self.assertTrue(scenarios["phase3_scenarios_valid"])
        exclusion = report["operation_exclusion_evidence"]
        self.assertEqual(4, exclusion["required_operation_family_count"])
        self.assertEqual(16, exclusion["selected_matrix_conflict_count"])
        self.assertEqual(0, exclusion["operation_invocation_count"])
        self.assertEqual(0, exclusion["retry_budget_consumed_count"])
        self.assertTrue(exclusion["all_family_checks_passed"])
        self.assertTrue(exclusion["reviewed_stage041_delivery_valid"])

    def test_automatic_recovery_eligibility_and_manual_cases_are_truthful(self):
        handling = self._report()["recovery_handling"]
        self.assertEqual(
            RESOURCE_RECOVERY_CASES,
            set(handling["automatic_recovery_eligible_cases"]),
        )
        self.assertEqual([], handling["successful_automatic_recovery_cases_observed"])
        self.assertEqual(MANUAL_CASES, set(handling["manual_action_required_cases"]))
        self.assertTrue(handling["owner_revalidation_required"])
        self.assertTrue(handling["resource_stability_required"])
        self.assertTrue(handling["no_active_claim_or_lock_required"])
        self.assertTrue(handling["fresh_admission_claim_lock_cycle_required"])
        self.assertFalse(handling["automatic_resume_performed"])
        self.assertEqual("STAGE-043", handling["process_crash_recovery_runtime_owner"])

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

    def test_safe_shutdown_recovery_rollback_and_limits_are_explicit(self):
        report = self._report()
        shutdown = report["safe_shutdown_and_recovery"]
        self.assertIn("STOP_NEW_LIFECYCLE_DECISIONS", shutdown["shutdown_steps"])
        self.assertIn(
            "WAIT_FOR_CHECKPOINT_OR_QUARANTINE", shutdown["shutdown_steps"]
        )
        self.assertTrue(shutdown["ordered_shutdown_candidate_verified"])
        self.assertTrue(shutdown["shutdown_timeout_fails_to_manual_review"])
        self.assertIn(
            "REOBSERVE_SOURCE_HASH_AND_RESOURCE_OWNERSHIP",
            shutdown["recovery_steps"],
        )
        self.assertFalse(shutdown["persistent_lifecycle_state_available_after_exit"])
        self.assertFalse(shutdown["process_termination_performed"])
        self.assertFalse(shutdown["automatic_process_recovery_performed"])
        self.assertIn("REVERT_PHASE4_FILES_ONLY", report["rollback_steps"])
        self.assertIn("NO_PROCESS_CRASH_RECOVERY", report["known_limits"])
        self.assertIn(
            "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS", report["known_limits"]
        )

    def test_truth_feedback_and_next_gate_stop_at_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual("PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED", report["result"])
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE042-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未观察到自动恢复成功", report["owner_feedback_zh"])
        self.assertIn("不是生产运行或生产就绪证明", report["owner_feedback_zh"])

    def test_governance_preserves_phase4_after_review_transition(self):
        for path in (BATCH, ROADMAP, EVENTS, HANDOFF, STATUS):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn('status: "stage042_phase4_completed_review_pending"', batch)
        self.assertIn('      - "Phase 4"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE042-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE042-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE042-REVIEW-GATE"', roadmap)
        self.assertIn("IDS-V0_1-STAGE042-P4", events)
        self.assertTrue(
            (
                status["phase"] == "IDS-STAGE042-P4"
                and status["next_gate"] == "IDS-STAGE042-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE042-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE042-REVIEW"
                and status["next_gate"] == "IDS-STAGE043-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P1"
                and status["next_gate"] == "IDS-STAGE043-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P2"
                and status["next_gate"] == "IDS-STAGE043-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P3"
                and status["next_gate"] == "IDS-STAGE043-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE043-P4"
                and status["next_gate"] == "IDS-STAGE043-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE043-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-REVIEW`" in handoff
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
