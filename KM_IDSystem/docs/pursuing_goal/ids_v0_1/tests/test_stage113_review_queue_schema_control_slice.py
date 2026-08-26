"""Stage113 复核队列 Schema Phase 2 纯内存受控最小切片的聚焦验证。"""

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
SCOPE = BASE / "STAGE113_PHASE2_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_control_slice_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-113_复核队列Schema.md"
)
PHASE1_SCOPE = BASE / "STAGE113_PHASE1_REVIEW_QUEUE_SCHEMA_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage113_review_queue_schema_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE112_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage113ReviewQueueSchemaPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage113_review_queue_schema_control_slice"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_review_queue_schema_control_slice(
            cls.control_input
        )

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
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

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage113.review_queue_schema.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-113", contract["stage"])
        self.assertEqual("IDS-STAGE113-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE113-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-113", contract["acceptance_id"])
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE113-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE113-P3-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE113_TASKPACK_STAGE113_PHASE1_AND_STAGE112_REVIEW_"
            "CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
            "control_slice_is_engineering_context_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        self.assertFalse(authority["second_authoritative_source_created"])
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage112_review_required"])
        self.assertTrue(predecessor["stage113_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED",
            predecessor["stage112_review_result"],
        )
        self.assertEqual(
            "PASS_REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage113_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage112_review_preserved",
            "stage113_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage114_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_input_preserves_phase1_queue_shape(self) -> None:
        controls = self.contract["control_slice_contract"]
        self.assertEqual(
            list(self.module.PHASE1_CONTROL_REFERENCE_FIELDS),
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(29, controls["phase1_control_reference_field_count"])
        self.assertEqual(32, len(self.module.INPUT_FIELDS))
        self.assertEqual(
            controls["control_input_field_count"], len(self.module.INPUT_FIELDS)
        )
        self.assertEqual(
            list(self.module.CONTROL_SCENARIOS), controls["fixed_control_scenarios"]
        )
        self.assertEqual(
            list(self.module.FIXED_REVIEW_STATUSES), controls["fixed_review_statuses"]
        )
        self.assertEqual(
            ["low_ocr_confidence", "source_conflict", "parsing_failure", "evidence_risk"],
            controls["review_trigger_types"],
        )
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.FIXED_REVIEW_STATUSES),
            {request["fixed_review_status_control_value"] for request in requests},
        )
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                self.assertTrue(
                    bool(request["evidence_id_ref"])
                    ^ bool(request["evidence_gap_ref"])
                )
                self.assertIn(
                    request["binding_mode"],
                    {"CONTROL_BINDING_EVIDENCE_ID", "CONTROL_BINDING_EVIDENCE_GAP"},
                )
                for field in self.module.PHASE1_CONTROL_REFERENCE_FIELDS:
                    value = request[field]
                    if value is not None:
                        with self.subTest(field=field):
                            self.assertTrue(value.startswith(self.module.CONTROL_PREFIX))
                            self.assertTrue(value.endswith(":reference-only"))

    def test_accepted_control_slice_projects_exact_shape(self) -> None:
        controls = self.contract["control_slice_contract"]
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(self.module.SCHEMA_VERSION, result["schema_version"])
        self.assertEqual(self.module.RECORD_KIND, result["record_kind"])
        self.assertEqual(controls["control_request_count"], result["control_input_count"])
        self.assertEqual(
            controls["projection_group_count"],
            result["control_projection_group_count"],
        )
        self.assertEqual(
            controls["projection_field_total_per_request"],
            result["control_projection_field_total_per_request"],
        )
        self.assertEqual(
            controls["projection_field_total"],
            result["control_projection_field_total"],
        )
        for prefix, fields in self.module.PROJECTION_FIELDS:
            records = result[f"{prefix}_control_projections"]
            with self.subTest(prefix=prefix):
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                self.assertEqual(5, len(records))
            for record in records:
                with self.subTest(prefix=prefix, scenario=record["control_scenario"]):
                    self.assertEqual(set(fields), set(record))

    def test_workflow_audit_and_writeback_remain_reference_only(self) -> None:
        workflows = self.result["review_queue_schema_and_workflow_control_projections"]
        audits = self.result["review_audit_control_projections"]
        writebacks = self.result[
            "evidence_risk_and_report_status_writeback_control_projections"
        ]
        for workflow, audit, writeback in zip(workflows, audits, writebacks):
            with self.subTest(scenario=workflow["control_scenario"]):
                self.assertTrue(
                    bool(workflow["evidence_id_ref"])
                    ^ bool(workflow["evidence_gap_ref"])
                )
                for field in (
                    "automatic_review_queue_schema_migration_allowed",
                    "automatic_review_queue_entry_allowed",
                    "automatic_review_status_transition_allowed",
                    "actual_review_queue_schema_migration_performed",
                    "actual_review_queue_entry_created",
                    "actual_review_status_transition_performed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(workflow[field])
                for field in (
                    "automatic_review_audit_write_allowed",
                    "automatic_human_confirmation_allowed",
                    "actual_review_audit_written",
                    "actual_actor_time_reason_old_new_recorded",
                    "actual_human_confirmation_recorded",
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
                    writeback["review_queue_writeback_control_label"].startswith(
                        self.module.CONTROL_PREFIX
                    )
                )

    def test_chinese_reason_external_augmentation_and_whitebox_gate_remain_closed(
        self,
    ) -> None:
        records = self.result["human_reason_and_source_boundary_control_projections"]
        self.assertEqual(5, len(records))
        for record in records:
            with self.subTest(scenario=record["control_scenario"]):
                self.assertTrue(record["review_reason_chinese_control_message"])
                self.assertTrue(
                    record["external_public_reference_control_label"].startswith(
                        self.module.CONTROL_PREFIX
                    )
                )
                self.assertTrue(
                    record["model_reasoning_control_label"].startswith(
                        self.module.CONTROL_PREFIX
                    )
                )
                for field in (
                    "external_augmentation_may_not_be_internal_project_evidence",
                    "external_augmentation_may_not_replace_evidence_binding",
                    "external_augmentation_may_not_close_evidence_gap",
                    "business_line_whitebox_confirmation_required",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(record[field])
                for field in (
                    "automatic_user_feedback_delivery_allowed",
                    "automatic_human_confirmation_allowed",
                    "automatic_final_conclusion_allowed",
                    "actual_review_ui_rendered",
                    "actual_external_augmentation_displayed",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(record[field])

    def test_input_drift_fails_closed_without_projection_or_runtime(self) -> None:
        drifted = copy.deepcopy(self.control_input)
        drifted[self.module.CONTROL_FIELDS[0]][0]["review_status_ref"] = "drifted"
        rejected = self.module.execute_review_queue_schema_control_slice(drifted)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(self.module.REJECTED_RESULT, rejected["execution_state"])
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        self.assertEqual(0, rejected["control_projection_field_total"])
        self.assertTrue(
            all(
                value == 0
                for key, value in rejected.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                self.assertEqual([], rejected[f"{prefix}_control_projections"])
                self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_receipt_and_current_governance_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "固定五条非业务、`reference-only` 控制请求",
            "每条请求固定 32 个输入字段",
            "共 101 个字段、五条共 505 个检查点",
            "P3 才专项验证低质量 OCR、冲突资料、撤回资料",
            "IDS-STAGE113-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(
                value == 0
                for key, value in self.result.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        self.assertTrue(
            all(value is False for value in self.result["runtime_boundary"].values())
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P2 最终治理投影将在冻结本地验收完成后启用")
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
        if is_legacy or current != phase2_current:
            return
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual(5, receipt["control_shape"]["control_request_count"])
        self.assertEqual(32, receipt["control_shape"]["control_input_field_count"])
        self.assertEqual(29, receipt["control_shape"]["phase1_control_reference_field_count"])
        self.assertEqual(4, receipt["control_shape"]["projection_group_count"])
        self.assertEqual(101, receipt["control_shape"]["projection_field_total_per_request"])
        self.assertEqual(505, receipt["control_shape"]["projection_field_total"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-113"])
        for acceptance_id in (
            "ACC-STAGE113-P2-01",
            "ACC-STAGE113-P2-02",
            "ACC-STAGE113-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE113-P2-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE113-P2-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
