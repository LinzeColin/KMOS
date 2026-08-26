"""Stage111 报告重新生成队列 Phase 3 纯内存异常场景的聚焦验证。"""

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
SCOPE = BASE / "STAGE111_PHASE3_REPORT_REGENERATION_QUEUE_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_controlled_scenarios_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-111_报告重新生成队列.md"
)
PHASE1_SCOPE = BASE / "STAGE111_PHASE1_REPORT_REGENERATION_QUEUE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage111_report_regeneration_queue_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE111_PHASE2_REPORT_REGENERATION_QUEUE_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE110_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage111ReportRegenerationQueuePhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage111_report_regeneration_queue_controlled_scenarios"
        )
        cls.phase2 = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage111_report_regeneration_queue_control_slice"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_regeneration_queue_phase3_report()

    def _mutated_phase2_executor(self, mutator):
        def executor(control_input):
            result = copy.deepcopy(
                self.phase2.execute_report_regeneration_queue_control_slice(control_input)
            )
            mutator(result)
            return result

        return executor

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
            "ids.stage111.report_regeneration_queue.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-111", contract["stage"])
        self.assertEqual("IDS-STAGE111-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE111-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-111", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_REGENERATION_QUEUE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE111-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE111-P4-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        for field in (
            "stage110_review_required",
            "stage111_phase1_required",
            "stage111_phase2_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertEqual(
            "PASS_IN_MEMORY_REPORT_REGENERATION_QUEUE_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage111_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage110_review_preserved",
            "stage111_phase1_completed",
            "stage111_phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage112_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_phase2_replay_shape_is_preserved(self) -> None:
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(self.phase2.SCHEMA_VERSION, replay["phase2_schema_version"])
        self.assertEqual(self.phase2.RECORD_KIND, replay["phase2_record_kind"])
        self.assertEqual(
            self.phase2.PASS_RESULT, replay["phase2_execution_state"]
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(32, replay["phase2_input_field_count"])
        self.assertEqual(30, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(88, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(440, replay["phase2_projection_field_count_total"])
        self.assertEqual(
            list(self.phase2.CONTROL_SCENARIOS), replay["phase2_control_scenarios"]
        )
        self.assertEqual(
            [prefix for prefix, _fields in self.phase2.PROJECTION_FIELDS],
            replay["phase2_projection_prefixes"],
        )

    def test_controlled_scenarios_cover_taskpack_exception_contract(self) -> None:
        report = self.report
        controlled = self.contract["controlled_scenario_contract"]
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["execution_state"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(5, report["phase2_control_replay_request_count"])
        self.assertEqual(440, report["phase2_projection_field_check_count"])
        self.assertEqual(controlled["scenario_count"], report["scenario_count"])
        self.assertEqual(controlled["scenario_field_count"], report["scenario_field_count"])
        self.assertEqual(
            controlled["scenario_field_check_count"], report["scenario_field_check_count"]
        )
        self.assertEqual(list(self.module.SCENARIO_FIELDS), controlled["scenario_fields"])
        states_by_phase2 = {}
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(
                    bool(scenario["evidence_id_ref"])
                    ^ bool(scenario["evidence_gap_ref"])
                )
                self.assertEqual(
                    "CONTROL_EXACTLY_ONE_EVIDENCE_ID_OR_GAP_REFERENCE_RETAINED",
                    scenario["evidence_binding_integrity_state"],
                )
                for field in (
                    "external_augmentation_may_not_be_internal_project_evidence",
                    "external_augmentation_may_not_replace_evidence_binding",
                    "external_augmentation_may_not_close_evidence_gap",
                    "expectation_met",
                ):
                    with self.subTest(field=field):
                        self.assertTrue(scenario[field])
                for field, value in scenario.items():
                    if field.startswith("actual_") or field.startswith("automatic_"):
                        with self.subTest(field=field):
                            self.assertFalse(value)
                states_by_phase2[scenario["phase2_control_scenario"]] = scenario
        for control_scenario, field in (
            (
                "source_withdrawal_reference_only",
                "source_withdrawal_report_status_impact_state",
            ),
            (
                "evidence_downgrade_reference_only",
                "evidence_downgrade_report_status_impact_state",
            ),
            (
                "index_version_change_reference_only",
                "index_version_change_report_status_impact_state",
            ),
        ):
            with self.subTest(control_scenario=control_scenario):
                self.assertIn("REQUIRED", states_by_phase2[control_scenario][field])

    def test_control_views_and_business_line_handlings_are_exact(self) -> None:
        report = self.report
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(5, report["business_line_whitebox_handling_count"])
        self.assertEqual(5, report["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(set(self.module.CONTROL_VIEW_FIELDS), set(report["control_views"]))
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(name=name):
                records = report["control_views"][name]
                self.assertEqual(5, len(records))
                for record in records:
                    self.assertEqual(set(fields), set(record))
        handlings = report["business_line_whitebox_handlings"]
        self.assertEqual(5, len(handlings))
        for handling in handlings:
            with self.subTest(scenario=handling["scenario_id"]):
                self.assertTrue(handling["whitebox_confirmation_required"])
                self.assertFalse(handling["human_confirmation_recorded"])
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    handling["final_conclusion_state"],
                )

    def test_projection_drift_fails_closed(self) -> None:
        shape_mismatch = self.module.build_report_regeneration_queue_phase3_report(
            phase2_executor=lambda _control_input: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_binding(result):
            result["report_evidence_binding_and_section_control_projections"][0][
                "evidence_id_ref"
            ] = ":control:stage111-p2:unexpected-evidence-id:reference-only"

        binding_drift = self.module.build_report_regeneration_queue_phase3_report(
            self._mutated_phase2_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual(
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT",
            binding_drift["failure_state"],
        )

        def allow_automatic_status_update(result):
            result["report_impact_queue_and_audit_control_projections"][1][
                "automatic_report_status_update_allowed"
            ] = True

        lifecycle_drift = self.module.build_report_regeneration_queue_phase3_report(
            self._mutated_phase2_executor(allow_automatic_status_update)
        )
        self.assertFalse(lifecycle_drift["valid"])
        self.assertEqual(
            "REPORT_STATUS_AUTOMATIC_UPDATE_BOUNDARY_BREACH",
            lifecycle_drift["failure_state"],
        )

        def represent_external_as_internal(result):
            result["external_augmentation_and_whitebox_gate_control_projections"][2][
                "external_augmentation_may_not_be_internal_project_evidence"
            ] = False

        external_drift = self.module.build_report_regeneration_queue_phase3_report(
            self._mutated_phase2_executor(represent_external_as_internal)
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            external_drift["failure_state"],
        )

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_regeneration_queue_phase3_report(
            self._mutated_phase2_executor(break_runtime_boundary)
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual(
            "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH", runtime_drift["failure_state"]
        )

        for failed_report in (
            shape_mismatch,
            binding_drift,
            lifecycle_drift,
            external_drift,
            runtime_drift,
        ):
            with self.subTest(failure=failed_report["failure_state"]):
                self.assertEqual(0, failed_report["scenario_count"])
                self.assertEqual([], failed_report["scenario_results"])
                self.assertEqual({}, failed_report["control_views"])
                self.assertEqual([], failed_report["business_line_whitebox_handlings"])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed_report.items()
                        if key.startswith("actual_")
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in failed_report["runtime_boundary"].values()
                    )
                )

    def test_runtime_receipt_and_current_governance_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五条固定、非业务、`reference-only`",
            "每条四十四个字段、共二百二十个场景检查点",
            "资料撤回、证据降级、证据冲突和索引版本变化",
            "不能写成内部项目依据",
            "IDS-STAGE111-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(
                value == 0
                for key, value in self.report.items()
                if key.startswith("actual_")
            )
        )
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P3 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-P1",
            "IDS-V0_1-STAGE111-P1",
            "IDS-STAGE111-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-P2",
            "IDS-V0_1-STAGE111-P2",
            "IDS-STAGE111-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-P3",
            "IDS-V0_1-STAGE111-P3",
            "IDS-STAGE111-P4-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current, phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertTrue(is_current_projection or current == phase3_current)
        if is_current_projection:
            return
        self.assertEqual(phase3_current, current)
        self.assertEqual(
            "REPORT_REGENERATION_QUEUE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_REGENERATION_QUEUE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE111-P3-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE111-P4-GATE", receipt["next_gate"])
        self.assertEqual(44, receipt["control_shape"]["scenario_field_count"])
        self.assertEqual(220, receipt["control_shape"]["scenario_field_check_count"])
        self.assertEqual(440, receipt["control_shape"]["phase2_projection_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual(8, validation["focused_controlled_scenario_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P3 报告重新生成队列专项异常场景已完成",
            acceptance_by_id["ACC-STAGE-111"],
        )
        for acceptance_id in (
            "ACC-STAGE111-P3-01",
            "ACC-STAGE111-P3-02",
            "ACC-STAGE111-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE111-P3-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE111-P3-20260827-001", event_ids)

    def test_contract_failure_and_feedback_shape_is_exact(self) -> None:
        self.assertEqual(
            list(self.module.FAILURE_STATES),
            self.contract["failure_and_stop_contract"]["failure_states"],
        )
        self.assertEqual(15, len(self.module.FAILURE_STATES))
        self.assertEqual(
            list(self.module.CHINESE_FEEDBACK), self.contract["operator_feedback"]["messages"]
        )
        self.assertEqual(4, len(self.report["chinese_feedback"]))


if __name__ == "__main__":
    unittest.main()
