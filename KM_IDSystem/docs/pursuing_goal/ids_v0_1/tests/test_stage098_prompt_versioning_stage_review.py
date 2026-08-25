"""Stage098 Prompt 版本化整阶段机械复审的聚焦测试。"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-098_Prompt版本化.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-099_内部依据与外部增强分离.md"
)
REVIEW_DOCUMENT = BASE / "STAGE098_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_stage_review_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage098_prompt_versioning_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage098_prompt_versioning_contract.json"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage098_prompt_versioning_control_slice_contract.json"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_controlled_scenarios_contract.json"
)
P4_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage098_prompt_versioning_delivery_contract.json"
)
P2_MODULE = BASE / "index_version_schema" / "stage098_prompt_versioning_control_slice.py"
P3_MODULE = (
    BASE / "index_version_schema" / "stage098_prompt_versioning_controlled_scenarios.py"
)
P4_MODULE = BASE / "index_version_schema" / "stage098_prompt_versioning_delivery.py"
P4_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage098-p4-local.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage098-review-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage098PromptVersioningReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("stage098_review", MODULE)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_prompt_versioning_stage098_review_report()

    def test_required_phase_artifacts_exist(self) -> None:
        for artifact in (
            TASKPACK,
            NEXT_TASKPACK,
            REVIEW_DOCUMENT,
            CONTRACT,
            MODULE,
            P1_CONTRACT,
            P2_CONTRACT,
            P3_CONTRACT,
            P4_CONTRACT,
            P2_MODULE,
            P3_MODULE,
            P4_MODULE,
            P4_RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_keeps_authority_runtime_and_stage099_closed(self) -> None:
        contract = self.contract
        self.assertEqual(self.module.SCHEMA_VERSION, contract["schema_version"])
        self.assertEqual("IDS-STAGE098-REVIEW", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE098-REVIEW", contract["task_id"])
        self.assertEqual(self.module.REVIEW_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        authority = contract["source_authority"]
        for field in (
            "source_document_remains_authoritative",
            "business_line_whitebox_human_review_remains_authoritative",
        ):
            with self.subTest(field=field):
                self.assertTrue(authority[field])
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
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage097_review_evidence_declared",
            "stage098_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_completed",
            "stage098_review_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage099_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        self.assertTrue(
            all(value == 0 for value in contract["runtime_boundary"].values() if isinstance(value, int))
        )

    def test_default_report_is_valid_and_preserves_fixed_replay(self) -> None:
        report = self.report
        self.assertTrue(report["review_valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.REVIEW_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        self.assertEqual(
            {
                "P1": True,
                "P2": True,
                "P3": True,
                "P4": True,
            },
            report["phase_results"],
        )
        self.assertEqual(self.module.EXPECTED_CONTROLLED_REPLAY, report["controlled_replay"])
        self.assertTrue(all(report["review_invariants"].values()))

    def test_source_type_injection_and_high_risk_controls_are_preserved(self) -> None:
        report = self.report
        replay = report["controlled_replay"]
        self.assertEqual(5, replay["phase1_reference_field_count"])
        self.assertEqual(246, replay["phase2_control_field_check_count"])
        self.assertEqual(186, replay["phase3_scenario_field_check_count"])
        self.assertEqual(444, replay["phase4_delivery_field_check_count"])
        self.assertTrue(report["review_invariants"]["single_authority_boundary_preserved"])
        self.assertTrue(report["review_invariants"]["owner_whitebox_boundary_preserved"])
        self.assertTrue(report["review_invariants"]["delivery_and_whitebox_boundaries_preserved"])
        self.assertTrue(report["review_invariants"]["failure_stop_and_rollback_boundaries_preserved"])

    def test_runtime_and_rollback_boundaries_are_closed(self) -> None:
        report = self.report
        for field in self.module.REVIEW_ZERO_COUNT_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(0, report[field])
        for field in self.module.REVIEW_RUNTIME_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(all(value is False for value in report["runtime_boundary"].values()))
        self.assertFalse(report["github_upload_allowed"])
        self.assertFalse(report["push_allowed"])
        self.assertFalse(report["stage099_started"])
        rollback = report["rollback"]
        self.assertEqual(self.module.P4_PASS_RESULT, rollback["return_to"])
        self.assertTrue(rollback["preserve_stage098_phase1_to_phase4_evidence"])
        self.assertFalse(rollback["business_source_or_runtime_change_allowed"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_invalid_phase_contracts_fail_closed(self) -> None:
        phase1 = copy.deepcopy(self.module._default_phase1_contract())
        phase1["source_authority"]["second_authoritative_source_created"] = True
        report = self.module.build_prompt_versioning_stage098_review_report(
            phase1_contract_provider=lambda: phase1
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P1"])
        self.assertIn("P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

        phase2 = copy.deepcopy(self.module._default_phase2_report())
        phase2["control_projection_field_total"] = 0
        report = self.module.build_prompt_versioning_stage098_review_report(
            phase2_report_provider=lambda: phase2
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertIn("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

        phase2_contract = copy.deepcopy(self.module._default_phase2_contract())
        phase2_contract["source_authority"][
            "second_authoritative_source_created"
        ] = True
        report = self.module.build_prompt_versioning_stage098_review_report(
            phase2_contract_provider=lambda: phase2_contract
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P2"])
        self.assertIn("P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

    def test_semantic_and_runtime_drift_fail_closed(self) -> None:
        phase3 = copy.deepcopy(self.module._default_phase3_report())
        for scenario in phase3["scenario_results"]:
            if scenario["scenario_id"] == (
                "retrieval_document_cannot_override_ids_rule_prompt_version_control"
            ):
                scenario["prompt_injection_defense_state"] = (
                    "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_ACCEPTED"
                )
        report = self.module.build_prompt_versioning_stage098_review_report(
            phase3_report_provider=lambda: phase3
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertIn("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

        phase4 = copy.deepcopy(self.module._default_phase4_report())
        phase4["runtime_boundary"]["model_token_consumption_performed"] = True
        report = self.module.build_prompt_versioning_stage098_review_report(
            phase4_report_provider=lambda: phase4
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

    def test_review_document_contract_and_rollback_are_explicit(self) -> None:
        text = REVIEW_DOCUMENT.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "提示注入防护",
            "业务线白箱人工确认",
            "P4→P3 回退",
            "模型 Token",
            "IDS-STAGE099-P1-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        self.assertTrue(failures["stage099_must_remain_not_started"])
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_PROMPT_VERSIONING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            rollback["fallback_result"],
        )
        self.assertFalse(rollback["actual_runtime_or_production_state_changed"])

    def test_governance_projection_records_review_when_current(self) -> None:
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
            "IDS-STAGE098",
            "IDS-STAGE098-P4",
            "IDS-V0_1-STAGE098-P4",
            "IDS-STAGE098-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-REVIEW",
            "IDS-V0_1-STAGE098-REVIEW",
            "IDS-STAGE099-P1-GATE",
        )
        stage099_phase1_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P1",
            "IDS-V0_1-STAGE099-P1",
            "IDS-STAGE099-P2-GATE",
        )
        stage099_phase2_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P2",
            "IDS-V0_1-STAGE099-P2",
            "IDS-STAGE099-P3-GATE",
        )
        stage099_phase3_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P3",
            "IDS-V0_1-STAGE099-P3",
            "IDS-STAGE099-P4-GATE",
        )

        stage099_phase4_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-P4",
            "IDS-V0_1-STAGE099-P4",
            "IDS-STAGE099-REVIEW-GATE",
        )

        stage099_review_current = (
            "IDS-STAGE099",
            "IDS-STAGE099-REVIEW",
            "IDS-V0_1-STAGE099-REVIEW",
            "IDS-STAGE100-P1-GATE",
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertIn(
            current,
            (
                phase4_current,
                review_current,
                stage099_phase1_current,
                stage099_phase2_current,
                stage099_phase3_current,
                stage099_phase4_current,
                stage099_review_current,
            ),
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase4_current:
            self.assertTrue(P4_RUN.is_file())
            self.assertEqual("P4 交付证据已完成", acceptance_by_id["ACC-STAGE-098"])
        else:
            self.assertTrue(REVIEW_RUN.is_file())
            receipt = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
            self.assertEqual(self.module.PASS_RESULT, receipt["result"])
            self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
            self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-098"])
            for acceptance_id in (
                "ACC-STAGE098-REVIEW-01",
                "ACC-STAGE098-REVIEW-02",
                "ACC-STAGE098-REVIEW-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE098-REVIEW-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE098-REVIEW-20260825-001", event_ids)
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage098_review_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE099-P1-GATE"', roadmap_text)


if __name__ == "__main__":
    unittest.main()
