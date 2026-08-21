import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT = BASE / "local_embedding_fallback/stage074_local_embedding_fallback_delivery_contract.json"
DELIVERY = BASE / "local_embedding_fallback/stage074_local_embedding_fallback_delivery.py"
P2 = BASE / "local_embedding_fallback/stage074_local_embedding_fallback_slice.py"
STATUS = ROOT / "machine/facts/status.json"
PLAN = ROOT / "machine/facts/plan.json"
ACCEPTANCE = ROOT / "machine/facts/acceptance.json"
ROADMAP = ROOT / "docs/governance/roadmap.yaml"
EVENTS = ROOT / "docs/governance/events.jsonl"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Stage074LocalEmbeddingFallbackPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load("stage074_p4", DELIVERY)
        cls.p2 = _load("stage074_p2", P2)

    def report(self):
        return self.module.build_local_embedding_fallback_phase4_delivery_report()

    def test_contract_scope_and_counts(self):
        c = self.contract
        self.assertEqual("ids.stage074.local_embedding_fallback.phase4.delivery.v1", c["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE074-P4", c["task_id"])
        self.assertEqual("PHASE4_LOCAL_EMBEDDING_FALLBACK_DELIVERY_EVIDENCE_RUNTIME_DISABLED", c["contract_state"])
        self.assertTrue(c["delivery_executable"])
        self.assertFalse(c["execution_ready"])
        self.assertEqual(("IDS-STAGE074-P4-GATE", "IDS-STAGE074-REVIEW-GATE"), (c["entry_gate"], c["next_gate"]))
        self.assertFalse(c["source_authority"]["second_authoritative_source_created"])
        self.assertFalse(c["source_authority"]["source_body_or_path_allowed"])
        self.assertEqual(35, c["phase3_controlled_scenario_replay_contract"]["scenario_field_count"])
        self.assertEqual(90, c["delivery_evidence_contract"]["control_audit_field_check_count"])
        self.assertEqual(12, c["failure_and_stop_contract"]["failure_state_count"])

    def test_delivery_samples_and_audits_are_control_only(self):
        r = self.report()
        self.assertTrue(r["valid"], r)
        self.assertEqual((self.module.PASS_RESULT, self.module.NEXT_GATE), (r["result"], r["next_gate"]))
        self.assertEqual((5, 5, 18, 90, 5, 5, 5), (
            r["policy_sample_count"], r["control_audit_log_sample_count"], r["control_audit_field_count"],
            r["control_audit_field_check_count"], r["zero_cost_estimate_sample_count"],
            r["failure_handling_result_count"], r["non_externalized_data_record_count"],
        ))
        self.assertEqual((3, 1, 1, 4), (
            r["future_external_api_call_candidate_count"], r["policy_denied_sample_count"],
            r["budget_pause_sample_count"], r["human_handling_required_count"],
        ))
        for p in r["local_embedding_fallback_policy_samples"]:
            self.assertTrue(p["control_metadata_only"])
            self.assertFalse(p["source_content_retained"])
            self.assertFalse(p["sent_to_external_api"])
            for key in ("policy_resolution_ref", "embedding_queue_request_ref", "cache_entry_ref", "retry_ref", "external_api_audit_ref"):
                self.assertIn(":control:stage074-p2:", p[key])
        for a in r["control_audit_log_samples"]:
            self.assertEqual(set(self.module.CONTROL_AUDIT_PROJECTION_FIELDS), set(a["audit_projection"]))
            self.assertTrue(a["audit_reference_fields_are_control_only"])
        self.assertTrue(all(x["failure_closed"] for x in r["failure_handling_results"]))
        self.assertTrue(all(not x["externalization_performed"] for x in r["non_externalized_data_records"]))

    def test_cost_query_rollback_and_runtime_stay_closed(self):
        r = self.report()
        self.assertTrue(all(x["estimated_token_count"] == 0 and x["estimated_cost"] == 0 for x in r["cost_estimate_samples"]))
        self.assertEqual(7, len(r["externalization_record_query_instructions"]["supported_query_keys"]))
        self.assertFalse(r["externalization_record_query_instructions"]["persistent_audit_log_available"])
        self.assertEqual(self.module.P3_PASS_RESULT, r["policy_rollback_instructions"]["rollback_target_result"])
        self.assertEqual(self.module.ENTRY_GATE, r["policy_rollback_instructions"]["rollback_target_gate"])
        self.assertEqual(4, len(r["chinese_feedback"]))
        self.assertTrue(r["source_document_remains_authoritative"])
        self.assertTrue(r["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(r["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(r["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(r["automatic_business_recommendation_allowed"])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            self.assertFalse(r[field], field)
        encoded = json.dumps(r, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_invalid_predecessors_fail_closed(self):
        invalid = self.module.build_local_embedding_fallback_phase4_delivery_report(phase3_report_provider=lambda: {"valid": False})
        self.assertFalse(invalid["valid"])
        self.assertEqual(0, invalid["policy_sample_count"])
        def malformed_p2():
            r = copy.deepcopy(self.p2.execute_local_embedding_fallback_control_slice(self.p2.build_control_input()))
            r["external_api_audit_projections"][0].pop("provider_ref")
            return r
        malformed = self.module.build_local_embedding_fallback_phase4_delivery_report(phase2_report_provider=malformed_p2)
        self.assertFalse(malformed["valid"])
        self.assertEqual(0, malformed["control_audit_log_sample_count"])

    def test_machine_and_governance_projection_match_p4(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {json.loads(line)["event_id"] for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()}
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
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

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE')),
        )
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                        "IDS-V0_1-STAGE079-P1",
                                        "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                            'IDS-V0_1-STAGE079-REVIEW',

                                        'IDS-V0_1-STAGE080-P1'))
        self.assertIn(acceptance["task"], ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
            'IDS-V0_1-STAGE076-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
        'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
        , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                                              "IDS-V0_1-STAGE079-P1",
                                              "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                                                  'IDS-V0_1-STAGE079-REVIEW',

                                              'IDS-V0_1-STAGE080-P1',))
        self.assertTrue({"ACC-STAGE-074", "ACC-STAGE074-P4-01", "ACC-STAGE074-P4-02", "ACC-STAGE074-P4-03", "ACC-STAGE074-P4-04"}.issubset({x["id"] for x in acceptance["items"]}))
        self.assertTrue(
            'current_phase_id: "IDS-STAGE074-P4"' in roadmap
            or 'current_phase_id: "IDS-STAGE074-REVIEW"' in roadmap
            or 'current_phase_id: "IDS-STAGE075-P2"' in roadmap
            or 'current_phase_id: "IDS-STAGE079-P1"' in roadmap
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE075-P2"' in roadmap
            or 'current_task_id: "IDS-V0_1-STAGE079-P1"' in roadmap
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE074-REVIEW-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE075-P1-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE075-P3-GATE"' in roadmap
            or 'next_gate_id: "IDS-STAGE079-P2-GATE"' in roadmap
        )
        self.assertIn("EVT-IDS-V0_1-STAGE074-P4-20260821-001", event_ids)

if __name__ == "__main__":
    unittest.main()
