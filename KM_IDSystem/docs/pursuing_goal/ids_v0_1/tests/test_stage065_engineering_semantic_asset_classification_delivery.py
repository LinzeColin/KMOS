import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_slice_contract.json"
)
PHASE2_SLICE = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_slice.py"
)
PHASE3 = BASE / "STAGE065_PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_scenarios.py"
)
CLOSEOUT = (
    BASE / "STAGE065_PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_CLOSEOUT.md"
)
CONTRACT = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_delivery_contract.json"
)
DELIVERY = (
    BASE
    / "engineering_semantic_asset_classification"
    / "stage065_engineering_semantic_asset_classification_delivery.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage065-p4-local.json"

EXPECTED_SCENARIO_IDS = [
    "long-document-semantic-asset-control-human-review",
    "cross-page-parameter-table-semantic-asset-control-human-handling",
    "engineering-procedure-semantic-asset-control-human-review",
    "parameter-table-semantic-asset-control-human-review",
    "citation-page-semantic-asset-control-human-confirmation",
    "duplicate-semantic-asset-embedding-index-control-human-review",
]


class Stage065EngineeringSemanticAssetClassificationPhase4DeliveryTests(
    unittest.TestCase
):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage065_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_engineering_semantic_asset_classification_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            PHASE3,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            CLOSEOUT,
            CONTRACT,
            DELIVERY,
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

    def test_contract_identity_and_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage065.engineering_semantic_asset_classification.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual(
            "PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-V0_1-STAGE065-P4", contract["task_id"])
        self.assertTrue(contract["delivery_evidence_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE065-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["ownership_boundary"]
            ["stage065_phase1_phase2_phase3_reused_as_reference_only"]
        )
        boundary = contract["delivery_boundary"]
        self.assertEqual(6, boundary["control_scenario_count"])
        self.assertEqual(6, boundary["chunk_jsonl_sample_count"])
        self.assertEqual(4, boundary["unique_control_semantic_asset_record_count"])
        self.assertEqual(36, boundary["control_traceability_reference_check_count"])
        self.assertTrue(boundary["chunk_jsonl_samples_are_metadata_only"])
        self.assertFalse(boundary["actual_chunk_jsonl_written"])
        self.assertFalse(contract["runtime_boundary"]["ovh_deployment_performed"])

    def test_delivery_report_derives_six_metadata_only_jsonl_samples(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE065-REVIEW-GATE", report["next_gate"])
        self.assertEqual(6, report["chunk_jsonl_sample_count"])
        self.assertEqual(
            EXPECTED_SCENARIO_IDS,
            [item["scenario_id"] for item in report["chunk_jsonl_samples"]],
        )

    def test_jsonl_samples_preserve_control_references_without_real_chunk_content(self):
        samples = self._report()["chunk_jsonl_samples"]
        lines = self._report()["chunk_jsonl_sample_lines"]
        self.assertEqual(len(samples), len(lines))
        for sample, line in zip(samples, lines):
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_JSONL_SAMPLE_NOT_REAL_CHUNK",
                    sample["sample_kind"],
                )
                self.assertEqual(sample, json.loads(line))
                self.assertTrue(sample["control_metadata_only"])
                self.assertTrue(sample["human_review_required"])
                self.assertFalse(sample["source_content_retained"])
                self.assertFalse(sample["actual_chunk_created"])
                self.assertFalse(sample["actual_chunk_id_generated"])
                self.assertFalse(sample["actual_chunk_hash_computed"])
                self.assertFalse(sample["actual_chunk_version_generated"])
                self.assertFalse(sample["actual_semantic_asset_classification_created"])
                self.assertFalse(sample["actual_embedding_written"])
                self.assertFalse(sample["actual_index_written"])
                self.assertEqual(6, sample["control_traceability_reference_count"])
                self.assertTrue(sample["control_traceability_reference_preserved"])
                self.assertIn(
                    ":control:", sample["semantic_asset_classification_record_ref"]
                )
                self.assertIn(":control:", sample["chunk_identity_version_record_ref"])
                self.assertIn(":control:", sample["chapter_aware_chunk_ref"])

    def test_coverage_report_is_complete_control_coverage_not_real_coverage(self):
        coverage = self._report()["coverage_report"]
        self.assertEqual(
            "CONTROLLED_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_COVERAGE_REPORT_NOT_REAL_COVERAGE",
            coverage["report_kind"],
        )
        self.assertEqual(6, coverage["control_scenario_count"])
        self.assertEqual(6, coverage["chunk_jsonl_sample_count"])
        self.assertEqual(4, coverage["unique_control_semantic_asset_record_count"])
        self.assertEqual(36, coverage["control_traceability_reference_check_count"])
        self.assertTrue(coverage["control_coverage_complete"])
        self.assertTrue(coverage["control_coverage_only"])
        self.assertFalse(coverage["actual_document_coverage_calculated"])
        self.assertFalse(coverage["actual_chunk_coverage_calculated"])
        self.assertFalse(coverage["coverage_can_support_real_quality_claim"])

    def test_low_quality_chunk_list_stays_human_control_only(self):
        records = self._report()["low_quality_chunk_list"]
        self.assertEqual(6, len(records))
        for record in records:
            with self.subTest(record=record["record_id"]):
                self.assertEqual(
                    "CONTROLLED_LOW_QUALITY_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_LIST_NOT_REAL_QUALITY_MEASUREMENT",
                    record["record_kind"],
                )
                self.assertEqual(
                    "CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW",
                    record["quality_disposition"],
                )
                self.assertTrue(record["human_handling_required"])
                self.assertTrue(record["control_metadata_only"])
                self.assertIn("人工", record["recommendation_zh"])
                self.assertFalse(record["actual_low_quality_chunk_observed"])
                self.assertFalse(record["actual_quality_measurement_performed"])
                self.assertFalse(record["automatic_quality_degradation_action_performed"])

    def test_regression_result_reuses_control_outcome_only(self):
        result = self._report()["regression_test_results"]
        self.assertEqual(
            "CONTROLLED_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_REGRESSION_RESULT_NOT_REAL_QUALITY_REGRESSION",
            result["report_kind"],
        )
        self.assertEqual(6, result["control_scenario_count"])
        self.assertEqual(6, result["passed_control_scenario_count"])
        self.assertEqual(0, result["silent_drop_count"])
        self.assertTrue(result["control_regression_consistent"])
        self.assertFalse(result["actual_quality_regression_performed"])
        self.assertFalse(
            result["actual_engineering_semantic_asset_quality_baseline_loaded"]
        )
        self.assertFalse(result["actual_duplicate_detection_performed"])
        self.assertFalse(result["actual_embedding_or_index_write_performed"])

    def test_strategy_boundary_and_rollback_are_non_operational(self):
        boundary = self._report()["strategy_applicability_boundary"]
        self.assertTrue(boundary["fixed_control_scenarios_only"])
        self.assertTrue(boundary["long_document_requires_human_boundary_review"])
        self.assertTrue(boundary["cross_page_parameter_table_requires_human_handling"])
        self.assertTrue(boundary["unverified_boundary_cannot_trigger_automatic_chunk_write"])
        self.assertFalse(
            boundary[
                "actual_engineering_semantic_asset_classification_strategy_applicability_validated"
            ]
        )
        self.assertFalse(boundary["actual_production_acceptance_claim_allowed"])

        instructions = self._report()["regeneration_and_version_rollback_instructions"]
        self.assertEqual(
            "ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_REGENERATION_AND_VERSION_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY",
            instructions["record_kind"],
        )
        self.assertEqual(
            "PHASE3_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            instructions["return_to"],
        )
        self.assertTrue(instructions["in_memory_control_replay_only"])
        self.assertFalse(instructions["actual_chunk_regeneration_performed"])
        self.assertFalse(instructions["actual_chunk_version_rollback_performed"])
        self.assertFalse(
            instructions[
                "actual_engineering_semantic_asset_classification_implementation_performed"
            ]
        )
        self.assertFalse(instructions["source_or_raw_data_change_allowed"])
        self.assertFalse(instructions["database_or_persistent_state_change_allowed"])
        self.assertFalse(instructions["embedding_or_index_write_allowed"])

    def test_chinese_prompts_require_human_confirmation_without_auto_action(self):
        prompts = self._report()["human_confirmation_prompts_zh"]
        self.assertEqual(3, len(prompts))
        for prompt in prompts:
            with self.subTest(prompt=prompt["prompt_id"]):
                self.assertIn("请", prompt["text"])
                self.assertFalse(prompt["automatic_confirmation_performed"])

    def test_all_runtime_side_effects_remain_false(self):
        report = self._report()
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
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_fails_closed(self):
        report = self._module().build_engineering_semantic_asset_classification_phase4_delivery_report(
            lambda: {"valid": True, "result": "tampered"}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_ENGINEERING_SEMANTIC_ASSET_CLASSIFICATION_DELIVERY_EVIDENCE",
            report["result"],
        )
        self.assertEqual([], report["chunk_jsonl_samples"])
        self.assertEqual([], report["low_quality_chunk_list"])

    def test_governance_projection_preserves_phase4_delivery(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(status["stage"], ("IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                           'IDS-STAGE079',
                                           "IDS-STAGE079"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
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
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068",
     "IDS-STAGE069",

     "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                         "IDS-STAGE079"))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
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
                ('IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4")),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"),
        )
        self.assertTrue(
            (
("IDS-STAGE065-REVIEW-GATE" in plan["stop_condition"]
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
                "ACC-STAGE065-P4-01",
                "ACC-STAGE065-P4-02",
                "ACC-STAGE065-P4-03",
                "ACC-STAGE065-P4-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE065-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE065-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-V0_1-STAGE065-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE066-P1-GATE"' in roadmap_text
            )
        )
        batch_text = BATCH.read_text(encoding="utf-8")
        self.assertTrue(
            'status: "stage065_phase4_completed_review_pending"' in batch_text
            or 'status: "stage065_completed_reviewed_local"' in batch_text
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE065-P4-20260814-001"
                for item in events
            )
        )
        self.assertEqual("RUN-IDS-STAGE065-P4-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE065-P4", run["task_id"])
        self.assertEqual("IDS-STAGE065-REVIEW-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))


if __name__ == "__main__":
    unittest.main()
