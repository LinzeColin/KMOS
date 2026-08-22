import copy
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
CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_scenarios_contract.json"
)
SCENARIOS = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_scenarios.py"
)
SCOPE = BASE / "STAGE072_PHASE3_EMBEDDING_MODEL_VERSION_CONTROLLED_SCENARIOS.md"
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
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage072-p3-local.json"


class Stage072EmbeddingModelVersionPhase3Tests(unittest.TestCase):
    def _module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _scenarios(self):
        return self._module("stage072_embedding_model_version_scenarios", SCENARIOS)

    def _phase2(self):
        return self._module("stage072_embedding_model_version_phase2", PHASE2_SLICE)

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
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_has_exact_p3_scope_and_runtime_remains_closed(self):
        contract = self._contract()
        module = self._scenarios()
        self.assertEqual(
            "ids.stage072.embedding_model_version.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE072-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE072-P4-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE072_TASKPACK_PHASE1_PHASE2_STAGE071_REVIEW_AND_BATCH_LOCK_ONLY",
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
        self.assertEqual(5, replay["control_request_count"])
        self.assertEqual(5, replay["policy_resolution_record_count"])
        self.assertEqual(14, replay["embedding_queue_record_field_count"])
        self.assertEqual(10, replay["cache_record_field_count"])
        self.assertEqual(7, replay["failed_retry_record_field_count"])
        self.assertEqual(6, replay["model_version_projection_field_count"])
        self.assertEqual(8, replay["cost_projection_field_count"])
        self.assertEqual(18, replay["external_api_audit_projection_field_count"])

        scenarios = contract["controlled_scenario_contract"]
        self.assertEqual(list(module.SCENARIO_RESULT_FIELDS), scenarios["required_fields"])
        self.assertEqual(35, scenarios["field_count"])
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(
            list(module.REQUIRED_SCENARIO_CATEGORIES),
            scenarios["scenario_order"],
        )
        audit = contract["audit_projection_invariant_contract"]
        self.assertEqual(5, audit["control_audit_projection_count"])
        self.assertEqual(90, audit["control_audit_field_check_count"])
        self.assertEqual(3, audit["future_external_api_call_candidate_count"])
        self.assertEqual(11, contract["failure_and_stop_contract"]["failure_state_count"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_report_replays_exact_p2_shape_and_all_five_scenarios(self):
        module = self._scenarios()
        report = module.build_embedding_model_version_phase3_report()
        self.assertTrue(report["valid"])
        self.assertEqual(module.PASS_RESULT, report["result"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(4, report["human_handling_required_count"])
        self.assertTrue(report["all_taskpack_special_scenarios_covered"])
        self.assertTrue(report["policy_payload_boundaries_preserved"])
        self.assertTrue(report["queue_cache_retry_boundaries_preserved"])
        self.assertTrue(report["budget_insufficient_pause_preserved"])
        self.assertEqual(5, report["control_policy_resolution_record_count"])
        self.assertEqual(5, report["control_embedding_queue_record_count"])
        self.assertEqual(5, report["control_cache_record_count"])
        self.assertEqual(5, report["control_failed_retry_record_count"])
        self.assertEqual(5, report["control_model_version_projection_count"])
        self.assertEqual(5, report["control_cost_projection_count"])
        self.assertEqual(5, report["control_external_api_audit_projection_count"])

    def test_scenario_records_keep_exact_shape_and_control_only_references(self):
        module = self._scenarios()
        report = module.build_embedding_model_version_phase3_report()
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
                self.assertFalse(record["model_version_sent_to_external_api"])
                self.assertTrue(record["audit_projection_present"])
                self.assertTrue(record["audit_required_fields_present"])
                self.assertTrue(record["audit_reference_fields_are_control_only"])
                for field in (
                    "referenced_policy_resolution_ref",
                    "referenced_embedding_queue_request_ref",
                    "referenced_cache_entry_ref",
                    "referenced_retry_ref",
                    "referenced_external_api_audit_ref",
                ):
                    self.assertIn(":control:stage072-p2:", record[field])

    def test_denied_summary_only_and_full_text_boundaries_are_distinct(self):
        report = self._scenarios().build_embedding_model_version_phase3_report()
        records = {item["scenario_category"]: item for item in report["scenario_results"]}
        denied = records["DENIED_EGRESS_BLOCK_CONTROL"]
        self.assertEqual("denied", denied["effective_external_api_policy"])
        self.assertEqual(
            "NO_CONTROL_PAYLOAD_REFERENCE",
            denied["observed_control_payload_scope"],
        )
        self.assertEqual(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
            denied["observed_queue_state"],
        )
        self.assertEqual("BLOCKED_POLICY_DENIED", denied["observed_audit_disposition"])
        self.assertFalse(denied["future_external_api_call_candidate"])

        summary = records["SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL"]
        restricted = records["DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL"]
        self.assertEqual("summary_only", summary["effective_external_api_policy"])
        self.assertEqual("summary_only", restricted["effective_external_api_policy"])
        self.assertEqual(
            "CONTROL_SUMMARY_REFERENCE_ONLY",
            summary["observed_control_payload_scope"],
        )
        self.assertEqual(
            "CONTROL_SUMMARY_REFERENCE_ONLY",
            restricted["observed_control_payload_scope"],
        )
        self.assertTrue(summary["future_external_api_call_candidate"])
        self.assertTrue(restricted["future_external_api_call_candidate"])

        full_text = records["FULL_TEXT_REFERENCE_BOUNDARY_CONTROL"]
        self.assertEqual("full_text_allowed", full_text["effective_external_api_policy"])
        self.assertEqual(
            "CONTROL_CHUNK_TEXT_REFERENCE_ONLY",
            full_text["observed_control_payload_scope"],
        )
        self.assertTrue(full_text["future_external_api_call_candidate"])

    def test_budget_pause_and_audit_precondition_are_preserved(self):
        report = self._scenarios().build_embedding_model_version_phase3_report()
        records = {item["scenario_category"]: item for item in report["scenario_results"]}
        budget = records["BUDGET_INSUFFICIENT_PAUSE_CONTROL"]
        self.assertEqual("CONTROL_BUDGET_INSUFFICIENT", budget["observed_budget_check_state"])
        self.assertEqual(
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
            budget["observed_queue_state"],
        )
        self.assertEqual(
            "CONTROL_CACHE_PAUSED_BUDGET_INSUFFICIENT",
            budget["observed_cache_disposition"],
        )
        self.assertEqual(
            "CONTROL_RETRY_PAUSED_BUDGET_INSUFFICIENT",
            budget["observed_retry_state"],
        )
        self.assertFalse(budget["future_external_api_call_candidate"])
        self.assertTrue(report["audit_projection_invariant_preserved"])
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(90, report["control_audit_field_check_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])
        for record in report["scenario_results"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["audit_projection_required"])
                self.assertTrue(record["audit_projection_present"])
                self.assertEqual(18, record["audit_field_count"])

    def test_invalid_or_malformed_phase2_result_fails_closed(self):
        module = self._scenarios()
        invalid = module.build_embedding_model_version_phase3_report(
            phase2_executor=lambda _control: {"input_accepted": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(module.FAIL_RESULT, invalid["result"])
        self.assertFalse(invalid["phase2_shape_preserved"])
        self.assertFalse(invalid["phase2_side_effect_free"])
        self.assertEqual(0, invalid["passed_scenario_count"])

        phase2 = self._phase2()

        def malformed(_control):
            result = copy.deepcopy(
                phase2.execute_embedding_model_version_control_slice(
                    phase2.build_control_input()
                )
            )
            result["external_api_audit_projections"][3].pop("model_ref")
            return result

        malformed_report = module.build_embedding_model_version_phase3_report(
            malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])
        self.assertEqual(4, malformed_report["passed_scenario_count"])

    def test_runtime_and_business_decisions_remain_closed(self):
        module = self._scenarios()
        report = module.build_embedding_model_version_phase3_report()
        self.assertFalse(report["control_payload_content_retained"])
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_embedding_queue_count"])
        self.assertEqual(0, report["actual_cache_entry_count"])
        self.assertEqual(0, report["actual_failed_retry_count"])
        self.assertEqual(0, report["actual_model_version_record_count"])
        self.assertEqual(0, report["actual_cost_count"])
        self.assertEqual(0, report["actual_external_api_audit_record_count"])
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertFalse(
            report["embedding_model_version_scenario_can_replace_source_document"]
        )
        self.assertFalse(
            report[
                "embedding_model_version_scenario_can_become_business_fact_authority"
            ]
        )
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        for field in module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["batch_review_performed"])
        self.assertFalse(report["stage073_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(
            all(
                any("一" <= char <= "鿿" for char in message)
                for message in report["chinese_feedback"]
            )
        )

    def test_scope_explains_authority_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "预算不足",
            "审计",
            "IDS-STAGE072-P4-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_governance_projection_records_p3_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                (
                    'IDS-STAGE076',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-STAGE076-REVIEW-GATE',
                ),
                (
                    'IDS-STAGE076',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-STAGE077-P1-GATE',
                ),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE')
            ,
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-V0_1-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P2", "IDS-V0_1-STAGE084-P2", "IDS-STAGE084-P3-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-V0_1-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-V0_1-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-V0_1-STAGE084-REVIEW', 'IDS-STAGE085-P1-GATE'),
                ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
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
                                        ))
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE072-P3-01",
                "ACC-STAGE072-P3-02",
                "ACC-STAGE072-P3-03",
                "ACC-STAGE072-P3-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("RUN-IDS-STAGE072-P3-LOCAL-20260820-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE072-P3", run["task_id"])
        self.assertEqual("IDS-STAGE072-P4-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_call_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            'current_stage_id: "IDS-STAGE072"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE073"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE072-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P1"' in roadmap_text or 'current_task_id: "IDS-V0_1-STAGE073-P2"' in roadmap_text
        )
        self.assertTrue(
            {
                "EVT-IDS-V0_1-STAGE072-P1-20260820-001",
                "EVT-IDS-V0_1-STAGE072-P2-20260820-001",
                "EVT-IDS-V0_1-STAGE072-P3-20260820-001",
                "EVT-IDS-V0_1-STAGE072-P4-20260820-001",
                "EVT-IDS-V0_1-STAGE072-REVIEW-20260820-001",
            }.issubset(event_ids)
        )


if __name__ == "__main__":
    unittest.main()
