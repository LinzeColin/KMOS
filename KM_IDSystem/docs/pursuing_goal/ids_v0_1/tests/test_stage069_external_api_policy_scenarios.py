import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_contract.json"
PHASE2_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_slice_contract.json"
PHASE2_SLICE = BASE / "external_api_policy" / "stage069_external_api_policy_slice.py"
CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_scenarios_contract.json"
SCENARIOS = BASE / "external_api_policy" / "stage069_external_api_policy_scenarios.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage069-p3-local.json"


class Stage069ExternalApiPolicyPhase3Tests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location(
            "stage069_external_api_policy_scenarios", SCENARIOS
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        return self._module().build_external_api_policy_phase3_report()

    def test_phase3_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            CONTRACT,
            SCENARIOS,
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

    def test_contract_is_executable_and_keeps_real_runtime_closed(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage069.external_api_policy.phase3.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE069-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE069-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
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
        self.assertEqual(5, replay["control_request_count"])
        self.assertEqual(5, replay["external_api_audit_projection_count"])
        self.assertTrue(replay["phase2_invalid_result_fails_closed"])

        scenarios = contract["controlled_scenario_contract"]
        self.assertEqual(23, scenarios["field_count"])
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertFalse(scenarios["source_or_document_body_allowed"])
        self.assertFalse(scenarios["summary_body_allowed"])
        self.assertFalse(scenarios["chunk_text_allowed"])
        self.assertFalse(scenarios["silent_drop_allowed"])

        audit = contract["audit_projection_invariant_contract"]
        self.assertEqual(18, audit["inherited_phase2_audit_field_count"])
        self.assertEqual(5, audit["control_audit_projection_count"])
        self.assertEqual(90, audit["control_audit_field_check_count"])
        self.assertEqual(3, audit["future_external_api_call_candidate_count"])
        self.assertTrue(audit["future_external_api_call_audit_invariant_required"])

        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_scenario_report_passes_all_taskpack_cases(self):
        module = self._module()
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(module.PASS_RESULT, report["result"])
        self.assertEqual("IDS-STAGE069-P4-GATE", report["next_gate"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(4, report["human_handling_required_count"])
        self.assertTrue(report["all_taskpack_special_scenarios_covered"])
        self.assertEqual(
            list(module.REQUIRED_SCENARIO_CATEGORIES),
            [item["scenario_category"] for item in report["scenario_results"]],
        )
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual(set(module.SCENARIO_RESULT_FIELDS), set(scenario))
                self.assertTrue(scenario["expectation_met"])
                self.assertFalse(scenario["silent_drop"])
                self.assertTrue(scenario["referenced_policy_resolution_ref"].startswith("policy-resolution:control:"))
                self.assertTrue(scenario["referenced_external_api_audit_ref"].startswith("external-api-audit:control:"))

    def test_denied_never_forms_an_external_payload(self):
        scenario = self._report()["scenario_results"][0]
        self.assertEqual("denied", scenario["effective_external_api_policy"])
        self.assertEqual("NO_EXTERNAL_PAYLOAD_POLICY_DENIED", scenario["external_payload_mode"])
        self.assertEqual("NO_CONTROL_PAYLOAD_REFERENCE", scenario["observed_control_payload_scope"])
        self.assertEqual("CONTROL_QUEUE_BLOCKED_POLICY_DENIED", scenario["observed_queue_state"])
        self.assertEqual("BLOCKED_POLICY_DENIED", scenario["audit_disposition"])
        self.assertFalse(scenario["future_external_api_call_candidate"])
        self.assertFalse(scenario["actual_external_api_call_performed"])
        self.assertFalse(scenario["actual_model_token_consumption_performed"])

    def test_summary_only_never_escalates_to_text_block_scope(self):
        summary_scenarios = self._report()["scenario_results"][1:3]
        self.assertEqual(2, len(summary_scenarios))
        for scenario in summary_scenarios:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertEqual("summary_only", scenario["effective_external_api_policy"])
                self.assertEqual(
                    "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
                    scenario["external_payload_mode"],
                )
                self.assertEqual(
                    "CONTROL_SUMMARY_REFERENCE_ONLY",
                    scenario["observed_control_payload_scope"],
                )
                self.assertEqual(
                    "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
                    scenario["observed_queue_state"],
                )
                self.assertTrue(scenario["audit_projection_present"])
                self.assertTrue(scenario["human_handling_required"])

    def test_full_text_and_budget_pause_keep_distinct_boundaries(self):
        full_text, budget_pause = self._report()["scenario_results"][3:5]
        self.assertEqual("full_text_allowed", full_text["effective_external_api_policy"])
        self.assertEqual(
            "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
            full_text["observed_control_payload_scope"],
        )
        self.assertEqual(
            "CONTROL_QUEUE_ELIGIBLE_NOT_PERSISTED_RUNTIME_DISABLED",
            full_text["observed_queue_state"],
        )
        self.assertTrue(full_text["future_external_api_call_candidate"])

        self.assertEqual("full_text_allowed", budget_pause["effective_external_api_policy"])
        self.assertEqual(
            "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
            budget_pause["observed_control_payload_scope"],
        )
        self.assertEqual(
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
            budget_pause["observed_queue_state"],
        )
        self.assertFalse(budget_pause["future_external_api_call_candidate"])
        self.assertFalse(budget_pause["actual_external_api_call_performed"])

    def test_audit_projection_is_present_before_each_future_candidate(self):
        report = self._report()
        self.assertEqual(5, report["audit_projection_required_count"])
        self.assertEqual(5, report["audit_projection_present_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(90, report["control_audit_field_check_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        for scenario in report["scenario_results"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertTrue(scenario["audit_projection_required"])
                self.assertTrue(scenario["audit_projection_present"])
                self.assertEqual(18, scenario["audit_field_count"])

    def test_invalid_phase2_result_fails_closed(self):
        module = self._module()
        report = module.build_external_api_policy_phase3_report(
            lambda _: {"input_accepted": True, "execution_state": "unexpected"}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(module.FAIL_RESULT, report["result"])
        self.assertFalse(report["phase2_shape_preserved"])
        self.assertEqual(0, report["passed_scenario_count"])

    def test_no_runtime_side_effect_or_payload_content_is_created(self):
        module = self._module()
        report = self._report()
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])
        self.assertEqual(0, report["actual_external_api_audit_record_count"])
        self.assertFalse(report["control_payload_content_retained"])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(report["external_api_policy_scenario_can_replace_source_document"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        for field in module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_current_governance_projects_phase3_without_upload_or_runtime(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(status["stage"], ("IDS-STAGE069", "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                           'IDS-STAGE079',
                                           "IDS-STAGE079",
                                           'IDS-STAGE080', "IDS-STAGE081", "IDS-STAGE082"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE069-P3",
                    "IDS-V0_1-STAGE069-P3",
                    "IDS-STAGE069-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE069-P4",
                    "IDS-V0_1-STAGE069-P4",
                    "IDS-STAGE069-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-STAGE070-P2-GATE",
                ),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                (
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-STAGE070-P1-GATE",
                ), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
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
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ('IDS-STAGE081-P2', 'IDS-V0_1-STAGE081-P2', 'IDS-STAGE081-P3-GATE'), ("IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE069", "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                         "IDS-STAGE079",
                                         'IDS-STAGE080', 'IDS-STAGE081', 'IDS-STAGE082'))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
                ("IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3"),
                ("IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW"),
                ("IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1"),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2"),
("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3"),
("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4"),
("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW"),
("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1"),
("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2"),
("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3"),
("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4"),
("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW"),
("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1"),
("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2"),
("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3"),
("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"),
("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),
("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4"),
                ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW'),
                ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4"),
                    ('IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW'),

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW'), ('IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1'), ("IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2"), ("IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3"), ("IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4"), ("IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW"), ("IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1")),
        )
        self.assertTrue(
            (
("IDS-STAGE069-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P2-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P3-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P4-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-REVIEW-GATE" in plan["stop_condition"]
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"], "IDS-STAGE075-P4-GATE" in plan["stop_condition"]
            )
        )
        for acceptance_id in (
            "ACC-STAGE069-P3-01",
            "ACC-STAGE069-P3-02",
            "ACC-STAGE069-P3-03",
            "ACC-STAGE069-P3-04",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertTrue(
                    any(item["id"] == acceptance_id for item in acceptance["items"])
                )
        self.assertEqual("IDS-V0_1-STAGE069-P3", run["task_id"])
        self.assertEqual("IDS-STAGE069-P4-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["external_api_call_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage069_phase3", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE069-P3", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE069-P3-20260814-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
