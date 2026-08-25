"""Stage105 P2：报告证据绑定的纯内存受控最小切片。

本模块只机械投影冻结的控制引用。它不读取业务资料、证据账本、报告或 PDF，
不生成、导出、保存或撤回报告，也不连接数据库、外部服务、模型或 OVH。
"""

from typing import Any, Mapping, Optional


SCHEMA_VERSION = "ids.stage105.report_evidence_binding.phase2.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REPORT_EVIDENCE_BINDING"
CONTROL_ADAPTER_VERSION = "stage105-p2-control-slice-v1"
PASS_RESULT = "PASS_IN_MEMORY_REPORT_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_REPORT_EVIDENCE_BINDING_CONTROL_SLICE"
CONTROL_PREFIX = ":control:stage105-p2:"
CONTROL_FIELDS = ("report_evidence_binding_control_requests",)

CONTROL_SCENARIOS = (
    "evidence_id_binding_reference_only",
    "evidence_gap_binding_reference_only",
    "external_augmentation_section_reference_only",
    "human_confirmation_item_reference_only",
    "report_lifecycle_reference_only",
)
CONTROL_SCENARIO_CONFIGURATION = {
    "evidence_id_binding_reference_only": {"binding_mode": "evidence_id"},
    "evidence_gap_binding_reference_only": {"binding_mode": "evidence_gap"},
    "external_augmentation_section_reference_only": {"binding_mode": "evidence_id"},
    "human_confirmation_item_reference_only": {"binding_mode": "evidence_id"},
    "report_lifecycle_reference_only": {"binding_mode": "evidence_id"},
}

PHASE1_CONTROL_REFERENCE_FIELDS = (
    "report_id_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "index_version_ref",
    "generated_at_ref",
    "data_snapshot_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "external_augmentation_section_ref",
    "external_augmentation_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "report_status_ref",
    "report_impact_analysis_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_and_withdrawal_ref",
    "audit_boundary_ref",
)
INPUT_FIELDS = (
    "control_scenario",
    "binding_mode",
    *PHASE1_CONTROL_REFERENCE_FIELDS,
)

REPORT_SECTION_BINDING_FIELDS = (
    "control_scenario",
    "report_id_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "external_augmentation_section_ref",
    "external_augmentation_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "report_evidence_binding_state",
    "report_section_output_state",
    "pdf_citation_source_display_state",
    "actual_report_section_written",
)
GENERATION_SNAPSHOT_FIELDS = (
    "control_scenario",
    "report_id_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "report_snapshot_ref",
    "generation_snapshot_control_state",
    "actual_generation_snapshot_persisted",
)
REPORT_LIFECYCLE_FIELDS = (
    "control_scenario",
    "report_id_ref",
    "report_status_ref",
    "report_impact_analysis_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_and_withdrawal_ref",
    "audit_boundary_ref",
    "report_lifecycle_control_state",
    "automatic_report_status_update_allowed",
    "automatic_report_quality_scoring_allowed",
    "automatic_report_export_audit_write_allowed",
    "actual_report_status_updated",
    "actual_report_impact_analysis_performed",
    "actual_report_quality_scored",
    "actual_report_export_audit_written",
)
EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_FIELDS = (
    "control_scenario",
    "report_id_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "external_augmentation_section_ref",
    "external_augmentation_source_type_ref",
    "external_public_reference_control_label",
    "model_reasoning_control_label",
    "external_augmentation_representation_state",
    "external_augmentation_may_not_be_internal_project_evidence",
    "external_augmentation_may_not_replace_evidence_binding",
    "external_augmentation_may_not_close_evidence_gap",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "human_confirmation_control_state",
    "business_line_whitebox_confirmation_required",
    "automatic_human_confirmation_allowed",
    "automatic_final_conclusion_allowed",
    "actual_external_augmentation_displayed",
    "actual_human_confirmation_recorded",
    "actual_final_conclusion_published",
)
PROJECTION_FIELDS = (
    ("report_section_binding", REPORT_SECTION_BINDING_FIELDS),
    ("generation_snapshot", GENERATION_SNAPSHOT_FIELDS),
    ("report_lifecycle", REPORT_LIFECYCLE_FIELDS),
    (
        "external_augmentation_and_whitebox_gate",
        EXTERNAL_AUGMENTATION_AND_WHITEBOX_GATE_FIELDS,
    ),
)
RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "report_evidence_binding_performed",
    "report_section_output_performed",
    "report_generation_performed",
    "pdf_generation_performed",
    "citation_generation_performed",
    "data_snapshot_persistence_performed",
    "index_snapshot_persistence_performed",
    "evidence_snapshot_persistence_performed",
    "model_snapshot_persistence_performed",
    "report_status_impact_analysis_performed",
    "report_quality_score_calculation_performed",
    "report_export_audit_write_performed",
    "report_regeneration_or_withdrawal_performed",
    "external_augmentation_displayed",
    "human_confirmation_performed",
    "database_connection_performed",
    "audit_log_write_performed",
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


