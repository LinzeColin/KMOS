import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE069_PHASE1_EXTERNAL_API_POLICY_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "external_api_policy"
    / "stage069_external_api_policy_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-069_外部API策略继承.md"
)
GUIDE = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "guides"
    / "external_api_policy操作流程说明.md"
)
ROOT_LOCK = BASE / "V0_1_ROOT_LOCK.yaml"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage069-p1-local.json"


class Stage069ExternalApiPolicyPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            GUIDE,
            ROOT_LOCK,
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
            "ids.stage069.external_api_policy.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-069", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE069-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-069", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EXTERNAL_API_POLICY_INHERITANCE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE069-P2-GATE", contract["next_gate"])

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE069_TASKPACK_STAGE068_REVIEW_ROOT_LOCK_AND_POLICY_GUIDE_ONLY",
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

    def test_default_policy_and_inheritance_are_closed_and_automatic(self):
        values = self.contract["policy_value_contract"]
        self.assertEqual("denied", values["default_external_api_policy"])
        self.assertEqual(
            ["denied", "summary_only", "full_text_allowed"],
            values["allowed_external_api_policy_values"],
        )
        self.assertEqual(3, values["allowed_value_count"])
        self.assertEqual("denied", values["unknown_policy_fails_closed_to"])
        self.assertTrue(values["owner_must_not_mark_chunks_individually"])
        self.assertFalse(values["chunk_manual_policy_assignment_allowed"])
        self.assertFalse(values["actual_policy_assignment_created"])

        inheritance = self.contract["policy_inheritance_contract"]
        self.assertEqual(
            [
                "data_source.external_api_policy",
                "document.effective_external_api_policy",
                "chunk.effective_external_api_policy",
            ],
            inheritance["inheritance_path"],
        )
        self.assertEqual(2, inheritance["inheritance_hop_count"])
        self.assertTrue(inheritance["document_inherits_data_source_policy_by_default"])
        self.assertTrue(inheritance["document_may_request_more_restrictive_policy"])
        self.assertFalse(inheritance["document_may_widen_data_source_policy"])
        self.assertTrue(inheritance["more_permissive_document_policy_fails_closed"])
        self.assertTrue(inheritance["chunk_inherits_effective_document_policy_automatically"])
        self.assertFalse(inheritance["chunk_policy_override_allowed"])
        self.assertEqual(
            "MOST_RESTRICTIVE_AUTHORIZED_SOURCE_DOCUMENT_POLICY",
            inheritance["effective_policy_resolution"],
        )
        for field in (
            "actual_data_source_policy_read",
            "actual_document_policy_resolved",
            "actual_chunk_policy_assigned",
        ):
            with self.subTest(field=field):
                self.assertFalse(inheritance[field])

    def test_reference_only_shapes_and_future_queue_cost_audit_are_static(self):
        inputs = self.contract["reference_only_policy_input_contract"]
        self.assertEqual(15, inputs["field_count"])
        self.assertFalse(inputs["additional_fields_allowed"])
        self.assertFalse(inputs["source_or_document_body_allowed"])
        self.assertFalse(inputs["summary_body_allowed"])
        self.assertFalse(inputs["chunk_text_allowed"])
        self.assertFalse(inputs["physical_path_or_actual_uri_allowed"])
        self.assertEqual(0, inputs["actual_input_request_count"])

        outputs = self.contract["future_policy_output_contract"]
        self.assertEqual(23, outputs["field_count"])
        self.assertTrue(outputs["schema_field_labels_only"])
        for field in (
            "actual_policy_resolution_record_created",
            "actual_embedding_queue_request_created",
            "actual_external_api_audit_record_created",
            "actual_provider_or_model_selected",
            "actual_token_count_recorded",
            "actual_cost_recorded",
        ):
            with self.subTest(field=field):
                self.assertFalse(outputs[field])

        queue = self.contract["future_embedding_queue_contract"]
        self.assertEqual(12, queue["field_count"])
        self.assertTrue(queue["queue_creation_requires_effective_policy_not_denied"])
        self.assertTrue(queue["queue_creation_requires_authorization_budget_and_audit"])
        self.assertFalse(queue["queue_creation_allowed_in_phase1"])
        self.assertFalse(queue["actual_embedding_queue_created"])
        self.assertFalse(queue["actual_cache_read_or_write_performed"])

        cost = self.contract["future_cost_and_model_contract"]
        self.assertEqual(8, cost["field_count"])
        self.assertTrue(cost["budget_unknown_fails_closed"])
        self.assertTrue(cost["budget_insufficient_pauses_future_external_api_task"])
        self.assertFalse(cost["provider_and_model_selection_allowed_in_phase1"])
        self.assertFalse(cost["actual_budget_checked"])
        self.assertEqual(0, cost["actual_token_count"])
        self.assertEqual(0, cost["actual_cost"])
        self.assertFalse(cost["actual_model_version_recorded"])

        audit = self.contract["future_external_api_audit_contract"]
        self.assertEqual(18, audit["field_count"])
        self.assertTrue(audit["audit_required_before_future_provider_call"])
        self.assertFalse(audit["audit_record_creation_allowed_in_phase1"])
        self.assertFalse(audit["actual_audit_record_created"])

    def test_three_policy_flows_and_decision_boundary_fail_closed(self):
        flows = self.contract["policy_flow_contract"]
        denied = flows["denied"]
        self.assertFalse(denied["external_payload_allowed"])
        self.assertFalse(denied["summary_payload_allowed"])
        self.assertFalse(denied["chunk_text_payload_allowed"])
        self.assertFalse(denied["embedding_queue_allowed"])
        self.assertFalse(denied["provider_call_allowed"])

        summary_only = flows["summary_only"]
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            summary_only["external_payload_allowed"],
        )
        self.assertFalse(summary_only["chunk_text_payload_allowed"])
        self.assertFalse(summary_only["provider_call_allowed"])

        full_text = flows["full_text_allowed"]
        self.assertEqual(
            "FUTURE_AUTHORIZED_CHUNK_TEXT_ONLY",
            full_text["external_payload_allowed"],
        )
        self.assertFalse(full_text["provider_call_allowed"])
        for field in (
            "actual_summary_created",
            "actual_chunk_text_externalized",
            "actual_external_api_call_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(flows[field])

        authority = self.contract["authority_and_decision_boundary"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        for field in (
            "external_api_policy_can_replace_source_document",
            "policy_resolution_can_become_business_fact_authority",
            "external_model_output_can_become_business_fact_authority",
            "model_direct_text_guessing_allowed",
            "automatic_business_recommendation_allowed",
            "actual_business_decision_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(13, failures["failure_state_count"])
        self.assertIn("SOURCE_POLICY_DENIED_BLOCKS_EXTERNALIZATION", failures["declared_failure_states"])
        self.assertIn("PHASE1_EXTERNAL_API_EXECUTION_NOT_AUTHORIZED", failures["declared_failure_states"])
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

    def test_runtime_phase_and_rollback_boundaries_remain_zero(self):
        runtime = self.contract["runtime_boundary"]
        self.assertTrue(runtime)
        for field, value in runtime.items():
            with self.subTest(field=field):
                self.assertFalse(value)

        boundary = self.contract["stage_and_phase_boundary"]
        self.assertTrue(boundary["stage069_started"])
        self.assertTrue(boundary["stage069_entry_authorized"])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage070_started",
            "stage070_entry_allowed",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

        protected = self.contract["protected_surface_boundary"]
        for field, value in protected.items():
            with self.subTest(field=field):
                self.assertFalse(value)

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "STAGE068_REVIEWED_LOCAL_QUALITY_DEGRADATION_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage068_review_evidence"])
        self.assertFalse(rollback["source_or_raw_data_change_allowed"])
        self.assertFalse(rollback["database_or_persistent_state_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_governance_projection_is_exact_and_stays_local(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        batch_text = BATCH.read_text(encoding="utf-8")
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

        self.assertIn(status["stage"], ("IDS-STAGE069", "IDS-STAGE070"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE069-P1",
                    "IDS-V0_1-STAGE069-P1",
                    "IDS-STAGE069-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE069-P2",
                    "IDS-V0_1-STAGE069-P2",
                    "IDS-STAGE069-P3-GATE",
                ),
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
                (
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-STAGE070-P1-GATE",
                ),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE069", "IDS-STAGE070"))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
                ("IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1"),
                ("IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2"),
                ("IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3"),
                ("IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW"),
                ("IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1"),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2"),
("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3"),
            ),
        )
        self.assertTrue(
            "IDS-STAGE069-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P4-GATE" in plan["stop_condition"]
        )
        self.assertTrue(
            any(item["id"] == "ACC-STAGE069-P1-01" for item in acceptance["items"])
        )
        for expected in (
            'current_stage_id: "IDS-STAGE069"',
            'current_phase_id: "IDS-STAGE069-P1"',
            'current_task_id: "IDS-V0_1-STAGE069-P1"',
            'next_gate_id: "IDS-STAGE069-P2-GATE"',
            "stage069_phase1_state:",
            'stage_id: "IDS-STAGE069"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, roadmap_text)
        for expected in (
            'status: "stage069_phase1_completed_local"',
            'current_task_id: "IDS-V0_1-STAGE069-P1"',
            'next_gate: "IDS-STAGE069-P2-GATE"',
            "stage069_phase2_entry_authorized: true",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, batch_text)
        self.assertIn("EVT-IDS-V0_1-STAGE069-P1-20260814-001", event_ids)


if __name__ == "__main__":
    unittest.main()
