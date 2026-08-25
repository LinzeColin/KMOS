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
SCOPE = BASE / "STAGE104_PHASE3_RAG_NEGATIVE_TEST_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-104_RAG负向测试.md"
)
PHASE1_SCOPE = BASE / "STAGE104_PHASE1_RAG_NEGATIVE_TEST_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage104_rag_negative_testing_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE104_PHASE2_RAG_NEGATIVE_TEST_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage104_rag_negative_testing_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage104_rag_negative_testing_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE103_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


HIGH_RISK_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}
EXPECTED_FAILURES = (
    "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
    "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
    "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage104_rag_negative_testing_controlled_scenarios", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage104 P3 RAG 负向测试专项场景模块")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage104RagNegativeTestingPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_rag_negative_testing_phase3_report()

    def _mutated_phase2_executor(self, mutator):
        phase2_module = self.module._load_phase2_module()
        baseline = phase2_module.execute_rag_negative_testing_control_slice(
            phase2_module.build_control_input()
        )

        def executor(_control_input):
            result = copy.deepcopy(baseline)
            mutator(result)
            return result

        return executor

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
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
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage104.rag_negative_testing.phase3.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-104", contract["stage"])
        self.assertEqual("IDS-STAGE104-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE104-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-104", contract["acceptance_id"])
        self.assertEqual("D16-S008", contract["local_stage_code"])
        self.assertEqual("IDS-STAGE104-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE104-P4-GATE", contract["next_gate"])
        self.assertEqual(
            "PHASE3_RAG_NEGATIVE_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE104_TASKPACK_STAGE104_PHASE1_PHASE2_AND_STAGE103_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(source["second_authoritative_source_created"])
        for field, value in source.items():
            if field.endswith("_performed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage103_review_required"])
        self.assertTrue(predecessor["stage104_phase1_required"])
        self.assertTrue(predecessor["stage104_phase2_required"])
        self.assertEqual(
            "PASS_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            predecessor["stage103_review_result"],
        )
        self.assertEqual(
            "PASS_RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage104_phase1_result"],
        )
        self.assertEqual(
            "PASS_IN_MEMORY_RAG_NEGATIVE_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage104_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage103_review_evidence_declared",
            "stage104_started",
            "stage104_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], True)
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage105_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], False)

    def test_phase2_replay_and_scenario_contract_have_exact_shape(self):
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(
            "ids.stage104.rag_negative_testing.phase2.v1",
            replay["phase2_schema_version"],
        )
        self.assertEqual("CONTROL_ONLY_IN_MEMORY_RAG_NEGATIVE_TEST", replay["phase2_record_kind"])
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(29, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(57, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(285, replay["phase2_projection_field_count_total"])
        self.assertTrue(replay["replay_is_control_only"])
        self.assertFalse(replay["actual_phase2_runtime_replay_performed"])
        scenarios = self.contract["controlled_scenario_contract"]
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(34, scenarios["scenario_field_count"])
        self.assertEqual(170, scenarios["scenario_field_check_count"])
        self.assertEqual(5, scenarios["control_view_count"])
        self.assertEqual(5, scenarios["human_handling_count"])
        self.assertEqual(3, scenarios["high_risk_human_confirmation_count"])
        self.assertEqual(
            set(self.module.SCENARIO_FIELDS), set(scenarios["scenario_fields"])
        )
        self.assertEqual(
            {name: len(fields) for name, fields in self.module.CONTROL_VIEW_FIELDS.items()},
            scenarios["control_views"],
        )
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(28, failure["failure_state_count"])
        self.assertEqual(28, len(failure["failure_states"]))

    def test_report_projects_five_closed_control_scenarios(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE104-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE104-P4-GATE", report["next_gate"])
        for field in (
            "phase2_control_shape_preserved",
            "phase2_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(29, report["phase2_input_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(57, report["phase2_projection_field_count_per_request"])
        self.assertEqual(285, report["phase2_projection_field_count_total"])
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
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    scenario["final_conclusion_state"],
                )
                self.assertFalse(scenario["automatic_final_conclusion_allowed"])
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
                self.assertFalse(scenario["actual_model_call_performed"])
                self.assertFalse(scenario["actual_answer_publication_performed"])
                self.assertFalse(scenario["actual_production_writeback_performed"])
                for field in (
                    "rag_answer_structure_ref",
                    "prompt_version_ref",
                    "query_ref",
                    "index_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                    "document_evidence_ref",
                    "document_instruction_candidate_ref",
                    "ids_rule_ref",
                ):
                    self.assertTrue(
                        scenario[field].startswith(":control:stage104-p2:"), field
                    )

    def test_taskpack_special_cases_and_human_handlings_are_preserved(self):
        scenarios = {item["scenario_category"]: item for item in self.report["scenario_results"]}
        document = scenarios["IDS_RULE_PRECEDENCE_CONTROL"]
        self.assertEqual(
            "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            document["document_instruction_evidence_state"],
        )
        self.assertEqual("CONTROL_IDS_RULES_PREVAIL", document["ids_rule_precedence_state"])
        self.assertEqual(
            "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
            document["injection_defense_state"],
        )
        gap = scenarios["EVIDENCE_GAP_SEMANTICS_CONTROL"]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertTrue(gap["evidence_gap_ref"].endswith("reference-only"))
        self.assertEqual("external_augmentation_opinion", gap["external_augmentation_display_label"])
        high_risk = [
            item
            for item in self.report["scenario_results"]
            if item["output_category"] in HIGH_RISK_CATEGORIES
        ]
        self.assertEqual(3, len(high_risk))
        for item in high_risk:
            with self.subTest(category=item["output_category"]):
                self.assertEqual(
                    "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED",
                    item["human_confirmation_state"],
                )
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                    item["output_permission_state"],
                )
        handlings = self.report["human_handlings"]
        self.assertEqual(5, len(handlings))
        self.assertEqual(
            3,
            sum(item["high_risk_human_confirmation_required"] for item in handlings),
        )
        for handling in handlings:
            with self.subTest(scenario=handling["scenario_id"]):
                self.assertFalse(handling["human_approval_recorded"])
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    handling["final_conclusion_state"],
                )

    def test_control_views_project_only_declared_scenario_fields(self):
        views = self.report["control_views"]
        self.assertEqual(set(self.module.CONTROL_VIEW_FIELDS), set(views))
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(name=name):
                self.assertEqual(5, len(views[name]))
                for record in views[name]:
                    self.assertEqual(set(fields), set(record))

    def test_projection_drift_fails_closed(self):
        shape_mismatch = self.module.build_rag_negative_testing_phase3_report(
            phase2_executor=lambda _control_input: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_rule_precedence(result):
            result["document_evidence_and_rule_defense_control_projections"][0][
                "ids_rule_precedence_state"
            ] = "CONTROL_DOCUMENT_RULES_PREVAIL"

        rule_drift = self.module.build_rag_negative_testing_phase3_report(
            self._mutated_phase2_executor(break_rule_precedence)
        )
        self.assertFalse(rule_drift["valid"])
        self.assertEqual(
            "DOCUMENT_INSTRUCTION_CAN_OVERRIDE_IDS_RULE", rule_drift["failure_state"]
        )

        def reclassify_gap(result):
            result["source_semantics_and_external_augmentation_control_projections"][1][
                "internal_evidence_ref"
            ] = ":control:stage104-p2:internal-evidence:gap:reference-only"

        gap_drift = self.module.build_rag_negative_testing_phase3_report(
            self._mutated_phase2_executor(reclassify_gap)
        )
        self.assertFalse(gap_drift["valid"])
        self.assertEqual(
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            gap_drift["failure_state"],
        )

        for index, expected_failure in zip(range(2, 5), EXPECTED_FAILURES):
            with self.subTest(index=index, expected_failure=expected_failure):
                def auto_finalize(result, index=index):
                    result["output_permission_and_whitebox_gate_control_projections"][
                        index
                    ]["automatic_final_conclusion_allowed"] = True

                drift = self.module.build_rag_negative_testing_phase3_report(
                    self._mutated_phase2_executor(auto_finalize)
                )
                self.assertFalse(drift["valid"])
                self.assertEqual(expected_failure, drift["failure_state"])

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_rag_negative_testing_phase3_report(
            self._mutated_phase2_executor(break_runtime_boundary)
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual(
            "PHASE2_SIDE_EFFECT_BOUNDARY_BREACH", runtime_drift["failure_state"]
        )

        for failed_report in (
            shape_mismatch,
            rule_drift,
            gap_drift,
            runtime_drift,
        ):
            with self.subTest(failure=failed_report["failure_state"]):
                self.assertEqual(0, failed_report["scenario_count"])
                self.assertEqual([], failed_report["scenario_results"])
                self.assertEqual({}, failed_report["control_views"])
                self.assertTrue(
                    all(value == 0 for key, value in failed_report.items() if key.startswith("actual_"))
                )
                self.assertTrue(
                    all(value is False for value in failed_report["runtime_boundary"].values())
                )

    def test_runtime_boundary_receipt_and_current_governance_are_exact(self):
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五条固定、非业务、`reference-only`",
            "evidence_gap",
            "最终结论未发布",
            "IDS-STAGE104-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(value == 0 for key, value in self.report.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        legacy = {
            (
                "IDS-STAGE104",
                "IDS-STAGE104-P1",
                "IDS-V0_1-STAGE104-P1",
                "IDS-STAGE104-P2-GATE",
            ),
            (
                "IDS-STAGE104",
                "IDS-STAGE104-P2",
                "IDS-V0_1-STAGE104-P2",
                "IDS-STAGE104-P3-GATE",
            ),
        }
        phase3_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P3",
            "IDS-V0_1-STAGE104-P3",
            "IDS-STAGE104-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P4",
            "IDS-V0_1-STAGE104-P4",
            "IDS-STAGE104-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-REVIEW",
            "IDS-V0_1-STAGE104-REVIEW",
            "IDS-STAGE105-P1-GATE",
        )
        stage105_phase1_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P1",
            "IDS-V0_1-STAGE105-P1",
            "IDS-STAGE105-P2-GATE",
        )
        stage105_phase2_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P2",
            "IDS-V0_1-STAGE105-P2",
            "IDS-STAGE105-P3-GATE",
        )
        stage105_phase3_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P3",
            "IDS-V0_1-STAGE105-P3",
            "IDS-STAGE105-P4-GATE",
        )
        stage105_phase4_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P4",
            "IDS-V0_1-STAGE105-P4",
            "IDS-STAGE105-REVIEW-GATE",
        )
        stage105_review_current = (
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
        is_current_projection = assert_legacy_or_current_projection(
            self, current, legacy, status, plan, ROADMAP
        )
        if current == phase3_current:
            self.assertTrue(is_current_projection)
            self.assertEqual(
                "RAG_NEGATIVE_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE104-P4-GATE", plan["stop_condition"])
        elif current == phase4_current:
            self.assertTrue(is_current_projection)
            self.assertEqual(
                "RAG_NEGATIVE_TEST_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE104-REVIEW-GATE", plan["stop_condition"])
        elif current == review_current:
            self.assertTrue(is_current_projection)
        elif current in {
            stage105_phase1_current,
            stage105_phase2_current,
            stage105_phase3_current,
            stage105_phase4_current,
            stage105_review_current,
            stage106_phase1_current,
            stage106_phase2_current,
            stage106_phase3_current,
        }:
            self.assertTrue(is_current_projection)
        else:
            self.assertFalse(is_current_projection)
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase3_current:
            self.assertEqual("P3 专项异常场景已完成", acceptance_by_id["ACC-STAGE-104"])
        elif current == phase4_current:
            self.assertEqual("P1/P2/P3/P4 控制工件已完成", acceptance_by_id["ACC-STAGE-104"])
        for acceptance_id in (
            "ACC-STAGE104-P3-01",
            "ACC-STAGE104-P3-02",
            "ACC-STAGE104-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE104-P3-04"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE104-P4-GATE", receipt["next_gate"])
        self.assertEqual(5, receipt["controlled_scenarios"]["scenario_count"])
        self.assertEqual(170, receipt["controlled_scenarios"]["scenario_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        validation = receipt["validation"]
        self.assertEqual(8, validation["focused_test_count"])
        self.assertEqual(797, validation["historical_whitebox_chain_test_count"])
        for field in (
            "full_whitebox_validation_recorded",
            "stage005_governance_valid",
            "document_budget_valid",
            "blocker_stop_valid",
            "dual_plane_valid",
            "final_validation_recorded",
        ):
            with self.subTest(validation_field=field):
                self.assertIs(validation[field], True)
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
        self.assertIn("EVT-IDS-V0_1-STAGE104-P3-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
