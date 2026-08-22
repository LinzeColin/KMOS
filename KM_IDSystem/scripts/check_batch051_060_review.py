#!/usr/bin/env python3
"""Fail-closed verifier for the local-only IDS v0.1 STAGE-051..060 review.

The verifier reads only checked-in taskpack projections and review evidence.  It
does not open business data, raw metadata, services, or external providers.
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
CONTRACT_PATH = PURSUE_ROOT / "batch_review" / "stage051_060_batch_review_contract.json"
BATCH_PATH = PURSUE_ROOT / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP_PATH = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
STATUS_PATH = PROJECT_ROOT / "machine" / "facts" / "status.json"
PLAN_PATH = PROJECT_ROOT / "machine" / "facts" / "plan.json"
FACT_ROADMAP_PATH = PROJECT_ROOT / "machine" / "facts" / "roadmap.json"
ACCEPTANCE_PATH = PROJECT_ROOT / "machine" / "facts" / "acceptance.json"
BATCH_RUN_PATH = PROJECT_ROOT / "machine" / "runs" / "2026-08-14-batch051-060-review-local.json"

TASK_ID = "IDS-V0_1-BATCH-051-060-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE061-P1-GATE"
NEXT_TASK = "IDS-V0_1-STAGE061-P1"
SUCCESSOR_STAGE = "IDS-STAGE061"
SUCCESSOR_PHASE = "IDS-STAGE061-P1"
SUCCESSOR_TASK = "IDS-V0_1-STAGE061-P1"
SUCCESSOR_NEXT_GATE = "IDS-STAGE061-P2-GATE"
SUCCESSOR_PHASE2 = "IDS-STAGE061-P2"
SUCCESSOR_TASK2 = "IDS-V0_1-STAGE061-P2"
SUCCESSOR_NEXT_GATE2 = "IDS-STAGE061-P3-GATE"
SUCCESSOR_PHASE3 = "IDS-STAGE061-P3"
SUCCESSOR_TASK3 = "IDS-V0_1-STAGE061-P3"
SUCCESSOR_NEXT_GATE3 = "IDS-STAGE061-P4-GATE"
SUCCESSOR_PHASE4 = "IDS-STAGE061-P4"
SUCCESSOR_TASK4 = "IDS-V0_1-STAGE061-P4"
SUCCESSOR_NEXT_GATE4 = "IDS-STAGE061-REVIEW-GATE"
SUCCESSOR_REVIEW = "IDS-STAGE061-REVIEW"
SUCCESSOR_REVIEW_TASK = "IDS-V0_1-STAGE061-REVIEW"
SUCCESSOR_REVIEW_NEXT_GATE = "IDS-STAGE062-P1-GATE"
SUCCESSOR_STAGE062 = "IDS-STAGE062"
SUCCESSOR_PHASE062 = "IDS-STAGE062-P1"
SUCCESSOR_TASK062 = "IDS-V0_1-STAGE062-P1"
SUCCESSOR_NEXT_GATE062 = "IDS-STAGE062-P2-GATE"
SUCCESSOR_PHASE062_P2 = "IDS-STAGE062-P2"
SUCCESSOR_TASK062_P2 = "IDS-V0_1-STAGE062-P2"
SUCCESSOR_NEXT_GATE062_P2 = "IDS-STAGE062-P3-GATE"
SUCCESSOR_PHASE062_P3 = "IDS-STAGE062-P3"
SUCCESSOR_TASK062_P3 = "IDS-V0_1-STAGE062-P3"
SUCCESSOR_NEXT_GATE062_P3 = "IDS-STAGE062-P4-GATE"
SUCCESSOR_PHASE062_P4 = "IDS-STAGE062-P4"
SUCCESSOR_TASK062_P4 = "IDS-V0_1-STAGE062-P4"
SUCCESSOR_NEXT_GATE062_P4 = "IDS-STAGE062-REVIEW-GATE"
SUCCESSOR_PHASE062_REVIEW = "IDS-STAGE062-REVIEW"
SUCCESSOR_TASK062_REVIEW = "IDS-V0_1-STAGE062-REVIEW"
SUCCESSOR_NEXT_GATE062_REVIEW = "IDS-STAGE063-P1-GATE"
SUCCESSOR_STAGE063 = "IDS-STAGE063"
SUCCESSOR_PHASE063 = "IDS-STAGE063-P1"
SUCCESSOR_TASK063 = "IDS-V0_1-STAGE063-P1"
SUCCESSOR_NEXT_GATE063 = "IDS-STAGE063-P2-GATE"
SUCCESSOR_PHASE063_P2 = "IDS-STAGE063-P2"
SUCCESSOR_TASK063_P2 = "IDS-V0_1-STAGE063-P2"
SUCCESSOR_NEXT_GATE063_P2 = "IDS-STAGE063-P3-GATE"
SUCCESSOR_PHASE063_P3 = "IDS-STAGE063-P3"
SUCCESSOR_TASK063_P3 = "IDS-V0_1-STAGE063-P3"
SUCCESSOR_NEXT_GATE063_P3 = "IDS-STAGE063-P4-GATE"
SUCCESSOR_PHASE063_P4 = "IDS-STAGE063-P4"
SUCCESSOR_TASK063_P4 = "IDS-V0_1-STAGE063-P4"
SUCCESSOR_NEXT_GATE063_P4 = "IDS-STAGE063-REVIEW-GATE"
SUCCESSOR_PHASE063_REVIEW = "IDS-STAGE063-REVIEW"
SUCCESSOR_TASK063_REVIEW = "IDS-V0_1-STAGE063-REVIEW"
SUCCESSOR_NEXT_GATE063_REVIEW = "IDS-STAGE064-P1-GATE"
SUCCESSOR_STAGE064 = "IDS-STAGE064"
SUCCESSOR_PHASE064 = "IDS-STAGE064-P1"
SUCCESSOR_TASK064 = "IDS-V0_1-STAGE064-P1"
SUCCESSOR_NEXT_GATE064 = "IDS-STAGE064-P2-GATE"
SUCCESSOR_PHASE064_P2 = "IDS-STAGE064-P2"
SUCCESSOR_TASK064_P2 = "IDS-V0_1-STAGE064-P2"
SUCCESSOR_NEXT_GATE064_P2 = "IDS-STAGE064-P3-GATE"
SUCCESSOR_PHASE064_P3 = "IDS-STAGE064-P3"
SUCCESSOR_TASK064_P3 = "IDS-V0_1-STAGE064-P3"
SUCCESSOR_NEXT_GATE064_P3 = "IDS-STAGE064-P4-GATE"
SUCCESSOR_PHASE064_P4 = "IDS-STAGE064-P4"
SUCCESSOR_TASK064_P4 = "IDS-V0_1-STAGE064-P4"
SUCCESSOR_NEXT_GATE064_P4 = "IDS-STAGE064-REVIEW-GATE"
SUCCESSOR_PHASE064_REVIEW = "IDS-STAGE064-REVIEW"
SUCCESSOR_TASK064_REVIEW = "IDS-V0_1-STAGE064-REVIEW"
SUCCESSOR_NEXT_GATE064_REVIEW = "IDS-STAGE065-P1-GATE"
SUCCESSOR_STAGE065 = "IDS-STAGE065"
SUCCESSOR_PHASE065 = "IDS-STAGE065-P1"
SUCCESSOR_TASK065 = "IDS-V0_1-STAGE065-P1"
SUCCESSOR_NEXT_GATE065 = "IDS-STAGE065-P2-GATE"
SUCCESSOR_PHASE065_P2 = "IDS-STAGE065-P2"
SUCCESSOR_TASK065_P2 = "IDS-V0_1-STAGE065-P2"
SUCCESSOR_NEXT_GATE065_P2 = "IDS-STAGE065-P3-GATE"
SUCCESSOR_PHASE065_P3 = "IDS-STAGE065-P3"
SUCCESSOR_TASK065_P3 = "IDS-V0_1-STAGE065-P3"
SUCCESSOR_NEXT_GATE065_P3 = "IDS-STAGE065-P4-GATE"
SUCCESSOR_PHASE065_P4 = "IDS-STAGE065-P4"
SUCCESSOR_TASK065_P4 = "IDS-V0_1-STAGE065-P4"
SUCCESSOR_NEXT_GATE065_P4 = "IDS-STAGE065-REVIEW-GATE"
SUCCESSOR_PHASE065_REVIEW = "IDS-STAGE065-REVIEW"
SUCCESSOR_TASK065_REVIEW = "IDS-V0_1-STAGE065-REVIEW"
SUCCESSOR_NEXT_GATE065_REVIEW = "IDS-STAGE066-P1-GATE"
SUCCESSOR_STAGE066 = "IDS-STAGE066"
SUCCESSOR_PHASE066 = "IDS-STAGE066-P1"
SUCCESSOR_TASK066 = "IDS-V0_1-STAGE066-P1"
SUCCESSOR_NEXT_GATE066 = "IDS-STAGE066-P2-GATE"
SUCCESSOR_PHASE066_P2 = "IDS-STAGE066-P2"
SUCCESSOR_TASK066_P2 = "IDS-V0_1-STAGE066-P2"
SUCCESSOR_NEXT_GATE066_P2 = "IDS-STAGE066-P3-GATE"
SUCCESSOR_PHASE066_P3 = "IDS-STAGE066-P3"
SUCCESSOR_TASK066_P3 = "IDS-V0_1-STAGE066-P3"
SUCCESSOR_NEXT_GATE066_P3 = "IDS-STAGE066-P4-GATE"
SUCCESSOR_PHASE066_P4 = "IDS-STAGE066-P4"
SUCCESSOR_TASK066_P4 = "IDS-V0_1-STAGE066-P4"
SUCCESSOR_NEXT_GATE066_P4 = "IDS-STAGE066-REVIEW-GATE"
SUCCESSOR_PHASE066_REVIEW = "IDS-STAGE066-REVIEW"
SUCCESSOR_TASK066_REVIEW = "IDS-V0_1-STAGE066-REVIEW"
SUCCESSOR_NEXT_GATE066_REVIEW = "IDS-STAGE067-P1-GATE"
SUCCESSOR_STAGE067 = "IDS-STAGE067"
SUCCESSOR_PHASE067 = "IDS-STAGE067-P1"
SUCCESSOR_TASK067 = "IDS-V0_1-STAGE067-P1"
SUCCESSOR_NEXT_GATE067 = "IDS-STAGE067-P2-GATE"
SUCCESSOR_PHASE067_P2 = "IDS-STAGE067-P2"
SUCCESSOR_TASK067_P2 = "IDS-V0_1-STAGE067-P2"
SUCCESSOR_NEXT_GATE067_P2 = "IDS-STAGE067-P3-GATE"
SUCCESSOR_PHASE067_P3 = "IDS-STAGE067-P3"
SUCCESSOR_TASK067_P3 = "IDS-V0_1-STAGE067-P3"
SUCCESSOR_NEXT_GATE067_P3 = "IDS-STAGE067-P4-GATE"
SUCCESSOR_PHASE067_P4 = "IDS-STAGE067-P4"
SUCCESSOR_TASK067_P4 = "IDS-V0_1-STAGE067-P4"
SUCCESSOR_NEXT_GATE067_P4 = "IDS-STAGE067-REVIEW-GATE"
SUCCESSOR_PHASE067_REVIEW = "IDS-STAGE067-REVIEW"
SUCCESSOR_TASK067_REVIEW = "IDS-V0_1-STAGE067-REVIEW"
SUCCESSOR_NEXT_GATE067_REVIEW = "IDS-STAGE068-P1-GATE"
SUCCESSOR_STAGE068 = "IDS-STAGE068"
SUCCESSOR_PHASE068 = "IDS-STAGE068-P1"
SUCCESSOR_TASK068 = "IDS-V0_1-STAGE068-P1"
SUCCESSOR_NEXT_GATE068 = "IDS-STAGE068-P2-GATE"
SUCCESSOR_PHASE068_P2 = "IDS-STAGE068-P2"
SUCCESSOR_TASK068_P2 = "IDS-V0_1-STAGE068-P2"
SUCCESSOR_NEXT_GATE068_P2 = "IDS-STAGE068-P3-GATE"
SUCCESSOR_PHASE068_P3 = "IDS-STAGE068-P3"
SUCCESSOR_TASK068_P3 = "IDS-V0_1-STAGE068-P3"
SUCCESSOR_NEXT_GATE068_P3 = "IDS-STAGE068-P4-GATE"
SUCCESSOR_PHASE068_P4 = "IDS-STAGE068-P4"
SUCCESSOR_TASK068_P4 = "IDS-V0_1-STAGE068-P4"
SUCCESSOR_NEXT_GATE068_P4 = "IDS-STAGE068-REVIEW-GATE"
SUCCESSOR_PHASE068_REVIEW = "IDS-STAGE068-REVIEW"
SUCCESSOR_TASK068_REVIEW = "IDS-V0_1-STAGE068-REVIEW"
SUCCESSOR_NEXT_GATE068_REVIEW = "IDS-STAGE069-P1-GATE"
SUCCESSOR_STAGE069 = "IDS-STAGE069"
SUCCESSOR_PHASE069 = "IDS-STAGE069-P1"
SUCCESSOR_TASK069 = "IDS-V0_1-STAGE069-P1"
SUCCESSOR_NEXT_GATE069 = "IDS-STAGE069-P2-GATE"
SUCCESSOR_PHASE069_P2 = "IDS-STAGE069-P2"
SUCCESSOR_TASK069_P2 = "IDS-V0_1-STAGE069-P2"
SUCCESSOR_NEXT_GATE069_P2 = "IDS-STAGE069-P3-GATE"
SUCCESSOR_PHASE069_P3 = "IDS-STAGE069-P3"
SUCCESSOR_TASK069_P3 = "IDS-V0_1-STAGE069-P3"
SUCCESSOR_NEXT_GATE069_P3 = "IDS-STAGE069-P4-GATE"
SUCCESSOR_PHASE069_P4 = "IDS-STAGE069-P4"
SUCCESSOR_TASK069_P4 = "IDS-V0_1-STAGE069-P4"
SUCCESSOR_NEXT_GATE069_P4 = "IDS-STAGE069-REVIEW-GATE"
SUCCESSOR_PHASE069_REVIEW = "IDS-STAGE069-REVIEW"
SUCCESSOR_TASK069_REVIEW = "IDS-V0_1-STAGE069-REVIEW"
SUCCESSOR_NEXT_GATE069_REVIEW = "IDS-STAGE070-P1-GATE"
SUCCESSOR_STAGE070 = "IDS-STAGE070"
SUCCESSOR_PHASE070 = "IDS-STAGE070-P1"
SUCCESSOR_TASK070 = "IDS-V0_1-STAGE070-P1"
SUCCESSOR_NEXT_GATE070 = "IDS-STAGE070-P2-GATE"
SUCCESSOR_PHASE070_P2 = "IDS-STAGE070-P2"
SUCCESSOR_TASK070_P2 = "IDS-V0_1-STAGE070-P2"
SUCCESSOR_NEXT_GATE070_P2 = "IDS-STAGE070-P3-GATE"
SUCCESSOR_PHASE070_P3 = "IDS-STAGE070-P3"
SUCCESSOR_TASK070_P3 = "IDS-V0_1-STAGE070-P3"
SUCCESSOR_NEXT_GATE070_P3 = "IDS-STAGE070-P4-GATE"
SUCCESSOR_PHASE070_P4 = "IDS-STAGE070-P4"
SUCCESSOR_TASK070_P4 = "IDS-V0_1-STAGE070-P4"
SUCCESSOR_NEXT_GATE070_P4 = "IDS-STAGE070-REVIEW-GATE"
SUCCESSOR_PHASE070_REVIEW = "IDS-STAGE070-REVIEW"
SUCCESSOR_TASK070_REVIEW = "IDS-V0_1-STAGE070-REVIEW"
SUCCESSOR_NEXT_GATE070_REVIEW = "IDS-STAGE071-P1-GATE"
SUCCESSOR_STAGE071 = "IDS-STAGE071"
SUCCESSOR_PHASE071 = "IDS-STAGE071-P1"
SUCCESSOR_TASK071 = "IDS-V0_1-STAGE071-P1"
SUCCESSOR_NEXT_GATE071 = "IDS-STAGE071-P2-GATE"
SUCCESSOR_PHASE071_P2 = "IDS-STAGE071-P2"
SUCCESSOR_TASK071_P2 = "IDS-V0_1-STAGE071-P2"
SUCCESSOR_NEXT_GATE071_P2 = "IDS-STAGE071-P3-GATE"
SUCCESSOR_PHASE071_P3 = "IDS-STAGE071-P3"
SUCCESSOR_TASK071_P3 = "IDS-V0_1-STAGE071-P3"
SUCCESSOR_NEXT_GATE071_P3 = "IDS-STAGE071-P4-GATE"
SUCCESSOR_PHASE071_P4 = "IDS-STAGE071-P4"
SUCCESSOR_TASK071_P4 = "IDS-V0_1-STAGE071-P4"
SUCCESSOR_NEXT_GATE071_P4 = "IDS-STAGE071-REVIEW-GATE"
SUCCESSOR_PHASE071_REVIEW = "IDS-STAGE071-REVIEW"
SUCCESSOR_TASK071_REVIEW = "IDS-V0_1-STAGE071-REVIEW"
SUCCESSOR_NEXT_GATE071_REVIEW = "IDS-STAGE072-P1-GATE"
SUCCESSOR_STAGE072 = "IDS-STAGE072"
SUCCESSOR_PHASE072_P1 = "IDS-STAGE072-P1"
SUCCESSOR_TASK072_P1 = "IDS-V0_1-STAGE072-P1"
SUCCESSOR_NEXT_GATE072_P1 = "IDS-STAGE072-P2-GATE"
SUCCESSOR_PHASE072_P2 = "IDS-STAGE072-P2"
SUCCESSOR_TASK072_P2 = "IDS-V0_1-STAGE072-P2"
SUCCESSOR_NEXT_GATE072_P2 = "IDS-STAGE072-P3-GATE"
SUCCESSOR_PHASE072_P3 = "IDS-STAGE072-P3"
SUCCESSOR_TASK072_P3 = "IDS-V0_1-STAGE072-P3"
SUCCESSOR_NEXT_GATE072_P3 = "IDS-STAGE072-P4-GATE"
SUCCESSOR_PHASE072_P4 = "IDS-STAGE072-P4"
SUCCESSOR_TASK072_P4 = "IDS-V0_1-STAGE072-P4"
SUCCESSOR_NEXT_GATE072_P4 = "IDS-STAGE072-REVIEW-GATE"
SUCCESSOR_PHASE072_REVIEW = "IDS-STAGE072-REVIEW"
SUCCESSOR_TASK072_REVIEW = "IDS-V0_1-STAGE072-REVIEW"
SUCCESSOR_NEXT_GATE072_REVIEW = "IDS-STAGE073-P1-GATE"
RESULT = "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED"
CONTRACT_SCHEMA = "ids.v0_1.batch051_060.review_contract.v1"
EXPECTED_STAGE_IDS = [f"STAGE-{number:03d}" for number in range(51, 61)]
EXPECTED_ACCEPTANCE_IDS = [f"ACC-STAGE-{number:03d}" for number in range(51, 61)]
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
EXPECTED_INTERFACE_CHAIN = [
    "STAGE-051 OCR queue baseline -> STAGE-052 bilingual OCR contract",
    "STAGE-052 bilingual OCR contract -> STAGE-053 per-page OCR output",
    "STAGE-053 per-page OCR output -> STAGE-054 low-confidence review route",
    "STAGE-054 low-confidence review route -> STAGE-055 OCR regression corpus",
    "STAGE-055 OCR regression corpus -> STAGE-056 OCR cache retention policy",
    "STAGE-056 OCR cache retention policy -> STAGE-057 XLSX/CSV ingestion contract",
    "STAGE-057 XLSX/CSV ingestion contract -> STAGE-058 table schema inference",
    "STAGE-058 table schema inference -> STAGE-059 fact extraction baseline",
    "STAGE-059 fact extraction baseline -> STAGE-060 table-to-RAG summary",
]
EXPECTED_TRUTH = {
    "taskpack_context_read_performed": True,
    "prior_stage_review_evidence_read_performed": True,
    "second_authoritative_source_created": False,
    "ids_business_source_read_performed": False,
    "raw_metadata_content_accessed": False,
    "source_file_open_performed": False,
    "ocr_engine_invocation_performed": False,
    "xlsx_or_csv_parse_performed": False,
    "parser_execution_performed": False,
    "quality_gate_evaluation_performed": False,
    "persistent_state_write_performed": False,
    "agent_execution_performed": False,
    "model_call_performed": False,
    "model_token_consumption_performed": False,
    "ovh_deployment_performed": False,
    "production_runtime_activation_performed": False,
    "stage061_started": False,
    "batch_upload_gate_started": False,
    "github_upload_performed": False,
    "push_performed": False,
    "app_reinstall_performed": False,
}


def load_contract() -> dict[str, Any]:
    return _load_json(CONTRACT_PATH)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _contract_shape_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    stages = contract.get("stage_reviews")
    cross = contract.get("cross_stage_contract")
    gate = contract.get("governance_gate")
    truth = contract.get("truth_contract")
    return {
        "top_level_keys_exact": set(contract) == EXPECTED_CONTRACT_KEYS,
        "identity_exact": (
            contract.get("schema_version") == CONTRACT_SCHEMA
            and contract.get("batch_id") == "IDS-V0_1-BATCH-051-060"
            and contract.get("task_id") == TASK_ID
            and contract.get("stage_range") == "STAGE-051..STAGE-060"
            and contract.get("acceptance_range") == "ACC-STAGE-051..ACC-STAGE-060"
            and contract.get("authority_context")
            == "FROZEN_IDS_V0_1_TASKPACK_AND_EXISTING_STAGE_REVIEW_EVIDENCE"
            and contract.get("second_authoritative_source_created") is False
        ),
        "stage_matrix_exact": (
            isinstance(stages, list)
            and [item.get("stage_id") for item in stages if isinstance(item, dict)]
            == EXPECTED_STAGE_IDS
            and [item.get("acceptance_id") for item in stages if isinstance(item, dict)]
            == EXPECTED_ACCEPTANCE_IDS
            and all(isinstance(item, dict) and set(item) == EXPECTED_STAGE_REVIEW_KEYS for item in stages)
        ),
        "cross_stage_contract_exact": (
            isinstance(cross, dict)
            and cross
            == {
                "interface_chain": EXPECTED_INTERFACE_CHAIN,
                "runtime_execution_allowed": False,
                "production_runtime_allowed": False,
                "stage061_started": False,
                "stage061_entry_gate": NEXT_GATE,
            }
        ),
        "governance_gate_exact": (
            isinstance(gate, dict)
            and gate
            == {
                "review_status": "batch051_060_reviewed_local_global_upload_locked",
                "reviewed_stage_count": 10,
                "current_gate": TASK_ID,
                "next_gate": NEXT_GATE,
                "push_allowed": False,
                "github_upload_allowed": False,
                "batch_upload_gate_deferred": "IDS-V0_1-BATCH-051-060-UPLOAD-GATE",
                "global_release_acceptance_required": "ACC-STAGE-168",
                "app_reinstall_allowed": False,
            }
        ),
        "finding_list_exact": contract.get("findings") == [],
        "truth_contract_exact": isinstance(truth, dict) and truth == EXPECTED_TRUTH,
    }


def _artifact_checks(contract: Mapping[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for item in contract.get("stage_reviews", []):
        if not isinstance(item, dict):
            continue
        stage_id = str(item.get("stage_id", "UNKNOWN"))
        checks[stage_id] = all(
            isinstance(item.get(field), str)
            and (REPO_ROOT / item[field]).is_file()
            for field in (
                "taskpack_ref",
                "review_artifact_ref",
                "checker_ref",
                "test_ref",
                "machine_run_ref",
            )
        )
    checks["batch_contract"] = CONTRACT_PATH.is_file()
    checks["batch_document"] = (PURSUE_ROOT / "BATCH051_060_REVIEW_GATE.md").is_file()
    checks["batch_checker"] = Path(__file__).is_file()
    checks["batch_machine_run"] = BATCH_RUN_PATH.is_file()
    return checks


def _stage_checks(
    contract: Mapping[str, Any], batch: Mapping[str, Any], overrides: Mapping[str, bool] | None
) -> dict[str, bool]:
    progress = batch.get("stage_progress")
    progress = progress if isinstance(progress, dict) else {}
    checks: dict[str, bool] = {}
    for item in contract.get("stage_reviews", []):
        if not isinstance(item, dict):
            continue
        stage_id = str(item.get("stage_id"))
        stage = progress.get(stage_id)
        normal = isinstance(stage, dict) and (
            stage.get("status") == item.get("expected_status")
            and stage.get("current_task_id") == item.get("review_task_id")
            and stage.get("review_status") in ("passed", None)
            and stage.get("whole_stage_review_performed") is True
            and stage.get("batch_review_performed") is True
            and stage.get("batch_review_contract_schema") == CONTRACT_SCHEMA
            and stage.get("batch_review_valid") is True
            and stage.get("batch_review_result") == RESULT
            and stage.get("github_upload_allowed") is False
            and stage.get("push_allowed") is False
            and stage.get("ovh_deployment_performed") is False
            and stage.get("production_runtime_activation_performed") is False
            and stage.get("agent_execution_performed") is False
            and stage.get("model_call_performed") is False
            and stage.get("model_token_consumption_performed") is False
        )
        checks[stage_id] = bool(overrides.get(stage_id, normal) if overrides else normal)
    return checks


def _governance_checks(batch: Mapping[str, Any], roadmap: Mapping[str, Any]) -> dict[str, bool]:
    transitions = batch.get("transition_history")
    decision = batch.get("decision")
    progress = batch.get("stage_progress")
    transitions = transitions if isinstance(transitions, dict) else {}
    decision = decision if isinstance(decision, dict) else {}
    progress = progress if isinstance(progress, dict) else {}
    stage060 = progress.get("STAGE-060")
    stage060 = stage060 if isinstance(stage060, dict) else {}
    phase = roadmap.get("current_phase_id")
    task = roadmap.get("current_task_id")
    return {
        "batch_top_state": (
            batch.get("status") == "batch051_060_reviewed_local_global_upload_locked"
            and batch.get("review_task_id") == TASK_ID
            and batch.get("review_evidence_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/BATCH051_060_REVIEW_GATE.md"
            and batch.get("review_contract_ref")
            == "KM_IDSystem/docs/pursuing_goal/ids_v0_1/batch_review/stage051_060_batch_review_contract.json"
        ),
        "transition_exact": transitions.get("batch051_060_review_state")
        == {
            "status": "batch051_060_reviewed_local_global_upload_locked",
            "current_task_id": TASK_ID,
            "next_gate": NEXT_GATE,
            "next_allowed_task_id": NEXT_TASK,
            "stage061_entry_authorized": False,
            "github_upload_allowed": False,
        },
        "decision_exact": (
            decision.get("current_task_id") == TASK_ID
            and decision.get("next_allowed_task_id") == NEXT_TASK
            and decision.get("github_upload_allowed") is False
            and decision.get("push_allowed") is False
            and decision.get("global_upload_deferred") is True
        ),
        "roadmap_current_route_exact": (
            (
                roadmap.get("current_stage_id") == "IDS-STAGE060"
                and phase == TASK_ID
                and task == TASK_ID
                and roadmap.get("next_gate_id") == NEXT_GATE
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("batch051_060_review_state")
                == {
                    "current_stage_id": "IDS-STAGE060",
                    "current_phase_id": TASK_ID,
                    "current_task_id": TASK_ID,
                    "next_gate_id": NEXT_GATE,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and phase == SUCCESSOR_PHASE
                and task == SUCCESSOR_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage061_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE,
                    "current_phase_id": SUCCESSOR_PHASE,
                    "current_task_id": SUCCESSOR_TASK,
                    "next_gate_id": SUCCESSOR_NEXT_GATE,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and phase == SUCCESSOR_PHASE2
                and task == SUCCESSOR_TASK2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage061_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE,
                    "current_phase_id": SUCCESSOR_PHASE2,
                    "current_task_id": SUCCESSOR_TASK2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and phase == SUCCESSOR_PHASE3
                and task == SUCCESSOR_TASK3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage061_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE,
                    "current_phase_id": SUCCESSOR_PHASE3,
                    "current_task_id": SUCCESSOR_TASK3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and phase == SUCCESSOR_PHASE4
                and task == SUCCESSOR_TASK4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage061_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE,
                    "current_phase_id": SUCCESSOR_PHASE4,
                    "current_task_id": SUCCESSOR_TASK4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE
                and phase == SUCCESSOR_REVIEW
                and task == SUCCESSOR_REVIEW_TASK
                and roadmap.get("next_gate_id") == SUCCESSOR_REVIEW_NEXT_GATE
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage061_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE,
                    "current_phase_id": SUCCESSOR_REVIEW,
                    "current_task_id": SUCCESSOR_REVIEW_TASK,
                    "next_gate_id": SUCCESSOR_REVIEW_NEXT_GATE,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and phase == SUCCESSOR_PHASE062
                and task == SUCCESSOR_TASK062
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage062_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE062,
                    "current_phase_id": SUCCESSOR_PHASE062,
                    "current_task_id": SUCCESSOR_TASK062,
                    "next_gate_id": SUCCESSOR_NEXT_GATE062,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and phase == SUCCESSOR_PHASE062_P2
                and task == SUCCESSOR_TASK062_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage062_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE062,
                    "current_phase_id": SUCCESSOR_PHASE062_P2,
                    "current_task_id": SUCCESSOR_TASK062_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE062_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and phase == SUCCESSOR_PHASE062_P3
                and task == SUCCESSOR_TASK062_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage062_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE062,
                    "current_phase_id": SUCCESSOR_PHASE062_P3,
                    "current_task_id": SUCCESSOR_TASK062_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE062_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and phase == SUCCESSOR_PHASE062_P4
                and task == SUCCESSOR_TASK062_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage062_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE062,
                    "current_phase_id": SUCCESSOR_PHASE062_P4,
                    "current_task_id": SUCCESSOR_TASK062_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE062_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE062
                and phase == SUCCESSOR_PHASE062_REVIEW
                and task == SUCCESSOR_TASK062_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE062_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage062_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE062,
                    "current_phase_id": SUCCESSOR_PHASE062_REVIEW,
                    "current_task_id": SUCCESSOR_TASK062_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE062_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and phase == SUCCESSOR_PHASE063
                and task == SUCCESSOR_TASK063
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage063_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE063,
                    "current_phase_id": SUCCESSOR_PHASE063,
                    "current_task_id": SUCCESSOR_TASK063,
                    "next_gate_id": SUCCESSOR_NEXT_GATE063,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and phase == SUCCESSOR_PHASE063_P2
                and task == SUCCESSOR_TASK063_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage063_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE063,
                    "current_phase_id": SUCCESSOR_PHASE063_P2,
                    "current_task_id": SUCCESSOR_TASK063_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE063_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and phase == SUCCESSOR_PHASE063_P3
                and task == SUCCESSOR_TASK063_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage063_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE063,
                    "current_phase_id": SUCCESSOR_PHASE063_P3,
                    "current_task_id": SUCCESSOR_TASK063_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE063_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and phase == SUCCESSOR_PHASE063_P4
                and task == SUCCESSOR_TASK063_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage063_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE063,
                    "current_phase_id": SUCCESSOR_PHASE063_P4,
                    "current_task_id": SUCCESSOR_TASK063_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE063_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE063
                and phase == SUCCESSOR_PHASE063_REVIEW
                and task == SUCCESSOR_TASK063_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE063_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage063_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE063,
                    "current_phase_id": SUCCESSOR_PHASE063_REVIEW,
                    "current_task_id": SUCCESSOR_TASK063_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE063_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and phase == SUCCESSOR_PHASE064
                and task == SUCCESSOR_TASK064
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage064_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE064,
                    "current_phase_id": SUCCESSOR_PHASE064,
                    "current_task_id": SUCCESSOR_TASK064,
                    "next_gate_id": SUCCESSOR_NEXT_GATE064,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and phase == SUCCESSOR_PHASE064_P2
                and task == SUCCESSOR_TASK064_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage064_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE064,
                    "current_phase_id": SUCCESSOR_PHASE064_P2,
                    "current_task_id": SUCCESSOR_TASK064_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE064_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and phase == SUCCESSOR_PHASE064_P3
                and task == SUCCESSOR_TASK064_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage064_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE064,
                    "current_phase_id": SUCCESSOR_PHASE064_P3,
                    "current_task_id": SUCCESSOR_TASK064_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE064_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and phase == SUCCESSOR_PHASE064_P4
                and task == SUCCESSOR_TASK064_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage064_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE064,
                    "current_phase_id": SUCCESSOR_PHASE064_P4,
                    "current_task_id": SUCCESSOR_TASK064_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE064_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE064
                and phase == SUCCESSOR_PHASE064_REVIEW
                and task == SUCCESSOR_TASK064_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE064_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage064_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE064,
                    "current_phase_id": SUCCESSOR_PHASE064_REVIEW,
                    "current_task_id": SUCCESSOR_TASK064_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE064_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and phase == SUCCESSOR_PHASE065
                and task == SUCCESSOR_TASK065
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage065_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE065,
                    "current_phase_id": SUCCESSOR_PHASE065,
                    "current_task_id": SUCCESSOR_TASK065,
                    "next_gate_id": SUCCESSOR_NEXT_GATE065,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and phase == SUCCESSOR_PHASE065_P2
                and task == SUCCESSOR_TASK065_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage065_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE065,
                    "current_phase_id": SUCCESSOR_PHASE065_P2,
                    "current_task_id": SUCCESSOR_TASK065_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE065_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and phase == SUCCESSOR_PHASE065_P3
                and task == SUCCESSOR_TASK065_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage065_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE065,
                    "current_phase_id": SUCCESSOR_PHASE065_P3,
                    "current_task_id": SUCCESSOR_TASK065_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE065_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and phase == SUCCESSOR_PHASE065_P4
                and task == SUCCESSOR_TASK065_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage065_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE065,
                    "current_phase_id": SUCCESSOR_PHASE065_P4,
                    "current_task_id": SUCCESSOR_TASK065_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE065_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE065
                and phase == SUCCESSOR_PHASE065_REVIEW
                and task == SUCCESSOR_TASK065_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE065_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage065_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE065,
                    "current_phase_id": SUCCESSOR_PHASE065_REVIEW,
                    "current_task_id": SUCCESSOR_TASK065_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE065_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and phase == SUCCESSOR_PHASE066
                and task == SUCCESSOR_TASK066
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage066_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE066,
                    "current_phase_id": SUCCESSOR_PHASE066,
                    "current_task_id": SUCCESSOR_TASK066,
                    "next_gate_id": SUCCESSOR_NEXT_GATE066,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and phase == SUCCESSOR_PHASE066_P2
                and task == SUCCESSOR_TASK066_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage066_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE066,
                    "current_phase_id": SUCCESSOR_PHASE066_P2,
                    "current_task_id": SUCCESSOR_TASK066_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE066_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and phase == SUCCESSOR_PHASE066_P3
                and task == SUCCESSOR_TASK066_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage066_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE066,
                    "current_phase_id": SUCCESSOR_PHASE066_P3,
                    "current_task_id": SUCCESSOR_TASK066_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE066_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and phase == SUCCESSOR_PHASE066_P4
                and task == SUCCESSOR_TASK066_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage066_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE066,
                    "current_phase_id": SUCCESSOR_PHASE066_P4,
                    "current_task_id": SUCCESSOR_TASK066_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE066_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE066
                and phase == SUCCESSOR_PHASE066_REVIEW
                and task == SUCCESSOR_TASK066_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE066_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage066_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE066,
                    "current_phase_id": SUCCESSOR_PHASE066_REVIEW,
                    "current_task_id": SUCCESSOR_TASK066_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE066_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and phase == SUCCESSOR_PHASE067
                and task == SUCCESSOR_TASK067
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage067_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE067,
                    "current_phase_id": SUCCESSOR_PHASE067,
                    "current_task_id": SUCCESSOR_TASK067,
                    "next_gate_id": SUCCESSOR_NEXT_GATE067,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and phase == SUCCESSOR_PHASE067_P2
                and task == SUCCESSOR_TASK067_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage067_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE067,
                    "current_phase_id": SUCCESSOR_PHASE067_P2,
                    "current_task_id": SUCCESSOR_TASK067_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE067_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and phase == SUCCESSOR_PHASE067_P3
                and task == SUCCESSOR_TASK067_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage067_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE067,
                    "current_phase_id": SUCCESSOR_PHASE067_P3,
                    "current_task_id": SUCCESSOR_TASK067_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE067_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and phase == SUCCESSOR_PHASE067_P4
                and task == SUCCESSOR_TASK067_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage067_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE067,
                    "current_phase_id": SUCCESSOR_PHASE067_P4,
                    "current_task_id": SUCCESSOR_TASK067_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE067_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE067
                and phase == SUCCESSOR_PHASE067_REVIEW
                and task == SUCCESSOR_TASK067_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE067_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage067_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE067,
                    "current_phase_id": SUCCESSOR_PHASE067_REVIEW,
                    "current_task_id": SUCCESSOR_TASK067_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE067_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and phase == SUCCESSOR_PHASE068
                and task == SUCCESSOR_TASK068
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage068_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE068,
                    "current_phase_id": SUCCESSOR_PHASE068,
                    "current_task_id": SUCCESSOR_TASK068,
                    "next_gate_id": SUCCESSOR_NEXT_GATE068,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and phase == SUCCESSOR_PHASE068_P2
                and task == SUCCESSOR_TASK068_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage068_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE068,
                    "current_phase_id": SUCCESSOR_PHASE068_P2,
                    "current_task_id": SUCCESSOR_TASK068_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE068_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and phase == SUCCESSOR_PHASE068_P3
                and task == SUCCESSOR_TASK068_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage068_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE068,
                    "current_phase_id": SUCCESSOR_PHASE068_P3,
                    "current_task_id": SUCCESSOR_TASK068_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE068_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and phase == SUCCESSOR_PHASE068_P4
                and task == SUCCESSOR_TASK068_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage068_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE068,
                    "current_phase_id": SUCCESSOR_PHASE068_P4,
                    "current_task_id": SUCCESSOR_TASK068_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE068_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE068
                and phase == SUCCESSOR_PHASE068_REVIEW
                and task == SUCCESSOR_TASK068_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE068_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage068_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE068,
                    "current_phase_id": SUCCESSOR_PHASE068_REVIEW,
                    "current_task_id": SUCCESSOR_TASK068_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE068_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and phase == SUCCESSOR_PHASE069
                and task == SUCCESSOR_TASK069
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage069_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE069,
                    "current_phase_id": SUCCESSOR_PHASE069,
                    "current_task_id": SUCCESSOR_TASK069,
                    "next_gate_id": SUCCESSOR_NEXT_GATE069,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and phase == SUCCESSOR_PHASE069_P2
                and task == SUCCESSOR_TASK069_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage069_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE069,
                    "current_phase_id": SUCCESSOR_PHASE069_P2,
                    "current_task_id": SUCCESSOR_TASK069_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE069_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and phase == SUCCESSOR_PHASE069_P3
                and task == SUCCESSOR_TASK069_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage069_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE069,
                    "current_phase_id": SUCCESSOR_PHASE069_P3,
                    "current_task_id": SUCCESSOR_TASK069_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE069_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and phase == SUCCESSOR_PHASE069_P4
                and task == SUCCESSOR_TASK069_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage069_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE069,
                    "current_phase_id": SUCCESSOR_PHASE069_P4,
                    "current_task_id": SUCCESSOR_TASK069_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE069_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE069
                and phase == SUCCESSOR_PHASE069_REVIEW
                and task == SUCCESSOR_TASK069_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE069_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage069_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE069,
                    "current_phase_id": SUCCESSOR_PHASE069_REVIEW,
                    "current_task_id": SUCCESSOR_TASK069_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE069_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and phase == SUCCESSOR_PHASE070
                and task == SUCCESSOR_TASK070
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage070_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE070,
                    "current_phase_id": SUCCESSOR_PHASE070,
                    "current_task_id": SUCCESSOR_TASK070,
                    "next_gate_id": SUCCESSOR_NEXT_GATE070,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and phase == SUCCESSOR_PHASE070_P2
                and task == SUCCESSOR_TASK070_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage070_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE070,
                    "current_phase_id": SUCCESSOR_PHASE070_P2,
                    "current_task_id": SUCCESSOR_TASK070_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE070_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and phase == SUCCESSOR_PHASE070_P3
                and task == SUCCESSOR_TASK070_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage070_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE070,
                    "current_phase_id": SUCCESSOR_PHASE070_P3,
                    "current_task_id": SUCCESSOR_TASK070_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE070_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and phase == SUCCESSOR_PHASE070_P4
                and task == SUCCESSOR_TASK070_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage070_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE070,
                    "current_phase_id": SUCCESSOR_PHASE070_P4,
                    "current_task_id": SUCCESSOR_TASK070_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE070_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE070
                and phase == SUCCESSOR_PHASE070_REVIEW
                and task == SUCCESSOR_TASK070_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE070_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage070_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE070,
                    "current_phase_id": SUCCESSOR_PHASE070_REVIEW,
                    "current_task_id": SUCCESSOR_TASK070_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE070_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and phase == SUCCESSOR_PHASE071
                and task == SUCCESSOR_TASK071
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage071_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE071,
                    "current_phase_id": SUCCESSOR_PHASE071,
                    "current_task_id": SUCCESSOR_TASK071,
                    "next_gate_id": SUCCESSOR_NEXT_GATE071,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and phase == SUCCESSOR_PHASE071_P2
                and task == SUCCESSOR_TASK071_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage071_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE071,
                    "current_phase_id": SUCCESSOR_PHASE071_P2,
                    "current_task_id": SUCCESSOR_TASK071_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE071_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and phase == SUCCESSOR_PHASE071_P3
                and task == SUCCESSOR_TASK071_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage071_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE071,
                    "current_phase_id": SUCCESSOR_PHASE071_P3,
                    "current_task_id": SUCCESSOR_TASK071_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE071_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and phase == SUCCESSOR_PHASE071_P4
                and task == SUCCESSOR_TASK071_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage071_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE071,
                    "current_phase_id": SUCCESSOR_PHASE071_P4,
                    "current_task_id": SUCCESSOR_TASK071_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE071_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE071
                and phase == SUCCESSOR_PHASE071_REVIEW
                and task == SUCCESSOR_TASK071_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE071_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage071_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE071,
                    "current_phase_id": SUCCESSOR_PHASE071_REVIEW,
                    "current_task_id": SUCCESSOR_TASK071_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE071_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and phase == SUCCESSOR_PHASE072_P1
                and task == SUCCESSOR_TASK072_P1
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P1
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage072_phase1_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE072,
                    "current_phase_id": SUCCESSOR_PHASE072_P1,
                    "current_task_id": SUCCESSOR_TASK072_P1,
                    "next_gate_id": SUCCESSOR_NEXT_GATE072_P1,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and phase == SUCCESSOR_PHASE072_P2
                and task == SUCCESSOR_TASK072_P2
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P2
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage072_phase2_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE072,
                    "current_phase_id": SUCCESSOR_PHASE072_P2,
                    "current_task_id": SUCCESSOR_TASK072_P2,
                    "next_gate_id": SUCCESSOR_NEXT_GATE072_P2,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and phase == SUCCESSOR_PHASE072_P3
                and task == SUCCESSOR_TASK072_P3
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P3
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage072_phase3_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE072,
                    "current_phase_id": SUCCESSOR_PHASE072_P3,
                    "current_task_id": SUCCESSOR_TASK072_P3,
                    "next_gate_id": SUCCESSOR_NEXT_GATE072_P3,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and phase == SUCCESSOR_PHASE072_P4
                and task == SUCCESSOR_TASK072_P4
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_P4
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage072_phase4_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE072,
                    "current_phase_id": SUCCESSOR_PHASE072_P4,
                    "current_task_id": SUCCESSOR_TASK072_P4,
                    "next_gate_id": SUCCESSOR_NEXT_GATE072_P4,
                }
            )
            or (
                roadmap.get("current_stage_id") == SUCCESSOR_STAGE072
                and phase == SUCCESSOR_PHASE072_REVIEW
                and task == SUCCESSOR_TASK072_REVIEW
                and roadmap.get("next_gate_id") == SUCCESSOR_NEXT_GATE072_REVIEW
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage072_review_state")
                == {
                    "current_stage_id": SUCCESSOR_STAGE072,
                    "current_phase_id": SUCCESSOR_PHASE072_REVIEW,
                    "current_task_id": SUCCESSOR_TASK072_REVIEW,
                    "next_gate_id": SUCCESSOR_NEXT_GATE072_REVIEW,
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P1",
                    "current_task_id": "IDS-V0_1-STAGE073-P1",
                    "next_gate_id": "IDS-STAGE073-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P2",
                    "current_task_id": "IDS-V0_1-STAGE073-P2",
                    "next_gate_id": "IDS-STAGE073-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P3",
                    "current_task_id": "IDS-V0_1-STAGE073-P3",
                    "next_gate_id": "IDS-STAGE073-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE073-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-P4",
                    "current_task_id": "IDS-V0_1-STAGE073-P4",
                    "next_gate_id": "IDS-STAGE073-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE073"
                and roadmap.get("current_phase_id") == "IDS-STAGE073-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE073-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage073_review_state")
                == {
                    "current_stage_id": "IDS-STAGE073",
                    "current_phase_id": "IDS-STAGE073-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE073-REVIEW",
                    "next_gate_id": "IDS-STAGE074-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P1",
                    "current_task_id": "IDS-V0_1-STAGE074-P1",
                    "next_gate_id": "IDS-STAGE074-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P2",
                    "current_task_id": "IDS-V0_1-STAGE074-P2",
                    "next_gate_id": "IDS-STAGE074-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P3",
                    "current_task_id": "IDS-V0_1-STAGE074-P3",
                    "next_gate_id": "IDS-STAGE074-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE074-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-P4",
                    "current_task_id": "IDS-V0_1-STAGE074-P4",
                    "next_gate_id": "IDS-STAGE074-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE074"
                and roadmap.get("current_phase_id") == "IDS-STAGE074-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE074-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage074_review_state")
                == {
                    "current_stage_id": "IDS-STAGE074",
                    "current_phase_id": "IDS-STAGE074-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE074-REVIEW",
                    "next_gate_id": "IDS-STAGE075-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P1",
                    "current_task_id": "IDS-V0_1-STAGE075-P1",
                    "next_gate_id": "IDS-STAGE075-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P2",
                    "current_task_id": "IDS-V0_1-STAGE075-P2",
                    "next_gate_id": "IDS-STAGE075-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P3",
                    "current_task_id": "IDS-V0_1-STAGE075-P3",
                    "next_gate_id": "IDS-STAGE075-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE075-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-P4",
                    "current_task_id": "IDS-V0_1-STAGE075-P4",
                    "next_gate_id": "IDS-STAGE075-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE075"
                and roadmap.get("current_phase_id") == "IDS-STAGE075-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE075-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage075_review_state")
                == {
                    "current_stage_id": "IDS-STAGE075",
                    "current_phase_id": "IDS-STAGE075-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE075-REVIEW",
                    "next_gate_id": "IDS-STAGE076-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P1",
                    "current_task_id": "IDS-V0_1-STAGE076-P1",
                    "next_gate_id": "IDS-STAGE076-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P2",
                    "current_task_id": "IDS-V0_1-STAGE076-P2",
                    "next_gate_id": "IDS-STAGE076-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P3",
                    "current_task_id": "IDS-V0_1-STAGE076-P3",
                    "next_gate_id": "IDS-STAGE076-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE076-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-P4",
                    "current_task_id": "IDS-V0_1-STAGE076-P4",
                    "next_gate_id": "IDS-STAGE076-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE076"
                and roadmap.get("current_phase_id") == "IDS-STAGE076-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE076-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage076_review_state")
                == {
                    "current_stage_id": "IDS-STAGE076",
                    "current_phase_id": "IDS-STAGE076-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE076-REVIEW",
                    "next_gate_id": "IDS-STAGE077-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P1",
                    "current_task_id": "IDS-V0_1-STAGE077-P1",
                    "next_gate_id": "IDS-STAGE077-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P2",
                    "current_task_id": "IDS-V0_1-STAGE077-P2",
                    "next_gate_id": "IDS-STAGE077-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P3",
                    "current_task_id": "IDS-V0_1-STAGE077-P3",
                    "next_gate_id": "IDS-STAGE077-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE077-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-P4",
                    "current_task_id": "IDS-V0_1-STAGE077-P4",
                    "next_gate_id": "IDS-STAGE077-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE077"
                and roadmap.get("current_phase_id") == "IDS-STAGE077-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE077-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage077_review_state")
                == {
                    "current_stage_id": "IDS-STAGE077",
                    "current_phase_id": "IDS-STAGE077-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE077-REVIEW",
                    "next_gate_id": "IDS-STAGE078-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P1",
                    "current_task_id": "IDS-V0_1-STAGE078-P1",
                    "next_gate_id": "IDS-STAGE078-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P2",
                    "current_task_id": "IDS-V0_1-STAGE078-P2",
                    "next_gate_id": "IDS-STAGE078-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P3",
                    "current_task_id": "IDS-V0_1-STAGE078-P3",
                    "next_gate_id": "IDS-STAGE078-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE078-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-P4",
                    "current_task_id": "IDS-V0_1-STAGE078-P4",
                    "next_gate_id": "IDS-STAGE078-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE078"
                and roadmap.get("current_phase_id") == "IDS-STAGE078-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE078-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage078_review_state")
                == {
                    "current_stage_id": "IDS-STAGE078",
                    "current_phase_id": "IDS-STAGE078-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE078-REVIEW",
                    "next_gate_id": "IDS-STAGE079-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P1",
                    "current_task_id": "IDS-V0_1-STAGE079-P1",
                    "next_gate_id": "IDS-STAGE079-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P2",
                    "current_task_id": "IDS-V0_1-STAGE079-P2",
                    "next_gate_id": "IDS-STAGE079-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P3",
                    "current_task_id": "IDS-V0_1-STAGE079-P3",
                    "next_gate_id": "IDS-STAGE079-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE079-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-P4",
                    "current_task_id": "IDS-V0_1-STAGE079-P4",
                    "next_gate_id": "IDS-STAGE079-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE079"
                and roadmap.get("current_phase_id") == "IDS-STAGE079-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE079-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage079_review_state")
                == {
                    "current_stage_id": "IDS-STAGE079",
                    "current_phase_id": "IDS-STAGE079-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE079-REVIEW",
                    "next_gate_id": "IDS-STAGE080-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P1",
                    "current_task_id": "IDS-V0_1-STAGE080-P1",
                    "next_gate_id": "IDS-STAGE080-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P2",
                    "current_task_id": "IDS-V0_1-STAGE080-P2",
                    "next_gate_id": "IDS-STAGE080-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P3",
                    "current_task_id": "IDS-V0_1-STAGE080-P3",
                    "next_gate_id": "IDS-STAGE080-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE080-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-P4",
                    "current_task_id": "IDS-V0_1-STAGE080-P4",
                    "next_gate_id": "IDS-STAGE080-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE080"
                and roadmap.get("current_phase_id") == "IDS-STAGE080-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE080-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage080_review_state")
                == {
                    "current_stage_id": "IDS-STAGE080",
                    "current_phase_id": "IDS-STAGE080-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE080-REVIEW",
                    "next_gate_id": "IDS-STAGE081-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P1",
                    "current_task_id": "IDS-V0_1-STAGE081-P1",
                    "next_gate_id": "IDS-STAGE081-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P2",
                    "current_task_id": "IDS-V0_1-STAGE081-P2",
                    "next_gate_id": "IDS-STAGE081-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P3",
                    "current_task_id": "IDS-V0_1-STAGE081-P3",
                    "next_gate_id": "IDS-STAGE081-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE081-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-P4",
                    "current_task_id": "IDS-V0_1-STAGE081-P4",
                    "next_gate_id": "IDS-STAGE081-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE081"
                and roadmap.get("current_phase_id") == "IDS-STAGE081-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE081-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage081_review_state")
                == {
                    "current_stage_id": "IDS-STAGE081",
                    "current_phase_id": "IDS-STAGE081-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE081-REVIEW",
                    "next_gate_id": "IDS-STAGE082-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P1",
                    "current_task_id": "IDS-V0_1-STAGE082-P1",
                    "next_gate_id": "IDS-STAGE082-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P2",
                    "current_task_id": "IDS-V0_1-STAGE082-P2",
                    "next_gate_id": "IDS-STAGE082-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P3",
                    "current_task_id": "IDS-V0_1-STAGE082-P3",
                    "next_gate_id": "IDS-STAGE082-P4-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-P4"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-P4"
                and roadmap.get("next_gate_id") == "IDS-STAGE082-REVIEW-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_phase4_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-P4",
                    "current_task_id": "IDS-V0_1-STAGE082-P4",
                    "next_gate_id": "IDS-STAGE082-REVIEW-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE082"
                and roadmap.get("current_phase_id") == "IDS-STAGE082-REVIEW"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE082-REVIEW"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P1-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage082_review_state")
                == {
                    "current_stage_id": "IDS-STAGE082",
                    "current_phase_id": "IDS-STAGE082-REVIEW",
                    "current_task_id": "IDS-V0_1-STAGE082-REVIEW",
                    "next_gate_id": "IDS-STAGE083-P1-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P1"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P1"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P2-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase1_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P1",
                    "current_task_id": "IDS-V0_1-STAGE083-P1",
                    "next_gate_id": "IDS-STAGE083-P2-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P2"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P2"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P3-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase2_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P2",
                    "current_task_id": "IDS-V0_1-STAGE083-P2",
                    "next_gate_id": "IDS-STAGE083-P3-GATE",
                }
            )
            or (
                roadmap.get("current_stage_id") == "IDS-STAGE083"
                and roadmap.get("current_phase_id") == "IDS-STAGE083-P3"
                and roadmap.get("current_task_id") == "IDS-V0_1-STAGE083-P3"
                and roadmap.get("next_gate_id") == "IDS-STAGE083-P4-GATE"
                and isinstance(roadmap.get("current_transition_history"), dict)
                and roadmap["current_transition_history"].get("stage083_phase3_state")
                == {
                    "current_stage_id": "IDS-STAGE083",
                    "current_phase_id": "IDS-STAGE083-P3",
                    "current_task_id": "IDS-V0_1-STAGE083-P3",
                    "next_gate_id": "IDS-STAGE083-P4-GATE",
                }
            )
        ),
        "stage060_route_exact": (
            stage060.get("next_stage") == "STAGE-061"
            and stage060.get("next_phase") == "Stage061 Phase 1"
            and stage060.get("next_gate") == NEXT_GATE
            and stage060.get("stage061_started") is False
            and stage060.get("stage061_entry_authorized") is False
            and stage060.get("batch_upload_gate_started") is False
        ),
        "global_upload_locked": (
            isinstance(batch.get("upload_gate"), dict)
            and batch["upload_gate"].get("push_allowed") is False
            and batch["upload_gate"].get("github_upload_allowed") is False
            and batch["upload_gate"].get("global_release_acceptance_required") == "ACC-STAGE-168"
        ),
    }


def _projection_checks() -> dict[str, bool]:
    status = _load_json(STATUS_PATH)
    plan = _load_json(PLAN_PATH)
    fact_roadmap = json.loads(FACT_ROADMAP_PATH.read_text(encoding="utf-8"))
    acceptance = _load_json(ACCEPTANCE_PATH)
    stages = fact_roadmap.get("stages", []) if isinstance(fact_roadmap, dict) else []
    items = acceptance.get("items") if isinstance(acceptance, dict) else []
    acceptance_ids = {item.get("id") for item in items if isinstance(item, dict)}
    stage060 = next(
        (item for item in stages if isinstance(item, dict) and item.get("id") == "IDS-STAGE060"),
        {},
    )
    stage061 = next(
        (item for item in stages if isinstance(item, dict) and item.get("id") == SUCCESSOR_STAGE),
        {},
    )
    stage062 = next(
        (item for item in stages if isinstance(item, dict) and item.get("id") == SUCCESSOR_STAGE062),
        {},
    )
    stage063 = next(
        (item for item in stages if isinstance(item, dict) and item.get("id") == SUCCESSOR_STAGE063),
        {},
    )
    successor_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE
        and status.get("phase") == SUCCESSOR_TASK
        and status.get("task") == SUCCESSOR_TASK
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK
        and plan.get("task") == SUCCESSOR_TASK
        and SUCCESSOR_NEXT_GATE in str(plan.get("stop_condition", ""))
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
    successor_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK2
        and plan.get("task") == SUCCESSOR_TASK2
        and SUCCESSOR_NEXT_GATE2 in str(plan.get("stop_condition", ""))
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
    successor_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK3
        and plan.get("task") == SUCCESSOR_TASK3
        and SUCCESSOR_NEXT_GATE3 in str(plan.get("stop_condition", ""))
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
    successor_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_TASK4
        and plan.get("task") == SUCCESSOR_TASK4
        and SUCCESSOR_NEXT_GATE4 in str(plan.get("stop_condition", ""))
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
    successor_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE
        and plan.get("phase") == SUCCESSOR_REVIEW_TASK
        and plan.get("task") == SUCCESSOR_REVIEW_TASK
        and SUCCESSOR_REVIEW_NEXT_GATE in str(plan.get("stop_condition", ""))
    )
    successor_stage062_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062
        and status.get("task") == SUCCESSOR_TASK062
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P2
        and status.get("task") == SUCCESSOR_TASK062_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P3
        and status.get("task") == SUCCESSOR_TASK062_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_TASK062_P4
        and status.get("task") == SUCCESSOR_TASK062_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE062
        and status.get("phase") == SUCCESSOR_PHASE062_REVIEW
        and status.get("task") == SUCCESSOR_TASK062_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE062_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063
        and status.get("task") == SUCCESSOR_TASK063
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P2
        and status.get("task") == SUCCESSOR_TASK063_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P3
        and status.get("task") == SUCCESSOR_TASK063_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_P4
        and status.get("task") == SUCCESSOR_TASK063_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage063_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE063
        and status.get("phase") == SUCCESSOR_TASK063_REVIEW
        and status.get("task") == SUCCESSOR_TASK063_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE063_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064
        and status.get("task") == SUCCESSOR_TASK064
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P2
        and status.get("task") == SUCCESSOR_TASK064_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P3
        and status.get("task") == SUCCESSOR_TASK064_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_P4
        and status.get("task") == SUCCESSOR_TASK064_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage064_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE064
        and status.get("phase") == SUCCESSOR_TASK064_REVIEW
        and status.get("task") == SUCCESSOR_TASK064_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE064_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065
        and status.get("task") == SUCCESSOR_TASK065
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P2
        and status.get("task") == SUCCESSOR_TASK065_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P3
        and status.get("task") == SUCCESSOR_TASK065_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_P4
        and status.get("task") == SUCCESSOR_TASK065_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage065_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE065
        and status.get("phase") == SUCCESSOR_TASK065_REVIEW
        and status.get("task") == SUCCESSOR_TASK065_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE065_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066
        and status.get("task") == SUCCESSOR_TASK066
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P2
        and status.get("task") == SUCCESSOR_TASK066_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P3
        and status.get("task") == SUCCESSOR_TASK066_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_TASK066_P4
        and status.get("task") == SUCCESSOR_TASK066_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage066_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE066
        and status.get("phase") == SUCCESSOR_PHASE066_REVIEW
        and status.get("task") == SUCCESSOR_TASK066_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE066_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067
        and status.get("task") == SUCCESSOR_TASK067
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P2
        and status.get("task") == SUCCESSOR_TASK067_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P3
        and status.get("task") == SUCCESSOR_TASK067_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_P4
        and status.get("task") == SUCCESSOR_TASK067_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage067_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE067
        and status.get("phase") == SUCCESSOR_TASK067_REVIEW
        and status.get("task") == SUCCESSOR_TASK067_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE067_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068
        and status.get("task") == SUCCESSOR_TASK068
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P2
        and status.get("task") == SUCCESSOR_TASK068_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P3
        and status.get("task") == SUCCESSOR_TASK068_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_P4
        and status.get("task") == SUCCESSOR_TASK068_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage068_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE068
        and status.get("phase") == SUCCESSOR_TASK068_REVIEW
        and status.get("task") == SUCCESSOR_TASK068_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE068_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069
        and status.get("task") == SUCCESSOR_TASK069
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase2_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P2
        and status.get("task") == SUCCESSOR_TASK069_P2
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P2
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase3_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P3
        and status.get("task") == SUCCESSOR_TASK069_P3
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P3
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_phase4_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_P4
        and status.get("task") == SUCCESSOR_TASK069_P4
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_P4
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage069_review_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE069
        and status.get("phase") == SUCCESSOR_TASK069_REVIEW
        and status.get("task") == SUCCESSOR_TASK069_REVIEW
        and status.get("next_gate") == SUCCESSOR_NEXT_GATE069_REVIEW
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage070_phase1_status = (
        isinstance(status, dict)
        and status.get("stage") == SUCCESSOR_STAGE070
        and status.get("phase")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and status.get("task")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and status.get("next_gate")
        in (
            SUCCESSOR_NEXT_GATE070,
            SUCCESSOR_NEXT_GATE070_P2,
            SUCCESSOR_NEXT_GATE070_P3,
            SUCCESSOR_NEXT_GATE070_P4,
            SUCCESSOR_NEXT_GATE070_REVIEW,
        )
        and status.get("runtime_enabled") is False
        and status.get("push_allowed") is False
    )
    successor_stage062_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062
        and plan.get("task") == SUCCESSOR_TASK062
        and SUCCESSOR_NEXT_GATE062 in str(plan.get("stop_condition", ""))
    )
    successor_stage062_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P2
        and plan.get("task") == SUCCESSOR_TASK062_P2
        and SUCCESSOR_NEXT_GATE062_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage062_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P3
        and plan.get("task") == SUCCESSOR_TASK062_P3
        and SUCCESSOR_NEXT_GATE062_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage062_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_TASK062_P4
        and plan.get("task") == SUCCESSOR_TASK062_P4
        and SUCCESSOR_NEXT_GATE062_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage062_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE062
        and plan.get("phase") == SUCCESSOR_PHASE062_REVIEW
        and plan.get("task") == SUCCESSOR_TASK062_REVIEW
        and SUCCESSOR_NEXT_GATE062_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage063_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063
        and plan.get("task") == SUCCESSOR_TASK063
        and SUCCESSOR_NEXT_GATE063 in str(plan.get("stop_condition", ""))
    )
    successor_stage063_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P2
        and plan.get("task") == SUCCESSOR_TASK063_P2
        and SUCCESSOR_NEXT_GATE063_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage063_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P3
        and plan.get("task") == SUCCESSOR_TASK063_P3
        and SUCCESSOR_NEXT_GATE063_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage063_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_P4
        and plan.get("task") == SUCCESSOR_TASK063_P4
        and SUCCESSOR_NEXT_GATE063_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage063_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE063
        and plan.get("phase") == SUCCESSOR_TASK063_REVIEW
        and plan.get("task") == SUCCESSOR_TASK063_REVIEW
        and SUCCESSOR_NEXT_GATE063_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage064_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064
        and plan.get("task") == SUCCESSOR_TASK064
        and SUCCESSOR_NEXT_GATE064 in str(plan.get("stop_condition", ""))
    )
    successor_stage064_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P2
        and plan.get("task") == SUCCESSOR_TASK064_P2
        and SUCCESSOR_NEXT_GATE064_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage064_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P3
        and plan.get("task") == SUCCESSOR_TASK064_P3
        and SUCCESSOR_NEXT_GATE064_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage064_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_P4
        and plan.get("task") == SUCCESSOR_TASK064_P4
        and SUCCESSOR_NEXT_GATE064_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage064_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE064
        and plan.get("phase") == SUCCESSOR_TASK064_REVIEW
        and plan.get("task") == SUCCESSOR_TASK064_REVIEW
        and SUCCESSOR_NEXT_GATE064_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage065_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065
        and plan.get("task") == SUCCESSOR_TASK065
        and SUCCESSOR_NEXT_GATE065 in str(plan.get("stop_condition", ""))
    )
    successor_stage065_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P2
        and plan.get("task") == SUCCESSOR_TASK065_P2
        and SUCCESSOR_NEXT_GATE065_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage065_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P3
        and plan.get("task") == SUCCESSOR_TASK065_P3
        and SUCCESSOR_NEXT_GATE065_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage065_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_P4
        and plan.get("task") == SUCCESSOR_TASK065_P4
        and SUCCESSOR_NEXT_GATE065_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage065_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE065
        and plan.get("phase") == SUCCESSOR_TASK065_REVIEW
        and plan.get("task") == SUCCESSOR_TASK065_REVIEW
        and SUCCESSOR_NEXT_GATE065_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage066_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066
        and plan.get("task") == SUCCESSOR_TASK066
        and SUCCESSOR_NEXT_GATE066 in str(plan.get("stop_condition", ""))
    )
    successor_stage066_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P2
        and plan.get("task") == SUCCESSOR_TASK066_P2
        and SUCCESSOR_NEXT_GATE066_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage066_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P3
        and plan.get("task") == SUCCESSOR_TASK066_P3
        and SUCCESSOR_NEXT_GATE066_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage066_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_P4
        and plan.get("task") == SUCCESSOR_TASK066_P4
        and SUCCESSOR_NEXT_GATE066_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage066_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE066
        and plan.get("phase") == SUCCESSOR_TASK066_REVIEW
        and plan.get("task") == SUCCESSOR_TASK066_REVIEW
        and SUCCESSOR_NEXT_GATE066_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage067_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067
        and plan.get("task") == SUCCESSOR_TASK067
        and SUCCESSOR_NEXT_GATE067 in str(plan.get("stop_condition", ""))
    )
    successor_stage067_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P2
        and plan.get("task") == SUCCESSOR_TASK067_P2
        and SUCCESSOR_NEXT_GATE067_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage067_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P3
        and plan.get("task") == SUCCESSOR_TASK067_P3
        and SUCCESSOR_NEXT_GATE067_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage067_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_P4
        and plan.get("task") == SUCCESSOR_TASK067_P4
        and SUCCESSOR_NEXT_GATE067_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage067_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE067
        and plan.get("phase") == SUCCESSOR_TASK067_REVIEW
        and plan.get("task") == SUCCESSOR_TASK067_REVIEW
        and SUCCESSOR_NEXT_GATE067_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage068_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068
        and plan.get("task") == SUCCESSOR_TASK068
        and SUCCESSOR_NEXT_GATE068 in str(plan.get("stop_condition", ""))
    )
    successor_stage068_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P2
        and plan.get("task") == SUCCESSOR_TASK068_P2
        and SUCCESSOR_NEXT_GATE068_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage068_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P3
        and plan.get("task") == SUCCESSOR_TASK068_P3
        and SUCCESSOR_NEXT_GATE068_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage068_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_P4
        and plan.get("task") == SUCCESSOR_TASK068_P4
        and SUCCESSOR_NEXT_GATE068_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage068_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE068
        and plan.get("phase") == SUCCESSOR_TASK068_REVIEW
        and plan.get("task") == SUCCESSOR_TASK068_REVIEW
        and SUCCESSOR_NEXT_GATE068_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage069_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069
        and plan.get("task") == SUCCESSOR_TASK069
        and SUCCESSOR_NEXT_GATE069 in str(plan.get("stop_condition", ""))
    )
    successor_stage069_phase2_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P2
        and plan.get("task") == SUCCESSOR_TASK069_P2
        and SUCCESSOR_NEXT_GATE069_P2 in str(plan.get("stop_condition", ""))
    )
    successor_stage069_phase3_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P3
        and plan.get("task") == SUCCESSOR_TASK069_P3
        and SUCCESSOR_NEXT_GATE069_P3 in str(plan.get("stop_condition", ""))
    )
    successor_stage069_phase4_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_P4
        and plan.get("task") == SUCCESSOR_TASK069_P4
        and SUCCESSOR_NEXT_GATE069_P4 in str(plan.get("stop_condition", ""))
    )
    successor_stage069_review_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE069
        and plan.get("phase") == SUCCESSOR_TASK069_REVIEW
        and plan.get("task") == SUCCESSOR_TASK069_REVIEW
        and SUCCESSOR_NEXT_GATE069_REVIEW in str(plan.get("stop_condition", ""))
    )
    successor_stage070_phase1_plan = (
        isinstance(plan, dict)
        and plan.get("stage") == SUCCESSOR_STAGE070
        and plan.get("phase")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and plan.get("task")
        in (
            SUCCESSOR_TASK070,
            SUCCESSOR_TASK070_P2,
            SUCCESSOR_TASK070_P3,
            SUCCESSOR_TASK070_P4,
            SUCCESSOR_TASK070_REVIEW,
        )
        and (
            SUCCESSOR_NEXT_GATE070 in str(plan.get("stop_condition", ""))
            or SUCCESSOR_NEXT_GATE070_P2 in str(plan.get("stop_condition", ""))
            or SUCCESSOR_NEXT_GATE070_P3 in str(plan.get("stop_condition", ""))
            or SUCCESSOR_NEXT_GATE070_P4 in str(plan.get("stop_condition", ""))
            or SUCCESSOR_NEXT_GATE070_REVIEW in str(plan.get("stop_condition", ""))
        )
    )
    return {
        "status_projection": (
            successor_status
            or successor_phase2_status
            or successor_phase3_status
            or successor_phase4_status
            or successor_review_status
            or successor_stage062_status
            or successor_stage062_phase2_status
            or successor_stage062_phase3_status
            or successor_stage062_phase4_status
            or successor_stage062_review_status
            or successor_stage063_status
            or successor_stage063_phase2_status
            or successor_stage063_phase3_status
            or successor_stage063_phase4_status
            or successor_stage063_review_status
            or successor_stage064_phase1_status
            or successor_stage064_phase2_status
            or successor_stage064_phase3_status
            or successor_stage064_phase4_status
            or successor_stage064_review_status
            or successor_stage065_phase1_status
            or successor_stage065_phase2_status
            or successor_stage065_phase3_status
            or successor_stage065_phase4_status
            or successor_stage065_review_status
            or successor_stage066_phase1_status
            or successor_stage066_phase2_status
            or successor_stage066_phase3_status
            or successor_stage066_phase4_status
            or successor_stage066_review_status
            or successor_stage067_phase1_status
            or successor_stage067_phase2_status
            or successor_stage067_phase3_status
            or successor_stage067_phase4_status
            or successor_stage067_review_status
            or successor_stage068_phase1_status
            or successor_stage068_phase2_status
            or successor_stage068_phase3_status
            or successor_stage068_phase4_status
            or successor_stage068_review_status
            or successor_stage069_phase1_status
            or successor_stage069_phase2_status
            or successor_stage069_phase3_status
            or successor_stage069_phase4_status
            or successor_stage069_review_status
            or successor_stage070_phase1_status
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071
                and status.get("task") == SUCCESSOR_TASK071
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P1"
                and status.get("task") == "IDS-V0_1-STAGE075-P1"
                and status.get("next_gate") == "IDS-STAGE075-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE075-REVIEW"
                and status.get("next_gate") == "IDS-STAGE076-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P1"
                and status.get("task") == "IDS-V0_1-STAGE076-P1"
                and status.get("next_gate") == "IDS-STAGE076-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P1"
                and status.get("task") == "IDS-V0_1-STAGE077-P1"
                and status.get("next_gate") == "IDS-STAGE077-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P1"
                and status.get("task") == "IDS-V0_1-STAGE078-P1"
                and status.get("next_gate") == "IDS-STAGE078-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-STAGE078-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE078-REVIEW"
                and status.get("next_gate") == "IDS-STAGE079-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P4"
                and status.get("task") == "IDS-V0_1-STAGE078-P4"
                and status.get("next_gate") == "IDS-STAGE078-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P2"
                and status.get("task") == "IDS-V0_1-STAGE078-P2"
                and status.get("next_gate") == "IDS-STAGE078-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE078"
                and status.get("phase") == "IDS-V0_1-STAGE078-P3"
                and status.get("task") == "IDS-V0_1-STAGE078-P3"
                and status.get("next_gate") == "IDS-STAGE078-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P3"
                and status.get("task") == "IDS-V0_1-STAGE077-P3"
                and status.get("next_gate") == "IDS-STAGE077-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P4"
                and status.get("task") == "IDS-V0_1-STAGE077-P4"
                and status.get("next_gate") == "IDS-STAGE077-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE077-REVIEW"
                and status.get("next_gate") == "IDS-STAGE078-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE077"
                and status.get("phase") == "IDS-V0_1-STAGE077-P2"
                and status.get("task") == "IDS-V0_1-STAGE077-P2"
                and status.get("next_gate") == "IDS-STAGE077-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE076-REVIEW"
                and status.get("next_gate") == "IDS-STAGE077-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P3"
                and status.get("task") == "IDS-V0_1-STAGE076-P3"
                and status.get("next_gate") == "IDS-STAGE076-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P4"
                and status.get("task") == "IDS-V0_1-STAGE076-P4"
                and status.get("next_gate") == "IDS-STAGE076-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE076"
                and status.get("phase") == "IDS-V0_1-STAGE076-P2"
                and status.get("task") == "IDS-V0_1-STAGE076-P2"
                and status.get("next_gate") == "IDS-STAGE076-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P4"
                and status.get("task") == "IDS-V0_1-STAGE075-P4"
                and status.get("next_gate") == "IDS-STAGE075-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P3"
                and status.get("task") == "IDS-V0_1-STAGE075-P3"
                and status.get("next_gate") == "IDS-STAGE075-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE075"
                and status.get("phase") == "IDS-V0_1-STAGE075-P2"
                and status.get("task") == "IDS-V0_1-STAGE075-P2"
                and status.get("next_gate") == "IDS-STAGE075-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P2
                and status.get("task") == SUCCESSOR_TASK071_P2
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P2
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P3
                and status.get("task") == SUCCESSOR_TASK071_P3
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P3
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_P4
                and status.get("task") == SUCCESSOR_TASK071_P4
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_P4
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE071
                and status.get("phase") == SUCCESSOR_TASK071_REVIEW
                and status.get("task") == SUCCESSOR_TASK071_REVIEW
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE071_REVIEW
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P1
                and status.get("task") == SUCCESSOR_TASK072_P1
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P1
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_REVIEW
                and status.get("task") == SUCCESSOR_TASK072_REVIEW
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_REVIEW
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P2
                and status.get("task") == SUCCESSOR_TASK072_P2
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P2
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P3
                and status.get("task") == SUCCESSOR_TASK072_P3
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P3
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == SUCCESSOR_STAGE072
                and status.get("phase") == SUCCESSOR_TASK072_P4
                and status.get("task") == SUCCESSOR_TASK072_P4
                and status.get("next_gate") == SUCCESSOR_NEXT_GATE072_P4
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                status.get("stage") == "IDS-STAGE060"
                and status.get("phase") == TASK_ID
                and status.get("task") == TASK_ID
                and status.get("next_gate") == NEXT_GATE
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P1"
                and status.get("task") == "IDS-V0_1-STAGE073-P1"
                and status.get("next_gate") == "IDS-STAGE073-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P2"
                and status.get("task") == "IDS-V0_1-STAGE073-P2"
                and status.get("next_gate") == "IDS-STAGE073-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P3"
                and status.get("task") == "IDS-V0_1-STAGE073-P3"
                and status.get("next_gate") == "IDS-STAGE073-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-P4"
                and status.get("task") == "IDS-V0_1-STAGE073-P4"
                and status.get("next_gate") == "IDS-STAGE073-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE073"
                and status.get("phase") == "IDS-V0_1-STAGE073-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE073-REVIEW"
                and status.get("next_gate") == "IDS-STAGE074-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P1"
                and status.get("task") == "IDS-V0_1-STAGE074-P1"
                and status.get("next_gate") == "IDS-STAGE074-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P2"
                and status.get("task") == "IDS-V0_1-STAGE074-P2"
                and status.get("next_gate") == "IDS-STAGE074-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P3"
                and status.get("task") == "IDS-V0_1-STAGE074-P3"
                and status.get("next_gate") == "IDS-STAGE074-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-P4"
                and status.get("task") == "IDS-V0_1-STAGE074-P4"
                and status.get("next_gate") == "IDS-STAGE074-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE074"
                and status.get("phase") == "IDS-V0_1-STAGE074-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE074-REVIEW"
                and status.get("next_gate") == "IDS-STAGE075-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P1"
                and status.get("task") == "IDS-V0_1-STAGE079-P1"
                and status.get("next_gate") == "IDS-STAGE079-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P1"
                and status.get("task") == "IDS-V0_1-STAGE080-P1"
                and status.get("next_gate") == "IDS-STAGE080-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P4"
                and status.get("task") == "IDS-V0_1-STAGE080-P4"
                and status.get("next_gate") == "IDS-STAGE080-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-STAGE080-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE080-REVIEW"
                and status.get("next_gate") == "IDS-STAGE081-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P1"
                and status.get("task") == "IDS-V0_1-STAGE081-P1"
                and status.get("next_gate") == "IDS-STAGE081-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE081-REVIEW"
                and status.get("next_gate") == "IDS-STAGE082-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P1"
                and status.get("task") == "IDS-V0_1-STAGE082-P1"
                and status.get("next_gate") == "IDS-STAGE082-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P2"
                and status.get("task") == "IDS-V0_1-STAGE082-P2"
                and status.get("next_gate") == "IDS-STAGE082-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P3"
                and status.get("task") == "IDS-V0_1-STAGE082-P3"
                and status.get("next_gate") == "IDS-STAGE082-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-P4"
                and status.get("task") == "IDS-V0_1-STAGE082-P4"
                and status.get("next_gate") == "IDS-STAGE082-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE082"
                and status.get("phase") == "IDS-STAGE082-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE082-REVIEW"
                and status.get("next_gate") == "IDS-STAGE083-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P1"
                and status.get("task") == "IDS-V0_1-STAGE083-P1"
                and status.get("next_gate") == "IDS-STAGE083-P2-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P3"
                and status.get("task") == "IDS-V0_1-STAGE083-P3"
                and status.get("next_gate") == "IDS-STAGE083-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE083"
                and status.get("phase") == "IDS-STAGE083-P2"
                and status.get("task") == "IDS-V0_1-STAGE083-P2"
                and status.get("next_gate") == "IDS-STAGE083-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P3"
                and status.get("task") == "IDS-V0_1-STAGE081-P3"
                and status.get("next_gate") == "IDS-STAGE081-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P4"
                and status.get("task") == "IDS-V0_1-STAGE081-P4"
                and status.get("next_gate") == "IDS-STAGE081-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE081"
                and status.get("phase") == "IDS-STAGE081-P2"
                and status.get("task") == "IDS-V0_1-STAGE081-P2"
                and status.get("next_gate") == "IDS-STAGE081-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P2"
                and status.get("task") == "IDS-V0_1-STAGE080-P2"
                and status.get("next_gate") == "IDS-STAGE080-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE080"
                and status.get("phase") == "IDS-V0_1-STAGE080-P3"
                and status.get("task") == "IDS-V0_1-STAGE080-P3"
                and status.get("next_gate") == "IDS-STAGE080-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-STAGE079-REVIEW"
                and status.get("task") == "IDS-V0_1-STAGE079-REVIEW"
                and status.get("next_gate") == "IDS-STAGE080-P1-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P2"
                and status.get("task") == "IDS-V0_1-STAGE079-P2"
                and status.get("next_gate") == "IDS-STAGE079-P3-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P3"
                and status.get("task") == "IDS-V0_1-STAGE079-P3"
                and status.get("next_gate") == "IDS-STAGE079-P4-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
            or (
                isinstance(status, dict)
                and status.get("stage") == "IDS-STAGE079"
                and status.get("phase") == "IDS-V0_1-STAGE079-P4"
                and status.get("task") == "IDS-V0_1-STAGE079-P4"
                and status.get("next_gate") == "IDS-STAGE079-REVIEW-GATE"
                and status.get("runtime_enabled") is False
                and status.get("push_allowed") is False
            )
        ),
        "plan_projection": (
            successor_plan
            or successor_phase2_plan
            or successor_phase3_plan
            or successor_phase4_plan
            or successor_review_plan
            or successor_stage062_plan
            or successor_stage062_phase2_plan
            or successor_stage062_phase3_plan
            or successor_stage062_phase4_plan
            or successor_stage062_review_plan
            or successor_stage063_plan
            or successor_stage063_phase2_plan
            or successor_stage063_phase3_plan
            or successor_stage063_phase4_plan
            or successor_stage063_review_plan
            or successor_stage064_phase1_plan
            or successor_stage064_phase2_plan
            or successor_stage064_phase3_plan
            or successor_stage064_phase4_plan
            or successor_stage064_review_plan
            or successor_stage065_phase1_plan
            or successor_stage065_phase2_plan
            or successor_stage065_phase3_plan
            or successor_stage065_phase4_plan
            or successor_stage065_review_plan
            or successor_stage066_phase1_plan
            or successor_stage066_phase2_plan
            or successor_stage066_phase3_plan
            or successor_stage066_phase4_plan
            or successor_stage066_review_plan
            or successor_stage067_phase1_plan
            or successor_stage067_phase2_plan
            or successor_stage067_phase3_plan
            or successor_stage067_phase4_plan
            or successor_stage067_review_plan
            or successor_stage068_phase1_plan
            or successor_stage068_phase2_plan
            or successor_stage068_phase3_plan
            or successor_stage068_phase4_plan
            or successor_stage068_review_plan
            or successor_stage069_phase1_plan
            or successor_stage069_phase2_plan
            or successor_stage069_phase3_plan
            or successor_stage069_phase4_plan
            or successor_stage069_review_plan
            or successor_stage070_phase1_plan
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071
                and plan.get("task") == SUCCESSOR_TASK071
                and SUCCESSOR_NEXT_GATE071 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P2
                and plan.get("task") == SUCCESSOR_TASK071_P2
                and SUCCESSOR_NEXT_GATE071_P2 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P3
                and plan.get("task") == SUCCESSOR_TASK071_P3
                and SUCCESSOR_NEXT_GATE071_P3 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_P4
                and plan.get("task") == SUCCESSOR_TASK071_P4
                and SUCCESSOR_NEXT_GATE071_P4 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE071
                and plan.get("phase") == SUCCESSOR_TASK071_REVIEW
                and plan.get("task") == SUCCESSOR_TASK071_REVIEW
                and SUCCESSOR_NEXT_GATE071_REVIEW in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P1
                and plan.get("task") == SUCCESSOR_TASK072_P1
                and SUCCESSOR_NEXT_GATE072_P1 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P2
                and plan.get("task") == SUCCESSOR_TASK072_P2
                and SUCCESSOR_NEXT_GATE072_P2 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P3
                and plan.get("task") == SUCCESSOR_TASK072_P3
                and SUCCESSOR_NEXT_GATE072_P3 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_P4
                and plan.get("task") == SUCCESSOR_TASK072_P4
                and SUCCESSOR_NEXT_GATE072_P4 in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == SUCCESSOR_STAGE072
                and plan.get("phase") == SUCCESSOR_TASK072_REVIEW
                and plan.get("task") == SUCCESSOR_TASK072_REVIEW
                and SUCCESSOR_NEXT_GATE072_REVIEW in str(plan.get("stop_condition", ""))
            )
            or (
                plan.get("stage") == "IDS-STAGE060"
                and plan.get("phase") == TASK_ID
                and plan.get("task") == TASK_ID
                and "IDS-STAGE061-P1-GATE" in str(plan.get("stop_condition", ""))
                and "OVH" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P1"
                and plan.get("task") == "IDS-V0_1-STAGE073-P1"
                and "IDS-STAGE073-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P2"
                and plan.get("task") == "IDS-V0_1-STAGE073-P2"
                and "IDS-STAGE073-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P3"
                and plan.get("task") == "IDS-V0_1-STAGE073-P3"
                and "IDS-STAGE073-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-P4"
                and plan.get("task") == "IDS-V0_1-STAGE073-P4"
                and "IDS-STAGE073-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE073"
                and plan.get("phase") == "IDS-V0_1-STAGE073-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE073-REVIEW"
                and "IDS-STAGE074-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P1"
                and plan.get("task") == "IDS-V0_1-STAGE074-P1"
                and "IDS-STAGE074-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P2"
                and plan.get("task") == "IDS-V0_1-STAGE074-P2"
                and "IDS-STAGE074-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P3"
                and plan.get("task") == "IDS-V0_1-STAGE074-P3"
                and "IDS-STAGE074-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-P4"
                and plan.get("task") == "IDS-V0_1-STAGE074-P4"
                and "IDS-STAGE074-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE074"
                and plan.get("phase") == "IDS-V0_1-STAGE074-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE074-REVIEW"
                and "IDS-STAGE075-P1-GATE" in str(plan.get("stop_condition", ""))
            )
           or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P1"
                and plan.get("task") == "IDS-V0_1-STAGE075-P1"
                and "IDS-STAGE075-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P2"
                and plan.get("task") == "IDS-V0_1-STAGE075-P2"
                and "IDS-STAGE075-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P3"
                and plan.get("task") == "IDS-V0_1-STAGE075-P3"
                and "IDS-STAGE075-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-P4"
                and plan.get("task") == "IDS-V0_1-STAGE075-P4"
                and "IDS-STAGE075-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE075"
                and plan.get("phase") == "IDS-V0_1-STAGE075-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE075-REVIEW"
                and "IDS-STAGE076-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P1"
                and plan.get("task") == "IDS-V0_1-STAGE076-P1"
                and "IDS-STAGE076-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P2"
                and plan.get("task") == "IDS-V0_1-STAGE076-P2"
                and "IDS-STAGE076-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P3"
                and plan.get("task") == "IDS-V0_1-STAGE076-P3"
                and "IDS-STAGE076-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-P4"
                and plan.get("task") == "IDS-V0_1-STAGE076-P4"
                and "IDS-STAGE076-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE076"
                and plan.get("phase") == "IDS-V0_1-STAGE076-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE076-REVIEW"
                and "IDS-STAGE077-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P1"
                and plan.get("task") == "IDS-V0_1-STAGE077-P1"
                and "IDS-STAGE077-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P2"
                and plan.get("task") == "IDS-V0_1-STAGE077-P2"
                and "IDS-STAGE077-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P3"
                and plan.get("task") == "IDS-V0_1-STAGE077-P3"
                and "IDS-STAGE077-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-P4"
                and plan.get("task") == "IDS-V0_1-STAGE077-P4"
                and "IDS-STAGE077-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE077"
                and plan.get("phase") == "IDS-V0_1-STAGE077-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE077-REVIEW"
                and "IDS-STAGE078-P1-GATE" in str(plan.get("stop_condition", ""))
            )
           or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P1"
                and plan.get("task") == "IDS-V0_1-STAGE078-P1"
                and "IDS-STAGE078-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P2"
                and plan.get("task") == "IDS-V0_1-STAGE078-P2"
                and "IDS-STAGE078-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P3"
                and plan.get("task") == "IDS-V0_1-STAGE078-P3"
                and "IDS-STAGE078-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-V0_1-STAGE078-P4"
                and plan.get("task") == "IDS-V0_1-STAGE078-P4"
                and "IDS-STAGE078-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE078"
                and plan.get("phase") == "IDS-STAGE078-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE078-REVIEW"
                and "IDS-STAGE079-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P1"
                and plan.get("task") == "IDS-V0_1-STAGE079-P1"
                and "IDS-STAGE079-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P2"
                and plan.get("task") == "IDS-V0_1-STAGE079-P2"
                and "IDS-STAGE079-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P3"
                and plan.get("task") == "IDS-V0_1-STAGE079-P3"
                and "IDS-STAGE079-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-V0_1-STAGE079-P4"
                and plan.get("task") == "IDS-V0_1-STAGE079-P4"
                and "IDS-STAGE079-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE079"
                and plan.get("phase") == "IDS-STAGE079-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE079-REVIEW"
                and "IDS-STAGE080-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P1"
                and plan.get("task") == "IDS-V0_1-STAGE080-P1"
                and "IDS-STAGE080-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P2"
                and plan.get("task") == "IDS-V0_1-STAGE080-P2"
                and "IDS-STAGE080-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P3"
                and plan.get("task") == "IDS-V0_1-STAGE080-P3"
                and "IDS-STAGE080-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-V0_1-STAGE080-P4"
                and plan.get("task") == "IDS-V0_1-STAGE080-P4"
                and "IDS-STAGE080-REVIEW-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE080"
                and plan.get("phase") == "IDS-STAGE080-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE080-REVIEW"
                and "IDS-STAGE081-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P1"
                and plan.get("task") == "IDS-V0_1-STAGE081-P1"
                and "IDS-STAGE081-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P2"
                and plan.get("task") == "IDS-V0_1-STAGE081-P2"
                and "IDS-STAGE081-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P3"
                and plan.get("task") == "IDS-V0_1-STAGE081-P3"
                and "IDS-STAGE081-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-P4"
                and plan.get("task") == "IDS-V0_1-STAGE081-P4"
                and "IDS-STAGE081-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE081"
                and plan.get("phase") == "IDS-STAGE081-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE081-REVIEW"
                and "IDS-STAGE082-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P1"
                and plan.get("task") == "IDS-V0_1-STAGE082-P1"
                and "IDS-STAGE082-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P2"
                and plan.get("task") == "IDS-V0_1-STAGE082-P2"
                and "IDS-STAGE082-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P3"
                and plan.get("task") == "IDS-V0_1-STAGE082-P3"
                and "IDS-STAGE082-P4-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-P4"
                and plan.get("task") == "IDS-V0_1-STAGE082-P4"
                and "IDS-STAGE082-REVIEW-GATE"
                in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE082"
                and plan.get("phase") == "IDS-STAGE082-REVIEW"
                and plan.get("task") == "IDS-V0_1-STAGE082-REVIEW"
                and "IDS-STAGE083-P1-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P1"
                and plan.get("task") == "IDS-V0_1-STAGE083-P1"
                and "IDS-STAGE083-P2-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P2"
                and plan.get("task") == "IDS-V0_1-STAGE083-P2"
                and "IDS-STAGE083-P3-GATE" in str(plan.get("stop_condition", ""))
            )
            or (
                isinstance(plan, dict)
                and plan.get("stage") == "IDS-STAGE083"
                and plan.get("phase") == "IDS-STAGE083-P3"
                and plan.get("task") == "IDS-V0_1-STAGE083-P3"
                and "IDS-STAGE083-P4-GATE" in str(plan.get("stop_condition", ""))
            )
        ),
        "roadmap_projection": (
            (
                isinstance(stage060, dict)
                and NEXT_GATE in str(stage060.get("gate", ""))
                and "批次复审" in str(stage060.get("status", ""))
            )
            or (
                isinstance(stage061, dict)
                and "Stage061 P2" in str(stage061.get("gate", ""))
                and "P1 白箱合同完成" in str(stage061.get("status", ""))
            )
            or (
                isinstance(stage061, dict)
                and "Stage061 P3" in str(stage061.get("gate", ""))
                and "P2 纯内存控制切片完成" in str(stage061.get("status", ""))
            )
            or (
                isinstance(stage061, dict)
                and "Stage061 P4" in str(stage061.get("gate", ""))
                and "P3 受控异常场景完成" in str(stage061.get("status", ""))
            )
            or (
                isinstance(stage061, dict)
                and "Stage061 Review" in str(stage061.get("gate", ""))
                and "P4 交付证据完成" in str(stage061.get("status", ""))
            )
            or (
                isinstance(stage061, dict)
                and "Stage062 Phase 1" in str(stage061.get("gate", ""))
                and "整阶段本地复审完成" in str(stage061.get("status", ""))
            )
            or (
                isinstance(stage062, dict)
                and "Stage062 Phase 2" in str(stage062.get("gate", ""))
                and "19 字段" in str(stage062.get("status", ""))
            )
            or (
                isinstance(stage062, dict)
                and "Stage062 Phase 3" in str(stage062.get("gate", ""))
                and "两条固定非业务 control" in str(stage062.get("status", ""))
            )
            or (
                isinstance(stage062, dict)
                and "Stage062 Phase 4" in str(stage062.get("gate", ""))
                and "六类显式人工处置" in str(stage062.get("status", ""))
            )
            or (
                isinstance(stage062, dict)
                and "Stage063 Phase 1" in str(stage062.get("gate", ""))
                and "整阶段本地复审完成" in str(stage062.get("status", ""))
            )
            or (
                isinstance(stage063, dict)
                and "Stage063 Phase 2" in str(stage063.get("gate", ""))
                and "8 个仅引用输入" in str(stage063.get("status", ""))
            )
            or (
                isinstance(stage063, dict)
                and "Stage063 Phase 3" in str(stage063.get("gate", ""))
                and "三条固定非业务 control" in str(stage063.get("status", ""))
            )
            or (
                isinstance(stage063, dict)
                and "Stage064 Phase 1" in str(stage063.get("gate", ""))
                and "整阶段本地复审完成" in str(stage063.get("status", ""))
            )
        ),
        "acceptance_projection": {
            "ACC-BATCH051-060-REVIEW-01",
            "ACC-BATCH051-060-REVIEW-02",
            "ACC-BATCH051-060-REVIEW-03",
            "ACC-BATCH051-060-REVIEW-04",
        }.issubset(acceptance_ids),
    }


def build_batch051_060_review_report(
    contract: Mapping[str, Any] | None = None,
    stage_result_overrides: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    checked_contract = dict(contract) if contract is not None else load_contract()
    batch = _load_yaml(BATCH_PATH)
    roadmap = _load_yaml(ROADMAP_PATH)
    contract_shape_checks = _contract_shape_checks(checked_contract)
    artifact_checks = _artifact_checks(checked_contract)
    stage_checks = _stage_checks(checked_contract, batch, stage_result_overrides)
    governance_checks = _governance_checks(batch, roadmap)
    projection_checks = _projection_checks()
    truth = checked_contract.get("truth_contract")
    truth_checks = {"truth_contract_exact": truth == EXPECTED_TRUTH}
    review_valid = all(
        all(group.values())
        for group in (
            contract_shape_checks,
            artifact_checks,
            stage_checks,
            governance_checks,
            projection_checks,
            truth_checks,
        )
    )
    return {
        "schema_version": "ids.v0_1.batch051_060.review_report.v1",
        "task_id": TASK_ID,
        "reviewed_stage_count": len(EXPECTED_STAGE_IDS),
        "review_valid": review_valid,
        "result": RESULT if review_valid else "FAIL_CLOSED",
        "next_gate": NEXT_GATE if review_valid else TASK_ID,
        "github_upload_allowed": False,
        "push_allowed": False,
        "app_reinstall_allowed": False,
        "contract_shape_checks": contract_shape_checks,
        "artifact_checks": artifact_checks,
        "stage_checks": stage_checks,
        "governance_checks": governance_checks,
        "projection_checks": projection_checks,
        "truth_checks": truth_checks,
    }


def main() -> int:
    report = build_batch051_060_review_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["review_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
