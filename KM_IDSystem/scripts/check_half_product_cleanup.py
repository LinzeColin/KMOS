#!/usr/bin/env python3
"""Validate the STAGE-044 Phase 1 half-product cleanup contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Mapping
from zipfile import ZipFile


CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
    "stage044_half_product_cleanup_contract.json"
)
STATE_MODEL_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/job_state_model/"
    "stage037_job_state_model_index.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "5cdcf2b0f6d22b44f74330e5fe55541b78141ea8400243a5e44992ef908b5730"
)

EXPECTED_SOURCE = {
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

EXPECTED_PREDECESSOR = {
    "stage043_review_commit": "e7835134550e2776f0949870fcaf7d7b9a54bd01",
    "stage043_review_tree": "9550bdf529cb7b48198fac18a68983325abd1af4",
    "stage043_review_parent": "641009f26df2119cf21bf33640789f4928d94037",
    "stage043_review_status": "completed_reviewed_local",
    "stage043_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

EXPECTED_UPSTREAM = {
    "stage029_closeout_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE029_PHASE4_CLOSEOUT.md",
        "sha256": "f7d3da08219e2c25f0c7088fedd0e4695155fbcf1f9a3be1d6ccb1bce4fb67fe",
    },
    "stage037_scope_boundary_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE037_PHASE1_SCOPE_BOUNDARY.md",
        "sha256": "e692bfb2f4786c076135888731c6eca6ce0f342a8fa19c1334394ca2d3db3730",
    },
    "stage037_state_index_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    },
    "stage038_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
            "stage038_worker_queue_delivery_contract.json"
        ),
        "sha256": "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4",
    },
    "stage039_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
            "stage039_retry_dead_letter_delivery_contract.json"
        ),
        "sha256": "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b",
    },
    "stage040_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
            "stage040_backpressure_delivery_contract.json"
        ),
        "sha256": "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    },
    "stage041_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_delivery_contract.json"
        ),
        "sha256": "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84",
    },
    "stage042_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
            "stage042_automatic_lifecycle_delivery_contract.json"
        ),
        "sha256": "b3406b6542256a4a7f8b015bf11271822496bdad8129b787dbbf0044035311f3",
    },
    "stage043_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_delivery_contract.json"
        ),
        "sha256": "4d991341c09784c11ca816977727f2d8ab568559f10b6b3fc1c9edb688fdc863",
    },
    "stage043_review_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE043_STAGE_REVIEW.md",
        "sha256": "0d7b1ae2985d458ae6c5031f8d992c7b6e5e7187bfc551606ed695345a86be45",
    },
}

EXPECTED_JOB_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "DEAD_LETTERED",
    "CANCELLED",
]
EXPECTED_TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
EXPECTED_ACTIVE_STATES = ["CLAIMED", "RUNNING", "PAUSE_REQUESTED"]
EXPECTED_CANDIDATE_STATES = ["FAILED", "DEAD_LETTERED", "CANCELLED"]
EXPECTED_BLOCKED_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED",
]
EXPECTED_ELIGIBLE_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
EXPECTED_PROTECTED_CLASSES = [
    "ORIGINAL_RAW_DATA", "SOURCE_FILE", "SOURCE_DATABASE", "RUNTIME_DATABASE",
    "FACT_SOURCE", "MANIFEST", "EVIDENCE_LEDGER", "AUDIT_LOG",
    "REPORT_SNAPSHOT", "DELIVERED_REPORT", "ACTIVE_INDEX",
    "VALIDATED_RETRY_CHECKPOINT", "OWNER_HELD_ARTIFACT", "SUCCEEDED_JOB_OUTPUT",
]
EXPECTED_PAUSE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed", "raw_metadata_content_accessed",
    "fake_ids_business_data_used", "real_ids_business_job_created",
    "queue_runtime_performed", "worker_runtime_performed",
    "retry_scheduler_performed", "backpressure_runtime_performed",
    "production_lock_runtime_performed", "automatic_lifecycle_runtime_performed",
    "process_crash_recovery_performed", "cleanup_scan_performed",
    "cleanup_candidate_evaluation_performed", "writer_quiescence_probe_performed",
    "filesystem_traversal_performed", "delete_operation_started",
    "unlinkat_called", "cleanup_runtime_performed",
    "protected_ref_delete_performed", "state_transition_performed",
    "terminal_result_changed", "persistent_state_write_performed",
    "database_connection_performed", "schema_change_performed",
    "runtime_output_written", "production_runtime_activation_performed",
    "whole_stage_review_performed", "batch_review_performed",
    "github_upload_allowed", "app_reinstall_allowed",
}

EXPECTED_ROOT_KEYS = {
    "schema_version", "stage", "phase", "task_id", "acceptance_id",
    "local_code", "domain", "entrance", "pursuing_goal",
    "cleanup_contract_id", "contract_state", "execution_ready", "next_gate",
    "source_binding", "predecessor_binding", "upstream_bindings",
    "state_and_worker_authority", "cleanup_candidate_contract",
    "eligibility_contract", "protected_artifact_contract",
    "resource_pause_contract", "namespace_lock_contract", "path_safety_contract",
    "deletion_protocol_contract", "idempotency_and_audit_contract",
    "parameter_contract", "human_status_projection", "phase2_entry_gate",
    "runtime_boundary", "rollback_contract", "truth_flags",
}

EXPECTED_NESTED_KEYS = {
    "source_binding": set(EXPECTED_SOURCE),
    "predecessor_binding": set(EXPECTED_PREDECESSOR),
    "upstream_bindings": set(EXPECTED_UPSTREAM),
    "state_and_worker_authority": {
        "state_model_version", "job_states", "terminal_states",
        "active_execution_states", "runtime_owners", "new_job_state_introduced",
        "worker_runtime_allowed", "state_mutation_allowed",
        "terminal_history_reopen_allowed",
    },
    "cleanup_candidate_contract": {
        "mode", "required_fields", "immutable_lstat_identity_fields",
        "attempt_owned_required", "approved_staging_or_cache_root_required",
        "raw_content_allowed", "candidate_record_write_allowed",
    },
    "eligibility_contract": {
        "eligible_artifact_classes", "candidate_job_states", "blocked_job_states",
        "attempt_ownership_proved", "approved_root_identity_proved",
        "root_relative_path_proved", "rebuildable_true_required",
        "cleanup_manifest_required", "no_retention_or_legal_or_owner_hold_required",
        "no_durable_reference_required", "writer_quiescence_required",
        "resource_gates_pass_required", "exclusive_namespace_lock_required",
        "lstat_identity_stable_required", "unknown_or_missing_evidence_action",
        "delete_allowed",
    },
    "protected_artifact_contract": {
        "protected_artifact_classes", "durable_evidence_reference_blocks_cleanup",
        "validated_retry_checkpoint_blocks_cleanup",
        "owner_or_legal_hold_blocks_cleanup", "succeeded_job_output_blocks_cleanup",
        "override_allowed", "delete_allowed",
    },
    "resource_pause_contract": {
        "mandatory_pause_signals", "blocked_signal_action",
        "fresh_owner_observation_required", "all_resource_gates_must_pass",
        "automatic_resume_allowed", "resource_probe_performed",
    },
    "namespace_lock_contract": {
        "lock_runtime_owner", "lock_key_fields",
        "exclusive_lock_required_before_validation",
        "producer_and_cleanup_leases_absent_or_fenced_required",
        "creation_rename_replacement_delete_excluded_while_locked",
        "lock_held_through_future_unlinkat", "unmanaged_namespace_action",
        "advisory_only_lock_action", "cannot_prove_quiescence_action",
        "production_lock_acquisition_allowed",
    },
    "path_safety_contract": {
        "root_relative_path_only", "absolute_path_blocked",
        "parent_traversal_blocked", "symlink_target_blocked",
        "symlink_component_blocked", "trusted_root_handle",
        "future_traversal_api", "future_nofollow_flag", "future_delete_api",
        "same_directory_descriptor_required",
        "canonical_containment_revalidation_required", "filesystem_traversal_allowed",
    },
    "deletion_protocol_contract": {
        "protocol_state", "ordered_future_steps",
        "toctou_or_identity_mismatch_action", "delete_allowed",
        "unlinkat_called", "directory_mutation_allowed",
    },
    "idempotency_and_audit_contract": {
        "idempotency_key_fields", "canonical_key_formula",
        "exact_replay_returns_original_decision",
        "same_key_payload_conflict_fails_closed", "separate_cleanup_audit_required",
        "terminal_job_result_change_allowed", "audit_write_allowed",
    },
    "parameter_contract": {
        "deferred_parameter_names", "required_future_fields",
        "numeric_values_assigned", "production_calibrated",
        "implicit_defaults_allowed", "status",
    },
    "human_status_projection": {
        "CLEANUP_CANDIDATE_REVIEW_REQUIRED", "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
        "CLEANUP_BLOCKED_RESOURCE", "CLEANUP_BLOCKED_PROTECTED",
        "CLEANUP_CONTRACT_READY_DELETE_DISABLED",
    },
    "phase2_entry_gate": {
        "required_gate", "required_conditions", "phase2_must_run_separately",
        "execution_ready", "delete_allowed", "push_allowed",
    },
    "runtime_boundary": {
        "mode", "cleanup_scan_allowed", "candidate_evaluation_allowed",
        "filesystem_traversal_allowed", "lock_acquisition_allowed",
        "delete_allowed", "audit_write_allowed", "runtime_output_allowed",
        "production_runtime_allowed",
    },
    "rollback_contract": {"steps", "destructive_rollback_allowed"},
    "truth_flags": {"taskpack_source_read_performed"} | FALSE_TRUTH_FLAGS,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _live_source_valid() -> bool:
    try:
        archive = Path(EXPECTED_SOURCE["source_archive_path"])
        if (
            not archive.is_file()
            or _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]
            or _sha256(ROADMAP_SOURCE_PATH) != EXPECTED_SOURCE["roadmap_sha256"]
            or _sha256(INSTRUCTIONS_SOURCE_PATH)
            != EXPECTED_SOURCE["instructions_sha256"]
        ):
            return False
        with ZipFile(archive) as source_zip:
            matches = [
                name
                for name in source_zip.namelist()
                if name == EXPECTED_SOURCE["source_member"]
            ]
            if len(matches) != 1:
                return False
            member_hash = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
        return member_hash == EXPECTED_SOURCE["source_member_sha256"]
    except (OSError, KeyError, ValueError):
        return False


def _predecessor_valid(repo_root: Path) -> bool:
    try:
        observed = subprocess.check_output(
            [
                "git", "show", "-s", "--format=%H%n%T%n%P",
                EXPECTED_PREDECESSOR["stage043_review_commit"],
            ],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        ancestor = subprocess.run(
            [
                "git", "merge-base", "--is-ancestor",
                EXPECTED_PREDECESSOR["stage043_review_commit"], "HEAD",
            ],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return observed == [
        EXPECTED_PREDECESSOR["stage043_review_commit"],
        EXPECTED_PREDECESSOR["stage043_review_tree"],
        EXPECTED_PREDECESSOR["stage043_review_parent"],
    ] and ancestor


def _upstream_valid(repo_root: Path, bindings: Any) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    try:
        return all(
            (repo_root / item["ref"]).is_file()
            and _sha256(repo_root / item["ref"]) == item["sha256"]
            for item in EXPECTED_UPSTREAM.values()
        )
    except (OSError, KeyError, TypeError):
        return False


def _state_authority_valid(root: Path, authority: Any) -> bool:
    if not isinstance(authority, Mapping):
        return False
    try:
        state_model = json.loads(
            (root / STATE_MODEL_RELATIVE).read_text(encoding="utf-8")
        )["state_model"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return (
        authority.get("state_model_version") == state_model.get("state_model_version")
        and authority.get("job_states") == state_model.get("job_states")
        and authority.get("terminal_states") == state_model.get("terminal_states")
        and authority.get("job_states") == EXPECTED_JOB_STATES
        and authority.get("terminal_states") == EXPECTED_TERMINAL_STATES
        and authority.get("active_execution_states") == EXPECTED_ACTIVE_STATES
        and authority.get("runtime_owners")
        == {
            "queue_and_worker": "STAGE-038",
            "retry_and_dead_letter": "STAGE-039",
            "backpressure_and_resource_pause": "STAGE-040",
            "lock_lease_and_fencing": "STAGE-041",
            "automatic_lifecycle": "STAGE-042",
            "worker_crash_recovery": "STAGE-043",
            "half_product_cleanup": "STAGE-044",
        }
        and authority.get("new_job_state_introduced") is False
        and authority.get("worker_runtime_allowed") is False
        and authority.get("state_mutation_allowed") is False
        and authority.get("terminal_history_reopen_allowed") is False
    )


def evaluate_contract(contract: Any, root: Path = None) -> Dict[str, bool]:
    root = root or Path(__file__).resolve().parents[1]
    repo_root = root.parent
    value: Mapping[str, Any] = contract if isinstance(contract, Mapping) else {}
    checks: Dict[str, bool] = {}
    checks["root_exact_shape"] = (
        isinstance(contract, Mapping) and set(value) == EXPECTED_ROOT_KEYS
    )
    checks["nested_exact_shapes"] = all(
        isinstance(value.get(name), Mapping)
        and set(value[name]) == expected
        for name, expected in EXPECTED_NESTED_KEYS.items()
    )
    checks["canonical_contract_identity"] = (
        isinstance(contract, Mapping)
        and _canonical_sha256(value) == EXPECTED_CANONICAL_CONTRACT_SHA256
    )
    checks["identity"] = (
        value.get("schema_version") == "ids.stage044.half_product_cleanup.phase1.v1"
        and value.get("stage") == "STAGE-044"
        and value.get("phase") == "Phase 1"
        and value.get("task_id") == "IDS-V0_1-STAGE044-P1"
        and value.get("acceptance_id") == "ACC-STAGE-044"
        and value.get("local_code") == "D07-S008"
        and value.get("domain") == "D07"
        and value.get("entrance") == "IDS_SYSTEM_OPERATIONS"
        and value.get("cleanup_contract_id") == "ids.half_product_cleanup.v0_1.p1"
        and value.get("contract_state")
        == "PHASE1_ENGINEERING_CONTRACT_DELETE_DISABLED"
        and value.get("execution_ready") is False
        and value.get("next_gate") == "IDS-STAGE044-P2-GATE"
    )
    checks["source_binding"] = value.get("source_binding") == EXPECTED_SOURCE
    checks["source_live"] = _live_source_valid()
    checks["predecessor_binding"] = (
        value.get("predecessor_binding") == EXPECTED_PREDECESSOR
        and _predecessor_valid(repo_root)
    )
    checks["upstream_bindings"] = _upstream_valid(
        repo_root, value.get("upstream_bindings")
    )
    checks["state_and_worker_authority"] = _state_authority_valid(
        root, value.get("state_and_worker_authority")
    )
    candidate = value.get("cleanup_candidate_contract", {})
    checks["cleanup_candidate_boundary"] = (
        isinstance(candidate, Mapping)
        and candidate.get("mode") == "REFERENCE_ONLY_STATIC_SCHEMA"
        and candidate.get("immutable_lstat_identity_fields")
        == ["st_dev", "st_ino", "file_type"]
        and candidate.get("attempt_owned_required") is True
        and candidate.get("approved_staging_or_cache_root_required") is True
        and candidate.get("raw_content_allowed") is False
        and candidate.get("candidate_record_write_allowed") is False
    )
    eligibility = value.get("eligibility_contract", {})
    checks["eligibility_fail_closed"] = (
        isinstance(eligibility, Mapping)
        and eligibility.get("eligible_artifact_classes") == EXPECTED_ELIGIBLE_CLASSES
        and eligibility.get("candidate_job_states")
        == EXPECTED_CANDIDATE_STATES
        and eligibility.get("blocked_job_states")
        == EXPECTED_BLOCKED_STATES
        and eligibility.get("unknown_or_missing_evidence_action") == "BLOCK_CLEANUP"
        and eligibility.get("delete_allowed") is False
    )
    protected = value.get("protected_artifact_contract", {})
    checks["protected_artifacts_immutable"] = (
        isinstance(protected, Mapping)
        and protected.get("protected_artifact_classes") == EXPECTED_PROTECTED_CLASSES
        and protected.get("durable_evidence_reference_blocks_cleanup") is True
        and protected.get("validated_retry_checkpoint_blocks_cleanup") is True
        and protected.get("owner_or_legal_hold_blocks_cleanup") is True
        and protected.get("succeeded_job_output_blocks_cleanup") is True
        and protected.get("override_allowed") is False
        and protected.get("delete_allowed") is False
    )
    pause = value.get("resource_pause_contract", {})
    checks["resource_pause_fail_closed"] = (
        isinstance(pause, Mapping)
        and pause.get("mandatory_pause_signals") == EXPECTED_PAUSE_SIGNALS
        and pause.get("blocked_signal_action") == "BLOCK_CLEANUP"
        and pause.get("fresh_owner_observation_required") is True
        and pause.get("all_resource_gates_must_pass") is True
        and pause.get("automatic_resume_allowed") is False
        and pause.get("resource_probe_performed") is False
    )
    namespace = value.get("namespace_lock_contract", {})
    checks["namespace_lock_and_quiescence"] = (
        isinstance(namespace, Mapping)
        and namespace.get("lock_runtime_owner") == "STAGE-041"
        and namespace.get("lock_key_fields")
        == ["approved_root_id", "candidate_parent_directory"]
        and namespace.get("exclusive_lock_required_before_validation") is True
        and namespace.get("producer_and_cleanup_leases_absent_or_fenced_required") is True
        and namespace.get("creation_rename_replacement_delete_excluded_while_locked") is True
        and namespace.get("lock_held_through_future_unlinkat") is True
        and namespace.get("unmanaged_namespace_action") == "BLOCK_CLEANUP"
        and namespace.get("advisory_only_lock_action") == "BLOCK_CLEANUP"
        and namespace.get("cannot_prove_quiescence_action") == "BLOCK_CLEANUP"
        and namespace.get("production_lock_acquisition_allowed") is False
    )
    path_safety = value.get("path_safety_contract", {})
    checks["dirfd_nofollow_path_safety"] = (
        isinstance(path_safety, Mapping)
        and path_safety.get("root_relative_path_only") is True
        and path_safety.get("absolute_path_blocked") is True
        and path_safety.get("parent_traversal_blocked") is True
        and path_safety.get("symlink_target_blocked") is True
        and path_safety.get("symlink_component_blocked") is True
        and path_safety.get("trusted_root_handle") == "dirfd"
        and path_safety.get("future_traversal_api") == "openat"
        and path_safety.get("future_nofollow_flag") == "O_NOFOLLOW"
        and path_safety.get("future_delete_api") == "unlinkat"
        and path_safety.get("same_directory_descriptor_required") is True
        and path_safety.get("canonical_containment_revalidation_required") is True
        and path_safety.get("filesystem_traversal_allowed") is False
    )
    deletion = value.get("deletion_protocol_contract", {})
    checks["future_deletion_protocol_delete_disabled"] = (
        isinstance(deletion, Mapping)
        and deletion.get("protocol_state")
        == "DOCUMENTED_FOR_FUTURE_PHASE_NOT_EXECUTABLE"
        and deletion.get("toctou_or_identity_mismatch_action") == "BLOCK_CLEANUP"
        and deletion.get("delete_allowed") is False
        and deletion.get("unlinkat_called") is False
        and deletion.get("directory_mutation_allowed") is False
    )
    idempotency = value.get("idempotency_and_audit_contract", {})
    checks["idempotency_audit_terminal_immutability"] = (
        isinstance(idempotency, Mapping)
        and idempotency.get("exact_replay_returns_original_decision") is True
        and idempotency.get("same_key_payload_conflict_fails_closed") is True
        and idempotency.get("separate_cleanup_audit_required") is True
        and idempotency.get("terminal_job_result_change_allowed") is False
        and idempotency.get("audit_write_allowed") is False
    )
    parameters = value.get("parameter_contract", {})
    checks["parameters_deferred"] = (
        isinstance(parameters, Mapping)
        and parameters.get("numeric_values_assigned") is False
        and parameters.get("production_calibrated") is False
        and parameters.get("implicit_defaults_allowed") is False
        and parameters.get("status") == "DEFERRED_TO_SEPARATE_PHASE2"
    )
    phase2 = value.get("phase2_entry_gate", {})
    checks["phase2_separate_and_locked"] = (
        isinstance(phase2, Mapping)
        and phase2.get("required_gate") == "IDS-STAGE044-P2-GATE"
        and phase2.get("phase2_must_run_separately") is True
        and phase2.get("execution_ready") is False
        and phase2.get("delete_allowed") is False
        and phase2.get("push_allowed") is False
    )
    runtime = value.get("runtime_boundary", {})
    checks["runtime_disabled"] = (
        isinstance(runtime, Mapping)
        and runtime.get("mode") == "STATIC_CONTRACT_VALIDATION_ONLY"
        and all(
            runtime.get(name) is False
            for name in (
                "cleanup_scan_allowed", "candidate_evaluation_allowed",
                "filesystem_traversal_allowed", "lock_acquisition_allowed",
                "delete_allowed", "audit_write_allowed", "runtime_output_allowed",
                "production_runtime_allowed",
            )
        )
    )
    rollback = value.get("rollback_contract", {})
    checks["rollback_nondestructive"] = (
        isinstance(rollback, Mapping)
        and rollback.get("destructive_rollback_allowed") is False
        and isinstance(rollback.get("steps"), list)
        and len(rollback.get("steps", [])) == 5
    )
    truth = value.get("truth_flags", {})
    checks["truth_flags"] = (
        isinstance(truth, Mapping)
        and truth.get("taskpack_source_read_performed") is True
        and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
    )
    return checks


def build_stage044_phase1_report(root: Path = None) -> Dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    contract_path = root / CONTRACT_RELATIVE
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        contract = {}
    checks = evaluate_contract(contract, root=root)
    valid = bool(checks) and all(checks.values())
    return {
        "schema_version": "ids.stage044.half_product_cleanup.phase1.report.v1",
        "stage": "STAGE-044",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE044-P1",
        "acceptance_id": "ACC-STAGE-044",
        "valid": valid,
        "result": "PASS_PHASE1_CONTRACT_DELETE_DISABLED" if valid else "FAIL_CLOSED",
        "contract_state": contract.get("contract_state") if isinstance(contract, dict) else None,
        "next_gate": "IDS-STAGE044-P2-GATE" if valid else "IDS-STAGE044-P1-GATE",
        "execution_ready": False,
        "delete_allowed": False,
        "checks": checks,
        "required_job_state_count": len(EXPECTED_JOB_STATES),
        "required_terminal_state_count": len(EXPECTED_TERMINAL_STATES),
        "eligible_artifact_class_count": len(EXPECTED_ELIGIBLE_CLASSES),
        "protected_artifact_class_count": len(EXPECTED_PROTECTED_CLASSES),
        "numeric_policy_values_assigned": False,
        "cleanup_scan_performed": False,
        "filesystem_traversal_performed": False,
        "delete_operation_started": False,
        "unlinkat_called": False,
        "state_transition_performed": False,
        "raw_metadata_content_accessed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage044_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
