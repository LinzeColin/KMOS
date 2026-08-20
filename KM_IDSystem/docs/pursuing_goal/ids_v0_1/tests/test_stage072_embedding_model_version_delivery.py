import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_slice_contract.json"
)
PHASE2_SLICE = (
    BASE / "embedding_model_version" / "stage072_embedding_model_version_slice.py"
)
PHASE3_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_scenarios_contract.json"
)
PHASE3_SCENARIOS = (
    BASE / "embedding_model_version" / "stage072_embedding_model_version_scenarios.py"
)
CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_delivery_contract.json"
)
DELIVERY = (
    BASE / "embedding_model_version" / "stage072_embedding_model_version_delivery.py"
)
SCOPE = BASE / "STAGE072_PHASE4_EMBEDDING_MODEL_VERSION_DELIVERY_CLOSEOUT.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-072_Embedding模型版本.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE071_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"


class Stage072EmbeddingModelVersionPhase4Tests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("stage072_p4_delivery", DELIVERY)
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
            "ids.stage072.embedding_model_version.phase4.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE072-P4", contract["task_id"])
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE072-REVIEW-GATE", contract["next_gate"])
        replay = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(5, replay["scenario_count"])
        self.assertEqual(35, replay["scenario_field_count"])
        self.assertEqual(18, replay["external_api_audit_projection_field_count"])
        self.assertEqual(90, replay["audit_field_check_count"])
        self.assertEqual(3, replay["future_external_api_call_candidate_count"])
        self.assertEqual(4, replay["human_handling_required_count"])
        delivery = contract["delivery_evidence_contract"]
        self.assertEqual(5, delivery["policy_sample_count"])
        self.assertEqual(5, delivery["control_audit_log_sample_count"])
        self.assertEqual(18, delivery["control_audit_projection_field_count"])
        self.assertEqual(90, delivery["control_audit_field_check_count"])
        self.assertEqual(5, delivery["zero_cost_estimate_sample_count"])
        self.assertEqual(5, delivery["failure_handling_result_count"])
        self.assertEqual(5, delivery["non_externalized_data_record_count"])
        self.assertEqual(7, delivery["externalization_record_query_key_count"])
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
        report = module.build_embedding_model_version_phase4_delivery_report()
        self.assertTrue(report["valid"])
        self.assertEqual(module.PASS_RESULT, report["result"])
        self.assertEqual(module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertTrue(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertEqual(5, report["policy_sample_count"])
        self.assertEqual(5, report["control_audit_log_sample_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(90, report["control_audit_field_check_count"])
        self.assertEqual(5, report["zero_cost_estimate_sample_count"])
        self.assertEqual(5, report["failure_handling_result_count"])
        self.assertEqual(5, report["non_externalized_data_record_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])
        self.assertEqual(1, report["policy_denied_sample_count"])
        self.assertEqual(1, report["budget_pause_sample_count"])
        self.assertEqual(4, report["human_handling_required_count"])

    def test_policy_samples_keep_control_only_references(self):
        module = self._module()
        report = module.build_embedding_model_version_phase4_delivery_report()
        samples = report["embedding_model_version_policy_samples"]
        self.assertEqual(
            list(module.EXPECTED_SCENARIO_IDS),
            [item["scenario_id"] for item in samples],
        )
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(module.POLICY_SAMPLE_KIND, item["sample_kind"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["sent_to_external_api"])
                self.assertFalse(item["actual_external_payload_created"])
                self.assertFalse(item["actual_embedding_queue_created"])
                self.assertFalse(item["actual_cache_entry_created"])
                self.assertFalse(item["actual_failed_retry_record_created"])
                self.assertFalse(item["actual_external_api_call_performed"])
                self.assertFalse(item["actual_model_token_consumption_performed"])
                for field in (
                    "policy_resolution_ref",
                    "embedding_queue_request_ref",
                    "cache_entry_ref",
                    "retry_ref",
                    "external_api_audit_ref",
                    "provider_ref",
                    "model_ref",
                    "model_version",
                    "dimension",
                    "created_at",
                ):
                    self.assertIn(":control:stage072-p2:", item[field])

    def test_audit_samples_rebuild_exact_eighteen_field_projection(self):
        module = self._module()
        report = module.build_embedding_model_version_phase4_delivery_report()
        samples = report["control_audit_log_samples"]
        self.assertEqual(5, len(samples))
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(module.AUDIT_LOG_SAMPLE_KIND, item["record_kind"])
                self.assertEqual(
                    set(module.CONTROL_AUDIT_PROJECTION_FIELDS),
                    set(item["audit_projection"]),
                )
                self.assertEqual(18, item["audit_field_count"])
                self.assertTrue(item["audit_projection_required"])
                self.assertTrue(item["audit_projection_present"])
                self.assertEqual(0, item["audit_projection"]["token_count"])
                self.assertEqual(0, item["audit_projection"]["cost_estimate"])
                self.assertFalse(item["actual_audit_record_created"])
                self.assertFalse(item["actual_audit_record_persisted"])

    def test_cost_estimates_are_zero_control_metadata_only(self):
        report = self._module().build_embedding_model_version_phase4_delivery_report()
        for item in report["cost_estimate_samples"]:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(0, item["estimated_token_count"])
                self.assertEqual(0, item["estimated_cost"])
                self.assertFalse(item["sent_to_external_api"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["provider_price_lookup_performed"])
                self.assertFalse(item["actual_cost_recorded"])
                self.assertFalse(item["actual_model_token_consumption_performed"])

    def test_failure_handling_covers_denied_budget_and_policy_boundaries(self):
        report = self._module().build_embedding_model_version_phase4_delivery_report()
        results = {item["scenario_id"]: item for item in report["failure_handling_results"]}
        self.assertEqual(5, len(results))
        self.assertEqual(
            "CONTROL_POLICY_DENIED_BLOCKS_EXTERNALIZATION",
            results[
                "denied-policy-blocks-embedding-model-version-egress-control"
            ]["failure_state"],
        )
        self.assertEqual(
            "CONTROL_DOCUMENT_RESTRICTION_BLOCKS_FULL_TEXT_ESCALATION",
            results[
                "document-restriction-keeps-full-text-at-summary-reference-control"
            ]["failure_state"],
        )
        self.assertEqual(
            "CONTROL_BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API",
            results[
                "budget-insufficient-pauses-full-text-external-api-control"
            ]["failure_state"],
        )
        for item in results.values():
            with self.subTest(result=item["scenario_id"]):
                self.assertTrue(item["failure_closed"])
                self.assertFalse(item["actual_failure_record_created"])
                self.assertFalse(item["actual_retry_execution_performed"])

    def test_all_control_references_are_recorded_not_externalized(self):
        report = self._module().build_embedding_model_version_phase4_delivery_report()
        records = report["non_externalized_data_records"]
        self.assertEqual(5, len(records))
        self.assertEqual(
            "CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD",
            records[0]["non_externalization_reason"],
        )
        self.assertEqual(
            1,
            sum(
                item["control_budget_check_state"] == "CONTROL_BUDGET_INSUFFICIENT"
                for item in records
            ),
        )
        for item in records:
            with self.subTest(record=item["scenario_id"]):
                self.assertFalse(item["externalization_performed"])
                self.assertFalse(item["external_payload_created"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["actual_external_api_call_performed"])

    def test_query_rollback_and_chinese_feedback_remain_control_only(self):
        module = self._module()
        report = module.build_embedding_model_version_phase4_delivery_report()
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
        report = module.build_embedding_model_version_phase4_delivery_report()
        for field in module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["stage071_review_evidence_read"])
        self.assertTrue(report["stage072_started"])
        self.assertTrue(report["phase1_started"])
        self.assertTrue(report["phase2_started"])
        self.assertTrue(report["phase3_started"])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["batch_review_performed"])
        self.assertFalse(report["stage073_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_predecessors_fail_closed_at_entry_gate(self):
        module = self._module()
        invalid_phase3 = module.build_embedding_model_version_phase4_delivery_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(invalid_phase3["valid"])
        self.assertEqual(module.FAIL_RESULT, invalid_phase3["result"])
        self.assertEqual(module.ENTRY_GATE, invalid_phase3["next_gate"])
        self.assertEqual([], invalid_phase3["embedding_model_version_policy_samples"])

        invalid_phase2 = module.build_embedding_model_version_phase4_delivery_report(
            phase2_report_provider=lambda: {"input_accepted": True}
        )
        self.assertFalse(invalid_phase2["valid"])
        self.assertEqual(module.FAIL_RESULT, invalid_phase2["result"])
        self.assertEqual(module.ENTRY_GATE, invalid_phase2["next_gate"])
        self.assertEqual([], invalid_phase2["embedding_model_version_policy_samples"])

    def test_delivery_report_never_claims_a_second_authoritative_source(self):
        report = self._module().build_embedding_model_version_phase4_delivery_report()
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertTrue(
            report["business_line_white_box_human_review_remains_authoritative"]
        )
        self.assertFalse(report["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(
            report["delivery_control_metadata_can_become_business_fact_authority"]
        )
        self.assertFalse(report["real_source_content_retained"])


if __name__ == "__main__":
    unittest.main()
