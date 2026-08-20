"""Stage071 的只读整阶段机械复审，不读取真实资料或启动 Stage072。"""

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
    / "STAGE-071_Embedding成本治理器.md"
)
P1_CONTRACT = BASE / "stage071_embedding_cost_governor_contract.json"
P2_CONTRACT = BASE / "stage071_embedding_cost_governor_slice_contract.json"
P3_CONTRACT = BASE / "stage071_embedding_cost_governor_scenarios_contract.json"
P4_CONTRACT = BASE / "stage071_embedding_cost_governor_delivery_contract.json"

SCHEMA_VERSION = "ids.stage071.embedding_cost_governor.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE071-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-071"
PASS_RESULT = "PASS_REVIEWED_LOCAL_EMBEDDING_COST_GOVERNOR_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_EMBEDDING_COST_GOVERNOR_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE071-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE072-P1-GATE"
RETURN_STATE = "PHASE4_EMBEDDING_COST_GOVERNOR_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED"
P3_PASS_RESULT = "PASS_PHASE3_EMBEDDING_COST_GOVERNOR_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PHASE4_EMBEDDING_COST_GOVERNOR_DELIVERY_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "denied-policy-blocks-cost-governor-queue-cache-retry-and-externalization-control",
    "summary-only-policy-limits-control-payload-after-all-budget-gates-pass",
    "document-restriction-limits-full-text-to-summary-control-after-all-budget-gates-pass",
    "full-text-policy-keeps-only-control-text-reference-after-all-budget-gates-pass",
    "current-batch-budget-insufficient-pauses-full-text-control",
    "monthly-budget-insufficient-pauses-full-text-control",
    "single-task-cap-exceeded-pauses-full-text-control",
)
EXPECTED_PHASE2_SCENARIOS = (
    "default_denied",
    "summary_only_inherited_all_budget_gates_pass",
    "document_restricts_full_text_to_summary_only_all_budget_gates_pass",
    "full_text_allowed_all_budget_gates_pass",
    "current_batch_budget_insufficient_pauses_full_text",
    "monthly_budget_insufficient_pauses_full_text",
    "single_task_cap_exceeded_pauses_full_text",
)
AUDIT_PROJECTION_FIELDS = (
    "external_api_audit_ref",
    "data_source_ref",
    "document_ref",
    "chunk_ref",
    "effective_external_api_policy",
    "external_payload_mode",
    "policy_inheritance_reason",
    "owner_authorization_ref",
    "authorized_at",
    "authorization_reason",
    "provider_ref",
    "model_ref",
    "model_version",
    "token_count",
    "cost_estimate",
    "embedding_queue_request_ref",
    "budget_check_state",
    "audit_disposition",
)

