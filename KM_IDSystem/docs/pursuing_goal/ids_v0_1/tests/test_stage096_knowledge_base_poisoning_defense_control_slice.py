import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE096_PHASE2_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_control_slice.py"
)
P1_SCOPE = BASE / "STAGE096_PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_SCOPE_BOUNDARY.md"
P1_CONTRACT = (
    BASE / "index_version_schema" / "stage096_knowledge_base_poisoning_defense_contract.json"
)
P1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage096-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE095_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_stage_review_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-096_知识库投毒防护.md"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage096-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "stage096_knowledge_base_poisoning_defense_control_slice", MODULE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage096KnowledgeBasePoisoningDefenseControlSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.p1_contract = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module()
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_knowledge_base_poisoning_defense_control_slice(
            cls.control_input
        )

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            P1_SCOPE,
            P1_CONTRACT,
            P1_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessor_and_phase_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage096.knowledge_base_poisoning_defense.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-096", contract["stage"])
        self.assertEqual("IDS-STAGE096-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE096-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE096-P3-GATE", contract["next_gate"])

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE096_TASKPACK_AND_STAGE096_PHASE1_STAGE095_REVIEWED_CONTROL_ARTIFACTS_ONLY",
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

        predecessor = contract["predecessor_contract"]
        for field in (
            "stage095_review_required",
            "stage096_phase1_required",
            "reviewed_evidence_regression_artifacts_remain_authoritative",
            "stage096_phase2_may_not_replace_predecessor_contracts",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])

        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage095_review_evidence_declared",
            "stage096_started",
            "stage096_entry_authorized",
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
            "stage097_started",
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
        reference_fields = (
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
            "risk_score_ref",
            "evidence_grade_ref",
            "revocation_status_ref",
            "poisoning_defense_status_ref",
        )
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                for field in reference_fields:
                    if request[field] is not None:
                        self.assertTrue(
                            request[field].startswith(self.module.CONTROL_PREFIX)
                        )
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
        self.assertIsNotNone(requests[0]["evidence_gap_ref"])
        self.assertTrue(all(item["evidence_id_ref"] for item in requests[1:]))
        self.assertTrue(all(item["evidence_gap_ref"] is None for item in requests[1:]))

    def test_exact_projection_shapes_and_phase1_relation_are_preserved(self):
        projections = self.contract["control_projection_contract"]
        self.assertTrue(self.result["input_accepted"])
        self.assertEqual(
            "CONTROL_KNOWLEDGE_BASE_POISONING_DEFENSE_PROJECTIONS_DECLARED",
            self.result["execution_state"],
        )
        self.assertIsNone(self.result["failure_state"])
        self.assertEqual(6, self.result["control_input_count"])
        self.assertEqual(6, projections["control_projection_group_count"])
        self.assertEqual(
            self.p1_contract["knowledge_base_poisoning_defense_contract"][
                "future_knowledge_base_poisoning_defense_fields"
            ],
            [
                "evidence_ledger_ref",
                "evidence_id_ref",
                "evidence_gap_ref",
                "critical_conclusion_ref",
                "risk_score_ref",
                "evidence_grade_ref",
                "revocation_status_ref",
                "poisoning_defense_status_ref",
            ],
        )
        self.assertTrue(
            set(
                self.p1_contract["knowledge_base_poisoning_defense_contract"][
                    "future_knowledge_base_poisoning_defense_fields"
                ]
            ).issubset(set(self.module.INPUT_FIELDS))
        )

        total = 0
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                expected_fields = projections[f"{prefix}_projection_fields"]
                records = self.result[f"{prefix}_control_projections"]
                self.assertEqual(fields, tuple(expected_fields))
                self.assertEqual(6, self.result[f"{prefix}_control_projection_count"])
                self.assertEqual(6, len(records))
                self.assertEqual(
                    projections[f"{prefix}_projection_field_count"], len(fields)
                )
                total += len(fields)
                for record in records:
                    self.assertEqual(set(fields), set(record))
        self.assertEqual(58, total)
        self.assertEqual(
            total, projections["control_projection_field_total_per_request"]
        )
        self.assertEqual(6 * total, projections["control_projection_field_total"])

    def test_binding_capture_risk_revocation_and_conclusion_chain_are_exact(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        for index, request in enumerate(requests):
            with self.subTest(scenario=request["control_scenario"]):
                schema = self.result[
                    "knowledge_base_poisoning_defense_schema_binding_control_projections"
                ][index]
                relation = self.result[
                    "knowledge_base_poisoning_defense_relation_control_projections"
                ][index]
                capture = self.result[
                    "retrieval_evidence_capture_binding_control_projections"
                ][index]
                risk = self.result[
                    "risk_and_evidence_grade_control_control_projections"
                ][index]
                revocation = self.result[
                    "revocation_and_poisoning_control_control_projections"
                ][index]
                conclusion = self.result[
                    "critical_conclusion_and_report_impact_control_projections"
                ][index]
                self.assertEqual(
                    self.module.PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTRACT_CONTROL_REF,
                    schema["phase1_knowledge_base_poisoning_defense_contract_ref"],
                )
                self.assertEqual(
                    self.module.STAGE095_REVIEW_CONTROL_REF,
                    schema["stage095_review_control_ref"],
                )
                self.assertEqual(
                    "CONTROL_PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_SHAPE_BOUND",
                    schema["schema_binding_state"],
                )
                for field in self.module.KNOWLEDGE_BASE_POISONING_DEFENSE_RELATION_FIELDS:
                    self.assertEqual(request[field], relation[field])
                for field in self.module.RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS:
                    self.assertEqual(request[field], capture[field])
                for field in self.module.RISK_AND_EVIDENCE_GRADE_CONTROL_FIELDS:
                    self.assertEqual(request[field], risk[field])
                self.assertEqual(
                    request["revocation_status_ref"], revocation["revocation_status_ref"]
                )
                self.assertEqual(
                    request["poisoning_defense_status_ref"],
                    revocation["poisoning_defense_status_ref"],
                )
                self.assertEqual(
                    request["critical_conclusion_ref"], conclusion["critical_conclusion_ref"]
                )
                self.assertEqual(request["evidence_id_ref"], conclusion["evidence_id_ref"])
                self.assertEqual(
                    request["evidence_gap_ref"], conclusion["evidence_gap_ref"]
                )
                self.assertTrue(
                    conclusion["evidence_id_ref"] is not None
                    or conclusion["evidence_gap_ref"] is not None
                )
                self.assertEqual(
                    "CONTROL_CONCLUSION_BOUND_TO_REFERENCE_ONLY_EVIDENCE_OR_GAP",
                    conclusion["conclusion_binding_state"],
                )

    def test_degradation_quarantine_and_report_impact_stay_in_whitebox_states(self):
        expected = {
            "internal_material_insufficient_evidence_gap_reference_only": (
                "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
                "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW",
                "CONTROL_EVIDENCE_GAP_REFERENCE_PENDING_WHITEBOX_REVIEW",
            ),
            "low_ocr_evidence_degradation_reference_only": (
                "CONTROL_DEGRADED_LOW_OCR_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_OCR",
                "CONTROL_LOW_OCR_DEGRADATION_REFERENCE_NOT_EXECUTED",
            ),
            "old_version_evidence_degradation_reference_only": (
                "CONTROL_DEGRADED_OLD_VERSION_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_OLD_VERSION",
                "CONTROL_OLD_VERSION_DEGRADATION_REFERENCE_NOT_EXECUTED",
            ),
            "conflict_evidence_degradation_reference_only": (
                "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
                "CONTROL_CONFLICT_DEGRADATION_REFERENCE_NOT_EXECUTED",
            ),
            "revoked_evidence_report_review_reference_only": (
                "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_REVOKED_PENDING_WHITEBOX_REVIEW",
                "CONTROL_REVOCATION_REFERENCE_NOT_EXECUTED",
            ),
            "suspected_poisoning_evidence_quarantined_reference_only": (
                "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING",
                "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED",
            ),
        }
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        risks = self.result["risk_and_evidence_grade_control_control_projections"]
        revocations = self.result["revocation_and_poisoning_control_control_projections"]
        conclusions = self.result[
            "critical_conclusion_and_report_impact_control_projections"
        ]
        for request, risk, revocation, conclusion in zip(
            requests, risks, revocations, conclusions
        ):
            with self.subTest(scenario=request["control_scenario"]):
                expected_degradation, expected_impact, expected_action = expected[
                    request["control_scenario"]
                ]
                self.assertEqual(expected_degradation, risk["degradation_state"])
                self.assertEqual(
                    expected_impact, conclusion["report_status_impact_state"]
                )
                self.assertEqual(expected_action, revocation["control_action_state"])
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
                    revocation["human_whitebox_review_state"],
                )

    def test_nonfixed_control_input_keeps_empty_projections(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][1]["evidence_grade_label"] = "A"
        invalid_input["unexpected"] = []
        rejected = self.module.execute_knowledge_base_poisoning_defense_control_slice(
            invalid_input
        )
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            self.assertEqual([], rejected[f"{prefix}_control_projections"])
            self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_boundary_actual_counts_and_failure_contract_stay_closed(self):
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
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "EVIDENCE_ID_AND_GAP_BOTH_MISSING",
            "LOW_OCR_EVIDENCE_NOT_DEGRADED",
            "REVOKED_EVIDENCE_NOT_DEGRADED",
            "SUSPECTED_POISONING_EVIDENCE_NOT_QUARANTINED",
            "REPORT_STATUS_AUTO_UPDATED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertEqual(4, len(self.contract["operator_feedback"]))

    def test_scope_rollback_and_current_governance_keep_the_next_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "21 个字段",
            "58 个投影字段",
            "低 OCR、旧版本、冲突和撤回资料保持降级候选",
            "疑似恶意资料保持隔离候选",
            "业务线白箱人工复核",
            "模型 Token",
            "IDS-STAGE096-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE1_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage096_phase1_evidence",
            "preserve_stage095_review_evidence",
            "preserve_stage095_phase1_to_phase4_evidence",
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
        stage096_p2_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P2",
            "IDS-V0_1-STAGE096-P2",
            "IDS-STAGE096-P3-GATE",
        )
        if current == stage096_p2_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-096"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P2-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P2-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE096-P2-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE096-P2-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE096-P2-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE096-P3-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_CONTROL_SLICE_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("IDS-V0_1-STAGE096-P2", plan["task"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage096_phase2_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE096-P2"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE096-P3-GATE"', roadmap_text)
        else:
            self.assertIn(
                current,
                (
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P1",
                        "IDS-V0_1-STAGE096-P1",
                        "IDS-STAGE096-P2-GATE",
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
                ),
            )


if __name__ == "__main__":
    unittest.main()
