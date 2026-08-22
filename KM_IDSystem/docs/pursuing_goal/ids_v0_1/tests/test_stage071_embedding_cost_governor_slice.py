import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_slice_contract.json"
)
SLICE = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_slice.py"
)
SCOPE = BASE / "STAGE071_PHASE2_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE.md"
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
RUN = ROOT / "machine" / "runs" / "2026-08-15-stage071-p2-local.json"


class Stage071EmbeddingCostGovernorPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage071_embedding_cost_governor_slice", SLICE
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
            SCOPE,
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

    def test_contract_is_executable_and_keeps_runtime_closed(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage071.embedding_cost_governor.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE071-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE071-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE071_TASKPACK_PHASE1_CONTRACT_STAGE070_REVIEW_AND_BATCH_LOCK_ONLY",
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

        inputs = contract["reference_only_cost_governor_input_control_contract"]
        self.assertEqual(16, inputs["field_count"])
        self.assertEqual(7, inputs["control_request_count"])
        self.assertEqual(
            [
                "default_denied",
                "summary_only_inherited_all_budget_gates_pass",
                "document_restricts_full_text_to_summary_only_all_budget_gates_pass",
                "full_text_allowed_all_budget_gates_pass",
                "current_batch_budget_insufficient_pauses_full_text",
                "monthly_budget_insufficient_pauses_full_text",
                "single_task_cap_exceeded_pauses_full_text",
            ],
            inputs["control_request_order"],
        )
        for field in (
            "additional_fields_allowed",
            "source_or_document_body_allowed",
            "summary_body_allowed",
            "chunk_text_allowed",
            "physical_path_or_actual_uri_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(inputs[field])

        queue_cache = contract["embedding_queue_cache_retry_control_contract"]
        self.assertEqual(12, queue_cache["future_queue_field_count"])
        self.assertEqual(10, queue_cache["future_cache_field_count"])
        self.assertEqual(7, queue_cache["future_retry_field_count"])
        governor = contract["cost_governor_control_contract"]
        self.assertEqual(16, governor["field_count"])
        self.assertEqual(3, governor["budget_scope_count"])
        self.assertEqual(18, contract["external_api_audit_control_contract"]["field_count"])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_control_slice_projects_policy_queue_cache_cost_and_audit_records(self):
        result = self._slice().execute_embedding_cost_governor_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_EMBEDDING_COST_GOVERNOR_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(7, result["control_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(7, result["policy_resolution_count"])
        self.assertEqual(7, result["cost_governor_record_count"])
        self.assertEqual(7, result["embedding_queue_record_count"])
        self.assertEqual(7, result["cache_record_count"])
        self.assertEqual(7, result["failed_retry_record_count"])
        self.assertEqual(7, result["external_api_audit_projection_count"])
        self.assertTrue(
            result["all_chunks_inherit_effective_document_policy_automatically"]
        )
        self.assertFalse(result["chunk_manual_policy_assignment_performed"])
        self.assertEqual(1, result["control_cost_governor_blocked_policy_denied_count"])
        self.assertEqual(
            3, result["control_cost_governor_paused_three_budget_gates_count"]
        )
        self.assertEqual(
            3, result["control_cost_governor_eligible_not_persisted_count"]
        )
        self.assertEqual(1, result["control_queue_blocked_policy_denied_count"])
        self.assertEqual(3, result["control_queue_paused_three_budget_gates_count"])
        self.assertEqual(3, result["control_queue_eligible_not_persisted_count"])

    def test_control_records_keep_exact_p1_shapes_and_reference_only_labels(self):
        module = self._slice()
        result = module.execute_embedding_cost_governor_control_slice(self._control())
        request = self._control()["embedding_cost_governor_requests"][0]
        self.assertEqual(set(module.REFERENCE_INPUT_FIELDS), set(request))
        for field in (
            "cost_governor_request_ref",
            "embedding_queue_request_ref",
            "policy_resolution_ref",
            "data_source_ref",
            "document_ref",
            "chunk_ref",
            "provider_ref",
            "model_ref",
            "model_version",
            "batch_budget_ref",
            "monthly_budget_ref",
            "task_budget_cap_ref",
            "external_api_audit_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", request[field])
        self.assertEqual(0, request["estimated_token_count"])

        queue = result["embedding_queue_records"][0]
        self.assertEqual(
            set(module.QUEUE_FIELDS) | {"control_queue_state", "control_queue_reason"},
            set(queue),
        )
        cache = result["cache_records"][0]
        self.assertEqual(set(module.CACHE_FIELDS), set(cache))
        retry = result["failed_retry_records"][0]
        self.assertEqual(set(module.RETRY_FIELDS), set(retry))
        governor = result["cost_governor_records"][0]
        self.assertEqual(
            set(module.COST_GOVERNOR_FIELDS)
            | {"control_cost_governor_state", "control_cost_governor_reason"},
            set(governor),
        )
        audit = result["external_api_audit_projections"][0]
        self.assertEqual(set(module.AUDIT_FIELDS), set(audit))
        self.assertEqual(0, governor["estimated_token_count"])
        self.assertEqual(0, governor["estimated_cost"])
        self.assertEqual(0, audit["token_count"])
        self.assertEqual(0, audit["cost_estimate"])
        self.assertTrue(result["all_control_records_keep_required_shapes"])
        self.assertFalse(result["source_body_summary_body_or_chunk_text_retained"])

    def test_policy_inheritance_blocks_unauthorized_chunk_egress(self):
        module = self._slice()
        result = module.execute_embedding_cost_governor_control_slice(self._control())
        resolutions = {
            scenario: record
            for scenario, record in zip(
                module.CONTROL_SCENARIOS, result["policy_resolutions"]
            )
        }
        self.assertEqual(
            "denied",
            resolutions["default_denied"]["effective_external_api_policy"],
        )
        self.assertEqual(
            "summary_only",
            resolutions[
                "document_restricts_full_text_to_summary_only_all_budget_gates_pass"
            ]["effective_external_api_policy"],
        )
        self.assertEqual(
            "full_text_allowed",
            resolutions["full_text_allowed_all_budget_gates_pass"][
                "effective_external_api_policy"
            ],
        )
        denied_queue = result["embedding_queue_records"][0]
        self.assertEqual(
            "CONTROL_QUEUE_BLOCKED_POLICY_DENIED",
            denied_queue["control_queue_state"],
        )
        summary_queue = result["embedding_queue_records"][1]
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            summary_queue["external_payload_mode"],
        )
        self.assertEqual(
            ("denied", "CONTROL_DOCUMENT_POLICY_WIDENING_BLOCKED"),
            module.resolve_effective_policy("summary_only", "full_text_allowed"),
        )

    def test_each_budget_scope_pauses_queue_cache_and_retry(self):
        module = self._slice()
        result = module.execute_embedding_cost_governor_control_slice(self._control())
        by_scenario = {
            scenario: governor
            for scenario, governor in zip(
                module.CONTROL_SCENARIOS, result["cost_governor_records"]
            )
        }
        for scenario, field, expected in (
            (
                "current_batch_budget_insufficient_pauses_full_text",
                "batch_budget_check_state",
                module.BUDGET_INSUFFICIENT,
            ),
            (
                "monthly_budget_insufficient_pauses_full_text",
                "monthly_budget_check_state",
                module.BUDGET_INSUFFICIENT,
            ),
            (
                "single_task_cap_exceeded_pauses_full_text",
                "task_budget_cap_check_state",
                module.TASK_CAP_EXCEEDED,
            ),
        ):
            with self.subTest(scenario=scenario):
                self.assertEqual(expected, by_scenario[scenario][field])
                index = module.CONTROL_SCENARIOS.index(scenario)
                self.assertEqual(
                    "CONTROL_QUEUE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    result["embedding_queue_records"][index]["control_queue_state"],
                )
                self.assertEqual(
                    "CONTROL_CACHE_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    result["cache_records"][index]["cache_disposition"],
                )
                self.assertEqual(
                    "CONTROL_RETRY_PAUSED_THREE_BUDGET_GATES_NOT_ALL_PASSED",
                    result["failed_retry_records"][index]["retry_state"],
                )
        self.assertTrue(result["all_three_budget_scope_failure_closures_covered"])

    def test_audit_projection_records_control_provider_model_token_chunk_and_reason(self):
        module = self._slice()
        result = module.execute_embedding_cost_governor_control_slice(self._control())
        audit = result["external_api_audit_projections"][3]
        for field in (
            "provider_ref",
            "model_ref",
            "model_version",
            "chunk_ref",
            "policy_inheritance_reason",
            "token_count",
        ):
            with self.subTest(field=field):
                self.assertIn(field, audit)
        self.assertIn(":control:", audit["provider_ref"])
        self.assertIn(":control:", audit["model_ref"])
        self.assertIn(":control:", audit["chunk_ref"])
        self.assertEqual(0, audit["token_count"])
        self.assertEqual(
            "CONTROL_AUDIT_REQUIRED_BEFORE_FUTURE_PROVIDER_CALL",
            audit["audit_disposition"],
        )

    def test_invalid_widened_reordered_or_tampered_input_fails_closed(self):
        module = self._slice()
        self.assertEqual(
            ("denied", "CONTROL_SOURCE_POLICY_INVALID_FAIL_CLOSED"),
            module.resolve_effective_policy("unexpected", None),
        )
        unexpected = self._control()
        unexpected["unexpected"] = "not accepted"
        self.assertFalse(
            module.execute_embedding_cost_governor_control_slice(unexpected)[
                "input_accepted"
            ]
        )
        reordered = self._control()
        reordered["embedding_cost_governor_requests"].reverse()
        self.assertFalse(
            module.execute_embedding_cost_governor_control_slice(reordered)[
                "input_accepted"
            ]
        )
        tampered = self._control()
        tampered["embedding_cost_governor_requests"][0][
            "provider_ref"
        ] = "provider:control:unexpected"
        self.assertFalse(
            module.execute_embedding_cost_governor_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_real_runtime_and_business_decisions_remain_closed(self):
        result = self._slice().execute_embedding_cost_governor_control_slice(
            self._control()
        )
        for field in (
            "actual_data_source_policy_read",
            "actual_document_policy_resolved",
            "actual_chunk_policy_assigned",
            "actual_policy_resolution_record_created",
            "actual_embedding_queue_request_created",
            "actual_cache_entry_created",
            "actual_cache_read_or_write_performed",
            "actual_failed_retry_record_created",
            "actual_retry_execution_performed",
            "actual_cost_governor_record_created",
            "actual_cost_estimation_performed",
            "actual_batch_budget_lookup_performed",
            "actual_monthly_budget_lookup_performed",
            "actual_task_cap_evaluation_performed",
            "actual_model_version_recorded",
            "actual_external_api_audit_record_created",
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "source_file_open_performed",
            "external_payload_created",
            "embedding_queue_execution_performed",
            "cache_read_or_write_performed",
            "failed_retry_execution_performed",
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

    def test_chinese_feedback_and_p2_governance_evidence_survives_stage_review(self):
        result = self._slice().execute_embedding_cost_governor_control_slice(
            self._control()
        )
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
        self.assertIn(
            (status["stage"], status["phase"], status["next_gate"]),
            (
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-P4', 'IDS-STAGE076-REVIEW-GATE'),
                ('IDS-STAGE076', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-STAGE077-P1-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'),
             ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ('IDS-STAGE081', 'IDS-STAGE081-P1', 'IDS-STAGE081-P2-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"),
                ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P2', 'IDS-STAGE084-P3-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-STAGE085-P3-GATE'),

                ('IDS-STAGE085', 'IDS-STAGE085-P2', 'IDS-STAGE085-P3-GATE'),
             ("IDS-STAGE085", "IDS-STAGE085-P3", "IDS-STAGE085-P4-GATE"),
             ("IDS-STAGE085", "IDS-STAGE085-P4", "IDS-STAGE085-REVIEW-GATE"), ("IDS-STAGE085", "IDS-STAGE085-REVIEW", "IDS-STAGE086-P1-GATE"), ("IDS-STAGE086", "IDS-STAGE086-P1", "IDS-STAGE086-P2-GATE")),
        )
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
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
                                     "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4", "IDS-V0_1-STAGE085-REVIEW", "IDS-V0_1-STAGE086-P1"))
        self.assertTrue(
            (
"IDS-STAGE073-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"] or "IDS-STAGE075-P4-GATE" in plan["stop_condition"] or "IDS-STAGE075-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE076-P1-GATE" in plan["stop_condition"] or "IDS-STAGE076-P2-GATE" in plan["stop_condition"] or "IDS-STAGE076-P3-GATE" in plan["stop_condition"] or "IDS-STAGE076-P4-GATE" in plan["stop_condition"] or "IDS-STAGE076-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE077-P1-GATE" in plan["stop_condition"] or "IDS-STAGE077-P2-GATE" in plan["stop_condition"] or "IDS-STAGE077-P3-GATE" in plan["stop_condition"] or "IDS-STAGE077-P4-GATE" in plan["stop_condition"] or "IDS-STAGE077-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE078-P1-GATE" in plan["stop_condition"] or "IDS-STAGE078-P2-GATE" in plan["stop_condition"] or "IDS-STAGE078-P3-GATE" in plan["stop_condition"] or "IDS-STAGE078-P4-GATE" in plan["stop_condition"] or "IDS-STAGE078-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE079-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE079-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE080-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE081-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE082-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE083-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE084-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE084-P2-GATE" in plan["stop_condition"]
            or 'IDS-STAGE084-P4-GATE' in plan['stop_condition']
            or 'IDS-STAGE084-REVIEW-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P3-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P3-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-P4-GATE' in plan['stop_condition']
            or 'IDS-STAGE085-REVIEW-GATE' in plan['stop_condition']
            or 'IDS-STAGE086-P1-GATE' in plan['stop_condition']
            or 'IDS-STAGE086-P2-GATE' in plan['stop_condition']
        )
        )
        self.assertTrue(
            {
                "ACC-STAGE071-P2-01",
                "ACC-STAGE071-P2-02",
                "ACC-STAGE071-P2-03",
                "ACC-STAGE071-P2-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        self.assertEqual("RUN-IDS-STAGE071-P2-LOCAL-20260815-001", run["run_id"])
        self.assertEqual("IDS-V0_1-STAGE071-P2", run["task_id"])
        self.assertEqual("IDS-STAGE071-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("IDS-V0_1-STAGE071-P2", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-P2-20260815-001"
                for item in events
            )
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-P3-20260815-001"
                for item in events
            )
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-P4-20260815-001"
                for item in events
            )
        )
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE071-REVIEW-20260820-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
