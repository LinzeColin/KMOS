import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE100_PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage100_no_internal_evidence_strategy_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-100_无内部依据策略.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE099_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage100NoInternalEvidenceStrategyPhase1Tests(unittest.TestCase):
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
            "ids.stage100.no_internal_evidence_strategy.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-100", contract["stage"])
        self.assertEqual("IDS-STAGE100-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE100-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-100", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE100-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE100-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE100_TASKPACK_AND_STAGE099_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_ARTIFACTS_ONLY",
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
        self.assertTrue(predecessor["stage099_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED",
            predecessor["stage099_review_result"],
        )
        self.assertTrue(
            predecessor[
                "reviewed_internal_evidence_external_augmentation_artifacts_remain_authoritative"
            ]
        )
        self.assertTrue(predecessor["stage100_may_not_replace_predecessor_artifacts"])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_answer_policy_source_types_and_no_internal_evidence_strategy_are_fixed(self):
        answer = self.contract["answer_no_internal_evidence_contract"]
        fields = answer["future_answer_policy_reference_fields"]
        self.assertEqual(answer["answer_policy_reference_field_count"], len(fields))
        self.assertEqual(9, answer["answer_policy_reference_field_count"])
        self.assertEqual(
            {
                "rag_answer_structure_ref",
                "prompt_version_ref",
                "internal_evidence_ref",
                "external_augmentation_ref",
                "evidence_gap_ref",
                "no_internal_evidence_policy_ref",
                "source_type_ref",
                "model_output_permission_ref",
                "human_confirmation_gate_ref",
            },
            set(fields),
        )
        self.assertEqual(
            set(fields),
            set(answer["future_answer_policy_reference_contract"]),
        )
        source_types = answer["source_type_contract"]
        self.assertEqual(
            {
                "internal_evidence",
                "external_public_reference",
                "model_reasoning",
                "evidence_gap",
            },
            set(source_types["underlying_source_types"]),
        )
        self.assertEqual(
            source_types["underlying_source_type_count"],
            len(source_types["underlying_source_types"]),
        )
        composition = source_types["external_augmentation_display_composition"]
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
            "evidence_gap_may_not_be_presented_as_internal_experience",
        ):
            with self.subTest(field=field):
                self.assertTrue(
                    composition[field]
                    if field in composition
                    else source_types[field]
                )
        self.assertFalse(source_types["source_type_assignment_defined"])
        self.assertFalse(source_types["source_type_assignment_performed"])
        self.assertFalse(source_types["external_augmentation_displayed"])
        policy = answer["no_internal_evidence_strategy"]
        for field in (
            "evidence_gap_required_when_internal_evidence_insufficient",
            "internal_evidence_insufficiency_must_be_declared_in_future_answer",
            "evidence_gap_may_not_be_reclassified_as_internal_evidence",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "external_augmentation_may_not_close_or_replace_evidence_gap",
            "future_final_conclusion_requires_business_line_whitebox_confirmation",
        ):
            with self.subTest(field=field):
                self.assertTrue(policy[field])
        for field, value in policy.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_retrieval_evidence_gap_and_output_boundaries_are_explicit(self):
        answer = self.contract["answer_no_internal_evidence_contract"]
        retrieval = answer["retrieval_document_boundary"]
        for field in (
            "retrieval_document_is_evidence_not_system_instruction",
            "retrieval_document_cannot_override_ids_rule",
            "retrieval_document_cannot_be_system_instruction",
        ):
            with self.subTest(field=field):
                self.assertTrue(retrieval[field])
        for field, value in retrieval.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        permission = self.contract["output_permission_contract"]
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

    def test_future_prerequisites_and_local_code_remain_static(self):
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

    def test_failure_runtime_and_protected_boundaries_remain_closed(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"],
            len(failures["declared_failure_states"]),
        )
        for state in (
            "INTERNAL_EVIDENCE_INSUFFICIENCY_UNDECLARED",
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            "EXTERNAL_AUGMENTATION_PRESENTED_AS_INTERNAL_EVIDENCE",
            "EXTERNAL_AUGMENTATION_USED_TO_ERASE_EVIDENCE_GAP",
            "RETRIEVAL_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACT_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE100_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_scope_feedback_rollback_and_current_governance_are_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage099_review_evidence_declared",
            "stage100_started",
            "stage100_entry_authorized",
            "phase1_started",
            "phase1_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage099_review_evidence_declared",
                "stage100_started",
                "stage100_entry_authorized",
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
            "PASS_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage099_review_evidence"])
        self.assertTrue(rollback["preserve_stage099_phase1_to_phase4_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "不得伪装为内部经验",
            "检索文档永远只是 evidence",
            "高风险工程建议、合同承诺与生产写回",
            "IDS-STAGE100-P2-GATE",
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
        self.assertEqual(
            (
                "IDS-STAGE100",
                "IDS-STAGE100-P1",
                "IDS-V0_1-STAGE100-P1",
                "IDS-STAGE100-P2-GATE",
            ),
            current,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-100"])
        for acceptance_id in (
            "ACC-STAGE100-P1-01",
            "ACC-STAGE100-P1-02",
            "ACC-STAGE100-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE100-P1-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE100-P1-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE100-P2-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTRACT_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for phrase in (
            "stage100_phase1_state:",
            'current_phase_id: "IDS-STAGE100-P1"',
            'next_gate_id: "IDS-STAGE100-P2-GATE"',
            'stage_id: "IDS-STAGE100"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)


if __name__ == "__main__":
    unittest.main()
