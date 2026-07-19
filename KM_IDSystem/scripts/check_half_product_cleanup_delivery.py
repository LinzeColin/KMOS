#!/usr/bin/env python3
"""Fail-closed STAGE-044 Phase 4 half-product-cleanup delivery checker."""

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
    / "half_product_cleanup/stage044_half_product_cleanup_delivery_contract.json"
)
MODULE_PATHS = {
    "stage043": PROJECT_ROOT / "scripts/check_worker_crash_recovery_delivery.py",
    "stage044_p3": PROJECT_ROOT / "scripts/check_half_product_cleanup_scenarios.py",
}

SCHEMA_VERSION = "ids.stage044.half_product_cleanup.phase4.delivery.v1"
REPORT_SCHEMA_VERSION = "ids.stage044.half_product_cleanup.phase4.report.v1"
TASK_ID = "IDS-V0_1-STAGE044-P4"
ACCEPTANCE_ID = "ACC-STAGE-044"
P4_GATE = "IDS-STAGE044-P4-GATE"
REVIEW_GATE = "IDS-STAGE044-REVIEW-GATE"
VALID_RESULT = "PASS_ISOLATED_CLEANUP_CLOSEOUT_DELETE_DISABLED"
UPSTREAM_VALID_RESULT = "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
PHASE3_COMMIT = "fd1d652bbe2e9edcbf4e7c9619b55db1873b365e"
PHASE3_KMIDS_TREE = "809a7f6e32ecf57f10803f81abed964fa7cff160"

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
    "cleanup_delivery_contract",
    "automatic_recovery_and_cleanup_handling",
    "operation_exclusion_contract",
    "resource_pressure_contract",
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
        "STAGE-044_半成品输出清理.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53"
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
    "stage044_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
            "stage044_half_product_cleanup_scenarios.json"
        ),
        "sha256": "4e44e134df9cef4106bd238a5c65ab2e567a18f3528943bbd5bedf486f89dc88",
    },
    "stage044_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_half_product_cleanup_scenarios.py",
        "sha256": "c754190f4e6724508f65b02507a435a6d50be7ce9afdc9abbefa7bf06fdc63f3",
    },
    "stage044_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage044_half_product_cleanup_scenarios.py"
        ),
        "sha256": "847216fef097b1c865cc634318d81dd2b635046a8948f08a7979deb1e2826bf4",
    },
    "stage044_phase3_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE044_PHASE3_SCENARIO_VALIDATION.md"
        ),
        "sha256": "72bc72ef58325511e82a9259f9c6ad4d94ba503a02364ceed6f4cec1a3cf0444",
    },
    "stage043_delivery_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_delivery_contract.json"
        ),
        "sha256": "4d991341c09784c11ca816977727f2d8ab568559f10b6b3fc1c9edb688fdc863",
    },
    "stage043_delivery_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_crash_recovery_delivery.py",
        "sha256": "c2357b74bcb4acfc487f0b304d5668ac9ead63cbd36c0263dc8fb85481895df1",
    },
    "stage043_delivery_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE043_PHASE4_CLOSEOUT.md"
        ),
        "sha256": "5c4090af94975c2f750edccf22ea6126046ee80d37eb6c482254adf7a6790b5c",
    },
}

