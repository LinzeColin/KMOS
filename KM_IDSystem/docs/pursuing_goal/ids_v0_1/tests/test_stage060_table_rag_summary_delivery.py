import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage060_table_rag_summary_contract.json"
)
PHASE2_CONTRACT = (
    BASE / "structured_table_facts" / "stage060_table_rag_summary_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage060_table_rag_summary_quality_scenarios_contract.json"
)
PHASE3_SCENARIOS = (
    BASE
    / "structured_table_facts"
    / "stage060_table_rag_summary_quality_scenarios.py"
)
CLOSEOUT = BASE / "STAGE060_PHASE4_TABLE_RAG_SUMMARY_DELIVERY_CLOSEOUT.md"
CONTRACT = BASE / "structured_table_facts" / "stage060_table_rag_summary_delivery_contract.json"
DELIVERY = BASE / "structured_table_facts" / "stage060_table_rag_summary_delivery.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage060-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"

EXPECTED_SCENARIO_IDS = [
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
]


class Stage060TableRagSummaryPhase4DeliveryTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage060_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_table_rag_summary_phase4_delivery_report()
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
            RUN,
            STATUS,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_zero_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage060.table_rag_summary.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE060-P4", contract["task_id"])
        self.assertTrue(contract["delivery_evidence_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE060-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertEqual(0, contract["delivery_input_boundary"]["actual_table_count"])
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_allowed"])
        self.assertFalse(
            contract["runtime_boundary"]["model_token_consumption_allowed"]
        )

    def test_delivery_samples_are_exactly_six_control_metadata_records(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_TABLE_RAG_SUMMARY_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        samples = report["delivery_samples"]
        self.assertEqual(6, len(samples))
        self.assertEqual(EXPECTED_SCENARIO_IDS, [item["scenario_id"] for item in samples])
        for sample in samples:
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_TABLE_FACT_REFERENCE_SAMPLE_NOT_REAL_STRUCTURED_FACT",
                    sample["sample_kind"],
                )
                self.assertTrue(sample["control_metadata_only"])
                self.assertTrue(sample["referenced_rag_summary_id"])
                self.assertTrue(sample["referenced_fact_id"])
                self.assertFalse(sample["source_content_retained"])
                self.assertFalse(sample["summary_text_retained"])
                self.assertFalse(sample["typed_value_retained"])
                self.assertFalse(sample["actual_structured_fact_created"])
                self.assertFalse(sample["actual_table_fact_sample_created"])
                self.assertFalse(sample["high_trust_direct_entry_allowed"])

    def test_field_inference_report_is_control_reference_not_real_field_inference(self):
        inference = self._report()["field_inference_report"]
        self.assertEqual(
            "CONTROLLED_TABLE_RAG_SUMMARY_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE",
            inference["report_kind"],
        )
        self.assertEqual(2, inference["rag_summary_candidate_pool_count"])
        self.assertEqual(6, inference["referenced_field_label_count"])
        self.assertEqual(6, inference["scenario_reference_count"])
        self.assertTrue(inference["control_reference_only"])
        self.assertFalse(inference["actual_field_mapping_created"])
        self.assertFalse(inference["real_table_schema_inference_performed"])
        self.assertFalse(inference["real_field_identification_performed"])
        self.assertFalse(inference["real_structured_fact_extraction_performed"])

    def test_quality_results_preserve_all_explicit_taskpack_exceptions(self):
        quality = self._report()["quality_test_results"]
        self.assertEqual(
            "CONTROLLED_TABLE_RAG_SUMMARY_QUALITY_TEST_RESULT_NOT_REAL_TABLE_VALIDATION",
            quality["report_kind"],
        )
        self.assertEqual(6, quality["scenario_count"])
        self.assertEqual(6, quality["passed_scenario_count"])
        self.assertEqual(6, quality["explicit_disposition_count"])
        self.assertEqual(0, quality["silent_drop_count"])
        self.assertTrue(quality["all_taskpack_exception_categories_covered"])
        self.assertFalse(quality["actual_table_quality_validation_performed"])
        self.assertFalse(quality["actual_source_file_traceability_validated"])

    def test_unrecognized_structure_and_human_handling_are_explicit(self):
        records = self._report()["unrecognized_structure_and_human_handling"]
        self.assertEqual(6, len(records))
        self.assertEqual(EXPECTED_SCENARIO_IDS, [item["scenario_id"] for item in records])
        merged = next(
            item
            for item in records
            if item["scenario_id"] == "merged-cells-control-human-handling"
        )
        self.assertEqual(
            "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
            merged["quality_disposition"],
        )
        self.assertTrue(merged["human_handling_required"])
        self.assertIn("人工", merged["recommendation_zh"])
        self.assertFalse(merged["actual_unrecognized_table_structure_observed"])

    def test_table_reparse_and_fact_rollback_remain_non_operational(self):
        instructions = self._report()["reparse_and_fact_rollback_instructions"]
        self.assertEqual(
            "TABLE_REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY",
            instructions["record_kind"],
        )
        self.assertEqual(
            "PHASE3_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            instructions["return_to"],
        )
        self.assertTrue(instructions["in_memory_control_replay_only"])
        self.assertFalse(instructions["actual_file_reparse_performed"])
        self.assertFalse(instructions["actual_fact_rollback_performed"])
        self.assertFalse(instructions["actual_fact_store_present"])
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
            "table_summary_generation_performed",
            "rag_summary_generation_performed",
            "merged_cell_resolution_performed",
            "unit_normalization_performed",
            "date_normalization_performed",
            "outlier_evaluation_performed",
            "duplicate_row_evaluation_performed",
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
        report = self._module().build_table_rag_summary_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_TABLE_RAG_SUMMARY_DELIVERY_EVIDENCE", report["result"])
        self.assertEqual([], report["delivery_samples"])
        self.assertEqual([], report["unrecognized_structure_and_human_handling"])

    def test_closeout_explains_chinese_boundary_and_next_gate(self):
        closeout = CLOSEOUT.read_text(encoding="utf-8")
        for expected in (
            "metadata-only",
            "PHASE3_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE060-REVIEW-GATE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, closeout)

    def test_governance_and_local_run_preserve_phase4(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage060_phase4_completed_review_pending"'),
            (batch, "stage060_phase4_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE060-P4"'),
            (batch, 'next_gate: "IDS-STAGE060-REVIEW-GATE"'),
            (batch, "table_rag_summary_delivery_evidence_derived: true"),
            (batch, "xlsx_or_csv_parse_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE060"'),
            (roadmap, 'current_phase_id: "IDS-STAGE060-P4"'),
            (roadmap, 'next_gate_id: "IDS-STAGE060-REVIEW-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE060",
                    "IDS-V0_1-STAGE060-REVIEW",
                    "IDS-V0_1-STAGE060-REVIEW",
                    "IDS-V0_1-BATCH-051-060-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-STAGE066-P2-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-STAGE066-P3-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-STAGE066-P4-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-STAGE066-REVIEW-GATE",
                ),
                ("IDS-STAGE066", "IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-STAGE067", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE060-P4", run["task_id"])
        self.assertEqual("IDS-STAGE060-REVIEW-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["whole_stage_review_performed"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE060-P4-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE060-P4", event["task_id"])
        self.assertTrue(
            any(
                item.endswith("STAGE060_PHASE4_TABLE_RAG_SUMMARY_DELIVERY_CLOSEOUT.md")
                for item in event["changed_files"]
            )
        )


if __name__ == "__main__":
    unittest.main()
