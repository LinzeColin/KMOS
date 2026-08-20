"""Stage074 的纯内存整阶段机械复审，不读取真实资料或启动 Stage075。"""

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
    / "STAGE-074_本地Embedding兜底合同.md"
)
NEXT_TASKPACK = (
    BASE.parents[2]
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-075_外部API覆盖授权审计.md"
)
P1_CONTRACT = BASE / "stage074_local_embedding_fallback_contract.json"
P2_CONTRACT = BASE / "stage074_local_embedding_fallback_slice_contract.json"
P3_CONTRACT = BASE / "stage074_local_embedding_fallback_scenarios_contract.json"
P4_CONTRACT = BASE / "stage074_local_embedding_fallback_delivery_contract.json"

SCHEMA_VERSION = "ids.stage074.local_embedding_fallback.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE074-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-074"
PASS_RESULT = "PASS_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED"
REVIEW_GATE = "IDS-STAGE074-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE075-P1-GATE"
RETURN_STATE = "PASS_PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_RUNTIME_DISABLED"
P2_STATE = "COMPLETED_IN_MEMORY_LOCAL_EMBEDDING_FALLBACK_CONTROL_SLICE"
P3_PASS_RESULT = "PASS_PHASE3_LOCAL_EMBEDDING_FALLBACK_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P4_PASS_RESULT = "PASS_PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_RUNTIME_DISABLED"

