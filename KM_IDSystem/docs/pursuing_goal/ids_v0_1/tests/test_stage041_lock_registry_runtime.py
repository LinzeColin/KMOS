import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "lock_registry" / "stage041_lock_registry_runtime_contract.json"
EVIDENCE = BASE / "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md"
CHECKER = ROOT / "scripts" / "check_lock_registry_runtime.py"
PHASE1_CHECKER = ROOT / "scripts" / "check_lock_registry.py"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
MODEL_REGISTRY = ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = ROOT / "docs" / "governance" / "formula_registry.yaml"
PARAMETER_REGISTRY = ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_SPEC = ROOT / "docs" / "governance" / "MODEL_SPEC.md"

POLICY_VERSION = "ids.lock_registry_policy.v0_1.stage041.p2"
CONTROL_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
)
PARAMETERS = {
    "lease_duration_seconds": 30,
    "renewal_interval_seconds": 10,
    "expiry_grace_seconds": 5,
    "acquisition_timeout_seconds": 1,
    "maximum_wait_seconds": 0,
    "retry_jitter_seconds": 0,
    "deadlock_timeout_seconds": 1,
}
PARAMETER_IDS = [f"PARAM-{value:03d}" for value in range(65, 72)]
UPSTREAM_BINDINGS = {
    "phase1_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_contract.json",
        "52e445bd581fb32c23887a290b656f72fb1fe123119255019f9e5bc65fe9beb5",
    ),
    "phase1_checker": (
        "KM_IDSystem/scripts/check_lock_registry.py",
        "11e20b3fb4ad2e15500053c8ff0284183c4d880601e6edf9095f2f49bc8d05de",
    ),
    "phase1_boundary": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md",
        "526c8f7c1b71ad342535f3bc36db7ad79a9d203737c977089ac33cd301077c34",
    ),
    "stage038_conflict_scenarios": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
        "stage038_worker_queue_scenarios.json",
        "0ec9f1a0de6ec24d64d4108214ea426f9171b15eebdd6c3c60693fade62f2961",
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
}


