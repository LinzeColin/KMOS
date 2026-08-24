import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE091_PHASE4_EVIDENCE_GAP_HANDLING_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage091_evidence_gap_handling_delivery.py"
P3_SCOPE = BASE / "STAGE091_PHASE3_EVIDENCE_GAP_HANDLING_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage091_evidence_gap_handling_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE / "index_version_schema" / "stage091_evidence_gap_handling_controlled_scenarios.py"
)
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage091_evidence_gap_handling_control_slice_contract.json"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage091_evidence_gap_handling_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE090_STAGE_REVIEW.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-091_证据缺口处理.md"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage091EvidenceGapHandlingPhase4DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage091_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage091_phase3_scenarios", P3_MODULE)
        cls.report = cls.module.build_evidence_gap_handling_phase4_delivery_report()

    def _phase3_report(self):
        return self.phase3.build_evidence_gap_handling_phase3_report()

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
        self.assertEqual("IDS-STAGE091-P4", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE091-P4", self.contract["task_id"])
        self.assertEqual("IDS-STAGE091-P4-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE091-REVIEW-GATE", self.contract["next_gate"])

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
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(468, replay["phase2_control_field_check_count"])
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
            all(value == 0 for key, value in runtime.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for key, value in runtime.items() if not key.startswith("actual_"))
        )
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage090_review_evidence_declared",
            "stage091_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage091_review_started",
            "stage092_started",
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
        self.assertEqual(468, report["phase2_control_field_check_count"])
        self.assertEqual(7, report["phase3_scenario_count"])
        self.assertEqual(32, report["phase3_scenario_field_count"])
        self.assertEqual(224, report["phase3_scenario_field_check_count"])
        self.assertEqual(517, report["delivery_field_check_count"])
        self.assertTrue(all(value is False for value in report["runtime_boundary"].values()))

    def test_all_delivery_groups_keep_exact_shape_and_control_references(self):
        groups = (
            (
                "evidence_ledger_sample_control_records",
                7,
                self.module.EVIDENCE_LEDGER_SAMPLE_FIELDS,
            ),
            (
                "evidence_grade_report_control_records",
                7,
                self.module.EVIDENCE_GRADE_REPORT_FIELDS,
            ),
            (
                "revocation_impact_control_records",
                7,
                self.module.REVOCATION_IMPACT_FIELDS,
            ),
            (
                "regression_test_control_records",
                7,
                self.module.REGRESSION_TEST_RECORD_FIELDS,
            ),
            (
                "non_conclusion_evidence_type_control_records",
                7,
                self.module.NON_CONCLUSION_EVIDENCE_TYPE_FIELDS,
            ),
            (
                "degradation_instruction_control_records",
                4,
                self.module.DEGRADATION_INSTRUCTION_FIELDS,
            ),
            (
                "revocation_recovery_instruction_control_records",
                2,
                self.module.REVOCATION_RECOVERY_INSTRUCTION_FIELDS,
            ),
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
                            == "no_internal_evidence_gap_control"
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
        }["revoked_evidence_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        for record in self.report["non_conclusion_evidence_type_control_records"]:
            self.assertEqual("CONTROL_NOT_A_CONCLUSION_BASIS", record["non_conclusion_state"])
            self.assertFalse(record["automatic_conclusion_allowed"])

    def test_degradation_and_revocation_recovery_instructions_remain_manual(self):
        degradation = self.report["degradation_instruction_control_records"]
        targets = {item["degradation_target_state"] for item in degradation}
        self.assertEqual(
            {
                "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
                "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
                "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
                "CONTROL_REVOKED_EVIDENCE_DEGRADED_NOT_ACCEPTED",
            },
            targets,
        )
        for record in degradation:
            self.assertFalse(record["actual_evidence_degradation_performed"])
            self.assertFalse(record["automatic_degradation_allowed"])
            self.assertTrue(record["human_handling_required"])
        for record in self.report["revocation_recovery_instruction_control_records"]:
            self.assertFalse(record["actual_revocation_execution_performed"])
            self.assertFalse(record["actual_recovery_execution_performed"])
            self.assertTrue(record["human_handling_required"])
            self.assertEqual(
                "CONTROL_FUTURE_AUTHORIZATION_AND_WHITEBOX_APPROVAL_REQUIRED",
                record["entry_precondition"],
            )

    def test_invalid_predecessor_fails_closed(self):
        result = self.module.build_evidence_gap_handling_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(result["valid"])
        self.assertEqual(self.module.FAIL_RESULT, result["result"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", result["failure_state"])
        self.assertEqual([], result["evidence_ledger_sample_control_records"])

    def test_predecessor_runtime_signal_fails_closed(self):
        bad = self._phase3_report()
        bad["runtime_boundary"]["model_call_performed"] = True
        result = self.module.build_evidence_gap_handling_phase4_delivery_report(
            lambda: bad
        )
        self.assertFalse(result["valid"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", result["failure_state"])

    def test_nonopaque_predecessor_reference_fails_closed(self):
        bad = self._phase3_report()
        bad["scenario_results"][1]["document_id_ref"] = "document:external:fixture"
        result = self.module.build_evidence_gap_handling_phase4_delivery_report(
            lambda: bad
        )
        self.assertFalse(result["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", result["failure_state"])

    def test_semantic_drift_for_gap_revocation_and_masquerade_fails_closed(self):
        cases = (
            (
                "gap",
                0,
                "evidence_id_ref",
                "evidence:control:stage091-p2:unexpected",
                "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING",
            ),
            (
                "revocation",
                4,
                "report_status_impact_state",
                "CONTROL_REPORT_STATUS_IMPACT_NOT_APPLIED",
                "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
            ),
            (
                "masquerade",
                6,
                "conclusion_acceptance_state",
                "CONTROL_ACCEPTED_AS_HIGH_TRUST",
                "LOW_GRADE_MASQUERADE_REJECTION_MISSING",
            ),
        )
        for name, index, field, value, expected_failure in cases:
            with self.subTest(name=name):
                bad = copy.deepcopy(self._phase3_report())
                bad["scenario_results"][index][field] = value
                result = self.module.build_evidence_gap_handling_phase4_delivery_report(
                    lambda: bad
                )
                self.assertFalse(result["valid"])
                self.assertEqual(expected_failure, result["failure_state"])

    def test_chinese_feedback_and_stage_boundary_remain_control_only(self):
        self.assertEqual(4, len(self.report["chinese_feedback"]))
        self.assertTrue(
            any("业务线白箱" in item for item in self.report["chinese_feedback"])
        )
        for field in (
            "automatic_conclusion_allowed",
            "automatic_degradation_allowed",
            "automatic_revocation_allowed",
            "automatic_recovery_allowed",
            "automatic_report_status_update_allowed",
            "github_upload_allowed",
            "push_allowed",
            "whole_stage_review_performed",
            "stage091_review_started",
            "stage092_started",
        ):
            with self.subTest(field=field):
                self.assertFalse(self.report[field])
        self.assertTrue(self.report["source_document_remains_authoritative"])
        self.assertTrue(self.report["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(self.report["second_authoritative_source_created"])
