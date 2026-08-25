"""Stage101 RAG 可复现整阶段机械复审的聚焦测试。"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-101_RAG可复现.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-102_文档内提示注入防护.md"
)
REVIEW_DOCUMENT = BASE / "STAGE101_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_stage_review_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage101_rag_reproducibility_contract.json"
P2_MODULE = BASE / "index_version_schema" / "stage101_rag_reproducibility_control_slice.py"
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_controlled_scenarios.py"
)
P4_MODULE = BASE / "index_version_schema" / "stage101_rag_reproducibility_delivery.py"
P4_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage101-p4-local.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage101-review-local.json"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"


def load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage101RagReproducibilityReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage101_rag_reproducibility_review", MODULE)
        cls.report = cls.module.build_rag_reproducibility_stage101_review_report()

    def test_required_phase_artifacts_and_identity_exist(self) -> None:
        for source in (
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_DOCUMENT,
            CONTRACT,
            MODULE,
            P1_CONTRACT,
            P2_MODULE,
            P3_MODULE,
            P4_MODULE,
            P4_RUN,
            REVIEW_RUN,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
        ):
            with self.subTest(source=source):
                self.assertTrue(source.is_file())
        self.assertEqual("IDS-STAGE101-REVIEW", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE101-REVIEW", self.contract["task_id"])
        self.assertEqual("IDS-STAGE101-REVIEW-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE102-P1-GATE", self.contract["next_gate"])

    def test_contract_keeps_authority_fixed_shapes_and_runtime_closed(self) -> None:
        authority = self.contract["source_authority"]
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(
            authority["business_line_whitebox_human_review_remains_authoritative"]
        )
        for field in (
            "review_can_replace_source_document",
            "review_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "prompt_or_answer_access_performed",
            "evidence_ledger_access_performed",
            "report_or_audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["reviewed_phase_contract"]
        self.assertEqual("15/4/5/5/3/22/4", replay["phase1_static_shape"])
        self.assertEqual(270, replay["phase2_control_field_check_count"])
        self.assertEqual(192, replay["phase3_scenario_field_check_count"])
        self.assertEqual("6/6/6/6/6/2", replay["phase4_delivery_shape"])
        self.assertEqual(456, replay["phase4_delivery_field_check_count"])
        self.assertEqual(8, replay["reproducibility_tuple_field_count"])
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertEqual(0 if field.startswith("actual_") else False, value)
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage100_review_evidence_declared",
            "stage101_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_completed",
            "stage101_review_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage102_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_default_report_is_valid_and_preserves_fixed_replay(self) -> None:
        report = self.report
        self.assertTrue(report["review_valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual([], report["failure_reasons"])
        self.assertEqual(self.module.REVIEW_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertEqual(
            {"P1": True, "P2": True, "P3": True, "P4": True},
            report["phase_results"],
        )
        self.assertEqual(self.module.REVIEWED_CONTROL_SHAPE, report["controlled_replay"])
        for field, value in report["review_invariants"].items():
            with self.subTest(field=field):
                self.assertTrue(value)

    def test_evidence_injection_whitebox_and_rollback_controls_are_preserved(self) -> None:
        phase3 = self.module._default_phase3_report()
        phase4 = self.module._default_phase4_report()
        scenarios = {item["scenario_id"]: item for item in phase3["scenario_results"]}
        gap = scenarios["draft_recommendation_evidence_gap_remains_declared_control"]
        self.assertFalse(gap["internal_evidence_present"])
        self.assertTrue(gap["evidence_gap_present"])
        injection = scenarios["retrieval_document_cannot_override_ids_rule_control"]
        self.assertEqual(
            "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
            injection["retrieval_document_instruction_precedence_state"],
        )
        self.assertEqual(
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            injection["prompt_injection_defense_state"],
        )
        permissions = {
            item["scenario_id"]: item
            for item in phase4["output_permission_boundary_control_records"]
        }
        for scenario_id in (
            "high_risk_engineering_advice_requires_whitebox_confirmation_control",
            "contractual_commitment_requires_whitebox_confirmation_control",
            "production_writeback_requires_whitebox_confirmation_control",
        ):
            with self.subTest(scenario_id=scenario_id):
                record = permissions[scenario_id]
                self.assertEqual(
                    "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                    record["output_permission_state"],
                )
                self.assertTrue(record["human_handling_required"])
                self.assertFalse(record["automatic_final_conclusion_allowed"])
                self.assertFalse(record["actual_human_confirmation_performed"])
        for record in phase4["rollback_and_fallback_control_records"]:
            with self.subTest(domain=record["control_domain"]):
                self.assertEqual(self.module.P3_PASS_RESULT, record["rollback_target_result"])
                self.assertTrue(record["business_line_whitebox_approval_required"])
                self.assertTrue(record["versioned_basis_required"])
                self.assertTrue(record["verifiable_rollback_target_required"])
                self.assertFalse(record["persistent_state_write_performed"])

    def test_runtime_and_rollback_boundaries_are_closed(self) -> None:
        report = self.report
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(
            all(
                report[field] is False for field in self.module.REVIEW_RUNTIME_FALSE_FIELDS
            )
        )
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["source_body_or_path_allowed"])
        self.assertFalse(report["stage102_started"])
        self.assertEqual(self.module.P4_PASS_RESULT, report["rollback"]["return_to"])
        self.assertTrue(report["rollback"]["preserve_stage101_phase1_to_phase4_evidence"])
        self.assertTrue(report["rollback"]["preserve_stage100_review_evidence"])
        self.assertFalse(report["rollback"]["business_source_or_runtime_change_allowed"])
        self.assertFalse(report["rollback"]["github_or_ovh_change_allowed"])

    def test_invalid_phase_contract_or_delivery_shape_fails_closed(self) -> None:
        for phase_name, kwargs in (
            ("P1", {"phase1_contract_provider": lambda: {"task_id": "tampered"}}),
            ("P2", {"phase2_report_provider": lambda: {"input_accepted": False}}),
            ("P3", {"phase3_report_provider": lambda: {"valid": False}}),
        ):
            with self.subTest(phase=phase_name):
                report = self.module.build_rag_reproducibility_stage101_review_report(
                    **kwargs
                )
                self.assertFalse(report["review_valid"])
                self.assertFalse(report["phase_results"][phase_name])
                self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])
                self.assertIn(
                    f"{phase_name}_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
                    report["failure_reasons"],
                )
        phase4 = copy.deepcopy(self.module._default_phase4_report())
        phase4["delivery_field_check_count"] = 0
        report = self.module.build_rag_reproducibility_stage101_review_report(
            phase4_report_provider=lambda: phase4
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

    def test_semantic_or_runtime_drift_fails_closed(self) -> None:
        phase3 = copy.deepcopy(self.module._default_phase3_report())
        phase3["runtime_boundary"]["model_token_consumption_performed"] = True
        report = self.module.build_rag_reproducibility_stage101_review_report(
            phase3_report_provider=lambda: phase3
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertIn("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

        phase4 = copy.deepcopy(self.module._default_phase4_report())
        for record in phase4["negative_test_result_control_records"]:
            if record["scenario_id"] == "retrieval_document_cannot_override_ids_rule_control":
                record["prompt_injection_defense_state"] = (
                    "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
                )
        report = self.module.build_rag_reproducibility_stage101_review_report(
            phase4_report_provider=lambda: phase4
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

    def test_scope_receipt_and_current_governance_projection_are_explicit(self) -> None:
        text = REVIEW_DOCUMENT.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "八元可复现记录键",
            "提示注入防护",
            "业务线白箱人工确认",
            "P4→P3 回退",
            "模型 Token",
            "IDS-STAGE102-P1-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        self.assertEqual(
            list(self.module.FAILURE_STATES), failures["declared_failure_states"]
        )
        self.assertTrue(failures["stage102_must_remain_not_started"])
        receipt = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        review_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-REVIEW",
            "IDS-V0_1-STAGE101-REVIEW",
            "IDS-STAGE102-P1-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        assert_legacy_or_current_projection(
            self,
            current,
            (review_current,),
            status,
            plan,
            ROADMAP,
        )
        if current == review_current:
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-101"])
            for acceptance_id in (
                "ACC-STAGE101-REVIEW-01",
                "ACC-STAGE101-REVIEW-02",
                "ACC-STAGE101-REVIEW-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE101-REVIEW-04"])
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE101-REVIEW-20260825-001", event_ids)


if __name__ == "__main__":
    unittest.main()
