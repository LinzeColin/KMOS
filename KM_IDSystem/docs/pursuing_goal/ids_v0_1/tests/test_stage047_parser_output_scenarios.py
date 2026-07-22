import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = (
    BASE
    / "parser_output"
    / "stage047_parser_output_scenarios_contract.json"
)
EVIDENCE = BASE / "STAGE047_PHASE3_PARSER_OUTPUT_SCENARIOS.md"
CHECKER = ROOT / "scripts" / "check_parser_output_scenarios.py"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = ROOT / "docs" / "HANDOFF.md"

SOURCE_BINDING = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-047_解析器输出合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
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

PHASE2_BINDING = {
    "commit": "65b81389e24d9ae371f464dcd6321784b9078d8b",
    "root_tree": "a66f59a71bd8c41ba122e0415f126d7cea6d8375",
    "kmids_tree": "eb2be74f3138221f39f4aab5e513c5fc8b03d984",
    "parent": "7d44f72c6a5d50e9042b8af1f588cd40e1caf4f3",
    "required_ancestor_of_head": True,
}

PHASE2_ARTIFACTS = {
    "stage047_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE047_PHASE2_PARSER_OUTPUT_SLICE.md"
        ),
        "sha256": (
            "4ec0b012ac3de8ae08b9359158d61df84e7a351ea39ede9d641deeeb328e7a9e"
        ),
    },
    "stage047_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/"
            "stage047_parser_output_runtime_contract.json"
        ),
        "sha256": (
            "16f4e8c5be806e835b686359f06ac32b4c069cb4441b0394ff53dda1e82b5ddc"
        ),
    },
    "stage047_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_output_runtime.py",
        "sha256": (
            "02b42621c89110c67a99e2a0d87ecd7b9a58f4cbf36725a7812b69a55de84be7"
        ),
    },
    "stage047_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage047_parser_output_runtime.py"
        ),
        "sha256": (
            "66241bf92a40b85abf37483bca562564ed27fb366789ecd08d0c228c70b4cf03"
        ),
    },
    "stage047_phase2_run": {
        "ref": (
            "KM_IDSystem/machine/runs/"
            "2026-07-23-stage047-p2-local.json"
        ),
        "sha256": (
            "b6f23424d6253bcdd9249e252c94263ae0c874cc4398238532ef41a7e1417db7"
        ),
    },
}

UPSTREAM_ROUTE_BASELINE = {
    "snapshot_commit": PHASE2_BINDING["commit"],
    "checker_ref": "KM_IDSystem/scripts/check_parser_routing_scenarios.py",
    "checker_sha256": (
        "5ab854480b0b079d848a6ff2c0cbd5808e9bbf529f7c34169d503c3084074b51"
    ),
    "contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_scenarios_contract.json"
    ),
    "contract_sha256": (
        "eef1c03bf3abd2a95bb0294b2b8671a61e3fd29f77e3495b2a118941b979c8a2"
    ),
    "run_ref": (
        "KM_IDSystem/machine/runs/2026-07-22-stage046-p3-local.json"
    ),
    "run_sha256": (
        "0c2d919db3db91f03e4e266bb5ea0f2bfb2ce1101b47deff40e69d43f95fafff"
    ),
    "expected_result": (
        "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED"
    ),
}

FORMAT_CONTROL_ROUTES = {
    "PDF": (
        "ROUTE_PDF",
        "PDF_PARSER",
        "ids.parser.control_fixture.pdf.v0_1.stage047.p3",
    ),
    "DOCX": (
        "ROUTE_OOXML_WORD",
        "OOXML_WORD_PARSER",
        "ids.parser.control_fixture.docx.v0_1.stage047.p3",
    ),
    "XLSX": (
        "ROUTE_OOXML_WORKBOOK",
        "OOXML_WORKBOOK_PARSER",
        "ids.parser.control_fixture.xlsx.v0_1.stage047.p3",
    ),
    "CSV": (
        "ROUTE_DELIMITED_TEXT",
        "DELIMITED_TEXT_PARSER",
        "ids.parser.control_fixture.csv.v0_1.stage047.p3",
    ),
    "TXT": (
        "ROUTE_PLAIN_TEXT",
        "PLAIN_TEXT_PARSER",
        "ids.parser.control_fixture.v0_1.stage047.p2",
    ),
    "PNG": (
        "ROUTE_IMAGE",
        "IMAGE_PARSER",
        "ids.parser.control_fixture.image.v0_1.stage047.p3",
    ),
    "JPEG": (
        "ROUTE_IMAGE",
        "IMAGE_PARSER",
        "ids.parser.control_fixture.image.v0_1.stage047.p3",
    ),
    "TIFF": (
        "ROUTE_IMAGE",
        "IMAGE_PARSER",
        "ids.parser.control_fixture.image.v0_1.stage047.p3",
    ),
}

