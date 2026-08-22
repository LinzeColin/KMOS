import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE090_PHASE1_RETRIEVAL_EVIDENCE_CAPTURE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage090_retrieval_evidence_capture_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-090_从检索捕获证据.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE089_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage089_evidence_ledger_schema_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-23-stage089-review-local.json"


class Stage090RetrievalEvidenceCapturePhase1Tests(unittest.TestCase):
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
            "ids.stage090.retrieval_evidence_capture_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-090", contract["stage"])
        self.assertEqual("IDS-STAGE090-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE090-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-090", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_RETRIEVAL_EVIDENCE_CAPTURE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE090-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE090_TASKPACK_AND_STAGE089_REVIEWED_EVIDENCE_LEDGER_CONTROL_ARTIFACTS_ONLY",
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

    def test_retrieval_capture_ledger_capture_and_relation_shapes_are_fixed(self):
        shape = self.contract["retrieval_evidence_capture_contract"]
        pairs = (
            ("retrieval_capture_request_field_count", "future_retrieval_capture_request_fields"),
            ("evidence_ledger_capture_field_count", "future_evidence_ledger_capture_fields"),
            ("capture_relation_field_count", "future_capture_relation_fields"),
        )
        for count_field, fields_field in pairs:
            with self.subTest(count_field=count_field):
                self.assertEqual(shape[count_field], len(shape[fields_field]))
        self.assertEqual(
            [
                "retrieval_trace_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "source_type_ref",
                "source_version_ref",
                "capture_request_state",
            ],
            shape["future_retrieval_capture_request_fields"],
        )
        self.assertEqual(
            [
                "evidence_id_ref",
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
            ],
            shape["future_capture_relation_fields"],
        )

    def test_a_to_e_grades_and_critical_conclusion_boundary_are_complete(self):
        shape = self.contract["retrieval_evidence_capture_contract"]
        grades = shape["evidence_grade_definitions"]
        self.assertEqual(5, shape["evidence_grade_count"])
        self.assertEqual(["A", "B", "C", "D", "E"], [item["grade"] for item in grades])
        self.assertIn("不得单独支撑关键结论", grades[3]["future_use_rule"])
        self.assertIn("不得进入关键结论", grades[4]["future_use_rule"])
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "evidence_grade_required_when_evidence_id_is_referenced",
            "low_grade_evidence_may_not_be_presented_as_high_grade",
            "low_trust_conflict_expired_or_revoked_evidence_must_be_degraded",
            "poisoning_suspected_or_unreviewed_evidence_must_not_be_automatically_accepted",
            "business_line_whitebox_human_review_required_before_business_use",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        authorized = {
            "retrieval_evidence_capture_is_future_authorized_work_only",
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
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "CRITICAL_CONCLUSION_EVIDENCE_AND_GAP_BOTH_MISSING",
            "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_GRADE",
            "LOW_TRUST_CONFLICT_EXPIRED_OR_REVOKED_EVIDENCE_NOT_DEGRADED",
            "POISONING_DEFENSE_REFERENCE_MISSING",
            "PHASE1_RETRIEVAL_EVIDENCE_CAPTURE_NOT_AUTHORIZED",
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
            "stage089_review_evidence_declared",
            "stage090_started",
            "stage090_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage091_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "retrieval trace、query、answer、report、document、chunk、fact",
            "关键结论未来必须关联至少一个 evidence_id 或 evidence_gap",
            "A/B/C/D/E",
            "撤回",
            "知识库投毒防护",
            "业务线白箱人工复核",
            "IDS-STAGE090-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_EVIDENCE_LEDGER_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage089_review_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])


if __name__ == "__main__":
    unittest.main()
