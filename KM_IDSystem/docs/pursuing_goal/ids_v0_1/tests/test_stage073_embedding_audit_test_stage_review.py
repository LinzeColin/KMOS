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
    / "STAGE-073_Embedding审计测试.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-074_本地Embedding兜底合同.md"
)
REVIEW_DOCUMENT = BASE / "STAGE073_STAGE_REVIEW.md"
MODULE = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_stage_review.py"
)
P1_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_contract.json"
P2_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_slice_contract.json"
P3_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_scenarios_contract.json"
P4_CONTRACT = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_delivery_contract.json"
P2_MODULE = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_slice.py"
P3_MODULE = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_scenarios.py"
P4_MODULE = BASE / "embedding_audit_test" / "stage073_embedding_audit_test_delivery.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage073-review-local.json"


class Stage073EmbeddingAuditTestStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage073_review", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage073_review_report()
        return self.__class__._report_value

    def test_review_artifacts_exist(self):
        for artifact in (
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_DOCUMENT,
            MODULE,
            P1_CONTRACT,
            P2_CONTRACT,
            P3_CONTRACT,
            P4_CONTRACT,
            P2_MODULE,
            P3_MODULE,
            P4_MODULE,
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
            "ids.stage073.embedding_audit_test.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE073-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-073", report["acceptance_id"])
        self.assertTrue(report["review_valid"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_AUDIT_TEST_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE074-P1-GATE", report["next_gate"])
        self.assertEqual(
            {"P1": True, "P2": True, "P3": True, "P4": True},
            report["phase_results"],
        )

    def test_review_replays_fixed_control_counts(self):
        self.assertEqual(
            {
                "phase1_policy_value_count": 3,
                "phase1_policy_inheritance_hop_count": 2,
                "phase1_future_queue_field_count": 12,
                "phase1_future_cost_field_count": 8,
                "phase1_future_model_field_count": 6,
                "phase1_future_audit_field_count": 18,
                "phase1_failure_state_count": 7,
                "phase2_control_request_count": 5,
                "phase2_policy_record_count": 5,
                "phase2_policy_record_field_count": 10,
                "phase2_queue_record_count": 5,
                "phase2_queue_record_field_count": 14,
                "phase2_cache_record_count": 5,
                "phase2_cache_record_field_count": 10,
                "phase2_retry_record_count": 5,
                "phase2_retry_record_field_count": 7,
                "phase2_model_record_count": 5,
                "phase2_model_record_field_count": 6,
                "phase2_cost_record_count": 5,
                "phase2_cost_record_field_count": 8,
                "phase2_audit_record_count": 5,
                "phase2_audit_record_field_count": 18,
                "phase3_scenario_count": 5,
                "phase3_scenario_field_count": 35,
                "phase3_explicit_disposition_count": 5,
                "phase3_silent_drop_count": 0,
                "phase3_human_handling_required_count": 4,
                "phase3_audit_field_check_count": 90,
                "phase3_future_call_candidate_count": 3,
                "phase3_denied_count": 1,
                "phase3_summary_only_count": 1,
                "phase3_document_restriction_count": 1,
                "phase3_full_text_count": 1,
                "phase3_budget_pause_count": 1,
                "phase4_policy_sample_count": 5,
                "phase4_audit_sample_count": 5,
                "phase4_audit_field_check_count": 90,
                "phase4_cost_sample_count": 5,
                "phase4_failure_handling_count": 5,
                "phase4_non_externalized_record_count": 5,
                "phase4_query_key_count": 7,
                "phase4_chinese_confirmation_count": 4,
                "phase4_failure_state_count": 12,
            },
            self._report()["controlled_replay"],
        )

    def test_review_preserves_authority_audit_and_rollback_boundaries(self):
        report = self._report()
        self.assertTrue(all(report["review_invariants"].values()))
        self.assertEqual(
            "PHASE4_EMBEDDING_AUDIT_TEST_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(report["rollback"]["preserve_phase1_to_phase4_evidence"])
        self.assertFalse(report["rollback"]["github_or_ovh_change_allowed"])
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])

    def test_review_keeps_runtime_and_stage074_closed(self):
        report = self._report()
        for field in self._module().REVIEW_RUNTIME_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["stage073_started"])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_stage073_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE073-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_stage073_review_report(
            phase3_report_provider=lambda: {"result": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE073-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_stage073_review_report(
            phase2_report_provider=lambda: {"input_accepted": True}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE073-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_stage073_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual("IDS-STAGE073-REVIEW-GATE", report["next_gate"])

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
                    "IDS-STAGE073",
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-STAGE074-P1-GATE",
                ),
                (
                    "IDS-STAGE074",
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-STAGE074-P2-GATE",
                ),
                (
                    "IDS-STAGE074",
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-STAGE074-P3-GATE",
                ),
                (
                    "IDS-STAGE074",
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-STAGE074-P4-GATE",
                ),
                (
                    "IDS-STAGE074",
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-STAGE074-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE074",
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-STAGE075-P1-GATE",
                ),
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

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE')),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            (plan["stage"], plan["phase"], plan["task"]),
            (
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1')),
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE073-REVIEW-01"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE073-REVIEW-02"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE073-REVIEW-03"])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE073-REVIEW-04"])
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE073-REVIEW-20260820-001"
        )
        self.assertEqual("stage_review", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE073-REVIEW", event["task_id"])
        self.assertEqual("IDS-STAGE074-P1-GATE", run["next_gate"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_AUDIT_TEST_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))


if __name__ == "__main__":
    unittest.main()
