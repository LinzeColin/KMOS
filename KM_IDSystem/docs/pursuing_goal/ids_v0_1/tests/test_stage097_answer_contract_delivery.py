"""Stage097 P4 回答合同交付证据的聚焦测试。"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE097_PHASE4_ANSWER_CONTRACT_DELIVERY_EVIDENCE.md"
CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract_delivery_contract.json"
MODULE = BASE / "index_version_schema" / "stage097_answer_contract_delivery.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)
P3_SCOPE = BASE / "STAGE097_PHASE3_ANSWER_CONTRACT_CONTROLLED_SCENARIOS.md"
P3_CONTRACT = (
    BASE / "index_version_schema" / "stage097_answer_contract_controlled_scenarios_contract.json"
)
P3_MODULE = BASE / "index_version_schema" / "stage097_answer_contract_controlled_scenarios.py"
P3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p3-local.json"
P2_SCOPE = BASE / "STAGE097_PHASE2_ANSWER_CONTRACT_CONTROL_SLICE.md"
P2_CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract_control_slice_contract.json"
P1_SCOPE = BASE / "STAGE097_PHASE1_ANSWER_CONTRACT_SCOPE_BOUNDARY.md"
P1_CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract.json"
PREDECESSOR_REVIEW = BASE / "STAGE096_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage096_knowledge_base_poisoning_defense_stage_review_contract.json"
)
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p4-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage097AnswerContractPhase4DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("stage097_phase4_delivery", MODULE)
        cls.phase3 = load_module("stage097_phase3_scenarios", P3_MODULE)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_answer_contract_phase4_delivery_report()

    def test_scope_contract_module_taskpack_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P3_SCOPE,
            P3_CONTRACT,
            P3_MODULE,
            P3_RECEIPT,
            P2_SCOPE,
            P2_CONTRACT,
            P1_SCOPE,
            P1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_and_phase_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(self.module.SCHEMA_VERSION, contract["schema_version"])
        self.assertEqual("STAGE-097", contract["stage"])
        self.assertEqual("IDS-STAGE097-P4", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE097-P4", contract["task_id"])
        self.assertEqual(self.module.ENTRY_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        self.assertEqual(
            "PHASE4_ANSWER_CONTRACT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        source = contract["source_authority"]
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field in (
            "delivery_control_metadata_can_replace_source_document",
            "delivery_control_metadata_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "live_source_read_performed",
            "prompt_or_answer_access_performed",
            "evidence_ledger_access_performed",
            "audit_log_access_performed",
            "authorized_fixture_access_performed",
            "raw_metadata_content_access_allowed",
            "source_body_or_path_allowed",
            "retrieval_result_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])
        boundary = contract["stage_boundary"]
        for field in (
            "stage096_review_evidence_declared",
            "stage097_started",
            "stage097_entry_authorized",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_started",
            "phase4_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage097_review_started",
            "stage098_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_default_report_is_valid_and_gated(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase3_side_effect_free"])
        self.assertTrue(report["delivery_evidence_metadata_only"])
        self.assertTrue(report["control_references_opaque"])
        self.assertFalse(report["second_authoritative_source_created"])

    def test_delivery_groups_have_exact_static_shapes(self) -> None:
        expected_counts = {
            "answer_sample_control_records": 6,
            "negative_test_result_control_records": 6,
            "prompt_version_control_records": 6,
            "reproducible_log_control_records": 6,
            "output_permission_boundary_control_records": 6,
            "rollback_and_fallback_control_records": 2,
        }
        for name, fields in self.module.DELIVERY_GROUPS:
            records = self.report[name]
            with self.subTest(group=name):
                self.assertEqual(expected_counts[name], len(records))
            for record in records:
                with self.subTest(group=name, record=record):
                    self.assertEqual(set(fields), set(record))
        self.assertEqual(384, self.report["delivery_field_check_count"])
        delivery = self.contract["delivery_evidence_contract"]
        self.assertEqual(384, delivery["delivery_field_check_count"])

    def test_samples_negative_results_and_source_types_preserve_p3_controls(self) -> None:
        samples = {
            item["scenario_id"]: item
            for item in self.report["answer_sample_control_records"]
        }
        self.assertTrue(
            all(
                item["answer_sample_state"]
                == "CONTROL_RAG_ANSWER_SAMPLE_REFERENCE_ONLY_NOT_EXECUTED"
                and item["actual_answer_published"] is False
                for item in samples.values()
            )
        )
        gap = samples[
            "evidence_gap_cannot_masquerade_as_internal_experience_control"
        ]
        self.assertTrue(gap["evidence_gap_ref"].startswith(self.module.CONTROL_PREFIX))
        self.assertEqual(
            "CONTROL_INTERNAL_EXTERNAL_PUBLIC_MODEL_REASONING_AND_GAP_SEPARATED",
            samples["external_augmentation_preserves_source_type_control"][
                "source_type_separation_state"
            ],
        )
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
        self.assertFalse(injection["actual_rag_execution_performed"])
        self.assertFalse(injection["actual_negative_test_result_persisted"])

    def test_permission_boundaries_and_rollbacks_remain_whitebox_controlled(self) -> None:
        high_risk = {
            "high_risk_engineering_advice_requires_whitebox_confirmation_control",
            "contract_commitment_requires_whitebox_confirmation_control",
            "production_writeback_requires_whitebox_confirmation_control",
        }
        boundaries = {
            item["scenario_id"]: item
            for item in self.report["output_permission_boundary_control_records"]
        }
        for scenario_id in high_risk:
            with self.subTest(scenario_id=scenario_id):
                record = boundaries[scenario_id]
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                    record["output_permission_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    record["final_conclusion_state"],
                )
                self.assertTrue(record["human_handling_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
                self.assertFalse(record["actual_answer_published"])
        rollback = self.report["rollback_and_fallback_control_records"]
        self.assertEqual({"prompt_rollback", "model_configuration_fallback"}, {
            item["control_domain"] for item in rollback
        })
        self.assertTrue(
            all(
                item["rollback_target_result"] == self.module.P3_PASS_RESULT
                and item["business_line_whitebox_approval_required"] is True
                and item["versioned_basis_required"] is True
                and item["verifiable_rollback_target_required"] is True
                and item["actual_prompt_rollback_performed"] is False
                and item["actual_model_configuration_fallback_performed"] is False
                and item["persistent_state_write_performed"] is False
                for item in rollback
            )
        )

    def test_version_log_and_runtime_boundaries_are_closed(self) -> None:
        for name in (
            "prompt_version_control_records",
            "reproducible_log_control_records",
        ):
            for record in self.report[name]:
                for field, value in record.items():
                    if field.endswith("_ref") or field == "delivery_record_id":
                        with self.subTest(group=name, field=field, value=value):
                            self.assertTrue(
                                value is None
                                or value.startswith(self.module.CONTROL_PREFIX)
                                or value.startswith(self.module.DELIVERY_PREFIX)
                            )
        self.assertTrue(
            all(value is False for value in self.report["runtime_boundary"].values())
        )
        for field, value in self.report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        self.assertEqual(4, len(self.report["chinese_feedback"]))

    def test_failure_and_rollback_contracts_are_explicit(self) -> None:
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(16, failures["failure_state_count"])
        self.assertEqual(
            list(self.module.FAILURE_STATES), failures["declared_failure_states"]
        )
        self.assertTrue(
            all(value is False for value in failures.values() if isinstance(value, bool))
        )
        rollback = self.contract["rollback_contract"]
        self.assertEqual(self.module.P3_PASS_RESULT, rollback["rollback_target_result"])
        self.assertTrue(rollback["preserve_stage096_review_evidence"])
        self.assertTrue(rollback["preserve_stage097_phase1_phase2_phase3"])
        self.assertTrue(rollback["preserve_real_evidence_ledger_audit_report_database_and_ovh"])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "负向测试结果",
            "prompt/version 记录",
            "可复现日志",
            "模型输出权限边界",
            "模型配置回退说明",
            "模型 Token",
            "IDS-STAGE097-REVIEW-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_invalid_predecessor_runtime_and_semantic_drift_fail_closed(self) -> None:
        failed = self.module.build_answer_contract_phase4_delivery_report(lambda: {})
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_CONTROL_OUTPUT_INVALID", failed["failure_state"])
        self.assertEqual(self.module.ENTRY_GATE, failed["next_gate"])
        self.assertEqual([], failed["answer_sample_control_records"])

        runtime = copy.deepcopy(self.phase3.build_answer_contract_phase3_report())
        runtime["runtime_boundary"]["model_token_consumption_performed"] = True
        failed = self.module.build_answer_contract_phase4_delivery_report(lambda: runtime)
        self.assertFalse(failed["valid"])
        self.assertEqual("PHASE3_RUNTIME_SIGNAL_DETECTED", failed["failure_state"])

        semantic = copy.deepcopy(self.phase3.build_answer_contract_phase3_report())
        semantic["scenario_results"][2]["prompt_injection_defense_state"] = (
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
        )
        failed = self.module.build_answer_contract_phase4_delivery_report(lambda: semantic)
        self.assertFalse(failed["valid"])
        self.assertEqual("PROMPT_INJECTION_PROTECTION_MISSING", failed["failure_state"])

    def test_current_governance_receipt_and_review_boundary_are_exact(self) -> None:
        for path in (STATUS, PLAN, ACCEPTANCE, EVENTS, ROADMAP, RECEIPT):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-REVIEW",
            "IDS-V0_1-STAGE097-REVIEW",
            "IDS-STAGE098-P1-GATE",
        )
        stage098_phase1_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P1",
            "IDS-V0_1-STAGE098-P1",
            "IDS-STAGE098-P2-GATE",
        )
        stage098_phase2_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P2",
            "IDS-V0_1-STAGE098-P2",
            "IDS-STAGE098-P3-GATE",
        )
        stage098_phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        stage098_phase4_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        stage098_review_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-REVIEW",
            "IDS-V0_1-STAGE098-REVIEW",
            "IDS-STAGE099-P1-GATE",
        )
        self.assertIn(
            current,
            (
                phase4_current,
                review_current,
                stage098_phase1_current,
                stage098_phase2_current,
                stage098_phase3_current,
                stage098_phase4_current,
                stage098_review_current,
            ),
        )
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE097-P4-20260825-001", event_ids)
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        if current == phase4_current:
            self.assertEqual("IDS-V0_1-STAGE097-P4", plan["task"])
            self.assertEqual(
                "STAGE097_ANSWER_CONTRACT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("P4 交付证据已完成", acceptance_by_id["ACC-STAGE-097"])
            for acceptance_id in (
                "ACC-STAGE097-P4-01",
                "ACC-STAGE097-P4-02",
                "ACC-STAGE097-P4-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE097-P4-04"])
        elif current == review_current:
            self.assertEqual("IDS-V0_1-STAGE097-REVIEW", plan["task"])
            self.assertEqual(
                "STAGE097_ANSWER_CONTRACT_REVIEW_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        elif current == stage098_phase1_current:
            self.assertEqual("IDS-V0_1-STAGE098-P1", plan["task"])
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTRACT_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        elif current == stage098_phase2_current:
            self.assertEqual("IDS-V0_1-STAGE098-P2", plan["task"])
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        elif current == stage098_phase3_current:
            self.assertEqual("IDS-V0_1-STAGE098-P3", plan["task"])
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        elif current == stage098_phase4_current:
            self.assertEqual("IDS-V0_1-STAGE098-P4", plan["task"])
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        else:
            self.assertEqual("IDS-V0_1-STAGE098-REVIEW", plan["task"])
            self.assertEqual(
                "STAGE098_PROMPT_VERSIONING_REVIEW_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-097"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage097_phase4_state:", roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE097-P4"', roadmap_text)
        self.assertIn('next_gate_id: "IDS-STAGE097-REVIEW-GATE"', roadmap_text)
        if current == stage098_phase1_current:
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P2-GATE"', roadmap_text)
        elif current == stage098_phase2_current:
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P2"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P3-GATE"', roadmap_text)
        elif current == stage098_phase3_current:
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P3"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P4-GATE"', roadmap_text)
        elif current == stage098_phase4_current:
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P4"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-REVIEW-GATE"', roadmap_text)
        else:
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn("stage098_phase4_state:", roadmap_text)
            self.assertIn("stage098_review_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE099-P1-GATE"', roadmap_text)


if __name__ == "__main__":
    unittest.main()
