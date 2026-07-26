#!/usr/bin/env python3
"""Build the fail-closed STAGE-047 whole-stage review report."""

from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Optional
import unicodedata
from zipfile import BadZipFile, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
OUTPUT_ROOT = PURSUE_ROOT / "parser_output"

ARCHIVE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/"
    "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/"
    "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
SOURCE_MEMBER = (
    "IDS_v0_1_Final_Chinese_Revised/stages/"
    "STAGE-047_解析器输出合同.md"
)
EXPECTED_SOURCE_HASHES = {
    "archive_sha256_exact": (
        ARCHIVE_PATH,
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3",
    ),
    "roadmap_sha256_exact": (
        ROADMAP_SOURCE_PATH,
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6",
    ),
    "instructions_sha256_exact": (
        INSTRUCTIONS_SOURCE_PATH,
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8",
    ),
}
EXPECTED_MEMBER_SHA256 = (
    "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_parser_output.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_parser_output_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_parser_output_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_parser_output_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE047_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"
MACHINE_RUN_PATH = (
    PROJECT_ROOT / "machine" / "runs" / "2026-07-24-stage047-review-local.json"
)

TASK_ID = "IDS-V0_1-STAGE047-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-047"
REVIEW_GATE = "IDS-STAGE047-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE048-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PARSER_OUTPUT_RUNTIME_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE047-REVIEW-20260724-001"
ROUTE_HUMAN_STATUS = "控制路线夹具已绑定，未选择或执行解析器"

PHASE4_COMMIT_BINDING = {
    "commit": "007ef85e6ee30e155269284dc9c0fe89572c8161",
    "root_tree": "779309d42552653af35f4a06701fecc7a6fe62d5",
    "km_ids_tree": "5c31c7341c8d3b546066b5565c273885fbd8fe11",
    "parent": "595a507519b443faa49fca9fa0a6e8bd21cb9dde",
    "required_ancestor_of_head": True,
}
PHASE4_ARTIFACT_BINDINGS = {
    "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE047_PHASE4_CLOSEOUT.md": (
        "571154e4bb79e2ba65dbff7793304fe4c9d8500f5d8ca873920b7c81b7fd7fe5"
    ),
    (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/"
        "stage047_parser_output_delivery_contract.json"
    ): "3a7b76351a52d8e70597cb1d0b3a5fab5bed9804344d26a9cc3a55600c4efe9b",
    "KM_IDSystem/scripts/check_parser_output_delivery.py": (
        "f242f77a08bb4b961887cceb3a482dd6cc54d0c3a7038a825cc9174ccaf8f779"
    ),
    (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage047_parser_output_delivery.py"
    ): "06c6417c9b91633c691ccb33577852afd786cb62a722eda89e03837104408c49",
    "KM_IDSystem/machine/runs/2026-07-23-stage047-p4-local.json": (
        "ba62c52148743a29d1d4ebd68913b7966d2bc989d9439fa72b5a5898cd9f3986"
    ),
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE047_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE047_PHASE1_PARSER_OUTPUT_SCOPE_BOUNDARY.md",
    OUTPUT_ROOT / "stage047_parser_output_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage047_parser_output.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-22-stage047-p1-local.json",
    PURSUE_ROOT / "STAGE047_PHASE2_PARSER_OUTPUT_SLICE.md",
    OUTPUT_ROOT / "stage047_parser_output_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage047_parser_output_runtime.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-23-stage047-p2-local.json",
    PURSUE_ROOT / "STAGE047_PHASE3_PARSER_OUTPUT_SCENARIOS.md",
    OUTPUT_ROOT / "stage047_parser_output_scenarios_contract.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage047_parser_output_scenarios.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-23-stage047-p3-local.json",
    PURSUE_ROOT / "STAGE047_PHASE4_CLOSEOUT.md",
    OUTPUT_ROOT / "stage047_parser_output_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage047_parser_output_delivery.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-23-stage047-p4-local.json",
    PURSUE_ROOT / "tests" / "test_stage047_parser_output_review_repairs.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage047_parser_output_stage_review.py",
    PURSUE_ROOT / "validate_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage005_governance_regression.py",
    BATCH_PATH,
    ROADMAP_PATH,
    EVENTS_PATH,
    HANDOFF_PATH,
    PROJECT_ROOT / "CHANGELOG.md",
    PROJECT_ROOT / "machine" / "facts" / "acceptance.json",
    PROJECT_ROOT / "machine" / "facts" / "changelog.json",
    PROJECT_ROOT / "machine" / "facts" / "glossary.json",
    PROJECT_ROOT / "machine" / "facts" / "plan.json",
    PROJECT_ROOT / "machine" / "facts" / "roadmap.json",
    PROJECT_ROOT / "machine" / "facts" / "status.json",
    MACHINE_RUN_PATH,
    PROJECT_ROOT / "文档" / "00_我在哪.md",
    PROJECT_ROOT / "文档" / "02_系统架构.md",
    PROJECT_ROOT / "文档" / "03_口径字典.md",
    PROJECT_ROOT / "文档" / "05_执行与验收.md",
    PROJECT_ROOT / "文档" / "06_运维手册.md",
)


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_integrity_checks() -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for name, (path, expected) in EXPECTED_SOURCE_HASHES.items():
        try:
            checks[name] = path.is_file() and _sha256_file(path) == expected
        except OSError:
            checks[name] = False
    try:
        with ZipFile(ARCHIVE_PATH) as archive:
            expected_member_nfc = unicodedata.normalize("NFC", SOURCE_MEMBER)
            normalized = [
                name
                for name in archive.namelist()
                if unicodedata.normalize("NFC", name) == expected_member_nfc
            ]
            member = archive.read(normalized[0]) if len(normalized) == 1 else b""
    except (OSError, KeyError, BadZipFile, RuntimeError):
        normalized = []
        member = b""
    checks["source_member_unique"] = len(normalized) == 1
    checks["source_member_sha256_exact"] = (
        bool(member)
        and hashlib.sha256(member).hexdigest() == EXPECTED_MEMBER_SHA256
    )
    return checks


def _git_output(*args: str) -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _phase4_commit_binding_valid() -> bool:
    commit = PHASE4_COMMIT_BINDING["commit"]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return (
        _git_output("rev-parse", f"{commit}^{{tree}}")
        == PHASE4_COMMIT_BINDING["root_tree"]
        and _git_output("rev-parse", f"{commit}:KM_IDSystem")
        == PHASE4_COMMIT_BINDING["km_ids_tree"]
        and _git_output("rev-parse", f"{commit}^")
        == PHASE4_COMMIT_BINDING["parent"]
        and ancestor.returncode == 0
    )


def _phase4_artifact_bindings_valid() -> bool:
    commit = PHASE4_COMMIT_BINDING["commit"]
    try:
        return all(
            hashlib.sha256(
                subprocess.check_output(
                    ["git", "show", f"{commit}:{ref}"],
                    cwd=REPO_ROOT,
                    stderr=subprocess.DEVNULL,
                )
            ).hexdigest()
            == expected
            for ref, expected in PHASE4_ARTIFACT_BINDINGS.items()
        )
    except (OSError, subprocess.CalledProcessError):
        return False


@lru_cache(maxsize=1)
def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage047_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage047_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage047_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage047_review_phase4")
        phase1_report = phase1.build_stage047_phase1_report()
        phase2_report = phase2.build_stage047_phase2_report()
        phase3_report = phase3.build_stage047_phase3_report()
        phase4_report = phase4.build_stage047_phase4_delivery_report()
    except Exception:
        return {
            "phase1_contract_valid": False,
            "phase2_slice_valid": False,
            "phase3_scenarios_valid": False,
            "phase4_delivery_valid": False,
        }
    return {
        "phase1_contract_valid": (
            phase1_report.get("valid") is True
            and phase1_report.get("result")
            == "PASS_PHASE1_PARSER_OUTPUT_CONTRACT_RUNTIME_DISABLED"
        ),
        "phase2_slice_valid": (
            phase2_report.get("valid") is True
            and phase2_report.get("result")
            == "PASS_ISOLATED_OUTPUT_NORMALIZATION_PARSER_RUNTIME_DISABLED"
        ),
        "phase3_scenarios_valid": (
            phase3_report.get("valid") is True
            and phase3_report.get("result")
            == "PASS_ISOLATED_PARSER_OUTPUT_SCENARIOS_RUNTIME_DISABLED"
        ),
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_PARSER_OUTPUT_CLOSEOUT_RUNTIME_DISABLED"
        ),
    }


