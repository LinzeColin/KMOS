"""Stage114 P3 复核工作流专项异常场景的纯内存控制投影。

模块机械投影 Stage114 P2 的固定 reference-only 控制请求，形成五条专项
场景、五个控制视图和五条业务线白箱处理记录。输出只包含控制引用、固定
状态标签和中文说明；运行边界始终保持关闭。
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage114_review_workflow_control_slice as phase2,
)


SCHEMA_VERSION = "ids.stage114.review_workflow.phase3.v1"
RECORD_KIND = "CONTROL_ONLY_IN_MEMORY_REVIEW_WORKFLOW_SCENARIOS"
CONTROL_ADAPTER_VERSION = "stage114-p3-controlled-scenarios-v1"
PASS_RESULT = "PASS_IN_MEMORY_REVIEW_WORKFLOW_CONTROLLED_SCENARIOS_RUNTIME_DISABLED"
REJECTED_RESULT = "REJECTED_IN_MEMORY_REVIEW_WORKFLOW_CONTROLLED_SCENARIOS"
CONTROL_PREFIX = ":control:stage114-p3:"
CONTROL_FIELDS = ("review_workflow_controlled_scenario_requests",)

PHASE2_CONTROL_SCENARIOS = phase2.CONTROL_SCENARIOS
PHASE2_INPUT_FIELDS = phase2.INPUT_FIELDS
PHASE2_REFERENCE_FIELDS = phase2.PHASE1_CONTROL_REFERENCE_FIELDS

SCENARIO_DYNAMIC_FIELDS = (
    "controlled_scenario_id",
    "controlled_scenario_chinese_title",
    "controlled_scenario_chinese_reason",
    "scenario_trigger_control_label",
    "scenario_route_control_label",
    "scenario_status_control_label",
    "scenario_action_control_label",
    "actor_control_ref",
    "time_control_ref",
    "reason_control_ref",
    "old_value_control_ref",
    "new_value_control_ref",
    "review_result_control_ref",
    "review_audit_control_ref",
    "re_review_control_ref",
    "archive_control_ref",
    "evidence_risk_before_control_ref",
    "evidence_risk_after_control_ref",
    "evidence_trust_level_before_control_ref",
    "evidence_trust_level_after_control_ref",
    "report_quality_score_before_control_ref",
    "report_quality_score_after_control_ref",
    "report_status_impact_control_ref",
    "external_augmentation_and_whitebox_control_ref",
)

SCENARIO_FIELDS = (*PHASE2_INPUT_FIELDS, *SCENARIO_DYNAMIC_FIELDS)

CONTROLLED_SCENARIO_DEFINITIONS = (
    {
        "scenario_id": "low_quality_ocr_review_operation_control",
        "category": "LOW_QUALITY_OCR_REVIEW_OPERATION_CONTROL",
        "phase2_control_scenario": PHASE2_CONTROL_SCENARIOS[0],
        "expected_binding_mode": "CONTROL_BINDING_EVIDENCE_ID",
        "expected_review_status": "pending_review",
        "expected_workflow_action": "submit_for_review",
        "chinese_title": "低质量 OCR 复核操作控制",
        "chinese_reason": "低 OCR 置信度进入待复核控制路径，业务线白箱确认后才可处理。",
        "whitebox_handling_code": "BUSINESS_LINE_WHITEBOX_REVIEW_LOW_QUALITY_OCR",
    },
    {
        "scenario_id": "conflicting_material_review_audit_control",
        "category": "CONFLICTING_MATERIAL_REVIEW_AUDIT_CONTROL",
        "phase2_control_scenario": PHASE2_CONTROL_SCENARIOS[1],
        "expected_binding_mode": "CONTROL_BINDING_EVIDENCE_GAP",
        "expected_review_status": "confirmed",
        "expected_workflow_action": "confirm",
        "chinese_title": "冲突资料复核审计控制",
        "chinese_reason": "资料冲突保留差异说明、确认动作和复核审计的未来控制引用。",
        "whitebox_handling_code": "BUSINESS_LINE_WHITEBOX_REVIEW_CONFLICTING_MATERIAL",
    },
    {
        "scenario_id": "withdrawn_material_re_review_control",
        "category": "WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL",
        "phase2_control_scenario": PHASE2_CONTROL_SCENARIOS[2],
        "expected_binding_mode": "CONTROL_BINDING_EVIDENCE_GAP",
        "expected_review_status": "needs_more_material",
        "expected_workflow_action": "request_more_material",
        "chinese_title": "撤回资料重新复核控制",
        "chinese_reason": "撤回资料固定需补资料、重新复核与归档的未来控制引用。",
        "whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_WITHDRAWN_MATERIAL_RE_REVIEW"
        ),
    },
    {
        "scenario_id": "evidence_trust_report_quality_impact_control",
        "category": "EVIDENCE_TRUST_AND_REPORT_QUALITY_IMPACT_CONTROL",
        "phase2_control_scenario": PHASE2_CONTROL_SCENARIOS[3],
        "expected_binding_mode": "CONTROL_BINDING_EVIDENCE_ID",
        "expected_review_status": "rejected",
        "expected_workflow_action": "reject",
        "chinese_title": "证据可信等级与报告质量影响控制",
        "chinese_reason": "证据风险保留拒绝结果及可信等级、报告质量和报告状态影响控制。",
        "whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EVIDENCE_TRUST_AND_REPORT_QUALITY"
        ),
    },
    {
        "scenario_id": "external_augmentation_internal_evidence_replacement_control",
        "category": "EXTERNAL_AUGMENTATION_INTERNAL_EVIDENCE_REPLACEMENT_CONTROL",
        "phase2_control_scenario": PHASE2_CONTROL_SCENARIOS[4],
        "expected_binding_mode": "CONTROL_BINDING_EVIDENCE_ID",
        "expected_review_status": "archived",
        "expected_workflow_action": "archive",
        "chinese_title": "外部增强替代内部证据控制",
        "chinese_reason": "外部增强保持外部来源身份，归档控制不能替代内部证据或白箱确认。",
        "whitebox_handling_code": (
            "BUSINESS_LINE_WHITEBOX_REVIEW_EXTERNAL_AUGMENTATION_SOURCE_SEPARATION"
        ),
    },
)

CONTROLLED_SCENARIO_IDS = tuple(
    definition["scenario_id"] for definition in CONTROLLED_SCENARIO_DEFINITIONS
)

CONTROL_VIEW_FIELDS = (
    (
        "review_trigger_and_status_control_view",
        "复核触发与状态控制视图",
        (
            "controlled_scenario_id",
            "control_scenario",
            "binding_mode",
            "scenario_trigger_control_label",
            "scenario_route_control_label",
            "scenario_status_control_label",
            "scenario_action_control_label",
            "review_queue_item_ref",
            "review_trigger_type_ref",
        ),
    ),
    (
        "review_operation_audit_control_view",
        "复核操作审计控制视图",
        (
            "controlled_scenario_id",
            "actor_control_ref",
            "time_control_ref",
            "reason_control_ref",
            "old_value_control_ref",
            "new_value_control_ref",
            "review_result_control_ref",
            "review_audit_control_ref",
            "re_review_control_ref",
            "archive_control_ref",
        ),
    ),
    (
        "evidence_trust_report_quality_impact_control_view",
        "证据可信等级与报告质量影响控制视图",
        (
            "controlled_scenario_id",
            "evidence_risk_before_control_ref",
            "evidence_risk_after_control_ref",
            "evidence_trust_level_before_control_ref",
            "evidence_trust_level_after_control_ref",
            "report_quality_score_before_control_ref",
            "report_quality_score_after_control_ref",
            "report_status_impact_control_ref",
        ),
    ),
    (
        "external_augmentation_source_separation_control_view",
        "外部增强来源分离控制视图",
        (
            "controlled_scenario_id",
            "external_augmentation_underlying_source_type_ref",
            "external_augmentation_and_whitebox_control_ref",
            "business_line_whitebox_confirmation_gate_ref",
        ),
    ),
    (
        "business_line_whitebox_execution_boundary_control_view",
        "业务线白箱与执行边界控制视图",
        (
            "controlled_scenario_id",
            "human_confirmation_item_ref",
            "business_line_whitebox_confirmation_gate_ref",
            "external_augmentation_and_whitebox_control_ref",
            "review_workflow_ref",
            "review_audit_record_ref",
        ),
    ),
)

RUNTIME_CLOSED_FIELDS = (
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "external_reference_read_performed",
    "report_or_pdf_read_performed",
    "evidence_ledger_read_performed",
    "evidence_ledger_write_performed",
    "existing_audit_log_read_performed",
    "low_ocr_evaluation_performed",
    "source_conflict_evaluation_performed",
    "withdrawn_material_evaluation_performed",
    "evidence_risk_evaluation_performed",
    "review_workflow_execution_performed",
    "review_queue_entry_created",
    "review_status_transition_performed",
    "review_ui_rendered",
    "review_audit_write_performed",
    "evidence_risk_writeback_performed",
    "evidence_trust_level_change_performed",
    "report_quality_score_change_performed",
    "report_status_update_performed",
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
    "phase2_control_slice_runtime_executed",
    "stage114_phase3_runtime_executed",
)

ZERO_COUNTER_FIELDS = (
    "actual_controlled_scenario_projection_execution_count",
    "actual_business_source_read_count",
    "actual_external_reference_read_count",
    "actual_report_or_pdf_read_count",
    "actual_evidence_ledger_read_count",
    "actual_existing_audit_log_read_count",
    "actual_review_workflow_execution_count",
    "actual_review_queue_entry_count",
    "actual_review_status_transition_count",
    "actual_review_ui_render_count",
    "actual_review_audit_write_count",
    "actual_evidence_risk_writeback_count",
    "actual_evidence_trust_level_change_count",
    "actual_report_quality_score_change_count",
    "actual_report_status_update_count",
    "actual_human_confirmation_count",
    "actual_database_connection_count",
    "actual_audit_log_write_count",
    "actual_persistent_state_write_count",
    "actual_model_call_count",
    "actual_model_token_count",
    "actual_agent_execution_count",
    "actual_ovh_deployment_count",
)

FAILURE_STATES = (
    "CONTROLLED_SCENARIO_INPUT_MISMATCH",
    "PHASE2_CONTROL_REQUEST_SHAPE_MISMATCH",
    "PHASE2_CONTROL_SLICE_RESULT_MISMATCH",
    "PHASE2_RUNTIME_BOUNDARY_BREACH",
    "SCENARIO_BINDING_CONTROL_INVALID",
    "LOW_QUALITY_OCR_CONTROL_MISSING",
    "CONFLICTING_MATERIAL_CONTROL_MISSING",
    "WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL_MISSING",
    "ACTOR_TIME_REASON_OLD_NEW_CONTROL_MISSING",
    "REVIEW_RESULT_OR_AUDIT_CONTROL_MISSING",
    "EVIDENCE_TRUST_OR_REPORT_QUALITY_CONTROL_MISSING",
    "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING",
    "BUSINESS_LINE_WHITEBOX_CONTROL_MISSING",
    "AUTOMATIC_REVIEW_OR_WRITEBACK_BOUNDARY_BREACH",
    "PERSISTENT_RECORD_BOUNDARY_BREACH",
)

CHINESE_FEEDBACK = (
    "复核工作流专项场景已验证，低质量 OCR、资料冲突和撤回资料保持 reference-only 控制记录。",
    "复核操作保留 actor、time、reason、old value、new value、复核结果与复核审计的未来控制引用。",
    "复核结果对 evidence trust level 与报告质量分的影响保持未来写回控制，业务线白箱确认仍为前置。",
    "外部增强保持外部来源身份，不能替代内部证据；真实复核、审计、写回、模型、Agent、OVH 与生产保持未执行。",
    "P4 交付样例、复核日志和 UI 流程说明继续受 IDS-STAGE114-P4-GATE 门禁控制。",
)


def _phase3_control_ref(kind: str, scenario_id: str) -> str:
    return f"{CONTROL_PREFIX}{kind}:{scenario_id}:future-only"


def _runtime_boundary() -> dict[str, bool]:
    return {field: False for field in RUNTIME_CLOSED_FIELDS}


def _zero_actual_counts() -> dict[str, int]:
    return {field: 0 for field in ZERO_COUNTER_FIELDS}


def _controlled_scenario_request(
    definition: Mapping[str, str],
    phase2_request: Mapping[str, Optional[str]],
) -> dict[str, Optional[str]]:
    """将一条 P2 控制请求扩展为固定 P3 场景记录。"""

    scenario_id = definition["scenario_id"]
    request: dict[str, Optional[str]] = dict(phase2_request)
    request.update(
        {
            "controlled_scenario_id": scenario_id,
            "controlled_scenario_chinese_title": definition["chinese_title"],
            "controlled_scenario_chinese_reason": definition["chinese_reason"],
            "scenario_trigger_control_label": _phase3_control_ref(
                "scenario-trigger", scenario_id
            ),
            "scenario_route_control_label": _phase3_control_ref(
                "scenario-route", scenario_id
            ),
            "scenario_status_control_label": _phase3_control_ref(
                "scenario-status", scenario_id
            ),
            "scenario_action_control_label": _phase3_control_ref(
                "scenario-action", scenario_id
            ),
            "actor_control_ref": phase2_request["review_actor_ref"],
            "time_control_ref": phase2_request["review_time_ref"],
            "reason_control_ref": phase2_request["review_transition_reason_ref"],
            "old_value_control_ref": phase2_request["old_value_ref"],
            "new_value_control_ref": phase2_request["new_value_ref"],
            "review_result_control_ref": phase2_request["review_result_ref"],
            "review_audit_control_ref": phase2_request["review_audit_record_ref"],
            "re_review_control_ref": phase2_request["re_review_reference_ref"],
            "archive_control_ref": phase2_request["archive_reference_ref"],
            "evidence_risk_before_control_ref": _phase3_control_ref(
                "evidence-risk-before", scenario_id
            ),
            "evidence_risk_after_control_ref": _phase3_control_ref(
                "evidence-risk-after", scenario_id
            ),
            "evidence_trust_level_before_control_ref": phase2_request[
                "evidence_trust_level_before_ref"
            ],
            "evidence_trust_level_after_control_ref": phase2_request[
                "evidence_trust_level_after_ref"
            ],
            "report_quality_score_before_control_ref": phase2_request[
                "report_quality_score_before_ref"
            ],
            "report_quality_score_after_control_ref": phase2_request[
                "report_quality_score_after_ref"
            ],
            "report_status_impact_control_ref": phase2_request[
                "report_status_impact_ref"
            ],
            "external_augmentation_and_whitebox_control_ref": _phase3_control_ref(
                "external-augmentation-and-whitebox", scenario_id
            ),
        }
    )
    return request


def build_controlled_scenario_input() -> dict[str, list[dict[str, Optional[str]]]]:
    """返回唯一允许的五条 Stage114 P3 专项场景控制输入。"""

    phase2_requests = phase2.build_control_input()[phase2.CONTROL_FIELDS[0]]
    return {
        CONTROL_FIELDS[0]: [
            _controlled_scenario_request(definition, phase2_request)
            for definition, phase2_request in zip(
                CONTROLLED_SCENARIO_DEFINITIONS, phase2_requests
            )
        ]
    }


def _phase2_control_input(
    controlled_scenario_input: Mapping[str, Any],
) -> dict[str, list[dict[str, Optional[str]]]]:
    requests = controlled_scenario_input[CONTROL_FIELDS[0]]
    return {
        phase2.CONTROL_FIELDS[0]: [
            {field: request[field] for field in PHASE2_INPUT_FIELDS}
            for request in requests
        ]
    }


def _phase2_result_is_closed(phase2_result: Mapping[str, Any]) -> bool:
    return all(
        (
            phase2_result.get("input_accepted") is True,
            phase2_result.get("execution_state") == phase2.PASS_RESULT,
            phase2_result.get("failure_state") is None,
            phase2_result.get("control_input_count")
            == len(PHASE2_CONTROL_SCENARIOS),
            phase2_result.get("control_projection_group_count")
            == len(phase2.PROJECTION_FIELDS),
            phase2_result.get("control_projection_field_total_per_request") == 132,
            phase2_result.get("control_projection_field_total") == 660,
            phase2_result.get("persistent_record_created") is False,
            all(value is False for value in phase2_result["runtime_boundary"].values()),
            all(
                value == 0
                for key, value in phase2_result.items()
                if key.startswith("actual_") and isinstance(value, int)
            ),
        )
    )


def _scenario_binding_is_valid(
    scenarios: list[Mapping[str, Optional[str]]],
) -> bool:
    """确认 P3 场景严格承接五条 P2 控制请求。"""

    if len(scenarios) != len(CONTROLLED_SCENARIO_DEFINITIONS):
        return False
    for definition, scenario in zip(CONTROLLED_SCENARIO_DEFINITIONS, scenarios):
        if set(scenario) != set(SCENARIO_FIELDS):
            return False
        if scenario["controlled_scenario_id"] != definition["scenario_id"]:
            return False
        if scenario["control_scenario"] != definition["phase2_control_scenario"]:
            return False
        if scenario["binding_mode"] != definition["expected_binding_mode"]:
            return False
        if (
            scenario["fixed_review_status_control_value"]
            != definition["expected_review_status"]
        ):
            return False
        if (
            scenario["fixed_workflow_action_control_value"]
            != definition["expected_workflow_action"]
        ):
            return False
        if bool(scenario["evidence_id_ref"]) == bool(scenario["evidence_gap_ref"]):
            return False
        for field in PHASE2_REFERENCE_FIELDS:
            if field in {"evidence_id_ref", "evidence_gap_ref"}:
                continue
            value = scenario[field]
            if not (
                isinstance(value, str)
                and value.startswith(phase2.CONTROL_PREFIX)
                and value.endswith(":reference-only")
            ):
                return False
        for field in (
            "scenario_trigger_control_label",
            "scenario_route_control_label",
            "scenario_status_control_label",
            "scenario_action_control_label",
            "evidence_risk_before_control_ref",
            "evidence_risk_after_control_ref",
            "external_augmentation_and_whitebox_control_ref",
        ):
            value = scenario[field]
            if not (
                isinstance(value, str)
                and value.startswith(CONTROL_PREFIX)
                and value.endswith(":future-only")
            ):
                return False
        for field in (
            "actor_control_ref",
            "time_control_ref",
            "reason_control_ref",
            "old_value_control_ref",
            "new_value_control_ref",
            "review_result_control_ref",
            "review_audit_control_ref",
            "re_review_control_ref",
            "archive_control_ref",
            "evidence_trust_level_before_control_ref",
            "evidence_trust_level_after_control_ref",
            "report_quality_score_before_control_ref",
            "report_quality_score_after_control_ref",
            "report_status_impact_control_ref",
        ):
            value = scenario[field]
            if not (
                isinstance(value, str)
                and value.startswith(phase2.CONTROL_PREFIX)
                and value.endswith(":reference-only")
            ):
                return False
    return True


def _control_views(
    scenarios: list[Mapping[str, Optional[str]]],
) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for view_id, chinese_title, fields in CONTROL_VIEW_FIELDS:
        views.append(
            {
                "control_view_id": view_id,
                "control_view_chinese_title": chinese_title,
                "scenario_control_record_count": len(scenarios),
                "actual_control_view_rendered": False,
                "scenario_control_records": [
                    {field: scenario[field] for field in fields}
                    for scenario in scenarios
                ],
            }
        )
    return views


def _business_line_whitebox_handlings(
    scenarios: list[Mapping[str, Optional[str]]],
) -> list[dict[str, Any]]:
    handlings: list[dict[str, Any]] = []
    for definition, scenario in zip(CONTROLLED_SCENARIO_DEFINITIONS, scenarios):
        handlings.append(
            {
                "controlled_scenario_id": scenario["controlled_scenario_id"],
                "scenario_category": definition["category"],
                "business_line_whitebox_handling_code": definition[
                    "whitebox_handling_code"
                ],
                "human_confirmation_item_ref": scenario[
                    "human_confirmation_item_ref"
                ],
                "business_line_whitebox_confirmation_gate_ref": scenario[
                    "business_line_whitebox_confirmation_gate_ref"
                ],
                "business_line_whitebox_confirmation_required": True,
                "actual_human_confirmation_execution_performed": False,
                "actual_final_business_conclusion_recorded": False,
                "handling_state": (
                    "BUSINESS_LINE_WHITEBOX_FUTURE_MANUAL_CONFIRMATION_REQUIRED"
                ),
            }
        )
    return handlings


def _result_base(
    *,
    input_accepted: bool,
    execution_state: str,
    failure_state: Optional[str],
    controlled_scenario_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": RECORD_KIND,
        "control_adapter_version": CONTROL_ADAPTER_VERSION,
        "input_accepted": input_accepted,
        "execution_state": execution_state,
        "failure_state": failure_state,
        "phase2_control_request_count": len(PHASE2_CONTROL_SCENARIOS),
        "phase2_control_input_field_count": len(PHASE2_INPUT_FIELDS),
        "phase2_phase1_reference_field_count": len(PHASE2_REFERENCE_FIELDS),
        "phase2_projection_group_count": len(phase2.PROJECTION_FIELDS),
        "phase2_projection_field_total_per_request": 132,
        "phase2_projection_field_check_count": 660,
        "controlled_scenario_count": controlled_scenario_count,
        "controlled_scenario_field_count": len(SCENARIO_FIELDS),
        "controlled_scenario_field_check_count": (
            controlled_scenario_count * len(SCENARIO_FIELDS)
        ),
        "control_view_count": 0,
        "business_line_whitebox_handling_count": 0,
        **_zero_actual_counts(),
        "persistent_record_created": False,
        "runtime_boundary": _runtime_boundary(),
        "controlled_scenarios": [],
        "control_views": [],
        "business_line_whitebox_handlings": [],
    }


def _rejected_result(failure_state: str) -> dict[str, Any]:
    """返回零运行时、零投影的失败关闭结果。"""

    return _result_base(
        input_accepted=False,
        execution_state=REJECTED_RESULT,
        failure_state=failure_state,
        controlled_scenario_count=0,
    )


def project_review_workflow_controlled_scenarios(
    controlled_scenario_input: Mapping[str, Any],
) -> dict[str, Any]:
    """机械投影固定 P3 输入；漂移输入保持失败关闭。"""

    if controlled_scenario_input != build_controlled_scenario_input():
        return _rejected_result("CONTROLLED_SCENARIO_INPUT_MISMATCH")

    phase2_input = _phase2_control_input(controlled_scenario_input)
    if phase2_input != phase2.build_control_input():
        return _rejected_result("PHASE2_CONTROL_REQUEST_SHAPE_MISMATCH")

    phase2_result = phase2.project_review_workflow_control_slice(phase2_input)
    if not _phase2_result_is_closed(phase2_result):
        return _rejected_result("PHASE2_CONTROL_SLICE_RESULT_MISMATCH")

    scenarios = controlled_scenario_input[CONTROL_FIELDS[0]]
    if not _scenario_binding_is_valid(scenarios):
        return _rejected_result("SCENARIO_BINDING_CONTROL_INVALID")

    result = _result_base(
        input_accepted=True,
        execution_state=PASS_RESULT,
        failure_state=None,
        controlled_scenario_count=len(scenarios),
    )
    views = _control_views(scenarios)
    handlings = _business_line_whitebox_handlings(scenarios)
    result.update(
        {
            "control_view_count": len(views),
            "business_line_whitebox_handling_count": len(handlings),
            "controlled_scenarios": scenarios,
            "control_views": views,
            "business_line_whitebox_handlings": handlings,
        }
    )
    return result
