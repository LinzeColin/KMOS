"""Stage072 的只读整阶段机械复审，不读取真实资料或启动 Stage073。"""

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
    / "STAGE-072_Embedding模型版本.md"
)
P1_CONTRACT = BASE / "stage072_embedding_model_version_contract.json"
P2_CONTRACT = BASE / "stage072_embedding_model_version_slice_contract.json"
P3_CONTRACT = BASE / "stage072_embedding_model_version_scenarios_contract.json"
P4_CONTRACT = BASE / "stage072_embedding_model_version_delivery_contract.json"

SCHEMA_VERSION = "ids.stage072.embedding_model_version.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE072-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-072"
PASS_RESULT = "PASS_REVIEWED_LOCAL_EMBEDDING_MODEL_VERSION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_EMBEDDING_MODEL_VERSION_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE072-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE073-P1-GATE"
RETURN_STATE = "PHASE4_EMBEDDING_MODEL_VERSION_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED"
P2_STATE = "COMPLETED_IN_MEMORY_EMBEDDING_MODEL_VERSION_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PHASE4_EMBEDDING_MODEL_VERSION_DELIVERY_RUNTIME_DISABLED"

P2_RECORD_SHAPES = {
    "policy_resolutions": 10,
    "embedding_queue_records": 14,
    "cache_records": 10,
    "failed_retry_records": 7,
    "model_version_control_projections": 6,
    "cost_control_projections": 8,
    "external_api_audit_projections": 18,
}
P4_RECORD_SHAPES = {
    "embedding_model_version_policy_samples": 34,
    "control_audit_log_samples": 15,
    "cost_estimate_samples": 20,
    "failure_handling_results": 14,
    "non_externalized_data_records": 12,
}
P2_REPORT_RUNTIME_FALSE_FIELDS = (
    "actual_budget_lookup_performed",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_chunk_policy_assigned",
    "actual_cost_estimation_performed",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_embedding_queue_request_created",
    "actual_external_api_audit_record_created",
    "actual_failed_retry_record_created",
    "actual_model_version_record_created",
    "actual_policy_resolution_record_created",
    "actual_retry_execution_performed",
    "agent_execution_performed",
    "budget_lookup_performed",
    "cache_read_or_write_performed",
    "chunk_manual_policy_assignment_performed",
    "chunking_execution_performed",
    "cost_estimation_execution_performed",
    "database_connection_performed",
    "embedding_or_index_write_performed",
    "embedding_queue_execution_performed",
    "external_api_call_performed",
    "external_api_client_initialized",
    "external_payload_created",
    "failed_retry_execution_performed",
    "github_upload_performed",
    "ids_business_source_read_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "model_version_record_execution_performed",
    "ovh_deployment_performed",
    "parser_execution_performed",
    "persistent_state_write_performed",
    "production_runtime_activation_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "push_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "summary_generation_performed",
)
P3_REPORT_RUNTIME_FALSE_FIELDS = (
    "actual_budget_lookup_performed",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_chunk_policy_assigned",
    "actual_control_scenario_record_persisted",
    "actual_cost_estimation_performed",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_embedding_queue_request_created",
    "actual_external_api_audit_record_created",
    "actual_external_payload_created",
    "actual_failed_retry_record_created",
    "actual_model_version_record_created",
    "actual_policy_resolution_record_created",
    "actual_retry_execution_performed",
    "agent_execution_performed",
    "authorized_fixture_access_performed",
    "batch_review_performed",
    "budget_lookup_performed",
    "cache_read_or_write_performed",
    "chunking_execution_performed",
    "cost_estimation_execution_performed",
    "database_connection_performed",
    "embedding_or_index_write_performed",
    "embedding_queue_execution_performed",
    "external_api_call_performed",
    "external_api_client_initialized",
    "external_payload_created",
    "failed_retry_execution_performed",
    "github_upload_allowed",
    "github_upload_performed",
    "ids_business_source_read_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "model_version_record_execution_performed",
    "ovh_deployment_performed",
    "parser_execution_performed",
    "persistent_state_write_performed",
    "production_runtime_activation_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "push_allowed",
    "push_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "stage073_started",
    "summary_generation_performed",
)
P4_REPORT_RUNTIME_FALSE_FIELDS = (
    "actual_audit_log_query_performed",
    "actual_budget_lookup_performed",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_chunk_policy_assigned",
    "actual_cost_estimation_performed",
    "actual_delivery_file_written",
    "actual_document_policy_resolved",
    "actual_embedding_queue_request_created",
    "actual_external_api_audit_record_created",
    "actual_externalization_record_query_performed",
    "actual_failed_retry_record_created",
    "actual_model_version_record_created",
    "actual_policy_resolution_record_created",
    "actual_policy_rollback_performed",
    "actual_retry_execution_performed",
    "agent_execution_performed",
    "authorized_fixture_access_performed",
    "batch_review_performed",
    "budget_lookup_performed",
    "cache_read_or_write_performed",
    "chunking_execution_performed",
    "cost_estimation_execution_performed",
    "database_connection_performed",
    "embedding_or_index_write_performed",
    "embedding_queue_execution_performed",
    "external_api_call_performed",
    "external_api_client_initialized",
    "external_payload_created",
    "failed_retry_execution_performed",
    "github_upload_allowed",
    "github_upload_performed",
    "ids_business_source_read_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "model_version_record_execution_performed",
    "ovh_deployment_performed",
    "parser_execution_performed",
    "persistent_state_write_performed",
    "production_runtime_activation_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "push_allowed",
    "push_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "stage073_started",
    "summary_generation_performed",
)
REVIEW_RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "cost_estimation_execution_performed",
    "budget_lookup_performed",
    "external_payload_created",
    "external_api_client_initialized",
    "external_api_call_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "actual_external_api_audit_record_created",
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "stage073_started",
    "batch_review_performed",
    "github_upload_performed",
    "github_upload_allowed",
    "push_performed",
    "push_allowed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage072_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage072 P1--P4，只输出本地控制结论、门禁和回退范围。"""

    phase1 = _mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    phase2_report = _mapping((phase2_report_provider or _phase2_report_provider())())
    phase3_report = _mapping((phase3_report_provider or _report_provider(
        "stage072_embedding_model_version_scenarios.py",
        "build_embedding_model_version_phase3_report",
    ))())
    phase4_report = _mapping((phase4_report_provider or _report_provider(
        "stage072_embedding_model_version_delivery.py",
        "build_embedding_model_version_phase4_delivery_report",
    ))())

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2) and _phase2_report_valid(phase2_report),
        "P3": _phase3_contract_valid(phase3) and _phase3_report_valid(phase3_report),
        "P4": _phase4_contract_valid(phase4) and _phase4_report_valid(phase4_report),
    }
    replay = _controlled_replay(
        phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "policy_and_audit_boundaries_preserved": _policy_and_audit_boundary(
            phase1, phase2, phase3_report, phase4_report
        ),
        "fixed_control_shapes_preserved": _shape_valid(replay),
        "future_calls_require_audit_and_whitebox_handling": _future_call_boundary(
            phase3_report, phase4_report
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary(
            phase4_report
        ),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain(
            phase1, phase2, phase3, phase4, phase4_report
        ),
        "future_stage_ownership_preserved": _future_stage_boundary(
            phase1, phase2, phase3, phase4
        ),
        "runtime_actions_disabled": _runtime_closed(
            phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
        ),
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_STAGE072_TASKPACK_AND_STAGE072_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "reviewed_phase_ids": ("P1", "P2", "P3", "P4"),
        "phase_results": phase_results,
        "controlled_replay": replay,
        "review_invariants": invariants,
        "review_finding_count": 0,
        "review_valid": False,
        "result": FAIL_RESULT,
        "rollback": {
            "return_to": RETURN_STATE,
            "revertable_artifacts": (
                "Stage072 review document",
                "Stage072 review module",
                "Stage072 review focused tests",
                "Stage072 review governance projection",
            ),
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "audit_log_change_allowed": False,
            "model_version_or_embedding_runtime_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": REVIEW_GATE,
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "actual_model_version_record_created": False,
        "actual_embedding_queue_request_created": False,
        "actual_cache_entry_created": False,
        "actual_failed_retry_record_created": False,
        "actual_cost_record_created": False,
        "actual_external_api_audit_log_created": False,
        "actual_delivery_file_written": False,
        "stage072_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        report["review_invariants"]["runtime_actions_disabled"]
        and _all_false(
            report,
            REVIEW_RUNTIME_FALSE_FIELDS
            + (
                "actual_model_version_record_created",
                "actual_embedding_queue_request_created",
                "actual_cache_entry_created",
                "actual_failed_retry_record_created",
                "actual_cost_record_created",
                "actual_external_api_audit_log_created",
                "actual_delivery_file_written",
            ),
        )
    )
    report["review_valid"] = all(phase_results.values()) and all(invariants.values())
    report["review_finding_count"] = 0 if report["review_valid"] else 1
    report["result"] = PASS_RESULT if report["review_valid"] else FAIL_RESULT
    report["next_gate"] = NEXT_GATE if report["review_valid"] else REVIEW_GATE
    return report


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage072.embedding_model_version.phase1.v1"),
            ("contract_state", "PHASE1_EMBEDDING_MODEL_VERSION_CONTRACT_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE072-P1"),
            ("next_gate", "IDS-STAGE072-P2-GATE"),
            ("execution_ready.static_contract_ready", True),
            ("execution_ready.runtime_execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("model_version_record_contract.field_count", 6),
            ("model_version_record_contract.actual_model_version_record_count", 0),
            ("policy_inheritance_dependency.default_external_api_policy", "denied"),
            ("policy_inheritance_dependency.allowed_value_count", 3),
            ("policy_inheritance_dependency.inheritance_hop_count", 2),
            ("policy_inheritance_dependency.document_may_widen_data_source_policy", False),
            ("policy_inheritance_dependency.chunk_inherits_effective_document_policy_automatically", True),
            ("queue_cost_and_audit_dependency.future_queue_field_count", 12),
            ("queue_cost_and_audit_dependency.future_cache_field_count", 10),
            ("queue_cost_and_audit_dependency.future_failed_retry_field_count", 7),
            ("queue_cost_and_audit_dependency.future_cost_and_model_field_count", 8),
            ("queue_cost_and_audit_dependency.future_external_api_audit_field_count", 18),
            ("failure_and_stop_contract.failure_state_count", 9),
            ("stage_and_phase_boundary.phase1_started", True),
            ("stage_and_phase_boundary.phase2_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage073_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage072.embedding_model_version.phase2.v1"),
            ("contract_state", "PHASE2_EMBEDDING_MODEL_VERSION_CONTROL_SLICE_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE072-P2"),
            ("next_gate", "IDS-STAGE072-P3-GATE"),
            ("slice_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("reference_only_embedding_model_version_input_control_contract.field_count", 20),
            ("reference_only_embedding_model_version_input_control_contract.control_request_count", 5),
            ("policy_inheritance_control_contract.default_external_api_policy", "denied"),
            ("policy_inheritance_control_contract.inheritance_hop_count", 2),
            ("policy_inheritance_control_contract.document_may_widen_data_source_policy", False),
            ("policy_inheritance_control_contract.chunk_inherits_effective_document_policy_automatically", True),
            ("embedding_queue_cache_retry_control_contract.future_queue_field_count", 12),
            ("embedding_queue_cache_retry_control_contract.future_cache_field_count", 10),
            ("embedding_queue_cache_retry_control_contract.future_failed_retry_field_count", 7),
            ("model_version_control_contract.field_count", 6),
            ("cost_control_contract.field_count", 8),
            ("external_api_audit_control_contract.field_count", 18),
            ("failure_and_stop_contract.failure_state_count", 10),
            ("stage_and_phase_boundary.phase2_started", True),
            ("stage_and_phase_boundary.phase3_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage073_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage072.embedding_model_version.phase3.v1"),
            ("contract_state", "PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE072-P3"),
            ("next_gate", "IDS-STAGE072-P4-GATE"),
            ("scenario_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("phase2_control_slice_replay_contract.required_execution_state", P2_STATE),
            ("phase2_control_slice_replay_contract.control_request_count", 5),
            ("phase2_control_slice_replay_contract.policy_resolution_record_field_count", 10),
            ("phase2_control_slice_replay_contract.embedding_queue_record_field_count", 14),
            ("phase2_control_slice_replay_contract.cache_record_field_count", 10),
            ("phase2_control_slice_replay_contract.failed_retry_record_field_count", 7),
            ("phase2_control_slice_replay_contract.model_version_projection_field_count", 6),
            ("phase2_control_slice_replay_contract.cost_projection_field_count", 8),
            ("phase2_control_slice_replay_contract.external_api_audit_projection_field_count", 18),
            ("controlled_scenario_contract.field_count", 35),
            ("controlled_scenario_contract.scenario_count", 5),
            ("controlled_scenario_contract.silent_drop_allowed", False),
            ("audit_projection_invariant_contract.control_audit_field_check_count", 90),
            ("audit_projection_invariant_contract.future_external_api_call_candidate_count", 3),
            ("failure_and_stop_contract.failure_state_count", 11),
            ("stage_and_phase_boundary.phase3_started", True),
            ("stage_and_phase_boundary.phase4_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage073_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage072.embedding_model_version.phase4.v1"),
            ("contract_state", RETURN_STATE),
            ("task_id", "IDS-V0_1-STAGE072-P4"),
            ("next_gate", REVIEW_GATE),
            ("delivery_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("phase3_controlled_scenario_replay_contract.scenario_count", 5),
            ("phase3_controlled_scenario_replay_contract.scenario_field_count", 35),
            ("phase3_controlled_scenario_replay_contract.audit_field_check_count", 90),
            ("delivery_evidence_contract.policy_sample_count", 5),
            ("delivery_evidence_contract.control_audit_log_sample_count", 5),
            ("delivery_evidence_contract.control_audit_projection_field_count", 18),
            ("delivery_evidence_contract.control_audit_field_check_count", 90),
            ("delivery_evidence_contract.zero_cost_estimate_sample_count", 5),
            ("delivery_evidence_contract.failure_handling_result_count", 5),
            ("delivery_evidence_contract.non_externalized_data_record_count", 5),
            ("delivery_evidence_contract.externalization_record_query_key_count", 7),
            ("delivery_evidence_contract.chinese_feedback_count", 4),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("authority_and_decision_boundary.source_document_remains_authoritative", True),
            ("authority_and_decision_boundary.delivery_control_metadata_can_replace_source_document", False),
            ("authority_and_decision_boundary.delivery_control_metadata_can_become_business_fact_authority", False),
            ("stage_and_phase_boundary.phase4_started", True),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage073_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _phase2_report_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("schema_version") == "ids.stage072.embedding_model_version.phase2.v1",
            report.get("record_kind") == "CONTROL_ONLY_IN_MEMORY_EMBEDDING_MODEL_VERSION",
            report.get("input_accepted") is True,
            report.get("execution_state") == P2_STATE,
            report.get("control_request_count") == 5,
            report.get("actual_input_request_count") == 0,
            report.get("policy_resolution_count") == 5,
            report.get("embedding_queue_record_count") == 5,
            report.get("cache_record_count") == 5,
            report.get("failed_retry_record_count") == 5,
            report.get("model_version_control_projection_count") == 5,
            report.get("cost_control_projection_count") == 5,
            report.get("external_api_audit_projection_count") == 5,
            report.get("all_chunks_inherit_effective_document_policy_automatically") is True,
            report.get("chunk_manual_policy_assignment_performed") is False,
            report.get("control_output_is_not_actual_queue_cache_model_version_cost_or_audit") is True,
            report.get("source_body_summary_body_or_chunk_text_retained") is False,
            _record_shapes(report, P2_RECORD_SHAPES, 5),
            _all_false(report, P2_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _sequence(report.get("scenario_results"))
    return all(
        (
            report.get("schema_version")
            == "ids.stage072.embedding_model_version.phase3.controlled_scenarios.v1",
            report.get("record_kind") == "CONTROLLED_EMBEDDING_MODEL_VERSION_SCENARIO_REPORT",
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("next_gate") == "IDS-STAGE072-P4-GATE",
            report.get("phase2_control_slice_reexecuted") is True,
            report.get("phase2_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("scenario_count") == 5,
            report.get("passed_scenario_count") == 5,
            report.get("explicit_disposition_count") == 5,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 4,
            report.get("control_audit_field_count") == 18,
            report.get("control_audit_field_check_count") == 90,
            report.get("future_external_api_call_candidate_count") == 3,
            report.get("future_external_api_call_audit_invariant_preserved") is True,
            report.get("policy_payload_boundaries_preserved") is True,
            report.get("queue_cache_retry_boundaries_preserved") is True,
            report.get("budget_insufficient_pause_preserved") is True,
            len(scenarios) == 5,
            all(len(item) == 35 for item in scenarios),
            all(item.get("expectation_met") is True for item in scenarios),
            all(item.get("silent_drop") is False for item in scenarios),
            _all_zero(
                report,
                (
                    "actual_cache_entry_count",
                    "actual_cost_count",
                    "actual_embedding_queue_count",
                    "actual_external_api_audit_record_count",
                    "actual_external_api_call_count",
                    "actual_failed_retry_count",
                    "actual_input_request_count",
                    "actual_model_token_count",
                    "actual_model_version_record_count",
                ),
            ),
            _all_false(report, P3_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    query = _mapping(report.get("externalization_record_query_instructions"))
    rollback = _mapping(report.get("policy_rollback_instructions"))
    return all(
        (
            report.get("schema_version") == "ids.stage072.embedding_model_version.phase4.delivery.v1",
            report.get("record_kind") == "EMBEDDING_MODEL_VERSION_DELIVERY_EVIDENCE_REPORT",
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("entry_gate") == "IDS-STAGE072-P4-GATE",
            report.get("next_gate") == REVIEW_GATE,
            report.get("phase3_controlled_scenarios_reused_as_reference_only") is True,
            report.get("phase3_controlled_scenarios_report_valid") is True,
            report.get("phase2_control_slice_reexecuted_in_memory_only") is True,
            report.get("source_document_remains_authoritative") is True,
            report.get("business_line_white_box_human_review_remains_authoritative")
            is True,
            report.get("delivery_control_metadata_can_replace_source_document") is False,
            report.get("delivery_control_metadata_can_become_business_fact_authority")
            is False,
            report.get("real_source_content_retained") is False,
            report.get("policy_sample_count") == 5,
            report.get("control_audit_log_sample_count") == 5,
            report.get("control_audit_field_count") == 18,
            report.get("control_audit_field_check_count") == 90,
            report.get("zero_cost_estimate_sample_count") == 5,
            report.get("failure_handling_result_count") == 5,
            report.get("non_externalized_data_record_count") == 5,
            report.get("future_external_api_call_candidate_count") == 3,
            report.get("policy_denied_sample_count") == 1,
            report.get("budget_pause_sample_count") == 1,
            len(_values(query.get("supported_query_keys"))) == 7,
            rollback.get("rollback_target_result") == P3_PASS_RESULT,
            rollback.get("actual_policy_rollback_performed") is False,
            _record_shapes(report, P4_RECORD_SHAPES, 5),
            _all_zero(
                report,
                (
                    "actual_cache_entry_count",
                    "actual_cost_count",
                    "actual_embedding_queue_count",
                    "actual_external_api_audit_log_count",
                    "actual_external_api_call_count",
                    "actual_external_payload_count",
                    "actual_failed_retry_count",
                    "actual_failure_record_count",
                    "actual_input_request_count",
                    "actual_model_token_count",
                    "actual_non_externalized_data_record_count",
                ),
            ),
            _all_false(report, P4_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> dict[str, int]:
    scenarios = _sequence(phase3_report.get("scenario_results"))
    query = _mapping(phase4_report.get("externalization_record_query_instructions"))
    return {
        "phase1_model_version_field_count": _int_at(
            phase1, "model_version_record_contract.field_count"
        ),
        "phase1_policy_inheritance_hop_count": _int_at(
            phase1, "policy_inheritance_dependency.inheritance_hop_count"
        ),
        "phase1_future_queue_field_count": _int_at(
            phase1, "queue_cost_and_audit_dependency.future_queue_field_count"
        ),
        "phase1_future_cache_field_count": _int_at(
            phase1, "queue_cost_and_audit_dependency.future_cache_field_count"
        ),
        "phase1_future_retry_field_count": _int_at(
            phase1, "queue_cost_and_audit_dependency.future_failed_retry_field_count"
        ),
        "phase1_future_cost_field_count": _int_at(
            phase1, "queue_cost_and_audit_dependency.future_cost_and_model_field_count"
        ),
        "phase1_future_audit_field_count": _int_at(
            phase1, "queue_cost_and_audit_dependency.future_external_api_audit_field_count"
        ),
        "phase1_failure_state_count": _int_at(
            phase1, "failure_and_stop_contract.failure_state_count"
        ),
        "phase2_control_request_count": _int_at(
            phase2, "reference_only_embedding_model_version_input_control_contract.control_request_count"
        ),
        "phase2_policy_record_count": int(phase2_report.get("policy_resolution_count", -1)),
        "phase2_policy_record_field_count": _record_field_count(
            phase2_report, "policy_resolutions"
        ),
        "phase2_queue_record_count": int(
            phase2_report.get("embedding_queue_record_count", -1)
        ),
        "phase2_queue_record_field_count": _record_field_count(
            phase2_report, "embedding_queue_records"
        ),
        "phase2_cache_record_count": int(phase2_report.get("cache_record_count", -1)),
        "phase2_cache_record_field_count": _record_field_count(
            phase2_report, "cache_records"
        ),
        "phase2_retry_record_count": int(
            phase2_report.get("failed_retry_record_count", -1)
        ),
        "phase2_retry_record_field_count": _record_field_count(
            phase2_report, "failed_retry_records"
        ),
        "phase2_model_record_count": int(
            phase2_report.get("model_version_control_projection_count", -1)
        ),
        "phase2_model_record_field_count": _record_field_count(
            phase2_report, "model_version_control_projections"
        ),
        "phase2_cost_record_count": int(
            phase2_report.get("cost_control_projection_count", -1)
        ),
        "phase2_cost_record_field_count": _record_field_count(
            phase2_report, "cost_control_projections"
        ),
        "phase2_audit_record_count": int(
            phase2_report.get("external_api_audit_projection_count", -1)
        ),
        "phase2_audit_record_field_count": _record_field_count(
            phase2_report, "external_api_audit_projections"
        ),
        "phase3_scenario_count": int(phase3_report.get("scenario_count", -1)),
        "phase3_scenario_field_count": _record_field_count(
            phase3_report, "scenario_results"
        ),
        "phase3_explicit_disposition_count": int(
            phase3_report.get("explicit_disposition_count", -1)
        ),
        "phase3_silent_drop_count": int(phase3_report.get("silent_drop_count", -1)),
        "phase3_human_handling_required_count": int(
            phase3_report.get("human_handling_required_count", -1)
        ),
        "phase3_audit_field_check_count": int(
            phase3_report.get("control_audit_field_check_count", -1)
        ),
        "phase3_future_call_candidate_count": int(
            phase3_report.get("future_external_api_call_candidate_count", -1)
        ),
        "phase3_denied_count": _scenario_category_count(
            scenarios, "DENIED_EGRESS_BLOCK_CONTROL"
        ),
        "phase3_summary_only_count": _scenario_category_count(
            scenarios, "SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL"
        ),
        "phase3_document_restriction_count": _scenario_category_count(
            scenarios, "DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL"
        ),
        "phase3_full_text_count": _scenario_category_count(
            scenarios, "FULL_TEXT_REFERENCE_BOUNDARY_CONTROL"
        ),
        "phase3_budget_pause_count": _scenario_category_count(
            scenarios, "BUDGET_INSUFFICIENT_PAUSE_CONTROL"
        ),
        "phase4_policy_sample_count": int(phase4_report.get("policy_sample_count", -1)),
        "phase4_audit_sample_count": int(
            phase4_report.get("control_audit_log_sample_count", -1)
        ),
        "phase4_audit_field_check_count": int(
            phase4_report.get("control_audit_field_check_count", -1)
        ),
        "phase4_cost_sample_count": int(
            phase4_report.get("zero_cost_estimate_sample_count", -1)
        ),
        "phase4_failure_handling_count": int(
            phase4_report.get("failure_handling_result_count", -1)
        ),
        "phase4_non_externalized_record_count": int(
            phase4_report.get("non_externalized_data_record_count", -1)
        ),
        "phase4_query_key_count": len(_values(query.get("supported_query_keys"))),
        "phase4_chinese_confirmation_count": len(
            _values(phase4_report.get("human_confirmation_prompts_zh"))
        ),
        "phase4_failure_state_count": _int_at(
            phase4, "failure_and_stop_contract.failure_state_count"
        ),
    }


def _shape_valid(replay: Mapping[str, int]) -> bool:
    return replay == {
        "phase1_model_version_field_count": 6,
        "phase1_policy_inheritance_hop_count": 2,
        "phase1_future_queue_field_count": 12,
        "phase1_future_cache_field_count": 10,
        "phase1_future_retry_field_count": 7,
        "phase1_future_cost_field_count": 8,
        "phase1_future_audit_field_count": 18,
        "phase1_failure_state_count": 9,
        "phase2_control_request_count": 5,
        "phase2_policy_record_count": 5,
        "phase2_policy_record_field_count": 10,
        "phase2_queue_record_count": 5,
        "phase2_queue_record_field_count": 14,
        "phase2_cache_record_count": 5,
        "phase2_cache_record_field_count": 10,
        "phase2_retry_record_count": 5,
        "phase2_retry_record_field_count": 7,
        "phase2_model_record_count": 5,
        "phase2_model_record_field_count": 6,
        "phase2_cost_record_count": 5,
        "phase2_cost_record_field_count": 8,
        "phase2_audit_record_count": 5,
        "phase2_audit_record_field_count": 18,
        "phase3_scenario_count": 5,
        "phase3_scenario_field_count": 35,
        "phase3_explicit_disposition_count": 5,
        "phase3_silent_drop_count": 0,
        "phase3_human_handling_required_count": 4,
        "phase3_audit_field_check_count": 90,
        "phase3_future_call_candidate_count": 3,
        "phase3_denied_count": 1,
        "phase3_summary_only_count": 1,
        "phase3_document_restriction_count": 1,
        "phase3_full_text_count": 1,
        "phase3_budget_pause_count": 1,
        "phase4_policy_sample_count": 5,
        "phase4_audit_sample_count": 5,
        "phase4_audit_field_check_count": 90,
        "phase4_cost_sample_count": 5,
        "phase4_failure_handling_count": 5,
        "phase4_non_externalized_record_count": 5,
        "phase4_query_key_count": 7,
        "phase4_chinese_confirmation_count": 4,
        "phase4_failure_state_count": 12,
    }


def _single_authority(*artifacts: Mapping[str, Any]) -> bool:
    contract_authority = all(
        _get(artifact, "source_authority.second_authoritative_source_created") is False
        and _get(artifact, "source_authority.source_body_or_path_allowed") is False
        for artifact in artifacts[:4]
    )
    report_authority = (
        artifacts[4].get("source_document_remains_authoritative") is True
        and artifacts[4].get("embedding_model_version_scenario_can_replace_source_document")
        is False
        and artifacts[4].get(
            "embedding_model_version_scenario_can_become_business_fact_authority"
        )
        is False
        and artifacts[5].get("source_document_remains_authoritative") is True
        and artifacts[5].get(
            "delivery_control_metadata_can_replace_source_document"
        )
        is False
        and artifacts[5].get(
            "delivery_control_metadata_can_become_business_fact_authority"
        )
        is False
    )
    return contract_authority and report_authority


def _policy_and_audit_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "policy_inheritance_dependency.default_external_api_policy")
            == "denied",
            _get(phase1, "policy_inheritance_dependency.document_may_widen_data_source_policy")
            is False,
            _get(
                phase1,
                "policy_inheritance_dependency.chunk_inherits_effective_document_policy_automatically",
            )
            is True,
            _get(phase2, "unauthorized_chunk_egress_control_contract.default_denied_blocks_external_payload")
            is True,
            _get(phase2, "unauthorized_chunk_egress_control_contract.summary_only_blocks_chunk_text")
            is True,
            phase3_report.get("policy_payload_boundaries_preserved") is True,
            phase3_report.get("audit_projection_invariant_preserved") is True,
            phase4_report.get("control_audit_field_count") == 18,
            phase4_report.get("control_audit_field_check_count") == 90,
        )
    )


def _future_call_boundary(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    return all(
        (
            phase3_report.get("future_external_api_call_candidate_count") == 3,
            phase3_report.get("future_external_api_call_audit_invariant_preserved")
            is True,
            phase3_report.get("human_handling_required_count") == 4,
            phase4_report.get("future_external_api_call_candidate_count") == 3,
            phase4_report.get(
                "business_line_white_box_human_review_remains_authoritative"
            )
            is True,
        )
    )


def _delivery_boundary(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("real_source_content_retained") is False,
            report.get("actual_delivery_file_written") is False,
            report.get("actual_external_api_call_count") == 0,
            report.get("actual_model_token_count") == 0,
            report.get("actual_external_api_audit_log_count") == 0,
        )
    )


def _rollback_chain(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    rollback = _mapping(phase4_report.get("policy_rollback_instructions"))
    return all(
        (
            _get(phase1, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase2, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase3, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase4, "rollback_contract.return_to") == P3_PASS_RESULT,
            rollback.get("rollback_target_result") == P3_PASS_RESULT,
            rollback.get("actual_policy_rollback_performed") is False,
            rollback.get("github_or_ovh_change_allowed") is False,
        )
    )


def _future_stage_boundary(*contracts: Mapping[str, Any]) -> bool:
    return all(
        (
            _get(contract, "stage_and_phase_boundary.stage073_started") is False,
            _get(contract, "stage_and_phase_boundary.github_upload_allowed") is False,
            _get(contract, "stage_and_phase_boundary.push_allowed") is False,
        )
        for contract in contracts
    )


def _runtime_closed(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _runtime_boundary_closed(_mapping(phase1.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase2.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase3.get("runtime_boundary"))),
            _runtime_boundary_closed(_mapping(phase4.get("runtime_boundary"))),
            _all_false(phase2_report, P2_REPORT_RUNTIME_FALSE_FIELDS),
            _all_false(phase3_report, P3_REPORT_RUNTIME_FALSE_FIELDS),
            _all_false(phase4_report, P4_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _phase2_report_provider() -> ReportProvider:
    module = _load_module("stage072_embedding_model_version_slice.py")
    return lambda: _mapping(
        module.execute_embedding_model_version_control_slice(module.build_control_input())
    )


def _report_provider(filename: str, function_name: str) -> ReportProvider:
    module = _load_module(filename)
    function = getattr(module, function_name)
    return lambda: _mapping(function())


def _json_provider(path: Path) -> ContractProvider:
    return lambda: _mapping(json.loads(path.read_text(encoding="utf-8")))


def _load_module(filename: str) -> Any:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage072_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load controlled review dependency: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checks(value: Mapping[str, Any], expected: Sequence[tuple[str, Any]]) -> bool:
    return all(_get(value, path) == expected_value for path, expected_value in expected)


def _get(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _int_at(value: Mapping[str, Any], path: str) -> int:
    item = _get(value, path)
    return item if isinstance(item, int) else -1


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


def _values(value: object) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


def _record_shapes(
    report: Mapping[str, Any], expected_shapes: Mapping[str, int], expected_count: int
) -> bool:
    return all(
        len(records := _sequence(report.get(name))) == expected_count
        and all(len(record) == field_count for record in records)
        for name, field_count in expected_shapes.items()
    )


def _record_field_count(report: Mapping[str, Any], name: str) -> int:
    records = _sequence(report.get(name))
    return len(records[0]) if len(records) == 5 and all(len(item) == len(records[0]) for item in records) else -1


def _scenario_category_count(
    scenarios: Sequence[Mapping[str, Any]], category: str
) -> int:
    return sum(item.get("scenario_category") == category for item in scenarios)


def _all_false(value: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(value.get(field) is False for field in fields)


def _all_zero(value: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(value.get(field) == 0 for field in fields)


def _runtime_boundary_closed(boundary: Mapping[str, Any]) -> bool:
    return bool(boundary) and all(value is False for value in boundary.values())
