import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
REVIEW = BASE / "STAGE048_STAGE_REVIEW.md"
REVIEW_MODULE = BASE / "parser_fallback" / "stage048_fallback_stage_review.py"
P1_CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_contract.json"
P2_CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_slice_contract.json"
P3_CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_scenarios_contract.json"
P4_CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_delivery_contract.json"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage048-review-local.json"


class Stage048ParserFallbackStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage048_review", REVIEW_MODULE)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage048_review_report()
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
        self.assertEqual("ids.stage048.parser_fallback.stage_review.v1", report["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE048-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-048", report["acceptance_id"])
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_FALLBACK_RUNTIME_DISABLED", report["result"]
        )
        self.assertEqual("IDS-STAGE049-P1-GATE", report["next_gate"])

    def test_review_preserves_single_authority_reference_only_boundary(self):
        report = self._report()
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE047_REVIEW_ARTIFACTS",
            report["source_authority"],
        )
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertFalse(report["raw_metadata_content_accessed"])
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])

    def test_review_replays_the_phase2_candidate_control_without_runtime(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual("NO_FALLBACK_CANDIDATE_RETAINED", replay["phase2_candidate_disposition"])
        self.assertEqual("FALLBACK_CANDIDATE_RETAINED", replay["phase2_candidate_feedback_code"])
        self.assertTrue(report["phase_results"]["phase2_slice_valid"])

    def test_review_replays_phase3_explicit_dispositions_and_instruction_invariance(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(14, replay["phase3_scenario_count"])
        self.assertEqual(14, replay["phase3_explicit_disposition_count"])
        self.assertEqual(0, replay["phase3_silent_drop_count"])
        self.assertTrue(report["phase_results"]["phase3_scenarios_valid"])
        self.assertTrue(
            report["review_invariants"]["instruction_text_invariance_preserved"]
        )

    def test_review_replays_phase4_delivery_boundary(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(8, replay["phase4_parser_output_sample_count"])
        self.assertEqual(14, replay["phase4_fallback_log_sample_count"])
        self.assertEqual(6, replay["phase4_failure_classification_count"])
        self.assertTrue(report["phase_results"]["phase4_delivery_valid"])
        self.assertTrue(
            report["review_invariants"]["format_and_runtime_boundary_preserved"]
        )

    def test_review_preserves_the_entire_rollback_chain(self):
        report = self._report()
        self.assertTrue(report["phase_results"]["phase1_contract_valid"])
        self.assertTrue(report["review_invariants"]["rollback_chain_preserved"])

    def test_review_has_no_runtime_or_external_actions(self):
        report = self._report()
        self.assertTrue(
            report["review_invariants"]["runtime_and_external_actions_disabled"]
        )
        for field in (
            "ids_business_source_read_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage049_started",
            "stage049_entry_allowed",
            "batch_review_performed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_governance_closes_stage048_only_to_a_separate_stage049_phase1_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage048_completed_reviewed_local"'),
            (batch, "stage048_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-REVIEW"'),
            (batch, 'next_allowed_task_id: "IDS-V0_1-STAGE049-P1"'),
            (batch, 'stage049_entry_authorized: false'),
            (roadmap, 'current_phase_id: "IDS-STAGE048-REVIEW"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE048-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-P1-GATE"'),
            (roadmap, 'status: "completed_reviewed_local"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(
            status["phase"],
            ("IDS-STAGE049-P4", "IDS-STAGE049-REVIEW", "IDS-STAGE050-P1", "IDS-STAGE050-P2"),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_review_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_FALLBACK_RUNTIME_DISABLED", run["result"].strip("`")
        )
        self.assertEqual(10, run["evidence_iterations"][0]["passed"])
        self.assertFalse(run["observed_work"]["parser_execution_performed"])
        self.assertFalse(run["observed_work"]["fallback_execution_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["stage049_started"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE048-REVIEW-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE048-REVIEW", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE049-P1-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(REVIEW.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
