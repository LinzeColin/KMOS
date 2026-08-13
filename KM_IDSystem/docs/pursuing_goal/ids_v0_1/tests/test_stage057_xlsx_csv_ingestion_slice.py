import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_contract.json"
)
PHASE2 = BASE / "STAGE057_PHASE2_XLSX_CSV_INGESTION_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage057-p2-local.json"


class Stage057XlsxCsvIngestionPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage057_xlsx_csv_ingestion_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "table_input_records": [
                {
                    "source_identity_ref": "source:control:stage057-p2",
                    "source_document_ref": "source-document:control:stage057-p2:1",
                    "file_format": "XLSX",
                    "workbook_ref": "workbook:control:stage057-p2:1",
                    "worksheet_ref": "worksheet:control:stage057-p2:1",
                    "row_range_ref": "row-range:control:stage057-p2:1",
                    "column_range_ref": "column-range:control:stage057-p2:1",
                    "record_type": "PRODUCTION_RECORD",
                    "schema_profile_ref": "schema-profile:control:stage057-p2:production",
                    "fact_type": "PRODUCTION_MEASUREMENT",
                    "evidence_ref": "evidence:control:stage057-p2:1",
                    "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
                },
                {
                    "source_identity_ref": "source:control:stage057-p2",
                    "source_document_ref": "source-document:control:stage057-p2:2",
                    "file_format": "CSV",
                    "workbook_ref": "workbook:control:stage057-p2:csv-reference",
                    "worksheet_ref": "worksheet:control:stage057-p2:2",
                    "row_range_ref": "row-range:control:stage057-p2:2",
                    "column_range_ref": "column-range:control:stage057-p2:2",
                    "record_type": "QUALITY_INSPECTION_RECORD",
                    "schema_profile_ref": "schema-profile:control:stage057-p2:quality",
                    "fact_type": "QUALITY_RESULT",
                    "evidence_ref": "evidence:control:stage057-p2:2",
                    "ingestion_state": "REFERENCE_ONLY_READY_FOR_CONTROL_SCHEMA_PROJECTION",
                },
            ]
        }

    def test_phase2_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2,
            CONTRACT,
            SLICE,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_is_executable_but_real_table_and_production_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage057.xlsx_csv_ingestion.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE057-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE057-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(12, contract["reference_only_table_input_contract"]["field_count"])
        self.assertEqual(2, contract["reference_only_table_input_contract"]["control_record_count"])
        self.assertEqual(19, contract["structured_fact_candidate_contract"]["field_count"])
        self.assertTrue(
            contract["structured_fact_candidate_contract"]
            ["in_memory_candidate_projection_created"]
        )
        self.assertFalse(
            contract["structured_fact_candidate_contract"]
            ["actual_structured_fact_created"]
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_schema_profiles_identify_only_p1_semantic_field_references(self):
        result = self._slice().execute_xlsx_csv_ingestion_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_SCHEMA_AND_FACT_CANDIDATE_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["table_input_record_count"])
        self.assertEqual(2, result["schema_profile_candidate_count"])
        self.assertTrue(result["control_schema_profile_inference_performed"])
        self.assertTrue(result["control_field_identification_performed"])
        self.assertEqual(
            [
                "record_date",
                "equipment_ref",
                "material_ref",
                "measurement_value",
                "unit_ref",
                "fact_type",
            ],
            result["schema_profile_candidates"][0]["identified_field_names"],
        )
        self.assertEqual(
            ["record_date", "equipment_ref", "quality_result", "fact_type"],
            result["schema_profile_candidates"][1]["identified_field_names"],
        )
        self.assertFalse(result["source_body_or_cell_content_retained"])

    def test_fact_candidates_preserve_all_future_fields_and_source_location_references(self):
        result = self._slice().execute_xlsx_csv_ingestion_control_slice(
            self._control()
        )
        self.assertEqual(10, result["structured_fact_candidate_count"])
        self.assertEqual(10, result["source_location_binding_candidate_count"])
        self.assertTrue(result["source_location_references_preserved"])
        candidate = result["structured_fact_candidates"][0]
        self.assertEqual(
            {
                "fact_id",
                "source_identity_ref",
                "source_document_ref",
                "file_format",
                "worksheet_ref",
                "row_range_ref",
                "column_range_ref",
                "field_name",
                "field_type",
                "typed_value",
                "unit_ref",
                "record_date",
                "equipment_ref",
                "material_ref",
                "quality_result",
                "fact_type",
                "quality_state",
                "evidence_ref",
                "rag_summary_eligibility",
            },
            set(candidate),
        )
        self.assertIsNone(candidate["typed_value"])
        self.assertEqual("UNASSESSED", candidate["quality_state"])
        self.assertEqual(
            "source-document:control:stage057-p2:1", candidate["source_document_ref"]
        )
        self.assertFalse(result["actual_structured_fact_created"])

    def test_rag_summary_candidates_are_separate_from_facts_and_numeric_authority(self):
        result = self._slice().execute_xlsx_csv_ingestion_control_slice(
            self._control()
        )
        self.assertEqual(2, result["rag_summary_candidate_count"])
        self.assertTrue(result["rag_summary_candidates_separated_from_facts"])
        self.assertEqual(1, result["numeric_field_candidate_count"])
        summary = result["rag_summary_candidates"][0]
        self.assertEqual(
            "METADATA_ONLY_SUMMARY_CANDIDATE_REQUIRES_FACT_REFERENCES",
            summary["summary_mode"],
        )
        self.assertTrue(summary["fact_candidate_references_required"])
        self.assertFalse(summary["summary_can_replace_structured_fact"])
        self.assertFalse(summary["summary_can_become_numeric_statistical_evidence"])
        self.assertFalse(result["numeric_statistic_computation_performed"])
        self.assertFalse(result["actual_rag_summary_created"])

    def test_invalid_control_rejects_without_returning_reference_or_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_xlsx_csv_ingestion_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["schema_profile_candidates"])
        self.assertEqual([], result["structured_fact_candidates"])
        self.assertEqual([], result["rag_summary_candidates"])

    def test_real_data_fact_storage_and_external_actions_remain_disabled(self):
        result = self._slice().execute_xlsx_csv_ingestion_control_slice(
            self._control()
        )
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "real_table_schema_inference_performed",
            "real_field_identification_performed",
            "real_structured_fact_extraction_performed",
            "actual_structured_fact_created",
            "actual_structured_fact_persisted",
            "actual_typed_value_retained",
            "actual_source_location_binding_created",
            "actual_evidence_record_created",
            "numeric_statistic_computation_performed",
            "database_connection_performed",
            "database_schema_migration_performed",
            "structured_fact_write_performed",
            "rag_summary_write_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_phase2_governance_projection_and_evidence_remain_historical_or_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage057_phase2_completed"'),
            (batch, "stage057_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE057-P2"'),
            (batch, 'next_gate: "IDS-STAGE057-P3-GATE"'),
            (batch, "phase2_started: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE057"'),
            (roadmap, 'current_phase_id: "IDS-STAGE057-P2"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE057-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE057-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE057", "IDS-STAGE058", "IDS-STAGE059"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE057-P2",
                "IDS-V0_1-STAGE057-P3",
                "IDS-V0_1-STAGE057-P4",
                "IDS-V0_1-STAGE057-REVIEW",
                "IDS-V0_1-STAGE058-P1",
            "IDS-V0_1-STAGE058-P2",
            "IDS-V0_1-STAGE058-P3",
            "IDS-V0_1-STAGE058-P4",
            "IDS-V0_1-STAGE058-REVIEW",
            "IDS-V0_1-STAGE059-P1",
            "IDS-V0_1-STAGE059-P2",
            "IDS-V0_1-STAGE059-P3",
            "IDS-V0_1-STAGE059-P4",
            ),
        )
        self.assertIn(
            status["next_gate"],
            (
                "IDS-STAGE057-P3-GATE",
                "IDS-STAGE057-P4-GATE",
                "IDS-STAGE057-REVIEW-GATE",
                "IDS-STAGE058-P1-GATE",
                "IDS-STAGE058-P2-GATE",
                "IDS-STAGE058-P3-GATE",
                "IDS-STAGE058-P4-GATE",
                "IDS-STAGE058-REVIEW-GATE",
                "IDS-STAGE059-P1-GATE",
                "IDS-STAGE059-P2-GATE",
                "IDS-STAGE059-P3-GATE",
            "IDS-STAGE059-P4-GATE",
            "IDS-STAGE059-REVIEW-GATE",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE2_XLSX_CSV_INGESTION_CONTROL_SLICE_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["observed_work"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(run["observed_work"]["structured_fact_write_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase3_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE057-P2-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE057-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-057"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE057-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
