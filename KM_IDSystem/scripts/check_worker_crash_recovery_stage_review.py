#!/usr/bin/env python3
"""Build the fail-closed STAGE-043 whole-stage review report."""

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
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
RECOVERY_ROOT = PURSUE_ROOT / "worker_crash_recovery"

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
    "STAGE-043_Worker崩溃恢复.md"
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
    "e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_worker_crash_recovery.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_worker_crash_recovery_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE043_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"

TASK_ID = "IDS-V0_1-STAGE043-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-043"
REVIEW_GATE = "IDS-STAGE043-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE044-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE043-REVIEW-20260719-001"
PHASE4_COMMIT_BINDING = {
    "commit": "641009f26df2119cf21bf33640789f4928d94037",
    "km_ids_tree": "da8e19520b72cea9db76656c12ae7ba0a1787287",
    "required_ancestor_of_head": True,
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE043_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE043_PHASE1_WORKER_CRASH_RECOVERY_SCOPE_BOUNDARY.md",
    RECOVERY_ROOT / "stage043_worker_crash_recovery_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage043_worker_crash_recovery.py",
    PURSUE_ROOT / "STAGE043_PHASE2_WORKER_CRASH_RECOVERY_SLICE.md",
    RECOVERY_ROOT / "stage043_worker_crash_recovery_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage043_worker_crash_recovery_runtime.py",
    PURSUE_ROOT / "STAGE043_PHASE3_SCENARIO_VALIDATION.md",
    RECOVERY_ROOT / "stage043_worker_crash_recovery_scenarios.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage043_worker_crash_recovery_scenarios.py",
    PURSUE_ROOT / "STAGE043_PHASE4_CLOSEOUT.md",
    RECOVERY_ROOT / "stage043_worker_crash_recovery_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage043_worker_crash_recovery_delivery.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage043_worker_crash_recovery_review.py",
    PURSUE_ROOT / "validate_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_delivery.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_runtime.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_scenarios.py",
    PURSUE_ROOT / "tests" / "test_stage039_retry_dead_letter_review.py",
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_review.py",
    PURSUE_ROOT / "tests" / "test_stage042_automatic_lifecycle_review.py",
    PROJECT_ROOT / "scripts" / "check_lock_registry_stage_review.py",
    PROJECT_ROOT / "scripts" / "check_automatic_lifecycle_stage_review.py",
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
    PROJECT_ROOT / "machine" / "runs" / "2026-07-19-stage043-review-local.json",
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


@lru_cache(maxsize=1)
def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage043_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage043_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage043_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage043_review_phase4")
        phase1_report = phase1.build_stage043_phase1_report()
        phase2_report = phase2.build_stage043_phase2_report()
        phase3_report = phase3.build_stage043_phase3_report()
        phase4_report = phase4.build_stage043_phase4_delivery_report()
    except Exception:
        return {
            "phase1_contract_valid": False,
            "phase2_slice_valid": False,
            "phase3_scenarios_valid": False,
            "phase4_delivery_valid": False,
        }
    return {
        "phase1_contract_valid": phase1_report.get("valid") is True,
        "phase2_slice_valid": phase2_report.get("result")
        == "PASS_ISOLATED_RECOVERY_DECISION_SLICE_PRODUCTION_DISABLED",
        "phase3_scenarios_valid": phase3_report.get("scenario_validation_valid")
        is True,
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED"
        ),
    }


