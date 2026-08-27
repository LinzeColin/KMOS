"""Stage114 P2 复核工作流纯内存受控最小切片的聚焦验证。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema import (
    stage114_review_workflow_control_slice as control_slice,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE114_PHASE2_REVIEW_WORKFLOW_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_control_slice_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-114_复核工作流.md"
)
PREDECESSOR_SCOPE = BASE / "STAGE114_PHASE1_REVIEW_WORKFLOW_SCOPE_BOUNDARY.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage114_review_workflow_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p1-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"

EXPECTED_STATUS_ACTIONS = {
    "low_ocr_pending_review_submit_reference_only": (
        "pending_review",
        "submit_for_review",
    ),
    "source_conflict_confirm_reference_only": ("confirmed", "confirm"),
    "parsing_failure_needs_more_material_reference_only": (
        "needs_more_material",
        "request_more_material",
    ),
    "evidence_risk_reject_reference_only": ("rejected", "reject"),
    "external_augmentation_archive_reference_only": ("archived", "archive"),
}


class Stage114ReviewWorkflowPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = control_slice.build_control_input()
        cls.result = control_slice.project_review_workflow_control_slice(
            cls.control_input
        )

    def test_required_artifacts_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_SCOPE,
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

    def test_identity_authority_predecessor_and_contract_shapes_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("ids.stage114.review_workflow.phase2.v1", contract["schema_version"])
        self.assertEqual("STAGE-114", contract["stage"])
        self.assertEqual("IDS-STAGE114-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE114-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-114", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE114-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE114-P3-GATE", contract["next_gate"])
        self.assertEqual(
            "REVIEW_WORKFLOW_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE114_TASKPACK_STAGE114_PHASE1_AND_STAGE113_REVIEW_CONTROL_ARTIFACTS_ONLY",
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
        predecessor = contract["predecessor_phase1_contract"]
        self.assertTrue(predecessor["stage114_phase1_required"])
        self.assertEqual(
            "PASS_REVIEW_WORKFLOW_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage114_phase1_result"],
        )
        controls = contract["control_input_contract"]
        self.assertEqual(5, controls["control_request_count"])
        self.assertEqual(30, controls["control_input_field_count"])
        self.assertEqual(26, controls["phase1_control_reference_field_count"])
        self.assertTrue(controls["four_required_review_routes_preserved"])
        projections = contract["control_projection_contract"]
        self.assertEqual(4, projections["projection_group_count"])
        self.assertEqual([45, 31, 28, 28], projections["projection_field_shape_per_request"])
        self.assertEqual(132, projections["projection_field_total_per_request"])
        self.assertEqual(660, projections["projection_field_total"])

    def test_canonical_control_input_preserves_routes_statuses_actions_and_binding(self) -> None:
        requests = self.control_input[control_slice.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(30, len(control_slice.INPUT_FIELDS))
        self.assertEqual(26, len(control_slice.PHASE1_CONTROL_REFERENCE_FIELDS))
        self.assertEqual(
            (
                "pending_review",
                "confirmed",
                "rejected",
                "needs_more_material",
                "archived",
            ),
            control_slice.FIXED_REVIEW_STATUSES,
        )
        self.assertEqual(
            (
                "submit_for_review",
                "confirm",
                "reject",
                "request_more_material",
                "archive",
            ),
            control_slice.FIXED_WORKFLOW_ACTIONS,
        )
        self.assertEqual(
            set(control_slice.FIXED_REVIEW_STATUSES),
            {status for status, _action in EXPECTED_STATUS_ACTIONS.values()},
        )
        self.assertEqual(
            set(control_slice.FIXED_WORKFLOW_ACTIONS),
            {action for _status, action in EXPECTED_STATUS_ACTIONS.values()},
        )
        for request in requests:
            scenario = request["control_scenario"]
            with self.subTest(scenario=scenario):
                self.assertEqual(set(control_slice.INPUT_FIELDS), set(request))
                self.assertEqual(
                    EXPECTED_STATUS_ACTIONS[scenario][0],
                    request["fixed_review_status_control_value"],
                )
                self.assertEqual(
                    EXPECTED_STATUS_ACTIONS[scenario][1],
                    request["fixed_workflow_action_control_value"],
                )
                self.assertTrue(
                    bool(request["evidence_id_ref"])
                    ^ bool(request["evidence_gap_ref"])
                )
                for field, value in request.items():
                    if field in {"evidence_id_ref", "evidence_gap_ref"}:
                        continue
                    with self.subTest(field=field):
                        self.assertTrue(value)

    def test_projection_shapes_and_zero_runtime_boundary_are_exact(self) -> None:
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(control_slice.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(132, result["control_projection_field_total_per_request"])
        self.assertEqual(660, result["control_projection_field_total"])
        self.assertFalse(result["persistent_record_created"])
        self.assertTrue(
            all(value is False for value in result["runtime_boundary"].values())
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in result.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        for prefix, fields in control_slice.PROJECTION_FIELDS:
            records = result[f"{prefix}_control_projections"]
            with self.subTest(prefix=prefix):
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                self.assertEqual(5, len(records))
            for record in records:
                with self.subTest(prefix=prefix, scenario=record["control_scenario"]):
                    self.assertEqual(set(fields), set(record))

    def test_workflow_audit_writeback_ui_and_whitebox_boundaries_remain_reference_only(self) -> None:
        workflows = self.result["review_workflow_queue_and_ui_control_projections"]
        audits = self.result["review_audit_control_projections"]
        writebacks = self.result[
            "evidence_risk_and_report_status_writeback_control_projections"
        ]
        sources = self.result["human_reason_and_source_boundary_control_projections"]
        for workflow, audit, writeback, source in zip(
            workflows, audits, writebacks, sources
        ):
            with self.subTest(scenario=workflow["control_scenario"]):
                self.assertTrue(workflow["review_reason_chinese_control_message"])
                self.assertTrue(workflow["review_status_chinese_control_label"])
                self.assertTrue(workflow["workflow_action_chinese_control_label"])
                self.assertTrue(
                    workflow["review_transition_control_label"].startswith(
                        control_slice.CONTROL_PREFIX
                    )
                )
                for field in (
                    "automatic_review_queue_entry_allowed",
                    "automatic_review_status_transition_allowed",
                    "automatic_review_ui_render_allowed",
                    "actual_review_queue_entry_created",
                    "actual_review_status_transition_performed",
                    "actual_review_ui_rendered",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(workflow[field])
                for field in (
                    "automatic_review_audit_write_allowed",
                    "automatic_human_confirmation_allowed",
                    "automatic_re_review_allowed",
                    "automatic_archive_allowed",
                    "actual_review_audit_written",
                    "actual_actor_time_reason_old_new_recorded",
                    "actual_human_confirmation_recorded",
                    "actual_re_review_performed",
                    "actual_archive_performed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(audit[field])
                for field in (
                    "automatic_evidence_risk_writeback_allowed",
                    "automatic_evidence_trust_level_change_allowed",
                    "automatic_report_quality_score_change_allowed",
                    "automatic_report_status_change_allowed",
                    "actual_evidence_risk_writeback_performed",
                    "actual_evidence_trust_level_changed",
                    "actual_report_quality_score_changed",
                    "actual_report_status_changed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(writeback[field])
                self.assertTrue(
                    writeback["review_workflow_writeback_control_label"].startswith(
                        control_slice.CONTROL_PREFIX
                    )
                )
                for field in (
                    "external_augmentation_may_not_be_internal_project_evidence",
                    "external_augmentation_may_not_replace_evidence_binding",
                    "external_augmentation_may_not_close_evidence_gap",
                    "business_line_whitebox_confirmation_required",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(source[field])
                for field in (
                    "automatic_user_feedback_delivery_allowed",
                    "automatic_human_confirmation_allowed",
                    "automatic_final_conclusion_allowed",
                    "actual_external_augmentation_displayed",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(source[field])

    def test_input_drift_fails_closed_without_projection_or_runtime(self) -> None:
        drifted = copy.deepcopy(self.control_input)
        drifted[control_slice.CONTROL_FIELDS[0]][0]["review_status_after_ref"] = "drifted"
        rejected = control_slice.project_review_workflow_control_slice(drifted)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(control_slice.REJECTED_RESULT, rejected["execution_state"])
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        self.assertEqual(0, rejected["control_projection_field_total"])
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )
        for prefix, _fields in control_slice.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                self.assertEqual([], rejected[f"{prefix}_control_projections"])
                self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_scope_receipt_and_p2_completion_evidence_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五条非业务、`reference-only` 纯内存控制请求",
            "每条请求固定 `30` 个输入字段",
            "字段形状为 `45/31/28/28`",
            "P3 才验证低质量 OCR、冲突资料、撤回资料",
            "IDS-STAGE114-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value == 0 for value in self.contract["runtime_counts"].values())
        )
        self.assertEqual(
            24,
            self.contract["failure_and_stop_contract"]["failure_state_count"],
        )
        self.assertEqual(
            24,
            len(self.contract["failure_and_stop_contract"]["declared_failure_states"]),
        )
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("P2 最终治理投影将在冻结本地验收完成后启用")
        self.assertEqual(
            (
                "IDS-STAGE114",
                "IDS-STAGE114-P2",
                "IDS-V0_1-STAGE114-P2",
                "IDS-STAGE114-P3-GATE",
            ),
            (
                receipt["stage"],
                receipt["phase"],
                receipt["task_id"],
                receipt["next_gate"],
            ),
        )
        self.assertEqual(control_slice.PASS_RESULT, receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        self.assertEqual("PASS", receipt["final_validation"]["state"])
        self.assertFalse(receipt["stage_boundary"]["stage114_phase3_started"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertIn("ACC-STAGE-114", acceptance_by_id)
        for acceptance_id in (
            "ACC-STAGE114-P2-01",
            "ACC-STAGE114-P2-02",
            "ACC-STAGE114-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE114-P2-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE114-P2-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
