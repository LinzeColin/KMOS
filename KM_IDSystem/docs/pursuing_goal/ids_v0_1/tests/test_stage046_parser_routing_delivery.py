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
CHECKER = PROJECT_ROOT / "scripts/check_parser_routing_delivery.py"
CONTRACT = BASE / "parser_routing/stage046_parser_routing_delivery_contract.json"
EVIDENCE = BASE / "STAGE046_PHASE4_CLOSEOUT.md"
RUN = PROJECT_ROOT / "machine/runs/2026-07-22-stage046-p4-local.json"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs/governance/roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs/governance/events.jsonl"
HANDOFF = PROJECT_ROOT / "docs/HANDOFF.md"
STATUS = PROJECT_ROOT / "machine/facts/status.json"

PHASE3_COMMIT = "49b876ec68ec8f92f0b9df72d57cca7b2d1d3344"
PHASE3_ROOT_TREE = "974c9917128938f133c64f5752c26502704e90ae"
PHASE3_KMIDS_TREE = "d1eba5655e94697a2381c141a7c55b0e3892d1a6"
PHASE3_PARENT = "18c45ee39522891abe4ef65ed609eb5482f2f148"
ROUTER_VERSION = "ids.parser_router.v0_1.stage046.p2"
REGISTRY_VERSION = "ids.parser_route_registry.v0_1.stage046.p2"

