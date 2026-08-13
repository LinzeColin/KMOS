import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE056_PHASE1_OCR_CACHE_RETENTION_POLICY_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage056-p1-local.json"


class Stage056OcrCacheRetentionPolicyPhase1Tests(unittest.TestCase):
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
            "ids.stage056.ocr_cache_retention_policy.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE056-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-056", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_OCR_CACHE_RETENTION_POLICY_BOUNDARY_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE056-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE055_REVIEW_ARTIFACTS",
            source["authority"],
        )
        self.assertFalse(source["second_authoritative_source_created"])
        self.assertFalse(source["source_body_or_path_allowed"])
        self.assertFalse(source["live_source_read_performed"])
        self.assertFalse(source["authorized_fixture_access_performed"])

    def test_reference_only_cache_inputs_and_outputs_are_content_free(self):
        input_contract = self.contract["reference_only_cache_input_contract"]
        self.assertEqual(11, input_contract["field_count"])
        self.assertEqual(
            [
                "cache_entry_ref",
                "source_identity_ref",
                "source_page_ref",
                "artifact_class",
                "language_profile",
                "confidence_level",
                "cache_state",
                "retention_class",
                "cleanup_eligibility",
                "evidence_eligibility",
                "review_route",
            ],
            input_contract["required_fields"],
        )
        for field in (
            "source_body_or_path_allowed",
            "source_page_content_allowed",
            "image_content_allowed",
            "ocr_text_allowed",
            "failure_content_allowed",
            "fixture_record_write_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(input_contract[field])

        output_contract = self.contract["future_cache_policy_output_contract"]
        self.assertEqual(10, output_contract["field_count"])
        for field in (
            "actual_cache_decision_created",
            "actual_cache_decision_persisted",
            "physical_storage_path_created",
            "artifact_content_retained",
            "cleanup_action_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(output_contract[field])

    def test_cache_artifact_classes_and_cleanup_eligibility_are_explicit(self):
        artifacts = self.contract["cache_artifact_class_contract"]
        self.assertEqual(
            [
                "TEMPORARY_PAGE_IMAGE",
                "INTERMEDIATE_OCR_TEXT",
                "FAILURE_ARTIFACT",
            ],
            artifacts["artifact_classes"],
        )
        self.assertEqual(3, artifacts["artifact_class_count"])
        self.assertEqual(0, artifacts["actual_cache_item_count"])
        for field in (
            "actual_cache_item_created",
            "artifact_content_or_path_allowed",
            "artifact_open_performed",
            "artifact_copy_or_move_performed",
            "physical_cache_enumeration_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(artifacts[field])

        policy = self.contract["retention_and_cleanup_policy_contract"]
        self.assertEqual(
            "FUTURE_REBUILDABLE_TEMPORARY",
            policy["retention_class_by_artifact"]["TEMPORARY_PAGE_IMAGE"],
        )
        self.assertEqual(
            "FUTURE_REBUILDABLE_TEMPORARY",
            policy["retention_class_by_artifact"]["INTERMEDIATE_OCR_TEXT"],
        )
        self.assertEqual(
            "FUTURE_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
            policy["retention_class_by_artifact"]["FAILURE_ARTIFACT"],
        )
        self.assertEqual(
            ["TEMPORARY_PAGE_IMAGE", "INTERMEDIATE_OCR_TEXT"],
            policy["cleanup_eligible_artifact_classes"],
        )
        self.assertIn("FAILURE_ARTIFACT", policy["cleanup_ineligible_artifact_classes"])
        self.assertIn("RAW_SOURCE", policy["cleanup_ineligible_artifact_classes"])
        self.assertIn("DELIVERED_REPORT", policy["cleanup_ineligible_artifact_classes"])

    def test_cache_policy_has_no_physical_cleanup_or_disk_action(self):
        policy = self.contract["retention_and_cleanup_policy_contract"]
        self.assertTrue(policy["future_write_requires_owner_approved_retention"])
        self.assertTrue(policy["future_write_requires_capacity_limit"])
        self.assertTrue(
            policy["future_cleanup_requires_explicit_temporary_artifact_identification"]
        )
        self.assertEqual(0, policy["temporary_artifact_count"])
        for field in (
            "numeric_retention_window_assigned",
            "physical_storage_location_assigned",
            "cache_capacity_threshold_assigned",
            "automatic_cleanup_allowed",
            "manual_cleanup_execution_allowed",
            "cleanup_target_path_assigned",
            "disk_scan_performed",
            "cache_capacity_evaluation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(policy[field])

        protected = self.contract["protected_surface_boundary"]
        for field in protected:
            with self.subTest(field=field):
                self.assertFalse(protected[field])

    def test_language_confidence_and_review_isolation_are_preserved(self):
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
            "regression_execution_performed",
            "actual_page_output_created",
            "review_queue_created",
            "cache_created",
            "cache_write_performed",
            "cache_cleanup_performed",
            "disk_scan_performed",
            "cache_capacity_evaluation_performed",
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
        self.assertTrue(runtime["stage055_review_reused_as_reference_only"])
        self.assertTrue(runtime["stage056_started"])
        self.assertTrue(runtime["stage056_entry_authorized"])

    def test_governance_run_and_event_only_record_local_phase1_evidence(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage056_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE056-P1"'),
            (batch, 'next_gate: "IDS-STAGE056-P2-GATE"'),
            (batch, "stage056_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE056-P2"'),
            (batch, 'next_gate: "IDS-STAGE056-P3-GATE"'),
            (batch, "stage056_started: true"),
            (batch, "stage056_entry_authorized: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE056"'),
            (roadmap, 'current_phase_id: "IDS-STAGE056-P2"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE056-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE056-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE056", "IDS-STAGE057", "IDS-STAGE058"))
        self.assertIn(
            status["phase"],
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_OCR_CACHE_RETENTION_POLICY_BOUNDARY_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual(
            [8, 278, 1, 1, 7],
            [item["passed"] for item in run["evidence_iterations"]],
        )
        self.assertEqual(
            [8, 278, 1, 1, 7],
            [item["total"] for item in run["evidence_iterations"]],
        )
        self.assertEqual(
            "PASS_PHASE1_AND_PREDECESSOR_REGRESSION",
            run["evidence_iterations"][1]["result"],
        )
        self.assertFalse(run["observed_work"]["authorized_fixture_access_performed"])
        self.assertFalse(run["observed_work"]["cache_write_performed"])
        self.assertFalse(run["observed_work"]["cache_cleanup_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase2_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE056-P1-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE056-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-056"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE056-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