def _control_ref(kind: str, scenario: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario}:reference-only"


def _control_request(scenario: str) -> dict[str, Optional[str]]:
    """构造一条固定控制请求，不包含业务事实或可执行运行时输入。"""

    configuration = CONTROL_SCENARIO_CONFIGURATION[scenario]
    binding_mode = configuration["binding_mode"]
    return {
        "control_scenario": scenario,
        "binding_mode": f"CONTROL_BINDING_{binding_mode.upper()}",
        "report_id_ref": _control_ref("report-id", scenario),
        "critical_conclusion_ref": _control_ref("critical-conclusion", scenario),
        "evidence_id_ref": (
            _control_ref("evidence-id", scenario)
            if binding_mode == "evidence_id"
            else None
        ),
        "evidence_gap_ref": (
            _control_ref("evidence-gap", scenario)
            if binding_mode == "evidence_gap"
            else None
        ),
        "evidence_grade_ref": _control_ref("evidence-grade", scenario),
        "citation_source_ref": _control_ref("citation-source", scenario),
        "citation_page_ref": _control_ref("citation-page", scenario),
        "index_version_ref": _control_ref("index-version", scenario),
        "generated_at_ref": _control_ref("generated-at", scenario),
        "data_snapshot_ref": _control_ref("data-snapshot", scenario),
        "evidence_snapshot_ref": _control_ref("evidence-snapshot", scenario),
        "model_snapshot_ref": _control_ref("model-snapshot", scenario),
        "external_augmentation_section_ref": _control_ref(
            "external-augmentation-section", scenario
        ),
        "external_augmentation_source_type_ref": _control_ref(
            "external-augmentation-source-type", scenario
        ),
        "human_confirmation_item_ref": _control_ref(
            "human-confirmation-item", scenario
        ),
        "business_line_whitebox_confirmation_gate_ref": _control_ref(
            "business-line-whitebox-confirmation-gate", scenario
        ),
        "report_snapshot_ref": _control_ref("report-snapshot", scenario),
        "report_status_ref": _control_ref("report-status", scenario),
        "report_impact_analysis_ref": _control_ref("report-impact-analysis", scenario),
        "report_quality_score_ref": _control_ref("report-quality-score", scenario),
        "report_export_audit_ref": _control_ref("report-export-audit", scenario),
        "report_template_limit_ref": _control_ref("report-template-limit", scenario),
        "report_regeneration_and_withdrawal_ref": _control_ref(
            "report-regeneration-and-withdrawal", scenario
        ),
        "audit_boundary_ref": _control_ref("audit-boundary", scenario),
    }


