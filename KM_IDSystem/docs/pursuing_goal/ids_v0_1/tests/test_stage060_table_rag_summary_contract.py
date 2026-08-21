import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE060_PHASE1_TABLE_RAG_SUMMARY_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "structured_table_facts" / "stage060_table_rag_summary_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage060-p1-local.json"


class Stage060TableRagSummaryContractPhase1Tests(unittest.TestCase):
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
            "ids.stage060.table_rag_summary.phase1.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-060", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE060-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-060", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_TABLE_RAG_SUMMARY_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE060-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_AND_STAGE059_REVIEW_ARTIFACTS_ONLY",
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

    def test_reference_only_summary_inputs_are_content_free(self):
        inputs = self.contract["reference_only_summary_input_contract"]
        self.assertEqual(13, inputs["field_count"])
        self.assertEqual(
            [
                "summary_scope_ref",
                "fact_set_ref",
                "fact_id_ref",
                "fact_type",
                "source_identity_ref",
                "source_document_ref",
                "workbook_ref",
                "worksheet_ref",
                "row_range_ref",
                "column_range_ref",
                "schema_profile_ref",
                "evidence_ref",
                "rag_summary_eligibility",
            ],
            inputs["required_fields"],
        )
        self.assertEqual(["XLSX", "CSV"], inputs["allowed_file_formats"])
        self.assertEqual(
            ["PRODUCTION_RECORD", "QUALITY_INSPECTION_RECORD"],
            inputs["record_types"],
        )
        self.assertEqual(0, inputs["actual_input_record_count"])
        for field in (
            "additional_fields_allowed",
            "source_body_or_path_allowed",
            "worksheet_content_allowed",
            "header_cell_content_allowed",
            "cell_value_content_allowed",
            "formula_value_allowed",
            "actual_structured_fact_read_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])

    def test_future_summary_output_and_table_semantics_are_declared_only(self):
        output = self.contract["future_rag_summary_output_contract"]
        self.assertEqual(10, output["field_count"])
        self.assertEqual(
            [
                "rag_summary_id",
                "summary_scope_ref",
                "fact_set_ref",
                "fact_reference_list",
                "source_location_ref_list",
                "summary_language",
                "summary_state",
                "numeric_claim_state",
                "human_review_state",
                "evidence_ref",
            ],
            output["required_fields"],
        )
        self.assertEqual("zh-CN", output["default_summary_language"])
        for field in (
            "additional_fields_allowed",
            "actual_rag_summary_created",
            "actual_summary_text_retained",
            "actual_summary_persisted",
            "actual_database_schema_created",
            "direct_high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

        semantics = self.contract["table_semantic_reference_contract"]
        self.assertEqual(7, semantics["typed_semantic_category_count"])
        self.assertEqual(
            "DECIMAL_OR_INTEGER_REFERENCE_ONLY",
            semantics["field_types"]["measurement_value"]["data_type"],
        )
        self.assertTrue(semantics["field_types"]["measurement_value"]["unit_required"])
        self.assertEqual("STAGE-058", semantics["schema_inference_owner"])
        self.assertEqual("STAGE-059", semantics["fact_extraction_owner"])
        self.assertFalse(semantics["field_identification_performed"])
        self.assertFalse(semantics["actual_field_mapping_created"])

    def test_structured_fact_and_numeric_authority_remain_separate(self):
        boundary = self.contract["structured_fact_and_numeric_authority_boundary"]
        self.assertEqual(
            "RAG_CONTEXTUAL_SUMMARY_NOT_SECOND_AUTHORITATIVE_SOURCE",
            boundary["mode"],
        )
        self.assertTrue(boundary["source_document_remains_authoritative"])
        self.assertFalse(boundary["model_direct_text_guessing_allowed"])
        self.assertFalse(boundary["model_text_statistic_authoritative"])
        self.assertFalse(boundary["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertTrue(boundary["numeric_aggregation_requires_source_location_and_evidence"])
        self.assertFalse(boundary["summary_can_replace_structured_fact"])
        self.assertFalse(boundary["summary_can_become_numeric_statistical_evidence"])
        self.assertTrue(boundary["summary_requires_fact_reference_before_future_use"])
        self.assertEqual(0, boundary["actual_structured_fact_count"])
        self.assertEqual(0, boundary["actual_numeric_fact_count"])
        self.assertFalse(boundary["numeric_statistic_computation_performed"])
        self.assertFalse(boundary["actual_rag_summary_created"])
        self.assertFalse(boundary["actual_summary_write_performed"])

    def test_source_traceability_failure_closure_and_rollback_are_declared(self):
        location = self.contract["source_location_and_evidence_contract"]
        self.assertEqual(6, location["location_field_count"])
        self.assertTrue(
            location["source_document_worksheet_header_row_column_binding_required"]
        )
        self.assertFalse(location["physical_path_or_uri_allowed"])
        self.assertFalse(location["source_body_or_cell_content_allowed"])
        self.assertEqual(0, location["actual_source_location_binding_count"])
        self.assertFalse(location["actual_evidence_record_created"])
        self.assertEqual("STAGE-062", location["evidence_binding_owner"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(10, failures["failure_state_count"])
        self.assertIn("FACT_REFERENCE_MISSING", failures["declared_failure_states"])
        self.assertIn("RAG_ELIGIBILITY_UNRESOLVED", failures["declared_failure_states"])
        self.assertIn("NUMERIC_VALUE_UNVERIFIED", failures["declared_failure_states"])
        self.assertTrue(failures["unrecognized_structure_requires_human_handling"])
        self.assertTrue(failures["unverified_numeric_value_blocks_statistical_conclusion"])
        self.assertFalse(failures["automatic_summary_write_allowed"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "STAGE059_REVIEWED_LOCAL_FACT_EXTRACTION_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "source_or_raw_data_change_allowed",
            "fixture_change_allowed",
            "database_schema_change_allowed",
            "persistent_runtime_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

    def test_chinese_feedback_and_runtime_boundary_do_not_claim_runtime(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertEqual(4, len(feedback["messages"]))
        for field in (
            "automation_claim_allowed",
            "retrieval_quality_claim_allowed",
            "numeric_accuracy_claim_allowed",
            "production_availability_claim_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(feedback[field])

        runtime = self.contract["runtime_boundary"]
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "table_summary_generation_performed",
            "rag_summary_generation_performed",
            "numeric_statistic_computation_performed",
            "quality_gate_evaluation_performed",
            "source_location_binding_performed",
            "evidence_binding_performed",
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
        self.assertTrue(runtime["stage059_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage060_started"])
        self.assertTrue(runtime["stage060_entry_authorized"])

    def test_governance_run_and_event_record_only_local_phase1_evidence(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage060_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE060-P1"'),
            (batch, 'next_gate: "IDS-STAGE060-P2-GATE"'),
            (batch, "stage060_started: true"),
            (batch, "stage060_entry_authorized: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE060"'),
            (roadmap, 'current_phase_id: "IDS-STAGE060-P1"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE060-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE060-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE060", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078"))
        self.assertIn(
            status["phase"],
            ("IDS-V0_1-STAGE060-P1", "IDS-V0_1-STAGE060-P2", "IDS-V0_1-STAGE060-P3", "IDS-V0_1-STAGE060-P4", "IDS-V0_1-STAGE060-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
                "IDS-V0_1-STAGE069-P1",
                "IDS-V0_1-STAGE069-P2",
                "IDS-V0_1-STAGE069-P3",
                "IDS-V0_1-STAGE069-P4",
                "IDS-V0_1-STAGE069-REVIEW",

                "IDS-V0_1-STAGE070-P1","IDS-V0_1-STAGE070-P2","IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
                'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
                'IDS-V0_1-STAGE076-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
            , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4"),
        )
        self.assertIn(
            status["task"],
            ("IDS-V0_1-STAGE060-P1", "IDS-V0_1-STAGE060-P2", "IDS-V0_1-STAGE060-P3", "IDS-V0_1-STAGE060-P4", "IDS-V0_1-STAGE060-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
                "IDS-V0_1-STAGE069-P1",
                "IDS-V0_1-STAGE069-P2",
                "IDS-V0_1-STAGE069-P3",
                "IDS-V0_1-STAGE069-P4",
                "IDS-V0_1-STAGE069-REVIEW",

                "IDS-V0_1-STAGE070-P1","IDS-V0_1-STAGE070-P2","IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
                'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
                'IDS-V0_1-STAGE076-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
            , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4"),
        )
        self.assertIn(
            status["next_gate"],
            ("IDS-STAGE060-P2-GATE", "IDS-STAGE060-P3-GATE", "IDS-STAGE060-P4-GATE", "IDS-STAGE060-REVIEW-GATE", "IDS-V0_1-BATCH-051-060-REVIEW-GATE", "IDS-STAGE066-P2-GATE", "IDS-STAGE066-P3-GATE", "IDS-STAGE066-P4-GATE", "IDS-STAGE066-REVIEW-GATE", "IDS-STAGE067-P1-GATE", "IDS-STAGE067-P2-GATE", "IDS-STAGE067-P3-GATE", "IDS-STAGE067-P4-GATE", "IDS-STAGE067-REVIEW-GATE", "IDS-STAGE068-P1-GATE", "IDS-STAGE068-P2-GATE", "IDS-STAGE068-P3-GATE", "IDS-STAGE068-P4-GATE", "IDS-STAGE068-REVIEW-GATE", "IDS-STAGE069-P1-GATE",
                "IDS-STAGE069-P2-GATE",
                "IDS-STAGE069-P3-GATE",
                "IDS-STAGE069-P4-GATE",
                "IDS-STAGE069-REVIEW-GATE",
                "IDS-STAGE070-P1-GATE",
                "IDS-STAGE070-P2-GATE",
                "IDS-STAGE070-P3-GATE",
"IDS-STAGE070-P4-GATE",
"IDS-STAGE070-REVIEW-GATE",
"IDS-STAGE071-P1-GATE",
"IDS-STAGE071-P2-GATE",
"IDS-STAGE071-P3-GATE",
"IDS-STAGE071-P4-GATE",
                "IDS-STAGE071-REVIEW-GATE",
                "IDS-STAGE072-P1-GATE",
                "IDS-STAGE072-P2-GATE", "IDS-STAGE072-P3-GATE", "IDS-STAGE072-P4-GATE", "IDS-STAGE072-REVIEW-GATE", "IDS-STAGE073-P1-GATE", "IDS-STAGE073-P2-GATE", "IDS-STAGE073-P3-GATE", "IDS-STAGE073-P4-GATE", "IDS-STAGE073-REVIEW-GATE", "IDS-STAGE074-P1-GATE", "IDS-STAGE074-P2-GATE", "IDS-STAGE074-P3-GATE", "IDS-STAGE074-P4-GATE", "IDS-STAGE074-REVIEW-GATE", "IDS-STAGE075-P1-GATE",
                'IDS-STAGE075-P2-GATE', 'IDS-STAGE075-P3-GATE', 'IDS-STAGE075-P4-GATE', 'IDS-STAGE075-REVIEW-GATE', 'IDS-STAGE076-P1-GATE',
                'IDS-STAGE076-P2-GATE',
            'IDS-STAGE076-P3-GATE', 'IDS-STAGE076-P4-GATE', 'IDS-STAGE076-REVIEW-GATE', 'IDS-STAGE077-P1-GATE', 'IDS-STAGE077-P2-GATE',
            'IDS-STAGE077-P3-GATE', 'IDS-STAGE077-P4-GATE', 'IDS-STAGE077-REVIEW-GATE', 'IDS-STAGE078-P1-GATE',
             "IDS-STAGE078-P2-GATE", "IDS-STAGE078-P3-GATE", "IDS-STAGE078-P4-GATE", "IDS-STAGE078-REVIEW-GATE"),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_TABLE_RAG_SUMMARY_CONTRACT_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual(8, run["evidence_iterations"][0]["passed"])
        self.assertEqual(8, run["evidence_iterations"][0]["total"])
        self.assertFalse(run["observed_work"]["rag_summary_generation_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE060-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE060-P1", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE060-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
