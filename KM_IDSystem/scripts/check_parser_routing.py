#!/usr/bin/env python3
"""Validate the STAGE-046 Phase 1 static parser-routing contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Mapping, Optional
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/parser_routing/"
    "stage046_parser_routing_contract.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "b9229e687be8d91dba4ea77d4d9058e81756cee43adecf1c89e6e2b1eef73448"
)

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
        "STAGE-046_解析器路由合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "V0_1_STAGE_EXECUTION_INDEX.csv"
    ),
    "source_index_sha256": (
        "2e0088153cd1e13a09d9aebd09a1bd0c8c7162acd0788360d45f5c7320af1e9a"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

EXPECTED_PREDECESSOR = {
    "stage045_review_commit": "76027b8dc89e325c212d492d7f5df88357ea7112",
    "stage045_review_root_tree": "37541fb276b548322227969fd36aadf40144e3e3",
    "stage045_review_kmids_tree": "ef8dafd9cd6e19967b7964f88e6eeead25b1866b",
    "stage045_review_parent": "02a3393766b3ba933383af415100ffe5e78c7630",
    "stage045_review_status": "completed_reviewed_local",
    "stage045_review_result": (
        "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
    ),
}

PREDECESSOR_COMMIT = EXPECTED_PREDECESSOR["stage045_review_commit"]
PREDECESSOR_RUN_REF = (
    "KM_IDSystem/machine/runs/2026-07-20-stage045-review-local.json"
)

EXPECTED_UPSTREAM = {
    "stage045_file_type_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
            "stage045_file_type_detection_contract.json"
        ),
        "sha256": (
            "6f3926cd87ee3a654384176516db1d4f7e83e0906a220057d33d6873be8a506f"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage045_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
            "stage045_file_type_detection_delivery_contract.json"
        ),
        "sha256": (
            "209c13f67d457419c8760841f13f401f3d8acec2ec7a72c5c13e0f4722b6c743"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage045_review_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE045_STAGE_REVIEW.md"
        ),
        "sha256": (
            "7dc6cc5c73a6c243ac457bf76af84f58dbee14ed9371d467b14158057d263116"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage045_review_checker_ref": {
        "ref": "KM_IDSystem/scripts/check_file_type_detection_stage_review.py",
        "sha256": (
            "ad9946e6db7303ac38f84927f3d4d51eba576cce545a8b4e75ff1e3b333cf977"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage045_review_run_ref": {
        "ref": PREDECESSOR_RUN_REF,
        "sha256": (
            "b78081cc37aee5c05e18a9942a1f9e0086348881fd4562743397bbac7b258c78"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage037_state_index_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": (
            "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "raw_data_boundary_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "IDS_METADATA_RAW_DATA_BOUNDARY.md"
        ),
        "sha256": (
            "ad4695abf250049699a1b96b49b81432e5d5754dfe7de69c7f3056463a0a7d51"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
}

EXPECTED_INPUT_FIELDS = [
    "routing_request_id",
    "detection_request_id",
    "source_fingerprint_ref",
    "source_identity_ref",
    "detected_type",
    "detection_state",
    "detection_confidence",
    "detection_evidence_ref",
    "detector_contract_version",
    "parser_registry_version",
    "requested_at",
]

EXPECTED_ROUTES = [
    {
        "route_id": "ROUTE_PDF",
        "accepted_types": ["PDF"],
        "parser_family": "PDF_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_OOXML_WORD",
        "accepted_types": ["DOCX"],
        "parser_family": "OOXML_WORD_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_OOXML_WORKBOOK",
        "accepted_types": ["XLSX"],
        "parser_family": "OOXML_WORKBOOK_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_DELIMITED_TEXT",
        "accepted_types": ["CSV"],
        "parser_family": "DELIMITED_TEXT_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_PLAIN_TEXT",
        "accepted_types": ["TXT"],
        "parser_family": "PLAIN_TEXT_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_IMAGE",
        "accepted_types": ["PNG", "JPEG", "TIFF"],
        "parser_family": "IMAGE_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
]

EXPECTED_OUTPUT_FIELDS = [
    "text", "tables", "pages", "sections", "confidence", "errors",
]

EXPECTED_PHASE2_CONDITIONS = [
    "SOURCE_BINDING_EXACT",
    "STAGE045_REVIEW_SNAPSHOT_EXACT",
    "REFERENCE_ONLY_INPUT_EXACT",
    "ROUTE_ELIGIBILITY_FAIL_CLOSED",
    "SIX_ROUTE_FAMILIES_EIGHT_TYPES_EXACT",
    "NO_PARSER_IMPLEMENTATION_OR_VERSION_ASSIGNED",
    "OUTPUT_FALLBACK_PROMPT_OWNERSHIP_PRESERVED",
    "QUALITY_AND_STATE_BOUNDARIES_CLOSED",
    "ALL_RUNTIME_TRUTH_FLAGS_FALSE",
]

EXPECTED_HUMAN_STATUS = {
    "PHASE1_CONTRACT_READY": (
        "解析器路由合同已就绪，实际路由与解析仍禁用"
    ),
    "ROUTE_CANDIDATE_READY_NOT_EXECUTED": (
        "已确认解析器候选路线，但尚未选择或执行解析器"
    ),
    "ROUTE_REVIEW_REQUIRED": "检测证据不足以自动路由，需要人工复核",
    "ROUTE_UNSUPPORTED": "当前文件类型不在支持路线内",
    "ROUTE_BLOCKED": "输入或解析器条件不完整，路由已阻断",
}

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "parser_registry_runtime_loaded",
    "parser_route_evaluation_performed",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "prompt_injection_scan_performed",
    "prompt_injection_marker_applied",
    "parser_output_produced",
    "high_confidence_evidence_write_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "job_creation_performed",
    "state_transition_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "phase2_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}

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
    "parser_routing_contract_id",
    "contract_state",
    "execution_ready",
    "next_gate",
    "source_binding",
    "predecessor_binding",
    "upstream_snapshot_bindings",
    "input_contract",
    "route_eligibility_contract",
    "route_registry_contract",
    "output_boundary",
    "fallback_boundary",
    "prompt_injection_boundary",
    "quality_and_evidence_boundary",
    "state_and_job_boundary",
    "phase2_entry_gate",
    "runtime_boundary",
    "rollback_contract",
    "human_status_projection",
    "truth_flags",
}

EXPECTED_NESTED_KEYS = {
    "source_binding": set(EXPECTED_SOURCE),
    "predecessor_binding": set(EXPECTED_PREDECESSOR),
    "upstream_snapshot_bindings": set(EXPECTED_UPSTREAM),
    "input_contract": {
        "mode",
        "required_fields",
        "detection_authority",
        "required_detector_contract",
        "caller_selected_parser_allowed",
        "file_type_redetection_allowed",
        "source_body_allowed",
        "source_path_allowed",
        "unbounded_error_or_text_allowed",
        "raw_metadata_boundary_blocked",
        "input_record_write_allowed",
    },
    "route_eligibility_contract": {
        "candidate_ready_combinations",
        "review_required_combinations",
        "always_review_states",
        "unsupported_states",
        "blocked_states",
        "blocked_type_values",
        "candidate_ready_action",
        "review_required_action",
        "unsupported_action",
        "blocked_action",
        "generic_parser_fallback_allowed",
        "unknown_type_route_allowed",
        "caller_override_allowed",
    },
    "route_registry_contract": {
        "registry_id",
        "registry_state",
        "routes",
        "route_family_count",
        "supported_type_count",
        "parser_implementations",
        "assigned_parser_versions",
        "parser_availability_required_before_dispatch",
        "missing_parser_action",
        "route_execution_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "remote_parser_lookup_allowed",
    },
    "output_boundary": {
        "detailed_contract_owner",
        "required_parser_output_fields",
        "all_content_fields_untrusted",
        "parser_version_and_provenance_required",
        "route_decision_ref_required",
        "empty_output_is_failure",
        "output_creation_allowed",
        "direct_evidence_or_index_write_allowed",
        "high_confidence_evidence_write_allowed",
    },
    "fallback_boundary": {
        "implementation_owner",
        "attempt_history_required",
        "attempt_parser_version_required",
        "bounded_error_required",
        "stop_reason_required",
        "silent_drop_allowed",
        "silent_parser_switch_allowed",
        "route_unavailable_action",
        "fallback_execution_allowed",
    },
    "prompt_injection_boundary": {
        "implementation_owner",
        "source_text_label",
        "forbidden_interpretations",
        "marker_required_before_downstream_model",
        "source_text_can_override_system_rules",
        "source_text_can_authorize_tools",
        "marker_application_allowed",
        "prompt_injection_scan_allowed",
    },
    "quality_and_evidence_boundary": {
        "route_decision_fact_level",
        "quality_gate_required_before_downstream",
        "missing_quality_action",
        "review_required_for_provisional_route",
        "evidence_promotion_allowed",
        "evidence_ledger_write_allowed",
        "audit_write_allowed",
        "manifest_or_index_mutation_allowed",
        "report_or_database_write_allowed",
        "original_or_delivered_output_mutation_allowed",
    },
    "state_and_job_boundary": {
        "job_type",
        "state_model_owner",
        "route_contract_owner",
        "job_creation_allowed",
        "queue_admission_allowed",
        "claim_or_lock_allowed",
        "state_transition_allowed",
        "attempt_mutation_allowed",
        "terminal_history_change_allowed",
    },
    "phase2_entry_gate": {
        "gate_id",
        "required_conditions",
        "entry_authorized",
        "must_run_separately",
        "dependency_install_allowed",
    },
    "runtime_boundary": {
        "parser_registry_runtime_load_allowed",
        "route_evaluation_allowed",
        "parser_selection_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "fallback_execution_allowed",
        "source_file_access_allowed",
        "backend_or_worker_start_allowed",
        "external_api_allowed",
        "persistent_write_allowed",
        "database_connection_allowed",
        "production_activation_allowed",
    },
    "rollback_contract": {
        "scope",
        "rollback_target",
        "delete_or_cleanup_source_allowed",
        "manifest_evidence_audit_index_report_mutation_allowed",
        "github_or_app_state_change_allowed",
    },
    "human_status_projection": set(EXPECTED_HUMAN_STATUS),
    "truth_flags": {"taskpack_source_read_performed"} | FALSE_TRUTH_FLAGS,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_show_bytes(repo_root: Path, commit: str, ref: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{ref}"],
        cwd=repo_root,
        stderr=subprocess.DEVNULL,
    )


def live_source_valid(repo_root: Optional[Path] = None) -> bool:
    """Rehash only the explicitly approved taskpack files and member."""

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    try:
        archive = Path(EXPECTED_SOURCE["source_archive_path"])
        source_index = root / EXPECTED_SOURCE["source_index_ref"]
        if (
            not archive.is_file()
            or _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]
            or _sha256(ROADMAP_SOURCE_PATH) != EXPECTED_SOURCE["roadmap_sha256"]
            or _sha256(INSTRUCTIONS_SOURCE_PATH)
            != EXPECTED_SOURCE["instructions_sha256"]
            or _sha256(source_index) != EXPECTED_SOURCE["source_index_sha256"]
        ):
            return False
        with ZipFile(archive) as source_zip:
            matches = [
                name
                for name in source_zip.namelist()
                if name == EXPECTED_SOURCE["source_member"]
            ]
            if len(matches) != EXPECTED_SOURCE["source_member_match_count"]:
                return False
            member_hash = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
        return member_hash == EXPECTED_SOURCE["source_member_sha256"]
    except (OSError, KeyError, TypeError, ValueError):
        return False


def predecessor_valid(repo_root: Optional[Path] = None) -> bool:
    """Verify the committed Stage045 review identity, ancestry, and verdict."""

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    commit = PREDECESSOR_COMMIT
    try:
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", commit],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        kmids_tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:KM_IDSystem"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        review_run = json.loads(
            _git_show_bytes(root, commit, PREDECESSOR_RUN_REF).decode("utf-8")
        )
    except (
        OSError,
        subprocess.CalledProcessError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return False
    return (
        observed
        == [
            commit,
            EXPECTED_PREDECESSOR["stage045_review_root_tree"],
            EXPECTED_PREDECESSOR["stage045_review_parent"],
        ]
        and kmids_tree == EXPECTED_PREDECESSOR["stage045_review_kmids_tree"]
        and ancestor
        and isinstance(review_run, dict)
        and review_run.get("stage") == "STAGE-045"
        and review_run.get("task_id") == "IDS-V0_1-STAGE045-REVIEW"
        and review_run.get("acceptance_id") == "ACC-STAGE-045"
        and review_run.get("result")
        == EXPECTED_PREDECESSOR["stage045_review_result"]
        and review_run.get("stage_review_status")
        == EXPECTED_PREDECESSOR["stage045_review_status"]
        and review_run.get("open_finding_count") == 0
        and review_run.get("resolved_finding_count")
        == review_run.get("finding_count")
        and review_run.get("approved_sources_live_exact") is True
        and review_run.get("stage046_started") is False
        and review_run.get("stage046_entry_allowed") is False
        and review_run.get("batch_review_performed") is False
        and review_run.get("github_upload_allowed") is False
    )


def upstream_snapshot_valid(repo_root: Optional[Path] = None) -> bool:
    """Rehash every upstream artifact from the immutable predecessor commit."""

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    try:
        for item in EXPECTED_UPSTREAM.values():
            if item["snapshot_commit"] != PREDECESSOR_COMMIT:
                return False
            payload = _git_show_bytes(root, PREDECESSOR_COMMIT, item["ref"])
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                return False
    except (OSError, KeyError, subprocess.CalledProcessError):
        return False
    return True


def _nested_shapes_exact(value: Mapping[str, Any]) -> bool:
    for name, expected_keys in EXPECTED_NESTED_KEYS.items():
        item = value.get(name)
        if not isinstance(item, Mapping) or set(item) != expected_keys:
            return False
    upstream = value.get("upstream_snapshot_bindings")
    if not isinstance(upstream, Mapping):
        return False
    return all(
        isinstance(item, Mapping)
        and set(item) == {"ref", "sha256", "snapshot_commit"}
        for item in upstream.values()
    )


def evaluate_contract(
    contract: Any,
    root: Optional[Path] = None,
) -> Dict[str, bool]:
    """Return independently inspectable, fail-closed contract checks."""

    project_root = Path(root) if root is not None else PROJECT_ROOT
    repo_root = project_root.parent
    value: Mapping[str, Any] = contract if isinstance(contract, Mapping) else {}
    checks: Dict[str, bool] = {}
    checks["root_exact_shape"] = (
        isinstance(contract, Mapping) and set(value) == EXPECTED_ROOT_KEYS
    )
    checks["nested_exact_shapes"] = (
        isinstance(contract, Mapping) and _nested_shapes_exact(value)
    )
    checks["canonical_contract_identity"] = (
        isinstance(contract, Mapping)
        and _canonical_sha256(value) == EXPECTED_CANONICAL_CONTRACT_SHA256
    )
    checks["identity"] = (
        value.get("schema_version") == "ids.stage046.parser_routing.phase1.v1"
        and value.get("stage") == "STAGE-046"
        and value.get("phase") == "Phase 1"
        and value.get("task_id") == "IDS-V0_1-STAGE046-P1"
        and value.get("acceptance_id") == "ACC-STAGE-046"
        and value.get("local_code") == "D08-S002"
        and value.get("domain") == "D08"
        and value.get("entrance") == "IDS_SYSTEM_OPERATIONS"
        and value.get("pursuing_goal")
        == "SELECT_EXPLICIT_PARSER_ROUTE_FOR_GOVERNED_FILE_TYPE_WITHOUT_DISPATCH"
        and value.get("parser_routing_contract_id")
        == "ids.parser_routing.v0_1.stage046.p1"
        and value.get("contract_state")
        == "PHASE1_ENGINEERING_CONTRACT_PARSER_DISPATCH_DISABLED"
        and value.get("execution_ready") is False
        and value.get("next_gate") == "IDS-STAGE046-P2-GATE"
    )
    checks["source_binding_exact"] = value.get("source_binding") == EXPECTED_SOURCE
    checks["source_live"] = live_source_valid(repo_root)
    checks["predecessor_binding_exact"] = (
        value.get("predecessor_binding") == EXPECTED_PREDECESSOR
    )
    checks["predecessor_live"] = predecessor_valid(repo_root)
    checks["upstream_snapshot_bindings_exact"] = (
        value.get("upstream_snapshot_bindings") == EXPECTED_UPSTREAM
    )
    checks["upstream_snapshot_live"] = upstream_snapshot_valid(repo_root)

    input_contract = value.get("input_contract", {})
    checks["stage045_reference_only_input"] = (
        isinstance(input_contract, Mapping)
        and input_contract.get("mode")
        == "REFERENCE_ONLY_STAGE045_DETECTION_RESULT"
        and input_contract.get("required_fields") == EXPECTED_INPUT_FIELDS
        and input_contract.get("detection_authority") == "STAGE-045"
        and input_contract.get("required_detector_contract")
        == "ids.file_type_detector.v0_1.stage045.p2"
        and input_contract.get("caller_selected_parser_allowed") is False
        and input_contract.get("file_type_redetection_allowed") is False
        and input_contract.get("source_body_allowed") is False
        and input_contract.get("source_path_allowed") is False
        and input_contract.get("unbounded_error_or_text_allowed") is False
        and input_contract.get("raw_metadata_boundary_blocked") is True
        and input_contract.get("input_record_write_allowed") is False
    )

    eligibility = value.get("route_eligibility_contract", {})
    checks["route_eligibility_fail_closed"] = (
        isinstance(eligibility, Mapping)
        and eligibility.get("candidate_ready_combinations")
        == ["TYPE_CONFIRMED:HIGH"]
        and eligibility.get("review_required_combinations")
        == ["TYPE_PROVISIONAL:MEDIUM", "TYPE_PROVISIONAL:LOW"]
        and eligibility.get("always_review_states")
        == [
            "TYPE_CONFLICT_REVIEW_REQUIRED",
            "TYPE_UNKNOWN_REVIEW_REQUIRED",
        ]
        and eligibility.get("unsupported_states") == ["TYPE_UNSUPPORTED"]
        and eligibility.get("blocked_states") == ["TYPE_INPUT_BLOCKED"]
        and eligibility.get("blocked_type_values")
        == ["UNKNOWN", "CORRUPT_OR_UNREADABLE"]
        and eligibility.get("candidate_ready_action")
        == "ROUTE_CANDIDATE_READY_NOT_EXECUTED"
        and eligibility.get("review_required_action")
        == "ROUTE_REVIEW_REQUIRED"
        and eligibility.get("unsupported_action") == "ROUTE_UNSUPPORTED"
        and eligibility.get("blocked_action") == "ROUTE_BLOCKED"
        and eligibility.get("generic_parser_fallback_allowed") is False
        and eligibility.get("unknown_type_route_allowed") is False
        and eligibility.get("caller_override_allowed") is False
    )

    registry = value.get("route_registry_contract", {})
    checks["static_route_registry_no_dispatch"] = (
        isinstance(registry, Mapping)
        and registry.get("registry_id")
        == "ids.parser_route_registry.v0_1.stage046.p1"
        and registry.get("registry_state")
        == "STATIC_CANDIDATE_REGISTRY_RUNTIME_DISABLED"
        and registry.get("routes") == EXPECTED_ROUTES
        and registry.get("route_family_count") == 6
        and registry.get("supported_type_count") == 8
        and registry.get("parser_implementations") == []
        and registry.get("assigned_parser_versions") == []
        and registry.get("parser_availability_required_before_dispatch") is True
        and registry.get("missing_parser_action")
        == "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE"
        and registry.get("route_execution_allowed") is False
        and registry.get("parser_dispatch_allowed") is False
        and registry.get("parser_execution_allowed") is False
        and registry.get("remote_parser_lookup_allowed") is False
    )

    output = value.get("output_boundary", {})
    checks["stage047_output_boundary"] = (
        isinstance(output, Mapping)
        and output.get("detailed_contract_owner") == "STAGE-047"
        and output.get("required_parser_output_fields") == EXPECTED_OUTPUT_FIELDS
        and output.get("all_content_fields_untrusted") is True
        and output.get("parser_version_and_provenance_required") is True
        and output.get("route_decision_ref_required") is True
        and output.get("empty_output_is_failure") is True
        and output.get("output_creation_allowed") is False
        and output.get("direct_evidence_or_index_write_allowed") is False
        and output.get("high_confidence_evidence_write_allowed") is False
    )

    fallback = value.get("fallback_boundary", {})
    checks["stage048_fallback_boundary"] = (
        isinstance(fallback, Mapping)
        and fallback.get("implementation_owner") == "STAGE-048"
        and fallback.get("attempt_history_required") is True
        and fallback.get("attempt_parser_version_required") is True
        and fallback.get("bounded_error_required") is True
        and fallback.get("stop_reason_required") is True
        and fallback.get("silent_drop_allowed") is False
        and fallback.get("silent_parser_switch_allowed") is False
        and fallback.get("route_unavailable_action") == "OWNER_REVIEW_REQUIRED"
        and fallback.get("fallback_execution_allowed") is False
    )

    prompt = value.get("prompt_injection_boundary", {})
    checks["stage050_untrusted_text_boundary"] = (
        isinstance(prompt, Mapping)
        and prompt.get("implementation_owner") == "STAGE-050"
        and prompt.get("source_text_label") == "UNTRUSTED_EVIDENCE_TEXT"
        and prompt.get("forbidden_interpretations")
        == ["SYSTEM_INSTRUCTION", "TOOL_INSTRUCTION", "POLICY", "CONTROL_COMMAND"]
        and prompt.get("marker_required_before_downstream_model") is True
        and prompt.get("source_text_can_override_system_rules") is False
        and prompt.get("source_text_can_authorize_tools") is False
        and prompt.get("marker_application_allowed") is False
        and prompt.get("prompt_injection_scan_allowed") is False
    )

    quality = value.get("quality_and_evidence_boundary", {})
    checks["quality_and_evidence_closed"] = (
        isinstance(quality, Mapping)
        and quality.get("route_decision_fact_level") == "CANDIDATE"
        and quality.get("quality_gate_required_before_downstream") is True
        and quality.get("missing_quality_action") == "BLOCK_DOWNSTREAM_PROMOTION"
        and quality.get("review_required_for_provisional_route") is True
        and all(
            quality.get(name) is False
            for name in (
                "evidence_promotion_allowed",
                "evidence_ledger_write_allowed",
                "audit_write_allowed",
                "manifest_or_index_mutation_allowed",
                "report_or_database_write_allowed",
                "original_or_delivered_output_mutation_allowed",
            )
        )
    )

    state = value.get("state_and_job_boundary", {})
    checks["stage037_job_boundary_closed"] = (
        isinstance(state, Mapping)
        and state.get("job_type") == "PARSE"
        and state.get("state_model_owner") == "STAGE-037"
        and state.get("route_contract_owner") == "STAGE-046"
        and all(
            state.get(name) is False
            for name in (
                "job_creation_allowed",
                "queue_admission_allowed",
                "claim_or_lock_allowed",
                "state_transition_allowed",
                "attempt_mutation_allowed",
                "terminal_history_change_allowed",
            )
        )
    )

    phase2 = value.get("phase2_entry_gate", {})
    checks["phase2_separate_and_locked"] = (
        isinstance(phase2, Mapping)
        and phase2.get("gate_id") == "IDS-STAGE046-P2-GATE"
        and phase2.get("required_conditions") == EXPECTED_PHASE2_CONDITIONS
        and phase2.get("entry_authorized") is False
        and phase2.get("must_run_separately") is True
        and phase2.get("dependency_install_allowed") is False
    )

    runtime = value.get("runtime_boundary", {})
    checks["runtime_disabled"] = (
        isinstance(runtime, Mapping)
        and all(item is False for item in runtime.values())
    )

    rollback = value.get("rollback_contract", {})
    checks["rollback_nondestructive"] = (
        isinstance(rollback, Mapping)
        and rollback.get("scope")
        == "STAGE046_PHASE1_CONTRACT_AND_GOVERNANCE_ONLY"
        and rollback.get("rollback_target") == "STAGE045_REVIEWED_LOCAL_SNAPSHOT"
        and rollback.get("delete_or_cleanup_source_allowed") is False
        and rollback.get(
            "manifest_evidence_audit_index_report_mutation_allowed"
        ) is False
        and rollback.get("github_or_app_state_change_allowed") is False
    )
    checks["human_status_exact"] = (
        value.get("human_status_projection") == EXPECTED_HUMAN_STATUS
    )
    truth = value.get("truth_flags", {})
    checks["truth_flags"] = (
        isinstance(truth, Mapping)
        and truth.get("taskpack_source_read_performed") is True
        and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
    )
    return checks


def build_stage046_phase1_report(
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build the stable Phase1 machine report; never execute a parser."""

    project_root = Path(root) if root is not None else PROJECT_ROOT
    contract_path = project_root / CONTRACT_RELATIVE
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        contract = {}
    checks = evaluate_contract(contract, root=project_root)
    valid = bool(checks) and all(checks.values())
    return {
        "schema_version": "ids.stage046.parser_routing.phase1.report.v1",
        "stage": "STAGE-046",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE046-P1",
        "acceptance_id": "ACC-STAGE-046",
        "valid": valid,
        "result": (
            "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED"
            if valid
            else "FAIL_CLOSED"
        ),
        "contract_state": (
            contract.get("contract_state") if isinstance(contract, dict) else None
        ),
        "next_gate": (
            "IDS-STAGE046-P2-GATE" if valid else "IDS-STAGE046-P1-GATE"
        ),
        "route_family_count": len(EXPECTED_ROUTES),
        "supported_type_count": sum(
            len(item["accepted_types"]) for item in EXPECTED_ROUTES
        ),
        "required_output_field_count": len(EXPECTED_OUTPUT_FIELDS),
        "execution_ready": False,
        "parser_dispatch_allowed": False,
        "checks": checks,
        "source_file_open_performed": False,
        "file_type_redetection_performed": False,
        "parser_registry_runtime_loaded": False,
        "parser_route_evaluation_performed": False,
        "parser_selected": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "prompt_injection_marker_applied": False,
        "parser_output_produced": False,
        "evidence_promotion_performed": False,
        "job_creation_performed": False,
        "state_transition_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "raw_metadata_content_accessed": False,
        "production_runtime_activation_performed": False,
        "phase2_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage046_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
