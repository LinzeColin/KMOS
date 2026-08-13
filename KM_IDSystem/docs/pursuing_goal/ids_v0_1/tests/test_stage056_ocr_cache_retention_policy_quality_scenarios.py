import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_contract.json"
PHASE2_CONTRACT = (
    BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_slice_contract.json"
)
EVIDENCE = BASE / "STAGE056_PHASE3_OCR_CACHE_RETENTION_POLICY_QUALITY_SCENARIOS.md"
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage056-p3-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
CONTRACT = (
    BASE
    / "ocr_queue"
    / "stage056_ocr_cache_retention_policy_quality_scenarios_contract.json"
)
SCENARIOS = (
    BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_quality_scenarios.py"
)
P2_SLICE = BASE / "ocr_queue" / "stage056_ocr_cache_retention_policy_slice.py"
EXPECTED_SCENARIOS = [
    "scanned-pdf-cache-policy-control-candidate",
    "blurred-image-cache-policy-control-degraded",
    "table-image-cache-policy-control-unassessed",
    "mixed-zh-en-cache-policy-control-degraded",
    "low-quality-cache-policy-control-failed",
]


class Stage056OcrCacheRetentionPolicyPhase3Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage056_p3", SCENARIOS)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_ocr_cache_retention_policy_phase3_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase3_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            EVIDENCE,
            BATCH,
            ROADMAP,
            EVENTS,
            RUN,
            STATUS,
            CONTRACT,
            SCENARIOS,
            P2_SLICE,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_non_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage056.ocr_cache_retention_policy.phase3.quality_scenarios.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE056-P3", contract["task_id"])
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE056-P4-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertEqual(0, contract["scenario_input_boundary"]["actual_fixture_count"])
        self.assertFalse(
            contract["scenario_input_boundary"]["actual_pdf_or_image_open_allowed"]
        )
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_allowed"])

    def test_scenario_catalog_covers_exact_taskpack_quality_categories(self):
        contract = self._contract()
        self.assertEqual(5, contract["scenario_input_boundary"]["scenario_count"])
        self.assertEqual(
            [
                "SCANNED_PDF_CONTROL",
                "BLURRED_IMAGE_CONTROL",
                "TABLE_IMAGE_CONTROL",
                "MIXED_ZH_EN_CONTROL",
                "LOW_QUALITY_CONTROL",
            ],
            contract["scenario_input_boundary"]["scenario_categories"],
        )
        self.assertTrue(
            contract["scenario_input_boundary"]["scenario_category_is_control_metadata"]
        )
        self.assertTrue(
            contract["quality_scenario_validation"]
            ["all_taskpack_quality_categories_covered"]
        )

    def test_all_controlled_quality_scenarios_are_explicit(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(4, report["unique_policy_candidate_count"])
        self.assertEqual(
            EXPECTED_SCENARIOS,
            [item["scenario_id"] for item in report["scenario_results"]],
        )

    def test_scanned_pdf_and_table_controls_remain_unassessed_candidates(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        scanned = report_by_id["scanned-pdf-cache-policy-control-candidate"]
        self.assertEqual(
            "CANDIDATE_RETAINED_NOT_REAL_OCR_QUALITY_UNASSESSED",
            scanned["quality_disposition"],
        )
        self.assertFalse(scanned["review_required_not_queued"])
        table = report_by_id["table-image-cache-policy-control-unassessed"]
        self.assertEqual(
            "CANDIDATE_RETAINED_TABLE_EXTRACTION_UNASSESSED",
            table["quality_disposition"],
        )
        self.assertFalse(table["table_structure_extraction_performed"])
        self.assertFalse(table["recognition_accuracy_evaluated"])
        self.assertFalse(table["high_trust_direct_entry_allowed"])

    def test_blurred_and_mixed_controls_are_degraded_without_a_review_task(self):
        report_by_id = {
            item["scenario_id"]: item for item in self._report()["scenario_results"]
        }
        blurred = report_by_id["blurred-image-cache-policy-control-degraded"]
        self.assertEqual("LOW", blurred["confidence_level"])
        self.assertEqual(
            "DEGRADED_EVIDENCE_LOW_CONFIDENCE_REVIEW_REQUIRED_NOT_QUEUED",
            blurred["quality_disposition"],
        )
        self.assertTrue(blurred["review_required_not_queued"])
        mixed = report_by_id["mixed-zh-en-cache-policy-control-degraded"]
        self.assertEqual(
            "SIMPLIFIED_CHINESE_AND_ENGLISH", mixed["language_profile"]
        )
        self.assertEqual(
            "DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED",
            mixed["quality_disposition"],
        )
        self.assertTrue(mixed["review_required_not_queued"])
        self.assertFalse(self._report()["human_review_task_created"])

    def test_low_quality_control_is_explicit_failed_not_promoted_and_not_auto_cleaned(self):
        item = next(
            result
            for result in self._report()["scenario_results"]
            if result["scenario_id"] == "low-quality-cache-policy-control-failed"
        )
        self.assertEqual("FAILURE_ARTIFACT", item["artifact_class"])
        self.assertEqual(
            "FAILED_PAGE_EXPLICIT_NO_AUTOMATIC_CLEANUP_OR_EVIDENCE_PROMOTION",
            item["quality_disposition"],
        )
        self.assertTrue(item["review_required_not_queued"])
        self.assertTrue(item["automatic_cleanup_blocked"])
        self.assertFalse(item["high_trust_direct_entry_allowed"])

    def test_report_retains_no_sample_or_ocr_payload(self):
        report = self._report()
        report_text = repr(report)
        for forbidden_fragment in (
            "OCR_EXECUTION_NOT_STARTED",
            "page-image-ref:",
            "CONTROL_SCANNED_DOCUMENT_OUTPUT",
        ):
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, report_text)
        for item in report["scenario_results"]:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["control_scenario_metadata_only"])
                self.assertFalse(item["actual_ocr_text_created"])
                self.assertFalse(item["actual_pdf_or_image_opened"])
                self.assertFalse(item["actual_cache_created"])

    def test_cache_and_disk_boundary_remain_controlled_and_nonphysical(self):
        report = self._report()
        self.assertTrue(report["cache_boundary_preserved"])
        self.assertEqual(0, report["physical_cache_item_count"])
        self.assertEqual(
            "NO_PHYSICAL_CACHE_CREATED_NO_CLEANUP_EXECUTED",
            report["cache_cleanup_action"],
        )
        self.assertEqual(3, report["temporary_cleanup_policy_candidate_count"])
        self.assertEqual(1, report["failure_automatic_cleanup_block_count"])
        self.assertFalse(report["actual_disk_capacity_proof_produced"])
        self.assertFalse(report["cache_capacity_evaluation_performed"])
        self.assertFalse(report["cache_cleanup_execution_performed"])

    def test_all_external_actions_remain_disabled(self):
        report = self._report()
        for field in (
            "authorized_fixture_access_performed",
            "real_pdf_or_image_opened",
            "source_file_open_performed",
            "file_type_detection_performed",
            "route_evaluation_performed",
            "parser_execution_performed",
            "pdf_rasterization_performed",
            "image_processing_performed",
            "table_structure_extraction_performed",
            "language_detection_performed",
            "confidence_evaluation_performed",
            "recognition_accuracy_evaluated",
            "ocr_engine_selected",
            "ocr_engine_invocation_performed",
            "human_review_queue_write_performed",
            "human_review_task_created",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "phase4_started",
            "github_upload_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_result_stays_non_passing(self):
        report = self._module().build_ocr_cache_retention_policy_phase3_report(
            lambda _: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual(
            "FAIL_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS",
            report["result"],
        )
        self.assertEqual(0, report["passed_scenario_count"])

    def test_contract_declares_p2_replay_and_recovery_boundary(self):
        contract = self._contract()
        self.assertTrue(contract["implementation"]["phase2_control_slice_reexecuted"])
        self.assertFalse(contract["implementation"]["actual_ocr_quality_evaluation_implemented"])
        self.assertFalse(contract["cache_boundary"]["actual_disk_capacity_proof_produced"])
        self.assertEqual("STAGE-056", contract["cache_boundary"]["cache_retention_owner"])
        batch_text = BATCH.read_text(encoding="utf-8")
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for expected in (
            'status: "stage056_phase3_completed"',
            'current_task_id: "IDS-V0_1-STAGE056-P3"',
            'next_gate: "IDS-STAGE056-P4-GATE"',
            'phase3_started: true',
            'phase4_started: false',
            'ovh_deployment_performed: false',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, batch_text)
        for expected in (
            'current_phase_id: "IDS-STAGE056-P3"',
            'current_task_id: "IDS-V0_1-STAGE056-P3"',
            'next_gate_id: "IDS-STAGE056-P4-GATE"',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, roadmap_text)
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE056-P3", run["task_id"])
        self.assertEqual("IDS-STAGE056-P4-GATE", run["next_gate"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertEqual("IDS-V0_1-STAGE056-P3", status["task"])
        self.assertEqual("IDS-STAGE056-P4-GATE", status["next_gate"])
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item["event_id"] == "EVT-IDS-V0_1-STAGE056-P3-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE056-P3", event["task_id"])
        self.assertIn("next_gate=IDS-STAGE056-P4-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
