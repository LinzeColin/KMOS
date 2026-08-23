import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE091_PHASE1_EVIDENCE_GAP_HANDLING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage091_evidence_gap_handling_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-091_证据缺口处理.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE090_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage090_retrieval_evidence_capture_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage090-review-local.json"


class Stage091EvidenceGapHandlingPhase1Tests(unittest.TestCase):
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
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage091.evidence_gap_handling_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-091", contract["stage"])
        self.assertEqual("IDS-STAGE091-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE091-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-091", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EVIDENCE_GAP_HANDLING_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE091-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE091_TASKPACK_AND_STAGE090_REVIEWED_RETRIEVAL_EVIDENCE_CAPTURE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "evidence_ledger_access_performed",
            "answer_or_report_access_performed",
            "audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_evidence_gap_shape_and_internal_experience_boundary_are_fixed(self):
        shape = self.contract["evidence_gap_contract"]
        self.assertEqual(shape["evidence_gap_field_count"], len(shape["future_evidence_gap_fields"]))
        self.assertEqual(
            [
                "evidence_gap_ref",
                "critical_conclusion_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "gap_reason_ref",
                "required_evidence_type_ref",
                "gap_status_ref",
                "gap_handling_state",
            ],
            shape["future_evidence_gap_fields"],
        )
        self.assertEqual(
            shape["evidence_gap_relation_field_count"],
            len(shape["future_evidence_gap_relation_fields"]),
        )
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "internal_material_insufficiency_requires_evidence_gap",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "system_output_may_not_replace_evidence_gap",
            "business_line_whitebox_human_review_required_before_business_use",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])
        for field in (
            "actual_evidence_gap_created",
            "actual_evidence_gap_resolved",
            "actual_evidence_gap_relation_created",
            "actual_critical_conclusion_bound",
        ):
            with self.subTest(field=field):
                self.assertFalse(shape[field])

    def test_grades_and_critical_conclusion_controls_are_complete(self):
        shape = self.contract["evidence_gap_contract"]
        grades = shape["evidence_grade_definitions"]
        self.assertEqual(5, shape["evidence_grade_count"])
        self.assertEqual(["A", "B", "C", "D", "E"], [item["grade"] for item in grades])
        self.assertIn("不得单独支撑关键结论", grades[3]["future_use_rule"])
        self.assertIn("不得进入关键结论", grades[4]["future_use_rule"])
        self.assertTrue(shape["low_grade_evidence_may_not_be_presented_as_high_grade"])
        self.assertTrue(
            shape["poisoning_suspected_or_unreviewed_evidence_must_not_be_automatically_accepted"]
        )

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        authorized = {
            "evidence_gap_detection_is_future_authorized_work_only",
            "evidence_gap_resolution_is_future_authorized_work_only",
            "evidence_ledger_capture_is_future_authorized_work_only",
            "risk_scoring_runtime_is_future_authorized_work_only",
            "revocation_runtime_is_future_authorized_work_only",
            "knowledge_base_poisoning_defense_runtime_is_future_authorized_work_only",
            "report_status_update_runtime_is_future_authorized_work_only",
        }
        for field, value in prerequisite.items():
            with self.subTest(field=field):
                self.assertEqual(field in authorized, value)

    def test_failure_and_runtime_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "CRITICAL_CONCLUSION_EVIDENCE_AND_GAP_BOTH_MISSING",
            "INTERNAL_MATERIAL_INSUFFICIENCY_WITHOUT_EVIDENCE_GAP",
            "EVIDENCE_GAP_MASQUERADING_AS_INTERNAL_EXPERIENCE",
            "SYSTEM_OUTPUT_USED_AS_INTERNAL_EVIDENCE",
            "PHASE1_EVIDENCE_GAP_HANDLING_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_stage_boundary_and_scope_keep_next_gate_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage090_review_evidence_declared",
            "stage091_started",
            "stage091_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage092_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "资料不足时以 `evidence_gap` 表达",
            "关键结论未来必须关联至少一个 `evidence_id_ref` 或 `evidence_gap_ref`",
            "不能伪装成内部经验",
            "A/B/C/D/E",
            "撤回",
            "知识库投毒防护",
            "业务线白箱人工复核",
            "IDS-STAGE091-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_RETRIEVAL_EVIDENCE_CAPTURE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage090_review_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])


if __name__ == "__main__":
    unittest.main()
