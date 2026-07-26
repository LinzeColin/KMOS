#!/usr/bin/env python3
"""Build the fail-closed STAGE-045 whole-stage review report."""

from __future__ import annotations

from functools import lru_cache
import hashlib
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Optional
import warnings
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
DETECTION_ROOT = PURSUE_ROOT / "file_type_detection"

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
    "STAGE-045_文件类型检测.md"
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
    "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_file_type_detection.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_file_type_detection_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_file_type_detection_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_file_type_detection_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE045_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"
MACHINE_RUN_PATH = (
    PROJECT_ROOT / "machine" / "runs" / "2026-07-20-stage045-review-local.json"
)

TASK_ID = "IDS-V0_1-STAGE045-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-045"
REVIEW_GATE = "IDS-STAGE045-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE046-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE045-REVIEW-20260720-001"
PHASE4_COMMIT_BINDING = {
    "commit": "c0b2f3e2069d371125b70a5621031b1332403f95",
    "km_ids_tree": "b00bab20eb5c265b7c3c3b25c0a7618d50cac2af",
    "required_ancestor_of_head": True,
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE045_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE045_PHASE1_FILE_TYPE_DETECTION_SCOPE_BOUNDARY.md",
    DETECTION_ROOT / "stage045_file_type_detection_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection.py",
    PURSUE_ROOT / "STAGE045_PHASE2_FILE_TYPE_DETECTION_SLICE.md",
    DETECTION_ROOT / "stage045_file_type_detection_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection_runtime.py",
    PURSUE_ROOT / "STAGE045_PHASE3_FILE_TYPE_DETECTION_SCENARIOS.md",
    DETECTION_ROOT / "stage045_file_type_detection_scenarios_contract.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection_scenarios.py",
    PURSUE_ROOT / "STAGE045_PHASE4_CLOSEOUT.md",
    DETECTION_ROOT / "stage045_file_type_detection_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection_delivery.py",
    PURSUE_ROOT / "STAGE045_STAGE_REVIEW_PRECHECK.md",
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection_review_repairs.py",
    PROJECT_ROOT / "machine" / "runs" / "2026-07-20-stage045-review-precheck-local.json",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage045_file_type_detection_stage_review.py",
    PURSUE_ROOT / "validate_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage005_governance_regression.py",
    BATCH_PATH,
    ROADMAP_PATH,
    EVENTS_PATH,
    HANDOFF_PATH,
    PROJECT_ROOT / "CHANGELOG.md",
    PROJECT_ROOT / "machine" / "facts" / "acceptance.json",
    PROJECT_ROOT / "machine" / "facts" / "changelog.json",
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
            matches = [name for name in archive.namelist() if name == SOURCE_MEMBER]
            member = archive.read(SOURCE_MEMBER) if len(matches) == 1 else b""
    except (OSError, KeyError, BadZipFile, RuntimeError):
        matches = []
        member = b""
    checks["source_member_unique"] = len(matches) == 1
    checks["source_member_sha256_exact"] = (
        bool(member) and hashlib.sha256(member).hexdigest() == EXPECTED_MEMBER_SHA256
    )
    return checks


def _phase4_commit_binding_valid() -> bool:
    try:
        commit = PHASE4_COMMIT_BINDING["commit"]
        tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:KM_IDSystem"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, KeyError, TypeError):
        return False
    return tree == PHASE4_COMMIT_BINDING["km_ids_tree"] and ancestor.returncode == 0


@lru_cache(maxsize=1)
def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage045_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage045_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage045_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage045_review_phase4")
        phase1_report = phase1.build_stage045_phase1_report()
        phase2_report = phase2.build_stage045_phase2_report()
        phase3_report = phase3.build_stage045_phase3_report()
        phase4_report = phase4.build_stage045_phase4_delivery_report()
    except Exception:
        return {
            "phase1_contract_valid": False,
            "phase2_slice_valid": False,
            "phase3_scenarios_valid": False,
            "phase4_delivery_valid": False,
        }
    return {
        "phase1_contract_valid": phase1_report.get("valid") is True,
        "phase2_slice_valid": phase2_report.get("valid") is True,
        "phase3_scenarios_valid": phase3_report.get("valid") is True,
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_FILE_TYPE_DETECTION_CLOSEOUT_PARSER_DISABLED"
        ),
    }


