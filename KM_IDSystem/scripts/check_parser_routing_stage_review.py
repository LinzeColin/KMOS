#!/usr/bin/env python3
"""Build the fail-closed STAGE-046 whole-stage review report."""

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
ROUTING_ROOT = PURSUE_ROOT / "parser_routing"

ARCHIVE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
)
ROADMAP_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
)
INSTRUCTIONS_SOURCE_PATH = Path(
    "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt"
)
SOURCE_MEMBER = (
    "IDS_v0_1_Final_Chinese_Revised/stages/"
    "STAGE-046_解析器路由合同.md"
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
    "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_parser_routing.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_parser_routing_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_parser_routing_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_parser_routing_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE046_STAGE_REVIEW.md"
PHASE3_EVIDENCE_PATH = PURSUE_ROOT / "STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"
MACHINE_RUN_PATH = (
    PROJECT_ROOT / "machine" / "runs" / "2026-07-22-stage046-review-local.json"
)

TASK_ID = "IDS-V0_1-STAGE046-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-046"
REVIEW_GATE = "IDS-STAGE046-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE047-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE046-REVIEW-20260722-001"
PHASE4_COMMIT_BINDING = {
    "commit": "5dee024cd44e2e772776487ee21761f274c7708e",
    "root_tree": "0d0508144b84e1dea5ab92f4c629255d2d22e6a9",
    "km_ids_tree": "20da3db8680bb39acf7ac5348d8587a97e8ad393",
    "parent": "49b876ec68ec8f92f0b9df72d57cca7b2d1d3344",
    "required_ancestor_of_head": True,
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE046_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md",
    ROUTING_ROOT / "stage046_parser_routing_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing.py",
    PURSUE_ROOT / "STAGE046_PHASE2_PARSER_ROUTING_SLICE.md",
    ROUTING_ROOT / "stage046_parser_routing_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing_runtime.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-20-stage046-p2-local.json",
    PURSUE_ROOT / "STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md",
    ROUTING_ROOT / "stage046_parser_routing_scenarios_contract.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing_scenarios.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-22-stage046-p3-local.json",
    PURSUE_ROOT / "STAGE046_PHASE4_CLOSEOUT.md",
    ROUTING_ROOT / "stage046_parser_routing_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing_delivery.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-22-stage046-p4-local.json",
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing_review_repairs.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage046_parser_routing_stage_review.py",
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
        bool(member) and hashlib.sha256(member).hexdigest() == EXPECTED_MEMBER_SHA256
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


@lru_cache(maxsize=1)
def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage046_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage046_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage046_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage046_review_phase4")
        phase1_report = phase1.build_stage046_phase1_report()
        phase2_report = phase2.build_stage046_phase2_report()
        phase3_report = phase3.build_stage046_phase3_report()
        phase4_report = phase4.build_stage046_phase4_delivery_report()
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
            == "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED"
        ),
        "phase2_slice_valid": (
            phase2_report.get("valid") is True
            and phase2_report.get("result")
            == "PASS_ISOLATED_PARSER_ROUTING_SLICE_PARSER_DISABLED"
        ),
        "phase3_scenarios_valid": (
            phase3_report.get("valid") is True
            and phase3_report.get("result")
            == "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED"
        ),
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_PARSER_ROUTING_CLOSEOUT_PARSER_DISABLED"
        ),
    }


def _request(runtime: Any, **overrides: Any) -> dict[str, Any]:
    values = {
        "detection_request_id": "detection:sha256:" + "a" * 64,
        "source_fingerprint_ref": "fingerprint:sha256:" + "a" * 64,
        "source_identity_ref": "source:stage046:review:a",
        "detected_type": "PDF",
        "detection_state": "TYPE_CONFIRMED",
        "detection_confidence": "HIGH",
        "detection_evidence_ref": "evidence:stage045:stage046:review:a",
        "evidence_text_marker_applied": False,
        "requested_at": "2026-07-22T10:00:00Z",
    }
    values.update(overrides)
    return runtime.build_routing_request(**values)


def _raises_value_error(runtime: Any, **overrides: Any) -> bool:
    try:
        _request(runtime, **overrides)
    except ValueError:
        return True
    return False


