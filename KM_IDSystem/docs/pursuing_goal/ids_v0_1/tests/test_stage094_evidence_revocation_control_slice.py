import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE094_PHASE2_EVIDENCE_REVOCATION_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_control_slice_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage094_evidence_revocation_control_slice.py"
P1_SCOPE = BASE / "STAGE094_PHASE1_EVIDENCE_REVOCATION_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage094_evidence_revocation_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE093_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_stage_review_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-094_证据撤回.md"
)
P1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage094-p1-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage094-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "stage094_evidence_revocation_control_slice", MODULE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage094EvidenceRevocationControlSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.p1_contract = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module()
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_evidence_revocation_control_slice(
            cls.control_input
        )

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            P1_SCOPE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessor_and_phase_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage094.evidence_revocation.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-094", contract["stage"])
        self.assertEqual("IDS-STAGE094-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE094-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_EVIDENCE_REVOCATION_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE094-P3-GATE", contract["next_gate"])

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE094_TASKPACK_AND_STAGE094_PHASE1_STAGE093_REVIEWED_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field, value in source.items():
            if field not in {
                "authority",
                "frozen_taskpack_ref",
                "stage094_phase1_scope_ref",
                "stage094_phase1_contract_ref",
                "stage094_phase1_receipt_ref",
                "stage093_review_ref",
                "stage093_review_contract_ref",
                "stage093_review_receipt_ref",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

        predecessor = contract["predecessor_contract"]
        for field in (
            "stage093_review_required",
            "stage094_phase1_required",
            "reviewed_evidence_grade_artifacts_remain_authoritative",
            "stage094_phase2_may_not_replace_predecessor_contracts",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage093_review_evidence_declared",
            "stage094_started",
            "stage094_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage095_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertFalse(self.p1_contract["stage_and_phase_boundary"]["phase2_started"])

    def test_fixed_control_input_is_exact_nonbusiness_and_reference_only(self):
        contract_input = self.contract["reference_only_control_input_contract"]
        self.assertEqual(
            self.module.CONTROL_FIELDS, tuple(contract_input["control_fields"])
        )
        self.assertEqual(self.module.INPUT_FIELDS, tuple(contract_input["input_fields"]))
        self.assertEqual(
            len(self.module.INPUT_FIELDS), contract_input["input_field_count"]
        )

        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(
            tuple(contract_input["fixed_control_scenarios"]),
            tuple(item["control_scenario"] for item in requests),
        )
        self.assertEqual(contract_input["control_request_count"], len(requests))
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                for field in (
                    "evidence_ledger_ref",
                    "evidence_capture_ref",
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
                    "risk_score_ref",
                    "revocation_status_ref",
                    "revocation_reason_ref",
                    "degradation_status_ref",
                    "recovery_reference_ref",
                    "poisoning_defense_status_ref",
                    "report_status_impact_ref",
                ):
                    self.assertIn(self.module.CONTROL_PREFIX, request[field])
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
                    request["human_whitebox_review_state"],
                )
                self.assertEqual(
                    "CONTROL_EVIDENCE_CAPTURE_REFERENCE_DECLARED_NOT_EXECUTED",
                    request["capture_state"],
                )
                self.assertEqual(
                    "CONTROL_RISK_REFERENCE_OWNER_FORMULA_REQUIRED_NOT_CALCULATED",
                    request["risk_assessment_state"],
                )
        self.assertIsNone(requests[0]["evidence_id_ref"])
        self.assertTrue(all(item["evidence_id_ref"] for item in requests[1:]))

    def test_exact_projection_shapes_and_phase1_shape_are_preserved(self):
        projections = self.contract["control_projection_contract"]
        self.assertTrue(self.result["input_accepted"])
        self.assertEqual(
            "CONTROL_EVIDENCE_REVOCATION_PROJECTIONS_DECLARED",
            self.result["execution_state"],
        )
        self.assertIsNone(self.result["failure_state"])
        self.assertEqual(6, self.result["control_input_count"])
        self.assertEqual(11, projections["control_projection_group_count"])
        self.assertEqual(
            self.p1_contract["evidence_revocation_contract"][
                "future_evidence_revocation_relation_fields"
            ],
            list(self.module.EVIDENCE_REVOCATION_RELATION_FIELDS),
        )
        p1_fields = set(
            self.p1_contract["evidence_revocation_contract"][
                "future_evidence_revocation_fields"
            ]
        )
        self.assertTrue(p1_fields.issubset(set(self.module.INPUT_FIELDS)))

        total = 0
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                expected_fields = projections[f"{prefix}_projection_fields"]
                records = self.result[f"{prefix}_control_projections"]
                self.assertEqual(fields, tuple(expected_fields))
                self.assertEqual(6, self.result[f"{prefix}_control_projection_count"])
                self.assertEqual(6, len(records))
                self.assertEqual(
                    projections[f"{prefix}_projection_field_count"],
                    len(fields),
                )
                total += len(fields)
                for record in records:
                    self.assertEqual(set(fields), set(record))
        self.assertEqual(105, total)
        self.assertEqual(
            total, projections["control_projection_field_total_per_request"]
        )
        self.assertEqual(6 * total, projections["control_projection_field_total"])

    def test_binding_capture_risk_revocation_and_conclusion_chain_are_exact(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        for index, request in enumerate(requests):
            with self.subTest(scenario=request["control_scenario"]):
                schema = self.result[
                    "evidence_revocation_schema_binding_control_projections"
                ][index]
                relation = self.result[
                    "evidence_revocation_relation_control_projections"
                ][index]
                capture = self.result[
                    "retrieval_evidence_capture_binding_control_projections"
                ][index]
                risk = self.result["risk_reference_binding_control_projections"][index]
                grade = self.result["evidence_grade_binding_control_projections"][index]
                revocation = self.result[
                    "revocation_control_control_projections"
                ][index]
                conclusion = self.result[
                    "critical_conclusion_binding_control_projections"
                ][index]
                self.assertEqual(
                    self.module.PHASE1_EVIDENCE_REVOCATION_CONTRACT_CONTROL_REF,
                    schema["phase1_evidence_revocation_contract_ref"],
                )
                self.assertEqual(
                    self.module.STAGE093_REVIEW_CONTROL_REF,
                    schema["stage093_review_control_ref"],
                )
                self.assertEqual(
                    "CONTROL_PHASE1_EVIDENCE_REVOCATION_SHAPE_BOUND",
                    schema["schema_binding_state"],
                )
                for field in self.module.EVIDENCE_REVOCATION_RELATION_FIELDS:
                    self.assertEqual(request[field], relation[field])
                for field in self.module.RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS:
                    self.assertEqual(request[field], capture[field])
                for field in self.module.RISK_REFERENCE_BINDING_FIELDS:
                    self.assertEqual(request[field], risk[field])
                for field in self.module.EVIDENCE_GRADE_BINDING_FIELDS:
                    self.assertEqual(request[field], grade[field])
                self.assertEqual(
                    request["revocation_status_ref"],
                    revocation["revocation_status_ref"],
                )
                self.assertEqual(
                    request["revocation_reason_ref"],
                    revocation["revocation_reason_ref"],
                )
                self.assertEqual(
                    request["recovery_reference_ref"],
                    revocation["recovery_reference_ref"],
                )
                self.assertEqual(
                    request["critical_conclusion_ref"],
                    conclusion["critical_conclusion_ref"],
                )
                self.assertEqual(request["evidence_id_ref"], conclusion["evidence_id_ref"])
                self.assertEqual(
                    request["evidence_gap_ref"], conclusion["evidence_gap_ref"]
                )
                self.assertTrue(
                    conclusion["evidence_id_ref"] is not None
                    or conclusion["evidence_gap_ref"] is not None
                )

    def test_degradation_revocation_and_quarantine_stay_in_whitebox_control_states(
        self,
    ):
        expected = {
            "internal_material_insufficient_revocation_pending_whitebox_review_reference_only": (
                "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
                "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW",
            ),
            "low_trust_evidence_degraded_reference_only": (
                "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_TRUST",
            ),
            "conflict_evidence_degraded_reference_only": (
                "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
            ),
            "expired_evidence_degraded_reference_only": (
                "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_EXPIRED",
            ),
            "revoked_evidence_revocation_and_degradation_reference_only": (
                "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_REVOKED_PENDING_WHITEBOX_REVIEW",
            ),
            "suspected_poisoning_evidence_quarantined_reference_only": (
                "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING",
            ),
        }
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        degradations = self.result["degradation_control_projections"]
        impacts = self.result["report_status_impact_control_projections"]
        poison_defenses = self.result["poisoning_defense_control_projections"]
        revocations = self.result["revocation_control_control_projections"]
        for request, degradation, impact, poison_defense, revocation in zip(
            requests, degradations, impacts, poison_defenses, revocations
        ):
            with self.subTest(scenario=request["control_scenario"]):
                expected_degradation, expected_impact = expected[
                    request["control_scenario"]
                ]
                self.assertEqual(expected_degradation, degradation["degradation_state"])
                self.assertEqual(
                    expected_impact, impact["report_status_impact_state"]
                )
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
                    poison_defense["human_whitebox_review_state"],
                )
                self.assertEqual(
                    "CONTROL_POISONING_DEFENSE_ROUTE_DECLARED_NOT_EXECUTED",
                    poison_defense["defense_state"],
                )
                self.assertIn(
                    "CONTROL_REVOCATION_REFERENCE",
                    revocation["revocation_state"],
                )

    def test_nonfixed_control_input_keeps_empty_projections(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][1]["evidence_grade_label"] = "A"
        rejected = self.module.execute_evidence_revocation_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_EVIDENCE_REVOCATION_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            self.assertEqual([], rejected[f"{prefix}_control_projections"])
            self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_boundary_and_actual_counts_stay_zero(self):
        self.assertFalse(self.result["persistent_record_created"])
        for field, value in self.result.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        for field, value in self.result["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"],
            len(failures["declared_failure_states"]),
        )
        for state in (
            "EVIDENCE_ID_AND_GAP_BOTH_MISSING",
            "REVOKED_EVIDENCE_NOT_DEGRADED",
            "SUSPECTED_POISONING_EVIDENCE_NOT_QUARANTINED",
            "REVOCATION_OR_DEGRADATION_AUTO_EXECUTED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])

    def test_scope_rollback_and_current_governance_keep_the_next_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "29 个字段",
            "105 个投影字段",
            "低可信、冲突、过期和撤回场景保持降级候选",
            "疑似投毒场景保持隔离候选",
            "业务线白箱人工复核",
            "模型 Token",
            "IDS-STAGE094-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE1_EVIDENCE_REVOCATION_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage094_phase1_evidence",
            "preserve_stage093_review_evidence",
            "preserve_stage093_phase1_to_phase4_evidence",
        ):
            with self.subTest(field=field):
                self.assertTrue(rollback[field])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

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
        stage094_phase2_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P2",
            "IDS-V0_1-STAGE094-P2",
            "IDS-STAGE094-P3-GATE",
        )
        stage094_phase1_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P1",
            "IDS-V0_1-STAGE094-P1",
            "IDS-STAGE094-P2-GATE",
        )
        stage094_phase3_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P3",
            "IDS-V0_1-STAGE094-P3",
            "IDS-STAGE094-P4-GATE",
        )
        stage094_phase4_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P4",
            "IDS-V0_1-STAGE094-P4",
            "IDS-STAGE094-REVIEW-GATE",
        )
        stage094_review_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-REVIEW",
            "IDS-V0_1-STAGE094-REVIEW",
            "IDS-STAGE095-P1-GATE",
        )
        if current == stage094_phase2_current:
            self.assertTrue(P1_RECEIPT.is_file())
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            self.assertEqual(
                "P2 受控最小切片已完成",
                acceptance_by_id["ACC-STAGE-094"],
            )
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P2-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P2-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P2-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE094-P2-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE094-P2-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE094-P3-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_EVIDENCE_REVOCATION_CONTROL_SLICE_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE094-P2", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage094_phase2_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE094-P2"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE094-P3-GATE"', roadmap_text)
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
                    stage094_phase1_current,
                    stage094_phase3_current,
                    stage094_phase4_current,
                    stage094_review_current,
                ),
            )


if __name__ == "__main__":
    unittest.main()
