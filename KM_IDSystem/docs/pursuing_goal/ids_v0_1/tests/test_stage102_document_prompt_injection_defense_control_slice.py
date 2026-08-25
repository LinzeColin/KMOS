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
SCOPE = BASE / "STAGE102_PHASE2_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_control_slice.py"
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
PREDECESSOR_REVIEW = BASE / "STAGE101_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "control_scenario",
    "untrusted_instruction_category",
    "rag_answer_structure_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "prompt_version_ref",
    "injection_defense_policy_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
    "output_category",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "source_type_separation_state",
    "output_permission_state",
]
EXPECTED_RISK_CATEGORIES = [
    "ids_rule_override_attempt",
    "system_instruction_or_role_redefinition_attempt",
    "tool_or_external_action_authorization_attempt",
    "prompt_or_model_configuration_override_attempt",
    "output_permission_or_human_gate_bypass_attempt",
    "publication_or_production_writeback_bypass_attempt",
    "source_or_secret_access_request",
]
EXPECTED_OUTPUT_CATEGORIES = {
    "safe_summary",
    "draft_recommendation",
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}
HUMAN_CONFIRMATION_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage102_document_prompt_injection_defense_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage102 P2 文档提示注入防护控制切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage102DocumentPromptInjectionDefensePhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_document_prompt_injection_defense_control_slice(
            cls.control_input
        )

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
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

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage102.document_prompt_injection_defense.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-102", contract["stage"])
        self.assertEqual("IDS-STAGE102-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE102-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-102", contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE102-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE102-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE102_TASKPACK_STAGE102_PHASE1_AND_STAGE101_REVIEWED_RAG_REPRODUCIBILITY_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage101_review_required"])
        self.assertTrue(predecessor["stage102_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_RAG_REPRODUCIBILITY_RUNTIME_DISABLED",
            predecessor["stage101_review_result"],
        )
        self.assertEqual(
            "PHASE1_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            predecessor["stage102_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage101_review_evidence_declared",
            "stage102_started",
            "stage102_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage101_review_evidence_declared",
                "stage102_started",
                "stage102_entry_authorized",
                "phase1_completed",
                "phase2_started",
                "phase2_completed",
            }:
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_fixed_control_input_preserves_seven_categories_and_record_shape(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(7, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(EXPECTED_CONTROL_FIELDS, list(self.module.INPUT_FIELDS))
        self.assertEqual(28, len(self.module.INPUT_FIELDS))
        self.assertEqual(
            EXPECTED_RISK_CATEGORIES,
            [
                self.module.CONTROL_SCENARIO_CONFIGURATION[scenario][
                    "untrusted_instruction_category"
                ]
                for scenario in self.module.CONTROL_SCENARIOS
            ],
        )
        required_record_fields = {
            "query_ref",
            "index_version_ref",
            "prompt_version_ref",
            "model_version_ref",
            "selected_evidence_ref",
        }
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                self.assertIn(
                    request["untrusted_instruction_category"],
                    EXPECTED_RISK_CATEGORIES,
                )
                self.assertTrue(required_record_fields.issubset(request))
                for field, value in request.items():
                    if field in {"control_scenario", "untrusted_instruction_category"}:
                        continue
                    if value is None:
                        self.assertIn(field, {"internal_evidence_ref", "evidence_gap_ref"})
                        continue
                    self.assertTrue(
                        value.startswith(":control:stage102-p2:")
                        or value.startswith("CONTROL_"),
                        field,
                    )
                for field in required_record_fields:
                    self.assertTrue(request[field].startswith(":control:stage102-p2:"))
                self.assertEqual(
                    "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
                    request["document_instruction_evidence_state"],
                )
                self.assertEqual(
                    "CONTROL_IDS_RULES_PREVAIL",
                    request["ids_rule_precedence_state"],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
                    request["injection_defense_state"],
                )
        self.assertEqual(
            {
                "CONTROL_OUTPUT_CATEGORY_SAFE_SUMMARY",
                "CONTROL_OUTPUT_CATEGORY_DRAFT_RECOMMENDATION",
                "CONTROL_OUTPUT_CATEGORY_HIGH_RISK_ENGINEERING_ADVICE",
                "CONTROL_OUTPUT_CATEGORY_CONTRACTUAL_COMMITMENT",
                "CONTROL_OUTPUT_CATEGORY_PRODUCTION_WRITEBACK",
            },
            {request["output_category"] for request in requests},
        )

    def test_accepted_control_slice_projects_exact_shape(self):
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "PASS_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
            result["execution_state"],
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(7, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(50, result["control_projection_field_total_per_request"])
        self.assertEqual(350, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(7, len(projections))
                self.assertEqual(7, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_reproducibility_and_document_instruction_defense_are_fixed(self):
        answer_projections = self.result[
            "answer_contract_and_reproducibility_control_projections"
        ]
        defense_projections = self.result["document_instruction_defense_control_projections"]
        self.assertEqual(7, len(answer_projections))
        self.assertEqual(7, len(defense_projections))
        observed_categories = set()
        for answer, defense in zip(answer_projections, defense_projections):
            with self.subTest(category=defense["untrusted_instruction_category"]):
                self.assertTrue(
                    answer[
                        "stage102_phase1_document_prompt_injection_defense_contract_ref"
                    ].endswith("reference-only")
                )
                self.assertTrue(
                    answer["stage101_review_control_ref"].endswith("reference-only")
                )
                self.assertEqual(
                    "CONTROL_REFERENCE_ONLY_IN_MEMORY", answer["control_slice_state"]
                )
                for field in self.module.REPRODUCIBILITY_RECORD_FIELDS:
                    self.assertTrue(answer[field].startswith(":control:stage102-p2:"))
                observed_categories.add(defense["untrusted_instruction_category"])
                self.assertEqual(
                    "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
                    defense["document_instruction_evidence_state"],
                )
                self.assertEqual("CONTROL_IDS_RULES_PREVAIL", defense["ids_rule_precedence_state"])
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
                    defense["injection_defense_state"],
                )
                self.assertEqual(
                    "CONTROL_NO_TOOL_OR_EXTERNAL_ACTION_AUTHORIZED",
                    defense["tool_or_external_action_authorization_state"],
                )
                self.assertEqual(
                    "CONTROL_NO_PROMPT_OR_MODEL_OVERRIDE",
                    defense["prompt_or_model_override_state"],
                )
                self.assertEqual(
                    "CONTROL_NO_PUBLICATION_OR_WRITEBACK",
                    defense["publication_or_writeback_state"],
                )
        self.assertEqual(set(EXPECTED_RISK_CATEGORIES), observed_categories)

    def test_source_semantics_and_output_permission_remain_separated(self):
        source_projections = self.result[
            "source_semantics_and_external_augmentation_display_control_projections"
        ]
        output_projections = self.result[
            "output_permission_and_whitebox_gate_control_projections"
        ]
        self.assertEqual(7, len(source_projections))
        self.assertEqual(7, len(output_projections))
        evidence_gap_projection_count = 0
        observed_output_categories = set()
        for source, output in zip(source_projections, output_projections):
            output_category = output["output_category"].removeprefix(
                "CONTROL_OUTPUT_CATEGORY_"
            ).lower()
            with self.subTest(output_category=output_category):
                self.assertEqual(
                    "external_augmentation_opinion",
                    source["external_augmentation_display_label"],
                )
                self.assertEqual(
                    "internal_evidence", source["internal_evidence_source_type"]
                )
                self.assertEqual(
                    "external_public_reference",
                    source["external_public_reference_source_type"],
                )
                self.assertEqual("model_reasoning", source["model_reasoning_source_type"])
                self.assertEqual("evidence_gap", source["evidence_gap_source_type"])
                self.assertEqual(
                    "CONTROL_DISPLAY_LABEL_IS_NOT_SOURCE_TYPE",
                    source["display_label_is_not_source_type_state"],
                )
                self.assertEqual(
                    "CONTROL_DISPLAY_PRESERVES_UNDERLYING_SOURCE_TYPES",
                    source["display_preserves_underlying_source_types_state"],
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP",
                    source["display_does_not_close_evidence_gap_state"],
                )
                if source["evidence_gap_ref"] is not None:
                    evidence_gap_projection_count += 1
                observed_output_categories.add(output_category)
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_RELAX_OUTPUT_PERMISSION",
                    output[
                        "document_instruction_may_not_relax_output_permission_state"
                    ],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_BYPASS_HUMAN_CONFIRMATION",
                    output[
                        "document_instruction_may_not_bypass_human_confirmation_state"
                    ],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    output["final_conclusion_state"],
                )
                self.assertEqual(
                    "CONTROL_AUTOMATIC_PUBLICATION_DISABLED",
                    output["automatic_publication_state"],
                )
                if output_category in HUMAN_CONFIRMATION_CATEGORIES:
                    self.assertEqual(
                        "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED",
                        output["human_confirmation_state"],
                    )
                else:
                    self.assertEqual(
                        "CONTROL_HUMAN_CONFIRMATION_NOT_EXECUTED",
                        output["human_confirmation_state"],
                    )
        self.assertEqual(2, evidence_gap_projection_count)
        self.assertEqual(EXPECTED_OUTPUT_CATEGORIES, observed_output_categories)

    def test_non_fixed_input_is_rejected_without_projection_or_side_effect(self):
        mutated = copy.deepcopy(self.control_input)
        mutated[self.module.CONTROL_FIELDS[0]][0]["ids_rule_ref"] = (
            ":control:stage102-p2:changed:reference-only"
        )
        result = self.module.execute_document_prompt_injection_defense_control_slice(
            mutated
        )
        self.assertFalse(result["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", result["failure_state"])
        self.assertEqual(0, result["control_input_count"])
        self.assertEqual(0, result["control_projection_field_total"])
        self.assertFalse(result["persistent_record_created"])
        self.assertTrue(all(value is False for value in result["runtime_boundary"].values()))
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                self.assertEqual([], result[f"{prefix}_control_projections"])
                self.assertEqual(0, result[f"{prefix}_control_projection_count"])

    def test_runtime_and_protected_surfaces_stay_closed(self):
        self.assertTrue(
            all(value == 0 for key, value in self.result.items() if key.startswith("actual_"))
        )
        self.assertFalse(self.result["persistent_record_created"])
        self.assertTrue(
            all(value is False for value in self.result["runtime_boundary"].values())
        )
        for section_name in (
            "runtime_boundary",
            "protected_surface_boundary",
        ):
            for field, value in self.contract[section_name].items():
                with self.subTest(section=section_name, field=field):
                    self.assertIs(value, False)
        for section_name in (
            "future_runtime_prerequisite_contract",
            "local_code",
        ):
            for field, value in self.contract[section_name].items():
                if field in {
                    "control_slice_module_created",
                    "control_slice_is_pure_memory",
                }:
                    self.assertIs(value, True)
                else:
                    with self.subTest(section=section_name, field=field):
                        self.assertIs(value, False)

    def test_receipt_scope_and_governance_project_phase2_only(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE102-P2-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE102-P3-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )

        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "reference-only",
            "7",
            "28",
            "50",
            "350",
            "IDS-STAGE102-P3-GATE",
            "模型 Token",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
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
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current == phase2_current:
            self.assertTrue(is_current_projection)
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            for acceptance_id in (
                "ACC-STAGE102-P2-01",
                "ACC-STAGE102-P2-02",
                "ACC-STAGE102-P2-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE102-P2-04"])
        elif current == phase1_current:
            self.assertFalse(is_current_projection)
        else:
            self.assertTrue(is_current_projection)

        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE102-P2-20260825-001", event_ids)


if __name__ == "__main__":
    unittest.main()
