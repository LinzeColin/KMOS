"""Stage105 报告证据绑定 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE105_PHASE1_REPORT_EVIDENCE_BINDING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage105_report_evidence_binding_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-105_报告证据绑定.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE104_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "report_id_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_grade_ref",
    "citation_source_ref",
    "citation_page_ref",
    "index_version_ref",
    "generated_at_ref",
    "data_snapshot_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "external_augmentation_section_ref",
    "external_augmentation_source_type_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "report_status_ref",
    "report_impact_analysis_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_and_withdrawal_ref",
    "audit_boundary_ref",
]


class Stage105ReportEvidenceBindingPhase1Tests(unittest.TestCase):
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
            "ids.stage105.report_evidence_binding.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-105", contract["stage"])
        self.assertEqual("IDS-STAGE105-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE105-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-105", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE105-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE105-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE105_TASKPACK_AND_STAGE104_REVIEWED_RAG_NEGATIVE_TEST_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created") or field.endswith("_judgment"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage104_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED",
            predecessor["stage104_review_result"],
        )
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_key_conclusion_binding_and_pdf_citation_control_shape_are_exact(self) -> None:
        controls = self.contract["report_evidence_binding_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(24, controls["future_control_reference_field_count"])
        self.assertEqual(
            set(EXPECTED_CONTROL_FIELDS),
            set(controls["future_control_reference_contract"]),
        )
        for field in (
            "control_references_are_labels_only",
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "citation_source_must_be_displayed_in_future_pdf_report",
            "citation_page_is_future_report_control_reference_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(controls[field])
        for field, value in controls.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_snapshot_external_augmentation_human_and_lifecycle_controls_are_complete(self) -> None:
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

        external = self.contract["external_augmentation_contract"]
        self.assertEqual(
            {"external_public_reference", "model_reasoning"},
            set(external["allowed_underlying_source_types"]),
        )
        for field, value in external.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
            elif field != "allowed_underlying_source_types":
                with self.subTest(field=field):
                    self.assertTrue(value)

        confirmation = self.contract["human_confirmation_contract"]
        for field, value in confirmation.items():
            with self.subTest(field=field):
                self.assertEqual(not field.startswith("actual_"), value)

        lifecycle = self.contract["report_lifecycle_control_contract"]
        for field, value in lifecycle.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
            else:
                with self.subTest(field=field):
                    self.assertTrue(value)

    def test_runtime_and_protected_surfaces_stay_closed(self) -> None:
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field, value in prerequisite.items():
            with self.subTest(field=field):
                self.assertEqual(field.endswith("_is_future_authorized_work_only"), value)
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
        self.assertEqual(22, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "EVIDENCE_ID_AND_GAP_BOTH_MISSING",
            "CITATION_SOURCE_REFERENCE_MISSING",
            "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            "ACTUAL_REPORT_OR_PDF_GENERATED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE105_PHASE2_NOT_AUTHORIZED",
            "STAGE106_STARTED_WITHOUT_AUTHORIZATION",
        ):
            with self.subTest(failure_state=failure_state):
                self.assertIn(failure_state, failures["declared_failure_states"])
        for field, value in failures.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        feedback = self.contract["chinese_feedback_contract"]
        self.assertEqual(4, feedback["feedback_count"])
        self.assertEqual(4, len(feedback["feedbacks"]))
        self.assertFalse(feedback["actual_user_feedback_emitted"])
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage104_review_evidence_declared",
            "stage105_started",
            "stage105_entry_authorized",
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
            "stage106_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage104_review_evidence"])
        self.assertTrue(rollback["preserve_stage104_phase1_to_phase4_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "report_or_evidence_ledger_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
            "stage105_phase2_execution_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

    def test_scope_receipt_and_current_governance_projection_are_explicit(self) -> None:
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "evidence_id_ref` 或 `evidence_gap_ref",
            "PDF 报告必须显示引用来源",
            "data/index/evidence/model snapshot",
            "业务线白箱人工确认项",
            "IDS-STAGE105-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REPORT_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE105-P2-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        stage105_phase1_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P1",
            "IDS-V0_1-STAGE105-P1",
            "IDS-STAGE105-P2-GATE",
        )
        stage105_phase2_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P2",
            "IDS-V0_1-STAGE105-P2",
            "IDS-STAGE105-P3-GATE",
        )
        stage105_phase3_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P3",
            "IDS-V0_1-STAGE105-P3",
            "IDS-STAGE105-P4-GATE",
        )
        stage105_phase4_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P4",
            "IDS-V0_1-STAGE105-P4",
            "IDS-STAGE105-REVIEW-GATE",
        )
        stage105_review_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-REVIEW",
            "IDS-V0_1-STAGE105-REVIEW",
            "IDS-STAGE106-P1-GATE",
        )
        stage106_phase1_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P1",
            "IDS-V0_1-STAGE106-P1",
            "IDS-STAGE106-P2-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {stage105_phase1_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertIn(
            current,
            {
                stage105_phase1_current,
                stage105_phase2_current,
                stage105_phase3_current,
                stage105_phase4_current,
                stage105_review_current,
                stage106_phase1_current,
            },
        )
        if current == stage105_phase1_current:
            self.assertFalse(is_current_projection)
        else:
            self.assertTrue(is_current_projection)
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            (
                "P1 静态合同已完成"
                if current == stage105_phase1_current
                else (
                    "P2 受控最小切片已完成"
                    if current == stage105_phase2_current
                    else (
                        "P3 专项异常场景已完成"
                        if current == stage105_phase3_current
                        else (
                            "整阶段已复审"
                            if current
                            in {stage105_review_current, stage106_phase1_current}
                            else "P1/P2/P3/P4 控制工件已完成"
                        )
                    )
                )
            ),
            acceptance_by_id["ACC-STAGE-105"],
        )
        for acceptance_id in (
            "ACC-STAGE105-P1-01",
            "ACC-STAGE105-P1-02",
            "ACC-STAGE105-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE105-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE105-P1-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
