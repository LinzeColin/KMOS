import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
REVIEW = BASE / "STAGE057_STAGE_REVIEW.md"
REVIEW_MODULE = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_stage_review.py"
P1_CONTRACT = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_contract.json"
P2_CONTRACT = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_slice_contract.json"
P3_CONTRACT = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_quality_scenarios_contract.json"
P4_CONTRACT = BASE / "structured_table_facts" / "stage057_xlsx_csv_ingestion_delivery_contract.json"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage057-review-local.json"


class Stage057XlsxCsvIngestionStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage057_review", REVIEW_MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage057_review_report()
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
            "ids.stage057.xlsx_csv_ingestion.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE057-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-057", report["acceptance_id"])
        self.assertTrue(report["review_valid"], report)
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE058-P1-GATE", report["next_gate"])

    def test_review_preserves_single_authority_boundary(self):
        report = self._report()
        self.assertEqual(
            "FROZEN_TASKPACK_AND_STAGE057_P1_TO_P4_CONTROLLED_ARTIFACTS_ONLY",
            report["source_authority"],
        )
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertTrue(
            report["review_invariants"]["single_authority_boundary_preserved"]
        )
        rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("source-document:control:", rendered)
        self.assertNotIn("worksheet:control:", rendered)

    def test_review_checks_phase1_and_phase2_contract_shapes(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(4, replay["phase_contract_count"])
        self.assertEqual(4, replay["phase_contract_passed_count"])
        self.assertEqual(12, replay["phase1_reference_input_field_count"])
        self.assertEqual(19, replay["phase1_future_structured_fact_output_field_count"])
        self.assertEqual(7, replay["phase1_field_semantic_count"])
        self.assertEqual(5, replay["phase1_source_location_field_count"])
        self.assertEqual(6, replay["phase1_declared_failure_state_count"])
        self.assertEqual(2, replay["phase2_control_record_count"])
        self.assertEqual(2, replay["phase2_schema_profile_candidate_count"])
        self.assertEqual(10, replay["phase2_structured_fact_candidate_count"])
        self.assertEqual(2, replay["phase2_rag_summary_candidate_count"])
        self.assertTrue(report["phase_results"]["P1"])
        self.assertTrue(report["phase_results"]["P2"])
        self.assertTrue(
            report["review_invariants"]["input_and_output_shape_preserved"]
        )

    def test_review_replays_phase3_explicit_dispositions_without_silent_drop(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(6, replay["quality_scenario_count"])
        self.assertEqual(6, replay["quality_explicit_disposition_count"])
        self.assertEqual(0, replay["quality_silent_drop_count"])
        self.assertEqual(1, replay["quality_outlier_numeric_block_count"])
        self.assertTrue(report["phase_results"]["P3"])
        self.assertTrue(
            report["review_invariants"]["quality_and_human_handling_boundary_preserved"]
        )

    def test_review_replays_phase4_metadata_only_delivery_and_human_handling(self):
        report = self._report()
        replay = report["controlled_replay"]
        self.assertEqual(6, replay["delivery_sample_count"])
        self.assertEqual(5, replay["delivery_field_reference_label_count"])
        self.assertEqual(6, replay["delivery_quality_result_count"])
        self.assertEqual(6, replay["delivery_human_handling_record_count"])
        self.assertEqual(3, replay["delivery_human_confirmation_prompt_count"])
        self.assertTrue(report["phase_results"]["P4"])
        self.assertTrue(
            report["review_invariants"]["metadata_only_delivery_boundary"]
        )

    def test_review_preserves_reparse_and_rollback_chain(self):
        report = self._report()
        self.assertTrue(
            report["controlled_replay"]["reparse_and_fact_rollback_instructions_created"]
        )
        self.assertEqual(
            "PHASE4_XLSX_CSV_INGESTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(
            report["review_invariants"]["reparse_and_rollback_chain_preserved"]
        )

    def test_review_fails_closed_when_a_contract_or_report_is_incomplete(self):
        module = self._module()
        for report in (
            module.build_stage057_review_report(phase4_contract_provider=lambda: {}),
            module.build_stage057_review_report(phase3_report_provider=lambda: {}),
        ):
            with self.subTest(result=report["result"]):
                self.assertFalse(report["review_valid"])
                self.assertEqual(
                    "FAIL_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED",
                    report["result"],
                )
                self.assertEqual("IDS-STAGE058-P1-GATE", report["next_gate"])

    def test_review_has_no_runtime_or_external_actions(self):
        report = self._report()
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "xlsx_or_csv_parse_performed",
            "real_table_schema_inference_performed",
            "real_table_quality_validation_performed",
            "actual_file_reparse_performed",
            "actual_fact_rollback_performed",
            "database_connection_performed",
            "agent_execution_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage058_started",
            "stage058_entry_allowed",
            "batch_review_performed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_governance_closes_stage057_only_to_a_separate_stage058_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage057_completed_reviewed_local"'),
            (batch, "stage057_review_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE057-REVIEW"'),
            (batch, 'next_allowed_task_id: "IDS-V0_1-STAGE058-P1"'),
            (batch, "stage058_entry_authorized: false"),
            (roadmap, 'current_phase_id: "IDS-STAGE057-REVIEW"'),
            (roadmap, 'current_task_id: "IDS-V0_1-STAGE057-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE058-P1-GATE"'),
            (roadmap, 'status: "completed_reviewed_local"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE057", "IDS-STAGE058", "IDS-STAGE059", "IDS-STAGE060"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE057-REVIEW",
                "IDS-V0_1-STAGE058-P1",
            "IDS-V0_1-STAGE058-P2",
            "IDS-V0_1-STAGE058-P3",
            "IDS-V0_1-STAGE058-P4",
            "IDS-V0_1-STAGE058-REVIEW",
            "IDS-V0_1-STAGE059-P1",
            "IDS-V0_1-STAGE059-P2",
            "IDS-V0_1-STAGE059-P3",
            "IDS-V0_1-STAGE059-P4",
            "IDS-V0_1-STAGE059-REVIEW",
            "IDS-V0_1-STAGE060-P1", "IDS-V0_1-STAGE060-P2", "IDS-V0_1-STAGE060-P3",
            "IDS-V0_1-STAGE060-P4",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_review_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_XLSX_CSV_INGESTION_RUNTIME_DISABLED",
            run["result"].strip(),
        )
        self.assertFalse(run["observed_work"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertTrue(run["observed_work"]["whole_stage_review_performed"])
        self.assertFalse(run["observed_work"]["stage058_started"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE057-REVIEW-20260813-001"
        )
        self.assertEqual("stage_review", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE057-REVIEW", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE058-P1-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(REVIEW.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
