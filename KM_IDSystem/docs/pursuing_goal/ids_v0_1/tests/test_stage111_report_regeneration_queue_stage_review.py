"""Stage111 报告重新生成队列整阶段机械复审的聚焦验证。"""

from __future__ import annotations

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
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-111_报告重新生成队列.md"
)
SCOPE = BASE / "STAGE111_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_stage_review_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage111_report_regeneration_queue_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage111_report_regeneration_queue_contract.json"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_control_slice_contract.json"
)
P2_MODULE = (
    BASE / "index_version_schema" / "stage111_report_regeneration_queue_control_slice.py"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_controlled_scenarios.py"
)
P4_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage111_report_regeneration_queue_delivery_contract.json"
)
P4_MODULE = BASE / "index_version_schema" / "stage111_report_regeneration_queue_delivery.py"
P4_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-p4-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE110_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage110_report_quality_score_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage110-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage111-review-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage111ReportRegenerationQueueStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module(MODULE, "stage111_review_for_test")
        cls.phase2 = _load_module(P2_MODULE, "stage111_phase2_for_review_test")
        cls.phase3 = _load_module(P3_MODULE, "stage111_phase3_for_review_test")
        cls.phase4 = _load_module(P4_MODULE, "stage111_phase4_for_review_test")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase1_contract = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        cls.phase2_report = cls.phase2.execute_report_regeneration_queue_control_slice(
            cls.phase2.build_control_input()
        )
        cls.phase3_report = cls.phase3.build_report_regeneration_queue_phase3_report()
        cls.phase4_report = cls.phase4.build_report_regeneration_queue_phase4_delivery_report()
        cls.report = cls.module.build_report_regeneration_queue_stage_review()

    def test_required_scope_contract_modules_and_predecessors_exist(self) -> None:
        for artifact in (
            TASKPACK,
            SCOPE,
            CONTRACT,
            MODULE,
            P1_CONTRACT,
            P2_CONTRACT,
            P2_MODULE,
            P3_CONTRACT,
            P3_MODULE,
            P4_CONTRACT,
            P4_MODULE,
            P4_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_reviewed_shape_failure_contract_and_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual("STAGE-111", contract["stage"])
        self.assertEqual("IDS-STAGE111-REVIEW", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE111-REVIEW", contract["task_id"])
        self.assertEqual(self.module.REVIEW_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        self.assertEqual(
            "STAGE111_REPORT_REGENERATION_QUEUE_REVIEW_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual(
            self.module.REVIEWED_CONTROL_SHAPE,
            contract["reviewed_phase_contract"],
        )
        failure = contract["failure_and_stop_contract"]
        self.assertEqual(
            self.module.FAILURE_STATES,
            tuple(failure["declared_failure_states"]),
        )
        self.assertEqual(10, failure["failure_state_count"])
        self.assertTrue(failure["stage112_must_remain_not_started"])
        self.assertFalse(failure["actual_model_or_token_execution_allowed"])
        self.assertFalse(failure["actual_agent_or_ovh_execution_allowed"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage110_review_evidence_declared",
            "stage111_phase1_completed",
            "stage111_phase2_completed",
            "stage111_phase3_completed",
            "stage111_phase4_completed",
            "stage111_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in ("stage112_started", "github_upload_allowed", "push_allowed"):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_review_passes_with_exact_phase_results_shapes_and_zero_runtime(self) -> None:
        report = self.report
        self.assertTrue(report["valid"])
        self.assertEqual(self.module.PASS_RESULT, report["result"])
        self.assertIsNone(report["failure_state"])
        self.assertEqual(self.module.REVIEW_GATE, report["current_gate"])
        self.assertEqual(self.module.NEXT_GATE, report["next_gate"])
        for field in (
            "phase1_static_contract_reviewed",
            "phase2_control_slice_reviewed",
            "phase3_controlled_scenarios_reviewed",
            "phase4_delivery_evidence_reviewed",
            "control_references_opaque",
            "single_authority_boundary_preserved",
            "report_regeneration_queue_semantics_preserved",
            "business_line_whitebox_gate_preserved",
            "phase4_to_phase3_rollback_preserved",
            "stage111_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertFalse(report["stage112_started"])
        self.assertEqual(
            self.module.REVIEWED_CONTROL_SHAPE,
            report["reviewed_control_shape"],
        )
        self.assertEqual(
            {
                "phase1_contract_state": self.module.P1_CONTRACT_STATE,
                "phase2_control_slice_result": self.module.P2_PASS_RESULT,
                "phase3_controlled_scenarios_result": self.module.P3_PASS_RESULT,
                "phase4_delivery_evidence_result": self.module.P4_PASS_RESULT,
            },
            report["reviewed_phase_results"],
        )
        self.assertEqual(4, len(report["chinese_feedback"]))
        self.assertTrue(
            all(
                value == 0
                for key, value in report.items()
                if key.startswith("actual_") and key.endswith("_count")
            )
        )
        self.assertTrue(
            all(value is False for value in report["runtime_boundary"].values())
        )

    def test_queue_semantics_whitebox_lifecycle_and_rollback_are_preserved(self) -> None:
        scenarios = self.phase3_report["scenario_results"]
        self.assertEqual(5, len(scenarios))
        for scenario in scenarios:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertNotEqual(
                    scenario["evidence_id_ref"] is None,
                    scenario["evidence_gap_ref"] is None,
                )
                self.assertTrue(
                    scenario[
                        "external_augmentation_may_not_be_internal_project_evidence"
                    ]
                )
                self.assertTrue(scenario["external_augmentation_may_not_close_evidence_gap"])
                self.assertFalse(scenario["actual_queue_entry_created"])
                self.assertFalse(scenario["actual_report_status_updated"])
                self.assertFalse(scenario["actual_human_confirmation_recorded"])
        for field, expected in (
            (
                "source_withdrawal_report_status_impact_state",
                "CONTROL_FUTURE_SOURCE_WITHDRAWAL_REPORT_STATUS_AND_QUEUE_REVIEW_REQUIRED",
            ),
            (
                "evidence_downgrade_report_status_impact_state",
                "CONTROL_FUTURE_EVIDENCE_DOWNGRADE_REPORT_STATUS_AND_QUEUE_REVIEW_REQUIRED",
            ),
            (
                "evidence_conflict_report_status_impact_state",
                "CONTROL_FUTURE_EVIDENCE_CONFLICT_REPORT_STATUS_AND_QUEUE_REVIEW_REQUIRED",
            ),
            (
                "index_version_change_report_status_impact_state",
                "CONTROL_FUTURE_INDEX_VERSION_CHANGE_REPORT_STATUS_AND_QUEUE_REVIEW_REQUIRED",
            ),
        ):
            with self.subTest(field=field):
                self.assertIn(expected, {item[field] for item in scenarios})
        handlings = self.phase3_report["business_line_whitebox_handlings"]
        self.assertEqual(5, len(handlings))
        self.assertTrue(all(item["whitebox_confirmation_required"] for item in handlings))
        self.assertTrue(all(not item["human_confirmation_recorded"] for item in handlings))
        lifecycle = self.phase4_report["regeneration_and_withdrawal_control_records"]
        self.assertEqual({"REPORT_REGENERATION", "REPORT_WITHDRAWAL"}, {item["control_domain"] for item in lifecycle})
        self.assertTrue(
            all(
                item["rollback_target_result"] == self.module.P3_PASS_RESULT
                and item["business_line_whitebox_confirmation_required"]
                and item["human_confirmation_required"]
                and item["versioned_basis_required"]
                and item["verifiable_rollback_target_required"]
                for item in lifecycle
            )
        )

    def test_each_phase_drift_fails_closed(self) -> None:
        phase1 = copy.deepcopy(self.phase1_contract)
        phase1["report_regeneration_queue_control_contract"][
            "future_control_reference_field_count"
        ] = 29
        p1_failed = self.module.build_report_regeneration_queue_stage_review(
            phase1_contract_provider=lambda: phase1
        )
        phase2 = copy.deepcopy(self.phase2_report)
        phase2["control_projection_field_total"] = 1
        p2_failed = self.module.build_report_regeneration_queue_stage_review(
            phase2_provider=lambda: phase2
        )
        phase3 = copy.deepcopy(self.phase3_report)
        phase3["scenario_results"][0]["actual_queue_entry_created"] = True
        p3_failed = self.module.build_report_regeneration_queue_stage_review(
            phase3_provider=lambda: phase3
        )
        phase4 = copy.deepcopy(self.phase4_report)
        phase4["regeneration_and_withdrawal_control_records"][0][
            "rollback_target_result"
        ] = "unexpected"
        p4_failed = self.module.build_report_regeneration_queue_stage_review(
            phase4_provider=lambda: phase4
        )
        expected = (
            (p1_failed, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (p2_failed, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (p3_failed, "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (p4_failed, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
        )
        for failed, failure_state in expected:
            with self.subTest(failure=failure_state):
                self.assertFalse(failed["valid"])
                self.assertEqual(self.module.FAIL_RESULT, failed["result"])
                self.assertEqual(failure_state, failed["failure_state"])
                self.assertEqual(self.module.REVIEW_GATE, failed["next_gate"])
                self.assertTrue(
                    all(value == 0 for key, value in failed.items() if key.startswith("actual_"))
                )
                self.assertTrue(
                    all(value is False for value in failed["runtime_boundary"].values())
                )

    def test_scope_contract_and_review_output_keep_every_runtime_surface_closed(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "evidence_id/evidence_gap",
            "报告状态与队列复核",
            "业务线白箱",
            "P4→P3",
            "模型 Token",
            "IDS-STAGE112-P1-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        self.assertTrue(
            all(value == 0 for value in self.contract["runtime_counts"].values())
        )
        self.assertEqual(
            self.module.P4_PASS_RESULT,
            self.contract["rollback_contract"]["fallback_result"],
        )

    def test_current_governance_receipt_and_event_are_exact(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("Review 最终治理投影将在全量本地验收完成后启用")

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        review_current = (
            "IDS-STAGE111",
            "IDS-STAGE111-REVIEW",
            "IDS-V0_1-STAGE111-REVIEW",
            "IDS-STAGE112-P1-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self, current, {review_current}, status, plan, ROADMAP
        )
        self.assertTrue(is_current_projection or current == review_current)
        if is_current_projection:
            return
        self.assertEqual(
            "REVIEWED_REPORT_REGENERATION_QUEUE_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual(self.module.REVIEW_GATE, receipt["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
        self.assertEqual(self.module.REVIEWED_CONTROL_SHAPE, receipt["controlled_replay"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(7, validation["focused_review_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        self.assertIn("IDS-STAGE112-P1-GATE", plan["stop_condition"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-111"])
        for acceptance_id in (
            "ACC-STAGE111-REVIEW-01",
            "ACC-STAGE111-REVIEW-02",
            "ACC-STAGE111-REVIEW-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE111-REVIEW-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE111-REVIEW-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
