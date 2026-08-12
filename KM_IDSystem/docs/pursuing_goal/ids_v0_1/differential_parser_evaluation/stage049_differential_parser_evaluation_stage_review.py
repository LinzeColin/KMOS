"""Stage049 差异化解析器评估的本地整阶段复审。

本模块只读取既有 P1--P4 合同并重放纯内存 control 结果。它不读取业务资料，
不执行 parser、差异比较、fallback、质量门、持久化或外部动作。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage049.differential_parser_evaluation.stage_review.v1"
RECORD_KIND = "STAGE049_CONTROLLED_DIFFERENTIAL_EVALUATION_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_LOCAL_DIFFERENTIAL_EVALUATION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE049-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE050-P1-GATE"
SOURCE_AUTHORITIES = {
    "phase1": "FROZEN_TASKPACK_TEXT_AND_STAGE048_REVIEW_ARTIFACTS",
    "phase2": "FROZEN_TASKPACK_TEXT_AND_STAGE048_REVIEW_ARTIFACTS",
    "phase3": "FROZEN_TASKPACK_TEXT_STAGE049_P1_P2_AND_STAGE048_REVIEW_ARTIFACTS",
    "phase4": "FROZEN_TASKPACK_TEXT_STAGE049_P1_P3_AND_STAGE048_REVIEW_ARTIFACTS",
}

_BASE = Path(__file__).resolve().parent
_CONTRACT_PATHS = {
    "phase1": _BASE / "stage049_differential_parser_evaluation_contract.json",
    "phase2": _BASE / "stage049_differential_parser_evaluation_slice_contract.json",
    "phase3": _BASE / "stage049_differential_parser_evaluation_scenarios_contract.json",
    "phase4": _BASE / "stage049_differential_parser_evaluation_delivery_contract.json",
}
_MODULE_PATHS = {
    "phase2": _BASE / "stage049_differential_parser_evaluation_slice.py",
    "phase3": _BASE / "stage049_differential_parser_evaluation_scenarios.py",
    "phase4": _BASE / "stage049_differential_parser_evaluation_delivery.py",
}


def build_stage049_review_report() -> dict[str, Any]:
    """复审 P1--P4 受控证据并返回本地白箱结论。"""

    contracts = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in _CONTRACT_PATHS.items()
    }
    phase2 = _load_module("stage049_review_phase2", _MODULE_PATHS["phase2"])
    phase3 = _load_module("stage049_review_phase3", _MODULE_PATHS["phase3"])
    phase4 = _load_module("stage049_review_phase4", _MODULE_PATHS["phase4"])

    candidate = phase2.evaluate_controlled_differential_eligibility(
        _review_candidate_control_input()
    )
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
            scenarios["explicit_disposition_count"] == 11
            and scenarios["silent_drop_count"] == 0
            and delivery["quality_metrics"]["explicit_disposition_count"] == 11
            and delivery["quality_metrics"]["silent_drop_count"] == 0
        ),
        "instruction_text_invariance_preserved": _instruction_text_invariance_preserved(
            scenarios
        ),
        "schema_sample_and_log_boundary_preserved": _delivery_boundary_preserved(
            delivery
        ),
        "format_and_runtime_boundary_preserved": _format_and_runtime_boundary_preserved(
            delivery
        ),
        "rollback_chain_preserved": _rollback_chain_preserved(contracts, delivery),
        "runtime_and_external_actions_disabled": _runtime_actions_disabled(
            contracts, candidate, scenarios, delivery
        ),
    }
    review_valid = all(review_invariants.values())
    findings = [] if review_valid else ["STAGE049_REVIEW_INVARIANT_NOT_MET"]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "stage": "STAGE-049",
        "task_id": "IDS-V0_1-STAGE049-REVIEW",
        "acceptance_id": "ACC-STAGE-049",
        "source_authority": "FROZEN_TASKPACK_TEXT_STAGE049_P1_TO_P4_AND_STAGE048_REVIEW_ARTIFACTS",
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "raw_metadata_content_accessed": False,
        "phase_contracts_reviewed": ["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        "phase_results": phase_results,
        "controlled_replay": {
            "phase2_candidate_disposition": candidate["comparison_disposition"],
            "phase2_candidate_feedback_code": candidate["human_feedback_code"],
            "phase3_scenario_count": scenarios["scenario_count"],
            "phase3_explicit_disposition_count": scenarios[
                "explicit_disposition_count"
            ],
            "phase3_silent_drop_count": scenarios["silent_drop_count"],
            "phase4_candidate_parse_product_sample_count": len(
                delivery["candidate_parse_product_samples"]
            ),
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
        "stage050_entry_allowed": False,
        "ids_business_source_read_performed": False,
        "source_file_open_performed": False,
        "file_signature_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_selection_performed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "actual_parse_product_comparison_performed": False,
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
        "stage050_started": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage049 review dependency is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _review_candidate_control_input() -> dict[str, object]:
    return {
        "candidate_controls": [
            _candidate("alpha"),
            _candidate("beta"),
        ]
    }


def _candidate(version_suffix: str) -> dict[str, object]:
    return {
        "candidate_reference": {
            "source_identity_ref": "source:control:stage049-review-candidate",
            "route_action": "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
            "parser_output_status": "OUTPUT_CANDIDATE_NOT_VALIDATED",
            "parser_family": "CONTROL_DIFFERENTIAL_FIXTURE_ADAPTER",
            "parser_version": (
                "ids.parser.control_fixture.v0_1.stage049.p2." + version_suffix
            ),
            "output_schema_version": "ids.parser_output.v0_1.stage047.p1",
            "evidence_text_label": "UNTRUSTED_EVIDENCE_TEXT",
        },
        "parser_confidence": "HIGH",
    }


def _phase1_contract_valid(contract: dict[str, Any]) -> bool:
    return (
        contract["schema_version"] == "ids.stage049.differential_parser_evaluation.phase1.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE049-P1"
        and contract["execution_ready"] is False
        and contract["reference_only_candidate_contract"]["required_fields"]
        == [
            "source_identity_ref",
            "route_action",
            "parser_output_status",
            "parser_family",
            "parser_version",
            "output_schema_version",
            "evidence_text_label",
        ]
        and contract["parse_product_output_contract"]["core_field_count"] == 6
        and contract["differential_comparison_contract"]["minimum_candidate_parser_versions"]
        == 2
        and contract["quality_and_evidence_boundary"]["quality_gate_execution_allowed"]
        is False
    )


def _phase2_slice_valid(contract: dict[str, Any], candidate: dict[str, Any]) -> bool:
    return (
        contract["schema_version"] == "ids.stage049.differential_parser_evaluation.phase2.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE049-P2"
        and contract["slice_executable"] is True
        and contract["execution_ready"] is False
        and contract["control_input_contract"]["candidate_count_exact"] == 2
        and candidate["input_accepted"] is True
        and candidate["candidate_count"] == 2
        and candidate["distinct_parser_version_count"] == 2
        and candidate["comparison_disposition"]
        == "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW"
        and candidate["human_feedback_code"]
        == "DIFFERENTIAL_CONTROL_QUALITY_REVIEW_REQUIRED"
        and candidate["evidence_text_label"] == "UNTRUSTED_EVIDENCE_TEXT"
        and candidate["evidence_text_interpretation"] == "EVIDENCE_ONLY"
    )


def _phase3_scenarios_valid(contract: dict[str, Any], report: dict[str, Any]) -> bool:
    return (
        contract["schema_version"]
        == "ids.stage049.differential_parser_evaluation.phase3.scenarios.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE049-P3"
        and contract["scenario_input_boundary"]["scenario_count"] == 11
        and contract["format_coverage"]["all_taskpack_format_families_covered"] is True
        and report["valid"] is True
        and report["result"]
        == "PASS_ISOLATED_CONTROLLED_DIFFERENTIAL_EVALUATION_SCENARIOS_RUNTIME_DISABLED"
        and report["scenario_count"] == 11
        and report["passed_scenario_count"] == 11
        and report["explicit_disposition_count"] == 11
        and report["silent_drop_count"] == 0
    )


def _phase4_delivery_valid(contract: dict[str, Any], report: dict[str, Any]) -> bool:
    metrics = report["quality_metrics"]
    return (
        contract["schema_version"]
        == "ids.stage049.differential_parser_evaluation.phase4.delivery.v1"
        and contract["task_id"] == "IDS-V0_1-STAGE049-P4"
        and contract["stage_review_status"] == "pending_next_run"
        and contract["valid_result"]
        == "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED"
        and report["valid"] is True
        and report["result"]
        == "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED"
        and len(report["candidate_parse_product_samples"]) == 20
        and len(report["fallback_log_samples"]) == 11
        and len(report["failure_classification"]) == 5
        and metrics["scenario_count"] == 11
        and metrics["explicit_disposition_count"] == 11
        and metrics["silent_drop_count"] == 0
    )


def _single_authority_boundary_preserved(
    contracts: dict[str, dict[str, Any]],
) -> bool:
    return all(
        contract["source_authority"]["authority"] == SOURCE_AUTHORITIES[name]
        and contract["source_authority"]["second_authoritative_source_created"]
        is False
        and contract["source_authority"]["source_body_or_path_allowed"] is False
        and contract["source_authority"]["raw_metadata_content_access_allowed"]
        is False
        and contract["source_authority"]["live_source_read_performed"] is False
        for name, contract in contracts.items()
    )


def _instruction_text_invariance_preserved(report: dict[str, Any]) -> bool:
    return report["instruction_disposition_invariance"] is True and all(
        item["evidence_text_label"] == "UNTRUSTED_EVIDENCE_TEXT"
        and item["evidence_text_interpretation"] == "EVIDENCE_ONLY"
        and item["system_instruction_allowed"] is False
        and item["tool_authorization_allowed"] is False
        and item["policy_override_allowed"] is False
        for item in report["scenario_results"]
    )


def _delivery_boundary_preserved(delivery: dict[str, Any]) -> bool:
    return all(
        item["sample_kind"]
        == "SCHEMA_ONLY_CANDIDATE_PARSE_PRODUCT_SAMPLE_NOT_EXECUTED"
        and item["text"] is None
        and item["tables"] == []
        and item["pages"] == []
        and item["sections"] == []
        and item["source_content_retained"] is False
        and item["source_reference_retained"] is False
        and item["runtime_output_produced"] is False
        for item in delivery["candidate_parse_product_samples"]
    ) and all(
        item["sample_kind"] == "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME"
        and item["attempted"] is False
        and item["attempt_count"] == 0
        and item["silent_drop"] is False
        and item["parser_switch_performed"] is False
        and item["human_review_queue_write_performed"] is False
        and item["runtime_log_written"] is False
        for item in delivery["fallback_log_samples"]
    )


def _format_and_runtime_boundary_preserved(delivery: dict[str, Any]) -> bool:
    metrics = delivery["quality_metrics"]
    return (
        delivery["support_boundary"]["control_format_labels"]
        == ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
        and delivery["support_boundary"]["runtime_supported_formats"] == []
        and delivery["support_boundary"]["generic_parser_allowed"] is False
        and metrics["parser_execution_count"] == 0
        and metrics["actual_parse_product_comparison_count"] == 0
        and metrics["fallback_execution_count"] == 0
        and metrics["quality_gate_evaluation_count"] == 0
        and metrics["persistent_write_count"] == 0
    )


def _rollback_chain_preserved(
    contracts: dict[str, dict[str, Any]], delivery: dict[str, Any]
) -> bool:
    return (
        delivery["configuration_rollback"]["rollback_target_state"]
        == "PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED"
        and contracts["phase3"]["rollback_contract"]["return_to"]
        == "PHASE2_CONTROLLED_DIFFERENTIAL_ELIGIBILITY_RUNTIME_DISABLED"
        and contracts["phase2"]["rollback_contract"]["return_to"]
        == "PHASE1_DIFFERENTIAL_PARSER_EVALUATION_BOUNDARY_RUNTIME_DISABLED"
        and contracts["phase1"]["rollback_contract"]["return_to"]
        == "STAGE048_REVIEWED_LOCAL_FALLBACK_RUNTIME_DISABLED"
    )


def _runtime_actions_disabled(
    contracts: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
    scenarios: dict[str, Any],
    delivery: dict[str, Any],
) -> bool:
    return (
        all(
            value is False
            for contract in contracts.values()
            for value in contract["runtime_boundary"].values()
        )
        and all(
            value is False
            for key, value in candidate.items()
            if key.endswith("_performed")
        )
        and all(
            value is False
            for key, value in scenarios.items()
            if key.endswith("_performed")
        )
        and scenarios["phase4_started"] is False
        and all(
            value is False
            for key, value in delivery.items()
            if key.endswith("_performed")
        )
        and delivery["whole_stage_review_performed"] is False
        and delivery["github_upload_performed"] is False
    )
