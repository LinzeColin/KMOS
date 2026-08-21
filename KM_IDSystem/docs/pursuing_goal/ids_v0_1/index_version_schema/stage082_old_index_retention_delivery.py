"""Stage082 P4 的纯内存旧索引保留交付证据。

模块只复用 Stage082 P2 的五条固定、非业务控制投影及 P3 的六条受控场景，
派生 metadata-only 索引清单、冒烟测试日志、切换记录、回滚证明、旧索引
保留／空间影响投影和重建、暂停、恢复说明。全部结果只存在于当前 Python
进程，不能替代来源文档、真实 manifest、日志、审计或业务事实，也不会写入
索引、调用模型或启动运行时。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage082.old_index_retention.phase4.delivery.v1"
RECORD_KIND = "OLD_INDEX_RETENTION_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_OLD_INDEX_RETENTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_OLD_INDEX_RETENTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE082-P4-GATE"
NEXT_GATE = "IDS-STAGE082-REVIEW-GATE"
P3_PASS_RESULT = "PASS_OLD_INDEX_RETENTION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_OLD_INDEX_RETENTION_CONTROL_SLICE"
P2_SCENARIOS = (
    "fulltext_smoke_passed_retention_unconfigured_switch_candidate",
    "vector_background_build_incomplete_preserves_active",
    "hybrid_shadow_smoke_failure_blocks_switch",
    "fulltext_atomic_switch_failure_preserves_active",
    "hybrid_retained_previous_rollback_window_unconfigured",
)

INDEX_MANIFEST_FIELDS = (
    "control_scenario",
    "index_manifest_ref",
    "index_version_ref",
    "index_kind",
    "document_scope_ref",
    "chunk_count_control_value",
    "embedding_model_ref",
    "active_index_version_ref",
    "manifest_state",
    "actual_index_manifest_written",
)
SMOKE_TEST_LOG_FIELDS = (
    "scenario_id",
    "smoke_test_log_ref",
    "index_version_ref",
    "smoke_test_status",
    "switch_outcome",
    "old_active_continues",
    "log_state",
    "actual_smoke_test_log_written",
    "human_handling_required",
)
SWITCH_RECORD_FIELDS = (
    "control_scenario",
    "switch_record_ref",
    "index_kind",
    "candidate_index_version_ref",
    "resulting_active_index_version_ref",
    "switch_outcome",
    "active_service_continues",
    "switch_applied",
)
ROLLBACK_PROOF_FIELDS = (
    "control_scenario",
    "rollback_proof_ref",
    "rollback_request_ref",
    "index_kind",
    "rollback_target_index_version_ref",
    "minimum_retained_previous_active_version_count",
    "retention_window_state",
    "rollback_eligibility",
    "rollback_state",
    "rollback_applied",
)
OLD_INDEX_RETENTION_FIELDS = (
    "retention_policy_summary_ref",
    "applies_to_control_scenario_count",
    "minimum_retained_previous_active_version_count",
    "additional_retention_quantity_state",
    "rollback_window_state",
    "cleanup_timing_state",
    "business_line_whitebox_approval_state",
    "cleanup_eligibility_state",
    "space_impact_state",
    "actual_space_impact_measurement_performed",
    "actual_old_index_cleanup_performed",
    "human_handling_required",
    "policy_state",
)
OPERATIONAL_INSTRUCTION_FIELDS = (
    "instruction_id",
    "action",
    "target_ref",
    "entry_precondition",
    "active_service_requirement",
    "control_outcome",
    "actual_operation_performed",
    "human_handling_required",
)

P2_RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "background_build_execution_performed",
    "index_build_execution_performed",
    "shadow_index_build_performed",
    "smoke_test_execution_performed",
    "active_pointer_read_performed",
    "active_pointer_switch_performed",
    "retrieval_query_performed",
    "concurrent_retrieval_performed",
    "index_rollback_execution_performed",
    "old_index_cleanup_performed",
    "space_measurement_performed",
    "persistent_state_write_performed",
    "external_api_call_performed",
    "provider_or_model_selected",
    "model_call_performed",
    "model_token_consumption_performed",
    "agent_execution_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)
P3_RUNTIME_CLOSED_FIELDS = (
    *P2_RUNTIME_CLOSED_FIELDS,
    "actual_operations_display_written",
    "actual_report_snapshot_written",
)
RUNTIME_CLOSED_FIELDS = (
    *P3_RUNTIME_CLOSED_FIELDS,
    "actual_index_manifest_written",
    "actual_smoke_test_log_written",
    "actual_switch_record_written",
    "actual_rollback_proof_written",
    "actual_old_index_retention_record_written",
    "actual_space_impact_measurement_performed",
    "actual_operational_instruction_issued",
)

PHASE2_RECORD_SPECS = (
    ("index_version_control_records", "INDEX_VERSION_RECORD_FIELDS"),
    ("building_and_shadow_control_projections", "BUILDING_AND_SHADOW_FIELDS"),
    ("active_pointer_control_projections", "ACTIVE_POINTER_FIELDS"),
    ("smoke_test_input_control_projections", "SMOKE_TEST_INPUT_FIELDS"),
    ("smoke_test_output_control_projections", "SMOKE_TEST_OUTPUT_FIELDS"),
    ("switch_control_projections", "SWITCH_PROJECTION_FIELDS"),
    ("rollback_request_control_projections", "ROLLBACK_REQUEST_FIELDS"),
    ("retention_policy_control_projections", "RETENTION_POLICY_FIELDS"),
    ("cleanup_eligibility_control_projections", "CLEANUP_ELIGIBILITY_FIELDS"),
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]
Phase2ReportProvider = Callable[[], Mapping[str, Any]]


def build_old_index_retention_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
    phase2_report_provider: Phase2ReportProvider | None = None,
) -> dict[str, Any]:
    """从已验证 P2/P3 报告派生 P4 metadata-only 控制交付证据。"""

    phase3_module = _load_phase3_module()
    phase2_module = _load_phase2_module()
    phase3_report = _provider_result(
        phase3_report_provider or _default_phase3_report_provider
    )
    phase2_report = _provider_result(
        phase2_report_provider or _default_phase2_report_provider
    )
    phase3_valid = _phase3_report_is_valid(phase3_module, phase3_report)
    phase2_valid = _phase2_report_is_valid(phase2_module, phase2_report)
    predecessors_valid = phase3_valid and phase2_valid

    manifests = _index_manifest_samples(phase2_report) if predecessors_valid else []
    smoke_logs = _smoke_test_log_samples(phase3_report) if predecessors_valid else []
    switch_records = _switch_record_samples(phase2_report) if predecessors_valid else []
    rollback_proofs = _rollback_proof_samples(phase2_report) if predecessors_valid else []
    retention = (
        _old_index_retention_projection(phase2_report) if predecessors_valid else {}
    )
    instructions = _operational_instruction_projections() if predecessors_valid else []
    runtime_flags = _runtime_closed_flags()

    delivery_integrity = (
        predecessors_valid
        and _records_have_exact_shape(manifests, 5, INDEX_MANIFEST_FIELDS)
        and _records_have_exact_shape(smoke_logs, 6, SMOKE_TEST_LOG_FIELDS)
        and _records_have_exact_shape(switch_records, 5, SWITCH_RECORD_FIELDS)
        and _records_have_exact_shape(rollback_proofs, 5, ROLLBACK_PROOF_FIELDS)
        and set(retention) == set(OLD_INDEX_RETENTION_FIELDS)
        and _records_have_exact_shape(instructions, 3, OPERATIONAL_INSTRUCTION_FIELDS)
        and all(_manifest_is_control_only(item) for item in manifests)
        and all(_smoke_log_is_control_only(item) for item in smoke_logs)
        and all(_switch_record_is_control_only(item) for item in switch_records)
        and all(_rollback_proof_is_control_only(item) for item in rollback_proofs)
        and _retention_is_control_only(retention)
        and all(_instruction_is_control_only(item) for item in instructions)
        and all(value is False for value in runtime_flags.values())
    )
    valid = bool(delivery_integrity)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": phase3_valid,
        "phase3_controlled_scenarios_report_valid": phase3_valid,
        "phase2_control_slice_reexecuted_in_memory_only": phase2_valid,
        "phase2_control_slice_report_valid": phase2_valid,
        "delivery_evidence_metadata_only": True,
        "index_manifest_control_samples": manifests,
        "index_manifest_control_sample_count": len(manifests),
        "index_manifest_field_count": len(INDEX_MANIFEST_FIELDS),
        "smoke_test_log_control_samples": smoke_logs,
        "smoke_test_log_control_sample_count": len(smoke_logs),
        "smoke_test_log_field_count": len(SMOKE_TEST_LOG_FIELDS),
        "switch_record_control_samples": switch_records,
        "switch_record_control_sample_count": len(switch_records),
        "switch_record_field_count": len(SWITCH_RECORD_FIELDS),
        "rollback_proof_control_samples": rollback_proofs,
        "rollback_proof_control_sample_count": len(rollback_proofs),
        "rollback_proof_field_count": len(ROLLBACK_PROOF_FIELDS),
        "old_index_retention_projection": retention,
        "old_index_retention_projection_count": 1 if retention else 0,
        "old_index_retention_field_count": len(OLD_INDEX_RETENTION_FIELDS),
        "operational_instruction_projections": instructions,
        "operational_instruction_projection_count": len(instructions),
        "operational_instruction_field_count": len(OPERATIONAL_INSTRUCTION_FIELDS),
        "all_delivery_references_control_only": all(
            _record_references_are_control_only(item)
            for group in (manifests, smoke_logs, switch_records, rollback_proofs)
            for item in group
        )
        and _record_references_are_control_only(retention)
        and all(_record_references_are_control_only(item) for item in instructions),
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "automatic_business_recommendation_allowed": False,
        "stage081_review_evidence_declared": True,
        "stage082_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "stage083_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_flags,
        "chinese_feedback": [
            "索引清单、冒烟测试日志、切换记录和回滚证明仅为内存控制投影，未写入实际索引或日志。",
            "至少保留一个上一活动版本；额外保留数量、回滚窗口、清理时点与业务线白箱批准均未设值，回滚和清理保持关闭。",
            "空间影响未测量、旧索引未删除；业务线白箱人工处理仍是保留策略进入真实运行前的前置。",
            "索引重建、暂停和恢复说明只描述未来操作前置，活动版本与实际服务均未变更。",
        ],
    }


def _default_phase3_report_provider() -> Mapping[str, Any]:
    return _load_phase3_module().build_old_index_retention_phase3_report()


def _default_phase2_report_provider() -> Mapping[str, Any]:
    module = _load_phase2_module()
    return module.execute_old_index_retention_control_slice(module.build_control_input())


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _load_phase3_module() -> Any:
    return _load_module(
        "stage082_phase3_scenarios", "stage082_old_index_retention_scenarios.py"
    )


def _load_phase2_module() -> Any:
    return _load_module(
        "stage082_phase2_slice", "stage082_old_index_retention_control_slice.py"
    )


def _load_module(module_name: str, file_name: str) -> Any:
    path = Path(__file__).with_name(file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {file_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase3_report_is_valid(module: Any, report: Mapping[str, Any]) -> bool:
    expected_ids = [item["scenario_id"] for item in module.SCENARIOS]
    results = _as_records(report.get("scenario_results"))
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == ENTRY_GATE
        and report.get("phase2_control_slice_reexecuted") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_views_preserved") is True
        and report.get("phase2_control_record_field_check_count") == 305
        and report.get("scenario_count") == 6
        and report.get("passed_scenario_count") == 6
        and report.get("scenario_field_count") == 31
        and report.get("scenario_field_check_count") == 186
        and report.get("operations_version_control_view_count") == 5
        and report.get("report_snapshot_version_control_view_count") == 5
        and [item.get("scenario_id") for item in results] == expected_ids
        and _records_have_exact_shape(results, 6, module.SCENARIO_RESULT_FIELDS)
        and all(item.get("expectation_met") is True for item in results)
        and all(item.get("silent_drop") is False for item in results)
        and report.get("all_control_references_opaque") is True
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase2_report_is_valid(module: Any, report: Mapping[str, Any]) -> bool:
    groups = tuple(
        (output_key, getattr(module, field_constant))
        for output_key, field_constant in PHASE2_RECORD_SPECS
    )
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("expected_control_request_count") == 5
        and report.get("received_control_request_count") == 5
        and report.get("actual_input_request_count") == 0
        and report.get("all_candidate_versions_are_isolated") is True
        and report.get("all_old_active_versions_continue_serving") is True
        and report.get("all_active_pointer_projections_unchanged") is True
        and report.get("all_minimum_previous_active_versions_retained") is True
        and report.get("all_rollback_targets_reference_retained_previous_active")
        is True
        and report.get("all_cleanup_projections_fail_closed") is True
        and all(
            _records_have_exact_shape(_as_records(report.get(key)), 5, fields)
            for key, fields in groups
        )
        and _phase2_field_check_count(report, groups) == 305
        and all(report.get(field) is False for field in P2_RUNTIME_CLOSED_FIELDS)
    )


def _phase2_field_check_count(
    report: Mapping[str, Any], groups: Sequence[tuple[str, Sequence[str]]]
) -> int:
    return sum(len(_as_records(report.get(key))) * len(fields) for key, fields in groups)


def _index_manifest_samples(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = _as_records(report.get("index_version_control_records"))
    pointers = _as_records(report.get("active_pointer_control_projections"))
    return [
        {
            "control_scenario": scenario,
            "index_manifest_ref": f"index-manifest:control:stage082-p2:{scenario}",
            "index_version_ref": record["index_version"],
            "index_kind": record["index_kind"],
            "document_scope_ref": record["document_scope_ref"],
            "chunk_count_control_value": record["chunk_count"],
            "embedding_model_ref": record["embedding_model_ref"],
            "active_index_version_ref": pointer["active_index_version_ref"],
            "manifest_state": "CONTROL_INDEX_MANIFEST_NOT_PERSISTED",
            "actual_index_manifest_written": False,
        }
        for scenario, record, pointer in zip(P2_SCENARIOS, records, pointers)
    ]


def _smoke_test_log_samples(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "smoke_test_log_ref": (
                "smoke-test-log:control:stage082-p2:"
                f"{scenario['phase2_control_scenario']}:{scenario['scenario_id']}"
            ),
            "index_version_ref": scenario["referenced_index_version_ref"],
            "smoke_test_status": scenario["observed_smoke_test_status"],
            "switch_outcome": scenario["observed_switch_outcome"],
            "old_active_continues": scenario["old_active_continues"],
            "log_state": "CONTROL_SMOKE_TEST_LOG_NOT_PERSISTED",
            "actual_smoke_test_log_written": False,
            "human_handling_required": scenario["human_handling_required"],
        }
        for scenario in _as_records(report.get("scenario_results"))
    ]


def _switch_record_samples(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "control_scenario": record["control_scenario"],
            "switch_record_ref": record["switch_record_ref"],
            "index_kind": record["index_kind"],
            "candidate_index_version_ref": record["candidate_index_version_ref"],
            "resulting_active_index_version_ref": record[
                "resulting_active_index_version_ref"
            ],
            "switch_outcome": record["switch_outcome"],
            "active_service_continues": True,
            "switch_applied": record["switch_applied"],
        }
        for record in _as_records(report.get("switch_control_projections"))
    ]


def _rollback_proof_samples(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rollbacks = _as_records(report.get("rollback_request_control_projections"))
    retentions = _as_records(report.get("retention_policy_control_projections"))
    return [
        {
            "control_scenario": scenario,
            "rollback_proof_ref": f"rollback-proof:control:stage082-p2:{scenario}",
            "rollback_request_ref": rollback["rollback_request_ref"],
            "index_kind": rollback["index_kind"],
            "rollback_target_index_version_ref": rollback[
                "previous_active_index_version_ref"
            ],
            "minimum_retained_previous_active_version_count": retention[
                "minimum_retained_previous_active_version_count"
            ],
            "retention_window_state": rollback["retention_window_state"],
            "rollback_eligibility": rollback["rollback_eligibility"],
            "rollback_state": "CONTROL_ROLLBACK_PROOF_NOT_PERSISTED",
            "rollback_applied": rollback["rollback_applied"],
        }
        for scenario, rollback, retention in zip(P2_SCENARIOS, rollbacks, retentions)
    ]


def _old_index_retention_projection(report: Mapping[str, Any]) -> dict[str, Any]:
    policies = _as_records(report.get("retention_policy_control_projections"))
    cleanups = _as_records(report.get("cleanup_eligibility_control_projections"))
    expected_policy_state = "CONTROL_OLD_INDEX_CLEANUP_BLOCKED_UNCONFIGURED_POLICY"
    expected_cleanup_state = "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY"
    expected_additional = "CONTROL_ADDITIONAL_RETENTION_QUANTITY_UNCONFIGURED"
    expected_window = "CONTROL_ROLLBACK_WINDOW_UNCONFIGURED"
    expected_timing = "CONTROL_CLEANUP_TIMING_UNCONFIGURED"
    expected_approval = "CONTROL_WHITEBOX_APPROVAL_NOT_RECORDED"
    if not (
        len(policies) == len(P2_SCENARIOS)
        and len(cleanups) == len(P2_SCENARIOS)
        and all(
            item.get("minimum_retained_previous_active_version_count") == 1
            and item.get("additional_retained_version_count_requirement_ref")
            == expected_additional
            and item.get("rollback_window_requirement_ref") == expected_window
            and item.get("cleanup_timing_requirement_ref") == expected_timing
            and item.get("business_line_whitebox_approval_ref") == expected_approval
            and item.get("policy_state") == expected_policy_state
            for item in policies
        )
        and all(
            item.get("rollback_window_state") == expected_window
            and item.get("cleanup_timing_state") == expected_timing
            and item.get("business_line_whitebox_approval_state") == expected_approval
            and item.get("cleanup_eligibility") == expected_cleanup_state
            for item in cleanups
        )
    ):
        return {}
    return {
        "retention_policy_summary_ref": (
            "old-index-retention-delivery:control:stage082-p2:aggregate"
        ),
        "applies_to_control_scenario_count": len(P2_SCENARIOS),
        "minimum_retained_previous_active_version_count": 1,
        "additional_retention_quantity_state": expected_additional,
        "rollback_window_state": expected_window,
        "cleanup_timing_state": expected_timing,
        "business_line_whitebox_approval_state": expected_approval,
        "cleanup_eligibility_state": expected_cleanup_state,
        "space_impact_state": "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED",
        "actual_space_impact_measurement_performed": False,
        "actual_old_index_cleanup_performed": False,
        "human_handling_required": True,
        "policy_state": "CONTROL_OLD_INDEX_RETENTION_POLICY_NOT_PERSISTED",
    }


def _operational_instruction_projections() -> list[dict[str, Any]]:
    marker = ":control:stage082-p2:operations"
    return [
        {
            "instruction_id": "OLD_INDEX_RETENTION_REBUILD_CONTROL_INSTRUCTION",
            "action": "REBUILD",
            "target_ref": f"old-index-retention-rebuild{marker}",
            "entry_precondition": (
                "AUTHORIZED_INPUT_AND_APPROVED_RETENTION_POLICY_REQUIRED"
            ),
            "active_service_requirement": (
                "OLD_ACTIVE_VERSION_CONTINUES_UNTIL_BUILD_SMOKE_AND_SWITCH_ARE_AUTHORIZED"
            ),
            "control_outcome": "CONTROL_REBUILD_NOT_STARTED",
            "actual_operation_performed": False,
            "human_handling_required": True,
        },
        {
            "instruction_id": "OLD_INDEX_RETENTION_PAUSE_CONTROL_INSTRUCTION",
            "action": "PAUSE",
            "target_ref": f"old-index-retention-pause{marker}",
            "entry_precondition": "ACTIVE_POINTER_MUST_REMAIN_UNCHANGED",
            "active_service_requirement": "OLD_ACTIVE_VERSION_CONTINUES_DURING_PAUSE",
            "control_outcome": "CONTROL_PAUSE_NOT_APPLIED",
            "actual_operation_performed": False,
            "human_handling_required": True,
        },
        {
            "instruction_id": "OLD_INDEX_RETENTION_RECOVERY_CONTROL_INSTRUCTION",
            "action": "RECOVERY",
            "target_ref": f"old-index-retention-recovery{marker}",
            "entry_precondition": (
                "RETAINED_PREVIOUS_ACTIVE_AND_APPROVED_ROLLBACK_WINDOW_REQUIRED"
            ),
            "active_service_requirement": (
                "RECOVERY_TARGET_MUST_BE_RETAINED_PREVIOUS_ACTIVE"
            ),
            "control_outcome": "CONTROL_RECOVERY_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW",
            "actual_operation_performed": False,
            "human_handling_required": True,
        },
    ]


def _manifest_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("chunk_count_control_value") == 0
        and record.get("manifest_state") == "CONTROL_INDEX_MANIFEST_NOT_PERSISTED"
        and record.get("actual_index_manifest_written") is False
        and _record_references_are_control_only(record)
    )


def _smoke_log_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("old_active_continues") is True
        and record.get("log_state") == "CONTROL_SMOKE_TEST_LOG_NOT_PERSISTED"
        and record.get("actual_smoke_test_log_written") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _switch_record_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("active_service_continues") is True
        and record.get("switch_applied") is False
        and _record_references_are_control_only(record)
    )


def _rollback_proof_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("minimum_retained_previous_active_version_count") == 1
        and record.get("retention_window_state")
        == "CONTROL_ROLLBACK_WINDOW_UNCONFIGURED"
        and record.get("rollback_eligibility")
        == "CONTROL_BLOCKED_UNCONFIGURED_ROLLBACK_WINDOW"
        and record.get("rollback_state") == "CONTROL_ROLLBACK_PROOF_NOT_PERSISTED"
        and record.get("rollback_applied") is False
        and _record_references_are_control_only(record)
    )


def _retention_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("applies_to_control_scenario_count") == 5
        and record.get("minimum_retained_previous_active_version_count") == 1
        and record.get("additional_retention_quantity_state")
        == "CONTROL_ADDITIONAL_RETENTION_QUANTITY_UNCONFIGURED"
        and record.get("rollback_window_state") == "CONTROL_ROLLBACK_WINDOW_UNCONFIGURED"
        and record.get("cleanup_timing_state") == "CONTROL_CLEANUP_TIMING_UNCONFIGURED"
        and record.get("business_line_whitebox_approval_state")
        == "CONTROL_WHITEBOX_APPROVAL_NOT_RECORDED"
        and record.get("cleanup_eligibility_state")
        == "CONTROL_CLEANUP_BLOCKED_UNCONFIGURED_POLICY"
        and record.get("space_impact_state")
        == "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED"
        and record.get("actual_space_impact_measurement_performed") is False
        and record.get("actual_old_index_cleanup_performed") is False
        and record.get("human_handling_required") is True
        and record.get("policy_state")
        == "CONTROL_OLD_INDEX_RETENTION_POLICY_NOT_PERSISTED"
        and _record_references_are_control_only(record)
    )


def _instruction_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("action") in {"REBUILD", "PAUSE", "RECOVERY"}
        and record.get("actual_operation_performed") is False
        and record.get("human_handling_required") is True
        and str(record.get("control_outcome", "")).startswith("CONTROL_")
        and _record_references_are_control_only(record)
    )


def _records_have_exact_shape(
    records: Sequence[Mapping[str, Any]], count: int, fields: Sequence[str]
) -> bool:
    return len(records) == count and all(set(record) == set(fields) for record in records)


def _as_records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _record_references_are_control_only(record: Mapping[str, Any]) -> bool:
    reference_values = [
        value
        for field, value in record.items()
        if field.endswith("_ref") or field in {"target_ref", "index_version_ref"}
    ]
    return bool(reference_values) and all(
        ":control:stage082-p2:" in str(value) for value in reference_values
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
