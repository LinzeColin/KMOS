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
SCOPE = BASE / "STAGE100_PHASE3_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-100_无内部依据策略.md"
)
PHASE2_SCOPE = BASE / "STAGE100_PHASE2_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p2-local.json"
PHASE1_SCOPE = BASE / "STAGE100_PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage100_no_internal_evidence_strategy_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE099_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage100NoInternalEvidenceStrategyPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(MODULE, "stage100_no_internal_evidence_scenarios")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_no_internal_evidence_strategy_phase3_report()

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE2_RECEIPT,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage100.no_internal_evidence_strategy.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-100", contract["stage"])
        self.assertEqual("IDS-STAGE100-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE100-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-100", contract["acceptance_id"])
        self.assertEqual(
            "PHASE3_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE100-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE100-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ) or field.endswith("can_replace_source_document") or field.endswith(
                "can_create_business_fact"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage099_review_required"])
        self.assertTrue(predecessor["stage100_phase1_required"])
        self.assertTrue(predecessor["stage100_phase2_required"])
        self.assertEqual(
            "PASS_IN_MEMORY_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage100_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage099_review_evidence_declared",
            "stage100_started",
            "stage100_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
            "phase3_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_performed",
            "stage101_started",
            "github_upload_allowed",
            "push_allowed",
            "ovh_deployment_allowed",
            "production_runtime_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_phase2_control_replay_and_scenario_shape_are_exact(self):
        replay = self.contract["phase2_control_replay_contract"]
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(21, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(38, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(228, replay["phase2_projection_field_count_total"])
        self.assertEqual(
            list(self.module.P2_CONTROL_SCENARIOS),
            replay["fixed_phase2_control_scenarios"],
        )
        scenario_contract = self.contract["controlled_scenario_contract"]
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenario_contract["scenario_fields"])
        self.assertEqual(29, scenario_contract["scenario_field_count"])
        self.assertEqual(6, scenario_contract["scenario_count"])
        self.assertEqual(174, scenario_contract["scenario_field_check_count"])
        self.assertEqual(
            [item["scenario_id"] for item in self.module.SCENARIO_DEFINITIONS],
            scenario_contract["fixed_scenarios"],
        )

    def test_accepted_report_has_exact_scenarios_views_and_whitebox_handlings(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE100-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE100-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(228, report["phase2_projection_field_count_total"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(29, report["scenario_field_count"])
        self.assertEqual(174, report["scenario_field_check_count"])
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(set(self.module.CONTROL_VIEW_NAMES), set(report["control_views"]))
        for view in report["control_views"].values():
            self.assertEqual(6, len(view))
            self.assertTrue(all("scenario_id" in item for item in view))
        self.assertEqual(6, report["human_handling_count"])
        for handling in report["human_handlings"]:
            with self.subTest(handling=handling["scenario_id"]):
                self.assertTrue(handling["business_line_whitebox_review_required"])
                self.assertFalse(handling["business_line_whitebox_human_approval_recorded"])
                self.assertFalse(handling["automatic_final_conclusion_allowed"])
                self.assertFalse(handling["actual_human_confirmation_performed"])

    def test_retrieval_document_and_evidence_gap_controls_hold(self):
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
        self.assertEqual("CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED", injection["final_conclusion_state"])
        gap = scenarios["evidence_gap_cannot_masquerade_as_internal_experience_control"]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage100-p2:"))
        source_types = scenarios[
            "internal_evidence_external_augmentation_source_types_preserved_control"
        ]
        self.assertEqual(
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
            source_types["source_type_separation_state"],
        )
        self.assertEqual(
            "external_augmentation_opinion",
            source_types["external_augmentation_display_label"],
        )

    def test_high_risk_outputs_and_actual_execution_remain_closed(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        for scenario_id in (
            "high_risk_engineering_advice_requires_whitebox_confirmation_control",
            "contract_commitment_requires_whitebox_confirmation_control",
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
        self.assertEqual(6, self.report["future_model_reasoning_candidate_count"])
        for scenario in self.report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertTrue(scenario["future_model_reasoning_candidate_declared"])
                self.assertFalse(scenario["actual_model_call_performed"])
                self.assertFalse(scenario["actual_answer_publication_performed"])

    def test_tampered_phase2_output_fails_closed(self):
        invalid = self.module.build_no_internal_evidence_strategy_phase3_report(
            lambda _input: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", invalid["failure_state"])
        self.assertEqual([], invalid["scenario_results"])

        phase2_module = _load_module(PHASE2_MODULE, "stage100_phase2_for_tamper")
        tampered = copy.deepcopy(
            phase2_module.execute_no_internal_evidence_strategy_control_slice(
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
        rejected = self.module.build_no_internal_evidence_strategy_phase3_report(
            lambda _input: tampered
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual("PROMPT_INJECTION_DEFENSE_MISSING", rejected["failure_state"])
        self.assertEqual([], rejected["scenario_results"])

    def test_runtime_authority_and_failure_contract_remain_closed(self):
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
        for field, value in self.report["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
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
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE",
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            "HIGH_RISK_OUTPUT_AUTO_FINALIZED",
            "HIGH_RISK_FINAL_CONCLUSION_PUBLISHED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])

    def test_scope_rollback_and_successor_governance_keep_p4_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "二十一字段",
            "二十九字段",
            "提示注入",
            "业务线白箱人工确认",
            "模型 Token",
            "IDS-STAGE100-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE2_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage100_phase1_evidence",
            "preserve_stage100_phase2_evidence",
            "preserve_stage099_review_evidence",
            "preserve_stage099_phase1_to_phase4_evidence",
        ):
            with self.subTest(field=field):
                self.assertTrue(rollback[field])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase3_current = (
            "IDS-STAGE100",
            "IDS-STAGE100-P3",
            "IDS-V0_1-STAGE100-P3",
            "IDS-STAGE100-P4-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE100-P3-01",
            "ACC-STAGE100-P3-02",
            "ACC-STAGE100-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE100-P3-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE100-P3-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE100-P4-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage100_phase3_state:", roadmap_text)
        if current == phase3_current:
            self.assertFalse(is_current_projection)
            self.assertEqual("P3 纯内存专项场景已完成", acceptance_by_id["ACC-STAGE-100"])
        else:
            self.assertTrue(is_current_projection)


if __name__ == "__main__":
    unittest.main()
