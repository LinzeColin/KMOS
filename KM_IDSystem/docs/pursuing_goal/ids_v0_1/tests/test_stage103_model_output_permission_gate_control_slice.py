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
SCOPE = BASE / "STAGE103_PHASE2_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-103_模型输出权限门禁.md"
)
PHASE1_SCOPE = BASE / "STAGE103_PHASE1_MODEL_OUTPUT_PERMISSION_GATE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE102_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "control_scenario",
    "rag_answer_structure_ref",
    "prompt_version_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
    "query_ref",
    "index_version_ref",
    "model_version_ref",
    "selected_evidence_ref",
    "external_public_reference_ref",
    "model_reasoning_ref",
    "output_category",
    "document_instruction_evidence_state",
    "ids_rule_precedence_state",
    "injection_defense_state",
    "source_type_separation_state",
    "output_permission_state",
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
        "stage103_model_output_permission_gate_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage103 P2 模型输出权限门禁控制切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage103ModelOutputPermissionGatePhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_model_output_permission_gate_control_slice(
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
            "ids.stage103.model_output_permission_gate.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-103", contract["stage"])
        self.assertEqual("IDS-STAGE103-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE103-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-103", contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE103-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE103-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE103_TASKPACK_STAGE103_PHASE1_AND_STAGE102_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage102_review_required"])
        self.assertTrue(predecessor["stage103_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            predecessor["stage102_review_result"],
        )
        self.assertEqual(
            "PHASE1_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            predecessor["stage103_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage102_review_evidence_declared",
            "stage103_started",
            "stage103_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage102_review_evidence_declared",
                "stage103_started",
                "stage103_entry_authorized",
                "phase1_completed",
                "phase2_started",
                "phase2_completed",
            }:
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_fixed_control_input_covers_output_categories_and_record_shape(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(EXPECTED_CONTROL_FIELDS, list(self.module.INPUT_FIELDS))
        self.assertEqual(26, len(self.module.INPUT_FIELDS))
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
                self.assertTrue(required_record_fields.issubset(request))
                for field, value in request.items():
                    if field == "control_scenario":
                        continue
                    if value is None:
                        self.assertIn(field, {"internal_evidence_ref", "evidence_gap_ref"})
                        continue
                    self.assertTrue(
                        value.startswith(":control:stage103-p2:")
                        or value.startswith("CONTROL_"),
                        field,
                    )
                for field in required_record_fields:
                    self.assertTrue(request[field].startswith(":control:stage103-p2:"))
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
            "PASS_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE_RUNTIME_DISABLED",
            result["execution_state"],
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(46, result["control_projection_field_total_per_request"])
        self.assertEqual(230, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(5, len(projections))
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_reproducibility_and_document_evidence_defense_are_fixed(self):
        answer_projections = self.result[
            "answer_contract_and_reproducibility_control_projections"
        ]
        defense_projections = self.result[
            "document_evidence_and_output_permission_defense_control_projections"
        ]
        self.assertEqual(5, len(answer_projections))
        self.assertEqual(5, len(defense_projections))
        for answer, defense in zip(answer_projections, defense_projections):
            with self.subTest(answer=answer["output_classification_ref"]):
                self.assertTrue(
                    answer[
                        "stage103_phase1_model_output_permission_gate_contract_ref"
                    ].endswith("reference-only")
                )
                self.assertTrue(
                    answer["stage102_review_control_ref"].endswith("reference-only")
                )
                self.assertEqual(
                    "CONTROL_REFERENCE_ONLY_IN_MEMORY", answer["control_slice_state"]
                )
                for field in self.module.REPRODUCIBILITY_RECORD_FIELDS:
                    self.assertTrue(answer[field].startswith(":control:stage103-p2:"))
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
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
                    defense["document_instruction_may_not_override_ids_rule_state"],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_RELAX_OUTPUT_PERMISSION",
                    defense[
                        "document_instruction_may_not_relax_output_permission_state"
                    ],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_BYPASS_HUMAN_CONFIRMATION",
                    defense[
                        "document_instruction_may_not_bypass_human_confirmation_state"
                    ],
                )

    def test_source_semantics_and_output_permission_remain_separated(self):
        source_projections = self.result[
            "source_semantics_and_external_augmentation_display_control_projections"
        ]
        output_projections = self.result[
            "output_permission_and_whitebox_gate_control_projections"
        ]
        observed_output_categories = set()
        evidence_gap_projection_count = 0
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
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    output["final_conclusion_state"],
                )
                self.assertEqual(
                    "CONTROL_AUTOMATIC_PUBLICATION_DISABLED",
                    output["automatic_publication_state"],
                )
                self.assertEqual(
                    "CONTROL_BUSINESS_USE_REQUIRES_WHITEBOX_OWNER",
                    output["business_use_state"],
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
        self.assertEqual(1, evidence_gap_projection_count)
        self.assertEqual(EXPECTED_OUTPUT_CATEGORIES, observed_output_categories)

    def test_non_fixed_input_is_rejected_without_projection_or_side_effect(self):
        mutated = copy.deepcopy(self.control_input)
        mutated[self.module.CONTROL_FIELDS[0]][0]["ids_rule_ref"] = (
            ":control:stage103-p2:changed:reference-only"
        )
        result = self.module.execute_model_output_permission_gate_control_slice(
            mutated
        )
        self.assertFalse(result["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE",
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
            "PASS_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE103-P2-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE103-P3-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )

        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "reference-only",
            "5",
            "26",
            "46",
            "230",
            "IDS-STAGE103-P3-GATE",
            "模型 Token",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P1",
            "IDS-V0_1-STAGE103-P1",
            "IDS-STAGE103-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P2",
            "IDS-V0_1-STAGE103-P2",
            "IDS-STAGE103-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P3",
            "IDS-V0_1-STAGE103-P3",
            "IDS-STAGE103-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P4",
            "IDS-V0_1-STAGE103-P4",
            "IDS-STAGE103-REVIEW-GATE",
        )
        review_current = (
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
                "ACC-STAGE103-P2-01",
                "ACC-STAGE103-P2-02",
                "ACC-STAGE103-P2-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE103-P2-04"])
        elif current == phase1_current:
            self.assertFalse(is_current_projection)
        elif current == phase3_current:
            self.assertTrue(is_current_projection)
        elif current == review_current:
            self.assertTrue(is_current_projection)
        elif current in {
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
            stage106_phase3_current,
            stage106_phase4_current,
            stage106_review_current,
            stage107_phase1_current,
            stage107_phase2_current,
            stage107_phase3_current,
            stage107_phase4_current,
        }:
            self.assertIn(
                current,
                {
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
                    stage106_phase3_current,
                    stage106_phase4_current,
                    stage106_review_current,
                    stage107_phase1_current,
                    stage107_phase2_current,
                    stage107_phase3_current,
                    stage107_phase4_current,
                },
            )
            self.assertTrue(is_current_projection)
        elif is_current_projection:
            self.assertTrue(is_current_projection)
        else:
            self.assertIn(current, {phase4_current, stage106_review_current})
            self.assertTrue(is_current_projection)

        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE103-P2-20260825-001", event_ids)


if __name__ == "__main__":
    unittest.main()
