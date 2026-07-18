#!/usr/bin/env python3
"""Validate the STAGE-043 Phase 1 worker-crash-recovery contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict
from zipfile import ZipFile


CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
    "stage043_worker_crash_recovery_contract.json"
)
STATE_MODEL_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/job_state_model/"
    "stage037_job_state_model_index.json"
)

EXPECTED_ROOT_KEYS = {
    "schema_version", "stage", "phase", "task_id", "acceptance_id",
    "local_code", "domain", "entrance", "pursuing_goal",
    "crash_recovery_contract_id", "contract_state", "execution_ready",
    "next_gate", "source_binding", "predecessor_binding",
    "upstream_bindings", "state_authority", "worker_boundary",
    "crash_detection_contract", "recovery_decision_contract",
    "resource_pause_contract", "idempotency_contract",
    "lock_and_fencing_contract", "partial_output_contract",
    "parameter_contract", "human_status_projection", "phase2_entry_gate",
    "truth_flags",
}

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
    "source_member_integrity": "OK",
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
    "stage042_review_commit": "ba248f66ce993a726cb12547ae1c772ab1228bfa",
    "stage042_review_tree": "0e13164deeaa491fb98384fad5158a89658a2f77",
    "stage042_review_parent": "2c489d049d73cd632e905c7af1b39ba662a2139b",
    "stage042_review_status": "completed_reviewed_local",
    "stage042_review_result": "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED",
}

EXPECTED_UPSTREAM = {
    "stage037_state_index_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    },
    "stage038_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
            "stage038_worker_queue_delivery_contract.json"
        ),
        "sha256": "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4",
    },
    "stage039_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
            "stage039_retry_dead_letter_delivery_contract.json"
        ),
        "sha256": "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b",
    },
    "stage040_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
            "stage040_backpressure_delivery_contract.json"
        ),
        "sha256": "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    },
    "stage041_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
            "stage041_lock_registry_delivery_contract.json"
        ),
        "sha256": "817ffc115bfec9ee29ec4f96f23ec6793ad1121f500eb13301b897ddcbabad84",
    },
    "stage042_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
            "stage042_automatic_lifecycle_delivery_contract.json"
        ),
        "sha256": "b3406b6542256a4a7f8b015bf11271822496bdad8129b787dbbf0044035311f3",
    },
    "stage042_review_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE042_STAGE_REVIEW.md"
        ),
        "sha256": "2ca9ef6107d54ccad624e46f3a6efda8832d00872964773bab6f70326803302d",
    },
}

EXPECTED_JOB_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "DEAD_LETTERED",
    "CANCELLED",
]
EXPECTED_TERMINAL_STATES = ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
EXPECTED_ACTIVE_STATES = ["CLAIMED", "RUNNING", "PAUSE_REQUESTED"]
EXPECTED_CRASH_EDGES = [
    "CLAIMED->RETRY_WAIT",
    "RUNNING->RETRY_WAIT",
    "RUNNING->FAILED",
    "PAUSE_REQUESTED->RETRY_WAIT",
]
EXPECTED_REENTRY = [
    "ACTIVE_STATE->RETRY_WAIT",
    "RETRY_WAIT->QUEUED",
    "QUEUED->CLAIMED",
    "CLAIMED->RUNNING",
]
EXPECTED_EVIDENCE_FIELDS = [
    "job_id", "attempt_id", "worker_instance_id", "worker_generation",
    "observed_state", "expected_state_version", "last_heartbeat_observed_at",
    "lease_owner_ref", "lease_expires_at", "lock_key", "fencing_token",
    "checkpoint_ref", "quarantine_ref", "error_ref", "audit_ref",
]
EXPECTED_RESUME_CONDITIONS = [
    "CHECKPOINT_INTEGRITY_VALID", "IDEMPOTENCY_IDENTITY_VALID",
    "OWNER_REVALIDATED", "RESOURCE_GATES_PASS", "LOST_WORKER_FENCED",
    "STATE_VERSION_CURRENT", "FRESH_ADMISSION_CLAIM_LOCK_CYCLE",
]
EXPECTED_PAUSE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
EXPECTED_PROTECTED_CLASSES = [
    "FACT_SOURCE", "MANIFEST", "EVIDENCE_LEDGER", "REPORT_SNAPSHOT",
    "AUDIT_LOG",
]
EXPECTED_PARAMETERS = [
    "crash_detection_interval", "heartbeat_stale_window", "lease_expiry_grace",
    "recovery_retry_backoff", "checkpoint_validation_timeout",
]
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed", "raw_metadata_content_accessed",
    "fake_ids_business_data_used", "real_ids_business_job_created",
    "queue_runtime_performed", "worker_runtime_performed",
    "retry_scheduler_performed", "backpressure_runtime_performed",
    "production_lock_runtime_performed",
    "automatic_lifecycle_runtime_performed", "process_termination_performed",
    "process_crash_recovery_performed", "worker_restart_performed",
    "state_transition_performed", "checkpoint_resume_performed",
    "cleanup_runtime_performed", "protected_ref_delete_performed",
    "persistent_state_write_performed", "database_connection_performed",
    "schema_change_performed", "runtime_output_written",
    "production_runtime_activation_performed", "whole_stage_review_performed",
    "batch_review_performed", "github_upload_allowed", "app_reinstall_allowed",
}

EXPECTED_NESTED_KEYS = {
    "source_binding": set(EXPECTED_SOURCE),
    "predecessor_binding": set(EXPECTED_PREDECESSOR),
    "upstream_bindings": set(EXPECTED_UPSTREAM),
    "state_authority": {
        "state_model_version", "job_states", "terminal_states",
        "active_execution_states", "legal_crash_transition_candidates",
        "guarded_reentry_sequence", "new_state_introduced",
        "terminal_history_reopen_allowed",
        "direct_running_to_running_resume_allowed",
        "direct_active_to_queued_recovery_allowed",
        "in_memory_state_restoration_allowed",
    },
    "worker_boundary": {
        "event_owners", "recognized_crash_classes",
        "queue_and_worker_transport_owner", "worker_runtime_allowed",
        "process_termination_allowed", "worker_restart_allowed",
        "production_runtime_allowed",
    },
    "crash_detection_contract": {
        "mode", "required_evidence_fields", "required_evidence_properties",
        "unknown_or_stale_evidence_action",
        "heartbeat_or_lease_threshold_source_required",
        "process_probe_performed", "crash_injected",
        "state_registry_read_performed",
    },
    "recovery_decision_contract": {
        "decision_mode", "allowed_outcomes",
        "checkpoint_resume_required_conditions",
        "retry_candidate_required_conditions",
        "safe_failure_required_conditions", "manual_review_cases",
        "retry_and_dead_letter_owner", "pressure_pause_owner",
        "lock_lease_fencing_owner", "automatic_lifecycle_owner",
        "cleanup_execution_owner", "blind_continue_allowed",
        "state_mutation_allowed", "successful_recovery_observed",
    },
    "resource_pause_contract": {
        "mandatory_pause_signals", "crashed_active_resource_blocked_sequence",
        "owner_revalidation_required", "fresh_resource_observation_required",
        "automatic_resume_allowed", "state_mutation_allowed",
    },
    "idempotency_contract": {
        "recovery_request_key_fields", "canonical_key_formula",
        "one_incident_one_decision", "exact_replay_returns_original_decision",
        "same_key_payload_conflict_fails_closed", "decision_audit_append_required",
        "idempotency_registry_write_allowed",
    },
    "lock_and_fencing_contract": {
        "owner", "lost_worker_must_be_fenced", "current_state_version_required",
        "current_fencing_token_required", "fresh_lock_lease_cycle_required",
        "stale_worker_output_acceptance_allowed",
        "missing_in_memory_lock_restoration_allowed",
        "takeover_or_lock_mutation_allowed",
    },
    "partial_output_contract": {
        "handling_mode", "cleanup_candidate_classes",
        "protected_artifact_classes", "checkpoint_or_quarantine_ref_required",
        "writer_quiescence_evidence_required", "cleanup_execution_owner",
        "delete_allowed", "output_mutation_allowed",
    },
    "parameter_contract": {
        "deferred_parameter_names", "required_future_fields",
        "numeric_values_assigned", "production_calibrated",
        "implicit_defaults_allowed", "status",
    },
    "human_status_projection": {
        "WAITING_CRASH_EVIDENCE", "RECOVERY_CANDIDATE_READY",
        "RESOURCE_PAUSED", "SAFE_FAILURE_CANDIDATE",
        "MANUAL_REVIEW_REQUIRED",
    },
    "phase2_entry_gate": {
        "required_gate", "required_conditions", "phase2_must_run_separately",
        "execution_ready", "push_allowed",
    },
    "truth_flags": {"taskpack_source_read_performed"} | FALSE_TRUTH_FLAGS,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_false(mapping: Dict[str, Any], names: set) -> bool:
    return all(mapping.get(name) is False for name in names)


def _live_source_valid() -> bool:
    archive = Path(EXPECTED_SOURCE["source_archive_path"])
    if not archive.is_file() or _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]:
        return False
    with ZipFile(archive) as source_zip:
        matches = [
            name for name in source_zip.namelist()
            if name == EXPECTED_SOURCE["source_member"]
        ]
        if len(matches) != 1:
            return False
        member_hash = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
    return member_hash == EXPECTED_SOURCE["source_member_sha256"]


def _predecessor_valid(repo_root: Path) -> bool:
    try:
        observed = subprocess.check_output(
            [
                "git", "show", "-s", "--format=%H%n%T%n%P",
                EXPECTED_PREDECESSOR["stage042_review_commit"],
            ],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        ancestor = subprocess.run(
            [
                "git", "merge-base", "--is-ancestor",
                EXPECTED_PREDECESSOR["stage042_review_commit"], "HEAD",
            ],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return observed == [
        EXPECTED_PREDECESSOR["stage042_review_commit"],
        EXPECTED_PREDECESSOR["stage042_review_tree"],
        EXPECTED_PREDECESSOR["stage042_review_parent"],
    ] and ancestor


def _upstream_valid(repo_root: Path, bindings: Any) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    for item in EXPECTED_UPSTREAM.values():
        path = repo_root / item["ref"]
        if not path.is_file() or _sha256(path) != item["sha256"]:
            return False
    return True


def _state_graph_valid(root: Path, authority: Any) -> bool:
    state_path = root / STATE_MODEL_RELATIVE
    if not state_path.is_file() or not isinstance(authority, dict):
        return False
    state_model = json.loads(state_path.read_text(encoding="utf-8"))["state_model"]
    allowed = state_model["allowed_transitions"]
    legal_edges = {
        "%s->%s" % (source, target)
        for source, targets in allowed.items()
        for target in targets
    }
    return (
        authority.get("state_model_version") == state_model["state_model_version"]
        and authority.get("job_states") == state_model["job_states"]
        and authority.get("terminal_states") == state_model["terminal_states"]
        and authority.get("active_execution_states") == EXPECTED_ACTIVE_STATES
        and authority.get("legal_crash_transition_candidates") == EXPECTED_CRASH_EDGES
        and set(EXPECTED_CRASH_EDGES).issubset(legal_edges)
        and authority.get("guarded_reentry_sequence") == EXPECTED_REENTRY
        and authority.get("new_state_introduced") is False
        and authority.get("terminal_history_reopen_allowed") is False
        and authority.get("direct_running_to_running_resume_allowed") is False
        and authority.get("direct_active_to_queued_recovery_allowed") is False
        and authority.get("in_memory_state_restoration_allowed") is False
    )


def evaluate_contract(contract: Dict[str, Any], root: Path = None) -> Dict[str, bool]:
    root = root or Path(__file__).resolve().parents[1]
    repo_root = root.parent
    checks: Dict[str, bool] = {}
    checks["root_exact_shape"] = set(contract) == EXPECTED_ROOT_KEYS
    checks["nested_exact_shapes"] = all(
        isinstance(contract.get(name), dict)
        and set(contract[name]) == expected
        for name, expected in EXPECTED_NESTED_KEYS.items()
    )
    checks["identity"] = (
        contract.get("schema_version")
        == "ids.stage043.worker_crash_recovery.phase1.v1"
        and contract.get("stage") == "STAGE-043"
        and contract.get("phase") == "Phase 1"
        and contract.get("task_id") == "IDS-V0_1-STAGE043-P1"
        and contract.get("acceptance_id") == "ACC-STAGE-043"
        and contract.get("local_code") == "D07-S007"
        and contract.get("domain") == "D07"
        and contract.get("entrance") == "IDS_SYSTEM_OPERATIONS"
        and contract.get("pursuing_goal")
        == "VERIFY_WORKER_CRASH_PRESERVES_JOB_STATE_AND_SUPPORTS_GUARDED_CONTINUATION_OR_SAFE_FAILURE"
        and contract.get("crash_recovery_contract_id")
        == "ids.worker_crash_recovery.v0_1.p1"
        and contract.get("contract_state")
        == "PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED"
        and contract.get("execution_ready") is False
        and contract.get("next_gate") == "IDS-STAGE043-P2-GATE"
    )
    checks["source_binding"] = contract.get("source_binding") == EXPECTED_SOURCE
    checks["source_live"] = _live_source_valid()
    checks["predecessor_binding"] = (
        contract.get("predecessor_binding") == EXPECTED_PREDECESSOR
        and _predecessor_valid(repo_root)
    )
    checks["upstream_bindings"] = _upstream_valid(
        repo_root, contract.get("upstream_bindings")
    )
    checks["state_graph"] = _state_graph_valid(root, contract.get("state_authority"))
    worker = contract.get("worker_boundary", {})
    checks["worker_boundary"] = (
        worker.get("event_owners") == {
            "TASK_EXCEPTION": "STAGE-039",
            "ORDERLY_LIFECYCLE_SHUTDOWN": "STAGE-042",
            "WORKER_PROCESS_LOST": "STAGE-043",
            "PARTIAL_OUTPUT_CLEANUP": "STAGE-044",
        }
        and worker.get("recognized_crash_classes") == [
            "WORKER_PROCESS_LOST", "WORKER_GENERATION_REPLACED",
            "HEARTBEAT_OR_LEASE_STALE",
            "PROCESS_EXIT_WITHOUT_PERSISTENT_STATE",
        ]
        and worker.get("queue_and_worker_transport_owner") == "STAGE-038"
        and _strict_false(worker, {
            "worker_runtime_allowed", "process_termination_allowed",
            "worker_restart_allowed", "production_runtime_allowed",
        })
    )
    detection = contract.get("crash_detection_contract", {})
    checks["crash_detection"] = (
        detection.get("mode") == "STATIC_EVIDENCE_EVALUATION_ONLY"
        and detection.get("required_evidence_fields") == EXPECTED_EVIDENCE_FIELDS
        and detection.get("required_evidence_properties")
        == ["CURRENT", "INTERNALLY_CONSISTENT", "SOURCE_BOUND", "AUDITABLE"]
        and detection.get("unknown_or_stale_evidence_action")
        == "REQUIRE_MANUAL_REVIEW"
        and detection.get("heartbeat_or_lease_threshold_source_required") is True
        and _strict_false(detection, {
            "process_probe_performed", "crash_injected",
            "state_registry_read_performed",
        })
    )
    recovery = contract.get("recovery_decision_contract", {})
    checks["recovery_decisions"] = (
        recovery.get("decision_mode") == "STATIC_CANDIDATE_ONLY"
        and recovery.get("allowed_outcomes") == [
            "CHECKPOINT_RESUME_CANDIDATE", "STAGE039_RETRY_CANDIDATE",
            "SAFE_FAILURE_CANDIDATE", "RESOURCE_PAUSE_CANDIDATE",
            "REQUIRE_MANUAL_REVIEW",
        ]
        and recovery.get("checkpoint_resume_required_conditions")
        == EXPECTED_RESUME_CONDITIONS
        and recovery.get("retry_and_dead_letter_owner") == "STAGE-039"
        and recovery.get("pressure_pause_owner") == "STAGE-040"
        and recovery.get("lock_lease_fencing_owner") == "STAGE-041"
        and recovery.get("automatic_lifecycle_owner") == "STAGE-042"
        and recovery.get("cleanup_execution_owner") == "STAGE-044"
        and _strict_false(recovery, {
            "blind_continue_allowed", "state_mutation_allowed",
            "successful_recovery_observed",
        })
    )
    pause = contract.get("resource_pause_contract", {})
    checks["resource_pause"] = (
        pause.get("mandatory_pause_signals") == EXPECTED_PAUSE_SIGNALS
        and pause.get("crashed_active_resource_blocked_sequence")
        == ["ACTIVE_STATE->RETRY_WAIT", "RETRY_WAIT->PAUSED"]
        and pause.get("owner_revalidation_required") is True
        and pause.get("fresh_resource_observation_required") is True
        and _strict_false(pause, {"automatic_resume_allowed", "state_mutation_allowed"})
    )
    identity = contract.get("idempotency_contract", {})
    checks["idempotency"] = (
        identity.get("recovery_request_key_fields") == [
            "job_id", "attempt_id", "worker_generation",
            "observed_state_version", "crash_incident_id",
        ]
        and identity.get("canonical_key_formula")
        == "sha256(canonical_json(recovery_request_key_fields))"
        and identity.get("one_incident_one_decision") is True
        and identity.get("exact_replay_returns_original_decision") is True
        and identity.get("same_key_payload_conflict_fails_closed") is True
        and identity.get("decision_audit_append_required") is True
        and identity.get("idempotency_registry_write_allowed") is False
    )
    fencing = contract.get("lock_and_fencing_contract", {})
    checks["lock_and_fencing"] = (
        fencing.get("owner") == "STAGE-041"
        and all(fencing.get(name) is True for name in {
            "lost_worker_must_be_fenced", "current_state_version_required",
            "current_fencing_token_required", "fresh_lock_lease_cycle_required",
        })
        and _strict_false(fencing, {
            "stale_worker_output_acceptance_allowed",
            "missing_in_memory_lock_restoration_allowed",
            "takeover_or_lock_mutation_allowed",
        })
    )
    partial = contract.get("partial_output_contract", {})
    checks["partial_output"] = (
        partial.get("handling_mode") == "QUARANTINE_AND_REFERENCE_ONLY"
        and partial.get("cleanup_candidate_classes")
        == ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
        and partial.get("protected_artifact_classes") == EXPECTED_PROTECTED_CLASSES
        and partial.get("checkpoint_or_quarantine_ref_required") is True
        and partial.get("writer_quiescence_evidence_required") is True
        and partial.get("cleanup_execution_owner") == "STAGE-044"
        and _strict_false(partial, {"delete_allowed", "output_mutation_allowed"})
    )
    parameters = contract.get("parameter_contract", {})
    checks["parameters"] = (
        parameters.get("deferred_parameter_names") == EXPECTED_PARAMETERS
        and parameters.get("required_future_fields") == [
            "value", "unit", "source", "rationale", "policy_version",
            "validation_evidence_ref", "rollback",
        ]
        and _strict_false(parameters, {
            "numeric_values_assigned", "production_calibrated",
            "implicit_defaults_allowed",
        })
        and parameters.get("status") == "DEFERRED_TO_SEPARATE_PHASE2"
    )
    checks["human_status"] = contract.get("human_status_projection") == {
        "WAITING_CRASH_EVIDENCE": "等待崩溃证据",
        "RECOVERY_CANDIDATE_READY": "恢复候选已就绪",
        "RESOURCE_PAUSED": "资源条件暂停",
        "SAFE_FAILURE_CANDIDATE": "安全失败候选",
        "MANUAL_REVIEW_REQUIRED": "需要人工复核",
    }
    gate = contract.get("phase2_entry_gate", {})
    checks["phase2_gate"] = (
        gate.get("required_gate") == "IDS-STAGE043-P2-GATE"
        and gate.get("required_conditions") == [
            "PHASE1_CHECKER_VALID", "SOURCE_AND_PREDECESSOR_BINDINGS_CURRENT",
            "ALL_UPSTREAM_HASHES_CURRENT",
            "STATE_GRAPH_AND_TERMINAL_IMMUTABILITY_VALID",
            "CRASH_EVIDENCE_SCHEMA_VALID",
            "IDEMPOTENCY_AND_FENCING_BOUNDARY_VALID",
            "RESOURCE_PAUSE_AND_CLEANUP_BOUNDARY_VALID",
            "NO_RUNTIME_OR_PRODUCTION_ACTION_PERFORMED",
        ]
        and gate.get("phase2_must_run_separately") is True
        and _strict_false(gate, {"execution_ready", "push_allowed"})
    )
    truth = contract.get("truth_flags", {})
    checks["truth_flags"] = (
        set(truth) == ({"taskpack_source_read_performed"} | FALSE_TRUTH_FLAGS)
        and truth.get("taskpack_source_read_performed") is True
        and _strict_false(truth, FALSE_TRUTH_FLAGS)
    )
    return checks


def build_stage043_phase1_report(root: Path = None) -> Dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    contract_path = root / CONTRACT_RELATIVE
    if not contract_path.is_file():
        return {
            "schema_version": "ids.stage043.worker_crash_recovery.phase1.report.v1",
            "stage": "STAGE-043",
            "phase": "Phase 1",
            "task_id": "IDS-V0_1-STAGE043-P1",
            "acceptance_id": "ACC-STAGE-043",
            "valid": False,
            "result": "BLOCKED_MISSING_CONTRACT",
            "next_gate": None,
            "execution_ready": False,
            "push_allowed": False,
            "checks": {},
        }
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    checks = evaluate_contract(contract, root=root)
    valid = bool(checks) and all(checks.values())
    return {
        "schema_version": "ids.stage043.worker_crash_recovery.phase1.report.v1",
        "stage": "STAGE-043",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE043-P1",
        "acceptance_id": "ACC-STAGE-043",
        "valid": valid,
        "result": (
            "PASS_PHASE1_CONTRACT_RUNTIME_DISABLED"
            if valid else "BLOCKED_CONTRACT_INVALID"
        ),
        "next_gate": contract.get("next_gate") if valid else None,
        "execution_ready": False,
        "push_allowed": False,
        "checks": checks,
    }


def main() -> int:
    report = build_stage043_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
