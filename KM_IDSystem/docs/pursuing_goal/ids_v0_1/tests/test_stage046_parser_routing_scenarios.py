import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CHECKER = ROOT / "scripts" / "check_parser_routing_scenarios.py"
CONTRACT = (
    BASE
    / "parser_routing"
    / "stage046_parser_routing_scenarios_contract.json"
)
EVIDENCE = BASE / "STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"

PHASE2_COMMIT = "18c45ee39522891abe4ef65ed609eb5482f2f148"
PHASE2_ROOT_TREE = "ae7b08d3bc0bab21c2523dfd9a5e756b7d6a840d"
PHASE2_KMIDS_TREE = "0e549aaf1c476fa6d926c12ad444db66921164b5"
PHASE2_PARENT = "c82e4e928b167c718d462dc8cef3eed5b5dbb3ea"
SCENARIO_CONTRACT_ID = "ids.parser_routing.v0_1.stage046.p3.scenarios"

EXPECTED_SOURCE = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-046_解析器路由合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
    ),
    "roadmap_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

EXPECTED_PHASE2_ARTIFACTS = {
    "stage046_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE046_PHASE2_PARSER_ROUTING_SLICE.md"
        ),
        "sha256": (
            "3f7d4bbc3a20cf74af0da4dcb065d85d5ee53dd07440bb364074d10df5588a32"
        ),
    },
    "stage046_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_runtime_contract.json"
        ),
        "sha256": (
            "de4111262bc87b94d238977fa4e1bc70e5d2c51aa8936f946c65413bcd6ff4d4"
        ),
    },
    "stage046_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_routing_runtime.py",
        "sha256": (
            "65f441499f4c0b2c5409ecd7b38b5274b7b3cedae6dc9a79cabd0dcc16be9927"
        ),
    },
    "stage046_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage046_parser_routing_runtime.py"
        ),
        "sha256": (
            "021940f65fdbf5f976e9b3e9ebad84f74abc666d481a41175f306ef1f75fdf9b"
        ),
    },
    "stage046_phase2_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-20-stage046-p2-local.json",
        "sha256": (
            "322a593202657673a92701d8498f5a62a3854b2d9ff96697cb20afcc3527b8aa"
        ),
    },
}

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

SUPPORTED_TYPES = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]