P2_REPORT_RUNTIME_FALSE_FIELDS = (
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_batch_budget_lookup_performed",
    "actual_monthly_budget_lookup_performed",
    "actual_task_cap_evaluation_performed",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "external_payload_created",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
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
P3_REPORT_RUNTIME_FALSE_FIELDS = (
    "authorized_fixture_access_performed",
    "actual_external_payload_created",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_batch_budget_lookup_performed",
    "actual_monthly_budget_lookup_performed",
    "actual_task_cap_evaluation_performed",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "external_payload_created",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
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
    "phase4_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "stage072_started",
    "github_upload_allowed",
    "push_allowed",
)
P4_REPORT_RUNTIME_FALSE_FIELDS = (
    "authorized_fixture_access_performed",
    "actual_external_payload_created",
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_batch_budget_lookup_performed",
    "actual_monthly_budget_lookup_performed",
    "actual_task_cap_evaluation_performed",
    "actual_model_version_recorded",
    "actual_external_api_audit_record_created",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "external_payload_created",
    "embedding_queue_execution_performed",
    "cache_read_or_write_performed",
    "failed_retry_execution_performed",
    "provider_credential_read_performed",
    "provider_or_model_selected",
    "external_api_client_initialized",
    "external_api_call_performed",
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
    "actual_audit_log_query_performed",
    "actual_externalization_record_query_performed",
    "actual_policy_rollback_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "stage072_started",
    "github_upload_allowed",
    "push_allowed",
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
    "batch_budget_lookup_performed",
    "monthly_budget_lookup_performed",
    "task_cap_evaluation_performed",
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
    "stage072_started",
    "batch_review_performed",
    "github_upload_performed",
    "github_upload_allowed",
    "push_performed",
    "push_allowed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]
MISSING = object()


def build_stage071_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage071 P1--P4，只输出本地控制结论、门禁与回退范围。"""

    phase1 = _mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    phase2_report = _mapping(
        (phase2_report_provider or _load_phase2_report_provider())()
    )
    phase3_report = _mapping(
        (phase3_report_provider or _load_report_provider(
            "stage071_embedding_cost_governor_scenarios.py",
            "build_embedding_cost_governor_phase3_report",
        ))()
    )
    phase4_report = _mapping(
        (phase4_report_provider or _load_report_provider(
            "stage071_embedding_cost_governor_delivery.py",
            "build_embedding_cost_governor_phase4_delivery_report",
        ))()
    )
    phase_results = {
        "P1": _p1_valid(phase1),
        "P2": _p2_contract_valid(phase2) and _p2_report_valid(phase2_report),
        "P3": _p3_contract_valid(phase3) and _p3_report_valid(phase3_report),
        "P4": _p4_contract_valid(phase4) and _p4_report_valid(phase4_report),
    }
    replay = _controlled_replay(
        phase1, phase2, phase3, phase4, phase2_report, phase3_report, phase4_report
    )
    invariants = {
        "frozen_taskpack_available": TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "policy_default_denied_and_three_budget_pauses_preserved": _policy_and_budget(
            phase1, phase2, phase2_report, phase3_report, phase4_report
        ),
        "cost_queue_cache_retry_control_shape_preserved": _shape_valid(replay),
        "future_external_calls_require_audit_and_whitebox_handling": _audit_and_human_boundary(
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
        "source_authority": "FROZEN_STAGE071_TASKPACK_AND_STAGE071_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
                "Stage071 review document",
                "Stage071 review module",
                "Stage071 review focused tests",
                "Stage071 review governance projection",
            ),
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "audit_log_change_allowed": False,
            "queue_cache_or_cost_governor_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": REVIEW_GATE,
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "actual_policy_resolution_record_created": False,
        "actual_embedding_queue_request_created": False,
        "actual_cache_entry_created": False,
        "actual_failed_retry_record_created": False,
        "actual_cost_governor_record_created": False,
        "actual_external_api_audit_log_created": False,
        "actual_delivery_file_written": False,
        "stage071_started": True,
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
                "actual_policy_resolution_record_created",
                "actual_embedding_queue_request_created",
                "actual_cache_entry_created",
                "actual_failed_retry_record_created",
                "actual_cost_governor_record_created",
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


def _p1_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage071.embedding_cost_governor.phase1.v1"),
            ("contract_state", "PHASE1_EMBEDDING_COST_GOVERNOR_CONTRACT_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE071-P1"),
            ("next_gate", "IDS-STAGE071-P2-GATE"),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("policy_inheritance_dependency.default_external_api_policy", "denied"),
            ("policy_inheritance_dependency.allowed_value_count", 3),
            ("policy_inheritance_dependency.document_may_widen_data_source_policy", False),
            ("policy_inheritance_dependency.chunk_inherits_effective_document_policy_automatically", True),
            ("reference_only_cost_governor_input_contract.field_count", 16),
            ("reference_only_cost_governor_input_contract.actual_input_request_count", 0),
            ("future_cost_governor_contract.field_count", 16),
            ("future_cost_governor_contract.budget_scope_count", 3),
            ("future_cost_governor_contract.all_budget_scopes_must_pass_before_future_queue", True),
            ("future_cost_and_model_dependency.field_count", 8),
            ("future_external_api_audit_dependency.field_count", 18),
            ("failure_and_stop_contract.failure_state_count", 14),
            ("stage_and_phase_boundary.phase1_started", True),
            ("stage_and_phase_boundary.phase2_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage072_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p2_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage071.embedding_cost_governor.phase2.v1"),
            ("contract_state", "PHASE2_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE071-P2"),
            ("next_gate", "IDS-STAGE071-P3-GATE"),
            ("slice_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("reference_only_cost_governor_input_control_contract.field_count", 16),
            ("reference_only_cost_governor_input_control_contract.control_request_count", 7),
            ("policy_inheritance_control_contract.default_external_api_policy", "denied"),
            ("policy_inheritance_control_contract.allowed_external_api_policy_values", ["denied", "summary_only", "full_text_allowed"]),
            ("policy_inheritance_control_contract.document_may_widen_data_source_policy", False),
            ("policy_inheritance_control_contract.chunk_inherits_effective_document_policy_automatically", True),
            ("embedding_queue_cache_retry_control_contract.future_queue_field_count", 12),
            ("embedding_queue_cache_retry_control_contract.future_cache_field_count", 10),
            ("embedding_queue_cache_retry_control_contract.future_retry_field_count", 7),
            ("embedding_queue_cache_retry_control_contract.control_projection_count", 7),
            ("cost_governor_control_contract.field_count", 16),
            ("cost_governor_control_contract.budget_scope_count", 3),
            ("cost_governor_control_contract.control_projection_count", 7),
            ("external_api_audit_control_contract.field_count", 18),
            ("external_api_audit_control_contract.control_projection_count", 7),
            ("failure_and_stop_contract.failure_state_count", 11),
            ("stage_and_phase_boundary.phase2_started", True),
            ("stage_and_phase_boundary.phase3_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage072_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage071.embedding_cost_governor.phase3.v1"),
            ("contract_state", "PHASE3_EMBEDDING_COST_GOVERNOR_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE071-P3"),
            ("next_gate", "IDS-STAGE071-P4-GATE"),
            ("scenario_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("phase2_control_slice_replay_contract.required_execution_state", "COMPLETED_IN_MEMORY_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE"),
            ("phase2_control_slice_replay_contract.control_request_count", 7),
            ("phase2_control_slice_replay_contract.policy_resolution_record_count", 7),
            ("phase2_control_slice_replay_contract.policy_resolution_record_field_count", 10),
            ("phase2_control_slice_replay_contract.cost_governor_record_count", 7),
            ("phase2_control_slice_replay_contract.cost_governor_record_field_count", 18),
            ("phase2_control_slice_replay_contract.embedding_queue_record_count", 7),
            ("phase2_control_slice_replay_contract.embedding_queue_record_field_count", 14),
            ("phase2_control_slice_replay_contract.cache_record_count", 7),
            ("phase2_control_slice_replay_contract.cache_record_field_count", 10),
            ("phase2_control_slice_replay_contract.failed_retry_record_count", 7),
            ("phase2_control_slice_replay_contract.failed_retry_record_field_count", 7),
            ("phase2_control_slice_replay_contract.external_api_audit_projection_count", 7),
            ("phase2_control_slice_replay_contract.external_api_audit_projection_field_count", 18),
            ("controlled_scenario_contract.field_count", 35),
            ("controlled_scenario_contract.scenario_count", 7),
            ("controlled_scenario_contract.silent_drop_allowed", False),
            ("externalization_policy_validation_contract.denied_no_external_payload_count", 1),
            ("externalization_policy_validation_contract.summary_only_control_summary_reference_count", 2),
            ("externalization_policy_validation_contract.full_text_allowed_control_chunk_text_reference_count", 1),
            ("externalization_policy_validation_contract.three_budget_scope_pause_count", 3),
            ("audit_projection_invariant_contract.inherited_phase2_audit_field_count", 18),
            ("audit_projection_invariant_contract.control_audit_projection_count", 7),
            ("audit_projection_invariant_contract.control_audit_field_check_count", 126),
            ("audit_projection_invariant_contract.future_external_api_call_candidate_count", 3),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("stage_and_phase_boundary.phase3_started", True),
            ("stage_and_phase_boundary.phase4_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage072_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage071.embedding_cost_governor.phase4.v1"),
            ("contract_state", RETURN_STATE),
            ("task_id", "IDS-V0_1-STAGE071-P4"),
            ("next_gate", REVIEW_GATE),
            ("delivery_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("source_authority.raw_metadata_content_access_allowed", False),
            ("phase3_controlled_scenario_replay_contract.required_phase3_result", P3_PASS_RESULT),
            ("phase3_controlled_scenario_replay_contract.scenario_count", 7),
            ("phase3_controlled_scenario_replay_contract.scenario_field_count", 35),
            ("phase3_controlled_scenario_replay_contract.policy_resolution_record_count", 7),
            ("phase3_controlled_scenario_replay_contract.cost_governor_record_count", 7),
            ("phase3_controlled_scenario_replay_contract.embedding_queue_record_count", 7),
            ("phase3_controlled_scenario_replay_contract.cache_record_count", 7),
            ("phase3_controlled_scenario_replay_contract.failed_retry_record_count", 7),
            ("phase3_controlled_scenario_replay_contract.external_api_audit_projection_count", 7),
            ("phase3_controlled_scenario_replay_contract.external_api_audit_projection_field_count", 18),
            ("phase3_controlled_scenario_replay_contract.future_external_api_call_candidate_count", 3),
            ("phase3_controlled_scenario_replay_contract.three_budget_scope_pause_count", 3),
            ("delivery_evidence_contract.policy_sample_count", 7),
            ("delivery_evidence_contract.control_audit_log_sample_count", 7),
            ("delivery_evidence_contract.control_audit_projection_field_count", 18),
            ("delivery_evidence_contract.control_audit_field_check_count", 126),
            ("delivery_evidence_contract.zero_cost_estimate_sample_count", 7),
            ("delivery_evidence_contract.failure_handling_result_count", 7),
            ("delivery_evidence_contract.non_externalized_data_record_count", 7),
            ("delivery_evidence_contract.human_confirmation_prompt_count", 4),
            ("externalization_and_budget_contract.denied_policy_sample_count", 1),
            ("externalization_and_budget_contract.current_batch_budget_pause_sample_count", 1),
            ("externalization_and_budget_contract.monthly_budget_pause_sample_count", 1),
            ("externalization_and_budget_contract.single_task_cap_pause_sample_count", 1),
            ("externalization_and_budget_contract.actual_external_api_call_performed", False),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("authority_and_decision_boundary.source_document_remains_authoritative", True),
            ("authority_and_decision_boundary.delivery_control_metadata_can_replace_source_document", False),
            ("authority_and_decision_boundary.delivery_control_metadata_can_become_business_fact_authority", False),
            ("stage_and_phase_boundary.phase4_started", True),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage072_started", False),
        ),
    ) and _runtime_boundary_closed(_mapping(contract.get("runtime_boundary")))


def _p2_report_valid(report: Mapping[str, Any]) -> bool:
    resolutions = _sequence(report.get("policy_resolutions"))
    cost_records = _sequence(report.get("cost_governor_records"))
    queue_records = _sequence(report.get("embedding_queue_records"))
    cache_records = _sequence(report.get("cache_records"))
    retry_records = _sequence(report.get("failed_retry_records"))
    audit_records = _sequence(report.get("external_api_audit_projections"))
    return all(
        (
            report.get("schema_version") == "ids.stage071.embedding_cost_governor.phase2.v1",
            report.get("record_kind") == "CONTROL_ONLY_IN_MEMORY_EMBEDDING_COST_GOVERNOR",
            report.get("input_accepted") is True,
            report.get("execution_state") == "COMPLETED_IN_MEMORY_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE",
            report.get("control_request_count") == 7,
            report.get("actual_input_request_count") == 0,
            tuple(report.get("control_scenarios_covered", ())) == EXPECTED_PHASE2_SCENARIOS,
            report.get("policy_resolution_count") == 7,
            len(resolutions) == 7,
            all(len(_mapping(item)) == 10 for item in resolutions),
            report.get("all_chunks_inherit_effective_document_policy_automatically") is True,
            report.get("chunk_manual_policy_assignment_performed") is False,
            report.get("cost_governor_record_count") == 7,
            len(cost_records) == 7,
            all(len(_mapping(item)) == 18 for item in cost_records),
            report.get("embedding_queue_record_count") == 7,
            len(queue_records) == 7,
            all(len(_mapping(item)) == 14 for item in queue_records),
            report.get("cache_record_count") == 7,
            len(cache_records) == 7,
            all(len(_mapping(item)) == 10 for item in cache_records),
            report.get("failed_retry_record_count") == 7,
            len(retry_records) == 7,
            all(len(_mapping(item)) == 7 for item in retry_records),
            report.get("external_api_audit_projection_count") == 7,
            len(audit_records) == 7,
            all(set(_mapping(item)) == set(AUDIT_PROJECTION_FIELDS) for item in audit_records),
            report.get("control_cost_governor_blocked_policy_denied_count") == 1,
            report.get("control_cost_governor_paused_three_budget_gates_count") == 3,
            report.get("control_cost_governor_eligible_not_persisted_count") == 3,
            report.get("all_control_records_keep_required_shapes") is True,
            report.get("all_three_budget_scope_failure_closures_covered") is True,
            report.get("source_body_summary_body_or_chunk_text_retained") is False,
            report.get("control_output_is_not_actual_queue_cache_retry_cost_or_audit") is True,
            _all_false(report, P2_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _p3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _sequence(report.get("scenario_results"))
    return all(
        (
            report.get("schema_version") == "ids.stage071.embedding_cost_governor.phase3.controlled_scenarios.v1",
            report.get("record_kind") == "CONTROLLED_EMBEDDING_COST_GOVERNOR_SCENARIO_REPORT",
            report.get("phase2_control_slice_reexecuted") is True,
            report.get("phase2_shape_preserved") is True,
            report.get("phase2_side_effect_free") is True,
            report.get("scenario_count") == 7,
            report.get("passed_scenario_count") == 7,
            report.get("explicit_disposition_count") == 7,
            report.get("silent_drop_count") == 0,
            report.get("human_handling_required_count") == 6,
            report.get("all_taskpack_special_scenarios_covered") is True,
            len(scenarios) == 7,
            tuple(_mapping(item).get("scenario_id") for item in scenarios)
            == EXPECTED_SCENARIO_IDS,
            all(len(_mapping(item)) == 35 for item in scenarios),
            all(_mapping(item).get("expectation_met") is True for item in scenarios),
            all(_mapping(item).get("silent_drop") is False for item in scenarios),
            report.get("control_policy_resolution_record_count") == 7,
            report.get("control_cost_governor_record_count") == 7,
            report.get("control_embedding_queue_record_count") == 7,
            report.get("control_cache_record_count") == 7,
            report.get("control_failed_retry_record_count") == 7,
            report.get("control_external_api_audit_projection_count") == 7,
            report.get("control_audit_field_count") == 18,
            report.get("control_audit_field_check_count") == 126,
            report.get("audit_projection_required_count") == 7,
            report.get("audit_projection_present_count") == 7,
            report.get("future_external_api_call_candidate_count") == 3,
            report.get("future_external_api_call_audit_invariant_preserved") is True,
            report.get("payload_boundaries_preserved") is True,
            report.get("cost_queue_cache_retry_boundaries_preserved") is True,
            report.get("budget_scope_failure_coverage_preserved") is True,
            report.get("denied_control_blocked_count") == 1,
            report.get("summary_only_control_scope_count") == 2,
            report.get("full_text_control_scope_count") == 1,
            report.get("three_budget_scope_paused_count") == 3,
            report.get("actual_input_request_count") == 0,
            report.get("actual_embedding_queue_count") == 0,
            report.get("actual_cache_entry_count") == 0,
            report.get("actual_failed_retry_count") == 0,
            report.get("actual_external_api_call_count") == 0,
            report.get("actual_model_token_count") == 0,
            report.get("actual_external_api_audit_record_count") == 0,
            report.get("source_document_remains_authoritative") is True,
            report.get("embedding_cost_governor_scenario_can_become_business_fact_authority") is False,
            report.get("valid") is True,
            report.get("result") == P3_PASS_RESULT,
            report.get("next_gate") == "IDS-STAGE071-P4-GATE",
            _all_false(report, P3_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _p4_report_valid(report: Mapping[str, Any]) -> bool:
    policy_samples = _sequence(report.get("embedding_cost_governor_policy_samples"))
    audit_samples = _sequence(report.get("control_audit_log_samples"))
    cost_samples = _sequence(report.get("cost_estimate_samples"))
    failures = _sequence(report.get("failure_handling_results"))
    non_externalized = _sequence(report.get("non_externalized_data_records"))
    prompts = _sequence(report.get("human_confirmation_prompts_zh"))
    return all(
        (
            report.get("schema_version") == "ids.stage071.embedding_cost_governor.phase4.delivery.v1",
            report.get("record_kind") == "EMBEDDING_COST_GOVERNOR_DELIVERY_EVIDENCE_REPORT",
            report.get("entry_gate") == "IDS-STAGE071-P4-GATE",
            report.get("phase3_controlled_scenarios_reused_as_reference_only") is True,
            report.get("phase3_controlled_scenarios_report_valid") is True,
            report.get("phase2_control_slice_reexecuted_in_memory_only") is True,
            report.get("source_document_remains_authoritative") is True,
            report.get("business_line_white_box_human_review_remains_authoritative") is True,
            report.get("delivery_control_metadata_can_replace_source_document") is False,
            report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
            report.get("real_source_content_retained") is False,
            report.get("policy_sample_count") == 7,
            len(policy_samples) == 7,
            tuple(_mapping(item).get("scenario_id") for item in policy_samples)
            == EXPECTED_SCENARIO_IDS,
            report.get("control_audit_log_sample_count") == 7,
            _p4_audit_samples_exact(audit_samples),
            report.get("control_audit_field_count") == 18,
            report.get("control_audit_field_check_count") == 126,
            report.get("zero_cost_estimate_sample_count") == 7,
            len(cost_samples) == 7,
            all(_mapping(item).get("estimated_token_count") == 0 for item in cost_samples),
            all(_mapping(item).get("estimated_cost") == 0 for item in cost_samples),
            report.get("failure_handling_result_count") == 7,
            len(failures) == 7,
            all(_mapping(item).get("failure_closed") is True for item in failures),
            all(_mapping(item).get("actual_failure_record_created") is False for item in failures),
            report.get("non_externalized_data_record_count") == 7,
            len(non_externalized) == 7,
            all(_mapping(item).get("externalization_performed") is False for item in non_externalized),
            len(prompts) == 4,
            all(isinstance(item, str) and item for item in prompts),
            report.get("future_external_api_call_candidate_count") == 3,
            report.get("policy_denied_sample_count") == 1,
            report.get("three_budget_scope_pause_sample_count") == 3,
            report.get("actual_input_request_count") == 0,
            report.get("actual_embedding_queue_count") == 0,
            report.get("actual_cache_entry_count") == 0,
            report.get("actual_failed_retry_count") == 0,
            report.get("actual_external_payload_count") == 0,
            report.get("actual_external_api_call_count") == 0,
            report.get("actual_model_token_count") == 0,
            report.get("actual_cost_count") == 0,
            report.get("actual_external_api_audit_log_count") == 0,
            report.get("actual_failure_record_count") == 0,
            report.get("actual_non_externalized_data_record_count") == 0,
            report.get("valid") is True,
            report.get("result") == P4_PASS_RESULT,
            report.get("next_gate") == REVIEW_GATE,
            _all_false(report, P4_REPORT_RUNTIME_FALSE_FIELDS),
        )
    )


def _p4_audit_samples_exact(samples: Sequence[Any]) -> bool:
    return (
        len(samples) == 7
        and tuple(_mapping(item).get("scenario_id") for item in samples)
        == EXPECTED_SCENARIO_IDS
        and all(
            set(_mapping(item).get("audit_projection", {}))
            == set(AUDIT_PROJECTION_FIELDS)
            and _mapping(item).get("audit_field_count") == 18
            and _mapping(item).get("external_api_audit_ref")
            == _mapping(item).get("audit_projection", {}).get("external_api_audit_ref")
            and _mapping(item).get("embedding_queue_request_ref")
            == _mapping(item).get("audit_projection", {}).get("embedding_queue_request_ref")
            and _mapping(item).get("audit_projection", {}).get("token_count") == 0
            and _mapping(item).get("audit_projection", {}).get("cost_estimate") == 0
            and _mapping(item).get("actual_audit_record_created") is False
            and _mapping(item).get("actual_audit_record_persisted") is False
            for item in samples
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
) -> dict[str, Any]:
    return {
        "phase1_reference_input_field_count": _get(phase1, "reference_only_cost_governor_input_contract.field_count"),
        "phase1_future_cost_governor_field_count": _get(phase1, "future_cost_governor_contract.field_count"),
        "phase1_budget_scope_count": _get(phase1, "future_cost_governor_contract.budget_scope_count"),
        "phase1_future_queue_field_count": _get(phase1, "queue_cache_dependency.future_queue_field_count"),
        "phase1_future_cache_field_count": _get(phase1, "queue_cache_dependency.future_cache_field_count"),
        "phase1_future_retry_field_count": _get(phase1, "queue_cache_dependency.future_failed_retry_field_count"),
        "phase1_future_model_field_count": _get(phase1, "future_cost_and_model_dependency.field_count"),
        "phase1_future_audit_field_count": _get(phase1, "future_external_api_audit_dependency.field_count"),
        "phase1_failure_state_count": _get(phase1, "failure_and_stop_contract.failure_state_count"),
        "phase2_control_request_count": phase2_report.get("control_request_count"),
        "phase2_policy_resolution_count": phase2_report.get("policy_resolution_count"),
        "phase2_policy_resolution_field_count": _get(phase3, "phase2_control_slice_replay_contract.policy_resolution_record_field_count"),
        "phase2_cost_governor_record_count": phase2_report.get("cost_governor_record_count"),
        "phase2_cost_governor_record_field_count": _get(phase3, "phase2_control_slice_replay_contract.cost_governor_record_field_count"),
        "phase2_queue_record_count": phase2_report.get("embedding_queue_record_count"),
        "phase2_queue_record_field_count": _get(phase3, "phase2_control_slice_replay_contract.embedding_queue_record_field_count"),
        "phase2_cache_record_count": phase2_report.get("cache_record_count"),
        "phase2_cache_record_field_count": _get(phase3, "phase2_control_slice_replay_contract.cache_record_field_count"),
        "phase2_retry_record_count": phase2_report.get("failed_retry_record_count"),
        "phase2_retry_record_field_count": _get(phase3, "phase2_control_slice_replay_contract.failed_retry_record_field_count"),
        "phase2_audit_projection_count": phase2_report.get("external_api_audit_projection_count"),
        "phase2_audit_field_count": _get(phase2, "external_api_audit_control_contract.field_count"),
        "phase2_policy_denied_count": phase2_report.get("control_cost_governor_blocked_policy_denied_count"),
        "phase2_three_budget_pause_count": phase2_report.get("control_cost_governor_paused_three_budget_gates_count"),
        "phase2_eligible_not_persisted_count": phase2_report.get("control_cost_governor_eligible_not_persisted_count"),
        "phase3_scenario_count": phase3_report.get("scenario_count"),
        "phase3_scenario_field_count": _get(phase3, "controlled_scenario_contract.field_count"),
        "phase3_explicit_disposition_count": phase3_report.get("explicit_disposition_count"),
        "phase3_silent_drop_count": phase3_report.get("silent_drop_count"),
        "phase3_human_handling_required_count": phase3_report.get("human_handling_required_count"),
        "phase3_audit_field_count": phase3_report.get("control_audit_field_count"),
        "phase3_audit_field_check_count": phase3_report.get("control_audit_field_check_count"),
        "phase3_future_external_api_call_candidate_count": phase3_report.get("future_external_api_call_candidate_count"),
        "phase3_denied_count": phase3_report.get("denied_control_blocked_count"),
        "phase3_summary_only_count": phase3_report.get("summary_only_control_scope_count"),
        "phase3_full_text_control_count": phase3_report.get("full_text_control_scope_count"),
        "phase3_three_budget_pause_count": phase3_report.get("three_budget_scope_paused_count"),
        "phase4_policy_sample_count": len(_sequence(phase4_report.get("embedding_cost_governor_policy_samples"))),
        "phase4_audit_sample_count": len(_sequence(phase4_report.get("control_audit_log_samples"))),
        "phase4_audit_field_count": _get(phase4, "delivery_evidence_contract.control_audit_projection_field_count"),
        "phase4_audit_field_check_count": _get(phase4, "delivery_evidence_contract.control_audit_field_check_count"),
        "phase4_cost_sample_count": len(_sequence(phase4_report.get("cost_estimate_samples"))),
        "phase4_failure_handling_count": len(_sequence(phase4_report.get("failure_handling_results"))),
        "phase4_non_externalized_record_count": len(_sequence(phase4_report.get("non_externalized_data_records"))),
        "phase4_query_key_count": len(_sequence(_get(phase4_report, "externalization_record_query_instructions.supported_query_keys", ()))),
        "phase4_chinese_confirmation_count": len(_sequence(phase4_report.get("human_confirmation_prompts_zh"))),
        "phase4_failure_state_count": _get(phase4, "failure_and_stop_contract.failure_state_count"),
    }


def _shape_valid(replay: Mapping[str, Any]) -> bool:
    expected = {
        "phase1_reference_input_field_count": 16,
        "phase1_future_cost_governor_field_count": 16,
        "phase1_budget_scope_count": 3,
        "phase1_future_queue_field_count": 12,
        "phase1_future_cache_field_count": 10,
        "phase1_future_retry_field_count": 7,
        "phase1_future_model_field_count": 8,
        "phase1_future_audit_field_count": 18,
        "phase1_failure_state_count": 14,
        "phase2_control_request_count": 7,
        "phase2_policy_resolution_count": 7,
        "phase2_policy_resolution_field_count": 10,
        "phase2_cost_governor_record_count": 7,
        "phase2_cost_governor_record_field_count": 18,
        "phase2_queue_record_count": 7,
        "phase2_queue_record_field_count": 14,
        "phase2_cache_record_count": 7,
        "phase2_cache_record_field_count": 10,
        "phase2_retry_record_count": 7,
        "phase2_retry_record_field_count": 7,
        "phase2_audit_projection_count": 7,
        "phase2_audit_field_count": 18,
        "phase2_policy_denied_count": 1,
        "phase2_three_budget_pause_count": 3,
        "phase2_eligible_not_persisted_count": 3,
        "phase3_scenario_count": 7,
        "phase3_scenario_field_count": 35,
        "phase3_explicit_disposition_count": 7,
        "phase3_silent_drop_count": 0,
        "phase3_human_handling_required_count": 6,
        "phase3_audit_field_count": 18,
        "phase3_audit_field_check_count": 126,
        "phase3_future_external_api_call_candidate_count": 3,
        "phase3_denied_count": 1,
        "phase3_summary_only_count": 2,
        "phase3_full_text_control_count": 1,
        "phase3_three_budget_pause_count": 3,
        "phase4_policy_sample_count": 7,
        "phase4_audit_sample_count": 7,
        "phase4_audit_field_count": 18,
        "phase4_audit_field_check_count": 126,
        "phase4_cost_sample_count": 7,
        "phase4_failure_handling_count": 7,
        "phase4_non_externalized_record_count": 7,
        "phase4_query_key_count": 7,
        "phase4_chinese_confirmation_count": 4,
        "phase4_failure_state_count": 12,
    }
    return all(replay.get(key) == value for key, value in expected.items())


def _single_authority(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "source_authority.second_authoritative_source_created") is False,
            _get(phase2, "source_authority.second_authoritative_source_created") is False,
            _get(phase3, "source_authority.second_authoritative_source_created") is False,
            _get(phase4, "source_authority.second_authoritative_source_created") is False,
            _get(phase1, "authority_and_decision_boundary.source_document_remains_authoritative") is True,
            _get(phase2, "authority_and_decision_boundary.source_document_remains_authoritative") is True,
            _get(phase3, "authority_and_decision_boundary.source_document_remains_authoritative") is True,
            _get(phase4, "authority_and_decision_boundary.source_document_remains_authoritative") is True,
            phase3_report.get("source_document_remains_authoritative") is True,
            phase3_report.get("embedding_cost_governor_scenario_can_become_business_fact_authority") is False,
            phase4_report.get("source_document_remains_authoritative") is True,
            phase4_report.get("business_line_white_box_human_review_remains_authoritative") is True,
            phase4_report.get("delivery_control_metadata_can_become_business_fact_authority") is False,
            phase4_report.get("real_source_content_retained") is False,
        )
    )


def _policy_and_budget(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase2_report: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "policy_inheritance_dependency.default_external_api_policy") == "denied",
            _get(phase1, "policy_inheritance_dependency.document_may_widen_data_source_policy") is False,
            _get(phase1, "policy_inheritance_dependency.chunk_inherits_effective_document_policy_automatically") is True,
            _get(phase2, "policy_inheritance_control_contract.default_external_api_policy") == "denied",
            _get(phase2, "policy_inheritance_control_contract.document_may_widen_data_source_policy") is False,
            _get(phase2, "policy_inheritance_control_contract.chunk_inherits_effective_document_policy_automatically") is True,
            phase2_report.get("all_chunks_inherit_effective_document_policy_automatically") is True,
            phase2_report.get("chunk_manual_policy_assignment_performed") is False,
            phase2_report.get("control_cost_governor_blocked_policy_denied_count") == 1,
            phase2_report.get("control_cost_governor_paused_three_budget_gates_count") == 3,
            phase3_report.get("denied_control_blocked_count") == 1,
            phase3_report.get("summary_only_control_scope_count") == 2,
            phase3_report.get("full_text_control_scope_count") == 1,
            phase3_report.get("three_budget_scope_paused_count") == 3,
            phase4_report.get("policy_denied_sample_count") == 1,
            phase4_report.get("three_budget_scope_pause_sample_count") == 3,
        )
    )


def _audit_and_human_boundary(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    policy_samples = _sequence(phase4_report.get("embedding_cost_governor_policy_samples"))
    return all(
        (
            phase3_report.get("audit_projection_required_count") == 7,
            phase3_report.get("audit_projection_present_count") == 7,
            phase3_report.get("future_external_api_call_candidate_count") == 3,
            phase3_report.get("future_external_api_call_audit_invariant_preserved") is True,
            phase3_report.get("human_handling_required_count") == 6,
            sum(_mapping(item).get("human_handling_required") is True for item in policy_samples) == 6,
            _p4_audit_samples_exact(_sequence(phase4_report.get("control_audit_log_samples"))),
            all(_mapping(item).get("explicit_disposition") for item in _sequence(phase4_report.get("failure_handling_results"))),
            all(_mapping(item).get("externalization_performed") is False for item in _sequence(phase4_report.get("non_externalized_data_records"))),
        )
    )


def _delivery_boundary(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("actual_delivery_file_written") is False,
            report.get("actual_embedding_queue_count") == 0,
            report.get("actual_cache_entry_count") == 0,
            report.get("actual_failed_retry_count") == 0,
            report.get("actual_external_payload_count") == 0,
            report.get("actual_external_api_call_count") == 0,
            report.get("actual_model_token_count") == 0,
            report.get("actual_cost_count") == 0,
            report.get("actual_external_api_audit_log_count") == 0,
            report.get("actual_failure_record_count") == 0,
            report.get("actual_non_externalized_data_record_count") == 0,
            report.get("actual_audit_log_query_performed") is False,
            report.get("actual_externalization_record_query_performed") is False,
            report.get("actual_policy_rollback_performed") is False,
        )
    )


def _rollback_chain(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase2, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase3, "rollback_contract.return_to")
            == "PHASE2_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE_RUNTIME_DISABLED",
            _get(phase4, "rollback_contract.return_to") == P3_PASS_RESULT,
            _get(phase4, "rollback_contract.preserve_phase1_contract") is True,
            _get(phase4, "rollback_contract.preserve_phase2_control_slice") is True,
            _get(phase4, "rollback_contract.preserve_phase3_controlled_scenarios") is True,
            _get(phase4, "rollback_contract.github_or_ovh_change_allowed") is False,
            _get(phase4_report, "policy_rollback_instructions.rollback_target_result") == P3_PASS_RESULT,
            _get(phase4_report, "policy_rollback_instructions.instruction_kind")
            == "EMBEDDING_COST_GOVERNOR_POLICY_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY",
            _get(phase4_report, "policy_rollback_instructions.real_source_change_allowed") is False,
            _get(phase4_report, "policy_rollback_instructions.persistent_state_change_allowed") is False,
            _get(phase4_report, "policy_rollback_instructions.actual_policy_rollback_performed") is False,
        )
    )


def _future_stage_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return all(
        (
            _get(phase1, "stage_and_phase_boundary.stage072_started") is False,
            _get(phase2, "stage_and_phase_boundary.stage072_started") is False,
            _get(phase3, "stage_and_phase_boundary.stage072_started") is False,
            _get(phase4, "stage_and_phase_boundary.stage072_started") is False,
            _get(phase4, "stage_and_phase_boundary.whole_stage_review_performed") is False,
            _get(phase4, "stage_and_phase_boundary.batch_review_performed") is False,
            _get(phase4, "stage_and_phase_boundary.github_upload_allowed") is False,
            _get(phase4, "stage_and_phase_boundary.push_allowed") is False,
        )
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


def _runtime_boundary_closed(boundary: Mapping[str, Any]) -> bool:
    return bool(boundary) and all(value is False for value in boundary.values())


def _checks(mapping: Mapping[str, Any], checks: Sequence[tuple[str, Any]]) -> bool:
    return all(_get(mapping, path) == expected for path, expected in checks)


def _get(mapping: Mapping[str, Any], path: str, default: Any = MISSING) -> Any:
    current: Any = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _all_false(mapping: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(field in mapping and mapping[field] is False for field in fields)


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_phase2_report_provider() -> ReportProvider:
    path = BASE / "stage071_embedding_cost_governor_slice.py"
    spec = importlib.util.spec_from_file_location("stage071_review_p2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage071 P2 review dependency is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_input = getattr(module, "build_control_input", None)
    execute = getattr(module, "execute_embedding_cost_governor_control_slice", None)
    if not callable(build_input) or not callable(execute):
        raise RuntimeError("Stage071 P2 review dependency is invalid")

    def provider() -> Mapping[str, Any]:
        return _mapping(execute(build_input()))

    return provider


def _load_report_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage071_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage071 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, callable_name, None)
    if not callable(provider):
        raise RuntimeError(f"Stage071 review dependency is invalid: {filename}")
    return provider


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, (list, tuple)) else ()
