import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE089_PHASE4_EVIDENCE_LEDGER_DELIVERY_EVIDENCE.md"
CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_delivery_contract.json"
MODULE = BASE / "index_version_schema" / "stage089_evidence_ledger_delivery.py"
P3_SCOPE = BASE / "STAGE089_PHASE3_EVIDENCE_LEDGER_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_scenarios_contract.json"
P3_MODULE = BASE / "index_version_schema" / "stage089_evidence_ledger_controlled_scenarios.py"
P2_CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_control_slice_contract.json"
P1_CONTRACT = BASE / "index_version_schema" / "stage089_evidence_ledger_schema_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE088_STAGE_REVIEW.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-089_证据账本Schema.md"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage089EvidenceLedgerPhase4DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage089_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage089_phase3_scenarios", P3_MODULE)
        cls.report = cls.module.build_evidence_ledger_phase4_delivery_report()

    def _phase3_report(self):
        return self.phase3.build_evidence_ledger_phase3_report()

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
            self.assertTrue(path.is_file(), path)
        self.assertEqual("IDS-STAGE089-P4", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE089-P4", self.contract["task_id"])
        self.assertEqual("IDS-STAGE089-P4-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE089-REVIEW-GATE", self.contract["next_gate"])

    def test_contract_keeps_single_authority_runtime_and_review_closed(self):
        authority = self.contract["source_authority"]
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])
        self.assertFalse(authority["evidence_ledger_access_performed"])
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(444, replay["phase2_control_field_check_count"])
        self.assertEqual(7, replay["scenario_count"])
        self.assertEqual(32, replay["scenario_field_count"])
        self.assertEqual(224, replay["scenario_field_check_count"])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertEqual(517, delivery["delivery_field_check_count"])
        self.assertEqual(7, delivery["evidence_ledger_sample_control_record_count"])
        self.assertEqual(7, delivery["evidence_grade_report_control_record_count"])
        self.assertEqual(7, delivery["revocation_impact_control_record_count"])
        self.assertEqual(7, delivery["regression_test_control_record_count"])
        self.assertEqual(7, delivery["non_conclusion_evidence_type_control_record_count"])
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
        self.assertTrue(boundary["phase4_started"])
        self.assertFalse(boundary["whole_stage_review_performed"])
        self.assertFalse(boundary["stage089_review_started"])
        self.assertFalse(boundary["stage090_started"])

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
        self.assertEqual(444, report["phase2_control_field_check_count"])
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
                        self.assertTrue(
                            self.module.CONTROL_PREFIX in value
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
            "证据降级、撤回和恢复说明",
        ):
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
        self.assertFalse(revoked["actual_revocation_impact_list_written"])
        non_conclusion = {
            item["scenario_id"]: item
            for item in self.report["non_conclusion_evidence_type_control_records"]
        }
        self.assertEqual(
            "CONTROL_NOT_A_CONCLUSION_BASIS",
            non_conclusion["low_grade_high_trust_masquerade_control"][
                "non_conclusion_state"
            ],
        )
        self.assertFalse(
            non_conclusion["low_grade_high_trust_masquerade_control"][
                "automatic_conclusion_allowed"
            ]
        )
        self.assertTrue(
            all(item["automatic_conclusion_allowed"] is False for item in non_conclusion.values())
        )

    def test_degradation_and_revocation_recovery_instructions_are_future_only(self):
        degradation = self.report["degradation_instruction_control_records"]
        self.assertEqual(4, len(degradation))
        self.assertTrue(
            all(
                item["instruction_state"]
                == "CONTROL_DEGRADATION_INSTRUCTION_DECLARED_NOT_EXECUTED"
                and item["actual_evidence_degradation_performed"] is False
                and item["automatic_degradation_allowed"] is False
                and item["human_handling_required"] is True
                for item in degradation
            )
        )
        recovery = self.report["revocation_recovery_instruction_control_records"]
        self.assertEqual(2, len(recovery))
        self.assertTrue(
            all(
                item["entry_precondition"]
                == "CONTROL_FUTURE_AUTHORIZATION_AND_WHITEBOX_APPROVAL_REQUIRED"
                and item["actual_revocation_execution_performed"] is False
                and item["actual_recovery_execution_performed"] is False
                and item["human_handling_required"] is True
                for item in recovery
            )
        )

    def test_invalid_phase3_output_fails_closed_without_delivery_records(self):
        failed = self.module.build_evidence_ledger_phase4_delivery_report(lambda: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, failed["next_gate"])
        self.assertEqual([], failed["evidence_ledger_sample_control_records"])
        self.assertEqual([], failed["revocation_impact_control_records"])

    def test_phase3_runtime_signal_fails_closed_without_delivery_records(self):
        def runtime_signal():
            altered = copy.deepcopy(self._phase3_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_evidence_ledger_phase4_delivery_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["evidence_grade_report_control_records"])

    def test_nonopaque_phase3_reference_fails_closed_without_delivery_records(self):
        def nonopaque_reference():
            altered = copy.deepcopy(self._phase3_report())
            altered["scenario_results"][0]["evidence_id_ref"] = "non-control-reference"
            return altered

        failed = self.module.build_evidence_ledger_phase4_delivery_report(
            nonopaque_reference
        )
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])
        self.assertEqual([], failed["regression_test_control_records"])

    def test_revocation_report_impact_drift_fails_closed_without_delivery_records(self):
        def revoked_drift():
            altered = copy.deepcopy(self._phase3_report())
            for scenario in altered["scenario_results"]:
                if scenario["scenario_id"] == "revoked_evidence_report_impact_control":
                    scenario["report_status_impact_state"] = "CONTROL_REPORT_STATUS_APPLIED"
            return altered

        failed = self.module.build_evidence_ledger_phase4_delivery_report(revoked_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual(
            "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
            failed["failure_state"],
        )
        self.assertEqual([], failed["revocation_recovery_instruction_control_records"])

    def test_review_and_external_boundaries_remain_closed(self):
        report = self.report
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage089_review_started"])
        self.assertFalse(report["stage090_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        self.assertTrue(
            all(
                "未" in feedback or "不可" in feedback
                for feedback in report["chinese_feedback"]
            )
        )


if __name__ == "__main__":
    unittest.main()
