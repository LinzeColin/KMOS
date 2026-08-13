import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
REVIEW = BASE / "STAGE051_STAGE_REVIEW.md"
REVIEW_MODULE = BASE / "ocr_queue" / "stage051_ocr_queue_stage_review.py"
P1_CONTRACT = BASE / "ocr_queue" / "stage051_ocr_queue_contract.json"
P2_CONTRACT = BASE / "ocr_queue" / "stage051_ocr_queue_slice_contract.json"
P3_CONTRACT = BASE / "ocr_queue" / "stage051_ocr_queue_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "ocr_queue" / "stage051_ocr_queue_delivery_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage051-review-local.json"


class Stage051OcrQueueStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage051_review", REVIEW_MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage051_review_report()
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
        self.assertEqual("ids.stage051.ocr_queue.stage_review.v1", report["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE051-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-051", report["acceptance_id"])
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_OCR_QUEUE_RUNTIME_DISABLED", report["result"]
        )
        self.assertEqual("IDS-STAGE052-P1-GATE", report["next_gate"])

    def test_review_preserves_single_authority_reference_only_boundary(self):
        report = self._report()
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_STAGE051_P1_TO_P4_AND_BATCH041_050_REVIEW_ARTIFACTS",
            report["source_authority"],
        )
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertFalse(report["raw_metadata_content_accessed"])
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])

    def test_review_checks_phase1_and_phase2_shape_without_returning_control_text(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(7, replay["phase1_reference_input_field_count"])
        self.assertEqual(8, replay["phase1_per_page_output_field_count"])
        self.assertEqual(2, replay["phase1_default_language_count"])
        self.assertEqual(4, replay["phase2_control_page_count"])
        self.assertEqual(4, replay["phase2_explicit_page_state_count"])
        self.assertTrue(report["phase_results"]["phase1_contract_valid"])
        self.assertTrue(report["phase_results"]["phase2_slice_valid"])
        self.assertNotIn("control_text", replay)
        self.assertNotIn("ocr_text", replay)

    def test_review_replays_phase3_explicit_dispositions_without_silent_drop(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(5, replay["phase3_scenario_count"])
        self.assertEqual(5, replay["phase3_explicit_disposition_count"])
        self.assertEqual(0, replay["phase3_silent_drop_count"])
        self.assertTrue(report["phase_results"]["phase3_scenarios_valid"])
        self.assertTrue(
            report["review_invariants"][
                "explicit_disposition_and_no_silent_drop_preserved"
            ]
        )

    def test_review_replays_metadata_only_phase4_delivery_boundary(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(5, replay["phase4_delivery_metadata_only_sample_count"])
        self.assertEqual(
            {"HIGH": 2, "MEDIUM": 1, "LOW": 1, "UNKNOWN": 1},
            replay["phase4_confidence_counts"],
        )
        self.assertEqual(1, replay["phase4_failure_list_count"])
        self.assertEqual(2, replay["phase4_review_route_proof_count"])
        self.assertEqual(3, replay["phase4_human_confirmation_prompt_count"])
        self.assertTrue(report["phase_results"]["phase4_delivery_valid"])
        self.assertTrue(
            report["review_invariants"]["metadata_only_delivery_boundary_preserved"]
        )

    def test_review_preserves_quality_limit_cache_and_rollback_chain(self):
        report = self._report()
        invariants = report["review_invariants"]
        self.assertTrue(invariants["quality_limit_and_confirmation_boundary_preserved"])
        self.assertTrue(invariants["cache_and_rerun_boundary_preserved"])
        self.assertTrue(invariants["rollback_chain_preserved"])

    def test_review_fails_closed_when_a_contract_is_incomplete(self):
        contracts = {
            "phase1": json.loads(P1_CONTRACT.read_text(encoding="utf-8")),
            "phase2": json.loads(P2_CONTRACT.read_text(encoding="utf-8")),
            "phase3": json.loads(P3_CONTRACT.read_text(encoding="utf-8")),
            "phase4": {},
        }
        report = self._module().build_stage051_review_report(
            contract_provider=lambda: contracts
        )
        self.assertFalse(report["review_valid"])
        self.assertEqual("FAIL_CLOSED_STAGE051_OCR_QUEUE_REVIEW", report["result"])
        self.assertEqual("IDS-STAGE051-REVIEW-GATE", report["next_gate"])

    def test_review_has_no_runtime_or_external_actions(self):
        report = self._report()
        self.assertTrue(
            report["review_invariants"]["runtime_and_external_actions_disabled"]
        )
        for field in (
            "ids_business_source_read_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "ocr_engine_invocation_performed",
            "cache_write_performed",
            "review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage052_started",
            "stage052_entry_allowed",
            "batch_review_performed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_governance_closes_stage051_only_to_a_separate_stage052_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage051_completed_reviewed_local"'),
            (batch, "stage051_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE051-REVIEW"'),
            (batch, 'next_allowed_task_id: "IDS-V0_1-STAGE052-P1"'),
            (batch, "stage052_entry_authorized: false"),
            (roadmap, 'current_phase_id: "IDS-STAGE051-REVIEW"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE051-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE052-P1-GATE"'),
            (roadmap, 'status: "completed_reviewed_local"'),
            (batch, 'status: "stage052_phase1_completed"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE052-P1"'),
            (batch, 'next_gate: "IDS-STAGE052-P2-GATE"'),
            (roadmap, 'current_stage_id: "IDS-STAGE052"'),
            (roadmap, 'current_phase_id: "IDS-STAGE052-P1"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(
            status["phase"],
            (
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
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_review_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_OCR_QUEUE_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertEqual(11, run["evidence_iterations"][0]["passed"])
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["review_queue_write_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["stage052_started"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE051-REVIEW-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE051-REVIEW", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE052-P1-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(REVIEW.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
