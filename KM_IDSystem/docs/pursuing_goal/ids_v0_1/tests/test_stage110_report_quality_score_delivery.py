"""Stage110 P4 报告质量评分 metadata-only 交付证据的聚焦验证。"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-110_报告质量评分.md"
)
SCOPE = BASE / "STAGE110_PHASE4_REPORT_QUALITY_SCORE_DELIVERY.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage110_report_quality_score_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage110_report_quality_score_delivery.py"
PHASE3_SCOPE = BASE / "STAGE110_PHASE3_REPORT_QUALITY_SCORE_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_controlled_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_controlled_scenarios.py"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p3-local.json"
PHASE2_SCOPE = BASE / "STAGE110_PHASE2_REPORT_QUALITY_SCORE_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_control_slice_contract.json"
)
PHASE1_SCOPE = BASE / "STAGE110_PHASE1_REPORT_QUALITY_SCORE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage110_report_quality_score_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE109_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage110ReportQualityScorePhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage110_report_quality_score_delivery"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_quality_score_phase4_delivery_report()

    def _mutated_phase3_executor(self, mutation):
        def executor():
            phase3_module = self.module._load_phase3_module()
            result = copy.deepcopy(
                phase3_module.build_report_quality_score_phase3_report()
            )
            mutation(result)
            return result

        return executor

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            TASKPACK,
            SCOPE,
            CONTRACT,
            MODULE,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE3_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage110.report_quality_score.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-110", contract["stage"])
        self.assertEqual("IDS-STAGE110-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE110-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-110", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE110-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE110-REVIEW-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE110_TASKPACK_STAGE110_PHASE1_PHASE2_PHASE3_AND_"
            "STAGE109_REVIEWED_REPORT_IMPACT_ANALYSIS_CONTROL_ARTIFACTS_ONLY",
            authority["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "delivered_report_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
        for field, value in authority.items():
            if field.startswith("actual_") or field.endswith("_created"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        boundary = contract["stage_boundary"]
        for field in (
            "stage109_review_evidence_declared",
            "stage110_phase1_completed",
            "stage110_phase2_completed",
            "stage110_phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage110_review_started",
            "stage111_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(
            "ids.stage110.report_quality_score.phase3.v1",
            replay["predecessor_schema_version_required"],
        )
        self.assertEqual(
            "CONTROL_ONLY_IN_MEMORY_REPORT_QUALITY_SCORE_SCENARIOS",
            replay["predecessor_record_kind_required"],
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(42, replay["phase2_input_field_count"])
        self.assertEqual(40, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(126, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(630, replay["phase2_projection_field_count_total"])
        self.assertEqual(5, replay["scenario_count"])
        self.assertEqual(52, replay["scenario_field_count"])
        self.assertEqual(260, replay["scenario_field_check_count"])
        self.assertEqual(5, replay["control_view_count"])
        self.assertEqual(5, replay["human_handling_count"])
        self.assertEqual(2, replay["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(
            1, replay["quality_whitebox_confirmation_required_scenario_count"]
        )
        self.assertFalse(replay["actual_phase3_runtime_execution_allowed"])

        delivery = self.contract["delivery_evidence_contract"]
        self.assertEqual(5, delivery["report_sample_control_record_count"])
        self.assertEqual(17, delivery["report_sample_field_count_per_record"])
        self.assertEqual(5, delivery["report_snapshot_control_record_count"])
        self.assertEqual(13, delivery["report_snapshot_field_count_per_record"])
        self.assertEqual(5, delivery["report_quality_score_control_record_count"])
        self.assertEqual(13, delivery["report_quality_score_field_count_per_record"])
        self.assertEqual(5, delivery["report_impact_analysis_control_record_count"])
        self.assertEqual(15, delivery["report_impact_analysis_field_count_per_record"])
        self.assertEqual(
            5,
            delivery[
                "report_template_and_whitebox_confirmation_control_record_count"
            ],
        )
        self.assertEqual(
            14,
            delivery[
                "report_template_and_whitebox_confirmation_field_count_per_record"
            ],
        )
        self.assertEqual(2, delivery["regeneration_and_withdrawal_control_record_count"])
        self.assertEqual(14, delivery["regeneration_and_withdrawal_field_count_per_record"])
        self.assertEqual(388, delivery["delivery_field_check_count"])
        self.assertEqual(17, delivery["failure_state_count"])
        self.assertEqual(4, delivery["chinese_feedback_count"])

    def test_report_projects_closed_metadata_only_delivery_evidence(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE110-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE110-REVIEW-GATE", report["next_gate"])
        for field in (
            "phase3_control_shape_preserved",
            "phase3_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(42, report["phase2_input_field_count"])
        self.assertEqual(40, report["phase2_phase1_reference_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(126, report["phase2_projection_field_count_per_request"])
        self.assertEqual(630, report["phase2_projection_field_count_total"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(52, report["scenario_field_count"])
        self.assertEqual(260, report["scenario_field_check_count"])
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(5, report["human_handling_count"])
        self.assertEqual(2, report["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(
            1, report["quality_whitebox_confirmation_required_scenario_count"]
        )
        self.assertEqual(388, report["delivery_field_check_count"])
        self.assertEqual(17, report["failure_state_count"])
        self.assertEqual(4, len(report["operator_feedback"]))
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )

    def test_delivery_group_shapes_and_evidence_binding_are_exact(self) -> None:
        report = self.report
        expected_groups = {
            "report_sample_control_records": self.module.REPORT_SAMPLE_FIELDS,
            "report_snapshot_control_records": self.module.REPORT_SNAPSHOT_FIELDS,
            "report_quality_score_control_records": self.module.REPORT_QUALITY_SCORE_FIELDS,
            "report_impact_analysis_control_records": self.module.REPORT_IMPACT_ANALYSIS_FIELDS,
            "report_template_and_whitebox_confirmation_control_records": (
                self.module.REPORT_TEMPLATE_AND_WHITEBOX_CONFIRMATION_FIELDS
            ),
        }
        for group, fields in expected_groups.items():
            records = report[group]
            with self.subTest(group=group):
                self.assertEqual(5, len(records))
                for record in records:
                    self.assertEqual(set(fields), set(record))
                    self.assertTrue(
                        record["delivery_record_id"].startswith(
                            ":control:stage110-p4:"
                        )
                    )
                    self.assertTrue(
                        all(
                            value is False
                            for key, value in record.items()
                            if key.startswith("actual_")
                        )
                    )

        for record in report["report_sample_control_records"]:
            with self.subTest(record=record["scenario_id"]):
                self.assertNotEqual(
                    record["evidence_id_ref"] is None,
                    record["evidence_gap_ref"] is None,
                )
                for field in (
                    "report_id_ref",
                    "critical_conclusion_ref",
                    "evidence_grade_ref",
                    "citation_source_ref",
                    "citation_page_ref",
                    "report_snapshot_ref",
                ):
                    self.assertTrue(record[field].startswith(":control:stage110-p2:"))
                self.assertFalse(record["automatic_final_conclusion_allowed"])

        quality_records = report["report_quality_score_control_records"]
        self.assertEqual(
            1,
            sum(record["quality_whitebox_confirmation_required"] for record in quality_records),
        )
        self.assertTrue(
            all(
                record["quality_score_delivery_state"]
                == "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED"
                for record in quality_records
            )
        )

    def test_taskpack_special_cases_and_lifecycle_controls_are_preserved(self) -> None:
        records_by_scenario = {
            record["scenario_id"]: record
            for record in self.report["report_impact_analysis_control_records"]
        }
        self.assertEqual(
            "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            records_by_scenario[
                "source_withdrawal_evidence_gap_report_status_impact_control"
            ]["source_withdrawal_report_status_impact_state"],
        )
        self.assertEqual(
            "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            records_by_scenario[
                "evidence_downgrade_evidence_id_report_status_impact_control"
            ]["evidence_downgrade_report_status_impact_state"],
        )
        self.assertEqual(
            "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            records_by_scenario[
                "index_version_change_evidence_gap_report_status_impact_control"
            ]["index_version_change_report_status_impact_state"],
        )
        template_records = self.report[
            "report_template_and_whitebox_confirmation_control_records"
        ]
        self.assertEqual(
            2,
            sum(
                record["business_line_whitebox_confirmation_required"]
                for record in template_records
            ),
        )
        self.assertTrue(
            all(
                record["final_conclusion_state"]
                == "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED"
                for record in template_records
            )
        )
        lifecycle = self.report["regeneration_and_withdrawal_control_records"]
        self.assertEqual(2, len(lifecycle))
        self.assertEqual(
            {"REPORT_REGENERATION", "REPORT_WITHDRAWAL"},
            {record["control_domain"] for record in lifecycle},
        )
        for record in lifecycle:
            with self.subTest(control_domain=record["control_domain"]):
                self.assertEqual(self.module.P3_PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_report_regeneration_performed"])
                self.assertFalse(record["actual_report_withdrawal_performed"])
                self.assertFalse(record["persistent_state_write_performed"])

    def test_predecessor_drift_fails_closed(self) -> None:
        shape_mismatch = self.module.build_report_quality_score_phase4_delivery_report(
            phase3_executor=lambda: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = self.module.build_report_quality_score_phase4_delivery_report(
            self._mutated_phase3_executor(break_runtime_boundary)
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual(
            "PHASE3_RUNTIME_BOUNDARY_BREACH", runtime_drift["failure_state"]
        )

        def break_evidence_binding(result):
            result["scenario_results"][0]["evidence_id_ref"] = None

        binding_drift = self.module.build_report_quality_score_phase4_delivery_report(
            self._mutated_phase3_executor(break_evidence_binding)
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual(
            "PHASE3_CONTROL_SHAPE_MISMATCH", binding_drift["failure_state"]
        )

        def allow_external_as_internal(result):
            result["scenario_results"][4][
                "external_augmentation_may_not_be_internal_project_evidence"
            ] = False

        external_drift = self.module.build_report_quality_score_phase4_delivery_report(
            self._mutated_phase3_executor(allow_external_as_internal)
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual(
            "PHASE3_CONTROL_SHAPE_MISMATCH", external_drift["failure_state"]
        )

        for failed_report in (
            shape_mismatch,
            runtime_drift,
            binding_drift,
            external_drift,
        ):
            with self.subTest(failure=failed_report["failure_state"]):
                self.assertEqual(0, failed_report["delivery_field_check_count"])
                for group, _fields in self.module.DELIVERY_GROUPS:
                    self.assertEqual([], failed_report[group])
                self.assertTrue(
                    all(value is False for value in failed_report["runtime_boundary"].values())
                )
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed_report.items()
                        if key.startswith("actual_") and isinstance(value, int)
                    )
                )

    def test_runtime_receipt_and_current_governance_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "metadata-only 交付控制记录",
            "资料撤回、证据降级和索引版本变化",
            "不能成为内部项目依据",
            "IDS-STAGE110-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("validation", {}).get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P4 最终治理投影将在冻结本地验收完成后启用")

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase3_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P3",
            "IDS-V0_1-STAGE110-P3",
            "IDS-STAGE110-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P4",
            "IDS-V0_1-STAGE110-P4",
            "IDS-STAGE110-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-REVIEW",
            "IDS-V0_1-STAGE110-REVIEW",
            "IDS-STAGE111-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {phase3_current}, status, plan, ROADMAP
        )
        self.assertEqual(phase4_current, current)
        self.assertTrue(is_current_projection)
        self.assertEqual(
            "REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_QUALITY_SCORE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE110-P4-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE110-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(388, receipt["delivery_evidence"]["delivery_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["validation"]["final_validation"]
        self.assertEqual(8, validation["focused_delivery_test_count"])
        self.assertTrue(validation["stage005_governance_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P4 报告质量评分交付控制证据已完成",
            acceptance_by_id["ACC-STAGE-110"],
        )
        for acceptance_id in (
            "ACC-STAGE110-P4-01",
            "ACC-STAGE110-P4-02",
            "ACC-STAGE110-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE110-P4-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE110-P4-20260826-001", event_ids)
        self.assertNotIn(review_current, {current})


if __name__ == "__main__":
    unittest.main()
