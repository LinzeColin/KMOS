import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE049_PHASE2_DIFFERENTIAL_PARSER_EVALUATION_SLICE.md"
CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_slice_contract.json"
)
SLICE = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_slice.py"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage049-p2-local.json"


class Stage049DifferentialParserEvaluationPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location("stage049_differential_slice", SLICE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _candidate(
        self,
        *,
        version,
        confidence="HIGH",
        status="OUTPUT_CANDIDATE_NOT_VALIDATED",
        source_ref="source:control:stage049-p2",
    ):
        return {
            "candidate_reference": {
                "source_identity_ref": source_ref,
                "route_action": "ROUTE_CANDIDATE_READY_NOT_EXECUTED",
                "parser_output_status": status,
                "parser_family": "CONTROL_DIFFERENTIAL_FIXTURE_ADAPTER",
                "parser_version": version,
                "output_schema_version": "ids.parser_output.v0_1.stage047.p1",
                "evidence_text_label": "UNTRUSTED_EVIDENCE_TEXT",
            },
            "parser_confidence": confidence,
        }

    def _control(self, first=None, second=None):
        return {
            "candidate_controls": [
                first
                or self._candidate(
                    version="ids.parser.control_fixture.v0_1.stage049.p2.alpha",
                    confidence="HIGH",
                ),
                second
                or self._candidate(
                    version="ids.parser.control_fixture.v0_1.stage049.p2.beta",
                    confidence="MEDIUM",
                ),
            ]
        }

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase2_artifacts_exist(self):
        for artifact in (BOUNDARY, CONTRACT, SLICE, BATCH, ROADMAP, EVENTS, STATUS, RUN):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_distinct_control_versions_record_versions_and_confidences(self):
        module = self._slice()
        result = module.evaluate_controlled_differential_eligibility(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(2, result["candidate_count"])
        self.assertEqual(2, result["distinct_parser_version_count"])
        self.assertEqual(
            "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW",
            result["comparison_disposition"],
        )
        self.assertEqual(
            [
                "ids.parser.control_fixture.v0_1.stage049.p2.alpha",
                "ids.parser.control_fixture.v0_1.stage049.p2.beta",
            ],
            result["candidate_parser_versions"],
        )
        self.assertEqual(["HIGH", "MEDIUM"], result["candidate_parser_confidences"])
        self.assertTrue(result["parser_versions_recorded"])
        self.assertTrue(result["parser_confidences_recorded"])

    def test_same_control_version_is_explicitly_not_eligible(self):
        module = self._slice()
        result = module.evaluate_controlled_differential_eligibility(
            self._control(
                second=self._candidate(
                    version="ids.parser.control_fixture.v0_1.stage049.p2.alpha",
                    confidence="LOW",
                )
            )
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(1, result["distinct_parser_version_count"])
        self.assertEqual(
            "COMPARISON_NOT_ELIGIBLE_INSUFFICIENT_DISTINCT_VERSIONS",
            result["comparison_disposition"],
        )
        self.assertFalse(result["fallback_execution_performed"])

    def test_partial_candidate_requires_review_without_queue_write(self):
        module = self._slice()
        result = module.evaluate_controlled_differential_eligibility(
            self._control(
                second=self._candidate(
                    version="ids.parser.control_fixture.v0_1.stage049.p2.beta",
                    confidence="LOW",
                    status="OUTPUT_PARTIAL_REVIEW_REQUIRED",
                )
            )
        )
        self.assertEqual(
            "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
            result["comparison_disposition"],
        )
        self.assertEqual(
            "DIFFERENTIAL_CONTROL_METADATA_REVIEW_REQUIRED",
            result["human_feedback_code"],
        )
        self.assertFalse(result["human_review_queue_write_performed"])

    def test_control_context_mismatch_is_explicitly_not_eligible(self):
        module = self._slice()
        result = module.evaluate_controlled_differential_eligibility(
            self._control(
                second=self._candidate(
                    version="ids.parser.control_fixture.v0_1.stage049.p2.beta",
                    source_ref="source:control:stage049-p2-other",
                )
            )
        )
        self.assertTrue(result["input_accepted"])
        self.assertFalse(result["shared_control_context"])
        self.assertEqual(
            "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
            result["comparison_disposition"],
        )
        self.assertIsNone(result["source_identity_ref"])

    def test_invalid_control_is_rejected_without_echoing_reference(self):
        module = self._slice()
        control = self._control()
        control["unexpected"] = "not accepted"
        result = module.evaluate_controlled_differential_eligibility(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("COMPARISON_INVALID_CONTROL_REJECTED", result["comparison_disposition"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["candidate_parser_versions"])

    def test_evidence_text_remains_data_and_runtime_actions_are_disabled(self):
        module = self._slice()
        result = module.evaluate_controlled_differential_eligibility(self._control())
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", result["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", result["evidence_text_interpretation"])
        for field in (
            "system_instruction_allowed",
            "tool_authorization_allowed",
            "policy_override_allowed",
            "actual_parse_product_comparison_performed",
            "actual_candidate_parse_product_created",
            "source_file_open_performed",
            "route_evaluation_performed",
            "parser_selection_performed",
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

    def test_contract_and_governance_projection_preserve_phase2(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage049.differential_parser_evaluation.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE049-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE049-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["implementation"]["differential_parser_eligibility_slice_implemented"]
        )
        self.assertFalse(
            contract["implementation"]["actual_parse_product_comparison_implemented"]
        )
        self.assertFalse(contract["runtime_boundary"]["parser_execution_allowed"])

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage049_phase2_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE049-P2"'),
            (batch, 'next_gate: "IDS-STAGE049-P3-GATE"'),
            (batch, 'differential_parser_eligibility_slice_implemented: true'),
            (batch, 'actual_parse_product_comparison_performed: false'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'phase_id: "IDS-STAGE049-P2"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-P3-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE049", "IDS-STAGE050"))
        self.assertIn(
            status["phase"],
            ("IDS-STAGE049-P4", "IDS-STAGE049-REVIEW", "IDS-STAGE050-P1", "IDS-STAGE050-P2", "IDS-STAGE050-P3"),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE2_CONTROLLED_DIFFERENTIAL_ELIGIBILITY_SLICE",
            run["result"].strip("`"),
        )
        self.assertTrue(
            run["observed_work"]["in_memory_controlled_differential_eligibility_evaluated"]
        )
        self.assertFalse(run["observed_work"]["actual_parse_product_comparison_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE049-P2-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE049-P2", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE049-P3-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
