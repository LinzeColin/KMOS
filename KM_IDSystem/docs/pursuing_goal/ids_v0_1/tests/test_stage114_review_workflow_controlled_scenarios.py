"""Stage114 P3 复核工作流专项异常场景的聚焦验证。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage114_review_workflow_controlled_scenarios as controlled_scenarios,
)
from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage114_review_workflow_control_slice as control_slice,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE114_PHASE3_REVIEW_WORKFLOW_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_controlled_scenarios_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-114_复核工作流.md"
)
P2_SCOPE = BASE / "STAGE114_PHASE2_REVIEW_WORKFLOW_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_control_slice_contract.json"
)
P2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p2-local.json"
P3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"

EXPECTED_SCENARIOS = (
    (
        "low_quality_ocr_review_operation_control",
        "low_ocr_pending_review_submit_reference_only",
        "CONTROL_BINDING_EVIDENCE_ID",
        "pending_review",
        "submit_for_review",
    ),
    (
        "conflicting_material_review_audit_control",
        "source_conflict_confirm_reference_only",
        "CONTROL_BINDING_EVIDENCE_GAP",
        "confirmed",
        "confirm",
    ),
    (
        "withdrawn_material_re_review_control",
        "parsing_failure_needs_more_material_reference_only",
        "CONTROL_BINDING_EVIDENCE_GAP",
        "needs_more_material",
        "request_more_material",
    ),
    (
        "evidence_trust_report_quality_impact_control",
        "evidence_risk_reject_reference_only",
        "CONTROL_BINDING_EVIDENCE_ID",
        "rejected",
        "reject",
    ),
    (
        "external_augmentation_internal_evidence_replacement_control",
        "external_augmentation_archive_reference_only",
        "CONTROL_BINDING_EVIDENCE_ID",
        "archived",
        "archive",
    ),
)


class Stage114ReviewWorkflowPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.controlled_scenario_input = (
            controlled_scenarios.build_controlled_scenario_input()
        )
        cls.result = controlled_scenarios.project_review_workflow_controlled_scenarios(
            cls.controlled_scenario_input
        )

    def test_required_artifacts_exist(self) -> None:
        for artifact in (SCOPE, CONTRACT, TASKPACK, P2_SCOPE, P2_CONTRACT, P2_RECEIPT):
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessor_and_contract_shapes_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage114.review_workflow.phase3.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-114", contract["stage"])
        self.assertEqual("IDS-STAGE114-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE114-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-114", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE114-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE114-P4-GATE", contract["next_gate"])
        self.assertEqual(
            "REVIEW_WORKFLOW_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE114_TASKPACK_STAGE114_PHASE1_PHASE2_AND_STAGE113_REVIEW_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
            "scenario_validation_is_engineering_context_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        self.assertFalse(authority["second_authoritative_source_created"])
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage114_phase1_required"])
        self.assertTrue(predecessor["stage114_phase2_required"])
        self.assertEqual(
            control_slice.PASS_RESULT, predecessor["stage114_phase2_result"]
        )
        scenarios = contract["scenario_contract"]
        self.assertEqual(5, scenarios["phase2_control_request_count"])
        self.assertEqual(30, scenarios["phase2_control_input_field_count"])
        self.assertEqual(26, scenarios["phase2_phase1_reference_field_count"])
        self.assertEqual(4, scenarios["phase2_projection_group_count"])
        self.assertEqual(132, scenarios["phase2_projection_field_count_per_request"])
        self.assertEqual(660, scenarios["phase2_projection_field_check_count"])
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(54, scenarios["scenario_field_count"])
        self.assertEqual(270, scenarios["scenario_field_check_count"])
        self.assertEqual(5, scenarios["control_view_count"])
        self.assertEqual(5, scenarios["business_line_whitebox_handling_count"])

    def test_canonical_input_strictly_preserves_p2_shape_and_scenario_binding(self) -> None:
        scenarios = self.controlled_scenario_input[controlled_scenarios.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(scenarios))
        self.assertEqual(30, len(controlled_scenarios.PHASE2_INPUT_FIELDS))
        self.assertEqual(26, len(controlled_scenarios.PHASE2_REFERENCE_FIELDS))
        self.assertEqual(54, len(controlled_scenarios.SCENARIO_FIELDS))
        for scenario, expected in zip(scenarios, EXPECTED_SCENARIOS):
            (
                scenario_id,
                p2_control_scenario,
                binding_mode,
                review_status,
                workflow_action,
            ) = expected
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    set(controlled_scenarios.SCENARIO_FIELDS), set(scenario)
                )
                self.assertEqual(scenario_id, scenario["controlled_scenario_id"])
                self.assertEqual(p2_control_scenario, scenario["control_scenario"])
                self.assertEqual(binding_mode, scenario["binding_mode"])
                self.assertEqual(
                    review_status, scenario["fixed_review_status_control_value"]
                )
                self.assertEqual(
                    workflow_action, scenario["fixed_workflow_action_control_value"]
                )
                self.assertTrue(
                    bool(scenario["evidence_id_ref"])
                    ^ bool(scenario["evidence_gap_ref"])
                )
                for field in controlled_scenarios.PHASE2_REFERENCE_FIELDS:
                    if field in {"evidence_id_ref", "evidence_gap_ref"}:
                        continue
                    with self.subTest(field=field):
                        self.assertTrue(
                            scenario[field].startswith(control_slice.CONTROL_PREFIX)
                        )

    def test_projection_shape_and_zero_runtime_boundary_are_exact(self) -> None:
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            controlled_scenarios.PASS_RESULT, result["execution_state"]
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["phase2_control_request_count"])
        self.assertEqual(30, result["phase2_control_input_field_count"])
        self.assertEqual(26, result["phase2_phase1_reference_field_count"])
        self.assertEqual(4, result["phase2_projection_group_count"])
        self.assertEqual(132, result["phase2_projection_field_total_per_request"])
        self.assertEqual(660, result["phase2_projection_field_check_count"])
        self.assertEqual(5, result["controlled_scenario_count"])
        self.assertEqual(54, result["controlled_scenario_field_count"])
        self.assertEqual(270, result["controlled_scenario_field_check_count"])
        self.assertEqual(5, result["control_view_count"])
        self.assertEqual(5, result["business_line_whitebox_handling_count"])
        self.assertFalse(result["persistent_record_created"])
        self.assertTrue(
            all(value is False for value in result["runtime_boundary"].values())
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in result.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        for scenario in result["controlled_scenarios"]:
            with self.subTest(scenario=scenario["controlled_scenario_id"]):
                self.assertEqual(
                    set(controlled_scenarios.SCENARIO_FIELDS), set(scenario)
                )

    def test_review_operation_fields_remain_future_control_references(self) -> None:
        for scenario in self.result["controlled_scenarios"]:
            with self.subTest(scenario=scenario["controlled_scenario_id"]):
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
                ):
                    self.assertTrue(
                        scenario[field].startswith(control_slice.CONTROL_PREFIX)
                    )
                for field in (
                    "scenario_trigger_control_label",
                    "scenario_route_control_label",
                    "scenario_status_control_label",
                    "scenario_action_control_label",
                ):
                    self.assertTrue(
                        scenario[field].startswith(controlled_scenarios.CONTROL_PREFIX)
                    )
        operation_contract = self.contract["review_operation_and_impact_contract"]
        for field in (
            "actor_time_reason_old_new_controls_required",
            "review_result_control_required",
            "review_audit_control_required",
            "re_review_and_archive_controls_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(operation_contract[field])

    def test_impact_external_augmentation_and_whitebox_controls_are_exact(self) -> None:
        for view in self.result["control_views"]:
            with self.subTest(view=view["control_view_id"]):
                self.assertFalse(view["actual_control_view_rendered"])
                self.assertEqual(5, view["scenario_control_record_count"])
                self.assertEqual(5, len(view["scenario_control_records"]))
        external_scenario = self.result["controlled_scenarios"][-1]
        self.assertEqual(
            "external_augmentation_internal_evidence_replacement_control",
            external_scenario["controlled_scenario_id"],
        )
        self.assertTrue(
            external_scenario[
                "external_augmentation_underlying_source_type_ref"
            ].startswith(control_slice.CONTROL_PREFIX)
        )
        self.assertTrue(
            external_scenario[
                "external_augmentation_and_whitebox_control_ref"
            ].startswith(controlled_scenarios.CONTROL_PREFIX)
        )
        self.assertEqual(5, len(self.result["business_line_whitebox_handlings"]))
        for handling in self.result["business_line_whitebox_handlings"]:
            with self.subTest(scenario=handling["controlled_scenario_id"]):
                self.assertTrue(
                    handling["business_line_whitebox_confirmation_required"]
                )
                self.assertFalse(
                    handling["actual_human_confirmation_execution_performed"]
                )
                self.assertFalse(
                    handling["actual_final_business_conclusion_recorded"]
                )
        source_boundary = self.contract[
            "external_augmentation_and_whitebox_contract"
        ]
        for field in (
            "external_augmentation_may_not_be_internal_project_evidence",
            "external_augmentation_may_not_replace_evidence_binding",
            "external_augmentation_may_not_close_evidence_gap",
            "business_line_whitebox_confirmation_required_before_future_business_use",
        ):
            with self.subTest(field=field):
                self.assertTrue(source_boundary[field])

    def test_input_drift_fails_closed_without_scenarios_or_runtime(self) -> None:
        drifted = copy.deepcopy(self.controlled_scenario_input)
        drifted[controlled_scenarios.CONTROL_FIELDS[0]][0][
            "review_status_after_ref"
        ] = "drifted"
        rejected = controlled_scenarios.project_review_workflow_controlled_scenarios(
            drifted
        )
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            controlled_scenarios.REJECTED_RESULT, rejected["execution_state"]
        )
        self.assertEqual(
            "CONTROLLED_SCENARIO_INPUT_MISMATCH", rejected["failure_state"]
        )
        self.assertEqual(0, rejected["controlled_scenario_count"])
        self.assertEqual(0, rejected["controlled_scenario_field_check_count"])
        self.assertEqual([], rejected["controlled_scenarios"])
        self.assertEqual([], rejected["control_views"])
        self.assertEqual([], rejected["business_line_whitebox_handlings"])
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )

    def test_scope_contract_and_final_governance_follow_phase3(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五条可验证的专项场景控制记录",
            "每条场景固定 54 个字段",
            "actor、time、reason、old value、new value、review result",
            "evidence trust level 与报告质量分",
            "IDS-STAGE114-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertEqual(15, len(controlled_scenarios.FAILURE_STATES))
        failure_contract = self.contract["failure_and_stop_contract"]
        self.assertEqual(15, failure_contract["failure_state_count"])
        self.assertEqual(
            set(controlled_scenarios.FAILURE_STATES),
            set(failure_contract["declared_failure_states"]),
        )
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        if not P3_RECEIPT.is_file():
            self.skipTest("P3 最终治理投影将在本 run 收尾时启用")
        receipt = json.loads(P3_RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("P3 最终治理投影将在本 run 收尾时启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(
            (
                "IDS-STAGE114",
                "IDS-STAGE114-P3",
                "IDS-V0_1-STAGE114-P3",
                "IDS-STAGE114-P4-GATE",
            ),
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
        )
        self.assertEqual(
            "REVIEW_WORKFLOW_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertIn("IDS-STAGE114-P4-GATE", plan["stop_condition"])
        self.assertEqual(controlled_scenarios.PASS_RESULT, receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        self.assertEqual("PASS", receipt["final_validation"]["state"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P3 专项异常场景已完成", acceptance_by_id["ACC-STAGE-114"]
        )
        for acceptance_id in (
            "ACC-STAGE114-P3-01",
            "ACC-STAGE114-P3-02",
            "ACC-STAGE114-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE114-P3-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE114-P3-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
