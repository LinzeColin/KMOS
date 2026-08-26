"""Stage112 报告导出审计 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE112_PHASE1_REPORT_EXPORT_AUDIT_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage112_report_export_audit_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-112_报告导出审计.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE111_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "report_export_audit_record_ref",
    "actor_ref",
    "export_time_ref",
    "report_id_ref",
    "evidence_snapshot_ref",
    "report_evidence_binding_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "impact_analysis_ref",
    "affected_report_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "export_destination_control_ref",
    "export_format_control_ref",
    "report_export_audit_state_ref",
    "report_export_audit_failure_reason_ref",
    "report_export_audit_retention_ref",
    "report_regeneration_reference_ref",
    "report_withdrawal_reference_ref",
]


class Stage112ReportExportAuditPhase1Tests(unittest.TestCase):
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

    def test_identity_authority_and_predecessor_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage112.report_export_audit.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-112", contract["stage"])
        self.assertEqual("IDS-STAGE112-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE112-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-112", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE112-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE112-P2-GATE", contract["next_gate"])
        self.assertEqual(
            "REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE112_TASKPACK_AND_STAGE111_REVIEWED_REPORT_REGENERATION_"
            "QUEUE_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
            "control_artifacts_are_engineering_context_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage111_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_REGENERATION_QUEUE_RUNTIME_DISABLED",
            predecessor["stage111_review_result"],
        )
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_audit_control_shape_and_taskpack_semantics_are_exact(self) -> None:
        controls = self.contract["report_export_audit_control_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(32, controls["future_control_reference_field_count"])
        self.assertTrue(controls["control_references_are_labels_only"])
        for field in (
            "future_actor_reference_required",
            "future_export_time_reference_required",
            "future_report_id_reference_required",
            "future_evidence_snapshot_reference_required",
            "future_report_evidence_binding_required",
            "critical_conclusion_requires_evidence_id_or_evidence_gap_independently",
            "future_pdf_must_display_citation_source",
            "future_external_augmentation_section_required",
            "external_augmentation_retains_underlying_source_type",
            "future_human_confirmation_item_required",
            "business_line_whitebox_confirmation_required",
            "future_report_snapshot_required",
            "future_impact_analysis_required",
            "future_report_quality_score_control_required",
            "future_export_destination_and_format_control_required",
            "future_export_audit_state_failure_reason_and_retention_required",
            "future_report_regeneration_and_withdrawal_references_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(controls[field])
        for field, value in controls.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_snapshot_delivery_and_whitebox_controls_are_complete(self) -> None:
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
        self.assertTrue(snapshot["report_snapshot_is_separate_control_reference"])
        for field, value in snapshot.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        delivery = self.contract["report_delivery_and_whitebox_control_contract"]
        for field, value in delivery.items():
            expected = not field.startswith("actual_")
            with self.subTest(field=field):
                self.assertEqual(expected, value)

    def test_runtime_and_protected_surfaces_stay_closed(self) -> None:
        prerequisites = self.contract["future_runtime_prerequisite_contract"]
        self.assertTrue(all(prerequisites.values()))
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value == 0 for value in self.contract["runtime_counts"].values())
        )

    def test_failure_feedback_rollback_and_stage_boundary_are_explicit(self) -> None:
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(20, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "PREDECESSOR_STAGE111_REVIEW_CONTROL_MISSING",
            "REPORT_EXPORT_AUDIT_ACTOR_REFERENCE_MISSING",
            "REPORT_EXPORT_AUDIT_EVIDENCE_SNAPSHOT_REFERENCE_MISSING",
            "PDF_CITATION_SOURCE_CONTROL_MISSING",
            "ACTUAL_EXPORT_AUDIT_OR_DATABASE_WRITE_EXECUTED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE112_PHASE2_NOT_AUTHORIZED",
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
            "stage111_review_evidence_declared",
            "stage112_started",
            "stage112_entry_authorized",
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
            "stage113_started",
            "formal_global_upload_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_REGENERATION_QUEUE_RUNTIME_DISABLED",
            self.contract["rollback_contract"]["fallback_result"],
        )

    def test_current_governance_receipt_and_event_are_exact(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P1 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        predecessor_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-REVIEW",
            "IDS-V0_1-STAGE111-REVIEW",
            "IDS-STAGE112-P1-GATE",
        )
        phase1_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P1",
            "IDS-V0_1-STAGE112-P1",
            "IDS-STAGE112-P2-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {predecessor_current, phase1_current}, status, plan, ROADMAP
        )
        self.assertTrue(
            is_current_projection or current in {predecessor_current, phase1_current}
        )
        if is_current_projection:
            return
        self.assertEqual(phase1_current, current)
        self.assertEqual(
            "REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("KM_IDSystem", receipt["project_id"])
        self.assertEqual("IDS-STAGE112", receipt["stage"])
        self.assertEqual("IDS-STAGE112-P1", receipt["phase"])
        self.assertEqual("IDS-V0_1-STAGE112-P1", receipt["task_id"])
        self.assertIn("ACC-STAGE112-P1-01", receipt["acceptance_ids"])
        self.assertEqual("IDS-STAGE112-P1-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE112-P2-GATE", receipt["next_gate"])
        self.assertEqual(32, receipt["control_shape"]["future_control_reference_field_count"])
        self.assertEqual(5, receipt["control_shape"]["snapshot_component_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(7, validation["focused_contract_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE112-P1-01",
            "ACC-STAGE112-P1-02",
            "ACC-STAGE112-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE112-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE112-P1-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