P2_REPORT_FALSE_FIELDS = (
    "actual_data_source_policy_read",
    "actual_document_policy_resolved",
    "actual_chunk_policy_assigned",
    "actual_policy_resolution_record_created",
    "actual_local_provider_selected",
    "actual_local_model_selected",
    "actual_local_embedding_execution_performed",
    "actual_local_embedding_or_index_written",
    "actual_embedding_queue_request_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_failed_retry_record_created",
    "actual_retry_execution_performed",
    "actual_cost_governor_record_created",
    "actual_cost_estimation_performed",
    "actual_budget_lookup_performed",
    "actual_model_version_record_created",
    "actual_external_api_audit_record_created",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chunking_execution_performed",
    "summary_generation_performed",
    "local_provider_or_model_selected",
    "local_embedding_execution_performed",
    "local_embedding_or_index_write_performed",
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
P3_REPORT_FALSE_FIELDS = P2_REPORT_FALSE_FIELDS + (
    "actual_control_scenario_record_persisted",
    "actual_external_payload_created",
    "control_payload_content_retained",
    "audit_test_execution_performed",
    "github_upload_allowed",
    "push_allowed",
    "stage075_started",
    "batch_review_performed",
)
P4_REPORT_FALSE_FIELDS = (
    "actual_audit_log_query_performed",
    "actual_business_decision_created",
    "actual_cache_entry_created",
    "actual_cache_read_or_write_performed",
    "actual_chunk_policy_assigned",
    "actual_control_scenario_record_persisted",
    "actual_cost_estimation_performed",
    "actual_cost_governor_record_created",
    "actual_data_source_policy_read",
    "actual_delivery_file_written",
    "actual_document_policy_resolved",
    "actual_embedding_queue_request_created",
    "actual_external_api_audit_record_created",
    "actual_external_payload_created",
    "actual_externalization_record_query_performed",
    "actual_failed_retry_record_created",
    "actual_local_embedding_execution_performed",
    "actual_local_embedding_or_index_written",
    "actual_local_model_selected",
    "actual_local_provider_selected",
    "actual_model_version_record_created",
    "actual_policy_resolution_record_created",
    "actual_policy_rollback_performed",
    "actual_retry_execution_performed",
    "agent_execution_performed",
    "audit_log_query_performed",
    "audit_record_creation_performed",
    "audit_test_execution_performed",
    "authorized_fixture_access_performed",
    "automatic_business_recommendation_allowed",
    "batch_review_performed",
    "budget_lookup_performed",
    "cache_read_or_write_performed",
    "chunking_execution_performed",
    "control_payload_content_retained",
    "cost_estimation_execution_performed",
    "database_connection_performed",
    "delivery_control_metadata_can_become_business_fact_authority",
    "delivery_control_metadata_can_replace_source_document",
    "embedding_or_index_write_performed",
    "embedding_queue_execution_performed",
    "external_api_call_performed",
    "external_api_client_initialized",
    "external_model_output_can_become_business_fact_authority",
    "external_payload_created",
    "failed_retry_execution_performed",
    "github_upload_allowed",
    "github_upload_performed",
    "ids_business_source_read_performed",
    "local_embedding_execution_performed",
    "local_embedding_or_index_write_performed",
    "local_provider_or_model_selected",
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
    "local_provider_or_model_selected",
    "local_embedding_execution_performed",
    "local_embedding_or_index_write_performed",
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
    "model_call_performed",
    "model_token_consumption_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "batch_review_performed",
    "stage075_started",
    "github_upload_allowed",
    "github_upload_performed",
    "push_allowed",
    "push_performed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage074_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase2_report_provider: ReportProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage074 P1--P4，只输出零运行时控制结论和下一门禁。"""

    phase1 = _mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    phase2_report = _mapping((phase2_report_provider or _phase2_report_provider())())
    phase3_report = _mapping((phase3_report_provider or _report_provider(
        "stage074_local_embedding_fallback_scenarios.py",
        "build_local_embedding_fallback_phase3_report",
    ))())
    phase4_report = _mapping((phase4_report_provider or _report_provider(
        "stage074_local_embedding_fallback_delivery.py",
        "build_local_embedding_fallback_phase4_delivery_report",
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
        "next_stage_taskpack_available_but_not_started": NEXT_TASKPACK.is_file(),
        "single_authority_boundary_preserved": _single_authority(
            phase1, phase2, phase3, phase4, phase3_report, phase4_report
        ),
        "policy_audit_and_whitebox_boundaries_preserved": _policy_boundary(
            phase1, phase2, phase3_report, phase4_report
        ),
        "fixed_control_shapes_preserved": _expected_replay(replay),
        "future_calls_remain_audited_and_whitebox_controlled": _future_call_boundary(
            phase3_report, phase4_report
        ),
        "metadata_only_delivery_boundary_preserved": _delivery_boundary(phase4_report),
        "p4_to_p3_control_rollback_chain_preserved": _rollback_chain(
            phase4, phase4_report
        ),
        "stage075_gate_only_opens_after_review": _future_stage_boundary(
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
        "source_authority": "FROZEN_STAGE074_TASKPACK_AND_STAGE074_P1_TO_P4_CONTROL_ARTIFACTS_ONLY",
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
                "Stage074 review document",
                "Stage074 review module",
                "Stage074 review focused tests",
                "Stage074 review governance projection",
            ),
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "audit_log_change_allowed": False,
            "embedding_or_external_api_runtime_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": REVIEW_GATE,
        **{field: False for field in REVIEW_RUNTIME_FALSE_FIELDS},
        "actual_local_embedding_count": 0,
        "actual_embedding_queue_count": 0,
        "actual_cache_entry_count": 0,
        "actual_failed_retry_count": 0,
        "actual_cost_count": 0,
        "actual_model_version_record_count": 0,
        "actual_external_api_audit_count": 0,
        "actual_external_api_call_count": 0,
        "actual_model_token_count": 0,
        "actual_delivery_file_written_count": 0,
        "actual_audit_log_query_count": 0,
        "actual_externalization_record_query_count": 0,
        "actual_policy_rollback_count": 0,
        "stage073_review_evidence_read": True,
        "stage074_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
    }
    report["review_invariants"]["runtime_actions_disabled"] = (
        report["review_invariants"]["runtime_actions_disabled"]
        and _all_false(report, REVIEW_RUNTIME_FALSE_FIELDS)
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
            ("schema_version", "ids.stage074.local_embedding_fallback.phase1.v1"),
            ("contract_state", "PHASE1_LOCAL_EMBEDDING_FALLBACK_CONTRACT_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE074-P1"),
            ("next_gate", "IDS-STAGE074-P2-GATE"),
            ("execution_ready", True),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("local_embedding_fallback_contract.local_provider_or_model_selection_allowed_in_phase1", False),
            ("local_embedding_fallback_contract.local_embedding_execution_allowed_in_phase1", False),
            ("policy_inheritance_contract.default_external_api_policy", "denied"),
            ("policy_inheritance_contract.allowed_value_count", 3),
            ("policy_inheritance_contract.inheritance_hop_count", 2),
            ("policy_inheritance_contract.document_may_widen_data_source_policy", False),
            ("policy_inheritance_contract.chunk_inherits_effective_document_policy_automatically", True),
            ("embedding_queue_cost_model_audit_contract.future_embedding_queue_field_count", 12),
            ("embedding_queue_cost_model_audit_contract.future_cache_field_count", 10),
            ("embedding_queue_cost_model_audit_contract.future_failed_retry_field_count", 7),
            ("embedding_queue_cost_model_audit_contract.future_cost_governor_field_count", 16),
            ("embedding_queue_cost_model_audit_contract.future_cost_and_model_field_count", 8),
            ("embedding_queue_cost_model_audit_contract.future_model_version_field_count", 6),
            ("embedding_queue_cost_model_audit_contract.future_external_api_audit_field_count", 18),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("stage_and_phase_boundary.phase1_started", True),
            ("stage_and_phase_boundary.phase2_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage075_started", False),
        ),
    ) and _all_false_mapping(_mapping(contract.get("runtime_boundary")))


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage074.local_embedding_fallback.phase2.v1"),
            ("contract_state", "PHASE2_LOCAL_EMBEDDING_FALLBACK_CONTROL_SLICE_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE074-P2"),
            ("next_gate", "IDS-STAGE074-P3-GATE"),
            ("slice_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("reference_only_local_embedding_fallback_input_control_contract.field_count", 20),
            ("reference_only_local_embedding_fallback_input_control_contract.control_request_count", 5),
            ("policy_inheritance_control_contract.default_external_api_policy", "denied"),
            ("policy_inheritance_control_contract.inheritance_hop_count", 2),
            ("policy_inheritance_control_contract.document_may_widen_data_source_policy", False),
            ("policy_inheritance_control_contract.chunk_inherits_effective_document_policy_automatically", True),
            ("local_fallback_route_control_contract.actual_local_embedding_execution_performed", False),
            ("embedding_queue_cache_retry_control_contract.future_queue_field_count", 12),
            ("embedding_queue_cache_retry_control_contract.future_cache_field_count", 10),
            ("embedding_queue_cache_retry_control_contract.future_failed_retry_field_count", 7),
            ("cost_governor_control_contract.field_count", 16),
            ("model_version_control_contract.field_count", 6),
            ("cost_control_contract.field_count", 8),
            ("external_api_audit_control_contract.field_count", 18),
            ("failure_and_stop_contract.failure_state_count", 12),
            ("stage_and_phase_boundary.phase2_started", True),
            ("stage_and_phase_boundary.phase3_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage075_started", False),
        ),
    ) and _all_false_mapping(_mapping(contract.get("runtime_boundary")))


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage074.local_embedding_fallback.phase3.v1"),
            ("contract_state", "PHASE3_LOCAL_EMBEDDING_FALLBACK_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE074-P3"),
            ("next_gate", "IDS-STAGE074-P4-GATE"),
            ("scenario_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("phase2_control_slice_replay_contract.control_request_count", 5),
            ("phase2_control_slice_replay_contract.policy_resolution_record_field_count", 10),
            ("phase2_control_slice_replay_contract.embedding_queue_record_field_count", 14),
            ("phase2_control_slice_replay_contract.cache_record_field_count", 10),
            ("phase2_control_slice_replay_contract.failed_retry_record_field_count", 7),
            ("phase2_control_slice_replay_contract.cost_governor_projection_field_count", 16),
            ("phase2_control_slice_replay_contract.model_version_projection_field_count", 6),
            ("phase2_control_slice_replay_contract.cost_projection_field_count", 8),
            ("phase2_control_slice_replay_contract.external_api_audit_projection_field_count", 18),
            ("controlled_scenario_contract.scenario_count", 5),
            ("controlled_scenario_contract.field_count", 35),
            ("controlled_scenario_contract.silent_drop_allowed", False),
            ("audit_projection_invariant_contract.inherited_phase2_audit_field_count", 18),
            ("audit_projection_invariant_contract.control_audit_field_check_count", 90),
            ("audit_projection_invariant_contract.future_external_api_call_candidate_count", 3),
            ("stage_and_phase_boundary.phase3_started", True),
            ("stage_and_phase_boundary.phase4_started", False),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage075_started", False),
        ),
    ) and _all_false_mapping(_mapping(contract.get("runtime_boundary")))


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return _checks(
        contract,
        (
            ("schema_version", "ids.stage074.local_embedding_fallback.phase4.delivery.v1"),
            ("contract_state", "PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_EVIDENCE_RUNTIME_DISABLED"),
            ("task_id", "IDS-V0_1-STAGE074-P4"),
            ("entry_gate", "IDS-STAGE074-P4-GATE"),
            ("next_gate", REVIEW_GATE),
            ("delivery_executable", True),
            ("execution_ready", False),
            ("source_authority.second_authoritative_source_created", False),
            ("source_authority.source_body_or_path_allowed", False),
            ("phase3_controlled_scenario_replay_contract.scenario_count", 5),
            ("phase3_controlled_scenario_replay_contract.scenario_field_count", 35),
            ("phase3_controlled_scenario_replay_contract.external_api_audit_projection_field_count", 18),
            ("phase3_controlled_scenario_replay_contract.audit_field_check_count", 90),
            ("phase3_controlled_scenario_replay_contract.future_external_api_call_candidate_count", 3),
            ("phase3_controlled_scenario_replay_contract.human_handling_required_count", 4),
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
            ("authority_and_decision_boundary.business_line_whitebox_human_review_remains_authoritative", True),
            ("authority_and_decision_boundary.delivery_control_metadata_can_replace_source_document", False),
            ("stage_and_phase_boundary.phase4_started", True),
            ("stage_and_phase_boundary.whole_stage_review_performed", False),
            ("stage_and_phase_boundary.stage075_started", False),
            ("rollback_contract.return_to", P3_PASS_RESULT),
        ),
    ) and _all_false_mapping(_mapping(contract.get("runtime_boundary")))


def _phase2_report_valid(report: Mapping[str, Any]) -> bool:
    shapes = {
        "policy_resolutions": 10,
        "embedding_queue_records": 14,
        "cache_records": 10,
        "failed_retry_records": 7,
        "cost_governor_control_projections": 16,
        "model_version_control_projections": 6,
        "cost_control_projections": 8,
        "external_api_audit_projections": 18,
    }
    return (
        _checks(
            report,
            (
                ("schema_version", "ids.stage074.local_embedding_fallback.phase2.v1"),
                ("record_kind", "CONTROL_ONLY_IN_MEMORY_LOCAL_EMBEDDING_FALLBACK"),
                ("input_accepted", True),
                ("execution_state", P2_STATE),
                ("control_request_count", 5),
                ("policy_resolution_count", 5),
                ("embedding_queue_record_count", 5),
                ("cache_record_count", 5),
                ("failed_retry_record_count", 5),
                ("cost_governor_control_projection_count", 5),
                ("model_version_control_projection_count", 5),
                ("cost_control_projection_count", 5),
                ("external_api_audit_projection_count", 5),
                ("actual_input_request_count", 0),
                ("all_chunks_inherit_effective_document_policy_automatically", True),
                ("chunk_manual_policy_assignment_performed", False),
                ("local_fallback_route_is_not_external_api_egress", True),
                ("source_body_summary_body_or_chunk_text_retained", False),
            ),
        )
        and all(
            len(_mapping_sequence(report.get(name))) == 5
            and all(len(item) == field_count for item in _mapping_sequence(report.get(name)))
            for name, field_count in shapes.items()
        )
        and _all_false(report, P2_REPORT_FALSE_FIELDS)
    )


def _phase3_report_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _mapping_sequence(report.get("scenario_results"))
    return (
        _checks(
            report,
            (
                ("schema_version", "ids.stage074.local_embedding_fallback.phase3.v1"),
                ("result", P3_PASS_RESULT),
                ("valid", True),
                ("scenario_count", 5),
                ("passed_scenario_count", 5),
                ("silent_drop_count", 0),
                ("control_audit_field_count", 18),
                ("control_audit_field_check_count", 90),
                ("future_external_api_call_candidate_count", 3),
                ("human_handling_required_count", 4),
                ("phase2_control_slice_reexecuted", True),
                ("phase2_shape_preserved", True),
                ("phase2_side_effect_free", True),
                ("policy_payload_boundaries_preserved", True),
                ("audit_projection_invariant_preserved", True),
                ("future_external_api_call_audit_invariant_preserved", True),
                ("source_document_remains_authoritative", True),
                ("control_scenario_can_replace_source_document", False),
                ("audit_projection_can_become_business_fact_authority", False),
                ("automatic_business_recommendation_allowed", False),
                ("next_gate", "IDS-STAGE074-P4-GATE"),
            ),
        )
        and len(scenarios) == 5
        and all(len(item) == 35 for item in scenarios)
        and _all_false(report, P3_REPORT_FALSE_FIELDS)
    )


def _phase4_report_valid(report: Mapping[str, Any]) -> bool:
    audit_samples = _mapping_sequence(report.get("control_audit_log_samples"))
    query = _mapping(report.get("externalization_record_query_instructions"))
    rollback = _mapping(report.get("policy_rollback_instructions"))
    return (
        _checks(
            report,
            (
                ("schema_version", "ids.stage074.local_embedding_fallback.phase4.delivery.v1"),
                ("result", P4_PASS_RESULT),
                ("valid", True),
                ("delivery_evidence_metadata_only", True),
                ("phase2_control_slice_reexecuted_in_memory_only", True),
                ("phase2_control_slice_report_valid", True),
                ("phase3_controlled_scenarios_reused_as_reference_only", True),
                ("phase3_controlled_scenarios_report_valid", True),
                ("policy_sample_count", 5),
                ("control_audit_log_sample_count", 5),
                ("control_audit_field_count", 18),
                ("control_audit_field_check_count", 90),
                ("zero_cost_estimate_sample_count", 5),
                ("failure_handling_result_count", 5),
                ("non_externalized_data_record_count", 5),
                ("future_external_api_call_candidate_count", 3),
                ("human_handling_required_count", 4),
                ("policy_denied_sample_count", 1),
                ("budget_pause_sample_count", 1),
                ("source_document_remains_authoritative", True),
                ("business_line_whitebox_human_review_remains_authoritative", True),
                ("next_gate", REVIEW_GATE),
            ),
        )
        and len(_mapping_sequence(report.get("local_embedding_fallback_policy_samples"))) == 5
        and len(audit_samples) == 5
        and all(
            item.get("audit_field_count") == 18
            and len(_mapping(item.get("audit_projection"))) == 18
            and item.get("actual_audit_record_created") is False
            and item.get("actual_audit_record_persisted") is False
            for item in audit_samples
        )
        and len(_mapping_sequence(report.get("cost_estimate_samples"))) == 5
        and len(_mapping_sequence(report.get("failure_handling_results"))) == 5
        and len(_mapping_sequence(report.get("non_externalized_data_records"))) == 5
        and len(_sequence(query.get("supported_query_keys"))) == 7
        and query.get("persistent_audit_log_available") is False
        and query.get("real_externalization_history_available") is False
        and rollback.get("rollback_target_result") == P3_PASS_RESULT
        and rollback.get("actual_policy_rollback_performed") is False
        and _all_false(report, P4_REPORT_FALSE_FIELDS)
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
    return {
        "phase1_policy_value_count": _int_at(
            phase1, "policy_inheritance_contract.allowed_value_count"
        ),
        "phase1_policy_inheritance_hop_count": _int_at(
            phase1, "policy_inheritance_contract.inheritance_hop_count"
        ),
        "phase1_future_queue_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_embedding_queue_field_count"
        ),
        "phase1_future_cache_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_cache_field_count"
        ),
        "phase1_future_retry_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_failed_retry_field_count"
        ),
        "phase1_future_cost_governor_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_cost_governor_field_count"
        ),
        "phase1_future_cost_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_cost_and_model_field_count"
        ),
        "phase1_future_model_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_model_version_field_count"
        ),
        "phase1_future_audit_field_count": _int_at(
            phase1, "embedding_queue_cost_model_audit_contract.future_external_api_audit_field_count"
        ),
        "phase1_failure_state_count": _int_at(
            phase1, "failure_and_stop_contract.failure_state_count"
        ),
        "phase2_control_request_count": _int_at(phase2_report, "control_request_count"),
        "phase2_input_field_count": _int_at(
            phase2, "reference_only_local_embedding_fallback_input_control_contract.field_count"
        ),
        "phase2_policy_record_field_count": _record_shape(
            phase2_report, "policy_resolutions"
        ),
        "phase2_queue_record_field_count": _record_shape(
            phase2_report, "embedding_queue_records"
        ),
        "phase2_cache_record_field_count": _record_shape(
            phase2_report, "cache_records"
        ),
        "phase2_retry_record_field_count": _record_shape(
            phase2_report, "failed_retry_records"
        ),
        "phase2_cost_governor_record_field_count": _record_shape(
            phase2_report, "cost_governor_control_projections"
        ),
        "phase2_model_record_field_count": _record_shape(
            phase2_report, "model_version_control_projections"
        ),
        "phase2_cost_record_field_count": _record_shape(
            phase2_report, "cost_control_projections"
        ),
        "phase2_audit_record_field_count": _record_shape(
            phase2_report, "external_api_audit_projections"
        ),
        "phase2_failure_state_count": _int_at(
            phase2, "failure_and_stop_contract.failure_state_count"
        ),
        "phase3_scenario_count": _int_at(phase3_report, "scenario_count"),
        "phase3_scenario_field_count": _record_shape(phase3_report, "scenario_results"),
        "phase3_audit_field_count": _int_at(phase3_report, "control_audit_field_count"),
        "phase3_audit_field_check_count": _int_at(
            phase3_report, "control_audit_field_check_count"
        ),
        "phase3_future_call_candidate_count": _int_at(
            phase3_report, "future_external_api_call_candidate_count"
        ),
        "phase3_human_handling_required_count": _int_at(
            phase3_report, "human_handling_required_count"
        ),
        "phase3_failure_state_count": _int_at(
            phase3, "failure_and_stop_contract.failure_state_count"
        ),
        "phase4_policy_sample_count": _int_at(phase4_report, "policy_sample_count"),
        "phase4_audit_sample_count": _int_at(
            phase4_report, "control_audit_log_sample_count"
        ),
        "phase4_audit_field_count": _int_at(
            phase4_report, "control_audit_field_count"
        ),
        "phase4_audit_field_check_count": _int_at(
            phase4_report, "control_audit_field_check_count"
        ),
        "phase4_cost_sample_count": _int_at(
            phase4_report, "zero_cost_estimate_sample_count"
        ),
        "phase4_failure_handling_count": _int_at(
            phase4_report, "failure_handling_result_count"
        ),
        "phase4_non_externalized_record_count": _int_at(
            phase4_report, "non_externalized_data_record_count"
        ),
        "phase4_query_key_count": len(
            _sequence(_mapping(phase4_report.get("externalization_record_query_instructions")).get(
                "supported_query_keys"
            ))
        ),
        "phase4_chinese_feedback_count": len(
            _sequence(phase4_report.get("chinese_feedback"))
        ),
        "phase4_failure_state_count": _int_at(
            phase4, "failure_and_stop_contract.failure_state_count"
        ),
    }


