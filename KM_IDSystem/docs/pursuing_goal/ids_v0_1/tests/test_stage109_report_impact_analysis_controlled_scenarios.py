"""Stage109 报告影响分析 Phase 3 纯内存专项场景的聚焦验证。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE109_PHASE3_REPORT_IMPACT_ANALYSIS_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_controlled_scenarios.py"
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
PHASE2_SCOPE = BASE / "STAGE109_PHASE2_REPORT_IMPACT_ANALYSIS_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE108_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage108_report_snapshot_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = (
    ROOT / "machine" / "runs" / "2026-08-26-stage108-review-local.json"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage109_report_impact_analysis_controlled_scenarios", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage109 P3 报告影响分析专项场景模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage109ReportImpactAnalysisPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_impact_analysis_phase3_report()

    def _mutated_phase2_executor(self, mutation):
        def executor(control_input):
            phase2_module = self.module._load_phase2_module()
            result = phase2_module.execute_report_impact_analysis_control_slice(
                control_input
            )
            mutation(result)
            return result

        return executor

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
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
            "ids.stage109.report_impact_analysis.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-109", contract["stage"])
        self.assertEqual("IDS-STAGE109-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE109-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-109", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_IMPACT_ANALYSIS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE109-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE109-P4-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE109_TASKPACK_STAGE109_PHASE1_PHASE2_AND_STAGE108_"
            "REVIEWED_REPORT_SNAPSHOT_CONTROL_ARTIFACTS_ONLY",
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
        for field in (
            "stage108_review_required",
            "stage109_phase1_required",
            "stage109_phase2_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertEqual(
            "PASS_REVIEWED_REPORT_SNAPSHOT_RUNTIME_DISABLED",
            predecessor["stage108_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_IMPACT_ANALYSIS_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage109_phase1_result"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_REPORT_IMPACT_ANALYSIS_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage109_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage108_review_preserved",
            "stage109_phase1_completed",
            "stage109_phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage110_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase2_replay_and_scenario_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            "ids.stage109.report_impact_analysis.phase2.v1",
            replay["phase2_schema_version"],
        )
        self.assertEqual(
            "CONTROL_ONLY_IN_MEMORY_REPORT_IMPACT_ANALYSIS",
            replay["phase2_record_kind"],
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(35, replay["phase2_input_field_count"])
        self.assertEqual(33, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(101, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(505, replay["phase2_projection_field_count_total"])
        self.assertTrue(replay["replay_is_control_only"])
        self.assertFalse(replay["actual_phase2_runtime_replay_performed"])
        scenarios = self.contract["controlled_scenario_contract"]
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(42, scenarios["scenario_field_count"])
        self.assertEqual(210, scenarios["scenario_field_check_count"])
        self.assertEqual(5, scenarios["control_view_count"])
        self.assertEqual(5, scenarios["human_handling_count"])
        self.assertEqual(2, scenarios["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenarios["scenario_fields"])
        self.assertEqual(
            {name: len(fields) for name, fields in self.module.CONTROL_VIEW_FIELDS.items()},
            scenarios["control_views"],
        )
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(20, failure["failure_state_count"])
        self.assertEqual(20, len(failure["failure_states"]))

    def test_report_projects_five_closed_control_scenarios(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE109-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE109-P4-GATE", report["next_gate"])
        for field in (
            "phase2_control_shape_preserved",
            "phase2_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(35, report["phase2_input_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(101, report["phase2_projection_field_count_per_request"])
        self.assertEqual(505, report["phase2_projection_field_count_total"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(42, report["scenario_field_count"])
        self.assertEqual(210, report["scenario_field_check_count"])
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
                    "impact_trigger_ref",
                    "impact_scope_ref",
                    "affected_report_ref",
                    "affected_critical_conclusion_ref",
                    "report_status_impact_ref",
                ):
                    self.assertTrue(
                        scenario[field].startswith(":control:stage109-p2:"), field
                    )
                for field in (
                    "automatic_final_conclusion_allowed",
                    "actual_report_impact_analysis_performed",
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
        lifecycle = scenarios[
            "AFFECTED_REPORT_EXTERNAL_AUGMENTATION_WHITEBOX_CONTROL"
        ]
        self.assertEqual(
            "CONTROL_AFFECTED_REPORT_AND_CRITICAL_CONCLUSION_FUTURE_REVIEW_REQUIRED",
            lifecycle["affected_report_control_state"],
        )
        self.assertEqual(
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_"
            "SEPARATE_FROM_INTERNAL_EVIDENCE",
            lifecycle["external_augmentation_source_separation_state"],
        )
        for field in (
            "external_augmentation_may_not_be_internal_project_evidence",
            "external_augmentation_may_not_replace_evidence_binding",
            "external_augmentation_may_not_close_evidence_gap",
        ):
            with self.subTest(field=field):
                self.assertTrue(lifecycle[field])
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
        shape_mismatch = self.module.build_report_impact_analysis_phase3_report(
            phase2_executor=lambda _control_input: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual(
            "PHASE2_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"]
        )

        def break_binding(result):
            result["report_evidence_binding_and_section_control_projections"][0][
                "evidence_id_ref"
            ] = ":control:stage109-p2:unexpected-evidence-id:reference-only"

        binding_drift = self.module.build_report_impact_analysis_phase3_report(
            self._mutated_phase2_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual(
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT",
            binding_drift["failure_state"],
        )

        def allow_automatic_status_update(result):
            result["report_impact_analysis_and_lifecycle_control_projections"][1][
                "automatic_report_impact_update_allowed"
            ] = True

        lifecycle_drift = self.module.build_report_impact_analysis_phase3_report(
            self._mutated_phase2_executor(allow_automatic_status_update)
        )
        self.assertFalse(lifecycle_drift["valid"])
        self.assertEqual(
            "REPORT_STATUS_AUTOMATIC_UPDATE_BOUNDARY_BREACH",
            lifecycle_drift["failure_state"],
        )

        def represent_external_as_internal(result):
            result["external_augmentation_and_whitebox_gate_control_projections"][4][
                "external_augmentation_may_not_be_internal_project_evidence"
            ] = False

        external_drift = self.module.build_report_impact_analysis_phase3_report(
            self._mutated_phase2_executor(represent_external_as_internal)
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            external_drift["failure_state"],
        )

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_impact_analysis_phase3_report(
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
            "五条固定、非业务、reference-only",
            "资料撤回、证据降级和索引版本变化",
            "不能成为内部项目依据",
            "IDS-STAGE109-P4-GATE",
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

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
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
        review_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-REVIEW",
            "IDS-V0_1-STAGE109-REVIEW",
            "IDS-STAGE110-P1-GATE",
        )
        stage110_phase1_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P1",
            "IDS-V0_1-STAGE110-P1",
            "IDS-STAGE110-P2-GATE",
        )
        stage110_phase2_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P2",
            "IDS-V0_1-STAGE110-P2",
            "IDS-STAGE110-P3-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase2_current, phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current in {phase2_current, phase3_current}:
            self.assertFalse(is_current_projection)
            return
        self.assertTrue(is_current_projection)
        self.assertIn(
            current,
            {phase4_current, review_current, stage110_phase1_current, stage110_phase2_current},
        )


if __name__ == "__main__":
    unittest.main()
