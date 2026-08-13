import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE055_PHASE1_OCR_REGRESSION_CORPUS_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage055-p1-local.json"


class Stage055OcrRegressionCorpusPhase1Tests(unittest.TestCase):
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
            "ids.stage055.ocr_regression_corpus.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE055-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-055", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_OCR_REGRESSION_CORPUS_BOUNDARY_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE054_REVIEW_ARTIFACTS",
            source["authority"],
        )
        self.assertFalse(source["second_authoritative_source_created"])
        self.assertFalse(source["source_body_or_path_allowed"])
        self.assertFalse(source["live_source_read_performed"])
        self.assertFalse(source["authorized_fixture_access_performed"])

    def test_reference_only_inputs_and_future_page_output_are_content_free(self):
        input_contract = self.contract["reference_only_regression_input_contract"]
        self.assertEqual(10, input_contract["field_count"])
        self.assertEqual(
            [
                "source_identity_ref",
                "source_page_ref",
                "input_class",
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
        self.assertFalse(input_contract["fixture_record_write_allowed"])

        output_contract = self.contract["future_per_page_output_contract"]
        self.assertEqual(11, output_contract["field_count"])
        self.assertFalse(output_contract["actual_page_output_created"])
        self.assertFalse(output_contract["actual_page_output_persisted"])
        self.assertFalse(output_contract["ocr_text_created"])
        self.assertFalse(output_contract["page_image_reference_created"])

    def test_taskpack_category_registry_has_no_fixture_or_regression_result(self):
        corpus = self.contract["regression_corpus_category_contract"]
        self.assertEqual(
            [
                "SCANNED_DOCUMENT_CONTROL",
                "BLURRED_DOCUMENT_CONTROL",
                "TABLE_DOCUMENT_CONTROL",
                "MIXED_ZH_EN_DOCUMENT_CONTROL",
                "LOW_QUALITY_DOCUMENT_CONTROL",
            ],
            corpus["category_ids"],
        )
        self.assertEqual(5, corpus["category_count"])
        self.assertEqual(0, corpus["actual_fixture_count"])
        for field in (
            "actual_fixture_created",
            "fixture_content_or_path_allowed",
            "fixture_open_performed",
            "fixture_copy_or_move_performed",
            "regression_execution_performed",
            "recognition_accuracy_evaluated",
        ):
            with self.subTest(field=field):
                self.assertFalse(corpus[field])

    def test_language_confidence_and_review_isolation_are_explicit(self):
        language = self.contract["bilingual_language_contract"]
        self.assertEqual(["SIMPLIFIED_CHINESE", "ENGLISH"], language["default_languages"])
        self.assertEqual(3, len(language["allowed_language_profiles"]))
        self.assertFalse(language["language_detection_performed"])

        boundary = self.contract["confidence_and_review_boundary"]
        self.assertEqual(["HIGH", "MEDIUM", "LOW", "UNKNOWN"], boundary["confidence_levels"])
        self.assertFalse(boundary["numeric_threshold_assigned"])
        self.assertFalse(boundary["low_confidence_direct_high_trust_allowed"])
        self.assertFalse(boundary["mixed_language_direct_high_trust_allowed"])
        self.assertFalse(boundary["failure_page_direct_high_trust_allowed"])
        self.assertEqual("STAGE-054", boundary["future_review_route_owner"])
        self.assertFalse(boundary["review_queue_record_creation_allowed"])

    def test_engine_mapping_and_cache_are_contract_only(self):
        engine = self.contract["future_engine_mapping_contract"]
        self.assertEqual(5, engine["field_count"])
        for field in (
            "engine_selected",
            "engine_configuration_allowed",
            "engine_mapping_instance_created",
            "engine_invocation_allowed",
            "engine_comparison_performed",
            "fallback_execution_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(engine[field])

        cache = self.contract["cache_boundary"]
        self.assertEqual("STAGE-056", cache["cache_cleanup_owner"])
        self.assertEqual(0, cache["temporary_artifact_count"])
        self.assertFalse(cache["cache_created"])
        self.assertFalse(cache["cache_write_allowed"])
        self.assertFalse(cache["cache_cleanup_allowed"])

    def test_chinese_feedback_and_runtime_boundary_do_not_claim_runtime(self):
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["all_messages_chinese"])
        self.assertEqual(4, len(feedback["messages"]))
        self.assertFalse(feedback["automation_claim_allowed"])
        self.assertFalse(feedback["recognition_accuracy_claim_allowed"])
        self.assertFalse(feedback["production_availability_claim_allowed"])

        runtime = self.contract["runtime_boundary"]
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "ocr_engine_selected",
            "ocr_engine_invocation_performed",
            "ocr_engine_comparison_performed",
            "regression_execution_performed",
            "actual_page_output_created",
            "review_queue_created",
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
        self.assertTrue(runtime["stage055_started"])
        self.assertTrue(runtime["stage055_entry_authorized"])

    def test_governance_run_and_event_only_record_local_phase1_evidence(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage055_phase1_completed"'),
            (batch, "stage055_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE055-P1"'),
            (batch, 'next_gate: "IDS-STAGE055-P2-GATE"'),
            (batch, "stage055_started: true"),
            (batch, "stage055_entry_authorized: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE055"'),
            (roadmap, 'current_phase_id: "IDS-STAGE055-P1"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE055-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE055-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE055", "IDS-STAGE056", "IDS-STAGE057"))
        self.assertIn(
            status["phase"],
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_OCR_REGRESSION_CORPUS_BOUNDARY_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual(
            [8, 226, 1, 1, 7],
            [item["passed"] for item in run["evidence_iterations"]],
        )
        self.assertEqual(
            [8, 226, 1, 1, 7],
            [item["total"] for item in run["evidence_iterations"]],
        )
        self.assertEqual(
            "PASS_PHASE1_AND_PREDECESSOR_REGRESSION",
            run["evidence_iterations"][1]["result"],
        )
        self.assertFalse(run["observed_work"]["authorized_fixture_access_performed"])
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["regression_execution_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE055-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE055-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-055"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE055-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
