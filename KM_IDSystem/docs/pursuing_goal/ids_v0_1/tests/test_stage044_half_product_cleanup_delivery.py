#!/usr/bin/env python3
"""Validate STAGE-044 Phase 4 half-product-cleanup closeout evidence."""

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
CHECKER = PROJECT_ROOT / "scripts/check_half_product_cleanup_delivery.py"
CONTRACT = (
    BASE
    / "half_product_cleanup/stage044_half_product_cleanup_delivery_contract.json"
)
EVIDENCE = BASE / "STAGE044_PHASE4_CLOSEOUT.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "fd1d652bbe2e9edcbf4e7c9619b55db1873b365e"
PHASE3_KMIDS_TREE = "809a7f6e32ecf57f10803f81abed964fa7cff160"

PRESSURE_SIGNALS = {
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
}
OPERATION_FAMILIES = {
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
}
ELIGIBLE_CLASSES = {
    "TEMP_STAGING_OUTPUT",
    "INCOMPLETE_DERIVATIVE_OUTPUT",
}
PROTECTED_CLASSES = {
    "ORIGINAL_RAW_DATA",
    "SOURCE_FILE",
    "SOURCE_DATABASE",
    "RUNTIME_DATABASE",
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "AUDIT_LOG",
    "REPORT_SNAPSHOT",
    "DELIVERED_REPORT",
    "ACTIVE_INDEX",
    "VALIDATED_RETRY_CHECKPOINT",
    "OWNER_HELD_ARTIFACT",
    "SUCCEEDED_JOB_OUTPUT",
}
UPSTREAM_RECOVERY_CANDIDATES = {
    "CHECKPOINT_RESUME_CANDIDATE_AFTER_ALL_GATES",
    "STAGE039_RETRY_CANDIDATE_AFTER_ALL_GATES",
    "SAFE_FAILURE_CANDIDATE_AFTER_ALL_GATES",
}
CONDITIONAL_CLEANUP_CANDIDATES = {
    "TEMP_STAGING_OUTPUT_AFTER_ALL_GATES",
    "INCOMPLETE_DERIVATIVE_OUTPUT_AFTER_ALL_GATES",
}
MANUAL_CASES = {
    "PROTECTED_ARTIFACT_OR_ORIGINAL_SOURCE",
    "MISSING_OR_INVALID_MANIFEST_OR_PROVENANCE",
    "ARTIFACT_NOT_REBUILDABLE",
    "RETENTION_OR_HOLD_NOT_CLEARED",
    "DURABLE_REFERENCE_PRESENT_OR_UNKNOWN",
    "ACTIVE_OR_UNKNOWN_WRITER",
    "WRITER_QUIESCENCE_NOT_PROVEN",
    "LSTAT_IDENTITY_STALE_OR_CHANGED",
    "EXCLUSIVE_NAMESPACE_LOCK_NOT_HELD",
    "SAME_SOURCE_OPERATION_CONFLICT",
    "RESOURCE_PRESSURE_OR_OBSERVATION_STALE",
    "IDEMPOTENCY_CONFLICT",
    "UNCALIBRATED_POLICY",
    "NO_PERSISTENT_CLEANUP_OR_AUDIT_STATE",
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
    "automatic_cleanup_performed",
    "successful_cleanup_observed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "cleanup_runtime_performed",
    "cleanup_scan_performed",
    "filesystem_probe_performed",
    "filesystem_traversal_performed",
    "writer_quiescence_probe_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "dirfd_open_performed",
    "openat_called",
    "unlinkat_called",
    "move_or_overwrite_performed",
    "delete_operation_started",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
    "audit_write_performed",
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
    "stage045_entry_allowed",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage044HalfProductCleanupDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage044_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage044_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_and_source_binding_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage044.half_product_cleanup.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-044", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE044-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-044", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE044-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53",
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
            lambda value: value[
                "automatic_recovery_and_cleanup_handling"
            ].update({"automatic_cleanup_eligible_cases": ["FAKE"]}),
            lambda value: value["cleanup_delivery_contract"][
                "cleanup_eligible_classes"
            ].append("FACT_SOURCE"),
            lambda value: value["review_gate"].update(
                {"phase4_may_mark_stage_reviewed": True}
            ),
            lambda value: value["truth_flags"].update(
                {"delete_operation_started": True}
            ),
        )
        for mutate in mutators:
            candidate = copy.deepcopy(self._contract())
            mutate(candidate)
            with self.subTest(candidate=candidate):
                report = module.build_stage044_phase4_delivery_report(candidate)
                self.assertFalse(report["contract_valid"], report)
                self.assertFalse(report["delivery_checks_performed"], report)
                self.assertEqual("IDS-STAGE044-P4-GATE", report["next_gate"])

    def test_job_graph_retry_log_and_backpressure_proof_are_exact(self):
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

    def test_phase3_scenarios_allowlist_and_protected_classes_are_exact(self):
        report = self._report()
        phase3 = report["phase3_cleanup_evidence"]
        self.assertEqual(14, phase3["scenario_count"])
        self.assertEqual(14, phase3["passed_scenario_count"])
        self.assertTrue(phase3["phase2_slice_valid"])
        self.assertTrue(phase3["phase3_scenarios_valid"])
        self.assertEqual(73, phase3["isolated_process_exit_code"])
        self.assertEqual(0, phase3["delete_attempt_count"])
        self.assertEqual(0, phase3["deleted_ref_count"])
        cleanup = report["cleanup_allowlist"]
        self.assertEqual(ELIGIBLE_CLASSES, set(cleanup["cleanup_eligible_classes"]))
        self.assertEqual(PROTECTED_CLASSES, set(cleanup["protected_artifact_classes"]))
        self.assertEqual(14, cleanup["protected_ref_count"])
        self.assertTrue(all(cleanup["protected_ref_checks"].values()), cleanup)
        self.assertTrue(all(cleanup["candidate_checks"].values()), cleanup)
        self.assertFalse(cleanup["delete_execution_allowed"])
        self.assertFalse(cleanup["cleanup_runtime_performed"])

    def test_automatic_recovery_cleanup_and_manual_cases_are_truthful(self):
        handling = self._report()["automatic_recovery_and_cleanup_handling"]
        self.assertEqual(
            UPSTREAM_RECOVERY_CANDIDATES,
            set(handling["upstream_conditional_recovery_candidates"]),
        )
        self.assertEqual(
            CONDITIONAL_CLEANUP_CANDIDATES,
            set(handling["conditional_cleanup_candidates"]),
        )
        self.assertEqual([], handling["automatic_recovery_eligible_cases"])
        self.assertEqual([], handling["automatic_cleanup_eligible_cases"])
        self.assertEqual(
            [], handling["successful_automatic_recovery_cases_observed"]
        )
        self.assertEqual([], handling["successful_cleanup_cases_observed"])
        self.assertEqual(MANUAL_CASES, set(handling["manual_action_required_cases"]))
        self.assertFalse(handling["persistent_cleanup_state_available"])
        self.assertFalse(handling["automatic_recovery_performed"])
        self.assertFalse(handling["automatic_cleanup_performed"])

    def test_same_source_exclusion_and_resource_proof_remain_fail_closed(self):
        report = self._report()
        exclusion = report["operation_exclusion_evidence"]
        self.assertEqual(OPERATION_FAMILIES, set(exclusion["operation_families"]))
        self.assertEqual(25, exclusion["source_full_conflict_count"])
        self.assertEqual(16, exclusion["selected_matrix_conflict_count"])
        self.assertEqual(0, exclusion["operation_invocation_count"])
        self.assertEqual(0, exclusion["queue_record_created_count"])
        self.assertEqual(0, exclusion["retry_budget_consumed_count"])
        self.assertTrue(exclusion["all_family_checks_passed"])
        resources = report["resource_pressure_evidence"]
        self.assertTrue(all(resources.values()), resources)

    def test_safe_shutdown_recovery_rollback_and_limits_are_explicit(self):
        report = self._report()
        shutdown = report["safe_shutdown_and_recovery"]
        self.assertIn("STOP_NEW_CLEANUP_EVALUATIONS", shutdown["shutdown_steps"])
        self.assertIn(
            "PRESERVE_SOURCE_MANIFEST_EVIDENCE_REPORT_AND_AUDIT",
            shutdown["shutdown_steps"],
        )
        self.assertTrue(shutdown["reviewed_transport_orderly_shutdown_proved"])
        self.assertTrue(shutdown["reviewed_transport_queue_closed"])
        self.assertTrue(shutdown["reviewed_transport_resource_locks_released"])
        self.assertFalse(shutdown["persistent_cleanup_state_available_after_exit"])
        self.assertFalse(shutdown["cleanup_in_progress_observed"])
        self.assertFalse(shutdown["delete_operation_in_progress"])
        self.assertIn(
            "REVALIDATE_MANIFEST_HOLDS_REFERENCES_RETENTION_AND_IDENTITY",
            shutdown["recovery_steps"],
        )
        self.assertIn("REVERT_PHASE4_FILES_ONLY", report["rollback_steps"])
        self.assertIn("NO_PRODUCTION_CLEANUP_RUNTIME", report["known_limits"])
        self.assertIn(
            "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS", report["known_limits"]
        )

    def test_truth_feedback_and_next_gate_stop_at_separate_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_CLEANUP_CLOSEOUT_DELETE_DISABLED", report["result"]
        )
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE044-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("没有自动恢复或自动清理资格", report["owner_feedback_zh"])
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
        self.assertIn('status: "stage044_phase4_completed_review_pending"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE044-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE044-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE044-REVIEW-GATE"', roadmap)
        self.assertIn("IDS-V0_1-STAGE044-P4", events)
        p4_current = (
            status["phase"] == "IDS-STAGE044-P4"
            and status["next_gate"] == "IDS-STAGE044-REVIEW-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE044-P4`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`" in handoff
        )
        review_current = (
            status["phase"] == "IDS-STAGE044-REVIEW"
            and status["next_gate"] == "IDS-STAGE045-P1-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE045-P1`" in handoff
        )
        stage045_phase1_current = (
            status["phase"] == "IDS-STAGE045-P1"
            and status["next_gate"] == "IDS-STAGE045-P2-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE045-P1`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE045-P2`" in handoff
        )
        stage045_phase2_current = (
            status["phase"] == "IDS-STAGE045-P2"
            and status["next_gate"] == "IDS-STAGE045-P3-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE045-P2`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE045-P3`" in handoff
        )
        stage045_phase3_current = (
            status["phase"] == "IDS-STAGE045-P3"
            and status["next_gate"] == "IDS-STAGE045-P4-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE045-P3`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE045-P4`" in handoff
        )
        stage045_phase4_current = (
            status["phase"] == "IDS-STAGE045-P4"
            and status["next_gate"] == "IDS-STAGE045-REVIEW-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE045-P4`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE045-REVIEW`" in handoff
        )
        stage045_review_current = (
            status["phase"] == "IDS-STAGE045-REVIEW"
            and status["next_gate"] == "IDS-STAGE046-P1-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE046-P1`" in handoff
        )
        stage046_phase1_current = (
            status["phase"] == "IDS-STAGE046-P1"
            and status["next_gate"] == "IDS-STAGE046-P2-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE046-P1`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE046-P2`" in handoff
        )
        stage046_phase2_current = (
            status["phase"] == "IDS-STAGE046-P2"
            and status["next_gate"] == "IDS-STAGE046-P3-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE046-P2`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE046-P3`" in handoff
        )
        stage046_phase3_current = (
            status["phase"] == "IDS-STAGE046-P3"
            and status["next_gate"] == "IDS-STAGE046-P4-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE046-P3`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE046-P4`" in handoff
        )
        stage046_phase4_current = (
            status["phase"] == "IDS-STAGE046-P4"
            and status["next_gate"] == "IDS-STAGE046-REVIEW-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE046-P4`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE046-REVIEW`" in handoff
        )
        stage046_review_current = (
            status["phase"] == "IDS-STAGE046-REVIEW"
            and status["next_gate"] == "IDS-STAGE047-P1-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE046-REVIEW`"
            in handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-P1`" in handoff
        )
        stage047_phase1_current = (
            status["phase"] == "IDS-STAGE047-P1"
            and status["next_gate"] == "IDS-STAGE047-P2-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE047-P1`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-P2`" in handoff
        )
        stage047_phase2_current = (
            status["phase"] == "IDS-STAGE047-P2"
            and status["next_gate"] == "IDS-STAGE047-P3-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE047-P2`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in handoff
        )
        stage047_phase3_current = (
            status["phase"] == "IDS-STAGE047-P3"
            and status["next_gate"] == "IDS-STAGE047-P4-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE047-P3`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in handoff
        )
        stage047_phase4_current = (
            status["phase"] == "IDS-STAGE047-P4"
            and status["next_gate"] == "IDS-STAGE047-REVIEW-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE047-P4`" in handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-REVIEW`" in handoff
        )
        stage047_review_current = (
            status["phase"] == "IDS-STAGE047-REVIEW"
            and status["next_gate"] == "IDS-STAGE048-P1-GATE"
            and "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
            in handoff
            and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in handoff
        )
        self.assertTrue(
            p4_current
            or review_current
            or stage045_phase1_current
            or stage045_phase2_current
            or stage045_phase3_current
            or stage045_phase4_current
            or stage045_review_current
            or stage046_phase1_current
            or stage046_phase2_current
            or stage046_phase3_current
            or stage046_phase4_current
            or stage046_review_current
            or stage047_phase1_current
            or stage047_phase2_current
            or stage047_phase3_current
            or stage047_phase4_current
            or stage047_review_current
        )

    def test_missing_or_malformed_contract_returns_structured_failure(self):
        module = self._module()
        missing = module.build_stage044_phase4_delivery_report(
            contract_path=BASE / "missing-stage044-p4.json"
        )
        self.assertFalse(missing["contract_valid"])
        self.assertFalse(missing["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE044-P4-GATE", missing["next_gate"])
        malformed = module.build_stage044_phase4_delivery_report([])
        self.assertFalse(malformed["contract_valid"])
        self.assertFalse(malformed["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE044-P4-GATE", malformed["next_gate"])

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
