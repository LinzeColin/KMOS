"""Stage095 P4 证据回归交付控制的聚焦测试。"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-095_证据回归测试.md"
)
CONTRACT = BASE / "index_version_schema" / "stage095_evidence_regression_delivery_contract.json"
MODULE = BASE / "index_version_schema" / "stage095_evidence_regression_delivery.py"
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_controlled_scenarios.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage095EvidenceRegressionPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("stage095_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage095_phase3_scenarios", P3_MODULE)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_evidence_regression_phase4_delivery_report()

    def test_contract_identity_and_source_authority(self) -> None:
        self.assertEqual(
            "ids.stage095.evidence_regression.phase4.delivery.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE095-P4", self.contract["task_id"])
        source = self.contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(source["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(source["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(source["second_authoritative_source_created"])

    def test_default_report_is_valid_and_gated(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertFalse(report["second_authoritative_source_created"])

    def test_delivery_groups_have_exact_static_shapes(self) -> None:
        groups = (
            ("evidence_ledger_sample_control_records", self.module.EVIDENCE_LEDGER_SAMPLE_FIELDS, 7),
            ("evidence_grade_report_control_records", self.module.EVIDENCE_GRADE_REPORT_FIELDS, 7),
            ("revocation_impact_control_records", self.module.REVOCATION_IMPACT_FIELDS, 7),
            ("regression_test_control_records", self.module.REGRESSION_TEST_RECORD_FIELDS, 7),
            ("non_conclusion_evidence_type_control_records", self.module.NON_CONCLUSION_EVIDENCE_TYPE_FIELDS, 7),
            ("degradation_instruction_control_records", self.module.DEGRADATION_INSTRUCTION_FIELDS, 4),
            ("revocation_recovery_instruction_control_records", self.module.REVOCATION_RECOVERY_INSTRUCTION_FIELDS, 2),
        )
        for name, fields, count in groups:
            records = self.report[name]
            with self.subTest(group=name):
                self.assertEqual(count, len(records))
            for record in records:
                with self.subTest(group=name, record=record):
                    self.assertEqual(set(fields), set(record))
        self.assertEqual(517, self.report["delivery_field_check_count"])

    def test_delivery_references_are_control_only(self) -> None:
        groups = (
            "evidence_ledger_sample_control_records",
            "evidence_grade_report_control_records",
            "revocation_impact_control_records",
            "regression_test_control_records",
            "non_conclusion_evidence_type_control_records",
            "degradation_instruction_control_records",
            "revocation_recovery_instruction_control_records",
        )
        for name in groups:
            for record in self.report[name]:
                for field, value in record.items():
                    if not field.endswith("_ref"):
                        continue
                    with self.subTest(group=name, field=field, value=value):
                        if value is None:
                            self.assertEqual("evidence_id_ref", field)
                            self.assertEqual(
                                "no_internal_evidence_regression_control",
                                record["scenario_id"],
                            )
                        else:
                            self.assertTrue(
                                self.module.CONTROL_PREFIX in value
                                or self.module.DELIVERY_PREFIX in value
                            )

    def test_taskpack_semantics_and_chinese_feedback_are_explicit(self) -> None:
        self.assertEqual(4, len(self.report["chinese_feedback"]))
        taskpack = TASKPACK.read_text(encoding="utf-8")
        for phrase in (
            "evidence ledger 样例",
            "证据等级报告",
            "撤回影响清单",
            "不可作为结论依据",
            "证据降级、撤回和恢复说明",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, taskpack)
        for message in self.report["chinese_feedback"]:
            self.assertIn("控制", message)

    def test_exception_dispositions_are_carried_forward(self) -> None:
        grades = {
            item["scenario_id"]: item
            for item in self.report["evidence_grade_report_control_records"]
        }
        self.assertEqual(
            "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
            grades["low_ocr_evidence_regression_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        self.assertEqual(
            "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
            grades["old_version_evidence_regression_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        impacts = {
            item["scenario_id"]: item
            for item in self.report["revocation_impact_control_records"]
        }
        revoked = impacts["revoked_evidence_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        non_conclusion = self.report["non_conclusion_evidence_type_control_records"]
        self.assertTrue(
            all(
                item["non_conclusion_state"] == "CONTROL_NOT_A_CONCLUSION_BASIS"
                and item["automatic_conclusion_allowed"] is False
                and item["human_handling_required"] is True
                for item in non_conclusion
            )
        )

    def test_degradation_recovery_and_runtime_boundaries_are_closed(self) -> None:
        self.assertEqual(4, len(self.report["degradation_instruction_control_records"]))
        self.assertEqual(
            2, len(self.report["revocation_recovery_instruction_control_records"])
        )
        for record in self.report["degradation_instruction_control_records"]:
            self.assertFalse(record["actual_evidence_degradation_performed"])
            self.assertFalse(record["automatic_degradation_allowed"])
            self.assertTrue(record["human_handling_required"])
        for record in self.report["revocation_recovery_instruction_control_records"]:
            self.assertFalse(record["actual_revocation_execution_performed"])
            self.assertFalse(record["actual_recovery_execution_performed"])
            self.assertTrue(record["human_handling_required"])
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        for key, value in self.report.items():
            if key.startswith("actual_") and key.endswith("_count"):
                with self.subTest(key=key):
                    self.assertEqual(0, value)

    def test_failure_stop_and_rollback_contracts_are_explicit(self) -> None:
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(18, failures["failure_state_count"])
        self.assertEqual(
            list(self.module.FAILURE_STATES), failures["declared_failure_states"]
        )
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value is False for value in failures.values() if isinstance(value, bool))
        )
        rollback = self.contract["rollback_contract"]
        self.assertEqual(self.module.P3_PASS_RESULT, rollback["rollback_target_result"])
        self.assertTrue(rollback["preserve_stage095_phase1_phase2_phase3"])
        self.assertTrue(rollback["preserve_stage094_reviewed_artifacts"])

    def test_invalid_predecessor_output_returns_controlled_failure(self) -> None:
        failed = self.module.build_evidence_regression_phase4_delivery_report(lambda: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, failed["next_gate"])
        self.assertEqual([], failed["evidence_ledger_sample_control_records"])

    def test_predecessor_runtime_signal_returns_controlled_failure(self) -> None:
        altered = copy.deepcopy(
            self.phase3.build_evidence_regression_phase3_report()
        )
        altered["runtime_boundary"]["model_token_consumption_performed"] = True
        failed = self.module.build_evidence_regression_phase4_delivery_report(
            lambda: altered
        )
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase3_side_effect_free"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])

    def test_nonopaque_reference_and_semantic_drift_return_specific_failures(self) -> None:
        nonopaque = copy.deepcopy(self.phase3.build_evidence_regression_phase3_report())
        nonopaque["scenario_results"][0]["evidence_gap_ref"] = "unscoped-reference"
        failed = self.module.build_evidence_regression_phase4_delivery_report(
            lambda: nonopaque
        )
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])

        semantic_drift = copy.deepcopy(
            self.phase3.build_evidence_regression_phase3_report()
        )
        semantic_drift["scenario_results"][1]["evidence_disposition_state"] = (
            "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW"
        )
        failed = self.module.build_evidence_regression_phase4_delivery_report(
            lambda: semantic_drift
        )
        self.assertFalse(failed["valid"])
        self.assertEqual(
            "EVIDENCE_DEGRADATION_DISPOSITION_MISSING", failed["failure_state"]
        )


if __name__ == "__main__":
    unittest.main()

