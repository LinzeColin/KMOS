import copy
import importlib.util
import json
from pathlib import Path
import unittest
from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import assert_legacy_or_current_projection


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE099_PHASE3_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_controlled_scenarios.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-099_内部依据与外部增强分离.md"
)
PHASE2_SCOPE = BASE / "STAGE099_PHASE2_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-p2-local.json"
PHASE1_SCOPE = BASE / "STAGE099_PHASE1_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_SEPARATION_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_separation_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE098_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage098-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-p3-local.json"
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


class Stage099InternalEvidenceExternalAugmentationPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(MODULE, "stage099_internal_evidence_scenarios")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_internal_evidence_external_augmentation_phase3_report()

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
        self.assertEqual(
            "ids.stage099.internal_evidence_external_augmentation_separation.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-099", contract["stage"])
        self.assertEqual("IDS-STAGE099-P3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE099-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-099", contract["acceptance_id"])
        self.assertEqual(
            "PHASE3_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE099-P3-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE099-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE099_TASKPACK_STAGE099_PHASE1_PHASE2_AND_STAGE098_REVIEWED_PROMPT_VERSIONING_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ) or field.endswith("can_replace_source_document"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage098_review_required"])
        self.assertTrue(predecessor["stage099_phase1_required"])
        self.assertTrue(predecessor["stage099_phase2_required"])
        self.assertEqual(
            "PASS_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED",
            predecessor["stage099_phase2_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage098_review_evidence_declared",
            "stage099_started",
            "stage099_entry_authorized",
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
            "stage100_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_fixed_control_replay_and_scenario_contract_are_exact(self):
        replay = self.contract["phase2_control_replay_contract"]
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(19, replay["phase2_input_field_count"])
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
            "PASS_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE099-P3-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE099-P4-GATE", report["next_gate"])
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
            set(self.contract["control_view_contract"]["control_view_names"]), set(views)
        )
        for name, view in views.items():
            with self.subTest(view=name):
                self.assertEqual(6, len(view))
                self.assertTrue(all("scenario_id" in item for item in view))
        self.assertEqual(6, report["human_handling_count"])
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
            == "retrieval_document_cannot_override_ids_rule_separation_control"
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
            "evidence_gap_cannot_masquerade_as_internal_experience_separation_control"
        ]
        self.assertIsNone(gap["internal_evidence_ref"])
        self.assertTrue(gap["evidence_gap_present"])
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage099-p2:"))
        external = scenarios[
            "external_augmentation_opinion_preserves_source_type_separation_control"
        ]
        self.assertTrue(external["internal_evidence_present"])
        self.assertFalse(external["evidence_gap_present"])
        self.assertEqual(
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
            external["source_type_separation_state"],
        )
        self.assertEqual(
            "external_augmentation_opinion",
            external["external_augmentation_display_label"],
        )
        self.assertEqual(
            "CONTROL_EXTERNAL_AUGMENTATION_OPINION_IS_DISPLAY_LABEL_ONLY",
            external["display_label_is_not_source_type_state"],
        )
        self.assertEqual(
            "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES",
            external["display_preserves_underlying_source_types_state"],
        )

    def test_high_risk_outputs_keep_human_handling_gate(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        for scenario_id in (
            "high_risk_engineering_advice_requires_whitebox_confirmation_separation_control",
            "contract_commitment_requires_whitebox_confirmation_separation_control",
            "production_writeback_requires_whitebox_confirmation_separation_control",
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
        invalid = self.module.build_internal_evidence_external_augmentation_phase3_report(
            lambda _input: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", invalid["failure_state"])
        self.assertEqual("IDS-STAGE099-P3-GATE", invalid["next_gate"])
        self.assertEqual([], invalid["scenario_results"])

        phase2_module = _load_module(PHASE2_MODULE, "stage099_phase2_for_tamper")
        tampered = copy.deepcopy(
            phase2_module.execute_internal_evidence_external_augmentation_control_slice(
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
        rejected = self.module.build_internal_evidence_external_augmentation_phase3_report(
            lambda _input: tampered
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            "RETRIEVAL_DOCUMENT_CAN_OVERRIDE_IDS_RULE", rejected["failure_state"]
        )
        self.assertEqual([], rejected["scenario_results"])

    def test_runtime_boundaries_and_local_code_remain_closed(self):
        self.assertFalse(self.report["second_authoritative_source_created"])
        self.assertFalse(self.report["persistent_record_created"])
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
            "唯一业务事实权威",
            "reference-only",
            "28 字段",
            "文档内提示词不能覆盖 IDS 规则",
            "不伪装为内部经验",
            "业务线白箱人工处理",
            "模型 Token",
            "IDS-STAGE099-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_IN_MEMORY_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        for field in (
            "preserve_stage099_phase1_and_phase2",
            "preserve_stage098_reviewed_artifacts",
            "preserve_frozen_taskpack",
            "preserve_business_source_authority",
        ):
            with self.subTest(field=field):
                self.assertTrue(rollback[field])
        for field in (
            "business_source_or_runtime_change_allowed",
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
            "IDS-STAGE099",
            "IDS-STAGE099-P3",
            "IDS-V0_1-STAGE099-P3",
            "IDS-STAGE099-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P4",
            "IDS-V0_1-STAGE099-P4",
            "IDS-STAGE099-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-REVIEW",
            "IDS-V0_1-STAGE099-REVIEW",
            "IDS-STAGE100-P1-GATE",
        )
        legacy_projections = (phase3_current, phase4_current, review_current)
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            legacy_projections,
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage099_phase3_state:", roadmap_text)
        if current == phase3_current:
            self.assertEqual(
                "STAGE099_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual(
                "P3 专项验证与异常场景已完成", acceptance_by_id["ACC-STAGE-099"]
            )
            for acceptance_id in (
                "ACC-STAGE099-P3-01",
                "ACC-STAGE099-P3-02",
                "ACC-STAGE099-P3-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE099-P3-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE099-P3-20260825-001", event_ids)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual("IDS-STAGE099-P4-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
            for phrase in (
                "stage099_phase1_state:",
                "stage099_phase2_state:",
                'current_phase_id: "IDS-STAGE099-P3"',
                'next_gate_id: "IDS-STAGE099-P4-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)


if __name__ == "__main__":
    unittest.main()
