"""Stage107 人工确认事项章节 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE107_PHASE1_HUMAN_CONFIRMATION_ITEMS_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage107_human_confirmation_items_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-107_人工确认事项章节.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE106_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage107-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "report_id_ref",
    "human_confirmation_section_ref",
    "human_confirmation_item_ref",
    "human_confirmation_category_ref",
    "human_confirmation_requirement_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "report_evidence_binding_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "report_snapshot_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "audit_boundary_ref",
]

EXPECTED_HUMAN_CONFIRMATION_CATEGORIES = [
    "停机",
    "焊接",
    "热处理",
    "吊装",
    "设备改造",
    "合同承诺",
]


class Stage107HumanConfirmationItemsPhase1Tests(unittest.TestCase):
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
            "ids.stage107.human_confirmation_items.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-107", contract["stage"])
        self.assertEqual("IDS-STAGE107-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE107-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-107", contract["acceptance_id"])
        self.assertEqual(
            "HUMAN_CONFIRMATION_ITEMS_CHAPTER_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE107-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE107-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE107_TASKPACK_AND_STAGE106_REVIEWED_EXTERNAL_AUGMENTATION_CONTROL_ARTIFACTS_ONLY",
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
        self.assertTrue(predecessor["stage106_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_EXTERNAL_AUGMENTATION_OPINION_RUNTIME_DISABLED",
            predecessor["stage106_review_result"],
        )
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_human_confirmation_shape_and_report_controls_are_exact(self) -> None:
        controls = self.contract["human_confirmation_items_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(25, controls["future_control_reference_field_count"])
        self.assertTrue(controls["control_references_are_labels_only"])
        self.assertEqual(
            EXPECTED_HUMAN_CONFIRMATION_CATEGORIES,
            controls["required_human_confirmation_categories"],
        )
        self.assertEqual(6, controls["required_human_confirmation_category_count"])
        for field in (
            "every_required_category_requires_business_line_whitebox_confirmation",
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
        self.assertEqual(21, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "REQUIRED_HIGH_RISK_CATEGORY_MISSING",
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_INVALID",
            "ACTUAL_HUMAN_CONFIRMATION_RECORDED_WITHOUT_AUTHORIZATION",
            "ACTUAL_MODEL_AGENT_OVH_OR_PRODUCTION_EXECUTED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE107_PHASE2_NOT_AUTHORIZED",
            "STAGE108_STARTED_WITHOUT_AUTHORIZATION",
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
            "stage106_review_evidence_declared",
            "stage107_started",
            "stage107_entry_authorized",
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
            "stage108_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_EXTERNAL_AUGMENTATION_OPINION_RUNTIME_DISABLED",
            rollback["fallback_result"],
        )
        self.assertFalse(rollback["actual_runtime_or_production_state_changed"])

    def test_current_governance_accepts_predecessor_phase1_or_phase2_projection(self) -> None:
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        predecessor_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-REVIEW",
            "IDS-V0_1-STAGE106-REVIEW",
            "IDS-STAGE107-P1-GATE",
        )
        phase1_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P1",
            "IDS-V0_1-STAGE107-P1",
            "IDS-STAGE107-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P2",
            "IDS-V0_1-STAGE107-P2",
            "IDS-STAGE107-P3-GATE",
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
        self.assertIn(current, {predecessor_current, phase1_current, phase2_current})
        if current == predecessor_current:
            self.assertFalse(is_current_projection)
        elif current == phase1_current:
            self.assertTrue(is_current_projection)
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual(
                "PASS_HUMAN_CONFIRMATION_ITEMS_CHAPTER_CONTRACT_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertEqual("IDS-STAGE107-P2-GATE", receipt["next_gate"])
            self.assertEqual(
                "HUMAN_CONFIRMATION_ITEMS_CHAPTER_CONTRACT_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE107-P2-GATE", plan["stop_condition"])
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertTrue(
                all(value is False for value in receipt["runtime_flags"].values())
            )
            validation = receipt["validation"]
            self.assertTrue(validation["final_validation_recorded"])
            self.assertEqual(
                {
                    "focused_test_count": 7,
                    "historical_whitebox_chain_test_count": 898,
                    "stage005_governance_valid": True,
                    "batch041_050_review_valid": True,
                    "batch051_060_review_valid": True,
                    "human_rendered_file_count": 7,
                    "document_budget_valid": True,
                    "blocker_stop_valid": True,
                    "dual_plane_valid": True,
                    "all_local_validation_passed": True,
                },
                {
                    key: validation["final_validation"][key]
                    for key in (
                        "focused_test_count",
                        "historical_whitebox_chain_test_count",
                        "stage005_governance_valid",
                        "batch041_050_review_valid",
                        "batch051_060_review_valid",
                        "human_rendered_file_count",
                        "document_budget_valid",
                        "blocker_stop_valid",
                        "dual_plane_valid",
                        "all_local_validation_passed",
                    )
                },
            )
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-107"])
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE107-P1-20260826-001", event_ids)
        else:
            self.assertTrue(is_current_projection)


if __name__ == "__main__":
    unittest.main()
