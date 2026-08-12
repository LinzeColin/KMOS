import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE052_PHASE1_BILINGUAL_OCR_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "ocr_queue" / "stage052_bilingual_ocr_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE051_STAGE_REVIEW.md"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage052-p1-local.json"


class Stage052BilingualOcrPhase1Tests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase1_artifacts_exist(self):
        for artifact in (
            BOUNDARY,
            CONTRACT,
            PREDECESSOR_REVIEW,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_forward_gate_are_exact(self):
        contract = self._contract()
        self.assertEqual("ids.stage052.bilingual_ocr.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-052", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE052-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-052", contract["acceptance_id"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE052-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE051_REVIEW_ARTIFACTS",
            authority["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])

    def test_ownership_and_reference_only_input_are_exact(self):
        contract = self._contract()
        ownership = contract["ownership_boundary"]
        self.assertEqual("STAGE-051", ownership["ocr_queue_baseline_owner"])
        self.assertEqual("STAGE-052", ownership["bilingual_ocr_contract_owner"])
        self.assertEqual("STAGE-053", ownership["per_page_ocr_output_owner"])
        self.assertEqual("STAGE-054", ownership["low_confidence_review_route_owner"])
        self.assertEqual("STAGE-055", ownership["ocr_engine_mapping_owner"])
        self.assertEqual("STAGE-056", ownership["ocr_cache_retention_owner"])
        self.assertFalse(ownership["upstream_result_rewrite_allowed"])
        self.assertFalse(ownership["queue_or_engine_activation_allowed"])

        incoming = contract["reference_only_input_contract"]
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
            "additional_fields_allowed",
            "source_body_or_path_allowed",
            "source_page_content_allowed",
            "image_content_allowed",
            "language_detection_performed",
            "candidate_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(incoming[field])

    def test_bilingual_profiles_and_output_reference_are_exact(self):
        contract = self._contract()
        output = contract["per_page_output_reference"]
        self.assertEqual(8, output["field_count"])
        self.assertEqual("CANDIDATE", output["initial_fact_level"])
        self.assertEqual("UNASSESSED", output["initial_quality_state"])
        for field in (
            "actual_page_output_created",
            "actual_page_output_persisted",
            "ocr_text_created",
            "page_content_return_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(output[field])

        language = contract["bilingual_language_contract"]
        self.assertEqual(
            ["SIMPLIFIED_CHINESE", "ENGLISH"], language["default_languages"]
        )
        self.assertEqual(2, language["default_language_count"])
        self.assertTrue(language["default_simplified_chinese_and_english_confirmed"])
        self.assertEqual(
            [
                "SIMPLIFIED_CHINESE",
                "ENGLISH",
                "SIMPLIFIED_CHINESE_AND_ENGLISH",
            ],
            language["allowed_language_profiles"],
        )
        self.assertTrue(language["mixed_language_profile_declared"])
        for field in (
            "ocr_engine_selected",
            "ocr_engine_configuration_allowed",
            "language_engine_mapping_defined",
            "language_detection_performed",
            "mixed_language_runtime_processing_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(language[field])

    def test_low_confidence_mixed_language_and_cache_remain_fail_closed(self):
        contract = self._contract()
        confidence = contract["confidence_and_review_boundary"]
        for field in (
            "numeric_threshold_assigned",
            "confidence_evaluation_performed",
            "low_confidence_direct_high_trust_allowed",
            "mixed_language_direct_high_trust_allowed",
            "review_queue_record_creation_allowed",
            "quality_gate_execution_allowed",
            "evidence_promotion_allowed",
            "high_trust_evidence_promotion_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(confidence[field])
        self.assertEqual(
            "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
            confidence["low_confidence_evidence_eligibility"],
        )
        self.assertEqual(
            "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
            confidence["mixed_language_evidence_eligibility"],
        )
        self.assertEqual(
            "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
            confidence["future_review_route"],
        )

        cache = contract["cache_boundary"]
        self.assertEqual("FUTURE_REBUILDABLE_DERIVED_CACHE_ONLY", cache["mode"])
        self.assertEqual("STAGE-056", cache["cache_cleanup_owner"])
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

    def test_runtime_and_external_actions_remain_disabled(self):
        runtime = self._contract()["runtime_boundary"]
        self.assertTrue(all(value is False for value in runtime.values()))

    def test_chinese_feedback_and_rollback_are_bounded(self):
        contract = self._contract()
        feedback = contract["chinese_feedback_contract"]
        self.assertEqual(5, len(feedback["messages"]))
        self.assertTrue(
            all("当前" in item["message"] or "不能" in item["message"] for item in feedback["messages"])
        )
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])

        rollback = contract["rollback_contract"]
        self.assertEqual(
            "STAGE051_REVIEWED_LOCAL_OCR_QUEUE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "source_or_raw_data_change_allowed",
            "manifest_change_allowed",
            "evidence_ledger_change_allowed",
            "audit_log_change_allowed",
            "delivered_report_change_allowed",
            "persistent_runtime_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

    def test_governance_and_local_run_preserve_stage052_phase1(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage052_phase1_completed"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE052-P1"'),
            (batch, 'next_gate: "IDS-STAGE052-P2-GATE"'),
            (batch, "stage052_started: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE052"'),
            (roadmap, 'current_phase_id: "IDS-STAGE052-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE052-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE052", "IDS-STAGE053", "IDS-STAGE054"))
        self.assertIn(
            status["phase"],
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_BILINGUAL_OCR_BOUNDARY_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE052-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE052-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-052"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE052-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
