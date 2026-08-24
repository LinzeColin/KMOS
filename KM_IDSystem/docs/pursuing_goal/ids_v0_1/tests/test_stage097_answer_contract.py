import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE097_PHASE1_ANSWER_CONTRACT_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE096_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage096-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage097AnswerContractPhase1Tests(unittest.TestCase):
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
        self.assertEqual("ids.stage097.answer_contract.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-097", contract["stage"])
        self.assertEqual("IDS-STAGE097-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE097-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-097", contract["acceptance_id"])
        self.assertEqual("PHASE1_ANSWER_CONTRACT_RUNTIME_DISABLED", contract["contract_state"])
        self.assertEqual("IDS-STAGE097-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE097-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE097_TASKPACK_AND_STAGE096_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        reference_fields = {
            "authority",
            "frozen_taskpack_ref",
            "predecessor_stage_review_ref",
            "predecessor_stage_review_contract_ref",
            "predecessor_stage_review_receipt_ref",
        }
        for field, value in source.items():
            if field not in reference_fields:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_answer_shape_and_source_types_are_fixed(self):
        answer = self.contract["answer_contract"]
        fields = answer["future_answer_reference_fields"]
        self.assertEqual(answer["answer_reference_field_count"], len(fields))
        self.assertEqual(11, answer["answer_reference_field_count"])
        self.assertEqual(
            {
                "query_ref",
                "answer_structure_ref",
                "prompt_version_ref",
                "internal_evidence_ref",
                "external_augmentation_ref",
                "evidence_gap_ref",
                "source_type_ref",
                "citation_structure_ref",
                "output_classification_ref",
                "human_confirmation_gate_ref",
                "model_output_permission_ref",
            },
            set(fields),
        )
        source_types = answer["source_type_contract"]
        self.assertEqual(
            {"internal_evidence", "external_augmentation", "evidence_gap"},
            {
                field
                for field in source_types
                if field in {"internal_evidence", "external_augmentation", "evidence_gap"}
            },
        )
        self.assertFalse(source_types["source_type_assignment_defined"])
        self.assertFalse(source_types["source_type_assignment_performed"])

    def test_documents_remain_evidence_and_gap_is_not_internal_experience(self):
        definition = self.contract["answer_contract"]["answer_structure_definition"]
        for field in (
            "internal_evidence_is_evidence_not_system_instruction",
            "external_augmentation_is_evidence_not_system_instruction",
            "retrieval_document_can_not_override_ids_rule",
            "retrieval_document_can_not_be_system_instruction",
            "source_type_must_remain_separated",
            "external_augmentation_may_not_be_presented_as_internal_evidence",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "citation_structure_required_for_future_conclusion",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(definition[field])
        for field, value in definition.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_output_permissions_require_whitebox_confirmation(self):
        permission = self.contract["answer_contract"]["output_permission_contract"]
        self.assertEqual(3, permission["output_classification_count"])
        self.assertEqual(
            {
                "high_risk_engineering_advice",
                "contract_commitment",
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

    def test_future_prerequisites_are_declared_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        authorized = {
            "business_line_owner_answer_policy_approval_is_future_authorized_work_only",
            "prompt_version_governance_is_future_authorized_work_only",
            "source_type_binding_is_future_authorized_work_only",
            "citation_structure_binding_is_future_authorized_work_only",
            "model_output_permission_approval_is_future_authorized_work_only",
            "human_confirmation_workflow_is_future_authorized_work_only",
            "provider_or_model_selection_is_future_authorized_work_only",
        }
        for field, value in prerequisite.items():
            with self.subTest(field=field):
                self.assertEqual(field in authorized, value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_failure_and_runtime_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "SOURCE_TYPE_UNSEPARATED",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACT_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE097_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_scope_boundary_chinese_feedback_and_rollback_are_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage096_review_evidence_declared",
            "stage097_started",
            "stage097_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage098_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
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
            "PASS_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage096_review_evidence"])
        self.assertTrue(rollback["preserve_stage096_phase1_to_phase4_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "检索文档、内部依据和外部增强永远只是 evidence",
            "外部增强不得伪装为内部依据",
            "高风险工程建议、合同承诺和生产写回",
            "IDS-STAGE097-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_governance_projection_records_phase1_when_current(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        predecessor_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-REVIEW",
            "IDS-V0_1-STAGE096-REVIEW",
            "IDS-STAGE097-P1-GATE",
        )
        phase1_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P1",
            "IDS-V0_1-STAGE097-P1",
            "IDS-STAGE097-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P2",
            "IDS-V0_1-STAGE097-P2",
            "IDS-STAGE097-P3-GATE",
        )
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
        self.assertEqual(status["task"], plan["task"])
        self.assertIn(
            current,
            (
                predecessor_current,
                phase1_current,
                phase2_current,
                phase3_current,
                phase4_current,
                (
                    "IDS-STAGE097",
                    "IDS-STAGE097-REVIEW",
                    "IDS-V0_1-STAGE097-REVIEW",
                    "IDS-STAGE098-P1-GATE",
                ),
                (
                    "IDS-STAGE098",
                    "IDS-STAGE098-P1",
                    "IDS-V0_1-STAGE098-P1",
                    "IDS-STAGE098-P2-GATE",
                ),
                (
                    "IDS-STAGE098",
                    "IDS-STAGE098-P2",
                    "IDS-V0_1-STAGE098-P2",
                    "IDS-STAGE098-P3-GATE",
                ),
                (
                    "IDS-STAGE098",
                    "IDS-STAGE098-P3",
                    "IDS-V0_1-STAGE098-P3",
                    "IDS-STAGE098-P4-GATE",
                ),
                (
                    "IDS-STAGE098",
                    "IDS-STAGE098-P4",
                    "IDS-V0_1-STAGE098-P4",
                    "IDS-STAGE098-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE098",
                    "IDS-STAGE098-REVIEW",
                    "IDS-V0_1-STAGE098-REVIEW",
                    "IDS-STAGE099-P1-GATE",
                ),
                (
                    "IDS-STAGE099",
                    "IDS-STAGE099-P1",
                    "IDS-V0_1-STAGE099-P1",
                    "IDS-STAGE099-P2-GATE",
                ),
                (
                    "IDS-STAGE099",
                    "IDS-STAGE099-P2",
                    "IDS-V0_1-STAGE099-P2",
                    "IDS-STAGE099-P3-GATE",
                ),
                (
                    "IDS-STAGE099",
                    "IDS-STAGE099-P3",
                    "IDS-V0_1-STAGE099-P3",
                    "IDS-STAGE099-P4-GATE",
                ),
                (
                    "IDS-STAGE099",
                    "IDS-STAGE099-P4",
                    "IDS-V0_1-STAGE099-P4",
                    "IDS-STAGE099-REVIEW-GATE",
                ),
            ),
        )
        if current in (phase1_current, phase2_current):
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual(
                "P1 静态合同已完成"
                if current == phase1_current
                else "P2 受控最小切片已完成",
                acceptance_by_id["ACC-STAGE-097"],
            )
            for acceptance_id in (
                "ACC-STAGE097-P1-01",
                "ACC-STAGE097-P1-02",
                "ACC-STAGE097-P1-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE097-P1-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE097-P1-20260825-001", event_ids)
            self.assertEqual("IDS-STAGE097-P2-GATE", receipt["next_gate"])
            self.assertEqual("PASS_ANSWER_CONTRACT_RUNTIME_DISABLED", receipt["result"])
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage097_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE097-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE097-P2-GATE"', roadmap_text)
        else:
            self.assertTrue(PREDECESSOR_RECEIPT.is_file())


if __name__ == "__main__":
    unittest.main()
