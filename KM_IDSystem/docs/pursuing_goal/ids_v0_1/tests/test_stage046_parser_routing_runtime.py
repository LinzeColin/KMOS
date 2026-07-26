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
    / "parser_routing"
    / "stage046_parser_routing_runtime_contract.json"
)
BOUNDARY = BASE / "STAGE046_PHASE2_PARSER_ROUTING_SLICE.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
CHECKER = ROOT / "scripts" / "check_parser_routing_runtime.py"

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
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

PREDECESSOR_BINDING = {
    "stage046_phase1_commit": "c82e4e928b167c718d462dc8cef3eed5b5dbb3ea",
    "stage046_phase1_root_tree": "403e4057c028667c23a35588f09b3c00ebb51735",
    "stage046_phase1_kmids_tree": "c59be0f27521a15dc876656c753ee9b503611f94",
    "stage046_phase1_parent": "76027b8dc89e325c212d492d7f5df88357ea7112",
    "stage046_phase1_status": "stage046_phase1_completed",
    "stage046_phase1_result": "PASS_PHASE1_CONTRACT_PARSER_DISPATCH_DISABLED",
}

PHASE1_BINDINGS = {
    "stage046_phase1_entry_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE046_ENTRY_CONTRACT.md",
        "379f5068c1a834165125ea1a2ed1655b248476873504962bc3908fb38613801b",
    ),
    "stage046_phase1_boundary_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md",
        "12a1f889eab68a77a02e8c34fdb7f074ec8a40c081f004abc4063bb430c80af6",
    ),
    "stage046_phase1_contract_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
        "stage046_parser_routing_contract.json",
        "5c145dba0ba2246b6daa33da0098b4b2ee2a48a53cfec993261d70596706c1fd",
    ),
    "stage046_phase1_checker_ref": (
        "KM_IDSystem/scripts/check_parser_routing.py",
        "eedea73a6f2a640f4f1b8836119ca9fe73170053e7b084abfed004d52c563ff8",
    ),
    "stage046_phase1_test_ref": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
        "test_stage046_parser_routing.py",
        "947fe518cd799297026ec32ea5707f9d6812524b83518cb014122e392906a74e",
    ),
    "stage046_phase1_run_ref": (
        "KM_IDSystem/machine/runs/2026-07-20-stage046-p1-local.json",
        "60370c3a60535e191a68e5d8f30b49668d0ddae52f3400eafa8fd609ea84e473",
    ),
}

ROUTER_VERSION = "ids.parser_router.v0_1.stage046.p2"
REGISTRY_VERSION = "ids.parser_route_registry.v0_1.stage046.p2"
DETECTOR_VERSION = "ids.file_type_detector.v0_1.stage045.p2"
UNASSIGNED_VERSION = "UNASSIGNED_NOT_IMPLEMENTED"

