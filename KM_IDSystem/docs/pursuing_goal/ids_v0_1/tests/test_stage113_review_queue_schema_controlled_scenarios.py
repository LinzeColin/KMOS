"""Stage113 复核队列 Schema Phase 3 纯内存专项场景的聚焦验证。"""

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
SCOPE = BASE / "STAGE113_PHASE3_REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_controlled_scenarios_contract.json"
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
PHASE2_SCOPE = BASE / "STAGE113_PHASE2_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE112_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage112_report_export_audit_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage112-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage113ReviewQueueSchemaPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage113_review_queue_schema_controlled_scenarios"
        )
        cls.phase2 = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage113_review_queue_schema_control_slice"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.phase2.build_control_input()
        cls.report = cls.module.build_review_queue_schema_phase3_report(
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
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_RECEIPT,
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
            "ids.stage113.review_queue_schema.phase3.contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-113", contract["stage"])
        self.assertEqual("IDS-STAGE113-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE113-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-113", contract["acceptance_id"])
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE113-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE113-P4-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE113_TASKPACK_STAGE113_PHASE1_PHASE2_AND_STAGE112_REVIEW_"
            "CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "existing_audit_log_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
            "scenario_validation_is_engineering_context_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        self.assertFalse(authority["second_authoritative_source_created"])
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage112_review_required"])
        self.assertTrue(predecessor["stage113_phase1_required"])
        self.assertTrue(predecessor["stage113_phase2_required"])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_EXPORT_AUDIT_RUNTIME_DISABLED",
            predecessor["stage112_review_result"],
        )
        self.assertEqual(
            "PASS_REVIEW_QUEUE_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage113_phase1_result"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_REVIEW_QUEUE_SCHEMA_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage113_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage112_review_preserved",
            "stage113_phase1_completed",
            "stage113_phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage114_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase2_replay_preserves_exact_control_shape(self) -> None:
        controls = self.contract["scenario_contract"]
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["execution_state"])
        self.assertIsNone(report["failure_state"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(
            controls["phase2_control_request_count"],
            report["phase2_control_replay_request_count"],
        )
        self.assertEqual(
            controls["phase2_control_input_field_count"],
            report["phase2_input_field_count"],
        )
        self.assertEqual(
            controls["phase2_phase1_reference_field_count"],
            report["phase2_phase1_reference_field_count"],
        )
        self.assertEqual(
            controls["phase2_projection_group_count"],
            report["phase2_projection_group_count"],
        )
        self.assertEqual(
            controls["phase2_projection_field_count_per_request"],
            report["phase2_projection_field_count_per_request"],
        )
        self.assertEqual(
            controls["phase2_projection_field_check_count"],
            report["phase2_projection_field_check_count"],
        )
        self.assertEqual(
            list(self.module.P2_CONTROL_SCENARIOS),
            [
                request["control_scenario"]
                for request in self.control_input[self.phase2.CONTROL_FIELDS[0]]
            ],
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )

    def test_controlled_scenarios_preserve_exact_taskpack_shape(self) -> None:
        controls = self.contract["scenario_contract"]
        report = self.report
        scenarios = report["scenario_results"]
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(
            controls["scenario_field_count"], report["scenario_field_count"]
        )
        self.assertEqual(
            controls["scenario_field_check_count"], report["scenario_field_check_count"]
        )
        self.assertEqual(
            controls["scenario_ids"], [scenario["scenario_id"] for scenario in scenarios]
        )
        self.assertEqual(
            controls["phase2_control_scenarios"],
            [scenario["phase2_control_scenario"] for scenario in scenarios],
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(
                    bool(scenario["evidence_id_ref"])
                    ^ bool(scenario["evidence_gap_ref"])
                )
                self.assertTrue(scenario["review_reason_chinese_control_message"])
                self.assertTrue(scenario["expectation_met"])
                for field in (
                    "actual_review_queue_or_ui_execution_performed",
                    "actual_review_audit_or_database_execution_performed",
                    "actual_evidence_or_report_writeback_execution_performed",
                    "actual_human_confirmation_execution_performed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(scenario[field])
        scenario_categories = {
            scenario["scenario_category"] for scenario in scenarios
        }
        self.assertIn("LOW_QUALITY_OCR_REVIEW_OPERATION_CONTROL", scenario_categories)
        self.assertIn("CONFLICTING_MATERIAL_REVIEW_AUDIT_CONTROL", scenario_categories)
        self.assertIn("WITHDRAWN_MATERIAL_RE_REVIEW_CONTROL", scenario_categories)
        self.assertIn(
            "EVIDENCE_TRUST_AND_REPORT_QUALITY_IMPACT_CONTROL", scenario_categories
        )
        self.assertIn(
            "EXTERNAL_AUGMENTATION_INTERNAL_EVIDENCE_REPLACEMENT_CONTROL",
            scenario_categories,
        )

    def test_audit_impact_external_augmentation_and_whitebox_controls_are_closed(self) -> None:
        scenarios = self.report["scenario_results"]
        for scenario in scenarios:
            with self.subTest(scenario=scenario["scenario_id"]):
                for field in (
                    "review_audit_record_ref",
                    "review_actor_ref",
                    "review_time_ref",
                    "review_reason_ref",
                    "old_value_ref",
                    "new_value_ref",
                    "review_result_ref",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(
                            scenario[field].startswith(self.module.P2_CONTROL_PREFIX)
                        )
                self.assertEqual(
                    "CONTROL_REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_REFERENCE_ONLY_"
                    "NOT_RECORDED",
                    scenario["review_operation_audit_state"],
                )
                self.assertEqual(
                    "CONTROL_REVIEW_RESULT_EVIDENCE_TRUST_REFERENCE_ONLY_NOT_APPLIED",
                    scenario["review_result_evidence_trust_impact_state"],
                )
                self.assertEqual(
                    "CONTROL_REVIEW_RESULT_REPORT_QUALITY_REFERENCE_ONLY_NOT_APPLIED",
                    scenario["review_result_report_quality_impact_state"],
                )
                self.assertTrue(
                    scenario[
                        "external_augmentation_may_not_be_internal_project_evidence"
                    ]
                )
                self.assertTrue(
                    scenario[
                        "external_augmentation_may_not_replace_evidence_binding"
                    ]
                )
                self.assertTrue(
                    scenario["external_augmentation_may_not_close_evidence_gap"]
                )
                self.assertTrue(
                    scenario["business_line_whitebox_confirmation_required"]
                )
                self.assertFalse(scenario["automatic_review_operation_allowed"])
                self.assertFalse(
                    scenario["automatic_evidence_or_report_writeback_allowed"]
                )

    def test_control_views_and_business_line_handlings_are_exact(self) -> None:
        report = self.report
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(
            set(self.module.CONTROL_VIEW_FIELDS), set(report["control_views"])
        )
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            records = report["control_views"][name]
            with self.subTest(name=name):
                self.assertEqual(5, len(records))
            for record in records:
                with self.subTest(name=name, scenario=record["scenario_id"]):
                    self.assertEqual(set(fields), set(record))
        self.assertEqual(5, report["business_line_whitebox_handling_count"])
        self.assertEqual(5, report["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(5, len(report["business_line_whitebox_handlings"]))
        for handling in report["business_line_whitebox_handlings"]:
            with self.subTest(scenario=handling["scenario_id"]):
                self.assertEqual(
                    set(self.module.BUSINESS_LINE_WHITEBOX_HANDLING_FIELDS),
                    set(handling),
                )
                self.assertTrue(handling["confirmation_required"])
                self.assertFalse(
                    handling["actual_human_confirmation_execution_performed"]
                )

    def test_drift_fails_closed_without_scenarios_or_runtime(self) -> None:
        accepted = self.phase2.execute_review_queue_schema_control_slice(
            self.control_input
        )

        def report_for(mutator):
            drifted = copy.deepcopy(accepted)
            mutator(drifted)
            return self.module.build_review_queue_schema_phase3_report(
                self.control_input,
                phase2_executor=lambda _control_input: drifted,
            )

        cases = (
            (
                "shape",
                lambda result: result.__setitem__(
                    "control_projection_field_total", 504
                ),
                "PHASE2_CONTROL_SHAPE_MISMATCH",
            ),
            (
                "side_effect",
                lambda result: result["runtime_boundary"].__setitem__(
                    "review_audit_write_performed", True
                ),
                "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH",
            ),
            (
                "persistent_record",
                lambda result: result.__setitem__("persistent_record_created", True),
                "P2_PERSISTENT_RECORD_BOUNDARY_BREACH",
            ),
            (
                "audit",
                lambda result: result["review_audit_control_projections"][0].__setitem__(
                    "review_actor_ref", "drifted"
                ),
                "REVIEW_OPERATION_ACTOR_TIME_REASON_OLD_NEW_CONTROL_MISSING",
            ),
            (
                "impact",
                lambda result: result[
                    "evidence_risk_and_report_status_writeback_control_projections"
                ][3].__setitem__("report_quality_score_after_ref", "drifted"),
                "EVIDENCE_TRUST_OR_REPORT_QUALITY_CONTROL_MISSING",
            ),
            (
                "external",
                lambda result: result[
                    "human_reason_and_source_boundary_control_projections"
                ][4].__setitem__(
                    "external_augmentation_may_not_replace_evidence_binding", False
                ),
                "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            ),
        )
        for name, mutator, failure_state in cases:
            with self.subTest(name=name):
                rejected = report_for(mutator)
                self.assertFalse(rejected["valid"])
                self.assertEqual(self.module.FAIL_RESULT, rejected["execution_state"])
                self.assertEqual(failure_state, rejected["failure_state"])
                self.assertEqual(0, rejected["scenario_count"])
                self.assertEqual([], rejected["scenario_results"])
                self.assertEqual({}, rejected["control_views"])
                self.assertEqual([], rejected["business_line_whitebox_handlings"])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in rejected.items()
                        if key.startswith("actual_") and isinstance(value, int)
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in rejected["runtime_boundary"].values()
                    )
                )

    def test_runtime_receipt_and_current_governance_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "低质量 OCR 的复核操作控制",
            "冲突资料的复核审计控制",
            "撤回资料的重新复核控制",
            "evidence trust level 与报告质量分",
            "每条场景固定 52 个字段，五条共 260 个专项场景检查点",
            "IDS-STAGE113-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P3 最终治理投影将在冻结本地验收完成后启用")
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
        if is_legacy or current != phase3_current:
            return
        self.assertEqual(
            "REVIEW_QUEUE_SCHEMA_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual(5, receipt["control_shape"]["phase2_control_request_count"])
        self.assertEqual(
            32, receipt["control_shape"]["phase2_control_input_field_count"]
        )
        self.assertEqual(
            29,
            receipt["control_shape"]["phase2_phase1_reference_field_count"],
        )
        self.assertEqual(
            505,
            receipt["control_shape"]["phase2_projection_field_check_count"],
        )
        self.assertEqual(5, receipt["control_shape"]["controlled_scenario_count"])
        self.assertEqual(
            52, receipt["control_shape"]["controlled_scenario_field_count"]
        )
        self.assertEqual(
            260, receipt["control_shape"]["controlled_scenario_field_check_count"]
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
        self.assertEqual("P3 专项控制场景已完成", acceptance_by_id["ACC-STAGE-113"])
        for acceptance_id in (
            "ACC-STAGE113-P3-01",
            "ACC-STAGE113-P3-02",
            "ACC-STAGE113-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE113-P3-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE113-P3-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
