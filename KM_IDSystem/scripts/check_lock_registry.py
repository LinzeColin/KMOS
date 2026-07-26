#!/usr/bin/env python3
"""Validate the STAGE-041 Phase 1 lock-registry engineering contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/lock_registry/"
    "stage041_lock_registry_contract.json"
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
    "lock_registry_contract_id",
    "contract_state",
    "execution_ready",
    "next_gate",
    "source_binding",
    "upstream_bindings",
    "state_model_inheritance",
    "operation_scope_contract",
    "registry_record_contract",
    "lock_key_contract",
    "idempotency_contract",
    "acquisition_contract",
    "lease_contract",
    "fencing_contract",
    "release_contract",
    "conflict_contract",
    "parameter_contract",
    "backpressure_boundary",
    "retry_boundary",
    "partial_output_cleanup_boundary",
    "ownership_matrix",
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
        "STAGE-041_锁注册与竞态控制.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

EXPECTED_UPSTREAM = {
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "job_state_model/stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage038_scenarios_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "worker_queue_baseline/stage038_worker_queue_scenarios.json",
        "0ec9f1a0de6ec24d64d4108214ea426f9171b15eebdd6c3c60693fade62f2961",
    ),
    "stage038_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "worker_queue_baseline/stage038_worker_queue_delivery_contract.json",
        "a4067c25b46340c33bee5017c286d6867d2b72e8fa208430c005d6b1a342c7e4",
    ),
    "stage039_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "retry_dead_letter/stage039_retry_dead_letter_delivery_contract.json",
        "c7d020d8fe5fc21dc9c6d7fb01030659f3e545f1416cae96f5c96c77a7f0c06b",
    ),
    "stage040_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "backpressure_policy/stage040_backpressure_delivery_contract.json",
        "f9934bc5e0f30e032f3138f9c11022b823942160f07b734b0ccbf9ad17f431ce",
    ),
    "previous_batch_lock_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "BATCH031_040_UPLOAD_LOCK.yaml",
        "ad235a242c5833e2e6243227cc8fe7ca9223a75d5ae98a8b732b3b4418477940",
    ),
}

EXPECTED_OPERATION_FAMILIES = {
    "FILE_PROCESSING": {
        "job_types": ["PARSE"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "FILE_PROCESSING"],
        "primary_granularity": "SOURCE_REFERENCE",
    },
    "ARCHIVE_EXTRACTION": {
        "job_types": ["ARCHIVE"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "ARCHIVE_EXTRACTION"],
        "primary_granularity": "SOURCE_REFERENCE",
    },
    "INDEX_BUILD": {
        "job_types": ["INDEX"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "INDEX_BUILD"],
        "primary_granularity": "INDEX_VERSION_REFERENCE",
    },
    "INDEX_SWITCH": {
        "job_types": ["INDEX"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "INDEX_SWITCH"],
        "primary_granularity": "INDEX_NAMESPACE_REFERENCE",
    },
    "REPORT_GENERATION": {
        "job_types": ["REPORT"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "REPORT_GENERATION"],
        "primary_granularity": "REPORT_IDENTITY_REFERENCE",
    },
}

REGISTRY_FIELDS = [
    "lock_key",
    "lock_namespace",
    "resource_identity_ref",
    "operation_scope",
    "holder_job_id",
    "holder_attempt_id",
    "lease_owner_ref",
    "lease_expires_at",
    "fencing_token",
    "lock_version",
    "acquired_at",
    "renewed_at",
    "released_at",
    "release_reason",
    "audit_ref",
    "checkpoint_ref",
    "policy_version",
]

DEFERRED_PARAMETERS = [
    "lease_duration",
    "renewal_interval",
    "expiry_grace",
    "acquisition_timeout",
    "maximum_wait",
    "retry_jitter",
    "deadlock_timeout",
]

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "lock_runtime_performed",
    "lease_runtime_performed",
    "fencing_runtime_performed",
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "backpressure_runtime_performed",
    "automatic_resume_performed",
    "crash_recovery_runtime_performed",
    "cleanup_runtime_performed",
    "database_connection_performed",
    "schema_change_performed",
    "state_registry_write_performed",
    "runtime_output_written",
    "real_ids_business_job_created",
    "fake_ids_business_data_used",
    "external_api_call_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keys_exact(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _upstream_bindings_valid(contract: dict[str, Any], project_root: Path) -> bool:
    bindings = contract.get("upstream_bindings")
    if not isinstance(bindings, dict) or set(bindings) != set(EXPECTED_UPSTREAM):
        return False
    repo_root = project_root.parent
    for key, (expected_ref, expected_hash) in EXPECTED_UPSTREAM.items():
        binding = bindings.get(key)
        if not _keys_exact(binding, {"ref", "sha256"}):
            return False
        if binding["ref"] != expected_ref or binding["sha256"] != expected_hash:
            return False
        source = repo_root / expected_ref
        if not source.is_file() or _sha256(source) != expected_hash:
            return False
    return True


def evaluate_contract(contract: Any, project_root: Path | None = None) -> dict[str, bool]:
    project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    if not isinstance(contract, dict):
        return {"contract_is_object": False}

    state = contract.get("state_model_inheritance")
    scope = contract.get("operation_scope_contract")
    registry = contract.get("registry_record_contract")
    lock_key = contract.get("lock_key_contract")
    idempotency = contract.get("idempotency_contract")
    acquisition = contract.get("acquisition_contract")
    lease = contract.get("lease_contract")
    fencing = contract.get("fencing_contract")
    release = contract.get("release_contract")
    conflict = contract.get("conflict_contract")
    parameters = contract.get("parameter_contract")
    backpressure = contract.get("backpressure_boundary")
    retry = contract.get("retry_boundary")
    cleanup = contract.get("partial_output_cleanup_boundary")
    ownership = contract.get("ownership_matrix")
    human_status = contract.get("human_status_projection")
    phase2 = contract.get("phase2_entry_gate")
    truth = contract.get("truth_flags")

    checks = {
        "contract_is_object": True,
        "root_fields_exact": set(contract) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            contract.get("schema_version") == "ids.stage041.lock_registry.phase1.v1"
            and contract.get("stage") == "STAGE-041"
            and contract.get("phase") == "Phase 1"
            and contract.get("task_id") == "IDS-V0_1-STAGE041-P1"
            and contract.get("acceptance_id") == "ACC-STAGE-041"
            and contract.get("local_code") == "D07-S005"
            and contract.get("domain") == "D07 · 任务编排与机器控制"
            and contract.get("entrance") == "IDS 系统运营入口"
            and contract.get("pursuing_goal")
            == "为文件处理、归档解包、索引构建、索引切换与报告生成定义锁注册、租约与 fencing 竞态控制契约。"
            and contract.get("lock_registry_contract_id")
            == "ids.lock_registry.v0_1.p1"
            and contract.get("contract_state")
            == "PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED"
            and contract.get("execution_ready") is False
            and contract.get("next_gate") == "IDS-STAGE041-P2-GATE"
        ),
        "source_binding_exact": contract.get("source_binding")
        == EXPECTED_SOURCE_BINDING,
        "upstream_bindings_current": _upstream_bindings_valid(
            contract, project_root
        ),
        "state_model_inheritance_valid": (
            _keys_exact(
                state,
                {
                    "state_model_version",
                    "required_envelope_fields",
                    "claim_transition",
                    "claim_guard",
                    "active_transition_guards",
                    "unclaimed_guard",
                    "terminal_states",
                    "terminal_state_mutation_allowed",
                },
            )
            and state.get("state_model_version") == "ids.job_state.v1"
            and state.get("required_envelope_fields")
            == ["lease_owner_ref", "lease_expires_at", "fencing_token", "lock_key"]
            and state.get("claim_transition") == ["QUEUED", "CLAIMED"]
            and state.get("claim_guard") == "claim_lease_and_lock_acquired"
            and state.get("active_transition_guards")
            == ["live_lease_valid", "fencing_token_matches"]
            and state.get("unclaimed_guard") == "no_active_claim_or_lock"
            and state.get("terminal_states")
            == ["SUCCEEDED", "FAILED", "DEAD_LETTERED", "CANCELLED"]
            and state.get("terminal_state_mutation_allowed") is False
        ),
        "operation_scope_valid": (
            _keys_exact(
                scope,
                {
                    "operation_families",
                    "stage038_same_source_conflict_job_types",
                    "stage038_conflict_result_code",
                    "mandatory_shared_guard_namespace",
                    "all_operation_families_require_shared_guard",
                    "stage038_baseline_narrowing_allowed",
                    "index_build_switch_coordination_required",
                },
            )
            and scope.get("operation_families") == EXPECTED_OPERATION_FAMILIES
            and scope.get("stage038_same_source_conflict_job_types")
            == ["ARCHIVE", "PARSE", "INDEX", "REPORT"]
            and scope.get("stage038_conflict_result_code")
            == "RESOURCE_CONFLICT_ACTIVE"
            and scope.get("mandatory_shared_guard_namespace") == "SOURCE_PIPELINE"
            and scope.get("all_operation_families_require_shared_guard") is True
            and scope.get("stage038_baseline_narrowing_allowed") is False
            and scope.get("index_build_switch_coordination_required") is True
        ),
        "registry_record_valid": (
            _keys_exact(
                registry,
                {
                    "required_fields",
                    "reference_only",
                    "raw_path_allowed",
                    "raw_payload_allowed",
                    "secret_material_allowed",
                    "unknown_field_action",
                },
            )
            and registry.get("required_fields") == REGISTRY_FIELDS
            and registry.get("reference_only") is True
            and registry.get("raw_path_allowed") is False
            and registry.get("raw_payload_allowed") is False
            and registry.get("secret_material_allowed") is False
            and registry.get("unknown_field_action") == "REJECT_CONTRACT"
        ),
        "lock_key_valid": (
            _keys_exact(
                lock_key,
                {
                    "derivation",
                    "multi_lock_order",
                    "stable_normalized_reference_required",
                    "source_content_read_required",
                    "raw_path_in_key_allowed",
                    "missing_identity_action",
                    "hash_algorithm",
                },
            )
            and lock_key.get("derivation")
            == "SHA256_CANONICAL_NAMESPACE_AND_STABLE_RESOURCE_IDENTITY_REF"
            and lock_key.get("multi_lock_order") == "LEXICOGRAPHIC_LOCK_KEY"
            and lock_key.get("stable_normalized_reference_required") is True
            and lock_key.get("source_content_read_required") is False
            and lock_key.get("raw_path_in_key_allowed") is False
            and lock_key.get("missing_identity_action") == "REQUIRE_MANUAL_REVIEW"
            and lock_key.get("hash_algorithm") == "SHA-256"
        ),
        "idempotency_valid": (
            _keys_exact(
                idempotency,
                {
                    "job_identity_derivation",
                    "lock_operation_derivation",
                    "replay_returns_existing_decision",
                    "replay_advances_fencing_token",
                    "same_idempotency_key_different_input_action",
                },
            )
            and idempotency.get("job_identity_derivation")
            == "SHA256_TASK_INPUT_JOB_TYPE"
            and idempotency.get("lock_operation_derivation")
            == "SHA256_JOB_ATTEMPT_LOCK_KEY"
            and idempotency.get("replay_returns_existing_decision") is True
            and idempotency.get("replay_advances_fencing_token") is False
            and idempotency.get("same_idempotency_key_different_input_action")
            == "REJECT_CONFLICT"
        ),
        "acquisition_fail_closed": (
            _keys_exact(
                acquisition,
                {
                    "compare_and_set_fields",
                    "multi_lock_atomicity",
                    "partial_lock_retention_allowed",
                    "canonical_order_required",
                    "unknown_evidence_action",
                    "conflict_action",
                    "deadlock_prevention",
                },
            )
            and acquisition.get("compare_and_set_fields")
            == ["lock_key", "expected_lock_version", "expected_fencing_token"]
            and acquisition.get("multi_lock_atomicity") == "ALL_OR_NONE_CAS"
            and acquisition.get("partial_lock_retention_allowed") is False
            and acquisition.get("canonical_order_required") is True
            and acquisition.get("unknown_evidence_action")
            == "REQUIRE_MANUAL_REVIEW"
            and acquisition.get("conflict_action")
            == "PAUSE_BEFORE_QUEUE_ADMISSION"
            and acquisition.get("deadlock_prevention")
            == "CANONICAL_ORDER_AND_ALL_OR_NONE"
        ),
        "lease_fail_closed": (
            _keys_exact(
                lease,
                {
                    "single_active_holder_per_lock_key",
                    "renewal_requires_same_holder_attempt_and_token",
                    "renewal_requires_unexpired_live_lease",
                    "expiry_observation_alone_grants_lock",
                    "takeover_requires_expiry_evidence",
                    "takeover_atomically_advances_fence_and_version",
                    "clock_source_policy",
                    "unknown_or_stale_lease_action",
                },
            )
            and lease.get("single_active_holder_per_lock_key") is True
            and lease.get("renewal_requires_same_holder_attempt_and_token") is True
            and lease.get("renewal_requires_unexpired_live_lease") is True
            and lease.get("expiry_observation_alone_grants_lock") is False
            and lease.get("takeover_requires_expiry_evidence") is True
            and lease.get("takeover_atomically_advances_fence_and_version") is True
            and lease.get("clock_source_policy") == "DEFERRED_TO_PHASE2"
            and lease.get("unknown_or_stale_lease_action")
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "fencing_fail_closed": (
            _keys_exact(
                fencing,
                {
                    "token_monotonic",
                    "guarded_commit_surfaces",
                    "stale_holder_commit_allowed",
                    "stale_holder_release_allowed",
                    "missing_token_action",
                    "token_regression_action",
                    "commit_requires_current_lock_version",
                },
            )
            and fencing.get("token_monotonic") is True
            and fencing.get("guarded_commit_surfaces")
            == ["output", "job_state", "checkpoint", "evidence"]
            and fencing.get("stale_holder_commit_allowed") is False
            and fencing.get("stale_holder_release_allowed") is False
            and fencing.get("missing_token_action") == "REJECT_COMMIT"
            and fencing.get("token_regression_action")
            == "REJECT_AND_REQUIRE_MANUAL_REVIEW"
            and fencing.get("commit_requires_current_lock_version") is True
        ),
        "release_fail_closed": (
            _keys_exact(
                release,
                {
                    "matching_identity_token_release_idempotent",
                    "release_requires_holder_job_attempt",
                    "release_requires_current_fencing_token",
                    "stale_release_action",
                    "terminal_release_requires_audit_ref",
                    "implicit_release_allowed",
                },
            )
            and release.get("matching_identity_token_release_idempotent") is True
            and release.get("release_requires_holder_job_attempt") is True
            and release.get("release_requires_current_fencing_token") is True
            and release.get("stale_release_action") == "REJECT_STALE_RELEASE"
            and release.get("terminal_release_requires_audit_ref") is True
            and release.get("implicit_release_allowed") is False
        ),
        "conflict_and_retry_safe": (
            _keys_exact(
                conflict,
                {
                    "result_code",
                    "queue_record_created",
                    "operation_invoked",
                    "retry_budget_consumed",
                    "partial_lock_retained",
                    "status_projection",
                    "active_conflict_terminal_mutation_allowed",
                },
            )
            and conflict.get("result_code") == "RESOURCE_CONFLICT_ACTIVE"
            and conflict.get("queue_record_created") is False
            and conflict.get("operation_invoked") is False
            and conflict.get("retry_budget_consumed") is False
            and conflict.get("partial_lock_retained") is False
            and conflict.get("status_projection") == "等待资源锁"
            and conflict.get("active_conflict_terminal_mutation_allowed") is False
            and _keys_exact(
                retry,
                {
                    "lock_conflict_consumes_retry",
                    "lease_expiry_observation_consumes_retry",
                    "retry_policy_runtime_owner",
                    "retry_scheduler_performed",
                },
            )
            and retry.get("lock_conflict_consumes_retry") is False
            and retry.get("lease_expiry_observation_consumes_retry") is False
            and retry.get("retry_policy_runtime_owner") == "STAGE-039"
            and retry.get("retry_scheduler_performed") is False
        ),
        "parameters_deferred": (
            _keys_exact(
                parameters,
                {
                    "numeric_values_assigned",
                    "deferred_parameters",
                    "phase2_selection_requirements",
                    "implicit_default_allowed",
                    "production_calibrated",
                },
            )
            and parameters.get("numeric_values_assigned") is False
            and parameters.get("deferred_parameters") == DEFERRED_PARAMETERS
            and parameters.get("phase2_selection_requirements")
            == [
                "source",
                "rationale",
                "unit",
                "policy_version",
                "validation_evidence",
                "rollback",
            ]
            and parameters.get("implicit_default_allowed") is False
            and parameters.get("production_calibrated") is False
        ),
        "later_stage_boundaries_preserved": (
            _keys_exact(
                backpressure,
                {
                    "policy_owner",
                    "resource_signals",
                    "resource_signal_effect",
                    "automatic_resume_allowed",
                    "automatic_resume_runtime_owner",
                    "backpressure_runtime_performed",
                },
            )
            and backpressure.get("policy_owner") == "STAGE-040"
            and backpressure.get("resource_signals")
            == [
                "EXTERNAL_DRIVE_OFFLINE",
                "DISK_SPACE_INSUFFICIENT",
                "EXTERNAL_API_BUDGET_INSUFFICIENT",
            ]
            and backpressure.get("resource_signal_effect")
            == "LEGAL_PAUSE_CANDIDATE_ONLY"
            and backpressure.get("automatic_resume_allowed") is False
            and backpressure.get("automatic_resume_runtime_owner") == "STAGE-042"
            and backpressure.get("backpressure_runtime_performed") is False
            and _keys_exact(
                cleanup,
                {
                    "runtime_owner",
                    "cleanup_candidate_requires_allowlist",
                    "cleanup_runtime_performed",
                    "protected_artifact_delete_allowed",
                    "protected_artifact_classes",
                },
            )
            and cleanup.get("runtime_owner") == "STAGE-044"
            and cleanup.get("cleanup_candidate_requires_allowlist") is True
            and cleanup.get("cleanup_runtime_performed") is False
            and cleanup.get("protected_artifact_delete_allowed") is False
            and cleanup.get("protected_artifact_classes")
            == [
                "FACT_SOURCE",
                "MANIFEST",
                "EVIDENCE_LEDGER",
                "AUDIT_LOG",
                "REPORT_SNAPSHOT",
            ]
            and _keys_exact(
                ownership,
                {
                    "job_state_model",
                    "queue_and_worker_transport",
                    "retry_and_dead_letter_policy",
                    "backpressure_decision_policy",
                    "lock_lease_and_fencing_runtime",
                    "automatic_resume_runtime",
                    "crash_recovery_runtime",
                    "cleanup_execution_runtime",
                },
            )
            and ownership.get("job_state_model") == "STAGE-037"
            and ownership.get("queue_and_worker_transport") == "STAGE-038"
            and ownership.get("retry_and_dead_letter_policy") == "STAGE-039"
            and ownership.get("backpressure_decision_policy") == "STAGE-040"
            and ownership.get("lock_lease_and_fencing_runtime") == "STAGE-041"
            and ownership.get("automatic_resume_runtime") == "STAGE-042"
            and ownership.get("crash_recovery_runtime") == "STAGE-043"
            and ownership.get("cleanup_execution_runtime") == "STAGE-044"
        ),
        "human_status_projection_valid": (
            _keys_exact(
                human_status,
                {
                    "ACQUIRED",
                    "RESOURCE_CONFLICT_ACTIVE",
                    "STALE_FENCING_TOKEN",
                    "UNKNOWN_OR_STALE_EVIDENCE",
                    "RUNTIME_DISABLED",
                },
            )
            and human_status
            == {
                "ACQUIRED": "已获取资源锁",
                "RESOURCE_CONFLICT_ACTIVE": "等待资源锁",
                "STALE_FENCING_TOKEN": "锁凭证已失效",
                "UNKNOWN_OR_STALE_EVIDENCE": "需人工复核",
                "RUNTIME_DISABLED": "锁运行时未启用",
            }
        ),
        "phase2_gate_exact": (
            _keys_exact(
                phase2,
                {
                    "entry_authorized",
                    "required_task_id",
                    "required_gate",
                    "separate_run_required",
                    "required_work",
                },
            )
            and phase2.get("entry_authorized") is True
            and phase2.get("required_task_id") == "IDS-V0_1-STAGE041-P2"
            and phase2.get("required_gate") == "IDS-STAGE041-P2-GATE"
            and phase2.get("separate_run_required") is True
            and phase2.get("required_work")
            == [
                "source and register every numeric parameter",
                "implement one isolated non-production lock decision slice",
                "prove acquire renew release takeover and fencing behavior",
                "preserve Stage038 conflict behavior",
                "keep persistence and production activation disabled",
            ]
        ),
        "truth_flags_exact": (
            _keys_exact(truth, FALSE_TRUTH_FLAGS | {"taskpack_source_read_performed"})
            and truth.get("taskpack_source_read_performed") is True
            and all(truth.get(key) is False for key in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def build_stage041_phase1_report(
    project_root: Path | None = None,
) -> dict[str, Any]:
    project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    contract_path = project_root / CONTRACT_RELATIVE
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    checks = evaluate_contract(contract, project_root)
    truth = contract.get("truth_flags", {})
    return {
        "schema_version": "ids.stage041.lock_registry.phase1.report.v1",
        "stage": "STAGE-041",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE041-P1",
        "acceptance_id": "ACC-STAGE-041",
        "contract_state": contract.get("contract_state"),
        "next_gate": contract.get("next_gate"),
        "phase1_contract_valid": bool(checks) and all(checks.values()),
        "contract_checks": checks,
        **{key: truth.get(key, False) for key in sorted(FALSE_TRUTH_FLAGS)},
    }


def main() -> int:
    report = build_stage041_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["phase1_contract_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
