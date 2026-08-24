import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE097_PHASE3_ANSWER_CONTRACT_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage097_answer_contract_controlled_scenarios_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage097_answer_contract_controlled_scenarios.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)
PHASE2_SCOPE = BASE / "STAGE097_PHASE2_ANSWER_CONTRACT_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage097_answer_contract_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage097_answer_contract_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p2-local.json"
PHASE1_SCOPE = BASE / "STAGE097_PHASE1_ANSWER_CONTRACT_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE096_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage096-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage097AnswerContractPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("stage097_answer_scenarios", MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 Stage097 P3 回答合同异常场景模块")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_answer_contract_phase3_report()

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

    def test_identity_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual("ids.stage097.answer_contract.phase3.v1", contract["schema_version"])
        self.assertEqual("STAGE-097", contract["stage"])
        self.assertEqual("IDS-STAGE097-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE097-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-097", contract["acceptance_id"])
        self.assertEqual(
            "PHASE3_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE097-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE097-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE097_TASKPACK_AND_STAGE097_PHASE1_PHASE2_STAGE096_REVIEWED_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage096_review_required"])
        self.assertTrue(predecessor["stage097_phase1_required"])
        self.assertTrue(predecessor["stage097_phase2_required"])
        self.assertEqual(
            "PASS_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage097_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage096_review_evidence_declared",
            "stage097_started",
            "stage097_entry_authorized",
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
            "stage098_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_replay_and_scenario_contract_are_exact(self):
        replay = self.contract["phase2_control_replay_contract"]
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(20, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(35, replay["phase2_projection_field_total_per_request"])
        self.assertEqual(210, replay["phase2_projection_field_total"])
        self.assertEqual(
            list(self.module.P2_CONTROL_SCENARIOS),
            replay["fixed_phase2_control_scenarios"],
        )
        scenario_contract = self.contract["controlled_scenario_contract"]
        self.assertEqual(list(self.module.SCENARIO_FIELDS), scenario_contract["scenario_fields"])
        self.assertEqual(28, scenario_contract["scenario_field_count"])
        self.assertEqual(6, scenario_contract["scenario_count"])
        self.assertEqual(168, scenario_contract["scenario_field_check_count"])
        self.assertEqual(
            [item["scenario_id"] for item in self.module.SCENARIO_DEFINITIONS],
            scenario_contract["fixed_scenarios"],
        )

    def test_accepted_report_has_exact_scenarios_views_and_human_handlings(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE097-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE097-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(210, report["phase2_field_check_count"])
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(28, report["scenario_field_count"])
        self.assertEqual(168, report["scenario_field_check_count"])
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
        self.assertEqual(
            set(self.contract["control_view_contract"]["control_view_names"]),
            set(views),
        )
        for name, view in views.items():
            with self.subTest(view=name):
                self.assertEqual(6, len(view))
                self.assertTrue(all("scenario_id" in item for item in view))
        self.assertEqual(6, report["human_handling_count"])
        self.assertEqual(6, len(report["human_handlings"]))
        for handling in report["human_handlings"]:
            with self.subTest(handling=handling["scenario_id"]):
                self.assertTrue(handling["business_line_whitebox_review_required"])
                self.assertFalse(
                    handling["business_line_whitebox_human_approval_recorded"]
                )
                self.assertFalse(handling["automatic_final_conclusion_allowed"])
                self.assertFalse(handling["actual_human_confirmation_performed"])

    def test_retrieval_document_instruction_cannot_override_ids_rule(self):
        scenario = next(
            item
            for item in self.report["scenario_results"]
            if item["scenario_id"]
            == "retrieval_document_cannot_override_ids_rule_control"
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
        scenarios = {
            item["scenario_id"]: item for item in self.report["scenario_results"]
        }
        gap = scenarios[
            "evidence_gap_cannot_masquerade_as_internal_experience_control"
        ]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage097-p2:"))
        external = scenarios["external_augmentation_preserves_source_type_control"]
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
        scenarios = {
            item["scenario_id"]: item for item in self.report["scenario_results"]
        }
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
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )

    def test_invalid_or_tampered_phase2_output_fails_closed(self):
        invalid = self.module.build_answer_contract_phase3_report(lambda _input: {})
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", invalid["failure_state"])
        self.assertEqual("IDS-STAGE097-P3-GATE", invalid["next_gate"])
        self.assertEqual([], invalid["scenario_results"])

        spec = importlib.util.spec_from_file_location("stage097_phase2_for_tamper", PHASE2_MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 Stage097 P2 受控切片用于异常场景验证")
        phase2_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phase2_module)
        tampered = copy.deepcopy(
            phase2_module.execute_answer_contract_control_slice(
                phase2_module.build_control_input()
            )
        )
        injection_index = phase2_module.CONTROL_SCENARIOS.index(
            "retrieval_document_instruction_rejected_reference_only"
        )
        tampered["prompt_injection_and_output_permission_control_projections"][
            injection_index
        ]["prompt_injection_defense_state"] = "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
        rejected = self.module.build_answer_contract_phase3_report(
            lambda _input: tampered
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE", rejected["failure_state"]
        )
        self.assertEqual([], rejected["scenario_results"])

    def test_runtime_boundaries_and_local_code_remain_closed(self):
        self.assertFalse(self.report["second_authoritative_source_created"])
        for field, value in self.report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
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

    def test_scope_rollback_and_current_governance_keep_phase4_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "28 个字段",
            "提示词不能覆盖 IDS 规则",
            "不伪装为内部经验",
            "业务线白箱人工处理",
            "模型 Token",
            "IDS-STAGE097-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage097_phase1_evidence",
            "preserve_stage097_phase2_evidence",
            "preserve_stage096_review_evidence",
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
            "IDS-STAGE097",
            "IDS-STAGE097-P3",
            "IDS-V0_1-STAGE097-P3",
            "IDS-STAGE097-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-REVIEW",
            "IDS-V0_1-STAGE097-REVIEW",
            "IDS-STAGE098-P1-GATE",
        )
        stage098_phase1_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P1",
            "IDS-V0_1-STAGE098-P1",
            "IDS-STAGE098-P2-GATE",
        )
        stage098_phase2_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P2",
            "IDS-V0_1-STAGE098-P2",
            "IDS-STAGE098-P3-GATE",
        )
        stage098_phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        stage098_phase4_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        stage098_review_current = (
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
        self.assertIn(
            current,
            (
                phase3_current,
                phase4_current,
                review_current,
                stage098_phase1_current,
                stage098_phase2_current,
                stage098_phase3_current,
                stage098_phase4_current,
                stage098_review_current,
                stage099_phase1_current,
                stage099_phase2_current,
                stage099_phase3_current,
                stage099_phase4_current,
            ),
        )
        self.assertEqual(status["task"], plan["task"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage097_phase3_state:", roadmap_text)
        if current == phase3_current:
            self.assertEqual(
                "STAGE097_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual(
                "P3 异常场景验证已完成", acceptance_by_id["ACC-STAGE-097"]
            )
            for acceptance_id in (
                "ACC-STAGE097-P3-01",
                "ACC-STAGE097-P3-02",
                "ACC-STAGE097-P3-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE097-P3-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE097-P3-20260825-001", event_ids)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual("IDS-STAGE097-P4-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        elif current == phase4_current:
            self.assertEqual(
                "STAGE097_ANSWER_CONTRACT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("P4 交付证据已完成", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_phase4_state:", roadmap_text)
        elif current == review_current:
            self.assertEqual(
                "STAGE097_ANSWER_CONTRACT_REVIEW_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
        elif current == stage098_phase1_current:
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTRACT_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
        elif current == stage098_phase2_current:
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
        elif current == stage098_phase3_current:
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
        elif current == stage098_phase4_current:
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
        elif current == stage098_review_current:
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_REVIEW_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn("stage098_review_state:", roadmap_text)
        elif current == stage099_phase1_current:
            self.assertEqual(
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SEPARATION_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn("stage098_review_state:", roadmap_text)
            self.assertIn("stage099_phase1_state:", roadmap_text)
        elif current == stage099_phase2_current:
            self.assertEqual(
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn("stage098_review_state:", roadmap_text)
            self.assertIn("stage099_phase1_state:", roadmap_text)
            self.assertIn("stage099_phase2_state:", roadmap_text)
        elif current == stage099_phase3_current:
            self.assertEqual(
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn("stage098_review_state:", roadmap_text)
            self.assertIn("stage099_phase1_state:", roadmap_text)
            self.assertIn("stage099_phase2_state:", roadmap_text)
            self.assertIn("stage099_phase3_state:", roadmap_text)


if __name__ == "__main__":
    unittest.main()
