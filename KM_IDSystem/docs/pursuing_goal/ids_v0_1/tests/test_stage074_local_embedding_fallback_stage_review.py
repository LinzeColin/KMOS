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
    / "STAGE-074_本地Embedding兜底合同.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-075_外部API覆盖授权审计.md"
)
REVIEW_DOCUMENT = BASE / "STAGE074_STAGE_REVIEW.md"
MODULE = (
    BASE
    / "local_embedding_fallback"
    / "stage074_local_embedding_fallback_stage_review.py"
)
P1_CONTRACT = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_contract.json"
P2_CONTRACT = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_slice_contract.json"
P3_CONTRACT = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_scenarios_contract.json"
P4_CONTRACT = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_delivery_contract.json"
P2_MODULE = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_slice.py"
P3_MODULE = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_scenarios.py"
P4_MODULE = BASE / "local_embedding_fallback" / "stage074_local_embedding_fallback_delivery.py"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage074-review-local.json"


class Stage074ReviewTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("stage074_review_test", MODULE)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_required_artifacts_exist(self):
        for path in (
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
            self.assertTrue(path.is_file(), path)

    def test_phase_contracts_and_reports_pass(self):
        report = self._module().build_stage074_review_report()
        self.assertTrue(report["review_valid"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE075-P1-GATE", report["next_gate"])

    def test_controlled_replay_has_exact_frozen_shapes(self):
        report = self._module().build_stage074_review_report()
        self.assertEqual(
            {
                "phase1_policy_value_count": 3,
                "phase1_policy_inheritance_hop_count": 2,
                "phase1_future_queue_field_count": 12,
                "phase1_future_cache_field_count": 10,
                "phase1_future_retry_field_count": 7,
                "phase1_future_cost_governor_field_count": 16,
                "phase1_future_cost_field_count": 8,
                "phase1_future_model_field_count": 6,
                "phase1_future_audit_field_count": 18,
                "phase1_failure_state_count": 12,
                "phase2_control_request_count": 5,
                "phase2_input_field_count": 20,
                "phase2_policy_record_field_count": 10,
                "phase2_queue_record_field_count": 14,
                "phase2_cache_record_field_count": 10,
                "phase2_retry_record_field_count": 7,
                "phase2_cost_governor_record_field_count": 16,
                "phase2_model_record_field_count": 6,
                "phase2_cost_record_field_count": 8,
                "phase2_audit_record_field_count": 18,
                "phase2_failure_state_count": 12,
                "phase3_scenario_count": 5,
                "phase3_scenario_field_count": 35,
                "phase3_audit_field_count": 18,
                "phase3_audit_field_check_count": 90,
                "phase3_future_call_candidate_count": 3,
                "phase3_human_handling_required_count": 4,
                "phase3_failure_state_count": 11,
                "phase4_policy_sample_count": 5,
                "phase4_audit_sample_count": 5,
                "phase4_audit_field_count": 18,
                "phase4_audit_field_check_count": 90,
                "phase4_cost_sample_count": 5,
                "phase4_failure_handling_count": 5,
                "phase4_non_externalized_record_count": 5,
                "phase4_query_key_count": 7,
                "phase4_chinese_feedback_count": 4,
                "phase4_failure_state_count": 12,
            },
            report["controlled_replay"],
        )

    def test_authority_rollback_and_runtime_are_closed(self):
        report = self._module().build_stage074_review_report()
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])
        self.assertTrue(report["review_invariants"]["p4_to_p3_control_rollback_chain_preserved"])
        self.assertTrue(report["review_invariants"]["runtime_actions_disabled"])
        self.assertFalse(report["secondary_authority_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertEqual(
            "PASS_PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(all(value == 0 for key, value in report.items() if key.startswith("actual_") and key.endswith("_count")))
        self.assertTrue(
            all(
                report[field] is False
                for field in self._module().REVIEW_RUNTIME_FALSE_FIELDS
            )
        )

    def test_next_stage_stays_closed_except_for_gate(self):
        report = self._module().build_stage074_review_report()
        self.assertTrue(report["review_invariants"]["next_stage_taskpack_available_but_not_started"])
        self.assertTrue(report["review_invariants"]["stage075_gate_only_opens_after_review"])
        self.assertFalse(report["stage075_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_stage074_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE074-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase3_report_fails_closed(self):
        report = self._module().build_stage074_review_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertEqual("IDS-STAGE074-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase2_report_fails_closed(self):
        report = self._module().build_stage074_review_report(
            phase2_report_provider=lambda: {"input_accepted": False}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertEqual("IDS-STAGE074-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_stage074_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertEqual("IDS-STAGE074-REVIEW-GATE", report["next_gate"])

    def test_governance_projection_records_stage_review(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ("IDS-STAGE075", "IDS-V0_1-STAGE075-P1", "IDS-V0_1-STAGE075-P1", "IDS-STAGE075-P2-GATE"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-P2", "IDS-V0_1-STAGE075-P2", "IDS-STAGE075-P3-GATE"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-P3", "IDS-V0_1-STAGE075-P3", "IDS-STAGE075-P4-GATE"), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
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
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            (plan["stage"], plan["phase"], plan["task"]),
            (
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ("IDS-STAGE075", "IDS-V0_1-STAGE075-P1", "IDS-V0_1-STAGE075-P1"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-P2", "IDS-V0_1-STAGE075-P2"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-P3", "IDS-V0_1-STAGE075-P3"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-P4", "IDS-V0_1-STAGE075-P4"), ("IDS-STAGE075", "IDS-V0_1-STAGE075-REVIEW", "IDS-V0_1-STAGE075-REVIEW"),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2")),
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-074"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE074-REVIEW-01"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE074-REVIEW-02"])
        self.assertEqual("已通过", acceptance_by_id["ACC-STAGE074-REVIEW-03"])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE074-REVIEW-04"])
        self.assertTrue(
            'current_phase_id: "IDS-STAGE074-REVIEW"' in roadmap
            or 'current_phase_id: "IDS-STAGE075-P1"' in roadmap
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE075-P1"' in roadmap
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE075-P1-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE075-P2-GATE"' in roadmap
        )
        self.assertIn("EVT-IDS-V0_1-STAGE074-REVIEW-20260821-001", event_ids)
        self.assertEqual("IDS-STAGE075-P1-GATE", run["next_gate"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))


if __name__ == "__main__":
    unittest.main()
