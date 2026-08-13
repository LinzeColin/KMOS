import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage059_fact_extraction_contract.json"
)
PHASE2 = BASE / "STAGE059_PHASE2_FACT_EXTRACTION_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage059_fact_extraction_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage059_fact_extraction_slice.py"


class Stage059FactExtractionPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage059_fact_extraction_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _phase1_contract(self):
        return json.loads(PHASE1_CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "fact_extraction_input_records": [
                {
                    "source_identity_ref": "source:control:stage059-p2",
                    "source_document_ref": "source-document:control:stage059-p2:production",
                    "file_format": "XLSX",
                    "workbook_ref": "workbook:control:stage059-p2:production",
                    "worksheet_ref": "worksheet:control:stage059-p2:production",
                    "header_row_ref": "header-row:control:stage059-p2:production",
                    "row_range_ref": "row-range:control:stage059-p2:production",
                    "column_range_ref": "column-range:control:stage059-p2:production",
                    "schema_profile_ref": "schema-profile:control:stage059-p2:production",
                    "field_candidate_ref": "field-candidate:control:stage059-p2:production",
                    "record_type": "PRODUCTION_RECORD",
                    "evidence_ref": "evidence:control:stage059-p2:production",
                },
                {
                    "source_identity_ref": "source:control:stage059-p2",
                    "source_document_ref": "source-document:control:stage059-p2:quality",
                    "file_format": "CSV",
                    "workbook_ref": "workbook:control:stage059-p2:quality",
                    "worksheet_ref": "worksheet:control:stage059-p2:quality",
                    "header_row_ref": "header-row:control:stage059-p2:quality",
                    "row_range_ref": "row-range:control:stage059-p2:quality",
                    "column_range_ref": "column-range:control:stage059-p2:quality",
                    "schema_profile_ref": "schema-profile:control:stage059-p2:quality",
                    "field_candidate_ref": "field-candidate:control:stage059-p2:quality",
                    "record_type": "QUALITY_INSPECTION_RECORD",
                    "evidence_ref": "evidence:control:stage059-p2:quality",
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
            "ids.stage059.fact_extraction.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE059-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE059-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(
            12, contract["reference_only_fact_extraction_input_contract"]["field_count"]
        )
        self.assertEqual(
            2,
            contract["reference_only_fact_extraction_input_contract"][
                "control_record_count"
            ],
        )
        self.assertEqual(25, contract["structured_fact_candidate_contract"]["field_count"])
        self.assertEqual(
            3, contract["structured_fact_candidate_contract"]["control_fact_candidate_count"]
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_slice_projects_three_fact_categories_from_p1_reference_only_input(self):
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_FACT_CANDIDATE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["fact_extraction_input_record_count"])
        self.assertEqual(3, result["structured_fact_candidate_count"])
        self.assertEqual(3, result["fact_category_count"])
        self.assertEqual(
            {"PRODUCTION_FACT", "QUALITY_FACT", "INSPECTION_FACT"},
            set(result["fact_categories"]),
        )
        self.assertTrue(result["control_schema_reference_validation_performed"])
        self.assertTrue(result["control_field_reference_validation_performed"])
        self.assertTrue(result["control_fact_candidate_projection_performed"])

    def test_candidates_keep_exact_p1_shape_and_control_only_references(self):
        phase1 = self._phase1_contract()
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        candidate = result["structured_fact_candidates"][0]
        self.assertEqual(
            phase1["future_typed_fact_output_contract"]["required_fields"],
            list(candidate),
        )
        self.assertEqual(25, len(candidate))
        self.assertTrue(candidate["fact_id"].startswith("fact-candidate:control:"))
        self.assertTrue(candidate["field_name_ref"].startswith("field-name:control:"))
        self.assertTrue(
            all(
                item["source_identity_ref"].startswith("source:control:")
                for item in result["structured_fact_candidates"]
            )
        )

    def test_typed_values_stay_unset_while_p1_semantics_are_covered(self):
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        self.assertTrue(result["all_control_typed_values_unset"])
        self.assertTrue(
            all(
                item["typed_value"] is None
                for item in result["structured_fact_candidates"]
            )
        )
        self.assertEqual(7, result["typed_semantic_category_count"])
        self.assertEqual(1, result["numeric_field_candidate_count"])
        self.assertEqual(
            {
                "DECIMAL_OR_INTEGER",
                "ENUMERATED_QUALITY_RESULT_REFERENCE",
                "ENUMERATED_FACT_TYPE",
            },
            set(result["candidate_field_types"]),
        )
        self.assertFalse(result["actual_typed_value_retained"])

    def test_candidates_preserve_reference_only_source_location_shape(self):
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        candidate = result["structured_fact_candidates"][0]
        self.assertEqual(3, result["source_location_binding_candidate_count"])
        self.assertTrue(result["source_location_references_preserved"])
        for field in (
            "source_document_ref",
            "worksheet_ref",
            "header_row_ref",
            "row_range_ref",
            "column_range_ref",
            "evidence_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", candidate[field])
        self.assertFalse(result["actual_source_location_binding_created"])
        self.assertFalse(result["actual_evidence_record_created"])

    def test_rag_and_numeric_authority_remain_separated_and_deferred(self):
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        self.assertEqual(0, result["rag_summary_candidate_count"])
        self.assertTrue(result["rag_summary_deferred_to_stage060"])
        self.assertFalse(result["summary_can_replace_structured_fact"])
        self.assertFalse(result["summary_can_become_numeric_statistical_evidence"])
        self.assertFalse(result["numeric_statistic_computation_performed"])
        self.assertFalse(result["actual_rag_summary_created"])

    def test_invalid_control_input_rejects_without_returning_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_fact_extraction_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["structured_fact_candidates"])
        self.assertEqual(0, result["structured_fact_candidate_count"])
        self.assertFalse(result["control_fact_candidate_projection_performed"])

    def test_real_data_storage_and_external_actions_remain_disabled(self):
        result = self._slice().execute_fact_extraction_control_slice(self._control())
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "real_table_schema_inference_performed",
            "real_field_identification_performed",
            "real_structured_fact_extraction_performed",
            "typed_value_extraction_performed",
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


if __name__ == "__main__":
    unittest.main()
