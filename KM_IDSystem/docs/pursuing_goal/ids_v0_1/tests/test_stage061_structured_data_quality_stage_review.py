import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
REVIEW = BASE / "STAGE061_STAGE_REVIEW.md"
REVIEW_MODULE = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_stage_review.py"
)
P1_CONTRACT = BASE / "structured_table_facts" / "stage061_structured_data_quality_contract.json"
P2_CONTRACT = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_slice_contract.json"
)
P3_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_scenarios_contract.json"
)
P4_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage061_structured_data_quality_delivery_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage061-review-local.json"


class Stage061StructuredDataQualityStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage061_review", REVIEW_MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage061_review_report()
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
            "ids.stage061.structured_data_quality.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE061-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-061", report["acceptance_id"])
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE062-P1-GATE", report["next_gate"])

    def test_review_preserves_single_authority_boundary(self):
        report = self._report()
        self.assertEqual(
            "FROZEN_TASKPACK_AND_STAGE061_P1_TO_P4_AND_BATCH051_060_REVIEW_ARTIFACTS_ONLY",
            report["source_authority"],
        )
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertTrue(
            report["review_invariants"]["single_authority_boundary_preserved"]
        )

    def test_review_checks_phase1_and_phase2_contract_shapes(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(4, replay["phase_contract_count"])
        self.assertEqual(4, replay["phase_contract_passed_count"])
        self.assertEqual(16, replay["phase1_reference_input_field_count"])
        self.assertEqual(18, replay["phase1_future_quality_result_output_field_count"])
        self.assertEqual(5, replay["phase1_quality_dimension_count"])
        self.assertEqual(8, replay["phase1_semantic_field_count"])
        self.assertEqual(6, replay["phase1_source_location_field_count"])
        self.assertEqual(11, replay["phase1_declared_failure_state_count"])
        self.assertEqual(2, replay["phase2_control_record_count"])
        self.assertEqual(10, replay["phase2_quality_result_candidate_count"])
        self.assertEqual(5, replay["phase2_quality_dimension_count"])
        self.assertEqual(6, replay["phase2_source_location_field_count"])
        self.assertEqual(10, replay["phase2_source_location_binding_candidate_count"])
        self.assertTrue(report["phase_results"]["P1"])
        self.assertTrue(report["phase_results"]["P2"])
        self.assertTrue(
            report["review_invariants"]["source_location_and_evidence_boundary_preserved"]
        )

    def test_review_replays_phase3_explicit_dispositions_without_silent_drop(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(6, replay["quality_scenario_count"])
        self.assertEqual(6, replay["quality_explicit_disposition_count"])
        self.assertEqual(0, replay["quality_silent_drop_count"])
        self.assertEqual(6, replay["quality_human_handling_required_count"])
        self.assertEqual(1, replay["quality_outlier_numeric_block_count"])
        self.assertTrue(report["phase_results"]["P3"])
        self.assertTrue(
            report["review_invariants"]["quality_and_human_handling_boundary_preserved"]
        )

    def test_review_replays_phase4_metadata_only_delivery_and_human_handling(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(6, replay["delivery_sample_count"])
        self.assertEqual(6, replay["delivery_field_reference_label_count"])
        self.assertEqual(6, replay["delivery_quality_result_count"])
        self.assertEqual(6, replay["delivery_human_handling_record_count"])
        self.assertEqual(3, replay["delivery_human_confirmation_prompt_count"])
        self.assertTrue(report["phase_results"]["P4"])
        self.assertTrue(
            report["review_invariants"]["metadata_only_delivery_boundary_preserved"]
        )

    def test_review_preserves_numeric_and_rollback_boundaries(self):
        report = self._report()
        self.assertTrue(
            report["review_invariants"][
                "structured_fact_and_numeric_authority_boundary_preserved"
            ]
        )
        self.assertTrue(
            report["controlled_replay"]["reparse_and_fact_rollback_instructions_created"]
        )
        self.assertEqual(
            "PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertEqual(
            "PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["controlled_replay"]["reparse_and_fact_rollback_return_to"],
        )
        self.assertTrue(
            report["review_invariants"]["reparse_and_rollback_chain_preserved"]
        )

    def test_review_fails_closed_when_a_contract_or_report_is_incomplete(self):
        module = self._module()
        for report in (
            module.build_stage061_review_report(phase4_contract_provider=lambda: {}),
            module.build_stage061_review_report(phase3_report_provider=lambda: {}),
        ):
            with self.subTest(result=report["result"]):
                self.assertFalse(report["review_valid"])
                self.assertEqual(
                    "FAIL_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED",
                    report["result"],
                )
                self.assertEqual("IDS-STAGE061-REVIEW-GATE", report["next_gate"])

    def test_review_has_no_runtime_or_external_actions(self):
        report = self._report()
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "xlsx_or_csv_parse_performed",
            "real_structured_fact_extraction_performed",
            "real_table_quality_validation_performed",
            "actual_file_reparse_performed",
            "actual_fact_rollback_performed",
            "database_connection_performed",
            "agent_execution_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "batch_review_performed",
            "stage062_started",
            "stage062_entry_allowed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_governance_closes_stage061_and_allows_only_its_legal_successor(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage061_completed_reviewed_local"'),
            (batch, "stage061_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE061-REVIEW"'),
            (batch, 'next_allowed_task_id: "IDS-V0_1-STAGE062-P1"'),
            (batch, "stage062_phase1_entry_authorized: true"),
            (roadmap, 'current_phase_id: "IDS-STAGE061-REVIEW"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE061-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE062-P1-GATE"'),
            (roadmap, 'status: "completed_reviewed_local"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE061",
                    "IDS-V0_1-STAGE061-REVIEW",
                    "IDS-V0_1-STAGE061-REVIEW",
                    "IDS-STAGE062-P1-GATE",
                ),
                (
                    "IDS-STAGE062",
                    "IDS-V0_1-STAGE062-P1",
                    "IDS-V0_1-STAGE062-P1",
                    "IDS-STAGE062-P2-GATE",
                ),
                (
                    "IDS-STAGE062",
                    "IDS-V0_1-STAGE062-P2",
                    "IDS-V0_1-STAGE062-P2",
                    "IDS-STAGE062-P3-GATE",
                ),
                (
                    "IDS-STAGE062",
                    "IDS-V0_1-STAGE062-P3",
                    "IDS-V0_1-STAGE062-P3",
                    "IDS-STAGE062-P4-GATE",
                ),
                (
                    "IDS-STAGE062",
                    "IDS-V0_1-STAGE062-P4",
                    "IDS-V0_1-STAGE062-P4",
                    "IDS-STAGE062-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE062",
                    "IDS-STAGE062-REVIEW",
                    "IDS-V0_1-STAGE062-REVIEW",
                    "IDS-STAGE063-P1-GATE",
                ),
                (
                    "IDS-STAGE063",
                    "IDS-V0_1-STAGE063-P1",
                    "IDS-V0_1-STAGE063-P1",
                    "IDS-STAGE063-P2-GATE",
                ),
                (
                    "IDS-STAGE063",
                    "IDS-V0_1-STAGE063-P2",
                    "IDS-V0_1-STAGE063-P2",
                    "IDS-STAGE063-P3-GATE",
                ),
                (
                    "IDS-STAGE063",
                    "IDS-V0_1-STAGE063-P3",
                    "IDS-V0_1-STAGE063-P3",
                    "IDS-STAGE063-P4-GATE",
                ),
                (
                    "IDS-STAGE063",
                    "IDS-V0_1-STAGE063-P4",
                    "IDS-V0_1-STAGE063-P4",
                    "IDS-STAGE063-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE063",
                    "IDS-V0_1-STAGE063-REVIEW",
                    "IDS-V0_1-STAGE063-REVIEW",
                    "IDS-STAGE064-P1-GATE",
                ),
                (
                    "IDS-STAGE064",
                    "IDS-V0_1-STAGE064-P1",
                    "IDS-V0_1-STAGE064-P1",
                    "IDS-STAGE064-P2-GATE",
                ),
                (
                    "IDS-STAGE064",
                    "IDS-V0_1-STAGE064-P2",
                    "IDS-V0_1-STAGE064-P2",
                    "IDS-STAGE064-P3-GATE",
                ),
                (
                    "IDS-STAGE064",
                    "IDS-V0_1-STAGE064-P3",
                    "IDS-V0_1-STAGE064-P3",
                    "IDS-STAGE064-P4-GATE",
                ),
                (
                    "IDS-STAGE064",
                    "IDS-V0_1-STAGE064-P4",
                    "IDS-V0_1-STAGE064-P4",
                    "IDS-STAGE064-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE064",
                    "IDS-V0_1-STAGE064-REVIEW",
                    "IDS-V0_1-STAGE064-REVIEW",
                    "IDS-STAGE065-P1-GATE",
                ),
                (
                    "IDS-STAGE065",
                    "IDS-V0_1-STAGE065-P1",
                    "IDS-V0_1-STAGE065-P1",
                    "IDS-STAGE065-P2-GATE",
                ),
                (
                    "IDS-STAGE065",
                    "IDS-V0_1-STAGE065-P2",
                    "IDS-V0_1-STAGE065-P2",
                    "IDS-STAGE065-P3-GATE",
                ),
                (
                    "IDS-STAGE065",
                    "IDS-V0_1-STAGE065-P3",
                    "IDS-V0_1-STAGE065-P3",
                    "IDS-STAGE065-P4-GATE",
                ),
                (
                    "IDS-STAGE065",
                    "IDS-V0_1-STAGE065-P4",
                    "IDS-V0_1-STAGE065-P4",
                    "IDS-STAGE065-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE065",
                    "IDS-V0_1-STAGE065-REVIEW",
                    "IDS-V0_1-STAGE065-REVIEW",
                    "IDS-STAGE066-P1-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-V0_1-STAGE066-P1",
                    "IDS-STAGE066-P2-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-V0_1-STAGE066-P2",
                    "IDS-STAGE066-P3-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-V0_1-STAGE066-P3",
                    "IDS-STAGE066-P4-GATE",
                ),
                (
                    "IDS-STAGE066",
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-V0_1-STAGE066-P4",
                    "IDS-STAGE066-REVIEW-GATE",
                ),
                ("IDS-STAGE066", "IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-STAGE067", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
("IDS-STAGE070", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_review_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_STRUCTURED_DATA_QUALITY_RUNTIME_DISABLED",
            run["result"].strip(),
        )
        self.assertFalse(run["observed_work"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertTrue(run["observed_work"]["whole_stage_review_performed"])
        self.assertFalse(run["observed_work"]["batch_review_performed"])
        self.assertFalse(run["observed_work"]["stage062_started"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE061-REVIEW-20260814-001"
        )
        self.assertEqual("stage_review", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE061-REVIEW", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE062-P1-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(REVIEW.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
