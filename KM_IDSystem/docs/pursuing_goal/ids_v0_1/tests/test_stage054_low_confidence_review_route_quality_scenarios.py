import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage054_low_confidence_review_route_contract.json"
PHASE2_CONTRACT = BASE / "ocr_queue" / "stage054_low_confidence_review_route_slice_contract.json"
EVIDENCE = BASE / "STAGE054_PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS.md"
CONTRACT = (
    BASE
    / "ocr_queue"
    / "stage054_low_confidence_review_route_quality_scenarios_contract.json"
)
SCENARIOS = (
    BASE
    / "ocr_queue"
    / "stage054_low_confidence_review_route_quality_scenarios.py"
)
P2_SLICE = BASE / "ocr_queue" / "stage054_low_confidence_review_route_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage054-p3-local.json"

EXPECTED_SCENARIOS = [
    "scanned-pdf-control-unassessed",
    "blurred-image-control-degraded",
    "table-image-control-unassessed",
    "mixed-zh-en-control-degraded",
    "low-quality-control-failed",
]


class Stage054LowConfidenceReviewRoutePhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage054_p3", SCENARIOS)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_low_confidence_review_route_phase3_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            EVIDENCE,
            CONTRACT,
            SCENARIOS,
            P2_SLICE,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_non_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage054.low_confidence_review_route.phase3.quality_scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE054-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE054-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(
            contract["scenario_input_boundary"]["actual_pdf_or_image_open_allowed"]
        )
        self.assertFalse(
            contract["scenario_input_boundary"]["recognition_accuracy_claim_allowed"]
        )
        self.assertFalse(
            contract["implementation"]["actual_human_review_route_implemented"]
        )
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_allowed"])

    def test_scenario_catalog_covers_exact_taskpack_quality_categories(self):
        contract = self._contract()
        self.assertEqual(5, contract["scenario_input_boundary"]["scenario_count"])
        self.assertEqual(
            [
                "SCANNED_PDF_CONTROL",
                "BLURRED_IMAGE_CONTROL",
                "TABLE_IMAGE_CONTROL",
                "MIXED_ZH_EN_CONTROL",
                "LOW_QUALITY_CONTROL",
            ],
            contract["scenario_input_boundary"]["scenario_categories"],
        )
        self.assertTrue(
            contract["review_route_scenario_validation"]
            ["all_taskpack_quality_categories_covered"]
        )
        self.assertTrue(
            contract["scenario_input_boundary"]["scenario_category_is_control_metadata"]
        )

    def test_all_controlled_quality_scenarios_are_explicit(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(
            EXPECTED_SCENARIOS,
            [item["scenario_id"] for item in report["scenario_results"]],
        )

    def test_scanned_pdf_and_table_controls_remain_unassessed_candidates(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        scanned = report_by_id["scanned-pdf-control-unassessed"]
        self.assertEqual(
            "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
            scanned["quality_disposition"],
        )
        self.assertFalse(scanned["automatic_review_route_state_created_in_memory"])
        table = report_by_id["table-image-control-unassessed"]
        self.assertEqual(
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            table["quality_disposition"],
        )
        self.assertFalse(table["table_structure_extraction_performed"])
        self.assertFalse(table["recognition_accuracy_evaluated"])
        self.assertFalse(table["high_trust_direct_entry_allowed"])

    def test_blurred_image_is_degraded_to_an_automatic_in_memory_candidate(self):
        item = next(
            result
            for result in self._report()["scenario_results"]
            if result["scenario_id"] == "blurred-image-control-degraded"
        )
        self.assertEqual("LOW", item["expected_confidence_level"])
        self.assertEqual(
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_CANDIDATE_ONLY",
            item["quality_disposition"],
        )
        self.assertTrue(item["automatic_review_route_state_created_in_memory"])
        self.assertTrue(item["degraded_evidence_candidate_only"])
        self.assertFalse(item["human_review_task_created"])
        self.assertFalse(item["high_trust_direct_entry_allowed"])

    def test_mixed_language_and_low_quality_controls_have_explicit_outcomes(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        mixed = report_by_id["mixed-zh-en-control-degraded"]
        self.assertEqual(
            "SIMPLIFIED_CHINESE_AND_ENGLISH", mixed["expected_language_profile"]
        )
        self.assertEqual(
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_CANDIDATE_ONLY",
            mixed["quality_disposition"],
        )
        self.assertTrue(mixed["automatic_review_route_state_created_in_memory"])
        failed = report_by_id["low-quality-control-failed"]
        self.assertEqual("FAILED_PAGE_REVIEW_REQUIRED", failed["route_state"])
        self.assertEqual(
            "FAILED_PAGE_DEGRADED_EVIDENCE_CANDIDATE_ONLY",
            failed["quality_disposition"],
        )
        self.assertFalse(failed["high_trust_direct_entry_allowed"])

    def test_report_retains_no_sample_or_candidate_payload(self):
        report = self._report()
        report_text = repr(report)
        for forbidden_fragment in (
            "review_request_candidate",
            "OCR_EXECUTION_NOT_STARTED",
            "CONTROL_REFERENCE_ONLY_NOT_REAL_OCR_OUTPUT",
        ):
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, report_text)
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["control_scenario_metadata_only"])
                self.assertFalse(item["actual_ocr_text_created"])
                self.assertFalse(item["actual_pdf_or_image_opened"])

    def test_cache_boundary_and_all_external_actions_remain_disabled(self):
        report = self._report()
        self.assertTrue(report["cache_boundary_preserved"])
        self.assertEqual(0, report["temporary_artifact_count"])
        self.assertEqual("NO_TEMPORARY_ARTIFACT_CREATED", report["cache_cleanup_action"])
        self.assertFalse(report["cache_capacity_evaluation_performed"])
        self.assertFalse(report["cache_cleanup_execution_performed"])
        for field in (
            "real_pdf_or_image_opened",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "pdf_rasterization_performed",
            "image_processing_performed",
            "table_structure_extraction_performed",
            "recognition_accuracy_evaluated",
            "ocr_engine_selected",
            "ocr_engine_invocation_performed",
            "human_review_queue_write_performed",
            "automatic_human_review_assignment_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_result_stays_non_passing(self):
        report = self._module().build_low_confidence_review_route_phase3_report(
            lambda _: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS", report["result"]
        )
        self.assertEqual(0, report["passed_scenario_count"])

    def test_contract_and_governance_projection_preserve_phase3(self):
        contract = self._contract()
        self.assertTrue(contract["implementation"]["phase2_control_route_reexecuted"])
        self.assertFalse(contract["implementation"]["actual_ocr_quality_evaluation_implemented"])
        self.assertEqual("STAGE-056", contract["cache_boundary"]["cache_retention_owner"])

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage054_phase3_completed"'),
            (batch, "stage054_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE054-P3"'),
            (batch, 'next_gate: "IDS-STAGE054-P4-GATE"'),
            (batch, "controlled_low_confidence_review_route_quality_scenarios_evaluated: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE054"'),
            (roadmap, 'current_phase_id: "IDS-STAGE054-P3"'),
            (roadmap, 'next_gate_id: "IDS-STAGE054-P4-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE054", "IDS-STAGE055", "IDS-STAGE056", "IDS-STAGE057", "IDS-STAGE058"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE054-P3",
                "IDS-V0_1-STAGE054-P4",
                "IDS-V0_1-STAGE054-REVIEW",
                "IDS-V0_1-STAGE055-P1",
                "IDS-V0_1-STAGE055-P2",
                "IDS-V0_1-STAGE055-P3",
                "IDS-V0_1-STAGE055-P4",
                "IDS-V0_1-STAGE055-REVIEW",
                "IDS-V0_1-STAGE056-P1",
                "IDS-V0_1-STAGE056-P2",
                "IDS-V0_1-STAGE056-P3",
                "IDS-V0_1-STAGE056-P4",
                "IDS-V0_1-STAGE056-REVIEW",
                "IDS-V0_1-STAGE057-P1",
                "IDS-V0_1-STAGE057-P2",
                "IDS-V0_1-STAGE057-P3",
            "IDS-V0_1-STAGE057-P4",
            "IDS-V0_1-STAGE057-REVIEW",
            "IDS-V0_1-STAGE058-P1",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(
            run["observed_work"]
            ["controlled_low_confidence_review_route_quality_scenarios_evaluated"]
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["human_review_task_created"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase4_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE054-P3-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE054-P3", event["task_id"])
        self.assertEqual(["ACC-STAGE-054"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE054-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
