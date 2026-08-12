"""Stage048 解析器失败降级链的本地整阶段复审。

本模块只读取已提交的 P1--P4 工程合同与纯内存控制模块，重放一个候选
控制记录、P3 场景和 P4 交付投影。它不读取业务资料、不调用外部服务，
也不启动 parser、fallback、队列、质量门或持久化运行态。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage048.parser_fallback.stage_review.v1"
RECORD_KIND = "STAGE048_CONTROLLED_FALLBACK_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_LOCAL_FALLBACK_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE048-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE049-P1-GATE"
SOURCE_AUTHORITY = "FROZEN_TASKPACK_TEXT_AND_STAGE047_REVIEW_ARTIFACTS"

_BASE = Path(__file__).resolve().parent
_CONTRACT_PATHS = {
    "phase1": _BASE / "stage048_parser_fallback_contract.json",
    "phase2": _BASE / "stage048_parser_fallback_slice_contract.json",
    "phase3": _BASE / "stage048_parser_fallback_scenarios_contract.json",
    "phase4": _BASE / "stage048_parser_fallback_delivery_contract.json",
}
_MODULE_PATHS = {
    "phase2": _BASE / "stage048_fallback_slice.py",
    "phase3": _BASE / "stage048_fallback_scenarios.py",
    "phase4": _BASE / "stage048_fallback_delivery.py",
}


def build_stage048_review_report() -> dict[str, Any]:
    """复审 P1--P4 受控证据，返回本地白箱结论。"""

    contracts = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in _CONTRACT_PATHS.items()
    }
    phase2 = _load_module("stage048_review_phase2", _MODULE_PATHS["phase2"])
    phase3 = _load_module("stage048_review_phase3", _MODULE_PATHS["phase3"])
    phase4 = _load_module("stage048_review_phase4", _MODULE_PATHS["phase4"])

    candidate = phase2.resolve_control_fallback(_candidate_control_input())
    scenarios = phase3.build_phase3_scenario_report()
    delivery = phase4.build_phase4_delivery_report()

    phase_results = {
        "phase1_contract_valid": _phase1_contract_valid(contracts["phase1"]),
        "phase2_slice_valid": _phase2_slice_valid(contracts["phase2"], candidate),
        "phase3_scenarios_valid": _phase3_scenarios_valid(
            contracts["phase3"], scenarios
        ),
        "phase4_delivery_valid": _phase4_delivery_valid(
            contracts["phase4"], delivery
        ),
    }
    review_invariants = {
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            contracts
        ),
        "phase1_to_phase4_contracts_valid": all(phase_results.values()),
        "explicit_disposition_and_no_silent_drop_preserved": (
            scenarios["explicit_disposition_count"] == 14
            and scenarios["silent_drop_count"] == 0
            and delivery["quality_metrics"]["explicit_disposition_count"] == 14
            and delivery["quality_metrics"]["silent_drop_count"] == 0
        ),
        "instruction_text_invariance_preserved": (
            scenarios["instruction_route_invariance"] is True
            and all(
                not item["system_instruction_allowed"]
                and not item["tool_authorization_allowed"]
                and not item["policy_override_allowed"]
                for item in scenarios["scenario_results"]
            )
        ),
        "format_and_runtime_boundary_preserved": (
            delivery["support_boundary"]["control_supported_formats"]
            == ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
            and delivery["support_boundary"]["runtime_supported_formats"] == []
            and delivery["quality_metrics"]["parser_execution_count"] == 0
            and delivery["quality_metrics"]["fallback_execution_count"] == 0
            and delivery["quality_metrics"]["persistent_write_count"] == 0
        ),
        "rollback_chain_preserved": _rollback_chain_preserved(contracts, delivery),
        "runtime_and_external_actions_disabled": _runtime_actions_disabled(
            contracts, candidate, scenarios, delivery
        ),
    }
    review_valid = all(review_invariants.values())
    findings = [] if review_valid else ["STAGE048_REVIEW_INVARIANT_NOT_MET"]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "stage": "STAGE-048",
        "task_id": "IDS-V0_1-STAGE048-REVIEW",
        "acceptance_id": "ACC-STAGE-048",
        "source_authority": SOURCE_AUTHORITY,
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "raw_metadata_content_accessed": False,
        "phase_contracts_reviewed": ["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        "phase_results": phase_results,
        "controlled_replay": {
            "phase2_candidate_disposition": candidate["disposition"],
            "phase2_candidate_feedback_code": candidate["human_feedback_code"],
            "phase3_scenario_count": scenarios["scenario_count"],
            "phase3_explicit_disposition_count": scenarios[
                "explicit_disposition_count"
            ],
            "phase3_silent_drop_count": scenarios["silent_drop_count"],
            "phase4_parser_output_sample_count": len(delivery["parser_output_samples"]),
            "phase4_fallback_log_sample_count": len(delivery["fallback_log_samples"]),
            "phase4_failure_classification_count": len(
                delivery["failure_classification"]
            ),
        },
        "review_invariants": review_invariants,
        "review_finding_count": len(findings),
        "review_findings": findings,
        "review_valid": review_valid,
        "execution_ready": False,
        "result": PASS_RESULT if review_valid else "FAIL_CLOSED",
        "review_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "stage049_entry_allowed": False,
        "ids_business_source_read_performed": False,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "automatic_parser_switch_performed": False,
        "human_review_queue_write_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": True,
        "stage049_started": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate_control_input() -> dict[str, object]:
    return {
        "fallback_reference": {
            "source_identity_ref": "source:control:stage048-review-candidate",
            "route_action": "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
            "parser_output_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
            "parser_family": "CONTROL_FIXTURE_ADAPTER",
            "parser_version": "ids.parser.control_fixture.v0_1.stage048.p2",
            "failure_class": "NO_FAILURE",
            "evidence_text_label": "UNTRUSTED_EVIDENCE_TEXT",
        },
        "parser_confidence": "HIGH",
    }


def _phase1_contract_valid(contract: dict[str, Any]) -> bool:
    return (
        contract["schema_version"] == "ids.stage048.parser_fallback.phase1.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE048-P1"
        and contract["execution_ready"] is False
        and contract["fallback_input_contract"]["required_fields"]
        == [
            "source_identity_ref",
            "route_action",
            "parser_output_status",
            "parser_family",
            "parser_version",
            "failure_class",
            "evidence_text_label",
        ]
        and contract["fallback_disposition_contract"]["silent_drop_allowed"] is False
        and contract["fallback_disposition_contract"]["automatic_parser_switch_allowed"]
        is False
    )


def _phase2_slice_valid(contract: dict[str, Any], candidate: dict[str, Any]) -> bool:
    return (
        contract["schema_version"] == "ids.stage048.parser_fallback.phase2.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE048-P2"
        and contract["slice_executable"] is True
        and contract["execution_ready"] is False
        and candidate["input_accepted"] is True
        and candidate["disposition"] == "NO_FALLBACK_CANDIDATE_RETAINED"
        and candidate["human_feedback_code"] == "FALLBACK_CANDIDATE_RETAINED"
        and candidate["evidence_text_label"] == "UNTRUSTED_EVIDENCE_TEXT"
        and candidate["evidence_text_interpretation"] == "EVIDENCE_ONLY"
    )


def _phase3_scenarios_valid(contract: dict[str, Any], report: dict[str, Any]) -> bool:
    return (
        contract["schema_version"] == "ids.stage048.parser_fallback.phase3.scenarios.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE048-P3"
        and contract["scenario_input_boundary"]["scenario_count"] == 14
        and report["valid"] is True
        and report["result"]
        == "PASS_ISOLATED_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED"
        and report["scenario_count"] == 14
        and report["passed_scenario_count"] == 14
        and report["explicit_disposition_count"] == 14
        and report["silent_drop_count"] == 0
    )


def _phase4_delivery_valid(contract: dict[str, Any], report: dict[str, Any]) -> bool:
    metrics = report["quality_metrics"]
    return (
        contract["schema_version"] == "ids.stage048.parser_fallback.phase4.delivery.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE048-P4"
        and report["valid"] is True
        and report["result"] == "PASS_ISOLATED_FALLBACK_CLOSEOUT_RUNTIME_DISABLED"
        and len(report["parser_output_samples"]) == 8
        and len(report["fallback_log_samples"]) == 14
        and len(report["failure_classification"]) == 6
        and metrics["scenario_count"] == 14
        and metrics["explicit_disposition_count"] == 14
        and metrics["silent_drop_count"] == 0
    )


def _single_authority_boundary_preserved(
    contracts: dict[str, dict[str, Any]],
) -> bool:
    return all(
        contract["source_authority"]["authority"] == SOURCE_AUTHORITY
        and contract["source_authority"]["second_authoritative_source_created"]
        is False
        and contract["source_authority"]["source_body_or_path_allowed"] is False
        and contract["source_authority"]["raw_metadata_content_access_allowed"]
        is False
        and contract["source_authority"]["live_source_read_performed"] is False
        for contract in contracts.values()
    )


def _rollback_chain_preserved(
    contracts: dict[str, dict[str, Any]], delivery: dict[str, Any]
) -> bool:
    return (
        delivery["configuration_rollback"]["rollback_target_state"]
        == "PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED"
        and contracts["phase3"]["rollback_contract"]["return_to"]
        == "STAGE048_PHASE2_IN_MEMORY_FALLBACK_DISPOSITION_SLICE_RUNTIME_DISABLED"
        and contracts["phase2"]["rollback_contract"]["return_to"]
        == "STAGE048_PHASE1_PARSER_FALLBACK_BOUNDARY_RUNTIME_DISABLED"
        and contracts["phase1"]["rollback_contract"]["return_to"]
        == "STAGE047_REVIEWED_LOCAL"
    )


def _runtime_actions_disabled(
    contracts: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
    scenarios: dict[str, Any],
    delivery: dict[str, Any],
) -> bool:
    phase1_fields = (
        "source_file_open_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "fallback_execution_allowed",
        "human_review_queue_write_allowed",
        "quality_gate_execution_allowed",
        "evidence_promotion_allowed",
        "persistent_state_write_allowed",
        "agent_execution_allowed",
        "model_call_allowed",
        "model_token_consumption_allowed",
        "ovh_deployment_allowed",
        "production_runtime_activation_allowed",
        "github_upload_allowed",
        "push_allowed",
    )
    later_phase_fields = (
        "source_file_open_allowed",
        "parser_dispatch_allowed",
        "parser_execution_allowed",
        "fallback_execution_allowed",
        "human_review_queue_write_allowed",
        "quality_gate_evaluation_allowed",
        "evidence_promotion_allowed",
        "persistent_state_write_allowed",
        "agent_execution_allowed",
        "model_call_allowed",
        "model_token_consumption_allowed",
        "ovh_deployment_allowed",
        "production_runtime_activation_allowed",
        "github_upload_allowed",
        "push_allowed",
    )
    candidate_fields = (
        "runtime_execution_performed",
        "source_file_open_performed",
        "route_evaluation_performed",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "fallback_execution_performed",
        "automatic_parser_switch_performed",
        "human_review_queue_write_performed",
        "quality_gate_evaluation_performed",
        "evidence_promotion_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
    )
    scenario_fields = (
        "source_file_open_performed",
        "file_signature_detection_performed",
        "route_evaluation_performed",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "fallback_execution_performed",
        "human_review_queue_write_performed",
        "quality_gate_evaluation_performed",
        "evidence_promotion_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "github_upload_performed",
    )
    delivery_fields = (
        "source_file_open_performed",
        "file_signature_detection_performed",
        "route_evaluation_performed",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "parser_output_produced",
        "fallback_execution_performed",
        "runtime_fallback_log_produced",
        "human_review_queue_write_performed",
        "quality_gate_evaluation_performed",
        "evidence_promotion_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "github_upload_performed",
    )
    return (
        all(
            contracts["phase1"]["runtime_boundary"][field] is False
            for field in phase1_fields
        )
        and all(
            all(contracts[name]["runtime_boundary"][field] is False for field in later_phase_fields)
            for name in ("phase2", "phase3", "phase4")
        )
        and all(candidate[field] is False for field in candidate_fields)
        and all(scenarios[field] is False for field in scenario_fields)
        and all(delivery[field] is False for field in delivery_fields)
    )
