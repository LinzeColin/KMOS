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
            or (
                status.get("stage") == "IDS-STAGE060"
                and status.get("phase") == TASK_ID
                and status.get("task") == TASK_ID
                and status.get("next_gate") == NEXT_GATE
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
            or (
                plan.get("stage") == "IDS-STAGE060"
                and plan.get("phase") == TASK_ID
                and plan.get("task") == TASK_ID
                and "IDS-STAGE061-P1-GATE" in str(plan.get("stop_condition", ""))
                and "OVH" in str(plan.get("stop_condition", ""))
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
