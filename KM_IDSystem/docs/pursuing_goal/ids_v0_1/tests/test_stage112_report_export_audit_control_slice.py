"""Stage112 报告导出审计 Phase 2 纯内存控制切片的聚焦验证。"""

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
SCOPE = BASE / "STAGE112_PHASE2_REPORT_EXPORT_AUDIT_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_control_slice_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-112_报告导出审计.md"
)
PHASE1_SCOPE = BASE / "STAGE112_PHASE1_REPORT_EXPORT_AUDIT_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage112_report_export_audit_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE111_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage112ReportExportAuditPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage112_report_export_audit_control_slice"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_report_export_audit_control_slice(
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
            "ids.stage112.report_export_audit.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-112", contract["stage"])
        self.assertEqual("IDS-STAGE112-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE112-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-112", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE112-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE112-P3-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE112_TASKPACK_STAGE112_PHASE1_AND_STAGE111_REVIEW_"
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
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage111_review_required"])
        self.assertTrue(predecessor["stage112_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_REGENERATION_QUEUE_RUNTIME_DISABLED",
            predecessor["stage111_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_EXPORT_AUDIT_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage112_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage111_review_preserved",
            "stage112_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
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

    def test_fixed_control_input_preserves_phase1_export_audit_shape(self) -> None:
        controls = self.contract["control_slice_contract"]
        self.assertEqual(
            list(self.module.PHASE1_CONTROL_REFERENCE_FIELDS),
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(32, controls["phase1_control_reference_field_count"])
        self.assertEqual(34, len(self.module.INPUT_FIELDS))
        self.assertEqual(
            controls["control_input_field_count"], len(self.module.INPUT_FIELDS)
        )
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            list(self.module.CONTROL_SCENARIOS), controls["fixed_control_scenarios"]
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
        contract = self.contract["control_slice_contract"]
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(self.module.SCHEMA_VERSION, result["schema_version"])
        self.assertEqual(self.module.RECORD_KIND, result["record_kind"])
        self.assertEqual(
            contract["control_request_count"], result["control_input_count"]
        )
        self.assertEqual(
            contract["projection_group_count"],
            result["control_projection_group_count"],
        )
        self.assertEqual(
            contract["projection_field_total_per_request"],
            result["control_projection_field_total_per_request"],
        )
        self.assertEqual(
            contract["projection_field_total"],
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

    def test_audit_binding_snapshot_impact_quality_and_retention_controls_are_reference_only(
        self,
    ) -> None:
        identity_records = self.result[
            "report_export_audit_identity_and_binding_control_projections"
        ]
        snapshot_records = self.result["generation_snapshot_control_projections"]
        audit_records = self.result[
            "report_impact_quality_and_audit_control_projections"
        ]
        for identity, snapshot, audit in zip(
            identity_records, snapshot_records, audit_records
        ):
            with self.subTest(scenario=identity["control_scenario"]):
                self.assertTrue(
                    bool(identity["evidence_id_ref"])
                    ^ bool(identity["evidence_gap_ref"])
                )
                for field in (
                    "actor_ref",
                    "export_time_ref",
                    "report_id_ref",
                    "evidence_snapshot_ref",
                    "evidence_grade_ref",
                    "citation_source_ref",
                    "citation_page_ref",
                    "human_confirmation_item_ref",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(identity[field].startswith(self.module.CONTROL_PREFIX))
                self.assertEqual(
                    "CONTROL_ACTOR_TIME_REPORT_ID_EVIDENCE_SNAPSHOT_REFERENCE_ONLY_"
                    "NOT_RECORDED",
                    identity["report_export_audit_identity_control_state"],
                )
                self.assertEqual(
                    "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED",
                    identity["report_section_output_control_state"],
                )
                self.assertEqual(
                    "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED",
                    identity["future_pdf_citation_control_state"],
                )
                self.assertEqual(
                    "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED",
                    snapshot["generation_snapshot_control_state"],
                )
                self.assertTrue(
                    audit["report_export_audit_control_label"].startswith(
                        self.module.CONTROL_PREFIX
                    )
                )
                for field in (
                    "report_impact_control_state",
                    "report_quality_score_control_state",
                    "report_export_audit_state_control_state",
                    "report_export_audit_failure_reason_control_state",
                    "report_export_audit_retention_control_state",
                    "report_regeneration_control_state",
                    "report_withdrawal_control_state",
                ):
                    with self.subTest(field=field):
                        self.assertIn("REFERENCE_ONLY", audit[field])
                for record in (identity, snapshot, audit):
                    for field, value in record.items():
                        if field.startswith("automatic_") or field.startswith("actual_"):
                            with self.subTest(field=field):
                                self.assertFalse(value)

    def test_external_augmentation_and_whitebox_gate_remain_closed(self) -> None:
        records = self.result[
            "external_augmentation_and_whitebox_gate_control_projections"
        ]
        self.assertEqual(5, len(records))
        for record in records:
            with self.subTest(scenario=record["control_scenario"]):
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
                    "SEPARATE_FROM_INTERNAL_EVIDENCE",
                    record["external_augmentation_representation_state"],
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
                    "automatic_human_confirmation_allowed",
                    "automatic_final_conclusion_allowed",
                    "actual_external_augmentation_displayed",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(record[field])

    def test_input_drift_fails_closed_without_projection_or_runtime(self) -> None:
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["actor_ref"] = (
            ":control:stage112-p2:unexpected-actor:reference-only"
        )
        rejected = self.module.execute_report_export_audit_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(self.module.REJECTED_RESULT, rejected["execution_state"])
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        self.assertEqual(0, rejected["control_projection_field_total"])
        self.assertFalse(rejected["persistent_record_created"])
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
            "五条非业务、reference-only 控制请求",
            "每条请求固定 34 个输入字段",
            "共 100 个字段、五条共 500 个检查点",
            "P3 才专项验证关键结论 `evidence_id/evidence_gap`",
            "IDS-STAGE112-P3-GATE",
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
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P1",
            "IDS-V0_1-STAGE112-P1",
            "IDS-STAGE112-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE112",
            "IDS-STAGE112-P2",
            "IDS-V0_1-STAGE112-P2",
            "IDS-STAGE112-P3-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {phase1_current, phase2_current}, status, plan, ROADMAP
        )
        self.assertTrue(
            is_current_projection or current in {phase1_current, phase2_current}
        )
        if is_current_projection or current != phase2_current:
            return
        self.assertEqual(phase2_current, current)
        self.assertEqual(
            "REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_REPORT_EXPORT_AUDIT_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE112-P2-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE112-P3-GATE", receipt["next_gate"])
        self.assertEqual(34, receipt["control_shape"]["control_input_field_count"])
        self.assertEqual(
            100, receipt["control_shape"]["projection_field_count_per_request"]
        )
        self.assertEqual(500, receipt["control_shape"]["projection_field_count_total"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(8, validation["focused_control_slice_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P2 报告导出审计受控最小切片已完成",
            acceptance_by_id["ACC-STAGE-112"],
        )
        for acceptance_id in (
            "ACC-STAGE112-P2-01",
            "ACC-STAGE112-P2-02",
            "ACC-STAGE112-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE112-P2-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE112-P2-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
