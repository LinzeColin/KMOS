"""Stage109 报告影响分析整阶段机械复审的聚焦验证。"""

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
    / "STAGE-109_报告影响分析.md"
)
SCOPE = BASE / "STAGE109_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_stage_review_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_stage_review.py"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage109_report_impact_analysis_contract.json"
P2_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_control_slice_contract.json"
)
P2_MODULE = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_control_slice.py"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_controlled_scenarios_contract.json"
)
P3_MODULE = (
    BASE
    / "index_version_schema"
    / "stage109_report_impact_analysis_controlled_scenarios.py"
)
P4_CONTRACT = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_delivery_contract.json"
)
P4_MODULE = (
    BASE / "index_version_schema" / "stage109_report_impact_analysis_delivery.py"
)
P4_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-p4-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE108_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage108_report_snapshot_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage108-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage109-review-local.json"
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


class Stage109ReportImpactAnalysisStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module(MODULE, "stage109_review_for_test")
        cls.phase3 = _load_module(P3_MODULE, "stage109_phase3_for_review_test")
        cls.phase4 = _load_module(P4_MODULE, "stage109_phase4_for_review_test")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_impact_analysis_stage_review()
        cls.phase4_report = cls.phase4.build_report_impact_analysis_phase4_delivery_report()

    def test_required_scope_contract_modules_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
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
        self.assertEqual("STAGE-109", contract["stage"])
        self.assertEqual("IDS-STAGE109-REVIEW", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE109-REVIEW", contract["task_id"])
        self.assertEqual(self.module.REVIEW_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        self.assertEqual(
            "STAGE109_REPORT_IMPACT_ANALYSIS_REVIEW_RUNTIME_DISABLED",
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
        self.assertEqual(11, failure["failure_state_count"])
        self.assertTrue(failure["stage110_must_remain_not_started"])
        self.assertFalse(failure["actual_model_or_token_execution_allowed"])
        self.assertFalse(failure["actual_agent_or_ovh_execution_allowed"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage108_review_evidence_declared",
            "stage109_phase1_completed",
            "stage109_phase2_completed",
            "stage109_phase3_completed",
            "stage109_phase4_completed",
            "stage109_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "stage110_started",
            "github_upload_allowed",
            "push_allowed",
        ):
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
            "report_impact_semantics_preserved",
            "business_line_whitebox_gate_preserved",
            "phase4_to_phase3_rollback_preserved",
            "stage109_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertFalse(report["stage110_started"])
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

    def test_critical_binding_impact_semantics_and_whitebox_gate_are_preserved(self) -> None:
        scenarios = self.phase3.build_report_impact_analysis_phase3_report()[
            "scenario_results"
        ]
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
                self.assertTrue(
                    scenario["external_augmentation_may_not_close_evidence_gap"]
                )
                self.assertFalse(scenario["actual_report_impact_analysis_performed"])
                self.assertFalse(scenario["actual_report_status_impact_updated"])
                self.assertFalse(scenario["actual_human_confirmation_recorded"])
        self.assertIn(
            "CONTROL_SOURCE_WITHDRAWAL_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            {item["source_withdrawal_report_status_impact_state"] for item in scenarios},
        )
        self.assertIn(
            "CONTROL_EVIDENCE_DOWNGRADE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            {item["evidence_downgrade_report_status_impact_state"] for item in scenarios},
        )
        self.assertIn(
            "CONTROL_INDEX_VERSION_CHANGE_FUTURE_REPORT_STATUS_REVIEW_REQUIRED",
            {item["index_version_change_report_status_impact_state"] for item in scenarios},
        )
        self.assertIn(
            "CONTROL_AFFECTED_REPORT_AND_CRITICAL_CONCLUSION_FUTURE_REVIEW_REQUIRED",
            {item["affected_report_control_state"] for item in scenarios},
        )
        templates = self.phase4_report[
            "report_template_and_whitebox_confirmation_control_records"
        ]
        self.assertEqual(5, len(templates))
        for item in templates:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertTrue(item["business_line_whitebox_confirmation_required"])
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    item["final_conclusion_state"],
                )
                self.assertFalse(item["actual_human_confirmation_performed"])
        for item in self.phase4_report[
            "regeneration_and_withdrawal_control_records"
        ]:
            with self.subTest(domain=item["control_domain"]):
                self.assertEqual(
                    self.module.P3_PASS_RESULT,
                    item["rollback_target_result"],
                )
                self.assertTrue(item["business_line_whitebox_confirmation_required"])
                self.assertTrue(item["versioned_basis_required"])
                self.assertTrue(item["verifiable_rollback_target_required"])

    def test_tampered_phase_outputs_fail_closed_with_zero_runtime(self) -> None:
        malformed_p1 = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        malformed_p1["report_impact_analysis_contract"][
            "future_control_reference_field_count"
        ] = 32
        malformed_p3 = copy.deepcopy(
            self.phase3.build_report_impact_analysis_phase3_report()
        )
        malformed_p3["scenario_results"][0][
            "evidence_gap_ref"
        ] = ":control:stage109-review:tampered-evidence-gap:reference-only"
        malformed_p4 = copy.deepcopy(self.phase4_report)
        malformed_p4["runtime_boundary"]["model_call_performed"] = True

        failures = (
            (
                self.module.build_report_impact_analysis_stage_review(
                    phase1_contract_provider=lambda: malformed_p1
                ),
                "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_impact_analysis_stage_review(
                    phase2_provider=lambda: {}
                ),
                "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_impact_analysis_stage_review(
                    phase3_provider=lambda: malformed_p3
                ),
                "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_impact_analysis_stage_review(
                    phase4_provider=lambda: malformed_p4
                ),
                "P4_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
        )
        for failed_report, failure_state in failures:
            with self.subTest(failure=failure_state):
                self.assertFalse(failed_report["valid"])
                self.assertEqual(self.module.FAIL_RESULT, failed_report["result"])
                self.assertEqual(failure_state, failed_report["failure_state"])
                self.assertEqual(self.module.REVIEW_GATE, failed_report["next_gate"])
                self.assertEqual({}, failed_report["reviewed_control_shape"])
                self.assertTrue(
                    all(
                        value == 0
                        for key, value in failed_report.items()
                        if key.startswith("actual_") and key.endswith("_count")
                    )
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in failed_report["runtime_boundary"].values()
                    )
                )

    def test_current_governance_receipt_and_event_are_exact(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if receipt.get("final_validation", {}).get("state") == "IN_PROGRESS":
            self.skipTest("Review 最终治理投影将在全量本地验收完成后启用")
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase4_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-P4",
            "IDS-V0_1-STAGE109-P4",
            "IDS-STAGE109-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE109",
            "IDS-STAGE109-REVIEW",
            "IDS-V0_1-STAGE109-REVIEW",
            "IDS-STAGE110-P1-GATE",
        )
        stage110_phase1_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P1",
            "IDS-V0_1-STAGE110-P1",
            "IDS-STAGE110-P2-GATE",
        )
        stage110_phase2_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P2",
            "IDS-V0_1-STAGE110-P2",
            "IDS-STAGE110-P3-GATE",
        )
        stage110_phase3_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P3",
            "IDS-V0_1-STAGE110-P3",
            "IDS-STAGE110-P4-GATE",
        )
        stage110_phase4_current = (
            "IDS-STAGE110",
            "IDS-STAGE110-P4",
            "IDS-V0_1-STAGE110-P4",
            "IDS-STAGE110-REVIEW-GATE",
        )
        self.assertTrue(
            assert_legacy_or_current_projection(
                self, current, {phase4_current}, status, plan, ROADMAP
            )
        )
        if current in {
            stage110_phase1_current,
            stage110_phase2_current,
            stage110_phase3_current,
            stage110_phase4_current,
        }:
            return
        self.assertEqual(review_current, current)
        self.assertEqual(
            "REVIEWED_REPORT_IMPACT_ANALYSIS_RUNTIME_DISABLED",
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
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        validation = receipt["final_validation"]
        self.assertEqual(7, validation["focused_review_test_count"])
        self.assertEqual(
            38,
            validation["stage109_phase1_to_review_compatibility_test_count"],
        )
        self.assertEqual(
            1005,
            validation["stage088_to_stage109_precise_chain_test_count"],
        )
        self.assertTrue(validation["stage005_direct_validation_valid"])
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual("整阶段已复审", acceptance_by_id["ACC-STAGE-109"])
        for acceptance_id in (
            "ACC-STAGE109-REVIEW-01",
            "ACC-STAGE109-REVIEW-02",
            "ACC-STAGE109-REVIEW-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE109-REVIEW-04"])
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE109-REVIEW-20260826-001", event_ids)

    def test_scope_contract_and_review_output_keep_every_runtime_surface_closed(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "evidence_id/evidence_gap",
            "外部增强",
            "报告状态影响",
            "业务线白箱",
            "P4→P3",
            "模型 Token",
            "IDS-STAGE110-P1-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertEqual(0 if field.startswith("actual_") else False, value)
        self.assertEqual(
            self.module.P4_PASS_RESULT,
            self.contract["rollback_contract"]["fallback_result"],
        )


if __name__ == "__main__":
    unittest.main()
