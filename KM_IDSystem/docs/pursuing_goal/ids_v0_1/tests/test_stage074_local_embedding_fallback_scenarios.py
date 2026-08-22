import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
MODULE = (
    ROOT
    / "docs/pursuing_goal/ids_v0_1/local_embedding_fallback/"
    "stage074_local_embedding_fallback_scenarios.py"
)
CONTRACT = (
    ROOT
    / "docs/pursuing_goal/ids_v0_1/local_embedding_fallback/"
    "stage074_local_embedding_fallback_scenarios_contract.json"
)
STATUS = ROOT / "machine/facts/status.json"
PLAN = ROOT / "machine/facts/plan.json"
ACCEPTANCE = ROOT / "machine/facts/acceptance.json"
ROADMAP = ROOT / "docs/governance/roadmap.yaml"
EVENTS = ROOT / "docs/governance/events.jsonl"


class Stage074LocalEmbeddingFallbackScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("stage074_p3", MODULE)
        if not MODULE.is_file():
            raise FileNotFoundError(f"missing P3 module: {MODULE}")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load P3 module: {MODULE}")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        return self.module.build_local_embedding_fallback_phase3_report()

    def _phase2(self):
        return self.module._load_phase2_module()

    def test_contract_declares_fixed_control_only_phase3_boundary(self):
        self.assertEqual("ids.stage074.local_embedding_fallback.phase3.v1", self.contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE074-P3", self.contract["task_id"])
        self.assertEqual(
            "PHASE3_LOCAL_EMBEDDING_FALLBACK_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            self.contract["contract_state"],
        )
        self.assertTrue(self.contract["scenario_executable"])
        self.assertFalse(self.contract["execution_ready"])
        self.assertEqual("IDS-STAGE074-P4-GATE", self.contract["next_gate"])
        authority = self.contract["source_authority"]
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])
        self.assertFalse(authority["live_source_read_performed"])
        self.assertFalse(authority["authorized_fixture_access_performed"])
        self.assertEqual(5, self.contract["controlled_scenario_contract"]["scenario_count"])
        self.assertEqual(35, self.contract["controlled_scenario_contract"]["field_count"])
        self.assertEqual(18, self.contract["audit_projection_invariant_contract"]["inherited_phase2_audit_field_count"])
        self.assertEqual(90, self.contract["audit_projection_invariant_contract"]["control_audit_field_check_count"])

    def test_report_replays_all_fixed_scenarios_and_preserves_shapes(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(4, report["human_handling_required_count"])
        self.assertEqual(5, report["control_policy_resolution_record_count"])
        self.assertEqual(5, report["control_embedding_queue_record_count"])
        self.assertEqual(5, report["control_cache_record_count"])
        self.assertEqual(5, report["control_failed_retry_record_count"])
        self.assertEqual(5, report["control_cost_governor_projection_count"])
        self.assertEqual(5, report["control_model_version_projection_count"])
        self.assertEqual(5, report["control_cost_projection_count"])
        self.assertEqual(5, report["control_external_api_audit_projection_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(90, report["control_audit_field_check_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])

    def test_each_policy_budget_and_audit_scenario_is_explicit(self):
        report = self._report()
        required_fields = set(self.contract["controlled_scenario_contract"]["required_fields"])
        expected_categories = self.contract["controlled_scenario_contract"]["scenario_order"]
        self.assertEqual(
            expected_categories,
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        self.assertEqual(
            ["denied", "summary_only", "summary_only", "full_text_allowed", "full_text_allowed"],
            [item["effective_external_api_policy"] for item in report["scenario_results"]],
        )
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(required_fields, set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertFalse(scenario["silent_drop"])
                self.assertEqual(
                    scenario["expected_control_payload_scope"],
                    scenario["observed_control_payload_scope"],
                )
                self.assertEqual(scenario["expected_queue_state"], scenario["observed_queue_state"])
                self.assertEqual(
                    scenario["expected_cache_disposition"],
                    scenario["observed_cache_disposition"],
                )
                self.assertEqual(scenario["expected_retry_state"], scenario["observed_retry_state"])
                self.assertEqual(
                    scenario["expected_budget_check_state"],
                    scenario["observed_budget_check_state"],
                )
                self.assertTrue(scenario["audit_projection_required"])
                self.assertTrue(scenario["audit_projection_present"])
                self.assertEqual(18, scenario["audit_field_count"])
                self.assertTrue(scenario["audit_required_fields_present"])
                self.assertTrue(scenario["audit_reference_fields_are_control_only"])

    def test_denied_and_budget_insufficient_close_without_egress_candidate(self):
        scenarios = self._report()["scenario_results"]
        denied = scenarios[0]
        budget_paused = scenarios[4]
        self.assertFalse(denied["future_external_api_call_candidate"])
        self.assertEqual("NO_EXTERNAL_PAYLOAD_CREATED", denied["observed_control_payload_scope"])
        self.assertEqual("CONTROL_QUEUE_BLOCKED_POLICY_DENIED", denied["observed_queue_state"])
        self.assertEqual("BLOCKED_POLICY_DENIED", denied["observed_audit_disposition"])
        self.assertFalse(budget_paused["future_external_api_call_candidate"])
        self.assertEqual("CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT", budget_paused["observed_queue_state"])
        self.assertEqual("CONTROL_CACHE_PAUSED_BUDGET_INSUFFICIENT", budget_paused["observed_cache_disposition"])
        self.assertEqual("CONTROL_RETRY_PAUSED_BUDGET_INSUFFICIENT", budget_paused["observed_retry_state"])
        self.assertEqual("CONTROL_AUDIT_REQUIRED_BUDGET_PAUSED", budget_paused["observed_audit_disposition"])

    def test_future_candidates_require_complete_control_audit_projection(self):
        report = self._report()
        candidates = [
            item
            for item in report["scenario_results"]
            if item["future_external_api_call_candidate"]
        ]
        self.assertEqual(3, len(candidates))
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        for candidate in candidates:
            with self.subTest(scenario=candidate["scenario_id"]):
                self.assertTrue(candidate["audit_projection_present"])
                self.assertTrue(candidate["audit_required_fields_present"])
                self.assertTrue(candidate["audit_reference_fields_are_control_only"])
                self.assertEqual(
                    "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
                    candidate["observed_audit_disposition"],
                )
                self.assertFalse(candidate["actual_external_api_call_performed"])
                self.assertFalse(candidate["actual_model_token_consumption_performed"])
                self.assertFalse(candidate["model_version_sent_to_external_api"])

    def test_invalid_or_malformed_phase2_fails_closed(self):
        invalid = self.module.build_local_embedding_fallback_phase3_report(
            phase2_executor=lambda _control: {"input_accepted": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertFalse(invalid["phase2_shape_preserved"])
        self.assertFalse(invalid["phase2_side_effect_free"])
        self.assertEqual(0, invalid["passed_scenario_count"])

        phase2 = self._phase2()

        def malformed(_control):
            result = copy.deepcopy(
                phase2.execute_local_embedding_fallback_control_slice(
                    phase2.build_control_input()
                )
            )
            result["external_api_audit_projections"][0].pop("provider_ref")
            return result

        malformed_report = self.module.build_local_embedding_fallback_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_phase2_runtime_signal_fails_closed(self):
        phase2 = self._phase2()

        def runtime_signal(_control):
            result = copy.deepcopy(
                phase2.execute_local_embedding_fallback_control_slice(
                    phase2.build_control_input()
                )
            )
            result["external_api_call_performed"] = True
            return result

        report = self.module.build_local_embedding_fallback_phase3_report(
            phase2_executor=runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertFalse(report["phase2_side_effect_free"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])

    def test_report_is_control_only_and_has_no_runtime_side_effect_flags(self):
        report = self._report()
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_embedding_queue_count"])
        self.assertEqual(0, report["actual_cache_entry_count"])
        self.assertEqual(0, report["actual_failed_retry_count"])
        self.assertEqual(0, report["actual_cost_count"])
        self.assertEqual(0, report["actual_model_version_record_count"])
        self.assertEqual(0, report["actual_external_api_audit_record_count"])
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_current_machine_and_governance_projection_preserves_phase3_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        event_ids = {
            item["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
            for item in [json.loads(line)]
        }
        self.assertIn(status["phase"], ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-STAGE078-REVIEW",
                                           'IDS-V0_1-STAGE079-P1',
                                           'IDS-V0_1-STAGE079-P2',
                                           "IDS-V0_1-STAGE079-P1",
                                           "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                               'IDS-STAGE079-REVIEW',

                                           'IDS-V0_1-STAGE080-P1',
                                           'IDS-V0_1-STAGE080-P2',
                                           'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW', "IDS-STAGE081-P1", "IDS-STAGE081-P2", "IDS-STAGE081-P3", "IDS-STAGE081-P4", "IDS-STAGE081-REVIEW", "IDS-STAGE082-P1",
                                           "IDS-STAGE082-P2",
                                           "IDS-STAGE082-P3", "IDS-STAGE082-P4", "IDS-STAGE082-REVIEW", "IDS-STAGE083-P1", "IDS-STAGE083-P2", "IDS-STAGE083-P3", "IDS-STAGE083-P4", "IDS-STAGE083-REVIEW", "IDS-STAGE084-P1", 'IDS-STAGE084-P2', 'IDS-STAGE084-P3', 'IDS-STAGE084-P4',
                                               'IDS-STAGE084-REVIEW',

                                           'IDS-STAGE085-P2',
                                        "IDS-STAGE085-P3", "IDS-STAGE085-P4", "IDS-STAGE085-REVIEW", "IDS-STAGE086-P1", 'IDS-STAGE086-P2', 'IDS-STAGE086-P3'))
        self.assertIn(status["task"], ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                          'IDS-V0_1-STAGE079-P1',
                                          'IDS-V0_1-STAGE079-P2',
                                          "IDS-V0_1-STAGE079-P1",
                                          "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                              'IDS-V0_1-STAGE079-REVIEW',

                                          'IDS-V0_1-STAGE080-P1',
                                          'IDS-V0_1-STAGE080-P2',
                                          'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', "IDS-V0_1-STAGE081-P1", "IDS-V0_1-STAGE081-P2", "IDS-V0_1-STAGE081-P3", "IDS-V0_1-STAGE081-P4", "IDS-V0_1-STAGE081-REVIEW", "IDS-V0_1-STAGE082-P1",
                                          "IDS-V0_1-STAGE082-P2",
                                          "IDS-V0_1-STAGE082-P3", "IDS-V0_1-STAGE082-P4", "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                                              'IDS-V0_1-STAGE084-REVIEW',

                                          'IDS-V0_1-STAGE085-P2',
                                       "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW", "IDS-V0_1-STAGE086-P1", 'IDS-V0_1-STAGE086-P2', 'IDS-V0_1-STAGE086-P3'))
        self.assertIn(status["next_gate"], ("IDS-STAGE074-P4-GATE", "IDS-STAGE074-REVIEW-GATE", "IDS-STAGE075-P1-GATE",
            'IDS-STAGE075-P2-GATE', 'IDS-STAGE075-P3-GATE', 'IDS-STAGE075-P4-GATE', 'IDS-STAGE075-REVIEW-GATE', 'IDS-STAGE076-P1-GATE',
            'IDS-STAGE076-P2-GATE',
        'IDS-STAGE076-P3-GATE', 'IDS-STAGE076-P4-GATE', 'IDS-STAGE076-REVIEW-GATE', 'IDS-STAGE077-P1-GATE', 'IDS-STAGE077-P2-GATE',
        'IDS-STAGE077-P3-GATE', 'IDS-STAGE077-P4-GATE', 'IDS-STAGE077-REVIEW-GATE', 'IDS-STAGE078-P1-GATE',
         "IDS-STAGE078-P2-GATE", "IDS-STAGE078-P3-GATE", "IDS-STAGE078-P4-GATE", "IDS-STAGE078-REVIEW-GATE", 'IDS-STAGE079-P1-GATE',
                                               "IDS-STAGE079-P2-GATE",
                                               "IDS-STAGE079-P3-GATE", "IDS-STAGE079-P4-GATE", "IDS-STAGE079-REVIEW-GATE",
                                                   'IDS-STAGE080-P1-GATE',

                                               'IDS-STAGE080-P2-GATE',
                                               'IDS-STAGE080-P3-GATE',
                                               'IDS-STAGE080-P4-GATE',
                                               'IDS-STAGE080-REVIEW-GATE', 'IDS-STAGE081-P1-GATE', "IDS-STAGE081-P2-GATE", "IDS-STAGE081-P3-GATE", "IDS-STAGE081-P4-GATE", "IDS-STAGE081-REVIEW-GATE", "IDS-STAGE082-P1-GATE", "IDS-STAGE082-P2-GATE",
                                               "IDS-STAGE082-P3-GATE",
                                               "IDS-STAGE082-P4-GATE", "IDS-STAGE082-REVIEW-GATE", "IDS-STAGE083-P1-GATE", "IDS-STAGE083-P2-GATE", "IDS-STAGE083-P3-GATE", "IDS-STAGE083-P4-GATE", "IDS-STAGE083-REVIEW-GATE", "IDS-STAGE084-P1-GATE", "IDS-STAGE084-P2-GATE", 'IDS-STAGE084-P3-GATE', 'IDS-STAGE084-P4-GATE', 'IDS-STAGE084-REVIEW-GATE',
                                                   'IDS-STAGE085-P3-GATE',

                                               'IDS-STAGE085-P3-GATE',
                                            "IDS-STAGE085-P4-GATE", "IDS-STAGE085-REVIEW-GATE", "IDS-STAGE086-P1-GATE", "IDS-STAGE086-P2-GATE", 'IDS-STAGE086-P3-GATE', 'IDS-STAGE086-P4-GATE'))
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                        "IDS-V0_1-STAGE079-P1",
                                        "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                        "IDS-V0_1-STAGE079-REVIEW",
                                        'IDS-V0_1-STAGE080-P1',
                                        'IDS-V0_1-STAGE080-P2',
                                        'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                                        'IDS-V0_1-STAGE082-P2',
                                        'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", "IDS-V0_1-STAGE084-P2", 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                                            "IDS-V0_1-STAGE084-REVIEW",

                                        'IDS-V0_1-STAGE085-P2',
                                     "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW", "IDS-V0_1-STAGE086-P1", 'IDS-V0_1-STAGE086-P2', 'IDS-V0_1-STAGE086-P3'))
        self.assertIn(acceptance["task"], ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                              "IDS-V0_1-STAGE079-P1",
                                              "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                              "IDS-V0_1-STAGE079-REVIEW",
                                              'IDS-V0_1-STAGE080-P1',
                                              'IDS-V0_1-STAGE080-P2',
                                              'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                                              'IDS-V0_1-STAGE082-P2',
                                              'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", "IDS-V0_1-STAGE084-P2", 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                                                  "IDS-V0_1-STAGE084-REVIEW",

                                              'IDS-V0_1-STAGE085-P2',
                                           "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW", "IDS-V0_1-STAGE086-P1", 'IDS-V0_1-STAGE086-P2', 'IDS-V0_1-STAGE086-P3'))
        self.assertTrue(
            'current_stage_id: "IDS-STAGE074"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE075"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE076"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE077"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE079"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE080"' in roadmap_text
        )
        self.assertTrue(
            'current_phase_id: "IDS-STAGE074-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE075-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE076-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE077-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE079-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE080-P4"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE074-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE075-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE076-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE077-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE079-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE080-P4"' in roadmap_text
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE074-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P3-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE076-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE078-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE079-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE080-REVIEW-GATE"' in roadmap_text
        )
        self.assertIn("EVT-IDS-V0_1-STAGE074-P3-20260821-001", event_ids)


if __name__ == "__main__":
    unittest.main()
