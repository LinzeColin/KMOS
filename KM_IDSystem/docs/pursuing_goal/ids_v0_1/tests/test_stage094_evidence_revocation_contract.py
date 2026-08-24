import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE094_PHASE1_EVIDENCE_REVOCATION_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage094_evidence_revocation_contract.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-094_证据撤回.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE093_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_stage_review_contract.json"
)
PREDECESSOR_GRADE_CONTRACT = (
    BASE / "index_version_schema" / "stage093_evidence_grade_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage093-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage094-p1-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage094EvidenceRevocationPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.predecessor_grade = json.loads(
            PREDECESSOR_GRADE_CONTRACT.read_text(encoding="utf-8")
        )

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_GRADE_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage094.evidence_revocation_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-094", contract["stage"])
        self.assertEqual("IDS-STAGE094-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE094-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-094", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EVIDENCE_REVOCATION_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE094-P1-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE094-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE094_TASKPACK_AND_STAGE093_REVIEWED_EVIDENCE_GRADE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field, value in source.items():
            if field not in {
                "authority",
                "frozen_taskpack_ref",
                "predecessor_stage_review_ref",
                "predecessor_stage_review_contract_ref",
                "predecessor_stage_review_receipt_ref",
                "predecessor_evidence_grade_contract_ref",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_static_shape_and_grade_reference_are_fixed(self):
        shape = self.contract["evidence_revocation_contract"]
        self.assertEqual(
            shape["evidence_revocation_field_count"],
            len(shape["future_evidence_revocation_fields"]),
        )
        self.assertEqual(18, shape["evidence_revocation_field_count"])
        self.assertEqual(
            shape["evidence_revocation_relation_field_count"],
            len(shape["future_evidence_revocation_relation_fields"]),
        )
        self.assertEqual(14, shape["evidence_revocation_relation_field_count"])
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
        self.assertEqual(
            "FUTURE_BUSINESS_LINE_WHITEBOX_OWNER_APPROVED_RULE_REQUIRED",
            grade_reference["grade_assignment_rule_state"],
        )
        self.assertFalse(grade_reference["grade_assignment_defined"])
        self.assertFalse(grade_reference["grade_threshold_defined"])
        self.assertEqual(
            ["A", "B", "C", "D", "E"],
            [
                item["grade"]
                for item in self.predecessor_grade["evidence_grade_contract"][
                    "evidence_grade_definitions"
                ]
            ],
        )

    def test_conclusion_revocation_and_whitebox_controls_are_complete(self):
        shape = self.contract["evidence_revocation_contract"]
        for field in (
            "critical_conclusion_requires_evidence_id_or_evidence_gap",
            "critical_conclusion_may_not_omit_evidence_id_and_evidence_gap",
            "evidence_revocation_may_not_replace_evidence_id_or_evidence_gap",
            "internal_material_insufficiency_requires_evidence_gap",
            "evidence_gap_may_not_be_presented_as_internal_experience",
            "low_trust_conflict_expired_or_revoked_evidence_requires_future_degradation_control",
            "poisoning_suspected_or_unreviewed_evidence_requires_future_whitebox_review",
            "report_status_impact_is_future_reference_only",
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
            "business_line_owner_revocation_rule_approval_is_future_authorized_work_only",
            "evidence_ledger_capture_is_future_authorized_work_only",
            "evidence_gap_detection_or_resolution_is_future_authorized_work_only",
            "risk_scoring_runtime_is_future_authorized_work_only",
            "evidence_grade_runtime_is_future_authorized_work_only",
            "revocation_or_degradation_runtime_is_future_authorized_work_only",
            "recovery_runtime_is_future_authorized_work_only",
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
            "EVIDENCE_ID_AND_GAP_BOTH_MISSING",
            "REVOCATION_RULE_OR_GRADE_ASSIGNMENT_UNAUTHORIZED",
            "REVOKED_OR_CONFLICTING_EVIDENCE_AUTO_ACCEPTED",
            "REVOCATION_OR_DEGRADATION_AUTO_EXECUTED",
            "REPORT_STATUS_AUTO_UPDATED",
            "STAGE094_PHASE2_NOT_AUTHORIZED",
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
            "stage093_review_evidence_declared",
            "stage094_started",
            "stage094_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage095_started",
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
            "IDS-STAGE094-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_EVIDENCE_GRADE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage093_review_evidence"])
        self.assertTrue(rollback["preserve_stage093_phase1_to_phase4_evidence"])
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
        stage095_phase1_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P1",
            "IDS-V0_1-STAGE095-P1",
            "IDS-STAGE095-P2-GATE",
        )
        stage095_phase2_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P2",
            "IDS-V0_1-STAGE095-P2",
            "IDS-STAGE095-P3-GATE",
        )
        stage095_phase3_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P3",
            "IDS-V0_1-STAGE095-P3",
            "IDS-STAGE095-P4-GATE",
        )
        stage095_phase4_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P4",
            "IDS-V0_1-STAGE095-P4",
            "IDS-STAGE095-REVIEW-GATE",
        )
        stage094_phase1_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P1",
            "IDS-V0_1-STAGE094-P1",
            "IDS-STAGE094-P2-GATE",
        )
        if current == stage094_phase1_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P1 静态合同已完成", acceptance_by_id["ACC-STAGE-094"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P1-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P1-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P1-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE094-P1-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE094-P1-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE094-P2-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_EVIDENCE_REVOCATION_CONTRACT_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE094-P1", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage094_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE094-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE094-P2-GATE"', roadmap_text)
        else:
            self.assertIn(
                current,
                (
                    stage095_phase1_current,
                    stage095_phase2_current,
                    stage095_phase3_current,
                    stage095_phase4_current,
                    (
                        "IDS-STAGE095",
                        "IDS-STAGE095-REVIEW",
                        "IDS-V0_1-STAGE095-REVIEW",
                        "IDS-STAGE096-P1-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P1",
                        "IDS-V0_1-STAGE096-P1",
                        "IDS-STAGE096-P2-GATE",
                    ),
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
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-REVIEW",
                        "IDS-V0_1-STAGE096-REVIEW",
                        "IDS-STAGE097-P1-GATE",
                    ),
                    (
                        "IDS-STAGE097",
                        "IDS-STAGE097-P1",
                        "IDS-V0_1-STAGE097-P1",
                        "IDS-STAGE097-P2-GATE",
                    ),
                    (
                        "IDS-STAGE097",
                        "IDS-STAGE097-P2",
                        "IDS-V0_1-STAGE097-P2",
                        "IDS-STAGE097-P3-GATE",
                    ),
                   (
                       "IDS-STAGE097",
                       "IDS-STAGE097-P3",
                       "IDS-V0_1-STAGE097-P3",
                       "IDS-STAGE097-P4-GATE",
                   ),
                    (
                        "IDS-STAGE097",
                        "IDS-STAGE097-P4",
                        "IDS-V0_1-STAGE097-P4",
                        "IDS-STAGE097-REVIEW-GATE",
                    ),
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
                        "IDS-STAGE093",
                        "IDS-STAGE093-REVIEW",
                        "IDS-V0_1-STAGE093-REVIEW",
                        "IDS-STAGE094-P1-GATE",
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
                        "IDS-STAGE094",
                        "IDS-STAGE094-P4",
                        "IDS-V0_1-STAGE094-P4",
                        "IDS-STAGE094-REVIEW-GATE",
                    ),
                    (
                        "IDS-STAGE094",
                        "IDS-STAGE094-REVIEW",
                        "IDS-V0_1-STAGE094-REVIEW",
                        "IDS-STAGE095-P1-GATE",
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