EXPECTED_OUTCOMES = {
    "pdf_high_candidate_parser_unavailable": (
        "PDF", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_PDF",
        "PDF_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "docx_high_candidate_parser_unavailable": (
        "DOCX", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_OOXML_WORD",
        "OOXML_WORD_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "xlsx_high_candidate_parser_unavailable": (
        "XLSX", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_OOXML_WORKBOOK",
        "OOXML_WORKBOOK_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "csv_medium_quality_review": (
        "CSV", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED", None,
        None, "QUALITY_REVIEW_REQUIRED",
    ),
    "txt_medium_quality_review": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED", None,
        None, "QUALITY_REVIEW_REQUIRED",
    ),
    "png_high_candidate_parser_unavailable": (
        "PNG", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "jpeg_high_candidate_parser_unavailable": (
        "JPEG", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "tiff_high_candidate_parser_unavailable": (
        "TIFF", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "unknown_requires_owner_review": (
        "UNKNOWN", "TYPE_UNKNOWN_REVIEW_REQUIRED", "UNKNOWN",
        "ROUTE_REVIEW_REQUIRED", None, None, "OWNER_REVIEW_REQUIRED",
    ),
    "corrupt_input_blocks_explicitly": (
        "CORRUPT_OR_UNREADABLE", "TYPE_INPUT_BLOCKED", "UNKNOWN",
        "ROUTE_BLOCKED", None, None, "EXPLICIT_ERROR_NO_FALLBACK",
    ),
    "conflict_requires_owner_review": (
        "UNKNOWN", "TYPE_CONFLICT_REVIEW_REQUIRED", "UNKNOWN",
        "ROUTE_REVIEW_REQUIRED", None, None, "OWNER_REVIEW_REQUIRED",
    ),
    "extension_only_low_requires_owner_review": (
        "PDF", "TYPE_PROVISIONAL", "LOW", "ROUTE_REVIEW_REQUIRED", None,
        None, "OWNER_REVIEW_REQUIRED",
    ),
    "unsupported_format_is_explicit": (
        "UNSUPPORTED", "TYPE_UNSUPPORTED", "UNKNOWN", "ROUTE_UNSUPPORTED",
        None, None, "UNSUPPORTED_EXPLICIT_NO_FALLBACK",
    ),
    "instruction_like_text_cannot_override_policy": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED", None,
        None, "QUALITY_REVIEW_REQUIRED",
    ),
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage046ParserRoutingScenarioTests(unittest.TestCase):
    _checker_module = None
    _report_value = None

    def _checker(self):
        if self.__class__._checker_module is None:
            self.__class__._checker_module = _load(
                CHECKER, "stage046_parser_routing_scenario_checker_under_test"
            )
        return self.__class__._checker_module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._checker().build_stage046_phase3_report()
            )
        return copy.deepcopy(self.__class__._report_value)

    def test_phase3_artifacts_and_identity_are_exact(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            self.assertTrue(path.is_file(), path)
        contract = self._contract()
        self.assertEqual(
            "ids.stage046.parser_routing.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-046", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE046-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-046", contract["acceptance_id"])
        self.assertEqual(SCENARIO_CONTRACT_ID, contract["scenario_contract_id"])
        self.assertEqual("IDS-STAGE046-P4-GATE", contract["next_gate"])

    def test_source_and_phase2_snapshot_bindings_are_exact(self):
        checker = self._checker()
        contract = self._contract()
        checks = checker.validate_scenario_contract(contract)
        for name in (
            "source_binding_exact",
            "source_live",
            "phase2_commit_bound",
            "phase2_artifacts_exact",
            "phase2_artifacts_live",
        ):
            with self.subTest(name=name):
                self.assertTrue(checks[name], checks)
        self.assertEqual(EXPECTED_SOURCE, contract["source_binding"])
        self.assertEqual(
            {
                "commit": PHASE2_COMMIT,
                "root_tree": PHASE2_ROOT_TREE,
                "kmids_tree": PHASE2_KMIDS_TREE,
                "parent": PHASE2_PARENT,
                "required_ancestor_of_head": True,
            },
            contract["phase2_commit_binding"],
        )
        self.assertEqual(
            EXPECTED_PHASE2_ARTIFACTS,
            contract["phase2_artifact_bindings"],
        )

    def test_scenario_catalog_and_format_coverage_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(14, len(contract["scenario_catalog"]))
        self.assertEqual(SUPPORTED_TYPES, contract["format_coverage"]["supported_types"])
        self.assertEqual(
            ["UNKNOWN", "CORRUPT_OR_UNREADABLE", "UNSUPPORTED"],
            contract["format_coverage"]["failure_types"],
        )
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))

    def test_quality_and_fallback_contract_is_explicit_and_non_runtime(self):
        quality = self._contract()["fallback_quality_contract"]
        self.assertTrue(quality["every_scenario_requires_explicit_disposition"])
        self.assertTrue(quality["all_non_high_quality_results_require_review_or_error"])
        self.assertEqual(0, quality["silent_drop_allowed_count"])
        self.assertFalse(quality["fallback_execution_allowed"])
        self.assertFalse(quality["fallback_log_claim_allowed"])
        self.assertEqual("STAGE-048", quality["fallback_runtime_owner"])

    def test_instruction_text_contract_preserves_stage050_ownership(self):
        instruction = self._contract()["instruction_text_contract"]
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", instruction["required_label"])
        self.assertEqual("EVIDENCE_ONLY", instruction["required_interpretation"])
        self.assertTrue(instruction["route_must_match_non_instruction_baseline"])
        self.assertFalse(instruction["system_rule_override_allowed"])
        self.assertFalse(instruction["tool_authorization_allowed"])
        self.assertFalse(instruction["prompt_injection_scan_allowed"])
        self.assertEqual("STAGE-050", instruction["scanner_runtime_owner"])

    def test_contract_tampering_fails_closed(self):
        checker = self._checker()
        original = self._contract()
        mutations = []
        for mutate in (
            lambda item: item["scenario_catalog"].pop(),
            lambda item: item["phase2_commit_binding"].update({"commit": "0" * 40}),
            lambda item: item["phase2_artifact_bindings"].pop("stage046_phase2_run"),
            lambda item: item["fallback_quality_contract"].update({"silent_drop_allowed_count": 1}),
            lambda item: item["instruction_text_contract"].update({"system_rule_override_allowed": True}),
            lambda item: item["truth_flags"].update({"parser_dispatch_performed": True}),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        unexpected = copy.deepcopy(original)
        unexpected["unexpected"] = True
        mutations.append(unexpected)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                checks = checker.validate_scenario_contract(candidate)
                self.assertFalse(all(checks.values()), checks)

    def test_all_eight_governed_formats_have_explicit_route_outcomes(self):
        results = self._report()["scenario_results"]
        observed = []
        for scenario in SCENARIOS[:8]:
            with self.subTest(scenario=scenario):
                item = results[scenario]
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._route_outcome_tuple(item),
                )
                self.assertFalse(item["silent_drop"])
                observed.append(item["detected_type"])
        self.assertEqual(SUPPORTED_TYPES, observed)

    def test_high_confidence_routes_select_candidates_but_never_dispatch(self):
        results = self._report()["scenario_results"]
        for scenario in (SCENARIOS[0], SCENARIOS[1], SCENARIOS[2], *SCENARIOS[5:8]):
            with self.subTest(scenario=scenario):
                item = results[scenario]
                self.assertTrue(item["route_candidate_selected"])
                self.assertEqual(
                    "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
                    item["quality_disposition"],
                )
                self.assertEqual("UNASSIGNED_NOT_IMPLEMENTED", item["parser_version"])
                self.assertFalse(item["parser_dispatch_performed"])
                self.assertFalse(item["parser_execution_performed"])

    def test_csv_and_txt_medium_quality_require_review_without_fallback(self):
        results = self._report()["scenario_results"]
        expected_routes = {
            "csv_medium_quality_review": "ROUTE_DELIMITED_TEXT",
            "txt_medium_quality_review": "ROUTE_PLAIN_TEXT",
        }
        for scenario, expected_route in expected_routes.items():
            with self.subTest(scenario=scenario):
                item = results[scenario]
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._route_outcome_tuple(item),
                )
                self.assertEqual(expected_route, item["governed_route_id"])
                self.assertFalse(item["route_candidate_selected"])
                self.assertFalse(item["fallback_execution_performed"])

    def test_unknown_and_conflict_require_owner_review_without_silent_drop(self):
        results = self._report()["scenario_results"]
        for scenario in ("unknown_requires_owner_review", "conflict_requires_owner_review"):
            with self.subTest(scenario=scenario):
                item = results[scenario]
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._route_outcome_tuple(item),
                )
                self.assertEqual("OWNER_REVIEW_REQUIRED", item["quality_disposition"])
                self.assertFalse(item["silent_drop"])

    def test_corrupt_input_is_explicit_error_with_no_fallback(self):
        item = self._report()["scenario_results"]["corrupt_input_blocks_explicitly"]
        self.assertEqual(
            EXPECTED_OUTCOMES["corrupt_input_blocks_explicitly"],
                self._route_outcome_tuple(item),
        )
        self.assertEqual("EXPLICIT_ERROR_NO_FALLBACK", item["quality_disposition"])
        self.assertEqual(["DETECTION_INPUT_BLOCKED"], item["errors"])
        self.assertFalse(item["fallback_execution_performed"])

    def test_low_quality_and_unsupported_results_are_explicit(self):
        results = self._report()["scenario_results"]
        low = results["extension_only_low_requires_owner_review"]
        unsupported = results["unsupported_format_is_explicit"]
        self.assertEqual(
            EXPECTED_OUTCOMES["extension_only_low_requires_owner_review"],
            self._route_outcome_tuple(low),
        )
        self.assertEqual("OWNER_REVIEW_REQUIRED", low["quality_disposition"])
        self.assertEqual(
            EXPECTED_OUTCOMES["unsupported_format_is_explicit"],
            self._route_outcome_tuple(unsupported),
        )
        self.assertEqual(
            "UNSUPPORTED_EXPLICIT_NO_FALLBACK",
            unsupported["quality_disposition"],
        )

    def test_instruction_like_text_cannot_change_route_or_policy(self):
        report = self._report()
        item = report["scenario_results"][
            "instruction_like_text_cannot_override_policy"
        ]
        baseline = report["instruction_baseline"]
        self.assertEqual(
            EXPECTED_OUTCOMES["instruction_like_text_cannot_override_policy"],
            self._route_outcome_tuple(item),
        )
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", item["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", item["evidence_text_interpretation"])
        self.assertTrue(item["route_matches_non_instruction_baseline"])
        self.assertEqual(baseline["route_outcome"], item["route_outcome"])
        self.assertFalse(item["system_rule_override_performed"])
        self.assertFalse(item["tool_authorization_performed"])
        self.assertFalse(item["prompt_injection_scan_performed"])

    def test_invalid_request_and_caller_override_rejection_are_replayed(self):
        proof = self._report()["phase2_invalid_request_rejection_proof"]
        self.assertTrue(proof["extra_parser_override_rejected"])
        self.assertTrue(proof["forged_routing_id_rejected"])
        self.assertEqual(2, proof["rejected_request_count"])
        self.assertFalse(proof["parser_dispatch_performed"])

    def test_report_has_fourteen_passes_zero_silent_drops_and_no_effects(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED",
            report["result"],
        )
        self.assertEqual(14, report["scenario_count"])
        self.assertEqual(14, report["passed_scenario_count"])
        self.assertEqual(14, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual("IDS-STAGE046-P4-GATE", report["next_gate"])
        for name in (
            "source_file_open_performed",
            "filesystem_scan_performed",
            "file_hash_performed",
            "file_type_redetection_performed",
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "differential_parser_evaluation_performed",
            "prompt_injection_scan_performed",
            "parser_output_produced",
            "high_confidence_evidence_write_performed",
            "persistent_state_write_performed",
            "database_connection_performed",
            "runtime_output_written",
            "production_runtime_activation_performed",
            "whole_stage_review_performed",
            "batch_review_performed",
            "github_upload_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(name=name):
                self.assertFalse(report[name])

    def test_scenario_results_expose_no_payload_text_or_absolute_paths(self):
        encoded = json.dumps(
            self._report()["scenario_results"],
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("IDS_MetaData", encoded)
        self.assertNotIn("content", encoded)
        self.assertNotIn("source_text", encoded)
        for item in self._report()["scenario_results"].values():
            self.assertEqual([], item["output_refs"])

    def test_cli_emits_machine_readable_pass_report(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(14, payload["passed_scenario_count"])
        self.assertEqual(0, payload["silent_drop_count"])
        self.assertEqual("IDS-STAGE046-P4-GATE", payload["next_gate"])

    def test_governance_routes_to_p4_without_upload_or_stage_review(self):
        docs = EVIDENCE.read_text(encoding="utf-8")
        for marker in (
            "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SCENARIOS",
            "NO_REAL_SOURCE_FILE_READ",
            "NO_PARSER_DISPATCH",
            "NO_FALLBACK_EXECUTION",
            "NO_PROMPT_RULE_OVERRIDE",
            "NO_PHASE4_THIS_RUN",
            "NO_STAGE_REVIEW_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage046_phase3_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE046-P4"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_phase_id: "IDS-STAGE046-P3"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE046-P4-GATE"', roadmap)
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE046-P3`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE046-P4`", handoff)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE046-P3-20260722-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE046-P3", matching[0]["task_id"])

    @staticmethod
    def _route_outcome_tuple(item):
        return (
            item["detected_type"],
            item["detection_state"],
            item["detection_confidence"],
            item["route_action"],
            item["candidate_route_id"],
            item["parser_family"],
            item["quality_disposition"],
        )


if __name__ == "__main__":
    unittest.main()
