#!/usr/bin/env python3
"""Validate and exercise the isolated STAGE-043 Phase 2 recovery decision slice."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
import re
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
    / "worker_crash_recovery"
    / "stage043_worker_crash_recovery_runtime_contract.json"
)
PARAMETER_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = PROJECT_ROOT / "docs" / "governance" / "formula_registry.yaml"
MODEL_SPEC = PROJECT_ROOT / "docs" / "governance" / "MODEL_SPEC.md"

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
        "IDS_v0_1_Final_Chinese_Revised/stages/STAGE-043_Worker崩溃恢复.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b"
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
    "commit": "d4b5ec1ef9bff3d2390869b4fd2998bd17d2c671",
    "tree": "6d7af7a50506df15f229e35977143ead0f5b3f06",
    "parent": "ba248f66ce993a726cb12547ae1c772ab1228bfa",
    "task_id": "IDS-V0_1-STAGE043-P1",
    "result": "PASS_LOCAL",
}

EXPECTED_UPSTREAM = {
    "phase1_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_contract.json"
        ),
        "sha256": "78cb110cd10f4068b72ceba01752d2771378c7d07b569797bd0efa88f6826ef4",
    },
    "phase1_checker": {
        "ref": "KM_IDSystem/scripts/check_worker_crash_recovery.py",
        "sha256": "ea15a378441e4ce9932daedb093523080936f2fd1b09323c486e5ae48f458f3f",
    },
    "phase1_boundary": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md"
        ),
        "sha256": "50baa3eda8d40317456e566da908b4cb8a69c0096b1725087ac165debf6af23e",
    },
    "stage037_state_index": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    },
    "stage039_retry_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
            "stage039_retry_dead_letter_runtime_contract.json"
        ),
        "sha256": "5fc9b49b0ede0fdbc87311f3280ffc69e8ec8e59f219b17a04a2ccae1e9124c0",
    },
    "stage040_backpressure_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
            "stage040_backpressure_runtime_contract.json"
        ),
        "sha256": "2970ebd143030821d9a8b00e4fdb11342f8f82ef3bcf4d91717ba707b5054e2e",
    },
    "stage041_lock_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_runtime_contract.json"
        ),
        "sha256": "80f87c789c6fc834b13eaec3d14d9444417ee7313ff8f88f6893bbda15e1f464",
    },
    "stage042_lifecycle_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
            "stage042_automatic_lifecycle_runtime_contract.json"
        ),
        "sha256": "f24283a0ab934082b0ceb48c6ca1597ca17d1c6cca6a939e2653fb00ede83e49",
    },
}

EXPECTED_PARAMETERS = {
    "crash_detection_interval": 1,
    "heartbeat_stale_window": 30,
    "lease_expiry_grace": 5,
    "recovery_retry_backoff": 30,
    "checkpoint_validation_timeout": 30,
}
EXPECTED_PARAMETER_RELATIONSHIPS = {
    "crash_detection_equals_stage042_tick": True,
    "heartbeat_stale_equals_stage041_lease": True,
    "lease_grace_equals_stage041_expiry_grace": True,
    "recovery_backoff_equals_stage039_max_backoff": True,
    "checkpoint_timeout_equals_stage042_checkpoint_wait": True,
}
EXPECTED_PARAMETER_SOURCES = {
    "crash_detection_interval": [
        EXPECTED_UPSTREAM["stage042_lifecycle_runtime"]["ref"],
        EXPECTED_UPSTREAM["stage041_lock_runtime"]["ref"],
    ],
    "heartbeat_stale_window": [EXPECTED_UPSTREAM["stage041_lock_runtime"]["ref"]],
    "lease_expiry_grace": [EXPECTED_UPSTREAM["stage041_lock_runtime"]["ref"]],
    "recovery_retry_backoff": [EXPECTED_UPSTREAM["stage039_retry_runtime"]["ref"]],
    "checkpoint_validation_timeout": [
        EXPECTED_UPSTREAM["stage042_lifecycle_runtime"]["ref"],
        EXPECTED_UPSTREAM["stage041_lock_runtime"]["ref"],
    ],
}
POLICY_VERSION = "ids.worker_crash_recovery_policy.v0_1.stage043.p2"
VALIDATION_REF = (
    "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
    "test_stage043_worker_crash_recovery_runtime.py"
)

REQUEST_ROOT_FIELDS = [
    "schema_version",
    "job_id",
    "attempt_id",
    "worker_instance_id",
    "worker_generation",
    "observed_state",
    "observed_state_version",
    "crash_incident_id",
    "recovery_request_key",
    "policy_version",
    "recovery_intent",
    "reason_code",
    "audit_ref",
    "evidence",
]
EVIDENCE_FIELDS = [
    "input_refs",
    "crash_event_ref",
    "crash_detected_at_epoch_seconds",
    "last_heartbeat_observed_at_epoch_seconds",
    "lease_expires_at_epoch_seconds",
    "evaluated_at_epoch_seconds",
    "state_version_current",
    "persistent_state_available",
    "lost_worker_generation_confirmed",
    "lease_owner_ref",
    "lock_key",
    "fencing_token",
    "lost_worker_fenced",
    "active_lock_or_claim_conflict",
    "checkpoint_ref",
    "checkpoint_integrity_valid",
    "checkpoint_idempotency_valid",
    "checkpoint_validation_elapsed_seconds",
    "owner_revalidated",
    "resource_gates_passed",
    "resource_pressure_signal",
    "fresh_admission_claim_lock_cycle_ref",
    "stage039_policy_eligible",
    "retry_budget_available",
    "replay_safe",
    "recovery_retry_wait_elapsed_seconds",
    "error_ref",
    "permanent_failure_recorded",
    "legal_state_edge_available",
    "quarantine_ref",
    "writer_quiescence_evidence_ref",
]
INTENTS = [
    "CHECKPOINT_RESUME",
    "STAGE039_RETRY",
    "SAFE_FAILURE",
    "RESOURCE_PAUSE",
]
KEY_FIELDS = [
    "job_id",
    "attempt_id",
    "worker_generation",
    "observed_state_version",
    "crash_incident_id",
]
REASON_CODES = {
    "CHECKPOINT_RESUME": "CHECKPOINT_CONTINUATION_REVALIDATION",
    "STAGE039_RETRY": "RETRY_POLICY_REVALIDATION",
    "SAFE_FAILURE": "PERMANENT_FAILURE_RECORDED",
    "RESOURCE_PAUSE": "RESOURCE_GATE_BLOCKED",
}
ERROR_REFS_BY_INTENT = {
    "CHECKPOINT_RESUME": [
        "error:WORKER_PROCESS_LOST",
        "error:ISOLATED_WORKER_PROCESS_EXIT_73",
    ],
    "STAGE039_RETRY": [
        "error:TRANSIENT_DEPENDENCY_UNAVAILABLE",
        "error:TRANSIENT_OPERATION_TIMEOUT",
    ],
    "SAFE_FAILURE": [
        "error:INVALID_CONTROL_METADATA",
        "error:UNSUPPORTED_CONTROL_OPERATION",
    ],
    "RESOURCE_PAUSE": ["error:WORKER_PROCESS_LOST"],
}
EVIDENCE_IDENTITY_BINDINGS = {
    "lease_owner_ref_must_equal_worker_instance_id": True,
    "checkpoint_ref_formula": (
        "checkpoint:sha256(canonical_json(kind,recovery_request_key))"
    ),
    "quarantine_ref_formula": (
        "quarantine:sha256(canonical_json(kind,recovery_request_key))"
    ),
}
EXPECTED_REQUEST_CONTRACT = {
    "schema_version": "ids.stage043.recovery_decision_request.v1",
    "required_root_fields": REQUEST_ROOT_FIELDS,
    "required_evidence_fields": EVIDENCE_FIELDS,
    "allowed_intents": INTENTS,
    "control_job_id_prefix": "control:stage043:",
    "recovery_request_key_fields": KEY_FIELDS,
    "reason_code_by_intent": REASON_CODES,
    "error_ref_allowlist_by_intent": ERROR_REFS_BY_INTENT,
    "evidence_identity_bindings": EVIDENCE_IDENTITY_BINDINGS,
    "observed_state_version_must_be_positive": True,
    "worker_generation_must_be_positive": True,
    "crash_detection_temporal_consistency_required": True,
    "resource_pressure_consistency_required": True,
    "unknown_field_action": "REJECT_CONTRACT",
    "malformed_request_action": "REQUIRE_MANUAL_REVIEW",
    "raw_payload_allowed": False,
    "absolute_path_allowed": False,
    "secret_material_allowed": False,
}

ACTIVE_STATES = ["CLAIMED", "RUNNING", "PAUSE_REQUESTED"]
TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
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
PRESSURE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
EXPECTED_DECISION_CONTRACT = {
    "CHECKPOINT_RESUME": {
        "eligible_states": ACTIVE_STATES,
        "transition_candidates": [
            ["ACTIVE_STATE", "RETRY_WAIT"],
            ["RETRY_WAIT", "QUEUED"],
            ["QUEUED", "CLAIMED"],
            ["CLAIMED", "RUNNING"],
        ],
        "required_guards": [
            "crash_proven",
            "persistent_state_available",
            "state_version_current",
            "lost_worker_generation_confirmed",
            "lost_worker_fenced",
            "no_active_lock_or_claim_conflict",
            "checkpoint_integrity_valid",
            "checkpoint_idempotency_valid",
            "checkpoint_validation_within_timeout",
            "owner_revalidated",
            "resource_gates_passed",
            "fresh_admission_claim_lock_cycle_ref",
        ],
        "decision_action": "CHECKPOINT_RESUME_CANDIDATE",
    },
    "STAGE039_RETRY": {
        "eligible_states": ACTIVE_STATES,
        "transition_candidates": [["ACTIVE_STATE", "RETRY_WAIT"]],
        "required_guards": [
            "crash_proven",
            "persistent_state_available",
            "state_version_current",
            "lost_worker_fenced",
            "stage039_policy_eligible",
            "retry_budget_available",
            "replay_safe",
            "error_ref",
            "resource_gates_passed",
            "recovery_backoff_elapsed",
        ],
        "runtime_owner": "STAGE-039",
        "decision_action": "STAGE039_RETRY_CANDIDATE",
    },
    "SAFE_FAILURE": {
        "eligible_states": ["RUNNING"],
        "transition_candidates": [["RUNNING", "FAILED"]],
        "required_guards": [
            "crash_proven",
            "persistent_state_available",
            "state_version_current",
            "lost_worker_fenced",
            "permanent_failure_recorded",
            "error_ref",
            "legal_state_edge_available",
        ],
        "decision_action": "SAFE_FAILURE_CANDIDATE",
    },
    "RESOURCE_PAUSE": {
        "eligible_states": ACTIVE_STATES,
        "mandatory_pressure_signals": PRESSURE_SIGNALS,
        "transition_candidates": [
            ["ACTIVE_STATE", "RETRY_WAIT"],
            ["RETRY_WAIT", "PAUSED"],
        ],
        "owner_revalidation_required_after_resource_recovery": True,
        "automatic_resume_allowed": False,
        "decision_action": "RESOURCE_PAUSE_CANDIDATE",
    },
}
EXPECTED_STATE_CONTRACT = {
    "state_model_version": "ids.job_state.v1",
    "job_states": JOB_STATES,
    "terminal_states": TERMINAL_STATES,
    "active_execution_states": ACTIVE_STATES,
    "candidate_only": True,
    "state_mutation_allowed": False,
    "terminal_history_reopen_allowed": False,
    "direct_active_to_queued_allowed": False,
    "direct_running_to_running_allowed": False,
    "in_memory_state_restoration_allowed": False,
    "fresh_admission_claim_lock_cycle_required": True,
}
EXPECTED_IDEMPOTENCY = {
    "request_key_formula": (
        "sha256(canonical_json(job_id,attempt_id,worker_generation,"
        "observed_state_version,crash_incident_id))"
    ),
    "ledger_mode": "IN_MEMORY_DECISION_REPLAY_ONLY",
    "one_incident_one_decision": True,
    "exact_replay_returns_original": True,
    "request_key_formula_enforced_for_new_requests": True,
    "same_request_key_changed_payload_action": "RECOVERY_REQUEST_CONFLICT",
    "persistent_ledger_allowed": False,
    "append_only_audit_required": True,
}
INPUT_REFS = [
    "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md"
]
AUDIT_REF = (
    "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md#Controlled-Evidence"
)
EXPECTED_METADATA = {
    "input_refs": INPUT_REFS,
    "input_refs_must_be_git_tracked": True,
    "raw_body_allowed": False,
    "output_refs": [],
    "checkpoint_ref_format": (
        "checkpoint:sha256:<canonical-kind-and-recovery-request-key-digest>"
    ),
    "quarantine_ref_format": (
        "quarantine:sha256:<canonical-kind-and-recovery-request-key-digest>"
    ),
    "error_ref_format": "error:<safe-control-reason-code>",
    "audit_ref": AUDIT_REF,
}
EXPECTED_HUMAN_STATUS = {
    "CHECKPOINT_RESUME_CANDIDATE": {
        "label_zh": "检查点续作候选已就绪",
        "owner_action_zh": "等待重新准入、领取、锁与栅栏确认",
        "owner_attention_required": True,
    },
    "STAGE039_RETRY_CANDIDATE": {
        "label_zh": "等待受控重试",
        "owner_action_zh": "由 Stage 39 复核策略与重试预算",
        "owner_attention_required": True,
    },
    "SAFE_FAILURE_CANDIDATE": {
        "label_zh": "等待安全失败确认",
        "owner_action_zh": "核对永久错误与审计证据",
        "owner_attention_required": True,
    },
    "RESOURCE_PAUSE_CANDIDATE": {
        "label_zh": "资源条件暂停",
        "owner_action_zh": "恢复资源后仍需负责人重新确认",
        "owner_attention_required": True,
    },
    "REQUIRE_MANUAL_REVIEW": {
        "label_zh": "需要人工复核",
        "owner_action_zh": "补齐当前、一致、可审计的崩溃与恢复证据",
        "owner_attention_required": True,
    },
}
EXPECTED_OWNERSHIP = {
    "queue_and_worker_transport": "STAGE-038",
    "retry_and_dead_letter_policy": "STAGE-039",
    "backpressure_observation_and_pause": "STAGE-040",
    "lock_lease_and_fencing_runtime": "STAGE-041",
    "automatic_lifecycle_policy": "STAGE-042",
    "process_crash_recovery_candidate_policy": "STAGE-043",
    "cleanup_execution_runtime": "STAGE-044",
}
EXPECTED_REGISTRY = {
    "model_id": "MOD-012",
    "formula_id": "FORM-012",
    "parameter_ids": [
        "PARAM-077",
        "PARAM-078",
        "PARAM-079",
        "PARAM-080",
        "PARAM-081",
    ],
    "production_calibration_task_id": "TASK-OPME-B-001",
}
CLEANUP_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
PROTECTED_CLASSES = [
    "FACT_SOURCE",
    "MANIFEST",
    "EVIDENCE_LEDGER",
    "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
EXPECTED_RUNTIME_BOUNDARY = {
    "isolated_recovery_decision_runtime_allowed": True,
    "reference_only_control_metadata_allowed": True,
    "process_probe_allowed": False,
    "crash_injection_allowed": False,
    "process_crash_recovery_allowed": False,
    "process_termination_allowed": False,
    "worker_restart_allowed": False,
    "state_mutation_allowed": False,
    "queue_runtime_allowed": False,
    "worker_runtime_allowed": False,
    "retry_scheduler_allowed": False,
    "backpressure_runtime_allowed": False,
    "production_lock_runtime_allowed": False,
    "checkpoint_resume_allowed": False,
    "cleanup_candidate_classes": CLEANUP_CLASSES,
    "protected_artifact_classes": PROTECTED_CLASSES,
    "cleanup_execution_owner": "STAGE-044",
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
    "production_activation_allowed": False,
}
EXPECTED_ROLLBACK = {
    "trigger": "INVALID_CONTRACT_PARAMETER_REQUEST_EVIDENCE_OR_UPSTREAM_BINDING",
    "action": (
        "NO_AUTOMATIC_CRASH_RECOVERY_REQUIRE_MANUAL_REVIEW_AND_"
        "REVERT_PHASE2_FILES_ONLY"
    ),
    "preserve_phase1": True,
    "preserve_stage037_stage042": True,
    "preserve_source_and_evidence": True,
    "github_action_allowed": False,
}
EXPECTED_PHASE3_GATE = {
    "entry_authorized": True,
    "required_task_id": "IDS-V0_1-STAGE043-P3",
    "required_gate": "IDS-STAGE043-P3-GATE",
    "separate_run_required": True,
    "required_work": [
        "validate duplicate and changed recovery requests",
        "validate stale and conflicting crash evidence",
        "validate mandatory resource pause boundaries",
        "validate lock and fencing prevent duplicate processing",
        "validate protected artifacts never enter cleanup execution",
    ],
}
EXPECTED_TRUTH_FLAGS = {
    "taskpack_source_read_performed": True,
    "parameter_values_assigned": True,
    "isolated_recovery_decision_runtime_performed": True,
    "recovery_candidate_evaluation_performed": True,
    "checkpoint_resume_candidate_evaluated": True,
    "stage039_retry_candidate_evaluated": True,
    "safe_failure_candidate_evaluated": True,
    "resource_pause_candidate_evaluated": True,
    "successful_recovery_observed": False,
    "ids_business_source_read_performed": False,
    "raw_metadata_content_accessed": False,
    "fake_ids_business_data_used": False,
    "real_ids_business_job_created": False,
    "process_probe_performed": False,
    "crash_injected": False,
    "process_crash_recovery_performed": False,
    "process_termination_performed": False,
    "worker_restart_performed": False,
    "state_transition_performed": False,
    "checkpoint_resume_performed": False,
    "queue_runtime_performed": False,
    "worker_runtime_performed": False,
    "retry_scheduler_performed": False,
    "backpressure_runtime_performed": False,
    "production_lock_runtime_performed": False,
    "automatic_lifecycle_runtime_performed": False,
    "cleanup_runtime_performed": False,
    "protected_ref_delete_performed": False,
    "persistent_state_write_performed": False,
    "database_connection_performed": False,
    "schema_change_performed": False,
    "runtime_output_written": False,
    "external_api_call_performed": False,
    "production_runtime_activation_performed": False,
    "whole_stage_review_performed": False,
    "batch_review_performed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}

BOOL_EVIDENCE_FIELDS = {
    "state_version_current",
    "persistent_state_available",
    "lost_worker_generation_confirmed",
    "lost_worker_fenced",
    "active_lock_or_claim_conflict",
    "checkpoint_integrity_valid",
    "checkpoint_idempotency_valid",
    "owner_revalidated",
    "resource_gates_passed",
    "stage039_policy_eligible",
    "retry_budget_available",
    "replay_safe",
    "permanent_failure_recorded",
    "legal_state_edge_available",
}
TIME_EVIDENCE_FIELDS = {
    "crash_detected_at_epoch_seconds",
    "last_heartbeat_observed_at_epoch_seconds",
    "lease_expires_at_epoch_seconds",
    "evaluated_at_epoch_seconds",
    "checkpoint_validation_elapsed_seconds",
    "recovery_retry_wait_elapsed_seconds",
}
SAFE_REF_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
DIGEST_REF_PATTERN = re.compile(r"^(checkpoint|quarantine):sha256:[0-9a-f]{64}$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _strict_int(value: Any, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _git_tracked(relative: str) -> bool:
    if not isinstance(relative, str) or not relative.startswith("KM_IDSystem/"):
        return False
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        return False
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _source_binding_valid(binding: Any) -> bool:
    if binding != EXPECTED_SOURCE:
        return False
    try:
        archive = Path(EXPECTED_SOURCE["source_archive_path"])
        if _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]:
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


def _predecessor_valid(binding: Any) -> bool:
    if binding != EXPECTED_PREDECESSOR:
        return False
    completed = subprocess.run(
        [
            "git",
            "show",
            "-s",
            "--format=%H%n%T%n%P",
            EXPECTED_PREDECESSOR["commit"],
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.splitlines() == [
        EXPECTED_PREDECESSOR["commit"],
        EXPECTED_PREDECESSOR["tree"],
        EXPECTED_PREDECESSOR["parent"],
    ]


def _upstream_valid(bindings: Any) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    try:
        return all(
            _sha256(REPO_ROOT / item["ref"]) == item["sha256"]
            for item in EXPECTED_UPSTREAM.values()
        )
    except OSError:
        return False


def _policy_valid(policy: Any) -> bool:
    if not isinstance(policy, dict):
        return False
    expected_keys = {
        "policy_version",
        "parameters",
        "parameter_provenance",
        "parameter_relationships",
        "parameter_source",
        "selection_rationale",
        "fact_level",
        "production_calibrated",
        "production_calibration_required",
        "production_calibration_task_id",
        "rollback_policy",
    }
    if set(policy) != expected_keys:
        return False
    if (
        policy.get("policy_version") != POLICY_VERSION
        or policy.get("parameters") != EXPECTED_PARAMETERS
        or policy.get("parameter_relationships")
        != EXPECTED_PARAMETER_RELATIONSHIPS
        or policy.get("parameter_source")
        != "STAGE043_PHASE2_COMPOSED_REVIEWED_UPSTREAM_BOUNDARY"
        or not isinstance(policy.get("selection_rationale"), str)
        or not policy["selection_rationale"]
        or policy.get("fact_level") != "PROPOSED"
        or policy.get("production_calibrated") is not False
        or policy.get("production_calibration_required") is not True
        or policy.get("production_calibration_task_id") != "TASK-OPME-B-001"
        or policy.get("rollback_policy")
        != "NO_AUTOMATIC_CRASH_RECOVERY_REQUIRE_MANUAL_REVIEW"
    ):
        return False
    provenance = policy.get("parameter_provenance")
    if not isinstance(provenance, dict) or set(provenance) != set(EXPECTED_PARAMETERS):
        return False
    for name, expected_value in EXPECTED_PARAMETERS.items():
        item = provenance.get(name)
        if not isinstance(item, dict) or set(item) != {
            "value",
            "unit",
            "source_refs",
            "derivation",
            "fact_level",
            "policy_version",
            "validation_evidence",
            "rollback",
        }:
            return False
        if (
            item.get("value") != expected_value
            or item.get("unit") != "seconds"
            or item.get("source_refs") != EXPECTED_PARAMETER_SOURCES[name]
            or not isinstance(item.get("derivation"), str)
            or not item["derivation"]
            or item.get("fact_level") != "PROPOSED"
            or item.get("policy_version") != POLICY_VERSION
            or item.get("validation_evidence") != VALIDATION_REF
            or item.get("rollback") != "NO_AUTOMATIC_CRASH_RECOVERY"
        ):
            return False
    return True


def _registry_valid(binding: Any) -> bool:
    if binding != EXPECTED_REGISTRY:
        return False
    try:
        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = {
            row.get("parameter_id"): row
            for row in rows
            if row.get("parameter_id") in EXPECTED_REGISTRY["parameter_ids"]
        }
        if set(selected) != set(EXPECTED_REGISTRY["parameter_ids"]):
            return False
        for parameter_id, (symbol, value) in zip(
            EXPECTED_REGISTRY["parameter_ids"], EXPECTED_PARAMETERS.items()
        ):
            row = selected[parameter_id]
            if not (
                row.get("model_id") == "MOD-012"
                and row.get("formula_id") == "FORM-012"
                and row.get("symbol") == symbol
                and row.get("active_value") == str(value)
                and row.get("status") == "planned"
                and row.get("fact_level") == "PROPOSED"
                and row.get("unknown_task_ids") == "TASK-OPME-B-001"
                and row.get("parameter_version") == POLICY_VERSION
            ):
                return False
        model_text = MODEL_REGISTRY.read_text(encoding="utf-8")
        formula_text = FORMULA_REGISTRY.read_text(encoding="utf-8")
        spec_text = MODEL_SPEC.read_text(encoding="utf-8")
        return all(
            marker in model_text
            for marker in ('assumption_id: "ASM-008"', 'model_id: "MOD-012"')
        ) and 'formula_id: "FORM-012"' in formula_text and all(
            marker in spec_text
            for marker in (
                "- active_model_count: 7",
                "- active_formula_count: 7",
                "- active_parameter_count: 49",
            )
        ) and any(
            all(marker in spec_text for marker in count_markers)
            for count_markers in (
                ("- model_count: 12", "- formula_count: 12", "- parameter_count: 81"),
                ("- model_count: 13", "- formula_count: 13", "- parameter_count: 86"),
            )
        )
    except (OSError, csv.Error):
        return False


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def evaluate_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, dict):
        contract = {}
    return {
        "root_shape_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version")
            == "ids.stage043.worker_crash_recovery.phase2.v1"
            and contract.get("stage") == "STAGE-043"
            and contract.get("phase") == "Phase 2"
            and contract.get("task_id") == "IDS-V0_1-STAGE043-P2"
            and contract.get("acceptance_id") == "ACC-STAGE-043"
            and contract.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CRASH_RECOVERY_DECISION_SLICE"
            and contract.get("policy_contract_id") == POLICY_VERSION
            and contract.get("contract_state")
            == "PHASE2_ISOLATED_RECOVERY_DECISION_SLICE_ENABLED_PRODUCTION_DISABLED"
            and contract.get("next_gate") == "IDS-STAGE043-P3-GATE"
        ),
        "source_binding_valid": _source_binding_valid(contract.get("source_binding")),
        "phase1_predecessor_valid": _predecessor_valid(
            contract.get("phase1_predecessor_binding")
        ),
        "upstream_bindings_valid": _upstream_valid(contract.get("upstream_bindings")),
        "parameter_policy_valid": _policy_valid(contract.get("policy")),
        "request_contract_exact": contract.get("request_contract")
        == EXPECTED_REQUEST_CONTRACT,
        "decision_contract_exact": contract.get("decision_contract")
        == EXPECTED_DECISION_CONTRACT,
        "state_contract_exact": contract.get("state_transition_contract")
        == EXPECTED_STATE_CONTRACT,
        "idempotency_exact": contract.get("idempotency_contract")
        == EXPECTED_IDEMPOTENCY,
        "control_metadata_exact": contract.get("control_metadata_contract")
        == EXPECTED_METADATA,
        "human_status_exact": contract.get("human_status_projection")
        == EXPECTED_HUMAN_STATUS,
        "ownership_exact": contract.get("ownership_matrix") == EXPECTED_OWNERSHIP,
        "registry_binding_valid": _registry_valid(contract.get("registry_binding")),
        "runtime_boundary_exact": contract.get("runtime_boundary")
        == EXPECTED_RUNTIME_BOUNDARY,
        "rollback_exact": contract.get("rollback") == EXPECTED_ROLLBACK,
        "phase3_gate_exact": contract.get("phase3_entry_gate")
        == EXPECTED_PHASE3_GATE,
        "truth_flags_exact": contract.get("truth_flags") == EXPECTED_TRUTH_FLAGS,
    }


def derive_recovery_request_key(request: Mapping[str, Any]) -> str:
    key_payload = {field: request.get(field) for field in KEY_FIELDS}
    return _canonical_digest(key_payload)


def _digest_ref(prefix: str, seed: Any) -> str:
    return f"{prefix}:sha256:{_canonical_digest(seed)}"


def _bound_evidence_ref(prefix: str, request_key: str) -> str:
    return _digest_ref(
        prefix,
        {"kind": prefix, "recovery_request_key": request_key},
    )


def build_recovery_request(
    recovery_intent: str,
    **overrides: Any,
) -> dict[str, Any]:
    root_fields = {
        "job_id",
        "attempt_id",
        "worker_instance_id",
        "worker_generation",
        "observed_state",
        "observed_state_version",
        "crash_incident_id",
        "reason_code",
        "audit_ref",
        "policy_version",
    }
    root_overrides = {
        key: value for key, value in overrides.items() if key in root_fields
    }
    evidence_overrides = {
        key: value for key, value in overrides.items() if key not in root_fields
    }
    default_error_ref = ERROR_REFS_BY_INTENT.get(
        recovery_intent, ["error:UNKNOWN_RECOVERY_INTENT"]
    )[0]
    evidence = {
        "input_refs": list(INPUT_REFS),
        "crash_event_ref": "event:stage043:worker-process-lost-001",
        "crash_detected_at_epoch_seconds": 1000,
        "last_heartbeat_observed_at_epoch_seconds": 970,
        "lease_expires_at_epoch_seconds": 995,
        "evaluated_at_epoch_seconds": 1000,
        "state_version_current": True,
        "persistent_state_available": True,
        "lost_worker_generation_confirmed": True,
        "lease_owner_ref": "control:stage043:worker-lost-001",
        "lock_key": "lock:SOURCE_PIPELINE:control-stage043",
        "fencing_token": 9,
        "lost_worker_fenced": True,
        "active_lock_or_claim_conflict": False,
        "checkpoint_ref": "",
        "checkpoint_integrity_valid": True,
        "checkpoint_idempotency_valid": True,
        "checkpoint_validation_elapsed_seconds": 30,
        "owner_revalidated": True,
        "resource_gates_passed": True,
        "resource_pressure_signal": "NONE",
        "fresh_admission_claim_lock_cycle_ref": "candidate:stage043:fresh-cycle-001",
        "stage039_policy_eligible": True,
        "retry_budget_available": True,
        "replay_safe": True,
        "recovery_retry_wait_elapsed_seconds": 30,
        "error_ref": default_error_ref,
        "permanent_failure_recorded": recovery_intent == "SAFE_FAILURE",
        "legal_state_edge_available": True,
        "quarantine_ref": "",
        "writer_quiescence_evidence_ref": "evidence:stage043:writer-quiescent-001",
    }
    if recovery_intent == "RESOURCE_PAUSE":
        evidence["resource_gates_passed"] = False
        evidence["resource_pressure_signal"] = "EXTERNAL_DRIVE_OFFLINE"
    evidence.update(evidence_overrides)
    request = {
        "schema_version": "ids.stage043.recovery_decision_request.v1",
        "job_id": "control:stage043:job-001",
        "attempt_id": "control:stage043:attempt-001",
        "worker_instance_id": "control:stage043:worker-lost-001",
        "worker_generation": 7,
        "observed_state": "RUNNING",
        "observed_state_version": 11,
        "crash_incident_id": "control:stage043:incident-001",
        "recovery_request_key": "",
        "policy_version": POLICY_VERSION,
        "recovery_intent": recovery_intent,
        "reason_code": REASON_CODES.get(recovery_intent, "UNKNOWN_RECOVERY_INTENT"),
        "audit_ref": AUDIT_REF,
        "evidence": evidence,
    }
    request.update(root_overrides)
    request["recovery_request_key"] = derive_recovery_request_key(request)
    if "lease_owner_ref" not in evidence_overrides:
        request["evidence"]["lease_owner_ref"] = request["worker_instance_id"]
    if "checkpoint_ref" not in evidence_overrides:
        request["evidence"]["checkpoint_ref"] = _bound_evidence_ref(
            "checkpoint", request["recovery_request_key"]
        )
    if "quarantine_ref" not in evidence_overrides:
        request["evidence"]["quarantine_ref"] = _bound_evidence_ref(
            "quarantine", request["recovery_request_key"]
        )
    return request


def _safe_scalar_ref(value: Any, *, prefixes: tuple[str, ...]) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and ".." not in value
        and value.startswith(prefixes)
        and SAFE_REF_PATTERN.fullmatch(value) is not None
    )


def validate_recovery_request(request: Any) -> bool:
    if not isinstance(request, dict) or set(request) != set(REQUEST_ROOT_FIELDS):
        return False
    evidence = request.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_FIELDS):
        return False
    if (
        request.get("schema_version")
        != "ids.stage043.recovery_decision_request.v1"
        or not _safe_scalar_ref(
            request.get("job_id"), prefixes=("control:stage043:",)
        )
        or not _safe_scalar_ref(request.get("attempt_id"), prefixes=("control:stage043:",))
        or not _safe_scalar_ref(
            request.get("worker_instance_id"), prefixes=("control:stage043:",)
        )
        or not _strict_int(request.get("worker_generation"), minimum=1)
        or request.get("observed_state") not in JOB_STATES
        or not _strict_int(request.get("observed_state_version"), minimum=1)
        or not _safe_scalar_ref(
            request.get("crash_incident_id"), prefixes=("control:stage043:",)
        )
        or request.get("policy_version") != POLICY_VERSION
        or request.get("recovery_intent") not in INTENTS
        or request.get("reason_code")
        != REASON_CODES.get(request.get("recovery_intent"))
        or request.get("audit_ref") != AUDIT_REF
        or not isinstance(request.get("recovery_request_key"), str)
        or HEX64_PATTERN.fullmatch(request["recovery_request_key"]) is None
        or request["recovery_request_key"] != derive_recovery_request_key(request)
    ):
        return False
    input_refs = evidence.get("input_refs")
    if input_refs != INPUT_REFS or not all(_git_tracked(ref) for ref in input_refs):
        return False
    if any(type(evidence.get(field)) is not bool for field in BOOL_EVIDENCE_FIELDS):
        return False
    if any(
        not _strict_int(evidence.get(field), minimum=0)
        for field in TIME_EVIDENCE_FIELDS
    ):
        return False
    if not _strict_int(evidence.get("fencing_token"), minimum=1):
        return False
    if evidence.get("resource_pressure_signal") not in ["NONE", *PRESSURE_SIGNALS]:
        return False
    if not _safe_scalar_ref(evidence.get("crash_event_ref"), prefixes=("event:",)):
        return False
    if not _safe_scalar_ref(evidence.get("lease_owner_ref"), prefixes=("control:",)):
        return False
    if evidence.get("lease_owner_ref") != request.get("worker_instance_id"):
        return False
    if not _safe_scalar_ref(evidence.get("lock_key"), prefixes=("lock:",)):
        return False
    if not _safe_scalar_ref(
        evidence.get("fresh_admission_claim_lock_cycle_ref"),
        prefixes=("candidate:",),
    ):
        return False
    if not _safe_scalar_ref(evidence.get("error_ref"), prefixes=("error:",)):
        return False
    if evidence.get("error_ref") not in ERROR_REFS_BY_INTENT.get(
        request.get("recovery_intent"), []
    ):
        return False
    if not _safe_scalar_ref(
        evidence.get("writer_quiescence_evidence_ref"), prefixes=("evidence:",)
    ):
        return False
    if not isinstance(evidence.get("checkpoint_ref"), str) or not DIGEST_REF_PATTERN.fullmatch(
        evidence["checkpoint_ref"]
    ):
        return False
    if not isinstance(evidence.get("quarantine_ref"), str) or not DIGEST_REF_PATTERN.fullmatch(
        evidence["quarantine_ref"]
    ):
        return False
    if evidence["checkpoint_ref"] != _bound_evidence_ref(
        "checkpoint", request["recovery_request_key"]
    ):
        return False
    if evidence["quarantine_ref"] != _bound_evidence_ref(
        "quarantine", request["recovery_request_key"]
    ):
        return False
    resource_consistent = (
        evidence["resource_gates_passed"] is True
        and evidence["resource_pressure_signal"] == "NONE"
    ) or (
        evidence["resource_gates_passed"] is False
        and evidence["resource_pressure_signal"] in PRESSURE_SIGNALS
    )
    if not resource_consistent:
        return False
    serialized = json.dumps(request, ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    if "raw_payload" in lowered or "api_key" in lowered or "password" in lowered:
        return False
    return True


class InMemoryRecoveryDecisionLedger:
    """Process-local replay ledger; it performs no persistent write."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[str, dict[str, Any]]] = {}

    def lookup(
        self, request_key: str, payload_digest: str
    ) -> tuple[str, Optional[dict[str, Any]]]:
        existing = self._records.get(request_key)
        if existing is None:
            return "NEW", None
        existing_digest, existing_result = existing
        if existing_digest == payload_digest:
            return "REPLAY", copy.deepcopy(existing_result)
        return "CONFLICT", None

    def record(
        self, request_key: str, payload_digest: str, result: dict[str, Any]
    ) -> None:
        self._records[request_key] = (payload_digest, copy.deepcopy(result))


