#!/usr/bin/env python3
"""Validate the STAGE-041 Phase 3 isolated lock scenario contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_scenarios.py"
PHASE2_CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_runtime.py"
CONTRACT = (
    PROJECT_ROOT
    / "docs/pursuing_goal/ids_v0_1/lock_registry/"
    "stage041_lock_registry_scenarios.json"
)
EVIDENCE = (
    PROJECT_ROOT
    / "docs/pursuing_goal/ids_v0_1/STAGE041_PHASE3_SCENARIO_VALIDATION.md"
)
BATCH = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1/BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE2_COMMIT = "22bd9263e38b697dfb681886a97c1b8ba0f4b5e9"
PHASE2_KMIDS_TREE = "c3e96185d5fe185fc9a8c27e8fa57a6279bc4e6d"
SCENARIOS = [
    "duplicate_click_idempotent_replay",
    "same_source_operation_exclusion_matrix",
    "renewal_current_cas_only",
    "expiry_plus_grace_takeover",
    "stale_cas_evidence_rejected",
    "isolated_worker_exception_lock_retained",
    "external_drive_offline_pause_boundary",
    "low_disk_pause_boundary",
    "external_api_budget_pause_boundary",
    "release_tombstone_reacquire",
    "protected_cleanup_denied",
]
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
    "automatic_resume_performed",
    "crash_recovery_runtime_performed",
    "persistent_lock_write_performed",
    "database_connection_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
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


class Stage041LockRegistryScenarioTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(
                CHECKER, "stage041_lock_registry_scenarios_test"
            )
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage041_phase3_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase3_artifacts_and_identity_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual("ids.stage041.lock_registry.phase3.scenarios.v1", contract["schema_version"])
        self.assertEqual("STAGE-041", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE041-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-041", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE041-P4-GATE", contract["next_gate"])

    def test_phase2_commit_tree_and_hash_bindings_are_current(self):
        contract = self._contract()
        self.assertEqual(
            {
                "commit": PHASE2_COMMIT,
                "km_ids_tree": PHASE2_KMIDS_TREE,
                "required_ancestor_of_head": True,
            },
            contract["phase2_commit_binding"],
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", PHASE2_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(0, ancestor.returncode)
        tree = subprocess.run(
            ["git", "rev-parse", f"{PHASE2_COMMIT}:KM_IDSystem"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(PHASE2_KMIDS_TREE, tree)
        checks = self._module().validate_scenario_contract(contract)
        self.assertTrue(checks["source_binding_exact"], checks)
        self.assertTrue(checks["phase2_commit_binding_current"], checks)
        self.assertTrue(checks["upstream_bindings_current"], checks)

    def test_scenario_catalog_and_boundaries_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))
        matrix = contract["operation_exclusion_contract"]
        self.assertEqual(
            [
                "FILE_PROCESSING",
                "ARCHIVE_EXTRACTION",
                "INDEX_BUILD",
                "INDEX_SWITCH",
                "REPORT_GENERATION",
            ],
            matrix["operation_families"],
        )
        self.assertEqual("SOURCE_PIPELINE", matrix["shared_lock_namespace"])
        self.assertEqual(5, matrix["expected_primary_acquisitions"])
        self.assertEqual(25, matrix["expected_conflict_decisions"])
        self.assertEqual(0, matrix["expected_operation_invocations"])
        self.assertFalse(contract["phase4_entry_gate"]["github_upload_allowed"])
        self.assertFalse(contract["phase4_entry_gate"]["whole_stage_review_allowed_in_phase3"])

    def test_contract_tampering_fails_closed_without_scenario_execution(self):
        module = self._module()
        tampered = copy.deepcopy(self._contract())
        tampered["unknown_root_field"] = True
        report = module.build_stage041_phase3_report(tampered)
        self.assertFalse(report["contract_valid"], report)
        self.assertFalse(report["scenario_runtime_performed"], report)
        self.assertFalse(report["scenario_validation_valid"], report)
        self.assertEqual("IDS-STAGE041-P3-GATE", report["next_gate"])
        self.assertEqual({}, report["scenario_results"])

    def test_duplicate_click_and_changed_input_are_idempotent_and_fail_closed(self):
        result = self._report()["scenario_results"]["duplicate_click_idempotent_replay"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(result["first_decision"], result["replay_decision"])
        self.assertEqual("IDEMPOTENCY_INPUT_CONFLICT", result["changed_input_result_code"])
        self.assertTrue(result["lock_state_unchanged_after_replay"])
        self.assertTrue(result["lock_state_unchanged_after_conflict"])
        self.assertEqual(1, result["fencing_counter"])

    def test_all_five_operation_families_share_source_exclusion(self):
        result = self._report()["scenario_results"]["same_source_operation_exclusion_matrix"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(5, result["primary_acquisition_count"])
        self.assertEqual(5, result["exact_replay_count"])
        self.assertEqual(25, result["resource_conflict_count"])
        self.assertEqual(0, result["operation_invocation_count"])
        self.assertEqual(0, result["partial_lock_retained_count"])
        self.assertEqual(0, result["retry_budget_consumed_count"])
        self.assertTrue(all(result["family_checks"].values()), result)

    def test_renewal_advances_versions_and_rejects_old_cas(self):
        result = self._report()["scenario_results"]["renewal_current_cas_only"]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["fence_preserved"])
        self.assertTrue(result["every_version_advanced_once"])
        self.assertEqual("STALE_FENCING_TOKEN", result["old_commit_result_code"])
        self.assertEqual("STALE_FENCING_TOKEN", result["old_renew_result_code"])
        self.assertEqual("STALE_FENCING_TOKEN", result["old_release_result_code"])

    def test_takeover_requires_expiry_plus_grace_and_invalidates_stale_holder(self):
        result = self._report()["scenario_results"]["expiry_plus_grace_takeover"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("LEASE_NOT_TAKEOVER_ELIGIBLE", result["early_result_code"])
        self.assertEqual("TAKEOVER_ACQUIRED", result["eligible_result_code"])
        self.assertTrue(result["fence_advanced_once"])
        self.assertTrue(result["every_version_advanced_once"])
        self.assertEqual("STALE_FENCING_TOKEN", result["stale_commit_result_code"])
        self.assertEqual("COMMIT_ALLOWED", result["successor_commit_action"])

    def test_stale_or_incomplete_cas_evidence_never_mutates_lock_state(self):
        result = self._report()["scenario_results"]["stale_cas_evidence_rejected"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("STALE_TAKEOVER_EVIDENCE", result["stale_result_code"])
        self.assertEqual("STALE_TAKEOVER_EVIDENCE", result["incomplete_result_code"])
        self.assertTrue(result["lock_state_unchanged"])
        self.assertTrue(result["fence_unchanged"])

    def test_actual_isolated_worker_exception_retains_lock_without_crash_recovery(self):
        result = self._report()["scenario_results"]["isolated_worker_exception_lock_retained"]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["actual_isolated_worker_exception_performed"])
        self.assertEqual("error:RuntimeError", result["safe_error_ref"])
        self.assertTrue(result["lock_retained_after_exception"])
        self.assertEqual("RESOURCE_CONFLICT_ACTIVE", result["contender_result_code"])
        self.assertFalse(result["process_termination_performed"])
        self.assertFalse(result["crash_recovery_runtime_performed"])

    def test_drive_disk_and_api_pause_boundaries_do_not_take_the_lock(self):
        results = self._report()["scenario_results"]
        drive = results["external_drive_offline_pause_boundary"]
        disk = results["low_disk_pause_boundary"]
        api = results["external_api_budget_pause_boundary"]
        for item in (drive, disk, api):
            self.assertEqual("PASS", item["status"])
            self.assertTrue(item["lock_state_unchanged"])
            self.assertFalse(item["retry_budget_consumed"])
        self.assertEqual("EXTERNAL_DRIVE_OFFLINE", drive["signal_code"])
        self.assertFalse(drive["physical_drive_removal_performed"])
        self.assertEqual("DISK_SPACE_INSUFFICIENT", disk["boundary_signal_code"])
        self.assertTrue(disk["actual_disk_observation_performed"])
        self.assertFalse(disk["disk_allocation_performed"])
        self.assertEqual("EXTERNAL_API_BUDGET_INSUFFICIENT", api["signal_code"])
        self.assertFalse(api["external_api_call_performed"])

    def test_release_tombstone_versions_precede_reacquisition(self):
        result = self._report()["scenario_results"]["release_tombstone_reacquire"]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["release_advanced_every_version"])
        self.assertTrue(result["reacquire_advanced_every_version"])
        self.assertTrue(result["fence_advanced_on_reacquire"])
        self.assertEqual(0, result["active_lock_count_after_release"])

    def test_protected_cleanup_is_denied_without_delete_surface(self):
        result = self._report()["scenario_results"]["protected_cleanup_denied"]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(5, len(result["artifact_results"]))
        self.assertEqual(0, result["delete_attempt_count"])
        self.assertEqual(0, result["deleted_ref_count"])
        for item in result["artifact_results"].values():
            self.assertTrue(item["git_tracked"])
            self.assertEqual("PROTECTED_ARTIFACT", item["result_code"])
            self.assertFalse(item["delete_allowed"])
            self.assertFalse(item["delete_attempted"])

    def test_report_has_exact_eleven_passes_and_no_forbidden_side_effects(self):
        report = self._report()
        self.assertTrue(report["contract_valid"], report)
        self.assertTrue(report["scenario_validation_valid"], report)
        self.assertEqual(11, report["scenario_count"])
        self.assertEqual(11, report["passed_scenario_count"])
        self.assertEqual(SCENARIOS, list(report["scenario_results"]))
        self.assertEqual("IDS-STAGE041-P4-GATE", report["next_gate"])
        self.assertTrue(report["actual_isolated_worker_exception_performed"])
        self.assertTrue(report["actual_project_disk_observation_performed"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])

    def test_phase2_remains_valid_and_phase3_route_is_preserved_in_history(self):
        phase2 = _load(PHASE2_CHECKER, "stage041_phase2_for_phase3_test")
        self.assertTrue(phase2.build_stage041_phase2_report()["phase2_slice_valid"])
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn('status: "stage041_phase3_completed"', batch)
        self.assertIn('      - "Phase 3"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE041-P4"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE041-P3"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE041-P4-GATE"', roadmap)
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
        )
        matching = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
            and json.loads(line).get("event_id")
            == "EVT-IDS-V0_1-STAGE041-P3-20260717-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertIn("github_upload_allowed=false", matching[0]["notes"])


if __name__ == "__main__":
    unittest.main()