SCENARIOS = [
    "pdf_preparsed_pages_candidate",
    "docx_preparsed_sections_candidate",
    "xlsx_preparsed_table_candidate_formula_preserved",
    "csv_preparsed_table_candidate",
    "txt_preparsed_text_candidate",
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "instruction_like_text_cannot_override_policy",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
]

EXPECTED_STATUS_COUNTS = {
    "OUTPUT_CANDIDATE_NOT_VALIDATED": 6,
    "OUTPUT_PARTIAL_REVIEW_REQUIRED": 4,
    "OUTPUT_FAILED_EXPLICIT": 1,
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage047ParserOutputScenarioTests(unittest.TestCase):
    def _checker(self):
        return _load_module(CHECKER, "stage047_parser_output_scenarios_checker")

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_artifacts_exist(self):
        for path in (CONTRACT, EVIDENCE, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_identity_source_phase2_and_upstream_bindings_are_exact(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage047.parser_output.phase3.scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-047", contract["stage"])
        self.assertEqual("Phase 3", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE047-P3", contract["task_id"])
        self.assertEqual("ACC-STAGE-047", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE047-P4-GATE", contract["next_gate"])
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PHASE2_BINDING, contract["phase2_commit_binding"])
        self.assertEqual(PHASE2_ARTIFACTS, contract["phase2_artifact_bindings"])
        self.assertEqual(
            UPSTREAM_ROUTE_BASELINE,
            contract["upstream_route_baseline"],
        )

    def test_contract_catalog_metrics_adapter_and_gate_are_exact(self):
        contract = self._contract()
        self.assertEqual(SCENARIOS, contract["scenario_catalog"])
        self.assertEqual(
            list(FORMAT_CONTROL_ROUTES),
            contract["format_coverage"]["supported_types"],
        )
        self.assertEqual(16, contract["result_contract"]["scenario_count"])
        self.assertEqual(11, contract["result_contract"]["accepted_output_count"])
        self.assertEqual(EXPECTED_STATUS_COUNTS, contract["result_contract"]["status_counts"])
        self.assertEqual(
            "SYNTHETIC_FORMAT_LABELED_PREPARSED_CONTROL_NOT_RUNTIME_PARSER",
            contract["format_control_adapter"]["adapter_state"],
        )
        self.assertFalse(
            contract["format_control_adapter"]["parser_execution_allowed"]
        )
        self.assertEqual(
            "IDS-STAGE047-P4-GATE",
            contract["phase4_entry_gate"]["next_gate"],
        )
        self.assertTrue(contract["phase4_entry_gate"]["must_run_separately"])
        self.assertFalse(contract["phase4_entry_gate"]["github_upload_allowed"])

    def test_contract_and_all_live_bindings_fail_closed_on_tampering(self):
        checker = self._checker()
        contract = self._contract()
        checks = checker.validate_scenario_contract(contract)
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()), checks)
        tampered = copy.deepcopy(contract)
        tampered["runtime_boundary"]["parser_execution_allowed"] = True
        self.assertFalse(all(checker.validate_scenario_contract(tampered).values()))
        tampered = copy.deepcopy(contract)
        tampered["phase2_commit_binding"]["commit"] = "0" * 40
        self.assertFalse(all(checker.validate_scenario_contract(tampered).values()))

    def test_source_phase2_and_upstream_route_baseline_are_live(self):
        checker = self._checker()
        self.assertTrue(checker.source_live())
        self.assertTrue(checker.phase2_commit_live())
        self.assertTrue(checker.phase2_artifacts_live())
        self.assertTrue(checker.upstream_route_baseline_live())

    def test_phase2_default_control_and_report_remain_backward_compatible(self):
        checker = self._checker()
        phase2 = checker.load_phase2_checker()
        wrapper = phase2.build_control_input(
            suffix="a",
            evidence_marker=True,
            requested_at="2026-07-23T01:00:00Z",
        )
        self.assertTrue(phase2.validate_input_wrapper(wrapper))
        self.assertEqual("TXT", wrapper["routing_request"]["detected_type"])
        self.assertEqual("ROUTE_PLAIN_TEXT", wrapper["route_result"]["candidate_route_id"])
        self.assertEqual(
            "ids.parser.control_fixture.v0_1.stage047.p2",
            wrapper["route_result"]["parser_version"],
        )
        self.assertTrue(phase2.build_stage047_phase2_report()["valid"])

    def test_format_control_inputs_bind_all_eight_governed_types(self):
        checker = self._checker()
        phase2 = checker.load_phase2_checker()
        for index, (detected_type, expected) in enumerate(
            FORMAT_CONTROL_ROUTES.items(), start=1
        ):
            with self.subTest(detected_type=detected_type):
                wrapper = checker.build_format_control_input(
                    detected_type=detected_type,
                    suffix=f"{index:x}",
                    requested_at=f"2026-07-23T02:{index:02d}:00Z",
                )
                self.assertTrue(phase2.validate_input_wrapper(wrapper))
                self.assertEqual(
                    detected_type,
                    wrapper["routing_request"]["detected_type"],
                )
                self.assertEqual(expected[0], wrapper["route_result"]["candidate_route_id"])
                self.assertEqual(expected[1], wrapper["route_result"]["parser_family"])
                self.assertEqual(expected[2], wrapper["route_result"]["parser_version"])

    def test_supported_format_scenarios_emit_candidate_or_partial_controls(self):
        checker = self._checker()
        expected = {
            "pdf_preparsed_pages_candidate": ("PDF", "OUTPUT_CANDIDATE_NOT_VALIDATED"),
            "docx_preparsed_sections_candidate": ("DOCX", "OUTPUT_CANDIDATE_NOT_VALIDATED"),
            "xlsx_preparsed_table_candidate_formula_preserved": ("XLSX", "OUTPUT_CANDIDATE_NOT_VALIDATED"),
            "csv_preparsed_table_candidate": ("CSV", "OUTPUT_CANDIDATE_NOT_VALIDATED"),
            "txt_preparsed_text_candidate": ("TXT", "OUTPUT_CANDIDATE_NOT_VALIDATED"),
            "png_preparsed_image_partial_review": ("PNG", "OUTPUT_PARTIAL_REVIEW_REQUIRED"),
            "jpeg_preparsed_image_partial_review": ("JPEG", "OUTPUT_PARTIAL_REVIEW_REQUIRED"),
            "tiff_preparsed_image_partial_review": ("TIFF", "OUTPUT_PARTIAL_REVIEW_REQUIRED"),
        }
        for scenario_id, (detected_type, output_status) in expected.items():
            with self.subTest(scenario_id=scenario_id):
                result = checker.run_scenario(scenario_id)
                self.assertEqual("PASS", result["status"])
                self.assertTrue(result["accepted"])
                self.assertEqual(detected_type, result["detected_type"])
                self.assertEqual(output_status, result["output_status"])
                self.assertTrue(result["output_id"].startswith("parser-output:sha256:"))
                self.assertTrue(result["explicit_disposition"])
                self.assertFalse(result["silent_drop"])

    def test_xlsx_formula_text_is_preserved_but_never_executed(self):
        result = self._checker().run_scenario(
            "xlsx_preparsed_table_candidate_formula_preserved"
        )
        self.assertTrue(result["formula_text_preserved"])
        self.assertFalse(result["formula_execution_performed"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", result["content_label"])

    def test_image_controls_are_partial_and_require_quality_review(self):
        checker = self._checker()
        for scenario_id in (
            "png_preparsed_image_partial_review",
            "jpeg_preparsed_image_partial_review",
            "tiff_preparsed_image_partial_review",
        ):
            with self.subTest(scenario_id=scenario_id):
                result = checker.run_scenario(scenario_id)
                self.assertEqual("OUTPUT_PARTIAL_REVIEW_REQUIRED", result["output_status"])
                self.assertEqual("QUALITY_REVIEW_REQUIRED_NO_FALLBACK", result["fallback_disposition"])
                self.assertEqual("REVIEW_REQUIRED", result["quality_gate_state"])

    def test_unknown_and_corrupt_routes_never_construct_output(self):
        checker = self._checker()
        expected = {
            "unknown_route_requires_owner_review_no_output": (
                "OWNER_REVIEW_REQUIRED_STAGE048_NOT_RUN",
                "ROUTE_REVIEW_REQUIRED",
            ),
            "corrupt_route_blocks_explicit_no_output": (
                "EXPLICIT_ROUTE_ERROR_STAGE048_NOT_RUN",
                "ROUTE_BLOCKED",
            ),
        }
        for scenario_id, (disposition, route_action) in expected.items():
            with self.subTest(scenario_id=scenario_id):
                result = checker.run_scenario(scenario_id)
                self.assertEqual("PASS", result["status"])
                self.assertFalse(result["accepted"])
                self.assertIsNone(result["output_id"])
                self.assertEqual(route_action, result["upstream_route_action"])
                self.assertEqual(disposition, result["fallback_disposition"])
                self.assertFalse(result["silent_drop"])

    def test_low_quality_and_explicit_failure_have_exact_dispositions(self):
        checker = self._checker()
        low = checker.run_scenario("low_quality_txt_output_requires_review")
        failed = checker.run_scenario("explicit_parser_failure_output_blocked")
        self.assertTrue(low["accepted"])
        self.assertEqual("OUTPUT_PARTIAL_REVIEW_REQUIRED", low["output_status"])
        self.assertEqual("REVIEW_REQUIRED", low["quality_gate_state"])
        self.assertTrue(failed["accepted"])
        self.assertEqual("OUTPUT_FAILED_EXPLICIT", failed["output_status"])
        self.assertEqual("BLOCKED", failed["quality_gate_state"])
        self.assertEqual("EXPLICIT_FAILURE_NO_FALLBACK", failed["fallback_disposition"])

    def test_instruction_like_text_cannot_override_ids_policy(self):
        result = self._checker().run_scenario(
            "instruction_like_text_cannot_override_policy"
        )
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["route_matches_non_instruction_baseline"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", result["content_label"])
        self.assertEqual("EVIDENCE_ONLY", result["content_interpretation"])
        self.assertFalse(result["system_rule_override_performed"])
        self.assertFalse(result["tool_authorization_performed"])
        self.assertFalse(result["prompt_injection_scan_performed"])

    def test_invalid_lineage_rejection_is_sanitized(self):
        result = self._checker().run_scenario(
            "invalid_lineage_rejected_sanitized"
        )
        self.assertEqual("PASS", result["status"])
        self.assertFalse(result["accepted"])
        self.assertEqual("OUTPUT_REJECTED_FAIL_CLOSED", result["normalization_result_code"])
        self.assertTrue(result["rejection_sanitized"])
        self.assertFalse(result["unsafe_input_echoed"])

    def test_malformed_references_and_empty_output_fail_closed(self):
        checker = self._checker()
        for scenario_id in (
            "malformed_nested_references_rejected",
            "empty_without_error_rejected",
        ):
            with self.subTest(scenario_id=scenario_id):
                result = checker.run_scenario(scenario_id)
                self.assertEqual("PASS", result["status"])
                self.assertFalse(result["accepted"])
                self.assertIsNone(result["output_id"])
                self.assertEqual(
                    "OUTPUT_REJECTED_FAIL_CLOSED",
                    result["normalization_result_code"],
                )

    def test_upstream_route_replay_covers_taskpack_formats_and_failures(self):
        report = self._checker().build_stage047_phase3_report()
        replay = report["upstream_route_replay"]
        self.assertTrue(replay["valid"])
        self.assertEqual(14, replay["scenario_count"])
        self.assertEqual(14, replay["passed_scenario_count"])
        self.assertEqual(8, replay["supported_type_count"])
        self.assertTrue(replay["unknown_route_explicit"])
        self.assertTrue(replay["corrupt_route_explicit"])

    def test_report_metrics_results_and_truth_are_exact(self):
        checker = self._checker()
        report = checker.build_stage047_phase3_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_PARSER_OUTPUT_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(16, report["scenario_count"])
        self.assertEqual(16, report["passed_scenario_count"])
        self.assertEqual(11, report["accepted_output_count"])
        self.assertEqual(3, report["rejected_output_count"])
        self.assertEqual(2, report["route_no_output_count"])
        self.assertEqual(EXPECTED_STATUS_COUNTS, report["status_counts"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual("IDS-STAGE047-P4-GATE", report["next_gate"])
        self.assertFalse(report["phase4_started"])
        self.assertFalse(report["push_allowed"])
        self.assertEqual(set(SCENARIOS), set(report["scenario_results"]))

    def test_truth_flags_limit_claims_to_synthetic_in_memory_scenarios(self):
        checker = self._checker()
        contract = self._contract()
        truth = contract["truth_flags"]
        self.assertEqual(checker.TRUE_TRUTH_FLAGS | checker.FALSE_TRUTH_FLAGS, set(truth))
        self.assertTrue(all(truth[name] is True for name in checker.TRUE_TRUTH_FLAGS))
        self.assertTrue(all(truth[name] is False for name in checker.FALSE_TRUTH_FLAGS))

    def test_governance_and_docs_stop_at_phase4_gate(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        evidence = EVIDENCE.read_text(encoding="utf-8")
        for text in (batch, roadmap):
            self.assertIn("IDS-V0_1-STAGE047-P3", text)
            self.assertIn("IDS-STAGE047-P4-GATE", text)
            self.assertIn("phase4_entry_authorized: false", text)
            self.assertIn("push_allowed: false", text)
        self.assertIn("EVT-IDS-V0_1-STAGE047-P3-20260723-001", events)
        self.assertIn("Completed task in this run: `IDS-V0_1-STAGE047-P3`", handoff)
        self.assertIn("Next allowed task: `IDS-V0_1-STAGE047-P4`", handoff)
        for marker in (
            "SYNTHETIC_FORMAT_LABELED_PREPARSED_CONTROL",
            "NO_REAL_SOURCE_FILE_READ",
            "NO_PARSER_EXECUTION",
            "NO_FALLBACK_EXECUTION",
            "NO_PHASE4_THIS_RUN",
            "NO_STAGE_REVIEW_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            self.assertIn(marker, evidence)


if __name__ == "__main__":
    unittest.main()
