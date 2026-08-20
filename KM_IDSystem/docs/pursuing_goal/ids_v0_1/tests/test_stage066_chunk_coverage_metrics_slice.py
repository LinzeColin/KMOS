import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_contract.json"
)
PHASE2 = BASE / "STAGE066_PHASE2_CHUNK_COVERAGE_METRICS_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "chunk_coverage_metrics"
    / "stage066_chunk_coverage_metrics_slice_contract.json"
)
SLICE = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_slice.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage066-p2-local.json"


class Stage066ChunkCoverageMetricsPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage066_chunk_coverage_metrics_slice", SLICE
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
            "chunk_coverage_metric_requests": [
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
            "ids.stage066.chunk_coverage_metrics.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE066-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE066-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE066_TASKPACK_AND_PHASE1_AND_STAGE065_REVIEW_ARTIFACTS_ONLY",
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

        inputs = contract["reference_only_chunk_coverage_input_control_contract"]
        self.assertEqual(12, inputs["field_count"])
        self.assertEqual(4, inputs["control_request_count"])
        self.assertEqual(
            ["procedure", "acceptance", "parameter_table", "unknown_denominator"],
            inputs["control_request_order"],
        )
        outputs = contract["control_chunk_coverage_metrics_record_contract"]
        self.assertEqual(17, outputs["field_count"])
        self.assertEqual(4, outputs["control_record_count"])
        self.assertTrue(
            outputs[
                "control_labels_are_not_actual_chunks_hashes_pages_ratios_or_coverage_metrics"
            ]
        )
        for field in (
            "actual_chunk_coverage_metrics_record_created",
            "actual_chunk_coverage_metrics_record_persisted",
            "actual_parse_coverage_ratio_assigned",
            "actual_chunk_coverage_ratio_assigned",
            "actual_uncovered_page_ref_assigned",
            "actual_parse_coverage_calculated",
            "actual_chunk_coverage_calculated",
            "actual_uncovered_page_detected",
        ):
            with self.subTest(field=field):
                self.assertFalse(outputs[field])

    def test_control_slice_projects_four_low_confidence_records(self):
        result = self._slice().execute_chunk_coverage_metrics_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_CHUNK_COVERAGE_METRICS_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(4, result["control_chunk_coverage_metric_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(4, result["chunk_coverage_metric_record_count"])
        self.assertEqual(
            ["procedure", "acceptance", "parameter_table", "unknown_denominator"],
            result["control_scenarios_covered"],
        )
        self.assertEqual(
            ["ENGINEERING_PROCEDURE_STEP", "ACCEPTANCE_CLAUSE", "PARAMETER_TABLE"],
            result["protected_semantic_asset_types_covered"],
        )
        self.assertTrue(result["one_control_record_per_scenario"])
        self.assertTrue(result["one_control_record_per_protected_semantic_asset_type"])
        self.assertTrue(result["all_protected_surfaces_atomic"])
        self.assertEqual(1, result["unknown_denominator_control_record_count"])
        self.assertEqual(4, result["low_confidence_control_marker_count"])
        self.assertTrue(result["all_control_records_low_confidence_requires_human_review"])

    def test_records_keep_exact_output_shape_control_labels_and_traceability(self):
        slice_module = self._slice()
        result = slice_module.execute_chunk_coverage_metrics_control_slice(self._control())
        record = result["chunk_coverage_metric_records"][0]
        self.assertEqual(
            set(slice_module.CHUNK_COVERAGE_METRIC_RECORD_FIELDS), set(record)
        )
        for field in (
            "chunk_coverage_metrics_record_ref",
            "chunk_coverage_request_ref",
            "chapter_aware_chunk_ref",
            "chunk_identity_version_record_ref",
            "engineering_semantic_asset_catalog_ref",
            "document_ref",
            "parser_output_ref",
            "parse_coverage_ratio",
            "chunk_coverage_ratio",
            "page_ref",
            "section_ref",
            "table_context_ref",
            "source_fragment_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", record[field])
        self.assertEqual(1, len(record["uncovered_page_refs"]))
        self.assertIn(":control:", record["uncovered_page_refs"][0])
        self.assertTrue(result["control_traceability_reference_shape_preserved"])
        self.assertEqual(6, result["traceability_field_count"])
        self.assertEqual(24, result["control_traceability_reference_count"])
        self.assertFalse(result["source_body_or_parser_output_or_fragment_content_retained"])
        self.assertTrue(result["control_metric_output_is_not_actual_coverage"])

    def test_real_metrics_and_external_actions_remain_closed(self):
        result = self._slice().execute_chunk_coverage_metrics_control_slice(
            self._control()
        )
        for field in (
            "actual_chapter_boundary_detected",
            "actual_protected_surface_split_detected",
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_id_generated",
            "actual_chunk_hash_computed",
            "actual_chunk_version_generated",
            "actual_parse_coverage_calculated",
            "actual_chunk_coverage_calculated",
            "actual_uncovered_page_detected",
            "actual_low_quality_chunk_detected",
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
        rejected = slice_module.execute_chunk_coverage_metrics_control_slice(unexpected)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("REJECTED", rejected["execution_state"])
        self.assertEqual([], rejected["chunk_coverage_metric_records"])
        self.assertFalse(rejected["control_coverage_metric_record_projection_performed"])

        reordered = self._control()
        reordered["chunk_coverage_metric_requests"].reverse()
        self.assertFalse(
            slice_module.execute_chunk_coverage_metrics_control_slice(reordered)[
                "input_accepted"
            ]
        )

        tampered = self._control()
        tampered["chunk_coverage_metric_requests"][0][
            "declared_document_page_set_ref"
        ] = "declared-document-page-set:control:stage066-p2:unexpected"
        self.assertFalse(
            slice_module.execute_chunk_coverage_metrics_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_chinese_feedback_and_current_governance_preserve_phase2_evidence(self):
        result = self._slice().execute_chunk_coverage_metrics_control_slice(
            self._control()
        )
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
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
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE066-P2-20260814-001"
        )

        self.assertIn(status["stage"], ("IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073"))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
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
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"), ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"),
        )
        self.assertTrue(
            ("IDS-STAGE066-P3-GATE" in plan["stop_condition"]
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
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"]
        )
        self.assertIn("OVH", plan["stop_condition"])
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE066-P2-01",
                "ACC-STAGE066-P2-02",
                "ACC-STAGE066-P2-03",
                "ACC-STAGE066-P2-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            'current_stage_id: "IDS-STAGE066"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE067"' in roadmap_text
        )
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE066-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE066-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE066-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE066-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE066-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE066-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-V0_1-STAGE067-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE067-P2-GATE"' in roadmap_text
            )
        )
        self.assertEqual("IDS-V0_1-STAGE066-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-066"], event["acceptance_ids"])
        self.assertEqual("IDS-V0_1-STAGE066-P2", run["task_id"])
        self.assertEqual("IDS-STAGE066-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])


if __name__ == "__main__":
    unittest.main()