def _linked_payload() -> dict[str, Any]:
    return {
        "text": "Bounded review fixture.",
        "tables": [
            {
                "table_id": "table:control:1",
                "page_refs": ["page:control:1"],
                "section_ref": "section:control:1",
                "cells": [["A"]],
                "confidence": "HIGH",
                "errors": [],
            }
        ],
        "pages": [
            {
                "page_id": "page:control:1",
                "page_number": 1,
                "text": "Bounded review fixture.",
                "table_refs": ["table:control:1"],
                "confidence": "HIGH",
                "errors": [],
            }
        ],
        "sections": [
            {
                "section_id": "section:control:1",
                "title": "Review",
                "level": 1,
                "page_refs": ["page:control:1"],
                "text": "Bounded review fixture.",
                "table_refs": ["table:control:1"],
                "confidence": "HIGH",
                "errors": [],
            }
        ],
        "confidence": "HIGH",
        "errors": [],
    }


def _canonical_finding_checks() -> dict[str, bool]:
    false_checks = {
        "complete_request_result_source_lineage": False,
        "invalid_unicode_structured_rejection": False,
        "canonical_lower_ascii_control_references": False,
        "reciprocal_internal_reference_graph": False,
        "bounded_status_and_safe_errors": False,
        "monotonic_request_production_time": False,
    }
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage047_findings_p1")
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage047_findings_p2")
        phase1_contract = json.loads(
            phase1.CONTRACT_PATH.read_text(encoding="utf-8")
            if hasattr(phase1, "CONTRACT_PATH")
            else (
                OUTPUT_ROOT / "stage047_parser_output_contract.json"
            ).read_text(encoding="utf-8")
        )
        runtime_contract = json.loads(
            runtime.CONTRACT_PATH.read_text(encoding="utf-8")
        )
        incoming = phase1_contract["input_boundary"]
        runtime_input = runtime_contract["input_contract"]
        payload_contract = runtime_contract["payload_contract"]
        output_contract = runtime_contract["output_contract"]

        wrapper = runtime.build_control_input(
            suffix="a",
            requested_at="2026-07-24T01:00:00Z",
        )
        invalid_unicode = _linked_payload()
        invalid_unicode["text"] = "\ud800"
        unicode_result = runtime.normalize_parser_payload(
            wrapper,
            invalid_unicode,
            produced_at="2026-07-24T01:00:01Z",
        )

        invalid_refs = all(
            not runtime._canonical_control_ref(
                value,
                prefix="source:control:",
            )
            for value in (
                "source:control:bad\nref",
                "source:control:é",
                "source:control:.hidden",
                "source:control:Upper",
            )
        )

        page_mismatch = _linked_payload()
        page_mismatch["pages"][0]["table_refs"] = []
        page_result = runtime.normalize_parser_payload(
            wrapper,
            page_mismatch,
            produced_at="2026-07-24T01:00:01Z",
        )
        section_mismatch = _linked_payload()
        section_mismatch["sections"][0]["table_refs"] = []
        section_result = runtime.normalize_parser_payload(
            wrapper,
            section_mismatch,
            produced_at="2026-07-24T01:00:01Z",
        )

        status_tampered = copy.deepcopy(wrapper)
        status_tampered["route_result"]["human_status"] = "unexpected"
        status_tampered["route_result_id"] = runtime.route_result_id(
            status_tampered["route_result"]
        )
        oversized_code = _linked_payload()
        oversized_code["errors"] = [
            {
                "code": "PARSER_" + "A" * 90,
                "severity": "WARNING",
                "retryable": False,
                "message_key": "parser.review_warning",
            }
        ]
        oversized_message = _linked_payload()
        oversized_message["errors"] = [
            {
                "code": "PARSER_REVIEW_WARNING",
                "severity": "WARNING",
                "retryable": False,
                "message_key": "parser." + "a" * 122,
            }
        ]
        error_results = [
            runtime.normalize_parser_payload(
                wrapper,
                payload,
                produced_at="2026-07-24T01:00:01Z",
            )
            for payload in (oversized_code, oversized_message)
        ]

        early_result = runtime.normalize_parser_payload(
            wrapper,
            _linked_payload(),
            produced_at="2026-07-24T00:59:59Z",
        )
    except Exception:
        return false_checks

    expected_input_fields = [
        "route_result_id",
        "route_result",
        "routing_request",
        "source_identity_ref",
        "requested_output_schema_version",
        "requested_at",
    ]
    return {
        "complete_request_result_source_lineage": (
            incoming.get("required_wrapper_fields") == expected_input_fields
            and incoming.get("routing_request_identity_required") is True
            and incoming.get("request_result_lineage_match_required") is True
            and runtime_input.get("phase1_required_field_names")
            == expected_input_fields
            and runtime.validate_input_wrapper(wrapper)
        ),
        "invalid_unicode_structured_rejection": (
            payload_contract.get("valid_utf8_encodable_text_required") is True
            and unicode_result.get("accepted") is False
            and unicode_result.get("result_code")
            == "OUTPUT_REJECTED_FAIL_CLOSED"
            and unicode_result.get("output") is None
        ),
        "canonical_lower_ascii_control_references": (
            incoming.get("canonical_control_reference_format")
            == "LOWER_ASCII_TOKEN_SEGMENTS"
            and runtime_input.get("canonical_control_reference_format")
            == "LOWER_ASCII_TOKEN_SEGMENTS"
            and invalid_refs
            and runtime._canonical_control_ref(
                "source:control:review-1",
                prefix="source:control:",
            )
        ),
        "reciprocal_internal_reference_graph": (
            payload_contract.get("reciprocal_table_page_references_required")
            is True
            and payload_contract.get(
                "reciprocal_table_section_references_required"
            )
            is True
            and page_result.get("accepted") is False
            and section_result.get("accepted") is False
        ),
        "bounded_status_and_safe_errors": (
            runtime_input.get("route_result_human_status_exact")
            == ROUTE_HUMAN_STATUS
            and runtime.validate_input_wrapper(status_tampered) is False
            and payload_contract.get("safe_error_code_max_characters") == 96
            and payload_contract.get("safe_error_message_key_max_characters")
            == 128
            and all(result.get("accepted") is False for result in error_results)
        ),
        "monotonic_request_production_time": (
            output_contract.get("produced_at_not_before_requested_at") is True
            and early_result.get("accepted") is False
            and early_result.get("result_code")
            == "OUTPUT_REJECTED_FAIL_CLOSED"
        ),
    }


