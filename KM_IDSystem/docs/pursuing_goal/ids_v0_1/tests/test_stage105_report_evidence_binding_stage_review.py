"""Stage105 报告证据绑定整阶段机械复审的聚焦白箱验证。"""

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
SCOPE = BASE / "STAGE105_STAGE_REVIEW.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_stage_review_contract.json"
)
MODULE = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_stage_review.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-105_报告证据绑定.md"
)
P1_CONTRACT = BASE / "index_version_schema" / "stage105_report_evidence_binding_contract.json"
P2_CONTRACT = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_control_slice_contract.json"
)
P3_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage105_report_evidence_binding_controlled_scenarios_contract.json"
)
P4_CONTRACT = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_delivery_contract.json"
)
P4_MODULE = (
    BASE / "index_version_schema" / "stage105_report_evidence_binding_delivery.py"
)
P4_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-p4-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE104_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage104_rag_negative_testing_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage105-review-local.json"
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


class Stage105ReportEvidenceBindingStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module(
            MODULE, "stage105_report_evidence_binding_stage_review_for_test"
        )
        cls.phase4 = _load_module(
            P4_MODULE, "stage105_report_evidence_binding_phase4_for_review_test"
        )
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report_evidence_binding_stage_review()
        cls.phase4_report = (
            cls.phase4.build_report_evidence_binding_phase4_delivery_report()
        )

    def test_required_scope_contract_modules_and_predecessors_exist(self) -> None:
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            P1_CONTRACT,
            P2_CONTRACT,
            P3_CONTRACT,
            P4_CONTRACT,
            P4_MODULE,
            P4_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            STATUS,
            PLAN,
            ACCEPTANCE,
            EVENTS,
            ROADMAP,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_reviewed_shape_failure_contract_and_boundary_are_exact(self) -> None:
        contract = self.contract
        self.assertEqual(self.module.SCHEMA_VERSION, contract["schema_version"])
        self.assertEqual("STAGE-105", contract["stage"])
        self.assertEqual("IDS-STAGE105-REVIEW", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE105-REVIEW", contract["task_id"])
        self.assertEqual("ACC-STAGE-105", contract["acceptance_id"])
        self.assertEqual(self.module.REVIEW_GATE, contract["entry_gate"])
        self.assertEqual(self.module.NEXT_GATE, contract["next_gate"])
        self.assertEqual(
            "STAGE105_REPORT_EVIDENCE_BINDING_REVIEW_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual(
            self.module.REVIEWED_CONTROL_SHAPE,
            contract["reviewed_phase_contract"],
        )
        failure = contract["failure_and_stop_contract"]
        self.assertEqual(10, failure["failure_state_count"])
        self.assertEqual(
            self.module.FAILURE_STATES,
            tuple(failure["declared_failure_states"]),
        )
        self.assertFalse(failure["actual_model_or_token_execution_allowed"])
        self.assertFalse(failure["actual_agent_or_ovh_execution_allowed"])
        self.assertTrue(failure["stage106_must_remain_not_started"])
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage104_review_evidence_declared",
            "stage105_phase1_completed",
            "stage105_phase2_completed",
            "stage105_phase3_completed",
            "stage105_phase4_completed",
            "stage105_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in ("stage106_started", "github_upload_allowed", "push_allowed"):
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
            "business_line_whitebox_gate_preserved",
            "phase4_to_phase3_rollback_preserved",
            "stage105_review_started",
            "whole_stage_review_completed_in_memory_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(report[field])
        self.assertFalse(report["second_authoritative_source_created"])
        self.assertFalse(report["persistent_record_created"])
        self.assertFalse(report["stage106_started"])
        self.assertEqual(
            self.module.REVIEWED_CONTROL_SHAPE, report["reviewed_control_shape"]
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
        for field, value in report.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        for field, value in report["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_critical_binding_source_semantics_lifecycle_and_whitebox_gate_are_preserved(
        self,
    ) -> None:
        phase3 = _load_module(
            BASE
            / "index_version_schema"
            / "stage105_report_evidence_binding_controlled_scenarios.py",
            "stage105_phase3_for_review_semantics",
        )
        phase3_report = phase3.build_report_evidence_binding_phase3_report()
        scenario_by_id = {
            item["scenario_id"]: item for item in phase3_report["scenario_results"]
        }
        self.assertIsNotNone(
            scenario_by_id[
                "critical_conclusion_evidence_id_binding_integrity_control"
            ]["evidence_id_ref"]
        )
        self.assertIsNone(
            scenario_by_id[
                "critical_conclusion_evidence_gap_binding_integrity_control"
            ]["evidence_id_ref"]
        )
        external = scenario_by_id[
            "external_augmentation_retains_external_source_type_control"
        ]
        self.assertTrue(
            external["external_augmentation_may_not_be_internal_project_evidence"]
        )
        self.assertTrue(external["external_augmentation_may_not_close_evidence_gap"])
        lifecycle = scenario_by_id[
            "withdrawal_downgrade_and_index_change_impact_report_status_control"
        ]
        self.assertEqual(
            "CONTROL_FUTURE_REPORT_STATUS_IMPACT_REVIEW_REQUIRED",
            lifecycle["report_status_impact_state"],
        )
        self.assertFalse(lifecycle["actual_report_status_updated"])

        templates = self.phase4_report[
            "report_template_and_whitebox_confirmation_control_records"
        ]
        self.assertEqual(
            2,
            sum(
                item["business_line_whitebox_confirmation_required"]
                for item in templates
            ),
        )
        for item in templates:
            with self.subTest(scenario=item["scenario_id"]):
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    item["final_conclusion_state"],
                )
                self.assertFalse(item["actual_human_confirmation_performed"])
        for item in self.phase4_report[
            "regeneration_and_withdrawal_control_records"
        ]:
            with self.subTest(domain=item["control_domain"]):
                self.assertEqual(self.module.P3_PASS_RESULT, item["rollback_target_result"])
                self.assertTrue(item["business_line_whitebox_confirmation_required"])
                self.assertTrue(item["versioned_basis_required"])
                self.assertTrue(item["verifiable_rollback_target_required"])

    def test_tampered_phase_outputs_fail_closed_with_zero_runtime(self) -> None:
        malformed_p1 = json.loads(P1_CONTRACT.read_text(encoding="utf-8"))
        malformed_p1["report_evidence_binding_contract"][
            "future_control_reference_field_count"
        ] = 23
        malformed_p3 = _load_module(
            BASE
            / "index_version_schema"
            / "stage105_report_evidence_binding_controlled_scenarios.py",
            "stage105_phase3_for_review_failure",
        ).build_report_evidence_binding_phase3_report()
        malformed_p3 = copy.deepcopy(malformed_p3)
        malformed_p3["scenario_results"][0]["evidence_gap_ref"] = (
            malformed_p3["scenario_results"][1]["evidence_gap_ref"]
        )
        malformed_p4 = copy.deepcopy(self.phase4_report)
        malformed_p4["runtime_boundary"]["model_call_performed"] = True

        failures = (
            (
                self.module.build_report_evidence_binding_stage_review(
                    phase1_contract_provider=lambda: malformed_p1
                ),
                "P1_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_evidence_binding_stage_review(
                    phase2_provider=lambda: {}
                ),
                "P2_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_evidence_binding_stage_review(
                    phase3_provider=lambda: malformed_p3
                ),
                "P3_CONTRACT_OR_CONTROL_OUTPUT_INVALID",
            ),
            (
                self.module.build_report_evidence_binding_stage_review(
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

    def test_scope_contract_and_review_output_keep_every_runtime_surface_closed(self) -> None:
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "evidence_id/evidence_gap",
            "外部增强",
            "报告状态影响",
            "业务线白箱",
            "P4→P3",
            "模型 Token",
            "IDS-STAGE106-P1-GATE",
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

    def test_current_governance_accepts_only_phase4_or_review_projection(self) -> None:
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase4_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-P4",
            "IDS-V0_1-STAGE105-P4",
            "IDS-STAGE105-REVIEW-GATE",
        )
        review_current = (
            "IDS-STAGE105",
            "IDS-STAGE105-REVIEW",
            "IDS-V0_1-STAGE105-REVIEW",
            "IDS-STAGE106-P1-GATE",
        )
        stage106_phase1_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P1",
            "IDS-V0_1-STAGE106-P1",
            "IDS-STAGE106-P2-GATE",
        )
        stage106_phase2_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P2",
            "IDS-V0_1-STAGE106-P2",
            "IDS-STAGE106-P3-GATE",
        )
        stage106_phase3_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P3",
            "IDS-V0_1-STAGE106-P3",
            "IDS-STAGE106-P4-GATE",
        )
        stage106_phase4_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-P4",
            "IDS-V0_1-STAGE106-P4",
            "IDS-STAGE106-REVIEW-GATE",
        )
        stage106_review_current = (
            "IDS-STAGE106",
            "IDS-STAGE106-REVIEW",
            "IDS-V0_1-STAGE106-REVIEW",
            "IDS-STAGE107-P1-GATE",
        )
        stage107_phase1_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P1",
            "IDS-V0_1-STAGE107-P1",
            "IDS-STAGE107-P2-GATE",
        )
        stage107_phase2_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P2",
            "IDS-V0_1-STAGE107-P2",
            "IDS-STAGE107-P3-GATE",
        )
        stage107_phase3_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P3",
            "IDS-V0_1-STAGE107-P3",
            "IDS-STAGE107-P4-GATE",
        )
        stage107_phase4_current = (
            "IDS-STAGE107",
            "IDS-STAGE107-P4",
            "IDS-V0_1-STAGE107-P4",
            "IDS-STAGE107-REVIEW-GATE",
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
        if is_current_projection:
            self.assertTrue(is_current_projection)
        else:
            self.assertIn(current, {phase4_current})
        if current == phase4_current:
            self.assertFalse(is_current_projection)
        else:
            self.assertTrue(is_current_projection)
            self.assertTrue(RECEIPT.is_file())
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            self.assertEqual(self.module.PASS_RESULT, receipt["result"])
            self.assertEqual(self.module.NEXT_GATE, receipt["next_gate"])
            self.assertTrue(
                all(value == 0 for value in receipt["runtime_counts"].values())
            )
            self.assertTrue(
                all(value is False for value in receipt["runtime_flags"].values())
            )
            acceptance_by_id = {
                item["id"]: item["status"] for item in acceptance["items"]
            }
            self.assertEqual(
                "整阶段已复审", acceptance_by_id["ACC-STAGE-105"]
            )
            event_ids = {
                json.loads(line)["event_id"]
                for line in EVENTS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self.assertIn("EVT-IDS-V0_1-STAGE105-REVIEW-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
