import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "parser_output" / "stage047_parser_output_contract.json"
ENTRY = BASE / "STAGE047_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE047_PHASE1_PARSER_OUTPUT_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_parser_output.py"

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
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
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
    "stage046_review_commit": "c7d66380cfab7cf00ccbb9af34ef43a7f44a7bde",
    "stage046_review_root_tree": "455b675a23243a8978b332e07e4a4cadcc532038",
    "stage046_review_kmids_tree": "98d21d245ccee585795cbc6e6180a8fcafda7f75",
    "stage046_review_parent": "5dee024cd44e2e772776487ee21761f274c7708e",
    "stage046_review_status": "completed_reviewed_local",
    "stage046_review_result": (
        "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
    ),
}

UPSTREAM_BINDINGS = {
    "stage045_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
        "stage045_file_type_detection_delivery_contract.json",
        "209c13f67d457419c8760841f13f401f3d8acec2ec7a72c5c13e0f4722b6c743",
    ),
    "stage046_phase1_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_contract.json",
        "5c145dba0ba2246b6daa33da0098b4b2ee2a48a53cfec993261d70596706c1fd",
    ),
    "stage046_phase2_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_runtime_contract.json",
        "d1772c08581d04a9b7932f1a74fcfe44877056973df559c2396fb69f9b1e3aab",
    ),
    "stage046_phase3_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_scenarios_contract.json",
        "eef1c03bf3abd2a95bb0294b2b8671a61e3fd29f77e3495b2a118941b979c8a2",
    ),
    "stage046_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_delivery_contract.json",
        "18629486122178a169ae88e54559d3166f73a19c1652011643ee88b4ae3e9dc0",
    ),
    "stage046_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE046_STAGE_REVIEW.md",
        "f946ffdecb1a896065f7a3a66e1a6a38a52df445b3ef6b5fab4d310aa86362a2",
    ),
    "stage046_review_checker_ref": (
        "KM_IDSystem/scripts/check_parser_routing_stage_review.py",
        "61a84f278b0db213e7cd28021cb16daeecc76c21bbb17cde547eb6286df43053",
    ),
    "stage046_review_run_ref": (
        "KM_IDSystem/machine/runs/2026-07-22-stage046-review-local.json",
        "f33f1d06dc569ffe996167df373ec108abb4e129b7104c8ace2fa13d1776f719",
    ),
    "raw_data_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "IDS_METADATA_RAW_DATA_BOUNDARY.md",
        "ad4695abf250049699a1b96b49b81432e5d5754dfe7de69c7f3056463a0a7d51",
    ),
}

CORE_FIELDS = ["text", "tables", "pages", "sections", "confidence", "errors"]
ENVELOPE_FIELDS = [
    "output_id",
    "output_schema_version",
    "route_result_id",
    "routing_request_id",
    "detection_result_id",
    "source_identity_ref",
    "parser_family",
    "parser_version",
    "status",
    *CORE_FIELDS,
    "content_security",
    "quality_gate",
    "produced_at",
]

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "route_evaluation_performed",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "parser_output_produced",
    "fallback_execution_performed",
    "differential_evaluation_performed",
    "prompt_injection_scan_performed",
    "prompt_injection_marker_applied",
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
    "phase2_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
}


