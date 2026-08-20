import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-071_Embedding成本治理器.md"
)
REVIEW_DOCUMENT = BASE / "STAGE071_STAGE_REVIEW.md"
MODULE = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_stage_review.py"
PHASE1_CONTRACT = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_contract.json"
PHASE2_CONTRACT = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_slice_contract.json"
PHASE3_CONTRACT = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_scenarios_contract.json"
PHASE4_CONTRACT = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_delivery_contract.json"
P2_MODULE = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_slice.py"
P3_MODULE = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_scenarios.py"
P4_MODULE = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_delivery.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage071-review-local.json"


class Stage071EmbeddingCostGovernorStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage071_review", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage071_review_report()
        return self.__class__._report_value

    def test_review_artifacts_exist(self):
        for artifact in (
            TASKPACK,
            REVIEW_DOCUMENT,
            MODULE,
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE3_CONTRACT,
            PHASE4_CONTRACT,
            P2_MODULE,
            P3_MODULE,
            P4_MODULE,
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

    def test_review_passes_all_phase_contracts_and_reports(self):
        report = self._report()
        self.assertEqual(
            "ids.stage071.embedding_cost_governor.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE071-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-071", report["acceptance_id"])
        self.assertTrue(report["review_valid"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_COST_GOVERNOR_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE072-P1-GATE", report["next_gate"])
        self.assertEqual(
            {"P1": True, "P2": True, "P3": True, "P4": True},
            report["phase_results"],
        )

    def test_review_replays_fixed_control_counts(self):
        replay = self._report()["controlled_replay"]
        expected = {
            "phase1_reference_input_field_count": 16,
            "phase1_future_cost_governor_field_count": 16,
            "phase1_budget_scope_count": 3,
            "phase1_future_queue_field_count": 12,
            "phase1_future_cache_field_count": 10,
            "phase1_future_retry_field_count": 7,
            "phase1_future_model_field_count": 8,
            "phase1_future_audit_field_count": 18,
            "phase1_failure_state_count": 14,
            "phase2_control_request_count": 7,
            "phase2_policy_resolution_count": 7,
            "phase2_policy_resolution_field_count": 10,
            "phase2_cost_governor_record_count": 7,
            "phase2_cost_governor_record_field_count": 18,
            "phase2_queue_record_count": 7,
            "phase2_queue_record_field_count": 14,
            "phase2_cache_record_count": 7,
            "phase2_cache_record_field_count": 10,
            "phase2_retry_record_count": 7,
            "phase2_retry_record_field_count": 7,
            "phase2_audit_projection_count": 7,
            "phase2_audit_field_count": 18,
            "phase2_policy_denied_count": 1,
            "phase2_three_budget_pause_count": 3,
            "phase2_eligible_not_persisted_count": 3,
            "phase3_scenario_count": 7,
            "phase3_scenario_field_count": 35,
            "phase3_explicit_disposition_count": 7,
            "phase3_silent_drop_count": 0,
            "phase3_human_handling_required_count": 6,
            "phase3_audit_field_count": 18,
            "phase3_audit_field_check_count": 126,
            "phase3_future_external_api_call_candidate_count": 3,
            "phase3_denied_count": 1,
            "phase3_summary_only_count": 2,
            "phase3_full_text_control_count": 1,
            "phase3_three_budget_pause_count": 3,
            "phase4_policy_sample_count": 7,
            "phase4_audit_sample_count": 7,
            "phase4_audit_field_count": 18,
            "phase4_audit_field_check_count": 126,
            "phase4_cost_sample_count": 7,
            "phase4_failure_handling_count": 7,
            "phase4_non_externalized_record_count": 7,
            "phase4_query_key_count": 7,
            "phase4_chinese_confirmation_count": 4,
            "phase4_failure_state_count": 12,
        }
        self.assertEqual(expected, replay)

    def test_review_preserves_authority_audit_and_rollback_boundaries(self):
        report = self._report()
        self.assertTrue(all(report["review_invariants"].values()))
        self.assertEqual(
            "PHASE4_EMBEDDING_COST_GOVERNOR_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(report["rollback"]["preserve_phase1_to_phase4_evidence"])
        self.assertFalse(report["rollback"]["github_or_ovh_change_allowed"])
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])

    def test_review_keeps_runtime_and_stage072_closed(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chunking_execution_performed",
            "cost_estimation_execution_performed",
            "batch_budget_lookup_performed",
            "monthly_budget_lookup_performed",
            "task_cap_evaluation_performed",
            "external_payload_created",
            "external_api_call_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "embedding_queue_execution_performed",
            "cache_read_or_write_performed",
            "failed_retry_execution_performed",
            "actual_external_api_audit_record_created",
            "actual_audit_log_query_performed",
            "actual_externalization_record_query_performed",
            "actual_policy_rollback_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage072_started",
            "batch_review_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_stage071_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE071-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_stage071_review_report(
            phase3_report_provider=lambda: {"result": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE071-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_stage071_review_report(
            phase2_report_provider=lambda: {"input_accepted": True}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE071-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_stage071_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual("IDS-STAGE071-REVIEW-GATE", report["next_gate"])

    def test_governance_projection_records_stage_review(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(
            (
                "IDS-STAGE071",
                "IDS-V0_1-STAGE071-REVIEW",
                "IDS-V0_1-STAGE071-REVIEW",
                "IDS-STAGE072-P1-GATE",
            ),
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertEqual(
            ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW"),
            (plan["stage"], plan["phase"], plan["task"]),
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE071-REVIEW-01"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE071-REVIEW-02"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE071-REVIEW-03"])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE071-REVIEW-04"])
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE071-REVIEW-20260820-001"
        )
        self.assertEqual("stage_review", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE071-REVIEW", event["task_id"])
        self.assertEqual("IDS-STAGE072-P1-GATE", run["next_gate"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_COST_GOVERNOR_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))


if __name__ == "__main__":
    unittest.main()
