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
CHECKER = PROJECT_ROOT / "scripts/check_parser_output_delivery.py"
CONTRACT = BASE / "parser_output/stage047_parser_output_delivery_contract.json"
EVIDENCE = BASE / "STAGE047_PHASE4_CLOSEOUT.md"
RUN = PROJECT_ROOT / "machine/runs/2026-07-23-stage047-p4-local.json"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "595a507519b443faa49fca9fa0a6e8bd21cb9dde"
PHASE3_ROOT_TREE = "65a4db060a67ffbb4e7007b25d0dd453fbdbfc88"
PHASE3_KMIDS_TREE = "d0e7058864e6669abcf213cf8c9defe4d57c6fa5"
PHASE3_PARENT = "65b81389e24d9ae371f464dcd6321784b9078d8b"

SUPPORTED_TYPES = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
SAMPLE_SCENARIOS = [
    "pdf_preparsed_pages_candidate",
    "docx_preparsed_sections_candidate",
    "xlsx_preparsed_table_candidate_formula_preserved",
    "csv_preparsed_table_candidate",
    "txt_preparsed_text_candidate",
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
]
ALL_SCENARIOS = SAMPLE_SCENARIOS + [
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "instruction_like_text_cannot_override_policy",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
]
FAILURE_SCENARIOS = {
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "ids_business_filesystem_scan_performed",
    "ids_business_file_hash_performed",
    "file_type_redetection_performed",
    "actual_business_route_evaluation_performed",
    "runtime_parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "ids_business_parser_output_produced",
    "fallback_execution_performed",
    "fallback_attempt_performed",
    "runtime_fallback_log_produced",
    "differential_parser_evaluation_performed",
    "prompt_injection_scan_performed",
    "formula_execution_performed",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "index_write_performed",
    "report_write_performed",
    "job_creation_performed",
    "state_transition_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "stage048_entry_allowed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage047ParserOutputDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage047_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage047_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_source_and_run_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE, RUN):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage047.parser_output.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-047", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE047-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-047", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE047-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4",
            source["source_member_sha256"],
        )

    def test_phase3_commit_tree_parent_and_artifact_hashes_are_exact(self):
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
            lambda value: value["output_samples_contract"].update(
                {"raw_content_retention_allowed": True}
            ),
            lambda value: value["fallback_log_contract"]["log_samples"][0].update(
                {"attempted": True}
            ),
            lambda value: value["review_gate"].update(
                {"phase4_may_mark_stage_reviewed": True}
            ),
        )
        for index, mutate in enumerate(mutators):
            with self.subTest(index=index):
                tampered = self._contract()
                mutate(tampered)
                report = module.build_stage047_phase4_delivery_report(tampered)
                self.assertFalse(report["contract_valid"])
                self.assertFalse(report["delivery_checks_performed"])
                self.assertEqual("IDS-STAGE047-P4-GATE", report["next_gate"])

    def test_sanitized_output_samples_cover_all_supported_formats(self):
        samples = self._report()["parser_output_samples"]
        self.assertEqual(SAMPLE_SCENARIOS, list(samples))
        self.assertEqual(SUPPORTED_TYPES, [item["detected_type"] for item in samples.values()])
        for scenario_id, sample in samples.items():
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    "RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME",
                    sample["sample_status"],
                )
                self.assertEqual(
                    {"text", "tables", "pages", "sections", "confidence", "errors"},
                    set(sample["output_projection"]),
                )
                self.assertTrue(sample["output_id"].startswith("parser-output:sha256:"))
                self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", sample["content_label"])
                self.assertEqual("EVIDENCE_ONLY", sample["content_interpretation"])
                self.assertFalse(sample["raw_content_retained"])
                self.assertFalse(sample["parser_execution_performed"])
                self.assertFalse(sample["quality_gate_evaluation_performed"])
        rendered = json.dumps(samples, ensure_ascii=False)
        self.assertNotIn("Synthetic PDF page", rendered)
        self.assertNotIn("UNSAFE_CONTROL_TEXT_MUST_NOT_BE_ECHOED", rendered)
        self.assertNotIn("=1+1", rendered)

    def test_fallback_logs_cover_every_phase3_scenario_without_runtime(self):
        logs = self._report()["fallback_log_samples"]
        self.assertEqual(ALL_SCENARIOS, [item["scenario_id"] for item in logs])
        self.assertEqual(16, len(logs))
        for item in logs:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertEqual(
                    "DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME",
                    item["sample_status"],
                )
                self.assertTrue(item["explicit_disposition"])
                self.assertFalse(item["attempted"])
                self.assertEqual(0, item["attempt_count"])
                self.assertFalse(item["silent_drop"])
                self.assertFalse(item["parser_switch_performed"])
                self.assertEqual("STAGE-048", item["runtime_owner"])

    def test_quality_metrics_are_recomputed_from_phase3_results(self):
        metrics = self._report()["quality_metrics"]
        self.assertEqual(16, metrics["scenario_count"])
        self.assertEqual(16, metrics["passed_scenario_count"])
        self.assertEqual(1.0, metrics["scenario_pass_rate"])
        self.assertEqual(8, metrics["supported_format_expected_count"])
        self.assertEqual(8, metrics["supported_format_observed_count"])
        self.assertEqual(1.0, metrics["supported_format_coverage_ratio"])
        self.assertEqual(11, metrics["accepted_output_count"])
        self.assertEqual(3, metrics["rejected_output_count"])
        self.assertEqual(2, metrics["route_no_output_count"])
        self.assertEqual(
            {
                "OUTPUT_CANDIDATE_NOT_VALIDATED": 6,
                "OUTPUT_PARTIAL_REVIEW_REQUIRED": 4,
                "OUTPUT_FAILED_EXPLICIT": 1,
            },
            metrics["status_counts"],
        )
        self.assertEqual(11, metrics["unique_output_id_count"])
        self.assertEqual(0, metrics["silent_drop_count"])
        self.assertEqual(0, metrics["parser_execution_count"])
        self.assertEqual(0, metrics["fallback_execution_count"])
        self.assertEqual(0, metrics["persistent_write_count"])

    def test_failure_classification_is_bounded_disjoint_and_complete(self):
        failures = self._report()["failure_classification"]
        covered = []
        self.assertEqual(7, len(failures))
        for name, item in failures.items():
            with self.subTest(name=name):
                self.assertTrue(item["fail_closed"])
                self.assertTrue(item["scenario_ids"])
                self.assertFalse(item["fallback_execution_performed"])
                covered.extend(item["scenario_ids"])
        self.assertEqual(FAILURE_SCENARIOS, set(covered))
        self.assertEqual(len(FAILURE_SCENARIOS), len(covered))

    def test_supported_and_unsupported_boundaries_are_explicit(self):
        boundary = self._report()["support_boundary"]
        self.assertEqual(SUPPORTED_TYPES, boundary["control_supported_formats"])
        self.assertEqual([], boundary["runtime_supported_formats"])
        self.assertEqual(
            ["UNKNOWN", "CORRUPT_OR_UNREADABLE"],
            boundary["route_no_output_types"],
        )
        self.assertIn("LEGACY_BINARY_OFFICE", boundary["not_claimed_format_classes"])
        self.assertIn("UNRECOGNIZED_BINARY", boundary["not_claimed_format_classes"])
        self.assertFalse(boundary["parser_runtime_available"])
        self.assertFalse(boundary["fallback_runtime_available"])
        self.assertTrue(boundary["control_support_does_not_imply_runtime_support"])

    def test_versions_configuration_rollback_and_review_gate_are_truthful(self):
        report = self._report()
        versions = report["version_evidence"]
        self.assertEqual(
            "ids.parser_output.v0_1.stage047.p1",
            versions["output_schema_version"],
        )
        self.assertEqual(
            "ids.parser.output_normalizer.v0_1.stage047.p2",
            versions["normalizer_version"],
        )
        self.assertEqual(set(SUPPORTED_TYPES), set(versions["control_parser_versions"]))
        self.assertTrue(versions["control_versions_are_runtime_versions"] is False)
        rollback = report["configuration_rollback"]
        self.assertEqual(PHASE3_COMMIT, rollback["rollback_target_commit"])
        self.assertEqual(PHASE3_KMIDS_TREE, rollback["rollback_target_kmids_tree"])
        self.assertFalse(rollback["configuration_change_performed"])
        self.assertFalse(rollback["parser_configuration_file_created"])
        self.assertIn("RESTORE_PHASE3_SCENARIO_ONLY_STATE", rollback["steps"])
        self.assertIn(
            "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_LEDGER_AUDIT_INDEX_AND_REPORTS",
            rollback["steps"],
        )

    def test_truth_feedback_and_next_gate_stop_at_separate_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_PARSER_OUTPUT_CLOSEOUT_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE047-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未执行真实解析器或回退", report["owner_feedback_zh"])
        self.assertIn("不是生产就绪证明", report["owner_feedback_zh"])

    def test_governance_records_phase4_and_stops_before_review(self):
        for path in (BATCH, ROADMAP, EVENTS, HANDOFF, STATUS):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn("stage047_phase4_state:", batch)
        self.assertIn('status: "stage047_phase4_completed_review_pending"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE047-P4"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE047-REVIEW"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE047-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE047-REVIEW-GATE"', roadmap)
        self.assertIn("EVT-IDS-V0_1-STAGE047-P4-20260723-001", events)
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE047-P4`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE047-REVIEW`", handoff)
        self.assertIn(
            status["phase"],
            {"IDS-STAGE047-P4", "IDS-STAGE047-REVIEW"},
        )
        if status["phase"] == "IDS-STAGE047-P4":
            self.assertEqual("IDS-STAGE047-REVIEW-GATE", status["next_gate"])
        else:
            self.assertEqual("IDS-V0_1-STAGE047-REVIEW", status["task"])
            self.assertEqual("IDS-STAGE048-P1-GATE", status["next_gate"])
        self.assertFalse(status["push_allowed"])

    def test_missing_or_malformed_contract_returns_structured_failure(self):
        module = self._module()
        missing = module.build_stage047_phase4_delivery_report(
            contract_path=BASE / "missing-stage047-p4.json"
        )
        self.assertFalse(missing["contract_valid"])
        self.assertFalse(missing["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE047-P4-GATE", missing["next_gate"])
        malformed = module.build_stage047_phase4_delivery_report([])
        self.assertFalse(malformed["contract_valid"])
        self.assertFalse(malformed["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE047-P4-GATE", malformed["next_gate"])

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
