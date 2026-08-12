import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE048_PHASE2_PARSER_FALLBACK_SLICE.md"
CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_slice_contract.json"
SLICE = BASE / "parser_fallback" / "stage048_fallback_slice.py"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage048-p2-local.json"


class Stage048ParserFallbackPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location("stage048_fallback_slice", SLICE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _control(
        self,
        *,
        route_action,
        parser_output_status,
        failure_class,
        confidence="HIGH",
    ):
        return {
            "fallback_reference": {
                "source_identity_ref": "source:control:stage048-p2",
                "route_action": route_action,
                "parser_output_status": parser_output_status,
                "parser_family": "CONTROL_FIXTURE_ADAPTER",
                "parser_version": "ids.parser.control_fixture.v0_1.stage048.p2",
                "failure_class": failure_class,
                "evidence_text_label": "UNTRUSTED_EVIDENCE_TEXT",
            },
            "parser_confidence": confidence,
        }

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase2_artifacts_exist(self):
        for artifact in (
            BOUNDARY,
            CONTRACT,
            SLICE,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_candidate_retains_control_parser_version_and_confidence(self):
        module = self._slice()
        result = module.resolve_control_fallback(
            self._control(
                route_action="ROUTE_CANDIDATE_READY_NOT_EXECUTED",
                parser_output_status="OUTPUT_CANDIDATE_NOT_VALIDATED",
                failure_class="NO_FAILURE",
                confidence="HIGH",
            )
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual("NO_FALLBACK_CANDIDATE_RETAINED", result["disposition"])
        self.assertEqual(
            "ids.parser.control_fixture.v0_1.stage048.p2",
            result["parser_version"],
        )
        self.assertEqual("HIGH", result["parser_confidence"])
        self.assertTrue(result["parser_version_recorded"])
        self.assertTrue(result["parser_confidence_recorded"])

    def test_partial_result_requires_human_review_without_queue_write(self):
        module = self._slice()
        result = module.resolve_control_fallback(
            self._control(
                route_action="ROUTE_REVIEW_REQUIRED",
                parser_output_status="OUTPUT_PARTIAL_REVIEW_REQUIRED",
                failure_class="REVIEW_REQUIRED",
                confidence="LOW",
            )
        )
        self.assertEqual(
            "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
            result["disposition"],
        )
        self.assertEqual(
            "FALLBACK_HUMAN_REVIEW_REQUIRED",
            result["human_feedback_code"],
        )
        self.assertFalse(result["human_review_queue_write_performed"])

    def test_explicit_failure_is_retained_without_parser_switch(self):
        module = self._slice()
        result = module.resolve_control_fallback(
            self._control(
                route_action="ROUTE_CANDIDATE_READY_NOT_EXECUTED",
                parser_output_status="OUTPUT_FAILED_EXPLICIT",
                failure_class="PARSER_FAILURE",
                confidence="UNKNOWN",
            )
        )
        self.assertEqual(
            "EXPLICIT_FAILURE_RETAINED_NOT_DROPPED",
            result["disposition"],
        )
        self.assertFalse(result["automatic_parser_switch_performed"])
        self.assertFalse(result["fallback_execution_performed"])

    def test_blocked_and_unsupported_routes_have_explicit_dispositions(self):
        module = self._slice()
        controls = (
            (
                "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
                "PARSER_IMPLEMENTATION_UNAVAILABLE",
            ),
            ("ROUTE_UNSUPPORTED", "UNSUPPORTED_FORMAT"),
            ("ROUTE_BLOCKED", "ROUTE_BLOCKED"),
        )
        for route_action, failure_class in controls:
            with self.subTest(route_action=route_action):
                result = module.resolve_control_fallback(
                    self._control(
                        route_action=route_action,
                        parser_output_status="NO_OUTPUT",
                        failure_class=failure_class,
                        confidence="LOW",
                    )
                )
                self.assertEqual(
                    "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
                    result["disposition"],
                )

    def test_invalid_control_is_rejected_without_echoing_reference(self):
        module = self._slice()
        control = self._control(
            route_action="ROUTE_CANDIDATE_READY_NOT_EXECUTED",
            parser_output_status="OUTPUT_CANDIDATE_NOT_VALIDATED",
            failure_class="NO_FAILURE",
        )
        control["unexpected"] = "not accepted"
        result = module.resolve_control_fallback(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual(
            "INVALID_OUTPUT_REJECTED_NO_FALLBACK",
            result["disposition"],
        )
        self.assertIsNone(result["source_identity_ref"])
        self.assertIsNone(result["parser_version"])

    def test_evidence_text_remains_data_and_runtime_actions_are_disabled(self):
        module = self._slice()
        result = module.resolve_control_fallback(
            self._control(
                route_action="ROUTE_CANDIDATE_READY_NOT_EXECUTED",
                parser_output_status="OUTPUT_CANDIDATE_NOT_VALIDATED",
                failure_class="NO_FAILURE",
            )
        )
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", result["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", result["evidence_text_interpretation"])
        for field in (
            "system_instruction_allowed",
            "tool_authorization_allowed",
            "policy_override_allowed",
            "runtime_execution_performed",
            "source_file_open_performed",
            "route_evaluation_performed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_contract_and_governance_projection_preserve_phase2_after_review(self):
        contract = self._contract()
        self.assertEqual("ids.stage048.parser_fallback.phase2.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE048-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE048-P3-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertTrue(
            contract["implementation"]["fallback_disposition_chain_implemented"]
        )
        self.assertFalse(contract["implementation"]["parser_route_implemented"])
        self.assertFalse(contract["runtime_boundary"]["fallback_execution_allowed"])

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage048_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P2"'),
            (batch, 'next_gate: "IDS-STAGE048-P3-GATE"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P3"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P4"'),
            (batch, 'next_gate: "IDS-STAGE049-P1-GATE"'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'phase_id: "IDS-STAGE048-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE048-P3-GATE"'),
            (roadmap, 'phase_id: "IDS-STAGE048-P3"'),
            (roadmap, 'current_phase_id: "IDS-STAGE048-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-P1-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(
            status["phase"],
            ("IDS-STAGE049-P4", "IDS-STAGE049-REVIEW", "IDS-STAGE050-P1", "IDS-STAGE050-P2", "IDS-STAGE050-P3", "IDS-STAGE050-P4", "IDS-STAGE050-REVIEW"),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE2_IN_MEMORY_FALLBACK_DISPOSITION_SLICE",
            run["result"].strip("`"),
        )
        self.assertTrue(
            run["observed_work"]["in_memory_fallback_disposition_evaluated"]
        )
        self.assertFalse(run["observed_work"]["fallback_execution_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE048-P2-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE048-P2", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE048-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
