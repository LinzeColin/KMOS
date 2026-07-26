#!/usr/bin/env python3
"""Validate the STAGE-045 Phase 1 file-type detection contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Mapping
from zipfile import ZipFile


CONTRACT_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/file_type_detection/"
    "stage045_file_type_detection_contract.json"
)
STATE_MODEL_RELATIVE = (
    "docs/pursuing_goal/ids_v0_1/job_state_model/"
    "stage037_job_state_model_index.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "aaaef43702a68835c7d8d729f8dec81cc7f140fff5cf9e92d3db0c40f6081c06"
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
        "STAGE-045_文件类型检测.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27"
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
    "stage044_review_commit": "97044d0b6475ebf41b4f79311164a392979305a0",
    "stage044_review_root_tree": "557791aa9f4694d80c221208b5e2dec7db6538ac",
    "stage044_review_kmids_tree": "eff34be6236b4ea3e89630961c510580aacf8259",
    "stage044_review_parent": "5da8fdf64cab35545e717900e71ccbbb5dacb11c",
    "stage044_review_status": "completed_reviewed_local",
    "stage044_review_result": "PASS_REVIEWED_LOCAL_DELETE_DISABLED",
}

EXPECTED_UPSTREAM = {
    "stage013_fingerprint_closeout_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE013_PHASE4_CLOSEOUT.md",
        "sha256": "e3e8b27ccb286c91028c6ec9ce96859cc04032ceeafd80c21ea803ee19f82049",
    },
    "stage027_reingest_boundary_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE027_PHASE1_SCOPE_BOUNDARY.md",
        "sha256": "c9c09a7ab620377eb9de75a5f53e59fd0f4cb54caa22c030f615d3021f7661b7",
    },
    "stage037_state_index_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
            "stage037_job_state_model_index.json"
        ),
        "sha256": "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    },
    "stage044_review_ref": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE044_STAGE_REVIEW.md",
        "sha256": "a8e3d765d7450146fc1649e330ad259966f4a446afdc847fc4790b73f1684916",
    },
    "stage044_review_checker_ref": {
        "ref": "KM_IDSystem/scripts/check_half_product_cleanup_stage_review.py",
        "sha256": "b67a633a20e801845c5b159a244e5e7817a3bc5c15669610becf0b65a47433e5",
    },
    "raw_data_boundary_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "IDS_METADATA_RAW_DATA_BOUNDARY.md"
        ),
        "sha256": "ad4695abf250049699a1b96b49b81432e5d5754dfe7de69c7f3056463a0a7d51",
    },
}

EXPECTED_JOB_STATES = [
    "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
    "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "DEAD_LETTERED",
    "CANCELLED",
]
EXPECTED_TYPES = [
    "PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF",
    "UNKNOWN", "CORRUPT_OR_UNREADABLE",
]
EXPECTED_DETECTION_STATES = [
    "TYPE_CONFIRMED", "TYPE_PROVISIONAL", "TYPE_CONFLICT_REVIEW_REQUIRED",
    "TYPE_UNKNOWN_REVIEW_REQUIRED", "TYPE_UNSUPPORTED", "TYPE_INPUT_BLOCKED",
]
EXPECTED_OUTPUT_FIELDS = [
    "text", "tables", "pages", "sections", "confidence", "errors",
]
EXPECTED_ROUTE_MAP = {
    "PDF": "PDF_PARSER",
    "DOCX": "OOXML_WORD_PARSER",
    "XLSX": "OOXML_WORKBOOK_PARSER",
    "CSV": "DELIMITED_TEXT_PARSER",
    "TXT": "PLAIN_TEXT_PARSER",
    "PNG": "IMAGE_PARSER",
    "JPEG": "IMAGE_PARSER",
    "TIFF": "IMAGE_PARSER",
    "UNKNOWN": "UNSUPPORTED",
    "CORRUPT_OR_UNREADABLE": "UNSUPPORTED",
}
EXPECTED_HUMAN_STATUS = {
    "TYPE_CONTRACT_READY_RUNTIME_DISABLED": (
        "文件类型检测合同已就绪，实际检测仍禁用"
    ),
    "TYPE_INPUT_BLOCKED": "输入证据不完整或不安全，文件类型检测已阻断",
    "TYPE_CONFLICT_REVIEW_REQUIRED": (
        "扩展名、MIME 或文件签名冲突，需要人工复核"
    ),
    "TYPE_UNKNOWN_REVIEW_REQUIRED": "文件类型无法可靠确认，需要人工复核",
    "TYPE_ROUTE_CANDIDATE_NOT_EXECUTED": (
        "已定义解析器候选路由，但尚未执行解析"
    ),
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed", "raw_metadata_content_accessed",
    "fake_ids_business_data_used", "real_ids_business_job_created",
    "source_file_open_performed", "file_scan_performed",
    "file_hash_performed", "extension_detection_performed",
    "mime_detection_performed", "file_signature_inspection_performed",
    "container_inspection_performed", "type_classification_runtime_performed",
    "parser_route_evaluation_performed", "parser_dispatch_performed",
    "parser_execution_performed", "fallback_execution_performed",
    "prompt_injection_scan_performed", "prompt_injection_marker_applied",
    "parser_output_produced", "high_confidence_evidence_write_performed",
    "manifest_write_performed", "evidence_ledger_write_performed",
    "audit_write_performed", "job_creation_performed",
    "state_transition_performed", "persistent_state_write_performed",
    "database_connection_performed", "schema_change_performed",
    "runtime_output_written", "production_runtime_activation_performed",
    "whole_stage_review_performed", "batch_review_performed",
    "github_upload_allowed", "app_reinstall_allowed",
}

EXPECTED_ROOT_KEYS = {
    "schema_version", "stage", "phase", "task_id", "acceptance_id",
    "local_code", "domain", "entrance", "pursuing_goal",
    "file_type_contract_id", "contract_state", "execution_ready", "next_gate",
    "source_binding", "predecessor_binding", "upstream_bindings",
    "input_contract", "signal_contract", "classification_contract",
    "parser_route_boundary", "output_contract", "fallback_contract",
    "prompt_injection_boundary", "quality_and_evidence_boundary",
    "state_and_job_boundary", "phase2_entry_gate", "runtime_boundary",
    "rollback_contract", "human_status_projection", "truth_flags",
}

EXPECTED_NESTED_KEYS = {
    "source_binding": set(EXPECTED_SOURCE),
    "predecessor_binding": set(EXPECTED_PREDECESSOR),
    "upstream_bindings": set(EXPECTED_UPSTREAM),
    "input_contract": {
        "mode", "required_fields", "approved_explicit_source_required",
        "fingerprint_provenance_required", "bounded_signal_metadata_required",
        "raw_metadata_boundary_blocked", "raw_source_body_allowed",
        "plaintext_secret_allowed", "source_file_read_allowed",
        "input_record_write_allowed",
    },
    "signal_contract": {
        "trust_order", "filename_extension_trust", "mime_trust",
        "signature_trust", "extension_only_route_allowed",
        "zip_magic_sufficient_for_ooxml", "docx_required_markers",
        "xlsx_required_markers", "text_without_magic_rule",
        "signal_conflict_action", "missing_signal_action",
        "remote_lookup_allowed", "raw_signal_payload_allowed",
    },
    "classification_contract": {
        "canonical_type_values", "detection_states", "confidence_values",
        "extension_only_max_confidence", "unknown_or_conflict_action",
        "corrupt_or_unreadable_action", "filename_overrides_other_signals",
        "parser_dispatch_allowed", "format_registry_runtime_activated",
    },
    "parser_route_boundary": {
        "detailed_contract_owner", "candidate_route_map", "route_states",
        "required_route_inputs", "route_execution_allowed",
        "parser_execution_allowed", "direct_index_or_evidence_write_allowed",
        "silent_route_selection_allowed",
    },
    "output_contract": {
        "detailed_contract_owner", "required_parser_output_fields",
        "field_types", "content_fields_are_untrusted_evidence",
        "quality_gate_required", "provenance_required",
        "parser_version_required", "parser_output_write_allowed",
        "high_confidence_evidence_write_allowed",
        "empty_output_silent_success_allowed",
        "raw_source_body_in_control_contract_allowed",
    },
    "fallback_contract": {
        "implementation_owner", "fallback_states", "silent_drop_allowed",
        "silent_parser_switch_allowed", "attempt_errors_required",
        "low_confidence_action", "unknown_type_action",
        "all_attempts_provenance_bound", "fallback_execution_allowed",
    },
    "prompt_injection_boundary": {
        "implementation_owner", "source_derived_text_label",
        "forbidden_interpretations", "marker_required_before_downstream_model",
        "source_text_can_override_system_rules",
        "source_text_can_authorize_tools", "prompt_injection_scan_performed",
        "marker_application_allowed",
    },
    "quality_and_evidence_boundary": {
        "parser_artifact_fact_level", "quality_gate_decision_required",
        "unknown_or_missing_quality_action", "evidence_promotion_allowed",
        "evidence_ledger_write_allowed", "audit_write_allowed",
        "report_generation_allowed", "direct_index_write_allowed",
        "manifest_mutation_allowed", "original_mutation_allowed",
    },
    "state_and_job_boundary": {
        "state_model_version", "state_model_owner", "job_type", "job_states",
        "runtime_owners", "job_creation_allowed", "state_transition_allowed",
        "terminal_history_change_allowed", "queue_or_worker_runtime_allowed",
    },
    "phase2_entry_gate": {
        "required_gate", "required_conditions", "phase2_must_run_separately",
        "execution_ready", "parser_dispatch_allowed", "push_allowed",
    },
    "runtime_boundary": {
        "mode", "source_file_open_allowed", "file_scan_allowed",
        "file_signature_inspection_allowed", "type_classification_runtime_allowed",
        "parser_route_evaluation_allowed", "parser_dispatch_allowed",
        "parser_execution_allowed", "fallback_execution_allowed",
        "prompt_marker_application_allowed", "persistent_write_allowed",
        "production_runtime_allowed",
    },
    "rollback_contract": {"steps", "destructive_rollback_allowed"},
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


def _live_source_valid(repo_root: Path) -> bool:
    try:
        archive = Path(EXPECTED_SOURCE["source_archive_path"])
        index_path = repo_root / EXPECTED_SOURCE["source_index_ref"]
        if (
            not archive.is_file()
            or _sha256(archive) != EXPECTED_SOURCE["source_archive_sha256"]
            or _sha256(ROADMAP_SOURCE_PATH) != EXPECTED_SOURCE["roadmap_sha256"]
            or _sha256(INSTRUCTIONS_SOURCE_PATH)
            != EXPECTED_SOURCE["instructions_sha256"]
            or _sha256(index_path) != EXPECTED_SOURCE["source_index_sha256"]
        ):
            return False
        with ZipFile(archive) as source_zip:
            matches = [
                name
                for name in source_zip.namelist()
                if name == EXPECTED_SOURCE["source_member"]
            ]
            if len(matches) != 1:
                return False
            member_hash = hashlib.sha256(source_zip.read(matches[0])).hexdigest()
        return member_hash == EXPECTED_SOURCE["source_member_sha256"]
    except (OSError, KeyError, ValueError):
        return False


def _predecessor_valid(repo_root: Path) -> bool:
    commit = EXPECTED_PREDECESSOR["stage044_review_commit"]
    try:
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", commit],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        kmids_tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:KM_IDSystem"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return (
        observed
        == [
            commit,
            EXPECTED_PREDECESSOR["stage044_review_root_tree"],
            EXPECTED_PREDECESSOR["stage044_review_parent"],
        ]
        and kmids_tree == EXPECTED_PREDECESSOR["stage044_review_kmids_tree"]
        and ancestor
    )


def _git_blob_sha256(repo_root: Path, commit: str, relative: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def _upstream_valid(repo_root: Path, bindings: Any) -> bool:
    if bindings != EXPECTED_UPSTREAM:
        return False
    try:
        commit = EXPECTED_PREDECESSOR["stage044_review_commit"]
        return all(
            _git_blob_sha256(repo_root, commit, item["ref"])
            == item["sha256"]
            for item in EXPECTED_UPSTREAM.values()
        )
    except (OSError, KeyError, TypeError, subprocess.SubprocessError):
        return False


def _state_boundary_valid(root: Path, boundary: Any) -> bool:
    if not isinstance(boundary, Mapping):
        return False
    try:
        state_model = json.loads(
            (root / STATE_MODEL_RELATIVE).read_text(encoding="utf-8")
        )["state_model"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return (
        boundary.get("state_model_version") == state_model.get("state_model_version")
        and boundary.get("job_states") == state_model.get("job_states")
        and boundary.get("job_states") == EXPECTED_JOB_STATES
        and boundary.get("state_model_owner") == "STAGE-037"
        and boundary.get("job_type") == "PARSE"
        and boundary.get("runtime_owners")
        == {
            "file_fingerprint": "STAGE-013",
            "extracted_file_reingest": "STAGE-027",
            "job_state": "STAGE-037",
            "half_product_cleanup": "STAGE-044",
            "file_type_detection": "STAGE-045",
            "parser_route_contract": "STAGE-046",
            "parser_output_contract": "STAGE-047",
            "parser_fallback_chain": "STAGE-048",
            "parser_evaluation": "STAGE-049",
            "prompt_injection_marking": "STAGE-050",
        }
        and boundary.get("job_creation_allowed") is False
        and boundary.get("state_transition_allowed") is False
        and boundary.get("terminal_history_change_allowed") is False
        and boundary.get("queue_or_worker_runtime_allowed") is False
    )


def evaluate_contract(contract: Any, root: Path = None) -> Dict[str, bool]:
    root = root or Path(__file__).resolve().parents[1]
    repo_root = root.parent
    value: Mapping[str, Any] = contract if isinstance(contract, Mapping) else {}
    checks: Dict[str, bool] = {}
    checks["root_exact_shape"] = (
        isinstance(contract, Mapping) and set(value) == EXPECTED_ROOT_KEYS
    )
    checks["nested_exact_shapes"] = all(
        isinstance(value.get(name), Mapping)
        and set(value[name]) == expected
        for name, expected in EXPECTED_NESTED_KEYS.items()
    )
    checks["canonical_contract_identity"] = (
        isinstance(contract, Mapping)
        and _canonical_sha256(value) == EXPECTED_CANONICAL_CONTRACT_SHA256
    )
    checks["identity"] = (
        value.get("schema_version") == "ids.stage045.file_type_detection.phase1.v1"
        and value.get("stage") == "STAGE-045"
        and value.get("phase") == "Phase 1"
        and value.get("task_id") == "IDS-V0_1-STAGE045-P1"
        and value.get("acceptance_id") == "ACC-STAGE-045"
        and value.get("local_code") == "D08-S001"
        and value.get("domain") == "D08"
        and value.get("entrance") == "IDS_SYSTEM_OPERATIONS"
        and value.get("file_type_contract_id") == "ids.file_type_detection.v0_1.p1"
        and value.get("contract_state")
        == "PHASE1_ENGINEERING_CONTRACT_DETECTION_RUNTIME_DISABLED"
        and value.get("execution_ready") is False
        and value.get("next_gate") == "IDS-STAGE045-P2-GATE"
    )
    checks["source_binding"] = value.get("source_binding") == EXPECTED_SOURCE
    checks["source_live"] = _live_source_valid(repo_root)
    checks["predecessor_binding"] = (
        value.get("predecessor_binding") == EXPECTED_PREDECESSOR
        and _predecessor_valid(repo_root)
    )
    checks["upstream_bindings"] = _upstream_valid(
        repo_root, value.get("upstream_bindings")
    )
    input_contract = value.get("input_contract", {})
    checks["bounded_reference_only_input"] = (
        isinstance(input_contract, Mapping)
        and input_contract.get("mode") == "REFERENCE_ONLY_STATIC_SCHEMA"
        and input_contract.get("approved_explicit_source_required") is True
        and input_contract.get("fingerprint_provenance_required") is True
        and input_contract.get("bounded_signal_metadata_required") is True
        and input_contract.get("raw_metadata_boundary_blocked") is True
        and input_contract.get("raw_source_body_allowed") is False
        and input_contract.get("plaintext_secret_allowed") is False
        and input_contract.get("source_file_read_allowed") is False
        and input_contract.get("input_record_write_allowed") is False
    )
    signal = value.get("signal_contract", {})
    checks["signal_trust_and_ooxml"] = (
        isinstance(signal, Mapping)
        and signal.get("trust_order")
        == ["FILE_SIGNATURE", "MIME_OBSERVATION", "FILENAME_EXTENSION"]
        and signal.get("filename_extension_trust") == "ADVISORY_ONLY"
        and signal.get("signature_trust")
        == "PRIMARY_BUT_FORMAT_VALIDATION_REQUIRED"
        and signal.get("extension_only_route_allowed") is False
        and signal.get("zip_magic_sufficient_for_ooxml") is False
        and signal.get("docx_required_markers") == ["[Content_Types].xml", "word/"]
        and signal.get("xlsx_required_markers") == ["[Content_Types].xml", "xl/"]
        and signal.get("signal_conflict_action") == "REVIEW_REQUIRED"
        and signal.get("missing_signal_action") == "FAIL_CLOSED"
        and signal.get("remote_lookup_allowed") is False
        and signal.get("raw_signal_payload_allowed") is False
    )
    classification = value.get("classification_contract", {})
    checks["classification_fail_closed"] = (
        isinstance(classification, Mapping)
        and classification.get("canonical_type_values") == EXPECTED_TYPES
        and classification.get("detection_states") == EXPECTED_DETECTION_STATES
        and classification.get("confidence_values")
        == ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
        and classification.get("extension_only_max_confidence") == "LOW"
        and classification.get("unknown_or_conflict_action")
        == "OWNER_REVIEW_REQUIRED"
        and classification.get("filename_overrides_other_signals") is False
        and classification.get("parser_dispatch_allowed") is False
        and classification.get("format_registry_runtime_activated") is False
    )
    route = value.get("parser_route_boundary", {})
    checks["parser_route_candidate_only"] = (
        isinstance(route, Mapping)
        and route.get("detailed_contract_owner") == "STAGE-046"
        and route.get("candidate_route_map") == EXPECTED_ROUTE_MAP
        and route.get("route_execution_allowed") is False
        and route.get("parser_execution_allowed") is False
        and route.get("direct_index_or_evidence_write_allowed") is False
        and route.get("silent_route_selection_allowed") is False
    )
    output = value.get("output_contract", {})
    checks["parser_output_candidate_only"] = (
        isinstance(output, Mapping)
        and output.get("detailed_contract_owner") == "STAGE-047"
        and output.get("required_parser_output_fields") == EXPECTED_OUTPUT_FIELDS
        and output.get("content_fields_are_untrusted_evidence") is True
        and output.get("quality_gate_required") is True
        and output.get("provenance_required") is True
        and output.get("parser_version_required") is True
        and output.get("parser_output_write_allowed") is False
        and output.get("high_confidence_evidence_write_allowed") is False
        and output.get("empty_output_silent_success_allowed") is False
        and output.get("raw_source_body_in_control_contract_allowed") is False
    )
    fallback = value.get("fallback_contract", {})
    checks["fallback_explicit_and_disabled"] = (
        isinstance(fallback, Mapping)
        and fallback.get("implementation_owner") == "STAGE-048"
        and fallback.get("silent_drop_allowed") is False
        and fallback.get("silent_parser_switch_allowed") is False
        and fallback.get("attempt_errors_required") is True
        and fallback.get("low_confidence_action") == "OWNER_REVIEW_REQUIRED"
        and fallback.get("unknown_type_action")
        == "UNSUPPORTED_OR_OWNER_REVIEW"
        and fallback.get("all_attempts_provenance_bound") is True
        and fallback.get("fallback_execution_allowed") is False
    )
    prompt = value.get("prompt_injection_boundary", {})
    checks["source_text_untrusted"] = (
        isinstance(prompt, Mapping)
        and prompt.get("implementation_owner") == "STAGE-050"
        and prompt.get("source_derived_text_label") == "UNTRUSTED_EVIDENCE_TEXT"
        and prompt.get("forbidden_interpretations")
        == ["SYSTEM_INSTRUCTION", "TOOL_INSTRUCTION", "POLICY", "CONTROL_COMMAND"]
        and prompt.get("marker_required_before_downstream_model") is True
        and prompt.get("source_text_can_override_system_rules") is False
        and prompt.get("source_text_can_authorize_tools") is False
        and prompt.get("prompt_injection_scan_performed") is False
        and prompt.get("marker_application_allowed") is False
    )
    quality = value.get("quality_and_evidence_boundary", {})
    checks["quality_gate_blocks_evidence_promotion"] = (
        isinstance(quality, Mapping)
        and quality.get("parser_artifact_fact_level") == "CANDIDATE"
        and quality.get("quality_gate_decision_required") is True
        and quality.get("unknown_or_missing_quality_action")
        == "BLOCK_DOWNSTREAM_PROMOTION"
        and all(
            quality.get(name) is False
            for name in (
                "evidence_promotion_allowed", "evidence_ledger_write_allowed",
                "audit_write_allowed", "report_generation_allowed",
                "direct_index_write_allowed", "manifest_mutation_allowed",
                "original_mutation_allowed",
            )
        )
    )
    checks["state_and_job_boundary"] = _state_boundary_valid(
        root, value.get("state_and_job_boundary")
    )
    phase2 = value.get("phase2_entry_gate", {})
    checks["phase2_separate_and_locked"] = (
        isinstance(phase2, Mapping)
        and phase2.get("required_gate") == "IDS-STAGE045-P2-GATE"
        and phase2.get("phase2_must_run_separately") is True
        and phase2.get("execution_ready") is False
        and phase2.get("parser_dispatch_allowed") is False
        and phase2.get("push_allowed") is False
    )
    runtime = value.get("runtime_boundary", {})
    checks["runtime_disabled"] = (
        isinstance(runtime, Mapping)
        and runtime.get("mode") == "STATIC_CONTRACT_VALIDATION_ONLY"
        and all(
            runtime.get(name) is False
            for name in (
                "source_file_open_allowed", "file_scan_allowed",
                "file_signature_inspection_allowed",
                "type_classification_runtime_allowed",
                "parser_route_evaluation_allowed", "parser_dispatch_allowed",
                "parser_execution_allowed", "fallback_execution_allowed",
                "prompt_marker_application_allowed", "persistent_write_allowed",
                "production_runtime_allowed",
            )
        )
    )
    rollback = value.get("rollback_contract", {})
    checks["rollback_nondestructive"] = (
        isinstance(rollback, Mapping)
        and rollback.get("destructive_rollback_allowed") is False
        and isinstance(rollback.get("steps"), list)
        and len(rollback.get("steps", [])) == 5
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


def build_stage045_phase1_report(root: Path = None) -> Dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    contract_path = root / CONTRACT_RELATIVE
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        contract = {}
    checks = evaluate_contract(contract, root=root)
    valid = bool(checks) and all(checks.values())
    return {
        "schema_version": "ids.stage045.file_type_detection.phase1.report.v1",
        "stage": "STAGE-045",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE045-P1",
        "acceptance_id": "ACC-STAGE-045",
        "valid": valid,
        "result": (
            "PASS_PHASE1_CONTRACT_DETECTION_RUNTIME_DISABLED"
            if valid
            else "FAIL_CLOSED"
        ),
        "contract_state": (
            contract.get("contract_state") if isinstance(contract, dict) else None
        ),
        "next_gate": (
            "IDS-STAGE045-P2-GATE" if valid else "IDS-STAGE045-P1-GATE"
        ),
        "execution_ready": False,
        "parser_dispatch_allowed": False,
        "checks": checks,
        "canonical_type_count": len(EXPECTED_TYPES),
        "detection_state_count": len(EXPECTED_DETECTION_STATES),
        "required_parser_output_field_count": len(EXPECTED_OUTPUT_FIELDS),
        "source_file_open_performed": False,
        "file_signature_inspection_performed": False,
        "type_classification_runtime_performed": False,
        "parser_route_evaluation_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "prompt_injection_marker_applied": False,
        "high_confidence_evidence_write_performed": False,
        "raw_metadata_content_accessed": False,
        "persistent_state_write_performed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage045_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
