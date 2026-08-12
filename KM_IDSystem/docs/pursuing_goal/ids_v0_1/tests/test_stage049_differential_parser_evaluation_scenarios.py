import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
EVIDENCE = BASE / "STAGE049_PHASE3_DIFFERENTIAL_PARSER_EVALUATION_SCENARIOS.md"
CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_scenarios_contract.json"
)
SCENARIOS = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_scenarios.py"
)
P2_SLICE = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_slice.py"
)
P2_CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_slice_contract.json"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage049-p3-local.json"


EXPECTED_SCENARIOS = [
    "pdf-control-candidates",
    "docx-control-candidates",
    "xlsx-control-candidates",
    "csv-low-quality-review",
    "txt-low-quality-review",
    "png-control-candidates",
    "jpeg-control-candidates",
    "tiff-control-candidates",
    "unknown-context-mismatch",
    "corrupt-invalid-control",
    "instruction-like-txt-review",
]


class Stage049DifferentialParserEvaluationPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage049_p3", SCENARIOS)
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
            "ids.stage049.differential_parser_evaluation.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE049-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE049-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(contract["scenario_input_boundary"]["actual_file_open_allowed"])
        self.assertFalse(contract["scenario_input_boundary"]["route_evaluation_allowed"])
        self.assertFalse(contract["implementation"]["actual_parser_route_implemented"])
        self.assertFalse(contract["runtime_boundary"]["fallback_execution_allowed"])

    def test_scenario_catalog_covers_taskpack_format_families(self):
        contract = self._contract()
        self.assertEqual(EXPECTED_SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(11, contract["scenario_input_boundary"]["scenario_count"])
        self.assertTrue(
            contract["format_coverage"]["all_taskpack_format_families_covered"]
        )
        self.assertEqual(
            ["PNG", "JPEG", "TIFF"],
            contract["format_coverage"]["image_variants"],
        )
        self.assertFalse(
            contract["scenario_input_boundary"]["format_label_is_file_detection_result"]
        )

    def test_all_controlled_scenarios_have_explicit_dispositions(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_ISOLATED_CONTROLLED_DIFFERENTIAL_EVALUATION_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(11, report["scenario_count"])
        self.assertEqual(11, report["passed_scenario_count"])
        self.assertEqual(11, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(
            EXPECTED_SCENARIOS,
            [item["scenario_id"] for item in report["scenario_results"]],
        )

    def test_low_quality_controls_require_review_without_fallback(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        for scenario_id in (
            "csv-low-quality-review",
            "txt-low-quality-review",
            "instruction-like-txt-review",
        ):
            item = report_by_id[scenario_id]
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
                    item["comparison_disposition"],
                )
                self.assertEqual("CANDIDATE", item["parser_product_fact_level"])
                self.assertEqual("UNASSESSED", item["quality_gate_state"])
                self.assertFalse(item["fallback_execution_performed"])
                self.assertTrue(item["explicit_disposition"])

    def test_unknown_and_bad_controls_are_explicitly_not_eligible(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        self.assertEqual(
            "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH",
            report_by_id["unknown-context-mismatch"]["comparison_disposition"],
        )
        self.assertEqual(
            "COMPARISON_INVALID_CONTROL_REJECTED",
            report_by_id["corrupt-invalid-control"]["comparison_disposition"],
        )
        for scenario_id in ("unknown-context-mismatch", "corrupt-invalid-control"):
            with self.subTest(scenario=scenario_id):
                item = report_by_id[scenario_id]
                self.assertFalse(item["silent_drop"])
                self.assertFalse(item["fallback_execution_performed"])

    def test_instruction_like_control_cannot_change_system_rules(self):
        report = self._report()
        self.assertTrue(report["instruction_disposition_invariance"])
        item = next(
            result
            for result in report["scenario_results"]
            if result["scenario_id"] == "instruction-like-txt-review"
        )
        self.assertTrue(item["instruction_like"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", item["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", item["evidence_text_interpretation"])
        self.assertFalse(item["system_instruction_allowed"])
        self.assertFalse(item["tool_authorization_allowed"])
        self.assertFalse(item["policy_override_allowed"])

    def test_each_result_is_control_only_and_side_effect_free(self):
        for item in self._report()["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["format_label_is_control_metadata"])
                self.assertFalse(item["actual_route_validation_performed"])
                self.assertFalse(item["actual_parse_product_comparison_performed"])
                self.assertEqual("STAGE048", item["fallback_owner"])
                self.assertTrue(item["side_effect_free"])
                self.assertTrue(item["expectation_met"])

    def test_contract_and_governance_projection_preserve_phase3(self):
        contract = self._contract()
        self.assertTrue(
            contract["implementation"]["phase2_eligibility_slice_reexecuted"]
        )
        self.assertFalse(
            contract["implementation"]["semantic_parse_product_comparison_implemented"]
        )
        self.assertEqual(
            "STAGE048", contract["differential_scenario_validation"]["fallback_owner"]
        )

        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, "stage049_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE049-P3"'),
            (batch, 'next_gate: "IDS-STAGE049-P4-GATE"'),
            (batch, "controlled_differential_scenarios_evaluated: true"),
            (batch, "actual_parse_product_comparison_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'phase_id: "IDS-STAGE049-P3"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-P4-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE049", "IDS-STAGE050"))
        self.assertIn(
            status["phase"],
            ("IDS-STAGE049-P4", "IDS-STAGE049-REVIEW", "IDS-STAGE050-P1", "IDS-STAGE050-P2"),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertTrue(run["observed_work"]["controlled_differential_scenarios_evaluated"])
        self.assertFalse(run["observed_work"]["actual_parse_product_comparison_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE049-P3-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE049-P3", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE049-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
