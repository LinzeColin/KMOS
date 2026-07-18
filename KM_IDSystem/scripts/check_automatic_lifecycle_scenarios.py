#!/usr/bin/env python3
"""Fail-closed Stage042 Phase 3 automatic-lifecycle scenario checker."""

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
BASE = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT_PATH = (
    BASE
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_scenarios.json"
)
PHASE2_CHECKER = PROJECT_ROOT / "scripts" / "check_automatic_lifecycle_runtime.py"
STAGE041_CHECKER = PROJECT_ROOT / "scripts" / "check_lock_registry_scenarios.py"

TASK_ID = "IDS-V0_1-STAGE042-P3"
ACCEPTANCE_ID = "ACC-STAGE-042"
POLICY_VERSION = "ids.automatic_lifecycle_policy.v0_1.stage042.p2"
PHASE2_COMMIT = "32bd7d9775229e03cd9855edc4e5b737860b6af7"
PHASE2_KMIDS_TREE = "6ddb0c27a95afa1662a892e6bb3b5d890f72f963"

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
    "stage042_phase2_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_runtime_contract.json",
        "27da5276a1f51a6fdf5bcfefd60559d02fa309f509fb5315999536e05b78aa04",
    ),
    "stage042_phase2_checker": (
        "KM_IDSystem/scripts/check_automatic_lifecycle_runtime.py",
        "70270f82dc94d3913ef455d494126c3a91fe2e09407f946e5c829db29f9c6c58",
    ),
    "stage042_phase2_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage042_automatic_lifecycle_runtime.py",
        "acd9e5c1927b44483f97e46666f58bb8580ab1d9bb993b15bfbf62dda281d5b5",
    ),
    "stage042_phase2_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md",
        "9461cfa35935c761966b3641ebc11f594b8b02e92f8ebcbbdc249627727a0cb5",
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
    "stage041_phase3_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage041_lock_registry_scenarios.py",
        "4fb9ac7418fd81873e5980d4da684894ba7966378a2993ce7d4422d9f1075eac",
    ),
}
SCENARIO_CATALOG = [
    "duplicate_request_exact_replay",
    "changed_payload_same_request_rejected",
    "stale_start_observation_blocked",
    "external_drive_pause_then_guarded_resume",
    "low_disk_pause_then_guarded_resume",
    "api_budget_pause_then_guarded_resume",
    "worker_exception_crash_recovery_deferred",
    "same_source_four_operation_lock_exclusion",
    "safe_shutdown_ordered_candidate",
    "shutdown_timeout_blocked",
    "protected_cleanup_denied",
    "eligible_cleanup_candidate_only",
]
EXPECTED_EXPECTATIONS = {
    "duplicate_request_exact_replay": (
        "EXACT_REPLAY_ONE_LEDGER_RECORD_NO_STATE_MUTATION"
    ),
    "changed_payload_same_request_rejected": (
        "SAME_REQUEST_ID_CHANGED_PAYLOAD_CONFLICT_NO_MUTATION"
    ),
    "stale_start_observation_blocked": (
        "STALE_RESOURCE_OBSERVATION_REQUIRES_MANUAL_REVIEW"
    ),
    "external_drive_pause_then_guarded_resume": (
        "PAUSE_THEN_OWNER_AND_STABILITY_REVALIDATION_TO_QUEUED_ONLY"
    ),
    "low_disk_pause_then_guarded_resume": (
        "ACTUAL_PROJECT_OBSERVATION_CONTROLLED_LOW_BOUNDARY_NO_ALLOCATION"
    ),
    "api_budget_pause_then_guarded_resume": (
        "CONTROLLED_API_BUDGET_PAUSE_NO_EXTERNAL_CALL"
    ),
    "worker_exception_crash_recovery_deferred": (
        "ACTUAL_ISOLATED_EXCEPTION_LOCK_RETAINED_STAGE043_OWNS_CRASH_RECOVERY"
    ),
    "same_source_four_operation_lock_exclusion": (
        "PROCESS_EXTRACT_INDEX_REPORT_SHARE_SOURCE_PIPELINE_EXCLUSION"
    ),
    "safe_shutdown_ordered_candidate": "ORDERED_CANDIDATE_NO_PROCESS_TERMINATION",
    "shutdown_timeout_blocked": "TIMEOUT_REQUIRES_MANUAL_REVIEW_NO_TERMINATION",
    "protected_cleanup_denied": "FIVE_GIT_TRACKED_PROTECTED_REFS_NEVER_DELETE",
    "eligible_cleanup_candidate_only": (
        "TWO_ELIGIBLE_CLASSES_REMAIN_CANDIDATE_ONLY"
    ),
}
EXPECTED_LIFECYCLE = {
    "candidate_decisions_only": True,
    "actual_state_mutation_allowed": False,
    "terminal_history_reopen_allowed": False,
    "direct_queued_to_running_allowed": False,
    "direct_running_to_paused_allowed": False,
    "direct_paused_to_running_allowed": False,
    "retry_budget_consumed_by_pause_or_resume": False,
    "idempotency_conflict_mutation_allowed": False,
}
EXPECTED_RESOURCE_RECOVERY = {
    "pause_signals": [
        "EXTERNAL_DRIVE_OFFLINE",
        "DISK_SPACE_INSUFFICIENT",
        "EXTERNAL_API_BUDGET_INSUFFICIENT",
    ],
    "active_pause_must_use_pause_requested": True,
    "resume_target": "QUEUED",
    "owner_revalidation_required": True,
    "resource_stability_required": True,
    "no_active_claim_or_lock_required": True,
    "fresh_admission_claim_lock_cycle_required": True,
    "actual_project_disk_observation_allowed": True,
    "physical_drive_removal_allowed": False,
    "disk_allocation_allowed": False,
    "external_api_call_allowed": False,
}
SELECTED_LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
EXPECTED_OPERATION_EXCLUSION = {
    "source_scenario_contract_id": (
        "ids.lock_registry_policy.v0_1.stage041.p3.scenarios"
    ),
    "required_operation_families": SELECTED_LOCK_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "same_source_reference_required": True,
    "source_full_matrix_conflict_count": 25,
    "selected_matrix_conflict_count": 16,
    "operation_invocation_count": 0,
    "queue_record_created": False,
    "retry_budget_consumed": False,
    "partial_lock_retained": False,
}
EXPECTED_WORKER_BOUNDARY = {
    "source_scenario_contract_id": (
        "ids.lock_registry_policy.v0_1.stage041.p3.scenarios"
    ),
    "actual_isolated_exception_allowed": True,
    "process_crash_claim_allowed": False,
    "lock_retained_after_isolated_exception_expected": True,
    "automatic_resume_after_exception_allowed": False,
    "process_termination_allowed": False,
    "crash_recovery_runtime_owner": "STAGE-043",
}
EXPECTED_SHUTDOWN = {
    "ordered_candidate_required": True,
    "checkpoint_or_quarantine_required_for_active": True,
    "matching_lock_evidence_required_for_active": True,
    "graceful_shutdown_timeout_seconds": 60,
    "timeout_action": "REQUIRE_MANUAL_REVIEW",
    "process_termination_allowed": False,
    "actual_shutdown_allowed": False,
}
EXPECTED_PROTECTED_REFS = {
    "FACT_SOURCE": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md"
    ),
    "MANIFEST": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE026_PHASE2_ARCHIVE_MANIFEST_SLICE.md"
    ),
    "EVIDENCE_LEDGER": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_runtime_contract.json"
    ),
    "REPORT_SNAPSHOT": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md"
    ),
    "AUDIT_LOG": "repo:KM_IDSystem/docs/governance/events.jsonl",
}
ELIGIBLE_CLEANUP_CLASSES = [
    "TEMP_STAGING_OUTPUT",
    "INCOMPLETE_DERIVATIVE_OUTPUT",
]
EXPECTED_DOWNSTREAM = {
    "queue_and_worker_transport": "STAGE-038",
    "retry_and_dead_letter_policy": "STAGE-039",
    "backpressure_observation_and_policy": "STAGE-040",
    "lock_lease_and_fencing_runtime": "STAGE-041",
    "automatic_lifecycle_scenario_policy": "STAGE-042",
    "process_crash_recovery_runtime": "STAGE-043",
    "cleanup_execution_runtime": "STAGE-044",
    "phase3_may_take_stage043_or_stage044_runtime": False,
}
EXPECTED_HUMAN_STATUS = {
    "AUTO_PAUSE_CANDIDATE": "等待安全暂停",
    "AUTO_RESUME_CANDIDATE": "可进入恢复队列",
    "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION": "等待复核后恢复",
    "SAFE_SHUTDOWN_CANDIDATE": "安全关闭中",
    "PROTECTED_ARTIFACT": "受保护资料不可清理",
    "REQUIRE_MANUAL_REVIEW": "需要人工处理",
}
EXPECTED_PHASE4_GATE = {
    "entry_authorized_after_scenario_pass": True,
    "required_task_id": "IDS-V0_1-STAGE042-P4",
    "required_acceptance_id": ACCEPTANCE_ID,
    "must_run_separately": True,
    "whole_stage_review_allowed_in_phase3": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
    "next_gate": "IDS-STAGE042-P4-GATE",
}
TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_lifecycle_decisions_reexecuted",
    "isolated_lifecycle_scenarios_performed",
    "duplicate_and_stale_scenarios_performed",
    "resource_pause_resume_scenarios_performed",
    "stage041_lock_scenarios_replayed",
    "actual_isolated_worker_exception_performed",
    "actual_project_disk_observation_performed",
    "protected_refs_verified",
    "lifecycle_candidate_evaluation_performed",
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase2_module() -> Any:
    return _load_module(PHASE2_CHECKER, "stage042_phase2_for_phase3")


