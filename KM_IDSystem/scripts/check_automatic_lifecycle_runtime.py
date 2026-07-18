#!/usr/bin/env python3
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Optional
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT_PATH = (
    PURSUE_ROOT
    / "automatic_lifecycle"
    / "stage042_automatic_lifecycle_runtime_contract.json"
)
STATE_INDEX_PATH = (
    PURSUE_ROOT / "job_state_model" / "stage037_job_state_model_index.json"
)
MODEL_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "formula_registry.yaml"
PARAMETER_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_SPEC = PROJECT_ROOT / "docs" / "governance" / "MODEL_SPEC.md"
PROJECT_GOVERNANCE = PROJECT_ROOT / "docs" / "governance" / "project.yaml"

POLICY_VERSION = "ids.automatic_lifecycle_policy.v0_1.stage042.p2"
CONTROL_INPUT_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md"
)
RESOURCE_OBSERVATION_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
    "stage040_backpressure_runtime_contract.json"
)
CLAIM_CANDIDATE_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE038_PHASE2_ASYNC_WORKER_QUEUE_SLICE.md"
)
LOCK_EVIDENCE_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md"
)
AUDIT_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md#Controlled-Evidence"
)

EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "execution_mode",
    "policy_contract_id",
    "contract_state",
    "next_gate",
    "source_binding",
    "phase1_predecessor_binding",
    "upstream_bindings",
    "policy",
    "request_contract",
    "decision_contract",
    "state_transition_contract",
    "idempotency_contract",
    "control_metadata_contract",
    "human_status_projection",
    "ownership_matrix",
    "registry_binding",
    "runtime_boundary",
    "rollback",
    "phase3_entry_gate",
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
        "STAGE-042_自动运行、暂停、恢复与关闭.md"
    ),
    "source_member_match_count": 1,
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
    "commit": "24972088d901d351ac6b59bdb704fea64121bfc9",
    "tree": "8a7f8d7746eb20034a30e09a9b037feb72246896",
    "parent": "f6b30f8a55d60f1b37b9d57ee55587149ad43876",
    "task_id": "IDS-V0_1-STAGE042-P1",
    "result": "PASS_LOCAL",
}
EXPECTED_UPSTREAM = {
    "phase1_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
            "stage042_automatic_lifecycle_contract.json"
        ),
        "sha256": (
            "5c3f7b4a446f14590bae4e6ab4b803d0b79c61e0b5a40de061adbe6c139980ba"
        ),
    },
    "phase1_checker": {
        "ref": "KM_IDSystem/scripts/check_automatic_lifecycle.py",
        "sha256": (
            "92fa435e88f3cd861dcde7d9a792021ee9d151d7d467203e746aed52ec9beb8a"
        ),
    },
    "phase1_boundary": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md"
        ),
        "sha256": (
            "60bdd35780b6e67c168fc17c4426c1e7bd08c69cb743b235a9743d81849e82d7"
        ),
    },
    "stage037_state_index": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": (
            "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3"
        ),
    },
    "stage038_queue_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
            "stage038_worker_queue_baseline_index.json"
        ),
        "sha256": (
            "68513591996a51fea90cd2ea863f42f910c0c3a45b70fd1611655bb6d95911ab"
        ),
    },
    "stage039_retry_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
            "stage039_retry_dead_letter_runtime_contract.json"
        ),
        "sha256": (
            "5fc9b49b0ede0fdbc87311f3280ffc69e8ec8e59f219b17a04a2ccae1e9124c0"
        ),
    },
    "stage040_backpressure_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
            "stage040_backpressure_runtime_contract.json"
        ),
        "sha256": (
            "2970ebd143030821d9a8b00e4fdb11342f8f82ef3bcf4d91717ba707b5054e2e"
        ),
    },
    "stage041_lock_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_runtime_contract.json"
        ),
        "sha256": (
            "80f87c789c6fc834b13eaec3d14d9444417ee7313ff8f88f6893bbda15e1f464"
        ),
    },
}
EXPECTED_PARAMETERS = {
    "lifecycle_tick_interval": 1,
    "resume_stability_window": 60,
    "checkpoint_wait_timeout": 30,
    "graceful_shutdown_timeout": 60,
    "cleanup_scan_interval": 300,
}
EXPECTED_PARAMETER_RELATIONSHIPS = {
    "lifecycle_tick_equals_stage041_acquisition_timeout": True,
    "resume_stability_equals_two_stage040_observation_ttls": True,
    "checkpoint_wait_equals_stage041_lease_duration": True,
    "graceful_shutdown_equals_two_stage041_lease_durations": True,
    "cleanup_scan_equals_five_stage040_api_windows": True,
}
REQUEST_ROOT_FIELDS = {
    "schema_version",
    "job_id",
    "expected_state",
    "expected_state_version",
    "lifecycle_action",
    "lifecycle_request_id",
    "policy_version",
    "reason_code",
    "audit_ref",
    "evidence",
}
EVIDENCE_FIELDS = {
    "input_refs",
    "resource_observation_refs",
    "observed_at_epoch_seconds",
    "evaluated_at_epoch_seconds",
    "resource_stability_started_at_epoch_seconds",
    "resource_stable_for_seconds",
    "owner_revalidated",
    "resource_gates_passed",
    "admission_gates_passed",
    "claim_candidate_ref",
    "pressure_signal",
    "active_claim_or_lock",
    "lock_evidence_ref",
    "lease_live",
    "fencing_token",
    "checkpoint_or_quarantine_complete",
    "checkpoint_ref",
    "checkpoint_wait_elapsed_seconds",
    "shutdown_elapsed_seconds",
    "cleanup_last_scan_at_epoch_seconds",
    "cleanup_candidate_ref",
    "cleanup_candidate_class",
}
ACTIONS = [
    "AUTO_START",
    "AUTO_PAUSE",
    "AUTO_RESUME",
    "SAFE_SHUTDOWN",
    "CLEANUP_CANDIDATE_SCAN",
]
EXPECTED_REASON_CODES = {
    "AUTO_START": "ELIGIBLE_CONTROL_START",
    "AUTO_PAUSE": "RESOURCE_PAUSE_REQUIRED",
    "AUTO_RESUME": "RESOURCE_STABILITY_REVALIDATED",
    "SAFE_SHUTDOWN": "ORDERLY_CONTROL_SHUTDOWN",
    "CLEANUP_CANDIDATE_SCAN": "CLEANUP_SCAN_DUE",
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
PRESSURE_SIGNALS = [
    "QUEUE_SOFT_PRESSURE",
    "QUEUE_HARD_CAPACITY",
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
    "JOB_TYPE_CONCURRENCY_LIMIT_REACHED",
    "SAME_SOURCE_CONFLICT",
]
MANDATORY_PRESSURE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
ELIGIBLE_CLEANUP_CLASSES = [
    "TEMP_STAGING_OUTPUT",
    "INCOMPLETE_DERIVATIVE_OUTPUT",
]
PROTECTED_ARTIFACT_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
ORDERED_SHUTDOWN_STEPS = [
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

EXPECTED_REQUEST_CONTRACT = {
    "schema_version": "ids.stage042.lifecycle_decision_request.v1",
    "required_root_fields": sorted(REQUEST_ROOT_FIELDS),
    "required_evidence_fields": sorted(EVIDENCE_FIELDS),
    "allowed_actions": ACTIONS,
    "control_job_id_prefix": "control:stage042:",
    "request_id_prefix": "lifecycle:stage042:",
    "expected_state_version_must_be_positive": True,
    "reason_code_by_action": EXPECTED_REASON_CODES,
    "unknown_field_action": "REJECT_CONTRACT",
    "malformed_request_action": "REQUIRE_MANUAL_REVIEW",
    "raw_payload_allowed": False,
    "absolute_path_allowed": False,
    "secret_material_allowed": False,
}
EXPECTED_DECISION_CONTRACT = {
    "AUTO_START": {
        "eligible_states": ["QUEUED"],
        "transition_candidates": [["QUEUED", "CLAIMED"], ["CLAIMED", "RUNNING"]],
        "required_guards": [
            "fresh_resource_observation",
            "resource_gates_passed",
            "admission_gates_passed",
            "claim_candidate_ref",
            "lock_evidence_ref",
            "lease_live",
            "fencing_token",
        ],
        "decision_action": "AUTO_START_CANDIDATE",
    },
    "AUTO_PAUSE": {
        "eligible_states": ["QUEUED", "CLAIMED", "RUNNING", "RETRY_WAIT"],
        "mandatory_pressure_signals": MANDATORY_PRESSURE_SIGNALS,
        "active_states": ["CLAIMED", "RUNNING"],
        "active_first_target": "PAUSE_REQUESTED",
        "checkpoint_or_quarantine_required": True,
        "retry_budget_consumed": False,
        "decision_action": "AUTO_PAUSE_CANDIDATE",
    },
    "AUTO_RESUME": {
        "eligible_states": ["PAUSED"],
        "transition_candidates": [["PAUSED", "QUEUED"]],
        "owner_revalidation_required": True,
        "resource_stability_required": True,
        "no_active_claim_or_lock_required": True,
        "fresh_admission_and_lock_cycle_required": True,
        "direct_resume_to_running_allowed": False,
        "decision_action": "AUTO_RESUME_CANDIDATE",
    },
    "SAFE_SHUTDOWN": {
        "eligible_states": [
            "CREATED",
            "QUEUED",
            "CLAIMED",
            "RUNNING",
            "PAUSE_REQUESTED",
            "PAUSED",
            "RETRY_WAIT",
        ],
        "active_states": ["CLAIMED", "RUNNING", "PAUSE_REQUESTED"],
        "checkpoint_or_quarantine_required_for_active": True,
        "matching_lock_evidence_required_for_active": True,
        "process_termination_allowed": False,
        "decision_action": "SAFE_SHUTDOWN_CANDIDATE",
    },
    "CLEANUP_CANDIDATE_SCAN": {
        "eligible_states": ["PAUSED"],
        "eligible_artifact_classes": ELIGIBLE_CLEANUP_CLASSES,
        "protected_artifact_classes": PROTECTED_ARTIFACT_CLASSES,
        "candidate_only": True,
        "delete_allowed": False,
        "runtime_owner": "STAGE-044",
        "decision_action": "CLEANUP_CANDIDATE_ONLY",
    },
}
EXPECTED_STATE_CONTRACT = {
    "state_model_version": "ids.job_state.v1",
    "terminal_states": TERMINAL_STATES,
    "terminal_state_mutation_allowed": False,
    "candidate_only": True,
    "state_mutation_allowed": False,
    "direct_queued_to_running_allowed": False,
    "direct_running_to_paused_allowed": False,
    "direct_paused_to_running_allowed": False,
    "fresh_admission_and_lock_cycle_after_resume_required": True,
}
EXPECTED_IDEMPOTENCY = {
    "request_key_formula": (
        "sha256(canonical_request_without_lifecycle_request_id)"
    ),
    "ledger_mode": "IN_MEMORY_DECISION_REPLAY_ONLY",
    "exact_replay_returns_original": True,
    "request_id_formula_enforced_for_new_requests": True,
    "same_request_id_changed_payload_action": (
        "REJECT_LIFECYCLE_REQUEST_CONFLICT"
    ),
    "persistent_ledger_allowed": False,
    "append_only_audit_required": True,
}
EXPECTED_METADATA = {
    "input_refs": [CONTROL_INPUT_REF],
    "input_refs_must_be_git_tracked": True,
    "resource_observation_refs_must_be_git_tracked": True,
    "raw_body_allowed": False,
    "output_refs": [],
    "checkpoint_ref_format": "checkpoint:sha256:<canonical-decision-digest>",
    "error_ref_format": "error:<safe-control-reason-code>",
    "audit_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md#Controlled-Evidence"
    ),
}
EXPECTED_HUMAN_STATUS = {
    "AUTO_START_CANDIDATE": {
        "label_zh": "可自动开始",
        "owner_action_zh": "等待受控执行器确认",
        "owner_attention_required": False,
    },
    "AUTO_PAUSE_CANDIDATE": {
        "label_zh": "等待安全暂停",
        "owner_action_zh": "等待 checkpoint 或隔离完成",
        "owner_attention_required": True,
    },
    "AUTO_RESUME_CANDIDATE": {
        "label_zh": "可进入恢复队列",
        "owner_action_zh": "等待重新准入与锁确认",
        "owner_attention_required": False,
    },
    "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION": {
        "label_zh": "等待复核后恢复",
        "owner_action_zh": "补齐负责人复核与稳定资源证据",
        "owner_attention_required": True,
    },
    "SAFE_SHUTDOWN_CANDIDATE": {
        "label_zh": "安全关闭中",
        "owner_action_zh": "等待受控执行器完成关闭",
        "owner_attention_required": True,
    },
    "CLEANUP_CANDIDATE_ONLY": {
        "label_zh": "待清理候选（不执行删除）",
        "owner_action_zh": "由 Stage 44 独立复核",
        "owner_attention_required": True,
    },
    "REJECT_TERMINAL_STATE_IMMUTABLE": {
        "label_zh": "任务已结束",
        "owner_action_zh": "如需重跑请新建关联任务",
        "owner_attention_required": True,
    },
    "REJECT_LIFECYCLE_REQUEST_CONFLICT": {
        "label_zh": "请求冲突",
        "owner_action_zh": "核对幂等键与请求内容",
        "owner_attention_required": True,
    },
    "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH": {
        "label_zh": "请求身份不一致",
        "owner_action_zh": "按规范请求内容重新计算请求 ID",
        "owner_attention_required": True,
    },
    "REQUIRE_MANUAL_REVIEW": {
        "label_zh": "需要人工处理",
        "owner_action_zh": "补齐有效控制证据",
        "owner_attention_required": True,
    },
}
EXPECTED_OWNERSHIP = {
    "queue_and_worker_transport": "STAGE-038",
    "retry_and_dead_letter_policy": "STAGE-039",
    "backpressure_observation_and_policy": "STAGE-040",
    "lock_lease_and_fencing_runtime": "STAGE-041",
    "automatic_lifecycle_decision_policy": "STAGE-042",
    "process_crash_recovery_runtime": "STAGE-043",
    "cleanup_execution_runtime": "STAGE-044",
}
EXPECTED_REGISTRY = {
    "model_id": "MOD-011",
    "formula_id": "FORM-011",
    "parameter_ids": [f"PARAM-{number:03d}" for number in range(72, 77)],
    "production_calibration_task_id": "TASK-OPME-B-001",
}
EXPECTED_RUNTIME_BOUNDARY = {
    "isolated_lifecycle_decision_runtime_allowed": True,
    "reference_only_control_metadata_allowed": True,
    "queue_runtime_allowed": False,
    "worker_runtime_allowed": False,
    "retry_scheduler_allowed": False,
    "backpressure_runtime_allowed": False,
    "production_lock_runtime_allowed": False,
    "process_crash_recovery_allowed": False,
    "cleanup_runtime_allowed": False,
    "delete_allowed": False,
    "database_allowed": False,
    "schema_change_allowed": False,
    "persistent_state_write_allowed": False,
    "runtime_output_write_allowed": False,
    "external_api_allowed": False,
    "raw_metadata_access_allowed": False,
    "ids_business_job_allowed": False,
    "fake_ids_business_data_allowed": False,
    "process_termination_allowed": False,
    "production_activation_allowed": False,
}
EXPECTED_ROLLBACK = {
    "trigger": "INVALID_CONTRACT_PARAMETER_REQUEST_EVIDENCE_OR_UPSTREAM_BINDING",
    "action": (
        "NO_AUTOMATIC_LIFECYCLE_REQUIRE_MANUAL_REVIEW_AND_"
        "REVERT_PHASE2_FILES_ONLY"
    ),
    "preserve_phase1": True,
    "preserve_stage037_stage041": True,
    "preserve_source_and_evidence": True,
    "github_action_allowed": False,
}
EXPECTED_PHASE3_GATE = {
    "entry_authorized": True,
    "required_task_id": "IDS-V0_1-STAGE042-P3",
    "required_gate": "IDS-STAGE042-P3-GATE",
    "separate_run_required": True,
    "required_work": [
        "validate duplicate request and stale evidence behavior",
        "validate resource pause and guarded resume scenarios",
        "validate worker crash remains Stage043-owned",
        "validate lock evidence prevents duplicate operations",
        "validate protected artifacts never enter cleanup execution",
    ],
}
TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "parameter_values_assigned",
    "isolated_lifecycle_decision_runtime_performed",
    "lifecycle_candidate_evaluation_performed",
    "automatic_start_candidate_evaluated",
    "automatic_pause_candidate_evaluated",
    "automatic_resume_candidate_evaluated",
    "safe_shutdown_candidate_evaluated",
    "cleanup_candidate_evaluated",
}
FALSE_TRUTH_FLAGS = {
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
    "persistent_decision_write_performed",
    "runtime_output_written",
    "external_api_call_performed",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _keys_exact(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _strict_int(value: Any, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _source_binding_valid(binding: Any) -> bool:
    if binding != EXPECTED_SOURCE:
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
                name for name in zf.namelist() if name == binding["source_member"]
            ]
            return (
                len(matches) == 1
                and hashlib.sha256(zf.read(matches[0])).hexdigest()
                == binding["source_member_sha256"]
            )
    except (OSError, KeyError, TypeError):
        return False


def _predecessor_valid(binding: Any) -> bool:
    if binding != EXPECTED_PREDECESSOR:
        return False
    try:
        observed = subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%H%n%T%n%P",
                binding["commit"],
            ],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
    except (OSError, subprocess.CalledProcessError, KeyError, TypeError):
        return False
    return observed == [binding["commit"], binding["tree"], binding["parent"]]


def _upstream_valid(bindings: Any) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    try:
        return all(
            _sha256(REPO_ROOT / item["ref"]) == item["sha256"]
            for item in bindings.values()
        )
    except (OSError, KeyError, TypeError):
        return False


def _repo_relative_ref(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.startswith("repo:KM_IDSystem/"):
        return None
    relative = value[len("repo:") :].split("#", 1)[0]
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return None
    if "IDS_MetaData" in value or "/Users/" in value:
        return None
    return relative


def _git_tracked(relative: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _refs_valid(values: Any, *, allow_empty: bool = False) -> bool:
    if not isinstance(values, list) or (not values and not allow_empty):
        return False
    relatives = [_repo_relative_ref(value) for value in values]
    return all(relative and _git_tracked(relative) for relative in relatives)


def _parameter_policy_valid(policy: Any) -> tuple[bool, bool, bool]:
    if not isinstance(policy, dict):
        return False, False, False
    parameters = policy.get("parameters")
    provenance = policy.get("parameter_provenance")
    parameters_valid = (
        parameters == EXPECTED_PARAMETERS
        and all(_strict_int(value, minimum=1) for value in parameters.values())
    )
    provenance_valid = (
        isinstance(provenance, dict)
        and set(provenance) == set(EXPECTED_PARAMETERS)
        and all(
            _keys_exact(
                item,
                {
                    "value",
                    "unit",
                    "source_refs",
                    "derivation",
                    "fact_level",
                    "policy_version",
                    "validation_evidence",
                    "rollback",
                },
            )
            and item["value"] == EXPECTED_PARAMETERS[name]
            and item["unit"] == "seconds"
            and isinstance(item["source_refs"], list)
            and bool(item["source_refs"])
            and all(
                isinstance(ref, str)
                and ref.startswith("KM_IDSystem/")
                and (REPO_ROOT / ref).is_file()
                for ref in item["source_refs"]
            )
            and isinstance(item["derivation"], str)
            and bool(item["derivation"])
            and item["fact_level"] == "PROPOSED"
            and item["policy_version"] == POLICY_VERSION
            and item["validation_evidence"]
            == (
                "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
                "test_stage042_automatic_lifecycle_runtime.py"
            )
            and item["rollback"] == "NO_AUTOMATIC_LIFECYCLE"
            for name, item in provenance.items()
        )
    )
    relationships_valid = (
        parameters_valid
        and policy.get("parameter_relationships")
        == EXPECTED_PARAMETER_RELATIONSHIPS
        and parameters["lifecycle_tick_interval"] == 1
        and parameters["resume_stability_window"] == 2 * 30
        and parameters["checkpoint_wait_timeout"] == 30
        and parameters["graceful_shutdown_timeout"] == 2 * 30
        and parameters["cleanup_scan_interval"] == 5 * 60
    )
    metadata_valid = (
        policy.get("policy_version") == POLICY_VERSION
        and policy.get("parameter_source")
        == "STAGE042_PHASE2_COMPOSED_REVIEWED_UPSTREAM_BOUNDARY"
        and isinstance(policy.get("selection_rationale"), str)
        and bool(policy.get("selection_rationale"))
        and policy.get("fact_level") == "PROPOSED"
        and policy.get("production_calibrated") is False
        and policy.get("production_calibration_required") is True
        and policy.get("production_calibration_task_id") == "TASK-OPME-B-001"
        and policy.get("rollback_policy")
        == "NO_AUTOMATIC_LIFECYCLE_REQUIRE_MANUAL_REVIEW"
    )
    return parameters_valid and metadata_valid, provenance_valid, relationships_valid


def _state_graph_valid(contract: Mapping[str, Any]) -> bool:
    if contract.get("state_transition_contract") != EXPECTED_STATE_CONTRACT:
        return False
    try:
        index = json.loads(STATE_INDEX_PATH.read_text(encoding="utf-8"))
        state_model = index["state_model"]
        allowed = {
            (source, target)
            for source, targets in state_model["allowed_transitions"].items()
            for target in targets
        }
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False
    used = {
        ("QUEUED", "CLAIMED"),
        ("CLAIMED", "RUNNING"),
        ("QUEUED", "PAUSED"),
        ("CLAIMED", "PAUSE_REQUESTED"),
        ("RUNNING", "PAUSE_REQUESTED"),
        ("PAUSE_REQUESTED", "PAUSED"),
        ("RETRY_WAIT", "PAUSED"),
        ("PAUSED", "QUEUED"),
        ("CREATED", "CANCELLED"),
        ("QUEUED", "CANCELLED"),
        ("PAUSE_REQUESTED", "CANCELLED"),
        ("PAUSED", "CANCELLED"),
        ("RETRY_WAIT", "CANCELLED"),
    }
    forbidden = {
        ("QUEUED", "RUNNING"),
        ("RUNNING", "PAUSED"),
        ("PAUSED", "RUNNING"),
    }
    return (
        state_model.get("job_states") == JOB_STATES
        and state_model.get("terminal_states") == TERMINAL_STATES
        and used.issubset(allowed)
        and not allowed.intersection(forbidden)
    )


def _registry_valid(binding: Any) -> bool:
    if binding != EXPECTED_REGISTRY:
        return False
    try:
        model = MODEL_REGISTRY.read_text(encoding="utf-8")
        formula = FORMULA_REGISTRY.read_text(encoding="utf-8")
        spec = MODEL_SPEC.read_text(encoding="utf-8")
        project = PROJECT_GOVERNANCE.read_text(encoding="utf-8")
        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return False
    selected = {
        row.get("parameter_id"): row
        for row in rows
        if row.get("parameter_id") in EXPECTED_REGISTRY["parameter_ids"]
    }
    return (
        'assumption_id: "ASM-007"' in model
        and 'model_id: "MOD-011"' in model
        and 'formula_id: "FORM-011"' in formula
        and 'model_id: "MOD-011"' in project
        and 'formula_id: "FORM-011"' in project
        and set(selected) == set(EXPECTED_REGISTRY["parameter_ids"])
        and all(
            selected[parameter_id].get("model_id") == "MOD-011"
            and selected[parameter_id].get("formula_id") == "FORM-011"
            and selected[parameter_id].get("symbol") == symbol
            and selected[parameter_id].get("active_value") == str(value)
            and selected[parameter_id].get("status") == "planned"
            and selected[parameter_id].get("fact_level") == "PROPOSED"
            and selected[parameter_id].get("unknown_task_ids")
            == "TASK-OPME-B-001"
            for parameter_id, (symbol, value) in zip(
                EXPECTED_REGISTRY["parameter_ids"], EXPECTED_PARAMETERS.items()
            )
        )
        and all(
            line in spec
            for line in (
                "- model_count: 11",
                "- formula_count: 11",
                "- parameter_count: 76",
                "- active_model_count: 7",
                "- active_formula_count: 7",
                "- active_parameter_count: 49",
            )
        )
    )


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def evaluate_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, dict):
        contract = {}
    policy_valid, provenance_valid, relationships_valid = _parameter_policy_valid(
        contract.get("policy")
    )
    truth = contract.get("truth_flags")
    return {
        "root_shape_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage042.automatic_lifecycle.phase2.v1"
            and contract.get("stage") == "STAGE-042"
            and contract.get("phase") == "Phase 2"
            and contract.get("task_id") == "IDS-V0_1-STAGE042-P2"
            and contract.get("acceptance_id") == "ACC-STAGE-042"
            and contract.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_LIFECYCLE_DECISION_SLICE"
            and contract.get("policy_contract_id") == POLICY_VERSION
            and contract.get("contract_state")
            == "PHASE2_ISOLATED_LIFECYCLE_DECISION_SLICE_ENABLED_PRODUCTION_DISABLED"
            and contract.get("next_gate") == "IDS-STAGE042-P3-GATE"
        ),
        "source_binding_exact": _source_binding_valid(contract.get("source_binding")),
        "phase1_predecessor_exact": _predecessor_valid(
            contract.get("phase1_predecessor_binding")
        ),
        "upstream_bindings_exact": _upstream_valid(
            contract.get("upstream_bindings")
        ),
        "parameters_exact_and_bounded": policy_valid,
        "parameter_provenance_complete": provenance_valid,
        "parameter_relationships_exact": relationships_valid,
        "request_contract_exact": (
            isinstance(contract.get("request_contract"), dict)
            and {
                **contract["request_contract"],
                "required_root_fields": sorted(
                    contract["request_contract"].get("required_root_fields", [])
                ),
                "required_evidence_fields": sorted(
                    contract["request_contract"].get(
                        "required_evidence_fields", []
                    )
                ),
            }
            == EXPECTED_REQUEST_CONTRACT
        ),
        "decision_contract_exact": (
            contract.get("decision_contract") == EXPECTED_DECISION_CONTRACT
        ),
        "state_graph_exact": _state_graph_valid(contract),
        "idempotency_exact": (
            contract.get("idempotency_contract") == EXPECTED_IDEMPOTENCY
        ),
        "control_metadata_exact": (
            contract.get("control_metadata_contract") == EXPECTED_METADATA
        ),
        "human_status_exact": (
            contract.get("human_status_projection") == EXPECTED_HUMAN_STATUS
        ),
        "ownership_exact": contract.get("ownership_matrix") == EXPECTED_OWNERSHIP,
        "registry_binding_exact": _registry_valid(contract.get("registry_binding")),
        "runtime_boundary_exact": (
            contract.get("runtime_boundary") == EXPECTED_RUNTIME_BOUNDARY
        ),
        "rollback_exact": contract.get("rollback") == EXPECTED_ROLLBACK,
        "phase3_gate_exact": (
            contract.get("phase3_entry_gate") == EXPECTED_PHASE3_GATE
        ),
        "truth_flags_exact": (
            isinstance(truth, dict)
            and set(truth) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
            and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }


def _checkpoint(seed: Any) -> str:
    return f"checkpoint:sha256:{_canonical_digest(seed)}"


def _cleanup_candidate(seed: Any) -> str:
    return f"cleanup-candidate:sha256:{_canonical_digest(seed)}"


def derive_lifecycle_request_id(request: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(request))
    payload.pop("lifecycle_request_id", None)
    return f"lifecycle:stage042:{_canonical_digest(payload)}"


def build_control_request(
    lifecycle_action: str,
    **overrides: Any,
) -> dict[str, Any]:
    default_state = {
        "AUTO_START": "QUEUED",
        "AUTO_PAUSE": "RUNNING",
        "AUTO_RESUME": "PAUSED",
        "SAFE_SHUTDOWN": "RUNNING",
        "CLEANUP_CANDIDATE_SCAN": "PAUSED",
    }.get(lifecycle_action, "CREATED")
    expected_state = overrides.pop("expected_state", default_state)
    evaluated_at = overrides.get("evaluated_at_epoch_seconds", 1000)
    stable_for = overrides.get(
        "resource_stable_for_seconds",
        EXPECTED_PARAMETERS["resume_stability_window"],
    )
    if (
        isinstance(evaluated_at, int)
        and not isinstance(evaluated_at, bool)
        and isinstance(stable_for, int)
        and not isinstance(stable_for, bool)
    ):
        default_stability_started_at = evaluated_at - stable_for
    else:
        default_stability_started_at = 940
    control_digest = _canonical_digest(CONTROL_INPUT_REF)
    checkpoint_ref = _checkpoint([CONTROL_INPUT_REF, lifecycle_action, expected_state])
    evidence: dict[str, Any] = {
        "input_refs": [CONTROL_INPUT_REF],
        "resource_observation_refs": [RESOURCE_OBSERVATION_REF],
        "observed_at_epoch_seconds": 1000,
        "evaluated_at_epoch_seconds": 1000,
        "resource_stability_started_at_epoch_seconds": (
            default_stability_started_at
        ),
        "resource_stable_for_seconds": EXPECTED_PARAMETERS[
            "resume_stability_window"
        ],
        "owner_revalidated": True,
        "resource_gates_passed": True,
        "admission_gates_passed": True,
        "claim_candidate_ref": CLAIM_CANDIDATE_REF,
        "pressure_signal": (
            "EXTERNAL_DRIVE_OFFLINE" if lifecycle_action == "AUTO_PAUSE" else None
        ),
        "active_claim_or_lock": expected_state
        in {"CLAIMED", "RUNNING", "PAUSE_REQUESTED"},
        "lock_evidence_ref": LOCK_EVIDENCE_REF,
        "lease_live": True,
        "fencing_token": 1,
        "checkpoint_or_quarantine_complete": True,
        "checkpoint_ref": checkpoint_ref,
        "checkpoint_wait_elapsed_seconds": 0,
        "shutdown_elapsed_seconds": 0,
        "cleanup_last_scan_at_epoch_seconds": 700,
        "cleanup_candidate_ref": _cleanup_candidate(
            [CONTROL_INPUT_REF, "TEMP_STAGING_OUTPUT"]
        ),
        "cleanup_candidate_class": "TEMP_STAGING_OUTPUT",
    }
    root_fields = {
        "job_id",
        "expected_state_version",
        "policy_version",
        "reason_code",
        "audit_ref",
        "lifecycle_request_id",
    }
    root_overrides = {
        key: overrides.pop(key) for key in list(overrides) if key in root_fields
    }
    evidence.update(overrides)
    request: dict[str, Any] = {
        "schema_version": "ids.stage042.lifecycle_decision_request.v1",
        "job_id": f"control:stage042:{control_digest[:32]}",
        "expected_state": expected_state,
        "expected_state_version": 1,
        "lifecycle_action": lifecycle_action,
        "lifecycle_request_id": "",
        "policy_version": POLICY_VERSION,
        "reason_code": {
            **EXPECTED_REASON_CODES,
        }.get(lifecycle_action, "UNKNOWN_LIFECYCLE_ACTION"),
        "audit_ref": AUDIT_REF,
        "evidence": evidence,
    }
    request.update(root_overrides)
    if not request.get("lifecycle_request_id"):
        request["lifecycle_request_id"] = derive_lifecycle_request_id(request)
    return request


def validate_control_request(request: Any) -> bool:
    if not _keys_exact(request, REQUEST_ROOT_FIELDS):
        return False
    evidence = request.get("evidence")
    if not _keys_exact(evidence, EVIDENCE_FIELDS):
        return False
    try:
        serialized = json.dumps(request, ensure_ascii=False)
    except (TypeError, ValueError):
        return False
    if any(token in serialized for token in ("IDS_MetaData", "/Users/", "raw_payload")):
        return False
    if request.get("schema_version") != "ids.stage042.lifecycle_decision_request.v1":
        return False
    if not isinstance(request.get("job_id"), str) or not request["job_id"].startswith(
        "control:stage042:"
    ):
        return False
    if request.get("expected_state") not in JOB_STATES:
        return False
    if not _strict_int(request.get("expected_state_version"), minimum=1):
        return False
    if request.get("lifecycle_action") not in ACTIONS:
        return False
    if not isinstance(request.get("lifecycle_request_id"), str) or not re.fullmatch(
        r"lifecycle:stage042:[0-9a-f]{64}", request["lifecycle_request_id"]
    ):
        return False
    if request.get("policy_version") != POLICY_VERSION:
        return False
    if request.get("reason_code") != EXPECTED_REASON_CODES.get(
        request.get("lifecycle_action")
    ):
        return False
    if not _refs_valid([request.get("audit_ref")]):
        return False
    if not _refs_valid(evidence.get("input_refs")) or not _refs_valid(
        evidence.get("resource_observation_refs")
    ):
        return False
    for key in (
        "observed_at_epoch_seconds",
        "evaluated_at_epoch_seconds",
        "resource_stability_started_at_epoch_seconds",
        "resource_stable_for_seconds",
        "checkpoint_wait_elapsed_seconds",
        "shutdown_elapsed_seconds",
    ):
        if not _strict_int(evidence.get(key)):
            return False
    for key in (
        "owner_revalidated",
        "resource_gates_passed",
        "admission_gates_passed",
        "active_claim_or_lock",
        "lease_live",
        "checkpoint_or_quarantine_complete",
    ):
        if not isinstance(evidence.get(key), bool):
            return False
    for key in ("claim_candidate_ref", "lock_evidence_ref"):
        value = evidence.get(key)
        if value is not None and not _refs_valid([value]):
            return False
    pressure = evidence.get("pressure_signal")
    if pressure is not None and pressure not in PRESSURE_SIGNALS:
        return False
    fencing = evidence.get("fencing_token")
    if fencing is not None and not _strict_int(fencing, minimum=1):
        return False
    checkpoint = evidence.get("checkpoint_ref")
    if checkpoint is not None and (
        not isinstance(checkpoint, str)
        or not re.fullmatch(r"checkpoint:sha256:[0-9a-f]{64}", checkpoint)
    ):
        return False
    cleanup_last = evidence.get("cleanup_last_scan_at_epoch_seconds")
    if cleanup_last is not None and not _strict_int(cleanup_last):
        return False
    cleanup_ref = evidence.get("cleanup_candidate_ref")
    if cleanup_ref is not None and (
        not isinstance(cleanup_ref, str)
        or not re.fullmatch(r"cleanup-candidate:sha256:[0-9a-f]{64}", cleanup_ref)
    ):
        return False
    cleanup_class = evidence.get("cleanup_candidate_class")
    if cleanup_class is not None and cleanup_class not in (
        ELIGIBLE_CLEANUP_CLASSES + PROTECTED_ARTIFACT_CLASSES
    ):
        return False
    stability_started_at = evidence[
        "resource_stability_started_at_epoch_seconds"
    ]
    observed_at = evidence["observed_at_epoch_seconds"]
    evaluated_at = evidence["evaluated_at_epoch_seconds"]
    if request["lifecycle_action"] == "AUTO_RESUME":
        return (
            stability_started_at <= observed_at <= evaluated_at
            and evidence["resource_stable_for_seconds"]
            == evaluated_at - stability_started_at
        )
    return evaluated_at >= observed_at


class IsolatedLifecycleDecisionLedger:
    def __init__(self) -> None:
        self._records: dict[str, tuple[str, dict[str, Any]]] = {}

    @property
    def record_count(self) -> int:
        return len(self._records)

    def lookup(
        self, request_id: str, digest: str
    ) -> tuple[str, Optional[dict[str, Any]]]:
        record = self._records.get(request_id)
        if record is None:
            return "NEW", None
        recorded_digest, result = record
        if recorded_digest == digest:
            return "REPLAY", copy.deepcopy(result)
        return "CONFLICT", None

    def store(self, request_id: str, digest: str, result: dict[str, Any]) -> None:
        self._records[request_id] = (digest, copy.deepcopy(result))


def _safe_result(
    request: Any,
    decision_action: str,
    transition_candidates: list[list[str]],
    *,
    error_ref: Optional[str] = None,
    ordered_shutdown_steps: Optional[list[str]] = None,
) -> dict[str, Any]:
    valid = isinstance(request, dict) and validate_control_request(request)
    evidence = request["evidence"] if valid else {}
    request_id = (
        request["lifecycle_request_id"] if valid else "lifecycle:stage042:invalid"
    )
    decision_seed = [request_id, decision_action, transition_candidates]
    return {
        "schema_version": "ids.stage042.lifecycle_decision_result.v1",
        "decision_id": f"decision:stage042:{_canonical_digest(decision_seed)}",
        "lifecycle_request_id": request_id,
        "job_id": request["job_id"] if valid else "control:stage042:invalid",
        "expected_state": request["expected_state"] if valid else "UNKNOWN",
        "expected_state_version": (
            request["expected_state_version"] if valid else None
        ),
        "lifecycle_action": request["lifecycle_action"] if valid else "UNKNOWN",
        "policy_version": request["policy_version"] if valid else POLICY_VERSION,
        "decision_action": decision_action,
        "reason_code": request["reason_code"] if valid else "INVALID_LIFECYCLE_REQUEST",
        "transition_candidates": transition_candidates,
        "fresh_admission_and_lock_cycle_required": decision_action
        in {"AUTO_START_CANDIDATE", "AUTO_RESUME_CANDIDATE"},
        "retry_budget_consumed": False,
        "ordered_shutdown_steps": ordered_shutdown_steps or [],
        "cleanup_candidate_only": decision_action == "CLEANUP_CANDIDATE_ONLY",
        "human_status": copy.deepcopy(
            EXPECTED_HUMAN_STATUS.get(
                decision_action, EXPECTED_HUMAN_STATUS["REQUIRE_MANUAL_REVIEW"]
            )
        ),
        "input_refs": copy.deepcopy(evidence.get("input_refs", [])),
        "output_refs": [],
        "error_ref": error_ref,
        "checkpoint_ref": evidence.get("checkpoint_ref"),
        "audit_ref": request["audit_ref"] if valid else AUDIT_REF,
        "cleanup_candidate_ref": evidence.get("cleanup_candidate_ref"),
        "state_mutation_performed": False,
        "queue_write_performed": False,
        "worker_action_performed": False,
        "retry_scheduler_performed": False,
        "lock_mutation_performed": False,
        "process_termination_performed": False,
        "cleanup_runtime_performed": False,
        "protected_ref_delete_performed": False,
        "database_write_performed": False,
        "runtime_output_written": False,
        "production_activation_performed": False,
    }


def _fresh(evidence: Mapping[str, Any]) -> bool:
    age = evidence["evaluated_at_epoch_seconds"] - evidence[
        "observed_at_epoch_seconds"
    ]
    return 0 <= age <= 30


def evaluate_lifecycle(
    request: Any,
    *,
    contract: Optional[dict[str, Any]] = None,
    ledger: Optional[IsolatedLifecycleDecisionLedger] = None,
) -> dict[str, Any]:
    contract_value = contract if contract is not None else load_contract()
    if not all(evaluate_contract(contract_value).values()):
        return _safe_result(
            request,
            "REQUIRE_MANUAL_REVIEW",
            [],
            error_ref="error:INVALID_LIFECYCLE_CONTRACT",
        )
    if not validate_control_request(request):
        return _safe_result(
            request,
            "REQUIRE_MANUAL_REVIEW",
            [],
            error_ref="error:INVALID_LIFECYCLE_REQUEST",
        )
    digest_payload = copy.deepcopy(request)
    digest_payload.pop("lifecycle_request_id", None)
    request_digest = _canonical_digest(digest_payload)
    canonical_request_id = f"lifecycle:stage042:{request_digest}"
    if ledger is not None:
        status, existing = ledger.lookup(
            request["lifecycle_request_id"], request_digest
        )
        if status == "CONFLICT":
            return _safe_result(
                request,
                "REJECT_LIFECYCLE_REQUEST_CONFLICT",
                [],
                error_ref="error:LIFECYCLE_REQUEST_CONFLICT",
            )
        if request["lifecycle_request_id"] != canonical_request_id:
            return _safe_result(
                request,
                "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH",
                [],
                error_ref="error:LIFECYCLE_REQUEST_ID_MISMATCH",
            )
        if status == "REPLAY" and existing is not None:
            return existing
    elif request["lifecycle_request_id"] != canonical_request_id:
        return _safe_result(
            request,
            "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH",
            [],
            error_ref="error:LIFECYCLE_REQUEST_ID_MISMATCH",
        )

    state = request["expected_state"]
    action = request["lifecycle_action"]
    evidence = request["evidence"]
    if state in TERMINAL_STATES:
        result = _safe_result(
            request,
            "REJECT_TERMINAL_STATE_IMMUTABLE",
            [],
            error_ref="error:TERMINAL_STATE_IMMUTABLE",
        )
    elif action == "AUTO_START":
        guards = (
            state == "QUEUED"
            and _fresh(evidence)
            and evidence["resource_gates_passed"]
            and evidence["admission_gates_passed"]
            and isinstance(evidence["claim_candidate_ref"], str)
            and isinstance(evidence["lock_evidence_ref"], str)
            and evidence["lease_live"]
            and _strict_int(evidence["fencing_token"], minimum=1)
        )
        result = _safe_result(
            request,
            "AUTO_START_CANDIDATE" if guards else "REQUIRE_MANUAL_REVIEW",
            [["QUEUED", "CLAIMED"], ["CLAIMED", "RUNNING"]] if guards else [],
            error_ref=None if guards else "error:START_GUARD_INCOMPLETE",
        )
    elif action == "AUTO_PAUSE":
        active = state in {"CLAIMED", "RUNNING"}
        base = state in {"QUEUED", "CLAIMED", "RUNNING", "RETRY_WAIT"} and (
            evidence["pressure_signal"] in PRESSURE_SIGNALS
        )
        if active:
            guards = (
                base
                and evidence["active_claim_or_lock"]
                and evidence["lease_live"]
                and _strict_int(evidence["fencing_token"], minimum=1)
                and isinstance(evidence["lock_evidence_ref"], str)
                and evidence["checkpoint_or_quarantine_complete"]
                and evidence["checkpoint_wait_elapsed_seconds"]
                <= EXPECTED_PARAMETERS["checkpoint_wait_timeout"]
            )
            transitions = (
                [[state, "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "PAUSED"]]
                if guards
                else []
            )
        else:
            guards = base and not evidence["active_claim_or_lock"]
            transitions = [[state, "PAUSED"]] if guards else []
        result = _safe_result(
            request,
            "AUTO_PAUSE_CANDIDATE" if guards else "REQUIRE_MANUAL_REVIEW",
            transitions,
            error_ref=None if guards else "error:PAUSE_GUARD_INCOMPLETE",
        )
    elif action == "AUTO_RESUME":
        guards = (
            state == "PAUSED"
            and _fresh(evidence)
            and evidence["owner_revalidated"]
            and evidence["resource_gates_passed"]
            and evidence["resource_stable_for_seconds"]
            >= EXPECTED_PARAMETERS["resume_stability_window"]
            and evidence["resource_stable_for_seconds"]
            == evidence["evaluated_at_epoch_seconds"]
            - evidence["resource_stability_started_at_epoch_seconds"]
            and not evidence["active_claim_or_lock"]
        )
        result = _safe_result(
            request,
            "AUTO_RESUME_CANDIDATE"
            if guards
            else "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION",
            [["PAUSED", "QUEUED"]] if guards else [],
            error_ref=None
            if guards
            else "error:OWNER_OR_RESOURCE_REVALIDATION_REQUIRED",
        )
    elif action == "SAFE_SHUTDOWN":
        active = state in {"CLAIMED", "RUNNING", "PAUSE_REQUESTED"}
        guards = (
            state
            in {
                "CREATED",
                "QUEUED",
                "CLAIMED",
                "RUNNING",
                "PAUSE_REQUESTED",
                "PAUSED",
                "RETRY_WAIT",
            }
            and evidence["shutdown_elapsed_seconds"]
            <= EXPECTED_PARAMETERS["graceful_shutdown_timeout"]
        )
        if active:
            guards = (
                guards
                and evidence["active_claim_or_lock"]
                and evidence["checkpoint_or_quarantine_complete"]
                and evidence["checkpoint_wait_elapsed_seconds"]
                <= EXPECTED_PARAMETERS["checkpoint_wait_timeout"]
                and isinstance(evidence["lock_evidence_ref"], str)
                and evidence["lease_live"]
                and _strict_int(evidence["fencing_token"], minimum=1)
            )
        if state in {"CLAIMED", "RUNNING"}:
            transitions = (
                [[state, "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "CANCELLED"]]
                if guards
                else []
            )
        elif state == "PAUSE_REQUESTED":
            transitions = [["PAUSE_REQUESTED", "CANCELLED"]] if guards else []
        else:
            transitions = [[state, "CANCELLED"]] if guards else []
        result = _safe_result(
            request,
            "SAFE_SHUTDOWN_CANDIDATE" if guards else "REQUIRE_MANUAL_REVIEW",
            transitions,
            error_ref=None if guards else "error:SHUTDOWN_GUARD_OR_TIMEOUT",
            ordered_shutdown_steps=ORDERED_SHUTDOWN_STEPS if guards else [],
        )
    elif action == "CLEANUP_CANDIDATE_SCAN":
        last_scan = evidence["cleanup_last_scan_at_epoch_seconds"]
        elapsed = (
            evidence["evaluated_at_epoch_seconds"] - last_scan
            if isinstance(last_scan, int) and not isinstance(last_scan, bool)
            else -1
        )
        guards = (
            state == "PAUSED"
            and elapsed >= EXPECTED_PARAMETERS["cleanup_scan_interval"]
            and evidence["cleanup_candidate_class"] in ELIGIBLE_CLEANUP_CLASSES
            and isinstance(evidence["cleanup_candidate_ref"], str)
            and not evidence["active_claim_or_lock"]
        )
        result = _safe_result(
            request,
            "CLEANUP_CANDIDATE_ONLY" if guards else "REQUIRE_MANUAL_REVIEW",
            [],
            error_ref=None if guards else "error:CLEANUP_CANDIDATE_NOT_ELIGIBLE",
        )
    else:
        result = _safe_result(
            request,
            "REQUIRE_MANUAL_REVIEW",
            [],
            error_ref="error:UNKNOWN_LIFECYCLE_ACTION",
        )
    if ledger is not None and result["decision_action"] not in {
        "REJECT_LIFECYCLE_REQUEST_CONFLICT",
        "REQUIRE_MANUAL_REVIEW",
    }:
        ledger.store(request["lifecycle_request_id"], request_digest, result)
    return result


def build_stage042_phase2_report() -> dict[str, Any]:
    contract = load_contract()
    contract_checks = evaluate_contract(contract)
    ledger = IsolatedLifecycleDecisionLedger()
    requests = {
        "automatic_start": build_control_request("AUTO_START"),
        "automatic_pause": build_control_request("AUTO_PAUSE"),
        "automatic_resume": build_control_request("AUTO_RESUME"),
        "safe_shutdown": build_control_request("SAFE_SHUTDOWN"),
        "cleanup_candidate": build_control_request("CLEANUP_CANDIDATE_SCAN"),
    }
    results = {
        name: evaluate_lifecycle(request, contract=contract, ledger=ledger)
        for name, request in requests.items()
    }
    replay = evaluate_lifecycle(
        copy.deepcopy(requests["automatic_start"]),
        contract=contract,
        ledger=ledger,
    )
    conflict = copy.deepcopy(requests["automatic_start"])
    conflict["expected_state_version"] += 1
    conflict_result = evaluate_lifecycle(
        conflict, contract=contract, ledger=ledger
    )
    terminal = build_control_request("AUTO_RESUME", expected_state="SUCCEEDED")
    blocked_resume = build_control_request("AUTO_RESUME", owner_revalidated=False)
    protected_cleanup = build_control_request(
        "CLEANUP_CANDIDATE_SCAN", cleanup_candidate_class="FACT_SOURCE"
    )
    timed_out_shutdown = build_control_request(
        "SAFE_SHUTDOWN",
        shutdown_elapsed_seconds=EXPECTED_PARAMETERS["graceful_shutdown_timeout"]
        + 1,
    )
    forged_request_id = build_control_request("AUTO_START")
    forged_request_id["lifecycle_request_id"] = (
        f"lifecycle:stage042:{'f' * 64}"
    )
    zero_state_version = build_control_request(
        "AUTO_START", expected_state_version=0
    )
    mismatched_reason = build_control_request(
        "AUTO_START", reason_code="CLEANUP_SCAN_DUE"
    )
    inconsistent_stability = build_control_request("AUTO_RESUME")
    inconsistent_stability["evidence"][
        "resource_stability_started_at_epoch_seconds"
    ] = 1000
    inconsistent_stability["lifecycle_request_id"] = (
        derive_lifecycle_request_id(inconsistent_stability)
    )
    running_cleanup = build_control_request(
        "CLEANUP_CANDIDATE_SCAN",
        expected_state="RUNNING",
        active_claim_or_lock=False,
    )
    expected_actions = {
        "automatic_start": "AUTO_START_CANDIDATE",
        "automatic_pause": "AUTO_PAUSE_CANDIDATE",
        "automatic_resume": "AUTO_RESUME_CANDIDATE",
        "safe_shutdown": "SAFE_SHUTDOWN_CANDIDATE",
        "cleanup_candidate": "CLEANUP_CANDIDATE_ONLY",
    }
    decision_checks = {
        "candidate_actions_exact": all(
            results[name]["decision_action"] == action
            for name, action in expected_actions.items()
        ),
        "exact_replay_idempotent": replay == results["automatic_start"],
        "request_conflict_rejected": (
            conflict_result["decision_action"]
            == "REJECT_LIFECYCLE_REQUEST_CONFLICT"
        ),
        "canonical_request_id_enforced": (
            evaluate_lifecycle(forged_request_id, contract=contract)[
                "decision_action"
            ]
            == "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH"
        ),
        "positive_state_version_enforced": (
            evaluate_lifecycle(zero_state_version, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "reason_code_action_binding_enforced": (
            evaluate_lifecycle(mismatched_reason, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "resume_stability_temporal_evidence_enforced": (
            evaluate_lifecycle(inconsistent_stability, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "cleanup_paused_state_enforced": (
            evaluate_lifecycle(running_cleanup, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "terminal_history_immutable": (
            evaluate_lifecycle(terminal, contract=contract)["decision_action"]
            == "REJECT_TERMINAL_STATE_IMMUTABLE"
        ),
        "resume_owner_revalidation_enforced": (
            evaluate_lifecycle(blocked_resume, contract=contract)[
                "decision_action"
            ]
            == "AUTO_RESUME_BLOCKED_OWNER_REVALIDATION"
        ),
        "protected_cleanup_denied": (
            evaluate_lifecycle(protected_cleanup, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "shutdown_timeout_fails_closed": (
            evaluate_lifecycle(timed_out_shutdown, contract=contract)[
                "decision_action"
            ]
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "reference_only_inputs_tracked": all(
            _refs_valid(result["input_refs"])
            for result in results.values()
        ),
        "outputs_errors_and_checkpoints_truthful": all(
            result["output_refs"] == []
            and result["error_ref"] is None
            and isinstance(result["checkpoint_ref"], str)
            and result["checkpoint_ref"].startswith("checkpoint:sha256:")
            for result in results.values()
        ),
        "no_state_or_runtime_side_effects": all(
            not result[flag]
            for result in results.values()
            for flag in (
                "state_mutation_performed",
                "queue_write_performed",
                "worker_action_performed",
                "retry_scheduler_performed",
                "lock_mutation_performed",
                "process_termination_performed",
                "cleanup_runtime_performed",
                "protected_ref_delete_performed",
                "database_write_performed",
                "runtime_output_written",
                "production_activation_performed",
            )
        ),
        "resume_never_targets_running": (
            results["automatic_resume"]["transition_candidates"]
            == [["PAUSED", "QUEUED"]]
        ),
        "active_pause_uses_pause_requested": (
            results["automatic_pause"]["transition_candidates"]
            == [["RUNNING", "PAUSE_REQUESTED"], ["PAUSE_REQUESTED", "PAUSED"]]
        ),
        "cleanup_remains_candidate_only": (
            results["cleanup_candidate"]["cleanup_candidate_only"] is True
            and results["cleanup_candidate"]["transition_candidates"] == []
        ),
    }
    truth = contract.get("truth_flags", {}) if isinstance(contract, dict) else {}
    valid = bool(contract_checks) and all(contract_checks.values()) and all(
        decision_checks.values()
    )
    return {
        "schema_version": "ids.stage042.automatic_lifecycle.phase2.report.v1",
        "stage": "STAGE-042",
        "phase": "Phase 2",
        "task_id": "IDS-V0_1-STAGE042-P2",
        "acceptance_id": "ACC-STAGE-042",
        "execution_mode": contract.get("execution_mode"),
        "policy_version": contract.get("policy_contract_id"),
        "contract_state": contract.get("contract_state"),
        "parameter_fact_level": contract.get("policy", {}).get("fact_level"),
        "production_calibrated": contract.get("policy", {}).get(
            "production_calibrated"
        ),
        "production_calibration_task_id": contract.get("policy", {}).get(
            "production_calibration_task_id"
        ),
        "parameter_values_assigned": truth.get(
            "parameter_values_assigned", False
        ),
        "control_job_id": requests["automatic_start"]["job_id"],
        "phase2_slice_valid": valid,
        "contract_checks": contract_checks,
        "decision_checks": decision_checks,
        "scenario_results": results,
        "phase3_entry_authorized": bool(valid),
        "next_gate": (
            "IDS-STAGE042-P3-GATE" if valid else "IDS-STAGE042-P2-GATE"
        ),
        **{
            name: truth.get(name, False)
            for name in sorted(TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS)
        },
    }


def main() -> int:
    report = build_stage042_phase2_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["phase2_slice_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
