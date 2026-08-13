import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_contract.json"
PHASE2 = BASE / "STAGE056_PHASE2_OCR_CACHE_RETENTION_POLICY_SLICE.md"
CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_slice_contract.json"
SLICE = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_slice.py"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage056-p2-local.json"


class Stage056OcrCacheRetentionPolicyPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage056_ocr_cache_retention_policy_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "cache_policy_input_records": [
                {
                    "cache_entry_ref": "cache-entry:control:stage056-p2:1",
                    "source_identity_ref": "source:control:stage056-p2",
                    "source_page_ref": "source-page:control:stage056-p2:1",
                    "artifact_class": "TEMPORARY_PAGE_IMAGE",
                    "language_profile": "SIMPLIFIED_CHINESE",
                    "confidence_level": "HIGH",
                    "cache_state": "CANDIDATE_NOT_PERSISTED",
                    "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                    "cleanup_eligibility": "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED",
                    "evidence_eligibility": "CANDIDATE_ONLY_QUALITY_UNASSESSED",
                    "review_route": "NO_REVIEW_QUEUE_CREATED",
                },
                {
                    "cache_entry_ref": "cache-entry:control:stage056-p2:2",
                    "source_identity_ref": "source:control:stage056-p2",
                    "source_page_ref": "source-page:control:stage056-p2:2",
                    "artifact_class": "INTERMEDIATE_OCR_TEXT",
                    "language_profile": "ENGLISH",
                    "confidence_level": "LOW",
                    "cache_state": "CANDIDATE_NOT_PERSISTED",
                    "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                    "cleanup_eligibility": "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED",
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                },
                {
                    "cache_entry_ref": "cache-entry:control:stage056-p2:3",
                    "source_identity_ref": "source:control:stage056-p2",
                    "source_page_ref": "source-page:control:stage056-p2:3",
                    "artifact_class": "INTERMEDIATE_OCR_TEXT",
                    "language_profile": "SIMPLIFIED_CHINESE_AND_ENGLISH",
                    "confidence_level": "MEDIUM",
                    "cache_state": "CANDIDATE_NOT_PERSISTED",
                    "retention_class": "FUTURE_REBUILDABLE_TEMPORARY",
                    "cleanup_eligibility": "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED",
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                },
                {
                    "cache_entry_ref": "cache-entry:control:stage056-p2:4",
                    "source_identity_ref": "source:control:stage056-p2",
                    "source_page_ref": "source-page:control:stage056-p2:4",
                    "artifact_class": "FAILURE_ARTIFACT",
                    "language_profile": "UNKNOWN",
                    "confidence_level": "UNKNOWN",
                    "cache_state": "CANDIDATE_NOT_PERSISTED",
                    "retention_class": "FUTURE_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
                    "cleanup_eligibility": "NOT_ELIGIBLE_FOR_AUTOMATIC_CLEANUP",
                    "evidence_eligibility": "NOT_ELIGIBLE_FOR_HIGH_TRUST_DIRECT_ENTRY",
                    "review_route": "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
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

    def test_contract_is_executable_but_real_cache_and_production_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage056.ocr_cache_retention_policy.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE056-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE056-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(11, contract["reference_only_cache_input_contract"]["field_count"])
        self.assertEqual(4, contract["reference_only_cache_input_contract"]["control_record_count"])
        self.assertEqual(10, contract["cache_policy_output_contract"]["field_count"])
        self.assertTrue(contract["cache_policy_output_contract"]["in_memory_candidate_policy_output_created"])
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_four_policy_candidates_preserve_phase1_output_fields_and_source_page_references(self):
        result = self._slice().execute_ocr_cache_retention_policy_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual("COMPLETED_IN_MEMORY_CONTROL_SLICE", result["execution_state"])
        self.assertEqual(4, result["cache_policy_input_record_count"])
        self.assertEqual(4, result["cache_policy_candidate_count"])
        self.assertTrue(result["source_page_reference_preserved"])
        candidate = result["candidate_policy_outputs"][0]
        self.assertEqual(
            {
                "cache_entry_ref",
                "artifact_class",
                "retention_class",
                "cleanup_eligibility",
                "rebuildability",
                "source_identity_ref",
                "source_page_ref",
                "language_profile",
                "confidence_level",
                "review_route",
            },
            set(candidate).intersection(
                {
                    "cache_entry_ref",
                    "artifact_class",
                    "retention_class",
                    "cleanup_eligibility",
                    "rebuildability",
                    "source_identity_ref",
                    "source_page_ref",
                    "language_profile",
                    "confidence_level",
                    "review_route",
                }
            ),
        )
        self.assertEqual("source-page:control:stage056-p2:1", candidate["source_page_ref"])
        self.assertEqual("CANDIDATE_NOT_PERSISTED", candidate["cache_state"])
        self.assertEqual(
            "CONTROL_REFERENCE_NOT_PHYSICAL_CACHE_ENTRY",
            candidate["cache_entry_reference_kind"],
        )
        self.assertFalse(candidate["actual_cache_decision_created"])

    def test_low_confidence_mixed_and_failed_candidates_are_explicit_and_not_high_trust(self):
        result = self._slice().execute_ocr_cache_retention_policy_control_slice(
            self._control()
        )
        low, mixed, failed = result["candidate_policy_outputs"][1:]
        self.assertEqual(
            "LOW_CONFIDENCE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
            low["policy_state"],
        )
        self.assertEqual(
            "MIXED_LANGUAGE_CACHE_POLICY_CANDIDATE_REVIEW_REQUIRED_NOT_QUEUED",
            mixed["policy_state"],
        )
        self.assertEqual(
            "FAILURE_ARTIFACT_REVIEW_REQUIRED_NO_AUTOMATIC_CLEANUP",
            failed["policy_state"],
        )
        self.assertEqual([1, 1, 1], [
            result["low_confidence_policy_candidate_count"],
            result["mixed_language_policy_candidate_count"],
            result["failed_page_policy_candidate_count"],
        ])
        self.assertFalse(low["high_trust_direct_entry_allowed"])
        self.assertFalse(mixed["high_trust_direct_entry_allowed"])
        self.assertFalse(failed["high_trust_direct_entry_allowed"])

    def test_temporary_and_failure_cleanup_boundaries_are_distinct(self):
        result = self._slice().execute_ocr_cache_retention_policy_control_slice(
            self._control()
        )
        temporary, failed = (
            result["candidate_policy_outputs"][0],
            result["candidate_policy_outputs"][3],
        )
        self.assertEqual(3, result["temporary_artifact_policy_candidate_count"])
        self.assertEqual(1, result["failure_artifact_policy_candidate_count"])
        self.assertEqual(
            "FUTURE_ELIGIBLE_IF_EXPLICITLY_IDENTIFIED_OWNER_APPROVED_AND_CAPACITY_APPROVED",
            temporary["cleanup_eligibility"],
        )
        self.assertEqual(
            "REBUILDABLE_TEMPORARY_IF_FUTURE_WRITE_AUTHORIZED",
            temporary["rebuildability"],
        )
        self.assertEqual("NOT_ELIGIBLE_FOR_AUTOMATIC_CLEANUP", failed["cleanup_eligibility"])
        self.assertEqual("REVIEW_REQUIRED_NO_AUTOMATIC_REBUILD", failed["rebuildability"])
        self.assertFalse(failed["cleanup_action_created"])

    def test_invalid_control_rejects_without_returning_reference_or_candidate_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_ocr_cache_retention_policy_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["candidate_policy_outputs"])
        self.assertEqual(0, result["cache_policy_candidate_count"])

    def test_cache_ocr_and_all_external_actions_remain_disabled(self):
        result = self._slice().execute_ocr_cache_retention_policy_control_slice(
            self._control()
        )
        for field in (
            "actual_cache_decision_created",
            "actual_cache_decision_persisted",
            "cache_created",
            "cache_write_performed",
            "cache_cleanup_performed",
            "physical_storage_path_created",
            "artifact_content_retained",
            "cleanup_action_created",
            "disk_scan_performed",
            "cache_capacity_evaluation_performed",
            "source_file_open_performed",
            "ocr_engine_selected",
            "ocr_engine_configuration_performed",
            "ocr_engine_invocation_performed",
            "language_detection_performed",
            "confidence_evaluation_performed",
            "actual_ocr_queue_created",
            "actual_page_output_created",
            "actual_ocr_text_created",
            "actual_page_image_reference_created",
            "actual_failure_record_created",
            "review_queue_created",
            "human_review_task_created",
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
            (batch, 'status: "stage056_phase2_completed"'),
            (batch, "stage056_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE056-P2"'),
            (batch, 'next_gate: "IDS-STAGE056-P3-GATE"'),
            (batch, "phase2_started: true"),
            (roadmap, 'current_stage_id: "IDS-STAGE056"'),
            (roadmap, 'current_phase_id: "IDS-STAGE056-P2"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE056-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE056-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE056", status["stage"])
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE056-P2",
                "IDS-V0_1-STAGE056-P3",
                "IDS-V0_1-STAGE056-P4",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE2_OCR_CACHE_RETENTION_POLICY_CONTROL_SLICE_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertFalse(run["observed_work"]["cache_write_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["phase3_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE056-P2-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE056-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-056"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE056-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
