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
SCOPE = BASE / "STAGE101_PHASE3_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_controlled_scenarios.py"
)
P2_SCOPE = BASE / "STAGE101_PHASE2_RAG_REPRODUCIBILITY_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_control_slice_contract.json"
)
P2_MODULE = (
    BASE / "index_version_schema" / "stage101_rag_reproducibility_control_slice.py"
)
P2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p2-local.json"
P1_SCOPE = BASE / "STAGE101_PHASE1_RAG_REPRODUCIBILITY_SCOPE_BOUNDARY.md"
P1_CONTRACT = (
    BASE / "index_version_schema" / "stage101_rag_reproducibility_contract.json"
)
P1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE100_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-review-local.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-101_RAG可复现.md"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p3-local.json"
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


class Stage101RagReproducibilityPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(MODULE, "stage101_phase3_controlled_scenarios")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_rag_reproducibility_phase3_report()

    def test_artifacts_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P2_SCOPE,
            P2_CONTRACT,
            P2_MODULE,
            P2_RECEIPT,
            P1_SCOPE,
            P1_CONTRACT,
            P1_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage101.rag_reproducibility.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-101", contract["stage"])
        self.assertEqual("IDS-STAGE101-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE101-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-101", contract["acceptance_id"])
        self.assertEqual(
            "PHASE3_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE101-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE101-P4-GATE", contract["next_gate"])

        authority = contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in authority.items():
            if isinstance(value, bool) and field not in {
                "source_document_remains_authoritative",
                "business_line_whitebox_human_review_remains_authoritative",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage100_review_required"])
        self.assertTrue(predecessor["stage101_phase1_required"])
        self.assertTrue(predecessor["stage101_phase2_required"])
        self.assertEqual(
            "PASS_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage101_phase2_receipt_result"],
        )

        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage100_review_evidence_declared",
            "stage101_started",
            "stage101_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage100_review_evidence_declared",
                "stage101_started",
                "stage101_entry_authorized",
                "phase1_completed",
                "phase2_completed",
                "phase3_started",
                "phase3_completed",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_phase2_replay_and_scenario_contract_shape_are_exact(self):
        replay = self.contract["phase2_control_replay_contract"]
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(23, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(45, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(270, replay["phase2_projection_field_count_total"])
        self.assertEqual(
            list(self.module.P2_CONTROL_SCENARIOS),
            replay["fixed_phase2_control_scenarios"],
        )

        scenarios = self.contract["controlled_scenario_contract"]
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenarios["scenario_fields"])
        self.assertEqual(32, scenarios["scenario_field_count"])
        self.assertEqual(6, scenarios["scenario_count"])
        self.assertEqual(192, scenarios["scenario_field_check_count"])
        self.assertEqual(
            [item["scenario_id"] for item in self.module.SCENARIO_DEFINITIONS],
            scenarios["fixed_scenarios"],
        )

    def test_accepted_report_has_exact_scenarios_views_and_whitebox_handlings(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE101-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE101-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(270, report["phase2_projection_field_count_total"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(32, report["scenario_field_count"])
        self.assertEqual(192, report["scenario_field_check_count"])
        self.assertEqual(6, report["future_model_reasoning_candidate_count"])
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(set(self.module.CONTROL_VIEW_FIELDS), set(report["control_views"]))
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(view=name):
                self.assertEqual(6, len(report["control_views"][name]))
                self.assertTrue(
                    all(set(item) == set(fields) for item in report["control_views"][name])
                )
        self.assertEqual(6, report["human_handling_count"])
        self.assertTrue(
            all(
                item["business_line_whitebox_review_required"]
                and item["business_line_whitebox_human_approval_recorded"] is False
                and item["automatic_final_conclusion_allowed"] is False
                and item["actual_human_confirmation_performed"] is False
                for item in report["human_handlings"]
            )
        )

    def test_taskpack_special_validations_hold(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        injection = scenarios["retrieval_document_cannot_override_ids_rule_control"]
        self.assertEqual(
            "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            injection["retrieval_document_instruction_precedence_state"],
        )
        self.assertEqual(
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            injection["prompt_injection_defense_state"],
        )
        self.assertEqual(
            "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
            injection["output_permission_state"],
        )
        self.assertEqual(
            "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
            injection["final_conclusion_state"],
        )

        gap = scenarios["draft_recommendation_evidence_gap_remains_declared_control"]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage101-p2:"))
        self.assertEqual("external_augmentation_opinion", gap["external_augmentation_display_label"])

        for scenario_id in (
            "high_risk_engineering_advice_requires_whitebox_confirmation_control",
            "contractual_commitment_requires_whitebox_confirmation_control",
            "production_writeback_requires_whitebox_confirmation_control",
        ):
            with self.subTest(scenario=scenario_id):
                scenario = scenarios[scenario_id]
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                    scenario["output_permission_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    scenario["final_conclusion_state"],
                )
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(scenario["automatic_final_conclusion_allowed"])
                self.assertFalse(scenario["actual_model_call_performed"])
                self.assertFalse(scenario["actual_answer_publication_performed"])

    def test_tampered_phase2_projection_fails_closed(self):
        invalid = self.module.build_rag_reproducibility_phase3_report(
            lambda _input: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", invalid["failure_state"])
        self.assertEqual([], invalid["scenario_results"])

        phase2_module = _load_module(P2_MODULE, "stage101_phase2_for_tamper")
        tampered = copy.deepcopy(
            phase2_module.execute_rag_reproducibility_control_slice(
                phase2_module.build_control_input()
            )
        )
        injection_index = phase2_module.CONTROL_SCENARIOS.index(
            "retrieval_document_instruction_rejected_reference_only"
        )
        tampered["prompt_injection_and_output_permission_control_projections"][
            injection_index
        ]["prompt_injection_defense_state"] = (
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
        )
        rejected = self.module.build_rag_reproducibility_phase3_report(
            lambda _input: tampered
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE",
            rejected["failure_state"],
        )
        self.assertEqual([], rejected["scenario_results"])

    def test_runtime_authority_failure_and_rollback_contract_remain_closed(self):
        self.assertFalse(self.report["second_authoritative_source_created"])
        self.assertFalse(self.report["persistent_record_created"])
        for field, value in self.report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        self.assertEqual(
            set(self.module.RUNTIME_CLOSED_FIELDS),
            set(self.report["runtime_boundary"]),
        )
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            self.assertTrue(
                all(value is False for value in self.contract[section].values())
            )
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["controlled_scenarios_module_created"])
        self.assertTrue(local_code["controlled_scenarios_are_pure_memory"])
        for field, value in local_code.items():
            if field not in {
                "controlled_scenarios_module_created",
                "controlled_scenarios_are_pure_memory",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE",
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE2_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage101_phase1_evidence",
            "preserve_stage101_phase2_evidence",
            "preserve_stage100_review_evidence",
            "preserve_stage100_phase1_to_phase4_evidence",
        ):
            with self.subTest(field=field):
                self.assertTrue(rollback[field])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_scope_receipt_and_successor_governance_keep_p4_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "二十三字段",
            "三十二字段",
            "提示注入",
            "业务线白箱人工确认",
            "模型 Token",
            "IDS-STAGE101-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P1",
            "IDS-V0_1-STAGE101-P1",
            "IDS-STAGE101-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P2",
            "IDS-V0_1-STAGE101-P2",
            "IDS-STAGE101-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P3",
            "IDS-V0_1-STAGE101-P3",
            "IDS-STAGE101-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P4",
            "IDS-V0_1-STAGE101-P4",
            "IDS-STAGE101-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-REVIEW",
            "IDS-V0_1-STAGE101-REVIEW",
            "IDS-STAGE102-P1-GATE",
        )
        successor_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P1",
            "IDS-V0_1-STAGE102-P1",
            "IDS-STAGE102-P2-GATE",
        )
        successor_phase2_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P2",
            "IDS-V0_1-STAGE102-P2",
            "IDS-STAGE102-P3-GATE",
        )
        successor_phase3_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P3",
            "IDS-V0_1-STAGE102-P3",
            "IDS-STAGE102-P4-GATE",
        )
        successor_phase4_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-P4",
            "IDS-V0_1-STAGE102-P4",
            "IDS-STAGE102-REVIEW-GATE",
        )
        successor_review_current = (
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
        legacy_projections = {phase1_current, phase2_current}
        if current in {
            phase4_current,
            review_current,
            successor_current,
            successor_phase2_current,
            successor_phase3_current,
            successor_phase4_current,
            successor_review_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
            stage104_phase1_current,
            stage104_phase2_current,
        }:
            legacy_projections.add(phase3_current)
        if current in {
            review_current,
            successor_current,
            successor_phase2_current,
            successor_phase3_current,
            successor_phase4_current,
            successor_review_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
        }:
            legacy_projections.add(phase4_current)
        if current in {
            successor_current,
            successor_phase2_current,
            successor_phase3_current,
            successor_phase4_current,
            successor_review_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
        }:
            legacy_projections.add(review_current)
        if current in {
            successor_phase2_current,
            successor_phase3_current,
            successor_phase4_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
        }:
            legacy_projections.add(successor_current)
        if current in {
            successor_phase3_current,
            successor_phase4_current,
            successor_review_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
        }:
            legacy_projections.add(successor_phase2_current)
        if current in {
            successor_phase4_current,
            successor_review_current,
            stage103_phase1_current,
            stage103_phase2_current,
            stage103_phase3_current,
            stage103_phase4_current,
            stage103_review_current,
        }:
            legacy_projections.add(successor_phase3_current)
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            legacy_projections,
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(P2_RECEIPT.is_file())
        if current == phase3_current:
            self.assertTrue(is_current_projection)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            for acceptance_id in (
                "ACC-STAGE101-P3-01",
                "ACC-STAGE101-P3-02",
                "ACC-STAGE101-P3-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE101-P3-04"])
            self.assertEqual("IDS-STAGE101-P4-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_RAG_REPRODUCIBILITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertTrue(
                all(value is False for value in receipt["runtime_flags"].values())
            )
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE101-P3-20260825-001", event_ids)
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            for phrase in (
                "stage101_phase3_state:",
                'current_phase_id: "IDS-STAGE101-P3"',
                'next_gate_id: "IDS-STAGE101-P4-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        elif current in {
            phase4_current,
            review_current,
            successor_current,
            successor_phase2_current,
            successor_phase3_current,
            successor_phase4_current,
            successor_review_current,
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
        }:
            self.assertTrue(is_current_projection)
        else:
            self.assertIn(current, {phase1_current, phase2_current})
            self.assertFalse(is_current_projection)


if __name__ == "__main__":
    unittest.main()
