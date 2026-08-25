import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE104_PHASE1_RAG_NEGATIVE_TEST_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage104_rag_negative_testing_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-104_RAG负向测试.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE103_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_CONTROL_FIELDS = [
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
]

EXPECTED_OUTPUT_TYPES = {
    "safe_summary",
    "draft_recommendation",
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}

EXPECTED_NEGATIVE_TEST_CASES = [
    "DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
    "EVIDENCE_GAP_CANNOT_PRESENT_AS_INTERNAL_EXPERIENCE",
    "HIGH_RISK_ENGINEERING_ADVICE_CANNOT_AUTO_FINALIZE",
    "CONTRACTUAL_COMMITMENT_CANNOT_AUTO_FINALIZE",
    "PRODUCTION_WRITEBACK_CANNOT_AUTO_FINALIZE",
]


class Stage104RagNegativeTestingPhase1Tests(unittest.TestCase):
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
            "ids.stage104.rag_negative_testing.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-104", contract["stage"])
        self.assertEqual("IDS-STAGE104-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE104-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-104", contract["acceptance_id"])
        self.assertEqual(
            "RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE104-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE104-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE104_TASKPACK_AND_STAGE103_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        for field in (
            "stage104_contract_can_replace_source_document",
            "stage104_contract_can_replace_business_line_judgment",
            "second_authoritative_source_created",
            "actual_source_document_read_performed",
            "actual_business_line_decision_performed",
        ):
            with self.subTest(field=field):
                self.assertIs(authority[field], False)
        predecessor = contract["predecessor_review_contract"]
        self.assertTrue(predecessor["stage103_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            predecessor["stage103_review_result"],
        )
        self.assertIs(
            predecessor["actual_predecessor_runtime_artifact_read_performed"], False
        )

    def test_answer_reference_shape_prompt_boundary_and_negative_case_labels(self):
        controls = self.contract["future_rag_control_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, controls["future_control_reference_fields"])
        self.assertEqual(13, controls["future_control_reference_field_count"])
        self.assertEqual(
            set(EXPECTED_CONTROL_FIELDS),
            set(controls["future_control_reference_contract"]),
        )
        self.assertTrue(controls["control_references_are_labels_only"])
        answer = controls["answer_structure_contract"]
        self.assertEqual(5, answer["required_future_section_count"])
        self.assertEqual(
            answer["required_future_section_count"],
            len(answer["required_future_sections"]),
        )
        for field, value in answer.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        prompt = controls["prompt_version_contract"]
        self.assertTrue(prompt["prompt_version_is_future_control_reference_only"])
        for field, value in prompt.items():
            if field.endswith("_performed") or field.endswith("_selected"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        negative = self.contract["negative_test_contract"]
        self.assertEqual(
            EXPECTED_NEGATIVE_TEST_CASES, negative["future_negative_test_case_ids"]
        )
        self.assertEqual(5, negative["future_negative_test_case_count"])
        self.assertEqual(
            set(EXPECTED_NEGATIVE_TEST_CASES),
            set(negative["negative_test_case_contract"]),
        )
        self.assertTrue(negative["negative_test_execution_is_future_authorized_work_only"])
        for field, value in negative.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_document_evidence_and_source_semantics_remain_separated(self):
        source = self.contract["document_and_source_semantics_contract"]
        self.assertEqual(
            "UNTRUSTED_EVIDENCE_ONLY_REFERENCE", source["document_evidence_state"]
        )
        self.assertEqual(
            "UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            source["document_instruction_candidate_state"],
        )
        self.assertEqual("IDS_RULES_PRECEDENCE_FIXED", source["ids_rule_precedence_state"])
        for field in (
            "retrieval_document_is_evidence_not_system_instruction",
            "retrieval_document_cannot_override_ids_rule",
            "retrieval_document_cannot_relax_output_permission",
            "retrieval_document_cannot_bypass_human_confirmation",
        ):
            with self.subTest(field=field):
                self.assertTrue(source[field])
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
        no_internal = source["no_internal_evidence_strategy"]
        for field, value in no_internal.items():
            with self.subTest(field=field):
                self.assertIs(value, not field.startswith("actual_"))

    def test_output_permission_and_human_confirmation_gate_are_exact(self):
        permission = self.contract["output_permission_contract"]
        self.assertEqual(
            "high_risk_engineering_advice",
            permission["taskpack_high_risk_advice_controlled_label"],
        )
        self.assertEqual(5, permission["output_classification_count"])
        self.assertEqual(EXPECTED_OUTPUT_TYPES, set(permission["classified_output_types"]))
        self.assertTrue(
            permission[
                "business_line_whitebox_human_confirmation_required_before_final_conclusion"
            ]
        )
        for field, value in permission.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        confirmation = self.contract["human_confirmation_contract"]
        for field, value in confirmation.items():
            with self.subTest(field=field):
                self.assertIs(value, not field.startswith("actual_"))

    def test_runtime_and_protected_surfaces_stay_closed(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field, value in prerequisite.items():
            with self.subTest(field=field):
                self.assertIs(
                    value, field.endswith("_is_future_authorized_work_only")
                )
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertIs(value, False)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertIs(value, False)

    def test_failure_feedback_rollback_and_stage_boundary_are_explicit(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(19, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "DOCUMENT_INSTRUCTION_OVERRIDES_IDS_RULE",
            "EVIDENCE_GAP_PRESENTED_AS_INTERNAL_EXPERIENCE",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE104_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(failure_state=failure_state):
                self.assertIn(failure_state, failures["declared_failure_states"])
        for field, value in failures.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        feedback = self.contract["chinese_feedback_contract"]
        self.assertEqual(4, feedback["feedback_count"])
        self.assertEqual(4, len(feedback["feedbacks"]))
        self.assertIs(feedback["actual_user_feedback_emitted"], False)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage103_review_evidence_declared",
            "stage104_started",
            "stage104_entry_authorized",
            "phase1_started",
            "phase1_completed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], True)
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage105_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], False)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage103_review_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_current_governance_projection_receipt_and_event_are_exact(self):
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "检索文档永远只是 evidence",
            "五个未来负向测试标签",
            "IDS-STAGE104-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        stage104_phase1_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P1",
            "IDS-V0_1-STAGE104-P1",
            "IDS-STAGE104-P2-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {stage104_phase1_current},
            status,
            plan,
            ROADMAP,
        )
        if current == stage104_phase1_current:
            self.assertFalse(is_current_projection)
            self.assertEqual(
                "RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE104-P2-GATE", plan["stop_condition"])
        else:
            self.assertTrue(is_current_projection)
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == stage104_phase1_current:
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-104"])
        for acceptance_id in (
            "ACC-STAGE104-P1-01",
            "ACC-STAGE104-P1-02",
            "ACC-STAGE104-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE104-P1-04"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED", receipt["result"]
        )
        self.assertEqual("IDS-STAGE104-P2-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        self.assertTrue(
            receipt["checkpoint_record"]["user_authorized_recovery_checkpoint_pushed"]
        )
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE104-P1-20260826-001"
        )
        self.assertEqual("IDS-V0_1-STAGE104-P1", event["task_id"])
        self.assertEqual(
            [
                "ACC-STAGE-104",
                "ACC-STAGE104-P1-01",
                "ACC-STAGE104-P1-02",
                "ACC-STAGE104-P1-03",
                "ACC-STAGE104-P1-04",
            ],
            event["acceptance_ids"],
        )


if __name__ == "__main__":
    unittest.main()
