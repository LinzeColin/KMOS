import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE049_PHASE1_DIFFERENTIAL_PARSER_EVALUATION_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_contract.json"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage049-p1-local.json"


class Stage049DifferentialParserEvaluationPhase1Tests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase1_artifacts_exist(self):
        for artifact in (BOUNDARY, CONTRACT, BATCH, ROADMAP, EVENTS, STATUS, RUN):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage049.differential_parser_evaluation.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-049", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE049-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-049", contract["acceptance_id"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE049-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE048_REVIEW_ARTIFACTS",
            authority["authority"],
        )
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])

    def test_reference_only_input_and_output_contract_are_exact(self):
        contract = self._contract()
        incoming = contract["reference_only_candidate_contract"]
        self.assertEqual("REFERENCE_ONLY_STAGE047_CANDIDATE_METADATA", incoming["mode"])
        self.assertEqual(
            [
                "source_identity_ref",
                "route_action",
                "parser_output_status",
                "parser_family",
                "parser_version",
                "output_schema_version",
                "evidence_text_label",
            ],
            incoming["required_fields"],
        )
        self.assertFalse(incoming["source_body_or_path_allowed"])
        self.assertFalse(incoming["raw_parser_output_allowed"])
        output = contract["parse_product_output_contract"]
        self.assertEqual(
            ["text", "tables", "pages", "sections", "confidence", "errors"],
            output["required_core_fields"],
        )
        self.assertEqual(6, output["core_field_count"])
        self.assertFalse(output["actual_output_created"])

    def test_comparison_quality_and_prompt_boundaries_are_preserved(self):
        contract = self._contract()
        comparison = contract["differential_comparison_contract"]
        self.assertEqual(2, comparison["minimum_candidate_parser_versions"])
        self.assertFalse(comparison["candidate_parser_set_created"])
        self.assertFalse(comparison["comparison_execution_allowed"])
        self.assertFalse(comparison["comparison_may_rewrite_parser_output"])
        self.assertFalse(comparison["comparison_may_promote_evidence"])
        quality = contract["quality_and_evidence_boundary"]
        self.assertEqual("CANDIDATE", quality["parser_product_fact_level"])
        self.assertEqual("UNASSESSED", quality["quality_gate_initial_state"])
        self.assertFalse(quality["comparison_may_bypass_quality_gate"])
        self.assertEqual(
            "REQUIRED_NOT_APPLIED_STAGE050_OWNED",
            contract["prompt_injection_marker_boundary"]["state"],
        )

    def test_runtime_and_external_actions_remain_disabled(self):
        runtime = self._contract()["runtime_boundary"]
        for field in (
            "source_file_open_allowed",
            "route_evaluation_allowed",
            "parser_selection_allowed",
            "parser_execution_allowed",
            "fallback_execution_allowed",
            "differential_evaluation_allowed",
            "quality_gate_execution_allowed",
            "persistent_state_write_allowed",
            "agent_execution_allowed",
            "model_call_allowed",
            "model_token_consumption_allowed",
            "ovh_deployment_allowed",
            "production_runtime_activation_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(runtime[field])

    def test_chinese_feedback_and_rollback_are_bounded(self):
        contract = self._contract()
        feedback = contract["chinese_feedback_contract"]
        self.assertEqual(4, len(feedback["messages"]))
        self.assertTrue(all("当前" in item["message"] or "需要" in item["message"] for item in feedback["messages"]))
        rollback = contract["rollback_contract"]
        self.assertEqual(
            "STAGE048_REVIEWED_LOCAL_FALLBACK_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertFalse(rollback["source_or_raw_data_change_allowed"])
        self.assertFalse(rollback["persistent_runtime_state_change_allowed"])

    def test_phase1_evidence_and_forward_route_are_retained(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage049_phase1_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE049-P1"'),
            (batch, 'next_gate: "IDS-STAGE049-P2-GATE"'),
            (batch, 'second_authoritative_source_created: false'),
            (batch, 'differential_evaluation_performed: false'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'phase_id: "IDS-STAGE049-P1"'),
            (roadmap, 'gate_id: "IDS-STAGE049-P1-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE049", status["stage"])
        self.assertEqual("IDS-STAGE049-P1", status["phase"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_DIFFERENTIAL_PARSER_EVALUATION_BOUNDARY_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertFalse(run["observed_work"]["differential_evaluation_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE049-P1-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE049-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-049"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE049-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
