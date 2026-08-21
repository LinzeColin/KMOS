import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE075_PHASE1_EXTERNAL_API_COVERAGE_AUDIT_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "external_api_coverage_audit"
    / "stage075_external_api_coverage_audit_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-075_外部API覆盖授权审计.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE074_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "local_embedding_fallback"
    / "stage074_local_embedding_fallback_contract.json"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage075-p1-local.json"


class Stage075ExternalApiCoverageAuditPhase1Tests(unittest.TestCase):
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
            "ids.stage075.external_api_coverage_audit.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-075", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE075-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-075", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EXTERNAL_API_COVERAGE_AUDIT_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE075-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE075_TASKPACK_STAGE074_REVIEW_AND_PREDECESSOR_CONTROL_CONTRACTS_ONLY",
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

    def test_default_policy_and_automatic_inheritance_are_reused(self):
        policy = self.contract["policy_inheritance_contract"]
        predecessor = self.predecessor["policy_inheritance_contract"]
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

    def test_coverage_and_owner_override_audit_shapes_are_static(self):
        runtime = self.contract["future_runtime_shape_contract"]
        self.assertEqual(12, runtime["future_embedding_queue_field_count"])
        self.assertEqual(10, runtime["future_cache_field_count"])
        self.assertEqual(7, runtime["future_failed_retry_field_count"])
        self.assertEqual(16, runtime["future_cost_governor_field_count"])
        self.assertEqual(8, runtime["future_cost_and_model_field_count"])
        self.assertEqual(6, runtime["future_model_version_field_count"])
        for field, value in runtime.items():
            if field.endswith("_allowed_in_phase1") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        audit = self.contract["future_external_api_coverage_audit_contract"]
        self.assertEqual(19, audit["field_count"])
        self.assertEqual(audit["field_count"], len(audit["required_fields"]))
        self.assertIn("chunk_id", audit["required_fields"])
        self.assertIn("owner_forced_egress_override_audit_ref", audit["required_fields"])
        self.assertFalse(audit["additional_fields_allowed"])
        self.assertTrue(audit["complete_before_future_provider_call"])
        self.assertFalse(audit["actual_audit_log_created"])
        self.assertFalse(audit["actual_audit_log_query_performed"])

        override = self.contract["owner_forced_egress_override_audit_contract"]
        self.assertEqual(
            ["actor", "reason", "old_value", "new_value"],
            override["required_fields"],
        )
        self.assertEqual(4, override["field_count"])
        self.assertTrue(override["business_line_whitebox_human_review_required"])
        self.assertTrue(override["complete_audit_required_before_future_policy_change"])
        for field in (
            "override_may_change_effective_policy_in_phase1",
            "actual_actor_recorded",
            "actual_override_requested",
            "actual_override_audit_record_created",
            "actual_policy_override_applied",
        ):
            with self.subTest(field=field):
                self.assertFalse(override[field])

    def test_policy_flows_fail_closed_and_no_runtime_test_is_claimed(self):
        flows = self.contract["policy_flow_contract"]
        self.assertFalse(flows["denied"]["external_payload_allowed"])
        self.assertFalse(flows["denied"]["embedding_queue_allowed"])
        self.assertFalse(flows["denied"]["provider_call_allowed"])
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            flows["summary_only"]["external_payload_allowed"],
        )
        self.assertFalse(flows["summary_only"]["chunk_text_payload_allowed"])
        self.assertFalse(flows["summary_only"]["provider_call_allowed"])
        self.assertEqual(
            "FUTURE_AUTHORIZED_CHUNK_TEXT_ONLY",
            flows["full_text_allowed"]["external_payload_allowed"],
        )
        self.assertFalse(flows["full_text_allowed"]["provider_call_allowed"])
        self.assertEqual(0, flows["actual_policy_test_execution_count"])
        for field in (
            "actual_summary_created",
            "actual_chunk_text_externalized",
            "actual_external_api_call_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(flows[field])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        self.assertIn(
            "OWNER_FORCED_EGRESS_AUDIT_FIELDS_INCOMPLETE",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "PHASE1_EXTERNAL_API_EXECUTION_NOT_AUTHORIZED",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_runtime_phase_and_rollback_boundaries_remain_zero(self):
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage074_review_evidence_read",
            "stage075_started",
            "stage075_entry_authorized",
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
            "stage076_started",
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
            "LOCAL_STAGE074_REVIEWED_LOCAL_EMBEDDING_FALLBACK_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage074_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_scope_taskpack_and_governance_projection_preserve_phase1_evidence(self):
        scope_text = SCOPE.read_text(encoding="utf-8")
        taskpack_text = TASKPACK.read_text(encoding="utf-8")
        for expected in (
            "actor`、`reason`、`old_value`、`new_value`",
            "IDS-STAGE075-P2-GATE",
            "不建立第二权威事实源",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, scope_text)
        self.assertIn("actor、reason、old_value、new_value", taskpack_text)

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
                    "IDS-STAGE075",
                    "IDS-V0_1-STAGE075-P1",
                    "IDS-V0_1-STAGE075-P1",
                    "IDS-STAGE075-P2-GATE",
                ),
                (
                    "IDS-STAGE075",
                    "IDS-V0_1-STAGE075-P2",
                    "IDS-V0_1-STAGE075-P2",
                    "IDS-STAGE075-P3-GATE",
                ),
                (
                    "IDS-STAGE075",
                    "IDS-V0_1-STAGE075-P3",
                    "IDS-V0_1-STAGE075-P3",
                    "IDS-STAGE075-P4-GATE",
                ),
                (
                    "IDS-STAGE075",
                    "IDS-V0_1-STAGE075-P4",
                    "IDS-V0_1-STAGE075-P4",
                    "IDS-STAGE075-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE075",
                    "IDS-V0_1-STAGE075-REVIEW",
                    "IDS-V0_1-STAGE075-REVIEW",
                    "IDS-STAGE076-P1-GATE",
                ),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
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
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE075-P1",
                "IDS-V0_1-STAGE075-P2",
                "IDS-V0_1-STAGE075-P3",
                "IDS-V0_1-STAGE075-P4",
                "IDS-V0_1-STAGE075-REVIEW",
                'IDS-V0_1-STAGE076-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
            , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4'),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE075-P1-01",
                "ACC-STAGE075-P1-02",
                "ACC-STAGE075-P1-03",
                "ACC-STAGE075-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE075-P1", run["task_id"])
        self.assertEqual("IDS-STAGE075-P2-GATE", run["next_gate"])
        self.assertFalse(run["runtime_actions"]["external_api_call_performed"])
        self.assertFalse(run["runtime_actions"]["model_token_consumption_performed"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertIn("EVT-IDS-V0_1-STAGE075-P1-20260821-001", event_ids)
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            (
                'current_stage_id: "IDS-STAGE075"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE075-P1"' in roadmap_text
                and 'current_task_id: "IDS-V0_1-STAGE075-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE075-P2-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE075"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE075-P2"' in roadmap_text
                and 'current_task_id: "IDS-V0_1-STAGE075-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE075-P3-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE075"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE075-P3"' in roadmap_text
                and 'current_task_id: "IDS-V0_1-STAGE075-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE075-P4-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE075"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE075-P4"' in roadmap_text
                and 'current_task_id: "IDS-V0_1-STAGE075-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE075-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE075"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE075-REVIEW"' in roadmap_text
                and 'current_task_id: "IDS-V0_1-STAGE075-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE076-P1-GATE"' in roadmap_text
            )
        )


if __name__ == "__main__":
    unittest.main()
