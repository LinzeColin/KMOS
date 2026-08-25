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
SCOPE = BASE / "STAGE104_PHASE2_RAG_NEGATIVE_TEST_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage104_rag_negative_testing_control_slice_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage104_rag_negative_testing_control_slice.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-104_RAG负向测试.md"
)
PHASE1_SCOPE = BASE / "STAGE104_PHASE1_RAG_NEGATIVE_TEST_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage104_rag_negative_testing_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE103_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE / "index_version_schema" / "stage103_model_output_permission_gate_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage103-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-26-stage104-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


EXPECTED_NEGATIVE_TEST_CASES = {
    "DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
    "EVIDENCE_GAP_CANNOT_PRESENT_AS_INTERNAL_EXPERIENCE",
    "HIGH_RISK_ENGINEERING_ADVICE_CANNOT_AUTO_FINALIZE",
    "CONTRACTUAL_COMMITMENT_CANNOT_AUTO_FINALIZE",
    "PRODUCTION_WRITEBACK_CANNOT_AUTO_FINALIZE",
}
EXPECTED_OUTPUT_CATEGORIES = {
    "safe_summary",
    "draft_recommendation",
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}
HUMAN_CONFIRMATION_CATEGORIES = {
    "high_risk_engineering_advice",
    "contractual_commitment",
    "production_writeback",
}


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage104_rag_negative_testing_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage104 P2 RAG 负向测试受控最小切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage104RagNegativeTestingPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_rag_negative_testing_control_slice(
            cls.control_input
        )

    def test_scope_contract_module_taskpack_and_predecessors_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE1_SCOPE,
            PHASE1_CONTRACT,
            PHASE1_RECEIPT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_RECEIPT,
            RECEIPT,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage104.rag_negative_testing.phase2.v1", contract["schema_version"]
        )
        self.assertEqual("STAGE-104", contract["stage"])
        self.assertEqual("IDS-STAGE104-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE104-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-104", contract["acceptance_id"])
        self.assertEqual(
            "RAG_NEGATIVE_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE104-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE104-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE104_TASKPACK_STAGE104_PHASE1_AND_STAGE103_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed"):
                with self.subTest(field=field):
                    self.assertIs(value, False)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage103_review_required"])
        self.assertTrue(predecessor["stage104_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_MODEL_OUTPUT_PERMISSION_GATE_RUNTIME_DISABLED",
            predecessor["stage103_review_result"],
        )
        self.assertEqual(
            "PASS_RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage104_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage103_review_preserved",
            "stage104_phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], True)
        for field in (
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage105_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertIs(boundary[field], False)

    def test_fixed_control_input_covers_negative_labels_and_record_shape(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(
            EXPECTED_NEGATIVE_TEST_CASES,
            {request["negative_test_case_id"] for request in requests},
        )
        self.assertEqual(29, len(self.module.INPUT_FIELDS))
        required_record_fields = {
            "query_ref",
            "index_version_ref",
            "prompt_version_ref",
            "model_version_ref",
            "selected_evidence_ref",
        }
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                self.assertTrue(required_record_fields.issubset(request))
                for field in required_record_fields:
                    self.assertTrue(
                        request[field].startswith(":control:stage104-p2:"), field
                    )
                self.assertEqual(
                    "CONTROL_UNTRUSTED_NON_EXECUTABLE_REFERENCE",
                    request["document_instruction_evidence_state"],
                )
                self.assertEqual(
                    "CONTROL_IDS_RULES_PREVAIL", request["ids_rule_precedence_state"]
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_REJECTED_REFERENCE_ONLY",
                    request["injection_defense_state"],
                )
                self.assertEqual(
                    "external_augmentation_opinion",
                    request["external_augmentation_display_label"],
                )
                self.assertEqual(
                    "CONTROL_NEGATIVE_TEST_LABEL_ONLY_NO_RUNTIME_EXECUTION",
                    request["negative_test_execution_state"],
                )
                self.assertEqual(
                    request["internal_evidence_ref"] is None,
                    request["evidence_gap_ref"] is not None,
                )
        self.assertEqual(
            {
                "CONTROL_OUTPUT_CATEGORY_SAFE_SUMMARY",
                "CONTROL_OUTPUT_CATEGORY_DRAFT_RECOMMENDATION",
                "CONTROL_OUTPUT_CATEGORY_HIGH_RISK_ENGINEERING_ADVICE",
                "CONTROL_OUTPUT_CATEGORY_CONTRACTUAL_COMMITMENT",
                "CONTROL_OUTPUT_CATEGORY_PRODUCTION_WRITEBACK",
            },
            {request["output_category"] for request in requests},
        )

    def test_accepted_control_slice_projects_exact_shape(self):
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(self.module.PASS_RESULT, result["execution_state"])
        self.assertIsNone(result["failure_state"])
        self.assertEqual(5, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(57, result["control_projection_field_total_per_request"])
        self.assertEqual(285, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(5, len(projections))
                self.assertEqual(5, result[f"{prefix}_control_projection_count"])
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_document_source_and_output_controls_remain_closed(self):
        defense = self.result["document_evidence_and_rule_defense_control_projections"]
        source = self.result["source_semantics_and_external_augmentation_control_projections"]
        output = self.result["output_permission_and_whitebox_gate_control_projections"]
        self.assertEqual(5, len(defense))
        self.assertEqual(5, len(source))
        self.assertEqual(5, len(output))
        for defense_record, source_record, output_record in zip(defense, source, output):
            with self.subTest(label=output_record["negative_test_case_id"]):
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_OVERRIDE_IDS_RULE",
                    defense_record["document_instruction_cannot_override_ids_rule_state"],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_RELAX_OUTPUT_PERMISSION",
                    defense_record[
                        "document_instruction_cannot_relax_output_permission_state"
                    ],
                )
                self.assertEqual(
                    "CONTROL_DOCUMENT_INSTRUCTION_CANNOT_BYPASS_HUMAN_CONFIRMATION",
                    defense_record[
                        "document_instruction_cannot_bypass_human_confirmation_state"
                    ],
                )
                self.assertFalse(defense_record["actual_document_content_read_performed"])
                self.assertFalse(defense_record["actual_document_instruction_processed"])
                self.assertEqual(
                    "external_augmentation_opinion",
                    source_record["external_augmentation_display_label"],
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING_RETAINED",
                    source_record["external_augmentation_display_composition_state"],
                )
                self.assertTrue(
                    source_record["external_augmentation_may_not_replace_internal_evidence"]
                )
                self.assertFalse(source_record["actual_source_type_bound"])
                self.assertFalse(source_record["actual_external_augmentation_displayed"])
                category = output_record["output_category"]
                self.assertIn(category, EXPECTED_OUTPUT_CATEGORIES)
                self.assertEqual(
                    category in HUMAN_CONFIRMATION_CATEGORIES,
                    output_record[
                        "business_line_whitebox_human_confirmation_required"
                    ],
                )
                for field in (
                    "automatic_final_conclusion_allowed",
                    "automatic_answer_publication_allowed",
                    "automatic_production_writeback_allowed",
                    "actual_output_classified",
                    "actual_human_confirmation_recorded",
                    "actual_final_conclusion_published",
                    "actual_production_writeback_performed",
                ):
                    with self.subTest(field=field):
                        self.assertFalse(output_record[field])

    def test_evidence_gap_case_remains_distinct_from_internal_experience(self):
        records = self.result[
            "source_semantics_and_external_augmentation_control_projections"
        ]
        gap_records = [
            record
            for record in records
            if record["negative_test_case_id"]
            == "EVIDENCE_GAP_CANNOT_PRESENT_AS_INTERNAL_EXPERIENCE"
        ]
        self.assertEqual(1, len(gap_records))
        gap_record = gap_records[0]
        self.assertIsNone(gap_record["internal_evidence_ref"])
        self.assertTrue(gap_record["evidence_gap_ref"].endswith("reference-only"))
        self.assertEqual(
            "CONTROL_EVIDENCE_GAP_NOT_INTERNAL_EXPERIENCE",
            gap_record["evidence_gap_presentation_state"],
        )

    def test_input_drift_fails_closed_without_projection_or_runtime(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["ids_rule_ref"] = (
            "CONTROL_INPUT_DRIFT"
        )
        rejected = self.module.execute_rag_negative_testing_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(self.module.REJECTED_RESULT, rejected["execution_state"])
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        self.assertEqual(0, rejected["control_projection_field_total"])
        self.assertFalse(rejected["persistent_record_created"])
        self.assertTrue(
            all(
                value == 0
                for key, value in rejected.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        self.assertTrue(
            all(value is False for value in rejected["runtime_boundary"].values())
        )
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                self.assertEqual([], rejected[f"{prefix}_control_projections"])
                self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_boundary_receipt_and_current_governance_are_exact(self):
        scope_text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "五条固定、非业务、`reference-only`",
            "P3 才验证异常场景",
            "不生成业务结论",
            "IDS-STAGE104-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope_text)
        self.assertTrue(
            all(
                value == 0
                for key, value in self.result.items()
                if key.startswith("actual_") and isinstance(value, int)
            )
        )
        self.assertTrue(
            all(value is False for value in self.result["runtime_boundary"].values())
        )
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P1",
            "IDS-V0_1-STAGE104-P1",
            "IDS-STAGE104-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE104",
            "IDS-STAGE104-P2",
            "IDS-V0_1-STAGE104-P2",
            "IDS-STAGE104-P3-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current},
            status,
            plan,
            ROADMAP,
        )
        if current == phase2_current:
            self.assertFalse(is_current_projection)
            self.assertEqual(
                "RAG_NEGATIVE_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
                status["evidence_status"],
            )
            self.assertIn("IDS-STAGE104-P3-GATE", plan["stop_condition"])
        else:
            self.assertTrue(is_current_projection)
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        if current == phase2_current:
            self.assertEqual("P2 受控最小切片已完成", acceptance_by_id["ACC-STAGE-104"])
        for acceptance_id in (
            "ACC-STAGE104-P2-01",
            "ACC-STAGE104-P2-02",
            "ACC-STAGE104-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE104-P2-04"])
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(self.module.PASS_RESULT, receipt["result"])
        self.assertEqual("IDS-STAGE104-P3-GATE", receipt["next_gate"])
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(
            all(value is False for value in receipt["runtime_flags"].values())
        )
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE104-P2-20260826-001", event_ids)


if __name__ == "__main__":
    unittest.main()
