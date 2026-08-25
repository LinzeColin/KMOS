import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE098_PHASE3_PROMPT_VERSIONING_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_controlled_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage098_prompt_versioning_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-098_Prompt版本化.md"
)
PHASE2_SCOPE = BASE / "STAGE098_PHASE2_PROMPT_VERSIONING_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_control_slice_contract.json"
)
PHASE2_MODULE = BASE / "index_version_schema" / "stage098_prompt_versioning_control_slice.py"
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage098-p2-local.json"
PHASE1_SCOPE = BASE / "STAGE098_PHASE1_PROMPT_VERSIONING_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage098_prompt_versioning_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage098-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE097_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage097_answer_contract_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage098-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage098PromptVersioningPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("stage098_prompt_scenarios", MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 Stage098 P3 Prompt 版本化异常场景模块")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_prompt_versioning_phase3_report()

    def _phase2_report(self):
        phase2 = self.module._load_phase2_module()
        return phase2.execute_prompt_versioning_control_slice(phase2.build_control_input())

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
            RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual("ids.stage098.prompt_versioning.phase3.v1", contract["schema_version"])
        self.assertEqual("STAGE-098", contract["stage"])
        self.assertEqual("IDS-STAGE098-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE098-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-098", contract["acceptance_id"])
        self.assertEqual(
            "PHASE3_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE098-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE098-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE098_TASKPACK_STAGE098_PHASE1_PHASE2_AND_STAGE097_REVIEWED_ANSWER_CONTRACT_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage097_review_required"])
        self.assertTrue(predecessor["stage098_phase1_required"])
        self.assertTrue(predecessor["stage098_phase2_required"])
        self.assertEqual(
            "PASS_PROMPT_VERSIONING_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage098_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage097_review_evidence_declared",
            "stage098_started",
            "stage098_entry_authorized",
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
            "stage099_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_replay_and_scenario_contract_are_exact(self):
        replay = self.contract["phase2_control_replay_contract"]
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(23, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(41, replay["phase2_projection_field_total_per_request"])
        self.assertEqual(246, replay["phase2_projection_field_total"])
        self.assertEqual(
            list(self.module.P2_CONTROL_SCENARIOS), replay["fixed_phase2_control_scenarios"]
        )
        scenario_contract = self.contract["controlled_scenario_contract"]
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenario_contract["scenario_fields"])
        self.assertEqual(31, scenario_contract["scenario_field_count"])
        self.assertEqual(6, scenario_contract["scenario_count"])
        self.assertEqual(186, scenario_contract["scenario_field_check_count"])
        self.assertEqual(
            [item["scenario_id"] for item in self.module.SCENARIO_DEFINITIONS],
            scenario_contract["fixed_scenarios"],
        )

    def test_accepted_report_has_exact_scenarios_views_and_human_handlings(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE098-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE098-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(246, report["phase2_field_check_count"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(31, report["scenario_field_count"])
        self.assertEqual(186, report["scenario_field_check_count"])
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
        views = report["control_views"]
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(set(self.module.CONTROL_VIEW_FIELDS), set(views))
        for name, fields in self.module.CONTROL_VIEW_FIELDS.items():
            with self.subTest(view=name):
                self.assertEqual(6, len(views[name]))
                self.assertTrue(all(set(item) == set(fields) for item in views[name]))
        self.assertEqual(6, report["human_handling_count"])
        self.assertEqual(6, len(report["human_handlings"]))

    def test_retrieval_document_instruction_cannot_override_ids_rule(self):
        scenario = next(
            item
            for item in self.report["scenario_results"]
            if item["scenario_id"]
            == "retrieval_document_cannot_override_ids_rule_prompt_version_control"
        )
        self.assertEqual(
            "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            scenario["retrieval_document_instruction_precedence_state"],
        )
        self.assertEqual(
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            scenario["prompt_injection_defense_state"],
        )
        self.assertEqual(
            "CONTROL_OUTPUT_WITHHELD_FOR_PROMPT_INJECTION_REVIEW",
            scenario["output_permission_state"],
        )
        self.assertEqual(
            "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
            scenario["final_conclusion_state"],
        )

    def test_evidence_gap_and_external_augmentation_preserve_source_types(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        gap = scenarios[
            "evidence_gap_cannot_masquerade_as_internal_experience_prompt_version_control"
        ]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage098-p2:"))
        external = scenarios[
            "external_augmentation_preserves_source_type_prompt_version_control"
        ]
        self.assertTrue(external["internal_evidence_present"])
        self.assertFalse(external["evidence_gap_present"])
        self.assertEqual(
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
            external["source_type_separation_state"],
        )
        self.assertEqual(
            "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING",
            external["external_augmentation_display_state"],
        )
        self.assertEqual(
            "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES",
            external["display_does_not_replace_source_type_state"],
        )

    def test_high_risk_outputs_never_auto_finalize(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        for scenario_id in (
            "high_risk_engineering_advice_requires_whitebox_confirmation_prompt_version_control",
            "contract_commitment_requires_whitebox_confirmation_prompt_version_control",
            "production_writeback_requires_whitebox_confirmation_prompt_version_control",
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
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )

    def test_invalid_predecessor_and_runtime_signal_fail_closed(self):
        failed = self.module.build_prompt_versioning_phase3_report(lambda _control: [])
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE2_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

        def runtime_signal(_control):
            altered = copy.deepcopy(self._phase2_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_prompt_versioning_phase3_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE2_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

    def test_control_reference_and_semantic_drift_return_specific_failures(self):
        def nonopaque_reference(_control):
            altered = copy.deepcopy(self._phase2_report())
            altered["prompt_versioning_and_answer_contract_binding_control_projections"][0][
                "prompt_version_ref"
            ] = "unscoped-reference"
            return altered

        failed = self.module.build_prompt_versioning_phase3_report(nonopaque_reference)
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])

        cases = (
            (
                "source_type",
                "source_type_and_external_augmentation_display_control_projections",
                0,
                "source_type_separation_state",
                "CONTROL_UNEXPECTED",
                "EXTERNAL_AUGMENTATION_SOURCE_TYPE_LOST",
            ),
            (
                "evidence_gap",
                "source_type_and_external_augmentation_display_control_projections",
                1,
                "internal_evidence_ref",
                ":control:stage098-p2:internal-evidence:gap:reference-only",
                "EVIDENCE_GAP_PRESENTED_AS_INTERNAL_EXPERIENCE",
            ),
            (
                "retrieval_instruction",
                "prompt_injection_and_output_permission_control_projections",
                2,
                "retrieval_document_instruction_precedence_state",
                "CONTROL_DOCUMENT_INSTRUCTION_OVERRIDES_IDS_RULE",
                "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE",
            ),
        )
        for name, collection, index, field, value, expected in cases:
            with self.subTest(name=name):
                altered = copy.deepcopy(self._phase2_report())
                altered[collection][index][field] = value
                failed = self.module.build_prompt_versioning_phase3_report(
                    lambda _control, altered=altered: altered
                )
                self.assertFalse(failed["valid"])
                self.assertEqual(expected, failed["failure_state"])

    def test_high_risk_auto_finalization_is_rejected_and_runtime_stays_closed(self):
        cases = (
            (3, "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED"),
            (4, "CONTRACT_COMMITMENT_AUTO_FINALIZED"),
            (5, "PRODUCTION_WRITEBACK_AUTO_FINALIZED"),
        )
        for index, expected in cases:
            with self.subTest(index=index):
                altered = copy.deepcopy(self._phase2_report())
                altered["prompt_injection_and_output_permission_control_projections"][
                    index
                ]["output_permission_state"] = "CONTROL_AUTOMATIC_FINALIZATION_ALLOWED"
                failed = self.module.build_prompt_versioning_phase3_report(
                    lambda _control, altered=altered: altered
                )
                self.assertFalse(failed["valid"])
                self.assertEqual(expected, failed["failure_state"])

        self.assertFalse(self.report["persistent_record_created"])
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        self.assertTrue(
            all(self.report[field] == 0 for field in self.module.ZERO_COUNTER_FIELDS)
        )
        self.assertFalse(self.report["second_authoritative_source_created"])

    def test_machine_facts_receipt_event_and_roadmap_record_phase3(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-REVIEW",
            "IDS-V0_1-STAGE098-REVIEW",
            "IDS-STAGE099-P1-GATE",
        )
        stage099_phase1_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P1",
            "IDS-V0_1-STAGE099-P1",
            "IDS-STAGE099-P2-GATE",
        )
        stage099_phase2_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P2",
            "IDS-V0_1-STAGE099-P2",
            "IDS-STAGE099-P3-GATE",
        )
        stage099_phase3_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P3",
            "IDS-V0_1-STAGE099-P3",
            "IDS-STAGE099-P4-GATE",
        )

        stage099_phase4_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P4",
            "IDS-V0_1-STAGE099-P4",
            "IDS-STAGE099-REVIEW-GATE",
        )

        stage099_review_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-REVIEW",
            "IDS-V0_1-STAGE099-REVIEW",
            "IDS-STAGE100-P1-GATE",
        )
        self.assertIn(
            current,
            (
                phase3_current,
                phase4_current,
                review_current,
                stage099_phase1_current,
                stage099_phase2_current,
                stage099_phase3_current,
                stage099_phase4_current,
                stage099_review_current,
            ),
        )
        expected = {
            phase3_current: (
                "IDS-V0_1-STAGE098-P3",
                "STAGE098_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                "P3 专项验证已完成",
            ),
            phase4_current: (
                "IDS-V0_1-STAGE098-P4",
                "STAGE098_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                "P4 交付证据已完成",
            ),
            review_current: (
                "IDS-V0_1-STAGE098-REVIEW",
                "STAGE098_PROMPT_VERSIONING_REVIEW_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage099_phase1_current: (
                "IDS-V0_1-STAGE099-P1",
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SEPARATION_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage099_phase2_current: (
                "IDS-V0_1-STAGE099-P2",
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage099_phase3_current: (
                "IDS-V0_1-STAGE099-P3",
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage099_phase4_current: (
                "IDS-V0_1-STAGE099-P4",
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage099_review_current: (
                "IDS-V0_1-STAGE099-REVIEW",
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_REVIEW_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
        }[current]
        self.assertEqual(expected[0], plan["task"])
        self.assertEqual(expected[1], status["evidence_status"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(expected[2], acceptance_by_id["ACC-STAGE-098"])
        for acceptance_id in (
            "ACC-STAGE098-P3-01",
            "ACC-STAGE098-P3-02",
            "ACC-STAGE098-P3-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE098-P3-04"])
        self.assertEqual("IDS-STAGE098-P4-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual(6, receipt["controlled_replay"]["controlled_scenario_count"])
        self.assertEqual(
            186, receipt["controlled_replay"]["controlled_scenario_field_check_count"]
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        self.assertFalse(receipt["stage098_phase4_started"])
        self.assertTrue(receipt["validation"]["final_validation_recorded"])
        self.assertIn("EVT-IDS-V0_1-STAGE098-P3-20260825-001", event_ids)
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for phrase in (
            "stage098_phase1_state:",
            "stage098_phase2_state:",
            "stage098_phase3_state:",
            'current_phase_id: "IDS-STAGE098-P3"',
            'next_gate_id: "IDS-STAGE098-P4-GATE"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)
        if current == review_current:
            for phrase in (
                "stage098_review_state:",
                'current_phase_id: "IDS-STAGE098-REVIEW"',
                'next_gate_id: "IDS-STAGE099-P1-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)


if __name__ == "__main__":
    unittest.main()
