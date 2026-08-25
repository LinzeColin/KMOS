import copy
import importlib.util
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE104_PHASE4_RAG_NEGATIVE_TEST_DELIVERY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_delivery_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_delivery.py"
)
P3_SCOPE = BASE / "STAGE104_PHASE3_RAG_NEGATIVE_TEST_SCENARIOS.md"
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_controlled_scenarios.py"
)
P3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p3-local.json"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-104_RAG负向测试.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE103_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage103_model_output_permission_gate_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载控制模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage104RagNegativeTestingPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(
            MODULE, "stage104_rag_negative_testing_delivery"
        )
        cls.phase3 = _load_module(
            P3_MODULE, "stage104_rag_negative_testing_phase3_for_delivery"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase3_report = cls.phase3.build_rag_negative_testing_phase3_report()
        cls.report = cls.module.build_rag_negative_testing_phase4_delivery_report()

    def test_required_scope_contract_modules_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P3_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_single_authority_predecessor_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage104.rag_negative_testing.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-104", contract["stage"])
        self.assertEqual("IDS-STAGE104-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE104-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-104", contract["acceptance_id"])
        self.assertEqual("IDS-STAGE104-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE104-REVIEW-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(source["delivery_control_metadata_can_replace_source_document"])
        self.assertFalse(source["delivery_control_metadata_can_become_business_fact_authority"])
        self.assertFalse(source["second_authoritative_source_created"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        predecessor = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(self.module.P3_SCHEMA_VERSION, predecessor["predecessor_schema_version_required"])
        self.assertEqual(self.module.P3_RECORD_KIND, predecessor["predecessor_record_kind_required"])
        self.assertEqual(self.module.P3_PASS_RESULT, predecessor["predecessor_pass_result_required"])
        self.assertEqual(5, predecessor["scenario_count"])
        self.assertEqual(34, predecessor["scenario_field_count"])
        self.assertEqual(170, predecessor["scenario_field_check_count"])
        self.assertEqual(8, predecessor["reproducibility_tuple_field_count"])
        self.assertFalse(predecessor["actual_phase3_runtime_execution_allowed"])

        boundary = contract["stage_boundary"]
        for field in (
            "stage103_review_evidence_declared",
            "stage104_started",
            "stage104_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage104_review_started",
            "stage105_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_delivery_shapes_and_reproducibility_tuple_are_preserved(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE104-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE104-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(384, report["delivery_field_check_count"])
        for group_name, fields in self.module.DELIVERY_GROUPS:
            expected_count = 2 if group_name == "rollback_and_fallback_control_records" else 5
            records = report[group_name]
            with self.subTest(group=group_name):
                self.assertEqual(expected_count, len(records))
            for record in records:
                with self.subTest(group=group_name, record=record):
                    self.assertEqual(set(fields), set(record))
                    for field, value in record.items():
                        if field == "evidence_gap_ref" and value is None:
                            continue
                        if field.endswith("_ref") or field in {
                            "delivery_record_id",
                            "instruction_id",
                        }:
                            self.assertTrue(
                                value.startswith(":control:stage104-p2:")
                                or value.startswith(":control:stage104-p4:")
                            )
        for record in report["answer_sample_control_records"] + report[
            "reproducible_log_control_records"
        ]:
            with self.subTest(record=record):
                for field in self.module.REPRODUCIBILITY_TUPLE_FIELDS:
                    self.assertTrue(record[field].startswith(":control:stage104-p2:"))

    def test_negative_semantics_output_permissions_and_evidence_gap_are_preserved(self):
        negative = {
            item["scenario_id"]: item
            for item in self.report["negative_test_result_control_records"]
        }
        instruction = negative[
            "document_instruction_cannot_override_ids_rule_control"
        ]
        self.assertEqual(
            "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
            instruction["document_instruction_evidence_state"],
        )
        self.assertEqual("CONTROL_IDS_RULES_PREVAIL", instruction["ids_rule_precedence_state"])
        self.assertEqual(
            "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
            instruction["injection_defense_state"],
        )
        answers = {
            item["scenario_id"]: item
            for item in self.report["answer_sample_control_records"]
        }
        gap = answers[
            "evidence_gap_cannot_masquerade_as_internal_experience_control"
        ]
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage104-p2:"))
        self.assertEqual(
            "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED", gap["final_conclusion_state"]
        )
        for record in self.report["prompt_version_control_records"]:
            with self.subTest(record=record):
                self.assertTrue(record["future_model_reasoning_candidate_declared"])
                self.assertFalse(record["actual_model_call_performed"])
                self.assertFalse(record["actual_model_token_consumption_performed"])
                self.assertFalse(record["actual_prompt_or_model_configuration_accessed"])
        boundaries = {
            item["scenario_id"]: item
            for item in self.report["output_permission_boundary_control_records"]
        }
        for scenario_id in self.module.HIGH_RISK_SCENARIO_IDS:
            boundary = boundaries[scenario_id]
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                    boundary["output_permission_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    boundary["final_conclusion_state"],
                )
                self.assertTrue(boundary["human_handling_required"])
                self.assertFalse(boundary["business_line_whitebox_human_approval_recorded"])
                self.assertFalse(boundary["automatic_final_conclusion_allowed"])
                self.assertFalse(boundary["actual_human_confirmation_performed"])
                self.assertFalse(boundary["actual_answer_published"])

    def test_prompt_rollback_and_model_fallback_are_explicit_future_controls(self):
        records = self.report["rollback_and_fallback_control_records"]
        self.assertEqual(
            {"prompt_rollback", "model_configuration_fallback"},
            {record["control_domain"] for record in records},
        )
        for record in records:
            with self.subTest(domain=record["control_domain"]):
                self.assertEqual(self.module.P3_PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["business_line_whitebox_approval_required"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_prompt_rollback_performed"])
                self.assertFalse(record["actual_model_configuration_fallback_performed"])
                self.assertFalse(record["persistent_state_write_performed"])

    def test_invalid_or_tampered_phase3_output_fails_closed(self):
        invalid = self.module.build_rag_negative_testing_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", invalid["failure_state"])
        self.assertEqual("IDS-STAGE104-P4-GATE", invalid["next_gate"])
        self.assertEqual([], invalid["answer_sample_control_records"])

        def replay_with(mutator):
            result = copy.deepcopy(self.phase3_report)
            mutator(result)
            return self.module.build_rag_negative_testing_phase4_delivery_report(
                lambda: result
            )

        injection = replay_with(
            lambda result: result["scenario_results"][0].update(
                {"ids_rule_precedence_state": "DOCUMENT_INSTRUCTION_CAN_OVERRIDE_IDS_RULE"}
            )
        )
        self.assertEqual(
            "DOCUMENT_INSTRUCTION_PRECEDENCE_PROTECTION_MISSING",
            injection["failure_state"],
        )
        gap = replay_with(
            lambda result: result["scenario_results"][1].update(
                {"internal_evidence_ref": ":control:stage104-p2:misclassified:reference-only"}
            )
        )
        self.assertEqual("EVIDENCE_GAP_SEMANTICS_MISSING", gap["failure_state"])
        high_risk_index = self.module.P3_SCENARIO_IDS.index(
            "high_risk_engineering_advice_requires_whitebox_confirmation_control"
        )
        high_risk = replay_with(
            lambda result: result["scenario_results"][high_risk_index].update(
                {"final_conclusion_state": "CONTROL_FINAL_CONCLUSION_PUBLISHED"}
            )
        )
        self.assertEqual("HIGH_RISK_OUTPUT_PERMISSION_MISSING", high_risk["failure_state"])
        runtime = replay_with(
            lambda result: result["runtime_boundary"].update(
                {"model_call_performed": True}
            )
        )
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", runtime["failure_state"])
        opaque = replay_with(
            lambda result: result["scenario_results"][0].update(
                {"document_instruction_candidate_ref": "not-a-control-reference"}
            )
        )
        self.assertEqual("CONTROL_REFERENCE_NOT_OPAQUE", opaque["failure_state"])
        for report in (invalid, injection, gap, high_risk, runtime, opaque):
            with self.subTest(failure=report["failure_state"]):
                self.assertEqual([], report["answer_sample_control_records"])
                self.assertTrue(
                    all(value is False for value in report["runtime_boundary"].values())
                )
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in report.items()
                        if key.startswith("actual_") and key.endswith("_count")
                    )
                )

    def test_runtime_authority_and_protected_surfaces_remain_closed(self):
        self.assertFalse(self.report["second_authoritative_source_created"])
        self.assertFalse(self.report["persistent_record_created"])
        for field, value in self.report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        for field, value in self.report["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        for section in (
            "runtime_boundary",
            "protected_surface_boundary",
            "future_runtime_prerequisite_contract",
        ):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_failure_contract_scope_and_current_governance_projection_are_complete(self):
        self.assertEqual(
            list(self.module.FAILURE_STATES),
            self.contract["failure_and_stop_contract"]["declared_failure_states"],
        )
        self.assertEqual(16, self.contract["failure_and_stop_contract"]["failure_state_count"])
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["enterprise_chinese_only"])
        self.assertFalse(feedback["published"])
        self.assertEqual(4, feedback["feedback_count"])
        self.assertEqual(feedback["messages"], self.report["chinese_feedback"])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "唯一控制上下文",
            "reference-only",
            "回答样例",
            "负向测试结果",
            "prompt/version",
            "可复现日志",
            "模型输出权限边界",
            "业务线白箱人工确认",
            "模型 Token",
            "IDS-STAGE104-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase3_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P3",
            "IDS-V0_1-STAGE104-P3",
            "IDS-STAGE104-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P4",
            "IDS-V0_1-STAGE104-P4",
            "IDS-STAGE104-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-REVIEW",
            "IDS-V0_1-STAGE104-REVIEW",
            "IDS-STAGE105-P1-GATE",
        )
        stage105_phase1_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P1",
            "IDS-V0_1-STAGE105-P1",
            "IDS-STAGE105-P2-GATE",
        )
        stage105_phase2_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P2",
            "IDS-V0_1-STAGE105-P2",
            "IDS-STAGE105-P3-GATE",
        )
        stage105_phase3_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P3",
            "IDS-V0_1-STAGE105-P3",
            "IDS-STAGE105-P4-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase3_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        if current == phase4_current:
            self.assertTrue(is_current_projection)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual(self.module.PASS_RESULT, receipt["result"])
            self.assertEqual("IDS-STAGE104-REVIEW-GATE", receipt["next_gate"])
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
            validation = receipt["validation"]
            self.assertEqual(8, validation["focused_delivery_test_count"])
            self.assertEqual(32, validation["explicit_predecessor_focused_test_count"])
            self.assertEqual(805, validation["historical_whitebox_chain_test_count"])
            for field in (
                "full_whitebox_validation_recorded",
                "stage005_governance_valid",
                "batch041_050_review_valid",
                "batch051_060_review_valid",
                "document_budget_passed",
                "blocker_stop_passed",
                "dual_plane_passed",
                "final_validation_recorded",
            ):
                with self.subTest(validation_field=field):
                    self.assertTrue(validation[field])
            self.assertEqual(7, validation["human_view_rendered_file_count"])
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("P1/P2/P3/P4 控制工件已完成", acceptance_by_id["ACC-STAGE-104"])
            for acceptance_id in (
                "ACC-STAGE104-P4-01",
                "ACC-STAGE104-P4-02",
                "ACC-STAGE104-P4-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE104-P4-04"])
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE104-P4-20260826-001", event_ids)
        elif current == review_current:
            self.assertTrue(is_current_projection)
        elif current in {
            stage105_phase1_current,
            stage105_phase2_current,
            stage105_phase3_current,
        }:
            self.assertIn(
                current,
                {
                    stage105_phase1_current,
                    stage105_phase2_current,
                    stage105_phase3_current,
                },
            )
            self.assertTrue(is_current_projection)
        else:
            self.assertEqual(phase3_current, current)
            self.assertFalse(is_current_projection)


if __name__ == "__main__":
    unittest.main()