def _canonical_finding_checks() -> dict[str, bool]:
    false_checks = {
        "detection_result_projection_identity_exact": False,
        "invalid_request_sanitized_no_echo": False,
        "canonical_reference_shapes_reject_paths": False,
        "route_fact_level_matches_disposition": False,
        "scenario_result_invariants_fail_closed": False,
        "phase_boundary_claim_corrected": False,
    }
    try:
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage046_review_findings_p2")
        scenarios = _load_module(
            PHASE_CHECKERS["phase3"], "stage046_review_findings_p3"
        )
        contract = json.loads(runtime.CONTRACT_PATH.read_text(encoding="utf-8"))
        scenario_contract = json.loads(
            scenarios.CONTRACT_PATH.read_text(encoding="utf-8")
        )

        pdf = _request(runtime)
        docx = _request(runtime, detected_type="DOCX")
        pdf_result = runtime.evaluate_parser_route(pdf)
        tampered = copy.deepcopy(pdf)
        tampered["detected_type"] = "DOCX"
        routing_body = {
            key: tampered[key]
            for key in runtime.REQUEST_FIELDS
            if key != "routing_request_id"
        }
        tampered["routing_request_id"] = (
            "routing:sha256:" + runtime._canonical_sha256(routing_body)
        )
        tampered_result = runtime.evaluate_parser_route(tampered)

        untrusted = {
            "routing_request_id": "file:///private/raw/control.pdf",
            "detection_request_id": "control:unverified",
            "detection_result_id": "control:unverified",
            "detected_type": {"untrusted": "value"},
            "detection_state": ["untrusted"],
            "detection_confidence": {"untrusted": "value"},
            "evidence_text_marker_applied": True,
        }
        invalid = runtime.evaluate_parser_route(untrusted)

        unsafe_refs_rejected = all(
            (
                _raises_value_error(runtime, **overrides)
                for overrides in (
                    {"source_identity_ref": "file:///private/raw/control.pdf"},
                    {"source_identity_ref": "source:review//control"},
                    {"source_identity_ref": "source:review/./control"},
                    {
                        "detection_evidence_ref": (
                            "evidence:stage045:file:///private/raw/control.pdf"
                        )
                    },
                )
            )
        )

        fact_cases = (
            ({}, "CANDIDATE"),
            (
                {
                    "detected_type": "TXT",
                    "detection_state": "TYPE_PROVISIONAL",
                    "detection_confidence": "MEDIUM",
                },
                "REVIEW_REQUIRED",
            ),
            (
                {
                    "detected_type": "UNSUPPORTED",
                    "detection_state": "TYPE_UNSUPPORTED",
                    "detection_confidence": "UNKNOWN",
                },
                "UNSUPPORTED",
            ),
            (
                {
                    "detected_type": "CORRUPT_OR_UNREADABLE",
                    "detection_state": "TYPE_INPUT_BLOCKED",
                    "detection_confidence": "UNKNOWN",
                },
                "BLOCKED",
            ),
        )
        fact_results = [
            (runtime.evaluate_parser_route(_request(runtime, **values)), expected)
            for values, expected in fact_cases
        ]

        summary_source = runtime.evaluate_parser_route(_request(runtime))
        missing_error = copy.deepcopy(summary_source)
        missing_error["errors"] = []
        unverified = copy.deepcopy(summary_source)
        unverified["detection_result_identity_status"] = "UNVERIFIED"
        missing_error_summary = scenarios._summarize(
            "pdf_high_candidate_parser_unavailable", missing_error
        )
        unverified_summary = scenarios._summarize(
            "pdf_high_candidate_parser_unavailable", unverified
        )
        phase3_text = PHASE3_EVIDENCE_PATH.read_text(encoding="utf-8")
    except Exception:
        return false_checks

    request_contract = contract.get("request_contract", {})
    result_contract = contract.get("result_contract", {})
    return {
        "detection_result_projection_identity_exact": (
            request_contract.get("detection_result_id_required") is True
            and request_contract.get("detection_result_identity_scope")
            == "INTEGRITY_ONLY_NOT_EXTERNAL_PROVENANCE"
            and pdf["detection_request_id"] == docx["detection_request_id"]
            and pdf["detection_result_id"] != docx["detection_result_id"]
            and pdf_result.get("detection_result_identity_status")
            == "PROJECTION_DIGEST_VERIFIED"
            and tampered_result.get("errors") == ["INVALID_ROUTING_REQUEST"]
            and tampered_result.get("detection_result_identity_status")
            == "UNVERIFIED"
        ),
        "invalid_request_sanitized_no_echo": (
            request_contract.get("invalid_input_echo_allowed") is False
            and invalid.get("routing_request_id") is None
            and invalid.get("detection_request_id") is None
            and invalid.get("detection_result_id") is None
            and invalid.get("detected_type") == "UNKNOWN"
            and invalid.get("detection_state") == "TYPE_INPUT_BLOCKED"
            and invalid.get("detection_confidence") == "UNKNOWN"
            and invalid.get("routing_confidence") == "UNKNOWN"
            and invalid.get("evidence_text_marker_preserved") is False
            and invalid.get("route_fact_level") == "INVALID"
            and invalid.get("errors") == ["INVALID_ROUTING_REQUEST"]
        ),
        "canonical_reference_shapes_reject_paths": (
            request_contract.get("source_path_allowed") is False
            and request_contract.get("path_like_reference_allowed") is False
            and unsafe_refs_rejected
        ),
        "route_fact_level_matches_disposition": (
            result_contract.get("route_fact_level_by_action")
            == runtime.ROUTE_FACT_LEVEL_BY_ACTION
            and all(
                result.get("route_fact_level") == expected
                for result, expected in fact_results
            )
        ),
        "scenario_result_invariants_fail_closed": (
            scenarios.RESULT_INVARIANTS_BY_ACTION
            == scenario_contract.get("result_contract", {}).get(
                "exact_invariants_by_route_action"
            )
            and missing_error_summary.get("status") == "FAIL_CLOSED"
            and unverified_summary.get("status") == "FAIL_CLOSED"
        ),
        "phase_boundary_claim_corrected": (
            "完成全 Stage 独立复审并修复其暴露问题" not in phase3_text
            and "完成 Phase 4；整 Stage 独立复审仍须后续单独执行"
            in phase3_text
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
            "stage046_review_governance",
        )
        current_checks = validator.evaluate_current_state_consistency(batch, roadmap)
        phase_checks = validator.evaluate_phase_state(
            batch, roadmap, require_structured=True
        )
    except (OSError, json.JSONDecodeError, RuntimeError, AttributeError, KeyError):
        return {"governance_files_parse": False}

    matching = [event for event in events if event.get("event_id") == REVIEW_EVENT_ID]
    top_handoff = "\n".join(handoff.splitlines()[:40])
    return {
        "governance_files_parse": True,
        "batch_reviewed_local_exact": all(
            term in batch
            for term in (
                'status: "stage046_completed_reviewed_local"',
                "stage046_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE046-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE047-P1"',
                "whole_stage_review_performed: true",
                "stage047_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE046-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE046-REVIEW"',
                'next_gate_id: "IDS-STAGE047-P1-GATE"',
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
                "STAGE046-REVIEW-F0",
                "STAGE046-REVIEW-F1",
                "STAGE046-REVIEW-F2",
                "STAGE046-REVIEW-F3",
                "STAGE046-REVIEW-F4",
                "STAGE046-REVIEW-F5",
                "NO_STAGE047_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
                "NO_PARSER_OR_FALLBACK_RUNTIME",
            )
        ),
        "handoff_current_gate_exact": (
            "Completed task in this run: `IDS-V0_1-STAGE046-REVIEW`"
            in top_handoff
            and "Next allowed task: `IDS-V0_1-STAGE047-P1`" in top_handoff
        ),
        "machine_run_exact": (
            machine_run.get("task_id") == TASK_ID
            and machine_run.get("result") == PASS_RESULT
            and machine_run.get("stage047_started") is False
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


def build_stage046_review_report(
    *, finding_checks: Optional[Mapping[str, Any]] = None
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
    review_valid = (
        phase4_valid
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
        "schema_version": "ids.stage046.parser_routing.stage_review.v1",
        "stage": "STAGE-046",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else "FAIL_CLOSED",
        "stage_review_status": (
            "completed_reviewed_local" if review_valid else "review_blocked"
        ),
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "source_integrity_valid": bool(source_checks) and all(source_checks.values()),
        "source_integrity_checks": source_checks,
        "phase4_commit_binding": PHASE4_COMMIT_BINDING,
        "phase4_commit_binding_valid": phase4_valid,
        "phase_results": phase_results,
        "finding_count": 6,
        "finding_counts": {"Critical": 2, "Important": 3, "Minor": 1},
        "finding_checks": effective_findings,
        "governance_checks": governance_checks,
        "source_binding_checks": source_binding_checks,
        "ids_business_source_read_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "persistent_state_write_performed": False,
        "audit_write_performed": False,
        "database_connection_performed": False,
        "raw_metadata_content_accessed": False,
        "production_runtime_activation_performed": False,
        "stage047_started": False,
        "stage047_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage046_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
