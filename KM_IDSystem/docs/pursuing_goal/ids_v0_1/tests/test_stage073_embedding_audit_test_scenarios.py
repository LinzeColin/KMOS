import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "embedding_audit_test" / "stage073_embedding_audit_test_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_slice_contract.json"
)
PHASE2_SLICE = (
    BASE / "embedding_audit_test" / "stage073_embedding_audit_test_slice.py"
)
CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_scenarios_contract.json"
)
SCENARIOS = (
    BASE / "embedding_audit_test" / "stage073_embedding_audit_test_scenarios.py"
)
SCOPE = BASE / "STAGE073_PHASE3_EMBEDDING_AUDIT_TEST_CONTROLLED_SCENARIOS.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-073_Embedding审计测试.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE072_STAGE_REVIEW.md"
PREDECESSOR_MODEL_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_contract.json"
)
PREDECESSOR_AUDIT_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-20-stage073-p3-local.json"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage073EmbeddingAuditTestPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module("stage073_embedding_audit_test_scenarios", SCENARIOS)

    def _report(self):
        return self.module.build_embedding_audit_test_phase3_report()

    def _phase2(self):
        return _load_module("stage073_embedding_audit_test_phase2", PHASE2_SLICE)

    def test_phase3_artifacts_and_predecessors_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_SLICE,
            CONTRACT,
            SCENARIOS,
            SCOPE,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_MODEL_CONTRACT,
            PREDECESSOR_AUDIT_CONTRACT,
            BATCH,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_has_exact_p3_scope_and_runtime_remains_closed(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage073.embedding_audit_test.phase3.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE073-P3", contract["task_id"])
        self.assertEqual(
            "PHASE3_EMBEDDING_AUDIT_TEST_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["scenario_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE073-P4-GATE", contract["next_gate"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(contract["source_authority"][field])

        replay = contract["phase2_control_slice_replay_contract"]
        self.assertEqual(5, replay["control_request_count"])
        self.assertEqual(10, replay["policy_resolution_record_field_count"])
        self.assertEqual(12, replay["future_embedding_queue_field_count"])
        self.assertEqual(14, replay["embedding_queue_record_field_count"])
        self.assertEqual(10, replay["cache_record_field_count"])
        self.assertEqual(7, replay["failed_retry_record_field_count"])
        self.assertEqual(6, replay["model_version_projection_field_count"])
        self.assertEqual(8, replay["cost_projection_field_count"])
        self.assertEqual(18, replay["external_api_audit_projection_field_count"])

        scenarios = contract["controlled_scenario_contract"]
        self.assertEqual(list(self.module.SCENARIO_RESULT_FIELDS), scenarios["required_fields"])
        self.assertEqual(35, scenarios["field_count"])
        self.assertEqual(5, scenarios["scenario_count"])
        self.assertEqual(
            list(self.module.REQUIRED_SCENARIO_CATEGORIES),
            scenarios["scenario_order"],
        )
        audit = contract["audit_projection_invariant_contract"]
        self.assertEqual(18, audit["inherited_phase2_audit_field_count"])
        self.assertEqual(90, audit["control_audit_field_check_count"])
        self.assertEqual(3, audit["future_external_api_call_candidate_count"])
        self.assertEqual(11, contract["failure_and_stop_contract"]["failure_state_count"])
        self.assertTrue(all(value is False for value in contract["runtime_boundary"].values()))

    def test_report_replays_exact_p2_shape_and_all_five_scenarios(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase2_control_slice_reexecuted"])
        self.assertTrue(report["phase2_shape_preserved"])
        self.assertTrue(report["phase2_side_effect_free"])
        self.assertEqual(5, report["scenario_count"])
        self.assertEqual(5, report["passed_scenario_count"])
        self.assertEqual(5, report["explicit_disposition_count"])
        self.assertEqual(0, report["silent_drop_count"])
        self.assertEqual(4, report["human_handling_required_count"])
        self.assertTrue(report["all_taskpack_special_scenarios_covered"])
        self.assertTrue(report["policy_payload_boundaries_preserved"])
        self.assertTrue(report["queue_cache_retry_boundaries_preserved"])
        self.assertTrue(report["budget_insufficient_pause_preserved"])
        self.assertTrue(report["audit_projection_invariant_preserved"])
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        self.assertEqual(5, report["control_policy_resolution_record_count"])
        self.assertEqual(5, report["control_embedding_queue_record_count"])
        self.assertEqual(5, report["control_cache_record_count"])
        self.assertEqual(5, report["control_failed_retry_record_count"])
        self.assertEqual(5, report["control_model_version_projection_count"])
        self.assertEqual(5, report["control_cost_projection_count"])
        self.assertEqual(5, report["control_external_api_audit_projection_count"])
        self.assertEqual(18, report["control_audit_field_count"])
        self.assertEqual(90, report["control_audit_field_check_count"])
        self.assertEqual(3, report["future_external_api_call_candidate_count"])

    def test_scenario_records_keep_exact_shape_and_control_only_references(self):
        report = self._report()
        self.assertEqual(
            list(self.module.REQUIRED_SCENARIO_CATEGORIES),
            [record["scenario_category"] for record in report["scenario_results"]],
        )
        for record in report["scenario_results"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertEqual(set(self.module.SCENARIO_RESULT_FIELDS), set(record))
                self.assertTrue(record["expectation_met"])
                self.assertFalse(record["silent_drop"])
                self.assertFalse(record["actual_external_api_call_performed"])
                self.assertFalse(record["actual_model_token_consumption_performed"])
                self.assertFalse(record["model_version_sent_to_external_api"])
                self.assertTrue(record["audit_projection_present"])
                self.assertTrue(record["audit_required_fields_present"])
                self.assertTrue(record["audit_reference_fields_are_control_only"])
                for field in (
                    "referenced_policy_resolution_ref",
                    "referenced_embedding_queue_request_ref",
                    "referenced_cache_entry_ref",
                    "referenced_retry_ref",
                    "referenced_external_api_audit_ref",
                ):
                    self.assertIn(":control:stage073-p2:", record[field])

    def test_denied_summary_only_and_full_text_boundaries_are_distinct(self):
        records = {
            item["scenario_category"]: item for item in self._report()["scenario_results"]
        }
        denied = records["DENIED_EGRESS_BLOCK_CONTROL"]
        self.assertEqual("denied", denied["effective_external_api_policy"])
        self.assertEqual("NO_CONTROL_PAYLOAD_REFERENCE", denied["observed_control_payload_scope"])
        self.assertEqual("CONTROL_QUEUE_BLOCKED_POLICY_DENIED", denied["observed_queue_state"])
        self.assertEqual("BLOCKED_POLICY_DENIED", denied["observed_audit_disposition"])
        self.assertFalse(denied["future_external_api_call_candidate"])

        summary = records["SUMMARY_ONLY_REFERENCE_BOUNDARY_CONTROL"]
        restricted = records["DOCUMENT_RESTRICTION_REFERENCE_BOUNDARY_CONTROL"]
        self.assertEqual("summary_only", summary["effective_external_api_policy"])
        self.assertEqual("summary_only", restricted["effective_external_api_policy"])
        self.assertEqual("CONTROL_SUMMARY_REFERENCE_ONLY", summary["observed_control_payload_scope"])
        self.assertEqual("CONTROL_SUMMARY_REFERENCE_ONLY", restricted["observed_control_payload_scope"])
        self.assertTrue(summary["future_external_api_call_candidate"])
        self.assertTrue(restricted["future_external_api_call_candidate"])

        full_text = records["FULL_TEXT_REFERENCE_BOUNDARY_CONTROL"]
        self.assertEqual("full_text_allowed", full_text["effective_external_api_policy"])
        self.assertEqual("CONTROL_CHUNK_TEXT_REFERENCE_ONLY", full_text["observed_control_payload_scope"])
        self.assertTrue(full_text["future_external_api_call_candidate"])

    def test_budget_pause_and_audit_precondition_are_preserved(self):
        report = self._report()
        records = {item["scenario_category"]: item for item in report["scenario_results"]}
        budget = records["BUDGET_INSUFFICIENT_PAUSE_CONTROL"]
        self.assertEqual("CONTROL_BUDGET_INSUFFICIENT", budget["observed_budget_check_state"])
        self.assertEqual("CONTROL_QUEUE_PAUSED_BUDGET_INSUFFICIENT", budget["observed_queue_state"])
        self.assertEqual("CONTROL_CACHE_PAUSED_BUDGET_INSUFFICIENT", budget["observed_cache_disposition"])
        self.assertEqual("CONTROL_RETRY_PAUSED_BUDGET_INSUFFICIENT", budget["observed_retry_state"])
        self.assertFalse(budget["future_external_api_call_candidate"])
        self.assertTrue(report["audit_projection_invariant_preserved"])
        self.assertTrue(report["future_external_api_call_audit_invariant_preserved"])
        for record in report["scenario_results"]:
            with self.subTest(scenario=record["scenario_id"]):
                self.assertTrue(record["audit_projection_required"])
                self.assertTrue(record["audit_projection_present"])
                self.assertEqual(18, record["audit_field_count"])

    def test_invalid_or_malformed_phase2_result_fails_closed(self):
        invalid = self.module.build_embedding_audit_test_phase3_report(
            phase2_executor=lambda _control: {"input_accepted": False}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual(self.module.FAIL_RESULT, invalid["result"])
        self.assertFalse(invalid["phase2_shape_preserved"])
        self.assertFalse(invalid["phase2_side_effect_free"])
        self.assertEqual(0, invalid["passed_scenario_count"])

        phase2 = self._phase2()

        def malformed(_control):
            result = copy.deepcopy(
                phase2.execute_embedding_audit_test_control_slice(
                    phase2.build_control_input()
                )
            )
            result["external_api_audit_projections"][0].pop("provider_ref")
            return result

        malformed_report = self.module.build_embedding_audit_test_phase3_report(
            phase2_executor=malformed
        )
        self.assertFalse(malformed_report["valid"])
        self.assertEqual(self.module.FAIL_RESULT, malformed_report["result"])
        self.assertFalse(malformed_report["phase2_shape_preserved"])

    def test_report_is_control_only_and_has_no_runtime_side_effect_flags(self):
        report = self._report()
        self.assertEqual(0, report["actual_input_request_count"])
        self.assertEqual(0, report["actual_embedding_queue_count"])
        self.assertEqual(0, report["actual_cache_entry_count"])
        self.assertEqual(0, report["actual_failed_retry_count"])
        self.assertEqual(0, report["actual_model_version_record_count"])
        self.assertEqual(0, report["actual_cost_count"])
        self.assertEqual(0, report["actual_external_api_audit_record_count"])
        self.assertEqual(0, report["actual_external_api_call_count"])
        self.assertEqual(0, report["actual_model_token_count"])
        for field in self.module.RUNTIME_CLOSED_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_current_machine_and_governance_projection_preserves_phase3_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        event_ids = {
            item["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
            for item in [json.loads(line)]
        }
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-V0_1-STAGE073-P3",
                    "IDS-V0_1-STAGE073-P3",
                    "IDS-STAGE073-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-V0_1-STAGE073-P4",
                    "IDS-STAGE073-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-V0_1-STAGE073-REVIEW",
                    "IDS-STAGE074-P1-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-V0_1-STAGE074-P1",
                    "IDS-STAGE074-P2-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-V0_1-STAGE074-P2",
                    "IDS-STAGE074-P3-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-V0_1-STAGE074-P3",
                    "IDS-STAGE074-P4-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-V0_1-STAGE074-P4",
                    "IDS-STAGE074-REVIEW-GATE",
                ),
                (
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-V0_1-STAGE074-REVIEW",
                    "IDS-STAGE075-P1-GATE",
                ),
                ('IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'), ('IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-P4', 'IDS-STAGE075-REVIEW-GATE'), ('IDS-V0_1-STAGE075-REVIEW', 'IDS-V0_1-STAGE075-REVIEW', 'IDS-STAGE076-P1-GATE'), ('IDS-V0_1-STAGE076-P1', 'IDS-V0_1-STAGE076-P1', 'IDS-STAGE076-P2-GATE'), ('IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P2', 'IDS-STAGE076-P3-GATE'), ('IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P3', 'IDS-STAGE076-P4-GATE'),
                (
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-V0_1-STAGE076-P4',
                    'IDS-STAGE076-REVIEW-GATE',
                ),
                (
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-V0_1-STAGE076-REVIEW',
                    'IDS-STAGE077-P1-GATE',
                ),

                ('IDS-V0_1-STAGE077-P1', 'IDS-V0_1-STAGE077-P1', 'IDS-STAGE077-P2-GATE'),
                ('IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P2', 'IDS-STAGE077-P3-GATE'), ('IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P3', 'IDS-STAGE077-P4-GATE'), ('IDS-V0_1-STAGE077-P4', 'IDS-V0_1-STAGE077-P4', 'IDS-STAGE077-REVIEW-GATE'), ('IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'),),
        )
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE073-P3",
                "IDS-V0_1-STAGE073-P4",
                "IDS-V0_1-STAGE073-REVIEW",
                "IDS-V0_1-STAGE074-P1",
                "IDS-V0_1-STAGE074-P2",
                "IDS-V0_1-STAGE074-P3",
                "IDS-V0_1-STAGE074-P4",
                "IDS-V0_1-STAGE074-REVIEW",
                'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P4', 'IDS-V0_1-STAGE075-REVIEW',
                'IDS-V0_1-STAGE076-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P1',
            'IDS-V0_1-STAGE076-P2', 'IDS-V0_1-STAGE076-P3', 'IDS-V0_1-STAGE076-P4', 'IDS-V0_1-STAGE076-REVIEW', 'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW"
            , "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4"),
        )
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE-073",
                "ACC-STAGE073-P3-01",
                "ACC-STAGE073-P3-02",
                "ACC-STAGE073-P3-03",
                "ACC-STAGE073-P3-04",
            }.issubset(acceptance_ids)
        )
        self.assertTrue(
            'current_phase_id: "IDS-STAGE073-P3"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE073-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE073-REVIEW"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P1"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P2"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-P4"' in roadmap_text
            or 'current_phase_id: "IDS-STAGE074-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'current_task_id: "IDS-V0_1-STAGE073-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE073-REVIEW"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P1"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P2"' in roadmap_text or 'current_task_id: "IDS-V0_1-STAGE074-P3"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-P4"' in roadmap_text
            or 'current_task_id: "IDS-V0_1-STAGE074-REVIEW"' in roadmap_text
        )
        self.assertTrue(
            'next_gate_id: "IDS-STAGE073-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE073-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-P1-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-P2-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-P3-GATE"' in roadmap_text or 'next_gate_id: "IDS-STAGE074-P4-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE074-REVIEW-GATE"' in roadmap_text
            or 'next_gate_id: "IDS-STAGE075-P1-GATE"' in roadmap_text
        )
        self.assertIn("EVT-IDS-V0_1-STAGE073-P3-20260820-001", event_ids)
        self.assertTrue(RUN.is_file())


if __name__ == "__main__":
    unittest.main()
