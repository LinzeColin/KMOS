"""Stage105 报告证据绑定 Phase 2 纯内存受控最小切片的聚焦验证。"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE105_PHASE2_REPORT_EVIDENCE_BINDING_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-105_报告证据绑定.md"
)
PHASE1_SCOPE = BASE / "STAGE105_PHASE1_REPORT_EVIDENCE_BINDING_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE104_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage105_report_evidence_binding_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage105 P2 报告证据绑定受控最小切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage105ReportEvidenceBindingPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_report_evidence_binding_control_slice(
            cls.control_input
        )

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
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
            "ids.stage105.report_evidence_binding.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-105", contract["stage"])
        self.assertEqual("IDS-STAGE105-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE105-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-105", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE105-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE105-P3-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE105_TASKPACK_STAGE105_PHASE1_AND_STAGE104_REVIEWED_RAG_NEGATIVE_TEST_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage104_review_required"])
        self.assertTrue(predecessor["stage105_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED",
            predecessor["stage104_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage105_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage104_review_preserved",
            "stage105_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage106_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_input_preserves_phase1_binding_shape(self) -> None:
        controls = self.contract["control_slice_contract"]
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(26, len(self.module.INPUT_FIELDS))
        self.assertEqual(
            list(self.module.PHASE1_CONTROL_REFERENCE_FIELDS),
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(24, controls["phase1_control_reference_field_count"])
        self.assertTrue(
            controls[
                "critical_conclusion_requires_exactly_one_evidence_id_or_evidence_gap_reference"
            ]
        )
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                self.assertTrue(
                    request["binding_mode"].startswith("CONTROL_BINDING_")
                )
                self.assertNotEqual(
                    request["evidence_id_ref"] is None,
                    request["evidence_gap_ref"] is None,
                )
                for field in self.module.PHASE1_CONTROL_REFERENCE_FIELDS:
                    value = request[field]
                    if value is not None:
                        self.assertTrue(value.startswith(":control:stage105-p2:"), field)
                        self.assertTrue(value.endswith(":reference-only"), field)

    def test_accepted_control_slice_projects_exact_shape(self) -> None:
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(66, result["control_projection_field_total_per_request"])
        self.assertEqual(330, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(5, len(projections))
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_report_section_snapshot_and_lifecycle_controls_remain_reference_only(self) -> None:
        sections = self.result["report_section_binding_control_projections"]
        snapshots = self.result["generation_snapshot_control_projections"]
        lifecycles = self.result["report_lifecycle_control_projections"]
        for section, snapshot, lifecycle in zip(sections, snapshots, lifecycles):
            with self.subTest(scenario=section["control_scenario"]):
                self.assertNotEqual(
                    section["evidence_id_ref"] is None,
                    section["evidence_gap_ref"] is None,
                )
                self.assertEqual(
                    "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED",
                    section["report_section_output_state"],
                )
                self.assertEqual(
                    "CONTROL_FUTURE_PDF_CITATION_SOURCE_REQUIRED_NOT_RENDERED",
                    section["pdf_citation_source_display_state"],
                )
                self.assertFalse(section["actual_report_section_written"])
                self.assertEqual(
                    "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED",
                    snapshot["generation_snapshot_control_state"],
                )
                self.assertFalse(snapshot["actual_generation_snapshot_persisted"])
                self.assertEqual(
                    "CONTROL_REPORT_LIFECYCLE_REFERENCE_ONLY_NOT_EXECUTED",
                    lifecycle["report_lifecycle_control_state"],
                )
                for field in (
                    "automatic_report_status_update_allowed",
                    "automatic_report_quality_scoring_allowed",
                    "automatic_report_export_audit_write_allowed",
                    "actual_report_status_updated",
                    "actual_report_impact_analysis_performed",
                    "actual_report_quality_scored",
                    "actual_report_export_audit_written",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(lifecycle[field])

    def test_external_augmentation_and_whitebox_gate_remain_closed(self) -> None:
        records = self.result[
            "external_augmentation_and_whitebox_gate_control_projections"
        ]
        self.assertEqual(5, len(records))
        for record in records:
            with self.subTest(scenario=record["control_scenario"]):
                self.assertEqual(
                    "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED",
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
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["evidence_gap_ref"] = (
            ":control:stage105-p2:unexpected-gap:reference-only"
        )
        rejected = self.module.execute_report_evidence_binding_control_slice(
            invalid_input
        )
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
            "五条固定、非业务、`reference-only`",
            "关键结论在每条控制请求中严格二选一关联",
            "P3 才验证资料撤回、证据降级和索引变化",
            "IDS-STAGE105-P3-GATE",
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

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P1",
            "IDS-V0_1-STAGE105-P1",
            "IDS-STAGE105-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P2",
            "IDS-V0_1-STAGE105-P2",
            "IDS-STAGE105-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P3",
            "IDS-V0_1-STAGE105-P3",
            "IDS-STAGE105-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P4",
            "IDS-V0_1-STAGE105-P4",
            "IDS-STAGE105-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-REVIEW",
            "IDS-V0_1-STAGE105-REVIEW",
            "IDS-STAGE106-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertIn(
            current,
            {
                phase1_current,
                phase2_current,
                phase3_current,
                phase4_current,
                review_current,
            },
        )
        if current == phase2_current:
            self.assertTrue(is_current_projection)
            self.assertEqual(
                "REPORT_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE105-P3-GATE", plan["stop_condition"])
        elif current in {phase3_current, phase4_current, review_current}:
            self.assertTrue(is_current_projection)
        else:
            self.assertFalse(is_current_projection)

        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase2_current:
            self.assertEqual("P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-105"])
        elif current == phase3_current:
            self.assertEqual("P3 专项异常场景已完成", acceptance_by_id["ACC-STAGE-105"])
        for acceptance_id in (
            "ACC-STAGE105-P2-01",
            "ACC-STAGE105-P2-02",
            "ACC-STAGE105-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE105-P2-04"])

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE105-P3-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE105-P2-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
