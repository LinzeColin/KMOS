import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = (
    BASE
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_contract.json"
)
ENTRY = BASE / "STAGE042_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_automatic_lifecycle.py"

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
        "STAGE-042_自动运行、暂停、恢复与关闭.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08"
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
    "stage041_review_commit": (
        "f6b30f8a55d60f1b37b9d57ee55587149ad43876"
    ),
    "stage041_review_tree": (
        "af262c4139f652d937534d58e826fe28a236f2a4"
    ),
    "stage041_review_parent": (
        "68a89e9c3d1fbb3eae347fe71f1bbbbf7bc9ddc2"
    ),
    "stage041_review_status": "completed_reviewed_local",
    "stage041_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

UPSTREAM_BINDINGS = {
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "job_state_model/stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
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
    "stage041_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "lock_registry/stage041_lock_registry_delivery_contract.json",
        "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84",
    ),
    "stage041_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE041_STAGE_REVIEW.md",
        "68ab244b3bf6e5f287164c8c738469425612de69a81cc128a734b19f3cb754d0",
    ),
}

JOB_STATES = [
    "CREATED",
    "QUEUED",
    "CLAIMED",
    "RUNNING",
    "PAUSE_REQUESTED",
    "PAUSED",
    "RETRY_WAIT",
    "SUCCEEDED",
    "FAILED",
    "DEAD_LETTERED",
    "CANCELLED",
]

AUTOMATIC_TRANSITION_PATHS = {
    "AUTO_START": [
        ["QUEUED", "CLAIMED"],
        ["CLAIMED", "RUNNING"],
    ],
    "AUTO_PAUSE": [
        ["QUEUED", "PAUSED"],
        ["CLAIMED", "PAUSE_REQUESTED"],
        ["RUNNING", "PAUSE_REQUESTED"],
        ["PAUSE_REQUESTED", "PAUSED"],
        ["RETRY_WAIT", "PAUSED"],
    ],
    "AUTO_RESUME": [
        ["PAUSED", "QUEUED"],
        ["RETRY_WAIT", "QUEUED"],
    ],
    "SAFE_CLOSE": [
        ["CREATED", "CANCELLED"],
        ["QUEUED", "CANCELLED"],
        ["PAUSE_REQUESTED", "CANCELLED"],
        ["PAUSED", "CANCELLED"],
        ["RETRY_WAIT", "CANCELLED"],
    ],
}

FORBIDDEN_SHORTCUTS = [
    ["QUEUED", "RUNNING"],
    ["PAUSED", "RUNNING"],
    ["RUNNING", "PAUSED"],
    ["RUNNING", "CANCELLED"],
    ["FAILED", "QUEUED"],
    ["DEAD_LETTERED", "QUEUED"],
]

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
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
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


