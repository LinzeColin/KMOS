#!/usr/bin/env python3
"""Validate and exercise the isolated STAGE-044 Phase 2 candidate decision slice."""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Mapping
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CONTRACT_PATH = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "half_product_cleanup"
    / "stage044_half_product_cleanup_runtime_contract.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)

SOURCE_BINDING = {
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
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

PREDECESSOR_BINDING = {
    "commit": "0eabde291fc54328e6fbc76df4f9dc5af894b770",
    "tree": "53a8e0388ba3a2f6551c43b6dc07ee22ff90505c",
    "parent": "e7835134550e2776f0949870fcaf7d7b9a54bd01",
    "task_id": "IDS-V0_1-STAGE044-P1",
    "result": "PASS_PHASE1_CONTRACT_DELETE_DISABLED",
}

UPSTREAM_BINDINGS = {
    "phase1_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
            "stage044_half_product_cleanup_contract.json"
        ),
        "sha256": "9630f59c6aa0a5bdfb35651392862e9b1031b460d9892fd7495071094d3d2475",
    },
    "phase1_checker": {
        "ref": "KM_IDSystem/scripts/check_half_product_cleanup.py",
        "sha256": "0db8d34b2be1e24abc87b7a3684ca59e800544ccebbd90ff4164a8b64c31c769",
    },
    "phase1_boundary": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE044_PHASE1_HALF_PRODUCT_CLEANUP_SCOPE_BOUNDARY.md"
        ),
        "sha256": "b634d8bdfe60d015c7277c435b65d21fc46e3597bce4bf635889e45175a6b810",
    },
    "stage034_retention_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/data_retention_table/"
            "stage034_data_retention_table_index.json"
        ),
        "sha256": "0b579f93c623cd20e99752c9801f5c9bb14757e531697d687f87fe5c7c6c8504",
    },
    "stage037_state_index": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
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
    "stage043_recovery_runtime": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
            "stage043_worker_crash_recovery_runtime_contract.json"
        ),
        "sha256": "153a451f3e5aef4fef1faa8b4e3035f472ac50298d790731f19ba8701361ab38",
    },
}

PARAMETERS = {
    "cleanup_scan_interval": 300,
    "cleanup_candidate_retention": 600,
    "cleanup_lock_lease": 30,
    "writer_quiescence_window": 60,
    "cleanup_attempt_timeout": 30,
}
ELIGIBLE_CLASSES = ["TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"]
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
CANDIDATE_STATES = ["PAUSED", "RETRY_WAIT", "FAILED", "DEAD_LETTERED", "CANCELLED"]
BLOCKED_STATES = ["CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED", "SUCCEEDED"]
RESOURCE_SIGNALS = [
    "EXTERNAL_DRIVE_OFFLINE",
    "DISK_SPACE_INSUFFICIENT",
    "EXTERNAL_API_BUDGET_INSUFFICIENT",
]
ROOT_FIELDS = [
    "schema_version",
    "cleanup_request_id",
    "job_id",
    "attempt_id",
    "creator_job_id",
    "observed_job_state",
    "expected_state_version",
    "approved_root_id",
    "approved_root_canonical_identity",
    "candidate_parent_directory",
    "root_relative_path",
    "artifact_class",
    "rebuildable",
    "retention_policy_ref",
    "legal_hold_status",
    "owner_hold_status",
    "cleanup_manifest_ref",
    "immutable_lstat_identity",
    "durable_reference_status",
    "writer_quiescence_evidence_ref",
    "resource_gate_evidence_ref",
    "evidence",
]
EVIDENCE_FIELDS = [
    "input_refs",
    "attempt_ownership_proved",
    "approved_root_identity_proved",
    "root_relative_path_proved",
    "cleanup_manifest_valid",
    "retention_elapsed_seconds",
    "writer_quiescence_elapsed_seconds",
    "writer_quiescence_proved",
    "exclusive_namespace_lock_proved",
    "namespace_lock_managed",
    "namespace_lock_exclusive",
    "producer_and_cleanup_leases_absent_or_fenced",
    "resource_gates_passed",
    "resource_pressure_signal",
    "resource_observation_fresh",
    "lstat_identity_stable",
    "no_symlink_components_proved",
    "canonical_containment_proved",
]
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,255}$")
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,511}$")
SHA_REF = re.compile(r"^(?:root|manifest):sha256:[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _safe_id(value: Any, prefix: str | None = None) -> bool:
    return (
        isinstance(value, str)
        and bool(SAFE_ID.fullmatch(value))
        and (prefix is None or value.startswith(prefix))
        and ".." not in value
    )


def _safe_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(SAFE_REF.fullmatch(value))
        and not value.startswith("/")
        and ".." not in PurePosixPath(value).parts
        and "\\" not in value
    )


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
        and len(path.parts) >= 2
    )


