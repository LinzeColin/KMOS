import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
CHECKER = ROOT / "scripts" / "check_automatic_lifecycle_scenarios.py"
CONTRACT = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_scenarios.json"
)
EVIDENCE = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "STAGE042_PHASE3_SCENARIO_VALIDATION.md"
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

PHASE2_COMMIT = "32bd7d9775229e03cd9855edc4e5b737860b6af7"
PHASE2_KMIDS_TREE = "6ddb0c27a95afa1662a892e6bb3b5d890f72f963"
POLICY_VERSION = "ids.automatic_lifecycle_policy.v0_1.stage042.p2"
SCENARIOS = [
    "duplicate_request_exact_replay",
    "changed_payload_same_request_rejected",
    "stale_start_observation_blocked",
    "external_drive_pause_then_guarded_resume",
    "low_disk_pause_then_guarded_resume",
    "api_budget_pause_then_guarded_resume",
    "worker_exception_crash_recovery_deferred",
    "same_source_four_operation_lock_exclusion",
    "safe_shutdown_ordered_candidate",
    "shutdown_timeout_blocked",
    "protected_cleanup_denied",
    "eligible_cleanup_candidate_only",
]
PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
SELECTED_LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
EXPECTED_HASHES = {
    "stage042_phase2_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_runtime_contract.json",
        "f24283a0ab934082b0ceb48c6ca1597ca17d1c6cca6a939e2653fb00ede83e49",
    ),
    "stage042_phase2_checker": (
        "KM_IDSystem/scripts/check_automatic_lifecycle_runtime.py",
        "d8516b714e5cb71d9a43ddb70a080e8315e0fdc8e654e264cd5f9cb56ae7e2a9",
    ),
    "stage042_phase2_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage042_automatic_lifecycle_runtime.py",
        "60cfb3d89dfb3cf921c3043adfe0ff91718e7442124def950e9a099019d40049",
    ),
    "stage042_phase2_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md",
        "ea7ba6d0411e07e3fa0751ad76ae5d42be6a89a56b57ee10b8c33eadc8fb55b7",
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
        "e84852e59ae5d7b963df242324549729db1f72abadcef7cb4b2ca67211f9be3d",
    ),
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage042AutomaticLifecycleScenarioTests(unittest.TestCase):
    _checker_module = None
    _report_value = None

    def _checker(self):
        if self.__class__._checker_module is None:
            self.__class__._checker_module = _load(
                CHECKER, "stage042_scenario_checker_under_test"
            )
        return self.__class__._checker_module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._checker().build_stage042_phase3_report()
            )
        return copy.deepcopy(self.__class__._report_value)

    def test_phase3_artifacts_and_identity_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            self.assertTrue(path.is_file(), path)
        contract = self._contract()
        self.assertEqual(
            "ids.stage042.automatic_lifecycle.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-042", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE042-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-042", contract["acceptance_id"])
        self.assertEqual(POLICY_VERSION, contract["policy_version"])
        self.assertEqual("IDS-STAGE042-P4-GATE", contract["next_gate"])

    def test_source_phase2_commit_and_upstream_hashes_are_exact(self):
        checker = self._checker()
        contract = self._contract()
        self.assertTrue(checker.validate_scenario_contract(contract)["source_binding_exact"])
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
            actual = checker.sha256_file(REPO_ROOT / ref)
            self.assertTrue(
                checker.upstream_file_hash_current(name, digest, actual),
                {"name": name, "declared": digest, "actual": actual},
            )

    def test_scenario_catalog_and_safety_contracts_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))
        self.assertEqual(
            SELECTED_LOCK_FAMILIES,
            contract["operation_exclusion_contract"]["required_operation_families"],
        )
        self.assertEqual(
            PROTECTED_CLASSES,
            list(contract["protected_artifact_contract"]["protected_refs"]),
        )
        self.assertFalse(
            contract["lifecycle_safety_contract"]["actual_state_mutation_allowed"]
        )
        self.assertFalse(
            contract["worker_crash_boundary_contract"]["process_crash_claim_allowed"]
        )
        self.assertFalse(
            contract["protected_artifact_contract"]["delete_api_call_allowed"]
        )

    def test_contract_tampering_fails_closed_without_scenario_execution(self):
        checker = self._checker()
        contract = self._contract()
        tampered = copy.deepcopy(contract)
        tampered["scenario_catalog"].append("UNREVIEWED_SCENARIO")
        report = checker.build_stage042_phase3_report(tampered)
        self.assertFalse(report["contract_valid"])
        self.assertFalse(report["scenario_runtime_performed"])
        self.assertFalse(report["scenario_validation_valid"])
        self.assertEqual("IDS-STAGE042-P3-GATE", report["next_gate"])

    def test_duplicate_request_replays_one_candidate_without_mutation(self):
        result = self._report()["scenario_results"]["duplicate_request_exact_replay"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("AUTO_START_CANDIDATE", result["first_decision_action"])
        self.assertTrue(result["replay_equal"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["state_mutation_performed"])

    def test_changed_payload_under_same_request_id_is_rejected(self):
        result = self._report()["scenario_results"][
            "changed_payload_same_request_rejected"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(
            "REJECT_LIFECYCLE_REQUEST_CONFLICT", result["changed_decision_action"]
        )
        self.assertEqual("error:LIFECYCLE_REQUEST_CONFLICT", result["error_ref"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["state_mutation_performed"])

    def test_stale_start_observation_fails_closed(self):
        result = self._report()["scenario_results"]["stale_start_observation_blocked"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("error:START_GUARD_INCOMPLETE", result["error_ref"])
        self.assertEqual([], result["transition_candidates"])
        self.assertFalse(result["state_mutation_performed"])

    def test_external_drive_pause_and_resume_require_owner_and_stability(self):
        result = self._report()["scenario_results"][
            "external_drive_pause_then_guarded_resume"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("EXTERNAL_DRIVE_OFFLINE", result["pressure_signal"])
        self.assertEqual("AUTO_PAUSE_CANDIDATE", result["pause_decision_action"])
        self.assertEqual(
            "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION",
            result["owner_blocked_decision_action"],
        )
        self.assertEqual(
            "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION",
            result["stability_blocked_decision_action"],
        )
        self.assertEqual("AUTO_RESUME_CANDIDATE", result["resume_decision_action"])
        self.assertEqual([["PAUSED", "QUEUED"]], result["resume_transitions"])
        self.assertTrue(result["fresh_admission_and_lock_cycle_required"])
        self.assertFalse(result["physical_drive_removal_performed"])

    def test_low_disk_and_api_budget_pause_without_physical_or_api_action(self):
        report = self._report()["scenario_results"]
        disk = report["low_disk_pause_then_guarded_resume"]
        api = report["api_budget_pause_then_guarded_resume"]
        self.assertEqual("PASS", disk["status"])
        self.assertEqual("DISK_SPACE_INSUFFICIENT", disk["pressure_signal"])
        self.assertEqual("AUTO_PAUSE_CANDIDATE", disk["pause_decision_action"])
        self.assertGreater(disk["actual_disk_free_bytes"], 0)
        self.assertFalse(disk["disk_allocation_performed"])
        self.assertEqual("PASS", api["status"])
        self.assertEqual("EXTERNAL_API_BUDGET_INSUFFICIENT", api["pressure_signal"])
        self.assertEqual("AUTO_PAUSE_CANDIDATE", api["pause_decision_action"])
        self.assertFalse(api["external_api_call_performed"])

    def test_worker_exception_is_actual_but_crash_recovery_stays_stage043_owned(self):
        result = self._report()["scenario_results"][
            "worker_exception_crash_recovery_deferred"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["actual_isolated_worker_exception_performed"])
        self.assertEqual("error:RuntimeError", result["safe_error_ref"])
        self.assertTrue(result["lock_retained_after_exception"])
        self.assertEqual("STAGE-043", result["crash_recovery_owner"])
        self.assertEqual(
            "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION",
            result["resume_decision_action"],
        )
        self.assertFalse(result["process_termination_performed"])
        self.assertFalse(result["crash_recovery_runtime_performed"])

    def test_lock_evidence_covers_processing_extract_index_and_report(self):
        result = self._report()["scenario_results"][
            "same_source_four_operation_lock_exclusion"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(SELECTED_LOCK_FAMILIES, result["required_operation_families"])
        self.assertTrue(all(result["family_checks"].values()))
        self.assertEqual(25, result["source_full_conflict_count"])
        self.assertEqual(16, result["selected_matrix_conflict_count"])
        self.assertEqual(0, result["operation_invocation_count"])
        self.assertEqual(0, result["retry_budget_consumed_count"])

    def test_safe_shutdown_is_ordered_and_timeout_never_terminates_process(self):
        results = self._report()["scenario_results"]
        ordered = results["safe_shutdown_ordered_candidate"]
        timeout = results["shutdown_timeout_blocked"]
        self.assertEqual("PASS", ordered["status"])
        self.assertEqual("SAFE_SHUTDOWN_CANDIDATE", ordered["decision_action"])
        self.assertGreater(len(ordered["ordered_shutdown_steps"]), 0)
        self.assertFalse(ordered["process_termination_performed"])
        self.assertEqual("PASS", timeout["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", timeout["decision_action"])
        self.assertEqual("error:SHUTDOWN_GUARD_OR_TIMEOUT", timeout["error_ref"])
        self.assertEqual([], timeout["ordered_shutdown_steps"])
        self.assertFalse(timeout["process_termination_performed"])

    def test_protected_artifacts_never_enter_cleanup_execution(self):
        result = self._report()["scenario_results"]["protected_cleanup_denied"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(PROTECTED_CLASSES, list(result["artifact_results"]))
        for item in result["artifact_results"].values():
            self.assertTrue(item["git_tracked"])
            self.assertEqual("REQUIRE_MANUAL_REVIEW", item["decision_action"])
            self.assertFalse(item["delete_allowed"])
            self.assertFalse(item["delete_attempted"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_eligible_cleanup_remains_candidate_only(self):
        result = self._report()["scenario_results"][
            "eligible_cleanup_candidate_only"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(
            ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"],
            list(result["artifact_results"]),
        )
        for item in result["artifact_results"].values():
            self.assertEqual("CLEANUP_CANDIDATE_ONLY", item["decision_action"])
            self.assertTrue(item["cleanup_candidate_only"])
            self.assertFalse(item["delete_allowed"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_report_has_twelve_passes_and_no_forbidden_side_effects(self):
        report = self._report()
        self.assertTrue(report["contract_valid"])
        self.assertTrue(report["phase2_slice_valid"])
        self.assertTrue(report["stage041_lock_scenarios_valid"])
        self.assertTrue(report["scenario_validation_valid"])
        self.assertEqual(12, report["scenario_count"])
        self.assertEqual(12, report["passed_scenario_count"])
        self.assertEqual("IDS-STAGE042-P4-GATE", report["next_gate"])
        for key in (
            "automatic_lifecycle_runtime_performed",
            "state_registry_write_performed",
            "persistent_decision_write_performed",
            "process_termination_performed",
            "crash_recovery_runtime_performed",
            "cleanup_runtime_performed",
            "protected_ref_delete_performed",
            "database_connection_performed",
            "runtime_output_written",
            "production_runtime_activation_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            self.assertFalse(report[key], key)

    def test_governance_routes_only_to_separate_phase4(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn('status: "stage042_phase3_completed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE042-P3"', batch)
        self.assertIn('next_gate: "IDS-STAGE042-P4-GATE"', batch)
        self.assertIn('phase4_entry_authorized: true', batch)
        p3_start = roadmap.index('phase_id: "IDS-STAGE042-P3"')
        p4_start = roadmap.index('phase_id: "IDS-STAGE042-P4"', p3_start)
        p3_block = roadmap[p3_start:p4_start]
        self.assertIn('status: "passed_with_local_evidence"', p3_block)
        self.assertIn('entry_authorized: true', p3_block)
        p4_block = roadmap[p4_start : p4_start + 700]
        if 'status: "stage042_phase4_completed_review_pending"' in batch:
            self.assertIn('status: "passed_with_local_evidence"', p4_block)
            self.assertIn('next_gate_id: "IDS-STAGE042-REVIEW-GATE"', roadmap)
            self.assertTrue(
                (
                    ROOT
                    / "docs"
                    / "pursuing_goal"
                    / "ids_v0_1"
                    / "STAGE042_PHASE4_CLOSEOUT.md"
                ).is_file()
            )
        else:
            self.assertIn('status: "pending"', p4_block)
        self.assertIn('entry_authorized: true', p4_block)
        phase3_events = [
            event
            for event in events
            if event.get("event_id") == "EVT-IDS-V0_1-STAGE042-P3-20260718-001"
        ]
        self.assertEqual(1, len(phase3_events))
        self.assertFalse(phase3_events[0]["notes"].split("push_allowed=")[-1].startswith("true"))

    def test_cli_emits_exact_machine_report(self):
        checker = self._checker()
        completed = subprocess.run(
            ["python3", "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        expected = checker.build_stage042_phase3_report()
        observed = json.loads(completed.stdout)
        for report in (expected, observed):
            report["scenario_results"]["low_disk_pause_then_guarded_resume"].pop(
                "actual_disk_free_bytes"
            )
        self.assertEqual(expected, observed)


if __name__ == "__main__":
    unittest.main()
