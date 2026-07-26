#!/usr/bin/env python3
"""Build the fail-closed STAGE-044 whole-stage review report."""

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
CLEANUP_ROOT = PURSUE_ROOT / "half_product_cleanup"

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
    "STAGE-044_半成品输出清理.md"
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
    "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53"
)

PHASE_CHECKERS = {
    "phase1": PROJECT_ROOT / "scripts" / "check_half_product_cleanup.py",
    "phase2": PROJECT_ROOT / "scripts" / "check_half_product_cleanup_runtime.py",
    "phase3": PROJECT_ROOT / "scripts" / "check_half_product_cleanup_scenarios.py",
    "phase4": PROJECT_ROOT / "scripts" / "check_half_product_cleanup_delivery.py",
}
REVIEW_ARTIFACT_PATH = PURSUE_ROOT / "STAGE044_STAGE_REVIEW.md"
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS_PATH = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF_PATH = PROJECT_ROOT / "docs" / "HANDOFF.md"
MACHINE_RUN_PATH = (
    PROJECT_ROOT / "machine" / "runs" / "2026-07-19-stage044-review-local.json"
)

TASK_ID = "IDS-V0_1-STAGE044-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-044"
REVIEW_GATE = "IDS-STAGE044-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE045-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_DELETE_DISABLED"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE044-REVIEW-20260719-001"
PHASE4_COMMIT_BINDING = {
    "commit": "5da8fdf64cab35545e717900e71ccbbb5dacb11c",
    "km_ids_tree": "4df0d01406b2021ef0c4968373b9649733a5f857",
    "required_ancestor_of_head": True,
}

