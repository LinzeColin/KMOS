import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE054_PHASE1_LOW_CONFIDENCE_REVIEW_ROUTE_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "ocr_queue" / "stage054_low_confidence_review_route_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage054-p1-local.json"


class Stage054LowConfidenceReviewRoutePhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_and_contract_artifacts_exist(self):
        for artifact in (SCOPE, CONTRACT, BATCH, ROADMAP, EVENTS, STATUS, RUN):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_single_authority_boundary(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage054.low_confidence_review_route.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE054-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-054", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_LOW_CONFIDENCE_REVIEW_ROUTE_BOUNDARY_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE053_REVIEW_ARTIFACTS",
            source["authority"],
        )
        self.assertFalse(source["second_authoritative_source_created"])
        self.assertFalse(source["source_body_or_path_allowed"])
        self.assertFalse(source["live_source_read_performed"])

    def test_reference_only_input_has_no_content_or_review_result(self):
        input_contract = self.contract["reference_only_review_input_contract"]
        self.assertEqual(9, input_contract["field_count"])
        self.assertEqual(
            [
                "source_identity_ref",
                "source_page_ref",
                "language_profile",
                "confidence_level",
                "output_status",
                "failure_reason",
                "evidence_eligibility",
                "review_route",
                "cache_policy_ref",
            ],
            input_contract["required_fields"],
        )
        self.assertFalse(input_contract["source_page_content_allowed"])
        self.assertFalse(input_contract["image_content_allowed"])
        self.assertFalse(input_contract["ocr_text_allowed"])
        self.assertFalse(input_contract["human_review_content_allowed"])

    def test_future_review_request_is_static_and_not_persisted(self):
        review_request = self.contract["future_review_request_contract"]
        self.assertEqual(10, review_request["field_count"])
        self.assertEqual(
            "FUTURE_REFERENCE_ONLY_NO_REVIEW_REQUEST_CREATED",
            review_request["mode"],
        )
        for field in (
            "actual_review_request_created",
            "actual_review_request_persisted",
            "review_queue_record_created",
            "automatic_assignment_performed",
            "human_review_result_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(review_request[field])

    def test_language_confidence_and_route_isolation_are_explicit(self):
        contract = self.contract
        language = contract["bilingual_language_contract"]
        self.assertEqual(["SIMPLIFIED_CHINESE", "ENGLISH"], language["default_languages"])
        self.assertEqual(3, len(language["allowed_language_profiles"]))
        boundary = contract["confidence_and_route_boundary"]
        self.assertEqual(["HIGH", "MEDIUM", "LOW", "UNKNOWN"], boundary["confidence_levels"])
        self.assertEqual(3, boundary["future_route_state_count"])
        self.assertFalse(boundary["numeric_threshold_assigned"])
        self.assertFalse(boundary["low_confidence_direct_high_trust_allowed"])
        self.assertFalse(boundary["mixed_language_direct_high_trust_allowed"])
        self.assertFalse(boundary["failure_page_direct_high_trust_allowed"])
        self.assertFalse(boundary["automatic_human_review_assignment_allowed"])

    def test_chinese_feedback_and_cache_boundary_do_not_claim_runtime(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertEqual(4, len(feedback["messages"]))
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["human_review_completion_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])
        cache = self.contract["cache_boundary"]
        self.assertEqual("STAGE-056", cache["cache_cleanup_owner"])
        self.assertFalse(cache["cache_created"])
        self.assertFalse(cache["cache_write_allowed"])
        self.assertFalse(cache["cache_cleanup_allowed"])

    def test_runtime_boundary_keeps_all_execution_and_external_actions_disabled(self):
        runtime = self.contract["runtime_boundary"]
        for field in (
            "ids_business_source_read_performed",
            "source_file_open_performed",
            "ocr_engine_invocation_performed",
            "actual_page_output_created",
            "review_queue_created",
            "human_review_task_created",
            "human_review_result_created",
            "cache_write_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "phase2_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(runtime[field])
        self.assertTrue(runtime["stage054_started"])

    def test_phase1_history_run_and_event_remain_available_after_successor_entry(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage054_phase1_completed"'),
            (batch, "stage054_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE054-P1"'),
            (batch, 'next_gate: "IDS-STAGE054-P2-GATE"'),
            (batch, "stage054_started: true"),
            (roadmap, 'current_phase_id: "IDS-STAGE054-P1"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE054-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE054-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE054", status["stage"])
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE054-P1",
                "IDS-V0_1-STAGE054-P2",
                "IDS-V0_1-STAGE054-P3",
                "IDS-V0_1-STAGE054-P4",
            ),
        )
        self.assertIn(
            status["next_gate"],
            (
                "IDS-STAGE054-P2-GATE",
                "IDS-STAGE054-P3-GATE",
                "IDS-STAGE054-P4-GATE",
                "IDS-STAGE054-REVIEW-GATE",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_LOW_CONFIDENCE_REVIEW_ROUTE_BOUNDARY_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["human_review_task_created"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE054-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE054-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-054"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE054-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
