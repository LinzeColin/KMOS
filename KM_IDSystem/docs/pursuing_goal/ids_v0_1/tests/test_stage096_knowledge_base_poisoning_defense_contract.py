import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE096_PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-096_知识库投毒防护.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE095_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage095-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage096-p1-local.json"
REVIEW_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage096-review-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage096KnowledgeBasePoisoningDefensePhase1Tests(unittest.TestCase):
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
            "ids.stage096.knowledge_base_poisoning_defense_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-096", contract["stage"])
        self.assertEqual("IDS-STAGE096-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE096-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-096", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE096-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE096-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE096_TASKPACK_AND_STAGE095_REVIEWED_EVIDENCE_REGRESSION_CONTROL_ARTIFACTS_ONLY",
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

    def test_static_shape_grade_reference_and_predecessor_are_fixed(self):
        shape = self.contract["knowledge_base_poisoning_defense_contract"]
        self.assertEqual(
            shape["knowledge_base_poisoning_defense_field_count"],
            len(shape["future_knowledge_base_poisoning_defense_fields"]),
        )
        self.assertEqual(8, shape["knowledge_base_poisoning_defense_field_count"])
        self.assertEqual(
            {
                "evidence_ledger",
                "evidence_gap",
                "risk_score",
                "evidence_grade",
                "revocation",
                "knowledge_base_poisoning_defense",
            },
            set(shape["control_definitions"]),
        )
        grade_reference = shape["evidence_grade_definition_reference"]
        self.assertEqual(
            ["A", "B", "C", "D", "E"], grade_reference["grade_labels"]
        )
        self.assertFalse(grade_reference["grade_definition_changed"])
        self.assertFalse(grade_reference["grade_assignment_defined"])
        self.assertFalse(grade_reference["grade_threshold_defined"])
        self.assertEqual(
            "14/14/6/5",
            self.predecessor["reviewed_phase_contract"]["phase1_static_shape"],
        )

    def test_conclusion_binding_and_control_only_boundary_are_complete(self):
        shape = self.contract["knowledge_base_poisoning_defense_contract"]
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "poisoning_defense_may_not_replace_evidence_id_or_evidence_gap",
            "internal_material_insufficiency_requires_evidence_gap",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "unreviewed_or_suspected_evidence_requires_future_whitebox_review",
            "low_trust_conflict_expired_or_revoked_evidence_requires_future_degradation_control",
            "high_trust_evidence_layer_admission_requires_future_whitebox_review",
            "business_line_whitebox_human_review_required_before_business_use",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])
        for field, value in shape.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        authorized = {
            "business_line_owner_poisoning_defense_rule_approval_is_future_authorized_work_only",
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
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "EVIDENCE_ID_AND_GAP_BOTH_MISSING",
            "EVIDENCE_GRADE_LABEL_SET_INVALID",
            "UNREVIEWED_OR_SUSPECTED_EVIDENCE_AUTO_ACCEPTED",
            "HIGH_TRUST_LAYER_ADMISSION_WITHOUT_WHITEBOX_REVIEW",
            "POISONING_DEFENSE_RUNTIME_EXECUTED",
            "SECOND_AUTHORITY_CREATED",
            "STAGE096_PHASE2_NOT_AUTHORIZED",
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
            "stage095_review_evidence_declared",
            "stage096_started",
            "stage096_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage097_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "Evidence Ledger、证据缺口、风险评分、可信等级、撤回和知识库投毒防护",
            "关键结论未来必须关联至少一个 `evidence_id_ref` 或 `evidence_gap_ref`",
            "A/B/C/D/E",
            "业务线白箱 owner",
            "业务线白箱人工复核",
            "IDS-STAGE096-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_EVIDENCE_REGRESSION_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage095_review_evidence"])
        self.assertTrue(rollback["preserve_stage095_phase1_to_phase4_evidence"])
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
        stage096_phase1_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P1",
            "IDS-V0_1-STAGE096-P1",
            "IDS-STAGE096-P2-GATE",
        )
        stage096_review_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-REVIEW",
            "IDS-V0_1-STAGE096-REVIEW",
            "IDS-STAGE097-P1-GATE",
        )
        stage097_phase1_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P1",
            "IDS-V0_1-STAGE097-P1",
            "IDS-STAGE097-P2-GATE",
        )
        stage097_phase2_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P2",
            "IDS-V0_1-STAGE097-P2",
            "IDS-STAGE097-P3-GATE",
        )
        stage097_phase3_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P3",
            "IDS-V0_1-STAGE097-P3",
            "IDS-STAGE097-P4-GATE",
        )
        stage097_phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        stage097_review_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-REVIEW",
            "IDS-V0_1-STAGE097-REVIEW",
            "IDS-STAGE098-P1-GATE",
        )
        stage098_phase1_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P1",
            "IDS-V0_1-STAGE098-P1",
            "IDS-STAGE098-P2-GATE",
        )
        stage098_phase2_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P2",
            "IDS-V0_1-STAGE098-P2",
            "IDS-STAGE098-P3-GATE",
        )
        stage098_phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        stage098_phase4_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        stage098_review_current = (
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
        if current == stage096_phase1_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-096"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P1-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P1-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P1-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE096-P1-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE096-P1-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE096-P2-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTRACT_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE096-P1", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage096_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE096-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE096-P2-GATE"', roadmap_text)
        elif current in (
            (
                "IDS-STAGE096",
                "IDS-STAGE096-P2",
                "IDS-V0_1-STAGE096-P2",
                "IDS-STAGE096-P3-GATE",
            ),
            (
                "IDS-STAGE096",
                "IDS-STAGE096-P3",
                "IDS-V0_1-STAGE096-P3",
                "IDS-STAGE096-P4-GATE",
            ),
            (
                "IDS-STAGE096",
                "IDS-STAGE096-P4",
                "IDS-V0_1-STAGE096-P4",
                "IDS-STAGE096-REVIEW-GATE",
            ),
        ):
            self.assertTrue(RECEIPT.is_file())
        elif current in (
            stage096_review_current,
            stage097_phase1_current,
            stage097_phase2_current,
            stage097_phase3_current,
            stage097_phase4_current,
            stage097_review_current,
            stage098_phase1_current,
            stage098_phase2_current,
            stage098_phase3_current,
            stage098_phase4_current,
            stage098_review_current,
            stage099_phase1_current,
        ):
            self.assertTrue(REVIEW_RECEIPT.is_file())
            review_receipt = json.loads(REVIEW_RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual("IDS-STAGE097-P1-GATE", review_receipt["next_gate"])
            self.assertEqual(
                "PASS_REVIEWED_KNOWLEDGE_BASE_POISONING_DEFENSE_RUNTIME_DISABLED",
                review_receipt["result"],
            )
            self.assertTrue(
                all(value == 0 for value in review_receipt["runtime_counts"].values())
            )
        else:
            self.assertEqual(
                (
                    "IDS-STAGE095",
                    "IDS-STAGE095-REVIEW",
                    "IDS-V0_1-STAGE095-REVIEW",
                    "IDS-STAGE096-P1-GATE",
                ),
                current,
            )


if __name__ == "__main__":
    unittest.main()
