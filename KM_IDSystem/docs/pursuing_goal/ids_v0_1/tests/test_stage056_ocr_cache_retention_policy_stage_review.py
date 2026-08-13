import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
REVIEW = BASE / "STAGE056_STAGE_REVIEW.md"
REVIEW_MODULE = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_stage_review.py"
P1_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_contract.json"
P2_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_slice_contract.json"
P3_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_delivery_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage056-review-local.json"


class Stage056OcrCacheRetentionPolicyStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage056_review", REVIEW_MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage056_review_report()
        return self.__class__._report_value

    def test_review_artifacts_exist(self):
        for artifact in (
            REVIEW,
            REVIEW_MODULE,
            P1_CONTRACT,
            P2_CONTRACT,
            P3_CONTRACT,
            P4_CONTRACT,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_review_identity_and_local_result(self):
        report = self._report()
        self.assertEqual(
            "ids.stage056.ocr_cache_retention_policy.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE056-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-056", report["acceptance_id"])
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_OCR_CACHE_RETENTION_POLICY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE057-P1-GATE", report["next_gate"])

    def test_review_preserves_single_authority_reference_only_boundary(self):
        report = self._report()
        self.assertEqual(
            "FROZEN_TASKPACK_AND_STAGE056_P1_TO_P4_CONTROLLED_ARTIFACTS_ONLY",
            report["source_authority"],
        )
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertFalse(report["raw_metadata_content_accessed"])
        self.assertTrue(
            report["review_invariants"]["single_authority_boundary_preserved"]
        )
        rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("source-page:control:", rendered)
        self.assertNotIn("cache-entry:control:", rendered)

    def test_review_checks_phase1_and_phase2_contract_shapes(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(4, replay["phase_contract_count"])
        self.assertEqual(4, replay["phase_contract_passed_count"])
        self.assertEqual(11, replay["phase1_reference_input_field_count"])
        self.assertEqual(10, replay["phase1_future_output_field_count"])
        self.assertEqual(4, replay["phase2_control_policy_candidate_count"])
        self.assertTrue(report["phase_results"]["P1"])
        self.assertTrue(report["phase_results"]["P2"])
        self.assertTrue(report["review_invariants"]["input_and_output_shape_preserved"])

    def test_review_replays_phase3_explicit_dispositions_without_silent_drop(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(5, replay["quality_scenario_count"])
        self.assertEqual(5, replay["quality_explicit_disposition_count"])
        self.assertEqual(0, replay["quality_silent_drop_count"])
        self.assertEqual(3, replay["quality_declared_review_route_count"])
        self.assertTrue(report["phase_results"]["P3"])
        self.assertTrue(
            report["review_invariants"]["quality_limit_and_confirmation_boundary_preserved"]
        )

    def test_review_replays_metadata_only_phase4_delivery_boundary(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(5, replay["delivery_sample_count"])
        self.assertEqual(
            {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1},
            replay["delivery_confidence_counts"],
        )
        self.assertEqual(1, replay["delivery_failure_list_count"])
        self.assertEqual(3, replay["delivery_review_route_proof_count"])
        self.assertEqual(3, replay["delivery_human_confirmation_prompt_count"])
        self.assertTrue(report["phase_results"]["P4"])
        self.assertTrue(
            report["review_invariants"]["metadata_only_delivery_boundary"]
        )

    def test_review_preserves_cache_and_rollback_chain(self):
        invariants = self._report()["review_invariants"]
        self.assertTrue(invariants["cache_and_rerun_boundary_preserved"])
        self.assertTrue(invariants["rollback_chain_preserved"])

    def test_review_fails_closed_when_a_contract_is_incomplete(self):
        report = self._module().build_stage056_review_report(
            phase4_contract_provider=lambda: {}
        )
        self.assertFalse(report["review_valid"])
        self.assertEqual(
            "FAIL_REVIEWED_LOCAL_OCR_CACHE_RETENTION_POLICY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE056-REVIEW-GATE", report["next_gate"])

    def test_review_has_no_runtime_or_external_actions(self):
        report = self._report()
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        for field in (
            "ids_business_source_read_performed",
            "real_business_source_read",
            "actual_ocr_executed",
            "persistent_cache_written",
            "automatic_business_write_executed",
            "production_operation_executed",
            "github_operation_executed",
            "github_upload_performed",
            "ovh_operation_executed",
            "model_token_consumed",
            "agent_runtime_executed",
            "stage057_started",
            "stage057_entry_allowed",
            "batch_review_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_governance_closes_stage056_only_to_a_separate_stage057_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage056_completed_reviewed_local"'),
            (batch, "stage056_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE056-REVIEW"'),
            (batch, 'next_allowed_task_id: "IDS-V0_1-STAGE057-P1"'),
            (batch, "stage057_entry_authorized: false"),
            (roadmap, 'current_phase_id: "IDS-STAGE056-REVIEW"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE056-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE057-P1-GATE"'),
            (roadmap, 'status: "completed_reviewed_local"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE056", "IDS-STAGE057", "IDS-STAGE058", "IDS-STAGE059"))
        self.assertIn(
            status["phase"],
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_review_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_OCR_CACHE_RETENTION_POLICY_RUNTIME_DISABLED",
            run["result"].strip(),
        )
        self.assertFalse(run["observed_work"]["actual_ocr_executed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertTrue(run["observed_work"]["whole_stage_review_performed"])
        self.assertFalse(run["observed_work"]["stage057_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE056-REVIEW-20260813-001"
        )
        self.assertEqual("stage_review", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE056-REVIEW", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE057-P1-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(REVIEW.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