def _sanitized_request_key(request: Any) -> str:
    if isinstance(request, dict):
        value = request.get("recovery_request_key")
        if isinstance(value, str) and HEX64_PATTERN.fullmatch(value):
            return value
    return ""


def _safe_result(
    request: Any,
    *,
    decision_action: str,
    reason_code: str,
    eligible: bool = False,
    transition_candidates: Optional[list[list[str]]] = None,
    runtime_owner: str = "STAGE-043",
) -> dict[str, Any]:
    request_value = request if isinstance(request, dict) else {}
    request_is_valid = validate_recovery_request(request_value)
    evidence_value = request_value.get("evidence")
    evidence = (
        evidence_value
        if request_is_valid and isinstance(evidence_value, dict)
        else {}
    )
    request_key = _sanitized_request_key(request_value)
    digest_seed = {
        "request_key": request_key,
        "decision_action": decision_action,
        "reason_code": reason_code,
    }
    checkpoint_ref = evidence.get("checkpoint_ref")
    if not isinstance(checkpoint_ref, str) or not DIGEST_REF_PATTERN.fullmatch(
        checkpoint_ref
    ):
        checkpoint_ref = _digest_ref("checkpoint", digest_seed)
    quarantine_ref = evidence.get("quarantine_ref")
    if not isinstance(quarantine_ref, str) or not DIGEST_REF_PATTERN.fullmatch(
        quarantine_ref
    ):
        quarantine_ref = _digest_ref("quarantine", digest_seed)
    safe_inputs = evidence.get("input_refs")
    if safe_inputs != INPUT_REFS:
        safe_inputs = []
    error_ref = evidence.get("error_ref")
    if not _safe_scalar_ref(error_ref, prefixes=("error:",)):
        error_ref = f"error:{reason_code}"
    human_status = EXPECTED_HUMAN_STATUS.get(
        decision_action, EXPECTED_HUMAN_STATUS["REQUIRE_MANUAL_REVIEW"]
    )
    return {
        "schema_version": "ids.stage043.recovery_decision_result.v1",
        "recovery_request_key": request_key,
        "decision_action": decision_action,
        "reason_code": reason_code,
        "eligible": eligible,
        "transition_candidates": transition_candidates or [],
        "runtime_owner": runtime_owner,
        "automatic_resume_allowed": False,
        "input_refs": list(safe_inputs),
        "output_refs": [],
        "error_ref": error_ref,
        "checkpoint_ref": checkpoint_ref,
        "quarantine_ref": quarantine_ref,
        "audit_ref": AUDIT_REF,
        "human_status": copy.deepcopy(human_status),
        "state_mutation_performed": False,
        "process_crash_recovery_performed": False,
        "process_termination_performed": False,
        "worker_restart_performed": False,
        "checkpoint_resume_performed": False,
        "delete_allowed": False,
        "cleanup_execution_owner": "STAGE-044",
        "persistent_write_performed": False,
    }


