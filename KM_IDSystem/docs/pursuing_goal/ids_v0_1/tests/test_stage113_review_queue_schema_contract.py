"""Stage113 复核队列 Schema Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE113_PHASE1_REVIEW_QUEUE_SCHEMA_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage113_review_queue_schema_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-113_复核队列Schema.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE112_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"

EXPECTED_QUEUE_FIELDS = [
    "review_queue_item_ref",
    "review_queue_schema_ref",
    "review_queue_entry_reason_ref",
    "review_trigger_type_ref",
    "review_status_ref",
    "source_document_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_risk_ref",
    "low_ocr_confidence_ref",
    "source_conflict_ref",
    "parsing_failure_ref",
    "external_augmentation_underlying_source_type_ref",
    "evidence_trust_level_before_ref",
    "evidence_trust_level_after_ref",
    "report_quality_score_before_ref",
    "report_quality_score_after_ref",
    "report_status_impact_ref",
    "review_actor_ref",
    "review_time_ref",
    "review_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "re_review_reference_ref",
    "archive_reference_ref",
    "review_audit_record_ref",
]
EXPECTED_TRIGGERS = [
    "low_ocr_confidence",
    "source_conflict",
    "parsing_failure",
    "evidence_risk",
]
EXPECTED_STATUSES = [
    "pending_review",
    "confirmed",
    "rejected",
    "needs_more_material",
    "archived",
]
EXPECTED_AUDIT_FIELDS = [
    "review_actor_ref",
    "review_time_ref",
    "review_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "review_audit_record_ref",
]


class Stage113ReviewQueueSchemaPhase1Tests(unittest.TestCase):
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

    def test_identity_authority_and_predecessor_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("STAGE-113", contract["stage"])
        self.assertEqual("IDS-STAGE113-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE113-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-113", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE113-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE113-P2-GATE", contract["next_gate"])
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        authority = contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["evidence_ledger_remains_authoritative"])
        self.assertTrue(authority["delivered_report_remains_authoritative"])
        self.assertTrue(authority["existing_audit_log_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        self.assertFalse(authority["second_authoritative_source_created"])
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage112_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED",
            predecessor["stage112_review_result"],
        )
        self.assertTrue(predecessor["business_line_whitebox_gate_preserved"])

    def test_queue_trigger_status_and_audit_shapes_are_exact(self) -> None:
        queue = self.contract["review_queue_schema_control_contract"]
        self.assertEqual(EXPECTED_QUEUE_FIELDS, queue["future_control_reference_fields"])
        self.assertEqual(29, queue["future_control_reference_field_count"])
        self.assertEqual(EXPECTED_TRIGGERS, queue["required_review_trigger_types"])
        self.assertEqual(4, queue["required_review_trigger_type_count"])
        self.assertTrue(
            queue["all_required_review_triggers_must_enter_future_review_queue"]
        )
        self.assertEqual(EXPECTED_STATUSES, queue["fixed_review_statuses"])
        self.assertEqual(5, queue["fixed_review_status_count"])
        self.assertTrue(
            queue[
                "review_status_transition_rules_are_future_business_line_whitebox_authorized_work_only"
            ]
        )
        audit = self.contract["review_audit_control_contract"]
        self.assertEqual(
            EXPECTED_AUDIT_FIELDS,
            audit["required_future_audit_reference_fields"],
        )
        self.assertEqual(7, audit["required_future_audit_reference_field_count"])
        self.assertTrue(audit["actor_time_reason_old_new_controls_required"])
        self.assertTrue(audit["business_line_whitebox_confirmation_required"])

    def test_evidence_report_impact_fail_closed_and_runtime_boundary_are_exact(self) -> None:
        impact = self.contract["evidence_and_report_impact_control_contract"]
        self.assertTrue(impact["evidence_id_or_evidence_gap_reference_required"])
        self.assertTrue(
            impact["future_evidence_trust_level_before_after_references_required"]
        )
        self.assertTrue(
            impact["future_report_quality_score_before_after_references_required"]
        )
        self.assertFalse(impact["actual_evidence_grade_assignment_performed"])
        self.assertFalse(impact["actual_report_quality_score_calculated"])
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(19, failure["failure_state_count"])
        self.assertEqual(19, len(failure["declared_failure_states"]))
        self.assertTrue(
            failure["stage113_phase2_entry_requires_new_independent_run"]
        )
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value == 0 for value in self.contract["runtime_counts"].values())
        )
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage112_review_evidence_declared",
            "stage113_started",
            "stage113_entry_authorized",
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
            "stage114_started",
            "formal_global_upload_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_scope_keeps_taskpack_terms_and_runtime_surfaces_closed(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "低 OCR 置信度",
            "资料冲突",
            "解析失败",
            "证据风险",
            "待复核",
            "已确认",
            "已拒绝",
            "需补资料",
            "已归档",
            "actor",
            "old_value",
            "new_value",
            "IDS-STAGE113-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertEqual(
            "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED",
            self.contract["rollback_contract"]["fallback_result"],
        )

    def test_current_governance_receipt_and_event_are_exact(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("P1 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
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
        is_legacy = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current, phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertTrue(
            is_legacy or current in {phase1_current, phase2_current, phase3_current}
        )
        if is_legacy or current != phase1_current:
            return
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-113"])
        for acceptance_id in (
            "ACC-STAGE113-P1-01",
            "ACC-STAGE113-P1-02",
            "ACC-STAGE113-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE113-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE113-P1-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
