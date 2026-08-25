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
SCOPE = BASE / "STAGE100_PHASE4_NO_INTERNAL_EVIDENCE_STRATEGY_DELIVERY_EVIDENCE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_delivery_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_delivery.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-100_无内部依据策略.md"
)
PHASE3_SCOPE = BASE / "STAGE100_PHASE3_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_controlled_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_controlled_scenarios.py"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p3-local.json"
PHASE2_SCOPE = BASE / "STAGE100_PHASE2_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_control_slice_contract.json"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p2-local.json"
PHASE1_SCOPE = BASE / "STAGE100_PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage100_no_internal_evidence_strategy_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE099_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage100NoInternalEvidenceStrategyPhase4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module(MODULE, "stage100_no_internal_evidence_delivery")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_no_internal_evidence_strategy_phase4_delivery_report()

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE3_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_RECEIPT,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage100.no_internal_evidence_strategy.phase4.delivery.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-100", contract["stage"])
        self.assertEqual("IDS-STAGE100-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE100-P4", contract["task_id"])
        self.assertEqual("ACC-STAGE-100", contract["acceptance_id"])
        self.assertEqual(
            "PHASE4_NO_INTERNAL_EVIDENCE_STRATEGY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE100-P4-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE100-REVIEW-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE100_TASKPACK_STAGE100_PHASE1_PHASE2_PHASE3_AND_STAGE099_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        replay = contract["phase3_controlled_scenario_replay_contract"]
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            replay["predecessor_pass_result_required"],
        )
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(21, replay["phase2_input_field_count"])
        self.assertEqual(4, replay["phase2_projection_group_count"])
        self.assertEqual(38, replay["phase2_projection_field_count_per_request"])
        self.assertEqual(228, replay["phase2_field_check_count"])
        self.assertEqual(6, replay["scenario_count"])
        self.assertEqual(29, replay["scenario_field_count"])
        self.assertEqual(174, replay["scenario_field_check_count"])
        self.assertEqual(5, replay["control_view_count"])
        self.assertEqual(6, replay["human_handling_count"])
        self.assertEqual(6, replay["future_model_reasoning_candidate_count"])
        delivery = contract["delivery_evidence_contract"]
        self.assertTrue(delivery["metadata_only"])
        for group_name, fields, count in (
            ("answer_sample", self.module.ANSWER_SAMPLE_FIELDS, 6),
            ("negative_test_result", self.module.NEGATIVE_TEST_RESULT_FIELDS, 6),
            ("prompt_version", self.module.PROMPT_VERSION_RECORD_FIELDS, 6),
            ("reproducible_log", self.module.REPRODUCIBLE_LOG_FIELDS, 6),
            (
                "output_permission_boundary",
                self.module.OUTPUT_PERMISSION_BOUNDARY_FIELDS,
                6,
            ),
            ("rollback_and_fallback", self.module.ROLLBACK_AND_FALLBACK_FIELDS, 2),
        ):
            with self.subTest(group=group_name):
                field_key = (
                    "prompt_version_record_field_count"
                    if group_name == "prompt_version"
                    else f"{group_name}_field_count"
                )
                self.assertEqual(count, delivery[f"{group_name}_record_count"])
                self.assertEqual(len(fields), delivery[field_key])
        self.assertEqual(384, delivery["delivery_field_check_count"])

    def test_delivery_report_shapes_and_opaque_control_references(self):
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertIsNone(report["failure_state"])
        self.assertEqual("IDS-STAGE100-P4-GATE", report["current_gate"])
        self.assertEqual("IDS-STAGE100-REVIEW-GATE", report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertTrue(report["control_references_opaque"])
        self.assertEqual(384, report["delivery_field_check_count"])
        for group_name, fields in self.module.DELIVERY_GROUPS:
            records = report[group_name]
            expected_count = 2 if group_name == "rollback_and_fallback_control_records" else 6
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
                                value.startswith(":control:stage100-p2:")
                                or value.startswith(":control:stage100-p4:")
                            )

    def test_negative_semantics_output_permissions_and_candidate_separation(self):
        negative = {
            item["scenario_id"]: item
            for item in self.report["negative_test_result_control_records"]
        }
        injection = negative[
            "retrieval_document_cannot_override_ids_rule_control"
        ]
        self.assertEqual(
            "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            injection["retrieval_document_instruction_precedence_state"],
        )
        self.assertEqual(
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            injection["prompt_injection_defense_state"],
        )
        answers = {
            item["scenario_id"]: item
            for item in self.report["answer_sample_control_records"]
        }
        gap = answers[
            "evidence_gap_cannot_masquerade_as_internal_experience_control"
        ]
        self.assertTrue(gap["evidence_gap_ref"].startswith(":control:stage100-p2:"))
        self.assertEqual(
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
            gap["source_type_separation_state"],
        )
        for record in self.report["prompt_version_control_records"]:
            with self.subTest(prompt_record=record):
                self.assertTrue(record["future_model_reasoning_candidate_declared"])
                self.assertFalse(record["actual_model_call_performed"])
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
                self.assertFalse(
                    boundary["business_line_whitebox_human_approval_recorded"]
                )
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
                self.assertEqual(
                    "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                    record["rollback_target_result"],
                )
                self.assertTrue(record["business_line_whitebox_approval_required"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["actual_prompt_rollback_performed"])
                self.assertFalse(
                    record["actual_model_configuration_fallback_performed"]
                )
                self.assertFalse(record["persistent_state_write_performed"])

    def test_invalid_or_tampered_phase3_output_fails_closed(self):
        invalid = self.module.build_no_internal_evidence_strategy_phase4_delivery_report(
            lambda: {}
        )
        self.assertFalse(invalid["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", invalid["failure_state"])
        self.assertEqual("IDS-STAGE100-P4-GATE", invalid["next_gate"])
        self.assertEqual([], invalid["answer_sample_control_records"])

        phase3_module = _load_module(PHASE3_MODULE, "stage100_phase3_for_delivery_tamper")
        tampered = copy.deepcopy(
            phase3_module.build_no_internal_evidence_strategy_phase3_report()
        )
        injection_index = self.module.P3_SCENARIO_IDS.index(
            "retrieval_document_cannot_override_ids_rule_control"
        )
        tampered["scenario_results"][injection_index][
            "prompt_injection_defense_state"
        ] = "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
        rejected = self.module.build_no_internal_evidence_strategy_phase4_delivery_report(
            lambda: tampered
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            "PROMPT_INJECTION_PROTECTION_MISSING", rejected["failure_state"]
        )
        self.assertEqual([], rejected["answer_sample_control_records"])

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
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)

    def test_failure_contract_chinese_feedback_and_scope_are_complete(self):
        self.assertEqual(
            list(self.module.FAILURE_STATES),
            self.contract["failure_and_stop_contract"]["declared_failure_states"],
        )
        self.assertEqual(
            16, self.contract["failure_and_stop_contract"]["failure_state_count"]
        )
        feedback = self.contract["chinese_feedback_contract"]
        self.assertTrue(feedback["enterprise_chinese_only"])
        self.assertFalse(feedback["published"])
        self.assertEqual(4, feedback["feedback_count"])
        self.assertEqual(feedback["messages"], self.report["chinese_feedback"])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "唯一业务事实权威",
            "reference-only",
            "RAG 回答样例",
            "负向测试结果",
            "prompt/version",
            "可复现日志",
            "模型输出权限边界",
            "业务线白箱人工处理",
            "模型 Token",
            "IDS-STAGE100-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_current_governance_keeps_stage100_p4_progression_explicit(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase4_current = (
            "IDS-STAGE100",
            "IDS-STAGE100-P4",
            "IDS-V0_1-STAGE100-P4",
            "IDS-STAGE100-REVIEW-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase4_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase4_current:
            self.assertFalse(is_current_projection)
            self.assertEqual(
                "STAGE100_NO_INTERNAL_EVIDENCE_STRATEGY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual(
                "P4 交付证据、回滚与中文反馈已完成",
                acceptance_by_id["ACC-STAGE-100"],
            )
        for acceptance_id in (
            "ACC-STAGE100-P4-01",
            "ACC-STAGE100-P4-02",
            "ACC-STAGE100-P4-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE100-P4-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE100-P4-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE100-REVIEW-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        for phrase in (
            "stage100_phase4_state:",
            'current_phase_id: "IDS-STAGE100-P4"',
            'next_gate_id: "IDS-STAGE100-REVIEW-GATE"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap_text)


if __name__ == "__main__":
    unittest.main()
