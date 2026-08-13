"""Stage061 P4 的结构化数据质量 metadata-only 交付证据。

本模块只重放 Stage061 P3 的六类固定、非业务、reference-only 受控异常场景，
派生交付样例、字段推断引用报告、质量结果、人工建议与重解析/事实回滚说明。
它不读取、打开、解析、规范化、评估、统计、保存或写入任何真实表格、业务记录、
质量结果、结构化事实、证据或数据库内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage061.structured_data_quality.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_STRUCTURED_DATA_QUALITY_DELIVERY_REPORT"
OUTPUT_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_STRUCTURED_DATA_QUALITY_SAMPLE_NOT_REAL_QUALITY_RESULT"
)
FIELD_INFERENCE_REPORT_KIND = (
    "CONTROLLED_STRUCTURED_DATA_QUALITY_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE"
)
QUALITY_TEST_RESULT_KIND = (
    "CONTROLLED_STRUCTURED_DATA_QUALITY_TEST_RESULT_NOT_REAL_QUALITY_VALIDATION"
)
HANDLING_RECORD_KIND = (
    "CONTROLLED_STRUCTURED_DATA_QUALITY_HUMAN_HANDLING_NOT_REAL_TABLE_OBSERVATION"
)
REPARSE_AND_ROLLBACK_KIND = (
    "STRUCTURED_DATA_REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)
PASS_RESULT = "PASS_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_STRUCTURED_DATA_QUALITY_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE061-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_RETURN_STATE = "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
)
SCENARIO_FIELD_REFERENCE_LABELS = {
    "empty-table-control-explicit-closed": "field_completeness_control_reference",
    "merged-cells-control-human-handling": "merged_structure_control_reference",
    "unit-confusion-control-human-handling": "unit_consistency_control_reference",
    "date-format-variation-control-human-handling": "date_validity_control_reference",
    "outlier-control-numeric-block": "outlier_review_control_reference",
    "duplicate-row-control-human-handling": "primary_key_duplication_control_reference",
}
HANDLING_RECOMMENDATIONS_ZH = {
    "empty-table-control-explicit-closed": (
        "请业务线在未来授权输入门内人工确认空表是否具有可用表头和业务范围；当前 control "
        "不代表真实表格，不得形成质量结论、事实或统计结论。"
    ),
    "merged-cells-control-human-handling": (
        "请业务线在未来授权输入门内人工确认合并单元格结构；当前不展开、拆分或规范化任何 "
        "单元格，也不生成质量结果或结构化事实。"
    ),
    "unit-confusion-control-human-handling": (
        "请业务线在未来授权输入门内人工确认单位语义和换算依据；当前不进行单位归一化， "
        "不得形成数值事实、异常结论或统计结论。"
    ),
    "date-format-variation-control-human-handling": (
        "请业务线在未来授权输入门内人工确认日期格式和时区语义；当前不进行日期规范化， "
        "不得写入质量结果、事实库或业务结论。"
    ),
    "outlier-control-numeric-block": (
        "请业务线在未来授权输入门内人工评估异常数值候选及其来源证据；当前阻断数值统计、 "
        "异常判定和任何模型确定性数值结论。"
    ),
    "duplicate-row-control-human-handling": (
        "请业务线在未来授权输入门内人工确认主键重复候选；当前不删除、合并、去重或持久化 "
        "任何记录。"
    ),
}
P3_SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "table_schema_inference_performed",
    "field_identification_performed",
    "structured_fact_extraction_performed",
    "typed_value_extraction_performed",
    "table_summary_generation_performed",
    "field_completeness_evaluation_performed",
    "unit_consistency_evaluation_performed",
    "date_validity_evaluation_performed",
    "primary_key_duplication_evaluation_performed",
    "outlier_evaluation_performed",
    "quality_gate_evaluation_performed",
    "numeric_statistic_computation_performed",
    "actual_structured_fact_created",
    "actual_quality_result_created",
    "actual_quality_result_persisted",
    "actual_source_location_binding_created",
    "actual_evidence_record_created",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "quality_result_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

QualityReportProvider = Callable[[], Mapping[str, Any]]


def build_structured_data_quality_phase4_delivery_report(
    quality_report_provider: QualityReportProvider | None = None,
) -> dict[str, Any]:
    """从 P3 控制报告派生 P4 交付证据；返回值只包含固定控制元数据。"""

    provider = quality_report_provider or _load_phase3_report_provider()
    predecessor = provider()
    predecessor = predecessor if isinstance(predecessor, Mapping) else {}
    scenarios = _scenario_map(predecessor.get("scenario_results"))
    delivery_samples = _build_delivery_samples(scenarios)
    field_inference_report = _build_field_inference_report(predecessor, scenarios)
    quality_test_results = _build_quality_test_results(predecessor)
    handling_records = _build_human_handling_records(scenarios)
    reparse_and_fact_rollback = _reparse_and_fact_rollback_instructions()
    prompts = _human_confirmation_prompts()
    valid = _is_valid(
        predecessor,
        scenarios,
        delivery_samples,
        field_inference_report,
        quality_test_results,
        handling_records,
        reparse_and_fact_rollback,
        prompts,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "predecessor_result": predecessor.get("result"),
        "delivery_samples": delivery_samples,
        "field_inference_report": field_inference_report,
        "quality_test_results": quality_test_results,
        "unrecognized_structure_and_human_handling": handling_records,
        "quality_limitations_zh": [
            "本交付只来自六类固定非业务 control，不能代表真实 XLSX/CSV、生产记录、质检记录、工作表、表头、单元格、数值、日期或业务资料质量。",
            "字段推断报告只保留 P3 control 的引用标签，不构成真实字段识别、字段映射、质量验证、结构化事实、来源追溯或数值统计。",
            "人工处理建议、重解析和事实回滚说明均为未来授权输入门的白箱操作说明；当前没有真实文件、质量结果、事实库、人工任务或回滚动作。",
        ],
        "human_confirmation_prompts_zh": prompts,
        "reparse_and_fact_rollback_instructions": reparse_and_fact_rollback,
        "rollback": {
            "return_to": P3_RETURN_STATE,
            "revertable_artifacts": [
                "Stage061 Phase4 structured-data quality delivery module",
                "Stage061 Phase4 delivery contract",
                "Stage061 Phase4 focused tests",
                "Stage061 Phase4 governance projection",
            ],
            "preserve_predecessor_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "stage_review_status": "pending_next_run",
        "execution_ready": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
        "ids_business_source_read_performed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "field_completeness_evaluation_performed": False,
        "unit_consistency_evaluation_performed": False,
        "date_validity_evaluation_performed": False,
        "primary_key_duplication_evaluation_performed": False,
        "outlier_evaluation_performed": False,
        "quality_gate_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "actual_quality_result_rollback_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage061_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
    }


def _load_phase3_report_provider() -> QualityReportProvider:
    module_path = Path(__file__).with_name("stage061_structured_data_quality_scenarios.py")
    spec = importlib.util.spec_from_file_location(
        "stage061_p3_quality_scenarios", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage061 P3 structured-data quality scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_structured_data_quality_phase3_report


def _scenario_map(value: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        return {}
    mapped: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            return {}
        scenario_id = item.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id in mapped:
            return {}
        mapped[scenario_id] = item
    return mapped


def _build_delivery_samples(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        samples.append(
            {
                "sample_id": f"delivery-{scenario_id}",
                "sample_kind": OUTPUT_SAMPLE_KIND,
                "scenario_id": scenario_id,
                "scenario_category": scenario.get("scenario_category"),
                "quality_dimension": scenario.get("quality_dimension"),
                "quality_disposition": scenario.get("quality_disposition"),
                "field_inference_label": SCENARIO_FIELD_REFERENCE_LABELS[scenario_id],
                "quality_request_ref": scenario.get("quality_request_ref"),
                "referenced_quality_result_ref": scenario.get(
                    "referenced_quality_result_ref"
                ),
                "source_document_ref": scenario.get("source_document_ref"),
                "workbook_ref": scenario.get("workbook_ref"),
                "worksheet_ref": scenario.get("worksheet_ref"),
                "header_row_ref": scenario.get("header_row_ref"),
                "row_range_ref": scenario.get("row_range_ref"),
                "column_range_ref": scenario.get("column_range_ref"),
                "evidence_ref": scenario.get("evidence_ref"),
                "control_metadata_only": True,
                "source_content_retained": False,
                "typed_value_retained": False,
                "actual_field_mapping_created": False,
                "actual_quality_result_created": False,
                "actual_structured_fact_created": False,
                "actual_source_file_traceability_validated": False,
                "high_trust_direct_entry_allowed": False,
            }
        )
    return samples


def _build_field_inference_report(
    predecessor: Mapping[str, Any], scenarios: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    labels = [
        {
            "scenario_id": scenario_id,
            "field_label": SCENARIO_FIELD_REFERENCE_LABELS[scenario_id],
            "quality_dimension": scenarios[scenario_id].get("quality_dimension"),
            "candidate_selector_field": scenarios[scenario_id].get(
                "candidate_selector_field"
            ),
            "candidate_selector_value": scenarios[scenario_id].get(
                "candidate_selector_value"
            ),
            "control_reference_only": True,
            "actual_field_mapping_created": False,
        }
        for scenario_id in EXPECTED_SCENARIO_IDS
        if scenario_id in scenarios
    ]
    return {
        "report_kind": FIELD_INFERENCE_REPORT_KIND,
        "quality_result_candidate_pool_count": predecessor.get(
            "unique_quality_result_candidate_count"
        ),
        "referenced_field_label_count": len(labels),
        "scenario_reference_count": len(labels),
        "field_reference_labels": labels,
        "control_reference_only": True,
        "actual_field_mapping_created": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_quality_validation_performed": False,
    }


def _build_quality_test_results(predecessor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": QUALITY_TEST_RESULT_KIND,
        "scenario_count": predecessor.get("scenario_count"),
        "passed_scenario_count": predecessor.get("passed_scenario_count"),
        "explicit_disposition_count": predecessor.get("explicit_disposition_count"),
        "silent_drop_count": predecessor.get("silent_drop_count"),
        "human_handling_required_count": predecessor.get(
            "human_handling_required_count"
        ),
        "all_taskpack_exception_categories_covered": predecessor.get(
            "all_taskpack_exception_categories_covered"
        ),
        "control_source_location_traceability_preserved": predecessor.get(
            "control_source_location_traceability_preserved"
        ),
        "all_quality_states_unassessed": predecessor.get(
            "all_quality_states_unassessed"
        ),
        "all_statistical_conclusions_blocked": predecessor.get(
            "all_statistical_conclusions_blocked"
        ),
        "actual_table_quality_validation_performed": False,
        "actual_source_file_traceability_validated": False,
        "actual_source_location_binding_created": False,
        "actual_evidence_record_created": False,
        "numeric_statistic_computation_performed": False,
        "model_definitive_numeric_conclusion_allowed": False,
    }


def _build_human_handling_records(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        records.append(
            {
                "record_kind": HANDLING_RECORD_KIND,
                "scenario_id": scenario_id,
                "scenario_category": scenario.get("scenario_category"),
                "quality_dimension": scenario.get("quality_dimension"),
                "quality_disposition": scenario.get("quality_disposition"),
                "human_handling_required": True,
                "recommendation_zh": HANDLING_RECOMMENDATIONS_ZH[scenario_id],
                "control_reference_only": True,
                "actual_unrecognized_table_structure_observed": False,
                "automatic_structure_resolution_performed": False,
                "automatic_quality_evaluation_performed": False,
                "automatic_quality_result_write_performed": False,
            }
        )
    return records


def _reparse_and_fact_rollback_instructions() -> dict[str, Any]:
    return {
        "record_kind": REPARSE_AND_ROLLBACK_KIND,
        "return_to": P3_RETURN_STATE,
        "in_memory_control_replay_only": True,
        "precondition_zh": (
            "未来若取得真实资料授权，须先由业务线 owner 明确来源、授权 fixture、输入范围、"
            "质量规则、事实存储、证据绑定、回滚点和恢复责任。"
        ),
        "current_action_zh": (
            "当前只允许重放 P3 固定 control 报告；若 P4 派生证据不一致，只撤回 P4 工件，"
            "保留 P1/P2/P3 证据。"
        ),
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "actual_quality_result_rollback_performed": False,
        "source_or_raw_data_change_allowed": False,
        "database_or_persistent_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _human_confirmation_prompts() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "confirm-structured-quality-control-delivery-boundary",
            "text": "请业务线确认：本交付只包含结构化数据质量的 control 元数据样例，不可替代真实质量结果、来源证据、结构化事实或数值统计。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-structured-quality-exception-handling-boundary",
            "text": "请业务线确认：六类异常均保留人工处理建议，当前没有自动解析、自动质量判定、自动质量结果写入或确定性模型结论。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-structured-quality-reparse-rollback-boundary",
            "text": "请业务线确认：表格重解析和事实回滚说明只适用于未来授权输入门；当前没有真实文件、质量结果库、事实库或回滚动作。",
            "automatic_confirmation_performed": False,
        },
    ]


def _is_valid(
    predecessor: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
    delivery_samples: list[Mapping[str, Any]],
    field_inference_report: Mapping[str, Any],
    quality_test_results: Mapping[str, Any],
    handling_records: list[Mapping[str, Any]],
    reparse_and_fact_rollback: Mapping[str, Any],
    prompts: list[Mapping[str, Any]],
) -> bool:
    predecessor_shape_valid = (
        predecessor.get("valid") is True
        and predecessor.get("result") == P3_PASS_RESULT
        and predecessor.get("next_gate") == "IDS-STAGE061-P4-GATE"
        and predecessor.get("phase2_control_slice_reexecuted") is True
        and predecessor.get("phase2_shape_preserved") is True
        and predecessor.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("explicit_disposition_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("silent_drop_count") == 0
        and predecessor.get("human_handling_required_count")
        == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("unique_quality_result_candidate_count")
        == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("all_taskpack_exception_categories_covered") is True
        and predecessor.get("control_source_location_traceability_preserved") is True
        and predecessor.get("all_quality_states_unassessed") is True
        and predecessor.get("all_statistical_conclusions_blocked") is True
        and predecessor.get("actual_source_file_traceability_validated") is False
        and predecessor.get("actual_evidence_record_created") is False
        and predecessor.get("actual_structured_fact_created") is False
        and predecessor.get("actual_quality_result_created") is False
        and all(predecessor.get(field) is False for field in P3_SIDE_EFFECT_FIELDS)
    )
    scenario_shape_valid = tuple(scenarios) == EXPECTED_SCENARIO_IDS and all(
        item.get("control_scenario_metadata_only") is True
        and item.get("expectation_met") is True
        and item.get("explicit_disposition") is True
        and item.get("silent_drop") is False
        and item.get("human_handling_required") is True
        and item.get("source_location_reference_preserved") is True
        and item.get("control_reference_only") is True
        and item.get("real_table_content_evaluated") is False
        and item.get("actual_source_file_traceability_validated") is False
        and item.get("actual_evidence_record_created") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("actual_quality_result_created") is False
        for item in scenarios.values()
    )
    delivery_shape_valid = len(delivery_samples) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("sample_kind") == OUTPUT_SAMPLE_KIND
        and item.get("control_metadata_only") is True
        and _control_references_preserved(item)
        and item.get("source_content_retained") is False
        and item.get("typed_value_retained") is False
        and item.get("actual_field_mapping_created") is False
        and item.get("actual_quality_result_created") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("high_trust_direct_entry_allowed") is False
        for item in delivery_samples
    )
    inference_valid = (
        field_inference_report.get("report_kind") == FIELD_INFERENCE_REPORT_KIND
        and field_inference_report.get("quality_result_candidate_pool_count") == 6
        and field_inference_report.get("scenario_reference_count") == 6
        and field_inference_report.get("referenced_field_label_count") == 6
        and len(field_inference_report.get("field_reference_labels", [])) == 6
        and field_inference_report.get("control_reference_only") is True
        and field_inference_report.get("actual_field_mapping_created") is False
        and field_inference_report.get("real_table_schema_inference_performed")
        is False
        and field_inference_report.get("real_field_identification_performed")
        is False
        and field_inference_report.get("real_structured_fact_extraction_performed")
        is False
        and field_inference_report.get("real_quality_validation_performed") is False
    )
    quality_valid = (
        quality_test_results.get("report_kind") == QUALITY_TEST_RESULT_KIND
        and quality_test_results.get("scenario_count") == 6
        and quality_test_results.get("passed_scenario_count") == 6
        and quality_test_results.get("explicit_disposition_count") == 6
        and quality_test_results.get("silent_drop_count") == 0
        and quality_test_results.get("human_handling_required_count") == 6
        and quality_test_results.get("all_taskpack_exception_categories_covered")
        is True
        and quality_test_results.get("control_source_location_traceability_preserved")
        is True
        and quality_test_results.get("all_quality_states_unassessed") is True
        and quality_test_results.get("all_statistical_conclusions_blocked") is True
        and quality_test_results.get("actual_table_quality_validation_performed")
        is False
        and quality_test_results.get("actual_source_file_traceability_validated")
        is False
        and quality_test_results.get("actual_evidence_record_created") is False
    )
    handling_valid = len(handling_records) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("record_kind") == HANDLING_RECORD_KIND
        and item.get("human_handling_required") is True
        and isinstance(item.get("recommendation_zh"), str)
        and bool(item.get("recommendation_zh"))
        and item.get("actual_unrecognized_table_structure_observed") is False
        and item.get("automatic_structure_resolution_performed") is False
        and item.get("automatic_quality_evaluation_performed") is False
        and item.get("automatic_quality_result_write_performed") is False
        for item in handling_records
    )
    rollback_valid = (
        reparse_and_fact_rollback.get("record_kind") == REPARSE_AND_ROLLBACK_KIND
        and reparse_and_fact_rollback.get("return_to") == P3_RETURN_STATE
        and reparse_and_fact_rollback.get("in_memory_control_replay_only") is True
        and reparse_and_fact_rollback.get("actual_file_reparse_performed") is False
        and reparse_and_fact_rollback.get("actual_fact_store_present") is False
        and reparse_and_fact_rollback.get("actual_fact_rollback_performed") is False
        and reparse_and_fact_rollback.get("actual_quality_result_rollback_performed")
        is False
    )
    prompts_valid = len(prompts) == 3 and all(
        isinstance(item.get("text"), str)
        and bool(item.get("text"))
        and item.get("automatic_confirmation_performed") is False
        for item in prompts
    )
    return all(
        (
            predecessor_shape_valid,
            scenario_shape_valid,
            delivery_shape_valid,
            inference_valid,
            quality_valid,
            handling_valid,
            rollback_valid,
            prompts_valid,
        )
    )


def _control_references_preserved(sample: Mapping[str, Any]) -> bool:
    fields = (
        "quality_request_ref",
        "referenced_quality_result_ref",
        "source_document_ref",
        "workbook_ref",
        "worksheet_ref",
        "header_row_ref",
        "row_range_ref",
        "column_range_ref",
        "evidence_ref",
    )
    return all(
        isinstance(sample.get(field), str) and ":control:" in sample[field]
        for field in fields
    )
