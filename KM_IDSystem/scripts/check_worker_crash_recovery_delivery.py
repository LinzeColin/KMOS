#!/usr/bin/env python3
"""Fail-closed STAGE-043 Phase 4 worker-crash-recovery delivery checker."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Optional
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT_PATH = (
    BASE
    / "worker_crash_recovery/stage043_worker_crash_recovery_delivery_contract.json"
)

MODULE_PATHS = {
    "stage038": PROJECT_ROOT / "scripts/check_worker_queue_delivery.py",
    "stage039": PROJECT_ROOT / "scripts/check_retry_dead_letter_delivery.py",
    "stage040": PROJECT_ROOT / "scripts/check_backpressure_delivery.py",
    "stage041": PROJECT_ROOT / "scripts/check_lock_registry_delivery.py",
    "stage042": PROJECT_ROOT / "scripts/check_automatic_lifecycle_delivery.py",
    "stage043_p3": PROJECT_ROOT / "scripts/check_worker_crash_recovery_scenarios.py",
}

SCHEMA_VERSION = "ids.stage043.worker_crash_recovery.phase4.delivery.v1"
REPORT_SCHEMA_VERSION = "ids.stage043.worker_crash_recovery.phase4.report.v1"
TASK_ID = "IDS-V0_1-STAGE043-P4"
ACCEPTANCE_ID = "ACC-STAGE-043"
P4_GATE = "IDS-STAGE043-P4-GATE"
REVIEW_GATE = "IDS-STAGE043-REVIEW-GATE"
VALID_RESULT = "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
PHASE3_COMMIT = "6af57993b35bde3c3a215b08ee7e1ab65c204747"
PHASE3_KMIDS_TREE = "3461f0ac16efe01fb48e0eb589ac2a00b804e226"

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
    "recovery_handling",
    "operation_exclusion_contract",
    "cleanup_allowlist",
    "safe_shutdown_and_recovery",
    "rollback_contract",
    "review_gate",
    "known_limits",
    "owner_feedback_contract",
    "truth_flags",
}

EXPECTED_SOURCE = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
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

EXPECTED_PHASE3_COMMIT = {
    "commit": PHASE3_COMMIT,
    "km_ids_tree": PHASE3_KMIDS_TREE,
    "required_ancestor_of_head": True,
}

EXPECTED_UPSTREAM = {
    "stage043_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_scenarios.json"
        ),
        "sha256": (
            "5c4c7134b5adb87dbf7790f7e6b9dfe0e237008dcba0a4d4bf3a9d11b0afc8ca"
        ),
    },
    "stage043_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_crash_recovery_scenarios.py",
        "sha256": (
            "d92e7d1d5a096c11b7db85f140c2f67361a58d2b0c19168ae7c96752fdb30775"
        ),
    },
    "stage043_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage043_worker_crash_recovery_scenarios.py"
        ),
        "sha256": (
            "ddf1b0e3c910e158c3d0352c757aa8e0f7ce645149c03d1c1962b332975c83a0"
        ),
    },
    "stage043_phase3_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE043_PHASE3_SCENARIO_VALIDATION.md"
        ),
        "sha256": (
            "10543e29ac87feb207ac14e656836d4a416470a36bafa3fd6f279960313b35bd"
        ),
    },
    "stage038_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
            "stage038_worker_queue_delivery_contract.json"
        ),
        "sha256": (
            "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4"
        ),
    },
    "stage038_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_queue_delivery.py",
        "sha256": (
            "305536595643979e34be5b3fdbc8e1c850f9869d4cd656331f4af0c7e2c12fd6"
        ),
    },
    "stage039_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
            "stage039_retry_dead_letter_delivery_contract.json"
        ),
        "sha256": (
            "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b"
        ),
    },
    "stage039_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_retry_dead_letter_delivery.py",
        "sha256": (
            "47b4fbbd6720f48f7ffcc1f29d405c7585f67c44b4ee7df40ea0c1b498f030b2"
        ),
    },
    "stage040_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
            "stage040_backpressure_delivery_contract.json"
        ),
        "sha256": (
            "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce"
        ),
    },
    "stage040_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_backpressure_delivery.py",
        "sha256": (
            "98b39ebc3d27cd6916958c1b46ea23486617d580fba576b1f23273a881d6ec41"
        ),
    },
    "stage041_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_delivery_contract.json"
        ),
        "sha256": (
            "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84"
        ),
    },
    "stage041_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_lock_registry_delivery.py",
        "sha256": (
            "01dec20a2f32a98788de88d38e7e97574b5ec31070f66f63fe0eb3eacf617310"
        ),
    },
    "stage042_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
            "stage042_automatic_lifecycle_delivery_contract.json"
        ),
        "sha256": (
            "b3406b6542256a4a7f8b015bf11271822496bdad8129b787dbbf0044035311f3"
        ),
    },
    "stage042_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_automatic_lifecycle_delivery.py",
        "sha256": (
            "87771f2492fb27b7b01151e1e1e637b76d229205a0cd3e8255745df2fe700c4e"
        ),
    },
}

PRESSURE_SIGNALS = [
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
]

EXPECTED_DELIVERY = {
    "required_job_type_count": 8,
    "required_job_state_count": 11,
    "required_terminal_state_count": 4,
    "required_transition_count": 21,
    "required_failure_attempt_count": 3,
    "required_failure_retry_count": 2,
    "required_failure_final_state": "DEAD_LETTERED",
    "required_pressure_signals": PRESSURE_SIGNALS,
    "required_scenario_count": 13,
    "required_passed_scenario_count": 13,
    "required_isolated_process_exit_code": 73,
}

CONDITIONAL_HANDLING = [
    "CHECKPOINT_RESUME_CANDIDATE_AFTER_ALL_GATES",
    "STAGE039_RETRY_CANDIDATE_AFTER_ALL_GATES",
    "SAFE_FAILURE_CANDIDATE_AFTER_ALL_GATES",
]
MANUAL_CASES = [
    "MISSING_OR_STALE_CRASH_EVIDENCE",
    "CHECKPOINT_INTEGRITY_UNKNOWN",
    "IDEMPOTENCY_CONFLICT",
    "STALE_STATE_VERSION",
    "LOST_WORKER_NOT_FENCED",
    "ACTIVE_LOCK_OR_CLAIM_PRESENT",
    "RESOURCE_OWNER_REVALIDATION_REQUIRED",
    "TERMINAL_HISTORY_REOPEN_REQUEST",
    "PROTECTED_CLEANUP_REQUEST",
    "SAFE_FAILURE_CONFIRMATION_REQUIRED",
    "INVALID_OR_MISSING_CONTRACT",
    "UNCALIBRATED_POLICY",
    "NO_PERSISTENT_JOB_OR_RECOVERY_STATE",
]
EXPECTED_RECOVERY_HANDLING = {
    "conditional_automatic_handling_candidates": CONDITIONAL_HANDLING,
    "automatic_recovery_eligible_cases": [],
    "successful_automatic_recovery_cases_observed": [],
    "manual_action_required_cases": MANUAL_CASES,
    "persistent_state_required": True,
    "current_persistent_state_available": False,
    "lost_worker_fence_required": True,
    "owner_revalidation_required": True,
    "resource_stability_required": True,
    "no_active_claim_or_lock_required": True,
    "fresh_admission_claim_lock_cycle_required": True,
    "terminal_history_reopen_allowed": False,
    "automatic_recovery_performed": False,
    "retry_runtime_owner": "STAGE-039",
    "lock_fencing_runtime_owner": "STAGE-041",
    "automatic_lifecycle_runtime_owner": "STAGE-042",
    "cleanup_runtime_owner": "STAGE-044",
}

OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
EXPECTED_OPERATION_EXCLUSION = {
    "required_operation_families": OPERATION_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "required_source_full_conflict_count": 25,
    "required_selected_matrix_conflict_count": 16,
    "operation_invocation_allowed": False,
    "queue_record_creation_allowed": False,
    "retry_budget_consumption_allowed": False,
    "runtime_owner": "STAGE-041",
}

CLEANUP_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
EXPECTED_CLEANUP = {
    "cleanup_eligible_classes": CLEANUP_CLASSES,
    "protected_artifact_classes": PROTECTED_CLASSES,
    "cleanup_manifest_required": True,
    "writer_quiescence_required": True,
    "quarantine_reference_only": True,
    "runtime_owner": "STAGE-044",
    "delete_execution_allowed": False,
}

SHUTDOWN_STEPS = [
    "STOP_NEW_RECOVERY_EVALUATIONS",
    "STOP_NEW_ADMISSION_CLAIMS_AND_RETRIES_BY_OWNER_RUNTIMES",
    "REQUEST_ACTIVE_JOB_PAUSE_BY_OWNER_RUNTIME",
    "WAIT_FOR_CHECKPOINT_OR_QUARANTINE_BY_OWNER_RUNTIME",
    "FREEZE_RETRY_RESUME_AND_RECOVERY_ELIGIBILITY",
    "PRESERVE_CRASH_CHECKPOINT_AND_AUDIT_EVIDENCE",
    "FENCE_LOST_WORKER_GENERATION_BY_STAGE041_OWNER_RUNTIME",
    "RELEASE_MATCHING_ACTIVE_LOCKS_BY_OWNER_RUNTIME",
    "CLOSE_REVIEWED_WORKER_TRANSPORT_BY_OWNER_RUNTIME",
    "VERIFY_NO_DELETE_PERSISTENCE_OR_RUNTIME_OUTPUT",
]
RECOVERY_STEPS = [
    "VERIFY_EXACT_SOURCE_POLICY_AND_UPSTREAM_HASHES",
    "REOBSERVE_CRASH_HEARTBEAT_LEASE_STATE_AND_CHECKPOINT",
    "REQUIRE_CURRENT_PERSISTENT_STATE_AND_POSITIVE_VERSION",
    "REJECT_UNKNOWN_STALE_OR_INCOMPLETE_EVIDENCE",
    "REQUIRE_OWNER_RESOURCE_AND_CHECKPOINT_REVALIDATION",
    "FENCE_LOST_WORKER_GENERATION_BEFORE_ANY_CANDIDATE",
    "VERIFY_NO_ACTIVE_CLAIM_OR_LOCK",
    "RERUN_IDEMPOTENT_RECOVERY_DECISION_EVALUATION",
    "REENTER_ONLY_THROUGH_RETRY_WAIT_TO_QUEUED_AND_FRESH_ADMISSION_CLAIM_LOCK",
    "DEFER_RETRY_ADMISSION_TO_STAGE039",
    "DEFER_LIFECYCLE_TRANSITIONS_TO_STAGE042",
    "DEFER_CLEANUP_EXECUTION_TO_STAGE044",
    "DO_NOT_RESTORE_MISSING_IN_MEMORY_JOB_OR_RECOVERY_STATE",
    "DO_NOT_REOPEN_TERMINAL_HISTORY",
]
EXPECTED_SHUTDOWN_RECOVERY = {
    "shutdown_steps": SHUTDOWN_STEPS,
    "recovery_steps": RECOVERY_STEPS,
    "persistent_recovery_state_available_after_exit": False,
    "process_termination_allowed": False,
    "automatic_process_recovery_allowed": False,
}

ROLLBACK_STEPS = [
    "STOP_ON_INVALID_DELIVERY_CONTRACT",
    "STOP_NEW_RECOVERY_EVALUATIONS",
    "REQUIRE_MANUAL_REVIEW_FOR_ACTIVE_UNKNOWN_OR_UNFENCED_STATE",
    "REVERT_PHASE4_FILES_ONLY",
    "PRESERVE_PHASE1_PHASE3_EVIDENCE",
    "PRESERVE_STAGE037_STAGE042_REVIEWED_EVIDENCE",
    "PRESERVE_RAW_DATA_AND_DURABLE_EVIDENCE",
    "DO_NOT_DELETE_OR_REOPEN_TERMINAL_HISTORY",
]
EXPECTED_ROLLBACK = {
    "steps": ROLLBACK_STEPS,
    "destructive_rollback_allowed": False,
}

EXPECTED_REVIEW_GATE = {
    "next_task_id": "IDS-V0_1-STAGE043-REVIEW",
    "must_run_separately": True,
    "phase4_may_mark_stage_reviewed": False,
    "stage044_entry_allowed": False,
    "batch_review_allowed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}

EXPECTED_LIMITS = [
    "NO_PERSISTENT_JOB_OR_RECOVERY_STATE",
    "NO_PRODUCTION_QUEUE_OR_WORKER_RUNTIME",
    "NO_PRODUCTION_CALIBRATION",
    "NO_EXTERNAL_PROCESS_PROBE_SIGNAL_KILL_OR_RESTART",
    "NO_ACTUAL_WORKER_CRASH_INJECTION_OR_PROCESS_RECOVERY",
    "NO_ACTUAL_STATE_TRANSITION_OR_CHECKPOINT_RESUME",
    "NO_AUTOMATIC_RECOVERY_ELIGIBILITY_OR_SUCCESS_OBSERVED",
    "NO_CLEANUP_RUNTIME",
    "NO_DATABASE_OR_RAW_SOURCE_ACCESS",
    "NO_STAGE043_WHOLE_STAGE_REVIEW_IN_THIS_RUN",
    "NO_STAGE044_ENTRY_IN_THIS_RUN",
    "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS",
]

EXPECTED_OWNER_FEEDBACK = {
    "status_zh": (
        "Stage043 Phase 4 隔离交付证据已收口，生产 Worker 崩溃恢复仍禁用。"
    ),
    "automatic_eligibility_zh": (
        "三条路径仅是全部门禁满足后的条件处理候选；当前没有自动恢复资格，"
        "未观察到自动恢复成功。"
    ),
    "manual_action_zh": (
        "陈旧或缺失崩溃证据、检查点未知、幂等冲突、未栅栏代际、活动 "
        "claim/lock、终态重开、受保护清理、安全失败确认、未校准策略和缺失持久"
        "状态均需要人工处理。"
    ),
    "limit_zh": (
        "下一步只能在独立 run 进行整阶段复审；本证据不是生产运行或生产就绪证明。"
    ),
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_recovery_decisions_reexecuted",
    "phase3_recovery_scenarios_replayed",
    "reviewed_stage038_delivery_replayed",
    "reviewed_stage039_delivery_replayed",
    "reviewed_stage040_delivery_replayed",
    "reviewed_stage041_delivery_replayed",
    "reviewed_stage042_delivery_replayed",
    "isolated_control_process_exit_evidence_replayed",
    "same_source_lock_evidence_replayed",
    "protected_refs_verified",
}
FALSE_TRUTH_FLAGS = {
    "actual_worker_process_crash_performed",
    "process_probe_performed",
    "signal_or_kill_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "worker_restart_performed",
    "automatic_recovery_performed",
    "successful_automatic_recovery_observed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
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
EXPECTED_TRUTH_FLAGS = {
    **{name: True for name in TRUE_TRUTH_FLAGS},
    **{name: False for name in FALSE_TRUTH_FLAGS},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_binding_valid(value: Any) -> bool:
    if value != EXPECTED_SOURCE:
        return False
    archive = Path(value["source_archive_path"])
    roadmap = Path(value["roadmap_path"])
    instructions = Path(value["instructions_path"])
    try:
        if _sha256(archive) != value["source_archive_sha256"]:
            return False
        if _sha256(roadmap) != value["roadmap_sha256"]:
            return False
        if _sha256(instructions) != value["instructions_sha256"]:
            return False
        with zipfile.ZipFile(archive) as bundle:
            matches = [
                name
                for name in bundle.namelist()
                if name == value["source_member"]
            ]
            if len(matches) != 1:
                return False
            member = bundle.read(matches[0])
        return hashlib.sha256(member).hexdigest() == value["source_member_sha256"]
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return False


def _phase3_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE3_COMMIT:
        return False
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE3_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def _index_bytes(relative: str) -> Optional[bytes]:
    completed = subprocess.run(
        ["git", "show", f":{relative}"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def _upstream_bindings_valid(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM:
        return False
    for item in value.values():
        relative = item["ref"]
        path = REPO_ROOT / relative
        if not path.is_file() or _sha256(path) != item["sha256"]:
            return False
        indexed = _index_bytes(relative)
        if indexed is None or hashlib.sha256(indexed).hexdigest() != item["sha256"]:
            return False
    return True


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("delivery contract must be a JSON object")
    return value


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    root = isinstance(contract, Mapping)
    value = dict(contract) if root else {}
    return {
        "root_exact": root and set(value) == EXPECTED_ROOT_KEYS,
        "identity_exact": root
        and value.get("schema_version") == SCHEMA_VERSION
        and value.get("stage") == "STAGE-043"
        and value.get("phase") == "Phase 4"
        and value.get("task_id") == TASK_ID
        and value.get("acceptance_id") == ACCEPTANCE_ID
        and value.get("execution_mode")
        == "ISOLATED_NON_PRODUCTION_WORKER_CRASH_RECOVERY_CLOSEOUT"
        and value.get("valid_result") == VALID_RESULT
        and value.get("contract_state")
        == "PHASE4_CLOSEOUT_EVIDENCE_ENABLED_PRODUCTION_DISABLED"
        and value.get("stage_review_status") == "pending_next_run"
        and value.get("next_gate") == REVIEW_GATE,
        "source_binding_exact_and_live": root
        and _source_binding_valid(value.get("source_binding")),
        "phase3_commit_tree_bound": root
        and _phase3_commit_bound(value.get("phase3_commit_binding")),
        "upstream_bindings_exact_indexed_and_live": root
        and _upstream_bindings_valid(value.get("upstream_bindings")),
        "delivery_shape_exact": root
        and value.get("delivery_contract") == EXPECTED_DELIVERY,
        "recovery_handling_exact": root
        and value.get("recovery_handling") == EXPECTED_RECOVERY_HANDLING,
        "operation_exclusion_exact": root
        and value.get("operation_exclusion_contract")
        == EXPECTED_OPERATION_EXCLUSION,
        "cleanup_allowlist_exact": root
        and value.get("cleanup_allowlist") == EXPECTED_CLEANUP,
        "shutdown_recovery_exact": root
        and value.get("safe_shutdown_and_recovery")
        == EXPECTED_SHUTDOWN_RECOVERY,
        "rollback_exact": root
        and value.get("rollback_contract") == EXPECTED_ROLLBACK,
        "review_gate_exact": root
        and value.get("review_gate") == EXPECTED_REVIEW_GATE,
        "limits_and_feedback_exact": root
        and value.get("known_limits") == EXPECTED_LIMITS
        and value.get("owner_feedback_contract") == EXPECTED_OWNER_FEEDBACK,
        "truth_flags_exact": root
        and value.get("truth_flags") == EXPECTED_TRUTH_FLAGS,
    }


def _delivery_reports() -> dict[str, dict[str, Any]]:
    modules = {
        key: _load_module(path, f"stage043_p4_{key}")
        for key, path in MODULE_PATHS.items()
    }
    return {
        "stage038": modules["stage038"].build_stage038_phase4_delivery_report(),
        "stage039": modules["stage039"].build_stage039_phase4_delivery_report(),
        "stage040": modules["stage040"].build_stage040_phase4_delivery_report(),
        "stage041": modules["stage041"].build_stage041_phase4_delivery_report(),
        "stage042": modules["stage042"].build_stage042_phase4_delivery_report(),
        "stage043_p3": modules["stage043_p3"].build_stage043_phase3_report(),
    }


def _pressure_proof(report: Mapping[str, Any]) -> dict[str, bool]:
    proof = report.get("backpressure_trigger_proof", {})
    if not isinstance(proof, Mapping):
        return {name: False for name in PRESSURE_SIGNALS}
    return {
        "QUEUE_SOFT_PRESSURE": (
            proof.get("QUEUE_SOFT_PRESSURE", {}).get("decision_action")
            == "THROTTLE_ADMISSION"
            and proof.get("QUEUE_SOFT_PRESSURE", {}).get(
                "persistent_write_performed"
            )
            is False
        ),
        "QUEUE_HARD_CAPACITY": (
            proof.get("QUEUE_HARD_CAPACITY", {}).get("decision_action")
            == "DENY_NEW_ADMISSION"
            and proof.get("QUEUE_HARD_CAPACITY", {}).get("job_created") is False
        ),
        "EXTERNAL_DRIVE_OFFLINE": (
            proof.get("EXTERNAL_DRIVE_OFFLINE", {}).get("decision_action")
            == "PAUSE_RESOURCE_GATE"
            and proof.get("EXTERNAL_DRIVE_OFFLINE", {}).get(
                "physical_drive_removal_performed"
            )
            is False
        ),
        "DISK_SPACE_INSUFFICIENT": (
            proof.get("DISK_SPACE_INSUFFICIENT", {}).get("decision_action")
            == "PAUSE_RESOURCE_GATE"
            and proof.get("DISK_SPACE_INSUFFICIENT", {}).get(
                "actual_disk_observation_performed"
            )
            is True
            and proof.get("DISK_SPACE_INSUFFICIENT", {}).get(
                "disk_allocation_performed"
            )
            is False
        ),
        "EXTERNAL_API_BUDGET_INSUFFICIENT": (
            proof.get("EXTERNAL_API_BUDGET_INSUFFICIENT", {}).get(
                "decision_action"
            )
            == "PAUSE_RESOURCE_GATE"
            and proof.get("EXTERNAL_API_BUDGET_INSUFFICIENT", {}).get(
                "external_api_call_performed"
            )
            is False
        ),
        "JOB_TYPE_CONCURRENCY_LIMIT_REACHED": (
            proof.get("JOB_TYPE_CONCURRENCY_LIMIT_REACHED", {}).get(
                "decision_action"
            )
            == "THROTTLE_ADMISSION"
            and proof.get("JOB_TYPE_CONCURRENCY_LIMIT_REACHED", {}).get(
                "created_job_count"
            )
            == 0
        ),
        "SAME_SOURCE_CONFLICT": (
            proof.get("SAME_SOURCE_CONFLICT", {}).get("decision_action")
            == "THROTTLE_ADMISSION"
            and proof.get("SAME_SOURCE_CONFLICT", {}).get("conflict_count", 0)
            > 0
            and proof.get("SAME_SOURCE_CONFLICT", {}).get(
                "production_lock_runtime_performed"
            )
            is False
        ),
    }


def _blank_report(
    checks: Mapping[str, bool], *, load_error: Optional[str] = None
) -> dict[str, Any]:
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-043",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "contract_valid": False,
        "delivery_contract_valid": False,
        "delivery_checks_performed": False,
        "contract_checks": dict(checks),
        "delivery_checks": {},
        "state_retry_backpressure_evidence": {},
        "phase3_recovery_evidence": {},
        "operation_exclusion_evidence": {},
        "cleanup_allowlist": {},
        "recovery_handling": {},
        "safe_shutdown_and_recovery": {},
        "rollback_steps": [],
        "known_limits": [],
        "execution_mode": None,
        "execution_ready": False,
        "stage_review_status": "not_started",
        "next_gate": P4_GATE,
        "result": "FAIL_CLOSED_MANUAL_REVIEW_REQUIRED",
        "owner_feedback_zh": "Worker 崩溃恢复 Phase 4 合同无效；保持失败关闭。",
        "load_error": load_error,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def build_stage043_phase4_delivery_report(
    contract: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    try:
        value = (
            copy.deepcopy(dict(contract))
            if isinstance(contract, Mapping)
            else load_delivery_contract()
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _blank_report(
            {"contract_loadable": False},
            load_error=f"{type(exc).__name__}: {exc}",
        )
    checks = validate_delivery_contract(value)
    contract_valid = bool(checks) and all(checks.values())
    if not contract_valid:
        return _blank_report(checks)

    try:
        reports = _delivery_reports()
    except Exception as exc:
        report = _blank_report(checks, load_error=f"{type(exc).__name__}: {exc}")
        report["contract_valid"] = True
        report["delivery_checks_performed"] = True
        report["execution_mode"] = value["execution_mode"]
        return report

    stage038 = reports["stage038"]
    stage039 = reports["stage039"]
    stage040 = reports["stage040"]
    stage041 = reports["stage041"]
    stage042 = reports["stage042"]
    phase3 = reports["stage043_p3"]

    graph = stage038.get("job_state_graph", {})
    failure = stage039.get("failure_retry_dead_letter_log", {})
    pressure = _pressure_proof(stage040)
    scenarios = phase3.get("scenario_results", {})
    process_exit = scenarios.get(
        "isolated_worker_process_exit_checkpoint_candidate", {}
    )
    exclusion = scenarios.get("same_source_four_operation_lock_exclusion", {})
    protected = scenarios.get("protected_cleanup_denied", {})
    quarantine = scenarios.get(
        "eligible_partial_output_quarantine_candidate_only", {}
    )
    transport = stage038.get("safe_shutdown", {})

    graph_summary = {
        "state_model_version": graph.get("state_model_version"),
        "job_type_count": len(graph.get("job_types", [])),
        "job_state_count": len(graph.get("job_states", [])),
        "terminal_state_count": len(graph.get("terminal_states", [])),
        "allowed_transition_count": graph.get("allowed_transition_count"),
    }
    failure_summary = {
        "attempt_count": failure.get("attempt_count"),
        "retry_count": failure.get("retry_count"),
        "final_state": failure.get("final_state"),
        "persisted": failure.get("persisted"),
        "reviewed_stage039_delivery_valid": (
            stage039.get("delivery_contract_valid") is True
            and stage039.get("result") == VALID_RESULT
        ),
    }
    state_retry_backpressure = {
        "job_state_graph": graph_summary,
        "failure_retry_log": failure_summary,
        "backpressure_trigger_proof": pressure,
        "reviewed_stage038_delivery_valid": (
            stage038.get("delivery_contract_valid") is True
            and stage038.get("result") == VALID_RESULT
        ),
        "reviewed_stage040_delivery_valid": (
            stage040.get("delivery_contract_valid") is True
            and stage040.get("result") == VALID_RESULT
        ),
    }
    phase3_evidence = {
        "scenario_count": phase3.get("scenario_count"),
        "passed_scenario_count": phase3.get("passed_scenario_count"),
        "phase2_slice_valid": phase3.get("phase2_slice_valid") is True,
        "phase3_scenarios_valid": phase3.get("scenario_validation_valid") is True,
        "isolated_process_exit": {
            "observed_exit_code": process_exit.get("observed_exit_code"),
            "stdout_empty": process_exit.get("stdout_empty") is True,
            "stderr_empty": process_exit.get("stderr_empty") is True,
            "signal_or_kill_performed": bool(
                process_exit.get("signal_or_kill_performed", False)
            ),
            "worker_restart_performed": bool(
                process_exit.get("worker_restart_performed", False)
            ),
            "process_crash_recovery_performed": bool(
                process_exit.get("process_crash_recovery_performed", False)
            ),
        },
    }
    exclusion_evidence = {
        "required_operation_family_count": len(
            exclusion.get("required_operation_families", [])
        ),
        "source_full_conflict_count": exclusion.get("source_full_conflict_count"),
        "selected_matrix_conflict_count": exclusion.get(
            "selected_matrix_conflict_count"
        ),
        "operation_invocation_count": exclusion.get("operation_invocation_count"),
        "queue_record_created_count": exclusion.get("queue_record_created_count"),
        "retry_budget_consumed_count": exclusion.get(
            "retry_budget_consumed_count"
        ),
        "all_family_checks_passed": (
            set(exclusion.get("family_checks", {})) == set(OPERATION_FAMILIES)
            and all(exclusion.get("family_checks", {}).values())
        ),
        "reviewed_stage041_delivery_valid": (
            stage041.get("delivery_contract_valid") is True
            and stage041.get("result") == VALID_RESULT
        ),
    }
    protected_results = protected.get("artifact_results", {})
    quarantine_results = quarantine.get("artifact_results", {})
    cleanup_evidence = {
        "cleanup_eligible_classes": list(CLEANUP_CLASSES),
        "protected_artifact_classes": list(PROTECTED_CLASSES),
        "protected_ref_count": len(protected_results),
        "protected_ref_checks": {
            name: (
                protected_results.get(name, {}).get("git_tracked") is True
                and protected_results.get(name, {}).get("delete_allowed") is False
                and protected_results.get(name, {}).get("delete_attempted") is False
            )
            for name in PROTECTED_CLASSES
        },
        "quarantine_candidate_checks": {
            name: (
                quarantine_results.get(name, {}).get("delete_allowed") is False
                and quarantine_results.get(name, {}).get("delete_attempted") is False
                and quarantine_results.get(name, {}).get(
                    "quarantine_reference_only"
                )
                is True
            )
            for name in CLEANUP_CLASSES
        },
        "cleanup_manifest_required": value["cleanup_allowlist"][
            "cleanup_manifest_required"
        ],
        "runtime_owner": value["cleanup_allowlist"]["runtime_owner"],
        "cleanup_runtime_performed": False,
        "delete_attempt_performed": False,
    }
    handling = copy.deepcopy(value["recovery_handling"])
    shutdown = {
        "shutdown_steps": list(SHUTDOWN_STEPS),
        "recovery_steps": list(RECOVERY_STEPS),
        "reviewed_transport_orderly_shutdown_proved": (
            transport.get("queue_closed") is True
            and transport.get("all_resource_locks_released") is True
            and transport.get("active_work_cancelled") is False
        ),
        "reviewed_transport_queue_closed": transport.get("queue_closed") is True,
        "reviewed_transport_resource_locks_released": (
            transport.get("all_resource_locks_released") is True
        ),
        "persistent_recovery_state_available_after_exit": False,
        "process_termination_performed": False,
        "automatic_process_recovery_performed": False,
    }

    delivery_checks = {
        "stage038_delivery_valid": state_retry_backpressure[
            "reviewed_stage038_delivery_valid"
        ],
        "stage039_delivery_valid": failure_summary[
            "reviewed_stage039_delivery_valid"
        ],
        "stage040_delivery_valid": state_retry_backpressure[
            "reviewed_stage040_delivery_valid"
        ],
        "stage041_delivery_valid": exclusion_evidence[
            "reviewed_stage041_delivery_valid"
        ],
        "stage042_delivery_valid": (
            stage042.get("delivery_contract_valid") is True
            and stage042.get("result") == VALID_RESULT
        ),
        "phase3_scenarios_valid": (
            phase3_evidence["phase3_scenarios_valid"]
            and phase3_evidence["scenario_count"] == 13
            and phase3_evidence["passed_scenario_count"] == 13
        ),
        "job_graph_exact": graph_summary
        == {
            "state_model_version": "ids.job_state.v1",
            "job_type_count": 8,
            "job_state_count": 11,
            "terminal_state_count": 4,
            "allowed_transition_count": 21,
        },
        "failure_retry_log_exact": failure_summary["attempt_count"] == 3
        and failure_summary["retry_count"] == 2
        and failure_summary["final_state"] == "DEAD_LETTERED"
        and failure_summary["persisted"] is False,
        "pressure_proof_exact": set(pressure) == set(PRESSURE_SIGNALS)
        and all(pressure.values()),
        "isolated_process_exit_truthful": (
            phase3_evidence["isolated_process_exit"]
            == {
                "observed_exit_code": 73,
                "stdout_empty": True,
                "stderr_empty": True,
                "signal_or_kill_performed": False,
                "worker_restart_performed": False,
                "process_crash_recovery_performed": False,
            }
        ),
        "same_source_exclusion_exact": (
            exclusion_evidence["required_operation_family_count"] == 4
            and exclusion_evidence["source_full_conflict_count"] == 25
            and exclusion_evidence["selected_matrix_conflict_count"] == 16
            and exclusion_evidence["operation_invocation_count"] == 0
            and exclusion_evidence["queue_record_created_count"] == 0
            and exclusion_evidence["retry_budget_consumed_count"] == 0
            and exclusion_evidence["all_family_checks_passed"]
        ),
        "cleanup_boundaries_exact": (
            cleanup_evidence["protected_ref_count"] == 5
            and all(cleanup_evidence["protected_ref_checks"].values())
            and all(cleanup_evidence["quarantine_candidate_checks"].values())
        ),
        "conditional_handling_not_overclaimed": (
            handling["automatic_recovery_eligible_cases"] == []
            and handling["successful_automatic_recovery_cases_observed"] == []
            and handling["automatic_recovery_performed"] is False
            and handling["current_persistent_state_available"] is False
        ),
        "safe_shutdown_recovery_fail_closed": (
            shutdown["reviewed_transport_orderly_shutdown_proved"]
            and shutdown["persistent_recovery_state_available_after_exit"] is False
            and shutdown["process_termination_performed"] is False
            and shutdown["automatic_process_recovery_performed"] is False
        ),
    }
    delivery_valid = all(delivery_checks.values())
    feedback = value["owner_feedback_contract"]
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-043",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "contract_valid": True,
        "delivery_contract_valid": delivery_valid,
        "delivery_checks_performed": True,
        "contract_checks": checks,
        "delivery_checks": delivery_checks,
        "state_retry_backpressure_evidence": state_retry_backpressure,
        "phase3_recovery_evidence": phase3_evidence,
        "operation_exclusion_evidence": exclusion_evidence,
        "cleanup_allowlist": cleanup_evidence,
        "recovery_handling": handling,
        "safe_shutdown_and_recovery": shutdown,
        "rollback_steps": list(value["rollback_contract"]["steps"]),
        "known_limits": list(value["known_limits"]),
        "execution_mode": value["execution_mode"],
        "execution_ready": False,
        "stage_review_status": value["stage_review_status"],
        "next_gate": REVIEW_GATE if delivery_valid else P4_GATE,
        "result": VALID_RESULT if delivery_valid else "FAIL_CLOSED_MANUAL_REVIEW_REQUIRED",
        "owner_feedback_zh": " ".join(feedback.values()),
        "load_error": None,
    }
    report.update(
        {name: bool(value["truth_flags"].get(name, False)) for name in TRUE_TRUTH_FLAGS}
    )
    report.update(
        {name: bool(value["truth_flags"].get(name, False)) for name in FALSE_TRUTH_FLAGS}
    )
    return report


def main() -> int:
    report = build_stage043_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["result"] == VALID_RESULT else 1


if __name__ == "__main__":
    sys.exit(main())
