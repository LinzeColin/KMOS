"""Stage112 P4 报告导出审计 metadata-only 交付控制验证。"""

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
SCOPE = BASE / "STAGE112_PHASE4_REPORT_EXPORT_AUDIT_DELIVERY.md"
CONTRACT = BASE / "index_version_schema" / "stage112_report_export_audit_delivery_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-112_报告导出审计.md"
)
PHASE1_SCOPE = BASE / "STAGE112_PHASE1_REPORT_EXPORT_AUDIT_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage112_report_export_audit_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE112_PHASE2_REPORT_EXPORT_AUDIT_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage112_report_export_audit_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE112_PHASE3_REPORT_EXPORT_AUDIT_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_controlled_scenarios_contract.json"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p3-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE111_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage112ReportExportAuditPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage112_report_export_audit_delivery"
        )
        cls.phase3 = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage112_report_export_audit_controlled_scenarios"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_export_audit_phase4_delivery_report()

    def _mutated_phase3_executor(self, mutator):
        def executor():
            result = copy.deepcopy(self.phase3.build_report_export_audit_phase3_report())
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
            "ids.stage112.report_export_audit.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-112", contract["stage"])
        self.assertEqual("IDS-STAGE112-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE112-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-112", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_EXPORT_AUDIT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE112-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE112-REVIEW-GATE", contract["next_gate"])
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
            "stage111_review_evidence_declared",
            "stage112_phase1_completed",
            "stage112_phase2_completed",
            "stage112_phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage112_review_started",
            "stage113_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(34, replay["phase2_input_field_count"])
        self.assertEqual(32, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(100, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(500, replay["phase2_projection_field_count_total"])
        self.assertEqual(5, replay["scenario_count"])
        self.assertEqual(53, replay["scenario_field_count"])
        self.assertEqual(265, replay["scenario_field_check_count"])
        self.assertEqual(5, replay["control_view_count"])
        delivery = self.contract["delivery_evidence_contract"]
        expected = {
            "report_sample_control_record_count": 5,
            "report_sample_field_count_per_record": 17,
            "report_snapshot_control_record_count": 5,
            "report_snapshot_field_count_per_record": 13,
            "report_quality_score_control_record_count": 5,
            "report_quality_score_field_count_per_record": 13,
            "report_impact_analysis_control_record_count": 5,
            "report_impact_analysis_field_count_per_record": 15,
            "report_template_and_whitebox_confirmation_control_record_count": 5,
            "report_template_and_whitebox_confirmation_field_count_per_record": 14,
            "regeneration_and_withdrawal_control_record_count": 2,
            "regeneration_and_withdrawal_field_count_per_record": 14,
            "delivery_field_check_count": 388,
            "failure_state_count": 17,
            "chinese_feedback_count": 4,
        }
        self.assertEqual(expected, {key: delivery[key] for key in expected})

    def test_delivery_projects_closed_metadata_only_control_evidence(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE112-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE112-REVIEW-GATE", report["next_gate"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(53, report["scenario_field_count"])
        self.assertEqual(265, report["scenario_field_check_count"])
        self.assertEqual(500, report["phase2_projection_field_count_total"])
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
            "report_sample_control_records": self.module.REPORT_SAMPLE_FIELDS,
            "report_snapshot_control_records": self.module.REPORT_SNAPSHOT_FIELDS,
            "report_quality_score_control_records": self.module.REPORT_QUALITY_SCORE_FIELDS,
            "report_impact_analysis_control_records": self.module.REPORT_IMPACT_ANALYSIS_FIELDS,
            "report_template_and_whitebox_confirmation_control_records": (
                self.module.REPORT_TEMPLATE_AND_WHITEBOX_CONFIRMATION_FIELDS
            ),
            "regeneration_and_withdrawal_control_records": (
                self.module.REGENERATION_AND_WITHDRAWAL_FIELDS
            ),
        }
        counts = (5, 5, 5, 5, 5, 2)
        for (name, fields), expected_count in zip(expected.items(), counts):
            with self.subTest(name=name):
                records = report[name]
                self.assertEqual(expected_count, len(records))
                for record in records:
                    self.assertEqual(set(fields), set(record))

        for record in report["report_sample_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(
                    bool(record["evidence_id_ref"]) ^ bool(record["evidence_gap_ref"])
                )
                self.assertEqual(
                    "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
                    record["evidence_binding_integrity_state"],
                )
                self.assertFalse(record["actual_report_sample_rendered"])

        impact_by_scenario = {
            record["scenario_id"]: record
            for record in report["report_impact_analysis_control_records"]
        }
        for scenario_id, field in (
            (
                "source_withdrawal_evidence_gap_report_status_audit_control",
                "source_withdrawal_report_status_impact_state",
            ),
            (
                "evidence_downgrade_evidence_id_report_status_quality_audit_control",
                "evidence_downgrade_report_status_impact_state",
            ),
            (
                "index_version_change_evidence_gap_report_snapshot_audit_control",
                "index_version_change_report_status_impact_state",
            ),
        ):
            with self.subTest(scenario=scenario_id, field=field):
                self.assertIn("REQUIRED", impact_by_scenario[scenario_id][field])
        for record in report[
            "report_template_and_whitebox_confirmation_control_records"
        ]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertIn(
                    "SEPARATE_FROM_INTERNAL_EVIDENCE",
                    record["external_augmentation_source_separation_state"],
                )
                self.assertTrue(record["business_line_whitebox_confirmation_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
        for record in report["regeneration_and_withdrawal_control_records"]:
            with self.subTest(instruction=record["instruction_id"]):
                self.assertEqual(self.phase3.PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_report_regeneration_performed"])
                self.assertFalse(record["actual_report_withdrawal_performed"])

    def test_predecessor_drift_fails_closed(self) -> None:
        shape_mismatch = self.module.build_report_export_audit_phase4_delivery_report(
            phase3_executor=lambda: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_binding(result):
            result["scenario_results"][0]["evidence_id_ref"] = (
                ":control:stage112-p2:unexpected-evidence-id:reference-only"
            )

        binding_drift = self.module.build_report_export_audit_phase4_delivery_report(
            self._mutated_phase3_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", binding_drift["failure_state"])

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_export_audit_phase4_delivery_report(
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
            "五组各 5 条控制记录、两条生命周期说明、共 388 个 metadata-only 检查点",
            "actor`、`time`、`report_id`、`evidence_snapshot",
            "资料撤回、证据降级和索引版本变化",
            "不能成为内部项目依据",
            "IDS-STAGE112-REVIEW-GATE",
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
            "IDS-STAGE112",
            "IDS-STAGE112-P1",
            "IDS-V0_1-STAGE112-P1",
            "IDS-STAGE112-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P2",
            "IDS-V0_1-STAGE112-P2",
            "IDS-STAGE112-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P3",
            "IDS-V0_1-STAGE112-P3",
            "IDS-STAGE112-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P4",
            "IDS-V0_1-STAGE112-P4",
            "IDS-STAGE112-REVIEW-GATE",
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
            "REPORT_EXPORT_AUDIT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE112-P4-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE112-REVIEW-GATE", receipt["next_gate"])
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
            "P4 报告导出审计交付控制证据已完成",
            acceptance_by_id["ACC-STAGE-112"],
        )
        for acceptance_id in (
            "ACC-STAGE112-P4-01",
            "ACC-STAGE112-P4-02",
            "ACC-STAGE112-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE112-P4-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE112-P4-20260827-001", event_ids)

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
