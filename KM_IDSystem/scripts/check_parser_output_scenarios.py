#!/usr/bin/env python3
"""Validate STAGE-047 Phase 3 parser-output control scenarios.

The scenarios use bounded, synthetic, already-parsed payloads.  They do not
open source files, select or execute parsers, run fallback, or persist output.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT_PATH = (
    BASE
    / "parser_output"
    / "stage047_parser_output_scenarios_contract.json"
)
PHASE2_CHECKER_PATH = ROOT / "scripts" / "check_parser_output_runtime.py"
UPSTREAM_ROUTE_CHECKER_PATH = (
    ROOT / "scripts" / "check_parser_routing_scenarios.py"
)

EXPECTED_CANONICAL_CONTRACT_SHA256 = (
    "88467d7ad2d830c1ef9562b67d2ce21668110cac30411c57b885179a8ce997b8"
)
PASS_RESULT = "PASS_ISOLATED_PARSER_OUTPUT_SCENARIOS_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE047-P4-GATE"

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
        "STAGE-047_解析器输出合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
    ),
    "roadmap_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

PHASE2_BINDING = {
    "commit": "65b81389e24d9ae371f464dcd6321784b9078d8b",
    "root_tree": "a66f59a71bd8c41ba122e0415f126d7cea6d8375",
    "kmids_tree": "eb2be74f3138221f39f4aab5e513c5fc8b03d984",
    "parent": "7d44f72c6a5d50e9042b8af1f588cd40e1caf4f3",
    "required_ancestor_of_head": True,
}

PHASE2_ARTIFACTS = {
    "stage047_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE047_PHASE2_PARSER_OUTPUT_SLICE.md"
        ),
        "sha256": (
            "4ec0b012ac3de8ae08b9359158d61df84e7a351ea39ede9d641deeeb328e7a9e"
        ),
    },
    "stage047_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/"
            "stage047_parser_output_runtime_contract.json"
        ),
        "sha256": (
            "16f4e8c5be806e835b686359f06ac32b4c069cb4441b0394ff53dda1e82b5ddc"
        ),
    },
    "stage047_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_output_runtime.py",
        "sha256": (
            "02b42621c89110c67a99e2a0d87ecd7b9a58f4cbf36725a7812b69a55de84be7"
        ),
    },
    "stage047_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage047_parser_output_runtime.py"
        ),
        "sha256": (
            "66241bf92a40b85abf37483bca562564ed27fb366789ecd08d0c228c70b4cf03"
        ),
    },
    "stage047_phase2_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-23-stage047-p2-local.json",
        "sha256": (
            "b6f23424d6253bcdd9249e252c94263ae0c874cc4398238532ef41a7e1417db7"
        ),
    },
}

UPSTREAM_ROUTE_BASELINE = {
    "snapshot_commit": PHASE2_BINDING["commit"],
    "checker_ref": "KM_IDSystem/scripts/check_parser_routing_scenarios.py",
    "checker_sha256": (
        "5ab854480b0b079d848a6ff2c0cbd5808e9bbf529f7c34169d503c3084074b51"
    ),
    "contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_scenarios_contract.json"
    ),
    "contract_sha256": (
        "eef1c03bf3abd2a95bb0294b2b8671a61e3fd29f77e3495b2a118941b979c8a2"
    ),
    "run_ref": "KM_IDSystem/machine/runs/2026-07-22-stage046-p3-local.json",
    "run_sha256": (
        "0c2d919db3db91f03e4e266bb5ea0f2bfb2ce1101b47deff40e69d43f95fafff"
    ),
    "expected_result": (
        "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED"
    ),
}

FORMAT_CONTROL_ROUTES = {
    "PDF": {
        "candidate_route_id": "ROUTE_PDF",
        "parser_family": "PDF_PARSER",
        "parser_version": "ids.parser.control_fixture.pdf.v0_1.stage047.p3",
    },
    "DOCX": {
        "candidate_route_id": "ROUTE_OOXML_WORD",
        "parser_family": "OOXML_WORD_PARSER",
        "parser_version": "ids.parser.control_fixture.docx.v0_1.stage047.p3",
    },
    "XLSX": {
        "candidate_route_id": "ROUTE_OOXML_WORKBOOK",
        "parser_family": "OOXML_WORKBOOK_PARSER",
        "parser_version": "ids.parser.control_fixture.xlsx.v0_1.stage047.p3",
    },
    "CSV": {
        "candidate_route_id": "ROUTE_DELIMITED_TEXT",
        "parser_family": "DELIMITED_TEXT_PARSER",
        "parser_version": "ids.parser.control_fixture.csv.v0_1.stage047.p3",
    },
    "TXT": {
        "candidate_route_id": "ROUTE_PLAIN_TEXT",
        "parser_family": "PLAIN_TEXT_PARSER",
        "parser_version": "ids.parser.control_fixture.v0_1.stage047.p2",
    },
    "PNG": {
        "candidate_route_id": "ROUTE_IMAGE",
        "parser_family": "IMAGE_PARSER",
        "parser_version": "ids.parser.control_fixture.image.v0_1.stage047.p3",
    },
    "JPEG": {
        "candidate_route_id": "ROUTE_IMAGE",
        "parser_family": "IMAGE_PARSER",
        "parser_version": "ids.parser.control_fixture.image.v0_1.stage047.p3",
    },
    "TIFF": {
        "candidate_route_id": "ROUTE_IMAGE",
        "parser_family": "IMAGE_PARSER",
        "parser_version": "ids.parser.control_fixture.image.v0_1.stage047.p3",
    },
}

SCENARIOS = [
    "pdf_preparsed_pages_candidate",
    "docx_preparsed_sections_candidate",
    "xlsx_preparsed_table_candidate_formula_preserved",
    "csv_preparsed_table_candidate",
    "txt_preparsed_text_candidate",
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "instruction_like_text_cannot_override_policy",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
]

EXPECTED_STATUS_COUNTS = {
    "OUTPUT_CANDIDATE_NOT_VALIDATED": 6,
    "OUTPUT_PARTIAL_REVIEW_REQUIRED": 4,
    "OUTPUT_FAILED_EXPLICIT": 1,
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "taskpack_and_git_artifact_hashes_recomputed",
    "phase2_snapshot_reverified",
    "upstream_stage046_route_scenarios_replayed",
    "synthetic_format_labeled_controls_evaluated",
    "all_taskpack_format_groups_covered",
    "in_memory_output_scenarios_performed",
    "fallback_quality_disposition_evaluated",
    "instruction_route_invariance_evaluated",
    "formula_text_preservation_verified",
    "rejection_sanitization_verified",
    "control_output_envelopes_constructed",
    "phase3_started",
}

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "ids_business_filesystem_scan_performed",
    "ids_business_file_hash_performed",
    "file_type_redetection_performed",
    "actual_business_route_evaluation_performed",
    "runtime_parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "ids_business_parser_output_produced",
    "fallback_execution_performed",
    "differential_parser_evaluation_performed",
    "prompt_injection_scan_performed",
    "prompt_injection_marker_applied",
    "formula_execution_performed",
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
    "phase4_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
}

ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "local_code",
    "execution_mode",
    "scenario_contract_id",
    "contract_state",
    "next_gate",
    "source_binding",
    "phase2_commit_binding",
    "phase2_artifact_bindings",
    "upstream_route_baseline",
    "format_control_adapter",
    "scenario_catalog",
    "format_coverage",
    "scenario_expectations",
    "output_expectations",
    "fallback_quality_contract",
    "instruction_text_contract",
    "result_contract",
    "runtime_boundary",
    "phase4_entry_gate",
    "rollback_contract",
    "truth_flags",
    "human_status_projection",
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_show_bytes(commit: str, ref: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{ref}"],
        cwd=REPO_ROOT,
        stderr=subprocess.DEVNULL,
    )


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def load_phase2_checker():
    return _load_module(PHASE2_CHECKER_PATH, "stage047_phase2_output_runtime")


@functools.lru_cache(maxsize=1)
def _load_upstream_route_checker():
    return _load_module(
        UPSTREAM_ROUTE_CHECKER_PATH,
        "stage046_phase3_route_scenarios",
    )


def source_live() -> bool:
    """Recompute the approved source bindings without scanning any source tree."""

    try:
        archive_path = Path(SOURCE_BINDING["source_archive_path"])
        roadmap_path = Path(SOURCE_BINDING["roadmap_path"])
        instructions_path = Path(SOURCE_BINDING["instructions_path"])
        if (
            not archive_path.is_file()
            or _sha256(archive_path) != SOURCE_BINDING["source_archive_sha256"]
            or _sha256(roadmap_path) != SOURCE_BINDING["roadmap_sha256"]
            or _sha256(instructions_path)
            != SOURCE_BINDING["instructions_sha256"]
        ):
            return False
        with ZipFile(archive_path) as archive:
            matches = [
                name
                for name in archive.namelist()
                if name == SOURCE_BINDING["source_member"]
            ]
            if len(matches) != SOURCE_BINDING["source_member_match_count"]:
                return False
            member_sha = hashlib.sha256(archive.read(matches[0])).hexdigest()
        return member_sha == SOURCE_BINDING["source_member_sha256"]
    except (OSError, KeyError, TypeError, ValueError, BadZipFile):
        return False


def phase2_commit_live() -> bool:
    """Verify the immutable P2 commit identity and current ancestry."""

    commit = PHASE2_BINDING["commit"]
    try:
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", commit],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        kmids_tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:KM_IDSystem"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return (
        observed
        == [commit, PHASE2_BINDING["root_tree"], PHASE2_BINDING["parent"]]
        and kmids_tree == PHASE2_BINDING["kmids_tree"]
        and PHASE2_BINDING["required_ancestor_of_head"] is True
        and ancestor
    )


def phase2_artifacts_live() -> bool:
    """Rehash all P2 inputs from the immutable P2 commit."""

    try:
        return all(
            hashlib.sha256(
                _git_show_bytes(PHASE2_BINDING["commit"], item["ref"])
            ).hexdigest()
            == item["sha256"]
            for item in PHASE2_ARTIFACTS.values()
        )
    except (OSError, KeyError, TypeError, subprocess.CalledProcessError):
        return False


@functools.lru_cache(maxsize=1)
def _upstream_route_report() -> dict[str, Any]:
    try:
        report = _load_upstream_route_checker().build_stage046_phase3_report()
        return report if isinstance(report, dict) else {}
    except (OSError, RuntimeError, TypeError, ValueError, KeyError):
        return {}


def upstream_route_baseline_live() -> bool:
    """Verify the frozen route artifacts and replay the Stage 46 scenarios."""

    commit = UPSTREAM_ROUTE_BASELINE["snapshot_commit"]
    refs = (
        ("checker_ref", "checker_sha256"),
        ("contract_ref", "contract_sha256"),
        ("run_ref", "run_sha256"),
    )
    try:
        artifacts_valid = all(
            hashlib.sha256(
                _git_show_bytes(commit, UPSTREAM_ROUTE_BASELINE[ref_key])
            ).hexdigest()
            == UPSTREAM_ROUTE_BASELINE[sha_key]
            for ref_key, sha_key in refs
        )
    except (OSError, KeyError, subprocess.CalledProcessError):
        return False
    report = _upstream_route_report()
    return (
        artifacts_valid
        and report.get("valid") is True
        and report.get("result") == UPSTREAM_ROUTE_BASELINE["expected_result"]
        and report.get("scenario_count") == 14
        and report.get("passed_scenario_count") == 14
    )


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    """Fail closed unless the exact P3 contract and all bindings are live."""

    value: Mapping[str, Any] = contract if isinstance(contract, Mapping) else {}
    adapter = value.get("format_control_adapter", {})
    coverage = value.get("format_coverage", {})
    fallback = value.get("fallback_quality_contract", {})
    instruction = value.get("instruction_text_contract", {})
    result = value.get("result_contract", {})
    runtime = value.get("runtime_boundary", {})
    gate = value.get("phase4_entry_gate", {})
    truth = value.get("truth_flags", {})
    checks = {
        "root_exact_shape": isinstance(contract, Mapping)
        and set(value) == ROOT_KEYS,
        "canonical_contract_identity": (
            _canonical_sha256(value) == EXPECTED_CANONICAL_CONTRACT_SHA256
        ),
        "identity_exact": (
            value.get("schema_version")
            == "ids.stage047.parser_output.phase3.scenarios.v1"
            and value.get("stage") == "STAGE-047"
            and value.get("phase") == "Phase 3"
            and value.get("task_id") == "IDS-V0_1-STAGE047-P3"
            and value.get("acceptance_id") == "ACC-STAGE-047"
            and value.get("local_code") == "D08-S003"
            and value.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_FORMAT_LABELED_PREPARSED_OUTPUT_SCENARIOS"
            and value.get("contract_state")
            == "PHASE3_SCENARIOS_VALID_REAL_PARSER_FALLBACK_AND_PERSISTENCE_DISABLED"
            and value.get("next_gate") == NEXT_GATE
        ),
        "source_binding_exact_and_live": (
            value.get("source_binding") == SOURCE_BINDING and source_live()
        ),
        "phase2_commit_exact_and_live": (
            value.get("phase2_commit_binding") == PHASE2_BINDING
            and phase2_commit_live()
        ),
        "phase2_artifacts_exact_and_live": (
            value.get("phase2_artifact_bindings") == PHASE2_ARTIFACTS
            and phase2_artifacts_live()
        ),
        "upstream_route_exact_and_live": (
            value.get("upstream_route_baseline") == UPSTREAM_ROUTE_BASELINE
            and upstream_route_baseline_live()
        ),
        "adapter_exact_and_runtime_disabled": (
            isinstance(adapter, Mapping)
            and adapter.get("adapter_state")
            == "SYNTHETIC_FORMAT_LABELED_PREPARSED_CONTROL_NOT_RUNTIME_PARSER"
            and adapter.get("format_routes") == FORMAT_CONTROL_ROUTES
            and adapter.get("source_file_access_allowed") is False
            and adapter.get("runtime_parser_selection_allowed") is False
            and adapter.get("parser_dispatch_allowed") is False
            and adapter.get("parser_execution_allowed") is False
            and adapter.get("fallback_execution_allowed") is False
            and adapter.get("production_use_allowed") is False
        ),
        "catalog_and_coverage_exact": (
            value.get("scenario_catalog") == SCENARIOS
            and isinstance(coverage, Mapping)
            and coverage.get("supported_types") == list(FORMAT_CONTROL_ROUTES)
            and coverage.get("image_types") == ["PNG", "JPEG", "TIFF"]
            and coverage.get("failure_types")
            == ["UNKNOWN", "CORRUPT_OR_UNREADABLE"]
            and coverage.get("supported_type_count") == 8
            and coverage.get("scenario_count") == 16
            and coverage.get("all_taskpack_format_groups_covered") is True
        ),
        "result_metrics_exact": (
            isinstance(result, Mapping)
            and result.get("scenario_count") == 16
            and result.get("passed_scenario_count") == 16
            and result.get("accepted_output_count") == 11
            and result.get("rejected_output_count") == 3
            and result.get("route_no_output_count") == 2
            and result.get("status_counts") == EXPECTED_STATUS_COUNTS
            and result.get("silent_drop_count_required") == 0
            and result.get("parser_execution_count_required") == 0
            and result.get("fallback_execution_count_required") == 0
            and result.get("persistent_write_count_required") == 0
            and result.get("raw_payload_retained_in_report") is False
        ),
        "fallback_fail_closed": (
            isinstance(fallback, Mapping)
            and fallback.get("every_scenario_requires_explicit_disposition")
            is True
            and fallback.get("low_quality_output_requires_review") is True
            and fallback.get("unknown_route_requires_owner_review") is True
            and fallback.get("corrupt_route_requires_explicit_error") is True
            and fallback.get("silent_drop_allowed_count") == 0
            and fallback.get("fallback_attempt_count") == 0
            and fallback.get("fallback_execution_allowed") is False
            and fallback.get("fallback_runtime_owner") == "STAGE-048"
        ),
        "instruction_text_fail_closed": (
            isinstance(instruction, Mapping)
            and instruction.get("required_label")
            == "UNTRUSTED_EVIDENCE_TEXT"
            and instruction.get("required_interpretation") == "EVIDENCE_ONLY"
            and instruction.get("route_must_match_non_instruction_baseline")
            is True
            and instruction.get("system_rule_override_allowed") is False
            and instruction.get("tool_authorization_allowed") is False
            and instruction.get("policy_override_allowed") is False
            and instruction.get("prompt_injection_scan_allowed") is False
            and instruction.get("scanner_runtime_owner") == "STAGE-050"
        ),
        "runtime_boundary_fail_closed": (
            isinstance(runtime, Mapping)
            and runtime.get("synthetic_format_labeled_fixture_allowed") is True
            and runtime.get("in_memory_normalization_allowed") is True
            and runtime.get("stage046_synthetic_metadata_route_replay_allowed")
            is True
            and runtime.get("source_file_open_allowed") is False
            and runtime.get("runtime_parser_selection_allowed") is False
            and runtime.get("parser_dispatch_allowed") is False
            and runtime.get("parser_execution_allowed") is False
            and runtime.get("fallback_execution_allowed") is False
            and runtime.get("formula_execution_allowed") is False
            and runtime.get("persistent_state_write_allowed") is False
            and runtime.get("production_activation_allowed") is False
        ),
        "phase4_gate_closed": (
            isinstance(gate, Mapping)
            and gate.get("gate_id") == NEXT_GATE
            and gate.get("next_gate") == NEXT_GATE
            and gate.get("required_task_id") == "IDS-V0_1-STAGE047-P4"
            and gate.get("entry_authorized_in_this_run") is False
            and gate.get("must_run_separately") is True
            and gate.get("whole_stage_review_allowed_in_phase3") is False
            and gate.get("github_upload_allowed") is False
            and gate.get("app_reinstall_allowed") is False
        ),
        "truth_flags_exact": (
            isinstance(truth, Mapping)
            and set(truth) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
            and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
            and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
        ),
    }
    return checks


def build_format_control_input(
    *,
    detected_type: str,
    suffix: str,
    requested_at: str,
    evidence_marker: bool = False,
) -> dict[str, Any]:
    """Build a format-labelled, preparsed control wrapper through the P2 API."""

    if detected_type not in FORMAT_CONTROL_ROUTES:
        raise ValueError("detected_type is not a governed control format")
    return load_phase2_checker().build_control_input(
        detected_type=detected_type,
        suffix=suffix,
        evidence_marker=evidence_marker,
        requested_at=requested_at,
    )


def _safe_error(
    code: str,
    *,
    severity: str = "WARNING",
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "retryable": retryable,
        "message_key": "parser." + code.removeprefix("PARSER_").lower(),
    }


def _payload(
    *,
    text: str | None = None,
    tables: list[dict[str, Any]] | None = None,
    pages: list[dict[str, Any]] | None = None,
    sections: list[dict[str, Any]] | None = None,
    confidence: str = "HIGH",
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "tables": tables or [],
        "pages": pages or [],
        "sections": sections or [],
        "confidence": confidence,
        "errors": errors or [],
    }


def _page(token: str, text: str | None, *, confidence: str = "HIGH"):
    return {
        "page_id": f"page:control:{token}",
        "page_number": 1,
        "text": text,
        "table_refs": [],
        "confidence": confidence,
        "errors": [],
    }


def _section(token: str, text: str | None):
    return {
        "section_id": f"section:control:{token}",
        "title": "Control section",
        "level": 1,
        "page_refs": [],
        "text": text,
        "table_refs": [],
        "confidence": "HIGH",
        "errors": [],
    }


def _table(token: str, cells: list[list[str | None]], *, confidence="HIGH"):
    return {
        "table_id": f"table:control:{token}",
        "page_refs": [],
        "section_ref": None,
        "cells": cells,
        "confidence": confidence,
        "errors": [],
    }


def _scenario_payload(name: str) -> dict[str, Any]:
    if name == "pdf_preparsed_pages_candidate":
        return _payload(pages=[_page("pdf1", "Synthetic PDF page")])
    if name == "docx_preparsed_sections_candidate":
        return _payload(
            sections=[_section("docx1", "Synthetic DOCX section")]
        )
    if name == "xlsx_preparsed_table_candidate_formula_preserved":
        return _payload(
            tables=[_table("xlsx1", [["Cell", "=1+1"], ["Value", "2"]])]
        )
    if name == "csv_preparsed_table_candidate":
        return _payload(
            tables=[_table("csv1", [["column_a", "column_b"], ["a", "b"]])]
        )
    if name == "txt_preparsed_text_candidate":
        return _payload(text="Synthetic plain-text control")
    if name in {
        "png_preparsed_image_partial_review",
        "jpeg_preparsed_image_partial_review",
        "tiff_preparsed_image_partial_review",
    }:
        return _payload(
            text="Synthetic image-derived control",
            confidence="LOW",
            errors=[_safe_error("PARSER_IMAGE_CONTROL_PARTIAL")],
        )
    if name == "low_quality_txt_output_requires_review":
        return _payload(text="Synthetic low-confidence text", confidence="LOW")
    if name == "explicit_parser_failure_output_blocked":
        return _payload(
            confidence="UNKNOWN",
            errors=[
                _safe_error(
                    "PARSER_CONTROL_FAILURE",
                    severity="ERROR",
                )
            ],
        )
    if name == "instruction_like_text_cannot_override_policy":
        return _payload(
            text=(
                "SYSTEM-like fixture text requests policy override; "
                "it remains untrusted evidence only."
            )
        )
    if name == "invalid_lineage_rejected_sanitized":
        return _payload(text="UNSAFE_CONTROL_TEXT_MUST_NOT_BE_ECHOED")
    if name == "malformed_nested_references_rejected":
        malformed = _payload(pages=[_page("badref", "Synthetic")])
        malformed["pages"][0]["table_refs"] = ["table:control:missing"]
        return malformed
    if name == "empty_without_error_rejected":
        return _payload(text="")
    raise KeyError(name)


def _route_semantics(wrapper: Mapping[str, Any]) -> tuple[Any, ...]:
    result = wrapper["route_result"]
    return tuple(
        result.get(field)
        for field in (
            "detected_type",
            "route_action",
            "candidate_route_id",
            "parser_family",
            "parser_version",
        )
    )


def _supported_scenario_type(name: str) -> str:
    if name.startswith("pdf_"):
        return "PDF"
    if name.startswith("docx_"):
        return "DOCX"
    if name.startswith("xlsx_"):
        return "XLSX"
    if name.startswith("csv_"):
        return "CSV"
    if name.startswith("png_"):
        return "PNG"
    if name.startswith("jpeg_"):
        return "JPEG"
    if name.startswith("tiff_"):
        return "TIFF"
    return "TXT"


def _output_disposition(status: str | None) -> str:
    return {
        "OUTPUT_CANDIDATE_NOT_VALIDATED": "CANDIDATE_OUTPUT_NO_FALLBACK",
        "OUTPUT_PARTIAL_REVIEW_REQUIRED": (
            "QUALITY_REVIEW_REQUIRED_NO_FALLBACK"
        ),
        "OUTPUT_FAILED_EXPLICIT": "EXPLICIT_FAILURE_NO_FALLBACK",
    }.get(status, "REJECTED_FAIL_CLOSED_NO_FALLBACK")


def _output_scenario(name: str, index: int) -> dict[str, Any]:
    phase2 = load_phase2_checker()
    detected_type = _supported_scenario_type(name)
    wrapper = build_format_control_input(
        detected_type=detected_type,
        suffix=f"{index:x}",
        evidence_marker=(
            name == "instruction_like_text_cannot_override_policy"
        ),
        requested_at=f"2026-07-23T03:{index:02d}:00Z",
    )
    payload = _scenario_payload(name)
    if name == "invalid_lineage_rejected_sanitized":
        wrapper = copy.deepcopy(wrapper)
        wrapper["route_result_id"] = "route-result:sha256:" + "0" * 64
    normalized = phase2.normalize_parser_payload(
        wrapper,
        payload,
        produced_at=f"2026-07-23T04:{index:02d}:00Z",
    )
    output = normalized.get("output")
    output_status = output.get("status") if isinstance(output, Mapping) else None
    output_id = output.get("output_id") if isinstance(output, Mapping) else None
    quality_state = (
        output.get("quality_gate", {}).get("state")
        if isinstance(output, Mapping)
        else None
    )
    content_security = (
        output.get("content_security", {})
        if isinstance(output, Mapping)
        else {}
    )
    formula_preserved = False
    if name == "xlsx_preparsed_table_candidate_formula_preserved" and isinstance(
        output, Mapping
    ):
        formula_preserved = any(
            cell == "=1+1"
            for table in output.get("tables", [])
            for row in table.get("cells", [])
            for cell in row
        )
    route_matches_baseline = None
    if name == "instruction_like_text_cannot_override_policy":
        baseline = build_format_control_input(
            detected_type="TXT",
            suffix="f0",
            evidence_marker=False,
            requested_at="2026-07-23T03:59:00Z",
        )
        route_matches_baseline = _route_semantics(wrapper) == _route_semantics(
            baseline
        )

    accepted = normalized.get("accepted") is True
    rejected = name in {
        "invalid_lineage_rejected_sanitized",
        "malformed_nested_references_rejected",
        "empty_without_error_rejected",
    }
    expected_status = {
        "pdf_preparsed_pages_candidate": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "docx_preparsed_sections_candidate": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "xlsx_preparsed_table_candidate_formula_preserved": (
            "OUTPUT_CANDIDATE_NOT_VALIDATED"
        ),
        "csv_preparsed_table_candidate": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "txt_preparsed_text_candidate": "OUTPUT_CANDIDATE_NOT_VALIDATED",
        "png_preparsed_image_partial_review": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "jpeg_preparsed_image_partial_review": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "tiff_preparsed_image_partial_review": "OUTPUT_PARTIAL_REVIEW_REQUIRED",
        "low_quality_txt_output_requires_review": (
            "OUTPUT_PARTIAL_REVIEW_REQUIRED"
        ),
        "explicit_parser_failure_output_blocked": "OUTPUT_FAILED_EXPLICIT",
        "instruction_like_text_cannot_override_policy": (
            "OUTPUT_CANDIDATE_NOT_VALIDATED"
        ),
    }.get(name)
    accepted_valid = (
        not rejected
        and accepted
        and output_status == expected_status
        and isinstance(output_id, str)
        and output_id.startswith("parser-output:sha256:")
        and phase2.validate_output_envelope(output, wrapper)
    )
    rejected_valid = (
        rejected
        and not accepted
        and output is None
        and normalized.get("result_code") == "OUTPUT_REJECTED_FAIL_CLOSED"
    )
    instruction_valid = (
        name != "instruction_like_text_cannot_override_policy"
        or (
            route_matches_baseline is True
            and content_security.get("content_label")
            == "UNTRUSTED_EVIDENCE_TEXT"
            and content_security.get("interpretation") == "EVIDENCE_ONLY"
            and content_security.get("system_instruction_allowed") is False
            and content_security.get("tool_authorization_allowed") is False
            and content_security.get("policy_override_allowed") is False
            and content_security.get("prompt_injection_scan_performed") is False
        )
    )
    formula_valid = (
        name != "xlsx_preparsed_table_candidate_formula_preserved"
        or formula_preserved
    )
    passed = (accepted_valid or rejected_valid) and instruction_valid and formula_valid
    return {
        "status": "PASS" if passed else "FAIL_CLOSED",
        "result_category": "REJECTED_OUTPUT" if rejected else "ACCEPTED_OUTPUT",
        "accepted": accepted,
        "detected_type": detected_type,
        "output_status": output_status,
        "output_id": output_id,
        "normalization_result_code": normalized.get("result_code"),
        "quality_gate_state": quality_state,
        "fallback_disposition": _output_disposition(output_status),
        "explicit_disposition": accepted_valid or rejected_valid,
        "silent_drop": False if accepted_valid or rejected_valid else True,
        "content_label": content_security.get("content_label"),
        "content_interpretation": content_security.get("interpretation"),
        "formula_text_preserved": formula_preserved,
        "formula_execution_performed": False,
        "route_matches_non_instruction_baseline": route_matches_baseline,
        "system_rule_override_performed": False,
        "tool_authorization_performed": False,
        "prompt_injection_scan_performed": False,
        "rejection_sanitized": rejected_valid,
        "unsafe_input_echoed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "persistent_write_performed": False,
        "raw_payload_retained_in_report": False,
    }


def _route_no_output_scenario(name: str) -> dict[str, Any]:
    upstream_name = {
        "unknown_route_requires_owner_review_no_output": (
            "unknown_requires_owner_review"
        ),
        "corrupt_route_blocks_explicit_no_output": (
            "corrupt_input_blocks_explicitly"
        ),
    }[name]
    expected_action, disposition = {
        "unknown_route_requires_owner_review_no_output": (
            "ROUTE_REVIEW_REQUIRED",
            "OWNER_REVIEW_REQUIRED_STAGE048_NOT_RUN",
        ),
        "corrupt_route_blocks_explicit_no_output": (
            "ROUTE_BLOCKED",
            "EXPLICIT_ROUTE_ERROR_STAGE048_NOT_RUN",
        ),
    }[name]
    upstream = _upstream_route_report().get("scenario_results", {}).get(
        upstream_name,
        {},
    )
    passed = (
        upstream.get("status") == "PASS"
        and upstream.get("route_action") == expected_action
        and upstream.get("explicit_disposition") is True
        and upstream.get("silent_drop") is False
        and upstream.get("parser_execution_performed") is False
        and upstream.get("fallback_execution_performed") is False
        and upstream.get("output_refs") == []
    )
    return {
        "status": "PASS" if passed else "FAIL_CLOSED",
        "result_category": "ROUTE_NO_OUTPUT",
        "accepted": False,
        "detected_type": upstream.get("detected_type"),
        "output_status": None,
        "output_id": None,
        "normalization_result_code": None,
        "quality_gate_state": None,
        "upstream_route_action": upstream.get("route_action"),
        "fallback_disposition": disposition,
        "explicit_disposition": passed,
        "silent_drop": not passed,
        "formula_text_preserved": False,
        "formula_execution_performed": False,
        "route_matches_non_instruction_baseline": None,
        "system_rule_override_performed": False,
        "tool_authorization_performed": False,
        "prompt_injection_scan_performed": False,
        "rejection_sanitized": False,
        "unsafe_input_echoed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "persistent_write_performed": False,
        "raw_payload_retained_in_report": False,
    }


def run_scenario(scenario_id: str) -> dict[str, Any]:
    """Run one deterministic scenario and return a payload-free summary."""

    if scenario_id not in SCENARIOS:
        raise ValueError("unknown scenario_id")
    if scenario_id in {
        "unknown_route_requires_owner_review_no_output",
        "corrupt_route_blocks_explicit_no_output",
    }:
        return _route_no_output_scenario(scenario_id)
    return _output_scenario(scenario_id, SCENARIOS.index(scenario_id) + 1)


def _upstream_replay_summary() -> dict[str, Any]:
    report = _upstream_route_report()
    results = report.get("scenario_results", {})
    supported = {
        item.get("detected_type")
        for item in results.values()
        if item.get("detected_type") in FORMAT_CONTROL_ROUTES
    }
    unknown = results.get("unknown_requires_owner_review", {})
    corrupt = results.get("corrupt_input_blocks_explicitly", {})
    valid = (
        upstream_route_baseline_live()
        and report.get("valid") is True
        and report.get("scenario_count") == 14
        and report.get("passed_scenario_count") == 14
        and supported == set(FORMAT_CONTROL_ROUTES)
        and unknown.get("route_action") == "ROUTE_REVIEW_REQUIRED"
        and corrupt.get("route_action") == "ROUTE_BLOCKED"
    )
    return {
        "valid": valid,
        "result": report.get("result"),
        "scenario_count": report.get("scenario_count"),
        "passed_scenario_count": report.get("passed_scenario_count"),
        "supported_type_count": len(supported),
        "unknown_route_explicit": (
            unknown.get("explicit_disposition") is True
            and unknown.get("silent_drop") is False
        ),
        "corrupt_route_explicit": (
            corrupt.get("explicit_disposition") is True
            and corrupt.get("silent_drop") is False
        ),
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "raw_route_results_retained": False,
    }


def build_stage047_phase3_report() -> dict[str, Any]:
    """Build the deterministic, payload-free Phase 3 control report."""

    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        contract = {}
    contract_checks = validate_scenario_contract(contract)
    try:
        phase2_valid = load_phase2_checker().build_stage047_phase2_report().get(
            "valid"
        ) is True
        scenario_results = {name: run_scenario(name) for name in SCENARIOS}
    except (OSError, RuntimeError, TypeError, ValueError, KeyError):
        phase2_valid = False
        scenario_results = {}
    upstream = _upstream_replay_summary()
    passed_count = sum(
        item.get("status") == "PASS" for item in scenario_results.values()
    )
    accepted_count = sum(
        item.get("result_category") == "ACCEPTED_OUTPUT"
        and item.get("accepted") is True
        for item in scenario_results.values()
    )
    rejected_count = sum(
        item.get("result_category") == "REJECTED_OUTPUT"
        and item.get("accepted") is False
        for item in scenario_results.values()
    )
    route_no_output_count = sum(
        item.get("result_category") == "ROUTE_NO_OUTPUT"
        for item in scenario_results.values()
    )
    status_counts = {status: 0 for status in EXPECTED_STATUS_COUNTS}
    for item in scenario_results.values():
        if item.get("output_status") in status_counts:
            status_counts[item["output_status"]] += 1
    silent_drop_count = sum(
        item.get("silent_drop") is True for item in scenario_results.values()
    )
    output_ids = [
        item["output_id"]
        for item in scenario_results.values()
        if isinstance(item.get("output_id"), str)
    ]
    metrics_valid = (
        list(scenario_results) == SCENARIOS
        and len(scenario_results) == 16
        and passed_count == 16
        and accepted_count == 11
        and rejected_count == 3
        and route_no_output_count == 2
        and status_counts == EXPECTED_STATUS_COUNTS
        and len(output_ids) == len(set(output_ids)) == 11
        and silent_drop_count == 0
    )
    side_effects_absent = all(
        item.get(field) is False
        for item in scenario_results.values()
        for field in (
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "persistent_write_performed",
            "raw_payload_retained_in_report",
        )
    )
    valid = (
        bool(contract_checks)
        and all(contract_checks.values())
        and phase2_valid
        and upstream.get("valid") is True
        and metrics_valid
        and side_effects_absent
    )
    return {
        "schema_version": "ids.stage047.parser_output.phase3.report.v1",
        "stage": "STAGE-047",
        "phase": "Phase 3",
        "task_id": "IDS-V0_1-STAGE047-P3",
        "acceptance_id": "ACC-STAGE-047",
        "execution_mode": (
            "ISOLATED_NON_PRODUCTION_FORMAT_LABELED_PREPARSED_OUTPUT_SCENARIOS"
        ),
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_CLOSED",
        "contract_checks": contract_checks,
        "phase2_output_runtime_valid": phase2_valid,
        "upstream_route_replay": upstream,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": passed_count,
        "accepted_output_count": accepted_count,
        "rejected_output_count": rejected_count,
        "route_no_output_count": route_no_output_count,
        "status_counts": status_counts,
        "unique_output_id_count": len(set(output_ids)),
        "silent_drop_count": silent_drop_count,
        "scenario_results": scenario_results,
        "raw_payload_retained_in_report": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "real_ids_business_job_created": False,
        "source_file_open_performed": False,
        "file_type_redetection_performed": False,
        "actual_business_route_evaluation_performed": False,
        "runtime_parser_selected": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "ids_business_parser_output_produced": False,
        "fallback_execution_performed": False,
        "prompt_injection_scan_performed": False,
        "formula_execution_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "runtime_output_written": False,
        "production_runtime_activation_performed": False,
        "phase4_started": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
        "phase4_entry_authorized": False,
        "next_gate": NEXT_GATE if valid else "IDS-STAGE047-P3-GATE",
    }


def main() -> int:
    report = build_stage047_phase3_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
