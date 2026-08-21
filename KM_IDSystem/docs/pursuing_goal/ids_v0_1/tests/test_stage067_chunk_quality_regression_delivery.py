import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "chunk_quality_regression" / "stage067_chunk_quality_regression_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "chunk_quality_regression"
    / "stage067_chunk_quality_regression_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE
    / "chunk_quality_regression"
    / "stage067_chunk_quality_regression_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "chunk_quality_regression" / "stage067_chunk_quality_regression_scenarios.py"
)
PHASE4_CLOSEOUT = BASE / "STAGE067_PHASE4_CHUNK_QUALITY_REGRESSION_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "chunk_quality_regression"
    / "stage067_chunk_quality_regression_delivery_contract.json"
)
MODULE = (
    BASE / "chunk_quality_regression" / "stage067_chunk_quality_regression_delivery.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage067-p4-local.json"

EXPECTED_SCENARIOS = [
    "long-document-chunk-quality-control-human-review",
    "cross-page-table-chunk-quality-control-human-handling",
    "engineering-procedure-chunk-quality-control-human-review",
    "parameter-table-chunk-quality-control-human-review",
    "citation-page-chunk-quality-control-human-confirmation",
    "duplicate-chunk-quality-control-human-review",
]


class Stage067ChunkQualityRegressionPhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage067_p4", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_chunk_quality_regression_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE4_CLOSEOUT,
            CONTRACT,
            MODULE,
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

    def test_contract_identity_delivery_boundary_and_authority(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage067.chunk_quality_regression.phase4.delivery_contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE067-P4", contract["task_id"])
        self.assertEqual("IDS-STAGE067-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE067-REVIEW-GATE", contract["next_gate"])
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertTrue(
            contract["predecessor_boundary"]
            ["phase3_controlled_scenarios_reused_as_reference_only"]
        )
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertTrue(contract["source_authority"]["source_document_remains_authoritative"])

    def test_contract_covers_all_required_delivery_items(self):
        delivery = self._contract()["delivery_artifacts"]
        self.assertEqual(6, delivery["chunk_jsonl_samples"]["sample_count"])
        self.assertTrue(delivery["chunk_jsonl_samples"]["metadata_only"])
        self.assertFalse(delivery["chunk_jsonl_samples"]["actual_jsonl_file_written"])
        self.assertEqual(
            36, delivery["coverage_report"]["control_traceability_reference_check_count"]
        )
        self.assertFalse(
            delivery["coverage_report"]["actual_chunk_quality_regression_performed"]
        )
        self.assertEqual(6, delivery["low_quality_chunk_list"]["control_item_count"])
        self.assertTrue(delivery["low_quality_chunk_list"]["all_items_require_human_review"])
        self.assertEqual(0, delivery["regression_test_results"]["silent_drop_count"])

    def test_delivery_report_is_valid_and_metadata_only(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_CHUNK_QUALITY_REGRESSION_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE067-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertFalse(report["actual_jsonl_file_written"])
        self.assertEqual(6, len(report["chunk_jsonl_samples"]))
        self.assertEqual(6, len(report["chunk_jsonl_sample_lines"]))

    def test_jsonl_samples_preserve_control_references_only(self):
        report = self._report()
        samples = report["chunk_jsonl_samples"]
        self.assertEqual(EXPECTED_SCENARIOS, [item["scenario_id"] for item in samples])
        for sample, line in zip(samples, report["chunk_jsonl_sample_lines"]):
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(sample, json.loads(line))
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_CHUNK_QUALITY_REGRESSION_JSONL_SAMPLE_NOT_REAL_CHUNK",
                    sample["sample_kind"],
                )
                self.assertTrue(sample["human_review_required"])
                self.assertTrue(sample["control_metadata_only"])
                self.assertFalse(sample["source_content_retained"])
                for field in (
                    "actual_chunk_created",
                    "actual_chunk_identifier_generated",
                    "actual_chunk_hash_computed",
                    "actual_chunk_version_generated",
                    "actual_chunk_quality_regression_created",
                    "actual_quality_measurement_performed",
                    "actual_quality_regression_performed",
                    "actual_embedding_written",
                    "actual_index_written",
                ):
                    self.assertFalse(sample[field])

    def test_coverage_report_does_not_claim_real_quality(self):
        coverage = self._report()["coverage_report"]
        self.assertTrue(coverage["control_delivery_coverage_complete"])
        self.assertTrue(coverage["control_delivery_coverage_only"])
        self.assertEqual(6, coverage["control_scenario_count"])
        self.assertEqual(4, coverage["unique_control_quality_regression_record_count"])
        self.assertEqual(36, coverage["control_traceability_reference_check_count"])
        self.assertEqual(EXPECTED_SCENARIOS, coverage["covered_scenario_ids"])
        self.assertFalse(coverage["actual_document_quality_validated"])
        self.assertFalse(coverage["actual_chunk_quality_regression_performed"])
        self.assertFalse(coverage["coverage_can_support_real_quality_claim"])

    def test_low_quality_list_requires_human_review_without_measurement_claim(self):
        items = self._report()["low_quality_chunk_list"]
        self.assertEqual(6, len(items))
        self.assertEqual(EXPECTED_SCENARIOS, [item["scenario_id"] for item in items])
        for item in items:
            with self.subTest(item=item["record_id"]):
                self.assertEqual(
                    "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW",
                    item["quality_disposition"],
                )
                self.assertIn("人工", item["recommendation_zh"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["actual_low_quality_chunk_observed"])
                self.assertFalse(item["actual_quality_measurement_performed"])
                self.assertFalse(item["automatic_quality_degradation_action_performed"])

    def test_regression_results_are_control_only(self):
        regression = self._report()["regression_test_results"]
        self.assertEqual(
            "CONTROLLED_CHUNK_QUALITY_REGRESSION_REGRESSION_RESULT_NOT_REAL_QUALITY_REGRESSION",
            regression["result_kind"],
        )
        self.assertTrue(regression["control_regression_consistent"])
        self.assertEqual(6, regression["control_scenario_count"])
        self.assertEqual(0, regression["silent_drop_count"])
        for field in (
            "actual_quality_regression_performed",
            "actual_quality_baseline_compared",
            "actual_duplicate_chunk_checked",
            "actual_embedding_or_index_write_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(regression[field])

    def test_strategy_boundary_and_rollback_are_closed(self):
        report = self._report()
        boundary = report["chunking_strategy_applicability_boundary"]
        rollback = report["regeneration_and_version_rollback_instructions"]
        self.assertTrue(boundary["strategy_boundary_is_control_metadata_only"])
        self.assertTrue(boundary["unverified_boundary_cannot_trigger_automatic_chunk_write"])
        self.assertFalse(boundary["actual_strategy_applicability_validated"])
        self.assertFalse(boundary["actual_production_quality_claim_allowed"])
        self.assertEqual(
            "PASS_PHASE3_CHUNK_QUALITY_REGRESSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["in_memory_control_replay_only"])
        self.assertTrue(rollback["phase1_phase2_phase3_artifacts_preserved"])
        for field in (
            "actual_chunk_regeneration_performed",
            "actual_chunk_version_rollback_performed",
            "actual_quality_regression_delivery_implementation_performed",
            "source_or_raw_data_change_allowed",
            "fixture_change_allowed",
            "database_schema_change_allowed",
            "persistent_runtime_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

    def test_chinese_feedback_and_runtime_boundary_are_explicit(self):
        report = self._report()
        self.assertEqual(3, len(report["human_confirmation_prompts_zh"]))
        self.assertTrue(
            all("确认" in item for item in report["human_confirmation_prompts_zh"])
        )
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in item)
                for item in report["chinese_feedback"]
            )
        )
        for field in (
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
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage068_started",
            "stage068_entry_allowed",
            "github_upload_allowed",
            "push_allowed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_fails_closed_without_delivery_samples(self):
        report = self._module().build_chunk_quality_regression_phase4_delivery_report(
            lambda: {"valid": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_CHUNK_QUALITY_REGRESSION_DELIVERY_EVIDENCE", report["result"]
        )
        self.assertEqual("IDS-STAGE067-P4-GATE", report["next_gate"])
        self.assertFalse(report["phase3_controlled_scenarios_report_valid"])
        self.assertEqual([], report["chunk_jsonl_samples"])
        self.assertEqual((), report["chunk_jsonl_sample_lines"])
        self.assertEqual([], report["low_quality_chunk_list"])

    def test_governance_projection_records_phase4_local_only(self):
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE067-P4-20260814-001"
        )
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE067",
                    "IDS-V0_1-STAGE067-P4",
                    "IDS-V0_1-STAGE067-P4",
                    "IDS-STAGE067-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE067",
                    "IDS-V0_1-STAGE067-REVIEW",
                    "IDS-V0_1-STAGE067-REVIEW",
                    "IDS-STAGE068-P1-GATE",
                ),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
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
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE')
            ,
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["phase"],
            ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
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
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3"),
        )
        self.assertIn(
            plan["task"],
            ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
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
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3"),
        )
        self.assertTrue(
            (
("IDS-STAGE067-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-P2-GATE" in plan["stop_condition"] or "IDS-STAGE068-P3-GATE" in plan["stop_condition"]
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
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE067-P4-01",
                "ACC-STAGE067-P4-02",
                "ACC-STAGE067-P4-03",
                "ACC-STAGE067-P4-04",
            }.issubset(acceptance_ids)
        )
        self.assertTrue(
            'current_phase_id: "IDS-STAGE067-P4"'
            in ROADMAP.read_text(encoding="utf-8")
            or 'current_phase_id: "IDS-V0_1-STAGE067-REVIEW"'
            in ROADMAP.read_text(encoding="utf-8")
        )
        self.assertTrue(
            'status: "stage067_phase4_completed_review_pending"'
            in BATCH.read_text(encoding="utf-8")
            or 'status: "stage067_completed_reviewed_local"'
            in BATCH.read_text(encoding="utf-8")
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE067-P4", event["task_id"])
        self.assertEqual("RUN-IDS-STAGE067-P4-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE067-REVIEW-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["github_upload_performed"])


if __name__ == "__main__":
    unittest.main()
