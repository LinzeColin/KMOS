import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "lock_registry" / "stage041_lock_registry_contract.json"
ENTRY = BASE / "STAGE041_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_lock_registry.py"

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
        "STAGE-041_锁注册与竞态控制.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

UPSTREAM_BINDINGS = {
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "job_state_model/stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage038_scenarios_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "worker_queue_baseline/stage038_worker_queue_scenarios.json",
        "0ec9f1a0de6ec24d64d4108214ea426f9171b15eebdd6c3c60693fade62f2961",
    ),
    "stage038_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "worker_queue_baseline/stage038_worker_queue_delivery_contract.json",
        "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4",
    ),
    "stage039_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "retry_dead_letter/stage039_retry_dead_letter_delivery_contract.json",
        "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b",
    ),
    "stage040_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "backpressure_policy/stage040_backpressure_delivery_contract.json",
        "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    ),
    "previous_batch_lock_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "BATCH031_040_UPLOAD_LOCK.yaml",
        "ad235a242c5833e2e6243227cc8fe7ca9223a75d5ae98a8b732b3b4418477940",
    ),
}

OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "INDEX_SWITCH",
    "REPORT_GENERATION",
]

REGISTRY_FIELDS = [
    "lock_key",
    "lock_namespace",
    "resource_identity_ref",
    "operation_scope",
    "holder_job_id",
    "holder_attempt_id",
    "lease_owner_ref",
    "lease_expires_at",
    "fencing_token",
    "lock_version",
    "acquired_at",
    "renewed_at",
    "released_at",
    "release_reason",
    "audit_ref",
    "checkpoint_ref",
    "policy_version",
]


