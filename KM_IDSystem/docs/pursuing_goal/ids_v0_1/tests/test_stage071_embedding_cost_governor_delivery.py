import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_slice_contract.json"
)
PHASE2_SLICE = (
    BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_slice.py"
)
PHASE3_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_scenarios_contract.json"
)
PHASE3_SCENARIOS = (
    BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_scenarios.py"
)
CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_delivery_contract.json"
)
DELIVERY = (
    BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_delivery.py"
)
SCOPE = BASE / "STAGE071_PHASE4_EMBEDDING_COST_GOVERNOR_DELIVERY_CLOSEOUT.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-071_Embedding成本治理器.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE070_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "embedding_queue_cache"
    / "stage070_embedding_queue_cache_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"


class Stage071EmbeddingCostGovernorPhase4Tests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("stage071_p4_delivery", DELIVERY)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            PHASE3_CONTRACT,
            PHASE3_SCENARIOS,
            CONTRACT,
            DELIVERY,
            SCOPE,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            BATCH,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_has_exact_p4_scope_and_runtime_remains_closed(self):
        contract = self._contract()
        module = self._module()
        self.assertEqual(
            "ids.stage071.embedding_cost_governor.phase4.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE071-P4", contract["task_id"])
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE071-REVIEW-GATE", contract["next_gate"])
        replay = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(7, replay["scenario_count"])
        self.assertEqual(35, replay["scenario_field_count"])
        self.assertEqual(18, replay["external_api_audit_projection_field_count"])
        self.assertEqual(3, replay["future_external_api_call_candidate_count"])
        delivery = contract["delivery_evidence_contract"]
        self.assertEqual(7, delivery["policy_sample_count"])
        self.assertEqual(7, delivery["control_audit_log_sample_count"])
        self.assertEqual(126, delivery["control_audit_field_check_count"])
        self.assertEqual(7, delivery["zero_cost_estimate_sample_count"])
        self.assertEqual(7, delivery["failure_handling_result_count"])
        self.assertEqual(7, delivery["non_externalized_data_record_count"])
        self.assertEqual(12, contract["failure_and_stop_contract"]["failure_state_count"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        self.assertEqual(18, len(module.CONTROL_AUDIT_PROJECTION_FIELDS))
        source = contract["source_authority"]
        self.assertFalse(source["second_authoritative_source_created"])
        self.assertFalse(source["source_body_or_path_allowed"])
        self.assertFalse(source["raw_metadata_content_access_allowed"])

    def test_report_reuses_predecessors_and_has_exact_delivery_counts(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report()
        self.assertTrue(report["valid"])
        self.assertEqual(module.PASS_RESULT, report["result"])
        self.assertEqual(module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertTrue(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertEqual(7, report["policy_sample_count"])
        self.assertEqual(7, report["control_audit_log_sample_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(126, report["control_audit_field_check_count"])
        self.assertEqual(7, report["zero_cost_estimate_sample_count"])
        self.assertEqual(7, report["failure_handling_result_count"])
        self.assertEqual(7, report["non_externalized_data_record_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])
        self.assertEqual(1, report["policy_denied_sample_count"])
        self.assertEqual(3, report["three_budget_scope_pause_sample_count"])

    def test_policy_samples_keep_control_only_references(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report()
        samples = report["embedding_cost_governor_policy_samples"]
        self.assertEqual(list(module.EXPECTED_SCENARIO_IDS), [item["scenario_id"] for item in samples])
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(module.POLICY_SAMPLE_KIND, item["sample_kind"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["actual_external_payload_created"])
                self.assertFalse(item["actual_embedding_queue_created"])
                self.assertFalse(item["actual_cache_entry_created"])
                self.assertFalse(item["actual_failed_retry_record_created"])
                self.assertFalse(item["actual_external_api_call_performed"])
                self.assertFalse(item["actual_model_token_consumption_performed"])
                for field in (
                    "cost_governor_request_ref",
                    "policy_resolution_ref",
                    "embedding_queue_request_ref",
                    "cache_entry_ref",
                    "retry_ref",
                    "external_api_audit_ref",
                ):
                    self.assertIn(":control:stage071-p2:", item[field])

    def test_audit_samples_rebuild_exact_eighteen_field_projection(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report()
        samples = report["control_audit_log_samples"]
        self.assertEqual(7, len(samples))
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(module.AUDIT_LOG_SAMPLE_KIND, item["record_kind"])
                self.assertEqual(set(module.CONTROL_AUDIT_PROJECTION_FIELDS), set(item["audit_projection"]))
                self.assertEqual(18, item["audit_field_count"])
                self.assertTrue(item["audit_projection_required"])
                self.assertTrue(item["audit_projection_present"])
                self.assertEqual(0, item["audit_projection"]["token_count"])
                self.assertEqual(0, item["audit_projection"]["cost_estimate"])
                self.assertFalse(item["actual_audit_record_created"])
                self.assertFalse(item["actual_audit_record_persisted"])

    def test_cost_estimates_are_zero_control_metadata_only(self):
        report = self._module().build_embedding_cost_governor_phase4_delivery_report()
        for item in report["cost_estimate_samples"]:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(0, item["estimated_token_count"])
                self.assertEqual(0, item["estimated_cost"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["provider_price_lookup_performed"])
                self.assertFalse(item["actual_cost_recorded"])
                self.assertFalse(item["actual_model_token_consumption_performed"])

    def test_failure_handling_covers_denied_and_all_three_budget_pauses(self):
        report = self._module().build_embedding_cost_governor_phase4_delivery_report()
        results = {item["scenario_id"]: item for item in report["failure_handling_results"]}
        self.assertEqual(7, len(results))
        self.assertEqual(
            "CONTROL_POLICY_DENIED_BLOCKS_EXTERNALIZATION",
            results["denied-policy-blocks-cost-governor-queue-cache-retry-and-externalization-control"]["failure_state"],
        )
        self.assertEqual(
            "CONTROL_CURRENT_BATCH_BUDGET_PAUSE",
            results["current-batch-budget-insufficient-pauses-full-text-control"]["failure_state"],
        )
        self.assertEqual(
            "CONTROL_MONTHLY_BUDGET_PAUSE",
            results["monthly-budget-insufficient-pauses-full-text-control"]["failure_state"],
        )
        self.assertEqual(
            "CONTROL_SINGLE_TASK_CAP_PAUSE",
            results["single-task-cap-exceeded-pauses-full-text-control"]["failure_state"],
        )
        for item in results.values():
            self.assertTrue(item["failure_closed"])
            self.assertFalse(item["actual_failure_record_created"])
            self.assertFalse(item["actual_retry_execution_performed"])

    def test_all_control_references_are_recorded_not_externalized(self):
        report = self._module().build_embedding_cost_governor_phase4_delivery_report()
        records = report["non_externalized_data_records"]
        self.assertEqual(7, len(records))
        self.assertEqual(
            "CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD",
            records[0]["non_externalization_reason"],
        )
        self.assertEqual(3, sum(item["budget_failure_scope"] is not None for item in records))
        for item in records:
            with self.subTest(record=item["scenario_id"]):
                self.assertFalse(item["externalization_performed"])
                self.assertFalse(item["external_payload_created"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["actual_external_api_call_performed"])

    def test_query_rollback_and_chinese_feedback_remain_control_only(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report()
        query = report["externalization_record_query_instructions"]
        rollback = report["policy_rollback_instructions"]
        self.assertTrue(query["query_contract_available"])
        self.assertEqual(7, len(query["supported_query_keys"]))
        self.assertFalse(query["persistent_audit_log_available"])
        self.assertFalse(query["real_externalization_history_available"])
        self.assertFalse(query["actual_audit_log_query_performed"])
        self.assertFalse(query["actual_externalization_record_query_performed"])
        self.assertEqual(module.P3_PASS_RESULT, rollback["rollback_target_result"])
        self.assertEqual(module.ENTRY_GATE, rollback["rollback_target_gate"])
        self.assertFalse(rollback["real_source_change_allowed"])
        self.assertFalse(rollback["persistent_state_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])
        self.assertFalse(rollback["actual_policy_rollback_performed"])
        self.assertEqual(4, len(report["human_confirmation_prompts_zh"]))
        self.assertEqual(4, len(report["chinese_feedback"]))

    def test_report_keeps_runtime_and_production_paths_closed(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report()
        for field in module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["stage071_started"])
        self.assertTrue(report["phase1_started"])
        self.assertTrue(report["phase2_started"])
        self.assertTrue(report["phase3_started"])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["batch_review_performed"])
        self.assertFalse(report["stage072_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_phase3_provider_fails_closed_at_entry_gate(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(module.FAIL_RESULT, report["result"])
        self.assertEqual(module.ENTRY_GATE, report["next_gate"])
        self.assertFalse(report["phase3_controlled_scenarios_report_valid"])
        self.assertFalse(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertEqual([], report["embedding_cost_governor_policy_samples"])

    def test_invalid_phase2_provider_fails_closed_at_entry_gate(self):
        module = self._module()
        report = module.build_embedding_cost_governor_phase4_delivery_report(
            phase2_report_provider=lambda: {"input_accepted": True}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(module.FAIL_RESULT, report["result"])
        self.assertEqual(module.ENTRY_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertFalse(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertEqual(0, report["control_audit_field_check_count"])

    def test_delivery_report_never_claims_a_second_authoritative_source(self):
        report = self._module().build_embedding_cost_governor_phase4_delivery_report()
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertTrue(report["business_line_white_box_human_review_remains_authoritative"])
        self.assertFalse(report["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(report["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(report["real_source_content_retained"])


if __name__ == "__main__":
    unittest.main()
