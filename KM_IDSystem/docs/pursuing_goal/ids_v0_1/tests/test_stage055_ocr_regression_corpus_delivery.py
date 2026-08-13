import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
CLOSEOUT = BASE / "STAGE055_PHASE4_OCR_REGRESSION_CORPUS_DELIVERY_CLOSEOUT.md"
CONTRACT = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_delivery_contract.json"
DELIVERY = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_delivery.py"
P3_SCENARIOS = BASE / "ocr_queue" / "stage055_ocr_regression_corpus_quality_scenarios.py"
P3_CONTRACT = (
    BASE
    / "ocr_queue"
    / "stage055_ocr_regression_corpus_quality_scenarios_contract.json"
)
BATCH = BASE / "BATCH051_060_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
RUN = ROOT / "machine" / "runs" / "2026-08-13-stage055-p4-local.json"

EXPECTED_SCENARIOS = [
    "scanned-pdf-control-candidate",
    "blurred-image-control-degraded",
    "table-image-control-unassessed",
    "mixed-zh-en-control-degraded",
    "low-quality-control-failed",
]
EXPECTED_REVIEW_SCENARIOS = [
    "blurred-image-control-degraded",
    "mixed-zh-en-control-degraded",
    "low-quality-control-failed",
]


class Stage055OcrRegressionCorpusPhase4Tests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage055_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_ocr_regression_corpus_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_artifacts_exist(self):
        for artifact in (
            CLOSEOUT,
            CONTRACT,
            DELIVERY,
            P3_SCENARIOS,
            P3_CONTRACT,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_isolated_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage055.ocr_regression_corpus.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE055-P4", contract["task_id"])
        self.assertEqual(
            "PASS_PHASE4_OCR_REGRESSION_CORPUS_DELIVERY_RUNTIME_DISABLED",
            contract["valid_result"],
        )
        self.assertEqual("IDS-STAGE055-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(
            contract["source_authority"]["second_authoritative_source_created"]
        )
        self.assertFalse(contract["source_authority"]["source_body_or_path_allowed"])
        self.assertFalse(contract["delivery_evidence"]["real_ocr_output_produced"])
        self.assertFalse(contract["runtime_boundary"]["ocr_engine_invocation_allowed"])

    def test_delivery_samples_preserve_only_control_metadata(self):
        samples = self._report()["delivery_samples"]
        self.assertEqual(5, len(samples))
        self.assertEqual(EXPECTED_SCENARIOS, [item["scenario_id"] for item in samples])
        for item in samples:
            with self.subTest(sample=item["sample_id"]):
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_OCR_REGRESSION_CORPUS_SAMPLE_NOT_REAL_OCR",
                    item["sample_kind"],
                )
                self.assertTrue(item["source_page_ref"].startswith("source-page:control:"))
                self.assertEqual("UNASSESSED", item["quality_state"])
                self.assertFalse(item["ocr_text_retained"])
                self.assertFalse(item["source_content_retained"])
                self.assertFalse(item["actual_ocr_output_produced"])
                self.assertFalse(item["high_trust_direct_entry_allowed"])
                self.assertNotIn("ocr_text", item)
                self.assertNotIn("source_identity_ref", item)

    def test_delivery_report_does_not_echo_symbolic_payload_or_real_paths(self):
        rendered = json.dumps(self._report(), ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "CONTROL_SCANNED_DOCUMENT_OUTPUT",
            "page-image-ref:control:stage055-p2",
            "OCR_EXECUTION_NOT_STARTED",
            "source_identity_ref",
            "/Users/",
            "IDS_MetaData",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, rendered)

    def test_confidence_report_matches_controlled_predecessor(self):
        report = self._report()["confidence_report"]
        self.assertEqual(
            "CONTROLLED_OCR_REGRESSION_CORPUS_CONFIDENCE_SUMMARY_NOT_REAL_OCR_ACCURACY",
            report["report_kind"],
        )
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(
            {"HIGH": 1, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 1},
            report["confidence_counts"],
        )
        self.assertEqual(2, report["candidate_sample_count"])
        self.assertEqual(3, report["declared_review_route_count"])
        self.assertEqual(1, report["explicit_failure_count"])
        self.assertFalse(report["recognition_accuracy_evaluated"])
        self.assertFalse(report["quality_gate_evaluated"])
        self.assertFalse(report["high_trust_evidence_promoted"])

    def test_failure_list_is_explicit_and_non_runtime(self):
        failures = self._report()["failure_list"]
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("low-quality-control-failed", failure["failure_id"])
        self.assertEqual(
            "CONTROLLED_OCR_REGRESSION_CORPUS_FAILURE_LIST_ENTRY_NOT_RUNTIME",
            failure["record_kind"],
        )
        self.assertEqual("OCR_PAGE_FAILED_EXPLICIT", failure["page_state"])
        self.assertEqual(
            "FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION",
            failure["quality_disposition"],
        )
        self.assertTrue(failure["failure_is_control_metadata_only"])
        self.assertFalse(failure["actual_failure_record_created"])
        self.assertFalse(failure["evidence_promotion_performed"])
        self.assertFalse(failure["review_queue_write_performed"])
        self.assertFalse(failure["silent_drop"])

    def test_review_route_proofs_remain_candidates_not_queued(self):
        proofs = self._report()["review_route_proofs"]
        self.assertEqual(
            EXPECTED_REVIEW_SCENARIOS,
            [item["scenario_id"] for item in proofs],
        )
        for proof in proofs:
            with self.subTest(scenario=proof["scenario_id"]):
                self.assertEqual(
                    "DECLARED_OCR_REGRESSION_CORPUS_REVIEW_ROUTE_PROOF_CANDIDATE_ONLY_NOT_QUEUED",
                    proof["record_kind"],
                )
                self.assertEqual(
                    "STAGE054_CONTROLLED_REVIEW_ROUTE_REQUIRED",
                    proof["review_route_declared"],
                )
                self.assertTrue(proof["review_required_not_queued"])
                self.assertTrue(proof["human_confirmation_required"])
                self.assertFalse(proof["review_queue_created"])
                self.assertFalse(proof["review_queue_write_performed"])
                self.assertFalse(proof["human_review_task_created"])

    def test_quality_limitations_and_confirmation_prompts_are_chinese_and_manual(self):
        report = self._report()
        self.assertEqual(3, len(report["quality_limitations_zh"]))
        prompts = report["human_confirmation_prompts_zh"]
        self.assertEqual(3, len(prompts))
        for prompt in prompts:
            with self.subTest(prompt=prompt["prompt_id"]):
                self.assertIn("确认", prompt["text"])
                self.assertFalse(prompt["automatic_confirmation_performed"])

    def test_cache_cleanup_and_rerun_instructions_are_non_destructive(self):
        cache = self._report()["cache_rerun_instructions"]
        self.assertEqual("IN_MEMORY_REBUILDABLE_NOT_PERSISTED", cache["cache_policy"])
        self.assertEqual(0, cache["temporary_artifact_count"])
        self.assertFalse(cache["cache_storage_location_assigned"])
        self.assertEqual("NO_TEMPORARY_ARTIFACT_CREATED", cache["cleanup_action"])
        self.assertFalse(cache["actual_cleanup_performed"])
        self.assertTrue(cache["rerun_is_in_memory_only"])
        self.assertEqual("STAGE-056", cache["cache_retention_owner"])
        self.assertTrue(any("不得扫描" in item for item in cache["cleanup_instructions_zh"]))

    def test_rollback_returns_to_phase3(self):
        rollback = self._report()["rollback"]
        self.assertEqual(
            "PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_predecessor_evidence"])
        self.assertFalse(rollback["source_or_raw_data_change_allowed"])
        self.assertFalse(rollback["persistent_runtime_state_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_report_level_runtime_actions_are_disabled(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_OCR_REGRESSION_CORPUS_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
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
            "review_queue_created",
            "human_review_queue_write_performed",
            "human_review_task_created",
            "human_review_result_created",
            "actual_ocr_text_created",
            "actual_page_image_reference_created",
            "actual_failure_record_created",
            "cache_created",
            "cache_write_performed",
            "cache_cleanup_performed",
            "quality_gate_evaluation_performed",
            "evidence_promotion_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "whole_stage_review_performed",
            "batch_review_performed",
            "github_upload_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_invalid_predecessor_fails_closed(self):
        report = self._module().build_ocr_regression_corpus_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_OCR_REGRESSION_CORPUS_DELIVERY_EVIDENCE", report["result"])
        self.assertEqual([], report["delivery_samples"])
        self.assertEqual([], report["failure_list"])

    def test_closeout_explains_chinese_boundary_and_next_gate(self):
        closeout = CLOSEOUT.read_text(encoding="utf-8")
        for expected in (
            "metadata-only",
            "NO_TEMPORARY_ARTIFACT_CREATED",
            "PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED",
            "IDS-STAGE055-REVIEW-GATE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, closeout)

    def test_governance_and_local_run_preserve_phase4(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for text, expected in (
            (batch, 'status: "stage055_phase4_completed_review_pending"'),
            (batch, "stage055_phase4_state:"),
            (batch, 'current_task_id: "IDS-V0_1-STAGE055-P4"'),
            (batch, 'next_gate: "IDS-STAGE055-REVIEW-GATE"'),
            (batch, "ocr_regression_corpus_delivery_evidence_derived: true"),
            (batch, "ocr_engine_invocation_performed: false"),
            (batch, "model_token_consumption_performed: false"),
            (batch, "ovh_deployment_performed: false"),
            (roadmap, 'current_stage_id: "IDS-STAGE055"'),
            (roadmap, 'current_phase_id: "IDS-STAGE055-P4"'),
            (roadmap, 'next_gate_id: "IDS-STAGE055-REVIEW-GATE"'),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        self.assertIn(status["stage"], ("IDS-STAGE055", "IDS-STAGE056"))
        self.assertIn(
            status["phase"],
            (
                "IDS-V0_1-STAGE055-P4",
                "IDS-V0_1-STAGE055-REVIEW",
                "IDS-V0_1-STAGE056-P1",
                "IDS-V0_1-STAGE056-P2",
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])

        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(
            "PASS_PHASE4_OCR_REGRESSION_CORPUS_DELIVERY_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertTrue(
            run["observed_work"]["ocr_regression_corpus_delivery_evidence_derived"]
        )
        self.assertFalse(run["observed_work"]["ocr_engine_invocation_performed"])
        self.assertFalse(run["observed_work"]["human_review_task_created"])
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["whole_stage_review_performed"])

        events = [
            json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE055-P4-20260813-001"
        )
        self.assertEqual("IDS-V0_1-STAGE055-P4", event["task_id"])
        self.assertEqual(["ACC-STAGE-055"], event["acceptance_ids"])
        self.assertIn("next_gate=IDS-STAGE055-REVIEW-GATE", event["notes"])


if __name__ == "__main__":
    unittest.main()
