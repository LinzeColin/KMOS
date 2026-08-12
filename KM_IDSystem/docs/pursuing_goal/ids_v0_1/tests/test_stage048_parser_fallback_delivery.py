import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CLOSEOUT = BASE / "STAGE048_PHASE4_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "parser_fallback"
    / "stage048_parser_fallback_delivery_contract.json"
)
DELIVERY = BASE / "parser_fallback" / "stage048_fallback_delivery.py"
P3_SCENARIOS = BASE / "parser_fallback" / "stage048_fallback_scenarios.py"
P3_CONTRACT = (
    BASE
    / "parser_fallback"
    / "stage048_parser_fallback_scenarios_contract.json"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage048-p4-local.json"


SUPPORTED_FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
FAILURE_CLASSES = {
    "PARSER_IMPLEMENTATION_UNAVAILABLE": 6,
    "QUALITY_REVIEW_REQUIRED": 2,
    "OWNER_REVIEW_REQUIRED": 3,
    "EXPLICIT_INPUT_BLOCKED": 1,
    "UNSUPPORTED_FORMAT": 1,
    "UNTRUSTED_INSTRUCTION_TEXT_REVIEW": 1,
}


class Stage048ParserFallbackPhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage048_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_phase4_delivery_report()
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_artifacts_exist(self):
        for artifact in (
            CLOSEOUT,
            CONTRACT,
            DELIVERY,
            P3_SCENARIOS,
            P3_CONTRACT,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_isolated_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage048.parser_fallback.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE048-P4", contract["task_id"])
        self.assertEqual(
            "PASS_ISOLATED_FALLBACK_CLOSEOUT_RUNTIME_DISABLED",
            contract["valid_result"],
        )
        self.assertEqual("IDS-STAGE048-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(contract["source_authority"]["source_body_or_path_allowed"])
        self.assertFalse(
            contract["delivery_implementation"]["actual_parser_execution_implemented"]
        )
        self.assertFalse(contract["runtime_boundary"]["fallback_execution_allowed"])

    def test_schema_only_parser_output_samples_cover_control_formats(self):
        samples = self._report()["parser_output_samples"]
        self.assertEqual(SUPPORTED_FORMATS, [item["format_label"] for item in samples])
        self.assertEqual(8, len(samples))
        for item in samples:
            with self.subTest(format_label=item["format_label"]):
                self.assertEqual(
                    "SCHEMA_ONLY_PARSER_OUTPUT_SAMPLE_NOT_EXECUTED",
                    item["sample_kind"],
                )
                self.assertIsNone(item["text"])
                self.assertEqual([], item["tables"])
                self.assertEqual([], item["pages"])
                self.assertEqual([], item["sections"])
                self.assertFalse(item["runtime_output_produced"])
                self.assertFalse(item["source_content_retained"])

    def test_disposition_log_samples_remain_non_runtime(self):
        logs = self._report()["fallback_log_samples"]
        self.assertEqual(14, len(logs))
        for item in logs:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertEqual(
                    "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME",
                    item["sample_kind"],
                )
                self.assertFalse(item["attempted"])
                self.assertEqual(0, item["attempt_count"])
                self.assertFalse(item["silent_drop"])
                self.assertFalse(item["parser_switch_performed"])
                self.assertFalse(item["human_review_queue_write_performed"])
                self.assertFalse(item["runtime_log_written"])

    def test_quality_metrics_match_the_replayed_controls(self):
        metrics = self._report()["quality_metrics"]
        self.assertEqual(14, metrics["scenario_count"])
        self.assertEqual(14, metrics["passed_scenario_count"])
        self.assertEqual(14, metrics["explicit_disposition_count"])
        self.assertEqual(0, metrics["silent_drop_count"])
        self.assertEqual(8, metrics["control_supported_format_count"])
        self.assertEqual(1.0, metrics["control_supported_format_coverage_ratio"])
        self.assertEqual(0, metrics["runtime_supported_format_count"])
        self.assertEqual(8, metrics["parser_output_sample_count"])
        self.assertEqual(14, metrics["fallback_log_sample_count"])
        self.assertEqual(
            {"HIGH": 6, "MEDIUM": 3, "LOW": 1, "UNKNOWN": 4},
            metrics["confidence_counts"],
        )
        self.assertEqual(
            {
                "BLOCKED_OR_UNSUPPORTED_NO_FALLBACK": 8,
                "HUMAN_REVIEW_REQUIRED_NOT_QUEUED": 6,
            },
            metrics["disposition_counts"],
        )
        self.assertEqual(FAILURE_CLASSES, metrics["failure_classification_counts"])
        self.assertEqual(0, metrics["parser_execution_count"])
        self.assertEqual(0, metrics["fallback_execution_count"])
        self.assertEqual(0, metrics["persistent_write_count"])

    def test_failure_classification_is_disjoint_complete_and_fail_closed(self):
        classifications = self._report()["failure_classification"]
        self.assertEqual(set(FAILURE_CLASSES), set(classifications))
        covered = []
        for name, count in FAILURE_CLASSES.items():
            with self.subTest(classification=name):
                item = classifications[name]
                self.assertEqual(count, len(item["scenario_ids"]))
                self.assertTrue(item["fail_closed"])
                self.assertFalse(item["fallback_execution_performed"])
                covered.extend(item["scenario_ids"])
        self.assertEqual(14, len(covered))
        self.assertEqual(14, len(set(covered)))

    def test_support_boundary_separates_control_and_runtime_formats(self):
        boundary = self._report()["support_boundary"]
        self.assertEqual(SUPPORTED_FORMATS, boundary["control_supported_formats"])
        self.assertEqual([], boundary["runtime_supported_formats"])
        self.assertFalse(boundary["parser_runtime_available"])
        self.assertFalse(boundary["fallback_runtime_available"])
        self.assertTrue(boundary["control_support_does_not_imply_runtime_support"])
        self.assertFalse(boundary["generic_parser_allowed"])

    def test_version_evidence_and_rollback_are_bounded_to_phase4(self):
        report = self._report()
        version = report["version_evidence"]
        rollback = report["configuration_rollback"]
        self.assertEqual(
            "ids.parser.control_fixture.v0_1.stage048.p2",
            version["control_parser_version"],
        )
        self.assertFalse(version["control_parser_versions_are_runtime_versions"])
        self.assertFalse(version["parser_configuration_change_performed"])
        self.assertFalse(rollback["configuration_change_performed"])
        self.assertEqual(
            "PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_state"],
        )

    def test_delivery_projection_retains_no_source_body_or_path(self):
        report = self._report()
        rendered = json.dumps(
            {
                "samples": report["parser_output_samples"],
                "logs": report["fallback_log_samples"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for forbidden in ("/Users/", "IDS_MetaData", "source_identity_ref"):
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
            "parser_output_produced",
            "fallback_execution_performed",
            "runtime_fallback_log_produced",
            "human_review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "whole_stage_review_performed",
            "github_upload_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_closeout_explains_the_chinese_boundary_and_next_gate(self):
        closeout = CLOSEOUT.read_text(encoding="utf-8")
        for expected in (
            "运行时支持格式集合为空",
            "PARSER_IMPLEMENTATION_UNAVAILABLE",
            "UNTRUSTED_INSTRUCTION_TEXT_REVIEW",
            "PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE048-REVIEW-GATE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, closeout)

    def test_governance_preserves_phase4_after_local_stage_review(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage048_completed_reviewed_local"'),
            (batch, "stage048_review_state:"),
            (batch, "stage048_phase4_state:"),
            (batch, "stage048_phase3_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-P4"'),
            (batch, 'current_task_id: "IDS-V0_1-STAGE048-REVIEW"'),
            (batch, 'next_gate: "IDS-STAGE049-P1-GATE"'),
            (batch, 'model_token_consumption_performed: false'),
            (batch, 'ovh_deployment_performed: false'),
            (roadmap, 'current_phase_id: "IDS-STAGE048-REVIEW"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-P1-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE049-P3", status["phase"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_phase4_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_ISOLATED_FALLBACK_CLOSEOUT_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertEqual(13, run["evidence_iterations"][0]["passed"])
        self.assertFalse(run["observed_work"]["parser_execution_performed"])
        self.assertFalse(run["observed_work"]["fallback_execution_performed"])
        self.assertFalse(run["observed_work"]["model_token_consumption_performed"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])

        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE048-P4-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE048-P4", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE048-REVIEW-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(CLOSEOUT.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
