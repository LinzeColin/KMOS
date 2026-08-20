import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE068_PHASE1_QUALITY_DEGRADATION_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "quality_degradation"
    / "stage068_quality_degradation_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage068-p1-local.json"


class Stage068QualityDegradationPhase1Tests(unittest.TestCase):
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

    def test_single_authority_and_stage_ownership_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage068.quality_degradation.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-068", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE068-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-068", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_QUALITY_DEGRADATION_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE068-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE068_TASKPACK_AND_STAGE067_REVIEW_ARTIFACTS_ONLY",
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

        owners = contract["ownership_boundary"]
        self.assertEqual("STAGE-063", owners["chapter_aware_chunking_boundary_owner"])
        self.assertEqual(
            "STAGE-064", owners["chunk_identity_and_version_contract_owner"]
        )
        self.assertEqual(
            "STAGE-065",
            owners["engineering_semantic_asset_classification_contract_owner"],
        )
        self.assertEqual("STAGE-066", owners["chunk_coverage_metrics_contract_owner"])
        self.assertEqual("STAGE-067", owners["chunk_quality_regression_contract_owner"])
        self.assertEqual(
            "STAGE-068",
            owners["quality_degradation_and_human_review_contract_owner"],
        )
        self.assertTrue(owners["predecessor_stage067_review_reused_as_reference_only"])
        self.assertFalse(owners["actual_quality_degradation_created"])
        self.assertFalse(owners["cross_stage_owner_override_allowed"])

    def test_reference_only_shape_and_future_output_remain_static(self):
        inputs = self.contract["reference_only_quality_degradation_input_contract"]
        self.assertEqual(13, inputs["field_count"])
        self.assertEqual(
            [
                "quality_degradation_request_ref",
                "chapter_aware_chunk_ref",
                "chunk_identity_version_record_ref",
                "engineering_semantic_asset_catalog_ref",
                "chunk_coverage_metrics_record_ref",
                "chunk_quality_regression_record_ref",
                "document_ref",
                "page_ref",
                "section_ref",
                "parser_output_ref",
                "table_context_ref",
                "source_fragment_ref",
                "duplicate_chunk_control_ref",
            ],
            inputs["required_fields"],
        )
        self.assertFalse(inputs["additional_fields_allowed"])
        self.assertFalse(inputs["document_body_allowed"])
        self.assertFalse(inputs["physical_path_or_actual_uri_allowed"])
        self.assertFalse(inputs["page_content_allowed"])
        self.assertFalse(inputs["section_text_allowed"])
        self.assertFalse(inputs["parser_output_content_allowed"])
        self.assertFalse(inputs["source_fragment_content_allowed"])
        self.assertEqual(0, inputs["actual_input_request_count"])

        outputs = self.contract["future_quality_degradation_output_contract"]
        self.assertEqual(19, outputs["field_count"])
        self.assertEqual(
            [
                "quality_degradation_record_ref",
                "quality_degradation_request_ref",
                "chunk_quality_regression_record_ref",
                "chapter_aware_chunk_ref",
                "chunk_identity_version_record_ref",
                "engineering_semantic_asset_catalog_ref",
                "chunk_coverage_metrics_record_ref",
                "document_ref",
                "page_ref",
                "section_ref",
                "parser_output_ref",
                "table_context_ref",
                "source_fragment_ref",
                "protected_semantic_boundary_status",
                "duplicate_embedding_index_status",
                "quality_degradation_status",
                "low_confidence_evidence_state",
                "human_review_state",
                "quality_degradation_reason_code",
            ],
            outputs["required_fields"],
        )
        for field in (
            "schema_field_labels_only",
            "actual_quality_degradation_record_created",
            "actual_quality_degradation_record_persisted",
            "actual_quality_score_assigned",
            "actual_quality_threshold_assigned",
            "actual_low_confidence_evidence_assigned",
            "actual_duplicate_embedding_or_index_status_assigned",
        ):
            with self.subTest(field=field):
                self.assertTrue(outputs[field]) if field == "schema_field_labels_only" else self.assertFalse(outputs[field])

    def test_future_degradation_preserves_protected_surfaces_and_traceability(self):
        degradation = self.contract["quality_degradation_definition_contract"]
        self.assertEqual(
            [
                "REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW",
                "LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW",
            ],
            degradation["declared_future_dispositions"],
        )
        self.assertEqual(2, degradation["declared_future_disposition_count"])
        self.assertTrue(degradation["low_quality_is_not_automatically_complete_failure"])
        self.assertTrue(degradation["quality_degradation_is_future_control_only"])
        for field in (
            "quality_degradation_can_replace_source_document",
            "low_confidence_evidence_can_become_business_fact_authority",
            "automatic_business_recommendation_allowed",
            "actual_quality_measurement_performed",
            "actual_quality_regression_performed",
            "actual_quality_degradation_performed",
            "actual_low_confidence_evidence_created",
            "actual_human_review_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(degradation[field])
        self.assertTrue(degradation["quality_degradation_requires_business_line_human_review"])

        protected = self.contract["protected_semantic_boundary_contract"]
        self.assertEqual(
            ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"],
            protected["protected_semantic_asset_types"],
        )
        self.assertEqual(3, protected["protected_semantic_asset_type_count"])
        for field in (
            "arbitrary_fixed_character_cut_allowed",
            "engineering_procedure_step_split_allowed",
            "acceptance_clause_split_allowed",
            "parameter_table_split_allowed",
            "quality_degradation_can_override_source_document",
            "actual_semantic_boundary_detected",
            "actual_protected_surface_split_detected",
        ):
            with self.subTest(field=field):
                self.assertFalse(protected[field])
        self.assertTrue(protected["cross_page_parameter_table_requires_human_handling"])

        traceability = self.contract["traceability_contract"]
        self.assertEqual(
            [
                "document_ref",
                "page_ref",
                "section_ref",
                "parser_output_ref",
                "table_context_ref",
                "source_fragment_ref",
            ],
            traceability["required_traceability_fields"],
        )
        self.assertEqual(6, traceability["traceability_field_count"])
        self.assertEqual(0, traceability["actual_traceability_binding_count"])
        for field in (
            "actual_document_traceability_validated",
            "actual_page_traceability_validated",
            "actual_section_traceability_validated",
            "actual_parser_output_traceability_validated",
            "actual_table_context_traceability_validated",
            "actual_source_fragment_traceability_validated",
        ):
            with self.subTest(field=field):
                self.assertFalse(traceability[field])

    def test_duplicate_boundary_authority_and_failure_closure_are_explicit(self):
        duplicate = self.contract["duplicate_embedding_index_boundary_contract"]
        self.assertTrue(duplicate["duplicate_chunk_control_reference_required"])
        self.assertTrue(duplicate["duplicate_chunk_must_not_repeat_embedding_or_index_write"])
        for field in (
            "actual_duplicate_chunk_detected",
            "actual_duplicate_chunk_identity_or_hash_validated",
            "actual_duplicate_embedding_prevented",
            "actual_duplicate_index_prevented",
            "duplicate_embedding_or_index_write_attempted",
        ):
            with self.subTest(field=field):
                self.assertFalse(duplicate[field])

        authority = self.contract["authority_and_decision_boundary"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_human_review_required_when_unverified"])
        for field in (
            "quality_degradation_can_replace_source_document",
            "quality_degradation_can_become_business_fact_authority",
            "model_direct_text_guessing_allowed",
            "model_decision_conclusion_authoritative",
            "actual_business_decision_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(17, failures["failure_state_count"])
        self.assertIn(
            "QUALITY_DEGRADATION_DISPOSITION_REQUIRES_BUSINESS_LINE_WHITEBOX_REVIEW",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "QUALITY_DEGRADATION_REQUIRES_AUTHORIZED_EXECUTION",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_chinese_feedback_is_non_authoritative_and_runtime_is_disabled(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])
        self.assertEqual(4, len(feedback["messages"]))
        self.assertTrue(all(item["message"] for item in feedback["messages"]))

        runtime = self.contract["runtime_boundary"]
        false_fields = (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chapter_detection_performed",
            "chunking_execution_performed",
            "chunk_identity_generation_performed",
            "chunk_hash_computation_performed",
            "chunk_version_generation_performed",
            "semantic_asset_classification_performed",
            "coverage_calculation_performed",
            "quality_regression_performed",
            "quality_degradation_performed",
            "low_confidence_evidence_creation_performed",
            "source_traceability_binding_performed",
            "embedding_or_index_write_performed",
            "database_connection_performed",
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
            "stage069_started",
            "stage069_entry_allowed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_performed",
            "push_allowed",
            "app_reinstall_performed",
        )
        for field in false_fields:
            with self.subTest(field=field):
                self.assertFalse(runtime[field])
        self.assertTrue(runtime["predecessor_stage067_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage068_started"])
        self.assertTrue(runtime["stage068_entry_authorized"])

    def test_rollback_and_governance_projections_allow_phase3_successor(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "STAGE067_REVIEWED_LOCAL_CHUNK_QUALITY_REGRESSION_RUNTIME_DISABLED",
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

        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE068"', roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE068-P3"', roadmap_text)
        self.assertIn('next_gate_id: "IDS-STAGE068-P4-GATE"', roadmap_text)
        self.assertIn("stage068_phase3_completed_local", BATCH.read_text(encoding="utf-8"))

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            (plan["stage"], plan["phase"], plan["task"]),
            (
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW"),

                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"),
        )
        self.assertTrue(
            ("IDS-STAGE069-P1-GATE" in plan["stop_condition"]
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
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"]
        )
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE068-P1-01",
                "ACC-STAGE068-P1-02",
                "ACC-STAGE068-P1-03",
                "ACC-STAGE068-P1-04",
            }.issubset(acceptance_ids)
        )

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("RUN-IDS-STAGE068-P1-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE068", run["stage"])
        self.assertEqual("IDS-V0_1-STAGE068-P1", run["phase"])
        self.assertEqual("IDS-STAGE068-P2-GATE", run["next_gate"])
        self.assertEqual(
            "PASS_LOCAL_STAGE068_PHASE1_QUALITY_DEGRADATION_CONTRACT_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["runtime_boundary"]["ovh_deployment_performed"])
        self.assertFalse(run["runtime_boundary"]["model_token_consumption_performed"])


if __name__ == "__main__":
    unittest.main()
