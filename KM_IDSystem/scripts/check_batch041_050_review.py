#!/usr/bin/env python3
"""Validate the local-only independent review of IDS v0.1 STAGE-041..050.

The checker reads only the checked-in taskpack projection and prior review evidence.
It intentionally does not open business sources, raw metadata, runtime services, or
external providers.  A missing artefact or an unexpected contract field fails closed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
PURSUE_ROOT = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT_PATH = (
    PURSUE_ROOT / "batch_review" / "stage041_050_batch_review_contract.json"
)
BATCH_PATH = PURSUE_ROOT / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
STATUS_PATH = PROJECT_ROOT / "machine" / "facts" / "status.json"
PLAN_PATH = PROJECT_ROOT / "machine" / "facts" / "plan.json"
FACT_ROADMAP_PATH = PROJECT_ROOT / "machine" / "facts" / "roadmap.json"
ACCEPTANCE_PATH = PROJECT_ROOT / "machine" / "facts" / "acceptance.json"

TASK_ID = "IDS-V0_1-BATCH-041-050-REVIEW-GATE"
REVIEW_GATE = TASK_ID
NEXT_GATE = "IDS-STAGE051-P1-GATE"
SUCCESSOR_STAGE = "IDS-STAGE051"
SUCCESSOR_PHASE = "IDS-STAGE051-P1"
SUCCESSOR_TASK = "IDS-V0_1-STAGE051-P1"
SUCCESSOR_NEXT_GATE = "IDS-STAGE051-P2-GATE"
SUCCESSOR_PHASE2 = "IDS-STAGE051-P2"
SUCCESSOR_TASK2 = "IDS-V0_1-STAGE051-P2"
SUCCESSOR_NEXT_GATE2 = "IDS-STAGE051-P3-GATE"
SUCCESSOR_PHASE3 = "IDS-STAGE051-P3"
SUCCESSOR_TASK3 = "IDS-V0_1-STAGE051-P3"
SUCCESSOR_NEXT_GATE3 = "IDS-STAGE051-P4-GATE"
SUCCESSOR_PHASE4 = "IDS-STAGE051-P4"
SUCCESSOR_TASK4 = "IDS-V0_1-STAGE051-P4"
SUCCESSOR_NEXT_GATE4 = "IDS-STAGE051-REVIEW-GATE"
SUCCESSOR_REVIEW = "IDS-STAGE051-REVIEW"
SUCCESSOR_REVIEW_TASK = "IDS-V0_1-STAGE051-REVIEW"
SUCCESSOR_REVIEW_NEXT_GATE = "IDS-STAGE052-P1-GATE"
SUCCESSOR_STAGE052 = "IDS-STAGE052"
SUCCESSOR_PHASE052 = "IDS-STAGE052-P1"
SUCCESSOR_TASK052 = "IDS-V0_1-STAGE052-P1"
SUCCESSOR_NEXT_GATE052 = "IDS-STAGE052-P2-GATE"
SUCCESSOR_PHASE052_P2 = "IDS-STAGE052-P2"
SUCCESSOR_TASK052_P2 = "IDS-V0_1-STAGE052-P2"
SUCCESSOR_NEXT_GATE052_P2 = "IDS-STAGE052-P3-GATE"
SUCCESSOR_PHASE052_P3 = "IDS-STAGE052-P3"
SUCCESSOR_TASK052_P3 = "IDS-V0_1-STAGE052-P3"
SUCCESSOR_NEXT_GATE052_P3 = "IDS-STAGE052-P4-GATE"
SUCCESSOR_PHASE052_P4 = "IDS-STAGE052-P4"
SUCCESSOR_TASK052_P4 = "IDS-V0_1-STAGE052-P4"
SUCCESSOR_NEXT_GATE052_P4 = "IDS-STAGE052-REVIEW-GATE"
SUCCESSOR_PHASE052_REVIEW = "IDS-STAGE052-REVIEW"
SUCCESSOR_TASK052_REVIEW = "IDS-V0_1-STAGE052-REVIEW"
SUCCESSOR_NEXT_GATE052_REVIEW = "IDS-STAGE053-P1-GATE"
SUCCESSOR_STAGE053 = "IDS-STAGE053"
SUCCESSOR_PHASE053 = "IDS-STAGE053-P1"
SUCCESSOR_TASK053 = "IDS-V0_1-STAGE053-P1"
SUCCESSOR_NEXT_GATE053 = "IDS-STAGE053-P2-GATE"
SUCCESSOR_PHASE053_P2 = "IDS-STAGE053-P2"
SUCCESSOR_TASK053_P2 = "IDS-V0_1-STAGE053-P2"
SUCCESSOR_NEXT_GATE053_P2 = "IDS-STAGE053-P3-GATE"
SUCCESSOR_PHASE053_P3 = "IDS-STAGE053-P3"
SUCCESSOR_TASK053_P3 = "IDS-V0_1-STAGE053-P3"
SUCCESSOR_NEXT_GATE053_P3 = "IDS-STAGE053-P4-GATE"
SUCCESSOR_PHASE053_P4 = "IDS-STAGE053-P4"
SUCCESSOR_TASK053_P4 = "IDS-V0_1-STAGE053-P4"
SUCCESSOR_NEXT_GATE053_P4 = "IDS-STAGE053-REVIEW-GATE"
SUCCESSOR_PHASE053_REVIEW = "IDS-STAGE053-REVIEW"
SUCCESSOR_TASK053_REVIEW = "IDS-V0_1-STAGE053-REVIEW"
SUCCESSOR_NEXT_GATE053_REVIEW = "IDS-STAGE054-P1-GATE"
SUCCESSOR_STAGE054 = "IDS-STAGE054"
SUCCESSOR_PHASE054 = "IDS-STAGE054-P1"
SUCCESSOR_TASK054 = "IDS-V0_1-STAGE054-P1"
SUCCESSOR_NEXT_GATE054 = "IDS-STAGE054-P2-GATE"
PASS_RESULT = "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED"
EXPECTED_STAGE_IDS = [f"STAGE-{stage:03d}" for stage in range(41, 51)]
EXPECTED_ACCEPTANCE_IDS = [f"ACC-STAGE-{stage:03d}" for stage in range(41, 51)]
EXPECTED_CONTRACT_KEYS = {
    "schema_version",
    "batch_id",
    "task_id",
    "stage_range",
    "acceptance_range",
    "authority_context",
    "second_authoritative_source_created",
    "stage_reviews",
    "cross_stage_contract",
    "governance_gate",
    "findings",
    "truth_contract",
}
EXPECTED_STAGE_REVIEW_KEYS = {
    "stage_id",
    "acceptance_id",
    "expected_status",
    "review_task_id",
    "taskpack_ref",
    "review_artifact_ref",
    "checker_ref",
    "test_ref",
    "machine_run_ref",
}
EXPECTED_TRUTH = {
    "taskpack_context_read_performed": True,
    "prior_stage_review_evidence_read_performed": True,
    "second_authoritative_source_created": False,
    "ids_business_source_read_performed": False,
    "raw_metadata_content_accessed": False,
    "source_file_open_performed": False,
    "file_detection_performed": False,
    "parser_execution_performed": False,
    "fallback_execution_performed": False,
    "quality_gate_evaluation_performed": False,
    "persistent_state_write_performed": False,
    "agent_execution_performed": False,
    "model_call_performed": False,
    "model_token_consumption_performed": False,
    "ovh_deployment_performed": False,
    "production_runtime_activation_performed": False,
    "stage051_started": False,
    "batch_upload_gate_started": False,
    "github_upload_performed": False,
    "push_performed": False,
    "app_reinstall_performed": False,
}
EXPECTED_INTERFACE_CHAIN = [
    "STAGE-041 lock registration and race control -> STAGE-042 automatic lifecycle",
    "STAGE-042 automatic lifecycle -> STAGE-043 worker crash recovery",
    "STAGE-043 worker crash recovery -> STAGE-044 half-product cleanup",
    "STAGE-044 cleanup boundary -> STAGE-045 file type detection",
    "STAGE-045 file type detection -> STAGE-046 parser routing",
    "STAGE-046 parser routing -> STAGE-047 parser output contract",
    "STAGE-047 parser output contract -> STAGE-048 parser fallback boundary",
    "STAGE-048 parser fallback boundary -> STAGE-049 differential parser evaluation",
    "STAGE-049 differential parser evaluation -> STAGE-050 prompt-injection marker boundary",
]


def load_contract() -> dict[str, Any]:
    """Return the only derived review matrix used by this gate."""

    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_shape_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    stages = contract.get("stage_reviews")
    truth = contract.get("truth_contract")
    gate = contract.get("governance_gate")
    chain = contract.get("cross_stage_contract")
    findings = contract.get("findings")
    return {
        "top_level_fields_exact": set(contract) == EXPECTED_CONTRACT_KEYS,
        "identity_exact": (
            contract.get("schema_version") == "ids.v0_1.batch041_050.review_contract.v1"
            and contract.get("batch_id") == "IDS-V0_1-BATCH-041-050"
            and contract.get("task_id") == TASK_ID
            and contract.get("stage_range") == "STAGE-041..STAGE-050"
            and contract.get("acceptance_range") == "ACC-STAGE-041..ACC-STAGE-050"
            and contract.get("authority_context")
            == "FROZEN_IDS_V0_1_TASKPACK_AND_EXISTING_STAGE_REVIEW_EVIDENCE"
            and contract.get("second_authoritative_source_created") is False
        ),
        "stage_review_shapes_exact": (
            isinstance(stages, list)
            and len(stages) == 10
            and all(
                isinstance(stage, dict) and set(stage) == EXPECTED_STAGE_REVIEW_KEYS
                for stage in stages
            )
        ),
        "stage_identity_matrix_exact": (
            isinstance(stages, list)
            and [stage.get("stage_id") for stage in stages] == EXPECTED_STAGE_IDS
            and [stage.get("acceptance_id") for stage in stages]
            == EXPECTED_ACCEPTANCE_IDS
            and all(
                stage.get("review_task_id")
                == f"IDS-V0_1-{stage.get('stage_id', '').replace('-', '')}-REVIEW"
                for stage in stages
                if isinstance(stage, dict)
            )
        ),
        "cross_stage_chain_exact": (
            isinstance(chain, dict)
            and chain.get("interface_chain") == EXPECTED_INTERFACE_CHAIN
            and chain.get("runtime_execution_allowed") is False
            and chain.get("production_runtime_allowed") is False
            and chain.get("stage051_started") is False
            and chain.get("stage051_entry_gate") == NEXT_GATE
        ),
        "governance_gate_exact": (
            isinstance(gate, dict)
            and gate
            == {
                "review_status": "batch041_050_reviewed_local_global_upload_locked",
                "reviewed_stage_count": 10,
                "current_gate": REVIEW_GATE,
                "next_gate": NEXT_GATE,
                "push_allowed": False,
                "github_upload_allowed": False,
                "batch_upload_gate_deferred": "IDS-V0_1-BATCH-041-050-UPLOAD-GATE",
                "global_release_acceptance_required": "ACC-STAGE-168",
                "app_reinstall_allowed": False,
            }
        ),
        "finding_shape_exact": (
            isinstance(findings, list)
            and findings
            == [
                {
                    "finding_id": "BATCH041-050-REVIEW-F1",
                    "severity": "Important",
                    "status": "repaired",
                    "summary": "The prior per-batch upload route did not express the frozen all-taskpack completion condition.",
                    "repair": "Batch review advances only to the Stage051 entry gate while all upload paths remain deferred.",
                }
            ]
        ),
        "truth_contract_exact": isinstance(truth, dict) and truth == EXPECTED_TRUTH,
    }


def _artifact_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    stages = contract.get("stage_reviews")
    checks: dict[str, bool] = {}
    if not isinstance(stages, list):
        return {stage_id: False for stage_id in EXPECTED_STAGE_IDS}
    for stage in stages:
        stage_id = stage.get("stage_id", "UNKNOWN")
        refs = (
            stage.get("taskpack_ref"),
            stage.get("review_artifact_ref"),
            stage.get("checker_ref"),
            stage.get("test_ref"),
            stage.get("machine_run_ref"),
        )
        try:
            checks[str(stage_id)] = all(
                isinstance(ref, str) and (REPO_ROOT / ref).is_file() for ref in refs
            )
            machine_run = REPO_ROOT / str(stage.get("machine_run_ref", ""))
            if checks[str(stage_id)]:
                checks[str(stage_id)] = isinstance(_load_json(machine_run), dict)
        except (OSError, json.JSONDecodeError):
            checks[str(stage_id)] = False
    return checks


def _stage_checks(
    contract: Mapping[str, Any],
    batch: Mapping[str, Any],
    stage_result_overrides: Mapping[str, bool] | None,
) -> dict[str, bool]:
    progress = batch.get("stage_progress")
    stages = contract.get("stage_reviews")
    checks: dict[str, bool] = {}
    if not isinstance(progress, dict) or not isinstance(stages, list):
        return {stage_id: False for stage_id in EXPECTED_STAGE_IDS}
    for item in stages:
        stage_id = item.get("stage_id")
        node = progress.get(stage_id) if isinstance(stage_id, str) else None
        override = (
            stage_result_overrides.get(stage_id, True)
            if stage_result_overrides is not None and isinstance(stage_id, str)
            else True
        )
        checks[str(stage_id)] = bool(
            override
            and isinstance(node, dict)
            and node.get("status") == item.get("expected_status")
            and node.get("current_task_id") == item.get("review_task_id")
            and node.get("acceptance_id") == item.get("acceptance_id")
            and node.get("review_status") == "passed"
            and node.get("whole_stage_review_performed") is True
            and node.get("batch_review_performed") is True
            and node.get("execution_ready", False) is False
            and node.get("github_upload_allowed") is False
            and node.get("app_reinstall_allowed") is False
            and node.get("push_allowed", False) is False
        )
    return checks


def _governance_checks(
    contract: Mapping[str, Any], batch: Mapping[str, Any], roadmap: Mapping[str, Any]
) -> dict[str, bool]:
    gate = contract.get("governance_gate", {})
    transitions = batch.get("transition_history", {})
    decision = batch.get("decision", {})
    upload_gate = batch.get("upload_gate", {})
    stage050 = next(
        (
            candidate
            for candidate in roadmap.get("stages", [])
            if isinstance(candidate, dict) and candidate.get("stage_id") == "IDS-STAGE050"
        ),
        {},
    )
    phase = next(
        (
            candidate
            for candidate in stage050.get("phases", [])
            if isinstance(candidate, dict) and candidate.get("phase_id") == TASK_ID
        ),
        {},
    )
    task = next(
        (
            candidate
            for candidate in phase.get("tasks", [])
            if isinstance(candidate, dict) and candidate.get("task_id") == TASK_ID
        ),
        {},
    )
    expected_evidence = {
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/BATCH041_050_REVIEW_GATE.md",
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/batch_review/stage041_050_batch_review_contract.json",
        "KM_IDSystem/scripts/check_batch041_050_review.py",
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_batch041_050_review_gate.py",
        "KM_IDSystem/machine/runs/2026-08-12-batch041-050-review-local.json",
    }
    return {
        "batch_lock_identity_and_status": (
            batch.get("batch_id") == "IDS-V0_1-BATCH-041-050"
            and batch.get("status") == gate.get("review_status")
            and batch.get("review_task_id") == TASK_ID
            and batch.get("review_evidence_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/BATCH041_050_REVIEW_GATE.md"
            and batch.get("review_contract_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/batch_review/stage041_050_batch_review_contract.json"
        ),
        "transition_history_exact": (
            isinstance(transitions, dict)
            and transitions.get("batch041_050_review_state")
            == {
                "status": "batch041_050_reviewed_local_global_upload_locked",
                "current_task_id": TASK_ID,
                "next_gate": NEXT_GATE,
                "next_allowed_task_id": "IDS-V0_1-STAGE051-P1",
                "github_upload_allowed": False,
            }
        ),
        "decision_keeps_all_upload_paths_closed": (
            isinstance(decision, dict)
            and decision.get("current_task_id") == TASK_ID
            and decision.get("next_allowed_task_id") == "IDS-V0_1-STAGE051-P1"
            and decision.get("github_upload_allowed") is False
            and decision.get("push_allowed") is False
            and decision.get("global_upload_deferred") is True
        ),
        "upload_gate_remains_deferred": (
            isinstance(upload_gate, dict)
            and upload_gate.get("push_allowed") is False
            and upload_gate.get("github_upload_allowed") is False
            and upload_gate.get("batch_upload_gate_deferred") is True
            and upload_gate.get("global_release_acceptance_required") == "ACC-STAGE-168"
        ),
        "roadmap_current_route_exact": (
            (
                roadmap.get("current_stage_id") == "IDS-STAGE050"
                and roadmap.get("current_phase_id") == TASK_ID
                and roadmap.get("current_task_id") == TASK_ID
                and roadmap.get("next_gate_id") == NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE
                and roadmap.get("current_task_id") == SUCCESSOR_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and roadmap.get("current_phase_id") == SUCCESSOR_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_REVIEW_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_REVIEW_NEXT_GATE
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE052
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE052_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK052_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE052_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P2
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P2
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P3
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P3
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_P4
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_P4
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE053
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE053_REVIEW
                and roadmap.get("current_task_id") == SUCCESSOR_TASK053_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE053_REVIEW
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE054
                and roadmap.get("current_phase_id") == SUCCESSOR_PHASE054
                and roadmap.get("current_task_id") == SUCCESSOR_TASK054
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE054
            )
        ),
        "roadmap_phase_and_task_evidence_exact": (
            isinstance(phase, dict)
            and phase.get("status") == "completed"
            and isinstance(task, dict)
            and task.get("status") == "completed"
            and task.get("acceptance_ids") == EXPECTED_ACCEPTANCE_IDS
            and expected_evidence.issubset(
                {item for item in task.get("evidence_refs", []) if isinstance(item, str)}
            )
        ),
    }


def _projection_checks() -> dict[str, bool]:
    try:
        status = _load_json(STATUS_PATH)
        plan = _load_json(PLAN_PATH)
        fact_roadmap = _load_json(FACT_ROADMAP_PATH)
        acceptance = _load_json(ACCEPTANCE_PATH)
    except (OSError, json.JSONDecodeError):
        return {
            "status_projection_exact": False,
            "plan_projection_exact": False,
            "roadmap_projection_exact": False,
            "acceptance_projection_exact": False,
        }
    acceptance_items = acceptance.get("items", []) if isinstance(acceptance, dict) else []
    acceptance_ids = {
        item.get("id") for item in acceptance_items if isinstance(item, dict)
    }
    fact_stages = (
        fact_roadmap.get("stages", [])
        if isinstance(fact_roadmap, dict)
        else fact_roadmap
    )
    stage050 = next(
        (
            item
            for item in fact_stages
            if isinstance(item, dict) and item.get("id") == "`IDS-STAGE050`"
        ),
        {},
    ) if isinstance(fact_stages, list) else {}
    successor_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK
        and status.get("task") == SUCCESSOR_TASK
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK2
        and status.get("task") == SUCCESSOR_TASK2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK3
        and status.get("task") == SUCCESSOR_TASK3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK4
        and status.get("task") == SUCCESSOR_TASK4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_REVIEW_TASK
        and status.get("task") == SUCCESSOR_REVIEW_TASK
        and status.get("next_gate") == SUCCESSOR_REVIEW_NEXT_GATE
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052
        and status.get("task") == SUCCESSOR_TASK052
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P2
        and status.get("task") == SUCCESSOR_TASK052_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P3
        and status.get("task") == SUCCESSOR_TASK052_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_P4
        and status.get("task") == SUCCESSOR_TASK052_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage052_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE052
        and status.get("phase") == SUCCESSOR_TASK052_REVIEW
        and status.get("task") == SUCCESSOR_TASK052_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE052_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053
        and status.get("task") == SUCCESSOR_TASK053
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P2
        and status.get("task") == SUCCESSOR_TASK053_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P3
        and status.get("task") == SUCCESSOR_TASK053_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_P4
        and status.get("task") == SUCCESSOR_TASK053_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage053_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE053
        and status.get("phase") == SUCCESSOR_TASK053_REVIEW
        and status.get("task") == SUCCESSOR_TASK053_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE053_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage054_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE054
        and status.get("phase") == SUCCESSOR_TASK054
        and status.get("task") == SUCCESSOR_TASK054
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE054
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK
        and plan.get("task") == SUCCESSOR_TASK
        and SUCCESSOR_NEXT_GATE in str(plan.get("stop_condition"))
    )
    successor_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK2
        and plan.get("task") == SUCCESSOR_TASK2
        and SUCCESSOR_NEXT_GATE2 in str(plan.get("stop_condition"))
    )
    successor_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK3
        and plan.get("task") == SUCCESSOR_TASK3
        and SUCCESSOR_NEXT_GATE3 in str(plan.get("stop_condition"))
    )
    successor_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK4
        and plan.get("task") == SUCCESSOR_TASK4
        and SUCCESSOR_NEXT_GATE4 in str(plan.get("stop_condition"))
    )
    successor_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_REVIEW_TASK
        and plan.get("task") == SUCCESSOR_REVIEW_TASK
        and SUCCESSOR_REVIEW_NEXT_GATE in str(plan.get("stop_condition"))
    )
    successor_stage052_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052
        and plan.get("task") == SUCCESSOR_TASK052
        and SUCCESSOR_NEXT_GATE052 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P2
        and plan.get("task") == SUCCESSOR_TASK052_P2
        and SUCCESSOR_NEXT_GATE052_P2 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P3
        and plan.get("task") == SUCCESSOR_TASK052_P3
        and SUCCESSOR_NEXT_GATE052_P3 in str(plan.get("stop_condition"))
    )
    successor_stage052_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_P4
        and plan.get("task") == SUCCESSOR_TASK052_P4
        and SUCCESSOR_NEXT_GATE052_P4 in str(plan.get("stop_condition"))
    )
    successor_stage052_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE052
        and plan.get("phase") == SUCCESSOR_TASK052_REVIEW
        and plan.get("task") == SUCCESSOR_TASK052_REVIEW
        and SUCCESSOR_NEXT_GATE052_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage053_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053
        and plan.get("task") == SUCCESSOR_TASK053
        and SUCCESSOR_NEXT_GATE053 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P2
        and plan.get("task") == SUCCESSOR_TASK053_P2
        and SUCCESSOR_NEXT_GATE053_P2 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P3
        and plan.get("task") == SUCCESSOR_TASK053_P3
        and SUCCESSOR_NEXT_GATE053_P3 in str(plan.get("stop_condition"))
    )
    successor_stage053_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_P4
        and plan.get("task") == SUCCESSOR_TASK053_P4
        and SUCCESSOR_NEXT_GATE053_P4 in str(plan.get("stop_condition"))
    )
    successor_stage053_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE053
        and plan.get("phase") == SUCCESSOR_TASK053_REVIEW
        and plan.get("task") == SUCCESSOR_TASK053_REVIEW
        and SUCCESSOR_NEXT_GATE053_REVIEW in str(plan.get("stop_condition"))
    )
    successor_stage054_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE054
        and plan.get("phase") == SUCCESSOR_TASK054
        and plan.get("task") == SUCCESSOR_TASK054
        and SUCCESSOR_NEXT_GATE054 in str(plan.get("stop_condition"))
    )
    return {
        "status_projection_exact": (
            successor_status
            or successor_phase2_status
            or successor_phase3_status
            or successor_phase4_status
            or successor_review_status
            or successor_stage052_status
            or successor_stage052_phase2_status
            or successor_stage052_phase3_status
            or successor_stage052_phase4_status
            or successor_stage052_review_status
            or successor_stage053_status
            or successor_stage053_phase2_status
            or successor_stage053_phase3_status
            or successor_stage053_phase4_status
            or successor_stage053_review_status
            or successor_stage054_status
            or (
                isinstance(status, dict)
                and status.get("phase") == TASK_ID
                and status.get("task") == TASK_ID
                and status.get("next_gate") == NEXT_GATE
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
        ),
        "plan_projection_exact": (
            successor_plan
            or successor_phase2_plan
            or successor_phase3_plan
            or successor_phase4_plan
            or successor_review_plan
            or successor_stage052_plan
            or successor_stage052_phase2_plan
            or successor_stage052_phase3_plan
            or successor_stage052_phase4_plan
            or successor_stage052_review_plan
            or successor_stage053_plan
            or successor_stage053_phase2_plan
            or successor_stage053_phase3_plan
            or successor_stage053_phase4_plan
            or successor_stage053_review_plan
            or successor_stage054_plan
            or (
                isinstance(plan, dict)
                and plan.get("phase") == f"`{TASK_ID}`"
                and plan.get("task") == f"`{TASK_ID}`"
                and NEXT_GATE in str(plan.get("stop_condition"))
            )
        ),
        "roadmap_projection_exact": (
            isinstance(stage050, dict)
            and "批次复审" in str(stage050.get("gate"))
            and "上传" in str(stage050.get("status"))
        ),
        "acceptance_projection_exact": {
            "`ACC-BATCH041-050-REVIEW-01`",
            "`ACC-BATCH041-050-REVIEW-02`",
            "`ACC-BATCH041-050-REVIEW-03`",
            "`ACC-BATCH041-050-REVIEW-04`",
        }.issubset(acceptance_ids),
    }


def build_batch041_050_review_report(
    *,
    contract: Mapping[str, Any] | None = None,
    stage_result_overrides: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, fail-closed batch-review report."""

    active_contract = copy.deepcopy(contract) if contract is not None else load_contract()
    batch = _load_yaml(BATCH_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    contract_shape_checks = _contract_shape_checks(active_contract)
    artifact_checks = _artifact_checks(active_contract)
    stage_checks = _stage_checks(active_contract, batch, stage_result_overrides)
    cross_stage_checks = {
        "contract_chain_preserved": contract_shape_checks["cross_stage_chain_exact"],
        "no_runtime_execution_declared": (
            active_contract.get("cross_stage_contract", {}).get("runtime_execution_allowed")
            is False
        ),
        "production_runtime_stays_disabled": (
            active_contract.get("cross_stage_contract", {}).get("production_runtime_allowed")
            is False
        ),
    }
    governance_checks = _governance_checks(active_contract, batch, roadmap)
    projection_checks = _projection_checks()
    truth_checks = {
        key: active_contract.get("truth_contract", {}).get(key) == expected
        for key, expected in EXPECTED_TRUTH.items()
    }
    review_valid = all(
        all(check.values())
        for check in (
            contract_shape_checks,
            artifact_checks,
            stage_checks,
            cross_stage_checks,
            governance_checks,
            projection_checks,
            truth_checks,
        )
    )
    return {
        "schema_version": "ids.v0_1.batch041_050.review_report.v1",
        "batch_id": "IDS-V0_1-BATCH-041-050",
        "task_id": TASK_ID,
        "reviewed_stage_count": sum(stage_checks.values()),
        "contract_shape_checks": contract_shape_checks,
        "artifact_checks": artifact_checks,
        "stage_checks": stage_checks,
        "cross_stage_checks": cross_stage_checks,
        "governance_checks": governance_checks,
        "projection_checks": projection_checks,
        "truth_checks": truth_checks,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else "FAIL_CLOSED",
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_batch041_050_review_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
