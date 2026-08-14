"""Stage065 P4 的工程语义资产分类 metadata-only 交付证据。

本模块只从 P3 六类固定、非业务、reference-only 控制场景派生内存中的
JSONL 样例、控制覆盖率报告、低质量待人工清单、回归结论和回退说明。它不读取
真实文档、创建真实 chunk 或工程语义资产分类，也不执行索引、数据库及任何运行时动作。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage065.engineering_semantic_asset_classification.phase4.delivery.v1"
RECORD_KIND = "ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_EVIDENCE_REPORT"
PASS_RESULT = (
    "PASS_PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_RUNTIME_DISABLED"
)
FAIL_RESULT = "FAIL_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_EVIDENCE"
NEXT_GATE = "IDS-STAGE065-REVIEW-GATE"

CHUNK_JSONL_SAMPLE_KIND = (
    "DELIVERY_METADATA_ONLY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_JSONL_SAMPLE_NOT_REAL_CHUNK"
)
COVERAGE_REPORT_KIND = (
    "CONTROLLED_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_COVERAGE_REPORT_NOT_REAL_COVERAGE"
)
LOW_QUALITY_LIST_KIND = (
    "CONTROLLED_LOW_QUALITY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_LIST_NOT_REAL_QUALITY_MEASUREMENT"
)
REGRESSION_RESULT_KIND = (
    "CONTROLLED_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_REGRESSION_RESULT_NOT_REAL_QUALITY_REGRESSION"
)
REGENERATION_ROLLBACK_KIND = (
    "ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_REGENERATION_AND_VERSION_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY"
)

EXPECTED_SCENARIO_IDS = (
    "long-document-semantic-asset-control-human-review",
    "cross-page-parameter-table-semantic-asset-control-human-handling",
    "engineering-procedure-semantic-asset-control-human-review",
    "parameter-table-semantic-asset-control-human-review",
    "citation-page-semantic-asset-control-human-confirmation",
    "duplicate-semantic-asset-embedding-index-control-human-review",
)
P3_RUNTIME_FALSE_FIELDS = (
    "actual_source_document_read_performed",
    "actual_page_traceability_validated",
    "actual_source_traceability_binding_created",
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
    "chunk_identity_generation_performed",
    "chunk_hash_computation_performed",
    "chunk_version_generation_performed",
    "actual_chunk_created",
    "actual_chunk_persisted",
    "actual_chunk_id_generated",
    "actual_chunk_hash_computed",
    "actual_chunk_version_generated",
    "actual_semantic_asset_classification_created",
    "semantic_asset_classification_performed",
    "coverage_calculation_performed",
    "quality_regression_performed",
    "quality_degradation_performed",
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
    "github_upload_performed",
    "push_performed",
)
TRACEABILITY_FIELDS = (
    "document_ref",
    "page_ref",
    "section_ref",
    "parser_output_ref",
    "table_context_ref",
    "source_fragment_ref",
)

ScenarioReportProvider = Callable[[], Mapping[str, Any]]


def build_engineering_semantic_asset_classification_phase4_delivery_report(
    phase3_report_provider: ScenarioReportProvider | None = None,
) -> dict[str, Any]:
    """派生 P4 交付证据；所有内容均为控制元数据而非业务资料。"""

    provider = phase3_report_provider or _load_phase3_report_provider()
    predecessor_value = provider()
    predecessor = (
        predecessor_value if isinstance(predecessor_value, Mapping) else {}
    )
    scenarios = _scenario_map(predecessor.get("scenario_results"))
    predecessor_valid = _predecessor_is_valid(predecessor, scenarios)
    samples = _build_chunk_jsonl_samples(scenarios)
    jsonl_lines = [_to_jsonl_line(sample) for sample in samples]
    coverage_report = _build_coverage_report(predecessor, scenarios, samples)
    low_quality_list = _build_low_quality_chunk_list(scenarios)
    regression_test_results = _build_regression_test_results(predecessor, samples)
    strategy_applicability_boundary = _build_strategy_applicability_boundary()
    regeneration_and_version_rollback_instructions = (
        _build_regeneration_and_version_rollback_instructions()
    )
    runtime_boundary_preserved = all(
        predecessor.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS
    )
    samples_valid = len(samples) == len(EXPECTED_SCENARIO_IDS) and all(
        _sample_has_control_only_shape(sample) for sample in samples
    )
    low_quality_list_valid = len(low_quality_list) == len(
        EXPECTED_SCENARIO_IDS
    ) and all(
        item["human_handling_required"]
        and item["control_metadata_only"]
        and item["actual_low_quality_chunk_observed"] is False
        and item["actual_quality_measurement_performed"] is False
        for item in low_quality_list
    )
    valid = (
        predecessor_valid
        and runtime_boundary_preserved
        and samples_valid
        and len(jsonl_lines) == len(samples)
        and all(
            _jsonl_line_matches_sample(line, sample)
            for line, sample in zip(jsonl_lines, samples)
        )
        and coverage_report["control_coverage_complete"]
        and coverage_report["actual_document_coverage_calculated"] is False
        and coverage_report["actual_chunk_coverage_calculated"] is False
        and low_quality_list_valid
        and regression_test_results["control_regression_consistent"]
        and regression_test_results["actual_quality_regression_performed"] is False
        and strategy_applicability_boundary["fixed_control_scenarios_only"]
        and strategy_applicability_boundary[
            "actual_engineering_semantic_asset_classification_strategy_applicability_validated"
        ]
        is False
        and regeneration_and_version_rollback_instructions[
            "in_memory_control_replay_only"
        ]
        and regeneration_and_version_rollback_instructions[
            "actual_chunk_regeneration_performed"
        ]
        is False
        and regeneration_and_version_rollback_instructions[
            "actual_chunk_version_rollback_performed"
        ]
        is False
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "phase3_control_scenarios_reused_as_reference_only": True,
        "chunk_jsonl_samples": samples,
        "chunk_jsonl_sample_lines": jsonl_lines,
        "chunk_jsonl_sample_count": len(samples),
        "coverage_report": coverage_report,
        "low_quality_chunk_list": low_quality_list,
        "regression_test_results": regression_test_results,
        "strategy_applicability_boundary": strategy_applicability_boundary,
        "regeneration_and_version_rollback_instructions": (
            regeneration_and_version_rollback_instructions
        ),
        "human_confirmation_prompts_zh": _human_confirmation_prompts(),
        "source_document_remains_authoritative": True,
        "delivery_evidence_can_replace_source_document": False,
        "delivery_evidence_can_become_business_fact_authority": False,
        "actual_source_document_read_performed": False,
        "actual_chunk_jsonl_written": False,
        "actual_document_coverage_calculated": False,
        "actual_chunk_coverage_calculated": False,
        "actual_low_quality_chunk_observed": False,
        "actual_quality_measurement_performed": False,
        "actual_quality_regression_performed": False,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "parser_execution_performed": False,
        "chapter_detection_performed": False,
        "chunking_execution_performed": False,
        "chunk_identity_generation_performed": False,
        "chunk_hash_computation_performed": False,
        "chunk_version_generation_performed": False,
        "semantic_asset_classification_performed": False,
        "coverage_calculation_performed": False,
        "quality_regression_performed": False,
        "quality_degradation_performed": False,
        "source_traceability_binding_performed": False,
        "embedding_or_index_write_performed": False,
        "database_connection_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage065_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "push_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "valid": valid,
        "result": PASS_RESULT if valid else FAIL_RESULT,
        "next_gate": NEXT_GATE,
    }


def _load_phase3_report_provider() -> ScenarioReportProvider:
    module_path = Path(__file__).with_name(
        "stage065_engineering_semantic_asset_classification_scenarios.py"
    )
    spec = importlib.util.spec_from_file_location("stage065_p3", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Stage065 P3 engineering semantic asset scenarios are unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_engineering_semantic_asset_classification_phase3_report


def _scenario_map(value: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        return {}
    scenarios: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            return {}
        scenario_id = item.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id in scenarios:
            return {}
        scenarios[scenario_id] = item
    return scenarios


def _predecessor_is_valid(
    predecessor: Mapping[str, Any], scenarios: Mapping[str, Mapping[str, Any]]
) -> bool:
    return (
        predecessor.get("valid") is True
        and predecessor.get("result")
        == "PASS_PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
        and predecessor.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("passed_scenario_count") == len(EXPECTED_SCENARIO_IDS)
        and predecessor.get("explicit_disposition_count") == len(
            EXPECTED_SCENARIO_IDS
        )
        and predecessor.get("silent_drop_count") == 0
        and predecessor.get("human_handling_required_count") == len(
            EXPECTED_SCENARIO_IDS
        )
        and predecessor.get("all_taskpack_special_scenarios_covered") is True
        and predecessor.get("phase2_control_slice_reexecuted") is True
        and predecessor.get("phase2_shape_preserved") is True
        and predecessor.get("unique_control_semantic_asset_record_count") == 4
        and predecessor.get("control_traceability_field_count") == len(
            TRACEABILITY_FIELDS
        )
        and predecessor.get("control_traceability_reference_check_count") == 36
        and predecessor.get("control_traceability_reference_shape_preserved") is True
        and predecessor.get("control_duplicate_write_prohibition_asserted") is True
        and tuple(scenarios) == EXPECTED_SCENARIO_IDS
        and all(
            _scenario_has_control_only_shape(scenario)
            for scenario in scenarios.values()
        )
    )


def _scenario_has_control_only_shape(scenario: Mapping[str, Any]) -> bool:
    return (
        scenario.get("human_handling_required") is True
        and scenario.get("silent_drop") is False
        and scenario.get("expectation_met") is True
        and scenario.get("control_traceability_reference_count")
        == len(TRACEABILITY_FIELDS)
        and scenario.get("control_traceability_reference_preserved") is True
        and scenario.get("control_reference_only") is True
        and scenario.get("control_scenario_metadata_only") is True
        and isinstance(scenario.get("explicit_disposition"), str)
        and bool(scenario["explicit_disposition"])
        and isinstance(
            scenario.get("referenced_semantic_asset_classification_record_ref"), str
        )
        and ":control:"
        in scenario["referenced_semantic_asset_classification_record_ref"]
        and isinstance(
            scenario.get("referenced_chunk_identity_version_record_ref"), str
        )
        and ":control:" in scenario["referenced_chunk_identity_version_record_ref"]
        and isinstance(scenario.get("referenced_chapter_aware_chunk_ref"), str)
        and ":control:" in scenario["referenced_chapter_aware_chunk_ref"]
        and all(
            isinstance(scenario.get(field), str) and ":control:" in scenario[field]
            for field in TRACEABILITY_FIELDS
        )
    )


def _build_chunk_jsonl_samples(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        samples.append(
            {
                "sample_id": (
                    "engineering-semantic-asset-jsonl-sample:" f"{scenario_id}"
                ),
                "sample_kind": CHUNK_JSONL_SAMPLE_KIND,
                "scenario_id": scenario_id,
                "scenario_category": scenario.get("scenario_category"),
                "semantic_asset_classification_record_ref": scenario.get(
                    "referenced_semantic_asset_classification_record_ref"
                ),
                "chunk_identity_version_record_ref": scenario.get(
                    "referenced_chunk_identity_version_record_ref"
                ),
                "chapter_aware_chunk_ref": scenario.get(
                    "referenced_chapter_aware_chunk_ref"
                ),
                "semantic_asset_type": scenario.get("referenced_semantic_asset_type"),
                "protected_semantic_surface": scenario.get(
                    "protected_semantic_surface"
                ),
                "explicit_disposition": scenario.get("explicit_disposition"),
                "control_traceability_reference_count": scenario.get(
                    "control_traceability_reference_count"
                ),
                "control_traceability_reference_preserved": scenario.get(
                    "control_traceability_reference_preserved"
                ),
                "human_review_required": True,
                "control_metadata_only": True,
                "source_content_retained": False,
                "actual_chunk_created": False,
                "actual_chunk_id_generated": False,
                "actual_chunk_hash_computed": False,
                "actual_chunk_version_generated": False,
                "actual_semantic_asset_classification_created": False,
                "actual_embedding_written": False,
                "actual_index_written": False,
            }
        )
    return samples


def _to_jsonl_line(sample: Mapping[str, Any]) -> str:
    return json.dumps(sample, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _jsonl_line_matches_sample(line: str, sample: Mapping[str, Any]) -> bool:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return False
    return parsed == dict(sample)


def _sample_has_control_only_shape(sample: Mapping[str, Any]) -> bool:
    return (
        sample.get("sample_kind") == CHUNK_JSONL_SAMPLE_KIND
        and sample.get("control_metadata_only") is True
        and sample.get("human_review_required") is True
        and sample.get("source_content_retained") is False
        and sample.get("actual_chunk_created") is False
        and sample.get("actual_chunk_id_generated") is False
        and sample.get("actual_chunk_hash_computed") is False
        and sample.get("actual_chunk_version_generated") is False
        and sample.get("actual_semantic_asset_classification_created") is False
        and sample.get("actual_embedding_written") is False
        and sample.get("actual_index_written") is False
        and sample.get("control_traceability_reference_count")
        == len(TRACEABILITY_FIELDS)
        and sample.get("control_traceability_reference_preserved") is True
        and isinstance(sample.get("semantic_asset_classification_record_ref"), str)
        and ":control:" in sample["semantic_asset_classification_record_ref"]
        and isinstance(sample.get("chunk_identity_version_record_ref"), str)
        and ":control:" in sample["chunk_identity_version_record_ref"]
        and isinstance(sample.get("chapter_aware_chunk_ref"), str)
        and ":control:" in sample["chapter_aware_chunk_ref"]
    )


def _build_coverage_report(
    predecessor: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
    samples: list[Mapping[str, Any]],
) -> dict[str, Any]:
    categories = [
        scenarios[scenario_id].get("scenario_category")
        for scenario_id in EXPECTED_SCENARIO_IDS
        if scenario_id in scenarios
    ]
    unique_record_refs = {
        sample.get("semantic_asset_classification_record_ref")
        for sample in samples
        if isinstance(sample.get("semantic_asset_classification_record_ref"), str)
    }
    return {
        "report_kind": COVERAGE_REPORT_KIND,
        "control_scenario_count": len(scenarios),
        "chunk_jsonl_sample_count": len(samples),
        "unique_control_semantic_asset_record_count": len(unique_record_refs),
        "covered_scenario_ids": list(EXPECTED_SCENARIO_IDS),
        "covered_scenario_categories": categories,
        "control_traceability_field_count": predecessor.get(
            "control_traceability_field_count"
        ),
        "control_traceability_reference_check_count": predecessor.get(
            "control_traceability_reference_check_count"
        ),
        "control_coverage_complete": (
            tuple(scenarios) == EXPECTED_SCENARIO_IDS
            and len(samples) == len(EXPECTED_SCENARIO_IDS)
            and len(unique_record_refs) == 4
            and all(_sample_has_control_only_shape(sample) for sample in samples)
        ),
        "control_coverage_only": True,
        "actual_document_coverage_calculated": False,
        "actual_chunk_coverage_calculated": False,
        "actual_source_traceability_validated": False,
        "coverage_can_support_real_quality_claim": False,
    }


def _build_low_quality_chunk_list(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for scenario_id in EXPECTED_SCENARIO_IDS:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            continue
        records.append(
            {
                "record_id": (
                    "low-quality-engineering-semantic-asset:control:" f"{scenario_id}"
                ),
                "record_kind": LOW_QUALITY_LIST_KIND,
                "scenario_id": scenario_id,
                "semantic_asset_classification_record_ref": scenario.get(
                    "referenced_semantic_asset_classification_record_ref"
                ),
                "chunk_identity_version_record_ref": scenario.get(
                    "referenced_chunk_identity_version_record_ref"
                ),
                "chapter_aware_chunk_ref": scenario.get(
                    "referenced_chapter_aware_chunk_ref"
                ),
                "quality_disposition": "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW",
                "reason_ref": scenario.get("explicit_disposition"),
                "human_handling_required": True,
                "recommendation_zh": "请由业务线人工白箱复核工程语义资产类型、章节边界、页码、表格上下文和来源位置；本记录不代表真实低质量 chunk 或真实分类结果。",
                "control_metadata_only": True,
                "actual_low_quality_chunk_observed": False,
                "actual_quality_measurement_performed": False,
                "automatic_quality_degradation_action_performed": False,
            }
        )
    return records


def _build_regression_test_results(
    predecessor: Mapping[str, Any], samples: list[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "report_kind": REGRESSION_RESULT_KIND,
        "control_scenario_count": predecessor.get("scenario_count"),
        "passed_control_scenario_count": predecessor.get("passed_scenario_count"),
        "explicit_disposition_count": predecessor.get("explicit_disposition_count"),
        "silent_drop_count": predecessor.get("silent_drop_count"),
        "chunk_jsonl_sample_count": len(samples),
        "control_regression_consistent": (
            predecessor.get("scenario_count") == len(EXPECTED_SCENARIO_IDS)
            and predecessor.get("passed_scenario_count") == len(
                EXPECTED_SCENARIO_IDS
            )
            and predecessor.get("silent_drop_count") == 0
            and len(samples) == len(EXPECTED_SCENARIO_IDS)
        ),
        "actual_quality_regression_performed": False,
        "actual_engineering_semantic_asset_quality_baseline_loaded": False,
        "actual_duplicate_detection_performed": False,
        "actual_embedding_or_index_write_performed": False,
    }


def _build_strategy_applicability_boundary() -> dict[str, Any]:
    return {
        "record_kind": "ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_STRATEGY_APPLICABILITY_BOUNDARY_CONTROL_ONLY",
        "fixed_control_scenarios_only": True,
        "long_document_requires_human_boundary_review": True,
        "cross_page_parameter_table_requires_human_handling": True,
        "engineering_procedure_requires_human_boundary_review": True,
        "parameter_table_requires_human_boundary_review": True,
        "citation_page_requires_human_source_confirmation": True,
        "duplicate_chunk_requires_later_identity_and_human_review": True,
        "unverified_boundary_cannot_trigger_automatic_chunk_write": True,
        "actual_engineering_semantic_asset_classification_strategy_applicability_validated": False,
        "actual_production_acceptance_claim_allowed": False,
    }


def _build_regeneration_and_version_rollback_instructions() -> dict[str, Any]:
    return {
        "record_kind": REGENERATION_ROLLBACK_KIND,
        "return_to": "PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
        "in_memory_control_replay_only": True,
        "preserve_phase1_phase2_phase3_artifacts": True,
        "actual_chunk_regeneration_performed": False,
        "actual_chunk_version_rollback_performed": False,
        "actual_engineering_semantic_asset_classification_implementation_performed": False,
        "actual_source_document_read_performed": False,
        "source_or_raw_data_change_allowed": False,
        "database_or_persistent_state_change_allowed": False,
        "embedding_or_index_write_allowed": False,
        "github_or_ovh_change_allowed": False,
    }


def _human_confirmation_prompts() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "stage065-p4-engineering-semantic-asset-jsonl-human-confirmation",
            "text": "请确认这六条 JSONL 样例仅为工程语义资产分类控制元数据，不代表真实 chunk、分类、页码或来源内容。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "stage065-p4-engineering-semantic-asset-coverage-human-confirmation",
            "text": "请确认覆盖率报告只覆盖六类固定控制场景，真实文档、chunk、分类和页码覆盖率仍需业务线白箱核验。",
            "automatic_confirmation_performed": False,
        },
        {
            "prompt_id": "stage065-p4-engineering-semantic-asset-rollback-human-confirmation",
            "text": "请确认重新生成与版本回滚说明只允许回到 P3 控制状态，不执行真实资料、chunk、分类、索引或数据库回退。",
            "automatic_confirmation_performed": False,
        },
    ]