def build_control_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的五条 Stage105 P2 非业务控制请求。"""

    return {
        CONTROL_FIELDS[0]: [_control_request(scenario) for scenario in CONTROL_SCENARIOS]
    }


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {
        "actual_business_source_read_count": 0,
        "actual_report_or_pdf_read_count": 0,
        "actual_evidence_ledger_read_count": 0,
        "actual_evidence_ledger_write_count": 0,
        "actual_report_evidence_binding_count": 0,
        "actual_report_section_output_count": 0,
        "actual_report_generation_count": 0,
        "actual_pdf_generation_count": 0,
        "actual_citation_generation_count": 0,
        "actual_snapshot_persistence_count": 0,
        "actual_report_status_impact_analysis_count": 0,
        "actual_report_quality_score_count": 0,
        "actual_report_export_audit_write_count": 0,
        "actual_report_regeneration_or_withdrawal_count": 0,
        "actual_external_augmentation_display_count": 0,
        "actual_human_confirmation_count": 0,
        "actual_database_connection_count": 0,
        "actual_audit_log_write_count": 0,
        "actual_model_call_count": 0,
        "actual_model_token_count": 0,
        "actual_agent_execution_count": 0,
        "actual_ovh_deployment_count": 0,
    }


def _empty_projection_result() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for prefix, _fields in PROJECTION_FIELDS:
        result[f"{prefix}_control_projections"] = []
        result[f"{prefix}_control_projection_count"] = 0
    return result


def _rejected_result() -> dict[str, Any]:
    """非固定控制输入保持拒绝状态，并且不产生控制投影。"""

    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": False,
        "execution_state": REJECTED_RESULT,
        "failure_state": "CONTROL_INPUT_MISMATCH",
        "control_input_count": 0,
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": 0,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        **_empty_projection_result(),
    }


def _binding_state(request: Mapping[str, Optional[str]]) -> str:
    if request["evidence_id_ref"] is not None:
        return "CONTROL_EVIDENCE_ID_BINDING_REFERENCE_ONLY"
    return "CONTROL_EVIDENCE_GAP_BINDING_REFERENCE_ONLY"


def _project(request: Mapping[str, Optional[str]]) -> dict[str, dict[str, Any]]:
    scenario = str(request["control_scenario"])
    return {
        "report_section_binding": {
            "control_scenario": scenario,
            "report_id_ref": request["report_id_ref"],
            "critical_conclusion_ref": request["critical_conclusion_ref"],
            "evidence_id_ref": request["evidence_id_ref"],
            "evidence_gap_ref": request["evidence_gap_ref"],
            "evidence_grade_ref": request["evidence_grade_ref"],
            "citation_source_ref": request["citation_source_ref"],
            "citation_page_ref": request["citation_page_ref"],
            "external_augmentation_section_ref": request[
                "external_augmentation_section_ref"
            ],
            "external_augmentation_source_type_ref": request[
                "external_augmentation_source_type_ref"
            ],
            "human_confirmation_item_ref": request["human_confirmation_item_ref"],
            "business_line_whitebox_confirmation_gate_ref": request[
                "business_line_whitebox_confirmation_gate_ref"
            ],
            "report_snapshot_ref": request["report_snapshot_ref"],
            "report_evidence_binding_state": _binding_state(request),
            "report_section_output_state": (
                "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED"
            ),
            "pdf_citation_source_display_state": (
                "CONTROL_FUTURE_PDF_CITATION_SOURCE_REQUIRED_NOT_RENDERED"
            ),
            "actual_report_section_written": False,
        },
        "generation_snapshot": {
            "control_scenario": scenario,
            "report_id_ref": request["report_id_ref"],
            "data_snapshot_ref": request["data_snapshot_ref"],
            "index_version_ref": request["index_version_ref"],
            "evidence_snapshot_ref": request["evidence_snapshot_ref"],
            "model_snapshot_ref": request["model_snapshot_ref"],
            "generated_at_ref": request["generated_at_ref"],
            "report_snapshot_ref": request["report_snapshot_ref"],
            "generation_snapshot_control_state": (
                "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED"
            ),
            "actual_generation_snapshot_persisted": False,
        },
        "report_lifecycle": {
            "control_scenario": scenario,
            "report_id_ref": request["report_id_ref"],
            "report_status_ref": request["report_status_ref"],
            "report_impact_analysis_ref": request["report_impact_analysis_ref"],
            "report_quality_score_ref": request["report_quality_score_ref"],
            "report_export_audit_ref": request["report_export_audit_ref"],
            "report_template_limit_ref": request["report_template_limit_ref"],
            "report_regeneration_and_withdrawal_ref": request[
                "report_regeneration_and_withdrawal_ref"
            ],
            "audit_boundary_ref": request["audit_boundary_ref"],
            "report_lifecycle_control_state": (
                "CONTROL_REPORT_LIFECYCLE_REFERENCE_ONLY_NOT_EXECUTED"
            ),
            "automatic_report_status_update_allowed": False,
            "automatic_report_quality_scoring_allowed": False,
            "automatic_report_export_audit_write_allowed": False,
            "actual_report_status_updated": False,
            "actual_report_impact_analysis_performed": False,
            "actual_report_quality_scored": False,
            "actual_report_export_audit_written": False,
        },
        "external_augmentation_and_whitebox_gate": {
            "control_scenario": scenario,
            "report_id_ref": request["report_id_ref"],
            "critical_conclusion_ref": request["critical_conclusion_ref"],
            "evidence_id_ref": request["evidence_id_ref"],
            "evidence_gap_ref": request["evidence_gap_ref"],
            "external_augmentation_section_ref": request[
                "external_augmentation_section_ref"
            ],
            "external_augmentation_source_type_ref": request[
                "external_augmentation_source_type_ref"
            ],
            "external_public_reference_control_label": _control_ref(
                "external-public-reference", scenario
            ),
            "model_reasoning_control_label": _control_ref("model-reasoning", scenario),
            "external_augmentation_representation_state": (
                "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED"
            ),
            "external_augmentation_may_not_be_internal_project_evidence": True,
            "external_augmentation_may_not_replace_evidence_binding": True,
            "external_augmentation_may_not_close_evidence_gap": True,
            "human_confirmation_item_ref": request["human_confirmation_item_ref"],
            "business_line_whitebox_confirmation_gate_ref": request[
                "business_line_whitebox_confirmation_gate_ref"
            ],
            "human_confirmation_control_state": (
                "CONTROL_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_NOT_RECORDED"
            ),
            "business_line_whitebox_confirmation_required": True,
            "automatic_human_confirmation_allowed": False,
            "automatic_final_conclusion_allowed": False,
            "actual_external_augmentation_displayed": False,
            "actual_human_confirmation_recorded": False,
            "actual_final_conclusion_published": False,
        },
    }


def execute_report_evidence_binding_control_slice(
    control_input: Mapping[str, Any],
) -> dict[str, Any]:
    """机械投影固定控制输入；任何漂移均返回零运行时拒绝结果。"""

    if control_input != build_control_input():
        return _rejected_result()

    projections = [_project(request) for request in control_input[CONTROL_FIELDS[0]]]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": True,
        "execution_state": PASS_RESULT,
        "failure_state": None,
        "control_input_count": len(projections),
        "control_projection_group_count": len(PROJECTION_FIELDS),
        "control_projection_field_total_per_request": sum(
            len(fields) for _prefix, fields in PROJECTION_FIELDS
        ),
        "control_projection_field_total": len(projections)
        * sum(len(fields) for _prefix, fields in PROJECTION_FIELDS),
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
    }
    for prefix, _fields in PROJECTION_FIELDS:
        records = [projection[prefix] for projection in projections]
        result[f"{prefix}_control_projections"] = records
        result[f"{prefix}_control_projection_count"] = len(records)
    return result
