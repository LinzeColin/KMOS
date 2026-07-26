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
CONTRACT = BASE / "worker_crash_recovery" / "stage043_worker_crash_recovery_contract.json"
ENTRY = BASE / "STAGE043_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_worker_crash_recovery.py"

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
    "source_member_integrity": "OK",
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
    "stage042_review_commit": "ba248f66ce993a726cb12547ae1c772ab1228bfa",
    "stage042_review_tree": "0e13164deeaa491fb98384fad5158a89658a2f77",
    "stage042_review_parent": "2c489d049d73cd632e905c7af1b39ba662a2139b",
    "stage042_review_status": "completed_reviewed_local",
    "stage042_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

UPSTREAM_BINDINGS = {
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage038_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
        "stage038_worker_queue_delivery_contract.json",
        "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4",
    ),
    "stage039_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
        "stage039_retry_dead_letter_delivery_contract.json",
        "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b",
    ),
    "stage040_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_delivery_contract.json",
        "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    ),
    "stage041_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_delivery_contract.json",
        "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84",
    ),
    "stage042_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_delivery_contract.json",
        "b3406b6542256a4a7f8b015bf11271822496bdad8129b787dbbf0044035311f3",
    ),
    "stage042_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE042_STAGE_REVIEW.md",
        "2ca9ef6107d54ccad624e46f3a6efda8832d00872964773bab6f70326803302d",
    ),
}

JOB_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "DEAD_LETTERED",
    "CANCELLED",
]
TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "worker_restart_performed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


