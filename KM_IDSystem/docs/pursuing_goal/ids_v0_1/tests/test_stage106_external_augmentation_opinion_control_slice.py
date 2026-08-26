"""Stage106 外部增强意见章节 Phase 2 纯内存受控最小切片的聚焦验证。"""

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
SCOPE = BASE / "STAGE106_PHASE2_EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-106_外部增强意见章节.md"
)
PHASE1_SCOPE = BASE / "STAGE106_PHASE1_EXTERNAL_AUGMENTATION_OPINION_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage106_external_augmentation_opinion_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE105_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_PHASE1_CONTROL_FIELDS = [
    "report_id_ref",
    "external_augmentation_opinion_section_ref",
    "external_augmentation_item_ref",
    "external_augmentation_display_label_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "underlying_source_type_ref",
    "internal_evidence_boundary_ref",
    "critical_conclusion_ref",
    "evidence_id_ref",
    "evidence_gap_ref",
    "citation_source_ref",
    "citation_page_ref",
    "data_snapshot_ref",
    "index_version_ref",
    "evidence_snapshot_ref",
    "model_snapshot_ref",
    "generated_at_ref",
    "human_confirmation_item_ref",
    "business_line_whitebox_confirmation_gate_ref",
    "report_snapshot_ref",
    "report_status_impact_ref",
    "report_quality_score_ref",
    "report_export_audit_ref",
    "report_template_limit_ref",
    "report_regeneration_and_withdrawal_ref",
    "audit_boundary_ref",
]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage106_external_augmentation_opinion_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage106 P2 外部增强意见章节受控最小切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage106ExternalAugmentationOpinionPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_external_augmentation_opinion_control_slice(
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
            "ids.stage106.external_augmentation_opinion.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-106", contract["stage"])
        self.assertEqual("IDS-STAGE106-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE106-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-106", contract["acceptance_id"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE106-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE106-P3-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE106_TASKPACK_STAGE106_PHASE1_AND_STAGE105_REVIEWED_REPORT_EVIDENCE_BINDING_CONTROL_ARTIFACTS_ONLY",
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
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage105_review_required"])
        self.assertTrue(predecessor["stage106_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_EVIDENCE_BINDING_RUNTIME_DISABLED",
            predecessor["stage105_review_result"],
        )
        self.assertEqual(
            "PASS_EXTERNAL_AUGMENTATION_OPINION_CHAPTER_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage106_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage105_review_preserved",
            "stage106_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage107_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_input_preserves_phase1_shape_and_evidence_grade(self) -> None:
        controls = self.contract["control_slice_contract"]
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(30, len(self.module.INPUT_FIELDS))
        self.assertEqual(
            EXPECTED_PHASE1_CONTROL_FIELDS,
            controls["phase1_control_reference_fields"],
        )
        self.assertEqual(27, controls["phase1_control_reference_field_count"])
        self.assertEqual(
            ["evidence_grade_ref"], controls["phase2_added_control_reference_fields"]
        )
        self.assertEqual(1, controls["phase2_added_control_reference_field_count"])
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
                for field in (
                    *self.module.PHASE1_CONTROL_REFERENCE_FIELDS,
                    *self.module.PHASE2_ADDED_CONTROL_REFERENCE_FIELDS,
                ):
                    value = request[field]
                    if value is not None:
                        self.assertTrue(value.startswith(":control:stage106-p2:"), field)
                        self.assertTrue(value.endswith(":reference-only"), field)

    def test_accepted_control_slice_projects_exact_shape(self) -> None:
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(74, result["control_projection_field_total_per_request"])
        self.assertEqual(370, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(5, len(projections))
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_report_binding_chapter_snapshot_and_lifecycle_remain_reference_only(self) -> None:
        bindings = self.result[
            "report_evidence_binding_and_chapter_control_projections"
        ]
        snapshots = self.result["generation_snapshot_control_projections"]
        lifecycles = self.result[
            "report_lifecycle_and_export_audit_control_projections"
        ]
        for binding, snapshot, lifecycle in zip(bindings, snapshots, lifecycles):
            with self.subTest(scenario=binding["control_scenario"]):
                self.assertNotEqual(
                    binding["evidence_id_ref"] is None,
                    binding["evidence_gap_ref"] is None,
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_OPINION_CHAPTER_REFERENCE_ONLY_NOT_RENDERED",
                    binding["external_augmentation_opinion_chapter_output_state"],
                )
                self.assertEqual(
                    "CONTROL_FUTURE_PDF_CITATION_SOURCE_AND_PAGE_REQUIRED_NOT_RENDERED",
                    binding["pdf_citation_source_and_page_display_state"],
                )
                self.assertFalse(binding["actual_report_evidence_binding_performed"])
                self.assertFalse(binding["actual_chapter_output_written"])
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
                    "automatic_report_status_impact_update_allowed",
                    "automatic_report_quality_scoring_allowed",
                    "automatic_report_export_audit_write_allowed",
                    "actual_report_status_impact_analysis_performed",
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
                    "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED_"
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
                    "actual_external_augmentation_opinion_generated",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(record[field])

    def test_input_drift_fails_closed_without_projection_or_runtime(self) -> None:
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["evidence_grade_ref"] = (
            ":control:stage106-p2:unexpected-grade:reference-only"
        )
        rejected = self.module.execute_external_augmentation_opinion_control_slice(
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
            "P3 才验证资料撤回、证据降级和索引版本变化",
            "IDS-STAGE106-P3-GATE",
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
            "IDS-STAGE106",
            "IDS-STAGE106-P1",
            "IDS-V0_1-STAGE106-P1",
            "IDS-STAGE106-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P2",
            "IDS-V0_1-STAGE106-P2",
            "IDS-STAGE106-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P3",
            "IDS-V0_1-STAGE106-P3",
            "IDS-STAGE106-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P4",
            "IDS-V0_1-STAGE106-P4",
            "IDS-STAGE106-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-REVIEW",
            "IDS-V0_1-STAGE106-REVIEW",
            "IDS-STAGE107-P1-GATE",
        )
        stage107_phase1_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P1",
            "IDS-V0_1-STAGE107-P1",
            "IDS-STAGE107-P2-GATE",
        )
        stage107_phase2_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P2",
            "IDS-V0_1-STAGE107-P2",
            "IDS-STAGE107-P3-GATE",
        )
        stage107_phase3_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P3",
            "IDS-V0_1-STAGE107-P3",
            "IDS-STAGE107-P4-GATE",
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
                stage107_phase1_current,
                stage107_phase2_current,
                stage107_phase3_current,
            },
        )
        if current == phase2_current:
            self.assertTrue(is_current_projection)
            self.assertEqual(
                "EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE106-P3-GATE", plan["stop_condition"])
        elif current in {
            phase3_current,
            phase4_current,
            review_current,
            stage107_phase1_current,
            stage107_phase2_current,
            stage107_phase3_current,
        }:
            self.assertTrue(is_current_projection)
        else:
            self.assertFalse(is_current_projection)

        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase2_current:
            self.assertEqual("P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-106"])
        for acceptance_id in (
            "ACC-STAGE106-P2-01",
            "ACC-STAGE106-P2-02",
            "ACC-STAGE106-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE106-P2-04"])

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE106-P3-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE106-P2-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