@lru_cache(maxsize=64)
def _git_tracked(relative: str) -> bool:
    if not _safe_relative_path(relative):
        return False
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _live_source_valid() -> bool:
    try:
        archive = Path(SOURCE_BINDING["source_archive_path"])
        if (
            not archive.is_file()
            or _sha256(archive) != SOURCE_BINDING["source_archive_sha256"]
            or _sha256(ROADMAP_SOURCE_PATH) != SOURCE_BINDING["roadmap_sha256"]
            or _sha256(INSTRUCTIONS_SOURCE_PATH) != SOURCE_BINDING["instructions_sha256"]
        ):
            return False
        with ZipFile(archive) as source_zip:
            matches = [
                name
                for name in source_zip.namelist()
                if name == SOURCE_BINDING["source_member"]
            ]
            if len(matches) != SOURCE_BINDING["source_member_match_count"]:
                return False
            digest = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
        return digest == SOURCE_BINDING["source_member_sha256"]
    except (OSError, KeyError, ValueError):
        return False


def _predecessor_valid() -> bool:
    try:
        observed = subprocess.check_output(
            [
                "git",
                "show",
                "-s",
                "--format=%H%n%T%n%P",
                PREDECESSOR_BINDING["commit"],
            ],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                PREDECESSOR_BINDING["commit"],
                "HEAD",
            ],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return observed == [
        PREDECESSOR_BINDING["commit"],
        PREDECESSOR_BINDING["tree"],
        PREDECESSOR_BINDING["parent"],
    ] and ancestor


def _upstream_valid(bindings: Any) -> bool:
    if bindings != UPSTREAM_BINDINGS:
        return False
    try:
        return all(
            _sha256(REPO_ROOT / item["ref"]) == item["sha256"]
            and _git_tracked(item["ref"])
            for item in bindings.values()
        )
    except OSError:
        return False


