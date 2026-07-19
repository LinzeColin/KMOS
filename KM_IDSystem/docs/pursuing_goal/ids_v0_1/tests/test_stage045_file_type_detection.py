import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "file_type_detection" / "stage045_file_type_detection_contract.json"
ENTRY = BASE / "STAGE045_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE045_PHASE1_FILE_TYPE_DETECTION_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_file_type_detection.py"

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
        "STAGE-045_文件类型检测.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "V0_1_STAGE_EXECUTION_INDEX.csv"
    ),
    "source_index_sha256": (
        "2e0088153cd1e13a09d9aebd09a1bd0c8c7162acd0788360d45f5c7320af1e9a"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

PREDECESSOR_BINDING = {
    "stage044_review_commit": "97044d0b6475ebf41b4f79311164a392979305a0",
    "stage044_review_root_tree": "557791aa9f4694d80c221208b5e2dec7db6538ac",
    "stage044_review_kmids_tree": "eff34be6236b4ea3e89630961c510580aacf8259",
    "stage044_review_parent": "5da8fdf64cab35545e717900e71ccbbb5dacb11c",
    "stage044_review_status": "completed_reviewed_local",
    "stage044_review_result": "PASS_REVIEWED_LOCAL_DELETE_DISABLED",
}

UPSTREAM_BINDINGS = {
    "stage013_fingerprint_closeout_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE013_PHASE4_CLOSEOUT.md",
        "e3e8b27ccb286c91028c6ec9ce96859cc04032ceeafd80c21ea803ee19f82049",
    ),
    "stage027_reingest_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE027_PHASE1_SCOPE_BOUNDARY.md",
        "c9c09a7ab620377eb9de75a5f53e59fd0f4cb54caa22c030f615d3021f7661b7",
    ),
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage044_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE044_STAGE_REVIEW.md",
        "a8e3d765d7450146fc1649e330ad259966f4a446afdc847fc4790b73f1684916",
    ),
    "stage044_review_checker_ref": (
        "KM_IDSystem/scripts/check_half_product_cleanup_stage_review.py",
        "b67a633a20e801845c5b159a244e5e7817a3bc5c15669610becf0b65a47433e5",
    ),
    "raw_data_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/IDS_METADATA_RAW_DATA_BOUNDARY.md",
        "ad4695abf250049699a1b96b49b81432e5d5754dfe7de69c7f3056463a0a7d51",
    ),
}

CANONICAL_TYPES = [
    "PDF",
    "DOCX",
    "XLSX",
    "CSV",
    "TXT",
    "PNG",
    "JPEG",
    "TIFF",
    "UNKNOWN",
    "CORRUPT_OR_UNREADABLE",
]
DETECTION_STATES = [
    "TYPE_CONFIRMED",
    "TYPE_PROVISIONAL",
    "TYPE_CONFLICT_REVIEW_REQUIRED",
    "TYPE_UNKNOWN_REVIEW_REQUIRED",
    "TYPE_UNSUPPORTED",
    "TYPE_INPUT_BLOCKED",
]
PARSER_OUTPUT_FIELDS = [
    "text",
    "tables",
    "pages",
    "sections",
    "confidence",
    "errors",
]
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "file_scan_performed",
    "file_hash_performed",
    "extension_detection_performed",
    "mime_detection_performed",
    "file_signature_inspection_performed",
    "container_inspection_performed",
    "type_classification_runtime_performed",
    "parser_route_evaluation_performed",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "prompt_injection_scan_performed",
    "prompt_injection_marker_applied",
    "parser_output_produced",
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
    "app_reinstall_allowed",
}


