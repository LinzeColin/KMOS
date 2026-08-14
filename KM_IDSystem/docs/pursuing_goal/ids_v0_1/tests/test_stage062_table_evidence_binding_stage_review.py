import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TABLE_FACTS = BASE / "structured_table_facts"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-062_表格证据绑定.md"
)
REVIEW = BASE / "STAGE062_STAGE_REVIEW.md"
MODULE = TABLE_FACTS / "stage062_table_evidence_binding_stage_review.py"
TEST = Path(__file__)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage062-review-local.json"

PHASE_ARTIFACTS = (
    BASE / "STAGE062_PHASE1_TABLE_EVIDENCE_BINDING_SCOPE_BOUNDARY.md",
    TABLE_FACTS / "stage062_table_evidence_binding_contract.json",
    BASE / "tests" / "test_stage062_table_evidence_binding_contract.py",
    BASE / "STAGE062_PHASE2_TABLE_EVIDENCE_BINDING_CONTROL_SLICE.md",
    TABLE_FACTS / "stage062_table_evidence_binding_slice_contract.json",
    TABLE_FACTS / "stage062_table_evidence_binding_slice.py",
    BASE / "tests" / "test_stage062_table_evidence_binding_slice.py",
    BASE / "STAGE062_PHASE3_TABLE_EVIDENCE_BINDING_SCENARIOS.md",
    TABLE_FACTS / "stage062_table_evidence_binding_scenarios_contract.json",
    TABLE_FACTS / "stage062_table_evidence_binding_scenarios.py",
    BASE / "tests" / "test_stage062_table_evidence_binding_scenarios.py",
    BASE / "STAGE062_PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_CLOSEOUT.md",
    TABLE_FACTS / "stage062_table_evidence_binding_delivery_contract.json",
    TABLE_FACTS / "stage062_table_evidence_binding_delivery.py",
    BASE / "tests" / "test_stage062_table_evidence_binding_delivery.py",
)
EXPECTED_SCENARIO_IDS = (
    "empty-table-binding-control-human-handling",
    "merged-cells-binding-control-human-handling",
    "unit-confusion-binding-control-human-handling",
    "date-variation-binding-control-human-handling",
    "outlier-binding-control-numeric-block",
    "duplicate-row-binding-control-human-handling",
)


