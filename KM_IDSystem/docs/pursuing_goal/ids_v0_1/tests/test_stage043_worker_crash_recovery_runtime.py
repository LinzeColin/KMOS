import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE2_DOC = BASE / "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md"
CONTRACT = (
    BASE
    / "worker_crash_recovery"
    / "stage043_worker_crash_recovery_runtime_contract.json"
)
CHECKER = ROOT / "scripts" / "check_worker_crash_recovery_runtime.py"
PARAMETER_REGISTRY = ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_REGISTRY = ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = ROOT / "docs" / "governance" / "formula_registry.yaml"
MODEL_SPEC = ROOT / "docs" / "governance" / "MODEL_SPEC.md"

PARAMETERS = {
    "crash_detection_interval": 1,
    "heartbeat_stale_window": 30,
    "lease_expiry_grace": 5,
    "recovery_retry_backoff": 30,
    "checkpoint_validation_timeout": 30,
}
PARAMETER_IDS = [
    "PARAM-077",
    "PARAM-078",
    "PARAM-079",
    "PARAM-080",
    "PARAM-081",
]
SOURCE_BINDING = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-043_Worker崩溃恢复.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}
PREDECESSOR_BINDING = {
    "commit": "d4b5ec1ef9bff3d2390869b4fd2998bd17d2c671",
    "tree": "6d7af7a50506df15f229e35977143ead0f5b3f06",
    "parent": "ba248f66ce993a726cb12547ae1c772ab1228bfa",
    "task_id": "IDS-V0_1-STAGE043-P1",
    "result": "PASS_LOCAL",
}
UPSTREAM_BINDINGS = {
    "phase1_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_contract.json",
        "78cb110cd10f4068b72ceba01752d2771378c7d07b569797bd0efa88f6826ef4",
    ),
    "phase1_checker": (
        "KM_IDSystem/scripts/check_worker_crash_recovery.py",
        "27abe895addb64f4280cb1b6c7b9f443e5bd9f3a038cb38ff27aa226271d39a3",
    ),
    "phase1_boundary": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md",
        "50baa3eda8d40317456e566da908b4cb8a69c0096b1725087ac165debf6af23e",
    ),
    "stage037_state_index": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage039_retry_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
        "stage039_retry_dead_letter_runtime_contract.json",
        "5fc9b49b0ede0fdbc87311f3280ffc69e8ec8e59f219b17a04a2ccae1e9124c0",
    ),
    "stage040_backpressure_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_runtime_contract.json",
        "2970ebd143030821d9a8b00e4fdb11342f8f82ef3bcf4d91717ba707b5054e2e",
    ),
    "stage041_lock_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_runtime_contract.json",
        "80f87c789c6fc834b13eaec3d14d9444417ee7313ff8f88f6893bbda15e1f464",
    ),
    "stage042_lifecycle_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_runtime_contract.json",
        "f24283a0ab934082b0ceb48c6ca1597ca17d1c6cca6a939e2653fb00ede83e49",
    ),
}