class Stage045FileTypeDetectionTests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        spec = importlib.util.spec_from_file_location(
            "stage045_file_type_checker", CHECKER
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase1_artifacts_exist(self):
        for path in (CONTRACT, ENTRY, BOUNDARY, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_identity_source_predecessor_and_upstream_bindings_are_exact(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage045.file_type_detection.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-045", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE045-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-045", contract["acceptance_id"])
        self.assertEqual("D08-S001", contract["local_code"])
        self.assertEqual("D08", contract["domain"])
        self.assertEqual("IDS-STAGE045-P2-GATE", contract["next_gate"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["predecessor_binding"])
        observed = {
            name: (item["ref"], item["sha256"])
            for name, item in contract["upstream_bindings"].items()
        }
        self.assertEqual(UPSTREAM_BINDINGS, observed)

    def test_input_contract_is_bounded_reference_only_and_raw_root_blocked(self):
        value = self._contract()["input_contract"]
        self.assertEqual("REFERENCE_ONLY_STATIC_SCHEMA", value["mode"])
        self.assertEqual(
            [
                "detection_request_id",
                "source_fingerprint_ref",
                "source_identity_ref",
                "extension_signal",
                "mime_signal",
                "signature_signal",
                "detector_contract_version",
                "requested_at",
            ],
            value["required_fields"],
        )
        self.assertTrue(value["approved_explicit_source_required"])
        self.assertTrue(value["raw_metadata_boundary_blocked"])
        self.assertFalse(value["raw_source_body_allowed"])
        self.assertFalse(value["source_file_read_allowed"])

    def test_signal_contract_never_trusts_filename_and_handles_ooxml_safely(self):
        value = self._contract()["signal_contract"]
        self.assertEqual(
            ["FILE_SIGNATURE", "MIME_OBSERVATION", "FILENAME_EXTENSION"],
            value["trust_order"],
        )
        self.assertEqual("ADVISORY_ONLY", value["filename_extension_trust"])
        self.assertEqual(
            "PRIMARY_BUT_FORMAT_VALIDATION_REQUIRED",
            value["signature_trust"],
        )
        self.assertFalse(value["extension_only_route_allowed"])
        self.assertFalse(value["zip_magic_sufficient_for_ooxml"])
        self.assertEqual(["[Content_Types].xml", "word/"], value["docx_required_markers"])
        self.assertEqual(["[Content_Types].xml", "xl/"], value["xlsx_required_markers"])
        self.assertEqual("REVIEW_REQUIRED", value["signal_conflict_action"])
        self.assertFalse(value["remote_lookup_allowed"])

    def test_classification_is_explicit_and_unknowns_fail_closed(self):
        value = self._contract()["classification_contract"]
        self.assertEqual(CANONICAL_TYPES, value["canonical_type_values"])
        self.assertEqual(DETECTION_STATES, value["detection_states"])
        self.assertEqual(["HIGH", "MEDIUM", "LOW", "UNKNOWN"], value["confidence_values"])
        self.assertEqual("LOW", value["extension_only_max_confidence"])
        self.assertEqual(
            "OWNER_REVIEW_REQUIRED",
            value["unknown_or_conflict_action"],
        )
        self.assertFalse(value["filename_overrides_other_signals"])
        self.assertFalse(value["parser_dispatch_allowed"])
        self.assertFalse(value["format_registry_runtime_activated"])

    def test_parser_route_is_candidate_only_and_owned_by_stage046(self):
        value = self._contract()["parser_route_boundary"]
        self.assertEqual("STAGE-046", value["detailed_contract_owner"])
        self.assertEqual(
            {
                "PDF": "PDF_PARSER",
                "DOCX": "OOXML_WORD_PARSER",
                "XLSX": "OOXML_WORKBOOK_PARSER",
                "CSV": "DELIMITED_TEXT_PARSER",
                "TXT": "PLAIN_TEXT_PARSER",
                "PNG": "IMAGE_PARSER",
                "JPEG": "IMAGE_PARSER",
                "TIFF": "IMAGE_PARSER",
                "UNKNOWN": "UNSUPPORTED",
                "CORRUPT_OR_UNREADABLE": "UNSUPPORTED",
            },
            value["candidate_route_map"],
        )
        self.assertFalse(value["route_execution_allowed"])
        self.assertFalse(value["parser_execution_allowed"])
        self.assertFalse(value["direct_index_or_evidence_write_allowed"])

    def test_output_contract_preserves_required_fields_without_evidence_promotion(self):
        value = self._contract()["output_contract"]
        self.assertEqual("STAGE-047", value["detailed_contract_owner"])
        self.assertEqual(PARSER_OUTPUT_FIELDS, value["required_parser_output_fields"])
        self.assertTrue(value["content_fields_are_untrusted_evidence"])
        self.assertTrue(value["quality_gate_required"])
        self.assertTrue(value["provenance_required"])
        self.assertFalse(value["parser_output_write_allowed"])
        self.assertFalse(value["high_confidence_evidence_write_allowed"])
        self.assertFalse(value["empty_output_silent_success_allowed"])

    def test_fallback_is_explicit_non_silent_and_owned_by_stage048(self):
        value = self._contract()["fallback_contract"]
        self.assertEqual("STAGE-048", value["implementation_owner"])
        self.assertFalse(value["silent_drop_allowed"])
        self.assertFalse(value["silent_parser_switch_allowed"])
        self.assertTrue(value["attempt_errors_required"])
        self.assertEqual("OWNER_REVIEW_REQUIRED", value["low_confidence_action"])
        self.assertEqual(
            "UNSUPPORTED_OR_OWNER_REVIEW",
            value["unknown_type_action"],
        )
        self.assertFalse(value["fallback_execution_allowed"])

    def test_source_text_is_untrusted_and_cannot_become_system_instruction(self):
        value = self._contract()["prompt_injection_boundary"]
        self.assertEqual("STAGE-050", value["implementation_owner"])
        self.assertEqual(
            "UNTRUSTED_EVIDENCE_TEXT",
            value["source_derived_text_label"],
        )
        self.assertEqual(
            [
                "SYSTEM_INSTRUCTION",
                "TOOL_INSTRUCTION",
                "POLICY",
                "CONTROL_COMMAND",
            ],
            value["forbidden_interpretations"],
        )
        self.assertTrue(value["marker_required_before_downstream_model"])
        self.assertFalse(value["source_text_can_override_system_rules"])
        self.assertFalse(value["marker_application_allowed"])

    def test_quality_state_and_job_boundaries_block_all_side_effects(self):
        contract = self._contract()
        quality = contract["quality_and_evidence_boundary"]
        self.assertEqual("CANDIDATE", quality["parser_artifact_fact_level"])
        self.assertEqual(
            "BLOCK_DOWNSTREAM_PROMOTION",
            quality["unknown_or_missing_quality_action"],
        )
        for field in (
            "evidence_promotion_allowed",
            "evidence_ledger_write_allowed",
            "audit_write_allowed",
            "report_generation_allowed",
            "direct_index_write_allowed",
            "manifest_mutation_allowed",
            "original_mutation_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(quality[field])
        state = contract["state_and_job_boundary"]
        self.assertEqual("PARSE", state["job_type"])
        self.assertEqual("STAGE-037", state["state_model_owner"])
        self.assertFalse(state["job_creation_allowed"])
        self.assertFalse(state["state_transition_allowed"])
        self.assertFalse(state["terminal_history_change_allowed"])

    def test_truth_flags_are_complete_and_fail_closed(self):
        truth = self._contract()["truth_flags"]
        self.assertTrue(truth["taskpack_source_read_performed"])
        for name in FALSE_TRUTH_FLAGS:
            with self.subTest(flag=name):
                self.assertIn(name, truth)
                self.assertFalse(truth[name])

    def test_checker_accepts_exact_contract_and_rejects_tampering(self):
        checker = self._checker()
        original = self._contract()
        checks = checker.evaluate_contract(original)
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()), checks)
        mutations = []
        for mutate in (
            lambda item: item["signal_contract"].update({"extension_only_route_allowed": True}),
            lambda item: item["classification_contract"].update({"parser_dispatch_allowed": True}),
            lambda item: item["parser_route_boundary"].update({"route_execution_allowed": True}),
            lambda item: item["output_contract"].update({"high_confidence_evidence_write_allowed": True}),
            lambda item: item["fallback_contract"].update({"silent_drop_allowed": True}),
            lambda item: item["prompt_injection_boundary"].update({"source_text_can_override_system_rules": True}),
            lambda item: item["truth_flags"].update({"parser_execution_performed": True}),
        ):
            candidate = copy.deepcopy(original)
            mutate(candidate)
            mutations.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["unexpected_field"] = True
        mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertFalse(all(checker.evaluate_contract(candidate).values()))
        non_mapping = checker.evaluate_contract([])
        self.assertFalse(non_mapping["root_exact_shape"])
        self.assertFalse(non_mapping["nested_exact_shapes"])
        self.assertFalse(all(non_mapping.values()))

    def test_report_docs_and_governance_stop_at_phase1(self):
        report = self._checker().build_stage045_phase1_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_PHASE1_CONTRACT_DETECTION_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE045-P2-GATE", report["next_gate"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["parser_dispatch_allowed"])
        self.assertFalse(report["push_allowed"])
        docs = ENTRY.read_text(encoding="utf-8") + BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "Phase 2 must run separately",
            "NO_PHASE2",
            "NO_SOURCE_FILE_OPEN",
            "NO_FILE_TYPE_RUNTIME",
            "NO_PARSER_ROUTE_EXECUTION",
            "NO_PARSER_EXECUTION",
            "NO_FALLBACK_EXECUTION",
            "NO_EVIDENCE_PROMOTION",
            "NO_RAW_METADATA_ACCESS",
            "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage045_phase1_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE045-P2"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE045"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE045-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE045-P2-GATE"', roadmap)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE045-P1-20260719-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE045-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-045"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