def _stage041_module() -> Any:
    return _load_module(STAGE041_CHECKER, "stage041_scenarios_for_stage042")


def load_scenario_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Stage042 Phase3 scenario contract must be an object")
    return value


def _keys_exact(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _source_valid(value: Any) -> bool:
    if value != EXPECTED_SOURCE:
        return False
    try:
        archive = Path(value["source_archive_path"])
        if sha256_file(archive) != value["source_archive_sha256"]:
            return False
        if sha256_file(Path(value["roadmap_path"])) != value["roadmap_sha256"]:
            return False
        if (
            sha256_file(Path(value["instructions_path"]))
            != value["instructions_sha256"]
        ):
            return False
        with ZipFile(archive) as bundle:
            matches = [
                name for name in bundle.namelist() if name == value["source_member"]
            ]
            return (
                len(matches) == value["source_member_match_count"] == 1
                and hashlib.sha256(bundle.read(matches[0])).hexdigest()
                == value["source_member_sha256"]
            )
    except (OSError, KeyError, TypeError):
        return False


def _upstream_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != set(EXPECTED_UPSTREAM):
        return False
    for name, (relative, digest) in EXPECTED_UPSTREAM.items():
        if value.get(name) != {"ref": relative, "sha256": digest}:
            return False
        path = REPO_ROOT / relative
        if not path.is_file() or sha256_file(path) != digest:
            return False
    return True


def _phase2_commit_current(value: Any) -> bool:
    expected = {
        "commit": PHASE2_COMMIT,
        "km_ids_tree": PHASE2_KMIDS_TREE,
        "required_ancestor_of_head": True,
    }
    if value != expected:
        return False
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE2_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    tree = subprocess.run(
        ["git", "rev-parse", f"{PHASE2_COMMIT}:KM_IDSystem"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return (
        ancestor.returncode == 0
        and tree.returncode == 0
        and tree.stdout.strip() == PHASE2_KMIDS_TREE
    )


def _git_tracked_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("repo:KM_IDSystem/"):
        return False
    relative = value.removeprefix("repo:").split("#", 1)[0]
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "ids_metadata" in relative.lower():
        return False
    if not (REPO_ROOT / relative).is_file():
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, dict):
        return {"contract_is_object": False}
    expected_root = {
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
        "lifecycle_safety_contract",
        "resource_recovery_contract",
        "operation_exclusion_contract",
        "worker_crash_boundary_contract",
        "shutdown_contract",
        "protected_artifact_contract",
        "downstream_ownership",
        "human_status_contract",
        "phase4_entry_gate",
        "truth_flags",
    }
    protected = contract.get("protected_artifact_contract")
    protected_refs = protected.get("protected_refs") if isinstance(protected, dict) else None
    truth = contract.get("truth_flags")
    return {
        "root_schema_exact": _keys_exact(contract, expected_root),
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage042.automatic_lifecycle.phase3.scenarios.v1"
            and contract.get("stage") == "STAGE-042"
            and contract.get("phase") == "Phase 3"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_AUTOMATIC_LIFECYCLE_SCENARIOS"
            and contract.get("scenario_contract_id")
            == "ids.automatic_lifecycle_policy.v0_1.stage042.p3.scenarios"
            and contract.get("contract_state")
            == "PHASE3_SCENARIOS_ENABLED_PRODUCTION_DISABLED"
            and contract.get("next_gate") == "IDS-STAGE042-P4-GATE"
        ),
        "source_binding_exact": _source_valid(contract.get("source_binding")),
        "phase2_commit_binding_current": _phase2_commit_current(
            contract.get("phase2_commit_binding")
        ),
        "upstream_bindings_current": _upstream_valid(
            contract.get("upstream_bindings")
        ),
        "policy_version_exact": contract.get("policy_version") == POLICY_VERSION,
        "scenario_catalog_exact": contract.get("scenario_catalog")
        == SCENARIO_CATALOG,
        "scenario_expectations_exact": contract.get("scenario_expectations")
        == EXPECTED_EXPECTATIONS,
        "lifecycle_safety_exact": contract.get("lifecycle_safety_contract")
        == EXPECTED_LIFECYCLE,
        "resource_recovery_exact": contract.get("resource_recovery_contract")
        == EXPECTED_RESOURCE_RECOVERY,
        "operation_exclusion_exact": contract.get("operation_exclusion_contract")
        == EXPECTED_OPERATION_EXCLUSION,
        "worker_crash_boundary_exact": contract.get("worker_crash_boundary_contract")
        == EXPECTED_WORKER_BOUNDARY,
        "shutdown_exact": contract.get("shutdown_contract") == EXPECTED_SHUTDOWN,
        "protected_artifact_exact": protected
        == {
            "protected_refs": EXPECTED_PROTECTED_REFS,
            "eligible_candidate_classes": ELIGIBLE_CLEANUP_CLASSES,
            "all_refs_must_be_git_tracked": True,
            "delete_attempt_allowed": False,
            "delete_api_call_allowed": False,
            "cleanup_runtime_owner": "STAGE-044",
        },
        "protected_refs_real_and_tracked": (
            protected_refs == EXPECTED_PROTECTED_REFS
            and all(_git_tracked_repo_ref(ref) for ref in protected_refs.values())
        ),
        "downstream_ownership_exact": contract.get("downstream_ownership")
        == EXPECTED_DOWNSTREAM,
        "human_status_exact": contract.get("human_status_contract")
        == EXPECTED_HUMAN_STATUS,
        "phase4_gate_exact": contract.get("phase4_entry_gate")
        == EXPECTED_PHASE4_GATE,
        "truth_flags_exact": (
            _keys_exact(truth, TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS)
            and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }


def _duplicate_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    ledger = phase2.IsolatedLifecycleDecisionLedger()
    request = phase2.build_control_request("AUTO_START")
    first = phase2.evaluate_lifecycle(request, contract=contract, ledger=ledger)
    replay = phase2.evaluate_lifecycle(request, contract=contract, ledger=ledger)
    passed = (
        first == replay
        and first.get("decision_action") == "AUTO_START_CANDIDATE"
        and ledger.record_count == 1
        and first.get("state_mutation_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "first_decision_action": first.get("decision_action"),
        "replay_equal": first == replay,
        "ledger_record_count": ledger.record_count,
        "state_mutation_performed": bool(first.get("state_mutation_performed")),
    }


def _changed_payload_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = phase2.IsolatedLifecycleDecisionLedger()
    request = phase2.build_control_request("AUTO_START")
    first = phase2.evaluate_lifecycle(request, contract=contract, ledger=ledger)
    changed = copy.deepcopy(request)
    changed["evidence"]["resource_stable_for_seconds"] += 1
    rejected = phase2.evaluate_lifecycle(changed, contract=contract, ledger=ledger)
    passed = (
        first.get("decision_action") == "AUTO_START_CANDIDATE"
        and rejected.get("decision_action")
        == "REJECT_LIFECYCLE_REQUEST_CONFLICT"
        and rejected.get("error_ref") == "error:LIFECYCLE_REQUEST_CONFLICT"
        and ledger.record_count == 1
        and rejected.get("state_mutation_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "changed_decision_action": rejected.get("decision_action"),
        "error_ref": rejected.get("error_ref"),
        "ledger_record_count": ledger.record_count,
        "state_mutation_performed": bool(rejected.get("state_mutation_performed")),
    }


def _stale_start_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    request = phase2.build_control_request(
        "AUTO_START",
        observed_at_epoch_seconds=900,
        evaluated_at_epoch_seconds=1000,
    )
    result = phase2.evaluate_lifecycle(request, contract=contract)
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("error_ref") == "error:START_GUARD_INCOMPLETE"
        and result.get("transition_candidates") == []
        and result.get("state_mutation_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "error_ref": result.get("error_ref"),
        "transition_candidates": result.get("transition_candidates"),
        "state_mutation_performed": bool(result.get("state_mutation_performed")),
    }


def _resource_pause_resume_scenario(
    phase2: Any,
    contract: Mapping[str, Any],
    signal: str,
    *,
    actual_disk_free_bytes: Optional[int] = None,
) -> dict[str, Any]:
    pause_request = phase2.build_control_request("AUTO_PAUSE", pressure_signal=signal)
    pause = phase2.evaluate_lifecycle(pause_request, contract=contract)
    owner_blocked = phase2.evaluate_lifecycle(
        phase2.build_control_request("AUTO_RESUME", owner_revalidated=False),
        contract=contract,
    )
    stability_blocked = phase2.evaluate_lifecycle(
        phase2.build_control_request("AUTO_RESUME", resource_stable_for_seconds=59),
        contract=contract,
    )
    resume = phase2.evaluate_lifecycle(
        phase2.build_control_request("AUTO_RESUME"), contract=contract
    )
    passed = (
        pause.get("decision_action") == "AUTO_PAUSE_CANDIDATE"
        and pause.get("transition_candidates")
        == [["RUNNING", "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "PAUSED"]]
        and owner_blocked.get("decision_action")
        == "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION"
        and stability_blocked.get("decision_action")
        == "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION"
        and resume.get("decision_action") == "AUTO_RESUME_CANDIDATE"
        and resume.get("transition_candidates") == [["PAUSED", "QUEUED"]]
        and resume.get("fresh_admission_and_lock_cycle_required") is True
        and all(
            result.get("state_mutation_performed") is False
            for result in (pause, owner_blocked, stability_blocked, resume)
        )
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pressure_signal": signal,
        "pause_decision_action": pause.get("decision_action"),
        "pause_transitions": pause.get("transition_candidates"),
        "owner_blocked_decision_action": owner_blocked.get("decision_action"),
        "stability_blocked_decision_action": stability_blocked.get("decision_action"),
        "resume_decision_action": resume.get("decision_action"),
        "resume_transitions": resume.get("transition_candidates"),
        "fresh_admission_and_lock_cycle_required": bool(
            resume.get("fresh_admission_and_lock_cycle_required")
        ),
        "actual_disk_free_bytes": actual_disk_free_bytes,
        "physical_drive_removal_performed": False,
        "disk_allocation_performed": False,
        "external_api_call_performed": False,
        "state_mutation_performed": False,
    }


def _worker_boundary_scenario(
    phase2: Any,
    phase2_contract: Mapping[str, Any],
    stage041_report: Mapping[str, Any],
) -> dict[str, Any]:
    source = stage041_report.get("scenario_results", {}).get(
        "isolated_worker_exception_lock_retained", {}
    )
    resume = phase2.evaluate_lifecycle(
        phase2.build_control_request(
            "AUTO_RESUME",
            owner_revalidated=False,
            active_claim_or_lock=True,
        ),
        contract=phase2_contract,
    )
    passed = (
        source.get("status") == "PASS"
        and source.get("actual_isolated_worker_exception_performed") is True
        and source.get("safe_error_ref") == "error:RuntimeError"
        and source.get("lock_retained_after_exception") is True
        and source.get("crash_recovery_owner") == "STAGE-043"
        and resume.get("decision_action")
        == "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION"
        and resume.get("process_termination_performed") is False
        and source.get("crash_recovery_runtime_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "actual_isolated_worker_exception_performed": bool(
            source.get("actual_isolated_worker_exception_performed")
        ),
        "safe_error_ref": source.get("safe_error_ref"),
        "lock_retained_after_exception": bool(
            source.get("lock_retained_after_exception")
        ),
        "crash_recovery_owner": source.get("crash_recovery_owner"),
        "resume_decision_action": resume.get("decision_action"),
        "process_termination_performed": False,
        "crash_recovery_runtime_performed": False,
    }


def _lock_exclusion_scenario(stage041_report: Mapping[str, Any]) -> dict[str, Any]:
    source = stage041_report.get("scenario_results", {}).get(
        "same_source_operation_exclusion_matrix", {}
    )
    source_checks = source.get("family_checks", {})
    selected_checks = {
        name: source_checks.get(name) is True for name in SELECTED_LOCK_FAMILIES
    }
    passed = (
        source.get("status") == "PASS"
        and all(selected_checks.values())
        and source.get("resource_conflict_count") == 25
        and source.get("operation_invocation_count") == 0
        and source.get("retry_budget_consumed_count") == 0
        and source.get("partial_lock_retained_count") == 0
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "required_operation_families": SELECTED_LOCK_FAMILIES,
        "family_checks": selected_checks,
        "source_full_conflict_count": source.get("resource_conflict_count"),
        "selected_matrix_conflict_count": len(SELECTED_LOCK_FAMILIES) ** 2,
        "operation_invocation_count": source.get("operation_invocation_count"),
        "retry_budget_consumed_count": source.get("retry_budget_consumed_count"),
        "partial_lock_retained_count": source.get("partial_lock_retained_count"),
    }


def _shutdown_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = phase2.evaluate_lifecycle(
        phase2.build_control_request("SAFE_SHUTDOWN"), contract=contract
    )
    passed = (
        result.get("decision_action") == "SAFE_SHUTDOWN_CANDIDATE"
        and result.get("ordered_shutdown_steps") == phase2.ORDERED_SHUTDOWN_STEPS
        and result.get("process_termination_performed") is False
        and result.get("state_mutation_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "ordered_shutdown_steps": result.get("ordered_shutdown_steps"),
        "process_termination_performed": False,
        "state_mutation_performed": False,
    }


def _shutdown_timeout_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_lifecycle(
        phase2.build_control_request("SAFE_SHUTDOWN", shutdown_elapsed_seconds=61),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("error_ref") == "error:SHUTDOWN_GUARD_OR_TIMEOUT"
        and result.get("ordered_shutdown_steps") == []
        and result.get("process_termination_performed") is False
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "error_ref": result.get("error_ref"),
        "ordered_shutdown_steps": result.get("ordered_shutdown_steps"),
        "process_termination_performed": False,
    }


def _protected_cleanup_scenario(
    phase2: Any,
    phase2_contract: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    refs = contract["protected_artifact_contract"]["protected_refs"]
    results: dict[str, dict[str, Any]] = {}
    for artifact_class, artifact_ref in refs.items():
        decision = phase2.evaluate_lifecycle(
            phase2.build_control_request(
                "CLEANUP_CANDIDATE_SCAN",
                cleanup_candidate_class=artifact_class,
            ),
            contract=phase2_contract,
        )
        results[artifact_class] = {
            "artifact_ref": artifact_ref,
            "git_tracked": _git_tracked_repo_ref(artifact_ref),
            "decision_action": decision.get("decision_action"),
            "error_ref": decision.get("error_ref"),
            "delete_allowed": False,
            "delete_attempted": False,
        }
    passed = all(
        item["git_tracked"]
        and item["decision_action"] == "REQUIRE_MANUAL_REVIEW"
        and item["error_ref"] == "error:CLEANUP_CANDIDATE_NOT_ELIGIBLE"
        and item["delete_allowed"] is False
        and item["delete_attempted"] is False
        for item in results.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact_results": results,
        "cleanup_runtime_performed": False,
        "protected_ref_delete_performed": False,
    }


def _eligible_cleanup_scenario(
    phase2: Any, phase2_contract: Mapping[str, Any]
) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for artifact_class in ELIGIBLE_CLEANUP_CLASSES:
        decision = phase2.evaluate_lifecycle(
            phase2.build_control_request(
                "CLEANUP_CANDIDATE_SCAN",
                cleanup_candidate_class=artifact_class,
            ),
            contract=phase2_contract,
        )
        results[artifact_class] = {
            "decision_action": decision.get("decision_action"),
            "cleanup_candidate_only": bool(decision.get("cleanup_candidate_only")),
            "delete_allowed": False,
        }
    passed = all(
        item["decision_action"] == "CLEANUP_CANDIDATE_ONLY"
        and item["cleanup_candidate_only"] is True
        and item["delete_allowed"] is False
        for item in results.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact_results": results,
        "cleanup_runtime_performed": False,
        "protected_ref_delete_performed": False,
    }


def _run_scenarios(
    scenario_contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], bool, bool]:
    phase2 = _phase2_module()
    stage041 = _stage041_module()
    phase2_contract = phase2.load_contract()
    phase2_valid = phase2.build_stage042_phase2_report().get("phase2_slice_valid") is True
    stage041_report = stage041.build_stage041_phase3_report()
    stage041_valid = stage041_report.get("scenario_validation_valid") is True
    disk_source = stage041_report.get("scenario_results", {}).get(
        "low_disk_pause_boundary", {}
    )
    results = {
        "duplicate_request_exact_replay": _duplicate_scenario(
            phase2, phase2_contract
        ),
        "changed_payload_same_request_rejected": _changed_payload_scenario(
            phase2, phase2_contract
        ),
        "stale_start_observation_blocked": _stale_start_scenario(
            phase2, phase2_contract
        ),
        "external_drive_pause_then_guarded_resume": _resource_pause_resume_scenario(
            phase2, phase2_contract, "EXTERNAL_DRIVE_OFFLINE"
        ),
        "low_disk_pause_then_guarded_resume": _resource_pause_resume_scenario(
            phase2,
            phase2_contract,
            "DISK_SPACE_INSUFFICIENT",
            actual_disk_free_bytes=disk_source.get("actual_disk_free_bytes"),
        ),
        "api_budget_pause_then_guarded_resume": _resource_pause_resume_scenario(
            phase2, phase2_contract, "EXTERNAL_API_BUDGET_INSUFFICIENT"
        ),
        "worker_exception_crash_recovery_deferred": _worker_boundary_scenario(
            phase2, phase2_contract, stage041_report
        ),
        "same_source_four_operation_lock_exclusion": _lock_exclusion_scenario(
            stage041_report
        ),
        "safe_shutdown_ordered_candidate": _shutdown_scenario(
            phase2, phase2_contract
        ),
        "shutdown_timeout_blocked": _shutdown_timeout_scenario(
            phase2, phase2_contract
        ),
        "protected_cleanup_denied": _protected_cleanup_scenario(
            phase2, phase2_contract, scenario_contract
        ),
        "eligible_cleanup_candidate_only": _eligible_cleanup_scenario(
            phase2, phase2_contract
        ),
    }
    return results, phase2_valid, stage041_valid


def _blank_report(
    contract_checks: Mapping[str, bool], *, load_error: Optional[str]
) -> dict[str, Any]:
    return {
        "schema_version": "ids.stage042.automatic_lifecycle.phase3.report.v1",
        "stage": "STAGE-042",
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
        "stage041_lock_scenarios_valid": False,
        "execution_mode": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "contract_state": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "load_error": load_error,
        "next_gate": "IDS-STAGE042-P3-GATE",
        "owner_feedback_zh": "自动生命周期 Phase 3 场景合同无效；保持失败关闭。",
        **{name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS},
    }


def build_stage042_phase3_report(
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
        results, phase2_valid, stage041_valid = _run_scenarios(value)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
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
    )
    truth = value["truth_flags"]
    worker = results["worker_exception_crash_recovery_deferred"]
    disk = results["low_disk_pause_then_guarded_resume"]
    return {
        "schema_version": "ids.stage042.automatic_lifecycle.phase3.report.v1",
        "stage": "STAGE-042",
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
        "stage041_lock_scenarios_valid": stage041_valid,
        "execution_mode": value["execution_mode"],
        "contract_state": value["contract_state"],
        "load_error": None,
        "next_gate": (
            "IDS-STAGE042-P4-GATE"
            if scenario_valid
            else "IDS-STAGE042-P3-GATE"
        ),
        "owner_feedback_zh": (
            "自动生命周期 Phase 3 的十二项隔离场景已通过；重复请求、"
            "资源暂停恢复、异常归属、同源排他、关闭与清理均失败关闭，"
            "生产运行继续禁用。"
            if scenario_valid
            else "自动生命周期 Phase 3 场景证据无效；保持失败关闭。"
        ),
        "actual_isolated_worker_exception_performed": (
            worker.get("actual_isolated_worker_exception_performed") is True
            and truth["actual_isolated_worker_exception_performed"] is True
        ),
        "actual_project_disk_observation_performed": (
            isinstance(disk.get("actual_disk_free_bytes"), int)
            and disk.get("actual_disk_free_bytes", 0) > 0
            and truth["actual_project_disk_observation_performed"] is True
        ),
        **{
            name: bool(truth.get(name, False))
            for name in TRUE_TRUTH_FLAGS
            if name
            not in {
                "actual_isolated_worker_exception_performed",
                "actual_project_disk_observation_performed",
            }
        },
        **{name: bool(truth.get(name, False)) for name in FALSE_TRUTH_FLAGS},
    }


def main() -> int:
    report = build_stage042_phase3_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["scenario_validation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