class Stage042AutomaticLifecyclePhase1Tests(unittest.TestCase):
    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage042_automatic_lifecycle_checker", CHECKER
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
        self.assertFalse(contract["truth_flags"]["raw_metadata_content_accessed"])

    def test_predecessor_commit_tree_and_upstream_hashes_are_exact(self):
        contract = self._contract()
        self.assertEqual(
            PREDECESSOR_BINDING,
            contract["predecessor_binding"],
        )
        observed = subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%H%n%T%n%P",
                PREDECESSOR_BINDING["stage041_review_commit"],
            ],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(
            [
                PREDECESSOR_BINDING["stage041_review_commit"],
                PREDECESSOR_BINDING["stage041_review_tree"],
                PREDECESSOR_BINDING["stage041_review_parent"],
            ],
            observed,
        )
        self.assertEqual(set(UPSTREAM_BINDINGS), set(contract["upstream_bindings"]))
        for key, (relative, expected_sha) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                binding = contract["upstream_bindings"][key]
                self.assertEqual({"ref": relative, "sha256": expected_sha}, binding)
                observed_sha = hashlib.sha256(
                    (REPO_ROOT / relative).read_bytes()
                ).hexdigest()
                self.assertEqual(expected_sha, observed_sha)

    def test_inherits_exact_state_model_without_shortcuts(self):
        lifecycle = self._contract()["lifecycle_state_contract"]
        self.assertEqual("ids.job_state.v1", lifecycle["state_model_version"])
        self.assertEqual(JOB_STATES, lifecycle["job_states"])
        self.assertEqual(
            ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"],
            lifecycle["terminal_states"],
        )
        self.assertFalse(lifecycle["new_job_states_allowed"])
        self.assertFalse(lifecycle["terminal_state_mutation_allowed"])
        self.assertEqual(
            AUTOMATIC_TRANSITION_PATHS,
            lifecycle["automatic_transition_paths"],
        )
        self.assertEqual(
            FORBIDDEN_SHORTCUTS,
            lifecycle["forbidden_shortcuts"],
        )
        self.assertTrue(lifecycle["all_paths_must_exist_upstream"])

    def test_start_pause_and_resume_guards_fail_closed(self):
        contract = self._contract()
        start = contract["automatic_start_contract"]
        pause = contract["automatic_pause_contract"]
        resume = contract["automatic_resume_contract"]
        self.assertEqual(
            ["QUEUED->CLAIMED", "CLAIMED->RUNNING"],
            start["required_transition_sequence"],
        )
        self.assertTrue(start["fresh_admission_required"])
        self.assertTrue(start["claim_lease_and_lock_required"])
        self.assertTrue(start["live_lease_and_fencing_required"])
        self.assertFalse(start["direct_queued_to_running_allowed"])
        self.assertEqual(
            [
                "EXTERNAL_DRIVE_OFFLINE",
                "DISK_SPACE_INSUFFICIENT",
                "EXTERNAL_API_BUDGET_INSUFFICIENT",
            ],
            pause["mandatory_resource_pause_signals"],
        )
        self.assertEqual(
            "PAUSE_REQUESTED",
            pause["active_job_first_target_state"],
        )
        self.assertTrue(pause["checkpoint_or_quarantine_required"])
        self.assertFalse(pause["running_to_paused_shortcut_allowed"])
        self.assertEqual("PAUSED->QUEUED", resume["resume_transition"])
        self.assertTrue(resume["owner_revalidation_required"])
        self.assertTrue(resume["fresh_resource_observation_required"])
        self.assertTrue(resume["new_admission_and_lock_cycle_required"])
        self.assertFalse(resume["direct_resume_to_running_allowed"])
        self.assertFalse(resume["process_crash_recovery_allowed"])

    def test_worker_retry_pressure_and_lock_ownership_are_preserved(self):
        boundaries = self._contract()["upstream_runtime_boundaries"]
        self.assertEqual("STAGE-038", boundaries["queue_and_worker_transport_owner"])
        self.assertEqual("STAGE-039", boundaries["retry_and_dead_letter_owner"])
        self.assertEqual("STAGE-040", boundaries["backpressure_owner"])
        self.assertEqual("STAGE-041", boundaries["lock_lease_and_fencing_owner"])
        self.assertEqual("STAGE-042", boundaries["automatic_lifecycle_owner"])
        self.assertEqual("STAGE-043", boundaries["process_crash_recovery_owner"])
        self.assertEqual("STAGE-044", boundaries["cleanup_execution_owner"])
        self.assertFalse(boundaries["worker_spawn_or_termination_allowed"])
        self.assertFalse(boundaries["retry_budget_consumed_by_pause_or_resume"])
        self.assertFalse(boundaries["lock_or_fencing_bypass_allowed"])
        self.assertFalse(boundaries["cleanup_delete_allowed"])

    def test_idempotency_and_reference_only_evidence_are_exact(self):
        contract = self._contract()
        idempotency = contract["lifecycle_idempotency_contract"]
        evidence = contract["lifecycle_evidence_contract"]
        self.assertEqual(
            "SHA256_JOB_EXPECTED_STATE_VERSION_ACTION_POLICY_EVIDENCE",
            idempotency["request_key_derivation"],
        )
        self.assertTrue(idempotency["exact_replay_returns_existing_decision"])
        self.assertEqual(
            "REJECT_LIFECYCLE_REQUEST_CONFLICT",
            idempotency["same_key_different_payload_action"],
        )
        self.assertTrue(evidence["reference_only"])
        self.assertFalse(evidence["raw_path_allowed"])
        self.assertFalse(evidence["raw_payload_allowed"])
        self.assertFalse(evidence["secret_material_allowed"])
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW",
            evidence["unknown_or_stale_evidence_action"],
        )
        self.assertIn("audit_ref", evidence["required_fields"])
        self.assertIn("checkpoint_ref", evidence["required_fields"])
        self.assertIn("fencing_token", evidence["required_fields"])

    def test_safe_shutdown_and_cleanup_candidate_never_delete(self):
        contract = self._contract()
        shutdown = contract["safe_shutdown_contract"]
        cleanup = contract["cleanup_candidate_contract"]
        self.assertEqual(
            [
                "STOP_NEW_LIFECYCLE_DECISIONS",
                "STOP_NEW_ADMISSION_AND_CLAIMS",
                "REQUEST_ACTIVE_JOB_PAUSE",
                "WAIT_FOR_CHECKPOINT_OR_QUARANTINE",
                "FREEZE_RETRY_AND_RESUME_ELIGIBILITY",
                "RELEASE_MATCHING_ACTIVE_LOCKS",
                "VERIFY_ZERO_ACTIVE_LOCKS",
                "CLOSE_REVIEWED_WORKER_TRANSPORT",
                "PRESERVE_AUDIT_CHECKPOINT_AND_EVIDENCE_REFS",
                "VERIFY_NO_DELETE_PERSISTENCE_OR_RUNTIME_OUTPUT",
            ],
            shutdown["ordered_steps"],
        )
        self.assertFalse(shutdown["process_termination_allowed"])
        self.assertFalse(shutdown["crash_recovery_claimed"])
        self.assertEqual("STAGE-044", cleanup["runtime_owner"])
        self.assertTrue(cleanup["candidate_only"])
        self.assertFalse(cleanup["delete_execution_allowed"])
        self.assertEqual(
            ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"],
            cleanup["eligible_artifact_classes"],
        )
        self.assertEqual(
            [
                "FACT_SOURCE",
                "MANIFEST",
                "EVIDENCE_LEDGER",
                "REPORT_SNAPSHOT",
                "AUDIT_LOG",
            ],
            cleanup["protected_artifact_classes"],
        )

    def test_parameters_truth_flags_and_phase2_gate_are_deferred(self):
        contract = self._contract()
        parameters = contract["parameter_contract"]
        truth = contract["truth_flags"]
        gate = contract["phase2_entry_gate"]
        self.assertFalse(parameters["numeric_values_assigned"])
        self.assertFalse(parameters["implicit_default_allowed"])
        self.assertFalse(parameters["production_calibrated"])
        self.assertEqual(
            [
                "lifecycle_tick_interval",
                "resume_stability_window",
                "checkpoint_wait_timeout",
                "graceful_shutdown_timeout",
                "cleanup_scan_interval",
            ],
            parameters["deferred_parameters"],
        )
        self.assertEqual(FALSE_TRUTH_FLAGS | {"taskpack_source_read_performed"}, set(truth))
        self.assertTrue(truth["taskpack_source_read_performed"])
        self.assertTrue(all(truth[key] is False for key in FALSE_TRUTH_FLAGS))
        self.assertTrue(gate["entry_authorized"])
        self.assertEqual("IDS-V0_1-STAGE042-P2", gate["required_task_id"])
        self.assertEqual("IDS-STAGE042-P2-GATE", gate["required_gate"])
        self.assertTrue(gate["separate_run_required"])

    def test_checker_reports_contract_only_and_rejects_tampering(self):
        checker = self._checker()
        report = checker.build_stage042_phase1_report()
        self.assertTrue(report["phase1_contract_valid"], report)
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertEqual("IDS-STAGE042-P2-GATE", report["next_gate"])
        self.assertEqual(
            "PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED",
            report["contract_state"],
        )
        for key in FALSE_TRUTH_FLAGS:
            with self.subTest(flag=key):
                self.assertFalse(report[key])

        original = self._contract()
        mutations = []
        for mutate in (
            lambda item: item.update({"unknown_root_field": True}),
            lambda item: item["lifecycle_state_contract"].update(
                {"new_job_states_allowed": True}
            ),
            lambda item: item["automatic_start_contract"].update(
                {"direct_queued_to_running_allowed": True}
            ),
            lambda item: item["automatic_resume_contract"].update(
                {"owner_revalidation_required": False}
            ),
            lambda item: item["upstream_runtime_boundaries"].update(
                {"lock_or_fencing_bypass_allowed": True}
            ),
            lambda item: item["cleanup_candidate_contract"].update(
                {"delete_execution_allowed": True}
            ),
            lambda item: item["parameter_contract"].update(
                {"numeric_values_assigned": True}
            ),
            lambda item: item["truth_flags"].update(
                {"automatic_resume_performed": True}
            ),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                checks = checker.evaluate_contract(candidate)
                self.assertFalse(all(checks.values()), checks)

    def test_docs_governance_event_and_upload_lock_stop_at_phase1(self):
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
            "NO_AUTOMATIC_LIFECYCLE_RUNTIME",
            "NO_PROCESS_CRASH_RECOVERY",
            "NO_CLEANUP_DELETE",
            "NO_RAW_METADATA_ACCESS",
            "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, entry + boundary)
        self.assertIn('status: "stage042_phase1_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE042-P2"', batch)
        self.assertIn('push_allowed: false', batch)
        self.assertIn('current_stage_id: "IDS-STAGE042"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE042-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE042-P2-GATE"', roadmap)
        matching = [
            item
            for item in events
            if item.get("event_id")
            == "EVT-IDS-V0_1-STAGE042-P1-20260718-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE042-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-042"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
