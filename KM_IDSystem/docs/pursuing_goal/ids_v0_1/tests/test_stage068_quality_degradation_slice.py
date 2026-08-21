import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "quality_degradation" / "stage068_quality_degradation_contract.json"
)
PHASE2 = BASE / "STAGE068_PHASE2_QUALITY_DEGRADATION_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "quality_degradation" / "stage068_quality_degradation_slice_contract.json"
)
SLICE = BASE / "quality_degradation" / "stage068_quality_degradation_slice.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage068-p2-local.json"


class Stage068QualityDegradationPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage068_quality_degradation_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        module = self._slice()
        return {
            "quality_degradation_requests": [
                module.build_control_request(scenario)
                for scenario in module.CONTROL_SCENARIOS
            ]
        }

    def test_phase2_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2,
            CONTRACT,
            SLICE,
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

    def test_contract_is_executable_but_real_sources_and_runtime_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage068.quality_degradation.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE068-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE068-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE068_TASKPACK_AND_PHASE1_AND_STAGE067_REVIEW_ARTIFACTS_ONLY",
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

        inputs = contract["reference_only_quality_degradation_input_control_contract"]
        self.assertEqual(13, inputs["field_count"])
        self.assertEqual(4, inputs["control_request_count"])
        self.assertEqual(
            ["procedure", "acceptance", "parameter_table", "duplicate_chunk"],
            inputs["control_request_order"],
        )
        outputs = contract["control_quality_degradation_record_contract"]
        self.assertEqual(19, outputs["field_count"])
        self.assertEqual(4, outputs["control_record_count"])
        self.assertTrue(
            outputs[
                "control_labels_are_not_actual_chunks_hashes_pages_quality_scores_degradations_low_confidence_evidence_or_duplicates"
            ]
        )
        self.assertEqual(3, outputs["business_line_whitebox_review_record_count"])
        self.assertEqual(1, outputs["low_confidence_evidence_review_record_count"])
        for field in (
            "actual_quality_degradation_record_created",
            "actual_quality_degradation_record_persisted",
            "actual_quality_score_assigned",
            "actual_quality_threshold_assigned",
            "actual_low_confidence_evidence_created",
            "actual_duplicate_embedding_or_index_status_assigned",
            "actual_business_line_human_review_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(outputs[field])

    def test_control_slice_projects_four_low_confidence_records(self):
        result = self._slice().execute_quality_degradation_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_QUALITY_DEGRADATION_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(4, result["control_quality_degradation_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(4, result["quality_degradation_record_count"])
        self.assertEqual(
            ["procedure", "acceptance", "parameter_table", "duplicate_chunk"],
            result["control_scenarios_covered"],
        )
        self.assertEqual(
            ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"],
            result["protected_semantic_asset_types_covered"],
        )
        self.assertTrue(result["one_control_record_per_scenario"])
        self.assertTrue(result["one_control_record_per_protected_semantic_asset_type"])
        self.assertTrue(result["all_protected_surfaces_atomic"])
        self.assertEqual(1, result["duplicate_chunk_control_record_count"])
        self.assertTrue(result["duplicate_control_never_requests_embedding_or_index_write"])
        self.assertEqual(4, result["low_confidence_control_marker_count"])
        self.assertTrue(result["all_control_records_low_confidence_requires_human_review"])
        self.assertEqual(3, result["business_line_whitebox_review_record_count"])
        self.assertEqual(1, result["low_confidence_evidence_review_record_count"])
        self.assertTrue(result["low_quality_is_not_automatic_complete_failure"])

    def test_records_keep_exact_output_shape_control_labels_and_traceability(self):
        slice_module = self._slice()
        result = slice_module.execute_quality_degradation_control_slice(self._control())
        record = result["quality_degradation_records"][0]
        self.assertEqual(
            set(slice_module.QUALITY_DEGRADATION_RECORD_FIELDS), set(record)
        )
        for field in (
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
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", record[field])
        self.assertEqual(
            "CONTROL_PROTECTED_SEMANTIC_SURFACE_REQUIRES_HUMAN_HANDLING",
            record["protected_semantic_boundary_status"],
        )
        self.assertEqual(
            "CONTROL_DEGRADED_NOT_COMPLETE_FAILURE_REQUIRES_HUMAN_REVIEW",
            record["quality_degradation_status"],
        )
        self.assertEqual(
            "CONTROL_LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW",
            record["low_confidence_evidence_state"],
        )
        self.assertEqual(
            "REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW",
            record["human_review_state"],
        )
        self.assertTrue(result["control_traceability_reference_shape_preserved"])
        self.assertEqual(6, result["traceability_field_count"])
        self.assertEqual(24, result["control_traceability_reference_count"])
        self.assertFalse(result["source_body_or_parser_output_or_fragment_content_retained"])
        self.assertTrue(result["control_output_is_not_actual_quality_degradation"])

        duplicate_record = result["quality_degradation_records"][-1]
        self.assertEqual(
            "CONTROL_DUPLICATE_CHUNK_NO_EMBEDDING_OR_INDEX_WRITE_REQUIRES_HUMAN_REVIEW",
            duplicate_record["duplicate_embedding_index_status"],
        )
        self.assertEqual(
            "LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW",
            duplicate_record["human_review_state"],
        )
        self.assertEqual(
            "CONTROL_DUPLICATE_CHUNK_REQUIRES_LOW_CONFIDENCE_EVIDENCE_HUMAN_REVIEW",
            duplicate_record["quality_degradation_reason_code"],
        )

    def test_real_quality_and_external_actions_remain_closed(self):
        result = self._slice().execute_quality_degradation_control_slice(self._control())
        for field in (
            "actual_chapter_boundary_detected",
            "actual_protected_surface_split_detected",
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_id_generated",
            "actual_chunk_hash_computed",
            "actual_chunk_version_generated",
            "actual_engineering_semantic_asset_classified",
            "actual_coverage_metric_calculated",
            "actual_quality_regression_record_created",
            "actual_quality_measurement_performed",
            "actual_quality_regression_performed",
            "actual_quality_degradation_record_created",
            "actual_quality_degradation_performed",
            "actual_low_confidence_evidence_created",
            "actual_low_quality_chunk_detected",
            "actual_duplicate_chunk_detected",
            "actual_duplicate_chunk_identity_or_hash_validated",
            "actual_duplicate_embedding_prevented",
            "actual_duplicate_index_prevented",
            "duplicate_embedding_or_index_write_attempted",
            "semantic_asset_classification_performed",
            "coverage_calculation_performed",
            "quality_regression_performed",
            "quality_degradation_performed",
            "low_confidence_evidence_creation_performed",
            "source_traceability_binding_performed",
            "embedding_or_index_write_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chapter_detection_performed",
            "chunking_execution_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])
        self.assertFalse(result["model_direct_text_guessing_allowed"])

    def test_invalid_reordered_or_tampered_control_input_rejects(self):
        slice_module = self._slice()
        unexpected = self._control()
        unexpected["unexpected"] = "not accepted"
        rejected = slice_module.execute_quality_degradation_control_slice(unexpected)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("REJECTED", rejected["execution_state"])
        self.assertEqual([], rejected["quality_degradation_records"])
        self.assertFalse(rejected["control_quality_degradation_record_projection_performed"])

        reordered = self._control()
        reordered["quality_degradation_requests"].reverse()
        self.assertFalse(
            slice_module.execute_quality_degradation_control_slice(reordered)[
                "input_accepted"
            ]
        )

        tampered = self._control()
        tampered["quality_degradation_requests"][0][
            "duplicate_chunk_control_ref"
        ] = "duplicate-chunk-control:control:stage068-p2:unexpected"
        self.assertFalse(
            slice_module.execute_quality_degradation_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_chinese_feedback_and_current_governance_record_phase4(self):
        result = self._slice().execute_quality_degradation_control_slice(self._control())
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("一" <= char <= "鿿" for char in message)
                for message in result["chinese_feedback"]
            )
        )

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE068",
                    "IDS-V0_1-STAGE068-REVIEW",
                    "IDS-V0_1-STAGE068-REVIEW",
                    "IDS-STAGE069-P1-GATE",
                ),
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-P1",
                    "IDS-V0_1-STAGE069-P1",
                    "IDS-STAGE069-P2-GATE",
                ),
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-P2",
                    "IDS-V0_1-STAGE069-P2",
                    "IDS-STAGE069-P3-GATE",
                ),
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-P3",
                    "IDS-V0_1-STAGE069-P3",
                    "IDS-STAGE069-P4-GATE",
                ),
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-P4",
                    "IDS-V0_1-STAGE069-P4",
                    "IDS-STAGE069-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-STAGE070-P2-GATE",
                ),
                (
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-STAGE070-P3-GATE",
                ),
(
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-STAGE070-P4-GATE",
                ),
(
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-STAGE070-REVIEW-GATE",
                ),
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
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-STAGE070-P1-GATE",
                ), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                (
                    'IDS-STAGE076',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-STAGE076-REVIEW-GATE',
                ),
                (
                    'IDS-STAGE076',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-STAGE077-P1-GATE',
                ),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE')
            ),
        )
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
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4')),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"),
        )
        self.assertTrue(
            (
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
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"], "IDS-STAGE075-P4-GATE" in plan["stop_condition"]
            )
        )
        self.assertTrue(
            {
                "ACC-STAGE068-P2-01",
                "ACC-STAGE068-P2-02",
                "ACC-STAGE068-P2-03",
                "ACC-STAGE068-P2-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE068-P2-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE068-P2", run["task_id"])
        self.assertEqual("IDS-STAGE068-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage068_phase2", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE068-P2", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE068-P2-20260814-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
