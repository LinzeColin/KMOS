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
CHECKER = ROOT / "scripts" / "check_file_type_detection_scenarios.py"
CONTRACT = (
    BASE
    / "file_type_detection"
    / "stage045_file_type_detection_scenarios_contract.json"
)
EVIDENCE = BASE / "STAGE045_PHASE3_FILE_TYPE_DETECTION_SCENARIOS.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"

PHASE2_COMMIT = "e61e8f7cbf8795a3f5d2b33be4031f1885948b00"
PHASE2_ROOT_TREE = "94f820df60f592c516c61160ce40e059458d7b9f"
PHASE2_KMIDS_TREE = "2daa58d66a496e3b1aede42ed1154de271d80824"
PHASE2_PARENT = "2f4051b7e9960e10698052b4e3f71fcb093f35e3"
INTEGRATION_COMMIT = "082565a958459fb4b9ad2b951a74982c30311a03"
INTEGRATION_ROOT_TREE = "532d8338fdbbdab89be2cd16ac12a50ad850a5fe"
INTEGRATION_KMIDS_TREE = "81489b941d9740cc0462d4dc1371481a44ed766d"
ORIGIN_MAIN_PARENT = "0495b8482b78ff937a92ee061c92980bcbde173b"
DETECTOR_VERSION = "ids.file_type_detector.v0_1.stage045.p2"
SCENARIO_CONTRACT_ID = "ids.file_type_detector.v0_1.stage045.p3.scenarios"

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
        "STAGE-045_文件类型检测.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27"
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

EXPECTED_UPSTREAM = {
    "stage045_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
            "stage045_file_type_detection_runtime_contract.json"
        ),
        "sha256": (
            "e3d8cb8408f513eaeaa156a1f43fe7d618736f6830415a48bb40e315e3dae9d7"
        ),
    },
    "stage045_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_file_type_detection_runtime.py",
        "sha256": (
            "48e0a4cae96f0ed605e0567ee5bdd38b7a0677ca892048d86290de09462a8d93"
        ),
    },
    "stage045_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage045_file_type_detection_runtime.py"
        ),
        "sha256": (
            "14271495dbed4b624973d26b2ae81b49e1578be6e21d3747daed60de8f2a4de7"
        ),
    },
    "stage045_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE045_PHASE2_FILE_TYPE_DETECTION_SLICE.md"
        ),
        "sha256": (
            "6de20b6c927d76fbad6286e7861a64f903a0c8cccc2c1226860ca6e3e266283c"
        ),
    },
    "stage045_phase2_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-19-stage045-p2-local.json",
        "sha256": (
            "4e82dda2b265251eac61806323a04acbce5fb1a7d89f2baf99482e0d29b5f19d"
        ),
    },
}

SCENARIOS = [
    "matching_pdf_signature_route_candidate",
    "matching_docx_container_route_candidate",
    "matching_xlsx_container_route_candidate",
    "matching_csv_text_route_candidate",
    "matching_txt_text_route_candidate",
    "matching_png_signature_route_candidate",
    "matching_jpeg_signature_route_candidate",
    "matching_tiff_little_endian_route_candidate",
    "matching_tiff_big_endian_route_candidate",
    "unknown_binary_requires_owner_review",
    "corrupt_zip_blocks_with_explicit_error",
    "conflicting_signature_mime_extension_requires_review",
    "extension_only_low_confidence_requires_review",
    "instruction_like_text_cannot_override_system_policy",
]