REVIEW_SOURCE_PATHS = (
    PURSUE_ROOT / "STAGE044_ENTRY_CONTRACT.md",
    PURSUE_ROOT / "STAGE044_PHASE1_HALF_PRODUCT_CLEANUP_SCOPE_BOUNDARY.md",
    CLEANUP_ROOT / "stage044_half_product_cleanup_contract.json",
    PHASE_CHECKERS["phase1"],
    PURSUE_ROOT / "tests" / "test_stage044_half_product_cleanup.py",
    PURSUE_ROOT / "STAGE044_PHASE2_HALF_PRODUCT_CLEANUP_SLICE.md",
    CLEANUP_ROOT / "stage044_half_product_cleanup_runtime_contract.json",
    PHASE_CHECKERS["phase2"],
    PURSUE_ROOT / "tests" / "test_stage044_half_product_cleanup_runtime.py",
    PURSUE_ROOT / "STAGE044_PHASE3_SCENARIO_VALIDATION.md",
    CLEANUP_ROOT / "stage044_half_product_cleanup_scenarios.json",
    PHASE_CHECKERS["phase3"],
    PURSUE_ROOT / "tests" / "test_stage044_half_product_cleanup_scenarios.py",
    PURSUE_ROOT / "STAGE044_PHASE4_CLOSEOUT.md",
    CLEANUP_ROOT / "stage044_half_product_cleanup_delivery_contract.json",
    PHASE_CHECKERS["phase4"],
    PURSUE_ROOT / "tests" / "test_stage044_half_product_cleanup_delivery.py",
    REVIEW_ARTIFACT_PATH,
    Path(__file__).resolve(),
    PURSUE_ROOT / "tests" / "test_stage044_half_product_cleanup_review.py",
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
        phase1 = _load_module(PHASE_CHECKERS["phase1"], "stage044_review_phase1")
        phase2 = _load_module(PHASE_CHECKERS["phase2"], "stage044_review_phase2")
        phase3 = _load_module(PHASE_CHECKERS["phase3"], "stage044_review_phase3")
        phase4 = _load_module(PHASE_CHECKERS["phase4"], "stage044_review_phase4")
        phase1_report = phase1.build_stage044_phase1_report()
        phase2_report = phase2.build_stage044_phase2_report()
        phase3_report = phase3.build_stage044_phase3_report()
        phase4_report = phase4.build_stage044_phase4_delivery_report()
    except Exception:
        return {
            "phase1_contract_valid": False,
            "phase2_slice_valid": False,
            "phase3_scenarios_valid": False,
            "phase4_delivery_valid": False,
        }
    return {
        "phase1_contract_valid": phase1_report.get("valid") is True,
        "phase2_slice_valid": phase2_report.get("phase2_slice_valid") is True,
        "phase3_scenarios_valid": (
            phase3_report.get("scenario_validation_valid") is True
        ),
        "phase4_delivery_valid": (
            phase4_report.get("delivery_contract_valid") is True
            and phase4_report.get("result")
            == "PASS_ISOLATED_CLEANUP_CLOSEOUT_DELETE_DISABLED"
        ),
    }


def _canonical_finding_checks() -> dict[str, bool]:
    false_checks = {
        "recoverable_states_excluded": False,
        "full_contract_validation_enforced": False,
        "candidate_identity_provenance_bound": False,
        "canonical_lexical_paths_enforced": False,
        "human_status_projection_exact": False,
        "review_governance_route_durable": False,
    }
    try:
        runtime = _load_module(PHASE_CHECKERS["phase2"], "stage044_review_findings")
        contract = runtime._load_contract()
        valid = runtime.build_cleanup_request()
        valid_result = runtime.evaluate_cleanup_candidate(valid, contract=contract)

        recoverable_results = [
            runtime.evaluate_cleanup_candidate(
                runtime.build_cleanup_request(observed_job_state=state),
                contract=contract,
            )
            for state in ("PAUSED", "RETRY_WAIT")
        ]

        invalid_identity_requests = [
            runtime.build_cleanup_request(input_refs=["KM_IDSystem/README.md"]),
            runtime.build_cleanup_request(
                creator_job_id="control:stage044:job:another"
            ),
            runtime.build_cleanup_request(
                approved_root_canonical_identity="root:sha256:" + "f" * 64
            ),
            runtime.build_cleanup_request(
                cleanup_manifest_ref="manifest:sha256:" + "0" * 64
            ),
            runtime.build_cleanup_request(
                writer_quiescence_evidence_ref="evidence:stage044:writer-forged"
            ),
            runtime.build_cleanup_request(
                resource_gate_evidence_ref="evidence:stage044:resource-forged"
            ),
        ]
        invalid_identity_results = [
            runtime.evaluate_cleanup_candidate(item, contract=contract)
            for item in invalid_identity_requests
        ]

        alias_requests = [
            runtime.build_cleanup_request(
                root_relative_path="control/stage044/./attempt-output.partial"
            ),
            runtime.build_cleanup_request(
                root_relative_path="control//stage044/attempt-output.partial"
            ),
        ]
        alias_results = [
            runtime.evaluate_cleanup_candidate(item, contract=contract)
            for item in alias_requests
        ]

        path_tamper = copy.deepcopy(contract)
        path_tamper["path_and_identity_contract"]["file_type_allowlist"] = [
            "DIRECTORY"
        ]
        source_tamper = copy.deepcopy(contract)
        source_tamper["source_binding"]["source_member_match_count"] = 2
        status_tamper = copy.deepcopy(contract)
        status_tamper["human_status_projection"][
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        ]["label_zh"] = "文件已自动删除"
        tampered_contracts = [path_tamper, source_tamper, status_tamper]
        tampered_results = [
            runtime.evaluate_cleanup_candidate(valid, contract=item)
            for item in tampered_contracts
        ]

        batch = BATCH_PATH.read_text(encoding="utf-8")
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
        events = EVENTS_PATH.read_text(encoding="utf-8")
        review = REVIEW_ARTIFACT_PATH.read_text(encoding="utf-8")
        handoff = "\n".join(
            HANDOFF_PATH.read_text(encoding="utf-8").splitlines()[:32]
        )
    except Exception:
        return false_checks

    return {
        "recoverable_states_excluded": (
            runtime.CANDIDATE_STATES == ["FAILED", "DEAD_LETTERED", "CANCELLED"]
            and "PAUSED" in runtime.BLOCKED_STATES
            and "RETRY_WAIT" in runtime.BLOCKED_STATES
            and all(
                item.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
                and item.get("reason_code") == "JOB_ACTIVE_SUCCEEDED_OR_UNKNOWN"
                and item.get("delete_allowed") is False
                for item in recoverable_results
            )
        ),
        "full_contract_validation_enforced": (
            all(not all(runtime.evaluate_contract(item).values()) for item in tampered_contracts)
            and all(runtime._contract_fast_valid(item) is False for item in tampered_contracts)
            and all(
                item.get("decision_action") == "REQUIRE_MANUAL_REVIEW"
                and item.get("reason_code") == "CLEANUP_CONTRACT_INVALID"
                for item in tampered_results
            )
        ),
        "candidate_identity_provenance_bound": (
            runtime.validate_cleanup_request(valid) is True
            and valid_result.get("decision_action")
            == "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
            and contract.get("evidence_identity_contract")
            == runtime.EVIDENCE_IDENTITY_CONTRACT
            and all(
                runtime.validate_cleanup_request(item) is False
                for item in invalid_identity_requests
            )
            and all(
                item.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
                and item.get("delete_allowed") is False
                for item in invalid_identity_results
            )
        ),
        "canonical_lexical_paths_enforced": (
            all(
                runtime.validate_cleanup_request(item) is False
                for item in alias_requests
            )
            and all(
                item.get("decision_action") == "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN"
                and item.get("delete_allowed") is False
                for item in alias_results
            )
        ),
        "human_status_projection_exact": (
            contract.get("human_status_projection")
            == runtime.HUMAN_STATUS_PROJECTION
            and runtime._contract_fast_valid(status_tamper) is False
            and tampered_results[-1].get("decision_action")
            == "REQUIRE_MANUAL_REVIEW"
        ),
        "review_governance_route_durable": (
            'status: "stage044_completed_reviewed_local"' in batch
            and 'next_allowed_task_id: "IDS-V0_1-STAGE045-P1"' in batch
            and 'next_gate_id: "IDS-STAGE045-P1-GATE"' in roadmap
            and REVIEW_EVENT_ID in events
            and "STAGE044-REVIEW-F6" in review
            and (
                (
                    "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                    in handoff
                    and "Next allowed task: `IDS-V0_1-STAGE045-P1`" in handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE047-P2`"
                    in handoff
                    and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE047-P3`"
                    in handoff
                    and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in handoff
                )
                or (
                    "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
                    in handoff
                    and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in handoff
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
        machine_run = json.loads(MACHINE_RUN_PATH.read_text(encoding="utf-8"))
        validator = _load_module(
            PURSUE_ROOT / "validate_stage005_governance_regression.py",
            "stage044_review_governance",
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
                'status: "stage044_completed_reviewed_local"',
                "stage044_review_state:",
                'review_status: "passed"',
                'current_task_id: "IDS-V0_1-STAGE044-REVIEW"',
                'next_allowed_task_id: "IDS-V0_1-STAGE045-P1"',
                "whole_stage_review_performed: true",
                "stage045_entry_allowed: false",
                "push_allowed: false",
            )
        ),
        "roadmap_reviewed_local_exact": all(
            term in roadmap
            for term in (
                'current_phase_id: "IDS-STAGE044-REVIEW"',
                'current_task_id: "IDS-V0_1-STAGE044-REVIEW"',
                'next_gate_id: "IDS-STAGE045-P1-GATE"',
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
                "STAGE044-REVIEW-F1",
                "STAGE044-REVIEW-F2",
                "STAGE044-REVIEW-F3",
                "STAGE044-REVIEW-F4",
                "STAGE044-REVIEW-F5",
                "STAGE044-REVIEW-F6",
                "NO_STAGE045_THIS_RUN",
                "NO_GITHUB_UPLOAD",
                "NO_APP_REINSTALL",
                "NO_RAW_METADATA_ACCESS",
                "NO_CLEANUP_OR_DELETE_RUNTIME",
            )
        ),
        "handoff_current_gate_exact": (
            (
                "Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE045-P1`" in top_handoff
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
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
                in top_handoff
                and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in top_handoff
            )
        ),
        "machine_run_exact": (
            machine_run.get("task_id") == TASK_ID
            and machine_run.get("result") == PASS_RESULT
            and machine_run.get("stage045_started") is False
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
        "all_review_sources_match_git_index": (
            bool(index_matches) and all(index_matches)
        ),
    }


def build_stage044_review_report(
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
        "schema_version": "ids.stage044.half_product_cleanup.stage_review.v1",
        "stage": "STAGE-044",
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
        "cleanup_runtime_performed": False,
        "filesystem_probe_performed": False,
        "filesystem_traversal_performed": False,
        "delete_operation_started": False,
        "unlinkat_called": False,
        "move_or_overwrite_performed": False,
        "persistent_state_write_performed": False,
        "audit_write_performed": False,
        "database_connection_performed": False,
        "raw_metadata_content_accessed": False,
        "production_runtime_activation_performed": False,
        "stage045_started": False,
        "stage045_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage044_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
