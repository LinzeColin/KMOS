"""Stage115 P4 复核 UI metadata-only 交付控制验证。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage115_review_ui_controlled_scenarios as phase3,
)
from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage115_review_ui_delivery as phase4,
)
from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE115_PHASE4_REVIEW_UI_DELIVERY.md"
CONTRACT = BASE / "index_version_schema" / "stage115_review_ui_delivery_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-115_复核UI.md"
)
PHASE1_SCOPE = BASE / "STAGE115_PHASE1_REVIEW_UI_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage115_review_ui_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage115-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE115_PHASE2_REVIEW_UI_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage115_review_ui_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage115-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE115_PHASE3_REVIEW_UI_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage115_review_ui_controlled_scenarios_contract.json"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage115-p3-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE114_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage115-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage115ReviewUiPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = phase4.build_review_ui_phase4_delivery_report()

    @staticmethod
    def _mutated_phase3_executor(mutator):
        def executor():
            result = phase3.project_review_ui_controlled_scenarios(
                phase3.build_controlled_scenario_input()
            )
            result = copy.deepcopy(result)
            mutator(result)
            return result

        return executor

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_RECEIPT,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("ids.stage115.review_ui.phase4.delivery.v1", contract["schema_version"])
        self.assertEqual("STAGE-115", contract["stage"])
        self.assertEqual("IDS-STAGE115-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE115-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-115", contract["acceptance_id"])
        self.assertEqual(
            "REVIEW_UI_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE115-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE115-REVIEW-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
            "delivery_validation_is_engineering_context_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage114_review_preserved",
            "stage115_phase1_completed",
            "stage115_phase2_completed",
            "stage115_phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage115_review_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertEqual(
            tuple(phase4.RUNTIME_CLOSED_FIELDS),
            tuple(contract["runtime_boundary"]),
        )
        self.assertTrue(
            all(value is False for value in contract["runtime_boundary"].values())
        )

    def test_phase3_replay_and_delivery_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        expected_replay = {
            "phase2_control_request_count": 5,
            "phase2_input_field_count": 23,
            "phase2_phase1_reference_field_count": 19,
            "phase2_projection_group_count": 4,
            "phase2_projection_field_count_per_request": 117,
            "phase2_projection_field_count_total": 585,
            "scenario_count": 5,
            "scenario_field_count": 47,
            "scenario_field_check_count": 235,
            "control_view_count": 5,
            "business_line_whitebox_handling_count": 5,
            "whitebox_confirmation_required_scenario_count": 5,
        }
        self.assertEqual(expected_replay, {key: replay[key] for key in expected_replay})
        self.assertEqual(phase3.SCHEMA_VERSION, replay["predecessor_schema_version_required"])
        self.assertEqual(phase3.RECORD_KIND, replay["predecessor_record_kind_required"])
        self.assertEqual(phase3.PASS_RESULT, replay["predecessor_pass_result_required"])
        self.assertEqual(list(phase3.CONTROLLED_SCENARIO_IDS), replay["scenario_ids"])
        delivery = self.contract["delivery_evidence_contract"]
        expected_delivery = {
            "review_queue_sample_control_record_count": 5,
            "review_queue_sample_field_count_per_record": 17,
            "review_audit_log_sample_control_record_count": 5,
            "review_audit_log_sample_field_count_per_record": 13,
            "review_ui_flow_explanation_control_record_count": 5,
            "review_ui_flow_explanation_field_count_per_record": 13,
            "human_judgment_boundary_control_record_count": 5,
            "human_judgment_boundary_field_count_per_record": 15,
            "business_line_whitebox_confirmation_control_record_count": 5,
            "business_line_whitebox_confirmation_field_count_per_record": 14,
            "rollback_and_re_review_instruction_control_record_count": 2,
            "rollback_and_re_review_instruction_field_count_per_record": 14,
            "delivery_field_check_count": 388,
            "failure_state_count": 17,
            "chinese_feedback_count": 4,
        }
        self.assertEqual(
            expected_delivery,
            {key: delivery[key] for key in expected_delivery},
        )

    def test_delivery_projects_closed_metadata_only_control_evidence(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(phase4.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE115-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE115-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_control_shape_preserved"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(47, report["scenario_field_count"])
        self.assertEqual(235, report["scenario_field_check_count"])
        self.assertEqual(585, report["phase2_projection_field_count_total"])
        self.assertEqual(388, report["delivery_field_check_count"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertTrue(
            all(value == 0 for key, value in report.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )

    def test_delivery_group_shapes_and_chinese_ui_flow_are_exact(self) -> None:
        report = self.report
        expected = {
            "review_queue_sample_control_records": phase4.REVIEW_QUEUE_SAMPLE_FIELDS,
            "review_audit_log_sample_control_records": phase4.REVIEW_AUDIT_LOG_SAMPLE_FIELDS,
            "review_ui_flow_explanation_control_records": (
                phase4.REVIEW_UI_FLOW_EXPLANATION_FIELDS
            ),
            "human_judgment_boundary_control_records": (
                phase4.HUMAN_JUDGMENT_BOUNDARY_FIELDS
            ),
            "business_line_whitebox_confirmation_control_records": (
                phase4.BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS
            ),
            "rollback_and_re_review_instruction_control_records": (
                phase4.ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS
            ),
        }
        counts = (5, 5, 5, 5, 5, 2)
        for (name, fields), expected_count in zip(expected.items(), counts):
            with self.subTest(name=name):
                records = report[name]
                self.assertEqual(expected_count, len(records))
                for record in records:
                    self.assertEqual(set(fields), set(record))
        for record in report["review_queue_sample_control_records"]:
            with self.subTest(scenario=record["controlled_scenario_id"]):
                self.assertFalse(record["actual_review_queue_sample_rendered"])
                self.assertTrue(
                    record["review_queue_entry_ref"].startswith(phase4.P2_CONTROL_PREFIX)
                )
        for record in report["review_audit_log_sample_control_records"]:
            with self.subTest(scenario=record["controlled_scenario_id"]):
                self.assertFalse(record["actual_review_audit_log_written"])
                self.assertTrue(
                    record["review_audit_control_ref"].startswith(phase4.P2_CONTROL_PREFIX)
                )
        for record in report["review_ui_flow_explanation_control_records"]:
            with self.subTest(scenario=record["controlled_scenario_id"]):
                self.assertTrue(record["review_reason_chinese_control_message"])
                self.assertFalse(record["screenshot_or_real_ui_rendered"])
                self.assertFalse(record["actual_review_ui_rendered"])
                self.assertFalse(record["actual_user_feedback_delivered"])

    def test_manual_boundary_whitebox_and_rollback_are_exact(self) -> None:
        report = self.report
        for record in report["human_judgment_boundary_control_records"]:
            with self.subTest(scenario=record["controlled_scenario_id"]):
                self.assertTrue(record["business_line_whitebox_confirmation_required"])
                self.assertFalse(record["automatic_evidence_or_report_writeback_allowed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
        for record in report["business_line_whitebox_confirmation_control_records"]:
            with self.subTest(scenario=record["controlled_scenario_id"]):
                self.assertTrue(record["handling_code"].startswith("BUSINESS_LINE_WHITEBOX_"))
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
                    "SEPARATE_FROM_INTERNAL_EVIDENCE",
                    record["external_augmentation_source_separation_state"],
                )
                self.assertTrue(record["confirmation_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
        for record in report["rollback_and_re_review_instruction_control_records"]:
            with self.subTest(domain=record["control_domain"]):
                self.assertEqual(phase3.PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_review_ui_rollback_performed"])
                self.assertFalse(record["actual_re_review_performed"])

    def test_phase3_drift_fails_closed_without_delivery_records_or_runtime(self) -> None:
        rejected = phase4.build_review_ui_phase4_delivery_report(
            self._mutated_phase3_executor(
                lambda result: result["controlled_scenarios"][0].__setitem__(
                    "controlled_scenario_chinese_reason", "drift"
                )
            )
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(phase4.FAIL_RESULT, rejected["result"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["scenario_count"])
        self.assertEqual(0, rejected["delivery_field_check_count"])
        for name, _fields in phase4.DELIVERY_GROUPS:
            with self.subTest(name=name):
                self.assertEqual([], rejected[name])
        self.assertTrue(
            all(value == 0 for key, value in rejected.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )

    def test_phase3_runtime_drift_fails_closed_without_delivery_records(self) -> None:
        rejected = phase4.build_review_ui_phase4_delivery_report(
            self._mutated_phase3_executor(
                lambda result: result["runtime_boundary"].__setitem__(
                    "review_ui_rendered", True
                )
            )
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual("PHASE3_RUNTIME_BOUNDARY_BREACH", rejected["failure_state"])
        self.assertEqual(0, rejected["delivery_field_check_count"])
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )

    def test_scope_contract_and_final_governance_follow_phase4(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五组各五条记录、两条回滚与重新复核说明、共 `388`",
            "复核队列样例",
            "复核审计日志样例",
            "中文 UI 流程说明",
            "需人工判断的边界",
            "IDS-STAGE115-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertEqual(17, len(phase4.FAILURE_STATES))
        failure_contract = self.contract["failure_and_stop_contract"]
        self.assertEqual(17, failure_contract["failure_state_count"])
        self.assertEqual(
            list(phase4.FAILURE_STATES), failure_contract["declared_failure_states"]
        )
        if not RECEIPT.is_file():
            self.skipTest("P4 最终治理投影将在本 run 收尾时启用")
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("P4 最终治理投影将在本 run 收尾时启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase4_current = (
            "IDS-STAGE115",
            "IDS-STAGE115-P4",
            "IDS-V0_1-STAGE115-P4",
            "IDS-STAGE115-REVIEW-GATE",
        )
        future_projection = assert_legacy_or_current_projection(
            self, current, {phase4_current}, status, plan, ROADMAP
        )
        self.assertFalse(future_projection)
        self.assertEqual(
            "REVIEW_UI_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(phase4.PASS_RESULT, receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P4 复核 UI 交付控制证据已完成", acceptance_by_id["ACC-STAGE-115"])
        for acceptance_id in (
            "ACC-STAGE115-P4-01",
            "ACC-STAGE115-P4-02",
            "ACC-STAGE115-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE115-P4-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE115-P4-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
