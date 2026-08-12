import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage053_per_page_ocr_output_contract.json"
PHASE2 = BASE / "STAGE053_PHASE2_PER_PAGE_OCR_OUTPUT_SLICE.md"
CONTRACT = BASE / "ocr_queue" / "stage053_per_page_ocr_output_slice_contract.json"
SLICE = BASE / "ocr_queue" / "stage053_per_page_ocr_output_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage053-p2-local.json"


class Stage053PerPageOcrOutputPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location("stage053_per_page_ocr_output_slice", SLICE)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "ocr_input_reference": {
                "source_identity_ref": "source:control:stage053-p2",
                "input_kind_hint": "SCANNED_PDF",
                "parser_output_status": "CONTROL_PER_PAGE_OCR_OUTPUT_CANDIDATE",
                "source_page_count_ref": "page-count:control:4",
                "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                "ocr_request_reason": "CONTROL_PER_PAGE_OUTPUT_SHAPE",
                "cache_policy_ref": "cache-policy:stage053-p2:in-memory",
            },
            "page_controls": [
                {
                    "page_number": 1,
                    "control_output_token": "CONTROL_ZH_PAGE",
                    "control_page_image_token": "CONTROL_PAGE_IMAGE_REFERENCE_1",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "HIGH",
                    "page_outcome": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                },
                {
                    "page_number": 2,
                    "control_output_token": "CONTROL_EN_LOW_CONFIDENCE_PAGE",
                    "control_page_image_token": "CONTROL_PAGE_IMAGE_REFERENCE_2",
                    "language_profile": "ENGLISH",
                    "confidence_level": "LOW",
                    "page_outcome": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                },
                {
                    "page_number": 3,
                    "control_output_token": "CONTROL_MIXED_ZH_EN_PAGE",
                    "control_page_image_token": "CONTROL_PAGE_IMAGE_REFERENCE_3",
                    "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                    "confidence_level": "MEDIUM",
                    "page_outcome": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                },
                {
                    "page_number": 4,
                    "control_output_token": None,
                    "control_page_image_token": None,
                    "language_profile": "UNKNOWN",
                    "confidence_level": "UNKNOWN",
                    "page_outcome": "OCR_PAGE_FAILED",
                    "failure_reason": "OCR_EXECUTION_NOT_STARTED",
                },
            ],
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
        self.assertEqual("ids.stage053.per_page_ocr_output.phase2.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE053-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE053-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(contract["implementation"]["in_memory_per_page_ocr_control_slice_implemented"])
        output = contract["per_page_output_contract"]
        self.assertEqual(11, output["field_count"])
        self.assertTrue(output["control_symbolic_output_is_not_real_ocr_text"])
        self.assertTrue(output["control_page_image_reference_is_not_real_image_reference"])
        self.assertTrue(output["control_failure_classification_is_not_actual_failure_record"])
        for field in (
            "actual_ocr_text_created",
            "actual_page_image_reference_created",
            "actual_failure_record_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(contract["ownership_boundary"][field])
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_allowed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_allowed"])

    def test_candidate_control_page_has_eleven_fields_and_derived_references(self):
        result = self._slice().execute_per_page_controlled_ocr_output(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual("COMPLETED", result["job_state"])
        self.assertEqual(["QUEUED", "PROCESSING", "COMPLETED"], result["job_state_history"])
        self.assertEqual(4, result["page_output_count"])
        self.assertEqual(3, result["symbolic_control_output_count"])
        self.assertEqual(3, result["symbolic_control_page_image_reference_count"])
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
        self.assertEqual("source:control:stage053-p2", page["source_identity_ref"])
        self.assertEqual("source-page:control:stage053-p2:1", page["source_page_ref"])
        self.assertEqual("page-image-ref:control:stage053-p2:1", page["page_image_ref"])
        self.assertEqual("CONTROL_ZH_PAGE", page["ocr_text"])
        self.assertEqual("CONTROL_SYMBOLIC_OUTPUT_NOT_REAL_OCR_TEXT", page["text_output_kind"])
        self.assertEqual("CONTROL_SYMBOLIC_PAGE_IMAGE_REFERENCE_NOT_REAL_IMAGE", page["page_image_reference_kind"])
        self.assertFalse(page["actual_ocr_text_created"])
        self.assertFalse(page["actual_page_image_reference_created"])
        self.assertEqual("OCR_PAGE_CANDIDATE_RETAINED", page["page_state"])
        self.assertEqual("CANDIDATE_ONLY_QUALITY_UNASSESSED", page["evidence_eligibility"])
        self.assertFalse(page["high_trust_direct_entry_allowed"])

    def test_low_confidence_page_is_explainable_and_not_queued_for_review(self):
        result = self._slice().execute_per_page_controlled_ocr_output(self._control())
        page = result["page_outputs"][1]
        self.assertEqual("LOW", page["confidence_level"])
        self.assertEqual("OCR_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED", page["page_state"])
        self.assertEqual("NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY", page["evidence_eligibility"])
        self.assertEqual("STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED", page["review_route"])
        self.assertEqual(1, result["low_confidence_page_count"])
        self.assertIn("当前未创建复核任务", page["human_feedback"])

    def test_mixed_chinese_english_page_has_explicit_state(self):
        result = self._slice().execute_per_page_controlled_ocr_output(self._control())
        page = result["page_outputs"][2]
        self.assertEqual("SIMPLIFIED_CHINESE_AND_ENGLISH", page["language_profile"])
        self.assertEqual("OCR_MIXED_ZH_EN_REVIEW_REQUIRED_NOT_QUEUED", page["page_state"])
        self.assertEqual("STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED", page["review_route"])
        self.assertEqual(1, result["mixed_language_page_count"])

    def test_failed_page_is_explicit_without_real_failure_record_or_output(self):
        result = self._slice().execute_per_page_controlled_ocr_output(self._control())
        page = result["page_outputs"][3]
        self.assertEqual("OCR_PAGE_FAILED_EXPLICIT", page["page_state"])
        self.assertIsNone(page["ocr_text"])
        self.assertIsNone(page["page_image_ref"])
        self.assertEqual("OCR_EXECUTION_NOT_STARTED", page["failure_reason"])
        self.assertEqual("CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD", page["failure_reason_kind"])
        self.assertFalse(page["actual_failure_record_created"])
        self.assertEqual(1, result["failed_page_count"])
        self.assertEqual(1, result["control_failure_reason_count"])

    def test_invalid_control_rejects_without_returning_reference_or_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_per_page_controlled_ocr_output(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["job_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["page_outputs"])
        self.assertEqual(0, result["page_output_count"])
        self.assertEqual(0, result["symbolic_control_output_count"])

    def test_cache_and_all_external_actions_remain_disabled(self):
        result = self._slice().execute_per_page_controlled_ocr_output(self._control())
        self.assertEqual("IN_MEMORY_REBUILDABLE_NOT_PERSISTED", result["cache_policy"])
        self.assertFalse(result["cache_created"])
        self.assertIsNone(result["cache_ref"])
        for field in (
            "actual_ocr_text_created",
            "actual_page_image_reference_created",
            "actual_failure_record_created",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "pdf_rasterization_performed",
            "image_processing_performed",
            "language_detection_performed",
            "ocr_engine_selected",
            "ocr_engine_configuration_performed",
            "ocr_engine_invocation_performed",
            "persistent_queue_write_performed",
            "persistent_page_output_write_performed",
            "page_image_reference_write_performed",
            "failure_record_write_performed",
            "cache_write_performed",
            "review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "audit_write_performed",
            "persistent_state_write_performed",
            "database_connection_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_phase2_governance_projection_and_evidence_are_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage053_phase2_completed"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE053-P2"'),
            (batch, 'next_gate: "IDS-STAGE053-P3-GATE"'),
            (batch, "phase2_started: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE053"'),
            (roadmap, 'current_phase_id: "IDS-STAGE053-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE053-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE053", "IDS-STAGE054"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE053-P2",
                "IDS-V0_1-STAGE053-P3",
                "IDS-V0_1-STAGE053-P4",
                "IDS-V0_1-STAGE053-REVIEW",
                "IDS-V0_1-STAGE054-P1",
                "IDS-V0_1-STAGE054-P2",
                "IDS-V0_1-STAGE054-P3",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("PASS_PHASE2_PER_PAGE_OCR_CONTROL_SLICE_ENGINE_DISABLED", run["result"])
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE053-P2-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE053-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-053"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE053-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
