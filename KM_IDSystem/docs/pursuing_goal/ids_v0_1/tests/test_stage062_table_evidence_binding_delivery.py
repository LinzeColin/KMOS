import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_contract.json"
)
PHASE2_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage062_table_evidence_binding_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_slice.py"
)
PHASE3_CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage062_table_evidence_binding_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_scenarios.py"
)
CLOSEOUT = BASE / "STAGE062_PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_CLOSEOUT.md"
CONTRACT = (
    BASE
    / "structured_table_facts"
    / "stage062_table_evidence_binding_delivery_contract.json"
)
DELIVERY = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_delivery.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage062-p4-local.json"

EXPECTED_SCENARIO_IDS = [
    "empty-table-binding-control-human-handling",
    "merged-cells-binding-control-human-handling",
    "unit-confusion-binding-control-human-handling",
    "date-variation-binding-control-human-handling",
    "outlier-binding-control-numeric-block",
    "duplicate-row-binding-control-human-handling",
]


class Stage062TableEvidenceBindingPhase4DeliveryTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage062_p4", DELIVERY)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = (
                self._module().build_table_evidence_binding_phase4_delivery_report()
            )
        return self.__class__._report_value

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_phase4_primary_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            CLOSEOUT,
            CONTRACT,
            DELIVERY,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_identity_and_zero_runtime_boundary(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage062.table_evidence_binding.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE062-P4", contract["task_id"])
        self.assertTrue(contract["delivery_evidence_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE062-REVIEW-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertTrue(
            contract["ownership_boundary"]
            ["stage062_phase1_phase2_phase3_reused_as_reference_only"]
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["ovh_deployment_performed"])

    def test_delivery_report_derives_six_control_samples(self):
        report = self._report()
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE062-REVIEW-GATE", report["next_gate"])
        self.assertEqual(6, len(report["delivery_samples"]))
        self.assertEqual(
            EXPECTED_SCENARIO_IDS,
            [item["scenario_id"] for item in report["delivery_samples"]],
        )

    def test_delivery_samples_keep_control_references_without_real_outputs(self):
        for sample in self._report()["delivery_samples"]:
            with self.subTest(sample=sample["sample_id"]):
                self.assertEqual(
                    "DELIVERY_METADATA_ONLY_TABLE_EVIDENCE_BINDING_SAMPLE_NOT_REAL_EVIDENCE_BINDING",
                    sample["sample_kind"],
                )
                self.assertTrue(sample["control_metadata_only"])
                self.assertTrue(
                    all(
                        ":control:" in sample[field]
                        for field in (
                            "referenced_table_evidence_binding_ref",
                            "referenced_binding_request_ref",
                            "referenced_fact_ref",
                            "evidence_id",
                            "document_id",
                            "sheet",
                            "row",
                            "column",
                            "source_uri",
                        )
                    )
                )
                self.assertFalse(sample["source_content_retained"])
                self.assertFalse(sample["typed_value_retained"])
                self.assertFalse(sample["actual_structured_fact_created"])
                self.assertFalse(sample["actual_table_evidence_binding_created"])

    def test_field_inference_report_keeps_six_reference_labels_only(self):
        report = self._report()["field_inference_report"]
        self.assertEqual(
            "CONTROLLED_TABLE_EVIDENCE_BINDING_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE",
            report["report_kind"],
        )
        self.assertEqual(2, report["table_evidence_binding_candidate_pool_count"])
        self.assertEqual(6, report["referenced_field_label_count"])
        self.assertEqual(6, report["scenario_reference_count"])
        self.assertTrue(report["control_reference_only"])
        self.assertFalse(report["actual_field_mapping_created"])
        self.assertFalse(report["real_table_schema_inference_performed"])
        self.assertFalse(report["real_table_evidence_binding_performed"])

    def test_quality_test_results_remain_control_only(self):
        results = self._report()["quality_test_results"]
        self.assertEqual(
            "CONTROLLED_TABLE_EVIDENCE_BINDING_TEST_RESULT_NOT_REAL_TABLE_VALIDATION",
            results["report_kind"],
        )
        self.assertEqual(6, results["scenario_count"])
        self.assertEqual(6, results["passed_scenario_count"])
        self.assertEqual(6, results["explicit_disposition_count"])
        self.assertEqual(0, results["silent_drop_count"])
        self.assertEqual(1, results["outlier_numeric_block_count"])
        self.assertTrue(results["all_taskpack_exception_categories_covered"])
        self.assertFalse(results["actual_table_evidence_binding_validation_performed"])

    def test_unrecognized_structure_requires_human_handling(self):
        records = {
            item["scenario_id"]: item
            for item in self._report()["unrecognized_structure_and_human_handling"]
        }
        self.assertEqual(6, len(records))
        merged = records["merged-cells-binding-control-human-handling"]
        self.assertEqual(
            "UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING",
            merged["handling_disposition"],
        )
        self.assertTrue(merged["human_handling_required"])
        self.assertIn("人工", merged["recommendation_zh"])
        self.assertFalse(merged["actual_unrecognized_table_structure_observed"])
        self.assertFalse(merged["automatic_structure_resolution_performed"])

    def test_reparse_and_fact_rollback_remain_non_operational(self):
        instructions = self._report()["reparse_and_fact_rollback_instructions"]
        self.assertEqual(
            "TABLE_EVIDENCE_BINDING_REPARSE_AND_FACT_ROLLBACK_INSTRUCTIONS_CONTROL_REPLAY_ONLY",
            instructions["record_kind"],
        )
        self.assertEqual(
            "PHASE3_TABLE_EVIDENCE_BINDING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            instructions["return_to"],
        )
        self.assertTrue(instructions["in_memory_control_replay_only"])
        self.assertFalse(instructions["actual_file_reparse_performed"])
        self.assertFalse(instructions["actual_fact_rollback_performed"])
        self.assertFalse(instructions["actual_table_evidence_binding_rollback_performed"])
        self.assertFalse(instructions["source_or_raw_data_change_allowed"])
        self.assertFalse(instructions["database_or_persistent_state_change_allowed"])

    def test_chinese_prompts_require_human_confirmation_without_auto_action(self):
        prompts = self._report()["human_confirmation_prompts_zh"]
        self.assertEqual(3, len(prompts))
        for prompt in prompts:
            with self.subTest(prompt=prompt["prompt_id"]):
                self.assertIn("请", prompt["text"])
                self.assertFalse(prompt["automatic_confirmation_performed"])

    def test_all_runtime_side_effects_remain_false(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "table_summary_generation_performed",
            "numeric_statistic_computation_performed",
            "source_location_binding_performed",
            "evidence_binding_performed",
            "database_connection_performed",
            "structured_fact_write_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_governance_projection_preserves_phase4_evidence_or_review_successor(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        roadmap = ROADMAP.read_text(encoding="utf-8")
        batch = BATCH.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        self.assertIn(status["stage"], ("IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE062-P4", "IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW-GATE"),
                ("IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
            ),
        )
        self.assertIn(plan["phase"], ("IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2"))
        self.assertTrue(
            "IDS-STAGE062-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P3-GATE" in plan["stop_condition"]
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            "ACC-STAGE062-P4-01",
            {item["id"] for item in acceptance["items"]},
        )
        self.assertIn("IDS-STAGE062-P4", roadmap)
        self.assertIn("IDS-STAGE062-REVIEW-GATE", roadmap)
        self.assertIn("stage062_phase4_completed_review_pending", batch)
        self.assertIn("EVT-IDS-V0_1-STAGE062-P4-20260814-001", events)

    def test_local_run_is_phase4_only(self):
        run = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual("RUN-IDS-STAGE062-P4-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE062", run["stage"])
        self.assertEqual("IDS-V0_1-STAGE062-P4", run["task_id"])
        self.assertEqual("IDS-STAGE062-REVIEW-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertFalse(run["observed_work"]["github_upload_performed"])

    def test_tampered_predecessor_is_rejected(self):
        report = self._module().build_table_evidence_binding_phase4_delivery_report(
            lambda: {"valid": True, "result": "tampered"}
        )
        self.assertFalse(report["valid"])
        self.assertEqual("FAIL_TABLE_EVIDENCE_BINDING_DELIVERY_EVIDENCE", report["result"])
        self.assertEqual([], report["delivery_samples"])


if __name__ == "__main__":
    unittest.main()
