"""Stage114 复核工作流整阶段机械复审验证。"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import unittest

from KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.current_governance_projection import (
    assert_legacy_or_current_projection,
)


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE114_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_stage_review_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage114_review_workflow_stage_review.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-114_复核工作流.md"
)
PHASE1_SCOPE = BASE / "STAGE114_PHASE1_REVIEW_WORKFLOW_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage114_review_workflow_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p1-local.json"
PHASE2_SCOPE = BASE / "STAGE114_PHASE2_REVIEW_WORKFLOW_CONTROL_SLICE.md"
PHASE2_CONTRACT = (
    BASE / "index_version_schema" / "stage114_review_workflow_control_slice_contract.json"
)
PHASE2_MODULE = (
    BASE / "index_version_schema" / "stage114_review_workflow_control_slice.py"
)
PHASE2_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p2-local.json"
PHASE3_SCOPE = BASE / "STAGE114_PHASE3_REVIEW_WORKFLOW_CONTROLLED_SCENARIOS.md"
PHASE3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_controlled_scenarios_contract.json"
)
PHASE3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage114_review_workflow_controlled_scenarios.py"
)
PHASE3_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p3-local.json"
PHASE4_SCOPE = BASE / "STAGE114_PHASE4_REVIEW_WORKFLOW_DELIVERY.md"
PHASE4_CONTRACT = (
    BASE / "index_version_schema" / "stage114_review_workflow_delivery_contract.json"
)
PHASE4_MODULE = (
    BASE / "index_version_schema" / "stage114_review_workflow_delivery.py"
)
PHASE4_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-p4-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE113_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage113_review_queue_schema_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage113-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-27-stage114-review-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage114ReviewWorkflowStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        prefix = "KM_IDSystem.docs.pursuing_goal.ids_v0_1.index_version_schema."
        cls.module = importlib.import_module(
            f"{prefix}stage114_review_workflow_stage_review"
        )
        cls.phase2 = importlib.import_module(
            f"{prefix}stage114_review_workflow_control_slice"
        )
        cls.phase3 = importlib.import_module(
            f"{prefix}stage114_review_workflow_controlled_scenarios"
        )
        cls.phase4 = importlib.import_module(
            f"{prefix}stage114_review_workflow_delivery"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase1_contract = json.loads(PHASE1_CONTRACT.read_text(encoding="utf-8"))
        cls.phase2_report = cls.phase2.project_review_workflow_control_slice(
            cls.phase2.build_control_input()
        )
        cls.phase3_report = cls.phase3.project_review_workflow_controlled_scenarios(
            cls.phase3.build_controlled_scenario_input()
        )
        cls.phase4_report = cls.phase4.build_review_workflow_phase4_delivery_report()
        cls.report = cls.module.build_review_workflow_stage_review()

    def test_required_scope_contract_modules_and_predecessors_exist(self) -> None:
        for artifact in (
            TASKPACK,
            SCOPE,
            CONTRACT,
            MODULE,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PHASE2_SCOPE,
            PHASE2_CONTRACT,
            PHASE2_MODULE,
            PHASE2_RECEIPT,
            PHASE3_SCOPE,
            PHASE3_CONTRACT,
            PHASE3_MODULE,
            PHASE3_RECEIPT,
            PHASE4_SCOPE,
            PHASE4_CONTRACT,
            PHASE4_MODULE,
            PHASE4_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact.name):
                self.assertTrue(artifact.is_file())

    def test_identity_reviewed_shape_failure_contract_and_boundary_are_exact(
        self,
    ) -> None:
        contract = self.contract
        self.assertEqual("STAGE-114", contract["stage"])
        self.assertEqual("IDS-STAGE114-REVIEW", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE114-REVIEW", contract["task_id"])
        self.assertEqual(self.module.REVIEW_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        self.assertEqual(
            "STAGE114_REVIEW_WORKFLOW_REVIEW_RUNTIME_DISABLED",
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
        self.assertTrue(failure["stage115_entry_requires_new_independent_run"])
        self.assertFalse(failure["actual_model_or_token_execution_allowed"])
        self.assertFalse(failure["actual_agent_or_ovh_execution_allowed"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage113_review_preserved",
            "stage114_phase1_completed",
            "stage114_phase2_completed",
            "stage114_phase3_completed",
            "stage114_phase4_completed",
            "stage114_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage115_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])

    def test_review_passes_with_exact_phase_results_shapes_and_zero_runtime(
        self,
    ) -> None:
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
            "review_audit_impact_and_whitebox_semantics_preserved",
            "phase4_to_phase3_rollback_preserved",
            "stage114_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertFalse(report["stage115_started"])
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

    def test_audit_impact_whitebox_and_rollback_semantics_are_preserved(self) -> None:
        scenarios = self.phase3_report["controlled_scenarios"]
        self.assertEqual(5, len(scenarios))
        for scenario in scenarios:
            with self.subTest(scenario=scenario["controlled_scenario_id"]):
                self.assertNotEqual(
                    scenario["evidence_id_ref"] is None,
                    scenario["evidence_gap_ref"] is None,
                )
                for field in (
                    "review_actor_ref",
                    "review_time_ref",
                    "review_transition_reason_ref",
                    "old_value_ref",
                    "new_value_ref",
                    "review_result_ref",
                    "review_audit_record_ref",
                ):
                    self.assertTrue(
                        scenario[field].startswith(":control:stage114-p2:")
                    )
        handlings = self.phase3_report["business_line_whitebox_handlings"]
        self.assertEqual(5, len(handlings))
        self.assertTrue(
            all(item["business_line_whitebox_confirmation_required"] for item in handlings)
        )
        self.assertTrue(
            all(
                item["actual_human_confirmation_execution_performed"] is False
                and item["actual_final_business_conclusion_recorded"] is False
                for item in handlings
            )
        )
        confirmations = self.phase4_report[
            "business_line_whitebox_confirmation_control_records"
        ]
        self.assertTrue(
            all(
                item["external_augmentation_source_separation_state"]
                == "CONTROL_EXTERNAL_AUGMENTATION_RETAINS_UNDERLYING_SOURCE_TYPE_SEPARATE_FROM_INTERNAL_EVIDENCE"
                and item["confirmation_required"]
                and item["automatic_final_conclusion_allowed"] is False
                for item in confirmations
            )
        )
        lifecycle = self.phase4_report[
            "rollback_and_re_review_instruction_control_records"
        ]
        self.assertEqual(
            {"REVIEW_WORKFLOW_ROLLBACK", "RE_REVIEW"},
            {item["control_domain"] for item in lifecycle},
        )
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

    def test_each_phase_or_semantic_drift_fails_closed(self) -> None:
        phase1 = copy.deepcopy(self.phase1_contract)
        phase1["review_workflow_input_output_control_contract"][
            "future_control_reference_field_count"
        ] = 25
        p1_failed = self.module.build_review_workflow_stage_review(
            phase1_contract_provider=lambda: phase1
        )
        phase2 = copy.deepcopy(self.phase2_report)
        phase2["control_projection_field_total"] = 1
        p2_failed = self.module.build_review_workflow_stage_review(
            phase2_provider=lambda: phase2
        )
        opaque = copy.deepcopy(self.phase3_report)
        opaque["controlled_scenarios"][0]["review_actor_ref"] = "CONTROL_OPAQUE_DRIFT"
        opaque_failed = self.module.build_review_workflow_stage_review(
            phase3_provider=lambda: opaque
        )
        whitebox = copy.deepcopy(self.phase3_report)
        whitebox["business_line_whitebox_handlings"][0][
            "business_line_whitebox_confirmation_required"
        ] = False
        whitebox_failed = self.module.build_review_workflow_stage_review(
            phase3_provider=lambda: whitebox
        )
        phase4 = copy.deepcopy(self.phase4_report)
        phase4["review_queue_sample_control_records"].pop()
        p4_failed = self.module.build_review_workflow_stage_review(
            phase4_provider=lambda: phase4
        )
        lifecycle = copy.deepcopy(self.phase4_report)
        lifecycle["rollback_and_re_review_instruction_control_records"][0][
            "rollback_target_result"
        ] = "CONTROL_INVALID_ROLLBACK_TARGET"
        lifecycle_failed = self.module.build_review_workflow_stage_review(
            phase4_provider=lambda: lifecycle
        )
        expected = (
            (p1_failed, "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (p2_failed, "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (opaque_failed, "CONTROL_REFERENCE_OPAQUENESS_MISMATCH"),
            (
                whitebox_failed,
                "REVIEW_AUDIT_IMPACT_AND_WHITEBOX_SEMANTICS_MISMATCH",
            ),
            (p4_failed, "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID"),
            (lifecycle_failed, "DELIVERY_AND_ROLLBACK_BOUNDARY_MISMATCH"),
        )
        for failed, failure_state in expected:
            with self.subTest(failure=failure_state):
                self.assertFalse(failed["valid"])
                self.assertEqual(self.module.FAIL_RESULT, failed["result"])
                self.assertEqual(failure_state, failed["failure_state"])
                self.assertEqual(self.module.REVIEW_GATE, failed["next_gate"])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed.items()
                        if key.startswith("actual_") and key.endswith("_count")
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in failed["runtime_boundary"].values()
                    )
                )

    def test_scope_contract_and_review_output_keep_runtime_surfaces_closed(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "actor、time、reason、old value、new value",
            "证据可信等级与报告质量／状态影响",
            "业务线白箱",
            "P4→P3",
            "IDS-STAGE115-P1-GATE",
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
        if not RECEIPT.is_file():
            self.skipTest("Review 最终治理投影将在冻结本地验收完成后启用")
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") != "PASS":
            self.skipTest("Review 最终治理投影将在冻结本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        review_current = (
            "IDS-STAGE114",
            "IDS-STAGE114-REVIEW",
            "IDS-V0_1-STAGE114-REVIEW",
            "IDS-STAGE115-P1-GATE",
        )
        stage115_phase1_current = (
            "IDS-STAGE115",
            "IDS-STAGE115-P1",
            "IDS-V0_1-STAGE115-P1",
            "IDS-STAGE115-P2-GATE",
        )
        stage115_phase2_current = (
            "IDS-STAGE115",
            "IDS-STAGE115-P2",
            "IDS-V0_1-STAGE115-P2",
            "IDS-STAGE115-P3-GATE",
        )
        future_projection = assert_legacy_or_current_projection(
            self,
            current,
            {review_current, stage115_phase1_current, stage115_phase2_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertFalse(future_projection)
        if current in {stage115_phase1_current, stage115_phase2_current}:
            return
        self.assertEqual(
            "REVIEWED_REVIEW_WORKFLOW_RUNTIME_DISABLED",
            status["evidence_status"],
        )
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual(self.module.REVIEW_GATE, receipt["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
        self.assertEqual(
            self.module.REVIEWED_CONTROL_SHAPE,
            receipt["controlled_replay"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        validation = receipt["final_validation"]
        self.assertEqual("PASS", validation["state"])
        self.assertEqual(7, validation["focused_review_test_count"])
        self.assertTrue(validation["stage005_direct_validation_valid"])
        self.assertTrue(validation["all_executed_validation_passed"])
        self.assertIn("IDS-STAGE115-P1-GATE", plan["stop_condition"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-114"])
        for acceptance_id in (
            "ACC-STAGE114-REVIEW-01",
            "ACC-STAGE114-REVIEW-02",
            "ACC-STAGE114-REVIEW-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE114-REVIEW-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE114-REVIEW-20260827-001", event_ids)


if __name__ == "__main__":
    unittest.main()
