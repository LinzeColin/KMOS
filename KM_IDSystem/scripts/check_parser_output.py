#!/usr/bin/env python3
"""Validate the STAGE-047 Phase 1 static parser-output contract."""

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
    "docs/pursuing_goal/ids_v0_1/parser_output/"
    "stage047_parser_output_contract.json"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "8e4739c33651e10377c413348cade34a656e03d18ba9464d22e00d7c65b3fd0a"
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
        "STAGE-047_解析器输出合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
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
    "stage046_review_commit": "c7d66380cfab7cf00ccbb9af34ef43a7f44a7bde",
    "stage046_review_root_tree": "455b675a23243a8978b332e07e4a4cadcc532038",
    "stage046_review_kmids_tree": "98d21d245ccee585795cbc6e6180a8fcafda7f75",
    "stage046_review_parent": "5dee024cd44e2e772776487ee21761f274c7708e",
    "stage046_review_status": "completed_reviewed_local",
    "stage046_review_result": (
        "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
    ),
}
PREDECESSOR_COMMIT = EXPECTED_PREDECESSOR["stage046_review_commit"]
PREDECESSOR_RUN_REF = (
    "KM_IDSystem/machine/runs/2026-07-22-stage046-review-local.json"
)

EXPECTED_UPSTREAM = {
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
    "stage046_phase1_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_contract.json"
        ),
        "sha256": (
            "5c145dba0ba2246b6daa33da0098b4b2ee2a48a53cfec993261d70596706c1fd"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_phase2_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_runtime_contract.json"
        ),
        "sha256": (
            "d1772c08581d04a9b7932f1a74fcfe44877056973df559c2396fb69f9b1e3aab"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_phase3_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_scenarios_contract.json"
        ),
        "sha256": (
            "eef1c03bf3abd2a95bb0294b2b8671a61e3fd29f77e3495b2a118941b979c8a2"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_delivery_contract_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_delivery_contract.json"
        ),
        "sha256": (
            "18629486122178a169ae88e54559d3166f73a19c1652011643ee88b4ae3e9dc0"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_review_ref": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE046_STAGE_REVIEW.md"
        ),
        "sha256": (
            "f946ffdecb1a896065f7a3a66e1a6a38a52df445b3ef6b5fab4d310aa86362a2"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_review_checker_ref": {
        "ref": "KM_IDSystem/scripts/check_parser_routing_stage_review.py",
        "sha256": (
            "61a84f278b0db213e7cd28021cb16daeecc76c21bbb17cde547eb6286df43053"
        ),
        "snapshot_commit": PREDECESSOR_COMMIT,
    },
    "stage046_review_run_ref": {
        "ref": PREDECESSOR_RUN_REF,
        "sha256": (
            "f33f1d06dc569ffe996167df373ec108abb4e129b7104c8ace2fa13d1776f719"
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

EXPECTED_CORE_FIELDS = [
    "text", "tables", "pages", "sections", "confidence", "errors",
]
EXPECTED_INPUT_FIELDS = [
    "route_result_id",
    "route_result",
    "routing_request",
    "source_identity_ref",
    "requested_output_schema_version",
    "requested_at",
]
EXPECTED_ROUTING_REQUEST_FIELDS = [
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
EXPECTED_ROUTE_HUMAN_STATUS = "控制路线夹具已绑定，未选择或执行解析器"
EXPECTED_ENVELOPE_FIELDS = [
    "output_id",
    "output_schema_version",
    "route_result_id",
    "routing_request_id",
    "detection_result_id",
    "source_identity_ref",
    "parser_family",
    "parser_version",
    "status",
    *EXPECTED_CORE_FIELDS,
    "content_security",
    "quality_gate",
    "produced_at",
]
EXPECTED_STATUSES = [
    "OUTPUT_CANDIDATE_NOT_VALIDATED",
    "OUTPUT_PARTIAL_REVIEW_REQUIRED",
    "OUTPUT_FAILED_EXPLICIT",
]
EXPECTED_PHASE2_CONDITIONS = [
    "SOURCE_BINDING_EXACT",
    "STAGE046_REVIEW_SNAPSHOT_EXACT",
    "STAGE045_DETECTION_AND_STAGE046_ROUTE_LINEAGE_EXACT",
    "OUTPUT_ENVELOPE_EXACT",
    "SIX_CORE_FIELDS_EXACT",
    "NESTED_ITEM_SCHEMAS_EXACT",
    "EMPTY_PARTIAL_FAILED_OUTPUTS_FAIL_CLOSED",
    "QUALITY_AND_EVIDENCE_PROMOTION_CLOSED",
    "STAGE048_049_050_OWNERSHIP_PRESERVED",
    "ALL_RUNTIME_TRUTH_FLAGS_FALSE",
]
EXPECTED_HUMAN_STATUS = {
    "PHASE1_CONTRACT_READY": "解析器输出合同已就绪，实际解析和输出仍禁用",
    "OUTPUT_CANDIDATE_NOT_VALIDATED": (
        "解析候选产物尚未通过质量门，不能作为高可信证据"
    ),
    "OUTPUT_PARTIAL_REVIEW_REQUIRED": (
        "解析结果不完整，需要人工复核后才能继续"
    ),
    "OUTPUT_FAILED_EXPLICIT": "解析失败已显式记录，未静默丢弃内容",
    "OUTPUT_REJECTED_FAIL_CLOSED": "解析输出不符合合同，已阻断下游使用",
}

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "route_evaluation_performed",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "parser_output_produced",
    "fallback_execution_performed",
    "differential_evaluation_performed",
    "prompt_injection_scan_performed",
    "prompt_injection_marker_applied",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "index_write_performed",
    "report_write_performed",
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
    "push_allowed",
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
    "parser_output_contract_id",
    "contract_state",
    "execution_ready",
    "next_gate",
    "source_binding",
    "predecessor_binding",
    "upstream_snapshot_bindings",
    "input_boundary",
    "output_envelope_contract",
    "core_output_contract",
    "item_schema_contracts",
    "lineage_and_integrity_contract",
    "completion_and_error_contract",
    "quality_and_evidence_boundary",
    "fallback_boundary",
    "differential_evaluation_boundary",
    "prompt_injection_boundary",
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
    "input_boundary": {
        "mode",
        "required_wrapper_fields",
        "required_routing_request_schema_version",
        "required_routing_request_fields",
        "required_route_result_schema_version",
        "required_route_result_fields",
        "eligible_route_actions",
        "ineligible_route_actions",
        "detection_authority",
        "route_authority",
        "result_identity_required",
        "result_identity_algorithm",
        "result_identity_format",
        "result_identity_scope",
        "routing_request_identity_required",
        "routing_request_identity_algorithm",
        "request_result_lineage_match_required",
        "required_route_result_human_status",
        "canonical_control_reference_format",
        "source_identity_match_required",
        "parser_family_and_version_match_required",
        "placeholder_parser_version_allowed_for_candidate_output",
        "source_body_or_path_allowed",
        "raw_exception_or_unbounded_text_allowed",
        "input_record_write_allowed",
        "raw_metadata_boundary_blocked",
    },
    "output_envelope_contract": {
        "required_fields",
        "additional_fields_allowed",
        "required_output_schema_version",
        "output_id_algorithm",
        "output_id_format",
        "output_id_scope",
        "allowed_statuses",
        "strict_utc_produced_at_required",
        "produced_at_not_before_requested_at",
        "parser_version_required",
        "placeholder_parser_version_allowed",
        "candidate_output_is_dispatch_authorization",
        "candidate_output_is_quality_approval",
        "output_creation_allowed",
        "output_persistence_allowed",
    },
    "core_output_contract": {
        "required_fields", "additional_core_fields_allowed", "field_contracts",
    },
    "item_schema_contracts": {"table", "page", "section", "safe_error"},
    "lineage_and_integrity_contract": {
        "route_detection_source_identity_chain_required",
        "route_result_id_must_match_input_projection",
        "output_id_must_match_output_projection",
        "source_identity_ref_must_match_route_result",
        "parser_family_and_version_must_match_route_result",
        "all_internal_references_must_resolve",
        "reciprocal_table_page_references_required",
        "reciprocal_table_section_references_required",
        "canonical_reference_format",
        "duplicate_item_ids_rejected",
        "orphan_page_section_or_table_refs_rejected",
        "filesystem_path_or_uri_reference_allowed",
        "identity_mismatch_action",
        "lineage_mismatch_action",
    },
    "completion_and_error_contract": {
        "candidate_non_empty_condition",
        "empty_candidate_without_error_rejected",
        "partial_or_failed_requires_safe_error",
        "failed_output_content_must_be_empty",
        "unknown_confidence_blocks_promotion",
        "low_confidence_requires_review",
        "safe_error_codes_required_for_all_failures",
        "valid_utf8_encodable_text_required",
        "silent_success_allowed",
        "silent_drop_allowed",
        "invalid_output_action",
    },
    "quality_and_evidence_boundary": {
        "parser_content_fact_level",
        "initial_quality_gate_state",
        "allowed_quality_gate_states",
        "quality_gate_required_before_downstream",
        "missing_quality_action",
        "quality_gate_pass_can_be_claimed_in_phase1",
        "direct_high_trust_evidence_write_allowed",
        "evidence_promotion_allowed",
        "manifest_write_allowed",
        "evidence_ledger_write_allowed",
        "audit_write_allowed",
        "index_or_report_write_allowed",
        "database_write_allowed",
        "original_or_delivered_output_mutation_allowed",
    },
    "fallback_boundary": {
        "runtime_owner",
        "attempt_history_required",
        "attempt_parser_version_required",
        "bounded_safe_error_required",
        "stop_reason_required",
        "silent_drop_allowed",
        "silent_parser_switch_allowed",
        "fallback_output_must_use_same_envelope",
        "execution_allowed",
    },
    "differential_evaluation_boundary": {
        "runtime_owner",
        "candidate_outputs_must_remain_separate",
        "comparison_cannot_rewrite_source_output",
        "comparison_cannot_self_promote_evidence",
        "execution_allowed",
    },
    "prompt_injection_boundary": {
        "runtime_owner",
        "required_content_label",
        "phase1_marker_state",
        "marker_required_before_downstream_model",
        "forbidden_interpretations",
        "content_can_override_system_rules",
        "content_can_authorize_tools",
        "scan_or_marker_application_allowed",
    },
    "state_and_job_boundary": {
        "job_type",
        "state_model_owner",
        "route_contract_owner",
        "output_contract_owner",
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
        "source_file_access_allowed",
        "file_type_redetection_allowed",
        "route_evaluation_allowed",
        "parser_selection_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "parser_output_creation_allowed",
        "fallback_execution_allowed",
        "differential_evaluation_allowed",
        "prompt_injection_scan_allowed",
        "prompt_injection_marker_application_allowed",
        "quality_gate_evaluation_allowed",
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
    """Rehash only the explicitly approved taskpack files and Stage047 member."""

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
    """Verify the committed Stage046 review identity, ancestry, and verdict."""

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
    review = review_run.get("review", {})
    findings = review_run.get("findings", [])
    return (
        observed
        == [
            commit,
            EXPECTED_PREDECESSOR["stage046_review_root_tree"],
            EXPECTED_PREDECESSOR["stage046_review_parent"],
        ]
        and kmids_tree == EXPECTED_PREDECESSOR["stage046_review_kmids_tree"]
        and ancestor
        and review_run.get("task_id") == "IDS-V0_1-STAGE046-REVIEW"
        and review_run.get("acceptance_id") == "ACC-STAGE-046"
        and review_run.get("result")
        == EXPECTED_PREDECESSOR["stage046_review_result"]
        and isinstance(review, Mapping)
        and review.get("finding_count") == 6
        and review.get("resolved_finding_count") == 6
        and review.get("open_finding_count") == 0
        and review.get("phase1_contract_valid") is True
        and review.get("phase2_slice_valid") is True
        and review.get("phase3_scenarios_valid") is True
        and review.get("phase4_delivery_valid") is True
        and review.get("phase4_commit_binding_valid") is True
        and isinstance(findings, list)
        and len(findings) == 6
        and all(item.get("status") == "resolved" for item in findings)
        and review_run.get("stage047_started") is False
        and review_run.get("stage047_entry_allowed") is False
        and review_run.get("batch_review_performed") is False
        and review_run.get("github_upload_allowed") is False
        and review_run.get("push_allowed") is False
        and review_run.get("app_reinstall_allowed") is False
        and review_run.get("next_gate") == "IDS-STAGE047-P1-GATE"
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
    if not isinstance(upstream, Mapping) or not all(
        isinstance(item, Mapping)
        and set(item) == {"ref", "sha256", "snapshot_commit"}
        for item in upstream.values()
    ):
        return False
    core = value.get("core_output_contract", {})
    fields = core.get("field_contracts", {}) if isinstance(core, Mapping) else {}
    if not isinstance(fields, Mapping) or set(fields) != set(EXPECTED_CORE_FIELDS):
        return False
    items = value.get("item_schema_contracts", {})
    if not isinstance(items, Mapping):
        return False
    expected_item_keys = {
        "table": {
            "schema_id",
            "required_fields",
            "additional_fields_allowed",
            "cells_type",
            "rectangular_shape_required",
            "source_order_preserved",
            "raw_formula_execution_allowed",
        },
        "page": {
            "schema_id",
            "required_fields",
            "additional_fields_allowed",
            "page_number_type",
            "page_numbers_unique_and_ascending",
            "text_trust_label",
        },
        "section": {
            "schema_id",
            "required_fields",
            "additional_fields_allowed",
            "level_type",
            "title_and_text_trust_label",
            "hierarchy_cycles_allowed",
        },
        "safe_error": {
            "schema_id",
            "required_fields",
            "additional_fields_allowed",
            "allowed_severities",
            "code_format",
            "code_max_characters",
            "message_key_format",
            "message_key_max_characters",
            "raw_message_exception_stack_path_uri_or_content_allowed",
        },
    }
    return all(
        isinstance(items.get(name), Mapping)
        and set(items[name]) == expected_keys
        for name, expected_keys in expected_item_keys.items()
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
        value.get("schema_version") == "ids.stage047.parser_output.phase1.v1"
        and value.get("stage") == "STAGE-047"
        and value.get("phase") == "Phase 1"
        and value.get("task_id") == "IDS-V0_1-STAGE047-P1"
        and value.get("acceptance_id") == "ACC-STAGE-047"
        and value.get("local_code") == "D08-S003"
        and value.get("domain") == "D08"
        and value.get("entrance") == "IDS_SYSTEM_OPERATIONS"
        and value.get("pursuing_goal")
        == "DEFINE_EXACT_FAIL_CLOSED_PARSER_OUTPUT_WITHOUT_EXECUTION_OR_EVIDENCE_PROMOTION"
        and value.get("parser_output_contract_id")
        == "ids.parser_output.v0_1.stage047.p1"
        and value.get("contract_state")
        == "PHASE1_ENGINEERING_CONTRACT_PARSER_OUTPUT_RUNTIME_DISABLED"
        and value.get("execution_ready") is False
        and value.get("next_gate") == "IDS-STAGE047-P2-GATE"
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

    incoming = value.get("input_boundary", {})
    checks["stage045_stage046_reference_only_input"] = (
        isinstance(incoming, Mapping)
        and incoming.get("mode")
        == "REFERENCE_ONLY_STAGE046_ROUTING_REQUEST_AND_RESULT"
        and incoming.get("required_wrapper_fields") == EXPECTED_INPUT_FIELDS
        and incoming.get("required_routing_request_schema_version")
        == "ids.stage046.parser_routing_request.v1"
        and incoming.get("required_routing_request_fields")
        == EXPECTED_ROUTING_REQUEST_FIELDS
        and incoming.get("required_route_result_schema_version")
        == "ids.stage046.parser_routing_result.v1"
        and incoming.get("eligible_route_actions")
        == ["ROUTE_CANDIDATE_READY_NOT_EXECUTED"]
        and incoming.get("ineligible_route_actions")
        == [
            "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
            "ROUTE_REVIEW_REQUIRED",
            "ROUTE_UNSUPPORTED",
            "ROUTE_BLOCKED",
        ]
        and incoming.get("detection_authority") == "STAGE-045"
        and incoming.get("route_authority") == "STAGE-046"
        and incoming.get("result_identity_required") is True
        and incoming.get("result_identity_algorithm") == "SHA256_CANONICAL_JSON"
        and incoming.get("result_identity_format")
        == "route-result:sha256:<64-lower-hex>"
        and incoming.get("result_identity_scope")
        == "INTEGRITY_ONLY_NOT_EXTERNAL_PROVENANCE_OR_AUTHORIZATION"
        and incoming.get("routing_request_identity_required") is True
        and incoming.get("routing_request_identity_algorithm")
        == "SHA256_CANONICAL_JSON"
        and incoming.get("request_result_lineage_match_required") is True
        and incoming.get("required_route_result_human_status")
        == EXPECTED_ROUTE_HUMAN_STATUS
        and incoming.get("canonical_control_reference_format")
        == "LOWER_ASCII_TOKEN_SEGMENTS"
        and incoming.get("source_identity_match_required") is True
        and incoming.get("parser_family_and_version_match_required") is True
        and incoming.get("placeholder_parser_version_allowed_for_candidate_output")
        is False
        and incoming.get("source_body_or_path_allowed") is False
        and incoming.get("raw_exception_or_unbounded_text_allowed") is False
        and incoming.get("input_record_write_allowed") is False
        and incoming.get("raw_metadata_boundary_blocked") is True
    )

    envelope = value.get("output_envelope_contract", {})
    checks["output_envelope_exact"] = (
        isinstance(envelope, Mapping)
        and envelope.get("required_fields") == EXPECTED_ENVELOPE_FIELDS
        and envelope.get("additional_fields_allowed") is False
        and envelope.get("required_output_schema_version")
        == "ids.parser_output.v0_1.stage047.p1"
        and envelope.get("output_id_algorithm")
        == "SHA256_CANONICAL_OUTPUT_PROJECTION"
        and envelope.get("output_id_format")
        == "parser-output:sha256:<64-lower-hex>"
        and envelope.get("output_id_scope")
        == "INTEGRITY_ONLY_NOT_EXTERNAL_PROVENANCE_OR_QUALITY_APPROVAL"
        and envelope.get("allowed_statuses") == EXPECTED_STATUSES
        and envelope.get("strict_utc_produced_at_required") is True
        and envelope.get("produced_at_not_before_requested_at") is True
        and envelope.get("parser_version_required") is True
        and envelope.get("placeholder_parser_version_allowed") is False
        and envelope.get("candidate_output_is_dispatch_authorization") is False
        and envelope.get("candidate_output_is_quality_approval") is False
        and envelope.get("output_creation_allowed") is False
        and envelope.get("output_persistence_allowed") is False
    )

    core = value.get("core_output_contract", {})
    fields = core.get("field_contracts", {}) if isinstance(core, Mapping) else {}
    checks["six_core_fields_exact"] = (
        isinstance(core, Mapping)
        and core.get("required_fields") == EXPECTED_CORE_FIELDS
        and core.get("additional_core_fields_allowed") is False
        and isinstance(fields, Mapping)
        and fields.get("text", {}).get("type") == "STRING_OR_NULL"
        and fields.get("text", {}).get("trust_label")
        == "UNTRUSTED_EVIDENCE_TEXT"
        and fields.get("text", {}).get("instruction_interpretation_allowed")
        is False
        and fields.get("text", {}).get("tool_authorization_allowed") is False
        and fields.get("tables", {}).get("item_schema_ref")
        == "ids.parser_output.table.v0_1"
        and fields.get("pages", {}).get("item_schema_ref")
        == "ids.parser_output.page.v0_1"
        and fields.get("sections", {}).get("item_schema_ref")
        == "ids.parser_output.section.v0_1"
        and all(
            fields.get(name, {}).get("type") == "ARRAY"
            and fields.get(name, {}).get("item_ids_unique") is True
            and fields.get(name, {}).get("source_order_preserved") is True
            for name in ("tables", "pages", "sections")
        )
        and fields.get("confidence", {}).get("type") == "ENUM"
        and fields.get("confidence", {}).get("allowed_values")
        == ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
        and fields.get("confidence", {}).get("numeric_thresholds_assigned")
        is False
        and fields.get("confidence", {}).get("unknown_blocks_promotion") is True
        and fields.get("errors", {}).get("item_schema_ref")
        == "ids.parser_output.safe_error.v0_1"
        and fields.get("errors", {}).get("raw_exception_allowed") is False
        and fields.get("errors", {}).get("business_content_echo_allowed") is False
        and fields.get("errors", {}).get("filesystem_path_or_secret_allowed")
        is False
    )

    items = value.get("item_schema_contracts", {})
    checks["nested_item_schemas_exact"] = (
        isinstance(items, Mapping)
        and items.get("table", {}).get("required_fields")
        == ["table_id", "page_refs", "section_ref", "cells", "confidence", "errors"]
        and items.get("table", {}).get("additional_fields_allowed") is False
        and items.get("table", {}).get("rectangular_shape_required") is True
        and items.get("table", {}).get("raw_formula_execution_allowed") is False
        and items.get("page", {}).get("required_fields")
        == ["page_id", "page_number", "text", "table_refs", "confidence", "errors"]
        and items.get("page", {}).get("additional_fields_allowed") is False
        and items.get("page", {}).get("page_number_type") == "POSITIVE_INTEGER"
        and items.get("page", {}).get("page_numbers_unique_and_ascending") is True
        and items.get("section", {}).get("required_fields")
        == [
            "section_id",
            "title",
            "level",
            "page_refs",
            "text",
            "table_refs",
            "confidence",
            "errors",
        ]
        and items.get("section", {}).get("additional_fields_allowed") is False
        and items.get("section", {}).get("hierarchy_cycles_allowed") is False
        and items.get("safe_error", {}).get("required_fields")
        == ["code", "severity", "retryable", "message_key"]
        and items.get("safe_error", {}).get("additional_fields_allowed") is False
        and items.get("safe_error", {}).get("allowed_severities")
        == ["WARNING", "ERROR", "FATAL"]
        and items.get("safe_error", {}).get("code_max_characters") == 96
        and items.get("safe_error", {}).get("message_key_max_characters")
        == 128
        and items.get("safe_error", {}).get(
            "raw_message_exception_stack_path_uri_or_content_allowed"
        )
        is False
    )

    lineage = value.get("lineage_and_integrity_contract", {})
    checks["lineage_and_identity_fail_closed"] = (
        isinstance(lineage, Mapping)
        and all(
            lineage.get(name) is True
            for name in (
                "route_detection_source_identity_chain_required",
                "route_result_id_must_match_input_projection",
                "output_id_must_match_output_projection",
                "source_identity_ref_must_match_route_result",
                "parser_family_and_version_must_match_route_result",
                "all_internal_references_must_resolve",
                "reciprocal_table_page_references_required",
                "reciprocal_table_section_references_required",
                "duplicate_item_ids_rejected",
                "orphan_page_section_or_table_refs_rejected",
            )
        )
        and lineage.get("canonical_reference_format")
        == "LOWER_ASCII_TOKEN_SEGMENTS"
        and lineage.get("filesystem_path_or_uri_reference_allowed") is False
        and lineage.get("identity_mismatch_action")
        == "OUTPUT_REJECTED_IDENTITY_MISMATCH"
        and lineage.get("lineage_mismatch_action")
        == "OUTPUT_REJECTED_LINEAGE_MISMATCH"
    )

    completion = value.get("completion_and_error_contract", {})
    checks["empty_partial_failed_output_fail_closed"] = (
        isinstance(completion, Mapping)
        and completion.get("candidate_non_empty_condition")
        == "NON_EMPTY_TEXT_OR_TABLES_OR_PAGES_OR_SECTIONS"
        and all(
            completion.get(name) is True
            for name in (
                "empty_candidate_without_error_rejected",
                "partial_or_failed_requires_safe_error",
                "failed_output_content_must_be_empty",
                "unknown_confidence_blocks_promotion",
                "low_confidence_requires_review",
                "safe_error_codes_required_for_all_failures",
                "valid_utf8_encodable_text_required",
            )
        )
        and completion.get("silent_success_allowed") is False
        and completion.get("silent_drop_allowed") is False
        and completion.get("invalid_output_action")
        == "OUTPUT_REJECTED_FAIL_CLOSED"
    )

    quality = value.get("quality_and_evidence_boundary", {})
    checks["quality_and_evidence_closed"] = (
        isinstance(quality, Mapping)
        and quality.get("parser_content_fact_level") == "CANDIDATE"
        and quality.get("initial_quality_gate_state") == "UNASSESSED"
        and quality.get("allowed_quality_gate_states")
        == ["UNASSESSED", "REVIEW_REQUIRED", "BLOCKED"]
        and quality.get("quality_gate_required_before_downstream") is True
        and quality.get("missing_quality_action") == "BLOCK_DOWNSTREAM_PROMOTION"
        and all(
            quality.get(name) is False
            for name in (
                "quality_gate_pass_can_be_claimed_in_phase1",
                "direct_high_trust_evidence_write_allowed",
                "evidence_promotion_allowed",
                "manifest_write_allowed",
                "evidence_ledger_write_allowed",
                "audit_write_allowed",
                "index_or_report_write_allowed",
                "database_write_allowed",
                "original_or_delivered_output_mutation_allowed",
            )
        )
    )

    fallback = value.get("fallback_boundary", {})
    differential = value.get("differential_evaluation_boundary", {})
    prompt = value.get("prompt_injection_boundary", {})
    checks["stage048_049_050_ownership_preserved"] = (
        isinstance(fallback, Mapping)
        and fallback.get("runtime_owner") == "STAGE-048"
        and fallback.get("attempt_history_required") is True
        and fallback.get("attempt_parser_version_required") is True
        and fallback.get("bounded_safe_error_required") is True
        and fallback.get("stop_reason_required") is True
        and fallback.get("silent_drop_allowed") is False
        and fallback.get("silent_parser_switch_allowed") is False
        and fallback.get("fallback_output_must_use_same_envelope") is True
        and fallback.get("execution_allowed") is False
        and isinstance(differential, Mapping)
        and differential.get("runtime_owner") == "STAGE-049"
        and differential.get("candidate_outputs_must_remain_separate") is True
        and differential.get("comparison_cannot_rewrite_source_output") is True
        and differential.get("comparison_cannot_self_promote_evidence") is True
        and differential.get("execution_allowed") is False
        and isinstance(prompt, Mapping)
        and prompt.get("runtime_owner") == "STAGE-050"
        and prompt.get("required_content_label") == "UNTRUSTED_EVIDENCE_TEXT"
        and prompt.get("phase1_marker_state") == "REQUIRED_NOT_APPLIED"
        and prompt.get("marker_required_before_downstream_model") is True
        and prompt.get("forbidden_interpretations")
        == ["SYSTEM_INSTRUCTION", "TOOL_INSTRUCTION", "POLICY", "CONTROL_COMMAND"]
        and prompt.get("content_can_override_system_rules") is False
        and prompt.get("content_can_authorize_tools") is False
        and prompt.get("scan_or_marker_application_allowed") is False
    )

    state = value.get("state_and_job_boundary", {})
    checks["job_and_state_boundary_closed"] = (
        isinstance(state, Mapping)
        and state.get("job_type") == "PARSE"
        and state.get("state_model_owner") == "STAGE-037"
        and state.get("route_contract_owner") == "STAGE-046"
        and state.get("output_contract_owner") == "STAGE-047"
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
        and phase2.get("gate_id") == "IDS-STAGE047-P2-GATE"
        and phase2.get("required_conditions") == EXPECTED_PHASE2_CONDITIONS
        and phase2.get("entry_authorized") is False
        and phase2.get("must_run_separately") is True
        and phase2.get("dependency_install_allowed") is False
    )
    runtime = value.get("runtime_boundary", {})
    checks["runtime_disabled"] = (
        isinstance(runtime, Mapping)
        and bool(runtime)
        and all(item is False for item in runtime.values())
    )
    rollback = value.get("rollback_contract", {})
    checks["rollback_nondestructive"] = (
        isinstance(rollback, Mapping)
        and rollback.get("scope")
        == "STAGE047_PHASE1_CONTRACT_AND_GOVERNANCE_ONLY"
        and rollback.get("rollback_target") == "STAGE046_REVIEWED_LOCAL_SNAPSHOT"
        and rollback.get("delete_or_cleanup_source_allowed") is False
        and rollback.get(
            "manifest_evidence_audit_index_report_mutation_allowed"
        )
        is False
        and rollback.get("github_or_app_state_change_allowed") is False
    )
    checks["human_status_exact"] = (
        value.get("human_status_projection") == EXPECTED_HUMAN_STATUS
    )
    truth = value.get("truth_flags", {})
    checks["truth_flags"] = (
        isinstance(truth, Mapping)
        and set(truth) == {"taskpack_source_read_performed"} | FALSE_TRUTH_FLAGS
        and truth.get("taskpack_source_read_performed") is True
        and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
    )
    return checks


def build_stage047_phase1_report(
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build a stable Phase1 report without opening a business source or parser."""

    project_root = Path(root) if root is not None else PROJECT_ROOT
    contract_path = project_root / CONTRACT_RELATIVE
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        contract = {}
    checks = evaluate_contract(contract, root=project_root)
    valid = bool(checks) and all(checks.values())
    return {
        "schema_version": "ids.stage047.parser_output.phase1.report.v1",
        "stage": "STAGE-047",
        "phase": "Phase 1",
        "task_id": "IDS-V0_1-STAGE047-P1",
        "acceptance_id": "ACC-STAGE-047",
        "valid": valid,
        "result": (
            "PASS_PHASE1_PARSER_OUTPUT_CONTRACT_RUNTIME_DISABLED"
            if valid
            else "FAIL_CLOSED"
        ),
        "contract_state": (
            contract.get("contract_state") if isinstance(contract, dict) else None
        ),
        "next_gate": (
            "IDS-STAGE047-P2-GATE" if valid else "IDS-STAGE047-P1-GATE"
        ),
        "required_core_field_count": len(EXPECTED_CORE_FIELDS),
        "required_envelope_field_count": len(EXPECTED_ENVELOPE_FIELDS),
        "nested_item_schema_count": 4,
        "execution_ready": False,
        "parser_execution_allowed": False,
        "checks": checks,
        "ids_business_source_read_performed": False,
        "source_file_open_performed": False,
        "file_type_redetection_performed": False,
        "route_evaluation_performed": False,
        "parser_selected": False,
        "parser_dispatch_performed": False,
        "parser_output_produced": False,
        "fallback_execution_performed": False,
        "differential_evaluation_performed": False,
        "prompt_injection_scan_performed": False,
        "prompt_injection_marker_applied": False,
        "quality_gate_evaluation_performed": False,
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
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage047_phase1_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
