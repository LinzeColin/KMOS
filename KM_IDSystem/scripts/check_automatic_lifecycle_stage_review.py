#!/usr/bin/env python3
"""Build the fail-closed STAGE-042 whole-stage review report."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Optional
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
LIFECYCLE_ROOT = PURSUE_ROOT / "automatic_lifecycle"

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
    "STAGE-042_自动运行、暂停、恢复与关闭.md"
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
    "78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_automatic_lifecycle.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_automatic_lifecycle_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_automatic_lifecycle_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_automatic_lifecycle_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE042_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"

TASK_ID = "IDS-V0_1-STAGE042-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-042"
REVIEW_GATE = "IDS-STAGE042-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE043-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE042-REVIEW-20260718-001"
PHASE4_COMMIT_BINDING = {
    "commit": "2c489d049d73cd632e905c7af1b39ba662a2139b",
    "km_ids_tree": "7d77abfd6c00ea3b663d899335d971342ac40384",
    "required_ancestor_of_head": True,
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE042_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md",
    LIFECYCLE_ROOT / "stage042_automatic_lifecycle_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle.py",
    PURSUE_ROOT / "STAGE042_PHASE2_AUTOMATIC_LIFECYCLE_SLICE.md",
    LIFECYCLE_ROOT / "stage042_automatic_lifecycle_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle_runtime.py",
    PURSUE_ROOT / "STAGE042_PHASE3_SCENARIO_VALIDATION.md",
    LIFECYCLE_ROOT / "stage042_automatic_lifecycle_scenarios.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle_scenarios.py",
    PURSUE_ROOT / "STAGE042_PHASE4_CLOSEOUT.md",
    LIFECYCLE_ROOT / "stage042_automatic_lifecycle_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle_delivery.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle_review.py",
    PURSUE_ROOT / "validate_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage039_retry_dead_letter_review.py",
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_scenarios.py",
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_delivery.py",
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_review.py",
    PROJECT_ROOT / "scripts" / "check_lock_registry_stage_review.py",
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
    PROJECT_ROOT / "machine" / "runs" / "2026-07-18-stage042-review-local.json",
    PROJECT_ROOT / "machine" / "tools" / "render_human.py",
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
        with zipfile.ZipFile(ARCHIVE_PATH) as archive:
            matches = [name for name in archive.namelist() if name == SOURCE_MEMBER]
            member = archive.read(SOURCE_MEMBER) if len(matches) == 1 else b""
    except (OSError, KeyError, zipfile.BadZipFile, RuntimeError):
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


def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage042_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage042_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage042_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage042_review_phase4")
        phase1_report = phase1.build_stage042_phase1_report()
        phase2_report = phase2.build_stage042_phase2_report()
        phase3_report = phase3.build_stage042_phase3_report()
        phase4_report = phase4.build_stage042_phase4_delivery_report()
    except Exception:
        return {
            "phase1_contract_valid": False,
            "phase2_slice_valid": False,
            "phase3_scenarios_valid": False,
            "phase4_delivery_valid": False,
        }
    return {
        "phase1_contract_valid": phase1_report.get("phase1_contract_valid") is True,
        "phase2_slice_valid": phase2_report.get("phase2_slice_valid") is True,
        "phase3_scenarios_valid": (
            phase3_report.get("scenario_validation_valid") is True
        ),
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
        ),
    }


def _canonical_finding_checks() -> dict[str, bool]:
    try:
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage042_review_findings")
        contract = runtime.load_contract()

        ledger = runtime.IsolatedLifecycleDecisionLedger()
        original = runtime.build_control_request("AUTO_START")
        first = runtime.evaluate_lifecycle(original, contract=contract, ledger=ledger)
        replay = runtime.evaluate_lifecycle(original, contract=contract, ledger=ledger)
        changed = copy.deepcopy(original)
        changed["expected_state_version"] += 1
        conflict = runtime.evaluate_lifecycle(changed, contract=contract, ledger=ledger)
        forged = runtime.build_control_request("AUTO_START")
        forged["lifecycle_request_id"] = f"lifecycle:stage042:{'f' * 64}"
        forged_ledger = runtime.IsolatedLifecycleDecisionLedger()
        forged_result = runtime.evaluate_lifecycle(
            forged, contract=contract, ledger=forged_ledger
        )

        invalid_versions = []
        for value in (0, -1, True, 1.0):
            request = runtime.build_control_request(
                "AUTO_START", expected_state_version=value
            )
            invalid_versions.append(
                (
                    runtime.validate_control_request(request),
                    runtime.evaluate_lifecycle(request, contract=contract),
                )
            )
        wrong_reason = runtime.build_control_request(
            "AUTO_START", reason_code="CLEANUP_SCAN_DUE"
        )
        wrong_reason_result = runtime.evaluate_lifecycle(
            wrong_reason, contract=contract
        )

        valid_resume = runtime.build_control_request("AUTO_RESUME")
        valid_resume_result = runtime.evaluate_lifecycle(
            valid_resume, contract=contract
        )
        invalid_resume_results = []
        for started_at, duration in ((1000, 60), (1001, 60), (940, 59)):
            request = runtime.build_control_request("AUTO_RESUME")
            request["evidence"][
                "resource_stability_started_at_epoch_seconds"
            ] = started_at
            request["evidence"]["resource_stable_for_seconds"] = duration
            request["lifecycle_request_id"] = runtime.derive_lifecycle_request_id(
                request
            )
            invalid_resume_results.append(
                runtime.evaluate_lifecycle(request, contract=contract)
            )

        paused_cleanup = runtime.evaluate_lifecycle(
            runtime.build_control_request("CLEANUP_CANDIDATE_SCAN"),
            contract=contract,
        )
        nonpaused_cleanup = []
        for state in ("CREATED", "QUEUED", "RUNNING", "RETRY_WAIT"):
            request = runtime.build_control_request(
                "CLEANUP_CANDIDATE_SCAN",
                expected_state=state,
                active_claim_or_lock=False,
            )
            nonpaused_cleanup.append(runtime.evaluate_lifecycle(request, contract=contract))

        handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        staged = handoff.split("## IDS v0.1 Staged Development", 1)[1]
        staged_head = "\n".join(staged.splitlines()[:18])
    except Exception:
        return {
            "canonical_request_id_enforced": False,
            "positive_version_and_reason_binding_enforced": False,
            "temporal_resume_evidence_enforced": False,
            "cleanup_requires_paused_state": False,
            "current_handoff_and_review_gate_exact": False,
        }

    request_contract = contract.get("request_contract", {})
    decision_contract = contract.get("decision_contract", {})
    return {
        "canonical_request_id_enforced": (
            first.get("decision_action") == "AUTO_START_CANDIDATE"
            and first == replay
            and ledger.record_count == 1
            and conflict.get("decision_action")
            == "REJECT_LIFECYCLE_REQUEST_CONFLICT"
            and forged_result.get("decision_action")
            == "REJECT_LIFECYCLE_REQUEST_ID_MISMATCH"
            and forged_result.get("error_ref")
            == "error:LIFECYCLE_REQUEST_ID_MISMATCH"
            and forged_ledger.record_count == 0
            and contract.get("idempotency_contract", {}).get(
                "request_id_formula_enforced_for_new_requests"
            )
            is True
        ),
        "positive_version_and_reason_binding_enforced": (
            request_contract.get("expected_state_version_must_be_positive") is True
            and request_contract.get("reason_code_by_action")
            == runtime.EXPECTED_REASON_CODES
            and all(
                valid is False
                and result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                and result.get("error_ref") == "error:INVALID_LIFECYCLE_REQUEST"
                for valid, result in invalid_versions
            )
            and runtime.validate_control_request(wrong_reason) is False
            and wrong_reason_result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
        ),
        "temporal_resume_evidence_enforced": (
            valid_resume["evidence"][
                "resource_stability_started_at_epoch_seconds"
            ]
            == 940
            and valid_resume_result.get("decision_action")
            == "AUTO_RESUME_CANDIDATE"
            and all(
                result.get("decision_action") != "AUTO_RESUME_CANDIDATE"
                and result.get("transition_candidates") == []
                for result in invalid_resume_results
            )
        ),
        "cleanup_requires_paused_state": (
            decision_contract.get("CLEANUP_CANDIDATE_SCAN", {}).get(
                "eligible_states"
            )
            == ["PAUSED"]
            and paused_cleanup.get("decision_action") == "CLEANUP_CANDIDATE_ONLY"
            and all(
                result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                and result.get("transition_candidates") == []
                for result in nonpaused_cleanup
            )
        ),
        "current_handoff_and_review_gate_exact": (
            (
                "`STAGE-042` is locally reviewed" in staged_head
                or (
                    "`STAGE-041`, `STAGE-042` and `STAGE-043` are locally reviewed"
                    in staged_head
                )
            )
            and (
                "Current task: `IDS-V0_1-STAGE043-P1`" in staged_head
                or "Current task: `IDS-V0_1-STAGE043-P2`" in staged_head
                or "Current task: `IDS-V0_1-STAGE043-P3`" in staged_head
                or "Current task: `IDS-V0_1-STAGE043-P4`" in staged_head
                or "Current task: `IDS-V0_1-STAGE043-REVIEW`" in staged_head
                or "Current task: `IDS-V0_1-STAGE044-P1`" in staged_head
                or "Current task: `IDS-V0_1-STAGE044-P2`" in staged_head
            )
            and "IDS-V0_1-STAGE042-P3" not in staged_head
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
        validator = _load_module(
            PURSUE_ROOT / "validate_stage005_governance_regression.py",
            "stage042_review_governance",
        )
        current_checks = validator.evaluate_current_state_consistency(batch, roadmap)
        phase_checks = validator.evaluate_phase_state(
            batch, roadmap, require_structured=True
        )
    except (OSError, json.JSONDecodeError, RuntimeError, AttributeError):
        return {"governance_files_parse": False}

    matching = [event for event in events if event.get("event_id") == REVIEW_EVENT_ID]
    top_handoff = "\n".join(handoff.splitlines()[:28])
    return {
        "governance_files_parse": True,
        "batch_reviewed_local_exact": all(
            term in batch
            for term in (
                'status: "stage042_completed_reviewed_local"',
                "stage042_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE042-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE043-P1"',
                "whole_stage_review_performed: true",
                "stage043_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE042-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE042-REVIEW"',
                'next_gate_id: "IDS-STAGE043-P1-GATE"',
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
                "STAGE042-REVIEW-F1",
                "STAGE042-REVIEW-F2",
                "STAGE042-REVIEW-F3",
                "STAGE042-REVIEW-F4",
                "STAGE042-REVIEW-F5",
                "NO_STAGE043_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
            )
        ),
        "handoff_current_gate_exact": (
            (
                "Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P1`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P1`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P2`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P2`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P3`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P3`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-P4`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-P4`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE043-REVIEW`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE043-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P1`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P1`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P2`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P2`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P3`"
                in top_handoff
            )
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


def build_stage042_review_report(
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
        "schema_version": "ids.stage042.automatic_lifecycle.stage_review.v1",
        "stage": "STAGE-042",
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
        "phase_results": phase_results,
        "finding_count": 5,
        "finding_counts": {"Critical": 1, "Important": 4, "Minor": 0},
        "finding_checks": effective_findings,
        "governance_checks": governance_checks,
        "source_binding_checks": source_binding_checks,
        "production_runtime_activation_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "stage043_started": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage042_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
