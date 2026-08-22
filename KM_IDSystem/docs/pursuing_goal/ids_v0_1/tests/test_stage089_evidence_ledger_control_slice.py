import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE089_PHASE2_EVIDENCE_LEDGER_CONTROL_SLICE.md"
CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_control_slice_contract.json"
MODULE = BASE / "index_version_schema" / "stage089_evidence_ledger_control_slice.py"
P1_SCOPE = BASE / "STAGE089_PHASE1_EVIDENCE_LEDGER_SCHEMA_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_schema_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE088_STAGE_REVIEW.md"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-089_证据账本Schema.md"


def load_module():
    spec = importlib.util.spec_from_file_location("stage089_evidence_ledger_control_slice", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage089EvidenceLedgerControlSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.p1_contract = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module()
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_evidence_ledger_control_slice(cls.control_input)

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            P1_SCOPE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            TASKPACK,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage089.evidence_ledger_schema.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-089", contract["stage"])
        self.assertEqual("IDS-STAGE089-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE089-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_EVIDENCE_LEDGER_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE089-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
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
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage088_review_evidence_declared",
            "stage089_started",
            "stage089_entry_authorized",
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
            "stage090_started",
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
                self.assertIn(self.module.CONTROL_PREFIX, request["evidence_id_ref"])
                self.assertIn(self.module.CONTROL_PREFIX, request["document_id_ref"])
                self.assertIn(self.module.CONTROL_PREFIX, request["query_ref"])
                self.assertIn(self.module.CONTROL_PREFIX, request["answer_ref"])
                self.assertIn(self.module.CONTROL_PREFIX, request["report_id_ref"])
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_REVIEW_REQUIRED",
                    request["human_whitebox_review_state"],
                )
                self.assertEqual(
                    "CONTROL_EVIDENCE_DECLARED_NOT_CAPTURED",
                    request["evidence_state"],
                )

    def test_exact_projection_shapes_and_field_total_are_preserved(self):
        projections = self.contract["control_projection_contract"]
        self.assertTrue(self.result["input_accepted"])
        self.assertEqual(
            "CONTROL_EVIDENCE_LEDGER_PROJECTIONS_DECLARED_NOT_EXECUTED",
            self.result["execution_state"],
        )
        self.assertIsNone(self.result["failure_state"])
        self.assertEqual(6, self.result["control_input_count"])
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
        self.assertEqual(74, total)
        self.assertEqual(total, projections["control_projection_field_total_per_request"])
        self.assertEqual(6 * total, projections["control_projection_field_total"])

    def test_evidence_relation_capture_risk_revocation_and_binding_chain_is_exact(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        for index, request in enumerate(requests):
            with self.subTest(scenario=request["control_scenario"]):
                evidence = self.result["evidence_schema_control_projections"][index]
                relation = self.result["evidence_relation_control_projections"][index]
                capture = self.result["evidence_capture_control_projections"][index]
                risk = self.result["risk_score_control_projections"][index]
                revocation = self.result["revocation_control_projections"][index]
                binding = self.result["critical_conclusion_binding_control_projections"][index]
                for field in (
                    "evidence_id_ref",
                    "document_id_ref",
                    "chunk_id_ref",
                    "fact_id_ref",
                    "report_id_ref",
                ):
                    self.assertEqual(request[field], evidence[field])
                for field in (
                    "evidence_id_ref",
                    "document_id_ref",
                    "chunk_id_ref",
                    "fact_id_ref",
                    "query_ref",
                    "answer_ref",
                    "report_id_ref",
                ):
                    self.assertEqual(request[field], relation[field])
                self.assertEqual(request["evidence_id_ref"], capture["evidence_id_ref"])
                self.assertEqual(request["retrieval_trace_ref"], capture["retrieval_trace_ref"])
                self.assertEqual(request["risk_score_ref"], risk["risk_score_ref"])
                self.assertEqual(request["revocation_ref"], revocation["revocation_ref"])
                self.assertEqual(
                    request["critical_conclusion_ref"], binding["critical_conclusion_ref"]
                )
                self.assertEqual(request["evidence_id_ref"], binding["evidence_id_ref"])
                self.assertEqual(request["evidence_gap_ref"], binding["evidence_gap_ref"])

    def test_low_conflict_expired_revoked_and_suspected_poisoning_are_not_accepted(self):
        expected = {
            "grade_a_pending_whitebox_review_reference_only": "CONTROL_PENDING_HUMAN_WHITEBOX_REVIEW",
            "low_grade_evidence_degraded_reference_only": "CONTROL_DEGRADED_LOW_TRUST_NOT_ACCEPTED",
            "conflict_evidence_degraded_reference_only": "CONTROL_DEGRADED_CONFLICT_NOT_ACCEPTED",
            "expired_evidence_degraded_reference_only": "CONTROL_DEGRADED_EXPIRED_NOT_ACCEPTED",
            "revoked_evidence_degraded_reference_only": "CONTROL_DEGRADED_REVOKED_NOT_ACCEPTED",
            "suspected_poisoning_quarantined_reference_only": "CONTROL_QUARANTINED_SUSPECTED_POISONING_NOT_ACCEPTED",
        }
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        degradations = self.result["degradation_control_projections"]
        poison_defenses = self.result["poisoning_defense_control_projections"]
        for request, degradation, poison_defense in zip(requests, degradations, poison_defenses):
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(
                    expected[request["control_scenario"]],
                    degradation["degradation_state"],
                )
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
        rejected = self.module.execute_evidence_ledger_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_EVIDENCE_LEDGER_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["actual_input_request_count"])
        for key, value in rejected.items():
            if key.endswith("_projection_count"):
                with self.subTest(key=key):
                    self.assertEqual(0, value)
        self.assertFalse(rejected["persistent_record_created"])
        self.assertTrue(all(value is False for value in rejected["runtime_boundary"].values()))

    def test_failure_runtime_and_protected_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "CONTROL_INPUT_MISMATCH",
            "EVIDENCE_RELATION_REFERENCE_MISSING",
            "CRITICAL_CONCLUSION_EVIDENCE_AND_GAP_BOTH_MISSING",
            "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_GRADE",
            "LOW_TRUST_EVIDENCE_NOT_DEGRADED",
            "CONFLICT_EVIDENCE_NOT_DEGRADED",
            "EXPIRED_EVIDENCE_NOT_DEGRADED",
            "REVOKED_EVIDENCE_NOT_DEGRADED",
            "SUSPECTED_POISONING_EVIDENCE_NOT_QUARANTINED",
            "PHASE2_EVIDENCE_LEDGER_CONTROL_INPUT_REJECTED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        self.assertTrue(all(value is False for value in self.result["runtime_boundary"].values()))
        future = self.contract["future_runtime_prerequisite_contract"]
        for field, value in future.items():
            if field.endswith("_is_future_authorized_work_only"):
                with self.subTest(field=field):
                    self.assertTrue(value)
            else:
                with self.subTest(field=field):
                    self.assertFalse(value)
        allowed_local_code = {
            "control_slice_created",
            "pure_in_memory_only",
            "evidence_schema_control_slice_created",
            "retrieval_evidence_capture_control_slice_created",
            "risk_score_control_slice_created",
            "revocation_control_slice_created",
            "poisoning_defense_control_slice_created",
            "degradation_control_slice_created",
        }
        for field, value in self.contract["local_code"].items():
            with self.subTest(field=field):
                self.assertEqual(field in allowed_local_code, value)
        self.assertFalse(self.result["persistent_record_created"])

    def test_scope_and_rollback_keep_only_phase3_next(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "document、chunk、fact、query、answer、report",
            "低可信、冲突、过期和撤回",
            "疑似投毒",
            "业务线白箱人工复核",
            "IDS-STAGE089-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_EVIDENCE_LEDGER_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage089_phase1_evidence"])
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
