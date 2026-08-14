import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_contract.json"
PHASE2_CONTRACT = (
    BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_scenarios.py"
)
CLOSEOUT = BASE / "STAGE070_PHASE4_EMBEDDING_QUEUE_CACHE_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_delivery_contract.json"
)
MODULE = BASE / "embedding_queue_cache" / "stage070_embedding_queue_cache_delivery.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage070-p4-local.json"

EXPECTED_SCENARIOS = [
    "denied-policy-blocks-queue-cache-retry-and-externalization-control",
    "summary-only-policy-limits-control-payload",
    "document-restriction-limits-full-text-to-summary-control",
    "full-text-policy-allows-only-control-text-reference",
    "budget-insufficient-pauses-full-text-control",
]


class Stage070EmbeddingQueueCachePhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage070_p4", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_embedding_queue_cache_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            CLOSEOUT,
            CONTRACT,
            MODULE,
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

    def test_contract_identity_delivery_boundary_and_authority(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage070.embedding_queue_cache.phase4.delivery_contract.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE070-P4", contract["task_id"])
        self.assertEqual("IDS-STAGE070-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE070-REVIEW-GATE", contract["next_gate"])
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertTrue(
            contract["predecessor_boundary"]
            ["phase3_controlled_scenarios_reused_as_reference_only"]
        )
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        for field in (
            "second_authoritative_source_created",
            "delivery_control_metadata_can_replace_source_document",
            "delivery_control_metadata_can_become_business_fact_authority",
            "real_source_content_retained",
            "source_body_or_path_allowed",
            "summary_body_allowed",
            "chunk_text_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_contract_covers_delivery_query_rollback_and_failure_items(self):
        contract = self._contract()
        artifacts = contract["delivery_artifacts"]
        self.assertEqual(5, artifacts["embedding_queue_cache_policy_samples"]["sample_count"])
        self.assertEqual(5, artifacts["audit_log_samples"]["sample_count"])
        self.assertEqual(18, artifacts["audit_log_samples"]["audit_field_count"])
        self.assertEqual(90, artifacts["audit_log_samples"]["audit_field_check_count"])
        self.assertTrue(
            artifacts["audit_log_samples"]
            ["exact_phase2_audit_projection_shape_in_each_sample"]
        )
        self.assertEqual(5, artifacts["cost_estimate_samples"]["sample_count"])
        self.assertTrue(artifacts["cost_estimate_samples"]["all_control_token_counts_zero"])
        self.assertTrue(artifacts["cost_estimate_samples"]["all_control_cost_estimates_zero"])
        self.assertEqual(5, artifacts["failure_handling_results"]["result_count"])
        self.assertEqual(0, artifacts["failure_handling_results"]["silent_drop_count"])
        self.assertEqual(5, artifacts["non_externalized_data_records"]["record_count"])
        self.assertFalse(
            artifacts["externalization_record_query_instructions"]
            ["persistent_audit_log_available"]
        )
        self.assertEqual(12, contract["failure_and_stop_contract"]["failure_state_count"])
        self.assertEqual(
            "PASS_PHASE3_EMBEDDING_QUEUE_CACHE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["rollback_contract"]["rollback_target_result"],
        )

    def test_delivery_report_is_valid_and_metadata_only(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_EMBEDDING_QUEUE_CACHE_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE070-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertEqual(5, len(report["embedding_queue_cache_policy_samples"]))
        self.assertEqual(5, len(report["embedding_queue_cache_policy_sample_lines"]))
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])

    def test_policy_samples_preserve_control_references_without_payload(self):
        report = self._report()
        samples = report["embedding_queue_cache_policy_samples"]
        self.assertEqual(EXPECTED_SCENARIOS, [item["scenario_id"] for item in samples])
        for sample, line in zip(samples, report["embedding_queue_cache_policy_sample_lines"]):
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(sample, json.loads(line))
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_EMBEDDING_QUEUE_CACHE_POLICY_SAMPLE_NOT_REAL_PAYLOAD",
                    sample["sample_kind"],
                )
                self.assertTrue(sample["control_metadata_only"])
                self.assertFalse(sample["source_content_retained"])
                for field in (
                    "actual_external_payload_created",
                    "actual_embedding_queue_created",
                    "actual_cache_entry_created",
                    "actual_failed_retry_record_created",
                    "actual_external_api_call_performed",
                    "actual_model_token_consumption_performed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(sample[field])
                for field in (
                    "policy_resolution_ref",
                    "embedding_queue_request_ref",
                    "cache_entry_ref",
                    "retry_ref",
                    "external_api_audit_ref",
                ):
                    with self.subTest(field=field):
                        self.assertIn(":control:stage070-p2:", sample[field])

    def test_audit_log_samples_are_unpersisted_control_projections(self):
        module = self._module()
        samples = self._report()["control_audit_log_samples"]
        self.assertEqual(5, len(samples))
        self.assertEqual(EXPECTED_SCENARIOS, [item["scenario_id"] for item in samples])
        for sample in samples:
            with self.subTest(sample=sample["audit_log_sample_id"]):
                self.assertEqual(
                    "CONTROL_EMBEDDING_QUEUE_CACHE_AUDIT_LOG_SAMPLE_NOT_PERSISTED",
                    sample["record_kind"],
                )
                self.assertEqual(18, sample["audit_field_count"])
                projection = sample["audit_projection"]
                self.assertEqual(
                    set(module.CONTROL_AUDIT_PROJECTION_FIELDS), set(projection)
                )
                self.assertEqual(
                    sample["external_api_audit_ref"], projection["external_api_audit_ref"]
                )
                self.assertEqual(
                    sample["embedding_queue_request_ref"],
                    projection["embedding_queue_request_ref"],
                )
                self.assertEqual(0, projection["token_count"])
                self.assertEqual(0, projection["cost_estimate"])
                for field in (
                    "external_api_audit_ref",
                    "data_source_ref",
                    "document_ref",
                    "chunk_ref",
                    "owner_authorization_ref",
                    "authorized_at",
                    "authorization_reason",
                    "provider_ref",
                    "model_ref",
                    "model_version",
                    "embedding_queue_request_ref",
                ):
                    with self.subTest(field=field):
                        self.assertIn(":control:stage070-p2:", projection[field])
                self.assertTrue(sample["audit_projection_required"])
                self.assertTrue(sample["audit_projection_present"])
                self.assertTrue(sample["control_metadata_only"])
                self.assertFalse(sample["actual_audit_record_created"])
                self.assertFalse(sample["actual_audit_record_persisted"])

    def test_cost_estimates_stay_zero_without_provider_or_model(self):
        samples = self._report()["cost_estimate_samples"]
        self.assertEqual(5, len(samples))
        for sample in samples:
            with self.subTest(sample=sample["cost_estimate_id"]):
                self.assertEqual(
                    "CONTROL_ZERO_COST_ESTIMATE_NOT_PROVIDER_PRICE",
                    sample["record_kind"],
                )
                self.assertEqual(0, sample["token_count"])
                self.assertEqual(0, sample["cost_estimate"])
                self.assertFalse(sample["provider_selected"])
                self.assertFalse(sample["model_selected"])
                self.assertFalse(sample["actual_cost_recorded"])

    def test_failure_handling_and_non_externalization_are_explicit(self):
        report = self._report()
        handling = report["failure_handling_results"]
        unsent = report["non_externalized_data_records"]
        self.assertEqual(5, len(handling))
        self.assertEqual(5, len(unsent))
        self.assertEqual(
            "POLICY_DENIED_QUEUE_CACHE_RETRY_BLOCKED_NO_EXTERNAL_PAYLOAD",
            handling[0]["failure_state"],
        )
        self.assertEqual(
            "BUDGET_INSUFFICIENT_QUEUE_CACHE_RETRY_PAUSED_NO_EXTERNALIZATION",
            handling[-1]["failure_state"],
        )
        self.assertEqual(0, sum(item["silent_drop"] for item in handling))
        for item in handling:
            with self.subTest(item=item["failure_handling_id"]):
                self.assertTrue(item["queue_cache_retry_stopped_or_paused"])
                self.assertTrue(item["externalization_stopped"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["actual_failure_record_created"])
        for item in unsent:
            with self.subTest(item=item["record_id"]):
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["externalization_performed"])
                self.assertFalse(item["actual_non_externalized_data_record_persisted"])
                self.assertTrue(item["non_externalization_reason"])

    def test_query_and_rollback_instructions_remain_control_only(self):
        report = self._report()
        query = report["externalization_record_query_instructions"]
        rollback = report["policy_rollback_instructions"]
        self.assertTrue(query["query_contract_available"])
        self.assertEqual(
            [
                "scenario_id",
                "external_api_audit_ref",
                "policy_resolution_ref",
                "embedding_queue_request_ref",
                "cache_entry_ref",
                "retry_ref",
            ],
            query["query_keys"],
        )
        self.assertFalse(query["persistent_audit_log_available"])
        self.assertFalse(query["persistent_queue_or_cache_record_available"])
        self.assertFalse(query["actual_audit_log_query_performed"])
        self.assertFalse(query["actual_externalization_record_query_performed"])
        self.assertFalse(query["can_return_real_externalization_history"])
        self.assertEqual(
            "PASS_PHASE3_EMBEDDING_QUEUE_CACHE_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_result"],
        )
        self.assertTrue(rollback["in_memory_control_replay_only"])
        self.assertTrue(rollback["phase1_phase2_phase3_artifacts_preserved"])
        for field in (
            "actual_policy_rollback_performed",
            "source_or_raw_data_change_allowed",
            "fixture_change_allowed",
            "audit_log_change_allowed",
            "queue_or_cache_change_allowed",
            "database_schema_change_allowed",
            "persistent_runtime_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

    def test_chinese_feedback_and_runtime_boundary_are_explicit(self):
        report = self._report()
        self.assertEqual(3, len(report["human_confirmation_prompts_zh"]))
        self.assertTrue(
            all("确认" in item for item in report["human_confirmation_prompts_zh"])
        )
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in item)
                for item in report["chinese_feedback"]
            )
        )
        for field in self._module().RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage071_started"])
        self.assertFalse(report["github_upload_allowed"])

    def test_invalid_predecessor_fails_closed_without_delivery_samples(self):
        report = self._module().build_embedding_queue_cache_phase4_delivery_report(
            lambda: {"valid": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_EMBEDDING_QUEUE_CACHE_DELIVERY_EVIDENCE", report["result"]
        )
        self.assertEqual("IDS-STAGE070-P4-GATE", report["next_gate"])
        self.assertFalse(report["phase3_controlled_scenarios_report_valid"])
        self.assertEqual([], report["embedding_queue_cache_policy_samples"])
        self.assertEqual((), report["embedding_queue_cache_policy_sample_lines"])
        self.assertEqual([], report["control_audit_log_samples"])
        self.assertEqual([], report["non_externalized_data_records"])
        self.assertFalse(
            report["externalization_record_query_instructions"]
            ["query_contract_available"]
        )

    def test_governance_projection_records_phase4_local_only(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual("IDS-STAGE070", status["stage"])
        self.assertEqual(
            (
                "IDS-V0_1-STAGE070-P4",
                "IDS-V0_1-STAGE070-P4",
                "IDS-STAGE070-REVIEW-GATE",
            ),
            (status["phase"], status["task"], status["next_gate"]),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertEqual("IDS-STAGE070", plan["stage"])
        self.assertEqual(
            ("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4"),
            (plan["phase"], plan["task"]),
        )
        self.assertIn("IDS-STAGE070-REVIEW-GATE", plan["stop_condition"])
        for acceptance_id in (
            "ACC-STAGE070-P4-01",
            "ACC-STAGE070-P4-02",
            "ACC-STAGE070-P4-03",
            "ACC-STAGE070-P4-04",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertTrue(
                    any(item["id"] == acceptance_id for item in acceptance["items"])
                )
        self.assertEqual("IDS-V0_1-STAGE070-P4", run["task_id"])
        self.assertEqual("IDS-STAGE070-REVIEW-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["external_api_call_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage070_phase4", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE070-P4", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE070-P4-20260815-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