class Stage062TableEvidenceBindingStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage062_review", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage062_review_report()
        return self.__class__._report_value

    def test_review_artifacts_and_predecessor_artifacts_exist(self):
        for artifact in (
            TASKPACK,
            *PHASE_ARTIFACTS,
            REVIEW,
            MODULE,
            TEST,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_review_passes_only_when_all_four_phase_evidences_hold(self):
        report = self._report()
        self.assertEqual(
            "ids.stage062.table_evidence_binding.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE062-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-062", report["acceptance_id"])
        self.assertTrue(report["review_valid"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE063-P1-GATE", report["next_gate"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])
        self.assertEqual(0, report["review_finding_count"])

    def test_review_replays_only_declared_control_counts(self):
        replay = self._report()["controlled_replay"]
        self.assertEqual(19, replay["phase1_reference_only_binding_input_field_count"])
        self.assertEqual(17, replay["phase1_future_binding_output_field_count"])
        self.assertEqual(2, replay["phase2_control_binding_request_count"])
        self.assertEqual(2, replay["phase2_control_binding_candidate_count"])
        self.assertEqual(12, replay["phase2_control_binding_dimension_reference_count"])
        self.assertEqual(6, replay["phase3_controlled_scenario_count"])
        self.assertEqual(6, replay["phase3_explicit_disposition_count"])
        self.assertEqual(0, replay["phase3_silent_drop_count"])
        self.assertEqual(6, replay["phase3_report_scenario_count"])
        self.assertEqual(6, replay["phase4_delivery_sample_count"])
        self.assertEqual(6, replay["phase4_field_reference_label_count"])
        self.assertEqual(6, replay["phase4_quality_test_result_delivery_count"])
        self.assertEqual(6, replay["phase4_human_handling_recommendation_count"])
        self.assertEqual(3, replay["phase4_human_confirmation_prompt_count"])
        self.assertEqual(6, replay["phase4_report_delivery_sample_count"])
        self.assertEqual(
            "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            replay["phase4_return_to"],
        )

    def test_review_preserves_all_control_boundaries(self):
        invariants = self._report()["review_invariants"]
        self.assertTrue(all(invariants.values()))
        self.assertTrue(invariants["frozen_taskpack_available"])
        self.assertTrue(invariants["single_authority_boundary_preserved"])
        self.assertTrue(invariants["binding_dimension_and_traceability_boundary_preserved"])
        self.assertTrue(invariants["numeric_authority_boundary_preserved"])
        self.assertTrue(invariants["six_exception_categories_require_human_handling"])
        self.assertTrue(invariants["metadata_only_delivery_boundary_preserved"])
        self.assertTrue(invariants["reparse_and_rollback_chain_preserved"])
        self.assertTrue(invariants["runtime_actions_disabled"])
        self.assertTrue(invariants["stage063_not_started"])

    def test_review_exposes_no_runtime_or_external_actions(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "table_summary_generation_performed",
            "numeric_statistic_computation_performed",
            "quality_gate_evaluation_performed",
            "source_location_binding_performed",
            "evidence_binding_performed",
            "database_connection_performed",
            "structured_fact_write_performed",
            "quality_result_write_performed",
            "persistent_state_write_performed",
            "actual_file_reparse_performed",
            "actual_fact_rollback_performed",
            "actual_table_evidence_binding_rollback_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "batch_review_performed",
            "stage063_started",
            "stage063_entry_allowed",
            "github_upload_performed",
            "github_upload_allowed",
            "push_performed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_review_keeps_six_control_scenarios_and_human_handling(self):
        module = self._module()
        phase3_report = module._load_phase3_report_provider()()
        phase4_report = module._load_phase4_report_provider()()
        scenarios = phase3_report["scenario_results"]
        self.assertEqual(EXPECTED_SCENARIO_IDS, tuple(item["scenario_id"] for item in scenarios))
        self.assertTrue(all(item["human_handling_required"] for item in scenarios))
        self.assertTrue(all(item["silent_drop"] is False for item in scenarios))
        handling = {
            item["scenario_id"]: item
            for item in phase4_report["unrecognized_structure_and_human_handling"]
        }
        self.assertEqual(6, len(handling))
        self.assertEqual(
            "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
            handling["merged-cells-binding-control-human-handling"][
                "handling_disposition"
            ],
        )

    def test_invalid_phase1_contract_fails_closed_to_review_gate(self):
        report = self._module().build_stage062_review_report(
            phase1_contract_provider=lambda: {},
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual(
            "FAIL_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE062-REVIEW-GATE", report["next_gate"])
        self.assertEqual(1, report["review_finding_count"])

    def test_invalid_phase4_delivery_report_fails_closed_to_review_gate(self):
        report = self._module().build_stage062_review_report(
            phase4_report_provider=lambda: {},
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE062-REVIEW-GATE", report["next_gate"])

    def test_governance_moves_only_to_stage063_phase1_gate(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE062"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE062-REVIEW"', roadmap)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE062-REVIEW"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE063-P1-GATE"', roadmap)
        self.assertIn('status: "stage062_completed_reviewed_local"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE062-REVIEW"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE063-P1"', batch)
        self.assertIn('stage063_phase1_entry_authorized: true', batch)
        self.assertIn('github_upload_allowed: false', batch)
        self.assertIn('push_allowed: false', batch)

    def test_machine_facts_event_and_run_record_review_without_runtime(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE062-REVIEW-20260814-001"
        )
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-STAGE062", "IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
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
            ),
        )
        self.assertIn(
            (plan["stage"], plan["phase"], plan["task"]),
            (
                ("IDS-STAGE062", "IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE062-REVIEW"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P1"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P2"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P3"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-P4"),
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2"), ("IDS-STAGE067", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW"),
            ),
        )
        self.assertIn("ACC-STAGE062-REVIEW-01", str(acceptance))
        self.assertEqual("IDS-V0_1-STAGE062-REVIEW", event["task_id"])
        self.assertEqual("RUN-IDS-STAGE062-REVIEW-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE062", run["stage"])
        self.assertEqual("IDS-V0_1-STAGE062-REVIEW", run["task_id"])
        self.assertEqual("IDS-STAGE063-P1-GATE", run["next_gate"])
        observed = run["observed_work"]
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "xlsx_or_csv_parse_performed",
            "structured_fact_extraction_performed",
            "actual_table_evidence_binding_created",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(observed[field])


if __name__ == "__main__":
    unittest.main()
