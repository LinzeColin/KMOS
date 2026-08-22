import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE088_PHASE4_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage088_retrieval_result_validity_delivery_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage088_retrieval_result_validity_delivery.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-088_检索结果有效性门禁.md"
)
P1_SCOPE = BASE / "STAGE088_PHASE1_RETRIEVAL_RESULT_VALIDITY_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage088_retrieval_result_validity_contract.json"
P2_SCOPE = BASE / "STAGE088_PHASE2_RETRIEVAL_RESULT_VALIDITY_CONTROL_SLICE.md"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage088_retrieval_result_validity_slice_contract.json"
)
P2_SLICE = BASE / "index_version_schema" / "stage088_retrieval_result_validity_control_slice.py"
P3_SCOPE = BASE / "STAGE088_PHASE3_RETRIEVAL_RESULT_VALIDITY_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE / "index_version_schema" / "stage088_retrieval_result_validity_scenarios_contract.json"
)
P3_MODULE = (
    BASE / "index_version_schema" / "stage088_retrieval_result_validity_controlled_scenarios.py"
)
P3_RUN = ROOT / "machine" / "runs" / "2026-08-23-stage088-p3-local.json"
STAGE087_REVIEW = BASE / "STAGE087_STAGE_REVIEW.md"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage088RetrievalResultValidityPhase4DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module("stage088_p4", MODULE)
        cls.phase3 = _load_module("stage088_p3", P3_MODULE)

    def _report(self):
        return self.module.build_retrieval_result_validity_phase4_delivery_report()

    def _phase3_report(self):
        return self.phase3.build_retrieval_result_validity_phase3_report()

    def test_phase4_artifacts_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P1_SCOPE,
            P1_CONTRACT,
            P2_SCOPE,
            P2_CONTRACT,
            P2_SLICE,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P3_RUN,
            STAGE087_REVIEW,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_authority_and_review_gate_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage088.retrieval_result_validity.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-088", contract["stage"])
        self.assertEqual("IDS-STAGE088-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE088-P4", contract["task_id"])
        self.assertEqual(
            "PHASE4_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE088-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE088-REVIEW-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(
            source["business_line_whitebox_human_review_remains_authoritative"]
        )
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
                self.assertFalse(source[field])

    def test_contract_replay_delivery_and_runtime_shapes_are_exact(self):
        replay = self.contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(6, replay["required_control_request_count"])
        self.assertEqual(528, replay["phase2_control_field_check_count"])
        self.assertEqual(8, replay["scenario_count"])
        self.assertEqual(33, replay["scenario_field_count"])
        self.assertEqual(264, replay["scenario_field_check_count"])
        for field in (
            "keyword_and_domain_coverage_required",
            "vector_baseline_and_vector_only_rejection_required",
            "vector_only_rejection_required",
            "six_dimension_filter_combination_required",
            "active_index_version_contract_required",
            "candidate_selected_score_trace_evidence_chain_required",
            "top_k_ranking_and_validity_required",
            "result_validity_gate_chain_required",
            "result_validity_not_evaluated_required",
            "validity_gate_pending_human_whitebox_required",
            "old_index_trace_version_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(replay[field])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertTrue(delivery["delivery_executable"])
        self.assertFalse(delivery["execution_ready"])
        self.assertTrue(delivery["metadata_only"])
        self.assertTrue(delivery["validity_gate_control_reference_preserved"])
        self.assertEqual(572, delivery["delivery_field_check_count"])
        self.assertEqual(4, delivery["chinese_feedback_count"])
        expected_shapes = (
            ("retrieval_sample_control_record_count", 8, "retrieval_sample_field_count", 14),
            ("trace_log_control_record_count", 8, "trace_log_field_count", 14),
            ("filter_result_control_record_count", 8, "filter_result_field_count", 10),
            ("validity_test_report_control_record_count", 8, "validity_test_report_field_count", 15),
            ("evidence_gap_control_record_count", 8, "evidence_gap_field_count", 14),
            ("parameter_rollback_instruction_count", 4, "parameter_rollback_instruction_field_count", 9),
        )
        for count_key, count, field_key, field_count in expected_shapes:
            with self.subTest(count_key=count_key):
                self.assertEqual(count, delivery[count_key])
                self.assertEqual(field_count, delivery[field_key])
        failure = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failure["failure_state_count"], len(failure["declared_failure_states"])
        )
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertIn(value, (False, 0))

    def test_report_replays_p3_and_produces_complete_delivery_evidence(self):
        report = self._report()
        self.assertTrue(report["valid"], report)
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_controlled_scenarios_report_valid"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertEqual(572, report["delivery_field_check_count"])
        self.assertTrue(report["all_delivery_references_control_only"])

    def test_all_delivery_groups_keep_exact_shapes_and_scenario_order(self):
        report = self._report()
        expected_ids = [item["scenario_id"] for item in self.phase3.SCENARIOS]
        groups = (
            ("retrieval_sample_control_records", self.module.RETRIEVAL_SAMPLE_FIELDS),
            ("trace_log_control_records", self.module.TRACE_LOG_FIELDS),
            ("filter_result_control_records", self.module.FILTER_RESULT_FIELDS),
            (
                "validity_test_report_control_records",
                self.module.VALIDITY_TEST_REPORT_FIELDS,
            ),
            ("evidence_gap_control_records", self.module.EVIDENCE_GAP_FIELDS),
        )
        for group_name, fields in groups:
            with self.subTest(group=group_name):
                records = report[group_name]
                self.assertEqual(expected_ids, [item["scenario_id"] for item in records])
                self.assertTrue(all(set(item) == set(fields) for item in records))

    def test_samples_and_trace_logs_are_unpersisted_control_references(self):
        report = self._report()
        for sample in report["retrieval_sample_control_records"]:
            with self.subTest(sample=sample["scenario_id"]):
                self.assertEqual("CONTROL_RETRIEVAL_SAMPLE_NOT_PERSISTED", sample["sample_state"])
                self.assertFalse(sample["actual_retrieval_sample_written"])
                self.assertTrue(sample["human_handling_required"])
                self.assertIn(self.module.CONTROL_PREFIX, sample["retrieval_sample_ref"])
        traces = {item["scenario_id"]: item for item in report["trace_log_control_records"]}
        self.assertEqual(
            "CONTROL_OLD_INDEX_VERSION_TRACE_DECLARED_NOT_READ_OR_WRITTEN",
            traces["old_index_service_trace_version_control"]["trace_version_state"],
        )
        for trace in traces.values():
            with self.subTest(trace=trace["scenario_id"]):
                self.assertEqual("CONTROL_TRACE_LOG_NOT_PERSISTED", trace["log_state"])
                self.assertFalse(trace["actual_trace_log_written"])
                self.assertIn(self.module.CONTROL_PREFIX, trace["trace_log_ref"])

    def test_filter_validity_and_evidence_gap_records_remain_control_only(self):
        report = self._report()
        for item in report["filter_result_control_records"]:
            with self.subTest(filter=item["scenario_id"]):
                self.assertGreater(item["filter_reference_count"], 0)
                self.assertEqual(
                    item["filter_reference_count"], len(item["metadata_filter_refs"])
                )
                self.assertFalse(item["actual_metadata_filter_evaluation_performed"])
                self.assertFalse(item["actual_filter_result_written"])
        validity = {
            item["scenario_id"]: item
            for item in report["validity_test_report_control_records"]
        }
        self.assertEqual(
            "CONTROL_RESULT_VALIDITY_NOT_EVALUATED",
            validity["top_k_ranking_explanation_result_validity_control"][
                "observed_result_validity_state"
            ],
        )
        for item in validity.values():
            with self.subTest(validity=item["scenario_id"]):
                self.assertFalse(item["actual_validity_test_executed"])
                self.assertEqual(
                    "CONTROL_VALIDITY_TEST_REPORT_NOT_EXECUTED_OR_PERSISTED",
                    item["report_state"],
                )
                self.assertIn(self.module.CONTROL_PREFIX, item["validity_gate_ref"])
        for item in report["evidence_gap_control_records"]:
            with self.subTest(gap=item["scenario_id"]):
                self.assertEqual(
                    "CONTROL_AUTOMATIC_GAP_RESOLUTION_DISABLED",
                    item["gap_resolution_state"],
                )
                self.assertFalse(item["automatic_resolution_allowed"])
                self.assertFalse(item["actual_evidence_gap_record_written"])

    def test_parameter_rollback_instructions_are_future_only_and_whitebox_gated(self):
        report = self._report()
        instructions = report["parameter_rollback_instruction_control_records"]
        self.assertEqual(4, len(instructions))
        self.assertTrue(
            all(
                set(item) == set(self.module.PARAMETER_ROLLBACK_INSTRUCTION_FIELDS)
                for item in instructions
            )
        )
        for item in instructions:
            with self.subTest(instruction=item["instruction_id"]):
                self.assertEqual(
                    "VERSIONED_PARAMETER_CHANGE_AND_BUSINESS_LINE_WHITEBOX_APPROVAL_REQUIRED",
                    item["entry_precondition"],
                )
                self.assertEqual(
                    "CONTROL_NO_LIVE_RETRIEVAL_PARAMETER_TO_ROLLBACK",
                    item["rollback_state"],
                )
                self.assertFalse(item["actual_retrieval_parameter_rollback_performed"])
                self.assertTrue(item["human_handling_required"])

    def test_malformed_phase3_report_fails_closed_without_delivery_records(self):
        altered = copy.deepcopy(self._phase3_report())
        altered["phase2_control_record_field_check_count"] = 527
        failed = self.module.build_retrieval_result_validity_phase4_delivery_report(lambda: altered)
        self.assertFalse(failed["valid"])
        self.assertEqual(self.module.FAIL_RESULT, failed["result"])
        self.assertEqual("PHASE3_CONTROL_SHAPE_MISMATCH", failed["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, failed["next_gate"])
        self.assertEqual([], failed["retrieval_sample_control_records"])
        self.assertEqual(0, failed["delivery_field_check_count"])

    def test_phase3_runtime_signal_fails_closed_without_delivery_records(self):
        altered = copy.deepcopy(self._phase3_report())
        altered["model_token_consumption_performed"] = True
        failed = self.module.build_retrieval_result_validity_phase4_delivery_report(lambda: altered)
        self.assertFalse(failed["valid"])
        self.assertFalse(failed["phase3_controlled_scenarios_report_valid"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])
        self.assertEqual([], failed["trace_log_control_records"])
        self.assertEqual([], failed["evidence_gap_control_records"])

    def test_zero_runtime_phase_boundaries_and_chinese_feedback_are_explicit(self):
        report = self._report()
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        for field in (
            "actual_input_request_count",
            "actual_keyword_retrieval_query_count",
            "actual_vector_retrieval_query_count",
            "actual_embedding_generation_count",
            "actual_metadata_filter_evaluation_count",
            "actual_hybrid_ranking_count",
            "actual_top_k_selection_count",
            "actual_retrieval_trace_access_count",
            "actual_evidence_ledger_access_count",
            "actual_retrieval_sample_record_write_count",
            "actual_trace_log_record_write_count",
            "actual_filter_result_record_write_count",
            "actual_validity_test_report_write_count",
            "actual_evidence_gap_record_write_count",
            "actual_retrieval_parameter_rollback_count",
        ):
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        self.assertTrue(report["stage088_started"])
        self.assertTrue(report["phase1_completed"])
        self.assertTrue(report["phase2_completed"])
        self.assertTrue(report["phase3_completed"])
        self.assertTrue(report["phase4_started"])
        self.assertFalse(report["whole_stage_review_performed"])
        self.assertFalse(report["stage088_review_started"])
        self.assertFalse(report["stage089_started"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        self.assertEqual(4, len(report["chinese_feedback"]))
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
