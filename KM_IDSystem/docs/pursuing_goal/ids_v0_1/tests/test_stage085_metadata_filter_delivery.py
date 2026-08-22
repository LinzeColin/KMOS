import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE085_PHASE4_METADATA_FILTER_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage085_metadata_filter_delivery.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-085_元数据过滤.md"
)
PHASE1_SCOPE = BASE / "STAGE085_PHASE1_METADATA_FILTER_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage085_metadata_filter_contract.json"
PHASE2_SCOPE = BASE / "STAGE085_PHASE2_METADATA_FILTER_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage085_metadata_filter_control_slice.py"
)
PHASE3_SCOPE = BASE / "STAGE085_PHASE3_METADATA_FILTER_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE / "index_version_schema" / "stage085_metadata_filter_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "index_version_schema" / "stage085_metadata_filter_controlled_scenarios.py"
)
PREDECESSOR_REVIEW = BASE / "STAGE084_STAGE_REVIEW.md"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage085MetadataFilterPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module(MODULE, "stage085_p4")
        cls.phase3 = _load_module(PHASE3_MODULE, "stage085_p3_for_p4_test")

    def report(self):
        return self.module.build_metadata_filter_phase4_delivery_report()

    def test_control_artifacts_and_phase_identity_are_explicit(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PREDECESSOR_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())
        self.assertEqual(
            "ids.stage085.metadata_filter.phase4.delivery.v1",
            self.contract["schema_version"],
        )
        self.assertEqual("IDS-STAGE085-P4", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE085-P4", self.contract["task_id"])
        self.assertEqual("IDS-STAGE085-P4-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE085-REVIEW-GATE", self.contract["next_gate"])

    def test_contract_declares_metadata_only_control_delivery(self):
        authority = self.contract["source_authority"]
        for field in (
            "delivery_control_metadata_can_replace_source_document",
            "delivery_control_metadata_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(366, replay["phase2_control_field_check_count"])
        self.assertEqual(8, replay["scenario_count"])
        self.assertEqual(31, replay["scenario_field_count"])
        self.assertEqual(248, replay["scenario_field_check_count"])
        self.assertTrue(replay["six_dimension_filter_combination_required"])
        self.assertTrue(replay["metadata_status_filter_reference_required"])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertTrue(delivery["delivery_executable"])
        self.assertFalse(delivery["execution_ready"])
        self.assertTrue(delivery["metadata_only"])
        self.assertEqual(572, delivery["delivery_field_check_count"])
        self.assertEqual(4, delivery["chinese_feedback_count"])
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertEqual(0 if field.startswith("actual_") else False, value)

    def test_predecessor_replay_preserves_exact_control_shapes(self):
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(
            self.module.PASS_RESULT,
            report["result"],
        )
        self.assertEqual(
            self.module.NEXT_GATE,
            report["next_gate"],
        )
        self.assertTrue(report["phase3_controlled_scenarios_reexecuted_in_memory_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertEqual(366, self.phase3.build_metadata_filter_phase3_report()["phase2_control_record_field_check_count"])
        self.assertEqual(8, self.phase3.build_metadata_filter_phase3_report()["scenario_count"])
        self.assertEqual(31, self.phase3.build_metadata_filter_phase3_report()["scenario_field_count"])
        self.assertEqual(248, self.phase3.build_metadata_filter_phase3_report()["scenario_field_check_count"])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])

    def test_delivery_reuses_phase3_without_runtime_writes(self):
        report = self.report()
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertEqual(8, report["retrieval_sample_control_record_count"])
        self.assertEqual(8, report["trace_log_control_record_count"])
        self.assertEqual(8, report["filter_result_control_record_count"])
        self.assertEqual(8, report["validity_test_report_control_record_count"])
        self.assertEqual(8, report["evidence_gap_control_record_count"])
        self.assertEqual(4, report["parameter_rollback_instruction_count"])
        self.assertEqual(572, report["delivery_field_check_count"])
        self.assertTrue(report["all_delivery_references_control_only"])

    def test_retrieval_samples_and_trace_logs_preserve_control_refs(self):
        report = self.report()
        for item in report["retrieval_sample_control_records"]:
            with self.subTest(sample=item["scenario_id"]):
                self.assertEqual(set(self.module.RETRIEVAL_SAMPLE_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_RETRIEVAL_SAMPLE_NOT_PERSISTED",
                    item["sample_state"],
                )
                self.assertFalse(item["actual_retrieval_sample_written"])
                self.assertTrue(item["human_handling_required"])
                for field in (
                    "retrieval_sample_ref",
                    "query_ref",
                    "candidate_ref",
                    "selected_result_ref",
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                    "active_index_version_ref",
                ):
                    self.assertIn(self.module.CONTROL_PREFIX, item[field])
        for item in report["trace_log_control_records"]:
            with self.subTest(trace=item["scenario_id"]):
                self.assertEqual(set(self.module.TRACE_LOG_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_OLD_INDEX_TRACE_VERSION_MATCH_NOT_WRITTEN",
                    item["trace_version_state"],
                )
                self.assertEqual("CONTROL_TRACE_LOG_NOT_PERSISTED", item["log_state"])
                self.assertFalse(item["actual_trace_log_written"])
                self.assertTrue(item["human_handling_required"])
                for field in (
                    "trace_log_ref",
                    "retrieval_trace_ref",
                    "active_index_version_ref",
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                    "evidence_ledger_ref",
                ):
                    self.assertIn(self.module.CONTROL_PREFIX, item[field])

    def test_filter_results_and_validity_reports_are_control_only(self):
        report = self.report()
        for item in report["filter_result_control_records"]:
            with self.subTest(filter=item["scenario_id"]):
                self.assertEqual(set(self.module.FILTER_RESULT_FIELDS), set(item))
                self.assertGreaterEqual(item["filter_reference_count"], 1)
                self.assertEqual(
                    "CONTROL_FILTER_RESULT_NOT_EVALUATED_OR_PERSISTED",
                    item["result_state"],
                )
                self.assertFalse(item["actual_metadata_filter_evaluation_performed"])
                self.assertFalse(item["actual_filter_result_written"])
                self.assertTrue(item["human_handling_required"])
                self.assertTrue(
                    all(
                        self.module.CONTROL_PREFIX in ref
                        for ref in item["metadata_filter_refs"]
                    )
                )
        for item in report["validity_test_report_control_records"]:
            with self.subTest(validity=item["scenario_id"]):
                self.assertEqual(set(self.module.VALIDITY_TEST_REPORT_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_RESULT_VALIDITY_DECLARED_NOT_EXECUTED",
                    item["observed_result_validity_state"],
                )
                self.assertEqual(
                    "CONTROL_VALIDITY_TEST_REPORT_NOT_EXECUTED_OR_PERSISTED",
                    item["report_state"],
                )
                self.assertFalse(item["actual_validity_test_executed"])
                self.assertTrue(item["human_handling_required"])
                for field in (
                    "validity_test_report_ref",
                    "requested_top_k_ref",
                    "hybrid_score_ref",
                    "score_explanation_ref",
                    "selected_result_ref",
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                ):
                    self.assertIn(self.module.CONTROL_PREFIX, item[field])

    def test_evidence_gap_records_are_explicit_and_not_automatically_resolved(self):
        report = self.report()
        self.assertEqual(8, len(report["evidence_gap_control_records"]))
        for item in report["evidence_gap_control_records"]:
            with self.subTest(gap=item["scenario_id"]):
                self.assertEqual(set(self.module.EVIDENCE_GAP_FIELDS), set(item))
                self.assertEqual(
                    "CONTROL_RETRIEVAL_INSUFFICIENCY_OR_EVIDENCE_GAP_REQUIRES_WHITEBOX",
                    item["gap_state"],
                )
                self.assertEqual(
                    "CONTROL_AUTOMATIC_GAP_RESOLUTION_DISABLED",
                    item["gap_resolution_state"],
                )
                self.assertFalse(item["actual_evidence_gap_record_written"])
                self.assertFalse(item["automatic_resolution_allowed"])
                self.assertTrue(item["human_handling_required"])
                for field in (
                    "evidence_gap_record_ref",
                    "evidence_ledger_ref",
                    "embedding_model_ref",
                    "embedding_model_version_ref",
                    "vector_dimension_ref",
                    "similarity_metric_ref",
                ):
                    self.assertIn(self.module.CONTROL_PREFIX, item[field])

    def test_parameter_rollback_instructions_do_not_change_live_parameters(self):
        report = self.report()
        self.assertEqual(
            4, len(report["parameter_rollback_instruction_control_records"])
        )
        for item in report["parameter_rollback_instruction_control_records"]:
            with self.subTest(instruction=item["instruction_id"]):
                self.assertEqual(
                    set(self.module.PARAMETER_ROLLBACK_INSTRUCTION_FIELDS), set(item)
                )
                self.assertEqual(
                    "VERSIONED_PARAMETER_CHANGE_AND_BUSINESS_LINE_WHITEBOX_APPROVAL_REQUIRED",
                    item["entry_precondition"],
                )
                self.assertEqual(
                    "CONTROL_NO_LIVE_RETRIEVAL_PARAMETER_TO_ROLLBACK",
                    item["rollback_state"],
                )
                self.assertFalse(
                    item["actual_retrieval_parameter_rollback_performed"]
                )
                self.assertTrue(item["human_handling_required"])
                self.assertIn(self.module.CONTROL_PREFIX, item["parameter_scope_ref"])
                self.assertIn(self.module.CONTROL_PREFIX, item["rollback_target_ref"])
        self.assertEqual(4, len(report["chinese_feedback"]))

    def test_invalid_or_malformed_phase3_fails_closed(self):
        invalid = self.module.build_metadata_filter_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertEqual(self.module.ENTRY_GATE, invalid["next_gate"])
        self.assertEqual(0, invalid["retrieval_sample_control_record_count"])
        malformed = self.module.build_metadata_filter_phase4_delivery_report(
            lambda: {
                "valid": True,
                "result": self.module.P3_PASS_RESULT,
                "next_gate": self.module.ENTRY_GATE,
                "scenario_results": [],
            }
        )
        self.assertFalse(malformed["valid"])
        self.assertEqual(0, malformed["trace_log_control_record_count"])

    def test_predecessor_runtime_signal_fails_closed(self):
        def runtime_signal():
            altered = copy.deepcopy(
                self.phase3.build_metadata_filter_phase3_report()
            )
            altered["model_token_consumption_performed"] = True
            return altered

        report = self.module.build_metadata_filter_phase4_delivery_report(
            runtime_signal
        )
        self.assertFalse(report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, report["result"])
        self.assertEqual(0, report["delivery_field_check_count"])

    def test_runtime_authority_and_stage_boundaries_stay_closed(self):
        report = self.report()
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["source_document_remains_authoritative"])
        self.assertTrue(
            report["business_line_whitebox_human_review_remains_authoritative"]
        )
        self.assertFalse(
            report["delivery_control_metadata_can_replace_source_document"]
        )
        self.assertFalse(
            report["delivery_control_metadata_can_become_business_fact_authority"]
        )
        self.assertFalse(report["automatic_gap_resolution_allowed"])
        self.assertFalse(report["automatic_business_recommendation_allowed"])
        self.assertFalse(report["automatic_parameter_rollback_allowed"])
        self.assertTrue(report["stage085_started"])
        self.assertTrue(report["phase1_completed"])
        self.assertTrue(report["phase2_completed"])
        self.assertTrue(report["phase3_completed"])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage086_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
