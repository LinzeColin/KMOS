"""Stage075 的纯内存整阶段机械复审，不读取真实资料或启动 Stage076。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-075_外部API覆盖授权审计.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-076_索引版本Schema.md"
)
P1_CONTRACT = BASE / "stage075_external_api_coverage_audit_contract.json"
P2_CONTRACT = BASE / "stage075_external_api_coverage_audit_slice_contract.json"
P3_CONTRACT = BASE / "stage075_external_api_coverage_audit_scenarios_contract.json"
P4_CONTRACT = BASE / "stage075_external_api_coverage_audit_delivery_contract.json"

SCHEMA_VERSION = "ids.stage075.external_api_coverage_audit.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE075-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-075"
PASS_RESULT = "PASS_REVIEWED_EXTERNAL_API_COVERAGE_AUDIT_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_EXTERNAL_API_COVERAGE_AUDIT_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE075-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE076-P1-GATE"
RETURN_STATE = "PASS_PHASE4_EXTERNAL_API_COVERAGE_AUDIT_DELIVERY_RUNTIME_DISABLED"
P3_PASS_RESULT = (
    "PASS_PHASE3_EXTERNAL_API_COVERAGE_AUDIT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
)
P4_PASS_RESULT = "PASS_PHASE4_EXTERNAL_API_COVERAGE_AUDIT_DELIVERY_RUNTIME_DISABLED"

P1_STATE = "PHASE1_EXTERNAL_API_COVERAGE_AUDIT_CONTRACT_RUNTIME_DISABLED"
P2_STATE = "PHASE2_EXTERNAL_API_COVERAGE_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED"
P3_STATE = "PHASE3_EXTERNAL_API_COVERAGE_AUDIT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_STATE = "PHASE4_EXTERNAL_API_COVERAGE_AUDIT_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

P2_EXPECTED_COUNTS = {
    "control_request_count": 5,
    "policy_resolution_count": 5,
    "embedding_queue_record_count": 5,
    "cache_record_count": 5,
    "failed_retry_record_count": 5,
    "cost_governor_control_projection_count": 5,
    "model_version_control_projection_count": 5,
    "cost_control_projection_count": 5,
    "external_api_coverage_audit_projection_count": 5,
    "owner_forced_egress_override_control_projection_count": 1,
}
P3_EXPECTED_COUNTS = {
    "scenario_count": 5,
    "passed_scenario_count": 5,
    "explicit_disposition_count": 5,
    "silent_drop_count": 0,
    "human_handling_required_count": 4,
    "control_audit_field_count": 19,
    "control_audit_field_check_count": 95,
    "future_external_api_call_candidate_count": 3,
    "owner_forced_egress_override_control_projection_count": 1,
    "owner_forced_egress_override_field_count": 4,
    "owner_forced_egress_override_field_check_count": 4,
}
P4_EXPECTED_COUNTS = {
    "policy_sample_count": 5,
    "control_audit_log_sample_count": 5,
    "control_audit_field_count": 19,
    "control_audit_field_check_count": 95,
    "zero_cost_estimate_sample_count": 5,
    "failure_handling_result_count": 5,
    "non_externalized_data_record_count": 5,
    "externalization_record_query_key_count": 8,
    "owner_forced_egress_override_precondition_sample_count": 1,
    "owner_forced_egress_override_field_count": 4,
    "owner_forced_egress_override_field_check_count": 4,
    "future_external_api_call_candidate_count": 3,
    "policy_denied_sample_count": 1,
    "budget_pause_sample_count": 1,
    "human_handling_required_count": 4,
}
ACTUAL_ZERO_COUNT_FIELDS = (
    "actual_embedding_queue_count",
    "actual_cache_entry_count",
    "actual_failed_retry_count",
    "actual_cost_count",
    "actual_model_version_record_count",
    "actual_external_api_audit_record_count",
    "actual_owner_forced_egress_override_audit_record_count",
    "actual_external_api_call_count",
    "actual_model_token_count",
)
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "cost_estimation_execution_performed",
    "budget_lookup_performed",
    "model_version_record_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
    "audit_record_creation_performed",
    "audit_log_query_performed",
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_external_api_coverage_audit_stage075_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage075 P1--P4，只输出零运行时控制结论和下一门禁。"""

    phase2_module = _load_module("stage075_external_api_coverage_audit_slice.py")
    phase3_module = _load_module("stage075_external_api_coverage_audit_scenarios.py")
    phase4_module = _load_module("stage075_external_api_coverage_audit_delivery.py")

    phase1 = _provider_value(phase1_contract_provider or _json_provider(P1_CONTRACT))
    phase2 = _provider_value(phase2_contract_provider or _json_provider(P2_CONTRACT))
    phase3 = _provider_value(phase3_contract_provider or _json_provider(P3_CONTRACT))
    phase4 = _provider_value(phase4_contract_provider or _json_provider(P4_CONTRACT))
    phase2_report = _provider_value(
        phase2_report_provider
        or (
            lambda: phase2_module.execute_external_api_coverage_audit_control_slice(
                phase2_module.build_control_input()
            )
        )
    )
    phase3_report = _provider_value(
        phase3_report_provider
        or phase3_module.build_external_api_coverage_audit_phase3_report
    )
    phase4_report = _provider_value(
        phase4_report_provider
        or phase4_module.build_external_api_coverage_audit_phase4_delivery_report
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2)
        and _phase2_report_valid(phase2_report, phase3_module),
        "P3": _phase3_contract_valid(phase3)
        and _phase3_report_valid(phase3_report, phase3_module),
        "P4": _phase4_contract_valid(phase4)
        and _phase4_report_valid(phase4_report, phase4_module),
    }
    controlled_replay = _controlled_replay(
        phase1, phase4, phase2_report, phase3_report, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
        "all_phase_contracts_and_control_reports_pass": all(phase_results.values()),
        "single_authority_boundary_preserved": _single_authority_boundary(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "fixed_control_shapes_preserved": _controlled_replay_is_expected(
            controlled_replay
        ),
        "policy_audit_and_whitebox_boundaries_preserved": _policy_and_whitebox_boundary(
            phase1, phase2_report, phase3_report, phase4_report
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary(
            phase4_report
        ),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain(
            phase4, phase4_report
        ),
        "stage076_gate_only_opens_after_review": _future_stage_boundary(
            phase1, phase2, phase3, phase4
        ),
        "runtime_actions_disabled": _runtime_closed(
            phase1,
            phase2,
            phase3,
            phase4,
            phase2_report,
            phase3_report,
            phase4_report,
            phase3_module,
            phase4_module,
        ),
    }
    review_valid = all(invariants.values())
    runtime_closed_flags = _runtime_closed_flags()
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": (
            "FROZEN_STAGE075_TASKPACK_AND_STAGE075_P1_TO_P4_CONTROL_ARTIFACTS_ONLY"
        ),
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "reviewed_phase_ids": ("P1", "P2", "P3", "P4"),
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": invariants,
        "review_finding_count": 0 if review_valid else 1,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "review_can_replace_source_document": False,
        "review_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "stage074_review_evidence_read": True,
        "stage075_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": review_valid,
        "batch_review_performed": False,
        "stage076_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **{field: 0 for field in ACTUAL_ZERO_COUNT_FIELDS},
        **runtime_closed_flags,
        "rollback": {
            "return_to": RETURN_STATE,
            "scope": "STAGE075_REVIEW_ARTIFACTS_AND_LOCAL_GOVERNANCE_ONLY",
            "preserve_phase1_contract": True,
            "preserve_phase2_control_slice": True,
            "preserve_phase3_controlled_scenarios": True,
            "preserve_phase4_delivery_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "chinese_feedback": _chinese_feedback(review_valid),
    }
    return report


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_module(filename: str) -> Any:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_value(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    try:
        return _mapping(provider())
    except Exception:
        return {}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _contract_valid(
        contract,
        task_id="IDS-V0_1-STAGE075-P1",
        schema_version="ids.stage075.external_api_coverage_audit.phase1.v1",
        contract_state=P1_STATE,
        next_gate="IDS-STAGE075-P2-GATE",
        phase_field="phase1_started",
        expected_failure_state_count=14,
        expected_execution_ready=True,
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _contract_valid(
        contract,
        task_id="IDS-V0_1-STAGE075-P2",
        schema_version="ids.stage075.external_api_coverage_audit.phase2.v1",
        contract_state=P2_STATE,
        next_gate="IDS-STAGE075-P3-GATE",
        phase_field="phase2_started",
        expected_failure_state_count=10,
        expected_execution_ready=False,
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _contract_valid(
        contract,
        task_id="IDS-V0_1-STAGE075-P3",
        schema_version="ids.stage075.external_api_coverage_audit.phase3.v1",
        contract_state=P3_STATE,
        next_gate="IDS-STAGE075-P4-GATE",
        phase_field="phase3_started",
        expected_failure_state_count=12,
        expected_execution_ready=False,
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _contract_valid(
        contract,
        task_id="IDS-V0_1-STAGE075-P4",
        schema_version="ids.stage075.external_api_coverage_audit.phase4.delivery.v1",
        contract_state=P4_STATE,
        next_gate=REVIEW_GATE,
        phase_field="phase4_started",
        expected_failure_state_count=13,
        expected_execution_ready=False,
    )


def _contract_valid(
    contract: Mapping[str, Any],
    *,
    task_id: str,
    schema_version: str,
    contract_state: str,
    next_gate: str,
    phase_field: str,
    expected_failure_state_count: int,
    expected_execution_ready: bool,
) -> bool:
    source_authority = _mapping(contract.get("source_authority"))
    runtime_boundary = _mapping(contract.get("runtime_boundary"))
    phase_boundary = _mapping(contract.get("stage_and_phase_boundary"))
    authority_boundary = _mapping(contract.get("authority_and_decision_boundary"))
    failures = _mapping(contract.get("failure_and_stop_contract"))
    return (
        contract.get("task_id") == task_id
        and contract.get("schema_version") == schema_version
        and contract.get("contract_state") == contract_state
        and contract.get("execution_ready") is expected_execution_ready
        and contract.get("next_gate") == next_gate
        and source_authority.get("second_authoritative_source_created") is False
        and source_authority.get("source_body_or_path_allowed") is False
        and all(value is False for value in runtime_boundary.values())
        and phase_boundary.get("stage075_started") is True
        and phase_boundary.get(phase_field) is True
        and phase_boundary.get("stage076_started") is False
        and phase_boundary.get("github_upload_allowed") is False
        and phase_boundary.get("push_allowed") is False
        and failures.get("failure_state_count") == expected_failure_state_count
        and authority_boundary.get("source_document_remains_authoritative") is True
        and authority_boundary.get("automatic_business_recommendation_allowed") is False
    )


def _phase2_report_valid(
    report: Mapping[str, Any], phase3_module: Any
) -> bool:
    p2_runtime_fields = tuple(getattr(phase3_module, "P2_RUNTIME_CLOSED_FIELDS", ()))
    audit_projections = _mapping_sequence(
        report.get("external_api_coverage_audit_projections")
    )
    return (
        report.get("input_accepted") is True
        and report.get("execution_state")
        == "COMPLETED_IN_MEMORY_EXTERNAL_API_COVERAGE_AUDIT_CONTROL_SLICE"
        and _has_expected_counts(report, P2_EXPECTED_COUNTS)
        and len(audit_projections) == 5
        and all(len(_mapping(item)) == 19 for item in audit_projections)
        and report.get("all_control_records_keep_required_shapes") is True
        and report.get("control_output_is_not_actual_queue_cache_cost_model_version_or_audit")
        is True
        and report.get("source_body_summary_body_or_chunk_text_retained") is False
        and report.get(
            "complete_owner_forced_egress_override_audit_required_before_future_policy_change"
        )
        is True
        and report.get(
            "owner_forced_egress_override_business_line_whitebox_human_review_required"
        )
        is True
        and report.get("owner_forced_egress_override_policy_change_applied") is False
        and _actual_counts_are_zero(report)
        and _all_false(report, p2_runtime_fields)
    )


def _phase3_report_valid(
    report: Mapping[str, Any], phase3_module: Any
) -> bool:
    runtime_fields = tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == "IDS-STAGE075-P4-GATE"
        and _has_expected_counts(report, P3_EXPECTED_COUNTS)
        and report.get("all_taskpack_special_scenarios_covered") is True
        and report.get("policy_payload_boundaries_preserved") is True
        and report.get("budget_insufficient_pause_preserved") is True
        and report.get("audit_projection_invariant_preserved") is True
        and report.get("future_external_api_call_audit_invariant_preserved") is True
        and report.get("owner_forced_egress_override_precondition_preserved") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("automatic_business_recommendation_allowed") is False
        and _actual_counts_are_zero(report)
        and _all_false(report, runtime_fields)
    )


def _phase4_report_valid(
    report: Mapping[str, Any], phase4_module: Any
) -> bool:
    runtime_fields = tuple(getattr(phase4_module, "RUNTIME_CLOSED_FIELDS", ()))
    return (
        report.get("valid") is True
        and report.get("result") == P4_PASS_RESULT
        and report.get("next_gate") == REVIEW_GATE
        and _has_expected_counts(report, P4_EXPECTED_COUNTS)
        and report.get("phase3_controlled_scenarios_report_valid") is True
        and report.get("phase2_control_slice_report_valid") is True
        and report.get("delivery_evidence_metadata_only") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
        and report.get("delivery_control_metadata_can_replace_source_document") is False
        and report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and report.get("automatic_business_recommendation_allowed") is False
        and report.get("stage076_started") is False
        and _actual_counts_are_zero(report)
        and _all_false(report, runtime_fields)
    )


def _has_expected_counts(
    report: Mapping[str, Any], expected: Mapping[str, int]
) -> bool:
    return all(report.get(field) == value for field, value in expected.items())


def _actual_counts_are_zero(report: Mapping[str, Any]) -> bool:
    return all(
        value == 0
        for key, value in report.items()
        if key.startswith("actual_") and key.endswith("_count")
    )


def _all_false(report: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return bool(fields) and all(report.get(field) is False for field in fields)


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int]:
    audit_projections = _mapping_sequence(
        phase2_report.get("external_api_coverage_audit_projections")
    )
    return {
        "phase1_failure_state_count": _mapping(
            phase1.get("failure_and_stop_contract")
        ).get("failure_state_count", -1),
        "phase2_control_request_count": phase2_report.get(
            "control_request_count", -1
        ),
        "phase2_audit_field_count": (
            len(audit_projections[0]) if audit_projections else -1
        ),
        "phase2_owner_override_projection_count": phase2_report.get(
            "owner_forced_egress_override_control_projection_count", -1
        ),
        "phase3_scenario_count": phase3_report.get("scenario_count", -1),
        "phase3_audit_field_count": phase3_report.get(
            "control_audit_field_count", -1
        ),
        "phase3_audit_field_check_count": phase3_report.get(
            "control_audit_field_check_count", -1
        ),
        "phase3_future_call_candidate_count": phase3_report.get(
            "future_external_api_call_candidate_count", -1
        ),
        "phase3_human_handling_required_count": phase3_report.get(
            "human_handling_required_count", -1
        ),
        "phase4_policy_sample_count": phase4_report.get(
            "policy_sample_count", -1
        ),
        "phase4_audit_sample_count": phase4_report.get(
            "control_audit_log_sample_count", -1
        ),
        "phase4_audit_field_count": phase4_report.get(
            "control_audit_field_count", -1
        ),
        "phase4_audit_field_check_count": phase4_report.get(
            "control_audit_field_check_count", -1
        ),
        "phase4_cost_sample_count": phase4_report.get(
            "zero_cost_estimate_sample_count", -1
        ),
        "phase4_failure_handling_count": phase4_report.get(
            "failure_handling_result_count", -1
        ),
        "phase4_non_externalized_record_count": phase4_report.get(
            "non_externalized_data_record_count", -1
        ),
        "phase4_query_key_count": phase4_report.get(
            "externalization_record_query_key_count", -1
        ),
        "phase4_owner_override_field_count": phase4_report.get(
            "owner_forced_egress_override_field_count", -1
        ),
        "phase4_chinese_feedback_count": len(
            _sequence(phase4_report.get("chinese_feedback"))
        ),
        "phase4_failure_state_count": _mapping(
            phase4.get("failure_and_stop_contract")
        ).get("failure_state_count", -1),
    }


def _controlled_replay_is_expected(replay: Mapping[str, int]) -> bool:
    return replay == {
        "phase1_failure_state_count": 14,
        "phase2_control_request_count": 5,
        "phase2_audit_field_count": 19,
        "phase2_owner_override_projection_count": 1,
        "phase3_scenario_count": 5,
        "phase3_audit_field_count": 19,
        "phase3_audit_field_check_count": 95,
        "phase3_future_call_candidate_count": 3,
        "phase3_human_handling_required_count": 4,
        "phase4_policy_sample_count": 5,
        "phase4_audit_sample_count": 5,
        "phase4_audit_field_count": 19,
        "phase4_audit_field_check_count": 95,
        "phase4_cost_sample_count": 5,
        "phase4_failure_handling_count": 5,
        "phase4_non_externalized_record_count": 5,
        "phase4_query_key_count": 8,
        "phase4_owner_override_field_count": 4,
        "phase4_chinese_feedback_count": 4,
        "phase4_failure_state_count": 13,
    }


def _single_authority_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    contracts = (phase1, phase2, phase3, phase4)
    return (
        all(
            _mapping(contract.get("source_authority")).get(
                "second_authoritative_source_created"
            )
            is False
            for contract in contracts
        )
        and all(
            _mapping(contract.get("source_authority")).get(
                "source_body_or_path_allowed"
            )
            is False
            for contract in contracts
        )
        and phase3_report.get("source_document_remains_authoritative") is True
        and phase3_report.get("audit_projection_can_become_business_fact_authority")
        is False
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and phase4_report.get("owner_override_control_metadata_can_become_business_fact_authority")
        is False
    )


def _policy_and_whitebox_boundary(
    phase1: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    policy_contract = _mapping(phase1.get("policy_inheritance_contract"))
    owner_sample = _mapping(
        phase4_report.get("owner_forced_egress_override_precondition_sample")
    )
    return (
        policy_contract.get("default_external_api_policy") == "denied"
        and phase2_report.get(
            "complete_owner_forced_egress_override_audit_required_before_future_policy_change"
        )
        is True
        and phase2_report.get(
            "owner_forced_egress_override_business_line_whitebox_human_review_required"
        )
        is True
        and phase3_report.get(
            "future_external_api_call_audit_invariant_preserved"
        )
        is True
        and phase4_report.get(
            "business_line_whitebox_human_review_remains_authoritative"
        )
        is True
        and owner_sample.get(
            "business_line_whitebox_human_review_required"
        )
        is True
        and owner_sample.get("actual_override_audit_record_created") is False
        and owner_sample.get("actual_policy_override_applied") is False
    )


def _delivery_boundary(report: Mapping[str, Any]) -> bool:
    return (
        report.get("delivery_evidence_metadata_only") is True
        and all(
            item.get("control_metadata_only") is True
            and item.get("source_content_retained") is False
            and item.get("sent_to_external_api") is False
            for item in _mapping_sequence(
                report.get("external_api_coverage_audit_policy_samples")
            )
        )
        and all(
            item.get("estimated_token_count") == 0
            and item.get("estimated_cost") == 0
            for item in _mapping_sequence(report.get("cost_estimate_samples"))
        )
        and _mapping(
            report.get("externalization_record_query_instructions")
        ).get("persistent_audit_log_available")
        is False
    )


def _rollback_chain(
    phase4_contract: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    return (
        _mapping(phase4_contract.get("rollback_contract")).get("return_to")
        == P3_PASS_RESULT
        and _mapping(phase4_report.get("policy_rollback_instructions")).get(
            "rollback_target_result"
        )
        == P3_PASS_RESULT
        and _mapping(phase4_report.get("policy_rollback_instructions")).get(
            "rollback_target_gate"
        )
        == "IDS-STAGE075-P4-GATE"
    )


def _future_stage_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return (
        all(
            _mapping(contract.get("stage_and_phase_boundary")).get(
                "stage076_started"
            )
            is False
            for contract in (phase1, phase2, phase3, phase4)
        )
        and _mapping(phase4.get("stage_and_phase_boundary")).get(
            "whole_stage_review_performed"
        )
        is False
    )


def _runtime_closed(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
    phase3_module: Any,
    phase4_module: Any,
) -> bool:
    contract_boundaries = (
        _mapping(phase1.get("runtime_boundary")),
        _mapping(phase2.get("runtime_boundary")),
        _mapping(phase3.get("runtime_boundary")),
        _mapping(phase4.get("runtime_boundary")),
    )
    phase2_fields = tuple(getattr(phase3_module, "P2_RUNTIME_CLOSED_FIELDS", ()))
    phase3_fields = tuple(getattr(phase3_module, "RUNTIME_CLOSED_FIELDS", ()))
    phase4_fields = tuple(getattr(phase4_module, "RUNTIME_CLOSED_FIELDS", ()))
    return (
        all(all(value is False for value in boundary.values()) for boundary in contract_boundaries)
        and _all_false(phase2_report, phase2_fields)
        and _all_false(phase3_report, phase3_fields)
        and _all_false(phase4_report, phase4_fields)
        and _actual_counts_are_zero(phase2_report)
        and _actual_counts_are_zero(phase3_report)
        and _actual_counts_are_zero(phase4_report)
    )


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    return [
        _mapping(item)
        for item in _sequence(value)
        if isinstance(item, Mapping)
    ]


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in REVIEW_RUNTIME_FALSE_FIELDS}


def _chinese_feedback(review_valid: bool) -> list[str]:
    if review_valid:
        return [
            "Stage075 的 P1 至 P4 固定控制合同和报告已在本地机械复审，未读取或创建任何真实资料、外发、审计或业务结论。",
            "默认 denied、摘要引用边界、文档收紧、未来文本块引用、预算暂停、十九字段审计和 owner 四字段前置均保持冻结控制形状。",
            "外部 API、模型、Token、队列、缓存、成本、持久审计、Agent、OVH、生产、上传和推送均未执行；来源文档与业务线白箱人工复核仍是唯一权威。",
            "本次复审只开放 Stage076 P1 的独立门禁，不启动 Stage076；如需回退，仅撤回本复审工件并回到 Stage075 P4 交付证据。",
        ]
    return [
        "Stage075 整阶段复审未通过，当前停留在 Review 门禁，不开放 Stage076。",
        "请仅检查冻结合同、控制报告、固定形状、单一权威和零运行时边界，不读取或处理真实资料。",
        "任何审计前置、白箱人工处理、回滚链或运行时关闭标志不一致都必须失败关闭。",
        "回退只影响本次复审工件，保留 Stage075 P1 至 P4 和所有受保护资料。",
    ]