def _crash_proven(evidence: Mapping[str, Any]) -> bool:
    evaluated = evidence["evaluated_at_epoch_seconds"]
    heartbeat = evidence["last_heartbeat_observed_at_epoch_seconds"]
    lease_expires = evidence["lease_expires_at_epoch_seconds"]
    detected = evidence["crash_detected_at_epoch_seconds"]
    return (
        detected >= heartbeat
        and detected - heartbeat >= EXPECTED_PARAMETERS["heartbeat_stale_window"]
        and detected >= lease_expires
        and detected - lease_expires >= EXPECTED_PARAMETERS["lease_expiry_grace"]
        and evaluated >= detected
        and evaluated - detected <= EXPECTED_PARAMETERS["crash_detection_interval"]
    )


def evaluate_recovery(
    request: Any,
    *,
    contract: Optional[Mapping[str, Any]] = None,
    ledger: Optional[InMemoryRecoveryDecisionLedger] = None,
) -> dict[str, Any]:
    contract_value: Any = load_contract() if contract is None else contract
    if not all(evaluate_contract(contract_value).values()):
        return _safe_result(
            request,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="INVALID_RECOVERY_CONTRACT",
        )

    if not validate_recovery_request(request):
        reason = "INVALID_RECOVERY_REQUEST"
        if isinstance(request, dict):
            key = request.get("recovery_request_key")
            if isinstance(key, str) and HEX64_PATTERN.fullmatch(key):
                try:
                    if key != derive_recovery_request_key(request):
                        reason = "RECOVERY_REQUEST_KEY_MISMATCH"
                except Exception:
                    pass
        return _safe_result(
            request,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code=reason,
        )

    request_value = request
    request_key = request_value["recovery_request_key"]
    payload_digest = _canonical_digest(request_value)
    if ledger is not None:
        ledger_state, existing = ledger.lookup(request_key, payload_digest)
        if ledger_state == "REPLAY" and existing is not None:
            return existing
        if ledger_state == "CONFLICT":
            return _safe_result(
                request_value,
                decision_action="REQUIRE_MANUAL_REVIEW",
                reason_code="RECOVERY_REQUEST_CONFLICT",
            )

    evidence = request_value["evidence"]
    state = request_value["observed_state"]
    intent = request_value["recovery_intent"]
    result: dict[str, Any]

    if state in TERMINAL_STATES:
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="TERMINAL_HISTORY_IMMUTABLE",
        )
    elif state not in ACTIVE_STATES:
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="INELIGIBLE_CRASH_STATE",
        )
    elif not _crash_proven(evidence):
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN",
        )
    elif not (
        evidence["persistent_state_available"]
        and evidence["state_version_current"]
        and evidence["lost_worker_generation_confirmed"]
        and evidence["lost_worker_fenced"]
        and not evidence["active_lock_or_claim_conflict"]
    ):
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="RECOVERY_OWNERSHIP_OR_STATE_EVIDENCE_INVALID",
        )
    elif intent == "RESOURCE_PAUSE":
        if (
            evidence["resource_gates_passed"] is False
            and evidence["resource_pressure_signal"] in PRESSURE_SIGNALS
        ):
            result = _safe_result(
                request_value,
                decision_action="RESOURCE_PAUSE_CANDIDATE",
                reason_code=evidence["resource_pressure_signal"],
                eligible=True,
                transition_candidates=[
                    [state, "RETRY_WAIT"],
                    ["RETRY_WAIT", "PAUSED"],
                ],
                runtime_owner="STAGE-040",
            )
        else:
            result = _safe_result(
                request_value,
                decision_action="REQUIRE_MANUAL_REVIEW",
                reason_code="RESOURCE_PAUSE_EVIDENCE_INVALID",
            )
    elif not evidence["resource_gates_passed"]:
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="RESOURCE_GATE_BLOCKED_WITHOUT_PAUSE_SIGNAL",
        )
    elif intent == "CHECKPOINT_RESUME":
        if (
            evidence["checkpoint_integrity_valid"]
            and evidence["checkpoint_idempotency_valid"]
            and evidence["owner_revalidated"]
            and bool(evidence["fresh_admission_claim_lock_cycle_ref"])
            and evidence["checkpoint_validation_elapsed_seconds"]
            <= EXPECTED_PARAMETERS["checkpoint_validation_timeout"]
        ):
            result = _safe_result(
                request_value,
                decision_action="CHECKPOINT_RESUME_CANDIDATE",
                reason_code="ALL_RECOVERY_GUARDS_REVALIDATED",
                eligible=True,
                transition_candidates=[
                    [state, "RETRY_WAIT"],
                    ["RETRY_WAIT", "QUEUED"],
                    ["QUEUED", "CLAIMED"],
                    ["CLAIMED", "RUNNING"],
                ],
            )
        else:
            result = _safe_result(
                request_value,
                decision_action="REQUIRE_MANUAL_REVIEW",
                reason_code="CHECKPOINT_CONTINUATION_GUARD_FAILED",
            )
    elif intent == "STAGE039_RETRY":
        if (
            evidence["stage039_policy_eligible"]
            and evidence["retry_budget_available"]
            and evidence["replay_safe"]
            and bool(evidence["error_ref"])
            and evidence["recovery_retry_wait_elapsed_seconds"]
            >= EXPECTED_PARAMETERS["recovery_retry_backoff"]
        ):
            result = _safe_result(
                request_value,
                decision_action="STAGE039_RETRY_CANDIDATE",
                reason_code="STAGE039_RETRY_GUARDS_REVALIDATED",
                eligible=True,
                transition_candidates=[[state, "RETRY_WAIT"]],
                runtime_owner="STAGE-039",
            )
        else:
            result = _safe_result(
                request_value,
                decision_action="REQUIRE_MANUAL_REVIEW",
                reason_code="STAGE039_RETRY_GUARD_FAILED",
            )
    elif intent == "SAFE_FAILURE":
        if (
            state == "RUNNING"
            and evidence["permanent_failure_recorded"]
            and bool(evidence["error_ref"])
            and evidence["legal_state_edge_available"]
        ):
            result = _safe_result(
                request_value,
                decision_action="SAFE_FAILURE_CANDIDATE",
                reason_code="PERMANENT_FAILURE_EVIDENCE_REVALIDATED",
                eligible=True,
                transition_candidates=[["RUNNING", "FAILED"]],
            )
        else:
            result = _safe_result(
                request_value,
                decision_action="REQUIRE_MANUAL_REVIEW",
                reason_code="SAFE_FAILURE_GUARD_FAILED",
            )
    else:
        result = _safe_result(
            request_value,
            decision_action="REQUIRE_MANUAL_REVIEW",
            reason_code="UNKNOWN_RECOVERY_INTENT",
        )

    if ledger is not None:
        ledger.record(request_key, payload_digest, result)
    return result


