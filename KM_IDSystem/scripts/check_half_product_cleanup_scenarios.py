#!/usr/bin/env python3
"""Fail-closed STAGE-044 Phase 3 half-product cleanup scenarios."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping, Optional
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
CONTRACT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "half_product_cleanup"
    / "stage044_half_product_cleanup_scenarios.json"
)
PHASE2_CHECKER_PATH = PROJECT_ROOT / "scripts" / "check_half_product_cleanup_runtime.py"
STAGE043_SCENARIO_CHECKER_PATH = (
    PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_scenarios.py"
)

TASK_ID = "IDS-V0_1-STAGE044-P3"
ACCEPTANCE_ID = "ACC-STAGE-044"
POLICY_VERSION = "ids.half_product_cleanup_policy.v0_1.stage044.p2"
SCHEMA_VERSION = "ids.stage044.half_product_cleanup.phase3.scenarios.v1"
SCENARIO_CONTRACT_ID = "ids.half_product_cleanup_policy.v0_1.stage044.p3.scenarios"
EXECUTION_MODE = "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_HALF_PRODUCT_CLEANUP_SCENARIOS"
CONTRACT_STATE = "PHASE3_SCENARIOS_ENABLED_DELETE_DISABLED"

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
    "source_member_sha256": (
        "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53"
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
EXPECTED_PHASE2_COMMIT = {
    "commit": "4867bb14f1ff87231d4dd6f4ebae7251d60be585",
    "km_ids_tree": "790114d3ce9e3e416d70c64da467ff148ceb848c",
    "required_ancestor_of_head": True,
}
EXPECTED_UPSTREAM = {
    "stage044_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
            "stage044_half_product_cleanup_runtime_contract.json"
        ),
        "sha256": "b0cf212df7ceef136f6ae0ec0adf89c1fefe9b1fd2159346b1c9d1b9444b3adb",
    },
    "stage044_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_half_product_cleanup_runtime.py",
        "sha256": "4dac82daf97f19ef3a385d57f4a7b39709c0b8b87724ea0346ec3378778715e9",
    },
    "stage044_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage044_half_product_cleanup_runtime.py"
        ),
        "sha256": "7b6e7578ae58db7c74574d31feb0553cef5bc38a41cb8fdb00fd6e20b4055697",
    },
    "stage044_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE044_PHASE2_HALF_PRODUCT_CLEANUP_SLICE.md"
        ),
        "sha256": "0657726f1f3baf4b215021b86cdf8f444a3044660ce4842dc0e0ee4bd74116a7",
    },
    "stage041_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_scenarios.json"
        ),
        "sha256": "0866db20e070d1b93981f4b7b4180977f3221395310f1194ddcaa14556268c19",
    },
    "stage041_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_lock_registry_scenarios.py",
        "sha256": "fa46f374e4708c15b0d3e856e42e55f1c784dd926278ad86a8610878b59d606e",
    },
    "stage041_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage041_lock_registry_scenarios.py"
        ),
        "sha256": "6b235e04b64ba09278821abaf0bd5258e40f8b5f03f56c395dba68ab8177e088",
    },
    "stage043_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_scenarios.json"
        ),
        "sha256": "4dcdcc6cc179c27c824f071fd4b4302ddadcbb54b718998d5629c81d195ab371",
    },
    "stage043_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_crash_recovery_scenarios.py",
        "sha256": "cefb69b019b8c47bfb5b846d89b0d9d7c8113ecf632980161f231401de114d0d",
    },
    "stage043_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage043_worker_crash_recovery_scenarios.py"
        ),
        "sha256": "8a020baa2d40ff54e406a3dea9b9f4d6c4775b3f37ed1232e660e0989bb97da7",
    },
    "stage043_phase3_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE043_PHASE3_SCENARIO_VALIDATION.md"
        ),
        "sha256": "10543e29ac87feb207ac14e656836d4a416470a36bafa3fd6f279960313b35bd",
    },
}

# Historical Phase 2 evidence remains bound to the committed digest. Later
# governance-only tests may add one exact current digest here without rewriting
# the Phase 2 commit contract.
FORWARD_COMPATIBLE_UPSTREAM_HASHES: dict[str, set[str]] = {
    "stage044_phase2_tests": {
        "82a02a9a9802e7a8a0ef68752eb397f915a735582cb5777bdd571734bbdbab29"
    }
}

SCENARIO_CATALOG = [
    "duplicate_cleanup_request_exact_replay",
    "changed_payload_same_request_rejected",
    "isolated_worker_exit_partial_output_candidate_only",
    "external_drive_offline_blocked",
    "low_disk_blocked",
    "api_budget_blocked",
    "active_writer_blocked",
    "unknown_writer_or_quiescence_blocked",
    "stale_lstat_identity_blocked",
    "concurrent_same_file_lock_conflict_blocked",
    "same_source_four_operation_lock_exclusion",
    "core_protected_artifacts_denied",
    "all_protected_classes_denied",
    "eligible_candidate_review_only_delete_disabled",
]
EXPECTED_SCENARIO_EXPECTATIONS = {
    "duplicate_cleanup_request_exact_replay": (
        "EXACT_REPLAY_ONE_LEDGER_RECORD_DELETE_DISABLED"
    ),
    "changed_payload_same_request_rejected": (
        "SAME_REQUEST_ID_CHANGED_PAYLOAD_CONFLICT_NO_EFFECT"
    ),
    "isolated_worker_exit_partial_output_candidate_only": (
        "REVIEWED_ISOLATED_WORKER_EXIT_PARTIAL_OUTPUT_CANDIDATE_ONLY_NO_DELETE"
    ),
    "external_drive_offline_blocked": (
        "CONTROLLED_DRIVE_SIGNAL_BLOCKS_NO_PHYSICAL_REMOVAL"
    ),
    "low_disk_blocked": "CONTROLLED_LOW_DISK_SIGNAL_BLOCKS_NO_ALLOCATION",
    "api_budget_blocked": (
        "CONTROLLED_API_BUDGET_SIGNAL_BLOCKS_NO_EXTERNAL_CALL"
    ),
    "active_writer_blocked": "ACTIVE_JOB_STATE_BLOCKS_CLEANUP",
    "unknown_writer_or_quiescence_blocked": (
        "UNKNOWN_WRITER_OR_QUIESCENCE_EVIDENCE_BLOCKS_CLEANUP"
    ),
    "stale_lstat_identity_blocked": (
        "STALE_LSTAT_IDENTITY_BLOCKS_WITHOUT_FILESYSTEM_PROBE"
    ),
    "concurrent_same_file_lock_conflict_blocked": (
        "SAME_PATH_LOCK_CONFLICT_BLOCKS_WITHOUT_OPERATION"
    ),
    "same_source_four_operation_lock_exclusion": (
        "PROCESS_EXTRACT_INDEX_REPORT_SHARE_SOURCE_PIPELINE_EXCLUSION"
    ),
    "core_protected_artifacts_denied": (
        "FACT_MANIFEST_EVIDENCE_REPORT_AUDIT_ALWAYS_PROTECTED"
    ),
    "all_protected_classes_denied": (
        "ALL_FOURTEEN_PROTECTED_CLASSES_NEVER_DELETE"
    ),
    "eligible_candidate_review_only_delete_disabled": (
        "ELIGIBLE_REFERENCE_ONLY_CANDIDATE_REQUIRES_REVIEW_DELETE_DISABLED"
    ),
}

RESOURCE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
CORE_PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
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
ELIGIBLE_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]

EXPECTED_WORKER_CRASH = {
    "source_stage": "STAGE-043",
    "source_scenario": "isolated_worker_process_exit_checkpoint_candidate",
    "reference_only_reuse": True,
    "isolated_control_process_allowed": True,
    "expected_self_exit_code": 73,
    "production_worker_crash_allowed": False,
    "crash_injection_allowed": False,
    "signal_or_kill_allowed": False,
    "process_crash_recovery_allowed": False,
    "worker_restart_allowed": False,
    "cleanup_execution_allowed": False,
    "interpretation": (
        "REVIEWED_CONTROL_PROCESS_EXIT_PROVES_ONLY_PARTIAL_OUTPUT_DECISION_BOUNDARY"
    ),
}
EXPECTED_RESOURCE_PRESSURE = {
    "signals": RESOURCE_SIGNALS,
    "control_metadata_only": True,
    "physical_drive_removal_allowed": False,
    "disk_allocation_allowed": False,
    "external_api_call_allowed": False,
    "automatic_resume_allowed": False,
    "cleanup_candidate_allowed_while_blocked": False,
    "delete_allowed": False,
}
EXPECTED_WRITER_IDENTITY = {
    "active_or_insufficient_states": [
        "CREATED",
        "QUEUED",
        "CLAIMED",
        "RUNNING",
        "PAUSE_REQUESTED",
        "SUCCEEDED",
    ],
    "exclusive_namespace_lock_required": True,
    "managed_lock_required": True,
    "producer_and_cleanup_leases_absent_or_fenced_required": True,
    "writer_quiescence_required": True,
    "immutable_lstat_identity_required": True,
    "actual_writer_probe_allowed": False,
    "filesystem_probe_allowed": False,
    "stale_or_unknown_evidence_action": "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
}
EXPECTED_OPERATION_EXCLUSION = {
    "source_scenario_contract_id": (
        "ids.lock_registry_policy.v0_1.stage041.p3.scenarios"
    ),
    "required_operation_families": LOCK_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "same_source_reference_required": True,
    "source_full_matrix_conflict_count": 25,
    "selected_matrix_conflict_count": 16,
    "operation_invocation_count": 0,
    "queue_record_created_count": 0,
    "retry_budget_consumed_count": 0,
    "production_lock_runtime_allowed": False,
}
EXPECTED_PROTECTED = {
    "required_core_classes": CORE_PROTECTED_CLASSES,
    "all_protected_classes": PROTECTED_CLASSES,
    "eligible_candidate_classes": ELIGIBLE_CLASSES,
    "candidate_only": True,
    "delete_attempt_allowed": False,
    "delete_api_call_allowed": False,
    "cleanup_runtime_allowed": False,
    "override_allowed": False,
}
EXPECTED_OWNERSHIP = {
    "queue_and_worker_transport": "STAGE-038",
    "retry_and_dead_letter_policy": "STAGE-039",
    "backpressure_and_resource_pause": "STAGE-040",
    "lock_lease_and_fencing_runtime": "STAGE-041",
    "automatic_lifecycle": "STAGE-042",
    "process_crash_recovery_candidates": "STAGE-043",
    "half_product_cleanup_candidates": "STAGE-044",
    "phase3_transfers_no_runtime_ownership": True,
}
EXPECTED_HUMAN_STATUS = {
    "CLEANUP_CANDIDATE_REVIEW_REQUIRED": "清理候选待人工复核，删除仍禁用",
    "CLEANUP_BLOCKED_RESOURCE": "资源条件不足，清理已阻断",
    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN": "任务仍活动或证据未知，清理已阻断",
    "CLEANUP_BLOCKED_PROTECTED": "受保护资料不可清理",
    "REQUIRE_MANUAL_REVIEW": "清理请求无效或冲突，需要人工复核",
}
EXPECTED_PHASE4_GATE = {
    "entry_authorized_after_scenario_pass": True,
    "required_task_id": "IDS-V0_1-STAGE044-P4",
    "required_acceptance_id": "ACC-STAGE-044",
    "must_run_separately": True,
    "whole_stage_review_allowed_in_phase3": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
    "next_gate": "IDS-STAGE044-P4-GATE",
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_cleanup_decisions_reexecuted",
    "isolated_cleanup_scenarios_performed",
    "duplicate_scenarios_performed",
    "worker_crash_evidence_replayed",
    "isolated_control_process_started",
    "isolated_worker_process_exit_observed",
    "actual_project_disk_observation_performed",
    "resource_pressure_scenarios_performed",
    "writer_identity_scenarios_performed",
    "stage041_lock_scenarios_replayed",
    "stage043_crash_scenarios_replayed",
    "protected_artifacts_evaluated",
    "eligible_candidate_evaluated",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "cleanup_scan_performed",
    "actual_worker_process_crash_performed",
    "process_probe_performed",
    "signal_or_kill_performed",
    "crash_injected",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "worker_restart_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "writer_quiescence_probe_performed",
    "filesystem_probe_performed",
    "filesystem_traversal_performed",
    "production_lock_runtime_performed",
    "openat_called",
    "delete_operation_started",
    "unlinkat_called",
    "move_or_overwrite_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "state_transition_performed",
    "terminal_result_changed",
    "persistent_state_write_performed",
    "audit_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
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
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "execution_mode",
    "scenario_contract_id",
    "contract_state",
    "next_gate",
    "source_binding",
    "phase2_commit_binding",
    "upstream_bindings",
    "policy_version",
    "scenario_catalog",
    "scenario_expectations",
    "worker_crash_evidence_contract",
    "resource_pressure_contract",
    "writer_identity_contract",
    "operation_exclusion_contract",
    "protected_artifact_contract",
    "ownership_matrix",
    "human_status_contract",
    "phase4_entry_gate",
    "truth_flags",
}

_PHASE2_MODULE: Any = None
_STAGE043_MODULE: Any = None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_module() -> Any:
    global _PHASE2_MODULE
    if _PHASE2_MODULE is None:
        _PHASE2_MODULE = _load_module(
            PHASE2_CHECKER_PATH, "stage044_phase2_checker_for_phase3"
        )
    return _PHASE2_MODULE


def _stage043_module() -> Any:
    global _STAGE043_MODULE
    if _STAGE043_MODULE is None:
        _STAGE043_MODULE = _load_module(
            STAGE043_SCENARIO_CHECKER_PATH,
            "stage043_scenario_checker_for_stage044",
        )
    return _STAGE043_MODULE


def load_scenario_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("scenario contract must be an object")
    return value


def _source_binding_valid(value: Any) -> bool:
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
            if source_zip.namelist().count(member) != 1:
                return False
            return (
                hashlib.sha256(source_zip.read(member)).hexdigest()
                == EXPECTED_SOURCE["source_member_sha256"]
            )
    except (OSError, KeyError, ValueError):
        return False


def _phase2_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE2_COMMIT:
        return False
    try:
        observed_tree = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"{EXPECTED_PHASE2_COMMIT['commit']}:KM_IDSystem",
            ],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                EXPECTED_PHASE2_COMMIT["commit"],
                "HEAD",
            ],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return observed_tree == EXPECTED_PHASE2_COMMIT["km_ids_tree"] and ancestor


def _safe_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("KM_IDSystem/"):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in value


def _git_tracked_repo_ref(value: Any) -> bool:
    if not _safe_repo_ref(value):
        return False
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", value],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _upstream_bindings_valid(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM:
        return False
    try:
        for name, binding in EXPECTED_UPSTREAM.items():
            ref = binding["ref"]
            actual = sha256_file(REPO_ROOT / ref)
            allowed = FORWARD_COMPATIBLE_UPSTREAM_HASHES.get(
                name, {binding["sha256"]}
            )
            if actual not in allowed or not _git_tracked_repo_ref(ref):
                return False
    except (OSError, KeyError):
        return False
    return True


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, Mapping):
        return {"contract_object": False}
    return {
        "contract_object": True,
        "root_shape_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version") == SCHEMA_VERSION
            and contract.get("stage") == "STAGE-044"
            and contract.get("phase") == "Phase 3"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("execution_mode") == EXECUTION_MODE
            and contract.get("scenario_contract_id") == SCENARIO_CONTRACT_ID
            and contract.get("contract_state") == CONTRACT_STATE
            and contract.get("next_gate") == "IDS-STAGE044-P4-GATE"
        ),
        "source_binding_exact": _source_binding_valid(contract.get("source_binding")),
        "phase2_commit_bound": _phase2_commit_bound(
            contract.get("phase2_commit_binding")
        ),
        "upstream_bindings_exact": _upstream_bindings_valid(
            contract.get("upstream_bindings")
        ),
        "policy_version_exact": contract.get("policy_version") == POLICY_VERSION,
        "scenario_catalog_exact": contract.get("scenario_catalog") == SCENARIO_CATALOG,
        "scenario_expectations_exact": (
            contract.get("scenario_expectations") == EXPECTED_SCENARIO_EXPECTATIONS
        ),
        "worker_crash_contract_exact": (
            contract.get("worker_crash_evidence_contract") == EXPECTED_WORKER_CRASH
        ),
        "resource_pressure_contract_exact": (
            contract.get("resource_pressure_contract") == EXPECTED_RESOURCE_PRESSURE
        ),
        "writer_identity_contract_exact": (
            contract.get("writer_identity_contract") == EXPECTED_WRITER_IDENTITY
        ),
        "operation_exclusion_contract_exact": (
            contract.get("operation_exclusion_contract")
            == EXPECTED_OPERATION_EXCLUSION
        ),
        "protected_artifact_contract_exact": (
            contract.get("protected_artifact_contract") == EXPECTED_PROTECTED
        ),
        "ownership_exact": contract.get("ownership_matrix") == EXPECTED_OWNERSHIP,
        "human_status_exact": (
            contract.get("human_status_contract") == EXPECTED_HUMAN_STATUS
        ),
        "phase4_gate_exact": contract.get("phase4_entry_gate") == EXPECTED_PHASE4_GATE,
        "truth_flags_exact": contract.get("truth_flags") == EXPECTED_TRUTH_FLAGS,
    }


def _decision_has_no_effects(result: Mapping[str, Any]) -> bool:
    return all(
        result.get(name) is False
        for name in (
            "delete_allowed",
            "filesystem_traversal_performed",
            "production_lock_acquired",
            "state_transition_performed",
            "audit_write_performed",
        )
    )


def _duplicate_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    ledger = phase2.InMemoryCleanupDecisionLedger()
    request = phase2.build_cleanup_request()
    first = phase2.evaluate_cleanup_candidate(request, contract=contract, ledger=ledger)
    replay = phase2.evaluate_cleanup_candidate(
        copy.deepcopy(request), contract=contract, ledger=ledger
    )
    count = len(getattr(ledger, "_records", {}))
    passed = (
        first.get("decision_action") == "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        and first == replay
        and count == 1
        and _decision_has_no_effects(first)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": first.get("decision_action"),
        "reason_code": first.get("reason_code"),
        "replay_equal": first == replay,
        "ledger_record_count": count,
        "delete_allowed": bool(first.get("delete_allowed", False)),
        "cleanup_runtime_performed": False,
    }


def _changed_payload_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = phase2.InMemoryCleanupDecisionLedger()
    request = phase2.build_cleanup_request()
    phase2.evaluate_cleanup_candidate(request, contract=contract, ledger=ledger)
    changed = copy.deepcopy(request)
    changed["owner_hold_status"] = "HELD"
    result = phase2.evaluate_cleanup_candidate(changed, contract=contract, ledger=ledger)
    count = len(getattr(ledger, "_records", {}))
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("reason_code") == "CLEANUP_REQUEST_CONFLICT"
        and count == 1
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "ledger_record_count": count,
        "delete_allowed": bool(result.get("delete_allowed", False)),
        "cleanup_runtime_performed": False,
    }


def _worker_exit_scenario(
    phase2: Any,
    phase2_contract: Mapping[str, Any],
    stage043_report: Mapping[str, Any],
) -> dict[str, Any]:
    upstream = stage043_report.get("scenario_results", {}).get(
        "isolated_worker_process_exit_checkpoint_candidate", {}
    )
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(
            artifact_class="INCOMPLETE_DERIVATIVE_OUTPUT",
            observed_job_state="FAILED",
        ),
        contract=phase2_contract,
    )
    passed = (
        upstream.get("status") == "PASS"
        and upstream.get("isolated_worker_process_exit_observed") is True
        and upstream.get("observed_exit_code") == 73
        and upstream.get("process_crash_recovery_performed") is False
        and upstream.get("worker_restart_performed") is False
        and result.get("decision_action") == "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "upstream_isolated_worker_exit_observed": (
            upstream.get("isolated_worker_process_exit_observed") is True
        ),
        "upstream_exit_code": upstream.get("observed_exit_code"),
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "process_crash_recovery_performed": False,
        "worker_restart_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
        "cleanup_runtime_performed": False,
    }


def _resource_scenario(
    phase2: Any,
    contract: Mapping[str, Any],
    signal: str,
) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(
            resource_gates_passed=False,
            resource_pressure_signal=signal,
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "CLEANUP_BLOCKED_RESOURCE"
        and result.get("reason_code") == "RESOURCE_GATE_BLOCKED"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pressure_signal": signal,
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "physical_drive_removal_performed": False,
        "disk_allocation_performed": False,
        "external_api_call_performed": False,
        "automatic_resume_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
        "cleanup_runtime_performed": False,
    }


def _active_writer_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(observed_job_state="RUNNING"),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
        and result.get("reason_code") == "JOB_ACTIVE_SUCCEEDED_OR_UNKNOWN"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "writer_probe_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
    }


def _unknown_writer_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(
            writer_quiescence_proved=False,
            producer_and_cleanup_leases_absent_or_fenced=False,
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
        and result.get("reason_code")
        == "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "writer_probe_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
    }


def _stale_identity_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(lstat_identity_stable=False),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
        and result.get("reason_code")
        == "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "filesystem_probe_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
    }


def _concurrent_same_file_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(
            exclusive_namespace_lock_proved=False,
            namespace_lock_exclusive=False,
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
        and result.get("reason_code")
        == "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN"
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "operation_invocation_count": 0,
        "production_lock_runtime_performed": False,
        "delete_allowed": bool(result.get("delete_allowed", False)),
    }


def _lock_exclusion_scenario(stage043_report: Mapping[str, Any]) -> dict[str, Any]:
    upstream = stage043_report.get("scenario_results", {}).get(
        "same_source_four_operation_lock_exclusion", {}
    )
    family_checks = upstream.get("family_checks", {})
    passed = (
        upstream.get("status") == "PASS"
        and upstream.get("required_operation_families") == LOCK_FAMILIES
        and set(family_checks) == set(LOCK_FAMILIES)
        and all(family_checks.values())
        and upstream.get("source_full_conflict_count") == 25
        and upstream.get("selected_matrix_conflict_count") == 16
        and upstream.get("operation_invocation_count") == 0
        and upstream.get("queue_record_created_count") == 0
        and upstream.get("retry_budget_consumed_count") == 0
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "required_operation_families": LOCK_FAMILIES,
        "family_checks": {name: family_checks.get(name) is True for name in LOCK_FAMILIES},
        "source_full_conflict_count": upstream.get("source_full_conflict_count"),
        "selected_matrix_conflict_count": upstream.get(
            "selected_matrix_conflict_count"
        ),
        "operation_invocation_count": upstream.get("operation_invocation_count"),
        "queue_record_created_count": upstream.get("queue_record_created_count"),
        "retry_budget_consumed_count": upstream.get("retry_budget_consumed_count"),
        "production_lock_runtime_performed": False,
    }


def _protected_scenario(
    phase2: Any,
    contract: Mapping[str, Any],
    classes: list[str],
) -> dict[str, Any]:
    artifact_results: dict[str, dict[str, Any]] = {}
    for artifact_class in classes:
        result = phase2.evaluate_cleanup_candidate(
            phase2.build_cleanup_request(artifact_class=artifact_class),
            contract=contract,
        )
        artifact_results[artifact_class] = {
            "artifact_class": artifact_class,
            "decision_action": result.get("decision_action"),
            "reason_code": result.get("reason_code"),
            "delete_allowed": bool(result.get("delete_allowed", False)),
            "delete_attempted": False,
        }
    passed = all(
        item["decision_action"] == "CLEANUP_BLOCKED_PROTECTED"
        and item["reason_code"] == "PROTECTED_HELD_NON_REBUILDABLE_OR_REFERENCED"
        and item["delete_allowed"] is False
        for item in artifact_results.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact_results": artifact_results,
        "delete_attempt_count": 0,
        "deleted_ref_count": 0,
        "cleanup_runtime_performed": False,
    }


def _eligible_candidate_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_cleanup_candidate(
        phase2.build_cleanup_request(), contract=contract
    )
    passed = (
        result.get("decision_action") == "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        and result.get("candidate_only") is True
        and _decision_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "candidate_only": result.get("candidate_only") is True,
        "candidate_ref": result.get("candidate_ref"),
        "delete_allowed": bool(result.get("delete_allowed", False)),
        "filesystem_traversal_performed": bool(
            result.get("filesystem_traversal_performed", False)
        ),
        "production_lock_acquired": bool(
            result.get("production_lock_acquired", False)
        ),
        "audit_write_performed": bool(result.get("audit_write_performed", False)),
        "cleanup_runtime_performed": False,
    }


def _run_scenarios(
    scenario_contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], bool, bool, bool, Mapping[str, Any]]:
    del scenario_contract
    phase2 = _phase2_module()
    stage043 = _stage043_module()
    phase2_contract = phase2._load_contract()
    phase2_report = phase2.build_stage044_phase2_report()
    stage043_report = stage043.build_stage043_phase3_report()
    phase2_valid = (
        phase2_report.get("result")
        == "PASS_ISOLATED_CLEANUP_CANDIDATE_DECISION_DELETE_DISABLED"
        and phase2_report.get("phase2_slice_valid") is True
    )
    stage043_valid = stage043_report.get("scenario_validation_valid") is True
    stage041_valid = stage043_report.get("stage041_lock_scenarios_valid") is True
    results = {
        "duplicate_cleanup_request_exact_replay": _duplicate_scenario(
            phase2, phase2_contract
        ),
        "changed_payload_same_request_rejected": _changed_payload_scenario(
            phase2, phase2_contract
        ),
        "isolated_worker_exit_partial_output_candidate_only": _worker_exit_scenario(
            phase2, phase2_contract, stage043_report
        ),
        "external_drive_offline_blocked": _resource_scenario(
            phase2, phase2_contract, "EXTERNAL_DRIVE_OFFLINE"
        ),
        "low_disk_blocked": _resource_scenario(
            phase2, phase2_contract, "DISK_SPACE_INSUFFICIENT"
        ),
        "api_budget_blocked": _resource_scenario(
            phase2, phase2_contract, "EXTERNAL_API_BUDGET_INSUFFICIENT"
        ),
        "active_writer_blocked": _active_writer_scenario(phase2, phase2_contract),
        "unknown_writer_or_quiescence_blocked": _unknown_writer_scenario(
            phase2, phase2_contract
        ),
        "stale_lstat_identity_blocked": _stale_identity_scenario(
            phase2, phase2_contract
        ),
        "concurrent_same_file_lock_conflict_blocked": _concurrent_same_file_scenario(
            phase2, phase2_contract
        ),
        "same_source_four_operation_lock_exclusion": _lock_exclusion_scenario(
            stage043_report
        ),
        "core_protected_artifacts_denied": _protected_scenario(
            phase2, phase2_contract, CORE_PROTECTED_CLASSES
        ),
        "all_protected_classes_denied": _protected_scenario(
            phase2, phase2_contract, PROTECTED_CLASSES
        ),
        "eligible_candidate_review_only_delete_disabled": _eligible_candidate_scenario(
            phase2, phase2_contract
        ),
    }
    return results, phase2_valid, stage041_valid, stage043_valid, stage043_report


def _blank_report(
    contract_checks: Mapping[str, bool], *, load_error: Optional[str]
) -> dict[str, Any]:
    report = {
        "schema_version": "ids.stage044.half_product_cleanup.phase3.report.v1",
        "stage": "STAGE-044",
        "phase": "Phase 3",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "policy_version": POLICY_VERSION,
        "contract_valid": False,
        "scenario_runtime_performed": False,
        "scenario_validation_valid": False,
        "contract_checks": dict(contract_checks),
        "scenario_count": 0,
        "passed_scenario_count": 0,
        "scenario_results": {},
        "phase2_slice_valid": False,
        "phase2_slice_reexecuted": False,
        "stage041_lock_scenarios_valid": False,
        "stage043_crash_scenarios_valid": False,
        "execution_mode": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "contract_state": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "load_error": load_error,
        "next_gate": "IDS-STAGE044-P3-GATE",
        "result": "BLOCKED_PHASE3_CONTRACT_OR_SCENARIO_CHECK_FAILED",
        "owner_feedback_zh": "半成品清理 Phase 3 场景合同无效；保持失败关闭。",
        "successful_cleanup_observed": False,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def build_stage044_phase3_report(
    contract: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    try:
        value = (
            copy.deepcopy(dict(contract))
            if isinstance(contract, Mapping)
            else load_scenario_contract()
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _blank_report(
            {"contract_loadable": False},
            load_error=f"{type(exc).__name__}: {exc}",
        )
    checks = validate_scenario_contract(value)
    contract_valid = bool(checks) and all(checks.values())
    if not contract_valid:
        return _blank_report(checks, load_error=None)
    try:
        (
            results,
            phase2_valid,
            stage041_valid,
            stage043_valid,
            stage043_report,
        ) = _run_scenarios(value)
    except Exception as exc:
        report = _blank_report(
            checks,
            load_error=f"{type(exc).__name__}: {exc}",
        )
        report["contract_valid"] = True
        report["scenario_runtime_performed"] = True
        report["execution_mode"] = value["execution_mode"]
        report["contract_state"] = value["contract_state"]
        return report

    passed = sum(item.get("status") == "PASS" for item in results.values())
    scenario_valid = (
        list(results) == SCENARIO_CATALOG
        and passed == len(SCENARIO_CATALOG)
        and phase2_valid
        and stage041_valid
        and stage043_valid
    )
    truth = value["truth_flags"]
    worker = results["isolated_worker_exit_partial_output_candidate_only"]
    report = {
        "schema_version": "ids.stage044.half_product_cleanup.phase3.report.v1",
        "stage": "STAGE-044",
        "phase": "Phase 3",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "policy_version": POLICY_VERSION,
        "contract_valid": contract_valid,
        "scenario_runtime_performed": True,
        "scenario_validation_valid": scenario_valid,
        "contract_checks": checks,
        "scenario_count": len(results),
        "passed_scenario_count": passed,
        "scenario_results": results,
        "phase2_slice_valid": phase2_valid,
        "phase2_slice_reexecuted": phase2_valid,
        "stage041_lock_scenarios_valid": stage041_valid,
        "stage043_crash_scenarios_valid": stage043_valid,
        "execution_mode": value["execution_mode"],
        "contract_state": value["contract_state"],
        "load_error": None,
        "next_gate": (
            "IDS-STAGE044-P4-GATE" if scenario_valid else "IDS-STAGE044-P3-GATE"
        ),
        "result": (
            "PASS_ISOLATED_CLEANUP_SCENARIOS_DELETE_DISABLED"
            if scenario_valid
            else "BLOCKED_PHASE3_CONTRACT_OR_SCENARIO_CHECK_FAILED"
        ),
        "owner_feedback_zh": (
            "半成品清理 Phase 3 的十四项隔离场景已通过；重复请求、进程丢失、"
            "资源压力、writer/身份/锁冲突和受保护资料均失败关闭，删除继续禁用。"
            if scenario_valid
            else "半成品清理 Phase 3 场景证据无效；保持失败关闭。"
        ),
        "successful_cleanup_observed": False,
    }
    derived_true = {
        "phase2_cleanup_decisions_reexecuted": phase2_valid,
        "stage041_lock_scenarios_replayed": stage041_valid,
        "stage043_crash_scenarios_replayed": stage043_valid,
        "isolated_control_process_started": (
            stage043_report.get("isolated_control_process_started") is True
        ),
        "isolated_worker_process_exit_observed": (
            worker.get("upstream_isolated_worker_exit_observed") is True
        ),
        "actual_project_disk_observation_performed": (
            stage043_report.get("actual_project_disk_observation_performed") is True
        ),
    }
    report.update(
        {
            name: bool(derived_true.get(name, truth.get(name, False)))
            for name in TRUE_TRUTH_FLAGS
        }
    )
    report.update({name: bool(truth.get(name, False)) for name in FALSE_TRUTH_FLAGS})
    return report


def main() -> int:
    report = build_stage044_phase3_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["scenario_validation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
