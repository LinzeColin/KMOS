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
SCOPE = BASE / "STAGE102_PHASE3_DOCUMENT_PROMPT_INJECTION_DEFENSE_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-102_文档内提示注入防护.md"
)
PHASE1_SCOPE = BASE / "STAGE102_PHASE1_DOCUMENT_PROMPT_INJECTION_DEFENSE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage102_document_prompt_injection_defense_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE102_PHASE2_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-p2-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE101_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载控制模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage102DocumentPromptInjectionDefensePhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(
            MODULE, "stage102_document_prompt_injection_defense_controlled_scenarios"
        )
        cls.phase2 = _load_module(
            PHASE2_MODULE, "stage102_document_prompt_injection_defense_control_slice"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase2_result = cls.phase2.execute_document_prompt_injection_defense_control_slice(
            cls.phase2.build_control_input()
        )
        cls.report = cls.module.build_document_prompt_injection_defense_phase3_report()

    def test_scope_contract_modules_taskpack_and_predecessors_exist(self):
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

    def test_identity_single_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage102.document_prompt_injection_defense.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-102", contract["stage"])
        self.assertEqual("IDS-STAGE102-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE102-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-102", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE102-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE102-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertIs(source["second_authoritative_source_created"], False)
        self.assertIs(source["scenario_report_can_replace_source_document"], False)
        self.assertIs(source["scenario_report_can_create_business_fact"], False)
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage101_review_required"])
        self.assertTrue(predecessor["stage102_phase1_required"])
        self.assertTrue(predecessor["stage102_phase2_required"])
        self.assertEqual(
            "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage102_phase2_result"],
        )
        self.assertEqual(":control:stage102-p2:", predecessor["stage102_phase2_control_prefix"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage101_review_evidence_declared",
            "stage102_started",
            "stage102_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], True)
        for field, value in boundary.items():
            if field not in {
                "stage101_review_evidence_declared",
                "stage102_started",
                "stage102_entry_authorized",
                "phase1_completed",
                "phase2_completed",
                "phase3_started",
                "phase3_completed",
            }:
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_phase2_replay_and_phase3_shape_are_exact(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE102-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE102-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(7, report["phase2_control_request_count"])
        self.assertEqual(28, report["phase2_input_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(50, report["phase2_projection_field_count_per_request"])
        self.assertEqual(350, report["phase2_projection_field_count_total"])
        self.assertEqual(7, report["scenario_count"])
        self.assertEqual(34, report["scenario_field_count"])
        self.assertEqual(238, report["scenario_field_check_count"])
        self.assertEqual(7, len(self.module.SCENARIO_DEFINITIONS))
        self.assertEqual(
            self.contract["controlled_scenario_contract"]["scenario_fields"],
            list(self.module.SCENARIO_FIELDS),
        )

    def test_special_scenarios_preserve_ids_rules_evidence_gap_and_whitebox_gate(self):
        scenarios = {
            scenario["scenario_id"]: scenario for scenario in self.report["scenario_results"]
        }
        self.assertEqual(
            {item["scenario_id"] for item in self.module.SCENARIO_DEFINITIONS},
            set(scenarios),
        )
        for scenario in scenarios.values():
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["document_evidence_ref"].endswith("reference-only"))
                self.assertTrue(
                    scenario["document_instruction_candidate_ref"].endswith(
                        "reference-only"
                    )
                )
                self.assertEqual(
                    "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
                    scenario["document_instruction_evidence_state"],
                )
                self.assertEqual(
                    "CONTROL_IDS_RULES_PREVAIL", scenario["ids_rule_precedence_state"]
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
                    scenario["injection_defense_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    scenario["final_conclusion_state"],
                )
                self.assertIs(scenario["automatic_final_conclusion_allowed"], False)
                self.assertIs(
                    scenario["business_line_whitebox_human_approval_recorded"], False
                )
                self.assertIs(scenario["actual_model_call_performed"], False)
                self.assertIs(scenario["actual_answer_publication_performed"], False)
                self.assertIs(scenario["actual_production_writeback_performed"], False)
                self.assertTrue(scenario["expectation_met"])
        gap = scenarios[
            "evidence_gap_cannot_masquerade_as_internal_experience_control"
        ]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_ref"].endswith("reference-only"))
        self.assertIs(gap["internal_evidence_present"], False)
        self.assertIs(gap["evidence_gap_present"], True)
        self.assertEqual("external_augmentation_opinion", gap["external_augmentation_display_label"])
        high_risk = {
            scenario["output_category"]
            for scenario in scenarios.values()
            if scenario["output_category"] in self.module.HUMAN_CONFIRMATION_OUTPUT_CATEGORIES
        }
        self.assertEqual(self.module.HUMAN_CONFIRMATION_OUTPUT_CATEGORIES, high_risk)
        self.assertEqual(7, self.report["human_handling_count"])
        self.assertEqual(7, len(self.report["human_handlings"]))
        self.assertEqual(
            3,
            sum(
                handling["high_risk_human_confirmation_required"]
                for handling in self.report["human_handlings"]
            ),
        )

    def test_control_views_preserve_exact_projection_fields(self):
        self.assertEqual(5, self.report["control_view_count"])
        self.assertEqual(
            set(self.module.CONTROL_VIEW_FIELDS), set(self.report["control_views"])
        )
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(view=name):
                values = self.report["control_views"][name]
                self.assertEqual(7, len(values))
                for value in values:
                    self.assertEqual(set(fields), set(value))

    def test_phase2_drift_fails_closed_for_shape_runtime_and_special_controls(self):
        rejected = self.module.build_document_prompt_injection_defense_phase3_report(
            lambda _input: {}
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", rejected["failure_state"])
        self.assertEqual([], rejected["scenario_results"])

        def replay_with(mutator):
            result = copy.deepcopy(self.phase2_result)
            mutator(result)
            return self.module.build_document_prompt_injection_defense_phase3_report(
                lambda _input: result
            )

        ids_rule_drift = replay_with(
            lambda result: result["document_instruction_defense_control_projections"][0].update(
                {"ids_rule_precedence_state": "DOCUMENT_INSTRUCTION_CAN_OVERRIDE_IDS_RULE"}
            )
        )
        self.assertEqual(
            "DOCUMENT_INSTRUCTION_CAN_OVERRIDE_IDS_RULE", ids_rule_drift["failure_state"]
        )
        evidence_gap_drift = replay_with(
            lambda result: result[
                "source_semantics_and_external_augmentation_display_control_projections"
            ][1].update(
                {"internal_evidence_ref": ":control:stage102-p2:misclassified:reference-only"}
            )
        )
        self.assertEqual(
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            evidence_gap_drift["failure_state"],
        )
        high_risk_drift = replay_with(
            lambda result: result["output_permission_and_whitebox_gate_control_projections"][2].update(
                {"final_conclusion_state": "CONTROL_FINAL_CONCLUSION_PUBLISHED"}
            )
        )
        self.assertEqual(
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            high_risk_drift["failure_state"],
        )
        runtime_drift = replay_with(
            lambda result: result["runtime_boundary"].pop("model_call_performed")
        )
        self.assertEqual("PHASE2_SIDE_EFFECT_BOUNDARY_BREACH", runtime_drift["failure_state"])
        for report in (rejected, ids_rule_drift, evidence_gap_drift, high_risk_drift, runtime_drift):
            with self.subTest(failure=report["failure_state"]):
                self.assertEqual([], report["scenario_results"])
                self.assertTrue(
                    all(value is False for value in report["runtime_boundary"].values())
                )
                self.assertTrue(
                    all(value == 0 for key, value in report.items() if key.startswith("actual_"))
                )

    def test_runtime_and_protected_surfaces_stay_closed(self):
        self.assertIs(self.report["second_authoritative_source_created"], False)
        self.assertIs(self.report["persistent_record_created"], False)
        self.assertEqual(
            set(self.module.RUNTIME_CLOSED_FIELDS), set(self.report["runtime_boundary"])
        )
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value == 0 for key, value in self.report.items() if key.startswith("actual_"))
        )
        for section_name in (
            "runtime_boundary",
            "protected_surface_boundary",
        ):
            for field, value in self.contract[section_name].items():
                with self.subTest(section=section_name, field=field):
                    self.assertIs(value, False)
        future_candidate = self.contract[
            "future_candidate_and_actual_execution_contract"
        ]
        self.assertIs(
            future_candidate["future_model_reasoning_candidate_reference_required"], True
        )
        for field, value in future_candidate.items():
            if field != "future_model_reasoning_candidate_reference_required":
                with self.subTest(section="future_candidate", field=field):
                    self.assertIs(value, False)
        for field, value in self.contract["local_code"].items():
            with self.subTest(field=field):
                if field in {
                    "controlled_scenarios_module_created",
                    "controlled_scenarios_are_pure_memory",
                }:
                    self.assertIs(value, True)
                else:
                    self.assertIs(value, False)

    def test_receipt_scope_and_current_governance_projection_are_exact(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE102-P3-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE102-P4-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "reference-only",
            "7",
            "34",
            "238",
            "IDS-STAGE102-P4-GATE",
            "模型 Token",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        phase1_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P1",
            "IDS-V0_1-STAGE102-P1",
            "IDS-STAGE102-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P2",
            "IDS-V0_1-STAGE102-P2",
            "IDS-STAGE102-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P3",
            "IDS-V0_1-STAGE102-P3",
            "IDS-STAGE102-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P4",
            "IDS-V0_1-STAGE102-P4",
            "IDS-STAGE102-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-REVIEW",
            "IDS-V0_1-STAGE102-REVIEW",
            "IDS-STAGE103-P1-GATE",
        )
        stage103_phase1_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P1",
            "IDS-V0_1-STAGE103-P1",
            "IDS-STAGE103-P2-GATE",
        )
        stage103_phase2_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P2",
            "IDS-V0_1-STAGE103-P2",
            "IDS-STAGE103-P3-GATE",
        )
        stage103_phase3_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P3",
            "IDS-V0_1-STAGE103-P3",
            "IDS-STAGE103-P4-GATE",
        )
        stage103_phase4_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P4",
            "IDS-V0_1-STAGE103-P4",
            "IDS-STAGE103-REVIEW-GATE",
        )
        stage103_review_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-REVIEW",
            "IDS-V0_1-STAGE103-REVIEW",
            "IDS-STAGE104-P1-GATE",
        )
        stage104_phase1_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P1",
            "IDS-V0_1-STAGE104-P1",
            "IDS-STAGE104-P2-GATE",
        )
        stage104_phase2_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P2",
            "IDS-V0_1-STAGE104-P2",
            "IDS-STAGE104-P3-GATE",
        )
        stage104_phase3_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P3",
            "IDS-V0_1-STAGE104-P3",
            "IDS-STAGE104-P4-GATE",
        )
        stage104_phase4_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P4",
            "IDS-V0_1-STAGE104-P4",
            "IDS-STAGE104-REVIEW-GATE",
        )
        stage104_review_current = (
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
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        self.assertIn(
            current,
            {
                phase3_current,
                phase4_current,
                review_current,
                stage103_phase1_current,
                stage103_phase2_current,
                stage103_phase3_current,
                stage103_phase4_current,
                stage103_review_current,
                stage104_phase1_current,
                stage104_phase2_current,
                stage104_phase3_current,
                stage104_phase4_current,
                stage104_review_current,
                stage105_phase1_current,
                stage105_phase2_current,
                stage105_phase3_current,
                stage105_phase4_current,
                stage105_review_current,
                stage106_phase1_current,
                stage106_phase2_current,
            },
        )
        self.assertTrue(
            assert_legacy_or_current_projection(
                self,
                current,
                {phase1_current, phase2_current},
                status,
                plan,
                ROADMAP,
            )
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE102-P3-01",
            "ACC-STAGE102-P3-02",
            "ACC-STAGE102-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE102-P3-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE102-P3-20260825-001", event_ids)


if __name__ == "__main__":
    unittest.main()