def _request(runtime: Any, *, filename: str, mime: str) -> dict[str, Any]:
    return runtime.build_detection_request(
        filename=filename,
        observed_mime=mime,
        mime_provenance_ref="evidence:stage045:final-review:mime",
        source_identity_ref="control:stage045:final-review",
        source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
        requested_at="2026-07-20T00:00:00Z",
    )


def _ooxml(*names: str) -> bytes:
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            for name in names:
                archive.writestr(name, "<control />")
    return output.getvalue()


def _canonical_finding_checks() -> dict[str, bool]:
    false_checks = {
        "approved_sources_live_exact": False,
        "bounded_format_structure_validation": False,
        "ooxml_marker_fallback_fail_closed": False,
        "ooxml_member_identity_canonical": False,
        "unknown_mime_canonical": False,
        "utc_timestamp_semantic": False,
        "evidence_prevalidated_before_signature": False,
    }
    try:
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage045_review_findings")
        contract = json.loads(runtime.CONTRACT_PATH.read_text(encoding="utf-8"))
        truncated_cases = (
            ("truncated.pdf", "application/pdf", b"%PDF-1.7\n", "PDF_STRUCTURE_INVALID"),
            ("truncated.png", "image/png", b"\x89PNG\r\n\x1a\n", "PNG_STRUCTURE_INVALID"),
            ("truncated.jpg", "image/jpeg", b"\xff\xd8\xff\xe0", "JPEG_STRUCTURE_INVALID"),
            ("truncated.tif", "image/tiff", b"II*\x00", "TIFF_STRUCTURE_INVALID"),
        )
        truncated_results = [
            (
                runtime.detect_control_bytes(_request(runtime, filename=name, mime=mime), payload),
                error,
            )
            for name, mime, payload, error in truncated_cases
        ]
        docx_mime = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
        marker_result = runtime.detect_control_bytes(
            _request(runtime, filename="misleading.docx", mime=docx_mime),
            _ooxml("unrelated/control.txt"),
        )
        invalid_member_result = runtime.detect_control_bytes(
            _request(runtime, filename="invalid.docx", mime=docx_mime),
            _ooxml("[Content_Types].xml", "word/../evil.xml"),
        )
        duplicate_result = runtime.detect_control_bytes(
            _request(runtime, filename="duplicate.docx", mime=docx_mime),
            _ooxml(
                "[Content_Types].xml",
                "[Content_Types].xml",
                "word/document.xml",
            ),
        )
        upper = _request(runtime, filename="control.bin", mime="UNKNOWN")
        lower = _request(runtime, filename="control.bin", mime="unknown")
        invalid_timestamps_blocked = []
        for timestamp in (
            "2026-13-20T00:00:00Z",
            "2026-02-30T00:00:00Z",
            "2026-07-20T24:00:00Z",
        ):
            try:
                runtime.build_detection_request(
                    filename="control.pdf",
                    observed_mime="application/pdf",
                    mime_provenance_ref="evidence:stage045:final-review:mime",
                    source_identity_ref="control:stage045:final-review",
                    source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
                    requested_at=timestamp,
                )
            except ValueError:
                invalid_timestamps_blocked.append(True)
            else:
                invalid_timestamps_blocked.append(False)
        evidence_result = runtime.detect_control_bytes(
            _request(runtime, filename="control.pdf", mime="application/pdf"),
            b"%PDF-1.7\ncontrol\n%%EOF",
            source_text_excerpt="x" * (runtime.MAX_EVIDENCE_TEXT_CHARS + 1),
        )
        source_checks = _source_integrity_checks()
    except Exception:
        return false_checks

    policy = contract.get("detector_policy", {})
    request_contract = contract.get("request_contract", {})
    runtime_boundary = contract.get("runtime_boundary", {})
    return {
        "approved_sources_live_exact": bool(source_checks)
        and all(source_checks.values()),
        "bounded_format_structure_validation": (
            policy.get("format_validation_rules") == runtime.FORMAT_VALIDATION_RULES
            and all(
                result.get("detected_type") == "CORRUPT_OR_UNREADABLE"
                and result.get("detection_state") == "TYPE_INPUT_BLOCKED"
                and result.get("route_state") == "ROUTE_BLOCKED"
                and error in result.get("errors", [])
                for result, error in truncated_results
            )
        ),
        "ooxml_marker_fallback_fail_closed": (
            marker_result.get("detected_type") == "UNKNOWN"
            and marker_result.get("detection_state")
            == "TYPE_UNKNOWN_REVIEW_REQUIRED"
            and marker_result.get("route_state") == "ROUTE_REVIEW_REQUIRED"
            and "OOXML_CONTAINER_MARKERS_MISSING"
            in marker_result.get("errors", [])
        ),
        "ooxml_member_identity_canonical": (
            policy.get("ooxml_container_rules", {}).get(
                "canonical_member_paths_required"
            )
            is True
            and policy.get("ooxml_container_rules", {}).get(
                "duplicate_member_names_allowed"
            )
            is False
            and invalid_member_result.get("detection_state") == "TYPE_INPUT_BLOCKED"
            and "OOXML_MEMBER_PATH_INVALID" in invalid_member_result.get("errors", [])
            and duplicate_result.get("detection_state") == "TYPE_INPUT_BLOCKED"
            and "OOXML_DUPLICATE_MEMBER" in duplicate_result.get("errors", [])
        ),
        "unknown_mime_canonical": (
            request_contract.get("unknown_mime_canonical_value") == "UNKNOWN"
            and upper == lower
            and upper.get("mime_signal", {}).get("value") == "UNKNOWN"
        ),
        "utc_timestamp_semantic": (
            request_contract.get("requested_at_validation")
            == "RFC3339_UTC_REAL_CALENDAR_VALUE"
            and all(invalid_timestamps_blocked)
        ),
        "evidence_prevalidated_before_signature": (
            runtime_boundary.get("evidence_text_bounds_checked_before_signature")
            is True
            and evidence_result.get("detection_state") == "TYPE_INPUT_BLOCKED"
            and "EVIDENCE_TEXT_LIMIT_EXCEEDED" in evidence_result.get("errors", [])
            and evidence_result.get("file_signature_inspection_performed") is False
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
            "stage045_review_governance",
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
                'status: "stage045_completed_reviewed_local"',
                "stage045_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE045-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE046-P1"',
                "whole_stage_review_performed: true",
                "stage046_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE045-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE045-REVIEW"',
                'next_gate_id: "IDS-STAGE046-P1-GATE"',
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
                "STAGE045-REVIEW-F0",
                "STAGE045-REVIEW-F1",
                "STAGE045-REVIEW-F2",
                "STAGE045-REVIEW-F3",
                "STAGE045-REVIEW-F4",
                "STAGE045-REVIEW-F5",
                "STAGE045-REVIEW-F6",
                "NO_STAGE046_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
                "NO_PARSER_OR_FALLBACK_RUNTIME",
            )
        ),
        "handoff_current_gate_exact": (
            (
                "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P1`" in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P1`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`" in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in top_handoff
            )
        ),
        "machine_run_exact": (
            machine_run.get("task_id") == TASK_ID
            and machine_run.get("result") == PASS_RESULT
            and machine_run.get("stage046_started") is False
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


def build_stage045_review_report(
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
        "schema_version": "ids.stage045.file_type_detection.stage_review.v1",
        "stage": "STAGE-045",
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
        "finding_count": 7,
        "finding_counts": {"Critical": 3, "Important": 4, "Minor": 0},
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
        "stage046_started": False,
        "stage046_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage045_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
