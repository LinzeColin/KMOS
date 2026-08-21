import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE074_PHASE1_LOCAL_EMBEDDING_FALLBACK_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "local_embedding_fallback"
    / "stage074_local_embedding_fallback_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-074_本地Embedding兜底合同.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE073_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_contract.json"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage074-p1-local.json"


class Stage074LocalEmbeddingFallbackPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.predecessor = json.loads(PREDECESSOR_CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage074.local_embedding_fallback.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-074", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE074-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-074", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_LOCAL_EMBEDDING_FALLBACK_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE074-P2-GATE", contract["next_gate"])
        self.assertEqual(
            "FROZEN_STAGE074_TASKPACK_STAGE073_REVIEW_AND_PREDECESSOR_CONTROL_CONTRACTS_ONLY",
            contract["source_authority"]["authority"],
        )
        for field, value in contract["source_authority"].items():
            if field != "authority":
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_policy_inheritance_and_local_fallback_remain_static(self):
        policy = self.contract["policy_inheritance_contract"]
        predecessor_policy = self.predecessor["policy_inheritance_contract"]
        self.assertEqual("denied", policy["default_external_api_policy"])
        self.assertEqual(
            predecessor_policy["allowed_external_api_policy_values"],
            policy["allowed_external_api_policy_values"],
        )
        self.assertEqual(
            predecessor_policy["inheritance_path"], policy["inheritance_path"]
        )
        self.assertEqual(2, policy["inheritance_hop_count"])
        self.assertTrue(policy["owner_must_not_mark_chunks_individually"])
        self.assertFalse(policy["chunk_manual_policy_assignment_allowed"])
        self.assertFalse(policy["document_may_widen_data_source_policy"])
        self.assertTrue(policy["chunk_inherits_effective_document_policy_automatically"])
        fallback = self.contract["local_embedding_fallback_contract"]
        self.assertTrue(fallback["fallback_activation_requires_future_phase2_and_authorized_runtime"])
        self.assertTrue(fallback["local_route_is_not_external_api_egress"])
        for field in (
            "local_provider_or_model_selection_allowed_in_phase1",
            "local_embedding_execution_allowed_in_phase1",
            "actual_local_provider_selected",
            "actual_local_model_selected",
            "actual_local_embedding_execution_performed",
            "actual_local_embedding_or_index_written",
        ):
            with self.subTest(field=field):
                self.assertFalse(fallback[field])

    def test_queue_cost_model_and_audit_shapes_are_reused_without_runtime(self):
        dependency = self.contract["embedding_queue_cost_model_audit_contract"]
        self.assertEqual(12, dependency["future_embedding_queue_field_count"])
        self.assertEqual(10, dependency["future_cache_field_count"])
        self.assertEqual(7, dependency["future_failed_retry_field_count"])
        self.assertEqual(16, dependency["future_cost_governor_field_count"])
        self.assertEqual(8, dependency["future_cost_and_model_field_count"])
        self.assertEqual(6, dependency["future_model_version_field_count"])
        self.assertEqual(18, dependency["future_external_api_audit_field_count"])
        for field, value in dependency.items():
            if field.endswith("_allowed_in_phase1") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        audit = self.contract["future_external_api_audit_contract"]
        self.assertEqual(18, audit["field_count"])
        self.assertEqual(audit["field_count"], len(audit["required_fields"]))
        self.assertFalse(audit["additional_fields_allowed"])
        self.assertTrue(audit["complete_before_future_provider_call"])
        self.assertFalse(audit["actual_audit_log_created"])
        self.assertFalse(audit["actual_audit_log_query_performed"])

    def test_policy_flows_and_stop_conditions_fail_closed(self):
        flows = self.contract["policy_flow_contract"]
        self.assertFalse(flows["denied"]["external_payload_allowed"])
        self.assertFalse(flows["denied"]["embedding_queue_allowed"])
        self.assertFalse(flows["denied"]["provider_call_allowed"])
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            flows["summary_only"]["external_payload_allowed"],
        )
        self.assertFalse(flows["summary_only"]["chunk_text_payload_allowed"])
        self.assertEqual(
            "FUTURE_AUTHORIZED_CHUNK_TEXT_ONLY",
            flows["full_text_allowed"]["external_payload_allowed"],
        )
        self.assertEqual(0, flows["actual_policy_test_execution_count"])
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        self.assertIn(
            "LOCAL_EMBEDDING_FALLBACK_UNAUTHORIZED_CHUNK_EGRESS",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "PHASE1_LOCAL_EMBEDDING_EXECUTION_NOT_AUTHORIZED",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_runtime_and_rollback_boundaries_remain_zero(self):
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage073_review_evidence_read",
            "stage074_started",
            "stage074_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage075_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        for field, value in self.contract["protected_surface_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "LOCAL_STAGE073_REVIEWED_EMBEDDING_AUDIT_TEST_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage073_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_governance_projection_preserves_phase1_evidence(self):
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

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE074-P1",
                "IDS-V0_1-STAGE074-P2",
                "IDS-V0_1-STAGE074-P3",
                "IDS-V0_1-STAGE074-P4",
                "IDS-V0_1-STAGE074-REVIEW",
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
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2'),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE074-P1-01",
                "ACC-STAGE074-P1-02",
                "ACC-STAGE074-P1-03",
                "ACC-STAGE074-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE074-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_local_embedding_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_call_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE074"', roadmap_text)
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE074-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap_text
        )
        self.assertIn("EVT-IDS-V0_1-STAGE074-P1-20260821-001", event_ids)

    def test_scope_document_explains_zero_runtime_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "external_api_policy=denied",
            "不选择或下载本地 provider/模型",
            "IDS-STAGE074-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
