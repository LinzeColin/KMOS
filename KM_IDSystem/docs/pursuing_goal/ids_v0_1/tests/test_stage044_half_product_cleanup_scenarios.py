import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
CHECKER = ROOT / "scripts" / "check_half_product_cleanup_scenarios.py"
CONTRACT = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "half_product_cleanup"
    / "stage044_half_product_cleanup_scenarios.json"
)
EVIDENCE = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "STAGE044_PHASE3_SCENARIO_VALIDATION.md"
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

PHASE2_COMMIT = "4867bb14f1ff87231d4dd6f4ebae7251d60be585"
PHASE2_KMIDS_TREE = "790114d3ce9e3e416d70c64da467ff148ceb848c"
POLICY_VERSION = "ids.half_product_cleanup_policy.v0_1.stage044.p2"
SCENARIOS = [
    "duplicate_cleanup_request_exact_replay",
    "changed_payload_same_request_rejected",
    "isolated_worker_exit_partial_output_candidate_only",
    "external_drive_offline_blocked",
    "low_disk_blocked",
    "api_budget_blocked",
    "active_writer_blocked",
    "unknown_writer_or_quiescence_blocked",
    "stale_lstat_identity_blocked",
    "concurrent_same_file_lock_conflict_blocked",
    "same_source_four_operation_lock_exclusion",
    "core_protected_artifacts_denied",
    "all_protected_classes_denied",
    "eligible_candidate_review_only_delete_disabled",
]
CORE_PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
PROTECTED_CLASSES = [
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
]
LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
RESOURCE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
EXPECTED_HASHES = {
    "stage044_phase2_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
        "stage044_half_product_cleanup_runtime_contract.json",
        "b0cf212df7ceef136f6ae0ec0adf89c1fefe9b1fd2159346b1c9d1b9444b3adb",
    ),
    "stage044_phase2_checker": (
        "KM_IDSystem/scripts/check_half_product_cleanup_runtime.py",
        "4dac82daf97f19ef3a385d57f4a7b39709c0b8b87724ea0346ec3378778715e9",
    ),
    "stage044_phase2_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage044_half_product_cleanup_runtime.py",
        "7b6e7578ae58db7c74574d31feb0553cef5bc38a41cb8fdb00fd6e20b4055697",
    ),
    "stage044_phase2_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE044_PHASE2_HALF_PRODUCT_CLEANUP_SLICE.md",
        "0657726f1f3baf4b215021b86cdf8f444a3044660ce4842dc0e0ee4bd74116a7",
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
    "stage043_phase3_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_scenarios.json",
        "4dcdcc6cc179c27c824f071fd4b4302ddadcbb54b718998d5629c81d195ab371",
    ),
    "stage043_phase3_checker": (
        "KM_IDSystem/scripts/check_worker_crash_recovery_scenarios.py",
        "cefb69b019b8c47bfb5b846d89b0d9d7c8113ecf632980161f231401de114d0d",
    ),
    "stage043_phase3_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage043_worker_crash_recovery_scenarios.py",
        "8a020baa2d40ff54e406a3dea9b9f4d6c4775b3f37ed1232e660e0989bb97da7",
    ),
    "stage043_phase3_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE043_PHASE3_SCENARIO_VALIDATION.md",
        "10543e29ac87feb207ac14e656836d4a416470a36bafa3fd6f279960313b35bd",
    ),
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage044HalfProductCleanupScenarioTests(unittest.TestCase):
    _checker_module = None
    _report_value = None

    def _checker(self):
        if self.__class__._checker_module is None:
            self.__class__._checker_module = _load(
                CHECKER, "stage044_cleanup_scenario_checker_under_test"
            )
        return self.__class__._checker_module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._checker().build_stage044_phase3_report()
            )
        return copy.deepcopy(self.__class__._report_value)

    def test_phase3_artifacts_and_identity_are_exact(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            self.assertTrue(path.is_file(), path)
        contract = self._contract()
        self.assertEqual(
            "ids.stage044.half_product_cleanup.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-044", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE044-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-044", contract["acceptance_id"])
        self.assertEqual(POLICY_VERSION, contract["policy_version"])
        self.assertEqual("IDS-STAGE044-P4-GATE", contract["next_gate"])

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
            actual_hash = checker.sha256_file(REPO_ROOT / ref)
            allowed_hashes = checker.FORWARD_COMPATIBLE_UPSTREAM_HASHES.get(
                name, {digest}
            )
            self.assertIn(actual_hash, allowed_hashes)

    def test_scenario_catalog_and_safety_contracts_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))
        self.assertEqual(
            RESOURCE_SIGNALS,
            contract["resource_pressure_contract"]["signals"],
        )
        self.assertEqual(
            LOCK_FAMILIES,
            contract["operation_exclusion_contract"]["required_operation_families"],
        )
        self.assertEqual(
            CORE_PROTECTED_CLASSES,
            contract["protected_artifact_contract"]["required_core_classes"],
        )
        self.assertEqual(
            PROTECTED_CLASSES,
            contract["protected_artifact_contract"]["all_protected_classes"],
        )
        self.assertTrue(
            contract["worker_crash_evidence_contract"]["reference_only_reuse"]
        )
        self.assertFalse(
            contract["worker_crash_evidence_contract"]["production_worker_crash_allowed"]
        )
        self.assertFalse(
            contract["protected_artifact_contract"]["delete_api_call_allowed"]
        )

    def test_contract_tampering_fails_closed_before_upstream_replay(self):
        checker = self._checker()
        tampered = self._contract()
        tampered["scenario_catalog"].append("UNREVIEWED_SCENARIO")
        report = checker.build_stage044_phase3_report(tampered)
        self.assertFalse(report["contract_valid"])
        self.assertFalse(report["scenario_runtime_performed"])
        self.assertFalse(report["phase2_slice_reexecuted"])
        self.assertFalse(report["stage041_lock_scenarios_replayed"])
        self.assertFalse(report["stage043_crash_scenarios_replayed"])
        self.assertFalse(report["isolated_control_process_started"])
        self.assertEqual("IDS-STAGE044-P3-GATE", report["next_gate"])

    def test_duplicate_request_exact_replay_is_idempotent(self):
        result = self._report()["scenario_results"][
            "duplicate_cleanup_request_exact_replay"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED", result["decision_action"]
        )
        self.assertTrue(result["replay_equal"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["delete_allowed"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_changed_payload_under_same_request_key_is_rejected(self):
        result = self._report()["scenario_results"][
            "changed_payload_same_request_rejected"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("CLEANUP_REQUEST_CONFLICT", result["reason_code"])
        self.assertEqual(1, result["ledger_record_count"])
        self.assertFalse(result["delete_allowed"])

    def test_isolated_worker_exit_only_forms_delete_disabled_candidate(self):
        result = self._report()["scenario_results"][
            "isolated_worker_exit_partial_output_candidate_only"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["upstream_isolated_worker_exit_observed"])
        self.assertEqual(73, result["upstream_exit_code"])
        self.assertEqual(
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED", result["decision_action"]
        )
        self.assertFalse(result["process_crash_recovery_performed"])
        self.assertFalse(result["worker_restart_performed"])
        self.assertFalse(result["delete_allowed"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_resource_pressure_blocks_without_physical_effects(self):
        results = self._report()["scenario_results"]
        names = [
            "external_drive_offline_blocked",
            "low_disk_blocked",
            "api_budget_blocked",
        ]
        for name, signal in zip(names, RESOURCE_SIGNALS):
            with self.subTest(name=name):
                item = results[name]
                self.assertEqual("PASS", item["status"])
                self.assertEqual(signal, item["pressure_signal"])
                self.assertEqual("CLEANUP_BLOCKED_RESOURCE", item["decision_action"])
                self.assertEqual("RESOURCE_GATE_BLOCKED", item["reason_code"])
                self.assertFalse(item["delete_allowed"])
        self.assertFalse(results[names[0]]["physical_drive_removal_performed"])
        self.assertFalse(results[names[1]]["disk_allocation_performed"])
        self.assertFalse(results[names[2]]["external_api_call_performed"])

    def test_active_and_unknown_writer_evidence_fail_closed(self):
        results = self._report()["scenario_results"]
        active = results["active_writer_blocked"]
        unknown = results["unknown_writer_or_quiescence_blocked"]
        self.assertEqual("PASS", active["status"])
        self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", active["decision_action"])
        self.assertEqual("JOB_ACTIVE_SUCCEEDED_OR_UNKNOWN", active["reason_code"])
        self.assertEqual("PASS", unknown["status"])
        self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", unknown["decision_action"])
        self.assertEqual(
            "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN",
            unknown["reason_code"],
        )
        self.assertFalse(active["delete_allowed"])
        self.assertFalse(unknown["delete_allowed"])

    def test_stale_identity_fails_closed_without_filesystem_probe(self):
        result = self._report()["scenario_results"][
            "stale_lstat_identity_blocked"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", result["decision_action"])
        self.assertEqual(
            "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN",
            result["reason_code"],
        )
        self.assertFalse(result["filesystem_probe_performed"])
        self.assertFalse(result["delete_allowed"])

    def test_concurrent_same_file_lock_conflict_blocks_cleanup(self):
        result = self._report()["scenario_results"][
            "concurrent_same_file_lock_conflict_blocked"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", result["decision_action"])
        self.assertEqual(
            "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN",
            result["reason_code"],
        )
        self.assertEqual(0, result["operation_invocation_count"])
        self.assertFalse(result["production_lock_runtime_performed"])
        self.assertFalse(result["delete_allowed"])

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

    def test_core_fact_and_evidence_artifacts_never_delete(self):
        result = self._report()["scenario_results"][
            "core_protected_artifacts_denied"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(CORE_PROTECTED_CLASSES, list(result["artifact_results"]))
        for item in result["artifact_results"].values():
            self.assertEqual("CLEANUP_BLOCKED_PROTECTED", item["decision_action"])
            self.assertFalse(item["delete_allowed"])
            self.assertFalse(item["delete_attempted"])
        self.assertFalse(result["cleanup_runtime_performed"])

    def test_all_fourteen_protected_classes_fail_closed(self):
        result = self._report()["scenario_results"][
            "all_protected_classes_denied"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(PROTECTED_CLASSES, list(result["artifact_results"]))
        self.assertEqual(0, result["delete_attempt_count"])
        self.assertEqual(0, result["deleted_ref_count"])
        self.assertTrue(
            all(
                item["decision_action"] == "CLEANUP_BLOCKED_PROTECTED"
                and item["delete_allowed"] is False
                for item in result["artifact_results"].values()
            )
        )

    def test_eligible_candidate_remains_review_only_and_delete_disabled(self):
        result = self._report()["scenario_results"][
            "eligible_candidate_review_only_delete_disabled"
        ]
        self.assertEqual("PASS", result["status"])
        self.assertEqual(
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED", result["decision_action"]
        )
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["delete_allowed"])
        self.assertFalse(result["filesystem_traversal_performed"])
        self.assertFalse(result["production_lock_acquired"])
        self.assertFalse(result["audit_write_performed"])

    def test_report_has_fourteen_passes_and_no_forbidden_effects(self):
        report = self._report()
        self.assertTrue(report["contract_valid"])
        self.assertTrue(report["phase2_slice_valid"])
        self.assertTrue(report["stage041_lock_scenarios_valid"])
        self.assertTrue(report["stage043_crash_scenarios_valid"])
        self.assertTrue(report["scenario_validation_valid"])
        self.assertEqual(14, report["scenario_count"])
        self.assertEqual(14, report["passed_scenario_count"])
        self.assertEqual("IDS-STAGE044-P4-GATE", report["next_gate"])
        self.assertEqual(
            "PASS_ISOLATED_CLEANUP_SCENARIOS_DELETE_DISABLED", report["result"]
        )
        for name in self._checker().FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])

    def test_scenario_results_do_not_expose_raw_or_absolute_paths(self):
        text = json.dumps(
            self._report()["scenario_results"], ensure_ascii=False, sort_keys=True
        )
        self.assertNotIn("must-not-be-returned", text)
        self.assertNotIn("/Users/", text)
        self.assertNotIn("IDS_MetaData", text)

    def test_cli_emits_machine_readable_pass_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertTrue(report["scenario_validation_valid"])
        self.assertEqual(14, report["passed_scenario_count"])
        self.assertEqual("IDS-STAGE044-P4-GATE", report["next_gate"])

    def test_governance_routes_forward_without_upload_or_stage045(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        p3_current = all(
            marker in batch
            for marker in (
                'current_task_id: "IDS-V0_1-STAGE044-P3"',
                'next_allowed_task_id: "IDS-V0_1-STAGE044-P4"',
                'next_gate: "IDS-STAGE044-P4-GATE"',
            )
        ) and all(
            marker in roadmap
            for marker in (
                'current_phase_id: "IDS-STAGE044-P3"',
                'current_task_id: "IDS-V0_1-STAGE044-P3"',
                'next_gate_id: "IDS-STAGE044-P4-GATE"',
            )
        )
        p4_current = all(
            marker in batch
            for marker in (
                'current_task_id: "IDS-V0_1-STAGE044-P4"',
                'next_allowed_task_id: "IDS-V0_1-STAGE044-REVIEW"',
                'next_gate: "IDS-STAGE044-REVIEW-GATE"',
            )
        ) and all(
            marker in roadmap
            for marker in (
                'current_phase_id: "IDS-STAGE044-P4"',
                'current_task_id: "IDS-V0_1-STAGE044-P4"',
                'next_gate_id: "IDS-STAGE044-REVIEW-GATE"',
            )
        )
        self.assertTrue(p3_current or p4_current)
        self.assertIn("push_allowed: false", batch)
        self.assertIn("EVT-IDS-V0_1-STAGE044-P3-20260719-001", events)
        if p4_current:
            self.assertIn("EVT-IDS-V0_1-STAGE044-P4-20260719-001", events)
            self.assertIn(
                "Completed task in this run: `IDS-V0_1-STAGE044-P4`", handoff
            )
            self.assertIn(
                "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`", handoff
            )
        else:
            self.assertIn(
                "Completed task in this run: `IDS-V0_1-STAGE044-P3`", handoff
            )
            self.assertIn("Next allowed task: `IDS-V0_1-STAGE044-P4`", handoff)
        self.assertNotIn("Stage044 whole-stage review completed", handoff)
        self.assertNotIn('current_stage_id: "IDS-STAGE045"', roadmap)


if __name__ == "__main__":
    unittest.main()
