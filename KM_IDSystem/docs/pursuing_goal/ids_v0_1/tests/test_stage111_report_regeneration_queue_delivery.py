"""Stage111 报告重新生成队列 Phase 4 纯内存交付控制的聚焦验证。"""

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
SCOPE = BASE / "STAGE111_PHASE4_REPORT_REGENERATION_QUEUE_DELIVERY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_delivery_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_delivery.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-111_报告重新生成队列.md"
)
PHASE1_SCOPE = BASE / "STAGE111_PHASE1_REPORT_REGENERATION_QUEUE_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage111_report_regeneration_queue_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE111_PHASE2_REPORT_REGENERATION_QUEUE_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE111_PHASE3_REPORT_REGENERATION_QUEUE_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_controlled_scenarios_contract.json"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p3-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE110_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage111ReportRegenerationQueuePhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage111_report_regeneration_queue_delivery"
        )
        cls.phase3 = importlib.import_module(
            "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
            "stage111_report_regeneration_queue_controlled_scenarios"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_regeneration_queue_phase4_delivery_report()

    def _mutated_phase3_executor(self, mutator):
        def executor():
            result = copy.deepcopy(
                self.phase3.build_report_regeneration_queue_phase3_report()
            )
            mutator(result)
            return result

        return executor

    def test_required_artifacts_and_predecessors_exist(self) -> None:
        for artifact in (
            TASKPACK,
            SCOPE,
            CONTRACT,
            MODULE,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_RECEIPT,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_RECEIPT,
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
            "ids.stage111.report_regeneration_queue.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-111", contract["stage"])
        self.assertEqual("IDS-STAGE111-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE111-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-111", contract["acceptance_id"])
        self.assertEqual(
            "REPORT_REGENERATION_QUEUE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE111-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE111-REVIEW-GATE", contract["next_gate"])
        authority = contract["source_authority"]
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
            "stage110_review_evidence_declared",
            "stage111_phase1_completed",
            "stage111_phase2_completed",
            "stage111_phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage111_review_started",
            "stage112_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase3_replay_and_delivery_contract_have_exact_shape(self) -> None:
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(
            self.phase3.SCHEMA_VERSION,
            replay["predecessor_schema_version_required"],
        )
        self.assertEqual(
            self.phase3.RECORD_KIND,
            replay["predecessor_record_kind_required"],
        )
        self.assertEqual(
            self.phase3.PASS_RESULT,
            replay["predecessor_pass_result_required"],
        )
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(32, replay["phase2_input_field_count"])
        self.assertEqual(30, replay["phase2_phase1_reference_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(88, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(440, replay["phase2_projection_field_count_total"])
        self.assertEqual(5, replay["scenario_count"])
        self.assertEqual(44, replay["scenario_field_count"])
        self.assertEqual(220, replay["scenario_field_check_count"])
        self.assertEqual(5, replay["control_view_count"])
        self.assertEqual(5, replay["business_line_whitebox_handling_count"])
        self.assertEqual(5, replay["whitebox_confirmation_required_scenario_count"])
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
        self.assertEqual(17, len(self.module.FAILURE_STATES))
        self.assertEqual(4, len(self.module.OPERATOR_FEEDBACK))

    def test_report_projects_closed_metadata_only_delivery_evidence(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE111-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE111-REVIEW-GATE", report["next_gate"])
        for field in (
            "phase3_control_shape_preserved",
            "phase3_side_effect_free",
            "control_references_opaque",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertEqual(5, report["phase2_control_request_count"])
        self.assertEqual(32, report["phase2_input_field_count"])
        self.assertEqual(30, report["phase2_phase1_reference_field_count"])
        self.assertEqual(4, report["phase2_projection_group_count"])
        self.assertEqual(88, report["phase2_projection_field_count_per_request"])
        self.assertEqual(440, report["phase2_projection_field_count_total"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(44, report["scenario_field_count"])
        self.assertEqual(220, report["scenario_field_check_count"])
        self.assertEqual(5, report["control_view_count"])
        self.assertEqual(5, report["business_line_whitebox_handling_count"])
        self.assertEqual(5, report["whitebox_confirmation_required_scenario_count"])
        self.assertEqual(388, report["delivery_field_check_count"])
        self.assertEqual(17, report["failure_state_count"])
        self.assertEqual(4, len(report["operator_feedback"]))
        self.assertEqual(list(self.module.OPERATOR_FEEDBACK), report["operator_feedback"])
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
            "report_quality_score_control_records": (
                self.module.REPORT_QUALITY_SCORE_FIELDS
            ),
            "report_impact_analysis_control_records": (
                self.module.REPORT_IMPACT_ANALYSIS_FIELDS
            ),
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
                            ":control:stage111-p4:"
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
                    self.assertTrue(record[field].startswith(":control:stage111-p2:"))
                self.assertFalse(record["automatic_final_conclusion_allowed"])

        for record in report["report_snapshot_control_records"]:
            with self.subTest(record=record["scenario_id"]):
                for field in (
                    "data_snapshot_control_ref",
                    "index_version_control_ref",
                    "evidence_snapshot_control_ref",
                    "model_snapshot_control_ref",
                    "generated_at_control_ref",
                ):
                    self.assertTrue(
                        record[field].startswith(":control:stage111-p4:")
                    )
                self.assertFalse(record["actual_report_snapshot_persisted"])

        quality_records = report["report_quality_score_control_records"]
        self.assertTrue(
            all(
                record["business_line_whitebox_confirmation_required"]
                for record in quality_records
            )
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
        self.assertIn(
            "REQUIRED",
            records_by_scenario[
                "source_withdrawal_evidence_gap_report_status_control"
            ]["source_withdrawal_report_status_impact_state"],
        )
        self.assertIn(
            "REQUIRED",
            records_by_scenario[
                "evidence_downgrade_evidence_id_report_status_control"
            ]["evidence_downgrade_report_status_impact_state"],
        )
        self.assertIn(
            "REQUIRED",
            records_by_scenario[
                "evidence_conflict_evidence_gap_report_status_control"
            ]["evidence_conflict_report_status_impact_state"],
        )
        self.assertIn(
            "REQUIRED",
            records_by_scenario[
                "index_version_change_evidence_id_report_status_control"
            ]["index_version_change_report_status_impact_state"],
        )
        template_records = self.report[
            "report_template_and_whitebox_confirmation_control_records"
        ]
        self.assertEqual(
            5,
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
                self.assertEqual(
                    self.module.P3_PASS_RESULT, record["rollback_target_result"]
                )
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_report_regeneration_performed"])
                self.assertFalse(record["actual_report_withdrawal_performed"])
                self.assertFalse(record["persistent_state_write_performed"])

    def test_predecessor_drift_fails_closed(self) -> None:
        shape_mismatch = (
            self.module.build_report_regeneration_queue_phase4_delivery_report(
                phase3_executor=lambda: {}
            )
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"])

        def break_runtime_boundary(result):
            result["runtime_boundary"]["model_call_performed"] = True

        runtime_drift = (
            self.module.build_report_regeneration_queue_phase4_delivery_report(
                self._mutated_phase3_executor(break_runtime_boundary)
            )
        )
        self.assertFalse(runtime_drift["valid"])
        self.assertEqual(
            "PHASE3_RUNTIME_BOUNDARY_BREACH", runtime_drift["failure_state"]
        )

        def break_evidence_binding(result):
            result["scenario_results"][0]["evidence_id_ref"] = None

        binding_drift = (
            self.module.build_report_regeneration_queue_phase4_delivery_report(
                self._mutated_phase3_executor(break_evidence_binding)
            )
        )
        self.assertFalse(binding_drift["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", binding_drift["failure_state"])

        def allow_external_as_internal(result):
            result["scenario_results"][4][
                "external_augmentation_may_not_be_internal_project_evidence"
            ] = False

        external_drift = (
            self.module.build_report_regeneration_queue_phase4_delivery_report(
                self._mutated_phase3_executor(allow_external_as_internal)
            )
        )
        self.assertFalse(external_drift["valid"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", external_drift["failure_state"])

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
                    all(
                        value is False
                        for value in failed_report["runtime_boundary"].values()
                    )
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
            "资料撤回、证据降级、证据冲突和索引版本变化",
            "不成为内部项目依据",
            "IDS-STAGE111-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("P4 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase3_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-P3",
            "IDS-V0_1-STAGE111-P3",
            "IDS-STAGE111-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-P4",
            "IDS-V0_1-STAGE111-P4",
            "IDS-STAGE111-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-REVIEW",
            "IDS-V0_1-STAGE111-REVIEW",
            "IDS-STAGE112-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase3_current, phase4_current, review_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertTrue(is_current_projection or current == phase4_current)
        if is_current_projection and current != phase4_current:
            return
        self.assertEqual(phase4_current, current)
        self.assertEqual(
            "REPORT_REGENERATION_QUEUE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(
            "PASS_REPORT_REGENERATION_QUEUE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertEqual("IDS-STAGE111-P4-GATE", receipt["entry_gate"])
        self.assertEqual("IDS-STAGE111-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(388, receipt["delivery_evidence"]["delivery_field_check_count"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual(8, validation["focused_delivery_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(
            "P4 报告重新生成队列交付控制证据已完成",
            acceptance_by_id["ACC-STAGE-111"],
        )
        for acceptance_id in (
            "ACC-STAGE111-P4-01",
            "ACC-STAGE111-P4-02",
            "ACC-STAGE111-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE111-P4-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE111-P4-20260827-001", event_ids)

if __name__ == "__main__":
    unittest.main()
