import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE2_CONTRACT = (
    BASE / "structured_table_facts" / "stage058_table_schema_inference_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "structured_table_facts" / "stage058_table_schema_inference_slice.py"
)
PHASE3 = BASE / "STAGE058_PHASE3_TABLE_SCHEMA_INFERENCE_QUALITY_SCENARIOS.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage058_table_schema_inference_quality_scenarios_contract.json"
)
MODULE = (
    BASE
    / "structured_table_facts"
    / "stage058_table_schema_inference_quality_scenarios.py"
)
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage058-p3-local.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"

EXPECTED_SCENARIOS = [
    "empty-table-control-explicit-closed",
    "merged-cells-control-human-handling",
    "unit-confusion-control-human-handling",
    "date-format-variation-control-human-handling",
    "outlier-control-numeric-block",
    "duplicate-row-control-human-handling",
]


class Stage058TableSchemaInferencePhase3Tests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location(
            "stage058_table_schema_inference_quality_scenarios", MODULE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        return self._module().build_table_schema_inference_phase3_report()

    def test_phase3_artifacts_exist(self):
        for artifact in (PHASE2_CONTRACT, PHASE2_MODULE, PHASE3, CONTRACT, MODULE):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_is_executable_but_real_input_and_runtime_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage058.table_schema_inference.phase3.quality_scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE058-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE058-P4-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["ownership_boundary"]
            ["stage058_phase2_control_slice_reused_as_reference_only"]
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

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
            "PASS_PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(11, report["unique_schema_profile_candidate_count"])
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

    def test_unit_and_date_variations_never_create_normalized_values(self):
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
        self.assertFalse(self._report()["actual_schema_profile_created"])

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

    def test_control_references_remain_traceable_without_real_source_claim(self):
        report = self._report()
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["source_location_reference_preserved"])
                self.assertTrue(item["referenced_schema_profile_id"])
                self.assertTrue(
                    item["referenced_candidate_column_handle"].startswith(
                        "column-handle:control:"
                    )
                )
                self.assertTrue(item["control_scenario_metadata_only"])
        self.assertEqual(6, report["source_location_reference_check_count"])
        self.assertTrue(report["control_source_location_traceability_preserved"])
        self.assertFalse(report["actual_source_file_traceability_validated"])
        self.assertFalse(report["actual_evidence_record_created"])

    def test_report_has_no_real_table_payload_or_actual_fact_creation_claim(self):
        report = self._report()
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertFalse(item["real_table_content_evaluated"])
                self.assertFalse(item["actual_source_file_traceability_validated"])
                self.assertFalse(item["actual_evidence_record_created"])
                self.assertFalse(item["actual_schema_profile_created"])
                self.assertFalse(item["actual_structured_fact_created"])
        self.assertFalse(report["actual_schema_profile_created"])
        self.assertFalse(report["actual_field_mapping_created"])
        self.assertFalse(report["actual_structured_fact_created"])
        self.assertFalse(report["actual_rag_summary_created"])

    def test_all_external_and_persistent_actions_remain_disabled(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "real_table_schema_inference_performed",
            "real_field_identification_performed",
            "real_structured_fact_extraction_performed",
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
        report = self._module().build_table_schema_inference_phase3_report(lambda _: {})
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS",
            report["result"],
        )
        self.assertEqual(0, report["passed_scenario_count"])

    def test_phase3_governance_projection_and_evidence_are_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage058_phase3_completed"'),
            (batch, "stage058_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE058-P3"'),
            (batch, 'next_gate: "IDS-STAGE058-P4-GATE"'),
            (batch, "phase3_started: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE058"'),
            (roadmap, 'current_phase_id: "IDS-STAGE058-P3"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE058-P3"'),
            (roadmap, 'next_gate_id: "IDS-STAGE058-P4-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE058", "IDS-STAGE059", "IDS-STAGE060"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE058-P3",
                "IDS-V0_1-STAGE058-P4",
                "IDS-V0_1-STAGE058-REVIEW",
                "IDS-V0_1-STAGE059-P1",
            "IDS-V0_1-STAGE059-P2",
            "IDS-V0_1-STAGE059-P3",
            "IDS-V0_1-STAGE059-P4",
            "IDS-V0_1-STAGE059-REVIEW",
            "IDS-V0_1-STAGE060-P1", "IDS-V0_1-STAGE060-P2", "IDS-V0_1-STAGE060-P3",
            "IDS-V0_1-STAGE060-P4",
            ),
        )
        self.assertIn(
            status["next_gate"],
            (
                "IDS-STAGE058-P4-GATE",
                "IDS-STAGE058-REVIEW-GATE",
                "IDS-STAGE059-P1-GATE",
                "IDS-STAGE059-P2-GATE",
                "IDS-STAGE059-P3-GATE",
            "IDS-STAGE059-P4-GATE",
            "IDS-STAGE059-REVIEW-GATE",
            "IDS-STAGE060-P1-GATE",
            "IDS-STAGE060-P2-GATE", "IDS-STAGE060-P3-GATE", "IDS-STAGE060-P4-GATE",
            "IDS-STAGE060-REVIEW-GATE",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE058-P3", run["task_id"])
        self.assertEqual("IDS-STAGE058-P4-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase4_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE058-P3-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE058-P3", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE058-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
