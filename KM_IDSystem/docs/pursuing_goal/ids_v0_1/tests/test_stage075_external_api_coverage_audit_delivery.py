import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT = (
    BASE
    / "external_api_coverage_audit/"
    "stage075_external_api_coverage_audit_delivery_contract.json"
)
DELIVERY = (
    BASE
    / "external_api_coverage_audit/"
    "stage075_external_api_coverage_audit_delivery.py"
)
P2 = (
    BASE
    / "external_api_coverage_audit/"
    "stage075_external_api_coverage_audit_slice.py"
)
STATUS = ROOT / "machine/facts/status.json"
PLAN = ROOT / "machine/facts/plan.json"
ACCEPTANCE = ROOT / "machine/facts/acceptance.json"
ROADMAP = ROOT / "docs/governance/roadmap.yaml"
EVENTS = ROOT / "docs/governance/events.jsonl"
RUN = ROOT / "machine/runs/2026-08-21-stage075-p4-local.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage075ExternalApiCoverageAuditPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load("stage075_p4", DELIVERY)
        cls.p2 = _load("stage075_p2", P2)

    def report(self):
        return self.module.build_external_api_coverage_audit_phase4_delivery_report()

    def test_contract_scope_and_counts(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage075.external_api_coverage_audit.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE075-P4", contract["task_id"])
        self.assertEqual(
            "PHASE4_EXTERNAL_API_COVERAGE_AUDIT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["delivery_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual(
            ("IDS-STAGE075-P4-GATE", "IDS-STAGE075-REVIEW-GATE"),
            (contract["entry_gate"], contract["next_gate"]),
        )
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertFalse(contract["source_authority"]["source_body_or_path_allowed"])
        self.assertEqual(
            (5, 35, 19, 95, 1, 4),
            (
                contract["phase3_controlled_scenario_replay_contract"]["scenario_count"],
                contract["phase3_controlled_scenario_replay_contract"]["scenario_field_count"],
                contract["phase3_controlled_scenario_replay_contract"]["external_api_coverage_audit_projection_field_count"],
                contract["phase3_controlled_scenario_replay_contract"]["audit_field_check_count"],
                contract["phase3_controlled_scenario_replay_contract"]["owner_forced_egress_override_control_projection_count"],
                contract["phase3_controlled_scenario_replay_contract"]["owner_forced_egress_override_field_count"],
            ),
        )
        self.assertEqual(
            (5, 5, 19, 95, 5, 5, 5, 8, 1, 4, 13),
            (
                contract["delivery_evidence_contract"]["policy_sample_count"],
                contract["delivery_evidence_contract"]["control_audit_log_sample_count"],
                contract["delivery_evidence_contract"]["control_audit_projection_field_count"],
                contract["delivery_evidence_contract"]["control_audit_field_check_count"],
                contract["delivery_evidence_contract"]["zero_cost_estimate_sample_count"],
                contract["delivery_evidence_contract"]["failure_handling_result_count"],
                contract["delivery_evidence_contract"]["non_externalized_data_record_count"],
                contract["delivery_evidence_contract"]["externalization_record_query_key_count"],
                contract["delivery_evidence_contract"]["owner_forced_egress_override_precondition_sample_count"],
                contract["delivery_evidence_contract"]["owner_forced_egress_override_field_count"],
                contract["failure_and_stop_contract"]["failure_state_count"],
            ),
        )

    def test_delivery_samples_audits_and_owner_precondition_are_control_only(self):
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            (self.module.PASS_RESULT, self.module.NEXT_GATE),
            (report["result"], report["next_gate"]),
        )
        self.assertEqual(
            (5, 5, 19, 95, 5, 5, 5, 8, 1, 4, 4),
            (
                report["policy_sample_count"],
                report["control_audit_log_sample_count"],
                report["control_audit_field_count"],
                report["control_audit_field_check_count"],
                report["zero_cost_estimate_sample_count"],
                report["failure_handling_result_count"],
                report["non_externalized_data_record_count"],
                report["externalization_record_query_key_count"],
                report["owner_forced_egress_override_precondition_sample_count"],
                report["owner_forced_egress_override_field_count"],
                report["owner_forced_egress_override_field_check_count"],
            ),
        )
        self.assertEqual((3, 1, 1, 4), (
            report["future_external_api_call_candidate_count"],
            report["policy_denied_sample_count"],
            report["budget_pause_sample_count"],
            report["human_handling_required_count"],
        ))
        for item in report["external_api_coverage_audit_policy_samples"]:
            self.assertTrue(item["control_metadata_only"])
            self.assertFalse(item["source_content_retained"])
            self.assertFalse(item["sent_to_external_api"])
            for field in (
                "policy_resolution_ref",
                "embedding_queue_request_ref",
                "cache_entry_ref",
                "retry_ref",
                "external_api_audit_ref",
            ):
                self.assertIn(":control:stage075-p2:", item[field])
        for item in report["control_audit_log_samples"]:
            self.assertEqual(
                set(self.module.CONTROL_AUDIT_PROJECTION_FIELDS),
                set(item["audit_projection"]),
            )
            self.assertTrue(item["audit_reference_fields_are_control_only"])
            self.assertEqual(0, item["audit_projection"]["token_count"])
            self.assertEqual(0, item["audit_projection"]["cost_estimate"])
        owner = report["owner_forced_egress_override_precondition_sample"]
        self.assertEqual(
            set(self.module.OWNER_FORCED_EGRESS_OVERRIDE_FIELDS),
            set(owner["precondition_projection"]),
        )
        self.assertTrue(owner["precondition_complete_before_future_policy_change"])
        self.assertTrue(owner["business_line_whitebox_human_review_required"])
        self.assertFalse(owner["actual_override_audit_record_created"])
        self.assertFalse(owner["actual_policy_override_applied"])
        self.assertTrue(all(item["failure_closed"] for item in report["failure_handling_results"]))
        self.assertTrue(
            all(
                not item["externalization_performed"]
                for item in report["non_externalized_data_records"]
            )
        )

    def test_cost_query_rollback_and_runtime_stay_closed(self):
        report = self.report()
        self.assertTrue(
            all(
                item["estimated_token_count"] == 0 and item["estimated_cost"] == 0
                for item in report["cost_estimate_samples"]
            )
        )
        self.assertEqual(
            8,
            len(report["externalization_record_query_instructions"]["supported_query_keys"]),
        )
        self.assertFalse(
            report["externalization_record_query_instructions"][
                "persistent_audit_log_available"
            ]
        )
        self.assertEqual(
            self.module.P3_PASS_RESULT,
            report["policy_rollback_instructions"]["rollback_target_result"],
        )
        self.assertEqual(
            self.module.ENTRY_GATE,
            report["policy_rollback_instructions"]["rollback_target_gate"],
        )
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertTrue(report["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(report["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(report["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(report["owner_override_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            self.assertFalse(report[field], field)
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_invalid_predecessors_fail_closed(self):
        invalid = self.module.build_external_api_coverage_audit_phase4_delivery_report(
            phase3_report_provider=lambda: {"valid": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(0, invalid["policy_sample_count"])

        def malformed_p2():
            report = copy.deepcopy(
                self.p2.execute_external_api_coverage_audit_control_slice(
                    self.p2.build_control_input()
                )
            )
            report["external_api_coverage_audit_projections"][0].pop("provider_ref")
            return report

        malformed = self.module.build_external_api_coverage_audit_phase4_delivery_report(
            phase2_report_provider=malformed_p2
        )
        self.assertFalse(malformed["valid"])
        self.assertEqual(0, malformed["control_audit_log_sample_count"])

    def test_machine_and_governance_projection_match_p4(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE075-P4",
                    "IDS-V0_1-STAGE075-P4",
                    "IDS-STAGE075-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE075-REVIEW",
                    "IDS-V0_1-STAGE075-REVIEW",
                    "IDS-STAGE076-P1-GATE",
                ),
                ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
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
                ("IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE")),
        )
        self.assertIn(
            plan["task"],
            ("IDS-V0_1-STAGE075-P4", "IDS-V0_1-STAGE075-REVIEW", 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW',
                'IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW", "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW"),
        )
        self.assertIn(
            acceptance["task"],
            ("IDS-V0_1-STAGE075-P4", "IDS-V0_1-STAGE075-REVIEW", 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
            'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW", "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',
                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW"),
        )
        self.assertTrue(
            {
                "ACC-STAGE-075",
                "ACC-STAGE075-P4-01",
                "ACC-STAGE075-P4-02",
                "ACC-STAGE075-P4-03",
                "ACC-STAGE075-P4-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertTrue(
            'current_phase_id: "IDS-STAGE075-P4"' in roadmap
            or 'current_phase_id: "IDS-STAGE076-P3"' in roadmap
            or 'current_phase_id: "IDS-STAGE079-P1"' in roadmap
            or 'current_phase_id: "IDS-STAGE080-P2"' in roadmap
            or 'current_phase_id: "IDS-STAGE080-P3"' in roadmap
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE075-P4"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE076-P3"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE079-P1"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE080-P2"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE080-P3"' in roadmap
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE075-REVIEW-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE076-P4-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE079-P2-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE080-P3-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE080-P4-GATE"' in roadmap
        )
        self.assertIn("EVT-IDS-V0_1-STAGE075-P4-20260821-001", event_ids)
        self.assertTrue(RUN.is_file())


if __name__ == "__main__":
    unittest.main()
