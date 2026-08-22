import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE073_PHASE1_EMBEDDING_AUDIT_TEST_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-073_Embedding审计测试.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE072_STAGE_REVIEW.md"
PREDECESSOR_MODEL_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_contract.json"
)
PREDECESSOR_AUDIT_CONTRACT = (
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
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage073-p1-local.json"


class Stage073EmbeddingAuditTestPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.model_contract = json.loads(
            PREDECESSOR_MODEL_CONTRACT.read_text(encoding="utf-8")
        )
        cls.audit_contract = json.loads(
            PREDECESSOR_AUDIT_CONTRACT.read_text(encoding="utf-8")
        )

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_MODEL_CONTRACT,
            PREDECESSOR_AUDIT_CONTRACT,
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

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage073.embedding_audit_test.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-073", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE073-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-073", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EMBEDDING_AUDIT_TEST_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE073-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE073_TASKPACK_STAGE072_REVIEW_AND_PREDECESSOR_CONTROL_CONTRACTS_ONLY",
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

    def test_policy_inheritance_is_default_denied_and_owner_needs_no_chunk_tags(self):
        policy = self.contract["policy_inheritance_contract"]
        predecessor = self.model_contract["policy_inheritance_dependency"]
        self.assertEqual("denied", policy["default_external_api_policy"])
        self.assertEqual(
            predecessor["allowed_external_api_policy_values"],
            policy["allowed_external_api_policy_values"],
        )
        self.assertEqual(
            predecessor["inheritance_path"], policy["inheritance_path"]
        )
        self.assertEqual(2, policy["inheritance_hop_count"])
        self.assertTrue(policy["owner_must_not_mark_chunks_individually"])
        self.assertFalse(policy["chunk_manual_policy_assignment_allowed"])
        self.assertFalse(policy["document_may_widen_data_source_policy"])
        self.assertTrue(policy["chunk_inherits_effective_document_policy_automatically"])
        self.assertFalse(policy["actual_policy_resolution_performed"])

    def test_queue_cost_model_and_complete_audit_shape_are_static(self):
        dependency = self.contract["embedding_queue_cost_model_audit_contract"]
        predecessor_dependency = self.model_contract[
            "queue_cost_and_audit_dependency"
        ]
        self.assertEqual(
            predecessor_dependency["future_queue_field_count"],
            dependency["future_embedding_queue_field_count"],
        )
        self.assertEqual(
            predecessor_dependency["future_cost_and_model_field_count"],
            dependency["future_cost_and_model_field_count"],
        )
        self.assertEqual(6, dependency["future_model_version_field_count"])
        self.assertEqual(
            predecessor_dependency["future_external_api_audit_field_count"],
            dependency["future_external_api_audit_field_count"],
        )
        for field in (
            "embedding_queue_execution_allowed_in_phase1",
            "cost_estimation_or_budget_lookup_allowed_in_phase1",
            "model_version_record_creation_allowed_in_phase1",
            "audit_record_creation_allowed_in_phase1",
            "actual_embedding_queue_created",
            "actual_cost_estimation_performed",
            "actual_budget_lookup_performed",
            "actual_model_version_record_created",
            "actual_audit_record_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(dependency[field])

        audit = self.contract["future_external_api_audit_contract"]
        predecessor_audit = self.audit_contract[
            "future_external_api_audit_dependency"
        ]
        self.assertEqual(predecessor_audit["required_fields"], audit["required_fields"])
        self.assertEqual(18, audit["field_count"])
        self.assertFalse(audit["additional_fields_allowed"])
        self.assertTrue(audit["complete_before_future_provider_call"])
        self.assertFalse(audit["actual_audit_log_created"])
        self.assertFalse(audit["actual_audit_log_query_performed"])

    def test_policy_flows_and_failures_fail_closed(self):
        flows = self.contract["policy_flow_contract"]
        denied = flows["denied"]
        for field in (
            "external_payload_allowed",
            "embedding_queue_allowed",
            "provider_call_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(denied[field])
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            flows["summary_only"]["external_payload_allowed"],
        )
        self.assertFalse(flows["summary_only"]["chunk_text_payload_allowed"])
        self.assertEqual(
            "FUTURE_AUTHORIZED_CHUNK_TEXT_ONLY",
            flows["full_text_allowed"]["external_payload_allowed"],
        )
        self.assertFalse(flows["actual_summary_created"])
        self.assertFalse(flows["actual_chunk_text_externalized"])
        self.assertFalse(flows["actual_external_api_call_performed"])
        self.assertEqual(0, flows["actual_policy_test_execution_count"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(7, failures["failure_state_count"])
        self.assertIn(
            "EMBEDDING_AUDIT_UNAUTHORIZED_CHUNK_EXTERNALIZATION",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "PHASE1_EMBEDDING_AUDIT_TEST_EXECUTION_NOT_AUTHORIZED",
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
            "stage072_review_evidence_read",
            "stage073_started",
            "stage073_entry_authorized",
            "phase1_started",
            "stage073_phase2_entry_authorized",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage074_started",
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
            "LOCAL_STAGE072_REVIEWED_EMBEDDING_MODEL_VERSION_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage072_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_governance_projection_preserves_phase1_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        batch_text = BATCH.read_text(encoding="utf-8")
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE073",
                    "IDS-V0_1-STAGE073-P1",
                    "IDS-V0_1-STAGE073-P1",
                    "IDS-STAGE073-P2-GATE",
                ),
                (
                    "IDS-STAGE073",
                    "IDS-V0_1-STAGE073-P2",
                    "IDS-V0_1-STAGE073-P2",
                    "IDS-STAGE073-P3-GATE",
                ),
                (
                    "IDS-STAGE073",
                    "IDS-V0_1-STAGE073-P3",
                    "IDS-V0_1-STAGE073-P3",
                    "IDS-STAGE073-P4-GATE",
                ),
                (
                    "IDS-STAGE073",
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-STAGE073-REVIEW-GATE",
                ),
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

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-V0_1-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P2", "IDS-V0_1-STAGE084-P2", "IDS-STAGE084-P3-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-V0_1-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-V0_1-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-V0_1-STAGE084-REVIEW', 'IDS-STAGE085-P3-GATE'),

                ('IDS-STAGE085', 'IDS-STAGE085-P2', 'IDS-V0_1-STAGE085-P2', 'IDS-STAGE085-P3-GATE'), ("IDS-STAGE085", "IDS-STAGE085-P3", "IDS-V0_1-STAGE085-P3", "IDS-STAGE085-P4-GATE"), ("IDS-STAGE085", "IDS-STAGE085-P4", "IDS-V0_1-STAGE085-P4", "IDS-STAGE085-REVIEW-GATE"), ("IDS-STAGE085", "IDS-STAGE085-REVIEW", "IDS-V0_1-STAGE085-REVIEW", "IDS-STAGE086-P1-GATE"), ("IDS-STAGE086", "IDS-STAGE086-P1", "IDS-V0_1-STAGE086-P1", "IDS-STAGE086-P2-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE073-P1",
                "IDS-V0_1-STAGE073-P2",
                "IDS-V0_1-STAGE073-P3",
                "IDS-V0_1-STAGE073-P4",
                "IDS-V0_1-STAGE073-REVIEW",
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
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                    'IDS-V0_1-STAGE084-REVIEW',

                'IDS-V0_1-STAGE085-P2',
             "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW", "IDS-V0_1-STAGE086-P1"),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE073-P1-01",
                "ACC-STAGE073-P1-02",
                "ACC-STAGE073-P1-03",
                "ACC-STAGE073-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE073-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_call_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_audit_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertTrue(
            'current_stage_id: "IDS-STAGE073"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE074"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE073-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P2"' in roadmap_text or 'current_task_id: "IDS-V0_1-STAGE074-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap_text
        )
        self.assertIn("stage070_completed_reviewed_local", batch_text)
        self.assertIn("EVT-IDS-V0_1-STAGE073-P1-20260820-001", event_ids)

    def test_scope_document_explains_zero_runtime_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "external_api_policy=denied",
            "不创建或执行 Embedding 队列",
            "IDS-STAGE073-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
