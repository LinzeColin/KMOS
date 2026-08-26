"""Stage108 P4 报告快照 metadata-only 交付证据的聚焦验证。"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-108_报告快照.md"
)
SCOPE = BASE / "STAGE108_PHASE4_REPORT_SNAPSHOT_DELIVERY.md"
CONTRACT = BASE / "index_version_schema" / "stage108_report_snapshot_delivery_contract.json"
MODULE = BASE / "index_version_schema" / "stage108_report_snapshot_delivery.py"
PHASE3_SCOPE = BASE / "STAGE108_PHASE3_REPORT_SNAPSHOT_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage108_report_snapshot_controlled_scenarios_contract.json"
)
PHASE3_MODULE = BASE / "index_version_schema" / "stage108_report_snapshot_controlled_scenarios.py"
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage108-p3-local.json"
PHASE2_SCOPE = BASE / "STAGE108_PHASE2_REPORT_SNAPSHOT_CONTROL_SLICE.md"
PHASE2_CONTRACT = BASE / "index_version_schema" / "stage108_report_snapshot_control_slice_contract.json"
PHASE1_SCOPE = BASE / "STAGE108_PHASE1_REPORT_SNAPSHOT_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage108_report_snapshot_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE107_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage107_human_confirmation_items_stage_review_contract.json"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage108-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage108_report_snapshot_delivery", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage108 P4 报告快照交付模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage108ReportSnapshotPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_snapshot_phase4_delivery_report()

    def _mutated_phase3_executor(self, mutation):
        def executor():
            phase3 = self.module._load_phase3_module()
            report = copy.deepcopy(phase3.build_report_snapshot_phase3_report())
            mutation(report)
            return report

        return executor

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            TASKPACK,
            SCOPE,
            CONTRACT,
            MODULE,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE3_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("ids.stage108.report_snapshot.phase4.delivery.v1", contract["schema_version"])
        self.assertEqual("STAGE-108", contract["stage"])
        self.assertEqual("IDS-STAGE108-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE108-P4", contract["task_id"])
        self.assertEqual("IDS-STAGE108-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE108-REVIEW-GATE", contract["next_gate"])
        self.assertEqual("REPORT_SNAPSHOT_DELIVERY_EVIDENCE_RUNTIME_DISABLED", contract["contract_state"])
        authority = contract["source_authority"]
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        boundary = contract["stage_boundary"]
        for field in (
            "stage107_review_evidence_declared",
            "stage108_started",
            "stage108_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in ("stage108_review_started", "stage109_started", "github_upload_allowed", "push_allowed"):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_shape_are_exact(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(26, replay["phase2_input_field_count"])
        self.assertEqual(24, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(82, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(410, replay["phase2_projection_field_count_total"])
        self.assertEqual(5, replay["scenario_count"])
        self.assertEqual(39, replay["scenario_field_count"])
        self.assertEqual(195, replay["scenario_field_check_count"])
        self.assertEqual(5, replay["control_view_count"])
        self.assertEqual(5, replay["human_handling_count"])
        self.assertEqual(2, replay["whitebox_confirmation_required_scenario_count"])
        self.assertFalse(replay["actual_phase3_runtime_execution_allowed"])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertEqual(5, delivery["report_sample_control_record_count"])
        self.assertEqual(5, delivery["report_snapshot_control_record_count"])
        self.assertEqual(5, delivery["report_quality_score_control_record_count"])
        self.assertEqual(5, delivery["report_impact_analysis_control_record_count"])
        self.assertEqual(5, delivery["report_template_and_whitebox_confirmation_control_record_count"])
        self.assertEqual(2, delivery["regeneration_and_withdrawal_control_record_count"])
        self.assertEqual(388, delivery["delivery_field_check_count"])
        self.assertEqual(17, delivery["failure_state_count"])
        self.assertEqual(4, delivery["chinese_feedback_count"])

    def test_report_projects_closed_delivery_control_records(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE108-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE108-REVIEW-GATE", report["next_gate"])
        for field in (
            "phase3_controlled_scenarios_replayed_in_memory_only",
            "phase3_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(388, report["delivery_field_check_count"])
        self.assertEqual(17, report["failure_state_count"])
        for name, fields in self.module.DELIVERY_GROUPS:
            with self.subTest(group=name):
                records = report[name]
                expected_count = 2 if name == "regeneration_and_withdrawal_control_records" else 5
                self.assertEqual(expected_count, len(records))
                for record in records:
                    self.assertEqual(set(fields), set(record))
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])

    def test_taskpack_controls_and_whitebox_requirements_are_preserved(self) -> None:
        for sample in self.report["report_sample_control_records"]:
            with self.subTest(scenario=sample["scenario_id"]):
                self.assertNotEqual(sample["evidence_id_ref"] is None, sample["evidence_gap_ref"] is None)
                self.assertEqual("CONTROL_REPORT_SAMPLE_REFERENCE_ONLY_NOT_RENDERED", sample["report_sample_state"])
                self.assertFalse(sample["automatic_final_conclusion_allowed"])
                self.assertFalse(sample["actual_report_sample_rendered"])
        lifecycle = self.report["report_impact_analysis_control_records"][-1]
        self.assertEqual("CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED", lifecycle["report_status_impact_state"])
        self.assertEqual("CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS", lifecycle["evidence_grade_downgrade_state"])
        self.assertEqual("CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS", lifecycle["index_version_change_state"])
        self.assertEqual("CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS", lifecycle["material_withdrawal_state"])
        for record in self.report["report_template_and_whitebox_confirmation_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["business_line_whitebox_confirmation_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
                self.assertEqual("CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED", record["final_conclusion_state"])
        instructions = self.report["regeneration_and_withdrawal_control_records"]
        self.assertEqual({"REPORT_REGENERATION", "REPORT_WITHDRAWAL"}, {item["control_domain"] for item in instructions})
        for item in instructions:
            self.assertEqual(self.module.P3_PASS_RESULT, item["rollback_target_result"])
            self.assertTrue(item["business_line_whitebox_confirmation_required"])
            self.assertTrue(item["human_confirmation_required"])
            self.assertTrue(item["versioned_basis_required"])
            self.assertTrue(item["verifiable_rollback_target_required"])
        self.assertEqual(4, len(self.report["operator_feedback"]))

    def test_phase3_drift_fails_closed(self) -> None:
        invalid = self.module.build_report_snapshot_phase4_delivery_report(phase3_executor=lambda: None)

        def break_runtime_boundary(report):
            report["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_snapshot_phase4_delivery_report(
            self._mutated_phase3_executor(break_runtime_boundary)
        )

        def break_binding(report):
            report["scenario_results"][0]["evidence_gap_ref"] = ":control:stage108-p2:unexpected:reference-only"

        binding_drift = self.module.build_report_snapshot_phase4_delivery_report(
            self._mutated_phase3_executor(break_binding)
        )
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", invalid["failure_state"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", runtime_drift["failure_state"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", binding_drift["failure_state"])
        for failed in (invalid, runtime_drift, binding_drift):
            with self.subTest(failure=failed["failure_state"]):
                self.assertFalse(failed["valid"])
                self.assertEqual(self.module.FAIL_RESULT, failed["result"])
                self.assertEqual("IDS-STAGE108-P4-GATE", failed["next_gate"])
                self.assertEqual(0, failed["delivery_field_check_count"])
                self.assertTrue(all(value == 0 for key, value in failed.items() if key.startswith("actual_")))
                self.assertTrue(all(value is False for value in failed["runtime_boundary"].values()))

    def test_runtime_boundary_is_closed(self) -> None:
        self.assertTrue(all(value == 0 for key, value in self.report.items() if key.startswith("actual_")))
        self.assertTrue(all(value is False for value in self.report["runtime_boundary"].values()))
        for record in self.report["report_snapshot_control_records"]:
            self.assertFalse(record["actual_report_snapshot_persisted"])
            self.assertFalse(record["actual_report_or_pdf_accessed"])
        for record in self.report["report_quality_score_control_records"]:
            self.assertFalse(record["actual_report_quality_score_calculated"])
            self.assertFalse(record["actual_report_quality_score_persisted"])

    def test_current_governance_and_final_receipt_are_exact_when_phase4_is_current(self) -> None:
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = ("IDS-STAGE108", "IDS-STAGE108-P1", "IDS-V0_1-STAGE108-P1", "IDS-STAGE108-P2-GATE")
        phase2_current = ("IDS-STAGE108", "IDS-STAGE108-P2", "IDS-V0_1-STAGE108-P2", "IDS-STAGE108-P3-GATE")
        phase3_current = ("IDS-STAGE108", "IDS-STAGE108-P3", "IDS-V0_1-STAGE108-P3", "IDS-STAGE108-P4-GATE")
        phase4_current = ("IDS-STAGE108", "IDS-STAGE108-P4", "IDS-V0_1-STAGE108-P4", "IDS-STAGE108-REVIEW-GATE")
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {phase1_current, phase2_current, phase3_current}, status, plan, ROADMAP
        )
        if current != phase4_current:
            self.assertTrue(is_current_projection or current in {phase1_current, phase2_current, phase3_current})
            return
        self.assertTrue(is_current_projection)
        self.assertEqual(status["task"], plan["task"])
        self.assertEqual("REPORT_SNAPSHOT_DELIVERY_EVIDENCE_RUNTIME_DISABLED", status["evidence_status"])
        self.assertIn("IDS-STAGE108-REVIEW-GATE", plan["stop_condition"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE108-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(388, receipt["delivery_evidence"]["delivery_field_check_count"])
        validation = receipt["validation"]["final_validation"]
        self.assertEqual(8, validation["focused_delivery_test_count"])
        self.assertEqual(31, validation["stage108_phase1_to_phase4_compatibility_test_count"])
        self.assertEqual(960, validation["historical_whitebox_chain_test_count"])
        for field in (
            "stage005_governance_valid",
            "batch041_050_review_valid",
            "batch051_060_review_valid",
            "document_budget_valid",
            "blocker_stop_valid",
            "dual_plane_valid",
            "stage108_required_acceptance_validation_passed",
            "all_executed_validation_passed",
        ):
            with self.subTest(validation_field=field):
                self.assertTrue(validation[field])
        self.assertEqual(7, validation["human_rendered_file_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P4 报告快照交付控制证据已完成", acceptance_by_id["ACC-STAGE-108"])
        for acceptance_id in ("ACC-STAGE108-P4-01", "ACC-STAGE108-P4-02", "ACC-STAGE108-P4-03"):
            self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE108-P4-04"])
        event_ids = {json.loads(line)["event_id"] for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()}
        self.assertIn("EVT-IDS-V0_1-STAGE108-P4-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
