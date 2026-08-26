"""Stage108 报告快照 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE108_PHASE1_REPORT_SNAPSHOT_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage108_report_snapshot_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-108_报告快照.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE107_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage107_human_confirmation_items_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage107-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage108-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "report_id_ref",
    "report_evidence_binding_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "report_snapshot_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "regeneration_and_withdrawal_instruction_ref",
]


class Stage108ReportSnapshotPhase1Tests(unittest.TestCase):
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
        self.assertEqual("ids.stage108.report_snapshot.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-108", contract["stage"])
        self.assertEqual("IDS-STAGE108-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE108-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-108", contract["acceptance_id"])
        self.assertEqual("REPORT_SNAPSHOT_CONTRACT_RUNTIME_DISABLED", contract["contract_state"])
        self.assertEqual("IDS-STAGE108-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE108-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE108_TASKPACK_AND_STAGE107_REVIEWED_HUMAN_CONFIRMATION_ITEMS_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
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
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage107_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_HUMAN_CONFIRMATION_ITEMS_RUNTIME_DISABLED",
            predecessor["stage107_review_result"],
        )
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_report_snapshot_shape_and_evidence_controls_are_exact(self) -> None:
        controls = self.contract["report_snapshot_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(24, controls["future_control_reference_field_count"])
        self.assertTrue(controls["control_references_are_labels_only"])
        for field in (
            "future_report_evidence_binding_required",
            "future_external_augmentation_opinion_section_required",
            "future_human_confirmation_reference_required",
            "critical_conclusion_requires_evidence_id_or_evidence_gap_independently",
            "evidence_grade_required_for_future_report_binding",
            "citation_source_and_page_required_in_future_pdf_report",
            "external_augmentation_retains_underlying_source_types",
            "external_augmentation_may_not_be_presented_as_internal_project_evidence",
            "external_augmentation_may_not_close_evidence_gap",
        ):
            with self.subTest(field=field):
                self.assertTrue(controls[field])
        for field, value in controls.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_snapshot_and_report_delivery_controls_are_complete(self) -> None:
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
        report_delivery = self.contract["report_delivery_control_contract"]
        for field, value in report_delivery.items():
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
        self.assertEqual(23, failures["failure_state_count"])
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for failure_state in (
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID",
            "PDF_CITATION_SOURCE_REQUIREMENT_MISSING",
            "EXTERNAL_AUGMENTATION_PRESENTED_AS_INTERNAL_EVIDENCE",
            "ACTUAL_MODEL_AGENT_OVH_OR_PRODUCTION_EXECUTED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE108_PHASE2_NOT_AUTHORIZED",
            "STAGE109_STARTED_WITHOUT_AUTHORIZATION",
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
            "stage107_review_evidence_declared",
            "stage108_started",
            "stage108_entry_authorized",
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
            "stage109_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertEqual(
            "PASS_REVIEWED_HUMAN_CONFIRMATION_ITEMS_RUNTIME_DISABLED",
            self.contract["rollback_contract"]["fallback_result"],
        )

    def test_current_governance_accepts_predecessor_or_current_projection(self) -> None:
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        predecessor_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-REVIEW",
            "IDS-V0_1-STAGE107-REVIEW",
            "IDS-STAGE108-P1-GATE",
        )
        phase1_current = (
            "IDS-STAGE108",
            "IDS-STAGE108-P1",
            "IDS-V0_1-STAGE108-P1",
            "IDS-STAGE108-P2-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {predecessor_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current == predecessor_current:
            self.assertFalse(is_current_projection)
            return
        self.assertTrue(is_current_projection)
        if current != phase1_current:
            return
        self.assertEqual("REPORT_SNAPSHOT_CONTRACT_RUNTIME_DISABLED", status["evidence_status"])
        self.assertIn("IDS-STAGE108-P2-GATE", plan["stop_condition"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual("PASS_REPORT_SNAPSHOT_CONTRACT_RUNTIME_DISABLED", receipt["result"])
        self.assertEqual("IDS-STAGE108-P2-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["validation"]
        self.assertTrue(validation["final_validation_recorded"])
        self.assertEqual(
            {
                "focused_test_count": 7,
                "stage107_phase1_to_review_compatibility_test_count": 38,
                "historical_whitebox_chain_test_count": 936,
                "stage005_governance_valid": True,
                "batch041_050_review_valid": True,
                "batch051_060_review_valid": True,
                "human_rendered_file_count": 7,
                "document_budget_valid": True,
                "blocker_stop_valid": True,
                "dual_plane_valid": True,
                "lean_governance_semantic_check": "NOT_AVAILABLE",
                "stage108_required_acceptance_validation_passed": True,
                "all_executed_validation_passed": True,
            },
            {
                key: validation["final_validation"][key]
                for key in (
                    "focused_test_count",
                    "stage107_phase1_to_review_compatibility_test_count",
                    "historical_whitebox_chain_test_count",
                    "stage005_governance_valid",
                    "batch041_050_review_valid",
                    "batch051_060_review_valid",
                    "human_rendered_file_count",
                    "document_budget_valid",
                    "blocker_stop_valid",
                    "dual_plane_valid",
                    "lean_governance_semantic_check",
                    "stage108_required_acceptance_validation_passed",
                    "all_executed_validation_passed",
                )
            },
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P1 静态报告快照合同已完成", acceptance_by_id["ACC-STAGE-108"])
        for acceptance_id in (
            "ACC-STAGE108-P1-01",
            "ACC-STAGE108-P1-02",
            "ACC-STAGE108-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE108-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE108-P1-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
