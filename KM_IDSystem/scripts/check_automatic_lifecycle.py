#!/usr/bin/env python3
"""Validate the STAGE-042 Phase 1 automatic-lifecycle contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any
from zipfile import ZipFile


CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
    "stage042_automatic_lifecycle_contract.json"
)
STATE_MODEL_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/job_state_model/"
    "stage037_job_state_model_index.json"
)

EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "local_code",
    "domain",
    "entrance",
    "pursuing_goal",
    "automatic_lifecycle_contract_id",
    "contract_state",
    "execution_ready",
    "next_gate",
    "source_binding",
    "predecessor_binding",
    "upstream_bindings",
    "lifecycle_state_contract",
    "transition_guard_contract",
    "automatic_start_contract",
    "automatic_pause_contract",
    "automatic_resume_contract",
    "safe_close_contract",
    "upstream_runtime_boundaries",
    "lifecycle_idempotency_contract",
    "lifecycle_evidence_contract",
    "safe_shutdown_contract",
    "cleanup_candidate_contract",
    "parameter_contract",
    "human_status_projection",
    "phase2_entry_gate",
    "truth_flags",
}

EXPECTED_SOURCE_BINDING = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-042_自动运行、暂停、恢复与关闭.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08"
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
    "stage041_review_commit": "f6b30f8a55d60f1b37b9d57ee55587149ad43876",
    "stage041_review_tree": "af262c4139f652d937534d58e826fe28a236f2a4",
    "stage041_review_parent": "68a89e9c3d1fbb3eae347fe71f1bbbbf7bc9ddc2",
    "stage041_review_status": "completed_reviewed_local",
    "stage041_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

EXPECTED_UPSTREAM = {
    "stage037_state_index_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "job_state_model/stage037_job_state_model_index.json"
        ),
        "sha256": (
            "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3"
        ),
    },
    "stage038_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "worker_queue_baseline/stage038_worker_queue_delivery_contract.json"
        ),
        "sha256": (
            "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4"
        ),
    },
    "stage039_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "retry_dead_letter/stage039_retry_dead_letter_delivery_contract.json"
        ),
        "sha256": (
            "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b"
        ),
    },
    "stage040_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "backpressure_policy/stage040_backpressure_delivery_contract.json"
        ),
        "sha256": (
            "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce"
        ),
    },
    "stage041_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "lock_registry/stage041_lock_registry_delivery_contract.json"
        ),
        "sha256": (
            "16d4d55ca91c92bd46e929a5741cbf6ae55d35b46a71fe3c901ce1b5e9bbfa5f"
        ),
    },
    "stage041_review_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE041_STAGE_REVIEW.md"
        ),
        "sha256": (
            "68ab244b3bf6e5f287164c8c738469425612de69a81cc128a734b19f3cb754d0"
        ),
    },
}

JOB_STATES = [
    "CREATED",
    "QUEUED",
    "CLAIMED",
    "RUNNING",
    "PAUSE_REQUESTED",
    "PAUSED",
    "RETRY_WAIT",
    "SUCCEEDED",
    "FAILED",
    "DEAD_LETTERED",
    "CANCELLED",
]
TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
AUTOMATIC_PATHS = {
    "AUTO_START": [["QUEUED", "CLAIMED"], ["CLAIMED", "RUNNING"]],
    "AUTO_PAUSE": [
        ["QUEUED", "PAUSED"],
        ["CLAIMED", "PAUSE_REQUESTED"],
        ["RUNNING", "PAUSE_REQUESTED"],
        ["PAUSE_REQUESTED", "PAUSED"],
        ["RETRY_WAIT", "PAUSED"],
    ],
    "AUTO_RESUME": [["PAUSED", "QUEUED"], ["RETRY_WAIT", "QUEUED"]],
    "SAFE_CLOSE": [
        ["CREATED", "CANCELLED"],
        ["QUEUED", "CANCELLED"],
        ["PAUSE_REQUESTED", "CANCELLED"],
        ["PAUSED", "CANCELLED"],
        ["RETRY_WAIT", "CANCELLED"],
    ],
}
FORBIDDEN_SHORTCUTS = [
    ["QUEUED", "RUNNING"],
    ["PAUSED", "RUNNING"],
    ["RUNNING", "PAUSED"],
    ["RUNNING", "CANCELLED"],
    ["FAILED", "QUEUED"],
    ["DEAD_LETTERED", "QUEUED"],
]

EXPECTED_START = {
    "decision_mode": "STATIC_CANDIDATE_ONLY",
    "required_transition_sequence": ["QUEUED->CLAIMED", "CLAIMED->RUNNING"],
    "fresh_admission_required": True,
    "claim_lease_and_lock_required": True,
    "live_lease_and_fencing_required": True,
    "direct_queued_to_running_allowed": False,
    "state_mutation_allowed": False,
    "unknown_or_stale_evidence_action": "REQUIRE_MANUAL_REVIEW",
}
EXPECTED_PAUSE = {
    "decision_mode": "STATIC_CANDIDATE_ONLY",
    "recognized_pressure_signals": [
        "QUEUE_SOFT_PRESSURE",
        "QUEUE_HARD_CAPACITY",
        "EXTERNAL_DRIVE_OFFLINE",
        "DISK_SPACE_INSUFFICIENT",
        "EXTERNAL_API_BUDGET_INSUFFICIENT",
        "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
        "SAME_SOURCE_CONFLICT",
    ],
    "mandatory_resource_pause_signals": [
        "EXTERNAL_DRIVE_OFFLINE",
        "DISK_SPACE_INSUFFICIENT",
        "EXTERNAL_API_BUDGET_INSUFFICIENT",
    ],
    "active_job_first_target_state": "PAUSE_REQUESTED",
    "checkpoint_or_quarantine_required": True,
    "running_to_paused_shortcut_allowed": False,
    "retry_budget_consumed": False,
    "state_mutation_allowed": False,
    "unknown_or_stale_observation_action": "REQUIRE_MANUAL_REVIEW",
}
EXPECTED_RESUME = {
    "decision_mode": "STATIC_CANDIDATE_ONLY",
    "resume_transition": "PAUSED->QUEUED",
    "reevaluation_candidates": [
        "QUEUE_SOFT_PRESSURE_CLEARED",
        "QUEUE_HARD_CAPACITY_CLEARED",
        "ADMISSION_RATE_WINDOW_RESET",
        "JOB_TYPE_CONCURRENCY_CLEARED",
        "RESOURCE_GATE_REVALIDATED",
        "SAME_SOURCE_CONFLICT_CLEARED",
    ],
    "owner_revalidation_required": True,
    "fresh_resource_observation_required": True,
    "new_admission_and_lock_cycle_required": True,
    "direct_resume_to_running_allowed": False,
    "terminal_job_resume_allowed": False,
    "process_crash_recovery_allowed": False,
    "state_mutation_allowed": False,
    "unknown_or_stale_evidence_action": "REQUIRE_MANUAL_REVIEW",
}
EXPECTED_CLOSE = {
    "decision_mode": "STATIC_CANDIDATE_ONLY",
    "non_active_close_states": ["CREATED", "QUEUED", "PAUSED", "RETRY_WAIT"],
    "active_job_required_sequence": [
        "CLAIMED|RUNNING->PAUSE_REQUESTED",
        "PAUSE_REQUESTED->PAUSED|CANCELLED",
    ],
    "checkpoint_or_quarantine_required": True,
    "matching_lock_release_required": True,
    "terminal_history_rewrite_allowed": False,
    "process_termination_allowed": False,
    "state_mutation_allowed": False,
}
EXPECTED_BOUNDARIES = {
    "queue_and_worker_transport_owner": "STAGE-038",
    "retry_and_dead_letter_owner": "STAGE-039",
    "backpressure_owner": "STAGE-040",
    "lock_lease_and_fencing_owner": "STAGE-041",
    "automatic_lifecycle_owner": "STAGE-042",
    "process_crash_recovery_owner": "STAGE-043",
    "cleanup_execution_owner": "STAGE-044",
    "worker_spawn_or_termination_allowed": False,
    "retry_budget_consumed_by_pause_or_resume": False,
    "lock_or_fencing_bypass_allowed": False,
    "cleanup_delete_allowed": False,
}
EXPECTED_IDEMPOTENCY = {
    "request_key_derivation": (
        "SHA256_JOB_EXPECTED_STATE_VERSION_ACTION_POLICY_EVIDENCE"
    ),
    "required_key_fields": [
        "job_id",
        "expected_state",
        "expected_state_version",
        "lifecycle_action",
        "policy_version",
        "evidence_digest",
    ],
    "state_version_compare_and_set_required": True,
    "exact_replay_returns_existing_decision": True,
    "same_key_different_payload_action": "REJECT_LIFECYCLE_REQUEST_CONFLICT",
    "append_only_audit_required": True,
}
EXPECTED_EVIDENCE = {
    "required_fields": [
        "job_id",
        "expected_state",
        "expected_state_version",
        "lifecycle_action",
        "lifecycle_request_id",
        "policy_version",
        "reason_code",
        "resource_observation_refs",
        "lock_evidence_ref",
        "fencing_token",
        "checkpoint_ref",
        "audit_ref",
        "cleanup_candidate_ref",
    ],
    "reference_only": True,
    "raw_path_allowed": False,
    "raw_payload_allowed": False,
    "secret_material_allowed": False,
    "unknown_or_stale_evidence_action": "REQUIRE_MANUAL_REVIEW",
    "unknown_field_action": "REJECT_CONTRACT",
}
EXPECTED_SHUTDOWN = {
    "ordered_steps": [
        "STOP_NEW_LIFECYCLE_DECISIONS",
        "STOP_NEW_ADMISSION_AND_CLAIMS",
        "REQUEST_ACTIVE_JOB_PAUSE",
        "WAIT_FOR_CHECKPOINT_OR_QUARANTINE",
        "FREEZE_RETRY_AND_RESUME_ELIGIBILITY",
        "RELEASE_MATCHING_ACTIVE_LOCKS",
        "VERIFY_ZERO_ACTIVE_LOCKS",
        "CLOSE_REVIEWED_WORKER_TRANSPORT",
        "PRESERVE_AUDIT_CHECKPOINT_AND_EVIDENCE_REFS",
        "VERIFY_NO_DELETE_PERSISTENCE_OR_RUNTIME_OUTPUT",
    ],
    "process_termination_allowed": False,
    "crash_recovery_claimed": False,
    "persistent_lifecycle_state_available_after_exit": False,
    "runtime_output_allowed": False,
}
EXPECTED_CLEANUP = {
    "runtime_owner": "STAGE-044",
    "candidate_only": True,
    "eligible_artifact_classes": [
        "TEMP_STAGING_OUTPUT",
        "INCOMPLETE_DERIVATIVE_OUTPUT",
    ],
    "protected_artifact_classes": [
        "FACT_SOURCE",
        "MANIFEST",
        "EVIDENCE_LEDGER",
        "REPORT_SNAPSHOT",
        "AUDIT_LOG",
    ],
    "required_preconditions": [
        "APPROVED_ROOT_IDENTITY",
        "ROOT_RELATIVE_PATH",
        "IMMUTABLE_LSTAT_IDENTITY",
        "SYMLINK_BLOCKED",
        "EXCLUSIVE_NAMESPACE_LOCK",
        "WRITER_QUIESCENCE",
        "NO_FOLLOW_TRAVERSAL",
    ],
    "delete_execution_allowed": False,
    "protected_artifact_delete_allowed": False,
}
EXPECTED_PARAMETERS = {
    "numeric_values_assigned": False,
    "deferred_parameters": [
        "lifecycle_tick_interval",
        "resume_stability_window",
        "checkpoint_wait_timeout",
        "graceful_shutdown_timeout",
        "cleanup_scan_interval",
    ],
    "phase2_selection_requirements": [
        "source",
        "rationale",
        "unit",
        "policy_version",
        "validation_evidence",
        "rollback",
    ],
    "implicit_default_allowed": False,
    "production_calibrated": False,
}
EXPECTED_HUMAN_STATUS = {
    "AUTO_START_ELIGIBLE": "可自动开始",
    "AUTO_PAUSE_REQUIRED": "等待安全暂停",
    "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION": "等待复核后恢复",
    "SAFE_SHUTDOWN_PENDING": "安全关闭中",
    "CLEANUP_CANDIDATE_ONLY": "待清理候选（不执行删除）",
    "REQUIRE_MANUAL_REVIEW": "需要人工处理",
    "RUNTIME_DISABLED": "自动生命周期未启用",
}
EXPECTED_PHASE2_GATE = {
    "entry_authorized": True,
    "required_task_id": "IDS-V0_1-STAGE042-P2",
    "required_gate": "IDS-STAGE042-P2-GATE",
    "separate_run_required": True,
    "required_work": [
        "source and register every deferred numeric parameter",
        "implement one isolated non-production lifecycle decision slice",
        "prove idempotent start pause resume and shutdown candidates",
        "map machine decisions to restrained Chinese owner status",
        "preserve Stage037-041 guards and Stage043-044 ownership",
        "keep persistence delete and production activation disabled",
    ],
}

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "automatic_lifecycle_runtime_performed",
    "automatic_start_performed",
    "automatic_pause_performed",
    "automatic_resume_performed",
    "automatic_shutdown_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "dead_letter_runtime_performed",
    "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "process_crash_recovery_performed",
    "cleanup_runtime_performed",
    "protected_ref_delete_performed",
    "database_connection_performed",
    "schema_change_performed",
    "state_registry_write_performed",
    "runtime_output_written",
    "external_api_call_performed",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_binding_valid(binding: Any) -> bool:
    if binding != EXPECTED_SOURCE_BINDING:
        return False
    try:
        archive = Path(binding["source_archive_path"])
        roadmap = archive.with_name(
            "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
        )
        instructions = archive.with_name(
            "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
        )
        if _sha256(archive) != binding["source_archive_sha256"]:
            return False
        if _sha256(roadmap) != binding["roadmap_sha256"]:
            return False
        if _sha256(instructions) != binding["instructions_sha256"]:
            return False
        with ZipFile(archive) as zf:
            matches = [
                name
                for name in zf.namelist()
                if name == binding["source_member"]
            ]
            if len(matches) != 1:
                return False
            return (
                hashlib.sha256(zf.read(matches[0])).hexdigest()
                == binding["source_member_sha256"]
            )
    except (OSError, KeyError, TypeError):
        return False


def _predecessor_valid(binding: Any, project_root: Path) -> bool:
    if binding != EXPECTED_PREDECESSOR:
        return False
    try:
        observed = subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%H%n%T%n%P",
                binding["stage041_review_commit"],
            ],
            cwd=project_root.parent,
            text=True,
        ).splitlines()
    except (OSError, subprocess.CalledProcessError, KeyError, TypeError):
        return False
    return observed == [
        binding["stage041_review_commit"],
        binding["stage041_review_tree"],
        binding["stage041_review_parent"],
    ]


def _upstream_bindings_valid(bindings: Any, project_root: Path) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    try:
        return all(
            _sha256(project_root.parent / item["ref"]) == item["sha256"]
            for item in bindings.values()
        )
    except (OSError, KeyError, TypeError):
        return False


def _state_and_guards_valid(contract: dict[str, Any], project_root: Path) -> bool:
    lifecycle = contract.get("lifecycle_state_contract")
    guards = contract.get("transition_guard_contract")
    if not isinstance(lifecycle, dict) or not isinstance(guards, dict):
        return False
    expected_lifecycle = {
        "state_model_version": "ids.job_state.v1",
        "job_states": JOB_STATES,
        "terminal_states": TERMINAL_STATES,
        "new_job_states_allowed": False,
        "terminal_state_mutation_allowed": False,
        "automatic_transition_paths": AUTOMATIC_PATHS,
        "forbidden_shortcuts": FORBIDDEN_SHORTCUTS,
        "all_paths_must_exist_upstream": True,
    }
    if lifecycle != expected_lifecycle:
        return False
    try:
        state_index = json.loads(
            (project_root / STATE_MODEL_RELATIVE).read_text(encoding="utf-8")
        )
        state_model = state_index["state_model"]
        transition = state_index["transition_contract"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False
    if state_model.get("job_states") != JOB_STATES:
        return False
    if state_model.get("terminal_states") != TERMINAL_STATES:
        return False
    allowed = {
        (source, target)
        for source, targets in state_model.get("allowed_transitions", {}).items()
        for target in targets
    }
    used = {
        tuple(edge)
        for paths in AUTOMATIC_PATHS.values()
        for edge in paths
    }
    forbidden = {tuple(edge) for edge in FORBIDDEN_SHORTCUTS}
    if not used.issubset(allowed) or allowed.intersection(forbidden):
        return False
    edge_names = {f"{source}->{target}" for source, target in used}
    return (
        set(guards)
        == {
            "compare_and_set_fields",
            "required_guards",
            "required_reference_fields",
            "missing_guard_action",
            "unknown_or_stale_evidence_action",
        }
        and guards.get("compare_and_set_fields")
        == transition.get("compare_and_set_fields")
        and set(guards.get("required_guards", {})) == edge_names
        and set(guards.get("required_reference_fields", {})) == edge_names
        and all(
            guards["required_guards"][edge]
            == transition["edge_guard_requirements"][edge]
            and guards["required_reference_fields"][edge]
            == transition["edge_reference_requirements"][edge]
            for edge in edge_names
        )
        and guards.get("missing_guard_action") == "REQUIRE_MANUAL_REVIEW"
        and guards.get("unknown_or_stale_evidence_action")
        == "REQUIRE_MANUAL_REVIEW"
    )


def evaluate_contract(
    contract: dict[str, Any],
    project_root: Path | None = None,
) -> dict[str, bool]:
    project_root = (
        project_root or Path(__file__).resolve().parents[1]
    ).resolve()
    truth = contract.get("truth_flags")
    checks = {
        "root_shape_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage042.automatic_lifecycle.phase1.v1"
            and contract.get("stage") == "STAGE-042"
            and contract.get("phase") == "Phase 1"
            and contract.get("task_id") == "IDS-V0_1-STAGE042-P1"
            and contract.get("acceptance_id") == "ACC-STAGE-042"
            and contract.get("local_code") == "D07-S006"
            and contract.get("domain") == "D07 · 任务编排与机器控制"
            and contract.get("entrance") == "IDS 系统运营入口"
            and contract.get("automatic_lifecycle_contract_id")
            == "ids.automatic_lifecycle.v0_1.p1"
            and contract.get("contract_state")
            == "PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED"
            and contract.get("execution_ready") is False
            and contract.get("next_gate") == "IDS-STAGE042-P2-GATE"
        ),
        "source_binding_exact": _source_binding_valid(
            contract.get("source_binding")
        ),
        "predecessor_binding_exact": _predecessor_valid(
            contract.get("predecessor_binding"), project_root
        ),
        "upstream_bindings_exact": _upstream_bindings_valid(
            contract.get("upstream_bindings"), project_root
        ),
        "state_and_transition_guards_exact": _state_and_guards_valid(
            contract, project_root
        ),
        "automatic_start_exact": (
            contract.get("automatic_start_contract") == EXPECTED_START
        ),
        "automatic_pause_exact": (
            contract.get("automatic_pause_contract") == EXPECTED_PAUSE
        ),
        "automatic_resume_exact": (
            contract.get("automatic_resume_contract") == EXPECTED_RESUME
        ),
        "safe_close_exact": (
            contract.get("safe_close_contract") == EXPECTED_CLOSE
        ),
        "upstream_runtime_boundaries_exact": (
            contract.get("upstream_runtime_boundaries") == EXPECTED_BOUNDARIES
        ),
        "idempotency_exact": (
            contract.get("lifecycle_idempotency_contract")
            == EXPECTED_IDEMPOTENCY
        ),
        "reference_only_evidence_exact": (
            contract.get("lifecycle_evidence_contract") == EXPECTED_EVIDENCE
        ),
        "safe_shutdown_exact": (
            contract.get("safe_shutdown_contract") == EXPECTED_SHUTDOWN
        ),
        "cleanup_candidate_exact": (
            contract.get("cleanup_candidate_contract") == EXPECTED_CLEANUP
        ),
        "parameters_deferred_exact": (
            contract.get("parameter_contract") == EXPECTED_PARAMETERS
        ),
        "human_status_projection_exact": (
            contract.get("human_status_projection") == EXPECTED_HUMAN_STATUS
        ),
        "phase2_gate_exact": (
            contract.get("phase2_entry_gate") == EXPECTED_PHASE2_GATE
        ),
        "truth_flags_exact": (
            isinstance(truth, dict)
            and set(truth)
            == FALSE_TRUTH_FLAGS | {"taskpack_source_read_performed"}
            and truth.get("taskpack_source_read_performed") is True
            and all(truth.get(key) is False for key in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def build_stage042_phase1_report(
    project_root: Path | None = None,
) -> dict[str, Any]:
    project_root = (
        project_root or Path(__file__).resolve().parents[1]
    ).resolve()
    contract_path = project_root / CONTRACT_RELATIVE
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    checks = evaluate_contract(contract, project_root)
    truth = contract.get("truth_flags", {})
    return {
        "schema_version": "ids.stage042.automatic_lifecycle.phase1.report.v1",
        "stage": "STAGE-042",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE042-P1",
        "acceptance_id": "ACC-STAGE-042",
        "contract_state": contract.get("contract_state"),
        "next_gate": contract.get("next_gate"),
        "phase1_contract_valid": bool(checks) and all(checks.values()),
        "contract_checks": checks,
        **{key: truth.get(key, False) for key in sorted(FALSE_TRUTH_FLAGS)},
    }


def main() -> int:
    report = build_stage042_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["phase1_contract_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