FORWARD_COMPATIBLE_UPSTREAM_HASHES: dict[str, set[str]] = {
    "stage044_phase3_checker": {
        "9a9349d7cc622e4038bff0b9062e42fc33b1d6a020eebbb3d10ab6e9c63d5710"
    },
    "stage044_phase3_tests": {
        "bf3d22ae93268ea1d3ad43dcac67b04a8a566ee6bed229a5eb5aee8681cbd032"
    }
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
    "required_phase3_scenario_count": 14,
    "required_phase3_passed_scenario_count": 14,
    "required_isolated_process_exit_code": 73,
    "required_source_full_conflict_count": 25,
    "required_selected_matrix_conflict_count": 16,
    "required_cleanup_eligible_class_count": 2,
    "required_protected_artifact_class_count": 14,
    "required_delete_attempt_count": 0,
    "required_deleted_ref_count": 0,
}

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
CORE_PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
EXPECTED_CLEANUP = {
    "cleanup_eligible_classes": ELIGIBLE_CLASSES,
    "protected_artifact_classes": PROTECTED_CLASSES,
    "core_protected_classes": CORE_PROTECTED_CLASSES,
    "canonical_root_and_relative_path_required": True,
    "job_attempt_creator_binding_required": True,
    "manifest_and_provenance_required": True,
    "rebuildability_required": True,
    "retention_elapsed_required": True,
    "legal_and_owner_holds_clear_required": True,
    "durable_references_absent_required": True,
    "writer_identity_and_quiescence_required": True,
    "immutable_lstat_identity_required": True,
    "exclusive_managed_namespace_lock_required": True,
    "fresh_resource_observations_required": True,
    "candidate_only": True,
    "human_review_required": True,
    "future_delete_protocol": {
        "dirfd_required": True,
        "openat_no_follow_required": True,
        "unlinkat_required": True,
        "immediate_identity_revalidation_required": True,
        "append_only_audit_required": True,
        "production_calibration_required": True,
    },
    "runtime_owner": "STAGE-044",
    "cleanup_runtime_available": False,
    "delete_execution_allowed": False,
}

UPSTREAM_RECOVERY_CANDIDATES = [
    "CHECKPOINT_RESUME_CANDIDATE_AFTER_ALL_GATES",
    "STAGE039_RETRY_CANDIDATE_AFTER_ALL_GATES",
    "SAFE_FAILURE_CANDIDATE_AFTER_ALL_GATES",
]
CONDITIONAL_CLEANUP_CANDIDATES = [
    "TEMP_STAGING_OUTPUT_AFTER_ALL_GATES",
    "INCOMPLETE_DERIVATIVE_OUTPUT_AFTER_ALL_GATES",
]
MANUAL_CASES = [
    "PROTECTED_ARTIFACT_OR_ORIGINAL_SOURCE",
    "MISSING_OR_INVALID_MANIFEST_OR_PROVENANCE",
    "ARTIFACT_NOT_REBUILDABLE",
    "RETENTION_OR_HOLD_NOT_CLEARED",
    "DURABLE_REFERENCE_PRESENT_OR_UNKNOWN",
    "ACTIVE_OR_UNKNOWN_WRITER",
    "WRITER_QUIESCENCE_NOT_PROVEN",
    "LSTAT_IDENTITY_STALE_OR_CHANGED",
    "EXCLUSIVE_NAMESPACE_LOCK_NOT_HELD",
    "SAME_SOURCE_OPERATION_CONFLICT",
    "RESOURCE_PRESSURE_OR_OBSERVATION_STALE",
    "IDEMPOTENCY_CONFLICT",
    "UNCALIBRATED_POLICY",
    "NO_PERSISTENT_CLEANUP_OR_AUDIT_STATE",
]
EXPECTED_HANDLING = {
    "upstream_conditional_recovery_candidates": UPSTREAM_RECOVERY_CANDIDATES,
    "conditional_cleanup_candidates": CONDITIONAL_CLEANUP_CANDIDATES,
    "automatic_recovery_eligible_cases": [],
    "automatic_cleanup_eligible_cases": [],
    "successful_automatic_recovery_cases_observed": [],
    "successful_cleanup_cases_observed": [],
    "manual_action_required_cases": MANUAL_CASES,
    "persistent_cleanup_state_required": True,
    "persistent_cleanup_state_available": False,
    "production_calibration_required": True,
    "production_calibrated": False,
    "owner_review_required": True,
    "automatic_recovery_performed": False,
    "automatic_cleanup_performed": False,
}

OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
EXPECTED_OPERATION_EXCLUSION = {
    "operation_families": OPERATION_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "source_full_conflict_count": 25,
    "selected_matrix_conflict_count": 16,
    "operation_invocation_allowed": False,
    "queue_record_creation_allowed": False,
    "retry_budget_consumption_allowed": False,
    "production_lock_runtime_allowed": False,
    "runtime_owner": "STAGE-041",
}
RESOURCE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
EXPECTED_RESOURCE_PRESSURE = {
    "cleanup_blocking_signals": RESOURCE_SIGNALS,
    "fresh_observation_required": True,
    "control_metadata_only": True,
    "physical_drive_removal_allowed": False,
    "disk_allocation_allowed": False,
    "external_api_call_allowed": False,
    "automatic_resume_allowed": False,
    "cleanup_candidate_allowed_while_blocked": False,
    "delete_allowed": False,
}