class Stage047ParserOutputTests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        spec = importlib.util.spec_from_file_location(
            "stage047_parser_output_checker", CHECKER
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase1_artifacts_exist(self):
        for path in (CONTRACT, ENTRY, BOUNDARY, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_identity_source_predecessor_and_snapshot_bindings_are_exact(self):
        contract = self._contract()
        self.assertEqual("ids.stage047.parser_output.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-047", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE047-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-047", contract["acceptance_id"])
        self.assertEqual("D08-S003", contract["local_code"])
        self.assertEqual("D08", contract["domain"])
        self.assertEqual("IDS-STAGE047-P2-GATE", contract["next_gate"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["predecessor_binding"])
        observed = {
            name: (item["ref"], item["sha256"])
            for name, item in contract["upstream_snapshot_bindings"].items()
        }
        self.assertEqual(UPSTREAM_BINDINGS, observed)
        self.assertTrue(
            all(
                item["snapshot_commit"]
                == PREDECESSOR_BINDING["stage046_review_commit"]
                for item in contract["upstream_snapshot_bindings"].values()
            )
        )

    def test_input_and_envelope_bind_stage045_detection_and_stage046_route(self):
        contract = self._contract()
        incoming = contract["input_boundary"]
        self.assertEqual(
            "REFERENCE_ONLY_STAGE046_ROUTING_REQUEST_AND_RESULT",
            incoming["mode"],
        )
        self.assertIn("routing_request", incoming["required_wrapper_fields"])
        self.assertTrue(incoming["routing_request_identity_required"])
        self.assertTrue(incoming["request_result_lineage_match_required"])
        self.assertEqual("STAGE-045", incoming["detection_authority"])
        self.assertEqual("STAGE-046", incoming["route_authority"])
        self.assertTrue(incoming["result_identity_required"])
        self.assertTrue(incoming["source_identity_match_required"])
        self.assertFalse(incoming["source_body_or_path_allowed"])
        envelope = contract["output_envelope_contract"]
        self.assertEqual(ENVELOPE_FIELDS, envelope["required_fields"])
        self.assertFalse(envelope["additional_fields_allowed"])
        self.assertEqual(
            "ids.parser_output.v0_1.stage047.p1",
            envelope["required_output_schema_version"],
        )
        self.assertEqual(
            [
                "OUTPUT_CANDIDATE_NOT_VALIDATED",
                "OUTPUT_PARTIAL_REVIEW_REQUIRED",
                "OUTPUT_FAILED_EXPLICIT",
            ],
            envelope["allowed_statuses"],
        )
        self.assertTrue(envelope["produced_at_not_before_requested_at"])

    def test_six_core_fields_have_exact_fail_closed_shapes(self):
        core = self._contract()["core_output_contract"]
        self.assertEqual(CORE_FIELDS, core["required_fields"])
        self.assertFalse(core["additional_core_fields_allowed"])
        fields = core["field_contracts"]
        self.assertEqual("STRING_OR_NULL", fields["text"]["type"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", fields["text"]["trust_label"])
        self.assertFalse(fields["text"]["instruction_interpretation_allowed"])
        for name, schema_ref in (
            ("tables", "ids.parser_output.table.v0_1"),
            ("pages", "ids.parser_output.page.v0_1"),
            ("sections", "ids.parser_output.section.v0_1"),
        ):
            with self.subTest(name=name):
                self.assertEqual("ARRAY", fields[name]["type"])
                self.assertEqual(schema_ref, fields[name]["item_schema_ref"])
                self.assertTrue(fields[name]["item_ids_unique"])
        self.assertEqual("ENUM", fields["confidence"]["type"])
        self.assertEqual(
            ["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
            fields["confidence"]["allowed_values"],
        )
        self.assertFalse(fields["confidence"]["numeric_thresholds_assigned"])
        self.assertEqual("ARRAY", fields["errors"]["type"])
        self.assertEqual(
            "ids.parser_output.safe_error.v0_1",
            fields["errors"]["item_schema_ref"],
        )
        self.assertFalse(fields["errors"]["raw_exception_allowed"])
        self.assertFalse(fields["errors"]["business_content_echo_allowed"])

    def test_nested_items_lineage_and_empty_output_rules_are_explicit(self):
        contract = self._contract()
        item_schemas = contract["item_schema_contracts"]
        self.assertEqual(
            ["table_id", "page_refs", "section_ref", "cells", "confidence", "errors"],
            item_schemas["table"]["required_fields"],
        )
        self.assertEqual(
            ["page_id", "page_number", "text", "table_refs", "confidence", "errors"],
            item_schemas["page"]["required_fields"],
        )
        self.assertEqual(
            [
                "section_id",
                "title",
                "level",
                "page_refs",
                "text",
                "table_refs",
                "confidence",
                "errors",
            ],
            item_schemas["section"]["required_fields"],
        )
        self.assertEqual(
            ["code", "severity", "retryable", "message_key"],
            item_schemas["safe_error"]["required_fields"],
        )
        lineage = contract["lineage_and_integrity_contract"]
        self.assertTrue(lineage["route_detection_source_identity_chain_required"])
        self.assertTrue(lineage["all_internal_references_must_resolve"])
        self.assertTrue(lineage["reciprocal_table_page_references_required"])
        self.assertTrue(
            lineage["reciprocal_table_section_references_required"]
        )
        self.assertTrue(lineage["duplicate_item_ids_rejected"])
        self.assertTrue(lineage["orphan_page_section_or_table_refs_rejected"])
        self.assertFalse(lineage["filesystem_path_or_uri_reference_allowed"])
        completeness = contract["completion_and_error_contract"]
        self.assertTrue(completeness["empty_candidate_without_error_rejected"])
        self.assertTrue(completeness["partial_or_failed_requires_safe_error"])
        self.assertTrue(completeness["unknown_confidence_blocks_promotion"])
        self.assertFalse(completeness["silent_success_allowed"])

    def test_quality_evidence_fallback_and_prompt_boundaries_remain_closed(self):
        contract = self._contract()
        quality = contract["quality_and_evidence_boundary"]
        self.assertEqual("CANDIDATE", quality["parser_content_fact_level"])
        self.assertEqual("UNASSESSED", quality["initial_quality_gate_state"])
        self.assertTrue(quality["quality_gate_required_before_downstream"])
        self.assertEqual("BLOCK_DOWNSTREAM_PROMOTION", quality["missing_quality_action"])
        self.assertFalse(quality["direct_high_trust_evidence_write_allowed"])
        self.assertFalse(quality["evidence_ledger_write_allowed"])
        fallback = contract["fallback_boundary"]
        self.assertEqual("STAGE-048", fallback["runtime_owner"])
        self.assertFalse(fallback["silent_drop_allowed"])
        self.assertFalse(fallback["silent_parser_switch_allowed"])
        self.assertFalse(fallback["execution_allowed"])
        prompt = contract["prompt_injection_boundary"]
        self.assertEqual("STAGE-050", prompt["runtime_owner"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", prompt["required_content_label"])
        self.assertEqual("REQUIRED_NOT_APPLIED", prompt["phase1_marker_state"])
        self.assertFalse(prompt["content_can_override_system_rules"])
        self.assertFalse(prompt["content_can_authorize_tools"])
        self.assertFalse(prompt["scan_or_marker_application_allowed"])

    def test_truth_flags_are_complete_and_runtime_false(self):
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
            lambda item: item["input_boundary"].update({"source_body_or_path_allowed": True}),
            lambda item: item["output_envelope_contract"].update({"additional_fields_allowed": True}),
            lambda item: item["core_output_contract"]["field_contracts"]["errors"].update({"raw_exception_allowed": True}),
            lambda item: item["lineage_and_integrity_contract"].update({"all_internal_references_must_resolve": False}),
            lambda item: item["completion_and_error_contract"].update({"silent_success_allowed": True}),
            lambda item: item["quality_and_evidence_boundary"].update({"direct_high_trust_evidence_write_allowed": True}),
            lambda item: item["prompt_injection_boundary"].update({"content_can_authorize_tools": True}),
            lambda item: item["truth_flags"].update({"parser_output_produced": True}),
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

    def test_checker_live_source_predecessor_and_snapshots_are_valid(self):
        checker = self._checker()
        self.assertTrue(checker.live_source_valid())
        self.assertTrue(checker.predecessor_valid())
        self.assertTrue(checker.upstream_snapshot_valid())

    def test_report_docs_and_governance_stop_at_phase1(self):
        report = self._checker().build_stage047_phase1_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_PHASE1_PARSER_OUTPUT_CONTRACT_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE047-P2-GATE", report["next_gate"])
        self.assertEqual(6, report["required_core_field_count"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["parser_execution_allowed"])
        self.assertFalse(report["push_allowed"])
        docs = ENTRY.read_text(encoding="utf-8") + BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "Phase 2 must run separately",
            "NO_PHASE2",
            "NO_SOURCE_FILE_OPEN",
            "NO_PARSER_EXECUTION",
            "NO_PARSER_OUTPUT_RUNTIME",
            "NO_FALLBACK_EXECUTION",
            "NO_PROMPT_INJECTION_SCAN_OR_MARKER_RUNTIME",
            "NO_EVIDENCE_PROMOTION",
            "NO_RAW_METADATA_ACCESS",
            "NO_FAKE_IDS_BUSINESS_DATA",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage047_phase1_completed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE047-P1"', batch)
        self.assertIn('next_gate: "IDS-STAGE047-P2-GATE"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE047-P2"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE047"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE047-P1"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE047-P2-GATE"', roadmap)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE047-P1-20260722-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE047-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-047"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
