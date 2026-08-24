import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE093_PHASE4_EVIDENCE_GRADE_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage093_evidence_grade_delivery.py"
P3_SCOPE = BASE / "STAGE093_PHASE3_EVIDENCE_GRADE_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE / "index_version_schema" / "stage093_evidence_grade_controlled_scenarios.py"
)
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage093_evidence_grade_control_slice_contract.json"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage093_evidence_grade_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE092_STAGE_REVIEW.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-093_证据可信等级A_B_C_D_E.md"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage093-p4-local.json"
P3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage093-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage093EvidenceGradePhase4DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage093_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage093_phase3_scenarios", P3_MODULE)
        cls.report = cls.module.build_evidence_grade_phase4_delivery_report()

    def _phase3_report(self):
        return self.phase3.build_evidence_grade_phase3_report()

    def test_artifacts_identity_and_frozen_taskpack_exist(self):
        for path in (
            SCOPE,
            CONTRACT,
            MODULE,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P2_CONTRACT,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            TASKPACK,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual("IDS-STAGE093-P4", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE093-P4", self.contract["task_id"])
        self.assertEqual("IDS-STAGE093-P4-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE093-REVIEW-GATE", self.contract["next_gate"])

    def test_contract_keeps_single_authority_runtime_and_review_closed(self):
        authority = self.contract["source_authority"]
        for field in (
            "delivery_control_metadata_can_replace_source_document",
            "delivery_control_metadata_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "evidence_ledger_access_performed",
            "report_or_audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_whitebox_human_review_remains_authoritative"])
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(27, replay["required_control_input_field_count"])
        self.assertEqual(11, replay["phase2_projection_group_count"])
        self.assertEqual(600, replay["phase2_control_field_check_count"])
        self.assertEqual(7, replay["scenario_count"])
        self.assertEqual(32, replay["scenario_field_count"])
        self.assertEqual(224, replay["scenario_field_check_count"])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertEqual(517, delivery["delivery_field_check_count"])
        for field in (
            "evidence_ledger_sample_control_record_count",
            "evidence_grade_report_control_record_count",
            "revocation_impact_control_record_count",
            "regression_test_control_record_count",
            "non_conclusion_evidence_type_control_record_count",
        ):
            with self.subTest(field=field):
                self.assertEqual(7, delivery[field])
        self.assertFalse(delivery["actual_evidence_ledger_sample_written"])
        self.assertFalse(delivery["actual_revocation_execution_performed"])
        runtime = self.contract["runtime_boundary"]
        self.assertTrue(
            all(
                value in (0, False)
                for value in runtime.values()
            )
        )
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage092_review_evidence_declared",
            "stage093_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage093_review_started",
            "stage094_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_report_replays_phase3_exact_shape_without_runtime(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertTrue(report["phase3_control_shape_preserved"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(27, report["phase2_control_input_field_count"])
        self.assertEqual(11, report["phase2_projection_group_count"])
        self.assertEqual(600, report["phase2_control_field_check_count"])
        self.assertEqual(7, report["phase3_scenario_count"])
        self.assertEqual(32, report["phase3_scenario_field_count"])
        self.assertEqual(224, report["phase3_scenario_field_check_count"])
        self.assertEqual(517, report["delivery_field_check_count"])
        self.assertTrue(all(value is False for value in report["runtime_boundary"].values()))

    def test_all_delivery_groups_keep_exact_shape_and_control_references(self):
        groups = (
            ("evidence_ledger_sample_control_records", 7, self.module.EVIDENCE_LEDGER_SAMPLE_FIELDS),
            ("evidence_grade_report_control_records", 7, self.module.EVIDENCE_GRADE_REPORT_FIELDS),
            ("revocation_impact_control_records", 7, self.module.REVOCATION_IMPACT_FIELDS),
            ("regression_test_control_records", 7, self.module.REGRESSION_TEST_RECORD_FIELDS),
            ("non_conclusion_evidence_type_control_records", 7, self.module.NON_CONCLUSION_EVIDENCE_TYPE_FIELDS),
            ("degradation_instruction_control_records", 4, self.module.DEGRADATION_INSTRUCTION_FIELDS),
            ("revocation_recovery_instruction_control_records", 2, self.module.REVOCATION_RECOVERY_INSTRUCTION_FIELDS),
        )
        for key, expected_count, fields in groups:
            records = self.report[key]
            self.assertEqual(expected_count, len(records), key)
            for record in records:
                self.assertEqual(set(fields), set(record), key)
                for field, value in record.items():
                    if field.endswith("_ref"):
                        allowed_none = (
                            field == "evidence_id_ref"
                            and record.get("scenario_id")
                            == "no_internal_evidence_grade_control"
                            and value is None
                        )
                        self.assertTrue(
                            allowed_none
                            or self.module.CONTROL_PREFIX in value
                            or self.module.DELIVERY_PREFIX in value,
                            (key, field, value),
                        )

    def test_taskpack_delivery_non_conclusion_and_revocation_rules_hold(self):
        taskpack = TASKPACK.read_text(encoding="utf-8")
        for required_text in (
            "evidence ledger 样例",
            "证据等级报告",
            "撤回影响清单",
            "回归测试",
            "不可作为结论依据",
            "降级",
            "撤回",
            "恢复",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, taskpack)
        revoked = {
            item["scenario_id"]: item
            for item in self.report["revocation_impact_control_records"]
        }["revoked_evidence_grade_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        for record in self.report["non_conclusion_evidence_type_control_records"]:
            self.assertEqual("CONTROL_NOT_A_CONCLUSION_BASIS", record["non_conclusion_state"])
            self.assertFalse(record["automatic_conclusion_allowed"])

    def test_degradation_recovery_and_chinese_feedback_remain_manual(self):
        targets = {
            item["degradation_target_state"]
            for item in self.report["degradation_instruction_control_records"]
        }
        self.assertEqual(
            {
                "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
                "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
                "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
                "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
            },
            targets,
        )
        for record in self.report["degradation_instruction_control_records"]:
            self.assertFalse(record["actual_evidence_degradation_performed"])
            self.assertFalse(record["automatic_degradation_allowed"])
            self.assertTrue(record["human_handling_required"])
        for record in self.report["revocation_recovery_instruction_control_records"]:
            self.assertFalse(record["actual_revocation_execution_performed"])
            self.assertFalse(record["actual_recovery_execution_performed"])
            self.assertTrue(record["human_handling_required"])
        feedback = self.report["chinese_feedback"]
        self.assertEqual(4, len(feedback))
        self.assertTrue(all(isinstance(message, str) and message for message in feedback))

    def test_failure_contract_is_complete_and_review_stays_closed(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "PHASE3_CONTROL_OUTPUT_INVALID",
            "PHASE3_RUNTIME_SIGNAL_DETECTED",
            "CONTROL_REFERENCE_NOT_OPAQUE",
            "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
            "DELIVERY_RECORD_SHAPE_MISMATCH",
            "AUTOMATIC_CONCLUSION_ALLOWED",
            "AUTOMATIC_REVOCATION_OR_RECOVERY_ALLOWED",
            "STAGE_REVIEW_STARTED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertFalse(self.report["whole_stage_review_performed"])
        self.assertFalse(self.report["stage093_review_started"])
        self.assertFalse(self.report["stage094_started"])
        self.assertFalse(self.report["github_upload_allowed"])
        self.assertFalse(self.report["push_allowed"])
        self.assertTrue(self.report["source_document_remains_authoritative"])
        self.assertTrue(self.report["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(self.report["second_authoritative_source_created"])

    def test_invalid_predecessor_fails_closed(self):
        failed = self.module.build_evidence_grade_phase4_delivery_report(lambda: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual([], failed["evidence_ledger_sample_control_records"])

    def test_predecessor_runtime_and_nonopaque_reference_fail_closed(self):
        def runtime_signal():
            altered = copy.deepcopy(self._phase3_report())
            altered["runtime_boundary"][self.phase3.RUNTIME_CLOSED_FIELDS[0]] = True
            return altered

        failed = self.module.build_evidence_grade_phase4_delivery_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])

        def nonopaque_reference():
            altered = copy.deepcopy(self._phase3_report())
            altered["scenario_results"][1]["document_id_ref"] = "document:external"
            return altered

        failed = self.module.build_evidence_grade_phase4_delivery_report(
            nonopaque_reference
        )
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])

    def test_semantic_drift_for_gap_revocation_and_masquerade_fails_closed(self):
        cases = (
            (
                "no_internal",
                "no_internal_evidence_grade_control",
                "evidence_id_ref",
                "evidence:control:stage093-p2:unexpected",
                "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING",
            ),
            (
                "degradation",
                "low_ocr_evidence_grade_degradation_control",
                "evidence_disposition_state",
                "CONTROL_UNEXPECTED",
                "EVIDENCE_DEGRADATION_DISPOSITION_MISSING",
            ),
            (
                "revocation",
                "revoked_evidence_grade_report_impact_control",
                "report_status_impact_state",
                "CONTROL_UNEXPECTED",
                "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
            ),
            (
                "malicious",
                "malicious_evidence_grade_quarantine_control",
                "evidence_disposition_state",
                "CONTROL_UNEXPECTED",
                "MALICIOUS_EVIDENCE_QUARANTINE_MISSING",
            ),
            (
                "masquerade",
                "low_grade_high_trust_masquerade_control",
                "high_trust_conclusion_allowed",
                True,
                "LOW_GRADE_MASQUERADE_REJECTION_MISSING",
            ),
        )
        for name, scenario_id, field, value, expected in cases:
            with self.subTest(name=name):
                altered = copy.deepcopy(self._phase3_report())
                scenario = next(
                    item
                    for item in altered["scenario_results"]
                    if item["scenario_id"] == scenario_id
                )
                scenario[field] = value
                failed = self.module.build_evidence_grade_phase4_delivery_report(
                    lambda altered=altered: altered
                )
                self.assertFalse(failed["valid"])
                self.assertEqual(expected, failed["failure_state"])

    def test_predecessor_p4_record_remains_immutable_after_review_completion(self):
        for path in (RECEIPT, P3_RECEIPT, STATUS, PLAN, ACCEPTANCE, EVENTS, ROADMAP):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn(
            (status["stage"], status["phase"], status["task"]),
            (
                ("IDS-STAGE093", "IDS-STAGE093-REVIEW", "IDS-V0_1-STAGE093-REVIEW"),
                ("IDS-STAGE094", "IDS-STAGE094-P1", "IDS-V0_1-STAGE094-P1"),
                ("IDS-STAGE094", "IDS-STAGE094-P2", "IDS-V0_1-STAGE094-P2"),
                ("IDS-STAGE094", "IDS-STAGE094-P3", "IDS-V0_1-STAGE094-P3"),
                ("IDS-STAGE094", "IDS-STAGE094-P4", "IDS-V0_1-STAGE094-P4"),
                ("IDS-STAGE094", "IDS-STAGE094-REVIEW", "IDS-V0_1-STAGE094-REVIEW"),
                ("IDS-STAGE095", "IDS-STAGE095-P1", "IDS-V0_1-STAGE095-P1"),
                ("IDS-STAGE095", "IDS-STAGE095-P2", "IDS-V0_1-STAGE095-P2"),
                ("IDS-STAGE095", "IDS-STAGE095-P3", "IDS-V0_1-STAGE095-P3"),
                ("IDS-STAGE095", "IDS-STAGE095-P4", "IDS-V0_1-STAGE095-P4"),
                ("IDS-STAGE095", "IDS-STAGE095-REVIEW", "IDS-V0_1-STAGE095-REVIEW"),
                ("IDS-STAGE096", "IDS-STAGE096-P1", "IDS-V0_1-STAGE096-P1"),
                ("IDS-STAGE096", "IDS-STAGE096-P2", "IDS-V0_1-STAGE096-P2"),
                ("IDS-STAGE096", "IDS-STAGE096-P3", "IDS-V0_1-STAGE096-P3"),
                ("IDS-STAGE096", "IDS-STAGE096-P4", "IDS-V0_1-STAGE096-P4"),
            ),
        )
        self.assertIn(
            status["next_gate"],
            (
                "IDS-STAGE094-P1-GATE",
                "IDS-STAGE094-P2-GATE",
                "IDS-STAGE094-P3-GATE",
                "IDS-STAGE094-P4-GATE",
                "IDS-STAGE094-REVIEW-GATE",
                "IDS-STAGE095-P1-GATE",
                "IDS-STAGE095-P2-GATE",
                "IDS-STAGE095-P3-GATE",
                "IDS-STAGE095-P4-GATE",
                "IDS-STAGE095-REVIEW-GATE",
                "IDS-STAGE096-P1-GATE",
                "IDS-STAGE096-P2-GATE",
                "IDS-STAGE096-P3-GATE",
                "IDS-STAGE096-P4-GATE",
                "IDS-STAGE096-REVIEW-GATE",
            ),
        )
        self.assertEqual(status["task"], plan["task"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-093"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P4-01"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P4-02"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P4-03"])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE093-P4-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE093-P4-20260824-001", event_ids)
        self.assertEqual("IDS-STAGE093-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_EVIDENCE_GRADE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual(517, receipt["controlled_static_shape"]["delivery_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage093_phase4_state:", roadmap_text)
        self.assertIn("stage093_review_state:", roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE093-REVIEW"', roadmap_text)
        self.assertIn('next_gate_id: "IDS-STAGE094-P1-GATE"', roadmap_text)


if __name__ == "__main__":
    unittest.main()