def _expected_top_keys() -> set[str]:
    return {
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
        "path_and_identity_contract",
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


def _policy_valid(policy: Any) -> bool:
    if not isinstance(policy, Mapping) or policy.get("parameters") != PARAMETERS:
        return False
    if (
        policy.get("policy_version")
        != "ids.half_product_cleanup_policy.v0_1.stage044.p2"
        or policy.get("fact_level") != "PROPOSED"
        or policy.get("production_calibrated") is not False
        or policy.get("production_calibration_required") is not True
        or policy.get("production_calibration_task_id") != "TASK-OPME-B-001"
        or policy.get("rollback_policy") != "NO_AUTOMATIC_HALF_PRODUCT_CLEANUP"
    ):
        return False
    provenance = policy.get("parameter_provenance")
    if not isinstance(provenance, Mapping) or set(provenance) != set(PARAMETERS):
        return False
    for name, value in PARAMETERS.items():
        item = provenance.get(name)
        if not isinstance(item, Mapping) or item.get("value") != value:
            return False
        if (
            item.get("unit") != "seconds"
            or item.get("fact_level") != "PROPOSED"
            or item.get("policy_version") != policy.get("policy_version")
            or not item.get("source_refs")
            or not item.get("derivation")
            or not item.get("validation_evidence")
            or item.get("rollback") != "NO_AUTOMATIC_HALF_PRODUCT_CLEANUP"
        ):
            return False
    return (
        PARAMETERS["cleanup_candidate_retention"]
        >= 2 * PARAMETERS["cleanup_scan_interval"]
        and PARAMETERS["writer_quiescence_window"]
        >= 2 * PARAMETERS["cleanup_lock_lease"]
        and PARAMETERS["cleanup_attempt_timeout"]
        <= PARAMETERS["cleanup_lock_lease"]
    )


def _request_contract_valid(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("schema_version") == "ids.stage044.cleanup_candidate_request.v1"
        and value.get("required_root_fields") == ROOT_FIELDS
        and value.get("required_lstat_identity_fields") == ["st_dev", "st_ino", "file_type"]
        and value.get("required_evidence_fields") == EVIDENCE_FIELDS
        and value.get("control_job_id_prefix") == "control:stage044:"
        and value.get("cleanup_request_id_prefix") == "control:stage044:cleanup:"
        and value.get("expected_state_version_must_be_positive") is True
        and value.get("raw_payload_allowed") is False
        and value.get("absolute_path_allowed") is False
        and value.get("secret_material_allowed") is False
    )


def _decision_contract_valid(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("eligible_artifact_classes") == ELIGIBLE_CLASSES
        and value.get("protected_artifact_classes") == PROTECTED_CLASSES
        and value.get("candidate_job_states") == CANDIDATE_STATES
        and value.get("blocked_job_states") == BLOCKED_STATES
        and value.get("mandatory_resource_pause_signals") == RESOURCE_SIGNALS
        and value.get("candidate_only") is True
        and value.get("automatic_cleanup_allowed") is False
        and value.get("delete_allowed") is False
        and value.get("override_allowed") is False
    )


def _runtime_boundary_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    allowed_true = {
        "isolated_candidate_decision_runtime_allowed",
        "reference_only_control_metadata_allowed",
    }
    return all(
        item is True if key in allowed_true else item is False
        for key, item in value.items()
    ) and set(value) == {
        "isolated_candidate_decision_runtime_allowed",
        "reference_only_control_metadata_allowed",
        "cleanup_scan_allowed",
        "filesystem_probe_allowed",
        "filesystem_traversal_allowed",
        "production_lock_runtime_allowed",
        "writer_quiescence_probe_allowed",
        "openat_allowed",
        "unlinkat_allowed",
        "delete_allowed",
        "move_or_overwrite_allowed",
        "cleanup_runtime_allowed",
        "audit_write_allowed",
        "database_allowed",
        "schema_change_allowed",
        "persistent_state_write_allowed",
        "runtime_output_write_allowed",
        "external_api_allowed",
        "raw_metadata_access_allowed",
        "ids_business_job_allowed",
        "fake_ids_business_data_allowed",
        "production_activation_allowed",
    }


def _truth_flags_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    true_flags = {
        "taskpack_source_read_performed",
        "parameter_values_assigned",
        "isolated_candidate_decision_runtime_performed",
        "cleanup_candidate_evaluation_performed",
        "candidate_only_decision_emitted",
    }
    return set(value) == true_flags | {
        "ids_business_source_read_performed",
        "raw_metadata_content_accessed",
        "fake_ids_business_data_used",
        "real_ids_business_job_created",
        "cleanup_scan_performed",
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
        "state_transition_performed",
        "terminal_result_changed",
        "persistent_state_write_performed",
        "audit_write_performed",
        "database_connection_performed",
        "schema_change_performed",
        "runtime_output_written",
        "external_api_call_performed",
        "production_runtime_activation_performed",
        "whole_stage_review_performed",
        "batch_review_performed",
        "github_upload_allowed",
        "app_reinstall_allowed",
    } and all(value[key] is True for key in true_flags) and all(
        value[key] is False for key in set(value) - true_flags
    )


def evaluate_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, Mapping):
        return {"contract_is_mapping": False}
    identity = (
        contract.get("schema_version") == "ids.stage044.half_product_cleanup.phase2.v1"
        and contract.get("stage") == "STAGE-044"
        and contract.get("phase") == "Phase 2"
        and contract.get("task_id") == "IDS-V0_1-STAGE044-P2"
        and contract.get("acceptance_id") == "ACC-STAGE-044"
        and contract.get("execution_mode")
        == "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CLEANUP_CANDIDATE_DECISION_SLICE"
        and contract.get("policy_contract_id")
        == "ids.half_product_cleanup_policy.v0_1.stage044.p2"
        and contract.get("contract_state")
        == "PHASE2_ISOLATED_CANDIDATE_DECISION_SLICE_ENABLED_DELETE_DISABLED"
        and contract.get("next_gate") == "IDS-STAGE044-P3-GATE"
    )
    path_contract = contract.get("path_and_identity_contract", {})
    idempotency = contract.get("idempotency_contract", {})
    metadata = contract.get("control_metadata_contract", {})
    rollback = contract.get("rollback", {})
    phase3 = contract.get("phase3_entry_gate", {})
    return {
        "exact_top_shape": set(contract) == _expected_top_keys(),
        "identity": identity,
        "source_binding": contract.get("source_binding") == SOURCE_BINDING,
        "live_source_integrity": _live_source_valid(),
        "phase1_predecessor_binding": contract.get("phase1_predecessor_binding") == PREDECESSOR_BINDING,
        "phase1_predecessor_ancestry": _predecessor_valid(),
        "upstream_bindings": _upstream_valid(contract.get("upstream_bindings")),
        "policy_and_parameters": _policy_valid(contract.get("policy")),
        "request_contract": _request_contract_valid(contract.get("request_contract")),
        "decision_contract": _decision_contract_valid(contract.get("decision_contract")),
        "path_identity_no_traversal": (
            isinstance(path_contract, Mapping)
            and path_contract.get("file_type_allowlist") == ["REGULAR_FILE"]
            and path_contract.get("filesystem_identity_probe_allowed") is False
            and path_contract.get("filesystem_traversal_allowed") is False
        ),
        "idempotency_no_persistence": (
            isinstance(idempotency, Mapping)
            and idempotency.get("ledger_mode") == "PROCESS_LOCAL_IN_MEMORY_DECISION_ONLY"
            and idempotency.get("exact_replay_returns_original") is True
            and idempotency.get("persistent_ledger_allowed") is False
            and idempotency.get("audit_write_allowed") is False
        ),
        "reference_only_metadata": (
            isinstance(metadata, Mapping)
            and metadata.get("input_refs_must_be_git_tracked") is True
            and metadata.get("raw_body_allowed") is False
            and metadata.get("output_refs") == []
            and metadata.get("candidate_record_write_allowed") is False
            and metadata.get("runtime_output_write_allowed") is False
        ),
        "human_status_complete": set(contract.get("human_status_projection", {})) == {
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED",
            "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
            "CLEANUP_BLOCKED_RESOURCE",
            "CLEANUP_BLOCKED_PROTECTED",
            "REQUIRE_MANUAL_REVIEW",
        },
        "ownership_separation": contract.get("ownership_matrix", {}).get("filesystem_cleanup_execution") == "FUTURE_STAGE044_PHASE_NOT_ENABLED",
        "registry_binding": contract.get("registry_binding") == {
            "model_id": "MOD-013",
            "formula_id": "FORM-013",
            "parameter_ids": ["PARAM-082", "PARAM-083", "PARAM-084", "PARAM-085", "PARAM-086"],
            "production_calibration_task_id": "TASK-OPME-B-001",
        },
        "runtime_boundary": _runtime_boundary_valid(contract.get("runtime_boundary")),
        "rollback_non_destructive": (
            isinstance(rollback, Mapping)
            and rollback.get("action") == "NO_AUTOMATIC_HALF_PRODUCT_CLEANUP"
            and rollback.get("destructive_rollback_allowed") is False
            and rollback.get("github_action_allowed") is False
        ),
        "phase3_separate_and_not_authorized": (
            isinstance(phase3, Mapping)
            and phase3.get("entry_authorized") is False
            and phase3.get("required_task_id") == "IDS-V0_1-STAGE044-P3"
            and phase3.get("required_gate") == "IDS-STAGE044-P3-GATE"
            and phase3.get("separate_run_required") is True
        ),
        "truth_flags": _truth_flags_valid(contract.get("truth_flags")),
    }