SHUTDOWN_STEPS = [
    "STOP_NEW_CLEANUP_EVALUATIONS",
    "STOP_NEW_CANDIDATE_DISCOVERY_BY_FUTURE_RUNTIME",
    "FREEZE_CLEANUP_CANDIDATE_LEDGER",
    "WAIT_FOR_OWNER_RUNTIME_WRITERS_AND_LOCKS_TO_QUIESCE",
    "PRESERVE_SOURCE_MANIFEST_EVIDENCE_REPORT_AND_AUDIT",
    "PRESERVE_PARTIAL_OUTPUT_AS_REFERENCE_ONLY_QUARANTINE",
    "RELEASE_ONLY_MATCHING_CLEANUP_LOCKS_BY_STAGE041_OWNER_RUNTIME",
    "CLOSE_REVIEWED_WORKER_TRANSPORT_BY_STAGE038_OWNER_RUNTIME",
    "VERIFY_NO_DELETE_PERSISTENCE_OR_RUNTIME_OUTPUT",
    "REQUIRE_MANUAL_REVIEW_FOR_UNKNOWN_OR_IN_PROGRESS_STATE",
]
RECOVERY_STEPS = [
    "VERIFY_EXACT_SOURCE_POLICY_AND_UPSTREAM_HASHES",
    "RELOAD_ONLY_DURABLE_CANDIDATE_AND_AUDIT_STATE",
    "REOBSERVE_RESOURCE_OWNER_WRITER_AND_LOCK_STATE",
    "REVALIDATE_MANIFEST_HOLDS_REFERENCES_RETENTION_AND_IDENTITY",
    "REQUIRE_WRITER_QUIESCENCE_AND_NO_ACTIVE_PRODUCER_LEASE",
    "REQUIRE_FRESH_LSTAT_IDENTITY_AT_FUTURE_RUNTIME",
    "REQUIRE_EXCLUSIVE_MANAGED_NAMESPACE_LOCK",
    "RERUN_IDEMPOTENT_CLEANUP_CANDIDATE_EVALUATION",
    "KEEP_DELETE_DISABLED_UNTIL_REVIEW_CALIBRATION_AND_RUNTIME_GATES",
    "DO_NOT_RESTORE_MISSING_IN_MEMORY_CLEANUP_STATE",
    "DO_NOT_REOPEN_TERMINAL_HISTORY",
    "DO_NOT_DELETE_AS_ROLLBACK",
]
EXPECTED_SHUTDOWN_RECOVERY = {
    "shutdown_steps": SHUTDOWN_STEPS,
    "recovery_steps": RECOVERY_STEPS,
    "persistent_cleanup_state_available_after_exit": False,
    "cleanup_in_progress_observed": False,
    "delete_operation_in_progress": False,
    "process_termination_allowed": False,
    "automatic_process_recovery_allowed": False,
}
ROLLBACK_STEPS = [
    "STOP_ON_INVALID_DELIVERY_CONTRACT",
    "STOP_NEW_CLEANUP_EVALUATIONS",
    "REQUIRE_MANUAL_REVIEW_FOR_ACTIVE_UNKNOWN_OR_UNFENCED_STATE",
    "REVERT_PHASE4_FILES_ONLY",
    "PRESERVE_PHASE1_PHASE3_EVIDENCE",
    "PRESERVE_STAGE037_STAGE043_REVIEWED_EVIDENCE",
    "PRESERVE_RAW_DATA_MANIFEST_EVIDENCE_AUDIT_AND_DELIVERED_REPORTS",
    "DO_NOT_DELETE_MOVE_OVERWRITE_OR_REOPEN_TERMINAL_HISTORY",
]
EXPECTED_ROLLBACK = {
    "steps": ROLLBACK_STEPS,
    "destructive_rollback_allowed": False,
}
EXPECTED_REVIEW_GATE = {
    "next_task_id": "IDS-V0_1-STAGE044-REVIEW",
    "must_run_separately": True,
    "phase4_may_mark_stage_reviewed": False,
    "stage045_entry_allowed": False,
    "batch_review_allowed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}
EXPECTED_LIMITS = [
    "NO_CLEANUP_SCANNER_OR_CANDIDATE_DISCOVERY_RUNTIME",
    "NO_PRODUCTION_CLEANUP_RUNTIME",
    "NO_FILESYSTEM_PROBE_OR_TRAVERSAL",
    "NO_DIRFD_OPENAT_UNLINKAT_MOVE_OVERWRITE_OR_DELETE",
    "NO_PERSISTENT_CLEANUP_CANDIDATE_OR_AUDIT_STATE",
    "NO_PRODUCTION_CALIBRATION",
    "NO_SUCCESSFUL_CLEANUP_OBSERVED",
    "NO_AUTOMATIC_RECOVERY_OR_CLEANUP_ELIGIBILITY",
    "NO_DATABASE_OR_RAW_SOURCE_ACCESS",
    "NO_STAGE044_WHOLE_STAGE_REVIEW_IN_THIS_RUN",
    "NO_STAGE045_ENTRY_IN_THIS_RUN",
    "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS",
]
EXPECTED_OWNER_FEEDBACK = {
    "status_zh": (
        "Stage044 Phase 4 隔离交付证据已收口，半成品自动清理与删除仍禁用。"
    ),
    "automatic_eligibility_zh": (
        "上游三条恢复路径和两类清理资料仅是全部门禁满足后的条件候选；"
        "当前没有自动恢复或自动清理资格，也未观察到成功清理。"
    ),
    "manual_action_zh": (
        "受保护资料、来源或 manifest 不完整、不可重建、保留期或 hold 未清、"
        "存在引用、writer 或身份未知、锁或资源不满足、幂等冲突、未校准策略和"
        "缺失持久清理状态均需要人工处理。"
    ),
    "limit_zh": (
        "下一步只能在独立 run 进行整阶段复审；本证据不是生产运行或生产就绪证明。"
    ),
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_cleanup_decisions_reexecuted",
    "phase3_cleanup_scenarios_replayed",
    "reviewed_stage043_delivery_replayed",
    "job_state_graph_replayed",
    "failure_retry_log_replayed",
    "backpressure_trigger_proof_replayed",
    "same_source_lock_evidence_replayed",
    "protected_artifacts_evaluated",
    "eligible_candidates_evaluated",
    "isolated_control_process_exit_evidence_replayed",
    "actual_project_disk_observation_performed",
    "phase4_delivery_evidence_composed",
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
    "automatic_cleanup_performed",
    "successful_cleanup_observed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "cleanup_runtime_performed",
    "cleanup_scan_performed",
    "filesystem_probe_performed",
    "filesystem_traversal_performed",
    "writer_quiescence_probe_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "dirfd_open_performed",
    "openat_called",
    "unlinkat_called",
    "move_or_overwrite_performed",
    "delete_operation_started",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
    "audit_write_performed",
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
    "stage045_entry_allowed",
}
EXPECTED_TRUTH_FLAGS = {
    **{name: True for name in TRUE_TRUTH_FLAGS},
    **{name: False for name in FALSE_TRUTH_FLAGS},
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


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
    archive = Path(EXPECTED_SOURCE["source_archive_path"])
    roadmap = Path(EXPECTED_SOURCE["roadmap_path"])
    instructions = Path(EXPECTED_SOURCE["instructions_path"])
    try:
        if _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]:
            return False
        if _sha256(roadmap) != EXPECTED_SOURCE["roadmap_sha256"]:
            return False
        if _sha256(instructions) != EXPECTED_SOURCE["instructions_sha256"]:
            return False
        member = EXPECTED_SOURCE["source_member"]
        with zipfile.ZipFile(archive) as source_zip:
            matches = [name for name in source_zip.namelist() if name == member]
            return (
                len(matches) == EXPECTED_SOURCE["source_member_match_count"]
                and _sha256_bytes(source_zip.read(member))
                == EXPECTED_SOURCE["source_member_sha256"]
            )
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def _phase3_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE3_COMMIT:
        return False
    try:
        tree = subprocess.run(
            ["git", "rev-parse", f"{PHASE3_COMMIT}:KM_IDSystem"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", PHASE3_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return tree == PHASE3_KMIDS_TREE and ancestor


def _safe_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("KM_IDSystem/"):
        return False
    path = Path(value)
    return path.is_absolute() is False and ".." not in path.parts


def _index_bytes(relative: str) -> Optional[bytes]:
    result = subprocess.run(
        ["git", "show", f":{relative}"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def _upstream_bindings_valid(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM:
        return False
    try:
        for name, binding in EXPECTED_UPSTREAM.items():
            relative = binding["ref"]
            if not _safe_repo_ref(relative):
                return False
            path = REPO_ROOT / relative
            current = path.read_bytes()
            indexed = _index_bytes(relative)
            allowed = {binding["sha256"]} | FORWARD_COMPATIBLE_UPSTREAM_HASHES.get(
                name, set()
            )
            if (
                indexed is None
                or indexed != current
                or _sha256_bytes(current) not in allowed
            ):
                return False
    except (OSError, KeyError, TypeError):
        return False
    return True


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("delivery contract must be an object")
    return value


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    root = isinstance(contract, Mapping)
    value = dict(contract) if root else {}
    return {
        "root_shape_exact": root and set(value) == EXPECTED_ROOT_KEYS,
        "identity_exact": root
        and value.get("schema_version") == SCHEMA_VERSION
        and value.get("stage") == "STAGE-044"
        and value.get("phase") == "Phase 4"
        and value.get("task_id") == TASK_ID
        and value.get("acceptance_id") == ACCEPTANCE_ID
        and value.get("execution_mode")
        == "ISOLATED_NON_PRODUCTION_HALF_PRODUCT_CLEANUP_CLOSEOUT"
        and value.get("valid_result") == VALID_RESULT
        and value.get("contract_state")
        == "PHASE4_CLOSEOUT_EVIDENCE_ENABLED_DELETE_DISABLED"
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
        "cleanup_delivery_exact": root
        and value.get("cleanup_delivery_contract") == EXPECTED_CLEANUP,
        "automatic_and_manual_handling_exact": root
        and value.get("automatic_recovery_and_cleanup_handling")
        == EXPECTED_HANDLING,
        "operation_exclusion_exact": root
        and value.get("operation_exclusion_contract")
        == EXPECTED_OPERATION_EXCLUSION,
        "resource_pressure_exact": root
        and value.get("resource_pressure_contract")
        == EXPECTED_RESOURCE_PRESSURE,
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
        key: _load_module(path, f"stage044_p4_{key}")
        for key, path in MODULE_PATHS.items()
    }
    return {
        "stage043": modules["stage043"].build_stage043_phase4_delivery_report(),
        "stage044_p3": modules["stage044_p3"].build_stage044_phase3_report(),
    }


def _blank_report(
    checks: Mapping[str, bool], *, load_error: Optional[str] = None
) -> dict[str, Any]:
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-044",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "contract_valid": False,
        "delivery_contract_valid": False,
        "delivery_checks_performed": False,
        "contract_checks": dict(checks),
        "delivery_checks": {},
        "state_retry_backpressure_evidence": {},
        "phase3_cleanup_evidence": {},
        "cleanup_allowlist": {},
        "automatic_recovery_and_cleanup_handling": {},
        "operation_exclusion_evidence": {},
        "resource_pressure_evidence": {},
        "safe_shutdown_and_recovery": {},
        "rollback_steps": [],
        "known_limits": [],
        "execution_mode": None,
        "execution_ready": False,
        "stage_review_status": "not_started",
        "next_gate": P4_GATE,
        "result": "FAIL_CLOSED_MANUAL_REVIEW_REQUIRED",
        "owner_feedback_zh": "半成品清理 Phase 4 合同无效；保持失败关闭。",
        "load_error": load_error,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def build_stage044_phase4_delivery_report(
    contract: Optional[Mapping[str, Any]] = None,
    *,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    if contract is not None and not isinstance(contract, Mapping):
        return _blank_report({"contract_mapping": False})
    try:
        value = (
            copy.deepcopy(dict(contract))
            if isinstance(contract, Mapping)
            else load_delivery_contract(contract_path)
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

    stage043 = reports["stage043"]
    phase3 = reports["stage044_p3"]
    state_evidence = copy.deepcopy(
        stage043.get("state_retry_backpressure_evidence", {})
    )
    scenarios = phase3.get("scenario_results", {})
    worker_exit = scenarios.get(
        "isolated_worker_exit_partial_output_candidate_only", {}
    )
    protected = scenarios.get("all_protected_classes_denied", {})
    eligible = scenarios.get(
        "eligible_candidate_review_only_delete_disabled", {}
    )
    exclusion = scenarios.get("same_source_four_operation_lock_exclusion", {})

    protected_results = protected.get("artifact_results", {})
    protected_checks = {
        name: (
            protected_results.get(name, {}).get("decision_action")
            == "CLEANUP_BLOCKED_PROTECTED"
            and protected_results.get(name, {}).get("delete_allowed") is False
            and protected_results.get(name, {}).get("delete_attempted") is False
        )
        for name in PROTECTED_CLASSES
    }
    eligible_scenario_valid = (
        eligible.get("status") == "PASS"
        and eligible.get("decision_action") == "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        and eligible.get("candidate_only") is True
        and eligible.get("delete_allowed") is False
        and eligible.get("cleanup_runtime_performed") is False
    )
    cleanup_evidence = {
        "cleanup_eligible_classes": list(ELIGIBLE_CLASSES),
        "protected_artifact_classes": list(PROTECTED_CLASSES),
        "core_protected_classes": list(CORE_PROTECTED_CLASSES),
        "protected_ref_count": len(protected_results),
        "protected_ref_checks": protected_checks,
        "candidate_checks": {
            name: eligible_scenario_valid for name in ELIGIBLE_CLASSES
        },
        "candidate_only": True,
        "human_review_required": True,
        "runtime_owner": "STAGE-044",
        "cleanup_runtime_available": False,
        "delete_execution_allowed": False,
        "cleanup_runtime_performed": False,
        "delete_attempt_performed": False,
    }
    phase3_evidence = {
        "scenario_count": phase3.get("scenario_count"),
        "passed_scenario_count": phase3.get("passed_scenario_count"),
        "phase2_slice_valid": phase3.get("phase2_slice_valid") is True,
        "phase3_scenarios_valid": phase3.get("scenario_validation_valid") is True,
        "isolated_process_exit_code": worker_exit.get("upstream_exit_code"),
        "delete_attempt_count": protected.get("delete_attempt_count"),
        "deleted_ref_count": protected.get("deleted_ref_count"),
    }
    exclusion_evidence = {
        "operation_families": list(
            exclusion.get("required_operation_families", [])
        ),
        "source_full_conflict_count": exclusion.get(
            "source_full_conflict_count"
        ),
        "selected_matrix_conflict_count": exclusion.get(
            "selected_matrix_conflict_count"
        ),
        "operation_invocation_count": exclusion.get("operation_invocation_count"),
        "queue_record_created_count": exclusion.get(
            "queue_record_created_count"
        ),
        "retry_budget_consumed_count": exclusion.get(
            "retry_budget_consumed_count"
        ),
        "all_family_checks_passed": (
            set(exclusion.get("family_checks", {})) == set(OPERATION_FAMILIES)
            and all(exclusion.get("family_checks", {}).values())
        ),
        "production_lock_runtime_performed": False,
    }
    resource_evidence = {
        "EXTERNAL_DRIVE_OFFLINE": (
            scenarios.get("external_drive_offline_blocked", {}).get("status")
            == "PASS"
            and scenarios.get("external_drive_offline_blocked", {}).get(
                "delete_allowed"
            )
            is False
            and scenarios.get("external_drive_offline_blocked", {}).get(
                "physical_drive_removal_performed"
            )
            is False
        ),
        "DISK_SPACE_INSUFFICIENT": (
            scenarios.get("low_disk_blocked", {}).get("status") == "PASS"
            and scenarios.get("low_disk_blocked", {}).get("delete_allowed")
            is False
            and scenarios.get("low_disk_blocked", {}).get(
                "disk_allocation_performed"
            )
            is False
        ),
        "EXTERNAL_API_BUDGET_INSUFFICIENT": (
            scenarios.get("api_budget_blocked", {}).get("status") == "PASS"
            and scenarios.get("api_budget_blocked", {}).get("delete_allowed")
            is False
            and scenarios.get("api_budget_blocked", {}).get(
                "external_api_call_performed"
            )
            is False
        ),
    }
    handling = copy.deepcopy(value["automatic_recovery_and_cleanup_handling"])
    upstream_shutdown = stage043.get("safe_shutdown_and_recovery", {})
    shutdown = {
        "shutdown_steps": list(SHUTDOWN_STEPS),
        "recovery_steps": list(RECOVERY_STEPS),
        "reviewed_transport_orderly_shutdown_proved": upstream_shutdown.get(
            "reviewed_transport_orderly_shutdown_proved"
        )
        is True,
        "reviewed_transport_queue_closed": upstream_shutdown.get(
            "reviewed_transport_queue_closed"
        )
        is True,
        "reviewed_transport_resource_locks_released": upstream_shutdown.get(
            "reviewed_transport_resource_locks_released"
        )
        is True,
        "persistent_cleanup_state_available_after_exit": False,
        "cleanup_in_progress_observed": False,
        "delete_operation_in_progress": False,
        "process_termination_performed": False,
        "automatic_process_recovery_performed": False,
    }

    graph = state_evidence.get("job_state_graph", {})
    failure = state_evidence.get("failure_retry_log", {})
    pressure = state_evidence.get("backpressure_trigger_proof", {})
    stage043_valid = (
        stage043.get("delivery_contract_valid") is True
        and stage043.get("result") == UPSTREAM_VALID_RESULT
    )
    phase3_valid = (
        phase3.get("scenario_validation_valid") is True
        and phase3.get("result")
        == "PASS_ISOLATED_CLEANUP_SCENARIOS_DELETE_DISABLED"
    )
    delivery_checks = {
        "stage043_delivery_valid": stage043_valid,
        "phase3_scenarios_valid": phase3_valid,
        "job_graph_exact": graph
        == {
            "state_model_version": "ids.job_state.v1",
            "job_type_count": 8,
            "job_state_count": 11,
            "terminal_state_count": 4,
            "allowed_transition_count": 21,
        },
        "failure_retry_log_exact": (
            failure.get("attempt_count") == 3
            and failure.get("retry_count") == 2
            and failure.get("final_state") == "DEAD_LETTERED"
            and failure.get("persisted") is False
        ),
        "backpressure_proof_exact": (
            set(pressure) == set(PRESSURE_SIGNALS) and all(pressure.values())
        ),
        "phase3_cleanup_evidence_exact": (
            phase3_evidence
            == {
                "scenario_count": 14,
                "passed_scenario_count": 14,
                "phase2_slice_valid": True,
                "phase3_scenarios_valid": True,
                "isolated_process_exit_code": 73,
                "delete_attempt_count": 0,
                "deleted_ref_count": 0,
            }
        ),
        "protected_artifacts_exact": (
            cleanup_evidence["protected_ref_count"] == 14
            and set(protected_checks) == set(PROTECTED_CLASSES)
            and all(protected_checks.values())
        ),
        "cleanup_candidates_exact_and_delete_disabled": (
            set(cleanup_evidence["candidate_checks"]) == set(ELIGIBLE_CLASSES)
            and all(cleanup_evidence["candidate_checks"].values())
            and cleanup_evidence["delete_execution_allowed"] is False
        ),
        "same_source_exclusion_exact": (
            set(exclusion_evidence["operation_families"])
            == set(OPERATION_FAMILIES)
            and exclusion_evidence["source_full_conflict_count"] == 25
            and exclusion_evidence["selected_matrix_conflict_count"] == 16
            and exclusion_evidence["operation_invocation_count"] == 0
            and exclusion_evidence["queue_record_created_count"] == 0
            and exclusion_evidence["retry_budget_consumed_count"] == 0
            and exclusion_evidence["all_family_checks_passed"]
        ),
        "resource_pressure_blocks_cleanup": (
            set(resource_evidence) == set(RESOURCE_SIGNALS)
            and all(resource_evidence.values())
        ),
        "automatic_and_manual_handling_not_overclaimed": (
            handling["automatic_recovery_eligible_cases"] == []
            and handling["automatic_cleanup_eligible_cases"] == []
            and handling["successful_automatic_recovery_cases_observed"] == []
            and handling["successful_cleanup_cases_observed"] == []
            and handling["persistent_cleanup_state_available"] is False
            and handling["automatic_recovery_performed"] is False
            and handling["automatic_cleanup_performed"] is False
        ),
        "safe_shutdown_and_recovery_fail_closed": (
            shutdown["reviewed_transport_orderly_shutdown_proved"]
            and shutdown["persistent_cleanup_state_available_after_exit"] is False
            and shutdown["cleanup_in_progress_observed"] is False
            and shutdown["delete_operation_in_progress"] is False
            and shutdown["process_termination_performed"] is False
            and shutdown["automatic_process_recovery_performed"] is False
        ),
    }
    delivery_valid = all(delivery_checks.values())
    feedback = value["owner_feedback_contract"]
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-044",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "contract_valid": True,
        "delivery_contract_valid": delivery_valid,
        "delivery_checks_performed": True,
        "contract_checks": checks,
        "delivery_checks": delivery_checks,
        "state_retry_backpressure_evidence": state_evidence,
        "phase3_cleanup_evidence": phase3_evidence,
        "cleanup_allowlist": cleanup_evidence,
        "automatic_recovery_and_cleanup_handling": handling,
        "operation_exclusion_evidence": exclusion_evidence,
        "resource_pressure_evidence": resource_evidence,
        "safe_shutdown_and_recovery": shutdown,
        "rollback_steps": list(value["rollback_contract"]["steps"]),
        "known_limits": list(value["known_limits"]),
        "execution_mode": value["execution_mode"],
        "execution_ready": False,
        "stage_review_status": value["stage_review_status"],
        "next_gate": REVIEW_GATE if delivery_valid else P4_GATE,
        "result": (
            VALID_RESULT if delivery_valid else "FAIL_CLOSED_MANUAL_REVIEW_REQUIRED"
        ),
        "owner_feedback_zh": " ".join(feedback.values()),
        "load_error": None,
    }
    derived_true = {
        "phase2_cleanup_decisions_reexecuted": (
            phase3.get("phase2_cleanup_decisions_reexecuted") is True
        ),
        "phase3_cleanup_scenarios_replayed": phase3_valid,
        "reviewed_stage043_delivery_replayed": stage043_valid,
        "job_state_graph_replayed": delivery_checks["job_graph_exact"],
        "failure_retry_log_replayed": delivery_checks["failure_retry_log_exact"],
        "backpressure_trigger_proof_replayed": delivery_checks[
            "backpressure_proof_exact"
        ],
        "same_source_lock_evidence_replayed": delivery_checks[
            "same_source_exclusion_exact"
        ],
        "protected_artifacts_evaluated": delivery_checks[
            "protected_artifacts_exact"
        ],
        "eligible_candidates_evaluated": delivery_checks[
            "cleanup_candidates_exact_and_delete_disabled"
        ],
        "isolated_control_process_exit_evidence_replayed": (
            phase3_evidence["isolated_process_exit_code"] == 73
        ),
        "actual_project_disk_observation_performed": (
            phase3.get("actual_project_disk_observation_performed") is True
        ),
        "phase4_delivery_evidence_composed": True,
    }
    report.update(
        {
            name: bool(derived_true.get(name, value["truth_flags"].get(name, False)))
            for name in TRUE_TRUTH_FLAGS
        }
    )
    report.update(
        {name: bool(value["truth_flags"].get(name, False)) for name in FALSE_TRUTH_FLAGS}
    )
    return report


def main() -> int:
    report = build_stage044_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["result"] == VALID_RESULT else 1


if __name__ == "__main__":
    sys.exit(main())
