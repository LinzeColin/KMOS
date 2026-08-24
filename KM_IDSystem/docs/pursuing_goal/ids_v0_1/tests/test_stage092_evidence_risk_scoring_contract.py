import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE092_PHASE1_EVIDENCE_RISK_SCORING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage092_evidence_risk_scoring_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-092_证据风险评分.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE091_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage091-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage092-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage092EvidenceRiskScoringPhase1Tests(unittest.TestCase):
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
            "ids.stage092.evidence_risk_scoring_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-092", contract["stage"])
        self.assertEqual("IDS-STAGE092-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE092-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-092", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EVIDENCE_RISK_SCORING_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE092-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE092_TASKPACK_AND_STAGE091_REVIEWED_EVIDENCE_GAP_HANDLING_CONTROL_ARTIFACTS_ONLY",
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

    def test_risk_shape_relations_and_factor_inputs_are_fixed(self):
        shape = self.contract["evidence_risk_scoring_contract"]
        self.assertEqual(
            shape["evidence_risk_field_count"],
            len(shape["future_evidence_risk_fields"]),
        )
        self.assertEqual(
            [
                "risk_score_ref",
                "evidence_ledger_ref",
                "evidence_id_ref",
                "evidence_gap_ref",
                "critical_conclusion_ref",
                "document_id_ref",
                "chunk_id_ref",
                "fact_id_ref",
                "query_ref",
                "answer_ref",
                "report_id_ref",
                "source_provenance_indicator_ref",
                "ocr_confidence_indicator_ref",
                "version_status_indicator_ref",
                "review_status_indicator_ref",
                "conflict_status_indicator_ref",
                "evidence_grade_ref",
                "revocation_status_ref",
                "poisoning_defense_status_ref",
                "risk_assessment_state",
            ],
            shape["future_evidence_risk_fields"],
        )
        self.assertEqual(
            shape["evidence_risk_relation_field_count"],
            len(shape["future_evidence_risk_relation_fields"]),
        )
        self.assertEqual(
            [
                "source_provenance_indicator_ref",
                "ocr_confidence_indicator_ref",
                "version_status_indicator_ref",
                "review_status_indicator_ref",
                "conflict_status_indicator_ref",
            ],
            shape["future_risk_factor_input_fields"],
        )
        self.assertEqual(
            shape["risk_factor_input_field_count"],
            len(shape["future_risk_factor_input_fields"]),
        )

    def test_formula_owner_boundary_grades_and_conclusion_controls_are_complete(self):
        shape = self.contract["evidence_risk_scoring_contract"]
        self.assertEqual(
            "FUTURE_BUSINESS_LINE_WHITEBOX_OWNER_APPROVED_RULE_REQUIRED",
            shape["risk_score_formula_state"],
        )
        for field in (
            "risk_score_formula_defined",
            "risk_score_weight_defined",
            "risk_score_threshold_defined",
            "actual_risk_factor_evaluated",
            "actual_risk_score_calculated",
        ):
            with self.subTest(field=field):
                self.assertFalse(shape[field])
        grades = shape["evidence_grade_definitions"]
        self.assertEqual(5, shape["evidence_grade_count"])
        self.assertEqual(["A", "B", "C", "D", "E"], [item["grade"] for item in grades])
        self.assertIn("不得单独支撑关键结论", grades[3]["future_use_rule"])
        self.assertIn("不得进入关键结论", grades[4]["future_use_rule"])
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "risk_score_may_not_replace_evidence_id_or_evidence_gap",
            "internal_material_insufficiency_requires_evidence_gap",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "low_grade_evidence_may_not_be_presented_as_high_grade",
            "business_line_whitebox_human_review_required_before_business_use",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        authorized = {
            "business_line_owner_risk_formula_approval_is_future_authorized_work_only",
            "evidence_ledger_capture_is_future_authorized_work_only",
            "evidence_gap_detection_or_resolution_is_future_authorized_work_only",
            "risk_scoring_runtime_is_future_authorized_work_only",
            "evidence_grade_runtime_is_future_authorized_work_only",
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
            failures["failure_state_count"],
            len(failures["declared_failure_states"]),
        )
        for state in (
            "RISK_SCORE_REFERENCE_MISSING",
            "RISK_SOURCE_PROVENANCE_INDICATOR_MISSING",
            "RISK_OCR_CONFIDENCE_INDICATOR_MISSING",
            "RISK_VERSION_STATUS_INDICATOR_MISSING",
            "RISK_REVIEW_STATUS_INDICATOR_MISSING",
            "RISK_CONFLICT_STATUS_INDICATOR_MISSING",
            "RISK_FORMULA_OR_THRESHOLD_UNAUTHORIZED",
            "PHASE1_EVIDENCE_RISK_SCORING_NOT_AUTHORIZED",
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

    def test_stage_boundary_scope_and_next_gate_are_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage091_review_evidence_declared",
            "stage092_started",
            "stage092_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage093_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "来源、OCR 置信度、版本、复核状态和冲突状态",
            "关键结论未来必须关联至少一个 `evidence_id_ref` 或 `evidence_gap_ref`",
            "风险权重、阈值和业务判定公式",
            "A/B/C/D/E",
            "撤回",
            "知识库投毒防护",
            "业务线白箱人工复核",
            "IDS-STAGE092-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_EVIDENCE_GAP_HANDLING_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage091_review_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

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
        stage092_phase1_current = (
            "IDS-STAGE092",
            "IDS-STAGE092-P1",
            "IDS-V0_1-STAGE092-P1",
            "IDS-STAGE092-P2-GATE",
        )
        if current == stage092_phase1_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-092"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE092-P1-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE092-P1-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE092-P1-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE092-P1-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE092-P1-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE092-P2-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_EVIDENCE_RISK_SCORING_CONTRACT_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE092-P1", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage092_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE092-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE092-P2-GATE"', roadmap_text)
        else:
            self.assertIn(
                current,
                (
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P2",
                        "IDS-V0_1-STAGE092-P2",
                        "IDS-STAGE092-P3-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P3",
                        "IDS-V0_1-STAGE092-P3",
                        "IDS-STAGE092-P4-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-P4",
                        "IDS-V0_1-STAGE092-P4",
                        "IDS-STAGE092-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE092",
                        "IDS-STAGE092-REVIEW",
                        "IDS-V0_1-STAGE092-REVIEW",
                        "IDS-STAGE093-P1-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P1",
                        "IDS-V0_1-STAGE093-P1",
                        "IDS-STAGE093-P2-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P2",
                        "IDS-V0_1-STAGE093-P2",
                        "IDS-STAGE093-P3-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P3",
                        "IDS-V0_1-STAGE093-P3",
                        "IDS-STAGE093-P4-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-P4",
                        "IDS-V0_1-STAGE093-P4",
                        "IDS-STAGE093-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE093",
                        "IDS-STAGE093-REVIEW",
                        "IDS-V0_1-STAGE093-REVIEW",
                        "IDS-STAGE094-P1-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P1",
                        "IDS-V0_1-STAGE094-P1",
                        "IDS-STAGE094-P2-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P2",
                        "IDS-V0_1-STAGE094-P2",
                        "IDS-STAGE094-P3-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-P3",
                        "IDS-V0_1-STAGE094-P3",
                        "IDS-STAGE094-P4-GATE",
                    ),
                    (
                        "IDS-STAGE091",
                        "IDS-STAGE091-REVIEW",
                        "IDS-V0_1-STAGE091-REVIEW",
                        "IDS-STAGE092-P1-GATE",
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