class Stage043WorkerCrashRecoveryPhase1Tests(unittest.TestCase):
    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage043_worker_crash_recovery_checker", CHECKER
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

    def test_source_and_predecessor_bindings_are_exact(self):
        contract = self._contract()
        self.assertTrue(self._checker()._live_source_valid())
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["predecessor_binding"])
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P",
             PREDECESSOR_BINDING["stage042_review_commit"]],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(
            [PREDECESSOR_BINDING["stage042_review_commit"],
             PREDECESSOR_BINDING["stage042_review_tree"],
             PREDECESSOR_BINDING["stage042_review_parent"]],
            observed,
        )

    def test_all_upstream_hashes_are_exact(self):
        contract = self._contract()
        self.assertEqual(set(UPSTREAM_BINDINGS), set(contract["upstream_bindings"]))
        for key, (relative, expected_hash) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                self.assertEqual(
                    {"ref": relative, "sha256": expected_hash},
                    contract["upstream_bindings"][key],
                )
                observed = hashlib.sha256(
                    (REPO_ROOT / relative).read_bytes()
                ).hexdigest()
                self.assertEqual(expected_hash, observed)

    def test_state_graph_is_reused_and_terminal_history_is_immutable(self):
        contract = self._contract()
        authority = contract["state_authority"]
        self.assertEqual("ids.job_state.v1", authority["state_model_version"])
        self.assertEqual(JOB_STATES, authority["job_states"])
        self.assertEqual(TERMINAL_STATES, authority["terminal_states"])
        self.assertFalse(authority["new_state_introduced"])
        self.assertFalse(authority["terminal_history_reopen_allowed"])
        self.assertFalse(authority["direct_running_to_running_resume_allowed"])
        self.assertFalse(authority["direct_active_to_queued_recovery_allowed"])

    def test_crash_detection_is_evidence_bound_and_non_runtime(self):
        contract = self._contract()
        detection = contract["crash_detection_contract"]
        self.assertEqual("STATIC_EVIDENCE_EVALUATION_ONLY", detection["mode"])
        self.assertIn("worker_instance_id", detection["required_evidence_fields"])
        self.assertIn("worker_generation", detection["required_evidence_fields"])
        self.assertIn("expected_state_version", detection["required_evidence_fields"])
        self.assertIn("fencing_token", detection["required_evidence_fields"])
        self.assertEqual(
            "REQUIRE_MANUAL_REVIEW", detection["unknown_or_stale_evidence_action"]
        )
        self.assertFalse(detection["process_probe_performed"])

    def test_recovery_candidates_are_guarded_and_owner_bounded(self):
        contract = self._contract()
        recovery = contract["recovery_decision_contract"]
        self.assertEqual("STATIC_CANDIDATE_ONLY", recovery["decision_mode"])
        self.assertEqual("STAGE-039", recovery["retry_and_dead_letter_owner"])
        self.assertEqual("STAGE-041", recovery["lock_lease_fencing_owner"])
        self.assertEqual("STAGE-044", recovery["cleanup_execution_owner"])
        self.assertIn(
            "LOST_WORKER_FENCED", recovery["checkpoint_resume_required_conditions"]
        )
        self.assertIn(
            "FRESH_ADMISSION_CLAIM_LOCK_CYCLE",
            recovery["checkpoint_resume_required_conditions"],
        )
        self.assertFalse(recovery["blind_continue_allowed"])
        self.assertFalse(recovery["state_mutation_allowed"])
        self.assertFalse(recovery["successful_recovery_observed"])

    def test_resource_pause_idempotency_fencing_and_cleanup_fail_closed(self):
        contract = self._contract()
        pause = contract["resource_pause_contract"]
        self.assertEqual(
            ["EXTERNAL_DRIVE_OFFLINE", "DISK_SPACE_INSUFFICIENT",
             "EXTERNAL_API_BUDGET_INSUFFICIENT"],
            pause["mandatory_pause_signals"],
        )
        self.assertFalse(pause["automatic_resume_allowed"])
        identity = contract["idempotency_contract"]
        self.assertTrue(identity["exact_replay_returns_original_decision"])
        self.assertTrue(identity["same_key_payload_conflict_fails_closed"])
        fencing = contract["lock_and_fencing_contract"]
        self.assertTrue(fencing["lost_worker_must_be_fenced"])
        self.assertFalse(fencing["takeover_or_lock_mutation_allowed"])
        partial = contract["partial_output_contract"]
        self.assertEqual("STAGE-044", partial["cleanup_execution_owner"])
        self.assertFalse(partial["delete_allowed"])
        self.assertEqual(
            ["FACT_SOURCE", "MANIFEST", "EVIDENCE_LEDGER",
             "REPORT_SNAPSHOT", "AUDIT_LOG"],
            partial["protected_artifact_classes"],
        )

    def test_parameters_and_truth_flags_make_no_runtime_claim(self):
        contract = self._contract()
        parameters = contract["parameter_contract"]
        self.assertFalse(parameters["numeric_values_assigned"])
        self.assertEqual("DEFERRED_TO_SEPARATE_PHASE2", parameters["status"])
        self.assertTrue(contract["truth_flags"]["taskpack_source_read_performed"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(flag=name):
                self.assertIn(name, contract["truth_flags"])
                self.assertFalse(contract["truth_flags"][name])

    def test_checker_accepts_exact_contract_and_rejects_tampering(self):
        checker = self._checker()
        original = self._contract()
        checks = checker.evaluate_contract(original)
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()), checks)
        mutations = []
        for mutate in (
            lambda item: item["state_authority"].update(
                {"direct_running_to_running_resume_allowed": True}
            ),
            lambda item: item["recovery_decision_contract"].update(
                {"state_mutation_allowed": True}
            ),
            lambda item: item["partial_output_contract"].update(
                {"delete_allowed": True}
            ),
            lambda item: item["parameter_contract"].update(
                {"numeric_values_assigned": True}
            ),
            lambda item: item["truth_flags"].update(
                {"process_crash_recovery_performed": True}
            ),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["unexpected_field"] = True
        mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertFalse(all(checker.evaluate_contract(candidate).values()))
        non_mapping = checker.evaluate_contract([])
        self.assertFalse(non_mapping["root_exact_shape"])
        self.assertFalse(non_mapping["nested_exact_shapes"])
        self.assertFalse(all(non_mapping.values()))

    def test_checker_report_is_phase1_only(self):
        report = self._checker().build_stage043_phase1_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual("PASS_PHASE1_CONTRACT_RUNTIME_DISABLED", report["result"])
        self.assertEqual("IDS-STAGE043-P2-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["push_allowed"])

    def test_docs_governance_event_and_upload_lock_stop_at_phase1(self):
        docs = ENTRY.read_text(encoding="utf-8") + BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "Phase 2 must run separately", "NO_PHASE2", "NO_CRASH_RECOVERY_RUNTIME",
            "NO_PROCESS_TERMINATION", "NO_STATE_MUTATION", "NO_CLEANUP_DELETE",
            "NO_RAW_METADATA_ACCESS", "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD", "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage043_phase1_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE043-P2"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE043"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE043-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE043-P2-GATE"', roadmap)
        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line]
        matching = [item for item in events if item.get("event_id") ==
                    "EVT-IDS-V0_1-STAGE043-P1-20260718-001"]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE043-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-043"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