class Stage043WorkerCrashRecoveryPhase2Tests(unittest.TestCase):
    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing Phase 2 contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing Phase 2 checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage043_worker_crash_recovery_runtime_checker", CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase2_artifacts_and_identity_are_exact(self):
        for path in (PHASE2_DOC, CONTRACT, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing Phase 2 artifact: {path}")
        contract = self._contract()
        self.assertEqual("ids.stage043.worker_crash_recovery.phase2.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE043-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-043", contract["acceptance_id"])
        self.assertEqual(
            "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CRASH_RECOVERY_DECISION_SLICE",
            contract["execution_mode"],
        )
        self.assertEqual(
            "ids.worker_crash_recovery_policy.v0_1.stage043.p2",
            contract["policy_contract_id"],
        )
        self.assertEqual("IDS-STAGE043-P3-GATE", contract["next_gate"])

    def test_source_predecessor_and_upstream_bindings_are_exact(self):
        module = self._checker()
        contract = self._contract()
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["phase1_predecessor_binding"])
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", PREDECESSOR_BINDING["commit"]],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(
            [PREDECESSOR_BINDING["commit"], PREDECESSOR_BINDING["tree"], PREDECESSOR_BINDING["parent"]],
            observed,
        )
        for key, (relative, digest) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                self.assertEqual(
                    {"ref": relative, "sha256": digest},
                    contract["upstream_bindings"][key],
                )
                self.assertEqual(
                    digest,
                    hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest(),
                )
        self.assertTrue(all(module.evaluate_contract(contract).values()))

    def test_all_five_parameters_are_sourced_registered_and_not_calibrated(self):
        contract = self._contract()
        policy = contract["policy"]
        self.assertEqual(PARAMETERS, policy["parameters"])
        self.assertEqual("PROPOSED", policy["fact_level"])
        self.assertFalse(policy["production_calibrated"])
        self.assertEqual("TASK-OPME-B-001", policy["production_calibration_task_id"])
        self.assertEqual(set(PARAMETERS), set(policy["parameter_provenance"]))
        for name, item in policy["parameter_provenance"].items():
            with self.subTest(parameter=name):
                self.assertEqual(PARAMETERS[name], item["value"])
                self.assertEqual("seconds", item["unit"])
                self.assertEqual("PROPOSED", item["fact_level"])
                self.assertEqual(policy["policy_version"], item["policy_version"])
                self.assertTrue(item["source_refs"])
                self.assertTrue(item["derivation"])
                self.assertTrue(item["validation_evidence"])
                self.assertEqual("NO_AUTOMATIC_CRASH_RECOVERY", item["rollback"])

        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = {
            row["parameter_id"]: row
            for row in rows
            if row["parameter_id"] in PARAMETER_IDS
        }
        self.assertEqual(set(PARAMETER_IDS), set(selected))
        for parameter_id, (symbol, value) in zip(PARAMETER_IDS, PARAMETERS.items()):
            with self.subTest(parameter_id=parameter_id):
                row = selected[parameter_id]
                self.assertEqual("MOD-012", row["model_id"])
                self.assertEqual("FORM-012", row["formula_id"])
                self.assertEqual(symbol, row["symbol"])
                self.assertEqual(str(value), row["active_value"])
                self.assertEqual("planned", row["status"])
                self.assertEqual("PROPOSED", row["fact_level"])
        model_text = MODEL_REGISTRY.read_text(encoding="utf-8")
        formula_text = FORMULA_REGISTRY.read_text(encoding="utf-8")
        spec_text = MODEL_SPEC.read_text(encoding="utf-8")
        self.assertIn('assumption_id: "ASM-008"', model_text)
        self.assertIn('model_id: "MOD-012"', model_text)
        self.assertIn('formula_id: "FORM-012"', formula_text)
        for marker in (
            "- model_count: 12",
            "- formula_count: 12",
            "- parameter_count: 81",
            "- active_model_count: 7",
            "- active_formula_count: 7",
            "- active_parameter_count: 49",
        ):
            self.assertIn(marker, spec_text)

    def test_control_request_is_exact_reference_only_and_canonical(self):
        module = self._checker()
        request = module.build_recovery_request("CHECKPOINT_RESUME")
        self.assertTrue(module.validate_recovery_request(request))
        self.assertEqual(
            request["recovery_request_key"],
            module.derive_recovery_request_key(request),
        )
        self.assertTrue(request["job_id"].startswith("control:stage043:"))
        self.assertNotIn("raw_payload", json.dumps(request, ensure_ascii=False))
        self.assertFalse(any(str(value).startswith("/") for value in request.values()))
        for ref in request["evidence"]["input_refs"]:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", ref],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, tracked.returncode, ref)

    def test_checkpoint_resume_candidate_requires_every_guard_and_legal_reentry(self):
        module = self._checker()
        request = module.build_recovery_request("CHECKPOINT_RESUME")
        result = module.evaluate_recovery(request)
        self.assertEqual("CHECKPOINT_RESUME_CANDIDATE", result["decision_action"])
        self.assertEqual(
            [
                ["RUNNING", "RETRY_WAIT"],
                ["RETRY_WAIT", "QUEUED"],
                ["QUEUED", "CLAIMED"],
                ["CLAIMED", "RUNNING"],
            ],
            result["transition_candidates"],
        )
        for field in (
            "checkpoint_integrity_valid",
            "checkpoint_idempotency_valid",
            "owner_revalidated",
            "resource_gates_passed",
            "lost_worker_fenced",
            "state_version_current",
            "persistent_state_available",
        ):
            with self.subTest(field=field):
                blocked = module.build_recovery_request("CHECKPOINT_RESUME")
                blocked["evidence"][field] = False
                blocked["recovery_request_key"] = module.derive_recovery_request_key(blocked)
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    module.evaluate_recovery(blocked)["decision_action"],
                )

    def test_resource_pause_is_mandatory_and_never_auto_resumes(self):
        module = self._checker()
        for signal in (
            "EXTERNAL_DRIVE_OFFLINE",
            "DISK_SPACE_INSUFFICIENT",
            "EXTERNAL_API_BUDGET_INSUFFICIENT",
        ):
            with self.subTest(signal=signal):
                request = module.build_recovery_request(
                    "RESOURCE_PAUSE",
                    resource_gates_passed=False,
                    resource_pressure_signal=signal,
                )
                result = module.evaluate_recovery(request)
                self.assertEqual("RESOURCE_PAUSE_CANDIDATE", result["decision_action"])
                self.assertEqual(
                    [["RUNNING", "RETRY_WAIT"], ["RETRY_WAIT", "PAUSED"]],
                    result["transition_candidates"],
                )
                self.assertFalse(result["automatic_resume_allowed"])

    def test_stage039_retry_candidate_requires_policy_budget_safety_and_backoff(self):
        module = self._checker()
        request = module.build_recovery_request("STAGE039_RETRY")
        result = module.evaluate_recovery(request)
        self.assertEqual("STAGE039_RETRY_CANDIDATE", result["decision_action"])
        self.assertEqual("STAGE-039", result["runtime_owner"])
        for field in (
            "stage039_policy_eligible",
            "retry_budget_available",
            "replay_safe",
        ):
            with self.subTest(field=field):
                blocked = module.build_recovery_request("STAGE039_RETRY")
                blocked["evidence"][field] = False
                blocked["recovery_request_key"] = module.derive_recovery_request_key(blocked)
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    module.evaluate_recovery(blocked)["decision_action"],
                )
        early = module.build_recovery_request(
            "STAGE039_RETRY", recovery_retry_wait_elapsed_seconds=29
        )
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_recovery(early)["decision_action"],
        )

    def test_safe_failure_is_only_a_legal_running_candidate(self):
        module = self._checker()
        valid = module.build_recovery_request("SAFE_FAILURE")
        result = module.evaluate_recovery(valid)
        self.assertEqual("SAFE_FAILURE_CANDIDATE", result["decision_action"])
        self.assertEqual([["RUNNING", "FAILED"]], result["transition_candidates"])
        for state in ("CLAIMED", "PAUSE_REQUESTED", "RETRY_WAIT"):
            with self.subTest(state=state):
                blocked = module.build_recovery_request(
                    "SAFE_FAILURE", observed_state=state
                )
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    module.evaluate_recovery(blocked)["decision_action"],
                )

    def test_terminal_or_stale_conflicting_and_malformed_evidence_fails_closed(self):
        module = self._checker()
        for state in ("SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"):
            with self.subTest(state=state):
                request = module.build_recovery_request(
                    "CHECKPOINT_RESUME", observed_state=state
                )
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    module.evaluate_recovery(request)["decision_action"],
                )
        stale_heartbeat = module.build_recovery_request(
            "CHECKPOINT_RESUME", last_heartbeat_observed_at_epoch_seconds=971
        )
        live_lease = module.build_recovery_request(
            "CHECKPOINT_RESUME", lease_expires_at_epoch_seconds=996
        )
        bool_version = module.build_recovery_request("CHECKPOINT_RESUME")
        bool_version["observed_state_version"] = True
        bool_version["recovery_request_key"] = module.derive_recovery_request_key(
            bool_version
        )
        conflict = module.build_recovery_request(
            "CHECKPOINT_RESUME", active_lock_or_claim_conflict=True
        )
        for request in (stale_heartbeat, live_lease, bool_version, conflict):
            with self.subTest(request=request):
                self.assertEqual(
                    "REQUIRE_MANUAL_REVIEW",
                    module.evaluate_recovery(request)["decision_action"],
                )

    def test_exact_replay_is_idempotent_and_same_key_changed_payload_conflicts(self):
        module = self._checker()
        ledger = module.InMemoryRecoveryDecisionLedger()
        request = module.build_recovery_request("CHECKPOINT_RESUME")
        first = module.evaluate_recovery(request, ledger=ledger)
        replay = module.evaluate_recovery(copy.deepcopy(request), ledger=ledger)
        self.assertEqual(first, replay)
        changed = copy.deepcopy(request)
        changed["evidence"]["owner_revalidated"] = False
        conflict = module.evaluate_recovery(changed, ledger=ledger)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", conflict["decision_action"])
        self.assertEqual("RECOVERY_REQUEST_CONFLICT", conflict["reason_code"])

    def test_partial_output_is_quarantined_and_protected_artifacts_never_delete(self):
        module = self._checker()
        result = module.evaluate_recovery(
            module.build_recovery_request("CHECKPOINT_RESUME")
        )
        self.assertTrue(result["quarantine_ref"].startswith("quarantine:sha256:"))
        self.assertFalse(result["delete_allowed"])
        self.assertEqual("STAGE-044", result["cleanup_execution_owner"])
        contract = self._contract()
        self.assertEqual(
            ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"],
            contract["runtime_boundary"]["cleanup_candidate_classes"],
        )
        self.assertEqual(
            ["FACT_SOURCE", "MANIFEST", "EVIDENCE_LEDGER", "REPORT_SNAPSHOT", "AUDIT_LOG"],
            contract["runtime_boundary"]["protected_artifact_classes"],
        )

    def test_results_are_safe_reference_only_and_human_readable(self):
        module = self._checker()
        request = module.build_recovery_request("CHECKPOINT_RESUME")
        result = module.evaluate_recovery(request)
        self.assertEqual(request["evidence"]["input_refs"], result["input_refs"])
        self.assertEqual([], result["output_refs"])
        self.assertTrue(result["checkpoint_ref"].startswith("checkpoint:sha256:"))
        self.assertTrue(result["audit_ref"])
        self.assertTrue(result["human_status"]["label_zh"])
        dumped = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("raw_payload", dumped)
        malformed = module.evaluate_recovery({"raw_payload": "secret-value"})
        self.assertEqual("REQUIRE_MANUAL_REVIEW", malformed["decision_action"])
        self.assertNotIn("secret-value", json.dumps(malformed, ensure_ascii=False))

        unsafe_identity = module.build_recovery_request("CHECKPOINT_RESUME")
        unsafe_identity["job_id"] = "control:stage043:../secret"
        unsafe_identity["recovery_request_key"] = module.derive_recovery_request_key(
            unsafe_identity
        )
        self.assertFalse(module.validate_recovery_request(unsafe_identity))
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            module.evaluate_recovery(unsafe_identity)["decision_action"],
        )

        untrusted_refs = module.build_recovery_request("CHECKPOINT_RESUME")
        untrusted_refs["evidence"]["error_ref"] = "error:password"
        untrusted_refs["evidence"]["checkpoint_ref"] = "checkpoint:sha256:" + "f" * 64
        untrusted_refs["evidence"]["quarantine_ref"] = "quarantine:sha256:" + "e" * 64
        untrusted_result = module.evaluate_recovery(untrusted_refs)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", untrusted_result["decision_action"])
        self.assertNotEqual(
            untrusted_refs["evidence"]["error_ref"], untrusted_result["error_ref"]
        )
        self.assertNotEqual(
            untrusted_refs["evidence"]["checkpoint_ref"],
            untrusted_result["checkpoint_ref"],
        )
        self.assertNotEqual(
            untrusted_refs["evidence"]["quarantine_ref"],
            untrusted_result["quarantine_ref"],
        )
        self.assertNotIn("password", json.dumps(untrusted_result, ensure_ascii=False))

    def test_contract_and_request_tampering_fail_closed(self):
        module = self._checker()
        contract = self._contract()
        mutations = []
        wrong_parameter = copy.deepcopy(contract)
        wrong_parameter["policy"]["parameters"]["heartbeat_stale_window"] = 1
        mutations.append(wrong_parameter)
        runtime_enabled = copy.deepcopy(contract)
        runtime_enabled["runtime_boundary"]["process_crash_recovery_allowed"] = True
        mutations.append(runtime_enabled)
        wrong_hash = copy.deepcopy(contract)
        wrong_hash["upstream_bindings"]["stage041_lock_runtime"]["sha256"] = "0" * 64
        mutations.append(wrong_hash)
        extra_root = copy.deepcopy(contract)
        extra_root["unexpected"] = True
        mutations.append(extra_root)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertFalse(all(module.evaluate_contract(candidate).values()))
                result = module.evaluate_recovery(
                    module.build_recovery_request("CHECKPOINT_RESUME"),
                    contract=candidate,
                )
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])

        forged = module.build_recovery_request("CHECKPOINT_RESUME")
        forged["recovery_request_key"] = "0" * 64
        result = module.evaluate_recovery(forged)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("RECOVERY_REQUEST_KEY_MISMATCH", result["reason_code"])

    def test_checker_report_proves_candidates_but_no_actual_recovery(self):
        module = self._checker()
        report = module.build_stage043_phase2_report()
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertTrue(all(report["decision_checks"].values()), report)
        self.assertTrue(report["parameter_values_assigned"])
        self.assertEqual("PROPOSED", report["parameter_fact_level"])
        self.assertTrue(report["isolated_recovery_decision_runtime_performed"])
        self.assertTrue(report["recovery_candidate_evaluation_performed"])
        self.assertFalse(report["process_crash_recovery_performed"])
        self.assertFalse(report["process_termination_performed"])
        self.assertFalse(report["worker_restart_performed"])
        self.assertFalse(report["state_transition_performed"])
        self.assertFalse(report["checkpoint_resume_performed"])
        self.assertFalse(report["cleanup_runtime_performed"])
        self.assertFalse(report["raw_metadata_content_accessed"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertEqual("IDS-STAGE043-P3-GATE", report["next_gate"])
        self.assertEqual(
            "PASS_ISOLATED_RECOVERY_DECISION_SLICE_PRODUCTION_DISABLED",
            report["result"],
        )

    def test_governance_event_handoff_and_route_stop_at_phase2(self):
        batch = (BASE / "BATCH041_050_UPLOAD_LOCK.yaml").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "governance" / "roadmap.yaml").read_text(
            encoding="utf-8"
        )
        events = (ROOT / "docs" / "governance" / "events.jsonl").read_text(
            encoding="utf-8"
        )
        handoff = (ROOT / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
        for marker in (
            'status: "stage043_phase2_completed"',
            'current_task_id: "IDS-V0_1-STAGE043-P2"',
            'next_allowed_task_id: "IDS-V0_1-STAGE043-P3"',
            'next_gate: "IDS-STAGE043-P3-GATE"',
            'github_upload_allowed: false',
        ):
            self.assertIn(marker, batch)
        for marker in (
            'current_stage_id: "IDS-STAGE043"',
            'current_phase_id: "IDS-STAGE043-P2"',
            'current_task_id: "IDS-V0_1-STAGE043-P2"',
            'next_gate_id: "IDS-STAGE043-P3-GATE"',
        ):
            self.assertIn(marker, roadmap)
        self.assertIn("EVT-IDS-V0_1-STAGE043-P2-20260718-001", events)
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE043-P2`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE043-P3`", handoff)
        self.assertIn("process_crash_recovery_performed=false", events)
        self.assertNotIn('current_phase_id: "IDS-STAGE043-P3"', roadmap)

    def test_cli_emits_the_exact_machine_report(self):
        module = self._checker()
        expected = module.build_stage043_phase2_report()
        completed = subprocess.run(
            ["python3", "-B", str(CHECKER)],
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
