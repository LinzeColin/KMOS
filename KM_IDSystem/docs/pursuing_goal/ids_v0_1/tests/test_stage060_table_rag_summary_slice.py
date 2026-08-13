import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage060_table_rag_summary_contract.json"
)
PHASE2 = BASE / "STAGE060_PHASE2_TABLE_RAG_SUMMARY_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage060_table_rag_summary_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage060_table_rag_summary_slice.py"


class Stage060TableRagSummaryPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage060_table_rag_summary_slice", SLICE
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
            "table_rag_summary_input_records": [
                {
                    "summary_scope_ref": "summary-scope:control:stage060-p2:production",
                    "fact_set_ref": "fact-set:control:stage060-p2:production",
                    "fact_id_ref": "fact-ref:control:stage060-p2:production",
                    "fact_type": "PRODUCTION_FACT",
                    "source_identity_ref": "source:control:stage060-p2",
                    "source_document_ref": (
                        "source-document:control:stage060-p2:production"
                    ),
                    "workbook_ref": "workbook:control:stage060-p2:production",
                    "worksheet_ref": "worksheet:control:stage060-p2:production",
                    "row_range_ref": "row-range:control:stage060-p2:production",
                    "column_range_ref": "column-range:control:stage060-p2:production",
                    "schema_profile_ref": (
                        "schema-profile:control:stage060-p2:production"
                    ),
                    "evidence_ref": "evidence:control:stage060-p2:production",
                    "rag_summary_eligibility": (
                        "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
                    ),
                },
                {
                    "summary_scope_ref": "summary-scope:control:stage060-p2:quality",
                    "fact_set_ref": "fact-set:control:stage060-p2:quality",
                    "fact_id_ref": "fact-ref:control:stage060-p2:quality",
                    "fact_type": "QUALITY_FACT",
                    "source_identity_ref": "source:control:stage060-p2",
                    "source_document_ref": (
                        "source-document:control:stage060-p2:quality"
                    ),
                    "workbook_ref": "workbook:control:stage060-p2:quality",
                    "worksheet_ref": "worksheet:control:stage060-p2:quality",
                    "row_range_ref": "row-range:control:stage060-p2:quality",
                    "column_range_ref": "column-range:control:stage060-p2:quality",
                    "schema_profile_ref": "schema-profile:control:stage060-p2:quality",
                    "evidence_ref": "evidence:control:stage060-p2:quality",
                    "rag_summary_eligibility": (
                        "ELIGIBLE_CONTROL_REFERENCE_ONLY_PENDING_HUMAN_CONFIRMATION"
                    ),
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
            "ids.stage060.table_rag_summary.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE060-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE060-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(
            13, contract["reference_only_summary_input_contract"]["field_count"]
        )
        self.assertEqual(
            2,
            contract["reference_only_summary_input_contract"]["control_record_count"],
        )
        self.assertEqual(10, contract["rag_summary_candidate_contract"]["field_count"])
        self.assertEqual(
            2,
            contract["rag_summary_candidate_contract"][
                "control_rag_summary_candidate_count"
            ],
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_slice_projects_two_chinese_summary_candidates_from_p1_reference_only_input(
        self,
    ):
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_RAG_SUMMARY_CANDIDATE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["control_summary_input_record_count"])
        self.assertEqual(0, result["actual_summary_input_record_count"])
        self.assertEqual(2, result["rag_summary_candidate_count"])
        self.assertEqual(2, result["fact_reference_count"])
        self.assertEqual(["PRODUCTION_FACT", "QUALITY_FACT"], result["fact_types"])
        self.assertTrue(result["control_schema_reference_validation_performed"])
        self.assertTrue(result["control_fact_reference_validation_performed"])
        self.assertTrue(result["control_table_summary_candidate_projection_performed"])

    def test_candidates_keep_exact_p1_shape_and_control_only_references(self):
        phase1 = self._phase1_contract()
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
        candidate = result["rag_summary_candidates"][0]
        self.assertEqual(
            phase1["future_rag_summary_output_contract"]["required_fields"],
            list(candidate),
        )
        self.assertEqual(10, len(candidate))
        self.assertTrue(candidate["rag_summary_id"].startswith("rag-summary-candidate:control:"))
        self.assertEqual(
            ["fact-ref:control:stage060-p2:production"],
            candidate["fact_reference_list"],
        )
        self.assertNotIn("summary_text", candidate)
        self.assertTrue(result["all_summary_text_unset"])

    def test_candidates_preserve_fact_and_source_location_reference_shape(self):
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
        candidate = result["rag_summary_candidates"][0]
        self.assertEqual(2, result["source_location_binding_candidate_count"])
        self.assertTrue(result["source_location_references_preserved"])
        self.assertEqual(6, len(candidate["source_location_ref_list"]))
        for value in candidate["source_location_ref_list"]:
            with self.subTest(value=value):
                self.assertIn(":control:", value)
        self.assertEqual(
            "evidence:control:stage060-p2:production", candidate["evidence_ref"]
        )
        self.assertFalse(result["actual_structured_fact_created"])
        self.assertFalse(result["actual_source_location_binding_created"])
        self.assertFalse(result["actual_evidence_record_created"])

    def test_structured_fact_and_numeric_authority_remain_separated(self):
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
        self.assertFalse(result["summary_can_replace_structured_fact"])
        self.assertFalse(result["summary_can_become_numeric_statistical_evidence"])
        self.assertTrue(result["summary_requires_fact_reference_before_future_use"])
        self.assertFalse(result["model_direct_text_guessing_allowed"])
        self.assertFalse(result["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertFalse(result["numeric_statistic_computation_performed"])
        self.assertFalse(result["actual_rag_summary_created"])

    def test_invalid_control_input_rejects_without_returning_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_table_rag_summary_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["rag_summary_candidates"])
        self.assertEqual(0, result["rag_summary_candidate_count"])
        self.assertFalse(result["control_table_summary_candidate_projection_performed"])

    def test_chinese_feedback_is_present_without_summary_text_or_business_content(self):
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
                for message in result["chinese_feedback"]
            )
        )
        self.assertFalse(result["source_body_or_header_or_cell_content_retained"])
        self.assertFalse(result["actual_summary_text_retained"])
        self.assertFalse(result["actual_rag_summary_persisted"])

    def test_real_data_storage_and_external_actions_remain_disabled(self):
        result = self._slice().execute_table_rag_summary_control_slice(self._control())
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
            "quality_gate_evaluation_performed",
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
