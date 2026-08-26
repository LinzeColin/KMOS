"""Stage113 P4 复核队列 Schema metadata-only 交付控制验证。"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE113_PHASE4_REVIEW_QUEUE_SCHEMA_DELIVERY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_delivery_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-113_复核队列Schema.md"
)
PHASE1_SCOPE = BASE / "STAGE113_PHASE1_REVIEW_QUEUE_SCHEMA_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage113_review_queue_schema_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE113_PHASE2_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE113_PHASE3_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_controlled_scenarios_contract.json"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p3-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE112_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage113ReviewQueueSchemaPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage113_review_queue_schema_delivery"
        )
        cls.phase3 = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage113_review_queue_schema_controlled_scenarios"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_review_queue_schema_phase4_delivery_report()

    def _mutated_phase3_executor(self, mutator):
        def executor():
            result = copy.deepcopy(self.phase3.build_review_queue_schema_phase3_report())
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
            RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage113.review_queue_schema.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-113", contract["stage"])
        self.assertEqual("IDS-STAGE113-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE113-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-113", contract["acceptance_id"])
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE113-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE113-REVIEW-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        replay = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(self.phase3.SCHEMA_VERSION, replay["predecessor_schema_version_required"])
        self.assertEqual(self.phase3.RECORD_KIND, replay["predecessor_record_kind_required"])
        self.assertEqual(self.phase3.PASS_RESULT, replay["predecessor_pass_result_required"])
        boundary = contract["stage_boundary"]
        for field in (
            "stage112_review_evidence_declared",
            "stage113_phase1_completed",
            "stage113_phase2_completed",
            "stage113_phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage113_review_started",
            "stage114_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        expected_replay = {
            "phase2_control_request_count": 5,
            "phase2_input_field_count": 32,
            "phase2_phase1_reference_field_count": 29,
            "phase2_projection_group_count": 4,
            "phase2_projection_field_count_per_request": 101,
            "phase2_projection_field_count_total": 505,
            "scenario_count": 5,
            "scenario_field_count": 52,
            "scenario_field_check_count": 260,
            "control_view_count": 5,
            "business_line_whitebox_handling_count": 5,
            "whitebox_confirmation_required_scenario_count": 5,
        }
        self.assertEqual(expected_replay, {key: replay[key] for key in expected_replay})
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
            expected_delivery, {key: delivery[key] for key in expected_delivery}
        )

    def test_delivery_projects_closed_metadata_only_control_evidence(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE113-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE113-REVIEW-GATE", report["next_gate"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(52, report["scenario_field_count"])
        self.assertEqual(260, report["scenario_field_check_count"])
        self.assertEqual(505, report["phase2_projection_field_count_total"])
        self.assertEqual(388, report["delivery_field_check_count"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertTrue(
            all(value == 0 for key, value in report.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )

    def test_delivery_group_shapes_and_taskpack_controls_are_exact(self) -> None:
        report = self.report
        expected = {
            "review_queue_sample_control_records": self.module.REVIEW_QUEUE_SAMPLE_FIELDS,
            "review_audit_log_sample_control_records": self.module.REVIEW_AUDIT_LOG_SAMPLE_FIELDS,
            "review_ui_flow_explanation_control_records": self.module.REVIEW_UI_FLOW_EXPLANATION_FIELDS,
            "human_judgment_boundary_control_records": self.module.HUMAN_JUDGMENT_BOUNDARY_FIELDS,
            "business_line_whitebox_confirmation_control_records": (
                self.module.BUSINESS_LINE_WHITEBOX_CONFIRMATION_FIELDS
            ),
            "rollback_and_re_review_instruction_control_records": (
                self.module.ROLLBACK_AND_RE_REVIEW_INSTRUCTION_FIELDS
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
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(bool(record["evidence_id_ref"]) ^ bool(record["evidence_gap_ref"]))
                self.assertFalse(record["actual_review_queue_sample_rendered"])
        for record in report["review_audit_log_sample_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertFalse(record["actual_review_audit_log_written"])
                self.assertTrue(record["review_actor_ref"].startswith(self.module.P2_CONTROL_PREFIX))
        for record in report["review_ui_flow_explanation_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["review_reason_chinese_control_message"])
                self.assertFalse(record["screenshot_or_real_ui_rendered"])
                self.assertFalse(record["actual_review_ui_rendered"])
        for record in report["human_judgment_boundary_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["business_line_whitebox_confirmation_required"])
                self.assertFalse(record["automatic_evidence_or_report_writeback_allowed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
        for record in report["business_line_whitebox_confirmation_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertIn(
                    "SEPARATE_FROM_INTERNAL_EVIDENCE",
                    record["external_augmentation_source_separation_state"],
                )
                self.assertTrue(record["confirmation_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
                self.assertFalse(record["actual_human_confirmation_execution_performed"])
        for record in report["rollback_and_re_review_instruction_control_records"]:
            with self.subTest(instruction=record["instruction_id"]):
                self.assertEqual(self.phase3.PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_review_queue_rollback_performed"])
                self.assertFalse(record["actual_re_review_performed"])

    def test_predecessor_drift_fails_closed(self) -> None:
        shape_mismatch = self.module.build_review_queue_schema_phase4_delivery_report(
            phase3_executor=lambda: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_binding(result):
            result["scenario_results"][0]["review_actor_ref"] = "drifted"

        binding_drift = self.module.build_review_queue_schema_phase4_delivery_report(
            self._mutated_phase3_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", binding_drift["failure_state"])

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_review_queue_schema_phase4_delivery_report(
            self._mutated_phase3_executor(break_runtime_boundary)
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual("PHASE3_RUNTIME_BOUNDARY_BREACH", runtime_drift["failure_state"])

        for failed_report in (shape_mismatch, binding_drift, runtime_drift):
            with self.subTest(failure=failed_report["failure_state"]):
                self.assertEqual(0, failed_report["scenario_count"])
                self.assertEqual(0, failed_report["delivery_field_check_count"])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed_report.items()
                        if key.startswith("actual_")
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in failed_report["runtime_boundary"].values()
                    )
                )

    def test_runtime_receipt_and_current_governance_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五组各 5 条控制记录、两条回滚与重新复核说明、共",
            "复核队列样例",
            "复核审计日志样例",
            "中文复核 UI 流程说明",
            "需人工判断的边界",
            "IDS-STAGE113-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("P4 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE113",
            "IDS-STAGE113-P1",
            "IDS-V0_1-STAGE113-P1",
            "IDS-STAGE113-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE113",
            "IDS-STAGE113-P2",
            "IDS-V0_1-STAGE113-P2",
            "IDS-STAGE113-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE113",
            "IDS-STAGE113-P3",
            "IDS-V0_1-STAGE113-P3",
            "IDS-STAGE113-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE113",
            "IDS-STAGE113-P4",
            "IDS-V0_1-STAGE113-P4",
            "IDS-STAGE113-REVIEW-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current, phase3_current, phase4_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertTrue(is_current_projection or current == phase4_current)
        if is_current_projection:
            return
        self.assertEqual(phase4_current, current)
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE113-P4-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE113-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(388, receipt["delivery_evidence"]["delivery_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(8, validation["focused_delivery_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P4 复核队列 Schema 交付控制证据已完成",
            acceptance_by_id["ACC-STAGE-113"],
        )
        for acceptance_id in (
            "ACC-STAGE113-P4-01",
            "ACC-STAGE113-P4-02",
            "ACC-STAGE113-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE113-P4-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE113-P4-20260827-001", event_ids)

    def test_contract_failure_and_feedback_shape_is_exact(self) -> None:
        self.assertEqual(
            list(self.module.FAILURE_STATES),
            self.contract["failure_and_stop_contract"]["failure_states"],
        )
        self.assertEqual(17, len(self.module.FAILURE_STATES))
        self.assertEqual(
            list(self.module.OPERATOR_FEEDBACK),
            self.contract["operator_feedback"]["messages"],
        )
        self.assertEqual(4, len(self.report["operator_feedback"]))


if __name__ == "__main__":
    unittest.main()
