import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CONTRACT = BASE / "parser_routing" / "stage046_parser_routing_contract.json"
ENTRY = BASE / "STAGE046_ENTRY_CONTRACT.md"
BOUNDARY = BASE / "STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_parser_routing.py"

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
        "STAGE-046_解析器路由合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_integrity": "OK",
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
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
    "stage045_review_commit": "76027b8dc89e325c212d492d7f5df88357ea7112",
    "stage045_review_root_tree": "37541fb276b548322227969fd36aadf40144e3e3",
    "stage045_review_kmids_tree": "ef8dafd9cd6e19967b7964f88e6eeead25b1866b",
    "stage045_review_parent": "02a3393766b3ba933383af415100ffe5e78c7630",
    "stage045_review_status": "completed_reviewed_local",
    "stage045_review_result": (
        "PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED"
    ),
}

UPSTREAM_BINDINGS = {
    "stage045_file_type_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
        "stage045_file_type_detection_contract.json",
        "6f3926cd87ee3a654384176516db1d4f7e83e0906a220057d33d6873be8a506f",
    ),
    "stage045_delivery_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/"
        "stage045_file_type_detection_delivery_contract.json",
        "209c13f67d457419c8760841f13f401f3d8acec2ec7a72c5c13e0f4722b6c743",
    ),
    "stage045_review_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE045_STAGE_REVIEW.md",
        "7dc6cc5c73a6c243ac457bf76af84f58dbee14ed9371d467b14158057d263116",
    ),
    "stage045_review_checker_ref": (
        "KM_IDSystem/scripts/check_file_type_detection_stage_review.py",
        "ad9946e6db7303ac38f84927f3d4d51eba576cce545a8b4e75ff1e3b333cf977",
    ),
    "stage045_review_run_ref": (
        "KM_IDSystem/machine/runs/2026-07-20-stage045-review-local.json",
        "b78081cc37aee5c05e18a9942a1f9e0086348881fd4562743397bbac7b258c78",
    ),
    "stage037_state_index_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "raw_data_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "IDS_METADATA_RAW_DATA_BOUNDARY.md",
        "ad4695abf250049699a1b96b49b81432e5d5754dfe7de69c7f3056463a0a7d51",
    ),
}

