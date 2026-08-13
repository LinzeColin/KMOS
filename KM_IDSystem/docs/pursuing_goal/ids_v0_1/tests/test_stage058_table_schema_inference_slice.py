import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage058_table_schema_inference_contract.json"
)
PHASE2 = BASE / "STAGE058_PHASE2_TABLE_SCHEMA_INFERENCE_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage058_table_schema_inference_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage058_table_schema_inference_slice.py"


class Stage058TableSchemaInferencePhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage058_table_schema_inference_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "schema_inference_input_records": [
                {
                    "source_identity_ref": "source:control:stage058-p2",
                    "source_document_ref": "source-document:control:stage058-p2:production",
                    "file_format": "XLSX",
                    "workbook_ref": "workbook:control:stage058-p2:production",
                    "worksheet_ref": "worksheet:control:stage058-p2:production",
                    "header_row_ref": "header-row:control:stage058-p2:production",
                    "row_range_ref": "row-range:control:stage058-p2:production",
                    "column_range_ref": "column-range:control:stage058-p2:production",
                    "record_type": "PRODUCTION_RECORD",
                    "evidence_ref": "evidence:control:stage058-p2:production",
                },
                {
                    "source_identity_ref": "source:control:stage058-p2",
                    "source_document_ref": "source-document:control:stage058-p2:quality",
                    "file_format": "CSV",
                    "workbook_ref": "workbook:control:stage058-p2:quality",
                    "worksheet_ref": "worksheet:control:stage058-p2:quality",
                    "header_row_ref": "header-row:control:stage058-p2:quality",
                    "row_range_ref": "row-range:control:stage058-p2:quality",
                    "column_range_ref": "column-range:control:stage058-p2:quality",
                    "record_type": "QUALITY_INSPECTION_RECORD",
                    "evidence_ref": "evidence:control:stage058-p2:quality",
                },
            ]
        }

    def test_phase2_artifacts_exist(self):
        for artifact in (PHASE1_CONTRACT, PHASE2, CONTRACT, SLICE):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_is_executable_but_real_input_and_runtime_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage058.table_schema_inference.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE058-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE058-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(
            10,
            contract["reference_only_schema_inference_input_contract"]["field_count"],
        )
        self.assertEqual(
            2,
            contract["reference_only_schema_inference_input_contract"]["control_record_count"],
        )
        self.assertEqual(18, contract["schema_profile_candidate_contract"]["field_count"])
        self.assertEqual(
            11,
            contract["schema_profile_candidate_contract"]
            ["control_schema_profile_candidate_count"],
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_slice_projects_candidate_profiles_from_p1_reference_only_input(self):
        result = self._slice().execute_table_schema_inference_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_SCHEMA_PROFILE_CANDIDATE_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["schema_inference_input_record_count"])
        self.assertEqual(2, result["schema_profile_group_count"])
        self.assertEqual(11, result["schema_profile_candidate_count"])
        self.assertEqual(11, result["candidate_field_mapping_count"])
        self.assertTrue(result["control_schema_profile_inference_performed"])
        self.assertTrue(result["control_field_identification_performed"])
        self.assertTrue(result["control_field_type_inference_performed"])
        self.assertFalse(result["source_body_or_header_or_cell_content_retained"])

    def test_candidate_profiles_cover_p1_semantics_and_field_types_only(self):
        result = self._slice().execute_table_schema_inference_control_slice(
            self._control()
        )
        self.assertEqual(9, result["semantic_category_count"])
        self.assertEqual(6, result["candidate_field_type_count"])
        self.assertEqual(
            {
                "DECIMAL_OR_INTEGER",
                "TEXT_REFERENCE",
                "DATE_OR_DATETIME",
                "IDENTIFIER_REFERENCE",
                "ENUMERATED_QUALITY_RESULT",
                "ENUMERATED_FACT_TYPE",
            },
            set(result["candidate_field_types"]),
        )
        self.assertEqual(
            "column-handle:control:stage058-p2:production:date",
            result["schema_profile_candidates"][0]["candidate_column_name"],
        )
        self.assertTrue(
            all(
                item["candidate_column_name"].startswith("column-handle:control:")
                for item in result["schema_profile_candidates"]
            )
        )

    def test_candidate_profiles_have_exact_p1_shape_and_source_location_references(self):
        result = self._slice().execute_table_schema_inference_control_slice(
            self._control()
        )
        candidate = result["schema_profile_candidates"][0]
        self.assertEqual(
            {
                "schema_profile_id",
                "source_document_ref",
                "file_format",
                "worksheet_ref",
                "header_row_ref",
                "row_range_ref",
                "column_range_ref",
                "candidate_column_name",
                "candidate_field_type",
                "candidate_unit_ref",
                "candidate_date_format_ref",
                "candidate_equipment_ref",
                "candidate_material_ref",
                "candidate_process_ref",
                "candidate_quality_result_ref",
                "candidate_fact_type",
                "evidence_ref",
                "inference_state",
            },
            set(candidate),
        )
        self.assertEqual(11, result["source_location_binding_candidate_count"])
        self.assertTrue(result["source_location_references_preserved"])
        self.assertEqual(
            "CANDIDATE_CONTROL_REFERENCE_ONLY", candidate["inference_state"]
        )
        self.assertFalse(result["actual_source_location_binding_created"])
        self.assertFalse(result["actual_evidence_record_created"])

    def test_fact_and_rag_layers_stay_deferred_and_numeric_authority_closed(self):
        result = self._slice().execute_table_schema_inference_control_slice(
            self._control()
        )
        self.assertEqual(0, result["structured_fact_candidate_count"])
        self.assertEqual(0, result["rag_summary_candidate_count"])
        self.assertTrue(result["fact_extraction_deferred_to_stage059"])
        self.assertTrue(result["rag_summary_deferred_to_stage060"])
        self.assertFalse(result["summary_can_replace_structured_fact"])
        self.assertFalse(result["summary_can_become_numeric_statistical_evidence"])
        self.assertFalse(result["numeric_statistic_computation_performed"])
        self.assertFalse(result["actual_structured_fact_created"])
        self.assertFalse(result["actual_rag_summary_created"])

    def test_invalid_control_input_rejects_without_returning_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_table_schema_inference_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["schema_profile_candidates"])
        self.assertEqual(0, result["schema_profile_candidate_count"])
        self.assertFalse(result["control_candidate_reference_projection_created"])

    def test_real_data_storage_and_external_actions_remain_disabled(self):
        result = self._slice().execute_table_schema_inference_control_slice(
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
            "actual_schema_profile_created",
            "actual_schema_profile_persisted",
            "actual_field_mapping_created",
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


if __name__ == "__main__":
    unittest.main()
