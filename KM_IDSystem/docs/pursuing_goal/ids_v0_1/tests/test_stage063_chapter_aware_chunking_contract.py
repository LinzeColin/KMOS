import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE063_PHASE1_CHAPTER_AWARE_CHUNKING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_contract.json"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage063-p1-local.json"
HUMAN_ACCEPTANCE = ROOT / "文档" / "05_执行与验收.md"


class Stage063ChapterAwareChunkingContractPhase1Tests(unittest.TestCase):
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
        self.assertEqual("ids.stage063.chapter_aware_chunking.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-063", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE063-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-063", contract["acceptance_id"])
        self.assertEqual("PHASE1_CHAPTER_AWARE_CHUNKING_CONTRACT_RUNTIME_DISABLED", contract["contract_state"])
        self.assertEqual("IDS-STAGE063-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual("FROZEN_STAGE063_TASKPACK_AND_STAGE062_REVIEW_ARTIFACTS_ONLY", source["authority"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_reference_only_inputs_and_future_outputs_are_declared_only(self):
        inputs = self.contract["reference_only_chunking_input_contract"]
        self.assertEqual(8, inputs["field_count"])
        self.assertEqual(
            [
                "chunking_request_ref",
                "document_ref",
                "page_ref",
                "section_ref",
                "parser_output_ref",
                "table_context_ref",
                "engineering_semantic_asset_ref",
                "source_fragment_ref",
            ],
            inputs["required_fields"],
        )
        self.assertEqual(0, inputs["actual_input_request_count"])
        for field in (
            "additional_fields_allowed",
            "document_body_allowed",
            "physical_path_or_actual_uri_allowed",
            "page_content_allowed",
            "section_text_allowed",
            "table_content_allowed",
            "parser_output_content_allowed",
            "source_fragment_content_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])

        output = self.contract["future_chapter_aware_chunk_output_contract"]
        self.assertEqual(14, output["field_count"])
        self.assertEqual(
            ["document_ref", "page_ref", "section_ref", "parser_output_ref", "table_context_ref", "source_fragment_ref"],
            [field for field in output["required_fields"] if field in {"document_ref", "page_ref", "section_ref", "parser_output_ref", "table_context_ref", "source_fragment_ref"}],
        )
        for field in (
            "additional_fields_allowed",
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_identity_created",
            "actual_chunk_version_created",
            "actual_semantic_asset_classification_created",
            "actual_coverage_metric_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

    def test_protected_boundaries_traceability_and_later_stage_ownership_are_explicit(self):
        protected = self.contract["protected_semantic_boundary_contract"]
        self.assertEqual(
            ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"],
            protected["protected_semantic_asset_types"],
        )
        self.assertEqual(3, protected["protected_semantic_asset_type_count"])
        self.assertFalse(protected["arbitrary_fixed_character_cut_allowed"])
        self.assertFalse(protected["protected_surface_split_allowed"])

        traceability = self.contract["traceability_contract"]
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

        owners = self.contract["ownership_boundary"]
        self.assertEqual("STAGE-047", owners["parser_output_contract_owner"])
        self.assertEqual("STAGE-062", owners["table_evidence_binding_owner"])
        self.assertEqual("STAGE-064", owners["chunk_identity_and_version_owner"])
        self.assertEqual("STAGE-065", owners["engineering_semantic_asset_classification_owner"])
        self.assertEqual("STAGE-066", owners["chunk_coverage_metrics_owner"])
        self.assertEqual("STAGE-067", owners["chunk_quality_regression_owner"])
        self.assertEqual("STAGE-068", owners["quality_degradation_and_human_review_owner"])

    def test_authority_failure_closure_and_rollback_are_declared(self):
        authority = self.contract["authority_and_decision_boundary"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        for field in (
            "chunk_can_replace_source_document",
            "chunk_can_become_business_fact_authority",
            "model_direct_text_guessing_allowed",
            "model_decision_conclusion_authoritative",
            "actual_business_decision_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(8, failures["failure_state_count"])
        self.assertIn("SAFE_CHAPTER_BOUNDARY_UNRESOLVED", failures["declared_failure_states"])
        self.assertIn("PROTECTED_SEMANTIC_SURFACE_REQUIRES_HUMAN_HANDLING", failures["declared_failure_states"])
        self.assertTrue(failures["cross_page_parameter_table_requires_human_handling"])
        self.assertTrue(failures["unverified_traceability_blocks_chunk_output"])
        self.assertFalse(failures["automatic_business_write_allowed"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual("STAGE062_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED", rollback["return_to"])
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
            "parser_execution_performed",
            "chapter_detection_performed",
            "chunking_execution_performed",
            "chunk_hash_computation_performed",
            "semantic_asset_classification_performed",
            "coverage_calculation_performed",
            "quality_regression_performed",
            "quality_degradation_performed",
            "source_traceability_binding_performed",
            "embedding_or_index_write_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
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
        self.assertTrue(runtime["predecessor_stage062_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage063_started"])
        self.assertTrue(runtime["stage063_entry_authorized"])

    def test_current_governance_preserves_phase1_evidence_or_legal_phase2_successor(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
        event = next(item for item in events if item.get("event_id") == "EVT-IDS-V0_1-STAGE063-P1-20260814-001")
        run = json.loads(RUN.read_text(encoding="utf-8"))

        self.assertIn(status["stage"], ("IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                           'IDS-STAGE079',
                                           "IDS-STAGE079",
                                           'IDS-STAGE080'))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
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
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ('IDS-V0_1-STAGE079-P1', 'IDS-V0_1-STAGE079-P1', 'IDS-STAGE079-P2-GATE'), ('IDS-V0_1-STAGE079-P2', 'IDS-V0_1-STAGE079-P2', 'IDS-STAGE079-P3-GATE'), ('IDS-V0_1-STAGE079-P3', 'IDS-V0_1-STAGE079-P3', 'IDS-STAGE079-P4-GATE'), ('IDS-V0_1-STAGE079-P4', 'IDS-V0_1-STAGE079-P4', 'IDS-STAGE079-REVIEW-GATE'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE')),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                         "IDS-STAGE079",
                                         'IDS-STAGE080'))
        self.assertIn(plan["phase"], ("IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
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
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-STAGE078-REVIEW",
                                         "IDS-V0_1-STAGE079-P1",
                                         "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                             'IDS-STAGE079-REVIEW',

                                         'IDS-V0_1-STAGE080-P1',
                                         'IDS-V0_1-STAGE080-P2',
                                         'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4'))
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
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
                                        "IDS-V0_1-STAGE079-P1",
                                        "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                            'IDS-V0_1-STAGE079-REVIEW',

                                        'IDS-V0_1-STAGE080-P1',
                                        'IDS-V0_1-STAGE080-P2',
                                        'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4'))
        self.assertTrue(
            (
("IDS-STAGE063-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
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
        self.assertTrue({"ACC-STAGE063-P1-01", "ACC-STAGE063-P1-02", "ACC-STAGE063-P1-03", "ACC-STAGE063-P1-04"}.issubset(acceptance_ids))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            'current_stage_id: "IDS-STAGE063"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE064"' in roadmap_text
        )
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE063-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P2-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE063-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE063-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE063-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE063-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P1-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE064-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P2-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE064-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P3-GATE"' in roadmap_text
            )
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE063-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-063"], event["acceptance_ids"])
        self.assertEqual("IDS-V0_1-STAGE063-P1", run["task_id"])
        self.assertEqual("RUN-IDS-STAGE063-P1-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE063", run["stage"])
        self.assertEqual("IDS-STAGE063-P2-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        human_acceptance = HUMAN_ACCEPTANCE.read_text(encoding="utf-8")
        self.assertTrue(
            (
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
            ),
            human_acceptance,
        )


if __name__ == "__main__":
    unittest.main()