ROUTES = [
    {
        "route_id": "ROUTE_PDF",
        "accepted_types": ["PDF"],
        "parser_family": "PDF_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_OOXML_WORD",
        "accepted_types": ["DOCX"],
        "parser_family": "OOXML_WORD_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_OOXML_WORKBOOK",
        "accepted_types": ["XLSX"],
        "parser_family": "OOXML_WORKBOOK_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_DELIMITED_TEXT",
        "accepted_types": ["CSV"],
        "parser_family": "DELIMITED_TEXT_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_PLAIN_TEXT",
        "accepted_types": ["TXT"],
        "parser_family": "PLAIN_TEXT_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
    {
        "route_id": "ROUTE_IMAGE",
        "accepted_types": ["PNG", "JPEG", "TIFF"],
        "parser_family": "IMAGE_PARSER",
        "parser_version": UNASSIGNED_VERSION,
        "parser_implementation_available": False,
    },
]

TYPE_ROUTE = {
    file_type: (route["route_id"], route["parser_family"])
    for route in ROUTES
    for file_type in route["accepted_types"]
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
    "external_parser_registry_loaded",
    "parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "fallback_execution_performed",
    "differential_parser_evaluation_performed",
    "prompt_injection_scan_performed",
    "runtime_prompt_injection_marker_applied",
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
    "phase3_started",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "app_reinstall_allowed",
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "metadata_only_routing_requests_evaluated",
    "static_route_registry_loaded_in_memory",
    "parser_route_evaluation_performed",
    "route_candidate_selected",
    "parser_version_status_recorded",
    "evidence_text_classification_enforced",
    "phase2_started",
}


class Stage046ParserRoutingPhase2Tests(unittest.TestCase):
    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        spec = importlib.util.spec_from_file_location(
            "stage046_parser_routing_runtime_checker", CHECKER
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _request(
        self,
        checker,
        *,
        detected_type="PDF",
        detection_state="TYPE_CONFIRMED",
        detection_confidence="HIGH",
        marker=False,
        suffix="a",
    ):
        return checker.build_routing_request(
            detection_request_id="detection:sha256:" + suffix * 64,
            source_fingerprint_ref="fingerprint:sha256:" + suffix * 64,
            source_identity_ref=f"source:control:{suffix}",
            detected_type=detected_type,
            detection_state=detection_state,
            detection_confidence=detection_confidence,
            detection_evidence_ref=f"evidence:stage045:control:{suffix}",
            evidence_text_marker_applied=marker,
            requested_at="2026-07-20T03:00:00Z",
        )

    def test_phase2_artifacts_exist(self):
        for file in (CONTRACT, BOUNDARY, CHECKER):
            with self.subTest(file=file):
                self.assertTrue(file.is_file())

    def test_identity_source_predecessor_and_phase1_bindings_are_exact(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage046.parser_routing.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-046", contract["stage"])
        self.assertEqual("Phase 2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE046-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-046", contract["acceptance_id"])
        self.assertEqual(
            "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SLICE",
            contract["execution_mode"],
        )
        self.assertEqual("IDS-STAGE046-P3-GATE", contract["next_gate"])
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(
            PREDECESSOR_BINDING, contract["phase1_predecessor_binding"]
        )
        observed = {
            name: (item["ref"], item["sha256"])
            for name, item in contract["phase1_snapshot_bindings"].items()
        }
        self.assertEqual(PHASE1_BINDINGS, observed)
        self.assertTrue(
            all(
                item["snapshot_commit"]
                == PREDECESSOR_BINDING["stage046_phase1_commit"]
                for item in contract["phase1_snapshot_bindings"].values()
            )
        )

    def test_runtime_contract_is_metadata_only_and_parser_disabled(self):
        contract = self._contract()
        request = contract["request_contract"]
        self.assertEqual(
            "REFERENCE_ONLY_STAGE045_DETECTION_RESULT", request["mode"]
        )
        self.assertFalse(request["source_path_allowed"])
        self.assertFalse(request["source_body_allowed"])
        self.assertFalse(request["caller_selected_parser_allowed"])
        self.assertFalse(request["file_type_redetection_allowed"])
        self.assertTrue(request["raw_metadata_boundary_blocked"])
        runtime = contract["runtime_boundary"]
        self.assertTrue(runtime["metadata_only_route_evaluation_allowed"])
        self.assertTrue(runtime["static_registry_in_memory_allowed"])
        self.assertFalse(runtime["source_file_access_allowed"])
        self.assertFalse(runtime["parser_dispatch_allowed"])
        self.assertFalse(runtime["parser_execution_allowed"])
        self.assertFalse(runtime["fallback_execution_allowed"])
        self.assertFalse(runtime["persistent_write_allowed"])

    def test_request_builder_is_deterministic_and_rejects_unsafe_metadata(self):
        checker = self._checker()
        first = self._request(checker)
        second = self._request(checker)
        self.assertEqual(first, second)
        self.assertEqual(
            "ids.stage046.parser_routing_request.v1", first["schema_version"]
        )
        self.assertTrue(first["routing_request_id"].startswith("routing:sha256:"))
        forbidden = {
            "source_path",
            "source_body",
            "source_text",
            "caller_selected_parser",
            "secret",
            "credential",
        }
        self.assertTrue(forbidden.isdisjoint(first))
        with self.assertRaises(ValueError):
            checker.build_routing_request(
                detection_request_id="not-a-detection-ref",
                source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
                source_identity_ref="source:control:a",
                detected_type="PDF",
                detection_state="TYPE_CONFIRMED",
                detection_confidence="HIGH",
                detection_evidence_ref="evidence:stage045:control:a",
                evidence_text_marker_applied=False,
                requested_at="2026-07-20T03:00:00Z",
            )
        with self.assertRaises(ValueError):
            checker.build_routing_request(
                detection_request_id="detection:sha256:" + "a" * 64,
                source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
                source_identity_ref="/private/raw/file.pdf",
                detected_type="PDF",
                detection_state="TYPE_CONFIRMED",
                detection_confidence="HIGH",
                detection_evidence_ref="evidence:stage045:control:a",
                evidence_text_marker_applied=False,
                requested_at="2026-07-20T03:00:00Z",
            )
        with self.assertRaises(ValueError):
            checker.build_routing_request(
                detection_request_id="detection:sha256:" + "a" * 64,
                source_fingerprint_ref="fingerprint:sha256:" + "a" * 64,
                source_identity_ref="source:control:a",
                detected_type="PDF",
                detection_state="TYPE_CONFIRMED",
                detection_confidence="HIGH",
                detection_evidence_ref="evidence:stage045:control:a",
                evidence_text_marker_applied=False,
                requested_at="2026-02-30T03:00:00Z",
            )

    def test_confirmed_high_types_select_exact_route_but_block_dispatch(self):
        checker = self._checker()
        for index, (file_type, expected) in enumerate(TYPE_ROUTE.items()):
            suffix = "abcdef01"[index]
            result = checker.evaluate_parser_route(
                self._request(checker, detected_type=file_type, suffix=suffix)
            )
            with self.subTest(file_type=file_type):
                self.assertEqual(
                    "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
                    result["route_action"],
                )
                self.assertEqual(expected[0], result["candidate_route_id"])
                self.assertEqual(expected[1], result["parser_family"])
                self.assertEqual(UNASSIGNED_VERSION, result["parser_version"])
                self.assertEqual(
                    "RECORDED_UNASSIGNED", result["parser_version_status"]
                )
                self.assertEqual("HIGH", result["routing_confidence"])
                self.assertEqual("CANDIDATE", result["route_fact_level"])
                self.assertTrue(result["route_candidate_selected"])
                self.assertFalse(result["parser_selected"])
                self.assertFalse(result["parser_dispatch_performed"])
                self.assertFalse(result["parser_execution_performed"])

    def test_non_high_or_unsupported_detection_fails_closed(self):
        checker = self._checker()
        cases = [
            (
                "PDF",
                "TYPE_PROVISIONAL",
                "MEDIUM",
                "ROUTE_REVIEW_REQUIRED",
            ),
            (
                "PDF",
                "TYPE_CONFLICT_REVIEW_REQUIRED",
                "UNKNOWN",
                "ROUTE_REVIEW_REQUIRED",
            ),
            (
                "UNKNOWN",
                "TYPE_UNKNOWN_REVIEW_REQUIRED",
                "UNKNOWN",
                "ROUTE_REVIEW_REQUIRED",
            ),
            (
                "UNSUPPORTED",
                "TYPE_UNSUPPORTED",
                "UNKNOWN",
                "ROUTE_UNSUPPORTED",
            ),
            (
                "CORRUPT_OR_UNREADABLE",
                "TYPE_INPUT_BLOCKED",
                "UNKNOWN",
                "ROUTE_BLOCKED",
            ),
        ]
        for index, (file_type, state, confidence, action) in enumerate(cases):
            suffix = "23456"[index]
            result = checker.evaluate_parser_route(
                self._request(
                    checker,
                    detected_type=file_type,
                    detection_state=state,
                    detection_confidence=confidence,
                    suffix=suffix,
                )
            )
            with self.subTest(state=state):
                self.assertEqual(action, result["route_action"])
                self.assertIsNone(result["candidate_route_id"])
                self.assertFalse(result["route_candidate_selected"])
                self.assertFalse(result["parser_dispatch_performed"])
                self.assertFalse(result["fallback_execution_performed"])

    def test_invalid_request_and_caller_override_fail_before_routing(self):
        checker = self._checker()
        request = self._request(checker)
        for mutate in (
            lambda item: item.update({"caller_selected_parser": "unsafe"}),
            lambda item: item.update({"source_path": "/private/raw/file.pdf"}),
            lambda item: item.update({"parser_registry_version": "wrong"}),
            lambda item: item.update({"detector_contract_version": "wrong"}),
            lambda item: item.update({"detected_type": "PDF", "detection_state": "TYPE_UNSUPPORTED"}),
            lambda item: item.update({"evidence_text_marker_applied": "true"}),
        ):
            candidate = copy.deepcopy(request)
            mutate(candidate)
            result = checker.evaluate_parser_route(candidate)
            with self.subTest(candidate=candidate):
                self.assertEqual("ROUTE_BLOCKED", result["route_action"])
                self.assertIn("INVALID_ROUTING_REQUEST", result["errors"])
                self.assertFalse(result["parser_route_evaluation_performed"])
                self.assertFalse(result["route_candidate_selected"])

    def test_instruction_like_text_marker_remains_evidence_only(self):
        checker = self._checker()
        result = checker.evaluate_parser_route(
            self._request(checker, marker=True, suffix="f")
        )
        self.assertTrue(result["evidence_text_marker_preserved"])
        self.assertEqual("UNTRUSTED_EVIDENCE_TEXT", result["evidence_text_label"])
        self.assertEqual("EVIDENCE_ONLY", result["evidence_text_interpretation"])
        self.assertFalse(result["system_instruction_allowed"])
        self.assertFalse(result["tool_authorization_allowed"])
        self.assertFalse(result["policy_override_allowed"])
        self.assertFalse(result["prompt_injection_scan_performed"])
        self.assertFalse(result["runtime_prompt_injection_marker_applied"])
        self.assertNotIn("content", result)
        self.assertNotIn("source_text", result)

    def test_results_are_in_memory_candidate_facts_with_no_outputs_or_writes(self):
        checker = self._checker()
        result = checker.evaluate_parser_route(self._request(checker))
        self.assertTrue(result["in_memory_only"])
        self.assertFalse(result["persisted"])
        self.assertEqual([], result["output_refs"])
        self.assertEqual("CANDIDATE", result["route_fact_level"])
        for flag in (
            "source_file_open_performed",
            "file_type_redetection_performed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "parser_output_produced",
            "high_confidence_evidence_write_performed",
            "persistent_state_write_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(result[flag])

    def test_contract_truth_flags_match_isolated_slice(self):
        truth = self._contract()["truth_flags"]
        for flag in TRUE_TRUTH_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(truth[flag], True)
        for flag in FALSE_TRUTH_FLAGS:
            with self.subTest(flag=flag):
                self.assertIs(truth[flag], False)

    def test_contract_checker_rejects_nested_and_runtime_tampering(self):
        checker = self._checker()
        original = self._contract()
        checks = checker.evaluate_runtime_contract(original)
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()), checks)
        mutations = []
        for mutate in (
            lambda item: item["request_contract"].update({"source_path_allowed": True}),
            lambda item: item["route_registry"].update({"generic_parser_allowed": True}),
            lambda item: item["route_registry"]["routes"][0].update({"parser_version": "1.0.0"}),
            lambda item: item["evidence_text_contract"].update({"source_text_can_authorize_tools": True}),
            lambda item: item["runtime_boundary"].update({"parser_dispatch_allowed": True}),
            lambda item: item["phase3_entry_gate"].update({"entry_authorized": True}),
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
                self.assertFalse(
                    all(checker.evaluate_runtime_contract(candidate).values())
                )

    def test_checker_live_bindings_and_runtime_report_are_valid(self):
        checker = self._checker()
        self.assertTrue(checker.live_source_valid())
        self.assertTrue(checker.predecessor_live())
        self.assertTrue(checker.phase1_snapshot_live())
        report = checker.build_stage046_phase2_report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            "PASS_ISOLATED_PARSER_ROUTING_SLICE_PARSER_DISABLED",
            report["result"],
        )
        self.assertEqual(3, report["isolated_routing_count"])
        self.assertEqual("IDS-STAGE046-P3-GATE", report["next_gate"])
        self.assertTrue(report["parser_route_evaluation_performed"])
        self.assertTrue(report["parser_version_status_recorded"])
        self.assertFalse(report["parser_dispatch_performed"])
        self.assertFalse(report["parser_execution_performed"])
        self.assertFalse(report["fallback_execution_performed"])
        self.assertFalse(report["push_allowed"])

    def test_governance_and_docs_stop_at_phase3_gate(self):
        docs = BOUNDARY.read_text(encoding="utf-8")
        for marker in (
            "NO_REAL_SOURCE_FILE_READ",
            "NO_FILE_TYPE_REDETECTION",
            "NO_PARSER_DISPATCH",
            "NO_PARSER_EXECUTION",
            "NO_FALLBACK_EXECUTION",
            "NO_PROMPT_INJECTION_SCAN",
            "NO_EVIDENCE_PROMOTION",
            "NO_PHASE3_THIS_RUN",
            "NO_STAGE_REVIEW_THIS_RUN",
            "NO_BATCH_REVIEW_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, docs)
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn('status: "stage046_phase2_completed"', batch)
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE046-P2-20260720-001"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("IDS-V0_1-STAGE046-P2", matching[0]["task_id"])
        self.assertEqual(["ACC-STAGE-046"], matching[0]["acceptance_ids"])
        self.assertIn(str(CONTRACT.relative_to(REPO_ROOT)), matching[0]["changed_files"])


if __name__ == "__main__":
    unittest.main()
