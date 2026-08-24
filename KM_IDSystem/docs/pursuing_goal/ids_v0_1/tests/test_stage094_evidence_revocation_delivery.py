import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE094_PHASE4_EVIDENCE_REVOCATION_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_delivery_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage094_evidence_revocation_delivery.py"
)
P3_SCOPE = BASE / "STAGE094_PHASE3_EVIDENCE_REVOCATION_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_controlled_scenarios.py"
)
P2_SCOPE = BASE / "STAGE094_PHASE2_EVIDENCE_REVOCATION_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage094_evidence_revocation_control_slice_contract.json"
)
P1_SCOPE = BASE / "STAGE094_PHASE1_EVIDENCE_REVOCATION_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage094_evidence_revocation_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE093_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage093_evidence_grade_stage_review_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-094_证据撤回.md"
)
P3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage094-p3-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-24-stage094-p4-local.json"
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


class Stage094EvidenceRevocationPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage094_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage094_phase3_scenarios", P3_MODULE)
        cls.report = cls.module.build_evidence_revocation_phase4_delivery_report()

    def _phase3_report(self):
        return self.phase3.build_evidence_revocation_phase3_report()

    def test_artifacts_phase_identity_and_frozen_taskpack_exist(self):
        for path in (
            SCOPE,
            CONTRACT,
            MODULE,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P2_SCOPE,
            P2_CONTRACT,
            P1_SCOPE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            TASKPACK,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual(
            "ids.stage094.evidence_revocation.phase4.delivery.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("STAGE-094", self.contract["stage"])
        self.assertEqual("IDS-STAGE094-P4", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE094-P4", self.contract["task_id"])
        self.assertEqual("IDS-STAGE094-P4-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE094-REVIEW-GATE", self.contract["next_gate"])

    def test_single_authority_replay_shape_and_phase_boundary_are_explicit(self):
        source = self.contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE094_TASKPACK_AND_STAGE093_REVIEWED_STAGE094_PHASE1_PHASE2_PHASE3_CONTROL_CONTRACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(source["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(source["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(source["second_authoritative_source_created"])
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(self.module.CONTROL_PREFIX, replay["reference_prefix_required"])
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(29, replay["required_control_input_field_count"])
        self.assertEqual(11, replay["required_projection_group_count"])
        self.assertEqual(630, replay["expected_phase2_field_check_count"])
        self.assertEqual(7, replay["scenario_count"])
        self.assertEqual(32, replay["scenario_field_count"])
        self.assertEqual(224, replay["scenario_field_check_count"])
        boundary = self.contract["stage_boundary"]
        for field in (
            "stage093_review_evidence_declared",
            "stage094_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_started",
            "stage094_review_started",
            "stage095_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_shapes_are_exact(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_control_shape_preserved"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["control_references_opaque"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertEqual(6, report["phase2_control_request_count"])
        self.assertEqual(29, report["phase2_control_input_field_count"])
        self.assertEqual(11, report["phase2_projection_group_count"])
        self.assertEqual(630, report["phase2_control_field_check_count"])
        self.assertEqual(7, report["phase3_scenario_count"])
        self.assertEqual(32, report["phase3_scenario_field_count"])
        self.assertEqual(224, report["phase3_scenario_field_check_count"])
        self.assertEqual(517, report["delivery_field_check_count"])

    def test_all_delivery_groups_have_exact_shape_and_opaque_references(self):
        groups = (
            (
                "evidence_ledger_sample_control_records",
                self.module.EVIDENCE_LEDGER_SAMPLE_FIELDS,
                7,
            ),
            (
                "evidence_grade_report_control_records",
                self.module.EVIDENCE_GRADE_REPORT_FIELDS,
                7,
            ),
            (
                "revocation_impact_control_records",
                self.module.REVOCATION_IMPACT_FIELDS,
                7,
            ),
            (
                "regression_test_control_records",
                self.module.REGRESSION_TEST_RECORD_FIELDS,
                7,
            ),
            (
                "non_conclusion_evidence_type_control_records",
                self.module.NON_CONCLUSION_EVIDENCE_TYPE_FIELDS,
                7,
            ),
            (
                "degradation_instruction_control_records",
                self.module.DEGRADATION_INSTRUCTION_FIELDS,
                4,
            ),
            (
                "revocation_recovery_instruction_control_records",
                self.module.REVOCATION_RECOVERY_INSTRUCTION_FIELDS,
                2,
            ),
        )
        for name, fields, count in groups:
            records = self.report[name]
            with self.subTest(group=name):
                self.assertEqual(count, len(records))
            for record in records:
                with self.subTest(group=name, record=record):
                    self.assertEqual(set(fields), set(record))
                    for field, value in record.items():
                        if field.endswith("_ref") and value is not None:
                            self.assertTrue(
                                self.module.CONTROL_PREFIX in value
                                or self.module.DELIVERY_PREFIX in value
                            )
                        if field.endswith("_ref") and value is None:
                            self.assertEqual("evidence_id_ref", field)
                            self.assertEqual(
                                "no_internal_evidence_revocation_control",
                                record["scenario_id"],
                            )

    def test_taskpack_semantics_non_conclusion_and_chinese_feedback_are_explicit(self):
        samples = {
            item["scenario_id"]: item
            for item in self.report["evidence_ledger_sample_control_records"]
        }
        self.assertIsNone(samples["no_internal_evidence_revocation_control"]["evidence_id_ref"])
        grades = {
            item["scenario_id"]: item
            for item in self.report["evidence_grade_report_control_records"]
        }
        self.assertEqual(
            "CONTROL_LOW_OCR_DEGRADED_NOT_ACCEPTED",
            grades["low_ocr_evidence_revocation_degradation_control"][
                "evidence_disposition_state"
            ],
        )
        self.assertEqual(
            "CONTROL_OLD_VERSION_DEGRADED_NOT_ACCEPTED",
            grades["old_version_evidence_revocation_degradation_control"][
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
        for record in self.report["non_conclusion_evidence_type_control_records"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertEqual("CONTROL_NOT_A_CONCLUSION_BASIS", record["non_conclusion_state"])
                self.assertFalse(record["automatic_conclusion_allowed"])
                self.assertTrue(record["human_handling_required"])
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

    def test_degradation_recovery_and_runtime_boundaries_are_closed(self):
        self.assertEqual(4, len(self.report["degradation_instruction_control_records"]))
        self.assertEqual(2, len(self.report["revocation_recovery_instruction_control_records"]))
        for record in self.report["degradation_instruction_control_records"]:
            with self.subTest(record=record["instruction_id"]):
                self.assertFalse(record["actual_evidence_degradation_performed"])
                self.assertFalse(record["automatic_degradation_allowed"])
                self.assertTrue(record["human_handling_required"])
        for record in self.report["revocation_recovery_instruction_control_records"]:
            with self.subTest(record=record["instruction_id"]):
                self.assertFalse(record["actual_revocation_execution_performed"])
                self.assertFalse(record["actual_recovery_execution_performed"])
                self.assertTrue(record["human_handling_required"])
        self.assertTrue(all(value is False for value in self.report["runtime_boundary"].values()))
        for key, value in self.report.items():
            if key.startswith("actual_") and key.endswith("_count"):
                with self.subTest(key=key):
                    self.assertEqual(0, value)

    def test_contract_failure_and_stop_rules_are_explicit(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(18, failures["failure_state_count"])
        self.assertEqual(list(self.module.FAILURE_STATES), failures["declared_failure_states"])
        for value in self.contract["runtime_boundary"].values():
            self.assertFalse(value)
        for value in failures.values():
            if isinstance(value, bool):
                self.assertFalse(value)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_EVIDENCE_REVOCATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["preserve_stage094_phase1_phase2_phase3"])
        self.assertTrue(rollback["preserve_stage093_reviewed_artifacts"])

    def test_invalid_phase3_output_returns_controlled_failure(self):
        failed = self.module.build_evidence_revocation_phase4_delivery_report(lambda: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, failed["next_gate"])
        self.assertEqual([], failed["evidence_ledger_sample_control_records"])

    def test_phase3_runtime_signal_returns_controlled_failure(self):
        def runtime_signal():
            altered = copy.deepcopy(self._phase3_report())
            altered["runtime_boundary"]["model_token_consumption_performed"] = True
            return altered

        failed = self.module.build_evidence_revocation_phase4_delivery_report(
            runtime_signal
        )
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase3_side_effect_free"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])

    def test_nonopaque_reference_and_semantic_drift_return_specific_failures(self):
        def nonopaque_reference():
            altered = copy.deepcopy(self._phase3_report())
            altered["scenario_results"][0]["evidence_gap_ref"] = "unscoped-reference"
            return altered

        failed = self.module.build_evidence_revocation_phase4_delivery_report(
            nonopaque_reference
        )
        self.assertFalse(failed["valid"])
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", failed["failure_state"])

        def degradation_drift():
            altered = copy.deepcopy(self._phase3_report())
            altered["scenario_results"][1]["evidence_disposition_state"] = (
                "CONTROL_EVIDENCE_GAP_PENDING_HUMAN_WHITEBOX_REVIEW"
            )
            return altered

        failed = self.module.build_evidence_revocation_phase4_delivery_report(
            degradation_drift
        )
        self.assertFalse(failed["valid"])
        self.assertEqual(
            "EVIDENCE_DEGRADATION_DISPOSITION_MISSING", failed["failure_state"]
        )

    def test_predecessor_or_current_governance_record_is_consistent(self):
        for path in (P3_RECEIPT, STATUS, PLAN, ACCEPTANCE, EVENTS, ROADMAP):
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
        stage095_phase1_current = (
            "IDS-STAGE095",
            "IDS-STAGE095-P1",
            "IDS-V0_1-STAGE095-P1",
            "IDS-STAGE095-P2-GATE",
        )
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
        p3_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P3",
            "IDS-V0_1-STAGE094-P3",
            "IDS-STAGE094-P4-GATE",
        )
        p4_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-P4",
            "IDS-V0_1-STAGE094-P4",
            "IDS-STAGE094-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE094",
            "IDS-STAGE094-REVIEW",
            "IDS-V0_1-STAGE094-REVIEW",
            "IDS-STAGE095-P1-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        if current == p4_current:
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P4 交付证据已完成", acceptance_by_id["ACC-STAGE-094"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P4-01"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P4-02"])
            self.assertEqual("已通过", acceptance_by_id["ACC-STAGE094-P4-03"])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE094-P4-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE094-P4-20260824-001", event_ids)
            self.assertEqual("IDS-STAGE094-REVIEW-GATE", receipt["next_gate"])
            self.assertEqual(self.module.PASS_RESULT, receipt["result"])
            self.assertEqual(517, receipt["controlled_static_shape"]["delivery_field_check_count"])
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        else:
            self.assertIn(
                current,
                (
                    stage095_phase1_current,
                    stage095_phase2_current,
                    stage095_phase3_current,
                    stage095_phase4_current,
                    (
                        "IDS-STAGE095",
                        "IDS-STAGE095-REVIEW",
                        "IDS-V0_1-STAGE095-REVIEW",
                        "IDS-STAGE096-P1-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P1",
                        "IDS-V0_1-STAGE096-P1",
                        "IDS-STAGE096-P2-GATE",
                    ),
                    (
                        "IDS-STAGE096",
                        "IDS-STAGE096-P2",
                        "IDS-V0_1-STAGE096-P2",
                        "IDS-STAGE096-P3-GATE",
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
                    p3_current,
                    review_current,
                ),
            )


if __name__ == "__main__":
    unittest.main()
