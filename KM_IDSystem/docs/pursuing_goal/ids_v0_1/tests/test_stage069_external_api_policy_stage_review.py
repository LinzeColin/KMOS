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
    / "STAGE-069_外部API策略继承.md"
)
REVIEW_DOCUMENT = BASE / "STAGE069_STAGE_REVIEW.md"
MODULE = BASE / "external_api_policy" / "stage069_external_api_policy_stage_review.py"
PHASE1_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_contract.json"
PHASE2_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_slice_contract.json"
PHASE3_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_scenarios_contract.json"
PHASE4_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_delivery_contract.json"
P2_MODULE = BASE / "external_api_policy" / "stage069_external_api_policy_slice.py"
P3_MODULE = BASE / "external_api_policy" / "stage069_external_api_policy_scenarios.py"
P4_MODULE = BASE / "external_api_policy" / "stage069_external_api_policy_delivery.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage069-review-local.json"


class Stage069ExternalApiPolicyStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage069_review", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage069_review_report()
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
            "ids.stage069.external_api_policy.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE069-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-069", report["acceptance_id"])
        self.assertTrue(report["review_valid"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EXTERNAL_API_POLICY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE070-P1-GATE", report["next_gate"])
        self.assertEqual(
            {"P1": True, "P2": True, "P3": True, "P4": True},
            report["phase_results"],
        )

    def test_review_replays_fixed_control_counts(self):
        replay = self._report()["controlled_replay"]
        self.assertEqual(15, replay["phase1_reference_input_field_count"])
        self.assertEqual(23, replay["phase1_future_policy_output_field_count"])
        self.assertEqual(12, replay["phase1_future_queue_field_count"])
        self.assertEqual(8, replay["phase1_future_cost_field_count"])
        self.assertEqual(18, replay["phase1_future_audit_field_count"])
        self.assertEqual(13, replay["phase1_failure_state_count"])
        self.assertEqual(5, replay["phase2_control_request_count"])
        self.assertEqual(5, replay["phase2_policy_resolution_count"])
        self.assertEqual(23, replay["phase2_policy_resolution_field_count"])
        self.assertEqual(5, replay["phase2_queue_intent_count"])
        self.assertEqual(12, replay["phase2_queue_intent_field_count"])
        self.assertEqual(5, replay["phase2_cost_projection_count"])
        self.assertEqual(8, replay["phase2_cost_projection_field_count"])
        self.assertEqual(5, replay["phase2_audit_projection_count"])
        self.assertEqual(18, replay["phase2_audit_field_count"])
        self.assertEqual(1, replay["phase2_policy_denied_count"])
        self.assertEqual(1, replay["phase2_budget_pause_count"])
        self.assertEqual(3, replay["phase2_eligible_not_persisted_count"])
        self.assertEqual(5, replay["phase3_scenario_count"])
        self.assertEqual(5, replay["phase3_explicit_disposition_count"])
        self.assertEqual(0, replay["phase3_silent_drop_count"])
        self.assertEqual(4, replay["phase3_human_handling_required_count"])
        self.assertEqual(18, replay["phase3_audit_field_count"])
        self.assertEqual(90, replay["phase3_audit_field_check_count"])
        self.assertEqual(3, replay["phase3_future_external_api_call_candidate_count"])
        self.assertEqual(5, replay["phase4_policy_sample_count"])
        self.assertEqual(5, replay["phase4_audit_sample_count"])
        self.assertEqual(18, replay["phase4_audit_field_count"])
        self.assertEqual(90, replay["phase4_audit_field_check_count"])
        self.assertEqual(5, replay["phase4_cost_sample_count"])
        self.assertEqual(5, replay["phase4_failure_handling_count"])
        self.assertEqual(5, replay["phase4_non_externalized_record_count"])
        self.assertEqual(4, replay["phase4_query_key_count"])
        self.assertEqual(3, replay["phase4_chinese_confirmation_count"])
        self.assertEqual(12, replay["phase4_failure_state_count"])

    def test_review_preserves_authority_audit_and_rollback_boundaries(self):
        report = self._report()
        self.assertTrue(all(report["review_invariants"].values()))
        self.assertEqual(
            "PHASE4_EXTERNAL_API_POLICY_METADATA_ONLY_DELIVERY_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(report["rollback"]["preserve_phase1_to_phase4_evidence"])
        self.assertFalse(report["rollback"]["github_or_ovh_change_allowed"])
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])

    def test_review_keeps_runtime_and_stage070_closed(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chunking_execution_performed",
            "external_payload_created",
            "external_api_call_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "embedding_queue_execution_performed",
            "cache_read_or_write_performed",
            "actual_external_api_audit_record_created",
            "actual_audit_log_query_performed",
            "actual_externalization_record_query_performed",
            "actual_policy_rollback_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage070_started",
            "stage070_entry_allowed",
            "batch_review_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_stage069_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE069-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_stage069_review_report(
            phase3_report_provider=lambda: {"result": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE069-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_stage069_review_report(
            phase2_report_provider=lambda: {"input_accepted": True}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE069-REVIEW-GATE", report["next_gate"])

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
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE069",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-STAGE070-P1-GATE",
                ),
                (
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-STAGE070-P2-GATE",
                ),
                (
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-STAGE070-P3-GATE",
                ),
(
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-STAGE070-P4-GATE",
                ),
(
                    "IDS-STAGE070",
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-STAGE070-REVIEW-GATE",
                ),
("IDS-STAGE070", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
("IDS-STAGE071", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
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
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE")),
        )
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
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
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW'), ('IDS-STAGE081-P1', 'IDS-V0_1-STAGE081-P1'), ("IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2"), ("IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3"), ("IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4"), ("IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW"), ("IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1"),
                ("IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2")),
        )
        self.assertTrue(
            (
("IDS-STAGE070-P1-GATE" in plan["stop_condition"]
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
        self.assertTrue(
            {
                "ACC-STAGE069-REVIEW-01",
                "ACC-STAGE069-REVIEW-02",
                "ACC-STAGE069-REVIEW-03",
                "ACC-STAGE069-REVIEW-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE069-REVIEW-LOCAL-20260815-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE069-REVIEW", run["task_id"])
        self.assertEqual("IDS-STAGE070-P1-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage069_review", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE069-REVIEW", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE069-REVIEW-20260815-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
