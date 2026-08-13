import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE057_PHASE1_XLSX_CSV_INGESTION_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_contract.json"
)
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage057-p1-local.json"


class Stage057XlsxCsvIngestionContractPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_and_contract_artifacts_exist(self):
        for artifact in (SCOPE, CONTRACT, BATCH, ROADMAP, EVENTS, STATUS, RUN):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage057.xlsx_csv_ingestion.phase1.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-057", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE057-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-057", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_XLSX_CSV_INGESTION_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE057-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE056_REVIEW_ARTIFACTS",
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
        input_contract = self.contract["reference_only_table_input_contract"]
        self.assertEqual(12, input_contract["field_count"])
        self.assertEqual(
            [
                "source_identity_ref",
                "source_document_ref",
                "file_format",
                "workbook_ref",
                "worksheet_ref",
                "row_range_ref",
                "column_range_ref",
                "record_type",
                "schema_profile_ref",
                "fact_type",
                "evidence_ref",
                "ingestion_state",
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
            "cell_value_content_allowed",
            "formula_value_allowed",
            "fixture_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(input_contract[field])

    def test_future_fact_fields_and_semantic_types_are_declared_only(self):
        output = self.contract["future_structured_fact_output_contract"]
        self.assertEqual(19, output["field_count"])
        self.assertEqual(
            [
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
            ],
            output["required_fields"],
        )
        for field in (
            "actual_structured_fact_created",
            "actual_structured_fact_persisted",
            "actual_typed_value_retained",
            "actual_database_schema_created",
            "direct_high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

        semantics = self.contract["field_semantic_contract"]
        self.assertEqual(
            [
                "measurement_value",
                "unit_ref",
                "record_date",
                "equipment_ref",
                "material_ref",
                "quality_result",
                "fact_type",
            ],
            semantics["required_business_fields"],
        )
        self.assertEqual(7, semantics["field_count"])
        self.assertEqual("DECIMAL_OR_INTEGER", semantics["field_types"]["measurement_value"]["data_type"])
        self.assertTrue(semantics["field_types"]["measurement_value"]["unit_required"])
        self.assertEqual("DATE_OR_DATETIME", semantics["field_types"]["record_date"]["data_type"])
        self.assertEqual("ENUMERATED_QUALITY_RESULT", semantics["field_types"]["quality_result"]["data_type"])
        self.assertEqual("ENUMERATED_FACT_TYPE", semantics["field_types"]["fact_type"]["data_type"])
        self.assertEqual("STAGE-058", semantics["schema_inference_owner"])
        self.assertEqual("STAGE-059", semantics["fact_extraction_owner"])
        self.assertFalse(semantics["field_identification_performed"])
        self.assertFalse(semantics["actual_field_mapping_created"])

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
        self.assertEqual("STAGE-060", summary["rag_summary_owner"])
        self.assertFalse(summary["summary_can_replace_structured_fact"])
        self.assertFalse(summary["summary_can_become_numeric_statistical_evidence"])
        self.assertTrue(summary["summary_requires_fact_reference_before_future_use"])
        self.assertFalse(summary["actual_rag_summary_created"])
        self.assertFalse(summary["actual_summary_write_performed"])

    def test_source_traceability_and_failure_closure_are_declared(self):
        location = self.contract["source_location_and_evidence_contract"]
        self.assertEqual(
            [
                "source_document_ref",
                "worksheet_ref",
                "row_range_ref",
                "column_range_ref",
                "evidence_ref",
            ],
            location["required_future_location_fields"],
        )
        self.assertEqual(5, location["location_field_count"])
        self.assertTrue(location["source_document_worksheet_row_column_binding_required"])
        self.assertFalse(location["physical_path_or_uri_allowed"])
        self.assertFalse(location["source_body_or_cell_content_allowed"])
        self.assertEqual(0, location["actual_source_location_binding_count"])
        self.assertFalse(location["actual_evidence_record_created"])
        self.assertEqual("STAGE-062", location["evidence_binding_owner"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            [
                "SOURCE_LOCATION_MISSING",
                "FIELD_TYPE_UNRECOGNIZED",
                "UNIT_UNRESOLVED",
                "DATE_FORMAT_UNRESOLVED",
                "QUALITY_RESULT_UNRESOLVED",
                "NUMERIC_VALUE_UNVERIFIED",
            ],
            failures["declared_failure_states"],
        )
        self.assertEqual(6, failures["failure_state_count"])
        self.assertTrue(failures["unrecognized_structure_requires_human_handling"])
        self.assertTrue(failures["unverified_numeric_value_blocks_statistical_conclusion"])
        self.assertFalse(failures["schema_migration_without_rollback_allowed"])
        self.assertFalse(failures["automatic_business_write_allowed"])

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
        self.assertTrue(runtime["stage056_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage057_started"])
        self.assertTrue(runtime["stage057_entry_authorized"])

    def test_governance_run_and_event_record_only_local_phase1_evidence(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage057_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE057-P1"'),
            (batch, 'next_gate: "IDS-STAGE057-P2-GATE"'),
            (batch, "stage057_started: true"),
            (batch, "stage057_entry_authorized: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE057"'),
            (roadmap, 'current_phase_id: "IDS-STAGE057-P1"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE057-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE057-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE057", status["stage"])
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE057-P1",
                "IDS-V0_1-STAGE057-P2",
                "IDS-V0_1-STAGE057-P3",
            ),
        )
        self.assertIn(
            status["next_gate"],
            (
                "IDS-STAGE057-P2-GATE",
                "IDS-STAGE057-P3-GATE",
                "IDS-STAGE057-P4-GATE",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_XLSX_CSV_INGESTION_CONTRACT_RUNTIME_DISABLED", run["result"]
        )
        self.assertEqual([8, 331, 1, 1, 7], [item["passed"] for item in run["evidence_iterations"]])
        self.assertEqual([8, 331, 1, 1, 7], [item["total"] for item in run["evidence_iterations"]])
        self.assertEqual(
            "PASS_PHASE1_AND_PREDECESSOR_REGRESSION",
            run["evidence_iterations"][1]["result"],
        )
        self.assertFalse(run["observed_work"]["authorized_fixture_access_performed"])
        self.assertFalse(run["observed_work"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(run["observed_work"]["structured_fact_write_performed"])
        self.assertFalse(run["observed_work"]["numeric_statistic_computation_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE057-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE057-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-057"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE057-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