def _expected_replay(replay: Mapping[str, int]) -> bool:
    return replay == {
        "phase1_policy_value_count": 3,
        "phase1_policy_inheritance_hop_count": 2,
        "phase1_future_queue_field_count": 12,
        "phase1_future_cache_field_count": 10,
        "phase1_future_retry_field_count": 7,
        "phase1_future_cost_governor_field_count": 16,
        "phase1_future_cost_field_count": 8,
        "phase1_future_model_field_count": 6,
        "phase1_future_audit_field_count": 18,
        "phase1_failure_state_count": 12,
        "phase2_control_request_count": 5,
        "phase2_input_field_count": 20,
        "phase2_policy_record_field_count": 10,
        "phase2_queue_record_field_count": 14,
        "phase2_cache_record_field_count": 10,
        "phase2_retry_record_field_count": 7,
        "phase2_cost_governor_record_field_count": 16,
        "phase2_model_record_field_count": 6,
        "phase2_cost_record_field_count": 8,
        "phase2_audit_record_field_count": 18,
        "phase2_failure_state_count": 12,
        "phase3_scenario_count": 5,
        "phase3_scenario_field_count": 35,
        "phase3_audit_field_count": 18,
        "phase3_audit_field_check_count": 90,
        "phase3_future_call_candidate_count": 3,
        "phase3_human_handling_required_count": 4,
        "phase3_failure_state_count": 11,
        "phase4_policy_sample_count": 5,
        "phase4_audit_sample_count": 5,
        "phase4_audit_field_count": 18,
        "phase4_audit_field_check_count": 90,
        "phase4_cost_sample_count": 5,
        "phase4_failure_handling_count": 5,
        "phase4_non_externalized_record_count": 5,
        "phase4_query_key_count": 7,
        "phase4_chinese_feedback_count": 4,
        "phase4_failure_state_count": 12,
    }