def _load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def derive_cleanup_request_id(request: Mapping[str, Any]) -> str:
    payload = {key: copy.deepcopy(value) for key, value in request.items() if key != "cleanup_request_id"}
    return "control:stage044:cleanup:" + _canonical_sha256(payload)


def derive_cleanup_idempotency_key(request: Mapping[str, Any]) -> str:
    identity = request.get("immutable_lstat_identity", {})
    payload = {
        "cleanup_request_id": request.get("cleanup_request_id"),
        "job_id": request.get("job_id"),
        "attempt_id": request.get("attempt_id"),
        "approved_root_id": request.get("approved_root_id"),
        "root_relative_path": request.get("root_relative_path"),
        "st_dev": identity.get("st_dev") if isinstance(identity, Mapping) else None,
        "st_ino": identity.get("st_ino") if isinstance(identity, Mapping) else None,
        "cleanup_manifest_ref": request.get("cleanup_manifest_ref"),
    }
    return _canonical_sha256(payload)


def build_cleanup_request(**overrides: Any) -> dict[str, Any]:
    control_digest = _canonical_sha256({"stage": "STAGE-044", "slice": "Phase 2"})
    request: dict[str, Any] = {
        "schema_version": "ids.stage044.cleanup_candidate_request.v1",
        "cleanup_request_id": "",
        "job_id": "control:stage044:job:phase2",
        "attempt_id": "control:stage044:attempt:phase2",
        "creator_job_id": "control:stage044:job:phase2",
        "observed_job_state": "FAILED",
        "expected_state_version": 1,
        "approved_root_id": "control:stage044:approved-root:isolated",
        "approved_root_canonical_identity": f"root:sha256:{control_digest}",
        "candidate_parent_directory": "control/stage044",
        "root_relative_path": "control/stage044/attempt-output.partial",
        "artifact_class": "TEMP_STAGING_OUTPUT",
        "rebuildable": True,
        "retention_policy_ref": "retention:stage034:temporary_file",
        "legal_hold_status": "CLEAR",
        "owner_hold_status": "CLEAR",
        "cleanup_manifest_ref": f"manifest:sha256:{control_digest}",
        "immutable_lstat_identity": {
            "st_dev": 1,
            "st_ino": 1,
            "file_type": "REGULAR_FILE",
        },
        "durable_reference_status": "UNREFERENCED",
        "writer_quiescence_evidence_ref": "evidence:stage044:writer-quiescence",
        "resource_gate_evidence_ref": "evidence:stage044:resource-gates",
        "evidence": {
            "input_refs": [
                UPSTREAM_BINDINGS["phase1_contract"]["ref"],
                UPSTREAM_BINDINGS["stage034_retention_contract"]["ref"],
                UPSTREAM_BINDINGS["stage041_lock_runtime"]["ref"],
                UPSTREAM_BINDINGS["stage042_lifecycle_runtime"]["ref"],
                UPSTREAM_BINDINGS["stage043_recovery_runtime"]["ref"],
            ],
            "attempt_ownership_proved": True,
            "approved_root_identity_proved": True,
            "root_relative_path_proved": True,
            "cleanup_manifest_valid": True,
            "retention_elapsed_seconds": PARAMETERS["cleanup_candidate_retention"],
            "writer_quiescence_elapsed_seconds": PARAMETERS["writer_quiescence_window"],
            "writer_quiescence_proved": True,
            "exclusive_namespace_lock_proved": True,
            "namespace_lock_managed": True,
            "namespace_lock_exclusive": True,
            "producer_and_cleanup_leases_absent_or_fenced": True,
            "resource_gates_passed": True,
            "resource_pressure_signal": "NONE",
            "resource_observation_fresh": True,
            "lstat_identity_stable": True,
            "no_symlink_components_proved": True,
            "canonical_containment_proved": True,
        },
    }
    lstat_fields = {"st_dev", "st_ino", "file_type"}
    evidence_fields = set(EVIDENCE_FIELDS)
    for key, value in overrides.items():
        if key in lstat_fields:
            request["immutable_lstat_identity"][key] = value
        elif key in evidence_fields:
            request["evidence"][key] = value
        else:
            request[key] = value
    request["cleanup_request_id"] = derive_cleanup_request_id(request)
    return request


