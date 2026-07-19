#!/usr/bin/env python3
"""Build the fail-closed STAGE-041 whole-stage review report."""

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
LOCK_ROOT = PURSUE_ROOT / "lock_registry"

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
    "STAGE-041_锁注册与竞态控制.md"
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
    "2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_lock_registry.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_lock_registry_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_lock_registry_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_lock_registry_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE041_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"

TASK_ID = "IDS-V0_1-STAGE041-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-041"
REVIEW_GATE = "IDS-STAGE041-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE042-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE041-REVIEW-20260718-001"
CONTROL_REF = (
    "repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
    "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md"
)

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE041_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md",
    LOCK_ROOT / "stage041_lock_registry_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry.py",
    PURSUE_ROOT / "STAGE041_PHASE2_LOCK_REGISTRY_SLICE.md",
    LOCK_ROOT / "stage041_lock_registry_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_runtime.py",
    PURSUE_ROOT / "STAGE041_PHASE3_SCENARIO_VALIDATION.md",
    LOCK_ROOT / "stage041_lock_registry_scenarios.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_scenarios.py",
    PURSUE_ROOT / "STAGE041_PHASE4_CLOSEOUT.md",
    LOCK_ROOT / "stage041_lock_registry_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_delivery.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage041_lock_registry_review.py",
    PURSUE_ROOT / "validate_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage005_governance_regression.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_runtime.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_scenarios.py",
    PURSUE_ROOT / "tests" / "test_stage038_worker_queue_delivery.py",
    PURSUE_ROOT / "tests" / "test_stage039_retry_dead_letter_review.py",
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
    PROJECT_ROOT / "machine" / "runs" / "2026-07-18-stage041-review-local.json",
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


def _phase_results() -> dict[str, bool]:
    try:
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage041_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage041_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage041_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage041_review_phase4")
        phase1_report = phase1.build_stage041_phase1_report()
        phase2_report = phase2.build_stage041_phase2_report()
        phase3_report = phase3.build_stage041_phase3_report()
        phase4_report = phase4.build_stage041_phase4_delivery_report()
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


def _request(runtime: Any, *, role: str = "primary", now: int = 1000) -> dict[str, Any]:
    return runtime.build_control_request(
        CONTROL_REF,
        operation_family="FILE_PROCESSING",
        holder_role=role,
        requested_at_epoch_seconds=now,
    )


