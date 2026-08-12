import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
EVIDENCE = BASE / "STAGE048_PHASE3_CONTROLLED_FALLBACK_SCENARIOS.md"
CONTRACT = (
    BASE
    / "parser_fallback"
    / "stage048_parser_fallback_scenarios_contract.json"
)
SCENARIOS = BASE / "parser_fallback" / "stage048_fallback_scenarios.py"
P2_SLICE = BASE / "parser_fallback" / "stage048_fallback_slice.py"
P2_CONTRACT = (
    BASE
    / "parser_fallback"
    / "stage048_parser_fallback_slice_contract.json"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage048-p3-local.json"


EXPECTED_SCENARIOS = [
    "pdf-parser-unavailable",
    "docx-parser-unavailable",
    "xlsx-parser-unavailable",
    "csv-quality-review",
    "txt-quality-review",
    "png-parser-unavailable",
    "jpeg-parser-unavailable",
    "tiff-parser-unavailable",
    "unknown-owner-review",
    "corrupt-explicit-block",
    "signal-conflict-owner-review",
    "extension-low-owner-review",
    "unsupported-explicit-block",
    "instruction-like-txt-review",
]


class Stage048ParserFallbackPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage048_p3", SCENARIOS)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_phase3_scenario_report()
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_artifacts_exist(self):
        for artifact in (
            EVIDENCE,
            CONTRACT,
            SCENARIOS,
            P2_SLICE,
            P2_CONTRACT,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_non_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage048.parser_fallback.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE048-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE048-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(contract["scenario_input_boundary"]["actual_file_open_allowed"])
        self.assertFalse(contract["implementation"]["actual_parser_route_implemented"])
        self.assertFalse(contract["runtime_boundary"]["fallback_execution_allowed"])

    def test_scenario_catalog_covers_taskpack_format_families(self):
        contract = self._contract()
        self.assertEqual(EXPECTED_SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(14, contract["scenario_input_boundary"]["scenario_count"])
        self.assertTrue(
            contract["format_coverage"]["all_taskpack_format_families_covered"]
        )
        self.assertEqual(
            ["PNG", "JPEG", "TIFF"],
            contract["format_coverage"]["image_variants"],
        )

    def test_all_controlled_scenarios_pass_with_explicit_dispositions(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_ISOLATED_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(14, report["scenario_count"])
        self.assertEqual(14, report["passed_scenario_count"])
        self.assertEqual(14, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(EXPECTED_SCENARIOS, [
            item["scenario_id"] for item in report["scenario_results"]
        ])

    def test_each_result_is_explicit_and_side_effect_free(self):
        for item in self._report()["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["expectation_met"])
                self.assertTrue(item["explicit_disposition"])
                self.assertFalse(item["silent_drop"])
                self.assertTrue(item["side_effect_free"])

    def test_low_quality_unknown_and_conflict_scenarios_require_review(self):
        expected = {
            "csv-quality-review",
            "txt-quality-review",
            "unknown-owner-review",
            "signal-conflict-owner-review",
            "extension-low-owner-review",
            "instruction-like-txt-review",
        }
        observed = {
            item["scenario_id"]
            for item in self._report()["scenario_results"]
            if item["disposition"] == "HUMAN_REVIEW_REQUIRED_NOT_QUEUED"
        }
        self.assertEqual(expected, observed)

    def test_bad_file_and_unsupported_format_remain_explicitly_blocked(self):
        results = {
            item["scenario_id"]: item
            for item in self._report()["scenario_results"]
        }
        for scenario in ("corrupt-explicit-block", "unsupported-explicit-block"):
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK",
                    results[scenario]["disposition"],
                )
                self.assertTrue(results[scenario]["explicit_disposition"])

    def test_instruction_like_text_matches_non_instruction_baseline(self):
        report = self._report()
        results = {
            item["scenario_id"]: item
            for item in report["scenario_results"]
        }
        instruction = results["instruction-like-txt-review"]
        baseline = results["txt-quality-review"]
        self.assertTrue(report["instruction_route_invariance"])
        self.assertEqual(baseline["disposition"], instruction["disposition"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", instruction["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", instruction["evidence_text_interpretation"])
        self.assertFalse(instruction["system_instruction_allowed"])
        self.assertFalse(instruction["tool_authorization_allowed"])
        self.assertFalse(instruction["policy_override_allowed"])

    def test_report_retains_no_source_body_or_path(self):
        rendered = json.dumps(self._report(), ensure_ascii=False, sort_keys=True)
        for forbidden in ("/Users/", "IDS_MetaData", "source_text", "content"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, rendered)

    def test_report_level_runtime_actions_are_disabled(self):
        report = self._report()
        for field in (
            "source_file_open_performed",
            "file_signature_detection_performed",
            "route_evaluation_performed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "human_review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "phase4_started",
            "github_upload_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_governance_preserves_phase3_after_local_stage_review(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage048_completed_reviewed_local"'),
            (batch, "stage048_review_state:"),
            (batch, "stage048_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P3"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P4"'),
            (batch, 'next_gate: "IDS-STAGE049-P1-GATE"'),
            (batch, "stage048_phase2_state:"),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
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
            "PASS_PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertEqual(11, run["evidence_iterations"][0]["passed"])
        self.assertFalse(run["observed_work"]["fallback_execution_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE048-P3-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE048-P3", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE048-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
