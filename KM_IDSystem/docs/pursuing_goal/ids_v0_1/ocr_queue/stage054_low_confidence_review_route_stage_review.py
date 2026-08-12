"""Stage054 低置信度复核路由的独立整阶段本地复审。

模块只读取已提交的 P1--P4 合同，并重放 P3/P4 的固定非业务 control 报告。
输出只保留字段数、计数、状态和边界结论；不输出 OCR 文本、control 内容、业务正文、
真实路径或真实来源，也不启动 OCR、人工任务、缓存或外部运行时。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage054.low_confidence_review_route.stage_review.v1"
RECORD_KIND = "STAGE054_CONTROLLED_LOW_CONFIDENCE_REVIEW_ROUTE_STAGE_REVIEW"
PASS_RESULT = "PASS_REVIEWED_LOCAL_LOW_CONFIDENCE_REVIEW_ROUTE_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_CLOSED_STAGE054_LOW_CONFIDENCE_REVIEW_ROUTE_REVIEW"
REVIEW_GATE = "IDS-STAGE054-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE055-P1-GATE"
CACHE_POLICY = "IN_MEMORY_REBUILDABLE_NOT_PERSISTED"
CACHE_CLEANUP_ACTION = "NO_TEMPORARY_ARTIFACT_CREATED"
REFERENCE_FIELDS = (
    "source_identity_ref",
    "source_page_ref",
    "language_profile",
    "confidence_level",
    "output_status",
    "failure_reason",
    "evidence_eligibility",
    "review_route",
    "cache_policy_ref",
)
REVIEW_REQUEST_FIELDS = REFERENCE_FIELDS + ("feedback_code",)
SCENARIO_CATEGORIES = {
    "SCANNED_PDF_CONTROL",
    "BLURRED_IMAGE_CONTROL",
    "TABLE_IMAGE_CONTROL",
    "MIXED_ZH_EN_CONTROL",
    "LOW_QUALITY_CONTROL",
}
CONFIDENCE_COUNTS = {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1}
SOURCE_AUTHORITIES = {
    "phase1": "FROZEN_TASKPACK_TEXT_AND_STAGE053_REVIEW_ARTIFACTS",
    "phase2": "FROZEN_TASKPACK_TEXT_AND_STAGE054_PHASE1_AND_STAGE053_REVIEW_ARTIFACTS",
    "phase3": "FROZEN_TASKPACK_TEXT_AND_STAGE054_PHASE1_PHASE2_ARTIFACTS",
    "phase4": "FROZEN_TASKPACK_TEXT_AND_STAGE054_PHASE1_PHASE2_PHASE3_ARTIFACTS",
}

_BASE = Path(__file__).resolve().parent
_CONTRACT_PATHS = {
    "phase1": _BASE / "stage054_low_confidence_review_route_contract.json",
    "phase2": _BASE / "stage054_low_confidence_review_route_slice_contract.json",
    "phase3": _BASE / "stage054_low_confidence_review_route_quality_scenarios_contract.json",
    "phase4": _BASE / "stage054_low_confidence_review_route_delivery_contract.json",
}
_MODULE_PATHS = {
    "phase3": _BASE / "stage054_low_confidence_review_route_quality_scenarios.py",
    "phase4": _BASE / "stage054_low_confidence_review_route_delivery.py",
}

ContractProvider = Callable[[], Mapping[str, Mapping[str, Any]]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage054_review_report(
    contract_provider: ContractProvider | None = None,
    quality_report_provider: ReportProvider | None = None,
    delivery_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """复审 P1--P4 control 证据，返回可机器验证的本地白箱结论。"""

    contracts = _load_contracts(contract_provider)
    quality_report = _mapping_or_empty(
        (quality_report_provider or _load_quality_report_provider())()
    )
    delivery_report = _mapping_or_empty(
        (delivery_report_provider or _load_delivery_report_provider())()
    )
    phase_results = {
        "phase1_contract_valid": _phase1_contract_valid(contracts["phase1"]),
        "phase2_slice_valid": _phase2_slice_valid(contracts["phase2"]),
        "phase3_scenarios_valid": _phase3_scenarios_valid(
            contracts["phase3"], quality_report
        ),
        "phase4_delivery_valid": _phase4_delivery_valid(
            contracts["phase4"], delivery_report
        ),
    }
    review_invariants = {
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            contracts
        ),
        "phase1_to_phase4_contracts_valid": all(phase_results.values()),
        "review_request_shape_preserved": _review_request_shape_preserved(contracts),
        "explicit_disposition_and_no_silent_drop_preserved": (
            quality_report.get("scenario_count") == 5
            and quality_report.get("passed_scenario_count") == 5
            and quality_report.get("explicit_disposition_count") == 5
            and quality_report.get("silent_drop_count") == 0
        ),
        "metadata_only_delivery_boundary_preserved": _metadata_only_delivery_boundary(
            delivery_report
        ),
        "quality_limit_and_confirmation_boundary_preserved": (
            _quality_limit_and_confirmation_boundary_preserved(delivery_report)
        ),
        "cache_and_rerun_boundary_preserved": _cache_and_rerun_boundary_preserved(
            contracts, quality_report, delivery_report
        ),
        "rollback_chain_preserved": _rollback_chain_preserved(
            contracts, delivery_report
        ),
        "runtime_and_external_actions_disabled": _runtime_actions_disabled(
            contracts, quality_report, delivery_report
        ),
    }
    review_valid = all(review_invariants.values())
    findings = [] if review_valid else ["STAGE054_REVIEW_INVARIANT_NOT_MET"]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "stage": "STAGE-054",
        "task_id": "IDS-V0_1-STAGE054-REVIEW",
        "acceptance_id": "ACC-STAGE-054",
        "source_authority": (
            "FROZEN_TASKPACK_TEXT_STAGE054_P1_TO_P4_AND_STAGE053_REVIEW_ARTIFACTS"
        ),
        "second_authoritative_source_created": False,
        "source_body_or_path_allowed": False,
        "raw_metadata_content_accessed": False,
        "phase_contracts_reviewed": ["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        "phase_results": phase_results,
        "controlled_replay": {
            "phase1_reference_input_field_count": len(
                _mapping_or_empty(
                    contracts["phase1"].get("reference_only_review_input_contract")
                ).get("required_fields", [])
            ),
            "phase1_future_review_request_field_count": _mapping_or_empty(
                contracts["phase1"].get("future_review_request_contract")
            ).get("field_count"),
            "phase1_default_language_count": _mapping_or_empty(
                contracts["phase1"].get("bilingual_language_contract")
            ).get("default_language_count"),
            "phase2_control_record_count": _mapping_or_empty(
                contracts["phase2"].get("reference_only_input_contract")
            ).get("control_record_count"),
            "phase2_review_request_candidate_field_count": _mapping_or_empty(
                contracts["phase2"].get("review_request_candidate_contract")
            ).get("field_count"),
            "phase2_in_memory_review_route_candidate_count": 3,
            "phase3_scenario_count": quality_report.get("scenario_count"),
            "phase3_explicit_disposition_count": quality_report.get(
                "explicit_disposition_count"
            ),
            "phase3_silent_drop_count": quality_report.get("silent_drop_count"),
            "phase3_review_route_candidate_count": quality_report.get(
                "automatic_review_route_candidate_count"
            ),
            "phase4_delivery_metadata_only_sample_count": len(
                _list_of_mappings(delivery_report.get("delivery_samples"))
            ),
            "phase4_confidence_counts": _mapping_or_empty(
                delivery_report.get("confidence_report")
            ).get("confidence_counts"),
            "phase4_failure_list_count": len(
                _list_of_mappings(delivery_report.get("failure_list"))
            ),
            "phase4_review_route_proof_count": len(
                _list_of_mappings(delivery_report.get("review_route_proofs"))
            ),
            "phase4_human_confirmation_prompt_count": len(
                _list_of_mappings(
                    delivery_report.get("human_confirmation_prompts_zh")
                )
            ),
        },
        "review_invariants": review_invariants,
        "review_finding_count": len(findings),
        "review_findings": findings,
        "review_valid": review_valid,
        "execution_ready": False,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "review_gate": REVIEW_GATE,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "ids_business_source_read_performed": False,
        "source_file_open_performed": False,
        "file_type_detection_performed": False,
        "route_evaluation_performed": False,
        "parser_execution_performed": False,
        "pdf_rasterization_performed": False,
        "image_processing_performed": False,
        "table_structure_extraction_performed": False,
        "ocr_engine_selected": False,
        "ocr_engine_invocation_performed": False,
        "persistent_queue_write_performed": False,
        "cache_write_performed": False,
        "cache_cleanup_performed": False,
        "review_queue_write_performed": False,
        "quality_gate_evaluation_performed": False,
        "evidence_promotion_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": True,
        "stage055_started": False,
        "stage055_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }


def _load_contracts(
    contract_provider: ContractProvider | None,
) -> dict[str, dict[str, Any]]:
    raw_contracts = (
        contract_provider()
        if contract_provider is not None
        else {
            name: json.loads(path.read_text(encoding="utf-8"))
            for name, path in _CONTRACT_PATHS.items()
        }
    )
    raw_contracts = _mapping_or_empty(raw_contracts)
    return {
        name: _mapping_or_empty(raw_contracts.get(name))
        for name in _CONTRACT_PATHS
    }


def _load_quality_report_provider() -> ReportProvider:
    module = _load_module("stage054_review_phase3", _MODULE_PATHS["phase3"])
    return module.build_low_confidence_review_route_phase3_report


def _load_delivery_report_provider() -> ReportProvider:
    module = _load_module("stage054_review_phase4", _MODULE_PATHS["phase4"])
    return module.build_low_confidence_review_route_phase4_delivery_report


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage054 review dependency is unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _mapping_or_empty(
        contract.get("reference_only_review_input_contract")
    )
    request = _mapping_or_empty(contract.get("future_review_request_contract"))
    language = _mapping_or_empty(contract.get("bilingual_language_contract"))
    confidence = _mapping_or_empty(contract.get("confidence_and_route_boundary"))
    ownership = _mapping_or_empty(contract.get("ownership_boundary"))
    cache = _mapping_or_empty(contract.get("cache_boundary"))
    return (
        contract.get("schema_version")
        == "ids.stage054.low_confidence_review_route.phase1.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE054-P1"
        and contract.get("execution_ready") is False
        and input_contract.get("required_fields") == list(REFERENCE_FIELDS)
        and input_contract.get("field_count") == 9
        and input_contract.get("source_body_or_path_allowed") is False
        and input_contract.get("source_page_content_allowed") is False
        and input_contract.get("image_content_allowed") is False
        and input_contract.get("ocr_text_allowed") is False
        and input_contract.get("human_review_content_allowed") is False
        and request.get("required_fields") == list(REVIEW_REQUEST_FIELDS)
        and request.get("field_count") == 10
        and request.get("actual_review_request_created") is False
        and request.get("review_queue_record_created") is False
        and request.get("human_review_result_created") is False
        and request.get("initial_fact_level") == "CANDIDATE"
        and request.get("initial_quality_state") == "UNASSESSED"
        and language.get("default_languages") == ["SIMPLIFIED_CHINESE", "ENGLISH"]
        and language.get("default_language_count") == 2
        and language.get("default_simplified_chinese_and_english_confirmed") is True
        and language.get("mixed_language_profile_declared") is True
        and confidence.get("confidence_levels") == ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
        and confidence.get("numeric_threshold_assigned") is False
        and confidence.get("future_route_state_count") == 3
        and confidence.get("low_confidence_direct_high_trust_allowed") is False
        and confidence.get("mixed_language_direct_high_trust_allowed") is False
        and confidence.get("failure_page_direct_high_trust_allowed") is False
        and confidence.get("automatic_human_review_assignment_allowed") is False
        and confidence.get("evidence_promotion_allowed") is False
        and ownership.get("low_confidence_review_route_owner") == "STAGE-054"
        and ownership.get("ocr_engine_mapping_owner") == "STAGE-055"
        and ownership.get("ocr_cache_retention_owner") == "STAGE-056"
        and cache.get("cache_created") is False
        and cache.get("cache_write_allowed") is False
        and cache.get("cache_cleanup_owner") == "STAGE-056"
        and _runtime_boundary_disabled(contract, {"stage054_started"})
    )


def _phase2_slice_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _mapping_or_empty(contract.get("reference_only_input_contract"))
    candidate = _mapping_or_empty(contract.get("review_request_candidate_contract"))
    route = _mapping_or_empty(contract.get("route_contract"))
    cache = _mapping_or_empty(contract.get("cache_boundary"))
    return (
        contract.get("schema_version")
        == "ids.stage054.low_confidence_review_route.phase2.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE054-P2"
        and contract.get("slice_executable") is True
        and contract.get("execution_ready") is False
        and input_contract.get("required_fields") == list(REFERENCE_FIELDS)
        and input_contract.get("field_count") == 9
        and input_contract.get("control_record_count") == 4
        and input_contract.get("source_body_or_path_allowed") is False
        and candidate.get("required_fields") == list(REVIEW_REQUEST_FIELDS)
        and candidate.get("field_count") == 10
        and candidate.get("in_memory_candidate_created") is True
        and candidate.get("actual_review_request_created") is False
        and candidate.get("review_queue_record_created") is False
        and candidate.get("human_review_task_created") is False
        and candidate.get("human_review_result_created") is False
        and route.get("route_state_count") == 3
        and route.get("low_confidence_route_count") == 1
        and route.get("mixed_language_route_count") == 1
        and route.get("failed_page_route_count") == 1
        and route.get("no_review_route_required_count") == 1
        and route.get("low_confidence_direct_high_trust_allowed") is False
        and route.get("mixed_language_direct_high_trust_allowed") is False
        and route.get("failure_page_direct_high_trust_allowed") is False
        and route.get("automatic_human_review_assignment_performed") is False
        and cache.get("policy") == CACHE_POLICY
        and cache.get("cache_created") is False
        and cache.get("cache_write_performed") is False
        and cache.get("cache_cleanup_performed") is False
        and _runtime_boundary_disabled(
            contract,
            {
                "in_memory_controlled_review_route_execution_allowed",
                "in_memory_review_request_candidate_creation_allowed",
            },
        )
    )


def _phase3_scenarios_valid(
    contract: Mapping[str, Any], report: Mapping[str, Any]
) -> bool:
    input_boundary = _mapping_or_empty(contract.get("scenario_input_boundary"))
    validation = _mapping_or_empty(contract.get("review_route_scenario_validation"))
    cache = _mapping_or_empty(contract.get("cache_boundary"))
    scenarios = _list_of_mappings(report.get("scenario_results"))
    return (
        contract.get("schema_version")
        == "ids.stage054.low_confidence_review_route.phase3.quality_scenarios.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE054-P3"
        and contract.get("scenario_executable") is True
        and contract.get("execution_ready") is False
        and input_boundary.get("scenario_count") == 5
        and set(input_boundary.get("scenario_categories", [])) == SCENARIO_CATEGORIES
        and input_boundary.get("scenario_category_is_control_metadata") is True
        and input_boundary.get("actual_pdf_or_image_open_allowed") is False
        and input_boundary.get("actual_page_or_table_content_allowed") is False
        and input_boundary.get("real_source_text_allowed") is False
        and input_boundary.get("real_ocr_text_allowed") is False
        and input_boundary.get("recognition_accuracy_claim_allowed") is False
        and validation.get("phase2_control_route_reexecuted") is True
        and validation.get("control_record_count") == 4
        and validation.get("all_taskpack_quality_categories_covered") is True
        and validation.get("automatic_human_review_assignment_performed") is False
        and validation.get("high_trust_evidence_promotion_allowed") is False
        and validation.get("silent_drop_allowed") is False
        and cache.get("policy") == CACHE_POLICY
        and cache.get("temporary_artifact_count") == 0
        and cache.get("cleanup_action") == CACHE_CLEANUP_ACTION
        and report.get("valid") is True
        and report.get("result")
        == "PASS_PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS_RUNTIME_DISABLED"
        and report.get("scenario_count") == 5
        and report.get("passed_scenario_count") == 5
        and report.get("explicit_disposition_count") == 5
        and report.get("silent_drop_count") == 0
        and report.get("automatic_review_route_candidate_count") == 3
        and len(scenarios) == 5
        and all(item.get("control_scenario_metadata_only") is True for item in scenarios)
        and all(item.get("expectation_met") is True for item in scenarios)
        and all(item.get("explicit_disposition") is True for item in scenarios)
        and not any(item.get("silent_drop") is True for item in scenarios)
        and all(item.get("actual_ocr_text_created") is False for item in scenarios)
        and all(item.get("actual_pdf_or_image_opened") is False for item in scenarios)
        and _runtime_boundary_disabled(
            contract, {"in_memory_controlled_review_route_scenario_execution_allowed"}
        )
    )


def _phase4_delivery_valid(
    contract: Mapping[str, Any], report: Mapping[str, Any]
) -> bool:
    evidence = _mapping_or_empty(contract.get("delivery_evidence"))
    feedback = _mapping_or_empty(contract.get("quality_limitations_and_feedback"))
    cache = _mapping_or_empty(contract.get("cache_rerun_boundary"))
    confidence = _mapping_or_empty(report.get("confidence_report"))
    return (
        contract.get("schema_version")
        == "ids.stage054.low_confidence_review_route.phase4.delivery.v1"
        and contract.get("task_id") == "IDS-V0_1-STAGE054-P4"
        and contract.get("execution_ready") is False
        and contract.get("valid_result")
        == "PASS_PHASE4_LOW_CONFIDENCE_REVIEW_ROUTE_DELIVERY_RUNTIME_DISABLED"
        and evidence.get("source_kind")
        == "P3_FIXED_NON_BUSINESS_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_CONTROL_REPORT"
        and evidence.get("delivery_sample_count") == 5
        and evidence.get("ocr_text_retained") is False
        and evidence.get("real_ocr_output_produced") is False
        and evidence.get("failure_list_count") == 1
        and evidence.get("review_route_proof_count") == 3
        and evidence.get("review_queue_created") is False
        and feedback.get("quality_limitations_recorded_in_chinese") is True
        and feedback.get("human_confirmation_prompt_count") == 3
        and feedback.get("automatic_confirmation_performed") is False
        and cache.get("policy") == CACHE_POLICY
        and cache.get("temporary_artifact_count") == 0
        and cache.get("cleanup_action") == CACHE_CLEANUP_ACTION
        and cache.get("actual_cleanup_performed") is False
        and report.get("valid") is True
        and report.get("result")
        == "PASS_PHASE4_LOW_CONFIDENCE_REVIEW_ROUTE_DELIVERY_RUNTIME_DISABLED"
        and len(_list_of_mappings(report.get("delivery_samples"))) == 5
        and confidence.get("confidence_counts") == CONFIDENCE_COUNTS
        and len(_list_of_mappings(report.get("failure_list"))) == 1
        and len(_list_of_mappings(report.get("review_route_proofs"))) == 3
        and len(_list_of_mappings(report.get("human_confirmation_prompts_zh"))) == 3
        and _runtime_boundary_disabled(
            contract, {"in_memory_delivery_evidence_execution_allowed"}
        )
    )


def _single_authority_boundary_preserved(
    contracts: Mapping[str, Mapping[str, Any]],
) -> bool:
    return all(
        _mapping_or_empty(contract.get("source_authority")).get("authority")
        == SOURCE_AUTHORITIES[name]
        and _mapping_or_empty(contract.get("source_authority")).get(
            "second_authoritative_source_created"
        )
        is False
        and _mapping_or_empty(contract.get("source_authority")).get(
            "source_body_or_path_allowed"
        )
        is False
        and _mapping_or_empty(contract.get("source_authority")).get(
            "raw_metadata_content_access_allowed"
        )
        is False
        and _mapping_or_empty(contract.get("source_authority")).get(
            "live_source_read_performed"
        )
        is False
        for name, contract in contracts.items()
    )


def _review_request_shape_preserved(
    contracts: Mapping[str, Mapping[str, Any]],
) -> bool:
    phase1_input = _mapping_or_empty(
        contracts["phase1"].get("reference_only_review_input_contract")
    )
    phase1_request = _mapping_or_empty(
        contracts["phase1"].get("future_review_request_contract")
    )
    phase2_input = _mapping_or_empty(
        contracts["phase2"].get("reference_only_input_contract")
    )
    phase2_request = _mapping_or_empty(
        contracts["phase2"].get("review_request_candidate_contract")
    )
    return (
        phase1_input.get("required_fields") == list(REFERENCE_FIELDS)
        and phase1_input.get("field_count") == 9
        and phase1_request.get("required_fields") == list(REVIEW_REQUEST_FIELDS)
        and phase1_request.get("field_count") == 10
        and phase2_input.get("required_fields") == list(REFERENCE_FIELDS)
        and phase2_input.get("field_count") == 9
        and phase2_request.get("required_fields") == list(REVIEW_REQUEST_FIELDS)
        and phase2_request.get("field_count") == 10
        and phase1_request.get("actual_review_request_created") is False
        and phase2_request.get("actual_review_request_created") is False
        and phase2_request.get("actual_review_request_persisted") is False
    )


def _metadata_only_delivery_boundary(report: Mapping[str, Any]) -> bool:
    samples = _list_of_mappings(report.get("delivery_samples"))
    failures = _list_of_mappings(report.get("failure_list"))
    route_proofs = _list_of_mappings(report.get("review_route_proofs"))
    return (
        len(samples) == 5
        and all(
            item.get("sample_kind")
            == "DELIVERY_METADATA_ONLY_LOW_CONFIDENCE_REVIEW_ROUTE_SAMPLE_NOT_REAL_OCR"
            and item.get("fact_level") == "CANDIDATE"
            and item.get("quality_state") == "UNASSESSED"
            and item.get("ocr_text_retained") is False
            and item.get("source_content_retained") is False
            and item.get("actual_ocr_output_produced") is False
            and item.get("high_trust_direct_entry_allowed") is False
            for item in samples
        )
        and len(failures) == 1
        and all(
            item.get("record_kind")
            == "CONTROLLED_LOW_CONFIDENCE_REVIEW_ROUTE_FAILURE_LIST_ENTRY_NOT_RUNTIME"
            and item.get("failure_is_control_metadata_only") is True
            and item.get("actual_failure_record_created") is False
            and item.get("evidence_promotion_performed") is False
            and item.get("review_queue_write_performed") is False
            and item.get("silent_drop") is False
            for item in failures
        )
        and len(route_proofs) == 3
        and all(
            item.get("record_kind")
            == "DECLARED_LOW_CONFIDENCE_REVIEW_ROUTE_PROOF_CANDIDATE_ONLY_NOT_QUEUED"
            and item.get("candidate_route_state_created_in_memory") is True
            and item.get("candidate_evidence_only") is True
            and item.get("human_confirmation_required") is True
            and item.get("automatic_human_review_assignment_performed") is False
            and item.get("review_queue_created") is False
            and item.get("review_queue_write_performed") is False
            and item.get("human_review_task_created") is False
            for item in route_proofs
        )
    )


def _quality_limit_and_confirmation_boundary_preserved(
    report: Mapping[str, Any]
) -> bool:
    confidence = _mapping_or_empty(report.get("confidence_report"))
    prompts = _list_of_mappings(report.get("human_confirmation_prompts_zh"))
    limitations = report.get("quality_limitations_zh")
    return (
        isinstance(limitations, list)
        and len(limitations) == 3
        and len(prompts) == 3
        and all(
            isinstance(item.get("text"), str)
            and "确认" in item["text"]
            and item.get("automatic_confirmation_performed") is False
            for item in prompts
        )
        and confidence.get("recognition_accuracy_evaluated") is False
        and confidence.get("quality_gate_evaluated") is False
        and confidence.get("high_trust_evidence_promoted") is False
    )


def _cache_and_rerun_boundary_preserved(
    contracts: Mapping[str, Mapping[str, Any]],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    phase2_cache = _mapping_or_empty(contracts["phase2"].get("cache_boundary"))
    phase3_cache = _mapping_or_empty(contracts["phase3"].get("cache_boundary"))
    phase4_cache = _mapping_or_empty(
        contracts["phase4"].get("cache_rerun_boundary")
    )
    rerun = _mapping_or_empty(delivery_report.get("cache_rerun_instructions"))
    return (
        all(
            cache.get("policy") == CACHE_POLICY
            for cache in (phase2_cache, phase3_cache, phase4_cache)
        )
        and all(
            cache.get("cache_created") is False
            for cache in (phase2_cache, phase3_cache, phase4_cache)
        )
        and phase2_cache.get("cache_write_performed") is False
        and phase3_cache.get("cache_write_performed") is False
        and phase4_cache.get("cache_write_performed") is False
        and phase3_cache.get("temporary_artifact_count") == 0
        and phase4_cache.get("temporary_artifact_count") == 0
        and quality_report.get("temporary_artifact_count") == 0
        and quality_report.get("cache_cleanup_action") == CACHE_CLEANUP_ACTION
        and rerun.get("cache_policy") == CACHE_POLICY
        and rerun.get("temporary_artifact_count") == 0
        and rerun.get("cleanup_action") == CACHE_CLEANUP_ACTION
        and rerun.get("actual_cleanup_performed") is False
        and rerun.get("rerun_is_in_memory_only") is True
        and rerun.get("cache_retention_owner") == "STAGE-056"
    )


def _rollback_chain_preserved(
    contracts: Mapping[str, Mapping[str, Any]],
    delivery_report: Mapping[str, Any],
) -> bool:
    rollback = _mapping_or_empty(delivery_report.get("rollback"))
    return (
        rollback.get("return_to")
        == "PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
        and _mapping_or_empty(contracts["phase4"].get("rollback_contract")).get(
            "return_to"
        )
        == "PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
        and _mapping_or_empty(contracts["phase3"].get("rollback_contract")).get(
            "return_to"
        )
        == "PHASE2_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROL_SLICE_RUNTIME_DISABLED"
        and _mapping_or_empty(contracts["phase2"].get("rollback_contract")).get(
            "return_to"
        )
        == "PHASE1_LOW_CONFIDENCE_REVIEW_ROUTE_BOUNDARY_RUNTIME_DISABLED"
        and _mapping_or_empty(contracts["phase1"].get("rollback_contract")).get(
            "return_to"
        )
        == "STAGE053_REVIEWED_LOCAL_PER_PAGE_OCR_OUTPUT_RUNTIME_DISABLED"
    )


def _runtime_actions_disabled(
    contracts: Mapping[str, Mapping[str, Any]],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    quality_action_fields = (
        "real_pdf_or_image_opened",
        "source_file_open_performed",
        "file_type_detection_performed",
        "route_evaluation_performed",
        "parser_execution_performed",
        "pdf_rasterization_performed",
        "image_processing_performed",
        "table_structure_extraction_performed",
        "recognition_accuracy_evaluated",
        "ocr_engine_selected",
        "ocr_engine_invocation_performed",
        "human_review_queue_write_performed",
        "automatic_human_review_assignment_performed",
        "quality_gate_evaluation_performed",
        "evidence_promotion_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "github_upload_performed",
    )
    delivery_action_fields = tuple(
        name
        for name in quality_action_fields
        if name != "automatic_human_review_assignment_performed"
    ) + (
        "review_queue_created",
        "human_review_task_created",
        "human_review_result_created",
        "actual_ocr_text_created",
        "actual_failure_record_created",
        "cache_created",
        "cache_write_performed",
        "cache_cleanup_performed",
    )
    return (
        _runtime_boundary_disabled(contracts["phase1"], {"stage054_started"})
        and _runtime_boundary_disabled(
            contracts["phase2"],
            {
                "in_memory_controlled_review_route_execution_allowed",
                "in_memory_review_request_candidate_creation_allowed",
            },
        )
        and _runtime_boundary_disabled(
            contracts["phase3"],
            {"in_memory_controlled_review_route_scenario_execution_allowed"},
        )
        and _runtime_boundary_disabled(
            contracts["phase4"], {"in_memory_delivery_evidence_execution_allowed"}
        )
        and all(quality_report.get(name) is False for name in quality_action_fields)
        and quality_report.get("phase4_started") is False
        and all(delivery_report.get(name) is False for name in delivery_action_fields)
        and delivery_report.get("whole_stage_review_performed") is False
        and delivery_report.get("batch_review_performed") is False
        and delivery_report.get("github_upload_performed") is False
    )


def _runtime_boundary_disabled(
    contract: Mapping[str, Any], allowed_true: set[str]
) -> bool:
    boundary = _mapping_or_empty(contract.get("runtime_boundary"))
    return bool(boundary) and all(
        value is True if name in allowed_true else value is False
        for name, value in boundary.items()
    )


def _mapping_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(
        isinstance(item, Mapping) for item in value
    ):
        return []
    return value