def _single_authority(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        all(
            _value_at(contract, "source_authority.second_authoritative_source_created")
            is False
            and _value_at(contract, "source_authority.source_body_or_path_allowed") is False
            for contract in (phase1, phase2, phase3, phase4)
        )
        and _value_at(
            phase1, "authority_and_decision_boundary.source_document_remains_authoritative"
        )
        is True
        and _value_at(
            phase2, "authority_and_decision_boundary.control_projection_can_replace_source_document"
        )
        is False
        and _value_at(
            phase3, "authority_and_decision_boundary.control_scenario_can_replace_source_document"
        )
        is False
        and _value_at(
            phase4, "authority_and_decision_boundary.delivery_control_metadata_can_replace_source_document"
        )
        is False
        and phase3_report.get("source_document_remains_authoritative") is True
        and phase3_report.get("control_scenario_can_replace_source_document") is False
        and phase4_report.get("source_document_remains_authoritative") is True
        and phase4_report.get("delivery_control_metadata_can_replace_source_document") is False
        and phase4_report.get("delivery_control_metadata_can_become_business_fact_authority")
        is False
        and phase4_report.get("actual_business_decision_created") is False
    )


def _policy_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3_report: Mapping[str, Any],
    phase4_report: Mapping[str, Any],
) -> bool:
    return (
        _value_at(phase1, "policy_inheritance_contract.default_external_api_policy")
        == "denied"
        and _value_at(
            phase1, "policy_inheritance_contract.document_may_widen_data_source_policy"
        )
        is False
        and _value_at(
            phase1,
            "policy_inheritance_contract.chunk_inherits_effective_document_policy_automatically",
        )
        is True
        and _value_at(
            phase2, "policy_inheritance_control_contract.default_external_api_policy"
        )
        == "denied"
        and phase3_report.get("policy_payload_boundaries_preserved") is True
        and phase3_report.get("audit_projection_invariant_preserved") is True
        and phase4_report.get("business_line_whitebox_human_review_remains_authoritative")
        is True
    )


