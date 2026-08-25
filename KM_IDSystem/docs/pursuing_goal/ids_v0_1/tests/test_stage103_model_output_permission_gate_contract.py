import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE103_PHASE1_MODEL_OUTPUT_PERMISSION_GATE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-103_模型输出权限门禁.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE102_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage102_document_prompt_injection_defense_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage102-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-p1-local.json"
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


class Stage103ModelOutputPermissionGatePhase1Tests(unittest.TestCase):
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
            "ids.stage103.model_output_permission_gate.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-103", contract["stage"])
        self.assertEqual("IDS-STAGE103-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE103-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-103", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE103-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE103-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE103_TASKPACK_AND_STAGE102_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        for field, value in authority.items():
            if field.endswith("_performed") or field.startswith("second_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage102_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            predecessor["stage102_review_result"],
        )
        self.assertIs(
            predecessor["actual_predecessor_runtime_artifact_read_performed"], False
        )

    def test_answer_reference_shape_and_prompt_boundary_are_exact(self):
        gate = self.contract["model_output_permission_gate_contract"]
        self.assertEqual(EXPECTED_CONTROL_FIELDS, gate["future_control_reference_fields"])
        self.assertEqual(13, gate["future_control_reference_field_count"])
        self.assertEqual(
            set(EXPECTED_CONTROL_FIELDS),
            set(gate["future_control_reference_contract"]),
        )
        self.assertTrue(gate["control_references_are_labels_only"])
        answer = gate["answer_structure_contract"]
        self.assertEqual(5, answer["required_future_section_count"])
        self.assertEqual(
            answer["required_future_section_count"],
            len(answer["required_future_sections"]),
        )
        for field, value in answer.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        prompt = gate["prompt_version_contract"]
        self.assertTrue(prompt["prompt_version_is_future_control_reference_only"])
        for field, value in prompt.items():
            if field.endswith("_performed") or field.endswith("_selected"):
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
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
            else:
                with self.subTest(field=field):
                    self.assertIs(value, True)

    def test_output_permission_and_human_confirmation_gate_are_exact(self):
        permission = self.contract["output_permission_contract"]
        self.assertEqual(
            "high_risk_engineering_advice",
            permission["taskpack_high_risk_advice_controlled_label"],
        )
        self.assertEqual(5, permission["output_classification_count"])
        self.assertEqual(
            EXPECTED_OUTPUT_TYPES, set(permission["classified_output_types"])
        )
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
        self.assertEqual(24, failures["failure_state_count"])
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for failure_state in (
            "DOCUMENT_EVIDENCE_TREATED_AS_SYSTEM_INSTRUCTION",
            "EVIDENCE_GAP_PRESENTED_AS_INTERNAL_EXPERIENCE",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE103_PHASE2_NOT_AUTHORIZED",
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
            "stage102_review_evidence_declared",
            "stage103_started",
            "stage103_entry_authorized",
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
            "stage104_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], False)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_DOCUMENT_PROMPT_INJECTION_DEFENSE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage102_review_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)

    def test_current_governance_projection_receipt_and_event_are_exact(self):
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "检索文档永远只是 evidence",
            "高风险工程建议、合同承诺和生产写回",
            "IDS-STAGE103-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
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
        stage103_phase3_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P3",
            "IDS-V0_1-STAGE103-P3",
            "IDS-STAGE103-P4-GATE",
        )
        stage103_phase4_current = (
            "IDS-STAGE103",
            "IDS-STAGE103-P4",
            "IDS-V0_1-STAGE103-P4",
            "IDS-STAGE103-REVIEW-GATE",
        )
        stage103_review_current = (
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
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {stage103_phase1_current},
            status,
            plan,
            ROADMAP,
        )
        if current == stage103_phase1_current:
            self.assertFalse(is_current_projection)
        elif current == stage103_phase2_current:
            self.assertEqual(stage103_phase2_current, current)
            self.assertTrue(is_current_projection)
        elif current == stage103_phase3_current:
            self.assertEqual(stage103_phase3_current, current)
            self.assertTrue(is_current_projection)
        elif current == stage103_review_current:
            self.assertEqual(stage103_review_current, current)
            self.assertTrue(is_current_projection)
        elif current in {
            stage104_phase1_current,
            stage104_phase2_current,
            stage104_phase3_current,
        }:
            self.assertIn(
                current,
                {
                    stage104_phase1_current,
                    stage104_phase2_current,
                    stage104_phase3_current,
                },
            )
            self.assertTrue(is_current_projection)
        else:
            self.assertEqual(stage103_phase4_current, current)
            self.assertTrue(is_current_projection)
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {
            item["id"]: item["status"] for item in acceptance["items"]
        }
        if current == stage103_phase1_current:
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-103"])
        elif current == stage103_phase2_current:
            self.assertEqual(
                "P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-103"]
            )
        elif current == stage103_phase3_current:
            self.assertEqual(
                "P3 专项异常场景已完成", acceptance_by_id["ACC-STAGE-103"]
            )
        elif current == stage103_review_current:
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-103"])
        elif current in {
            stage104_phase1_current,
            stage104_phase2_current,
            stage104_phase3_current,
        }:
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-103"])
        else:
            self.assertEqual(
                "P1/P2/P3/P4 控制工件已完成", acceptance_by_id["ACC-STAGE-103"]
            )
        for acceptance_id in (
            "ACC-STAGE103-P1-01",
            "ACC-STAGE103-P1-02",
            "ACC-STAGE103-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE103-P1-04"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED", receipt["result"]
        )
        self.assertEqual("IDS-STAGE103-P2-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE103-P1-20260825-001"
        )
        self.assertEqual("IDS-V0_1-STAGE103-P1", event["task_id"])
        self.assertEqual(
            [
                "ACC-STAGE-103",
                "ACC-STAGE103-P1-01",
                "ACC-STAGE103-P1-02",
                "ACC-STAGE103-P1-03",
                "ACC-STAGE103-P1-04",
            ],
            event["acceptance_ids"],
        )


if __name__ == "__main__":
    unittest.main()
