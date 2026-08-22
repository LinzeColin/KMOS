import copy
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
CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_scenarios_contract.json"
)
SCENARIOS = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_scenarios.py"
)
SCOPE = BASE / "STAGE071_PHASE3_EMBEDDING_COST_GOVERNOR_CONTROLLED_SCENARIOS.md"
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
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage071-p3-local.json"


class Stage071EmbeddingCostGovernorPhase3Tests(unittest.TestCase):
    def _module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _scenarios(self):
        return self._module("stage071_embedding_cost_governor_scenarios", SCENARIOS)

    def _phase2(self):
        return self._module("stage071_embedding_cost_governor_phase2", PHASE2_SLICE)

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            CONTRACT,
            SCENARIOS,
            SCOPE,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
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

    def test_contract_has_exact_p3_scope_and_runtime_remains_closed(self):
        contract = self._contract()
        module = self._scenarios()
        self.assertEqual(
            "ids.stage071.embedding_cost_governor.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE071-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE071-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE071_TASKPACK_PHASE1_PHASE2_STAGE070_REVIEW_AND_BATCH_LOCK_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

        replay = contract["phase2_control_slice_replay_contract"]
        self.assertEqual(7, replay["control_request_count"])
        self.assertEqual(7, replay["cost_governor_record_count"])
        self.assertEqual(18, replay["cost_governor_record_field_count"])
        self.assertEqual(14, replay["embedding_queue_record_field_count"])
        self.assertEqual(18, replay["external_api_audit_projection_field_count"])
        scenarios = contract["controlled_scenario_contract"]
        self.assertEqual(list(module.SCENARIO_RESULT_FIELDS), scenarios["required_fields"])
        self.assertEqual(35, scenarios["field_count"])
        self.assertEqual(7, scenarios["scenario_count"])
        self.assertEqual(list(module.REQUIRED_SCENARIO_CATEGORIES), scenarios["scenario_order"])
        audit = contract["audit_projection_invariant_contract"]
        self.assertEqual(7, audit["control_audit_projection_count"])
        self.assertEqual(126, audit["control_audit_field_check_count"])
        self.assertEqual(3, audit["future_external_api_call_candidate_count"])
        self.assertEqual(12, contract["failure_and_stop_contract"]["failure_state_count"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_report_replays_exact_p2_shape_and_all_seven_scenarios(self):
        module = self._scenarios()
        report = module.build_embedding_cost_governor_phase3_report()
        self.assertTrue(report["valid"])
        self.assertEqual(module.PASS_RESULT, report["result"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(7, report["scenario_count"])
        self.assertEqual(7, report["passed_scenario_count"])
        self.assertEqual(7, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(6, report["human_handling_required_count"])
        self.assertTrue(report["all_taskpack_special_scenarios_covered"])
        self.assertTrue(report["cost_queue_cache_retry_boundaries_preserved"])
        self.assertTrue(report["budget_scope_failure_coverage_preserved"])
        self.assertEqual(7, report["control_policy_resolution_record_count"])
        self.assertEqual(7, report["control_cost_governor_record_count"])
        self.assertEqual(7, report["control_embedding_queue_record_count"])
        self.assertEqual(7, report["control_cache_record_count"])
        self.assertEqual(7, report["control_failed_retry_record_count"])
        self.assertEqual(7, report["control_external_api_audit_projection_count"])

    def test_scenario_records_keep_exact_shape_and_control_only_references(self):
        module = self._scenarios()
        report = module.build_embedding_cost_governor_phase3_report()
        self.assertEqual(
            list(module.REQUIRED_SCENARIO_CATEGORIES),
            [record["scenario_category"] for record in report["scenario_results"]],
        )
        for record in report["scenario_results"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertEqual(set(module.SCENARIO_RESULT_FIELDS), set(record))
                self.assertTrue(record["expectation_met"])
                self.assertFalse(record["silent_drop"])
                self.assertFalse(record["actual_external_api_call_performed"])
                self.assertFalse(record["actual_model_token_consumption_performed"])
                for field in (
                    "referenced_cost_governor_request_ref",
                    "referenced_policy_resolution_ref",
                    "referenced_embedding_queue_request_ref",
                    "referenced_cache_entry_ref",
                    "referenced_retry_ref",
                    "referenced_external_api_audit_ref",
                ):
                    self.assertIn(":control:", record[field])

    def test_denied_summary_only_and_full_text_boundaries_are_distinct(self):
        report = self._scenarios().build_embedding_cost_governor_phase3_report()
        records = {item["scenario_category"]: item for item in report["scenario_results"]}
        denied = records["DENIED_NO_EXTERNALIZATION_CONTROL"]
        self.assertEqual("denied", denied["effective_external_api_policy"])
        self.assertEqual("NO_CONTROL_PAYLOAD_REFERENCE", denied["observed_control_payload_scope"])
        self.assertEqual("CONTROL_QUEUE_BLOCKED_POLICY_DENIED", denied["observed_queue_state"])
        self.assertEqual("BLOCKED_POLICY_DENIED", denied["observed_audit_disposition"])
        self.assertFalse(denied["future_external_api_call_candidate"])

        summary = records["SUMMARY_ONLY_PAYLOAD_BOUNDARY_CONTROL"]
        restricted = records["DOCUMENT_RESTRICTION_PAYLOAD_BOUNDARY_CONTROL"]
        self.assertEqual("summary_only", summary["effective_external_api_policy"])
        self.assertEqual("summary_only", restricted["effective_external_api_policy"])
        self.assertEqual("CONTROL_SUMMARY_REFERENCE_ONLY", summary["observed_control_payload_scope"])
        self.assertEqual("CONTROL_SUMMARY_REFERENCE_ONLY", restricted["observed_control_payload_scope"])
        self.assertTrue(summary["future_external_api_call_candidate"])
        self.assertTrue(restricted["future_external_api_call_candidate"])

        full_text = records["FULL_TEXT_PAYLOAD_BOUNDARY_CONTROL"]
        self.assertEqual("full_text_allowed", full_text["effective_external_api_policy"])
        self.assertEqual("CONTROL_CHUNK_TEXT_REFERENCE_ONLY", full_text["observed_control_payload_scope"])
        self.assertTrue(full_text["future_external_api_call_candidate"])

    def test_each_budget_scope_pauses_cost_governor_queue_cache_and_retry(self):
        report = self._scenarios().build_embedding_cost_governor_phase3_report()
        records = {item["scenario_category"]: item for item in report["scenario_results"]}
        for category, expected_scope in (
            ("CURRENT_BATCH_BUDGET_PAUSE_CONTROL", "current_batch"),
            ("MONTHLY_BUDGET_PAUSE_CONTROL", "calendar_month"),
            ("SINGLE_TASK_CAP_PAUSE_CONTROL", "single_task"),
        ):
            with self.subTest(category=category):
                record = records[category]
                self.assertEqual(expected_scope, record["observed_budget_failure_scope"])
                self.assertEqual(
                    "CONTROL_COST_GOVERNOR_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    record["observed_cost_governor_state"],
                )
                self.assertEqual(
                    "CONTROL_QUEUE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    record["observed_queue_state"],
                )
                self.assertEqual(
                    "CONTROL_CACHE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    record["observed_cache_disposition"],
                )
                self.assertEqual(
                    "CONTROL_RETRY_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    record["observed_retry_state"],
                )
                self.assertEqual(
                    "PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    record["observed_audit_disposition"],
                )
                self.assertFalse(record["future_external_api_call_candidate"])
        self.assertEqual(3, report["three_budget_scope_paused_count"])

    def test_all_scenarios_have_complete_audit_projection_and_future_candidates_are_pre_audited(self):
        report = self._scenarios().build_embedding_cost_governor_phase3_report()
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        self.assertEqual(7, report["audit_projection_required_count"])
        self.assertEqual(7, report["audit_projection_present_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(126, report["control_audit_field_check_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])
        for record in report["scenario_results"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["audit_projection_required"])
                self.assertTrue(record["audit_projection_present"])
                self.assertEqual(18, record["audit_field_count"])

    def test_invalid_phase2_shape_fails_closed(self):
        module = self._scenarios()
        report = module.build_embedding_cost_governor_phase3_report(
            phase2_executor=lambda _control: {"input_accepted": False}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(module.FAIL_RESULT, report["result"])
        self.assertFalse(report["phase2_shape_preserved"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(0, report["passed_scenario_count"])

    def test_missing_audit_projection_fails_closed(self):
        module = self._scenarios()
        phase2 = self._phase2()

        def malformed(_control):
            result = copy.deepcopy(
                phase2.execute_embedding_cost_governor_control_slice(
                    phase2.build_control_input()
                )
            )
            result["external_api_audit_projections"][3].pop("model_ref")
            return result

        report = module.build_embedding_cost_governor_phase3_report(malformed)
        self.assertFalse(report["valid"])
        self.assertEqual(module.FAIL_RESULT, report["result"])
        self.assertFalse(report["phase2_shape_preserved"])
        self.assertEqual(6, report["passed_scenario_count"])

    def test_runtime_and_business_decisions_remain_closed(self):
        module = self._scenarios()
        report = module.build_embedding_cost_governor_phase3_report()
        self.assertFalse(report["control_payload_content_retained"])
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_embedding_queue_count"])
        self.assertEqual(0, report["actual_cache_entry_count"])
        self.assertEqual(0, report["actual_failed_retry_count"])
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])
        self.assertEqual(0, report["actual_external_api_audit_record_count"])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(report["embedding_cost_governor_scenario_can_replace_source_document"])
        self.assertFalse(report["embedding_cost_governor_scenario_can_become_business_fact_authority"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        for field in module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["batch_review_performed"])
        self.assertFalse(report["stage072_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_chinese_feedback_and_p3_governance_evidence_survives_stage_review(self):
        report = self._scenarios().build_embedding_cost_governor_phase3_report()
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(
            all(
                any("一" <= char <= "鿿" for char in message)
                for message in report["chinese_feedback"]
            )
        )
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(
            (status["stage"], status["phase"], status["next_gate"]),
            (
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P4', 'IDS-STAGE076-REVIEW-GATE'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-STAGE077-P1-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'),
             ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"),
                ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P2', 'IDS-STAGE084-P3-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-STAGE085-P3-GATE'),

                ('IDS-STAGE085', 'IDS-STAGE085-P2', 'IDS-STAGE085-P3-GATE'),
             ("IDS-STAGE085", "IDS-STAGE085-P3", "IDS-STAGE085-P4-GATE"),
             ("IDS-STAGE085", "IDS-STAGE085-P4", "IDS-STAGE085-REVIEW-GATE"), ("IDS-STAGE085", "IDS-STAGE085-REVIEW", "IDS-STAGE086-P1-GATE")),
        )
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                        "IDS-V0_1-STAGE079-P1",
                                        "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                            'IDS-V0_1-STAGE079-REVIEW',

                                        'IDS-V0_1-STAGE080-P1',
                                        'IDS-V0_1-STAGE080-P2',
                                        'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                                        'IDS-V0_1-STAGE082-P2',
                                        'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                                            'IDS-V0_1-STAGE084-REVIEW',

                                        'IDS-V0_1-STAGE085-P2',
                                     "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW"))
        self.assertTrue(
            (
"IDS-STAGE073-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"] or "IDS-STAGE075-P4-GATE" in plan["stop_condition"] or "IDS-STAGE075-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE076-P1-GATE" in plan["stop_condition"] or "IDS-STAGE076-P2-GATE" in plan["stop_condition"] or "IDS-STAGE076-P3-GATE" in plan["stop_condition"] or "IDS-STAGE076-P4-GATE" in plan["stop_condition"] or "IDS-STAGE076-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE077-P1-GATE" in plan["stop_condition"] or "IDS-STAGE077-P2-GATE" in plan["stop_condition"] or "IDS-STAGE077-P3-GATE" in plan["stop_condition"] or "IDS-STAGE077-P4-GATE" in plan["stop_condition"] or "IDS-STAGE077-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE078-P1-GATE" in plan["stop_condition"] or "IDS-STAGE078-P2-GATE" in plan["stop_condition"] or "IDS-STAGE078-P3-GATE" in plan["stop_condition"] or "IDS-STAGE078-P4-GATE" in plan["stop_condition"] or "IDS-STAGE078-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE079-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE084-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE084-P2-GATE" in plan["stop_condition"]
            or 'IDS-STAGE084-P4-GATE' in plan['stop_condition']
            or 'IDS-STAGE084-REVIEW-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P3-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P3-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P4-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-REVIEW-GATE' in plan['stop_condition']
            or 'IDS-STAGE086-P1-GATE' in plan['stop_condition']
        )
        )
        self.assertTrue(
            {
                "ACC-STAGE071-P3-01",
                "ACC-STAGE071-P3-02",
                "ACC-STAGE071-P3-03",
                "ACC-STAGE071-P3-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE071-P3-LOCAL-20260815-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE071-P3", run["task_id"])
        self.assertEqual("IDS-STAGE071-P4-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("IDS-V0_1-STAGE071-P3", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-P3-20260815-001"
                for item in events
            )
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-P4-20260815-001"
                for item in events
            )
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-REVIEW-20260820-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
