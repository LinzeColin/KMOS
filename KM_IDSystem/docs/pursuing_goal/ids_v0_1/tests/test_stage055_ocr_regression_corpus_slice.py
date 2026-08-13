import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_contract.json"
PHASE2 = BASE / "STAGE055_PHASE2_OCR_REGRESSION_CORPUS_SLICE.md"
CONTRACT = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_slice_contract.json"
SLICE = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage055-p2-local.json"


class Stage055OcrRegressionCorpusPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage055_ocr_regression_corpus_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "regression_input_records": [
                {
                    "source_identity_ref": "source:control:stage055-p2",
                    "source_page_ref": "source-page:control:stage055-p2:1",
                    "input_class": "SCANNED_DOCUMENT_CONTROL",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "HIGH",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                    "review_route": "NO_REVIEW_QUEUE_CREATED",
                    "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage055-p2",
                    "source_page_ref": "source-page:control:stage055-p2:2",
                    "input_class": "BLURRED_DOCUMENT_CONTROL",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "LOW",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage055-p2",
                    "source_page_ref": "source-page:control:stage055-p2:3",
                    "input_class": "TABLE_DOCUMENT_CONTROL",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "MEDIUM",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                    "review_route": "NO_REVIEW_QUEUE_CREATED",
                    "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage055-p2",
                    "source_page_ref": "source-page:control:stage055-p2:4",
                    "input_class": "MIXED_ZH_EN_DOCUMENT_CONTROL",
                    "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                    "confidence_level": "MEDIUM",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage055-p2",
                    "source_page_ref": "source-page:control:stage055-p2:5",
                    "input_class": "LOW_QUALITY_DOCUMENT_CONTROL",
                    "language_profile": "UNKNOWN",
                    "confidence_level": "UNKNOWN",
                    "output_status": "OCR_PAGE_FAILED",
                    "failure_reason": "OCR_EXECUTION_NOT_STARTED",
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage055-p2:in-memory",
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
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_is_executable_but_real_ocr_and_production_remain_disabled(self):
        contract = self._contract()
        self.assertEqual("ids.stage055.ocr_regression_corpus.phase2.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE055-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE055-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(5, contract["reference_only_input_contract"]["control_record_count"])
        self.assertEqual(11, contract["per_page_output_contract"]["field_count"])
        self.assertTrue(contract["implementation"]["in_memory_ocr_regression_queue_record_created"])
        self.assertFalse(contract["implementation"]["ocr_engine_invocation_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_allowed"])

    def test_queue_and_five_page_outputs_are_created_only_in_memory(self):
        result = self._slice().execute_ocr_regression_corpus_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual("COMPLETED", result["queue_state"])
        self.assertEqual(["QUEUED", "PROCESSING", "COMPLETED"], result["queue_state_history"])
        self.assertEqual(5, result["queue_record"]["input_record_count"])
        self.assertEqual(5, result["page_output_count"])
        self.assertEqual(4, result["symbolic_control_output_count"])
        self.assertEqual(4, result["symbolic_control_page_image_reference_count"])
        self.assertTrue(result["in_memory_ocr_regression_queue_record_created"])
        self.assertTrue(result["in_memory_per_page_output_created"])
        self.assertTrue(result["in_memory_confidence_record_created"])
        self.assertFalse(result["actual_ocr_queue_created"])
        self.assertFalse(result["actual_page_output_created"])

    def test_per_page_structure_preserves_reference_and_marks_symbolic_values(self):
        result = self._slice().execute_ocr_regression_corpus_control_slice(self._control())
        page = result["page_outputs"][0]
        self.assertEqual(
            {
                "source_identity_ref",
                "source_page_ref",
                "page_image_ref",
                "ocr_text",
                "language_profile",
                "confidence_level",
                "failure_reason",
                "output_status",
                "evidence_eligibility",
                "cache_ref",
                "review_route",
            },
            set(page).intersection(
                {
                    "source_identity_ref",
                    "source_page_ref",
                    "page_image_ref",
                    "ocr_text",
                    "language_profile",
                    "confidence_level",
                    "failure_reason",
                    "output_status",
                    "evidence_eligibility",
                    "cache_ref",
                    "review_route",
                }
            ),
        )
        self.assertEqual("source-page:control:stage055-p2:1", page["source_page_ref"])
        self.assertEqual("page-image-ref:control:stage055-p2:1", page["page_image_ref"])
        self.assertEqual("CONTROL_SCANNED_DOCUMENT_OUTPUT", page["ocr_text"])
        self.assertEqual("CONTROL_SYMBOLIC_OUTPUT_NOT_REAL_OCR_TEXT", page["text_output_kind"])
        self.assertEqual("CONTROL_SYMBOLIC_PAGE_IMAGE_REFERENCE_NOT_REAL_IMAGE", page["page_image_reference_kind"])
        self.assertTrue(page["source_page_reference_preserved"])
        self.assertFalse(page["actual_ocr_text_created"])
        self.assertFalse(page["actual_page_image_reference_created"])

    def test_low_confidence_mixed_and_failed_pages_are_explicit_and_not_high_trust(self):
        result = self._slice().execute_ocr_regression_corpus_control_slice(self._control())
        blurred, mixed, failed = (
            result["page_outputs"][1],
            result["page_outputs"][3],
            result["page_outputs"][4],
        )
        self.assertEqual("OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED", blurred["page_state"])
        self.assertEqual("STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED", blurred["review_route"])
        self.assertEqual("OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED", mixed["page_state"])
        self.assertEqual("OCR_PAGE_FAILED_EXPLICIT", failed["page_state"])
        self.assertIsNone(failed["ocr_text"])
        self.assertIsNone(failed["page_image_ref"])
        self.assertEqual("CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD", failed["failure_reason_kind"])
        self.assertEqual([1, 1, 1], [result["low_confidence_page_count"], result["mixed_language_page_count"], result["failed_page_count"]])
        self.assertFalse(blurred["high_trust_direct_entry_allowed"])
        self.assertFalse(mixed["high_trust_direct_entry_allowed"])
        self.assertFalse(failed["high_trust_direct_entry_allowed"])

    def test_invalid_control_rejects_without_returning_reference_or_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_ocr_regression_corpus_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["queue_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertIsNone(result["queue_record"])
        self.assertEqual([], result["page_outputs"])
        self.assertEqual(0, result["page_output_count"])

    def test_cache_and_all_external_actions_remain_disabled(self):
        result = self._slice().execute_ocr_regression_corpus_control_slice(self._control())
        self.assertEqual("IN_MEMORY_REBUILDABLE_NOT_PERSISTED", result["cache_policy"])
        self.assertFalse(result["cache_created"])
        self.assertIsNone(result["cache_ref"])
        for field in (
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "pdf_rasterization_performed",
            "image_processing_performed",
            "table_structure_extraction_performed",
            "language_detection_performed",
            "confidence_evaluation_performed",
            "ocr_engine_selected",
            "ocr_engine_configuration_performed",
            "ocr_engine_invocation_performed",
            "ocr_engine_comparison_performed",
            "regression_execution_performed",
            "recognition_accuracy_evaluated",
            "persistent_queue_write_performed",
            "persistent_page_output_write_performed",
            "cache_write_performed",
            "cache_cleanup_performed",
            "review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "manifest_write_performed",
            "evidence_ledger_write_performed",
            "audit_write_performed",
            "report_write_performed",
            "persistent_state_write_performed",
            "database_connection_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_phase2_governance_projection_and_evidence_are_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage055_phase2_completed"'),
            (batch, "stage055_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE055-P2"'),
            (batch, 'next_gate: "IDS-STAGE055-P3-GATE"'),
            (batch, "phase2_started: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE055"'),
            (roadmap, 'current_phase_id: "IDS-STAGE055-P2"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE055-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE055-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE055", "IDS-STAGE056"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE055-P2",
                "IDS-V0_1-STAGE055-P3",
                "IDS-V0_1-STAGE055-P4",
                "IDS-V0_1-STAGE055-REVIEW",
                "IDS-V0_1-STAGE056-P1",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("PASS_PHASE2_OCR_REGRESSION_CORPUS_CONTROL_SLICE_ENGINE_DISABLED", run["result"])
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase3_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE055-P2-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE055-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-055"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE055-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
