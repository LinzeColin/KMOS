import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE058_PHASE1_TABLE_SCHEMA_INFERENCE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage058_table_schema_inference_contract.json"
)


class Stage058TableSchemaInferenceContractPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_and_contract_artifacts_exist(self):
        for artifact in (SCOPE, CONTRACT):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage058.table_schema_inference.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-058", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE058-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-058", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_TABLE_SCHEMA_INFERENCE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE058-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE057_REVIEW_ARTIFACTS",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_reference_only_xlsx_csv_inputs_are_content_free(self):
        input_contract = self.contract["reference_only_schema_inference_input_contract"]
        self.assertEqual(10, input_contract["field_count"])
        self.assertEqual(
            [
                "source_identity_ref",
                "source_document_ref",
                "file_format",
                "workbook_ref",
                "worksheet_ref",
                "header_row_ref",
                "row_range_ref",
                "column_range_ref",
                "record_type",
                "evidence_ref",
            ],
            input_contract["required_fields"],
        )
        self.assertEqual(["XLSX", "CSV"], input_contract["allowed_file_formats"])
        self.assertEqual(
            ["PRODUCTION_RECORD", "QUALITY_INSPECTION_RECORD"],
            input_contract["record_types"],
        )
        self.assertEqual(0, input_contract["actual_input_record_count"])
        for field in (
            "additional_fields_allowed",
            "source_body_or_path_allowed",
            "worksheet_content_allowed",
            "header_cell_content_allowed",
            "cell_value_content_allowed",
            "formula_value_allowed",
            "fixture_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(input_contract[field])

    def test_future_schema_profile_and_semantics_are_declared_only(self):
        profile = self.contract["future_schema_profile_contract"]
        self.assertEqual(18, profile["field_count"])
        self.assertEqual(
            [
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
            ],
            profile["required_fields"],
        )
        for field in (
            "additional_fields_allowed",
            "actual_schema_profile_created",
            "actual_schema_profile_persisted",
            "actual_column_name_retained",
            "actual_field_mapping_created",
            "direct_high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(profile[field])

        semantics = self.contract["field_candidate_semantic_contract"]
        self.assertEqual(9, semantics["semantic_category_count"])
        self.assertEqual(
            [
                "candidate_column_name",
                "candidate_field_type",
                "candidate_date_format_ref",
                "candidate_unit_ref",
                "candidate_material_ref",
                "candidate_equipment_ref",
                "candidate_process_ref",
                "candidate_quality_result_ref",
                "candidate_fact_type",
            ],
            semantics["required_semantic_categories"],
        )
        self.assertEqual(6, semantics["candidate_field_type_count"])
        for field in (
            "field_identification_performed",
            "field_type_inference_performed",
            "unit_inference_performed",
            "date_format_inference_performed",
            "equipment_resolution_performed",
            "material_resolution_performed",
            "process_resolution_performed",
            "quality_result_evaluation_performed",
            "fact_type_inference_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(semantics[field])

    def test_numeric_authority_and_rag_summary_are_separated(self):
        numeric = self.contract["numeric_fact_authority_boundary"]
        self.assertEqual(
            "DERIVED_STRUCTURED_FACT_PROJECTION_NOT_SECOND_AUTHORITATIVE_SOURCE",
            numeric["mode"],
        )
        self.assertTrue(numeric["source_document_remains_authoritative"])
        self.assertFalse(numeric["model_direct_text_guessing_allowed"])
        self.assertFalse(numeric["model_text_statistic_authoritative"])
        self.assertFalse(numeric["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertTrue(numeric["numeric_aggregation_requires_source_location_and_evidence"])
        self.assertEqual(0, numeric["actual_numeric_fact_count"])
        self.assertFalse(numeric["numeric_statistic_computation_performed"])
        self.assertFalse(numeric["structured_fact_store_created"])

        summary = self.contract["fact_and_rag_summary_boundary"]
        self.assertFalse(summary["summary_can_replace_structured_fact"])
        self.assertFalse(summary["summary_can_become_numeric_statistical_evidence"])
        self.assertTrue(summary["summary_requires_fact_reference_before_future_use"])
        self.assertFalse(summary["actual_structured_fact_created"])
        self.assertFalse(summary["actual_rag_summary_created"])
        self.assertFalse(summary["actual_summary_write_performed"])

    def test_source_traceability_failure_and_rollback_are_explicit(self):
        location = self.contract["source_location_and_evidence_contract"]
        self.assertEqual(6, location["location_field_count"])
        self.assertTrue(
            location["source_document_worksheet_header_row_column_binding_required"]
        )
        self.assertFalse(location["physical_path_or_uri_allowed"])
        self.assertFalse(location["source_body_or_cell_content_allowed"])
        self.assertEqual(0, location["actual_source_location_binding_count"])
        self.assertFalse(location["actual_evidence_record_created"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(8, failures["failure_state_count"])
        self.assertTrue(failures["unrecognized_structure_requires_human_handling"])
        self.assertTrue(failures["unverified_numeric_value_blocks_statistical_conclusion"])
        self.assertFalse(failures["schema_migration_without_rollback_allowed"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "STAGE057_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED",
            rollback["rollback_target_contract_state"],
        )
        self.assertFalse(rollback["actual_rollback_performed"])
        self.assertFalse(rollback["raw_source_change_allowed"])
        self.assertFalse(rollback["persistent_database_change_allowed"])
        self.assertFalse(rollback["production_state_change_allowed"])

    def test_chinese_feedback_and_runtime_boundary_do_not_claim_runtime(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertEqual(4, len(feedback["messages"]))
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["numeric_accuracy_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])

        runtime = self.contract["runtime_boundary"]
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "table_summary_generation_performed",
            "numeric_statistic_computation_performed",
            "quality_gate_evaluation_performed",
            "source_location_binding_performed",
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
            "phase2_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(runtime[field])
        self.assertTrue(runtime["stage057_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage058_started"])
        self.assertTrue(runtime["stage058_entry_authorized"])


if __name__ == "__main__":
    unittest.main()