ROUTES = {
    "ROUTE_PDF": ("PDF_PARSER", ["PDF"]),
    "ROUTE_OOXML_WORD": ("OOXML_WORD_PARSER", ["DOCX"]),
    "ROUTE_OOXML_WORKBOOK": ("OOXML_WORKBOOK_PARSER", ["XLSX"]),
    "ROUTE_DELIMITED_TEXT": ("DELIMITED_TEXT_PARSER", ["CSV"]),
    "ROUTE_PLAIN_TEXT": ("PLAIN_TEXT_PARSER", ["TXT"]),
    "ROUTE_IMAGE": ("IMAGE_PARSER", ["PNG", "JPEG", "TIFF"]),
}
OUTPUT_FIELDS = {"text", "tables", "pages", "sections", "confidence", "errors"}
SCENARIOS = [
    "pdf_high_candidate_parser_unavailable",
    "docx_high_candidate_parser_unavailable",
    "xlsx_high_candidate_parser_unavailable",
    "csv_medium_quality_review",
    "txt_medium_quality_review",
    "png_high_candidate_parser_unavailable",
    "jpeg_high_candidate_parser_unavailable",
    "tiff_high_candidate_parser_unavailable",
    "unknown_requires_owner_review",
    "corrupt_input_blocks_explicitly",
    "conflict_requires_owner_review",
    "extension_only_low_requires_owner_review",
    "unsupported_format_is_explicit",
    "instruction_like_text_cannot_override_policy",
]
FAILURE_CLASSES = {
    "PARSER_IMPLEMENTATION_UNAVAILABLE",
    "QUALITY_REVIEW_REQUIRED",
    "OWNER_REVIEW_REQUIRED",
    "DETECTION_INPUT_BLOCKED",
    "FILE_TYPE_UNSUPPORTED",
}
FALSE_TRUTH_FLAGS = {
    "source_file_open_performed",
    "filesystem_scan_performed",
    "file_hash_performed",
    "file_type_redetection_performed",
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
    "stage047_entry_allowed",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage046ParserRoutingDeliveryTests(unittest.TestCase):
    _CHECKER_MODULE = None
    _REPORT = None

    def _module(self):
        self.assertTrue(CHECKER.is_file(), f"missing checker: {CHECKER}")
        cls = type(self)
        if cls._CHECKER_MODULE is None:
            cls._CHECKER_MODULE = _load(CHECKER, "stage046_delivery_test")
        return cls._CHECKER_MODULE

    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing contract: {CONTRACT}")
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _report(self):
        cls = type(self)
        if cls._REPORT is None:
            cls._REPORT = self._module().build_stage046_phase4_delivery_report()
        return copy.deepcopy(cls._REPORT)

    def test_phase4_artifacts_identity_source_and_run_exist(self):
        for path in (CHECKER, CONTRACT, EVIDENCE, RUN):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        contract = self._contract()
        self.assertEqual(
            "ids.stage046.parser_routing.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-046", contract["stage"])
        self.assertEqual("Phase 4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE046-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-046", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE046-REVIEW-GATE", contract["next_gate"])
        source = contract["source_binding"]
        self.assertEqual("SOURCE_VERIFIED", source["source_verification_status"])
        self.assertEqual(1, source["source_member_match_count"])
        self.assertEqual(
            "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39",
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
            lambda value: value["phase3_commit_binding"].update({"commit": "0" * 40}),
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
                report = module.build_stage046_phase4_delivery_report(tampered)
                self.assertFalse(report["contract_valid"])
                self.assertFalse(report["delivery_checks_performed"])
                self.assertEqual("IDS-STAGE046-P4-GATE", report["next_gate"])

    def test_parser_output_samples_are_schema_only_for_all_six_routes(self):
        samples = self._report()["parser_output_samples"]
        self.assertEqual(set(ROUTES), set(samples))
        for route_id, sample in samples.items():
            with self.subTest(route_id=route_id):
                family, accepted_types = ROUTES[route_id]
                self.assertEqual("SCHEMA_ONLY_NOT_EXECUTED", sample["sample_status"])
                self.assertEqual(family, sample["parser_family"])
                self.assertEqual(accepted_types, sample["accepted_types"])
                self.assertEqual("UNASSIGNED_NOT_IMPLEMENTED", sample["parser_version"])
                self.assertEqual(OUTPUT_FIELDS, set(sample["output"]))
                self.assertIsNone(sample["output"]["text"])
                self.assertEqual([], sample["output"]["tables"])
                self.assertEqual([], sample["output"]["pages"])
                self.assertEqual([], sample["output"]["sections"])
                self.assertEqual("UNKNOWN", sample["output"]["confidence"])
                self.assertEqual([], sample["output"]["errors"])
                self.assertTrue(sample["content_fields_are_untrusted_evidence"])
                self.assertFalse(sample["parser_execution_performed"])

    def test_fallback_logs_cover_all_phase3_dispositions_without_runtime(self):
        report = self._report()
        logs = report["fallback_log_samples"]
        self.assertEqual(SCENARIOS, [item["scenario_id"] for item in logs])
        self.assertEqual(14, len(logs))
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
                self.assertTrue(item["quality_disposition"])
                self.assertTrue(item["fallback_state"])

    def test_quality_metrics_are_recomputed_from_phase3_scenarios(self):
        metrics = self._report()["quality_metrics"]
        self.assertEqual(14, metrics["scenario_count"])
        self.assertEqual(14, metrics["passed_scenario_count"])
        self.assertEqual(1.0, metrics["scenario_pass_rate"])
        self.assertEqual(8, metrics["governed_format_expected_count"])
        self.assertEqual(8, metrics["governed_format_observed_count"])
        self.assertEqual(1.0, metrics["governed_format_coverage_ratio"])
        self.assertEqual(6, metrics["governed_route_family_count"])
        self.assertEqual(4, metrics["selected_candidate_route_id_count"])
        self.assertEqual(
            {"HIGH": 6, "MEDIUM": 3, "LOW": 1, "UNKNOWN": 4},
            metrics["confidence_counts"],
        )
        self.assertEqual(
            {
                "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE": 6,
                "QUALITY_REVIEW_REQUIRED": 3,
                "OWNER_REVIEW_REQUIRED": 3,
                "EXPLICIT_ERROR_NO_FALLBACK": 1,
                "UNSUPPORTED_EXPLICIT_NO_FALLBACK": 1,
            },
            metrics["quality_disposition_counts"],
        )
        self.assertEqual(14, metrics["explicit_disposition_count"])
        self.assertEqual(14, metrics["results_with_error_codes"])
        self.assertEqual(0, metrics["silent_drop_count"])
        self.assertEqual(0, metrics["parser_output_produced_count"])
        self.assertEqual(0, metrics["fallback_execution_count"])

    def test_failure_classification_is_bounded_complete_and_fail_closed(self):
        failures = self._report()["failure_classification"]
        self.assertEqual(FAILURE_CLASSES, set(failures))
        covered = []
        for name, item in failures.items():
            with self.subTest(name=name):
                self.assertTrue(item["fail_closed"])
                self.assertTrue(item["error_codes"])
                covered.extend(item["scenario_ids"])
        self.assertEqual(set(SCENARIOS), set(covered))
        self.assertEqual(len(SCENARIOS), len(covered))

    def test_supported_and_unsupported_boundaries_are_explicit(self):
        boundary = self._report()["support_boundary"]
        self.assertEqual(
            {"PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"},
            set(boundary["governed_candidate_formats"]),
        )
        self.assertEqual(set(ROUTES), set(boundary["candidate_route_ids"]))
        self.assertEqual([], boundary["available_parser_routes"])
        self.assertEqual(0, boundary["parser_implementation_count"])
        self.assertEqual(0, boundary["assigned_parser_version_count"])
        self.assertIn("LEGACY_BINARY_OFFICE", boundary["not_claimed_format_classes"])
        self.assertIn("UNRECOGNIZED_BINARY", boundary["not_claimed_format_classes"])
        self.assertFalse(boundary["parser_runtime_available"])
        self.assertFalse(boundary["fallback_runtime_available"])
        self.assertTrue(boundary["route_contract_does_not_imply_parser_support"])

    def test_router_parser_versions_and_configuration_rollback_are_truthful(self):
        report = self._report()
        versions = report["version_evidence"]
        self.assertEqual(ROUTER_VERSION, versions["router_version"])
        self.assertEqual(REGISTRY_VERSION, versions["registry_version"])
        self.assertEqual("STAGE-047", versions["parser_output_contract_owner"])
        self.assertEqual("STAGE-048", versions["fallback_runtime_owner"])
        self.assertEqual("STAGE-049", versions["differential_evaluation_owner"])
        self.assertEqual("STAGE-050", versions["prompt_injection_scan_owner"])
        self.assertEqual(set(ROUTES), set(versions["parser_versions"]))
        self.assertTrue(
            all(
                value == "UNASSIGNED_NOT_IMPLEMENTED"
                for value in versions["parser_versions"].values()
            )
        )
        rollback = report["configuration_rollback"]
        self.assertEqual(PHASE3_COMMIT, rollback["rollback_target_commit"])
        self.assertEqual(PHASE3_KMIDS_TREE, rollback["rollback_target_kmids_tree"])
        self.assertFalse(rollback["configuration_change_performed"])
        self.assertFalse(rollback["parser_configuration_file_created"])
        self.assertIn("RESTORE_PHASE3_SCENARIO_ONLY_STATE", rollback["steps"])
        self.assertIn(
            "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_AUDIT_REPORT_AND_INDEX_ARTIFACTS",
            rollback["steps"],
        )

    def test_truth_feedback_and_next_gate_stop_at_separate_review(self):
        report = self._report()
        self.assertTrue(report["delivery_contract_valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_PARSER_ROUTING_CLOSEOUT_PARSER_DISABLED",
            report["result"],
        )
        self.assertEqual("pending_next_run", report["stage_review_status"])
        self.assertEqual("IDS-STAGE046-REVIEW-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(name=name):
                self.assertFalse(report[name])
        self.assertIn("整阶段复审", report["owner_feedback_zh"])
        self.assertIn("未执行解析器或回退", report["owner_feedback_zh"])
        self.assertIn("不是生产就绪证明", report["owner_feedback_zh"])

    def test_governance_preserves_phase4_route_after_separate_stage_review(self):
        for path in (BATCH, ROADMAP, EVENTS, HANDOFF, STATUS):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing {path}")
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn("stage046_phase4_state:", batch)
        self.assertIn('status: "stage046_phase4_completed_review_pending"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE046-REVIEW"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE046-REVIEW"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE047-P1"', batch)
        self.assertIn("stage046_phase4_state:", roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE046-P4"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE046-REVIEW-GATE"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE046-REVIEW"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE047-P1-GATE"', roadmap)
        self.assertIn("IDS-V0_1-STAGE046-P4", events)
        self.assertIn(
            status["phase"],
            {
                "IDS-STAGE046-REVIEW",
                "IDS-STAGE047-P1",
                "IDS-STAGE047-P2",
                "IDS-STAGE047-P3",
                "IDS-STAGE047-P4",
                "IDS-STAGE047-REVIEW",
            },
        )
        expected_next_gate = {
            "IDS-STAGE046-REVIEW": "IDS-STAGE047-P1-GATE",
            "IDS-STAGE047-P1": "IDS-STAGE047-P2-GATE",
            "IDS-STAGE047-P2": "IDS-STAGE047-P3-GATE",
            "IDS-STAGE047-P3": "IDS-STAGE047-P4-GATE",
            "IDS-STAGE047-P4": "IDS-STAGE047-REVIEW-GATE",
            "IDS-STAGE047-REVIEW": "IDS-STAGE048-P1-GATE",
        }
        self.assertEqual(expected_next_gate[status["phase"]], status["next_gate"])
        self.assertFalse(status["push_allowed"])
        self.assertTrue(
            (
                "Completed task in this run: `IDS-V0_1-STAGE046-REVIEW`" in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P1`" in handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P1`" in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P2`" in handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P2`" in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P3`" in handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P3`" in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-P4`" in handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-P4`" in handoff
                and "Next allowed task: `IDS-V0_1-STAGE047-REVIEW`" in handoff
            )
            or (
                "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`"
                in handoff
                and "Next allowed task: `IDS-V0_1-STAGE048-P1`" in handoff
            )
        )
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE046-P4`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE046-REVIEW`", handoff)

    def test_missing_or_malformed_contract_returns_structured_failure(self):
        module = self._module()
        missing = module.build_stage046_phase4_delivery_report(
            contract_path=BASE / "missing-stage046-p4.json"
        )
        self.assertFalse(missing["contract_valid"])
        self.assertFalse(missing["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE046-P4-GATE", missing["next_gate"])
        malformed = module.build_stage046_phase4_delivery_report([])
        self.assertFalse(malformed["contract_valid"])
        self.assertFalse(malformed["delivery_checks_performed"])
        self.assertEqual("IDS-STAGE046-P4-GATE", malformed["next_gate"])

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