def _request_shape_valid(request: Any) -> bool:
    return (
        isinstance(request, Mapping)
        and list(request) == ROOT_FIELDS
        and set(request) == set(ROOT_FIELDS)
        and isinstance(request.get("immutable_lstat_identity"), Mapping)
        and list(request["immutable_lstat_identity"]) == ["st_dev", "st_ino", "file_type"]
        and isinstance(request.get("evidence"), Mapping)
        and list(request["evidence"]) == EVIDENCE_FIELDS
    )


def _request_identity_valid(request: Mapping[str, Any]) -> bool:
    identity = request.get("immutable_lstat_identity")
    return (
        request.get("schema_version") == "ids.stage044.cleanup_candidate_request.v1"
        and _safe_id(request.get("cleanup_request_id"), "control:stage044:cleanup:")
        and _safe_id(request.get("job_id"), "control:stage044:")
        and _safe_id(request.get("attempt_id"), "control:stage044:")
        and _safe_id(request.get("creator_job_id"), "control:stage044:")
        and _positive_int(request.get("expected_state_version"))
        and _safe_id(request.get("approved_root_id"), "control:stage044:")
        and isinstance(request.get("approved_root_canonical_identity"), str)
        and bool(SHA_REF.fullmatch(request["approved_root_canonical_identity"]))
        and _safe_relative_path(request.get("candidate_parent_directory"))
        and _safe_relative_path(request.get("root_relative_path"))
        and str(PurePosixPath(request["root_relative_path"]).parent)
        == request.get("candidate_parent_directory")
        and _safe_ref(request.get("retention_policy_ref"))
        and isinstance(request.get("cleanup_manifest_ref"), str)
        and bool(SHA_REF.fullmatch(request["cleanup_manifest_ref"]))
        and _safe_ref(request.get("writer_quiescence_evidence_ref"))
        and _safe_ref(request.get("resource_gate_evidence_ref"))
        and isinstance(identity, Mapping)
        and _positive_int(identity.get("st_dev"))
        and _positive_int(identity.get("st_ino"))
        and identity.get("file_type") == "REGULAR_FILE"
    )


def _evidence_structure_valid(evidence: Any) -> bool:
    if not isinstance(evidence, Mapping) or list(evidence) != EVIDENCE_FIELDS:
        return False
    bool_fields = set(EVIDENCE_FIELDS) - {
        "input_refs",
        "retention_elapsed_seconds",
        "writer_quiescence_elapsed_seconds",
        "resource_pressure_signal",
    }
    return (
        isinstance(evidence.get("input_refs"), list)
        and bool(evidence["input_refs"])
        and all(isinstance(ref, str) and _git_tracked(ref) for ref in evidence["input_refs"])
        and _nonnegative_int(evidence.get("retention_elapsed_seconds"))
        and _nonnegative_int(evidence.get("writer_quiescence_elapsed_seconds"))
        and isinstance(evidence.get("resource_pressure_signal"), str)
        and all(isinstance(evidence.get(field), bool) for field in bool_fields)
    )


def validate_cleanup_request(request: Any) -> bool:
    if not _request_shape_valid(request):
        return False
    assert isinstance(request, Mapping)
    return (
        _request_identity_valid(request)
        and _evidence_structure_valid(request.get("evidence"))
        and request.get("cleanup_request_id") == derive_cleanup_request_id(request)
        and request.get("observed_job_state") in CANDIDATE_STATES + BLOCKED_STATES
        and request.get("artifact_class") in ELIGIBLE_CLASSES + PROTECTED_CLASSES
        and isinstance(request.get("rebuildable"), bool)
        and request.get("legal_hold_status") in {"CLEAR", "HELD", "UNKNOWN"}
        and request.get("owner_hold_status") in {"CLEAR", "HELD", "UNKNOWN"}
        and request.get("durable_reference_status") in {"UNREFERENCED", "REFERENCED", "UNKNOWN"}
    )


