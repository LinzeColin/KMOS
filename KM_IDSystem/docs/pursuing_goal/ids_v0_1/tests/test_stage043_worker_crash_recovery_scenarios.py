import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
CHECKER = ROOT / "scripts" / "check_worker_crash_recovery_scenarios.py"
CONTRACT = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "worker_crash_recovery"
    / "stage043_worker_crash_recovery_scenarios.json"
)
EVIDENCE = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "STAGE043_PHASE3_SCENARIO_VALIDATION.md"
)
BATCH = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "BATCH041_050_UPLOAD_LOCK.yaml"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"

PHASE2_COMMIT = "b1a8e4689eb9c3a3a469a9f8d77dff4683aa709c"
PHASE2_KMIDS_TREE = "6a3c6f683ab2e2e263b36463f0dc20d2ff277985"
POLICY_VERSION = "ids.worker_crash_recovery_policy.v0_1.stage043.p2"
SCENARIOS = [
    "duplicate_recovery_request_exact_replay",
    "changed_payload_same_request_rejected",
    "stale_crash_evidence_blocked",
    "isolated_worker_process_exit_checkpoint_candidate",
    "unfenced_worker_generation_blocked",
    "external_drive_offline_pause_candidate",
    "low_disk_pause_candidate",
    "api_budget_pause_candidate",
    "same_source_four_operation_lock_exclusion",
    "active_lock_or_claim_conflict_blocked",
    "terminal_history_immutable",
    "protected_cleanup_denied",
    "eligible_partial_output_quarantine_candidate_only",
]
PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
EXPECTED_HASHES = {
    "stage043_phase2_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_runtime_contract.json",
        "153a451f3e5aef4fef1faa8b4e3035f472ac50298d790731f19ba8701361ab38",
    ),
    "stage043_phase2_checker": (
        "KM_IDSystem/scripts/check_worker_crash_recovery_runtime.py",
        "eea785da3a1fd07ce9fe3a9c43e9a73660e945872b0b4b2ac8b456784ba515e4",
    ),
    "stage043_phase2_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage043_worker_crash_recovery_runtime.py",
        "4516f1d43e0cba261d942522c487003b4febae82d03ef25157b4ffe5841d5919",
    ),
    "stage043_phase2_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md",
        "8cb325a141b7549b569c50ed718193a337d686eaa083c65dbc0d038fefde9aab",
    ),
    "stage041_phase3_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_scenarios.json",
        "0866db20e070d1b93981f4b7b4180977f3221395310f1194ddcaa14556268c19",
    ),
    "stage041_phase3_checker": (
        "KM_IDSystem/scripts/check_lock_registry_scenarios.py",
        "fa46f374e4708c15b0d3e856e42e55f1c784dd926278ad86a8610878b59d606e",
    ),
    "stage041_phase3_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage041_lock_registry_scenarios.py",
        "6b235e04b64ba09278821abaf0bd5258e40f8b5f03f56c395dba68ab8177e088",
    ),
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage043WorkerCrashRecoveryScenarioTests(unittest.TestCase):
    _checker_module = None
    _report_value = None

    def _checker(self):
        if self.__class__._checker_module is None:
            self.__class__._checker_module = _load(
                CHECKER, "stage043_scenario_checker_under_test"
            )
        return self.__class__._checker_module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._checker().build_stage043_phase3_report()
            )
        return copy.deepcopy(self.__class__._report_value)

    def test_phase3_artifacts_and_identity_are_exact(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            self.assertTrue(path.is_file(), path)
        contract = self._contract()
        self.assertEqual(
            "ids.stage043.worker_crash_recovery.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-043", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE043-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-043", contract["acceptance_id"])
        self.assertEqual(POLICY_VERSION, contract["policy_version"])
        self.assertEqual("IDS-STAGE043-P4-GATE", contract["next_gate"])

    def test_source_phase2_commit_and_upstream_hashes_are_exact(self):
        checker = self._checker()
        contract = self._contract()
        checks = checker.validate_scenario_contract(contract)
        self.assertTrue(checks["source_binding_exact"])
        self.assertTrue(checks["phase2_commit_bound"])
        self.assertEqual(
            {
                "commit": PHASE2_COMMIT,
                "km_ids_tree": PHASE2_KMIDS_TREE,
                "required_ancestor_of_head": True,
            },
            contract["phase2_commit_binding"],
        )
        for name, (ref, digest) in EXPECTED_HASHES.items():
            self.assertEqual(
                {"ref": ref, "sha256": digest},
                contract["upstream_bindings"][name],
            )
            self.assertEqual(digest, checker.sha256_file(REPO_ROOT / ref))

    def test_scenario_catalog_and_safety_contracts_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))
        self.assertEqual(
            LOCK_FAMILIES,
            contract["operation_exclusion_contract"]["required_operation_families"],
        )
        self.assertEqual(
            PROTECTED_CLASSES,
            list(contract["protected_artifact_contract"]["protected_refs"]),
        )
        process = contract["isolated_process_exit_contract"]
        self.assertTrue(process["isolated_control_process_allowed"])
        self.assertEqual(73, process["expected_self_exit_code"])
        self.assertFalse(process["signal_or_kill_allowed"])
        self.assertFalse(process["worker_restart_allowed"])
        self.assertFalse(process["recovery_execution_allowed"])
        self.assertFalse(
            contract["recovery_safety_contract"]["actual_state_mutation_allowed"]
        )
        self.assertFalse(
            contract["protected_artifact_contract"]["delete_api_call_allowed"]
        )

    def test_contract_tampering_fails_closed_before_child_process_execution(self):
        checker = self._checker()
        tampered = self._contract()
        tampered["scenario_catalog"].append("UNREVIEWED_SCENARIO")
        report = checker.build_stage043_phase3_report(tampered)
        self.assertFalse(report["contract_valid"])
        self.assertFalse(report["scenario_runtime_performed"])
        self.assertFalse(report["isolated_control_process_started"])
        self.assertFalse(report["scenario_validation_valid"])
        self.assertEqual("IDS-STAGE043-P3-GATE", report["next_gate"])

    def test_duplicate_request_exact_replay_is_idempotent(self):
        result = self._report()["scenario_results"][
            "duplicate_recovery_request_exact_replay"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("CHECKPOINT_RESUME_CANDIDATE", result["decision_action"])
        self.assertTrue(result["replay_equal"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["state_mutation_performed"])

    def test_changed_payload_under_same_request_key_is_rejected(self):
        result = self._report()["scenario_results"][
            "changed_payload_same_request_rejected"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("RECOVERY_REQUEST_CONFLICT", result["reason_code"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["state_mutation_performed"])

    def test_stale_evidence_fails_closed(self):
        result = self._report()["scenario_results"]["stale_crash_evidence_blocked"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual(
            "CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN", result["reason_code"]
        )
        self.assertEqual([], result["transition_candidates"])
        self.assertFalse(result["state_mutation_performed"])

    def test_isolated_worker_process_exit_is_observed_without_recovery(self):
        result = self._report()["scenario_results"][
            "isolated_worker_process_exit_checkpoint_candidate"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["isolated_control_process_started"])
        self.assertTrue(result["isolated_worker_process_exit_observed"])
        self.assertEqual(73, result["observed_exit_code"])
        self.assertTrue(result["stdout_empty"])
        self.assertTrue(result["stderr_empty"])
        self.assertFalse(result["signal_or_kill_performed"])
        self.assertEqual("CHECKPOINT_RESUME_CANDIDATE", result["decision_action"])
        self.assertFalse(result["process_crash_recovery_performed"])
        self.assertFalse(result["worker_restart_performed"])
        self.assertFalse(result["state_mutation_performed"])

    def test_unfenced_generation_and_active_lock_conflict_fail_closed(self):
        report = self._report()["scenario_results"]
        unfenced = report["unfenced_worker_generation_blocked"]
        conflict = report["active_lock_or_claim_conflict_blocked"]
        for result in (unfenced, conflict):
            self.assertEqual("PASS", result["status"])
            self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
            self.assertEqual(
                "RECOVERY_OWNERSHIP_OR_STATE_EVIDENCE_INVALID",
                result["reason_code"],
            )
            self.assertFalse(result["state_mutation_performed"])

    def test_external_drive_pause_is_control_metadata_only(self):
        result = self._report()["scenario_results"][
            "external_drive_offline_pause_candidate"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("EXTERNAL_DRIVE_OFFLINE", result["pressure_signal"])
        self.assertEqual("RESOURCE_PAUSE_CANDIDATE", result["decision_action"])
        self.assertEqual(
            [["RUNNING", "RETRY_WAIT"], ["RETRY_WAIT", "PAUSED"]],
            result["transition_candidates"],
        )
        self.assertFalse(result["physical_drive_removal_performed"])
        self.assertFalse(result["automatic_resume_performed"])

    def test_low_disk_and_api_budget_pause_without_side_effects(self):
        report = self._report()["scenario_results"]
        disk = report["low_disk_pause_candidate"]
        api = report["api_budget_pause_candidate"]
        self.assertEqual("PASS", disk["status"])
        self.assertGreater(disk["actual_project_free_bytes"], 0)
        self.assertEqual(
            disk["actual_project_free_bytes"] + 1,
            disk["controlled_required_free_bytes"],
        )
        self.assertEqual("RESOURCE_PAUSE_CANDIDATE", disk["decision_action"])
        self.assertFalse(disk["disk_allocation_performed"])
        self.assertEqual("PASS", api["status"])
        self.assertEqual("RESOURCE_PAUSE_CANDIDATE", api["decision_action"])
        self.assertFalse(api["external_api_call_performed"])

    def test_lock_evidence_blocks_duplicate_process_extract_index_and_report(self):
        result = self._report()["scenario_results"][
            "same_source_four_operation_lock_exclusion"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(LOCK_FAMILIES, result["required_operation_families"])
        self.assertTrue(all(result["family_checks"].values()))
        self.assertEqual(25, result["source_full_conflict_count"])
        self.assertEqual(16, result["selected_matrix_conflict_count"])
        self.assertEqual(0, result["operation_invocation_count"])
        self.assertEqual(0, result["queue_record_created_count"])
        self.assertEqual(0, result["retry_budget_consumed_count"])

    def test_terminal_history_never_reopens(self):
        result = self._report()["scenario_results"]["terminal_history_immutable"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("TERMINAL_HISTORY_IMMUTABLE", result["reason_code"])
        self.assertEqual([], result["transition_candidates"])
        self.assertFalse(result["terminal_reopen_performed"])

    def test_protected_artifacts_never_enter_cleanup_execution(self):
        result = self._report()["scenario_results"]["protected_cleanup_denied"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(PROTECTED_CLASSES, list(result["artifact_results"]))
        for item in result["artifact_results"].values():
            self.assertTrue(item["git_tracked"])
            self.assertEqual("PROTECTED_ARTIFACT", item["result_code"])
            self.assertFalse(item["delete_allowed"])
            self.assertFalse(item["delete_attempted"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_partial_outputs_remain_quarantine_candidates_only(self):
        result = self._report()["scenario_results"][
            "eligible_partial_output_quarantine_candidate_only"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(
            ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"],
            list(result["artifact_results"]),
        )
        for item in result["artifact_results"].values():
            self.assertEqual("QUARANTINE_CANDIDATE_ONLY", item["decision_action"])
            self.assertTrue(item["quarantine_reference_only"])
            self.assertFalse(item["delete_allowed"])
            self.assertFalse(item["delete_attempted"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_report_has_thirteen_passes_and_no_forbidden_effects(self):
        report = self._report()
        self.assertTrue(report["contract_valid"])
        self.assertTrue(report["phase2_slice_valid"])
        self.assertTrue(report["stage041_lock_scenarios_valid"])
        self.assertTrue(report["scenario_validation_valid"])
        self.assertEqual(13, report["scenario_count"])
        self.assertEqual(13, report["passed_scenario_count"])
        self.assertEqual("IDS-STAGE043-P4-GATE", report["next_gate"])
        self.assertTrue(report["isolated_worker_process_exit_observed"])
        self.assertTrue(report["actual_project_disk_observation_performed"])
        for key in (
            "process_probe_performed",
            "signal_or_kill_performed",
            "process_crash_recovery_performed",
            "worker_restart_performed",
            "state_transition_performed",
            "checkpoint_resume_performed",
            "cleanup_runtime_performed",
            "protected_ref_delete_performed",
            "persistent_state_write_performed",
            "database_connection_performed",
            "runtime_output_written",
            "production_runtime_activation_performed",
            "whole_stage_review_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            self.assertFalse(report[key], key)

    def test_governance_preserves_phase3_and_routes_after_phase4_to_review(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn('status: "stage043_phase3_completed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE043-P3"', batch)
        self.assertIn('next_gate: "IDS-STAGE043-P4-GATE"', batch)
        self.assertIn('phase4_entry_authorized: true', batch)
        p3_start = roadmap.index('phase_id: "IDS-STAGE043-P3"')
        p4_start = roadmap.index('phase_id: "IDS-STAGE043-P4"', p3_start)
        p3_block = roadmap[p3_start:p4_start]
        self.assertIn('status: "passed_with_local_evidence"', p3_block)
        self.assertIn('entry_authorized: true', p3_block)
        p4_block = roadmap[p4_start : p4_start + 700]
        self.assertIn('status: "passed_with_local_evidence"', p4_block)
        self.assertIn('entry_authorized: true', p4_block)
        self.assertIn("IDS-V0_1-STAGE043-P4", handoff)
        self.assertIn("IDS-V0_1-STAGE043-REVIEW", handoff)
        self.assertIn("NO_STAGE_REVIEW_THIS_RUN", handoff)
        self.assertIn('current_phase_id: "IDS-STAGE043-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE043-REVIEW-GATE"', roadmap)
        phase3_events = [
            event
            for event in events
            if event.get("event_id") == "EVT-IDS-V0_1-STAGE043-P3-20260718-001"
        ]
        self.assertEqual(1, len(phase3_events))
        self.assertIn("push_allowed=false", phase3_events[0]["notes"])

    def test_cli_emits_the_exact_machine_report(self):
        checker = self._checker()
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        expected = checker.build_stage043_phase3_report()
        observed = json.loads(completed.stdout)
        for report in (expected, observed):
            report["scenario_results"]["low_disk_pause_candidate"].pop(
                "actual_project_free_bytes"
            )
            report["scenario_results"]["low_disk_pause_candidate"].pop(
                "controlled_required_free_bytes"
            )
        self.assertEqual(expected, observed)


if __name__ == "__main__":
    unittest.main()
