import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE051_PHASE1_OCR_QUEUE_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "ocr_queue" / "stage051_ocr_queue_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
PREDECESSOR_REVIEW = BASE / "BATCH041_050_REVIEW_GATE.md"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage051-p1-local.json"


class Stage051OcrQueuePhase1Tests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase1_artifacts_exist(self):
        for artifact in (
            BOUNDARY,
            CONTRACT,
            BATCH,
            PREDECESSOR_REVIEW,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_forward_gate_are_exact(self):
        contract = self._contract()
        self.assertEqual("ids.stage051.ocr_queue.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-051", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE051-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-051", contract["acceptance_id"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE051-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_BATCH041_050_REVIEW_ARTIFACTS",
            authority["authority"],
        )
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])
        self.assertFalse(authority["raw_metadata_content_access_allowed"])

    def test_ownership_and_reference_only_input_are_exact(self):
        contract = self._contract()
        ownership = contract["upstream_ownership_boundary"]
        self.assertEqual("STAGE-045", ownership["file_type_detection_owner"])
        self.assertEqual("STAGE-046", ownership["parser_routing_owner"])
        self.assertEqual("STAGE-047", ownership["parser_output_envelope_owner"])
        self.assertEqual("STAGE-048", ownership["parser_fallback_owner"])
        self.assertEqual("STAGE-049", ownership["differential_evaluation_owner"])
        self.assertEqual("STAGE-050", ownership["prompt_injection_marker_owner"])
        self.assertEqual("STAGE-051", ownership["ocr_queue_baseline_owner"])
        self.assertEqual("STAGE-052", ownership["bilingual_ocr_contract_owner"])
        self.assertEqual("STAGE-053", ownership["per_page_ocr_output_owner"])
        self.assertEqual("STAGE-054", ownership["low_confidence_review_route_owner"])
        self.assertEqual("STAGE-056", ownership["ocr_cache_retention_owner"])

        incoming = contract["reference_only_ocr_input_contract"]
        self.assertEqual(
            [
                "source_identity_ref",
                "input_kind_hint",
                "parser_output_status",
                "source_page_count_ref",
                "language_profile",
                "ocr_request_reason",
                "cache_policy_ref",
            ],
            incoming["required_fields"],
        )
        self.assertEqual(
            ["SCANNED_PDF", "IMAGE", "LOW_TEXT_COVERAGE_PDF"],
            incoming["input_kind_hints"],
        )
        for field in (
            "source_body_or_path_allowed",
            "source_page_content_allowed",
            "image_content_allowed",
            "candidate_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(incoming[field])

    def test_page_output_and_default_languages_are_exact(self):
        contract = self._contract()
        output = contract["per_page_output_contract"]
        self.assertEqual(
            [
                "source_identity_ref",
                "source_page_ref",
                "ocr_text",
                "language_profile",
                "confidence_level",
                "evidence_eligibility",
                "cache_ref",
                "review_route",
            ],
            output["required_fields"],
        )
        self.assertEqual(8, output["field_count"])
        self.assertFalse(output["actual_page_output_created"])
        self.assertFalse(output["actual_page_output_persisted"])
        self.assertFalse(output["ocr_text_created"])
        self.assertEqual("CANDIDATE", output["initial_fact_level"])
        self.assertEqual("UNASSESSED", output["initial_quality_state"])

        language = contract["language_contract"]
        self.assertEqual(
            ["SIMPLIFIED_CHINESE", "ENGLISH"], language["default_languages"]
        )
        self.assertTrue(language["default_simplified_chinese_and_english_confirmed"])
        self.assertFalse(language["ocr_engine_selected"])
        self.assertFalse(language["ocr_engine_configuration_allowed"])

    def test_low_confidence_and_cache_remain_fail_closed(self):
        contract = self._contract()
        confidence = contract["confidence_and_review_boundary"]
        self.assertFalse(confidence["numeric_threshold_assigned"])
        self.assertFalse(confidence["confidence_evaluation_performed"])
        self.assertFalse(confidence["low_confidence_direct_high_trust_allowed"])
        self.assertEqual(
            "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
            confidence["low_confidence_evidence_eligibility"],
        )
        self.assertEqual(
            "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
            confidence["future_review_route"],
        )
        self.assertFalse(confidence["review_queue_record_creation_allowed"])
        self.assertFalse(confidence["high_trust_evidence_promotion_allowed"])

        cache = contract["cache_boundary"]
        self.assertEqual("FUTURE_REBUILDABLE_DERIVED_CACHE_ONLY", cache["mode"])
        for field in (
            "cache_created",
            "cache_write_allowed",
            "cache_storage_location_assigned",
            "cache_retention_policy_defined",
            "cache_cleanup_allowed",
            "raw_source_cache_allowed",
            "persistent_cache_evidence_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(cache[field])
        self.assertEqual("STAGE-056", cache["cache_cleanup_owner"])

    def test_runtime_and_external_actions_remain_disabled(self):
        runtime = self._contract()["runtime_boundary"]
        for field in (
            "source_file_open_allowed",
            "file_type_detection_allowed",
            "route_evaluation_allowed",
            "parser_execution_allowed",
            "pdf_rasterization_allowed",
            "image_processing_allowed",
            "ocr_engine_selection_allowed",
            "ocr_engine_invocation_allowed",
            "ocr_queue_creation_allowed",
            "per_page_output_creation_allowed",
            "cache_write_allowed",
            "review_queue_write_allowed",
            "quality_gate_execution_allowed",
            "evidence_promotion_allowed",
            "persistent_state_write_allowed",
            "agent_execution_allowed",
            "model_call_allowed",
            "model_token_consumption_allowed",
            "ovh_deployment_allowed",
            "production_runtime_activation_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(runtime[field])

    def test_chinese_feedback_and_rollback_are_bounded(self):
        contract = self._contract()
        feedback = contract["chinese_feedback_contract"]
        self.assertEqual(4, len(feedback["messages"]))
        self.assertTrue(
            all("当前" in item["message"] or "不能" in item["message"] for item in feedback["messages"])
        )
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])

        rollback = contract["rollback_contract"]
        self.assertEqual(
            "BATCH041_050_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED",
            rollback["return_to"],
        )
        self.assertFalse(rollback["source_or_raw_data_change_allowed"])
        self.assertFalse(rollback["persistent_runtime_state_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_phase1_evidence_and_forward_route_are_retained(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'batch_id: "IDS-V0_1-BATCH-051-060"'),
            (batch, 'status: "stage051_phase1_completed"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE051-P1"'),
            (batch, 'next_gate: "IDS-STAGE051-P2-GATE"'),
            (batch, 'second_authoritative_source_created: false'),
            (batch, 'ocr_queue_created: false'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'phase_id: "IDS-STAGE051-P1"'),
            (roadmap, 'gate_id: "IDS-STAGE051-P1-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE051", "IDS-STAGE052", "IDS-STAGE053", "IDS-STAGE054", "IDS-STAGE055", "IDS-STAGE056", "IDS-STAGE057", "IDS-STAGE058", "IDS-STAGE059"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE051-P1",
                "IDS-V0_1-STAGE051-P2",
                "IDS-V0_1-STAGE051-P3",
                "IDS-V0_1-STAGE051-P4",
                "IDS-V0_1-STAGE051-REVIEW",
                "IDS-V0_1-STAGE052-P1",
                "IDS-V0_1-STAGE052-P2",
                "IDS-V0_1-STAGE052-P3",
                "IDS-V0_1-STAGE052-P4",
                "IDS-V0_1-STAGE052-REVIEW",
                "IDS-V0_1-STAGE053-P1",
                "IDS-V0_1-STAGE053-P2",
                "IDS-V0_1-STAGE053-P3",
                "IDS-V0_1-STAGE053-P4",
                "IDS-V0_1-STAGE053-REVIEW",
                "IDS-V0_1-STAGE054-P1",
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
            "IDS-V0_1-STAGE058-P2",
            "IDS-V0_1-STAGE058-P3",
            "IDS-V0_1-STAGE058-P4",
            "IDS-V0_1-STAGE058-REVIEW",
            "IDS-V0_1-STAGE059-P1",
            "IDS-V0_1-STAGE059-P2",
            "IDS-V0_1-STAGE059-P3",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_OCR_QUEUE_BOUNDARY_RUNTIME_DISABLED",
            run["result"].strip(chr(96)),
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE051-P1-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE051-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-051"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE051-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