class InMemoryCleanupDecisionLedger:
    """Process-local replay guard; it never persists or writes an audit record."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[str, dict[str, Any]]] = {}

    def lookup(self, request: Mapping[str, Any]) -> tuple[str, dict[str, Any] | None]:
        request_id = request.get("cleanup_request_id")
        if not isinstance(request_id, str):
            return "MISS", None
        digest = _canonical_sha256(request)
        existing = self._records.get(request_id)
        if existing is None:
            return "MISS", None
        if existing[0] == digest:
            return "REPLAY", copy.deepcopy(existing[1])
        return "CONFLICT", None

    def store(self, request: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        request_id = request["cleanup_request_id"]
        self._records[request_id] = (
            _canonical_sha256(request),
            copy.deepcopy(dict(result)),
        )


def _fixed_ref(namespace: str, payload: Any) -> str:
    return f"{namespace}:sha256:{_canonical_sha256(payload)}"


def _manual_result(reason_code: str) -> dict[str, Any]:
    payload = {"stage": "STAGE-044", "reason_code": reason_code}
    return {
        "schema_version": "ids.stage044.cleanup_candidate_decision.v1",
        "decision_action": "REQUIRE_MANUAL_REVIEW",
        "reason_code": reason_code,
        "runtime_owner": "STAGE-044",
        "candidate_only": True,
        "idempotency_key": "",
        "input_refs": [],
        "output_refs": [],
        "candidate_ref": _fixed_ref("candidate", payload),
        "error_ref": f"error:{reason_code}",
        "audit_ref": _fixed_ref("audit:stage044", payload),
        "human_status": {
            "label_zh": "清理请求无效或冲突，需要人工复核",
            "severity": "CRITICAL",
        },
        "automatic_resume_allowed": False,
        "delete_allowed": False,
        "filesystem_traversal_performed": False,
        "production_lock_acquired": False,
        "state_transition_performed": False,
        "audit_write_performed": False,
    }


def _decision_result(
    request: Mapping[str, Any],
    action: str,
    reason_code: str,
    human_status: Mapping[str, Any],
) -> dict[str, Any]:
    identity = {
        "cleanup_request_id": request["cleanup_request_id"],
        "idempotency_key": derive_cleanup_idempotency_key(request),
        "decision_action": action,
    }
    return {
        "schema_version": "ids.stage044.cleanup_candidate_decision.v1",
        "decision_action": action,
        "reason_code": reason_code,
        "runtime_owner": "STAGE-044",
        "candidate_only": True,
        "idempotency_key": identity["idempotency_key"],
        "input_refs": list(request["evidence"]["input_refs"]),
        "output_refs": [],
        "candidate_ref": _fixed_ref("candidate", identity),
        "error_ref": "error:NONE" if action == "CLEANUP_CANDIDATE_REVIEW_REQUIRED" else f"error:{reason_code}",
        "audit_ref": _fixed_ref("audit:stage044", identity),
        "human_status": copy.deepcopy(dict(human_status)),
        "automatic_resume_allowed": False,
        "delete_allowed": False,
        "filesystem_traversal_performed": False,
        "production_lock_acquired": False,
        "state_transition_performed": False,
        "audit_write_performed": False,
    }


def _contract_fast_valid(contract: Any) -> bool:
    if not isinstance(contract, Mapping):
        return False
    return (
        set(contract) == _expected_top_keys()
        and contract.get("schema_version") == "ids.stage044.half_product_cleanup.phase2.v1"
        and contract.get("policy", {}).get("parameters") == PARAMETERS
        and contract.get("upstream_bindings") == UPSTREAM_BINDINGS
        and _request_contract_valid(contract.get("request_contract"))
        and _decision_contract_valid(contract.get("decision_contract"))
        and _runtime_boundary_valid(contract.get("runtime_boundary"))
        and _truth_flags_valid(contract.get("truth_flags"))
    )


def _semantic_identity_valid(request: Mapping[str, Any]) -> bool:
    return _request_identity_valid(request) and _evidence_structure_valid(request.get("evidence"))


def evaluate_cleanup_candidate(
    request: Any,
    *,
    contract: Mapping[str, Any] | None = None,
    ledger: InMemoryCleanupDecisionLedger | None = None,
) -> dict[str, Any]:
    selected_contract: Mapping[str, Any]
    try:
        selected_contract = _load_contract() if contract is None else contract
    except (OSError, json.JSONDecodeError):
        return _manual_result("CLEANUP_CONTRACT_INVALID")
    if not _contract_fast_valid(selected_contract):
        return _manual_result("CLEANUP_CONTRACT_INVALID")
    if not isinstance(request, Mapping) or not _request_shape_valid(request):
        return _manual_result("MALFORMED_CLEANUP_REQUEST")

    if ledger is not None:
        replay_state, replay = ledger.lookup(request)
        if replay_state == "REPLAY" and replay is not None:
            return replay
        if replay_state == "CONFLICT":
            return _manual_result("CLEANUP_REQUEST_CONFLICT")

    if request.get("cleanup_request_id") != derive_cleanup_request_id(request):
        return _manual_result("CLEANUP_REQUEST_ID_MISMATCH")

    statuses = selected_contract["human_status_projection"]
    if not _semantic_identity_valid(request):
        result = _decision_result(
            request,
            "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
            "IDENTITY_ROOT_PATH_OR_EVIDENCE_NOT_PROVEN",
            statuses["CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"],
        )
    elif request.get("artifact_class") in PROTECTED_CLASSES or (
        request.get("artifact_class") in ELIGIBLE_CLASSES
        and (
            request.get("rebuildable") is not True
            or request.get("legal_hold_status") != "CLEAR"
            or request.get("owner_hold_status") != "CLEAR"
            or request.get("durable_reference_status") != "UNREFERENCED"
        )
    ):
        result = _decision_result(
            request,
            "CLEANUP_BLOCKED_PROTECTED",
            "PROTECTED_HELD_NON_REBUILDABLE_OR_REFERENCED",
            statuses["CLEANUP_BLOCKED_PROTECTED"],
        )
    elif request.get("artifact_class") not in ELIGIBLE_CLASSES:
        result = _manual_result("UNKNOWN_ARTIFACT_CLASS")
    elif request.get("observed_job_state") not in CANDIDATE_STATES:
        result = _decision_result(
            request,
            "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
            "JOB_ACTIVE_SUCCEEDED_OR_UNKNOWN",
            statuses["CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"],
        )
    else:
        evidence = request["evidence"]
        signal = evidence["resource_pressure_signal"]
        if signal in RESOURCE_SIGNALS or evidence["resource_gates_passed"] is False:
            result = _decision_result(
                request,
                "CLEANUP_BLOCKED_RESOURCE",
                "RESOURCE_GATE_BLOCKED",
                statuses["CLEANUP_BLOCKED_RESOURCE"],
            )
        elif signal != "NONE":
            result = _decision_result(
                request,
                "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                "RESOURCE_SIGNAL_UNKNOWN",
                statuses["CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"],
            )
        else:
            required_true = [
                "attempt_ownership_proved",
                "approved_root_identity_proved",
                "root_relative_path_proved",
                "cleanup_manifest_valid",
                "writer_quiescence_proved",
                "exclusive_namespace_lock_proved",
                "namespace_lock_managed",
                "namespace_lock_exclusive",
                "producer_and_cleanup_leases_absent_or_fenced",
                "resource_gates_passed",
                "resource_observation_fresh",
                "lstat_identity_stable",
                "no_symlink_components_proved",
                "canonical_containment_proved",
            ]
            evidence_complete = all(evidence[field] is True for field in required_true)
            windows_complete = (
                evidence["retention_elapsed_seconds"] >= PARAMETERS["cleanup_candidate_retention"]
                and evidence["writer_quiescence_elapsed_seconds"] >= PARAMETERS["writer_quiescence_window"]
            )
            if not evidence_complete or not windows_complete:
                result = _decision_result(
                    request,
                    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                    "OWNERSHIP_RETENTION_LOCK_OR_QUIESCENCE_NOT_PROVEN",
                    statuses["CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"],
                )
            else:
                result = _decision_result(
                    request,
                    "CLEANUP_CANDIDATE_REVIEW_REQUIRED",
                    "ALL_REFERENCE_ONLY_CANDIDATE_GATES_PASSED_DELETE_DISABLED",
                    statuses["CLEANUP_CANDIDATE_REVIEW_REQUIRED"],
                )

    if ledger is not None:
        ledger.store(request, result)
    return result


def build_stage044_phase2_report() -> dict[str, Any]:
    try:
        contract = _load_contract()
    except (OSError, json.JSONDecodeError):
        contract = {}
    contract_checks = evaluate_contract(contract)

    valid = build_cleanup_request()
    valid_result = evaluate_cleanup_candidate(valid, contract=contract)
    protected_results = [
        evaluate_cleanup_candidate(
            build_cleanup_request(artifact_class=artifact_class),
            contract=contract,
        )["decision_action"]
        for artifact_class in PROTECTED_CLASSES
    ]
    resource_results = [
        evaluate_cleanup_candidate(
            build_cleanup_request(
                resource_gates_passed=False,
                resource_pressure_signal=signal,
            ),
            contract=contract,
        )["decision_action"]
        for signal in RESOURCE_SIGNALS
    ]
    active_results = [
        evaluate_cleanup_candidate(
            build_cleanup_request(observed_job_state=state),
            contract=contract,
        )["decision_action"]
        for state in BLOCKED_STATES
    ]
    ledger = InMemoryCleanupDecisionLedger()
    first = evaluate_cleanup_candidate(valid, contract=contract, ledger=ledger)
    replay = evaluate_cleanup_candidate(copy.deepcopy(valid), contract=contract, ledger=ledger)
    changed = copy.deepcopy(valid)
    changed["owner_hold_status"] = "HELD"
    conflict = evaluate_cleanup_candidate(changed, contract=contract, ledger=ledger)
    bad_path = evaluate_cleanup_candidate(
        build_cleanup_request(root_relative_path="../escape.partial"),
        contract=contract,
    )
    stale = evaluate_cleanup_candidate(
        build_cleanup_request(writer_quiescence_elapsed_seconds=59),
        contract=contract,
    )
    malformed = evaluate_cleanup_candidate(
        {"raw_payload": "must-not-be-returned"},
        contract=contract,
    )
    forged = build_cleanup_request()
    forged["cleanup_request_id"] = "control:stage044:cleanup:" + "0" * 64
    forged_result = evaluate_cleanup_candidate(forged, contract=contract)

    decision_checks = {
        "valid_candidate_requires_review": valid_result["decision_action"] == "CLEANUP_CANDIDATE_REVIEW_REQUIRED",
        "valid_candidate_delete_disabled": valid_result["delete_allowed"] is False,
        "valid_candidate_no_traversal": valid_result["filesystem_traversal_performed"] is False,
        "valid_candidate_no_production_lock": valid_result["production_lock_acquired"] is False,
        "all_protected_classes_blocked": set(protected_results) == {"CLEANUP_BLOCKED_PROTECTED"},
        "all_resource_signals_blocked": set(resource_results) == {"CLEANUP_BLOCKED_RESOURCE"},
        "all_active_or_succeeded_states_blocked": set(active_results) == {"CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"},
        "unsafe_path_blocked": bad_path["decision_action"] == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
        "short_quiescence_blocked": stale["decision_action"] == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
        "exact_replay_idempotent": first == replay,
        "changed_payload_conflicts": conflict["reason_code"] == "CLEANUP_REQUEST_CONFLICT",
        "forged_request_id_rejected": forged_result["reason_code"] == "CLEANUP_REQUEST_ID_MISMATCH",
        "malformed_request_not_echoed": "must-not-be-returned" not in json.dumps(malformed, ensure_ascii=False),
        "safe_reference_only_result": valid_result["output_refs"] == [] and valid_result["candidate_ref"].startswith("candidate:sha256:"),
        "no_actual_effect_flags": all(
            valid_result[field] is False
            for field in (
                "delete_allowed",
                "filesystem_traversal_performed",
                "production_lock_acquired",
                "state_transition_performed",
                "audit_write_performed",
            )
        ),
    }
    phase2_valid = all(contract_checks.values()) and all(decision_checks.values())
    truth = contract.get("truth_flags", {}) if isinstance(contract, Mapping) else {}
    return {
        "schema_version": "ids.stage044.half_product_cleanup.phase2.report.v1",
        "stage": "STAGE-044",
        "phase": "Phase 2",
        "task_id": "IDS-V0_1-STAGE044-P2",
        "acceptance_id": "ACC-STAGE-044",
        "execution_mode": "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CLEANUP_CANDIDATE_DECISION_SLICE",
        "policy_contract_id": "ids.half_product_cleanup_policy.v0_1.stage044.p2",
        "contract_checks": contract_checks,
        "contract_check_count": len(contract_checks),
        "decision_checks": decision_checks,
        "decision_check_count": len(decision_checks),
        "parameter_values_assigned": truth.get("parameter_values_assigned", False),
        "parameter_fact_level": contract.get("policy", {}).get("fact_level", "UNKNOWN") if isinstance(contract, Mapping) else "UNKNOWN",
        "production_calibrated": contract.get("policy", {}).get("production_calibrated", False) if isinstance(contract, Mapping) else False,
        "isolated_candidate_decision_runtime_performed": truth.get("isolated_candidate_decision_runtime_performed", False),
        "cleanup_candidate_evaluation_performed": truth.get("cleanup_candidate_evaluation_performed", False),
        "cleanup_scan_performed": truth.get("cleanup_scan_performed", False),
        "writer_quiescence_probe_performed": truth.get("writer_quiescence_probe_performed", False),
        "filesystem_probe_performed": truth.get("filesystem_probe_performed", False),
        "filesystem_traversal_performed": truth.get("filesystem_traversal_performed", False),
        "production_lock_runtime_performed": truth.get("production_lock_runtime_performed", False),
        "openat_called": truth.get("openat_called", False),
        "delete_operation_started": truth.get("delete_operation_started", False),
        "unlinkat_called": truth.get("unlinkat_called", False),
        "move_or_overwrite_performed": truth.get("move_or_overwrite_performed", False),
        "cleanup_runtime_performed": truth.get("cleanup_runtime_performed", False),
        "state_transition_performed": truth.get("state_transition_performed", False),
        "persistent_state_write_performed": truth.get("persistent_state_write_performed", False),
        "audit_write_performed": truth.get("audit_write_performed", False),
        "runtime_output_written": truth.get("runtime_output_written", False),
        "ids_business_source_read_performed": truth.get("ids_business_source_read_performed", False),
        "raw_metadata_content_accessed": truth.get("raw_metadata_content_accessed", False),
        "fake_ids_business_data_used": truth.get("fake_ids_business_data_used", False),
        "real_ids_business_job_created": truth.get("real_ids_business_job_created", False),
        "production_runtime_activation_performed": truth.get("production_runtime_activation_performed", False),
        "whole_stage_review_performed": truth.get("whole_stage_review_performed", False),
        "batch_review_performed": truth.get("batch_review_performed", False),
        "github_upload_allowed": truth.get("github_upload_allowed", False),
        "app_reinstall_allowed": truth.get("app_reinstall_allowed", False),
        "phase2_slice_valid": phase2_valid,
        "next_gate": "IDS-STAGE044-P3-GATE" if phase2_valid else "IDS-STAGE044-P2-GATE",
        "result": (
            "PASS_ISOLATED_CLEANUP_CANDIDATE_DECISION_DELETE_DISABLED"
            if phase2_valid
            else "BLOCKED_PHASE2_CONTRACT_OR_DECISION_CHECK_FAILED"
        ),
    }


def main() -> int:
    report = build_stage044_phase2_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["phase2_slice_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
