#!/usr/bin/env python3
"""Build and validate STAGE-042 Phase 4 isolated closeout evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping, Optional
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT_PATH = (
    BASE
    / "automatic_lifecycle/stage042_automatic_lifecycle_delivery_contract.json"
)
PHASE3_CHECKER = PROJECT_ROOT / "scripts/check_automatic_lifecycle_scenarios.py"
STAGE040_DELIVERY_CHECKER = PROJECT_ROOT / "scripts/check_backpressure_delivery.py"
STAGE041_DELIVERY_CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_delivery.py"

TASK_ID = "IDS-V0_1-STAGE042-P4"
ACCEPTANCE_ID = "ACC-STAGE-042"
EXECUTION_MODE = "ISOLATED_NON_PRODUCTION_AUTOMATIC_LIFECYCLE_CLOSEOUT"
VALID_RESULT = "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
PHASE4_GATE = "IDS-STAGE042-P4-GATE"
REVIEW_GATE = "IDS-STAGE042-REVIEW-GATE"
PHASE3_COMMIT = "d8773ac03d10d877b0b9c439bfce91fe85f8fdfe"
PHASE3_KMIDS_TREE = "51a990dbb6563197d7a16d97c7cf2af201a7224e"

PRESSURE_SIGNALS = [
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
]
RESOURCE_RECOVERY_CASES = [
    "EXTERNAL_DRIVE_PAUSE_THEN_GUARDED_REQUEUE",
    "LOW_DISK_PAUSE_THEN_GUARDED_REQUEUE",
    "API_BUDGET_PAUSE_THEN_GUARDED_REQUEUE",
]
RESOURCE_SCENARIOS = {
    "EXTERNAL_DRIVE_PAUSE_THEN_GUARDED_REQUEUE": (
        "external_drive_pause_then_guarded_resume",
        "EXTERNAL_DRIVE_OFFLINE",
    ),
    "LOW_DISK_PAUSE_THEN_GUARDED_REQUEUE": (
        "low_disk_pause_then_guarded_resume",
        "DISK_SPACE_INSUFFICIENT",
    ),
    "API_BUDGET_PAUSE_THEN_GUARDED_REQUEUE": (
        "api_budget_pause_then_guarded_resume",
        "EXTERNAL_API_BUDGET_INSUFFICIENT",
    ),
}
OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
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
MANUAL_ACTION_CASES = [
    "CHANGED_INPUT_IDEMPOTENCY_CONFLICT",
    "STALE_OR_INCOMPLETE_START_OBSERVATION",
    "RESOURCE_OWNER_OR_STABILITY_REVALIDATION_MISSING",
    "ACTIVE_CLAIM_OR_LOCK_PRESENT",
    "SHUTDOWN_GUARD_OR_TIMEOUT",
    "WORKER_PROCESS_CRASH",
    "PROTECTED_CLEANUP_REQUEST",
    "TERMINAL_HISTORY_REOPEN_REQUEST",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "PROCESS_EXIT_WITHOUT_PERSISTENT_LIFECYCLE_STATE",
]
SHUTDOWN_STEPS = [
    "STOP_NEW_LIFECYCLE_DECISIONS",
    "STOP_NEW_ADMISSION_AND_CLAIMS",
    "REQUEST_ACTIVE_JOB_PAUSE",
    "WAIT_FOR_CHECKPOINT_OR_QUARANTINE",
    "FREEZE_RETRY_AND_RESUME_ELIGIBILITY",
    "RELEASE_MATCHING_ACTIVE_LOCKS_BY_OWNER_RUNTIME",
    "VERIFY_ZERO_ACTIVE_LOCKS_BY_OWNER_RUNTIME",
    "CLOSE_REVIEWED_WORKER_TRANSPORT_BY_OWNER_RUNTIME",
    "PRESERVE_AUDIT_CHECKPOINT_AND_EVIDENCE_REFS",
    "VERIFY_NO_DELETE_PERSISTENCE_OR_RUNTIME_OUTPUT",
]
RECOVERY_STEPS = [
    "VERIFY_EXACT_SOURCE_POLICY_AND_UPSTREAM_HASHES",
    "REOBSERVE_SOURCE_HASH_AND_RESOURCE_OWNERSHIP",
    "REJECT_UNKNOWN_OR_STALE_OBSERVATIONS",
    "REQUIRE_OWNER_REVALIDATION_AND_STABILITY",
    "VERIFY_NO_ACTIVE_CLAIM_OR_LOCK",
    "RERUN_IDEMPOTENT_LIFECYCLE_DECISION_EVALUATION",
    "REQUEUE_ONLY_TO_QUEUED_WITH_FRESH_ADMISSION_CLAIM_LOCK",
    "DO_NOT_RESTORE_MISSING_IN_MEMORY_LIFECYCLE_STATE",
    "DEFER_PROCESS_CRASH_RECOVERY_TO_STAGE043",
    "DEFER_CLEANUP_EXECUTION_TO_STAGE044",
]
ROLLBACK_STEPS = [
    "STOP_ON_INVALID_DELIVERY_CONTRACT",
    "STOP_NEW_LIFECYCLE_DECISIONS",
    "REQUIRE_MANUAL_REVIEW_FOR_ACTIVE_OR_UNKNOWN_STATE",
    "REVERT_PHASE4_FILES_ONLY",
    "PRESERVE_PHASE1_PHASE3_EVIDENCE",
    "PRESERVE_STAGE037_STAGE041_REVIEWED_EVIDENCE",
    "PRESERVE_RAW_DATA_AND_DURABLE_EVIDENCE",
    "DO_NOT_DELETE_OR_REOPEN_TERMINAL_HISTORY",
]
KNOWN_LIMITS = [
    "NO_PERSISTENT_LIFECYCLE_STATE",
    "NO_PRODUCTION_QUEUE_OR_WORKER_RUNTIME",
    "NO_PRODUCTION_CALIBRATION",
    "NO_ACTUAL_AUTOMATIC_START_PAUSE_RESUME_OR_SHUTDOWN",
    "NO_PROCESS_CRASH_RECOVERY",
    "NO_PROCESS_TERMINATION",
    "NO_CLEANUP_RUNTIME",
    "NO_DATABASE_OR_RAW_SOURCE_ACCESS",
    "NO_STAGE042_WHOLE_STAGE_REVIEW_IN_THIS_RUN",
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
        "STAGE-042_自动运行、暂停、恢复与关闭.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08"
    ),
    "roadmap_path": (
        "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_path": (
        "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}
EXPECTED_UPSTREAM = {
    "stage042_phase3_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_scenarios.json",
        "5ce7c014971e5aa708d6081d34a208c7b78c77b7593de119555b39206463db5b",
    ),
    "stage042_phase3_checker": (
        "KM_IDSystem/scripts/check_automatic_lifecycle_scenarios.py",
        "631a301630544421caa08c4f78105be3ee2035ed5b16aed1b3a8c094f21e66e2",
    ),
    "stage042_phase3_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage042_automatic_lifecycle_scenarios.py",
        "6e63e4ed21e36f10ce156cd8fd28e45d1bbec78799dc818a9f8a44009e34d14f",
    ),
    "stage042_phase3_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE3_SCENARIO_VALIDATION.md",
        "c8bdcd7459638b72ea98fcfad1af8a71a7c5ebc757415bc683e694b2e0652263",
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
    "stage041_delivery_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_delivery_contract.json",
        "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84",
    ),
    "stage041_delivery_checker": (
        "KM_IDSystem/scripts/check_lock_registry_delivery.py",
        "8816e81a015220a8ccc0024e8c3847375b5649123d007e393152e91a76eed18c",
    ),
    "stage041_review_artifact": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE041_STAGE_REVIEW.md",
        "68ab244b3bf6e5f287164c8c738469425612de69a81cc128a734b19f3cb754d0",
    ),
}
FORWARD_COMPATIBLE_UPSTREAM_HASHES = {
    "stage042_phase3_checker": {
        "631a301630544421caa08c4f78105be3ee2035ed5b16aed1b3a8c094f21e66e2",
        "1014b6d5cfd33c918dc4ef1250615ac39a190c30a74db4931c285293e3ef903c",
        "c57662f4f3d9b65ecd2b8a2e971bfa9b92ade2d535d804ceda33e173511e4d7a",
    },
    "stage042_phase3_tests": {
        "6e63e4ed21e36f10ce156cd8fd28e45d1bbec78799dc818a9f8a44009e34d14f",
        "ac4da088d2b21fa86d08e0979dcc971c5a760525c60dac6d607d2886cb28d406",
    },
    "stage041_delivery_checker": {
        "8816e81a015220a8ccc0024e8c3847375b5649123d007e393152e91a76eed18c",
        "01dec20a2f32a98788de88d38e7e97574b5ec31070f66f63fe0eb3eacf617310",
    },
}
EXPECTED_DELIVERY = {
    "required_job_type_count": 8,
    "required_job_state_count": 11,
    "required_terminal_state_count": 4,
    "required_transition_count": 21,
    "required_failure_attempt_count": 3,
    "required_failure_retry_count": 2,
    "required_failure_final_state": "DEAD_LETTERED",
    "required_pressure_signals": PRESSURE_SIGNALS,
    "required_scenario_count": 12,
    "required_passed_scenario_count": 12,
}
EXPECTED_AUTOMATIC = {
    "automatic_recovery_eligible_cases": RESOURCE_RECOVERY_CASES,
    "successful_automatic_recovery_cases_observed": [],
    "resume_target": "QUEUED",
    "owner_revalidation_required": True,
    "resource_stability_required": True,
    "no_active_claim_or_lock_required": True,
    "fresh_admission_claim_lock_cycle_required": True,
    "terminal_history_reopen_allowed": False,
    "actual_lifecycle_execution_allowed": False,
}
EXPECTED_EXCLUSION = {
    "required_operation_families": OPERATION_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "required_selected_matrix_conflict_count": 16,
    "operation_invocation_allowed": False,
    "retry_budget_consumption_allowed": False,
    "runtime_owner": "STAGE-041",
}
EXPECTED_CLEANUP = {
    "cleanup_eligible_classes": CLEANUP_CLASSES,
    "protected_artifact_classes": PROTECTED_CLASSES,
    "cleanup_manifest_required": True,
    "required_preconditions": CLEANUP_PRECONDITIONS,
    "runtime_owner": "STAGE-044",
    "delete_execution_allowed": False,
}
EXPECTED_RECOVERY = {
    "automatic_recovery_eligible_cases": RESOURCE_RECOVERY_CASES,
    "successful_automatic_recovery_cases_observed": [],
    "manual_action_required_cases": MANUAL_ACTION_CASES,
    "owner_revalidation_required": True,
    "resource_stability_required": True,
    "no_active_claim_or_lock_required": True,
    "fresh_admission_claim_lock_cycle_required": True,
    "automatic_resume_performed": False,
    "process_crash_recovery_runtime_owner": "STAGE-043",
}
EXPECTED_SHUTDOWN = {
    "shutdown_steps": SHUTDOWN_STEPS,
    "recovery_steps": RECOVERY_STEPS,
    "persistent_lifecycle_state_available_after_exit": False,
    "process_termination_allowed": False,
    "automatic_process_recovery_allowed": False,
}
EXPECTED_ROLLBACK = {
    "steps": ROLLBACK_STEPS,
    "destructive_rollback_allowed": False,
}
EXPECTED_REVIEW = {
    "next_task_id": "IDS-V0_1-STAGE042-REVIEW",
    "must_run_separately": True,
    "phase4_may_mark_stage_reviewed": False,
    "stage043_entry_allowed": False,
    "batch_review_allowed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}
EXPECTED_OWNER = {
    "status_zh": (
        "Stage042 Phase 4 隔离交付证据已收口，生产自动生命周期仍禁用。"
    ),
    "automatic_eligibility_zh": (
        "三类资源暂停仅具备复核后重新排队的候选资格；未观察到自动恢复成功。"
    ),
    "manual_action_zh": (
        "冲突、陈旧观察、owner 或稳定性复核缺失、活动 claim/lock、关闭超时、"
        "进程崩溃、受保护清理和未知状态均需要人工处理。"
    ),
    "limit_zh": (
        "下一步只能在独立 run 进行整阶段复审；"
        "本证据不是生产运行或生产就绪证明。"
    ),
}
POSITIVE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_lifecycle_decisions_reexecuted",
    "phase3_lifecycle_scenarios_replayed",
    "reviewed_stage040_delivery_replayed",
    "reviewed_stage041_delivery_replayed",
}
FALSE_TRUTH_FLAGS = {
    "automatic_lifecycle_runtime_performed",
    "automatic_start_performed",
    "automatic_pause_performed",
    "automatic_resume_performed",
    "automatic_shutdown_performed",
    "state_registry_write_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "production_lock_runtime_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "crash_recovery_runtime_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_decision_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
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
EXPECTED_TRUTH = {
    **{name: True for name in POSITIVE_TRUTH_FLAGS},
    **{name: False for name in FALSE_TRUTH_FLAGS},
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
    "automatic_lifecycle_contract",
    "operation_exclusion_contract",
    "cleanup_allowlist",
    "recovery_handling",
    "safe_shutdown_and_recovery",
    "rollback_contract",
    "review_gate",
    "known_limits",
    "owner_feedback_contract",
    "truth_flags",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upstream_file_hash_current(
    name: str, declared_hash: str, actual_hash: str
) -> bool:
    allowed = FORWARD_COMPATIBLE_UPSTREAM_HASHES.get(name, {declared_hash})
    return declared_hash in allowed and actual_hash in allowed


def _upstream_matches_git_index(relative: str, actual_hash: str) -> bool:
    indexed = subprocess.run(
        ["git", "show", f":{relative}"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return (
        indexed.returncode == 0
        and hashlib.sha256(indexed.stdout).hexdigest() == actual_hash
    )


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase3_module() -> Any:
    return _load_module(PHASE3_CHECKER, "stage042_phase3_delivery_upstream")


def _stage040_module() -> Any:
    return _load_module(STAGE040_DELIVERY_CHECKER, "stage040_delivery_upstream")


def _stage041_module() -> Any:
    return _load_module(STAGE041_DELIVERY_CHECKER, "stage041_delivery_upstream")


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("delivery contract root must be an object")
    return value


def _source_files_valid(value: Any) -> bool:
    if value != EXPECTED_SOURCE:
        return False
    try:
        archive = Path(EXPECTED_SOURCE["source_archive_path"])
        roadmap = Path(EXPECTED_SOURCE["roadmap_path"])
        instructions = Path(EXPECTED_SOURCE["instructions_path"])
        if sha256_file(archive) != EXPECTED_SOURCE["source_archive_sha256"]:
            return False
        if sha256_file(roadmap) != EXPECTED_SOURCE["roadmap_sha256"]:
            return False
        if sha256_file(instructions) != EXPECTED_SOURCE["instructions_sha256"]:
            return False
        member = EXPECTED_SOURCE["source_member"]
        with ZipFile(archive) as source_zip:
            matches = [name for name in source_zip.namelist() if name == member]
            if len(matches) != EXPECTED_SOURCE["source_member_match_count"]:
                return False
            digest = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
        return digest == EXPECTED_SOURCE["source_member_sha256"]
    except (OSError, KeyError, ValueError):
        return False


def _upstream_declaration() -> dict[str, dict[str, str]]:
    return {
        name: {"ref": ref, "sha256": digest}
        for name, (ref, digest) in EXPECTED_UPSTREAM.items()
    }


def _upstream_valid(value: Any) -> bool:
    if value != _upstream_declaration():
        return False
    try:
        for name, (ref, digest) in EXPECTED_UPSTREAM.items():
            pure = PurePosixPath(ref)
            if pure.is_absolute() or ".." in pure.parts:
                return False
            path = REPO_ROOT / pure
            if not path.is_file():
                return False
            actual_hash = sha256_file(path)
            if not upstream_file_hash_current(name, digest, actual_hash):
                return False
            if not _upstream_matches_git_index(ref, actual_hash):
                return False
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", ref],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if tracked.returncode != 0:
                return False
        return True
    except (OSError, ValueError):
        return False


def _phase3_commit_is_current(value: Any) -> bool:
    expected = {
        "commit": PHASE3_COMMIT,
        "km_ids_tree": PHASE3_KMIDS_TREE,
        "required_ancestor_of_head": True,
    }
    if value != expected:
        return False
    try:
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
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return tree == PHASE3_KMIDS_TREE
    except (OSError, subprocess.CalledProcessError):
        return False


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, Mapping):
        return {"contract_is_object": False}
    return {
        "root_keys_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage042.automatic_lifecycle.phase4.delivery.v1"
            and contract.get("stage") == "STAGE-042"
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
        "source_declared_exactly": contract.get("source_binding") == EXPECTED_SOURCE,
        "source_files_current": _source_files_valid(contract.get("source_binding")),
        "phase3_binding_current": _phase3_commit_is_current(
            contract.get("phase3_commit_binding")
        ),
        "upstream_declared_exactly": (
            contract.get("upstream_bindings") == _upstream_declaration()
        ),
        "upstream_files_current": _upstream_valid(
            contract.get("upstream_bindings")
        ),
        "delivery_requirements_exact": (
            contract.get("delivery_contract") == EXPECTED_DELIVERY
        ),
        "automatic_lifecycle_boundary_exact": (
            contract.get("automatic_lifecycle_contract") == EXPECTED_AUTOMATIC
        ),
        "operation_exclusion_exact": (
            contract.get("operation_exclusion_contract") == EXPECTED_EXCLUSION
        ),
        "cleanup_allowlist_exact": (
            contract.get("cleanup_allowlist") == EXPECTED_CLEANUP
        ),
        "recovery_handling_exact": (
            contract.get("recovery_handling") == EXPECTED_RECOVERY
        ),
        "safe_shutdown_and_recovery_exact": (
            contract.get("safe_shutdown_and_recovery") == EXPECTED_SHUTDOWN
        ),
        "rollback_exact": contract.get("rollback_contract") == EXPECTED_ROLLBACK,
        "review_gate_exact": contract.get("review_gate") == EXPECTED_REVIEW,
        "known_limits_exact": contract.get("known_limits") == KNOWN_LIMITS,
        "owner_feedback_exact": (
            contract.get("owner_feedback_contract") == EXPECTED_OWNER
        ),
        "truth_flags_exact": contract.get("truth_flags") == EXPECTED_TRUTH,
    }


def _automatic_lifecycle_evidence(
    phase3: Mapping[str, Any]
) -> dict[str, Any]:
    results = phase3["scenario_results"]
    scenario_checks = {
        name: item.get("status") == "PASS" for name, item in results.items()
    }
    return {
        "scenario_count": phase3["scenario_count"],
        "passed_scenario_count": phase3["passed_scenario_count"],
        "scenario_checks": scenario_checks,
        "phase2_lifecycle_decisions_valid": phase3["phase2_slice_valid"] is True,
        "phase3_scenarios_valid": phase3["scenario_validation_valid"] is True,
        "duplicate_request_exact_replay_verified": (
            results["duplicate_request_exact_replay"].get("replay_equal") is True
            and results["duplicate_request_exact_replay"].get(
                "state_mutation_performed"
            )
            is False
        ),
        "changed_payload_conflict_verified": (
            results["changed_payload_same_request_rejected"].get(
                "state_mutation_performed"
            )
            is False
        ),
        "stale_start_fails_to_manual_review": (
            results["stale_start_observation_blocked"].get("decision_action")
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "actual_lifecycle_performed": False,
    }


def _pressure_signal_checks(proof: Mapping[str, Any]) -> dict[str, bool]:
    soft = proof.get("QUEUE_SOFT_PRESSURE", {})
    hard = proof.get("QUEUE_HARD_CAPACITY", {})
    drive = proof.get("EXTERNAL_DRIVE_OFFLINE", {})
    disk = proof.get("DISK_SPACE_INSUFFICIENT", {})
    api = proof.get("EXTERNAL_API_BUDGET_INSUFFICIENT", {})
    concurrency = proof.get("JOB_TYPE_CONCURRENCY_LIMIT_REACHED", {})
    conflict = proof.get("SAME_SOURCE_CONFLICT", {})
    return {
        "QUEUE_SOFT_PRESSURE": (
            soft.get("decision_action") == "THROTTLE_ADMISSION"
            and soft.get("persistent_write_performed") is False
        ),
        "QUEUE_HARD_CAPACITY": (
            hard.get("decision_action") == "DENY_NEW_ADMISSION"
            and hard.get("job_created") is False
            and hard.get("persistent_write_performed") is False
        ),
        "EXTERNAL_DRIVE_OFFLINE": (
            drive.get("decision_action") == "PAUSE_RESOURCE_GATE"
            and drive.get("physical_drive_removal_performed") is False
            and drive.get("retry_budget_consumed") is False
        ),
        "DISK_SPACE_INSUFFICIENT": (
            disk.get("decision_action") == "PAUSE_RESOURCE_GATE"
            and disk.get("actual_disk_observation_performed") is True
            and disk.get("disk_allocation_performed") is False
            and disk.get("retry_budget_consumed") is False
        ),
        "EXTERNAL_API_BUDGET_INSUFFICIENT": (
            api.get("decision_action") == "PAUSE_RESOURCE_GATE"
            and api.get("external_api_call_performed") is False
            and api.get("retry_budget_consumed") is False
        ),
        "JOB_TYPE_CONCURRENCY_LIMIT_REACHED": (
            concurrency.get("decision_action") == "THROTTLE_ADMISSION"
            and concurrency.get("created_job_count") == 0
            and concurrency.get("retry_budget_consumed_count") == 0
            and concurrency.get("production_lock_runtime_performed") is False
        ),
        "SAME_SOURCE_CONFLICT": (
            conflict.get("decision_action") == "THROTTLE_ADMISSION"
            and conflict.get("conflict_count") == 3
            and conflict.get("production_lock_runtime_performed") is False
        ),
    }


def _state_retry_backpressure_evidence(
    stage040: Mapping[str, Any], stage041: Mapping[str, Any]
) -> dict[str, Any]:
    state_retry = stage041["state_retry_backpressure_evidence"]
    return {
        "job_state_graph": copy.deepcopy(state_retry["job_state_graph"]),
        "failure_retry_log": copy.deepcopy(state_retry["failure_retry_log"]),
        "backpressure_trigger_proof": _pressure_signal_checks(
            stage040["backpressure_trigger_proof"]
        ),
        "reviewed_stage040_delivery_valid": (
            stage040.get("delivery_contract_valid") is True
            and stage040.get("result") == VALID_RESULT
            and stage040.get("next_gate") == "IDS-STAGE040-REVIEW-GATE"
            and state_retry.get("reviewed_stage040_delivery_valid") is True
        ),
    }


def _operation_exclusion_evidence(
    phase3: Mapping[str, Any], stage041: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase3["scenario_results"][
        "same_source_four_operation_lock_exclusion"
    ]
    return {
        "required_operation_families": copy.deepcopy(
            result["required_operation_families"]
        ),
        "required_operation_family_count": len(
            result["required_operation_families"]
        ),
        "selected_matrix_conflict_count": result[
            "selected_matrix_conflict_count"
        ],
        "operation_invocation_count": result["operation_invocation_count"],
        "retry_budget_consumed_count": result["retry_budget_consumed_count"],
        "partial_lock_retained_count": result["partial_lock_retained_count"],
        "all_family_checks_passed": all(result["family_checks"].values()),
        "reviewed_stage041_delivery_valid": (
            stage041.get("delivery_contract_valid") is True
            and stage041.get("result") == VALID_RESULT
            and stage041.get("next_gate") == "IDS-STAGE041-REVIEW-GATE"
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
            and item.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
            and item.get("delete_allowed") is False
            and item.get("delete_attempted") is False
        )
        for name, item in protected["artifact_results"].items()
    }
    eligible = phase3["scenario_results"]["eligible_cleanup_candidate_only"]
    eligible_checks = {
        name: (
            item.get("cleanup_candidate_only") is True
            and item.get("delete_allowed") is False
        )
        for name, item in eligible["artifact_results"].items()
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
        "eligible_candidate_checks": eligible_checks,
        "cleanup_manifest_required": configured["cleanup_manifest_required"],
        "required_preconditions": copy.deepcopy(configured["required_preconditions"]),
        "runtime_owner": configured["runtime_owner"],
        "cleanup_runtime_performed": False,
        "delete_attempt_performed": False,
    }


def _recovery_handling(
    contract: Mapping[str, Any], phase3: Mapping[str, Any]
) -> dict[str, Any]:
    configured = contract["recovery_handling"]
    results = phase3["scenario_results"]
    eligibility_checks = {}
    for case, (scenario_name, signal) in RESOURCE_SCENARIOS.items():
        result = results[scenario_name]
        eligibility_checks[case] = (
            result.get("status") == "PASS"
            and result.get("pressure_signal") == signal
            and result.get("pause_decision_action") == "AUTO_PAUSE_CANDIDATE"
            and result.get("resume_decision_action") == "AUTO_RESUME_CANDIDATE"
            and result.get("owner_blocked_decision_action")
            == "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION"
            and result.get("fresh_admission_and_lock_cycle_required") is True
            and result.get("state_mutation_performed") is False
        )
    return {
        "automatic_recovery_eligible_cases": copy.deepcopy(
            configured["automatic_recovery_eligible_cases"]
        ),
        "eligibility_checks": eligibility_checks,
        "successful_automatic_recovery_cases_observed": copy.deepcopy(
            configured["successful_automatic_recovery_cases_observed"]
        ),
        "manual_action_required_cases": copy.deepcopy(
            configured["manual_action_required_cases"]
        ),
        "owner_revalidation_required": configured["owner_revalidation_required"],
        "resource_stability_required": configured["resource_stability_required"],
        "no_active_claim_or_lock_required": configured[
            "no_active_claim_or_lock_required"
        ],
        "fresh_admission_claim_lock_cycle_required": configured[
            "fresh_admission_claim_lock_cycle_required"
        ],
        "automatic_resume_performed": False,
        "process_crash_recovery_performed": False,
        "process_crash_recovery_runtime_owner": configured[
            "process_crash_recovery_runtime_owner"
        ],
    }


def _safe_shutdown_and_recovery(
    contract: Mapping[str, Any], phase3: Mapping[str, Any]
) -> dict[str, Any]:
    configured = contract["safe_shutdown_and_recovery"]
    results = phase3["scenario_results"]
    ordered = results["safe_shutdown_ordered_candidate"]
    timeout = results["shutdown_timeout_blocked"]
    return {
        "shutdown_steps": copy.deepcopy(configured["shutdown_steps"]),
        "recovery_steps": copy.deepcopy(configured["recovery_steps"]),
        "ordered_shutdown_candidate_verified": (
            ordered.get("status") == "PASS"
            and ordered.get("decision_action") == "SAFE_SHUTDOWN_CANDIDATE"
            and ordered.get("ordered_shutdown_steps") == SHUTDOWN_STEPS
            and ordered.get("process_termination_performed") is False
            and ordered.get("state_mutation_performed") is False
        ),
        "shutdown_timeout_fails_to_manual_review": (
            timeout.get("status") == "PASS"
            and timeout.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
            and timeout.get("process_termination_performed") is False
        ),
        "persistent_lifecycle_state_available_after_exit": configured[
            "persistent_lifecycle_state_available_after_exit"
        ],
        "process_termination_performed": False,
        "automatic_process_recovery_performed": False,
    }


def _delivery_checks(
    lifecycle: Mapping[str, Any],
    state_retry: Mapping[str, Any],
    exclusion: Mapping[str, Any],
    cleanup: Mapping[str, Any],
    recovery: Mapping[str, Any],
    shutdown: Mapping[str, Any],
) -> dict[str, bool]:
    graph = state_retry.get("job_state_graph", {})
    failure = state_retry.get("failure_retry_log", {})
    return {
        "phase3_lifecycle_evidence_complete": (
            lifecycle.get("scenario_count") == 12
            and lifecycle.get("passed_scenario_count") == 12
            and all(lifecycle.get("scenario_checks", {}).values())
            and lifecycle.get("phase2_lifecycle_decisions_valid") is True
            and lifecycle.get("phase3_scenarios_valid") is True
            and lifecycle.get("duplicate_request_exact_replay_verified") is True
            and lifecycle.get("changed_payload_conflict_verified") is True
            and lifecycle.get("stale_start_fails_to_manual_review") is True
            and lifecycle.get("actual_lifecycle_performed") is False
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
            and all(state_retry.get("backpressure_trigger_proof", {}).values())
            and state_retry.get("reviewed_stage040_delivery_valid") is True
        ),
        "same_source_exclusion_reviewed": (
            exclusion.get("required_operation_families") == OPERATION_FAMILIES
            and exclusion.get("required_operation_family_count") == 4
            and exclusion.get("selected_matrix_conflict_count") == 16
            and exclusion.get("operation_invocation_count") == 0
            and exclusion.get("retry_budget_consumed_count") == 0
            and exclusion.get("partial_lock_retained_count") == 0
            and exclusion.get("all_family_checks_passed") is True
            and exclusion.get("reviewed_stage041_delivery_valid") is True
        ),
        "cleanup_allowlist_narrow_and_protected": (
            cleanup.get("cleanup_eligible_classes") == CLEANUP_CLASSES
            and cleanup.get("protected_artifact_classes") == PROTECTED_CLASSES
            and cleanup.get("protected_ref_count") == 5
            and all(cleanup.get("protected_ref_checks", {}).values())
            and all(cleanup.get("eligible_candidate_checks", {}).values())
            and cleanup.get("cleanup_manifest_required") is True
            and cleanup.get("runtime_owner") == "STAGE-044"
            and cleanup.get("cleanup_runtime_performed") is False
            and cleanup.get("delete_attempt_performed") is False
        ),
        "automatic_and_manual_recovery_truthful": (
            recovery.get("automatic_recovery_eligible_cases")
            == RESOURCE_RECOVERY_CASES
            and all(recovery.get("eligibility_checks", {}).values())
            and recovery.get("successful_automatic_recovery_cases_observed") == []
            and recovery.get("manual_action_required_cases") == MANUAL_ACTION_CASES
            and recovery.get("owner_revalidation_required") is True
            and recovery.get("resource_stability_required") is True
            and recovery.get("no_active_claim_or_lock_required") is True
            and recovery.get("fresh_admission_claim_lock_cycle_required") is True
            and recovery.get("automatic_resume_performed") is False
            and recovery.get("process_crash_recovery_performed") is False
        ),
        "shutdown_recovery_fail_closed": (
            shutdown.get("shutdown_steps") == SHUTDOWN_STEPS
            and shutdown.get("recovery_steps") == RECOVERY_STEPS
            and shutdown.get("ordered_shutdown_candidate_verified") is True
            and shutdown.get("shutdown_timeout_fails_to_manual_review") is True
            and shutdown.get("persistent_lifecycle_state_available_after_exit")
            is False
            and shutdown.get("process_termination_performed") is False
            and shutdown.get("automatic_process_recovery_performed") is False
        ),
    }


def _blank_report(checks: Mapping[str, bool]) -> dict[str, Any]:
    return {
        "schema_version": "ids.stage042.automatic_lifecycle.phase4.report.v1",
        "stage": "STAGE-042",
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
        "automatic_lifecycle_evidence": {},
        "state_retry_backpressure_evidence": {},
        "operation_exclusion_evidence": {},
        "cleanup_allowlist": {},
        "recovery_handling": {},
        "safe_shutdown_and_recovery": {},
        "rollback_steps": copy.deepcopy(ROLLBACK_STEPS),
        "known_limits": copy.deepcopy(KNOWN_LIMITS),
        "source_error_type": None,
        **{name: False for name in POSITIVE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS},
        "owner_feedback_zh": "交付合同未通过；保持停止并返回 Phase 4 修复。",
    }


def build_stage042_phase4_delivery_report(
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
    report = _blank_report(checks)
    if not report["contract_valid"] or not execute_delivery_checks:
        if report["contract_valid"]:
            report["stage_review_status"] = "blocked_delivery_checks_not_executed"
        return report

    try:
        phase3 = _phase3_module().build_stage042_phase3_report()
        stage040 = _stage040_module().build_stage040_phase4_delivery_report()
        stage041 = _stage041_module().build_stage041_phase4_delivery_report()
        if phase3.get("scenario_validation_valid") is not True:
            raise RuntimeError("invalid Stage042 Phase3 prerequisite")
        if stage040.get("delivery_contract_valid") is not True:
            raise RuntimeError("invalid reviewed Stage040 delivery prerequisite")
        if stage041.get("delivery_contract_valid") is not True:
            raise RuntimeError("invalid reviewed Stage041 delivery prerequisite")

        lifecycle = _automatic_lifecycle_evidence(phase3)
        state_retry = _state_retry_backpressure_evidence(stage040, stage041)
        exclusion = _operation_exclusion_evidence(phase3, stage041)
        cleanup = _cleanup_allowlist(safe_contract, phase3)
        recovery = _recovery_handling(safe_contract, phase3)
        shutdown = _safe_shutdown_and_recovery(safe_contract, phase3)
        delivery_checks = _delivery_checks(
            lifecycle, state_retry, exclusion, cleanup, recovery, shutdown
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
            "automatic_lifecycle_evidence": lifecycle,
            "state_retry_backpressure_evidence": state_retry,
            "operation_exclusion_evidence": exclusion,
            "cleanup_allowlist": cleanup,
            "recovery_handling": recovery,
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
    report = build_stage042_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["delivery_contract_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
