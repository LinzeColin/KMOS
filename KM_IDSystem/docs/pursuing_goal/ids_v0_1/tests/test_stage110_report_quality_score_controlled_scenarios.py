"""Stage110 P3 报告质量评分专项控制场景的聚焦验证。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE110_PHASE3_REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_controlled_scenarios_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-110_报告质量评分.md"
)
PHASE1_SCOPE = BASE / "STAGE110_PHASE1_REPORT_QUALITY_SCORE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage110_report_quality_score_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE110_PHASE2_REPORT_QUALITY_SCORE_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage110_report_quality_score_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE109_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage110ReportQualityScorePhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage110_report_quality_score_controlled_scenarios"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_quality_score_phase3_report()

    def _mutated_phase2_executor(self, mutation):
        def executor(control_input):
            phase2_module = self.module._load_phase2_module()
            result = phase2_module.execute_report_quality_score_control_slice(control_input)
            mutation(result)
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
            PHASE2_MODULE,
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
            "ids.stage110.report_quality_score.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-110", contract["stage"])
        self.assertEqual("IDS-STAGE110-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE110-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-110", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE110-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE110-P4-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE110_TASKPACK_STAGE110_PHASE1_PHASE2_AND_STAGE109_"
            "REVIEWED_REPORT_IMPACT_ANALYSIS_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
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
            "stage109_review_required",
            "stage110_phase1_required",
            "stage110_phase2_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_IMPACT_ANALYSIS_RUNTIME_DISABLED",
            predecessor["stage109_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_QUALITY_SCORE_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage110_phase1_result"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_REPORT_QUALITY_SCORE_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage110_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage109_review_preserved",
            "stage110_phase1_completed",
            "stage110_phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage111_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase2_replay_and_scenario_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            "ids.stage110.report_quality_score.phase2.v1",
            replay["phase2_schema_version"],
        )
        self.assertEqual(
            "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE",
            replay["phase2_record_kind"],
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(42, replay["phase2_input_field_count"])
        self.assertEqual(40, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(126, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(630, replay["phase2_projection_field_count_total"])
        self.assertTrue(replay["replay_is_control_only"])
        self.assertFalse(replay["actual_phase2_runtime_replay_performed"])
        scenarios = self.contract["controlled_scenario_contract"]
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(52, scenarios["scenario_field_count"])
        self.assertEqual(260, scenarios["scenario_field_check_count"])
        self.assertEqual(5, scenarios["control_view_count"])
        self.assertEqual(5, scenarios["human_handling_count"])
        self.assertEqual(2, scenarios["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(
            1, scenarios["quality_whitebox_confirmation_required_scenario_count"]
        )
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenarios["scenario_fields"])
        self.assertEqual(
            {name: len(fields) for name, fields in self.module.CONTROL_VIEW_FIELDS.items()},
            scenarios["control_views"],
        )
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(21, failure["failure_state_count"])
        self.assertEqual(21, len(failure["failure_states"]))

    def test_report_projects_five_closed_control_scenarios(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE110-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE110-P4-GATE", report["next_gate"])
        for field in (
            "phase2_control_shape_preserved",
            "phase2_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(42, report["phase2_input_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(126, report["phase2_projection_field_count_per_request"])
        self.assertEqual(630, report["phase2_projection_field_count_total"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(52, report["scenario_field_count"])
        self.assertEqual(260, report["scenario_field_check_count"])
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(5, report["human_handling_count"])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertEqual(5, len(report["scenario_results"]))
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertNotEqual(
                    scenario["evidence_id_ref"] is None,
                    scenario["evidence_gap_ref"] is None,
                )
                for field in (
                    "report_id_ref",
                    "report_evidence_binding_ref",
                    "critical_conclusion_ref",
                    "evidence_grade_ref",
                    "citation_source_ref",
                    "citation_page_ref",
                    "report_snapshot_ref",
                    "source_withdrawal_ref",
                    "evidence_downgrade_ref",
                    "index_version_change_ref",
                    "impact_scope_ref",
                    "affected_report_ref",
                    "report_status_impact_ref",
                    "internal_evidence_coverage_rate_ref",
                    "citation_completeness_rate_ref",
                    "external_augmentation_ratio_ref",
                    "evidence_gap_count_ref",
                    "quality_metric_definition_ref",
                    "quality_formula_ref",
                    "quality_weight_ref",
                    "quality_threshold_ref",
                    "report_quality_score_ref",
                    "quality_score_explanation_ref",
                    "report_export_audit_ref",
                ):
                    self.assertTrue(
                        scenario[field].startswith(":control:stage110-p2:"), field
                    )
                for field in (
                    "automatic_final_conclusion_allowed",
                    "actual_report_quality_scored",
                    "actual_report_status_impact_updated",
                    "actual_external_augmentation_displayed",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                ):
                    self.assertFalse(scenario[field])

    def test_taskpack_special_cases_and_human_handlings_are_preserved(self) -> None:
        scenarios = {
            item["scenario_category"]: item for item in self.report["scenario_results"]
        }
        cited_material = scenarios["CITED_MATERIAL_UPDATE_EVIDENCE_ID_BINDING_CONTROL"]
        self.assertIsNotNone(cited_material["evidence_id_ref"])
        self.assertIsNone(cited_material["evidence_gap_ref"])
        source_withdrawal = scenarios["SOURCE_WITHDRAWAL_REPORT_STATUS_IMPACT_CONTROL"]
        self.assertIsNone(source_withdrawal["evidence_id_ref"])
        self.assertIsNotNone(source_withdrawal["evidence_gap_ref"])
        self.assertEqual(
            "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            source_withdrawal["source_withdrawal_report_status_impact_state"],
        )
        evidence_downgrade = scenarios[
            "EVIDENCE_DOWNGRADE_REPORT_STATUS_IMPACT_CONTROL"
        ]
        self.assertEqual(
            "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            evidence_downgrade["evidence_downgrade_report_status_impact_state"],
        )
        index_change = scenarios["INDEX_VERSION_CHANGE_REPORT_STATUS_IMPACT_CONTROL"]
        self.assertEqual(
            "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            index_change["index_version_change_report_status_impact_state"],
        )
        quality = scenarios["QUALITY_SCORE_EXPORT_EXTERNAL_AUGMENTATION_WHITEBOX_CONTROL"]
        self.assertEqual(
            "CONTROL_QUALITY_SCORE_BUSINESS_LINE_WHITEBOX_CONFIRMATION_REQUIRED_"
            "NOT_RECORDED",
            quality["quality_score_boundary_state"],
        )
        self.assertEqual(
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
            "SEPARATE_FROM_INTERNAL_EVIDENCE",
            quality["external_augmentation_source_separation_state"],
        )
        for field in (
            "external_augmentation_may_not_be_internal_project_evidence",
            "external_augmentation_may_not_replace_evidence_binding",
            "external_augmentation_may_not_close_evidence_gap",
        ):
            with self.subTest(field=field):
                self.assertTrue(quality[field])
        requiring_confirmation = [
            item
            for item in self.report["scenario_results"]
            if item["human_confirmation_state"]
            == "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
        ]
        self.assertEqual(2, len(requiring_confirmation))
        handlings = self.report["human_handlings"]
        self.assertEqual(5, len(handlings))
        self.assertEqual(2, sum(item["whitebox_confirmation_required"] for item in handlings))
        self.assertEqual(
            1,
            sum(
                item["quality_whitebox_confirmation_required"]
                for item in handlings
            ),
        )
        for handling in handlings:
            with self.subTest(scenario=handling["scenario_id"]):
                self.assertFalse(handling["human_confirmation_recorded"])
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    handling["final_conclusion_state"],
                )

    def test_control_views_project_only_declared_scenario_fields(self) -> None:
        views = self.report["control_views"]
        self.assertEqual(set(self.module.CONTROL_VIEW_FIELDS), set(views))
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(name=name):
                self.assertEqual(5, len(views[name]))
                for record in views[name]:
                    self.assertEqual(set(fields), set(record))

    def test_projection_drift_fails_closed(self) -> None:
        shape_mismatch = self.module.build_report_quality_score_phase3_report(
            phase2_executor=lambda _control_input: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual(
            "PHASE2_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"]
        )

        def break_binding(result):
            result["report_evidence_binding_and_section_control_projections"][0][
                "evidence_id_ref"
            ] = ":control:stage110-p2:unexpected-evidence-id:reference-only"

        binding_drift = self.module.build_report_quality_score_phase3_report(
            self._mutated_phase2_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual(
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT",
            binding_drift["failure_state"],
        )

        def remove_source_withdrawal_control(result):
            result["report_quality_score_and_lifecycle_control_projections"][1][
                "source_withdrawal_control_state"
            ] = "CONTROL_UNEXPECTED"

        withdrawal_drift = self.module.build_report_quality_score_phase3_report(
            self._mutated_phase2_executor(remove_source_withdrawal_control)
        )
        self.assertFalse(withdrawal_drift["valid"])
        self.assertEqual(
            "SOURCE_WITHDRAWAL_IMPACT_CONTROL_MISSING",
            withdrawal_drift["failure_state"],
        )

        def allow_quality_scoring(result):
            result["report_quality_score_and_lifecycle_control_projections"][4][
                "actual_report_quality_scored"
            ] = True

        quality_drift = self.module.build_report_quality_score_phase3_report(
            self._mutated_phase2_executor(allow_quality_scoring)
        )
        self.assertFalse(quality_drift["valid"])
        self.assertEqual(
            "QUALITY_SCORING_BOUNDARY_BREACH", quality_drift["failure_state"]
        )

        def represent_external_as_internal(result):
            result["external_augmentation_and_whitebox_gate_control_projections"][4][
                "external_augmentation_may_not_be_internal_project_evidence"
            ] = False

        external_drift = self.module.build_report_quality_score_phase3_report(
            self._mutated_phase2_executor(represent_external_as_internal)
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            external_drift["failure_state"],
        )

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_quality_score_phase3_report(
            self._mutated_phase2_executor(break_runtime_boundary)
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual(
            "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH", runtime_drift["failure_state"]
        )

        for failed_report in (
            shape_mismatch,
            binding_drift,
            withdrawal_drift,
            quality_drift,
            external_drift,
            runtime_drift,
        ):
            with self.subTest(failure=failed_report["failure_state"]):
                self.assertEqual(0, failed_report["scenario_count"])
                self.assertEqual([], failed_report["scenario_results"])
                self.assertEqual({}, failed_report["control_views"])
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
            "资料撤回、证据降级和索引版本变化",
            "不能成为内部项目依据",
            "IDS-STAGE110-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(
                value == 0
                for key, value in self.report.items()
                if key.startswith("actual_") and isinstance(value, int)
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
        phase2_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P2",
            "IDS-V0_1-STAGE110-P2",
            "IDS-STAGE110-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P3",
            "IDS-V0_1-STAGE110-P3",
            "IDS-STAGE110-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P4",
            "IDS-V0_1-STAGE110-P4",
            "IDS-STAGE110-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-REVIEW",
            "IDS-V0_1-STAGE110-REVIEW",
            "IDS-STAGE111-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {phase2_current}, status, plan, ROADMAP
        )
        self.assertTrue(is_current_projection)
        if is_current_projection:
            return
        if current in {phase4_current, review_current}:
            return
        self.assertEqual(phase3_current, current)
        self.assertEqual(
            "REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE110-P3-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE110-P4-GATE", receipt["next_gate"])
        self.assertEqual(52, receipt["scenario_shape"]["scenario_field_count"])
        self.assertEqual(260, receipt["scenario_shape"]["scenario_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual(8, validation["focused_controlled_scenarios_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P3 报告质量评分专项控制场景已完成",
            acceptance_by_id["ACC-STAGE-110"],
        )
        for acceptance_id in (
            "ACC-STAGE110-P3-01",
            "ACC-STAGE110-P3-02",
            "ACC-STAGE110-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE110-P3-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE110-P3-20260826-001", event_ids)
        self.assertNotIn(phase4_current, {current})
        self.assertNotIn(review_current, {current})


if __name__ == "__main__":
    unittest.main()
