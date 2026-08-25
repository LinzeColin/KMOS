import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE102_PHASE1_DOCUMENT_PROMPT_INJECTION_DEFENSE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-102_文档内提示注入防护.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE101_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
    "rag_answer_structure_ref",
    "document_evidence_ref",
    "document_instruction_candidate_ref",
    "ids_rule_ref",
    "prompt_version_ref",
    "injection_defense_policy_ref",
    "query_ref",
    "index_version_ref",
    "selected_evidence_ref",
    "internal_evidence_ref",
    "external_augmentation_ref",
    "evidence_gap_ref",
    "source_type_ref",
    "model_output_permission_ref",
    "output_classification_ref",
    "human_confirmation_gate_ref",
    "audit_boundary_ref",
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


class Stage102DocumentPromptInjectionDefensePhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage102.document_prompt_injection_defense.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-102", contract["stage"])
        self.assertEqual("IDS-STAGE102-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE102-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-102", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE102-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE102-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE102_TASKPACK_AND_STAGE101_REVIEWED_RAG_REPRODUCIBILITY_CONTROL_ARTIFACTS_ONLY",
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
        self.assertEqual(
            "PASS_REVIEWED_RAG_REPRODUCIBILITY_RUNTIME_DISABLED",
            predecessor["stage101_review_result"],
        )
        self.assertIs(
            predecessor["actual_predecessor_runtime_artifact_read_performed"], False
        )

    def test_document_instruction_control_shape_and_precedence_are_exact(self):
        boundary = self.contract["document_instruction_boundary_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, boundary["future_control_reference_fields"])
        self.assertEqual(17, boundary["future_control_reference_field_count"])
        self.assertEqual(
            set(EXPECTED_CONTROL_FIELDS),
            set(boundary["future_control_reference_contract"]),
        )
        self.assertEqual("UNTRUSTED_EVIDENCE_ONLY_REFERENCE", boundary["document_evidence_state"])
        self.assertEqual(
            "UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            boundary["document_instruction_candidate_state"],
        )
        self.assertEqual("IDS_RULES_PRECEDENCE_FIXED", boundary["ids_rule_precedence_state"])
        self.assertTrue(boundary["control_references_are_labels_only"])
        for field, value in boundary.items():
            if field.startswith("document_content_may_") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_risk_categories_and_failure_closure_are_exact(self):
        risk = self.contract["document_instruction_risk_contract"]
        self.assertEqual(
            EXPECTED_RISK_CATEGORIES,
            risk["future_untrusted_instruction_categories"],
        )
        self.assertEqual(7, risk["future_untrusted_instruction_category_count"])
        self.assertTrue(risk["all_categories_require_ids_rule_precedence"])
        self.assertTrue(risk["all_categories_require_non_executable_evidence_treatment"])
        self.assertTrue(risk["all_categories_require_future_business_line_whitebox_handling"])
        self.assertIs(risk["actual_risk_category_assigned"], False)
        self.assertIs(risk["actual_document_content_classified"], False)
        self.assertIs(risk["actual_document_instruction_suppressed"], False)

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(25, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"],
            len(failures["declared_failure_states"]),
        )
        for field, value in failures.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_source_semantics_and_output_permission_remain_separated(self):
        source = self.contract["source_semantics_contract"]
        self.assertEqual(
            {
                "internal_evidence",
                "external_public_reference",
                "model_reasoning",
                "evidence_gap",
            },
            set(source["underlying_source_types"]),
        )
        self.assertEqual(4, source["underlying_source_type_count"])
        composition = source["external_augmentation_display_composition"]
        self.assertEqual("external_augmentation_opinion", composition["display_label"])
        self.assertEqual(
            {"external_public_reference", "model_reasoning"},
            set(composition["composed_from_source_types"]),
        )
        self.assertTrue(source["document_evidence_is_untrusted_evidence_not_system_instruction"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_displayed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

        permission = self.contract["output_permission_contract"]
        self.assertEqual(5, permission["output_classification_count"])
        self.assertEqual(
            {
                "safe_summary",
                "draft_recommendation",
                "high_risk_engineering_advice",
                "contractual_commitment",
                "production_writeback",
            },
            set(permission["classified_output_types"]),
        )
        self.assertTrue(
            permission[
                "business_line_whitebox_human_confirmation_required_before_final_conclusion"
            ]
        )
        self.assertTrue(permission["document_instruction_may_not_relax_output_permission"])
        self.assertTrue(permission["document_instruction_may_not_bypass_human_confirmation"])
        for field, value in permission.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_runtime_and_protected_surfaces_stay_closed(self):
        for name in (
            "future_runtime_prerequisite_contract",
            "local_code",
            "runtime_boundary",
            "protected_surface_boundary",
        ):
            section = self.contract[name]
            for field, value in section.items():
                if field.endswith("_is_future_authorized_work_only"):
                    with self.subTest(section=name, field=field):
                        self.assertTrue(value)
                elif name == "local_code" and field == "static_contract_only":
                    with self.subTest(section=name, field=field):
                        self.assertTrue(value)
                elif isinstance(value, bool):
                    with self.subTest(section=name, field=field):
                        self.assertIs(value, False)

    def test_stage_boundary_and_rollback_are_fixed(self):
        boundary = self.contract["stage_and_phase_boundary"]
        self.assertTrue(boundary["stage101_review_evidence_declared"])
        self.assertTrue(boundary["stage102_started"])
        self.assertTrue(boundary["stage102_entry_authorized"])
        self.assertTrue(boundary["phase1_started"])
        self.assertTrue(boundary["phase1_completed"])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage103_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], False)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_RAG_REPRODUCIBILITY_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage101_review_evidence"])
        for field, value in rollback.items():
            if field.endswith("_execution_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_current_governance_projection_receipt_and_event_are_exact(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
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
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current},
            status,
            plan,
            ROADMAP,
        )
        if current in {
            phase3_current,
            phase4_current,
            review_current,
            stage103_phase1_current,
            stage103_phase2_current,
        }:
            self.assertTrue(is_current_projection)
        elif current == phase2_current:
            self.assertTrue(is_current_projection)
        else:
            self.assertEqual(phase1_current, current)
            self.assertFalse(is_current_projection)
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_ids = {
            item["id"] for item in acceptance["items"] if isinstance(item, dict)
        }
        self.assertTrue(
            {
                "ACC-STAGE-102",
                "ACC-STAGE102-P1-01",
                "ACC-STAGE102-P1-02",
                "ACC-STAGE102-P1-03",
                "ACC-STAGE102-P1-04",
            }.issubset(acceptance_ids)
        )
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            receipt["result"],
        )
        for value in receipt["runtime_counts"].values():
            self.assertEqual(0, value)
        for value in receipt["runtime_flags"].values():
            self.assertIs(value, False)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE102-P1-20260825-001"
        )
        self.assertEqual("IDS-V0_1-STAGE102-P1", event["task_id"])
        self.assertEqual(
            [
                "ACC-STAGE-102",
                "ACC-STAGE102-P1-01",
                "ACC-STAGE102-P1-02",
                "ACC-STAGE102-P1-03",
                "ACC-STAGE102-P1-04",
            ],
            event["acceptance_ids"],
        )


if __name__ == "__main__":
    unittest.main()