ROUTE_REGISTRY = [
    {
        "route_id": "ROUTE_PDF",
        "accepted_types": ["PDF"],
        "parser_family": "PDF_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_OOXML_WORD",
        "accepted_types": ["DOCX"],
        "parser_family": "OOXML_WORD_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_OOXML_WORKBOOK",
        "accepted_types": ["XLSX"],
        "parser_family": "OOXML_WORKBOOK_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_DELIMITED_TEXT",
        "accepted_types": ["CSV"],
        "parser_family": "DELIMITED_TEXT_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_PLAIN_TEXT",
        "accepted_types": ["TXT"],
        "parser_family": "PLAIN_TEXT_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
    {
        "route_id": "ROUTE_IMAGE",
        "accepted_types": ["PNG", "JPEG", "TIFF"],
        "parser_family": "IMAGE_PARSER",
        "selection_status": "CANDIDATE_ONLY_NOT_EXECUTED",
    },
]

OUTPUT_FIELDS = ["text", "tables", "pages", "sections", "confidence", "errors"]

FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "source_file_open_performed",
    "file_type_redetection_performed",
    "parser_registry_runtime_loaded",
    "parser_route_evaluation_performed",
    "parser_selected",
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
    "phase2_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}


class Stage046ParserRoutingTests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        spec = importlib.util.spec_from_file_location(
            "stage046_parser_routing_checker", CHECKER
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
        self.assertEqual("ids.stage046.parser_routing.phase1.v1", contract["schema_version"])
        self.assertEqual("STAGE-046", contract["stage"])
        self.assertEqual("Phase 1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE046-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-046", contract["acceptance_id"])
        self.assertEqual("D08-S002", contract["local_code"])
        self.assertEqual("D08", contract["domain"])
        self.assertEqual("IDS-STAGE046-P2-GATE", contract["next_gate"])
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
                item["snapshot_commit"] == PREDECESSOR_BINDING["stage045_review_commit"]
                for item in contract["upstream_snapshot_bindings"].values()
            )
        )

    def test_input_contract_consumes_only_governed_stage045_results(self):
        value = self._contract()["input_contract"]
        self.assertEqual("REFERENCE_ONLY_STAGE045_DETECTION_RESULT", value["mode"])
        self.assertEqual(
            [
                "routing_request_id",
                "detection_request_id",
                "source_fingerprint_ref",
                "source_identity_ref",
                "detected_type",
                "detection_state",
                "detection_confidence",
                "detection_evidence_ref",
                "detector_contract_version",
                "parser_registry_version",
                "requested_at",
            ],
            value["required_fields"],
        )
        self.assertEqual("STAGE-045", value["detection_authority"])
        self.assertFalse(value["caller_selected_parser_allowed"])
        self.assertFalse(value["file_type_redetection_allowed"])
        self.assertFalse(value["source_body_allowed"])
        self.assertTrue(value["raw_metadata_boundary_blocked"])

    def test_route_eligibility_is_explicit_and_fail_closed(self):
        value = self._contract()["route_eligibility_contract"]
        self.assertEqual(
            ["TYPE_CONFIRMED:HIGH"], value["candidate_ready_combinations"]
        )
        self.assertEqual(
            ["TYPE_PROVISIONAL:MEDIUM", "TYPE_PROVISIONAL:LOW"],
            value["review_required_combinations"],
        )
        self.assertEqual(
            [
                "TYPE_CONFLICT_REVIEW_REQUIRED",
                "TYPE_UNKNOWN_REVIEW_REQUIRED",
            ],
            value["always_review_states"],
        )
        self.assertEqual(["TYPE_UNSUPPORTED"], value["unsupported_states"])
        self.assertEqual(["TYPE_INPUT_BLOCKED"], value["blocked_states"])
        self.assertEqual(
            ["UNKNOWN", "CORRUPT_OR_UNREADABLE"], value["blocked_type_values"]
        )
        self.assertFalse(value["generic_parser_fallback_allowed"])
        self.assertFalse(value["unknown_type_route_allowed"])

    def test_route_registry_covers_eight_types_without_parser_implementation(self):
        value = self._contract()["route_registry_contract"]
        self.assertEqual(ROUTE_REGISTRY, value["routes"])
        self.assertEqual(6, value["route_family_count"])
        self.assertEqual(8, value["supported_type_count"])
        self.assertEqual([], value["parser_implementations"])
        self.assertEqual([], value["assigned_parser_versions"])
        self.assertTrue(value["parser_availability_required_before_dispatch"])
        self.assertFalse(value["route_execution_allowed"])
        self.assertFalse(value["parser_dispatch_allowed"])

    def test_output_boundary_preserves_stage047_contract_and_quality_gate(self):
        value = self._contract()["output_boundary"]
        self.assertEqual("STAGE-047", value["detailed_contract_owner"])
        self.assertEqual(OUTPUT_FIELDS, value["required_parser_output_fields"])
        self.assertTrue(value["all_content_fields_untrusted"])
        self.assertTrue(value["parser_version_and_provenance_required"])
        self.assertTrue(value["empty_output_is_failure"])
        self.assertFalse(value["output_creation_allowed"])
        self.assertFalse(value["direct_evidence_or_index_write_allowed"])

    def test_fallback_and_prompt_injection_owners_are_not_preempted(self):
        contract = self._contract()
        fallback = contract["fallback_boundary"]
        self.assertEqual("STAGE-048", fallback["implementation_owner"])
        self.assertFalse(fallback["silent_drop_allowed"])
        self.assertFalse(fallback["silent_parser_switch_allowed"])
        self.assertFalse(fallback["fallback_execution_allowed"])
        self.assertEqual("OWNER_REVIEW_REQUIRED", fallback["route_unavailable_action"])
        prompt = contract["prompt_injection_boundary"]
        self.assertEqual("STAGE-050", prompt["implementation_owner"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", prompt["source_text_label"])
        self.assertTrue(prompt["marker_required_before_downstream_model"])
        self.assertFalse(prompt["source_text_can_override_system_rules"])
        self.assertFalse(prompt["marker_application_allowed"])

    def test_quality_job_and_side_effect_boundaries_are_closed(self):
        contract = self._contract()
        quality = contract["quality_and_evidence_boundary"]
        self.assertEqual("CANDIDATE", quality["route_decision_fact_level"])
        self.assertEqual("BLOCK_DOWNSTREAM_PROMOTION", quality["missing_quality_action"])
        self.assertFalse(quality["evidence_promotion_allowed"])
        self.assertFalse(quality["manifest_or_index_mutation_allowed"])
        state = contract["state_and_job_boundary"]
        self.assertEqual("PARSE", state["job_type"])
        self.assertEqual("STAGE-037", state["state_model_owner"])
        self.assertFalse(state["job_creation_allowed"])
        self.assertFalse(state["state_transition_allowed"])
        runtime = contract["runtime_boundary"]
        self.assertFalse(runtime["parser_registry_runtime_load_allowed"])
        self.assertFalse(runtime["route_evaluation_allowed"])
        self.assertFalse(runtime["backend_or_worker_start_allowed"])
        self.assertFalse(runtime["persistent_write_allowed"])

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
            lambda item: item["input_contract"].update({"caller_selected_parser_allowed": True}),
            lambda item: item["route_eligibility_contract"].update({"unknown_type_route_allowed": True}),
            lambda item: item["route_registry_contract"].update({"parser_dispatch_allowed": True}),
            lambda item: item["output_boundary"].update({"direct_evidence_or_index_write_allowed": True}),
            lambda item: item["fallback_boundary"].update({"silent_parser_switch_allowed": True}),
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

    def test_checker_live_source_and_predecessor_snapshot_are_valid(self):
        checker = self._checker()
        self.assertTrue(checker.live_source_valid())
        self.assertTrue(checker.predecessor_valid())
        self.assertTrue(checker.upstream_snapshot_valid())

    def test_report_and_governance_stop_at_phase1(self):
        report = self._checker().build_stage046_phase1_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED", report["result"]
        )
        self.assertEqual("IDS-STAGE046-P2-GATE", report["next_gate"])
        self.assertEqual(6, report["route_family_count"])
        self.assertEqual(8, report["supported_type_count"])
        self.assertEqual(6, report["required_output_field_count"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["parser_dispatch_allowed"])
        self.assertFalse(report["push_allowed"])
        docs = ENTRY.read_text(encoding="utf-8") + BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "Phase 2 must run separately",
            "NO_PHASE2",
            "NO_SOURCE_FILE_OPEN",
            "NO_FILE_TYPE_REDETECTION",
            "NO_PARSER_REGISTRY_RUNTIME_LOAD",
            "NO_PARSER_ROUTE_EXECUTION",
            "NO_PARSER_DISPATCH",
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
        self.assertIn('status: "stage046_phase2_completed"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE046-P2"', batch)
        self.assertIn('next_allowed_task_id: "IDS-V0_1-STAGE046-P3"', batch)
        self.assertIn("push_allowed: false", batch)
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE046"', roadmap)
        self.assertIn('current_phase_id: "IDS-STAGE046-P2"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE046-P3-GATE"', roadmap)
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line
        ]
        matching = [
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE046-P1-20260720-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE046-P1", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-046"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
