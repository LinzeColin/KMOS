import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage054_low_confidence_review_route_contract.json"
PHASE2 = BASE / "STAGE054_PHASE2_LOW_CONFIDENCE_REVIEW_ROUTE_SLICE.md"
CONTRACT = BASE / "ocr_queue" / "stage054_low_confidence_review_route_slice_contract.json"
SLICE = BASE / "ocr_queue" / "stage054_low_confidence_review_route_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage054-p2-local.json"


class Stage054LowConfidenceReviewRoutePhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage054_low_confidence_review_route_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "review_input_records": [
                {
                    "source_identity_ref": "source:control:stage054-p2",
                    "source_page_ref": "source-page:control:stage054-p2:1",
                    "language_profile": "ENGLISH",
                    "confidence_level": "LOW",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage054-p2",
                    "source_page_ref": "source-page:control:stage054-p2:2",
                    "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                    "confidence_level": "MEDIUM",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage054-p2",
                    "source_page_ref": "source-page:control:stage054-p2:3",
                    "language_profile": "UNKNOWN",
                    "confidence_level": "UNKNOWN",
                    "output_status": "OCR_PAGE_FAILED",
                    "failure_reason": "OCR_EXECUTION_NOT_STARTED",
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
                },
                {
                    "source_identity_ref": "source:control:stage054-p2",
                    "source_page_ref": "source-page:control:stage054-p2:4",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "HIGH",
                    "output_status": "OCR_OUTPUT_CONTROL_READY",
                    "failure_reason": None,
                    "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                    "review_route": "NO_REVIEW_QUEUE_CREATED",
                    "cache_policy_ref": "cache-policy:stage054-p2:in-memory",
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

    def test_contract_is_executable_but_actual_review_and_production_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage054.low_confidence_review_route.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE054-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE054-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["implementation"]["in_memory_controlled_review_route_implemented"]
        )
        self.assertFalse(contract["review_request_candidate_contract"]["actual_review_request_created"])
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_allowed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_allowed"])

    def test_low_confidence_record_forms_exact_candidate_request(self):
        result = self._slice().route_low_confidence_controlled_reviews(self._control())
        route = result["route_results"][0]
        request = route["review_request_candidate"]
        self.assertEqual("LOW_CONFIDENCE_REVIEW_REQUIRED", route["route_state"])
        self.assertEqual(
            {
                "source_identity_ref",
                "source_page_ref",
                "language_profile",
                "confidence_level",
                "output_status",
                "failure_reason",
                "evidence_eligibility",
                "review_route",
                "cache_policy_ref",
                "feedback_code",
            },
            set(request),
        )
        self.assertEqual("LOW", request["confidence_level"])
        self.assertEqual(
            "source-page:control:stage054-p2:1", request["source_page_ref"]
        )
        self.assertTrue(route["source_page_reference_preserved"])
        self.assertFalse(route["actual_review_request_created"])
        self.assertFalse(route["high_trust_direct_entry_allowed"])
        self.assertIn("未创建人工任务", route["human_feedback"])

    def test_mixed_language_record_has_explicit_route_state(self):
        result = self._slice().route_low_confidence_controlled_reviews(self._control())
        route = result["route_results"][1]
        self.assertEqual("MIXED_LANGUAGE_REVIEW_REQUIRED", route["route_state"])
        self.assertEqual(
            "SIMPLIFIED_CHINESE_AND_ENGLISH",
            route["review_request_candidate"]["language_profile"],
        )
        self.assertEqual(1, result["mixed_language_route_count"])
        self.assertFalse(route["high_trust_direct_entry_allowed"])

    def test_failed_page_record_has_explicit_route_state_without_actual_failure(self):
        result = self._slice().route_low_confidence_controlled_reviews(self._control())
        route = result["route_results"][2]
        self.assertEqual("FAILED_PAGE_REVIEW_REQUIRED", route["route_state"])
        self.assertEqual(
            "OCR_EXECUTION_NOT_STARTED",
            route["review_request_candidate"]["failure_reason"],
        )
        self.assertEqual(
            "CONTROL_FAILURE_CLASSIFICATION_NOT_ACTUAL_FAILURE_RECORD",
            route["failure_reason_kind"],
        )
        self.assertEqual(1, result["failed_page_route_count"])
        self.assertFalse(route["human_review_task_created"])

    def test_high_confidence_control_does_not_create_review_request_or_high_trust_entry(self):
        result = self._slice().route_low_confidence_controlled_reviews(self._control())
        route = result["route_results"][3]
        self.assertIsNone(route["route_state"])
        self.assertIsNone(route["review_request_candidate"])
        self.assertEqual(1, result["no_review_route_required_count"])
        self.assertFalse(route["high_trust_direct_entry_allowed"])
        self.assertIn("未进行质量评估", route["human_feedback"])

    def test_invalid_control_rejects_without_reference_or_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().route_low_confidence_controlled_reviews(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["route_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["route_results"])
        self.assertEqual(0, result["review_request_candidate_count"])

    def test_cache_and_all_external_actions_remain_disabled(self):
        result = self._slice().route_low_confidence_controlled_reviews(self._control())
        self.assertEqual("IN_MEMORY_REBUILDABLE_NOT_PERSISTED", result["cache_policy"])
        self.assertFalse(result["cache_created"])
        self.assertIsNone(result["cache_ref"])
        for field in (
            "actual_review_request_created",
            "actual_review_request_persisted",
            "review_queue_record_created",
            "human_review_task_created",
            "human_review_result_created",
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
            "cache_write_performed",
            "cache_cleanup_performed",
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

    def test_phase2_governance_projection_and_evidence_remain_historical_or_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage054_phase2_completed"'),
            (batch, "stage054_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE054-P2"'),
            (batch, 'next_gate: "IDS-STAGE054-P3-GATE"'),
            (batch, "phase2_started: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE054"'),
            (roadmap, 'phase_id: "IDS-STAGE054-P2"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        self.assertTrue(
            'current_phase_id: "IDS-STAGE054-P2"' in roadmap
            or 'current_phase_id: "IDS-STAGE054-P3"' in roadmap
            or 'current_phase_id: "IDS-STAGE054-P4"' in roadmap
            or 'current_phase_id: "IDS-STAGE054-REVIEW"' in roadmap
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE054-P3-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE054-P4-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE054-REVIEW-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE055-P1-GATE"' in roadmap
        )

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE054", "IDS-STAGE055", "IDS-STAGE056", "IDS-STAGE057", "IDS-STAGE058"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE054-P2",
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
            "PASS_PHASE2_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROL_SLICE_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["human_review_task_created"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase3_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE054-P2-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE054-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-054"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE054-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
