import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_contract.json"
PHASE2_CONTRACT = (
    BASE / "ocr_queue" / "stage055_ocr_regression_corpus_slice_contract.json"
)
EVIDENCE = BASE / "STAGE055_PHASE3_OCR_REGRESSION_CORPUS_QUALITY_SCENARIOS.md"
CONTRACT = (
    BASE
    / "ocr_queue"
    / "stage055_ocr_regression_corpus_quality_scenarios_contract.json"
)
SCENARIOS = (
    BASE / "ocr_queue" / "stage055_ocr_regression_corpus_quality_scenarios.py"
)
P2_SLICE = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage055-p3-local.json"

EXPECTED_SCENARIOS = [
    "scanned-pdf-control-candidate",
    "blurred-image-control-degraded",
    "table-image-control-unassessed",
    "mixed-zh-en-control-degraded",
    "low-quality-control-failed",
]


class Stage055OcrRegressionCorpusPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage055_p3", SCENARIOS)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_ocr_regression_corpus_phase3_report()
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
            "ids.stage055.ocr_regression_corpus.phase3.quality_scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE055-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE055-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(
            contract["source_authority"]["authorized_fixture_access_performed"]
        )
        self.assertFalse(
            contract["scenario_input_boundary"]["actual_pdf_or_image_open_allowed"]
        )
        self.assertFalse(
            contract["implementation"]["actual_ocr_quality_evaluation_implemented"]
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
            contract["quality_scenario_validation"]
            ["all_taskpack_quality_categories_covered"]
        )
        self.assertTrue(
            contract["scenario_input_boundary"]["scenario_category_is_control_metadata"]
        )

    def test_all_controlled_quality_scenarios_are_explicit(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
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
        scanned = report_by_id["scanned-pdf-control-candidate"]
        self.assertEqual(
            "CANDIDATE_RETAINED_QUALITY_UNASSESSED",
            scanned["quality_disposition"],
        )
        self.assertFalse(scanned["review_required_not_queued"])
        table = report_by_id["table-image-control-unassessed"]
        self.assertEqual(
            "CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED",
            table["quality_disposition"],
        )
        self.assertFalse(table["table_structure_extraction_performed"])
        self.assertFalse(table["recognition_accuracy_evaluated"])
        self.assertFalse(table["high_trust_direct_entry_allowed"])

    def test_blurred_and_mixed_controls_are_degraded_without_a_review_task(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        blurred = report_by_id["blurred-image-control-degraded"]
        self.assertEqual("LOW", blurred["confidence_level"])
        self.assertEqual(
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            blurred["quality_disposition"],
        )
        self.assertTrue(blurred["review_required_not_queued"])
        mixed = report_by_id["mixed-zh-en-control-degraded"]
        self.assertEqual(
            "SIMPLIFIED_CHINESE_AND_ENGLISH", mixed["language_profile"]
        )
        self.assertEqual(
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
            mixed["quality_disposition"],
        )
        self.assertTrue(mixed["review_required_not_queued"])
        self.assertFalse(self._report()["human_review_task_created"])

    def test_low_quality_control_is_explicit_failed_and_not_promoted(self):
        item = next(
            result
            for result in self._report()["scenario_results"]
            if result["scenario_id"] == "low-quality-control-failed"
        )
        self.assertEqual("OCR_PAGE_FAILED_EXPLICIT", item["page_state"])
        self.assertEqual(
            "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
            item["quality_disposition"],
        )
        self.assertTrue(item["review_required_not_queued"])
        self.assertFalse(item["high_trust_direct_entry_allowed"])
        self.assertTrue(item["symbolic_output_shape_preserved"])

    def test_report_retains_no_sample_or_symbolic_ocr_payload(self):
        report = self._report()
        report_text = repr(report)
        for forbidden_fragment in (
            "CONTROL_SCANNED_DOCUMENT_OUTPUT",
            "page-image-ref:control:stage055-p2",
            "OCR_EXECUTION_NOT_STARTED",
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
            "authorized_fixture_access_performed",
            "real_pdf_or_image_opened",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "pdf_rasterization_performed",
            "image_processing_performed",
            "table_structure_extraction_performed",
            "language_detection_performed",
            "confidence_evaluation_performed",
            "recognition_accuracy_evaluated",
            "ocr_engine_selected",
            "ocr_engine_invocation_performed",
            "human_review_queue_write_performed",
            "human_review_task_created",
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
        report = self._module().build_ocr_regression_corpus_phase3_report(
            lambda _: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS",
            report["result"],
        )
        self.assertEqual(0, report["passed_scenario_count"])

    def test_contract_and_governance_projection_preserve_phase3(self):
        contract = self._contract()
        self.assertTrue(contract["implementation"]["phase2_control_slice_reexecuted"])
        self.assertFalse(contract["implementation"]["actual_human_review_route_implemented"])
        self.assertEqual("STAGE-056", contract["cache_boundary"]["cache_retention_owner"])

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage055_phase3_completed"'),
            (batch, "stage055_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE055-P3"'),
            (batch, 'next_gate: "IDS-STAGE055-P4-GATE"'),
            (batch, "controlled_ocr_regression_corpus_quality_scenarios_evaluated: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE055"'),
            (roadmap, 'current_phase_id: "IDS-STAGE055-P3"'),
            (roadmap, 'next_gate_id: "IDS-STAGE055-P4-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE055", status["stage"])
        self.assertEqual("IDS-V0_1-STAGE055-P3", status["phase"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(
            run["observed_work"]
            ["controlled_ocr_regression_corpus_quality_scenarios_evaluated"]
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE055-P3-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE055-P3", event["task_id"])
        self.assertEqual(["ACC-STAGE-055"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE055-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
