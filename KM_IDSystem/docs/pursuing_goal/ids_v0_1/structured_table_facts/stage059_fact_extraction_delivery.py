"""Stage059 P4 的事实抽取 metadata-only 交付证据。

模块只从 P3 的六类固定、非业务、reference-only 控制场景派生事实样例、字段
引用报告、质量结果、人工处理建议及重解析/事实回滚说明。它不读取、打开、解析、
规范化、统计或保存任何真实 XLSX、CSV、工作表、单元格、事实或证据内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage059.fact_extraction.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_FACT_EXTRACTION_DELIVERY_REPORT"
OUTPUT_SAMPLE_KIND = "DELIVERY_METADATA_ONLY_FACT_SAMPLE_NOT_REAL_STRUCTURED_FACT"
FIELD_INFERENCE_REPORT_KIND = (
    "CONTROLLED_FACT_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE"
)
QUALITY_TEST_RESULT_KIND = (
    "CONTROLLED_FACT_EXTRACTION_QUALITY_TEST_RESULT_NOT_REAL_TABLE_VALIDATION"
)
HANDLING_RECORD_KIND = (
    "CONTROLLED_FACT_EXCEPTION_AND_HUMAN_HANDLING_NOT_REAL_TABLE_OBSERVATION"
)
REPARSE_AND_ROLLBACK_KIND = (
    "REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)
PASS_RESULT = "PASS_PHASE4_FACT_EXTRACTION_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_FACT_EXTRACTION_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE059-REVIEW-GATE"
P3_PASS_RESULT = (
    "PASS_PHASE3_FACT_EXTRACTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
)
P3_RETURN_STATE = (
    "PHASE3_FACT_EXTRACTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
)

EXPECTED_SCENARIO_IDS = (
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
)
SCENARIO_FIELD_REFERENCE_LABELS = {
    "empty-table-control-explicit-closed": "fact_type_control_reference",
    "merged-cells-control-human-handling": "record_type_control_reference",
    "unit-confusion-control-human-handling": "unit_ref_control_reference",
    "date-format-variation-control-human-handling": "record_date_ref_control_reference",
    "outlier-control-numeric-block": "field_type_control_reference",
    "duplicate-row-control-human-handling": "inspection_fact_type_control_reference",
}
HANDLING_RECOMMENDATIONS_ZH = {
    "empty-table-control-explicit-closed": (
        "请业务线在未来授权输入门内人工确认空表结构；当前 control 不代表真实表格，"
        "不得创建事实或统计结论。"
    ),
    "merged-cells-control-human-handling": (
        "请业务线在未来授权输入门内人工识别合并单元格结构；当前不解析、展开或"
        "规范化任何单元格。"
    ),
    "unit-confusion-control-human-handling": (
        "请业务线在未来授权输入门内人工确认单位含义；当前不进行单位换算，"
        "不得形成数值事实或统计结论。"
    ),
    "date-format-variation-control-human-handling": (
        "请业务线在未来授权输入门内人工确认日期格式；当前不进行日期规范化，"
        "不得写入事实库。"
    ),
    "outlier-control-numeric-block": (
        "请业务线在未来授权输入门内人工评估异常数值候选；当前阻断数值统计和"
        "任何确定性模型结论。"
    ),
    "duplicate-row-control-human-handling": (
        "请业务线在未来授权输入门内人工确认重复行候选；当前不删除、合并或"
        "持久化任何记录。"
    ),
}
P3_SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "real_table_schema_inference_performed",
    "real_field_identification_performed",
    "real_structured_fact_extraction_performed",
    "real_table_content_evaluated",
    "typed_value_extraction_performed",
    "merged_cell_resolution_performed",
    "unit_normalization_performed",
    "date_normalization_performed",
    "outlier_evaluation_performed",
    "duplicate_row_evaluation_performed",
    "numeric_statistic_computation_performed",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "rag_summary_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "github_upload_performed",
    "push_performed",
)

QualityReportProvider = Callable[[], Mapping[str, Any]]


def build_fact_extraction_phase4_delivery_report(
    quality_report_provider: QualityReportProvider | None = None,
) -> dict[str, Any]:
    """派生 P4 交付证据；返回值只包含固定 control 元数据。"""

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
            "字段推断报告只保留 P3 control 的候选引用标签，不构成真实字段识别、事实抽取、来源追溯或数值统计。",
            "人工处理建议、重解析和事实回滚说明均为未来授权输入门的白箱操作说明；当前没有真实文件、事实库、人工任务、回滚动作或运行时状态。",
        ],
        "human_confirmation_prompts_zh": prompts,
        "reparse_and_fact_rollback_instructions": reparse_and_fact_rollback,
        "rollback": {
            "return_to": P3_RETURN_STATE,
            "revertable_artifacts": [
                "Stage059 Phase4 fact extraction delivery module",
                "Stage059 Phase4 delivery contract",
                "Stage059 Phase4 focused tests",
                "Stage059 Phase4 governance projection",
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
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_table_content_evaluated": False,
        "typed_value_extraction_performed": False,
        "merged_cell_resolution_performed": False,
        "unit_normalization_performed": False,
        "date_normalization_performed": False,
        "outlier_evaluation_performed": False,
        "duplicate_row_evaluation_performed": False,
        "numeric_statistic_computation_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "rag_summary_write_performed": False,
        "persistent_state_write_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage059_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
    }


def _load_phase3_report_provider() -> QualityReportProvider:
    module_path = Path(__file__).with_name(
        "stage059_fact_extraction_quality_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location(
        "stage059_p3_quality_scenarios", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage059 P3 fact extraction quality scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_fact_extraction_phase3_report


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
                "quality_disposition": scenario.get("quality_disposition"),
                "referenced_fact_id": scenario.get("referenced_fact_id"),
                "referenced_fact_type": scenario.get("referenced_fact_type"),
                "referenced_record_type": scenario.get("referenced_record_type"),
                "source_document_ref": scenario.get("source_document_ref"),
                "worksheet_ref": scenario.get("worksheet_ref"),
                "header_row_ref": scenario.get("header_row_ref"),
                "row_range_ref": scenario.get("row_range_ref"),
                "column_range_ref": scenario.get("column_range_ref"),
                "evidence_ref": scenario.get("evidence_ref"),
                "control_metadata_only": True,
                "source_content_retained": False,
                "typed_value_retained": False,
                "actual_structured_fact_created": False,
                "actual_table_fact_sample_created": False,
                "high_trust_direct_entry_allowed": False,
            }
        )
    return samples


def _build_field_inference_report(
    predecessor: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    labels = [
        SCENARIO_FIELD_REFERENCE_LABELS[scenario_id]
        for scenario_id in EXPECTED_SCENARIO_IDS
        if scenario_id in scenarios
    ]
    return {
        "report_kind": FIELD_INFERENCE_REPORT_KIND,
        "control_reference_only": True,
        "fact_candidate_pool_count": _nonnegative_int(
            predecessor.get("unique_fact_candidate_count")
        ),
        "scenario_reference_count": len(scenarios),
        "referenced_field_candidate_count": len(labels),
        "referenced_field_labels": labels,
        "actual_field_mapping_created": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "actual_typed_value_created": False,
        "actual_source_file_traceability_validated": False,
    }


def _build_quality_test_results(predecessor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "report_kind": QUALITY_TEST_RESULT_KIND,
        "scenario_count": _nonnegative_int(predecessor.get("scenario_count")),
        "passed_scenario_count": _nonnegative_int(
            predecessor.get("passed_scenario_count")
        ),
        "explicit_disposition_count": _nonnegative_int(
            predecessor.get("explicit_disposition_count")
        ),
        "silent_drop_count": _nonnegative_int(
            predecessor.get("silent_drop_count")
        ),
        "all_taskpack_exception_categories_covered": predecessor.get(
            "taskpack_exception_categories_covered"
        )
        is True,
        "control_source_location_traceability_preserved": predecessor.get(
            "control_source_location_traceability_preserved"
        )
        is True,
        "actual_table_quality_validation_performed": False,
        "actual_source_file_traceability_validated": False,
        "actual_evidence_record_created": False,
        "actual_numeric_statistic_created": False,
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
                "quality_disposition": scenario.get("quality_disposition"),
                "human_handling_required": scenario.get("human_handling_required")
                is True,
                "recommendation_zh": HANDLING_RECOMMENDATIONS_ZH[scenario_id],
                "actual_unrecognized_table_structure_observed": False,
                "actual_table_content_evaluated": False,
                "automatic_structure_resolution_performed": False,
                "automatic_fact_write_performed": False,
            }
        )
    return records


def _reparse_and_fact_rollback_instructions() -> dict[str, Any]:
    return {
        "record_kind": REPARSE_AND_ROLLBACK_KIND,
        "return_to": P3_RETURN_STATE,
        "in_memory_control_replay_only": True,
        "reparse_steps_zh": [
            "仅在新的授权 run 中重放固定 P3 control 报告；不得打开、遍历或解析真实 XLSX/CSV。",
            "若未来获得真实资料授权，必须先由授权输入门和业务线 owner 明确来源、fixture、责任人与回滚点。",
            "本 P4 发现的交付证据不一致时，只撤回 P4 派生工件并恢复到 P3 control 状态。",
        ],
        "fact_rollback_steps_zh": [
            "当前不存在真实事实库、真实 typed value 或持久化事实，因此没有可执行的事实删除、覆写或迁移。",
            "未来事实回滚必须以来源定位、证据记录、业务线确认和可恢复迁移为前提，不能由本 control 自动触发。",
        ],
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "source_or_raw_data_change_allowed": False,
        "fixture_change_allowed": False,
        "database_or_persistent_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _human_confirmation_prompts() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "confirm-fact-delivery-boundary",
            "text": "请业务线确认：本交付只包含事实抽取 control 元数据样例，不可替代真实表格事实、来源证据或数值统计。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-fact-human-handling-boundary",
            "text": "请业务线确认：空表、合并单元格、单位、日期、异常值和重复行均保留人工处理建议，当前没有自动解析或事实写入。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-fact-reparse-rollback-boundary",
            "text": "请业务线确认：重解析和事实回滚说明仅适用于未来授权输入门；当前没有真实文件、事实库或回滚动作。",
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
        and predecessor.get("next_gate") == "IDS-STAGE059-P4-GATE"
        and predecessor.get("phase2_control_slice_reexecuted") is True
        and predecessor.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("explicit_disposition_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("silent_drop_count") == 0
        and predecessor.get("human_handling_required_count")
        == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("unique_fact_candidate_count") == 3
        and predecessor.get("taskpack_exception_categories_covered") is True
        and predecessor.get("control_source_location_traceability_preserved") is True
        and predecessor.get("actual_source_file_traceability_validated") is False
        and predecessor.get("actual_evidence_record_created") is False
        and predecessor.get("actual_structured_fact_created") is False
        and predecessor.get("actual_typed_value_created") is False
        and all(predecessor.get(field) is False for field in P3_SIDE_EFFECT_FIELDS)
    )
    scenario_shape_valid = tuple(scenarios) == EXPECTED_SCENARIO_IDS and all(
        item.get("control_scenario_metadata_only") is True
        and item.get("explicit_disposition") is True
        and item.get("silent_drop") is False
        and item.get("human_handling_required") is True
        and item.get("source_location_reference_preserved") is True
        and item.get("control_reference_only") is True
        and item.get("typed_value_unset") is True
        and item.get("actual_structured_fact_created") is False
        and item.get("actual_typed_value_created") is False
        for item in scenarios.values()
    )
    delivery_shape_valid = len(delivery_samples) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("sample_kind") == OUTPUT_SAMPLE_KIND
        and item.get("control_metadata_only") is True
        and isinstance(item.get("referenced_fact_id"), str)
        and isinstance(item.get("referenced_fact_type"), str)
        and item.get("source_content_retained") is False
        and item.get("typed_value_retained") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("actual_table_fact_sample_created") is False
        and item.get("high_trust_direct_entry_allowed") is False
        for item in delivery_samples
    )
    inference_valid = (
        field_inference_report.get("report_kind") == FIELD_INFERENCE_REPORT_KIND
        and field_inference_report.get("fact_candidate_pool_count") == 3
        and field_inference_report.get("scenario_reference_count") == 6
        and field_inference_report.get("referenced_field_candidate_count") == 6
        and field_inference_report.get("control_reference_only") is True
        and field_inference_report.get("actual_field_mapping_created") is False
        and field_inference_report.get("real_field_identification_performed")
        is False
        and field_inference_report.get("real_structured_fact_extraction_performed")
        is False
    )
    quality_valid = (
        quality_test_results.get("report_kind") == QUALITY_TEST_RESULT_KIND
        and quality_test_results.get("scenario_count") == 6
        and quality_test_results.get("passed_scenario_count") == 6
        and quality_test_results.get("explicit_disposition_count") == 6
        and quality_test_results.get("silent_drop_count") == 0
        and quality_test_results.get("all_taskpack_exception_categories_covered")
        is True
        and quality_test_results.get("control_source_location_traceability_preserved")
        is True
        and quality_test_results.get("actual_table_quality_validation_performed")
        is False
    )
    handling_valid = len(handling_records) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("record_kind") == HANDLING_RECORD_KIND
        and item.get("human_handling_required") is True
        and isinstance(item.get("recommendation_zh"), str)
        and bool(item.get("recommendation_zh"))
        and item.get("actual_unrecognized_table_structure_observed") is False
        and item.get("automatic_structure_resolution_performed") is False
        and item.get("automatic_fact_write_performed") is False
        for item in handling_records
    )
    rollback_valid = (
        reparse_and_fact_rollback.get("record_kind") == REPARSE_AND_ROLLBACK_KIND
        and reparse_and_fact_rollback.get("return_to") == P3_RETURN_STATE
        and reparse_and_fact_rollback.get("in_memory_control_replay_only") is True
        and reparse_and_fact_rollback.get("actual_file_reparse_performed") is False
        and reparse_and_fact_rollback.get("actual_fact_store_present") is False
        and reparse_and_fact_rollback.get("actual_fact_rollback_performed") is False
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


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