def _future_call_boundary(
    phase3_report: Mapping[str, Any], phase4_report: Mapping[str, Any]
) -> bool:
    return (
        phase3_report.get("future_external_api_call_candidate_count") == 3
        and phase3_report.get("human_handling_required_count") == 4
        and phase3_report.get("future_external_api_call_audit_invariant_preserved") is True
        and phase4_report.get("future_external_api_call_candidate_count") == 3
        and phase4_report.get("human_handling_required_count") == 4
        and all(
            item.get("audit_projection_required") is True
            and item.get("audit_projection_present") is True
            and item.get("actual_external_api_call_performed") is False
            and item.get("actual_model_token_consumption_performed") is False
            for item in _mapping_sequence(phase4_report.get("control_audit_log_samples"))
        )
    )


def _delivery_boundary(report: Mapping[str, Any]) -> bool:
    return (
        report.get("delivery_evidence_metadata_only") is True
        and report.get("actual_delivery_file_written") is False
        and report.get("actual_audit_log_query_performed") is False
        and report.get("actual_externalization_record_query_performed") is False
        and report.get("actual_policy_rollback_performed") is False
        and report.get("actual_external_api_call_count") == 0
        and report.get("actual_model_token_count") == 0
        and len(_mapping_sequence(report.get("non_externalized_data_records"))) == 5
    )


