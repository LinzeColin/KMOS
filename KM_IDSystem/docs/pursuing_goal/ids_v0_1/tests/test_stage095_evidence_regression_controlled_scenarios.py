import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE095_PHASE3_EVIDENCE_REGRESSION_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_controlled_scenarios.py"
)
P2_SCOPE = BASE / "STAGE095_PHASE2_EVIDENCE_REGRESSION_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage095_evidence_regression_control_slice_contract.json"
)
P2_MODULE = BASE / "index_version_schema" / "stage095_evidence_regression_control_slice.py"
P1_SCOPE = BASE / "STAGE095_PHASE1_EVIDENCE_REGRESSION_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage095_evidence_regression_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE094_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_stage_review_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-095_证据回归测试.md"
)
P2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage095-p2-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage095-p3-local.json"
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


class Stage095EvidenceRegressionPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage095_phase3_scenarios", MODULE)
        cls.phase2 = load_module("stage095_phase2_slice", P2_MODULE)
        cls.report = cls.module.build_evidence_regression_phase3_report()

    def _phase2_report(self):
        return self.phase2.execute_evidence_regression_control_slice(
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
            P1_SCOPE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual("ids.stage095.evidence_regression.phase3.v1", self.contract["schema_version"])
        self.assertEqual("STAGE-095", self.contract["stage"])
        self.assertEqual("IDS-STAGE095-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE095-P3", self.contract["task_id"])
        self.assertEqual("IDS-STAGE095-P4-GATE", self.contract["next_gate"])

    def test_single_authority_replay_shape_and_phase_boundary_are_explicit(self):
        source = self.contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE095_TASKPACK_AND_STAGE095_PHASE1_PHASE2_STAGE094_REVIEWED_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        allowed = {
            "authority",
            "frozen_taskpack_ref",
            "stage094_review_ref",
            "stage094_review_contract_ref",
            "stage094_review_receipt_ref",
            "stage095_phase1_scope_ref",
            "stage095_phase1_contract_ref",
            "stage095_phase1_receipt_ref",
            "stage095_phase2_scope_ref",
            "stage095_phase2_contract_ref",
            "stage095_phase2_receipt_ref",
        }
        for field, value in source.items():
            if field not in allowed:
                with self.subTest(field=field):
                    self.assertFalse(value)
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(self.module.CONTROL_PREFIX, replay["control_prefix"])
        self.assertEqual(
            self.module.P2_CONTROL_SCENARIOS,
            tuple(replay["required_control_scenarios"]),
        )
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(21, replay["required_input_field_count"])
        self.assertEqual(6, replay["required_projection_group_count"])
        self.assertEqual(58, replay["expected_projection_fields_per_request"])
        self.assertEqual(348, replay["expected_phase2_field_check_count"])
        boundary = self.contract["stage_boundary"]
        for field in (
            "stage094_review_evidence_declared",
            "stage095_started",
            "stage095_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_started",
            "stage096_started",
            "ovh_started",
            "production_started",
            "phase3_upload_or_push_started",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase2_replay_and_scenario_shapes_are_exact(self):
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
        self.assertEqual(6, report["phase2_projection_group_count"])
        self.assertEqual(348, report["phase2_field_check_count"])
        self.assertEqual(7, report["scenario_count"])
        self.assertEqual(32, report["scenario_field_count"])
        self.assertEqual(224, report["scenario_field_check_count"])
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertFalse(scenario["business_line_whitebox_human_approval_recorded"])
                self.assertFalse(scenario["actual_report_status_updated"])
                self.assertTrue(scenario["human_handling_required"])

    def test_exception_semantics_and_taskpack_coverage_are_exact(self):
        scenarios = {item["scenario_id"]: item for item in self.report["scenario_results"]}
        no_internal = scenarios["no_internal_evidence_regression_control"]
        self.assertIsNone(no_internal["evidence_id_ref"])
        self.assertTrue(no_internal["evidence_gap_ref"].startswith(self.module.CONTROL_PREFIX))
        self.assertEqual(
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW",
            no_internal["conclusion_acceptance_state"],
        )
        self.assertEqual(
            "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
            scenarios["low_ocr_evidence_regression_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        self.assertEqual(
            "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
            scenarios["old_version_evidence_regression_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        revoked = scenarios["revoked_evidence_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        self.assertEqual(
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED",
            scenarios["malicious_evidence_regression_quarantine_control"][
                "evidence_disposition_state"
            ],
        )
        masquerade = scenarios["low_grade_high_trust_masquerade_control"]
        self.assertEqual("D", masquerade["evidence_grade_label"])
        self.assertEqual(
            "CONTROL_REJECT_LOW_GRADE_AS_HIGH_TRUST_NOT_ACCEPTED",
            masquerade["conclusion_acceptance_state"],
        )
        self.assertFalse(masquerade["high_trust_conclusion_allowed"])
        taskpack = TASKPACK.read_text(encoding="utf-8")
        for phrase in (
            "无内部证据",
            "低 OCR",
            "旧版本",
            "冲突资料",
            "撤回资料",
            "恶意资料",
            "高可信结论不能使用低等级证据伪装",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, taskpack)

    def test_contract_failure_and_protected_boundaries_are_explicit(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "PHASE2_CONTROL_SHAPE_MISMATCH",
            "PHASE2_RUNTIME_SIGNAL_DETECTED",
            "CONTROL_REFERENCE_NOT_OPAQUE",
            "NO_INTERNAL_EVIDENCE_GAP_ROUTE_MISSING",
            "LOW_OCR_EVIDENCE_NOT_DEGRADED",
            "OLD_VERSION_EVIDENCE_NOT_DEGRADED",
            "CONFLICT_EVIDENCE_NOT_DEGRADED",
            "REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_MISSING",
            "MALICIOUS_EVIDENCE_NOT_QUARANTINED",
            "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_TRUST",
            "CRITICAL_CONCLUSION_BINDING_MISSING",
            "HUMAN_WHITEBOX_REVIEW_REQUIRED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        self.assertEqual(4, len(self.contract["operator_feedback"]))
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE2_EVIDENCE_REGRESSION_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["preserve_stage095_phase1_and_phase2"])
        self.assertTrue(rollback["preserve_stage094_reviewed_artifacts"])

    def test_invalid_phase2_output_returns_controlled_failure(self):
        failed = self.module.build_evidence_regression_phase3_report(lambda _: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", failed["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, failed["next_gate"])
        self.assertEqual([], failed["scenario_results"])

    def test_phase2_runtime_signal_returns_controlled_failure(self):
        def runtime_signal(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_evidence_regression_phase3_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase2_side_effect_free"])
        self.assertEqual("PHASE2_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

    def test_nonopaque_reference_and_semantic_drift_return_specific_failures(self):
        def nonopaque_reference(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["evidence_regression_schema_binding_control_projections"][0][
                "evidence_gap_ref"
            ] = "unscoped-reference"
            return altered

        failed = self.module.build_evidence_regression_phase3_report(nonopaque_reference)
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

        def low_ocr_drift(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["risk_and_evidence_grade_control_control_projections"][1][
                "degradation_state"
            ] = "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW"
            return altered

        failed = self.module.build_evidence_regression_phase3_report(low_ocr_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual("LOW_OCR_EVIDENCE_NOT_DEGRADED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

        def masquerade_drift(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["critical_conclusion_and_report_impact_control_projections"][1][
                "evidence_grade_ref"
            ] = ":control:stage095-p2:evidence-grade-A:reference-only"
            return altered

        failed = self.module.build_evidence_regression_phase3_report(masquerade_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual(
            "LOW_GRADE_EVIDENCE_MASQUERADING_AS_HIGH_TRUST",
            failed["failure_state"],
        )
        self.assertEqual([], failed["scenario_results"])

    def test_predecessor_p2_record_remains_immutable_before_or_after_p3(self):
        for path in (P2_RECEIPT, STATUS, PLAN, ACCEPTANCE, EVENTS, ROADMAP):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
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
        stage096_phase1_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P1",
            "IDS-V0_1-STAGE096-P1",
            "IDS-STAGE096-P2-GATE",
        )
        stage096_phase2_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P2",
            "IDS-V0_1-STAGE096-P2",
            "IDS-STAGE096-P3-GATE",
        )
        stage096_phase3_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P3",
            "IDS-V0_1-STAGE096-P3",
            "IDS-STAGE096-P4-GATE",
        )
        stage096_phase4_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-P4",
            "IDS-V0_1-STAGE096-P4",
            "IDS-STAGE096-REVIEW-GATE",
        )
        stage096_review_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-REVIEW",
            "IDS-V0_1-STAGE096-REVIEW",
            "IDS-STAGE097-P1-GATE",
        )
        stage097_phase1_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P1",
            "IDS-V0_1-STAGE097-P1",
            "IDS-STAGE097-P2-GATE",
        )
        stage097_phase2_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P2",
            "IDS-V0_1-STAGE097-P2",
            "IDS-STAGE097-P3-GATE",
        )
        stage097_phase3_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P3",
            "IDS-V0_1-STAGE097-P3",
            "IDS-STAGE097-P4-GATE",
        )
        stage097_phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        stage097_review_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-REVIEW",
            "IDS-V0_1-STAGE097-REVIEW",
            "IDS-STAGE098-P1-GATE",
        )
        stage098_phase1_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P1",
            "IDS-V0_1-STAGE098-P1",
            "IDS-STAGE098-P2-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        if current == stage095_phase3_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P3 受控场景已完成", acceptance_by_id["ACC-STAGE-095"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE095-P3-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE095-P3-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE095-P3-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE095-P3-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE095-P3-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE095-P4-GATE", receipt["next_gate"])
            self.assertEqual(
                "PASS_EVIDENCE_REGRESSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                receipt["result"],
            )
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertIn("stage095_phase3_state:", ROADMAP.read_text(encoding="utf-8"))
        self.assertIn(
            current,
            (
                stage095_phase2_current,
                stage095_phase3_current,
                    stage095_phase4_current,
                    (
                        "IDS-STAGE095",
                        "IDS-STAGE095-REVIEW",
                        "IDS-V0_1-STAGE095-REVIEW",
                        "IDS-STAGE096-P1-GATE",
                    ),
                    stage096_phase1_current,
                    stage096_phase2_current,
                    stage096_phase3_current,
                    stage096_phase4_current,
                    stage096_review_current,
                    stage097_phase1_current,
                    stage097_phase2_current,
                    stage097_phase3_current,
                    stage097_phase4_current,
                    stage097_review_current,
                    stage098_phase1_current,
            ),
        )


if __name__ == "__main__":
    unittest.main()
