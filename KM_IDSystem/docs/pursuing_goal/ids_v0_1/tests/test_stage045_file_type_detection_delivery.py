#!/usr/bin/env python3
"""Validate STAGE-045 Phase 4 file-type-detection closeout evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CHECKER = PROJECT_ROOT / "scripts/check_file_type_detection_delivery.py"
CONTRACT = (
    BASE
    / "file_type_detection/stage045_file_type_detection_delivery_contract.json"
)
EVIDENCE = BASE / "STAGE045_PHASE4_CLOSEOUT.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "dea3c486aceaaa34837aa4a6c9262a907e8dccba"
PHASE3_ROOT_TREE = "ae1dfb9d1135cf578857fda9d6368ef0e2b4a4e7"
PHASE3_KMIDS_TREE = "2a95d14bee023d2c1a3f4965a3206d0299c4b74d"
PHASE3_PARENT = "082565a958459fb4b9ad2b951a74982c30311a03"
DETECTOR_VERSION = "ids.file_type_detector.v0_1.stage045.p2"

PARSER_ROUTES = {
    "PDF_PARSER",
    "OOXML_WORD_PARSER",
    "OOXML_WORKBOOK_PARSER",
    "DELIMITED_TEXT_PARSER",
    "PLAIN_TEXT_PARSER",
    "IMAGE_PARSER",
}
PARSER_OUTPUT_FIELDS = {
    "text",
    "tables",
    "pages",
    "sections",
    "confidence",
    "errors",
}
SUPPORTED_FORMATS = {"PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"}
FAILURE_CLASSES = {
    "UNKNOWN_BINARY",
    "CORRUPT_ZIP_CONTAINER",
    "SIGNAL_TYPE_CONFLICT",
    "EXTENSION_ONLY_LOW_CONFIDENCE",
}
QUALITY_COUNTS = {
    "PRIMARY_ROUTE_CANDIDATE_ONLY": 7,
    "QUALITY_REVIEW_REQUIRED": 3,
    "OWNER_REVIEW_REQUIRED": 3,
    "EXPLICIT_ERROR_NO_FALLBACK": 1,
}
CONFIDENCE_COUNTS = {"HIGH": 7, "MEDIUM": 3, "LOW": 1, "UNKNOWN": 3}
FALSE_TRUTH_FLAGS = {
    "source_file_open_performed",
    "filesystem_scan_performed",
    "file_hash_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "parser_output_produced",
    "fallback_execution_performed",
    "fallback_attempt_performed",
    "runtime_fallback_log_produced",
    "parser_configuration_mutated",
    "high_confidence_evidence_write_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "job_creation_performed",
    "state_transition_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
    "stage046_entry_allowed",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage045FileTypeDetectionDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage045_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage045_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_and_source_binding_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage045.file_type_detection.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-045", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE045-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-045", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE045-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27",
            source["source_member_sha256"],
        )

    def test_phase3_commit_tree_parent_and_upstream_hashes_are_exact(self):
        contract = self._contract()
        self.assertEqual(
            {
                "commit": PHASE3_COMMIT,
                "root_tree": PHASE3_ROOT_TREE,
                "kmids_tree": PHASE3_KMIDS_TREE,
                "parent": PHASE3_PARENT,
                "required_ancestor_of_head": True,
            },
            contract["phase3_commit_binding"],
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", PHASE3_COMMIT, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(0, ancestor.returncode)
        checks = self._module().validate_delivery_contract(contract)
        self.assertTrue(all(checks.values()), checks)

    def test_contract_tampering_fails_closed_before_delivery_checks(self):
        module = self._module()
        mutators = (
            lambda value: value.update({"unknown_root": True}),
            lambda value: value["phase3_commit_binding"].update(
                {"commit": "0" * 40}
            ),
            lambda value: value["parser_output_samples_contract"].update(
                {"parser_execution_allowed": True}
            ),
            lambda value: value["fallback_log_contract"]["log_samples"][0].update(
                {"silent_drop": True}
            ),
            lambda value: value["review_gate"].update(
                {"phase4_may_mark_stage_reviewed": True}
            ),
        )
        for index, mutate in enumerate(mutators):
            with self.subTest(index=index):
                tampered = self._contract()
                mutate(tampered)
                report = module.build_stage045_phase4_delivery_report(tampered)
                self.assertFalse(report["contract_valid"])
                self.assertFalse(report["delivery_checks_performed"])
                self.assertEqual("IDS-STAGE045-P4-GATE", report["next_gate"])

    def test_parser_output_samples_are_schema_only_and_exact(self):
        samples = self._report()["parser_output_samples"]
        self.assertEqual(PARSER_ROUTES, set(samples))
        for route, sample in samples.items():
            with self.subTest(route=route):
                self.assertEqual("SCHEMA_ONLY_NOT_EXECUTED", sample["sample_status"])
                self.assertEqual(route, sample["route_candidate"])
                self.assertEqual("UNASSIGNED_STAGE046", sample["parser_version"])
                self.assertEqual(PARSER_OUTPUT_FIELDS, set(sample["output"]))
                self.assertIsNone(sample["output"]["text"])
                self.assertEqual([], sample["output"]["tables"])
                self.assertEqual([], sample["output"]["pages"])
                self.assertEqual([], sample["output"]["sections"])
                self.assertEqual("UNKNOWN", sample["output"]["confidence"])
                self.assertEqual([], sample["output"]["errors"])
                self.assertTrue(sample["content_fields_are_untrusted_evidence"])
                self.assertFalse(sample["parser_execution_performed"])

    def test_fallback_log_samples_derive_all_non_high_quality_results(self):
        report = self._report()
        logs = report["fallback_log_samples"]
        self.assertEqual(7, len(logs))
        self.assertEqual(
            {item["scenario_id"] for item in logs},
            set(report["non_high_quality_scenario_ids"]),
        )
        for item in logs:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertEqual(
                    "DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME", item["sample_status"]
                )
                self.assertFalse(item["attempted"])
                self.assertEqual(0, item["attempt_count"])
                self.assertFalse(item["silent_drop"])
                self.assertFalse(item["parser_switch_performed"])
                self.assertEqual("STAGE-048", item["runtime_owner"])

    def test_quality_metrics_are_computed_from_phase3_scenarios(self):
        metrics = self._report()["quality_metrics"]
        self.assertEqual(14, metrics["scenario_count"])
        self.assertEqual(14, metrics["passed_scenario_count"])
        self.assertEqual(1.0, metrics["scenario_pass_rate"])
        self.assertEqual(8, metrics["supported_format_expected_count"])
        self.assertEqual(8, metrics["supported_format_observed_count"])
        self.assertEqual(1.0, metrics["supported_format_coverage_ratio"])
        self.assertEqual(CONFIDENCE_COUNTS, metrics["confidence_counts"])
        self.assertEqual(QUALITY_COUNTS, metrics["quality_disposition_counts"])
        self.assertEqual(7, metrics["non_high_quality_result_count"])
        self.assertEqual(7, metrics["explicitly_disposed_non_high_quality_count"])
        self.assertEqual(3, metrics["results_with_error_codes"])
        self.assertEqual(0, metrics["silent_drop_count"])
        self.assertEqual(0, metrics["parser_output_produced_count"])

    def test_failure_classification_is_bounded_and_fail_closed(self):
        failures = self._report()["failure_classification"]
        self.assertEqual(FAILURE_CLASSES, set(failures))
        self.assertEqual(
            "OWNER_REVIEW_REQUIRED", failures["UNKNOWN_BINARY"]["disposition"]
        )
        self.assertEqual(
            ["NO_RELIABLE_TYPE_SIGNAL"],
            failures["UNKNOWN_BINARY"]["error_codes"],
        )
        self.assertEqual(
            "EXPLICIT_ERROR_NO_FALLBACK",
            failures["CORRUPT_ZIP_CONTAINER"]["disposition"],
        )
        self.assertEqual(
            ["CORRUPT_ZIP_CONTAINER"],
            failures["CORRUPT_ZIP_CONTAINER"]["error_codes"],
        )
        self.assertEqual(
            "OWNER_REVIEW_REQUIRED",
            failures["EXTENSION_ONLY_LOW_CONFIDENCE"]["disposition"],
        )
        self.assertEqual([], failures["EXTENSION_ONLY_LOW_CONFIDENCE"]["error_codes"])
        self.assertTrue(all(item["fail_closed"] for item in failures.values()))

    def test_supported_and_unsupported_boundaries_are_explicit(self):
        boundary = self._report()["support_boundary"]
        self.assertEqual(SUPPORTED_FORMATS, set(boundary["detection_candidate_formats"]))
        self.assertEqual(
            {"UNKNOWN", "CORRUPT_OR_UNREADABLE"},
            set(boundary["failure_sentinel_types"]),
        )
        self.assertEqual(PARSER_ROUTES, set(boundary["candidate_only_parser_routes"]))
        self.assertEqual([], boundary["available_parser_routes"])
        self.assertIn("LEGACY_BINARY_OFFICE", boundary["not_claimed_format_classes"])
        self.assertIn("UNRECOGNIZED_BINARY", boundary["not_claimed_format_classes"])
        self.assertFalse(boundary["parser_runtime_available"])
        self.assertFalse(boundary["fallback_runtime_available"])

    def test_detector_parser_versions_and_config_rollback_are_truthful(self):
        report = self._report()
        versions = report["version_evidence"]
        self.assertEqual(DETECTOR_VERSION, versions["detector_version"])
        self.assertEqual("STAGE-046", versions["parser_contract_owner"])
        self.assertEqual("STAGE-047", versions["parser_output_contract_owner"])
        self.assertEqual("STAGE-048", versions["fallback_runtime_owner"])
        self.assertEqual(PARSER_ROUTES, set(versions["parser_versions"]))
        self.assertTrue(
            all(value == "UNASSIGNED_NOT_IMPLEMENTED" for value in versions["parser_versions"].values())
        )
        rollback = report["configuration_rollback"]
        self.assertEqual(PHASE3_COMMIT, rollback["rollback_target_commit"])
        self.assertEqual(PHASE3_KMIDS_TREE, rollback["rollback_target_kmids_tree"])
        self.assertEqual(
            "PHASE3_SCENARIOS_ENABLED_PARSER_AND_FALLBACK_DISABLED",
            rollback["rollback_target_state"],
        )
        self.assertFalse(rollback["configuration_change_performed"])
        self.assertIn("RESTORE_PHASE3_SCENARIO_ONLY_STATE", rollback["steps"])
        self.assertIn("KEEP_PARSER_FALLBACK_AND_PERSISTENCE_DISABLED", rollback["steps"])

    def test_truth_feedback_and_next_gate_stop_at_separate_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_FILE_TYPE_DETECTION_CLOSEOUT_PARSER_DISABLED",
            report["result"],
        )
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE045-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未执行解析器或回退", report["owner_feedback_zh"])
        self.assertIn("不是生产就绪证明", report["owner_feedback_zh"])

    def test_governance_routes_phase4_to_separate_stage_review(self):
        for path in (BATCH, ROADMAP, EVENTS, HANDOFF, STATUS):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn('status: "stage045_phase4_completed_review_pending"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE045-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE045-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE045-REVIEW-GATE"', roadmap)
        self.assertIn("IDS-V0_1-STAGE045-P4", events)
        self.assertTrue(
            (
                status["phase"] == "IDS-STAGE045-REVIEW"
                and status["next_gate"] == "IDS-STAGE046-P1-GATE"
            )
            or (
                status["phase"] == "IDS-STAGE046-P1"
                and status["next_gate"] == "IDS-STAGE046-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P2`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P2"
                and status["next_gate"] == "IDS-STAGE046-P3-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P2`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P3`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P3"
                and status["next_gate"] == "IDS-STAGE046-P4-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P3`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-P4`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-P4"
                and status["next_gate"] == "IDS-STAGE046-REVIEW-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-P4`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE046-REVIEW`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE046-REVIEW"
                and status["next_gate"] == "IDS-STAGE047-P1-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE046-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P1`" in handoff
            )
            or (
                status["phase"] == "IDS-STAGE047-P1"
                and status["next_gate"] == "IDS-STAGE047-P2-GATE"
                and "Completed task in this run: `IDS-V0_1-STAGE047-P1`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`" in handoff
            )
        )
        self.assertIn(
            "Completed task in this run: `IDS-V0_1-STAGE045-P4`", handoff
        )
        self.assertIn(
            "Next allowed task: `IDS-V0_1-STAGE045-REVIEW`", handoff
        )

    def test_missing_or_malformed_contract_returns_structured_failure(self):
        module = self._module()
        missing = module.build_stage045_phase4_delivery_report(
            contract_path=BASE / "missing-stage045-p4.json"
        )
        self.assertFalse(missing["contract_valid"])
        self.assertFalse(missing["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE045-P4-GATE", missing["next_gate"])
        malformed = module.build_stage045_phase4_delivery_report([])
        self.assertFalse(malformed["contract_valid"])
        self.assertFalse(malformed["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE045-P4-GATE", malformed["next_gate"])

    def test_cli_report_matches_in_process_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(self._report(), json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
