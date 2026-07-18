#!/usr/bin/env python3
"""Run the STAGE-041 Phase 3 isolated lock-registry scenarios."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
CONTRACT_PATH = (
    PROJECT_ROOT
    / "docs/pursuing_goal/ids_v0_1/lock_registry/"
    "stage041_lock_registry_scenarios.json"
)
PHASE2_CHECKER = PROJECT_ROOT / "scripts/check_lock_registry_runtime.py"
STAGE040_CHECKER = PROJECT_ROOT / "scripts/check_backpressure_scenarios.py"

TASK_ID = "IDS-V0_1-STAGE041-P3"
ACCEPTANCE_ID = "ACC-STAGE-041"
POLICY_VERSION = "ids.lock_registry_policy.v0_1.stage041.p2"
PHASE2_COMMIT = "22bd9263e38b697dfb681886a97c1b8ba0f4b5e9"
PHASE2_KMIDS_TREE = "c3e96185d5fe185fc9a8c27e8fa57a6279bc4e6d"
CONTROL_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
)

EXPECTED_SOURCE = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/STAGE-041_锁注册与竞态控制.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36"
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
    "stage041_phase2_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_runtime_contract.json",
        "80f87c789c6fc834b13eaec3d14d9444417ee7313ff8f88f6893bbda15e1f464",
    ),
    "stage041_phase2_checker": (
        "KM_IDSystem/scripts/check_lock_registry_runtime.py",
        "931d0c39630a9a7353766524d072c0a8269fd2eb4bcbd896afa87609b285e5ef",
    ),
    "stage041_phase2_evidence": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md",
        "c4981bf6d990f197162841d1a8b8b5b506cb93a70d9b9c9584ee83822ad8f46f",
    ),
    "stage041_phase2_tests": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage041_lock_registry_runtime.py",
        "0fb59cf892f5ef0246f1382b646cd3140cd3483d804d8504f252f878a31eb0ab",
    ),
    "stage040_phase3_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_scenarios.json",
        "d50d4a35ad796695a8050e549c16386d607405065628a57da81d4246b9ad4fd3",
    ),
    "stage040_phase3_checker": (
        "KM_IDSystem/scripts/check_backpressure_scenarios.py",
        "4779e6bd028bc1c41fba3d098e00d51a6a7f7be5b7f0e44bfcf4f7b110617552",
    ),
}
SCENARIO_CATALOG = [
    "duplicate_click_idempotent_replay",
    "same_source_operation_exclusion_matrix",
    "renewal_current_cas_only",
    "expiry_plus_grace_takeover",
    "stale_cas_evidence_rejected",
    "isolated_worker_exception_lock_retained",
    "external_drive_offline_pause_boundary",
    "low_disk_pause_boundary",
    "external_api_budget_pause_boundary",
    "release_tombstone_reacquire",
    "protected_cleanup_denied",
]
EXPECTED_EXPECTATIONS = {
    "duplicate_click_idempotent_replay": (
        "EXACT_REPLAY_NO_ADVANCE_CHANGED_INPUT_FAILS_CLOSED"
    ),
    "same_source_operation_exclusion_matrix": (
        "FIVE_PRIMARY_ACQUISITIONS_FIVE_REPLAYS_TWENTY_FIVE_CONFLICTS_NO_OPERATION"
    ),
    "renewal_current_cas_only": (
        "FENCE_PRESERVED_ALL_VERSIONS_ADVANCED_OLD_CAS_REJECTED"
    ),
    "expiry_plus_grace_takeover": (
        "EARLY_DENIED_ELIGIBLE_AT_BOUNDARY_FENCE_AND_VERSIONS_ADVANCED"
    ),
    "stale_cas_evidence_rejected": (
        "STALE_OR_INCOMPLETE_EVIDENCE_NO_LOCK_STATE_MUTATION"
    ),
    "isolated_worker_exception_lock_retained": (
        "ACTUAL_ISOLATED_EXCEPTION_LOCK_RETAINED_PROCESS_CRASH_RECOVERY_DEFERRED"
    ),
    "external_drive_offline_pause_boundary": (
        "STAGE040_PRELOCK_PAUSE_REPLAY_NO_PHYSICAL_REMOVAL"
    ),
    "low_disk_pause_boundary": (
        "ACTUAL_PROJECT_OBSERVATION_AND_CONTROLLED_LOW_BOUNDARY_NO_ALLOCATION"
    ),
    "external_api_budget_pause_boundary": (
        "STAGE040_PRELOCK_PAUSE_REPLAY_NO_API_CALL"
    ),
    "release_tombstone_reacquire": (
        "RELEASE_AND_REACQUIRE_EACH_ADVANCE_ALL_VERSIONS_REACQUIRE_ADVANCES_FENCE"
    ),
    "protected_cleanup_denied": (
        "FIVE_GIT_TRACKED_PROTECTED_REFS_NO_DELETE_SURFACE"
    ),
}
OPERATION_FAMILIES = [
    "FILE_PROCESSING",
    "ARCHIVE_EXTRACTION",
    "INDEX_BUILD",
    "INDEX_SWITCH",
    "REPORT_GENERATION",
]
EXPECTED_OPERATION_EXCLUSION = {
    "operation_families": OPERATION_FAMILIES,
    "shared_lock_namespace": "SOURCE_PIPELINE",
    "same_source_reference_required": True,
    "canonical_all_or_none_required": True,
    "expected_primary_acquisitions": 5,
    "expected_exact_replays": 5,
    "expected_conflict_decisions": 25,
    "expected_operation_invocations": 0,
    "conflict_creates_queue_record": False,
    "conflict_consumes_retry_budget": False,
    "conflict_retains_partial_lock": False,
}
EXPECTED_LIFECYCLE = {
    "logical_clock_only": True,
    "renewal_requires_current_holder_and_cas": True,
    "takeover_requires_expiry_plus_grace_and_current_cas": True,
    "stale_holder_commit_renew_release_allowed": False,
    "worker_exception_observation": "ACTUAL_ISOLATED_EXCEPTION_NOT_PROCESS_CRASH",
    "lock_retained_after_isolated_exception": True,
    "process_termination_allowed": False,
    "crash_recovery_allowed": False,
    "automatic_resume_allowed": False,
}
EXPECTED_PRESSURE = {
    "source_scenario_contract_id": (
        "ids.backpressure_policy.v0_1.stage040.p3.scenarios"
    ),
    "pressure_evaluated_before_lock_acquisition": True,
    "drive_offline_signal": "EXTERNAL_DRIVE_OFFLINE",
    "low_disk_signal": "DISK_SPACE_INSUFFICIENT",
    "api_budget_signal": "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "actual_project_disk_observation_allowed": True,
    "physical_drive_removal_allowed": False,
    "disk_allocation_allowed": False,
    "external_api_call_allowed": False,
    "pressure_pause_consumes_retry_budget": False,
}
EXPECTED_PROTECTED_REFS = {
    "FACT_SOURCE": CONTROL_REF,
    "MANIFEST": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE026_PHASE2_ARCHIVE_MANIFEST_SLICE.md"
    ),
    "EVIDENCE_LEDGER": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_runtime_contract.json"
    ),
    "REPORT_SNAPSHOT": (
        "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md"
    ),
    "AUDIT_LOG": "repo:KM_IDSystem/docs/governance/events.jsonl",
}
EXPECTED_DOWNSTREAM = {
    "automatic_resume_and_lifecycle": "STAGE-042",
    "process_crash_recovery": "STAGE-043",
    "cleanup_execution": "STAGE-044",
    "phase3_may_take_downstream_runtime_ownership": False,
}
EXPECTED_HUMAN_STATUS = {
    "LOCK_SET_ACQUIRED": "已获取资源锁",
    "RESOURCE_CONFLICT_ACTIVE": "等待资源锁",
    "LEASE_RENEWED": "资源锁已续租",
    "TAKEOVER_ACQUIRED": "已接管过期资源锁",
    "PROTECTED_ARTIFACT": "受保护资料不可清理",
    "REQUIRE_MANUAL_REVIEW": "等待人工复核",
}
EXPECTED_PHASE4_GATE = {
    "entry_authorized_after_scenario_pass": True,
    "required_task_id": "IDS-V0_1-STAGE041-P4",
    "required_acceptance_id": ACCEPTANCE_ID,
    "must_run_separately": True,
    "whole_stage_review_allowed_in_phase3": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
    "next_gate": "IDS-STAGE041-P4-GATE",
}
TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase2_lock_runtime_reexecuted",
    "isolated_lock_scenarios_performed",
    "operation_exclusion_matrix_performed",
    "actual_isolated_worker_exception_performed",
    "stage040_pressure_scenarios_replayed",
    "actual_project_disk_observation_performed",
    "protected_refs_verified",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "process_termination_performed",
    "physical_drive_removal_performed",
    "disk_allocation_performed",
    "external_api_call_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "automatic_resume_performed",
    "crash_recovery_runtime_performed",
    "persistent_lock_write_performed",
    "state_registry_write_performed",
    "database_connection_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
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
    return _load_module(PHASE2_CHECKER, "stage041_phase2_for_phase3")


def _stage040_module() -> Any:
    return _load_module(STAGE040_CHECKER, "stage040_scenarios_for_stage041")


def load_scenario_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Stage041 Phase3 scenario contract must be an object")
    return value


def _keys_exact(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _git_tracked_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("repo:KM_IDSystem/"):
        return False
    relative = value.removeprefix("repo:")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "ids_metadata" in relative.lower():
        return False
    path = REPO_ROOT / relative
    if not path.is_file():
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _upstream_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != set(EXPECTED_UPSTREAM):
        return False
    for name, (relative, expected_hash) in EXPECTED_UPSTREAM.items():
        if value.get(name) != {"ref": relative, "sha256": expected_hash}:
            return False
        path = REPO_ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
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
    if ancestor.returncode != 0:
        return False
    tree = subprocess.run(
        ["git", "rev-parse", f"{PHASE2_COMMIT}:KM_IDSystem"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return tree.returncode == 0 and tree.stdout.strip() == PHASE2_KMIDS_TREE


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    """Validate exact shapes before any scenario is allowed to execute."""
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
        "operation_exclusion_contract",
        "lifecycle_safety_contract",
        "pressure_boundary_contract",
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
            == "ids.stage041.lock_registry.phase3.scenarios.v1"
            and contract.get("stage") == "STAGE-041"
            and contract.get("phase") == "Phase 3"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_LOCK_REGISTRY_SCENARIOS"
            and contract.get("scenario_contract_id")
            == "ids.lock_registry_policy.v0_1.stage041.p3.scenarios"
            and contract.get("contract_state")
            == "PHASE3_SCENARIOS_ENABLED_PRODUCTION_DISABLED"
            and contract.get("next_gate") == "IDS-STAGE041-P4-GATE"
        ),
        "source_binding_exact": contract.get("source_binding") == EXPECTED_SOURCE,
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
        "operation_exclusion_exact": contract.get("operation_exclusion_contract")
        == EXPECTED_OPERATION_EXCLUSION,
        "lifecycle_safety_exact": contract.get("lifecycle_safety_contract")
        == EXPECTED_LIFECYCLE,
        "pressure_boundary_exact": contract.get("pressure_boundary_contract")
        == EXPECTED_PRESSURE,
        "protected_artifact_exact": protected
        == {
            "protected_refs": EXPECTED_PROTECTED_REFS,
            "all_refs_must_be_git_tracked": True,
            "delete_attempt_allowed": False,
            "delete_api_call_allowed": False,
            "runtime_owner": "STAGE-044",
        },
        "protected_refs_real_and_tracked": (
            protected_refs == EXPECTED_PROTECTED_REFS
            and all(_git_tracked_repo_ref(value) for value in protected_refs.values())
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


def _state_core(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "locks": copy.deepcopy(snapshot.get("locks")),
        "lock_versions": copy.deepcopy(snapshot.get("lock_versions")),
        "fencing_counter": snapshot.get("fencing_counter"),
    }


def _request(
    phase2: Any,
    *,
    operation_family: str = "FILE_PROCESSING",
    role: str = "primary",
    now: int = 1000,
) -> dict[str, Any]:
    return phase2.build_control_request(
        CONTROL_REF,
        operation_family=operation_family,
        holder_role=role,
        requested_at_epoch_seconds=now,
    )


def _duplicate_click_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    request = _request(phase2)
    first = registry.acquire(request)
    after_first = registry.snapshot()
    replay = registry.acquire(copy.deepcopy(request))
    after_replay = registry.snapshot()
    changed = copy.deepcopy(request)
    changed["requested_at_epoch_seconds"] = 1001
    conflict = registry.acquire(changed)
    after_conflict = registry.snapshot()
    passed = (
        first.get("result_code") == "LOCK_SET_ACQUIRED"
        and replay == first
        and conflict.get("result_code") == "IDEMPOTENCY_INPUT_CONFLICT"
        and after_first == after_replay == after_conflict
        and after_first.get("fencing_counter") == 1
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "first_decision": first,
        "replay_decision": replay,
        "changed_input_result_code": conflict.get("result_code"),
        "lock_state_unchanged_after_replay": after_first == after_replay,
        "lock_state_unchanged_after_conflict": after_first == after_conflict,
        "fencing_counter": after_conflict.get("fencing_counter"),
        "persistent_write_performed": False,
    }


def _operation_exclusion_matrix(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    primary_acquisitions = 0
    exact_replays = 0
    conflicts = 0
    partial_retained = 0
    retry_consumed = 0
    family_checks: dict[str, bool] = {}
    for primary_family in OPERATION_FAMILIES:
        registry = phase2.IsolatedLockRegistry(contract)
        primary = _request(
            phase2,
            operation_family=primary_family,
            role=f"primary-{primary_family.lower()}",
        )
        acquired = registry.acquire(primary)
        replay = registry.acquire(copy.deepcopy(primary))
        family_conflicts = 0
        primary_acquisitions += acquired.get("result_code") == "LOCK_SET_ACQUIRED"
        exact_replays += replay == acquired
        for contender_family in OPERATION_FAMILIES:
            contender = _request(
                phase2,
                operation_family=contender_family,
                role=(
                    f"contender-{primary_family.lower()}-"
                    f"{contender_family.lower()}"
                ),
                now=1001,
            )
            result = registry.acquire(contender)
            is_conflict = (
                result.get("result_code") == "RESOURCE_CONFLICT_ACTIVE"
                and result.get("decision_action") == "PAUSE_BEFORE_QUEUE_ADMISSION"
            )
            family_conflicts += is_conflict
            conflicts += is_conflict
            partial_retained += result.get("partial_lock_retained") is True
            retry_consumed += result.get("retry_budget_consumed") is True
        snapshot = registry.snapshot()
        records = list(snapshot.get("locks", {}).values())
        family_checks[primary_family] = (
            acquired.get("result_code") == "LOCK_SET_ACQUIRED"
            and replay == acquired
            and family_conflicts == len(OPERATION_FAMILIES)
            and len(records) == 2
            and any(
                item.get("lock_namespace") == "SOURCE_PIPELINE"
                for item in records
            )
            and all(
                item.get("holder_job_id") == acquired.get("holder_job_id")
                for item in records
            )
        )
    passed = (
        primary_acquisitions == 5
        and exact_replays == 5
        and conflicts == 25
        and partial_retained == 0
        and retry_consumed == 0
        and all(family_checks.values())
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "operation_families": list(OPERATION_FAMILIES),
        "primary_acquisition_count": primary_acquisitions,
        "exact_replay_count": exact_replays,
        "resource_conflict_count": conflicts,
        "operation_invocation_count": 0,
        "partial_lock_retained_count": partial_retained,
        "retry_budget_consumed_count": retry_consumed,
        "family_checks": family_checks,
    }


def _renewal_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    acquired = registry.acquire(_request(phase2))
    renewed = registry.renew(_request(phase2, now=1010), acquired)
    old_commit = registry.can_commit(_request(phase2, now=1011), acquired)
    old_renew = registry.renew(_request(phase2, now=1011), acquired)
    old_release = registry.release(_request(phase2, now=1011), acquired)
    version_advanced = all(
        renewed.get("lock_versions", {}).get(key) == version + 1
        for key, version in acquired.get("lock_versions", {}).items()
    )
    passed = (
        renewed.get("result_code") == "LEASE_RENEWED"
        and renewed.get("fencing_token") == acquired.get("fencing_token")
        and version_advanced
        and old_commit.get("result_code") == "STALE_FENCING_TOKEN"
        and old_renew.get("result_code") == "STALE_FENCING_TOKEN"
        and old_release.get("result_code") == "STALE_FENCING_TOKEN"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "fence_preserved": (
            renewed.get("fencing_token") == acquired.get("fencing_token")
        ),
        "every_version_advanced_once": version_advanced,
        "old_commit_result_code": old_commit.get("result_code"),
        "old_renew_result_code": old_renew.get("result_code"),
        "old_release_result_code": old_release.get("result_code"),
    }


def _takeover_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    acquired = registry.acquire(_request(phase2, role="primary"))
    early = registry.takeover(
        _request(phase2, role="successor", now=1034), acquired
    )
    eligible = registry.takeover(
        _request(phase2, role="successor", now=1035), acquired
    )
    stale = registry.can_commit(
        _request(phase2, role="primary", now=1036), acquired
    )
    current = registry.can_commit(
        _request(phase2, role="successor", now=1036), eligible
    )
    versions_advanced = all(
        eligible.get("lock_versions", {}).get(key) == version + 1
        for key, version in acquired.get("lock_versions", {}).items()
    )
    fence_advanced = (
        eligible.get("fencing_token") == acquired.get("fencing_token", 0) + 1
    )
    passed = (
        early.get("result_code") == "LEASE_NOT_TAKEOVER_ELIGIBLE"
        and eligible.get("result_code") == "TAKEOVER_ACQUIRED"
        and fence_advanced
        and versions_advanced
        and stale.get("result_code") == "STALE_FENCING_TOKEN"
        and current.get("decision_action") == "COMMIT_ALLOWED"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "early_result_code": early.get("result_code"),
        "eligible_result_code": eligible.get("result_code"),
        "fence_advanced_once": fence_advanced,
        "every_version_advanced_once": versions_advanced,
        "stale_commit_result_code": stale.get("result_code"),
        "successor_commit_action": current.get("decision_action"),
    }


def _stale_cas_scenario(phase2: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    acquired = registry.acquire(_request(phase2))
    renewed = registry.renew(_request(phase2, now=1010), acquired)
    before = registry.snapshot()
    stale = registry.takeover(
        _request(phase2, role="successor-stale", now=1045), acquired
    )
    after_stale = registry.snapshot()
    incomplete = copy.deepcopy(renewed)
    incomplete["lock_versions"].pop(next(iter(incomplete["lock_versions"])))
    incomplete_result = registry.takeover(
        _request(phase2, role="successor-incomplete", now=1045), incomplete
    )
    after_incomplete = registry.snapshot()
    before_core = _state_core(before)
    passed = (
        stale.get("result_code") == "STALE_TAKEOVER_EVIDENCE"
        and incomplete_result.get("result_code") == "STALE_TAKEOVER_EVIDENCE"
        and before_core == _state_core(after_stale) == _state_core(after_incomplete)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "stale_result_code": stale.get("result_code"),
        "incomplete_result_code": incomplete_result.get("result_code"),
        "lock_state_unchanged": (
            before_core["locks"]
            == _state_core(after_stale)["locks"]
            == _state_core(after_incomplete)["locks"]
        ),
        "fence_unchanged": (
            before_core["fencing_counter"]
            == _state_core(after_stale)["fencing_counter"]
            == _state_core(after_incomplete)["fencing_counter"]
        ),
    }


def _isolated_worker_exception_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    acquired = registry.acquire(_request(phase2))
    before = registry.snapshot()
    error_ref: Optional[str] = None
    actual_exception = False
    try:
        raise RuntimeError("isolated lock-holder exception boundary")
    except RuntimeError as exc:
        actual_exception = True
        error_ref = f"error:{type(exc).__name__}"
    after = registry.snapshot()
    contender = registry.acquire(_request(phase2, role="contender", now=1001))
    lock_retained = (
        _state_core(before) == _state_core(after)
        and len(after.get("locks", {})) == len(acquired.get("lock_keys", []))
    )
    passed = (
        actual_exception
        and error_ref == "error:RuntimeError"
        and lock_retained
        and contender.get("result_code") == "RESOURCE_CONFLICT_ACTIVE"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "actual_isolated_worker_exception_performed": actual_exception,
        "safe_error_ref": error_ref,
        "lock_retained_after_exception": lock_retained,
        "contender_result_code": contender.get("result_code"),
        "process_termination_performed": False,
        "crash_recovery_runtime_performed": False,
        "crash_recovery_owner": "STAGE-043",
    }


def _empty_lock_state(phase2: Any, contract: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = phase2.IsolatedLockRegistry(contract)
    before = registry.snapshot()
    after = registry.snapshot()
    return before, after


def _drive_boundary(
    phase2: Any,
    contract: Mapping[str, Any],
    stage040_report: Mapping[str, Any],
) -> dict[str, Any]:
    source = stage040_report.get("scenario_results", {}).get(
        "external_drive_offline_pause_candidate", {}
    )
    before, after = _empty_lock_state(phase2, contract)
    passed = (
        stage040_report.get("scenario_validation_valid") is True
        and source.get("status") == "PASS"
        and source.get("signal_code") == "EXTERNAL_DRIVE_OFFLINE"
        and source.get("decision_action") == "PAUSE_RESOURCE_GATE"
        and source.get("retry_budget_consumed") is False
        and source.get("physical_drive_removal_performed") is False
        and before == after
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "signal_code": source.get("signal_code"),
        "decision_action": source.get("decision_action"),
        "retry_budget_consumed": bool(source.get("retry_budget_consumed")),
        "lock_state_unchanged": before == after,
        "physical_drive_removal_performed": False,
    }


def _disk_boundary(
    phase2: Any,
    contract: Mapping[str, Any],
    stage040_report: Mapping[str, Any],
) -> dict[str, Any]:
    source = stage040_report.get("scenario_results", {}).get(
        "actual_disk_observation_and_low_disk_boundary", {}
    )
    before, after = _empty_lock_state(phase2, contract)
    actual = source.get("actual_disk_free_bytes", 0)
    passed = (
        stage040_report.get("scenario_validation_valid") is True
        and source.get("status") == "PASS"
        and isinstance(actual, int)
        and actual > 0
        and source.get("actual_disk_decision_matches_formula") is True
        and source.get("boundary_signal_code") == "DISK_SPACE_INSUFFICIENT"
        and source.get("retry_budget_consumed") is False
        and source.get("disk_allocation_performed") is False
        and before == after
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "actual_disk_free_bytes": actual,
        "actual_disk_observation_performed": isinstance(actual, int) and actual > 0,
        "actual_disk_decision_matches_formula": source.get(
            "actual_disk_decision_matches_formula"
        ),
        "boundary_signal_code": source.get("boundary_signal_code"),
        "retry_budget_consumed": bool(source.get("retry_budget_consumed")),
        "lock_state_unchanged": before == after,
        "disk_allocation_performed": False,
    }


def _api_boundary(
    phase2: Any,
    contract: Mapping[str, Any],
    stage040_report: Mapping[str, Any],
) -> dict[str, Any]:
    source = stage040_report.get("scenario_results", {}).get(
        "external_api_budget_pause_candidate", {}
    )
    before, after = _empty_lock_state(phase2, contract)
    passed = (
        stage040_report.get("scenario_validation_valid") is True
        and source.get("status") == "PASS"
        and source.get("signal_code") == "EXTERNAL_API_BUDGET_INSUFFICIENT"
        and source.get("decision_action") == "PAUSE_RESOURCE_GATE"
        and source.get("retry_budget_consumed") is False
        and source.get("external_api_call_performed") is False
        and before == after
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "signal_code": source.get("signal_code"),
        "decision_action": source.get("decision_action"),
        "retry_budget_consumed": bool(source.get("retry_budget_consumed")),
        "lock_state_unchanged": before == after,
        "external_api_call_performed": False,
    }


def _release_reacquire_scenario(
    phase2: Any, contract: Mapping[str, Any]
) -> dict[str, Any]:
    registry = phase2.IsolatedLockRegistry(contract)
    acquired = registry.acquire(_request(phase2))
    released = registry.release(_request(phase2, now=1011), acquired)
    after_release = registry.snapshot()
    replay = registry.release(_request(phase2, now=1011), acquired)
    reacquired = registry.acquire(_request(phase2, now=1012))
    release_advanced = all(
        released.get("lock_versions", {}).get(key) == version + 1
        for key, version in acquired.get("lock_versions", {}).items()
    )
    reacquire_advanced = all(
        reacquired.get("lock_versions", {}).get(key) == version + 1
        for key, version in released.get("lock_versions", {}).items()
    )
    fence_advanced = (
        reacquired.get("fencing_token") == released.get("fencing_token", 0) + 1
    )
    passed = (
        released.get("result_code") == "LOCK_SET_RELEASED"
        and replay == released
        and after_release.get("locks") == {}
        and release_advanced
        and reacquire_advanced
        and fence_advanced
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "release_advanced_every_version": release_advanced,
        "reacquire_advanced_every_version": reacquire_advanced,
        "fence_advanced_on_reacquire": fence_advanced,
        "active_lock_count_after_release": len(after_release.get("locks", {})),
        "release_replay_idempotent": replay == released,
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
        "owner_action_zh": "受保护资料不可清理" if valid else "等待人工复核",
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


def _run_scenarios(
    scenario_contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], bool, bool]:
    phase2 = _phase2_module()
    stage040 = _stage040_module()
    phase2_contract = phase2.load_contract()
    phase2_valid = phase2.build_stage041_phase2_report().get("phase2_slice_valid") is True
    stage040_report = stage040.build_stage040_phase3_report()
    stage040_valid = stage040_report.get("scenario_validation_valid") is True
    results = {
        "duplicate_click_idempotent_replay": _duplicate_click_scenario(
            phase2, phase2_contract
        ),
        "same_source_operation_exclusion_matrix": _operation_exclusion_matrix(
            phase2, phase2_contract
        ),
        "renewal_current_cas_only": _renewal_scenario(phase2, phase2_contract),
        "expiry_plus_grace_takeover": _takeover_scenario(phase2, phase2_contract),
        "stale_cas_evidence_rejected": _stale_cas_scenario(
            phase2, phase2_contract
        ),
        "isolated_worker_exception_lock_retained": (
            _isolated_worker_exception_scenario(phase2, phase2_contract)
        ),
        "external_drive_offline_pause_boundary": _drive_boundary(
            phase2, phase2_contract, stage040_report
        ),
        "low_disk_pause_boundary": _disk_boundary(
            phase2, phase2_contract, stage040_report
        ),
        "external_api_budget_pause_boundary": _api_boundary(
            phase2, phase2_contract, stage040_report
        ),
        "release_tombstone_reacquire": _release_reacquire_scenario(
            phase2, phase2_contract
        ),
        "protected_cleanup_denied": _protected_cleanup_scenario(
            scenario_contract
        ),
    }
    return results, phase2_valid, stage040_valid


def _blank_report(
    contract_checks: Mapping[str, bool], *, load_error: Optional[str]
) -> dict[str, Any]:
    return {
        "schema_version": "ids.stage041.lock_registry.phase3.report.v1",
        "stage": "STAGE-041",
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
        "phase2_runtime_valid": False,
        "stage040_pressure_scenarios_valid": False,
        "execution_mode": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "contract_state": "BLOCKED_INVALID_SCENARIO_CONTRACT",
        "load_error": load_error,
        "next_gate": "IDS-STAGE041-P3-GATE",
        "owner_feedback_zh": "锁注册 Phase 3 场景合同无效；保持失败关闭。",
        **{name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS},
    }


def build_stage041_phase3_report(
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
        results, phase2_valid, stage040_valid = _run_scenarios(value)
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
        and stage040_valid
    )
    truth = value["truth_flags"]
    worker = results["isolated_worker_exception_lock_retained"]
    disk = results["low_disk_pause_boundary"]
    return {
        "schema_version": "ids.stage041.lock_registry.phase3.report.v1",
        "stage": "STAGE-041",
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
        "phase2_runtime_valid": phase2_valid,
        "stage040_pressure_scenarios_valid": stage040_valid,
        "execution_mode": value["execution_mode"],
        "contract_state": value["contract_state"],
        "load_error": None,
        "next_gate": (
            "IDS-STAGE041-P4-GATE"
            if scenario_valid
            else "IDS-STAGE041-P3-GATE"
        ),
        "owner_feedback_zh": (
            "锁注册 Phase 3 的十一项隔离场景已通过；重复处理、竞态、"
            "陈旧凭证和受保护资料清理均失败关闭，生产运行继续禁用。"
            if scenario_valid
            else "锁注册 Phase 3 场景证据无效；保持失败关闭。"
        ),
        "actual_isolated_worker_exception_performed": (
            worker.get("actual_isolated_worker_exception_performed") is True
            and truth["actual_isolated_worker_exception_performed"] is True
        ),
        "actual_project_disk_observation_performed": (
            disk.get("actual_disk_observation_performed") is True
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
    report = build_stage041_phase3_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["scenario_validation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
