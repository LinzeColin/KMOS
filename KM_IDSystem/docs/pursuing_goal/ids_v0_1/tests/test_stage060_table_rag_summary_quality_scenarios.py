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
PHASE2_MODULE = BASE / "structured_table_facts" / "stage060_table_rag_summary_slice.py"
PHASE3 = BASE / "STAGE060_PHASE3_TABLE_RAG_SUMMARY_QUALITY_SCENARIOS.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage060_table_rag_summary_quality_scenarios_contract.json"
)
MODULE = (
    BASE
    / "structured_table_facts"
    / "stage060_table_rag_summary_quality_scenarios.py"
)
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage060-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"

EXPECTED_SCENARIOS = [
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
]


class Stage060TableRagSummaryPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage060_p3", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_table_rag_summary_phase3_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE3,
            CONTRACT,
            MODULE,
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
            "ids.stage060.table_rag_summary.phase3.quality_scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE060-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE060-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertEqual(0, contract["scenario_input_boundary"]["actual_table_count"])
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(
            contract["runtime_boundary"]["model_token_consumption_performed"]
        )

    def test_scenario_catalog_covers_exact_taskpack_exceptions(self):
        contract = self._contract()
        self.assertEqual(6, contract["scenario_input_boundary"]["scenario_count"])
        self.assertEqual(
            [
                "EMPTY_TABLE_CONTROL",
                "MERGED_CELLS_CONTROL",
                "UNIT_CONFUSION_CONTROL",
                "DATE_FORMAT_VARIATION_CONTROL",
                "OUTLIER_VALUE_CONTROL",
                "DUPLICATE_ROW_CONTROL",
            ],
            contract["scenario_input_boundary"]["scenario_categories"],
        )
        self.assertTrue(
            contract["quality_scenario_validation"]
            ["all_taskpack_exception_categories_covered"]
        )
        self.assertTrue(
            contract["scenario_input_boundary"]["scenario_category_is_control_metadata"]
        )

    def test_all_controlled_quality_scenarios_are_explicit_and_passing(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE3_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(2, report["unique_rag_summary_candidate_count"])
        self.assertEqual(
            EXPECTED_SCENARIOS,
            [item["scenario_id"] for item in report["scenario_results"]],
        )

    def test_empty_table_and_merged_cells_are_explicitly_closed_to_human_handling(self):
        results = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        empty = results["empty-table-control-explicit-closed"]
        self.assertEqual(
            "REJECTED_EMPTY_TABLE_REQUIRES_HUMAN_HANDLING",
            empty["quality_disposition"],
        )
        self.assertTrue(empty["human_handling_required"])
        merged = results["merged-cells-control-human-handling"]
        self.assertEqual(
            "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
            merged["quality_disposition"],
        )
        self.assertTrue(merged["human_handling_required"])
        self.assertFalse(merged["merged_cell_resolution_performed"])

    def test_unit_and_date_variations_never_create_normalized_values_or_summary_text(self):
        results = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        unit = results["unit-confusion-control-human-handling"]
        self.assertEqual(
            "UNVERIFIED_UNIT_REQUIRES_HUMAN_HANDLING", unit["quality_disposition"]
        )
        self.assertFalse(unit["unit_normalization_performed"])
        date = results["date-format-variation-control-human-handling"]
        self.assertEqual(
            "UNVERIFIED_DATE_REQUIRES_HUMAN_HANDLING", date["quality_disposition"]
        )
        self.assertFalse(date["date_normalization_performed"])
        self.assertTrue(self._report()["all_summary_text_unset"])
        self.assertFalse(self._report()["actual_summary_text_retained"])

    def test_outlier_blocks_numeric_statistics_and_model_conclusions(self):
        item = next(
            result
            for result in self._report()["scenario_results"]
            if result["scenario_id"] == "outlier-control-numeric-block"
        )
        self.assertEqual(
            "UNVERIFIED_NUMERIC_CANDIDATE_BLOCKS_STATISTICAL_CONCLUSION",
            item["quality_disposition"],
        )
        self.assertTrue(item["unverified_numeric_blocks_statistical_conclusion"])
        self.assertFalse(item["numeric_statistical_conclusion_allowed"])
        self.assertFalse(item["model_definitive_numeric_conclusion_allowed"])
        self.assertFalse(self._report()["numeric_statistic_computation_performed"])

    def test_duplicate_row_is_explicit_and_control_references_remain_traceable(self):
        item = next(
            result
            for result in self._report()["scenario_results"]
            if result["scenario_id"] == "duplicate-row-control-human-handling"
        )
        self.assertEqual(
            "DUPLICATE_ROW_CANDIDATE_REQUIRES_HUMAN_HANDLING",
            item["quality_disposition"],
        )
        self.assertTrue(item["human_handling_required"])
        self.assertTrue(item["source_location_reference_preserved"])
        self.assertTrue(item["control_reference_only"])
        self.assertTrue(item["summary_text_unset"])
        self.assertEqual(6, self._report()["source_location_reference_check_count"])
        self.assertTrue(self._report()["control_source_location_traceability_preserved"])

    def test_report_has_no_real_table_payload_or_actual_source_traceability_claim(self):
        report = self._report()
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["control_scenario_metadata_only"])
                self.assertFalse(item["real_table_content_evaluated"])
                self.assertFalse(item["actual_source_file_traceability_validated"])
                self.assertFalse(item["actual_evidence_record_created"])
                self.assertFalse(item["actual_structured_fact_created"])
                self.assertFalse(item["actual_rag_summary_created"])
        self.assertFalse(report["actual_source_file_traceability_validated"])
        self.assertFalse(report["actual_evidence_record_created"])

    def test_all_external_and_persistent_actions_remain_disabled(self):
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
            "actual_structured_fact_created",
            "actual_evidence_record_created",
            "numeric_statistic_computation_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "phase4_started",
            "github_upload_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_phase2_result_stays_non_passing(self):
        report = self._module().build_table_rag_summary_phase3_report(lambda _: {})
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_TABLE_RAG_SUMMARY_CONTROLLED_QUALITY_SCENARIOS", report["result"]
        )
        self.assertEqual(0, report["passed_scenario_count"])

    def test_phase3_governance_projection_and_evidence_are_historical_or_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage060_phase3_completed"'),
            (batch, "stage060_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE060-P3"'),
            (batch, 'next_gate: "IDS-STAGE060-P4-GATE"'),
            (batch, "phase3_started: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE060"'),
            (roadmap, 'current_phase_id: "IDS-STAGE060-P3"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE060-P3"'),
            (roadmap, 'next_gate_id: "IDS-STAGE060-P4-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE060", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070",))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE060-P3",
                    "IDS-V0_1-STAGE060-P3",
                    "IDS-STAGE060-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE060-P4",
                    "IDS-V0_1-STAGE060-P4",
                    "IDS-STAGE060-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE060-REVIEW",
                    "IDS-V0_1-STAGE060-REVIEW",
                    "IDS-V0_1-BATCH-051-060-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-STAGE066-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-STAGE066-P3-GATE",
                ),
                (
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-STAGE066-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-STAGE066-REVIEW-GATE",
                ),
                ("IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE060-P3", run["task_id"])
        self.assertEqual("IDS-STAGE060-P4-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase4_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE060-P3-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE060-P3", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE060-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
