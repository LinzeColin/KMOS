import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_contract.json"
CONTRACT = BASE / "external_api_policy" / "stage069_external_api_policy_slice_contract.json"
SLICE = BASE / "external_api_policy" / "stage069_external_api_policy_slice.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage069-p2-local.json"


class Stage069ExternalApiPolicyPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage069_external_api_policy_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return self._slice().build_control_input()

    def test_phase2_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            CONTRACT,
            SLICE,
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

    def test_contract_is_executable_and_keeps_all_real_runtime_closed(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage069.external_api_policy.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("IDS-V0_1-STAGE069-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE069-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE069_TASKPACK_PHASE1_STAGE068_REVIEW_ROOT_LOCK_AND_POLICY_GUIDE_ONLY",
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

        inputs = contract["reference_only_policy_input_control_contract"]
        self.assertEqual(15, inputs["field_count"])
        self.assertEqual(5, inputs["control_request_count"])
        self.assertEqual(
            [
                "default_denied",
                "summary_only_inherited",
                "document_restricts_full_text_to_summary_only",
                "full_text_allowed_control_only",
                "budget_insufficient_pauses_full_text",
            ],
            inputs["control_request_order"],
        )
        self.assertTrue(inputs["all_control_references_are_non_business_labels"])
        for field in (
            "additional_fields_allowed",
            "source_or_document_body_allowed",
            "summary_body_allowed",
            "chunk_text_allowed",
            "physical_path_or_actual_uri_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])

        inheritance = contract["policy_inheritance_control_contract"]
        self.assertEqual(
            ["denied", "summary_only", "full_text_allowed"],
            inheritance["allowed_external_api_policy_values"],
        )
        self.assertEqual("denied", inheritance["default_external_api_policy"])
        self.assertTrue(inheritance["chunk_inherits_effective_document_policy_automatically"])
        self.assertFalse(inheritance["document_may_widen_data_source_policy"])
        self.assertFalse(inheritance["chunk_manual_policy_assignment_allowed"])

        self.assertEqual(
            23,
            contract["control_policy_resolution_record_contract"]["field_count"],
        )
        self.assertEqual(12, contract["embedding_queue_intent_contract"]["field_count"])
        self.assertEqual(8, contract["cost_and_model_projection_contract"]["field_count"])
        self.assertEqual(
            18, contract["external_api_audit_projection_contract"]["field_count"]
        )
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_control_slice_projects_policy_inheritance_and_queue_intents(self):
        result = self._slice().execute_external_api_policy_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_EXTERNAL_API_POLICY_INHERITANCE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(5, result["control_policy_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(5, result["policy_resolution_count"])
        self.assertEqual(
            [
                "default_denied",
                "summary_only_inherited",
                "document_restricts_full_text_to_summary_only",
                "full_text_allowed_control_only",
                "budget_insufficient_pauses_full_text",
            ],
            result["control_scenarios_covered"],
        )
        self.assertTrue(result["one_control_resolution_per_scenario"])
        self.assertEqual(
            [
                "denied",
                "summary_only",
                "summary_only",
                "full_text_allowed",
                "full_text_allowed",
            ],
            result["effective_policy_values_observed"],
        )
        self.assertTrue(
            result["all_chunks_inherit_effective_document_policy_automatically"]
        )
        self.assertFalse(result["chunk_manual_policy_assignment_performed"])
        self.assertEqual(5, result["embedding_queue_intent_count"])
        self.assertEqual(1, result["control_queue_blocked_policy_denied_count"])
        self.assertEqual(1, result["control_queue_paused_budget_insufficient_count"])
        self.assertEqual(
            3, result["control_queue_eligible_but_not_persisted_count"]
        )
        self.assertEqual("CONTROL_CACHE_DISABLED_NO_READ_OR_WRITE", result["control_cache_state"])

    def test_control_records_keep_exact_shapes_and_reference_only_labels(self):
        slice_module = self._slice()
        result = slice_module.execute_external_api_policy_control_slice(self._control())
        resolution = result["policy_resolutions"][0]
        self.assertEqual(set(slice_module.POLICY_RESOLUTION_FIELDS), set(resolution))
        for field in (
            "policy_resolution_ref",
            "data_source_ref",
            "document_ref",
            "chunk_ref",
            "embedding_queue_request_ref",
            "provider_ref",
            "model_ref",
            "model_version",
            "external_api_audit_ref",
            "owner_authorization_ref",
            "authorized_at",
            "authorization_reason",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", resolution[field])
        self.assertEqual("denied", resolution["effective_external_api_policy"])
        self.assertEqual("NO_EXTERNAL_PAYLOAD_POLICY_DENIED", resolution["external_payload_mode"])
        self.assertEqual(0, resolution["estimated_token_count"])
        self.assertEqual(0, resolution["estimated_cost"])

        queue_intent = result["embedding_queue_intents"][0]
        self.assertEqual(set(slice_module.QUEUE_INTENT_FIELDS), set(queue_intent))
        self.assertEqual(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
            result["queue_intent_dispositions"][0]["control_queue_state"],
        )
        self.assertEqual(
            "CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT",
            result["queue_intent_dispositions"][-1]["control_queue_state"],
        )

        cost = result["cost_model_records"][0]
        self.assertEqual(set(slice_module.COST_MODEL_FIELDS), set(cost))
        self.assertEqual(0, cost["estimated_token_count"])
        self.assertEqual(0, cost["estimated_cost"])
        audit = result["external_api_audit_projections"][0]
        self.assertEqual(set(slice_module.AUDIT_FIELDS), set(audit))
        self.assertEqual(0, audit["token_count"])
        self.assertEqual(0, audit["cost_estimate"])
        self.assertTrue(result["all_control_audit_projections_have_required_fields"])
        self.assertFalse(result["source_body_summary_body_or_chunk_text_retained"])
        self.assertTrue(
            result[
                "control_output_is_not_actual_policy_assignment_queue_cache_cost_or_audit"
            ]
        )

    def test_invalid_widened_reordered_or_tampered_input_fails_closed(self):
        slice_module = self._slice()
        self.assertEqual(
            ("denied", "CONTROL_SOURCE_POLICY_INVALID_FAIL_CLOSED"),
            slice_module.resolve_effective_policy("unexpected", None),
        )
        self.assertEqual(
            ("denied", "CONTROL_DOCUMENT_POLICY_WIDENING_BLOCKED"),
            slice_module.resolve_effective_policy("summary_only", "full_text_allowed"),
        )

        unexpected = self._control()
        unexpected["unexpected"] = "not accepted"
        rejected = slice_module.execute_external_api_policy_control_slice(unexpected)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("REJECTED", rejected["execution_state"])
        self.assertEqual([], rejected["policy_resolutions"])

        reordered = self._control()
        reordered["external_api_policy_requests"].reverse()
        self.assertFalse(
            slice_module.execute_external_api_policy_control_slice(reordered)[
                "input_accepted"
            ]
        )
        tampered = self._control()
        tampered["external_api_policy_requests"][0]["provider_ref"] = (
            "provider:control:stage069-p2:unexpected"
        )
        self.assertFalse(
            slice_module.execute_external_api_policy_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_real_runtime_actions_and_business_decisions_remain_closed(self):
        result = self._slice().execute_external_api_policy_control_slice(self._control())
        for field in (
            "actual_data_source_policy_read",
            "actual_document_policy_resolved",
            "actual_chunk_policy_assigned",
            "actual_policy_resolution_record_created",
            "actual_embedding_queue_request_created",
            "actual_cache_read_or_write_performed",
            "actual_cost_recorded",
            "actual_model_version_recorded",
            "actual_external_api_audit_record_created",
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chunking_execution_performed",
            "summary_generation_performed",
            "external_payload_created",
            "embedding_queue_execution_performed",
            "cache_read_or_write_performed",
            "provider_credential_read_performed",
            "provider_or_model_selected",
            "external_api_client_initialized",
            "external_api_call_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "embedding_or_index_write_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_chinese_feedback_and_current_governance_preserves_phase2_evidence(self):
        result = self._slice().execute_external_api_policy_control_slice(self._control())
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("一" <= char <= "鿿" for char in message)
                for message in result["chinese_feedback"]
            )
        )

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(status["stage"], ("IDS-STAGE069", "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                           'IDS-STAGE079',
                                           "IDS-STAGE079",
                                           'IDS-STAGE080'))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
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
("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                (
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-V0_1-STAGE069-REVIEW",
                    "IDS-STAGE070-P1-GATE",
                ), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
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

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE')),
        )
        self.assertIn(plan["stage"], ("IDS-STAGE069", "IDS-STAGE070", "IDS-STAGE071", "IDS-STAGE072", "IDS-STAGE073", "IDS-STAGE074",
            'IDS-STAGE075',
            'IDS-STAGE076',

            'IDS-STAGE077', "IDS-STAGE078",
                                         "IDS-STAGE079",
                                         'IDS-STAGE080'))
        self.assertIn(
            (plan["phase"], plan["task"]),
            (
                ("IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2"),
                ("IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3"),
                ("IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4"),
                ("IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW"),
                ("IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1"),
                ("IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2"),
("IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3"),
("IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4"),
("IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW"),
("IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1"),
("IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2"),
("IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3"),
("IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4"),
("IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW"),
("IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1"),
("IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2"),
("IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3"),
("IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4"), ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW"),
("IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1"), ("IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2"), ('IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3'), ('IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4'), ("IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW"),
("IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1"), ("IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2"), ("IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3"), ("IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4"),
                ("IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW"),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW'),
                ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3'),
                ('IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-P4'), ('IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE076-REVIEW'),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4'), ('IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW'),
                ("IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1"), ("IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2"), ("IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3"), ("IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4"),
                    ('IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW'),

                ('IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1'),
                ('IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2'), ('IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3'), ('IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4'), ('IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW')),
        )
        self.assertTrue(
            (
("IDS-STAGE069-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P2-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P3-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P4-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-REVIEW-GATE" in plan["stop_condition"]
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"], "IDS-STAGE075-P4-GATE" in plan["stop_condition"]
            )
        )
        self.assertTrue(
            {
                "ACC-STAGE069-P2-01",
                "ACC-STAGE069-P2-02",
                "ACC-STAGE069-P2-03",
                "ACC-STAGE069-P2-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE069-P2-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE069-P2", run["task_id"])
        self.assertEqual("IDS-STAGE069-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage069_phase2", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE069-P2", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE069-P2-20260814-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
