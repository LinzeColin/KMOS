import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE071_PHASE1_EMBEDDING_COST_GOVERNOR_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-071_Embedding成本治理器.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE070_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "embedding_queue_cache"
    / "stage070_embedding_queue_cache_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage071-p1-local.json"


class Stage071EmbeddingCostGovernorPhase1Tests(unittest.TestCase):
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
            "ids.stage071.embedding_cost_governor.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-071", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE071-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-071", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EMBEDDING_COST_GOVERNOR_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE071-P2-GATE", contract["next_gate"])

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE071_TASKPACK_STAGE070_REVIEW_STAGE070_PHASE1_CONTRACT_AND_BATCH_LOCK_ONLY",
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

    def test_policy_and_queue_cache_inheritance_are_reused_and_fail_closed(self):
        policy = self.contract["policy_inheritance_dependency"]
        predecessor_policy = self.predecessor["policy_inheritance_dependency"]
        self.assertEqual("denied", policy["default_external_api_policy"])
        self.assertEqual(
            predecessor_policy["allowed_external_api_policy_values"],
            policy["allowed_external_api_policy_values"],
        )
        self.assertEqual(
            predecessor_policy["inheritance_path"], policy["inheritance_path"]
        )
        self.assertEqual(3, policy["allowed_value_count"])
        self.assertEqual(2, policy["inheritance_hop_count"])
        self.assertTrue(policy["owner_must_not_mark_chunks_individually"])
        self.assertFalse(policy["chunk_manual_policy_assignment_allowed"])
        self.assertFalse(policy["document_may_widen_data_source_policy"])
        self.assertTrue(policy["chunk_inherits_effective_document_policy_automatically"])
        self.assertFalse(policy["actual_policy_resolution_performed"])

        dependency = self.contract["queue_cache_dependency"]
        self.assertEqual(
            "PHASE1_EMBEDDING_QUEUE_AND_CACHE_CONTRACT_RUNTIME_DISABLED",
            dependency["required_predecessor_contract_state"],
        )
        self.assertEqual(12, dependency["future_queue_field_count"])
        self.assertEqual(10, dependency["future_cache_field_count"])
        self.assertEqual(7, dependency["future_failed_retry_field_count"])
        for field in (
            "queue_cache_retry_execution_allowed_in_phase1",
            "actual_embedding_queue_created",
            "actual_cache_entry_created",
            "actual_failed_retry_record_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(dependency[field])

    def test_cost_governor_shapes_are_reference_only_and_do_not_embed_numeric_budget(self):
        inputs = self.contract["reference_only_cost_governor_input_contract"]
        governor = self.contract["future_cost_governor_contract"]
        scopes = self.contract["budget_scope_contract"]
        self.assertEqual(16, inputs["field_count"])
        self.assertFalse(inputs["additional_fields_allowed"])
        self.assertEqual(16, governor["field_count"])
        self.assertEqual(
            ["current_batch", "calendar_month", "single_task"],
            governor["budget_scope_names"],
        )
        self.assertEqual(3, governor["budget_scope_count"])
        self.assertTrue(governor["all_budget_scopes_must_pass_before_future_queue"])
        for field in (
            "cost_estimation_or_budget_lookup_allowed_in_phase1",
            "actual_cost_governor_record_created",
            "actual_cost_estimation_performed",
            "actual_budget_lookup_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(governor[field])
        for name, fields in (
            (
                "current_batch",
                (
                    "estimate_required_before_future_queue",
                    "unknown_or_insufficient_fails_closed",
                    "actual_budget_value_recorded",
                    "actual_estimate_generated",
                ),
            ),
            (
                "calendar_month",
                (
                    "remaining_budget_required_before_future_queue",
                    "unknown_or_insufficient_fails_closed",
                    "actual_budget_value_recorded",
                    "actual_monthly_budget_lookup_performed",
                ),
            ),
            (
                "single_task",
                (
                    "task_cap_required_before_future_queue",
                    "unknown_or_exceeded_fails_closed",
                    "actual_budget_value_recorded",
                    "actual_task_cap_evaluation_performed",
                ),
            ),
        ):
            for field in fields:
                with self.subTest(scope=name, field=field):
                    expected = not field.startswith("actual_")
                    self.assertEqual(expected, scopes[name][field])
        self.assertTrue(scopes["no_numeric_budget_or_price_in_phase1"])
        self.assertEqual(0, scopes["actual_batch_cost_estimate_count"])
        self.assertEqual(0, scopes["actual_monthly_budget_check_count"])
        self.assertEqual(0, scopes["actual_task_cap_check_count"])

    def test_predecessor_cost_model_and_audit_shapes_remain_static(self):
        cost = self.contract["future_cost_and_model_dependency"]
        audit = self.contract["future_external_api_audit_dependency"]
        self.assertEqual(
            self.predecessor["future_cost_and_model_contract"]["required_fields"],
            cost["required_fields"],
        )
        self.assertEqual(
            self.predecessor["future_external_api_audit_contract"]["required_fields"],
            audit["required_fields"],
        )
        self.assertEqual(8, cost["field_count"])
        self.assertEqual(18, audit["field_count"])
        self.assertFalse(cost["provider_and_model_selection_allowed_in_phase1"])
        self.assertFalse(cost["actual_budget_checked"])
        self.assertEqual(0, cost["actual_token_count"])
        self.assertEqual(0, cost["actual_cost"])
        self.assertFalse(cost["actual_model_version_recorded"])
        self.assertTrue(audit["audit_required_before_future_provider_call"])
        self.assertFalse(audit["audit_record_creation_allowed_in_phase1"])
        self.assertFalse(audit["actual_audit_record_created"])

    def test_policy_flows_failure_closure_and_business_boundary_are_closed(self):
        flows = self.contract["policy_flow_contract"]
        denied = flows["denied"]
        for field in (
            "external_payload_allowed",
            "embedding_queue_allowed",
            "cache_read_or_write_allowed",
            "failed_retry_allowed",
            "cost_governor_allowed",
            "provider_call_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(denied[field])

        summary = flows["summary_only"]
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            summary["external_payload_allowed"],
        )
        self.assertFalse(summary["chunk_text_payload_allowed"])
        self.assertFalse(summary["provider_call_allowed"])

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

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(14, failures["failure_state_count"])
        self.assertIn(
            "COST_GOVERNOR_BATCH_BUDGET_INSUFFICIENT",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "COST_GOVERNOR_MONTHLY_BUDGET_INSUFFICIENT",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "COST_GOVERNOR_TASK_CAP_EXCEEDED",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        authority = self.contract["authority_and_decision_boundary"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority[
                "business_line_whitebox_human_review_required_for_policy_exception"
            ]
        )
        for field in (
            "cost_governor_can_replace_source_document",
            "budget_check_can_become_business_fact_authority",
            "external_model_output_can_become_business_fact_authority",
            "model_direct_text_guessing_allowed",
            "automatic_business_recommendation_allowed",
            "actual_business_decision_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])

    def test_runtime_phase_protected_and_rollback_boundaries_remain_zero(self):
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        boundary = self.contract["stage_and_phase_boundary"]
        self.assertTrue(boundary["stage070_review_evidence_read"])
        self.assertTrue(boundary["stage071_started"])
        self.assertTrue(boundary["stage071_entry_authorized"])
        self.assertTrue(boundary["phase1_started"])
        self.assertTrue(boundary["stage071_phase2_entry_authorized"])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage072_started",
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
            "STAGE070_REVIEWED_LOCAL_EMBEDDING_QUEUE_CACHE_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage070_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_governance_projection_preserves_phase1_evidence_after_stage_review(self):
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
        self.assertEqual("IDS-STAGE071", status["stage"])
        self.assertEqual("IDS-V0_1-STAGE071-REVIEW", status["phase"])
        self.assertEqual("IDS-V0_1-STAGE071-REVIEW", status["task"])
        self.assertEqual("IDS-STAGE072-P1-GATE", status["next_gate"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertEqual("IDS-V0_1-STAGE071-REVIEW", plan["task"])
        self.assertIn("不创建第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE071-P1-01",
                "ACC-STAGE071-P1-02",
                "ACC-STAGE071-P1-03",
                "ACC-STAGE071-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE071-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_call_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertIn('current_stage_id: "IDS-STAGE071"', roadmap_text)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE071-REVIEW"', roadmap_text)
        self.assertIn("stage070_completed_reviewed_local", batch_text)
        self.assertIn("stage071_phase1_entry_authorized: true", batch_text)
        self.assertIn("EVT-IDS-V0_1-STAGE071-P1-20260815-001", event_ids)
        self.assertIn("EVT-IDS-V0_1-STAGE071-P2-20260815-001", event_ids)
        self.assertIn("EVT-IDS-V0_1-STAGE071-P3-20260815-001", event_ids)
        self.assertIn("EVT-IDS-V0_1-STAGE071-P4-20260815-001", event_ids)
        self.assertIn("EVT-IDS-V0_1-STAGE071-REVIEW-20260820-001", event_ids)

    def test_scope_document_explains_zero_runtime_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "默认 external_api_policy=denied",
            "不创建或执行成本估算、预算查找、单任务上限判断",
            "IDS-STAGE071-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
