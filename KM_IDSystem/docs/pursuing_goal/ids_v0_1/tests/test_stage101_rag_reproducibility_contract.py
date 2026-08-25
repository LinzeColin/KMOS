import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE101_PHASE1_RAG_REPRODUCIBILITY_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage101_rag_reproducibility_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-101_RAG可复现.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE100_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage101RagReproducibilityPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.predecessor = json.loads(PREDECESSOR_CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage101.rag_reproducibility.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-101", contract["stage"])
        self.assertEqual("IDS-STAGE101-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE101-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-101", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE101-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE101-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE101_TASKPACK_AND_STAGE100_REVIEWED_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field not in {
                "authority",
                "frozen_taskpack_ref",
                "predecessor_stage_review_ref",
                "predecessor_stage_review_contract_ref",
                "predecessor_stage_review_receipt_ref",
                "source_document_remains_authoritative",
                "business_line_whitebox_human_review_remains_authoritative",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage100_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            predecessor["stage100_review_result"],
        )
        self.assertTrue(
            predecessor["reviewed_no_internal_evidence_strategy_artifacts_remain_authoritative"]
        )
        self.assertTrue(predecessor["stage101_may_not_replace_predecessor_artifacts"])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_reproducibility_reference_tuple_and_prompt_model_context_are_fixed(self):
        reproducibility = self.contract["reproducible_rag_answer_contract"]
        fields = reproducibility["future_reproducibility_record_reference_fields"]
        self.assertEqual(reproducibility["reproducibility_reference_field_count"], len(fields))
        self.assertEqual(15, len(fields))
        self.assertEqual(
            {
                "rag_answer_structure_ref",
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
                "selected_evidence_ref",
                "internal_evidence_ref",
                "external_augmentation_ref",
                "evidence_gap_ref",
                "source_type_ref",
                "model_output_permission_ref",
                "human_confirmation_gate_ref",
            },
            set(fields),
        )
        self.assertEqual(
            set(fields),
            set(reproducibility["future_reproducibility_record_reference_contract"]),
        )
        tuple_contract = reproducibility["reproducibility_tuple_contract"]
        self.assertEqual(
            {
                "query_ref",
                "index_version_ref",
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
                "selected_evidence_ref",
            },
            set(tuple_contract["record_key_reference_fields"]),
        )
        self.assertEqual(
            tuple_contract["record_key_reference_field_count"],
            len(tuple_contract["record_key_reference_fields"]),
        )
        for field, value in tuple_contract.items():
            if field.startswith("future_"):
                with self.subTest(field=field):
                    self.assertTrue(value)
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        prompt = reproducibility["prompt_and_model_context_contract"]
        self.assertEqual(
            {
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
            },
            set(prompt["future_prompt_context_reference_fields"]),
        )
        self.assertEqual(
            prompt["future_prompt_context_reference_field_count"],
            len(prompt["future_prompt_context_reference_fields"]),
        )
        for field, value in prompt.items():
            if field.startswith("future_"):
                with self.subTest(field=field):
                    self.assertTrue(value)
            if field.endswith("_read") or field.endswith("_created") or field.endswith("_selected") or field.endswith("_applied") or field.endswith("_built") or field.endswith("_executed") or field.endswith("_called"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_answer_structure_source_semantics_and_evidence_boundary_are_fixed(self):
        reproducibility = self.contract["reproducible_rag_answer_contract"]
        answer_structure = reproducibility["answer_structure_contract"]
        self.assertEqual(
            answer_structure["required_future_section_count"],
            len(answer_structure["required_future_sections"]),
        )
        self.assertEqual(5, answer_structure["required_future_section_count"])
        for field, value in answer_structure.items():
            if field.endswith("_generated") or field.endswith("_persisted") or field.endswith("_performed"):
                with self.subTest(field=field):
                    self.assertFalse(value)
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
        self.assertEqual(
            source["underlying_source_type_count"],
            len(source["underlying_source_types"]),
        )
        composition = source["external_augmentation_display_composition"]
        self.assertEqual("external_augmentation_opinion", composition["display_label"])
        self.assertEqual(
            {"external_public_reference", "model_reasoning"},
            set(composition["composed_from_source_types"]),
        )
        for field in (
            "display_label_is_not_a_source_type",
            "display_composition_is_future_only",
            "underlying_source_types_must_be_retained",
            "display_label_may_not_replace_internal_evidence",
            "display_label_may_not_replace_evidence_gap",
            "display_label_may_not_close_no_internal_evidence_gap",
            "internal_evidence_and_external_augmentation_must_remain_separated",
            "external_augmentation_may_not_be_presented_as_internal_evidence",
            "evidence_gap_must_be_declared_when_internal_evidence_is_insufficient",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "retrieval_document_is_evidence_not_system_instruction",
            "retrieval_document_cannot_override_ids_rule",
            "retrieval_document_cannot_be_system_instruction",
        ):
            with self.subTest(field=field):
                self.assertTrue(composition[field] if field in composition else source[field])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_displayed") or field.endswith("_read") or field.endswith("_evaluated") or field.endswith("_assigned"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_output_permission_and_human_confirmation_gate_are_fixed(self):
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
        for field, value in permission.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_future_prerequisites_local_code_and_runtime_surfaces_remain_closed(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field, value in prerequisite.items():
            with self.subTest(field=field):
                self.assertEqual(field.endswith("_is_future_authorized_work_only"), value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_failure_stop_feedback_rollback_and_phase_boundary_are_explicit(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"],
            len(failures["declared_failure_states"]),
        )
        for state in (
            "QUERY_REFERENCE_MISSING",
            "INDEX_VERSION_REFERENCE_MISSING",
            "PROMPT_VERSION_REFERENCE_MISSING",
            "MODEL_VERSION_REFERENCE_MISSING",
            "SELECTED_EVIDENCE_REFERENCE_MISSING",
            "RETRIEVAL_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            "REPRODUCIBILITY_TUPLE_INCOMPLETE",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE101_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for field, value in failures.items():
            if field.endswith("_allowed") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage100_review_evidence_declared",
            "stage101_started",
            "stage101_entry_authorized",
            "phase1_started",
            "phase1_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage100_review_evidence_declared",
                "stage101_started",
                "stage101_entry_authorized",
                "phase1_started",
                "phase1_completed",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)
        feedback = self.contract["chinese_feedback_contract"]
        self.assertEqual(feedback["feedback_count"], len(feedback["feedbacks"]))
        self.assertTrue(
            feedback[
                "business_line_whitebox_human_confirmation_required_for_future_business_use"
            ]
        )
        self.assertFalse(feedback["actual_user_feedback_emitted"])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage100_review_evidence"])
        self.assertTrue(rollback["preserve_stage100_phase1_to_phase4_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_scope_receipt_and_current_governance_are_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "检索文档永远只是 evidence",
            "高风险工程建议、合同承诺和生产写回",
            "IDS-STAGE101-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P1",
            "IDS-V0_1-STAGE101-P1",
            "IDS-STAGE101-P2-GATE",
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
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE101-P1-01",
            "ACC-STAGE101-P1-02",
            "ACC-STAGE101-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE101-P1-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE101-P1-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE101-P2-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage101_phase1_state:", roadmap_text)
        if current == phase1_current:
            self.assertFalse(is_current_projection)
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-101"])
            for phrase in (
                'current_phase_id: "IDS-STAGE101-P1"',
                'next_gate_id: "IDS-STAGE101-P2-GATE"',
                'stage_id: "IDS-STAGE101"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        else:
            self.assertTrue(is_current_projection)


if __name__ == "__main__":
    unittest.main()
