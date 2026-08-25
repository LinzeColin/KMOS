import copy
import importlib.util
import json
from pathlib import Path
import unittest
from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import assert_legacy_or_current_projection


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE093_PHASE3_EVIDENCE_GRADE_CONTROLLED_SCENARIOS.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_controlled_scenarios_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_controlled_scenarios.py"
)
P2_SCOPE = BASE / "STAGE093_PHASE2_EVIDENCE_GRADE_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_control_slice_contract.json"
)
P2_MODULE = BASE / "index_version_schema" / "stage093_evidence_grade_control_slice.py"
P1_SCOPE = BASE / "STAGE093_PHASE1_EVIDENCE_GRADE_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage093_evidence_grade_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE092_STAGE_REVIEW.md"
PREDECESSOR_REVIEW_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage092_evidence_risk_scoring_stage_review_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-093_证据可信等级A_B_C_D_E.md"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage093-p3-local.json"
P2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage093-p2-local.json"
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


class Stage093EvidenceGradePhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage093_phase3_scenarios", MODULE)
        cls.phase2 = load_module("stage093_phase2_slice", P2_MODULE)
        cls.report = cls.module.build_evidence_grade_phase3_report()

    def _phase2_report(self):
        return self.phase2.execute_evidence_grade_control_slice(
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
            PREDECESSOR_REVIEW_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual("IDS-STAGE093-P3", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE093-P3", self.contract["task_id"])
        self.assertEqual("IDS-STAGE093-P4-GATE", self.contract["next_gate"])

    def test_contract_binds_single_authority_phase2_and_stage_boundary(self):
        authority = self.contract["source_authority"]
        for field in (
            "second_authoritative_source_created",
            "control_scenario_can_replace_source_document",
            "control_result_can_become_business_fact_authority",
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
                self.assertFalse(authority[field])
        replay = self.contract["phase2_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(27, replay["required_input_field_count"])
        self.assertEqual(11, replay["required_projection_group_count"])
        self.assertEqual(100, replay["expected_projection_fields_per_request"])
        self.assertEqual(600, replay["expected_phase2_field_check_count"])
        self.assertTrue(replay["grade_assignment_owner_approved_rule_required"])
        scenario = self.contract["scenario_result_contract"]
        self.assertEqual(7, scenario["scenario_count"])
        self.assertEqual(tuple(scenario["scenario_fields"]), self.module.SCENARIO_FIELDS)
        self.assertEqual(32, scenario["scenario_field_count"])
        self.assertEqual(224, scenario["expected_scenario_field_check_count"])
        self.assertFalse(scenario["actual_report_status_updated"])
        self.assertFalse(scenario["actual_evidence_grade_assigned"])
        self.assertFalse(scenario["actual_evidence_grade_changed"])
        self.assertFalse(scenario["actual_risk_score_calculated"])
        self.assertFalse(scenario["low_grade_high_trust_conclusion_allowed"])
        self.assertTrue(
            all(value is False for value in self.contract["runtime_boundary"].values())
        )
        boundary = self.contract["stage_boundary"]
        for field in (
            "stage092_review_evidence_declared",
            "stage093_started",
            "stage093_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase4_started",
            "whole_stage_review_started",
            "stage094_started",
            "ovh_started",
            "production_started",
            "phase3_upload_or_push_started",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_report_replays_exact_phase2_shape_without_runtime(self):
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
        self.assertEqual(11, report["phase2_projection_group_count"])
        self.assertEqual(600, report["phase2_field_check_count"])
        self.assertEqual(7, report["scenario_count"])
        self.assertEqual(32, report["scenario_field_count"])
        self.assertEqual(224, report["scenario_field_check_count"])
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )

    def test_each_exception_scenario_is_control_only_and_whitebox_gated(self):
        scenarios = {
            item["scenario_id"]: item for item in self.report["scenario_results"]
        }
        expected = {
            "no_internal_evidence_grade_control",
            "low_ocr_evidence_grade_degradation_control",
            "old_version_evidence_grade_degradation_control",
            "conflict_evidence_grade_degradation_control",
            "revoked_evidence_grade_report_impact_control",
            "malicious_evidence_grade_quarantine_control",
            "low_grade_high_trust_masquerade_control",
        }
        self.assertEqual(expected, set(scenarios))
        for scenario in scenarios.values():
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertTrue(scenario["human_handling_required"])
                self.assertFalse(
                    scenario["business_line_whitebox_human_approval_recorded"]
                )
                self.assertFalse(scenario["actual_report_status_updated"])
                self.assertFalse(scenario["high_trust_conclusion_allowed"])
                self.assertFalse(scenario["silent_drop"])
                for field, value in scenario.items():
                    if field.endswith("_ref") and value is not None:
                        self.assertIn(self.module.CONTROL_PREFIX, value)
        self.assertIsNone(scenarios["no_internal_evidence_grade_control"]["evidence_id_ref"])
        self.assertTrue(
            all(
                scenario["evidence_id_ref"]
                for scenario_id, scenario in scenarios.items()
                if scenario_id != "no_internal_evidence_grade_control"
            )
        )

    def test_taskpack_exception_dispositions_report_impact_and_masquerade_hold(self):
        scenarios = {
            item["scenario_id"]: item for item in self.report["scenario_results"]
        }
        self.assertEqual(
            "CONTROL_NOT_ACCEPTED_PENDING_EVIDENCE_GAP_AND_WHITEBOX_REVIEW",
            scenarios["no_internal_evidence_grade_control"][
                "conclusion_acceptance_state"
            ],
        )
        self.assertEqual(
            "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
            scenarios["low_ocr_evidence_grade_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        self.assertEqual(
            "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
            scenarios["old_version_evidence_grade_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        self.assertEqual(
            "CONTROL_CONFLICT_DEGRADED_NOT_ACCEPTED",
            scenarios["conflict_evidence_grade_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        revoked = scenarios["revoked_evidence_grade_report_impact_control"]
        self.assertEqual(
            "CONTROL_REVOKED_EVIDENCE_REPORT_STATUS_IMPACT_DECLARED_NOT_APPLIED",
            revoked["report_status_impact_state"],
        )
        self.assertFalse(revoked["actual_report_status_updated"])
        self.assertEqual(
            "CONTROL_MALICIOUS_EVIDENCE_QUARANTINED_NOT_ACCEPTED",
            scenarios["malicious_evidence_grade_quarantine_control"][
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
            "EVIDENCE_GRADE_ASSIGNMENT_RULE_UNAUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE2_EVIDENCE_GRADE_CONTROL_SLICE_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["preserve_stage093_phase1_and_phase2"])
        self.assertTrue(rollback["preserve_stage092_reviewed_artifacts"])

    def test_invalid_phase2_output_returns_controlled_failure(self):
        failed = self.module.build_evidence_grade_phase3_report(lambda _: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE2_CONTROL_SHAPE_MISMATCH", failed["failure_state"])
        self.assertEqual(self.module.CURRENT_GATE, failed["next_gate"])
        self.assertEqual([], failed["scenario_results"])

    def test_phase2_runtime_signal_returns_controlled_failure(self):
        def runtime_signal(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_evidence_grade_phase3_report(runtime_signal)
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase2_side_effect_free"])
        self.assertEqual("PHASE2_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

    def test_nonopaque_reference_and_semantic_drift_return_specific_failures(self):
        def nonopaque_reference(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["evidence_grade_schema_binding_control_projections"][0][
                "evidence_gap_ref"
            ] = "unscoped-reference"
            return altered

        failed = self.module.build_evidence_grade_phase3_report(nonopaque_reference)
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

        def low_ocr_drift(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["degradation_control_projections"][1]["degradation_state"] = (
                "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW"
            )
            return altered

        failed = self.module.build_evidence_grade_phase3_report(low_ocr_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual("LOW_OCR_EVIDENCE_NOT_DEGRADED", failed["failure_state"])
        self.assertEqual([], failed["scenario_results"])

        def assignment_rule_drift(_control_input):
            altered = copy.deepcopy(self._phase2_report())
            altered["evidence_grade_assignment_control_projections"][1][
                "grade_assignment_state"
            ] = "CONTROL_GRADE_ASSIGNMENT_UNAUTHORIZED"
            return altered

        failed = self.module.build_evidence_grade_phase3_report(assignment_rule_drift)
        self.assertFalse(failed["valid"])
        self.assertEqual(
            "EVIDENCE_GRADE_ASSIGNMENT_RULE_UNAUTHORIZED", failed["failure_state"]
        )
        self.assertEqual([], failed["scenario_results"])

    def test_predecessor_p3_record_remains_immutable_after_review_completion(self):
        for path in (RECEIPT, P2_RECEIPT, STATUS, PLAN, ACCEPTANCE, EVENTS, ROADMAP):
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
        legacy_projections = (
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
                ("IDS-STAGE096", "IDS-STAGE096-REVIEW", "IDS-V0_1-STAGE096-REVIEW"),
                ("IDS-STAGE097", "IDS-STAGE097-P1", "IDS-V0_1-STAGE097-P1"),
                ("IDS-STAGE097", "IDS-STAGE097-P2", "IDS-V0_1-STAGE097-P2"),
                ("IDS-STAGE097", "IDS-STAGE097-P3", "IDS-V0_1-STAGE097-P3"),
                ("IDS-STAGE097", "IDS-STAGE097-P4", "IDS-V0_1-STAGE097-P4"),
                ("IDS-STAGE097", "IDS-STAGE097-REVIEW", "IDS-V0_1-STAGE097-REVIEW"),
                ("IDS-STAGE098", "IDS-STAGE098-P1", "IDS-V0_1-STAGE098-P1"),
                ("IDS-STAGE098", "IDS-STAGE098-P2", "IDS-V0_1-STAGE098-P2"),
                ("IDS-STAGE098", "IDS-STAGE098-P3", "IDS-V0_1-STAGE098-P3"),
                ("IDS-STAGE098", "IDS-STAGE098-P4", "IDS-V0_1-STAGE098-P4"),
                ("IDS-STAGE098", "IDS-STAGE098-REVIEW", "IDS-V0_1-STAGE098-REVIEW"),
                ("IDS-STAGE099", "IDS-STAGE099-P1", "IDS-V0_1-STAGE099-P1"),
                ("IDS-STAGE099", "IDS-STAGE099-P2", "IDS-V0_1-STAGE099-P2"),
                ("IDS-STAGE099", "IDS-STAGE099-P3", "IDS-V0_1-STAGE099-P3"),
                ("IDS-STAGE099", "IDS-STAGE099-P4", "IDS-V0_1-STAGE099-P4"),
                ("IDS-STAGE099", "IDS-STAGE099-REVIEW", "IDS-V0_1-STAGE099-REVIEW"),
            )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            (status["stage"], status["phase"], status["task"]),
            legacy_projections,
            status,
            plan,
            ROADMAP,
        )
        self.assertTrue(
            is_current_projection or status["next_gate"] in
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
                "IDS-STAGE097-P1-GATE",
                "IDS-STAGE097-P2-GATE",
                "IDS-STAGE097-P3-GATE",
                "IDS-STAGE097-P4-GATE",
                "IDS-STAGE097-REVIEW-GATE",
                "IDS-STAGE098-P1-GATE",
                "IDS-STAGE098-P2-GATE",
                "IDS-STAGE098-P3-GATE",
                "IDS-STAGE098-P4-GATE",
                "IDS-STAGE098-REVIEW-GATE",
                "IDS-STAGE099-P1-GATE",
                "IDS-STAGE099-P2-GATE",
                "IDS-STAGE099-P3-GATE",
                "IDS-STAGE099-P4-GATE",
                "IDS-STAGE099-REVIEW-GATE",
                "IDS-STAGE100-P1-GATE",
            ),
        )
        self.assertEqual(status["task"], plan["task"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-093"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P3-01"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P3-02"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE093-P3-03"])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE093-P3-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE093-P3-20260824-001", event_ids)
        self.assertEqual("IDS-STAGE093-P4-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_EVIDENCE_GRADE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual(7, receipt["controlled_static_shape"]["scenario_count"])
        self.assertTrue(
            all(value == 0 for value in receipt["runtime_counts"].values())
        )
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage093_phase3_state:", roadmap_text)
        self.assertIn("stage093_phase4_state:", roadmap_text)
        self.assertIn("stage093_review_state:", roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE093-REVIEW"', roadmap_text)
        self.assertIn('next_gate_id: "IDS-STAGE094-P1-GATE"', roadmap_text)


if __name__ == "__main__":
    unittest.main()