def _governance_checks() -> dict[str, bool]:
    try:
        batch = BATCH_PATH.read_text(encoding="utf-8")
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
        review = REVIEW_ARTIFACT_PATH.read_text(encoding="utf-8")
        handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        events = [
            json.loads(line)
            for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        machine_run = json.loads(MACHINE_RUN_PATH.read_text(encoding="utf-8"))
        validator = _load_module(
            PURSUE_ROOT / "validate_stage005_governance_regression.py",
            "stage047_review_governance",
        )
        current_checks = validator.evaluate_current_state_consistency(
            batch,
            roadmap,
        )
        phase_checks = validator.evaluate_phase_state(
            batch,
            roadmap,
            require_structured=True,
        )
    except (OSError, json.JSONDecodeError, RuntimeError, AttributeError, KeyError):
        return {"governance_files_parse": False}

    matching = [event for event in events if event.get("event_id") == REVIEW_EVENT_ID]
    top_handoff = "\n".join(handoff.splitlines()[:60])
    return {
        "governance_files_parse": True,
        "batch_reviewed_local_exact": all(
            term in batch
            for term in (
                'status: "stage047_completed_reviewed_local"',
                "stage047_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE047-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE048-P1"',
                "whole_stage_review_performed: true",
                "stage048_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE047-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE047-REVIEW"',
                'next_gate_id: "IDS-STAGE048-P1-GATE"',
                'status: "completed_reviewed_local"',
            )
        ),
        "stage005_current_state_valid": bool(current_checks)
        and all(value is True for value in current_checks.values()),
        "stage005_phase_state_valid": bool(phase_checks)
        and all(value is True for value in phase_checks.values()),
        "review_event_exact": (
            len(matching) == 1
            and matching[0].get("event_type") == "stage_review"
            and matching[0].get("task_id") == TASK_ID
            and matching[0].get("acceptance_ids") == [ACCEPTANCE_ID]
            and matching[0].get("fact_level") == "VERIFIED"
        ),
        "review_markers_exact": all(
            term in review
            for term in (
                "STAGE047-REVIEW-F0",
                "STAGE047-REVIEW-F1",
                "STAGE047-REVIEW-F2",
                "STAGE047-REVIEW-F3",
                "STAGE047-REVIEW-F4",
                "STAGE047-REVIEW-F5",
                "NO_STAGE048_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
                "NO_PARSER_OR_FALLBACK_RUNTIME",
            )
        ),
        "handoff_current_gate_exact": (
            "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
            in top_handoff
            and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in top_handoff
        ),
        "machine_run_exact": (
            machine_run.get("task_id") == TASK_ID
            and machine_run.get("result") == PASS_RESULT
            and machine_run.get("stage048_started") is False
            and machine_run.get("github_upload_allowed") is False
        ),
    }


def _git_source_binding_checks() -> dict[str, bool]:
    tracked: list[bool] = []
    index_matches: list[bool] = []
    for path in REVIEW_SOURCE_PATHS:
        try:
            relative = path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            tracked.append(False)
            index_matches.append(False)
            continue
        tracked_result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        tracked.append(path.is_file() and tracked_result.returncode == 0)
        index_result = subprocess.run(
            ["git", "diff", "--quiet", "--", relative],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        index_matches.append(tracked[-1] and index_result.returncode == 0)
    return {
        "all_review_sources_git_tracked": bool(tracked) and all(tracked),
        "all_review_sources_match_git_index": bool(index_matches)
        and all(index_matches),
    }


def build_stage047_review_report(
    *,
    finding_checks: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    source_checks = _source_integrity_checks()
    phase_results = _phase_results()
    canonical_findings = _canonical_finding_checks()
    effective_findings = (
        dict(finding_checks)
        if isinstance(finding_checks, Mapping)
        else canonical_findings
    )
    governance_checks = _governance_checks()
    source_binding_checks = _git_source_binding_checks()
    phase4_valid = _phase4_commit_binding_valid()
    phase4_artifacts_valid = _phase4_artifact_bindings_valid()
    review_valid = (
        phase4_valid
        and phase4_artifacts_valid
        and all(
            bool(checks) and all(value is True for value in checks.values())
            for checks in (
                source_checks,
                phase_results,
                effective_findings,
                governance_checks,
                source_binding_checks,
            )
        )
    )
    return {
        "schema_version": "ids.stage047.parser_output.stage_review.v1",
        "stage": "STAGE-047",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else "FAIL_CLOSED",
        "stage_review_status": (
            "completed_reviewed_local" if review_valid else "review_blocked"
        ),
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "source_integrity_valid": bool(source_checks)
        and all(source_checks.values()),
        "source_integrity_checks": source_checks,
        "phase4_commit_binding": PHASE4_COMMIT_BINDING,
        "phase4_commit_binding_valid": phase4_valid,
        "phase4_artifact_bindings": PHASE4_ARTIFACT_BINDINGS,
        "phase4_artifact_bindings_valid": phase4_artifacts_valid,
        "phase_results": phase_results,
        "finding_count": 6,
        "finding_counts": {"Critical": 2, "Important": 4},
        "finding_checks": effective_findings,
        "governance_checks": governance_checks,
        "source_binding_checks": source_binding_checks,
        "ids_business_source_read_performed": False,
        "source_file_open_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "quality_gate_evaluation_performed": False,
        "persistent_state_write_performed": False,
        "audit_write_performed": False,
        "database_connection_performed": False,
        "raw_metadata_content_accessed": False,
        "production_runtime_activation_performed": False,
        "stage048_started": False,
        "stage048_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage047_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
