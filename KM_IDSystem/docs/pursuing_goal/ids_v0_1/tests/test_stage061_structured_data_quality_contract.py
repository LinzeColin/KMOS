import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE061_PHASE1_STRUCTURED_DATA_QUALITY_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
PREDECESSOR_BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage061-p1-local.json"
HUMAN_ACCEPTANCE = ROOT / "文档" / "05_执行与验收.md"


class Stage061StructuredDataQualityContractPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_and_contract_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            BATCH,
            PREDECESSOR_BATCH,
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
            "ids.stage061.structured_data_quality.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-061", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE061-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-061", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_STRUCTURED_DATA_QUALITY_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE061-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_AND_BATCH051_060_REVIEW_ARTIFACTS_ONLY",
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

    def test_reference_only_quality_inputs_are_content_free(self):
        input_contract = self.contract["reference_only_quality_input_contract"]
        self.assertEqual(16, input_contract["field_count"])
        self.assertEqual(
            [
                "quality_request_ref",
                "source_identity_ref",
                "source_document_ref",
                "file_format",
                "workbook_ref",
                "worksheet_ref",
                "header_row_ref",
                "row_range_ref",
                "column_range_ref",
                "schema_profile_ref",
                "fact_set_ref",
                "field_candidate_ref",
                "primary_key_ref",
                "record_type",
                "evidence_ref",
                "quality_profile_ref",
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

    def test_future_output_and_quality_dimensions_are_declared_only(self):
        output = self.contract["future_quality_result_output_contract"]
        self.assertEqual(18, output["field_count"])
        self.assertEqual(
            [
                "quality_result_ref",
                "quality_request_ref",
                "quality_dimension",
                "quality_state",
                "field_candidate_ref",
                "primary_key_ref",
                "source_identity_ref",
                "source_document_ref",
                "workbook_ref",
                "worksheet_ref",
                "header_row_ref",
                "row_range_ref",
                "column_range_ref",
                "fact_set_ref",
                "evidence_ref",
                "human_review_state",
                "statistical_conclusion_state",
                "remediation_state",
            ],
            output["required_fields"],
        )
        for field in (
            "additional_fields_allowed",
            "actual_quality_result_created",
            "actual_quality_result_persisted",
            "actual_quality_profile_created",
            "actual_database_schema_created",
            "direct_high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

        quality = self.contract["quality_dimension_contract"]
        self.assertEqual(
            [
                "FIELD_COMPLETENESS",
                "UNIT_CONSISTENCY",
                "DATE_VALIDITY",
                "PRIMARY_KEY_DUPLICATION",
                "OUTLIER_REVIEW",
            ],
            quality["required_quality_dimensions"],
        )
        self.assertEqual(5, quality["quality_dimension_count"])
        self.assertEqual(0, quality["actual_quality_result_count"])
        self.assertFalse(quality["automatic_quality_pass_allowed"])
        for field in (
            "field_completeness_evaluation_performed",
            "unit_consistency_evaluation_performed",
            "date_validity_evaluation_performed",
            "primary_key_duplication_evaluation_performed",
            "outlier_evaluation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(quality[field])

    def test_semantic_fields_and_numeric_authority_are_preserved(self):
        semantics = self.contract["field_semantic_contract"]
        self.assertEqual(
            [
                "measurement_value",
                "unit_ref",
                "record_date_ref",
                "equipment_ref",
                "material_ref",
                "quality_result_ref",
                "fact_type",
                "primary_key_ref",
            ],
            semantics["required_semantic_fields"],
        )
        self.assertEqual(8, semantics["semantic_field_count"])
        self.assertEqual(
            "DECIMAL_OR_INTEGER",
            semantics["field_types"]["measurement_value"]["data_type"],
        )
        self.assertTrue(semantics["field_types"]["measurement_value"]["unit_required"])
        self.assertEqual(
            "DATE_OR_DATETIME_REFERENCE",
            semantics["field_types"]["record_date_ref"]["data_type"],
        )
        self.assertEqual(
            "ENUMERATED_QUALITY_RESULT_REFERENCE",
            semantics["field_types"]["quality_result_ref"]["data_type"],
        )
        self.assertFalse(
            semantics["field_types"]["primary_key_ref"][
                "primary_key_resolution_performed"
            ]
        )
        self.assertFalse(semantics["field_identification_performed"])
        self.assertFalse(semantics["actual_field_mapping_created"])

        numeric = self.contract["numeric_fact_authority_boundary"]
        self.assertEqual(
            "DERIVED_STRUCTURED_FACT_PROJECTION_NOT_SECOND_AUTHORITATIVE_SOURCE",
            numeric["mode"],
        )
        self.assertTrue(numeric["source_document_remains_authoritative"])
        self.assertFalse(numeric["model_direct_text_guessing_allowed"])
        self.assertFalse(numeric["model_text_statistic_authoritative"])
        self.assertFalse(numeric["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertTrue(
            numeric["outlier_statistical_conclusion_requires_verified_structured_facts"]
        )
        self.assertEqual(0, numeric["actual_structured_fact_count"])
        self.assertEqual(0, numeric["actual_numeric_fact_count"])
        self.assertFalse(numeric["numeric_statistic_computation_performed"])
        self.assertFalse(numeric["structured_fact_store_created"])

        summary = self.contract["fact_and_rag_summary_boundary"]
        self.assertEqual("STAGE-060", summary["rag_summary_owner"])
        self.assertFalse(summary["summary_can_replace_structured_fact"])
        self.assertFalse(summary["summary_can_become_numeric_statistical_evidence"])
        self.assertTrue(summary["summary_requires_fact_reference_before_future_use"])

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
        self.assertEqual(11, failures["failure_state_count"])
        self.assertIn("FIELD_COMPLETENESS_UNVERIFIABLE", failures["declared_failure_states"])
        self.assertIn("DUPLICATION_STATUS_UNVERIFIABLE", failures["declared_failure_states"])
        self.assertIn("OUTLIER_BASELINE_UNAVAILABLE", failures["declared_failure_states"])
        self.assertTrue(failures["unrecognized_structure_requires_human_handling"])
        self.assertTrue(failures["unverified_numeric_value_blocks_statistical_conclusion"])
        self.assertFalse(failures["schema_migration_without_rollback_allowed"])
        self.assertFalse(failures["automatic_business_write_allowed"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "BATCH051_060_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED",
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
        self.assertTrue(runtime["predecessor_batch_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage061_started"])
        self.assertTrue(runtime["stage061_entry_authorized"])

    def test_historical_phase1_evidence_and_current_governance_preserve_a_legal_successor(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_lines = EVENTS.read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in event_lines if line.strip()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE061-P1-20260814-001"
        )
        run = json.loads(RUN.read_text(encoding="utf-8"))

        self.assertIn(status["stage"], ("IDS-STAGE061", "IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070",))
        self.assertIn(
            (status["phase"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE061-P2", "IDS-STAGE061-P3-GATE"),
                ("IDS-V0_1-STAGE061-P3", "IDS-STAGE061-P4-GATE"),
                ("IDS-V0_1-STAGE061-P4", "IDS-STAGE061-REVIEW-GATE"),
                ("IDS-V0_1-STAGE061-REVIEW", "IDS-STAGE062-P1-GATE"),
                ("IDS-V0_1-STAGE062-P1", "IDS-STAGE062-P2-GATE"),
                ("IDS-V0_1-STAGE062-P2", "IDS-STAGE062-P3-GATE"),
                ("IDS-V0_1-STAGE062-P3", "IDS-STAGE062-P4-GATE"),
                ("IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW-GATE"),
                ("IDS-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
                ("IDS-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE061", "IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070",))
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE061-P2",
                "IDS-V0_1-STAGE061-P3",
                "IDS-V0_1-STAGE061-P4",
                "IDS-V0_1-STAGE061-REVIEW",
                "IDS-V0_1-STAGE062-P1",
                "IDS-V0_1-STAGE062-P2",
                "IDS-V0_1-STAGE062-P3",
                "IDS-V0_1-STAGE062-P4",
                "IDS-V0_1-STAGE062-REVIEW",
                "IDS-V0_1-STAGE063-P1",
                "IDS-V0_1-STAGE063-P2",
                "IDS-V0_1-STAGE063-P3",
                "IDS-V0_1-STAGE063-P4",
                "IDS-V0_1-STAGE063-REVIEW",
                "IDS-V0_1-STAGE064-P1",
                "IDS-V0_1-STAGE064-P2",
                "IDS-V0_1-STAGE064-P3",
                "IDS-V0_1-STAGE064-P4",
                "IDS-V0_1-STAGE064-REVIEW",
                "IDS-V0_1-STAGE065-P1",
                "IDS-V0_1-STAGE065-P2",
                "IDS-V0_1-STAGE065-P3",
                "IDS-V0_1-STAGE065-P4",
                "IDS-V0_1-STAGE065-REVIEW",
                "IDS-V0_1-STAGE066-P1",
                "IDS-V0_1-STAGE066-P2",
                "IDS-V0_1-STAGE066-P3",
                "IDS-V0_1-STAGE066-P4",
                "IDS-V0_1-STAGE066-REVIEW",
                "IDS-V0_1-STAGE067-P1",
                "IDS-V0_1-STAGE067-P2",
                "IDS-V0_1-STAGE067-P3",
                "IDS-V0_1-STAGE067-P4",
                "IDS-V0_1-STAGE067-REVIEW",
                "IDS-V0_1-STAGE068-P1",
                "IDS-V0_1-STAGE068-P2",
                "IDS-V0_1-STAGE068-P3",
                "IDS-V0_1-STAGE068-P4",
            "IDS-V0_1-STAGE068-REVIEW",
                "IDS-V0_1-STAGE069-P1",
                "IDS-V0_1-STAGE069-P2",
                "IDS-V0_1-STAGE069-P3",
                "IDS-V0_1-STAGE069-P4",
                "IDS-V0_1-STAGE069-REVIEW",

                "IDS-V0_1-STAGE070-P1","IDS-V0_1-STAGE070-P2",),
        )
        self.assertIn(status["next_gate"], plan["stop_condition"])
        self.assertIn("OVH", plan["stop_condition"])
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE061-P1-01",
                "ACC-STAGE061-P1-02",
                "ACC-STAGE061-P1-03",
                "ACC-STAGE061-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertTrue(
            {
                "ACC-STAGE061-P2-01",
                "ACC-STAGE061-P2-02",
                "ACC-STAGE061-P2-03",
                "ACC-STAGE061-P2-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            'current_stage_id: "IDS-STAGE061"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE062"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE063"' in roadmap_text
        )
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE061-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE061-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE061-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE061-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE061-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE061-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE061-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P1-GATE"' in roadmap_text
            )
            or (
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
                'current_phase_id: "IDS-STAGE063-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P2-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE063-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P3-GATE"' in roadmap_text
            )
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE061-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-061"], event["acceptance_ids"])
        self.assertEqual("IDS-V0_1-STAGE061-P1", run["task_id"])
        self.assertEqual("RUN-IDS-STAGE061-P1-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE061", run["stage"])
        self.assertEqual("IDS-STAGE061-P2-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        human_acceptance = HUMAN_ACCEPTANCE.read_text(encoding="utf-8")
        self.assertTrue(
            (
                "ACC-STAGE061-P1-01" in human_acceptance
                and "RUN-IDS-STAGE061-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE062-P1-01" in human_acceptance
                and "RUN-IDS-STAGE062-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE063-P1-01" in human_acceptance
                and "RUN-IDS-STAGE063-P1-LOCAL-20260814-001" in human_acceptance
            )
            or (
                "ACC-STAGE063-P2-01" in human_acceptance
                and "RUN-IDS-STAGE063-P2-LOCAL-20260814-001" in human_acceptance
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
            ),
            human_acceptance,
        )


if __name__ == "__main__":
    unittest.main()
