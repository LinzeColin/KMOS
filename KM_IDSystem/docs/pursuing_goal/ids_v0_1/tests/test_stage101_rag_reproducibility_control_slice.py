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
SCOPE = BASE / "STAGE101_PHASE2_RAG_REPRODUCIBILITY_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage101_rag_reproducibility_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-101_RAG可复现.md"
)
PHASE1_SCOPE = BASE / "STAGE101_PHASE1_RAG_REPRODUCIBILITY_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage101_rag_reproducibility_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE100_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage101-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage101_rag_reproducibility_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Stage101 P2 RAG 可复现控制切片")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage101RagReproducibilityPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_rag_reproducibility_control_slice(
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
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_authority_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage101.rag_reproducibility.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-101", contract["stage"])
        self.assertEqual("IDS-STAGE101-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE101-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-101", contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE101-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE101-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE101_TASKPACK_STAGE101_PHASE1_AND_STAGE100_REVIEWED_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field not in {
                "authority",
                "frozen_taskpack_ref",
                "stage101_phase1_scope_ref",
                "stage101_phase1_contract_ref",
                "stage101_phase1_receipt_ref",
                "stage100_review_ref",
                "stage100_review_contract_ref",
                "stage100_review_receipt_ref",
                "source_document_remains_authoritative",
                "business_line_whitebox_human_review_remains_authoritative",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage100_review_required"])
        self.assertTrue(predecessor["stage101_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            predecessor["stage100_review_result"],
        )
        self.assertEqual(
            "PHASE1_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage101_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage100_review_evidence_declared",
            "stage101_started",
            "stage101_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage100_review_evidence_declared",
                "stage101_started",
                "stage101_entry_authorized",
                "phase1_completed",
                "phase2_started",
                "phase2_completed",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_fixed_control_input_has_complete_reproducibility_reference_shape(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(6, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(23, len(self.module.INPUT_FIELDS))
        required_reference_fields = {
            "rag_answer_structure_ref",
            "query_ref",
            "index_version_ref",
            "prompt_version_ref",
            "model_provider_ref",
            "model_version_ref",
            "temperature_ref",
            "retrieval_context_ref",
            "selected_evidence_ref",
            "internal_evidence_ref",
            "external_augmentation_ref",
            "evidence_gap_ref",
            "source_type_ref",
            "model_output_permission_ref",
            "human_confirmation_gate_ref",
        }
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                for field, value in request.items():
                    if field == "control_scenario" or value is None:
                        continue
                    self.assertTrue(
                        value.startswith(":control:stage101-p2:")
                        or value.startswith("CONTROL_"),
                        field,
                    )
                self.assertTrue(required_reference_fields.issubset(request))
                for field in (
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_provider_ref",
                    "model_version_ref",
                    "temperature_ref",
                    "retrieval_context_ref",
                    "selected_evidence_ref",
                ):
                    self.assertTrue(request[field].startswith(":control:stage101-p2:"))
                self.assertTrue(
                    request["retrieval_document_instruction_precedence_state"].endswith(
                        "IDS_RULES_PREVAIL"
                    )
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

    def test_accepted_control_slice_projects_exact_record_shape(self):
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "PASS_IN_MEMORY_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED",
            result["execution_state"],
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(6, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(45, result["control_projection_field_total_per_request"])
        self.assertEqual(270, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(6, result[f"{prefix}_control_projection_count"])
                self.assertEqual(6, len(projections))
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_reproducibility_record_and_source_semantics_remain_reference_only(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        bindings = self.result["reproducibility_record_binding_control_projections"]
        records = self.result["reproducibility_record_control_projections"]
        source_projections = self.result[
            "source_semantics_and_external_augmentation_display_control_projections"
        ]
        record_fields = (
            "query_ref",
            "index_version_ref",
            "prompt_version_ref",
            "model_provider_ref",
            "model_version_ref",
            "temperature_ref",
            "retrieval_context_ref",
            "selected_evidence_ref",
        )
        for request, binding, record, source in zip(
            requests, bindings, records, source_projections
        ):
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(
                    self.module.PHASE1_RAG_REPRODUCIBILITY_CONTRACT_REF,
                    binding["stage101_phase1_rag_reproducibility_contract_ref"],
                )
                self.assertEqual(
                    self.module.STAGE100_REVIEW_CONTROL_REF,
                    binding["stage100_review_control_ref"],
                )
                for field in record_fields:
                    self.assertEqual(request[field], binding[field])
                    self.assertEqual(request[field], record[field])
                self.assertEqual(
                    "CONTROL_REPRODUCIBILITY_RECORD_REFERENCE_ONLY",
                    record["record_shape_state"],
                )
                for field in (
                    "source_type_ref",
                    "source_type_separation_state",
                    "internal_evidence_ref",
                    "external_public_reference_ref",
                    "model_reasoning_ref",
                    "evidence_gap_ref",
                    "external_augmentation_ref",
                ):
                    self.assertEqual(request[field], source[field])
                self.assertEqual(
                    "external_augmentation_opinion",
                    source["external_augmentation_display_label"],
                )
                self.assertEqual("internal_evidence", source["internal_evidence_source_type"])
                self.assertEqual(
                    "external_public_reference",
                    source["external_public_reference_source_type"],
                )
                self.assertEqual("model_reasoning", source["model_reasoning_source_type"])
                self.assertEqual("evidence_gap", source["evidence_gap_source_type"])
                self.assertEqual(
                    "CONTROL_DISPLAY_LABEL_IS_NOT_SOURCE_TYPE",
                    source["display_label_is_not_source_type_state"],
                )
                self.assertEqual(
                    "CONTROL_DISPLAY_PRESERVES_UNDERLYING_SOURCE_TYPES",
                    source["display_preserves_underlying_source_types_state"],
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP",
                    source["display_does_not_close_evidence_gap_state"],
                )
        gap_index = self.module.CONTROL_SCENARIOS.index(
            "draft_recommendation_evidence_gap_with_external_augmentation_reference_only"
        )
        self.assertIsNone(requests[gap_index]["internal_evidence_ref"])
        self.assertIsNotNone(requests[gap_index]["evidence_gap_ref"])

    def test_prompt_injection_and_output_permissions_preserve_whitebox_gate(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        projections = self.result[
            "prompt_injection_and_output_permission_control_projections"
        ]
        for request, projection in zip(requests, projections):
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(
                    request["model_output_permission_ref"],
                    projection["model_output_permission_ref"],
                )
                self.assertEqual(
                    request["human_confirmation_gate_ref"],
                    projection["human_confirmation_gate_ref"],
                )
                self.assertEqual(
                    "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
                    projection["retrieval_document_instruction_precedence_state"],
                )
                self.assertEqual(
                    "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                    projection["final_conclusion_state"],
                )
                self.assertEqual(
                    "CONTROL_AUTOMATIC_PUBLICATION_DISABLED",
                    projection["automatic_publication_state"],
                )
        injection_index = self.module.CONTROL_SCENARIOS.index(
            "retrieval_document_instruction_rejected_reference_only"
        )
        self.assertEqual(
            "CONTROL_UNTRUSTED_DOCUMENT_INSTRUCTION_REJECTED",
            projections[injection_index]["prompt_injection_defense_state"],
        )
        for scenario in (
            "high_risk_engineering_advice_confirmation_required_reference_only",
            "contractual_commitment_confirmation_required_reference_only",
            "production_writeback_confirmation_required_reference_only",
        ):
            index = self.module.CONTROL_SCENARIOS.index(scenario)
            self.assertEqual(
                "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                projections[index]["output_permission_state"],
            )

    def test_non_fixed_input_returns_zero_projection_rejection(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["query_ref"] = (
            ":control:stage101-p2:query:changed:reference-only"
        )
        result = self.module.execute_rag_reproducibility_control_slice(invalid_input)
        self.assertFalse(result["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_RAG_REPRODUCIBILITY_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", result["failure_state"])
        self.assertEqual(0, result["control_input_count"])
        self.assertEqual(0, result["control_projection_field_total"])
        self.assertTrue(
            all(value == 0 for key, value in result.items() if key.startswith("actual_"))
        )
        self.assertTrue(all(value is False for value in result["runtime_boundary"].values()))
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            self.assertEqual([], result[f"{prefix}_control_projections"])
            self.assertEqual(0, result[f"{prefix}_control_projection_count"])

    def test_contract_runtime_boundary_failure_shape_and_rollback_are_complete(self):
        contract = self.contract
        input_contract = contract["reference_only_control_input_contract"]
        self.assertEqual(
            list(self.module.INPUT_FIELDS), input_contract["input_fields"]
        )
        self.assertEqual(23, input_contract["input_field_count"])
        self.assertEqual(6, input_contract["control_request_count"])
        self.assertTrue(input_contract["all_values_are_control_labels_only"])
        for field, value in input_contract.items():
            if field.startswith("request_contains_") or field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        record = contract["reproducibility_record_contract"]
        self.assertEqual(8, record["required_record_reference_field_count"])
        self.assertEqual(
            set(self.module.REPRODUCIBILITY_RECORD_FIELDS) - {"record_shape_state"},
            set(record["required_record_reference_fields"]),
        )
        source = contract["source_type_and_external_augmentation_contract"]
        self.assertEqual(4, source["underlying_source_type_count"])
        self.assertEqual(
            {"internal_evidence", "external_public_reference", "model_reasoning", "evidence_gap"},
            set(source["underlying_source_types"]),
        )
        permission = contract["prompt_injection_and_output_permission_contract"]
        self.assertEqual(5, permission["output_category_count"])
        for field, value in permission.items():
            if field.endswith("_allowed") or field.startswith("actual_") or field.startswith("retrieval_document_can_"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        projection = contract["control_projection_contract"]
        self.assertEqual(4, projection["control_projection_group_count"])
        self.assertEqual(45, projection["control_projection_field_total_per_request"])
        self.assertEqual(270, projection["control_projection_field_total"])
        failures = contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "CONTROL_INPUT_MISMATCH",
            "REPRODUCIBILITY_RECORD_REFERENCE_MISSING",
            "RETRIEVAL_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACTUAL_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
            "SECOND_AUTHORITY_CREATED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        self.assertTrue(
            all(value is False for value in contract["runtime_boundary"].values())
        )
        self.assertTrue(
            all(value is False for value in contract["protected_surface_boundary"].values())
        )
        local_code = contract["local_code"]
        self.assertTrue(local_code["control_slice_module_created"])
        self.assertTrue(local_code["control_slice_is_pure_memory"])
        for field, value in local_code.items():
            if field not in {"control_slice_module_created", "control_slice_is_pure_memory"}:
                with self.subTest(field=field):
                    self.assertFalse(value)
        rollback = contract["rollback_contract"]
        self.assertEqual(
            "PHASE1_RAG_REPRODUCIBILITY_CONTRACT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage101_phase1_evidence"])
        self.assertTrue(rollback["preserve_stage100_review_evidence"])
        for field, value in rollback.items():
            if field.endswith("_allowed"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_scope_receipt_and_current_governance_are_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "external_augmentation_opinion",
            "IDS-STAGE101-P3-GATE",
            "270 个控制检查点",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase1_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P1",
            "IDS-V0_1-STAGE101-P1",
            "IDS-STAGE101-P2-GATE",
        )
        phase2_current = (
            "IDS-STAGE101",
            "IDS-STAGE101-P2",
            "IDS-V0_1-STAGE101-P2",
            "IDS-STAGE101-P3-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase1_current, phase2_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {
            item["id"]: item["status"] for item in acceptance["items"]
        }
        for acceptance_id in (
            "ACC-STAGE101-P2-01",
            "ACC-STAGE101-P2-02",
            "ACC-STAGE101-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE101-P2-04"])
        self.assertEqual("IDS-STAGE101-P3-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_RAG_REPRODUCIBILITY_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn("EVT-IDS-V0_1-STAGE101-P2-20260825-001", event_ids)
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage101_phase2_state:", roadmap_text)
        if current == phase2_current:
            self.assertFalse(is_current_projection)
            for phrase in (
                'current_phase_id: "IDS-STAGE101-P2"',
                'next_gate_id: "IDS-STAGE101-P3-GATE"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        else:
            self.assertTrue(is_current_projection)


if __name__ == "__main__":
    unittest.main()
