"""Stage102 文档内提示注入防护整阶段机械复审的聚焦验证。"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parents[1] / "index_version_schema"
REVIEW_SOURCE = BASE / "stage102_document_prompt_injection_defense_stage_review.py"
REVIEW_CONTRACT = (
    BASE / "stage102_document_prompt_injection_defense_stage_review_contract.json"
)
P1_CONTRACT = BASE / "stage102_document_prompt_injection_defense_contract.json"
P2_SOURCE = BASE / "stage102_document_prompt_injection_defense_control_slice.py"
P3_SOURCE = BASE / "stage102_document_prompt_injection_defense_controlled_scenarios.py"
P4_SOURCE = BASE / "stage102_document_prompt_injection_defense_delivery.py"
SCOPE_DOCUMENT = BASE.parent / "STAGE102_STAGE_REVIEW.md"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-102_文档内提示注入防护.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-103_模型输出权限门禁.md"
)
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage102-review-local.json"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"


def _load_module(name: str, source: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {source.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage102DocumentPromptInjectionDefenseReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.review = _load_module("stage102_review_test_module", REVIEW_SOURCE)

    def test_required_artifacts_and_identity_exist(self) -> None:
        for source in (
            REVIEW_SOURCE,
            REVIEW_CONTRACT,
            P1_CONTRACT,
            P2_SOURCE,
            P3_SOURCE,
            P4_SOURCE,
            SCOPE_DOCUMENT,
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_RUN,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
        ):
            self.assertTrue(source.is_file(), source)

        self.assertEqual(
            self.review.SCHEMA_VERSION,
            "ids.stage102.document_prompt_injection_defense.stage_review.v1",
        )
        self.assertEqual(
            self.review.RECORD_KIND,
            "CONTROL_ONLY_IN_MEMORY_DOCUMENT_PROMPT_INJECTION_DEFENSE_STAGE_REVIEW",
        )
        self.assertEqual(
            self.review.REVIEW_GATE,
            "IDS-STAGE102-REVIEW-GATE",
        )
        self.assertEqual(self.review.NEXT_GATE, "IDS-STAGE103-P1-GATE")

    def test_contract_keeps_authority_shape_and_runtime_closed(self) -> None:
        contract = json.loads(REVIEW_CONTRACT.read_text(encoding="utf-8"))
        authority = contract["source_authority"]
        reviewed = contract["reviewed_phase_contract"]
        runtime = contract["runtime_boundary"]
        boundary = contract["stage_and_phase_boundary"]

        self.assertEqual(contract["schema_version"], self.review.SCHEMA_VERSION)
        self.assertEqual(contract["phase"], "IDS-STAGE102-REVIEW")
        self.assertEqual(contract["task_id"], "IDS-V0_1-STAGE102-REVIEW")
        self.assertEqual(contract["entry_gate"], self.review.REVIEW_GATE)
        self.assertEqual(contract["next_gate"], self.review.NEXT_GATE)
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(authority["review_can_replace_source_document"])
        self.assertFalse(authority["review_can_become_business_fact_authority"])
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertEqual(reviewed["phase1_static_shape"], "17/7/4/5/25/4")
        self.assertEqual(reviewed["phase2_control_field_check_count"], 350)
        self.assertEqual(reviewed["phase3_scenario_field_check_count"], 238)
        self.assertEqual(reviewed["phase4_delivery_field_check_count"], 528)
        self.assertEqual(reviewed["reproducibility_tuple_field_count"], 8)
        self.assertTrue(all(value == 0 for key, value in runtime.items() if key.endswith("_count")))
        self.assertTrue(all(value is False for key, value in runtime.items() if not key.endswith("_count")))
        self.assertTrue(boundary["stage102_review_started"])
        self.assertFalse(boundary["stage103_started"])
        self.assertFalse(boundary["github_upload_allowed"])
        self.assertFalse(boundary["push_allowed"])

    def test_default_report_is_valid_and_replays_fixed_phases(self) -> None:
        report = self.review.build_document_prompt_injection_defense_stage102_review_report()

        self.assertTrue(report["valid"])
        self.assertEqual(report["result"], self.review.PASS_RESULT)
        self.assertIsNone(report["failure_state"])
        self.assertEqual(report["current_gate"], self.review.REVIEW_GATE)
        self.assertEqual(report["next_gate"], self.review.NEXT_GATE)
        self.assertTrue(report["phase1_contract_replayed_in_memory_only"])
        self.assertTrue(report["phase2_control_slice_replayed_in_memory_only"])
        self.assertTrue(report["phase3_controlled_scenarios_replayed_in_memory_only"])
        self.assertTrue(report["phase4_delivery_evidence_replayed_in_memory_only"])
        self.assertEqual(
            report["reviewed_phase_results"],
            {
                "phase1_contract_state": self.review.P1_CONTRACT_STATE,
                "phase2_execution_state": self.review.P2_PASS_RESULT,
                "phase3_result": self.review.P3_PASS_RESULT,
                "phase4_result": self.review.P4_PASS_RESULT,
            },
        )

    def test_fixed_review_shape_and_p4_to_p3_rollback_are_preserved(self) -> None:
        report = self.review.build_document_prompt_injection_defense_stage102_review_report()
        shape = report["reviewed_control_shape"]
        rollback = report["rollback_contract"]

        self.assertEqual(shape, self.review.REVIEWED_CONTROL_SHAPE)
        self.assertEqual(shape["phase1_reference_field_count"], 17)
        self.assertEqual(shape["phase2_control_request_count"], 7)
        self.assertEqual(shape["phase2_projection_field_count_per_request"], 50)
        self.assertEqual(shape["phase3_scenario_field_count"], 34)
        self.assertEqual(shape["phase3_human_handling_count"], 7)
        self.assertEqual(shape["phase4_delivery_shape"], "7/7/7/7/7/2")
        self.assertEqual(shape["phase4_delivery_field_shape"], "17/12/14/17/12/12")
        self.assertEqual(rollback["rollback_target_result"], self.review.P4_PASS_RESULT)
        self.assertTrue(rollback["phase4_to_phase3_rollback_preserved"])
        self.assertFalse(rollback["actual_prompt_rollback_performed"])
        self.assertFalse(rollback["actual_model_configuration_fallback_performed"])

    def test_authority_semantic_and_whitebox_controls_are_preserved(self) -> None:
        report = self.review.build_document_prompt_injection_defense_stage102_review_report()
        authority = report["source_authority"]
        semantic = report["semantic_controls"]

        self.assertTrue(authority["frozen_control_artifacts_only"])
        self.assertTrue(authority["source_document_remains_authoritative"])
        self.assertTrue(authority["business_line_whitebox_human_review_remains_authoritative"])
        self.assertFalse(authority["second_authoritative_source_created"])
        self.assertTrue(semantic["document_instruction_remains_untrusted_evidence"])
        self.assertTrue(semantic["document_instruction_cannot_override_ids_rules"])
        self.assertTrue(semantic["evidence_gap_cannot_be_presented_as_internal_experience"])
        self.assertTrue(semantic["source_type_separation_preserved"])
        self.assertTrue(semantic["high_risk_engineering_advice_requires_business_line_whitebox_confirmation"])
        self.assertTrue(semantic["contractual_commitment_requires_business_line_whitebox_confirmation"])
        self.assertTrue(semantic["production_writeback_requires_business_line_whitebox_confirmation"])
        self.assertFalse(semantic["final_conclusion_published"])
        self.assertFalse(semantic["actual_human_confirmation_performed"])

    def test_runtime_and_next_stage_boundaries_are_closed(self) -> None:
        report = self.review.build_document_prompt_injection_defense_stage102_review_report()
        boundary = report["runtime_boundary"]
        stage = report["stage_and_phase_boundary"]
        failure = report["failure_and_stop_contract"]

        self.assertTrue(all(value == 0 for key, value in report.items() if key.startswith("actual_") and key.endswith("_count")))
        self.assertTrue(all(value is False for value in boundary.values()))
        self.assertFalse(report["persistent_record_created"])
        self.assertTrue(stage["whole_stage_review_completed_in_memory_only"])
        self.assertFalse(stage["stage103_started"])
        self.assertFalse(stage["github_upload_allowed"])
        self.assertFalse(stage["push_allowed"])
        self.assertEqual(failure["failure_state_count"], len(self.review.FAILURE_STATES))
        self.assertTrue(failure["stage103_must_remain_not_started"])
        self.assertTrue(all(value is False for key, value in failure.items() if key.endswith("_allowed")))

    def test_phase1_or_phase2_drift_fails_closed(self) -> None:
        phase1 = copy.deepcopy(self.review._default_phase1_contract())
        phase1["document_instruction_boundary_contract"]["ids_rule_precedence_state"] = "DRIFT"
        phase1_report = self.review.build_document_prompt_injection_defense_stage102_review_report(
            phase1_provider=lambda: phase1
        )
        self.assertFalse(phase1_report["valid"])
        self.assertEqual(
            phase1_report["failure_state"],
            "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        )

        phase2 = copy.deepcopy(self.review._default_phase2_report())
        phase2["control_projection_field_total"] = 349
        phase2_report = self.review.build_document_prompt_injection_defense_stage102_review_report(
            phase2_provider=lambda: phase2
        )
        self.assertFalse(phase2_report["valid"])
        self.assertEqual(
            phase2_report["failure_state"],
            "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        )

    def test_phase3_or_phase4_drift_fails_closed(self) -> None:
        phase3 = copy.deepcopy(self.review._default_phase3_report())
        phase3["scenario_results"][0]["ids_rule_precedence_state"] = "DRIFT"
        phase3_report = self.review.build_document_prompt_injection_defense_stage102_review_report(
            phase3_provider=lambda: phase3
        )
        self.assertFalse(phase3_report["valid"])
        self.assertEqual(
            phase3_report["failure_state"],
            "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        )

        phase4 = copy.deepcopy(self.review._default_phase4_report())
        phase4["rollback_and_fallback_control_records"][0]["rollback_target_result"] = "DRIFT"
        phase4_report = self.review.build_document_prompt_injection_defense_stage102_review_report(
            phase4_provider=lambda: phase4
        )
        self.assertFalse(phase4_report["valid"])
        self.assertEqual(
            phase4_report["failure_state"],
            "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
        )

    def test_report_is_detached_from_future_mutation(self) -> None:
        report = self.review.build_document_prompt_injection_defense_stage102_review_report()
        report["reviewed_control_shape"]["phase4_delivery_field_check_count"] = -1
        fresh = self.review.build_document_prompt_injection_defense_stage102_review_report()

        self.assertEqual(
            fresh["reviewed_control_shape"]["phase4_delivery_field_check_count"],
            528,
        )
        self.assertTrue(fresh["valid"])

    def test_scope_receipt_and_current_governance_projection_are_explicit(self) -> None:
        text = SCOPE_DOCUMENT.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "八元控制引用",
            "文档内提示注入防护",
            "业务线白箱人工处理",
            "P4→P3 回退",
            "模型 Token",
            "IDS-STAGE103-P1-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        contract = json.loads(REVIEW_CONTRACT.read_text(encoding="utf-8"))
        failures = contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        self.assertEqual(
            list(self.review.FAILURE_STATES), failures["declared_failure_states"]
        )
        self.assertTrue(failures["stage103_must_remain_not_started"])

        receipt = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
        self.assertEqual(self.review.PASS_RESULT, receipt["result"])
        self.assertEqual(self.review.NEXT_GATE, receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        review_current = (
            "IDS-STAGE102",
            "IDS-STAGE102-REVIEW",
            "IDS-V0_1-STAGE102-REVIEW",
            "IDS-STAGE103-P1-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        assert_legacy_or_current_projection(
            self,
            current,
            {review_current},
            status,
            plan,
            ROADMAP,
        )
        if current == review_current:
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-102"])
            for acceptance_id in (
                "ACC-STAGE102-REVIEW-01",
                "ACC-STAGE102-REVIEW-02",
                "ACC-STAGE102-REVIEW-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE102-REVIEW-04"])
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE102-REVIEW-20260825-001", event_ids)


if __name__ == "__main__":
    unittest.main()
