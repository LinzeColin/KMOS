"""Stage083 P4 的纯内存关键词检索基线交付证据。

模块只复用 Stage083 P3 的八个受控场景，派生 metadata-only 的检索样例、
trace 日志、过滤结果、有效性测试报告、证据缺口和参数回滚说明。全部结果只
存在于当前 Python 进程，不能替代来源文档、真实检索结果、证据账本、审计或
业务事实，也不会写入参数、调用模型或启动运行时。
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage083.keyword_retrieval_baseline.phase4.delivery.v1"
RECORD_KIND = "KEYWORD_RETRIEVAL_BASELINE_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_KEYWORD_RETRIEVAL_BASELINE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_KEYWORD_RETRIEVAL_BASELINE_DELIVERY_EVIDENCE_RUNTIME_DISABLED"
ENTRY_GATE = "IDS-STAGE083-P4-GATE"
NEXT_GATE = "IDS-STAGE083-REVIEW-GATE"
P3_PASS_RESULT = "PASS_KEYWORD_RETRIEVAL_BASELINE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
CONTROL_PREFIX = ":control:stage083-p2:"

RETRIEVAL_SAMPLE_FIELDS = (
    "scenario_id",
    "retrieval_sample_ref",
    "query_ref",
    "candidate_ref",
    "selected_result_ref",
    "active_index_version_ref",
    "sample_state",
    "actual_retrieval_sample_written",
    "human_handling_required",
    "explicit_disposition",
)
TRACE_LOG_FIELDS = (
    "scenario_id",
    "trace_log_ref",
    "retrieval_trace_ref",
    "active_index_version_ref",
    "evidence_ledger_ref",
    "trace_version_state",
    "log_state",
    "actual_trace_log_written",
    "human_handling_required",
    "explicit_disposition",
)
FILTER_RESULT_FIELDS = (
    "scenario_id",
    "filter_result_ref",
    "metadata_filter_refs",
    "filter_reference_count",
    "filter_state",
    "result_state",
    "actual_metadata_filter_evaluation_performed",
    "actual_filter_result_written",
    "human_handling_required",
    "explicit_disposition",
)
VALIDITY_TEST_REPORT_FIELDS = (
    "scenario_id",
    "validity_test_report_ref",
    "requested_top_k_ref",
    "hybrid_score_ref",
    "score_explanation_ref",
    "selected_result_ref",
    "observed_result_validity_state",
    "report_state",
    "actual_validity_test_executed",
    "human_handling_required",
    "explicit_disposition",
)
EVIDENCE_GAP_FIELDS = (
    "scenario_id",
    "evidence_gap_record_ref",
    "gap_category",
    "gap_state",
    "evidence_ledger_ref",
    "gap_resolution_state",
    "actual_evidence_gap_record_written",
    "automatic_resolution_allowed",
    "human_handling_required",
    "explicit_disposition",
)
PARAMETER_ROLLBACK_INSTRUCTION_FIELDS = (
    "instruction_id",
    "parameter_scope_ref",
    "rollback_target_ref",
    "entry_precondition",
    "rollback_state",
    "actual_retrieval_parameter_rollback_performed",
    "human_handling_required",
    "explicit_disposition",
)

P3_RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "bulk_import_execution_performed",
    "database_schema_migration_performed",
    "database_connection_performed",
    "postgresql_fts_index_build_performed",
    "pgvector_index_build_performed",
    "keyword_retrieval_query_performed",
    "vector_retrieval_query_performed",
    "metadata_filter_evaluation_performed",
    "hybrid_ranking_performed",
    "top_k_selection_performed",
    "retrieval_trace_read_performed",
    "retrieval_trace_write_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
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
RUNTIME_CLOSED_FIELDS = (
    *P3_RUNTIME_CLOSED_FIELDS,
    "actual_retrieval_sample_written",
    "actual_trace_log_written",
    "actual_filter_result_written",
    "actual_validity_test_report_written",
    "actual_evidence_gap_record_written",
    "actual_retrieval_parameter_rollback_performed",
    "actual_chinese_feedback_published",
)

P3_SCENARIO_COUNT = 8
P3_SCENARIO_FIELD_COUNT = 26
P3_SCENARIO_FIELD_CHECK_COUNT = 208
P2_CONTROL_FIELD_CHECK_COUNT = 250

Phase3ReportProvider = Callable[[], Mapping[str, Any]]


def build_keyword_retrieval_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
) -> dict[str, Any]:
    """从已验证的 Stage083 P3 场景派生 P4 metadata-only 交付证据。"""

    phase3_module = _load_phase3_module()
    phase3_report = _provider_result(
        phase3_report_provider or _default_phase3_report_provider
    )
    phase3_valid = _phase3_report_is_valid(phase3_module, phase3_report)
    scenario_results = _as_records(phase3_report.get("scenario_results"))
    records = scenario_results if phase3_valid else []

    samples = _retrieval_samples(records)
    trace_logs = _trace_logs(records)
    filter_results = _filter_results(records)
    validity_reports = _validity_reports(records)
    evidence_gaps = _evidence_gaps(records)
    rollback_instructions = _parameter_rollback_instructions() if phase3_valid else []
    runtime_flags = _runtime_closed_flags()

    delivery_integrity = (
        phase3_valid
        and _records_have_exact_shape(samples, P3_SCENARIO_COUNT, RETRIEVAL_SAMPLE_FIELDS)
        and _records_have_exact_shape(trace_logs, P3_SCENARIO_COUNT, TRACE_LOG_FIELDS)
        and _records_have_exact_shape(
            filter_results, P3_SCENARIO_COUNT, FILTER_RESULT_FIELDS
        )
        and _records_have_exact_shape(
            validity_reports, P3_SCENARIO_COUNT, VALIDITY_TEST_REPORT_FIELDS
        )
        and _records_have_exact_shape(evidence_gaps, P3_SCENARIO_COUNT, EVIDENCE_GAP_FIELDS)
        and _records_have_exact_shape(
            rollback_instructions,
            3,
            PARAMETER_ROLLBACK_INSTRUCTION_FIELDS,
        )
        and all(_retrieval_sample_is_control_only(item) for item in samples)
        and all(_trace_log_is_control_only(item) for item in trace_logs)
        and all(_filter_result_is_control_only(item) for item in filter_results)
        and all(_validity_report_is_control_only(item) for item in validity_reports)
        and all(_evidence_gap_is_control_only(item) for item in evidence_gaps)
        and all(
            _rollback_instruction_is_control_only(item) for item in rollback_instructions
        )
        and all(value is False for value in runtime_flags.values())
    )
    valid = bool(delivery_integrity)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "phase3_controlled_scenarios_reexecuted_in_memory_only": phase3_valid,
        "phase3_controlled_scenarios_report_valid": phase3_valid,
        "delivery_evidence_metadata_only": True,
        "retrieval_sample_control_records": samples,
        "retrieval_sample_control_record_count": len(samples),
        "retrieval_sample_field_count": len(RETRIEVAL_SAMPLE_FIELDS),
        "trace_log_control_records": trace_logs,
        "trace_log_control_record_count": len(trace_logs),
        "trace_log_field_count": len(TRACE_LOG_FIELDS),
        "filter_result_control_records": filter_results,
        "filter_result_control_record_count": len(filter_results),
        "filter_result_field_count": len(FILTER_RESULT_FIELDS),
        "validity_test_report_control_records": validity_reports,
        "validity_test_report_control_record_count": len(validity_reports),
        "validity_test_report_field_count": len(VALIDITY_TEST_REPORT_FIELDS),
        "evidence_gap_control_records": evidence_gaps,
        "evidence_gap_control_record_count": len(evidence_gaps),
        "evidence_gap_field_count": len(EVIDENCE_GAP_FIELDS),
        "parameter_rollback_instruction_control_records": rollback_instructions,
        "parameter_rollback_instruction_count": len(rollback_instructions),
        "parameter_rollback_instruction_field_count": len(
            PARAMETER_ROLLBACK_INSTRUCTION_FIELDS
        ),
        "delivery_field_check_count": _delivery_field_check_count(
            samples,
            trace_logs,
            filter_results,
            validity_reports,
            evidence_gaps,
            rollback_instructions,
        ),
        "all_delivery_references_control_only": all(
            _record_references_are_control_only(item)
            for group in (
                samples,
                trace_logs,
                filter_results,
                validity_reports,
                evidence_gaps,
                rollback_instructions,
            )
            for item in group
        ),
        "source_document_remains_authoritative": True,
        "business_line_whitebox_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "automatic_gap_resolution_allowed": False,
        "automatic_business_recommendation_allowed": False,
        "actual_input_request_count": 0,
        "actual_keyword_retrieval_query_count": 0,
        "actual_vector_retrieval_query_count": 0,
        "actual_metadata_filter_evaluation_count": 0,
        "actual_hybrid_ranking_count": 0,
        "actual_top_k_selection_count": 0,
        "actual_retrieval_trace_access_count": 0,
        "actual_evidence_ledger_access_count": 0,
        "actual_retrieval_sample_record_write_count": 0,
        "actual_trace_log_record_write_count": 0,
        "actual_filter_result_record_write_count": 0,
        "actual_validity_test_report_write_count": 0,
        "actual_evidence_gap_record_write_count": 0,
        "actual_retrieval_parameter_rollback_count": 0,
        "stage082_review_evidence_declared": True,
        "stage083_started": True,
        "phase1_completed": True,
        "phase2_completed": True,
        "phase3_completed": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "stage084_started": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        **runtime_flags,
        "chinese_feedback": [
            "检索样例、trace、过滤结果和有效性报告均为内存控制投影，未写入真实资料或日志。",
            "检索不足与证据缺口已逐场景显式记录，仍需业务线白箱人工处理，自动补全和自动采纳保持关闭。",
            "关键词基线、过滤与排序参数没有实时值可回滚；未来授权变更必须先具备版本化参数、白箱批准和可验证回退目标。",
            "本阶段不执行数据库、检索、参数写入或回滚、模型、Agent、OVH、生产、上传或推送。",
        ],
    }


def _default_phase3_report_provider() -> Mapping[str, Any]:
    return _load_phase3_module().build_keyword_retrieval_phase3_report()


def _provider_result(provider: Callable[[], Mapping[str, Any]]) -> Mapping[str, Any]:
    result = provider()
    return result if isinstance(result, Mapping) else {}


def _load_phase3_module() -> Any:
    path = Path(__file__).with_name("stage083_keyword_retrieval_baseline_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage083_phase3_scenarios", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage083 P3 keyword retrieval scenarios")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase3_report_is_valid(module: Any, report: Mapping[str, Any]) -> bool:
    scenarios = _as_records(report.get("scenario_results"))
    expected_ids = [item["scenario_id"] for item in module.SCENARIOS]
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("next_gate") == ENTRY_GATE
        and report.get("phase2_control_slice_reexecuted") is True
        and report.get("phase2_shape_preserved") is True
        and report.get("phase2_side_effect_free") is True
        and report.get("phase2_control_record_field_check_count")
        == P2_CONTROL_FIELD_CHECK_COUNT
        and report.get("scenario_count") == P3_SCENARIO_COUNT
        and report.get("scenario_field_count") == P3_SCENARIO_FIELD_COUNT
        and report.get("scenario_field_check_count") == P3_SCENARIO_FIELD_CHECK_COUNT
        and report.get("passed_scenario_count") == P3_SCENARIO_COUNT
        and report.get("keyword_and_domain_coverage_preserved") is True
        and report.get("filter_combination_preserved") is True
        and report.get("top_k_ranking_and_validity_preserved") is True
        and report.get("old_index_trace_version_preserved") is True
        and report.get("all_control_references_opaque") is True
        and [item.get("scenario_id") for item in scenarios] == expected_ids
        and _records_have_exact_shape(
            scenarios, P3_SCENARIO_COUNT, module.SCENARIO_RESULT_FIELDS
        )
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("silent_drop") is False for item in scenarios)
        and all(report.get(field) is False for field in module.RUNTIME_CLOSED_FIELDS)
        and report.get("stage082_review_evidence_declared") is True
        and report.get("stage083_started") is True
        and report.get("phase1_completed") is True
        and report.get("phase2_completed") is True
        and report.get("phase3_started") is True
        and report.get("phase4_started") is False
        and report.get("whole_stage_review_performed") is False
        and report.get("stage084_started") is False
        and report.get("github_upload_allowed") is False
        and report.get("push_allowed") is False
    )


def _retrieval_samples(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": _text(item, "scenario_id"),
            "retrieval_sample_ref": (
                f"retrieval-sample{CONTROL_PREFIX}{_text(item, 'scenario_id')}"
            ),
            "query_ref": _text(item, "query_ref"),
            "candidate_ref": _text(item, "candidate_ref"),
            "selected_result_ref": _text(item, "selected_result_ref"),
            "active_index_version_ref": _text(item, "active_index_version_ref"),
            "sample_state": "CONTROL_RETRIEVAL_SAMPLE_NOT_PERSISTED",
            "actual_retrieval_sample_written": False,
            "human_handling_required": item.get("human_handling_required") is True,
            "explicit_disposition": _text(item, "explicit_disposition"),
        }
        for item in records
    ]


def _trace_logs(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": _text(item, "scenario_id"),
            "trace_log_ref": f"trace-log{CONTROL_PREFIX}{_text(item, 'scenario_id')}",
            "retrieval_trace_ref": _text(item, "retrieval_trace_ref"),
            "active_index_version_ref": _text(item, "active_index_version_ref"),
            "evidence_ledger_ref": _text(item, "evidence_ledger_ref"),
            "trace_version_state": _text(item, "observed_old_index_trace_state"),
            "log_state": "CONTROL_TRACE_LOG_NOT_PERSISTED",
            "actual_trace_log_written": False,
            "human_handling_required": item.get("human_handling_required") is True,
            "explicit_disposition": _text(item, "explicit_disposition"),
        }
        for item in records
    ]


def _filter_results(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": _text(item, "scenario_id"),
            "filter_result_ref": (
                f"filter-result{CONTROL_PREFIX}{_text(item, 'scenario_id')}"
            ),
            "metadata_filter_refs": _refs(item.get("metadata_filter_refs")),
            "filter_reference_count": len(_refs(item.get("metadata_filter_refs"))),
            "filter_state": _text(item, "observed_filter_combination_state"),
            "result_state": "CONTROL_FILTER_RESULT_NOT_EVALUATED_OR_PERSISTED",
            "actual_metadata_filter_evaluation_performed": False,
            "actual_filter_result_written": False,
            "human_handling_required": item.get("human_handling_required") is True,
            "explicit_disposition": _text(item, "explicit_disposition"),
        }
        for item in records
    ]


def _validity_reports(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": _text(item, "scenario_id"),
            "validity_test_report_ref": (
                f"validity-test-report{CONTROL_PREFIX}{_text(item, 'scenario_id')}"
            ),
            "requested_top_k_ref": _text(item, "requested_top_k_ref"),
            "hybrid_score_ref": _text(item, "hybrid_score_ref"),
            "score_explanation_ref": _text(item, "score_explanation_ref"),
            "selected_result_ref": _text(item, "selected_result_ref"),
            "observed_result_validity_state": _text(
                item, "observed_result_validity_state"
            ),
            "report_state": "CONTROL_VALIDITY_TEST_REPORT_NOT_EXECUTED_OR_PERSISTED",
            "actual_validity_test_executed": False,
            "human_handling_required": item.get("human_handling_required") is True,
            "explicit_disposition": _text(item, "explicit_disposition"),
        }
        for item in records
    ]


def _evidence_gaps(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scenario_id": _text(item, "scenario_id"),
            "evidence_gap_record_ref": (
                f"evidence-gap{CONTROL_PREFIX}{_text(item, 'scenario_id')}"
            ),
            "gap_category": _text(item, "scenario_category"),
            "gap_state": "CONTROL_RETRIEVAL_INSUFFICIENCY_OR_EVIDENCE_GAP_REQUIRES_WHITEBOX",
            "evidence_ledger_ref": _text(item, "evidence_ledger_ref"),
            "gap_resolution_state": "CONTROL_AUTOMATIC_GAP_RESOLUTION_DISABLED",
            "actual_evidence_gap_record_written": False,
            "automatic_resolution_allowed": False,
            "human_handling_required": item.get("human_handling_required") is True,
            "explicit_disposition": _text(item, "explicit_disposition"),
        }
        for item in records
    ]


def _parameter_rollback_instructions() -> list[dict[str, Any]]:
    controls = (
        (
            "KEYWORD_BASELINE_PARAMETER_ROLLBACK_CONTROL",
            "keyword_document_type_filter_reference_only",
        ),
        (
            "METADATA_FILTER_PARAMETER_ROLLBACK_CONTROL",
            "keyword_year_filter_reference_only",
        ),
        (
            "RANKING_AND_TOP_K_PARAMETER_ROLLBACK_CONTROL",
            "hybrid_evidence_level_filter_reference_only",
        ),
    )
    return [
        {
            "instruction_id": instruction_id,
            "parameter_scope_ref": f"retrieval-parameter{CONTROL_PREFIX}{scenario}",
            "rollback_target_ref": f"stage083-p3-control-boundary{CONTROL_PREFIX}{scenario}",
            "entry_precondition": (
                "VERSIONED_PARAMETER_CHANGE_AND_BUSINESS_LINE_WHITEBOX_APPROVAL_REQUIRED"
            ),
            "rollback_state": "CONTROL_NO_LIVE_RETRIEVAL_PARAMETER_TO_ROLLBACK",
            "actual_retrieval_parameter_rollback_performed": False,
            "human_handling_required": True,
            "explicit_disposition": "CONTROL_PARAMETER_ROLLBACK_REQUIRES_BUSINESS_LINE_WHITEBOX",
        }
        for instruction_id, scenario in controls
    ]


def _retrieval_sample_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("sample_state") == "CONTROL_RETRIEVAL_SAMPLE_NOT_PERSISTED"
        and record.get("actual_retrieval_sample_written") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _trace_log_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("trace_version_state")
        == "CONTROL_OLD_INDEX_TRACE_VERSION_MATCH_NOT_WRITTEN"
        and record.get("log_state") == "CONTROL_TRACE_LOG_NOT_PERSISTED"
        and record.get("actual_trace_log_written") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _filter_result_is_control_only(record: Mapping[str, Any]) -> bool:
    refs = _refs(record.get("metadata_filter_refs"))
    return (
        bool(refs)
        and record.get("filter_reference_count") == len(refs)
        and str(record.get("filter_state", "")).startswith("CONTROL_")
        and record.get("result_state")
        == "CONTROL_FILTER_RESULT_NOT_EVALUATED_OR_PERSISTED"
        and record.get("actual_metadata_filter_evaluation_performed") is False
        and record.get("actual_filter_result_written") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _validity_report_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("observed_result_validity_state")
        == "CONTROL_RESULT_VALIDITY_DECLARED_NOT_EXECUTED"
        and record.get("report_state")
        == "CONTROL_VALIDITY_TEST_REPORT_NOT_EXECUTED_OR_PERSISTED"
        and record.get("actual_validity_test_executed") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _evidence_gap_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("gap_state")
        == "CONTROL_RETRIEVAL_INSUFFICIENCY_OR_EVIDENCE_GAP_REQUIRES_WHITEBOX"
        and record.get("gap_resolution_state")
        == "CONTROL_AUTOMATIC_GAP_RESOLUTION_DISABLED"
        and record.get("actual_evidence_gap_record_written") is False
        and record.get("automatic_resolution_allowed") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _rollback_instruction_is_control_only(record: Mapping[str, Any]) -> bool:
    return (
        record.get("entry_precondition")
        == "VERSIONED_PARAMETER_CHANGE_AND_BUSINESS_LINE_WHITEBOX_APPROVAL_REQUIRED"
        and record.get("rollback_state")
        == "CONTROL_NO_LIVE_RETRIEVAL_PARAMETER_TO_ROLLBACK"
        and record.get("actual_retrieval_parameter_rollback_performed") is False
        and record.get("human_handling_required") is True
        and _record_references_are_control_only(record)
    )


def _delivery_field_check_count(
    samples: Sequence[Mapping[str, Any]],
    trace_logs: Sequence[Mapping[str, Any]],
    filter_results: Sequence[Mapping[str, Any]],
    validity_reports: Sequence[Mapping[str, Any]],
    evidence_gaps: Sequence[Mapping[str, Any]],
    rollback_instructions: Sequence[Mapping[str, Any]],
) -> int:
    return (
        len(samples) * len(RETRIEVAL_SAMPLE_FIELDS)
        + len(trace_logs) * len(TRACE_LOG_FIELDS)
        + len(filter_results) * len(FILTER_RESULT_FIELDS)
        + len(validity_reports) * len(VALIDITY_TEST_REPORT_FIELDS)
        + len(evidence_gaps) * len(EVIDENCE_GAP_FIELDS)
        + len(rollback_instructions) * len(PARAMETER_ROLLBACK_INSTRUCTION_FIELDS)
    )


def _records_have_exact_shape(
    records: Sequence[Mapping[str, Any]], count: int, fields: Sequence[str]
) -> bool:
    return len(records) == count and all(set(record) == set(fields) for record in records)


def _as_records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _text(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    return value if isinstance(value, str) else ""


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _record_references_are_control_only(record: Mapping[str, Any]) -> bool:
    reference_values: list[str] = []
    for field, value in record.items():
        if field.endswith("_ref") and isinstance(value, str):
            reference_values.append(value)
        elif field.endswith("_refs"):
            reference_values.extend(_refs(value))
    return bool(reference_values) and all(CONTROL_PREFIX in value for value in reference_values)


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}
