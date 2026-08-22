import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE089_PHASE1_EVIDENCE_LEDGER_SCHEMA_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_schema_contract.json"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-089_证据账本Schema.md"
PREDECESSOR_REVIEW = BASE / "STAGE088_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = BASE / "index_version_schema" / "stage088_retrieval_result_validity_contract.json"
PREDECESSOR_DELIVERY = BASE / "index_version_schema" / "stage088_retrieval_result_validity_delivery.py"


class Stage089EvidenceLedgerSchemaPhase1Tests(unittest.TestCase):
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
            PREDECESSOR_DELIVERY,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage089.evidence_ledger_schema_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-089", contract["stage"])
        self.assertEqual("IDS-STAGE089-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE089-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-089", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EVIDENCE_LEDGER_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE089-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE089_TASKPACK_AND_STAGE088_REVIEWED_RETRIEVAL_RESULT_VALIDITY_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "evidence_ledger_access_performed",
            "audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_evidence_relation_gap_risk_revocation_poison_and_conclusion_shapes_are_fixed(self):
        shape = self.contract["evidence_ledger_schema_contract"]
        pairs = (
            ("evidence_record_field_count", "future_evidence_record_fields"),
            ("evidence_relation_record_field_count", "future_evidence_relation_record_fields"),
            ("evidence_gap_record_field_count", "future_evidence_gap_record_fields"),
            ("risk_score_record_field_count", "future_risk_score_record_fields"),
            ("revocation_record_field_count", "future_revocation_record_fields"),
            (
                "knowledge_base_poisoning_defense_record_field_count",
                "future_knowledge_base_poisoning_defense_record_fields",
            ),
            (
                "critical_conclusion_binding_record_field_count",
                "future_critical_conclusion_binding_record_fields",
            ),
        )
        for count_field, fields_field in pairs:
            with self.subTest(count_field=count_field):
                self.assertEqual(shape[count_field], len(shape[fields_field]))
        self.assertEqual(
            [
                "evidence_id_ref",
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "report_id_ref",
                "source_type_ref",
                "evidence_grade_ref",
                "source_version_ref",
                "retrieval_trace_ref",
                "evidence_state",
            ],
            shape["future_evidence_record_fields"],
        )
        for field in ("query_ref", "answer_ref", "report_id_ref"):
            with self.subTest(field=field):
                self.assertIn(field, shape["future_evidence_relation_record_fields"])
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "evidence_grade_required_when_evidence_id_is_referenced",
            "low_grade_evidence_may_not_be_presented_as_high_grade",
            "low_trust_conflict_expired_or_revoked_evidence_must_be_degraded",
            "revocation_impact_must_reference_affected_fact_or_report",
            "poisoning_suspected_or_unreviewed_evidence_must_not_be_automatically_accepted",
            "business_line_whitebox_human_review_required_before_business_use",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])

    def test_a_to_e_grades_are_complete_and_conservative(self):
        shape = self.contract["evidence_ledger_schema_contract"]
        grades = shape["evidence_grade_definitions"]
        self.assertEqual(5, shape["evidence_grade_count"])
        self.assertEqual(["A", "B", "C", "D", "E"], [item["grade"] for item in grades])
        self.assertIn("不得单独支撑关键结论", grades[3]["future_use_rule"])
        self.assertIn("不得进入关键结论", grades[4]["future_use_rule"])
        self.assertTrue(
            shape["business_line_whitebox_human_review_required_before_business_use"]
        )

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field in (
            "evidence_schema_runtime_is_future_authorized_work_only",
            "retrieval_evidence_capture_is_future_authorized_work_only",
            "risk_scoring_runtime_is_future_authorized_work_only",
            "revocation_runtime_is_future_authorized_work_only",
            "knowledge_base_poisoning_defense_runtime_is_future_authorized_work_only",
            "report_status_update_runtime_is_future_authorized_work_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(prerequisite[field])
        for field, value in prerequisite.items():
            if field not in {
                "evidence_schema_runtime_is_future_authorized_work_only",
                "retrieval_evidence_capture_is_future_authorized_work_only",
                "risk_scoring_runtime_is_future_authorized_work_only",
                "revocation_runtime_is_future_authorized_work_only",
                "knowledge_base_poisoning_defense_runtime_is_future_authorized_work_only",
                "report_status_update_runtime_is_future_authorized_work_only",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_failure_and_runtime_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "CRITICAL_CONCLUSION_EVIDENCE_AND_GAP_BOTH_MISSING",
            "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_GRADE",
            "LOW_TRUST_CONFLICT_EXPIRED_OR_REVOKED_EVIDENCE_NOT_DEGRADED",
            "REVOCATION_IMPACT_REFERENCE_MISSING",
            "POISONING_DEFENSE_REFERENCE_MISSING",
            "SUSPECTED_POISONING_EVIDENCE_NOT_QUARANTINED",
            "PHASE1_EVIDENCE_LEDGER_SCHEMA_NOT_AUTHORIZED",
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
            "stage088_review_evidence_declared",
            "stage089_started",
            "stage089_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage090_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "evidence_id、document_id、chunk_id、fact_id、report_id、source_type、evidence_grade",
            "关键结论必须关联至少一个 evidence_id 或 evidence_gap",
            "A/B/C/D/E",
            "撤回",
            "知识库投毒防护",
            "业务线白箱人工复核",
            "IDS-STAGE089-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_RETRIEVAL_RESULT_VALIDITY_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage088_review_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])


if __name__ == "__main__":
    unittest.main()
