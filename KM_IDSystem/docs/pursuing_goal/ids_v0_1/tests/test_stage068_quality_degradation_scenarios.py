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
PHASE2_CONTRACT = (
    BASE / "quality_degradation" / "stage068_quality_degradation_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "quality_degradation" / "stage068_quality_degradation_slice.py"
)
PHASE3 = BASE / "STAGE068_PHASE3_QUALITY_DEGRADATION_SCENARIOS.md"
CONTRACT = (
    BASE / "quality_degradation" / "stage068_quality_degradation_scenarios_contract.json"
)
MODULE = (
    BASE / "quality_degradation" / "stage068_quality_degradation_scenarios.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage068-p3-local.json"

EXPECTED_SCENARIOS = [
    "long-document-quality-degradation-control-human-review",
    "cross-page-table-quality-degradation-control-human-handling",
    "engineering-procedure-quality-degradation-control-human-review",
    "parameter-table-quality-degradation-control-human-review",
    "citation-page-quality-degradation-control-human-confirmation",
    "duplicate-chunk-quality-degradation-control-human-review",
]


class Stage068QualityDegradationPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage068_p3", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_quality_degradation_phase3_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE3,
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

    def test_contract_identity_and_zero_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage068.quality_degradation.phase3.controlled_scenarios_contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE068-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE068-P4-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["ownership_boundary"]
            ["stage068_phase2_control_slice_reexecuted_as_reference_only"]
        )
        self.assertFalse(contract["runtime_boundary"]["quality_degradation_performed"])
        self.assertFalse(
            contract["runtime_boundary"]["production_runtime_activation_performed"]
        )

    def test_scenario_catalog_covers_frozen_taskpack_surfaces(self):
        contract = self._contract()
        boundary = contract["scenario_input_boundary"]
        self.assertEqual(4, boundary["phase2_control_record_count"])
        self.assertEqual(19, boundary["phase2_control_record_field_count"])
        self.assertEqual(6, boundary["scenario_count"])
        self.assertEqual(
            [
                "LONG_DOCUMENT_CONTROL",
                "CROSS_PAGE_TABLE_CONTROL",
                "ENGINEERING_PROCEDURE_CONTROL",
                "PARAMETER_TABLE_CONTROL",
                "CITATION_PAGE_TRACEABILITY_CONTROL",
                "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL",
            ],
            boundary["scenario_categories"],
        )
        self.assertTrue(boundary["scenario_category_is_control_metadata"])
        self.assertTrue(
            contract["scenario_validation"]["all_taskpack_special_scenarios_covered"]
        )
        self.assertTrue(
            contract["scenario_validation"]["low_quality_is_not_automatic_complete_failure"]
        )
        self.assertEqual(
            36,
            contract["scenario_validation"]["control_traceability_reference_check_count"],
        )

    def test_controlled_scenarios_are_explicit_and_passing(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE3_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(6, report["scenario_count"])
        self.assertEqual(6, report["passed_scenario_count"])
        self.assertEqual(6, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(6, report["human_handling_required_count"])
        self.assertEqual(4, report["unique_control_quality_degradation_record_count"])
        self.assertEqual(
            EXPECTED_SCENARIOS,
            [item["scenario_id"] for item in report["scenario_results"]],
        )

    def test_all_categories_keep_control_traceability_and_human_handling(self):
        report = self._report()
        self.assertEqual(36, report["control_traceability_reference_check_count"])
        self.assertTrue(report["control_traceability_reference_shape_preserved"])
        self.assertTrue(report["low_quality_is_not_automatic_complete_failure"])
        self.assertFalse(report["actual_source_document_read_performed"])
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["expectation_met"])
                self.assertTrue(item["human_handling_required"])
                self.assertTrue(item["control_traceability_reference_preserved"])
                self.assertTrue(item["control_reference_only"])
                self.assertTrue(item["control_scenario_metadata_only"])
                self.assertTrue(item["low_quality_is_not_automatic_complete_failure"])
                self.assertFalse(item["actual_page_traceability_validated"])
                self.assertFalse(item["actual_source_traceability_binding_created"])
                self.assertFalse(item["actual_quality_degradation_validated"])
                for field in (
                    "document_ref",
                    "page_ref",
                    "section_ref",
                    "parser_output_ref",
                    "table_context_ref",
                    "source_fragment_ref",
                ):
                    self.assertIn(":control:", item[field])

    def test_duplicate_boundary_does_not_claim_actual_deduplication(self):
        contract = self._contract()
        report = self._report()
        duplicate = next(
            item
            for item in report["scenario_results"]
            if item["scenario_category"] == "DUPLICATE_CHUNK_EMBEDDING_INDEX_CONTROL"
        )
        boundary = contract["duplicate_embedding_and_index_boundary"]
        self.assertTrue(boundary["control_duplicate_write_prohibition_asserted"])
        self.assertFalse(boundary["actual_duplicate_chunk_detected"])
        self.assertFalse(boundary["deduplication_effect_claim_allowed"])
        self.assertTrue(report["control_duplicate_write_prohibition_asserted"])
        self.assertFalse(report["actual_duplicate_chunk_detected"])
        self.assertFalse(report["actual_duplicate_chunk_identity_or_hash_validated"])
        self.assertFalse(report["actual_duplicate_embedding_prevented"])
        self.assertFalse(report["actual_duplicate_index_prevented"])
        self.assertFalse(duplicate["duplicate_embedding_or_index_write_attempted"])
        self.assertTrue(duplicate["deduplication_control_prohibition_asserted"])

    def test_invalid_phase2_replay_cannot_pass_the_scenario_gate(self):
        report = self._module().build_quality_degradation_phase3_report(
            lambda _control: {"input_accepted": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_QUALITY_DEGRADATION_CONTROLLED_SCENARIOS", report["result"])
        self.assertFalse(report["phase2_shape_preserved"])
        self.assertEqual(0, report["passed_scenario_count"])

    def test_runtime_and_authority_boundary_remain_closed(self):
        report = self._report()
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(
            report["quality_degradation_control_record_can_replace_source_document"]
        )
        self.assertFalse(
            report[
                "quality_degradation_control_record_can_become_business_fact_authority"
            ]
        )
        self.assertFalse(report["model_direct_text_guessing_allowed"])
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chapter_detection_performed",
            "chunking_execution_performed",
            "actual_chunk_created",
            "actual_chunk_persisted",
            "actual_chunk_id_generated",
            "actual_chunk_hash_computed",
            "actual_chunk_version_generated",
            "actual_quality_degradation_record_count",
            "actual_quality_degradation_validated",
            "actual_low_confidence_evidence_created",
            "actual_duplicate_chunk_detected",
            "actual_duplicate_chunk_identity_or_hash_validated",
            "actual_duplicate_embedding_prevented",
            "actual_duplicate_index_prevented",
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
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage069_started",
            "stage069_entry_allowed",
            "github_upload_allowed",
            "push_allowed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_governance_projection_preserves_phase3_evidence(self):
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
                ), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'),
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
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'),),
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
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"]
        )
        self.assertTrue(
            {
                "ACC-STAGE068-P3-01",
                "ACC-STAGE068-P3-02",
                "ACC-STAGE068-P3-03",
                "ACC-STAGE068-P3-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE068-P3-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE068-P3", run["task_id"])
        self.assertEqual("IDS-STAGE068-P4-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage068_phase3", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE068-P3", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE068-P3-20260814-001"
                for item in events
            )
        )

    def test_local_run_is_phase3_only(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("RUN-IDS-STAGE068-P3-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE068", run["stage"])
        self.assertEqual("IDS-V0_1-STAGE068-P3", run["task_id"])
        self.assertEqual("IDS-STAGE068-P4-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["github_upload_performed"])


if __name__ == "__main__":
    unittest.main()
