import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_contract.json"
)
PHASE2_CONTRACT = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_scenarios_contract.json"
)
PHASE3_SCENARIOS = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_scenarios.py"
)
CLOSEOUT = BASE / "STAGE061_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_delivery_contract.json"
)
DELIVERY = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_delivery.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage061-p4-local.json"

EXPECTED_SCENARIO_IDS = [
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
]


class Stage061StructuredDataQualityPhase4DeliveryTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage061_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_structured_data_quality_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE3_CONTRACT,
            PHASE3_SCENARIOS,
            CLOSEOUT,
            CONTRACT,
            DELIVERY,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_zero_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage061.structured_data_quality.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE061-P4", contract["task_id"])
        self.assertTrue(contract["delivery_evidence_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE061-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["ownership_boundary"]
            ["stage061_phase1_phase2_phase3_reused_as_reference_only"]
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["ovh_deployment_performed"])

    def test_delivery_report_derives_six_control_samples(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE061-REVIEW-GATE", report["next_gate"])
        self.assertEqual(6, len(report["delivery_samples"]))
        self.assertEqual(
            EXPECTED_SCENARIO_IDS,
            [item["scenario_id"] for item in report["delivery_samples"]],
        )

    def test_delivery_samples_keep_control_references_without_real_outputs(self):
        for sample in self._report()["delivery_samples"]:
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_STRUCTURED_DATA_QUALITY_SAMPLE_NOT_REAL_QUALITY_RESULT",
                    sample["sample_kind"],
                )
                self.assertTrue(sample["control_metadata_only"])
                self.assertTrue(
                    all(
                        ":control:" in sample[field]
                        for field in (
                            "quality_request_ref",
                            "referenced_quality_result_ref",
                            "source_document_ref",
                            "workbook_ref",
                            "worksheet_ref",
                            "header_row_ref",
                            "row_range_ref",
                            "column_range_ref",
                            "evidence_ref",
                        )
                    )
                )
                self.assertFalse(sample["source_content_retained"])
                self.assertFalse(sample["typed_value_retained"])
                self.assertFalse(sample["actual_quality_result_created"])
                self.assertFalse(sample["actual_structured_fact_created"])

    def test_field_inference_report_keeps_six_reference_labels_only(self):
        report = self._report()["field_inference_report"]
        self.assertEqual(
            "CONTROLLED_STRUCTURED_DATA_QUALITY_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE",
            report["report_kind"],
        )
        self.assertEqual(6, report["quality_result_candidate_pool_count"])
        self.assertEqual(6, report["referenced_field_label_count"])
        self.assertEqual(6, report["scenario_reference_count"])
        self.assertTrue(report["control_reference_only"])
        self.assertFalse(report["actual_field_mapping_created"])
        self.assertFalse(report["real_table_schema_inference_performed"])
        self.assertFalse(report["real_quality_validation_performed"])

    def test_quality_test_results_remain_control_only(self):
        results = self._report()["quality_test_results"]
        self.assertEqual(
            "CONTROLLED_STRUCTURED_DATA_QUALITY_TEST_RESULT_NOT_REAL_QUALITY_VALIDATION",
            results["report_kind"],
        )
        self.assertEqual(6, results["scenario_count"])
        self.assertEqual(6, results["passed_scenario_count"])
        self.assertEqual(6, results["explicit_disposition_count"])
        self.assertEqual(0, results["silent_drop_count"])
        self.assertTrue(results["all_taskpack_exception_categories_covered"])
        self.assertTrue(results["all_quality_states_unassessed"])
        self.assertTrue(results["all_statistical_conclusions_blocked"])
        self.assertFalse(results["actual_table_quality_validation_performed"])

    def test_unrecognized_structure_requires_human_handling(self):
        records = {
            item["scenario_id"]: item
            for item in self._report()["unrecognized_structure_and_human_handling"]
        }
        self.assertEqual(6, len(records))
        merged = records["merged-cells-control-human-handling"]
        self.assertEqual(
            "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
            merged["quality_disposition"],
        )
        self.assertTrue(merged["human_handling_required"])
        self.assertIn("人工", merged["recommendation_zh"])
        self.assertFalse(merged["actual_unrecognized_table_structure_observed"])
        self.assertFalse(merged["automatic_structure_resolution_performed"])

    def test_reparse_and_fact_rollback_remain_non_operational(self):
        instructions = self._report()["reparse_and_fact_rollback_instructions"]
        self.assertEqual(
            "STRUCTURED_DATA_REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY",
            instructions["record_kind"],
        )
        self.assertEqual(
            "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            instructions["return_to"],
        )
        self.assertTrue(instructions["in_memory_control_replay_only"])
        self.assertFalse(instructions["actual_file_reparse_performed"])
        self.assertFalse(instructions["actual_fact_rollback_performed"])
        self.assertFalse(instructions["actual_quality_result_rollback_performed"])
        self.assertFalse(instructions["source_or_raw_data_change_allowed"])
        self.assertFalse(instructions["database_or_persistent_state_change_allowed"])

    def test_chinese_prompts_require_human_confirmation_without_auto_action(self):
        prompts = self._report()["human_confirmation_prompts_zh"]
        self.assertEqual(3, len(prompts))
        for prompt in prompts:
            with self.subTest(prompt=prompt["prompt_id"]):
                self.assertIn("请", prompt["text"])
                self.assertFalse(prompt["automatic_confirmation_performed"])

    def test_all_runtime_side_effects_remain_false(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "field_completeness_evaluation_performed",
            "unit_consistency_evaluation_performed",
            "date_validity_evaluation_performed",
            "primary_key_duplication_evaluation_performed",
            "outlier_evaluation_performed",
            "numeric_statistic_computation_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "actual_file_reparse_performed",
            "actual_fact_rollback_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "whole_stage_review_performed",
            "batch_review_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_fails_closed(self):
        report = self._module().build_structured_data_quality_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_STRUCTURED_DATA_QUALITY_DELIVERY_EVIDENCE", report["result"])
        self.assertEqual([], report["delivery_samples"])
        self.assertEqual([], report["unrecognized_structure_and_human_handling"])

    def test_closeout_explains_chinese_boundary_and_next_gate(self):
        closeout = CLOSEOUT.read_text(encoding="utf-8")
        for expected in (
            "metadata-only",
            "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE061-REVIEW-GATE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, closeout)

    def test_governance_and_local_run_preserve_phase4(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage061_completed_reviewed_local"'),
            (batch, "stage061_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE061-REVIEW"'),
            (batch, 'next_gate: "IDS-STAGE062-P1-GATE"'),
            (batch, "structured_data_quality_delivery_evidence_derived: true"),
            (batch, "xlsx_or_csv_parse_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE061"'),
            (roadmap, 'current_phase_id: "IDS-STAGE061-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE062-P1-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE061", "IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073"))
        self.assertIn(
            (status["phase"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE061-REVIEW", "IDS-STAGE062-P1-GATE"),
                ("IDS-V0_1-STAGE062-P1", "IDS-STAGE062-P2-GATE"),
                ("IDS-V0_1-STAGE062-P2", "IDS-STAGE062-P3-GATE"),
                ("IDS-V0_1-STAGE062-P3", "IDS-STAGE062-P4-GATE"),
                ("IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW-GATE"),
                ("IDS-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
                ("IDS-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
                ("IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
                ("IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
                ("IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
                ("IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
                ("IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
                ("IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE061-REVIEW",
                "IDS-V0_1-STAGE062-P1",
                "IDS-V0_1-STAGE062-P2",
                "IDS-V0_1-STAGE062-P3",
                "IDS-V0_1-STAGE062-P4",
                "IDS-V0_1-STAGE062-REVIEW",
                "IDS-V0_1-STAGE063-P1",
                "IDS-V0_1-STAGE063-P2",
                "IDS-V0_1-STAGE063-P3",
                "IDS-V0_1-STAGE063-P4",
                "IDS-V0_1-STAGE063-REVIEW",
                "IDS-V0_1-STAGE064-P1",
                "IDS-V0_1-STAGE064-P2",
                "IDS-V0_1-STAGE064-P3",
                "IDS-V0_1-STAGE064-P4",
                "IDS-V0_1-STAGE064-REVIEW",
                "IDS-V0_1-STAGE065-P1",
                "IDS-V0_1-STAGE065-P2",
                "IDS-V0_1-STAGE065-P3",
                "IDS-V0_1-STAGE065-P4",
                "IDS-V0_1-STAGE065-REVIEW",
                "IDS-V0_1-STAGE066-P1",
                "IDS-V0_1-STAGE066-P2",
                "IDS-V0_1-STAGE066-P3",
                "IDS-V0_1-STAGE066-P4",
                "IDS-V0_1-STAGE066-REVIEW",
                "IDS-V0_1-STAGE067-P1",
                "IDS-V0_1-STAGE067-P2",
                "IDS-V0_1-STAGE067-P3",
                "IDS-V0_1-STAGE067-P4",
                "IDS-V0_1-STAGE067-REVIEW",
                "IDS-V0_1-STAGE068-P1",
                "IDS-V0_1-STAGE068-P2",
                "IDS-V0_1-STAGE068-P3",
                "IDS-V0_1-STAGE068-P4",
            "IDS-V0_1-STAGE068-REVIEW",
                "IDS-V0_1-STAGE069-P1",
                "IDS-V0_1-STAGE069-P2",
                "IDS-V0_1-STAGE069-P3",
                "IDS-V0_1-STAGE069-P4",
                "IDS-V0_1-STAGE069-REVIEW",

                "IDS-V0_1-STAGE070-P1","IDS-V0_1-STAGE070-P2","IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1",),
        )
        self.assertIn(status["next_gate"], plan["stop_condition"])
        self.assertEqual("IDS-V0_1-STAGE061-P4", run["task_id"])
        self.assertEqual("IDS-STAGE061-REVIEW-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["whole_stage_review_performed"])
        self.assertTrue(
            {
                "ACC-STAGE061-P4-01",
                "ACC-STAGE061-P4-02",
                "ACC-STAGE061-P4-03",
                "ACC-STAGE061-P4-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE061-P4-20260814-001"
        )
        self.assertEqual("IDS-V0_1-STAGE061-P4", event["task_id"])
        self.assertTrue(
            any(
                item.endswith("STAGE061_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_CLOSEOUT.md")
                for item in event["changed_files"]
            )
        )


if __name__ == "__main__":
    unittest.main()
