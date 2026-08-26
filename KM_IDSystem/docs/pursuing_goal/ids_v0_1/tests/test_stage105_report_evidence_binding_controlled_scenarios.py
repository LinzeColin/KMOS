"""Stage105 报告证据绑定 Phase 3 纯内存专项场景的聚焦验证。"""

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
SCOPE = BASE / "STAGE105_PHASE3_REPORT_EVIDENCE_BINDING_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_controlled_scenarios.py"
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
PHASE2_SCOPE = BASE / "STAGE105_PHASE2_REPORT_EVIDENCE_BINDING_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE104_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage105_report_evidence_binding_controlled_scenarios", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage105 P3 报告证据绑定专项场景模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage105ReportEvidenceBindingPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_evidence_binding_phase3_report()

    def _mutated_phase2_executor(self, mutation):
        def executor(control_input):
            phase2_module = self.module._load_phase2_module()
            result = phase2_module.execute_report_evidence_binding_control_slice(
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
            "ids.stage105.report_evidence_binding.phase3.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-105", contract["stage"])
        self.assertEqual("IDS-STAGE105-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE105-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-105", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE105-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE105-P4-GATE", contract["next_gate"])
        self.assertEqual(
            "REPORT_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE105_TASKPACK_STAGE105_PHASE1_PHASE2_AND_STAGE104_REVIEWED_RAG_NEGATIVE_TEST_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(source["second_authoritative_source_created"])
        for field, value in source.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        for field in (
            "stage104_review_required",
            "stage105_phase1_required",
            "stage105_phase2_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertEqual(
            "PASS_REVIEWED_RAG_NEGATIVE_TEST_RUNTIME_DISABLED",
            predecessor["stage104_review_result"],
        )
        self.assertEqual(
            "PASS_REPORT_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage105_phase1_result"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_REPORT_EVIDENCE_BINDING_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage105_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage104_review_preserved",
            "stage105_phase1_completed",
            "stage105_phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage106_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase2_replay_and_scenario_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            "ids.stage105.report_evidence_binding.phase2.v1",
            replay["phase2_schema_version"],
        )
        self.assertEqual(
            "CONTROL_ONLY_IN_MEMORY_REPORT_EVIDENCE_BINDING",
            replay["phase2_record_kind"],
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(26, replay["phase2_input_field_count"])
        self.assertEqual(24, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(66, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(330, replay["phase2_projection_field_count_total"])
        self.assertTrue(replay["replay_is_control_only"])
        self.assertFalse(replay["actual_phase2_runtime_replay_performed"])
        scenarios = self.contract["controlled_scenario_contract"]
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(34, scenarios["scenario_field_count"])
        self.assertEqual(170, scenarios["scenario_field_check_count"])
        self.assertEqual(5, scenarios["control_view_count"])
        self.assertEqual(5, scenarios["human_handling_count"])
        self.assertEqual(2, scenarios["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(
            list(self.module.SCENARIO_FIELDS), scenarios["scenario_fields"]
        )
        self.assertEqual(
            {name: len(fields) for name, fields in self.module.CONTROL_VIEW_FIELDS.items()},
            scenarios["control_views"],
        )
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(15, failure["failure_state_count"])
        self.assertEqual(15, len(failure["failure_states"]))

    def test_report_projects_five_closed_control_scenarios(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE105-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE105-P4-GATE", report["next_gate"])
        for field in (
            "phase2_control_shape_preserved",
            "phase2_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(26, report["phase2_input_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(66, report["phase2_projection_field_count_per_request"])
        self.assertEqual(330, report["phase2_projection_field_count_total"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(34, report["scenario_field_count"])
        self.assertEqual(170, report["scenario_field_check_count"])
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
                    "critical_conclusion_ref",
                    "evidence_grade_ref",
                    "citation_source_ref",
                    "citation_page_ref",
                    "index_version_ref",
                    "report_snapshot_ref",
                    "report_status_ref",
                    "report_impact_analysis_ref",
                    "report_quality_score_ref",
                    "report_export_audit_ref",
                ):
                    self.assertTrue(
                        scenario[field].startswith(":control:stage105-p2:"), field
                    )
                self.assertFalse(scenario["automatic_final_conclusion_allowed"])
                self.assertFalse(scenario["actual_report_status_updated"])
                self.assertFalse(scenario["actual_external_augmentation_displayed"])

    def test_taskpack_special_cases_and_human_handlings_are_preserved(self) -> None:
        scenarios = {
            item["scenario_category"]: item for item in self.report["scenario_results"]
        }
        evidence_id = scenarios["EVIDENCE_ID_BINDING_INTEGRITY_CONTROL"]
        self.assertIsNotNone(evidence_id["evidence_id_ref"])
        self.assertIsNone(evidence_id["evidence_gap_ref"])
        evidence_gap = scenarios["EVIDENCE_GAP_BINDING_INTEGRITY_CONTROL"]
        self.assertIsNone(evidence_gap["evidence_id_ref"])
        self.assertIsNotNone(evidence_gap["evidence_gap_ref"])
        external = scenarios["EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_CONTROL"]
        self.assertEqual(
            "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING",
            external["external_augmentation_source_separation_state"],
        )
        self.assertTrue(
            external["external_augmentation_may_not_be_internal_project_evidence"]
        )
        self.assertTrue(external["external_augmentation_may_not_close_evidence_gap"])
        lifecycle = scenarios["REPORT_STATUS_IMPACT_CONTROL"]
        self.assertEqual(
            "CONTROL_MATERIAL_WITHDRAWAL_EVIDENCE_DOWNGRADE_INDEX_VERSION_CHANGE",
            lifecycle["report_status_impact_trigger"],
        )
        self.assertEqual(
            "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED",
            lifecycle["report_status_impact_state"],
        )
        self.assertEqual(
            "CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS",
            lifecycle["evidence_grade_downgrade_state"],
        )
        self.assertEqual(
            "CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS",
            lifecycle["index_version_change_state"],
        )
        self.assertEqual(
            "CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS",
            lifecycle["material_withdrawal_state"],
        )
        requiring_confirmation = [
            item
            for item in self.report["scenario_results"]
            if item["human_confirmation_state"]
            == "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
        ]
        self.assertEqual(2, len(requiring_confirmation))
        handlings = self.report["human_handlings"]
        self.assertEqual(5, len(handlings))
        self.assertEqual(
            2, sum(item["whitebox_confirmation_required"] for item in handlings)
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
        shape_mismatch = self.module.build_report_evidence_binding_phase3_report(
            phase2_executor=lambda _control_input: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_binding(result):
            result["report_section_binding_control_projections"][1][
                "evidence_id_ref"
            ] = ":control:stage105-p2:unexpected-evidence-id:reference-only"

        binding_drift = self.module.build_report_evidence_binding_phase3_report(
            self._mutated_phase2_executor(break_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual(
            "CRITICAL_CONCLUSION_EVIDENCE_BINDING_DRIFT",
            binding_drift["failure_state"],
        )

        def allow_automatic_status_update(result):
            result["report_lifecycle_control_projections"][4][
                "automatic_report_status_update_allowed"
            ] = True

        lifecycle_drift = self.module.build_report_evidence_binding_phase3_report(
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

        external_drift = self.module.build_report_evidence_binding_phase3_report(
            self._mutated_phase2_executor(represent_external_as_internal)
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_REPRESENTED_AS_INTERNAL_EVIDENCE",
            external_drift["failure_state"],
        )

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_evidence_binding_phase3_report(
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
            "五条固定、非业务、`reference-only`",
            "资料撤回、证据降级与索引版本变化",
            "不能写成内部项目依据",
            "IDS-STAGE105-P4-GATE",
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
        stage106_phase1_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P1",
            "IDS-V0_1-STAGE106-P1",
            "IDS-STAGE106-P2-GATE",
        )
        stage106_phase2_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P2",
            "IDS-V0_1-STAGE106-P2",
            "IDS-STAGE106-P3-GATE",
        )
        stage106_phase3_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P3",
            "IDS-V0_1-STAGE106-P3",
            "IDS-STAGE106-P4-GATE",
        )
        stage106_phase4_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P4",
            "IDS-V0_1-STAGE106-P4",
            "IDS-STAGE106-REVIEW-GATE",
        )
        stage106_review_current = (
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
        stage107_phase4_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P4",
            "IDS-V0_1-STAGE107-P4",
            "IDS-STAGE107-REVIEW-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current},
            status,
            plan,
            ROADMAP,
        )
        if current == phase3_current:
            self.assertTrue(is_current_projection)
            self.assertEqual(
                "REPORT_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE105-P4-GATE", plan["stop_condition"])
        elif current in {
            phase4_current,
            review_current,
            stage106_phase1_current,
            stage106_phase2_current,
            stage106_phase3_current,
            stage106_phase4_current,
            stage106_review_current,
            stage107_phase1_current,
            stage107_phase2_current,
            stage107_phase3_current,
            stage107_phase4_current,
        }:
            self.assertTrue(is_current_projection)
        else:
            self.assertFalse(is_current_projection)

        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase3_current:
            self.assertEqual("P3 专项异常场景已完成", acceptance_by_id["ACC-STAGE-105"])
        for acceptance_id in (
            "ACC-STAGE105-P3-01",
            "ACC-STAGE105-P3-02",
            "ACC-STAGE105-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE105-P3-04"])

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE105-P4-GATE", receipt["next_gate"])
        self.assertEqual(5, receipt["controlled_scenarios"]["scenario_count"])
        self.assertEqual(
            170, receipt["controlled_scenarios"]["scenario_field_check_count"]
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        validation = receipt["validation"]
        self.assertEqual(8, validation["focused_test_count"])
        self.assertEqual(838, validation["historical_whitebox_chain_test_count"])
        for field in (
            "full_whitebox_validation_recorded",
            "stage005_governance_valid",
            "document_budget_valid",
            "blocker_stop_valid",
            "dual_plane_valid",
            "final_validation_recorded",
        ):
            with self.subTest(validation_field=field):
                self.assertTrue(validation[field])
        self.assertEqual(
            "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED",
            validation["batch041_050_review_result"],
        )
        self.assertEqual(
            "PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED",
            validation["batch051_060_review_result"],
        )
        self.assertEqual(7, validation["human_rendered_file_count"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE105-P3-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
