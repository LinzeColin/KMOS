"""Stage110 报告质量评分 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE110_PHASE1_REPORT_QUALITY_SCORE_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage110_report_quality_score_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-110_报告质量评分.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE109_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "report_id_ref",
    "report_evidence_binding_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "report_snapshot_ref",
    "cited_material_update_ref",
    "source_withdrawal_ref",
    "evidence_downgrade_ref",
    "index_version_change_ref",
    "impact_scope_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "internal_evidence_coverage_rate_ref",
    "citation_completeness_rate_ref",
    "external_augmentation_ratio_ref",
    "evidence_gap_count_ref",
    "quality_metric_definition_ref",
    "quality_formula_ref",
    "quality_weight_ref",
    "quality_threshold_ref",
    "report_quality_score_ref",
    "quality_score_explanation_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_instruction_ref",
    "report_withdrawal_instruction_ref",
]

EXPECTED_QUALITY_METRIC_FIELDS = [
    "internal_evidence_coverage_rate_ref",
    "citation_completeness_rate_ref",
    "external_augmentation_ratio_ref",
    "evidence_gap_count_ref",
    "quality_metric_definition_ref",
    "quality_formula_ref",
    "quality_weight_ref",
    "quality_threshold_ref",
    "report_quality_score_ref",
    "quality_score_explanation_ref",
]


class Stage110ReportQualityScorePhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
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

    def test_identity_and_single_authority_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage110.report_quality_score.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-110", contract["stage"])
        self.assertEqual("IDS-STAGE110-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE110-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-110", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_QUALITY_SCORE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE110-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE110-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE110_TASKPACK_AND_STAGE109_REVIEWED_REPORT_"
            "IMPACT_ANALYSIS_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage109_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_IMPACT_ANALYSIS_RUNTIME_DISABLED",
            predecessor["stage109_review_result"],
        )
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_quality_control_shape_and_quality_metric_boundary_are_exact(self) -> None:
        controls = self.contract["report_quality_score_control_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(40, controls["future_control_reference_field_count"])
        self.assertTrue(controls["control_references_are_labels_only"])
        for field in (
            "future_report_evidence_binding_required",
            "critical_conclusion_requires_evidence_id_or_evidence_gap_independently",
            "evidence_grade_required_for_future_quality_control",
            "citation_source_and_page_required_in_future_pdf_report",
            "future_external_augmentation_opinion_section_required",
            "external_augmentation_retains_underlying_source_types",
            "external_augmentation_may_not_be_presented_as_internal_project_evidence",
            "external_augmentation_may_not_close_evidence_gap",
            "future_impact_triggers_include_cited_material_update_source_withdrawal_evidence_downgrade_and_index_version_change",
            "future_affected_report_and_report_status_impact_identification_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(controls[field])
        for field, value in controls.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        metrics = self.contract["quality_metric_definition_contract"]
        self.assertEqual(
            EXPECTED_QUALITY_METRIC_FIELDS,
            metrics["required_quality_metric_control_fields"],
        )
        self.assertEqual(10, metrics["required_quality_metric_control_field_count"])
        for field, value in metrics.items():
            if field.endswith("_is_future_control_reference_only") or field.endswith(
                "_require_business_line_whitebox_approval"
            ) or field.endswith("_controls"):
                with self.subTest(field=field):
                    self.assertTrue(value)
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_snapshot_quality_delivery_external_and_whitebox_controls_are_complete(self) -> None:
        snapshot = self.contract["generation_snapshot_contract"]
        self.assertEqual(
            [
                "data_snapshot_ref",
                "index_version_ref",
                "evidence_snapshot_ref",
                "model_snapshot_ref",
                "generated_at_ref",
            ],
            snapshot["required_future_snapshot_components"],
        )
        self.assertEqual(5, snapshot["required_future_snapshot_component_count"])
        self.assertTrue(snapshot["snapshot_components_are_control_references_only"])
        for field, value in snapshot.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        delivery = self.contract["report_quality_delivery_control_contract"]
        for field, value in delivery.items():
            expected = not field.startswith("actual_")
            with self.subTest(field=field):
                self.assertEqual(expected, value)

    def test_runtime_and_protected_surfaces_stay_closed(self) -> None:
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field, value in prerequisite.items():
            expected = field.endswith("_is_future_authorized_work_only")
            with self.subTest(field=field):
                self.assertEqual(expected, value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_failure_feedback_rollback_and_stage_boundary_are_explicit(self) -> None:
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(30, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID",
            "INTERNAL_EVIDENCE_COVERAGE_RATE_REFERENCE_MISSING",
            "CITATION_COMPLETENESS_RATE_REFERENCE_MISSING",
            "EXTERNAL_AUGMENTATION_RATIO_REFERENCE_MISSING",
            "EVIDENCE_GAP_COUNT_REFERENCE_MISSING",
            "QUALITY_FORMULA_REFERENCE_MISSING",
            "QUALITY_THRESHOLD_REFERENCE_MISSING",
            "ACTUAL_REPORT_QUALITY_SCORING_EXECUTED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE110_PHASE2_NOT_AUTHORIZED",
            "STAGE111_STARTED_WITHOUT_AUTHORIZATION",
        ):
            with self.subTest(failure_state=failure_state):
                self.assertIn(failure_state, failures["declared_failure_states"])
        for field, value in failures.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        feedback = self.contract["chinese_feedback_contract"]
        self.assertEqual(4, feedback["feedback_count"])
        self.assertEqual(4, len(feedback["feedbacks"]))
        self.assertFalse(feedback["actual_user_feedback_emitted"])
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage109_review_evidence_declared",
            "stage110_started",
            "stage110_entry_authorized",
            "phase1_started",
            "phase1_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage111_started",
            "formal_global_upload_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_IMPACT_ANALYSIS_RUNTIME_DISABLED",
            self.contract["rollback_contract"]["fallback_result"],
        )

    def test_current_governance_receipt_and_event_are_exact(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P1 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        predecessor_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-REVIEW",
            "IDS-V0_1-STAGE109-REVIEW",
            "IDS-STAGE110-P1-GATE",
        )
        phase1_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P1",
            "IDS-V0_1-STAGE110-P1",
            "IDS-STAGE110-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P2",
            "IDS-V0_1-STAGE110-P2",
            "IDS-STAGE110-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P3",
            "IDS-V0_1-STAGE110-P3",
            "IDS-STAGE110-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P4",
            "IDS-V0_1-STAGE110-P4",
            "IDS-STAGE110-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-REVIEW",
            "IDS-V0_1-STAGE110-REVIEW",
            "IDS-STAGE111-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {predecessor_current, phase1_current}, status, plan, ROADMAP
        )
        self.assertTrue(
            is_current_projection or current in {predecessor_current, phase1_current}
        )
        if current in {phase2_current, phase3_current, phase4_current, review_current}:
            self.assertTrue(is_current_projection)
            return
        self.assertFalse(is_current_projection)
        self.assertEqual(phase1_current, current)
        self.assertEqual(
            "REPORT_QUALITY_SCORE_CONTRACT_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_QUALITY_SCORE_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE110-P1-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE110-P2-GATE", receipt["next_gate"])
        self.assertEqual(40, receipt["control_shape"]["future_control_reference_field_count"])
        self.assertEqual(10, receipt["control_shape"]["quality_metric_control_field_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual(7, validation["focused_contract_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE110-P1-01",
            "ACC-STAGE110-P1-02",
            "ACC-STAGE110-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE110-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE110-P1-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