EXPECTED_OUTCOMES = {
    "matching_pdf_signature_route_candidate": (
        "PDF", "TYPE_CONFIRMED", "HIGH", "PDF_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_docx_container_route_candidate": (
        "DOCX", "TYPE_CONFIRMED", "HIGH", "OOXML_WORD_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_xlsx_container_route_candidate": (
        "XLSX", "TYPE_CONFIRMED", "HIGH", "OOXML_WORKBOOK_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_csv_text_route_candidate": (
        "CSV", "TYPE_PROVISIONAL", "MEDIUM", "DELIMITED_TEXT_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_txt_text_route_candidate": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "PLAIN_TEXT_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_png_signature_route_candidate": (
        "PNG", "TYPE_CONFIRMED", "HIGH", "IMAGE_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_jpeg_signature_route_candidate": (
        "JPEG", "TYPE_CONFIRMED", "HIGH", "IMAGE_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_tiff_little_endian_route_candidate": (
        "TIFF", "TYPE_CONFIRMED", "HIGH", "IMAGE_PARSER", "ROUTE_CANDIDATE"
    ),
    "matching_tiff_big_endian_route_candidate": (
        "TIFF", "TYPE_CONFIRMED", "HIGH", "IMAGE_PARSER", "ROUTE_CANDIDATE"
    ),
    "unknown_binary_requires_owner_review": (
        "UNKNOWN", "TYPE_UNKNOWN_REVIEW_REQUIRED", "UNKNOWN", "UNSUPPORTED", "ROUTE_REVIEW_REQUIRED"
    ),
    "corrupt_zip_blocks_with_explicit_error": (
        "CORRUPT_OR_UNREADABLE", "TYPE_INPUT_BLOCKED", "UNKNOWN", "UNSUPPORTED", "ROUTE_BLOCKED"
    ),
    "conflicting_signature_mime_extension_requires_review": (
        "UNKNOWN", "TYPE_CONFLICT_REVIEW_REQUIRED", "UNKNOWN", "UNSUPPORTED", "ROUTE_REVIEW_REQUIRED"
    ),
    "extension_only_low_confidence_requires_review": (
        "PDF", "TYPE_PROVISIONAL", "LOW", "PDF_PARSER", "ROUTE_REVIEW_REQUIRED"
    ),
    "instruction_like_text_cannot_override_system_policy": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "PLAIN_TEXT_PARSER", "ROUTE_CANDIDATE"
    ),
}

EXPECTED_QUALITY_DISPOSITIONS = {
    "matching_pdf_signature_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_docx_container_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_xlsx_container_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_csv_text_route_candidate": "QUALITY_REVIEW_REQUIRED",
    "matching_txt_text_route_candidate": "QUALITY_REVIEW_REQUIRED",
    "matching_png_signature_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_jpeg_signature_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_tiff_little_endian_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "matching_tiff_big_endian_route_candidate": "PRIMARY_ROUTE_CANDIDATE_ONLY",
    "unknown_binary_requires_owner_review": "OWNER_REVIEW_REQUIRED",
    "corrupt_zip_blocks_with_explicit_error": "EXPLICIT_ERROR_NO_FALLBACK",
    "conflicting_signature_mime_extension_requires_review": "OWNER_REVIEW_REQUIRED",
    "extension_only_low_confidence_requires_review": "OWNER_REVIEW_REQUIRED",
    "instruction_like_text_cannot_override_system_policy": "QUALITY_REVIEW_REQUIRED",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage045FileTypeDetectionScenarioTests(unittest.TestCase):
    _checker_module = None
    _report_value = None

    def _checker(self):
        if self.__class__._checker_module is None:
            self.__class__._checker_module = _load(
                CHECKER, "stage045_detection_scenario_checker_under_test"
            )
        return self.__class__._checker_module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._checker().build_stage045_phase3_report()
            )
        return copy.deepcopy(self.__class__._report_value)

    def test_phase3_artifacts_and_identity_are_exact(self):
        for path in (CHECKER, CONTRACT, EVIDENCE):
            self.assertTrue(path.is_file(), path)
        contract = self._contract()
        self.assertEqual(
            "ids.stage045.file_type_detection.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-045", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE045-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-045", contract["acceptance_id"])
        self.assertEqual(SCENARIO_CONTRACT_ID, contract["scenario_contract_id"])
        self.assertEqual("IDS-STAGE045-P4-GATE", contract["next_gate"])

    def test_source_phase2_integration_and_upstream_bindings_are_exact(self):
        checker = self._checker()
        contract = self._contract()
        checks = checker.validate_scenario_contract(contract)
        self.assertTrue(checks["source_binding_exact"])
        self.assertTrue(checks["source_live"])
        self.assertTrue(checks["phase2_commit_bound"])
        self.assertTrue(checks["integration_baseline_bound"])
        self.assertTrue(checks["upstream_bindings_exact"])
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
            {
                "commit": INTEGRATION_COMMIT,
                "root_tree": INTEGRATION_ROOT_TREE,
                "kmids_tree": INTEGRATION_KMIDS_TREE,
                "parents": [PHASE2_COMMIT, ORIGIN_MAIN_PARENT],
                "required_ancestor_of_head": True,
                "handoff_resolution": (
                    "CURRENT_STAGE045_GATE_PRESERVED_CANONICAL_OVERRIDE_ADDED"
                ),
            },
            contract["integration_baseline"],
        )
        self.assertEqual(EXPECTED_UPSTREAM, contract["upstream_bindings"])

    def test_scenario_catalog_format_coverage_and_expectations_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(14, len(contract["scenario_catalog"]))
        self.assertEqual(
            ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"],
            contract["format_coverage"]["supported_types"],
        )
        self.assertEqual(
            ["UNKNOWN", "CORRUPT_OR_UNREADABLE"],
            contract["format_coverage"]["failure_types"],
        )
        self.assertEqual(set(SCENARIOS), set(contract["scenario_expectations"]))

    def test_fallback_quality_and_instruction_contracts_fail_closed(self):
        contract = self._contract()
        quality = contract["fallback_quality_contract"]
        self.assertTrue(quality["all_non_high_quality_results_require_review_or_error"])
        self.assertEqual(0, quality["silent_drop_allowed_count"])
        self.assertFalse(quality["fallback_execution_allowed"])
        self.assertEqual("STAGE-048", quality["fallback_runtime_owner"])
        instruction = contract["instruction_text_contract"]
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", instruction["required_label"])
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
            lambda item: item["integration_baseline"].update({"required_ancestor_of_head": False}),
            lambda item: item["fallback_quality_contract"].update({"silent_drop_allowed_count": 1}),
            lambda item: item["instruction_text_contract"].update({"system_rule_override_allowed": True}),
            lambda item: item["truth_flags"].update({"parser_dispatch_performed": True}),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["unexpected"] = True
        mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                checks = checker.validate_scenario_contract(candidate)
                self.assertFalse(all(checks.values()), checks)

    def test_pdf_signature_scenario_is_high_confidence_candidate_only(self):
        item = self._report()["scenario_results"][SCENARIOS[0]]
        self.assertEqual(EXPECTED_OUTCOMES[SCENARIOS[0]], self._result_outcome(item))
        self.assertEqual("PRIMARY_ROUTE_CANDIDATE_ONLY", item["quality_disposition"])

    def test_docx_and_xlsx_require_valid_ooxml_containers(self):
        results = self._report()["scenario_results"]
        for scenario in SCENARIOS[1:3]:
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._result_outcome(results[scenario]),
                )
                self.assertTrue(results[scenario]["container_inspection_performed"])

    def test_csv_and_txt_are_medium_quality_and_require_quality_review(self):
        results = self._report()["scenario_results"]
        for scenario in SCENARIOS[3:5]:
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._result_outcome(results[scenario]),
                )
                self.assertEqual("QUALITY_REVIEW_REQUIRED", results[scenario]["quality_disposition"])

    def test_png_jpeg_and_both_tiff_endiannesses_are_detected(self):
        results = self._report()["scenario_results"]
        for scenario in SCENARIOS[5:9]:
            with self.subTest(scenario=scenario):
                self.assertEqual(
                    EXPECTED_OUTCOMES[scenario],
                    self._result_outcome(results[scenario]),
                )
                self.assertEqual("PRIMARY_ROUTE_CANDIDATE_ONLY", results[scenario]["quality_disposition"])

    def test_unknown_binary_requires_owner_review_without_silent_drop(self):
        scenario = "unknown_binary_requires_owner_review"
        item = self._report()["scenario_results"][scenario]
        self.assertEqual(EXPECTED_OUTCOMES[scenario], self._result_outcome(item))
        self.assertEqual("OWNER_REVIEW_REQUIRED", item["quality_disposition"])
        self.assertIn("NO_RELIABLE_TYPE_SIGNAL", item["errors"])

    def test_corrupt_zip_blocks_with_explicit_error_and_no_fallback(self):
        scenario = "corrupt_zip_blocks_with_explicit_error"
        item = self._report()["scenario_results"][scenario]
        self.assertEqual(EXPECTED_OUTCOMES[scenario], self._result_outcome(item))
        self.assertEqual("EXPLICIT_ERROR_NO_FALLBACK", item["quality_disposition"])
        self.assertEqual(["CORRUPT_ZIP_CONTAINER"], item["errors"])
        self.assertFalse(item["fallback_execution_performed"])

    def test_conflicting_signals_require_owner_review(self):
        scenario = "conflicting_signature_mime_extension_requires_review"
        item = self._report()["scenario_results"][scenario]
        self.assertEqual(EXPECTED_OUTCOMES[scenario], self._result_outcome(item))
        self.assertEqual("OWNER_REVIEW_REQUIRED", item["quality_disposition"])
        self.assertEqual(["SIGNAL_TYPE_CONFLICT"], item["errors"])

    def test_extension_only_is_low_confidence_and_never_dispatches(self):
        scenario = "extension_only_low_confidence_requires_review"
        item = self._report()["scenario_results"][scenario]
        self.assertEqual(EXPECTED_OUTCOMES[scenario], self._result_outcome(item))
        self.assertEqual("OWNER_REVIEW_REQUIRED", item["quality_disposition"])
        self.assertFalse(item["parser_dispatch_performed"])

    def test_instruction_like_text_cannot_change_route_or_policy(self):
        scenario = "instruction_like_text_cannot_override_system_policy"
        checker = self._checker()
        item = self._report()["scenario_results"][scenario]
        self.assertEqual(EXPECTED_OUTCOMES[scenario], self._result_outcome(item))
        self.assertTrue(item["evidence_text_marker_applied"])
        self.assertTrue(item["route_matches_non_instruction_baseline"])
        self.assertFalse(item["system_rule_override_performed"])
        self.assertFalse(item["tool_authorization_performed"])
        self.assertFalse(item["prompt_injection_scan_performed"])

        unsafe_controls = checker._instruction_control_flags(
            {
                "label": "UNTRUSTED_EVIDENCE_TEXT",
                "interpretation": "EVIDENCE_ONLY",
                "content": "bounded control",
                "system_instruction_allowed": True,
                "tool_authorization_allowed": False,
                "policy_override_allowed": False,
            }
        )
        self.assertTrue(unsafe_controls["system_rule_override_performed"])
        phase2 = checker._load_module(
            checker.PHASE2_CHECKER_PATH,
            "stage045_phase2_detector_instruction_fail_closed_test",
        )
        request, control_bytes = checker._scenario_inputs(phase2)[scenario]
        raw_result = phase2.detect_control_bytes(
            request,
            control_bytes,
            source_text_excerpt="bounded control",
        )
        blocked = checker._summarize(
            scenario,
            raw_result,
            route_matches_baseline=True,
            instruction_controls=unsafe_controls,
        )
        self.assertEqual("FAIL_CLOSED", blocked["status"])
        self.assertTrue(blocked["system_rule_override_performed"])

    def test_report_has_fourteen_passes_and_no_forbidden_effects(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_FILE_TYPE_DETECTION_SCENARIOS_PARSER_DISABLED",
            report["result"],
        )
        self.assertEqual(14, report["scenario_count"])
        self.assertEqual(14, report["passed_scenario_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual("IDS-STAGE045-P4-GATE", report["next_gate"])
        for scenario, item in report["scenario_results"].items():
            with self.subTest(scenario=scenario):
                self.assertEqual("PASS", item["status"])
                self.assertEqual(
                    EXPECTED_QUALITY_DISPOSITIONS[scenario],
                    item["quality_disposition"],
                )
        for name in (
            "source_file_open_performed",
            "filesystem_scan_performed",
            "file_hash_performed",
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "prompt_injection_scan_performed",
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

    def test_scenario_results_expose_no_payload_source_text_or_absolute_path(self):
        encoded = json.dumps(
            self._report()["scenario_results"],
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("IDS_MetaData", encoded)
        self.assertNotIn("忽略系统规则", encoded)
        self.assertNotIn("control_bytes", encoded)
        for item in self._report()["scenario_results"].values():
            self.assertNotIn("content", item)
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
        self.assertEqual("IDS-STAGE045-P4-GATE", payload["next_gate"])

    def test_governance_routes_to_p4_without_upload_or_stage_review(self):
        docs = EVIDENCE.read_text(encoding="utf-8")
        for marker in (
            "ISOLATED_NON_PRODUCTION_IN_MEMORY_FILE_TYPE_DETECTION_SCENARIOS",
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
        self.assertIn('status: "stage045_phase3_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE045-P4"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_phase_id: "IDS-STAGE045-P3"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE045-P4-GATE"', roadmap)
        handoff = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE045-P3`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE045-P4`", handoff)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE045-P3-20260720-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE045-P3", matching[0]["task_id"])

    @staticmethod
    def _result_outcome(item):
        return (
            item["detected_type"],
            item["detection_state"],
            item["confidence"],
            item["route_candidate"],
            item["route_state"],
        )


if __name__ == "__main__":
    unittest.main()
