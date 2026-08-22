import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_contract.json"
PHASE2_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_slice_contract.json"
PHASE2_SLICE = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_slice.py"
PHASE3_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_scenarios_contract.json"
PHASE3_SCENARIOS = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_scenarios.py"
CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_delivery_contract.json"
DELIVERY = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_delivery.py"
SCOPE = BASE / "STAGE073_PHASE4_EMBEDDING_AUDIT_TEST_DELIVERY_CLOSEOUT.md"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-073_Embedding审计测试.md"
PREDECESSOR_REVIEW = BASE / "STAGE072_STAGE_REVIEW.md"
PREDECESSOR_MODEL_CONTRACT = BASE / "embedding_model_version" / "stage072_embedding_model_version_contract.json"
PREDECESSOR_AUDIT_CONTRACT = BASE / "embedding_cost_governor" / "stage071_embedding_cost_governor_contract.json"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage073-p4-local.json"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage073EmbeddingAuditTestPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module("stage073_p4_delivery", DELIVERY)

    def _report(self):
        return self.module.build_embedding_audit_test_phase4_delivery_report()

    def test_phase4_artifacts_and_predecessors_exist(self):
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
            PREDECESSOR_MODEL_CONTRACT,
            PREDECESSOR_AUDIT_CONTRACT,
            BATCH,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_has_exact_p4_scope_and_runtime_remains_closed(self):
        contract = self.contract
        self.assertEqual("ids.stage073.embedding_audit_test.phase4.delivery.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE073-P4", contract["task_id"])
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE073-REVIEW-GATE", contract["next_gate"])
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
        source = contract["source_authority"]
        self.assertFalse(source["second_authoritative_source_created"])
        self.assertFalse(source["source_body_or_path_allowed"])
        self.assertFalse(source["raw_metadata_content_access_allowed"])

    def test_report_reuses_predecessors_and_has_exact_delivery_counts(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_reused_as_reference_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertTrue(report["phase2_control_slice_reexecuted_in_memory_only"])
        self.assertTrue(report["phase2_control_slice_report_valid"])
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
        samples = self._report()["embedding_audit_test_policy_samples"]
        self.assertEqual(list(self.module.EXPECTED_SCENARIO_IDS), [item["scenario_id"] for item in samples])
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(self.module.POLICY_SAMPLE_KIND, item["sample_kind"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["sent_to_external_api"])
                self.assertFalse(item["actual_external_payload_created"])
                self.assertFalse(item["actual_embedding_queue_created"])
                self.assertFalse(item["actual_cache_entry_created"])
                self.assertFalse(item["actual_failed_retry_record_created"])
                self.assertFalse(item["actual_external_api_call_performed"])
                self.assertFalse(item["actual_model_token_consumption_performed"])
                for field in ("policy_resolution_ref", "embedding_queue_request_ref", "cache_entry_ref", "retry_ref", "external_api_audit_ref"):
                    self.assertIn(":control:stage073-p2:", item[field])

    def test_audit_samples_rebuild_exact_eighteen_field_projection(self):
        samples = self._report()["control_audit_log_samples"]
        self.assertEqual(5, len(samples))
        for item in samples:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(self.module.AUDIT_LOG_SAMPLE_KIND, item["record_kind"])
                self.assertEqual(set(self.module.CONTROL_AUDIT_PROJECTION_FIELDS), set(item["audit_projection"]))
                self.assertEqual(18, item["audit_field_count"])
                self.assertTrue(item["audit_projection_required"])
                self.assertTrue(item["audit_projection_present"])
                self.assertTrue(item["audit_reference_fields_are_control_only"])
                self.assertEqual(0, item["audit_projection"]["token_count"])
                self.assertEqual(0, item["audit_projection"]["cost_estimate"])
                self.assertFalse(item["actual_audit_record_created"])
                self.assertFalse(item["actual_audit_record_persisted"])

    def test_cost_estimates_are_zero_control_metadata_only(self):
        for item in self._report()["cost_estimate_samples"]:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(0, item["estimated_token_count"])
                self.assertEqual(0, item["estimated_cost"])
                self.assertFalse(item["sent_to_external_api"])
                self.assertTrue(item["control_metadata_only"])
                self.assertFalse(item["provider_price_lookup_performed"])
                self.assertFalse(item["actual_cost_recorded"])
                self.assertFalse(item["actual_model_token_consumption_performed"])

    def test_failure_handling_covers_denied_budget_and_policy_boundaries(self):
        results = {item["scenario_id"]: item for item in self._report()["failure_handling_results"]}
        self.assertEqual(5, len(results))
        self.assertEqual("CONTROL_POLICY_DENIED_BLOCKS_EXTERNALIZATION", results["denied-policy-blocks-embedding-audit-test-egress-control"]["failure_state"])
        self.assertEqual("CONTROL_DOCUMENT_RESTRICTION_BLOCKS_FULL_TEXT_ESCALATION", results["document-restriction-keeps-full-text-at-summary-reference-control"]["failure_state"])
        self.assertEqual("CONTROL_BUDGET_INSUFFICIENT_PAUSES_EXTERNAL_API", results["budget-insufficient-pauses-full-text-external-api-control"]["failure_state"])
        for item in results.values():
            with self.subTest(result=item["scenario_id"]):
                self.assertTrue(item["failure_closed"])
                self.assertFalse(item["actual_failure_record_created"])
                self.assertFalse(item["actual_retry_execution_performed"])
                self.assertFalse(item["actual_external_api_call_performed"])

    def test_all_control_references_are_recorded_not_externalized(self):
        records = self._report()["non_externalized_data_records"]
        self.assertEqual(5, len(records))
        self.assertEqual("CONTROL_POLICY_DENIED_NO_EXTERNAL_PAYLOAD", records[0]["non_externalization_reason"])
        self.assertEqual(1, sum(item["control_budget_check_state"] == "CONTROL_BUDGET_INSUFFICIENT" for item in records))
        for item in records:
            with self.subTest(record=item["scenario_id"]):
                self.assertFalse(item["externalization_performed"])
                self.assertFalse(item["external_payload_created"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["actual_external_api_call_performed"])

    def test_query_rollback_and_chinese_feedback_remain_control_only(self):
        report = self._report()
        query = report["externalization_record_query_instructions"]
        rollback = report["policy_rollback_instructions"]
        self.assertTrue(query["query_contract_available"])
        self.assertEqual(7, len(query["supported_query_keys"]))
        self.assertFalse(query["persistent_audit_log_available"])
        self.assertFalse(query["real_externalization_history_available"])
        self.assertFalse(query["actual_audit_log_query_performed"])
        self.assertFalse(query["actual_externalization_record_query_performed"])
        self.assertEqual(self.module.P3_PASS_RESULT, rollback["rollback_target_result"])
        self.assertEqual(self.module.ENTRY_GATE, rollback["rollback_target_gate"])
        self.assertFalse(rollback["real_source_change_allowed"])
        self.assertFalse(rollback["persistent_state_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])
        self.assertFalse(rollback["actual_policy_rollback_performed"])
        self.assertEqual(4, len(report["human_confirmation_prompts_zh"]))
        self.assertEqual(4, len(report["chinese_feedback"]))

    def test_invalid_phase3_report_fails_closed(self):
        report = self.module.build_embedding_audit_test_phase4_delivery_report(phase3_report_provider=lambda: {"valid": False})
        self.assertFalse(report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])
        self.assertEqual(self.module.ENTRY_GATE, report["next_gate"])
        self.assertFalse(report["phase3_controlled_scenarios_report_valid"])
        self.assertEqual(0, report["policy_sample_count"])

    def test_malformed_phase2_report_fails_closed(self):
        phase2 = _load_module("stage073_p2_slice", PHASE2_SLICE)
        malformed = copy.deepcopy(phase2.execute_embedding_audit_test_control_slice(phase2.build_control_input()))
        malformed["external_api_audit_projections"][0].pop("provider_ref")
        report = self.module.build_embedding_audit_test_phase4_delivery_report(phase2_report_provider=lambda: malformed)
        self.assertFalse(report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])
        self.assertFalse(report["phase2_control_slice_report_valid"])
        self.assertEqual(0, report["control_audit_log_sample_count"])

    def test_report_keeps_runtime_and_production_paths_closed(self):
        report = self._report()
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        for field in ("actual_embedding_queue_count", "actual_cache_entry_count", "actual_failed_retry_count", "actual_cost_count", "actual_model_version_record_count", "actual_external_api_audit_record_count", "actual_external_api_call_count", "actual_model_token_count"):
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_current_machine_and_governance_projection_match_p4(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        event_ids = {item["event_id"] for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip() for item in [json.loads(line)]}
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-STAGE073-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-STAGE074-P1-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-STAGE074-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-STAGE074-P3-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-STAGE074-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-STAGE074-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-STAGE075-P1-GATE",
                ),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                (
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-STAGE076-REVIEW-GATE',
                ),
                (
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-STAGE077-P1-GATE',
                ),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE")),
        )
        self.assertTrue(
            "IDS-V0_1-STAGE073-P4" in plan["now"]
            or "IDS-V0_1-STAGE073-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE074-P1" in plan["now"]
            or "IDS-V0_1-STAGE074-P2" in plan["now"] or "IDS-V0_1-STAGE074-P3" in plan["now"]
            or "IDS-V0_1-STAGE074-P4" in plan["now"]
            or "IDS-V0_1-STAGE074-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE075-P1" in plan["now"]
            or "IDS-V0_1-STAGE075-P2" in plan["now"]
            or "IDS-V0_1-STAGE075-P3" in plan["now"]
            or "IDS-V0_1-STAGE075-P4" in plan["now"]
            or "IDS-V0_1-STAGE075-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE076-P1" in plan["now"]
            or "IDS-V0_1-STAGE076-P2" in plan["now"]
            or "IDS-V0_1-STAGE076-P3" in plan["now"]
            or "IDS-V0_1-STAGE076-P4" in plan["now"]
            or "IDS-V0_1-STAGE076-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE077-P1" in plan["now"]
            or "IDS-V0_1-STAGE077-P2" in plan["now"]
            or "IDS-V0_1-STAGE077-P3" in plan["now"]
            or "IDS-V0_1-STAGE077-P4" in plan["now"]
            or "IDS-V0_1-STAGE077-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE078-P1" in plan["now"]
            or "IDS-V0_1-STAGE078-P2" in plan["now"]
            or "IDS-V0_1-STAGE078-P3" in plan["now"]
            or "IDS-V0_1-STAGE078-P4" in plan["now"]
            or "IDS-V0_1-STAGE078-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE079-P1" in plan["now"]
            or "IDS-V0_1-STAGE079-P2" in plan["now"]
            or "IDS-V0_1-STAGE079-P3" in plan["now"]
            or "IDS-V0_1-STAGE079-P4" in plan["now"]
            or "IDS-V0_1-STAGE079-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE080-P1" in plan["now"]
            or "IDS-V0_1-STAGE080-P2" in plan["now"]
            or "IDS-V0_1-STAGE080-P3" in plan["now"]
            or "IDS-V0_1-STAGE080-P4" in plan["now"]
            or "IDS-V0_1-STAGE080-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE081-P1" in plan["now"]
            or "IDS-V0_1-STAGE081-P2" in plan["now"]
            or "IDS-V0_1-STAGE081-P3" in plan["now"]
            or "IDS-V0_1-STAGE081-P4" in plan["now"]
            or "IDS-V0_1-STAGE081-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE082-P1" in plan["now"]
            or "IDS-V0_1-STAGE082-P2" in plan["now"]
            or "IDS-V0_1-STAGE082-P3" in plan["now"]
            or "IDS-V0_1-STAGE082-P4" in plan["now"]
            or "IDS-V0_1-STAGE082-REVIEW" in plan["now"]
            or "IDS-V0_1-STAGE083-P1" in plan["now"]
            or "IDS-V0_1-STAGE083-P2" in plan["now"]
            or "IDS-V0_1-STAGE083-P3" in plan["now"]
            or "IDS-V0_1-STAGE083-P4" in plan["now"]
        )
        self.assertTrue(
            "IDS-V0_1-STAGE073-P4" in "\n".join(plan["scope"])
            or "P1--P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE075-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE075-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE075-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE075-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE076-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE076-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE076-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE076-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE077-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE077-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE077-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE077-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE078-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE078-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE078-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE078-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE078-REVIEW" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE079-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE079-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE079-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE079-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE079-REVIEW" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE080-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE080-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE080-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE080-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE081-P1" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE081-P2" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE081-P3" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE081-P4" in "\n".join(plan["scope"])
            or "IDS-V0_1-STAGE081-REVIEW" in "\n".join(plan["scope"])
        )
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue({"ACC-STAGE-073", "ACC-STAGE073-P4-01", "ACC-STAGE073-P4-02", "ACC-STAGE073-P4-03", "ACC-STAGE073-P4-04"}.issubset(acceptance_ids))
        self.assertTrue(
            'current_phase_id: "IDS-STAGE073-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE076-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE076-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE076-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE077-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE077-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE078-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE078-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE078-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE078-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE079-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE079-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE079-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE079-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE080-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE080-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE080-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE081-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE081-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE081-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE081-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE081-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE073-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P2"' in roadmap_text or 'current_task_id: "IDS-V0_1-STAGE074-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE076-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE076-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE076-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE078-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE078-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE078-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE078-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE079-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE079-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE079-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE079-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE080-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE080-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE080-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE080-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE081-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE081-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE081-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE081-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE081-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE073-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-P3-GATE"' in roadmap_text or 'next_gate_id: "IDS-STAGE074-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE076-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE076-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE076-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE077-P3-GATE"' in roadmap_text or 'next_gate_id: "IDS-STAGE077-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE079-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE079-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE079-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE081-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE081-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE081-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE081-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE082-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE082-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE082-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE082-REVIEW-GATE"' in roadmap_text
        )
        self.assertIn("EVT-IDS-V0_1-STAGE073-P4-20260820-001", event_ids)
        self.assertTrue(RUN.is_file())


if __name__ == "__main__":
    unittest.main()
