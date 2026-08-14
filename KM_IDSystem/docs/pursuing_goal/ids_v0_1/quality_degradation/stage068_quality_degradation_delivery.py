"""Stage068 P4 的质量降级 metadata-only 交付证据。

本模块只由 P3 固定控制场景派生内存 JSONL 样例、控制交付覆盖报告、低质量待人工
清单、回归控制结果和回退说明。它不读取来源、不生成真实 chunk、不验证真实质量或
质量降级，也不写入文件、索引、数据库或运行时服务。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage068.quality_degradation.phase4.delivery.v1"
RECORD_KIND = "QUALITY_DEGRADATION_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = "PASS_PHASE4_QUALITY_DEGRADATION_DELIVERY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_QUALITY_DEGRADATION_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE068-REVIEW-GATE"
ENTRY_GATE = "IDS-STAGE068-P4-GATE"
P3_PASS_RESULT = "PASS_PHASE3_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"

CHUNK_JSONL_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_QUALITY_DEGRADATION_JSONL_SAMPLE_NOT_REAL_CHUNK"
)
COVERAGE_REPORT_KIND = (
    "CONTROLLED_QUALITY_DEGRADATION_DELIVERY_COVERAGE_REPORT_NOT_REAL_COVERAGE"
)
LOW_QUALITY_LIST_KIND = (
    "CONTROLLED_LOW_QUALITY_QUALITY_DEGRADATION_LIST_NOT_REAL_QUALITY_MEASUREMENT"
)
REGRESSION_RESULT_KIND = (
    "CONTROLLED_QUALITY_DEGRADATION_REGRESSION_RESULT_NOT_REAL_QUALITY_REGRESSION"
)
REGENERATION_ROLLBACK_KIND = (
    "QUALITY_DEGRADATION_REGENERATION_AND_VERSION_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)

EXPECTED_SCENARIO_IDS = (
    "long-document-quality-degradation-control-human-review",
    "cross-page-table-quality-degradation-control-human-handling",
    "engineering-procedure-quality-degradation-control-human-review",
    "parameter-table-quality-degradation-control-human-review",
    "citation-page-quality-degradation-control-human-confirmation",
    "duplicate-chunk-quality-degradation-control-human-review",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)
DELIVERY_REFERENCE_FIELDS = (
    "referenced_quality_degradation_record_ref",
    "referenced_quality_degradation_request_ref",
    "referenced_chunk_quality_regression_record_ref",
    "referenced_chapter_aware_chunk_ref",
    "referenced_chunk_identity_version_record_ref",
    "referenced_engineering_semantic_asset_catalog_ref",
    "referenced_chunk_coverage_metrics_record_ref",
)
P3_RUNTIME_FALSE_FIELDS = (
    "actual_source_document_read_performed",
    "actual_long_document_quality_validated",
    "actual_cross_page_table_relation_validated",
    "actual_protected_semantic_boundary_validated",
    "actual_page_traceability_validated",
    "actual_source_traceability_binding_created",
    "actual_quality_degradation_validated",
    "actual_low_confidence_evidence_created",
    "actual_duplicate_chunk_detected",
    "actual_duplicate_chunk_identity_or_hash_validated",
    "actual_duplicate_embedding_prevented",
    "actual_duplicate_index_prevented",
    "duplicate_embedding_or_index_write_attempted",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chapter_detection_performed",
    "chunking_execution_performed",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "low_confidence_evidence_creation_performed",
    "source_traceability_binding_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "phase4_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "stage069_started",
    "stage069_entry_allowed",
    "github_upload_allowed",
    "push_allowed",
)
RUNTIME_FALSE_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "parser_execution_performed",
    "chapter_detection_performed",
    "chunking_execution_performed",
    "chunk_identity_generation_performed",
    "chunk_hash_computation_performed",
    "chunk_version_generation_performed",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
    "low_confidence_evidence_creation_performed",
    "source_traceability_binding_performed",
    "embedding_or_index_write_performed",
    "database_connection_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

Phase3ReportProvider = Callable[[], Mapping[str, Any]]


def build_quality_degradation_phase4_delivery_report(
    phase3_report_provider: Phase3ReportProvider | None = None,
) -> dict[str, Any]:
    """输出 P4 纯内存交付证据，并在 P3 前序不完整时失败关闭。"""

    provider = phase3_report_provider or _load_phase3_report_provider()
    try:
        candidate = provider()
    except (RuntimeError, TypeError, ValueError):
        candidate = {}
    phase3_report = candidate if isinstance(candidate, Mapping) else {}
    predecessor_valid = _phase3_report_is_valid(phase3_report)
    scenarios = _scenario_results(phase3_report) if predecessor_valid else []
    samples = [_jsonl_sample(item) for item in scenarios]
    sample_lines = tuple(_json_line(item) for item in samples)
    coverage_report = _coverage_report(phase3_report, samples, predecessor_valid)
    low_quality_list = _low_quality_list(scenarios)
    regression_results = _regression_results(
        phase3_report, samples, low_quality_list, predecessor_valid
    )
    valid = (
        predecessor_valid
        and len(samples) == len(EXPECTED_SCENARIO_IDS)
        and _expected_sample_ids(samples)
        and coverage_report["control_delivery_coverage_complete"]
        and len(low_quality_list) == len(EXPECTED_SCENARIO_IDS)
        and regression_results["control_regression_consistent"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "entry_gate": ENTRY_GATE,
        "phase3_controlled_scenarios_reused_as_reference_only": predecessor_valid,
        "phase3_controlled_scenarios_report_valid": predecessor_valid,
        "chunk_jsonl_samples": samples,
        "chunk_jsonl_sample_lines": sample_lines,
        "actual_jsonl_file_written": False,
        "coverage_report": coverage_report,
        "low_quality_chunk_list": low_quality_list,
        "regression_test_results": regression_results,
        "chunking_strategy_applicability_boundary": _strategy_boundary(),
        "regeneration_and_version_rollback_instructions": _rollback_instructions(),
        "human_confirmation_prompts_zh": _human_confirmation_prompts(),
        "source_document_remains_authoritative": True,
        "business_line_white_box_human_review_remains_authoritative": True,
        "delivery_control_metadata_can_replace_source_document": False,
        "delivery_control_metadata_can_become_business_fact_authority": False,
        "real_source_content_retained": False,
        "actual_input_document_count": 0,
        "actual_chunk_count": 0,
        "actual_quality_degradation_record_count": 0,
        "actual_low_confidence_evidence_count": 0,
        "actual_traceability_binding_count": 0,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "actual_quality_degradation_delivery_implementation_performed": False,
        "actual_delivery_file_written": False,
        **_runtime_closed_flags(),
        "stage068_started": True,
        "phase1_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "stage069_started": False,
        "stage069_entry_allowed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "github_upload_performed": False,
        "push_performed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if valid else ENTRY_GATE,
        "chinese_feedback": [
            "已生成六条仅含控制引用的交付样例；它们不是实际 chunk、质量结果或来源正文。",
            "交付覆盖报告只核对固定控制场景和引用形状；真实页面、质量、质量降级与来源结论仍须业务线白箱人工确认。",
            "低质量清单全部是控制边界待人工复核，不能解读为观察到真实质量问题或实际低可信证据。",
            "如需撤回本 phase，只回到 P3 的纯内存控制场景，不改动来源、版本、索引、数据库或部署。",
        ],
    }


def _load_phase3_report_provider() -> Phase3ReportProvider:
    module_path = Path(__file__).with_name("stage068_quality_degradation_scenarios.py")
    spec = importlib.util.spec_from_file_location("stage068_p3", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage068 P3 controlled-scenarios module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = getattr(module, "build_quality_degradation_phase3_report", None)
    if not callable(provider):
        raise RuntimeError("Stage068 P3 report provider is unavailable")
    return provider


def _phase3_report_is_valid(report: Mapping[str, Any]) -> bool:
    scenarios = _scenario_results(report)
    return (
        report.get("valid") is True
        and report.get("result") == P3_PASS_RESULT
        and report.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("explicit_disposition_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("silent_drop_count") == 0
        and report.get("human_handling_required_count") == len(EXPECTED_SCENARIO_IDS)
        and report.get("unique_control_quality_degradation_record_count") == 4
        and report.get("control_traceability_field_count") == len(TRACEABILITY_FIELDS)
        and report.get("control_traceability_reference_check_count") == 36
        and report.get("control_traceability_reference_shape_preserved") is True
        and report.get("low_quality_is_not_automatic_complete_failure") is True
        and report.get("control_duplicate_write_prohibition_asserted") is True
        and report.get("source_document_remains_authoritative") is True
        and report.get("quality_degradation_control_record_can_replace_source_document")
        is False
        and report.get(
            "quality_degradation_control_record_can_become_business_fact_authority"
        )
        is False
        and tuple(item.get("scenario_id") for item in scenarios) == EXPECTED_SCENARIO_IDS
        and all(_scenario_is_control_only(item) for item in scenarios)
        and all(report.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS)
    )


def _scenario_results(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = report.get("scenario_results")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _scenario_is_control_only(item: Mapping[str, Any]) -> bool:
    return (
        isinstance(item.get("scenario_category"), str)
        and item.get("expectation_met") is True
        and item.get("human_handling_required") is True
        and item.get("control_reference_only") is True
        and item.get("control_scenario_metadata_only") is True
        and item.get("control_traceability_reference_preserved") is True
        and item.get("control_traceability_reference_count") == len(TRACEABILITY_FIELDS)
        and item.get("low_quality_is_not_automatic_complete_failure") is True
        and item.get("silent_drop") is False
        and all(
            isinstance(item.get(field), str) and ":control:" in item[field]
            for field in TRACEABILITY_FIELDS + DELIVERY_REFERENCE_FIELDS
        )
    )


def _jsonl_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": f"quality-degradation-jsonl-sample:{item['scenario_id']}",
        "sample_kind": CHUNK_JSONL_SAMPLE_KIND,
        "scenario_id": item["scenario_id"],
        "scenario_category": item["scenario_category"],
        "quality_degradation_record_ref": item[
            "referenced_quality_degradation_record_ref"
        ],
        "quality_degradation_request_ref": item[
            "referenced_quality_degradation_request_ref"
        ],
        "chunk_quality_regression_record_ref": item[
            "referenced_chunk_quality_regression_record_ref"
        ],
        "chapter_aware_chunk_ref": item["referenced_chapter_aware_chunk_ref"],
        "chunk_identity_version_record_ref": item[
            "referenced_chunk_identity_version_record_ref"
        ],
        "engineering_semantic_asset_catalog_ref": item[
            "referenced_engineering_semantic_asset_catalog_ref"
        ],
        "chunk_coverage_metrics_record_ref": item[
            "referenced_chunk_coverage_metrics_record_ref"
        ],
        "protected_semantic_surface": item["protected_semantic_surface"],
        "explicit_disposition": item["explicit_disposition"],
        "quality_degradation_status": item["quality_degradation_status"],
        "low_confidence_evidence_state": item["low_confidence_evidence_state"],
        "human_review_state": item["human_review_state"],
        "low_quality_is_not_automatic_complete_failure": True,
        "control_traceability_reference_count": len(TRACEABILITY_FIELDS),
        "control_traceability_reference_preserved": True,
        "human_review_required": True,
        "control_metadata_only": True,
        "source_content_retained": False,
        "actual_chunk_created": False,
        "actual_chunk_identifier_generated": False,
        "actual_chunk_hash_computed": False,
        "actual_chunk_version_generated": False,
        "actual_quality_degradation_record_created": False,
        "actual_low_confidence_evidence_created": False,
        "actual_quality_measurement_performed": False,
        "actual_quality_degradation_performed": False,
        "actual_embedding_written": False,
        "actual_index_written": False,
    }


def _json_line(sample: Mapping[str, Any]) -> str:
    return json.dumps(sample, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _coverage_report(
    phase3_report: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    predecessor_valid: bool,
) -> dict[str, Any]:
    complete = (
        predecessor_valid
        and len(samples) == len(EXPECTED_SCENARIO_IDS)
        and _expected_sample_ids(samples)
    )
    return {
        "report_kind": COVERAGE_REPORT_KIND,
        "control_scenario_count": len(EXPECTED_SCENARIO_IDS) if complete else 0,
        "chunk_jsonl_sample_count": len(samples),
        "unique_control_quality_degradation_record_count": (
            phase3_report.get("unique_control_quality_degradation_record_count")
            if complete
            else 0
        ),
        "covered_scenario_ids": [sample["scenario_id"] for sample in samples],
        "control_traceability_field_count": len(TRACEABILITY_FIELDS) if complete else 0,
        "control_traceability_reference_check_count": 36 if complete else 0,
        "control_delivery_coverage_complete": complete,
        "control_delivery_coverage_only": True,
        "actual_document_quality_validated": False,
        "actual_quality_degradation_performed": False,
        "actual_low_confidence_evidence_created": False,
        "actual_source_traceability_validated": False,
        "coverage_can_support_real_quality_claim": False,
    }


def _low_quality_list(scenarios: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_id": (
                f"quality-degradation-low-quality-control:{item['scenario_id']}"
            ),
            "record_kind": LOW_QUALITY_LIST_KIND,
            "scenario_id": item["scenario_id"],
            "scenario_category": item["scenario_category"],
            "quality_degradation_record_ref": item[
                "referenced_quality_degradation_record_ref"
            ],
            "protected_semantic_surface": item["protected_semantic_surface"],
            "quality_disposition": "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW",
            "recommendation_zh": (
                "请业务线白箱人工复核切块边界、页面追溯、质量与质量降级依据；"
                "当前控制记录不能自动降级、创建低可信证据或写入。"
            ),
            "control_metadata_only": True,
            "actual_low_quality_chunk_observed": False,
            "actual_quality_measurement_performed": False,
            "actual_quality_degradation_performed": False,
            "actual_low_confidence_evidence_created": False,
            "automatic_quality_degradation_action_performed": False,
        }
        for item in scenarios
    ]


def _regression_results(
    phase3_report: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    low_quality_list: Sequence[Mapping[str, Any]],
    predecessor_valid: bool,
) -> dict[str, Any]:
    consistent = (
        predecessor_valid
        and len(samples) == len(EXPECTED_SCENARIO_IDS)
        and len(low_quality_list) == len(EXPECTED_SCENARIO_IDS)
        and phase3_report.get("silent_drop_count") == 0
        and _expected_sample_ids(samples)
    )
    return {
        "result_kind": REGRESSION_RESULT_KIND,
        "control_scenario_count": len(EXPECTED_SCENARIO_IDS) if consistent else 0,
        "chunk_jsonl_sample_count": len(samples),
        "low_quality_control_item_count": len(low_quality_list),
        "silent_drop_count": 0 if consistent else None,
        "control_regression_consistent": consistent,
        "actual_quality_regression_performed": False,
        "actual_quality_baseline_compared": False,
        "actual_quality_degradation_performed": False,
        "actual_duplicate_chunk_checked": False,
        "actual_embedding_or_index_write_performed": False,
    }


def _expected_sample_ids(samples: Sequence[Mapping[str, Any]]) -> bool:
    return tuple(sample.get("scenario_id") for sample in samples) == EXPECTED_SCENARIO_IDS


def _strategy_boundary() -> dict[str, Any]:
    return {
        "strategy_boundary_is_control_metadata_only": True,
        "long_document_requires_human_boundary_review": True,
        "cross_page_table_requires_human_handling": True,
        "engineering_procedure_requires_human_boundary_review": True,
        "parameter_table_requires_human_boundary_review": True,
        "citation_page_requires_human_source_confirmation": True,
        "duplicate_chunk_requires_later_identity_and_human_review": True,
        "unverified_boundary_cannot_trigger_automatic_chunk_write": True,
        "unverified_boundary_cannot_trigger_automatic_quality_degradation": True,
        "actual_strategy_applicability_validated": False,
        "actual_production_quality_claim_allowed": False,
    }


def _rollback_instructions() -> dict[str, Any]:
    return {
        "instruction_kind": REGENERATION_ROLLBACK_KIND,
        "rollback_target_result": P3_PASS_RESULT,
        "regeneration_instruction": "仅可重新运行 P4 的纯内存控制投影。",
        "rollback_instruction": "仅撤回 P4 工件并返回 P3 控制场景；保留 P1、P2、P3。",
        "in_memory_control_replay_only": True,
        "phase1_phase2_phase3_artifacts_preserved": True,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "actual_quality_degradation_delivery_implementation_performed": False,
        "actual_low_confidence_evidence_created": False,
        "source_or_raw_data_change_allowed": False,
        "fixture_change_allowed": False,
        "database_schema_change_allowed": False,
        "persistent_runtime_state_change_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _human_confirmation_prompts() -> list[str]:
    return [
        "请确认：六条 JSONL 样例仅为控制元数据，不代表真实 chunk、质量或来源内容。",
        "请确认：交付覆盖报告与低质量清单仅覆盖固定控制场景，真实质量、降级与页面需业务线白箱人工确认。",
        "请确认：如需回退，只回到 P3 的纯内存控制场景，不触及来源、版本、索引、数据库、OVH 或生产。",
    ]


def _runtime_closed_flags() -> dict[str, bool]:
    return {field: False for field in RUNTIME_FALSE_FIELDS}
