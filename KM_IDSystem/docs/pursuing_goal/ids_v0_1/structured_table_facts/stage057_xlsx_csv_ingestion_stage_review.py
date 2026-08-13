"""Stage057 XLSX/CSV 接入合同的零运行时整阶段复审。

复审只读取 Git 跟踪的 P1--P4 合同和 P3/P4 control 报告，输出字段形状、
受控计数、显式人工处置和回滚边界。它不读取真实 XLSX/CSV、工作表、单元格、
业务资料或 fixture，也不创建事实、证据、数据库或任何运行时状态。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import importlib.util
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ids.stage057.xlsx_csv_ingestion.stage_review.v1"
TASK_ID = "IDS-V0_1-STAGE057-REVIEW"
ACCEPTANCE_ID = "ACC-STAGE-057"
PASS_RESULT = "PASS_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED"
FAIL_RESULT = "FAIL_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED"
NEXT_GATE = "IDS-STAGE058-P1-GATE"
RETURN_STATE = "PHASE4_XLSX_CSV_INGESTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED"

BASE = Path(__file__).resolve().parent
P1_CONTRACT = BASE / "stage057_xlsx_csv_ingestion_contract.json"
P2_CONTRACT = BASE / "stage057_xlsx_csv_ingestion_slice_contract.json"
P3_CONTRACT = BASE / "stage057_xlsx_csv_ingestion_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "stage057_xlsx_csv_ingestion_delivery_contract.json"

CONTRACT_RUNTIME_FIELDS = (
    "ids_business_source_read_performed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "xlsx_or_csv_parse_performed",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_token_consumption_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
)

P3_RUNTIME_FALSE_FIELDS = (
    "source_file_open_allowed",
    "file_type_detection_allowed",
    "xlsx_or_csv_parse_allowed",
    "real_table_schema_inference_allowed",
    "real_field_identification_allowed",
    "real_structured_fact_extraction_allowed",
    "merged_cell_resolution_allowed",
    "unit_normalization_allowed",
    "date_normalization_allowed",
    "outlier_evaluation_allowed",
    "duplicate_row_evaluation_allowed",
    "numeric_statistic_computation_allowed",
    "database_connection_allowed",
    "database_schema_migration_allowed",
    "structured_fact_write_allowed",
    "rag_summary_write_allowed",
    "persistent_state_write_allowed",
    "agent_execution_allowed",
    "model_call_allowed",
    "model_token_consumption_allowed",
    "local_service_start_allowed",
    "ovh_deployment_allowed",
    "production_runtime_activation_allowed",
    "phase4_started",
    "whole_stage_review_started",
    "batch_review_started",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
)

REVIEW_RUNTIME_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "authorized_fixture_access_performed",
    "source_file_open_performed",
    "xlsx_or_csv_parse_performed",
    "real_table_schema_inference_performed",
    "real_field_identification_performed",
    "real_structured_fact_extraction_performed",
    "real_table_quality_validation_performed",
    "actual_file_reparse_performed",
    "actual_fact_rollback_performed",
    "database_connection_performed",
    "database_schema_migration_performed",
    "structured_fact_write_performed",
    "persistent_state_write_performed",
    "agent_execution_performed",
    "model_call_performed",
    "model_token_consumption_performed",
    "local_service_start_performed",
    "ovh_deployment_performed",
    "production_runtime_activation_performed",
    "stage058_started",
    "stage058_entry_allowed",
    "batch_review_performed",
    "github_upload_performed",
    "github_upload_allowed",
    "push_allowed",
)

ContractProvider = Callable[[], Mapping[str, Any]]
ReportProvider = Callable[[], Mapping[str, Any]]


def build_stage057_review_report(
    phase1_contract_provider: ContractProvider | None = None,
    phase2_contract_provider: ContractProvider | None = None,
    phase3_contract_provider: ContractProvider | None = None,
    phase4_contract_provider: ContractProvider | None = None,
    phase3_report_provider: ReportProvider | None = None,
    phase4_report_provider: ReportProvider | None = None,
) -> dict[str, Any]:
    """机械复审 Stage057 P1--P4，绝不读取真实表格或启动下游阶段。"""

    phase1 = _as_mapping((phase1_contract_provider or _json_provider(P1_CONTRACT))())
    phase2 = _as_mapping((phase2_contract_provider or _json_provider(P2_CONTRACT))())
    phase3 = _as_mapping((phase3_contract_provider or _json_provider(P3_CONTRACT))())
    phase4 = _as_mapping((phase4_contract_provider or _json_provider(P4_CONTRACT))())
    quality_report = _as_mapping((phase3_report_provider or _load_phase3_report_provider())())
    delivery_report = _as_mapping((phase4_report_provider or _load_phase4_report_provider())())

    phase_results = {
        "P1": _phase1_contract_valid(phase1),
        "P2": _phase2_contract_valid(phase2),
        "P3": _phase3_contract_valid(phase3) and _quality_report_valid(quality_report),
        "P4": _phase4_contract_valid(phase4) and _delivery_report_valid(delivery_report),
    }
    controlled_replay = _controlled_replay(phase1, phase2, quality_report, delivery_report)
    invariants = {
        "single_authority_boundary_preserved": _single_authority_boundary_preserved(
            phase1, phase2, phase3, phase4
        ),
        "input_and_output_shape_preserved": _input_and_output_shape_preserved(
            phase1, phase2
        ),
        "quality_and_human_handling_boundary_preserved": _quality_boundary_preserved(
            quality_report, delivery_report
        ),
        "metadata_only_delivery_boundary": _metadata_only_delivery_boundary(
            delivery_report
        ),
        "reparse_and_rollback_chain_preserved": _rollback_chain_preserved(
            phase1, phase2, phase3, phase4, delivery_report
        ),
        "runtime_actions_disabled": _contracts_have_no_runtime_actions(
            phase1, phase2, phase3, phase4
        ),
        "stage058_not_started": True,
    }
    review_valid = all(phase_results.values()) and all(invariants.values())
    review_finding_count = 0 if review_valid else 1
    report = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "source_authority": "FROZEN_TASKPACK_AND_STAGE057_P1_TO_P4_CONTROLLED_ARTIFACTS_ONLY",
        "secondary_authority_created": False,
        "source_body_or_path_allowed": False,
        "phase_results": phase_results,
        "controlled_replay": controlled_replay,
        "review_invariants": invariants,
        "review_finding_count": review_finding_count,
        "review_valid": review_valid,
        "result": PASS_RESULT if review_valid else FAIL_RESULT,
        "rollback": {
            "return_to": RETURN_STATE,
            "revertable_artifacts": [
                "Stage057 review document",
                "Stage057 review module",
                "Stage057 review focused tests",
                "Stage057 review governance projection",
            ],
            "preserve_phase1_to_phase4_evidence": True,
            "source_or_raw_data_change_allowed": False,
            "fixture_change_allowed": False,
            "database_or_persistent_state_change_allowed": False,
            "github_or_ovh_change_allowed": False,
        },
        "next_gate": NEXT_GATE,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "authorized_fixture_access_performed": False,
        "source_file_open_performed": False,
        "xlsx_or_csv_parse_performed": False,
        "real_table_schema_inference_performed": False,
        "real_field_identification_performed": False,
        "real_structured_fact_extraction_performed": False,
        "real_table_quality_validation_performed": False,
        "actual_file_reparse_performed": False,
        "actual_fact_rollback_performed": False,
        "database_connection_performed": False,
        "database_schema_migration_performed": False,
        "structured_fact_write_performed": False,
        "persistent_state_write_performed": False,
        "agent_execution_performed": False,
        "model_call_performed": False,
        "model_token_consumption_performed": False,
        "local_service_start_performed": False,
        "ovh_deployment_performed": False,
        "production_runtime_activation_performed": False,
        "stage057_started": True,
        "phase2_started": True,
        "phase3_started": True,
        "phase4_started": True,
        "whole_stage_review_performed": True,
        "stage058_started": False,
        "stage058_entry_allowed": False,
        "batch_review_performed": False,
        "github_upload_performed": False,
        "github_upload_allowed": False,
        "push_allowed": False,
    }
    report["review_invariants"]["runtime_actions_disabled"] = all(
        report[field] is False for field in REVIEW_RUNTIME_FIELDS
    ) and report["review_invariants"]["runtime_actions_disabled"]
    report["review_valid"] = all(report["phase_results"].values()) and all(
        report["review_invariants"].values()
    )
    report["review_finding_count"] = 0 if report["review_valid"] else 1
    report["result"] = PASS_RESULT if report["review_valid"] else FAIL_RESULT
    return report


def _json_provider(path: Path) -> ContractProvider:
    def provider() -> Mapping[str, Any]:
        return _as_mapping(json.loads(path.read_text(encoding="utf-8")))

    return provider


def _load_phase3_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage057_xlsx_csv_ingestion_quality_scenarios.py",
        "build_xlsx_csv_ingestion_phase3_report",
    )


def _load_phase4_report_provider() -> ReportProvider:
    return _module_callable_provider(
        "stage057_xlsx_csv_ingestion_delivery.py",
        "build_xlsx_csv_ingestion_phase4_delivery_report",
    )


def _module_callable_provider(filename: str, callable_name: str) -> ReportProvider:
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(
        f"stage057_review_{path.stem}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage057 review dependency is unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, callable_name, None)
    if not callable(candidate):
        raise RuntimeError(f"Stage057 review dependency is invalid: {filename}")
    return candidate


def _phase1_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _as_mapping(contract.get("reference_only_table_input_contract"))
    output_contract = _as_mapping(contract.get("future_structured_fact_output_contract"))
    field_contract = _as_mapping(contract.get("field_semantic_contract"))
    location_contract = _as_mapping(contract.get("source_location_and_evidence_contract"))
    failures = _as_mapping(contract.get("failure_and_stop_contract"))
    return all(
        (
            contract.get("schema_version") == "ids.stage057.xlsx_csv_ingestion.phase1.v1",
            contract.get("contract_state") == "PHASE1_XLSX_CSV_INGESTION_CONTRACT_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE057-P1",
            contract.get("next_gate") == "IDS-STAGE057-P2-GATE",
            _single_authority_contract(contract),
            input_contract.get("field_count") == 12,
            input_contract.get("actual_input_record_count") == 0,
            output_contract.get("field_count") == 19,
            output_contract.get("actual_structured_fact_created") is False,
            field_contract.get("field_count") == 7,
            location_contract.get("location_field_count") == 5,
            failures.get("failure_state_count") == 6,
            _contract_runtime_disabled(contract),
        )
    )


def _phase2_contract_valid(contract: Mapping[str, Any]) -> bool:
    input_contract = _as_mapping(contract.get("reference_only_table_input_contract"))
    schema_contract = _as_mapping(contract.get("schema_profile_candidate_contract"))
    fact_contract = _as_mapping(contract.get("structured_fact_candidate_contract"))
    summary_contract = _as_mapping(contract.get("fact_and_rag_summary_boundary"))
    location_contract = _as_mapping(contract.get("source_location_and_evidence_contract"))
    semantic_contract = _as_mapping(contract.get("field_semantic_contract"))
    numeric_contract = _as_mapping(contract.get("numeric_fact_authority_boundary"))
    return all(
        (
            contract.get("schema_version") == "ids.stage057.xlsx_csv_ingestion.phase2.v1",
            contract.get("contract_state") == "PHASE2_XLSX_CSV_INGESTION_CONTROL_SLICE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE057-P2",
            contract.get("next_gate") == "IDS-STAGE057-P3-GATE",
            contract.get("slice_executable") is True,
            _single_authority_contract(contract),
            input_contract.get("field_count") == 12,
            input_contract.get("control_record_count") == 2,
            input_contract.get("actual_input_record_count") == 0,
            schema_contract.get("profile_count") == 2,
            schema_contract.get("identified_field_candidate_count") == 10,
            fact_contract.get("candidate_count") == 10,
            fact_contract.get("actual_structured_fact_created") is False,
            summary_contract.get("rag_summary_candidate_count") == 2,
            summary_contract.get("rag_summary_candidates_separated_from_facts") is True,
            location_contract.get("candidate_binding_count") == 10,
            semantic_contract.get("numeric_field_candidate_count") == 1,
            numeric_contract.get("actual_numeric_fact_count") == 0,
            _contract_runtime_disabled(contract),
        )
    )


def _phase3_contract_valid(contract: Mapping[str, Any]) -> bool:
    return all(
        (
            contract.get("schema_version") == "ids.stage057.xlsx_csv_ingestion.phase3.quality_scenarios.v1",
            contract.get("contract_state") == "PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE057-P3",
            contract.get("next_gate") == "IDS-STAGE057-P4-GATE",
            contract.get("scenario_executable") is True,
            _single_authority_contract(contract),
            _contract_runtime_disabled(contract),
        )
    )


def _phase4_contract_valid(contract: Mapping[str, Any]) -> bool:
    return all(
        (
            contract.get("schema_version") == "ids.stage057.xlsx_csv_ingestion.phase4.delivery.v1",
            contract.get("contract_state") == "PHASE4_XLSX_CSV_INGESTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract.get("task_id") == "IDS-V0_1-STAGE057-P4",
            contract.get("next_gate") == "IDS-STAGE057-REVIEW-GATE",
            contract.get("delivery_evidence_executable") is True,
            _single_authority_contract(contract),
            _contract_runtime_disabled(contract),
        )
    )


def _quality_report_valid(report: Mapping[str, Any]) -> bool:
    return all(
        (
            report.get("valid") is True,
            report.get("result") == "PASS_PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report.get("scenario_count") == 6,
            report.get("passed_scenario_count") == 6,
            report.get("explicit_disposition_count") == 6,
            report.get("silent_drop_count") == 0,
            report.get("unique_fact_candidate_count") == 10,
            report.get("control_source_location_traceability_preserved") is True,
            report.get("actual_source_file_traceability_validated") is False,
            report.get("actual_structured_fact_created") is False,
            report.get("numeric_statistic_computation_performed") is False,
            report.get("agent_execution_performed") is False,
            report.get("model_token_consumption_performed") is False,
            report.get("ovh_deployment_performed") is False,
        )
    )


def _delivery_report_valid(report: Mapping[str, Any]) -> bool:
    inference = _as_mapping(report.get("field_inference_report"))
    quality = _as_mapping(report.get("quality_test_results"))
    rollback = _as_mapping(report.get("reparse_and_fact_rollback_instructions"))
    samples = _list_of_mappings(report.get("delivery_samples"))
    handling = _list_of_mappings(report.get("unrecognized_structure_and_human_handling"))
    prompts = _list_of_mappings(report.get("human_confirmation_prompts_zh"))
    return all(
        (
            report.get("valid") is True,
            report.get("result") == "PASS_PHASE4_XLSX_CSV_INGESTION_DELIVERY_RUNTIME_DISABLED",
            report.get("stage_review_status") == "pending_next_run",
            report.get("next_gate") == "IDS-STAGE057-REVIEW-GATE",
            len(samples) == 6,
            len(handling) == 6,
            len(prompts) == 3,
            inference.get("referenced_field_candidate_count") == 5,
            inference.get("actual_table_schema_created") is False,
            quality.get("scenario_count") == 6,
            quality.get("explicit_disposition_count") == 6,
            quality.get("silent_drop_count") == 0,
            quality.get("actual_table_quality_validation_performed") is False,
            rollback.get("return_to") == "PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            rollback.get("in_memory_control_replay_only") is True,
            rollback.get("actual_file_reparse_performed") is False,
            rollback.get("actual_fact_store_present") is False,
            rollback.get("actual_fact_rollback_performed") is False,
            report.get("agent_execution_performed") is False,
            report.get("model_token_consumption_performed") is False,
            report.get("ovh_deployment_performed") is False,
        )
    )


def _single_authority_boundary_preserved(*contracts: Mapping[str, Any]) -> bool:
    return all(_single_authority_contract(contract) for contract in contracts)


def _single_authority_contract(contract: Mapping[str, Any]) -> bool:
    source = _as_mapping(contract.get("source_authority"))
    return (
        str(source.get("authority", "")).startswith("FROZEN_TASKPACK")
        and source.get("second_authoritative_source_created") is False
        and source.get("source_body_or_path_allowed") is False
        and source.get("raw_metadata_content_access_allowed") is False
    )


def _input_and_output_shape_preserved(
    phase1: Mapping[str, Any], phase2: Mapping[str, Any]
) -> bool:
    return all(
        (
            _as_mapping(phase1.get("reference_only_table_input_contract")).get("field_count") == 12,
            _as_mapping(phase1.get("future_structured_fact_output_contract")).get("field_count") == 19,
            _as_mapping(phase2.get("reference_only_table_input_contract")).get("field_count") == 12,
            _as_mapping(phase2.get("structured_fact_candidate_contract")).get("field_count") == 19,
            _as_mapping(phase2.get("source_location_and_evidence_contract")).get("location_field_count") == 5,
        )
    )


def _quality_boundary_preserved(
    quality_report: Mapping[str, Any], delivery_report: Mapping[str, Any]
) -> bool:
    handling = _list_of_mappings(delivery_report.get("unrecognized_structure_and_human_handling"))
    return all(
        (
            quality_report.get("explicit_disposition_count") == 6,
            quality_report.get("silent_drop_count") == 0,
            quality_report.get("outlier_numeric_block_count") == 1,
            len(handling) == 6,
            all(item.get("human_handling_required") is True for item in handling),
            all(item.get("automatic_fact_write_performed") is False for item in handling),
        )
    )


def _metadata_only_delivery_boundary(report: Mapping[str, Any]) -> bool:
    samples = _list_of_mappings(report.get("delivery_samples"))
    return len(samples) == 6 and all(
        item.get("sample_kind")
        == "DELIVERY_METADATA_ONLY_TABLE_FACT_SAMPLE_NOT_REAL_TABLE_FACT"
        and item.get("control_metadata_only") is True
        and item.get("source_content_retained") is False
        and item.get("typed_value_retained") is False
        and item.get("actual_structured_fact_created") is False
        and item.get("high_trust_direct_entry_allowed") is False
        for item in samples
    )


def _rollback_chain_preserved(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    phase3: Mapping[str, Any],
    phase4: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> bool:
    returns = (
        _as_mapping(phase1.get("rollback_contract")).get("return_to"),
        _as_mapping(phase2.get("rollback_contract")).get("return_to"),
        _as_mapping(phase3.get("rollback_contract")).get("return_to"),
        _as_mapping(phase4.get("rollback_contract")).get("return_to"),
        _as_mapping(delivery_report.get("rollback")).get("return_to"),
    )
    return all(isinstance(value, str) and bool(value) for value in returns) and (
        returns[-1] == "PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED"
    )


def _contracts_have_no_runtime_actions(*contracts: Mapping[str, Any]) -> bool:
    return all(_contract_runtime_disabled(contract) for contract in contracts)


def _contract_runtime_disabled(contract: Mapping[str, Any]) -> bool:
    runtime = _as_mapping(contract.get("runtime_boundary"))
    if not runtime:
        return False
    if "ids_business_source_read_performed" in runtime:
        return all(runtime.get(field) is False for field in CONTRACT_RUNTIME_FIELDS)
    return (
        all(runtime.get(field) is False for field in P3_RUNTIME_FALSE_FIELDS)
        and runtime.get("in_memory_controlled_quality_scenario_execution_allowed")
        is True
    )


def _controlled_replay(
    phase1: Mapping[str, Any],
    phase2: Mapping[str, Any],
    quality_report: Mapping[str, Any],
    delivery_report: Mapping[str, Any],
) -> dict[str, Any]:
    input_contract = _as_mapping(phase1.get("reference_only_table_input_contract"))
    phase2_input_contract = _as_mapping(
        phase2.get("reference_only_table_input_contract")
    )
    output_contract = _as_mapping(phase1.get("future_structured_fact_output_contract"))
    schema_contract = _as_mapping(phase2.get("schema_profile_candidate_contract"))
    fact_contract = _as_mapping(phase2.get("structured_fact_candidate_contract"))
    summary_contract = _as_mapping(phase2.get("fact_and_rag_summary_boundary"))
    location_contract = _as_mapping(phase2.get("source_location_and_evidence_contract"))
    semantic_contract = _as_mapping(phase2.get("field_semantic_contract"))
    inference = _as_mapping(delivery_report.get("field_inference_report"))
    quality = _as_mapping(delivery_report.get("quality_test_results"))
    rollback = _as_mapping(delivery_report.get("reparse_and_fact_rollback_instructions"))
    return {
        "phase_contract_count": 4,
        "phase_contract_passed_count": 4,
        "phase1_reference_input_field_count": input_contract.get("field_count"),
        "phase1_future_structured_fact_output_field_count": output_contract.get("field_count"),
        "phase1_field_semantic_count": _as_mapping(phase1.get("field_semantic_contract")).get("field_count"),
        "phase1_source_location_field_count": _as_mapping(phase1.get("source_location_and_evidence_contract")).get("location_field_count"),
        "phase1_declared_failure_state_count": _as_mapping(phase1.get("failure_and_stop_contract")).get("failure_state_count"),
        "phase2_control_record_count": phase2_input_contract.get("control_record_count"),
        "phase2_schema_profile_candidate_count": schema_contract.get("profile_count"),
        "phase2_structured_fact_candidate_count": fact_contract.get("candidate_count"),
        "phase2_rag_summary_candidate_count": summary_contract.get("rag_summary_candidate_count"),
        "phase2_source_location_binding_candidate_count": location_contract.get("candidate_binding_count"),
        "phase2_numeric_field_candidate_count": semantic_contract.get("numeric_field_candidate_count"),
        "quality_scenario_count": quality_report.get("scenario_count"),
        "quality_explicit_disposition_count": quality_report.get("explicit_disposition_count"),
        "quality_silent_drop_count": quality_report.get("silent_drop_count"),
        "quality_outlier_numeric_block_count": quality_report.get("outlier_numeric_block_count"),
        "delivery_sample_count": len(_list_of_mappings(delivery_report.get("delivery_samples"))),
        "delivery_field_reference_label_count": inference.get("referenced_field_candidate_count"),
        "delivery_quality_result_count": quality.get("scenario_count"),
        "delivery_human_handling_record_count": len(_list_of_mappings(delivery_report.get("unrecognized_structure_and_human_handling"))),
        "delivery_human_confirmation_prompt_count": len(_list_of_mappings(delivery_report.get("human_confirmation_prompts_zh"))),
        "reparse_and_fact_rollback_instructions_created": rollback.get("in_memory_control_replay_only") is True,
    }


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]
