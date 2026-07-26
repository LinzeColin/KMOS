#!/usr/bin/env python3
"""Validate and exercise the STAGE-046 Phase 2 metadata-only router."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CONTRACT_PATH = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "parser_routing"
    / "stage046_parser_routing_runtime_contract.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/"
    "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/"
    "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)

ROUTER_VERSION = "ids.parser_router.v0_1.stage046.p2"
REGISTRY_VERSION = "ids.parser_route_registry.v0_1.stage046.p2"
DETECTOR_VERSION = "ids.file_type_detector.v0_1.stage045.p2"
UNASSIGNED_VERSION = "UNASSIGNED_NOT_IMPLEMENTED"
EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "61b8e85f35e2762757ba4a5a088f74adab62aaf5b7dd8205dcad125d521d516c"
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
        "STAGE-046_解析器路由合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
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
    "stage046_phase1_commit": "c82e4e928b167c718d462dc8cef3eed5b5dbb3ea",
    "stage046_phase1_root_tree": "403e4057c028667c23a35588f09b3c00ebb51735",
    "stage046_phase1_kmids_tree": "c59be0f27521a15dc876656c753ee9b503611f94",
    "stage046_phase1_parent": "76027b8dc89e325c212d492d7f5df88357ea7112",
    "stage046_phase1_status": "stage046_phase1_completed",
    "stage046_phase1_result": "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED",
}

PHASE1_BINDINGS = {
    "stage046_phase1_entry_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE046_ENTRY_CONTRACT.md",
        "379f5068c1a834165125ea1a2ed1655b248476873504962bc3908fb38613801b",
    ),
    "stage046_phase1_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md",
        "12a1f889eab68a77a02e8c34fdb7f074ec8a40c081f004abc4063bb430c80af6",
    ),
    "stage046_phase1_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_contract.json",
        "5c145dba0ba2246b6daa33da0098b4b2ee2a48a53cfec993261d70596706c1fd",
    ),
    "stage046_phase1_checker_ref": (
        "KM_IDSystem/scripts/check_parser_routing.py",
        "eedea73a6f2a640f4f1b8836119ca9fe73170053e7b084abfed004d52c563ff8",
    ),
    "stage046_phase1_test_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage046_parser_routing.py",
        "947fe518cd799297026ec32ea5707f9d6812524b83518cb014122e392906a74e",
    ),
    "stage046_phase1_run_ref": (
        "KM_IDSystem/machine/runs/2026-07-20-stage046-p1-local.json",
        "60370c3a60535e191a68e5d8f30b49668d0ddae52f3400eafa8fd609ea84e473",
    ),
}

ROUTES = [
    {
        "route_id": "ROUTE_PDF",
        "accepted_types": ["PDF"],
        "parser_family": "PDF_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_OOXML_WORD",
        "accepted_types": ["DOCX"],
        "parser_family": "OOXML_WORD_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_OOXML_WORKBOOK",
        "accepted_types": ["XLSX"],
        "parser_family": "OOXML_WORKBOOK_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_DELIMITED_TEXT",
        "accepted_types": ["CSV"],
        "parser_family": "DELIMITED_TEXT_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_PLAIN_TEXT",
        "accepted_types": ["TXT"],
        "parser_family": "PLAIN_TEXT_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_IMAGE",
        "accepted_types": ["PNG", "JPEG", "TIFF"],
        "parser_family": "IMAGE_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
]
TYPE_ROUTE = {
    file_type: route
    for route in ROUTES
    for file_type in route["accepted_types"]
}
SUPPORTED_TYPES = set(TYPE_ROUTE)
ALLOWED_TYPES = SUPPORTED_TYPES | {
    "UNKNOWN",
    "CORRUPT_OR_UNREADABLE",
    "UNSUPPORTED",
}
ALLOWED_STATES = {
    "TYPE_CONFIRMED",
    "TYPE_PROVISIONAL",
    "TYPE_CONFLICT_REVIEW_REQUIRED",
    "TYPE_UNKNOWN_REVIEW_REQUIRED",
    "TYPE_UNSUPPORTED",
    "TYPE_INPUT_BLOCKED",
}
ALLOWED_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}

REQUEST_FIELDS = [
    "schema_version",
    "routing_request_id",
    "detection_request_id",
    "detection_result_id",
    "source_fingerprint_ref",
    "source_identity_ref",
    "detected_type",
    "detection_state",
    "detection_confidence",
    "detection_evidence_ref",
    "detector_contract_version",
    "parser_registry_version",
    "evidence_text_marker_applied",
    "requested_at",
]
RESULT_FIELDS = [
    "schema_version",
    "routing_request_id",
    "router_version",
    "registry_version",
    "detection_request_id",
    "detection_result_id",
    "detection_result_identity_status",
    "detected_type",
    "detection_state",
    "detection_confidence",
    "route_action",
    "candidate_route_id",
    "parser_family",
    "parser_version",
    "parser_version_status",
    "dispatch_block_reason",
    "route_fact_level",
    "routing_confidence",
    "evidence_text_label",
    "evidence_text_interpretation",
    "evidence_text_marker_preserved",
    "system_instruction_allowed",
    "tool_authorization_allowed",
    "policy_override_allowed",
    "errors",
    "human_status",
    "in_memory_only",
    "persisted",
    "output_refs",
    "parser_route_evaluation_performed",
    "route_candidate_selected",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "prompt_injection_scan_performed",
    "runtime_prompt_injection_marker_applied",
    "parser_output_produced",
    "high_confidence_evidence_write_performed",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "persistent_state_write_performed",
    "production_runtime_activation_performed",
]

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "metadata_only_routing_requests_evaluated",
    "static_route_registry_loaded_in_memory",
    "parser_route_evaluation_performed",
    "route_candidate_selected",
    "parser_version_status_recorded",
    "detection_result_identity_verified",
    "evidence_text_classification_enforced",
    "phase2_started",
}
FALSE_TRUTH_FLAGS = {
    "source_file_open_performed",
    "filesystem_scan_performed",
    "file_hash_performed",
    "file_type_redetection_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "external_parser_registry_loaded",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "differential_parser_evaluation_performed",
    "prompt_injection_scan_performed",
    "runtime_prompt_injection_marker_applied",
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
    "phase3_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}

ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "execution_mode",
    "router_contract_id",
    "router_version",
    "contract_state",
    "next_gate",
    "source_binding",
    "phase1_predecessor_binding",
    "phase1_snapshot_bindings",
    "route_policy",
    "request_contract",
    "route_registry",
    "result_contract",
    "evidence_text_contract",
    "quality_and_state_boundary",
    "runtime_boundary",
    "phase3_entry_gate",
    "rollback_contract",
    "human_status_projection",
    "truth_flags",
}
NESTED_KEYS = {
    "source_binding": set(SOURCE_BINDING),
    "phase1_predecessor_binding": set(PREDECESSOR_BINDING),
    "phase1_snapshot_bindings": set(PHASE1_BINDINGS),
    "route_policy": {
        "detection_authority",
        "required_detector_contract",
        "candidate_ready_combinations",
        "review_required_combinations",
        "always_review_states",
        "unsupported_states",
        "blocked_states",
        "blocked_types",
        "candidate_action",
        "review_action",
        "unsupported_action",
        "blocked_action",
        "generic_parser_allowed",
        "caller_override_allowed",
        "unknown_type_route_allowed",
    },
    "request_contract": {
        "schema_version",
        "mode",
        "required_fields",
        "required_detector_contract",
        "required_parser_registry_version",
        "detection_result_id_required",
        "detection_result_id_formula",
        "detection_result_projection_fields",
        "detection_result_identity_scope",
        "strict_utc_required",
        "bounded_reference_max_chars",
        "source_identity_ref_pattern",
        "detection_evidence_ref_pattern",
        "path_like_reference_allowed",
        "invalid_input_echo_allowed",
        "source_path_allowed",
        "source_body_allowed",
        "source_text_allowed",
        "caller_selected_parser_allowed",
        "file_type_redetection_allowed",
        "unbounded_error_allowed",
        "raw_metadata_boundary_blocked",
        "input_record_write_allowed",
    },
    "route_registry": {
        "registry_id",
        "registry_state",
        "routes",
        "route_family_count",
        "supported_type_count",
        "parser_implementation_count",
        "assigned_parser_version_count",
        "parser_version_status",
        "generic_parser_allowed",
        "remote_registry_lookup_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
    },
    "result_contract": {
        "schema_version",
        "required_fields",
        "route_fact_levels",
        "route_fact_level_by_action",
        "invalid_result_fact_level",
        "detection_result_identity_status_required",
        "invalid_input_echo_allowed",
        "invalid_marker_preservation_allowed",
        "parser_version_record_required",
        "detection_confidence_preserved",
        "candidate_route_is_dispatch_authorization",
        "output_creation_allowed",
        "empty_output_is_not_success",
        "persisted",
    },
    "evidence_text_contract": {
        "upstream_marker_field",
        "source_text_label",
        "interpretation",
        "marker_preservation_required",
        "source_content_accepted",
        "source_text_can_be_system_instruction",
        "source_text_can_authorize_tools",
        "source_text_can_override_policy",
        "prompt_injection_implementation_owner",
        "prompt_injection_scan_allowed",
        "runtime_marker_application_allowed",
    },
    "quality_and_state_boundary": {
        "parser_output_contract_owner",
        "fallback_implementation_owner",
        "differential_evaluation_owner",
        "prompt_injection_owner",
        "parse_job_state_owner",
        "quality_gate_required_before_downstream",
        "missing_quality_action",
        "evidence_promotion_allowed",
        "manifest_or_index_mutation_allowed",
        "audit_or_database_write_allowed",
        "job_creation_or_state_transition_allowed",
        "fallback_or_parser_switch_allowed",
        "silent_drop_allowed",
    },
    "runtime_boundary": {
        "metadata_only_route_evaluation_allowed",
        "static_registry_in_memory_allowed",
        "source_file_access_allowed",
        "file_type_redetection_allowed",
        "external_parser_registry_load_allowed",
        "parser_selection_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "fallback_execution_allowed",
        "differential_parser_evaluation_allowed",
        "prompt_injection_scan_allowed",
        "backend_or_worker_start_allowed",
        "external_api_allowed",
        "persistent_write_allowed",
        "database_connection_allowed",
        "production_activation_allowed",
    },
    "phase3_entry_gate": {
        "gate_id",
        "required_conditions",
        "entry_authorized",
        "must_run_separately",
        "dependency_install_allowed",
        "push_allowed",
    },
    "rollback_contract": {
        "scope",
        "rollback_target_commit",
        "rollback_target_state",
        "source_or_original_cleanup_allowed",
        "manifest_evidence_audit_index_report_mutation_allowed",
        "github_or_app_state_change_allowed",
    },
    "human_status_projection": {
        "ROUTE_CANDIDATE_SELECTED_NOT_DISPATCHED",
        "ROUTE_REVIEW_REQUIRED",
        "ROUTE_UNSUPPORTED",
        "ROUTE_BLOCKED",
        "UNTRUSTED_EVIDENCE_TEXT",
    },
    "truth_flags": TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS,
}

DETECTION_REF = re.compile(r"^detection:sha256:[0-9a-f]{64}$")
DETECTION_RESULT_REF = re.compile(
    r"^detection-result:sha256:[0-9a-f]{64}$"
)
FINGERPRINT_REF = re.compile(r"^fingerprint:sha256:[0-9a-f]{64}$")
SOURCE_IDENTITY_REF = re.compile(
    r"^source:[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
    r"(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63}){0,7}$"
)
DETECTION_EVIDENCE_REF = re.compile(
    r"^evidence:stage045:[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
    r"(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63}){0,7}$"
)
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

DETECTION_RESULT_PROJECTION_FIELDS = [
    "detection_request_id",
    "source_fingerprint_ref",
    "source_identity_ref",
    "detected_type",
    "detection_state",
    "detection_confidence",
    "detection_evidence_ref",
    "detector_contract_version",
    "evidence_text_marker_applied",
]
ROUTE_FACT_LEVEL_BY_ACTION = {
    "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE": "CANDIDATE",
    "ROUTE_REVIEW_REQUIRED": "REVIEW_REQUIRED",
    "ROUTE_UNSUPPORTED": "UNSUPPORTED",
    "ROUTE_BLOCKED": "BLOCKED",
}

HUMAN_STATUS = {
    "CANDIDATE_BLOCKED": "已确定候选解析路线，但解析器实现尚未提供，未执行分派",
    "REVIEW": "检测状态或置信度不足，解析路线需要人工复核",
    "UNSUPPORTED": "当前文件类型没有受支持的解析路线",
    "BLOCKED": "路由请求或上游检测状态无效，已失败关闭",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(file: Path) -> str:
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def _source_identity_ref_valid(value: Any) -> bool:
    return isinstance(value, str) and bool(SOURCE_IDENTITY_REF.fullmatch(value))


def _detection_evidence_ref_valid(value: Any) -> bool:
    return isinstance(value, str) and bool(DETECTION_EVIDENCE_REF.fullmatch(value))


def _detection_result_projection(values: Mapping[str, Any]) -> dict[str, Any]:
    return {name: values[name] for name in DETECTION_RESULT_PROJECTION_FIELDS}


def _detection_result_id(values: Mapping[str, Any]) -> str:
    return "detection-result:sha256:" + _canonical_sha256(
        _detection_result_projection(values)
    )


def _rfc3339_utc_valid(value: Any) -> bool:
    if not isinstance(value, str) or not RFC3339_UTC.fullmatch(value):
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def live_source_valid() -> bool:
    try:
        archive = Path(SOURCE_BINDING["source_archive_path"])
        if _sha256(archive) != SOURCE_BINDING["source_archive_sha256"]:
            return False
        with ZipFile(archive) as bundle:
            matches = [
                name
                for name in bundle.namelist()
                if name == SOURCE_BINDING["source_member"]
            ]
            if len(matches) != SOURCE_BINDING["source_member_match_count"]:
                return False
            member_sha = hashlib.sha256(bundle.read(matches[0])).hexdigest()
            if member_sha != SOURCE_BINDING["source_member_sha256"]:
                return False
        return (
            _sha256(ROADMAP_SOURCE_PATH) == SOURCE_BINDING["roadmap_sha256"]
            and _sha256(INSTRUCTIONS_SOURCE_PATH)
            == SOURCE_BINDING["instructions_sha256"]
        )
    except (OSError, BadZipFile, KeyError, IndexError):
        return False


def predecessor_live() -> bool:
    commit = PREDECESSOR_BINDING["stage046_phase1_commit"]
    try:
        observed = {
            "stage046_phase1_commit": _git("rev-parse", commit).stdout.strip(),
            "stage046_phase1_root_tree": _git(
                "show", "-s", "--format=%T", commit
            ).stdout.strip(),
            "stage046_phase1_kmids_tree": _git(
                "rev-parse", f"{commit}:KM_IDSystem"
            ).stdout.strip(),
            "stage046_phase1_parent": _git(
                "rev-parse", f"{commit}^"
            ).stdout.strip(),
            "stage046_phase1_status": "stage046_phase1_completed",
            "stage046_phase1_result": (
                "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED"
            ),
        }
        ancestor = _git(
            "merge-base", "--is-ancestor", commit, "HEAD", check=False
        ).returncode == 0
        return observed == PREDECESSOR_BINDING and ancestor
    except (OSError, subprocess.CalledProcessError):
        return False


def phase1_snapshot_live() -> bool:
    commit = PREDECESSOR_BINDING["stage046_phase1_commit"]
    try:
        for ref, expected_sha in PHASE1_BINDINGS.values():
            data = subprocess.run(
                ["git", "show", f"{commit}:{ref}"],
                cwd=REPO_ROOT,
                capture_output=True,
                check=True,
            ).stdout
            if hashlib.sha256(data).hexdigest() != expected_sha:
                return False
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _nested_shapes_exact(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    for name, expected_keys in NESTED_KEYS.items():
        nested = value.get(name)
        if not isinstance(nested, Mapping) or set(nested) != expected_keys:
            return False
    bindings = value.get("phase1_snapshot_bindings", {})
    return all(
        isinstance(item, Mapping)
        and set(item) == {"ref", "sha256", "snapshot_commit"}
        for item in bindings.values()
    )


def evaluate_runtime_contract(contract: Any) -> dict[str, bool]:
    value = contract if isinstance(contract, Mapping) else {}
    source = value.get("source_binding", {})
    predecessor = value.get("phase1_predecessor_binding", {})
    snapshots = value.get("phase1_snapshot_bindings", {})
    policy = value.get("route_policy", {})
    request = value.get("request_contract", {})
    registry = value.get("route_registry", {})
    result = value.get("result_contract", {})
    evidence = value.get("evidence_text_contract", {})
    quality = value.get("quality_and_state_boundary", {})
    runtime = value.get("runtime_boundary", {})
    phase3 = value.get("phase3_entry_gate", {})
    rollback = value.get("rollback_contract", {})
    human = value.get("human_status_projection", {})
    truth = value.get("truth_flags", {})
    normalized_snapshots = {
        name: (item.get("ref"), item.get("sha256"))
        for name, item in snapshots.items()
        if isinstance(item, Mapping)
    }
    checks = {
        "root_exact_shape": set(value) == ROOT_KEYS,
        "nested_exact_shapes": _nested_shapes_exact(value),
        "canonical_contract_identity": (
            _canonical_sha256(value) == EXPECTED_CANONICAL_CONTRACT_SHA256
        ),
        "identity": (
            value.get("schema_version")
            == "ids.stage046.parser_routing.phase2.v1"
            and value.get("stage") == "STAGE-046"
            and value.get("phase") == "Phase 2"
            and value.get("task_id") == "IDS-V0_1-STAGE046-P2"
            and value.get("acceptance_id") == "ACC-STAGE-046"
            and value.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SLICE"
            and value.get("router_contract_id")
            == "ids.parser_routing.v0_1.stage046.p2"
            and value.get("router_version") == ROUTER_VERSION
            and value.get("contract_state")
            == "PHASE2_ISOLATED_ROUTING_EVALUATOR_ENABLED_PARSER_DISABLED"
            and value.get("next_gate") == "IDS-STAGE046-P3-GATE"
        ),
        "source_binding_exact": source == SOURCE_BINDING,
        "source_live": live_source_valid(),
        "predecessor_binding_exact": predecessor == PREDECESSOR_BINDING,
        "predecessor_live": predecessor_live(),
        "phase1_snapshot_bindings_exact": (
            normalized_snapshots == PHASE1_BINDINGS
            and all(
                item.get("snapshot_commit")
                == PREDECESSOR_BINDING["stage046_phase1_commit"]
                for item in snapshots.values()
                if isinstance(item, Mapping)
            )
        ),
        "phase1_snapshot_live": phase1_snapshot_live(),
        "route_policy_fail_closed": (
            policy.get("detection_authority") == "STAGE-045"
            and policy.get("required_detector_contract") == DETECTOR_VERSION
            and policy.get("candidate_ready_combinations")
            == ["TYPE_CONFIRMED:HIGH"]
            and policy.get("review_required_combinations")
            == ["TYPE_PROVISIONAL:MEDIUM", "TYPE_PROVISIONAL:LOW"]
            and policy.get("always_review_states")
            == [
                "TYPE_CONFLICT_REVIEW_REQUIRED",
                "TYPE_UNKNOWN_REVIEW_REQUIRED",
            ]
            and policy.get("unsupported_states") == ["TYPE_UNSUPPORTED"]
            and policy.get("blocked_states") == ["TYPE_INPUT_BLOCKED"]
            and policy.get("blocked_types")
            == ["UNKNOWN", "CORRUPT_OR_UNREADABLE"]
            and policy.get("candidate_action")
            == "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE"
            and policy.get("review_action") == "ROUTE_REVIEW_REQUIRED"
            and policy.get("unsupported_action") == "ROUTE_UNSUPPORTED"
            and policy.get("blocked_action") == "ROUTE_BLOCKED"
            and policy.get("generic_parser_allowed") is False
            and policy.get("caller_override_allowed") is False
            and policy.get("unknown_type_route_allowed") is False
        ),
        "request_reference_only": (
            request.get("schema_version")
            == "ids.stage046.parser_routing_request.v1"
            and request.get("mode")
            == "REFERENCE_ONLY_STAGE045_DETECTION_RESULT"
            and request.get("required_fields") == REQUEST_FIELDS
            and request.get("required_detector_contract") == DETECTOR_VERSION
            and request.get("required_parser_registry_version")
            == REGISTRY_VERSION
            and request.get("detection_result_id_required") is True
            and request.get("detection_result_id_formula")
            == "detection-result:sha256(canonical_json(exact_detection_result_projection))"
            and request.get("detection_result_projection_fields")
            == DETECTION_RESULT_PROJECTION_FIELDS
            and request.get("detection_result_identity_scope")
            == "INTEGRITY_ONLY_NOT_EXTERNAL_PROVENANCE"
            and request.get("strict_utc_required") is True
            and request.get("bounded_reference_max_chars") == 512
            and request.get("source_identity_ref_pattern")
            == SOURCE_IDENTITY_REF.pattern
            and request.get("detection_evidence_ref_pattern")
            == DETECTION_EVIDENCE_REF.pattern
            and request.get("path_like_reference_allowed") is False
            and request.get("invalid_input_echo_allowed") is False
            and request.get("source_path_allowed") is False
            and request.get("source_body_allowed") is False
            and request.get("source_text_allowed") is False
            and request.get("caller_selected_parser_allowed") is False
            and request.get("file_type_redetection_allowed") is False
            and request.get("unbounded_error_allowed") is False
            and request.get("raw_metadata_boundary_blocked") is True
            and request.get("input_record_write_allowed") is False
        ),
        "registry_exact_and_unavailable": (
            registry.get("registry_id") == REGISTRY_VERSION
            and registry.get("registry_state")
            == "STATIC_IN_MEMORY_ROUTING_POLICY_PARSER_IMPLEMENTATIONS_UNAVAILABLE"
            and registry.get("routes") == ROUTES
            and registry.get("route_family_count") == 6
            and registry.get("supported_type_count") == 8
            and registry.get("parser_implementation_count") == 0
            and registry.get("assigned_parser_version_count") == 0
            and registry.get("parser_version_status")
            == "UNASSIGNED_NOT_IMPLEMENTED_RECORDED"
            and registry.get("generic_parser_allowed") is False
            and registry.get("remote_registry_lookup_allowed") is False
            and registry.get("parser_dispatch_allowed") is False
            and registry.get("parser_execution_allowed") is False
        ),
        "result_candidate_only": (
            result.get("schema_version")
            == "ids.stage046.parser_routing_result.v1"
            and result.get("required_fields") == RESULT_FIELDS
            and result.get("route_fact_levels")
            == ["CANDIDATE", "REVIEW_REQUIRED", "UNSUPPORTED", "BLOCKED", "INVALID"]
            and result.get("route_fact_level_by_action")
            == ROUTE_FACT_LEVEL_BY_ACTION
            and result.get("invalid_result_fact_level") == "INVALID"
            and result.get("detection_result_identity_status_required") is True
            and result.get("invalid_input_echo_allowed") is False
            and result.get("invalid_marker_preservation_allowed") is False
            and result.get("parser_version_record_required") is True
            and result.get("detection_confidence_preserved") is True
            and result.get("candidate_route_is_dispatch_authorization") is False
            and result.get("output_creation_allowed") is False
            and result.get("empty_output_is_not_success") is True
            and result.get("persisted") is False
        ),
        "evidence_text_only": (
            evidence.get("upstream_marker_field")
            == "evidence_text_marker_applied"
            and evidence.get("source_text_label") == "UNTRUSTED_EVIDENCE_TEXT"
            and evidence.get("interpretation") == "EVIDENCE_ONLY"
            and evidence.get("marker_preservation_required") is True
            and evidence.get("source_content_accepted") is False
            and evidence.get("source_text_can_be_system_instruction") is False
            and evidence.get("source_text_can_authorize_tools") is False
            and evidence.get("source_text_can_override_policy") is False
            and evidence.get("prompt_injection_implementation_owner")
            == "STAGE-050"
            and evidence.get("prompt_injection_scan_allowed") is False
            and evidence.get("runtime_marker_application_allowed") is False
        ),
        "ownership_and_quality_closed": (
            quality.get("parser_output_contract_owner") == "STAGE-047"
            and quality.get("fallback_implementation_owner") == "STAGE-048"
            and quality.get("differential_evaluation_owner") == "STAGE-049"
            and quality.get("prompt_injection_owner") == "STAGE-050"
            and quality.get("parse_job_state_owner") == "STAGE-037"
            and quality.get("quality_gate_required_before_downstream") is True
            and quality.get("missing_quality_action")
            == "BLOCK_DOWNSTREAM_PROMOTION"
            and quality.get("evidence_promotion_allowed") is False
            and quality.get("manifest_or_index_mutation_allowed") is False
            and quality.get("audit_or_database_write_allowed") is False
            and quality.get("job_creation_or_state_transition_allowed") is False
            and quality.get("fallback_or_parser_switch_allowed") is False
            and quality.get("silent_drop_allowed") is False
        ),
        "runtime_isolated_and_parser_disabled": (
            runtime.get("metadata_only_route_evaluation_allowed") is True
            and runtime.get("static_registry_in_memory_allowed") is True
            and runtime.get("source_file_access_allowed") is False
            and runtime.get("file_type_redetection_allowed") is False
            and runtime.get("external_parser_registry_load_allowed") is False
            and runtime.get("parser_selection_allowed") is False
            and runtime.get("parser_dispatch_allowed") is False
            and runtime.get("parser_execution_allowed") is False
            and runtime.get("fallback_execution_allowed") is False
            and runtime.get("differential_parser_evaluation_allowed") is False
            and runtime.get("prompt_injection_scan_allowed") is False
            and runtime.get("backend_or_worker_start_allowed") is False
            and runtime.get("external_api_allowed") is False
            and runtime.get("persistent_write_allowed") is False
            and runtime.get("database_connection_allowed") is False
            and runtime.get("production_activation_allowed") is False
        ),
        "phase3_separate_and_locked": (
            phase3.get("gate_id") == "IDS-STAGE046-P3-GATE"
            and phase3.get("required_conditions")
            == [
                "SOURCE_BINDING_EXACT",
                "PHASE1_PREDECESSOR_AND_SNAPSHOT_EXACT",
                "REFERENCE_ONLY_REQUEST_VALIDATED",
                "SIX_ROUTE_FAMILIES_EIGHT_TYPES_MAPPED",
                "NON_HIGH_AND_UNKNOWN_RESULTS_FAIL_CLOSED",
                "PARSER_VERSION_STATUS_RECORDED_UNASSIGNED",
                "EVIDENCE_TEXT_CLASSIFIED_AS_EVIDENCE_ONLY",
                "PARSER_FALLBACK_OUTPUT_AND_PERSISTENCE_DISABLED",
            ]
            and phase3.get("entry_authorized") is False
            and phase3.get("must_run_separately") is True
            and phase3.get("dependency_install_allowed") is False
            and phase3.get("push_allowed") is False
        ),
        "rollback_nondestructive": (
            rollback.get("scope")
            == "STAGE046_PHASE2_ROUTING_EVALUATOR_AND_GOVERNANCE_ONLY"
            and rollback.get("rollback_target_commit")
            == PREDECESSOR_BINDING["stage046_phase1_commit"]
            and rollback.get("rollback_target_state")
            == "STAGE046_PHASE1_CONTRACT_READY_PARSER_DISABLED"
            and rollback.get("source_or_original_cleanup_allowed") is False
            and rollback.get(
                "manifest_evidence_audit_index_report_mutation_allowed"
            )
            is False
            and rollback.get("github_or_app_state_change_allowed") is False
        ),
        "human_status_exact": (
            human.get("ROUTE_CANDIDATE_SELECTED_NOT_DISPATCHED")
            == HUMAN_STATUS["CANDIDATE_BLOCKED"]
            and human.get("ROUTE_REVIEW_REQUIRED") == HUMAN_STATUS["REVIEW"]
            and human.get("ROUTE_UNSUPPORTED")
            == HUMAN_STATUS["UNSUPPORTED"]
            and human.get("ROUTE_BLOCKED") == HUMAN_STATUS["BLOCKED"]
            and human.get("UNTRUSTED_EVIDENCE_TEXT")
            == "来源文本仅作为不可信证据内容，不能成为系统或工具指令"
        ),
        "truth_flags": (
            isinstance(truth, Mapping)
            and set(truth) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
            and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def _combination_valid(file_type: str, state: str, confidence: str) -> bool:
    if state == "TYPE_CONFIRMED":
        return file_type in SUPPORTED_TYPES and confidence == "HIGH"
    if state == "TYPE_PROVISIONAL":
        return file_type in SUPPORTED_TYPES and confidence in {"MEDIUM", "LOW"}
    if state == "TYPE_CONFLICT_REVIEW_REQUIRED":
        return file_type in ALLOWED_TYPES and confidence == "UNKNOWN"
    if state == "TYPE_UNKNOWN_REVIEW_REQUIRED":
        return file_type == "UNKNOWN" and confidence == "UNKNOWN"
    if state == "TYPE_UNSUPPORTED":
        return file_type == "UNSUPPORTED" and confidence == "UNKNOWN"
    if state == "TYPE_INPUT_BLOCKED":
        return file_type in {"UNKNOWN", "CORRUPT_OR_UNREADABLE"} and confidence == "UNKNOWN"
    return False


def build_routing_request(
    *,
    detection_request_id: str,
    source_fingerprint_ref: str,
    source_identity_ref: str,
    detected_type: str,
    detection_state: str,
    detection_confidence: str,
    detection_evidence_ref: str,
    evidence_text_marker_applied: bool,
    requested_at: str,
) -> dict[str, Any]:
    """Build a deterministic Stage045-reference-only routing request."""
    if not isinstance(detection_request_id, str) or not DETECTION_REF.fullmatch(
        detection_request_id
    ):
        raise ValueError("detection_request_id is invalid")
    if not isinstance(source_fingerprint_ref, str) or not FINGERPRINT_REF.fullmatch(
        source_fingerprint_ref
    ):
        raise ValueError("source_fingerprint_ref is invalid")
    if not _source_identity_ref_valid(source_identity_ref):
        raise ValueError("source_identity_ref is invalid")
    if not _detection_evidence_ref_valid(detection_evidence_ref):
        raise ValueError("detection_evidence_ref is invalid")
    if detected_type not in ALLOWED_TYPES:
        raise ValueError("detected_type is invalid")
    if detection_state not in ALLOWED_STATES:
        raise ValueError("detection_state is invalid")
    if detection_confidence not in ALLOWED_CONFIDENCE:
        raise ValueError("detection_confidence is invalid")
    if not _combination_valid(
        detected_type, detection_state, detection_confidence
    ):
        raise ValueError("detection state/type/confidence combination is invalid")
    if not isinstance(evidence_text_marker_applied, bool):
        raise ValueError("evidence_text_marker_applied must be boolean")
    if not _rfc3339_utc_valid(requested_at):
        raise ValueError("requested_at must be a real RFC3339 UTC timestamp")
    detection_projection = {
        "detection_request_id": detection_request_id,
        "source_fingerprint_ref": source_fingerprint_ref,
        "source_identity_ref": source_identity_ref,
        "detected_type": detected_type,
        "detection_state": detection_state,
        "detection_confidence": detection_confidence,
        "detection_evidence_ref": detection_evidence_ref,
        "detector_contract_version": DETECTOR_VERSION,
        "evidence_text_marker_applied": evidence_text_marker_applied,
    }
    body = {
        "schema_version": "ids.stage046.parser_routing_request.v1",
        **detection_projection,
        "detection_result_id": _detection_result_id(detection_projection),
        "parser_registry_version": REGISTRY_VERSION,
        "requested_at": requested_at,
    }
    return {
        **body,
        "routing_request_id": "routing:sha256:" + _canonical_sha256(body),
    }


def _request_valid(request: Any) -> bool:
    if not isinstance(request, Mapping) or set(request) != set(REQUEST_FIELDS):
        return False
    try:
        body = {key: request[key] for key in REQUEST_FIELDS if key != "routing_request_id"}
        return (
            request["schema_version"]
            == "ids.stage046.parser_routing_request.v1"
            and isinstance(request["detection_request_id"], str)
            and bool(DETECTION_REF.fullmatch(request["detection_request_id"]))
            and isinstance(request["detection_result_id"], str)
            and bool(DETECTION_RESULT_REF.fullmatch(request["detection_result_id"]))
            and isinstance(request["source_fingerprint_ref"], str)
            and bool(FINGERPRINT_REF.fullmatch(request["source_fingerprint_ref"]))
            and _source_identity_ref_valid(request["source_identity_ref"])
            and request["detected_type"] in ALLOWED_TYPES
            and request["detection_state"] in ALLOWED_STATES
            and request["detection_confidence"] in ALLOWED_CONFIDENCE
            and _combination_valid(
                request["detected_type"],
                request["detection_state"],
                request["detection_confidence"],
            )
            and _detection_evidence_ref_valid(request["detection_evidence_ref"])
            and request["detector_contract_version"] == DETECTOR_VERSION
            and request["detection_result_id"] == _detection_result_id(request)
            and request["parser_registry_version"] == REGISTRY_VERSION
            and isinstance(request["evidence_text_marker_applied"], bool)
            and _rfc3339_utc_valid(request["requested_at"])
            and request["routing_request_id"]
            == "routing:sha256:" + _canonical_sha256(body)
        )
    except (KeyError, TypeError):
        return False


def _base_result(
    request: Any = None, *, request_validated: bool = False
) -> dict[str, Any]:
    if request_validated and isinstance(request, Mapping):
        getter = request.get
        marker = getter("evidence_text_marker_applied") is True
        detected_type = getter("detected_type")
        detection_state = getter("detection_state")
        detection_confidence = getter("detection_confidence")
        routing_confidence = detection_confidence
        route_fact_level = "BLOCKED"
        identity_status = "PROJECTION_DIGEST_VERIFIED"
    else:
        getter = lambda _name: None
        marker = False
        detected_type = "UNKNOWN"
        detection_state = "TYPE_INPUT_BLOCKED"
        detection_confidence = "UNKNOWN"
        routing_confidence = "UNKNOWN"
        route_fact_level = "INVALID"
        identity_status = "UNVERIFIED"
    return {
        "schema_version": "ids.stage046.parser_routing_result.v1",
        "routing_request_id": getter("routing_request_id"),
        "router_version": ROUTER_VERSION,
        "registry_version": REGISTRY_VERSION,
        "detection_request_id": getter("detection_request_id"),
        "detection_result_id": getter("detection_result_id"),
        "detection_result_identity_status": identity_status,
        "detected_type": detected_type,
        "detection_state": detection_state,
        "detection_confidence": detection_confidence,
        "route_action": "ROUTE_BLOCKED",
        "candidate_route_id": None,
        "parser_family": None,
        "parser_version": UNASSIGNED_VERSION,
        "parser_version_status": "RECORDED_UNASSIGNED",
        "dispatch_block_reason": "NOT_APPLICABLE",
        "route_fact_level": route_fact_level,
        "routing_confidence": routing_confidence,
        "evidence_text_label": (
            "UNTRUSTED_EVIDENCE_TEXT"
            if marker
            else "NO_SOURCE_TEXT_MARKER_PRESENT"
        ),
        "evidence_text_interpretation": (
            "EVIDENCE_ONLY" if marker else "EVIDENCE_ONLY_WHEN_PRESENT"
        ),
        "evidence_text_marker_preserved": marker,
        "system_instruction_allowed": False,
        "tool_authorization_allowed": False,
        "policy_override_allowed": False,
        "errors": [],
        "human_status": HUMAN_STATUS["BLOCKED"],
        "in_memory_only": True,
        "persisted": False,
        "output_refs": [],
        "parser_route_evaluation_performed": False,
        "route_candidate_selected": False,
        "parser_selected": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "prompt_injection_scan_performed": False,
        "runtime_prompt_injection_marker_applied": False,
        "parser_output_produced": False,
        "high_confidence_evidence_write_performed": False,
        "source_file_open_performed": False,
        "file_type_redetection_performed": False,
        "persistent_state_write_performed": False,
        "production_runtime_activation_performed": False,
    }


def evaluate_parser_route(request: Any) -> dict[str, Any]:
    """Evaluate one governed detection result without dispatching a parser."""
    if not _request_valid(request):
        result = _base_result()
        result["errors"] = ["INVALID_ROUTING_REQUEST"]
        return result

    result = _base_result(request, request_validated=True)
    result["parser_route_evaluation_performed"] = True
    state = request["detection_state"]
    confidence = request["detection_confidence"]
    file_type = request["detected_type"]

    if state == "TYPE_CONFIRMED" and confidence == "HIGH":
        route = TYPE_ROUTE.get(file_type)
        if route is None:
            result["errors"] = ["ROUTE_MAPPING_MISSING"]
            return result
        result.update(
            route_action="ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
            candidate_route_id=route["route_id"],
            parser_family=route["parser_family"],
            dispatch_block_reason="PARSER_IMPLEMENTATION_UNAVAILABLE",
            route_fact_level="CANDIDATE",
            route_candidate_selected=True,
            errors=["PARSER_IMPLEMENTATION_UNAVAILABLE"],
            human_status=HUMAN_STATUS["CANDIDATE_BLOCKED"],
        )
        return result

    if state in {
        "TYPE_PROVISIONAL",
        "TYPE_CONFLICT_REVIEW_REQUIRED",
        "TYPE_UNKNOWN_REVIEW_REQUIRED",
    }:
        result.update(
            route_action="ROUTE_REVIEW_REQUIRED",
            route_fact_level="REVIEW_REQUIRED",
            errors=["DETECTION_REVIEW_REQUIRED"],
            human_status=HUMAN_STATUS["REVIEW"],
        )
        return result

    if state == "TYPE_UNSUPPORTED":
        result.update(
            route_action="ROUTE_UNSUPPORTED",
            route_fact_level="UNSUPPORTED",
            errors=["FILE_TYPE_UNSUPPORTED"],
            human_status=HUMAN_STATUS["UNSUPPORTED"],
        )
        return result

    result.update(
        route_action="ROUTE_BLOCKED",
        route_fact_level="BLOCKED",
        errors=["DETECTION_INPUT_BLOCKED"],
        human_status=HUMAN_STATUS["BLOCKED"],
    )
    return result


def _control_request(
    *,
    suffix: str,
    file_type: str,
    state: str,
    confidence: str,
    marker: bool = False,
) -> dict[str, Any]:
    return build_routing_request(
        detection_request_id="detection:sha256:" + suffix * 64,
        source_fingerprint_ref="fingerprint:sha256:" + suffix * 64,
        source_identity_ref=f"source:control:{suffix}",
        detected_type=file_type,
        detection_state=state,
        detection_confidence=confidence,
        detection_evidence_ref=f"evidence:stage045:control:{suffix}",
        evidence_text_marker_applied=marker,
        requested_at="2026-07-20T03:00:00Z",
    )


def build_stage046_phase2_report() -> dict[str, Any]:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        contract = {}
    contract_checks = evaluate_runtime_contract(contract)

    pdf = evaluate_parser_route(
        _control_request(
            suffix="a",
            file_type="PDF",
            state="TYPE_CONFIRMED",
            confidence="HIGH",
            marker=True,
        )
    )
    docx = evaluate_parser_route(
        _control_request(
            suffix="b",
            file_type="DOCX",
            state="TYPE_CONFIRMED",
            confidence="HIGH",
        )
    )
    unknown = evaluate_parser_route(
        _control_request(
            suffix="c",
            file_type="UNKNOWN",
            state="TYPE_UNKNOWN_REVIEW_REQUIRED",
            confidence="UNKNOWN",
        )
    )
    controls = [pdf, docx, unknown]
    slice_checks = {
        "pdf_route_selected_dispatch_blocked": (
            pdf["candidate_route_id"] == "ROUTE_PDF"
            and pdf["parser_family"] == "PDF_PARSER"
            and pdf["route_action"]
            == "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE"
        ),
        "docx_route_selected_dispatch_blocked": (
            docx["candidate_route_id"] == "ROUTE_OOXML_WORD"
            and docx["parser_family"] == "OOXML_WORD_PARSER"
            and docx["route_action"]
            == "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE"
        ),
        "unknown_failed_closed_to_review": (
            unknown["route_action"] == "ROUTE_REVIEW_REQUIRED"
            and unknown["candidate_route_id"] is None
        ),
        "parser_version_status_recorded": all(
            item["parser_version"] == UNASSIGNED_VERSION
            and item["parser_version_status"] == "RECORDED_UNASSIGNED"
            for item in controls
        ),
        "detection_result_identity_verified": all(
            isinstance(item["detection_result_id"], str)
            and bool(DETECTION_RESULT_REF.fullmatch(item["detection_result_id"]))
            and item["detection_result_identity_status"]
            == "PROJECTION_DIGEST_VERIFIED"
            for item in controls
        ),
        "evidence_text_is_evidence_only": (
            pdf["evidence_text_label"] == "UNTRUSTED_EVIDENCE_TEXT"
            and pdf["evidence_text_interpretation"] == "EVIDENCE_ONLY"
            and pdf["system_instruction_allowed"] is False
            and pdf["tool_authorization_allowed"] is False
            and pdf["policy_override_allowed"] is False
        ),
        "no_parser_fallback_output_or_write": all(
            item["parser_selected"] is False
            and item["parser_dispatch_performed"] is False
            and item["parser_execution_performed"] is False
            and item["fallback_execution_performed"] is False
            and item["parser_output_produced"] is False
            and item["persisted"] is False
            and item["output_refs"] == []
            for item in controls
        ),
    }
    valid = (
        bool(contract_checks)
        and all(contract_checks.values())
        and all(slice_checks.values())
    )
    return {
        "schema_version": "ids.stage046.parser_routing.phase2.report.v1",
        "stage": "STAGE-046",
        "phase": "Phase 2",
        "task_id": "IDS-V0_1-STAGE046-P2",
        "acceptance_id": "ACC-STAGE-046",
        "execution_mode": (
            "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SLICE"
        ),
        "valid": valid,
        "result": (
            "PASS_ISOLATED_PARSER_ROUTING_SLICE_PARSER_DISABLED"
            if valid
            else "FAIL_CLOSED"
        ),
        "contract_checks": contract_checks,
        "slice_checks": slice_checks,
        "isolated_routing_count": len(controls),
        "routing_result_summaries": [
            {
                key: item[key]
                for key in (
                    "routing_request_id",
                    "detection_request_id",
                    "detection_result_id",
                    "detection_result_identity_status",
                    "detected_type",
                    "detection_state",
                    "detection_confidence",
                    "route_action",
                    "candidate_route_id",
                    "parser_family",
                    "parser_version",
                    "parser_version_status",
                    "route_fact_level",
                    "routing_confidence",
                    "evidence_text_label",
                    "errors",
                    "human_status",
                )
            }
            for item in controls
        ],
        "next_gate": (
            "IDS-STAGE046-P3-GATE" if valid else "IDS-STAGE046-P2-GATE"
        ),
        "metadata_only_routing_requests_evaluated": True,
        "static_route_registry_loaded_in_memory": True,
        "parser_route_evaluation_performed": True,
        "route_candidate_selected": True,
        "parser_version_status_recorded": True,
        "detection_result_identity_verified": True,
        "evidence_text_classification_enforced": True,
        "source_file_open_performed": False,
        "filesystem_scan_performed": False,
        "file_hash_performed": False,
        "file_type_redetection_performed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "real_ids_business_job_created": False,
        "external_parser_registry_loaded": False,
        "parser_selected": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "differential_parser_evaluation_performed": False,
        "prompt_injection_scan_performed": False,
        "runtime_prompt_injection_marker_applied": False,
        "parser_output_produced": False,
        "high_confidence_evidence_write_performed": False,
        "manifest_write_performed": False,
        "evidence_ledger_write_performed": False,
        "audit_write_performed": False,
        "job_creation_performed": False,
        "state_transition_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "schema_change_performed": False,
        "runtime_output_written": False,
        "production_runtime_activation_performed": False,
        "phase3_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage046_phase2_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