def _rollback_chain(phase4: Mapping[str, Any], report: Mapping[str, Any]) -> bool:
    rollback = _mapping(report.get("policy_rollback_instructions"))
    return (
        _value_at(phase4, "rollback_contract.return_to") == P3_PASS_RESULT
        and rollback.get("rollback_target_result") == P3_PASS_RESULT
        and rollback.get("actual_policy_rollback_performed") is False
        and rollback.get("real_source_change_allowed") is False
        and rollback.get("persistent_state_change_allowed") is False
        and rollback.get("github_or_ovh_change_allowed") is False
    )


def _future_stage_boundary(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
) -> bool:
    return all(
        _value_at(contract, "stage_and_phase_boundary.stage075_started") is False
        and _value_at(contract, "stage_and_phase_boundary.whole_stage_review_performed")
        is False
        and _value_at(contract, "stage_and_phase_boundary.github_upload_allowed") is False
        and _value_at(contract, "stage_and_phase_boundary.push_allowed") is False
        for contract in (phase1, phase2, phase3, phase4)
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
    return (
        all(
            _all_false_mapping(_mapping(contract.get("runtime_boundary")))
            for contract in (phase1, phase2, phase3, phase4)
        )
        and _all_false(phase2_report, P2_REPORT_FALSE_FIELDS)
        and _all_false(phase3_report, P3_REPORT_FALSE_FIELDS)
        and _all_false(phase4_report, P4_REPORT_FALSE_FIELDS)
        and all(
            report.get(field) == 0
            for report in (phase3_report, phase4_report)
            for field in (
                "actual_embedding_queue_count",
                "actual_cache_entry_count",
                "actual_failed_retry_count",
                "actual_cost_count",
                "actual_model_version_record_count",
                "actual_external_api_audit_record_count",
                "actual_external_api_call_count",
                "actual_model_token_count",
            )
        )
    )


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _phase2_report_provider() -> ReportProvider:
    def provider() -> Mapping[str, Any]:
        module = _load_module("stage074_local_embedding_fallback_slice.py")
        return _mapping(
            module.execute_local_embedding_fallback_control_slice(
                module.build_control_input()
            )
        )

    return provider


def _report_provider(filename: str, function_name: str) -> ReportProvider:
    def provider() -> Mapping[str, Any]:
        module = _load_module(filename)
        return _mapping(getattr(module, function_name)())

    return provider


def _load_module(filename: str) -> Any:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(f"stage074_review_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load controlled review provider: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checks(mapping: Mapping[str, Any], checks: Sequence[tuple[str, object]]) -> bool:
    return all(_value_at(mapping, path) == expected for path, expected in checks)


def _value_at(mapping: Mapping[str, Any], path: str) -> object:
    current: object = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _int_at(mapping: Mapping[str, Any], path: str) -> int:
    value = _value_at(mapping, path)
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _record_shape(mapping: Mapping[str, Any], name: str) -> int:
    records = _mapping_sequence(mapping.get(name))
    return len(records[0]) if records and all(len(item) == len(records[0]) for item in records) else -1


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _sequence(value: object) -> list[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return list(value)


def _all_false(mapping: Mapping[str, Any], fields: Sequence[str]) -> bool:
    return all(mapping.get(field) is False for field in fields)


def _all_false_mapping(mapping: Mapping[str, Any]) -> bool:
    return bool(mapping) and all(value is False for value in mapping.values())