def _canonical_finding_checks() -> dict[str, bool]:
    try:
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage041_review_findings")
        delivery = _load_module(PHASE_CHECKERS["phase4"], "stage041_review_limits")
        contract = runtime.load_contract()

        cas_registry = runtime.IsolatedLockRegistry(contract)
        acquired = cas_registry.acquire(_request(runtime))
        invalid_commits = []
        for value in (True, 1.0):
            evidence = copy.deepcopy(acquired)
            evidence["lock_versions"] = {
                key: value for key in acquired["lock_keys"]
            }
            invalid_commits.append(
                cas_registry.can_commit(_request(runtime, now=1001), evidence)
            )
        takeover_evidence = copy.deepcopy(acquired)
        takeover_evidence["lock_versions"] = {
            key: True for key in acquired["lock_keys"]
        }
        invalid_takeover = cas_registry.takeover(
            _request(runtime, role="successor", now=1035), takeover_evidence
        )

        time_registry = runtime.IsolatedLockRegistry(contract)
        time_acquired = time_registry.acquire(_request(runtime))
        backward_commit = time_registry.can_commit(
            _request(runtime, now=999), time_acquired
        )
        backward_renew = time_registry.renew(
            _request(runtime, now=999), time_acquired
        )
        same_time_renew = time_registry.renew(
            _request(runtime, now=1000), time_acquired
        )
        expired_release = time_registry.release(
            _request(runtime, now=1030), time_acquired
        )
        negative_registry = runtime.IsolatedLockRegistry(contract)
        negative_acquire = negative_registry.acquire(_request(runtime, now=-1))

        wrong_scope = copy.deepcopy(contract)
        wrong_scope["operation_scope_contract"]["FILE_PROCESSING"][
            "job_types"
        ] = ["REPORT"]
        blank_provenance = copy.deepcopy(contract)
        item = blank_provenance["policy"]["parameter_provenance"][
            "lease_duration_seconds"
        ]
        item["source"] = ""
        item["validation_evidence"] = ""
        item["rollback"] = ""
        wrong_relationships = copy.deepcopy(contract)
        wrong_relationships["policy"]["parameter_relationships"] = ["anything"]

        handoff_lines = HANDOFF_PATH.read_text(encoding="utf-8").splitlines()[:24]
        handoff_top = "\n".join(handoff_lines)
        known_limits = delivery.build_stage041_phase4_delivery_report().get(
            "known_limits", []
        )
    except Exception:
        return {
            "strict_integer_cas_versions": False,
            "logical_time_and_live_release_fail_closed": False,
            "runtime_contract_semantics_exact": False,
            "handoff_current_truth_exact": False,
        }

    return {
        "strict_integer_cas_versions": all(
            item.get("result_code") == "STALE_FENCING_TOKEN"
            and item.get("decision_action") == "REJECT_COMMIT"
            for item in invalid_commits
        )
        and invalid_takeover.get("result_code") == "STALE_TAKEOVER_EVIDENCE",
        "logical_time_and_live_release_fail_closed": (
            negative_acquire.get("result_code") == "INVALID_CONTROL_REQUEST"
            and negative_registry.snapshot().get("locks") == {}
            and backward_commit.get("result_code")
            == "NON_MONOTONIC_LOGICAL_TIME"
            and backward_commit.get("decision_action") == "REJECT_COMMIT"
            and backward_renew.get("result_code")
            == "NON_MONOTONIC_LOGICAL_TIME"
            and same_time_renew.get("result_code") == "LEASE_NOT_EXTENDED"
            and expired_release.get("result_code") == "LEASE_EXPIRED"
            and len(time_registry.snapshot().get("locks", {})) == 2
            and "NO_TRUSTED_PRODUCTION_CLOCK_SOURCE" in known_limits
        ),
        "runtime_contract_semantics_exact": (
            all(runtime.evaluate_contract(contract).values())
            and runtime.evaluate_contract(wrong_scope).get("operation_scope_exact")
            is False
            and runtime.evaluate_contract(blank_provenance).get(
                "parameter_provenance_complete"
            )
            is False
            and runtime.evaluate_contract(wrong_relationships).get(
                "parameter_relationships_exact"
            )
            is False
        ),
        "handoff_current_truth_exact": (
            "IDS-V0_1-STAGE041-P3" not in handoff_top
            and "IDS-V0_1-STAGE041-P4`" not in handoff_top
            and (
                (
                    "Completed task in this run: `IDS-V0_1-STAGE041-REVIEW`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE042-P1`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE042-P1`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE042-P2`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE042-P2`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE042-P3`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE042-P3`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE042-P4`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE042-P4`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE042-REVIEW`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE043-P1`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE043-P1`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE043-P2`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE043-P2`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE043-P3`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE043-P3`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE043-P4`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE043-P4`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE043-REVIEW`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE043-REVIEW`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE044-P1`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P1`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE044-P2`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P2`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE044-P3`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P3`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE044-P4`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-P4`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`"
                    in handoff_top
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                    in handoff_top
                    and "Next allowed task: `IDS-V0_1-STAGE045-P1`"
                    in handoff_top
                )
            )
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
            "stage041_review_governance",
        )
        current_checks = validator.evaluate_current_state_consistency(
            batch, roadmap
        )
        phase_checks = validator.evaluate_phase_state(
            batch, roadmap, require_structured=True
        )
    except (OSError, json.JSONDecodeError, RuntimeError, AttributeError):
        return {"governance_files_parse": False}

    matching = [event for event in events if event.get("event_id") == REVIEW_EVENT_ID]
    top_handoff = "\n".join(handoff.splitlines()[:24])
    return {
        "governance_files_parse": True,
        "batch_reviewed_local_exact": all(
            term in batch
            for term in (
                'status: "stage041_completed_reviewed_local"',
                "stage041_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE041-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE042-P1"',
                "whole_stage_review_performed: true",
                "stage042_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE041-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE041-REVIEW"',
                'next_gate_id: "IDS-STAGE042-P1-GATE"',
                'status: "completed_reviewed_local"',
            )
        ),
        "stage005_current_state_valid": bool(current_checks)
        and all(value is True for value in current_checks.values()),
        "stage005_phase_state_valid": bool(phase_checks)
        and all(value is True for value in phase_checks.values()),
        "review_event_exact": len(matching) == 1
        and matching[0].get("event_type") == "stage_review"
        and matching[0].get("task_id") == TASK_ID
        and matching[0].get("acceptance_ids") == [ACCEPTANCE_ID]
        and matching[0].get("fact_level") == "VERIFIED",
        "review_markers_exact": all(
            term in review
            for term in (
                "STAGE041-REVIEW-F1",
                "STAGE041-REVIEW-F2",
                "STAGE041-REVIEW-F3",
                "STAGE041-REVIEW-F4",
                "NO_STAGE042_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
            )
        ),
        "handoff_current_gate_exact": (
            (
                "Completed task in this run: `IDS-V0_1-STAGE041-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-P1`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P1`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-P2`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P2`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-P3`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P3`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-P4`"
                in top_handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE042-P4`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE042-REVIEW`"
                in top_handoff
            )
            or (
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


def build_stage041_review_report(
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
    review_valid = all(
        bool(checks) and all(value is True for value in checks.values())
        for checks in (
            source_checks,
            phase_results,
            effective_findings,
            governance_checks,
            source_binding_checks,
        )
    )
    return {
        "schema_version": "ids.stage041.lock_registry.stage_review.v1",
        "stage": "STAGE-041",
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
        "phase_results": phase_results,
        "finding_count": 4,
        "finding_counts": {"Critical": 1, "Important": 3, "Minor": 0},
        "finding_checks": effective_findings,
        "governance_checks": governance_checks,
        "source_binding_checks": source_binding_checks,
        "production_runtime_activation_performed": False,
        "raw_metadata_content_accessed": False,
        "fake_ids_business_data_used": False,
        "stage042_started": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage041_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