class Stage041LockRegistryTests(unittest.TestCase):
    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage041_lock_registry_checker", CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase1_artifacts_exist(self):
        for path in (CONTRACT, ENTRY, BOUNDARY, BATCH, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing Phase 1 artifact: {path}")

    def test_source_binding_is_exact_and_unique(self):
        contract = self._contract()
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertTrue(contract["truth_flags"]["taskpack_source_read_performed"])
        self.assertFalse(contract["truth_flags"]["ids_business_source_read_performed"])
        self.assertFalse(contract["truth_flags"]["raw_metadata_content_accessed"])

    def test_upstream_bindings_match_tracked_sources(self):
        contract = self._contract()
        self.assertEqual(set(UPSTREAM_BINDINGS), set(contract["upstream_bindings"]))
        for key, (relative, expected_sha) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                binding = contract["upstream_bindings"][key]
                self.assertEqual(relative, binding["ref"])
                self.assertEqual(expected_sha, binding["sha256"])
                observed = hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()
                self.assertEqual(expected_sha, observed)

    def test_operation_scope_preserves_stage038_conflict_baseline(self):
        scope = self._contract()["operation_scope_contract"]
        self.assertEqual(OPERATION_FAMILIES, list(scope["operation_families"]))
        self.assertEqual(
            ["ARCHIVE", "PARSE", "INDEX", "REPORT"],
            scope["stage038_same_source_conflict_job_types"],
        )
        self.assertEqual(
            "RESOURCE_CONFLICT_ACTIVE", scope["stage038_conflict_result_code"]
        )
        self.assertEqual(
            "SOURCE_PIPELINE", scope["mandatory_shared_guard_namespace"]
        )
        self.assertTrue(scope["all_operation_families_require_shared_guard"])
        self.assertFalse(scope["stage038_baseline_narrowing_allowed"])
        expected_job_types = {
            "FILE_PROCESSING": ["PARSE"],
            "ARCHIVE_EXTRACTION": ["ARCHIVE"],
            "INDEX_BUILD": ["INDEX"],
            "INDEX_SWITCH": ["INDEX"],
            "REPORT_GENERATION": ["REPORT"],
        }
        for family, job_types in expected_job_types.items():
            self.assertEqual(job_types, scope["operation_families"][family]["job_types"])

    def test_registry_and_key_contract_are_reference_only(self):
        contract = self._contract()
        registry = contract["registry_record_contract"]
        keys = contract["lock_key_contract"]
        self.assertEqual(REGISTRY_FIELDS, registry["required_fields"])
        self.assertTrue(registry["reference_only"])
        self.assertFalse(registry["raw_path_allowed"])
        self.assertFalse(registry["raw_payload_allowed"])
        self.assertEqual(
            "SHA256_CANONICAL_NAMESPACE_AND_STABLE_RESOURCE_IDENTITY_REF",
            keys["derivation"],
        )
        self.assertEqual("LEXICOGRAPHIC_LOCK_KEY", keys["multi_lock_order"])
        self.assertTrue(keys["stable_normalized_reference_required"])
        self.assertFalse(keys["source_content_read_required"])
        self.assertFalse(keys["raw_path_in_key_allowed"])

    def test_acquisition_lease_fencing_and_release_fail_closed(self):
        contract = self._contract()
        acquisition = contract["acquisition_contract"]
        lease = contract["lease_contract"]
        fencing = contract["fencing_contract"]
        release = contract["release_contract"]
        self.assertEqual("ALL_OR_NONE_CAS", acquisition["multi_lock_atomicity"])
        self.assertFalse(acquisition["partial_lock_retention_allowed"])
        self.assertEqual("REQUIRE_MANUAL_REVIEW", acquisition["unknown_evidence_action"])
        self.assertTrue(lease["single_active_holder_per_lock_key"])
        self.assertTrue(lease["renewal_requires_same_holder_attempt_and_token"])
        self.assertFalse(lease["expiry_observation_alone_grants_lock"])
        self.assertTrue(lease["takeover_atomically_advances_fence_and_version"])
        self.assertTrue(fencing["token_monotonic"])
        self.assertEqual(
            ["output", "job_state", "checkpoint", "evidence"],
            fencing["guarded_commit_surfaces"],
        )
        self.assertFalse(fencing["stale_holder_commit_allowed"])
        self.assertFalse(fencing["stale_holder_release_allowed"])
        self.assertTrue(release["matching_identity_token_release_idempotent"])
        self.assertEqual("REJECT_STALE_RELEASE", release["stale_release_action"])

    def test_idempotency_conflict_retry_and_cleanup_boundaries(self):
        contract = self._contract()
        idempotency = contract["idempotency_contract"]
        conflict = contract["conflict_contract"]
        retry = contract["retry_boundary"]
        cleanup = contract["partial_output_cleanup_boundary"]
        self.assertEqual(
            "SHA256_TASK_INPUT_JOB_TYPE", idempotency["job_identity_derivation"]
        )
        self.assertEqual(
            "SHA256_JOB_ATTEMPT_LOCK_KEY", idempotency["lock_operation_derivation"]
        )
        self.assertTrue(idempotency["replay_returns_existing_decision"])
        self.assertFalse(conflict["queue_record_created"])
        self.assertFalse(conflict["operation_invoked"])
        self.assertFalse(conflict["retry_budget_consumed"])
        self.assertFalse(conflict["partial_lock_retained"])
        self.assertFalse(retry["lock_conflict_consumes_retry"])
        self.assertEqual("STAGE-039", retry["retry_policy_runtime_owner"])
        self.assertEqual("STAGE-044", cleanup["runtime_owner"])
        self.assertFalse(cleanup["cleanup_runtime_performed"])
        self.assertFalse(cleanup["protected_artifact_delete_allowed"])

    def test_parameters_and_later_stage_ownership_are_deferred(self):
        contract = self._contract()
        parameters = contract["parameter_contract"]
        ownership = contract["ownership_matrix"]
        self.assertFalse(parameters["numeric_values_assigned"])
        self.assertEqual(
            [
                "lease_duration",
                "renewal_interval",
                "expiry_grace",
                "acquisition_timeout",
                "maximum_wait",
                "retry_jitter",
                "deadlock_timeout",
            ],
            parameters["deferred_parameters"],
        )
        self.assertEqual(
            [
                "source",
                "rationale",
                "unit",
                "policy_version",
                "validation_evidence",
                "rollback",
            ],
            parameters["phase2_selection_requirements"],
        )
        self.assertFalse(parameters["implicit_default_allowed"])
        self.assertEqual("STAGE-041", ownership["lock_lease_and_fencing_runtime"])
        self.assertEqual("STAGE-042", ownership["automatic_resume_runtime"])
        self.assertEqual("STAGE-043", ownership["crash_recovery_runtime"])
        self.assertEqual("STAGE-044", ownership["cleanup_execution_runtime"])

    def test_checker_reports_contract_only_and_rejects_tampering(self):
        checker = self._checker()
        report = checker.build_stage041_phase1_report()
        self.assertTrue(report["phase1_contract_valid"], report)
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertEqual("IDS-STAGE041-P2-GATE", report["next_gate"])
        self.assertEqual(
            "PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED",
            report["contract_state"],
        )
        for key in (
            "lock_runtime_performed",
            "lease_runtime_performed",
            "fencing_runtime_performed",
            "queue_runtime_performed",
            "worker_runtime_performed",
            "retry_scheduler_performed",
            "automatic_resume_performed",
            "crash_recovery_runtime_performed",
            "cleanup_runtime_performed",
            "database_connection_performed",
            "runtime_output_written",
            "raw_metadata_content_accessed",
            "fake_ids_business_data_used",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(flag=key):
                self.assertFalse(report[key])

        original = self._contract()
        mutations = []
        for mutate in (
            lambda item: item.update({"unknown_root_field": True}),
            lambda item: item["operation_scope_contract"].update(
                {"stage038_baseline_narrowing_allowed": True}
            ),
            lambda item: item["acquisition_contract"].update(
                {"partial_lock_retention_allowed": True}
            ),
            lambda item: item["acquisition_contract"].update(
                {"unknown_nested_field": True}
            ),
            lambda item: item["lease_contract"].update(
                {"expiry_observation_alone_grants_lock": True}
            ),
            lambda item: item["fencing_contract"].update(
                {"stale_holder_commit_allowed": True}
            ),
            lambda item: item["parameter_contract"].update(
                {"numeric_values_assigned": True}
            ),
            lambda item: item["truth_flags"].update(
                {"raw_metadata_content_accessed": True}
            ),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                checks = checker.evaluate_contract(candidate)
                self.assertFalse(all(checks.values()), checks)

    def test_docs_governance_and_event_stop_at_phase1(self):
        entry = ENTRY.read_text(encoding="utf-8")
        boundary = BOUNDARY.read_text(encoding="utf-8")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for marker in (
            "Phase 2 must run separately",
            "NO_PHASE2",
            "NO_LOCK_RUNTIME",
            "NO_LEASE_RUNTIME",
            "NO_FENCING_RUNTIME",
            "NO_RAW_METADATA_ACCESS",
            "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, entry + boundary)
        self.assertIn('status: "stage041_phase1_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE041-P2"', batch)
        self.assertIn('push_allowed: false', batch)
        self.assertIn('current_stage_id: "IDS-STAGE041"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE041-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE041-P2-GATE"', roadmap)
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE041-P1-20260714-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE041-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-041"], matching[0]["acceptance_ids"])


if __name__ == "__main__":
    unittest.main()
