"""Stage109 报告影响分析 Phase 2 纯内存受控最小切片的聚焦验证。"""

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
SCOPE = BASE / "STAGE109_PHASE2_REPORT_IMPACT_ANALYSIS_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-109_报告影响分析.md"
)
PHASE1_SCOPE = BASE / "STAGE109_PHASE1_REPORT_IMPACT_ANALYSIS_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE108_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage108_report_snapshot_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = (
    ROOT / "machine" / "runs" / "2026-08-26-stage108-review-local.json"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage109_report_impact_analysis_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage109 P2 报告影响分析受控最小切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage109ReportImpactAnalysisPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase1_contract = json.loads(PHASE1_CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_report_impact_analysis_control_slice(
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
            "ids.stage109.report_impact_analysis.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-109", contract["stage"])
        self.assertEqual("IDS-STAGE109-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE109-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-109", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_IMPACT_ANALYSIS_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE109-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE109-P3-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE109_TASKPACK_STAGE109_PHASE1_AND_STAGE108_REVIEWED_"
            "REPORT_SNAPSHOT_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field in (
            "second_authoritative_source_created",
            "actual_source_document_read_performed",
            "actual_external_reference_read_performed",
            "actual_evidence_ledger_read_performed",
            "actual_report_or_pdf_read_performed",
            "actual_business_line_decision_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage108_review_required"])
        self.assertTrue(predecessor["stage109_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_SNAPSHOT_RUNTIME_DISABLED",
            predecessor["stage108_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_IMPACT_ANALYSIS_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage109_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage108_review_preserved",
            "stage109_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage110_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_input_preserves_phase1_report_impact_shape(self) -> None:
        controls = self.contract["control_slice_contract"]
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(35, len(self.module.INPUT_FIELDS))
        self.assertEqual(35, controls["control_input_field_count"])
        self.assertEqual(
            list(self.module.PHASE1_CONTROL_REFERENCE_FIELDS),
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(
            self.phase1_contract["report_impact_analysis_contract"][
                "future_control_reference_fields"
            ],
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(33, controls["phase1_control_reference_field_count"])
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
                        self.assertTrue(value.startswith(":control:stage109-p2:"), field)
                        self.assertTrue(value.endswith(":reference-only"), field)

    def test_accepted_control_slice_projects_exact_shape(self) -> None:
        result = self.result
        controls = self.contract["control_slice_contract"]
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(101, result["control_projection_field_total_per_request"])
        self.assertEqual(505, result["control_projection_field_total"])
        self.assertEqual(5, controls["control_request_count"])
        self.assertEqual(4, controls["projection_group_count"])
        self.assertEqual(101, controls["projection_field_total_per_request"])
        self.assertEqual(505, controls["projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(5, len(projections))
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_binding_snapshot_and_impact_controls_remain_reference_only(self) -> None:
        bindings = self.result["report_evidence_binding_and_section_control_projections"]
        snapshots = self.result["generation_snapshot_control_projections"]
        impacts = self.result["report_impact_analysis_and_lifecycle_control_projections"]
        for binding, snapshot, impact in zip(bindings, snapshots, impacts):
            with self.subTest(scenario=binding["control_scenario"]):
                self.assertNotEqual(
                    binding["evidence_id_ref"] is None,
                    binding["evidence_gap_ref"] is None,
                )
                self.assertIn(
                    binding["report_evidence_binding_control_state"],
                    {
                        "CONTROL_EVIDENCE_ID_BINDING_REFERENCE_ONLY",
                        "CONTROL_EVIDENCE_GAP_BINDING_REFERENCE_ONLY",
                    },
                )
                self.assertEqual(
                    "CONTROL_REPORT_SECTION_REFERENCE_ONLY_NOT_RENDERED",
                    binding["report_section_output_control_state"],
                )
                self.assertEqual(
                    "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED",
                    binding["future_pdf_citation_control_state"],
                )
                for field in (
                    "actual_report_evidence_binding_performed",
                    "actual_report_section_output_performed",
                    "actual_pdf_citation_rendered",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(binding[field])
                self.assertEqual(
                    "CONTROL_FIVE_COMPONENT_REFERENCE_ONLY_NOT_PERSISTED",
                    snapshot["generation_snapshot_control_state"],
                )
                self.assertFalse(snapshot["actual_generation_snapshot_persisted"])
                self.assertEqual(
                    "CONTROL_REPORT_IMPACT_REFERENCE_ONLY_NOT_ANALYZED",
                    impact["report_impact_control_state"],
                )
                for field in (
                    "automatic_report_impact_update_allowed",
                    "automatic_report_quality_scoring_allowed",
                    "automatic_report_export_audit_write_allowed",
                    "automatic_report_regeneration_allowed",
                    "automatic_report_withdrawal_allowed",
                    "actual_report_snapshot_created",
                    "actual_report_impact_analysis_performed",
                    "actual_report_status_impact_updated",
                    "actual_report_quality_scored",
                    "actual_report_export_audit_written",
                    "actual_template_limit_applied",
                    "actual_report_regenerated",
                    "actual_report_withdrawn",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(impact[field])

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
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["evidence_gap_ref"] = (
            ":control:stage109-p2:unexpected-gap:reference-only"
        )
        rejected = self.module.execute_report_impact_analysis_control_slice(
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
            "五条非业务、reference-only 控制请求",
            "严格二选一关联 evidence_id_ref 或 evidence_gap_ref",
            "P3 才验证资料撤回、证据降级与索引版本变化",
            "IDS-STAGE109-P3-GATE",
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
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-P1",
            "IDS-V0_1-STAGE109-P1",
            "IDS-STAGE109-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-P2",
            "IDS-V0_1-STAGE109-P2",
            "IDS-STAGE109-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-P3",
            "IDS-V0_1-STAGE109-P3",
            "IDS-STAGE109-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-P4",
            "IDS-V0_1-STAGE109-P4",
            "IDS-STAGE109-REVIEW-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current, phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current in {phase1_current, phase2_current, phase3_current}:
            self.assertFalse(is_current_projection)
            return
        self.assertTrue(is_current_projection)
        self.assertEqual(phase4_current, current)


if __name__ == "__main__":
    unittest.main()
