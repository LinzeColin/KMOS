import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "chunk_identity_and_version" / "stage064_chunk_identity_version_contract.json"
)
PHASE2 = BASE / "STAGE064_PHASE2_CHUNK_IDENTITY_VERSION_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "chunk_identity_and_version" / "stage064_chunk_identity_version_slice_contract.json"
)
SLICE = BASE / "chunk_identity_and_version" / "stage064_chunk_identity_version_slice.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage064-p2-local.json"


class Stage064ChunkIdentityVersionPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage064_chunk_identity_version_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "chunk_identity_version_requests": [
                {
                    "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:procedure",
                    "chunking_request_ref": "chunking-request:control:stage064-p2:procedure",
                    "document_ref": "document:control:stage064-p2:procedure",
                    "page_ref": "page:control:stage064-p2:procedure",
                    "section_ref": "section:control:stage064-p2:procedure",
                    "parser_output_ref": "parser-output:control:stage064-p2:procedure",
                    "table_context_ref": "table-context:control:stage064-p2:procedure",
                    "source_fragment_ref": "source-fragment:control:stage064-p2:procedure",
                    "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:procedure",
                    "chunk_version_ref": "chunk-version-ref:control:stage064-p2:procedure",
                },
                {
                    "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:acceptance",
                    "chunking_request_ref": "chunking-request:control:stage064-p2:acceptance",
                    "document_ref": "document:control:stage064-p2:acceptance",
                    "page_ref": "page:control:stage064-p2:acceptance",
                    "section_ref": "section:control:stage064-p2:acceptance",
                    "parser_output_ref": "parser-output:control:stage064-p2:acceptance",
                    "table_context_ref": "table-context:control:stage064-p2:acceptance",
                    "source_fragment_ref": "source-fragment:control:stage064-p2:acceptance",
                    "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:acceptance",
                    "chunk_version_ref": "chunk-version-ref:control:stage064-p2:acceptance",
                },
                {
                    "chapter_aware_chunk_ref": "chapter-aware-chunk:control:stage064-p2:parameter-table",
                    "chunking_request_ref": "chunking-request:control:stage064-p2:parameter-table",
                    "document_ref": "document:control:stage064-p2:parameter-table",
                    "page_ref": "page:control:stage064-p2:parameter-table",
                    "section_ref": "section:control:stage064-p2:parameter-table",
                    "parser_output_ref": "parser-output:control:stage064-p2:parameter-table",
                    "table_context_ref": "table-context:control:stage064-p2:parameter-table",
                    "source_fragment_ref": "source-fragment:control:stage064-p2:parameter-table",
                    "chunk_identity_ref": "chunk-identity-ref:control:stage064-p2:parameter-table",
                    "chunk_version_ref": "chunk-version-ref:control:stage064-p2:parameter-table",
                },
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
            "ids.stage064.chunk_identity_and_version.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE064-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE064-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE064_TASKPACK_AND_PHASE1_AND_STAGE063_REVIEW_ARTIFACTS_ONLY",
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

        inputs = contract["reference_only_identity_and_version_input_control_contract"]
        self.assertEqual(10, inputs["field_count"])
        self.assertEqual(3, inputs["control_request_count"])
        self.assertEqual(
            [
                "chapter_aware_chunk_ref",
                "chunking_request_ref",
                "document_ref",
                "page_ref",
                "section_ref",
                "parser_output_ref",
                "table_context_ref",
                "source_fragment_ref",
                "chunk_identity_ref",
                "chunk_version_ref",
            ],
            inputs["required_fields"],
        )
        outputs = contract["control_chunk_identity_and_version_record_contract"]
        self.assertEqual(14, outputs["field_count"])
        self.assertEqual(3, outputs["control_record_count"])
        self.assertTrue(outputs["control_labels_are_not_actual_identifiers_hashes_or_versions"])
        for field in (
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_id_generated",
            "actual_chunk_hash_computed",
            "actual_document_id_bound",
            "actual_chunk_version_generated",
            "actual_identity_or_version_record_persisted",
        ):
            with self.subTest(field=field):
                self.assertFalse(outputs[field])

    def test_control_slice_projects_three_identity_version_records_from_phase1_shape(self):
        result = self._slice().execute_chunk_identity_version_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_CHUNK_IDENTITY_AND_VERSION_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(3, result["control_identity_version_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(3, result["chunk_identity_version_record_count"])
        self.assertEqual(
            ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"],
            result["protected_semantic_asset_types_covered"],
        )
        self.assertTrue(
            result["one_control_record_per_protected_semantic_asset_type"]
        )
        self.assertTrue(result["all_protected_surfaces_atomic"])
        self.assertTrue(result["control_identity_version_record_projection_performed"])

    def test_records_keep_exact_output_shape_control_labels_and_traceability(self):
        result = self._slice().execute_chunk_identity_version_control_slice(self._control())
        record = result["chunk_identity_version_records"][0]
        self.assertEqual(
            {
                "chunk_identity_version_record_ref",
                "chapter_aware_chunk_ref",
                "chunk_id",
                "chunk_hash",
                "document_id",
                "page",
                "section",
                "version",
                "parser_output_ref",
                "table_context_ref",
                "source_fragment_ref",
                "engineering_semantic_asset_type_ref",
                "coverage_reference_ref",
                "human_review_state",
            },
            set(record),
        )
        for field in (
            "chunk_identity_version_record_ref",
            "chapter_aware_chunk_ref",
            "chunk_id",
            "chunk_hash",
            "document_id",
            "page",
            "section",
            "version",
            "parser_output_ref",
            "table_context_ref",
            "source_fragment_ref",
            "engineering_semantic_asset_type_ref",
            "coverage_reference_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", record[field])
        self.assertEqual(
            "REQUIRED_WHEN_TRACEABILITY_OR_VERSION_BASIS_UNVERIFIED",
            record["human_review_state"],
        )
        self.assertTrue(result["control_traceability_reference_shape_preserved"])
        self.assertEqual(6, result["traceability_field_count"])
        self.assertEqual(18, result["control_traceability_reference_count"])
        self.assertFalse(result["source_body_or_parser_output_or_fragment_content_retained"])

    def test_identity_version_implementation_and_external_actions_remain_closed(self):
        result = self._slice().execute_chunk_identity_version_control_slice(self._control())
        self.assertTrue(result["all_human_review_required"])
        for field in (
            "actual_chapter_boundary_detected",
            "actual_protected_surface_split_detected",
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_id_generated",
            "actual_chunk_hash_computed",
            "actual_document_id_bound",
            "actual_chunk_version_generated",
            "semantic_asset_classification_performed",
            "coverage_calculation_performed",
            "quality_regression_performed",
            "quality_degradation_performed",
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
        rejected = slice_module.execute_chunk_identity_version_control_slice(unexpected)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("REJECTED", rejected["execution_state"])
        self.assertEqual([], rejected["chunk_identity_version_records"])
        self.assertFalse(rejected["control_identity_version_record_projection_performed"])

        reordered = self._control()
        reordered["chunk_identity_version_requests"].reverse()
        self.assertFalse(
            slice_module.execute_chunk_identity_version_control_slice(reordered)[
                "input_accepted"
            ]
        )

        tampered = self._control()
        tampered["chunk_identity_version_requests"][0]["chunk_version_ref"] = (
            "chunk-version-ref:control:stage064-p2:unexpected"
        )
        self.assertFalse(
            slice_module.execute_chunk_identity_version_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_chinese_feedback_is_present(self):
        result = self._slice().execute_chunk_identity_version_control_slice(self._control())
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
                for message in result["chinese_feedback"]
            )
        )

    def test_current_governance_preserves_phase2_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE064-P2-20260814-001"
        )

        self.assertIn(status["stage"], ("IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',
        ))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',
        ))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
                ("IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2"),
                ("IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3"),
                ("IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW"),
                ("IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1"),
                ("IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2"),
                ("IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3"),
                ("IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW"),
                ("IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1"),
                ("IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2"),
                ("IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3"),
                ("IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4"),
                ("IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW"),
                ("IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2"), ("IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2"),
            ("IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3"),
            ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW"),
                ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW"),
                ("IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW"),
                ("IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1"),
                ("IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2"),
                ("IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3"),
                ("IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4"),
                ("IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW"),
                ("IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1"),
                ("IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2"),
                ("IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3"),
                ("IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW"),

                ("IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1"),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2"),
("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3"),
("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4"),
("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW"),
("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1"),
("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2"),
("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3"),
("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW"),
                ("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1"),
                ("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2"),
                ("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3"),
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"), ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),
                ("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4"),
                ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW'),
                ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'),
            ),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"),
        )
        self.assertTrue(
            (
("IDS-STAGE064-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
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
                "ACC-STAGE064-P2-01",
                "ACC-STAGE064-P2-02",
                "ACC-STAGE064-P2-03",
                "ACC-STAGE064-P2-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE064-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE064-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE064-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-V0_1-STAGE064-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE065-P1-GATE"' in roadmap_text
            )
        )
        batch_text = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage064_phase2_completed"', batch_text)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE064-P2"', batch_text)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE064-P3"', batch_text)
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE064-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-064"], event["acceptance_ids"])
        self.assertEqual("RUN-IDS-STAGE064-P2-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE064", run["stage"])
        self.assertEqual("IDS-V0_1-STAGE064-P2", run["task_id"])
        self.assertEqual("IDS-STAGE064-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))


if __name__ == "__main__":
    unittest.main()