def _canonical_finding_checks() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage043_review_f1_phase1")
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage043_review_findings")
        contract = runtime.load_contract()

        valid = runtime.build_recovery_request("CHECKPOINT_RESUME")
        valid_result = runtime.evaluate_recovery(valid, contract=contract)
        identity_invalid = [
            runtime.build_recovery_request(
                "CHECKPOINT_RESUME",
                lease_owner_ref="control:stage043:another-worker",
            ),
            runtime.build_recovery_request(
                "CHECKPOINT_RESUME",
                checkpoint_ref="checkpoint:sha256:" + "0" * 64,
            ),
            runtime.build_recovery_request(
                "CHECKPOINT_RESUME",
                quarantine_ref="quarantine:sha256:" + "f" * 64,
            ),
        ]
        identity_results = [
            runtime.evaluate_recovery(item, contract=contract)
            for item in identity_invalid
        ]

        early_detection = runtime.build_recovery_request(
            "CHECKPOINT_RESUME", crash_detected_at_epoch_seconds=999
        )
        early_result = runtime.evaluate_recovery(early_detection, contract=contract)

        pressure_invalid = [
            runtime.build_recovery_request(
                "CHECKPOINT_RESUME",
                resource_gates_passed=True,
                resource_pressure_signal="DISK_SPACE_INSUFFICIENT",
            ),
            runtime.build_recovery_request(
                "RESOURCE_PAUSE",
                resource_gates_passed=False,
                resource_pressure_signal="NONE",
            ),
        ]
        pressure_results = [
            runtime.evaluate_recovery(item, contract=contract)
            for item in pressure_invalid
        ]
        valid_pause = runtime.evaluate_recovery(
            runtime.build_recovery_request("RESOURCE_PAUSE"), contract=contract
        )

        valid_retry = runtime.evaluate_recovery(
            runtime.build_recovery_request("STAGE039_RETRY"), contract=contract
        )
        valid_failure = runtime.evaluate_recovery(
            runtime.build_recovery_request("SAFE_FAILURE"), contract=contract
        )
        error_invalid = [
            runtime.build_recovery_request(
                "STAGE039_RETRY", error_ref="error:PERMANENT_DATA_CORRUPTION"
            ),
            runtime.build_recovery_request(
                "SAFE_FAILURE", error_ref="error:TRANSIENT_OPERATION_TIMEOUT"
            ),
        ]
        error_results = [
            runtime.evaluate_recovery(item, contract=contract)
            for item in error_invalid
        ]

        non_mapping_checks = phase1.evaluate_contract([])
        phase1_report = phase1.build_stage043_phase1_report()

        handoff = HANDOFF_PATH.read_text(encoding="utf-8")
        top_handoff = "\n".join(handoff.splitlines()[:32])
    except Exception:
        return {
            "recovery_identity_evidence_bound": False,
            "crash_detection_temporal_consistency_enforced": False,
            "resource_pressure_consistency_enforced": False,
            "stage039_error_classification_bound": False,
            "phase1_checker_structured_and_source_complete": False,
            "current_handoff_and_review_gate_exact": False,
        }

    request_contract = contract.get("request_contract", {})
    return {
        "recovery_identity_evidence_bound": (
            valid_result.get("decision_action") == "CHECKPOINT_RESUME_CANDIDATE"
            and request_contract.get("evidence_identity_bindings")
            == runtime.EVIDENCE_IDENTITY_BINDINGS
            and all(runtime.validate_recovery_request(item) is False for item in identity_invalid)
            and all(
                result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                and result.get("transition_candidates") == []
                for result in identity_results
            )
        ),
        "crash_detection_temporal_consistency_enforced": (
            request_contract.get("crash_detection_temporal_consistency_required")
            is True
            and early_result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
            and early_result.get("reason_code")
            == "CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN"
        ),
        "resource_pressure_consistency_enforced": (
            request_contract.get("resource_pressure_consistency_required") is True
            and valid_pause.get("decision_action") == "RESOURCE_PAUSE_CANDIDATE"
            and all(runtime.validate_recovery_request(item) is False for item in pressure_invalid)
            and all(
                result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                and result.get("transition_candidates") == []
                for result in pressure_results
            )
        ),
        "stage039_error_classification_bound": (
            request_contract.get("error_ref_allowlist_by_intent")
            == runtime.ERROR_REFS_BY_INTENT
            and valid_retry.get("decision_action") == "STAGE039_RETRY_CANDIDATE"
            and valid_failure.get("decision_action") == "SAFE_FAILURE_CANDIDATE"
            and all(runtime.validate_recovery_request(item) is False for item in error_invalid)
            and all(
                result.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                for result in error_results
            )
        ),
        "phase1_checker_structured_and_source_complete": (
            non_mapping_checks.get("root_exact_shape") is False
            and non_mapping_checks.get("nested_exact_shapes") is False
            and not all(non_mapping_checks.values())
            and phase1._live_source_valid() is True
            and phase1_report.get("valid") is True
        ),
        "current_handoff_and_review_gate_exact": (
            (
                (
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
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P3`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE044-P4`"
                    in top_handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P4`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`"
                    in top_handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE045-P1`"
                    in top_handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE046-P1`"
                    in top_handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE047-P3`"
                    in top_handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                    in top_handoff
                    and "Next allowed task: `IDS-V0_1-STAGE047-P4`"
                    in top_handoff
                )
            )
            and "NO_STAGE044_THIS_RUN" in REVIEW_ARTIFACT_PATH.read_text(encoding="utf-8")
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
            "stage043_review_governance",
        )
        current_checks = validator.evaluate_current_state_consistency(batch, roadmap)
        phase_checks = validator.evaluate_phase_state(
            batch, roadmap, require_structured=True
        )
    except (OSError, json.JSONDecodeError, RuntimeError, AttributeError, KeyError):
        return {"governance_files_parse": False}

    matching = [event for event in events if event.get("event_id") == REVIEW_EVENT_ID]
    top_handoff = "\n".join(handoff.splitlines()[:32])
    return {
        "governance_files_parse": True,
        "batch_reviewed_local_exact": all(
            term in batch
            for term in (
                'status: "stage043_completed_reviewed_local"',
                "stage043_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE043-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE044-P1"',
                "whole_stage_review_performed: true",
                "stage044_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE043-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE043-REVIEW"',
                'next_gate_id: "IDS-STAGE044-P1-GATE"',
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
                "STAGE043-REVIEW-F1",
                "STAGE043-REVIEW-F2",
                "STAGE043-REVIEW-F3",
                "STAGE043-REVIEW-F4",
                "STAGE043-REVIEW-F5",
                "STAGE043-REVIEW-F6",
                "NO_STAGE044_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
            )
        ),
        "handoff_current_gate_exact": (
            (
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
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P3`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-P4`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-P4`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P1`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P1`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P1`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`"
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


def build_stage043_review_report(
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
        "schema_version": "ids.stage043.worker_crash_recovery.stage_review.v1",
        "stage": "STAGE-043",
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
        "finding_counts": {"Critical": 1, "Important": 5, "Minor": 0},
        "finding_checks": effective_findings,
        "governance_checks": governance_checks,
        "source_binding_checks": source_binding_checks,
        "production_runtime_activation_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "stage044_started": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage043_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
