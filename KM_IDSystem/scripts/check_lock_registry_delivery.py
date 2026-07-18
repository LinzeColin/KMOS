#!/usr/bin/env python3
"""Build and validate STAGE-041 Phase 4 isolated closeout evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT_PATH = (
    BASE / "lock_registry/stage041_lock_registry_delivery_contract.json"
)
PHASE2_CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_runtime.py"
PHASE3_CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_scenarios.py"
STAGE040_DELIVERY_CHECKER = PROJECT_ROOT / "scripts/check_backpressure_delivery.py"

TASK_ID = "IDS-V0_1-STAGE041-P4"
ACCEPTANCE_ID = "ACC-STAGE-041"
EXECUTION_MODE = "ISOLATED_NON_PRODUCTION_LOCK_REGISTRY_CLOSEOUT"
VALID_RESULT = "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
PHASE4_GATE = "IDS-STAGE041-P4-GATE"
REVIEW_GATE = "IDS-STAGE041-REVIEW-GATE"
PHASE3_COMMIT = "03677aaec2fe7dbe6780736bf802e6ef555f383d"
PHASE3_KMIDS_TREE = "ac363a93c711ac8bf41d9cb3894e37f3b3f1a405"

OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "INDEX_SWITCH",
    "REPORT_GENERATION",
]
PRESSURE_SIGNALS = [
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
]
CLEANUP_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
CLEANUP_PRECONDITIONS = [
    "APPROVED_ROOT_IDENTITY",
    "ROOT_RELATIVE_PATH",
    "IMMUTABLE_LSTAT_IDENTITY",
    "SYMLINK_BLOCKED",
    "EXCLUSIVE_NAMESPACE_LOCK",
    "WRITER_QUIESCENCE",
    "NO_FOLLOW_TRAVERSAL",
]
AUTOMATIC_LOCK_DECISIONS = [
    "EXACT_IDEMPOTENT_REPLAY",
    "MATCHING_HOLDER_RENEWAL",
    "MATCHING_HOLDER_RELEASE",
]
MANUAL_ACTION_CASES = [
    "STALE_OR_INCOMPLETE_CAS",
    "ACTIVE_SAME_SOURCE_CONFLICT",
    "RESOURCE_GATE_OWNER_REVALIDATION",
    "WORKER_PROCESS_CRASH",
    "PROTECTED_CLEANUP_REQUEST",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "PROCESS_EXIT_WITHOUT_PERSISTENT_STATE",
]
SHUTDOWN_STEPS = [
    "STOP_NEW_LOCK_ACQUISITIONS",
    "FREEZE_RENEW_AND_TAKEOVER",
    "PRESERVE_REFERENCE_ONLY_AUDIT_AND_CHECKPOINT_REFS",
    "RELEASE_MATCHING_ACTIVE_LOCK_SET",
    "VERIFY_ZERO_ACTIVE_LOCKS",
    "VERIFY_TOMBSTONE_VERSIONS_ADVANCED",
    "VERIFY_NO_PERSISTENT_OR_RUNTIME_OUTPUT",
]
RECOVERY_STEPS = [
    "VERIFY_EXACT_SOURCE_POLICY_AND_UPSTREAM_HASHES",
    "REBUILD_ONLY_FROM_CURRENT_AUTHORIZED_EVIDENCE",
    "DO_NOT_RESTORE_MISSING_IN_MEMORY_LOCK_STATE",
    "REJECT_UNKNOWN_STALE_OR_INCOMPLETE_CAS",
    "REQUIRE_OWNER_REVALIDATION_FOR_MANUAL_CASES",
    "DEFER_AUTOMATIC_RESUME_TO_STAGE042",
    "DEFER_PROCESS_CRASH_RECOVERY_TO_STAGE043",
]
ROLLBACK_STEPS = [
    "STOP_ON_INVALID_DELIVERY_CONTRACT",
    "DENY_NEW_LOCK_ACQUISITIONS_REQUIRE_MANUAL_REVIEW",
    "FREEZE_RENEW_AND_TAKEOVER",
    "REVERT_PHASE4_FILES_ONLY",
    "PRESERVE_PHASE1_PHASE3_EVIDENCE",
    "PRESERVE_STAGE037_STAGE040_REVIEWED_EVIDENCE",
    "PRESERVE_RAW_DATA_AND_DURABLE_EVIDENCE",
]
KNOWN_LIMITS = [
    "NO_PERSISTENT_LOCK_REGISTRY",
    "NO_TRUSTED_PRODUCTION_CLOCK_SOURCE",
    "NO_PRODUCTION_QUEUE_OR_WORKER_RUNTIME",
    "NO_PRODUCTION_CALIBRATION",
    "NO_AUTOMATIC_RESUME_OR_LIFECYCLE_RUNTIME",
    "NO_PROCESS_CRASH_RECOVERY",
    "NO_CLEANUP_RUNTIME",
    "NO_DATABASE_OR_RAW_SOURCE_ACCESS",
    "NO_STAGE041_WHOLE_STAGE_REVIEW_IN_THIS_RUN",
    "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS",
]

EXPECTED_SOURCE = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-041_锁注册与竞态控制.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36"
    ),
    "roadmap_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}
EXPECTED_UPSTREAM = {
    "stage037_state_index": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage040_delivery_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_delivery_contract.json",
        "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    ),
    "stage040_delivery_checker": (
        "KM_IDSystem/scripts/check_backpressure_delivery.py",
        "98b39ebc3d27cd6916958c1b46ea23486617d580fba576b1f23273a881d6ec41",
    ),
    "stage040_review_artifact": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE040_STAGE_REVIEW.md",
        "ea1a6dacacc862d66de60883dd10ee2dbf23d3adc72efbf9586ba2ccf6c223f0",
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
    "stage041_phase3_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE041_PHASE3_SCENARIO_VALIDATION.md",
        "9cf6509ea5ef2d1250f98d3065338bb80a014ed25cf263c1650527e08e83cf6f",
    ),
    "stage041_phase3_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage041_lock_registry_scenarios.py",
        "766aacd28398ffaefd16c6c3a00167e3ab317929cf7ff4038f2361f3bb12eb5c",
    ),
}

DELIVERY_CONTRACT = {
    "state_model_version": "ids.job_state.v1",
    "required_job_type_count": 8,
    "required_job_state_count": 11,
    "required_terminal_state_count": 4,
    "required_transition_count": 21,
    "required_pressure_signals": PRESSURE_SIGNALS,
    "failure_retry_log_source": (
        "STAGE039_REVIEWED_PHASE4_ACTUAL_ISOLATED_CONTROL_METADATA"
    ),
    "expected_attempt_count": 3,
    "expected_retry_count": 2,
    "expected_final_state": "DEAD_LETTERED",
    "stage040_delivery_must_be_reviewed_and_valid": True,
    "stage_review_must_run_separately": True,
}
LOCK_LIFECYCLE_CONTRACT = {
    "operation_families": OPERATION_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "expected_primary_acquisitions": 5,
    "expected_exact_replays": 5,
    "expected_resource_conflicts": 25,
    "canonical_all_or_none_required": True,
    "renewal_version_monotonic_required": True,
    "takeover_fence_and_version_monotonic_required": True,
    "stale_cas_and_fence_rejection_required": True,
    "release_tombstone_monotonic_required": True,
    "orderly_release_must_leave_zero_active_locks": True,
    "persistent_lock_write_allowed": False,
}
CLEANUP_ALLOWLIST = {
    "cleanup_eligible_classes": CLEANUP_CLASSES,
    "protected_artifact_classes": PROTECTED_CLASSES,
    "cleanup_manifest_required": True,
    "required_preconditions": CLEANUP_PRECONDITIONS,
    "runtime_owner": "STAGE-044",
    "delete_execution_allowed": False,
}
RECOVERY_HANDLING = {
    "automatic_lock_decision_cases": AUTOMATIC_LOCK_DECISIONS,
    "automatic_recovery_eligible_cases": [],
    "successful_automatic_recovery_cases_observed": [],
    "manual_action_required_cases": MANUAL_ACTION_CASES,
    "automatic_resume_allowed": False,
    "automatic_resume_runtime_owner": "STAGE-042",
    "process_crash_recovery_runtime_owner": "STAGE-043",
}
SAFE_SHUTDOWN_AND_RECOVERY = {
    "shutdown_steps": SHUTDOWN_STEPS,
    "recovery_steps": RECOVERY_STEPS,
    "persistent_lock_state_available_after_exit": False,
    "process_termination_allowed": False,
    "automatic_process_recovery_allowed": False,
}
ROLLBACK_CONTRACT = {
    "steps": ROLLBACK_STEPS,
    "destructive_rollback_allowed": False,
}
REVIEW_GATE_CONTRACT = {
    "next_task_id": "IDS-V0_1-STAGE041-REVIEW",
    "must_run_separately": True,
    "phase4_may_mark_stage_reviewed": False,
    "batch_review_allowed": False,
    "stage042_entry_allowed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}
POSITIVE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_lock_runtime_reexecuted",
    "phase3_lock_scenarios_replayed",
    "reviewed_stage040_delivery_replayed",
    "actual_isolated_orderly_release_performed",
}
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
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "automatic_resume_performed",
    "process_crash_recovery_performed",
    "persistent_lock_write_performed",
    "state_registry_write_performed",
    "database_connection_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "execution_mode",
    "valid_result",
    "contract_state",
    "stage_review_status",
    "next_gate",
    "source_binding",
    "phase3_commit_binding",
    "upstream_bindings",
    "delivery_contract",
    "lock_lifecycle_contract",
    "cleanup_allowlist",
    "recovery_handling",
    "safe_shutdown_and_recovery",
    "rollback_contract",
    "known_limits",
    "owner_feedback_contract",
    "review_gate",
    "truth_flags",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_module() -> Any:
    return _load_module(PHASE2_CHECKER, "stage041_phase2_for_delivery")


def _phase3_module() -> Any:
    return _load_module(PHASE3_CHECKER, "stage041_phase3_for_delivery")


def _stage040_module() -> Any:
    return _load_module(STAGE040_DELIVERY_CHECKER, "stage040_for_stage041_delivery")


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Stage041 Phase4 delivery contract must be an object")
    return value


def _upstream_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != set(EXPECTED_UPSTREAM):
        return False
    for name, (relative, expected_hash) in EXPECTED_UPSTREAM.items():
        binding = value.get(name)
        if binding != {"ref": relative, "sha256": expected_hash}:
            return False
        path = REPO_ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            return False
    return True


def _phase3_commit_is_current(value: Any) -> bool:
    expected = {
        "commit": PHASE3_COMMIT,
        "km_ids_tree": PHASE3_KMIDS_TREE,
        "required_ancestor_of_head": True,
    }
    if value != expected:
        return False
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE3_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        return False
    tree = subprocess.run(
        ["git", "rev-parse", f"{PHASE3_COMMIT}:KM_IDSystem"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return tree.returncode == 0 and tree.stdout.strip() == PHASE3_KMIDS_TREE


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    """Validate the complete P4 shape before any delivery replay is executed."""
    if not isinstance(contract, dict):
        return {"contract_is_object": False}
    owner = contract.get("owner_feedback_contract")
    truth = contract.get("truth_flags")
    checks = {
        "contract_is_object": True,
        "root_shape_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage041.lock_registry.phase4.delivery.v1"
            and contract.get("stage") == "STAGE-041"
            and contract.get("phase") == "Phase 4"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("execution_mode") == EXECUTION_MODE
            and contract.get("valid_result") == VALID_RESULT
            and contract.get("contract_state")
            == "PHASE4_CLOSEOUT_EVIDENCE_ENABLED_PRODUCTION_DISABLED"
            and contract.get("stage_review_status") == "pending_next_run"
            and contract.get("next_gate") == REVIEW_GATE
        ),
        "source_binding_exact": contract.get("source_binding") == EXPECTED_SOURCE,
        "phase3_commit_tree_current": _phase3_commit_is_current(
            contract.get("phase3_commit_binding")
        ),
        "upstream_bindings_current": _upstream_valid(
            contract.get("upstream_bindings")
        ),
        "delivery_contract_exact": (
            contract.get("delivery_contract") == DELIVERY_CONTRACT
        ),
        "lock_lifecycle_contract_exact": (
            contract.get("lock_lifecycle_contract")
            == LOCK_LIFECYCLE_CONTRACT
        ),
        "cleanup_allowlist_exact": (
            contract.get("cleanup_allowlist") == CLEANUP_ALLOWLIST
        ),
        "recovery_handling_exact": (
            contract.get("recovery_handling") == RECOVERY_HANDLING
        ),
        "safe_shutdown_recovery_exact": (
            contract.get("safe_shutdown_and_recovery")
            == SAFE_SHUTDOWN_AND_RECOVERY
        ),
        "rollback_exact": contract.get("rollback_contract") == ROLLBACK_CONTRACT,
        "known_limits_exact": contract.get("known_limits") == KNOWN_LIMITS,
        "owner_feedback_exact": (
            isinstance(owner, dict)
            and set(owner)
            == {
                "status_zh",
                "automatic_eligibility_zh",
                "manual_action_zh",
                "limit_zh",
            }
            and all(isinstance(value, str) and value for value in owner.values())
            and "整阶段复审" in owner["status_zh"]
            and "未观察到自动恢复成功" in owner["automatic_eligibility_zh"]
            and "不是生产运行或生产就绪证明" in owner["limit_zh"]
        ),
        "review_gate_exact": contract.get("review_gate") == REVIEW_GATE_CONTRACT,
        "truth_flags_exact": (
            isinstance(truth, dict)
            and set(truth) == POSITIVE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
            and all(truth.get(name) is True for name in POSITIVE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def _lock_lifecycle_evidence(phase3: Mapping[str, Any]) -> dict[str, Any]:
    scenarios = phase3["scenario_results"]
    matrix = scenarios["same_source_operation_exclusion_matrix"]
    renewal = scenarios["renewal_current_cas_only"]
    takeover = scenarios["expiry_plus_grace_takeover"]
    stale = scenarios["stale_cas_evidence_rejected"]
    release = scenarios["release_tombstone_reacquire"]
    return {
        "operation_families": copy.deepcopy(matrix["operation_families"]),
        "shared_lock_namespace": "SOURCE_PIPELINE",
        "primary_acquisition_count": matrix["primary_acquisition_count"],
        "exact_replay_count": matrix["exact_replay_count"],
        "resource_conflict_count": matrix["resource_conflict_count"],
        "canonical_all_or_none": (
            matrix["partial_lock_retained_count"] == 0
            and matrix["retry_budget_consumed_count"] == 0
            and all(matrix["family_checks"].values())
        ),
        "renewal_version_monotonic": (
            renewal["status"] == "PASS"
            and renewal["every_version_advanced_once"] is True
            and renewal["fence_preserved"] is True
        ),
        "takeover_fence_and_version_monotonic": (
            takeover["status"] == "PASS"
            and takeover["fence_advanced_once"] is True
            and takeover["every_version_advanced_once"] is True
        ),
        "stale_cas_and_fence_rejected": (
            stale["status"] == "PASS"
            and stale["lock_state_unchanged"] is True
            and stale["fence_unchanged"] is True
        ),
        "release_tombstone_monotonic": (
            release["status"] == "PASS"
            and release["release_advanced_every_version"] is True
            and release["reacquire_advanced_every_version"] is True
            and release["fence_advanced_on_reacquire"] is True
        ),
        "phase2_runtime_valid": phase3["phase2_runtime_valid"] is True,
        "phase3_scenarios_valid": phase3["scenario_validation_valid"] is True,
        "persistent_lock_write_performed": False,
    }


def _state_retry_backpressure_evidence(
    stage040: Mapping[str, Any],
) -> dict[str, Any]:
    graph = stage040["state_decision_graph"]
    failure = copy.deepcopy(stage040["failure_retry_log"])
    proof = copy.deepcopy(stage040["backpressure_trigger_proof"])
    return {
        "job_state_graph": {
            "state_model_version": graph["state_model_version"],
            "job_type_count": len(graph["job_types"]),
            "job_state_count": len(graph["job_states"]),
            "terminal_state_count": len(graph["terminal_states"]),
            "allowed_transition_count": graph["allowed_transition_count"],
            "job_types": copy.deepcopy(graph["job_types"]),
            "job_states": copy.deepcopy(graph["job_states"]),
            "terminal_states": copy.deepcopy(graph["terminal_states"]),
            "allowed_transitions": copy.deepcopy(graph["allowed_transitions"]),
        },
        "failure_retry_log": failure,
        "backpressure_trigger_proof": proof,
        "reviewed_stage040_delivery_valid": (
            stage040.get("delivery_contract_valid") is True
            and stage040.get("result") == VALID_RESULT
            and stage040.get("next_gate") == "IDS-STAGE040-REVIEW-GATE"
        ),
    }


def _cleanup_allowlist(
    contract: Mapping[str, Any], phase3: Mapping[str, Any]
) -> dict[str, Any]:
    configured = contract["cleanup_allowlist"]
    protected = phase3["scenario_results"]["protected_cleanup_denied"]
    checks = {
        name: (
            item.get("git_tracked") is True
            and item.get("result_code") == "PROTECTED_ARTIFACT"
            and item.get("delete_allowed") is False
            and item.get("delete_attempted") is False
        )
        for name, item in protected["artifact_results"].items()
    }
    return {
        "cleanup_eligible_classes": copy.deepcopy(
            configured["cleanup_eligible_classes"]
        ),
        "protected_artifact_classes": copy.deepcopy(
            configured["protected_artifact_classes"]
        ),
        "protected_ref_count": len(checks),
        "protected_ref_checks": checks,
        "cleanup_manifest_required": configured["cleanup_manifest_required"],
        "required_preconditions": copy.deepcopy(configured["required_preconditions"]),
        "runtime_owner": configured["runtime_owner"],
        "cleanup_runtime_performed": False,
        "delete_attempt_performed": False,
    }


def _recovery_handling(contract: Mapping[str, Any]) -> dict[str, Any]:
    configured = contract["recovery_handling"]
    return {
        "automatic_lock_decision_cases": copy.deepcopy(
            configured["automatic_lock_decision_cases"]
        ),
        "automatic_recovery_eligible_cases": [],
        "successful_automatic_recovery_cases_observed": [],
        "manual_action_required_cases": copy.deepcopy(
            configured["manual_action_required_cases"]
        ),
        "automatic_resume_allowed": configured["automatic_resume_allowed"],
        "automatic_resume_performed": False,
        "automatic_resume_runtime_owner": configured[
            "automatic_resume_runtime_owner"
        ],
        "process_crash_recovery_performed": False,
        "process_crash_recovery_runtime_owner": configured[
            "process_crash_recovery_runtime_owner"
        ],
    }


def _orderly_lock_shutdown(phase2: Any) -> dict[str, Any]:
    phase2_contract = phase2.load_contract()
    registry = phase2.IsolatedLockRegistry(phase2_contract)
    common = {
        "resource_identity_ref": phase2.CONTROL_REF,
        "operation_family": "FILE_PROCESSING",
        "holder_role": "phase4-closeout",
    }
    acquired = registry.acquire(
        phase2.build_control_request(
            **common, requested_at_epoch_seconds=1000
        )
    )
    renewed = registry.renew(
        phase2.build_control_request(
            **common, requested_at_epoch_seconds=1010
        ),
        acquired,
    )
    released = registry.release(
        phase2.build_control_request(
            **common, requested_at_epoch_seconds=1011
        ),
        renewed,
    )
    after_release = registry.snapshot()
    stale = registry.can_commit(
        phase2.build_control_request(
            **common, requested_at_epoch_seconds=1012
        ),
        renewed,
    )
    renew_advanced = all(
        renewed.get("lock_versions", {}).get(key) == version + 1
        for key, version in acquired.get("lock_versions", {}).items()
    )
    release_advanced = all(
        released.get("lock_versions", {}).get(key) == version + 1
        for key, version in renewed.get("lock_versions", {}).items()
    )
    return {
        "actual_isolated_orderly_release_performed": True,
        "acquire_result_code": acquired.get("result_code"),
        "renew_result_code": renewed.get("result_code"),
        "release_result_code": released.get("result_code"),
        "active_lock_count_after_release": len(after_release.get("locks", {})),
        "tombstone_version_count": len(after_release.get("lock_versions", {})),
        "renew_versions_advanced_once": renew_advanced,
        "release_versions_advanced_once": release_advanced,
        "stale_commit_result_code": stale.get("result_code"),
        "persistent_lock_write_performed": False,
    }


def _safe_shutdown_and_recovery(
    contract: Mapping[str, Any], orderly: Mapping[str, Any]
) -> dict[str, Any]:
    configured = contract["safe_shutdown_and_recovery"]
    return {
        "shutdown_steps": copy.deepcopy(configured["shutdown_steps"]),
        "recovery_steps": copy.deepcopy(configured["recovery_steps"]),
        "zero_active_locks_verified": (
            orderly.get("active_lock_count_after_release") == 0
        ),
        "tombstone_versions_advanced_verified": (
            orderly.get("tombstone_version_count") == 2
            and orderly.get("release_versions_advanced_once") is True
        ),
        "persistent_lock_state_available_after_exit": configured[
            "persistent_lock_state_available_after_exit"
        ],
        "process_termination_performed": False,
        "automatic_process_recovery_performed": False,
    }


def _delivery_checks(
    lifecycle: Mapping[str, Any],
    state_retry: Mapping[str, Any],
    cleanup: Mapping[str, Any],
    recovery: Mapping[str, Any],
    orderly: Mapping[str, Any],
    shutdown: Mapping[str, Any],
) -> dict[str, bool]:
    graph = state_retry.get("job_state_graph", {})
    failure = state_retry.get("failure_retry_log", {})
    return {
        "lock_lifecycle_exact_and_monotonic": (
            lifecycle.get("operation_families") == OPERATION_FAMILIES
            and lifecycle.get("shared_lock_namespace") == "SOURCE_PIPELINE"
            and lifecycle.get("primary_acquisition_count") == 5
            and lifecycle.get("exact_replay_count") == 5
            and lifecycle.get("resource_conflict_count") == 25
            and lifecycle.get("canonical_all_or_none") is True
            and lifecycle.get("renewal_version_monotonic") is True
            and lifecycle.get("takeover_fence_and_version_monotonic") is True
            and lifecycle.get("stale_cas_and_fence_rejected") is True
            and lifecycle.get("release_tombstone_monotonic") is True
            and lifecycle.get("phase2_runtime_valid") is True
            and lifecycle.get("phase3_scenarios_valid") is True
        ),
        "state_retry_backpressure_reviewed": (
            graph.get("state_model_version") == "ids.job_state.v1"
            and graph.get("job_type_count") == 8
            and graph.get("job_state_count") == 11
            and graph.get("terminal_state_count") == 4
            and graph.get("allowed_transition_count") == 21
            and failure.get("attempt_count") == 3
            and failure.get("retry_count") == 2
            and failure.get("final_state") == "DEAD_LETTERED"
            and failure.get("persisted") is False
            and set(state_retry.get("backpressure_trigger_proof", {}))
            == set(PRESSURE_SIGNALS)
            and state_retry.get("reviewed_stage040_delivery_valid") is True
        ),
        "cleanup_allowlist_narrow_and_protected": (
            cleanup.get("cleanup_eligible_classes") == CLEANUP_CLASSES
            and cleanup.get("protected_artifact_classes") == PROTECTED_CLASSES
            and cleanup.get("protected_ref_count") == 5
            and all(cleanup.get("protected_ref_checks", {}).values())
            and cleanup.get("cleanup_manifest_required") is True
            and cleanup.get("runtime_owner") == "STAGE-044"
            and cleanup.get("cleanup_runtime_performed") is False
            and cleanup.get("delete_attempt_performed") is False
        ),
        "automatic_and_manual_handling_truthful": (
            recovery.get("automatic_lock_decision_cases")
            == AUTOMATIC_LOCK_DECISIONS
            and recovery.get("automatic_recovery_eligible_cases") == []
            and recovery.get("successful_automatic_recovery_cases_observed") == []
            and recovery.get("manual_action_required_cases")
            == MANUAL_ACTION_CASES
            and recovery.get("automatic_resume_allowed") is False
            and recovery.get("automatic_resume_performed") is False
            and recovery.get("process_crash_recovery_performed") is False
        ),
        "actual_orderly_release_fail_closed": (
            orderly.get("actual_isolated_orderly_release_performed") is True
            and orderly.get("acquire_result_code") == "LOCK_SET_ACQUIRED"
            and orderly.get("renew_result_code") == "LEASE_RENEWED"
            and orderly.get("release_result_code") == "LOCK_SET_RELEASED"
            and orderly.get("active_lock_count_after_release") == 0
            and orderly.get("tombstone_version_count") == 2
            and orderly.get("renew_versions_advanced_once") is True
            and orderly.get("release_versions_advanced_once") is True
            and orderly.get("stale_commit_result_code") == "STALE_FENCING_TOKEN"
            and orderly.get("persistent_lock_write_performed") is False
        ),
        "shutdown_recovery_fail_closed": (
            shutdown.get("shutdown_steps") == SHUTDOWN_STEPS
            and shutdown.get("recovery_steps") == RECOVERY_STEPS
            and shutdown.get("zero_active_locks_verified") is True
            and shutdown.get("tombstone_versions_advanced_verified") is True
            and shutdown.get("persistent_lock_state_available_after_exit") is False
            and shutdown.get("process_termination_performed") is False
            and shutdown.get("automatic_process_recovery_performed") is False
        ),
    }


def _blank_report(
    contract: Mapping[str, Any], checks: Mapping[str, bool]
) -> dict[str, Any]:
    return {
        "schema_version": "ids.stage041.lock_registry.phase4.report.v1",
        "stage": "STAGE-041",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "execution_mode": EXECUTION_MODE,
        "contract_checks": dict(checks),
        "contract_valid": bool(checks) and all(checks.values()),
        "delivery_checks_performed": False,
        "delivery_checks": {},
        "delivery_contract_valid": False,
        "result": "BLOCKED_INVALID_OR_UNCHECKED_DELIVERY_CONTRACT",
        "stage_review_status": "blocked_invalid_delivery_contract",
        "next_gate": PHASE4_GATE,
        "execution_ready": False,
        "lock_lifecycle_evidence": {},
        "state_retry_backpressure_evidence": {},
        "cleanup_allowlist": {},
        "recovery_handling": {},
        "orderly_lock_shutdown": {},
        "safe_shutdown_and_recovery": {},
        "rollback_steps": copy.deepcopy(ROLLBACK_STEPS),
        "known_limits": copy.deepcopy(KNOWN_LIMITS),
        "source_error_type": None,
        **{name: False for name in POSITIVE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS},
        "owner_feedback_zh": "交付合同未通过；保持停止并返回 Phase 4 修复。",
    }


def build_stage041_phase4_delivery_report(
    contract: Optional[Any] = None,
    *,
    execute_delivery_checks: bool = True,
) -> dict[str, Any]:
    try:
        contract_value = (
            copy.deepcopy(contract)
            if contract is not None
            else load_delivery_contract()
        )
    except (OSError, ValueError, json.JSONDecodeError):
        contract_value = {}
    checks = validate_delivery_contract(contract_value)
    safe_contract = contract_value if isinstance(contract_value, dict) else {}
    report = _blank_report(safe_contract, checks)
    if not report["contract_valid"] or not execute_delivery_checks:
        if report["contract_valid"]:
            report["stage_review_status"] = "blocked_delivery_checks_not_executed"
        return report

    try:
        phase2_module = _phase2_module()
        phase3 = _phase3_module().build_stage041_phase3_report()
        stage040 = _stage040_module().build_stage040_phase4_delivery_report()
        if phase3.get("scenario_validation_valid") is not True:
            raise RuntimeError("invalid Stage041 Phase3 prerequisite")
        if stage040.get("delivery_contract_valid") is not True:
            raise RuntimeError("invalid reviewed Stage040 delivery prerequisite")

        lifecycle = _lock_lifecycle_evidence(phase3)
        state_retry = _state_retry_backpressure_evidence(stage040)
        cleanup = _cleanup_allowlist(safe_contract, phase3)
        recovery = _recovery_handling(safe_contract)
        orderly = _orderly_lock_shutdown(phase2_module)
        shutdown = _safe_shutdown_and_recovery(safe_contract, orderly)
        delivery_checks = _delivery_checks(
            lifecycle, state_retry, cleanup, recovery, orderly, shutdown
        )
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        report["delivery_checks_performed"] = True
        report["stage_review_status"] = "blocked_delivery_check_error"
        report["result"] = "FAIL_CLOSEOUT_CHECKS"
        report["source_error_type"] = f"{type(exc).__name__}: {exc}"
        return report

    valid = bool(delivery_checks) and all(delivery_checks.values())
    truth = safe_contract["truth_flags"]
    owner = safe_contract["owner_feedback_contract"]
    report.update(
        {
            "delivery_checks_performed": True,
            "delivery_checks": delivery_checks,
            "delivery_contract_valid": valid,
            "result": VALID_RESULT if valid else "FAIL_CLOSEOUT_CHECKS",
            "stage_review_status": (
                "pending_next_run" if valid else "blocked_delivery_check_failure"
            ),
            "next_gate": REVIEW_GATE if valid else PHASE4_GATE,
            "lock_lifecycle_evidence": lifecycle,
            "state_retry_backpressure_evidence": state_retry,
            "cleanup_allowlist": cleanup,
            "recovery_handling": recovery,
            "orderly_lock_shutdown": orderly,
            "safe_shutdown_and_recovery": shutdown,
            "rollback_steps": copy.deepcopy(
                safe_contract["rollback_contract"]["steps"]
            ),
            "known_limits": copy.deepcopy(safe_contract["known_limits"]),
            **{name: bool(truth[name]) for name in POSITIVE_TRUTH_FLAGS},
            **{name: bool(truth[name]) for name in FALSE_TRUTH_FLAGS},
            "owner_feedback_zh": " ".join(
                [
                    owner["status_zh"],
                    owner["automatic_eligibility_zh"],
                    owner["manual_action_zh"],
                    owner["limit_zh"],
                ]
            ),
        }
    )
    return report


def main() -> int:
    report = build_stage041_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["delivery_contract_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
