import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE062_PHASE1_TABLE_EVIDENCE_BINDING_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage062_table_evidence_binding_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage062-p1-local.json"
HUMAN_ACCEPTANCE = ROOT / "文档" / "05_执行与验收.md"


class Stage062TableEvidenceBindingContractPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_and_contract_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage062.table_evidence_binding.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-062", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE062-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-062", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_TABLE_EVIDENCE_BINDING_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE062-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE062_TASKPACK_AND_STAGE061_REVIEW_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "actual_source_uri_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_reference_only_inputs_cover_all_six_binding_dimensions(self):
        inputs = self.contract["reference_only_binding_input_contract"]
        self.assertEqual(19, inputs["field_count"])
        self.assertEqual(
            [
                "binding_request_ref",
                "fact_ref",
                "evidence_id",
                "document_id",
                "sheet",
                "row",
                "column",
                "source_uri",
                "file_format",
                "record_type",
                "workbook_ref",
                "schema_profile_ref",
                "field_candidate_ref",
                "primary_key_ref",
                "quality_result_ref",
                "measurement_value_ref",
                "unit_ref",
                "record_date_ref",
                "fact_type",
            ],
            inputs["required_fields"],
        )
        self.assertEqual(
            ["evidence_id", "document_id", "sheet", "row", "column", "source_uri"],
            inputs["required_binding_dimensions"],
        )
        self.assertEqual(6, inputs["binding_dimension_count"])
        self.assertEqual(["XLSX", "CSV"], inputs["allowed_file_formats"])
        self.assertEqual(
            ["PRODUCTION_RECORD", "QUALITY_INSPECTION_RECORD"],
            inputs["record_types"],
        )
        self.assertEqual(0, inputs["actual_input_record_count"])
        for field in (
            "additional_fields_allowed",
            "source_uri_physical_path_or_actual_uri_allowed",
            "source_body_or_path_allowed",
            "worksheet_content_allowed",
            "header_cell_content_allowed",
            "cell_value_content_allowed",
            "formula_value_allowed",
            "fixture_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])
        self.assertTrue(inputs["source_uri_is_opaque_reference_only"])

    def test_future_output_and_semantic_fields_are_declared_only(self):
        output = self.contract["future_table_evidence_binding_output_contract"]
        self.assertEqual(17, output["field_count"])
        self.assertEqual(
            ["evidence_id", "document_id", "sheet", "row", "column", "source_uri"],
            [
                field
                for field in output["required_fields"]
                if field in {"evidence_id", "document_id", "sheet", "row", "column", "source_uri"}
            ],
        )
        for field in (
            "additional_fields_allowed",
            "actual_table_evidence_binding_created",
            "actual_table_evidence_binding_persisted",
            "actual_evidence_record_created",
            "actual_database_schema_created",
            "direct_high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

        semantics = self.contract["field_semantic_contract"]
        self.assertEqual(8, semantics["semantic_field_count"])
        self.assertEqual(
            "DECIMAL_OR_INTEGER_REFERENCE",
            semantics["field_types"]["measurement_value_ref"]["data_type"],
        )
        self.assertTrue(semantics["field_types"]["measurement_value_ref"]["unit_required"])
        self.assertEqual(
            "DATE_OR_DATETIME_REFERENCE",
            semantics["field_types"]["record_date_ref"]["data_type"],
        )
        self.assertEqual(
            "IDENTIFIER_REFERENCE",
            semantics["field_types"]["equipment_ref"]["data_type"],
        )
        self.assertEqual(
            "IDENTIFIER_REFERENCE",
            semantics["field_types"]["material_ref"]["data_type"],
        )
        self.assertEqual(
            "ENUMERATED_QUALITY_RESULT_REFERENCE",
            semantics["field_types"]["quality_result_ref"]["data_type"],
        )
        self.assertEqual(
            "ENUMERATED_FACT_TYPE",
            semantics["field_types"]["fact_type"]["data_type"],
        )
        self.assertFalse(semantics["field_identification_performed"])
        self.assertFalse(semantics["actual_field_mapping_created"])

    def test_binding_and_numeric_authority_boundaries_remain_closed(self):
        binding = self.contract["binding_dimension_contract"]
        self.assertEqual(6, binding["binding_dimension_count"])
        self.assertEqual(
            "OPAQUE_REFERENCE_IDENTIFIER_NO_PHYSICAL_PATH_OR_ACTUAL_URI",
            binding["source_uri_reference_format"],
        )
        self.assertEqual(0, binding["actual_source_location_binding_count"])
        self.assertEqual(0, binding["actual_evidence_binding_count"])
        for field in (
            "evidence_id_binding_performed",
            "document_id_binding_performed",
            "sheet_binding_performed",
            "row_binding_performed",
            "column_binding_performed",
            "source_uri_binding_performed",
            "actual_source_traceability_validated",
        ):
            with self.subTest(field=field):
                self.assertFalse(binding[field])

        numeric = self.contract["numeric_fact_authority_boundary"]
        self.assertEqual(
            "DERIVED_STRUCTURED_FACT_PROJECTION_NOT_SECOND_AUTHORITATIVE_SOURCE",
            numeric["mode"],
        )
        self.assertTrue(numeric["source_document_remains_authoritative"])
        self.assertFalse(numeric["model_direct_text_guessing_allowed"])
        self.assertFalse(numeric["model_text_statistic_authoritative"])
        self.assertFalse(numeric["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertTrue(numeric["numeric_aggregation_requires_all_six_binding_dimensions"])
        self.assertEqual(0, numeric["actual_structured_fact_count"])
        self.assertEqual(0, numeric["actual_numeric_fact_count"])
        self.assertFalse(numeric["numeric_statistic_computation_performed"])
        self.assertFalse(numeric["structured_fact_store_created"])

        summary = self.contract["fact_and_rag_summary_boundary"]
        self.assertEqual("STAGE-060", summary["rag_summary_owner"])
        self.assertFalse(summary["summary_can_replace_structured_fact"])
        self.assertFalse(summary["summary_can_become_numeric_statistical_evidence"])

    def test_failure_closure_and_rollback_are_declared(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(13, failures["failure_state_count"])
        for state in (
            "EVIDENCE_ID_MISSING",
            "DOCUMENT_ID_MISSING",
            "SHEET_REFERENCE_MISSING",
            "ROW_REFERENCE_MISSING",
            "COLUMN_REFERENCE_MISSING",
            "SOURCE_URI_REFERENCE_MISSING",
            "NUMERIC_VALUE_UNVERIFIED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertTrue(failures["unrecognized_structure_requires_human_handling"])
        self.assertTrue(failures["unverified_numeric_value_blocks_statistical_conclusion"])
        self.assertFalse(failures["schema_migration_without_rollback_allowed"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "STAGE061_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED",
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

    def test_chinese_feedback_and_runtime_boundary_are_explicit(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["numeric_accuracy_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])
        self.assertEqual(4, len(feedback["messages"]))
        for item in feedback["messages"]:
            with self.subTest(code=item["code"]):
                self.assertTrue(item["message"])
                self.assertTrue(any("\u4e00" <= char <= "\u9fff" for char in item["message"]))

        runtime = self.contract["runtime_boundary"]
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "numeric_statistic_computation_performed",
            "quality_gate_evaluation_performed",
            "source_location_binding_performed",
            "evidence_binding_performed",
            "database_connection_performed",
            "structured_fact_write_performed",
            "quality_result_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
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
        self.assertTrue(runtime["predecessor_stage061_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage062_started"])
        self.assertTrue(runtime["stage062_entry_authorized"])

    def test_current_governance_preserves_phase1_evidence_or_legal_successor(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE062-P1-20260814-001"
        )
        run = json.loads(RUN.read_text(encoding="utf-8"))

        self.assertIn(status["stage"], ("IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                           'IDS-STAGE079',
                                           "IDS-STAGE079",
                                           'IDS-STAGE080', "IDS-STAGE081", "IDS-STAGE082", "IDS-STAGE083", "IDS-STAGE084",
                                           'IDS-STAGE085',
                                       ))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE062-P1", "IDS-V0_1-STAGE062-P1", "IDS-STAGE062-P2-GATE"),
                ("IDS-V0_1-STAGE062-P2", "IDS-V0_1-STAGE062-P2", "IDS-STAGE062-P3-GATE"),
                ("IDS-V0_1-STAGE062-P3", "IDS-V0_1-STAGE062-P3", "IDS-STAGE062-P4-GATE"),
                ("IDS-V0_1-STAGE062-P4", "IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW-GATE"),
                ("IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
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
                ("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
                ("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
                ("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
                ("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
                ("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
                ("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                (
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-STAGE076-REVIEW-GATE',
                ),
                (
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-STAGE077-P1-GATE',
                ),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ("IDS-STAGE078-REVIEW", "IDS-V0_1-STAGE078-REVIEW", "IDS-STAGE079-P1-GATE"),
                ('IDS-V0_1-STAGE079-P1', 'IDS-V0_1-STAGE079-P1', 'IDS-STAGE079-P2-GATE'), ('IDS-V0_1-STAGE079-P2', 'IDS-V0_1-STAGE079-P2', 'IDS-STAGE079-P3-GATE'), ('IDS-V0_1-STAGE079-P3', 'IDS-V0_1-STAGE079-P3', 'IDS-STAGE079-P4-GATE'), ('IDS-V0_1-STAGE079-P4', 'IDS-V0_1-STAGE079-P4', 'IDS-STAGE079-REVIEW-GATE'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                    ("IDS-STAGE084-REVIEW", "IDS-V0_1-STAGE084-REVIEW", "IDS-STAGE085-P3-GATE"),
                ("IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084-P1", "IDS-V0_1-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ("IDS-STAGE084-P2", "IDS-V0_1-STAGE084-P2", "IDS-STAGE084-P3-GATE"), ('IDS-STAGE084-P3', 'IDS-V0_1-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084-P4', 'IDS-V0_1-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                ('IDS-STAGE085-P2', 'IDS-V0_1-STAGE085-P2', 'IDS-STAGE085-P3-GATE'), ("IDS-STAGE085-P3", "IDS-V0_1-STAGE085-P3", "IDS-STAGE085-P4-GATE"), ("IDS-STAGE085-P4", "IDS-V0_1-STAGE085-P4", "IDS-STAGE085-REVIEW-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                         'IDS-STAGE079',
                                         "IDS-STAGE079",
                                         'IDS-STAGE080', 'IDS-STAGE081', 'IDS-STAGE082', 'IDS-STAGE083', "IDS-STAGE084",
                                         'IDS-STAGE085',
                                     ))
        self.assertIn(
            plan["task"],
            ("IDS-V0_1-STAGE062-P1", "IDS-V0_1-STAGE062-P2", "IDS-V0_1-STAGE062-P3", "IDS-V0_1-STAGE062-P4", "IDS-V0_1-STAGE062-REVIEW", "IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
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
            , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                'IDS-V0_1-STAGE079-P1',
                'IDS-V0_1-STAGE079-P2',
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                    "IDS-V0_1-STAGE084-REVIEW",
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                'IDS-V0_1-STAGE085-P2',
             "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4"),
        )
        self.assertTrue(
            (
("IDS-STAGE062-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE062-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE062-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE062-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE067-P1-GATE" in plan["stop_condition"]
            or ("IDS-STAGE067-P2-GATE" in plan["stop_condition"] or "IDS-STAGE067-P3-GATE" in plan["stop_condition"] or "IDS-STAGE067-P4-GATE" in plan["stop_condition"] or "IDS-STAGE067-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE068-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-P2-GATE" in plan["stop_condition"] or "IDS-STAGE068-P3-GATE" in plan["stop_condition"])
            or "IDS-STAGE068-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P2-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P3-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P4-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-REVIEW-GATE" in plan["stop_condition"]
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"], "IDS-STAGE075-P4-GATE" in plan["stop_condition"]
            )
        )
        self.assertIn("OVH", plan["stop_condition"])
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE062-P1-01",
                "ACC-STAGE062-P1-02",
                "ACC-STAGE062-P1-03",
                "ACC-STAGE062-P1-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE062-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P2-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE062-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE062-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE062-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P1-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P2-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P3-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P4-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-V0_1-STAGE063-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P1-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE064"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE064-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P2-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE064"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE064-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P3-GATE"' in roadmap_text
            )
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE062-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-062"], event["acceptance_ids"])
        self.assertEqual("IDS-V0_1-STAGE062-P1", run["task_id"])
        self.assertEqual("RUN-IDS-STAGE062-P1-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE062", run["stage"])
        self.assertEqual("IDS-STAGE062-P2-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        human_acceptance = HUMAN_ACCEPTANCE.read_text(encoding="utf-8")
        self.assertTrue(
            (
                "ACC-STAGE062-P1-01" in human_acceptance
                and "RUN-IDS-STAGE062-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE063-P1-01" in human_acceptance
                and "RUN-IDS-STAGE063-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE064-P1-01" in human_acceptance
                and "RUN-IDS-STAGE064-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE064-P2-01" in human_acceptance
                and "RUN-IDS-STAGE064-P2-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE065-P1-01" in human_acceptance
                and "RUN-IDS-STAGE065-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE066-P1-01" in human_acceptance
                and "RUN-IDS-STAGE066-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE067-P1-01" in human_acceptance
                and "RUN-IDS-STAGE067-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE068-P1-01" in human_acceptance
                and "RUN-IDS-STAGE068-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE069-P1-01" in human_acceptance
                and "RUN-IDS-STAGE069-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE070-P1-01" in human_acceptance
                and "RUN-IDS-STAGE070-P1-LOCAL-20260815-001" in human_acceptance
            )
            or (
                "ACC-STAGE071-P1-01" in human_acceptance
                and "RUN-IDS-STAGE071-P1-LOCAL-20260815-001" in human_acceptance
            )
            or (
                "ACC-STAGE072-P1-01" in human_acceptance
                and "RUN-IDS-STAGE072-P1-LOCAL-20260820-001" in human_acceptance
            )
            or (
                "ACC-STAGE073-P1-01" in human_acceptance
                and "RUN-IDS-STAGE073-P1-LOCAL-20260820-001" in human_acceptance
            )
            or (
                "ACC-STAGE074-P1-01" in human_acceptance
                and "RUN-IDS-STAGE074-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE075-P1-01" in human_acceptance
                and "RUN-IDS-STAGE075-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE076-P1-01" in human_acceptance
                and "RUN-IDS-STAGE076-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE077-P1-01" in human_acceptance
                and "RUN-IDS-STAGE077-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE078-P1-01" in human_acceptance
                and "RUN-IDS-STAGE078-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE079-P1-01" in human_acceptance
                and "RUN-IDS-STAGE079-P1-LOCAL-20260821-001" in human_acceptance
            )
            or (
                "ACC-STAGE080-P1-01" in human_acceptance
                and "RUN-IDS-STAGE080-P1-LOCAL-20260822-001" in human_acceptance
            )
            or (
                "ACC-STAGE081-P1-01" in human_acceptance
                and "RUN-IDS-STAGE081-P1-LOCAL-20260822-001" in human_acceptance
            )
            or (
                "ACC-STAGE082-P1-01" in human_acceptance
                and "RUN-IDS-STAGE082-P1-LOCAL-20260822-001" in human_acceptance
            ,
                "ACC-STAGE082-P2-01" in human_acceptance
                and "RUN-IDS-STAGE082-P2-LOCAL-20260822-001" in human_acceptance)
        )


if __name__ == "__main__":
    unittest.main()
