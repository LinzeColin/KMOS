import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_contract.json"
)
PHASE2_CONTRACT = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_scenarios.py"
)
PHASE4_CLOSEOUT = BASE / "STAGE066_PHASE4_CHUNK_COVERAGE_METRICS_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_delivery_contract.json"
)
MODULE = BASE / "chunk_coverage_metrics" / "stage066_chunk_coverage_metrics_delivery.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage066-p4-local.json"

EXPECTED_SCENARIOS = [
    "long-document-coverage-control-human-review",
    "cross-page-table-coverage-control-human-handling",
    "engineering-procedure-coverage-control-human-review",
    "parameter-table-coverage-control-human-review",
    "citation-page-coverage-control-human-confirmation",
    "duplicate-chunk-coverage-control-human-review",
]


class Stage066ChunkCoverageMetricsPhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage066_p4", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_chunk_coverage_metrics_phase4_delivery_report()
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
            "ids.stage066.chunk_coverage_metrics.phase4.delivery_contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE066-P4", contract["task_id"])
        self.assertEqual("IDS-STAGE066-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE066-REVIEW-GATE", contract["next_gate"])
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
        self.assertEqual(36, delivery["coverage_report"]["control_traceability_reference_check_count"])
        self.assertFalse(delivery["coverage_report"]["actual_chunk_coverage_calculated"])
        self.assertEqual(6, delivery["low_quality_chunk_list"]["control_item_count"])
        self.assertTrue(delivery["low_quality_chunk_list"]["all_items_require_human_review"])
        self.assertEqual(0, delivery["regression_test_results"]["silent_drop_count"])

    def test_delivery_report_is_valid_and_metadata_only(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_CHUNK_COVERAGE_METRICS_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE066-REVIEW-GATE", report["next_gate"])
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
                    "DELIVERY_METADATA_ONLY_CHUNK_COVERAGE_METRICS_JSONL_SAMPLE_NOT_REAL_CHUNK",
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
                    "actual_chunk_coverage_metrics_created",
                    "actual_parse_coverage_calculated",
                    "actual_chunk_coverage_calculated",
                    "actual_embedding_written",
                    "actual_index_written",
                ):
                    self.assertFalse(sample[field])

    def test_coverage_report_does_not_claim_real_coverage(self):
        coverage = self._report()["coverage_report"]
        self.assertTrue(coverage["control_coverage_complete"])
        self.assertTrue(coverage["control_coverage_only"])
        self.assertEqual(6, coverage["control_scenario_count"])
        self.assertEqual(4, coverage["unique_control_metric_record_count"])
        self.assertEqual(36, coverage["control_traceability_reference_check_count"])
        self.assertEqual(EXPECTED_SCENARIOS, coverage["covered_scenario_ids"])
        self.assertFalse(coverage["actual_document_coverage_calculated"])
        self.assertFalse(coverage["actual_chunk_coverage_calculated"])
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
            "CONTROLLED_CHUNK_COVERAGE_METRICS_REGRESSION_RESULT_NOT_REAL_QUALITY_REGRESSION",
            regression["result_kind"],
        )
        self.assertTrue(regression["control_regression_consistent"])
        self.assertEqual(6, regression["control_scenario_count"])
        self.assertEqual(0, regression["silent_drop_count"])
        for field in (
            "actual_quality_regression_performed",
            "actual_coverage_baseline_compared",
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
            "PASS_PHASE3_CHUNK_COVERAGE_METRICS_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["in_memory_control_replay_only"])
        self.assertTrue(rollback["phase1_phase2_phase3_artifacts_preserved"])
        for field in (
            "actual_chunk_regeneration_performed",
            "actual_chunk_version_rollback_performed",
            "actual_coverage_metrics_implementation_performed",
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
        self.assertTrue(all("确认" in item for item in report["human_confirmation_prompts_zh"]))
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(all(any("\u4e00" <= char <= "\u9fff" for char in item) for item in report["chinese_feedback"]))
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
            "github_upload_allowed",
            "push_allowed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_fails_closed_without_delivery_samples(self):
        report = self._module().build_chunk_coverage_metrics_phase4_delivery_report(
            lambda: {"valid": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_CHUNK_COVERAGE_METRICS_DELIVERY_EVIDENCE", report["result"])
        self.assertEqual("IDS-STAGE066-P4-GATE", report["next_gate"])
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE066-P4-20260814-001"
        )
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            ("IDS-STAGE066", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4"),
            (status["stage"], status["phase"], status["task"]),
        )
        self.assertEqual("IDS-STAGE066-REVIEW-GATE", status["next_gate"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertEqual("IDS-V0_1-STAGE066-P4", plan["phase"])
        self.assertIn("IDS-STAGE066-REVIEW-GATE", plan["stop_condition"])
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE066-P4-01",
                "ACC-STAGE066-P4-02",
                "ACC-STAGE066-P4-03",
                "ACC-STAGE066-P4-04",
            }.issubset(acceptance_ids)
        )
        self.assertIn('current_phase_id: "IDS-STAGE066-P4"', ROADMAP.read_text(encoding="utf-8"))
        self.assertIn('status: "stage066_phase4_completed_review_pending"', BATCH.read_text(encoding="utf-8"))
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE066-P4", event["task_id"])
        self.assertEqual("RUN-IDS-STAGE066-P4-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE066-REVIEW-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["github_upload_performed"])


if __name__ == "__main__":
    unittest.main()
