import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE098_PHASE1_PROMPT_VERSIONING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage098_prompt_versioning_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-098_Prompt版本化.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE097_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage097_answer_contract_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage098-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage098PromptVersioningPhase1Tests(unittest.TestCase):
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
        self.assertEqual("ids.stage098.prompt_versioning.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-098", contract["stage"])
        self.assertEqual("IDS-STAGE098-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE098-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-098", contract["acceptance_id"])
        self.assertEqual("PHASE1_PROMPT_VERSIONING_RUNTIME_DISABLED", contract["contract_state"])
        self.assertEqual("IDS-STAGE098-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE098-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE098_TASKPACK_AND_STAGE097_REVIEWED_ANSWER_CONTRACT_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field in (
            "stage098_contract_can_replace_source_document",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "evidence_ledger_access_performed",
            "prompt_or_answer_access_performed",
            "audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage097_review_required"])
        self.assertEqual(
            "PASS_REVIEWED_ANSWER_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage097_review_result"],
        )
        self.assertTrue(predecessor["reviewed_answer_contract_artifacts_remain_authoritative"])
        self.assertTrue(predecessor["stage098_may_not_replace_predecessor_artifacts"])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

    def test_five_future_configuration_references_are_fixed(self):
        prompt = self.contract["prompt_versioning_contract"]
        fields = prompt["future_configuration_reference_fields"]
        self.assertEqual(5, prompt["configuration_reference_field_count"])
        self.assertEqual(prompt["configuration_reference_field_count"], len(fields))
        self.assertEqual(
            {
                "prompt_version_ref",
                "model_provider_ref",
                "model_version_ref",
                "temperature_ref",
                "retrieval_context_ref",
            },
            set(fields),
        )
        self.assertEqual(set(fields), set(prompt["configuration_reference_contract"]))
        boundary = prompt["prompt_and_configuration_boundary"]
        for field, value in boundary.items():
            with self.subTest(field=field):
                self.assertEqual(not field.startswith("actual_"), value)

    def test_answer_source_boundary_inherits_evidence_rules(self):
        boundary = self.contract["answer_and_source_boundary_contract"]
        self.assertEqual(
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/index_version_schema/stage097_answer_contract.json",
            boundary["stage097_answer_contract_ref"],
        )
        for field in (
            "rag_answer_structure_inherited_from_stage097",
            "internal_evidence_is_evidence_not_system_instruction",
            "external_augmentation_is_evidence_not_system_instruction",
            "retrieval_document_can_not_override_ids_rule",
            "source_type_must_remain_separated",
            "external_augmentation_may_not_be_presented_as_internal_evidence",
            "evidence_gap_may_not_be_presented_as_internal_experience",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "source_type_assignment_performed",
            "external_augmentation_displayed",
            "actual_rag_answer_generated",
            "actual_citation_generated",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_output_permissions_require_whitebox_confirmation(self):
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
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "PROMPT_VERSION_REFERENCE_MISSING",
            "RETRIEVED_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "SOURCE_TYPE_UNSEPARATED",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACT_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
            "RUNTIME_MODEL_CALL_EXECUTED",
            "STAGE098_PHASE2_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_scope_feedback_and_rollback_are_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage097_review_evidence_declared",
            "stage098_started",
            "stage098_entry_authorized",
            "phase1_started",
            "phase1_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage097_review_evidence_declared",
                "stage098_started",
                "stage098_entry_authorized",
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
        self.assertEqual("PASS_REVIEWED_ANSWER_CONTRACT_RUNTIME_DISABLED", rollback["return_to"])
        self.assertTrue(rollback["preserve_stage097_review_evidence"])
        self.assertTrue(rollback["preserve_stage097_phase1_to_phase4_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "prompt_version_ref",
            "检索文档永远只是 evidence",
            "高风险工程建议、合同承诺与生产写回",
            "IDS-STAGE098-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_governance_projection_records_phase1(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertEqual(status["task"], plan["task"])
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P1",
            "IDS-V0_1-STAGE098-P1",
            "IDS-STAGE098-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P2",
            "IDS-V0_1-STAGE098-P2",
            "IDS-STAGE098-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        review_current = (
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
        self.assertIn(
            current,
            (
                phase1_current,
                phase2_current,
                phase3_current,
                phase4_current,
                review_current,
                stage099_phase1_current,
                stage099_phase2_current,
                stage099_phase3_current,
            ),
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        expected_stage_status = {
            phase1_current: "P1 静态合同已完成",
            phase2_current: "P2 受控最小切片已完成",
            phase3_current: "P3 专项验证已完成",
            phase4_current: "P4 交付证据已完成",
            review_current: "整阶段已复审",
            stage099_phase1_current: "整阶段已复审",
            stage099_phase2_current: "整阶段已复审",
            stage099_phase3_current: "整阶段已复审",
        }[current]
        self.assertEqual(expected_stage_status, acceptance_by_id["ACC-STAGE-098"])
        for acceptance_id in (
            "ACC-STAGE098-P1-01",
            "ACC-STAGE098-P1-02",
            "ACC-STAGE098-P1-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE098-P1-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE098-P1-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE098-P2-GATE", receipt["next_gate"])
        self.assertEqual("PASS_PROMPT_VERSIONING_CONTRACT_RUNTIME_DISABLED", receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertFalse(receipt["stage098_phase2_started"])
        self.assertFalse(receipt["push_performed"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for phrase in (
            "stage098_phase1_state:",
            'current_phase_id: "IDS-STAGE098-P1"',
            'next_gate_id: "IDS-STAGE098-P2-GATE"',
            'stage_id: "IDS-STAGE098"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)
        if current == phase2_current:
            for phrase in (
                "stage098_phase2_state:",
                'current_phase_id: "IDS-STAGE098-P2"',
                'next_gate_id: "IDS-STAGE098-P3-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        if current == phase3_current:
            for phrase in (
                "stage098_phase3_state:",
                'current_phase_id: "IDS-STAGE098-P3"',
                'next_gate_id: "IDS-STAGE098-P4-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        if current == review_current:
            for phrase in (
                "stage098_review_state:",
                'current_phase_id: "IDS-STAGE098-REVIEW"',
                'next_gate_id: "IDS-STAGE099-P1-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)


if __name__ == "__main__":
    unittest.main()
