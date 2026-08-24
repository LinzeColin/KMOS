"""Stage096 知识库投毒防护整阶段机械复审的聚焦测试。"""

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
    / "STAGE-096_知识库投毒防护.md"
)
NEXT_TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)
REVIEW_DOCUMENT = BASE / "STAGE096_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_stage_review_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage096_knowledge_base_poisoning_defense_contract.json"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_control_slice_contract.json"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_controlled_scenarios_contract.json"
)
P4_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_delivery_contract.json"
)
P2_MODULE = (
    BASE / "index_version_schema" / "stage096_knowledge_base_poisoning_defense_control_slice.py"
)
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_controlled_scenarios.py"
)
P4_MODULE = (
    BASE / "index_version_schema" / "stage096_knowledge_base_poisoning_defense_delivery.py"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
P4_RUN = ROOT / "machine" / "runs" / "2026-08-24-stage096-p4-local.json"
REVIEW_RUN = ROOT / "machine" / "runs" / "2026-08-25-stage096-review-local.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage096ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.module = load_module("stage096_review_test", MODULE)
        cls.report = cls.module.build_knowledge_base_poisoning_defense_stage096_review_report()

    def test_required_phase_artifacts_exist(self) -> None:
        for path in (
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
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
        self.assertEqual("IDS-STAGE096-REVIEW", self.contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE096-REVIEW", self.contract["task_id"])
        self.assertEqual("IDS-STAGE096-REVIEW-GATE", self.contract["entry_gate"])
        self.assertEqual("IDS-STAGE097-P1-GATE", self.contract["next_gate"])

    def test_contract_keeps_authority_runtime_and_stage097_closed(self) -> None:
        authority = self.contract["source_authority"]
        for field in (
            "review_can_replace_source_document",
            "review_can_become_business_fact_authority",
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
            "retrieval_result_access_performed",
            "evidence_ledger_access_performed",
            "report_or_audit_log_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(authority[field])
        replay = self.contract["reviewed_phase_contract"]
        self.assertEqual("8/6/5/14", replay["phase1_static_shape"])
        self.assertEqual(6, replay["phase2_control_request_count"])
        self.assertEqual(348, replay["phase2_control_field_check_count"])
        self.assertEqual(7, replay["phase3_scenario_count"])
        self.assertEqual(224, replay["phase3_scenario_field_check_count"])
        self.assertEqual("7/7/7/7/7/4/2", replay["phase4_delivery_shape"])
        self.assertEqual(517, replay["phase4_delivery_field_check_count"])
        self.assertTrue(replay["malicious_evidence_quarantine_required"])
        self.assertTrue(replay["low_grade_high_trust_rejection_required"])
        runtime = self.contract["runtime_boundary"]
        self.assertTrue(
            all(value == 0 for key, value in runtime.items() if key.startswith("actual_"))
        )
        self.assertTrue(
            all(value is False for key, value in runtime.items() if not key.startswith("actual_"))
        )
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage095_review_evidence_declared",
            "stage096_started",
            "phase1_completed",
            "phase2_completed",
            "phase3_completed",
            "phase4_completed",
            "stage096_review_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "whole_stage_review_performed",
            "stage097_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_phase_contracts_and_control_reports_pass(self) -> None:
        self.assertTrue(self.report["review_valid"])
        self.assertEqual(
            {"P1": True, "P2": True, "P3": True, "P4": True},
            self.report["phase_results"],
        )
        self.assertEqual(self.module.PASS_RESULT, self.report["result"])
        self.assertEqual(self.module.NEXT_GATE, self.report["next_gate"])

    def test_controlled_replay_has_exact_frozen_shapes(self) -> None:
        self.assertEqual(
            self.module.EXPECTED_CONTROLLED_REPLAY,
            self.report["controlled_replay"],
        )

    def test_authority_rollback_and_runtime_are_closed(self) -> None:
        invariants = self.report["review_invariants"]
        self.assertTrue(invariants["single_authority_boundary_preserved"])
        self.assertTrue(invariants["owner_whitebox_boundary_preserved"])
        self.assertTrue(invariants["failure_stop_and_rollback_boundaries_preserved"])
        self.assertTrue(invariants["delivery_and_whitebox_boundaries_preserved"])
        self.assertTrue(invariants["runtime_actions_disabled"])
        self.assertFalse(self.report["second_authoritative_source_created"])
        self.assertFalse(self.report["source_body_or_path_allowed"])
        self.assertEqual(
            "PASS_KNOWLEDGE_BASE_POISONING_DEFENSE_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            self.report["rollback"]["return_to"],
        )
        self.assertTrue(
            all(
                value == 0
                for key, value in self.report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(
            all(
                self.report[field] is False
                for field in self.module.REVIEW_RUNTIME_FALSE_FIELDS
            )
        )

    def test_stage097_stays_closed_except_for_gate(self) -> None:
        invariants = self.report["review_invariants"]
        self.assertTrue(invariants["next_stage_taskpack_available_but_not_started"])
        self.assertTrue(invariants["stage097_gate_only_opens_after_review"])
        self.assertTrue(self.report["stage096_started"])
        self.assertTrue(self.report["stage096_review_started"])
        self.assertFalse(self.report["whole_stage_review_performed"])
        self.assertFalse(self.report["stage097_started"])
        self.assertFalse(self.report["github_upload_allowed"])
        self.assertFalse(self.report["push_allowed"])

    def test_invalid_phase_contracts_fail_closed(self) -> None:
        for phase_name, kwargs in (
            ("P1", {"phase1_contract_provider": lambda: {"task_id": "tampered"}}),
            ("P2", {"phase2_report_provider": lambda: {"input_accepted": False}}),
            ("P3", {"phase3_report_provider": lambda: {"valid": False}}),
            ("P4", {"phase4_report_provider": lambda: {"valid": False}}),
        ):
            with self.subTest(phase=phase_name):
                report = self.module.build_knowledge_base_poisoning_defense_stage096_review_report(
                    **kwargs
                )
                self.assertFalse(report["review_valid"])
                self.assertFalse(report["phase_results"][phase_name])
                self.assertEqual(self.module.REVIEW_GATE, report["next_gate"])

    def test_semantic_and_runtime_drift_fail_closed(self) -> None:
        phase3 = self.module._default_phase3_report()
        altered_phase3 = copy.deepcopy(phase3)
        for scenario in altered_phase3["scenario_results"]:
            if scenario["scenario_id"] == "low_grade_high_trust_masquerade_control":
                scenario["high_trust_conclusion_allowed"] = True
        report = self.module.build_knowledge_base_poisoning_defense_stage096_review_report(
            phase3_report_provider=lambda: altered_phase3
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P3"])
        self.assertIn("P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

        phase4 = self.module._default_phase4_report()
        altered_phase4 = copy.deepcopy(phase4)
        altered_phase4["runtime_boundary"]["model_token_consumption_performed"] = True
        report = self.module.build_knowledge_base_poisoning_defense_stage096_review_report(
            phase4_report_provider=lambda: altered_phase4
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertIn("P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID", report["failure_reasons"])

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
            "IDS-STAGE096",
            "IDS-STAGE096-P4",
            "IDS-V0_1-STAGE096-P4",
            "IDS-STAGE096-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE096",
            "IDS-STAGE096-REVIEW",
            "IDS-V0_1-STAGE096-REVIEW",
            "IDS-STAGE097-P1-GATE",
        )
        stage097_phase1_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P1",
            "IDS-V0_1-STAGE097-P1",
            "IDS-STAGE097-P2-GATE",
        )
        stage097_phase2_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P2",
            "IDS-V0_1-STAGE097-P2",
            "IDS-STAGE097-P3-GATE",
        )
        stage097_phase3_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P3",
            "IDS-V0_1-STAGE097-P3",
            "IDS-STAGE097-P4-GATE",
        )
        stage097_phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        stage097_review_current = (
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
        self.assertEqual(status["task"], plan["task"])
        self.assertIn(
            current,
            (
                phase4_current,
                review_current,
                stage098_phase1_current,
                stage097_phase1_current,
                stage097_phase2_current,
                stage097_phase3_current,
                stage097_phase4_current,
                stage097_review_current,
                stage098_phase1_current,
            ),
        )
        if current in (
            review_current,
            stage098_phase1_current,
            stage097_phase1_current,
            stage097_phase2_current,
            stage097_phase3_current,
            stage097_phase4_current,
            stage097_review_current,
            stage098_phase1_current,
        ):
            self.assertTrue(REVIEW_RUN.is_file())
            run = json.loads(REVIEW_RUN.read_text(encoding="utf-8"))
            acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
            self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-096"])
            for acceptance_id in (
                "ACC-STAGE096-REVIEW-01",
                "ACC-STAGE096-REVIEW-02",
                "ACC-STAGE096-REVIEW-03",
            ):
                with self.subTest(acceptance_id=acceptance_id):
                    self.assertEqual("已通过", acceptance_by_id[acceptance_id])
            self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE096-REVIEW-04"])
            self.assertIn("EVT-IDS-V0_1-STAGE096-REVIEW-20260825-001", event_ids)
            self.assertEqual("IDS-STAGE097-P1-GATE", run["next_gate"])
            self.assertEqual(self.module.PASS_RESULT, run["result"])
            self.assertTrue(all(value == 0 for value in run["runtime_counts"].values()))
            validation = run["validation"]
            self.assertEqual(9, validation["stage096_review_focused_test_count"])
            self.assertEqual(448, validation["inherited_successor_test_count"])
            self.assertEqual(
                457,
                validation["precise_stage088_to_stage096_review_chain_test_count"],
            )
            self.assertTrue(validation["full_whitebox_validation_recorded"])
            self.assertTrue(validation["final_validation_recorded"])
            self.assertFalse(validation["repository_wide_green_claimed"])
            self.assertFalse(validation["github_upload_allowed"])
            self.assertFalse(validation["push_allowed"])
            roadmap_text = ROADMAP.read_text(encoding="utf-8")
            self.assertIn("stage096_review_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE096-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE097-P1-GATE"', roadmap_text)
        else:
            self.assertTrue(P4_RUN.is_file())


if __name__ == "__main__":
    unittest.main()
