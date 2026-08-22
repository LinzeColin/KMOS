import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE089_PHASE3_EVIDENCE_LEDGER_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage089_evidence_ledger_scenarios_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage089_evidence_ledger_controlled_scenarios.py"
)
P2_SCOPE = BASE / "STAGE089_PHASE2_EVIDENCE_LEDGER_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage089_evidence_ledger_control_slice_contract.json"
)
P2_MODULE = (
    BASE / "index_version_schema" / "stage089_evidence_ledger_control_slice.py"
)
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


class Stage089EvidenceLedgerPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage089_phase3_scenarios", MODULE)
        cls.phase2 = load_module("stage089_phase2_slice", P2_MODULE)
        cls.report = cls.module.build_evidence_ledger_phase3_report()

    def _phase2_report(self):
        return self.phase2.execute_evidence_ledger_control_slice(
            self.phase2.build_control_input()
        )

    def test_artifacts_phase_identity_and_frozen_taskpack_exist(self):
        for path in (
            SCOPE,
            CONTRACT,
            MODULE,
            P2_SCOPE,
            P2_CONTRACT,
            P2_MODULE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            TASKPACK,
        ):
            self.assertTrue(path.is_file(), path)
        self.assertEqual("IDS-STAGE089-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE089-P3", self.contract["task_id"])
        self.assertEqual(
            "IDS-STAGE089-P4-GATE",
            self.contract["next_gate"],
        )

    def test_contract_keeps_single_authority_runtime_and_future_phases_closed(self):
        authority = self.contract["source_authority"]
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])
        self.assertFalse(authority["evidence_ledger_access_performed"])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(24, replay["required_input_field_count"])
        self.assertEqual(10, replay["required_projection_group_count"])
        self.assertEqual(444, replay["expected_phase2_field_check_count"])
        scenario = self.contract["scenario_result_contract"]
        self.assertEqual(7, scenario["scenario_count"])
        self.assertEqual(32, scenario["scenario_field_count"])
        self.assertEqual(224, scenario["expected_scenario_field_check_count"])
        self.assertFalse(scenario["actual_report_status_updated"])
        self.assertFalse(scenario["actual_evidence_grade_changed"])
        self.assertTrue(all(value is False for value in self.contract["runtime_boundary"].values()))
        boundary = self.contract["stage_boundary"]
        self.assertTrue(boundary["phase3_started"])
        self.assertFalse(boundary["phase4_started"])
        self.assertFalse(boundary["whole_stage_review_started"])
        self.assertFalse(boundary["stage090_started"])

    def test_report_replays_p2_exact_shape_without_runtime(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(10, report["phase2_projection_group_count"])
        self.assertEqual(444, report["phase2_field_check_count"])
        self.assertEqual(7, report["scenario_count"])
        self.assertEqual(32, report["scenario_field_count"])
        self.assertEqual(224, report["scenario_field_check_count"])
        self.assertTrue(all(value is False for value in report["runtime_boundary"].values()))

    def test_each_exception_scenario_is_control_only_and_whitebox_gated(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        expected = {
            "no_internal_evidence_gap_control",
            "low_ocr_evidence_degradation_control",
            "old_version_evidence_degradation_control",
            "conflict_evidence_degradation_control",
            "revoked_evidence_report_impact_control",
            "malicious_evidence_quarantine_control",
            "low_grade_high_trust_masquerade_control",
        }
        self.assertEqual(expected, set(scenarios))
        for scenario in scenarios.values():
            self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
            self.assertTrue(scenario["expectation_met"])
            self.assertTrue(scenario["human_handling_required"])
            self.assertFalse(scenario["business_line_whitebox_human_approval_recorded"])
            self.assertFalse(scenario["actual_report_status_updated"])
            self.assertFalse(scenario["actual_evidence_grade_changed"])
            self.assertFalse(scenario["silent_drop"])
            for field, value in scenario.items():
                if field.endswith("_ref"):
                    self.assertIn(self.module.CONTROL_PREFIX, value)

    def test_taskpack_exception_dispositions_report_impact_and_masquerade_rejection_hold(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        self.assertEqual(
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW",
            scenarios["no_internal_evidence_gap_control"]["conclusion_acceptance_state"],
        )
        self.assertEqual(
            "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
            scenarios["low_ocr_evidence_degradation_control"]["evidence_disposition_state"],
        )
        self.assertEqual(
            "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
            scenarios["old_version_evidence_degradation_control"]["evidence_disposition_state"],
        )
        self.assertEqual(
            "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
            scenarios["conflict_evidence_degradation_control"]["evidence_disposition_state"],
        )
        revoked = scenarios["revoked_evidence_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        self.assertEqual(
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED",
            scenarios["malicious_evidence_quarantine_control"]["evidence_disposition_state"],
        )
        masquerade = scenarios["low_grade_high_trust_masquerade_control"]
        self.assertEqual("D", masquerade["evidence_grade_label"])
        self.assertEqual(
            "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED",
            masquerade["conclusion_acceptance_state"],
        )
        taskpack = TASKPACK.read_text(encoding="utf-8")
        self.assertIn("低 OCR", taskpack)
        self.assertIn("撤回证据会影响报告状态", taskpack)
        self.assertIn("低等级证据伪装", taskpack)

    def test_invalid_phase2_output_fails_closed_without_scenarios(self):
        failed = self.module.build_evidence_ledger_phase3_report(lambda _: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", failed["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, failed["next_gate"])
        self.assertEqual([], failed["scenario_results"])

    def test_phase2_runtime_signal_fails_closed_without_scenarios(self):
        def runtime_signal(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_evidence_ledger_phase3_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase2_side_effect_free"])
        self.assertEqual("PHASE2_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

    def test_nonopaque_reference_fails_closed_without_scenarios(self):
        def nonopaque_reference(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["evidence_schema_control_projections"][0]["evidence_id_ref"] = (
                "non-control-reference"
            )
            return altered

        failed = self.module.build_evidence_ledger_phase3_report(nonopaque_reference)
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

    def test_exception_degradation_drift_fails_closed_without_scenarios(self):
        def degraded_state_drift(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["degradation_control_projections"][1]["degradation_state"] = (
                "CONTROL_NOT_DEGRADED"
            )
            return altered

        failed = self.module.build_evidence_ledger_phase3_report(degraded_state_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual("LOW_OCR_EVIDENCE_NOT_DEGRADED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])


if __name__ == "__main__":
    unittest.main()