class Stage041LockRegistryRuntimeTests(unittest.TestCase):
    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage041_lock_registry_runtime", CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _phase1_module(self):
        spec = importlib.util.spec_from_file_location(
            "stage041_lock_registry_phase1", PHASE1_CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _request(self, *, role="primary", now=1000, operation="FILE_PROCESSING"):
        return self._module().build_control_request(
            CONTROL_REF,
            operation_family=operation,
            holder_role=role,
            requested_at_epoch_seconds=now,
        )

    def test_phase2_artifacts_and_identity_exist(self):
        for path in (CONTRACT, EVIDENCE, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing Phase 2 artifact: {path}")
        contract = self._contract()
        self.assertEqual("ids.stage041.lock_registry.phase2.v1", contract["schema_version"])
        self.assertEqual("STAGE-041", contract["stage"])
        self.assertEqual("Phase 2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE041-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-041", contract["acceptance_id"])
        self.assertEqual(POLICY_VERSION, contract["policy_contract_id"])
        self.assertEqual("IDS-STAGE041-P3-GATE", contract["next_gate"])

    def test_upstream_bindings_are_current_and_exact(self):
        bindings = self._contract()["upstream_bindings"]
        self.assertEqual(set(UPSTREAM_BINDINGS), set(bindings))
        for key, (relative, expected_sha) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                self.assertEqual(relative, bindings[key]["ref"])
                self.assertEqual(expected_sha, bindings[key]["sha256"])
                self.assertEqual(
                    expected_sha,
                    hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest(),
                )

    def test_parameters_are_complete_bounded_and_not_production_calibrated(self):
        policy = self._contract()["policy"]
        self.assertEqual(POLICY_VERSION, policy["policy_version"])
        self.assertEqual(PARAMETERS, policy["parameters"])
        self.assertEqual("PROPOSED", policy["fact_level"])
        self.assertFalse(policy["production_calibrated"])
        self.assertTrue(policy["production_calibration_required"])
        self.assertEqual("TASK-OPME-B-001", policy["production_calibration_task_id"])
        self.assertEqual(
            PARAMETERS["lease_duration_seconds"],
            3 * PARAMETERS["renewal_interval_seconds"],
        )
        self.assertLess(
            PARAMETERS["expiry_grace_seconds"],
            PARAMETERS["renewal_interval_seconds"],
        )
        self.assertEqual(0, PARAMETERS["maximum_wait_seconds"])
        self.assertEqual(0, PARAMETERS["retry_jitter_seconds"])

    def test_control_ref_is_real_tracked_and_business_data_is_excluded(self):
        contract = self._contract()
        self.assertEqual([CONTROL_REF], contract["control_metadata_contract"]["input_refs"])
        relative = CONTROL_REF.removeprefix("repo:")
        self.assertTrue((REPO_ROOT / relative).is_file())
        self.assertNotIn("/Users/linzezhang/Downloads/IDS_MetaData", CONTROL_REF)
        self.assertFalse(contract["control_metadata_contract"]["raw_body_allowed"])
        self.assertFalse(contract["runtime_boundary"]["ids_business_job_allowed"])
        self.assertFalse(contract["runtime_boundary"]["fake_ids_business_data_allowed"])

    def test_registry_entries_cover_mod_formula_and_all_seven_parameters(self):
        contract = self._contract()
        binding = contract["registry_binding"]
        self.assertEqual("MOD-010", binding["model_id"])
        self.assertEqual("FORM-010", binding["formula_id"])
        self.assertEqual(PARAMETER_IDS, binding["parameter_ids"])
        self.assertIn('model_id: "MOD-010"', MODEL_REGISTRY.read_text(encoding="utf-8"))
        self.assertIn('formula_id: "FORM-010"', FORMULA_REGISTRY.read_text(encoding="utf-8"))
        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = {row["parameter_id"]: row for row in rows if row["parameter_id"] in PARAMETER_IDS}
        self.assertEqual(set(PARAMETER_IDS), set(selected))
        for parameter_id, (symbol, value) in zip(PARAMETER_IDS, PARAMETERS.items()):
            with self.subTest(parameter_id=parameter_id):
                self.assertEqual(symbol, selected[parameter_id]["symbol"])
                self.assertEqual(str(value), selected[parameter_id]["active_value"])
                self.assertEqual("PROPOSED", selected[parameter_id]["fact_level"])
                self.assertEqual("planned", selected[parameter_id]["status"])
        spec = MODEL_SPEC.read_text(encoding="utf-8")
        total_counts = {
            key: int(value)
            for line in spec.splitlines()
            if line.startswith("- ") and ": " in line
            for key, value in [line[2:].split(": ", 1)]
            if key in {"model_count", "formula_count", "parameter_count"}
        }
        self.assertGreaterEqual(total_counts.get("model_count", 0), 10)
        self.assertGreaterEqual(total_counts.get("formula_count", 0), 10)
        self.assertGreaterEqual(total_counts.get("parameter_count", 0), 71)
        self.assertIn("- active_model_count: 7", spec)
        self.assertIn("- active_formula_count: 7", spec)
        self.assertIn("- active_parameter_count: 49", spec)

    def test_acquire_is_canonical_all_or_none_and_records_bounded_metadata(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        result = registry.acquire(self._request(now=1000))
        self.assertTrue(result["decision_valid"], result)
        self.assertEqual("ACQUIRE", result["operation"])
        self.assertEqual("LOCK_SET_ACQUIRED", result["result_code"])
        self.assertEqual("ACQUIRED", result["decision_action"])
        self.assertEqual(sorted(result["lock_keys"]), result["lock_keys"])
        self.assertEqual(2, len(result["lock_keys"]))
        self.assertEqual(1, result["fencing_token"])
        self.assertEqual({key: 1 for key in result["lock_keys"]}, result["lock_versions"])
        self.assertEqual(1030, result["lease_expires_at"])
        self.assertEqual([CONTROL_REF], result["input_refs"])
        self.assertEqual([], result["output_refs"])
        self.assertIsNone(result["error_ref"])
        self.assertRegex(result["checkpoint_ref"], r"^checkpoint:sha256:[0-9a-f]{64}$")
        self.assertEqual("已获取资源锁", result["human_status"]["label_zh"])
        self.assertFalse(result["queue_record_created"])
        self.assertFalse(result["retry_budget_consumed"])
        self.assertFalse(result["partial_lock_retained"])

    def test_duplicate_acquire_replays_without_advancing_fence_or_version(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        request = self._request(now=1000)
        first = registry.acquire(request)
        before = registry.snapshot()
        replay = registry.acquire(copy.deepcopy(request))
        self.assertEqual(first, replay)
        self.assertEqual(before, registry.snapshot())
        self.assertEqual(1, replay["fencing_token"])

    def test_same_idempotency_key_with_changed_input_fails_closed(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        original = self._request(now=1000)
        first = registry.acquire(original)
        before = registry.snapshot()
        changed = self._request(now=1001)
        self.assertEqual(first["holder_job_id"], changed["holder_job_id"])
        changed["idempotency_key"] = original["idempotency_key"]
        conflict = registry.acquire(changed)
        self.assertEqual("IDEMPOTENCY_INPUT_CONFLICT", conflict["result_code"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", conflict["decision_action"])
        self.assertEqual(before, registry.snapshot())

    def test_contention_pauses_before_queue_and_retains_no_partial_lock(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        acquired = registry.acquire(self._request(role="primary", now=1000))
        conflict = registry.acquire(self._request(role="contender", now=1001))
        self.assertTrue(conflict["decision_valid"])
        self.assertEqual("RESOURCE_CONFLICT_ACTIVE", conflict["result_code"])
        self.assertEqual("PAUSE_BEFORE_QUEUE_ADMISSION", conflict["decision_action"])
        self.assertEqual("等待资源锁", conflict["human_status"]["label_zh"])
        self.assertFalse(conflict["queue_record_created"])
        self.assertFalse(conflict["retry_budget_consumed"])
        self.assertFalse(conflict["partial_lock_retained"])
        self.assertEqual(2, len(registry.snapshot()["locks"]))
        self.assertEqual(
            acquired["holder_job_id"],
            next(iter(registry.snapshot()["locks"].values()))["holder_job_id"],
        )

    def test_renew_requires_live_matching_holder_and_advances_only_version(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        acquired = registry.acquire(self._request(now=1000))
        renewed = registry.renew(self._request(now=1010), acquired)
        self.assertEqual("LEASE_RENEWED", renewed["result_code"])
        self.assertEqual("RENEWED", renewed["decision_action"])
        self.assertEqual(1040, renewed["lease_expires_at"])
        self.assertEqual(acquired["fencing_token"], renewed["fencing_token"])
        self.assertEqual(
            {key: version + 1 for key, version in acquired["lock_versions"].items()},
            renewed["lock_versions"],
        )
        stale_commit = registry.can_commit(self._request(now=1011), acquired)
        self.assertEqual("STALE_FENCING_TOKEN", stale_commit["result_code"])
        replay = registry.renew(self._request(now=1010), acquired)
        self.assertEqual(renewed, replay)

    def test_takeover_requires_expiry_plus_grace_and_advances_fence_atomically(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        acquired = registry.acquire(self._request(role="primary", now=1000))
        early = registry.takeover(
            self._request(role="successor", now=1034), acquired
        )
        self.assertTrue(early["decision_valid"])
        self.assertEqual("LEASE_NOT_TAKEOVER_ELIGIBLE", early["result_code"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", early["decision_action"])
        takeover_request = self._request(role="successor", now=1035)
        takeover_request["idempotency_key"] = (
            "idempotency:sha256:"
            + hashlib.sha256(b"successor-takeover-1035").hexdigest()
        )
        takeover = registry.takeover(takeover_request, acquired)
        self.assertEqual("TAKEOVER_ACQUIRED", takeover["result_code"])
        self.assertEqual("ACQUIRED", takeover["decision_action"])
        self.assertEqual(acquired["fencing_token"] + 1, takeover["fencing_token"])
        self.assertEqual(
            {key: version + 1 for key, version in acquired["lock_versions"].items()},
            takeover["lock_versions"],
        )
        self.assertEqual(1065, takeover["lease_expires_at"])

    def test_takeover_rejects_stale_cas_evidence_after_renew(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        acquired = registry.acquire(self._request(role="primary", now=1000))
        renewed = registry.renew(self._request(role="primary", now=1010), acquired)
        before = registry.snapshot()
        successor = self._request(role="successor", now=1045)
        stale = registry.takeover(successor, acquired)
        self.assertEqual("STALE_TAKEOVER_EVIDENCE", stale["result_code"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", stale["decision_action"])
        after_stale = registry.snapshot()
        for key in ("locks", "lock_versions", "fencing_counter"):
            self.assertEqual(before[key], after_stale[key])
        successor["idempotency_key"] = (
            "idempotency:sha256:"
            + hashlib.sha256(b"successor-takeover-current-evidence").hexdigest()
        )
        takeover = registry.takeover(successor, renewed)
        self.assertEqual("TAKEOVER_ACQUIRED", takeover["result_code"])

    def test_stale_holder_cannot_commit_renew_or_release_after_takeover(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        primary = self._request(role="primary", now=1000)
        acquired = registry.acquire(primary)
        successor = self._request(role="successor", now=1035)
        takeover = registry.takeover(successor, acquired)
        stale_commit = registry.can_commit(self._request(role="primary", now=1036), acquired)
        self.assertEqual("STALE_FENCING_TOKEN", stale_commit["result_code"])
        self.assertEqual("REJECT_COMMIT", stale_commit["decision_action"])
        stale_renew = registry.renew(self._request(role="primary", now=1036), acquired)
        self.assertEqual("STALE_FENCING_TOKEN", stale_renew["result_code"])
        stale_release = registry.release(self._request(role="primary", now=1036), acquired)
        self.assertEqual("STALE_FENCING_TOKEN", stale_release["result_code"])
        current_commit = registry.can_commit(
            self._request(role="successor", now=1036), takeover
        )
        self.assertEqual("COMMIT_ALLOWED", current_commit["decision_action"])
        self.assertEqual("锁凭证有效", current_commit["human_status"]["label_zh"])

    def test_matching_release_is_idempotent_and_removes_the_whole_lock_set(self):
        module = self._module()
        registry = module.IsolatedLockRegistry(self._contract())
        request = self._request(now=1000)
        acquired = registry.acquire(request)
        released = registry.release(self._request(now=1011), acquired)
        self.assertEqual("LOCK_SET_RELEASED", released["result_code"])
        self.assertEqual("RELEASED", released["decision_action"])
        self.assertEqual(
            {key: version + 1 for key, version in acquired["lock_versions"].items()},
            released["lock_versions"],
        )
        self.assertEqual({}, registry.snapshot()["locks"])
        self.assertEqual(released["lock_versions"], registry.snapshot()["lock_versions"])
        replay = registry.release(self._request(now=1011), acquired)
        self.assertEqual(released, replay)
        reacquired = registry.acquire(self._request(now=1012))
        self.assertEqual(released["fencing_token"] + 1, reacquired["fencing_token"])
        self.assertEqual(
            {key: version + 1 for key, version in released["lock_versions"].items()},
            reacquired["lock_versions"],
        )

    def test_invalid_contract_request_and_unknown_nested_fields_fail_closed(self):
        module = self._module()
        valid = self._contract()
        tampered = copy.deepcopy(valid)
        tampered["policy"]["unknown_nested_field"] = True
        self.assertFalse(all(module.evaluate_contract(tampered).values()))
        registry = module.IsolatedLockRegistry(valid)
        invalid = self._request(now=1000)
        invalid["resource_identity_ref"] = "/Users/linzezhang/Downloads/IDS_MetaData/raw"
        result = registry.acquire(invalid)
        self.assertEqual("INVALID_CONTROL_REQUEST", result["result_code"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertNotIn("IDS_MetaData", json.dumps(result, ensure_ascii=False))
        self.assertEqual({}, registry.snapshot()["locks"])
        malformed_key = self._request(now=1000)
        malformed_key["idempotency_key"] = "idempotency:sha256:not-a-digest"
        malformed_result = registry.acquire(malformed_key)
        self.assertEqual("INVALID_CONTROL_REQUEST", malformed_result["result_code"])
        self.assertEqual({}, registry.snapshot()["locks"])

    def test_report_executes_real_control_slice_without_forbidden_side_effects(self):
        report = self._module().build_stage041_phase2_report()
        self.assertTrue(report["phase2_slice_valid"], report)
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertTrue(all(report["slice_checks"].values()), report)
        self.assertEqual("IDS-STAGE041-P3-GATE", report["next_gate"])
        self.assertTrue(report["parameter_values_assigned"])
        self.assertTrue(report["isolated_lock_decision_runtime_performed"])
        for key in (
            "database_connection_performed",
            "persistent_lock_write_performed",
            "runtime_output_written",
            "raw_metadata_content_accessed",
            "fake_ids_business_data_used",
            "real_ids_business_job_created",
            "automatic_resume_performed",
            "crash_recovery_runtime_performed",
            "cleanup_runtime_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(flag=key):
                self.assertFalse(report[key])

    def test_phase1_remains_valid_and_governance_stops_at_phase3_gate(self):
        self.assertTrue(self._phase1_module().build_stage041_phase1_report()["phase1_contract_valid"])
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('status: "stage041_phase2_completed"', batch)
        self.assertIn('      - "Phase 1"', batch)
        self.assertIn('      - "Phase 2"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE041-P3"', batch)
        self.assertIn('push_allowed: false', batch)
        self.assertIn('current_stage_id: "IDS-STAGE041"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE041-P2"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE041-P3-GATE"', roadmap)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE041-P2-20260717-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE041-P2", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-041"], matching[0]["acceptance_ids"])


if __name__ == "__main__":
    unittest.main()
