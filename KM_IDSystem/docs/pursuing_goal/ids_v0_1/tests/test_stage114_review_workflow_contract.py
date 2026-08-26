"""Stage114 复核工作流 Phase 1 静态合同的聚焦验证。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE114_PHASE1_REVIEW_WORKFLOW_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage114_review_workflow_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-114_复核工作流.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE113_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"

EXPECTED_WORKFLOW_FIELDS = [
    "review_workflow_ref",
    "review_queue_item_ref",
    "review_trigger_type_ref",
    "review_status_before_ref",
    "review_status_after_ref",
    "review_transition_request_ref",
    "review_transition_reason_ref",
    "review_actor_ref",
    "review_time_ref",
    "review_result_ref",
    "old_value_ref",
    "new_value_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "evidence_risk_ref",
    "evidence_trust_level_before_ref",
    "evidence_trust_level_after_ref",
    "report_quality_score_before_ref",
    "report_quality_score_after_ref",
    "report_status_impact_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "re_review_reference_ref",
    "archive_reference_ref",
    "review_audit_record_ref",
    "external_augmentation_underlying_source_type_ref",
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
EXPECTED_ACTIONS = [
    "submit_for_review",
    "confirm",
    "reject",
    "request_more_material",
    "archive",
]
EXPECTED_AUDIT_FIELDS = [
    "review_actor_ref",
    "review_time_ref",
    "review_transition_reason_ref",
    "old_value_ref",
    "new_value_ref",
    "review_result_ref",
    "review_audit_record_ref",
]


class Stage114ReviewWorkflowPhase1Tests(unittest.TestCase):
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
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_predecessor_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("ids.stage114.review_workflow.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-114", contract["stage"])
        self.assertEqual("IDS-STAGE114-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE114-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-114", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE114-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE114-P2-GATE", contract["next_gate"])
        self.assertEqual("REVIEW_WORKFLOW_CONTRACT_RUNTIME_DISABLED", contract["contract_state"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE114_TASKPACK_AND_STAGE113_REVIEWED_REVIEW_QUEUE_SCHEMA_CONTROL_ARTIFACTS_ONLY",
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
        self.assertFalse(authority["second_authoritative_source_created"])
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage113_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_REVIEW_QUEUE_SCHEMA_RUNTIME_DISABLED",
            predecessor["stage113_review_result"],
        )
        self.assertTrue(predecessor["fixed_review_statuses_preserved"])
        self.assertTrue(predecessor["business_line_whitebox_gate_preserved"])

    def test_workflow_routes_states_actions_and_audit_shapes_are_exact(self) -> None:
        workflow = self.contract["review_workflow_input_output_control_contract"]
        self.assertEqual(EXPECTED_WORKFLOW_FIELDS, workflow["future_control_reference_fields"])
        self.assertEqual(26, workflow["future_control_reference_field_count"])
        self.assertTrue(workflow["control_references_are_labels_only"])
        self.assertEqual(EXPECTED_TRIGGERS, workflow["required_review_trigger_types"])
        self.assertEqual(4, workflow["required_review_trigger_type_count"])
        self.assertTrue(workflow["all_required_review_triggers_route_to_future_pending_review"])
        self.assertEqual(EXPECTED_STATUSES, workflow["fixed_review_statuses"])
        self.assertEqual(5, workflow["fixed_review_status_count"])
        self.assertEqual(EXPECTED_ACTIONS, workflow["future_workflow_action_labels"])
        self.assertEqual(5, workflow["future_workflow_action_label_count"])
        self.assertTrue(
            workflow[
                "each_future_action_requires_from_to_actor_time_reason_old_new_and_result_controls"
            ]
        )
        self.assertTrue(
            workflow[
                "status_transition_rules_are_future_business_line_whitebox_authorized_work_only"
            ]
        )
        audit = self.contract["review_audit_control_contract"]
        self.assertEqual(EXPECTED_AUDIT_FIELDS, audit["required_future_audit_reference_fields"])
        self.assertEqual(7, audit["required_future_audit_reference_field_count"])
        self.assertTrue(audit["actor_time_reason_old_new_controls_required"])
        self.assertTrue(audit["business_line_whitebox_confirmation_required"])

    def test_evidence_impact_runtime_and_stop_boundaries_are_exact(self) -> None:
        impact = self.contract["evidence_and_report_impact_control_contract"]
        for field in (
            "evidence_id_or_evidence_gap_reference_required",
            "future_evidence_trust_level_before_after_references_required",
            "future_report_quality_score_before_after_references_required",
            "future_report_status_impact_reference_required",
            "review_result_does_not_create_business_fact_or_final_verdict",
            "external_augmentation_is_not_internal_project_evidence",
        ):
            with self.subTest(field=field):
                self.assertTrue(impact[field])
        self.assertTrue(all(self.contract["future_runtime_prerequisite_contract"].values()))
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        self.assertTrue(all(not value for key, value in local_code.items() if key != "static_contract_only"))
        self.assertTrue(all(value is False for value in self.contract["runtime_boundary"].values()))
        self.assertTrue(all(value == 0 for value in self.contract["runtime_counts"].values()))
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(20, failures["failure_state_count"])
        self.assertEqual(20, len(failures["declared_failure_states"]))
        for failure_state in (
            "REVIEW_WORKFLOW_TRANSITION_CONTROL_INVALID",
            "REVIEW_AUDIT_CONTROL_REFERENCE_MISSING",
            "ACTUAL_REVIEW_WORKFLOW_OR_DATABASE_EXECUTED_WITHOUT_AUTHORIZATION",
            "SECOND_AUTHORITY_CREATED",
            "STAGE114_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(failure_state=failure_state):
                self.assertIn(failure_state, failures["declared_failure_states"])
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage113_review_evidence_declared",
            "stage114_started",
            "stage114_entry_authorized",
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
            "stage115_started",
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
            "IDS-STAGE114-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertEqual(
            "PASS_REVIEWED_REVIEW_QUEUE_SCHEMA_RUNTIME_DISABLED",
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
            "IDS-STAGE114",
            "IDS-STAGE114-P1",
            "IDS-V0_1-STAGE114-P1",
            "IDS-STAGE114-P2-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {phase1_current}, status, plan, ROADMAP
        )
        self.assertTrue(is_current_projection or current == phase1_current)
        if is_current_projection:
            return
        self.assertEqual("REVIEW_WORKFLOW_CONTRACT_RUNTIME_DISABLED", status["evidence_status"])
        self.assertEqual("PASS_REVIEW_WORKFLOW_CONTRACT_RUNTIME_DISABLED", receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(6, validation["focused_phase1_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        self.assertIn("IDS-STAGE114-P2-GATE", plan["stop_condition"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-114"])
        for acceptance_id in (
            "ACC-STAGE114-P1-01",
            "ACC-STAGE114-P1-02",
            "ACC-STAGE114-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE114-P1-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE114-P1-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
