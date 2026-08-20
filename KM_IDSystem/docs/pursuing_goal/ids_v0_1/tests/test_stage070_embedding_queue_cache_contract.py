import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE070_PHASE1_EMBEDDING_QUEUE_CACHE_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "embedding_queue_cache"
    / "stage070_embedding_queue_cache_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-070_Embedding队列与缓存.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE069_STAGE_REVIEW.md"
PREDECESSOR_POLICY = (
    BASE
    / "external_api_policy"
    / "stage069_external_api_policy_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage070-p1-local.json"


class Stage070EmbeddingQueueCachePhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.predecessor = json.loads(PREDECESSOR_POLICY.read_text(encoding="utf-8"))

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_POLICY,
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
            "ids.stage070.embedding_queue_cache.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-070", contract["stage"])
        self.assertEqual("IDS-V0_1-STAGE070-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-070", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_EMBEDDING_QUEUE_AND_CACHE_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE070-P2-GATE", contract["next_gate"])

        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE070_TASKPACK_STAGE069_REVIEW_STAGE069_POLICY_CONTRACT_AND_BATCH_LOCK_ONLY",
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

    def test_policy_inheritance_is_reused_automatic_and_fail_closed(self):
        policy = self.contract["policy_inheritance_dependency"]
        self.assertEqual("denied", policy["default_external_api_policy"])
        self.assertEqual(
            ["denied", "summary_only", "full_text_allowed"],
            policy["allowed_external_api_policy_values"],
        )
        self.assertEqual(3, policy["allowed_value_count"])
        self.assertEqual("denied", policy["unknown_policy_fails_closed_to"])
        self.assertEqual(
            self.predecessor["policy_inheritance_contract"]["inheritance_path"],
            policy["inheritance_path"],
        )
        self.assertTrue(policy["owner_must_not_mark_chunks_individually"])
        self.assertFalse(policy["chunk_manual_policy_assignment_allowed"])
        self.assertFalse(policy["document_may_widen_data_source_policy"])
        self.assertTrue(policy["chunk_inherits_effective_document_policy_automatically"])
        self.assertFalse(policy["actual_policy_resolution_performed"])

    def test_reference_queue_cache_retry_cost_and_audit_shapes_are_static(self):
        inputs = self.contract["reference_only_embedding_queue_input_contract"]
        self.assertEqual(17, inputs["field_count"])
        self.assertFalse(inputs["additional_fields_allowed"])
        for field in (
            "source_or_document_body_allowed",
            "summary_body_allowed",
            "chunk_text_allowed",
            "physical_path_or_actual_uri_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])
        self.assertEqual(0, inputs["actual_input_request_count"])

        queue = self.contract["future_embedding_queue_contract"]
        cache = self.contract["future_cache_contract"]
        retry = self.contract["future_failed_retry_contract"]
        self.assertEqual(12, queue["field_count"])
        self.assertEqual(10, cache["field_count"])
        self.assertEqual(7, retry["field_count"])
        for item, fields in (
            (queue, ("queue_creation_allowed_in_phase1", "actual_embedding_queue_created", "actual_embedding_queue_execution_performed")),
            (cache, ("cache_read_or_write_allowed_in_phase1", "actual_cache_entry_created", "actual_cache_read_or_write_performed")),
            (retry, ("automatic_retry_scheduler_allowed_in_phase1", "actual_failed_retry_record_created", "actual_retry_execution_performed")),
        ):
            for field in fields:
                with self.subTest(item=item["mode"], field=field):
                    self.assertFalse(item[field])

        cost = self.contract["future_cost_and_model_contract"]
        audit = self.contract["future_external_api_audit_contract"]
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
        self.assertTrue(cost["budget_unknown_fails_closed"])
        self.assertTrue(cost["budget_insufficient_pauses_future_external_api_task"])
        self.assertFalse(cost["provider_and_model_selection_allowed_in_phase1"])
        self.assertFalse(audit["audit_record_creation_allowed_in_phase1"])

    def test_three_policy_flows_failure_closure_and_business_boundary_are_closed(self):
        flows = self.contract["policy_flow_contract"]
        denied = flows["denied"]
        for field in (
            "external_payload_allowed",
            "summary_payload_allowed",
            "chunk_text_payload_allowed",
            "embedding_queue_allowed",
            "cache_read_or_write_allowed",
            "failed_retry_allowed",
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
        self.assertEqual(12, failures["failure_state_count"])
        self.assertIn("EMBEDDING_QUEUE_POLICY_DENIED", failures["declared_failure_states"])
        self.assertIn(
            "PHASE1_EMBEDDING_QUEUE_EXECUTION_NOT_AUTHORIZED",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        authority = self.contract["authority_and_decision_boundary"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_whitebox_human_review_required_for_policy_exception"])
        for field in (
            "embedding_queue_or_cache_can_replace_source_document",
            "policy_resolution_can_become_business_fact_authority",
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
        self.assertTrue(boundary["stage070_started"])
        self.assertTrue(boundary["stage070_entry_authorized"])
        self.assertTrue(boundary["phase1_started"])
        self.assertTrue(boundary["stage070_phase2_entry_authorized"])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "batch_review_performed",
            "stage071_started",
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
            "STAGE069_REVIEWED_LOCAL_EXTERNAL_API_POLICY_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage069_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_governance_projection_preserves_phase1_evidence_or_legal_phase2_successor(self):
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
        self.assertIn(status["stage"], ("IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
        ))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-V0_1-STAGE070-P1",
                    "IDS-STAGE070-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-V0_1-STAGE070-P2",
                    "IDS-STAGE070-P3-GATE",
                ),
                (
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-V0_1-STAGE070-P3",
                    "IDS-STAGE070-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-V0_1-STAGE070-P4",
                    "IDS-STAGE070-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE070-REVIEW",
                    "IDS-V0_1-STAGE070-REVIEW",
                    "IDS-STAGE071-P1-GATE",
                ),
                (
                    "IDS-V0_1-STAGE071-P1",
                    "IDS-V0_1-STAGE071-P1",
                    "IDS-STAGE071-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE071-P2",
                    "IDS-V0_1-STAGE071-P2",
                    "IDS-STAGE071-P3-GATE",
                ),
                ("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"), ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE070-P1",
                "IDS-V0_1-STAGE070-P2",
                "IDS-V0_1-STAGE070-P3",
                "IDS-V0_1-STAGE070-P4",
                "IDS-V0_1-STAGE070-REVIEW",
                "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P2",
                "IDS-V0_1-STAGE071-P3",
                "IDS-V0_1-STAGE071-P4",
                "IDS-V0_1-STAGE071-REVIEW",
                "IDS-V0_1-STAGE072-P1",
                "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
                'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4',
            ),
        )
        self.assertIn("不创建第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE070-P1-01",
                "ACC-STAGE070-P1-02",
                "ACC-STAGE070-P1-03",
                "ACC-STAGE070-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE070-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_external_api_call_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertTrue(
            'current_stage_id: "IDS-STAGE070"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE071"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE072"' in roadmap_text
            or 'current_stage_id: "IDS-STAGE073"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE070-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE070-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE071-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE071-P2"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE071-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE071-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE071-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE072-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P1"' in roadmap_text or 'current_task_id: "IDS-V0_1-STAGE073-P2"' in roadmap_text
        )
        self.assertIn('STAGE-070:', batch_text)
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE070-P1"' in batch_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P2"' in batch_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P3"' in batch_text
            or 'current_task_id: "IDS-V0_1-STAGE070-P4"' in batch_text
            or 'current_task_id: "IDS-V0_1-STAGE070-REVIEW"' in batch_text
        )
        self.assertIn("EVT-IDS-V0_1-STAGE070-P1-20260815-001", event_ids)

    def test_scope_document_explains_zero_runtime_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "默认 `external_api_policy=denied`",
            "不创建或执行队列、缓存、失败重试",
            "IDS-STAGE070-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
