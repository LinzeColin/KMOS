"""Stage062 P4 的表格证据绑定 metadata-only 交付证据。

本模块只重放 Stage062 P3 的六类固定、非业务、reference-only 受控异常场景，
派生交付样例、字段推断引用报告、质量结果、人工建议与重解析/事实回滚说明。
它不读取、打开、解析、规范化、评估、统计、保存或写入任何真实表格、业务记录、
结构化事实、来源位置、证据或数据库内容。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage062.table_evidence_binding.phase4.delivery.v1"
RECORD_KIND = "CONTROLLED_TABLE_EVIDENCE_BINDING_DELIVERY_REPORT"
OUTPUT_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_TABLE_EVIDENCE_BINDING_SAMPLE_NOT_REAL_EVIDENCE_BINDING"
)
FIELD_INFERENCE_REPORT_KIND = (
    "CONTROLLED_TABLE_EVIDENCE_BINDING_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE"
)
QUALITY_TEST_RESULT_KIND = (
    "CONTROLLED_TABLE_EVIDENCE_BINDING_TEST_RESULT_NOT_REAL_TABLE_VALIDATION"
)
HANDLING_RECORD_KIND = (
    "CONTROLLED_TABLE_EVIDENCE_BINDING_HUMAN_HANDLING_NOT_REAL_TABLE_OBSERVATION"
)
REPARSE_AND_ROLLBACK_KIND = (
    "TABLE_EVIDENCE_BINDING_REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)
PASS_RESULT = "PASS_PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_TABLE_EVIDENCE_BINDING_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE062-REVIEW-GATE"
P3_PASS_RESULT = "PASS_PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
P3_RETURN_STATE = "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

EXPECTED_SCENARIO_IDS = (
    "empty-table-binding-control-human-handling",
    "merged-cells-binding-control-human-handling",
    "unit-confusion-binding-control-human-handling",
    "date-variation-binding-control-human-handling",
    "outlier-binding-control-numeric-block",
    "duplicate-row-binding-control-human-handling",
)
CONTROL_REFERENCE_FIELDS = (
    "referenced_table_evidence_binding_ref",
    "referenced_binding_request_ref",
    "referenced_fact_ref",
    "evidence_id",
    "document_id",
    "sheet",
    "row",
    "column",
    "source_uri",
)
SCENARIO_FIELD_REFERENCE_LABELS = {
    "empty-table-binding-control-human-handling": "empty_table_binding_reference",
    "merged-cells-binding-control-human-handling": "merged_cell_binding_reference",
    "unit-confusion-binding-control-human-handling": "unit_binding_reference",
    "date-variation-binding-control-human-handling": "date_binding_reference",
    "outlier-binding-control-numeric-block": "numeric_authority_binding_reference",
    "duplicate-row-binding-control-human-handling": "duplicate_row_binding_reference",
}
HANDLING_RECOMMENDATIONS_ZH = {
    "empty-table-binding-control-human-handling": (
        "请业务线在未来授权输入门内人工确认空表是否具备可定位的表头、行列与业务范围；"
        "当前 control 不代表真实表格，不得形成事实、证据或统计结论。"
    ),
    "merged-cells-binding-control-human-handling": (
        "请业务线在未来授权输入门内人工确认合并单元格的结构和定位规则；当前不展开、拆分、"
        "规范化或绑定任何单元格，也不创建事实或证据记录。"
    ),
    "unit-confusion-binding-control-human-handling": (
        "请业务线在未来授权输入门内人工确认单位语义和换算依据；当前不进行单位归一化，"
        "不得形成数值事实、来源绑定或统计结论。"
    ),
    "date-variation-binding-control-human-handling": (
        "请业务线在未来授权输入门内人工确认日期格式和时区语义；当前不进行日期规范化，"
        "不得写入结构化事实、证据记录或业务结论。"
    ),
    "outlier-binding-control-numeric-block": (
        "请业务线在未来授权输入门内人工评估异常数值候选及其来源证据；当前阻断数值统计、"
        "异常判定和任何模型确定性数值结论。"
    ),
    "duplicate-row-binding-control-human-handling": (
        "请业务线在未来授权输入门内人工确认重复行候选及其来源定位；当前不删除、合并、"
        "去重、绑定或持久化任何记录。"
    ),
}
P3_SIDE_EFFECT_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "file_type_detection_performed",
    "xlsx_or_csv_parse_performed",
    "table_schema_inference_performed",
    "field_identification_performed",
    "structured_fact_extraction_performed",
    "typed_value_extraction_performed",
    "table_summary_generation_performed",
    "numeric_statistic_computation_performed",
    "quality_gate_evaluation_performed",
    "source_location_binding_performed",
    "evidence_binding_performed",
    "actual_structured_fact_created",
    "actual_table_evidence_binding_created",
    "actual_table_evidence_binding_persisted",
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

ScenarioReportProvider = Callable[[], Mapping[str, Any]]


def build_table_evidence_binding_phase4_delivery_report(
    scenario_report_provider: ScenarioReportProvider | None = None,
) -> dict[str, Any]:
    """从 P3 控制报告派生 P4 交付证据；返回值只包含固定控制元数据。"""

    provider = scenario_report_provider or _load_phase3_report_provider()
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
            "本交付只来自六类固定非业务 control，不能代表真实 XLSX/CSV、生产记录、质检记录、工作表、表头、单元格、数值、日期或业务资料。",
            "字段推断报告只保留 P3 control 的引用标签，不构成真实字段识别、字段映射、表格证据绑定、结构化事实、来源追溯或数值统计。",
            "人工处理建议、重解析和事实回滚说明均为未来授权输入门的白箱操作说明；当前没有真实文件、事实库、证据库、人工任务或回滚动作。",
        ],
        "human_confirmation_prompts_zh": prompts,
        "reparse_and_fact_rollback_instructions": reparse_and_fact_rollback,
        "rollback": {
            "return_to": P3_RETURN_STATE,
            "revertable_artifacts": [
                "Stage062 Phase4 table-evidence binding delivery module",
                "Stage062 Phase4 delivery contract",
                "Stage062 Phase4 focused tests",
                "Stage062 Phase4 governance projection",
            ],
            "preserve_predecessor_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "actual_input_record_count": 0,
        "actual_structured_fact_count": 0,
        "actual_numeric_fact_count": 0,
        "actual_table_evidence_binding_count": 0,
        "actual_source_location_binding_count": 0,
        "actual_evidence_record_count": 0,
        "source_document_remains_authoritative": True,
        "model_direct_text_guessing_allowed": False,
        "unverified_numeric_value_as_definitive_fact_allowed": False,
        "numeric_statistical_conclusion_allowed": False,
        "model_definitive_numeric_conclusion_allowed": False,
        "summary_can_replace_structured_fact": False,
        "summary_can_become_numeric_statistical_evidence": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "table_schema_inference_performed": False,
        "field_identification_performed": False,
        "structured_fact_extraction_performed": False,
        "typed_value_extraction_performed": False,
        "table_summary_generation_performed": False,
        "numeric_statistic_computation_performed": False,
        "quality_gate_evaluation_performed": False,
        "source_location_binding_performed": False,
        "evidence_binding_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "quality_result_write_performed": False,
        "persistent_state_write_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "actual_table_evidence_binding_rollback_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage062_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
    }


def _load_phase3_report_provider() -> ScenarioReportProvider:
    module_path = Path(__file__).with_name("stage062_table_evidence_binding_scenarios.py")
    spec = importlib.util.spec_from_file_location(
        "stage062_p3_table_evidence_binding_scenarios", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage062 P3 table-evidence binding scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_table_evidence_binding_phase3_report


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
        sample = {
            "sample_id": f"delivery-{scenario_id}",
            "sample_kind": OUTPUT_SAMPLE_KIND,
            "scenario_id": scenario_id,
            "scenario_category": scenario.get("scenario_category"),
            "explicit_disposition": scenario.get("explicit_disposition"),
            "fact_type": scenario.get("fact_type"),
            "field_inference_label": SCENARIO_FIELD_REFERENCE_LABELS[scenario_id],
            "control_metadata_only": True,
            "source_content_retained": False,
            "typed_value_retained": False,
            "actual_field_mapping_created": False,
            "actual_structured_fact_created": False,
            "actual_table_evidence_binding_created": False,
            "actual_evidence_record_created": False,
            "actual_source_file_traceability_validated": False,
            "high_trust_direct_entry_allowed": False,
        }
        sample.update({field: scenario.get(field) for field in CONTROL_REFERENCE_FIELDS})
        samples.append(sample)
    return samples


def _build_field_inference_report(
    predecessor: Mapping[str, Any], scenarios: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    labels = [
        {
            "scenario_id": scenario_id,
            "field_label": SCENARIO_FIELD_REFERENCE_LABELS[scenario_id],
            "scenario_category": scenarios[scenario_id].get("scenario_category"),
            "fact_type": scenarios[scenario_id].get("fact_type"),
            "binding_request_ref": scenarios[scenario_id].get(
                "referenced_binding_request_ref"
            ),
            "control_reference_only": True,
            "actual_field_mapping_created": False,
        }
        for scenario_id in EXPECTED_SCENARIO_IDS
        if scenario_id in scenarios
    ]
    return {
        "report_kind": FIELD_INFERENCE_REPORT_KIND,
        "table_evidence_binding_candidate_pool_count": predecessor.get(
            "unique_table_evidence_binding_candidate_count"
        ),
        "referenced_field_label_count": len(labels),
        "scenario_reference_count": len(labels),
        "field_reference_labels": labels,
        "control_reference_only": True,
        "actual_field_mapping_created": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_table_evidence_binding_performed": False,
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
        "outlier_numeric_block_count": predecessor.get("outlier_numeric_block_count"),
        "actual_table_evidence_binding_validation_performed": False,
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
        disposition = scenario.get("explicit_disposition")
        if scenario_id == "merged-cells-binding-control-human-handling":
            disposition = "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING"
        records.append(
            {
                "record_kind": HANDLING_RECORD_KIND,
                "scenario_id": scenario_id,
                "scenario_category": scenario.get("scenario_category"),
                "handling_disposition": disposition,
                "human_handling_required": True,
                "recommendation_zh": HANDLING_RECOMMENDATIONS_ZH[scenario_id],
                "control_reference_only": True,
                "actual_unrecognized_table_structure_observed": False,
                "automatic_structure_resolution_performed": False,
                "automatic_table_evidence_binding_performed": False,
                "automatic_structured_fact_write_performed": False,
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
            "字段规则、行列定位、证据绑定、事实存储、回滚点和恢复责任。"
        ),
        "current_action_zh": (
            "当前只允许重放 P3 固定 control 报告；若 P4 派生证据不一致，只撤回 P4 工件，"
            "保留 P1/P2/P3 证据。"
        ),
        "actual_file_reparse_performed": False,
        "actual_fact_store_present": False,
        "actual_fact_rollback_performed": False,
        "actual_table_evidence_binding_rollback_performed": False,
        "source_or_raw_data_change_allowed": False,
        "database_or_persistent_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _human_confirmation_prompts() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "confirm-table-evidence-binding-control-delivery-boundary",
            "text": "请业务线确认：本交付只包含表格证据绑定的 control 元数据样例，不可替代真实表格事实、来源位置、证据记录或数值结论。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-table-evidence-binding-exception-handling-boundary",
            "text": "请业务线确认：六类异常均保留人工处理建议，当前没有自动解析、自动字段映射、自动绑定、自动写入或确定性模型结论。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "confirm-table-evidence-binding-reparse-rollback-boundary",
            "text": "请业务线确认：表格重解析和事实回滚说明只适用于未来授权输入门；当前没有真实文件、事实库、证据库或回滚动作。",
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
        and predecessor.get("next_gate") == "IDS-STAGE062-P4-GATE"
        and predecessor.get("phase2_control_slice_reexecuted") is True
        and predecessor.get("phase2_shape_preserved") is True
        and predecessor.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("explicit_disposition_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("silent_drop_count") == 0
        and predecessor.get("human_handling_required_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("unique_table_evidence_binding_candidate_count") == 2
        and predecessor.get("all_taskpack_exception_categories_covered") is True
        and predecessor.get("control_source_location_traceability_preserved") is True
        and predecessor.get("actual_source_file_traceability_validated") is False
        and predecessor.get("actual_source_location_binding_created") is False
        and predecessor.get("actual_evidence_record_created") is False
        and predecessor.get("actual_structured_fact_created") is False
        and predecessor.get("actual_table_evidence_binding_created") is False
        and all(predecessor.get(field) is False for field in P3_SIDE_EFFECT_FIELDS)
    )
    scenario_shape_valid = tuple(scenarios) == EXPECTED_SCENARIO_IDS and all(
        item.get("control_scenario_metadata_only") is True
        and item.get("expectation_met") is True
        and item.get("explicit_disposition")
        and item.get("human_handling_required") is True
        and item.get("control_source_location_reference_preserved") is True
        and item.get("control_reference_only") is True
        and item.get("silent_drop") is False
        and item.get("actual_source_file_traceability_validated") is False
        and item.get("actual_source_location_binding_created") is False
        and item.get("actual_evidence_record_created") is False
        for item in scenarios.values()
    )
    delivery_shape_valid = len(delivery_samples) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("sample_kind") == OUTPUT_SAMPLE_KIND
        and item.get("control_metadata_only") is True
        and _control_references_preserved(item)
        and item.get("source_content_retained") is False
        and item.get("typed_value_retained") is False
        and item.get("actual_field_mapping_created") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("actual_table_evidence_binding_created") is False
        and item.get("high_trust_direct_entry_allowed") is False
        for item in delivery_samples
    )
    inference_valid = (
        field_inference_report.get("report_kind") == FIELD_INFERENCE_REPORT_KIND
        and field_inference_report.get("table_evidence_binding_candidate_pool_count") == 2
        and field_inference_report.get("scenario_reference_count") == 6
        and field_inference_report.get("referenced_field_label_count") == 6
        and len(field_inference_report.get("field_reference_labels", [])) == 6
        and field_inference_report.get("control_reference_only") is True
        and field_inference_report.get("actual_field_mapping_created") is False
        and field_inference_report.get("real_table_schema_inference_performed") is False
        and field_inference_report.get("real_field_identification_performed") is False
        and field_inference_report.get("real_structured_fact_extraction_performed") is False
        and field_inference_report.get("real_table_evidence_binding_performed") is False
    )
    quality_valid = (
        quality_test_results.get("report_kind") == QUALITY_TEST_RESULT_KIND
        and quality_test_results.get("scenario_count") == 6
        and quality_test_results.get("passed_scenario_count") == 6
        and quality_test_results.get("explicit_disposition_count") == 6
        and quality_test_results.get("silent_drop_count") == 0
        and quality_test_results.get("human_handling_required_count") == 6
        and quality_test_results.get("all_taskpack_exception_categories_covered") is True
        and quality_test_results.get("control_source_location_traceability_preserved") is True
        and quality_test_results.get("outlier_numeric_block_count") == 1
        and quality_test_results.get("actual_table_evidence_binding_validation_performed")
        is False
        and quality_test_results.get("actual_source_file_traceability_validated") is False
        and quality_test_results.get("actual_evidence_record_created") is False
    )
    handling_valid = len(handling_records) == len(EXPECTED_SCENARIO_IDS) and all(
        item.get("record_kind") == HANDLING_RECORD_KIND
        and item.get("human_handling_required") is True
        and isinstance(item.get("recommendation_zh"), str)
        and bool(item.get("recommendation_zh"))
        and item.get("actual_unrecognized_table_structure_observed") is False
        and item.get("automatic_structure_resolution_performed") is False
        and item.get("automatic_table_evidence_binding_performed") is False
        and item.get("automatic_structured_fact_write_performed") is False
        for item in handling_records
    )
    merged_handling_valid = any(
        item.get("scenario_id") == "merged-cells-binding-control-human-handling"
        and item.get("handling_disposition")
        == "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING"
        for item in handling_records
    )
    rollback_valid = (
        reparse_and_fact_rollback.get("record_kind") == REPARSE_AND_ROLLBACK_KIND
        and reparse_and_fact_rollback.get("return_to") == P3_RETURN_STATE
        and reparse_and_fact_rollback.get("in_memory_control_replay_only") is True
        and reparse_and_fact_rollback.get("actual_file_reparse_performed") is False
        and reparse_and_fact_rollback.get("actual_fact_store_present") is False
        and reparse_and_fact_rollback.get("actual_fact_rollback_performed") is False
        and reparse_and_fact_rollback.get(
            "actual_table_evidence_binding_rollback_performed"
        )
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
            merged_handling_valid,
            rollback_valid,
            prompts_valid,
        )
    )


def _control_references_preserved(sample: Mapping[str, Any]) -> bool:
    return all(
        isinstance(sample.get(field), str) and ":control:" in sample[field]
        for field in CONTROL_REFERENCE_FIELDS
    )
