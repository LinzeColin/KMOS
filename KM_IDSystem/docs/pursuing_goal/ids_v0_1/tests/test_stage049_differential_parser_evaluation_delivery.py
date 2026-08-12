import importlib.util
import json
from collections import Counter
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CLOSEOUT = BASE / "STAGE049_PHASE4_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_delivery_contract.json"
)
DELIVERY = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_delivery.py"
)
P3_SCENARIOS = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_scenarios.py"
)
P3_CONTRACT = (
    BASE
    / "differential_parser_evaluation"
    / "stage049_differential_parser_evaluation_scenarios_contract.json"
)
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-12-stage049-p4-local.json"


CONTROL_FORMAT_LABELS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
FAILURE_CLASSES = {
    "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW": 6,
    "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED": 2,
    "UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY": 1,
    "CONTROL_CONTEXT_MISMATCH_NOT_ELIGIBLE": 1,
    "INVALID_CONTROL_REJECTED": 1,
}


class Stage049DifferentialParserEvaluationPhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage049_p4", DELIVERY)
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
            "ids.stage049.differential_parser_evaluation.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE049-P4", contract["task_id"])
        self.assertEqual(
            "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED",
            contract["valid_result"],
        )
        self.assertEqual("IDS-STAGE049-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(contract["source_authority"]["source_body_or_path_allowed"])
        self.assertFalse(
            contract["delivery_implementation"]["actual_parse_product_comparison_implemented"]
        )
        self.assertFalse(contract["runtime_boundary"]["fallback_execution_allowed"])

    def test_schema_only_candidate_samples_cover_non_invalid_controls(self):
        samples = self._report()["candidate_parse_product_samples"]
        sample_counts = Counter(item["scenario_id"] for item in samples)
        self.assertEqual(20, len(samples))
        self.assertNotIn("corrupt-invalid-control", sample_counts)
        self.assertEqual(
            20,
            sum(
                count
                for scenario, count in sample_counts.items()
                if scenario != "corrupt-invalid-control"
            ),
        )
        self.assertEqual(
            set(CONTROL_FORMAT_LABELS) | {"UNKNOWN"},
            {item["format_label"] for item in samples},
        )
        for item in samples:
            with self.subTest(sample=item["sample_id"]):
                self.assertEqual(
                    "SCHEMA_ONLY_CANDIDATE_PARSE_PRODUCT_SAMPLE_NOT_EXECUTED",
                    item["sample_kind"],
                )
                self.assertIsNone(item["text"])
                self.assertEqual([], item["tables"])
                self.assertEqual([], item["pages"])
                self.assertEqual([], item["sections"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["source_reference_retained"])
                self.assertFalse(item["runtime_output_produced"])

    def test_disposition_logs_remain_non_runtime(self):
        logs = self._report()["fallback_log_samples"]
        self.assertEqual(11, len(logs))
        for item in logs:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertEqual(
                    "DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME",
                    item["sample_kind"],
                )
                self.assertEqual("STAGE048", item["fallback_owner"])
                self.assertFalse(item["attempted"])
                self.assertEqual(0, item["attempt_count"])
                self.assertFalse(item["silent_drop"])
                self.assertFalse(item["parser_switch_performed"])
                self.assertFalse(item["human_review_queue_write_performed"])
                self.assertFalse(item["runtime_log_written"])

    def test_quality_metrics_match_replayed_controls(self):
        metrics = self._report()["quality_metrics"]
        self.assertEqual(11, metrics["scenario_count"])
        self.assertEqual(11, metrics["passed_scenario_count"])
        self.assertEqual(11, metrics["explicit_disposition_count"])
        self.assertEqual(0, metrics["silent_drop_count"])
        self.assertEqual(8, metrics["control_format_label_count"])
        self.assertEqual(1.0, metrics["control_format_label_coverage_ratio"])
        self.assertEqual(0, metrics["runtime_supported_format_count"])
        self.assertEqual(9, metrics["eligible_control_scenario_count"])
        self.assertEqual(1, metrics["control_context_mismatch_count"])
        self.assertEqual(1, metrics["invalid_control_count"])
        self.assertEqual(20, metrics["candidate_parse_product_sample_count"])
        self.assertEqual(11, metrics["fallback_log_sample_count"])
        self.assertEqual(
            {"HIGH": 12, "MEDIUM": 2, "LOW": 4, "UNKNOWN": 2},
            metrics["candidate_confidence_counts"],
        )
        self.assertEqual(
            {
                "CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW": 6,
                "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED": 3,
                "COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH": 1,
                "COMPARISON_INVALID_CONTROL_REJECTED": 1,
            },
            metrics["comparison_disposition_counts"],
        )
        self.assertEqual(0, metrics["parser_execution_count"])
        self.assertEqual(0, metrics["actual_parse_product_comparison_count"])
        self.assertEqual(0, metrics["fallback_execution_count"])
        self.assertEqual(0, metrics["quality_gate_evaluation_count"])
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
        self.assertEqual(11, len(covered))
        self.assertEqual(11, len(set(covered)))

    def test_instruction_text_remains_evidence_only(self):
        report = self._report()
        instruction_log = next(
            item
            for item in report["fallback_log_samples"]
            if item["scenario_id"] == "instruction-like-txt-review"
        )
        self.assertEqual(
            "UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY",
            instruction_log["failure_classification"],
        )
        self.assertEqual(
            "CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED",
            instruction_log["comparison_disposition"],
        )

    def test_support_boundary_version_evidence_and_rollback_are_bounded(self):
        report = self._report()
        boundary = report["support_boundary"]
        version = report["version_evidence"]
        rollback = report["configuration_rollback"]
        self.assertEqual(CONTROL_FORMAT_LABELS, boundary["control_format_labels"])
        self.assertFalse(boundary["format_label_is_runtime_file_detection"])
        self.assertEqual([], boundary["runtime_supported_formats"])
        self.assertFalse(boundary["parser_runtime_available"])
        self.assertFalse(boundary["differential_comparison_runtime_available"])
        self.assertFalse(boundary["fallback_runtime_available"])
        self.assertTrue(boundary["control_format_labels_do_not_imply_runtime_support"])
        self.assertFalse(boundary["generic_parser_allowed"])
        self.assertEqual(
            "ids.parser.control_fixture.v0_1.stage049.p2",
            version["control_candidate_parser_version_family"],
        )
        self.assertFalse(version["control_candidate_parser_versions_are_runtime_versions"])
        self.assertFalse(version["parser_configuration_change_performed"])
        self.assertFalse(rollback["configuration_change_performed"])
        self.assertEqual(
            "PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED",
            rollback["rollback_target_state"],
        )

    def test_delivery_projection_retains_no_source_body_or_reference(self):
        report = self._report()
        rendered = json.dumps(
            {
                "samples": report["candidate_parse_product_samples"],
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
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED",
            report["result"],
        )
        for field in (
            "source_file_open_performed",
            "file_signature_detection_performed",
            "route_evaluation_performed",
            "parser_selection_performed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "parser_output_produced",
            "actual_parse_product_comparison_performed",
            "fallback_execution_performed",
            "runtime_fallback_log_produced",
            "human_review_queue_write_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
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
            "UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY",
            "PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE049-REVIEW-GATE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, closeout)

    def test_governance_projects_phase4_without_starting_review(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage049_phase4_completed_review_pending"'),
            (batch, "stage049_phase4_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE049-P4"'),
            (batch, 'next_gate: "IDS-STAGE049-REVIEW-GATE"'),
            (batch, "candidate_parse_product_samples_derived: true"),
            (batch, "actual_parse_product_comparison_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_phase_id: "IDS-STAGE049-P4"'),
            (roadmap, 'next_gate_id: "IDS-STAGE049-REVIEW-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertTrue(expected in text, expected)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE049", status["stage"])
        self.assertEqual("IDS-STAGE049-P4", status["phase"])
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

    def test_machine_run_and_event_record_only_local_phase4_evidence(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_ISOLATED_DIFFERENTIAL_EVALUATION_CLOSEOUT_RUNTIME_DISABLED",
            run["result"].strip("`"),
        )
        self.assertEqual(13, run["evidence_iterations"][0]["passed"])
        self.assertFalse(run["observed_work"]["parser_execution_performed"])
        self.assertFalse(run["observed_work"]["actual_parse_product_comparison_performed"])
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE049-P4-20260812-001"
        )
        self.assertEqual("IDS-V0_1-STAGE049-P4", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE049-REVIEW-GATE", event["notes"])
        self.assertIn(
            "KM_IDSystem/" + str(CLOSEOUT.relative_to(ROOT)),
            {item["ref"] for item in event["evidence_refs"]},
        )


if __name__ == "__main__":
    unittest.main()
