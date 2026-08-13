"""Stage056 OCR 缓存保留策略的本地整阶段复审。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage056.ocr_cache_retention_policy.stage_review.v1"
RECORD_KIND = "STAGE056_OCR_CACHE_RETENTION_POLICY_STAGE_REVIEW"
REVIEW_GATE = "IDS-STAGE056-REVIEW-GATE"
NEXT_GATE = "IDS-STAGE057-P1-GATE"
PASS_RESULT = "PASS_REVIEWED_LOCAL_OCR_CACHE_RETENTION_POLICY_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_OCR_CACHE_RETENTION_POLICY_RUNTIME_DISABLED"

P1_INPUT_FIELDS = (
    "cache_entry_ref",
    "source_identity_ref",
    "source_page_ref",
    "artifact_class",
    "language_profile",
    "confidence_level",
    "cache_state",
    "retention_class",
    "cleanup_eligibility",
    "evidence_eligibility",
    "review_route",
)
P1_OUTPUT_FIELDS = (
    "cache_entry_ref",
    "artifact_class",
    "retention_class",
    "cleanup_eligibility",
    "rebuildability",
    "source_identity_ref",
    "source_page_ref",
    "language_profile",
    "confidence_level",
    "review_route",
)
P3_SCENARIO_CATEGORIES = (
    "SCANNED_PDF_CONTROL",
    "BLURRED_IMAGE_CONTROL",
    "TABLE_IMAGE_CONTROL",
    "MIXED_ZH_EN_CONTROL",
    "LOW_QUALITY_CONTROL",
)
P4_CONFIDENCE_COUNTS = {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1}


def _load_sibling_module(module_name: str) -> Any:
    module_path = Path(__file__).with_name(f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载本地复审依赖：{module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _bool(value: Any) -> bool:
    return value is True


def _all_false(mapping: Mapping[str, Any], *, allowed_true: set[str] | None = None) -> bool:
    allowed = allowed_true or set()
    for key, value in mapping.items():
        if key not in allowed and isinstance(value, bool) and value:
            return False
    return True


def _load_contract_json(filename: str) -> Mapping[str, Any]:
    path = Path(__file__).with_name(filename)
    return _mapping_or_empty(json.loads(path.read_text(encoding="utf-8")))


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _mapping_or_empty(contract.get("source_authority"))
    input_contract = _mapping_or_empty(contract.get("reference_only_cache_input_contract"))
    output_contract = _mapping_or_empty(contract.get("future_cache_policy_output_contract"))
    retention = _mapping_or_empty(contract.get("retention_and_cleanup_policy_contract"))
    runtime = _mapping_or_empty(contract.get("runtime_boundary"))
    language = _mapping_or_empty(contract.get("bilingual_language_contract"))
    confidence = _mapping_or_empty(contract.get("confidence_and_review_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage056.ocr_cache_retention_policy.phase1.v1",
            contract.get("contract_state") == "PHASE1_OCR_CACHE_RETENTION_POLICY_BOUNDARY_RUNTIME_DISABLED",
            contract.get("phase") == "Phase 1",
            source.get("authority") == "FROZEN_TASKPACK_TEXT_AND_STAGE055_REVIEW_ARTIFACTS",
            source.get("second_authoritative_source_created") is False,
            input_contract.get("required_fields") == list(P1_INPUT_FIELDS),
            input_contract.get("field_count") == len(P1_INPUT_FIELDS),
            output_contract.get("required_fields") == list(P1_OUTPUT_FIELDS),
            output_contract.get("field_count") == len(P1_OUTPUT_FIELDS),
            retention.get("temporary_artifact_count") == 0,
            retention.get("physical_storage_location_assigned") is False,
            retention.get("automatic_cleanup_allowed") is False,
            language.get("default_languages") == ["SIMPLIFIED_CHINESE", "ENGLISH"],
            confidence.get("confidence_levels") == ["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
            _all_false(
                runtime,
                allowed_true={
                    "stage055_review_reused_as_reference_only",
                    "stage056_started",
                    "stage056_entry_authorized",
                },
            ),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _mapping_or_empty(contract.get("source_authority"))
    input_contract = _mapping_or_empty(contract.get("reference_only_cache_input_contract"))
    output_contract = _mapping_or_empty(contract.get("cache_policy_output_contract"))
    states = _mapping_or_empty(contract.get("controlled_policy_states"))
    retention = _mapping_or_empty(contract.get("retention_and_cleanup_policy"))
    runtime = _mapping_or_empty(contract.get("runtime_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage056.ocr_cache_retention_policy.phase2.v1",
            contract.get("contract_state") == "PHASE2_OCR_CACHE_RETENTION_POLICY_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("phase") == "Phase 2",
            source.get("authority") == "FROZEN_TASKPACK_TEXT_AND_STAGE056_PHASE1_AND_STAGE055_REVIEW_ARTIFACTS",
            source.get("second_authoritative_source_created") is False,
            input_contract.get("required_fields") == list(P1_INPUT_FIELDS),
            input_contract.get("field_count") == len(P1_INPUT_FIELDS),
            output_contract.get("required_fields") == list(P1_OUTPUT_FIELDS),
            output_contract.get("field_count") == len(P1_OUTPUT_FIELDS),
            states.get("control_policy_candidate_count") == 4,
            states.get("review_queue_created") is False,
            retention.get("physical_cache_item_count") == 0,
            retention.get("automatic_cleanup_allowed") is False,
            _all_false(
                runtime,
                allowed_true={
                    "stage056_started",
                    "stage056_entry_authorized",
                    "phase2_started",
                    "in_memory_controlled_cache_policy_execution_allowed",
                },
            ),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _mapping_or_empty(contract.get("source_authority"))
    scenario_contract = _mapping_or_empty(contract.get("scenario_input_boundary"))
    validation = _mapping_or_empty(contract.get("quality_scenario_validation"))
    retention = _mapping_or_empty(contract.get("cache_boundary"))
    runtime = _mapping_or_empty(contract.get("runtime_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage056.ocr_cache_retention_policy.phase3.quality_scenarios.v1",
            contract.get("contract_state") == "PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            contract.get("phase") == "Phase 3",
            source.get("authority") == "FROZEN_TASKPACK_TEXT_AND_STAGE056_PHASE1_PHASE2_AND_STAGE055_REVIEW_ARTIFACTS",
            source.get("second_authoritative_source_created") is False,
            scenario_contract.get("scenario_count") == len(P3_SCENARIO_CATEGORIES),
            scenario_contract.get("scenario_categories") == list(P3_SCENARIO_CATEGORIES),
            scenario_contract.get("actual_fixture_count") == 0,
            validation.get("silent_drop_count") == 0,
            validation.get("declared_review_route_count") == 3,
            retention.get("physical_cache_item_count") == 0,
            retention.get("cleanup_execution_performed") is False,
            _all_false(
                runtime,
                allowed_true={"in_memory_controlled_quality_scenario_execution_allowed"},
            ),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    source = _mapping_or_empty(contract.get("source_authority"))
    delivery = _mapping_or_empty(contract.get("delivery_evidence"))
    retention = _mapping_or_empty(contract.get("cache_rerun_boundary"))
    runtime = _mapping_or_empty(contract.get("runtime_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage056.ocr_cache_retention_policy.phase4.delivery.v1",
            contract.get("contract_state") == "PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract.get("phase") == "Phase 4",
            contract.get("valid_result") == "PASS_PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_RUNTIME_DISABLED",
            source.get("authority") == "FROZEN_TASKPACK_TEXT_AND_STAGE056_PHASE1_PHASE2_PHASE3_AND_STAGE055_REVIEW_ARTIFACTS",
            source.get("second_authoritative_source_created") is False,
            delivery.get("delivery_sample_count") == 5,
            delivery.get("failure_list_count") == 1,
            delivery.get("review_route_proof_count") == 3,
            delivery.get("confidence_counts") == P4_CONFIDENCE_COUNTS,
            delivery.get("delivery_sample_kind") == "DELIVERY_METADATA_ONLY_OCR_CACHE_RETENTION_POLICY_SAMPLE_NOT_REAL_OCR",
            retention.get("physical_cache_item_count") == 0,
            retention.get("actual_cleanup_performed") is False,
            _all_false(
                runtime,
                allowed_true={"in_memory_delivery_evidence_execution_allowed"},
            ),
        )
    )


def _quality_report_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("valid") is True,
            report.get("result") == "PASS_PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report.get("scenario_count") == 5,
            report.get("passed_scenario_count") == 5,
            report.get("explicit_disposition_count") == 5,
            report.get("silent_drop_count") == 0,
            report.get("candidate_retained_unassessed_count") == 2,
            report.get("low_confidence_degraded_not_queued_count") == 1,
            report.get("mixed_language_degraded_not_queued_count") == 1,
            report.get("declared_review_route_count") == 3,
            report.get("failed_page_quality_scenario_count") == 1,
            report.get("physical_cache_item_count") == 0,
            report.get("cache_cleanup_execution_performed") is False,
        )
    )


def _delivery_report_valid(report: Mapping[str, Any]) -> bool:
    confidence_report = _mapping_or_empty(report.get("confidence_report"))
    samples = _list_of_mappings(report.get("delivery_samples"))
    failures = _list_of_mappings(report.get("failure_list"))
    review_proofs = _list_of_mappings(report.get("review_route_proofs"))
    return all(
        (
            report.get("valid") is True,
            report.get("result") == "PASS_PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_RUNTIME_DISABLED",
            len(samples) == 5,
            len(failures) == 1,
            len(review_proofs) == 3,
            len(_list_of_mappings(report.get("human_confirmation_prompts_zh"))) == 3,
            confidence_report.get("confidence_counts") == P4_CONFIDENCE_COUNTS,
            all(
                item.get("sample_kind")
                == "DELIVERY_METADATA_ONLY_OCR_CACHE_RETENTION_POLICY_SAMPLE_NOT_REAL_OCR"
                for item in samples
            ),
            all(item.get("automatic_confirmation_performed") is False for item in _list_of_mappings(report.get("human_confirmation_prompts_zh"))),
            _mapping_or_empty(report.get("cache_rerun_instructions")).get("physical_cache_item_count") == 0,
            report.get("stage_review_status") == "pending_next_run",
            report.get("next_gate") == REVIEW_GATE,
        )
    )


def _single_authority_boundary_preserved(
    phase1: Mapping[str, Any], phase2: Mapping[str, Any], phase3: Mapping[str, Any], phase4: Mapping[str, Any]
) -> bool:
    contracts = (phase1, phase2, phase3, phase4)
    return all(
        str(_mapping_or_empty(contract.get("source_authority")).get("authority", "")).startswith("FROZEN_TASKPACK_TEXT_AND_")
        and _mapping_or_empty(contract.get("source_authority")).get("second_authoritative_source_created") is False
        and _mapping_or_empty(contract.get("source_authority")).get("source_body_or_path_allowed") is False
        for contract in contracts
    )


def _input_and_output_shape_preserved(phase1: Mapping[str, Any], phase2: Mapping[str, Any]) -> bool:
    phase1_input = _mapping_or_empty(phase1.get("reference_only_cache_input_contract"))
    phase1_output = _mapping_or_empty(phase1.get("future_cache_policy_output_contract"))
    phase2_input = _mapping_or_empty(phase2.get("reference_only_cache_input_contract"))
    phase2_output = _mapping_or_empty(phase2.get("cache_policy_output_contract"))
    return all(
        (
            phase1_input.get("required_fields") == list(P1_INPUT_FIELDS),
            phase1_output.get("required_fields") == list(P1_OUTPUT_FIELDS),
            phase2_input.get("required_fields") == list(P1_INPUT_FIELDS),
            phase2_output.get("required_fields") == list(P1_OUTPUT_FIELDS),
        )
    )


def _metadata_only_delivery_boundary(phase3: Mapping[str, Any], phase4: Mapping[str, Any]) -> bool:
    scenarios = _mapping_or_empty(phase3.get("scenario_input_boundary"))
    delivery = _mapping_or_empty(phase4.get("delivery_evidence"))
    return all(
        (
            scenarios.get("actual_fixture_count") == 0,
            scenarios.get("actual_pdf_or_image_open_allowed") is False,
            scenarios.get("real_ocr_text_allowed") is False,
            delivery.get("delivery_sample_kind") == "DELIVERY_METADATA_ONLY_OCR_CACHE_RETENTION_POLICY_SAMPLE_NOT_REAL_OCR",
            delivery.get("ocr_text_retained") is False,
            delivery.get("real_ocr_output_produced") is False,
        )
    )


def _quality_limit_and_confirmation_boundary_preserved(
    quality_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    return all(
        (
            quality_report.get("silent_drop_count") == 0,
            quality_report.get("declared_review_route_count") == 3,
            len(_list_of_mappings(delivery_report.get("review_route_proofs"))) == 3,
            len(_list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))) == 3,
            all(item.get("automatic_confirmation_performed") is False for item in _list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))),
            delivery_report.get("persistent_state_write_performed") is False,
        )
    )


def _cache_and_rerun_boundary_preserved(phase1: Mapping[str, Any], phase2: Mapping[str, Any], phase3: Mapping[str, Any], phase4: Mapping[str, Any]) -> bool:
    p1 = _mapping_or_empty(phase1.get("retention_and_cleanup_policy_contract"))
    p2 = _mapping_or_empty(phase2.get("retention_and_cleanup_policy"))
    p3 = _mapping_or_empty(phase3.get("cache_boundary"))
    p4 = _mapping_or_empty(phase4.get("cache_rerun_boundary"))
    return all(
        (
            p1.get("temporary_artifact_count") == 0,
            p1.get("physical_storage_location_assigned") is False,
            p2.get("physical_cache_item_count") == 0,
            p2.get("disk_scan_performed") is False,
            p3.get("physical_cache_item_count") == 0,
            p3.get("cleanup_execution_performed") is False,
            p4.get("physical_cache_item_count") == 0,
            p4.get("actual_cleanup_performed") is False,
            p4.get("rerun_is_in_memory_only") is True,
        )
    )


def _rollback_chain_preserved(phase1: Mapping[str, Any], phase2: Mapping[str, Any], phase3: Mapping[str, Any], phase4: Mapping[str, Any]) -> bool:
    expected_targets = (
        "STAGE055_REVIEWED_LOCAL_OCR_REGRESSION_CORPUS_RUNTIME_DISABLED",
        "PHASE1_OCR_CACHE_RETENTION_POLICY_BOUNDARY_RUNTIME_DISABLED",
        "PHASE2_OCR_CACHE_RETENTION_POLICY_CONTROL_SLICE_RUNTIME_DISABLED",
        "PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
    )
    contracts = (phase1, phase2, phase3, phase4)
    actual_targets = tuple(_mapping_or_empty(contract.get("rollback_contract")).get("return_to") for contract in contracts)
    return actual_targets == expected_targets and all(
        _mapping_or_empty(contract.get("rollback_contract")).get("source_or_raw_data_change_allowed") is False
        and _mapping_or_empty(contract.get("rollback_contract")).get("physical_cache_change_allowed") is False
        and _mapping_or_empty(contract.get("rollback_contract")).get("persistent_runtime_state_change_allowed") is False
        and _mapping_or_empty(contract.get("rollback_contract")).get("github_or_ovh_change_allowed") is False
        for contract in contracts
    )


def _runtime_actions_disabled(quality_report: Mapping[str, Any], delivery_report: Mapping[str, Any]) -> bool:
    quality_fields = (
        "authorized_fixture_access_performed",
        "real_pdf_or_image_opened",
        "source_file_open_performed",
        "parser_execution_performed",
        "ocr_engine_invocation_performed",
        "human_review_queue_write_performed",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "github_upload_performed",
    )
    delivery_fields = (
        "authorized_fixture_access_performed",
        "real_pdf_or_image_opened",
        "source_file_open_performed",
        "parser_execution_performed",
        "ocr_engine_invocation_performed",
        "review_queue_created",
        "persistent_state_write_performed",
        "agent_execution_performed",
        "model_call_performed",
        "model_token_consumption_performed",
        "ovh_deployment_performed",
        "production_runtime_activation_performed",
        "github_upload_performed",
    )
    return all(quality_report.get(field) is False for field in quality_fields) and all(
        delivery_report.get(field) is False for field in delivery_fields
    )


def _controlled_replay(
    phase_results: Mapping[str, bool],
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> Mapping[str, Any]:
    phase1_input = _mapping_or_empty(phase1.get("reference_only_cache_input_contract"))
    phase1_output = _mapping_or_empty(phase1.get("future_cache_policy_output_contract"))
    phase2_states = _mapping_or_empty(phase2.get("controlled_policy_states"))
    confidence = _mapping_or_empty(delivery_report.get("confidence_report"))
    return {
        "replay_kind": "STATIC_CONTRACT_AND_IN_MEMORY_CONTROLLED_REPORT_REVIEW",
        "phase_contract_count": len(phase_results),
        "phase_contract_passed_count": sum(phase_results.values()),
        "phase1_reference_input_field_count": phase1_input.get("field_count"),
        "phase1_future_output_field_count": phase1_output.get("field_count"),
        "phase2_control_policy_candidate_count": phase2_states.get("control_policy_candidate_count"),
        "quality_scenario_count": quality_report.get("scenario_count"),
        "quality_explicit_disposition_count": quality_report.get("explicit_disposition_count"),
        "quality_silent_drop_count": quality_report.get("silent_drop_count"),
        "quality_declared_review_route_count": quality_report.get("declared_review_route_count"),
        "delivery_sample_count": len(_list_of_mappings(delivery_report.get("delivery_samples"))),
        "delivery_confidence_counts": confidence.get("confidence_counts"),
        "delivery_failure_list_count": len(_list_of_mappings(delivery_report.get("failure_list"))),
        "delivery_review_route_proof_count": len(_list_of_mappings(delivery_report.get("review_route_proofs"))),
        "delivery_human_confirmation_prompt_count": len(_list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))),
        "real_business_source_read": False,
        "actual_ocr_executed": False,
        "physical_cache_created": 0,
        "persistent_cache_written": False,
        "automatic_business_write_executed": False,
        "production_operation_executed": False,
        "github_operation_executed": False,
        "ovh_operation_executed": False,
        "model_token_consumed": False,
        "agent_runtime_executed": False,
    }


def build_stage056_review_report(
    *,
    phase1_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase2_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase3_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    phase4_contract_provider: Callable[[], Mapping[str, Any]] | None = None,
    quality_report_provider: Callable[[], Mapping[str, Any]] | None = None,
    delivery_report_provider: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """复审 Stage056 P1-P4 的静态合同和受控内存报告，绝不触碰业务资料或运行面。"""
    phase1 = _mapping_or_empty(
        (phase1_contract_provider or (lambda: _load_contract_json("stage056_ocr_cache_retention_policy_contract.json")))()
    )
    phase2 = _mapping_or_empty(
        (phase2_contract_provider or (lambda: _load_contract_json("stage056_ocr_cache_retention_policy_slice_contract.json")))()
    )
    phase3 = _mapping_or_empty(
        (phase3_contract_provider or (lambda: _load_contract_json("stage056_ocr_cache_retention_policy_quality_scenarios_contract.json")))()
    )
    phase4 = _mapping_or_empty(
        (phase4_contract_provider or (lambda: _load_contract_json("stage056_ocr_cache_retention_policy_delivery_contract.json")))()
    )
    quality_report = _mapping_or_empty(
        (quality_report_provider or (lambda: _load_sibling_module("stage056_ocr_cache_retention_policy_quality_scenarios").build_ocr_cache_retention_policy_phase3_report()))()
    )
    delivery_report = _mapping_or_empty(
        (delivery_report_provider or (lambda: _load_sibling_module("stage056_ocr_cache_retention_policy_delivery").build_ocr_cache_retention_policy_phase4_delivery_report()))()
    )

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3),
        "P4": _phase4_contract_valid(phase4),
    }
    review_invariants = {
        "phase_contracts_valid": all(phase_results.values()),
        "quality_report_valid": _quality_report_valid(quality_report),
        "delivery_report_valid": _delivery_report_valid(delivery_report),
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(phase1, phase2, phase3, phase4),
        "input_and_output_shape_preserved": _input_and_output_shape_preserved(phase1, phase2),
        "metadata_only_delivery_boundary": _metadata_only_delivery_boundary(phase3, phase4),
        "quality_limit_and_confirmation_boundary_preserved": _quality_limit_and_confirmation_boundary_preserved(quality_report, delivery_report),
        "cache_and_rerun_boundary_preserved": _cache_and_rerun_boundary_preserved(phase1, phase2, phase3, phase4),
        "rollback_chain_preserved": _rollback_chain_preserved(phase1, phase2, phase3, phase4),
        "runtime_actions_disabled": _runtime_actions_disabled(quality_report, delivery_report),
    }
    review_valid = all(review_invariants.values())
    review_findings = [
        "Stage056 仅复审冻结任务包、P1-P4 静态合同与受控内存报告，不读取真实业务资料。",
        "候选保留、置信度、失败页和人工确认均保持白箱可见；没有静默丢弃或自动业务写入。",
        "缓存策略保持内存候选不落盘，失败路径不创建物理缓存，回滚链逐相位可逆。",
    ]
    if not review_valid:
        review_findings.append("至少一项复审不变量不成立；不得进入 Stage057。")

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "review_gate": REVIEW_GATE,
        "stage_id": "STAGE056",
        "stage_name": "OCR缓存保留策略",
        "task_id": "IDS-V0_1-STAGE056-REVIEW",
        "acceptance_id": "ACC-STAGE-056",
        "stage_review_kind": "LOCAL_STATIC_CONTRACT_REVIEW",
        "source_authority": "FROZEN_TASKPACK_AND_STAGE056_P1_TO_P4_CONTROLLED_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "raw_metadata_content_accessed": False,
        "phase_results": phase_results,
        "controlled_replay": _controlled_replay(phase_results, phase1, phase2, quality_report, delivery_report),
        "review_invariants": review_invariants,
        "review_findings": review_findings,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "next_gate": NEXT_GATE if review_valid else REVIEW_GATE,
        "stage057_started": False,
        "stage057_entry_allowed": False,
        "whole_stage_review_performed": True,
        "batch_review_performed": False,
        "ids_business_source_read_performed": False,
        "real_business_source_read": False,
        "actual_ocr_executed": False,
        "physical_cache_created": 0,
        "persistent_cache_written": False,
        "temporary_file_created": False,
        "automatic_business_write_executed": False,
        "production_operation_executed": False,
        "github_operation_executed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
        "ovh_operation_executed": False,
        "model_token_consumed": False,
        "agent_runtime_executed": False,
        "execution_ready": False,
        "rollback": {
            "rollback_available": True,
            "return_to": "PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            "rollback_action": "恢复 Stage056 P4 交付证据，不触发 OCR、缓存、业务写入、部署或上传。",
            "raw_data_operation": False,
            "persistent_cache_operation": False,
            "production_operation": False,
            "github_operation": False,
            "ovh_operation": False,
        },
    }
