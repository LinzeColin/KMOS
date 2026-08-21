"""Stage079 P4 的纯内存索引原子切换交付证据。

模块只复用 Stage079 P2 的五组固定、非业务控制投影及 P3 的六条专项场景，
派生控制版索引清单、冒烟测试日志、切换记录、回退证明、保留／空间影响投影
和操作说明。所有结果只存在于当前 Python 进程，不能替代来源文档、真实
manifest、日志、审计或业务事实，也不会写入索引、调用模型或启动运行时。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage079.atomic_index_switch.phase4.delivery.v1"
RECORD_KIND = "ATOMIC_INDEX_SWITCH_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_ATOMIC_INDEX_SWITCH_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_ATOMIC_INDEX_SWITCH_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE079-P4-GATE"
NEXT_GATE = "IDS-STAGE079-REVIEW-GATE"
P3_PASS_RESULT = "PASS_ATOMIC_INDEX_SWITCH_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P2_EXECUTION_STATE = "COMPLETED_IN_MEMORY_ATOMIC_INDEX_SWITCH_CONTROL_SLICE"
P2_SCENARIOS = (
    "fulltext_smoke_passed_switch_candidate",
    "vector_build_incomplete_preserves_active",
    "hybrid_smoke_test_failure_blocks_switch",
    "fulltext_switch_failure_preserves_active",
    "hybrid_rollback_candidate_retains_previous",
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
    "rollback_record_ref",
    "index_kind",
    "rollback_target_index_version_ref",
    "retention_window_state",
    "rollback_state",
    "rollback_applied",
)
OLD_INDEX_RETENTION_FIELDS = (
    "retention_policy_ref",
    "applies_to_control_scenario_count",
    "retained_previous_active_required",
    "retention_window_state",
    "space_impact_state",
    "actual_space_impact_measurement_performed",
    "actual_index_deletion_performed",
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

Phase3ReportProvider = Callable[[], Mapping[str, Any]]
Phase2ReportProvider = Callable[[], Mapping[str, Any]]


def build_atomic_index_switch_phase4_delivery_report(
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
    retention = _old_index_retention_projection() if predecessors_valid else {}
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
        "stage078_review_evidence_declared": True,
        "stage079_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "stage080_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_flags,
        "chinese_feedback": [
            "索引清单、冒烟测试日志、切换记录和回退证明仅为内存控制投影，未写入实际索引或日志。",
            "旧活动版本保留只表达回滚前置，空间影响未测量、未删除，须业务线白箱人工处理。",
            "索引重建、暂停和恢复说明只描述未来操作前置，活动版本与实际服务均未变更。",
            "本交付不替代来源文档、业务线白箱复核或真实生产验收。",
        ],
    }


def _default_phase3_report_provider() -> Mapping[str, Any]:
    return _load_phase3_module().build_atomic_index_switch_phase3_report()


def _default_phase2_report_provider() -> Mapping[str, Any]:
    module = _load_phase2_module()
    return module.execute_atomic_index_switch_control_slice(module.build_control_input())


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _load_phase3_module() -> Any:
    return _load_module(
        "stage079_phase3_scenarios", "stage079_atomic_index_switch_scenarios.py"
    )


def _load_phase2_module() -> Any:
    return _load_module(
        "stage079_phase2_slice", "stage079_atomic_index_switch_control_slice.py"
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
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("control_views_preserved") is True
        and report.get("phase2_control_record_field_check_count") == 205
        and report.get("scenario_count") == 6
        and report.get("passed_scenario_count") == 6
        and report.get("scenario_field_count") == 26
        and report.get("scenario_field_check_count") == 156
        and report.get("operations_version_control_view_count") == 5
        and report.get("report_snapshot_version_control_view_count") == 5
        and [item.get("scenario_id") for item in results] == expected_ids
        and _records_have_exact_shape(results, 6, module.SCENARIO_RESULT_FIELDS)
        and all(item.get("expectation_met") is True for item in results)
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
    )


def _phase2_report_is_valid(module: Any, report: Mapping[str, Any]) -> bool:
    groups = (
        ("index_version_control_records", module.INDEX_VERSION_RECORD_FIELDS),
        ("candidate_build_control_projections", module.CANDIDATE_BUILD_FIELDS),
        ("active_pointer_control_projections", module.ACTIVE_POINTER_FIELDS),
        ("smoke_test_control_projections", module.SMOKE_TEST_PROJECTION_FIELDS),
        ("switch_control_projections", module.SWITCH_PROJECTION_FIELDS),
        ("rollback_control_projections", module.ROLLBACK_PROJECTION_FIELDS),
    )
    return (
        report.get("input_accepted") is True
        and report.get("execution_state") == P2_EXECUTION_STATE
        and report.get("control_scenarios_covered") == list(P2_SCENARIOS)
        and report.get("control_request_count") == 5
        and report.get("actual_input_request_count") == 0
        and report.get("all_candidate_versions_are_isolated") is True
        and report.get("all_old_active_versions_continue_serving") is True
        and report.get("all_active_pointer_projections_unchanged") is True
        and report.get("all_rollback_targets_reference_retained_previous_active")
        is True
        and all(
            _records_have_exact_shape(_as_records(report.get(key)), 5, fields)
            for key, fields in groups
        )
        and all(report.get(field) is False for field in P2_RUNTIME_CLOSED_FIELDS)
    )


def _index_manifest_samples(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = _as_records(report.get("index_version_control_records"))
    pointers = _as_records(report.get("active_pointer_control_projections"))
    return [
        {
            "control_scenario": scenario,
            "index_manifest_ref": f"index-manifest:control:stage079-p2:{scenario}",
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
                "smoke-test-log:control:stage079-p2:"
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
    return [
        {
            "control_scenario": record["control_scenario"],
            "rollback_proof_ref": (
                f"rollback-proof:control:stage079-p2:{record['control_scenario']}"
            ),
            "rollback_record_ref": record["rollback_record_ref"],
            "index_kind": record["index_kind"],
            "rollback_target_index_version_ref": record[
                "rollback_target_index_version_ref"
            ],
            "retention_window_state": record["retention_window_state"],
            "rollback_state": record["rollback_state"],
            "rollback_applied": record["rollback_applied"],
        }
        for record in _as_records(report.get("rollback_control_projections"))
    ]


def _old_index_retention_projection() -> dict[str, Any]:
    return {
        "retention_policy_ref": (
            "index-retention-policy:control:stage079-p2:previous-active"
        ),
        "applies_to_control_scenario_count": 5,
        "retained_previous_active_required": True,
        "retention_window_state": "CONTROL_PREVIOUS_ACTIVE_RETAINED",
        "space_impact_state": "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED",
        "actual_space_impact_measurement_performed": False,
        "actual_index_deletion_performed": False,
        "human_handling_required": True,
        "policy_state": "CONTROL_RETENTION_POLICY_NOT_PERSISTED",
    }


def _operational_instruction_projections() -> list[dict[str, Any]]:
    marker = ":control:stage079-p2:operations"
    return [
        {
            "instruction_id": "ATOMIC_INDEX_SWITCH_REBUILD_CONTROL_INSTRUCTION",
            "action": "REBUILD",
            "target_ref": f"index-rebuild{marker}",
            "entry_precondition": "AUTHORIZED_INPUT_AND_NEW_CANDIDATE_REQUIRED",
            "active_service_requirement": (
                "OLD_ACTIVE_VERSION_CONTINUES_UNTIL_SMOKE_TEST_PASSES_AND_SWITCH_IS_AUTHORIZED"
            ),
            "control_outcome": "CONTROL_REBUILD_NOT_STARTED",
            "actual_operation_performed": False,
            "human_handling_required": True,
        },
        {
            "instruction_id": "ATOMIC_INDEX_SWITCH_PAUSE_CONTROL_INSTRUCTION",
            "action": "PAUSE",
            "target_ref": f"index-pause{marker}",
            "entry_precondition": "ACTIVE_POINTER_MUST_REMAIN_UNCHANGED",
            "active_service_requirement": "OLD_ACTIVE_VERSION_CONTINUES_DURING_PAUSE",
            "control_outcome": "CONTROL_PAUSE_NOT_APPLIED",
            "actual_operation_performed": False,
            "human_handling_required": True,
        },
        {
            "instruction_id": "ATOMIC_INDEX_SWITCH_RECOVERY_CONTROL_INSTRUCTION",
            "action": "RECOVERY",
            "target_ref": f"index-recovery{marker}",
            "entry_precondition": "RETAINED_PREVIOUS_ACTIVE_REFERENCE_REQUIRED",
            "active_service_requirement": "RECOVERY_TARGET_MUST_BE_RETAINED_PREVIOUS_ACTIVE",
            "control_outcome": "CONTROL_RECOVERY_NOT_APPLIED",
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
        record.get("rollback_applied") is False
        and record.get("retention_window_state") == "CONTROL_PREVIOUS_ACTIVE_RETAINED"
        and _record_references_are_control_only(record)
    )


def _retention_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("applies_to_control_scenario_count") == 5
        and record.get("retained_previous_active_required") is True
        and record.get("retention_window_state") == "CONTROL_PREVIOUS_ACTIVE_RETAINED"
        and record.get("space_impact_state")
        == "CONTROL_SPACE_IMPACT_NOT_MEASURED_RUNTIME_DISABLED"
        and record.get("actual_space_impact_measurement_performed") is False
        and record.get("actual_index_deletion_performed") is False
        and record.get("human_handling_required") is True
        and record.get("policy_state") == "CONTROL_RETENTION_POLICY_NOT_PERSISTED"
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
        ":control:stage079-p2:" in str(value) for value in reference_values
    )


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
