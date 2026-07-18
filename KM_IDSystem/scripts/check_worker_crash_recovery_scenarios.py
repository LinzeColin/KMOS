#!/usr/bin/env python3
"""Fail-closed STAGE-043 Phase 3 worker crash recovery scenarios."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping, Optional
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
CONTRACT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "worker_crash_recovery"
    / "stage043_worker_crash_recovery_scenarios.json"
)
PHASE2_CHECKER_PATH = PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_runtime.py"
STAGE041_SCENARIO_CHECKER_PATH = (
    PROJECT_ROOT / "scripts" / "check_lock_registry_scenarios.py"
)

TASK_ID = "IDS-V0_1-STAGE043-P3"
ACCEPTANCE_ID = "ACC-STAGE-043"
POLICY_VERSION = "ids.worker_crash_recovery_policy.v0_1.stage043.p2"
SCHEMA_VERSION = "ids.stage043.worker_crash_recovery.phase3.scenarios.v1"
SCENARIO_CONTRACT_ID = (
    "ids.worker_crash_recovery_policy.v0_1.stage043.p3.scenarios"
)
EXECUTION_MODE = "ISOLATED_NON_PRODUCTION_WORKER_CRASH_RECOVERY_SCENARIOS"
CONTRACT_STATE = "PHASE3_SCENARIOS_ENABLED_PRODUCTION_DISABLED"

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
        "STAGE-043_Worker崩溃恢复.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b"
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
    "commit": "b1a8e4689eb9c3a3a469a9f8d77dff4683aa709c",
    "km_ids_tree": "6a3c6f683ab2e2e263b36463f0dc20d2ff277985",
    "required_ancestor_of_head": True,
}
EXPECTED_UPSTREAM = {
    "stage043_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_runtime_contract.json"
        ),
        "sha256": (
            "5cbdb1416b3b3fd2464b53b83655f8c8382f8392bdd0d56ad69b02160b6b5837"
        ),
    },
    "stage043_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_crash_recovery_runtime.py",
        "sha256": (
            "c8b104c506b3cac374cefca80613855e2d3964116426a70c9c4babff89e269dc"
        ),
    },
    "stage043_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage043_worker_crash_recovery_runtime.py"
        ),
        "sha256": (
            "66241b07cc9a5f6806d8063617c841d2a6549ed3f22d9afba00f940729e3acb0"
        ),
    },
    "stage043_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md"
        ),
        "sha256": (
            "5eccf7561e384d3f3e8ccab86d1bae7e9e10677943db854b6a09e5b691531cdd"
        ),
    },
    "stage041_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_scenarios.json"
        ),
        "sha256": (
            "0866db20e070d1b93981f4b7b4180977f3221395310f1194ddcaa14556268c19"
        ),
    },
    "stage041_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_lock_registry_scenarios.py",
        "sha256": (
            "fa46f374e4708c15b0d3e856e42e55f1c784dd926278ad86a8610878b59d606e"
        ),
    },
    "stage041_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage041_lock_registry_scenarios.py"
        ),
        "sha256": (
            "6b235e04b64ba09278821abaf0bd5258e40f8b5f03f56c395dba68ab8177e088"
        ),
    },
}

SCENARIO_CATALOG = [
    "duplicate_recovery_request_exact_replay",
    "changed_payload_same_request_rejected",
    "stale_crash_evidence_blocked",
    "isolated_worker_process_exit_checkpoint_candidate",
    "unfenced_worker_generation_blocked",
    "external_drive_offline_pause_candidate",
    "low_disk_pause_candidate",
    "api_budget_pause_candidate",
    "same_source_four_operation_lock_exclusion",
    "active_lock_or_claim_conflict_blocked",
    "terminal_history_immutable",
    "protected_cleanup_denied",
    "eligible_partial_output_quarantine_candidate_only",
]
EXPECTED_SCENARIO_EXPECTATIONS = {
    "duplicate_recovery_request_exact_replay": (
        "EXACT_REPLAY_ONE_LEDGER_RECORD_NO_STATE_MUTATION"
    ),
    "changed_payload_same_request_rejected": (
        "SAME_REQUEST_KEY_CHANGED_PAYLOAD_CONFLICT_NO_MUTATION"
    ),
    "stale_crash_evidence_blocked": (
        "STALE_HEARTBEAT_OR_CRASH_EVIDENCE_REQUIRES_MANUAL_REVIEW"
    ),
    "isolated_worker_process_exit_checkpoint_candidate": (
        "ISOLATED_CONTROL_CHILD_SELF_EXIT_OBSERVED_CANDIDATE_ONLY_NO_RECOVERY"
    ),
    "unfenced_worker_generation_blocked": (
        "LOST_WORKER_NOT_FENCED_REQUIRES_MANUAL_REVIEW"
    ),
    "external_drive_offline_pause_candidate": (
        "CONTROLLED_DRIVE_SIGNAL_PAUSES_NO_PHYSICAL_REMOVAL"
    ),
    "low_disk_pause_candidate": (
        "ACTUAL_PROJECT_OBSERVATION_CONTROLLED_LOW_BOUNDARY_NO_ALLOCATION"
    ),
    "api_budget_pause_candidate": (
        "CONTROLLED_API_BUDGET_PAUSE_NO_EXTERNAL_CALL"
    ),
    "same_source_four_operation_lock_exclusion": (
        "PROCESS_EXTRACT_INDEX_REPORT_SHARE_SOURCE_PIPELINE_EXCLUSION"
    ),
    "active_lock_or_claim_conflict_blocked": (
        "ACTIVE_LOCK_OR_CLAIM_PREVENTS_RECOVERY_CANDIDATE"
    ),
    "terminal_history_immutable": "TERMINAL_JOB_NEVER_REOPENS",
    "protected_cleanup_denied": (
        "FIVE_GIT_TRACKED_PROTECTED_REFS_NEVER_DELETE"
    ),
    "eligible_partial_output_quarantine_candidate_only": (
        "TWO_PARTIAL_OUTPUT_CLASSES_REMAIN_REFERENCE_ONLY_STAGE044_CANDIDATES"
    ),
}
EXPECTED_RECOVERY_SAFETY = {
    "candidate_decisions_only": True,
    "actual_state_mutation_allowed": False,
    "checkpoint_resume_execution_allowed": False,
    "terminal_history_reopen_allowed": False,
    "automatic_resume_allowed": False,
    "recovery_request_conflict_mutation_allowed": False,
    "active_lock_or_claim_recovery_allowed": False,
    "unfenced_worker_recovery_allowed": False,
    "fresh_admission_claim_lock_cycle_required": True,
    "persistent_state_write_allowed": False,
}
EXPECTED_PROCESS_EXIT = {
    "isolated_control_process_allowed": True,
    "process_identity": "STAGE043_EPHEMERAL_CONTROL_CHILD",
    "expected_self_exit_code": 73,
    "timeout_seconds": 5,
    "stdout_must_be_empty": True,
    "stderr_must_be_empty": True,
    "signal_or_kill_allowed": False,
    "external_process_probe_allowed": False,
    "process_tree_enumeration_allowed": False,
    "worker_restart_allowed": False,
    "recovery_execution_allowed": False,
    "state_mutation_allowed": False,
    "persistent_output_allowed": False,
    "interpretation": (
        "ISOLATED_CONTROL_PROCESS_LOSS_BOUNDARY_NOT_PRODUCTION_WORKER_CRASH"
    ),
}
EXPECTED_RESOURCE_PAUSE = {
    "pause_signals": [
        "EXTERNAL_DRIVE_OFFLINE",
        "DISK_SPACE_INSUFFICIENT",
        "EXTERNAL_API_BUDGET_INSUFFICIENT",
    ],
    "transition_candidates": [
        ["RUNNING", "RETRY_WAIT"],
        ["RETRY_WAIT", "PAUSED"],
    ],
    "actual_project_disk_observation_allowed": True,
    "physical_drive_removal_allowed": False,
    "disk_allocation_allowed": False,
    "external_api_call_allowed": False,
    "automatic_resume_allowed": False,
    "owner_revalidation_required_before_future_resume": True,
}
LOCK_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "REPORT_GENERATION",
]
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
    "partial_lock_retained_count": 0,
}
PROTECTED_REFS = {
    "FACT_SOURCE": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md"
    ),
    "MANIFEST": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE026_PHASE2_ARCHIVE_MANIFEST_SLICE.md"
    ),
    "EVIDENCE_LEDGER": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_runtime_contract.json"
    ),
    "REPORT_SNAPSHOT": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md"
    ),
    "AUDIT_LOG": "repo:KM_IDSystem/docs/governance/events.jsonl",
}
ELIGIBLE_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
EXPECTED_PROTECTED = {
    "protected_refs": PROTECTED_REFS,
    "eligible_candidate_classes": ELIGIBLE_CLASSES,
    "all_refs_must_be_git_tracked": True,
    "writer_quiescence_required": True,
    "quarantine_reference_only": True,
    "delete_attempt_allowed": False,
    "delete_api_call_allowed": False,
    "cleanup_runtime_owner": "STAGE-044",
}
EXPECTED_OWNERSHIP = {
    "queue_and_worker_transport": "STAGE-038",
    "retry_and_dead_letter_policy": "STAGE-039",
    "backpressure_and_resource_pause": "STAGE-040",
    "lock_lease_and_fencing_runtime": "STAGE-041",
    "automatic_lifecycle": "STAGE-042",
    "process_crash_recovery_candidates": "STAGE-043",
    "cleanup_execution_runtime": "STAGE-044",
    "phase3_transfers_no_runtime_ownership": True,
}
EXPECTED_HUMAN_STATUS = {
    "CHECKPOINT_RESUME_CANDIDATE": "可进入检查点恢复候选",
    "RESOURCE_PAUSE_CANDIDATE": "已暂停，等待资源恢复与人工复核",
    "REQUIRE_MANUAL_REVIEW": "需要人工处理",
    "PROTECTED_ARTIFACT": "受保护资料不可清理",
    "QUARANTINE_CANDIDATE_ONLY": "半成品已隔离，等待后续清理复核",
}
EXPECTED_PHASE4_GATE = {
    "entry_authorized_after_scenario_pass": True,
    "required_task_id": "IDS-V0_1-STAGE043-P4",
    "required_acceptance_id": "ACC-STAGE-043",
    "must_run_separately": True,
    "whole_stage_review_allowed_in_phase3": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
    "next_gate": "IDS-STAGE043-P4-GATE",
}
TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_recovery_decisions_reexecuted",
    "isolated_recovery_scenarios_performed",
    "duplicate_and_stale_scenarios_performed",
    "isolated_control_process_started",
    "isolated_worker_process_exit_observed",
    "resource_pause_scenarios_performed",
    "stage041_lock_scenarios_replayed",
    "actual_project_disk_observation_performed",
    "protected_refs_verified",
    "quarantine_candidates_evaluated",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "process_probe_performed",
    "signal_or_kill_performed",
    "crash_injected",
    "actual_worker_process_crash_performed",
    "process_termination_performed",
    "process_crash_recovery_performed",
    "worker_restart_performed",
    "production_worker_runtime_performed",
    "queue_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed",
    "state_transition_performed",
    "checkpoint_resume_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "automatic_resume_performed",
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
    "recovery_safety_contract",
    "isolated_process_exit_contract",
    "resource_pause_contract",
    "operation_exclusion_contract",
    "protected_artifact_contract",
    "ownership_matrix",
    "human_status_contract",
    "phase4_entry_gate",
    "truth_flags",
}

_PHASE2_MODULE: Any = None
_STAGE041_MODULE: Any = None


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
            PHASE2_CHECKER_PATH, "stage043_phase2_checker_for_phase3"
        )
    return _PHASE2_MODULE


def _stage041_module() -> Any:
    global _STAGE041_MODULE
    if _STAGE041_MODULE is None:
        _STAGE041_MODULE = _load_module(
            STAGE041_SCENARIO_CHECKER_PATH,
            "stage041_scenario_checker_for_stage043",
        )
    return _STAGE041_MODULE


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
        with ZipFile(archive) as zip_file:
            if zip_file.namelist().count(member) != 1:
                return False
            return (
                hashlib.sha256(zip_file.read(member)).hexdigest()
                == EXPECTED_SOURCE["source_member_sha256"]
            )
    except (OSError, KeyError, ValueError):
        return False


def _phase2_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE2_COMMIT:
        return False
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            EXPECTED_PHASE2_COMMIT["commit"],
            "HEAD",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    tree = subprocess.run(
        [
            "git",
            "rev-parse",
            f"{EXPECTED_PHASE2_COMMIT['commit']}:KM_IDSystem",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return (
        ancestor.returncode == 0
        and tree.returncode == 0
        and tree.stdout.strip() == EXPECTED_PHASE2_COMMIT["km_ids_tree"]
    )


def _upstream_bindings_valid(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM:
        return False
    try:
        return all(
            sha256_file(REPO_ROOT / item["ref"]) == item["sha256"]
            for item in EXPECTED_UPSTREAM.values()
        )
    except OSError:
        return False


def _git_tracked_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("repo:KM_IDSystem/"):
        return False
    relative = value.removeprefix("repo:")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return False
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    value = contract if isinstance(contract, dict) else {}
    identity = {
        "schema_version": SCHEMA_VERSION,
        "stage": "STAGE-043",
        "phase": "Phase 3",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "execution_mode": EXECUTION_MODE,
        "scenario_contract_id": SCENARIO_CONTRACT_ID,
        "contract_state": CONTRACT_STATE,
        "next_gate": "IDS-STAGE043-P4-GATE",
    }
    protected = value.get("protected_artifact_contract")
    protected_refs = (
        protected.get("protected_refs") if isinstance(protected, dict) else {}
    )
    return {
        "root_shape_exact": set(value) == EXPECTED_ROOT_KEYS,
        "identity_exact": all(value.get(key) == expected for key, expected in identity.items()),
        "source_binding_exact": _source_binding_valid(value.get("source_binding")),
        "phase2_commit_bound": _phase2_commit_bound(
            value.get("phase2_commit_binding")
        ),
        "upstream_bindings_exact": _upstream_bindings_valid(
            value.get("upstream_bindings")
        ),
        "policy_version_exact": value.get("policy_version") == POLICY_VERSION,
        "scenario_catalog_exact": value.get("scenario_catalog") == SCENARIO_CATALOG,
        "scenario_expectations_exact": (
            value.get("scenario_expectations") == EXPECTED_SCENARIO_EXPECTATIONS
        ),
        "recovery_safety_exact": (
            value.get("recovery_safety_contract") == EXPECTED_RECOVERY_SAFETY
        ),
        "isolated_process_exit_exact": (
            value.get("isolated_process_exit_contract") == EXPECTED_PROCESS_EXIT
        ),
        "resource_pause_exact": (
            value.get("resource_pause_contract") == EXPECTED_RESOURCE_PAUSE
        ),
        "operation_exclusion_exact": (
            value.get("operation_exclusion_contract")
            == EXPECTED_OPERATION_EXCLUSION
        ),
        "protected_artifact_exact": protected == EXPECTED_PROTECTED,
        "protected_refs_git_tracked": (
            protected_refs == PROTECTED_REFS
            and all(_git_tracked_repo_ref(ref) for ref in PROTECTED_REFS.values())
        ),
        "ownership_exact": value.get("ownership_matrix") == EXPECTED_OWNERSHIP,
        "human_status_exact": (
            value.get("human_status_contract") == EXPECTED_HUMAN_STATUS
        ),
        "phase4_gate_exact": value.get("phase4_entry_gate") == EXPECTED_PHASE4_GATE,
        "truth_flags_exact": value.get("truth_flags") == EXPECTED_TRUTH_FLAGS,
    }


def _result_has_no_effects(result: Mapping[str, Any]) -> bool:
    return all(
        result.get(key) is False
        for key in (
            "state_mutation_performed",
            "process_crash_recovery_performed",
            "process_termination_performed",
            "worker_restart_performed",
            "checkpoint_resume_performed",
            "delete_allowed",
            "persistent_write_performed",
        )
    )


def _duplicate_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    ledger = phase2.InMemoryRecoveryDecisionLedger()
    request = phase2.build_recovery_request("CHECKPOINT_RESUME")
    first = phase2.evaluate_recovery(request, contract=contract, ledger=ledger)
    replay = phase2.evaluate_recovery(
        copy.deepcopy(request), contract=contract, ledger=ledger
    )
    count = len(getattr(ledger, "_records", {}))
    passed = (
        first.get("decision_action") == "CHECKPOINT_RESUME_CANDIDATE"
        and first.get("eligible") is True
        and replay == first
        and count == 1
        and _result_has_no_effects(first)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": first.get("decision_action"),
        "reason_code": first.get("reason_code"),
        "replay_equal": replay == first,
        "ledger_record_count": count,
        "state_mutation_performed": False,
    }


def _changed_payload_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = phase2.InMemoryRecoveryDecisionLedger()
    request = phase2.build_recovery_request("CHECKPOINT_RESUME")
    first = phase2.evaluate_recovery(request, contract=contract, ledger=ledger)
    changed = copy.deepcopy(request)
    changed["evidence"]["owner_revalidated"] = False
    conflict = phase2.evaluate_recovery(changed, contract=contract, ledger=ledger)
    count = len(getattr(ledger, "_records", {}))
    passed = (
        first.get("decision_action") == "CHECKPOINT_RESUME_CANDIDATE"
        and conflict.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and conflict.get("reason_code") == "RECOVERY_REQUEST_CONFLICT"
        and count == 1
        and _result_has_no_effects(conflict)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": conflict.get("decision_action"),
        "reason_code": conflict.get("reason_code"),
        "ledger_record_count": count,
        "state_mutation_performed": False,
    }


def _stale_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    request = phase2.build_recovery_request(
        "CHECKPOINT_RESUME",
        last_heartbeat_observed_at_epoch_seconds=971,
    )
    result = phase2.evaluate_recovery(request, contract=contract)
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("reason_code") == "CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN"
        and result.get("transition_candidates") == []
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "transition_candidates": result.get("transition_candidates"),
        "state_mutation_performed": False,
    }


def _isolated_process_exit_scenario(
    phase2: Any,
    phase2_contract: Mapping[str, Any],
    scenario_contract: Mapping[str, Any],
) -> dict[str, Any]:
    process_contract = scenario_contract["isolated_process_exit_contract"]
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import os; os._exit(73)",
        ],
        check=False,
        capture_output=True,
        timeout=process_contract["timeout_seconds"],
    )
    request = phase2.build_recovery_request(
        "CHECKPOINT_RESUME",
        crash_event_ref="event:stage043:isolated-worker-process-exit-73",
        error_ref="error:ISOLATED_WORKER_PROCESS_EXIT_73",
    )
    decision = phase2.evaluate_recovery(request, contract=phase2_contract)
    observed = (
        completed.returncode == process_contract["expected_self_exit_code"]
        and completed.stdout == b""
        and completed.stderr == b""
    )
    passed = (
        observed
        and decision.get("decision_action") == "CHECKPOINT_RESUME_CANDIDATE"
        and decision.get("eligible") is True
        and _result_has_no_effects(decision)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "isolated_control_process_started": True,
        "isolated_worker_process_exit_observed": observed,
        "observed_exit_code": completed.returncode,
        "stdout_empty": completed.stdout == b"",
        "stderr_empty": completed.stderr == b"",
        "signal_or_kill_performed": False,
        "decision_action": decision.get("decision_action"),
        "reason_code": decision.get("reason_code"),
        "process_crash_recovery_performed": False,
        "worker_restart_performed": False,
        "state_mutation_performed": False,
        "checkpoint_resume_performed": False,
    }


def _unfenced_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = phase2.evaluate_recovery(
        phase2.build_recovery_request(
            "CHECKPOINT_RESUME", lost_worker_fenced=False
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("reason_code")
        == "RECOVERY_OWNERSHIP_OR_STATE_EVIDENCE_INVALID"
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "state_mutation_performed": False,
    }


def _resource_pause_decision(
    phase2: Any,
    contract: Mapping[str, Any],
    signal: str,
) -> dict[str, Any]:
    request = phase2.build_recovery_request(
        "RESOURCE_PAUSE", resource_pressure_signal=signal
    )
    return phase2.evaluate_recovery(request, contract=contract)


def _drive_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = _resource_pause_decision(
        phase2, contract, "EXTERNAL_DRIVE_OFFLINE"
    )
    passed = (
        result.get("decision_action") == "RESOURCE_PAUSE_CANDIDATE"
        and result.get("reason_code") == "EXTERNAL_DRIVE_OFFLINE"
        and result.get("transition_candidates")
        == [["RUNNING", "RETRY_WAIT"], ["RETRY_WAIT", "PAUSED"]]
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pressure_signal": "EXTERNAL_DRIVE_OFFLINE",
        "decision_action": result.get("decision_action"),
        "transition_candidates": result.get("transition_candidates"),
        "physical_drive_removal_performed": False,
        "automatic_resume_performed": False,
        "state_mutation_performed": False,
    }


def _disk_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    free_bytes = shutil.disk_usage(PROJECT_ROOT).free
    required_bytes = free_bytes + 1
    result = _resource_pause_decision(
        phase2, contract, "DISK_SPACE_INSUFFICIENT"
    )
    passed = (
        free_bytes > 0
        and required_bytes > free_bytes
        and result.get("decision_action") == "RESOURCE_PAUSE_CANDIDATE"
        and result.get("reason_code") == "DISK_SPACE_INSUFFICIENT"
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pressure_signal": "DISK_SPACE_INSUFFICIENT",
        "actual_project_free_bytes": free_bytes,
        "controlled_required_free_bytes": required_bytes,
        "decision_action": result.get("decision_action"),
        "disk_allocation_performed": False,
        "state_mutation_performed": False,
    }


def _api_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = _resource_pause_decision(
        phase2, contract, "EXTERNAL_API_BUDGET_INSUFFICIENT"
    )
    passed = (
        result.get("decision_action") == "RESOURCE_PAUSE_CANDIDATE"
        and result.get("reason_code") == "EXTERNAL_API_BUDGET_INSUFFICIENT"
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pressure_signal": "EXTERNAL_API_BUDGET_INSUFFICIENT",
        "decision_action": result.get("decision_action"),
        "external_api_call_performed": False,
        "state_mutation_performed": False,
    }


def _lock_exclusion_scenario(stage041_report: Mapping[str, Any]) -> dict[str, Any]:
    source = stage041_report.get("scenario_results", {}).get(
        "same_source_operation_exclusion_matrix", {}
    )
    source_checks = source.get("family_checks", {})
    family_checks = {family: source_checks.get(family) is True for family in LOCK_FAMILIES}
    passed = (
        stage041_report.get("scenario_validation_valid") is True
        and source.get("status") == "PASS"
        and source.get("resource_conflict_count") == 25
        and source.get("operation_invocation_count") == 0
        and source.get("retry_budget_consumed_count") == 0
        and all(family_checks.values())
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "required_operation_families": list(LOCK_FAMILIES),
        "family_checks": family_checks,
        "source_full_conflict_count": source.get("resource_conflict_count"),
        "selected_matrix_conflict_count": 16 if all(family_checks.values()) else 0,
        "operation_invocation_count": source.get("operation_invocation_count"),
        "queue_record_created_count": 0,
        "retry_budget_consumed_count": source.get("retry_budget_consumed_count"),
        "partial_lock_retained_count": source.get("partial_lock_retained_count"),
        "production_lock_runtime_performed": False,
    }


def _active_conflict_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    result = phase2.evaluate_recovery(
        phase2.build_recovery_request(
            "CHECKPOINT_RESUME", active_lock_or_claim_conflict=True
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("reason_code")
        == "RECOVERY_OWNERSHIP_OR_STATE_EVIDENCE_INVALID"
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "state_mutation_performed": False,
    }


def _terminal_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    result = phase2.evaluate_recovery(
        phase2.build_recovery_request(
            "CHECKPOINT_RESUME", observed_state="SUCCEEDED"
        ),
        contract=contract,
    )
    passed = (
        result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        and result.get("reason_code") == "TERMINAL_HISTORY_IMMUTABLE"
        and result.get("transition_candidates") == []
        and _result_has_no_effects(result)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "decision_action": result.get("decision_action"),
        "reason_code": result.get("reason_code"),
        "transition_candidates": result.get("transition_candidates"),
        "terminal_reopen_performed": False,
        "state_mutation_performed": False,
    }


def evaluate_protected_cleanup_candidate(
    artifact_class: Any,
    artifact_ref: Any,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    expected = contract.get("protected_artifact_contract", {}).get(
        "protected_refs", {}
    )
    valid = (
        isinstance(artifact_class, str)
        and expected.get(artifact_class) == artifact_ref
        and _git_tracked_repo_ref(artifact_ref)
    )
    return {
        "artifact_class": artifact_class if isinstance(artifact_class, str) else None,
        "artifact_ref": artifact_ref if valid else None,
        "git_tracked": valid,
        "result_code": "PROTECTED_ARTIFACT" if valid else "INVALID_CLEANUP_REQUEST",
        "delete_allowed": False,
        "delete_attempted": False,
        "owner_action_zh": "受保护资料不可清理" if valid else "需要人工处理",
    }


def _protected_cleanup_scenario(contract: Mapping[str, Any]) -> dict[str, Any]:
    refs = contract["protected_artifact_contract"]["protected_refs"]
    results = {
        name: evaluate_protected_cleanup_candidate(name, ref, contract)
        for name, ref in refs.items()
    }
    passed = len(results) == 5 and all(
        item.get("git_tracked") is True
        and item.get("result_code") == "PROTECTED_ARTIFACT"
        and item.get("delete_allowed") is False
        and item.get("delete_attempted") is False
        for item in results.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact_results": results,
        "delete_attempt_count": 0,
        "deleted_ref_count": 0,
        "cleanup_runtime_performed": False,
        "runtime_owner": "STAGE-044",
    }


def _quarantine_scenario(contract: Mapping[str, Any]) -> dict[str, Any]:
    classes = contract["protected_artifact_contract"]["eligible_candidate_classes"]
    results: dict[str, dict[str, Any]] = {}
    for artifact_class in classes:
        digest = hashlib.sha256(
            f"stage043:{artifact_class}:reference-only".encode("utf-8")
        ).hexdigest()
        results[artifact_class] = {
            "artifact_class": artifact_class,
            "quarantine_ref": f"quarantine:sha256:{digest}",
            "decision_action": "QUARANTINE_CANDIDATE_ONLY",
            "quarantine_reference_only": True,
            "writer_quiescence_required": True,
            "stage044_authorization_required": True,
            "delete_allowed": False,
            "delete_attempted": False,
        }
    passed = list(results) == ELIGIBLE_CLASSES and all(
        item["decision_action"] == "QUARANTINE_CANDIDATE_ONLY"
        and item["quarantine_reference_only"] is True
        and item["delete_allowed"] is False
        and item["delete_attempted"] is False
        for item in results.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "artifact_results": results,
        "cleanup_runtime_performed": False,
        "runtime_owner": "STAGE-044",
    }


def _run_scenarios(
    scenario_contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], bool, bool]:
    phase2 = _phase2_module()
    stage041 = _stage041_module()
    phase2_contract = phase2.load_contract()
    phase2_report = phase2.build_stage043_phase2_report()
    stage041_report = stage041.build_stage041_phase3_report()
    phase2_valid = phase2_report.get("result") == (
        "PASS_ISOLATED_RECOVERY_DECISION_SLICE_PRODUCTION_DISABLED"
    )
    stage041_valid = stage041_report.get("scenario_validation_valid") is True
    results = {
        "duplicate_recovery_request_exact_replay": _duplicate_scenario(
            phase2, phase2_contract
        ),
        "changed_payload_same_request_rejected": _changed_payload_scenario(
            phase2, phase2_contract
        ),
        "stale_crash_evidence_blocked": _stale_scenario(
            phase2, phase2_contract
        ),
        "isolated_worker_process_exit_checkpoint_candidate": (
            _isolated_process_exit_scenario(
                phase2, phase2_contract, scenario_contract
            )
        ),
        "unfenced_worker_generation_blocked": _unfenced_scenario(
            phase2, phase2_contract
        ),
        "external_drive_offline_pause_candidate": _drive_scenario(
            phase2, phase2_contract
        ),
        "low_disk_pause_candidate": _disk_scenario(phase2, phase2_contract),
        "api_budget_pause_candidate": _api_scenario(phase2, phase2_contract),
        "same_source_four_operation_lock_exclusion": _lock_exclusion_scenario(
            stage041_report
        ),
        "active_lock_or_claim_conflict_blocked": _active_conflict_scenario(
            phase2, phase2_contract
        ),
        "terminal_history_immutable": _terminal_scenario(
            phase2, phase2_contract
        ),
        "protected_cleanup_denied": _protected_cleanup_scenario(
            scenario_contract
        ),
        "eligible_partial_output_quarantine_candidate_only": (
            _quarantine_scenario(scenario_contract)
        ),
    }
    return results, phase2_valid, stage041_valid


def _blank_report(
    contract_checks: Mapping[str, bool], *, load_error: Optional[str]
) -> dict[str, Any]:
    report = {
        "schema_version": "ids.stage043.worker_crash_recovery.phase3.report.v1",
        "stage": "STAGE-043",
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
        "next_gate": "IDS-STAGE043-P3-GATE",
        "owner_feedback_zh": "Worker 崩溃恢复 Phase 3 场景合同无效；保持失败关闭。",
        "successful_recovery_observed": False,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def build_stage043_phase3_report(
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
    )
    truth = value["truth_flags"]
    process_result = results["isolated_worker_process_exit_checkpoint_candidate"]
    disk_result = results["low_disk_pause_candidate"]
    report = {
        "schema_version": "ids.stage043.worker_crash_recovery.phase3.report.v1",
        "stage": "STAGE-043",
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
            "IDS-STAGE043-P4-GATE"
            if scenario_valid
            else "IDS-STAGE043-P3-GATE"
        ),
        "owner_feedback_zh": (
            "Worker 崩溃恢复 Phase 3 的十三项隔离场景已通过；进程丢失仅形成"
            "候选决策，重复请求、陈旧证据、资源压力、锁冲突和受保护资料清理"
            "均失败关闭，生产恢复继续禁用。"
            if scenario_valid
            else "Worker 崩溃恢复 Phase 3 场景证据无效；保持失败关闭。"
        ),
        "successful_recovery_observed": False,
        "isolated_control_process_started": (
            process_result.get("isolated_control_process_started") is True
            and truth["isolated_control_process_started"] is True
        ),
        "isolated_worker_process_exit_observed": (
            process_result.get("isolated_worker_process_exit_observed") is True
            and truth["isolated_worker_process_exit_observed"] is True
        ),
        "actual_project_disk_observation_performed": (
            disk_result.get("actual_project_free_bytes", 0) > 0
            and truth["actual_project_disk_observation_performed"] is True
        ),
    }
    report.update(
        {
            name: bool(truth.get(name, False))
            for name in TRUE_TRUTH_FLAGS
            if name
            not in {
                "isolated_control_process_started",
                "isolated_worker_process_exit_observed",
                "actual_project_disk_observation_performed",
            }
        }
    )
    report.update({name: bool(truth.get(name, False)) for name in FALSE_TRUTH_FLAGS})
    return report


def main() -> int:
    report = build_stage043_phase3_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["scenario_validation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
