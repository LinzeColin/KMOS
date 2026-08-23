import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE091_PHASE2_EVIDENCE_GAP_HANDLING_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_control_slice_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage091_evidence_gap_handling_control_slice.py"
)
P1_SCOPE = BASE / "STAGE091_PHASE1_EVIDENCE_GAP_HANDLING_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage091_evidence_gap_handling_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE090_STAGE_REVIEW.md"
PREDECESSOR_REVIEW_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage090_retrieval_evidence_capture_stage_review_contract.json"
)
PREDECESSOR_CONTROL_SLICE_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage090_retrieval_evidence_capture_control_slice_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-091_证据缺口处理.md"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "stage091_evidence_gap_handling_control_slice", MODULE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage091EvidenceGapHandlingControlSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.p1_contract = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module()
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_evidence_gap_handling_control_slice(
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
            PREDECESSOR_REVIEW_CONTRACT,
            PREDECESSOR_CONTROL_SLICE_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessor_and_phase_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage091.evidence_gap_handling.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-091", contract["stage"])
        self.assertEqual("IDS-STAGE091-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE091-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_EVIDENCE_GAP_HANDLING_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE091-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE091_TASKPACK_AND_STAGE091_PHASE1_STAGE090_REVIEWED_RETRIEVAL_EVIDENCE_CAPTURE_CONTROL_ARTIFACTS_ONLY",
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
            "stage090_review_required",
            "stage091_phase1_required",
            "stage090_retrieval_evidence_capture_binding_required",
            "stage091_phase2_may_not_replace_predecessor_contracts",
        ):
            with self.subTest(field=field):
                self.assertTrue(predecessor[field])
        self.assertFalse(predecessor["actual_predecessor_runtime_artifact_read_performed"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage090_review_evidence_declared",
            "stage091_started",
            "stage091_entry_authorized",
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
            "stage092_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertFalse(
            self.p1_contract["stage_and_phase_boundary"]["phase2_started"]
        )

    def test_fixed_control_input_is_exact_nonbusiness_and_reference_only(self):
        contract_input = self.contract["reference_only_control_input_contract"]
        self.assertEqual(
            self.module.CONTROL_FIELDS,
            tuple(contract_input["control_fields"]),
        )
        self.assertEqual(
            self.module.INPUT_FIELDS,
            tuple(contract_input["input_fields"]),
        )
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
                    "evidence_capture_ref",
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
                    "risk_score_ref",
                    "revocation_state_ref",
                    "poisoning_defense_state_ref",
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
        self.assertIsNone(requests[0]["evidence_id_ref"])
        self.assertTrue(all(item["evidence_id_ref"] for item in requests[1:]))

    def test_exact_projection_shapes_and_field_total_are_preserved(self):
        projections = self.contract["control_projection_contract"]
        self.assertTrue(self.result["input_accepted"])
        self.assertEqual(
            "CONTROL_EVIDENCE_GAP_HANDLING_PROJECTIONS_DECLARED_NOT_EXECUTED",
            self.result["execution_state"],
        )
        self.assertIsNone(self.result["failure_state"])
        self.assertEqual(6, self.result["control_input_count"])
        self.assertEqual(10, projections["control_projection_group_count"])
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
        self.assertEqual(78, total)
        self.assertEqual(
            total, projections["control_projection_field_total_per_request"]
        )
        self.assertEqual(6 * total, projections["control_projection_field_total"])

    def test_gap_relation_capture_risk_revocation_and_conclusion_chain_is_exact(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        for index, request in enumerate(requests):
            with self.subTest(scenario=request["control_scenario"]):
                schema = self.result["evidence_gap_schema_binding_control_projections"][
                    index
                ]
                relation = self.result["evidence_gap_relation_control_projections"][
                    index
                ]
                capture = self.result[
                    "retrieval_evidence_capture_binding_control_projections"
                ][index]
                risk = self.result["risk_score_control_projections"][index]
                revocation = self.result["revocation_control_projections"][index]
                conclusion = self.result[
                    "critical_conclusion_binding_control_projections"
                ][index]
                self.assertEqual(
                    self.module.PHASE1_EVIDENCE_GAP_CONTRACT_CONTROL_REF,
                    schema["phase1_evidence_gap_contract_ref"],
                )
                self.assertEqual(
                    self.module.STAGE090_REVIEW_CONTROL_REF,
                    schema["stage090_review_control_ref"],
                )
                self.assertEqual(
                    "CONTROL_PHASE1_EVIDENCE_GAP_SHAPE_BOUND_NOT_REDEFINED",
                    schema["schema_binding_state"],
                )
                for field in self.module.EVIDENCE_GAP_RELATION_FIELDS:
                    self.assertEqual(request[field], relation[field])
                for field in self.module.RETRIEVAL_EVIDENCE_CAPTURE_BINDING_FIELDS:
                    self.assertEqual(request[field], capture[field])
                self.assertEqual(request["risk_score_ref"], risk["risk_score_ref"])
                self.assertEqual(
                    request["revocation_state_ref"], revocation["revocation_state_ref"]
                )
                self.assertEqual(
                    request["critical_conclusion_ref"],
                    conclusion["critical_conclusion_ref"],
                )
                self.assertEqual(request["evidence_id_ref"], conclusion["evidence_id_ref"])
                self.assertEqual(request["evidence_gap_ref"], conclusion["evidence_gap_ref"])
                self.assertTrue(
                    conclusion["evidence_id_ref"] is not None
                    or conclusion["evidence_gap_ref"] is not None
                )

    def test_gap_and_degradation_scenarios_stay_in_whitebox_control_states(self):
        expected = {
            "internal_material_insufficient_gap_pending_whitebox_review_reference_only": (
                "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW",
                "CONTROL_REPORT_STATUS_REFERENCE_PENDING_EVIDENCE_GAP_REVIEW",
            ),
            "low_grade_evidence_gap_degraded_reference_only": (
                "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_LOW_TRUST",
            ),
            "conflict_evidence_gap_degraded_reference_only": (
                "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_CONFLICT",
            ),
            "expired_evidence_gap_degraded_reference_only": (
                "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_EXPIRED",
            ),
            "revoked_evidence_gap_degraded_reference_only": (
                "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_DEGRADED_REVOKED",
            ),
            "suspected_poisoning_gap_quarantined_reference_only": (
                "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
                "CONTROL_REPORT_STATUS_REFERENCE_QUARANTINED_SUSPECTED_POISONING",
            ),
        }
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        degradations = self.result["degradation_control_projections"]
        impacts = self.result["report_status_impact_control_projections"]
        poison_defenses = self.result["poisoning_defense_control_projections"]
        for request, degradation, impact, poison_defense in zip(
            requests, degradations, impacts, poison_defenses
        ):
            with self.subTest(scenario=request["control_scenario"]):
                expected_degradation, expected_impact = expected[
                    request["control_scenario"]
                ]
                self.assertEqual(expected_degradation, degradation["degradation_state"])
                self.assertEqual(expected_impact, impact["report_status_impact_state"])
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
                    poison_defense["human_whitebox_review_state"],
                )
                self.assertEqual(
                    "CONTROL_POISONING_DEFENSE_REFERENCE_NOT_EXECUTED",
                    poison_defense["defense_state"],
                )

    def test_nonfixed_control_input_fails_closed_without_projections(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][1]["evidence_grade_label"] = "A"
        rejected = self.module.execute_evidence_gap_handling_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_EVIDENCE_GAP_HANDLING_CONTROL_SLICE",
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
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(contract_field=field):
                self.assertFalse(value)

    def test_scope_and_rollback_keep_the_next_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "资料不足场景允许关键结论只关联 `evidence_gap_ref`",
            "低可信、冲突、过期和撤回场景固定为降级候选",
            "疑似投毒场景固定为隔离候选",
            "业务线白箱人工复核",
            "模型 Token",
            "IDS-STAGE091-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE1_EVIDENCE_GAP_HANDLING_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage091_phase1_evidence",
            "preserve_stage090_review_evidence",
            "preserve_stage090_phase1_to_phase4_evidence",
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


if __name__ == "__main__":
    unittest.main()
