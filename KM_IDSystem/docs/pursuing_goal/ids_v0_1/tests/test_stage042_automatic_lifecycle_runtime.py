import copy
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
PURSUE_ROOT = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = (
    PURSUE_ROOT
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_runtime_contract.json"
)
EVIDENCE = PURSUE_ROOT / "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md"
CHECKER = ROOT / "scripts" / "check_automatic_lifecycle_runtime.py"
BATCH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"
MODEL_REGISTRY = ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = ROOT / "docs" / "governance" / "formula_registry.yaml"
PARAMETER_REGISTRY = ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_SPEC = ROOT / "docs" / "governance" / "MODEL_SPEC.md"

POLICY_VERSION = "ids.automatic_lifecycle_policy.v0_1.stage042.p2"
PARAMETERS = {
    "lifecycle_tick_interval": 1,
    "resume_stability_window": 60,
    "checkpoint_wait_timeout": 30,
    "graceful_shutdown_timeout": 60,
    "cleanup_scan_interval": 300,
}
PARAMETER_IDS = [f"PARAM-{number:03d}" for number in range(72, 77)]
CONTROL_INPUT_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md"
)
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"}
FALSE_RUNTIME_FLAGS = {
    "automatic_lifecycle_runtime_performed",
    "automatic_start_performed",
    "automatic_pause_performed",
    "automatic_resume_performed",
    "automatic_shutdown_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "dead_letter_runtime_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "process_crash_recovery_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "database_connection_performed",
    "schema_change_performed",
    "state_registry_write_performed",
    "runtime_output_written",
    "external_api_call_performed",
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
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Stage042AutomaticLifecycleRuntimeTests(unittest.TestCase):
    def _module(self):
        return _load(CHECKER, "stage042_runtime_under_test")

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase2_artifacts_and_identity_are_exact(self):
        for path in (CONTRACT, EVIDENCE, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing Phase 2 artifact: {path}")
        contract = self._contract()
        self.assertEqual("ids.stage042.automatic_lifecycle.phase2.v1", contract["schema_version"])
        self.assertEqual("STAGE-042", contract["stage"])
        self.assertEqual("Phase 2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE042-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-042", contract["acceptance_id"])
        self.assertEqual(
            "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_LIFECYCLE_DECISION_SLICE",
            contract["execution_mode"],
        )
        self.assertEqual("IDS-STAGE042-P3-GATE", contract["next_gate"])

    def test_source_predecessor_and_upstream_bindings_are_exact(self):
        module = self._module()
        checks = module.evaluate_contract(self._contract())
        for name in (
            "source_binding_exact",
            "phase1_predecessor_exact",
            "upstream_bindings_exact",
            "state_graph_exact",
        ):
            with self.subTest(name=name):
                self.assertTrue(checks[name], checks)
        predecessor = self._contract()["phase1_predecessor_binding"]
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", predecessor["commit"]],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(
            [predecessor["commit"], predecessor["tree"], predecessor["parent"]],
            observed,
        )

    def test_all_five_parameters_are_sourced_registered_and_not_calibrated(self):
        contract = self._contract()
        policy = contract["policy"]
        self.assertEqual(POLICY_VERSION, policy["policy_version"])
        self.assertEqual(PARAMETERS, policy["parameters"])
        self.assertEqual("PROPOSED", policy["fact_level"])
        self.assertFalse(policy["production_calibrated"])
        self.assertTrue(policy["production_calibration_required"])
        self.assertEqual("TASK-OPME-B-001", policy["production_calibration_task_id"])
        self.assertEqual(set(PARAMETERS), set(policy["parameter_provenance"]))
        for name, item in policy["parameter_provenance"].items():
            with self.subTest(parameter=name):
                self.assertEqual(PARAMETERS[name], item["value"])
                self.assertEqual("seconds", item["unit"])
                self.assertEqual("PROPOSED", item["fact_level"])
                self.assertEqual(POLICY_VERSION, item["policy_version"])
                self.assertTrue(item["source_refs"])
                self.assertTrue(item["derivation"])
                self.assertTrue(item["validation_evidence"])
                self.assertEqual("NO_AUTOMATIC_LIFECYCLE", item["rollback"])

        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = {row["parameter_id"]: row for row in rows if row["parameter_id"] in PARAMETER_IDS}
        self.assertEqual(set(PARAMETER_IDS), set(selected))
        for parameter_id, (symbol, value) in zip(PARAMETER_IDS, PARAMETERS.items()):
            with self.subTest(parameter_id=parameter_id):
                self.assertEqual("MOD-011", selected[parameter_id]["model_id"])
                self.assertEqual("FORM-011", selected[parameter_id]["formula_id"])
                self.assertEqual(symbol, selected[parameter_id]["symbol"])
                self.assertEqual(str(value), selected[parameter_id]["active_value"])
                self.assertEqual("planned", selected[parameter_id]["status"])
                self.assertEqual("PROPOSED", selected[parameter_id]["fact_level"])
        self.assertIn('model_id: "MOD-011"', MODEL_REGISTRY.read_text(encoding="utf-8"))
        self.assertIn('formula_id: "FORM-011"', FORMULA_REGISTRY.read_text(encoding="utf-8"))
        spec = MODEL_SPEC.read_text(encoding="utf-8")
        for line in (
            "- model_count: 11",
            "- formula_count: 11",
            "- parameter_count: 76",
            "- active_model_count: 7",
            "- active_formula_count: 7",
            "- active_parameter_count: 49",
        ):
            self.assertIn(line, spec)

    def test_control_request_is_exact_reference_only_and_git_tracked(self):
        module = self._module()
        request = module.build_control_request("AUTO_START")
        self.assertTrue(module.validate_control_request(request))
        self.assertEqual(CONTROL_INPUT_REF, request["evidence"]["input_refs"][0])
        self.assertTrue(request["job_id"].startswith("control:stage042:"))
        self.assertTrue(request["lifecycle_request_id"].startswith("lifecycle:stage042:"))
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("IDS_MetaData", serialized)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("raw_payload", serialized)

    def test_start_candidate_is_guarded_and_exact_replay_is_idempotent(self):
        module = self._module()
        ledger = module.IsolatedLifecycleDecisionLedger()
        request = module.build_control_request("AUTO_START")
        first = module.evaluate_lifecycle(request, ledger=ledger)
        replay = module.evaluate_lifecycle(copy.deepcopy(request), ledger=ledger)
        self.assertEqual("AUTO_START_CANDIDATE", first["decision_action"])
        self.assertEqual(
            [["QUEUED", "CLAIMED"], ["CLAIMED", "RUNNING"]],
            first["transition_candidates"],
        )
        self.assertTrue(first["fresh_admission_and_lock_cycle_required"])
        self.assertEqual(first, replay)
        self.assertEqual(1, ledger.record_count)
        self.assertFalse(first["state_mutation_performed"])
        blocked = module.build_control_request("AUTO_START", admission_gates_passed=False)
        blocked_result = module.evaluate_lifecycle(blocked)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", blocked_result["decision_action"])

    def test_pause_candidates_preserve_legal_paths_and_retry_budget(self):
        module = self._module()
        running = module.build_control_request(
            "AUTO_PAUSE",
            expected_state="RUNNING",
            pressure_signal="EXTERNAL_DRIVE_OFFLINE",
        )
        running_result = module.evaluate_lifecycle(running)
        self.assertEqual("AUTO_PAUSE_CANDIDATE", running_result["decision_action"])
        self.assertEqual(
            [["RUNNING", "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "PAUSED"]],
            running_result["transition_candidates"],
        )
        self.assertFalse(running_result["retry_budget_consumed"])
        queued = module.build_control_request(
            "AUTO_PAUSE",
            expected_state="QUEUED",
            pressure_signal="DISK_SPACE_INSUFFICIENT",
        )
        queued_result = module.evaluate_lifecycle(queued)
        self.assertEqual([["QUEUED", "PAUSED"]], queued_result["transition_candidates"])
        unsafe = copy.deepcopy(queued)
        unsafe["evidence"]["active_claim_or_lock"] = True
        unsafe["lifecycle_request_id"] = module.derive_lifecycle_request_id(unsafe)
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_lifecycle(unsafe)["decision_action"],
        )

    def test_resume_requires_owner_stability_and_a_fresh_cycle(self):
        module = self._module()
        valid = module.build_control_request("AUTO_RESUME")
        result = module.evaluate_lifecycle(valid)
        self.assertEqual("AUTO_RESUME_CANDIDATE", result["decision_action"])
        self.assertEqual([["PAUSED", "QUEUED"]], result["transition_candidates"])
        self.assertTrue(result["fresh_admission_and_lock_cycle_required"])
        self.assertNotIn(["PAUSED", "RUNNING"], result["transition_candidates"])
        for override in (
            {"owner_revalidated": False},
            {"resource_stable_for_seconds": PARAMETERS["resume_stability_window"] - 1},
            {"active_claim_or_lock": True},
            {"resource_gates_passed": False},
        ):
            with self.subTest(override=override):
                blocked = module.build_control_request("AUTO_RESUME", **override)
                self.assertEqual(
                    "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION",
                    module.evaluate_lifecycle(blocked)["decision_action"],
                )

    def test_terminal_states_and_non_integer_versions_fail_closed(self):
        module = self._module()
        for state in sorted(TERMINAL_STATES):
            with self.subTest(state=state):
                request = module.build_control_request("AUTO_RESUME", expected_state=state)
                result = module.evaluate_lifecycle(request)
                self.assertEqual("REJECT_TERMINAL_STATE_IMMUTABLE", result["decision_action"])
                self.assertEqual([], result["transition_candidates"])
        invalid = module.build_control_request("AUTO_START")
        invalid["expected_state_version"] = True
        invalid["lifecycle_request_id"] = module.derive_lifecycle_request_id(invalid)
        self.assertFalse(module.validate_control_request(invalid))
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_lifecycle(invalid)["decision_action"],
        )

    def test_safe_shutdown_is_ordered_bounded_and_never_terminates_process(self):
        module = self._module()
        request = module.build_control_request("SAFE_SHUTDOWN", expected_state="RUNNING")
        result = module.evaluate_lifecycle(request)
        self.assertEqual("SAFE_SHUTDOWN_CANDIDATE", result["decision_action"])
        self.assertEqual(
            [["RUNNING", "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "CANCELLED"]],
            result["transition_candidates"],
        )
        self.assertTrue(result["ordered_shutdown_steps"])
        self.assertFalse(result["process_termination_performed"])
        timeout = module.build_control_request(
            "SAFE_SHUTDOWN",
            expected_state="RUNNING",
            shutdown_elapsed_seconds=PARAMETERS["graceful_shutdown_timeout"] + 1,
        )
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_lifecycle(timeout)["decision_action"],
        )

    def test_cleanup_is_candidate_only_and_protected_artifacts_never_delete(self):
        module = self._module()
        request = module.build_control_request("CLEANUP_CANDIDATE_SCAN")
        result = module.evaluate_lifecycle(request)
        self.assertEqual("CLEANUP_CANDIDATE_ONLY", result["decision_action"])
        self.assertEqual([], result["transition_candidates"])
        self.assertTrue(result["cleanup_candidate_only"])
        self.assertFalse(result["cleanup_runtime_performed"])
        self.assertFalse(result["protected_ref_delete_performed"])
        protected = module.build_control_request(
            "CLEANUP_CANDIDATE_SCAN",
            cleanup_candidate_class="FACT_SOURCE",
        )
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_lifecycle(protected)["decision_action"],
        )

    def test_results_record_input_output_error_checkpoint_without_raw_echo(self):
        module = self._module()
        request = module.build_control_request("AUTO_PAUSE", expected_state="RUNNING")
        result = module.evaluate_lifecycle(request)
        self.assertEqual(request["evidence"]["input_refs"], result["input_refs"])
        self.assertEqual([], result["output_refs"])
        self.assertIsNone(result["error_ref"])
        self.assertTrue(result["checkpoint_ref"].startswith("checkpoint:sha256:"))
        malformed = {"raw_payload": "secret-value", "expected_state_version": True}
        failed = module.evaluate_lifecycle(malformed)
        serialized = json.dumps(failed, ensure_ascii=False)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", failed["decision_action"])
        self.assertEqual("error:INVALID_LIFECYCLE_REQUEST", failed["error_ref"])
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("raw_payload", serialized)

    def test_same_request_id_with_changed_payload_is_rejected(self):
        module = self._module()
        ledger = module.IsolatedLifecycleDecisionLedger()
        original = module.build_control_request("AUTO_START")
        self.assertEqual(
            "AUTO_START_CANDIDATE",
            module.evaluate_lifecycle(original, ledger=ledger)["decision_action"],
        )
        conflict = copy.deepcopy(original)
        conflict["expected_state_version"] += 1
        result = module.evaluate_lifecycle(conflict, ledger=ledger)
        self.assertEqual("REJECT_LIFECYCLE_REQUEST_CONFLICT", result["decision_action"])
        self.assertEqual([], result["transition_candidates"])
        self.assertEqual(1, ledger.record_count)

    def test_checker_report_proves_candidates_but_no_actual_lifecycle(self):
        module = self._module()
        report = module.build_stage042_phase2_report()
        self.assertTrue(report["phase2_slice_valid"], report)
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertTrue(all(report["decision_checks"].values()), report)
        self.assertEqual(
            {
                "automatic_start",
                "automatic_pause",
                "automatic_resume",
                "safe_shutdown",
                "cleanup_candidate",
            },
            set(report["scenario_results"]),
        )
        self.assertTrue(report["parameter_values_assigned"])
        self.assertTrue(report["isolated_lifecycle_decision_runtime_performed"])
        self.assertTrue(report["lifecycle_candidate_evaluation_performed"])
        self.assertTrue(report["phase3_entry_authorized"])
        self.assertEqual("IDS-STAGE042-P3-GATE", report["next_gate"])
        for name in FALSE_RUNTIME_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])

    def test_contract_and_request_tampering_fail_closed(self):
        module = self._module()
        contract = self._contract()
        mutations = []
        wrong_parameter = copy.deepcopy(contract)
        wrong_parameter["policy"]["parameters"]["resume_stability_window"] = 1
        mutations.append(wrong_parameter)
        extra_root = copy.deepcopy(contract)
        extra_root["unexpected"] = True
        mutations.append(extra_root)
        production = copy.deepcopy(contract)
        production["runtime_boundary"]["production_activation_allowed"] = True
        mutations.append(production)
        broken_upstream = copy.deepcopy(contract)
        broken_upstream["upstream_bindings"]["stage041_lock_runtime"]["sha256"] = "0" * 64
        mutations.append(broken_upstream)
        for candidate in mutations:
            with self.subTest(candidate=list(candidate)):
                self.assertFalse(all(module.evaluate_contract(candidate).values()))

    def test_governance_event_and_handoff_stop_at_phase2(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn('status: "stage042_phase2_completed"', batch)
        self.assertIn('      - "Phase 2"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE042-P3"', batch)
        self.assertIn('push_allowed: false', batch)
        self.assertIn('current_phase_id: "IDS-STAGE042-P2"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE042-P3-GATE"', roadmap)
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE042-P2`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE042-P3`", handoff)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matching = [
            event
            for event in events
            if event.get("event_id") == "EVT-IDS-V0_1-STAGE042-P2-20260718-001"
        ]
        self.assertEqual(1, len(matching), matching)
        self.assertEqual("phase_completed", matching[0]["event_type"])
        self.assertEqual("IDS-V0_1-STAGE042-P2", matching[0]["task_id"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])
        self.assertFalse((PURSUE_ROOT / "STAGE042_PHASE3_SCENARIO_VALIDATION.md").exists())

    def test_cli_emits_the_exact_machine_report(self):
        module = self._module()
        expected = module.build_stage042_phase2_report()
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(expected, json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