def build_stage043_phase2_report() -> dict[str, Any]:
    contract = load_contract()
    contract_checks = evaluate_contract(contract)
    ledger = InMemoryRecoveryDecisionLedger()
    checkpoint_request = build_recovery_request("CHECKPOINT_RESUME")
    checkpoint = evaluate_recovery(checkpoint_request, contract=contract, ledger=ledger)
    replay = evaluate_recovery(
        copy.deepcopy(checkpoint_request), contract=contract, ledger=ledger
    )
    changed = copy.deepcopy(checkpoint_request)
    changed["evidence"]["owner_revalidated"] = False
    conflict = evaluate_recovery(changed, contract=contract, ledger=ledger)
    retry = evaluate_recovery(
        build_recovery_request("STAGE039_RETRY"), contract=contract
    )
    safe_failure = evaluate_recovery(
        build_recovery_request("SAFE_FAILURE"), contract=contract
    )
    resource_pause = evaluate_recovery(
        build_recovery_request("RESOURCE_PAUSE"), contract=contract
    )
    terminal = evaluate_recovery(
        build_recovery_request("CHECKPOINT_RESUME", observed_state="SUCCEEDED"),
        contract=contract,
    )
    stale = evaluate_recovery(
        build_recovery_request(
            "CHECKPOINT_RESUME", last_heartbeat_observed_at_epoch_seconds=971
        ),
        contract=contract,
    )
    live_lease = evaluate_recovery(
        build_recovery_request(
            "CHECKPOINT_RESUME", lease_expires_at_epoch_seconds=996
        ),
        contract=contract,
    )
    unfenced = evaluate_recovery(
        build_recovery_request("CHECKPOINT_RESUME", lost_worker_fenced=False),
        contract=contract,
    )
    active_conflict = evaluate_recovery(
        build_recovery_request(
            "CHECKPOINT_RESUME", active_lock_or_claim_conflict=True
        ),
        contract=contract,
    )
    timed_out_checkpoint = evaluate_recovery(
        build_recovery_request(
            "CHECKPOINT_RESUME", checkpoint_validation_elapsed_seconds=31
        ),
        contract=contract,
    )
    early_retry = evaluate_recovery(
        build_recovery_request(
            "STAGE039_RETRY", recovery_retry_wait_elapsed_seconds=29
        ),
        contract=contract,
    )
    forged = build_recovery_request("CHECKPOINT_RESUME")
    forged["recovery_request_key"] = "0" * 64
    key_mismatch = evaluate_recovery(forged, contract=contract)
    candidate_results = [checkpoint, retry, safe_failure, resource_pause]
    all_no_effects = all(
        not result["state_mutation_performed"]
        and not result["process_crash_recovery_performed"]
        and not result["process_termination_performed"]
        and not result["worker_restart_performed"]
        and not result["checkpoint_resume_performed"]
        and not result["delete_allowed"]
        and not result["persistent_write_performed"]
        for result in candidate_results
    )
    decision_checks = {
        "checkpoint_resume_candidate": checkpoint["decision_action"]
        == "CHECKPOINT_RESUME_CANDIDATE",
        "stage039_retry_candidate": retry["decision_action"]
        == "STAGE039_RETRY_CANDIDATE",
        "safe_failure_candidate": safe_failure["decision_action"]
        == "SAFE_FAILURE_CANDIDATE",
        "resource_pause_candidate": resource_pause["decision_action"]
        == "RESOURCE_PAUSE_CANDIDATE",
        "exact_replay_idempotent": checkpoint == replay,
        "changed_payload_conflict": conflict["reason_code"]
        == "RECOVERY_REQUEST_CONFLICT",
        "terminal_history_immutable": terminal["reason_code"]
        == "TERMINAL_HISTORY_IMMUTABLE",
        "stale_heartbeat_fails_closed": stale["decision_action"]
        == "REQUIRE_MANUAL_REVIEW",
        "live_lease_fails_closed": live_lease["decision_action"]
        == "REQUIRE_MANUAL_REVIEW",
        "unfenced_worker_fails_closed": unfenced["decision_action"]
        == "REQUIRE_MANUAL_REVIEW",
        "active_claim_or_lock_conflict_fails_closed": active_conflict[
            "decision_action"
        ]
        == "REQUIRE_MANUAL_REVIEW",
        "checkpoint_timeout_fails_closed": timed_out_checkpoint["decision_action"]
        == "REQUIRE_MANUAL_REVIEW",
        "retry_backoff_fails_closed": early_retry["decision_action"]
        == "REQUIRE_MANUAL_REVIEW",
        "request_key_mismatch_fails_closed": key_mismatch["reason_code"]
        == "RECOVERY_REQUEST_KEY_MISMATCH",
        "all_results_reference_only_no_effects": all_no_effects,
    }
    passed = all(contract_checks.values()) and all(decision_checks.values())
    return {
        "schema_version": "ids.stage043.worker_crash_recovery.phase2.report.v1",
        "task_id": "IDS-V0_1-STAGE043-P2",
        "acceptance_id": "ACC-STAGE-043",
        "policy_version": POLICY_VERSION,
        "contract_state": (
            "PHASE2_ISOLATED_RECOVERY_DECISION_SLICE_ENABLED_PRODUCTION_DISABLED"
        ),
        "contract_checks": contract_checks,
        "contract_check_count": len(contract_checks),
        "decision_checks": decision_checks,
        "decision_check_count": len(decision_checks),
        "parameter_values": EXPECTED_PARAMETERS,
        "parameter_values_assigned": True,
        "parameter_fact_level": "PROPOSED",
        "production_calibrated": False,
        "production_calibration_task_id": "TASK-OPME-B-001",
        "isolated_recovery_decision_runtime_performed": True,
        "recovery_candidate_evaluation_performed": True,
        "checkpoint_resume_candidate_evaluated": True,
        "stage039_retry_candidate_evaluated": True,
        "safe_failure_candidate_evaluated": True,
        "resource_pause_candidate_evaluated": True,
        "successful_recovery_observed": False,
        "process_probe_performed": False,
        "crash_injected": False,
        "process_crash_recovery_performed": False,
        "process_termination_performed": False,
        "worker_restart_performed": False,
        "state_transition_performed": False,
        "checkpoint_resume_performed": False,
        "cleanup_runtime_performed": False,
        "protected_ref_delete_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "schema_change_performed": False,
        "runtime_output_written": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "real_ids_business_job_created": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
        "next_gate": "IDS-STAGE043-P3-GATE",
        "result": (
            "PASS_ISOLATED_RECOVERY_DECISION_SLICE_PRODUCTION_DISABLED"
            if passed
            else "FAIL_CLOSED_MANUAL_REVIEW_REQUIRED"
        ),
    }


def main() -> int:
    report = build_stage043_phase2_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
