"""Stage106 外部增强意见章节 Phase 4 纯内存交付证据的聚焦验证。"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE106_PHASE4_EXTERNAL_AUGMENTATION_OPINION_DELIVERY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_delivery_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_delivery.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-106_外部增强意见章节.md"
)
PHASE1_SCOPE = BASE / "STAGE106_PHASE1_EXTERNAL_AUGMENTATION_OPINION_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage106_external_augmentation_opinion_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE106_PHASE2_EXTERNAL_AUGMENTATION_OPINION_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE106_PHASE3_EXTERNAL_AUGMENTATION_OPINION_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_controlled_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage106_external_augmentation_opinion_controlled_scenarios.py"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p3-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE105_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage106-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage106ExternalAugmentationOpinionPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module(
            MODULE, "stage106_external_augmentation_opinion_delivery_for_test"
        )
        cls.phase3 = _load_module(
            PHASE3_MODULE,
            "stage106_external_augmentation_opinion_phase3_for_delivery_test",
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase3_report = cls.phase3.build_external_augmentation_opinion_phase3_report()
        cls.report = cls.module.build_external_augmentation_opinion_phase4_delivery_report()

    def test_required_scope_contract_modules_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE2_RECEIPT,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE3_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessor_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(
            "ids.stage106.external_augmentation_opinion.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-106", contract["stage"])
        self.assertEqual("IDS-STAGE106-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE106-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-106", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE106-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE106-REVIEW-GATE", contract["next_gate"])
        self.assertEqual(
            "EXTERNAL_AUGMENTATION_OPINION_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE106_TASKPACK_STAGE106_PHASE1_PHASE2_PHASE3_AND_"
            "STAGE105_REVIEWED_REPORT_EVIDENCE_BINDING_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field in (
            "source_document_remains_authoritative",
            "evidence_ledger_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(source[field])
        for field, value in source.items():
            if field.startswith("actual_") or field.endswith("_created") or field.startswith(
                "delivery_control_metadata_can_"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)

        predecessor = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(
            self.module.P3_SCHEMA_VERSION,
            predecessor["predecessor_schema_version_required"],
        )
        self.assertEqual(
            self.module.P3_RECORD_KIND,
            predecessor["predecessor_record_kind_required"],
        )
        self.assertEqual(
            self.module.P3_PASS_RESULT,
            predecessor["predecessor_pass_result_required"],
        )
        self.assertEqual(5, predecessor["phase2_control_request_count"])
        self.assertEqual(30, predecessor["phase2_input_field_count"])
        self.assertEqual(27, predecessor["phase2_phase1_reference_field_count"])
        self.assertEqual(1, predecessor["phase2_added_control_reference_field_count"])
        self.assertEqual(4, predecessor["phase2_projection_group_count"])
        self.assertEqual(74, predecessor["phase2_projection_field_count_per_request"])
        self.assertEqual(370, predecessor["phase2_projection_field_count_total"])
        self.assertEqual(5, predecessor["scenario_count"])
        self.assertEqual(34, predecessor["scenario_field_count"])
        self.assertEqual(170, predecessor["scenario_field_check_count"])
        self.assertEqual(5, predecessor["control_view_count"])
        self.assertEqual(5, predecessor["human_handling_count"])
        self.assertEqual(2, predecessor["whitebox_confirmation_required_scenario_count"])
        self.assertFalse(predecessor["actual_phase3_runtime_execution_allowed"])

        delivery = contract["delivery_evidence_contract"]
        self.assertEqual(388, delivery["delivery_field_check_count"])
        self.assertEqual(17, delivery["failure_state_count"])
        self.assertEqual(4, delivery["chinese_feedback_count"])
        self.assertTrue(delivery["delivery_metadata_only"])
        for field, value in delivery.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        boundary = contract["stage_boundary"]
        for field in (
            "stage105_review_evidence_declared",
            "stage106_started",
            "stage106_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage106_review_started",
            "stage107_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_delivery_shapes_control_references_and_counts_are_exact(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE106-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE106-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(388, report["delivery_field_check_count"])
        for group_name, fields in self.module.DELIVERY_GROUPS:
            expected_count = (
                2
                if group_name == "regeneration_and_withdrawal_control_records"
                else 5
            )
            records = report[group_name]
            with self.subTest(group=group_name):
                self.assertEqual(expected_count, len(records))
            for record in records:
                with self.subTest(group=group_name, record=record):
                    self.assertEqual(set(fields), set(record))
                    for field, value in record.items():
                        if field in {"evidence_id_ref", "evidence_gap_ref"} and value is None:
                            continue
                        if field.endswith("_ref") or field in {
                            "delivery_record_id",
                            "instruction_id",
                        }:
                            self.assertTrue(
                                value.startswith(":control:stage106-p2:")
                                or value.startswith(":control:stage106-p4:")
                            )

    def test_taskpack_delivery_semantics_and_whitebox_gates_are_preserved(self) -> None:
        samples = {
            item["scenario_id"]: item
            for item in self.report["report_sample_control_records"]
        }
        evidence_id = samples[
            "critical_conclusion_evidence_id_binding_integrity_control"
        ]
        self.assertIsNotNone(evidence_id["evidence_id_ref"])
        self.assertIsNone(evidence_id["evidence_gap_ref"])
        evidence_gap = samples[
            "critical_conclusion_evidence_gap_binding_integrity_control"
        ]
        self.assertIsNone(evidence_gap["evidence_id_ref"])
        self.assertIsNotNone(evidence_gap["evidence_gap_ref"])
        external = samples[
            "external_augmentation_retains_external_source_type_control"
        ]
        self.assertEqual(
            "CONTROL_EXTERNAL_AUGMENTATION_OPINION_RETAINS_EXTERNAL_PUBLIC_REFERENCE_"
            "AND_MODEL_REASONING_SEPARATE_FROM_INTERNAL_EVIDENCE",
            external["external_augmentation_source_separation_state"],
        )

        impacts = {
            item["scenario_id"]: item
            for item in self.report["report_impact_analysis_control_records"]
        }
        lifecycle = impacts[
            "withdrawal_downgrade_and_index_change_impact_report_status_control"
        ]
        self.assertEqual(
            "CONTROL_MATERIAL_WITHDRAWAL_EVIDENCE_DOWNGRADE_INDEX_VERSION_CHANGE",
            lifecycle["report_status_impact_trigger"],
        )
        self.assertEqual(
            "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED",
            lifecycle["report_status_impact_state"],
        )
        self.assertEqual(
            "CONTROL_EVIDENCE_GRADE_DOWNGRADE_IMPACTS_REPORT_STATUS",
            lifecycle["evidence_grade_downgrade_state"],
        )
        self.assertEqual(
            "CONTROL_INDEX_VERSION_CHANGE_IMPACTS_REPORT_STATUS",
            lifecycle["index_version_change_state"],
        )
        self.assertEqual(
            "CONTROL_MATERIAL_WITHDRAWAL_IMPACTS_REPORT_STATUS",
            lifecycle["material_withdrawal_state"],
        )

        for record in self.report["report_quality_score_control_records"]:
            with self.subTest(record=record["scenario_id"]):
                self.assertEqual(
                    "CONTROL_REPORT_QUALITY_SCORE_REFERENCE_ONLY_NOT_CALCULATED",
                    record["quality_score_delivery_state"],
                )
                self.assertFalse(record["actual_report_quality_score_calculated"])
                self.assertFalse(record["actual_report_quality_score_persisted"])

        templates = self.report[
            "report_template_and_whitebox_confirmation_control_records"
        ]
        self.assertEqual(
            2,
            sum(
                record["business_line_whitebox_confirmation_required"]
                for record in templates
            ),
        )
        for record in templates:
            with self.subTest(record=record["scenario_id"]):
                self.assertEqual(
                    "CONTROL_REPORT_TEMPLATE_LIMIT_RECORDED_REFERENCE_ONLY",
                    record["report_template_limit_delivery_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    record["final_conclusion_state"],
                )
                self.assertFalse(record["actual_template_constraint_reviewed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
                self.assertFalse(record["actual_final_conclusion_published"])
                self.assertFalse(record["actual_report_or_pdf_generated"])

    def test_regeneration_and_withdrawal_controls_return_to_phase3(self) -> None:
        records = self.report["regeneration_and_withdrawal_control_records"]
        self.assertEqual(
            {"report_regeneration", "report_withdrawal"},
            {record["control_domain"] for record in records},
        )
        for record in records:
            with self.subTest(domain=record["control_domain"]):
                self.assertEqual(
                    self.module.P3_PASS_RESULT, record["rollback_target_result"]
                )
                self.assertTrue(
                    record["business_line_whitebox_confirmation_required"]
                )
                self.assertTrue(record["human_confirmation_required"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_report_regeneration_performed"])
                self.assertFalse(record["actual_report_withdrawal_performed"])
                self.assertFalse(record["persistent_state_write_performed"])

    def test_invalid_or_tampered_phase3_output_fails_closed(self) -> None:
        invalid = self.module.build_external_augmentation_opinion_phase4_delivery_report(
            lambda: None
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", invalid["failure_state"])
        self.assertEqual("IDS-STAGE106-P4-GATE", invalid["next_gate"])

        shape_mismatch = self.module.build_external_augmentation_opinion_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(shape_mismatch["valid"])
        self.assertEqual(
            "PHASE3_CONTROL_SHAPE_MISMATCH", shape_mismatch["failure_state"]
        )

        def replay_with(mutator):
            result = copy.deepcopy(self.phase3_report)
            mutator(result)
            return self.module.build_external_augmentation_opinion_phase4_delivery_report(
                lambda: result
            )

        binding = replay_with(
            lambda result: result["scenario_results"][1].update(
                {
                    "evidence_id_ref": result["scenario_results"][0][
                        "evidence_id_ref"
                    ]
                }
            )
        )
        external = replay_with(
            lambda result: result["scenario_results"][2].update(
                {"external_augmentation_may_not_be_internal_project_evidence": False}
            )
        )
        impact = replay_with(
            lambda result: result["scenario_results"][4].update(
                {"report_status_impact_state": "CONTROL_STATUS_IMPACT_MISSING"}
            )
        )
        confirmation = replay_with(
            lambda result: result["scenario_results"][0].update(
                {
                    "human_confirmation_state": (
                        "CONTROL_WHITEBOX_HUMAN_CONFIRMATION_REQUIRED_NOT_RECORDED"
                    )
                }
            )
        )
        runtime = replay_with(
            lambda result: result["runtime_boundary"].update(
                {"model_call_performed": True}
            )
        )
        opaque = replay_with(
            lambda result: result["scenario_results"][0].update(
                {"report_id_ref": "uncontrolled-reference"}
            )
        )
        expected = (
            (binding, "CRITICAL_CONCLUSION_BINDING_MISSING"),
            (external, "EXTERNAL_AUGMENTATION_SOURCE_SEPARATION_MISSING"),
            (impact, "REPORT_STATUS_IMPACT_CONTROL_MISSING"),
            (confirmation, "WHITEBOX_CONFIRMATION_GATE_MISSING"),
            (runtime, "PHASE3_RUNTIME_SIGNAL_DETECTED"),
            (opaque, "CONTROL_REFERENCE_NOT_OPAQUE"),
        )
        for failed_report, failure_state in (
            (invalid, "PHASE3_CONTROL_OUTPUT_INVALID"),
            (shape_mismatch, "PHASE3_CONTROL_SHAPE_MISMATCH"),
            *expected,
        ):
            with self.subTest(failure=failure_state):
                self.assertEqual(failure_state, failed_report["failure_state"])
                for group_name, _ in self.module.DELIVERY_GROUPS:
                    self.assertEqual([], failed_report[group_name])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed_report.items()
                        if key.startswith("actual_") and key.endswith("_count")
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in failed_report["runtime_boundary"].values()
                    )
                )

    def test_delivery_boundary_validators_detect_write_review_and_template_drift(self) -> None:
        template_drift = copy.deepcopy(self.report)
        template_drift["report_template_and_whitebox_confirmation_control_records"][0][
            "actual_human_confirmation_performed"
        ] = True
        self.assertFalse(
            self.module._template_and_confirmation_is_valid(
                template_drift,
                self.phase3_report["scenario_results"],
            )
        )

        write_drift = copy.deepcopy(self.report)
        write_drift["report_sample_control_records"][0][
            "actual_report_sample_rendered"
        ] = True
        self.assertEqual(
            "ACTUAL_REPORT_OR_SNAPSHOT_WRITE_SIGNAL_DETECTED",
            self.module._delivery_execution_boundary_failure(write_drift),
        )

        quality_drift = copy.deepcopy(self.report)
        quality_drift["report_quality_score_control_records"][0][
            "actual_report_quality_score_calculated"
        ] = True
        self.assertEqual(
            "ACTUAL_REPORT_STATUS_OR_QUALITY_CHANGE_SIGNAL_DETECTED",
            self.module._delivery_execution_boundary_failure(quality_drift),
        )

        review_drift = copy.deepcopy(self.report)
        review_drift["stage106_review_started"] = True
        self.assertEqual(
            "STAGE106_REVIEW_STARTED",
            self.module._delivery_execution_boundary_failure(review_drift),
        )
        self.assertEqual(
            388,
            sum(
                len(self.report[group_name]) * len(fields)
                for group_name, fields in self.module.DELIVERY_GROUPS
            ),
        )

    def test_scope_runtime_and_current_governance_projection_are_exact(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "报告样例",
            "报告快照",
            "报告质量评分",
            "影响分析",
            "报告模板限制",
            "业务线白箱人工确认",
            "报告重新生成和撤回",
            "模型 Token",
            "IDS-STAGE106-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertFalse(self.report["second_authoritative_source_created"])
        self.assertFalse(self.report["persistent_record_created"])
        self.assertFalse(self.report["stage106_review_started"])
        for field, value in self.report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        for field, value in self.report["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        for section in (
            "runtime_boundary",
            "protected_surface_boundary",
            "future_runtime_prerequisite_contract",
        ):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P1",
            "IDS-V0_1-STAGE106-P1",
            "IDS-STAGE106-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P2",
            "IDS-V0_1-STAGE106-P2",
            "IDS-STAGE106-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P3",
            "IDS-V0_1-STAGE106-P3",
            "IDS-STAGE106-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P4",
            "IDS-V0_1-STAGE106-P4",
            "IDS-STAGE106-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-REVIEW",
            "IDS-V0_1-STAGE106-REVIEW",
            "IDS-STAGE107-P1-GATE",
        )
        stage107_phase1_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P1",
            "IDS-V0_1-STAGE107-P1",
            "IDS-STAGE107-P2-GATE",
        )
        stage107_phase2_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P2",
            "IDS-V0_1-STAGE107-P2",
            "IDS-STAGE107-P3-GATE",
        )
        stage107_phase3_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P3",
            "IDS-V0_1-STAGE107-P3",
            "IDS-STAGE107-P4-GATE",
        )
        stage107_phase4_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P4",
            "IDS-V0_1-STAGE107-P4",
            "IDS-STAGE107-REVIEW-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current, phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current == phase4_current:
            self.assertTrue(is_current_projection)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual(self.module.PASS_RESULT, receipt["result"])
            self.assertEqual("IDS-STAGE106-REVIEW-GATE", receipt["next_gate"])
            delivery = receipt["delivery_evidence"]
            self.assertEqual(5, delivery["report_sample_control_record_count"])
            self.assertEqual(5, delivery["report_snapshot_control_record_count"])
            self.assertEqual(5, delivery["report_quality_score_control_record_count"])
            self.assertEqual(5, delivery["report_impact_analysis_control_record_count"])
            self.assertEqual(
                5,
                delivery[
                    "report_template_and_whitebox_confirmation_control_record_count"
                ],
            )
            self.assertEqual(
                2, delivery["regeneration_and_withdrawal_control_record_count"]
            )
            self.assertEqual(388, delivery["delivery_field_check_count"])
            self.assertTrue(
                all(value == 0 for value in receipt["runtime_counts"].values())
            )
            self.assertTrue(
                all(value is False for value in receipt["runtime_flags"].values())
            )
            validation = receipt["validation"]
            self.assertEqual(8, validation["focused_delivery_test_count"])
            self.assertEqual(
                31, validation["explicit_predecessor_focused_test_count"]
            )
            self.assertEqual(
                884, validation["historical_whitebox_chain_test_count"]
            )
            for field in (
                "full_whitebox_validation_recorded",
                "stage005_governance_valid",
                "batch041_050_review_valid",
                "batch051_060_review_valid",
                "document_budget_valid",
                "blocker_stop_valid",
                "dual_plane_valid",
                "final_validation_recorded",
            ):
                with self.subTest(validation_field=field):
                    self.assertTrue(validation[field])
            self.assertEqual(7, validation["human_rendered_file_count"])
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            self.assertEqual(
                "P1/P2/P3/P4 控制工件已完成",
                acceptance_by_id["ACC-STAGE-106"],
            )
            for acceptance_id in (
                "ACC-STAGE106-P4-01",
                "ACC-STAGE106-P4-02",
                "ACC-STAGE106-P4-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual(
                "已遵守", acceptance_by_id["ACC-STAGE106-P4-04"]
            )
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE106-P4-20260826-001", event_ids)
        elif is_current_projection:
            self.assertTrue(is_current_projection)
        else:
            self.assertIn(current, {phase1_current, phase2_current, phase3_current})
            self.assertFalse(is_current_projection)


if __name__ == "__main__":
    unittest.main()
