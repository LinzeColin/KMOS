#!/usr/bin/env python3
"""Run and validate the STAGE-041 Phase 2 isolated lock registry slice."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Mapping, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
CONTRACT_PATH = (
    PROJECT_ROOT
    / "docs/pursuing_goal/ids_v0_1/lock_registry/"
    "stage041_lock_registry_runtime_contract.json"
)
POLICY_VERSION = "ids.lock_registry_policy.v0_1.stage041.p2"
TASK_ID = "IDS-V0_1-STAGE041-P2"
ACCEPTANCE_ID = "ACC-STAGE-041"
PRODUCTION_CALIBRATION_TASK_ID = "TASK-" + "OP" + "ME-B-001"
CONTROL_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
)
AUDIT_REF = (
    "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md#Controlled-Evidence"
)
EXPECTED_PARAMETERS = {
    "lease_duration_seconds": 30,
    "renewal_interval_seconds": 10,
    "expiry_grace_seconds": 5,
    "acquisition_timeout_seconds": 1,
    "maximum_wait_seconds": 0,
    "retry_jitter_seconds": 0,
    "deadlock_timeout_seconds": 1,
}
EXPECTED_PARAMETER_RELATIONSHIPS = [
    "lease_duration_seconds == 3 * renewal_interval_seconds",
    "0 < expiry_grace_seconds < renewal_interval_seconds < lease_duration_seconds",
    "acquisition_timeout_seconds == deadlock_timeout_seconds",
    "maximum_wait_seconds == 0",
    "retry_jitter_seconds == 0",
]
EXPECTED_OPERATION_SCOPES = {
    "FILE_PROCESSING": {
        "job_types": ["PARSE"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "FILE_PROCESSING"],
    },
    "ARCHIVE_EXTRACTION": {
        "job_types": ["ARCHIVE"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "ARCHIVE_EXTRACTION"],
    },
    "INDEX_BUILD": {
        "job_types": ["INDEX"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "INDEX_BUILD"],
    },
    "INDEX_SWITCH": {
        "job_types": ["INDEX"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "INDEX_SWITCH"],
    },
    "REPORT_GENERATION": {
        "job_types": ["REPORT"],
        "required_lock_namespaces": ["SOURCE_PIPELINE", "REPORT_GENERATION"],
    },
}
EXPECTED_UPSTREAM = {
    "phase1_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_contract.json",
        "52e445bd581fb32c23887a290b656f72fb1fe123119255019f9e5bc65fe9beb5",
    ),
    "phase1_checker": (
        "KM_IDSystem/scripts/check_lock_registry.py",
        "11e20b3fb4ad2e15500053c8ff0284183c4d880601e6edf9095f2f49bc8d05de",
    ),
    "phase1_boundary": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md",
        "526c8f7c1b71ad342535f3bc36db7ad79a9d203737c977089ac33cd301077c34",
    ),
    "stage038_conflict_scenarios": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_queue_baseline/"
        "stage038_worker_queue_scenarios.json",
        "0ec9f1a0de6ec24d64d4108214ea426f9171b15eebdd6c3c60693fade62f2961",
    ),
    "stage039_retry_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/retry_dead_letter/"
        "stage039_retry_dead_letter_runtime_contract.json",
        "5fc9b49b0ede0fdbc87311f3280ffc69e8ec8e59f219b17a04a2ccae1e9124c0",
    ),
    "stage040_backpressure_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_runtime_contract.json",
        "2970ebd143030821d9a8b00e4fdb11342f8f82ef3bcf4d91717ba707b5054e2e",
    ),
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
        "STAGE-041_锁注册与竞态控制.md"
    ),
    "source_member_match_count": 1,
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
REQUEST_FIELDS = {
    "resource_identity_ref",
    "operation_family",
    "holder_job_id",
    "holder_attempt_id",
    "lease_owner_ref",
    "requested_at_epoch_seconds",
    "input_refs",
    "idempotency_key",
    "policy_version",
}
RECORD_FIELDS = {
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
}
FALSE_TRUTH_FLAGS = {
    "queue_runtime_performed",
    "worker_runtime_performed",
    "retry_scheduler_performed",
    "automatic_resume_performed",
    "crash_recovery_runtime_performed",
    "cleanup_runtime_performed",
    "database_connection_performed",
    "persistent_lock_write_performed",
    "state_registry_write_performed",
    "runtime_output_written",
    "external_api_call_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "production_runtime_activation_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}
TRUE_TRUTH_FLAGS = {
    "parameter_values_assigned",
    "isolated_lock_decision_runtime_performed",
    "actual_control_ref_verified",
    "acquire_evaluation_performed",
    "renew_evaluation_performed",
    "release_evaluation_performed",
    "takeover_evaluation_performed",
    "fencing_evaluation_performed",
}


def _canonical_digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        encoded = b"INVALID_NON_JSON_CONTROL_METADATA"
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keys_exact(value: Any, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _version_map_exact(value: Any, lock_keys: list[str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(lock_keys)
        and all(type(value[key]) is int and value[key] > 0 for key in lock_keys)
    )


def _git_tracked(relative: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _repo_relative_ref(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.startswith("repo:"):
        return None
    if "\\" in value or len(value) > 512:
        return None
    relative = value.removeprefix("repo:")
    pure = PurePosixPath(relative)
    normalized = pure.as_posix()
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or not normalized.startswith("KM_IDSystem/")
        or "ids_metadata" in normalized.lower()
    ):
        return None
    path = REPO_ROOT / normalized
    if not path.is_file() or not _git_tracked(normalized):
        return None
    return normalized


def _upstream_valid(contract: Mapping[str, Any]) -> bool:
    bindings = contract.get("upstream_bindings")
    if not isinstance(bindings, dict) or set(bindings) != set(EXPECTED_UPSTREAM):
        return False
    for name, (relative, expected_hash) in EXPECTED_UPSTREAM.items():
        if bindings.get(name) != {"ref": relative, "sha256": expected_hash}:
            return False
        path = REPO_ROOT / relative
        if not path.is_file() or _sha256(path) != expected_hash:
            return False
    return True


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Stage041 Phase2 contract must be an object")
    return value


def evaluate_contract(contract: Any) -> dict[str, bool]:
    """Validate the complete contract shape; unknown nested fields fail closed."""
    if not isinstance(contract, dict):
        return {"contract_is_object": False}
    policy = contract.get("policy")
    scope = contract.get("operation_scope_contract")
    request = contract.get("request_contract")
    decision = contract.get("decision_contract")
    record = contract.get("registry_record_contract")
    control = contract.get("control_metadata_contract")
    projection = contract.get("human_status_projection")
    binding = contract.get("registry_binding")
    runtime = contract.get("runtime_boundary")
    rollback = contract.get("rollback")
    truth = contract.get("truth_flags")
    root_keys = {
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
        "upstream_bindings",
        "policy",
        "operation_scope_contract",
        "request_contract",
        "decision_contract",
        "registry_record_contract",
        "control_metadata_contract",
        "human_status_projection",
        "registry_binding",
        "runtime_boundary",
        "rollback",
        "truth_flags",
    }
    expected_policy_keys = {
        "policy_version",
        "parameters",
        "parameter_provenance",
        "parameter_relationships",
        "logical_clock_only",
        "wall_clock_sleep_allowed",
        "parameter_source",
        "fact_level",
        "production_calibrated",
        "production_calibration_required",
        "production_calibration_task_id",
        "rollback_policy",
    }
    provenance_keys = {
        "unit",
        "source",
        "rationale",
        "policy_version",
        "validation_evidence",
        "rollback",
    }
    scope_valid = scope == EXPECTED_OPERATION_SCOPES
    parameters = policy.get("parameters") if isinstance(policy, dict) else None
    provenance = (
        policy.get("parameter_provenance") if isinstance(policy, dict) else None
    )
    parameters_valid = parameters == EXPECTED_PARAMETERS
    provenance_valid = (
        isinstance(provenance, dict)
        and set(provenance) == set(EXPECTED_PARAMETERS)
        and all(_keys_exact(item, provenance_keys) for item in provenance.values())
        and all(item["unit"] == "seconds" for item in provenance.values())
        and all(item["policy_version"] == POLICY_VERSION for item in provenance.values())
        and all(
            isinstance(item[field], str) and bool(item[field].strip())
            for item in provenance.values()
            for field in ("source", "rationale", "validation_evidence", "rollback")
        )
        and all(
            item["rollback"]
            == "DISABLE_ISOLATED_LOCK_RUNTIME_REQUIRE_MANUAL_REVIEW"
            for item in provenance.values()
        )
    )
    projections = {
        "ACQUIRED",
        "RENEWED",
        "RELEASED",
        "PAUSE_BEFORE_QUEUE_ADMISSION",
        "REJECT_COMMIT",
        "COMMIT_ALLOWED",
        "REQUIRE_MANUAL_REVIEW",
    }
    projection_valid = isinstance(projection, dict) and set(projection) == projections
    if projection_valid:
        projection_valid = all(
            _keys_exact(
                item,
                {"label_zh", "owner_action_zh", "owner_attention_required"},
            )
            and isinstance(item["label_zh"], str)
            and isinstance(item["owner_action_zh"], str)
            and isinstance(item["owner_attention_required"], bool)
            for item in projection.values()
        )
    checks = {
        "root_schema_exact": _keys_exact(contract, root_keys),
        "identity_exact": (
            contract.get("schema_version") == "ids.stage041.lock_registry.phase2.v1"
            and contract.get("stage") == "STAGE-041"
            and contract.get("phase") == "Phase 2"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_LOCK_DECISION_SLICE"
            and contract.get("policy_contract_id") == POLICY_VERSION
            and contract.get("contract_state")
            == "PHASE2_ISOLATED_LOCK_DECISION_SLICE_ENABLED_PRODUCTION_DISABLED"
            and contract.get("next_gate") == "IDS-STAGE041-P3-GATE"
        ),
        "source_binding_exact": contract.get("source_binding") == EXPECTED_SOURCE,
        "upstream_bindings_current": _upstream_valid(contract),
        "policy_schema_exact": _keys_exact(policy, expected_policy_keys),
        "parameters_exact": parameters_valid,
        "parameter_provenance_complete": provenance_valid,
        "parameter_relationships_exact": (
            isinstance(policy, dict)
            and policy.get("parameter_relationships")
            == EXPECTED_PARAMETER_RELATIONSHIPS
        ),
        "parameter_policy_metadata_exact": (
            isinstance(policy, dict)
            and policy.get("parameter_source")
            == "STAGE041_PHASE2_LOCAL_ENGINEERING_SAFETY_BOUNDARY"
            and policy.get("rollback_policy")
            == "DISABLE_ISOLATED_LOCK_RUNTIME_REQUIRE_MANUAL_REVIEW"
        ),
        "parameter_bounds_valid": (
            parameters_valid
            and parameters["lease_duration_seconds"]
            == 3 * parameters["renewal_interval_seconds"]
            and 0
            < parameters["expiry_grace_seconds"]
            < parameters["renewal_interval_seconds"]
            < parameters["lease_duration_seconds"]
            and parameters["acquisition_timeout_seconds"]
            == parameters["deadlock_timeout_seconds"]
            and parameters["maximum_wait_seconds"] == 0
            and parameters["retry_jitter_seconds"] == 0
        ),
        "parameter_truth_bounded": (
            isinstance(policy, dict)
            and policy.get("policy_version") == POLICY_VERSION
            and policy.get("logical_clock_only") is True
            and policy.get("wall_clock_sleep_allowed") is False
            and policy.get("fact_level") == "PROPOSED"
            and policy.get("production_calibrated") is False
            and policy.get("production_calibration_required") is True
            and policy.get("production_calibration_task_id")
            == PRODUCTION_CALIBRATION_TASK_ID
        ),
        "operation_scope_exact": scope_valid,
        "request_contract_exact": request
        == {
            "required_fields": [
                "resource_identity_ref",
                "operation_family",
                "holder_job_id",
                "holder_attempt_id",
                "lease_owner_ref",
                "requested_at_epoch_seconds",
                "input_refs",
                "idempotency_key",
                "policy_version",
            ],
            "reference_only": True,
            "raw_path_allowed": False,
            "raw_payload_allowed": False,
            "requested_at_must_be_non_negative": True,
            "logical_time_regression_action": "REQUIRE_MANUAL_REVIEW",
            "renewal_must_strictly_extend_expiry": True,
            "release_requires_live_lease": True,
            "unknown_field_action": "REQUIRE_MANUAL_REVIEW",
        },
        "decision_contract_exact": decision
        == {
            "acquire": "CANONICAL_ALL_OR_NONE_CAS",
            "renew": "MATCHING_LIVE_HOLDER_VERSION_ADVANCE_NO_FENCE_ADVANCE",
            "takeover": "EXPECTED_CAS_EVIDENCE_EXPIRY_PLUS_GRACE_ATOMIC_FENCE_AND_VERSION_ADVANCE",
            "commit": "CURRENT_HOLDER_FENCE_VERSION_AND_LIVE_LEASE_REQUIRED",
            "release": "MATCHING_HOLDER_FENCE_VERSION_TOMBSTONE_ADVANCE_IDEMPOTENT",
            "idempotency": "SAME_OPERATION_KEY_SAME_INPUT_REPLAY_DIFFERENT_INPUT_REJECT",
            "contention": "PAUSE_BEFORE_QUEUE_ADMISSION_NO_RETRY_NO_PARTIAL_LOCK",
            "unknown_or_invalid": "REQUIRE_MANUAL_REVIEW",
        },
        "registry_record_contract_exact": record
        == {
            "required_fields": [
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
            ],
            "registry_mode": "IN_MEMORY_CONTROL_METADATA_ONLY",
            "canonical_key_order_required": True,
            "partial_record_retention_allowed": False,
            "persistent_write_allowed": False,
        },
        "control_metadata_exact": control
        == {
            "input_refs": [CONTROL_REF],
            "input_refs_must_be_git_tracked": True,
            "raw_body_allowed": False,
            "output_refs": [],
            "checkpoint_ref_format": (
                "checkpoint:sha256:<canonical-decision-digest>"
            ),
            "error_ref_format": "error:<safe-control-reason-code>",
            "audit_ref": AUDIT_REF,
        },
        "control_ref_real_and_tracked": _repo_relative_ref(CONTROL_REF) is not None,
        "human_status_projection_exact": projection_valid,
        "registry_binding_exact": binding
        == {
            "model_id": "MOD-010",
            "formula_id": "FORM-010",
            "parameter_ids": [f"PARAM-{value:03d}" for value in range(65, 72)],
            "production_calibration_task_id": PRODUCTION_CALIBRATION_TASK_ID,
        },
        "runtime_boundary_exact": _keys_exact(
            runtime,
            {
                "isolated_lock_decision_runtime_allowed",
                "logical_clock_evaluation_allowed",
                "wall_clock_sleep_allowed",
                "queue_runtime_allowed",
                "worker_runtime_allowed",
                "retry_scheduler_allowed",
                "automatic_resume_allowed",
                "crash_recovery_allowed",
                "cleanup_runtime_allowed",
                "database_allowed",
                "persistent_lock_write_allowed",
                "state_registry_write_allowed",
                "runtime_output_write_allowed",
                "external_api_allowed",
                "raw_metadata_access_allowed",
                "ids_business_job_allowed",
                "fake_ids_business_data_allowed",
                "production_activation_allowed",
            },
        )
        and runtime.get("isolated_lock_decision_runtime_allowed") is True
        and runtime.get("logical_clock_evaluation_allowed") is True
        and all(
            runtime.get(name) is False
            for name in set(runtime)
            - {
                "isolated_lock_decision_runtime_allowed",
                "logical_clock_evaluation_allowed",
            }
        ),
        "rollback_exact": rollback
        == {
            "trigger": "INVALID_CONTRACT_PARAMETER_REQUEST_LEASE_OR_FENCE_EVIDENCE",
            "action": (
                "DISABLE_ISOLATED_LOCK_RUNTIME_REQUIRE_MANUAL_REVIEW_"
                "AND_REVERT_PHASE2_FILES_ONLY"
            ),
            "preserve_phase1": True,
            "preserve_stage037_stage040": True,
            "preserve_source_and_evidence": True,
            "github_action_allowed": False,
        },
        "truth_flags_exact": (
            _keys_exact(truth, TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS)
            and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def build_control_request(
    resource_identity_ref: str,
    *,
    operation_family: str,
    holder_role: str,
    requested_at_epoch_seconds: int,
) -> dict[str, Any]:
    """Create deterministic control metadata from a real repository reference."""
    identity = _canonical_digest(
        {
            "resource_identity_ref": resource_identity_ref,
            "operation_family": operation_family,
            "holder_role": holder_role,
        }
    )
    operation_identity = _canonical_digest(
        {
            "holder_identity": identity,
            "requested_at_epoch_seconds": requested_at_epoch_seconds,
        }
    )
    return {
        "resource_identity_ref": resource_identity_ref,
        "operation_family": operation_family,
        "holder_job_id": f"control-job:{identity[:24]}",
        "holder_attempt_id": f"control-attempt:{identity[24:48]}",
        "lease_owner_ref": f"control-owner:{holder_role}",
        "requested_at_epoch_seconds": requested_at_epoch_seconds,
        "input_refs": [resource_identity_ref],
        "idempotency_key": f"idempotency:sha256:{operation_identity}",
        "policy_version": POLICY_VERSION,
    }


class IsolatedLockRegistry:
    """A deterministic process-local registry with no persistence or waiting."""

    def __init__(self, contract: Mapping[str, Any]):
        self.contract = copy.deepcopy(dict(contract))
        self.contract_valid = all(evaluate_contract(self.contract).values())
        self.parameters = self.contract.get("policy", {}).get("parameters", {})
        self.scopes = self.contract.get("operation_scope_contract", {})
        self.projections = self.contract.get("human_status_projection", {})
        self._locks: dict[str, dict[str, Any]] = {}
        self._lock_versions: dict[str, int] = {}
        self._fencing_counter = 0
        self._operation_ledger: dict[str, dict[str, Any]] = {}
        self._operation_fingerprints: dict[str, str] = {}

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(
            {
                "locks": self._locks,
                "lock_versions": self._lock_versions,
                "fencing_counter": self._fencing_counter,
                "operation_ledger_size": len(self._operation_ledger),
            }
        )

    def _request_valid(self, request: Any) -> bool:
        if not self.contract_valid or not _keys_exact(request, REQUEST_FIELDS):
            return False
        if request.get("policy_version") != POLICY_VERSION:
            return False
        if request.get("operation_family") not in self.scopes:
            return False
        if _repo_relative_ref(request.get("resource_identity_ref")) is None:
            return False
        if request.get("input_refs") != [request.get("resource_identity_ref")]:
            return False
        if not isinstance(request.get("requested_at_epoch_seconds"), int):
            return False
        if isinstance(request.get("requested_at_epoch_seconds"), bool):
            return False
        if request["requested_at_epoch_seconds"] < 0:
            return False
        for name in (
            "holder_job_id",
            "holder_attempt_id",
            "lease_owner_ref",
            "idempotency_key",
        ):
            value = request.get(name)
            if not isinstance(value, str) or not value or len(value) > 256:
                return False
        return (
            re.fullmatch(
                r"idempotency:sha256:[0-9a-f]{64}",
                request["idempotency_key"],
            )
            is not None
        )

    def _lock_keys(self, request: Mapping[str, Any]) -> list[str]:
        resource_digest = _canonical_digest(request["resource_identity_ref"])
        namespaces = self.scopes[request["operation_family"]][
            "required_lock_namespaces"
        ]
        return sorted(f"{name}:{resource_digest}" for name in namespaces)

    def _ledger_key(
        self,
        operation: str,
        request: Mapping[str, Any],
    ) -> str:
        return _canonical_digest(
            {
                "operation": operation,
                "idempotency_key": request["idempotency_key"],
            }
        )

    def _operation_fingerprint(
        self,
        operation: str,
        request: Mapping[str, Any],
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> str:
        return _canonical_digest(
            {"operation": operation, "request": request, "evidence": evidence}
        )

    def _human_status(self, decision_action: str) -> dict[str, Any]:
        return copy.deepcopy(
            self.projections.get(
                decision_action,
                {
                    "label_zh": "等待人工复核",
                    "owner_action_zh": "检查请求、租约与 fencing 证据",
                    "owner_attention_required": True,
                },
            )
        )

    def _result(
        self,
        operation: str,
        request: Optional[Mapping[str, Any]],
        *,
        result_code: str,
        decision_action: str,
        lock_keys: Optional[list[str]] = None,
        fencing_token: Optional[int] = None,
        lock_versions: Optional[dict[str, int]] = None,
        lease_expires_at: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> dict[str, Any]:
        safe_request = request if self._request_valid(request) else None
        result = {
            "operation": operation,
            "decision_valid": safe_request is not None,
            "result_code": result_code,
            "decision_action": decision_action,
            "holder_job_id": (
                safe_request.get("holder_job_id") if safe_request else None
            ),
            "holder_attempt_id": (
                safe_request.get("holder_attempt_id") if safe_request else None
            ),
            "lease_owner_ref": (
                safe_request.get("lease_owner_ref") if safe_request else None
            ),
            "lock_keys": list(lock_keys or []),
            "fencing_token": fencing_token,
            "lock_versions": copy.deepcopy(lock_versions or {}),
            "lease_expires_at": lease_expires_at,
            "input_refs": list(safe_request.get("input_refs", [])) if safe_request else [],
            "output_refs": [],
            "error_ref": f"error:{error_code}" if error_code else None,
            "audit_ref": AUDIT_REF,
            "human_status": self._human_status(decision_action),
            "queue_record_created": False,
            "retry_budget_consumed": False,
            "partial_lock_retained": False,
            "persistent_write_performed": False,
        }
        result["checkpoint_ref"] = (
            f"checkpoint:sha256:{_canonical_digest(result)}"
        )
        return result

    def _invalid(self, operation: str) -> dict[str, Any]:
        return self._result(
            operation,
            None,
            result_code="INVALID_CONTROL_REQUEST",
            decision_action="REQUIRE_MANUAL_REVIEW",
            error_code="INVALID_CONTROL_REQUEST",
        )

    def _ledger_replay_or_conflict(
        self,
        operation: str,
        request: Mapping[str, Any],
        evidence: Optional[Mapping[str, Any]] = None,
    ) -> tuple[str, str, Optional[dict[str, Any]]]:
        ledger_key = self._ledger_key(operation, request)
        fingerprint = self._operation_fingerprint(operation, request, evidence)
        existing = self._operation_ledger.get(ledger_key)
        if existing is None:
            return ledger_key, fingerprint, None
        if self._operation_fingerprints.get(ledger_key) != fingerprint:
            return (
                ledger_key,
                fingerprint,
                self._result(
                    operation,
                    request,
                    result_code="IDEMPOTENCY_INPUT_CONFLICT",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=self._lock_keys(request),
                    error_code="IDEMPOTENCY_INPUT_CONFLICT",
                ),
            )
        return ledger_key, fingerprint, copy.deepcopy(existing)

    def _record_operation(
        self,
        ledger_key: str,
        fingerprint: str,
        result: Mapping[str, Any],
    ) -> None:
        self._operation_fingerprints[ledger_key] = fingerprint
        self._operation_ledger[ledger_key] = copy.deepcopy(dict(result))

    def _current_matches(
        self,
        request: Mapping[str, Any],
        evidence: Mapping[str, Any],
        lock_keys: list[str],
    ) -> bool:
        if not isinstance(evidence, Mapping):
            return False
        expected_versions = evidence.get("lock_versions")
        if (
            not _version_map_exact(expected_versions, lock_keys)
            or evidence.get("lock_keys") != lock_keys
            or not isinstance(evidence.get("fencing_token"), int)
            or isinstance(evidence.get("fencing_token"), bool)
        ):
            return False
        for key in lock_keys:
            record = self._locks.get(key)
            if not record or not _keys_exact(record, RECORD_FIELDS):
                return False
            if (
                record["holder_job_id"] != request["holder_job_id"]
                or record["holder_attempt_id"] != request["holder_attempt_id"]
                or record["lease_owner_ref"] != request["lease_owner_ref"]
                or record["fencing_token"] != evidence.get("fencing_token")
                or record["lock_version"] != expected_versions.get(key)
            ):
                return False
        return True

    def _takeover_evidence_matches(
        self,
        evidence: Mapping[str, Any],
        lock_keys: list[str],
    ) -> bool:
        if not isinstance(evidence, Mapping):
            return False
        expected_versions = evidence.get("lock_versions")
        if (
            not _version_map_exact(expected_versions, lock_keys)
            or evidence.get("lock_keys") != lock_keys
            or not isinstance(evidence.get("fencing_token"), int)
            or isinstance(evidence.get("fencing_token"), bool)
        ):
            return False
        return all(
            (record := self._locks.get(key)) is not None
            and _keys_exact(record, RECORD_FIELDS)
            and record["fencing_token"] == evidence["fencing_token"]
            and record["lock_version"] == expected_versions[key]
            for key in lock_keys
        )

    def _latest_record_time(self, lock_keys: list[str]) -> int:
        return max(
            max(
                record["acquired_at"],
                record["renewed_at"]
                if isinstance(record["renewed_at"], int)
                else record["acquired_at"],
            )
            for key in lock_keys
            if (record := self._locks.get(key)) is not None
        )

    def acquire(self, request: Mapping[str, Any]) -> dict[str, Any]:
        operation = "ACQUIRE"
        if not self._request_valid(request):
            return self._invalid(operation)
        ledger_key, fingerprint, replay = self._ledger_replay_or_conflict(
            operation, request
        )
        if replay is not None:
            return replay
        lock_keys = self._lock_keys(request)
        occupied = [key for key in lock_keys if key in self._locks]
        if occupied:
            result = self._result(
                operation,
                request,
                result_code="RESOURCE_CONFLICT_ACTIVE",
                decision_action="PAUSE_BEFORE_QUEUE_ADMISSION",
                lock_keys=lock_keys,
                error_code="RESOURCE_CONFLICT_ACTIVE",
            )
            self._record_operation(ledger_key, fingerprint, result)
            return result
        self._fencing_counter += 1
        now = request["requested_at_epoch_seconds"]
        lease_expires_at = now + self.parameters["lease_duration_seconds"]
        versions = {
            key: self._lock_versions.get(key, 0) + 1 for key in lock_keys
        }
        result = self._result(
            operation,
            request,
            result_code="LOCK_SET_ACQUIRED",
            decision_action="ACQUIRED",
            lock_keys=lock_keys,
            fencing_token=self._fencing_counter,
            lock_versions=versions,
            lease_expires_at=lease_expires_at,
        )
        for key in lock_keys:
            namespace = key.split(":", 1)[0]
            self._lock_versions[key] = versions[key]
            self._locks[key] = {
                "lock_key": key,
                "lock_namespace": namespace,
                "resource_identity_ref": request["resource_identity_ref"],
                "operation_scope": request["operation_family"],
                "holder_job_id": request["holder_job_id"],
                "holder_attempt_id": request["holder_attempt_id"],
                "lease_owner_ref": request["lease_owner_ref"],
                "lease_expires_at": lease_expires_at,
                "fencing_token": self._fencing_counter,
                "lock_version": versions[key],
                "acquired_at": now,
                "renewed_at": None,
                "released_at": None,
                "release_reason": None,
                "audit_ref": AUDIT_REF,
                "checkpoint_ref": result["checkpoint_ref"],
                "policy_version": POLICY_VERSION,
            }
        self._record_operation(ledger_key, fingerprint, result)
        return result

    def renew(
        self,
        request: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        operation = "RENEW"
        if not self._request_valid(request):
            return self._invalid(operation)
        ledger_key, fingerprint, replay = self._ledger_replay_or_conflict(
            operation, request, evidence
        )
        if replay is not None:
            return replay
        lock_keys = self._lock_keys(request)
        if not self._current_matches(request, evidence, lock_keys):
            result = self._result(
                operation,
                request,
                result_code="STALE_FENCING_TOKEN",
                decision_action="REQUIRE_MANUAL_REVIEW",
                lock_keys=lock_keys,
                error_code="STALE_FENCING_TOKEN",
            )
        else:
            now = request["requested_at_epoch_seconds"]
            current_expiry = min(self._locks[key]["lease_expires_at"] for key in lock_keys)
            if now < self._latest_record_time(lock_keys):
                result = self._result(
                    operation,
                    request,
                    result_code="NON_MONOTONIC_LOGICAL_TIME",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=lock_keys,
                    error_code="NON_MONOTONIC_LOGICAL_TIME",
                )
            elif now >= current_expiry:
                result = self._result(
                    operation,
                    request,
                    result_code="LEASE_EXPIRED",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=lock_keys,
                    error_code="LEASE_EXPIRED",
                )
            else:
                expiry = now + self.parameters["lease_duration_seconds"]
                if expiry <= current_expiry:
                    result = self._result(
                        operation,
                        request,
                        result_code="LEASE_NOT_EXTENDED",
                        decision_action="REQUIRE_MANUAL_REVIEW",
                        lock_keys=lock_keys,
                        error_code="LEASE_NOT_EXTENDED",
                    )
                else:
                    versions = {
                        key: self._locks[key]["lock_version"] + 1
                        for key in lock_keys
                    }
                    fence = self._locks[lock_keys[0]]["fencing_token"]
                    result = self._result(
                        operation,
                        request,
                        result_code="LEASE_RENEWED",
                        decision_action="RENEWED",
                        lock_keys=lock_keys,
                        fencing_token=fence,
                        lock_versions=versions,
                        lease_expires_at=expiry,
                    )
                    for key in lock_keys:
                        self._lock_versions[key] = versions[key]
                        self._locks[key]["lock_version"] = versions[key]
                        self._locks[key]["lease_expires_at"] = expiry
                        self._locks[key]["renewed_at"] = now
                        self._locks[key]["checkpoint_ref"] = result["checkpoint_ref"]
        self._record_operation(ledger_key, fingerprint, result)
        return result

    def takeover(
        self,
        request: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        operation = "TAKEOVER"
        if not self._request_valid(request):
            return self._invalid(operation)
        ledger_key, fingerprint, replay = self._ledger_replay_or_conflict(
            operation, request, evidence
        )
        if replay is not None:
            return replay
        lock_keys = self._lock_keys(request)
        records = [self._locks.get(key) for key in lock_keys]
        if any(record is None for record in records):
            result = self._result(
                operation,
                request,
                result_code="NO_LOCK_SET_TO_TAKEOVER",
                decision_action="REQUIRE_MANUAL_REVIEW",
                lock_keys=lock_keys,
                error_code="NO_LOCK_SET_TO_TAKEOVER",
            )
        elif not self._takeover_evidence_matches(evidence, lock_keys):
            result = self._result(
                operation,
                request,
                result_code="STALE_TAKEOVER_EVIDENCE",
                decision_action="REQUIRE_MANUAL_REVIEW",
                lock_keys=lock_keys,
                error_code="STALE_TAKEOVER_EVIDENCE",
            )
        else:
            now = request["requested_at_epoch_seconds"]
            takeover_at = max(record["lease_expires_at"] for record in records)
            takeover_at += self.parameters["expiry_grace_seconds"]
            if now < takeover_at:
                result = self._result(
                    operation,
                    request,
                    result_code="LEASE_NOT_TAKEOVER_ELIGIBLE",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=lock_keys,
                    error_code="LEASE_NOT_TAKEOVER_ELIGIBLE",
                )
            else:
                self._fencing_counter += 1
                expiry = now + self.parameters["lease_duration_seconds"]
                versions = {
                    key: self._lock_versions.get(key, 0) + 1 for key in lock_keys
                }
                result = self._result(
                    operation,
                    request,
                    result_code="TAKEOVER_ACQUIRED",
                    decision_action="ACQUIRED",
                    lock_keys=lock_keys,
                    fencing_token=self._fencing_counter,
                    lock_versions=versions,
                    lease_expires_at=expiry,
                )
                for key in lock_keys:
                    namespace = key.split(":", 1)[0]
                    self._lock_versions[key] = versions[key]
                    self._locks[key] = {
                        "lock_key": key,
                        "lock_namespace": namespace,
                        "resource_identity_ref": request["resource_identity_ref"],
                        "operation_scope": request["operation_family"],
                        "holder_job_id": request["holder_job_id"],
                        "holder_attempt_id": request["holder_attempt_id"],
                        "lease_owner_ref": request["lease_owner_ref"],
                        "lease_expires_at": expiry,
                        "fencing_token": self._fencing_counter,
                        "lock_version": versions[key],
                        "acquired_at": now,
                        "renewed_at": None,
                        "released_at": None,
                        "release_reason": None,
                        "audit_ref": AUDIT_REF,
                        "checkpoint_ref": result["checkpoint_ref"],
                        "policy_version": POLICY_VERSION,
                    }
        self._record_operation(ledger_key, fingerprint, result)
        return result

    def can_commit(
        self,
        request: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        operation = "CAN_COMMIT"
        if not self._request_valid(request):
            return self._invalid(operation)
        lock_keys = self._lock_keys(request)
        if not self._current_matches(request, evidence, lock_keys):
            return self._result(
                operation,
                request,
                result_code="STALE_FENCING_TOKEN",
                decision_action="REJECT_COMMIT",
                lock_keys=lock_keys,
                error_code="STALE_FENCING_TOKEN",
            )
        now = request["requested_at_epoch_seconds"]
        if now < self._latest_record_time(lock_keys):
            return self._result(
                operation,
                request,
                result_code="NON_MONOTONIC_LOGICAL_TIME",
                decision_action="REJECT_COMMIT",
                lock_keys=lock_keys,
                error_code="NON_MONOTONIC_LOGICAL_TIME",
            )
        if any(now >= self._locks[key]["lease_expires_at"] for key in lock_keys):
            return self._result(
                operation,
                request,
                result_code="LEASE_EXPIRED",
                decision_action="REJECT_COMMIT",
                lock_keys=lock_keys,
                error_code="LEASE_EXPIRED",
            )
        return self._result(
            operation,
            request,
            result_code="CURRENT_FENCE_VALID",
            decision_action="COMMIT_ALLOWED",
            lock_keys=lock_keys,
            fencing_token=evidence.get("fencing_token"),
            lock_versions=evidence.get("lock_versions"),
            lease_expires_at=min(
                self._locks[key]["lease_expires_at"] for key in lock_keys
            ),
        )

    def release(
        self,
        request: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        operation = "RELEASE"
        if not self._request_valid(request):
            return self._invalid(operation)
        ledger_key, fingerprint, replay = self._ledger_replay_or_conflict(
            operation, request, evidence
        )
        if replay is not None:
            return replay
        lock_keys = self._lock_keys(request)
        if not self._current_matches(request, evidence, lock_keys):
            result = self._result(
                operation,
                request,
                result_code="STALE_FENCING_TOKEN",
                decision_action="REQUIRE_MANUAL_REVIEW",
                lock_keys=lock_keys,
                error_code="STALE_FENCING_TOKEN",
            )
        else:
            now = request["requested_at_epoch_seconds"]
            current_expiry = min(
                self._locks[key]["lease_expires_at"] for key in lock_keys
            )
            if now < self._latest_record_time(lock_keys):
                result = self._result(
                    operation,
                    request,
                    result_code="NON_MONOTONIC_LOGICAL_TIME",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=lock_keys,
                    error_code="NON_MONOTONIC_LOGICAL_TIME",
                )
            elif now >= current_expiry:
                result = self._result(
                    operation,
                    request,
                    result_code="LEASE_EXPIRED",
                    decision_action="REQUIRE_MANUAL_REVIEW",
                    lock_keys=lock_keys,
                    error_code="LEASE_EXPIRED",
                )
            else:
                versions = {
                    key: self._locks[key]["lock_version"] + 1
                    for key in lock_keys
                }
                fence = self._locks[lock_keys[0]]["fencing_token"]
                result = self._result(
                    operation,
                    request,
                    result_code="LOCK_SET_RELEASED",
                    decision_action="RELEASED",
                    lock_keys=lock_keys,
                    fencing_token=fence,
                    lock_versions=versions,
                    lease_expires_at=None,
                )
                for key in lock_keys:
                    self._lock_versions[key] = versions[key]
                    del self._locks[key]
        self._record_operation(ledger_key, fingerprint, result)
        return result


def build_stage041_phase2_report() -> dict[str, Any]:
    contract = load_contract()
    contract_checks = evaluate_contract(contract)

    registry = IsolatedLockRegistry(contract)
    primary = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="primary",
        requested_at_epoch_seconds=1000,
    )
    acquired = registry.acquire(primary)
    acquire_snapshot = registry.snapshot()
    replay = registry.acquire(copy.deepcopy(primary))
    idempotency_before = registry.snapshot()
    changed_input = copy.deepcopy(primary)
    changed_input["requested_at_epoch_seconds"] = 1001
    idempotency_conflict = registry.acquire(changed_input)
    idempotency_after = registry.snapshot()
    contender = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="contender",
        requested_at_epoch_seconds=1001,
    )
    conflict = registry.acquire(contender)

    renew_registry = IsolatedLockRegistry(contract)
    renew_acquired = renew_registry.acquire(primary)
    renew_request = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="primary",
        requested_at_epoch_seconds=1010,
    )
    renewed = renew_registry.renew(renew_request, renew_acquired)
    renew_stale_commit = renew_registry.can_commit(
        build_control_request(
            CONTROL_REF,
            operation_family="FILE_PROCESSING",
            holder_role="primary",
            requested_at_epoch_seconds=1011,
        ),
        renew_acquired,
    )

    takeover_registry = IsolatedLockRegistry(contract)
    takeover_acquired = takeover_registry.acquire(primary)
    early_request = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="successor",
        requested_at_epoch_seconds=1034,
    )
    early = takeover_registry.takeover(early_request, takeover_acquired)
    successor = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="successor",
        requested_at_epoch_seconds=1035,
    )
    successor["idempotency_key"] = (
        "idempotency:sha256:"
        + _canonical_digest("successor-takeover-at-expiry-grace")
    )
    takeover = takeover_registry.takeover(successor, takeover_acquired)
    stale = takeover_registry.can_commit(
        build_control_request(
            CONTROL_REF,
            operation_family="FILE_PROCESSING",
            holder_role="primary",
            requested_at_epoch_seconds=1036,
        ),
        takeover_acquired,
    )
    current = takeover_registry.can_commit(
        build_control_request(
            CONTROL_REF,
            operation_family="FILE_PROCESSING",
            holder_role="successor",
            requested_at_epoch_seconds=1036,
        ),
        takeover,
    )

    takeover_cas_registry = IsolatedLockRegistry(contract)
    cas_acquired = takeover_cas_registry.acquire(primary)
    cas_renewed = takeover_cas_registry.renew(renew_request, cas_acquired)
    cas_successor = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="successor",
        requested_at_epoch_seconds=1045,
    )
    cas_before = takeover_cas_registry.snapshot()
    stale_takeover = takeover_cas_registry.takeover(cas_successor, cas_acquired)
    cas_after_stale = takeover_cas_registry.snapshot()
    cas_successor["idempotency_key"] = (
        "idempotency:sha256:"
        + _canonical_digest("successor-takeover-current-cas")
    )
    current_takeover = takeover_cas_registry.takeover(cas_successor, cas_renewed)

    release_registry = IsolatedLockRegistry(contract)
    release_acquired = release_registry.acquire(primary)
    release_request = build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role="primary",
        requested_at_epoch_seconds=1011,
    )
    released = release_registry.release(release_request, release_acquired)
    release_replay = release_registry.release(release_request, release_acquired)

    slice_checks = {
        "acquire_all_or_none": (
            acquired["result_code"] == "LOCK_SET_ACQUIRED"
            and len(acquired["lock_keys"]) == 2
            and len(acquire_snapshot["locks"]) == 2
        ),
        "acquire_idempotent": (
            replay == acquired and registry.snapshot()["fencing_counter"] == 1
        ),
        "idempotency_input_conflict_fails_closed": (
            idempotency_conflict["result_code"] == "IDEMPOTENCY_INPUT_CONFLICT"
            and idempotency_conflict["decision_action"] == "REQUIRE_MANUAL_REVIEW"
            and idempotency_before == idempotency_after
        ),
        "contention_preserves_stage038": (
            conflict["result_code"] == "RESOURCE_CONFLICT_ACTIVE"
            and conflict["decision_action"] == "PAUSE_BEFORE_QUEUE_ADMISSION"
            and not conflict["queue_record_created"]
            and not conflict["retry_budget_consumed"]
            and not conflict["partial_lock_retained"]
        ),
        "renew_advances_version_without_fence": (
            renewed["result_code"] == "LEASE_RENEWED"
            and renewed["fencing_token"] == renew_acquired["fencing_token"]
            and all(
                renewed["lock_versions"][key]
                == renew_acquired["lock_versions"][key] + 1
                for key in renewed["lock_keys"]
            )
            and renewed["lease_expires_at"] == 1040
            and renew_stale_commit["result_code"] == "STALE_FENCING_TOKEN"
        ),
        "takeover_requires_expiry_plus_grace": (
            early["result_code"] == "LEASE_NOT_TAKEOVER_ELIGIBLE"
            and takeover["result_code"] == "TAKEOVER_ACQUIRED"
        ),
        "takeover_advances_fence_and_versions": (
            takeover["fencing_token"] == takeover_acquired["fencing_token"] + 1
            and all(
                takeover["lock_versions"][key]
                == takeover_acquired["lock_versions"][key] + 1
                for key in takeover["lock_keys"]
            )
        ),
        "takeover_requires_current_cas_evidence": (
            stale_takeover["result_code"] == "STALE_TAKEOVER_EVIDENCE"
            and all(
                cas_before[key] == cas_after_stale[key]
                for key in ("locks", "lock_versions", "fencing_counter")
            )
            and current_takeover["result_code"] == "TAKEOVER_ACQUIRED"
        ),
        "stale_fence_rejected": (
            stale["result_code"] == "STALE_FENCING_TOKEN"
            and stale["decision_action"] == "REJECT_COMMIT"
            and current["decision_action"] == "COMMIT_ALLOWED"
        ),
        "release_whole_set_idempotent": (
            released["result_code"] == "LOCK_SET_RELEASED"
            and released == release_replay
            and release_registry.snapshot()["locks"] == {}
            and released["lock_versions"]
            == release_registry.snapshot()["lock_versions"]
            and all(
                released["lock_versions"][key]
                == release_acquired["lock_versions"][key] + 1
                for key in released["lock_keys"]
            )
        ),
        "no_forbidden_side_effects": all(
            contract["truth_flags"][name] is False for name in FALSE_TRUTH_FLAGS
        ),
    }
    report = {
        "stage": "STAGE-041",
        "phase": "Phase 2",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "policy_contract_id": POLICY_VERSION,
        "next_gate": "IDS-STAGE041-P3-GATE",
        "contract_checks": contract_checks,
        "slice_checks": slice_checks,
    }
    report.update(contract["truth_flags"])
    report["phase2_slice_valid"] = all(contract_checks.values()) and all(
        slice_checks.values()
    )
    return report


def main() -> int:
    report = build_stage041_phase2_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["phase2_slice_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
