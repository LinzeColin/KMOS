import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "half_product_cleanup" / "stage044_half_product_cleanup_contract.json"
ENTRY = BASE / "STAGE044_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE044_PHASE1_HALF_PRODUCT_CLEANUP_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_half_product_cleanup.py"

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
        "STAGE-044_半成品输出清理.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53"
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
    "stage043_review_commit": "e7835134550e2776f0949870fcaf7d7b9a54bd01",
    "stage043_review_tree": "9550bdf529cb7b48198fac18a68983325abd1af4",
    "stage043_review_parent": "641009f26df2119cf21bf33640789f4928d94037",
    "stage043_review_status": "completed_reviewed_local",
    "stage043_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

UPSTREAM_BINDINGS = {
    "stage029_closeout_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE029_PHASE4_CLOSEOUT.md",
        "f7d3da08219e2c25f0c7088fedd0e4695155fbcf1f9a3be1d6ccb1bce4fb67fe",
    ),
    "stage037_scope_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE037_PHASE1_SCOPE_BOUNDARY.md",
        "e692bfb2f4786c076135888731c6eca6ce0f342a8fa19c1334394ca2d3db3730",
    ),
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
    "stage043_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_delivery_contract.json",
        "4d991341c09784c11ca816977727f2d8ab568559f10b6b3fc1c9edb688fdc863",
    ),
    "stage043_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE043_STAGE_REVIEW.md",
        "0d7b1ae2985d458ae6c5031f8d992c7b6e5e7187bfc551606ed695345a86be45",
    ),
}

JOB_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "DEAD_LETTERED",
    "CANCELLED",
]
TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
ACTIVE_STATES = ["CLAIMED", "RUNNING", "PAUSE_REQUESTED"]
ELIGIBLE_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
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
REQUIRED_CANDIDATE_FIELDS = [
    "cleanup_request_id",
    "job_id",
    "attempt_id",
    "creator_job_id",
    "approved_root_id",
    "approved_root_canonical_identity",
    "root_relative_path",
    "artifact_class",
    "rebuildable",
    "retention_policy_ref",
    "legal_hold_status",
    "owner_hold_status",
    "cleanup_manifest_ref",
    "immutable_lstat_identity",
    "durable_reference_status",
    "writer_quiescence_evidence_ref",
    "resource_gate_evidence_ref",
]
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
    "process_crash_recovery_performed",
    "cleanup_scan_performed",
    "cleanup_candidate_evaluation_performed",
    "writer_quiescence_probe_performed",
    "filesystem_traversal_performed",
    "delete_operation_started",
    "unlinkat_called",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "state_transition_performed",
    "terminal_result_changed",
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


