import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
BOUNDARY = BASE / "STAGE048_PHASE1_PARSER_FALLBACK_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "parser_fallback" / "stage048_parser_fallback_contract.json"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage048-p1-local.json"


class Stage048ParserFallbackPhase1Tests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase1_artifacts_exist(self):
        self.assertTrue(BOUNDARY.is_file())
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(BATCH.is_file())
        self.assertTrue(ROADMAP.is_file())
        self.assertTrue(EVENTS.is_file())
        self.assertTrue(STATUS.is_file())
        self.assertTrue(RUN.is_file())

    def test_identity_authority_and_phase_boundary(self):
        contract = self._contract()
        self.assertEqual("ids.stage048.parser_fallback.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-048", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE048-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-048", contract["acceptance_id"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE048-P2-GATE", contract["next_gate"])
        authority = contract["source_authority"]
        self.assertEqual(
            "FROZEN_TASKPACK_TEXT_AND_STAGE047_REVIEW_ARTIFACTS",
            authority["authority"],
        )
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertFalse(authority["source_body_or_path_allowed"])

    def test_reference_only_input_and_explicit_dispositions(self):
        contract = self._contract()
        incoming = contract["fallback_input_contract"]
        self.assertEqual("REFERENCE_ONLY_STAGE047_RESULT", incoming["mode"])
        self.assertEqual(
            [
                "source_identity_ref",
                "route_action",
                "parser_output_status",
                "parser_family",
                "parser_version",
                "failure_class",
                "evidence_text_label",
            ],
            incoming["required_fields"],
        )
        self.assertFalse(incoming["source_body_or_path_allowed"])
        self.assertFalse(incoming["raw_exception_allowed"])
        dispositions = contract["fallback_disposition_contract"]
        self.assertTrue(dispositions["silent_drop_allowed"] is False)
        self.assertTrue(dispositions["automatic_parser_switch_allowed"] is False)
        self.assertEqual(
            [
                "NO_FALLBACK_CANDIDATE_RETAINED",
                "HUMAN_REVIEW_REQUIRED_NOT_QUEUED",
                "EXPLICIT_FAILURE_RETAINED_NOT_DROPPED",
                "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
                "INVALID_OUTPUT_REJECTED_NO_FALLBACK",
            ],
            [item["code"] for item in dispositions["dispositions"]],
        )
        self.assertTrue(all(item["explicit"] for item in dispositions["dispositions"]))

    def test_quality_prompt_and_runtime_boundaries(self):
        contract = self._contract()
        self.assertEqual(
            "REQUIRED_NOT_APPLIED_STAGE050_OWNED",
            contract["prompt_injection_marker_boundary"]["state"],
        )
        self.assertFalse(contract["quality_and_evidence_boundary"]["evidence_promotion_allowed"])
        self.assertFalse(contract["quality_and_evidence_boundary"]["quality_gate_execution_allowed"])
        runtime = contract["runtime_boundary"]
        for field in (
            "source_file_open_allowed",
            "parser_dispatch_allowed",
            "parser_execution_allowed",
            "fallback_execution_allowed",
            "human_review_queue_write_allowed",
            "persistent_state_write_allowed",
            "agent_execution_allowed",
            "model_call_allowed",
            "model_token_consumption_allowed",
            "local_service_start_allowed",
            "ovh_deployment_allowed",
            "production_runtime_activation_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(runtime[field])

    def test_chinese_feedback_and_rollback_are_bounded(self):
        contract = self._contract()
        feedback = contract["chinese_feedback_contract"]
        self.assertEqual(5, len(feedback["messages"]))
        self.assertTrue(
            all("人工复核" in item["message"] or "不执行" in item["message"] for item in feedback["messages"])
        )
        rollback = contract["rollback_contract"]
        self.assertEqual("STAGE047_REVIEWED_LOCAL", rollback["return_to"])
        self.assertFalse(rollback["source_or_raw_data_change_allowed"])
        self.assertFalse(rollback["persistent_runtime_state_change_allowed"])

    def test_governance_projection_and_local_run_are_current(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage048_phase1_completed"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P1"'),
            (batch, 'next_gate: "IDS-STAGE048-P2-GATE"'),
            (batch, 'second_authoritative_source_created: false'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'current_stage_id: "IDS-STAGE048"'),
            (roadmap, 'current_phase_id: "IDS-STAGE048-P1"'),
            (roadmap, 'next_gate_id: "IDS-STAGE048-P2-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE048", status["stage"])
        self.assertEqual("IDS-STAGE048-P1", status["phase"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE1_PARSER_FALLBACK_BOUNDARY_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertFalse(run["observed_work"]["fallback_execution_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])

        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE048-P1-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE048-P1", event["task_id"])
        self.assertEqual(["ACC-STAGE-048"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE048-P2-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