class Stage044HalfProductCleanupTests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        spec = importlib.util.spec_from_file_location("stage044_cleanup_checker", CHECKER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase1_artifacts_exist(self):
        for path in (CONTRACT, ENTRY, BOUNDARY, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_identity_source_predecessor_and_upstream_bindings_are_exact(self):
        contract = self._contract()
        self.assertEqual("ids.stage044.half_product_cleanup.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-044", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE044-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-044", contract["acceptance_id"])
        self.assertEqual("D07-S008", contract["local_code"])
        self.assertEqual("IDS-STAGE044-P2-GATE", contract["next_gate"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["predecessor_binding"])
        observed = {
            name: (item["ref"], item["sha256"])
            for name, item in contract["upstream_bindings"].items()
        }
        self.assertEqual(UPSTREAM_BINDINGS, observed)

    def test_state_and_worker_authority_reuses_reviewed_control_plane(self):
        authority = self._contract()["state_and_worker_authority"]
        self.assertEqual("ids.job_state.v1", authority["state_model_version"])
        self.assertEqual(JOB_STATES, authority["job_states"])
        self.assertEqual(TERMINAL_STATES, authority["terminal_states"])
        self.assertEqual(ACTIVE_STATES, authority["active_execution_states"])
        self.assertEqual(
            {
                "queue_and_worker": "STAGE-038",
                "retry_and_dead_letter": "STAGE-039",
                "backpressure_and_resource_pause": "STAGE-040",
                "lock_lease_and_fencing": "STAGE-041",
                "automatic_lifecycle": "STAGE-042",
                "worker_crash_recovery": "STAGE-043",
                "half_product_cleanup": "STAGE-044",
            },
            authority["runtime_owners"],
        )
        self.assertFalse(authority["new_job_state_introduced"])
        self.assertFalse(authority["worker_runtime_allowed"])
        self.assertFalse(authority["state_mutation_allowed"])
        self.assertFalse(authority["terminal_history_reopen_allowed"])

    def test_candidate_contract_binds_attempt_root_path_and_lstat_identity(self):
        candidate = self._contract()["cleanup_candidate_contract"]
        self.assertEqual(REQUIRED_CANDIDATE_FIELDS, candidate["required_fields"])
        self.assertEqual(["st_dev", "st_ino", "file_type"], candidate["immutable_lstat_identity_fields"])
        self.assertEqual("REFERENCE_ONLY_STATIC_SCHEMA", candidate["mode"])
        self.assertTrue(candidate["attempt_owned_required"])
        self.assertTrue(candidate["approved_staging_or_cache_root_required"])
        self.assertFalse(candidate["raw_content_allowed"])
        self.assertFalse(candidate["candidate_record_write_allowed"])

    def test_eligibility_is_narrow_and_unknowns_fail_closed(self):
        eligibility = self._contract()["eligibility_contract"]
        self.assertEqual(ELIGIBLE_CLASSES, eligibility["eligible_artifact_classes"])
        self.assertEqual(
            ["FAILED", "DEAD_LETTERED", "CANCELLED"],
            eligibility["candidate_job_states"],
        )
        self.assertEqual(
            [
                "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
                "PAUSED", "RETRY_WAIT", "SUCCEEDED",
            ],
            eligibility["blocked_job_states"],
        )
        for field in (
            "attempt_ownership_proved",
            "approved_root_identity_proved",
            "root_relative_path_proved",
            "rebuildable_true_required",
            "cleanup_manifest_required",
            "no_retention_or_legal_or_owner_hold_required",
            "no_durable_reference_required",
            "writer_quiescence_required",
            "resource_gates_pass_required",
            "exclusive_namespace_lock_required",
            "lstat_identity_stable_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(eligibility[field])
        self.assertEqual("BLOCK_CLEANUP", eligibility["unknown_or_missing_evidence_action"])
        self.assertFalse(eligibility["delete_allowed"])

    def test_protected_artifacts_and_success_outputs_can_never_be_targets(self):
        protected = self._contract()["protected_artifact_contract"]
        self.assertEqual(PROTECTED_CLASSES, protected["protected_artifact_classes"])
        self.assertTrue(protected["durable_evidence_reference_blocks_cleanup"])
        self.assertTrue(protected["validated_retry_checkpoint_blocks_cleanup"])
        self.assertTrue(protected["owner_or_legal_hold_blocks_cleanup"])
        self.assertTrue(protected["succeeded_job_output_blocks_cleanup"])
        self.assertFalse(protected["override_allowed"])
        self.assertFalse(protected["delete_allowed"])

    def test_resource_pressure_pauses_cleanup_and_never_auto_resumes(self):
        pause = self._contract()["resource_pause_contract"]
        self.assertEqual(
            [
                "EXTERNAL_DRIVE_OFFLINE",
                "DISK_SPACE_INSUFFICIENT",
                "EXTERNAL_API_BUDGET_INSUFFICIENT",
            ],
            pause["mandatory_pause_signals"],
        )
        self.assertEqual("BLOCK_CLEANUP", pause["blocked_signal_action"])
        self.assertTrue(pause["fresh_owner_observation_required"])
        self.assertTrue(pause["all_resource_gates_must_pass"])
        self.assertFalse(pause["automatic_resume_allowed"])
        self.assertFalse(pause["resource_probe_performed"])

    def test_namespace_lock_and_writer_quiescence_are_mandatory(self):
        namespace = self._contract()["namespace_lock_contract"]
        self.assertEqual("STAGE-041", namespace["lock_runtime_owner"])
        self.assertEqual(
            ["approved_root_id", "candidate_parent_directory"],
            namespace["lock_key_fields"],
        )
        self.assertTrue(namespace["exclusive_lock_required_before_validation"])
        self.assertTrue(namespace["producer_and_cleanup_leases_absent_or_fenced_required"])
        self.assertTrue(namespace["creation_rename_replacement_delete_excluded_while_locked"])
        self.assertTrue(namespace["lock_held_through_future_unlinkat"])
        self.assertEqual("BLOCK_CLEANUP", namespace["unmanaged_namespace_action"])
        self.assertEqual("BLOCK_CLEANUP", namespace["advisory_only_lock_action"])
        self.assertEqual("BLOCK_CLEANUP", namespace["cannot_prove_quiescence_action"])
        self.assertFalse(namespace["production_lock_acquisition_allowed"])

    def test_path_safety_requires_dirfd_nofollow_and_same_descriptor(self):
        path_safety = self._contract()["path_safety_contract"]
        self.assertTrue(path_safety["root_relative_path_only"])
        self.assertTrue(path_safety["absolute_path_blocked"])
        self.assertTrue(path_safety["parent_traversal_blocked"])
        self.assertTrue(path_safety["symlink_target_blocked"])
        self.assertTrue(path_safety["symlink_component_blocked"])
        self.assertEqual("dirfd", path_safety["trusted_root_handle"])
        self.assertEqual("openat", path_safety["future_traversal_api"])
        self.assertEqual("O_NOFOLLOW", path_safety["future_nofollow_flag"])
        self.assertEqual("unlinkat", path_safety["future_delete_api"])
        self.assertTrue(path_safety["same_directory_descriptor_required"])
        self.assertTrue(path_safety["canonical_containment_revalidation_required"])
        self.assertFalse(path_safety["filesystem_traversal_allowed"])

    def test_future_delete_protocol_revalidates_identity_but_phase1_deletes_nothing(self):
        protocol = self._contract()["deletion_protocol_contract"]
        self.assertEqual(
            "DOCUMENTED_FOR_FUTURE_PHASE_NOT_EXECUTABLE",
            protocol["protocol_state"],
        )
        self.assertEqual(
            [
                "ACQUIRE_EXCLUSIVE_NAMESPACE_LOCK",
                "PROVE_WRITER_QUIESCENCE",
                "OPEN_TRUSTED_APPROVED_ROOT_DIRFD",
                "TRAVERSE_ROOT_RELATIVE_PATH_WITH_OPENAT_O_NOFOLLOW",
                "REVALIDATE_CANONICAL_CONTAINMENT",
                "REVALIDATE_OWNER_ATTEMPT_ARTIFACT_CLASS_AND_FILE_TYPE",
                "REVALIDATE_ST_DEV_ST_INO_AND_CLEANUP_MANIFEST",
                "REVALIDATE_RETENTION_HOLD_DURABLE_REFS_AND_RESOURCE_GATES",
                "UNLINKAT_RELATIVE_TO_SAME_DIRECTORY_DESCRIPTOR",
                "APPEND_SEPARATE_CLEANUP_AUDIT",
                "RELEASE_NAMESPACE_LOCK",
            ],
            protocol["ordered_future_steps"],
        )
        self.assertEqual("BLOCK_CLEANUP", protocol["toctou_or_identity_mismatch_action"])
        self.assertFalse(protocol["delete_allowed"])
        self.assertFalse(protocol["unlinkat_called"])
        self.assertFalse(protocol["directory_mutation_allowed"])

    def test_idempotency_audit_parameters_and_truth_flags_are_fail_closed(self):
        contract = self._contract()
        identity = contract["idempotency_and_audit_contract"]
        self.assertEqual(
            [
                "cleanup_request_id",
                "job_id",
                "attempt_id",
                "approved_root_id",
                "root_relative_path",
                "st_dev",
                "st_ino",
                "cleanup_manifest_ref",
            ],
            identity["idempotency_key_fields"],
        )
        self.assertTrue(identity["exact_replay_returns_original_decision"])
        self.assertTrue(identity["same_key_payload_conflict_fails_closed"])
        self.assertTrue(identity["separate_cleanup_audit_required"])
        self.assertFalse(identity["terminal_job_result_change_allowed"])
        self.assertFalse(identity["audit_write_allowed"])
        parameters = contract["parameter_contract"]
        self.assertFalse(parameters["numeric_values_assigned"])
        self.assertFalse(parameters["production_calibrated"])
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
            lambda item: item["eligibility_contract"].update({"delete_allowed": True}),
            lambda item: item["protected_artifact_contract"].update({"override_allowed": True}),
            lambda item: item["namespace_lock_contract"].update({"lock_held_through_future_unlinkat": False}),
            lambda item: item["path_safety_contract"].update({"symlink_component_blocked": False}),
            lambda item: item["deletion_protocol_contract"].update({"unlinkat_called": True}),
            lambda item: item["truth_flags"].update({"cleanup_runtime_performed": True}),
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

    def test_report_docs_and_governance_stop_at_phase1(self):
        report = self._checker().build_stage044_phase1_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual("PASS_PHASE1_CONTRACT_DELETE_DISABLED", report["result"])
        self.assertEqual("IDS-STAGE044-P2-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["delete_allowed"])
        self.assertFalse(report["push_allowed"])
        docs = ENTRY.read_text(encoding="utf-8") + BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "Phase 2 must run separately",
            "NO_PHASE2",
            "NO_CLEANUP_SCAN",
            "NO_FILESYSTEM_TRAVERSAL",
            "NO_DELETE",
            "NO_STATE_MUTATION",
            "NO_RAW_METADATA_ACCESS",
            "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage044_phase1_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE044-P2"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE044"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE044-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE044-P2-GATE"', roadmap)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE044-P1-20260719-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE044-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-044"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
